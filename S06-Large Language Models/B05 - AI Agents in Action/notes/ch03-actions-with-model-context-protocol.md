# Chapter 3: Actions with Model Context Protocol

## Table of Contents

1. [The Problem MCP Solves](#1-the-problem-mcp-solves)
2. [The Shape of MCP: Client, Server, Service](#2-the-shape-of-mcp-client-server-service)
3. [The Three Things a Server Can Offer](#3-the-three-things-a-server-can-offer)
4. [Stateless by Design: How a Request Actually Travels](#4-stateless-by-design-how-a-request-actually-travels)
5. [Transports: STDIO and Streamable HTTP](#5-transports-stdio-and-streamable-http)
6. [Building Your First Server](#6-building-your-first-server)
7. [Seeing Inside a Server: The Inspector and Logging](#7-seeing-inside-a-server-the-inspector-and-logging)
8. [Connecting a Server to an Agent](#8-connecting-a-server-to-an-agent)
9. [Moving In-Process Tools Out to a Server](#9-moving-in-process-tools-out-to-a-server)
10. [When a Tool Needs to Ask a Question Back](#10-when-a-tool-needs-to-ask-a-question-back)
11. [What Is Deprecated, and What Replaced It](#11-what-is-deprecated-and-what-replaced-it)
12. [What Agency Actually Costs](#12-what-agency-actually-costs)
13. [Chapter 3 Code Map](#13-chapter-3-code-map)
14. [Key Takeaways](#14-key-takeaways)

---

# 1: The Problem MCP Solves

## In One Sentence

**MCP** (Model Context Protocol) is a shared language for connecting an AI
model to outside things — files, databases, APIs, other programs — so you
write each connection once instead of once per model provider.

## The Problem, With Numbers

Chapter 2 gave an agent tools by writing Python functions and handing them
over with `tools=[...]`. That works, and for tools only one agent will ever
use, it stays the right answer. The trouble starts when the same tool has to
work with more than one model provider, or be shared with more than one
agent.

Every provider describes tools a little differently. One wants
`input_schema`, another wants `parameters`. One returns tool results as
`{"role": "tool"}`, another wraps them in a `tool_result` block. None of
those differences are hard, but each one is real work: read that provider's
docs, write the adapter, test it live, and keep it working forever.

The cost is not additive, it is multiplicative:

```text
WITHOUT a shared protocol           WITH a shared protocol
(every pair needs its own glue)     (each side speaks MCP once)

 agent A ─┬─> file tool              agent A ─┐
          ├─> database tool                   │
          └─> search tool            agent B ─┼──> [ MCP ] ──┬─> file server
                                              │              ├─> database server
 agent B ─┬─> file tool              agent C ─┘              └─> search server
          ├─> database tool
          └─> search tool            3 agents + 3 servers = 6 pieces
                                     of code, each written once
 agent C ─┬─> file tool
          ├─> database tool
          └─> search tool

 3 agents x 3 tools = 9 separate
 integrations to write and maintain
```

Three agents and three tools is nine integrations one way and six pieces the
other. At four agents and ten tools it is forty versus fourteen. That gap is
the entire reason the protocol exists.

## What MCP Does Not Solve

Worth saying plainly, because it is oversold: MCP removes the per-provider
schema and call-format work. It does **not** remove authentication, error
handling, versioning your server, or keeping that server running. Those are
still yours. What you get back is that a tool you write once can be used by
any agent, in any language, that speaks the protocol.

---

# 2: The Shape of MCP: Client, Server, Service

Three roles, and it helps to keep them separate in your head:

```text
   ┌──────────────┐         ┌──────────────┐        ┌──────────────┐
   │  MCP CLIENT  │  MCP    │  MCP SERVER  │  its   │   SERVICE    │
   │              │ ──────> │              │ ─────> │              │
   │ an agent,    │ (JSON-  │ owns the     │  own   │ a database,  │
   │ Claude       │  RPC    │ tools and    │  code  │ an API, the  │
   │ Desktop,     │  2.0)   │ decides what │        │ filesystem,  │
   │ an IDE, the  │         │ to expose    │        │ another      │
   │ Inspector    │ <────── │              │ <───── │ agent        │
   └──────────────┘         └──────────────┘        └──────────────┘
```

The **client** is whatever connects and asks for things. An agent is one kind
of client, but so is Claude Desktop, so is an IDE, so is the debugging
Inspector you will meet in section 7.

The **server** owns the actual capabilities and decides what to expose. It
knows nothing about who is calling it.

The **service** is whatever sits behind the server doing the real work — a
database, a web API, the filesystem. That word is our own label for
convenience, not a protocol term.

Messages between client and server are **JSON-RPC 2.0** — a long-standing,
boring convention for "here is a method name and some parameters, send me
back a result or an error." Nothing about it is AI-specific, which is a
feature.

One practical consequence people underrate: because the agreement is at the
message level, **the two sides do not need to share a language**. Your Python
agent can use a server written in Node.js without any bridge code. That is
exactly what `04_mcp_agent_local_server_files.py` does — a Python agent
consuming `@modelcontextprotocol/server-filesystem`, which is Node, launched
through `npx`, with zero cross-language plumbing on your side.

---

# 3: The Three Things a Server Can Offer

A server can expose three kinds of thing. The clearest way to tell them apart
is to ask **who decides when it gets used**.

| Primitive | What it is | Who decides to use it |
|---|---|---|
| **Tool** | An action the model can take | The **model**, mid-conversation |
| **Resource** | Data sitting at an address, ready to be read | The **user or the app** |
| **Prompt** | A reusable template that steers the model | The **user or the app** |

Tools are the ones an agent reaches for on its own. Resources and prompts are
things a person hands to the model — you pick a prompt template from a menu,
or attach a resource to the conversation. That is why they are separate
categories rather than one.

Here is one server exposing all three, from `01_complete_mcp_server.py`:

```python
import sys
from mcp.server import MCPServer

mcp = MCPServer("DemoServer")

@mcp.resource("greeting://{name}")          # a RESOURCE, at a template address
def get_greeting(name: str) -> str:
    """return a personalized greeting for the given name"""
    print(f"Received request for greeting: {name}", file=sys.stderr)
    return f"Greetings, {name}! (from resource)"

@mcp.tool()                                  # a TOOL, the model may call it
def add(a: int, b: int) -> int:
    """Add two integers and return the sum"""
    return a + b

@mcp.prompt()                                # a PROMPT, a person picks it
def welcome(name: str) -> str:
    """Generate a welcome message using the greeting resource"""
    greeting_text = get_greeting(name)       # plain Python call, see below
    return f"{greeting_text} How can I assist you today?"
```

Three details in that small file are worth pulling out.

**The resource address has a placeholder.** `greeting://{name}` is a
**template URI** — an address with a blank in it. A client fills in the blank
(`greeting://Alice`) when reading it. Templates are listed separately from
fixed resources, under `resources/templates/list`, and they appear there with
the `{name}` still intact.

**The prompt calls the resource as a normal function.** `welcome` calls
`get_greeting(name)` directly. It can, because both are just Python functions
in the same process. A *client* has no such shortcut — from outside, reaching
a prompt and reaching a resource are two different requests (`prompts/get`
versus `resources/read`). Inside your own server, they are just code.

**Docstrings are not comments.** The docstring on a tool becomes the
description the model reads when deciding whether to call it. So do
`Field(description=...)` entries and even pydantic class docstrings — all of
it is published to the model. If you want a note that stays private, use a
`#` comment.

One limitation to plan around: **the OpenAI Agents SDK consumes tools only.**
Resources and prompts from a server are invisible to it. They are not
useless — the Inspector reads them, Claude Desktop reads them — but if your
agent needs data from a server, expose it as a tool.

---

# 4: Stateless by Design: How a Request Actually Travels

This section is the one that most online material still gets wrong, so it is
worth reading slowly.

## The Core Idea

**Every MCP request stands completely on its own.** There is no connecting
step, no session, and nothing the server has to remember between one request
and the next. A request arrives carrying everything needed to understand it,
gets answered, and the server can forget it happened.

```text
 ┌─────────┐                                      ┌─────────┐
 │ CLIENT  │                                      │ SERVER  │
 └─────────┘                                      └─────────┘
      │                                                │
      │  tools/call  (carries protocol version,        │
      │              capabilities, tool name)          │
      │ ─────────────────────────────────────────────> │
      │                                                │  handles it
      │  <───────────────────────────────────────────  │  forgets it
      │                        result                  │
      │                                                │
      │  tools/call  (carries ALL of that AGAIN)        │
      │ ─────────────────────────────────────────────> │
      │                                                │  handles it
      │  <───────────────────────────────────────────  │  forgets it
      │                        result                  │
```

Nothing above depends on anything before it. Two requests from the same
client could be answered by two different server processes on two different
machines and neither would notice.

## Where the Per-Request Information Lives

Since nothing is negotiated up front, each request carries its own context in
a `_meta` object — and `_meta` goes **inside `params`**, not next to it:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {"a": 5, "b": 7},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

Both `protocolVersion` and `clientCapabilities` are required in `_meta`.
`clientInfo` is optional. Miss the required ones and the request is rejected —
this is a common first-time stumble when hand-writing requests.

## Two Headers That Let Gateways Route Without Reading Bodies

Over HTTP, two headers are part of the contract:

- **`Mcp-Method`** — required on every request, naming the method
  (`tools/call`, `tools/list`, and so on).
- **`Mcp-Name`** — required for the three requests that target something by
  name: `tools/call`, `prompts/get`, `resources/read`.

Get either wrong — absent, or not matching the body — and you get error
`-32020`. Several write-ups claim the SDK ignores these. It does not.

The point of putting them in headers is infrastructure: a load balancer or
gateway can route and rate-limit on a header without opening the request
body at all.

## Asking a Server What It Supports

If a client wants to know a server's capabilities before calling anything,
there is `server/discover`, which returns supported protocol versions,
capabilities, and identity in one response. **Servers must implement it;
clients may skip it.** A client that already knows what it wants can simply
call `tools/call` as its very first message.

## Caching, Because Answers Are Now Reusable

Statelessness makes caching straightforward, so list-style results carry
`ttlMs` (how long this answer stays fresh) and `cacheScope` (whether it is
safe to share across users) — the same idea as HTTP cache headers.

Six methods are cacheable: `prompts/list`, `resources/list`,
`resources/read`, `resources/templates/list`, `server/discover`, and
`tools/list`. Two notable ones are **not**: `tools/call` and `prompts/get`.
That makes sense — calling a tool does work, and work is not a cached
lookup.

## Why This Matters Operationally

```text
BEFORE (session-based)                 NOW (stateless)

 client ──> [ sticky session ]          client ──> [ plain round-robin ]
              must always                            any server, any
              reach THE SAME                         request, no memory
              server process                         needed
                    │
                    v
            shared session store,       no session store,
            gateway parsing bodies      routes on Mcp-Method header,
            to track sessions           serverless deploys work
```

A server that used to need sticky sessions and a shared session store can now
sit behind an ordinary round-robin load balancer, or run as a serverless
function that spins up per request.

## The Gotcha That Will Bite You First

In the Python SDK, **`stateless_http` defaults to `False`.** Leave it out and
a client that sends no `MCP-Protocol-Version` gets an HTTP 400 with
`-32600 "Bad Request: Missing session ID"` — confusing, because you are
running current software that appears to demand a session. Opt in
explicitly:

```python
mcp.run(
    transport="streamable-http",
    host="127.0.0.1",
    port=8000,
    stateless_http=True,      # <- not the default; you must ask for it
)
```

That is exactly what `06_mcp_time_travel_tracker.py` and
`01_claude_mcp_server.py` do in their `__main__` blocks.

## An Era Tell

You will meet servers from both eras. The fastest way to spot an older one:
its results lack `resultType`, `ttlMs`, `cacheScope`, and `_meta.serverInfo`.
A known older protocol version is served in that older shape without
complaint; only an *unknown* version is an error (`-32022`, which helpfully
includes `data.supported`).

---

# 5: Transports: STDIO and Streamable HTTP

**Transport** just means "how the messages physically get from client to
server." The messages themselves are identical either way — same JSON-RPC,
same methods. Only the pipe changes.

## STDIO

The client launches the server as a **subprocess** on the same machine and
talks to it through that process's standard input and output.

```text
  ┌────────────────── your agent process ──────────────────┐
  │                                                        │
  │   agent code                                           │
  │       │                                                │
  │       │ starts as subprocess                           │
  │       v                                                │
  │   ┌──────────────────────────┐                         │
  │   │  server process          │                         │
  │   │  stdin  <── requests     │  no network at all      │
  │   │  stdout ──> responses    │  one caller only        │
  │   │  stderr ──> your logs    │                         │
  │   └──────────────────────────┘                         │
  └────────────────────────────────────────────────────────┘
```

Fast, private, no ports, no network. Strictly one-to-one: only the process
that spawned it can talk to it. Ideal for local development and for tools
that should never be reachable from outside.

**The rule you must not break with STDIO:** `stdout` *is* the message
channel. A plain `print()` inside a STDIO server writes into the same stream
carrying protocol messages and corrupts it. This is not theoretical — it
produces `Failed to parse JSONRPC message from server` the moment the tool
runs. Send all narration to `stderr` instead:

```python
print(f"Event recorded: {entry}", file=sys.stderr)   # safe
print(f"Event recorded: {entry}")                    # corrupts the protocol
```

## Streamable HTTP

The server is an ordinary HTTP service. Requests are POSTed to **one
endpoint**, and responses come back the same way.

```text
  ┌─────────────────┐                    ┌─────────────────────────┐
  │  agent process  │   POST /mcp        │  server process         │
  │                 │ ─────────────────> │  (started separately,   │
  │  (only knows    │                    │   stays running,        │
  │   a URL)        │ <───────────────── │   serves many callers)  │
  └─────────────────┘     response       └─────────────────────────┘
```

The default endpoint path is `/mcp` — which is why
`06_time_travel_agent_mcp_sse.py` connects to
`http://127.0.0.1:8000/mcp`.

This replaced an older arrangement that used **two** addresses: one to POST
requests to and a separate long-lived stream to receive replies on. Two
addresses meant a dropped connection was awkward to recover from; folding
both directions into one endpoint fixed that. You will still see the older
two-endpoint style in tutorials and in some running servers, and the Python
CLI still accepts it as a transport name, but new work should not use it.

One oddity worth knowing so it does not confuse you while debugging: a plain
`GET /mcp` does not return a tidy "method not allowed" — it hangs, holding a
stream open.

## Choosing Between Them

| | STDIO | Streamable HTTP |
|---|---|---|
| How the server starts | Your agent launches it as a subprocess | You start it yourself, separately, ahead of time |
| Terminals needed | 1 | 2 (one for the server, one for the agent) |
| Reachable over a network | No | Yes |
| Callers at once | One | Many |
| State between agent runs | Gone every run (new process each time) | Survives while the server keeps running |
| Best for | Local dev, private tools | Shared tools, cloud deploys, several agents |

A given server is one or the other at a time, not both. What real systems do
is connect to **several servers at once** — a local filesystem one over
STDIO, a shared search one over HTTP — and the agent treats them all
identically. That mix is what people mean by "hybrid," not any single server
being hybrid.

---

# 6: Building Your First Server

The smallest useful server is a class, a decorator, and a function:

```python
from mcp.server import MCPServer

mcp = MCPServer("Research Tools")        # the server, and its name

@mcp.tool()                               # publish the function as a tool
def get_research_sources() -> list[str]:
    """Provides a list of research sources"""
    return ["Wikipedia", "Google", "YouTube"]

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

`@mcp.tool()` does the work you would otherwise do by hand: it reads the
function's signature, docstring, and return type, and turns them into the
tool description a model reads. The signature becomes the parameter list,
the docstring becomes the "when should I use this," and the return type tells
the client what shape to expect.

**The class name.** In the current SDK the class is `MCPServer`. An older
name for the same thing was `FastMCP`, imported from `mcp.server.fastmcp`;
that module now raises `ModuleNotFoundError` with a pointer to the migration
guide, so code using it will not silently misbehave — it will refuse to
start.

## One Server, Either Transport

A neat pattern, used in `01_claude_mcp_server.py` and
`06_mcp_time_travel_tracker.py`: let an environment variable pick the
transport, so one file serves both ways.

```python
if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "streamable-http":
        mcp.run(transport="streamable-http", host="127.0.0.1",
                port=8000, stateless_http=True)
    else:
        mcp.run(transport="stdio")
```

There is a subtlety here worth internalizing, because it explains behavior
that otherwise looks impossible. When you run `mcp run <file>`, that command
**imports your file as a module, finds the `mcp` object, and calls `.run()`
on it itself.** Your `if __name__ == "__main__":` block never executes. So:

```text
  python 06_mcp_time_travel_tracker.py        mcp run 06_mcp_time_travel_tracker.py
            │                                          │
            v                                          v
   __main__ block RUNS                        __main__ block SKIPPED
   env var respected                          always the CLI's own default
   (stdio, or streamable-http)                 (stdio)
```

Which is why the HTTP path needs `MCP_TRANSPORT=streamable-http python
<file>` and not `mcp run`.

## Running It

```bash
# start it over STDIO (waits quietly for a client on stdin/stdout)
python 01_claude_mcp_server.py

# start it as a real HTTP server on :8000
MCP_TRANSPORT=streamable-http python 01_claude_mcp_server.py

# or let the CLI run it, with an explicit transport
mcp run -t stdio 01_claude_mcp_server.py
```

A STDIO server started by hand looks like nothing is happening. That is
correct — it is waiting for a client to speak to it on stdin. To actually
poke at it, use the Inspector.

---

# 7: Seeing Inside a Server: The Inspector and Logging

## The Inspector

`mcp dev` starts your server *and* a browser-based debugging UI in front of
it:

```bash
mcp dev 01_claude_mcp_server.py
```

It prints a local URL. Open it and you get the live tool list exactly as a
model would see it — names, descriptions, parameters, return types — plus a
button to call any tool with arguments you choose, and a view of the raw
JSON-RPC traffic.

This is the first thing to reach for when a tool "is not working." Most of
the time the tool is fine and the *description* is the problem: the model
never picked it because the docstring did not tell it to. The Inspector shows
you what the model actually reads, which is not always what you thought you
wrote.

## Logging, and Why Your Prints Vanish

Two places your output can go, and it matters which you pick:

```text
   your tool function
        │
        ├── print(..., file=sys.stderr) ──> the terminal that launched the
        │                                   server (mixed in with the
        │                                   Inspector's own startup messages)
        │
        └── write to a log file ──────────> a file on disk, which you can
                                            watch live with `tail -f`
```

The file approach is the reliable one when you are clicking around in a
browser UI and not watching a terminal. A small helper is enough:

```python
def log(output: str, file_name: str = "server_output.log"):
    """Log output to a file"""
    with open(file_name, "a") as log_file:
        log_file.write(output + "\n")
```

Then, in a second terminal:

```bash
tail -f server_output.log
```

Every tool, resource, and prompt call shows up there the instant it happens.
One detail that trips people up: that filename is **relative to wherever you
ran the command from**, not to where the script lives. If you cannot find the
log, that is usually why.

---

# 8: Connecting a Server to an Agent

On the agent side there are two classes, matching the two transports:

```python
from agents.mcp import MCPServerStdio, MCPServerStdioParams   # subprocess
from agents.mcp import MCPServerStreamableHttp                # over HTTP
```

A third, `MCPServerSse`, still exists for the older two-endpoint style. Its
transport is deprecated; do not start new work with it.

## Over STDIO

```python
async def main():
    async with MCPServerStdio(
        params=MCPServerStdioParams(command="mcp", args=["run", str(SCRIPT)]),
    ) as server:
        agent = Agent(
            name="Assistant",
            instructions="Use the research tools to perform research.",
            model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
            mcp_servers=[server],          # <- the one new argument
        )
        result = await Runner.run(agent, "Get the available research sources")
        print(result.final_output)

asyncio.run(main())
```

Four things are happening, and only two of them are new:

`command="mcp", args=["run", str(SCRIPT)]` is literally the shell command
`mcp run <that file>`, written as a list. Python runs it for you as a
subprocess.

`async with ... as server` starts that subprocess now and shuts it down
cleanly when the block ends. Everything the agent does happens inside the
block, while the server is alive.

`mcp_servers=[server]` is the only new `Agent` argument compared to chapter
2. Where `tools=[my_function]` gave the agent one local function, this gives
it a whole server, and the agent discovers every tool on it by itself — you
never list them by name.

`await Runner.run(...)` is the async twin of `Runner.run_sync(...)`. You need
it because you are inside `async def main()`.

**Why async at all?** Not a style choice. `MCPServerStdio` is an async
context manager, so it can only be opened with `async with`, and `await` is
only legal inside an `async def`. Hence the `async def main()` /
`asyncio.run(main())` wrapper on every one of these files. It is fixed
scaffolding, identical every time.

## Over Streamable HTTP

```python
async def main():
    async with MCPServerStreamableHttp(
        params={"url": "http://127.0.0.1:8000/mcp"},
    ) as server:
        ...
```

Notice there is no `command` and no `args` — only a `url`. This agent does
not start the server. It assumes the server is **already running somewhere**
and connects to it, the way a browser connects to a website. So this path
takes two terminals:

```bash
# terminal 1 — start the server, leave it running
MCP_TRANSPORT=streamable-http python 06_mcp_time_travel_tracker.py

# terminal 2 — run the agent against it
python 06_time_travel_agent_mcp_sse.py
```

## Servers You Did Not Write

Because the protocol is language-agnostic, third-party servers work the same
way. `04_mcp_agent_local_server_files.py` reaches a Node.js filesystem
server:

```python
async with MCPServerStdio(
    name="Filesystem Server, via npx",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", current_dir],
    },
) as server:
```

`npx` fetches and launches it on first run. Your Python code does not know or
care that the thing on the other end is JavaScript, or which protocol
revision it speaks — the client adapts.

That server can read, write, and delete inside whatever directory you hand
it. Choose that directory deliberately.

---

# 9: Moving In-Process Tools Out to a Server

The clearest way to feel what MCP changes is to take working tools and move
them out without changing what they do. That is the journal example, in four
files.

## Before: Tools in the Agent's Own File

```python
_journal = []

@function_tool
def record_event(entry: str) -> dict:
    _journal.append(entry)
    return {"status": "recorded", "entry": entry}

agent = Agent(..., tools=[record_event, load_journal])
```

One process, one file. `_journal` is a plain list the agent's own code could
reach into directly.

## After: The Same Tools, Served

```python
mcp = MCPServer("Time Travel Tracker")
_journal = []

@mcp.tool()                                   # was @function_tool
def record_event(entry: str) -> dict:
    """Add a new travel event to the journal."""
    _journal.append(entry)
    print(f"Event recorded: {entry}", file=sys.stderr)   # was plain print
    return {"status": "recorded", "entry": entry}
```

Two lines changed: the decorator, and where the narration goes. The function
body is untouched.

## What Actually Changed, Though

It looks like copy-and-paste. It is an architectural shift:

```text
BEFORE                              AFTER

┌─────────────────────────┐         ┌───────────────┐      ┌───────────────┐
│ one process             │         │ agent process │      │ server process│
│                         │         │               │ MCP  │               │
│  agent  <──>  _journal  │         │  agent  ──────┼─────>│  _journal     │
│  (can see the list)     │         │  (sees only a │      │  (private)    │
│                         │         │   tool name)  │      │               │
└─────────────────────────┘         └───────────────┘      └───────────────┘
```

Afterward the agent sees a tool name, a description, a parameter schema, and
a return type. It cannot see the implementation, and does not need to. The
journal could become a Postgres table or a remote API and **no line of agent
code would change.** That is the payoff: the tool schema is the contract, and
the implementation is the server's private business.

## The Consequence Nobody Warns You About

Where state lives changes what sharing means:

- Over **STDIO**, a fresh subprocess starts every run, so `_journal` is empty
  every single time.
- Over **HTTP**, the server keeps running between runs, so the journal
  persists — and if two agents connect at once, they are writing to *the same
  list*.

Neither is wrong; they are different shapes with different correctness
properties. Just know which one you picked. A module-level list is fine for a
single local agent and is not the right shape for a shared deployment.

A fuller walkthrough of these four files, with exact run commands, lives
alongside the code in `code/ch03/solutions/time_travel_mcp_walkthrough.md`.

---

# 10: When a Tool Needs to Ask a Question Back

Sometimes a tool cannot finish without more information — a missing
parameter, or a confirmation before doing something irreversible. In a
session-based world, the server would push a question down a held-open
connection. With no sessions and no held connections, that is not possible,
so the pattern is inverted.

**MRTR** (Multi Round-Trip Requests) works like this: the tool answers with
`resultType: "input_required"` plus the questions it needs answered. The
client asks the user, then **reissues the same call** with the answers
attached.

```text
  CLIENT                                      SERVER
    │                                            │
    │  tools/call  place_order(id=42)            │
    │ ─────────────────────────────────────────> │
    │                                            │ needs confirmation
    │  <─────────────────────────────────────── │
    │   resultType: "input_required"             │
    │   + "Confirm total of $91.20?"             │
    │                                            │
    │  (client asks the user)                    │
    │                                            │
    │  tools/call  place_order(id=42)            │
    │              + inputResponses              │
    │ ─────────────────────────────────────────> │
    │                                            │ proceeds
    │  <─────────────────────────────────────── │
    │                  result                    │
```

Two calls, both self-contained, no connection held open in between. In the
Python SDK the first response is an `InputRequiredResult` carrying a plain
dict of requests, and on the retry your handler reads
`ctx.input_responses["key"].action`.

There is a security detail here that the SDK handles for you, and it is worth
knowing so you do not reimplement it: anything you stash in `request_state`
between the two calls is **encrypted and bound to the request** — the SDK
seals the method, tool name, and a hash of the arguments together, and
rejects any retry where those differ, before your handler runs. So a retry
cannot quietly swap the order id while reusing an approval. Do not hand-roll
an arguments digest; it is already done.

---

# 11: What Is Deprecated, and What Replaced It

You will run into all of these in older code and older tutorials.

| Old thing | Status | What to do instead |
|---|---|---|
| `initialize` / `initialized` handshake | Removed | Nothing — just send your request, with `_meta` in `params` |
| `Mcp-Session-Id` header and protocol sessions | Removed | Nothing; requests are independent |
| Two-endpoint HTTP streaming (separate POST and stream addresses) | Deprecated | Streamable HTTP, single `/mcp` endpoint |
| Server-initiated requests (elicitation, sampling, roots list) | Replaced | MRTR, section 10 |
| **Roots**, **Sampling**, **Logging** | Deprecated, ≥12-month window | Keep working for now; do not adopt in new servers |
| Blocking `tasks/result`, and `tasks/list` | Removed | Poll `tasks/get`; `tasks/update` sends input. Tasks now live in an extension, not the core |
| `FastMCP` from `mcp.server.fastmcp` | Renamed | `MCPServer` from `mcp.server` |

A genuinely useful side effect of MRTR: **there are now zero server-to-client
requests.** All traffic is client-initiated. If you are reasoning about
security or writing a gateway, that is a big simplification — nothing arrives
from the server side unprompted.

The deprecation window is a real promise, not a vague one: a feature marked
deprecated must stay available for at least twelve months from the release
that marked it before it can be removed. So deprecated is "plan your
migration," not "it breaks tomorrow."

## A Note on Error Behavior

Worth knowing before you debug something confusing, because these are not
uniform across the three primitives:

For **tools**, an unknown tool name comes back as a normal result with
`isError: true` — not a JSON-RPC error. A bare Python exception has its
message *withheld* from the model (the traceback goes to stderr); raise
`ToolError` if you want the model to read the message. Schema-validation
messages are forwarded in full.

For **resources**, the same disclosure boundary exists but uses real
JSON-RPC errors: a bare exception gives `-32603` withheld, `ResourceError`
gives `-32603` forwarded, and `ResourceNotFoundError` gives `-32602`
forwarded.

For **prompts**, there is no dedicated error type at all, and everything
except `MCPError` — including pydantic argument validation — is flattened
into an opaque `-32603 "Internal server error"`. If you want a useful message
out of a prompt handler, raise `MCPError` explicitly. Also: prompt arguments
arrive as **strings** on the wire (`"true"`, not `true`), and your type hints
do the coercion.

---

# 12: What Agency Actually Costs

An assistant that calls one wrong tool gives one wrong answer. An agent that
calls one wrong tool can chain that mistake into ten more before anyone
looks. Adding a server to an agent is adding capability *and* risk, and the
risk is broader than "it might delete a file."

**Destructive actions.** An agent with write or delete access will
eventually write or delete something you wish it had not. Filesystems,
databases, version control, cloud resources.

**Data exfiltration.** An agent that can both read sensitive data and send
messages can be talked into combining those two abilities.

**Cost runaways.** A stuck loop calling paid tools can spend a lot of money
before monitoring notices.

**Prompt injection through tool output.** This is the important one. Anything
a tool returns becomes part of the model's context, and text in a web page,
document, or email can contain instructions the model will follow. Treat this
as the **default condition** for any tool returning external content, not an
edge case.

The defenses are unglamorous and they work: allowlist which tools an agent
can even see; sandbox anything touching the filesystem or a shell; validate
tool output against an expected shape before the agent acts on it; cap rate
and spend so a runaway hits a ceiling; and require a human confirmation for
irreversible actions. MRTR (section 10) is the protocol-level way to do that
last one.

Understanding what your servers can do is the floor, not the ceiling.

---

# 13: Chapter 3 Code Map

All under `code/ch03/` (`template/` pristine, `solutions/` your own work,
`solved/` the worked answers).

| File | What it demonstrates |
|---|---|
| `01_claude_mcp_server.py` | Smallest server, one tool; dual-transport `__main__` |
| `01_complete_mcp_server.py` | All three primitives — resource, tool, prompt — in one server |
| `01_complete_agent.py` | An agent reaching that three-primitive server over STDIO |
| `02_mcp_agent_stdio_server.py` | Agent + server over STDIO, minimal version |
| `03_mcp_agent_sse_server.py` | The HTTP path: `MCPServerStreamableHttp` against a separately-started server |
| `04_mcp_agent_local_server_files.py` | Consuming a third-party Node.js server through `npx` |
| `05_time_travel_agent.py` | The "before": journal tools as plain `@function_tool` |
| `06_mcp_time_travel_tracker.py` | The same tools, now an MCP server |
| `06_time_travel_agent_mcp_stdio.py` | Reaching the tracker over STDIO (1 terminal) |
| `06_time_travel_agent_mcp_sse.py` | Reaching the tracker over Streamable HTTP (2 terminals) |
| `time_travel_mcp_walkthrough.md` | Line-by-line walkthrough of the journal set |

---

# 14: Key Takeaways

MCP exists to turn a multiplying problem into an additive one: write each
tool once, use it from any agent in any language, instead of writing glue per
provider-and-tool pair. It does not solve auth, error handling, or keeping
your server running.

Three roles: a **client** connects and asks (an agent is one kind), a
**server** owns and exposes capabilities, and a **service** is whatever real
system sits behind it. Messages are ordinary JSON-RPC 2.0, which is why the
two sides never need to share a programming language.

A server can expose **tools** (the model decides to call them), **resources**
(data at an address, a person attaches them), and **prompts** (templates a
person picks). The OpenAI Agents SDK consumes tools only — if your agent
needs it, make it a tool.

The protocol is **stateless**. No handshake, no session id, nothing
remembered between requests. Each request carries its own protocol version
and capabilities in `_meta` inside `params`, HTTP requests carry `Mcp-Method`
(and `Mcp-Name` where something is targeted by name), `server/discover`
exists for optional up-front capability lookup, and list-style results carry
`ttlMs`/`cacheScope` so answers can be cached. Practically: plain load
balancers and serverless deployments now work. In the Python SDK,
`stateless_http` defaults to `False` — opt in, or get a confusing
`"Missing session ID"` 400.

Two transports carry identical messages. **STDIO** is a subprocess, private
and one-to-one, and its `stdout` is the protocol channel — narrate to
`stderr` or you will corrupt it. **Streamable HTTP** is a normal HTTP service
on a single `/mcp` endpoint, reachable by many callers, and it replaced an
older two-address streaming arrangement you will still see in the wild.

`@mcp.tool()` publishes a function by reading its signature, docstring, and
return type — so the docstring is model-facing documentation, not a comment.
On the agent side, `mcp_servers=[server]` replaces listing tools by name, and
the `async def main()` / `asyncio.run(main())` wrapper is required
scaffolding, not decoration.

Moving tools out of the agent's process does not change what they do; it
changes who can see the implementation (nobody) and where the state lives
(the server) — which quietly changes whether that state is per-run or shared.

When a tool needs input mid-call, **MRTR** handles it with two independent
calls rather than a held-open connection, and the SDK cryptographically binds
anything you carry between them so an approval cannot be replayed against
different arguments.

Finally: every tool you add is a decision you have delegated. Prompt
injection through tool output is the default condition, not the edge case,
and allowlisting, sandboxing, output validation, spend caps, and
human-in-the-loop confirmation are the things that actually help.
