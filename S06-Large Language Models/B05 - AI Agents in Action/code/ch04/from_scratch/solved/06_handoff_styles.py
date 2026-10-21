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

# --- shared support desk data and tools (just the one billing needs) ---

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
    kept = [messages[0]]  # the system message, swapped by the caller anyway
    for message in messages[1:]:
        if message["role"] == "tool":
            continue
        if message["role"] == "assistant" and "tool_calls" in message:
            continue
        kept.append(message)
    return kept


def fresh_stats() -> dict:
    return {"calls": 0, "prompt_tokens": 0}


async def run_style_a_shared_thread(ticket_text: str) -> tuple[str, dict]:
    """Style A: one messages list for the whole chain. Each agent sees
    everything every earlier agent said and did."""
    stats = {"triage": fresh_stats(), "billing": fresh_stats(), "drafting": fresh_stats()}

    messages = [{"role": "system", "content": TRIAGE_PROMPT}, {"role": "user", "content": ticket_text}]
    messages, outcome = await run_stage(messages, [TRANSFER_TO_BILLING_SCHEMA], {}, {"transfer_to_billing"}, stats["triage"])
    print(f"  [handoff] triage -> billing, carrying {outcome['args']}")

    messages[0] = {"role": "system", "content": BILLING_PROMPT}
    billing_schemas = [LOOKUP_ORDER_SCHEMA, TRANSFER_TO_DRAFTING_SCHEMA]
    billing_handlers = {"lookup_order": lookup_order}
    messages, outcome = await run_stage(messages, billing_schemas, billing_handlers, {"transfer_to_drafting"}, stats["billing"])
    print(f"  [handoff] billing -> drafting, carrying {outcome['args']}")

    messages[0] = {"role": "system", "content": DRAFTING_PROMPT}
    messages, outcome = await run_stage(messages, [], {}, set(), stats["drafting"])

    return outcome["text"] or "(no reply)", stats


async def run_style_b_package_only(ticket_text: str) -> tuple[str, dict]:
    """Style B: each agent starts with a fresh messages list holding only
    the package handed to it, validated with Pydantic along the way."""
    stats = {"triage": fresh_stats(), "billing": fresh_stats(), "drafting": fresh_stats()}

    triage_messages = [{"role": "system", "content": TRIAGE_PROMPT}, {"role": "user", "content": ticket_text}]
    _, outcome = await run_stage(triage_messages, [TRANSFER_TO_BILLING_SCHEMA], {}, {"transfer_to_billing"}, stats["triage"])
    billing_package = BillingHandoff.model_validate(outcome["args"])
    print(f"  [handoff] triage -> billing, carrying {billing_package.model_dump()}")

    billing_messages = [
        {"role": "system", "content": BILLING_PROMPT},
        {"role": "user", "content": billing_package.model_dump_json()},
    ]
    billing_schemas = [LOOKUP_ORDER_SCHEMA, TRANSFER_TO_DRAFTING_SCHEMA]
    billing_handlers = {"lookup_order": lookup_order}
    _, outcome = await run_stage(billing_messages, billing_schemas, billing_handlers, {"transfer_to_drafting"}, stats["billing"])
    drafting_package = DraftingHandoff.model_validate(outcome["args"])
    print(f"  [handoff] billing -> drafting, carrying {drafting_package.model_dump()}")

    drafting_messages = [
        {"role": "system", "content": DRAFTING_PROMPT},
        {"role": "user", "content": drafting_package.summary},
    ]
    _, outcome = await run_stage(drafting_messages, [], {}, set(), stats["drafting"])

    return outcome["text"] or "(no reply)", stats


async def run_style_c_filtered_thread(ticket_text: str) -> tuple[str, dict]:
    """Style C: like the shared thread, but tool calls and tool results are
    stripped out of the history before each handoff."""
    stats = {"triage": fresh_stats(), "billing": fresh_stats(), "drafting": fresh_stats()}

    messages = [{"role": "system", "content": TRIAGE_PROMPT}, {"role": "user", "content": ticket_text}]
    messages, outcome = await run_stage(messages, [TRANSFER_TO_BILLING_SCHEMA], {}, {"transfer_to_billing"}, stats["triage"])

    messages = filter_history(messages)
    messages[0] = {"role": "system", "content": BILLING_PROMPT}
    billing_schemas = [LOOKUP_ORDER_SCHEMA, TRANSFER_TO_DRAFTING_SCHEMA]
    billing_handlers = {"lookup_order": lookup_order}
    messages, outcome = await run_stage(messages, billing_schemas, billing_handlers, {"transfer_to_drafting"}, stats["billing"])

    messages = filter_history(messages)
    messages[0] = {"role": "system", "content": DRAFTING_PROMPT}
    messages, outcome = await run_stage(messages, [], {}, set(), stats["drafting"])

    return outcome["text"] or "(no reply)", stats


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
