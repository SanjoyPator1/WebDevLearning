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

# Agent Instructions
instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""

agent = Agent(
    name="Research Planner",
    instructions=instructions,
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
        model_settings=ModelSettings(
            temperature=0.0,
            max_tokens=150,
            top_p=1.0,
            frequency_penalty=0.5,
            presence_penalty=0.5
        )
)

# agent = Agent(
#     name="Research Planner", 
#     instructions=instructions,
#     model="gpt-4.1",  # Specify the model to use
#     model_settings=ModelSettings(
#         temperature=0.0,  # Set the temperature for repeatability
#         max_tokens=150,  # Set the maximum number of tokens in the response
#         top_p=1.0,  # Set the top-p sampling parameter
#         frequency_penalty=0.5,  # Set the frequency penalty
#         presence_penalty=0.5,  # Set the presence penalty
#     )
# )

input = "learn about AI agents"

result = Runner.run_sync(
    agent, 
    input=input,
    )

print(result.final_output)