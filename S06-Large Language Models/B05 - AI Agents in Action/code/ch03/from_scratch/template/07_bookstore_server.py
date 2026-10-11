# Problem 07 -- a catalog too big for one answer. search_books hands out
# pages with an opaque cursor.

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
    # your turn: json + base64 encode {"genre": genre, "offset": offset}
    raise NotImplementedError


def _decode_cursor(cursor: str) -> dict:
    # your turn: base64 decode + json parse, raise ToolError on bad input
    raise NotImplementedError


@mcp.tool()
def search_books(genre: str, cursor: str | None = None) -> BookPage:
    """Search books by genre, 10 at a time.

    Returns up to 10 books plus a next_cursor. If next_cursor is not null,
    call this tool again with cursor set to that exact value to see more.
    Never make up a cursor -- copy it from next_cursor.
    """
    # your turn: decode the cursor if given (checking the genre matches),
    # else start at offset 0; slice PAGE_SIZE books; build the next cursor
    # only if there is more left
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8007, stateless_http=True)
