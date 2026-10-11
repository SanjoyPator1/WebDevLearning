# Problem 09 -- a tool slow enough that it should say how far along it is,
# instead of going silent until it's done.

import asyncio
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import BaseModel

mcp = MCPServer("Indexer")


class IndexReport(BaseModel):
    files: int
    total_words: int
    largest: list[str]


@mcp.tool()
async def index_folder(folder: str, ctx: Context) -> IndexReport:
    """Walk every .txt and .md file in a folder, counting words, reporting progress as it goes."""
    paths = sorted(p for p in Path(folder).iterdir() if p.suffix in (".txt", ".md"))
    total_files = len(paths)
    total_words = 0
    sizes: list[tuple[str, int]] = []

    for done, path in enumerate(paths, start=1):
        await asyncio.sleep(0.3)
        words = len(path.read_text().split())
        total_words += words
        sizes.append((path.name, words))

        # done is just your own loop counter — how many files have I finished so far, right now
        # enumerate(paths, start=1) numbers each file 1, 2, 3, ... as you process it
        # total : "the whole job" means "process every file in the folder."
        # total should stay the same number across every call within one run, 
        # so the client can always compute a sensible fraction progress / total.
        await ctx.report_progress(progress=done, total=total_files, message=f"indexed {path.name}")
    # sort by the second element of each tuple
    

    sizes.sort(key=lambda item: item[1], reverse=True)
    largest = [f"{name} ({words})" for name, words in sizes[:3]]

    return IndexReport(files=total_files, total_words=total_words, largest=largest)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8009, stateless_http=True)
