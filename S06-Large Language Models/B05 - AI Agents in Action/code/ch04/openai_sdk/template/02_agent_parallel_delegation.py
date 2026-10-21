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

# --- Your turn ---
# Write two async functions and a main():
#
#   1. run_sequential(customer_id, service_name) -> (findings, elapsed):
#      call Runner.run() on billing_check_agent, then account_check_agent,
#      then outage_check_agent, one after another with `await`. Time the
#      whole thing with time.monotonic() before and after, and return the
#      list of three `.final_output` strings plus the elapsed seconds.
#
#   2. run_parallel(customer_id, service_name) -> (findings, elapsed):
#      do the SAME three calls, but wrap them in asyncio.gather(...) so
#      they run at the same time instead of one after another. Time it
#      the same way.
#
#   3. main(): run both versions on customer_id="CUST-88" and
#      service_name="mobile-app-login", print each one's findings and
#      elapsed time, print how much time the parallel version saved, then
#      run synthesis_agent on the three parallel findings (joined with
#      newlines) and print its final_output.

if __name__ == "__main__":
    asyncio.run(main())
