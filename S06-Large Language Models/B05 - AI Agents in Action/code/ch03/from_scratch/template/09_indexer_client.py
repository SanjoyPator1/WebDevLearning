# Problem 09 -- watch a slow tool report its own progress, and see what
# happens when the progress callback isn't async.

import asyncio
import random
from pathlib import Path

from mcp.client import Client

SERVER_URL = "http://127.0.0.1:8009/mcp"
DOCS_DIR = (Path(__file__).parent / "09_docs").resolve()

WORDS = ["apple", "bridge", "candle", "desert", "ember", "forest", "glacier", "harbor", "island", "jungle"]


def _make_docs() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    if any(DOCS_DIR.iterdir()):
        return
    random.seed(7)
    names = ["apples", "bridges", "candles", "deserts", "embers", "forests", "harbors", "islands", "rivers"]
    for name in names:
        extension = ".md" if random.random() < 0.5 else ".txt"
        word_count = random.randint(50, 550)
        text = " ".join(random.choice(WORDS) for _ in range(word_count))
        (DOCS_DIR / f"{name}{extension}").write_text(text)


async def on_progress(progress: float, total: float | None, message: str | None) -> None:
    # your turn: print a simple text progress bar
    raise NotImplementedError


async def main() -> None:
    _make_docs()
    print(f"[client] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        # your turn: call_tool("index_folder", {...}, progress_callback=on_progress),
        # print the report

        # your turn: call it again with a plain `def` callback (not async def)
        # and see what shows up in your terminal
        raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
