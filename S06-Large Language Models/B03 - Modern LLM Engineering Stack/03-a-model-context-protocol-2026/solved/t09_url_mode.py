# ============================================================
# TOPIC: 09 — MRTR in URL mode: consent outside the model's context
# REF:   notes/09-url-mode.md
# RUN:   python solved/t09_url_mode.py
# ============================================================
#
# Topic 08's confirmation form asked for a name and a yes/no — small, harmless
# data that is fine for a model to read and relay. Card numbers are not. A
# server that needs a HUMAN to do something sensitive — pay, authorise, log in
# — must never route that data through the model's context at all.
#
# URL-mode elicitation is the answer: the server hands back a LINK. The client
# opens it for the human, directly, outside the conversation. The model learns
# only whether the human said yes — never what they typed on that page.
#
# The interesting design problem this topic solves is one the SDK does not
# solve for you: form-mode's answer arrives as structured content the SDK can
# validate against your schema. A URL has no such content — a human clicked
# around on a page you do not control the rendering of. So how does round 2
# know the human actually paid, rather than the client simply lying with
# `action: "accept"`?
#
# The answer is the same primitive as everything else in this folder: a signed
# token. The "pay page" in this file is itself a small MCP-adjacent HTTP route
# that, on completion, mints a RECEIPT — a token proving "this exact order, for
# this exact amount, was paid, and this server is the one that says so". The
# receipt travels back as ordinary `content` on the retry, and round 2 checks
# it exactly the way topic 07 taught you to check anything signed: verify the
# signature, check the `kind`, and check that the payload's CONTENTS match what
# you expect — not just that a signature exists.

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
NONCE_TTL_S = 5 * 60  # the payment link itself expires quickly
RECEIPT_TTL_S = 5 * 60  # the receipt, once minted, must be redeemed quickly too


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
        "to open a payment LINK — never ask the customer for card details "
        "yourself, and never put any card information in your own messages. "
        "Once the customer says they have completed the page, call "
        "`pay_for_order` again with THE SAME order token to finish."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Pay for the order",
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    )
)
async def pay_for_order(
    order: Annotated[str, Field(description="The order token to pay for.")],
    ctx: Context,
) -> PaymentAccepted | PaymentNotCompleted | InputRequiredResult:
    """Pay for an order. Sends the customer to a payment page rather than
    asking for card details in this conversation.

    Call with an order token. The first call comes back with a link — tell the
    customer to open it and complete payment there, never here. Once they
    confirm they are done, call `pay_for_order` again with THE EXACT SAME order
    token to finish.
    """
    print(
        f"  [server] pay_for_order(round={'2' if ctx.input_responses else '1'})",
        file=sys.stderr,
    )

    try:
        cart_lines = orders.load_cart(order)
        priced_lines = orders.reprice(cart_lines)
    except (tokens.TokenError, orders.OrderPricingError) as exc:
        raise ToolError(f"Can't pay for this order: {exc}. Build a fresh order first.") from None

    if not priced_lines:
        raise ToolError("This order has no items to pay for.")

    total = orders.total_of(priced_lines)

    # ============================================================
    # ROUND 1 — mint a payment link, not a form
    # ============================================================
    if ctx.input_responses is None:
        # The nonce IS a signed token. There is no server memory linking a
        # nonce to an order — a nonce path segment has to carry everything the
        # /pay/{nonce} route will need, the same way every token in this folder
        # does. It binds the nonce to THIS order and THIS total so the pay page
        # cannot be reused to authorise a different amount.
        nonce = tokens.sign(PAY_NONCE_KIND, {"order": order, "total": total}, ttl_s=NONCE_TTL_S)
        pay_url = f"http://{HOST}:{PORT}/pay/{nonce}"

        return InputRequiredResult(
            result_type="input_required",
            input_requests={
                "pay": ElicitRequest(
                    method="elicitation/create",
                    params=ElicitRequestURLParams(
                        mode="url",
                        message=(
                            f"Open this link to pay ${total:.2f} for "
                            f"{orders.summarize(priced_lines)}. Do not enter any "
                            f"card details in this chat."
                        ),
                        url=pay_url,
                    ),
                )
            },
            # Same use as topic 08: not what binds the retry (the SDK already
            # does that for the `order` argument automatically) — this is
            # where the quote is written down so round 2 can catch drift.
            request_state=f'{{"quoted_total": {total}}}',
        )

    # ============================================================
    # ROUND 2 — a receipt, not a form answer
    # ============================================================
    quoted_total = json.loads(ctx.request_state)["quoted_total"]
    if abs(quoted_total - total) > 0.001:
        raise ToolError(
            f"The price changed since you were quoted ${quoted_total:.2f} (it is "
            f"now ${total:.2f}). Call `view_order`, then `pay_for_order` again."
        )

    confirmation = ctx.input_responses["pay"]
    confirmation = getattr(confirmation, "root", confirmation)

    if confirmation.action != "accept":
        print(
            f"  [server]   -> customer did not complete payment ({confirmation.action})",
            file=sys.stderr,
        )
        return PaymentNotCompleted(reason=f"payment not completed ({confirmation.action})")

    # --- THE PART A NAIVE INTEGRATION SKIPS ---
    # `confirmation.action == "accept"` on its own proves NOTHING. It is a
    # claim made by whoever sent this retry — a compromised or careless client
    # could send "accept" without the human ever visiting the link at all. The
    # only thing worth trusting is a RECEIPT this server itself minted, and
    # only after checking three things about it, in order: is the signature
    # genuine, is it the RIGHT KIND of token (domain separation — a pay_nonce
    # must never be accepted here as a receipt), and does its CONTENT actually
    # match this order and this total (a validly-signed receipt for a
    # DIFFERENT, cheaper order must not authorise this one).
    receipt = (confirmation.content or {}).get("receipt")
    if not receipt:
        raise MCPError(
            code=INVALID_PARAMS,
            message="No payment receipt was provided. The customer must complete "
            "the payment page before this can be confirmed.",
            data={"argument": "receipt"},
        )

    try:
        receipt_body = tokens.verify(RECEIPT_KIND, receipt)
    except tokens.TokenError as exc:
        raise ToolError(
            f"That payment receipt is not valid ({exc}). Send the customer back "
            f"to a fresh payment link — call `pay_for_order` again with no "
            f"prior confirmation."
        ) from None

    if receipt_body["order"] != order or abs(receipt_body["total"] - total) > 0.001:
        # A real, validly-signed receipt — just not for THIS order or THIS
        # amount. Signature verification and payload-content verification are
        # different checks, and skipping the second is a real vulnerability.
        raise ToolError(
            "This payment receipt does not match the current order. It may have "
            "been issued for a different order or a different total."
        )

    ticket = f"P-{abs(hash((order, total))) % 1000:03d}"
    print(f"  [server]   -> PAID, ticket {ticket}, total {total}", file=sys.stderr)
    return PaymentAccepted(
        ticket=ticket,
        lines=[OrderLine(**line.as_dict()) for line in priced_lines],
        total=total,
        served_by=_served_by(),
    )


