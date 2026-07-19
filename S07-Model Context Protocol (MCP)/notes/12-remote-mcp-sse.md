# 12 — Remote MCP Servers with HTTP+SSE

> **Phase:** Advanced  
> **Goal:** Move from local stdio to a cloud-deployed MCP server using HTTP + Server-Sent Events transport.

---

## Table of Contents
1. [Why Go Remote?](#1-why-go-remote)
2. [What are Server-Sent Events (SSE)?](#2-what-are-server-sent-events-sse)
3. [The HTTP+SSE Message Flow](#3-the-httpsse-message-flow)
4. [Building a Remote Server in Python (FastAPI)](#4-building-a-remote-server-in-python-fastapi)
5. [Building a Remote Server in TypeScript (Express)](#5-building-a-remote-server-in-typescript-express)
6. [Deploying Your Server](#6-deploying-your-server)
7. [Connecting Claude Desktop to a Remote Server](#7-connecting-claude-desktop-to-a-remote-server)
8. [Security for Remote Servers](#8-security-for-remote-servers)
9. [The Future: Streamable HTTP](#9-the-future-streamable-http)

---

## 1. Why Go Remote?

```
stdio (local) vs HTTP+SSE (remote)
────────────────────────────────────────────────────────────

  stdio                              HTTP+SSE
  ─────────────────────────────      ─────────────────────────────────
  Runs as subprocess on your PC      Runs on a server (VPS, cloud)
  Only you can use it                Many users can connect to it
  Data stays 100% local              Data transits over network
  Zero infrastructure needed         Requires hosting + HTTPS
  No auth needed                     Auth required (tokens, OAuth)

  When to go remote:
  ├── You want to share your server with teammates
  ├── You need it accessible on multiple machines/devices
  ├── You're building a product (multi-user MCP server)
  └── You want to integrate with services that can't run locally
```

---

## 2. What are Server-Sent Events (SSE)?

SSE is a web standard for **one-way streaming** from server to client over HTTP. It's simpler than WebSockets because it's unidirectional.

```
SSE vs WebSockets
────────────────────────────────────────────────────────────

                SSE                        WebSockets
                ───────────────────────    ──────────────────────────
  Direction:    Server → Client only       Bidirectional
  Protocol:     Plain HTTP                 Separate WS protocol
  Reconnect:    Automatic                  Manual
  Complexity:   Low                        Higher
  MCP usage:    Server → Client events     Not used in MCP

  Why MCP chose SSE:
  ├── Client → Server: normal HTTP POST (simple, stateless-ish)
  └── Server → Client: SSE stream (persistent, efficient for events)
```

### SSE Message Format

```
Raw SSE Event
────────────────────────────────────────────────────────────

  HTTP Response with Content-Type: text/event-stream

  data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progress":50}}\n\n
  data: {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}\n\n

  Each event is prefixed with "data: " and followed by "\n\n"
```

---

## 3. The HTTP+SSE Message Flow

```
HTTP+SSE Full Connection Flow
────────────────────────────────────────────────────────────

  MCP Client                              MCP Server (remote)
  (Claude Desktop)                        (your FastAPI/Express app)
       │                                        │
       │── GET /sse ────────────────────────────►│
       │   (open persistent SSE connection)      │
       │◄── SSE stream open ─────────────────────│
       │   (server sends endpoint URL)           │
       │                                         │
       │── POST /message ────────────────────────►│
       │   { method: "initialize", ... }         │ processes
       │◄── SSE event: initialize result ────────│
       │                                         │
       │── POST /message ────────────────────────►│
       │   { method: "tools/list" }              │ processes
       │◄── SSE event: tools list ───────────────│
       │                                         │
       │── POST /message ────────────────────────►│
       │   { method: "tools/call", ... }         │ runs tool
       │◄── SSE event: tool result ──────────────│
       │                                         │
       │── GET /sse closed ──────────────────────►│
       │   (client disconnects)                  │ cleanup
```

The two key HTTP endpoints your server must expose:
- `GET /sse` — persistent SSE stream (server → client)
- `POST /message` — incoming JSON-RPC messages (client → server)

---

## 4. Building a Remote Server in Python (FastAPI)

```bash
# Install dependencies
pip install mcp fastapi uvicorn
```

```python
# remote_server.py — HTTP+SSE MCP server using FastAPI

import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, CallToolResult
import uvicorn

# ── MCP Server setup (same as any MCP server) ──────────────
mcp_server = Server("remote-demo-server")

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="say_hello",
            description="Returns a greeting. Use when user wants to test the server.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"}
                },
                "required": ["name"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "say_hello":
        return CallToolResult(
            content=[TextContent(type="text", text=f"Hello from remote server, {arguments['name']}!")]
        )
    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True
    )


# ── FastAPI app (handles HTTP transport) ───────────────────
app = FastAPI(title="Remote MCP Server")

# SseServerTransport bridges the HTTP layer to the MCP server
sse_transport = SseServerTransport("/message")


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint — client connects here to receive server events."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


@app.post("/message")
async def message_endpoint(request: Request):
    """Message endpoint — client POSTs JSON-RPC messages here."""
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


# ── Health check endpoint (useful for deployment) ──────────
@app.get("/health")
async def health():
    return {"status": "ok", "server": "remote-demo-server"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Run locally:**
```bash
python remote_server.py
# Server running at http://localhost:8000
# SSE endpoint: http://localhost:8000/sse
```

---

## 5. Building a Remote Server in TypeScript (Express)

```bash
# Install dependencies
npm install @modelcontextprotocol/sdk express
npm install --save-dev @types/express ts-node typescript
```

```typescript
// remote-server.ts — HTTP+SSE MCP server using Express

import express, { Request, Response } from "express";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

// ── MCP Server ─────────────────────────────────────────────
const mcp = new Server(
  { name: "remote-demo-server", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "say_hello",
      description: "Returns a greeting. Test the remote server connection.",
      inputSchema: {
        type: "object",
        properties: { name: { type: "string" } },
        required: ["name"],
      },
    },
  ],
}));

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === "say_hello") {
    const { name } = req.params.arguments as { name: string };
    return { content: [{ type: "text", text: `Hello from remote server, ${name}!` }] };
  }
  return { content: [{ type: "text", text: "Unknown tool" }], isError: true };
});


// ── Express HTTP server ────────────────────────────────────
const app = express();
const PORT = process.env.PORT || 8000;

// Store active SSE transports per connection
const transports: Map<string, SSEServerTransport> = new Map();

// SSE endpoint — client connects here
app.get("/sse", async (req: Request, res: Response) => {
  const transport = new SSEServerTransport("/message", res);
  transports.set(transport.sessionId, transport);

  res.on("close", () => {
    transports.delete(transport.sessionId);
  });

  await mcp.connect(transport);
});

// Message endpoint — client POSTs here
app.post("/message", express.json(), async (req: Request, res: Response) => {
  const sessionId = req.query.sessionId as string;
  const transport = transports.get(sessionId);

  if (!transport) {
    res.status(400).json({ error: "No active session" });
    return;
  }

  await transport.handlePostMessage(req, res);
});

// Health check
app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.listen(PORT, () => {
  console.error(`Remote MCP server listening on port ${PORT}`);
});
```

---

## 6. Deploying Your Server

### 6.1 Option A: Railway (Easiest — recommended for beginners)

```bash
# 1. Push your code to GitHub

# 2. Go to railway.app → New Project → Deploy from GitHub
#    Railway auto-detects Python/Node and deploys it

# 3. Set environment variables in Railway dashboard
#    (Settings → Variables)

# 4. Railway gives you a public URL:
#    https://your-server-name.up.railway.app
```

### 6.2 Option B: Render

```bash
# render.com → New → Web Service → connect GitHub repo
# Start command: python remote_server.py  OR  node dist/server.js
# Gets a URL: https://your-app.onrender.com
```

### 6.3 Option C: Docker (for any VPS)

```dockerfile
# Dockerfile for Python MCP server

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "remote_server.py"]
```

```bash
# Build and run locally
docker build -t my-mcp-server .
docker run -p 8000:8000 -e WEATHER_API_KEY=your_key my-mcp-server

# Push to Docker Hub / deploy to VPS
docker push yourname/my-mcp-server
```

### 6.4 requirements.txt / package.json

```text
# requirements.txt for Python
mcp
fastapi
uvicorn
```

```json
// package.json scripts for TypeScript
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/remote-server.js"
  }
}
```

---

## 7. Connecting Claude Desktop to a Remote Server

For remote servers, use the `url` field instead of `command`+`args`:

```json
// claude_desktop_config.json

