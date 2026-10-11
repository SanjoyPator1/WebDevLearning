# Problem 05 -- the chapter 2 agent loop, unchanged, pointed at tools that
# now live on an MCP server instead of in this file. The app fetches the
# persona (a prompt) and the house rules (a resource) itself, before the
# loop starts; the model only ever sees the three tools.

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
        tools = await self.mcp_client.list_tools()
        self.schemas = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in tools.tools
        ]

    async def call(self, name: str, arguments: dict) -> str:
        result = await self.mcp_client.call_tool(name, arguments)
        if result.is_error:
            return "ERROR: " + result.content[0].text
        if result.structured_content is not None:
            return json.dumps(result.structured_content)
        return "\n".join(block.text for block in result.content)


async def run_tool_loop(messages, toolbox: McpToolbox, *, max_steps=6):
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
    print(f"[agent] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        prompt_result = await mcp_client.get_prompt("trip_planner_persona")
        persona = prompt_result.messages[0].content.text

        rules_result = await mcp_client.read_resource("trip://travel-rules")
        rules = rules_result.contents[0].text

        system_prompt = f"{persona}\n\n**HOUSE RULES**\n{rules}"
        print("[agent] system prompt built from: prompt 'trip_planner_persona' + resource 'trip://travel-rules'")

        toolbox = McpToolbox(mcp_client)
        await toolbox.load()
        print(f"[agent] tools from server: {[s['function']['name'] for s in toolbox.schemas]}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "I'm feeling adventurous this weekend"},
        ]

        messages, final_answer = await run_tool_loop(messages, toolbox)

        print("\nFINAL ANSWER")
        print(final_answer or "(step budget ran out before a final answer)")


if __name__ == "__main__":
    asyncio.run(main())
