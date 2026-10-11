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
    # your turn: list the .txt/.md files, loop over them, await asyncio.sleep
    # for a bit per file, count words, call ctx.report_progress after each
    # one, then return the report with the 3 largest files
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8009, stateless_http=True)
