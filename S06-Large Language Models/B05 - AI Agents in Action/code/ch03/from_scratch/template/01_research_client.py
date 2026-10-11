# Problem 01 -- client that starts the server and calls both tools.

import asyncio
import sys
from pathlib import Path

from mcp import StdioServerParameters
from mcp.client import Client

SERVER_PATH = Path(__file__).parent / "01_research_server.py"


async def main() -> None:
    # your turn: build StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])

    # your turn: open the client with `async with Client(server_params) as client:`
    # and do everything below inside that block

    # your turn: list_tools() and print each tool's name, description, input_schema

    # your turn: call_tool("get_research_sources", {}) and print content,
    # structured_content, is_error

    # your turn: call_tool("count_words", {"text": "..."}) and print the same
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
