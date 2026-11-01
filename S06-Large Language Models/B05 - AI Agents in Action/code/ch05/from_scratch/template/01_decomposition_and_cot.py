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
# is never returned as text.

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
# days they spent in the past before seeing the event's end.
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
    """OPTIONAL, not part of the graded Part 2 comparison: Gemini can return
    a *thought summary* (condensed, not the raw trace) if you ask through
    `extra_body` instead of the plain `reasoning_effort` kwarg -- the two
    cannot be combined on one call. Keep this call completely separate from
    run_arm()/RUNS_PER_ARM so it never touches the official measurement."""
    # your turn: one call with
    #   extra_body={"extra_body": {"google": {"thinking_config": {
    #       "thinking_level": thinking_level, "include_thoughts": True}}}}
    # then return {"answer_text": message.content or "",
    #              "reasoning_summary": getattr(message, "reasoning_content", None)}
    raise NotImplementedError


def hidden_thinking_tokens(usage) -> int:
    """Built-in thinking is billed but its text is never returned through
    this endpoint. The only trace of it is this gap: total_tokens counts
    it, completion_tokens does not."""
    # your turn: usage.total_tokens - usage.prompt_tokens - usage.completion_tokens
    raise NotImplementedError


def extract_answer_number(raw_text: str) -> int | None:
    """Pull the first integer out of a response, since even a model asked
    for 'just a number' sometimes wraps it in a sentence or markdown."""
    # your turn: re.search(r"-?\d+", raw_text), return int(...) or None
    raise NotImplementedError


async def run_puzzle_once(*, system_prompt: str | None, reasoning_effort: str | None) -> dict:
    """One call against the puzzle, in whichever of the three styles the
    caller asks for. Returns the parsed answer plus the raw usage numbers
    needed to report tokens and hidden thinking afterward."""
    # your turn: build messages (system_prompt only if given, then the
    # puzzle as the user message); pass reasoning_effort=reasoning_effort
    # to chat.completions.create only if it was given; time the call with
    # time.perf_counter(); extract the answer with extract_answer_number;
    # return a dict with answer, correct (answer == PUZZLE_GROUND_TRUTH),
    # total_tokens, hidden_thinking, elapsed
    raise NotImplementedError


async def run_arm(arm_name: str, *, system_prompt: str | None, reasoning_effort: str | None) -> dict:
    """Run one reasoning style RUNS_PER_ARM times and average the results.
    Catch RateLimitError, wait, and retry once -- Gemini's free tier can
    throttle a burst of calls."""
    # your turn: loop RUNS_PER_ARM times calling run_puzzle_once, collect
    # results, average total_tokens/hidden_thinking/elapsed, count how many
    # were correct, return a summary dict (see the solved file's shape)
    raise NotImplementedError


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

    # your turn: run all three arms (plain, chain-of-thought,
    # built-in thinking) with run_arm(...), collect their summaries into a
    # list, then print a table: arm name, correct count, avg total_tokens,
    # avg hidden thinking, avg elapsed time
    raise NotImplementedError

    # OPTIONAL BONUS, not required, not graded, and NOT part of the table
    # above -- once Part 2 runs cleanly and you've implemented
    # run_puzzle_with_visible_thinking, uncomment this to see Gemini's own
    # thought summary for the puzzle (a condensed version, not the raw trace):
    #
    # print("\nBONUS: one call asking Gemini to show its thought summary")
    # visible = await run_puzzle_with_visible_thinking(thinking_level="high")
    # if visible["reasoning_summary"]:
    #     print(f"  [thought summary]\n{visible['reasoning_summary']}")
    # else:
    #     print("  (no reasoning_content field came back on this call/SDK version)")
    # print(f"  [final answer] {visible['answer_text']}")


if __name__ == "__main__":
    asyncio.run(main())
