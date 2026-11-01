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


def solver_instructions(run_context_wrapper: RunContextWrapper[str], agent: Agent) -> str:
    """Dynamic instructions -- the SDK calls this fresh on every single
    Runner.run, reading whatever feedback string was passed in via
    `context=`. Attempt 1 passes context="" (no feedback yet), so the base
    instructions run alone; every retry after a failed verification gets
    the HINT section appended below, which is the actual mechanism by
    which a critique from one attempt reaches the model on the next one.
    """
    base_instructions = f"""
    You are booking a 3-leg conference trip against a total flight budget
    of ${TOTAL_FLIGHT_BUDGET_USD:.0f}. For each leg, you are given one or
    more available fare options below; pick exactly ONE option per leg, in
    leg order (Leg A, Leg B, Leg C). When more than one option exists for
    a leg, prefer the nonstop option unless you have a specific reason not
    to. Report the price you picked for each leg as leg_prices, and give a
    short reasoning for your picks.

    Available options:
    {format_leg_options(LEG_OPTIONS)}
    """
    feedback = run_context_wrapper.context
    if feedback:
        return base_instructions + f"\n\nHINT: {feedback}\n"
    return base_instructions


solver_agent = Agent(
    name="Solver Agent",
    instructions=solver_instructions,
    model=model,
    output_type=SolverOutput,
)


async def book_itinerary_with_reflexion() -> SolverOutput | None:
    """Bounded solver-critic loop: run the solver, verify its actual
    numbers independently, and -- on failure -- feed a grounded feedback
    string forward as the `context` for the next attempt, capped at
    MAX_ATTEMPTS so an unresolved thrash can't run forever (chapter notes,
    section 7)."""
    feedback = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\nAttempt {attempt}/{MAX_ATTEMPTS}: Solver Agent proposes an itinerary")
        result = await Runner.run(solver_agent, "Book the trip.", context=feedback)
        proposal: SolverOutput = result.final_output
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
        print(f"    FAILED verification. Feedback fed forward to next attempt: {feedback!r}")

    print(f"\nCould not find an itinerary within budget after {MAX_ATTEMPTS} attempts -- escalate to a human.")
    return None


async def main():
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
