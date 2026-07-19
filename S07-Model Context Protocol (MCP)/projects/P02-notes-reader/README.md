# P02 — Notes Reader

A personal notes reader server that scans a local `notes/` directory and exposes each markdown file as an MCP resource. It also includes a `search_notes` tool for regex-based text search across all notes.

---

## What This Server Does

| Primitive | Name | What it does |
|---|---|---|
| 📄 Resource | `notes://<filename>` | Exposes `.md` files in the `notes/` directory as dynamically listed resources. |
| 🔧 Tool | `search_notes` | Searches for a regex pattern or keyword across all your notes and returns matching lines. |

---

## Setup

```bash
# From inside this folder:
pip install -r requirements.txt
```

---

## Step 1 — Test with the MCP Inspector

```bash
npx @modelcontextprotocol/inspector python3 server.py
```

This opens a browser at `http://localhost:5173`. Try:
1. **Resources tab** → see all your `.md` files listed. Click one to read its content.
2. **Tools tab** → click `search_notes` → enter a query like `MCP` → **Call Tool** → see matching lines and filenames.

---

## Step 2 — Connect to Claude Desktop

Add this to your `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "notes-reader": {
      "command": "python3",
      "args": ["/Users/sanjoypator/Desktop/dev/ai/WebDevLearning/S07-Model Context Protocol (MCP)/projects/P02-notes-reader/server.py"]
    }
  }
}
```

Then **fully quit and reopen Claude Desktop** (Cmd+Q).

---

## Step 3 — Try It in Claude

Once connected, try these prompts in Claude:

```
List all my notes available through MCP.
```
```
Search my notes for any mentions of "Claude" or "LLM".
```
```
Read the note about the MCP architecture and summarize it for me.
```

---

## Key Concepts Practiced

- - [x] Dynamic Resource listing based on local filesystem state.
- - [x] Custom URI schemes (`notes://`).
- - [x] Resource Read handlers with path traversal security checks.
- - [x] A filesystem-aware Tool (`search_notes`) that complements the Resources.

---

> **Next project →** [P03 Calculator](../P03-calculator/) — A multi-tool server demonstrating input validation and error handling.
