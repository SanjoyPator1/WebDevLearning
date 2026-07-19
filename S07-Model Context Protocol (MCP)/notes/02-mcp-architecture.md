# 02 — MCP Architecture

> **Phase:** Fundamentals  
> **Goal:** Understand the Client-Server model, transport layers, JSON-RPC messaging, and the full connection lifecycle.

---

## Table of Contents
1. [The Three-Layer Model: Host, Client, Server](#1-the-three-layer-model-host-client-server)
2. [Transport Layers: stdio vs HTTP+SSE](#2-transport-layers-stdio-vs-httpsse)
3. [The Underlying Protocol: JSON-RPC 2.0](#3-the-underlying-protocol-json-rpc-20)
4. [Capability Negotiation](#4-capability-negotiation)
5. [The Full Connection Lifecycle](#5-the-full-connection-lifecycle)
6. [Multi-Server Architecture](#6-multi-server-architecture)

---

## 1. The Three-Layer Model: Host, Client, Server

MCP has three distinct layers. Many beginners confuse "Host" and "Client" — here is the exact distinction:

```
MCP Component Breakdown
────────────────────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────┐
  │                   MCP HOST                          │
  │   (e.g. Claude Desktop, Cursor, your custom app)   │
  │                                                     │
  │  ┌──────────────┐   ┌──────────────┐               │
  │  │  MCP Client  │   │  MCP Client  │  ...          │
  │  │      #1      │   │      #2      │               │
  │  └──────┬───────┘   └──────┬───────┘               │
  └─────────┼─────────────────┼───────────────────────-┘
            │                 │
            │ 1:1 connection  │ 1:1 connection
            │                 │
            ▼                 ▼
  ┌──────────────────┐  ┌──────────────────┐
  │   MCP Server A   │  │   MCP Server B   │
  │ (your notes app) │  │  (GitHub tools)  │
  └──────────────────┘  └──────────────────┘
```

| Component | What it is | Examples |
|---|---|---|
| **Host** | The user-facing application | Claude Desktop, Cursor, VS Code |
| **Client** | Lives inside the Host; manages one server connection | Internal to the host app |
| **Server** | The program YOU build; exposes resources/tools/prompts | Your Python/TS script |

> **Key rule:** One Client ↔ One Server. The Host creates a new Client for every Server it connects to.

---

## 2. Transport Layers: stdio vs HTTP+SSE

MCP supports two transport mechanisms. The transport is just the "pipe" — how messages physically travel between Client and Server.

### 2.1 stdio (Standard Input/Output)
The server runs as a **local subprocess** of the Host. Messages go through the process's stdin/stdout streams.

```
stdio Transport (Local)
────────────────────────────────────────────────────────────

  MCP Host (Claude Desktop)
  │
  │  spawns as subprocess
  ├──────────────────────────────► python my_server.py
  │                                   │
  │  writes JSON-RPC to stdin ────────►│
  │                                   │ processes request
  │◄─────────── reads stdout ─────────│
  │                                   │
  │  stderr is for logs only          │ (never use stdout for logs!)
```

**When to use stdio:**
- ✅ Local development (easiest to set up)
- ✅ Servers that access local files or local databases
- ✅ Servers that should only work on the user's machine
- ❌ Cannot be shared across machines or the internet

### 2.2 HTTP + Server-Sent Events (SSE)
The server runs as an HTTP server. The Client connects via HTTP and receives streaming events via SSE.

```
HTTP+SSE Transport (Remote)
────────────────────────────────────────────────────────────

  MCP Host (anywhere)
  │
  │  HTTP POST /message ──────────────► MCP Server (remote host)
  │                                         │
  │◄── SSE stream /sse ─────────────────────│
  │   (persistent open connection)          │
  │   receives events as they come          │

  Server can be deployed on:
  └── localhost (local web server)
  └── VPS / cloud (accessible from anywhere)
  └── Railway, Render, Fly.io, etc.
```

**When to use HTTP+SSE:**
- ✅ Sharing your server with multiple users or machines
- ✅ Cloud-deployed integrations (e.g. a Slack or Notion server)
- ✅ Servers that need OAuth/authentication flows
- ❌ More complex to set up initially

### 2.3 Comparison Table

| Feature | stdio | HTTP+SSE |
|---|---|---|
| Setup complexity | Very easy | Moderate |
| Scope | Local machine only | Network-accessible |
| Authentication | Not needed (local) | Required for remote |
| Latency | Minimal (subprocess) | Network latency |
| Best for | Dev/local tools | Production/shared |
| Config field | `command` + `args` | `url` |

---

## 3. The Underlying Protocol: JSON-RPC 2.0

All MCP messages are **JSON-RPC 2.0** formatted. You don't usually write this by hand (the SDK does it), but understanding it helps you debug.

### 3.1 Request (Client → Server)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {
      "city": "London"
    }
  }
}
```

### 3.2 Response (Server → Client)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "London: 15°C, Partly Cloudy"
      }
    ]
  }
}
```

### 3.3 Error Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": "city field is required"
  }
}
```

### 3.4 Notification (Server → Client, no response expected)
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "abc123",
    "progress": 50,
    "total": 100
  }
}
```

> **Note:** Notifications have no `id` field — they are fire-and-forget.

### Key MCP Methods Reference

| Method | Direction | Purpose |
|---|---|---|
| `initialize` | Client → Server | Start the connection, exchange capabilities |
| `resources/list` | Client → Server | List available resources |
| `resources/read` | Client → Server | Read a specific resource |
| `tools/list` | Client → Server | List available tools |
| `tools/call` | Client → Server | Execute a tool |
| `prompts/list` | Client → Server | List available prompts |
| `prompts/get` | Client → Server | Get a specific prompt |
| `notifications/initialized` | Client → Server | Signal ready after init |
| `notifications/resources/updated` | Server → Client | Tell client a resource changed |

---

## 4. Capability Negotiation

When a connection opens, Client and Server **announce their capabilities** to each other via the `initialize` handshake. Neither side will attempt to use a feature the other hasn't declared support for.

### Client sends `initialize`:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "clientInfo": {
      "name": "claude-desktop",
      "version": "1.0.0"
    },
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {}
    }
  }
}
```

### Server responds with its capabilities:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "my-notes-server",
      "version": "0.1.0"
    },
    "capabilities": {
      "resources": { "subscribe": true, "listChanged": true },
      "tools": {},
      "prompts": {}
    }
  }
}
```

