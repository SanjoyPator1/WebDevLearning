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
    # your turn: build the arguments dict (thought, thought_number,
    # total_thoughts=7, next_thought_needed, plus **extra_fields), call
    # record_thought through call_tool_as_text, print the thought and the
    # receipt, and return the reply text
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
    # your turn: call get_thoughts and return the "thoughts" list from the
    # result's structured_content
    result = await mcp_client.call_tool("get_thoughts", {})
    return result.structured_content["thoughts"]


def print_thought_record(thoughts: list[dict]) -> None:
    """Print the notebook in order: a revision is marked with the thought it
    corrects, a branch thought with its branch name and starting point."""
    # your turn: sort by thought_number; print "#N text" for a plain thought,
    # "#N [revises #M] text" (indented) for a revision, and
    # "#N (branch 'name', from #M) text" (indented) for a branch thought
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
    # your turn: record three plain thoughts with record():
    #   #1 Sam starts with 12 apples.
    #   #2 Sam gives 5 apples to Ana: 12 - 5 = 7.
    #   #3 Sam buys a bag of 8: 7 + 8 = 15.
    # then print the notebook with fetch_thoughts + print_thought_record
    print_banner("STEP 1: store three thoughts, then read them back")
    await record(mcp_client, 1, f"Sam starts with {STARTING_APPLES} apples.")
    await record(mcp_client, 2, "Sam gives 5 apples to Ana: 12 - 5 = 7.")
    await record(mcp_client, 3, "Sam buys a bag of 8: 7 + 8 = 15.")
    print("\n  read back with get_thoughts:")
    print_thought_record(await fetch_thoughts(mcp_client))


async def step_2_revise(mcp_client: Client) -> None:
    print_banner("STEP 2: a correction arrives -- revise, do not overwrite")
    # your turn: print the new fact (Ana actually took 6, not 5), then record
    #   #4 revising thought 2 (is_revision=True, revises_thought=2): 12 - 6 = 6
    #   #5 revising thought 3: 6 + 8 = 14
    # and print the notebook again: thoughts 2 and 3 must still be there
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
    # your turn: record two thoughts that both start from thought 1
    # (branch_from_thought=1), each with its own branch_id:
    #   #6 branch 'add-first':      12 + 8 = 20, then 20 - 6 = 14
    #   #7 branch 'subtract-first': 12 - 6 = 6, then 6 + 8 = 14
    #      (pass next_thought_needed=False on this last one)
    # watch branches_seen grow in the receipts
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
    # your turn: count the stored thoughts, then try to record thought 8 as a
    # revision of thought 99. Check the reply starts with "ERROR:", count
    # again, and print both counts: nothing should have been stored
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
    # your turn: list_tools(); for the tool named "record_thought" only,
    # build {"type": "function", "function": {"name", "description",
    # "parameters": tool.input_schema}} and return a list of those
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


# TERMINAL OUTPUT
#  python 09_scratchpad_agent.py 

# ------------------------------------------------------------
# STEP 1: store three thoughts, then read them back
# ------------------------------------------------------------

# ------------------------------------------------------------
# STEP 1: store three thoughts, then read them back
# ------------------------------------------------------------
#   #1: Sam starts with 12 apples.
#       receipt: {"thought_number": 1, "total_thoughts": 7, "thoughts_so_far": 1, "branches_seen": [], "next_thought_needed": true}
#   #2: Sam gives 5 apples to Ana: 12 - 5 = 7.
#       receipt: {"thought_number": 2, "total_thoughts": 7, "thoughts_so_far": 2, "branches_seen": [], "next_thought_needed": true}
#   #3: Sam buys a bag of 8: 7 + 8 = 15.
#       receipt: {"thought_number": 3, "total_thoughts": 7, "thoughts_so_far": 3, "branches_seen": [], "next_thought_needed": true}

#   read back with get_thoughts:
#   #1 Sam starts with 12 apples.
#   #2 Sam gives 5 apples to Ana: 12 - 5 = 7.
#   #3 Sam buys a bag of 8: 7 + 8 = 15.

# ------------------------------------------------------------
# STEP 2: a correction arrives -- revise, do not overwrite
# ------------------------------------------------------------

# ------------------------------------------------------------
# STEP 2: a correction arrives -- revise, do not overwrite
# ------------------------------------------------------------
#   New fact: Ana actually took 6 apples, not 5.

#   #4: Correction: Ana took 6, not 5, so thought 2 is wrong: 12 - 6 = 6.
#       receipt: {"thought_number": 4, "total_thoughts": 7, "thoughts_so_far": 4, "branches_seen": [], "next_thought_needed": true}
#   #5: That also changes thought 3: 6 + 8 = 14.
#       receipt: {"thought_number": 5, "total_thoughts": 7, "thoughts_so_far": 5, "branches_seen": [], "next_thought_needed": true}

