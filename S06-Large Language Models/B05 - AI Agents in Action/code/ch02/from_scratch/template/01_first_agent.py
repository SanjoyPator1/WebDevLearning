# ============================================================
# LISTING: 01_first_agent.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: The minimal possible agent, with no SDK underneath it -- one
#           system message (the "Research Planner" persona), one user
#           message (a topic), one chat.completions.create call, printed.
# REF: Chapter 2 notes, section 7 (Building the Agent)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/01_first_agent.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# The SDK version of this file constructs an Agent(instructions=...,
# model=...) and calls Runner.run_sync(agent, input=...). This file makes
# visible exactly what those two calls were doing underneath: there is no
# hidden orchestration layer. Agent.instructions IS the system message.
# Runner.run_sync(agent, input=X) IS building
# messages=[{"role": "system", "content": agent.instructions},
#           {"role": "user", "content": X}]
# and calling chat.completions.create(model=..., messages=messages).
# result.final_output IS response.choices[0].message.content. Nothing
# else happens underneath for a plain, tool-less, typed-output-less agent
# -- this file is the proof.

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

# This string is the ENTIRE persona layer -- exactly what `instructions=`
# would be handed to Agent() in the SDK version. It never mentions
# `client`, `PROVIDER`, or anything provider-specific: the persona is
# completely decoupled from which backend answers it.
instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""

# --- Your turn ---
# Build the messages list by hand: a "system" message using `instructions`
# above, and a "user" message with the topic "learn about AI agents".
# This messages list IS what Runner.run_sync(agent, input="learn about AI
# agents") builds internally before it ever touches the network.
#
# Call `await client.chat.completions.create(model=MODEL_NAME, messages=messages)`.
# Pull `response.choices[0].message.content` out of the result -- this is
# the raw-API equivalent of `result.final_output` -- and print it.
#
# Wrap the call in an `async def main(): ...` and run it with
# `asyncio.run(main())` under `if __name__ == "__main__":` (you'll need
# to `import asyncio` at the top alongside the other imports).
