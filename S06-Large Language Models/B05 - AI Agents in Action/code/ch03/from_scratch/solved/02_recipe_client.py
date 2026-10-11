# Problem 02 -- exercise every primitive, then do a tour of how each one
# fails, to see the different shapes with your own eyes.

import asyncio
import sys
from pathlib import Path

from mcp import MCPError, StdioServerParameters
from mcp.client import Client

SERVER_PATH = Path(__file__).parent / "02_recipe_server.py"


async def main() -> None:
    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])

    async with Client(server_params) as client:
        print("--- resources vs templates ---")
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        print(f"  fixed resources : {[r.uri for r in resources.resources]}")
        print(f"  templates       : {[t.uri_template for t in templates.resource_templates]}")

        print("\n--- reading resources ---")
        index_text = await client.read_resource("recipes://index")
        print(f"  recipes://index ->\n{index_text.contents[0].text}")

        first_name = index_text.contents[0].text.splitlines()[0]
        recipe_text = await client.read_resource(f"recipes://{first_name}")
        print(f"\n  recipes://{first_name} ->\n{recipe_text.contents[0].text}")

        print("\n--- getting a prompt ---")
        prompt_result = await client.get_prompt(
            "cook_with", {"ingredient": "egg", "max_minutes": "15"}
        )
        for message in prompt_result.messages:
            print(f"  [{message.role}] {message.content.text}")

        print("\n--- failure tour ---")

        result = await client.call_tool("search_recipes", {"cuisine": ""})
        print(f"  tool  search_recipes('')  -> is_error={result.is_error}  text={result.content[0].text!r}")

        result = await client.call_tool("broken_tool", {})
        print(f"  tool  broken_tool()       -> is_error={result.is_error}  text={result.content[0].text!r}")

        result = await client.call_tool("no_such_tool", {})
        print(f"  tool  no_such_tool()      -> is_error={result.is_error}  text={result.content[0].text!r}")

        try:
            await client.read_resource("recipes://unknown")
        except MCPError as error:
            print(f"  res   recipes://unknown   -> MCPError code={error.code}")

        try:
            await client.get_prompt("cook_with", {"ingredient": "egg", "max_minutes": "2"})
        except MCPError as error:
            print(f"  prompt cook_with(max=2)   -> MCPError code={error.code} {error.message!r}")


if __name__ == "__main__":
    asyncio.run(main())
