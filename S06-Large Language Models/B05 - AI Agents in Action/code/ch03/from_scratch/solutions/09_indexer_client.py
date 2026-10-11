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

# on_progress works and on_progress_sync doesnot work
# here progress is the done that we get from the server

async def on_progress(progress: float, total: float | None, message: str | None) -> None:
    # your turn: print a simple text progress bar
    total = total or 1
    filled = int((progress / total) * 20)
    bar = ('#' * filled) + ("." * (20 - filled))
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
        # your turn: call_tool("index_folder", {...}, progress_callback=on_progress),
        # print the report
        file_count = len(list(DOCS_DIR.iterdir()))
        print(f"[client] indexing {DOCS_DIR.name}/ ({file_count} files)")

        result = await mcp_client.call_tool(
            "index_folder" , {"folder" : str(DOCS_DIR)}, progress_callback=on_progress
        )

        report = result.structured_content
        print("\nREPORT")
        print(f"  files      : {report['files']}")
        print(f"  total words: {report['total_words']}")
        print(f"  largest    : {', '.join(report['largest'])}")

        # your turn: call it again with a plain `def` callback (not async def)
        # and see what shows up in your terminal
        print("\n[client] now with a PLAIN (non-async) progress callback, on purpose:")
        await mcp_client.call_tool(
            "index_folder", {"folder": str(DOCS_DIR)}, progress_callback=on_progress_sync
        )


if __name__ == "__main__":
    asyncio.run(main())

# python 09_indexer_client.py 
# [client] connecting to http://127.0.0.1:8009/mcp
# [client] indexing 09_docs/ (9 files)
#   [##..................]  1/9  indexed apples.md
#   [####................]  2/9  indexed bridges.md
#   [######..............]  3/9  indexed candles.txt
#   [########............]  4/9  indexed deserts.md
#   [###########.........]  5/9  indexed embers.md
#   [#############.......]  6/9  indexed forests.txt
#   [###############.....]  7/9  indexed harbors.txt
#   [#################...]  8/9  indexed islands.txt
#   [####################]  9/9  indexed rivers.md

# REPORT
#   files      : 9
#   total words: 2426
#   largest    : 539 (candles.txt), 450 (forests.txt), 427 (embers.md)

# [client] now with a PLAIN (non-async) progress callback, on purpose:
#   [##..................]  1/9  indexed apples.md
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [####................]  2/9  indexed bridges.md
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [######..............]  3/9  indexed candles.txt
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [########............]  4/9  indexed deserts.md
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [###########.........]  5/9  indexed embers.md
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [#############.......]  6/9  indexed forests.txt
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [###############.....]  7/9  indexed harbors.txt
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [#################...]  8/9  indexed islands.txt
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
#   [####################]  9/9  indexed rivers.md
# progress callback raised
# Traceback (most recent call last):
#   File "/Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
#     await fn(progress, total, message)
# TypeError: object NoneType can't be used in 'await' expression
