# ============================================================
# LISTING: 04_mcp_agent_local_server_files.py  (reference implementation)
# BUILDING: An agent that reaches a THIRD-PARTY MCP server —
#           `@modelcontextprotocol/server-filesystem`, via npx.
# REF: Chapter 3, §3.3.3 "Connecting to the standard MCP servers"
# PROVIDERS: gemini (default) or ollama — see switch below
# REQUIRES: Node.js + npx on PATH (see Appendix B) and network access the
#           first time, to fetch the package.
# UPDATED FOR: MCP 2026-07-28 (stateless)
# ============================================================
#
# This file is different from every other one in this chapter: the server
# is code you did not write and cannot change. You do not control, and do
# not need to know, which protocol era `@modelcontextprotocol/server-
# filesystem` actually speaks — that is the entire point of `mode="auto"`
# on the client side (verified in every other file in this chapter):
# whatever version that package negotiates, `MCPServerStdio` adapts to it
# automatically. The only thing this file needed updated from the book was
# the model wiring — the MCP connection code is untouched, on purpose.

import asyncio
import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStdio
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


async def main():
    # Define path to your sample files
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Use async context manager to initialize the server
    async with MCPServerStdio(
        name="Filesystem Server, via npx",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", current_dir],
        },
    ) as server:
        # Create an agent that uses the MCP server
        agent = Agent(
            name="Filesystem Agent",
            instructions="Use the filesystem tools to help the user with their tasks.",
            model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
            mcp_servers=[server],
        )

        print("Running: Get the available files")
        result = await Runner.run(agent, "List all file names in the current directory")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
