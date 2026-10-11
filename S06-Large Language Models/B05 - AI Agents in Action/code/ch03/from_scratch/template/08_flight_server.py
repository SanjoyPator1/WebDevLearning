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
    raise NotImplementedError


def _flights_for(origin: str, destination: str) -> list[dict]:
    return FLIGHTS.get((origin, destination), FLIGHTS["others"])


@mcp.tool()
def search_flights(origin: str, destination: str) -> list[Flight]:
    """List flights between two cities with their current price."""
    # your turn
    raise NotImplementedError


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
    # round 2: read the quoted price back from ctx.request_state, ToolError
    # if the current fare has moved, else look at
    # ctx.input_responses["confirm"] (unwrap .root if present) -- decline or
    # cancel returns a normal cancelled BookingResult, accept books it
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8008, stateless_http=True)
