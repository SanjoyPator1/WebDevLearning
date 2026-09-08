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

model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)

# --- Your turn ---

SERVER_FILE = Path(__file__).with_name("01_complete_mcp_server.py")

async def main():
    async with MCPServerStdio(params=MCPServerStdioParams(command="mcp", args=["run", str(SERVER_FILE)])) as server:
        agent = Agent(name="Assistant", instructions="Use the tools you're given.", model=model, mcp_servers=[server])
        result = await Runner.run(agent, "What is 5 + 7?")
        print(result.final_output)

asyncio.run(main())

# 01_complete_mcp_server.py          01_complete_agent.py
#    (the SERVER)          <----->      (the AGENT / CLIENT)
# "I have these tools/       MCP        "I start that server,
#  resources/prompts,      protocol      connect to it, and let
#  ask me for them"                      the model decide what
#                                         to ask it for"
# 01_complete_mcp_server.py is the server — it owns the actual tools (add), the resource (greeting://{name}), and the prompt (welcome). It doesn't know or care who's using it.

# 01_complete_agent.py is the agent — the one you already know from chapter 2 (Agent, Runner, instructions, a model). The only thing new about it is that instead of (or alongside) local Python-function tools, it starts up the server file as a background helper and asks it "what have you got?" — then the model decides when to actually call add or ask for the greeting, same as it decided when to call get_research_sources back in chapter 2.