# ============================================================
# TOPIC: 07 — the order token: a shopping cart in a tool argument
# REF:   notes/07-the-order-token.md
# RUN:   python solutions/t07_order_token.py
# ============================================================
#
# YOUR TURN. Five TODOs.
#
# Topic 06's cursor was opaque but unsigned, because forging one was worthless —
# an offset into a public menu. This time the payload is a cart with a real total,
# so forging one IS worth something to an attacker, and that is the whole reason
# this token is HMAC-signed.
#
# `cafe_mcp/tokens.py` (generic signing) and `cafe_mcp/orders.py` (cart pricing
# and cart-specific signing, built on top of tokens.py) are both given to you
# complete and tested. What you are writing is the MCP-facing tool layer on top
# of them: the pydantic response shape, and the wiring that turns a domain
# failure (`orders.OrderPricingError`, `tokens.TokenError`) into a `ToolError`
# with a message a model can act on.
#
# Prove it from outside, IN ORDER:
#     bash curl/07_add_first_item.sh
#     bash curl/07_add_second_item.sh <token from above>
#     bash curl/07_view_order.sh <token>
#     bash curl/07_tamper.sh <token>        <- flip one character, watch it fail
#     bash curl/07_bad_size.sh
#     bash curl/07_walk_order.sh            <- the whole flow, scripted

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
ORDER_TTL_S = 15 * 60
MAX_QTY_PER_LINE = 10


class OrderLine(BaseModel):
    """One line item: a drink, a size, a quantity."""

    slug: str
    name: str
    size: str
    qty: int
    unit_price: float
    line_total: float


# TODO 1: Define OrderResult.
#   Fields: order (str — the token itself), lines (list[OrderLine]),
#   total (float), expires_in_s (int), served_by (str).
#   Field(description=...) on `order`: tell the model it is opaque, and to pass
#   it back as `order` on the next call.
class OrderResult(BaseModel):
    pass  # TODO 1: replace with the fields described above


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


# TODO 2: Write `_order_result(cart_lines) -> OrderResult`.
#
#   This is the wiring between `cafe_mcp.orders` (given, tested) and the
#   pydantic shape the SDK publishes a schema for:
#
#     1. `orders.reprice(cart_lines)` — recomputes every line's price from
#        TODAY's menu. Never trust a price you might have stored earlier: if
#        the café's prices changed since a line was added, the customer should
#        see today's price. The token remembers WHAT was ordered, never what it
#        cost at the time. This can raise `orders.OrderPricingError` if a line
#        is no longer sellable — catch it and raise `ToolError` instead, with a
#        message that tells the model to start a new order.
#     2. `orders.total_of(priced_lines)` — the total.
#     3. `orders.sign_cart(cart_lines, ttl_s=ORDER_TTL_S)` — a FRESH signed
#        token for the current state. Note this signs the ORIGINAL cart_lines
#        (slug/size/qty), not the priced ones — the token stores what was
#        ordered, not what it costs.
def _order_result(cart_lines: list[dict]) -> OrderResult:
    raise NotImplementedError  # replace


mcp = MCPServer(
    name="cafe-mcp",
    version="0.7.0",
    instructions=(
        "You are working the counter of a small coffee shop.\n\n"
        # TODO 3: explain the order-token protocol to the model. Cover: the first
        # add_to_order call needs no `order` argument; every call returns a NEW
        # token; pass that token back to keep adding to the SAME cart; it expires
        # after 15 minutes.
        "..."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


# TODO 4: Write add_to_order(slug, size, qty=1, order=None) -> OrderResult.
#
#   Validate slug and size against the menu FIRST, before touching the cart — a
#   bad line should never get a chance to corrupt an otherwise-good order.
#
#   If `order` is None, start with an empty list of cart lines.
#   If `order` is given, load it with `orders.load_cart(order)` — catch
#   `tokens.TokenError` and convert to `ToolError`. Think about what recovery you
#   can honestly offer here: is there a "try a different token" option, the way
#   there was a "try a different slug" option in topic 03? (You answered this
#   exact question for a bad CURSOR in topic 06 — same answer applies here.)
#
#   Append the new line ({"slug": ..., "size": ..., "qty": ...}) to the cart
#   lines and return `_order_result(cart_lines)`.
#
#   Annotations: this CHANGES state (not read-only), nothing is ever REMOVED
#   (not destructive), and calling it twice adds two lines (not idempotent).
@mcp.tool()  # replace with annotations
def add_to_order(slug: str, size: str, qty: int = 1, order: str | None = None) -> OrderResult:
    """TODO: write this for a model to read. Explain the token contract."""
    print(
        f"  [server] add_to_order(slug={slug!r}, size={size!r}, qty={qty}, "
        f"order={'<token>' if order else None})",
        file=sys.stderr,
    )
    raise NotImplementedError  # replace


# TODO 5: Write view_order(order) -> OrderResult.
#
#   Just orders.load_cart(order) + _order_result(cart_lines). Note this MUTATES
#   NOTHING about the cart's contents, but it DOES mint a new token with a fresh
#   expiry — calling it is how a client keeps a cart alive without adding
#   anything. read_only_hint should still be True: nothing about the ORDER's
#   contents changed, only how long its token remains valid.
@mcp.tool()  # replace with annotations
def view_order(order: str) -> OrderResult:
    """TODO: write this for a model to read."""
    raise NotImplementedError  # replace


# --- Health ---
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "07"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 07 — the order token (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
