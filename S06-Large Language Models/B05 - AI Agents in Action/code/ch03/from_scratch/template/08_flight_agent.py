# Problem 08 -- the model only ever sees one tool call and one result for
# book_flight. The question to the user is handled by this client.

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
    raise NotImplementedError


async def run_tool_loop(mcp_client: Client, messages, schemas, *, max_steps=6):
    # your turn: same loop shape as earlier problems, dispatching through
    # mcp_client.call_tool directly (no toolbox class needed for one server)
    raise NotImplementedError


async def main() -> None:
    print(f"[agent] connecting to {SERVER_URL}")

    async with Client(SERVER_URL, elicitation_callback=elicitation_callback) as mcp_client:
        # your turn: list_tools, build schemas, build messages (a system
        # message that tells the model book_flight already handles
        # confirmation itself, plus a user request), run the loop, print the
        # final answer
        raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