```
Capability Negotiation Flow
────────────────────────────────────────────────────────────

  Client                              Server
    │                                   │
    │──── initialize (with caps) ──────►│
    │                                   │ checks protocol version
    │◄─── initialize result (with caps)─│
    │                                   │
    │──── notifications/initialized ───►│
    │                                   │
    │    ✅ Connection is now READY      │
    │    Both sides know what the       │
    │    other can do.                  │
```

---

## 5. The Full Connection Lifecycle

Here is the complete lifecycle of an MCP connection from start to finish:

```
Full MCP Connection Lifecycle
────────────────────────────────────────────────────────────

  PHASE 1: STARTUP
  ─────────────────
  Host App starts
  │
  ├── Reads config file (claude_desktop_config.json)
  ├── For each server in config:
  │   └── Creates a new MCP Client
  │       └── Spawns server process (stdio) OR opens HTTP connection (SSE)
  │
  PHASE 2: INITIALIZATION
  ────────────────────────
  Client ──── initialize ──────────────────────────────► Server
  Client ◄─── initialize result ───────────────────────  Server
  Client ──── notifications/initialized ───────────────► Server

  PHASE 3: OPERATION (normal usage)
  ──────────────────────────────────
  User asks Claude a question
  │
  ├── Claude determines it needs a tool
  │   Client ──── tools/list ──────────────────────────► Server
  │   Client ◄─── list of tools ───────────────────────  Server
  │
  ├── Claude calls the tool
  │   Client ──── tools/call (name + args) ────────────► Server
  │   Client ◄─── tool result ─────────────────────────  Server
  │
  └── Claude uses result to form response to user

  PHASE 4: SHUTDOWN
  ──────────────────
  Host app closes (or server is removed from config)
  │
  ├── Client sends shutdown signal
  ├── Server cleans up (closes DB connections, etc.)
  └── Process exits / HTTP connection closes
```

---

## 6. Multi-Server Architecture

A real-world Host typically connects to **many servers at once**. Each has its own Client and they operate independently:

```
Real-World Multi-Server Setup (Claude Desktop)
────────────────────────────────────────────────────────────

  Claude Desktop (Host)
  │
  ├── Client #1 ──► Notes Server    (reads ~/notes/*.md)
  ├── Client #2 ──► GitHub Server   (lists issues, creates PRs)
  ├── Client #3 ──► Postgres Server (queries your local DB)
  └── Client #4 ──► Calendar Server (reads your Google Calendar)

  Claude sees ALL tools and resources from ALL servers
  simultaneously. It picks the right one based on context.
```

> **Important:** Servers are **isolated** from each other. Server A cannot talk to Server B — only the Host/Client orchestrates everything.

---

> **Previous Note ←** `01-introduction-to-mcp.md`  
> **Next Note →** `03-core-primitives.md` — Deep dive into Resources, Tools, and Prompts with full examples.
