# ============================================================
# LISTING: 08_agent_with_tools_tracing.py  (reference implementation -- FROM SCRATCH, no agents SDK) -- CAPSTONE
# BUILDING: TWO tools, registered together, where the second
#           (get_resource_url) needs a source name that only the first
#           (get_research_sources) can supply -- real tool chaining --
#           run through run_tool_loop, followed by the same two-phase
#           structured-extraction call as 07/07x, followed by
#           print_trace(messages) to confirm both tool calls land in the
#           trace before the final message.
# REF: Chapter 2 notes, section 9 (Tracing) and section 10 (Giving the
#      Agent Tools, "Tool Chaining")
# COMPARE: the SDK version of this file at ../../openai_sdk/template/08_agent_with_tools_tracing.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# The notes call this pattern tool chaining: "the second tool NEEDS a
# source name that only the first tool's result can supply." Both tools
# are registered on the SAME run_tool_loop call, in the SAME tools_schema
# list -- there is no special "chained tools" API, no ordering hint we
# give the model. The model has to (1) call get_research_sources, (2)
# read its result out of the tool-result message run_tool_loop appended,
# and (3) decide on its own to call get_resource_url with one of the
# names it just saw. Chaining is a MODEL decision visible only in the
# order tool calls actually happen in -- exactly what print_trace(messages)
# at the end of this file lets you confirm.

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

# --- Tool 1: same as 07's get_research_sources -- returns a small,
# hardcoded list of plain source-name strings.
get_research_sources_tool_schema = {
    "type": "function",
    "function": {
        "name": "get_research_sources",
        "description": "Provides a list of research sources the plan may draw on.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def get_research_sources() -> list[str]:
    """Same tool as 07."""
    sources = ["Wikipedia", "Google", "YouTube"]
    print(f"    [tool] get_research_sources() -> {sources}")
    return sources


# --- Tool 2: NEW. This is the one that needs a source name only tool 1's
# result can supply -- the model has to have already seen
# get_research_sources's output in `messages` before it can call this
# tool with a name that will actually resolve.
get_resource_url_tool_schema = {
    "type": "function",
    "function": {
        "name": "get_resource_url",
        "description": (
            "Given a research source's name (e.g. one returned by "
            "get_research_sources), returns that source's URL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "source name, e.g. 'Wikipedia'."},
            },
            "required": ["source"],
        },
    },
}

_known_resource_urls = {
    "Wikipedia": "https://wikipedia.org",
    "Google": "https://google.com",
    "YouTube": "https://youtube.com",
}


def get_resource_url(source: str) -> str:
    """Look up a hardcoded URL for a known source name. The `.get(...,
    fallback)` default means calling this with an unknown/guessed name
    still returns SOMETHING rather than crashing -- but a well-chained
    run should never hit that fallback, because the model should only
    ever pass a name it just saw come back from get_research_sources."""
    url = _known_resource_urls.get(source, "https://unknown.example")
    print(f"    [tool] get_resource_url({source!r}) -> {url}")
    return url


# TWO tools total, registered together in one schema list and one
# handler dict -- the model decides for itself which to call, in what
# order, and how many times, exactly as section 10's "Tool Chaining"
# note describes.
tools_schema = [get_research_sources_tool_schema, get_resource_url_tool_schema]
tool_handlers = {
    "get_research_sources": get_research_sources,
    "get_resource_url": get_resource_url,
}

instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- First, call get_research_sources to see what sources are available.
- Then, for at least one of those sources, call get_resource_url to find
  its URL. Only pass source names you actually saw returned by
  get_research_sources.
- Then provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
- For each task, say which source it uses and that source's URL.
"""


class Task(BaseModel):
    """Extended with BOTH new fields this capstone file adds: `source`
    (same as 07) and `source_url` (new -- the URL get_resource_url
    resolved for that source)."""

    id: int
    description: str
    source: str
    source_url: str


class ResearchPlanModel(BaseModel):
    tasks: list[Task]


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6):
    """Unchanged from 07/07x -- copied from
    ch04/from_scratch/solved/03_agent_orchestrator.py. Registering TWO
    tools here instead of one changes nothing about this function's
    code: `tools_schema` is just a longer list, `tool_handlers` is just a
    dict with two keys, and the dispatch loop below already handles
    however many tool_calls come back on message.tool_calls in a single
    turn."""
    for step in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, message.content or ""
        # messages.append({
        #     "role": "assistant", "content": message.content,
        #     "tool_calls": [{"id": tc.id, "type": "function",
        #         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
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


def print_trace(messages):
    """Reused directly from ch04/from_scratch/solved/03_agent_orchestrator.py
    (and 06's copy of the same function). Walking `messages` after this
    run should show BOTH tool calls -- get_research_sources, then
    get_resource_url -- appearing in order, BEFORE the final assistant
    message."""
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
#   1. Builds `messages` (system = instructions, user = "learn about AI
#      agents").
#   2. Calls `await run_tool_loop(messages, tools_schema, tool_handlers)`
#      -- note BOTH tools are registered together here, so the model
#      decides for itself whether/when to call get_resource_url after
#      seeing get_research_sources's result.
#   3. PHASE TWO: appends one more {"role": "user", ...} message asking
#      for ONLY a JSON object of this exact shape, no other text, no
#      markdown fences:
#        {"tasks": [{"id": 1, "description": "...", "source": "...",
#                   "source_url": "..."}, ...]}
#      Then one more chat.completions.create call, no `tools=` this time.
#   4. Parses with json.loads + ResearchPlanModel.model_validate (print
#      raw text and re-raise on failure).
#   5. Prints each task's id, description, source, and source_url.
#   6. Calls print_trace(messages) and confirm -- by reading the printed
#      output -- that BOTH tool calls (get_research_sources, then
#      get_resource_url) appear in order before the final assistant
#      message. That ordering is the entire proof of tool chaining.
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
        tools_schema,
        tool_handlers
    )

    print("Plan text is : ",plan_text)

    # step 2 : phase 2 - one more, tool-less call to extract the structured research plan model from the same conversation
    messages.append({
        "role": "user",
        "content": (
            "Now convert the plan above into ONLY a JSON object of this "
            "exact shape, no other text, no markdown fences:\n"
            '{"tasks": [{"id": 1, "description": "...", "source": "...", '
            '"source_url": "..."}, {"id": 2, "description": "...", '
            '"source": "...", "source_url": "..."}, ...]}'
        ),
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
        print(f"  task {task.id}: {task.description}  (source: {task.source}), url:{task.source_url}")

    # step 4 :  print trace
    print_trace(messages) 

if __name__ == "__main__":
    asyncio.run(main())
