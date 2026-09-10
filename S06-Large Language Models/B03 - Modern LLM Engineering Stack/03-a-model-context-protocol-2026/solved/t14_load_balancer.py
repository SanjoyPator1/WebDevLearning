# ============================================================
# TOPIC: 14 — three instances behind a round-robin proxy
# REF:   notes/14-load-balancer.md
# RUN:   python solved/loadbalancer.py     (starts THREE of these, plus a proxy)
# ============================================================
#
# This is the payoff for topics 06-08 and the fix for topic 11, run against
# three genuinely separate OS processes instead of argued about in the
# abstract. One server file, started three times on three ports, each with:
#
#   - CAFE_MCP_INSTANCE set to a different label, so `served_by` in every
#     response tells you which replica actually answered.
#   - a SHARED SqliteSubscriptionBus (cafe_mcp.shared_bus), all three pointed
#     at the same file — the topic 11 fix, applied for real.
#
# add_to_order / view_order are topic 07's tools verbatim, reusing
# cafe_mcp.orders exactly as written. Nothing about them changes here — that
# is the entire point. A signed token needs no cooperation between replicas
# to be verified correctly by whichever one receives it next.
#
# sell_out / un_sell_out are topic 11's tools verbatim too. What changes is
# only the ONE constructor argument passed to MCPServer — subscriptions=...
# — not one line inside either function.

# --- Imports ---
import os
import sys
from typing import Annotated, Literal

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu, orders, render, tokens
from cafe_mcp.shared_bus import SqliteSubscriptionBus

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))
ORDER_TTL_S = 15 * 60

# Every instance MUST point at the same file for the fix to do anything at
# all — this is the one piece of configuration a real deployment would need
# to get right (a shared Redis URL, not a shared file path, in production).
BUS_PATH = os.environ.get("CAFE_MCP_BUS_PATH", "/tmp/cafe_mcp_shared_bus.db")

SOLD_OUT: set[str] = set()


class OrderLine(BaseModel):
    """One line item: a drink, a size, a quantity."""

    slug: str
    name: str
    size: str
    qty: int
    unit_price: float
    line_total: float


class OrderResult(BaseModel):
    """The current state of a cart, plus the token that IS that cart and the
    instance that answered — the field topics 06-08 never needed, because
    only here are there several instances to tell apart."""

    order: str = Field(
        description=(
            "The order token — this cart's entire state, signed. Pass it back as "
            "`order` on the next add_to_order or view_order call. Treat it as "
            "opaque: never construct or edit one."
        )
    )
    lines: list[OrderLine]
    total: float = Field(description="Sum of every line's line_total.")
    expires_in_s: int = Field(description="Seconds until this token stops being valid.")
    served_by: str = Field(description="Which server instance answered this call.")


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


def _order_result(cart_lines: list[dict]) -> OrderResult:
    try:
        priced_lines = orders.reprice(cart_lines)
    except orders.OrderPricingError as exc:
        raise ToolError(
            f"{exc} — the menu changed since this item was added. Start a new "
            f"order with `add_to_order`."
        ) from None

    new_token = orders.sign_cart(cart_lines, ttl_s=ORDER_TTL_S)
    return OrderResult(
        order=new_token,
        lines=[OrderLine(**line.as_dict()) for line in priced_lines],
        total=orders.total_of(priced_lines),
        expires_in_s=ORDER_TTL_S,
        served_by=_served_by(),
    )


def _menu_document() -> str:
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
    version="0.14.0",
    instructions=(
        "You are working the counter of a small coffee shop, one of several "
        "identical instances behind a load balancer. Build an order with "
        "`add_to_order`, check it with `view_order` — either call may land on "
        "a different instance than the last one, and both work regardless. "
        "Staff use `sell_out`/`un_sell_out` to change the live menu."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
    # THE ONE LINE THAT FIXES TOPIC 11. Every other MCPServer in this folder
    # left this argument at its default (InMemorySubscriptionBus). Passing a
    # bus every instance shares is the entire diff between "leaks" and
    # "does not leak" — nothing inside sell_out or notify_resource_updated
    # changes at all.
    subscriptions=SqliteSubscriptionBus(BUS_PATH),
)


