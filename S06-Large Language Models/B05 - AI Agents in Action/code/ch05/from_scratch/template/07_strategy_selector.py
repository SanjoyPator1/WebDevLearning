# ============================================================
# LISTING: 07_strategy_selector.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: A pure, deterministic router that picks which reasoning
#           strategy (chain-of-thought, ReAct, tree-of-thought, or
#           Reflexion + verifier) a trip-planning subtask calls for, based
#           on three properties of the subtask -- NOT on a model call.
#           The chapter notes are explicit that choosing a strategy is a
#           plain decision, not itself something that needs an LLM.
# REF: Chapter 5 notes, section 8 (Choosing the Right Reasoning Strategy)
# COMPARE: the SDK version of this file at ../../openai_sdk/solved/07_strategy_selector.py
# PROVIDERS: none -- this file makes ZERO model calls, on purpose, in
#            BOTH the SDK and from-scratch versions.
# ============================================================
#
# This is the deliberate exception in this set of four files. Files 05,
# 06, and 08 each replace an `agents`-SDK mechanism (output_type,
# dynamic instructions, @function_tool + Runner.run) with the raw
# chat-completions call and plain-Python bookkeeping it was hiding. This
# file has nothing to replace: the SDK version already made ZERO model
# calls, because the chapter notes are explicit that deciding WHICH
# reasoning strategy to use is itself a cheap, mechanical, three-property
# check -- exactly the kind of decision that should NOT be handed to a
# model. So the from-scratch version below is, on purpose, essentially
# the same file as the SDK version, with no `agents` import to remove and
# no provider-switch block to write, because there was never a model call
# here to begin with. The lesson worth stating plainly: not every file
# benefits from removing a framework, because not every file used one.

from pydantic import BaseModel


class Subtask(BaseModel):
    """One piece of the trip-planning goal, described by the properties
    choose_reasoning_strategy() below actually reads. The first three
    fields are the chapter's own three-property check; the fourth exists
    only to catch the ReAct edge case where the loop's full machinery
    would be wasted on a single tool call with no follow-up decision."""

    label: str
    needs_outside_information: bool
    has_multiple_viable_paths: bool
    result_is_checkable_after_the_fact: bool
    steps_known_upfront: bool = False
    only_needs_a_single_tool_call: bool = False


def choose_reasoning_strategy(subtask: Subtask) -> str:
    """Route a subtask to a reasoning strategy using plain properties of
    the subtask -- a plain `if`-chain, not a model call, since picking a
    strategy is itself a cheap, mechanical decision."""
    # your turn, in this exact priority order:
    #   a. if needs_outside_information AND only_needs_a_single_tool_call
    #      -> return "single action, no loop needed" (the ReAct edge
    #      case: shaped like ReAct, but there's no follow-up decision
    #      hanging on the one lookup, so the full loop is overkill)
    #   b. elif NOT needs_outside_information AND NOT
    #      has_multiple_viable_paths -> pure computation over things
    #      already known. If result_is_checkable_after_the_fact is True,
    #      this is a finished answer being rechecked -> return
    #      "Reflexion + verifier". Otherwise it's a forward computation
    #      -> return "chain-of-thought"
    #   c. elif needs_outside_information AND steps_known_upfront -> the
    #      order is already decided, only details might move -> return
    #      "plan-and-execute"
    #   d. elif needs_outside_information -> the next move depends on a
    #      live result -> return "ReAct"
    #   e. elif has_multiple_viable_paths -> a genuine fork worth
    #      comparing -> return "tree-of-thought"
    #   f. fall back to "chain-of-thought" (shouldn't be reachable given
    #      the branches above, but keep it as an honest default)
    raise NotImplementedError


def explain_strategy_choice(strategy: str) -> str:
    """One-line, human-readable rationale for a chosen strategy -- printed
    alongside each routed subtask so the "why", not just the "what", is
    visible in the output."""
    # your turn: a dict mapping each of the six possible strategy strings
    # ("chain-of-thought", "ReAct", "plan-and-execute", "tree-of-thought",
    # "Reflexion + verifier", "single action, no loop needed") to a
    # one-line rationale, then return rationales.get(strategy, "no rule
    # matched -- default fallback")
    raise NotImplementedError


# your turn: a list named example_subtasks of SEVEN Subtask instances
# drawn from the trip-planning scenario, covering all five strategies
# plus both edge cases -- for example: summing known flight costs
# (chain-of-thought), checking live hotel availability with a follow-up
# decision (ReAct), booking three legs in a known order where fares may
# move (plan-and-execute), routing via Doha vs. Frankfurt (tree-of-
# thought), re-checking a finished itinerary against budget (Reflexion +
# verifier), a one-shot single hotel availability check with nothing
# hinging on it (the "single action, no loop needed" edge case), and
# picking among "candidate" hotels where filtering leaves only one real
# option (the tree-of-thought edge case -- set
# has_multiple_viable_paths=False here, since after filtering there isn't
# a genuine fork anymore)
example_subtasks: list[Subtask] = []


def main() -> None:
    """Entry point: route every subtask in example_subtasks and print the
    decision. Plain, synchronous -- there are no model calls in this
    file, so no asyncio needed."""
    # your turn: loop over example_subtasks, call
    # choose_reasoning_strategy() on each (already written above), and
    # print: the subtask's label, its five property values, the chosen
    # strategy, and the one-line rationale from explain_strategy_choice()
    raise NotImplementedError


if __name__ == "__main__":
    main()
