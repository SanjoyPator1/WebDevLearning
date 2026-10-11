# Problem 02 -- exercise every primitive, then tour how each one fails.

import asyncio
import sys
from pathlib import Path

from mcp import MCPError, StdioServerParameters
from mcp.client import Client

SERVER_PATH = Path(__file__).parent / "02_recipe_server.py"


async def main() -> None:
    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])

    async with Client(server_params) as client:
        # your turn: list_resources() and list_resource_templates(), print both

        # your turn: read_resource("recipes://index"), then read one real recipe

        # your turn: get_prompt("cook_with", {"ingredient": "egg", "max_minutes": "15"})
        # print each message's role and text

        # your turn: the failure tour -- one call per failure:
        #   search_recipes('') -> is_error, print text
        #   broken_tool() -> is_error, print text
        #   no_such_tool() -> is_error, print text
        #   read_resource("recipes://unknown") -> catch MCPError, print code
        #   get_prompt("cook_with", max_minutes="2") -> catch MCPError, print code + message
        raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
