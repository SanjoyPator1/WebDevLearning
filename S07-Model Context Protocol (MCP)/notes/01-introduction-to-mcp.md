# 01 — Introduction to Model Context Protocol (MCP)

> **Phase:** Fundamentals  
> **Goal:** Understand what MCP is, why it exists, and its core vocabulary before writing any code.

---

## Table of Contents
1. [The Problem MCP Solves](#1-the-problem-mcp-solves)
2. [What is MCP?](#2-what-is-mcp)
3. [The Analogy: USB-C for AI](#3-the-analogy-usb-c-for-ai)
4. [How it Works — The Big Picture](#4-how-it-works--the-big-picture)
5. [Core Vocabulary](#5-core-vocabulary)
6. [What MCP is NOT](#6-what-mcp-is-not)
7. [A Minimal Real-World Example](#7-a-minimal-real-world-example)
8. [References](#8-references)

---

## 1. The Problem MCP Solves

Before MCP, connecting an LLM (like Claude or GPT) to external data was messy. Every AI app had to build **custom, one-off integrations** for every data source it needed.

```
Without MCP (The Old Way)
──────────────────────────────────────────────────────────

  Claude Desktop ──── custom code ───► GitHub API
  Claude Desktop ──── custom code ───► Notion
  Claude Desktop ──── custom code ───► Local Files
  Claude Desktop ──── custom code ───► Postgres DB

  Cursor ──────────── custom code ───► GitHub API
  Cursor ──────────── custom code ───► Notion
  ... and so on for every new AI app
```

This is the **M × N problem**: M AI apps × N data sources = M×N separate integrations to build and maintain. This doesn't scale.

---

## 2. What is MCP?

**MCP (Model Context Protocol)** is an **open standard** created by Anthropic (released Nov 2024) that defines a universal way for AI applications (clients) to talk to data/tool providers (servers).

Think of it as a **common language** — if your data source speaks MCP, any AI app that speaks MCP can instantly connect to it.

```
With MCP (The New Way)
──────────────────────────────────────────────────────────

  Claude Desktop ─────┐
  Cursor ─────────────┤──► MCP Protocol ──► GitHub MCP Server
  Your Custom AI App ─┘                     (built once, used by all)

  All clients connect to all servers via one standard.
  M + N integrations instead of M × N.
```

> **Key Point:** MCP decouples the AI app from the data source. You build the server once; every MCP-compatible client gets access automatically.

---

## 3. The Analogy: USB-C for AI

The best mental model for MCP is **USB-C**.

```
USB-C Analogy
──────────────────────────────────────────────────────────

  Physical World                     AI World
  ─────────────────                  ─────────────────────
  USB-C Port (standard)       ≈      MCP Protocol (standard)
  Your Laptop (consumer)      ≈      MCP Client (Claude, Cursor)
  External Device (provider)  ≈      MCP Server (your data/tools)
  Cable                       ≈      Transport (stdio / HTTP+SSE)

  Just like USB-C: any laptop can plug into any USB-C device,
  any MCP Client can connect to any MCP Server.
```

---

## 4. How it Works — The Big Picture

MCP uses a **Client ↔ Server** architecture. Here is the full flow of a single interaction:

```
MCP Interaction Flow
──────────────────────────────────────────────────────────

  User
   │
   │  "Summarize my latest GitHub issues"
   ▼
  MCP Client (e.g. Claude Desktop)
   │
   │  1. Sends user message to LLM
   │  2. LLM decides it needs a tool → "list_github_issues"
   │
   ├──── Tool Call Request ─────────────────────────────►  MCP Server
   │                                                         (GitHub Server)
   │                                                          │
   │                                                          │  3. Fetches real data
   │                                                          │     from GitHub API
   │                                                          │
   │◄─── Tool Call Result ──────────────────────────────     │
   │     (list of issues in JSON)                             │
   │
   │  4. LLM receives real data, generates summary
   │
   ▼
  User sees: "Your top 3 open issues are..."
```

The MCP Server is just a **lightweight process** (could be a Python or Node.js script) running locally on your machine or on a remote server.

---

## 5. Core Vocabulary

These are the six terms you will see everywhere in MCP documentation.

### 5.1 MCP Host
The application that the **user interacts with directly**. It manages one or more MCP Clients internally.

> Examples: Claude Desktop, Cursor, VS Code (with extension), your own chat app.

### 5.2 MCP Client
A **protocol-level connector** that lives inside the Host. Each Client maintains exactly **one connection** to one MCP Server.

> Think of it as the "socket" or "pipe" between the host app and a server.

### 5.3 MCP Server
The **program you build**. It exposes your data or functionality to any MCP Client using three primitives: Resources, Tools, and Prompts.

> Examples: a server that reads your local files, one that queries your database, one that wraps the Stripe API.

### 5.4 Resources
**Read-only data** that your server exposes. The LLM can read this for context.

```
# Example Resource URI
file:///Users/you/notes/meeting.md
database://mydb/customers/id/42
github://repos/my-org/my-repo/issues
```

> Think of Resources like **GET endpoints** — they return data, they don't change anything.

### 5.5 Tools
**Executable functions** that the LLM can call to take actions or fetch dynamic data. This is where the real power is.

```
# Example Tool Definition (conceptual)
Tool Name:    create_github_issue
Description:  Creates a new issue in a GitHub repository
Parameters:
  - title:  string  (required)
  - body:   string  (required)
  - labels: list    (optional)
```

> Think of Tools like **POST endpoints** — they do things, they can change state.

> ⚠️ **Important:** The LLM *decides* when to call a tool, but the **user/host controls** whether to allow it. MCP is designed with human-in-the-loop safety in mind.

### 5.6 Prompts
**Reusable prompt templates** that your server provides to the client. The user can select these from the host UI.

```
# Example Prompt Template
Name:     summarize-code-review
Template: "Review the following code diff and provide: 
           1) A brief summary, 2) Potential bugs, 
           3) Suggestions for improvement.\n\nDiff:\n{{diff}}"
```

> Think of Prompts like **saved shortcuts** — they help standardize how the LLM is asked to do a task.

---

## 6. What MCP is NOT

It is easy to confuse MCP with related concepts. Here's a quick comparison:

```
Concept Comparison
──────────────────────────────────────────────────────────

  Concept          What it is                        vs MCP
  ───────────────  ────────────────────────────────  ──────────────────────────────
  RAG              Technique to retrieve docs and     MCP is a *protocol*, not a
                   stuff them into a prompt.          technique. You can implement
                                                      RAG *over* MCP using Resources.

  OpenAI Plugins   Similar idea, but proprietary      MCP is open-source and model-
                   and tied to OpenAI ecosystem.      agnostic. Works with any LLM.

  LangChain/       Agent frameworks that orchestrate  MCP is a lower-level transport
  LlamaIndex       LLMs and tools.                    standard. These frameworks
                                                      *can use* MCP to talk to tools.

  REST API         A way to expose data over HTTP.    An MCP Server *can use* a REST
                                                      API internally, but MCP adds
                                                      the AI-specific layer on top.
```

---

## 7. A Minimal Real-World Example

Let's make this concrete. Imagine you want Claude to be able to read your local notes.

**Without MCP:** You'd have to manually copy-paste your notes into the Claude chat window every time.

**With MCP:** You build a tiny MCP Server that exposes your notes folder, and Claude can read them on demand.

Here is the *conceptual* flow (actual code comes in later notes):

```
Step-by-step: "Read my notes" with MCP
──────────────────────────────────────────────────────────

Step 1: You build a Notes MCP Server
        └── It exposes: Resource → "file://notes/*.md"

Step 2: You add it to Claude Desktop's config
        └── claude_desktop_config.json points to your server

Step 3: You open Claude Desktop
        └── Claude auto-connects to your Notes Server

Step 4: You ask Claude:
        └── "What did I write about machine learning last week?"

Step 5: Claude internally:
        ├── Calls Resource: "file://notes/2024-05-13.md"
        ├── Calls Resource: "file://notes/2024-05-14.md"
        └── Reads the content, finds the ML section

Step 6: Claude responds with a smart summary of YOUR notes.
        No copy-pasting. No manual context.
```

This is the power of MCP — your data stays local and private, but the AI can access it intelligently.

---

## 8. References

| Resource | Link |
|---|---|
| Official MCP Documentation | https://modelcontextprotocol.io/ |
| MCP Specification (GitHub) | https://github.com/modelcontextprotocol/specification |
| Anthropic's Announcement Blog | https://www.anthropic.com/news/model-context-protocol |
| MCP SDKs (Python & TypeScript) | https://github.com/modelcontextprotocol |
| MCP Inspector (debugging tool) | https://github.com/modelcontextprotocol/inspector |

---

> **Next Note →** `02-mcp-architecture.md` — Deep dive into the Client-Server model, transport layers (stdio vs HTTP+SSE), and the connection lifecycle.
