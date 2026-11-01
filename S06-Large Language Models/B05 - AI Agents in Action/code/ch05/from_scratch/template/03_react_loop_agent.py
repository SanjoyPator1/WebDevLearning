# ============================================================
# LISTING: 03_react_loop_agent.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: A genuine ReAct (Reason-Act-Observe) loop booking a multi-leg
#           conference trip under a $1,500 total budget. The two tools are
#           backed by a small, STATEFUL, module-level "world" dict: the
#           FIRST search for leg two deliberately comes back sold out, and
#           only a follow-up search with adjusted parameters (a connecting
#           itinerary) returns a real, bookable result. This forces the
#           loop to genuinely observe a bad result and change its next
#           action -- the entire point of ReAct, as opposed to
#           chain-of-thought with an incidental tool call bolted on.
# REF: Chapter 5 notes, section 4 (ReAct: The Reason-Act-Observe Loop)
# COMPARE: the SDK version of this file at ../../openai_sdk/solved/03_react_loop_agent.py
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# This is the file where the SDK hides the most. Runner.run(agent, goal,
# max_turns=15) was doing three things invisibly: building and growing the
# `messages` list (system prompt, user goal, every assistant tool-call
# turn, every tool result) call after call; dispatching each tool call the
# model asked for by name and appending its result back onto that list;
# and deciding when to stop -- either because the model finally answered
# with no more tool calls, or because the step budget ran out. Here all
# three are one function you can read top to bottom: run_tool_loop()
# below. The tools themselves are plain Python functions with no
# @function_tool decorator turning a docstring into a schema behind the
# scenes -- the OpenAI tool-definition dicts (search_flights_tool_schema,
# book_flight_tool_schema) are written out by hand instead, so you can see
# exactly what JSON schema the model is actually being told about, and the
# tool_handlers dict below is the entire "dispatch table" the loop uses to
# turn a tool call's name string into the Python function that runs it.

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

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

# Same order of magnitude as the notes' own ReAct dry run ($1,500 across
# three legs, first leg landing around $620).
TOTAL_TRIP_BUDGET = 1500.0

# --- Stateful "world" for this demo -- a module-level dict that changes
# across calls WITHIN one run. This is what makes the sold-out result on
# leg two a genuine surprise rather than something scripted into the
# prompt: the loop has no way to know it in advance, it only finds out by
# calling the tool.
_world = {
    "booked_legs": {},  # flight_id -> price, filled in as book_flight() runs
}

# Fixed flight inventory keyed by (route, is_connection) so the same route
# can return a different result depending on what the tool call asks for.
_flight_inventory = {
    ("city-a-to-city-b", False): {"flight_id": "AB-101", "price": 620.0, "seats_left": 1},
    ("city-b-to-city-c", False): {"flight_id": "BC-DIRECT-1", "price": 0.0, "seats_left": 0},  # sold out
    ("city-b-to-city-c", True): {"flight_id": "BC-CONN-7", "price": 410.0, "seats_left": 3},
    ("city-c-to-city-d", False): {"flight_id": "CD-909", "price": 260.0, "seats_left": 4},
}

# --- Raw OpenAI tool-definition schemas, written by hand -- this is
# exactly what @function_tool built from search_flights' and
# book_flight's signatures and docstrings in the SDK version.
search_flights_tool_schema = {
    "type": "function",
    "function": {
        "name": "search_flights",
        "description": (
            "Search for a flight on one route. Some routes are sold out on "
            "their first (direct) search and only return a bookable result "
            "once searched again with connecting=True -- a real observation "
            "the caller has to act on, not something it can predict in "
            "advance."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "route": {"type": "string", "description": "route key, e.g. 'city-a-to-city-b'."},
                "max_price": {"type": "number", "description": "the price ceiling for this search."},
                "connecting": {
                    "type": "boolean",
                    "description": "whether to search connecting itineraries instead of direct flights.",
                },
            },
            "required": ["route", "max_price"],
        },
    },
}

book_flight_tool_schema = {
    "type": "function",
    "function": {
        "name": "book_flight",
        "description": (
            "Book a specific flight by its flight_id at the given price, "
            "updating the running total spent so far."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "flight_id": {"type": "string"},
                "price": {"type": "number"},
            },
            "required": ["flight_id", "price"],
        },
    },
}

tools_schema = [search_flights_tool_schema, book_flight_tool_schema]


