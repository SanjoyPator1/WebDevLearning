# ============================================================
# TOPIC: 06 — pagination: the opaque cursor
# REF:   notes/06-pagination.md
# RUN:   python solutions/t06_pagination.py
# ============================================================
#
# YOUR TURN. Four TODOs. This opens Part 3.
#
# Before you write anything, answer this from memory: topic 00 asked where state
# lives once sessions are gone. Where does IT go? (One word.) This topic is the
# smallest possible instance of that answer — a cursor only has to remember a
# position, nothing more.
#
# `cafe_mcp/pagination.py` is given to you complete — it is the mechanism, and it
# has its own tests. What you are writing is the tool that uses it.
#
# Prove it from outside, IN ORDER:
#     bash curl/06_list_page1.sh
#     bash curl/06_list_next.sh <cursor from above>
#     bash curl/06_walk_all_pages.sh
#     bash curl/06_decode_cursor.sh <any cursor>    <- opaque is not secret
#     bash curl/06_bad_cursor.sh

# --- Imports ---
import os
import sys
from typing import Annotated

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu, pagination

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))
PAGE_SIZE = 5


# TODO 1: Define DrinkPage.
#   Fields: drinks (list[menu.Drink]), next_cursor (str | None).
#   Field(description=...) on next_cursor should tell the model three things:
#     - pass it back as `cursor` to continue
#     - null/absent means this was the last page
#     - never construct or edit one yourself
class DrinkPage(BaseModel):
    pass  # TODO 1: replace with the fields described above


mcp = MCPServer(
    name="cafe-mcp",
    version="0.6.0",
    instructions=(
        # TODO 2: mention list_drinks's paging behaviour. Say what next_cursor
        # means and warn against the mistake this topic is built around: a short
        # page does NOT by itself mean the menu is exhausted.
        "..."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


# TODO 3: Write list_drinks(cursor=None, limit=PAGE_SIZE) -> DrinkPage.
#
#   Use pagination.page(items, cursor, limit) — it does the slicing and the
#   cursor decoding. Your job is the WIRING:
#
#   (a) `limit` should be schema-constrained (Field(ge=..., le=...)) — pick sane
#       bounds. Why does this belong in the schema rather than a runtime check?
#       You answered this exact question in topic 03.
#
#   (b) Catch `pagination.CursorError` and convert it to `ToolError`. This is the
#       part worth thinking about: a bad SLUG has an obvious recovery ("try a real
#       one from list_drinks"). A bad CURSOR does not — it is opaque, so a model
#       cannot reason its way to a valid one. What is the ONLY thing your message
#       can honestly tell the model to do?
@mcp.tool(
    annotations=ToolAnnotations(
        title="List the drinks",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def list_drinks(cursor: str | None = None, limit: int = PAGE_SIZE) -> "DrinkPage":
    """TODO: write this for a model to read. Explain the paging contract."""
    print(f"  [server] list_drinks(cursor={cursor!r}, limit={limit})", file=sys.stderr)
    ...  # replace


# --- Health ---
# TODO 4: @mcp.custom_route("/healthz", methods=["GET"]) again. You know this one.
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "06"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 06 — pagination (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
