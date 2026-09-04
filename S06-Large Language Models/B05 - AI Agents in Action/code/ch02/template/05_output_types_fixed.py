# ============================================================
# LISTING: 05_output_types_fixed.py  (reference implementation)
# BUILDING: The fix for 04's schema error.
# REF: Chapter 2, listing 2.9 (the "after")
# PROVIDERS: gemini (default) or ollama — see switch below
# ============================================================

import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

load_dotenv()
set_tracing_disabled(True)

PROVIDER = "gemini"  # "gemini" or "ollama"

if PROVIDER == "gemini":
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    MODEL_NAME = os.environ["GEMINI_MODEL"]
elif PROVIDER == "ollama":
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL_NAME = "qwen3:8b"
else:
    raise ValueError(f"unknown PROVIDER: {PROVIDER!r}")

# --- Your turn ---
# Fix the schema from 04: instead of a dict, define a small typed record
# with an id and a description field, and use a list of those. Make sure
# the model forbids unexpected extra fields. Run it and confirm you get a
# clean list of {id, description} objects.
