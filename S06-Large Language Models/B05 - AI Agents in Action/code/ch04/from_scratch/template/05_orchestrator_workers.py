# Problem 05 -- an orchestrator agent whose tools ARE other agents. It
# reads the ticket, writes a separate brief for each specialist it needs,
# runs them (in parallel when it asks for several at once), and writes the
# final reply itself.

import asyncio
import json
import os
from collections import defaultdict

from dotenv import load_dotenv
from openai import AsyncOpenAI

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

CUSTOMERS = {
    "C-100": {"status": "active"},
    "C-200": {"status": "locked"},
    "C-300": {"status": "active"},
}

SERVICES = {
    "login": {"status": "outage", "detail": "login service has been down since 09:10 UTC"},
    "payments": {"status": "ok", "detail": "payments service is healthy"},
    "email": {"status": "degraded", "detail": "email service is sending with delays"},
}

HELP_ARTICLES = [
    {"title": "Refund policy", "body": "Refunds for duplicate or incorrect charges are issued within 5 business days."},
    {"title": "Resetting your password", "body": "Use the 'forgot password' link on the login page to reset your password."},
    {"title": "Outage updates", "body": "Check our status page for live updates on login, payments, and email outages."},
    {"title": "Locked accounts", "body": "Accounts lock after 5 failed login attempts and can be unlocked by support."},
]


def lookup_order(order_id: str) -> dict:
    """Look up an order: its customer, amount, and how many times it was charged."""
    if order_id not in ORDERS:
        raise ValueError(f"no such order: {order_id}")
    return {"order_id": order_id, **ORDERS[order_id]}


def list_charges(customer_id: str) -> dict:
    """List recent charges for a customer."""
    if customer_id not in CUSTOMERS:
        raise ValueError(f"no such customer: {customer_id}")
    charges = [
        f"{order_id}: ${o['amount']:.2f} x{o['times_charged']}"
        for order_id, o in ORDERS.items()
        if o["customer_id"] == customer_id
    ]
    return {"customer_id": customer_id, "charges": charges}


def get_account_status(customer_id: str) -> dict:
    """Check whether a customer's account is active or locked."""
    if customer_id not in CUSTOMERS:
        raise ValueError(f"no such customer: {customer_id}")
    return {"customer_id": customer_id, "status": CUSTOMERS[customer_id]["status"]}


def unlock_account(customer_id: str) -> dict:
    """Unlock a customer's account. Only works if the account is currently locked."""
    if customer_id not in CUSTOMERS:
        raise ValueError(f"no such customer: {customer_id}")
    if CUSTOMERS[customer_id]["status"] != "locked":
        raise ValueError(f"account {customer_id} is not locked")
    CUSTOMERS[customer_id]["status"] = "active"
    return {"customer_id": customer_id, "status": "active"}


def check_service_status(service_name: str) -> dict:
    """Check whether a service (login, payments, email) is healthy."""
    if service_name not in SERVICES:
        raise ValueError(f"no such service: {service_name}")
    service = SERVICES[service_name]
    return {"service_name": service_name, "status": service["status"], "detail": service["detail"]}


def search_help_articles(query: str) -> list[dict]:
    """Search help articles by keyword, matching against titles and bodies."""
    query_lower = query.lower()
    return [
        article
        for article in HELP_ARTICLES
        if query_lower in article["title"].lower() or query_lower in article["body"].lower()
    ]


TOOL_FUNCTIONS = {
    "lookup_order": lookup_order,
    "list_charges": list_charges,
    "get_account_status": get_account_status,
    "unlock_account": unlock_account,
    "check_service_status": check_service_status,
    "search_help_articles": search_help_articles,
}

TOOL_SCHEMAS = {
    "lookup_order": {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": lookup_order.__doc__,
            "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
        },
    },
    "list_charges": {
        "type": "function",
        "function": {
            "name": "list_charges",
            "description": list_charges.__doc__,
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
        },
    },
    "get_account_status": {
        "type": "function",
        "function": {
            "name": "get_account_status",
            "description": get_account_status.__doc__,
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
        },
    },
    "unlock_account": {
        "type": "function",
        "function": {
            "name": "unlock_account",
            "description": unlock_account.__doc__,
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
        },
    },
    "check_service_status": {
        "type": "function",
        "function": {
            "name": "check_service_status",
            "description": check_service_status.__doc__,
            "parameters": {"type": "object", "properties": {"service_name": {"type": "string"}}, "required": ["service_name"]},
        },
    },
    "search_help_articles": {
        "type": "function",
        "function": {
            "name": "search_help_articles",
            "description": search_help_articles.__doc__,
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
}


def select_tools(names: list[str]) -> tuple[list[dict], dict]:
    """Pick out the OpenAI tool schemas and handler functions for just the
    named tools."""
    schemas = [TOOL_SCHEMAS[name] for name in names]
    handlers = {name: TOOL_FUNCTIONS[name] for name in names}
    return schemas, handlers


# prompt tokens spent, per agent label -- safe to share across asyncio.gather
# because every += runs on the one event-loop thread
PROMPT_TOKENS: dict[str, int] = defaultdict(int)


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6, label="agent"):
    """The chapter 2 tool-calling loop, adding each call's prompt tokens to PROMPT_TOKENS[label]."""
    for _ in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema or None
        )
        PROMPT_TOKENS[label] += response.usage.prompt_tokens
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


