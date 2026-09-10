# ============================================================
# TOPIC: 11 — subscriptions/listen: where statelessness leaks
# REF:   notes/11-subscriptions.md
# RUN:   python solved/t11_subscriptions.py
# ============================================================
#
# Every RPC in this folder so far has been ASK-AND-ANSWER: one request, one
# reply, done. `subscriptions/listen` is the exception. A client opens it once
# and it stays open — potentially for the lifetime of a whole conversation —
# streaming a notification every time something the client asked about
# changes, with NO further request needed to keep hearing about it.
#
# That long-lived stream is why this topic exists, and why its title says
# "where statelessness leaks." Every other RPC you have built keeps its state
# in a signed token the CLIENT carries — any server instance can answer the
# next call because nothing lives only in one process's memory. This topic's
# state — which drinks are sold out right now — lives nowhere but this one
# process's RAM, in a plain Python set. Put three copies of this server behind
# a load balancer (topic 14 does exactly that) and a customer's listen stream
# is pinned, structurally, to whichever ONE instance answered it — an event
# published on a different instance never arrives, and there is no signed
# token that could fix that, because the thing missing is fan-out, not
# authentication.
#
# This file demonstrates the mechanism on a single instance: an ack, fan-out
# to several concurrent listeners, and a live update as it happens. The
# cross-instance gap is provable with two copies of this exact file — see
# notes/11-subscriptions.md and curl/11_cross_instance_leak.sh.

# --- Imports ---
import os
import sys
from typing import Annotated

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu, render

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))

# THIS is the state that does not survive a load balancer. Every other
# server in this folder kept its state in a token; this one keeps it in a
# plain Python set, in this process's memory, on purpose — that is the whole
# point of the topic. `CAFE_MCP_INSTANCE` is printed alongside it so you can
# tell, in a two-instance demo, which process actually holds a given fact.
SOLD_OUT: set[str] = set()


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


def _menu_document() -> str:
    """The menu, plus which drinks THIS INSTANCE currently believes are sold
    out. In a two-instance demo, two requests to two different instances can
    legitimately show two different answers here — that disagreement is not a
    bug, it is the lesson made visible."""
    doc = render.menu_markdown()
    if SOLD_OUT:
        doc += "\n## Sold Out Right Now\n\n"
        doc += "\n".join(f"- {menu.find(slug).name} (`{slug}`)" for slug in sorted(SOLD_OUT))
        doc += "\n"
    else:
        doc += "\n## Sold Out Right Now\n\nNothing — everything is available.\n"
    doc += f"\n_(answered by instance: {_served_by()})_\n"
    return doc


mcp = MCPServer(
    name="cafe-mcp",
    version="0.11.0",
    instructions=(
        "You are working the counter of a small coffee shop. Read `cafe://menu` for "
        "the current menu, including anything sold out right now. Staff can use "
        "`sell_out` and `un_sell_out` to mark a drink unavailable or available "
        "again; both change the live menu immediately."
    ),
    cache_hints={
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        # NOT cacheable with a long TTL, unlike topic 04's menu: this document
        # can now change at any moment a member of staff calls sell_out, and a
        # client relying on subscriptions/listen wants a SHORT ttl here as a
        # fallback in case it ever misses a notification.
        "resources/read": CacheHint(ttl_ms=5_000, scope="public"),
    },
)


@mcp.resource(
    "cafe://menu",
    name="menu",
    title="The café menu",
    mime_type="text/markdown",
)
def menu_resource() -> str:
    """The menu, including which drinks are sold out right now.

    Subscribe to this URI via `subscriptions/listen` to be told the moment it
    changes, instead of polling it.
    """
    return _menu_document()


@mcp.tool(
    annotations=ToolAnnotations(
        title="Mark a drink sold out",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,  # selling out an already-sold-out drink changes nothing further
        open_world_hint=False,
    )
)
async def sell_out(
    slug: Annotated[str, Field(description="The drink's slug, as in `cafe://menu`.")],
    ctx: Context,
) -> str:
    """Mark a drink as sold out. Changes the live menu immediately and notifies
    anyone subscribed to `cafe://menu` via `subscriptions/listen`."""
    if menu.find(slug) is None:
        raise ToolError(
            f"There is no drink with slug {slug!r}. Read `cafe://menu` for valid slugs."
        )

    SOLD_OUT.add(slug)
    print(f"  [server:{_served_by()}] sell_out({slug!r}) -- notifying subscribers", file=sys.stderr)
    # THE ONE LINE THIS WHOLE TOPIC IS ABOUT: publish to whatever
    # SubscriptionBus this MCPServer holds. Every listener currently attached
    # to THIS instance's bus (there may be several) gets a
    # notifications/resources/updated event. Nothing on a different instance
    # hears anything, because InMemorySubscriptionBus is exactly that: in
    # this process's memory, and nowhere else.
    await ctx.notify_resource_updated("cafe://menu")
    return f"{menu.find(slug).name} is now marked sold out."


@mcp.tool(
    annotations=ToolAnnotations(
        title="Bring a drink back",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def un_sell_out(
    slug: Annotated[str, Field(description="The drink's slug, as in `cafe://menu`.")],
    ctx: Context,
) -> str:
    """Mark a previously sold-out drink as available again. Notifies
    subscribers the same way `sell_out` does."""
    if menu.find(slug) is None:
        raise ToolError(
            f"There is no drink with slug {slug!r}. Read `cafe://menu` for valid slugs."
        )

    SOLD_OUT.discard(slug)
    print(
        f"  [server:{_served_by()}] un_sell_out({slug!r}) -- notifying subscribers",
        file=sys.stderr,
    )
    await ctx.notify_resource_updated("cafe://menu")
    return f"{menu.find(slug).name} is available again."


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse(
        {"status": "ok", "server": "cafe-mcp", "topic": "11", "instance": _served_by()}
    )


def main() -> None:
    print("-" * 68)
    print("TOPIC 11 — subscriptions/listen")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print(f"  instance : {_served_by()}")
    print("-" * 68)
    print("  In one terminal, open a listen stream:")
    print("    bash curl/11_listen.sh")
    print("  In another, change the menu:")
    print("    bash curl/11_sell_out.sh espresso")
    print("    bash curl/11_un_sell_out.sh espresso")
    print("-" * 68)
    print("  Then, without copy-pasting anything by hand:")
    print("    bash curl/11_two_listeners.sh          <- fan-out, ONE instance")
    print("    bash curl/11_cross_instance_leak.sh    <- the central proof")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
