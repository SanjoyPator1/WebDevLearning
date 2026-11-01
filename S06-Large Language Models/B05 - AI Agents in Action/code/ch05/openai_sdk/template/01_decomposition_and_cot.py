# ============================================================
# LISTING: 01_decomposition_and_cot.py  (reference implementation)
# BUILDING: Two ideas from the start of Chapter 5, kept separate on purpose:
#           1. DECOMPOSITION as its own inspectable step -- turning one
#              goal ("book my 3-city conference trip") into a list of
#              subproblems, with no ordering decided yet.
#           2. CHAIN-OF-THOUGHT prompting -- the same budget-arithmetic
#              question asked two ways against the same non-reasoning
#              model, once with no scaffolding and once with an explicit
#              "add the legs one at a time" instruction, to show the same
#              model reach a different (correct) answer once the working
#              is forced into the open.
# REF: Chapter 5 notes, section 1 (Reasoning and Planning as Distinct
#      Operations) and section 2 (Chain-of-Thought and the Rise of
#      Reasoning Models)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# Decomposition answers "what are the pieces?" and nothing more -- it does
# not sequence them, that's planning's job and belongs elsewhere. Keeping
# decomposition_agent from ever touching ordering is deliberate: it lets
# you inspect a decomposition failure (a missing subproblem) completely
# separately from a planning failure (a bad order over a correct list).
#
# The budget dry run reuses the exact numbers from the chapter notes'
# own CoT dry run ($420 + $310 + $275 against a $950 cap) so you can put
# this file's printed output side by side with the notes and see the same
# arithmetic land in the same place.

import asyncio
import os

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    set_tracing_disabled,
)
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()
set_tracing_disabled(True)  # no real OpenAI key -> no trace export attempts

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

model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)

# These three leg prices and this budget are the exact figures used in the
# chapter notes' own chain-of-thought dry run -- $420 + $310 + $275 =
# $1,005, which is $55 OVER the $950 cap. Kept as plain Python constants,
# never as text the model has to retype, so the "ground truth" for grading
# the model's answer never depends on the model itself.
FLIGHT_LEG_PRICES = [420.0, 310.0, 275.0]
TRAVEL_BUDGET = 950.0


class TripSubproblems(BaseModel):
    """Structured output for the decomposition step -- a flat list of
    pieces, with NO ordering or dependency information attached. That is
    planning's job, handled in a later file, not here."""

    subproblems: list[str]


decomposition_agent = Agent(
    name="Decomposition Agent",
    instructions="""
    You are given a one-line trip-booking goal. Break it into the distinct
    subproblems it is made of -- for example flights, hotel, and visa, if
    the destination needs one. Do NOT decide what order to do them in and
    do NOT say anything about dependencies between them; just list the
    pieces. If a subproblem clearly does not apply (e.g. no visa needed),
    leave it out rather than including it as "not needed".
    """,
    model=model,
    output_type=TripSubproblems,
)

# Same underlying model, asked the identical budget question two different
# ways -- the contrast is the whole point of this file, not the agent.
budget_check_agent_plain = Agent(
    name="Budget Check Agent (no scaffolding)",
    instructions="""
    You are given a list of flight leg prices and a travel budget. Answer
    directly: state the total and whether it is within budget. Keep your
    answer short.
    """,
    model=model,
)

budget_check_agent_cot = Agent(
    name="Budget Check Agent (chain-of-thought)",
    instructions="""
    You are given a list of flight leg prices and a travel budget. Add the
    leg costs ONE AT A TIME, showing the running total after each leg, then
    compare the final running total to the budget. Show every step before
    giving your final answer.
    """,
    model=model,
)

# --- Your turn ---
# Write an async main() that does the following, printing a short label
# before each step so the output reads top to bottom:
#
#   1. Run decomposition_agent on the goal string below via Runner.run(...).
#      Its result.final_output is a TripSubproblems (a `subproblems` list
#      of strings) -- print the list so decomposition is visible as its
#      own, separate step.
#
#   2. Build a plain-English prompt describing the three FLIGHT_LEG_PRICES
#      and the TRAVEL_BUDGET (e.g. "Leg prices: $420, $310, $275. Budget:
#      $950. What's the total, and is this within budget?") and run it
#      against budget_check_agent_plain via Runner.run(...). Print the
#      raw final_output text.
#
#   3. Run the SAME prices-and-budget facts (same numbers, same prompt
#      content) against budget_check_agent_cot via Runner.run(...). Print
#      the raw final_output text -- it should show the running-total
#      arithmetic explicitly.
#
#   4. Print a short side-by-side comparison: compute the TRUE total and
#      over/under-budget amount yourself in plain Python (sum(FLIGHT_LEG_PRICES)
#      vs TRAVEL_BUDGET) and state it next to what each agent said, so a
#      reader can see whether the plain prompt got the arithmetic right or
#      wrong compared to the chain-of-thought prompt.

goal = "book my 3-city conference trip"

if __name__ == "__main__":
    asyncio.run(main())
