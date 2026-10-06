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

import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

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


# --- Your turn ---
# Build a system prompt that is `instructions` above PLUS an explicit
# instruction to respond with ONLY a JSON object matching
# {"tasks": ["...", "...", ...]}, no other text, no markdown fences.
# This whole function is what output_type=ResearchPlanModel did for you
# in the SDK version: construct the schema (here: describe it in plain
# words in the prompt), tell the model about it, and parse the response
# back into the type.
#
# Call chat.completions.create with that system prompt and a user
# message of "learn about AI agents".
#
# Parse response.choices[0].message.content with json.loads, then
# validate it into a ResearchPlanModel with .model_validate(...). Handle
# json.JSONDecodeError / pydantic.ValidationError the way
# 06_reflexion_with_verifier.py does (print the raw text and re-raise).
#
# Print the typed ResearchPlanModel instance's .tasks field.
#
# Wrap in `async def main(): ...` and run with `asyncio.run(main())`
# under `if __name__ == "__main__":`.
