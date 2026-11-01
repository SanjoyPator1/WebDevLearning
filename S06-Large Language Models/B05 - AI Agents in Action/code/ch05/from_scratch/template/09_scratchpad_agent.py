# Problem 09 -- the Problem 08 scratchpad, used through a real MCP server.
# Steps 1 to 4 are driven by plain code with no model call: store a few
# thoughts, revise one, branch from one, and watch the server refuse a
# reference to a thought that does not exist. Step 5 hands the same server
# to a real model for a tiny apple word problem, with a correction injected
# half-way so that a real revision has to happen.
#
# Terminal 1:  python 09_scratchpad_server.py     (leave it running, port 8150)
# Terminal 2:  python 09_scratchpad_agent.py

import asyncio
import json
import os
import re

from dotenv import load_dotenv
from mcp.client import Client
from openai import AsyncOpenAI, RateLimitError

load_dotenv()

SERVER_URL = "http://127.0.0.1:8150/mcp"

# Step 5 makes roughly 6 to 10 real model calls. Set this to False to run
# steps 1 to 4 only: no API key, no model calls, no rate limit.
RUN_MODEL_STEP = True
PROVIDER = "gemini"  # "gemini" or "ollama"
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_WAIT_SECONDS = 40

# --- the apple story ---
# Sam has 12 apples, gives 5 to Ana, buys a bag of 8. Then comes a
# correction: Ana really took 6, not 5.
STARTING_APPLES = 12
APPLES_ANA_ACTUALLY_TOOK = 6
APPLES_BOUGHT = 8
EXPECTED_ANSWER_AFTER_CORRECTION = STARTING_APPLES - APPLES_ANA_ACTUALLY_TOOK + APPLES_BOUGHT  # 14


def print_banner(title: str) -> None:
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


async def call_tool_as_text(mcp_client: Client, name: str, arguments: dict) -> str:
    """Call one MCP tool and flatten the result into the string a model
    would see."""
    # your turn: result = await mcp_client.call_tool(name, arguments), then
    #   - result.is_error          -> "ERROR: " + the first content block's text
    #   - result.structured_content is not None -> json.dumps(it)
    #   - otherwise                -> the content blocks' text joined by newlines
    raise NotImplementedError


async def record(
    mcp_client: Client,
    thought_number: int,
    thought: str,
    next_thought_needed: bool = True,
    **extra_fields,
) -> str:
    """Store one thought through record_thought and print it with the
    server's receipt. extra_fields carries is_revision, revises_thought,
    branch_from_thought, branch_id."""
    # your turn: build the arguments dict (thought, thought_number,
    # total_thoughts=7, next_thought_needed, plus **extra_fields), call
    # record_thought through call_tool_as_text, print the thought and the
    # receipt, and return the reply text
    raise NotImplementedError


async def fetch_thoughts(mcp_client: Client) -> list[dict]:
    # your turn: call get_thoughts and return the "thoughts" list from the
    # result's structured_content
    raise NotImplementedError


def print_thought_record(thoughts: list[dict]) -> None:
    """Print the notebook in order: a revision is marked with the thought it
    corrects, a branch thought with its branch name and starting point."""
    # your turn: sort by thought_number; print "#N text" for a plain thought,
    # "#N [revises #M] text" (indented) for a revision, and
    # "#N (branch 'name', from #M) text" (indented) for a branch thought
    raise NotImplementedError


async def clear_scratchpad(mcp_client: Client) -> None:
    await call_tool_as_text(mcp_client, "clear_thoughts", {})


# ---------------------------------------------------------------------
# Steps 1 to 4: no model, just your code talking to the server
# ---------------------------------------------------------------------


async def step_1_store_and_read(mcp_client: Client) -> None:
    print_banner("STEP 1: store three thoughts, then read them back")
    # your turn: record three plain thoughts with record():
    #   #1 Sam starts with 12 apples.
    #   #2 Sam gives 5 apples to Ana: 12 - 5 = 7.
    #   #3 Sam buys a bag of 8: 7 + 8 = 15.
    # then print the notebook with fetch_thoughts + print_thought_record
    raise NotImplementedError


async def step_2_revise(mcp_client: Client) -> None:
    print_banner("STEP 2: a correction arrives -- revise, do not overwrite")
    # your turn: print the new fact (Ana actually took 6, not 5), then record
    #   #4 revising thought 2 (is_revision=True, revises_thought=2): 12 - 6 = 6
    #   #5 revising thought 3: 6 + 8 = 14
    # and print the notebook again: thoughts 2 and 3 must still be there
    raise NotImplementedError


async def step_3_branch(mcp_client: Client) -> None:
    print_banner("STEP 3: two ways to work it out, branching from thought 1")
    # your turn: record two thoughts that both start from thought 1
    # (branch_from_thought=1), each with its own branch_id:
    #   #6 branch 'add-first':      12 + 8 = 20, then 20 - 6 = 14
    #   #7 branch 'subtract-first': 12 - 6 = 6, then 6 + 8 = 14
    #      (pass next_thought_needed=False on this last one)
    # watch branches_seen grow in the receipts
    raise NotImplementedError


