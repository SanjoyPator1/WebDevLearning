# ============================================================
# LISTING: 09_native_structured_output.py  (bonus -- FROM SCRATCH, no agents SDK)
# BUILDING: The "forcing" path from the notes (section 8, "How Strict
#           Mode Actually Works"), side by side with the "asking" path
#           you've used in every file up to this point (03, 05, 07).
#           Same ResearchPlanModel/Task shape as 05 -- only the mechanism
#           that gets the model to respect it changes.
# REF: Chapter 2 notes, section 8 -- "Asking vs Forcing: Where Each
#      Chapter 2 File Sits" table, and the provider-code block right
#      after it.
# NOT part of the numbered problem statement (sections 1-9 end at
# 08_agent_with_tools_tracing.py) -- this file exists to let you feel the
# difference the notes describe, rather than just read about it.
# ============================================================
#
# Every file so far (03, 05, 07, 08) has been on the ASKING path: describe
# the shape in the system prompt as English + an example, then
# json.loads + model_validate it yourself afterwards, inside a
# try/except for when the model doesn't comply. Nothing in that pipeline
# stops the model from writing "Sure! Here's your plan:" before the JSON.
#
# This file runs the exact same persona and topic through THREE paths and
# prints what each one actually returns, so you can compare them instead
# of taking the notes' word for it:
#
#   Path A (asking)            -- what you've already built in file 05.
#   Path B (Gemini, forcing)   -- client.chat.completions.parse(...,
#                                 response_format=ResearchPlanModel) on
#                                 the SAME AsyncOpenAI client you already
#                                 have, since Gemini's OpenAI-compatible
#                                 endpoint accepts response_format with
#                                 json_schema on real-time (non-batch)
#                                 calls for Gemini 2.5+ models.
#   Path C (Ollama, forcing)   -- a SEPARATE client, ollama.AsyncClient
#                                 (pip install ollama), using Ollama's own
#                                 `format=` field.
#                                 CORRECTION, confirmed by direct testing:
#                                 the plain AsyncOpenAI client's
#                                 response_format=/`.parse()` ALSO works
#                                 correctly against Ollama's OpenAI-
#                                 compatible endpoint -- this was NOT true
#                                 when this file was first written (an
#                                 older Ollama release didn't support it),
#                                 but testing against a current Ollama
#                                 install shows both routes now work. Path
#                                 C still uses the separate native client
#                                 here so you see Ollama's OWN format=
#                                 mechanism at least once, not because
#                                 it's the only way to force a schema on
#                                 Ollama anymore.

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from ollama import AsyncClient as AsyncOllamaClient
from pydantic import BaseModel, ValidationError

load_dotenv()

gemini_client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
GEMINI_MODEL_NAME = os.environ["GEMINI_MODEL"]

ollama_client = AsyncOllamaClient(host="http://localhost:11434")
# A second client for the SAME Ollama server, but using the plain OpenAI-
# compatible route instead of Ollama's own native API -- confirmed by
# direct testing to also support response_format=/`.parse()` correctly.
ollama_openai_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
OLLAMA_MODEL_NAME = "qwen3:8b"  # swap for whatever tag `ollama list` shows you

instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""

topic = "learn about AI agents"


class Task(BaseModel):
    """Same shape as file 05's Task -- id + description, nothing new."""

    id: int
    description: str


class ResearchPlanModel(BaseModel):
    """Same shape as file 05's ResearchPlanModel -- reused unchanged so
    Paths A, B, and C are judged on the SAME target shape."""

    tasks: list[Task]


async def run_path_a_asking() -> ResearchPlanModel:
    """Path A: ASKING. Describe the shape in plain English inside the
    system prompt, call the model, then parse + validate the raw text
    ourselves afterwards. Nothing here stops the model from ignoring the
    instruction -- the try/except exists because of that fact, not as a
    formality."""
    json_instructions = (
        instructions
        + """
**OUTPUT FORMAT**
Respond with ONLY a JSON object of this exact shape, no other text, no
markdown fences:
{"tasks": [{"id": 1, "description": "..."}, {"id": 2, "description": "..."}, ...]}
"""
    )
    messages = [
        {"role": "system", "content": json_instructions},
        {"role": "user", "content": topic},
    ]

    response = await gemini_client.chat.completions.create(model=GEMINI_MODEL_NAME, messages=messages)
    raw_text = response.choices[0].message.content
    print(f"  raw text back from the model:\n{raw_text}")

    try:
        parsed_json = json.loads(raw_text)
        research_plan = ResearchPlanModel.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"    [ERROR] model did not return valid ResearchPlanModel JSON: {error}")
        print(f"    raw text was: {raw_text!r}")
        raise

    return research_plan


