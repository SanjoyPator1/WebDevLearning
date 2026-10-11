# Problem 07 -- a catalog too big for one answer. search_books hands out
# pages with an opaque cursor, and the tool list itself is cacheable.

import base64
import json
import random

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

mcp = MCPServer(
    "Bookstore",
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)

PAGE_SIZE = 10
GENRES = ["sci-fi", "mystery", "romance", "history", "fantasy"]

random.seed(42)
BOOKS = [
    {
        "title": f"Book {i:03d}",
        "genre": GENRES[i % len(GENRES)],
        "pages": random.randint(120, 500),
    }
    for i in range(200)
]


class Book(BaseModel):
    title: str
    pages: int


class BookPage(BaseModel):
    books: list[Book]
    next_cursor: str | None


def _encode_cursor(genre: str, offset: int) -> str:
    raw = json.dumps({"genre": genre, "offset": offset}).encode()
    return base64.urlsafe_b64encode(raw).decode()


def _decode_cursor(cursor: str) -> dict:
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except Exception as error:
        raise ToolError(
            f"that cursor is not valid for this server ({error}). cursors are "
            "opaque and must be copied exactly from a previous next_cursor -- "
            "call search_books again with no cursor to start from the beginning"
        ) from None


@mcp.tool()
def search_books(genre: str, cursor: str | None = None) -> BookPage:
    """Search books by genre, 10 at a time.

    Returns up to 10 books plus a next_cursor. If next_cursor is not null,
    call this tool again with cursor set to that exact value to see more.
    Never make up a cursor -- copy it from next_cursor. Stop only when
    next_cursor is null, not just because a page had fewer than 10 books.
    """
    if cursor is not None:
        state = _decode_cursor(cursor)
        if state["genre"] != genre:
            raise ToolError("this cursor was issued for a different genre -- start again with no cursor")
        offset = state["offset"]
    else:
        offset = 0

    matches = [b for b in BOOKS if b["genre"] == genre]
    chunk = matches[offset : offset + PAGE_SIZE]
    new_offset = offset + PAGE_SIZE
    next_cursor = _encode_cursor(genre, new_offset) if new_offset < len(matches) else None

    return BookPage(books=[Book(**b) for b in chunk], next_cursor=next_cursor)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8007, stateless_http=True)
