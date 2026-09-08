# ============================================================
# LISTING: 01_complete_mcp_server.py  (reference implementation)
# BUILDING: "DemoServer" — all three primitives in one file: a resource,
#           a tool, and a prompt that reuses the resource.
# REF: Chapter 3, §3.1.3 "Core components: tools, resources, and prompts"
# UPDATED FOR: MCP 2026-07-28 (stateless)
# ============================================================
#
# `FastMCP` -> `MCPServer`, same as 01_claude_mcp_server.py. Everything else
# about defining a resource, a tool, and a prompt is unchanged: a resource
# is still a function bound to a URI (here, a TEMPLATE URI —
# `greeting://{name}` — because it has a `{placeholder}`), a tool is still a
# plain function the model can call, and a prompt is still a function that
# returns text meant to steer the model.
#
# This server is used only over STDIO (by 01_complete_agent.py, via
# `mcp run`), so there is no dual-transport `__main__` block here the way
# 01_claude_mcp_server.py has one — that split is 01_claude_mcp_server.py's
# own teaching point, not repeated here.

# server.py
import sys

from mcp.server import MCPServer

# Initialize an MCP server with a name
mcp = MCPServer("DemoServer")


def log(output: str, file_name: str = "server_output.log"):
    """Log output to a file"""
    with open(file_name, "a") as log_file:
        log_file.write(output + "\n")


# Define a resource: greeting://{name}
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Return a personalized greeting for the given name"""
    # STDOUT IS THE STDIO SERVER'S OWN PROTOCOL CHANNEL. The book's original
    # code printed here with a plain `print(...)`, which writes to stdout —
    # verified directly: it corrupts the JSON-RPC stream the moment this
    # resource is read over stdio ("Failed to parse JSONRPC message from
    # server", the exact gotcha this project's own README warns about for
    # this chapter). `file=sys.stderr` keeps the narration without breaking
    # the transport.
    print(f"Received request for greeting: {name}", file=sys.stderr)
    log(f"Received request for greeting: {name}")
    return f"Greetings, {name}! (from resource)"


# Define a tool: add(a, b)
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return the sum"""
    log(f"Adding {a} and {b}")
    return a + b


# Define a prompt template: welcome(name)
@mcp.prompt()
def welcome(name: str) -> str:
    """Generate a welcome message using the greeting resource"""
    # Incorporate the greeting resource into a prompt message. This calls
    # `get_greeting` as a PLAIN PYTHON FUNCTION, not through the protocol —
    # a prompt handler can reuse a resource's logic directly because they
    # are both just functions in this same process. A client, by contrast,
    # can only reach either one through its own RPC (`prompts/get` vs
    # `resources/read`) — it has no such shortcut.
    greeting_text = get_greeting(name)  # e.g., "Greetings, Alice! (from resource)"
    log(f"Creating welcome message for: {name}")
    return f"{greeting_text} How can I assist you today?"


if __name__ == "__main__":
    # `mcp run` (used by 01_complete_agent.py) never reaches this block —
    # see 01_claude_mcp_server.py's header comment for why. This is here
    # only so `python 01_complete_mcp_server.py` also works, for poking at
    # the server directly.
    mcp.run(transport="stdio")
