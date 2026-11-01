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

RUNS_PER_ARM = 3


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
    
    messages = [{"role" : "user", "content" : TIME_TRAVEL_PUZZLE}]

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        extra_body={
            "extra_body" : {
                "google" : {
                    "thinking_config" : {
                        "thinking_level" : thinking_level,
                        "include_thoughts" : True
                    }
                }
            }
        }
    )

    message = response.choices[0].message

    content = message.content or ""
    thought_match = re.search(r"<thought>(.*?)</thought>", content, re.DOTALL)

    reasoning_summary = getattr(message, "reasoning_content", None)
    if reasoning_summary is None and thought_match:
        reasoning_summary = thought_match.group(1).strip()

    answer_text = content[thought_match.end():].strip() if thought_match else content

    return {"answer_text": answer_text, "reasoning_summary": reasoning_summary}


def hidden_thinking_tokens(usage) -> int:
    """Built-in thinking is billed but its text is never returned through
    this endpoint. The only trace of it is this gap: total_tokens counts
    it, completion_tokens does not."""
    # your turn: usage.total_tokens - usage.prompt_tokens - usage.completion_tokens
    return usage.total_tokens - usage.prompt_tokens - usage.completion_tokens



def extract_answer_number(raw_text: str) -> int | None:
    """Pull the first integer out of a response, since even a model asked
    for 'just a number' sometimes wraps it in a sentence or markdown."""
    # your turn: re.search(r"-?\d+", raw_text), return int(...) or None
    match = re.search(r"-?\d+", raw_text)
    return int(match.group()) if match else None


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
    
    messages = []

    if system_prompt:
        messages.append({"role" : "system", "content" : system_prompt})

    messages.append({"role":"user", "content" : TIME_TRAVEL_PUZZLE})

    kwargs = {}

    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    start = time.perf_counter()

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        **kwargs
    )

    elapsed = time.perf_counter() - start

    raw_text = response.choices[0].message.content
    answer = extract_answer_number(raw_text)
    usage = response.usage

    return {
        "answer" : answer,
        "correct" : answer == PUZZLE_GROUND_TRUTH,
        "total_tokens" : usage.total_tokens,
        "hidden_thinking" : hidden_thinking_tokens(usage),
        "elapsed" : elapsed
    }


async def run_arm(arm_name: str, *, system_prompt: str | None, reasoning_effort: str | None) -> dict:
    """Run one reasoning style RUNS_PER_ARM times and average the results.
    Catch RateLimitError, wait, and retry once -- Gemini's free tier can
    throttle a burst of calls."""
    # your turn: loop RUNS_PER_ARM times calling run_puzzle_once, collect
    # results, average total_tokens/hidden_thinking/elapsed, count how many
    # were correct, return a summary dict (see the solved file's shape)
    
    results = []

    for run_number in range(1, RUNS_PER_ARM + 1):
        try:
            print(f"run :{run_number} : calling run puzzle normally")
            result = await run_puzzle_once(system_prompt=system_prompt, reasoning_effort=reasoning_effort)
            print(f"run :{run_number} : got result normally")
        except RateLimitError:
            print(f"    [{arm_name}] run {run_number}: rate limited, waiting 20s and retrying")
            await asyncio.sleep(20)
            result = await run_puzzle_once(system_prompt=system_prompt, reasoning_effort=reasoning_effort)
            print(f"run :{run_number} : got result after rate limit")

        print(f"    answer = {result['answer']}, correct = {result['correct']}")
        results.append(result)

        if PROVIDER == "gemini":
            print(f"    provider is gemini sleep for 2")
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

    # your turn: run all three arms (plain, chain-of-thought,
    # built-in thinking) with run_arm(...), collect their summaries into a
    # list, then print a table: arm name, correct count, avg total_tokens,
    # avg hidden thinking, avg elapsed time
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

    # OPTIONAL BONUS, not required, not graded, and NOT part of the table
    # above -- once Part 2 runs cleanly and you've implemented
    # run_puzzle_with_visible_thinking, uncomment this to see Gemini's own
    # thought summary for the puzzle (a condensed version, not the raw trace):
    #
    print("\nBONUS: one call asking Gemini to show its thought summary")
    visible = await run_puzzle_with_visible_thinking(thinking_level="high")
    if visible["reasoning_summary"]:
        print(f"  [thought summary]\n{visible['reasoning_summary']}")
    else:
        print("  (no reasoning_content field came back on this call/SDK version)")
    print(f"  [final answer] {visible['answer_text']}")


