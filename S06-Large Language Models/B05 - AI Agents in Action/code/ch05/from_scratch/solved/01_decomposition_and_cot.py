# ============================================================
# LISTING: 01_decomposition_and_cot.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: Two ideas from the start of Chapter 5, kept separate on purpose:
#           1. DECOMPOSITION as its own inspectable step -- turning one
#              goal ("book my 3-city conference trip") into a list of
#              subproblems, with no ordering decided yet.
#           2. THREE WAYS TO REASON on the same time-travel puzzle: a
#              plain single pass, a chain-of-thought prompt, and the
#              model's own built-in thinking (reasoning_effort="high").
#              Each one is run 5 times and checked against a ground truth
#              computed in plain Python from the trip's timeline, never
#              from a model's own claim.
# REF: Chapter 5 notes, section 1 (Reasoning and Planning as Distinct
#      Operations) and section 2 (Chain-of-Thought and the Rise of
#      Reasoning Models)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# Part 2 measures something the model's text never shows you: built-in
# thinking is billed as tokens you cannot read. Through Gemini's
# OpenAI-compatible endpoint, that hidden thinking shows up only as the
# gap between total_tokens and (prompt_tokens + completion_tokens) -- it
# is never returned as text. The hidden_thinking_tokens() helper below is
# just that subtraction, done once so every arm can reuse it.

import asyncio
import json
import os
import re
import time

from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError
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

GOAL = "book my 3-city conference trip"

# The puzzle: a traveler jumps between years, and the question is how many
# days they spent in the past before seeing the event's end. This is the
# "nuances that make it difficult for a model" puzzle from the chapter --
# the kind of thing a model gets wrong often enough that comparing
# reasoning styles on it actually shows a difference.
TIME_TRAVEL_PUZZLE = """
A traveler starts in the present and goes back 100 years, arriving 3 days
before a 10-day historical event. After spending 6 days there, they jump
forward 50 years and stay 20 days. Then they jump back to see the last
day of the event. How many days did they spend in the past before seeing
the end of the event? Answer with just a number.
""".strip()

# Ground truth, computed in plain Python from the trip's own timeline --
# never from a model's answer. Each stop is (year_offset_from_present,
# days_spent_there); "in the past" means year_offset < 0.
PUZZLE_TIMELINE = [
    (-100, 6),   # 100 years back, stays 6 days
    (-50, 20),   # jumps forward 50 years (net -50 from present), stays 20 days
    (-100, 0),   # jumps back to the event's last day, 0 more days spent
]
PUZZLE_GROUND_TRUTH = sum(days for year_offset, days in PUZZLE_TIMELINE if year_offset < 0)

CHAIN_OF_THOUGHT_STRATEGY = """
Use this strategy before answering:
Step 1: Define the present as year 0, and the past as negative years.
Step 2: List every stop on the trip, with its year and days spent there.
Step 3: Decide which stops count as "in the past" from the traveler's
  point of view.
Step 4: Add up the days spent at each of those stops.
Step 5: Check your total before giving the final answer.
""".strip()

RUNS_PER_ARM = 5


class TripSubproblems(BaseModel):
    """Structured output for the decomposition step -- a flat list of
    pieces, with NO ordering or dependency information attached. That is
    planning's job, handled in a later file, not here."""

    subproblems: list[str]


DECOMPOSITION_SYSTEM_PROMPT = """
You are given a one-line trip-booking goal. Break it into the distinct
subproblems it is made of -- for example flights, hotel, and visa, if the
destination needs one. Do NOT decide what order to do them in and do NOT
say anything about dependencies between them; just list the pieces. If a
subproblem clearly does not apply (e.g. no visa needed), leave it out
rather than including it as "not needed".

Respond with ONLY a JSON object matching this shape, no other text:
{"subproblems": ["...", "...", ...]}
""".strip()


def parse_subproblems(raw_text: str) -> TripSubproblems:
    """Parse the decomposition call's raw text response into a validated
    TripSubproblems object -- a few lines you can read, debug, and see
    fail loudly if the model didn't comply."""
    try:
        parsed_dict = json.loads(raw_text)
        return TripSubproblems.model_validate(parsed_dict)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"    !! failed to parse decomposition response as TripSubproblems: {error}")
        print(f"    !! raw text was: {raw_text!r}")
        raise


async def run_puzzle_with_visible_thinking(*, thinking_level: str) -> dict:
    """BONUS, not part of the graded comparison above: Gemini can return a
    *thought summary* (a condensed version of its reasoning, not the raw
    trace) if you ask for it through `extra_body`, instead of the plain
    `reasoning_effort` kwarg -- the two cannot be combined on one call.
    Kept entirely separate from run_arm()/RUNS_PER_ARM so the official,
    graded hidden-thinking measurement above is never touched by this."""
    messages = [{"role": "user", "content": TIME_TRAVEL_PUZZLE}]

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        extra_body={
            "extra_body": {
                "google": {
                    "thinking_config": {
                        "thinking_level": thinking_level,
                        "include_thoughts": True,
                    }
                }
            }
        },
    )

    message = response.choices[0].message
    return {
        "answer_text": message.content or "",
        # not a guaranteed field on every SDK version -- fall back cleanly
        # if this particular response didn't carry one
        "reasoning_summary": getattr(message, "reasoning_content", None),
    }


def hidden_thinking_tokens(usage) -> int:
    """Built-in thinking is billed but its text is never returned through
    this endpoint. The only trace of it is this gap: total_tokens counts
    it, completion_tokens does not."""
    return usage.total_tokens - usage.prompt_tokens - usage.completion_tokens


