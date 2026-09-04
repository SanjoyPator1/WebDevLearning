# ============================================================
# EXERCISE 4: Apply prompt-engineering best practices.
# REF: Chapter 2, §2.5 Exercise 4 / table 2.2
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
# Rewrite the persona to use at least 4 distinct prompt-engineering
# techniques (pick from: clear persona/role, delimiters, a specific length
# limit, few-shot examples, chain-of-thought, positive phrasing, eliminating
# ambiguity). Wrap the task/topic block in a Markdown code fence as one of
# your delimiters. Keep temperature at 0. Run it twice and confirm each run
# gives exactly 5 tasks, each 7 words or fewer.
