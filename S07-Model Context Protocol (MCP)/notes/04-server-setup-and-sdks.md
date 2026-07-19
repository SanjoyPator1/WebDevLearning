# 04 — Server Setup & SDKs

> **Phase:** Building Your First MCP Server  
> **Goal:** Install the right SDK, scaffold a project, and get a minimal server running locally.

---

## Table of Contents
1. [Choosing Your SDK: Python vs TypeScript](#1-choosing-your-sdk-python-vs-typescript)
2. [Setting Up a Python MCP Server](#2-setting-up-a-python-mcp-server)
3. [Setting Up a TypeScript MCP Server](#3-setting-up-a-typescript-mcp-server)
4. [Recommended Project Structure](#4-recommended-project-structure)
5. [Server Initialization Concepts](#5-server-initialization-concepts)

---

## 1. Choosing Your SDK: Python vs TypeScript

Anthropic officially maintains SDKs for both. Choose based on your background:

| | Python SDK | TypeScript SDK |
|---|---|---|
| **Package** | `mcp` | `@modelcontextprotocol/sdk` |
| **Install** | `pip install mcp` or `uv add mcp` | `npm install @modelcontextprotocol/sdk` |
| **Min version** | Python 3.10+ | Node.js 18+ |
| **Best for** | Data science, ML, file processing | Web devs, API integrations |
| **Async model** | `asyncio` (`async`/`await`) | Node.js event loop (`async`/`await`) |
| **GitHub** | `modelcontextprotocol/python-sdk` | `modelcontextprotocol/typescript-sdk` |

> **Recommendation:** If you are comfortable with Python (given your ML background), start there. The concepts transfer 1:1 to TypeScript.

---

## 2. Setting Up a Python MCP Server

### 2.1 Prerequisites

```bash
# Check Python version (need 3.10+)
python3 --version

# Option A: using pip
pip install mcp

# Option B: using uv (modern, recommended — faster)
pip install uv
uv init my-mcp-server
cd my-mcp-server
uv add mcp
```

### 2.2 Minimal Server Boilerplate

Create `server.py`:

```python
# server.py — Minimal MCP Server in Python

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
import asyncio

# 1. Create the server instance with a name
app = Server("my-first-server")


# 2. Register a handler that lists available tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="say_hello",
            description="Returns a friendly greeting for the given name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the person to greet"
                    }
                },
                "required": ["name"]
            }
        )
    ]


# 3. Register a handler that executes a tool when called
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "say_hello":
        person = arguments.get("name", "World")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Hello, {person}! Welcome to MCP."
                )
            ]
        )
    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True
    )


# 4. Run the server using the stdio transport
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### 2.3 Running the Server

```bash
# Run directly
python server.py

# If using uv
uv run server.py
```

> **Note:** When you run it directly, it will appear to hang — this is correct! The server is waiting for JSON-RPC input on stdin. Use the MCP Inspector (note 09) to test it interactively.

---

## 3. Setting Up a TypeScript MCP Server

### 3.1 Prerequisites

```bash
# Check Node version (need 18+)
node --version

# Create a new project
mkdir my-mcp-server && cd my-mcp-server
npm init -y

# Install the MCP SDK
npm install @modelcontextprotocol/sdk

# Optional: TypeScript support
npm install --save-dev typescript ts-node @types/node
npx tsc --init
```

### 3.2 Minimal Server Boilerplate

Create `server.ts`:

```typescript
// server.ts — Minimal MCP Server in TypeScript

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// 1. Create the server instance with name and version
const server = new Server(
  { name: "my-first-server", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

// 2. Handle the list_tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "say_hello",
        description: "Returns a friendly greeting for the given name.",
        inputSchema: {
          type: "object",
          properties: {
            name: {
              type: "string",
              description: "The name of the person to greet",
            },
          },
          required: ["name"],
        },
      },
    ],
  };
});

// 3. Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "say_hello") {
    const name = (request.params.arguments as { name: string }).name;
    return {
      content: [{ type: "text", text: `Hello, ${name}! Welcome to MCP.` }],
    };
  }
  return {
    content: [{ type: "text", text: `Unknown tool: ${request.params.name}` }],
    isError: true,
  };
});

// 4. Start the server with stdio transport
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Use stderr for logs — NEVER stdout
  console.error("MCP Server running on stdio");
}

main().catch(console.error);
```

### 3.3 Running the TypeScript Server

```bash
# Run with ts-node (no compile step needed)
npx ts-node server.ts

# Or compile then run
npx tsc && node dist/server.js
```

---

## 4. Recommended Project Structure

```
my-mcp-server/
│
├── server.py              # main entry point
├── requirements.txt       # or pyproject.toml / package.json
│
├── tools/                 # one file per tool group
│   ├── __init__.py
│   ├── weather.py
│   └── calculator.py
│
├── resources/             # resource handlers
│   ├── __init__.py
│   └── notes.py
│
├── prompts/               # prompt templates
│   └── templates.py
│
├── tests/                 # unit tests
│   └── test_tools.py
│
└── README.md              # install & run instructions
```

---

## 5. Server Initialization Concepts

### 5.1 Declaring Capabilities

Declare upfront which primitives your server uses. If you skip a capability, the client won't request it:

```typescript
// TypeScript — explicit declaration
const server = new Server(
  { name: "my-server", version: "0.1.0" },
  {
    capabilities: {
      resources: {},   // exposes resources
      tools: {},       // exposes tools
      prompts: {},     // exposes prompts
    },
  }
);
```

```python
# Python — auto-detected from registered handlers
await app.run(read_stream, write_stream, app.create_initialization_options())
```

### 5.2 The Golden Rule: Never Print to stdout

```
stdio Transport — stdout is SACRED
────────────────────────────────────────────────────────────

  stdout  ──►  JSON-RPC messages only
               Any stray print() CORRUPTS the protocol

  stderr  ──►  Safe for all logs and debug output

  # Python — WRONG:
  print("Server started!")

  # Python — CORRECT:
  import sys
  print("Server started!", file=sys.stderr)

  # TypeScript — CORRECT:
  console.error("Server started!")
```

---

> **Previous Note ←** `03-core-primitives.md`  
> **Next Note →** `05-exposing-resources.md` — Building a server that exposes local files as resources.
