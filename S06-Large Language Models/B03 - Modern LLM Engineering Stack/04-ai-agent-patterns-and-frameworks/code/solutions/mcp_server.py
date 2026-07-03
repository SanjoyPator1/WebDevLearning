"""A minimal MCP server exposing a small SQLite database of learning notes.

Run directly to start the server over stdio:

    python mcp_server.py

The notebook in this folder spawns this file as a subprocess and talks to it
over the Model Context Protocol (JSON-RPC over stdio).
"""

import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

DB_PATH = Path(__file__).parent / "learning_notes.db"

NOTES = {
    "langgraph": "LangGraph is a library for building stateful, multi-step LLM applications as graphs of nodes and edges.",
    "checkpointer": "A checkpointer persists the state of a graph after every step, identified by a thread_id.",
    "react": "The ReAct pattern interleaves reasoning (LLM thoughts) with acting (tool calls) in a loop.",
    "attention": "Self-attention lets each token in a sequence weigh and combine information from every other token.",
    "mcp": "The Model Context Protocol standardizes how LLM applications connect to external tools, data, and prompts.",
}


def init_db() -> None:
    """Create the notes table if needed and (re)seed the built-in notes."""
    connection = sqlite3.connect(DB_PATH)
    connection.execute("CREATE TABLE IF NOT EXISTS notes (topic TEXT PRIMARY KEY, content TEXT NOT NULL)")
    connection.executemany(
        "INSERT OR REPLACE INTO notes (topic, content) VALUES (?, ?)",
        list(NOTES.items()),
    )
    connection.commit()
    connection.close()


init_db()

mcp = FastMCP("learning-notes", log_level="ERROR")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
def search_notes(query: str) -> str:
    """Search the learning notes database for a topic and return its content."""
    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute("SELECT topic, content FROM notes").fetchall()
    connection.close()
    query_lower = query.lower()
    for topic, content in rows:
        if topic in query_lower:
            return content
    return "No results found."


@mcp.resource("notes://topics")
def list_topics() -> str:
    """List every topic available in the learning notes database."""
    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute("SELECT topic FROM notes ORDER BY topic").fetchall()
    connection.close()
    return ", ".join(topic for (topic,) in rows)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))
def add_note(topic: str, content: str) -> str:
    """Add or update a note in the learning notes database.

    1. Open a sqlite3 connection to DB_PATH.
    2. Run "INSERT OR REPLACE INTO notes (topic, content) VALUES (?, ?)" with
       (topic.lower(), content) as parameters, then commit and close.
    3. Return a confirmation string, e.g. f"Saved note for topic '{topic}'."
    """
    # YOUR CODE HERE
    raise NotImplementedError("add_note is not implemented yet")


if __name__ == "__main__":
    mcp.run(transport="stdio")
