# ============================================================
# LISTING: 02_setting_agent_model_parameters.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: The same Research Planner persona as 01, but now with explicit
#           sampling parameters, and run twice in a row to show firsthand
#           that temperature=0.0 reduces output variance, it does not
#           eliminate it.
# REF: Chapter 2 notes, section 4 (The Sampling Knobs) and section 7
#      (Building the Agent)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/02_setting_agent_model_parameters.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# The SDK version wraps temperature/max_tokens in a ModelSettings(...)
# dataclass passed to Agent(model_settings=...). This file makes visible
# that ModelSettings is not a special mechanism -- it is a plain
# dataclass whose fields get unpacked into the exact same keyword
# arguments shown below, on the exact same chat.completions.create call.
# There is no additional enforcement, translation, or validation layer:
# `ModelSettings(temperature=0.0, max_tokens=150)` IS
# `temperature=0.0, max_tokens=150` as literal kwargs here.

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

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

# --- Your turn ---
# Build the same messages list as 01 (system=instructions, user="learn
# about AI agents").
#
# Call chat.completions.create TWICE in a row, passing
# `temperature=0.0, max_tokens=150` as plain keyword arguments both times
# -- this pair of kwargs is exactly what ModelSettings(temperature=0.0,
# max_tokens=150) unpacks into in the SDK version; there is no extra
# translation step happening in between.
#
# Print both raw response texts side by side and compare them. Per the
# notes' section 4 dry run: even at T=0, providers clamp to a tiny
# nonzero temperature rather than true 0, so there is still a nonzero
# probability mass on the second-best token at every generation step --
# expect the two outputs to often agree on the first few tasks and
# diverge on a later one, not be byte-identical.
#
# Wrap everything in `async def main(): ...` and run with
# `asyncio.run(main())` under `if __name__ == "__main__":`.
