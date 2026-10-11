# Problem 01 -- the smallest MCP server.

import sys

from mcp.server import MCPServer

mcp = MCPServer("Research Tools")


@mcp.tool()
def get_research_sources() -> list[str]:
    """Return the list of research sources this server knows about."""
    # your turn: return ["Wikipedia", "Google", "YouTube"]
    print("get_research_sources tool called : ",file=sys.stderr)
    return ["Wikipedia", "Google", "YouTube"]


@mcp.tool()
def count_words(text: str) -> int:
    """Count the words in a piece of text, splitting on whitespace."""
    # your turn: count the words in text
    print(f"count_words called with: {text!r}", file=sys.stderr)
    return len(text.split())

if __name__ == "__main__":
    mcp.run()
