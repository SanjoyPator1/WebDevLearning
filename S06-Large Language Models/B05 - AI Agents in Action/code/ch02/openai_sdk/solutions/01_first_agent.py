# ============================================================
# LISTING: 01_first_agent.py  (reference implementation)
# BUILDING: The minimal possible agent — a "Research Planner"
#           persona that turns a topic into 5 short tasks.
#           No model settings, no output type, no tools yet.
# REF: Chapter 2, listing 2.1-ish
# PROVIDERS: gemini (default) or ollama — see switch below
# ============================================================

import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
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

# --- Your turn ---
# Build the "Research Planner" persona: a system prompt that turns any topic
# into exactly 5 short tasks (5 words or less each).
# Wire that persona into an Agent using `client` and `MODEL_NAME` above.
# Run it on the topic "learn about AI agents" and print what comes back.

# Agent Instructions
instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)
)

input="learn about AI agents"

result = Runner.run_sync(agent, input=input)

print("result: ",result.final_output)
