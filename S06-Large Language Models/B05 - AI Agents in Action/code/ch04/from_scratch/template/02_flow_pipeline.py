# Problem 02 -- a fixed pipeline (triage -> gate -> billing -> drafting)
# with the gate decided by plain Python, and every stage protected by a
# retry with exponential backoff and jitter.

import asyncio
import json
import os
import random
from typing import Literal

import openai
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

# --- shared support desk data and tools (given) ---

ORDERS = {
    "ORD-4471": {"customer_id": "C-100", "amount": 150.0, "times_charged": 2},
    "ORD-9910": {"customer_id": "C-300", "amount": 800.0, "times_charged": 1},
    "ORD-2002": {"customer_id": "C-200", "amount": 45.0, "times_charged": 1},
}


def lookup_order(order_id: str) -> dict:
    """Look up an order: its customer, amount, and how many times it was charged."""
    if order_id not in ORDERS:
        raise ValueError(f"no such order: {order_id}")
    return {"order_id": order_id, **ORDERS[order_id]}


def issue_refund(order_id: str, amount: float) -> dict:
    """Issue a refund for an order. This is irreversible; amount cannot exceed the order total."""
    if order_id not in ORDERS:
        raise ValueError(f"no such order: {order_id}")
    order = ORDERS[order_id]
    if amount > order["amount"]:
        raise ValueError(f"refund amount {amount} exceeds order amount {order['amount']}")
    return {"order_id": order_id, "amount": amount, "status": "issued"}


TOOL_FUNCTIONS = {"lookup_order": lookup_order, "issue_refund": issue_refund}

TOOL_SCHEMAS = {
    "lookup_order": {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": lookup_order.__doc__,
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    "issue_refund": {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": issue_refund.__doc__,
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
                "required": ["order_id", "amount"],
            },
        },
    },
}


def select_tools(names: list[str]) -> tuple[list[dict], dict]:
    """Pick out the OpenAI tool schemas and handler functions for just the
    named tools -- this is how each agent in this chapter gets only the
    tools its role needs."""
    schemas = [TOOL_SCHEMAS[name] for name in names]
    handlers = {name: TOOL_FUNCTIONS[name] for name in names}
    return schemas, handlers


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6):
    """The chapter 2 tool-calling loop: call the model, dispatch any tool
    calls, feed results back, repeat until the model stops or the step
    budget runs out."""
    for _ in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema or None
        )
        message = response.choices[0].message

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, message.content or ""

        messages.append(
            {"role": "assistant", "tool_calls": [tc.model_dump() for tc in message.tool_calls]}
        )

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            handler = tool_handlers[tool_call.function.name]
            try:
                result_text = json.dumps(handler(**arguments), default=str)
            except ValueError as error:
                result_text = f"ERROR: {error}"
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
            )

    return messages, None


# --- the pipeline itself ---

REFUND_APPROVAL_LIMIT = 500.0

FAILURE_RATE = 0.5
_rng = random.Random(7)


class SimulatedOutage(Exception):
    """A stand-in for a transient failure (rate limit, network blip) you
    would see for real against a live API."""


def maybe_fail(stage_name: str) -> None:
    if _rng.random() < FAILURE_RATE:
        raise SimulatedOutage(f"{stage_name} hit a simulated transient failure")


class TicketAssessment(BaseModel):
    order_id: str
    issue: Literal["duplicate_charge", "wrong_amount", "other"]
    refund_requested: float


TRANSIENT_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    SimulatedOutage,
)


async def with_retry(stage_fn, *args, max_attempts=4, base_delay=0.5):
    """Retry a stage on a transient error, waiting longer each time with
    some randomness so repeated callers do not all retry at once."""
    # your turn: loop up to max_attempts, catching TRANSIENT_ERRORS;
    # on failure (not the last attempt) wait random.uniform(0, base_delay * 2**attempt)
    # and print what happened; on the last attempt, let the exception raise
    raise NotImplementedError


async def run_triage(ticket_text: str) -> TicketAssessment:
    maybe_fail("triage")
    # your turn: structured-output call (response_format=TicketAssessment)
    # extracting order_id, issue, refund_requested from ticket_text
    raise NotImplementedError


async def run_billing_step(assessment: TicketAssessment) -> str:
    maybe_fail("billing")
    # your turn: select_tools(["lookup_order"]), run_tool_loop, return the findings
    raise NotImplementedError


async def run_drafting_step(findings: str) -> str:
    maybe_fail("drafting")
    # your turn: a plain completion call (no tools) turning findings into a reply
    raise NotImplementedError


async def handle_ticket(ticket_text: str) -> str:
    # your turn: with_retry(run_triage, ...), then the two-part gate (order
    # exists via a direct lookup_order call, and refund_requested <=
    # REFUND_APPROVAL_LIMIT), then with_retry around billing and drafting --
    # print each stage's result and return the final reply
    raise NotImplementedError


async def main() -> None:
    tickets = [
        "My card was charged twice for order ORD-4471, and I'd like a $150 refund.",
        "My card was charged $800 in error for order ORD-9910, please refund the full amount.",
        "I was charged for order ORD-0000 and I don't recognize it.",
    ]

    for i, ticket_text in enumerate(tickets, start=1):
        print(f"\nTICKET {i}: {ticket_text}")
        reply = await handle_ticket(ticket_text)
        print(f"  REPLY: {reply}")


if __name__ == "__main__":
    asyncio.run(main())
