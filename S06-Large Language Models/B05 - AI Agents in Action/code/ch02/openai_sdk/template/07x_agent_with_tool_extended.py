# ============================================================
# LISTING: 07x_agent_with_tool_extended.py  (reference implementation)
# BUILDING: Same idea as 07, but the tool returns structured objects
#           instead of plain strings.
# REF: Chapter 2, §2.5 (extended variant)
# PROVIDERS: gemini (default) or ollama — see switch below
# ============================================================

import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
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
# Same idea as 07, but instead of the tool returning plain strings, have it
# return a small structured record per source (e.g. just a name field for
# now). Update your task schema to hold that structured source instead of
# a bare string.