#   the record now (thoughts 2 and 3 are still there):
#   #1 Sam starts with 12 apples.
#   #2 Sam gives 5 apples to Ana: 12 - 5 = 7.
#   #3 Sam buys a bag of 8: 7 + 8 = 15.
#       #4 [revises #2] Correction: Ana took 6, not 5, so thought 2 is wrong: 12 - 6 = 6.
#       #5 [revises #3] That also changes thought 3: 6 + 8 = 14.

# ------------------------------------------------------------
# STEP 3: two ways to work it out, branching from thought 1
# ------------------------------------------------------------

# ------------------------------------------------------------
# STEP 3: two ways to work it out, branching from thought 1
# ------------------------------------------------------------
#   #6: Add first: 12 + 8 = 20, then 20 - 6 = 14.
#       receipt: {"thought_number": 6, "total_thoughts": 7, "thoughts_so_far": 6, "branches_seen": ["add-first"], "next_thought_needed": true}
#   #7: Subtract first: 12 - 6 = 6, then 6 + 8 = 14.
#       receipt: {"thought_number": 7, "total_thoughts": 7, "thoughts_so_far": 7, "branches_seen": ["add-first", "subtract-first"], "next_thought_needed": false}

#   Note branches_seen in the receipts above: it grows as new branch names appear.

# ------------------------------------------------------------
# STEP 4: the server refuses a reference to a thought that does not exist
# ------------------------------------------------------------

# ------------------------------------------------------------
# STEP 4: the server refuses a reference to a thought that does not exist
# ------------------------------------------------------------
#   thoughts stored before: 7

#   #8: Revising a thought that was never recorded.
#       receipt: ERROR: Error executing tool record_thought: revises_thought=99 does not exist yet on the scratchpad

#   thoughts stored after: 7  (unchanged: rejected before anything was stored)
#   The ERROR text above is exactly what a model would read, and it names the bad number.

# ------------------------------------------------------------
# STEP 5: a real model reasons on the scratchpad
# ------------------------------------------------------------
#   tools the model sees: ['record_thought']

#   --- turn 1: the original story ---
#   tool call: record_thought({'thought': 'Sam starts with 12 apples. He gives 5 to Ana, so he has 12 - 5 = 7 apples left. Then he buys a bag of 8 apples, so he now has 7 + 8 = 15 apples.', 'total_thoughts': 2, 'next_thought_needed': True, 'thought_number': 1})
#   tool result: {"thought_number": 1, "total_thoughts": 2, "thoughts_so_far": 1, "branches_seen": [], "next_thought_needed": true}
#   tool call: record_thought({'thought_number': 2, 'thought': 'The final calculation is 12 - 5 + 8 = 15. Sam has 15 apples.', 'next_thought_needed': False, 'total_thoughts': 2})
#   tool result: {"thought_number": 2, "total_thoughts": 2, "thoughts_so_far": 2, "branches_seen": [], "next_thought_needed": false}
#   model's answer: Sam has 15 apples.

#   --- turn 2: your code injects a correction ---
#   tool call: record_thought({'thought_number': 1, 'thought': 'Sam starts with 12 apples. He gives 6 to Ana, so he has 12 - 6 = 6 apples left. Then he buys a bag of 8, making it 6 + 8 = 14 apples.', 'total_thoughts': 2, 'next_thought_needed': True})
#   tool result: {"thought_number": 1, "total_thoughts": 2, "thoughts_so_far": 3, "branches_seen": [], "next_thought_needed": true}
#   tool call: record_thought({'total_thoughts': 2, 'thought_number': 2, 'next_thought_needed': False, 'thought': 'The updated calculation is 12 - 6 + 8 = 14. Sam has 14 apples.'})
#   tool result: {"thought_number": 2, "total_thoughts": 2, "thoughts_so_far": 4, "branches_seen": [], "next_thought_needed": false}
#   model's answer: Sam has 14 apples.

#   THE RECORD (read from the server by your code, not by the model)
#   #1 Sam starts with 12 apples. He gives 5 to Ana, so he has 12 - 5 = 7 apples left. Then he buys a bag of 8 apples, so he now has7 + 8 = 15 apples.
#   #1 Sam starts with 12 apples. He gives 6 to Ana, so he has 12 - 6 = 6 apples left. Then he buys a bag of 8, making it 6 + 8 = 14apples.
#   #2 The final calculation is 12 - 5 + 8 = 15. Sam has 15 apples.
#   #2 The updated calculation is 12 - 6 + 8 = 14. Sam has 14 apples.

#   GROUND TRUTH (checked in code, not by asking the model)
#     expected answer after the correction: 14
#     model's final number:                 14  -> CORRECT
#     a revision was recorded:              False
#     model calls made:                     6
