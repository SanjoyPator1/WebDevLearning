# ============================================================
# LISTING: 07_agent_with_tool.py  (reference implementation)
# BUILDING: First tool-using agent — a research-sources lookup tool the
#           agent is told to call before planning.
# REF: Chapter 2, §2.5 / listing 2.11
# PROVIDERS: gemini (default) or ollama — see switch below
# NOTE: tool-calling reliability varies by model — if the agent never
#       calls the tool, that's worth checking before blaming your code.
# ============================================================

import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

load_dotenv()
set_tracing_disabled(True)

PROVIDER = "gemini"  # "gemini" or "ollama"

if PROVIDER == "gemini":
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    MODEL_NAME = os.environ["GEMINI_MODEL"]
elif PROVIDER == "ollama":
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL_NAME = "qwen3:8b"
else:
    raise ValueError(f"unknown PROVIDER: {PROVIDER!r}")

# --- Your turn ---
# Add a tool the agent can call to fetch a list of allowed research sources
# (return a small hardcoded list — no real network call needed). Update the
# persona so it's told to call that tool first, then build a plan that only
# uses the sources it got back. Extend the typed output so each task also
# names which source it uses.

# Agent Instructions
instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Begin by using the tool get_research_sources() 
to get a list of available research sources. 
- Constrain your research plan 
only to use the available research sources.
- Your task is to provide a plan for researching this topic.
- Output 5 concise tasks and specify which of the 
available research sources will be used for each task.
"""

class Task(TypedDict):
    step: int
    research_source: str
    description: str

class ResearchPlanModel(BaseModel):
    tasks: list[Task]
    model_config = ConfigDict(extra="forbid")

@function_tool
def get_research_sources() -> list[str]:
    """Provides a list of research sources"""
    search_sources = [
        "Wikipedia",
        "Google",
        "Youtube"
    ]
    return search_sources

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    output_type=ResearchPlanModel,
    tools=[get_research_sources],   # register the tool with the agent
)

input = "learn about AI agents"

result = Runner.run_sync(
    agent, 
    input=input,
    )

print(result.final_output)
