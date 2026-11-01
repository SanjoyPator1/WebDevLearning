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
    strategy is itself a cheap, mechanical decision.

    Priority:
      1. Needs a live lookup but there's no follow-up decision hanging on
         it -> "single action, no loop needed" (the ReAct edge case).
      2. No outside info, no real fork -> either "chain-of-thought" (a
         forward computation) or "Reflexion + verifier" (a finished answer
         being rechecked), decided by result_is_checkable_after_the_fact.
      3. Needs outside info, and the steps are already known, just their
         details might move -> "plan-and-execute".
      4. Needs outside info otherwise, and the next move genuinely depends
         on what comes back -> "ReAct".
      5. A genuine fork between multiple viable paths -> "tree-of-thought".
    """
    if subtask.needs_outside_information and subtask.only_needs_a_single_tool_call:
        return "single action, no loop needed"

    if not subtask.needs_outside_information and not subtask.has_multiple_viable_paths:
        if subtask.result_is_checkable_after_the_fact:
            return "Reflexion + verifier"
        return "chain-of-thought"

    if subtask.needs_outside_information and subtask.steps_known_upfront:
        return "plan-and-execute"

    if subtask.needs_outside_information:
        return "ReAct"

    if subtask.has_multiple_viable_paths:
        return "tree-of-thought"

    return "chain-of-thought"  # unreachable given the branches above, kept as an honest fallback


def explain_strategy_choice(strategy: str) -> str:
    """One-line, human-readable rationale for a chosen strategy -- printed
    alongside each routed subtask so the "why", not just the "what", is
    visible in the output."""
    rationales = {
        "chain-of-thought": "no outside info needed, one clear path -- just show the arithmetic",
        "ReAct": "needs a live lookup and the next move depends on what comes back",
        "plan-and-execute": "the steps are already known upfront -- plan them, then fix the plan if a step's details move",
        "tree-of-thought": "a genuine fork between differently-priced, differently-risky options",
        "Reflexion + verifier": (
            "a finished, checkable answer already exists -- recheck it against "
            "ground truth, don't trust a self-report"
        ),
        "single action, no loop needed": (
            "shaped like ReAct, but it's one tool call with no follow-up decision -- "
            "the full loop would be wasted machinery"
        ),
    }
    return rationales.get(strategy, "no rule matched -- default fallback")


# --- The batch: seven trip-planning subtasks, covering all five
# strategies plus both "when the choice isn't obvious" edge cases ---
example_subtasks = [
    Subtask(
        label="Sum the three known flight leg costs against the budget",
        needs_outside_information=False,
        has_multiple_viable_paths=False,
        result_is_checkable_after_the_fact=False,
    ),
    Subtask(
        label="Check whether the City 2 hotel has a room for the conference dates, and react to what comes back",
        needs_outside_information=True,
        has_multiple_viable_paths=False,
        result_is_checkable_after_the_fact=False,
    ),
    Subtask(
        label="Book all three legs in order, knowing fares may move between planning and booking",
        needs_outside_information=True,
        has_multiple_viable_paths=False,
        result_is_checkable_after_the_fact=False,
        steps_known_upfront=True,
    ),
    Subtask(
        label="Choose a connecting hub for one flight leg: route via Doha or via Frankfurt",
        needs_outside_information=False,
        has_multiple_viable_paths=True,
        result_is_checkable_after_the_fact=False,
    ),
    Subtask(
        label="Re-check the already-finished itinerary's total against the $1,800 flight budget",
        needs_outside_information=False,
        has_multiple_viable_paths=False,
        result_is_checkable_after_the_fact=True,
    ),
    Subtask(
        label="One-shot check: is the City 1 hotel available on the exact conference dates -- nothing else hinges on the answer",
        needs_outside_information=True,
        has_multiple_viable_paths=False,
        result_is_checkable_after_the_fact=False,
        only_needs_a_single_tool_call=True,
    ),
    Subtask(
        label="Pick among three 'candidate' hotels near the venue, once filtering shows only one is actually in the right city",
        needs_outside_information=False,
        has_multiple_viable_paths=False,  # only one real option survives filtering -- not a genuine fork
        result_is_checkable_after_the_fact=False,
    ),
]


def main():
    print("=" * 60)
    print("STRATEGY SELECTOR: routing trip-planning subtasks (no model calls)")
    print("=" * 60)

    for subtask in example_subtasks:
        strategy = choose_reasoning_strategy(subtask)
        rationale = explain_strategy_choice(strategy)

        print(f"\nSubtask: {subtask.label}")
        print(
            f"    needs_outside_information={subtask.needs_outside_information} "
            f"has_multiple_viable_paths={subtask.has_multiple_viable_paths} "
            f"result_is_checkable_after_the_fact={subtask.result_is_checkable_after_the_fact} "
            f"steps_known_upfront={subtask.steps_known_upfront} "
            f"only_needs_a_single_tool_call={subtask.only_needs_a_single_tool_call}"
        )
        print(f"    -> strategy: {strategy}")
        print(f"    -> why: {rationale}")


if __name__ == "__main__":
    main()
