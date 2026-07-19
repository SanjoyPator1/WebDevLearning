# P01 — Echo Server

The simplest possible MCP server. A great first project to understand the
full structure of an MCP server before adding any complexity.

---

## What This Server Does

| Primitive | Name | What it does |
|---|---|---|
| 🔧 Tool | `echo` | Returns your text back (optionally repeated) |
| 🔧 Tool | `reverse` | Reverses the characters in a string |
| 🔧 Tool | `word_count` | Counts words, characters, and lines |
| 📄 Resource | `info://server-info` | Plain text description of this server |
| 📄 Resource | `info://how-to-use` | Markdown usage instructions |
| 💬 Prompt | `try-echo` | A demo prompt that tests all three tools |

---

## Setup

```bash
# From inside this folder:
pip install -r requirements.txt
```

---

## Step 1 — Test with the MCP Inspector (no Claude needed)

```bash
npx @modelcontextprotocol/inspector python3 server.py
```

This opens a browser at `http://localhost:5173`. Try:
1. **Tools tab** → click `echo` → enter some text → **Call Tool** → see the response
2. **Tools tab** → click `reverse` → enter a word → see it reversed
3. **Resources tab** → click `Echo Server Info` → see the content
4. **Messages tab** → see the raw JSON-RPC messages flying back and forth

---

## Step 2 — Connect to Claude Desktop

Add this to your `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "echo-server": {
      "command": "python3",
      "args": ["/Users/sanjoypator/Desktop/dev/ai/WebDevLearning/S07-Model Context Protocol (MCP)/projects/P01-echo-server/server.py"]
    }
  }
}
```

Then **fully quit and reopen Claude Desktop** (Cmd+Q, not just close the window).

---

## Step 3 — Try It in Claude

Once connected, try these prompts in Claude:

```
Echo the phrase "Learning MCP is fun!" back to me 3 times.
```
```
Reverse the word "Artificial Intelligence" for me.
```
```
Count the words and characters in this paragraph: [paste any text]
```
```
Read the info://server-info resource and tell me what you find.
```
```
Use the try-echo prompt with my name.
```

---

## What to Notice

- The **hammer icon** in Claude's chat input shows connected MCP tools
- Claude **automatically decides** when to call a tool — you don't trigger it manually
- The tool result appears in a **collapsible block** before Claude's response
- Any `isError: true` results cause Claude to tell you what went wrong gracefully

---

## Files

```
P01-echo-server/
├── server.py        ← the MCP server (read every comment!)
├── requirements.txt ← just: mcp
└── README.md        ← this file
```

---

## Key Concepts Practiced

- - [x] Note 04 — Server setup & SDK
- - [x] Note 06 — Creating tools (all 3 tools + isError pattern)
- - [x] Note 05 — Exposing resources (2 static resources)
- - [x] Note 03 — All 3 primitives in one server
- - [x] Note 07 — Connecting to Claude Desktop
- - [x] Note 09 — Debugging with MCP Inspector

---

> **Next project →** [P02 Notes Reader](../P02-notes-reader/) — expose real local files as dynamic resources.
