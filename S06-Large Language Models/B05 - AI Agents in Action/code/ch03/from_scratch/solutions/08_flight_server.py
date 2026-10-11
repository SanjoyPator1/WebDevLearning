# Problem 08 -- a tool that cannot finish without asking first. Round 1
# quotes a price and asks for confirmation; round 2 checks the price is
# still good and finishes the booking.

import json
import random
import sys
import time

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ElicitRequest, ElicitRequestFormParams, InputRequiredResult
from pydantic import BaseModel

mcp = MCPServer("Flight Desk")

FLIGHTS = {
    ("Delhi", "Goa"): [
        {"id": "AI-101", "base_price": 5400},
        {"id": "6E-202", "base_price": 4900},
    ],
    "others": [{"id": "XX-000", "base_price": 6000}],
}


class Flight(BaseModel):
    id: str
    price: int


class BookingResult(BaseModel):
    status: str
    confirmation: str | None = None
    reason: str | None = None
    price: int | None = None


def _current_fare(base_price: int) -> int:
    """The fare bumps every 30 seconds, cycling every 10 minutes."""
    # your turn
    # The fare bumps every 30 seconds, to simulate a price that really
    # moves while a human is deciding. The window cycles every 10 minutes so
    # the bump stays a small, readable number instead of tracking the whole
    # Unix epoch.
    window = (int(time.time()) % 600) // 30
    return base_price + window * 25

def _flights_for(origin: str, destination: str) -> list[dict]:
    return FLIGHTS.get((origin, destination), FLIGHTS["others"])


@mcp.tool()
def search_flights(origin: str, destination: str) -> list[Flight]:
    """List flights between two cities with their current price."""
    # your turn
    return [
                Flight(id=f["id"], price=_current_fare(f["base_price"])) 
                    for f in _flights_for(origin, destination)
           ]

@mcp.tool()
async def book_flight(
    flight_id: str, passenger_name: str, ctx: Context
) -> BookingResult | InputRequiredResult:
    """Book a flight. Asks the user to confirm the price before booking."""
    # your turn:
    # round 1 (ctx.input_responses is None): quote the current price,
    # return InputRequiredResult with one "confirm" ElicitRequest (form mode,
    # a boolean schema), request_state carrying the quoted price as json
    #
    # all_flights = [f for flights in FLIGHTS.values() for f in flights]
    all_flights = []

    for flights in FLIGHTS.values():
        for flight in flights:
            all_flights.append(flight)

    # find the first flight whose id matches; if none exists, give me None instead of crashing.
    # can be written simply
    # matching = None
    # for f in all_flights:
    #     if f["id"] == flight_id:
    #         matching = f
    #         break

    matching = next((f for f in all_flights if f["id"] == flight_id), None) 

    if matching is None:
        raise ToolError(f"no such flight: {flight_id}")

    current_price = _current_fare(matching["base_price"])

    if ctx.input_responses is None:
        print(f"  [server] round 1 -- quoting {flight_id} at {current_price}", file=sys.stderr)

        return InputRequiredResult(
            result_type="input_required",
            input_requests={
                "confirm" : ElicitRequest(
                    method="elicitation/create",
                    params=ElicitRequestFormParams(
                        message=f"Book flight {flight_id} for {passenger_name} at Rs. {current_price}?",
                        mode="form",
                        requested_schema={
                            "type" : "object",
                            "properties": {"confirm": {"type": "boolean", "title": "Confirm booking?"}},
                            "required": ["confirm"],
                        }
                    )
                )
            },
            request_state=json.dumps({"quoted_price": current_price}),
        )

    # round 2: read the quoted price back from ctx.request_state, ToolError
    # if the current fare has moved, else look at
    # ctx.input_responses["confirm"] (unwrap .root if present) -- decline or
    # cancel returns a normal cancelled BookingResult, accept books it
    
    quoted_price = json.loads(ctx.request_state)["quoted_price"]
    print(f"  [server] round 2 -- quoted {quoted_price}, now {current_price}", file=sys.stderr)

    if quoted_price != current_price:
        raise ToolError(
            f"the fare changed since you were quoted Rs. {quoted_price} (it is now "
            f"Rs. {current_price}). call search_flights again, then try booking again."
        )

    confirmation = ctx.input_responses["confirm"]
    confirmation = getattr(confirmation, "root", confirmation)

    if confirmation.action != "accept":
        # a lookup, not confirmation.action + "d" -- that turns "cancel" into
        # "canceld", a bug that looks completely plausible until you say it
        # out loud
        past_tense = {"decline": "declined", "cancel": "cancelled"}
        reason = past_tense.get(confirmation.action, confirmation.action)
        return BookingResult(status="cancelled", reason=f"passenger {reason} the booking")

    confirmation_code = f"GOA-{random.randint(1000, 9999)}"

    return BookingResult(status="booked", confirmation=confirmation_code, price=quoted_price)





if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8008, stateless_http=True)
