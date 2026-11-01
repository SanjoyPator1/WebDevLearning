# ============================================================
# LISTING: 04_plan_and_execute.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: The planner/executor split -- one raw chat-completions call
#           for planning plus plain Python orchestration code --
#           mirroring the notes' own brittle-plan dry run: a $2,400 total
#           budget with $700 reserved for three flight legs planned at
#           $180/$210/$260 (total $650, $50 headroom). Leg two comes back
#           sold out at its planned price with a $410 connecting-flight
#           replacement, exactly like the notes' dry run. Each executed
#           step's actual cost is checked against the plan's expected cost
#           with a DETERMINISTIC plain-Python comparison (never a model
#           judgment); a mismatch triggers calling the planner AGAIN with
#           the new fact, asking for a revised plan over the remaining
#           steps and whatever budget is left -- this is the fix for the
#           brittle-plan failure mode the notes describe.
# REF: Chapter 5 notes, section 5 (Planning Ahead: High-Level Plans and
#      Plan-and-Execute)
# COMPARE: the SDK version of this file at ../../openai_sdk/solved/04_plan_and_execute.py
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The SDK version got a validated TripPlan back "for free" via
# Agent(output_type=TripPlan) -- Runner.run() handled turning the model's
# text into that Pydantic object invisibly, on both the original planning
# call AND the replanning call. Here call_planner() does that step
# explicitly: it puts the exact JSON shape TripPlan expects into the
# system prompt, makes a plain chat-completions call with no tools, and
# parses+validates the response text itself, wrapped in a try/except that
# fails loudly instead of silently if the model didn't comply. Calling it
# twice (once to plan, once to replan) makes visible that "replanning" is
# not a special SDK feature -- it's the exact same function called again
# with a different prompt.

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

# Matches the notes' brittle-plan dry run exactly: $2,400 total trip
# budget, $700 of it reserved for the three flight legs.
TOTAL_TRIP_BUDGET = 2400.0
FLIGHT_LEGS_BUDGET = 700.0

# Planned leg costs the notes use: $180 + $210 + $260 = $650, leaving $50
# of headroom against the $700 flight budget. These figures are also
# baked into PLANNER_SYSTEM_PROMPT below, since the planner is the
# component that is supposed to arrive at this plan on its own.


class PlanStep(BaseModel):
    """One line item of a plan -- real structured data, not prose, so the
    executor and the mismatch-check code can read it directly."""

    step_description: str
    expected_cost: float


class TripPlan(BaseModel):
    """The planner's full output type -- an ordered list of PlanSteps.
    Nothing here decides HOW a step gets carried out, only what it is and
    what it should cost."""

    steps: list[PlanStep]


PLANNER_SYSTEM_PROMPT = f"""
You plan a three-leg conference trip: city-a-to-city-b, then
city-b-to-city-c, then city-c-to-city-d. The flight budget for all three
legs combined is ${FLIGHT_LEGS_BUDGET:.0f}. Typical fares for these three
legs are around $180, $210, and $260 respectively. Produce an ordered
plan with one step per leg, each with a short step_description and its
expected_cost. You do not call any tools and you do not book anything --
you only decide the ordered plan.

If you are asked to REVISE a plan because a step came back at an
unexpected price, produce a new plan covering only the REMAINING steps,
using the new fact you were given and staying within whatever budget
remains.

Respond with ONLY a JSON object matching this shape, no other text:
{{"steps": [{{"step_description": "...", "expected_cost": <number>}}, ...]}}
""".strip()

# --- Fixed "what actually happens" outcomes for this demo, keyed by step
# index (0-based). Leg 2 (index 1) is deliberately the one that comes back
# at an unexpected price, mirroring the notes' dry run: sold out at the
# planned $210, cheapest alternative is a $410 connection.
_actual_outcomes = {
    0: {"description": "leg_1_city_a_to_city_b", "actual_cost": 180.0},
    1: {"description": "leg_2_city_b_to_city_c (connecting, planned direct sold out)", "actual_cost": 410.0},
    2: {"description": "leg_3_city_c_to_city_d", "actual_cost": 260.0},
}


