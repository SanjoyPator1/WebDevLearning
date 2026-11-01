# ============================================================
# LISTING: 03_react_loop_agent.py  (reference implementation)
# BUILDING: A genuine ReAct (Reason-Act-Observe) loop booking a multi-leg
#           conference trip under a $1,500 total budget. The two tools are
#           backed by a small, STATEFUL, module-level "world" dict: the
#           FIRST search for leg two deliberately comes back sold out, and
#           only a follow-up search with adjusted parameters (a connecting
#           itinerary) returns a real, bookable result. This forces the
#           agent to genuinely observe a bad result and change its next
#           action -- the entire point of ReAct, as opposed to
#           chain-of-thought with an incidental tool call bolted on.
# REF: Chapter 5 notes, section 4 (ReAct: The Reason-Act-Observe Loop)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# Compare this file against 01_decomposition_and_cot.py: chain-of-thought
# makes the model's own arithmetic visible, but nothing forces it to
# revise course against a fact from the outside world. ReAct's loop is
# closed specifically because each new reasoning step is conditioned on
# the observation the previous tool call actually returned -- the
# sold-out result on leg two is not something the agent could have known
# at turn one, it only becomes a fact once search_flights() is called.
# The tools themselves print on every call, so the loop's behavior is
# visible in the console regardless of what the model's final text says.

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

# Same order of magnitude as the notes' own ReAct dry run ($1,500 across
# three legs, first leg landing around $620).
TOTAL_TRIP_BUDGET = 1500.0

# --- Stateful "world" for this demo -- a module-level dict that changes
# across calls WITHIN one run. This is what makes the sold-out result on
# leg two a genuine surprise rather than something scripted into the
# prompt: the agent has no way to know it in advance, it only finds out by
# calling the tool.
_world = {
    "booked_legs": {},  # flight_id -> price, filled in as book_flight() runs
}

# Fixed flight inventory keyed by (route, is_connection) so the same route
# can return a different result depending on what the agent asks for.
_flight_inventory = {
    ("city-a-to-city-b", False): {"flight_id": "AB-101", "price": 620.0, "seats_left": 1},
    ("city-b-to-city-c", False): {"flight_id": "BC-DIRECT-1", "price": 0.0, "seats_left": 0},  # sold out
    ("city-b-to-city-c", True): {"flight_id": "BC-CONN-7", "price": 410.0, "seats_left": 3},
    ("city-c-to-city-d", False): {"flight_id": "CD-909", "price": 260.0, "seats_left": 4},
}


@function_tool
def search_flights(route: str, max_price: float, connecting: bool = False) -> dict:
    """Search for a flight on one route. Some routes are sold out on their
    first (direct) search and only return a bookable result once searched
    again with connecting=True -- a real observation the agent has to act
    on, not something it can predict in advance.

    Args:
        route: route key, e.g. "city-a-to-city-b".
        max_price: the agent's price ceiling for this search.
        connecting: whether to search connecting itineraries instead of
            direct flights.
    """
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


@function_tool
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


trip_booking_agent = Agent(
    name="Trip Booking Agent",
    instructions=f"""
    You are booking a three-leg conference trip: city-a-to-city-b,
    city-b-to-city-c, and city-c-to-city-d, in that order, under a total
    trip budget of ${TOTAL_TRIP_BUDGET:.0f} across all three legs combined.

    Follow the Reason-Act-Observe loop on every single step:
      1. REASON: before taking any action, briefly state what you are
         trying to do next and why.
      2. ACT: call exactly ONE tool to take that action -- either
         search_flights or book_flight. Never assume a result; always call
         the tool to find out.
      3. OBSERVE: read the tool's actual returned result before deciding
         your next step. Do not assume what a search will return before
         you have called it.

    If a search_flights call returns {{"status": "sold_out"}}, you must NOT
    give up on that leg or assume the whole route is impossible. Instead,
    genuinely revise your plan: try searching again with connecting=True
    to look for a connecting itinerary before moving on.

    If a search returns {{"status": "over_budget", ...}}, try a higher
    max_price on your next search for that leg, as long as the running
    total across all booked legs would still stay under the total trip
    budget.

    Book each leg with book_flight only after a search_flights call has
    returned status "available" for it. Keep track of the running total
    spent (shown in each book_flight response) and make sure it never
    exceeds the total trip budget.

    Continue this loop until all three legs are booked. Then report the
    final itinerary (each leg's flight_id and price) and the total spent.
    """,
    model=model,
    tools=[search_flights, book_flight],
)


async def main():
    print("=" * 60)
    print("ReAct loop: booking a 3-leg conference trip under budget")
    print("=" * 60)
    goal = (
        "Book my conference trip: fly city-a-to-city-b, then "
        "city-b-to-city-c, then city-c-to-city-d, keeping the total spent "
        f"under ${TOTAL_TRIP_BUDGET:.0f}."
    )
    print(f"\nGOAL: {goal}")
    print("\nRunning the agent (watch the tool calls below to see the loop react to the sold-out leg):\n")

    # max_turns needs real headroom here -- a genuine multi-step loop over
    # three legs, including one sold-out retry, takes several turns, not one.
    result = await Runner.run(trip_booking_agent, goal, max_turns=15)

    print("\n" + "=" * 60)
    print("AGENT'S FINAL SUMMARY")
    print("=" * 60)
    print(result.final_output)

    print("\n" + "=" * 60)
    print("GROUND TRUTH: actual state of the stateful world, independent of the model's text")
    print("=" * 60)
    total_spent = sum(_world["booked_legs"].values())
    for flight_id, price in _world["booked_legs"].items():
        print(f"    booked: {flight_id} at ${price:.2f}")
    print(f"    TOTAL SPENT: ${total_spent:.2f} (budget: ${TOTAL_TRIP_BUDGET:.2f})")
    print(
        f"    {'WITHIN BUDGET' if total_spent <= TOTAL_TRIP_BUDGET else 'OVER BUDGET'} "
        f"by ${abs(TOTAL_TRIP_BUDGET - total_spent):.2f}"
    )


if __name__ == "__main__":
    asyncio.run(main())
