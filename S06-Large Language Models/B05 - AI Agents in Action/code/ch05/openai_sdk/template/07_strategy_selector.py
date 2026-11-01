# ============================================================
# LISTING: 07_strategy_selector.py  (reference implementation)
# BUILDING: A pure, deterministic router that picks which reasoning
#           strategy (chain-of-thought, ReAct, tree-of-thought, or
#           Reflexion + verifier) a trip-planning subtask calls for, based
#           on three properties of the subtask -- NOT on a model call.
#           The chapter notes are explicit that choosing a strategy is a
#           plain decision, not itself something that needs an LLM.
# REF: Chapter 5 notes, section 8 (Choosing the Right Reasoning Strategy)
# PROVIDERS: none -- this file makes ZERO model calls, on purpose. See the
#            BUILDING note above: routing to a strategy is exactly the
#            kind of cheap, external, mechanical decision the notes say
#            should NOT be handed to a model. The usual provider switch
#            block is intentionally omitted here rather than left in as
#            unused, dead scaffolding.
# ============================================================
#
# Three yes/no properties of a subtask do almost all of the work: does it
# need outside information, is there more than one genuinely viable path,
# and is the result something checked against reality only after the fact
# (rather than observed immediately)? This file batches six trip-planning
# subtasks through that check, including the two "when the choice isn't
# obvious" edge cases the notes call out by name.

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
    only_needs_a_single_tool_call: bool = False


# --- Your turn ---
# Write two things and then run them:
#
#   1. choose_reasoning_strategy(subtask: Subtask) -> str, implementing
#      the notes' own decision logic (section 8) as a plain if-chain, in
#      this priority order:
#        a. If needs_outside_information AND only_needs_a_single_tool_call
#           -> return "single action, no loop needed" (the ReAct edge
#           case: shaped like ReAct, but there's no follow-up decision
#           hanging on the one lookup, so the full loop is overkill).
#        b. Else if NOT needs_outside_information AND NOT
#           has_multiple_viable_paths -> this subtask is pure computation
#           over things already known. If result_is_checkable_after_the_fact
#           is True, this is a finished answer being rechecked -> return
#           "Reflexion + verifier". Otherwise it's a forward computation
#           -> return "chain-of-thought".
#        c. Else if needs_outside_information -> the next move depends on
#           a live result -> return "ReAct".
#        d. Else if has_multiple_viable_paths -> a genuine fork worth
#           comparing -> return "tree-of-thought".
#        e. Fall back to "chain-of-thought" (shouldn't be reachable given
#           the branches above, but keep it as an honest default).
#      Also write a small explain_strategy_choice(strategy: str) -> str
#      helper returning a one-line rationale for each of the five possible
#      strategy strings, for printing alongside the routing decision.
#
#   2. A list named example_subtasks of SIX Subtask instances drawn from
#      the trip-planning scenario, covering all four strategies plus both
#      edge cases -- for example: summing known flight costs (chain-of-
#      thought), checking live hotel availability with a follow-up
#      decision (ReAct), routing via Doha vs. Frankfurt (tree-of-thought),
#      re-checking a finished itinerary against budget (Reflexion +
#      verifier), a one-shot single hotel availability check with nothing
#      hinging on it (the "single action, no loop needed" edge case), and
#      picking among "candidate" hotels where filtering leaves only one
#      real option (the tree-of-thought edge case -- set
#      has_multiple_viable_paths=False here, since after filtering there
#      isn't a genuine fork anymore).
#
# Then write a main() (plain, synchronous -- there are no model calls in
# this file, so no asyncio needed) that loops over example_subtasks,
# calls choose_reasoning_strategy() on each, and prints: the subtask's
# label, its four property values, the chosen strategy, and the one-line
# rationale from explain_strategy_choice().

if __name__ == "__main__":
    main()
