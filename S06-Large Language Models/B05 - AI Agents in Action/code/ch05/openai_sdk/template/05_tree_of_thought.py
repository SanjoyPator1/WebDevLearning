# ============================================================
# LISTING: 05_tree_of_thought.py  (reference implementation)
# BUILDING: The Tree-of-Thought generate -> expand -> evaluate -> prune
#           loop, applied to a single branch point in the conference trip:
#           which city to connect through for one flight leg. Reuses the
#           chapter notes' own Doha-vs-Frankfurt dry run numbers exactly.
#           Evaluation is a DETERMINISTIC plain-Python scoring function,
#           not a second model call -- the notes are explicit that a cheap
#           external check is often the right evaluator, not another LLM.
# REF: Chapter 5 notes, section 6 (Tree-of-Thought: Branching, Evaluating,
#      and Pruning Reasoning Paths)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# Generate: one model call per candidate hub proposes that branch's fare,
# layover, and visa complication. Evaluate: score_branch() below recomputes
# a 0-10 score from those same fields, no model involved -- this is the
# "cheap external check" the notes point to instead of a second LLM call.
# Prune: anything under PRUNE_THRESHOLD gets dropped. Expand: only the
# single surviving, highest-scoring branch gets a follow-up model call to
# work out its next concrete step -- losing branches are never expanded,
# which is the entire point of pruning before paying for the next round.

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

# The two candidate hubs from the chapter notes' own dry run (section 6).
# Each hub costs its own generation call below -- N candidate hubs costs N
# generation calls, mirroring the notes' "generating two branches costs 2
# calls" accounting exactly.
CANDIDATE_HUBS = ["Doha", "Frankfurt"]

TRIP_CONTEXT = """
The conference trip needs one connecting flight leg routed through a hub
city on the way to the destination. The traveler cares about the total
fare, how comfortable the layover is (a short connection risks a missed
flight), and whether the hub requires a short-notice transit visa.
""".strip()

# --- Scoring rubric constants -- plain numbers, no model involved ---
FARE_CHEAP_REFERENCE_USD = 1_800.0  # fare at/below this earns full cost points
FARE_EXPENSIVE_REFERENCE_USD = 2_150.0  # fare at/above this earns zero cost points
LAYOVER_COMFORTABLE_MINUTES = 120  # layover at/above this earns full layover points
LAYOVER_RISKY_MINUTES = 30  # layover at/below this earns zero layover points
COST_WEIGHT = 4.0  # out of 10
LAYOVER_WEIGHT = 4.0  # out of 10
VISA_WEIGHT = 2.0  # out of 10
PRUNE_THRESHOLD = 6.0  # branches scoring below this get dropped


class RouteBranch(BaseModel):
    """One candidate routing branch through a connecting hub -- the
    Tree-of-Thought 'node' for this branch point."""

    hub_city: str
    fare_usd: float
    layover_minutes: int
    visa_transit_needed: bool
    reasoning: str  # one sentence: why this hub, in the model's own words


def score_branch(branch: RouteBranch) -> float:
    """Deterministic 0-10 score for one routing branch, combining cost,
    layover risk, and visa complication. Pure Python, no model call --
    this is the cheap external check the chapter notes point to as the
    right kind of evaluator for a branch point like this one.

    MATH: score = cost_points + layover_points + visa_points, each
    component linearly interpolated between a "full points" reference and
    a "zero points" reference, then clamped to its own weight.
    """
    cost_fraction = (FARE_EXPENSIVE_REFERENCE_USD - branch.fare_usd) / (
        FARE_EXPENSIVE_REFERENCE_USD - FARE_CHEAP_REFERENCE_USD
    )
    cost_points = max(0.0, min(COST_WEIGHT, COST_WEIGHT * cost_fraction))

    layover_fraction = (branch.layover_minutes - LAYOVER_RISKY_MINUTES) / (
        LAYOVER_COMFORTABLE_MINUTES - LAYOVER_RISKY_MINUTES
    )
    layover_points = max(0.0, min(LAYOVER_WEIGHT, LAYOVER_WEIGHT * layover_fraction))

    visa_points = 0.0 if branch.visa_transit_needed else VISA_WEIGHT

    total_score = cost_points + layover_points + visa_points
    print(
        f"    [score_branch] {branch.hub_city}: cost={cost_points:.2f}/"
        f"{COST_WEIGHT:.0f} layover={layover_points:.2f}/{LAYOVER_WEIGHT:.0f} "
        f"visa={visa_points:.2f}/{VISA_WEIGHT:.0f} -> total={total_score:.2f}/10"
    )
    return total_score


# --- Your turn ---
# Define two agents and write the orchestration loop that ties them to
# score_branch() above.
#
#   1. generator_agent: an Agent whose instructions describe TRIP_CONTEXT
#      and tell it that it will be given one specific hub city, and asked
#      to propose a realistic candidate itinerary through that hub -- a
#      fare in USD, a layover duration in minutes, and whether a transit
#      visa is needed, plus one sentence of reasoning. Give it
#      output_type=RouteBranch.
#
#   2. expansion_agent: an Agent whose instructions say it will be given
#      the single surviving routing branch from a Tree-of-Thought search,
#      and should describe (in one or two sentences) the next concrete
#      step for finishing that leg of the trip now that the hub is chosen.
#      No output_type needed -- plain text is fine here.
#
#   3. An async main() that:
#      a. GENERATE: loops over CANDIDATE_HUBS, calling Runner.run(
#         generator_agent, f"Candidate hub: {hub_city}") once per hub, and
#         collects each result.final_output (a RouteBranch) into a list.
#         Print each branch as it comes back. This is N generation calls
#         for N hubs -- keep count.
#      b. EVALUATE: call score_branch(branch) on every branch collected
#         above (this is plain Python, not a model call -- keep count of
#         how many "evaluation-equivalent" checks ran).
#      c. PRUNE: for each (branch, score) pair, print the branch, its
#         score, and whether it's KEPT (score >= PRUNE_THRESHOLD) or
#         PRUNED. Collect the survivors.
#      d. If no branch survives, print a message and stop. Otherwise pick
#         the single highest-scoring survivor and EXPAND it: run
#         expansion_agent on winning_branch.model_dump_json() via
#         Runner.run(...), and print the next step it returns. This is 1
#         expansion call -- keep count.
#      e. Print an honest cost accounting: the REAL model calls made
#         (generation + expansion, since evaluation was free), a
#         notes-style tally that counts evaluation as if it had been a
#         model call too (for comparison against the chapter's own
#         dry run), and what a single straight-line answer (1 call, no
#         branching) would have cost instead.

if __name__ == "__main__":
    asyncio.run(main())
