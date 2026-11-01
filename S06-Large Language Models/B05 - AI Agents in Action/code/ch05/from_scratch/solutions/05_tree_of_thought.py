# ============================================================
# LISTING: 05_tree_of_thought.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: The Tree-of-Thought generate -> expand -> evaluate -> prune
#           loop, applied to a single branch point in the conference trip:
#           which city to connect through for one flight leg. Reuses the
#           chapter notes' own Doha-vs-Frankfurt dry run numbers exactly.
#           Evaluation is a DETERMINISTIC plain-Python scoring function,
#           not a second model call -- the notes are explicit that a cheap
#           external check is often the right evaluator, not another LLM.
# REF: Chapter 5 notes, section 6 (Tree-of-Thought: Branching, Evaluating,
#      and Pruning Reasoning Paths)
# COMPARE: the SDK version of this file at ../../openai_sdk/solved/05_tree_of_thought.py
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The SDK version got RouteBranch back "for free" via output_type=
# RouteBranch on generator_agent -- the SDK silently turned that Pydantic
# model into a JSON schema, handed it to the provider, and parsed the
# response for you. Here that machinery is made visible: the exact JSON
# shape is spelled out by hand in the generator's system prompt, the raw
# response text is pulled off message.content, and it is parsed with
# json.loads and validated with RouteBranch.model_validate(), wrapped in a
# try/except that prints the offending raw text instead of failing
# silently. The GENERATE / EVALUATE / PRUNE / EXPAND orchestration itself
# was never an SDK feature in the first place -- score_branch() is plain
# Python in both versions, and the loop that calls the generator once per
# candidate hub is just a plain Python for-loop calling an async function.

# NOTE: "the pruning and the decision about what to expand are done by your code" — not by the model
#  You could ask a model "which of these is better?" but then you'd be back to trusting a model's opinion, 
# same caution as every scoring exercise so far in this chapter.
# The cost trade-off : Every branch is at least one call, and a deeper tree multiplies quickly: 3 options at each of 3 levels is 27 leaves.

# also for the first model call output of the branch it just guesses at this point - which is fine as this is a dummy problem
# then next it does some arithmetic calculation based on some rules to get the score and prunes some branch accordingly
# then for the non pruned branch it takes the previous model call json and gives out a text reply as final answer

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


async def generate_route_branch(hub_city: str) -> RouteBranch:
    """One raw chat-completions call, no tools, proposing a candidate
    itinerary through hub_city. This is the whole of what output_type=
    RouteBranch did for us in the SDK version: it is JUST a system prompt
    that spells out the target JSON shape, plus json.loads() +
    RouteBranch.model_validate() on the way back out. No schema is sent to
    the provider -- the model is simply told, in plain English, what shape
    to respond in, and we hold it to that by hand.
    """
    # your turn:
    #   1. build a system prompt combining TRIP_CONTEXT with instructions
    #      to propose a realistic candidate itinerary through hub_city (a
    #      fare in USD, a layover duration in minutes, whether a transit
    #      visa is needed, and one sentence of reasoning), ending with the
    #      exact target JSON shape spelled out in plain text (the fields
    #      RouteBranch expects: hub_city, fare_usd, layover_minutes,
    #      visa_transit_needed, reasoning) and an instruction to respond
    #      with ONLY that JSON object, no other text
    #   2. messages = [{"role": "system", "content": system_prompt},
    #                   {"role": "user", "content": f"Candidate hub: {hub_city}"}]
    #   3. response = await client.chat.completions.create(model=MODEL_NAME,
    #      messages=messages) -- no tools parameter needed
    #   4. raw_text = response.choices[0].message.content
    #   5. parse with json.loads, validate with RouteBranch.model_validate(...),
    #      inside a try/except catching (json.JSONDecodeError, ValidationError)
    #      that prints a clear error plus the raw text, then re-raises
    #   6. return the validated RouteBranch
    system_prompt = f"""
    {TRIP_CONTEXT}

    You will be told one specific hub city to route the connecting leg
    through. Propose a realistic candidate itinerary through that hub: a
    total fare in USD, the layover duration in minutes, and whether the
    hub requires a short-notice transit visa. Give one sentence of
    reasoning for your numbers.

    Respond with ONLY a JSON object matching this shape, no other text:
    {{"hub_city": "<the hub city you were given>", "fare_usd": <number>,
      "layover_minutes": <integer>, "visa_transit_needed": <true or false>,
      "reasoning": "<one sentence>"}}
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Candidate hub: {hub_city}"},
    ]

    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    raw_text = response.choices[0].message.content

    try:
        parsed_json = json.loads(raw_text)
        branch = RouteBranch.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as error:
        print(f"    [ERROR] model did not return valid RouteBranch JSON for {hub_city}: {error}")
        print(f"    raw text was: {raw_text!r}")
        raise

    return branch


async def expand_winning_branch(branch: RouteBranch) -> str:
    """One raw chat-completions call, no tools and no structured output --
    plain text is fine here, exactly as it was in the SDK version (no
    output_type was set on expansion_agent either)."""
    # your turn:
    #   1. a system prompt saying: you are given the single surviving
    #      routing branch from a Tree-of-Thought search; in one or two
    #      sentences, describe the next concrete step for finishing this
    #      leg of the trip now that this hub has been chosen
    #   2. messages = [{"role": "system", "content": system_prompt},
    #                   {"role": "user", "content": branch.model_dump_json()}]
    #   3. response = await client.chat.completions.create(model=MODEL_NAME,
    #      messages=messages)
    #   4. return response.choices[0].message.content directly (no parsing)
    system_prompt = """
    You are given the single surviving routing branch from a Tree-of-
    Thought search. In one or two sentences, describe the next concrete
    step for finishing this leg of the trip now that this hub has been
    chosen -- for example, matching the hotel check-in date to the actual
    arrival time this route produces.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": branch.model_dump_json()},
    ]

    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages)
    return response.choices[0].message.content


