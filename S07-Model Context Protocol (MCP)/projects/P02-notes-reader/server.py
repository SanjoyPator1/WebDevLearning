# ============================================================
#  P02 — Notes Reader Server
#
#  What this server does:
#    - Exposes a dynamic list of Resources: all .md files in the notes/ directory
#    - Exposes 1 tool: search_notes to find text within those notes.
#
#  This project teaches:
#    - [x] Dynamic resource generation based on local files
#    - [x] Implementing both list_resources and read_resource handlers
#    - [x] Path traversal security checks
#    - [x] Building a tool that interacts with the filesystem
# ============================================================

import asyncio
import sys
import re
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    ReadResourceResult,
    TextResourceContents,
    Tool,
    CallToolResult,
    TextContent
)

# ── 1. Configuration ────────────────────────────────────────
# We point this to the notes directory we created earlier.
# This assumes the server runs in the P02 folder.
# Resolving it makes it an absolute path to avoid cwd issues.
BASE_DIR = Path(__file__).parent.parent.parent
NOTES_DIR = (BASE_DIR / "notes").resolve()

app = Server("notes-reader-server")


# ── 2. Helper Functions ─────────────────────────────────────
def is_safe_path(target_path: Path) -> bool:
    """
    Security check to prevent Directory Traversal attacks.
    Ensures that the resolved target_path is strictly inside NOTES_DIR.
    """
    try:
        resolved_target = target_path.resolve(strict=False)
        return str(resolved_target).startswith(str(NOTES_DIR))
    except Exception:
        return False


# ── 3. Resources Handlers ───────────────────────────────────
#
# List resources returns metadata for all .md files.
#
@app.list_resources()
async def list_resources() -> list[Resource]:
    resources = []
    
    if not NOTES_DIR.exists() or not NOTES_DIR.is_dir():
        print(f"Warning: Notes directory not found at {NOTES_DIR}", file=sys.stderr)
        return resources

    # Iterate over all .md files in the directory
    for file_path in sorted(NOTES_DIR.glob("*.md")):
        # We use a custom URI scheme: notes://<filename>
        uri = f"notes://{file_path.name}"
        
        resources.append(
            Resource(
                uri=uri,
                name=file_path.stem.replace("-", " ").title(),
                description=f"Local markdown note: {file_path.name}",
                mimeType="text/markdown",
            )
        )
        
    return resources


#
# Read resource returns the actual content of the requested URI.
#
@app.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    # 1. Validate the URI scheme
    if not uri.startswith("notes://"):
        raise ValueError(f"Unsupported URI scheme: {uri}")
        
    filename = uri[len("notes://"):]
    file_path = NOTES_DIR / filename
    
    # 2. Security Check!
    if not is_safe_path(file_path):
        raise ValueError("Access Denied: Path traversal detected.")
        
    # 3. Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"Note not found: {filename}")
        
    # 4. Read content
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Error reading file {filename}: {e}")
        
    return ReadResourceResult(
        contents=[
            TextResourceContents(
                uri=uri,
                mimeType="text/markdown",
                text=content
            )
        ]
    )


# ── 4. Tools Handlers ───────────────────────────────────────
#
# We add a tool so Claude can search across all notes at once
# without having to read them all individually.
#
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_notes",
            description=(
                "Search for a keyword or regex pattern across all markdown notes. "
                "Returns a list of matching lines with their filenames. "
                "Use this to find specific topics or concepts mentioned in the notes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The text or regex pattern to search for",
                    },
                    "ignore_case": {
                        "type": "boolean",
                        "description": "Whether to ignore case (default true)",
                        "default": True
                    }
                },
                "required": ["query"],
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name != "search_notes":
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True
        )
        
    query = arguments.get("query", "")
    ignore_case = arguments.get("ignore_case", True)
    
    if not query:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: search query cannot be empty")],
            isError=True
        )
        
    if not NOTES_DIR.exists() or not NOTES_DIR.is_dir():
        return CallToolResult(
            content=[TextContent(type="text", text="Error: Notes directory not found.")],
            isError=True
        )

    try:
        flags = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(query, flags)
    except re.error as e:
         return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Invalid regex pattern '{query}': {e}")],
            isError=True
        )

    results = []
    # Search through all .md files
    for file_path in sorted(NOTES_DIR.glob("*.md")):
        try:
            content = file_path.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), start=1):
                if pattern.search(line):
                    results.append(f"[{file_path.name}:{line_num}] {line.strip()}")
        except Exception as e:
            print(f"Error reading {file_path.name} for search: {e}", file=sys.stderr)

    if not results:
        output = f"No matches found for '{query}'."
    else:
        # Limit results to avoid massive context consumption
        max_results = 100
        output = "\n".join(results[:max_results])
        if len(results) > max_results:
            output += f"\n\n... and {len(results) - max_results} more matches."

    return CallToolResult(content=[TextContent(type="text", text=output)])


# ── 5. Run Server ───────────────────────────────────────────
async def main():
    print(f"Notes Reader server starting. Watching: {NOTES_DIR}", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())
