# ============================================================
# LISTING: 03_output_types_basic.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: Structured output (tasks: list[str]) WITHOUT the SDK's
#           output_type -- a JSON-instructing prompt, json.loads, and
#           Pydantic model_validate, done by hand.
# REF: Chapter 2 notes, section 8 (Typed Outputs and the Strict-JSON Wall)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/03_output_types_basic.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# The SDK version passes output_type=ResearchPlanModel to Agent(...) and
# Runner.run_sync returns a RunResult whose .final_output is already a
# validated ResearchPlanModel instance. This file makes visible the three
# things that call was doing for you underneath: (1) building a JSON
# Schema from the Pydantic model, (2) telling the model about that shape
# in the prompt, and (3) parsing the raw text response back into the
# typed model by hand -- json.loads + ResearchPlanModel.model_validate,
# the same pattern already established in this repo's chapter 5
# from-scratch files (see 06_reflexion_with_verifier.py's SolverOutput).

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


class ResearchPlanModel(BaseModel):
    """The typed shape we want back -- exactly what `output_type=
    ResearchPlanModel` declares to the SDK in the reference version.
    Here, WE are the ones responsible for telling the model about this
    shape (in the prompt) and for parsing the raw text back into it."""

    tasks: list[str]


def build_structured_output_prompt() -> str:
    """Persona PLUS an explicit JSON-only instruction. This whole
    function is what output_type=ResearchPlanModel did for you in the
    SDK version: construct the schema (described here in plain words,
    since we have no schema-builder of our own yet -- that arrives in
    file 04), tell the model about it, and set up the response to be
    parseable back into the type."""
    return (
        instructions
        + """
**OUTPUT FORMAT**
Respond with ONLY a JSON object matching this exact shape, no other
text, no markdown code fences, no explanation before or after it:
{"tasks": ["<task 1>", "<task 2>", "<task 3>", "<task 4>", "<task 5>"]}
"""
    )


async def get_research_plan(topic: str) -> ResearchPlanModel:
    """One raw chat-completions call whose response is parsed and
    validated into ResearchPlanModel by hand -- the same
    json.loads + model_validate pattern as
    06_reflexion_with_verifier.py's SolverOutput."""
    messages = [
        {"role": "system", "content": build_structured_output_prompt()},
        {"role": "user", "content": topic},
    ]

    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    raw_text = response.choices[0].message.content

    try:
        parsed_json = json.loads(raw_text)
        plan = ResearchPlanModel.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"  [ERROR] model did not return valid ResearchPlanModel JSON: {error}")
        print(f"  raw text was: {raw_text!r}")
        raise

    return plan


async def main():
    print("=" * 60)
    print("STEP 1: Building the JSON-instructing system prompt")
    print("=" * 60)
    topic = "learn about AI agents"
    print(f"  topic: {topic!r}")

    print("\n" + "=" * 60)
    print("STEP 2: Calling chat.completions.create and parsing the result")
    print("=" * 60)
    plan = await get_research_plan(topic)

    print("\n" + "=" * 60)
    print("STEP 3: Typed result -- this IS what output_type would have")
    print("        handed back as result.final_output in the SDK version")
    print("=" * 60)
    print(f"  ResearchPlanModel.tasks ({len(plan.tasks)} tasks):")
    for index, task in enumerate(plan.tasks, start=1):
        print(f"    {index}. {task}")


if __name__ == "__main__":
    asyncio.run(main())