async def execute_step(step_index: int, step: PlanStep) -> dict:
    """The 'executor': carry out one step of the plan and report what
    actually happened. For leg 2 specifically, this returns a higher
    price than planned (the leg is sold out at the planned fare, and the
    cheapest alternative is a $410 connection) -- everything else returns
    the expected price. In a real system this would call a booking tool;
    here the outcome is a fixed lookup so the mismatch is reproducible."""
    outcome = _actual_outcomes[step_index]
    result = {
        "step_description": step.step_description,
        "expected_cost": step.expected_cost,
        "actual_cost": outcome["actual_cost"],
        "detail": outcome["description"],
    }
    print(f"    [executor] ran step {step_index + 1} ({step.step_description!r}) -> {result}")
    return result


# --- Your turn ---
# Write:
#   1. An async call_planner(user_prompt: str) -> TripPlan that makes ONE
#      raw chat.completions.create call with NO tools: system prompt
#      PLANNER_SYSTEM_PROMPT (already defined above -- it spells out the
#      exact JSON shape a TripPlan must match), user content=user_prompt.
#      Parse response.choices[0].message.content with json.loads and
#      validate it into a TripPlan via .model_validate(...), wrapped in a
#      try/except that prints a clear error (including the raw text) and
#      re-raises if the model didn't comply. This same function gets
#      called again later for replanning -- only the prompt text differs.
#   2. An async run_trip_booking() -> None that:
#        a. STEP 1: calls call_planner(...) with a prompt describing the
#           three-leg trip and the $700 FLIGHT_LEGS_BUDGET. Prints every
#           step (description + expected_cost) and the planned total vs.
#           budget.
#        b. STEP 2: executes the plan's steps ONE AT A TIME, in order,
#           via execute_step(step_index, step) (already defined above).
#           After each executed step, run a DETERMINISTIC plain-Python
#           check: does result["actual_cost"] match
#           result["expected_cost"]? Print the comparison either way.
#        c. On a MATCH: advance to the next step of the current plan.
#        d. On a MISMATCH (leg 2, in this demo): do NOT blindly continue.
#           Compute the remaining flight budget (FLIGHT_LEGS_BUDGET minus
#           everything actually spent so far), call call_planner(...)
#           AGAIN with a prompt describing the new fact (leg 2's actual
#           cost vs. its planned cost) and asking for a revised plan over
#           the REMAINING steps within the remaining budget. Print the
#           revised plan, then splice its steps in and keep executing
#           from there (still going through execute_step and the same
#           check).
#        e. STEP 4: prints the total actually spent across all legs vs.
#           FLIGHT_LEGS_BUDGET, and whether the trip stayed within
#           budget.
#
# Then write an async main() that calls run_trip_booking().
async def call_planner(user_prompt: str) -> TripPlan:
    """One raw chat-completions call that plays the planner's role, with
    no tools: the JSON shape TripPlan expects is spelled out in
    PLANNER_SYSTEM_PROMPT, and the response text is parsed with
    json.loads and validated with TripPlan.model_validate. This same
    function is used for both the original plan and every later replan --
    only the user_prompt changes."""
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
        return TripPlan.model_validate(parsed_dict)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"    !! failed to parse planner response as TripPlan: {error}")
        print(f"    !! raw text was: {raw_text!r}")
        raise