async def main() -> None:
    """Entry point: run the GENERATE -> EVALUATE -> PRUNE -> EXPAND search
    over CANDIDATE_HUBS, then print an honest cost accounting."""
    # your turn:
    #   STEP 1 (GENERATE): loop over CANDIDATE_HUBS, calling
    #     `await generate_route_branch(hub_city)` once per hub, collecting
    #     each RouteBranch into a list and printing it as it comes back.
    #     This is N generation calls for N hubs -- keep count.
    #
    #   STEP 2 (EVALUATE): call score_branch(branch) (already defined
    #     above -- do not reimplement it) on every branch collected above.
    #     Plain Python, not a model call -- keep count of how many
    #     "evaluation-equivalent" checks ran.
    #
    #   STEP 3 (PRUNE): for each (branch, score) pair, print the branch,
    #     its score, and whether it's KEPT (score >= PRUNE_THRESHOLD) or
    #     PRUNED. Collect the survivors into a list.
    #
    #   STEP 4 (EXPAND): if no branch survives, print a message and
    #     return. Otherwise pick the single highest-scoring survivor with
    #     max(survivors, key=lambda pair: pair[1]) and expand it: call
    #     `await expand_winning_branch(winning_branch)` and print the next
    #     step it returns. This is 1 expansion call -- keep count.
    #
    #   STEP 5 (COST ACCOUNTING): print the REAL model calls made
    #     (generation + expansion, since evaluation was free), a
    #     notes-style tally that counts evaluation as if it had been a
    #     model call too (for comparison against the chapter's own dry
    #     run), and what a single straight-line answer (1 call, no
    #     branching) would have cost instead.
    
    print("=" * 60)
    print("TREE-OF-THOUGHT: choosing a connecting hub")
    print("=" * 60)

    print(f"\nSTEP 1: GENERATE -- one raw chat-completions call per candidate hub {CANDIDATE_HUBS}")
    branches: list[RouteBranch] = []
    for hub_city in CANDIDATE_HUBS:
        branch = await generate_route_branch(hub_city)
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
    next_step = await expand_winning_branch(winning_branch)
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

# TERMINAL OUTPUT

# python 05_tree_of_thought.py 
# ============================================================
# TREE-OF-THOUGHT: choosing a connecting hub
# ============================================================

# STEP 1: GENERATE -- one raw chat-completions call per candidate hub ['Doha', 'Frankfurt']
#     branch proposed -- Doha: $1150, 120 min layover, visa_transit_needed=False
#     branch proposed -- Frankfurt: $850, 110 min layover, visa_transit_needed=False

# STEP 2: EVALUATE -- 2 deterministic score_branch() checks, $0 extra LLM cost
#     [score_branch] Doha: cost=4.00/4 layover=4.00/4 visa=2.00/2 -> total=10.00/10
#     [score_branch] Frankfurt: cost=4.00/4 layover=3.56/4 visa=2.00/2 -> total=9.56/10

# STEP 3: PRUNE -- drop anything below PRUNE_THRESHOLD=6.0
#     Doha: score=10.00 -> KEEP
#     Frankfurt: score=9.56 -> KEEP

# STEP 4: EXPAND -- only the single survivor is carried forward: Doha (score=10.00)
#     next step: Now that the Doha hub and its 120-minute layover are locked in, the next step is to confirm the exact flight arrival and departure times to align airport terminal transfers and verify baggage-check-through policies for the entire journey.

# ============================================================
# COST ACCOUNTING: what this search actually spent
# ============================================================
#     REAL model calls made: 2 generation + 1 expansion = 3 calls (evaluation was free -- deterministic score_branch(), not a model call)
#     Notes-style accounting (counting evaluation as if it were a model call too, for comparison to the chapter's own dry run): 2 generation + 2 evaluation-equivalent-checks + 1 expansion = 5 calls total
#     A single straight-line answer -- pick one hub, price it, book it, no branching at all -- would have cost 1 call.

