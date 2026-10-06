# ============================================================
# LISTING: 06_agent_with_tracing.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: 05's fixed research-planner agent (same persona, same models,
#           no tools yet), run once, then read back through print_trace()
#           -- the from-scratch substitute for the SDK's `with
#           trace(...):` block and its `result.new_items` list.
# REF: Chapter 2 notes, section 9 (Tracing: What the Dashboard Shows, and
#      What We Substitute)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/06_agent_with_tracing.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# There was never a `with trace(...):` block to build here, and that is
# the entire point of this file, not a gap in it. In the SDK version,
# `with trace("name"): result = Runner.run_sync(...)` opens a context
# manager that (with a real OPENAI_API_KEY) uploads a timeline of typed
# items -- ToolCallItem, ToolCallOutputItem, MessageOutputItem -- to
# OpenAI's Traces dashboard, and `result.new_items` is the same timeline
# read back locally as Python objects instead of a web page. But a
# "trace" is not a separate thing the SDK computes -- it is a record of
# messages that were already going to exist as soon as you build a
# messages list and call the model with it. There is no special object
# model to construct by hand here, because there is nothing extra to
# construct: `messages` already IS the full ordered record of what
# happened. print_trace(messages) below is copied directly from
# ch04/from_scratch/solved/03_agent_orchestrator.py's own print_trace.

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

load_dotenv()

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

instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""


class Task(BaseModel):
    """One task in the plan -- same closed, enumerable shape fixed in 05."""

    id: int
    description: str


class ResearchPlanModel(BaseModel):
    """The typed shape we want back -- unchanged from 05, and unchanged
    in every file from here through 08."""

    tasks: list[Task]


def print_trace(messages):
    """Print a one-line summary of every step actually taken, in order.
    Reused directly from ch04/from_scratch/solved/03_agent_orchestrator.py
    -- same function, same shape, because the underlying claim is
    identical: a plain `messages` list already records every LLM call,
    tool call, and tool result in chronological order, so "reading the
    trace" is just walking that list."""
    for message in messages:
        if message["role"] == "assistant" and message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                print(
                    f"    [trace] assistant called tool: "
                    f"{tool_call['function']['name']}({tool_call['function']['arguments']})"
                )
        elif message["role"] == "tool":
            print(f"    [trace] tool result: {message['content']}")
        elif message["role"] == "assistant" and message.get("content"):
            print(f"    [trace] assistant produced a message: {message['content']!r}")


# --- Your turn ---
# Write `async def main(): ...` that:
#   1. Builds the JSON-instructing system prompt (same OUTPUT FORMAT
#      block from 05, appended to `instructions`).
#   2. Builds `messages = [{"role": "system", ...}, {"role": "user",
#      "content": "learn about AI agents"}]`.
#   3. Calls chat.completions.create once (no tools -- this file doesn't
#      have any yet), reads `message.content`, and appends
#      {"role": "assistant", "content": ...} onto `messages` by hand --
#      this append IS the "recording" step; there is no separate object
#      to build.
#   4. Parses the raw text into a ResearchPlanModel the same way 05 did
#      (json.loads + model_validate, print raw text and re-raise on
#      failure) and prints each task.
#   5. Calls print_trace(messages) and observe: since this run has no
#      tool calls, the trace shows only the final assistant message --
#      that's the correct, expected trace for a tool-less run.
#
# Run with `asyncio.run(main())` under `if __name__ == "__main__":`.