def extract_answer_number(raw_text: str) -> int | None:
    """Pull the first integer out of a response, since even a model asked
    for 'just a number' sometimes wraps it in a sentence or markdown."""
    match = re.search(r"-?\d+", raw_text)
    return int(match.group()) if match else None


async def run_puzzle_once(*, system_prompt: str | None, reasoning_effort: str | None) -> dict:
    """One call against the puzzle, in whichever of the three styles the
    caller asks for. Returns the parsed answer plus the raw usage numbers
    needed to report tokens and hidden thinking afterward."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": TIME_TRAVEL_PUZZLE})

    kwargs = {}
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    start = time.perf_counter()
    response = await client.chat.completions.create(model=MODEL_NAME, messages=messages, **kwargs)
    elapsed = time.perf_counter() - start

    raw_text = response.choices[0].message.content or ""
    answer = extract_answer_number(raw_text)
    usage = response.usage

    return {
        "answer": answer,
        "correct": answer == PUZZLE_GROUND_TRUTH,
        "total_tokens": usage.total_tokens,
        "hidden_thinking": hidden_thinking_tokens(usage),
        "elapsed": elapsed,
    }


async def run_arm(arm_name: str, *, system_prompt: str | None, reasoning_effort: str | None) -> dict:
    """Run one reasoning style RUNS_PER_ARM times and average the results.
    Ollama's free-running local endpoint has no rate limit; Gemini's free
    tier does, so a short pause between calls here keeps this runnable
    without hand-tuning delays per provider."""
    results = []
    for run_number in range(1, RUNS_PER_ARM + 1):
        try:
            result = await run_puzzle_once(system_prompt=system_prompt, reasoning_effort=reasoning_effort)
        except RateLimitError:
            print(f"    [{arm_name}] run {run_number}: rate limited, waiting 20s and retrying")
            await asyncio.sleep(20)
            result = await run_puzzle_once(system_prompt=system_prompt, reasoning_effort=reasoning_effort)
        results.append(result)
        if PROVIDER == "gemini":
            await asyncio.sleep(2)

    correct_count = sum(1 for r in results if r["correct"])
    avg_total_tokens = sum(r["total_tokens"] for r in results) / len(results)
    avg_hidden_thinking = sum(r["hidden_thinking"] for r in results) / len(results)
    avg_elapsed = sum(r["elapsed"] for r in results) / len(results)

    return {
        "arm": arm_name,
        "correct": f"{correct_count}/{RUNS_PER_ARM}",
        "avg_total_tokens": avg_total_tokens,
        "avg_hidden_thinking": avg_hidden_thinking,
        "avg_elapsed": avg_elapsed,
    }


async def main():
    print("=" * 60)
    print("PART 1: Decomposition as its own, separate step")
    print("=" * 60)

    print("\nSTEP 1: Decomposition call breaks down the goal")
    print(f'    goal: "{GOAL}"')
    decomposition_response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
            {"role": "user", "content": GOAL},
        ],
    )
    decomposition_raw_text = decomposition_response.choices[0].message.content
    print(f"    raw response text: {decomposition_raw_text!r}")
    subproblems = parse_subproblems(decomposition_raw_text)
    print(f"    subproblems found: {subproblems.subproblems}")
    print(
        "    Note: no ordering was decided here -- decomposition only "
        "answers 'what are the pieces?', not 'in what order?'"
    )

    print("\n" + "=" * 60)
    print("PART 2: three ways to reason, on one trap")
    print("=" * 60)
    print(f"\nPuzzle: {TIME_TRAVEL_PUZZLE}")
    print(f"Ground truth (computed in code from the timeline): {PUZZLE_GROUND_TRUTH}")

    arm_results = []

    print(f"\nARM 1: plain -- no scaffolding, default settings, {RUNS_PER_ARM} runs")
    arm_results.append(await run_arm("plain", system_prompt=None, reasoning_effort=None))

    print(f"\nARM 2: chain-of-thought prompt -- default settings, {RUNS_PER_ARM} runs")
    arm_results.append(
        await run_arm("chain-of-thought", system_prompt=CHAIN_OF_THOUGHT_STRATEGY, reasoning_effort=None)
    )

    print(f"\nARM 3: built-in thinking -- no scaffolding, reasoning_effort='high', {RUNS_PER_ARM} runs")
    arm_results.append(await run_arm("built-in thinking", system_prompt=None, reasoning_effort="high"))

    print("\n" + "=" * 60)
    print(f"RESULTS (ground truth: {PUZZLE_GROUND_TRUTH})")
    print("=" * 60)
    print(f"  {'arm':<20s} {'correct':>9s} {'avg total_tokens':>18s} {'avg hidden thinking':>21s} {'avg time':>10s}")
    for result in arm_results:
        print(
            f"  {result['arm']:<20s} {result['correct']:>9s} "
            f"{result['avg_total_tokens']:>18.0f} {result['avg_hidden_thinking']:>21.0f} "
            f"{result['avg_elapsed']:>9.1f}s"
        )

    print("\n" + "=" * 60)
    print("BONUS (not graded, not part of the table above): one call asking")
    print("Gemini to actually show its thought summary via extra_body")
    print("=" * 60)
    visible = await run_puzzle_with_visible_thinking(thinking_level="high")
    if visible["reasoning_summary"]:
        print(f"\n  [thought summary]\n{visible['reasoning_summary']}\n")
    else:
        print("\n  (no reasoning_content field came back on this call/SDK version)")
    print(f"  [final answer] {visible['answer_text']}")


if __name__ == "__main__":
    asyncio.run(main())
