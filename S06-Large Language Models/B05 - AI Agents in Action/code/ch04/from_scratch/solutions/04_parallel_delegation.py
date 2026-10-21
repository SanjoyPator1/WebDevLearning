# Problem 04 -- three independent checks, run one after another and then
# at the same time, with the wall-clock time measured both ways. Also:
# one check failing should not sink the other two.

import asyncio
import json
import os
import time

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

# --- shared support desk data and tools (the slow three) (given) ---

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


async def list_charges(customer_id: str) -> dict:
    """List recent charges for a customer. Slow: simulates a real billing lookup."""
    await asyncio.sleep(1.5)
    if customer_id not in CUSTOMERS:
        raise ValueError(f"no such customer: {customer_id}")
    charges = [
        f"{order_id}: ${o['amount']:.2f} x{o['times_charged']}"
        for order_id, o in ORDERS.items()
        if o["customer_id"] == customer_id
    ]
    return {"customer_id": customer_id, "charges": charges}


async def get_account_status(customer_id: str) -> dict:
    """Check whether a customer's account is active or locked. Slow: simulates a real lookup."""
    await asyncio.sleep(1.5)
    if customer_id not in CUSTOMERS:
        raise ValueError(f"no such customer: {customer_id}")
    return {"customer_id": customer_id, "status": CUSTOMERS[customer_id]["status"]}


async def check_service_status(service_name: str) -> dict:
    """Check whether a service (login, payments, email) is healthy. Slow: simulates a real check."""
    await asyncio.sleep(1.5)
    if service_name not in SERVICES:
        raise ValueError(f"no such service: {service_name}")
    service = SERVICES[service_name]
    return {"service_name": service_name, "status": service["status"], "detail": service["detail"]}


TOOL_FUNCTIONS = {
    "list_charges": list_charges,
    "get_account_status": get_account_status,
    "check_service_status": check_service_status,
}

TOOL_SCHEMAS = {
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
    "check_service_status": {
        "type": "function",
        "function": {
            "name": "check_service_status",
            "description": check_service_status.__doc__,
            "parameters": {"type": "object", "properties": {"service_name": {"type": "string"}}, "required": ["service_name"]},
        },
    },
}


def select_tools(names: list[str]) -> tuple[list[dict], dict]:
    """Pick out the OpenAI tool schemas and handler functions for just the
    named tools."""
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
                result = await handler(**arguments)
                result_text = json.dumps(result, default=str)
            except ValueError as error:
                result_text = f"ERROR: {error}"
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
            )

    return messages, None


# --- the three checks ---

async def run_charges_check(customer_id: str) -> str:
    schemas, handlers = select_tools(["list_charges"])
    messages = [
        {"role": "system", "content": "Check this customer's recent charges and summarize in one sentence."},
        {"role": "user", "content": customer_id},
    ]
    _, answer = await run_tool_loop(messages, schemas, handlers)
    return answer or "(no answer)"


async def run_account_check(customer_id: str) -> str:
    # your turn: raise RuntimeError directly for customer_id == "C-999", to
    # give Problem 04's failure-isolation part a real exception to isolate --
    # see the comment on this in the problem statement's theory section
    schemas, handlers = select_tools(["get_account_status"])
    messages = [
        {"role": "system", "content": "Check this customer's account status and summarize in one sentence."},
        {"role": "user", "content": customer_id},
    ]
    _, answer = await run_tool_loop(messages, schemas, handlers)
    return answer or "(no answer)"


async def run_outage_check(service_name: str) -> str:
    schemas, handlers = select_tools(["check_service_status"])
    messages = [
        {"role": "system", "content": "Check this service's status and summarize in one sentence."},
        {"role": "user", "content": service_name},
    ]
    _, answer = await run_tool_loop(messages, schemas, handlers)
    return answer or "(no answer)"


