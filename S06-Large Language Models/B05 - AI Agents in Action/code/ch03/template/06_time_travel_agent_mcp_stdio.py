# ============================================================
# LISTING: 06_time_travel_agent_mcp_stdio.py  (reference implementation)
# BUILDING: The same journaling agent as 06_time_travel_agent_mcp_sse.py,
#           reaching 06_mcp_time_travel_tracker.py over STDIO instead.
# REF: Chapter 3, §3.4.2 "Consuming MCP servers locally or remotely"
# PROVIDERS: gemini (default) or ollama — see switch below
# UPDATED FOR: MCP 2026-07-28 (stateless)
# ============================================================
#
# Compare this file to 06_time_travel_agent_mcp_sse.py: same agent, same
# instructions, same simulated events — the ONLY difference is which
# `agents.mcp.MCPServer*` class reaches the tracker, because
# 06_mcp_time_travel_tracker.py itself does not care which transport
# delivers a given `tools/call` any more than 01_claude_mcp_server.py did.

# agent.py
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

SCRIPT = Path(__file__).with_name("06_mcp_time_travel_tracker.py").resolve()

# Simulate a series of historical travel events
travel_events = [
    "Traveled to Ancient Rome and watched a gladiator fight",
    "Visited the signing of the Declaration of Independence in 1776",
    "Witnessed the moon landing in 1969",
]

# --- Your turn ---
# Write an async main() that:
#   1. Opens `MCPServerStdio(name="Time Tracker Server", params=
#      MCPServerStdioParams(command="mcp", args=["run", str(SCRIPT)]))` as
#      an async context manager.
#   2. Builds an Agent named "Assistant" using `client`/`MODEL_NAME` above,
#      with the SAME instructions as 06_time_travel_agent_mcp_sse.py's
#      agent. Pass the opened server in `mcp_servers=[...]`.
#   3. Runs the agent once per entry in `travel_events`, then once more on
#      "Show my travel history", and prints `result.final_output`.
#   4. Close with `if __name__ == "__main__": asyncio.run(main())`.
