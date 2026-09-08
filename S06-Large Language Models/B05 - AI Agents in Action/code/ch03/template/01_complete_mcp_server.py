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


# --- Your turn (1/3): the resource ---
# Write a resource bound to the TEMPLATE URI `greeting://{name}` — a
# function taking `name: str` and returning a personalized greeting
# string, e.g. f"Greetings, {name}! (from resource)". Narrate it with
# `print(..., file=sys.stderr)`, NEVER a plain `print(...)` — this server is
# reached over STDIO, and stdout IS the protocol channel. Verified directly
# while building the solved version: a plain `print()` here corrupts the
# JSON-RPC stream with "Failed to parse JSONRPC message from server" the
# moment the resource is read. Call `log(...)` too, same message.


# --- Your turn (2/3): the tool ---
# Write a tool `add(a: int, b: int) -> int` that returns the sum. Log it
# with `log(...)` (not `print`, for the same reason as above).


# --- Your turn (3/3): the prompt ---
# Write a prompt `welcome(name: str) -> str` that calls your resource
# function DIRECTLY as a plain Python call (not through the protocol — a
# prompt handler can reuse a resource's logic because both are just
# functions in this same process) and appends
# " How can I assist you today?" to the greeting it gets back. Log it too.


if __name__ == "__main__":
    # `mcp run` (used by 01_complete_agent.py) never reaches this block —
    # see 01_claude_mcp_server.py's header comment for why. This is here
    # only so `python 01_complete_mcp_server.py` also works, for poking at
    # the server directly.
    mcp.run(transport="stdio")
