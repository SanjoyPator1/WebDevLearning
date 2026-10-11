# Problem 06 -- one agent, three servers at once: your own recipe server
# (stdio), your own trip server (http, started separately), and a Node.js
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
    """Loads tools from several MCP clients at once, prefixes each name with
    its server so there are no clashes, and can drop tools you don't trust."""

    def __init__(self):
        self.schemas: list[dict] = []
        self._routes: dict[str, tuple[Client, str]] = {}

    async def add_server(self, prefix: str, mcp_client: Client, allowlist: set[str] | None = None) -> None:
        tools = await mcp_client.list_tools()
        kept, dropped = [], []
        for tool in tools.tools:
            if allowlist is not None and tool.name not in allowlist:
                dropped.append(tool.name)
                continue
            kept.append(tool.name)
            prefixed_name = f"{prefix}__{tool.name}"
            self._routes[prefixed_name] = (mcp_client, tool.name)
            self.schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": prefixed_name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                }
            )
        if allowlist is not None:
            print(f"[agent] {prefix}: kept {len(kept)} tools, dropped {len(dropped)}: {dropped}")

    async def call(self, prefixed_name: str, arguments: dict) -> str:
        mcp_client, original_name = self._routes[prefixed_name]
        result = await mcp_client.call_tool(original_name, arguments)
        if result.is_error:
            return "ERROR: " + result.content[0].text
        if result.structured_content is not None:
            return json.dumps(result.structured_content)
        return "\n".join(block.text for block in result.content)


async def run_tool_loop(messages, toolbox: MultiToolbox, *, max_steps=8):
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
        recipes_client = await stack.enter_async_context(Client(recipes_params))
        trips_client = await stack.enter_async_context(Client("http://127.0.0.1:8005/mcp"))
        files_client = await stack.enter_async_context(Client(files_params))

        print("[agent] connected: recipes (stdio), trips (http :8005), files (stdio via npx)")

        toolbox = MultiToolbox()
        await toolbox.add_server("recipes", recipes_client)
        await toolbox.add_server("trips", trips_client)
        await toolbox.add_server("files", files_client, allowlist=FILES_ALLOWLIST)

        names = [s["function"]["name"] for s in toolbox.schemas]
        print(f"[agent] tools the model sees ({len(names)}):\n  " + ", ".join(names))

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

        saved_path = SANDBOX_DIR / "trip_plan.md"
        if saved_path.exists():
            print(f"\n[agent] {saved_path.relative_to(HERE)} now contains:")
            print(saved_path.read_text())


if __name__ == "__main__":
    asyncio.run(main())
