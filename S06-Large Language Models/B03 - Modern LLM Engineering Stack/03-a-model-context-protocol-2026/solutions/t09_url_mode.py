# ============================================================
# TOPIC: 09 — MRTR in URL mode: consent outside the model's context
# REF:   notes/09-url-mode.md
# RUN:   python solutions/t09_url_mode.py
# ============================================================
#
# YOUR TURN. Topic 08's confirmation form asked for a name and yes/no — fine
# for a model to see. A card number is not. This topic sends the human to a
# LINK instead of a form, and answers the question the SDK does not answer for
# you: how does round 2 know the human actually paid, rather than the client
# simply lying with action="accept"?
#
# Seven TODOs. TODO 5 (the receipt check) is the one that matters most.
#
# Prove it from outside, IN ORDER:
#     bash curl/08_get_order_token.sh
#     bash curl/09_pay_round1.sh <order token>
#     bash curl/09_visit_pay_page.sh <url from round 1>
#     bash curl/09_pay_round2.sh <order token> <requestState> <receipt>
#     bash curl/09_no_receipt.sh <order token> <requestState>       <- attack 1
#     bash curl/09_wrong_order_receipt.sh <order token> <requestState>  <- attack 2
#     bash curl/09_walk_payment.sh                                   <- scripted

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
    ElicitRequestURLParams,
    InputRequiredResult,
    ToolAnnotations,
)
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from cafe_mcp import orders, tokens

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))
PAY_NONCE_KIND = "pay_nonce"
RECEIPT_KIND = "payment_receipt"
NONCE_TTL_S = 5 * 60
RECEIPT_TTL_S = 5 * 60


class OrderLine(BaseModel):
    slug: str
    name: str
    size: str
    qty: int
    unit_price: float
    line_total: float


class PaymentAccepted(BaseModel):
    ticket: str
    lines: list[OrderLine]
    total: float
    served_by: str


class PaymentNotCompleted(BaseModel):
    placed: bool = False
    reason: str


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


mcp = MCPServer(
    name="cafe-mcp",
    version="0.9.0",
    instructions=(
        "You are working the counter of a small coffee shop. Call `pay_for_order` "
        "with an order token to pay for it. It will come back asking the customer "
        "to open a payment LINK — never ask for card details yourself."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


# TODO 1: Annotate pay_for_order.
#   Like place_order in topic 08: not read-only, IS destructive, NOT
#   idempotent.
@mcp.tool()  # replace with annotations
async def pay_for_order(
    order: Annotated[str, Field(description="The order token to pay for.")],
    ctx: Context,
) -> PaymentAccepted | PaymentNotCompleted | InputRequiredResult:
    """TODO: write this. Tell the model never to ask for card details itself."""
    print(
        f"  [server] pay_for_order(round={'2' if ctx.input_responses else '1'})",
        file=sys.stderr,
    )

    # TODO 2: Load and reprice the cart, exactly as topic 08 did.
    #   orders.load_cart / orders.reprice, catching TokenError /
    #   OrderPricingError and raising ToolError. Refuse an empty cart.
    raise NotImplementedError  # replace up to here, then continue below

    # ============================================================
    # TODO 3: ROUND 1 — mint a payment LINK, not a form.
    # ============================================================
    #   The nonce itself must be a signed token (kind=PAY_NONCE_KIND) carrying
    #   {"order": order, "total": total} — there is no server memory to look
    #   the nonce up in later, so the nonce has to carry everything the pay
    #   page will need, the same way every token in this folder does.
    #
    #   Build the URL: f"http://{HOST}:{PORT}/pay/{nonce}"
    #
    #   Return InputRequiredResult with input_requests={"pay":
    #   ElicitRequest(method="elicitation/create",
    #       params=ElicitRequestURLParams(mode="url", message=..., url=...))}
    #   and request_state carrying the quoted total (same purpose as topic 08:
    #   catching a price that drifted between round 1 and round 2 — the SDK's
    #   automatic binding covers `order` but knows nothing about prices).

    # ============================================================
    # TODO 4: ROUND 2 — check the price drift, same as topic 08.
    # ============================================================
    #   json.loads(ctx.request_state)["quoted_total"], compare against a
    #   freshly computed total, ToolError if they differ by more than a cent.
    #
    #   Then read ctx.input_responses["pay"] (getattr(x, "root", x) if needed).
    #   If action != "accept", return PaymentNotCompleted — not an error.

    # ============================================================
    # TODO 5: THE PART THAT MATTERS. Verify the receipt properly.
    # ============================================================
    #   `action == "accept"` proves NOTHING by itself — it is a claim by
    #   whoever sent the retry. Pull `confirmation.content.get("receipt")`.
    #   If it's missing, raise MCPError(code=INVALID_PARAMS, ...) — no receipt,
    #   no payment.
    #
    #   If present, verify it: tokens.verify(RECEIPT_KIND, receipt), catching
    #   TokenError -> ToolError.
    #
    #   THEN — and this is the step a naive integration skips — check that the
    #   receipt's OWN CONTENT matches what you're actually paying for right
    #   now: does receipt_body["order"] == order? Does receipt_body["total"]
    #   match the current total? A validly-signed receipt for a DIFFERENT,
    #   cheaper order must not authorise THIS one. Signature verification and
    #   payload-content verification are two different checks; write both.
    #
    #   If everything checks out, build and return a PaymentAccepted with a
    #   ticket.


# TODO 6: Write the fake payment page.
#
#   @mcp.custom_route("/pay/{nonce}", methods=["GET", "POST"])
#
#   Verify the nonce (kind=PAY_NONCE_KIND) — if invalid, an HTMLResponse (GET)
#   or JSONResponse (POST) explaining the link expired, status_code=400.
#
#   On GET: return an HTMLResponse — what a human would actually see. No MCP
#   traffic here at all; this is a plain web page.
#
#   On POST ("the human clicked Pay"): mint a receipt with
#   tokens.sign(RECEIPT_KIND, {"order": ..., "total": ...}, ttl_s=RECEIPT_TTL_S)
#   and return it as JSON: {"paid": True, "total": ..., "receipt": ...}.
#   This route is the ONLY place in the whole server that mints a receipt —
#   that is what makes it trustworthy.
async def pay_page(request: Request):
    raise NotImplementedError  # replace


# --- Health ---
# TODO 7: /healthz again.
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "09"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 09 — MRTR in URL mode (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
