# Problem 03 -- the server side is nothing new, just one tool plus a cache
# hint. The real exercise is in the client, which speaks to this over raw
# HTTP instead of through the library's Client class.

from mcp.server import CacheHint, MCPServer

mcp = MCPServer(
    "Wire Demo",
    cache_hints={"tools/list": CacheHint(ttl_ms=60_000, scope="public")},
)


@mcp.tool()
def echo(text: str) -> str:
    """Return the same text back, unchanged."""
    return text


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, stateless_http=True)
