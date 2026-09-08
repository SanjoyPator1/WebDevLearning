# ============================================================
# LISTING: 05_time_travel_agent.py  (reference implementation)
# BUILDING: A journaling agent, using PLAIN @function_tool — no MCP yet.
# REF: Chapter 3, §3.4.1 "Converting tools to an MCP server" (the "before")
# PROVIDERS: gemini (default) or ollama — see switch below
# ============================================================
#
# This file does not touch MCP at all — it is the book's deliberate "before"
# picture. The next two files (06_mcp_time_travel_tracker.py +
# 06_time_travel_agent_mcp_sse.py / 06_time_travel_agent_mcp_stdio.py) take
# these EXACT same two functions and expose them through an MCP server
# instead, so you can compare `@function_tool` (in-process, same Python
# object) against `@mcp.tool()` (out-of-process, reached over the wire) side
# by side. Only the model wiring changed from the book here.

import asyncio
import os

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
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

# In-memory journal state (list of entries)
_journal = []

# --- Your turn (1/3): the tools ---
# Write `record_event(entry: str) -> dict`, decorated with `@function_tool`,
# that appends `entry` to `_journal`, prints "Event recorded: {entry}", and
# returns `{"status": "recorded", "entry": entry}`.
#
# Write `load_journal() -> dict`, also `@function_tool`, that prints
# "Loading journal entries...", and returns `{"status": "loaded",
# "journal": "\n".join(_journal)}`.


# --- Your turn (2/3): the agent ---
# Build an `Agent` named "Time Tracker Agent" using `client`/`MODEL_NAME`
# above, with instructions telling it to ALWAYS call `load_journal` first,
# to call `record_event` for a new event, and to output every recorded
# event when asked for a summary. Pass both tools in `tools=[...]`.

# Simulate a series of historical travel events
travel_events = [
    "Traveled to Ancient Rome and watched a gladiator fight",
    "Visited the signing of the Declaration of Independence in 1776",
    "Witnessed the moon landing in 1969",
]

# --- Your turn (3/3): main() ---
# Write an async main() that runs the agent once per entry in
# `travel_events` (via `Runner.run(agent, event)`), then runs it once more
# on "Show my travel history" and prints `result.final_output`. Close with
# `if __name__ == "__main__": asyncio.run(main())`.