@mcp.resource("cafe://menu", name="menu", title="The café menu", mime_type="text/markdown")
def menu_resource() -> str:
    """The menu, including which drinks are sold out right now. Subscribe via
    `subscriptions/listen` to be told the moment it changes."""
    return _menu_document()


@mcp.tool(
    annotations=ToolAnnotations(
        title="Add a drink to the order",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    )
)
def add_to_order(
    slug: Annotated[str, Field(description="The drink's slug, as in `list_drinks`.")],
    size: Annotated[
        Literal["S", "M", "L"],
        Field(description="Cup size. Not every drink is sold in every size."),
    ],
    qty: Annotated[int, Field(ge=1, le=10, description="1 to 10.")] = 1,
    order: Annotated[
        str | None,
        Field(description="The order token from a previous call. Omit on the first call."),
    ] = None,
) -> OrderResult:
    """Add one drink to an order, starting a new order if none is given.

    THIS CALL MAY BE ANSWERED BY A DIFFERENT INSTANCE than your last one — it
    does not matter. Everything this tool needs to know is inside `order`
    itself, signed, so any instance can pick up exactly where the last one
    left off.
    """
    print(
        f"  [instance:{_served_by()}] add_to_order(slug={slug!r}, size={size!r}, "
        f"order={'<token>' if order else None})",
        file=sys.stderr,
    )

    if menu.find(slug) is None:
        raise ToolError(f"There is no drink with slug {slug!r}. Call `list_drinks` first.")
    if menu.price_of(slug, size) is None:
        available = ", ".join(menu.sizes_for(slug))
        raise ToolError(
            f"{menu.find(slug).name} is not sold in size {size!r}. It comes in: {available}."
        )

    if order is None:
        cart_lines: list[dict] = []
    else:
        try:
            cart_lines = orders.load_cart(order)
        except tokens.TokenError as exc:
            raise ToolError(
                f"That order token is not valid ({exc}). Start a new order by "
                f"calling `add_to_order` again with no `order` argument."
            ) from None

    cart_lines.append({"slug": slug, "size": size, "qty": qty})
    return _order_result(cart_lines)


@mcp.tool(
    annotations=ToolAnnotations(
        title="View an order",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def view_order(
    order: Annotated[str, Field(description="The order token to inspect.")],
) -> OrderResult:
    """Show the current contents and total of an order, on WHICHEVER instance
    answers this call — proves the token, not the process, is what remembers
    the cart."""
    print(f"  [instance:{_served_by()}] view_order(order=<token>)", file=sys.stderr)
    try:
        cart_lines = orders.load_cart(order)
    except tokens.TokenError as exc:
        raise ToolError(
            f"That order token is not valid ({exc}). Start a new order with `add_to_order`."
        ) from None
    return _order_result(cart_lines)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Mark a drink sold out",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def sell_out(
    slug: Annotated[str, Field(description="The drink's slug, as in `cafe://menu`.")],
    ctx: Context,
) -> str:
    """Mark a drink as sold out. Notifies anyone subscribed to `cafe://menu`
    via `subscriptions/listen` — including listeners connected to a DIFFERENT
    instance than this one, because of the shared bus this server was built
    with."""
    if menu.find(slug) is None:
        raise ToolError(
            f"There is no drink with slug {slug!r}. Read `cafe://menu` for valid slugs."
        )
    SOLD_OUT.add(slug)
    print(
        f"  [instance:{_served_by()}] sell_out({slug!r}) -- publishing to the SHARED bus",
        file=sys.stderr,
    )
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
    """Mark a previously sold-out drink as available again."""
    if menu.find(slug) is None:
        raise ToolError(
            f"There is no drink with slug {slug!r}. Read `cafe://menu` for valid slugs."
        )
    SOLD_OUT.discard(slug)
    print(f"  [instance:{_served_by()}] un_sell_out({slug!r})", file=sys.stderr)
    await ctx.notify_resource_updated("cafe://menu")
    return f"{menu.find(slug).name} is available again."


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse(
        {"status": "ok", "server": "cafe-mcp", "topic": "14", "instance": _served_by()}
    )


def main() -> None:
    print("-" * 68)
    print("TOPIC 14 — one replica of the load-balanced café")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print(f"  instance : {_served_by()}")
    print(f"  bus path : {BUS_PATH}")
    print("-" * 68)
    print("  Run this directly to see ONE instance. For the real payoff:")
    print("    python solved/loadbalancer.py")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
