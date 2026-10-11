# Problem 01 -- a client that starts the server itself and calls both tools.
# No model involved here, this is just you and the protocol.

import asyncio
import sys
from pathlib import Path

from mcp import StdioServerParameters
from mcp.client import Client

SERVER_PATH = Path(__file__).parent / "01_research_server.py"


async def main() -> None:
    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])

    print(f"[client] starting {SERVER_PATH.name} over STDIO")
    async with Client(server_params) as client:
        tools = await client.list_tools()
        print("[client] tools on this server:")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description}")
            print(f"    input_schema: {tool.input_schema}")

        print()
        result = await client.call_tool("get_research_sources", {})
        print("[client] call_tool('get_research_sources', {})")
        print(f"  content            : {result.content}")
        print(f"  structured_content : {result.structured_content}")
        print(f"  is_error           : {result.is_error}")

        print()
        sentence = "MCP is just JSON-RPC with rules"
        result = await client.call_tool("count_words", {"text": sentence})
        print(f"[client] call_tool('count_words', {{'text': {sentence!r}}})")
        print(f"  structured_content : {result.structured_content}")
        print(f"  is_error           : {result.is_error}")


if __name__ == "__main__":
    asyncio.run(main())
