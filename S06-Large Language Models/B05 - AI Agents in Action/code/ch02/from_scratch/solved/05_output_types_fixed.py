# ============================================================
# LISTING: 05_output_types_fixed.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: The FIX for 04_output_types.py's broken shape. Same JSON-
#           prompt + json.loads + Pydantic model_validate pattern already
#           established in 03_output_types_basic.py -- only the schema
#           shape changes, from a flat list[str] to a list of a closed,
#           enumerable Task record.
# REF: Chapter 2 notes, section 8 (Typed Outputs and the Strict-JSON Wall)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/05_output_types_fixed.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# 04's broken shape was `tasks: dict[int, str]` -- an arbitrary,
# open-ended set of integer keys, which the SDK's strict-JSON-schema
# builder rejects outright (UserError, before any network call) because
# strict mode requires a fixed, closed set of named properties. `Task`
# below is exactly the fix the notes describe: a record with the SAME
# named fields (`id`, `description`) on every element of the list. That
# is a closed, enumerable shape a JSON Schema can express cleanly as
# `properties: {id: ..., description: ...}, required: [id, description]`
# -- nothing about the fix is SDK-specific, it is a schema-design fix,
# which is exactly why it applies unchanged here where there is no SDK
# schema builder to reject anything in the first place. There was never
# anything to "break" in this from-scratch version -- we just write
# whatever prompt+model shape we choose -- but the same closed-shape
# discipline is worth carrying over anyway, since it's what keeps a real
# model's JSON output landing cleanly on the first try instead of
# wandering into an open-ended, hard-to-validate structure.

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
    """One task in the plan. Every task has the SAME two named fields --
    this is the closed, enumerable shape that fixes 04's broken
    `dict[int, str]`. `id` replaces the dict's arbitrary integer key with
    an explicit, named field instead, and `description` replaces the
    dict's value. Same information, closed shape."""

    id: int
    description: str


class ResearchPlanModel(BaseModel):
    """The typed shape we want back. `tasks: list[Task]` is a list of
    records with identical named fields on every element -- exactly the
    shape a strict JSON Schema builder can express as a fixed
    `properties` object, `additionalProperties: false`, all fields
    `required`. Reused unchanged in every later file in this set (06
    onward) since this fix doesn't change again after this point."""

    tasks: list[Task]


async def main():
    """Same JSON-prompt-then-parse pattern as 03_output_types_basic.py:
    tell the model the exact shape in the system prompt, call the model,
    json.loads the raw text, then ResearchPlanModel.model_validate it.
    The only thing different from 03 is the schema shape itself -- this
    was never a broken pattern to begin with, unlike 04's dict."""
    print("=" * 60)
    print("STEP 1: Building the JSON-instructing system prompt")
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
    print("STEP 2: Calling chat.completions.create")
    print("=" * 60)
    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    raw_text = response.choices[0].message.content
    print(f"  raw text back from the model:\n{raw_text}")

    print("\n" + "=" * 60)
    print("STEP 3: Parsing raw text -> json.loads -> ResearchPlanModel.model_validate")
    print("=" * 60)
    try:
        parsed_json = json.loads(raw_text)
        research_plan = ResearchPlanModel.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"    [ERROR] model did not return valid ResearchPlanModel JSON: {error}")
        print(f"    raw text was: {raw_text!r}")
        raise

    print("\n" + "=" * 60)
    print("STEP 4: The typed result -- this IS what result.final_output would")
    print("        already be, as a validated ResearchPlanModel instance, if")
    print("        output_type=ResearchPlanModel had been passed to Agent(...)")
    print("=" * 60)
    for task in research_plan.tasks:
        print(f"  task {task.id}: {task.description}")


if __name__ == "__main__":
    asyncio.run(main())
