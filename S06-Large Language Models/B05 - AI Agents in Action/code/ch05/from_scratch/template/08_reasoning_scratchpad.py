# ============================================================
# LISTING: 08_reasoning_scratchpad.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: An external, stateful ReasoningScratchpad exposed to the model
#           as two raw OpenAI-format tools (store_thought, read_all_
#           thoughts), driven through the chapter notes' own worked
#           example: decompose, book leg 1, attempt leg 2 over budget,
#           REVISE that attempt, then fork into two named branches before
#           picking a winner.
# REF: Chapter 5 notes, section 9 (The Reasoning Scratchpad: External
#      Memory for Multi-Step Thinking)
# COMPARE: the SDK version of this file at ../../openai_sdk/solved/08_reasoning_scratchpad.py
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The SDK version hid three things inside Runner.run(): the growing
# `messages` list itself (the SDK tracks conversation state for you), the
# reason-act-observe LOOP that keeps calling the model and dispatching
# whatever tools it asks for until it stops asking, and the wiring that
# turns @function_tool-decorated Python functions into tool schemas the
# provider understands. All three are made visible here. run_tool_loop()
# below IS the reason-act-observe loop, written out by hand: call the
# model, check message.tool_calls, dispatch each one through a plain
# tool_handlers dict, append the tool results back onto messages as
# role="tool" entries, and repeat. store_thought and read_all_thoughts
# are plain OpenAI tool-schema dicts plus plain Python handler functions
# closing over the same shared ReasoningScratchpad instance -- there is
# no decorator doing this conversion invisibly. Finally, where the SDK
# version combined tools=[...] with output_type=RoutingDecision in one
# Agent, here the model is told directly, once it is done calling tools,
# to respond with a final plain-text JSON object matching RoutingDecision
# -- parsed and validated by hand exactly like files 05 and 06.
#
# The scratchpad itself does no reasoning -- it is a filing cabinet, not a
# thinker, exactly as the notes insist. Thoughts 1-3 are seeded directly
# by plain orchestrating code (no model call needed to decompose a goal
# and record two already-known prices); the model only takes over once
# there is a real decision to make: how to revise the failed leg-2
# attempt and which of two connecting-hub branches to keep.

import asyncio
import json
import os
from dataclasses import dataclass

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
    """External, stateful memory for the model's reasoning steps. Entries
    persist across separate chat-completions calls, can be revised
    without being erased, and can branch off an earlier point without
    repeating the shared history that came before it (chapter notes,
    section 9). This class does no reasoning of its own -- it only stores
    and returns what it's told."""

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


# Module-level shared instance -- the tool handler functions below close
# over this one object, so every tool call reads and writes the same
# scratchpad regardless of which loop step triggered it.
_scratchpad = ReasoningScratchpad()


def handle_store_thought(thought_text: str, revises: int = 0, branch_id: str = "") -> dict:
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


def handle_read_all_thoughts() -> list[dict]:
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


