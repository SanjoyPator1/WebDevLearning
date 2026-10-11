# Problem 07 -- three looks at the same server: walking cursors by hand,
# watching the client's own cache, then letting a model page through
# results on its own.

import asyncio
import json
import os
import time

from dotenv import load_dotenv
from mcp.client import Client
from openai import AsyncOpenAI

load_dotenv()

llm_client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

SERVER_URL = "http://127.0.0.1:8007/mcp"


async def walk_all_pages(mcp_client: Client, genre: str) -> list[dict]:
    """Walk every page for a genre by hand, following next_cursor until it is null."""
    all_books = []
    cursor = None
    page_number = 0
    while True:
        page_number += 1
        result = await mcp_client.call_tool("search_books", {"genre": genre, "cursor": cursor})
        page = result.structured_content
        all_books.extend(page["books"])
        print(f"  page {page_number}: {len(page['books'])} books, next_cursor={page['next_cursor']}")
        cursor = page["next_cursor"]
        if cursor is None:
            break
    return all_books


async def main() -> None:
    print(f"[client] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        print("PART 1: walking pages by hand")
        all_books = await walk_all_pages(mcp_client, "sci-fi")
        print(f"  total sci-fi books: {len(all_books)}")

        print("\nPART 2: client-side cache")
        start = time.perf_counter()
        await mcp_client.list_tools()
        print(f"  list_tools #1                : {(time.perf_counter() - start) * 1000:.2f} ms   (server)")

        start = time.perf_counter()
        await mcp_client.list_tools()
        print(f"  list_tools #2                : {(time.perf_counter() - start) * 1000:.2f} ms  (cache)")

        start = time.perf_counter()
        await mcp_client.list_tools()
        print(f"  list_tools #3                : {(time.perf_counter() - start) * 1000:.2f} ms  (cache)")

        start = time.perf_counter()
        await mcp_client.list_tools(cache_mode="bypass")
        print(f"  list_tools cache_mode=bypass : {(time.perf_counter() - start) * 1000:.2f} ms   (server)")

        print("\nPART 3: the model pages on its own")
        tools = await mcp_client.list_tools()
        schemas = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.input_schema,
                },
            }
            for t in tools.tools
        ]

        messages = [
            {
                "role": "system",
                "content": "You help customers search a bookstore catalog. Use search_books to look things up.",
            },
            {
                "role": "user",
                "content": "How many sci-fi books under 250 pages do you have? List them.",
            },
        ]

        for _ in range(8):
            response = await llm_client.chat.completions.create(
                model=MODEL_NAME, messages=messages, tools=schemas
            )
            message = response.choices[0].message
            if not message.tool_calls:
                print(f"\nFINAL ANSWER\n{message.content}")
                break

            messages.append(
                {"role": "assistant", "tool_calls": [tc.model_dump() for tc in message.tool_calls]}
            )
            for tool_call in message.tool_calls:
                arguments = json.loads(tool_call.function.arguments)
                print(f"  tool call: {tool_call.function.name}({arguments})")
                result = await mcp_client.call_tool(tool_call.function.name, arguments)
                content = json.dumps(result.structured_content)
                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": content}
                )


if __name__ == "__main__":
    asyncio.run(main())
