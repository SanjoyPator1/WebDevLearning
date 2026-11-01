# ============================================================
# LISTING: 06_reflexion_with_verifier.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: A Reflexion solver-critic loop where the critic is NOT the
#           solver re-reading its own work -- it is a deterministic
#           verifier that recomputes the itinerary total directly from the
#           raw leg prices. Feedback from a failed verification is fed
#           back into the next attempt WITHOUT any special "dynamic
#           instructions" mechanism at all -- see the COMPARE note below.
# REF: Chapter 5 notes, section 7 (Reflexion and Independent Verifiers:
#      Self-Critique That Actually Works)
# COMPARE: the SDK version of this file at ../../openai_sdk/solved/06_reflexion_with_verifier.py
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The SDK version's dynamic instructions trick -- a callable passed as
# `instructions=`, which the SDK invokes fresh on every Runner.run with a
# RunContextWrapper it can read `.context` off of -- makes "dynamic
# instructions" look like a distinct framework feature with its own
# object (RunContextWrapper) and its own calling convention. This file
# makes the trick fully transparent: THERE IS NO SPECIAL MECHANISM. Every
# retry attempt just builds a brand-new system-prompt string in plain
# Python, string-concatenating the previous attempt's feedback onto the
# end when there is any, and hands that fresh string straight to
# chat.completions.create(). "Dynamic instructions" in the SDK never did
# anything more than this -- it only LOOKED like more because it was
# hidden behind a callable and a context object.
#
# The notes' own dry run is reused directly: a $1,800 flight budget, and
# three legs that -- if the solver books the "obvious" nonstop option on
# every leg -- price out to $650 + $590 + $610 = $1,850, exactly $50 over
# budget. verify_itinerary_total() never trusts anything the solver claims
# about its own total; it re-adds the raw leg_prices every single time,
# which is the whole reason this verifier is trustworthy where asking the
# solver to grade its own homework would not be.

# NOTE: we do a normal llm call at first and get its proposed leg prices.
# the verifier recomputes the total from those prices and checks it
# against the budget rule (no answer key, just a pass/fail rule).
# if it fails, we build feedback describing the failure and feed it into
# the prompt for the next llm call.

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

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

MAX_ATTEMPTS = 4
TOTAL_FLIGHT_BUDGET_USD = 1_800.0
LEG_NAMES = ["Leg A (home -> City 1)", "Leg B (City 1 -> City 2)", "Leg C (City 2 -> home)"]

# Fixed fare data for this demo -- the same shape a real search_flights
# tool would hand back. Only Leg B has a second, cheaper option, which is
# what makes the second Reflexion attempt able to actually fix the
# overage instead of being stuck repeating the same $50-over itinerary.
LEG_OPTIONS = {
    "Leg A (home -> City 1)": [
        {"price_usd": 650.0, "description": "nonstop, preferred departure time"},
    ],
    "Leg B (City 1 -> City 2)": [
        {"price_usd": 590.0, "description": "nonstop, preferred departure time"},
        {"price_usd": 460.0, "description": "one-stop connection, adds ~2h but meets all date constraints"},
    ],
    "Leg C (City 2 -> home)": [
        {"price_usd": 610.0, "description": "nonstop, preferred departure time"},
    ],
}


def format_leg_options(leg_options: dict) -> str:
    """Render the fixed fare data as plain text for the solver's prompt --
    plain Python string formatting, not something a model needs to do."""
    lines = []
    for leg_name, options in leg_options.items():
        lines.append(f"{leg_name}:")
        for option in options:
            lines.append(f"  - ${option['price_usd']:.0f}: {option['description']}")
    return "\n".join(lines)


class SolverOutput(BaseModel):
    """Structured output for the solver. Extracting the three per-leg
    prices this way means the retry loop can call
    verify_itinerary_total() directly on solver.leg_prices -- no regex
    parsing of prose required, and no self-reported total to be misled
    by, since this model doesn't even ask for one."""

    leg_prices: list[float]  # one price per leg, in leg order (A, B, C)
    reasoning: str


def verify_itinerary_total(leg_prices: list[float], budget: float) -> dict:
    """Independent verifier: recomputes the itinerary total DIRECTLY from
    the raw leg prices, never trusting any total the solver itself might
    claim. Deterministic, no model call -- this groundedness is exactly
    what makes a verifier trustworthy where self-critique is not (chapter
    notes, section 7).

    Returns a dict with the recomputed total, whether it passes, how far
    over budget it is if it fails, and which leg is currently the priciest.
    """
    recomputed_total = sum(leg_prices)
    passes = recomputed_total <= budget
    overage = max(0.0, recomputed_total - budget)
    most_expensive_leg_index = leg_prices.index(max(leg_prices))
    return {
        "recomputed_total": recomputed_total,
        "passes": passes,
        "overage": overage,
        "most_expensive_leg_index": most_expensive_leg_index,
    }


