# ============================================================
# LISTING: 06_reflexion_with_verifier.py  (reference implementation)
# BUILDING: A Reflexion solver-critic loop where the critic is NOT the
#           solver re-reading its own work -- it is a deterministic
#           verifier that recomputes the itinerary total directly from the
#           raw leg prices. Feedback from a failed verification is fed
#           back into the next attempt through the SDK's real DYNAMIC
#           instructions mechanism: the Solver Agent's instructions are a
#           callable that reads run_context_wrapper.context and appends a
#           HINT section built from the previous attempt's failure.
# REF: Chapter 5 notes, section 7 (Reflexion and Independent Verifiers:
#      Self-Critique That Actually Works)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The notes' own dry run is reused directly: a $1,800 flight budget, and
# three legs that -- if the solver books the "obvious" nonstop option on
# every leg -- price out to $650 + $590 + $610 = $1,850, exactly $50 over
# budget. verify_itinerary_total() never trusts anything the solver claims
# about its own total; it re-adds the raw leg_prices every single time,
# which is the whole reason this verifier is trustworthy where asking the
# solver to grade its own homework would not be.

import asyncio
import os

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    RunContextWrapper,
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
    """Structured output for the Solver Agent. Extracting the three
    per-leg prices this way means the retry loop can call
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


# --- Your turn ---
# This is the trickiest file in the set -- take it one piece at a time.
#
#   1. Write solver_instructions(run_context_wrapper, agent) -> str, a
#      DYNAMIC instructions function (the real mechanism: pass a plain
#      function as an Agent's `instructions=`, and the SDK calls it fresh
#      on every Runner.run with a RunContextWrapper it can read
#      run_context_wrapper.context off of). It should:
#        - Build a base instruction string telling the solver it is
#          booking a 3-leg trip against TOTAL_FLIGHT_BUDGET_USD, that it
#          must pick exactly one option per leg from LEG_OPTIONS (use
#          format_leg_options(LEG_OPTIONS) to render them), preferring the
#          nonstop option unless it has a reason not to, and that it
#          should report its picks as leg_prices plus a short reasoning.
#        - Read run_context_wrapper.context (a plain string -- empty on
#          the first attempt). If it's non-empty, append a "HINT: <that
#          feedback>" section to the base instructions before returning.
#          If it's empty, return the base instructions unchanged.
#
#   2. Define solver_agent = Agent(..., instructions=solver_instructions,
#      model=model, output_type=SolverOutput).
#
#   3. Write an async book_itinerary_with_reflexion() -> SolverOutput | None
#      that runs a bounded retry loop, capped at MAX_ATTEMPTS:
#        a. Start with feedback = "" (no hint on attempt 1).
#        b. Each attempt: call `await Runner.run(solver_agent, "Book the
#           trip.", context=feedback)` -- passing feedback as `context` is
#           what makes the dynamic instructions function above pick it up
#           on the NEXT call. Print the proposed leg_prices and reasoning.
#        c. Call verify_itinerary_total(proposal.leg_prices,
#           TOTAL_FLIGHT_BUDGET_USD) and print the recomputed total and
#           whether it passed.
#        d. If it passed, return the proposal immediately.
#        e. If it failed, build a new feedback string naming the
#           recomputed total, how far over budget it is, and which leg
#           (via LEG_NAMES and the most_expensive_leg_index) is the
#           priciest and worth reconsidering -- print it, then let the
#           loop continue to the next attempt with that feedback set.
#        f. If every attempt fails, print a message and return None.
#
#   4. Write an async main() that runs book_itinerary_with_reflexion() and
#      prints the final accepted itinerary (or the "no itinerary found"
#      outcome), clearly labelled as the end result.

if __name__ == "__main__":
    asyncio.run(main())
