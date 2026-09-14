# ============================================================
# TOPIC: 10 — progress on the response stream
# REF:   notes/10-progress-and-streaming.md
# RUN:   python solutions/t10_progress.py
# ============================================================
#
# YOUR TURN. Four code TODOs plus one experiment. This is the "streamable"
# half of streamable HTTP that nothing before this topic needed at all.
#
# Prove it from outside:
#     bash curl/10_get_order_token.sh
#     bash curl/10_brew_with_progress.sh <order token>
#     bash curl/10_brew_no_progress_token.sh <order token>   <- same work, silent
#     bash curl/10_interrupt_brew.sh <order token>            <- watch the SERVER terminal
#     bash curl/10_last_event_id.sh <order token>             <- proves no resumability

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
STEP_DELAY_S = 0.8
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


# TODO 1: Annotate brew.
#   It genuinely changes the world, but nothing is ever LOST by calling it —
#   worst case, a repeat call makes a second batch of the same drinks. Not
#   idempotent: two calls make two batches.
@mcp.tool()  # replace with annotations
async def brew(
    order: Annotated[str, Field(description="The order token to brew.")],
    ctx: Context,
) -> BrewResult:
    """TODO: write this. Warn that an interrupted connection cannot be resumed."""
    # TODO 2: Load and reprice the cart (same pattern as topics 07-09).
    #   orders.load_cart / orders.reprice, catching TokenError /
    #   OrderPricingError and raising ToolError. Refuse an empty cart.
    raise NotImplementedError  # replace up to here, then continue below

    # TODO 3: Brew every line, reporting progress the whole way through.
    #
    #   For each priced line, for each step in BREW_STEPS: increment a running
    #   `done` counter (across ALL lines, not reset per line — a two-line
    #   order should count 1..10, not 1..5 twice), build a message like
    #   f"{step} — {line.name} ({line.size})", call
    #
    #       await ctx.report_progress(progress=done, total=total_steps, message=message)
    #
    #   then `await anyio.sleep(STEP_DELAY_S)`.
    #
    #   THE POINT TO PROVE TO YOURSELF: this call produces an SSE event ON THE
    #   SAME RESPONSE the client is already waiting on. No new connection, no
    #   separate request. Confirm this by comparing
    #   curl/10_brew_with_progress.sh (progressToken set) against
    #   curl/10_brew_no_progress_token.sh (same code path, no token) — the
    #   SERVER does identical work either way; only the CLIENT's opt-in
    #   changes what arrives on the wire.

    # TODO 4: Return a BrewResult once every line is done.


# --- Health ---
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "10"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 10 — progress on the response stream (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()


# TODO 5 (no code — an experiment): run curl/10_interrupt_brew.sh while
#   WATCHING THIS SERVER'S OWN TERMINAL. Predict, before you run it, exactly
#   which step number the server's log will stop at, and whether it will ever
#   print "brew COMPLETE" for that interrupted call. Then run it and check.
