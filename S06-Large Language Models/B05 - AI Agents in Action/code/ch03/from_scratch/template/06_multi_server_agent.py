# Problem 06 -- one agent, three servers at once: your recipe server
# (stdio), your trip server (http, started separately), and a Node.js
# filesystem server via npx (stdio). No new server in this file.

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from dotenv import load_dotenv
from mcp import StdioServerParameters
from mcp.client import Client
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

HERE = Path(__file__).parent
SANDBOX_DIR = HERE / "06_sandbox"
SANDBOX_DIR.mkdir(exist_ok=True)

FILES_ALLOWLIST = {"read_text_file", "write_file", "list_directory"}


class MultiToolbox:
    """Loads tools from several MCP clients, prefixes each name with its
    server, and can drop tools you don't trust."""

    def __init__(self):
        self.schemas: list[dict] = []
        self._routes: dict[str, tuple[Client, str]] = {}

    async def add_server(self, prefix: str, mcp_client: Client, allowlist: set[str] | None = None) -> None:
        # your turn: list_tools(), skip anything not in allowlist (if given),
        # build prefixed schemas, store prefixed_name -> (mcp_client, original_name)
        raise NotImplementedError

    async def call(self, prefixed_name: str, arguments: dict) -> str:
        # your turn: look up the route, call_tool with the ORIGINAL name,
        # turn the result into a string same as problem 05
        raise NotImplementedError


async def run_tool_loop(messages, toolbox: MultiToolbox, *, max_steps=8):
    # your turn: same loop shape as problem 05
    raise NotImplementedError


async def main() -> None:
    recipes_params = StdioServerParameters(
        command=sys.executable, args=[str(HERE / "02_recipe_server.py")]
    )
    files_params = StdioServerParameters(
        command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", str(SANDBOX_DIR)]
    )

    async with AsyncExitStack() as stack:
        # your turn: enter_async_context three clients: recipes (stdio),
        # trips (http://127.0.0.1:8005/mcp -- start 05_trip_server.py with
        # MCP_TRANSPORT=streamable-http in another terminal first), files (stdio)

        # your turn: build a MultiToolbox, add all three servers (files with
        # the allowlist), print the combined tool list

        # your turn: build messages for a task that needs all three servers,
        # run the loop, print the final answer

        # your turn: read back 06_sandbox/trip_plan.md from disk and print it
        raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
