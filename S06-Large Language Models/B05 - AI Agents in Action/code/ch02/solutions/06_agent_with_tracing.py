# ============================================================
# LISTING: 06_agent_with_tracing.py  (reference implementation)
# BUILDING: The fixed structured-output agent from 05, wrapped in a
#           named trace block.
# REF: Chapter 2, §2.3.4 / listing 2.10
# PROVIDERS: gemini (default) or ollama — see switch below
# NOT POSSIBLE HERE: there's no OpenAI dashboard to view without a real
#       OpenAI key — `set_tracing_disabled(True)` makes the trace block a
#       harmless no-op instead of erroring. Substitute check below.
# ============================================================

import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled, trace
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

load_dotenv()
set_tracing_disabled(True)  # trace(...) below becomes a no-op, safe to keep

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
# Take the fixed agent from 05 and wrap the run in a named trace block.
# Since there's no real OpenAI dashboard here, tracing is a no-op — instead,
# after the run, loop over the run result's step-by-step items and print
# their types, to see the shape of what happened.
