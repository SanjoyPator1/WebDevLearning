# ============================================================
# LISTING: 04_output_types.py  (reference implementation)
# BUILDING: A DELIBERATELY BROKEN version of 03's schema — meant to fail.
# REF: Chapter 2, listing 2.7 (the "before")
# PROVIDERS: gemini (default) or ollama — see switch below
# NOTE: the failure here is raised by the SDK's own schema builder BEFORE
#       any network call — it reproduces identically regardless of provider.
#       Fixed in 05_output_types_fixed.py.
# ============================================================

import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

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
# Try changing `tasks` to a dict keyed by task number instead of a list.
# Wire it into output_type the same way as 03. Run it — expect an error
# before any request is even sent. Read the error message carefully; it
# tells you exactly what's disallowed and why.
