# ============================================================
# LISTING: 02_best_of_n_sampling.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: Best-of-N sampling for a single flight-booking decision --
#           generate N independent candidate itineraries CONCURRENTLY via
#           asyncio.gather over raw chat-completions calls, score each one
#           with a DETERMINISTIC plain Python rubric (never a model
#           judgment), auto-reject anything over budget, and pick the
#           highest scorer. A separate, much simpler
#           self_consistency_vote() shows majority voting as the
#           alternative to reach for when candidates should converge on
#           one discrete answer instead of being independently scored.
# REF: Chapter 5 notes, section 3 (Test-Time Compute: The Budget Behind
#      "Thinking Longer")
# COMPARE: the SDK version of this file at ../../openai_sdk/solved/02_best_of_n_sampling.py
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The SDK version sampled N candidates by running Runner.run() N times
# over one Agent whose @function_tool-decorated search_flights() quietly
# advanced through a fixed pool on every call -- the model never saw the
# pool directly, it just called a tool and got told what it found. Here
# there is no tool at all: each of the N concurrent tasks is a single raw
# client.chat.completions.create call, grounded directly in one pool
# entry's raw data (passed in the user message) and asked to reformat it
# as strict JSON. That makes the thing Best-of-N is actually about --
# firing N calls at once with asyncio.gather and scoring N independently
# parsed JSON results -- the only moving part left, instead of it being
# entangled with tool-calling machinery this scenario doesn't need.

import asyncio
import json
import os
from collections import Counter

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

# Matches the notes' Best-of-4 dry run: candidate prices $420 / $455 /
# $410 / $440 against a $450 budget cap, so B is the one over-budget
# candidate the rubric must auto-reject regardless of how it scores
# otherwise.
CANDIDATE_SAMPLE_COUNT = 4
FLIGHT_LEG_BUDGET = 450.0

# --- Fixed candidate pool for this demo, indexed by call order so the
# scoring stays deterministic and repeatable rather than truly random
# every run. Each pool entry stands in for "one real-world search result"
# -- in the SDK version this lived behind a stateful tool; here it's just
# grounding data handed straight to the model in the prompt.
_candidate_pool = [
    {"flight_id": "A", "price": 420.0, "stops": 1, "connection_risk": "comfortable, 1h40m layover"},
    {"flight_id": "B", "price": 455.0, "stops": 0, "connection_risk": "n/a"},
    {"flight_id": "C", "price": 410.0, "stops": 2, "connection_risk": "tight, 35-minute connection"},
    {"flight_id": "D", "price": 440.0, "stops": 1, "connection_risk": "comfortable, 1h10m layover"},
]


class CandidateFlight(BaseModel):
    """One candidate itinerary, parsed and validated from the model's raw
    JSON response -- real structured data the scoring rubric can read
    directly."""

    flight_id: str
    price: float
    stops: int
    connection_risk: str


CANDIDATE_SYSTEM_PROMPT = """
You are proposing ONE candidate flight itinerary for the given route,
based on the raw search-result data provided in the user message.
Reformat that exact data faithfully -- do not invent different numbers or
change any field.

Respond with ONLY a JSON object matching this shape, no other text:
{"flight_id": "...", "price": <number>, "stops": <integer>, "connection_risk": "..."}
""".strip()


def score_candidate(candidate: dict, budget: float) -> float:
    """Deterministic scoring rubric (plain Python, never a model call) on
    a 0-10 scale: budget compliance is a hard gate, then stops and
    connection risk are weighed. Mirrors the notes' Best-of-4 table.

    Math note: score = 0 if over budget (auto-reject), else a weighted sum
    -- fewer stops and lower connection risk each add points.
    """
    if candidate["price"] > budget:
        return 0.0

    stops_score = {0: 4.0, 1: 3.0, 2: 1.5}.get(candidate["stops"], 0.0)

    risk_text = candidate["connection_risk"].lower()
    if "tight" in risk_text:
        risk_score = 1.0
    elif "comfortable" in risk_text:
        risk_score = 4.0
    else:
        risk_score = 3.0  # nonstop, no connection risk to weigh

    price_headroom = budget - candidate["price"]
    price_score = min(price_headroom / budget * 5.0, 2.0)

    return round(stops_score + risk_score + price_score, 2)


def self_consistency_vote(candidate_answers: list[str]) -> str:
    """Majority voting over independently generated DISCRETE answers --
    the simpler alternative to best-of-N scoring, used when candidates are
    expected to converge on the same result (e.g. several independent
    price quotes for the same booking) rather than being genuinely
    different tradeoffs that need a rubric to compare."""
    counts = Counter(candidate_answers)
    winner, winner_count = counts.most_common(1)[0]
    print(f"    [self-consistency] votes: {dict(counts)} -> majority: {winner!r} ({winner_count}/{len(candidate_answers)})")
    return winner


# --- Your turn ---
# Write:
#   1. An async sample_one_candidate(route: str, raw_search_result: dict)
#      -> dict that makes ONE raw chat.completions.create call: system
#      prompt CANDIDATE_SYSTEM_PROMPT, user content describing the route
#      and embedding raw_search_result (e.g. via json.dumps) as the "raw
#      search-result data" the model must faithfully reformat. Parse the
#      response text with json.loads and validate it into a
#      CandidateFlight with .model_validate(...), wrapped in a
#      try/except that prints a clear error and re-raises on failure.
#      Print the parsed candidate, then return it as a dict
#      (candidate.model_dump()).
#   2. An async run_best_of_n(route: str, budget: float, n: int) -> dict
#      that:
#        a. STEP 1: builds n tasks -- one sample_one_candidate(...) call
#           per pool entry, cycling through _candidate_pool with
#           `_candidate_pool[i % len(_candidate_pool)]` -- and fires them
#           all CONCURRENTLY with asyncio.gather. This concurrency is what
#           makes it Best-of-N rather than N sequential calls.
#        b. STEP 2: scores every sampled candidate with score_candidate(...)
#           (already defined above -- do not reimplement it) and prints
#           each candidate with its score, noting any that got
#           auto-rejected for being over budget.
#        c. STEP 3: picks the highest-scoring candidate with max(...) and
#           prints the winner.
#        d. STEP 4: prints a short note on the cost tradeoff -- n
#           generation calls instead of 1, to avoid a blind pick.
#      Return the winning candidate dict.
#
# Then write an async main() that:
#   - Runs PART 1: await run_best_of_n("conference city leg 2",
#     FLIGHT_LEG_BUDGET, CANDIDATE_SAMPLE_COUNT).
#   - Runs PART 2: builds price_quotes = ["$620", "$620", "$635", "$620"],
#     prints them, and calls self_consistency_vote(price_quotes)
#     (already defined above), printing the majority-vote winner.

if __name__ == "__main__":
    asyncio.run(main())