{
  "mcpServers": {
    "remote-demo": {
      "url": "https://your-server.up.railway.app/sse"
    },
    "local-notes": {
      "command": "python3",
      "args": ["/path/to/local/server.py"]
    }
  }
}
```

You can mix local (stdio) and remote (HTTP+SSE) servers in the same config.

---

## 8. Security for Remote Servers

```
Remote Server Security Requirements
────────────────────────────────────────────────────────────

  ✅ Always use HTTPS in production
     └── Get a TLS cert (Railway/Render provide this automatically)
     └── Never accept connections on plain HTTP in production

  ✅ Implement authentication
     └── Bearer token validation on every request
     └── Or full OAuth 2.0 flow (see note 10)

  ✅ Add CORS if serving from browser-based clients
     └── Set appropriate Access-Control-Allow-Origin headers

  ✅ Rate limit your endpoints
     └── Prevent abuse and runaway tool calls

  ✅ Validate all inputs server-side
     └── Never trust what comes over the network
```

**Quick bearer token auth middleware (FastAPI):**

```python
from fastapi import Header, HTTPException
import os

EXPECTED_TOKEN = os.environ["MCP_AUTH_TOKEN"]

async def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ")
    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

# Use as a dependency on your endpoints:
@app.get("/sse", dependencies=[Depends(verify_token)])
async def sse_endpoint(request: Request):
    ...
```

---

## 9. The Future: Streamable HTTP

> ⚠️ **Heads up:** The MCP spec is actively evolving. The HTTP+SSE transport is being superseded by **Streamable HTTP**, which uses a single HTTP endpoint for both directions.

```
SSE (current) vs Streamable HTTP (future)
────────────────────────────────────────────────────────────

  SSE Transport (current)            Streamable HTTP (new)
  ─────────────────────────────      ─────────────────────────────────
  GET /sse   → persistent stream     POST /mcp  → single endpoint
  POST /msg  → client messages       Uses HTTP streaming both ways

  More complex (2 endpoints)         Simpler (1 endpoint)
  Widely supported now               Becoming the new standard
  Use this today                     Watch for SDK updates
```

Check the [MCP changelog](https://modelcontextprotocol.io/changelog) for when Streamable HTTP becomes stable in your SDK version.

---

> 🎉 **End of Roadmap** — You now have a complete foundation in the Model Context Protocol!

**What's next?** Head to the `projects/` folder and start building:
1. `mcp-starter/` — An echo server to solidify the basics
2. A **File Explorer Server** — expose your notes as resources (notes 04+05)
3. An **API Integration Server** — wrap a public API as a tool (notes 06+10)
4. A **Remote Server** — deploy to Railway and share with others (this note)
