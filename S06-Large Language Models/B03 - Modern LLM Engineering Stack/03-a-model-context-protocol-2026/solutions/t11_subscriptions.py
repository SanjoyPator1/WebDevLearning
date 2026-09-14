# ============================================================
# TOPIC: 11 — subscriptions/listen: where statelessness leaks
# REF:   notes/11-subscriptions.md
# RUN:   python solutions/t11_subscriptions.py
# ============================================================
#
# YOUR TURN. Five TODOs. This is the one topic in the whole folder whose state
# does NOT live in a signed token — read notes/11-subscriptions.md before
# touching this file, because that absence is the entire point.
#
# Prove it from outside, in two terminals:
#     Terminal 1:  bash curl/11_listen.sh
#     Terminal 2:  bash curl/11_sell_out.sh espresso
#                  bash curl/11_un_sell_out.sh espresso
#
# Then, no copy-pasting required:
#     bash curl/11_two_listeners.sh          <- fan-out, ONE instance
#     bash curl/11_cross_instance_leak.sh    <- the central proof

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

# TODO 1: Declare SOLD_OUT.
#   A plain `set[str]` of slugs, module-level, empty to start. This is
#   deliberately NOT a signed token like everything else in this folder — it
#   is ordinary Python state, living only in this one process's memory. That
#   is the whole point: it will not survive being one of several instances
#   behind a load balancer, and this topic is about seeing that happen.
SOLD_OUT: set[str] = set()


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


def _menu_document() -> str:
    """The menu, plus which drinks THIS INSTANCE currently believes are sold
    out, and which instance is answering."""
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
        # TODO 2: Give resources/read a SHORT ttl (a few seconds), not the long
        #   one topic 04 used. Why does a resource backed by subscriptions/listen
        #   still want a cache hint at all, given the client can be told the
        #   moment it changes? (Hint: what happens if a notification is missed —
        #   dropped connection, client wasn't listening yet?)
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


# TODO 3: Write sell_out(slug, ctx) -> str.
#
#   Validate the slug against menu.find, raising ToolError for an unknown one
#   (same pattern as every earlier topic). Add it to SOLD_OUT.
#
#   Then the one line this whole topic is about:
#       await ctx.notify_resource_updated("cafe://menu")
#
#   Every listener currently attached to THIS instance's subscription bus gets
#   a notifications/resources/updated event. Nothing on a DIFFERENT instance
#   hears anything — there is no code you could add here to fix that; the fix
#   is a different kind of bus entirely (topic 14).
#
#   Annotations: not read_only (it changes the menu), not destructive (nothing
#   is lost — un_sell_out reverses it), idempotent (selling out an
#   already-sold-out drink changes nothing further).
@mcp.tool()  # replace with annotations
async def sell_out(slug: str, ctx: Context) -> str:
    """TODO: write this for a model to read."""
    raise NotImplementedError  # replace


# TODO 4: Write un_sell_out(slug, ctx) -> str. The mirror image of TODO 3:
#   discard from SOLD_OUT instead of adding, notify the same way.
@mcp.tool()  # replace with annotations
async def un_sell_out(slug: str, ctx: Context) -> str:
    """TODO: write this for a model to read."""
    raise NotImplementedError  # replace


# --- Health ---
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "server": "cafe-mcp", "topic": "11", "instance": _served_by()}
    )


def main() -> None:
    print("-" * 68)
    print("TOPIC 11 — subscriptions/listen (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()


# TODO 5 (no code — an experiment): run curl/11_cross_instance_leak.sh, but
#   BEFORE you run it, predict in one sentence what instance A's listener will
#   see after sell_out runs on instance B. Then run it and check. If your
#   prediction was right, explain out loud why a bigger or better-signed
#   order token could never have fixed this — the answer is the difference
#   between topic 11 and every topic before it.
