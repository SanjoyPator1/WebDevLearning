# ============================================================
# LISTING: 01_agent_flow_pipeline.py  (reference implementation)
# BUILDING: A 3-step sequential agent FLOW (Triage -> Billing -> Drafting)
#           with a DETERMINISTIC decision point in between -- plain Python
#           code decides whether Billing even runs, not the model.
# REF: Chapter 4 notes, sections 1 (why split an agent), 3 (the flow shape),
#      6 (splitting one agent by role), 7 (deterministic decision points)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# This is the "manual pass-off" style: our own code calls each agent in
# turn and threads one agent's output into the next agent's input. Nothing
# here uses the SDK's built-in handoff mechanism -- that comes in
# 04_agent_handoffs.py, once you've seen the manual version to compare it
# against.

import asyncio
import os

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

# A hard business rule: an agent may never approve a refund this large on
# its own. This number lives in plain Python, not in a prompt -- see
# STEP 2 in handle_ticket() below.
REFUND_ESCALATION_LIMIT = 500.0

# --- Fake billing "database" for this demo ---
_billing_records = {
    "ORD-4471": {"amount_charged": 150.0, "duplicate_charge": True},
    "ORD-9910": {"amount_charged": 800.0, "duplicate_charge": True},
}


@function_tool
def lookup_billing(order_id: str) -> dict:
    """Look up the charge history for one order ID."""
    record = _billing_records.get(
        order_id, {"amount_charged": 0.0, "duplicate_charge": False}
    )
    print(f"    [tool] lookup_billing({order_id!r}) -> {record}")
    return record


class TicketAssessment(BaseModel):
    """Structured output the Triage Agent must return -- plain code can
    check these fields directly, no prose parsing required."""

    category: str  # "billing", "technical", or "account"
    order_id: str  # empty string if this isn't a billing ticket
    refund_amount: float  # 0.0 if no refund is being requested


triage_agent = Agent(
    name="Triage Agent",
    instructions="""
    Read the support ticket and classify it as "billing", "technical", or
    "account". If it is a billing ticket asking for a refund, extract the
    order ID (format ORD-####) and the dollar amount being requested. If
    no refund is requested, set refund_amount to 0.0.
    """,
    model=model,
    output_type=TicketAssessment,
)

billing_agent = Agent(
    name="Billing Agent",
    instructions="""
    You resolve billing tickets. Call lookup_billing with the order ID you
    are given, then report in one short sentence whether the charge looks
    correct and what should happen next. Do not write the customer-facing
    reply yourself -- a different agent does that.
    """,
    model=model,
    tools=[lookup_billing],
)

drafting_agent = Agent(
    name="Drafting Agent",
    instructions="""
    Write a short, polite, customer-facing reply based on the findings you
    are given. Do not invent any facts that were not in the findings.
    """,
    model=model,
)


async def handle_ticket(ticket_text: str) -> str:
    """Run one ticket through the Triage -> [decision] -> Billing -> Drafting
    pipeline, printing every step so the flow is visible end to end."""
    print("=" * 60)
    print(f"TICKET: {ticket_text}")
    print("=" * 60)

    print("\nSTEP 1: Triage Agent classifies the ticket")
    triage_result = await Runner.run(triage_agent, ticket_text)
    assessment: TicketAssessment = triage_result.final_output
    print(
        f"    category={assessment.category!r} order_id={assessment.order_id!r} "
        f"refund_amount={assessment.refund_amount}"
    )

    print("\nSTEP 2: Deterministic decision point (plain Python, not the model)")
    if assessment.refund_amount > REFUND_ESCALATION_LIMIT:
        print(
            f"    {assessment.refund_amount} > {REFUND_ESCALATION_LIMIT} limit "
            "-> ESCALATE, skip Billing Agent entirely"
        )
        return (
            f"This ticket requests a ${assessment.refund_amount:.2f} refund, "
            f"which is above the ${REFUND_ESCALATION_LIMIT:.2f} limit an agent "
            "may approve on its own. Escalated to a human for approval."
        )
    print(
        f"    {assessment.refund_amount} <= {REFUND_ESCALATION_LIMIT} limit "
        "-> continue to Billing Agent"
    )

    print("\nSTEP 3: Billing Agent looks up the charge")
    billing_result = await Runner.run(billing_agent, assessment.model_dump_json())
    findings = billing_result.final_output
    print(f"    findings: {findings}")

    print("\nSTEP 4: Drafting Agent writes the customer-facing reply")
    drafting_result = await Runner.run(drafting_agent, findings)
    reply = drafting_result.final_output
    print(f"    reply: {reply}")
    return reply


async def main():
    tickets = [
        "My card was charged twice for order ORD-4471, and I'd like a $150 refund.",
        "My card was charged $800 in error for order ORD-9910, please refund the full amount.",
    ]
    for ticket in tickets:
        final_reply = await handle_ticket(ticket)
        print("\nFINAL OUTPUT SENT TO CUSTOMER:")
        print(final_reply)
        print()


if __name__ == "__main__":
    asyncio.run(main())
