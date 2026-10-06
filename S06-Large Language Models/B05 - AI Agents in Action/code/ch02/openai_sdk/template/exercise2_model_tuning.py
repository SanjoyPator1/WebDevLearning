# ============================================================
# EXERCISE 2: Tune the model for determinism.
# REF: Chapter 2, §2.5 Exercise 2
# PROVIDERS: gemini (default) or ollama — see switch below
# GOTCHA: if you switch to ollama, qwen3:8b's thinking mode can burn the
#         whole max_tokens=150 budget on reasoning and return an EMPTY
#         final_output. If that happens, that's why.
# ============================================================

import os

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

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
# Pin the model and set temperature=0.0, max_tokens=150. Run it twice and
# save both outputs. Then raise temperature to 1.0 and run a third time.
# At the bottom of this file, write a short comment on which lines changed
# between runs and which stayed the same.
