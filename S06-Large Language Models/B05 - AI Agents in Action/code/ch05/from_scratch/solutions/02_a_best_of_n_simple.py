# ============================================================
# LISTING: 02_a_best_of_n_simple.py  (companion file -- FROM SCRATCH, no agents SDK)
# BUILDING: Best-of-N sampling, stripped down to the smallest version that
#           still teaches the real idea. No Pydantic model, no JSON
#           parsing, no multi-factor rubric, no travel-booking domain --
#           just one number in, one number out, and a one-line score.
#           The task: ask the model to GUESS how many jellybeans are in a
#           jar, 5 independent times. Each guess is a genuine, different
#           ESTIMATE (there is no single fact to recall), which is exactly
#           the shape Best-of-N wants. Score each guess by how close it is
#           to a true count WE already know, and keep the closest one.
# REF: Chapter 5 notes, section 3 (Test-Time Compute: The Budget Behind
#      "Thinking Longer") -- this is the same pattern as
#      02_best_of_n_sampling.py with every bit of incidental complexity
#      removed, so the pattern itself is easier to see.
# COMPARE: 02_best_of_n_sampling.py in this same folder applies the
#      identical shape (generate N concurrently -> score deterministically
#      -> keep the best) to a flight-booking decision, with real
#      structured candidates and a weighted rubric. Once this file makes
#      sense, that one is the same idea with more realistic plumbing
#      around it, not a different idea.
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# Why jellybeans, specifically: "how many jellybeans are in this jar?" has
# no single correct answer the model can recall from memory -- every reply
# is a genuine, independent estimate. That is the exact situation
# Best-of-N is for: several different plausible answers, picked between by
# a rule you trust. Compare that to asking "what is 17% of $3,650?" five
# times -- there, every honest sample SHOULD converge on the same number,
# which is self-consistency's job (collections.Counter, majority wins),
# not this file's.

import asyncio
import os
import re

from dotenv import load_dotenv
from openai import AsyncOpenAI

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

JAR_DESCRIPTION = (
    "A cylindrical glass jar, about 20cm tall and 10cm across, is filled "
    "almost to the top with small jellybeans, each roughly 1.5cm long."
)

# Ground truth: a made-up jar, so WE decide the true count ahead of time.
# Never asked from a model -- same rule as Problem 01's puzzle answer.
TRUE_JELLYBEAN_COUNT = 310

SAMPLE_COUNT = 5

GUESS_SYSTEM_PROMPT = """
You are playing a jellybean-guessing game. Based on the jar description,
make your single best estimate of how many jellybeans are inside.
Answer with ONLY a number, nothing else.
""".strip()


def extract_guess(raw_text: str) -> int | None:
    """Pull the first integer out of the model's reply -- the exact same
    trick as Problem 01's extract_answer_number, reused here on purpose so
    this file introduces nothing new on the parsing side."""
    match = re.search(r"\d+", raw_text)
    return int(match.group()) if match else None


def score_guess(guess: int, true_count: int) -> int:
    """The simplest possible deterministic scorer: just the distance
    between the guess and the true count. LOWER is better here (0 would be
    a perfect guess) -- the opposite direction from the flight file's 0-10
    rubric, where higher is better. Worth noticing: "good" always depends
    on what the number actually represents, not on a fixed rule like
    "bigger wins"."""
    return abs(guess - true_count)


# --- Your turn ---
# Write:
#   1. An async sample_one_guess() -> int | None that makes ONE raw
#      chat.completions.create call (system prompt GUESS_SYSTEM_PROMPT,
#      user content JAR_DESCRIPTION), pulls the guess out of the reply
#      with extract_guess(...) (already defined above -- do not
#      reimplement it), prints the raw reply and the parsed guess, and
#      returns the guess (or None if nothing parseable came back).
#   2. An async run_best_of_n_simple(n: int) -> int | None that:
#        a. STEP 1: fires n sample_one_guess() calls CONCURRENTLY with
#           asyncio.gather. This concurrency is what makes it Best-of-N
#           rather than n sequential calls.
#        b. STEP 2: scores every guess that came back non-None with
#           score_guess(...) (already defined above), skipping any that
#           failed to parse, and prints each guess with its distance from
#           TRUE_JELLYBEAN_COUNT.
#        c. STEP 3: picks the CLOSEST guess with min(scored, key=lambda
#           pair: pair[1]) -- min, not max, because here a smaller
#           distance is better -- and prints the winner.
#      Return the winning guess (or None if nothing scored).
#
# Then write an async main() that:
#   - Prints the jar description and the true count.
#   - Calls await run_best_of_n_simple(SAMPLE_COUNT).
#   - Prints a short closing note on why this scenario calls for scoring
#     (Best-of-N) rather than voting (self-consistency): the guesses are
#     independent estimates that are not expected to agree with each
#     other, unlike a question with one right answer.
async def sample_one_guess() -> int | None:
    """One independent call: ask the model to guess, once."""
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role" : "system", "content" : GUESS_SYSTEM_PROMPT},
            {"role" : "user", "content" : JAR_DESCRIPTION}
        ]
    )

    raw_text = response.choices[0].message.content or ""

    guess = extract_guess(raw_text)

    print(f"    [sample] raw reply: {raw_text} -> guess={guess}")
    return guess


