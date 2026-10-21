# Problem 01 -- the same ticket solved two ways: one agent holding all
# eight tools, versus a flow of three narrow agents. The MCP server from
# 00_support_server.py must already be running on port 8100.

import asyncio
import json
import os

from dotenv import load_dotenv
from mcp.client import Client
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

SERVER_URL = "http://127.0.0.1:8100/mcp"

TICKET = "I was charged twice for order ORD-4471. Please sort it out and tell me what happens next."


class McpToolbox:
    """Turns an MCP server's tools into OpenAI-shaped schemas, filtered by an
    optional allowlist, and routes a model's tool calls back through the
    MCP client that owns them."""

    def __init__(self, mcp_client: Client, allowlist: list[str] | None = None):
        self.mcp_client = mcp_client
        self.allowlist = set(allowlist) if allowlist is not None else None
        self.schemas: list[dict] = []

    async def load(self) -> None:
        tools = await self.mcp_client.list_tools()
        kept = [
            tool
            for tool in tools.tools
            if self.allowlist is None or tool.name in self.allowlist
        ]
        self.schemas = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in kept
        ]

    async def call(self, name: str, arguments: dict) -> str:
        result = await self.mcp_client.call_tool(name, arguments)
        if result.is_error:
            return "ERROR: " + result.content[0].text
        if result.structured_content is not None:
            return json.dumps(result.structured_content)
        return "\n".join(block.text for block in result.content)


class CallStats(BaseModel):
    calls: int = 0
    prompt_tokens: int = 0


async def run_tool_loop(messages, toolbox: McpToolbox, stats: CallStats, *, max_steps=6):
    for _ in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=toolbox.schemas or None
        )
        stats.calls += 1
        stats.prompt_tokens += response.usage.prompt_tokens
        message = response.choices[0].message

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return message.content or ""

        messages.append(
            {"role": "assistant", "tool_calls": [tc.model_dump() for tc in message.tool_calls]}
        )

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            result_text = await toolbox.call(tool_call.function.name, arguments)
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
            )

    return None


def tool_schema_size(toolbox: McpToolbox) -> tuple[int, int]:
    chars = len(json.dumps(toolbox.schemas))
    return chars, chars // 4


MONOLITH_PROMPT = """
You are a customer support assistant for an online store.
You handle billing questions, account questions, service outages, and
help-article lookups, and you write the final reply to the customer
yourself once you have what you need.
"""

TRIAGE_PROMPT = """
You are a triage assistant. Read the support ticket and reply with one
short line naming the order id and the problem, nothing else.
"""

BILLING_PROMPT = """
You are a billing assistant. You have tools to look up an order and list
a customer's charges. Investigate the ticket and report your findings in
one or two sentences.
"""

DRAFTING_PROMPT = """
You are a drafting assistant. Turn the billing findings you are given
into a short, friendly reply to the customer. Do not call any tools.
"""


async def run_monolith(mcp_client: Client) -> tuple[str, CallStats]:
    toolbox = McpToolbox(mcp_client)
    await toolbox.load()
    chars, tokens_est = tool_schema_size(toolbox)
    print(f"  tool descriptions sent on EVERY call : {chars:,} chars (~{tokens_est:,} tokens)")

    stats = CallStats()
    messages = [
        {"role": "system", "content": MONOLITH_PROMPT},
        {"role": "user", "content": TICKET},
    ]
    final_answer = await run_tool_loop(messages, toolbox, stats)
    print(f"  model calls                          : {stats.calls}")
    print(f"  total prompt_tokens                  : {stats.prompt_tokens:,}")
    return final_answer or "(no final answer)", stats


async def run_flow(mcp_client: Client) -> tuple[str, CallStats]:
    stats = CallStats()

    no_tools = McpToolbox(mcp_client, allowlist=[])
    await no_tools.load()

    triage_messages = [
        {"role": "system", "content": TRIAGE_PROMPT},
        {"role": "user", "content": TICKET},
    ]
    triage_answer = await run_tool_loop(triage_messages, no_tools, stats)
    print(f"  triage   : 0 tools, {stats.calls} call,  prompt_tokens {stats.prompt_tokens}")

    billing_calls_before = stats.calls
    billing_tokens_before = stats.prompt_tokens
    billing_toolbox = McpToolbox(mcp_client, allowlist=["lookup_order", "list_charges"])
    await billing_toolbox.load()
    billing_messages = [
        {"role": "system", "content": BILLING_PROMPT},
        {"role": "user", "content": triage_answer or TICKET},
    ]
    billing_answer = await run_tool_loop(billing_messages, billing_toolbox, stats)
    print(
        f"  billing  : 2 tools, {stats.calls - billing_calls_before} calls, "
        f"prompt_tokens {stats.prompt_tokens - billing_tokens_before}"
    )

    drafting_calls_before = stats.calls
    drafting_tokens_before = stats.prompt_tokens
    drafting_messages = [
        {"role": "system", "content": DRAFTING_PROMPT},
        {"role": "user", "content": billing_answer or "No findings."},
    ]
    final_answer = await run_tool_loop(drafting_messages, no_tools, stats)
    print(
        f"  drafting : 0 tools, {stats.calls - drafting_calls_before} call,  "
        f"prompt_tokens {stats.prompt_tokens - drafting_tokens_before}"
    )
    print(f"  total prompt_tokens                  : {stats.prompt_tokens:,}")

    return final_answer or "(no final answer)", stats


async def main() -> None:
    async with Client(SERVER_URL) as mcp_client:
        print("MONOLITH (1 agent, 8 tools)")
        monolith_answer, monolith_stats = await run_monolith(mcp_client)

        print("\nFLOW (3 agents: triage -> billing -> drafting)")
        flow_answer, flow_stats = await run_flow(mcp_client)

        print("\nBoth replies should describe the duplicate $150 charge on ORD-4471.")
        print(f"monolith reply:\n  {monolith_answer}")
        print(f"flow reply:\n  {flow_answer}")

        saved = monolith_stats.prompt_tokens - flow_stats.prompt_tokens
        print(f"\ntokens saved by the flow: {saved:,}")


if __name__ == "__main__":
    asyncio.run(main())
