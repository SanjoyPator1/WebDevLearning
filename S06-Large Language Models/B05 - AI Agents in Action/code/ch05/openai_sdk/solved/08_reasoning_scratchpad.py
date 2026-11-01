# ============================================================
# LISTING: 08_reasoning_scratchpad.py  (reference implementation)
# BUILDING: An external, stateful ReasoningScratchpad exposed to an agent
#           as two @function_tool functions (store_thought, read_all_
#           thoughts), driven through the chapter notes' own worked
#           example: decompose, book leg 1, attempt leg 2 over budget,
#           REVISE that attempt, then fork into two named branches before
#           picking a winner.
# REF: Chapter 5 notes, section 9 (The Reasoning Scratchpad: External
#      Memory for Multi-Step Thinking)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The scratchpad itself does no reasoning -- it is a filing cabinet, not a
# thinker, exactly as the notes insist. Thoughts 1-3 are seeded directly
# by plain orchestrating code (no model call needed to decompose a goal
# and record two already-known prices); the agent only takes over once
# there is a real decision to make: how to revise the failed leg-2
# attempt and which of two connecting-hub branches to keep.

import asyncio
import os
from dataclasses import dataclass

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
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


@dataclass
class ThoughtEntry:
    """One entry on the scratchpad. `revises` points at an earlier
    entry's sequence_number when this thought corrects it (None means
    this is not a revision); `branch_id` marks this thought as belonging
    to a named alternative rather than the main spine (None means it
    continues the main spine)."""

    sequence_number: int
    thought_text: str
    revises: int | None = None
    branch_id: str | None = None


class ReasoningScratchpad:
    """External, stateful memory for an agent's reasoning steps. Entries
    persist across separate Runner.run calls, can be revised without
    being erased, and can branch off an earlier point without repeating
    the shared history that came before it (chapter notes, section 9).
    This class does no reasoning of its own -- it only stores and returns
    what it's told."""

    def __init__(self) -> None:
        self._entries: list[ThoughtEntry] = []

    def add_thought(
        self, thought_text: str, revises: int | None = None, branch_id: str | None = None
    ) -> ThoughtEntry:
        entry = ThoughtEntry(
            sequence_number=len(self._entries) + 1,
            thought_text=thought_text,
            revises=revises,
            branch_id=branch_id,
        )
        self._entries.append(entry)
        return entry

    def all_entries(self) -> list[ThoughtEntry]:
        return list(self._entries)


# Module-level shared instance -- the @function_tool functions below close
# over this one object, so every tool call reads and writes the same
# scratchpad regardless of which agent run triggered it.
_scratchpad = ReasoningScratchpad()


@function_tool
def store_thought(thought_text: str, revises: int = 0, branch_id: str = "") -> dict:
    """Store one reasoning step on the shared scratchpad.

    Args:
        thought_text: the reasoning step itself, in plain language.
        revises: the sequence_number of an earlier entry this thought
            corrects, or 0 if this is not a revision.
        branch_id: a name for the alternative this thought belongs to, or
            an empty string if this continues the main spine rather than
            branching.
    """
    entry = _scratchpad.add_thought(
        thought_text=thought_text,
        revises=revises or None,
        branch_id=branch_id or None,
    )
    revises_note = f", revises #{entry.revises}" if entry.revises else ""
    branch_note = f", branch={entry.branch_id!r}" if entry.branch_id else ""
    print(f"    [tool] store_thought(#{entry.sequence_number}{revises_note}{branch_note}): {thought_text!r}")
    return {"sequence_number": entry.sequence_number}


@function_tool
def read_all_thoughts() -> list[dict]:
    """Read back every thought stored on the scratchpad so far, in order."""
    entries = [
        {
            "sequence_number": entry.sequence_number,
            "thought_text": entry.thought_text,
            "revises": entry.revises,
            "branch_id": entry.branch_id,
        }
        for entry in _scratchpad.all_entries()
    ]
    print(f"    [tool] read_all_thoughts() -> {len(entries)} entries")
    return entries


