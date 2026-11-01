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
    actual_price = _actual_prices[step.item]
    result = {"item": step.item, "expected_price": step.expected_price, "actual_price": actual_price}
    print(f"    [executor] bought {step.item!r} -> expected ${step.expected_price:.2f}, actual ${actual_price:.2f}")
    return result


async def call_planner(user_prompt: str) -> ShoppingPlan:
    """One raw chat-completions call that plays the planner's role, with
    no tools: the JSON shape ShoppingPlan expects is spelled out in
    PLANNER_SYSTEM_PROMPT, and the response text is parsed with
    json.loads and validated with ShoppingPlan.model_validate. This same
    function is used for the original plan AND every later replan -- only
    the user_prompt changes."""
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw_text = response.choices[0].message.content
    try:
        parsed_dict = json.loads(raw_text)
        return ShoppingPlan.model_validate(parsed_dict)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"    !! failed to parse planner response as ShoppingPlan: {error}")
        print(f"    !! raw text was: {raw_text!r}")
        raise


async def run_shopping_trip() -> None:
    """Plan once, execute steps in order, check each against the plan with
    plain Python, and replan -- calling the SAME planner again -- the
    moment a step's actual price doesn't match what was planned."""

    print("STEP 1: Planner call produces the original plan")
    plan = await call_planner(
        f"Plan a trip to buy {', '.join(SHOPPING_LIST)} within a ${GROCERY_BUDGET:.0f} budget."
    )
    planned_total = sum(step.expected_price for step in plan.steps)
    for i, step in enumerate(plan.steps, start=1):
        print(f"    step {i}: {step.item} -- expected ${step.expected_price:.2f}")
    print(f"    planned total: ${planned_total:.2f} (budget: ${GROCERY_BUDGET:.2f}, "
          f"headroom: ${GROCERY_BUDGET - planned_total:.2f})")

    total_spent = 0.0
    current_steps = plan.steps
    i = 0

    print("\nSTEP 2: Executing steps one at a time, checking each against the plan")
    while i < len(current_steps):
        step = current_steps[i]
        print(f"\n  -- step {i + 1}/{len(current_steps)} --")
        result = await execute_step(step)
        total_spent += result["actual_price"]

        matches = abs(result["actual_price"] - result["expected_price"]) < 0.01
        if matches:
            print(
                f"    [check] actual ${result['actual_price']:.2f} == expected "
                f"${result['expected_price']:.2f} -> MATCH, advancing"
            )
            i += 1
            continue

        difference = result["actual_price"] - result["expected_price"]
        print(
            f"    [check] actual ${result['actual_price']:.2f} != expected "
            f"${result['expected_price']:.2f} -> MISMATCH (+${difference:.2f}). "
            "Do NOT blindly continue the original plan."
        )

        remaining_items = [s.item for s in current_steps[i + 1:]]
        budget_remaining = GROCERY_BUDGET - total_spent
        print(
            f"\nSTEP 3: Replanning -- {len(remaining_items)} item(s) remain, "
            f"${budget_remaining:.2f} of budget left"
        )
        replan_prompt = (
            f"New fact: {step.item} actually cost ${result['actual_price']:.2f} "
            f"instead of the planned ${result['expected_price']:.2f}. "
            f"Remaining items to replan: {', '.join(remaining_items)}. "
            f"Remaining budget: ${budget_remaining:.2f}. "
            "Produce a revised plan covering only these remaining items."
        )
        revised_plan = await call_planner(replan_prompt)
        for j, revised_step in enumerate(revised_plan.steps, start=1):
            print(f"    revised step {j}: {revised_step.item} -- expected ${revised_step.expected_price:.2f}")

        # No index bookkeeping needed: each revised step still names its own
        # item, so execute_step() will find the right real price regardless
        # of where it now sits in the list.
        current_steps = current_steps[: i + 1] + revised_plan.steps
        i += 1

    print("\n" + "=" * 60)
    print("STEP 4: Final tally")
    print("=" * 60)
    print(f"    total actually spent: ${total_spent:.2f}")
    print(f"    budget:               ${GROCERY_BUDGET:.2f}")
    within_budget = total_spent <= GROCERY_BUDGET
    print(
        f"    {'WITHIN BUDGET' if within_budget else 'OVER BUDGET'} by "
        f"${abs(GROCERY_BUDGET - total_spent):.2f}"
    )


async def main():
    print("=" * 60)
    print("Plan-and-Execute, the simplest possible version")
    print("=" * 60)
    await run_shopping_trip()


if __name__ == "__main__":
    asyncio.run(main())
