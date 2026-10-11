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

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)]
    )

    print(f"[client] starting {SERVER_PATH.name} over STDIO")

    async with Client(server_params) as client:
        tools = await client.list_tools()
        print("\n[client] tools on the server:")

        for tool in tools.tools:
            print(f"    - {tool.name} : {tool.description}")
            print(f"      input_schema : {tool.input_schema}")
        
        result = await client.call_tool("get_research_sources", {})
        print("\n[client] call_tool('get_research_sources', {})")
        print(f"     - content : {result.content}")
        print(f"     - structured_content : {result.structured_content}")
        print(f"     - is_error : {result.is_error}")

        sentence = "MCP is just JSON_RPC with rules"
        result = await client.call_tool("count_words", {"text": sentence})
        print(f"[client] call_tool('count_words', {{'text': {sentence!r}}})")
        print(f"  structured_content : {result.structured_content}")
        print(f"  is_error           : {result.is_error}")

if __name__ == "__main__":
    asyncio.run(main())

# Got this output in terminal
 
# [client] starting 01_research_server.py over STDIO

# [client] tools on the server:
#     - get_research_sources : Return the list of research sources this server knows about.
#       input_schema : {'type': 'object', 'properties': {}, 'title': 'get_research_sourcesArguments'}
#     - count_words : Count the words in a piece of text, splitting on whitespace.
#       input_schema : {'type': 'object', 'properties': {'text': {'title': 'Text', 'type': 'string'}}, 'required': ['text'], 'title': 'count_wordsArguments'}
# get_research_sources tool called : 

# [client] call_tool('get_research_sources', {})
#      - content : [TextContent(type='text', text='Wikipedia', annotations=None, meta=None), TextContent(type='text', text='Google', annotations=None, meta=None), TextContent(type='text', text='YouTube', annotations=None, meta=None)]
#      - structured_content : {'result': ['Wikipedia', 'Google', 'YouTube']}
#      - is_error : False
# count_words called with: 'MCP is just JSON_RPC with rules'
# [client] call_tool('count_words', {'text': 'MCP is just JSON_RPC with rules'})
#   structured_content : {'result': 6}
#   is_error           : False