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
    total = total or 1
    filled = int((progress / total) * 20)
    bar = "#" * filled + "." * (20 - filled)
    print(f"  [{bar}]  {int(progress)}/{int(total)}  {message}")


def on_progress_sync(progress: float, total: float | None, message: str | None) -> None:
    total = total or 1
    filled = int((progress / total) * 20)
    bar = "#" * filled + "." * (20 - filled)
    print(f"  [{bar}]  {int(progress)}/{int(total)}  {message}")


async def main() -> None:
    _make_docs()
    print(f"[client] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        file_count = len(list(DOCS_DIR.iterdir()))
        print(f"[client] indexing {DOCS_DIR.name}/ ({file_count} files)")

        result = await mcp_client.call_tool(
            "index_folder", {"folder": str(DOCS_DIR)}, progress_callback=on_progress
        )
        report = result.structured_content
        print("\nREPORT")
        print(f"  files      : {report['files']}")
        print(f"  total words: {report['total_words']}")
        print(f"  largest    : {', '.join(report['largest'])}")

        print("\n[client] now with a PLAIN (non-async) progress callback, on purpose:")
        await mcp_client.call_tool(
            "index_folder", {"folder": str(DOCS_DIR)}, progress_callback=on_progress_sync
        )
        # the bar above still prints correctly, but check your terminal for
        # "progress callback raised ... await expression" noise -- the SDK
        # awaits this callback's return value, and a plain def returns None,
        # which can't be awaited


if __name__ == "__main__":
    asyncio.run(main())
