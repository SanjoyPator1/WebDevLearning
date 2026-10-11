# Problem 03 -- nothing new here, one tool plus a cache hint. The real
# exercise is the client, which speaks raw HTTP instead of using Client.

from mcp.server import CacheHint, MCPServer

mcp = MCPServer(
    "Wire Demo",
    cache_hints={"tools/list": CacheHint(ttl_ms=60_000, scope="public")},
)


@mcp.tool()
def echo(text: str) -> str:
    """Return the same text back, unchanged."""
    # your turn
    return text


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, stateless_http=True)
