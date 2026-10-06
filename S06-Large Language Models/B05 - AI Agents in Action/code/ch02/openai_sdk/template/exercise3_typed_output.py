# ============================================================
# EXERCISE 3: Enforce strictly typed output.
# REF: Chapter 2, §2.5 Exercise 3
# PROVIDERS: gemini (default) or ollama — see switch below
# NOTE: the schema error in step 1 is raised by the SDK's own schema
#       builder before any network call — it reproduces identically
#       regardless of provider.
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
# Step 1: give the agent a typed output where tasks is a dict keyed by an
# int id. Run it and read the error you get.
# Step 2: fix it by switching to a list of a small typed record (id +
# description) instead of a dict. Run it again and confirm you get a clean
# list of 5 {id, description} objects.
