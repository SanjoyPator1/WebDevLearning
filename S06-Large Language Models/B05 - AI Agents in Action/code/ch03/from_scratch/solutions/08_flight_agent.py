# Problem 08 -- the model only ever sees one tool call and one result for
# book_flight. The question to the user is handled by this client.

# TIPS:
# 1. Good problem statement - it teaches you how the mcp server tool can ask question and get its answer and act accordingly
# 2. mainly focus on elicitation_callback - input is ran on a different thread as it can block the main event loop so use asyncio.to_thread
# 3. here the content confirm: true is hardcoded but in production we will use a different method

import asyncio
import json
import os

from dotenv import load_dotenv
from mcp.client import Client
from mcp_types import ElicitRequestParams, ElicitResult
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

SERVER_URL = "http://127.0.0.1:8008/mcp"


async def elicitation_callback(context, params: ElicitRequestParams) -> ElicitResult:
    # your turn: print params.message, ask the user with
    # await asyncio.to_thread(input, ...), return an ElicitResult
    # (action="accept", content={"confirm": True}) or action="decline"
    
    print(f"\n  [server asks] {params.message}")
    answer = await asyncio.to_thread(input, "   Confirm? (y/n): ")

    # in here the content is hardcoded as confirm : True
    # but in production we will have other way of doing this in 
    # runtime using schema maybe jsonschema-form (web) or pydantic
    if answer.strip().lower().startswith("y"):
        return ElicitResult(action="accept", content={"confirm" : True})

    return ElicitResult(action= "decline")


async def run_tool_loop(mcp_client: Client, messages, schemas, *, max_steps=6):
    # your turn: same loop shape as earlier problems, dispatching through
    # mcp_client.call_tool directly (no toolbox class needed for one server)
    for _ in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=schemas
        )
        message = response.choices[0].message

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return message.content or ""

        messages.append(
            {"role": "assistant", "tool_calls": [tc.model_dump() for tc in message.tool_calls]}
        )

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            print(f"  tool call: {tool_call.function.name}({arguments})")

            result = await mcp_client.call_tool(tool_call.function.name, arguments)

            if result.is_error:
                content = "Error: " + result.content[0].text
            else:
                content = json.dumps(result.structured_content)

            print(f"  tool result: {content}")

            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": content}
            )

    return None


async def main() -> None:
    print(f"[agent] connecting to {SERVER_URL}")

    async with Client(SERVER_URL, elicitation_callback=elicitation_callback) as mcp_client:
        # your turn: list_tools, build schemas, build messages (a system
        # message that tells the model book_flight already handles
        # confirmation itself, plus a user request), run the loop, print the
        # final answer
        
        tools = await mcp_client.list_tools()

        schemas = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.input_schema,
                },
            }
            for t in tools.tools
        ]

        messages = [
            {
                "role" : "system",
                "content" : (
                    "You help book flights. Use the flight tools. Call "
                    "book_flight directly once you know which flight to book "
                    "-- it already asks the passenger to confirm the price "
                    "itself, so you do not need to ask in chat first."
                )
            },
            {"role": "user", "content": "Book me the cheapest flight from Delhi to Goa. My name is Sanjoy."},

        ]

        final_answer = await run_tool_loop(mcp_client, messages, schemas)

        print("\nFinal answer")
        print(final_answer or "(step budget ran out before a final answer)")



if __name__ == "__main__":
    asyncio.run(main())

# TERMINAL OUTPUT

# python 08_flight_agent.py 
# [agent] connecting to http://127.0.0.1:8008/mcp
#   tool call: search_flights({'destination': 'Goa', 'origin': 'Delhi'})
#   tool result: {"result": [{"id": "AI-101", "price": 5775}, {"id": "6E-202", "price": 5275}]}
#   tool call: book_flight({'passenger_name': 'Sanjoy', 'flight_id': '6E-202'})

#   [server asks] Book flight 6E-202 for Sanjoy at Rs. 5275?
#    Confirm? (y/n): y
#   tool result: {"status": "booked", "confirmation": "GOA-4129", "reason": null, "price": 5275}

# Final answer
# Your flight from Delhi to Goa has been successfully booked! 

# **Booking Details:**
# * **Flight ID:** 6E-202
# * **Passenger Name:** Sanjoy
# * **Confirmation Code:** GOA-4129
# * **Price:** ₹5,275

# User (human) waits for sometime and reply again when the current price changes
# python 08_flight_agent.py
# [agent] connecting to http://127.0.0.1:8008/mcp
#   tool call: search_flights({'origin': 'Delhi', 'destination': 'Goa'})
#   tool result: {"result": [{"id": "AI-101", "price": 5625}, {"id": "6E-202", "price": 5125}]}
#   tool call: book_flight({'flight_id': '6E-202', 'passenger_name': 'Sanjoy'})

#   [server asks] Book flight 6E-202 for Sanjoy at Rs. 5125?
#    Confirm? (y/n): y
#   tool result: Error: Error executing tool book_flight: the fare changed since you were quoted Rs. 5125 (it is now Rs. 5225). call search_flights again, then try booking again.
#   tool call: search_flights({'destination': 'Goa', 'origin': 'Delhi'})
#   tool result: {"result": [{"id": "AI-101", "price": 5725}, {"id": "6E-202", "price": 5225}]}
#   tool call: book_flight({'passenger_name': 'Sanjoy', 'flight_id': '6E-202'})

#   [server asks] Book flight 6E-202 for Sanjoy at Rs. 5225?
#    Confirm? (y/n): y
#   tool result: {"status": "booked", "confirmation": "GOA-5547", "reason": null, "price": 5225}

# Final answer
# I have successfully booked the cheapest flight (6E-202) from Delhi to Goa for you. 

# **Booking Details:**
# - **Passenger Name:** Sanjoy
# - **Flight ID:** 6E-202
# - **Confirmation Code:** GOA-5547
# - **Price:** Rs. 5225

