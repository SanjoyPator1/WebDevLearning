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
# named fields (`id`, `description`) on every element of the list --
# a closed, enumerable shape a JSON Schema can express cleanly.

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
    records with identical named fields on every element. Reused
    unchanged in every later file in this set (06 onward) since this fix
    doesn't change again after this point."""

    tasks: list[Task]


# --- Your turn ---
# Build a JSON-instructing system prompt: take `instructions` above and
# append an explicit "**OUTPUT FORMAT**" block telling the model to
# respond with ONLY a JSON object of this exact shape, no other text, no
# markdown fences:
#   {"tasks": [{"id": 1, "description": "..."}, {"id": 2, "description": "..."}, ...]}
#
# Call chat.completions.create with that system prompt and a user
# message of "learn about AI agents".
#
# Parse response.choices[0].message.content with json.loads, then
# validate it into a ResearchPlanModel with .model_validate(...). Handle
# json.JSONDecodeError / pydantic.ValidationError the way
# 06_reflexion_with_verifier.py (ch05/from_scratch) does: print the raw
# text and re-raise, don't swallow the error.
#
# Print each task's id and description from the typed result.
#
# Wrap in `async def main(): ...` and run with `asyncio.run(main())`
# under `if __name__ == "__main__":`.

async def main():
    # step 1 : building the json instruction system prompt
    output_prompt = """
**OUTPUT FORMAT**
Respond with ONLY a JSON object of this exact shape, no other text, no
markdown fences:
{"tasks": [{"id": 1, "description": "..."}, {"id": 2, "description": "..."}, ...]}
"""

    json_instructions = instructions + output_prompt


    topic = "learn about AI agents"
    messages = [
        {"role": "system", "content": json_instructions},
        {"role": "user", "content": topic},
    ]

    print("Step 1: json instruction is : ",json_instructions)

    # step 2 : calling chat.completions.create
    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    raw_text = response.choices[0].message.content
    print(f"  raw text back from the model:\n{raw_text}")

    # step 3 : Parsing raw text -> json.loads -> ResearchModel.model_validate
    try:
        parsed_json = json.loads(raw_text)
        research_plan = ResearchPlanModel.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"    [ERROR] model did not return valid ResearchPlanModel JSON: {error}")
        print(f"    raw text was: {raw_text!r}")
        raise

    # Step 4 : typed result
    for task in research_plan.tasks:
        print(f"    task {task.id} : {task.description}") 

if __name__ == "__main__":
    asyncio.run(main())