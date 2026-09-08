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


@function_tool
def record_event(entry: str) -> dict:
    """Add a new travel event to the journal."""
    _journal.append(entry)
    print(f"Event recorded: {entry}")
    return {"status": "recorded", "entry": entry}


@function_tool
def load_journal() -> dict:
    """Load the current travel journal entries."""
    print("Loading journal entries...")
    return {"status": "loaded", "journal": "\n".join(_journal)}


agent = Agent(
    name="Time Tracker Agent",
    instructions="""You are a time tracking journaling agent.
Always use the 'load_journal' tool at the start to get past entries.
For a new event, call 'record_event' to save it.
If asked for a summary or to show the journal, output all recorded events.""",
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    tools=[record_event, load_journal],
)

# Simulate a series of historical travel events
travel_events = [
    "Traveled to Ancient Rome and watched a gladiator fight",
    "Visited the signing of the Declaration of Independence in 1776",
    "Witnessed the moon landing in 1969",
]


async def main():
    print("Recording travels:")
    for event in travel_events:
        await Runner.run(agent, event)
    # Ask the agent to summarize the adventures
    result = await Runner.run(agent, "Show my travel history")
    print("\nFinal Journal:")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
