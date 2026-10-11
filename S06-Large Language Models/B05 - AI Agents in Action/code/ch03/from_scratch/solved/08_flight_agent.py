# Problem 08 -- the model only ever sees one tool call and one result for
# book_flight. The question to the user, and the two rounds behind it, are
# handled entirely between this client and the server.

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
    print(f"\n  [server asks] {params.message}")
    answer = await asyncio.to_thread(input, "  Confirm? (y/n): ")
    if answer.strip().lower().startswith("y"):
        return ElicitResult(action="accept", content={"confirm": True})
    return ElicitResult(action="decline")


async def run_tool_loop(mcp_client: Client, messages, schemas, *, max_steps=6):
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
                "role": "system",
                "content": (
                    "You help book flights. Use the flight tools. Call "
                    "book_flight directly once you know which flight to book "
                    "-- it already asks the passenger to confirm the price "
                    "itself, so you do not need to ask in chat first."
                ),
            },
            {"role": "user", "content": "Book me the cheapest flight from Delhi to Goa. My name is Sanjoy."},
        ]

        final_answer = await run_tool_loop(mcp_client, messages, schemas)

        print("\nFINAL ANSWER")
        print(final_answer or "(step budget ran out before a final answer)")


if __name__ == "__main__":
    asyncio.run(main())
