# ============================================================
# LISTING: 02_mcp_agent_stdio_server.py  (reference implementation)
# BUILDING: An agent that reaches a local MCP server over STDIO.
# REF: Chapter 3, §3.3.1 "Local MCP servers over STDIO"
# PROVIDERS: gemini (default) or ollama — see switch below
# UPDATED FOR: MCP 2026-07-28 (stateless)
# ============================================================
#
# `agents.mcp.MCPServerStdio` spawns `01_claude_mcp_server.py` as a
# subprocess (`mcp run <script>`) and talks to it over stdin/stdout. Nothing
# about that call changes for 2026-07-28 — verified directly against the
# installed SDK: `MCPServerStdio` connects through `mcp.Client(transport,
# mode="auto", ...)` internally (openai-agents 0.22.0, mcp 2.1.1), and
# `mode="auto"` is exactly what lets ONE client class speak either the
# pre-2026 handshake or the modern, session-less dialect — it tries
# `server/discover` first and adapts to whatever the server on the other
# end actually understands. You do not have to pick a mode yourself; it
# negotiates protocol version PER CONNECTION, every time.
#
# The book's original agent had no `model=` at all, which defaults to
# needing a real `OPENAI_API_KEY`. This repo's convention (see
# code/ch02/solutions) is Gemini by default, Ollama as a local fallback —
# both speak the OpenAI-compatible chat completions API, so only the
# `client`/`MODEL_NAME` setup changes, never the `Agent`/`Runner` calls.

import asyncio
import os
from pathlib import Path

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStdio, MCPServerStdioParams
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

SCRIPT = Path(__file__).with_name("01_claude_mcp_server.py").resolve()

# --- Your turn ---
# Write an async main() that:
#   1. Opens `MCPServerStdio(name="Research Tools", params=
#      MCPServerStdioParams(command="mcp", args=["run", str(SCRIPT)]))` as
#      an async context manager.
#   2. Builds an Agent named "Assistant" using `client`/`MODEL_NAME` above,
#      instructed to use the research tools to perform research, with the
#      opened server passed in `mcp_servers=[...]`.
#   3. Runs the agent on "Get the available research sources" via
#      `Runner.run(agent, ...)` and prints `result.final_output`.
#   4. Close with `if __name__ == "__main__": asyncio.run(main())`.
