# Problem 01 -- the smallest MCP server.
# Two tools, no resources, no prompts. Everything the decorator needs comes
# from the function itself: its name, its docstring, its signature, its
# return type.

import sys

from mcp.server import MCPServer

mcp = MCPServer("Research Tools")


@mcp.tool()
def get_research_sources() -> list[str]:
    """Return the list of research sources this server knows about."""
    print("get_research_sources called", file=sys.stderr)
    return ["Wikipedia", "Google", "YouTube"]


@mcp.tool()
def count_words(text: str) -> int:
    """Count the words in a piece of text, splitting on whitespace."""
    print(f"count_words called with: {text!r}", file=sys.stderr)
    return len(text.split())


if __name__ == "__main__":
    # defaults to stdio -- a client starts this file as a subprocess and
    # talks to it over stdin/stdout
    mcp.run()
