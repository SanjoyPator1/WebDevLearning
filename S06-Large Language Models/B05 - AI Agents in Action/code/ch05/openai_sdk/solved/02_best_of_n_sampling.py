# ============================================================
# LISTING: 02_best_of_n_sampling.py  (reference implementation)
# BUILDING: Best-of-N sampling for a single flight-booking decision --
#           generate N independent candidate itineraries concurrently
#           (asyncio.gather), score each one with a DETERMINISTIC plain
#           Python rubric (never a model judgment), auto-reject anything
#           over budget, and pick the highest scorer. A separate, much
#           simpler self_consistency_vote() shows majority voting as the
#           alternative to reach for when candidates should converge on
#           one discrete answer instead of being independently scored.
# REF: Chapter 5 notes, section 3 (Test-Time Compute: The Budget Behind
#      "Thinking Longer")
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# This mirrors the notes' own Best-of-4 dry run almost exactly: a $450
# budget, four candidates, one auto-rejected for being over budget, and a
# rubric that weighs price, stops, and connection risk rather than price
# alone. The point isn't that any one candidate reasons better -- it's
# that sampling several and scoring them catches a risky pick (a cheap
# option with a tight connection) that a single-sample draw could have
# landed on with no way to know a safer alternative existed.

import asyncio
import os
from collections import Counter

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from dotenv import load_dotenv
from openai import AsyncOpenAI

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

# Matches the notes' Best-of-4 dry run: candidate prices $420 / $455 /
# $410 / $440 against a $450 budget cap, so B is the one over-budget
# candidate the rubric must auto-reject regardless of how it scores
# otherwise.
CANDIDATE_SAMPLE_COUNT = 4
FLIGHT_LEG_BUDGET = 450.0

# --- Fixed candidate pool for this demo, indexed by call order so the
# tool is deterministic and repeatable rather than truly random every run.
_candidate_pool = [
    {"flight_id": "A", "price": 420.0, "stops": 1, "connection_risk": "comfortable, 1h40m layover"},
    {"flight_id": "B", "price": 455.0, "stops": 0, "connection_risk": "n/a"},
    {"flight_id": "C", "price": 410.0, "stops": 2, "connection_risk": "tight, 35-minute connection"},
    {"flight_id": "D", "price": 440.0, "stops": 1, "connection_risk": "comfortable, 1h10m layover"},
]


@function_tool
def search_flights(route: str) -> dict:
    """Return one candidate flight for the given route. Each call advances
    to the next fixed candidate in the pool, simulating N independent
    searches turning up N different real-world options."""
    index = search_flights.call_count % len(_candidate_pool)
    search_flights.call_count += 1
    candidate = {"route": route, **_candidate_pool[index]}
    print(f"    [tool] search_flights({route!r}) -> {candidate}")
    return candidate


search_flights.call_count = 0


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


flight_candidate_agent = Agent(
    name="Flight Candidate Agent",
    instructions="""
    Call search_flights once for the given route and report back the
    candidate flight you found in one short sentence, including its price,
    stops, and connection risk.
    """,
    model=model,
    tools=[search_flights],
)


async def run_best_of_n(route: str, budget: float, n: int) -> dict:
    """Generate n independent candidate itineraries CONCURRENTLY, score
    every one with the deterministic rubric, and return the winner."""
    print(f"\nSTEP 1: Launching {n} independent Flight Candidate Agent calls concurrently")
    print(f"    route={route!r} budget=${budget:.2f}")
    tasks = [Runner.run(flight_candidate_agent, route) for _ in range(n)]
    results = await asyncio.gather(*tasks)
    for i, result in enumerate(results, start=1):
        print(f"    candidate {i} agent summary: {result.final_output}")

    print(f"\nSTEP 2: Scoring the {n} underlying candidates with the deterministic rubric")
    # search_flights() is a stateful tool: by the time all n calls have
    # finished, the pool's call_count has advanced exactly n times, so the
    # first n pool entries are the candidates that were actually sampled.
    sampled_candidates = _candidate_pool[:n]
    scored = []
    for candidate in sampled_candidates:
        score = score_candidate(candidate, budget)
        scored.append((candidate, score))
        rejection_note = " (AUTO-REJECT: over budget)" if candidate["price"] > budget else ""
        print(
            f"    candidate {candidate['flight_id']}: price=${candidate['price']:.2f} "
            f"stops={candidate['stops']} risk={candidate['connection_risk']!r} "
            f"-> score={score}{rejection_note}"
        )

    print("\nSTEP 3: Picking the winner")
    winning_candidate, winning_score = max(scored, key=lambda pair: pair[1])
    print(
        f"    WINNER: candidate {winning_candidate['flight_id']} "
        f"(${winning_candidate['price']:.2f}, score={winning_score})"
    )

    print("\nSTEP 4: Cost tradeoff")
    print(
        f"    {n} candidate generations + {n} scoring passes vs. 1 generation "
        f"for a single sample -- this run spent roughly {n}x the generation "
        f"calls (plus {n} cheap scoring passes, which are plain Python here "
        "and cost nothing extra) to avoid a blind pick."
    )
    return winning_candidate


async def main():
    print("=" * 60)
    print("PART 1: Best-of-N sampling for the flight-booking step")
    print("=" * 60)
    await run_best_of_n("conference city leg 2", FLIGHT_LEG_BUDGET, CANDIDATE_SAMPLE_COUNT)

    print("\n" + "=" * 60)
    print("PART 2: Self-consistency (majority vote) -- the simpler alternative")
    print("=" * 60)
    print(
        "    Used when independent samples are expected to CONVERGE on the "
        "same discrete answer (e.g. several independent price quotes for "
        "the same already-known flight), rather than being genuinely "
        "different tradeoffs that need a rubric to compare."
    )
    price_quotes = ["$620", "$620", "$635", "$620"]
    print(f"\nSTEP 1: Independent price quotes gathered: {price_quotes}")
    winning_quote = self_consistency_vote(price_quotes)
    print(f"STEP 2: Majority-vote result: {winning_quote}")


if __name__ == "__main__":
    asyncio.run(main())
