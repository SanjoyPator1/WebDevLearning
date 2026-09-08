# ============================================================
# LISTING: 03_mcp_agent_sse_server.py  (reference implementation)
# BUILDING: An agent that reaches a local MCP server over HTTP.
# REF: Chapter 3, §3.3.2 "Local MCP servers over SSE"
# PROVIDERS: gemini (default) or ollama — see switch below
# UPDATED FOR: MCP 2026-07-28 (stateless) — see the transport note below
# ============================================================
#
# THE BIGGEST CHANGE IN THIS CHAPTER. The book's original file used
# `agents.mcp.MCPServerSse`, connecting to `http://localhost:8000/sse` — the
# SSE-only transport from the ORIGINAL 2024-11-05 spec. That transport was
# already replaced in the 2025-03-26 revision by "Streamable HTTP" (one
# `/mcp` endpoint, a single POST per request, SSE used only when a response
# genuinely needs to stream), and 2026-07-28 goes further still: no
# `initialize`/`initialized` handshake and no `Mcp-Session-Id` pinning a
# client to one server process AT ALL. `MCPServerSse` still exists in the
# installed `agents` package for talking to old servers, but it has nothing
# to do with how a 2026-07-28 server actually works — using it here would
# silently teach the wrong transport.
#
# The replacement is `agents.mcp.MCPServerStreamableHttp`, pointed at the
# `/mcp` path (not `/sse`) that `01_claude_mcp_server.py` serves when you run
# it directly with `MCP_TRANSPORT=streamable-http`. Verified directly: this
# class also connects through `mcp.Client(transport, mode="auto", ...)`
# internally, so it needs no special stateless-aware configuration on the
# CLIENT side at all — the negotiation happens automatically, the same as
# the STDIO agents in this chapter.
#
# HOW TO RUN THIS ONE (two terminals, because nothing here spawns the server
# for you — a real HTTP server is a separate long-lived process, not a
# subprocess this script owns the lifetime of):
#   Terminal 1:  MCP_TRANSPORT=streamable-http python 01_claude_mcp_server.py
#   Terminal 2:  python 03_mcp_agent_sse_server.py

import asyncio
import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStreamableHttp
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
set_tracing_disabled(True)  # no real OpenAI key -> no trace export attempts

PROVIDER = "gemini"  # "gemini" or "ollama"

if PROVIDER == "gemini":
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    MODEL_NAME = os.environ["GEMINI_MODEL"]
elif PROVIDER == "ollama":
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL_NAME = "qwen3:8b"  # swap for whatever tag `ollama list` shows you
else:
    raise ValueError(f"unknown PROVIDER: {PROVIDER!r}")

# --- Your turn ---
# Write an async main() that:
#   1. Opens `MCPServerStreamableHttp(name="Streamable HTTP Python Server",
#      params={"url": "http://127.0.0.1:8000/mcp"})` as an async context
#      manager. NOT `MCPServerSse` and NOT `/sse` — that transport is gone.
#   2. Builds an Agent named "Assistant" using `client`/`MODEL_NAME` above,
#      instructed to use the research tools to perform research, with the
#      opened server passed in `mcp_servers=[...]`.
#   3. Runs the agent on "Get the available research sources" via
#      `Runner.run(agent, ...)` and prints `result.final_output`.
#   4. Close with `if __name__ == "__main__": asyncio.run(main())`.
