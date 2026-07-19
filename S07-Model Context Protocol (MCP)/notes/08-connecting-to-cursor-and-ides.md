# 08 — Connecting to Cursor & IDEs

> **Phase:** Integration  
> **Goal:** Use your MCP servers directly inside code editors like Cursor and VS Code for an AI-enhanced coding workflow.

---

## Table of Contents
1. [MCP in IDEs vs Chat Apps — Key Differences](#1-mcp-in-ides-vs-chat-apps--key-differences)
2. [IDE MCP Support Overview](#2-ide-mcp-support-overview)
3. [Setting Up MCP in Cursor](#3-setting-up-mcp-in-cursor)
4. [Setting Up MCP in VS Code (with Continue.dev)](#4-setting-up-mcp-in-vs-code-with-continuedev)
5. [IDE-Specific Use Cases](#5-ide-specific-use-cases)
6. [Tips for IDE MCP Usage](#6-tips-for-ide-mcp-usage)

---

## 1. MCP in IDEs vs Chat Apps — Key Differences

```
Chat App (Claude Desktop) vs IDE (Cursor)
────────────────────────────────────────────────────────────

  Claude Desktop                     Cursor / VS Code
  ─────────────────────────────      ─────────────────────────────
  General-purpose conversation       Code-centric, project-aware

  Tools invoked during chat          Tools invoked in:
                                     ├── Composer (agent mode)
                                     └── Inline chat (@tool)

  Context = conversation history     Context = open files,
                                     project structure, cursor pos

  Great for:                         Great for:
  ├── Research tasks                 ├── "Run my tests and fix errors"
  ├── Summarizing documents          ├── "Read my package.json and
  └── General Q&A with tools             suggest dependency updates"
                                     └── "Query my DB for this schema"
```

---

## 2. IDE MCP Support Overview

| IDE | MCP Support | Config File |
|---|---|---|
| **Cursor** | ✅ Built-in (v0.45+) | `.cursor/mcp.json` or `~/.cursor/mcp.json` |
| **VS Code** | ✅ Via Continue.dev extension | `.continue/config.json` |
| **Zed** | ✅ Built-in | `~/.config/zed/settings.json` |
| **Windsurf** | ✅ Built-in | `~/.codeium/windsurf/mcp_config.json` |
| **JetBrains** | 🔄 Via plugins | Varies |

---

## 3. Setting Up MCP in Cursor

### 3.1 Config File Location

Cursor supports two config locations:

```
Cursor MCP Config Locations
────────────────────────────────────────────────────────────

  Global (all projects):  ~/.cursor/mcp.json
  Project-specific:       .cursor/mcp.json   (in your project root)

  Project config takes precedence over global config.
  Commit .cursor/mcp.json to share with your team.
```

### 3.2 Config File Format

The format is identical to Claude Desktop's config:

```json
{
  "mcpServers": {
    "notes-server": {
      "command": "python3",
      "args": ["/Users/yourname/mcp/notes-server/server.py"]
    },
    "project-tools": {
      "command": "node",
      "args": ["/Users/yourname/mcp/project-tools/dist/server.js"],
      "env": {
        "PROJECT_ROOT": "/Users/yourname/myproject"
      }
    }
  }
}
```

### 3.3 Enabling MCP in Cursor Settings

```
Cursor Settings Path
────────────────────────────────────────────────────────────

  Cursor → Settings (Cmd+,) → Search "MCP"
  └── Enable "Model Context Protocol" toggle

  Then: Cmd+Shift+P → "MCP: Reload Servers"
  Or:   Restart Cursor
```

### 3.4 Using MCP Tools in Cursor Agent

Once configured, MCP tools are available in **Composer (Agent mode)**:

```
Using Tools in Cursor
────────────────────────────────────────────────────────────

  Method 1: Let the agent decide
  ──────────────────────────────
  Open Composer (Cmd+I) → Switch to "Agent" mode
  Type: "Check my test suite and fix any failing tests"
  └── Agent will call your run_tests MCP tool automatically

  Method 2: Explicitly reference a tool
  ──────────────────────────────────────
  In chat: "@get_weather What's the weather in Mumbai?"
  └── Directly invokes the named tool

  Method 3: Tools in Cursor's inline chat
  ─────────────────────────────────────────
  Select code → Cmd+K → ask about it
  └── Tools are available here too in agent mode
```

---

## 4. Setting Up MCP in VS Code (with Continue.dev)

[Continue.dev](https://continue.dev) is the most popular open-source AI coding assistant for VS Code and JetBrains, and it has MCP support.

### 4.1 Installation

```bash
# Install the Continue extension from VS Code Marketplace
# Search: "Continue - Codestral, Claude, and more"

# Or via CLI
code --install-extension Continue.continue
```

### 4.2 Config File

Continue's config lives at `~/.continue/config.json`:

```json
{
  "models": [...],
  "mcpServers": [
    {
      "name": "notes-server",
      "command": "python3",
      "args": ["/Users/yourname/mcp/notes-server/server.py"]
    },
    {
      "name": "github-tools",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    }
  ]
}
```

> **Note:** Continue uses an array for `mcpServers` (not an object like Claude Desktop).

### 4.3 Using MCP in Continue

```
Continue MCP Usage
────────────────────────────────────────────────────────────

  Open Continue sidebar (Cmd+L)
  Type @ to see available context providers and tools
  │
  └── @notes-server/daily-note  ──►  reads a resource
  └── "@get_weather London"     ──►  calls a tool
```

---

## 5. IDE-Specific Use Cases

These tool ideas are particularly useful in an IDE context:

### 5.1 Project Info Tool — reads project metadata

```python
# Tool: get_project_info
# Reads package.json or requirements.txt and returns a summary

@app.list_tools()
async def list_tools():
    return [Tool(
        name="get_project_info",
        description=(
            "Get metadata about the current project: dependencies, "
            "scripts, Python version requirements, etc. Use when the user "
            "asks about the project setup, dependencies, or build commands."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Absolute path to the project root directory"
                }
            },
            "required": ["project_root"]
        }
    )]
```

### 5.2 Test Runner Tool — runs tests and returns results

```python
# Tool: run_tests
# Runs the test suite and returns pass/fail results

async def handle_run_tests(arguments: dict) -> CallToolResult:
    import subprocess
    project_root = arguments.get("project_root", ".")

    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=60
    )

    output = result.stdout + result.stderr
    return CallToolResult(
        content=[TextContent(type="text", text=output)],
        isError=(result.returncode != 0)
    )
```

### 5.3 README Resource — exposes project README to the LLM

```python
@app.list_resources()
async def list_resources():
    return [Resource(
        uri="project://readme",
        name="Project README",
        description="The project's README.md file",
        mimeType="text/markdown"
    )]

@app.read_resource()
async def read_resource(uri: str):
    if uri == "project://readme":
        readme = Path(os.environ["PROJECT_ROOT"]) / "README.md"
        return ReadResourceResult(contents=[
            TextResourceContents(uri=uri, mimeType="text/markdown", text=readme.read_text())
        ])
```

---

## 6. Tips for IDE MCP Usage

```
IDE MCP Best Practices
────────────────────────────────────────────────────────────

  ✅ Use project-specific configs (.cursor/mcp.json)
     └── Lets you have different servers per project

  ✅ Pass PROJECT_ROOT as an env variable
     └── Lets your server tools know which project they're working in

  ✅ Use agent mode (not just chat) in Cursor
     └── Agent can chain multiple tool calls to complete complex tasks

  ✅ Keep IDE-facing tools focused on code tasks
     └── file reading, test running, lint checking, dependency info

  ✅ Use resources for stable reference data
     └── README, schema files, config files the agent reads for context

  ⚠️ Be careful with tools that WRITE to files in agent mode
     └── Agent can make many rapid changes — scope tools carefully
```

---

> **Previous Note ←** `07-connecting-to-claude-desktop.md`  
> **Next Note →** `09-debugging-mcp.md` — Debugging your MCP server with the Inspector tool and log files.