# Raw OpenAI tool-definition dicts -- what @function_tool built for us
# invisibly in the SDK version, written out by hand here.
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "store_thought",
            "description": "Store one reasoning step on the shared scratchpad.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought_text": {
                        "type": "string",
                        "description": "the reasoning step itself, in plain language",
                    },
                    "revises": {
                        "type": "integer",
                        "description": "the sequence_number of an earlier entry this thought corrects, or 0 if this is not a revision",
                    },
                    "branch_id": {
                        "type": "string",
                        "description": "a name for the alternative this thought belongs to, or an empty string to continue the main spine",
                    },
                },
                "required": ["thought_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_all_thoughts",
            "description": "Read back every thought stored on the scratchpad so far, in order.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# Dispatch table the tool loop uses to turn a tool_call.function.name back
# into the plain Python function that actually does the work.
tool_handlers = {
    "store_thought": handle_store_thought,
    "read_all_thoughts": handle_read_all_thoughts,
}


class RoutingDecision(BaseModel):
    """Structured final output -- which branch_id the model ultimately
    kept, and why, so the orchestrating code can print it without parsing
    prose."""

    kept_branch_id: str
    reasoning: str


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=10):
    """The reason-act-observe loop itself, made visible: call the model,
    dispatch whatever tool calls it asked for, append the results, and
    repeat until the model stops calling tools or the step budget runs
    out. This is exactly what Runner.run(..., max_turns=...) was doing
    for us invisibly in the SDK version of this file. Deliberately
    minimal -- no result-size capping, no persisted debug log, no MCP, no
    structured-termination dataclass; a real production harness typically
    layers truncation and richer termination tracking on top of this same
    basic shape."""
    for step in range(max_steps):
        print(f"\n--- loop step {step + 1} ---")
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            print("  model returned no tool calls -- loop is done")
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, "no_tool_calls", step + 1

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            print(f"  tool call: {tool_call.function.name}({arguments})")
            handler = tool_handlers[tool_call.function.name]
            result = handler(**arguments)
            if hasattr(result, "__await__"):
                result = await result
            print(f"  tool result: {result}")
            messages.append({
                "role": "tool", "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })

    print(f"  step budget ({max_steps}) exhausted")
    return messages, "budget", max_steps


def print_scratchpad(scratchpad: ReasoningScratchpad, kept_branch_id: str | None) -> None:
    """Print the scratchpad in the notes' own spine/revision/branch shape:
    the main line of thinking down the left margin, a revision indented
    directly under it, and branches indented further and grouped by
    branch_id, with the kept branch marked."""
    # your turn:
    #   1. split scratchpad.all_entries() into spine_entries (branch_id is
    #      None) and branch_entries (branch_id is not None)
    #   2. for each spine entry: if it's not a revision (revises is None),
    #      print " thought <n>: <text>". If it IS a revision, print it
    #      indented further with a "[revises thought <k>]" marker, e.g.
    #      "      thought <n>: [revises thought <k>] <text>"
    #   3. collect the sorted set of distinct branch_ids among
    #      branch_entries. For each branch_id, print a header line like
    #      "      +---- branch '<branch_id>'", appending "  <-- KEPT" if
    #      branch_id == kept_branch_id, then print each entry belonging to
    #      that branch_id further indented underneath
    raise NotImplementedError


async def main() -> None:
    """Entry point: seed the known facts, hand the model the scratchpad
    tools to revise and branch, then print its final decision and the
    full scratchpad structure."""
    # your turn:
    #   STEP 1 (seed, no model call): print a banner, then seed thoughts
    #     1-3 directly via _scratchpad.add_thought(...) -- decomposing the
    #     goal and recording two already-known prices doesn't need a
    #     model call:
    #       "Decompose the trip into flights, hotel, and visa paperwork."
    #       "Book leg 1 (home -> City 1): $410, within budget."
    #       "Attempt leg 2 (City 1 -> City 2) direct: $610 -- OVER BUDGET."
    #     Print each seeded thought as it's added.
    #
    #   STEP 2 (build the prompt): a system prompt telling the model:
    #     three thoughts are already on the shared scratchpad (it can
    #     call read_all_thoughts to see them), thought 3 found leg 2's
    #     direct fare is over budget, and it must -- storing EVERY step
    #     with store_thought before moving on --
    #       a. store a thought that REVISES thought 3 (revises=3) saying
    #          the direct route is too expensive and a connecting route
    #          will be tried instead,
    #       b. store a thought with branch_id="via-hub-x" proposing a
    #          connection through hub X at $340,
    #       c. store a thought with branch_id="via-hub-y" proposing a
    #          connection through hub Y at $365,
    #       d. compare the two branches and pick one to keep (prefer the
    #          cheaper one absent a reason not to),
    #     ending with an instruction that once all four thoughts are
    #     stored, it must respond with ONLY a JSON object shaped like
    #     {"kept_branch_id": "...", "reasoning": "..."} and no more tool
    #     calls or other text.
    #
    #   STEP 3 (run the loop): messages = [{"role": "system", ...},
    #     {"role": "user", "content": "<tell it leg 2 is over budget,
    #     work out what to do next using the scratchpad tools for every
    #     step, then report which branch it kept>"}]. Call `await
    #     run_tool_loop(messages, tools_schema, tool_handlers,
    #     max_steps=10)` (already defined above), print the stop_reason
    #     and steps_used it returns.
    #
    #   STEP 4 (parse the final decision): read the final assistant
    #     content off the returned messages list (messages[-1]["content"]),
    #     parse with json.loads, validate into RoutingDecision with
    #     RoutingDecision.model_validate(...) -- wrapped in a try/except
    #     catching (json.JSONDecodeError, ValidationError) that prints a
    #     clear error plus the raw text, then re-raises. Print the
    #     decision's kept_branch_id and reasoning.
    #
    #   STEP 5 (show the result): call print_scratchpad(_scratchpad,
    #     kept_branch_id=decision.kept_branch_id) (already defined above)
    #     to show the full, final scratchpad structure.
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
