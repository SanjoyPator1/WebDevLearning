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
        # your turn: list_tools(), keep only tools in self.allowlist (if set),
        # build self.schemas
        raise NotImplementedError

    async def call(self, name: str, arguments: dict) -> str:
        # your turn: call_tool, turn the result into a string -- same pattern
        # as chapter 3's McpToolbox
        raise NotImplementedError


class CallStats(BaseModel):
    calls: int = 0
    prompt_tokens: int = 0


async def run_tool_loop(messages, toolbox: McpToolbox, stats: CallStats, *, max_steps=6):
    # your turn: same loop shape as chapter 3, but also add
    # response.usage.prompt_tokens into stats.prompt_tokens and increment
    # stats.calls on every completion call
    raise NotImplementedError


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
    # your turn: one McpToolbox with every tool, MONOLITH_PROMPT + TICKET,
    # print the tool description size, run the loop, print calls and tokens
    raise NotImplementedError


async def run_flow(mcp_client: Client) -> tuple[str, CallStats]:
    # your turn: three stages (triage, billing, drafting), each with its own
    # McpToolbox (no-tools / billing allowlist / no-tools), each stage's
    # output feeding the next stage's input, sharing one CallStats so you
    # can see the per-stage deltas
    raise NotImplementedError


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
