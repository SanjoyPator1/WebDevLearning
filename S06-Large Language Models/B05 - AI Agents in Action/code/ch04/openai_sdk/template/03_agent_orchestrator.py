# ============================================================
# LISTING: 03_agent_orchestrator.py  (reference implementation)
# BUILDING: An ORCHESTRATOR agent that treats two other agents as its own
#           tools (via Agent.as_tool) and decides for itself which one to
#           call, and in what order -- unlike 01_agent_flow_pipeline.py,
#           where our own code fixed that order in advance.
# REF: Chapter 4 notes, sections 2 (decision-making authority), 3 (the
#      orchestrator shape vs. the flow shape)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# The practical test from the notes: could this central step be replaced
# by a dumb fan-out/fan-in function? Here, no -- the Orchestrator Agent is
# genuinely deciding what to do next based on the ticket, not just
# splitting one task into fixed pieces. That is what makes this an
# orchestrator rather than parallel delegation (see 02_agent_parallel_delegation.py
# for the parallel-delegation version of "many agents, one central step").

import asyncio
import os

from agents import (
    Agent,
    HandoffOutputItem,
    MessageOutputItem,
    OpenAIChatCompletionsModel,
    Runner,
    ToolCallItem,
    function_tool,
    set_tracing_disabled,
)
from dotenv import load_dotenv
from openai import AsyncOpenAI

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

# --- Fake billing "database" for this demo ---
_billing_records = {"ORD-4471": {"amount_charged": 150.0, "duplicate_charge": True}}


@function_tool
def lookup_billing(order_id: str) -> dict:
    """Look up the charge history for one order ID."""
    record = _billing_records.get(order_id, {"amount_charged": 0.0, "duplicate_charge": False})
    print(f"    [tool] lookup_billing({order_id!r}) -> {record}")
    return record


billing_agent = Agent(
    name="Billing Agent",
    instructions="""
    Call lookup_billing with the order ID you are given, then report in
    one short sentence whether the charge looks correct and what should
    happen next.
    """,
    model=model,
    tools=[lookup_billing],
)

drafting_agent = Agent(
    name="Drafting Agent",
    instructions="Write a short, polite, customer-facing reply from the findings you are given.",
    model=model,
)


def print_trace(result):
    """Print a one-line summary of every step the orchestrator actually
    took, so you can see which tools it decided to call and in what order."""
    for item in result.new_items:
        agent_name = item.agent.name if getattr(item, "agent", None) else "?"
        if isinstance(item, HandoffOutputItem):
            print(f"    [trace] HANDOFF: {item.source_agent.name} -> {item.target_agent.name}")
        elif isinstance(item, ToolCallItem):
            print(f"    [trace] {agent_name} called tool: {item.tool_name}")
        elif isinstance(item, MessageOutputItem):
            print(f"    [trace] {agent_name} produced a message")

# --- Your turn ---
# 1. Wrap billing_agent as a tool with billing_agent.as_tool(tool_name=...,
#    tool_description=...) -- pick a name like "consult_billing_agent" and
#    a description that tells a model what input it expects (the order ID).
# 2. Do the same for drafting_agent -- "consult_drafting_agent", expecting
#    findings text as input.
# 3. Build orchestrator_agent = Agent(...) with model=model and
#    tools=[billing_tool, drafting_tool]. Write instructions telling it to
#    decide for itself which tool to call and in what order, using
#    consult_billing_agent for lookups and consult_drafting_agent to write
#    the final reply.
# 4. Write an async main() that runs orchestrator_agent (only!) on the
#    ticket below via Runner.run(..., max_turns=10), calls print_trace()
#    on the result, then prints result.final_output.

ticket = "My card was charged twice for order ORD-4471, please help."

if __name__ == "__main__":
    asyncio.run(main())
