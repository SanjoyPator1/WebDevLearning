# ============================================================
# TOPIC: 06 — pagination: the opaque cursor
# REF:   notes/06-pagination.md
# RUN:   python solved/t06_pagination.py
# ============================================================
#
# This opens Part 3, and answers the question topic 00 raised and left hanging:
#
#   If sessions are gone, and a server needs to remember something across two
#   calls, where does it live?
#
# In an ARGUMENT. Here, the "something" is only a position in a list — the
# gentlest version of the idea, deliberately, before topic 07 makes it a shopping
# cart and topic 08 makes it a half-finished request. Same shape all three times:
# the server mints an opaque token, hands it back, and any instance that later
# receives that token can pick up exactly where the last one left off.
#
# `cafe_mcp/pagination.py` is the mechanism (given complete, and covered by its
# own tests). This file is the wiring: one tool, one failure path.

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


class DrinkPage(BaseModel):
    """One page of the menu."""

    drinks: list[menu.Drink]
    next_cursor: str | None = Field(
        description=(
            "Pass this back as `cursor` to get the next page. Absent or null means "
            "this was the last page — do not construct a cursor yourself, and do "
            "not assume the list is exhausted just because this page was short."
        )
    )


mcp = MCPServer(
    name="cafe-mcp",
    version="0.6.0",
    instructions=(
        "You are working the counter of a small coffee shop.\n\n"
        f"`list_drinks` returns {PAGE_SIZE} drinks at a time. If `next_cursor` is "
        "present in the result, call `list_drinks` again with that exact value as "
        "`cursor` to see more — never edit or guess a cursor, and never assume the "
        "menu is exhausted just because a page had fewer than "
        f"{PAGE_SIZE} drinks; check `next_cursor` instead."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="List the drinks",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def list_drinks(
    cursor: Annotated[
        str | None,
        Field(
            description=(
                "Opaque token from a previous call's `next_cursor`. Omit it (or pass "
                "null) to get the first page. Treat it as a black box — copy it "
                "back exactly, never construct or edit one yourself."
            )
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(ge=1, le=10, description=f"Page size. Defaults to {PAGE_SIZE}."),
    ] = PAGE_SIZE,
) -> DrinkPage:
    """List drinks, one page at a time.

    Call this with no arguments to see the first page. If the result's
    `next_cursor` is not null, call again with `cursor` set to that exact value to
    see more. Stop when `next_cursor` is null — that is the only reliable signal
    that you have seen everything; a short page does not by itself mean the list
    is exhausted.
    """
    print(f"  [server] list_drinks(cursor={cursor!r}, limit={limit})", file=sys.stderr)

    try:
        chunk, next_cursor = pagination.page(list(menu.all_drinks()), cursor, limit)
    except pagination.CursorError as exc:
        # --- THE FAILURE PATH, AND WHY THE MESSAGE MATTERS MORE THAN USUAL ---
        #
        # A cursor is opaque, so a model that gets one wrong has no way to guess a
        # correct one by reasoning about it — unlike a bad slug, where "try a real
        # one from list_drinks" is an obvious next step. The only correct recovery
        # is "start over with no cursor at all", so the message says exactly that,
        # not just "invalid cursor".
        raise ToolError(
            f"That cursor is not valid for this server ({exc}). Cursors are opaque "
            f"and must be copied exactly from a previous `next_cursor` — call "
            f"`list_drinks` again with no `cursor` argument to start from the "
            f"beginning."
        ) from None

    print(f"  [server]   -> {len(chunk)} drinks, next_cursor={next_cursor!r}", file=sys.stderr)
    return DrinkPage(drinks=chunk, next_cursor=next_cursor)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "06"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 06 — pagination: the opaque cursor")
    print("-" * 68)
    print(f"  endpoint  : http://{HOST}:{PORT}/mcp")
    print(f"  page size : {PAGE_SIZE} (12 drinks -> 3 pages)")
    print("-" * 68)
    print("  Try, IN ORDER:")
    print("    bash curl/06_list_page1.sh")
    print("    bash curl/06_list_next.sh <cursor from above>")
    print("    bash curl/06_walk_all_pages.sh     <- walks the whole menu for you")
    print("    bash curl/06_decode_cursor.sh <cursor>   <- base64 -d it yourself")
    print("    bash curl/06_bad_cursor.sh")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
