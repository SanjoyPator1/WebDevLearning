# ============================================================
# LISTING: 01_claude_mcp_server.py  (reference implementation)
# BUILDING: The minimal possible MCP server — "Research Tools", one tool.
# REF: Chapter 3, §3.2.1 "Coding up an MCP server for Claude"
# UPDATED FOR: MCP 2026-07-28 (stateless) — see notes at the bottom of this file
# ============================================================
#
# The book's original file used `from mcp.server.fastmcp import FastMCP`.
# `FastMCP` was renamed to `MCPServer` when the SDK moved to its v2 line —
# `mcp.server.fastmcp` no longer exists at all in the installed package
# (verified: importing it raises `ModuleNotFoundError`, with the SDK's own
# error message pointing at the migration guide). Everything else about
# defining a tool is identical: `@mcp.tool()` on a plain function, a
# docstring the model reads, a return type it validates against.
#
# This same file is used TWO different ways later in this chapter:
#   - 02_mcp_agent_stdio_server.py spawns it via `mcp run <this file>`,
#     talking to it over STDIO (transport picked by the CLI, defaults to
#     stdio).
#   - 03_mcp_agent_sse_server.py expects you to run this file DIRECTLY
#     (`python 01_claude_mcp_server.py`), which starts it over Streamable
#     HTTP instead — the `__main__` block below picks the transport.
#
# Both work against the SAME server object because `mcp run` never executes
# this file's `__main__` block at all — it imports the module, finds the
# `mcp` variable, and calls `.run()` on it directly. The `if __name__ ==
# "__main__":` guard below only fires when you run this file yourself.

import os

from mcp.server import MCPServer

# Create an MCP server
mcp = MCPServer("Research Tools")

# --- Your turn ---
# Write a tool called `get_research_sources` that takes no arguments and
# returns a `list[str]` of research source names — for example Wikipedia,
# Google, YouTube. Give it a one-line docstring; that becomes the
# description a model reads in `tools/list`.
@mcp.tool()
def get_research_sources() -> list[str]:
    """Provides a list of research sources"""
    search_sources = [
        "Wikipedia",
        "Google",
        "YouTube",
    ]
    return search_sources

if __name__ == "__main__":
    # `mcp run` (used by 02_mcp_agent_stdio_server.py) never reaches this
    # block — it imports this module and calls `mcp.run()` itself. This
    # branch exists so you can ALSO run `python 01_claude_mcp_server.py`
    # directly (used by 03_mcp_agent_sse_server.py) and get a real,
    # stateless Streamable HTTP server instead.
    if os.environ.get("MCP_TRANSPORT") == "streamable-http":
        print("Research Tools server — Streamable HTTP, stateless, on :8000")
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8000,
            stateless_http=True,
        )
    else:
        mcp.run(transport="stdio")

# ------------------------------------------------------------------
# What changed from the book, and why:
#
# 1. `FastMCP` -> `MCPServer`. Same class, renamed at the mcp v2 line.
# 2. Nothing about `@mcp.tool()` itself changed — a tool is still just a
#    Python function with a docstring and a return type.
# 3. `stateless_http=True` is the whole point of the 2026-07-28 revision:
#    no `initialize`/`initialized` handshake, no `Mcp-Session-Id` cookie
#    pinning a client to one server process. It defaults to False (for
#    backward compatibility with pre-2026 clients), so it must be opted
#    into explicitly — this file does that for you.
# ------------------------------------------------------------------
