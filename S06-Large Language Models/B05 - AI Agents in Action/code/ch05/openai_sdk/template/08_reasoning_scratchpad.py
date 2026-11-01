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


# --- Your turn ---
# Define the agent, drive it through the sequence, and print the result.
#
#   1. RoutingDecision(BaseModel): a structured final output with
#      kept_branch_id: str and reasoning: str, so the orchestrating code
#      can read which branch the agent kept without parsing prose.
#
#   2. routing_agent = Agent(...) with tools=[store_thought,
#      read_all_thoughts], output_type=RoutingDecision, and instructions
#      telling it: three thoughts are already on the shared scratchpad
#      (it can call read_all_thoughts to see them), thought 3 found that
#      leg 2's direct fare is over budget, and it must -- storing EVERY
#      step with store_thought before moving on --
#        a. store a thought that REVISES thought 3 (revises=3) saying the
#           direct route is too expensive and a connecting route will be
#           tried instead,
#        b. store a thought with branch_id="via-hub-x" proposing a
#           connection through hub X at $340,
#        c. store a thought with branch_id="via-hub-y" proposing a
#           connection through hub Y at $365,
#        d. compare the two branches and report which one it's keeping
#           (prefer the cheaper one absent a reason not to).
#
#   3. def print_scratchpad(scratchpad, kept_branch_id): prints every
#      entry in the notes' own spine/revision/branch shape -- the main
#      line of thinking down the left margin, a revision indented
#      directly under the entry it corrects, and branches indented
#      further and grouped by branch_id, with the kept branch clearly
#      marked (e.g. append "<-- KEPT" next to its branch header).
#
#   4. An async main() that:
#        a. Seeds thoughts 1-3 directly via _scratchpad.add_thought(...)
#           (no model call for this part -- decomposing the goal and
#           recording two already-known prices doesn't need one):
#             "Decompose the trip into flights, hotel, and visa paperwork."
#             "Book leg 1 (home -> City 1): $410, within budget."
#             "Attempt leg 2 (City 1 -> City 2) direct: $610 -- OVER BUDGET."
#           Print each seeded thought.
#        b. Runs routing_agent via Runner.run(...) with a prompt telling
#           it leg 2 is over budget and to work out what to do next using
#           the scratchpad tools, then report which branch it kept.
#        c. Prints the agent's final kept_branch_id and reasoning.
#        d. Calls print_scratchpad(_scratchpad, kept_branch_id=...) to
#           show the full, final scratchpad structure.

if __name__ == "__main__":
    asyncio.run(main())
