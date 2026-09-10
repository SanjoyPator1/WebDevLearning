# ============================================================
# TOPIC: 10 — progress on the response stream
# REF:   notes/10-progress-and-streaming.md
# RUN:   python solved/t10_progress.py
# ============================================================
#
# Every tool so far has been question-and-answer: one request, one reply, done
# in microseconds. `brew` takes a few real seconds, and while it runs it wants
# to say "grinding... tamping... extracting..." rather than leaving the caller
# staring at a blank line.
#
# This is the OTHER half of "streamable HTTP" — nothing before this topic has
# needed it. A quick tool call gets a plain JSON body back. A tool that reports
# progress gets its response framed as Server-Sent Events instead, with each
# progress update arriving as one SSE event on the SAME response stream, ahead
# of the final JSON-RPC result. One POST, one response, multiple events.
#
# The removal that matters just as much as the addition: 2026-07-28 deleted SSE
# resumability. There is no `Last-Event-ID`, no reconnecting mid-stream. Drop
# the connection during a brew and the work is simply gone — proven in this
# topic's notes by killing a real connection and watching the server's own
# task get cancelled mid-loop.

# --- Imports ---
import os
import sys
from typing import Annotated

import anyio
from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import orders, tokens

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))
# 0.8s makes curl demos and the interrupt experiment feel real. Tests override
# this to something tiny (CAFE_MCP_BREW_STEP_DELAY_S=0.01) — the PROGRESS
# MECHANICS being tested do not depend on the delay's size, only on a delay
# existing at all between report_progress calls.
STEP_DELAY_S = float(os.environ.get("CAFE_MCP_BREW_STEP_DELAY_S", "0.8"))

# One realistic step sequence per cup, in order. Reused for every line in the
# order, so a two-line order narrates ten steps total, not five.
BREW_STEPS = ("grinding", "tamping", "extracting", "steaming milk", "pouring")


class OrderLine(BaseModel):
    slug: str
    name: str
    size: str
    qty: int


class BrewResult(BaseModel):
    ready: bool
    lines: list[OrderLine]
    served_by: str


def _served_by() -> str:
    return os.environ.get("CAFE_MCP_INSTANCE", "single")


mcp = MCPServer(
    name="cafe-mcp",
    version="0.10.0",
    instructions=(
        "You are working the counter of a small coffee shop. Call `brew` with a "
        "paid order token once the customer has completed payment; it takes a "
        "few real seconds per drink and reports progress as it works."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Brew the order",
        # Genuinely changes the world (drinks get made) but nothing is EVER
        # lost by calling it — worst case, a second brew makes a second round
        # of the same drinks. Not idempotent either way: two calls make two
        # batches, not one.
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    )
)
async def brew(
    order: Annotated[str, Field(description="The order token to brew.")],
    ctx: Context,
) -> BrewResult:
    """Brew every drink in a paid order, reporting progress as it works.

    This takes several real seconds — one short pass per drink — and reports
    progress the whole way through. If the connection carrying this call is
    lost partway, the brew stops; there is no way to resume it. Call `brew`
    again from scratch if that happens.
    """
    try:
        cart_lines = orders.load_cart(order)
        priced_lines = orders.reprice(cart_lines)
    except (tokens.TokenError, orders.OrderPricingError) as exc:
        raise ToolError(f"Can't brew this order: {exc}. Check the order token.") from None

    if not priced_lines:
        raise ToolError("This order has no items to brew.")

    # Every line gets its own full pass through BREW_STEPS, so `total` counts
    # every step of every cup — a two-line order narrates ten steps, not five,
    # and `progress` climbs steadily across the whole job rather than
    # restarting at 1 for each drink.
    total_steps = len(priced_lines) * len(BREW_STEPS)
    done = 0

    for line in priced_lines:
        for step in BREW_STEPS:
            done += 1
            message = f"{step} — {line.name} ({line.size})"
            print(f"  [server] brew step {done}/{total_steps}: {message}", file=sys.stderr)
            # THIS is the whole topic. One call, one SSE event on the SAME
            # response the client is already waiting on — no separate
            # connection, no new request.
            await ctx.report_progress(progress=done, total=total_steps, message=message)
            await anyio.sleep(STEP_DELAY_S)

    print(f"  [server] brew COMPLETE ({total_steps}/{total_steps})", file=sys.stderr)
    result_lines = [
        OrderLine(slug=line.slug, name=line.name, size=line.size, qty=line.qty)
        for line in priced_lines
    ]
    return BrewResult(ready=True, lines=result_lines, served_by=_served_by())


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "10"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 10 — progress on the response stream")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print(f"  per-cup steps : {', '.join(BREW_STEPS)} ({STEP_DELAY_S}s each)")
    print("-" * 68)
    print("  You need a PAID order token — see topic 09, or:")
    print("    bash curl/10_get_order_token.sh")
    print("  Then:")
    print("    bash curl/10_brew_with_progress.sh <order token>")
    print("    bash curl/10_brew_no_progress_token.sh <order token>   <- silent, same work")
    print("    bash curl/10_interrupt_brew.sh <order token>            <- kill it mid-way")
    print("    bash curl/10_last_event_id.sh <order token>             <- proves no resumability")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
