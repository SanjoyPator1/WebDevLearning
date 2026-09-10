# ============================================================
# TOPIC: 08 — MRTR: input_required and requestState
# REF:   notes/08-mrtr.md
# RUN:   python solved/t08_mrtr.py
# ============================================================
#
# Topic 00 said the direction that used to carry a question — server asks
# client, via elicitation/create — is GONE at 2026-07-28. Zero server-to-client
# requests. So how does place_order ask "are you sure?" before it commits real
# money to a cart?
#
# It doesn't ask. It ANSWERS the call it received with a QUESTION, packaged as
# the reply, and the client — if it wants to proceed — reissues the SAME call a
# second time, this time carrying the answer. That is Multi Round-Trip Requests:
#
#     round 1:  tools/call place_order(order=X)
#           ->  resultType: "input_required", a form to fill in, and a
#               requestState token that means "I was in the middle of this"
#
#     round 2:  tools/call place_order(order=X)          <- SAME arguments
#               + inputResponses: {"confirm": {...the filled form...}}
#               + requestState: <the exact token from round 1>
#           ->  resultType: "complete", the order is placed (or declined)
#
# The one thing this file exists to teach you is that "SAME arguments" above is
# not a suggestion — the SDK ENFORCES it, automatically, on every retry, and
# that enforcement is the most interesting security property in the whole
# revision. Read notes/08-mrtr.md before this file; the code will make much
# more sense once you have seen it fail on purpose.

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
ORDER_TTL_S = 15 * 60


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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Place the order",
        # This is the first genuinely destructive tool in the whole folder: it
        # commits money to an order, and calling it twice with two different
        # confirmations places two orders.
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    )
)
async def place_order(
    order: Annotated[str, Field(description="The order token from add_to_order.")],
    ctx: Context,
) -> OrderPlaced | OrderNotPlaced | InputRequiredResult:
    """Place an order for real. Asks for confirmation before committing.

    Call this with the order token from `add_to_order`. The FIRST call will
    come back asking you to confirm the total and provide a name for the cup —
    when it does, ask the customer, then call `place_order` again with THE
    EXACT SAME order token (do not modify it) to finish. Declining is a normal,
    successful outcome, not an error.
    """
    print(
        f"  [server] place_order(order=<token>, round={'2' if ctx.input_responses else '1'})",
        file=sys.stderr,
    )

    # --- BOTH ROUNDS need the cart, and it must be the SAME cart both times ---
    # This lookup runs identically on round 1 and round 2. On round 2 it is
    # guaranteed to see the exact same `order` value it saw on round 1 — the
    # SDK's RequestStateBoundary refuses the retry outright if `order` (or any
    # other argument) has changed. See notes/08-mrtr.md for what that refusal
    # looks like on the wire.
    try:
        cart_lines = orders.load_cart(order)
    except tokens.TokenError as exc:
        raise ToolError(
            f"That order token is not valid ({exc}). Build a fresh order with "
            f"`add_to_order` and try again."
        ) from None

    try:
        priced_lines = orders.reprice(cart_lines)
    except orders.OrderPricingError as exc:
        raise ToolError(
            f"{exc} — the menu changed since this order was built. Start a new "
            f"order with `add_to_order`."
        ) from None

    if not priced_lines:
        raise ToolError("This order has no items. Add at least one drink with `add_to_order`.")

    total = orders.total_of(priced_lines)

    # ============================================================
    # ROUND 1 — ctx.input_responses is None
    # ============================================================
    if ctx.input_responses is None:
        summary = orders.summarize(priced_lines)
        return InputRequiredResult(
            result_type="input_required",
            input_requests={
                "confirm": ElicitRequest(
                    method="elicitation/create",
                    params=ElicitRequestFormParams(
                        message=(
                            f"Confirm {summary} — ${total:.2f}. What name should go on the cup?"
                        ),
                        mode="form",
                        # RequestedSchema, per the spec, is top-level primitives
                        # only — no nested objects. mcp 2.1.1 does not enforce
                        # this itself (see notes/appendix-sdk-vs-spec.md), so
                        # following it is on you, not the SDK.
                        requested_schema={
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "title": "Name for the cup"},
                                "confirm": {"type": "boolean", "title": "Place this order?"},
                            },
                            "required": ["name", "confirm"],
                        },
                    ),
                )
            },
            # --- WHAT request_state IS ACTUALLY FOR ---
            # It is NOT how the retry gets bound to this exact order — the SDK
            # already does that automatically, for every argument, without your
            # help. It is where YOU carry something that ISN'T an argument but
            # still needs to survive the round trip: here, the total the
            # customer was SHOWN. Round 2 uses it to detect a rare but real
            # case the automatic binding cannot see — the underlying cart is
            # unchanged (guaranteed by the binding) but the MENU PRICE moved
            # between round 1 and round 2.
            request_state=f'{{"quoted_total": {total}}}',
        )

    # ============================================================
    # ROUND 2 — ctx.input_responses is populated
    # ============================================================
    # ctx.request_state is the PLAINTEXT you handed back above — the SDK has
    # already unsealed it AND confirmed this retry's method, tool name and
    # arguments match round 1's exactly. If either check had failed, this
    # handler would never have been entered; the client would have received
    # `-32602 "Invalid or expired requestState"` instead.
    quoted_total = json.loads(ctx.request_state)["quoted_total"]
    if abs(quoted_total - total) > 0.001:
        # The cart is PROVABLY unchanged (the SDK guarantees that). The PRICE
        # moved underneath it between round 1 and round 2 — a race the
        # argument-binding cannot catch, because the argument (the order
        # token) never changed at all.
        raise ToolError(
            f"The price changed since you were quoted ${quoted_total:.2f} (it is "
            f"now ${total:.2f}). Call `view_order` to see the new total, then "
            f"call `place_order` again to reconfirm."
        )

    confirmation = ctx.input_responses["confirm"]
    confirmation = getattr(confirmation, "root", confirmation)

    if confirmation.action != "accept":
        # Declining is a NORMAL outcome, not a failure. The tool did its job —
        # it asked, and got an answer. resultType is still "complete".
        #
        # Note this is a lookup, not `confirmation.action + "d"` — that naive
        # concatenation turns "cancel" into "canceld", which is exactly the kind
        # of bug a test catches instantly and a human proofreading the code does
        # not, because "declined" from "decline" looks so plausible.
        past_tense = {"decline": "declined", "cancel": "cancelled"}
        reason = past_tense.get(confirmation.action, confirmation.action)
        print(f"  [server]   -> customer {reason}", file=sys.stderr)
        return OrderNotPlaced(reason=f"customer {reason}")

    name = confirmation.content.get("name") if confirmation.content else None
    if not name:
        raise MCPError(
            code=INVALID_PARAMS,
            message="A name for the cup is required to place the order.",
            data={"argument": "name"},
        )

    ticket = f"A-{abs(hash((name, total))) % 1000:03d}"
    print(f"  [server]   -> PLACED, ticket {ticket}, total {total}", file=sys.stderr)
    return OrderPlaced(
        ticket=ticket,
        name=str(name),
        lines=[OrderLine(**line.as_dict()) for line in priced_lines],
        total=total,
        served_by=_served_by(),
    )


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "08"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 08 — MRTR: input_required and requestState")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68)
    print("  You need an order token first — this server does not expose")
    print("  add_to_order. Get one with topic 07's server, or run:")
    print("    bash curl/08_get_order_token.sh")
    print("-" * 68)
    print("  Then, IN ORDER:")
    print("    bash curl/08_place_round1.sh <order token>")
    print("    bash curl/08_place_round2.sh <order token> <requestState>")
    print("    bash curl/08_decline.sh <order token> <requestState>")
    print("    bash curl/08_swap_order.sh <order token> <requestState>  <- the attack, blocked")
    print("    bash curl/08_walk_mrtr.sh                 <- the whole flow, scripted")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
