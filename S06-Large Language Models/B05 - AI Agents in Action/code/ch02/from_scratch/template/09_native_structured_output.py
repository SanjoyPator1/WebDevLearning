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
#                                 (pip install ollama; already done for
#                                 you), using Ollama's own `format=` field.
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


# --- Your turn: Path A (asking) ---
# Reuse file 05's approach: append an **OUTPUT FORMAT** block (describing
# the {"tasks": [{"id": 1, "description": "..."}, ...]} shape) onto
# `instructions`, call `gemini_client.chat.completions.create(...)` with
# that system prompt and the `topic` user message, then
# json.loads + ResearchPlanModel.model_validate the raw text, inside a
# try/except (json.JSONDecodeError, ValidationError) that prints the raw
# text and re-raises on failure, matching every prior file.
#
# Wrap this in `async def run_path_a_asking() -> ResearchPlanModel: ...`
# and return the validated instance.
#
async def run_path_a_asking() -> ResearchPlanModel:
    raise NotImplementedError("Path A: build the asking-path call, same pattern as file 05")


# --- Your turn: Path B (Gemini, forcing) ---
# Call `await gemini_client.chat.completions.parse(model=GEMINI_MODEL_NAME,
# messages=[...], response_format=ResearchPlanModel)` -- note this is
# `instructions` WITHOUT any hand-written JSON-format block appended; the
# schema itself is doing the instructing now, not prompt text.
#
# Read `response.choices[0].message`. Check `.refusal` first -- if it is
# truthy, raise a RuntimeError naming it (per the notes' gotchas list: a
# refusal means the output may not match the schema even under strict
# mode). Otherwise, `.parsed` is already a validated ResearchPlanModel
# instance -- no json.loads, no model_validate, no try/except needed for
# shape errors, because the shape was never allowed to be wrong.
#
# Wrap this in `async def run_path_b_gemini_forcing() -> ResearchPlanModel: ...`
#
async def run_path_b_gemini_forcing() -> ResearchPlanModel:
    raise NotImplementedError("Path B: use chat.completions.parse with response_format=ResearchPlanModel")


# --- Your turn: Path C (Ollama, forcing) ---
# Call `await ollama_client.chat(model=OLLAMA_MODEL_NAME, messages=[...],
# format=ResearchPlanModel.model_json_schema())`. Notice: `ollama_client`
# is a DIFFERENT client object (AsyncOllamaClient, not AsyncOpenAI), and
# its `.chat(...)` method takes `format=` directly, not
# `response_format=` wrapped in a dict.
#
# The response object's shape also differs from OpenAI's: read the raw
# text off `response.message.content` (NOT `.choices[0].message.content`
# -- there is no `.choices` list here; Ollama's `ChatResponse` has a
# single `message` field, not a list), then run it through
# `ResearchPlanModel.model_validate_json(...)` yourself. Ollama's grammar
# guarantees the JSON is well-formed and schema-shaped, but running your
# own validate() here is still worth doing once, just to see it pass
# instantly -- in real code you could trust it and skip straight to using
# the dict.
#
# One more field worth knowing about on Ollama's `Message`:
# `response.message.thinking` -- qwen3 is a thinking model (same one from
# file 02's token-budget gotcha). If your output ever looks empty or
# truncated, print `response.message.thinking` to check whether the
# reasoning ate the whole response before any JSON got written.
#
# A SPECIFIC version of that gotcha to watch for here: with thinking left
# on (the default), qwen3:8b has been observed returning a perfectly
# schema-valid but EMPTY {"tasks": []} -- the grammar only promises
# well-formed JSON, never a non-empty list. Pass `think=False` as a
# keyword argument to `ollama_client.chat(...)` to get a real answer
# instead of the "technically valid, practically useless" one.
#
# Wrap this in `async def run_path_c_ollama_forcing() -> ResearchPlanModel: ...`
#
async def run_path_c_ollama_forcing() -> ResearchPlanModel:
    raise NotImplementedError("Path C: use ollama_client.chat with format=ResearchPlanModel.model_json_schema()")


# --- Your turn: run all three and compare ---
# Call all three paths (sequentially is fine -- this file is about the
# mechanism, not about asyncio.gather), printing a labeled banner before
# each one's result, in the same `print("task N: description")` shape
# used by every earlier file's output loop. At the end, print one summary
# line per path noting which mechanism it used (asking vs forcing) and
# whether it needed a try/except for shape errors.
#
async def main():
    raise NotImplementedError("call all three run_path_* functions and print their results")


if __name__ == "__main__":
    asyncio.run(main())
