# ============================================================
# LISTING: 06_time_travel_agent_mcp_sse.py  (reference implementation)
# BUILDING: The journaling agent from 05_time_travel_agent.py, now talking
#           to 06_mcp_time_travel_tracker.py over HTTP instead of calling
#           `@function_tool`s in-process.
# REF: Chapter 3, §3.4.2 "Consuming MCP servers locally or remotely"
# PROVIDERS: gemini (default) or ollama — see switch below
# UPDATED FOR: MCP 2026-07-28 (stateless) — see 03_mcp_agent_sse_server.py
#              for the full explanation of why MCPServerSse is gone.
# ============================================================
#
# HOW TO RUN THIS ONE (two terminals — see 03_mcp_agent_sse_server.py for
# why a real HTTP server isn't spawned as a subprocess the way STDIO is):
#   Terminal 1:  MCP_TRANSPORT=streamable-http python 06_mcp_time_travel_tracker.py
#   Terminal 2:  python 06_time_travel_agent_mcp_sse.py

# agent.py
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

# Simulate a series of historical travel events
travel_events = [
    "Traveled to Ancient Rome and watched a gladiator fight",
    "Visited the signing of the Declaration of Independence in 1776",
    "Witnessed the moon landing in 1969",
]


async def main():
    async with MCPServerStreamableHttp(
        name="Time Tracker Server",
        params={
            "url": "http://127.0.0.1:8000/mcp",
        },
    ) as time_tracker_server:
        agent = Agent(
            name="Assistant",
            instructions="""
You are a time-travel journaling agent.
Always use the 'load_journal' tool at the start to get past entries.
For a new event, call 'record_event' to save it.
If asked for a summary or to show the journal, output all recorded events.
            """,
            model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
            mcp_servers=[time_tracker_server],
        )
        print("Recording travels:")
        for event in travel_events:
            await Runner.run(agent, event)
        # Ask the agent to summarize the adventures
        result = await Runner.run(agent, "Show my travel history")
        print("\nFinal Journal:")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