async def run_path_b_gemini_forcing() -> ResearchPlanModel:
    """Path B: FORCING, via Gemini's OpenAI-compatible endpoint.
    `response_format=ResearchPlanModel` sends the schema itself with the
    request -- the persona has NO hand-written JSON-format block, because
    the schema is doing that job now, not prompt text. `.parsed` comes
    back as an already-validated ResearchPlanModel instance: no
    json.loads, no model_validate, no try/except for shape errors,
    because the shape was never allowed to be wrong in the first place."""
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": topic},
    ]

    response = await gemini_client.chat.completions.parse(
        model=GEMINI_MODEL_NAME,
        messages=messages,
        response_format=ResearchPlanModel,
    )
    message = response.choices[0].message

    if message.refusal:
        raise RuntimeError(f"model refused: {message.refusal}")

    return message.parsed


async def run_path_c_ollama_forcing() -> ResearchPlanModel:
    """Path C: FORCING, against Ollama. Originally written against
    Ollama's own grammar-constrained `format=` field via a DIFFERENT
    client (AsyncOllamaClient, not AsyncOpenAI), with a different response
    shape (`response.message.content`, no `.choices` list). That native
    route is kept below, commented out, for reference. Confirmed by direct
    testing: the plain AsyncOpenAI client's response_format=/`.parse()`
    also works correctly against Ollama's OpenAI-compatible endpoint, with
    the exact same call shape as Path B -- so that's the active path now."""
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": topic},
    ]

    # --- Native ollama.AsyncClient route (commented out, kept for reference) ---
    # # think=False matters here, not just for cost: with thinking left on
    # # (the default), qwen3:8b was observed spending its reasoning budget
    # # and then taking the grammar's EASIEST valid path -- an empty
    # # {"tasks": []} -- which is schema-valid JSON but a useless answer.
    # # This is "strict mode guarantees shape, not content" happening live:
    # # the grammar never promised a NON-EMPTY list, only a well-formed one.
    # response = await ollama_client.chat(
    #     model=OLLAMA_MODEL_NAME,
    #     messages=messages,
    #     format=ResearchPlanModel.model_json_schema(),
    #     think=False,
    # )
    #
    # if response.message.thinking:
    #     print(f"  [thinking tokens spent]: {len(response.message.thinking)} chars")
    #
    # raw_text = response.message.content
    # print(f"  raw text back from the model:\n{raw_text}")
    #
    # return ResearchPlanModel.model_validate_json(raw_text)

    # --- Plain AsyncOpenAI route, same shape as Path B, confirmed working ---
    response = await ollama_openai_client.chat.completions.parse(
        model=OLLAMA_MODEL_NAME,
        messages=messages,
        response_format=ResearchPlanModel,
    )
    message = response.choices[0].message

    if message.refusal:
        raise RuntimeError(f"model refused: {message.refusal}")

    return message.parsed


async def main():
    """Run all three paths against the SAME persona and topic, print each
    one's result, and summarize which mechanism each one used."""
    print("=" * 60)
    print("PATH A: ASKING (Gemini, prompt text + json.loads + model_validate)")
    print("=" * 60)
    plan_a = await run_path_a_asking()
    for task in plan_a.tasks:
        print(f"  task {task.id}: {task.description}")

    print("\n" + "=" * 60)
    print("PATH B: FORCING (Gemini, response_format=ResearchPlanModel)")
    print("=" * 60)
    plan_b = await run_path_b_gemini_forcing()
    for task in plan_b.tasks:
        print(f"  task {task.id}: {task.description}")

    print("\n" + "=" * 60)
    print("PATH C: FORCING (Ollama, format=ResearchPlanModel.model_json_schema())")
    print("=" * 60)
    plan_c = await run_path_c_ollama_forcing()
    for task in plan_c.tasks:
        print(f"  task {task.id}: {task.description}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("  Path A (Gemini, asking)  : prompt text only -- needed try/except for shape errors")
    print("  Path B (Gemini, forcing) : response_format=  -- no try/except needed for shape")
    print("  Path C (Ollama, forcing) : format=            -- no try/except needed for shape")


if __name__ == "__main__":
    asyncio.run(main())