async def step_4_rejection(mcp_client: Client) -> None:
    print_banner("STEP 4: the server refuses a reference to a thought that does not exist")
    # your turn: count the stored thoughts, then try to record thought 8 as a
    # revision of thought 99. Check the reply starts with "ERROR:", count
    # again, and print both counts: nothing should have been stored
    raise NotImplementedError


# ---------------------------------------------------------------------
# Step 5: a real model uses the same scratchpad
# ---------------------------------------------------------------------


def build_model_client() -> tuple[AsyncOpenAI, str]:
    if PROVIDER == "gemini":
        client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.environ["GEMINI_API_KEY"],
        )
        return client, os.environ["GEMINI_MODEL"]
    if PROVIDER == "ollama":
        return AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama"), "qwen3:4b"
    raise ValueError(f"unknown PROVIDER: {PROVIDER!r}")


async def scratchpad_schemas_for_model(mcp_client: Client) -> list[dict]:
    """Turn the server's record_thought tool into an OpenAI-format tool
    schema. get_thoughts and clear_thoughts are left out on purpose: the
    model only writes; your code does the reading and the clearing."""
    # your turn: list_tools(); for the tool named "record_thought" only,
    # build {"type": "function", "function": {"name", "description",
    # "parameters": tool.input_schema}} and return a list of those
    raise NotImplementedError


async def create_with_retry(model_client: AsyncOpenAI, model_name: str, messages: list, schemas: list):
    """One chat completion, retried when the provider says 'too many
    requests'. The wait is long enough for a per-minute quota to reset."""
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return await model_client.chat.completions.create(
                model=model_name, messages=messages, tools=schemas
            )
        except RateLimitError:
            if attempt == RATE_LIMIT_RETRIES:
                raise
            print(f"    (rate limited, waiting {RATE_LIMIT_WAIT_SECONDS}s, retry {attempt + 1}/{RATE_LIMIT_RETRIES})")
            await asyncio.sleep(RATE_LIMIT_WAIT_SECONDS)


async def run_tool_loop(
    model_client: AsyncOpenAI,
    model_name: str,
    messages: list,
    schemas: list,
    mcp_client: Client,
    stats: dict,
    *,
    max_steps: int = 10,
) -> str:
    """The reason-act-observe loop from Problem 03, with one tool that
    lives on the MCP server. Returns the model's final text."""
    # your turn: same loop shape as Problem 03's run_tool_loop, but:
    #   - call create_with_retry, and add 1 to stats["model_calls"] each time
    #   - no tool calls in the reply -> append the assistant text to messages
    #     and return it
    #   - otherwise append the assistant message using tc.model_dump() for
    #     every tool call (the Gemini thought_signature gotcha)
    #   - for each tool call: if the name is "record_thought", send it to the
    #     server with call_tool_as_text; any other name -> an
    #     "ERROR: unknown tool" string. Append the result as a role="tool" message
    #   - if max_steps runs out, return a short "(step budget used up)" string
    raise NotImplementedError


async def step_5_model_uses_scratchpad(mcp_client: Client) -> None:
    print_banner("STEP 5: a real model reasons on the scratchpad")
    # your turn:
    #   1. clear the scratchpad, build the model client, load the schemas
    #   2. system prompt: record ONE thought per reasoning step with
    #      record_thought, thought_number going up by one; when new
    #      information shows an earlier thought was wrong, record a REVISION
    #      (is_revision=True, revises_thought=<the wrong thought's number>);
    #      next_thought_needed=False only on the last thought; finish with
    #      one sentence ending in the number
    #   3. turn 1 user message: "Sam has 12 apples. He gives 5 to Ana, then
    #      buys a bag of 8. How many apples does Sam have?" -> run the loop
    #   4. turn 2: YOUR CODE appends the user message "Correction: Ana
    #      actually took 6 apples, not 5. How many apples does Sam have now?"
    #      to the same messages list -> run the loop again
    #   5. read the record with fetch_thoughts and print it (your code, not
    #      the model)
    #   6. ground truth in code: the last integer in the final answer
    #      (re.findall) equals EXPECTED_ANSWER_AFTER_CORRECTION, and at least
    #      one stored thought has is_revision True; print both, and the
    #      number of model calls
    raise NotImplementedError


async def main() -> None:
    async with Client(SERVER_URL) as mcp_client:
        await clear_scratchpad(mcp_client)
        await step_1_store_and_read(mcp_client)
        await step_2_revise(mcp_client)
        await step_3_branch(mcp_client)
        await step_4_rejection(mcp_client)

        if RUN_MODEL_STEP:
            await step_5_model_uses_scratchpad(mcp_client)
        else:
            print("\n(RUN_MODEL_STEP is False: skipping step 5, the real model call)")


if __name__ == "__main__":
    asyncio.run(main())
