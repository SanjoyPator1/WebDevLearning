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
# construct: `messages` (the same plain list `run_tool_loop` builds in
# 07/07x/08, or here just a plain 2-3-message list from one call with no
# tools at all) already IS the full ordered record of what happened.
# print_trace(messages) below is copied directly from
# ch04/from_scratch/solved/03_agent_orchestrator.py's own print_trace --
# it just walks the list and prints what it finds, exactly the same way
# reading result.new_items back in the SDK version would.

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
    trace" is just walking that list. There is no tool call in this
    file's messages (06 has no tools yet), so this run's trace will show
    only the final assistant message -- that absence of any [tool] line
    IS the trace correctly proving no tool was called this time, the
    same way the dashboard's screenshot would."""
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


async def main():
    """Run 05's fixed agent exactly once, building `messages` by hand
    (system + user + the assistant's raw reply), then call
    print_trace(messages) on that same list. This one call, and the
    plain list it builds, is the entirety of what needs to exist for a
    'trace' to be readable back afterward -- no context manager, no
    upload, no typed item classes."""
    print("=" * 60)
    print("STEP 1: Building the JSON-instructing system prompt (05's fix)")
    print("=" * 60)
    json_instructions = instructions + """
**OUTPUT FORMAT**
Respond with ONLY a JSON object of this exact shape, no other text, no
markdown fences:
{"tasks": [{"id": 1, "description": "..."}, {"id": 2, "description": "..."}, ...]}
"""
    topic = "learn about AI agents"
    messages = [
        {"role": "system", "content": json_instructions},
        {"role": "user", "content": topic},
    ]
    print(f"  system message (persona + JSON shape), {len(json_instructions)} chars")
    print(f"  user message: {topic!r}")

    print("\n" + "=" * 60)
    print("STEP 2: Calling chat.completions.create -- one call, no tools")
    print("=" * 60)
    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    message = response.choices[0].message
    raw_text = message.content or ""
    print(f"  raw text back from the model:\n{raw_text}")

    # This append is the entire "recording" step -- messages now holds
    # the complete, ordered history of this run: system, user, assistant.
    # There is nothing else a trace object could add.
    messages.append({"role": "assistant", "content": raw_text})

    print("\n" + "=" * 60)
    print("STEP 3: Parsing the typed result (same pattern as 05)")
    print("=" * 60)
    try:
        parsed_json = json.loads(raw_text)
        research_plan = ResearchPlanModel.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"    [ERROR] model did not return valid ResearchPlanModel JSON: {error}")
        print(f"    raw text was: {raw_text!r}")
        raise
    for task in research_plan.tasks:
        print(f"  task {task.id}: {task.description}")

    print("\n" + "=" * 60)
    print("STEP 4: print_trace(messages) -- the result.new_items substitute")
    print("=" * 60)
    print_trace(messages)


if __name__ == "__main__":
    asyncio.run(main())
