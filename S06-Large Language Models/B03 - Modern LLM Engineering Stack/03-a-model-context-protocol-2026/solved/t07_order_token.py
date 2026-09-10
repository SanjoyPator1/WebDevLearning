# ============================================================
# TOPIC: 07 — the order token: a shopping cart in a tool argument
# REF:   notes/07-the-order-token.md
# RUN:   python solved/t07_order_token.py
# ============================================================
#
# Topic 06 answered "where does state live once sessions are gone?" for something
# read-only and worthless to forge — a page position. This topic asks the same
# question for something that actually matters: a shopping cart, carrying real
# items and a real total.
#
# The SHAPE is identical to topic 06's cursor: mint a token, hand it back, decode
# it on the next call. What changes is that this token is signed
# (cafe_mcp/tokens.py), because forging one is now the whole game — an attacker
# who could construct a valid-looking cart token for free could add items without
# paying, or claim a total lower than what they ordered.
#
# Two tools: add_to_order (start or extend a cart) and view_order (read it back
# without changing it). place_order — the one that actually commits — is topic 08,
# because committing needs a human's confirmation, and getting that confirmation
# without a session is the whole reason MRTR exists.

# --- Imports ---
import os
import sys
from typing import Annotated, Literal

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu, orders, tokens

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))
ORDER_TTL_S = 15 * 60  # 15 minutes — long enough to keep talking, short enough
# that a forgotten cart from yesterday cannot resurface and be charged today.
MAX_QTY_PER_LINE = 10


class OrderLine(BaseModel):
    """One line item: a drink, a size, a quantity."""

    slug: str
    name: str
    size: str
    qty: int
    unit_price: float
    line_total: float


class OrderResult(BaseModel):
    """The current state of a cart, plus the token that IS that cart."""

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
    served_by: str = Field(
        description=(
            "Which server instance is answering. Meaningful once several are "
            "running behind a load balancer — topic 14."
        )
    )


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


def _order_result(cart_lines: list[dict]) -> OrderResult:
    """Turn stored cart lines into the tool's return value: reprice every line
    against TODAY's menu, total them, and mint a fresh signed token.

    The pricing and signing mechanics live in `cafe_mcp.orders` — shared with
    topic 08's `place_order`, which needs to load and reprice a cart the exact
    same way on its way to committing it. This function is the thin MCP-facing
    layer: it converts `orders.OrderPricingError` to `ToolError` and builds the
    pydantic response shape the SDK publishes a schema for.
    """
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


mcp = MCPServer(
    name="cafe-mcp",
    version="0.7.0",
    instructions=(
        "You are working the counter of a small coffee shop.\n\n"
        "To build an order, call `add_to_order` once per drink. The FIRST call "
        "needs no `order` argument — omit it to start a new cart. Every call "
        "returns a NEW `order` token representing the cart so far; pass THAT "
        "token back on the next call to keep adding to the same cart. The token "
        "is opaque and expires after 15 minutes of inactivity.\n\n"
        "Sizes are S, M and L, but not every drink is sold in every size."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Add a drink to the order",
        # Adding a line changes state, so this is NOT read-only. It is also NOT
        # destructive (nothing is lost, only added) and NOT idempotent (calling
        # it twice adds two lines, not one).
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
    qty: Annotated[
        int, Field(ge=1, le=MAX_QTY_PER_LINE, description=f"1 to {MAX_QTY_PER_LINE}.")
    ] = 1,
    order: Annotated[
        str | None,
        Field(
            description=(
                "The order token from a previous call, to add to that same cart. "
                "Omit this on the FIRST call of a new order."
            )
        ),
    ] = None,
) -> OrderResult:
    """Add one drink to an order, starting a new order if none is given.

    Call this once per distinct drink+size combination. Omit `order` for the
    first item; pass back the `order` token this returns for every item after
    that, so they land in the same cart. The response always shows the FULL
    cart so far, not just the line you added.
    """
    print(
        f"  [server] add_to_order(slug={slug!r}, size={size!r}, qty={qty}, "
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
            # --- THE SAME RULE AS A BAD CURSOR, FOR THE SAME REASON ---
            # The order token is opaque, so there is nothing about it a model
            # could reason about to repair. The only honest recovery is starting
            # a fresh cart.
            raise ToolError(
                f"That order token is not valid ({exc}). Start a new order by "
                f"calling `add_to_order` again with no `order` argument."
            ) from None

    cart_lines.append({"slug": slug, "size": size, "qty": qty})
    result = _order_result(cart_lines)
    print(
        f"  [server]   -> cart now has {len(result.lines)} line(s), total {result.total}",
        file=sys.stderr,
    )
    return result


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
    """Show the current contents and total of an order, without changing it.

    Every call re-signs and returns a fresh token even though nothing changed —
    this REFRESHES the 15-minute expiry window, so checking on a cart keeps it
    alive.
    """
    print("  [server] view_order(order=<token>)", file=sys.stderr)
    try:
        cart_lines = orders.load_cart(order)
    except tokens.TokenError as exc:
        raise ToolError(
            f"That order token is not valid ({exc}). Start a new order with `add_to_order`."
        ) from None
    return _order_result(cart_lines)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "07"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 07 — the order token")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print(f"  ttl      : {ORDER_TTL_S}s")
    secret_status = (
        "CAFE_MCP_SECRET set"
        if os.environ.get("CAFE_MCP_SECRET")
        else "DEV DEFAULT (see stderr warning)"
    )
    print(f"  secret   : {secret_status}")
    print("-" * 68)
    print("  Try, IN ORDER:")
    print("    bash curl/07_add_first_item.sh")
    print("    bash curl/07_add_second_item.sh <order token from above>")
    print("    bash curl/07_view_order.sh <order token>")
    print("    bash curl/07_tamper.sh <order token>       <- flip one char")
    print("    bash curl/07_bad_size.sh")
    print("    bash curl/07_walk_order.sh                 <- does the whole flow for you")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
