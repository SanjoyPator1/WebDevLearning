# ============================================================
# LISTING: 02_agent_parallel_delegation.py  (reference implementation)
# BUILDING: Three independent specialist agents (billing, account, outage
#           status) run SEQUENTIALLY, then the same three run in PARALLEL
#           via asyncio.gather, with real wall-clock timing printed so the
#           speed difference is not just a claim -- you can watch it happen.
#           A Synthesis Agent then combines the three findings.
# REF: Chapter 4 notes, sections 2 (communication -- narrow inputs per
#      agent), 5 (parallel delegation, and how it differs from a plain
#      sequential pipeline)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# Each fake lookup tool sleeps for a bit to simulate a slow network call
# (a real billing API, a real outage-status service). None of the three
# lookups depends on either of the other two, which is exactly the
# condition that makes parallel delegation the right pattern here.

import asyncio
import os
import time

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
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

# How long each fake lookup "network call" takes, in seconds.
SIMULATED_LATENCY = 1.5

# --- Fake data sources for this demo ---
_billing_history = {"CUST-88": ["Charged $45.00 on 2026-08-01", "Charged $45.00 on 2026-09-01"]}
_account_status = {"CUST-88": "active, in good standing"}
_known_outages = {"mobile-app-login": "Login service had a 20-minute outage yesterday at 14:00 UTC"}


@function_tool
async def lookup_billing_history(customer_id: str) -> dict:
    """Fetch recent charges for a customer. Simulates a slow network call."""
    print(f"    [tool] lookup_billing_history({customer_id!r}) started...")
    await asyncio.sleep(SIMULATED_LATENCY)
    result = {"charges": _billing_history.get(customer_id, [])}
    print(f"    [tool] lookup_billing_history({customer_id!r}) done -> {result}")
    return result


@function_tool
async def check_account_status(customer_id: str) -> dict:
    """Check whether a customer's account is active. Simulates a slow network call."""
    print(f"    [tool] check_account_status({customer_id!r}) started...")
    await asyncio.sleep(SIMULATED_LATENCY)
    result = {"status": _account_status.get(customer_id, "unknown")}
    print(f"    [tool] check_account_status({customer_id!r}) done -> {result}")
    return result


@function_tool
async def check_service_outages(service_name: str) -> dict:
    """Check for known outages affecting a service. Simulates a slow network call."""
    print(f"    [tool] check_service_outages({service_name!r}) started...")
    await asyncio.sleep(SIMULATED_LATENCY)
    result = {"outage_note": _known_outages.get(service_name, "no known outages")}
    print(f"    [tool] check_service_outages({service_name!r}) done -> {result}")
    return result


billing_check_agent = Agent(
    name="Billing Check Agent",
    instructions="Call lookup_billing_history with the given customer ID and report what you found in one sentence.",
    model=model,
    tools=[lookup_billing_history],
)

account_check_agent = Agent(
    name="Account Check Agent",
    instructions="Call check_account_status with the given customer ID and report what you found in one sentence.",
    model=model,
    tools=[check_account_status],
)

outage_check_agent = Agent(
    name="Outage Check Agent",
    instructions="Call check_service_outages with the given service name and report what you found in one sentence.",
    model=model,
    tools=[check_service_outages],
)

synthesis_agent = Agent(
    name="Synthesis Agent",
    instructions="Combine the three findings you are given into one short paragraph for a support agent to read.",
    model=model,
)


async def run_sequential(customer_id: str, service_name: str) -> tuple[list[str], float]:
    """Run the three lookups one after another -- each waits for the previous one."""
    start = time.monotonic()
    billing_result = await Runner.run(billing_check_agent, customer_id)
    account_result = await Runner.run(account_check_agent, customer_id)
    outage_result = await Runner.run(outage_check_agent, service_name)
    elapsed = time.monotonic() - start
    findings = [billing_result.final_output, account_result.final_output, outage_result.final_output]
    return findings, elapsed


async def run_parallel(customer_id: str, service_name: str) -> tuple[list[str], float]:
    """Run the same three lookups at the same time -- none depends on the others."""
    start = time.monotonic()
    billing_result, account_result, outage_result = await asyncio.gather(
        Runner.run(billing_check_agent, customer_id),
        Runner.run(account_check_agent, customer_id),
        Runner.run(outage_check_agent, service_name),
    )
    elapsed = time.monotonic() - start
    findings = [billing_result.final_output, account_result.final_output, outage_result.final_output]
    return findings, elapsed


async def main():
    customer_id = "CUST-88"
    service_name = "mobile-app-login"

    print("=" * 60)
    print("SEQUENTIAL: each lookup waits for the previous one to finish")
    print("=" * 60)
    seq_findings, seq_time = await run_sequential(customer_id, service_name)
    for finding in seq_findings:
        print(f"  - {finding}")
    print(f"\nsequential wall-clock time: {seq_time:.2f}s")

    print("\n" + "=" * 60)
    print("PARALLEL: all three lookups run at the same time")
    print("=" * 60)
    par_findings, par_time = await run_parallel(customer_id, service_name)
    for finding in par_findings:
        print(f"  - {finding}")
    print(f"\nparallel wall-clock time: {par_time:.2f}s")

    print(f"\ntime saved by running in parallel: {seq_time - par_time:.2f}s")

    print("\n" + "=" * 60)
    print("Synthesis Agent combines all three findings")
    print("=" * 60)
    combined_input = "\n".join(par_findings)
    synthesis_result = await Runner.run(synthesis_agent, combined_input)
    print(synthesis_result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
