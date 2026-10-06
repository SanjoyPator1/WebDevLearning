# ============================================================
# LISTING: 03_output_types_basic.py  (reference implementation)
# BUILDING: First structured-output version — a ResearchPlanModel
#           Pydantic class with tasks: List[str], set as the
#           agent's output_type instead of raw text.
# REF: Chapter 2, §2.4 (structured output intro)
# PROVIDERS: gemini (default) or ollama — see switch below
# NOTE: strict output-type enforcement is strongest on real OpenAI. Ollama
#       and Gemini's OpenAI-compatible endpoint may not constrain generation
#       as tightly, so an occasional off-schema response is a model
#       instruction-following issue, not a bug in your wiring.
# ============================================================

import os
from typing import List

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

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
# Give the agent a typed output instead of free text: a Pydantic model whose
# `tasks` field is a plain list of strings. Wire it in via the agent's
# output_type. Run it and inspect the typed result.

# Agent Instructions
instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""

class ResearchPlanModel(BaseModel):
    task: List[str]
    """A list of tasks to perform for research"""

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    output_type=ResearchPlanModel
)

input = "learn about ai agents"

result = Runner.run_sync(
    agent,
    input=input
)

print(result.final_output)
