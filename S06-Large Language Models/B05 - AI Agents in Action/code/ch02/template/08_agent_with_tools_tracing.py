# ============================================================
# LISTING: 08_agent_with_tools_tracing.py  (reference implementation)
# BUILDING: Two chained tools (the second depends on the first's output)
#           plus tracing, combined into one agent.
# REF: Chapter 2, §2.5-2.6 (tools + tracing)
# PROVIDERS: gemini (default) or ollama — see switch below
# NOT POSSIBLE HERE: no OpenAI dashboard without a real OpenAI key —
#       trace(...) is a no-op under set_tracing_disabled(True).
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
# Combine 07's tool-using agent with 06's tracing: add a second tool that
# looks up a URL for a given source name (it should depend on the first
# tool's output), register both tools, and wrap the run in a trace block.
# Afterward, print the run's step-by-step item types and confirm you see
# both tool calls before the final message.