# --- the three specialists, each isolated to its own brief ---

SPECIALISTS = {
    "billing": {
        "tools": ["lookup_order", "list_charges"],
        "prompt": "You are a billing specialist. Investigate using your tools and answer in 1-2 sentences.",
    },
    "account": {
        "tools": ["get_account_status", "unlock_account"],
        "prompt": "You are an account specialist. Investigate using your tools and answer in 1-2 sentences.",
    },
    "technical": {
        "tools": ["check_service_status", "search_help_articles"],
        "prompt": "You are a technical specialist. Investigate using your tools and answer in 1-2 sentences.",
    },
}


async def run_specialist(name: str, brief: str) -> str:
    # your turn: select_tools(SPECIALISTS[name]["tools"]), fresh messages
    # seeded ONLY with the brief, run the loop with label=name so its
    # tokens are counted under the specialist's name
    raise NotImplementedError


# --- the orchestrator's own tools: each one IS a specialist call ---

ORCHESTRATOR_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "ask_billing_specialist",
            "description": (
                "Ask the billing specialist to investigate something. The specialist "
                "sees ONLY the brief you write here, nothing else, so include every "
                "detail it needs (order ids, customer ids, what to check)."
            ),
            "parameters": {"type": "object", "properties": {"brief": {"type": "string"}}, "required": ["brief"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_account_specialist",
            "description": (
                "Ask the account specialist to investigate something. The specialist "
                "sees ONLY the brief you write here, nothing else, so include every "
                "detail it needs (customer ids, what to check)."
            ),
            "parameters": {"type": "object", "properties": {"brief": {"type": "string"}}, "required": ["brief"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_technical_specialist",
            "description": (
                "Ask the technical specialist to investigate something, including "
                "service outages and help articles. The specialist sees ONLY the "
                "brief you write here, nothing else."
            ),
            "parameters": {"type": "object", "properties": {"brief": {"type": "string"}}, "required": ["brief"]},
        },
    },
]

SPECIALIST_BY_TOOL_NAME = {
    "ask_billing_specialist": "billing",
    "ask_account_specialist": "account",
    "ask_technical_specialist": "technical",
}

ORCHESTRATOR_PROMPT = """
You are a support desk orchestrator. You do not investigate anything
yourself. Instead, decide which specialists are needed (billing, account,
technical) and ask each one with a clear, self-contained brief -- the
specialist will see nothing except what you write in that brief. You may
ask several specialists at once if the ticket needs it. Once you have
their answers, write the final reply to the customer yourself.
"""


async def run_orchestrator(ticket_text: str) -> str:
    # your turn: build the messages list, loop calling the model with
    # tools=ORCHESTRATOR_SCHEMAS; when message.tool_calls is empty, that is
    # the final reply; otherwise, for EACH tool call in this turn, print the
    # brief, then run ALL of them together with asyncio.gather (this is the
    # "several tool calls in one turn -> run them together" rule), append
    # each specialist's answer as a tool message keyed by its tool_call_id,
    # and loop again. After every model call, add response.usage.prompt_tokens
    # to PROMPT_TOKENS["orchestrator"]
    raise NotImplementedError


async def main() -> None:
    ticket = (
        "Hi, I'm customer C-100. I was charged twice for ORD-4471, my login "
        "keeps failing, and I'd like to know your refund policy."
    )
    print(f"TICKET: {ticket}\n")
    reply = await run_orchestrator(ticket)
    print(f"\nFINAL REPLY:\n{reply}")

    # your turn: save a copy of PROMPT_TOKENS, clear it, run the billing
    # specialist alone on "I was charged twice for ORD-4471." as a baseline,
    # then print the per-agent breakdown, the total, and the baseline


if __name__ == "__main__":
    asyncio.run(main())
