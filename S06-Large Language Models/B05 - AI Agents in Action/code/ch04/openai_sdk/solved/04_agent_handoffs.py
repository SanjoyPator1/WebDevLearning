# ============================================================
# LISTING: 04_agent_handoffs.py  (reference implementation)
# BUILDING: The SAME three-agent idea as 01_agent_flow_pipeline.py, but
#           wired with the SDK's built-in handoff mechanism instead of our
#           own pass-off code -- each agent is told, in its own
#           instructions, which peer to transfer control to. An on_handoff
#           callback lets us watch what data actually crosses each
#           boundary, since a handoff is otherwise a black box from the
#           outside.
# REF: Chapter 4 notes, section 8 (handoffs: letting agents route themselves)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# Compare this file line-for-line against 01_agent_flow_pipeline.py: the
# three agents do the same jobs, but here we only ever call Runner.run()
# ONCE, on the entry-point agent. Everything after that happens because
# each agent's own instructions say who to hand off to next.

import asyncio
import os

from agents import (
    Agent,
    HandoffOutputItem,
    MessageOutputItem,
    OpenAIChatCompletionsModel,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    function_tool,
    handoff,
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

# --- Fake billing "database" for this demo ---
_billing_records = {"ORD-4471": {"amount_charged": 150.0, "duplicate_charge": True}}


@function_tool
def lookup_billing(order_id: str) -> dict:
    """Look up the charge history for one order ID."""
    record = _billing_records.get(order_id, {"amount_charged": 0.0, "duplicate_charge": False})
    print(f"    [tool] lookup_billing({order_id!r}) -> {record}")
    return record


class TicketCategory(BaseModel):
    """This is the shape of data the Triage Agent hands to the Billing
    Agent at handoff time -- the handoff's own input schema."""

    category: str  # "billing", "technical", or "account"
    order_id: str  # empty string if no order was mentioned


# Build the chain from the END backwards, since each agent needs to know
# about the agent (or handoff) it points to.

drafting_agent = Agent(
    name="Drafting Agent",
    instructions="Write a short, polite, customer-facing reply from the findings you receive.",
    model=model,
)

billing_agent = Agent(
    name="Billing Agent",
    instructions="""
    Call lookup_billing using the order_id you were handed. Then ALWAYS
    hand off to the Drafting Agent with a one-sentence summary of what you
    found -- never write the final customer reply yourself.
    """,
    model=model,
    tools=[lookup_billing],
    handoffs=[drafting_agent],
)


async def log_handoff_to_billing(ctx: RunContextWrapper, data: TicketCategory):
    """Fires the moment Triage hands off -- purely for observing what
    crosses the boundary, it does not get a vote on whether it proceeds."""
    print(
        f"    [on_handoff] Triage -> Billing, carrying: "
        f"category={data.category!r} order_id={data.order_id!r}"
    )


triage_to_billing_handoff = handoff(
    agent=billing_agent,
    on_handoff=log_handoff_to_billing,
    input_type=TicketCategory,
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="""
    Classify the ticket as "billing", "technical", or "account", and
    extract the order_id if one is mentioned (format ORD-####, empty
    string if none). Always hand off to the Billing Agent for billing
    tickets.
    """,
    model=model,
    handoffs=[triage_to_billing_handoff],
)


def print_trace(result):
    """Print a one-line summary of every step the run actually took,
    including every handoff, so the flow is visible from the outside."""
    for item in result.new_items:
        agent_name = item.agent.name if getattr(item, "agent", None) else "?"
        if isinstance(item, HandoffOutputItem):
            print(f"    [trace] HANDOFF: {item.source_agent.name} -> {item.target_agent.name}")
        elif isinstance(item, ToolCallItem):
            print(f"    [trace] {agent_name} called tool: {item.tool_name}")
        elif isinstance(item, MessageOutputItem):
            print(f"    [trace] {agent_name} produced a message")


async def main():
    ticket = "My card was charged twice for order ORD-4471, please help."
    print(f"TICKET: {ticket}\n")
    print("Running only the Triage Agent -- everything else happens via handoff:")
    # max_turns is a real safety limit: without one, a misconfigured chain
    # of handoffs could keep passing control back and forth indefinitely.
    result = await Runner.run(triage_agent, ticket, max_turns=10)

    print("\n--- trace of what actually happened ---")
    print_trace(result)

    print("\nFINAL OUTPUT:")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
