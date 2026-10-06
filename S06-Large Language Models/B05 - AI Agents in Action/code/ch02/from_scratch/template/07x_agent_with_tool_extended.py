# ============================================================
# LISTING: 07x_agent_with_tool_extended.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: The same one-tool pattern as 07_agent_with_tool.py, except
#           the tool now returns STRUCTURED records (list[dict]) instead
#           of plain strings, to show that this was never a distinct
#           mechanism to build.
# REF: Chapter 2 notes, section 10 (Giving the Agent Tools)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/07x_agent_with_tool_extended.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# There is nothing special here from the raw client's point of view.
# get_research_sources() in 07 returned `list[str]`; here it returns
# `list[dict]`. A tool's handler just returns whatever Python value it
# wants to, and that value gets `json.dumps(result, default=str)`'d into
# the tool-result message exactly the same way in every case (see
# run_tool_loop's `messages.append({"role": "tool", ...})` line,
# unchanged from 07). "Returning a structured object instead of a
# string" was never a distinct mechanism in the SDK either.

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

# --- The one tool, raw schema + handler -- schema is IDENTICAL to 07's;
# only the handler's return value's shape changes.
get_research_sources_tool_schema = {
    "type": "function",
    "function": {
        "name": "get_research_sources",
        "description": (
            "Provides a list of research sources the plan may draw on, "
            "each as a record with a 'name' field."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def get_research_sources() -> list[dict]:
    """Same tool as 07, except the return value is now a list of
    structured records instead of plain strings. Nothing about the
    mechanics changes -- json.dumps(result, default=str) handles a list
    of dicts exactly as readily as a list of strings."""
    sources = [{"name": "Wikipedia"}, {"name": "Google"}, {"name": "YouTube"}]
    print(f"    [tool] get_research_sources() -> {sources}")
    return sources


tool_handlers = {"get_research_sources": get_research_sources}

instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- First, call the get_research_sources tool to see what sources are available.
  Each source is a record with a "name" field.
- Then provide a plan on how to research this topic, using those sources.
- Output 5 concise tasks (5 words or less) to your plan.
- For each task, say which source (its "name") it uses.
"""


class Task(BaseModel):
    """Same shape as 07's Task -- the tool's return shape changing has no
    effect on the OUTPUT shape we ask the model to produce; `source` is
    still just the plain source name string, read off of the tool
    result's "name" field."""

    id: int
    description: str
    source: str


class ResearchPlanModel(BaseModel):
    tasks: list[Task]


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6):
    """Unchanged from 07 -- copied from
    ch04/from_scratch/solved/03_agent_orchestrator.py. This function's
    code does not know or care whether a handler returns a string, a
    dict, or a list of dicts; `json.dumps(result, default=str)` handles
    all of them identically."""
    for step in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, message.content or ""
        messages.append({
            "role": "assistant", "content": message.content,
            "tool_calls": [{"id": tc.id, "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message.tool_calls],
        })
        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            print(f"    [tool] {tool_call.function.name}({arguments})")
            handler = tool_handlers[tool_call.function.name]
            result = handler(**arguments)
            if hasattr(result, "__await__"):
                result = await result
            print(f"    [tool] -> {result}")
            messages.append({"role": "tool", "tool_call_id": tool_call.id,
                              "content": json.dumps(result, default=str)})
    return messages, None  # budget exhausted, no final text


# --- Your turn ---
# Same shape as 07_agent_with_tool.py's main(). Write `async def main():
# ...` that:
#   1. Builds `messages` (system = instructions, user = "learn about AI
#      agents").
#   2. Calls `await run_tool_loop(messages, [get_research_sources_tool_schema],
#      tool_handlers)`.
#   3. PHASE TWO: appends a {"role": "user", ...} message asking for ONLY
#      a JSON object of this exact shape, no other text, no markdown
#      fences (note each source's "name" value becomes the plain source
#      string in the output):
#        {"tasks": [{"id": 1, "description": "...", "source": "..."},
#                   {"id": 2, "description": "...", "source": "..."}, ...]}
#      Then one more chat.completions.create call, no `tools=` this time.
#   4. Parses with json.loads + ResearchPlanModel.model_validate (print
#      raw text and re-raise on failure).
#   5. Prints each task's id, description, and source.
#
# Run with `asyncio.run(main())` under `if __name__ == "__main__":`.
