# Topic 3 — Model Context Protocol (MCP): Code Explanation

This file walks through every cell of `03-mcp-fundamentals.ipynb` and the
standalone `mcp_server.py`, showing the actual output each cell produces and
— for the two exercises (`build_mcp_agent_graph` and `add_note`) — the
canonical implementation with a line-by-line explanation and a dry run.

For the *why* behind each concept (protocol basics, transports, the security
model), see [`../../notes/03-model-context-protocol-mcp.md`](../../notes/03-model-context-protocol-mcp.md)
and the topic plan,
[`../../../03-model-context-protocol-mcp.md`](../../../03-model-context-protocol-mcp.md).
This file stays close to the code.

---

## Table of Contents

- [1. Protocol Basics](#1-protocol-basics)
- [2. Building a Minimal MCP Server](#2-building-a-minimal-mcp-server)
- [3. Running & Inspecting the Server](#3-running--inspecting-the-server)
- [4. Connecting a Client](#4-connecting-a-client)
  - [Exercise 1 — `build_mcp_agent_graph`](#exercise-1--build_mcp_agent_graph)
  - [Exercise 2 — `add_note`](#exercise-2--add_note)
- [5. Transports](#5-transports)
- [6. Security Model](#6-security-model)
- [Putting It All Together](#putting-it-all-together)
- [Where to Go Next](#where-to-go-next)

---

## 1. Protocol Basics

```python
tool_description = types.Tool(
    name="search_notes",
    description="Search the learning notes database for a topic and return its content.",
    inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)

resource_description = types.Resource(
    name="topics",
    uri="notes://topics",
    description="List every topic available in the learning notes database.",
    mimeType="text/plain",
)

prompt_description = types.Prompt(
    name="summarize_note",
    description="Summarize a learning note in one sentence.",
    arguments=[types.PromptArgument(name="topic", description="The topic to summarize", required=True)],
)

print("TOOL primitive:")
print(json.dumps(tool_description.model_dump(exclude_none=True), indent=2))
# ... RESOURCE and PROMPT printed the same way
```

Output:

```
TOOL primitive:
{
  "name": "search_notes",
  "description": "Search the learning notes database for a topic and return its content.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string"
      }
    },
    "required": [
      "query"
    ]
  }
}

RESOURCE primitive:
{
  "name": "topics",
  "uri": "notes://topics",
  "description": "List every topic available in the learning notes database.",
  "mimeType": "text/plain"
}

PROMPT primitive:
{
  "name": "summarize_note",
  "description": "Summarize a learning note in one sentence.",
  "arguments": [
    {
      "name": "topic",
      "description": "The topic to summarize",
      "required": true
    }
  ]
}
```

`mcp.types.Tool`, `Resource`, and `Prompt` are pydantic models that mirror the
JSON shapes the MCP spec defines for `tools/list`, `resources/list`, and
`prompts/list` responses respectively. `model_dump(exclude_none=True)` drops
fields that weren't set (e.g. `Tool.title`, `Tool.outputSchema`), so the
printed JSON shows only the fields this notebook actually populated.
`Resource.uri` is a pydantic `AnyUrl`, which is why its dump needs
`mode="json"` to serialize as the plain string `"notes://topics"` rather than
a `Url` object repr.

Three things to notice: a **tool**'s `inputSchema` is exactly the JSON Schema
shape Topic 1 covered for `bind_tools` — `{"type": "object", "properties": {...},
"required": [...]}`. A **resource** is identified by a `uri`
(`"notes://topics"` is a made-up scheme specific to this server — MCP doesn't
mandate particular URI schemes) and optionally a `mimeType` describing the
shape of its content. A **prompt** has `arguments`, each with its own `name`,
`description`, and `required` flag — structurally similar to a tool's input
schema, but describing a *prompt template's* parameters rather than a
function call's.

---

## 2. Building a Minimal MCP Server

```python
demo_mcp = FastMCP("demo")


@demo_mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two integers together."""
    return a + b


demo_tools = await demo_mcp.list_tools()
for demo_tool in demo_tools:
    print("name:", demo_tool.name)
    print("description:", demo_tool.description)
    print("input_schema:", demo_tool.inputSchema)

content, structured = await demo_mcp.call_tool("add_numbers", {"a": 3, "b": 4})
print("\ncall_tool result:")
print("content:", content)
print("structured:", structured)
```

Output:

```
name: add_numbers
description: Add two integers together.
input_schema: {'properties': {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}, 'required': ['a', 'b'], 'title': 'add_numbersArguments', 'type': 'object'}

call_tool result:
content: [TextContent(type='text', text='7', annotations=None, meta=None)]
structured: {'result': 7}
```

`@demo_mcp.tool()` reads `add_numbers`'s signature (`a: int, b: int`) and
docstring to build a `Tool` description — `inputSchema.properties.a.type ==
"integer"` comes directly from the `int` type hint, and `description` comes
verbatim from the docstring. This is the *server-side* mirror of Topic 1's
`@tool` decorator: there, `@tool` produced a `BaseTool` for a single
process's `ToolNode`; here, `@demo_mcp.tool()` produces a `Tool` description
that *any* MCP client, in any language, can discover via `tools/list`.

`await demo_mcp.call_tool(...)` returns a 2-tuple: `content` is the list of
content blocks (here, one `TextContent` with `text='7'` — note it's the
*string* `"7"`, not the integer `7`, since MCP tool results are always
serialized as content blocks) and `structured` is `{"result": 7}` — a
separate "structured content" channel that preserves the original Python
return type for clients that want to use it programmatically, alongside the
human/model-readable text representation.

This `demo_mcp` instance never calls `.run(...)` — it answers `list_tools`
and `call_tool` directly, in-process, with no transport at all. That's useful
for understanding the decorator, but Section 3 needs the real thing: a
*separate process* speaking JSON-RPC over stdio, which is what `mcp_server.py`
is for.

### `mcp_server.py`

The full source is reproduced by the notebook's `print(Path("mcp_server.py").read_text())`
cell (omitted here for brevity — see the file directly). Three things from it
are worth calling out up front, since they're referenced throughout the rest
of this file:

- `mcp = FastMCP("learning-notes", log_level="ERROR")` — `log_level="ERROR"`
  suppresses FastMCP's per-request `INFO` logging (e.g. `"Processing request
  of type ListToolsRequest"`), which would otherwise print to stderr for
  every single `tools/list` / `tools/call` / etc. and clutter the notebook's
  output.
- `DB_PATH = Path(__file__).parent / "learning_notes.db"` — the database
  lives next to `mcp_server.py`, not in some global location, and
  `init_db()` runs at **import time** (i.e. every time the server process
  starts), using `INSERT OR REPLACE` so re-seeding the five built-in `NOTES`
  is idempotent and doesn't clobber any *additional* rows `add_note` may have
  written in a previous run.
- `search_notes` is annotated `ToolAnnotations(readOnlyHint=True,
  openWorldHint=False)` and `add_note` is annotated
  `ToolAnnotations(destructiveHint=True, idempotentHint=False)` — these are
  discussed in [Section 6](#6-security-model).

---

## 3. Running & Inspecting the Server

```python
server_params = StdioServerParameters(command="python3", args=["mcp_server.py"])

async with stdio_client(server_params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        init_result = await session.initialize()
        print("server name:", init_result.serverInfo.name)
        print("protocol version:", init_result.protocolVersion)
        # ... list_tools, list_resources, call_tool x2, read_resource
```

Output:

```
server name: learning-notes
protocol version: 2025-11-25

--- list_tools ---
name: search_notes
description: Search the learning notes database for a topic and return its content.
name: add_note
description: Add or update a note in the learning notes database.

    1. Open a sqlite3 connection to DB_PATH.
    2. Run "INSERT OR REPLACE INTO notes (topic, content) VALUES (?, ?)" with
       (topic.lower(), content) as parameters, then commit and close.
    3. Return a confirmation string, e.g. f"Saved note for topic '{topic}'."
    

--- list_resources ---
uri: notes://topics
name: list_topics
description: List every topic available in the learning notes database.

--- call_tool: search_notes(query='langgraph') ---
isError: False
content: LangGraph is a library for building stateful, multi-step LLM applications as graphs of nodes and edges.

--- call_tool: search_notes(query='quantum gravity') ---
content: No results found.

--- read_resource: notes://topics ---
text: attention, checkpointer, langgraph, mcp, react
```

`StdioServerParameters(command="python3", args=["mcp_server.py"])` describes
*how to start* the server — it does not start it yet. `stdio_client(server_params)`
is an async context manager that spawns `python3 mcp_server.py` as a
subprocess and yields `(read_stream, write_stream)` wired to that process's
stdout/stdin. `ClientSession(read_stream, write_stream)` wraps those streams
with the MCP protocol; `await session.initialize()` performs the handshake —
the server responds with `serverInfo.name == "learning-notes"` (the string
passed to `FastMCP(...)`) and `protocolVersion == "2025-11-25"` (the MCP
spec version this `mcp` SDK release implements).

Note that `add_note`'s full docstring — including its three numbered
implementation steps — is printed as its `description`. `FastMCP` uses a
function's *entire* docstring as the tool description by default; for a
finished tool you'd typically write a one-line description, but leaving the
exercise instructions in the docstring means they're visible to *any* MCP
client introspecting this server, including the agent in Section 4.

`search_notes(query="quantum gravity")` returns `"No results found."` — the
same fallback string as Topic 2's `search_index`, since `mcp_server.py`'s
`search_notes` does the identical substring lookup, just against SQLite rows
instead of a Python dict.

### Raw JSON-RPC for one `tools/call`

```python
request = {
    "jsonrpc": "2.0",
    "id": 99,
    "method": "tools/call",
    "params": {"name": "search_notes", "arguments": {"query": "react"}},
}
print("request:")
print(json.dumps(request, indent=2))

# ... spawn the server, call session.call_tool("search_notes", {"query": "react"}) ...

response = {
    "jsonrpc": "2.0",
    "id": 99,
    "result": {
        "content": [{"type": block.type, "text": block.text} for block in result.content],
        "isError": result.isError,
    },
}
print("\nresponse:")
print(json.dumps(response, indent=2))
```

Output:

```
request:
{
  "jsonrpc": "2.0",
  "id": 99,
  "method": "tools/call",
  "params": {
    "name": "search_notes",
    "arguments": {
      "query": "react"
    }
  }
}

response:
{
  "jsonrpc": "2.0",
  "id": 99,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "The ReAct pattern interleaves reasoning (LLM thoughts) with acting (tool calls) in a loop."
      }
    ],
    "isError": false
  }
}
```

The `request` dict here is constructed by hand — it is **not** what
`session.call_tool(...)` literally sends (the SDK builds and serializes the
real JSON-RPC message internally over the stdio pipe), but it shows the exact
shape of that message: `method: "tools/call"`, and `params` carrying the tool
`name` and its `arguments` dict (which must match `search_notes`'s
`inputSchema` — a `query` string). The `response` dict is built from the
*actual* `CallToolResult` returned by `session.call_tool(...)`:
`result.content` is a list of content blocks (`block.type` and `block.text`
for each `TextContent`), and `result.isError` is `False` for a successful
call. The `id: 99` is shared between request and response — in a real
JSON-RPC exchange, the client picks this value and uses it to match the
response when it arrives, regardless of how many other requests are
in flight.

---

## 4. Connecting a Client

```python
client = MultiServerMCPClient({
    "learning_notes": {
        "transport": "stdio",
        "command": "python3",
        "args": ["mcp_server.py"],
    }
})

mcp_tools = await client.get_tools()
for mcp_tool in mcp_tools:
    print("tool:", mcp_tool.name, "-", mcp_tool.description)
```

Output:

```
tool: search_notes - Search the learning notes database for a topic and return its content.
tool: add_note - Add or update a note in the learning notes database.

    1. Open a sqlite3 connection to DB_PATH.
    2. Run "INSERT OR REPLACE INTO notes (topic, content) VALUES (?, ?)" with
       (topic.lower(), content) as parameters, then commit and close.
    3. Return a confirmation string, e.g. f"Saved note for topic '{topic}'."
    
```

`MultiServerMCPClient({"learning_notes": {...}})` is a small registry of
named server connections — `"learning_notes"` here is a label *we* chose,
used later in [Exercise 2](#exercise-2--add_note) to open a session against
this specific server. `await client.get_tools()` connects to every configured
server, runs `tools/list` on each, and wraps each `Tool` description (the
same `Tool` objects from Section 1/3) in a LangChain `BaseTool`. The result —
`mcp_tools`, a `list[BaseTool]` containing `search_notes` and `add_note` — is
exactly the kind of list Topic 2's `ToolNode([web_search])` expected, just
sourced from a subprocess instead of a local `@tool`-decorated function.

### Exercise 1 — `build_mcp_agent_graph`

#### The docstring (as given in the template)

> Build a 2-node agent/tools LangGraph app using MCP-loaded tools.
>
> 1. Define `agent_node(state)` that returns
>    `{"messages": [llm.invoke(state["messages"])]}`.
> 2. Build a `StateGraph(AgentState)`: add `"agent"` (`agent_node`) and
>    `"tools"` (`ToolNode(tools)`) nodes.
> 3. Wire `START -> "agent"`, `"agent" -> (tools_condition) -> "tools"` or
>    `END`, and `"tools" -> "agent"`.
> 4. Compile and return the app.

#### Canonical implementation

```python
def build_mcp_agent_graph(tools, llm):
    def agent_node(state: AgentState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()
```

**What each line does**:

- `def agent_node(state: AgentState) -> dict` — defined *inside*
  `build_mcp_agent_graph` so it closes over the function's `llm` parameter,
  letting the same graph-building function be reused with different models
  (or, as here, the same `GenericFakeChatModel` instance across notebook
  cells) without hardcoding a global.
- `graph.add_node("tools", ToolNode(tools))` — `tools` is whatever list
  `get_tools()` returned (`[search_notes, add_note]`); `ToolNode` dispatches
  each `tool_call` in the latest `AIMessage` to the matching `BaseTool` by
  name and wraps each result in a `ToolMessage` — identical to Topic 2
  Section 3, just with MCP-backed tools.
- `graph.add_conditional_edges("agent", tools_condition)` — no explicit
  mapping argument, exactly as in Topic 2: `tools_condition` returns either
  `"tools"` (if the latest `AIMessage.tool_calls` is non-empty) or `END`
  directly.
- `return graph.compile()` — returns the compiled `CompiledStateGraph`. If
  this function is left as `pass` (returns `None`), the demo cell below
  detects that and skips invocation rather than calling `.ainvoke()` on
  `None`.

#### Dry run

```python
agent_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[{"name": "search_notes", "args": {"query": "mcp"}, "id": "call_1"}]),
    AIMessage(content="MCP standardizes how LLM apps access external tools, data, and prompts."),
]))

mcp_agent_app = build_mcp_agent_graph(mcp_tools, agent_llm)
result = await mcp_agent_app.ainvoke({"messages": [HumanMessage(content="What is MCP?")]})
for message in result["messages"]:
    print(type(message).__name__, "|", repr(message.content))
```

Output (canonical implementation):

```
HumanMessage | 'What is MCP?'
AIMessage | ''
ToolMessage | [{'type': 'text', 'text': 'The Model Context Protocol standardizes how LLM applications connect to external tools, data, and prompts.', 'id': 'lc_e6474be9-7043-4cee-af37-47337f6fbcc0'}]
AIMessage | 'MCP standardizes how LLM apps access external tools, data, and prompts.'
```

`agent_llm` is scripted with two responses, mirroring Topic 2 Section 3
exactly: first a tool-call `AIMessage` (empty `content`, `tool_calls`
requesting `search_notes(query="mcp")`), then a final plain-text answer.
**agent** runs (1st `agent_llm` call), `tools_condition` sees a non-empty
`tool_calls` and routes to **tools**. `ToolNode` calls the MCP-backed
`search_notes` tool — which spawns `mcp_server.py` as a subprocess, sends a
`tools/call` request, and gets back `result.content =
[{"type": "text", "text": "The Model Context Protocol standardizes..."}]`.
Crucially, **this `ToolMessage.content` is a list of dicts**, not a plain
string: `langchain-mcp-adapters` preserves MCP's content-block structure
rather than collapsing a single text block to a bare string (Topic 2's
in-process `web_search` returned a plain string, so its `ToolMessage.content`
was a plain string too). The plain edge `tools -> agent` runs **agent** again
(2nd `agent_llm` call), producing the final `AIMessage` with `tool_calls ==
[]`, so `tools_condition` returns `END`.

### About the unsolved template

With `build_mcp_agent_graph` left as `pass` (returning `None`), the demo cell
checks `if mcp_agent_app is None` and prints
`"Exercise not yet solved -- build_mcp_agent_graph returned None, skipping the agent run."`
instead of calling `.ainvoke()` on `None` (which would raise
`AttributeError`). The unsolved template therefore still executes cleanly
end-to-end — the output above is from the **canonical** implementation.

### Exercise 2 — `add_note`

#### The docstring (as given in the template, inside `mcp_server.py`)

> Add or update a note in the learning notes database.
>
> 1. Open a sqlite3 connection to `DB_PATH`.
> 2. Run `"INSERT OR REPLACE INTO notes (topic, content) VALUES (?, ?)"` with
>    `(topic.lower(), content)` as parameters, then commit and close.
> 3. Return a confirmation string, e.g. `f"Saved note for topic '{topic}'."`

#### Canonical implementation

```python
@mcp.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))
def add_note(topic: str, content: str) -> str:
    """Add or update a note in the learning notes database."""
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        "INSERT OR REPLACE INTO notes (topic, content) VALUES (?, ?)",
        (topic.lower(), content),
    )
    connection.commit()
    connection.close()
    return f"Saved note for topic '{topic}'."
```

**What each line does**:

- `connection = sqlite3.connect(DB_PATH)` — opens (or creates) the same
  `learning_notes.db` file that `init_db()` seeded at server startup; every
  tool call opens its own short-lived connection, mirroring `search_notes`
  and `list_topics`.
- `connection.execute("INSERT OR REPLACE INTO notes (topic, content) VALUES (?, ?)", (topic.lower(), content))`
  — parameterized SQL (the `?` placeholders) avoids SQL injection from the
  `topic`/`content` arguments, which ultimately come from model output.
  `INSERT OR REPLACE` means calling `add_note` again with the same `topic`
  *overwrites* the existing row rather than raising a primary-key conflict —
  this is exactly why the tool is annotated `idempotentHint=False`: two calls
  with the same arguments both "succeed," but the second one's effect (a
  fresh write) is not a true no-op the way a read-only idempotent operation
  would be.
- `connection.commit(); connection.close()` — persists the write to disk and
  releases the connection. Because `DB_PATH` is a real file
  (`learning_notes.db`, next to `mcp_server.py`), this write is visible to
  *any subsequent connection to the same server process or a freshly spawned
  one* — unlike Topic 2's `SEARCH_INDEX`, which was a Python dict that reset
  every time the process restarted.
- `return f"Saved note for topic '{topic}'."` — this string becomes the
  tool's `result.content[0].text` (wrapped in a `TextContent` block by
  `FastMCP` automatically).

#### Dry run

```python
client_2 = MultiServerMCPClient({
    "learning_notes": {"transport": "stdio", "command": "python3", "args": ["mcp_server.py"]}
})

async with client_2.session("learning_notes") as session:
    result = await session.call_tool(
        "add_note",
        {"topic": "transports", "content": "stdio is for local processes; streamable HTTP is for remote/shared servers."},
    )
    print("isError:", result.isError)
    for block in result.content:
        print("content:", block.text)

    if not result.isError:
        verify = await session.call_tool("search_notes", {"query": "transports"})
        for block in verify.content:
            print("verify:", block.text)
```

Output (canonical implementation):

```
isError: False
content: Saved note for topic 'transports'.
verify: stdio is for local processes; streamable HTTP is for remote/shared servers.
```

`client_2.session("learning_notes")` opens **one** persistent session (one
subprocess, one stdio connection) for both calls — unlike `get_tools()` in
Exercise 1, which wraps each tool independently. `add_note(topic="transports", ...)`
inserts a new row (note: `"transports"` was deliberately chosen so it's not a
substring of, and doesn't contain, any existing topic — `"mcp"` would have
been a bad choice, since `search_notes`'s substring match would find the
existing `"mcp"` row inside a query like `"mcp-transports"` first).
`search_notes(query="transports")` then finds and returns that *same* row's
content — round-tripping through `learning_notes.db`.

### About the unsolved template

With `add_note` left raising `NotImplementedError("add_note is not implemented yet")`,
`FastMCP` catches the exception inside the tool and returns a `CallToolResult`
with `isError=True` and `content=[TextContent(text="Error executing tool add_note: add_note is not implemented yet")]`
— **not** a raised exception on the client side. The demo cell's
`if not result.isError` branch is therefore never taken, and it prints
`isError: True`, the error message, and `"add_note is not implemented yet -- nothing to verify."`
instead — again, "ran without error, exercise not yet solved," not a crash.

---

## 5. Transports

```python
stdio_server_line = 'mcp.run(transport="stdio")'
http_server_line = 'mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)'

stdio_client_config = {"transport": "stdio", "command": "python3", "args": ["mcp_server.py"]}
http_client_config = {"transport": "streamable_http", "url": "http://localhost:8000/mcp"}
```

Output:

```
Server-side (mcp_server.py), last line only:
  stdio:           mcp.run(transport="stdio")
  streamable HTTP: mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)

Client-side connection config:
  stdio:           {'transport': 'stdio', 'command': 'python3', 'args': ['mcp_server.py']}
  streamable HTTP: {'transport': 'streamable_http', 'url': 'http://localhost:8000/mcp'}
```

This cell is **illustrative only** — it constructs and prints the two
configurations side by side without connecting to anything (no Streamable
HTTP server is started anywhere in this notebook, to keep everything offline
and dependency-free). The point is the *symmetry*: every server-side
primitive (`@mcp.tool()`, `@mcp.resource()`, `add_note`'s implementation) and
every client-side call (`session.call_tool(...)`, `session.read_resource(...)`)
from Sections 2-4 would be **completely unchanged** under Streamable HTTP —
only `mcp.run(...)`'s arguments and the connection dict's `transport`/`command`/`url`
fields differ. `MultiServerMCPClient`'s `connections` dict (Section 4) accepts
either shape per server, so a single client could even talk to one server over
stdio and another over Streamable HTTP simultaneously.

---

## 6. Security Model

```python
server_params = StdioServerParameters(command="python3", args=["mcp_server.py"])
async with stdio_client(server_params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            print(tool.name, "->", tool.annotations)
```

Output:

```
search_notes -> title=None readOnlyHint=True destructiveHint=None idempotentHint=None openWorldHint=False
add_note -> title=None readOnlyHint=None destructiveHint=True idempotentHint=False openWorldHint=None
```

These come straight from `mcp_server.py`'s decorators:
`@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))`
on `search_notes`, and
`@mcp.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))`
on `add_note`. `ToolAnnotations` is a pydantic model with five optional
fields (`title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`,
`openWorldHint`); printing one prints all five, with `None` for any field the
server didn't set.

`readOnlyHint=True, openWorldHint=False` on `search_notes` says: this tool
never modifies anything, and it only ever looks things up in a closed,
known set (the `notes` table) — a client could reasonably auto-approve every
call to it, the same way Claude Code doesn't prompt before `git status` or
reading a file. `destructiveHint=True, idempotentHint=False` on `add_note`
says: this tool can overwrite existing data, and calling it twice is *not*
equivalent to calling it once — exactly the profile that should make a
client pause for confirmation, the same way Claude Code prompts before an
`Edit` or a `Bash` command outside your auto-allow list. As the notes file
emphasizes, these are **hints** the server *declares about itself* — a
client is free to ignore them, and a misbehaving server could mislabel a
destructive tool as read-only. The actual safety net is the client's consent
policy (and the human behind it), not the annotation itself.

---

## Putting It All Together

```
notebook (client)                            mcp_server.py (separate process)
  |                                                |
  |-- initialize -------------------------------->|
  |<----------------------- serverInfo -----------|
  |-- tools/list --------------------------------->|
  |<--------- [search_notes, add_note] -----------|
  |-- tools/call(search_notes, {query}) --------->|
  |<------------------ result.content ------------|   SQLite: learning_notes.db
  |-- resources/read(notes://topics) ------------>|
  |<------------------ topic list -----------------|
  |                                                |
  |== via langchain-mcp-adapters ==>  ToolNode([search_notes, add_note])
  |                                       |
  |                              agent <-> tools  (Topic 2's cycle, unchanged)
```

Every section builds toward this picture. `mcp.types.Tool` / `Resource` /
`Prompt` (Section 1) are the *vocabulary* of `tools/list` and
`resources/list` responses. `FastMCP` decorators (Section 2) turn Python
functions into objects that speak that vocabulary. `StdioServerParameters` +
`stdio_client` + `ClientSession` (Section 3) are the *transport* and
*session* that carry JSON-RPC messages built from that vocabulary between
processes. `MultiServerMCPClient` + `langchain-mcp-adapters` (Section 4)
re-wrap that vocabulary as LangChain `BaseTool`s so Topic 2's `StateGraph` /
`ToolNode` / `tools_condition` machinery works unchanged. Sections 5-6 are the
two questions you ask before deploying any of this beyond your own laptop:
*how do clients reach this server* (transport), and *what should require a
human's okay* (security/consent).

---

## Where to Go Next

Topic 4 (AI Agent Patterns & Frameworks) takes this same stack — a
`StateGraph` agent (Topic 2) wired to an MCP tool server with a read-only and
a destructive tool (Topic 3) — and compares it against higher-level
frameworks (LangGraph's own prebuilt `create_react_agent`, CrewAI, the Claude
Agent SDK) that bundle the agent loop, tool wiring, and (in some cases) MCP
client configuration behind a single call. Having built the loop by hand
here, you'll be able to recognize exactly which pieces each framework is
doing *for* you — and what control you trade away to get that convenience.
