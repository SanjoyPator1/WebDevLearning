# Topic 3 — Model Context Protocol (MCP)

## Why This Topic

MCP, originated by Anthropic and now governed under the Linux Foundation's
Agentic AI Foundation, has become the standard way to connect LLMs/agents to
external tools and data sources — described as "the USB-C of agent tool
integration." You're already using an MCP-capable environment (Claude Code),
so understanding the protocol you're standing on, and being able to build
your own server, is high-leverage.

## Prerequisites

Topic 1 (tools/`bind_tools` concept). Topic 2 helps but isn't required —
MCP servers can be tested standalone before wiring into a graph.

## Outline

1. **Protocol Basics** — client/server architecture, JSON-RPC messages,
   the three primitives: **tools** (actions), **resources** (data the model
   can read), and **prompts** (reusable prompt templates the server exposes).
2. **Building a Minimal MCP Server** — using the official Python SDK
   (`mcp` package), exposing one tool (e.g. a function that queries a small
   local SQLite database of your learning notes) and one resource.
3. **Running & Inspecting the Server** — using the MCP Inspector to call the
   tool/resource directly and see the raw JSON-RPC traffic (dry-run: trace
   one full request/response cycle).
4. **Connecting a Client** — wiring the server into a LangChain/LangGraph
   agent via an MCP client adapter, so a graph node can call your custom tool
   through the protocol instead of a direct Python import.
5. **Transports** — stdio vs HTTP/SSE transports, and when each is
   appropriate (local dev tool vs remote shared service).
6. **Security Model** — why tool/resource access needs explicit user consent,
   and how this maps to the permission-prompt behavior you already see in
   Claude Code.

## Planned Deliverables

- `code/template/mcp-fundamentals.ipynb` (+ a small standalone
  `mcp_server.py`, since MCP servers run as separate processes) — sections
  1-3 built out fully; **exercise cells** for section 4 (connect the server
  into a LangGraph agent from Topic 2) and a second tool you design yourself.
- `code/solutions/` — copy of the template + server file.
- `notes/03-model-context-protocol-mcp.md` — diagram of client/server/
  transport plus a dry-run of one JSON-RPC `tools/call` request and response.
