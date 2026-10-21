# Problem 03 -- a router reads a ticket, decides which specialist should
# handle it, and sends it there -- or to a human, when it isn't sure.

import asyncio
import json
import os
from typing import Literal

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
    named tools -- this is how each agent in this chapter gets only the
    tools its role needs."""
    schemas = [TOOL_SCHEMAS[name] for name in names]
    handlers = {name: TOOL_FUNCTIONS[name] for name in names}
    return schemas, handlers


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6):
    """The chapter 2 tool-calling loop."""
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


# --- routing ---

CONFIDENCE_FLOOR = 0.6

SPECIALISTS = {
    "billing": {
        "tools": ["lookup_order", "list_charges"],
        "prompt": "You are a billing specialist. Investigate the ticket using your tools and answer in 1-2 sentences.",
    },
    "account": {
        "tools": ["get_account_status", "unlock_account"],
        "prompt": "You are an account specialist. Investigate the ticket using your tools and answer in 1-2 sentences.",
    },
    "technical": {
        "tools": ["check_service_status", "search_help_articles"],
        "prompt": "You are a technical specialist. Investigate the ticket using your tools and answer in 1-2 sentences.",
    },
}


class Route(BaseModel):
    department: Literal["billing", "account", "technical", "unknown"]
    confidence: float
    reason: str


async def route_ticket(ticket_text: str) -> Route:
    # your turn: structured-output call (response_format=Route), with a
    # system prompt telling the model to pick one department or 'unknown'
    raise NotImplementedError


async def run_specialist(department: str, ticket_text: str) -> str:
    # your turn: select_tools(SPECIALISTS[department]["tools"]), run the loop
    raise NotImplementedError


async def route_and_handle(ticket_text: str) -> str:
    # your turn: route, print the route and confidence, send to the human
    # fallback if department == "unknown" or confidence < CONFIDENCE_FLOOR,
    # otherwise run that specialist
    raise NotImplementedError


async def main() -> None:
    tickets = [
        "I was charged twice for ORD-4471.",
        "I'm locked out of my account C-200.",
        "The login page has been down all morning.",
        "What's your office address?",
        "I was charged twice AND now I can't log in.",
    ]

    for ticket_text in tickets:
        print(f'\n"{ticket_text}"')
        answer = await route_and_handle(ticket_text)
        print(f"  answer: {answer}")


if __name__ == "__main__":
    asyncio.run(main())
