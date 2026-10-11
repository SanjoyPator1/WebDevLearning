# Problem 07 -- walking cursors by hand, watching the client's own cache,
# then letting a model page through results on its own.

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

# TIPS:
# 1. for this file mainly remember to have prompts like send cursor if any and 
# actually get the current cursor from response and send it over to mcp for next set of results
# and at the end when the cursor is none that means we did iterated through all the items in the lisr
# but i guess this is true for only this problem but in production or any other app
# the llm will decide to search through maybe with search names, sorting and filtering
# and then use cursor to iterate through items to check more results till 
# they get the item or exhaust or end the iteration i.e. go till end

async def walk_all_pages(mcp_client: Client, genre: str) -> list[dict]:
    """Walk every page for a genre by hand, following next_cursor until it is null."""
    # your turn
    
    all_books = []
    cursor = None
    page_number = 0

    while True:
        page_number += 1
        result = await mcp_client.call_tool("search_books", {"genre" : genre, "cursor" : cursor})

        page = result.structured_content
        all_books.extend(page["books"])
        print(f"  page {page_number}: {len(page['books'])} books, next_cursor={page['next_cursor']}")
        cursor = page["next_cursor"]

        # if the cursor is end - we reached the end
        if cursor is None:
            break

    return all_books



async def main() -> None:
    print(f"[client] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        print("PART 1: walking pages by hand")
        # your turn: call walk_all_pages, print the total
        all_books = await walk_all_pages(mcp_client, "sci-fi")
        print(f"  total sci-fi books: {len(all_books)}")

        print("\nPART 2: client-side cache")
        # your turn: call list_tools() three times with time.perf_counter()
        # around each, then once more with cache_mode="bypass" -- print each
        # duration
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
        # your turn: build tool schemas from list_tools(), then run a normal
        # tool loop asking "How many sci-fi books under 250 pages do you
        # have? List them." -- let the model call search_books repeatedly
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

        # tool loop
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

        print("----- messages at the end -------")
        print(json.dumps(messages, indent=4))
        
if __name__ == "__main__":
    asyncio.run(main())

# TERMINAL OUTPUT LOGS

# python 07_bookstore_client.py 
# [client] connecting to http://127.0.0.1:8007/mcp
# PART 1: walking pages by hand
#   page 1: 10 books, next_cursor=eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMTB9
#   page 2: 10 books, next_cursor=eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMjB9
#   page 3: 10 books, next_cursor=eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMzB9
#   page 4: 10 books, next_cursor=None
#   total sci-fi books: 40

# PART 2: client-side cache
#   list_tools #1                : 1.28 ms   (server)
#   list_tools #2                : 0.09 ms  (cache)
#   list_tools #3                : 0.09 ms  (cache)
#   list_tools cache_mode=bypass : 1.15 ms   (server)

# PART 3: the model pages on its own
#   tool call: search_books({'genre': 'sci-fi'})
#   tool call: search_books({'genre': 'sci-fi', 'cursor': 'eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMTB9'})
#   tool call: search_books({'genre': 'sci-fi', 'cursor': 'eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMjB9'})
#   tool call: search_books({'genre': 'sci-fi', 'cursor': 'eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMzB9'})

# FINAL ANSWER
# We have **16** sci-fi books under 250 pages. Here they are:

# 1. **Book 005** (245 pages)
# 2. **Book 020** (239 pages)
# 3. **Book 025** (221 pages)
# 4. **Book 035** (123 pages)
# 5. **Book 045** (167 pages)
# 6. **Book 065** (218 pages)
# 7. **Book 070** (236 pages)
# 8. **Book 080** (203 pages)
# 9. **Book 095** (245 pages)
# 10. **Book 125** (191 pages)
# 11. **Book 135** (232 pages)
# 12. **Book 140** (144 pages)
# 13. **Book 165** (177 pages)
# 14. **Book 170** (121 pages)
# 15. **Book 175** (211 pages)
# ----- messages at the end -------
# [
#     {
#         "role": "system",
#         "content": "You help customers search a bookstore catalog. Use search_books to look things up."
#     },
#     {
#         "role": "user",
#         "content": "How many sci-fi books under 250 pages do you have? List them."
#     },
#     {
#         "role": "assistant",
#         "tool_calls": [
#             {
#                 "id": "call_1039904",
#                 "function": {
#                     "arguments": "{\"genre\":\"sci-fi\"}",
#                     "name": "search_books"
#                 },
#                 "type": "function",
#                 "extra_content": {
#                     "google": {
#                         "thought_signature": "EmAKXgFpFH0T/Hp6dmhfQV4gxwzM4yHgRWprHk9EZYnFs2QYHeNpLV3KAOHciG5rr4bZoKBxnGuG/xhxpsd4xxxRY2f11MZYQgAK1xa4faJKgesxLEgXGC7FM2cT1pGLhys="
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_1039904",
#         "content": "{\"books\": [{\"title\": \"Book 000\", \"pages\": 447}, {\"title\": \"Book 005\", \"pages\": 245}, {\"title\": \"Book 010\", \"pages\": 466}, {\"title\": \"Book 015\", \"pages\": 336}, {\"title\": \"Book 020\", \"pages\": 239}, {\"title\": \"Book 025\", \"pages\": 221}, {\"title\": \"Book 030\", \"pages\": 334}, {\"title\": \"Book 035\", \"pages\": 123}, {\"title\": \"Book040\", \"pages\": 262}, {\"title\": \"Book 045\", \"pages\": 167}], \"next_cursor\": \"eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMTB9\"}"
#     },
#     {
#         "role": "assistant",
#         "tool_calls": [
#             {
#                 "id": "call_1038353",
#                 "function": {
#                     "arguments": "{\"genre\":\"sci-fi\",\"cursor\":\"eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMTB9\"}",
#                     "name": "search_books"
#                 },
#                 "type": "function",
#                 "extra_content": {
#                     "google": {
#                         "thought_signature": "EmAKXgFpFH0TodevemfWN1G9K97mhqDMCWeSwTJeZTOm0dzeMko3xc2Niw2bHtGMmvjbAOCYZ+3R9WHM6wyhmhPQDXH1QaIo/fBsAT3fNuSb9qJGWO76IU+T8Lq5DasrReA="
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_1038353",
#         "content": "{\"books\": [{\"title\": \"Book 050\", \"pages\": 429}, {\"title\": \"Book 055\", \"pages\": 394}, {\"title\": \"Book 060\", \"pages\": 270}, {\"title\": \"Book 065\", \"pages\": 218}, {\"title\": \"Book 070\", \"pages\": 236}, {\"title\": \"Book 075\", \"pages\": 314}, {\"title\": \"Book 080\", \"pages\": 203}, {\"title\": \"Book 085\", \"pages\": 256}, {\"title\": \"Book090\", \"pages\": 431}, {\"title\": \"Book 095\", \"pages\": 245}], \"next_cursor\": \"eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMjB9\"}"
#     },
#     {
#         "role": "assistant",
#         "tool_calls": [
#             {
#                 "id": "call_1319352",
#                 "function": {
#                     "arguments": "{\"genre\":\"sci-fi\",\"cursor\":\"eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMjB9\"}",
#                     "name": "search_books"
#                 },
#                 "type": "function",
#                 "extra_content": {
#                     "google": {
#                         "thought_signature": "EmAKXgFpFH0Tuk3l8HjsNsj+hbPxG+uoX2OP9zC0V1Kh/Q2HdyMS5JtigQESTw6vKFyjsa6/virxKhgeufGzbPuxsEuwhqxZg8F5a3xeuWnnUhSfMQz/ppUtwyGfs+eNJTU="
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_1319352",
#         "content": "{\"books\": [{\"title\": \"Book 100\", \"pages\": 447}, {\"title\": \"Book 105\", \"pages\": 286}, {\"title\": \"Book 110\", \"pages\": 325}, {\"title\": \"Book 115\", \"pages\": 487}, {\"title\": \"Book 120\", \"pages\": 322}, {\"title\": \"Book 125\", \"pages\": 191}, {\"title\": \"Book 130\", \"pages\": 419}, {\"title\": \"Book 135\", \"pages\": 232}, {\"title\": \"Book140\", \"pages\": 144}, {\"title\": \"Book 145\", \"pages\": 468}], \"next_cursor\": \"eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMzB9\"}"
#     },
#     {
#         "role": "assistant",
#         "tool_calls": [
#             {
#                 "id": "call_1028435",
#                 "function": {
#                     "arguments": "{\"genre\":\"sci-fi\",\"cursor\":\"eyJnZW5yZSI6ICJzY2ktZmkiLCAib2Zmc2V0IjogMzB9\"}",
#                     "name": "search_books"
#                 },
#                 "type": "function",
#                 "extra_content": {
#                     "google": {
#                         "thought_signature": "EmAKXgFpFH0TSDe6VquTePjpWThIuQDT/hhadUOzJVBICrE5PRSSyMLFdsre1+d9fYDHJMXV0NnXpsvqvmVw4Er3Wli6CzOa94XiY9EKS8Ub60/HL3bSNmKaVtZ4mQxBOdk="
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_1028435",
#         "content": "{\"books\": [{\"title\": \"Book 150\", \"pages\": 315}, {\"title\": \"Book 155\", \"pages\": 403}, {\"title\": \"Book 160\", \"pages\": 469}, {\"title\": \"Book 165\", \"pages\": 177}, {\"title\": \"Book 170\", \"pages\": 121}, {\"title\": \"Book 175\", \"pages\": 211}, {\"title\": \"Book 180\", \"pages\": 447}, {\"title\": \"Book 185\", \"pages\": 311}, {\"title\": \"Book190\", \"pages\": 426}, {\"title\": \"Book 195\", \"pages\": 305}], \"next_cursor\": null}"
#     }
# ]