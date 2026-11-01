# ============================================================
# LISTING: 04_a_plan_and_execute_simple.py  (companion file -- FROM SCRATCH, no agents SDK)
# BUILDING: Plan-and-execute, with replanning, stripped to the smallest
#           version that still teaches the real idea. No dual budgets, no
#           flight-leg jargon, no index-splicing bookkeeping. The task:
#           plan a 3-item grocery trip (milk, eggs, bread) under a $20
#           budget. Eggs come back at a real price far above what the
#           planner expected (a price spike); the mismatch is caught by
#           plain code, never a model opinion, and triggers calling the
#           SAME planner again for just the remaining items, with the new
#           fact and the budget that's actually left.
# REF: Chapter 5 notes, section 5 (Planning Ahead: High-Level Plans and
#      Plan-and-Execute) -- same pattern as 04_plan_and_execute.py, with
#      the incidental bookkeeping removed.
# COMPARE: 04_plan_and_execute.py in this same folder applies the
#      identical shape (plan -> execute -> check -> replan) to a 3-leg
#      flight trip with two budgets and position-based outcome lookups
#      that need careful re-indexing after every replan. Once this file
#      makes sense, that one is the same idea with messier real-world
#      bookkeeping around it, not a different idea.
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The one simplification worth calling out explicitly: _actual_prices is
# keyed by ITEM NAME, not by position in the plan. In 04_plan_and_execute.py,
# _actual_outcomes is keyed by list index, so after a replan rebuilds the
# step list, the code has to carefully carry forward "which original leg
# was this." Here, a revised step for "bread" is still just "bread" --
# whatever position it ends up at in a rebuilt list, execute_step(step)
# looks its real price up by step.item, so no index ever needs to be
# tracked across a replan at all.

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

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

GROCERY_BUDGET = 20.0
SHOPPING_LIST = ["milk", "eggs", "bread"]


class PlanStep(BaseModel):
    """One line item of a plan -- real structured data, not prose, so the
    executor and the mismatch-check code can read it directly."""

    item: str
    expected_price: float


class ShoppingPlan(BaseModel):
    """The planner's full output type: an ordered list of PlanSteps.
    Nothing here decides what anything actually costs -- only what the
    planner currently expects."""

    steps: list[PlanStep]


PLANNER_SYSTEM_PROMPT = f"""
You are planning a grocery shopping trip for exactly these items, in this
order: {", ".join(SHOPPING_LIST)}. Typical prices for these items are
around $4 each. Produce one step per item, each with the item name and
its expected_price, totaling comfortably within a ${GROCERY_BUDGET:.0f}
budget. You do not buy anything yourself -- you only decide the plan.

If you are asked to REVISE a plan because an item's actual price came
back different than expected, produce a new plan covering ONLY the
remaining items you are told about, using the new fact you were given and
staying within whatever budget remains.

Respond with ONLY a JSON object matching this shape, no other text:
{{"steps": [{{"item": "...", "expected_price": <number>}}, ...]}}
""".strip()

# --- Fixed "what things actually cost" for this demo, keyed by ITEM NAME
# (not position -- see the module docstring above for why that matters).
# Eggs are deliberately the one with a real price far above anything a
# planner would reasonably expect, mirroring a real price spike.
_actual_prices = {
    "milk": 4.00,
    "eggs": 9.00,  # the surprise: a planner will expect roughly $4
    "bread": 4.00,
}


async def execute_step(step: PlanStep) -> dict:
    """The 'executor': find out what one planned item actually costs. In a
    real system this would call a checkout/pricing tool; here the price is
    a fixed lookup by item name, so the mismatch is reproducible."""
    # your turn:
    #   1. look up the real price in _actual_prices by step.item
    #   2. print a line showing the item, its expected_price, and the
    #      actual_price you just looked up
    #   3. return {"item": step.item, "expected_price": step.expected_price,
    #              "actual_price": <the looked-up price>}
    raise NotImplementedError


async def call_planner(user_prompt: str) -> ShoppingPlan:
    """One raw chat-completions call that plays the planner's role, with
    no tools: the JSON shape ShoppingPlan expects is spelled out in
    PLANNER_SYSTEM_PROMPT, and the response text is parsed with
    json.loads and validated with ShoppingPlan.model_validate. This same
    function is used for the original plan AND every later replan -- only
    the user_prompt changes."""
    # your turn:
    #   1. call client.chat.completions.create with PLANNER_SYSTEM_PROMPT
    #      as the system message and user_prompt as the user message (no
    #      tools)
    #   2. pull the raw text out of the response
    #   3. json.loads it, then ShoppingPlan.model_validate(...) it, inside
    #      a try/except (json.JSONDecodeError, ValueError) that prints a
    #      clear error plus the raw text and re-raises on failure
    #   4. return the validated ShoppingPlan
    raise NotImplementedError


async def run_shopping_trip() -> None:
    """Plan once, execute steps in order, check each against the plan with
    plain Python, and replan -- calling the SAME planner again -- the
    moment a step's actual price doesn't match what was planned."""
    # your turn:
    #   STEP 1: call_planner(...) with a prompt asking it to plan a trip
    #     for SHOPPING_LIST within GROCERY_BUDGET. Print each planned step
    #     and the planned total vs. the budget (and headroom).
    #
    #   STEP 2: walk the steps with a plain `while i < len(current_steps)`
    #     loop (NOT a for loop -- you need to be able to replace the rest
    #     of the list mid-walk after a replan). For each step:
    #       a. await execute_step(step), add its actual_price to a running
    #          total_spent
    #       b. check `abs(actual_price - expected_price) < 0.01`
    #       c. if it matches: print MATCH, do `i += 1`, `continue`
    #       d. if it does NOT match: print MISMATCH with the difference,
    #          then go to STEP 3 below
    #
    #   STEP 3 (only on a mismatch): build `remaining_items` from
    #     `current_steps[i + 1:]` (their .item names), compute
    #     `budget_remaining = GROCERY_BUDGET - total_spent`, print both.
    #     Build a replan_prompt string that explicitly states: the item
    #     that surprised you, its expected vs actual price, the list of
    #     remaining_items, and budget_remaining. Call
    #     `await call_planner(replan_prompt)` to get a revised ShoppingPlan,
    #     print its steps. Then splice it in:
    #       current_steps = current_steps[: i + 1] + revised_plan.steps
    #     (no index remapping needed -- see the module docstring) and
    #     `i += 1` to move past the step that just ran.
    #
    #   STEP 4: after the while loop ends, print the final tally:
    #     total_spent vs. GROCERY_BUDGET, and whether it finished within
    #     or over budget.
    raise NotImplementedError


async def main() -> None:
    """Entry point: print a header, then run the one demo."""
    # your turn: print a header banner, then `await run_shopping_trip()`
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