# --- The fake payment page ---
# A GET renders a confirmation page a human would actually see. A POST to the
# SAME path is "the human clicked Pay" — this is what makes the flow testable
# from curl without a real browser, and it is the ONLY place in this whole
# server that mints a RECEIPT_KIND token.
@mcp.custom_route("/pay/{nonce}", methods=["GET", "POST"])
async def pay_page(request: Request):
    nonce = request.path_params["nonce"]
    try:
        nonce_body = tokens.verify(PAY_NONCE_KIND, nonce)
    except tokens.TokenError as exc:
        message = f"This payment link is not valid: {exc}"
        if request.method == "GET":
            return HTMLResponse(f"<h1>Payment link expired</h1><p>{message}</p>", status_code=400)
        return JSONResponse({"error": message}, status_code=400)

    total = nonce_body["total"]

    if request.method == "GET":
        # What a human would actually see if they opened this link. No MCP
        # traffic happens here at all — this is a plain web page.
        return HTMLResponse(
            f"<h1>Pay ${total:.2f}</h1>"
            f"<p>This is a fake payment page for the café learning project. "
            f"No real payment processor is involved.</p>"
            f'<form method="POST"><button type="submit">Pay ${total:.2f}</button></form>'
        )

    # POST: "the human clicked Pay". Mint the receipt — the ONLY proof round 2
    # of pay_for_order will accept.
    receipt = tokens.sign(
        RECEIPT_KIND, {"order": nonce_body["order"], "total": total}, ttl_s=RECEIPT_TTL_S
    )
    print(f"  [pay page] minted a receipt for total {total}", file=sys.stderr)
    return JSONResponse({"paid": True, "total": total, "receipt": receipt})


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "09"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 09 — MRTR in URL mode")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68)
    print("  You need an order token first:")
    print("    bash curl/08_get_order_token.sh")
    print("  Then, IN ORDER:")
    print("    bash curl/09_pay_round1.sh <order token>")
    print("    bash curl/09_visit_pay_page.sh <the url from round 1>")
    print("    bash curl/09_pay_round2.sh <order token> <requestState> <receipt>")
    print("    bash curl/09_fake_receipt.sh <order token> <requestState>  <- the attack, blocked")
    print("    bash curl/09_walk_payment.sh                <- the whole flow, scripted")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
