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
    would see: an 'ERROR: ...' string on failure, the structured JSON when
    the tool returns one, otherwise the plain text."""
    result = await mcp_client.call_tool(name, arguments)
    if result.is_error:
        return "ERROR: " + result.content[0].text
    if result.structured_content is not None:
        return json.dumps(result.structured_content)
    return "\n".join(block.text for block in result.content)


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
    arguments = {
        "thought": thought,
        "thought_number": thought_number,
        "total_thoughts": 7,
        "next_thought_needed": next_thought_needed,
        **extra_fields,
    }
    reply = await call_tool_as_text(mcp_client, "record_thought", arguments)
    print(f"  #{thought_number}: {thought}")
    print(f"      receipt: {reply}")
    return reply


async def fetch_thoughts(mcp_client: Client) -> list[dict]:
    result = await mcp_client.call_tool("get_thoughts", {})
    return result.structured_content["thoughts"]


def print_thought_record(thoughts: list[dict]) -> None:
    """Print the notebook in order: a revision is marked with the thought it
    corrects, a branch thought with its branch name and starting point."""
    for entry in sorted(thoughts, key=lambda stored: stored["thought_number"]):
        number = entry["thought_number"]
        if entry["is_revision"]:
            print(f"      #{number} [revises #{entry['revises_thought']}] {entry['thought']}")
        elif entry["branch_id"]:
            print(f"      #{number} (branch {entry['branch_id']!r}, from #{entry['branch_from_thought']}) {entry['thought']}")
        else:
            print(f"  #{number} {entry['thought']}")


async def clear_scratchpad(mcp_client: Client) -> None:
    await call_tool_as_text(mcp_client, "clear_thoughts", {})


# ---------------------------------------------------------------------
# Steps 1 to 4: no model, just your code talking to the server
# ---------------------------------------------------------------------


async def step_1_store_and_read(mcp_client: Client) -> None:
    print_banner("STEP 1: store three thoughts, then read them back")
    await record(mcp_client, 1, f"Sam starts with {STARTING_APPLES} apples.")
    await record(mcp_client, 2, "Sam gives 5 apples to Ana: 12 - 5 = 7.")
    await record(mcp_client, 3, "Sam buys a bag of 8: 7 + 8 = 15.")
    print("\n  read back with get_thoughts:")
    print_thought_record(await fetch_thoughts(mcp_client))


async def step_2_revise(mcp_client: Client) -> None:
    print_banner("STEP 2: a correction arrives -- revise, do not overwrite")
    print("  New fact: Ana actually took 6 apples, not 5.\n")
    await record(
        mcp_client, 4,
        "Correction: Ana took 6, not 5, so thought 2 is wrong: 12 - 6 = 6.",
        is_revision=True, revises_thought=2,
    )
    await record(
        mcp_client, 5,
        "That also changes thought 3: 6 + 8 = 14.",
        is_revision=True, revises_thought=3,
    )
    print("\n  the record now (thoughts 2 and 3 are still there):")
    print_thought_record(await fetch_thoughts(mcp_client))


async def step_3_branch(mcp_client: Client) -> None:
    print_banner("STEP 3: two ways to work it out, branching from thought 1")
    await record(
        mcp_client, 6, "Add first: 12 + 8 = 20, then 20 - 6 = 14.",
        branch_from_thought=1, branch_id="add-first",
    )
    await record(
        mcp_client, 7, "Subtract first: 12 - 6 = 6, then 6 + 8 = 14.",
        next_thought_needed=False, branch_from_thought=1, branch_id="subtract-first",
    )
    print("\n  Note branches_seen in the receipts above: it grows as new branch names appear.")


async def step_4_rejection(mcp_client: Client) -> None:
    print_banner("STEP 4: the server refuses a reference to a thought that does not exist")
    stored_before = len(await fetch_thoughts(mcp_client))
    print(f"  thoughts stored before: {stored_before}\n")

    reply = await record(
        mcp_client, 8, "Revising a thought that was never recorded.",
        is_revision=True, revises_thought=99,
    )
    assert reply.startswith("ERROR:"), "the server should have rejected thought 8"

    stored_after = len(await fetch_thoughts(mcp_client))
    print(f"\n  thoughts stored after: {stored_after}  (unchanged: rejected before anything was stored)")
    print("  The ERROR text above is exactly what a model would read, and it names the bad number.")


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
    listed = await mcp_client.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in listed.tools
        if tool.name == "record_thought"
    ]


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
    for step in range(max_steps):
        response = await create_with_retry(model_client, model_name, messages, schemas)
        stats["model_calls"] += 1
        message = response.choices[0].message

        if not message.tool_calls:
            final_text = message.content or ""
            messages.append({"role": "assistant", "content": final_text})
            return final_text

        # model_dump() keeps provider-specific fields (Gemini's thought_signature)
        messages.append({"role": "assistant", "tool_calls": [tc.model_dump() for tc in message.tool_calls]})

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"  tool call: {name}({arguments})")

            if name == "record_thought":
                result_text = await call_tool_as_text(mcp_client, name, arguments)
            else:
                result_text = f"ERROR: unknown tool {name}"

            print(f"  tool result: {result_text}")
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_text})

    return "(step budget used up before the model gave a final answer)"


async def step_5_model_uses_scratchpad(mcp_client: Client) -> None:
    print_banner("STEP 5: a real model reasons on the scratchpad")
    await clear_scratchpad(mcp_client)
    model_client, model_name = build_model_client()
    schemas = await scratchpad_schemas_for_model(mcp_client)
    print(f"  tools the model sees: {[schema['function']['name'] for schema in schemas]}")

    system_prompt = (
        "You solve small word problems. Think on the scratchpad with the "
        "record_thought tool: record one thought per reasoning step, with "
        "thought_number going up by one each time (1, 2, 3, ...). If new "
        "information shows an earlier thought was wrong, record a REVISION: "
        "is_revision=True and revises_thought=<the number of the wrong thought>. "
        "Set next_thought_needed=False only on your very last thought. When "
        "you are done, answer in one sentence that ends with the number."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Sam has 12 apples. He gives 5 to Ana, then buys a bag of 8. How many apples does Sam have?"},
    ]
    stats = {"model_calls": 0}

    print("\n  --- turn 1: the original story ---")
    answer_one = await run_tool_loop(model_client, model_name, messages, schemas, mcp_client, stats)
    print(f"  model's answer: {answer_one}")

    print("\n  --- turn 2: your code injects a correction ---")
    messages.append({"role": "user", "content": "Correction: Ana actually took 6 apples, not 5. How many apples does Sam have now?"})
    answer_two = await run_tool_loop(model_client, model_name, messages, schemas, mcp_client, stats)
    print(f"  model's answer: {answer_two}")

    print("\n  THE RECORD (read from the server by your code, not by the model)")
    thoughts = await fetch_thoughts(mcp_client)
    print_thought_record(thoughts)

    print("\n  GROUND TRUTH (checked in code, not by asking the model)")
    numbers_in_answer = re.findall(r"\d+", answer_two)
    final_number = int(numbers_in_answer[-1]) if numbers_in_answer else None
    revision_recorded = any(entry["is_revision"] for entry in thoughts)
    print(f"    expected answer after the correction: {EXPECTED_ANSWER_AFTER_CORRECTION}")
    print(f"    model's final number:                 {final_number}  -> {'CORRECT' if final_number == EXPECTED_ANSWER_AFTER_CORRECTION else 'WRONG'}")
    print(f"    a revision was recorded:              {revision_recorded}")
    print(f"    model calls made:                     {stats['model_calls']}")


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