def search_flights(route: str, max_price: float, connecting: bool = False) -> dict:
    """Plain Python tool handler -- no decorator. Same behavior as the SDK
    version's search_flights: some routes are sold out on their first
    (direct) search and only return a bookable result once searched again
    with connecting=True."""
    key = (route, connecting)
    result = _flight_inventory.get(key)
    if result is None or result["seats_left"] == 0:
        print(
            f"    [tool] search_flights(route={route!r}, max_price={max_price}, "
            f"connecting={connecting}) -> {{'status': 'sold_out'}}"
        )
        return {"status": "sold_out"}

    if result["price"] > max_price:
        print(
            f"    [tool] search_flights(route={route!r}, max_price={max_price}, "
            f"connecting={connecting}) -> over price ceiling: ${result['price']}"
        )
        return {"status": "over_budget", "price": result["price"]}

    response = {
        "status": "available",
        "flight_id": result["flight_id"],
        "price": result["price"],
        "seats_left": result["seats_left"],
    }
    print(
        f"    [tool] search_flights(route={route!r}, max_price={max_price}, "
        f"connecting={connecting}) -> {response}"
    )
    return response


def book_flight(flight_id: str, price: float) -> dict:
    """Book a specific flight by its flight_id at the given price, updating
    the running total spent so far."""
    _world["booked_legs"][flight_id] = price
    total_spent = sum(_world["booked_legs"].values())
    response = {
        "status": "confirmed",
        "flight_id": flight_id,
        "price": price,
        "total_spent_so_far": total_spent,
        "remaining_budget": TOTAL_TRIP_BUDGET - total_spent,
    }
    print(f"    [tool] book_flight({flight_id!r}, {price}) -> {response}")
    return response


# --- The dispatch table run_tool_loop uses to turn a tool call's name
# string into the function that actually runs it. This dict IS the thing
# @function_tool + Agent(tools=[...]) built and wired together for us
# behind the scenes in the SDK version.
tool_handlers = {
    "search_flights": search_flights,
    "book_flight": book_flight,
}


async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=10):
    """The reason-act-observe loop itself, made visible: call the model,
    dispatch whatever tool calls it asked for, append the results, and
    repeat until the model stops calling tools or the step budget runs
    out. This is exactly what Runner.run(..., max_turns=...) was doing for
    us invisibly in the SDK version of this file."""
    for step in range(max_steps):
        print(f"\n--- loop step {step + 1} ---")
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=tools_schema,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            print("  model returned no tool calls -- loop is done")
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, "no_tool_calls", step + 1

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            print(f"  tool call: {tool_call.function.name}({arguments})")
            handler = tool_handlers[tool_call.function.name]
            result = handler(**arguments)
            if hasattr(result, "__await__"):
                result = await result
            print(f"  tool result: {result}")
            messages.append({
                "role": "tool", "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })

    print(f"  step budget ({max_steps}) exhausted")
    return messages, "budget", max_steps

# A production harness built on this same shape would typically add
# tool-result size capping (so one huge tool response can't blow the
# context window) and richer, structured termination tracking -- neither
# is needed for this teaching example, so neither is built here.


# --- Your turn ---
# Write an async main() that:
#   1. Builds a system_prompt string that tells the model, explicitly:
#        a. REASON step by step about what to do next before each action.
#        b. ACT by calling exactly ONE tool at a time -- search_flights or
#           book_flight -- and never assume a result without calling the
#           tool.
#        c. OBSERVE the tool's actual returned result before deciding the
#           next step. If a search_flights call comes back
#           {"status": "sold_out"}, it must NOT give up on that leg -- it
#           should try again with connecting=True before moving on. If a
#           search comes back {"status": "over_budget", ...}, it should
#           try a higher max_price, as long as the running total across
#           all booked legs would stay under TOTAL_TRIP_BUDGET.
#        d. Book each leg with book_flight only after a search_flights
#           call has returned status "available" for it, and track the
#           running total against TOTAL_TRIP_BUDGET.
#        e. Once all three legs (city-a-to-city-b, city-b-to-city-c,
#           city-c-to-city-d) are booked, report the final itinerary and
#           total spent.
#   2. Builds the starting `messages` list: a system message with that
#      prompt, then a user message describing the goal (book all three
#      legs under the $1,500 TOTAL_TRIP_BUDGET).
#   3. Calls:
#        messages, termination_reason, steps_taken = await run_tool_loop(
#            messages, tools_schema, tool_handlers, max_steps=15
#        )
#      -- max_steps needs real headroom here: a genuine multi-step loop
#      over three legs, including one sold-out retry, takes several
#      turns, not one.
#   4. Prints the model's final text summary (messages[-1]["content"], if
#      termination_reason == "no_tool_calls" -- handle the "budget" case
#      too, since the loop can in principle exhaust its step budget before
#      the model gives a final answer).
#   5. Prints the GROUND TRUTH independent of the model's text: iterate
#      _world["booked_legs"], print each booked flight_id and price, the
#      total spent, and whether it stayed within TOTAL_TRIP_BUDGET.

if __name__ == "__main__":
    asyncio.run(main())
