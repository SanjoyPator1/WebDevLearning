# 03 — Core Primitives: Resources, Tools & Prompts

> **Phase:** Fundamentals  
> **Goal:** Deeply understand the three building blocks of every MCP server — and know when to use each.

---

## Table of Contents
1. [Overview & Quick Comparison](#1-overview--quick-comparison)
2. [Resources — Read-Only Data](#2-resources--read-only-data)
3. [Tools — Executable Actions](#3-tools--executable-actions)
4. [Prompts — Reusable Templates](#4-prompts--reusable-templates)
5. [Which Primitive to Use? — Decision Guide](#5-which-primitive-to-use--decision-guide)

---

## 1. Overview & Quick Comparison

Every MCP server exposes some combination of these three primitives:

```
The Three Primitives
────────────────────────────────────────────────────────────

  ┌────────────────┬──────────────────────────┬────────────────────────┐
  │   Primitive    │       Think of it as…    │      Initiated by…     │
  ├────────────────┼──────────────────────────┼────────────────────────┤
  │  Resources     │  GET endpoint / file      │  Application / LLM     │
  │  Tools         │  POST endpoint / function │  LLM (AI decides)      │
  │  Prompts       │  Saved template / macro   │  User (picks from UI)  │
  └────────────────┴──────────────────────────┴────────────────────────┘
```

| | Resources | Tools | Prompts |
|---|---|---|---|
| **Purpose** | Expose data | Execute actions | Provide templates |
| **Can modify state?** | ❌ No | ✅ Yes | ❌ No |
| **Who calls it?** | LLM or app | LLM autonomously | User |
| **Analogy** | Read a file | Run a script | Fill in a form |

---

## 2. Resources — Read-Only Data

Resources let your server **expose data** that the LLM can read for context.

### 2.1 URI Scheme

Every resource has a unique URI. There is no enforced format, but conventions exist:

```
Resource URI Examples
────────────────────────────────────────────────────────────

  file:///Users/you/notes/2024-05-20.md        # local file
  database://mydb/users/id/42                  # DB record
  github://repos/my-org/api/issues/open        # API data
  memory://conversation/last-summary           # in-memory
  notes://daily/2024-05-20                     # custom scheme
```

### 2.2 Static vs Dynamic Resources

**Static resources** — the list is fixed and known ahead of time:
```python
# Always exposes exactly these two files
resources = [
    Resource(uri="file:///notes/readme.md", name="Readme"),
    Resource(uri="file:///notes/faq.md",    name="FAQ"),
]
```

**Dynamic resources** — discovered at runtime (e.g. all files in a folder):
```python
# Exposes whatever .md files exist right now
import os
resources = [
    Resource(uri=f"file:///notes/{f}", name=f)
    for f in os.listdir("/notes")
    if f.endswith(".md")
]
```

### 2.3 Resource Templates (URI Templates)

When you want to expose a *pattern* of resources rather than a fixed list, use **URI templates** with `{variable}` placeholders:

```
URI Template Example
────────────────────────────────────────────────────────────

  Template:   notes://{date}/entry
  
  Matches:
    notes://2024-05-20/entry  ──►  returns the note for May 20
    notes://2024-05-21/entry  ──►  returns the note for May 21
    notes://2024-06-01/entry  ──►  returns the note for June 1
```

### 2.4 The listResources Operation

When the client calls `resources/list`, your server returns an array of available resources:

```json
// Response to resources/list
{
  "resources": [
    {
      "uri": "file:///notes/2024-05-20.md",
      "name": "May 20th Notes",
      "description": "Daily notes from May 20th",
      "mimeType": "text/markdown"
    },
    {
      "uri": "file:///notes/2024-05-21.md",
      "name": "May 21st Notes",
      "mimeType": "text/markdown"
    }
  ]
}
```

### 2.5 The readResource Operation

When the client calls `resources/read` with a URI, your server returns the content:

```json
// Request
{ "method": "resources/read", "params": { "uri": "file:///notes/2024-05-20.md" } }

// Response
{
  "contents": [
    {
      "uri": "file:///notes/2024-05-20.md",
      "mimeType": "text/markdown",
      "text": "# May 20th\n\n- Learned about MCP\n- Set up first server..."
    }
  ]
}
```

> **Note:** For binary content (images, PDFs), use `blob` instead of `text`, with base64-encoded data.

### 2.6 Resource Subscriptions

Servers can optionally support **subscriptions** — notifying the client when a resource changes:

```
Resource Subscription Flow
────────────────────────────────────────────────────────────

  Client ──── resources/subscribe (uri) ───────────────► Server
                                                          │
  (file changes on disk)                                  │
                                                          │
  Client ◄─── notifications/resources/updated ──────────  Server
  │
  └── Client re-reads the resource automatically
```

---

## 3. Tools — Executable Actions

Tools are the most powerful primitive. They let the **LLM take actions** — calling APIs, running code, writing to databases, etc.

### 3.1 Tool Anatomy

Every tool has four parts:

```
Tool Structure
────────────────────────────────────────────────────────────

  ┌──────────────────────────────────────────────────────┐
  │  name        "get_weather"                           │
  │              ─────────────────────────────────────── │
  │  description "Get current weather for a city.        │
  │               Returns temperature and conditions."   │
  │              ─────────────────────────────────────── │
  │  inputSchema  {                                      │
  │    type: "object",                                   │
  │    properties: {                                     │
  │      city: { type: "string", description: "..." }   │
  │    },                                                │
  │    required: ["city"]                                │
  │  }                                                   │
  │              ─────────────────────────────────────── │
  │  handler      async function that does the work      │
  └──────────────────────────────────────────────────────┘
```

> ⚠️ **The description is critical.** The LLM reads ONLY the name and description to decide when and whether to call a tool. Write it like documentation for a human.

### 3.2 JSON Schema for Inputs

Tools use **JSON Schema** to define their parameters. Here are the most common patterns:

```json
// String parameter
"city": {
  "type": "string",
  "description": "The name of the city, e.g. 'London' or 'New York'"
}

// Number with constraints
"temperature": {
  "type": "number",
  "minimum": -100,
  "maximum": 100
}

// Enum (fixed choices)
"unit": {
  "type": "string",
  "enum": ["celsius", "fahrenheit"],
  "description": "Temperature unit to use"
}

// Boolean flag
"include_forecast": {
  "type": "boolean",
  "default": false
}

// Array of strings
"labels": {
  "type": "array",
  "items": { "type": "string" },
  "description": "List of labels to apply"
}

// Marking required fields (at the object level)
"required": ["city", "unit"]
```

### 3.3 Tool Call Flow

```
Tool Call Lifecycle
────────────────────────────────────────────────────────────

  User: "What's the weather in Tokyo?"
    │
    ▼
  LLM reads system context:
  ├── Sees tool: "get_weather — Get current weather for a city"
  └── Decides this tool is relevant

    │
    ▼
  LLM emits tool call:
  { "name": "get_weather", "arguments": { "city": "Tokyo" } }

    │
    ▼
  Host/Client sends to MCP Server:
  { "method": "tools/call", "params": { "name": "get_weather", ... } }

    │
    ▼
  Server handler runs → calls weather API → returns result

    │
    ▼
  Result sent back to LLM:
  { "content": [{ "type": "text", "text": "Tokyo: 22°C, Sunny" }] }

    │
    ▼
  LLM forms natural response:
  "The current weather in Tokyo is 22°C and sunny! 🌞"
```

### 3.4 Returning Errors from Tools

When something goes wrong in your tool, use the `isError` flag instead of throwing:

```python
# ✅ Correct: return an error result
return CallToolResult(
    content=[TextContent(type="text", text="Error: City not found")],
    isError=True
)

# ❌ Wrong: throwing an exception crashes the server
raise ValueError("City not found")
```

### 3.5 Safety Considerations

> ⚠️ **Human-in-the-loop:** MCP clients (like Claude Desktop) are designed to show the user which tools are about to be called and ask for confirmation before executing them — especially for destructive actions. Your server should also be defensive (validate inputs, have sensible limits).

---

## 4. Prompts — Reusable Templates

Prompts are **pre-built conversation starters** that your server exposes. Users can select them from the host UI (e.g., the `/` command menu in Claude Desktop).

### 4.1 Prompt Structure

```json
{
  "name": "review-code",
  "description": "Review a code snippet for bugs and improvements",
  "arguments": [
    {
      "name": "language",
      "description": "Programming language (e.g. Python, TypeScript)",
      "required": true
    },
    {
      "name": "focus",
      "description": "What to focus on: bugs, performance, or style",
      "required": false
    }
  ]
}
```

### 4.2 Prompt Response (What the Server Returns)

When the client calls `prompts/get`, the server returns a list of messages that pre-populate the conversation:

```json
{
  "description": "Code review prompt",
  "messages": [
    {
      "role": "user",
      "content": {
        "type": "text",
        "text": "Please review the following Python code for bugs and performance issues:\n\n```python\n{code_goes_here}\n```"
      }
    }
  ]
}
```

### 4.3 When to Use Prompts

Prompts are useful when you have a **standard way of asking the LLM to do a task** related to your server's domain:

```
Good Prompt Examples
────────────────────────────────────────────────────────────

  Server: GitHub MCP Server
  ├── Prompt: "summarize-pr"    → summarize a pull request
  ├── Prompt: "write-issue"     → create a well-formatted bug report
  └── Prompt: "review-diff"     → review a code diff

  Server: Notes MCP Server
  ├── Prompt: "daily-summary"   → summarize all notes from today
  └── Prompt: "find-action-items" → extract TODOs from notes
```

---

## 5. Which Primitive to Use? — Decision Guide

```
Decision Tree: Which Primitive?
────────────────────────────────────────────────────────────

  What do you want the LLM to do?
  │
  ├── Read/access some data?
  │   │
  │   ├── Is the data relatively static and addressable by URI?
  │   │   └── ✅ Use a RESOURCE
  │   │
  │   └── Is the data fetched dynamically with complex logic?
  │       └── ✅ Use a TOOL (with read-only intent)
  │
  ├── Take an action / change something?
  │   └── ✅ Use a TOOL
  │
  └── Give the user a pre-built way to start a conversation?
      └── ✅ Use a PROMPT

  Quick rule of thumb:
  ┌──────────────────────────────────────────────────────┐
  │  RESOURCE = noun  (a thing to look at)               │
  │  TOOL     = verb  (an action to perform)             │
  │  PROMPT   = template (a way to start a conversation) │
  └──────────────────────────────────────────────────────┘
```

---

> **Previous Note ←** `02-mcp-architecture.md`  
> **Next Note →** `04-server-setup-and-sdks.md` — Setting up your Python or TypeScript MCP server from scratch.
