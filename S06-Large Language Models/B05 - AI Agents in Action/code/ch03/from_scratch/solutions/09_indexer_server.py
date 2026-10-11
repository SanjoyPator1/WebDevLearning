# Problem 09 -- a tool slow enough that it should say how far along it is,
# instead of going silent until it's done.

import asyncio
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import BaseModel

# TIPS:
# 1. ctx.report_progress takes this 3 args only

mcp = MCPServer("Indexer")


class IndexReport(BaseModel):
    files: int
    total_words: int
    largest: list[str]

@mcp.tool()
async def index_folder(folder: str, ctx: Context) -> IndexReport:
    """Walk every .txt and .md file in a folder, counting words, reporting progress as it goes."""
    # your turn: list the .txt/.md files, loop over them, await asyncio.sleep
    # for a bit per file, count words, call ctx.report_progress after each
    # one, then return the report with the 3 largest files
    
    paths = sorted(p for p in Path(folder).iterdir() if p.suffix in (".txt", ".md"))
    total_files = len(paths)
    total_words = 0

    # word counts per file e.g. [(120, "apple.md",), (512, "bridges.txt")...] 
    sizes: list[tuple[int, str]] = []

    for done, path in enumerate(paths, start=1):
        # dummy long process simulation
        await asyncio.sleep(0.3)

        # path.read_text() reads the whole file as one string, .split() 
        # breaks it into a list of words 
        words = len(path.read_text().split())
        total_words += words
        sizes.append((words, path.name))

        await ctx.report_progress(progress=done, total=total_files, message=f"indexed {path.name}")

    # tuple sort compares the first element first (words), so no key= is
    # needed here -- you'd only reach for key=lambda/itemgetter if you had
    # to sort by something NOT already in the first position, e.g. a dict,
    # or a tuple where the sort field isn't first
    sizes.sort(reverse=True)
    largest = [f"{name} ({words})" for name, words in sizes[:3]]

    return IndexReport(files=total_files, total_words=total_words, largest=largest)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8009, stateless_http=True)
