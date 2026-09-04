# ============================================================
# LISTING: 02_setting_agent_model_parameters.py  (reference implementation)
# BUILDING: Same Research Planner, now with an explicit model and
#           ModelSettings (temperature, max_tokens, top_p,
#           frequency_penalty, presence_penalty) for repeatability.
# REF: Chapter 2, §2.3
# PROVIDERS: gemini (default) or ollama — see switch below
# GOTCHA: if you switch to ollama, qwen3:8b's thinking mode can burn the
#         whole max_tokens=150 budget on reasoning and return an empty
#         final_output. If output is empty, that's why.
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
# Same persona as 01. This time, pin the model explicitly and tune generation
# for repeatability: temperature near 0, and a token ceiling around 150.
# Run it twice and compare the two outputs — they won't be byte-identical.
