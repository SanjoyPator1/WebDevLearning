# ============================================================
# LISTING: 06_mcp_time_travel_tracker.py  (reference implementation)
# BUILDING: The SAME journal tools as 05_time_travel_agent.py, now served
#           over MCP instead of `@function_tool`.
# REF: Chapter 3, §3.4.1 "Converting tools to an MCP server"
# UPDATED FOR: MCP 2026-07-28 (stateless)
# ============================================================
#
# The book's original file called `mcp.run(transport="sse")` — the obsolete
# transport (see 03_mcp_agent_sse_server.py's header for the full
# explanation). This file follows 01_claude_mcp_server.py's exact pattern:
# ONE server, launchable either way, decided at `__main__` time (which
# `mcp run` never reaches — see that file's header comment for why):
#   - 06_time_travel_agent_mcp_stdio.py launches this via
#     `mcp run <this file>` (STDIO).
#   - 06_time_travel_agent_mcp_sse.py expects you to run this file
#     DIRECTLY with `MCP_TRANSPORT=streamable-http`, over HTTP instead.

import os
import sys

from mcp.server import MCPServer

mcp = MCPServer("Time Travel Tracker")

# In-memory journal state (list of entries)
_journal = []

# --- Your turn (1/2): record_event ---
# Write a tool `record_event(entry: str) -> dict` that appends `entry` to
# `_journal` and returns `{"status": "recorded", "entry": entry}`. Narrate
# it with `print(..., file=sys.stderr)` — NOT plain `print(...)`. This
# server is reached over STDIO by 06_time_travel_agent_mcp_stdio.py, and
# stdout IS the protocol channel there; a plain print corrupts it (the same
# gotcha 01_complete_mcp_server.py's template calls out).
@mcp.tool()
def record_event(entry: str) -> dict:
    """Add a new travel event to the journal."""
    _journal.append(entry)
    # STDOUT IS THE STDIO SERVER'S OWN PROTOCOL CHANNEL — see
    # 01_complete_mcp_server.py's header for the same gotcha, reproduced and
    # confirmed there. `file=sys.stderr` keeps the narration without
    # corrupting the transport this tool is reached over via
    # 06_time_travel_agent_mcp_stdio.py.
    print(f"Event recorded: {entry}", file=sys.stderr)
    return {"status": "recorded", "entry": entry}

# --- Your turn (2/2): load_journal ---
# Write a tool `load_journal() -> dict` that returns
# `{"status": "loaded", "journal": "\n".join(_journal)}`. Same stderr rule.
@mcp.tool()
def load_journal() -> dict:
    """Load the current travel journal entries."""
    print("Loading journal entries...", file=sys.stderr)
    return {"status": "loaded", "journal": "\n".join(_journal)}


if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "streamable-http":
        print("Time Travel Tracker server — Streamable HTTP, stateless, on :8000")
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8000,
            stateless_http=True,
        )
    else:
        mcp.run(transport="stdio")
