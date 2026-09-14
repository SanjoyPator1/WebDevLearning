# ============================================================
# TOPIC: 08 — MRTR: input_required and requestState
# REF:   notes/08-mrtr.md
# RUN:   python solutions/t08_mrtr.py
# ============================================================
#
# YOUR TURN. This is the heart of the whole revision — read notes/08-mrtr.md in
# full before touching this file. Six TODOs, but TODO 4 and TODO 5 are where the
# real thinking happens.
#
# Before you write anything, be able to answer: topic 00 said zero server-to-
# client requests exist at 2026-07-28. So how does a tool ask "are you sure?"
# without one? (One sentence. If you cannot answer it, re-read notes/00 and
# notes/08's opening before continuing.)
#
# Prove it from outside, IN ORDER:
#     bash curl/08_get_order_token.sh                    <- mints you a token
#     bash curl/08_place_round1.sh <token>
#     bash curl/08_place_round2.sh <token> <requestState from round 1>
#     bash curl/08_decline.sh <token> <requestState>
#     bash curl/08_swap_order.sh <requestState>            <- the attack, blocked
#     bash curl/08_walk_mrtr.sh                             <- the whole flow, scripted

# --- Imports ---
import json
import os
import sys
from typing import Annotated

from mcp import MCPError
from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import (
    INVALID_PARAMS,
    ElicitRequest,
    ElicitRequestFormParams,
    InputRequiredResult,
    ToolAnnotations,
)
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import orders, tokens

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))


class OrderLine(BaseModel):
    slug: str
    name: str
    size: str
    qty: int
    unit_price: float
    line_total: float


class OrderPlaced(BaseModel):
    """The final, committed order — what round 2 returns on success."""

    ticket: str = Field(description="A ticket number for the counter, not a security token.")
    name: str = Field(description="The name the customer gave for the cup.")
    lines: list[OrderLine]
    total: float
    served_by: str


class OrderNotPlaced(BaseModel):
    """What round 2 returns if the customer declined or cancelled."""

    placed: bool = False
    reason: str


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


mcp = MCPServer(
    name="cafe-mcp",
    version="0.8.0",
    instructions=(
        "You are working the counter of a small coffee shop. Build an order with "
        "`add_to_order`, then call `place_order` with that same order token to "
        "commit it. `place_order` will ask you to confirm before it commits — "
        "when it does, relay the question to the customer, then call "
        "`place_order` again with THE SAME order token to complete it."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


# TODO 1: Annotate place_order correctly.
#   This is the FIRST genuinely destructive tool in the whole folder — it
#   commits money to an order. read_only_hint, destructive_hint, idempotent_hint
#   — get all three right, because a host uses these to decide whether to ask a
#   human before running a tool silently.
@mcp.tool()  # replace with annotations
async def place_order(
    order: Annotated[str, Field(description="The order token from add_to_order.")],
    ctx: Context,
) -> OrderPlaced | OrderNotPlaced | InputRequiredResult:
    """TODO: write this docstring. Tell the model to call again with the SAME
    order token after the confirmation question comes back."""
    print(
        f"  [server] place_order(order=<token>, round={'2' if ctx.input_responses else '1'})",
        file=sys.stderr,
    )

    # --- Load and price the cart. Runs identically on BOTH rounds. ---
    # TODO 2: Load the cart with `orders.load_cart(order)`, catching
    #   `tokens.TokenError` and raising `ToolError`. Then reprice it with
    #   `orders.reprice(cart_lines)`, catching `orders.OrderPricingError` and
    #   raising `ToolError`. Refuse an empty cart (no lines) with `ToolError`
    #   too — there is nothing to place.
    #
    #   Compute `total = orders.total_of(priced_lines)`.
    raise NotImplementedError  # replace up to here; keep going below once done

    # ============================================================
    # TODO 3: ROUND 1 — build the question.
    # ============================================================
    #   `if ctx.input_responses is None:` — this is the FIRST call. Return an
    #   `InputRequiredResult` with:
    #     result_type="input_required"
    #     input_requests={"confirm": ElicitRequest(method="elicitation/create",
    #         params=ElicitRequestFormParams(message=..., mode="form",
    #             requested_schema={...}))}
    #
    #   The message should show what's in the cart (orders.summarize) and the
    #   total, and ask for a name for the cup plus a yes/no confirm.
    #   requested_schema needs two top-level properties: "name" (string) and
    #   "confirm" (boolean), both required.
    #
    #   request_state=... — THIS IS THE PART TO THINK ABOUT. It is NOT what
    #   binds the retry to this order — the SDK already does that automatically
    #   for every argument, with no help from you (you will see this yourself
    #   in TODO 6). So what SHOULD go in request_state? Think about what
    #   information exists at round 1 that is NOT an argument, that round 2
    #   might need to compare against. (Hint: prices can change between round 1
    #   and round 2, even though the order token cannot.)

    # ============================================================
    # TODO 4: ROUND 2 — read the answer, and use request_state for what it's
    # actually for.
    # ============================================================
    #   ctx.request_state is the PLAINTEXT you handed back in TODO 3 — already
    #   unsealed and verified by the SDK before this function was even entered.
    #   Parse it (it's whatever string you put there — JSON is a reasonable
    #   choice) and compare against a freshly-computed value NOW. If they
    #   differ, something changed between round 1 and round 2 that the SDK's
    #   own binding could not have caught (because the ARGUMENT — the order
    #   token — never changed at all). Raise a ToolError telling the model to
    #   re-quote.
    #
    #   Then read `ctx.input_responses["confirm"]` — note it may need
    #   `getattr(x, "root", x)` depending on how it comes back; check for
    #   yourself what type it actually is. If `.action != "accept"`, return
    #   `OrderNotPlaced` with a reason — remember decline/cancel are SUCCESSFUL
    #   outcomes, not failures. If accepted, pull `name` out of `.content` and
    #   raise `MCPError(code=INVALID_PARAMS, ...)` if it's missing. Otherwise
    #   build and return an `OrderPlaced`.


# --- Health ---
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "08"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 08 — MRTR (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()


# TODO 5: once round 1 and round 2 both work, deliberately try to break it.
#   Mint TWO order tokens for two different carts. Get requestState from round
#   1 of the FIRST one. Try to complete round 2 for the SECOND cart's token,
#   using the FIRST cart's requestState. What happens? Why? (This is
#   curl/08_swap_order.sh — try to predict its output before you run it.)
#
# TODO 6: find out for yourself, rather than trusting this comment, whether
#   `place_order`'s return type annotation is REQUIRED to include
#   `InputRequiredResult` for the input_required path to work at all. Remove it
#   from the annotation (leave the `return InputRequiredResult(...)` in the
#   body) and see what actually happens on the wire.