def build_solver_prompt(feedback: str) -> str:
    """Build a fresh system-prompt string for one solver attempt. THIS
    function is the entirety of "dynamic instructions" without the SDK --
    no callable stashed on an Agent, no RunContextWrapper, just a plain
    function called by hand before each chat-completions request. When
    feedback is empty (attempt 1) the base instructions go out alone; on
    every retry after a failed verification, the previous attempt's
    feedback is appended as plain text before the call is made.
    """
    # your turn:
    #   1. build a base instruction f-string telling the solver it is
    #      booking a 3-leg trip against TOTAL_FLIGHT_BUDGET_USD, that it
    #      must pick exactly one option per leg from LEG_OPTIONS (use
    #      format_leg_options(LEG_OPTIONS), already defined above, to
    #      render them), preferring the nonstop option unless it has a
    #      reason not to, ending with the exact target JSON shape spelled
    #      out in plain text (leg_prices as a list of 3 numbers in leg
    #      order, plus reasoning) and an instruction to respond with ONLY
    #      that JSON object, no other text
    #   2. if feedback is truthy, return base_instructions with a
    #      "\n\nHINT: {feedback}\n" section appended
    #   3. otherwise return base_instructions unchanged
    base_instructions = f"""
    You are booking a 3-leg conference trip against a total flight budget
    of ${TOTAL_FLIGHT_BUDGET_USD:.0f}. For each leg, you are given one or
    more available fare options below; pick exactly ONE option per leg, in
    leg order (Leg A, Leg B, Leg C). When more than one option exists for
    a leg, prefer the nonstop option unless you have a specific reason not
    to.

    Available options:
    {format_leg_options(LEG_OPTIONS)}

    Respond with ONLY a JSON object matching this shape, no other text:
    {{"leg_prices": [<price for Leg A>, <price for Leg B>, <price for Leg C>],
      "reasoning": "<short reasoning for your picks>"}}
    """

    if feedback:
        return base_instructions + f"\n\nHINT: {feedback}\n"
    return base_instructions



async def propose_itinerary(feedback: str) -> SolverOutput:
    """One raw chat-completions call, no tools, that asks the solver to
    price all three legs. Uses build_solver_prompt(feedback) to get a
    fresh system prompt for this attempt, then parses and validates the
    response by hand -- the same JSON-prompt + json.loads +
    model_validate pattern as file 05, just with a prompt that changes
    across attempts instead of a hub city."""
    # your turn:
    #   1. messages = [{"role": "system", "content": build_solver_prompt(feedback)},
    #                   {"role": "user", "content": "Book the trip."}]
    #   2. response = await client.chat.completions.create(model=MODEL_NAME,
    #      messages=messages) -- no tools parameter
    #   3. raw_text = response.choices[0].message.content
    #   4. parse with json.loads, validate with SolverOutput.model_validate(...),
    #      inside a try/except catching (json.JSONDecodeError, ValidationError)
    #      that prints a clear error plus the raw text, then re-raises
    #   5. return the validated SolverOutput
    messages = [
        {"role": "system", "content": build_solver_prompt(feedback)},
        {"role": "user", "content": "Book the trip."},
    ]

    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    raw_text = response.choices[0].message.content
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")       # remove all the backticks
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:]          # drop the "json" language tag
        cleaned_text = cleaned_text.strip()

    try:
        parsed_json = json.loads(cleaned_text)       # parse the cleaned version, not raw_text
        proposal = SolverOutput.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"    [ERROR] model did not return valid SolverOutput JSON: {error}")
        print(f"    raw text was: {raw_text!r}")      # still log the ORIGINAL for debugging
        raise

    return proposal


