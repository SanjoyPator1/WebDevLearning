# ============================================================
# LISTING: 01_complete_agent.py  (reference implementation)
# BUILDING: An agent that reaches "DemoServer" (tool + resource + prompt)
#           over STDIO.
# REF: Chapter 3, §3.3.1 "Local MCP servers over STDIO"
# PROVIDERS: gemini (default) or ollama — see switch below
# UPDATED FOR: MCP 2026-07-28 (stateless)
# ============================================================
#
# Same modernization as 02_mcp_agent_stdio_server.py: `MCPServerStdio`
# already speaks 2026-07-28 correctly (verified there), so the only change
# from the book is the model wiring — Gemini by default instead of an
# implicit OpenAI key.

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

SCRIPT = Path(__file__).with_name("01_complete_mcp_server.py").resolve()


async def main():
    async with MCPServerStdio(
        name="MCP Server",
        params=MCPServerStdioParams(
            command="mcp",
            args=["run", str(SCRIPT)],
        ),
    ) as mcp_server:
        agent = Agent(
            name="Assistant",
            instructions=(
                "You are a helpful assistant. "
                "Use the available tools and resources to answer the user's question. "
                "For math calculations, **always** use the add tool. "
                "For greeting the user by name, use the greeting resource or prompt from the mcp server."
            ),
            model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
            mcp_servers=[mcp_server],
        )

        result = await Runner.run(agent, "Hello, my name is Alice. What is 5 + 7?")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
