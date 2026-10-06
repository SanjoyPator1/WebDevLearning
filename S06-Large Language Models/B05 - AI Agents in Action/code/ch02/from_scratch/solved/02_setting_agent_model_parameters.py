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

import asyncio
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


async def run_planner_once(call_label: str) -> str:
    """One raw chat-completions call with explicit sampling parameters.
    `temperature=0.0, max_tokens=150` here are literal keyword arguments
    on the SAME underlying call ModelSettings(temperature=0.0,
    max_tokens=150) would have produced in the SDK version -- this
    function IS that dataclass's runtime effect, made explicit."""
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": "learn about AI agents"},
    ]
    print(f"  [{call_label}] calling chat.completions.create(temperature=0.0, max_tokens=150)")
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.0,
        max_tokens=150,
    )
    return response.choices[0].message.content


async def main():
    """Run the exact same temperature=0.0 call twice and compare the raw
    text side by side. Per the notes' section 4 dry run: dividing logits
    by a temperature that providers clamp to a tiny nonzero value (rather
    than true 0) still leaves a nonzero, if minuscule, probability on the
    second-best token at every generation step -- so five runs at
    temperature=0.0 on a five-task plan can agree on the first few tasks
    and still drift on a later one. temperature=0.0 REDUCES variance; it
    does not ELIMINATE it (chapter notes, section 6's pitfalls table
    makes the same point from the other direction)."""
    print("=" * 60)
    print("STEP 1: First call at temperature=0.0, max_tokens=150")
    print("=" * 60)
    first_output = await run_planner_once("call 1")
    print(f"  output:\n{first_output}")

    print("\n" + "=" * 60)
    print("STEP 2: Second call, identical parameters, identical prompt")
    print("=" * 60)
    second_output = await run_planner_once("call 2")
    print(f"  output:\n{second_output}")

    print("\n" + "=" * 60)
    print("STEP 3: Side-by-side comparison")
    print("=" * 60)
    print(f"  identical byte-for-byte? {first_output == second_output}")
    print("  (temperature=0.0 is clamped to a tiny nonzero T by the provider,")
    print("   not true 0 -- there is still nonzero probability mass on the")
    print("   second-best token at every step, which is exactly why these")
    print("   two outputs can diverge even though nothing else changed.)")


if __name__ == "__main__":
    asyncio.run(main())