async def run_best_of_n_simple(n: int) -> int | None:
    """Ask for n independent guesses AT THE SAME TIME (asyncio.gather),
    score each one by distance from the true count, and return the
    closest. Same shape as run_best_of_n in 02_best_of_n_sampling.py:
    generate concurrently -> score with plain code -> pick the winner."""

    print(f"\nSTEP 1: asking for {n} independent guesses, concurrently")
    guesses = await asyncio.gather(*(sample_one_guess() for _ in range(n)))

    print(f"\nSTEP 2: scoring each guess against the true count ({TRUE_JELLYBEAN_COUNT})")
    scored = []
    for guess in guesses:
        if guess is None:
            print("    guess: (could not parse a number) -> skipped")
            continue
        distance = score_guess(guess, TRUE_JELLYBEAN_COUNT)
        scored.append((distance, guess))
        print(f"    guess={guess:4d}   distance from truth={distance:4d}")

    if not scored:
        print("\nNo usable guesses came back.")
        return None

    print("\nSTEP 3: picking the closest guess (smallest distance wins)")
    best_distance, best_guess = min(scored)
    print(f"    BEST-OF-{n}: {best_guess} (off by {best_distance})")
    return best_guess

async def main():
    print("=" * 60)
    print("BEST-OF-N, THE SIMPLEST POSSIBLE VERSION")
    print("=" * 60)
    print(f"\nJar: {JAR_DESCRIPTION}")
    print(f"(true count, known only to us, never told to the model: {TRUE_JELLYBEAN_COUNT})")

    await run_best_of_n_simple(SAMPLE_COUNT)

    print("\n" + "=" * 60)
    print("WHY THIS IS BEST-OF-N, NOT SELF-CONSISTENCY")
    print("=" * 60)
    print(
        "    Every guess above is a genuinely different ESTIMATE -- there is\n"
        "    no single fact to recall, so the samples are not expected to\n"
        "    agree with each other. Voting would not make sense here (five\n"
        "    different numbers, rarely any repeats). What makes one guess\n"
        "    better than another is a rule we trust -- closeness to the true\n"
        "    count -- so we SCORE and keep the best one, instead of counting\n"
        "    votes like self_consistency_vote() does in 02_best_of_n_sampling.py."
    )

if __name__ == "__main__":
    asyncio.run(main())


# TERMINAL OUTPUT
# python 02_a_best_of_n_simple.py 
# ============================================================
# BEST-OF-N, THE SIMPLEST POSSIBLE VERSION
# ============================================================

# Jar: A cylindrical glass jar, about 20cm tall and 10cm across, is filled almost to the top with small jellybeans, each roughly 1.5cm long.
# (true count, known only to us, never told to the model: 310)

# STEP 1: asking for 5 independent guesses, concurrently
#     [sample] raw reply: 550 -> guess=550
#     [sample] raw reply: 650 -> guess=650
#     [sample] raw reply: 750 -> guess=750
#     [sample] raw reply: 540 -> guess=540
#     [sample] raw reply: 750 -> guess=750

# STEP 2: scoring each guess against the true count (310)
#     guess= 550   distance from truth= 240
#     guess= 540   distance from truth= 230
#     guess= 750   distance from truth= 440
#     guess= 650   distance from truth= 340
#     guess= 750   distance from truth= 440

# STEP 3: picking the closest guess (smallest distance wins)
#     BEST-OF-5: 540 (off by 230)

# ============================================================
# WHY THIS IS BEST-OF-N, NOT SELF-CONSISTENCY
# ============================================================
#     Every guess above is a genuinely different ESTIMATE -- there is
#     no single fact to recall, so the samples are not expected to
#     agree with each other. Voting would not make sense here (five
#     different numbers, rarely any repeats). What makes one guess
#     better than another is a rule we trust -- closeness to the true
#     count -- so we SCORE and keep the best one, instead of counting
#     votes like self_consistency_vote() does in 02_best_of_n_sampling.py.
