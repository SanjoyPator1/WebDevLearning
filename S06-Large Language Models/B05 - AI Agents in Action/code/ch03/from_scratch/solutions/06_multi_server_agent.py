# Problem 06 -- one agent, three servers at once: your recipe server
# (stdio), your trip server (http, started separately), and a Node.js
# filesystem server via npx (stdio). No new server in this file.

# >> NOTE: good problem statement as this makes use of the _routes with prefix and tuple of client and toolname

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

    # in add server method we are getting prefix to put it in front of the tool name
    # e.g. trips__get_destination_by_mood and
    # _routes contains = { prefixed_name, (Client, tool.name)tuple } i.e.
    # {trips__get_destination_by_mood : (trips_client, get_destination_by_mood)}
    # here key is the prefixed + __ + tool name that will be shown to the llm and
    # value is a tuple of Client and the tool name
    async def add_server(self, prefix: str, mcp_client: Client, allowlist: set[str] | None = None) -> None:
        # your turn: list_tools(), skip anything not in allowlist (if given),
        # build prefixed schemas, store prefixed_name -> (mcp_client, original_name)
        tools = await mcp_client.list_tools()

        kept, dropped = [], []

        for tool in tools.tools:
            # guard clause - check if the tool is not in allowlist add it to dropped and continue
            if allowlist is not None and tool.name not in allowlist:
                dropped.append(tool.name)
                continue

            # if not in dropped - add the tool in kept
            kept.append(tool.name)
            prefixed_name = f"{prefix}__{tool.name}"
            self._routes[prefixed_name] = (mcp_client, tool.name)
            self.schemas.append(
                {
                    "type" : "function",
                    "function" : {
                        "name" : prefixed_name,
                        "description" : tool.description or "",
                        "parameters" : tool.input_schema
                    }
                }
            )

        if allowlist is not None:
            print(f"[agent] {prefix}: kept {len(kept)} tools, dropped {len(dropped)}: {dropped}")


    async def call(self, prefixed_name: str, arguments: dict) -> str:
        # your turn: look up the route, call_tool with the ORIGINAL name,
        # turn the result into a string same as problem 05
        
        # here we are using the routes with prefixed_name (key) to 
        # get the tuple value mcp_client and orginal tool name
        mcp_client, original_name = self._routes[prefixed_name]

        # use the above mcp client and call tool with the tool name original
        result = await mcp_client.call_tool(original_name, arguments)

        if result.is_error:
            return "ERROR: " + result.content[0].text
        if result.structured_content is not None:
            return json.dumps(result.structured_content)
        return "\n".join(block.text for block in result.content)


async def run_tool_loop(messages, toolbox: MultiToolbox, *, max_steps=8):
    # your turn: same loop shape as problem 05
    for _ in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=toolbox.schemas
        )
        message = response.choices[0].message

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages, message.content or ""

        messages.append(
            {"role": "assistant", "tool_calls": [tc.model_dump() for tc in message.tool_calls]}
        )

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            print(f"  tool call: {tool_call.function.name}({arguments})")

            # this toolbox call doesnot change - its the same one as previous agents
            # the new prefixed route tool call is handled by toolbox call function
            result_text = await toolbox.call(tool_call.function.name, arguments)
            print(f"  tool result: {result_text}")

            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
            )

    return messages, None


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
        recipes_client = await stack.enter_async_context(Client(recipes_params))
        trips_client = await stack.enter_async_context(Client("http://127.0.0.1:8005/mcp"))
        files_client = await stack.enter_async_context(Client(files_params))

        print("[agent] connected: recipes (stdio), trips (http :8005), files (stdio via npx)")

        # your turn: build a MultiToolbox, add all three servers (files with
        # the allowlist), print the combined tool list
        toolbox = MultiToolbox()

        await toolbox.add_server("recipes", recipes_client)
        await toolbox.add_server("trips", trips_client)
        await toolbox.add_server("files", files_client, allowlist=FILES_ALLOWLIST)

        names = [s["function"]["name"] for s in toolbox.schemas]
        print(f"[agent] tools the model sees ({len(names)}):\n  " + ", ".join(names))

        # your turn: build messages for a task that needs all three servers,
        # run the loop, print the final answer

        messages = [
            {
                "role": "system",
                "content": (
                    "You plan trips, suggest recipes, and can save files. "
                    "Use the trip tools to pick a destination, the recipe "
                    "tools to suggest something to cook, and the file tools "
                    "to save the plan when asked."
                ),
            },
            {
                "role": "user",
                "content": (
                    "I'm feeling relaxed. Pick a destination, suggest an "
                    "Indian recipe I can cook after the trip, and save the "
                    "plan to trip_plan.md."
                ),
            },
        ]

        messages, final_answer = await run_tool_loop(messages, toolbox)

        print("\nFINAL ANSWER")
        print(final_answer or "(step budget ran out before a final answer)")

        # your turn: read back 06_sandbox/trip_plan.md from disk and print it
        saved_path = SANDBOX_DIR / "trip_plan.md"
        if saved_path.exists():
            print(f"\n[agent] {saved_path.relative_to(HERE)} now contains:")
            print(saved_path.read_text())


if __name__ == "__main__":
    asyncio.run(main())


# TERMINAL OUTPUT

# python 06_multi_server_agent.py


# Secure MCP Filesystem Server running on stdio
# [agent] connected: recipes (stdio), trips (http :8005), files (stdio via npx)
# Client does not support MCP Roots, using allowed directories set from server args: [
#   '/Users/abc/Desktop/dev/others/ai/WebDevLearning/S06-Large Language Models/B05 - AI Agents in Action/code/ch03/from_scratch/solutions/06_sandbox'
# ]
# [agent] files: kept 3 tools, dropped 11: ['read_file', 'read_media_file', 'read_multiple_files', 'edit_file', 'create_directory', 'list_directory_with_sizes', 'directory_tree', 'move_file', 'search_files', 'get_file_info', 'list_allowed_directories']
# [agent] tools the model sees (8):
#   recipes__search_recipes, recipes__broken_tool, trips__get_destination_by_mood, trips__get_weather_condition_by_destination, trips__get_activities_by_destination, files__read_text_file, files__write_file, files__list_directory
#   tool call: trips__get_destination_by_mood({'mood': 'relaxed'})
#   tool result: {"result": ["India", "France"]}
#   tool call: recipes__search_recipes({'cuisine': 'Indian'})
# [MCP tool call] : search_recipes for cuisine Indian -> []
#   tool result: {"result": []}
#   tool call: recipes__search_recipes({'cuisine': 'indian'})
# [MCP tool call] : search_recipes for cuisine indian -> ['masala chai']
#   tool result: {"result": ["masala chai"]}
#   tool call: files__write_file({'content': '# Trip & Recipe Plan\n\n## Destination\n- **Country:** India\n\n## Post-Trip Recipe\n- **Recipe:** Masala Chai\n', 'path': 'trip_plan.md'})
#   tool result: {"content": "Successfully wrote to trip_plan.md"}

# FINAL ANSWER
# I've put together your plan!

# - **Destination:** India (perfect for a relaxed vibe)
# - **Recipe to cook after the trip:** Masala Chai
# - **Saved to:** `trip_plan.md`

# [agent] 06_sandbox/trip_plan.md now contains:
# # Trip & Recipe Plan

# ## Destination
# - **Country:** India

# ## Post-Trip Recipe
# - **Recipe:** Masala Chai