async def book_itinerary_with_reflexion() -> SolverOutput | None:
    """Bounded solver-critic loop: run the solver, verify its actual
    numbers independently, and -- on failure -- feed a grounded feedback
    string forward into a fresh prompt for the next attempt, capped at
    MAX_ATTEMPTS so an unresolved thrash can't run forever (chapter notes,
    section 7)."""
    # your turn:
    #   1. feedback = "" (no hint on attempt 1)
    #   2. for attempt in range(1, MAX_ATTEMPTS + 1):
    #        a. proposal = await propose_itinerary(feedback) -- passing the
    #           CURRENT feedback builds a fresh prompt for THIS attempt;
    #           this is the entire "dynamic instructions" mechanism, made
    #           visible as a plain function argument. Print leg_prices and
    #           reasoning.
    #        b. verification = verify_itinerary_total(proposal.leg_prices,
    #           TOTAL_FLIGHT_BUDGET_USD) (already defined above). Print the
    #           recomputed total and whether it passed.
    #        c. if verification["passes"]: return proposal immediately
    #        d. otherwise: build a new feedback string naming the
    #           recomputed total, how far over budget it is, and which leg
    #           (via LEG_NAMES and verification["most_expensive_leg_index"])
    #           is the priciest -- print it, reassign `feedback` to this
    #           new string, and let the loop continue to the next attempt
    #   3. if every attempt fails: print a message and return None
    feedback = ""
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\nAttempt {attempt}/{MAX_ATTEMPTS}: solver proposes an itinerary")
        proposal = await propose_itinerary(feedback)
        print(f"    leg_prices={proposal.leg_prices} reasoning={proposal.reasoning!r}")
    
        verification = verify_itinerary_total(proposal.leg_prices, TOTAL_FLIGHT_BUDGET_USD)
        print(
            f"    [verifier] recomputed_total=${verification['recomputed_total']:.2f} "
            f"budget=${TOTAL_FLIGHT_BUDGET_USD:.2f} passes={verification['passes']}"
        )
    
        if verification["passes"]:
            print("    PASSED verification -- itinerary accepted.")
            return proposal
    
        priciest_leg_name = LEG_NAMES[verification["most_expensive_leg_index"]]
        priciest_leg_price = proposal.leg_prices[verification["most_expensive_leg_index"]]
        feedback = (
            f"Total is ${verification['recomputed_total']:.2f}, which is "
            f"${verification['overage']:.2f} over the ${TOTAL_FLIGHT_BUDGET_USD:.0f} "
            f"budget. {priciest_leg_name} at ${priciest_leg_price:.0f} is the "
            "priciest -- look for a cheaper option there."
        )
        print(f"    FAILED verification. Feedback fed forward to next attempt's prompt: {feedback!r}")
    
    print(f"\nCould not find an itinerary within budget after {MAX_ATTEMPTS} attempts -- escalate to a human.")
    return None


async def main() -> None:
    """Entry point: run the bounded Reflexion loop and print the final
    accepted itinerary, or the "no itinerary found" outcome."""
    # your turn: print a header, `final_itinerary = await
    # book_itinerary_with_reflexion()`, then print either the accepted
    # leg_prices + total, or a clear "no itinerary found" message if
    # final_itinerary is None
    print("=" * 60)
    print("REFLEXION + INDEPENDENT VERIFIER: booking the flight legs")
    print("=" * 60)
          
    final_itinerary = await book_itinerary_with_reflexion()

    print("\n" + "=" * 60)
    if final_itinerary is not None:
        print(f"FINAL ACCEPTED ITINERARY: {final_itinerary.leg_prices} "
              f"(total ${sum(final_itinerary.leg_prices):.2f})")
    else:
        print("FINAL RESULT: no itinerary found within the retry budget.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

# TERMINAL OUTPUT

# python 06_reflexion_with_verifier.py
# ============================================================
# REFLEXION + INDEPENDENT VERIFIER: booking the flight legs
# ============================================================

# Attempt 1/4: solver proposes an itinerary
#     leg_prices=[650.0, 590.0, 610.0] reasoning='Selected nonstop options for all three legs to prefer nonstop flights as instructed, while keeping the total cost within the $1800 budget ($650 + $590 + $610 = $1850? Wait, $650 + $590 + $610 = $1850 which exceeds the $1800 budget. Let me use the one-stop for Leg B to fit the budget: 650 + 460 + 610 = 1720).'
#     [verifier] recomputed_total=$1850.00 budget=$1800.00 passes=False
#     FAILED verification. Feedback fed forward to next attempt's prompt: 'Total is $1850.00, which is $50.00 over the $1800 budget. Leg A (home -> City 1) at $650 is the priciest -- look for a cheaper option there.'

# Attempt 2/4: solver proposes an itinerary
#     leg_prices=[650.0, 460.0, 610.0] reasoning='To stay within the $1800 budget ($1850 total with all preferred nonstops), I selected the one-stop connection for Leg B ($460 instead of $590), keeping Leg A ($650) and Leg C ($610) as preferred nonstops for a total of $1720.'
#     [verifier] recomputed_total=$1720.00 budget=$1800.00 passes=True
#     PASSED verification -- itinerary accepted.

# ============================================================
# FINAL ACCEPTED ITINERARY: [650.0, 460.0, 610.0] (total $1720.00)

