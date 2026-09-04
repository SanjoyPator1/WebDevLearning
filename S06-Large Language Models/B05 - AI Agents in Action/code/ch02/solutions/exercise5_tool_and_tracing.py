# ============================================================
# EXERCISE 5: Add an internal tool, and trace it.
# REF: Chapter 2, §2.5 Exercise 5
# PROVIDERS: gemini (default) or ollama — see switch below
# NOT POSSIBLE HERE: no OpenAI dashboard without a real OpenAI key —
#       set_tracing_disabled(True) makes trace(...) a safe no-op.
#       Substitute check below.
# ============================================================

import os

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
    trace,
)
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
# Add a tool that returns a hardcoded list of research sources, and update
# the persona so the first step is always to call it. Register the tool,
# wrap the run in a named trace block, and run it once. Since there's no
# real OpenAI dashboard here, confirm the tool ran before the final answer
# by printing the run result's step-by-step item types in order.
