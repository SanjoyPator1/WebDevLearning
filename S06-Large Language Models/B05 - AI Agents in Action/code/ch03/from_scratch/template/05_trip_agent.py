# Problem 05 -- the chapter 2 agent loop, pointed at tools that now live on
# an MCP server instead of in this file.

import asyncio
import json
import os

from dotenv import load_dotenv
from mcp.client import Client
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

SERVER_URL = "http://127.0.0.1:8005/mcp"


class McpToolbox:
    """Turns an MCP server's tools into OpenAI-shaped schemas, and routes a
    model's tool calls back through the MCP client that owns them."""

    def __init__(self, mcp_client: Client):
        self.mcp_client = mcp_client
        self.schemas: list[dict] = []

    async def load(self) -> None:
        # your turn: list_tools(), build self.schemas (OpenAI function shape)
        raise NotImplementedError

    async def call(self, name: str, arguments: dict) -> str:
        # your turn: call_tool, then turn the result into a string --
        # "ERROR: " + text if is_error, else json.dumps(structured_content),
        # else join the text blocks in content
        raise NotImplementedError


async def run_tool_loop(messages, toolbox: McpToolbox, *, max_steps=6):
    # your turn: same loop shape as chapter 2, but dispatch tool calls
    # through toolbox.call(name, arguments) instead of a local handler dict
    raise NotImplementedError


async def main() -> None:
    print(f"[agent] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        # your turn: fetch the persona prompt and the travel-rules resource,
        # combine them into one system message -- this is the app deciding,
        # not the model

        # your turn: build an McpToolbox, load it, print the tool names

        # your turn: build messages (system + a user mood message), run the
        # loop, print the final answer
        raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
