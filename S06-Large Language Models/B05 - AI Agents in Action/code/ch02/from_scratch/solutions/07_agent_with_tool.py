# ============================================================
# LISTING: 07_agent_with_tool.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: One tool -- get_research_sources() -> list[str] -- registered
#           as a raw tool schema + Python handler, dispatched through
#           run_tool_loop, followed by a second, tool-less call that
#           extracts the tool-informed conversation into a structured
#           ResearchPlanModel (now extended with a `source` field).
# REF: Chapter 2 notes, section 10 (Giving the Agent Tools)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/07_agent_with_tool.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# The SDK version's `@function_tool` decorator inspects a plain Python
# function's signature and docstring and auto-generates the JSON schema
# the model sees; `tools=[get_research_sources]` on Agent(...) means that
# schema rides along on every LLM call, and Runner.run_sync handles the
# entire call -> tool_calls -> dispatch -> re-call loop invisibly. This
# file makes every one of those steps visible.
#
# Combining tool-calling AND structured typed output in one raw round
# trip is more than one new mechanic to absorb at once, so this file
# keeps the two phases separate: first `run_tool_loop` runs until the
# model stops calling tools; then ONE MORE tool-less call, with the
# JSON-shape instruction appended to the same `messages` history, asks
# the model to convert that tool-informed conversation into the strict
# ResearchPlanModel shape.

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

# --- The one tool, raw schema + handler -- this pair IS what
# @function_tool built from get_research_sources's signature and
# docstring in the SDK version. Registered on every call whether the
# model uses it or not, per section 3/10's token-tax point.
get_research_sources_tool_schema = {
    "type": "function",
    "function": {
        "name": "get_research_sources",
        "description": "Provides a list of research sources the plan may draw on.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def get_research_sources() -> list[str]:
    """Plain Python function -- no @function_tool decorator; the schema
    above is written out by hand instead. Returns a small hardcoded list
    of source names."""
    sources = ["Wikipedia", "Google", "YouTube"]
    print(f"    [tool] get_research_sources() -> {sources}")
    return sources


tool_handlers = {"get_research_sources": get_research_sources}

instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- First, call the get_research_sources tool to see what sources are available.
- Then provide a plan on how to research this topic, using those sources.
- Output 5 concise tasks (5 words or less) to your plan.
- For each task, say which source it uses.
"""


class Task(BaseModel):
    """One task in the plan. `source` is new in this file -- the name of
    the research source (from get_research_sources's result) that this
    task relies on."""

    id: int
    description: str
    source: str


class ResearchPlanModel(BaseModel):
    tasks: list[Task]


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6):
    """Call the model, dispatch any tool calls, append results, repeat
    until the model stops calling tools or the step budget runs out. This
    is exactly what Runner.run_sync() did invisibly whenever tools were
    registered on Agent(...) -- copied unchanged from
    ch04/from_scratch/solved/03_agent_orchestrator.py."""
    for step in range(max_steps):
        print(f"\n Step:{step} -> messages start: ",messages)
        
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, message.content or ""
        # messages.append({
        #     "role": "assistant", "content": message.content,
        #     "tool_calls": [
        #         {
        #             "id": tc.id, 
        #             "type": "function",
        #             "function": {
        #                             "name": tc.function.name, 
        #                             "arguments": tc.function.arguments
        #                         }
        #         }
        #         for tc in message.tool_calls],
        # })

        # tc.model_dump() instead of hand-picking id/type/function: Gemini attaches an
        # extra thought_signature field to each tool call that MUST be echoed back
        # unchanged on the next turn, or the follow-up call fails with a 400. Picking
        # only a few known fields silently drops it.
        messages.append({
            "role": "assistant", "content": message.content,
            "tool_calls": [tc.model_dump() for tc in message.tool_calls],
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
# Write `async def main(): ...` that:
#   1. Builds `messages = [{"role": "system", "content": instructions},
#      {"role": "user", "content": "learn about AI agents"}]`.
#   2. Calls `await run_tool_loop(messages, [get_research_sources_tool_schema],
#      tool_handlers)` -- this drives the model through calling the tool
#      and producing a free-form plan in prose.
#   3. PHASE TWO: appends one more {"role": "user", ...} message onto the
#      SAME `messages` list instructing the model to respond with ONLY a
#      JSON object of this exact shape, no other text, no markdown fences:
#        {"tasks": [{"id": 1, "description": "...", "source": "..."},
#                   {"id": 2, "description": "...", "source": "..."}, ...]}
#      Then call chat.completions.create ONE more time over that history
#      -- no `tools=` this time, the tool phase is over.
#   4. Parses the raw text with json.loads + ResearchPlanModel.model_validate
#      (print raw text and re-raise on failure, same pattern as 05/06).
#   5. Prints each task's id, description, and source.
#
# Run with `asyncio.run(main())` under `if __name__ == "__main__":`.
async def main():
    # STEP 1: Building messages and running the tool loop
    topic = "learn about AI agents"
    messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": topic},
        ]

    messages, plan_text = await run_tool_loop(
        messages,
        [get_research_sources_tool_schema],
        tool_handlers
    )

    print("Plan text is : ",plan_text)

    # step 2 : phase 2 - one more, tool-less call to extract the structured research plan model from the same conversation
    messages.append({
        "role" : "user",
        "content" : (
            "Now convert the plan above into ONLY a JSON object of this "
            "exact shape, no other text, no markdown fences:\n"
            '{"tasks": [{"id": 1, "description": "...", "source": "..."}, '
            '{"id": 2, "description": "...", "source": "..."}, ...]}'
        )
    })

    print(f"\nmessages out of loop : ",messages)

    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    raw_text = response.choices[0].message.content
    print(f"  raw JSON text back from the model:\n{raw_text}")

    # step 3 parsing into the typed tool-informed research plan model
    try:
        parsed_json = json.loads(raw_text)
        research_plan = ResearchPlanModel.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"    [ERROR] model did not return valid ResearchPlanModel JSON: {error}")
        print(f"    raw text was: {raw_text!r}")
        raise
    for task in research_plan.tasks:
        print(f"  task {task.id}: {task.description}  (source: {task.source})")


if __name__ == "__main__":
    asyncio.run(main())

    