if __name__ == "__main__":
    asyncio.run(main())

# TERMINAL OUTPUT

# python 01_decomposition_and_cot.py 
# ============================================================
# PART 1: Decomposition as its own, separate step
# ============================================================

# STEP 1: Decomposition call breaks down the goal
#     goal: "book my 3-city conference trip"
#     raw response text: '{"subproblems": ["Flight from origin to first city", "Hotel in first city", "Flight from first city to second city", "Hotel in second city", "Flight from second city to third city", "Hotel in third city", "Flight from third city back to origin", "Conference registration"]}'
#     subproblems found: ['Flight from origin to first city', 'Hotel in first city', 'Flight from first city to second city', 'Hotel in second city', 'Flight from second city to third city', 'Hotel in third city', 'Flight from third city back to origin', 'Conference registration']
#     Note: no ordering was decided here -- decomposition only answers 'what are the pieces?', not 'in what order?'

# ============================================================
# PART 2: three ways to reason, on one trap
# ============================================================

# Puzzle: A traveler starts in the present and goes back 100 years, arriving 3 days
# before a 10-day historical event. After spending 6 days there, they jump
# forward 50 years and stay 20 days. Then they jump back to see the last
# day of the event. How many days did they spend in the past before seeing
# the end of the event? Answer with just a number.
# Ground truth (computed in code from the timeline): 26

# ARM 1: plain -- no scaffolding, default settings, 3 runs
# run :1 : calling run puzzle normally
# run :1 : got result normally
#     answer = 1, correct = False
#     provider is gemini sleep for 2
# run :2 : calling run puzzle normally
# run :2 : got result normally
#     answer = 6, correct = False
#     provider is gemini sleep for 2
# run :3 : calling run puzzle normally
# run :3 : got result normally
#     answer = 1, correct = False
#     provider is gemini sleep for 2

# ARM 2: chain-of-thought prompt -- default settings, 3 runs
# run :1 : calling run puzzle normally
# run :1 : got result normally
#     answer = 1, correct = False
#     provider is gemini sleep for 2
# run :2 : calling run puzzle normally
# run :2 : got result normally
#     answer = 1, correct = False
#     provider is gemini sleep for 2
# run :3 : calling run puzzle normally
# run :3 : got result normally
#     answer = 1, correct = False
#     provider is gemini sleep for 2

# ARM 3: built-in thinking -- no scaffolding, reasoning_effort='high', 3 runs
# run :1 : calling run puzzle normally
# run :1 : got result normally
#     answer = 26, correct = True
#     provider is gemini sleep for 2
# run :2 : calling run puzzle normally
# run :2 : got result normally
#     answer = 26, correct = True
#     provider is gemini sleep for 2
# run :3 : calling run puzzle normally
# run :3 : got result normally
#     answer = 26, correct = True
#     provider is gemini sleep for 2

# ============================================================
# RESULTS (ground truth: 26)
# ============================================================
#   arm                    correct   avg total_tokens   avg hidden thinking   avg time
#   plain                      0/3                377                     0       1.8s
#   chain-of-thought           0/3                659                     0       2.0s
#   built-in thinking          3/3               1486                  1393       4.2s

# BONUS: one call asking Gemini to show its thought summary
#   [thought summary]
# **Analyzing the Time Traveler's Itinerary**

# Okay, let's break this down. We have a time traveler, and we need to determine the total number of days spent "in the past" (or at any time prior to the final observation) before witnessing the end of a specific 10-day historical event.

# First, I need to define the event's timeline. Let the event begin at Day 0, ending on Day 9.  The traveler first arrives three days *before* the start of this event, which puts them at Day -3. They then spend six days there. So, their time at this first location spans days -3, -2, -1, 0, 1, and 2.

# Next, they jump forward 50 years and stay for 20 days. Now, the prompt doesn't specify *where* they're jumping relative to the event's timeline, only that they stay for 20 days after the jump. We just count those 20 days of the second stay.

# Finally, they jump back to see the *last* day of the event, Day 9.

# To calculate the answer, I need to sum the total days "in the past". These are the days they stayed prior to the final jump to observe the end of the event.
# The first stay: 6 days.
# The second stay: 20 days.
# Therefore, the total number of days is 6 + 20 = 26.

# I need to make sure I am not missing any subtle points, such as days of travel.

# I've carefully considered the time jumps and stays and I'm confident my answer is correct. The total days spent before observing the end of the event is simply 6 days + 20 days = 26 days.
#   [final answer] 26