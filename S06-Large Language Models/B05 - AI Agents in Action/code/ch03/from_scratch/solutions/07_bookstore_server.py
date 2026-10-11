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


# TIPS:
# 1. for this problem mainly check how you can create pagination and send it over to client
# 2. this pattern of converting bytes to string and string to bytes and whatnot check those


def _encode_cursor(genre: str, offset: int) -> str:
    # your turn: json + base64 encode {"genre": genre, "offset": offset}
    # 1. json to string using json.dumps(json_obj)
    # 2. .encode convert it into bytes
    raw = json.dumps({
        "genre" : genre,
        "offset" : offset
    }).encode()

    # 3. urlsafe_b64encode returns base64 encoded bytes
    # 4. .decode turns it into string as this will be sent in a json key cursor
    # so it goes from str → bytes → bytes → str
    return base64.urlsafe_b64encode(raw).decode()


def _decode_cursor(cursor: str) -> dict:
    # your turn: base64 decode + json parse, raise ToolError on bad input
    try:
        # 1. cursor is string in json so we use encode on cursor to convert it into bytes 
        #    as urlsafe_b64decode takes bytes
        # 2. base64.urlsafe_b64decode decodes the base64 bytes back into the original bytes
        # 3. json.loads parses that directly into a dict
        # 4. no decode at the end as json.loads takes bytes
        return json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except Exception as error:
        # the error will be given back to the llm for understanding what went wrong and how to fix it
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
    Never make up a cursor -- copy it from next_cursor.
    """
    # your turn: decode the cursor if given (checking the genre matches),
    # else start at offset 0; slice PAGE_SIZE books; build the next cursor
    # only if there is more left
    if cursor is not None:
        state = _decode_cursor(cursor)
        if state["genre"] != genre:
            raise ToolError("this cursor was issued for a different genre -- start again with no cursor")
        offset = state["offset"]
    else:
        offset = 0

    matches = [book for book in BOOKS if book["genre"] == genre]
    chunk = matches[offset: offset + PAGE_SIZE]
    new_offset = offset + PAGE_SIZE
    next_cursor = _encode_cursor(genre, new_offset) if new_offset < len(matches) else None

    return BookPage(books=[Book(**book) for book in chunk], next_cursor=next_cursor)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8007, stateless_http=True)
