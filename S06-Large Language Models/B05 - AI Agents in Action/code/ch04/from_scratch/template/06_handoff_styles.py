# Problem 06 -- the same triage -> billing -> drafting handoff chain, done
# three ways: a shared thread, a small typed package, and a filtered
# thread. Each style is measured in prompt_tokens.

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

TICKET = "My card was charged twice for order ORD-4471, and I'd like a $150 refund."

# --- shared support desk data and tools (just the one billing needs) (given) ---

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


LOOKUP_ORDER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_order",
        "description": lookup_order.__doc__,
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
    },
}

TRANSFER_TO_BILLING_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transfer_to_billing",
        "description": "Hand the ticket off to the billing agent. Call this once you know the order id and the issue.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "issue": {"type": "string"}},
            "required": ["order_id", "issue"],
        },
    },
}

TRANSFER_TO_DRAFTING_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transfer_to_drafting",
        "description": "Hand the ticket off to the drafting agent once billing is confirmed.",
        "parameters": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
}

TRIAGE_PROMPT = "You are a triage assistant. Read the ticket, then call transfer_to_billing with the order id and issue."
BILLING_PROMPT = "You are a billing assistant. Use lookup_order to confirm the issue, then call transfer_to_drafting with a one-sentence summary."
DRAFTING_PROMPT = "You are a drafting assistant. Turn the summary into a short, friendly reply. Do not call any tools."


class BillingHandoff(BaseModel):
    order_id: str
    issue: str


class DraftingHandoff(BaseModel):
    summary: str


async def run_stage(messages, tools_schema, tool_handlers, handoff_names, stats):
    """Run one agent's turn(s) until it either hands off (returns a dict with
    kind='handoff') or produces a final text answer (kind='final'). Real
    tool calls are dispatched and looped on exactly like run_tool_loop;
    a handoff tool call is detected by name, acknowledged with a tool
    message (so the API's tool_calls/tool_result pairing stays valid), and
    returned immediately."""
    for _ in range(6):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema or None
        )
        stats["calls"] += 1
        stats["prompt_tokens"] += response.usage.prompt_tokens
        message = response.choices[0].message

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, {"kind": "final", "text": message.content or ""}

        messages.append(
            {"role": "assistant", "tool_calls": [tc.model_dump() for tc in message.tool_calls]}
        )

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if name in handoff_names:
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(arguments)})
                return messages, {"kind": "handoff", "name": name, "args": arguments}

            handler = tool_handlers[name]
            try:
                result_text = json.dumps(handler(**arguments), default=str)
            except ValueError as error:
                result_text = f"ERROR: {error}"
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_text})

    return messages, {"kind": "final", "text": None}


def filter_history(messages: list[dict]) -> list[dict]:
    """Keep the conversation (user and plain assistant text), drop every
    tool call and tool result -- the chapter 3 'remove all tools' filter."""
    # your turn: keep messages[0] (the system message, replaced by the
    # caller anyway), and from the rest, drop any role=="tool" message and
    # any role=="assistant" message that has "tool_calls" in it
    raise NotImplementedError


def fresh_stats() -> dict:
    return {"calls": 0, "prompt_tokens": 0}


async def run_style_a_shared_thread(ticket_text: str) -> tuple[str, dict]:
    """Style A: one messages list for the whole chain. Each agent sees
    everything every earlier agent said and did."""
    # your turn: triage with TRANSFER_TO_BILLING_SCHEMA only, log the
    # handoff, swap messages[0] to BILLING_PROMPT and keep the SAME list,
    # billing with [LOOKUP_ORDER_SCHEMA, TRANSFER_TO_DRAFTING_SCHEMA], log
    # that handoff, swap messages[0] to DRAFTING_PROMPT, drafting with no tools
    raise NotImplementedError


async def run_style_b_package_only(ticket_text: str) -> tuple[str, dict]:
    """Style B: each agent starts with a fresh messages list holding only
    the package handed to it, validated with Pydantic along the way."""
    # your turn: same three stages, but each one gets a brand NEW messages
    # list containing only its system prompt plus the validated package
    # (BillingHandoff / DraftingHandoff) from the previous stage's handoff
    raise NotImplementedError


async def run_style_c_filtered_thread(ticket_text: str) -> tuple[str, dict]:
    """Style C: like the shared thread, but tool calls and tool results are
    stripped out of the history before each handoff."""
    # your turn: same as style A, but call filter_history(messages) right
    # after each handoff, before swapping in the next system prompt
    raise NotImplementedError


def print_stats(stats: dict) -> None:
    total = 0
    for name, s in stats.items():
        print(f"  {name:8s} : prompt_tokens {s['prompt_tokens']:5d}")
        total += s["prompt_tokens"]
    print(f"  total    : {total}")


def draw_handoff_graph(agents: list[dict]) -> None:
    """Stretch: a text diagram of the handoff wiring, generated from a plain
    list of {name, tools, hands_off_to} dicts rather than typed by hand."""
    for agent in agents:
        tools = ", ".join(agent["tools"]) or "(none)"
        print(f"  [{agent['name']}]  tools: {tools}")
        for target in agent["hands_off_to"]:
            print(f"      --> {target}")


async def main() -> None:
    print("STYLE A: shared thread")
    _, stats_a = await run_style_a_shared_thread(TICKET)
    print_stats(stats_a)

    print("\nSTYLE B: pass only the package")
    _, stats_b = await run_style_b_package_only(TICKET)
    print_stats(stats_b)

    print("\nSTYLE C: filtered thread")
    _, stats_c = await run_style_c_filtered_thread(TICKET)
    print_stats(stats_c)

    print("\nHANDOFF GRAPH")
    draw_handoff_graph(
        [
            {"name": "triage", "tools": [], "hands_off_to": ["billing"]},
            {"name": "billing", "tools": ["lookup_order"], "hands_off_to": ["drafting"]},
            {"name": "drafting", "tools": [], "hands_off_to": []},
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())
