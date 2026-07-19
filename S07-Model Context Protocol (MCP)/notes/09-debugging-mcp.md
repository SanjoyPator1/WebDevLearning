# 09 — Debugging MCP Servers

> **Phase:** Integration  
> **Goal:** Master every debugging tool and technique to diagnose any MCP issue quickly.

---

## Table of Contents
1. [Debugging Overview](#1-debugging-overview)
2. [The MCP Inspector](#2-the-mcp-inspector)
3. [Logging Best Practices](#3-logging-best-practices)
4. [Reading Claude Desktop Logs](#4-reading-claude-desktop-logs)
5. [Common Errors & Fixes](#5-common-errors--fixes)
6. [The Debugging Checklist](#6-the-debugging-checklist)

---

## 1. Debugging Overview

MCP debugging has two layers: your server's own logic, and the protocol connection itself.

```
MCP Debugging Layers
────────────────────────────────────────────────────────────

  Layer 1: Your server logic
  ──────────────────────────
  ├── Is my tool handler returning the right data?
  ├── Is my resource reading the correct file?
  └── Are my inputs validated correctly?
  Tool: unit tests, local logs, MCP Inspector

  Layer 2: The MCP protocol connection
  ─────────────────────────────────────
  ├── Is the server starting at all?
  ├── Is the client connecting successfully?
  ├── Are JSON-RPC messages being exchanged correctly?
  └── Does the host see all the tools/resources?
  Tool: Claude Desktop logs, MCP Inspector, stderr output
```

---

## 2. The MCP Inspector

The **MCP Inspector** is an official browser-based debugging tool from Anthropic. It lets you connect to your server and manually test all its capabilities without needing Claude Desktop.

### 2.1 Installation & Launch

```bash
# No installation needed — run directly with npx
npx @modelcontextprotocol/inspector python3 /path/to/server.py

# For a Node.js server:
npx @modelcontextprotocol/inspector node /path/to/server.js

# For a uv-managed server:
npx @modelcontextprotocol/inspector uv --directory /path/to/project run server.py
```

This launches a local web app (usually at `http://localhost:5173`) in your browser.

### 2.2 What the Inspector Lets You Do

```
MCP Inspector Capabilities
────────────────────────────────────────────────────────────

  ┌──────────────────────────────────────────────────────┐
  │  MCP Inspector (browser UI)                          │
  │                                                      │
  │  📋 Resources tab                                    │
  │  └── See all resources returned by list_resources    │
  │  └── Click any resource to read its content          │
  │                                                      │
  │  🔧 Tools tab                                        │
  │  └── See all tools with their inputSchema            │
  │  └── Fill in arguments and call tools manually       │
  │  └── See exact JSON request + response               │
  │                                                      │
  │  💬 Prompts tab                                      │
  │  └── List and preview all prompt templates           │
  │                                                      │
  │  📨 Messages tab (raw JSON-RPC)                      │
  │  └── See every message exchanged on the wire         │
  │  └── Invaluable for debugging protocol issues        │
  └──────────────────────────────────────────────────────┘
```

### 2.3 Inspector Workflow

```
Inspector Debug Workflow
────────────────────────────────────────────────────────────

  1. Run Inspector with your server
     $ npx @modelcontextprotocol/inspector python3 server.py

  2. Browser opens → Inspector connects to your server

  3. Click "Tools" tab
     └── Verify your tool appears with the right description

  4. Click your tool → fill in arguments → "Call Tool"
     └── See the exact result your handler returns

  5. If something is wrong:
     ├── Check "Messages" tab for raw JSON-RPC
     ├── Check your terminal for stderr output
     └── Fix the issue and restart the Inspector
```

---

## 3. Logging Best Practices

### 3.1 The #1 Rule: Never Use stdout for Logs

In a stdio MCP server, **stdout is reserved exclusively for JSON-RPC messages**. Any other output on stdout will corrupt the protocol and cause mysterious parse errors.

```
stdio stdout vs stderr
────────────────────────────────────────────────────────────

  stdout ──►  JSON-RPC protocol messages (SDK handles this)
              DO NOT write anything here manually

  stderr ──►  Your logs, debug output, error messages
              SAFE to write anything here

  Python — WRONG:
  print("Tool called with args:", arguments)        # corrupts protocol!

  Python — CORRECT:
  import sys
  print("Tool called with args:", arguments, file=sys.stderr)

  TypeScript — CORRECT:
  console.error("Tool called with args:", args)     # error → stderr
  // console.log() would go to stdout — AVOID
```

### 3.2 Structured Logging in Python

```python
import sys
import logging

# Configure logging to write to stderr
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr   # <-- critical: stderr not stdout
)

logger = logging.getLogger(__name__)

# Usage in your handlers:
@app.call_tool()
async def call_tool(name: str, arguments: dict):
    logger.info(f"Tool called: {name} with args: {arguments}")
    # ... tool logic ...
    logger.debug(f"Tool result: {result}")
    return result
```

### 3.3 MCP Logging Notifications

You can also send log messages through the MCP protocol itself (they appear in the host's UI):

```python
# Python — send a log notification to the client
from mcp.types import LoggingLevel

await app.request_context.session.send_log_message(
    level=LoggingLevel.INFO,
    data="Processing weather request for London",
    logger="weather-server"
)
```

```typescript
// TypeScript
await server.notification({
  method: "notifications/message",
  params: {
    level: "info",
    data: "Processing weather request for London",
    logger: "weather-server",
  },
});
```

---

## 4. Reading Claude Desktop Logs

Claude Desktop writes detailed logs about MCP connections that are essential for diagnosing connection issues.

### 4.1 Log File Location

```bash
# macOS
~/Library/Logs/Claude/

# Windows
%APPDATA%\Claude\logs\

# List log files
ls ~/Library/Logs/Claude/
# mcp-server-my-server.log  mcp.log  main.log
```

### 4.2 Tailing Logs in Real Time

```bash
# Watch all Claude logs in real time
tail -f ~/Library/Logs/Claude/*.log

# Watch a specific server's log
tail -f ~/Library/Logs/Claude/mcp-server-my-notes-server.log
```

### 4.3 What to Look For

```
Log Patterns to Watch For
────────────────────────────────────────────────────────────

  ✅ Success patterns:
  [INFO]  Server "my-server" started successfully (PID 12345)
  [INFO]  Initialized with capabilities: tools, resources
  [INFO]  tools/list returned 3 tools

  ❌ Error patterns:
  [ERROR] Failed to start "my-server": spawn python3 ENOENT
          → python3 not found in PATH
          → Fix: use full path /usr/bin/python3

  [ERROR] Server "my-server" exited with code 1
          → Server crashed on startup
          → Fix: run server.py manually and check stderr

  [ERROR] JSON parse error at position 42
          → print() on stdout in your server
          → Fix: change all print() to sys.stderr.write()

  [WARN]  Server "my-server" is slow to respond (>5s)
          → Your tool handler is taking too long
          → Fix: add timeout handling or async execution
```

---

## 5. Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `spawn python3 ENOENT` | `python3` not in PATH | Use full path: `which python3` |
| `spawn node ENOENT` | `node` not in PATH | Use full path: `which node` |
| Server exits code 1 | Import error or syntax error | Run server manually, read the traceback |
| `JSON parse error` | `print()` on stdout | Replace with `sys.stderr.write()` / `console.error()` |
| Tools not appearing | Wrong capability declared | Ensure `tools: {}` in capabilities |
| `Method not found` | Handler not registered | Check spelling of handler decorator/method |
| Tool times out | Handler blocks the event loop | Use `asyncio.to_thread()` for sync code |
| File not found error | Wrong path in config | Use absolute paths; verify with `ls` |
| `Permission denied` | Server lacks file read rights | Check file permissions: `ls -la` |

---

## 6. The Debugging Checklist

Use this top-to-bottom checklist whenever your MCP server has issues:

```
MCP Debugging Checklist
────────────────────────────────────────────────────────────

  STEP 1: Can the server run at all?
  ────────────────────────────────────
  □ Run manually: python3 server.py
  □ Does it start without crashing?
  □ Any import errors? (ModuleNotFoundError, etc.)

  STEP 2: Does the Inspector connect?
  ────────────────────────────────────
  □ npx @modelcontextprotocol/inspector python3 server.py
  □ Does the browser open?
  □ Do tools/resources appear in their tabs?
  □ Can you call a tool and get a valid result?

  STEP 3: Is the config correct?
  ────────────────────────────────
  □ Is claude_desktop_config.json valid JSON? (check jsonlint.com)
  □ Are all paths ABSOLUTE (not relative)?
  □ Is the command the full path? (which python3)
  □ Did you fully restart Claude Desktop (not just close)?

  STEP 4: Check the logs
  ───────────────────────
  □ tail -f ~/Library/Logs/Claude/*.log
  □ Look for ERROR lines
  □ Does the server log show "started successfully"?
  □ Any JSON parse errors? (→ you're printing to stdout)

  STEP 5: Test in Claude
  ───────────────────────
  □ Ask Claude: "What MCP tools do you have?"
  □ Is your server listed?
  □ Try calling a tool by name
  □ Check the Messages tab in Inspector while doing this
```

---

> **Previous Note ←** `08-connecting-to-cursor-and-ides.md`  
> **Next Note →** `10-handling-authentication.md` — Securely passing API keys and handling auth in MCP servers.
