# 11 — Pagination & Large Data

> **Phase:** Advanced  
> **Goal:** Handle large resource lists and oversized data gracefully using MCP's cursor-based pagination pattern.

---

## Table of Contents
1. [Why Large Data is a Problem](#1-why-large-data-is-a-problem)
2. [Cursor-Based Pagination in MCP](#2-cursor-based-pagination-in-mcp)
3. [Implementing Pagination in Python](#3-implementing-pagination-in-python)
4. [Implementing Pagination in TypeScript](#4-implementing-pagination-in-typescript)
5. [Strategies for Large Single Resources](#5-strategies-for-large-single-resources)
6. [Rate Limiting](#6-rate-limiting)
7. [Caching for Performance](#7-caching-for-performance)
8. [Performance Tips](#8-performance-tips)

---

## 1. Why Large Data is a Problem

```
The Large Data Problem
────────────────────────────────────────────────────────────

  LLM Context Window (e.g. Claude: ~200k tokens)
  ┌──────────────────────────────────────────────────────┐
  │ System prompt                          ~2k tokens    │
  │ Conversation history                  ~10k tokens    │
  │ Tool results + resource content       ~??k tokens    │ ← problem
  │ LLM response                          ~??k tokens    │
  └──────────────────────────────────────────────────────┘

  If your server returns 1000 files all at once:
  ├── Each file is ~500 tokens average
  ├── Total: 500,000 tokens — exceeds the context window!
  └── Result: error, truncation, or degraded performance

  Solutions:
  ├── Pagination: return 10-50 items at a time
  ├── Chunking: split large files into sections
  └── Summarization: summarize at the server before returning
```

---

## 2. Cursor-Based Pagination in MCP

MCP uses **cursor-based pagination** (also called keyset pagination). Instead of page numbers, you use an opaque "cursor" token that represents a position in the result set.

```
Cursor Pagination Flow
────────────────────────────────────────────────────────────

  Request 1 (no cursor = start from beginning):
  Client ──► resources/list {}
  Server ──► { resources: [item1..item10], nextCursor: "cursor_abc" }

  Request 2 (use nextCursor from previous response):
  Client ──► resources/list { cursor: "cursor_abc" }
  Server ──► { resources: [item11..item20], nextCursor: "cursor_def" }

  Request 3:
  Client ──► resources/list { cursor: "cursor_def" }
  Server ──► { resources: [item21..item25] }  ← no nextCursor = last page

  Key: if nextCursor is absent, you've reached the end.
```

### What a Cursor Actually Is

The cursor is an **opaque string** — the client never interprets it, just passes it back. Internally, you can encode anything:

```python
import base64
import json

# Simple cursor: encode the offset as base64
def make_cursor(offset: int) -> str:
    return base64.b64encode(json.dumps({"offset": offset}).encode()).decode()

def parse_cursor(cursor: str) -> int:
    data = json.loads(base64.b64decode(cursor).decode())
    return data["offset"]

# Example:
cursor = make_cursor(10)   # "eyJvZmZzZXQiOiAxMH0="
offset = parse_cursor(cursor)  # 10
```

### JSON-RPC Example

```json
// Request with cursor
{
  "method": "resources/list",
  "params": {
    "cursor": "eyJvZmZzZXQiOiAxMH0="
  }
}

// Response with nextCursor (more pages)
{
  "result": {
    "resources": [
      { "uri": "notes://note11.md", "name": "Note 11" },
      { "uri": "notes://note12.md", "name": "Note 12" }
    ],
    "nextCursor": "eyJvZmZzZXQiOiAyMH0="
  }
}

// Response without nextCursor (last page)
{
  "result": {
    "resources": [
      { "uri": "notes://note25.md", "name": "Note 25" }
    ]
  }
}
```

---

## 3. Implementing Pagination in Python

```python
# paginated_server.py — Python resource server with cursor pagination

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, ReadResourceResult, TextResourceContents

NOTES_DIR = Path.home() / "notes"
PAGE_SIZE = 10   # number of resources per page

app = Server("paginated-notes-server")


def make_cursor(offset: int) -> str:
    """Encode an offset into an opaque cursor string."""
    payload = json.dumps({"offset": offset})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def parse_cursor(cursor: str | None) -> int:
    """Decode a cursor string back to an offset. Returns 0 for no cursor."""
    if not cursor:
        return 0
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        return json.loads(payload)["offset"]
    except Exception:
        return 0   # invalid cursor → start from beginning


@app.list_resources()
async def list_resources(cursor: str | None = None) -> dict:
    """Return a paginated list of markdown files."""

    # Get ALL files, sorted consistently
    all_files = sorted(NOTES_DIR.glob("*.md")) if NOTES_DIR.exists() else []

    # Parse the cursor to get the current offset
    offset = parse_cursor(cursor)

    # Slice the result for this page
    page = all_files[offset : offset + PAGE_SIZE]

    resources = [
        Resource(
            uri=f"notes://{f.name}",
            name=f.stem.replace("-", " ").title(),
            mimeType="text/markdown",
        )
        for f in page
    ]

    # Build response — include nextCursor only if there are more items
    result = {"resources": resources}
    next_offset = offset + PAGE_SIZE
    if next_offset < len(all_files):
        result["nextCursor"] = make_cursor(next_offset)

    return result


@app.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    filename = uri.removeprefix("notes://")
    file_path = (NOTES_DIR / filename).resolve()

    if not str(file_path).startswith(str(NOTES_DIR.resolve())):
        raise ValueError("Access denied")
    if not file_path.exists():
        raise FileNotFoundError(f"Not found: {filename}")

    return ReadResourceResult(contents=[
        TextResourceContents(uri=uri, mimeType="text/markdown", text=file_path.read_text())
    ])


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. Implementing Pagination in TypeScript

```typescript
// paginated-server.ts

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ListResourcesRequestSchema, ReadResourceRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs";
import * as path from "path";

const NOTES_DIR = path.join(process.env.HOME || "~", "notes");
const PAGE_SIZE = 10;

const server = new Server(
  { name: "paginated-notes-server", version: "0.1.0" },
  { capabilities: { resources: {} } }
);

// ── Cursor helpers ─────────────────────────────────────────
function makeCursor(offset: number): string {
  return Buffer.from(JSON.stringify({ offset })).toString("base64url");
}

function parseCursor(cursor?: string): number {
  if (!cursor) return 0;
  try {
    return JSON.parse(Buffer.from(cursor, "base64url").toString()).offset;
  } catch {
    return 0;
  }
}


// ── Paginated list handler ─────────────────────────────────
server.setRequestHandler(ListResourcesRequestSchema, async (request) => {
  const cursor = request.params?.cursor as string | undefined;
  const offset = parseCursor(cursor);

  const allFiles = fs.existsSync(NOTES_DIR)
    ? fs.readdirSync(NOTES_DIR).filter((f) => f.endsWith(".md")).sort()
    : [];

  const page = allFiles.slice(offset, offset + PAGE_SIZE);

  const resources = page.map((file) => ({
    uri: `notes://${file}`,
    name: file.replace(".md", "").replace(/-/g, " "),
    mimeType: "text/markdown",
  }));

  const result: { resources: typeof resources; nextCursor?: string } = { resources };

  if (offset + PAGE_SIZE < allFiles.length) {
    result.nextCursor = makeCursor(offset + PAGE_SIZE);
  }

  return result;
});


// ── Read resource handler ──────────────────────────────────
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;
  const filename = uri.replace("notes://", "");
  const filePath = path.resolve(NOTES_DIR, filename);

  if (!filePath.startsWith(path.resolve(NOTES_DIR))) throw new Error("Access denied");
  if (!fs.existsSync(filePath)) throw new Error(`Not found: ${filename}`);

  return {
    contents: [{ uri, mimeType: "text/markdown", text: fs.readFileSync(filePath, "utf-8") }],
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Paginated server started");
}

main().catch(console.error);
```

---

## 5. Strategies for Large Single Resources

What if a single file or resource is too large for the LLM's context window?

```
Handling Large Single Resources
────────────────────────────────────────────────────────────

  Strategy 1: Chunking / Windowing
  ──────────────────────────────────
  Expose the large resource as multiple smaller resources:
  notes://bigfile.md/chunk/1    → lines 1-100
  notes://bigfile.md/chunk/2    → lines 101-200

  Strategy 2: Server-side summarization
  ───────────────────────────────────────
  Before returning a large file, summarize it:
  ├── Return the summary as the resource content
  └── Add a tool: "get_full_content(uri)" for when more detail is needed

  Strategy 3: Selective return + offer more
  ──────────────────────────────────────────
  Return only the first N lines, then append:
  "... [truncated, 3240 lines remaining. Ask for a specific section.]"
  The LLM will tell the user it can fetch more if needed.
```

**Python example — chunked resource:**

```python
CHUNK_SIZE = 100  # lines per chunk

@app.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    # URI format: notes://filename.md/chunk/2
    parts = uri.split("/chunk/")
    filename = parts[0].removeprefix("notes://")
    chunk_index = int(parts[1]) if len(parts) > 1 else 0

    lines = (NOTES_DIR / filename).read_text().splitlines()
    start = chunk_index * CHUNK_SIZE
    chunk_lines = lines[start : start + CHUNK_SIZE]
    chunk_text = "\n".join(chunk_lines)

    if start + CHUNK_SIZE < len(lines):
        chunk_text += f"\n\n[Showing lines {start+1}-{start+CHUNK_SIZE} of {len(lines)}. Next chunk: {uri.split('/chunk/')[0]}/chunk/{chunk_index+1}]"

    return ReadResourceResult(contents=[
        TextResourceContents(uri=uri, mimeType="text/markdown", text=chunk_text)
    ])
```

---

## 6. Rate Limiting

Protect your server from being overwhelmed by too many rapid tool calls:

```python
# Simple token-bucket rate limiter

import time
import asyncio

class RateLimiter:
    def __init__(self, calls_per_second: float = 2.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0.0

    async def acquire(self):
        """Wait if necessary to stay within the rate limit."""
        now = time.monotonic()
        elapsed = now - self.last_call_time
        wait_time = self.min_interval - elapsed

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        self.last_call_time = time.monotonic()

# Usage in your tool handler:
rate_limiter = RateLimiter(calls_per_second=2)  # max 2 calls/sec

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    await rate_limiter.acquire()  # blocks if going too fast
    # ... tool logic
```

---

## 7. Caching for Performance

Cache expensive results to avoid redundant API calls or file reads:

```python
import time
from functools import lru_cache

# Simple time-based cache
_cache: dict[str, tuple[float, any]] = {}
CACHE_TTL_SECONDS = 60  # cache results for 60 seconds

def get_cached(key: str):
    if key in _cache:
        timestamp, value = _cache[key]
        if time.monotonic() - timestamp < CACHE_TTL_SECONDS:
            return value
    return None

def set_cached(key: str, value: any):
    _cache[key] = (time.monotonic(), value)

# Usage in a tool handler:
async def handle_get_weather(arguments: dict):
    city = arguments["city"]
    cache_key = f"weather:{city}"

    # Check cache first
    cached = get_cached(cache_key)
    if cached:
        return CallToolResult(content=[TextContent(type="text", text=cached)])

    # Fetch from API (expensive)
    result = await fetch_weather_from_api(city)

    # Store in cache
    set_cached(cache_key, result)
    return CallToolResult(content=[TextContent(type="text", text=result)])
```

---

## 8. Performance Tips

| Tip | Benefit |
|---|---|
| Use `PAGE_SIZE = 20-50` for resource lists | Good balance between UX and context usage |
| Cache API responses for 30-120 seconds | Reduces API calls, avoids rate limits |
| Use async I/O (`aiofiles`, `aiohttp`) | Non-blocking — server stays responsive |
| Run sync code in a thread pool | `await asyncio.to_thread(sync_fn)` |
| Validate inputs before expensive operations | Fail fast before API calls |
| Set timeouts on all HTTP requests | Prevent tools from hanging indefinitely |
| Return summaries, not full raw data | Keeps context window usage low |

---

> **Previous Note ←** `10-handling-authentication.md`  
> **Next Note →** `12-remote-mcp-sse.md` — Deploying your MCP server to the cloud with HTTP+SSE transport.
