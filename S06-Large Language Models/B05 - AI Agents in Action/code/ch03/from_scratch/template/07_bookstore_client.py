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


async def walk_all_pages(mcp_client: Client, genre: str) -> list[dict]:
    """Walk every page for a genre by hand, following next_cursor until it is null."""
    # your turn
    raise NotImplementedError


async def main() -> None:
    print(f"[client] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        print("PART 1: walking pages by hand")
        # your turn: call walk_all_pages, print the total

        print("\nPART 2: client-side cache")
        # your turn: call list_tools() three times with time.perf_counter()
        # around each, then once more with cache_mode="bypass" -- print each
        # duration

        print("\nPART 3: the model pages on its own")
        # your turn: build tool schemas from list_tools(), then run a normal
        # tool loop asking "How many sci-fi books under 250 pages do you
        # have? List them." -- let the model call search_books repeatedly
        raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
