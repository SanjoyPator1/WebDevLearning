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


async def main():
    print("=" * 60)
    print("PART 1: Decomposition as its own, separate step")
    print("=" * 60)

    print(f"\nSTEP 1: Decomposition Agent breaks down the goal")
    print(f'    goal: "{goal}"')
    decomposition_result = await Runner.run(decomposition_agent, goal)
    subproblems: TripSubproblems = decomposition_result.final_output
    print(f"    subproblems found: {subproblems.subproblems}")
    print(
        "    Note: no ordering was decided here -- decomposition only "
        "answers 'what are the pieces?', not 'in what order?'"
    )

    print("\n" + "=" * 60)
    print("PART 2: Same budget question, with and without chain-of-thought")
    print("=" * 60)

    budget_facts = (
        f"Leg prices: ${FLIGHT_LEG_PRICES[0]:.0f}, ${FLIGHT_LEG_PRICES[1]:.0f}, "
        f"${FLIGHT_LEG_PRICES[2]:.0f}. Budget: ${TRAVEL_BUDGET:.0f}. "
        "What's the total, and is this within budget?"
    )
    print(f"\nSTEP 2: Prompt sent to BOTH agents (identical facts):\n    {budget_facts!r}")

    print("\nSTEP 3: Budget Check Agent (no scaffolding) answers directly")
    plain_result = await Runner.run(budget_check_agent_plain, budget_facts)
    plain_answer = plain_result.final_output
    print(f"    raw response:\n    {plain_answer}")

    print("\nSTEP 4: Budget Check Agent (chain-of-thought) adds legs one at a time")
    cot_result = await Runner.run(budget_check_agent_cot, budget_facts)
    cot_answer = cot_result.final_output
    print(f"    raw response:\n    {cot_answer}")

    print("\nSTEP 5: Ground truth, computed in plain Python (not a model call)")
    true_total = sum(FLIGHT_LEG_PRICES)
    difference = true_total - TRAVEL_BUDGET
    status = f"${difference:.2f} OVER budget" if difference > 0 else f"${-difference:.2f} under budget"
    print(f"    sum(FLIGHT_LEG_PRICES) = {' + '.join(f'${p:.0f}' for p in FLIGHT_LEG_PRICES)} = ${true_total:.2f}")
    print(f"    ${true_total:.2f} vs ${TRAVEL_BUDGET:.2f} budget -> {status}")

    print("\n" + "=" * 60)
    print("SIDE-BY-SIDE: what changed between the two prompts")
    print("=" * 60)
    print(f"    Ground truth:              {status}")
    print(f"    Plain prompt (no CoT):      may eyeball the total and answer wrong or right by luck --")
    print(f"                                see 'raw response' above, nothing forced the arithmetic")
    print(f"                                to happen visibly before the answer was given")
    print(f"    Chain-of-thought prompt:    forced to show '${FLIGHT_LEG_PRICES[0]:.0f} + "
          f"${FLIGHT_LEG_PRICES[1]:.0f} + ${FLIGHT_LEG_PRICES[2]:.0f} = ${true_total:.2f}' as a")
    print(f"                                visible running total before comparing to the ${TRAVEL_BUDGET:.0f} cap")
    print(
        "    Same model, same weights, same underlying arithmetic ability in both calls -- "
        "the only difference was whether the intermediate sum was forced into the open."
    )


goal = "book my 3-city conference trip"

if __name__ == "__main__":
    asyncio.run(main())