class RoutingDecision(BaseModel):
    """Structured final output -- which branch_id the agent ultimately
    kept, and why, so the orchestrating code can print it without parsing
    prose."""

    kept_branch_id: str
    reasoning: str


routing_agent = Agent(
    name="Routing Agent",
    instructions="""
    You are continuing a trip-booking reasoning trail. Three thoughts are
    already stored on a shared scratchpad -- call read_all_thoughts if you
    want to see them. Thought 3 found that leg 2's direct fare is over
    budget. Do the following, storing EVERY reasoning step with
    store_thought before moving on to the next one:

    1. Store a thought that REVISES thought 3 (pass revises=3) explaining
       that the direct route is too expensive and a connecting route will
       be tried instead.
    2. Store a thought with branch_id="via-hub-x" proposing a connecting
       route through hub X priced at $340.
    3. Store a thought with branch_id="via-hub-y" proposing a connecting
       route through hub Y priced at $365.
    4. Compare the two branches and decide which one to keep (prefer the
       cheaper one unless you have a specific reason not to), then report
       your decision.
    """,
    model=model,
    tools=[store_thought, read_all_thoughts],
    output_type=RoutingDecision,
)


def print_scratchpad(scratchpad: ReasoningScratchpad, kept_branch_id: str | None) -> None:
    """Print the scratchpad in the notes' own spine/revision/branch shape:
    the main line of thinking down the left margin, a revision indented
    directly under it, and branches indented further and grouped by
    branch_id, with the kept branch marked."""
    entries = scratchpad.all_entries()
    spine_entries = [entry for entry in entries if entry.branch_id is None]
    branch_entries = [entry for entry in entries if entry.branch_id is not None]

    for entry in spine_entries:
        if entry.revises is None:
            print(f" thought {entry.sequence_number}: {entry.thought_text}")
        else:
            print(f"      thought {entry.sequence_number}: [revises thought {entry.revises}] {entry.thought_text}")

    branch_ids = sorted({entry.branch_id for entry in branch_entries})
    for branch_id in branch_ids:
        kept_marker = "  <-- KEPT" if branch_id == kept_branch_id else ""
        print(f"      +---- branch {branch_id!r}{kept_marker}")
        for entry in branch_entries:
            if entry.branch_id == branch_id:
                print(f"            thought {entry.sequence_number}: {entry.thought_text}")


async def main():
    print("=" * 60)
    print("REASONING SCRATCHPAD: booking leg 2 with a revision and a branch")
    print("=" * 60)

    print("\nSTEP 1: Orchestrating code seeds thoughts 1-3 directly (no model call needed for these)")
    _scratchpad.add_thought("Decompose the trip into flights, hotel, and visa paperwork.")
    _scratchpad.add_thought("Book leg 1 (home -> City 1): $410, within budget.")
    _scratchpad.add_thought("Attempt leg 2 (City 1 -> City 2) direct: $610 -- OVER BUDGET.")
    for entry in _scratchpad.all_entries():
        print(f"    seeded #{entry.sequence_number}: {entry.thought_text}")

    print("\nSTEP 2: Routing Agent takes over -- revises thought 3, then branches into two hub options")
    result = await Runner.run(
        routing_agent,
        "Leg 2's direct fare is over budget (see the scratchpad). Work out what to do "
        "next, using the scratchpad tools for every step, then tell me which branch you kept.",
    )
    decision: RoutingDecision = result.final_output
    print(f"    agent's final decision: kept branch {decision.kept_branch_id!r} -- {decision.reasoning}")

    print("\n" + "=" * 60)
    print("FULL SCRATCHPAD CONTENTS")
    print("=" * 60)
    print_scratchpad(_scratchpad, kept_branch_id=decision.kept_branch_id)


if __name__ == "__main__":
    asyncio.run(main())
