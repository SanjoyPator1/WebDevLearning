# ============================================================
# TOPIC: 14 — three instances behind a round-robin proxy
# REF:   notes/14-load-balancer.md
# RUN:   python solved/loadbalancer.py     (starts THREE of these, plus a proxy)
# ============================================================
#
# YOUR TURN. Five TODOs. This is the payoff topic: nothing new to learn about
# the WIRE, only a question about which of your last thirteen topics survive
# being one of several replicas, and which do not.
#
# add_to_order / view_order are topic 07's tools — copy them in unmodified.
# sell_out / un_sell_out are topic 11's tools — copy them in unmodified too.
# The interesting line is the ONE constructor argument on MCPServer.

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
BUS_PATH = os.environ.get("CAFE_MCP_BUS_PATH", "/tmp/cafe_mcp_shared_bus.db")

SOLD_OUT: set[str] = set()


class OrderLine(BaseModel):
    slug: str
    name: str
    size: str
    qty: int
    unit_price: float
    line_total: float


class OrderResult(BaseModel):
    order: str
    lines: list[OrderLine]
    total: float
    expires_in_s: int
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


# TODO 1: Pass `subscriptions=SqliteSubscriptionBus(BUS_PATH)` to MCPServer
#   below. Every other server in this folder left this argument at its
#   default (an in-memory bus, private to one process). This ONE line is the
#   entire diff between topic 11's leak and this topic's fix — nothing inside
#   sell_out or notify_resource_updated changes at all. Before you add it, say
#   out loud why a signed token (the fix for everything in Part 3) could never
#   have fixed topic 11's leak the way it fixes this one.
mcp = MCPServer(
    name="cafe-mcp",
    version="0.14.0",
    instructions=(
        "You are working the counter of a small coffee shop, one of several "
        "identical instances behind a load balancer. Build an order with "
        "`add_to_order`, check it with `view_order` — either call may land on "
        "a different instance than the last one, and both work regardless."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


@mcp.resource("cafe://menu", name="menu", title="The café menu", mime_type="text/markdown")
def menu_resource() -> str:
    """The menu, including which drinks are sold out right now."""
    return _menu_document()


# TODO 2: Write add_to_order, copied from topic 07 (`solved/t07_order_token.py`
#   or your own `solutions/t07_order_token.py`) with ONE change: the docstring
#   should say this call may be answered by a different instance than the
#   last one. The function body needs nothing else — that is the point.
@mcp.tool()  # replace with annotations
def add_to_order(
    slug: Annotated[str, Field(description="The drink's slug, as in `list_drinks`.")],
    size: Annotated[Literal["S", "M", "L"], Field(description="Cup size.")],
    qty: Annotated[int, Field(ge=1, le=10, description="1 to 10.")] = 1,
    order: Annotated[str | None, Field(description="The order token from a previous call.")] = None,
) -> OrderResult:
    """TODO: write this for a model to read."""
    raise NotImplementedError  # replace


# TODO 3: Write view_order, copied from topic 07 unmodified.
@mcp.tool()  # replace with annotations
def view_order(
    order: Annotated[str, Field(description="The order token to inspect.")],
) -> OrderResult:
    """TODO: write this for a model to read."""
    raise NotImplementedError  # replace


# TODO 4: Write sell_out(slug, ctx) -> str, copied from topic 11 unmodified —
#   validate the slug, add it to SOLD_OUT, call
#   `await ctx.notify_resource_updated("cafe://menu")`. The tool code does not
#   know or care that the bus underneath it is now shared; that is exactly
#   why TODO 1 was a one-line change instead of a rewrite.
@mcp.tool()  # replace with annotations
async def sell_out(slug: str, ctx: Context) -> str:
    """TODO: write this for a model to read."""
    raise NotImplementedError  # replace


# TODO 5: Write un_sell_out(slug, ctx) -> str, the mirror image of TODO 4.
@mcp.tool()  # replace with annotations
async def un_sell_out(slug: str, ctx: Context) -> str:
    """TODO: write this for a model to read."""
    raise NotImplementedError  # replace


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "server": "cafe-mcp", "topic": "14", "instance": _served_by()}
    )


def main() -> None:
    print("-" * 68)
    print("TOPIC 14 — one replica of the load-balanced café (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print(f"  instance : {_served_by()}")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()


# TODO 6 (no code — an experiment): before running `python solved/loadbalancer.py`,
#   predict in one sentence what happens to an in-flight `subscriptions/listen`
#   connection when the proxy round-robins the NEXT request to a different
#   replica. Does the listener's own connection move? Then run it, open a
#   listen stream, and fire `sell_out` from a different terminal against a
#   DIFFERENT replica port directly — check your prediction against what
#   actually arrives.