async def run_sequential(customer_id: str, service_name: str) -> tuple[list[str], float]:
    # your turn: await each check in turn, timed with time.perf_counter()
    start = time.perf_counter()

    charges = await run_charges_check(customer_id)
    account = await run_account_check(customer_id)
    outage = await run_outage_check(customer_id)

    elapsed = time.perf_counter() - start
    return [charges, account, outage], elapsed


async def run_parallel(customer_id: str, service_name: str) -> tuple[list[str], float]:
    # your turn: the same three checks via asyncio.gather(...), timed the same way
    start = time.perf_counter()
    
    results = await asyncio.gather(
        run_charges_check(customer_id),
        run_account_check(customer_id),
        run_outage_check(customer_id)
    )

    elapsed = time.perf_counter() - start

    return list(results), elapsed


async def run_parallel_with_failure(bad_customer_id: str, service_name: str) -> list[str | Exception]:
    # your turn: asyncio.gather(..., return_exceptions=True) with a customer
    # id that makes run_account_check raise
    results = await asyncio.gather(
        run_charges_check(bad_customer_id),
        run_account_check(bad_customer_id),
        run_outage_check(bad_customer_id),
        return_exceptions=True
    )

    return list(results)


async def run_synthesis(findings: list[str]) -> str:
    # your turn: a plain completion call (no tools) combining findings into one paragraph
    messages = [
        {"role" : "system", "content" : "Combine these findings into one short paragraph for the customer"},
        {"role" : "user", "content" : "\n".join(findings)}
    ]

    _, answer = await run_tool_loop(messages, [], {})

    return answer or "(no synthesis)"


async def main() -> None:
    customer_id = "C-100"
    service_name = "login"

    print("SEQUENTIAL: each lookup waits for the previous one to finish")
    findings, elapsed = await run_sequential(customer_id, service_name)
    for finding in findings:
        print(f"  - {finding}")
    print(f"\nsequential wall-clock time: {elapsed:.2f}s")

    print("\nPARALLEL: all three lookups run at the same time")
    findings, elapsed_parallel = await run_parallel(customer_id, service_name)
    for finding in findings:
        print(f"  - {finding}")
    print(f"\nparallel wall-clock time: {elapsed_parallel:.2f}s")
    print(f"time saved by running in parallel: {elapsed - elapsed_parallel:.2f}s")

    print("\nPARALLEL WITH ONE FAILURE")
    results = await run_parallel_with_failure("C-999", service_name)
    labels = ["charges", "account", "outage"]
    good_findings = []
    for label, result in zip(labels, results):
        if isinstance(result, Exception):
            print(f"  {label:8s}: FAILED ({result})")
        else:
            print(f"  {label:8s}: {result}")
            good_findings.append(result)
    failed_labels = [label for label, result in zip(labels, results) if isinstance(result, Exception)]
    if failed_labels:
        good_findings.append(f"Could not check: {', '.join(failed_labels)}")
    synthesis = await run_synthesis(good_findings)
    print(f"  synthesis: {synthesis}")


if __name__ == "__main__":
    asyncio.run(main())

# TERMINAL OUTPUT

# python 04_parallel_delegation.py 
# SEQUENTIAL: each lookup waits for the previous one to finish
#   - Customer C-100 has a recent charge for order ORD-4471 consisting of two items priced at $150.00 each, totaling $300.00.
#   - The account status for customer C-100 is currently active.
#   - The service "C-100" does not exist in the system.

# sequential wall-clock time: 32.05s

# PARALLEL: all three lookups run at the same time
#   - Customer C-100 has a recent charge for order ORD-4471 consisting of two items priced at $150.00 each, totaling $300.00.
#   - Customer C-100's account is currently active.
#   - No service named "C-100" exists in the system.

# parallel wall-clock time: 19.58s
# time saved by running in parallel: 12.46s

# PARALLEL WITH ONE FAILURE
#   charges : Customer C-999 could not be found in the system, so no recent charges are available.
#   account : The account C-999 could not be found in the system.
#   outage  : The service "C-999" does not exist in the system.
#   synthesis: We were unable to locate account or service C-999 in our system, and as a result, no recent charges are available for this identifier. Please verify the account or service number and try again.