async def run_trip_booking() -> None:
    """Runs the planner once, executes the plan step by step, checks each
    result against expectation with plain Python, and triggers a replan
    the moment a step's actual cost doesn't match what was planned."""

    print("STEP 1: Planner call produces the original plan")
    print(
        f"    context: ${TOTAL_TRIP_BUDGET:.2f} total trip budget, of which "
        f"${FLIGHT_LEGS_BUDGET:.2f} is reserved for the three flight legs "
        "(the rest covers hotels and other costs, not this file's concern)"
    )
    planning_prompt = (
        f"Plan the three-leg conference trip (city-a-to-city-b, "
        f"city-b-to-city-c, city-c-to-city-d) within the "
        f"${FLIGHT_LEGS_BUDGET:.0f} flight budget."
    )
    plan = await call_planner(planning_prompt)
    planned_total = sum(step.expected_cost for step in plan.steps)
    for i, step in enumerate(plan.steps, start=1):
        print(f"    step {i}: {step.step_description} -- expected ${step.expected_cost:.2f}")
    print(f"    planned total: ${planned_total:.2f} (budget: ${FLIGHT_LEGS_BUDGET:.2f}, "
          f"headroom: ${FLIGHT_LEGS_BUDGET - planned_total:.2f})")

    total_actual_spent = 0.0
    step_index = 0
    steps_to_run = list(enumerate(plan.steps))

    print("\nSTEP 2: Executing steps one at a time, checking each against the plan")
    while step_index < len(steps_to_run):
        original_index, step = steps_to_run[step_index]
        print(f"\n  -- executing step {step_index + 1}/{len(steps_to_run)} --")
        result = await execute_step(original_index, step)
        total_actual_spent += result["actual_cost"]

        matches = abs(result["actual_cost"] - result["expected_cost"]) < 0.01
        if matches:
            print(
                f"    [check] actual ${result['actual_cost']:.2f} == expected "
                f"${result['expected_cost']:.2f} -> MATCH, advancing to next step"
            )
            step_index += 1
            continue

        difference = result["actual_cost"] - result["expected_cost"]
        print(
            f"    [check] actual ${result['actual_cost']:.2f} != expected "
            f"${result['expected_cost']:.2f} -> MISMATCH (+${difference:.2f}). "
            "This is the brittle-plan trigger point: do NOT blindly continue "
            "the original plan."
        )

        remaining_steps = steps_to_run[step_index + 1:]
        budget_remaining = FLIGHT_LEGS_BUDGET - total_actual_spent
        print(
            f"\nSTEP 3: Replanning -- {len(remaining_steps)} step(s) remain, "
            f"${budget_remaining:.2f} of flight budget left "
            f"(${FLIGHT_LEGS_BUDGET:.2f} - ${total_actual_spent:.2f} spent so far)"
        )
        remaining_descriptions = ", ".join(s.step_description for _, s in remaining_steps)
        replan_prompt = (
            f"New fact: {result['step_description']} actually cost "
            f"${result['actual_cost']:.2f} instead of the planned "
            f"${result['expected_cost']:.2f} ({result['detail']}). "
            f"Remaining steps to replan: {remaining_descriptions}. "
            f"Remaining flight budget: ${budget_remaining:.2f}. "
            "Produce a revised plan covering only these remaining steps."
        )
        revised_plan = await call_planner(replan_prompt)
        for i, step in enumerate(revised_plan.steps, start=1):
            print(f"    revised step {i}: {step.step_description} -- expected ${step.expected_cost:.2f}")

        # Splice the revised steps in, keeping their original _actual_outcomes
        # indices so execute_step still looks up the right fixed outcome.
        remaining_original_indices = [idx for idx, _ in remaining_steps]
        steps_to_run = steps_to_run[: step_index + 1] + list(
            zip(remaining_original_indices, revised_plan.steps)
        )
        step_index += 1

    print("\n" + "=" * 60)
    print("STEP 4: Final tally")
    print("=" * 60)
    print(f"    total actually spent on flights: ${total_actual_spent:.2f}")
    print(f"    flight budget:                   ${FLIGHT_LEGS_BUDGET:.2f}")
    within_budget = total_actual_spent <= FLIGHT_LEGS_BUDGET
    print(
        f"    {'WITHIN BUDGET' if within_budget else 'OVER BUDGET'} by "
        f"${abs(FLIGHT_LEGS_BUDGET - total_actual_spent):.2f}"
    )

async def main():
    print("=" * 60)
    print("Plan-and-Execute: booking a 3-leg trip, replanning on a surprise")
    print("=" * 60)
    await run_trip_booking()


if __name__ == "__main__":
    asyncio.run(main())
