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


generator_agent = Agent(
    name="Route Branch Generator",
    instructions=f"""
    {TRIP_CONTEXT}

    You will be told one specific hub city to route the connecting leg
    through. Propose a realistic candidate itinerary through that hub: a
    total fare in USD, the layover duration in minutes, and whether the
    hub requires a short-notice transit visa. Give one sentence of
    reasoning for your numbers.
    """,
    model=model,
    output_type=RouteBranch,
)

expansion_agent = Agent(
    name="Branch Expansion Agent",
    instructions="""
    You are given the single surviving routing branch from a Tree-of-
    Thought search. In one or two sentences, describe the next concrete
    step for finishing this leg of the trip now that this hub has been
    chosen -- for example, matching the hotel check-in date to the actual
    arrival time this route produces.
    """,
    model=model,
)


async def main():
    print("=" * 60)
    print("TREE-OF-THOUGHT: choosing a connecting hub")
    print("=" * 60)

    print(f"\nSTEP 1: GENERATE -- one model call per candidate hub {CANDIDATE_HUBS}")
    branches: list[RouteBranch] = []
    for hub_city in CANDIDATE_HUBS:
        prompt = f"Candidate hub: {hub_city}"
        result = await Runner.run(generator_agent, prompt)
        branch: RouteBranch = result.final_output
        branches.append(branch)
        print(
            f"    branch proposed -- {branch.hub_city}: ${branch.fare_usd:.0f}, "
            f"{branch.layover_minutes} min layover, "
            f"visa_transit_needed={branch.visa_transit_needed}"
        )
    generation_calls = len(CANDIDATE_HUBS)

    print(f"\nSTEP 2: EVALUATE -- {len(branches)} deterministic score_branch() checks, $0 extra LLM cost")
    scored_branches = [(branch, score_branch(branch)) for branch in branches]

    print(f"\nSTEP 3: PRUNE -- drop anything below PRUNE_THRESHOLD={PRUNE_THRESHOLD}")
    survivors = []
    for branch, score in scored_branches:
        decision = "KEEP" if score >= PRUNE_THRESHOLD else "PRUNE"
        print(f"    {branch.hub_city}: score={score:.2f} -> {decision}")
        if score >= PRUNE_THRESHOLD:
            survivors.append((branch, score))
    evaluation_calls_equivalent = len(branches)

    if not survivors:
        print("\nNo branch cleared the prune threshold -- would fall back to a human or a wider search.")
        return

    winning_branch, winning_score = max(survivors, key=lambda pair: pair[1])
    print(
        f"\nSTEP 4: EXPAND -- only the single survivor is carried forward: "
        f"{winning_branch.hub_city} (score={winning_score:.2f})"
    )
    expansion_result = await Runner.run(expansion_agent, winning_branch.model_dump_json())
    next_step = expansion_result.final_output
    print(f"    next step: {next_step}")
    expansion_calls = 1

    print("\n" + "=" * 60)
    print("COST ACCOUNTING: what this search actually spent")
    print("=" * 60)
    real_calls = generation_calls + expansion_calls
    notes_style_total = generation_calls + evaluation_calls_equivalent + expansion_calls
    print(
        f"    REAL model calls made: {generation_calls} generation + "
        f"{expansion_calls} expansion = {real_calls} calls "
        f"(evaluation was free -- deterministic score_branch(), not a model call)"
    )
    print(
        f"    Notes-style accounting (counting evaluation as if it were a "
        f"model call too, for comparison to the chapter's own dry run): "
        f"{generation_calls} generation + {evaluation_calls_equivalent} "
        f"evaluation-equivalent-checks + {expansion_calls} expansion = "
        f"{notes_style_total} calls total"
    )
    print(
        "    A single straight-line answer -- pick one hub, price it, book "
        "it, no branching at all -- would have cost 1 call."
    )


if __name__ == "__main__":
    asyncio.run(main())
