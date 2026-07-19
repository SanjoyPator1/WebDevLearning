# 07 — Connecting to Claude Desktop

> **Phase:** Integration  
> **Goal:** Wire your local MCP server into Claude Desktop and test it with a real conversation.

---

## Table of Contents
1. [What is claude_desktop_config.json?](#1-what-is-claude_desktop_configjson)
2. [Config File Location](#2-config-file-location)
3. [Config File Structure](#3-config-file-structure)
4. [Adding Your Server (Python)](#4-adding-your-server-python)
5. [Adding Your Server (Node.js)](#5-adding-your-server-nodejs)
6. [Restarting Claude Desktop](#6-restarting-claude-desktop)
7. [Verifying the Connection](#7-verifying-the-connection)
8. [End-to-End Walkthrough](#8-end-to-end-walkthrough)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. What is claude_desktop_config.json?

Claude Desktop reads a JSON configuration file at startup to know which MCP servers to connect to. For each server listed, it spawns the server process (via stdio) and establishes a Client connection.

```
Config File Role
────────────────────────────────────────────────────────────

  claude_desktop_config.json
          │
          │ read at startup
          ▼
  Claude Desktop (Host)
          │
          ├── For each server entry:
          │   └── spawn: python /path/to/server.py
          │                       OR
          │              node /path/to/server.js
          │
          └── MCP Client connects via stdio
```

---

## 2. Config File Location

| OS | Path |
|---|---|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

```bash
# macOS — open the config file in your default editor
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or create it if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

---

## 3. Config File Structure

The config is a JSON object with a single `mcpServers` key. Each entry is a named server:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "python3",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "MY_API_KEY": "sk-..."
      }
    },
    "another-server": {
      "command": "node",
      "args": ["/absolute/path/to/server.js"]
    }
  }
}
```

### Config Field Reference

| Field | Required | Description |
|---|---|---|
| `command` | ✅ Yes | The executable to run (`python3`, `node`, `uv`) |
| `args` | ✅ Yes | Array of arguments passed to the command |
| `env` | ❌ No | Environment variables injected into the server process |

> ⚠️ **Always use absolute paths** in `args`. Relative paths fail because Claude Desktop's working directory is unpredictable.

---

## 4. Adding Your Server (Python)

```json
{
  "mcpServers": {
    "my-notes-server": {
      "command": "python3",
      "args": ["/Users/yourname/projects/my-mcp-server/server.py"]
    }
  }
}
```

**If you use `uv` (recommended for virtual environments):**
```json
{
  "mcpServers": {
    "my-notes-server": {
      "command": "uv",
      "args": [
        "--directory", "/Users/yourname/projects/my-mcp-server",
        "run", "server.py"
      ]
    }
  }
}
```

**With environment variables (e.g. for API keys):**
```json
{
  "mcpServers": {
    "weather-server": {
      "command": "python3",
      "args": ["/Users/yourname/projects/weather-server/server.py"],
      "env": {
        "WEATHER_API_KEY": "your-actual-api-key-here",
        "LOG_LEVEL": "debug"
      }
    }
  }
}
```

---

## 5. Adding Your Server (Node.js)

```json
{
  "mcpServers": {
    "my-ts-server": {
      "command": "node",
      "args": ["/Users/yourname/projects/my-mcp-server/dist/server.js"]
    }
  }
}
```

**Using npx (if your server is a package):**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/yourname/docs"]
    }
  }
}
```

**With ts-node (skip compile step):**
```json
{
  "mcpServers": {
    "my-ts-server": {
      "command": "npx",
      "args": ["ts-node", "/Users/yourname/projects/my-mcp-server/server.ts"]
    }
  }
}
```

---

## 6. Restarting Claude Desktop

After editing the config file, you **must fully restart** Claude Desktop:

```
macOS Restart Steps
────────────────────────────────────────────────────────────

  1. Click Claude in the menu bar (top right) → Quit Claude
     OR: Cmd + Q while Claude Desktop is focused

  2. Wait 2-3 seconds for full shutdown

  3. Reopen Claude Desktop from Applications

  ⚠️ Do NOT just close the window — Claude stays running in the menu bar.
  You must fully quit the app for config changes to take effect.
```

---

## 7. Verifying the Connection

Once Claude restarts, verify your server loaded correctly:

```
Verification Steps
────────────────────────────────────────────────────────────

  1. Look for the MCP icon (hammer icon 🔨) in the Claude chat input bar
     └── Click it to see a list of connected servers and available tools

  2. In the chat, ask Claude directly:
     "What MCP tools do you have available?"
     └── Claude will list all tools from all connected servers

  3. Try calling your tool:
     "Use the say_hello tool with my name"
     └── Claude should call the tool and show the result
```

---

## 8. End-to-End Walkthrough

Here is a complete example from a working server to using it in Claude:

```
Full End-to-End Flow
────────────────────────────────────────────────────────────

  Step 1: Write your server
  ─────────────────────────
  /Users/yourname/mcp/weather-server/server.py
  (contains get_weather tool — see note 06)

  Step 2: Test it runs
  ────────────────────
  $ python3 /Users/yourname/mcp/weather-server/server.py
  (hangs waiting for input — correct behavior)
  Ctrl+C to quit

  Step 3: Add to config
  ──────────────────────
  ~/Library/Application Support/Claude/claude_desktop_config.json:
  {
    "mcpServers": {
      "weather": {
        "command": "python3",
        "args": ["/Users/yourname/mcp/weather-server/server.py"]
      }
    }
  }

  Step 4: Restart Claude Desktop
  ───────────────────────────────
  Cmd+Q → reopen

  Step 5: Use it!
  ────────────────
  You: "What's the weather like in Tokyo right now?"
  Claude: [calls get_weather tool internally]
  Claude: "The current weather in Tokyo is 22°C with clear skies..."
```

---

## 9. Troubleshooting

### Common Issues and Fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| Server doesn't appear in hammer menu | Config JSON is invalid | Validate JSON at jsonlint.com |
| `spawn python3 ENOENT` error | `python3` not in PATH | Use full path: `/usr/bin/python3` or `/opt/homebrew/bin/python3` |
| `spawn node ENOENT` | Node not found | Use full path: `/usr/local/bin/node` |
| Server listed but tools don't work | Server crashes on start | Check stderr logs (see below) |
| Config changes not taking effect | Claude not fully restarted | Quit from menu bar, not just close window |
| `JSON parse error` in logs | `print()` on stdout in server | Replace all `print()` with `sys.stderr.write()` |

### Reading Claude Desktop Logs

```bash
# macOS — Claude writes MCP logs here:
tail -f ~/Library/Logs/Claude/mcp*.log

# Or check all logs:
ls ~/Library/Logs/Claude/
```

Look for lines like:
```
[ERROR] Failed to start server "weather": spawn python3 ENOENT
[INFO]  Server "weather" started (PID 12345)
[ERROR] Server "weather" exited with code 1
```

### Finding the Full Python Path

```bash
# macOS
which python3
# → /usr/bin/python3  or  /opt/homebrew/bin/python3

# If using a virtual environment:
source venv/bin/activate
which python3
# → /Users/yourname/projects/myserver/venv/bin/python3
```

---

> **Previous Note ←** `06-creating-tools.md`  
> **Next Note →** `08-connecting-to-cursor-and-ides.md` — Using MCP servers inside your code editor.
