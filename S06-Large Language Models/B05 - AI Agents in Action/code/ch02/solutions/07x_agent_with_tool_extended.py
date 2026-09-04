# ============================================================
# LISTING: 07x_agent_with_tool_extended.py  (reference implementation)
# BUILDING: Same idea as 07, but the tool returns structured objects
#           instead of plain strings.
# REF: Chapter 2, §2.5 (extended variant)
# PROVIDERS: gemini (default) or ollama — see switch below
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
# Same idea as 07, but instead of the tool returning plain strings, have it
# return a small structured record per source (e.g. just a name field for
# now). Update your task schema to hold that structured source instead of
# a bare string.

# Agent Instructions
instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Begin by using the tool get_research_sources() to get a list of available research sources. 
- Constrain your research plan to only use the available research sources.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks, and specify which available research source will be used for each task.
"""

class ResearchSource(TypedDict):
    name: str

class Task(TypedDict):
    step: int
    research_source: ResearchSource
    description: str

class ResearchPlanModel(BaseModel):
    tasks: list[Task]

    model_config = ConfigDict(extra="forbid")

@function_tool
def get_research_sources() -> list[str]:
    """Provides a list of research sources"""
    search_sources = [
        ResearchSource(name="Wikipedia"),
        ResearchSource(name="Google"),
        ResearchSource(name="Youtube")
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

