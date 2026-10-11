# Chapter 3 From Scratch: MCP With the Official Library

## Table of Contents

- [How This Folder Works](#how-this-folder-works)
- [Setup and Running](#setup-and-running)
- **Part 1: The Problems**
  - [Problem 01: Your First Server and Client](#problem-01-your-first-server-and-client)
  - [Problem 02: Tools, Resources, Prompts, and How Each One Fails](#problem-02-tools-resources-prompts-and-how-each-one-fails)
  - [Problem 03: What Actually Travels Over the Wire](#problem-03-what-actually-travels-over-the-wire)
  - [Problem 04: Two Servers, One Shopping Cart](#problem-04-two-servers-one-shopping-cart)
  - [Problem 05: Your Trip Planner, Now Powered by MCP](#problem-05-your-trip-planner-now-powered-by-mcp)
  - [Problem 06: One Agent, Many Servers](#problem-06-one-agent-many-servers)
  - [Problem 07: Big Lists: Pagination and Caching](#problem-07-big-lists-pagination-and-caching)
  - [Problem 08: Asking the User Mid-Call (MRTR)](#problem-08-asking-the-user-mid-call-mrtr)
  - [Problem 09: Progress Updates on Slow Tools](#problem-09-progress-updates-on-slow-tools)
  - [Problem 10 (Optional): Getting Told When Something Changes](#problem-10-optional-getting-told-when-something-changes)
- **Part 2: The Theory**
  - [Theory 01: Servers, Clients, and the STDIO Pipe](#theory-01-servers-clients-and-the-stdio-pipe)
  - [Theory 02: The Three Primitives and Their Error Rules](#theory-02-the-three-primitives-and-their-error-rules)
  - [Theory 03: The Request on the Wire](#theory-03-the-request-on-the-wire)
  - [Theory 04: What Stateless Really Means](#theory-04-what-stateless-really-means)
  - [Theory 05: Bridging MCP Into Your Own Agent Loop](#theory-05-bridging-mcp-into-your-own-agent-loop)
  - [Theory 06: Connecting to Several Servers at Once](#theory-06-connecting-to-several-servers-at-once)
  - [Theory 07: Cursors and Caches](#theory-07-cursors-and-caches)
  - [Theory 08: Multi Round-Trip Requests](#theory-08-multi-round-trip-requests)
  - [Theory 09: Progress Notifications](#theory-09-progress-notifications)
  - [Theory 10: Subscriptions and Where Statelessness Leaks](#theory-10-subscriptions-and-where-statelessness-leaks)
- [What Is Not Covered Here](#what-is-not-covered-here)

---

## How This Folder Works

Every problem in this chapter uses the **official `mcp` Python library** (version 2.1.1) for the protocol part: `MCPServer` on the server side and `mcp.client.Client` on the client side. You never write a JSON-RPC parser or an HTTP handler yourself, except once, in Problem 03, where you look at the raw wire on purpose so you know what the library is doing for you.

What you *do* still write by hand is the **agent**: the model call, turning MCP tools into OpenAI-style tool schemas, dispatching tool calls, and the reason-act-observe loop. That is the same work you did in chapter 2. So "from scratch" in this chapter means "the agent is yours", not "the protocol is yours".

Each problem has **two files: a server and a client**. The client always reaches the server through the protocol, never by importing it. That keeps the two sides honestly separate, exactly like in real use, where the server is often written by someone else.

**Which transport, where.** Problems 01 and 02 use **STDIO**: the client starts the server as a subprocess on the same machine. That is how local tools work (a desktop app or a CLI starting a server for itself), and it is the simplest way to meet the client and server for the first time. From Problem 03 on, every server runs as its own long-lived **stateless Streamable HTTP** service on a fixed port, and the client connects with a URL. That is the shape you deploy: a shared service many clients can reach, that can sit behind a load balancer. Problem 06 deliberately mixes both, because real agents often do. Theory 01 ends with a short comparison of the two.

The three folders mean the same thing as in chapter 2:

```text
from_scratch/
|-- PROBLEM_STATEMENT.md     <-- this file
|-- template/                pristine stubs, never edit
|-- solutions/               YOUR working copy, write code here
|-- solved/                  reference answers, look only after trying
```

Each problem below has a short "Read first" link pointing at its theory section in Part 2. If a problem feels unclear, scroll down and read that section before you start.

---

## Setup and Running

Everything runs from the repo's root virtual environment, which already has `mcp` 2.1.1, `openai`, `httpx`, and `python-dotenv` installed.

The model calls use the same `.env` as chapter 2:

```text
GEMINI_API_KEY=...            default provider
GEMINI_MODEL=gemini-3.5-flash-lite
```

Ollama (`qwen3:4b`) is the fallback, through its OpenAI-compatible endpoint at `http://localhost:11434/v1`. Only Problems 05, 06, 07 (part 3), and 08 call a model at all. Every other problem is plain client and server code with no model involved, so it costs nothing to run.

Problem 06 also uses Node.js (`npx`) to start a third-party filesystem server. Node is already installed on this machine.

### Running the HTTP Problems

An HTTP server is started on its own and keeps running; the client does not start it. So every problem from 03 on needs two terminals:

```text
Terminal 1:  python NN_something_server.py     (leave it running)
Terminal 2:  python NN_something_client.py     (or _agent.py)
```

If Terminal 1 is not running, the client fails with a connection error. That is the correct failure: start the server first. Each server has its own port, so you can leave several running at once without them clashing:

| Problem | Server | Port |
|---|---|---|
| 03 | `03_wire_server.py` | 8000 |
| 04 | `04_cart_server.py` (two replicas, started by the client) | 8001, 8002 |
| 05 | `05_trip_server.py` (also used by 06) | 8005 |
| 07 | `07_bookstore_server.py` | 8007 |
| 08 | `08_flight_server.py` | 8008 |
| 09 | `09_indexer_server.py` | 8009 |
| 10 | `10_inventory_server.py` | 8010 |

Problem 04 is the one exception to "start it yourself": the whole point there is two replicas, so the client starts both itself.

---

# Part 1: The Problems

## Problem 01: Your First Server and Client

**Files:** `01_research_server.py` + `01_research_client.py`
**Read first:** [Theory 01](#theory-01-servers-clients-and-the-stdio-pipe)

### Goal

Build the smallest possible MCP server and a client that starts it, asks what it can do, and calls it. No model involved.

### What You Build

**The server** (`01_research_server.py`):

1. Create `mcp = MCPServer("Research Tools")`.
2. Add a tool `get_research_sources() -> list[str]` that returns `["Wikipedia", "Google", "YouTube"]`.
3. Add a second tool `count_words(text: str) -> int` that returns the number of words in `text`.
4. Give both tools a proper docstring. The docstring is what a model will read later, so write it for a model, not for yourself.
5. Any narration (`print`) goes to `sys.stderr`, never to stdout.
6. `mcp.run()` in `__main__` (this defaults to STDIO).

**The client** (`01_research_client.py`):

1. Build `StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])`, where `SERVER_PATH` is `01_research_server.py` in the same folder as the client.
2. Open `async with Client(server_params) as client:`. This one line starts the server as a subprocess.
3. Call `list_tools()` and print, for every tool: its name, its description, and its `input_schema`.
4. Call `get_research_sources` and `count_words` (with any sentence you like) through `call_tool(...)`.
5. For each result, print both `result.content` (the text version) and `result.structured_content` (the typed version), and `result.is_error`.

### Expected Output

```text
[client] starting 01_research_server.py over STDIO
[client] tools on this server:
  - get_research_sources: Return the list of research sources ...
    input_schema: {'type': 'object', 'properties': {}}
  - count_words: Count the words in a piece of text ...
    input_schema: {'type': 'object', 'properties': {'text': {...}}, 'required': ['text']}

[client] call_tool('get_research_sources', {})
  content            : [TextContent(type='text', text='["Wikipedia", "Google", "YouTube"]')]
  structured_content : {'result': ['Wikipedia', 'Google', 'YouTube']}
  is_error           : False

[client] call_tool('count_words', {'text': 'MCP is just JSON-RPC with rules'})
  structured_content : {'result': 6}
  is_error           : False
```

Notice the `{'result': ...}` wrapper. Theory 01 explains where it comes from.

---

## Problem 02: Tools, Resources, Prompts, and How Each One Fails

**Files:** `02_recipe_server.py` + `02_recipe_client.py`
**Read first:** [Theory 02](#theory-02-the-three-primitives-and-their-error-rules)

### Goal

Use all three things a server can offer, and see that each one reports failure in a *different* way.

### What You Build

**The server** (`02_recipe_server.py`), named `"Recipe Book"`, with a small hard-coded dict of 4 or 5 recipes (name, cuisine, minutes, ingredients, steps):

1. **Tool** `search_recipes(cuisine: str) -> list[str]`: returns recipe names for that cuisine. If the cuisine is an empty string, raise `ToolError("cuisine cannot be empty")`.
2. **Tool** `broken_tool() -> str`: raises a plain `ValueError("secret internal detail")`. This exists only to show what the client sees from an unplanned crash.
3. **Static resource** `recipes://index`: returns a short text list of every recipe name.
4. **Resource template** `recipes://{name}`: returns the full recipe as text. If the name is unknown, raise `ResourceNotFoundError`.
5. **Prompt** `cook_with(ingredient: str, max_minutes: int)`: returns a message asking the model to suggest a recipe using that ingredient, within that time. If `max_minutes` is less than 5, raise `MCPError(code=INVALID_PARAMS, message=...)`.

**The client** (`02_recipe_client.py`), starting the server over STDIO like Problem 01, prints a labelled section for each of these:

1. `list_resources()` and `list_resource_templates()` separately. Notice the template only shows up in the second one.
2. `read_resource("recipes://index")` and `read_resource("recipes://<a real name>")`.
3. `get_prompt("cook_with", {"ingredient": "egg", "max_minutes": "15"})`, then print the returned messages.
4. The **failure tour**, one call per failure, each inside its own `try/except MCPError`:
   - `call_tool("search_recipes", {"cuisine": ""})`: no exception, `is_error=True`, the message is readable.
   - `call_tool("broken_tool", {})`: no exception, `is_error=True`, but "secret internal detail" is **not** in the text.
   - `call_tool("no_such_tool", {})`: no exception, `is_error=True`.
   - `read_resource("recipes://unknown")`: raises `MCPError`. Print its code.
   - `get_prompt("cook_with", {"ingredient": "egg", "max_minutes": "2"})`: raises `MCPError`. Print its code and message.

End with a summary table you print yourself: primitive, how it failed, whether the message reached the client.

### Expected Output (failure tour part)

```text
FAILURE TOUR
  tool  search_recipes('')   -> is_error=True  text='Error executing tool search_recipes: cuisine cannot be empty'
  tool  broken_tool()        -> is_error=True  text='Error executing tool broken_tool' (detail hidden)
  tool  no_such_tool()       -> is_error=True  text='Unknown tool: no_such_tool'
  res   recipes://unknown    -> MCPError code=-32602
  prompt cook_with(max=2)    -> MCPError code=-32602 'max_minutes must be at least 5'
```

The exact wording of the SDK's own messages may differ slightly. The *shape* (which ones raise, which ones return `is_error`, which ones hide the detail) is what matters.

---

## Problem 03: What Actually Travels Over the Wire

**Files:** `03_wire_server.py` + `03_raw_wire_client.py`
**Read first:** [Theory 03](#theory-03-the-request-on-the-wire)

### Goal

The one problem where you skip the client library. You send raw HTTP requests with `httpx` so you can see exactly what `Client` does for you in every other problem.

### What You Build

**The server** (`03_wire_server.py`): a tiny `MCPServer("Wire Demo")` with one tool `echo(text: str) -> str`, and cache hints for `tools/list` (`CacheHint(ttl_ms=60_000, scope="public")`). Run it with:

```python
mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, stateless_http=True)
```

**The client** (`03_raw_wire_client.py`): a helper `send(method, params, headers_override=None)` that POSTs one JSON-RPC message to `http://127.0.0.1:8000/mcp` with the right headers (including `MCP-Protocol-Version: 2026-07-28`, not just `_meta` inside the body), then prints the HTTP status and the JSON body. Use it to send, in order:

1. `server/discover`: print the protocol versions and the server info.
2. `tools/list`: point out `resultType`, `ttlMs`, and `cacheScope` in the response.
3. `tools/call` for `echo`: point out that there is **no** `ttlMs` here (calls are never cached).
4. `tools/list` **without** `_meta`: expect a `-32602` error naming the missing keys.
5. `tools/call` with a **wrong** `Mcp-Name` header: expect HTTP 400 with a `-32020` error.
6. A made-up method `"recipes/cook"`: expect `-32601`.

Responses can come back either as plain JSON or as a short Server-Sent Events (SSE) stream. Your helper must handle both (Theory 03 shows how).

### How to Run

```text
Terminal 1:  python 03_wire_server.py
Terminal 2:  python 03_raw_wire_client.py
```

### Expected Output (shortened)

```text
--- 2. tools/list ---
HTTP 200
  resultType : complete
  ttlMs      : 60000
  cacheScope : public
  tools      : ['echo']

--- 4. tools/list WITHOUT _meta ---
HTTP 400
  error: -32602 params._meta must be an object carrying the required
         'io.modelcontextprotocol/protocolVersion' and
         'io.modelcontextprotocol/clientCapabilities' envelope keys

--- 5. tools/call with WRONG Mcp-Name ---
HTTP 400
  error: -32020 mcp-name header does not match the request body's 'name' parameter

--- 6. a made-up method ---
HTTP 404
  error: -32601 Method not found
```

A header you have not met yet shows up here: every request also needs
`MCP-Protocol-Version: 2026-07-28`. Without it, the server does not even
route the request to the modern, stateless code path, so it falls through to
an older handler that does not know newer methods like `server/discover` at
all, and gives `-32601` instead of actually checking `_meta`. Theory 03
explains why this header exists separately from `_meta`.

---

## Problem 04: Two Servers, One Shopping Cart

**Files:** `04_cart_server.py` + `04_cart_client.py`
**Read first:** [Theory 04](#theory-04-what-stateless-really-means)

### Goal

Prove, with two real running server processes, why a stateless server must not keep important state in its own memory, and fix it.

### What You Build

**The server** (`04_cart_server.py`) runs over stateless HTTP. It reads its port and a replica name (`"A"` or `"B"`) from environment variables, and every tool result includes `served_by` so you can see which process answered. It has two versions of the same cart:

1. **The naive version:** a module-level dict `CARTS: dict[str, list[str]]`. Tools `naive_add(cart_id: str, item: str)` and `naive_view(cart_id: str)`.
2. **The token version:** no server memory at all. Tool `add_item(item: str, cart_token: str | None = None)` returns a **new** `cart_token` that contains the full item list, signed with HMAC-SHA256 using a secret both replicas share (read from an env var). Tool `view_cart(cart_token: str)` checks the signature, then returns the items. A tampered token must be rejected with a `ToolError`.

**The client** (`04_cart_client.py`):

1. Start **two** server processes (`asyncio.create_subprocess_exec`), replica A on port 8001 and replica B on port 8002, with the same shared secret. Wait until both are ready.
2. Open one `Client` per URL. Every call alternates between them, A, B, A, B, the way a round-robin load balancer would.
3. **Naive run:** add "apple" (lands on A), add "bread" (lands on B), view (lands on A). Print what you get. The cart is wrong.
4. **Token run:** same three steps, but pass the latest token along each time. The cart is right, even though each step hit a different process.
5. **Tamper run:** change one character in the token's signature and call `view_cart`. Expect `is_error=True`.
6. Shut both server processes down cleanly at the end.

### Expected Output

```text
NAIVE CART (state in server memory)
  add 'apple'  -> served_by=A  cart=['apple']
  add 'bread'  -> served_by=B  cart=['bread']          <-- B never saw the apple
  view         -> served_by=A  cart=['apple']          <-- A never saw the bread

TOKEN CART (state travels with the request)
  add 'apple'  -> served_by=A  items=['apple']
  add 'bread'  -> served_by=B  items=['apple', 'bread']
  view         -> served_by=A  items=['apple', 'bread']

TAMPERED TOKEN
  view         -> is_error=True  'This cart token has been modified ...'
```

---

## Problem 05: Your Trip Planner, Now Powered by MCP

**Files:** `05_trip_server.py` + `05_trip_agent.py`
**Read first:** [Theory 05](#theory-05-bridging-mcp-into-your-own-agent-loop)

### Goal

Take the weekend trip planner you built in chapter 2's `own_practice`, move its tools into an MCP server, and make your own hand-written agent use them through the protocol. This is the heart of the chapter.

### What You Build

**The server** (`05_trip_server.py`), named `"Trip Planner"`:

1. **Three tools**, same names and logic as your chapter 2 version: `get_destination_by_mood(mood: str)`, `get_weather_condition_by_destination(destination: str)`, `get_activities_by_destination(destination: str)`, with the same lookup tables and `"others"` fallbacks.
2. **A prompt** `trip_planner_persona()` returning the system persona text, including the "you must check weather and activities for at least two destinations" instruction.
3. **A resource** `trip://travel-rules` with a few short house rules (for example: "budget under 5000 rupees", "no overnight travel").
4. Runs as a stateless Streamable HTTP server on port 8005. Problem 06 connects to this same running server.

**The agent** (`05_trip_agent.py`):

1. Open a `Client` to `http://127.0.0.1:8005/mcp`.
2. **The app decides** (no model involved): fetch the persona with `get_prompt("trip_planner_persona")` and the rules with `read_resource("trip://travel-rules")`, and combine them into the system message.
3. Build a class `McpToolbox` with:
   - `async def load(self)`: calls `list_tools()` and converts every MCP tool into an OpenAI tool schema (`name`, `description`, `input_schema` becomes `parameters`).
   - `self.schemas`: the list you hand to the model.
   - `async def call(self, name, arguments) -> str`: calls `call_tool`, and turns the result into a string for the model. Prefer `structured_content` (as JSON), fall back to the text in `content`. If `is_error` is true, return the error text prefixed with `"ERROR: "` so the model knows.
4. Reuse your chapter 2 `run_tool_loop` (with `tc.model_dump()` for Gemini's `thought_signature`), but dispatch every tool call through `toolbox.call(...)` instead of a local function dict.
5. Run it for a user message like `"I'm feeling adventurous this weekend"` and print each tool call, its result, and the final answer.

### How to Run

```text
Terminal 1:  python 05_trip_server.py
Terminal 2:  python 05_trip_agent.py
```

### Expected Output

```text
[agent] connecting to http://127.0.0.1:8005/mcp
[agent] system prompt built from: prompt 'trip_planner_persona' + resource 'trip://travel-rules'
[agent] tools from server: ['get_destination_by_mood', 'get_weather_condition_by_destination', 'get_activities_by_destination']

  tool call: get_destination_by_mood({'mood': 'adventurous'})
  tool result: {"result": ["India", "Vietnam"]}
  tool call: get_weather_condition_by_destination({'destination': 'India'})
  tool result: {"temperature": 30, "condition": "warm"}
  tool call: get_activities_by_destination({'destination': 'India'})
  tool result: {"result": ["Cultural Tours", "Food Tours", "Hiking"]}
  ...

FINAL ANSWER
Since you are feeling adventurous this weekend, here are two options ...
```

The agent file never imports anything from the server file, and does not even know where the server's code lives: it only knows a URL. If you swapped the server for one written in Node.js, running on another machine, with the same tool names, the agent would not change at all.

---

## Problem 06: One Agent, Many Servers

**Files:** `06_multi_server_agent.py` only (no new server)
**Read first:** [Theory 06](#theory-06-connecting-to-several-servers-at-once)

> NOTE: good problem statement as this makes use of the _routes with prefix and tuple of client and toolname


### Goal

Real agents connect to several servers at once, over different transports, including servers someone else wrote. Combine them into one toolbox without name clashes, and only expose the tools you trust.

### What You Build

One agent file that connects to **three** servers at the same time:

| Server | How it is reached | Prefix |
|---|---|---|
| your `02_recipe_server.py` | STDIO subprocess | `recipes` |
| your `05_trip_server.py` | stateless HTTP on port 8005 (already running in another terminal) | `trips` |
| `@modelcontextprotocol/server-filesystem` (Node.js, via `npx`) | STDIO subprocess, limited to a `06_sandbox/` folder | `files` |

1. Open all three `Client`s together using `contextlib.AsyncExitStack`.
2. Extend `McpToolbox` (or write a `MultiToolbox`) that loads tools from every server and **prefixes** each name: `recipes__search_recipes`, `trips__get_destination_by_mood`, `files__write_file`. Keep a lookup from the prefixed name back to `(client, original_name)`.
3. Apply an **allowlist** to the filesystem server: expose only `read_text_file`, `write_file`, and `list_directory`. Everything else it offers (moving files, editing, and so on) is dropped before the model ever sees it. Print what you dropped.
4. Run the agent with a task that needs all three servers, for example: *"I'm feeling relaxed. Pick a destination, suggest an Indian recipe I can cook after the trip, and save the plan to trip_plan.md."*
5. After the run, read `06_sandbox/trip_plan.md` from the client side and print it, to prove the file was really written.

### How to Run

```text
Terminal 1:  python 05_trip_server.py
Terminal 2:  python 06_multi_server_agent.py
```

The other two servers are started by the agent itself, as STDIO subprocesses: your recipe server from Problem 02 is a STDIO server, and third-party servers launched through `npx` are almost always STDIO too, because they are meant to run as local tools on your own machine.

### Expected Output (shortened)

```text
[agent] connected: recipes (stdio), trips (http :8005), files (stdio via npx)
[agent] files: kept 3 tools, dropped 11: ['read_file', 'read_media_file', 'read_multiple_files',
  'edit_file', 'create_directory', 'list_directory_with_sizes', 'directory_tree', 'move_file',
  'search_files', 'get_file_info', 'list_allowed_directories']
[agent] tools the model sees (8):
  recipes__search_recipes, recipes__broken_tool, trips__get_destination_by_mood,
  trips__get_weather_condition_by_destination, trips__get_activities_by_destination,
  files__read_text_file, files__write_file, files__list_directory

  tool call: trips__get_destination_by_mood({'mood': 'relaxed'})
  tool result: {"result": ["India", "France"]}
  tool call: recipes__search_recipes({'cuisine': 'indian'})
...
  tool call: files__write_file({'path': 'trip_plan.md', 'content': '...'})
  tool result: {"content": "Successfully wrote to trip_plan.md"}

FINAL ANSWER
...

[agent] 06_sandbox/trip_plan.md now contains:
# Trip and Recipe Plan
...
```

A real wrinkle you may hit: the recipe lookup in Problem 02 matches cuisine names exactly (`"indian"`, lowercase), so if the model calls it with `"Indian"` it gets an empty list back and falls back to suggesting a recipe on its own instead of using yours. That is not a bug in your code, it is the model being slightly looser with casing than your tool is. Worth noticing, not worth over-engineering around.

The exact list of tools the filesystem server offers depends on its version. Print whatever it actually reports, and keep your allowlist as the source of truth.

---

## Problem 07: Big Lists: Pagination and Caching

**Files:** `07_bookstore_server.py` + `07_bookstore_client.py`
**Read first:** [Theory 07](#theory-07-cursors-and-caches)

### Goal

When there is too much data for one answer, hand it out in pages using an opaque cursor. And when an answer does not change often, let the client reuse it instead of asking again.

### What You Build

**The server** (`07_bookstore_server.py`), named `"Bookstore"`:

1. A catalog of 200 fake books, generated deterministically (fixed `random.seed`) with title, genre (5 genres), and page count.
2. Tool `search_books(genre: str, cursor: str | None = None) -> BookPage`, returning at most 10 books plus a `next_cursor`. `next_cursor` is `None` on the last page.
3. The cursor is **opaque**: a base64 string the client must copy back exactly, not a page number. An invalid cursor raises a `ToolError` that tells the caller to start again without a cursor.
4. The tool's description tells the model, in plain words, how paging works ("if `next_cursor` is not null, call again with it").
5. Cache hints: `tools/list` cached for 5 minutes, `scope="public"`.
6. Runs as a stateless Streamable HTTP server on port 8007.

**The client** (`07_bookstore_client.py`), connected to `http://127.0.0.1:8007/mcp`, in three parts:

1. **Walk the pages by hand:** loop `search_books(genre="sci-fi", cursor=...)` until `next_cursor` is `None`. Print each page's size and the total.
2. **Watch the cache:** call `list_tools()` three times. Time each call. The first goes to the server; the second should be served from the client's cache (much faster). Then call `list_tools(cache_mode="bypass")` and show that it goes to the server again.
3. **Let the model page:** give `search_books` to a model (through your `McpToolbox` from Problem 05) and ask *"How many sci-fi books under 250 pages do you have? List them."* The model must keep calling with `next_cursor` on its own until it has seen every page.

### How to Run

```text
Terminal 1:  python 07_bookstore_server.py
Terminal 2:  python 07_bookstore_client.py
```

### Expected Output (shortened)

```text
PART 1: walking pages by hand
  page 1: 10 books, next_cursor=eyJnZW5yZSI6...
  page 2: 10 books, next_cursor=eyJnZW5yZSI6...
  page 3: 10 books, next_cursor=eyJnZW5yZSI6...
  page 4: 10 books, next_cursor=None
  total sci-fi books: 40

PART 2: client-side cache
  list_tools #1                : 4.10 ms  (server)
  list_tools #2                : 0.08 ms  (cache)
  list_tools #3                : 0.07 ms  (cache)
  list_tools cache_mode=bypass : 3.60 ms  (server)

PART 3: the model pages on its own
  tool call: search_books({'genre': 'sci-fi'})
  tool call: search_books({'genre': 'sci-fi', 'cursor': 'eyJnZW5yZSI6...'})
  ...
FINAL ANSWER
We have 15 sci-fi books under 250 pages: ...
```

A real wrinkle: a model may try a few guesses at the genre string first
(`"Science Fiction"`, `"Sci-Fi"`) before landing on the exact value
`"sci-fi"` your server expects. That is ordinary model behavior with an
exact-match lookup, not a bug to fix -- it is the same "shape, not content"
lesson from earlier files, just showing up as spelling instead of schema.

The cache timings are where HTTP makes the lesson clearer: a real network round trip costs milliseconds, a cache hit costs microseconds, so the gap is impossible to miss. Your exact numbers will differ; the size of the gap is what matters.

Pagination is also where statelessness pays off. Because the cursor carries everything the server needs (genre and offset), you can stop the server between page 2 and page 3, start it again, and page 3 still works. A server that remembered "where you were" in its own memory would have lost your place.

---

## Problem 08: Asking the User Mid-Call (MRTR)

**Files:** `08_flight_server.py` + `08_flight_agent.py`
**Read first:** [Theory 08](#theory-08-multi-round-trip-requests)

### Goal

Some tools must not finish without a human saying yes, like booking a flight. Build a tool that stops halfway, asks the user to confirm, and finishes only after the answer comes back, all without the server keeping any memory between the two calls.

### What You Build

**The server** (`08_flight_server.py`), named `"Flight Desk"`:

1. Tool `search_flights(origin: str, destination: str) -> list[Flight]`: returns 2 or 3 fake flights with ids and base prices.
2. A pricing function where the fare **changes every 30 seconds** (for example, the base price plus a bump based on `int(time.time() // 30)`). This simulates real fares moving while the user thinks.
3. Tool `book_flight(flight_id: str, passenger_name: str, ctx: Context)`:
   - **Round 1** (`ctx.input_responses is None`): compute the current fare and return an `InputRequiredResult` with one form-mode elicitation asking *"Book flight X for NAME at Rs. PRICE?"* with a boolean `confirm` field. Store the quoted price in `request_state`.
   - **Round 2** (`ctx.input_responses` is set): read the quoted price back from `ctx.request_state`. If the fare has changed since the quote, raise a `ToolError` saying so. If the user declined, return a normal "booking cancelled by the user" result. If they accepted, return a booking with a confirmation code.
4. Runs as a stateless Streamable HTTP server on port 8008.

**The agent** (`08_flight_agent.py`):

1. Write an `elicitation_callback(context, params)` that prints `params.message` and asks the user in the terminal (yes or no). Because `input()` blocks, call it with `await asyncio.to_thread(input, "...")`, exactly the trick from the async notebook. Return an `ElicitResult` with `action="accept"` and `content={"confirm": True}`, or `action="decline"`.
2. Pass it in: `Client("http://127.0.0.1:8008/mcp", elicitation_callback=elicitation_callback)`.
3. Use your `McpToolbox` and `run_tool_loop` unchanged. Ask the model: *"Book me the cheapest flight from Delhi to Goa. My name is Sanjoy."*
4. Try it three times and record what happens:
   - Answer **yes** quickly: booking confirmed.
   - Answer **no**: the model is told the user cancelled, and says so.
   - Wait **more than 30 seconds** before answering yes: the fare changed, the tool returns an error, and the model explains it (and may offer to try again).

**Stretch (optional):** drive the two rounds by hand with `client.session.call_tool(..., allow_input_required=True)`, print the raw `InputRequiredResult`, then replay round 2 with a *different* `flight_id` but the same `request_state`. The SDK rejects it before your tool code runs.

### How to Run

```text
Terminal 1:  python 08_flight_server.py
Terminal 2:  python 08_flight_agent.py
```

Over HTTP, round 1 and round 2 are two completely separate POST requests, and you can watch both arrive in Terminal 1's log. Nothing connects them on the server except what the client carries back: the same arguments and the `request_state` string. Run two copies of this server behind a load balancer and round 2 could land on the other copy without anything breaking.

### Expected Output (the "yes" run)

```text
--- loop step 1 ---
  tool call: search_flights({'origin': 'Delhi', 'destination': 'Goa'})
  tool result: [{"id": "AI-101", "price": 5400}, {"id": "6E-202", "price": 4900}, ...]

--- loop step 2 ---
  tool call: book_flight({'flight_id': '6E-202', 'passenger_name': 'Sanjoy'})

  [server asks] Book flight 6E-202 for Sanjoy at Rs. 4900?
  Confirm? (y/n): y

  tool result: {"status": "booked", "confirmation": "GOA-7F3K", "price": 4900}

FINAL ANSWER
Done! You're booked on 6E-202 for Rs. 4900. Confirmation code: GOA-7F3K.
```

Notice what the model saw in step 2: one tool call, one result. It never saw the question or the second round. The client handled all of that.

---

## Problem 09: Progress Updates on Slow Tools

**Files:** `09_indexer_server.py` + `09_indexer_client.py`
**Read first:** [Theory 09](#theory-09-progress-notifications)

### Goal

A tool that takes a while should tell the caller how far along it is, instead of going silent until it is done.

### What You Build

**The server** (`09_indexer_server.py`), named `"Indexer"`:

1. Tool `index_folder(folder: str, ctx: Context) -> IndexReport`: walks every `.txt` and `.md` file in the folder, counts words in each, and sleeps about 0.3 seconds per file (with `await asyncio.sleep`) to simulate slow work.
2. After each file, call `await ctx.report_progress(progress=done, total=total_files, message=f"indexed {name}")`.
3. Return a report: number of files, total words, and the 3 largest files.
4. Runs as a stateless Streamable HTTP server on port 8009.

**The client** (`09_indexer_client.py`), connected to `http://127.0.0.1:8009/mcp`:

1. Create a small folder `09_docs/` with 8 to 10 text files (the client can generate them on first run).
2. Write an **`async def`** `on_progress(progress, total, message)` that prints a simple text progress bar.
3. Call `call_tool("index_folder", {"folder": ...}, progress_callback=on_progress)` with the folder's **absolute** path, and print the final report. The server is a separate process with its own working directory, so a relative path would be resolved from wherever the server was started, not from the client's folder.
4. Then deliberately pass a plain `def` (not `async def`) callback once, and look carefully at the output. The bar still prints, but you also get error noise. Write down why in a comment (Theory 09 explains it).

### How to Run

```text
Terminal 1:  python 09_indexer_server.py
Terminal 2:  python 09_indexer_client.py
```

### Expected Output

```text
[client] indexing 09_docs/ (9 files)
  [###.................]  1/9  indexed apples.md
  [####................]  2/9  indexed bridges.txt
  ...
  [####################]  9/9  indexed zebras.md

REPORT
  files      : 9
  total words: 2,341
  largest    : bridges.txt (512), rivers.md (430), zebras.md (377)
```

---

## Problem 10 (Optional): Getting Told When Something Changes

**Files:** `10_inventory_server.py` + `10_inventory_listener.py`
**Read first:** [Theory 10](#theory-10-subscriptions-and-where-statelessness-leaks)

### Goal

Every request so far was "ask once, get one answer". Here the client opens one long-lived stream and the server pushes a note down it whenever a resource changes. Then you see the one place where statelessness breaks down.

### What You Build

**The server** (`10_inventory_server.py`), stateless HTTP on port 8010 by default, overridable with an `INVENTORY_PORT` environment variable (the stretch below needs a second copy on another port):

1. A module-level stock dict, for example `{"laptop": 5, "phone": 10, "charger": 25}`.
2. Resource `inventory://stock`: returns the current stock as text.
3. Tool `sell(item: str, quantity: int, ctx: Context)`: lowers the stock (`ToolError` if not enough), then calls `await ctx.notify_resource_updated("inventory://stock")`.

**The listener** (`10_inventory_listener.py`), using `asyncio.gather` to run two things at once against the server on port 8010:

1. **The watcher:** `async with client.listen(resource_subscriptions=["inventory://stock"]) as sub:` then `async for event in sub:` re-read `inventory://stock` and print the new stock. Stop after 3 events.
2. **The shopper:** wait 1 second, then call `sell` three times, 1 second apart.

**Stretch (optional), the leak:** start a second server with `INVENTORY_PORT=8011 python 10_inventory_server.py`. Point the watcher at 8010 and the shopper at 8011. The watcher hears nothing, even though the stock really changed on 8011. Explain why in a comment.

### How to Run

```text
Terminal 1:  python 10_inventory_server.py
Terminal 2:  python 10_inventory_listener.py
```

### Expected Output

```text
[watcher] listening on inventory://stock
[shopper] sell laptop x1
[watcher] change! stock now: laptop=4 phone=10 charger=25
[shopper] sell phone x2
[watcher] change! stock now: laptop=4 phone=8 charger=25
[shopper] sell charger x5
[watcher] change! stock now: laptop=4 phone=8 charger=20
[watcher] got 3 events, done
```

---

# Part 2: The Theory

## Theory 01: Servers, Clients, and the STDIO Pipe

### The Two Sides

An MCP **server** is a program that offers capabilities (tools, data, templates). An MCP **client** is a program that connects to it and uses them. Your agent is one kind of client. Claude Desktop, an IDE, and a test script are other kinds. The server never knows or cares which one is calling.

```text
   CLIENT (your code)                         SERVER (your code, or anyone's)
 +---------------------+   JSON-RPC 2.0    +--------------------------+
 | Client(...)         | ----------------> | MCPServer("Research")    |
 |  .list_tools()      |                   |   @mcp.tool()            |
 |  .call_tool(...)    | <---------------- |   def get_sources(): ... |
 +---------------------+   results         +--------------------------+
```

### What `@mcp.tool()` Does for You

You write a normal Python function. The decorator reads three things from it and builds the tool's public description:

```text
  def count_words(text: str) -> int:        name         -> "count_words"
      """Count the words in a text."""      docstring    -> "description"
      return len(text.split())              parameters   -> "inputSchema"
                                            return type  -> "outputSchema"
```

So this is what a client receives from `tools/list` for that function:

```json
{
  "name": "count_words",
  "description": "Count the words in a text.",
  "inputSchema": {
    "type": "object",
    "properties": {"text": {"type": "string", "title": "Text"}},
    "required": ["text"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {"result": {"type": "integer", "title": "Result"}},
    "required": ["result"]
  }
}
```

That is why the docstring matters so much: it is the only thing a model reads when deciding whether to use the tool. Anything you want to keep private goes in a `#` comment, not the docstring.

### Why Results Have a `{"result": ...}` Wrapper

A tool result comes back in two forms at once:

- `content`: a list of text blocks, for humans and for older clients.
- `structured_content`: the typed value, matching `outputSchema`.

The protocol says `structured_content` must be a JSON **object** (a dict). A function returning `int`, `str`, or `list[str]` does not return an object, so the SDK wraps it: `6` becomes `{"result": 6}`. A function returning a Pydantic model (or a dict) already is an object, so it is sent as-is, with no wrapper. When you want clean structured output, return a Pydantic model.

### The STDIO Transport

**STDIO** means the client starts the server as a child process and talks to it through that process's standard input and output. One JSON message per line.

```text
 +------------------- client process --------------------+
 |                                                        |
 |  Client(StdioServerParameters(...))                    |
 |      |  starts                                         |
 |      v                                                 |
 |  +---------------------------+                         |
 |  | server process            |                         |
 |  |  stdin   <-- requests     |   no network, no port   |
 |  |  stdout  --> responses    |   only this client      |
 |  |  stderr  --> your logs    |   can talk to it        |
 |  +---------------------------+                         |
 +--------------------------------------------------------+
```

`StdioServerParameters(command=sys.executable, args=[path])` is just the command line `python path/to/server.py`, written as a list. Using `sys.executable` makes sure the server runs with the same Python (and the same installed packages) as the client.

**The one rule you must never break:** stdout *is* the message channel. A plain `print("hello")` inside a STDIO server writes `hello` into the stream the client is parsing as JSON, and the client fails with a parse error. Always print to `sys.stderr`:

```python
print("indexing...", file=sys.stderr)   # safe, shows up in your terminal
print("indexing...")                    # breaks the protocol
```

### What Happens When You Open `Client(...)`

```text
async with Client(params) as client:
   1. start the subprocess
   2. send server/discover      -> "which protocol versions do you speak?"
   3. server answers 2026-07-28 -> client uses the modern, stateless protocol
   ... your calls ...
   4. on exit: close stdin, wait for the subprocess to end
```

Step 2 is what `mode="auto"` (the default) does. If the server is an old one that does not know `server/discover`, the client falls back to the old handshake by itself. You do not have to do anything.

### Gotchas

- The SDK's Python objects use **snake_case** (`result.is_error`, `result.structured_content`, `tool.input_schema`) even though the JSON on the wire uses camelCase (`isError`, `structuredContent`, `inputSchema`). `result.isError` raises `AttributeError`.
- A STDIO server started by hand (`python 01_research_server.py`) looks frozen. It is not. It is waiting for a client to write to its stdin.

### STDIO or Streamable HTTP: Which One, When

MCP has exactly two standard transports. The messages are identical over both; only the pipe and who starts the server change.

```text
  STDIO                                      STREAMABLE HTTP
  -----                                      ---------------
  client starts the server                   server is started on its own,
  as a subprocess                            keeps running

  client --stdin/stdout--> server            client A --POST /mcp--+
                                             client B --POST /mcp--+--> server
  one client only                            client C --POST /mcp--+
  same machine only                          many clients, any machine
```

| | STDIO | Streamable HTTP |
|---|---|---|
| Who starts the server | the client, as a subprocess | you (or your deployment), ahead of time |
| How the client finds it | a command line | a URL |
| Callers at once | one | many |
| Reachable over a network | no | yes |
| Can run several copies behind a load balancer | no | yes (that is what statelessness is for) |
| Authentication | not needed, nothing is exposed | needed for anything public (OAuth) |
| Typical use | local tools: a desktop app or CLI starting a server for itself | shared services, cloud deployments, a server used by a team or by customers |

The rule of thumb: **STDIO for local, Streamable HTTP for anything shared or deployed.** Both are current and both are standard; neither is the "old" one. A desktop app like Claude Desktop starting a filesystem server on your laptop is a perfect STDIO case, and the spec asks clients to support STDIO whenever they can. A tool your whole team uses, or one you run in the cloud, is an HTTP case, and it is the only one of the two where the stateless design of 2026-07-28 actually matters, because only HTTP can have more than one server process answering the same client.

That is why this chapter uses STDIO for its first two problems (the simplest way to meet a client and a server) and Streamable HTTP from Problem 03 on (the shape you will build and deploy).

---

## Theory 02: The Three Primitives and Their Error Rules

### Who Decides

A server can offer three kinds of thing. The easiest way to tell them apart is to ask **who decides when it gets used**.

| Primitive | What it is | Who decides to use it | Client method |
|---|---|---|---|
| **Tool** | An action | The **model**, in the middle of a conversation | `call_tool` |
| **Resource** | Data at an address | The **app or the user** | `read_resource` |
| **Prompt** | A ready-made message template | The **app or the user** | `get_prompt` |

A real-world picture: in a restaurant kitchen, tools are the knives and pans the chef (the model) grabs whenever needed. Resources are the recipe cards pinned on the wall that the manager (the app) decides to show. Prompts are the order slips the waiter (the user) hands in to start a dish.

### Resources: Fixed Addresses and Templates

A resource lives at a URI. There are two kinds:

```python
@mcp.resource("recipes://index")          # fixed address
def index() -> str: ...

@mcp.resource("recipes://{name}")         # template: {name} is a blank
def recipe(name: str) -> str: ...
```

They are listed by **two different methods**, which surprises everyone the first time:

```text
  list_resources()            -> recipes://index           (fixed ones only)
  list_resource_templates()   -> recipes://{name}          (templates, blank intact)
  read_resource("recipes://pasta")  -> fills the blank, calls recipe("pasta")
```

### Prompts

A prompt returns one or more messages ready to send to a model. Prompt arguments always travel as **strings** on the wire, even if your function says `max_minutes: int`. The SDK converts `"15"` to `15` using your type hints. That is why the client in Problem 02 passes `"15"`, not `15`.

### Each Primitive Fails Differently

This is deliberate, and it follows from who the failure is for.

```text
                   TOOL                         RESOURCE / PROMPT
                   ----                         -----------------
 failure goes to   the MODEL                    the APP (your code)
 shape             normal result,               a real JSON-RPC error,
                   is_error = True              client raises MCPError
 why               the model should read the    the app asked for something
                   error and try something      that does not exist; that is
                   else ("wrong cuisine,        a bug or bad input in the app,
                   let me retry")               not something to "reason" about
```

And within each, there is a choice about whether the message is shown:

| You raise... | In a tool | In a resource | In a prompt |
|---|---|---|---|
| a plain exception (`ValueError`) | `is_error=True`, message **hidden** | `-32603`, message hidden | `-32603 "Internal server error"`, hidden |
| the "safe to show" error | `ToolError`: message shown | `ResourceError`: shown | (no special type) |
| a "not found" error | unknown tool name: `is_error=True` | `ResourceNotFoundError`: `-32602`, shown | (no special type) |
| `MCPError(code, message)` | | | the **only** way to show a message |

Why hide plain exceptions? Because they often contain internal details (file paths, SQL, secrets). The SDK assumes an unplanned crash is not safe to show anyone. When you *want* the message to be seen, raise the error type that means "this is safe to show".

The prompt column is the odd one: prompts have no dedicated error class, and every exception except `MCPError` (including argument validation errors) becomes the same unhelpful `-32603`. If you want a useful message from a prompt, raise `MCPError(code=INVALID_PARAMS, message="...")` yourself.

### Imports You Will Need

```python
from mcp import MCPError
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, ResourceNotFoundError
from mcp_types import INVALID_PARAMS
```

---

## Theory 03: The Request on the Wire

### One Request, Fully Self-Contained

The 2026-07-28 version of MCP is **stateless**. There is no "connect and introduce yourself" step and no session. Every request carries everything the server needs to understand it, inside a `_meta` object that sits **inside `params`**:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "echo",
    "arguments": {"text": "hi"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

Both `_meta` keys are required on every request. Leave either out and you get `-32602` before the server even looks at the method.

### The HTTP Headers

Over HTTP, a few headers are part of the contract too:

```text
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream     <- you must accept BOTH
MCP-Protocol-Version: 2026-07-28                <- routes to the MODERN handler at all
Mcp-Method: tools/call                          <- always, must match body "method"
Mcp-Name: echo                                  <- for tools/call, prompts/get,
                                                   resources/read; must match the name
```

`MCP-Protocol-Version` is the one that is easy to miss, because `_meta` inside the body already says the protocol version, and it feels redundant to say it again in a header. It is not redundant: the server uses this header, before it even parses `_meta`, to decide whether to hand the request to the 2026-07-28 stateless code path at all. Leave it out, and the request quietly falls through to an older handler that pre-dates `_meta` entirely, so a missing `_meta` is never even noticed, and a newer method like `server/discover` comes back `-32601 Method not found`, not because the server does not have it, but because you never reached the code that knows about it. Always send both: the header gets you to the right code path, `_meta` inside the body is what that code path actually validates.

`Mcp-Method` and `Mcp-Name` exist for a different reason: so that a load balancer or gateway can route, log, or rate-limit a request **without opening and parsing the JSON body**. If either is missing or does not match the body, the server rejects it with `-32020`.

### What a Response Looks Like

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [ ... ],
    "resultType": "complete",
    "ttlMs": 60000,
    "cacheScope": "public",
    "_meta": {"serverInfo": {"name": "Wire Demo", "version": "..."}}
  }
}
```

- `resultType`: `"complete"` for a normal answer, `"input_required"` when the server needs something first (Theory 08).
- `ttlMs` and `cacheScope`: caching hints, only on the six list-like methods (`tools/list`, `prompts/list`, `resources/list`, `resources/templates/list`, `resources/read`, `server/discover`). Never on `tools/call` or `prompts/get`, because those do work, and work is not a lookup you can reuse.

### JSON or a Stream

The server may answer as plain JSON (`Content-Type: application/json`) or as a short SSE stream (`Content-Type: text/event-stream`). An SSE body looks like:

```text
event: message
data: {"jsonrpc": "2.0", "id": 2, "result": {...}}

```

So your raw client checks the `Content-Type` header. If it is JSON, call `response.json()`. If it is an event stream, find the line that starts with `data:`, cut off that prefix, and `json.loads` the rest. The SDK client does this for you, which is one of the many small things you stop thinking about once you use it.

### `server/discover`

`server/discover` asks a server "which protocol versions do you support, what can you do, and who are you?" in one call. Servers must answer it. Clients may skip it: a client that already knows what it wants can send `tools/call` as its very first message.

### The Error Codes You Will Meet

| Code | Meaning | When |
|---|---|---|
| `-32602` | Invalid params | missing `_meta` keys, bad arguments, unknown resource |
| `-32601` | Method not found | a method the server does not know |
| `-32020` | Header mismatch | `Mcp-Method` / `Mcp-Name` missing or not matching the body |
| `-32022` | Unsupported protocol version | a version string the server has never heard of |

### The Gotcha That Bites First

In the Python SDK, `stateless_http` **defaults to `False`**. If you forget to pass `stateless_http=True`, a stateless client gets HTTP 400 with `"Bad Request: Missing session ID"`, which is very confusing on brand-new software. Always pass it:

```python
mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, stateless_http=True)
```

---

## Theory 04: What Stateless Really Means

### The Picture

Stateless means **the server does not remember anything between requests**. Each request is answered using only what is inside it. The big practical win: you can run many copies (replicas) of a server behind a plain round-robin load balancer, and any copy can answer any request.

```text
                         +--> replica A  (port 8001)
 client --> load balancer|
            (round-robin)+--> replica B  (port 8002)

 request 1 -> A     request 2 -> B     request 3 -> A     ...
```

### Why In-Memory State Breaks

The protocol being stateless does not stop *your code* from keeping state. A module-level dict is still allowed. It is just a trap once there is more than one replica, because each process has its own separate copy of that dict:

```text
  add "apple"  -> A   A.CARTS = {"c1": ["apple"]}      B.CARTS = {}
  add "bread"  -> B   A.CARTS = {"c1": ["apple"]}      B.CARTS = {"c1": ["bread"]}
  view         -> A   returns ["apple"]                  (bread is lost on B)
```

Nobody did anything wrong at the protocol level. The data simply lives in the wrong place.

### Two Fixes

1. **Put the state somewhere shared**: a database, Redis, a file every replica can read. This is the usual answer for real data like orders and accounts.
2. **Make the request carry the state**: the server hands the client a token that contains the data, and the client sends it back next time. No server memory needed at all. This is what Problem 04 does.

### Why the Token Must Be Signed

If the token were just `base64(["apple", "bread"])`, the client could decode it, add `"free laptop"`, encode it again, and send it back. So the server **signs** it with a secret only the servers know:

```text
 payload   = base64( {"items": ["apple", "bread"]} )
 signature = HMAC_SHA256(secret, payload)
 token     = payload + "." + signature

 on every request:
   recompute HMAC_SHA256(secret, payload) and compare with signature
   same      -> trust the payload
   different -> someone changed it -> reject
```

A tiny dry run with a made-up 4-character "hash" to show the idea:

```text
 secret = "s3cr3t"
 payload "apple"        -> sign -> "9f2c"     token = "apple.9f2c"
 attacker edits payload -> "apple+laptop.9f2c"
 server recomputes sign("apple+laptop") = "41ab"  !=  "9f2c"  -> rejected
```

The attacker cannot produce the right signature without the secret. Both replicas share the same secret (through an environment variable), so a token signed by A verifies fine on B. Use `hmac.compare_digest` to compare signatures, not `==`, so the check takes the same time whether the first character or the last one differs.

### Gotcha

When you tamper with a token to test rejection, change a character **near the start** of the signature, not the very last one. The last base64 character of a 32-byte digest carries a couple of unused padding bits, so some replacement characters decode to the exact same bytes and the "tampered" token still verifies. Changing the first character of the signature always changes the bytes.

---

## Theory 05: Bridging MCP Into Your Own Agent Loop

### The Gap

An MCP server describes its tools one way. The OpenAI chat completions API wants them described another way. Your agent sits in the middle and translates, in both directions.

```text
          MCP side                     YOUR AGENT                 MODEL side
 +--------------------------+   +---------------------+   +-----------------------+
 | Tool                     |   |  McpToolbox.load()  |   | {"type": "function",  |
 |  name                    |-->|   translate each    |-->|  "function": {        |
 |  description             |   |   tool once         |   |    "name": ...,       |
 |  input_schema            |   |                     |   |    "description": ...,|
 +--------------------------+   |                     |   |    "parameters": ...}}|
                                |                     |   +-----------------------+
 +--------------------------+   |  McpToolbox.call()  |   +-----------------------+
 | CallToolResult           |<--|   call_tool(name,   |<--| tool_calls[i]         |
 |  structured_content      |   |     args)           |   |  .function.name       |
 |  content                 |-->|   result -> string  |-->| {"role": "tool",      |
 |  is_error                |   |                     |   |  "content": "..."}    |
 +--------------------------+   +---------------------+   +-----------------------+
```

The translation is short, because MCP's `inputSchema` is already a JSON Schema, which is exactly what OpenAI's `parameters` field wants:

```python
{
    "type": "function",
    "function": {
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.input_schema,
    },
}
```

### Turning a Result Into Text for the Model

The model only reads strings in a `tool` message, so `call()` has to flatten the result:

1. If `result.is_error` is true, return `"ERROR: " + the text`. Saying so clearly lets the model react ("that city is not supported, let me try another").
2. Otherwise, if `structured_content` is present, return `json.dumps(structured_content)`.
3. Otherwise, join the text of every block in `content`.

### The App Decides, the Model Decides

Problem 05 uses all three primitives, and each one has a different decider:

```text
  prompt   trip_planner_persona  --+
                                   +--> system message      APP decides (before the loop)
  resource trip://travel-rules   --+

  tools    get_weather, ...       ----> tools=[...]          MODEL decides (inside the loop)
```

The model never "calls" the prompt or the resource. Your code fetches them once, before the loop starts, and puts them into the system message. This is how real hosts like Claude Desktop work too: you pick a prompt from a menu, or attach a resource, and the app inserts it.

### What Changed Compared to Chapter 2

In chapter 2 the tool lived in the same file: `handlers = {"get_weather": get_weather}`. Now it lives in another process, maybe on another machine, maybe written in another language.

```text
 chapter 2                                  chapter 3
 handler = handlers[name]                   result = await client.call_tool(name, args)
 result  = handler(**args)                  (a round trip through the protocol)
```

Your loop does not care. That is the whole payoff: the tool's schema is the contract, and the code behind it is the server's private business.

### Gotcha: Gemini's `thought_signature`

Same as chapter 2: when you append the assistant's tool-call message back into `messages`, use `tc.model_dump()` for each tool call, not a hand-built dict. Gemini attaches a `thought_signature` in an extra field, and loop step 2 fails with a 400 error if it is missing.

---

## Theory 06: Connecting to Several Servers at Once

### Opening Many Clients Together

Each server needs its own `Client`, and each `Client` is an `async with` block. Writing three nested `async with` blocks works but gets ugly fast. `contextlib.AsyncExitStack` lets you open any number of them in a loop and closes them all, in reverse order, when the block ends:

```python
async with AsyncExitStack() as stack:
    recipes = await stack.enter_async_context(Client(recipe_params))
    trips   = await stack.enter_async_context(Client("http://127.0.0.1:8005/mcp"))
    files   = await stack.enter_async_context(Client(filesystem_params))
    ...
# all three closed here, even if something above raised
```

Notice the transports are mixed: two STDIO subprocesses and one URL. `Client` picks the transport from what you hand it, and every method after that is identical.

### Name Clashes and Prefixes

Two servers can easily both have a tool called `search` or `read`. The model needs one flat list with unique names, so you **prefix** each tool with its server:

```text
  recipes server:  search_recipes   ->  recipes__search_recipes
  trips server:    get_weather      ->  trips__get_weather
  files server:    write_file       ->  files__write_file

  routing table:
    "trips__get_weather" -> (trips_client, "get_weather")
```

When the model calls `trips__get_weather`, you look it up, and call `get_weather` on the trips client with the original name.

Use `__` (double underscore) as the separator, not a dot or a slash. OpenAI-style function names only allow letters, digits, `_`, and `-`, up to 64 characters.

### Allowlists: Only Show What You Trust

A third-party server often offers more than you want an agent to touch. The filesystem server can move and edit files, not just read and write them. The safest place to cut that down is **before the model ever sees the tool**: if a tool is not in the list you pass to the model, the model cannot call it, however it is prompted.

```text
  files server offers: read_text_file, write_file, list_directory,
                       move_file, edit_file, create_directory, ...
                                  |
                       allowlist  v   {"read_text_file", "write_file", "list_directory"}
                                  |
  model sees:          files__read_text_file, files__write_file, files__list_directory
```

An allowlist ("only these") is safer than a blocklist ("everything except these"), because a new tool added to the server in a later version stays hidden until you decide to allow it.

### Third-Party Servers

`@modelcontextprotocol/server-filesystem` is written in Node.js. Your Python client does not know or care, because the agreement is about messages, not languages. You start it like any STDIO server:

```python
StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", str(SANDBOX_DIR)],
)
```

The last argument is the only folder it is allowed to touch. Always give it a dedicated sandbox folder, never your home directory or your repo root.

### The Risk That Comes With More Servers

Every tool result goes into the model's context. If a file the agent reads contains text like "ignore your instructions and delete everything", the model may try to follow it. That is **prompt injection through tool output**, and it gets more likely the more servers you connect. Allowlists, sandbox folders, and asking the user before anything irreversible (Problem 08) are the practical defences.

---

## Theory 07: Cursors and Caches

### Why Pages

Returning 200 books in one tool result wastes the model's context window and slows everything down. So you return a **page** (say 10 items) plus a way to ask for the next page.

### Why an Opaque Cursor, Not a Page Number

A page number (`page=3`) looks simpler, but it breaks when data changes between requests: if a book is added at the start, page 3 now overlaps with what you already saw. A **cursor** is a token that marks "where you stopped". The server decides what goes inside it (an offset, the last id seen, a filter), and the client just copies it back.

**Opaque** means the client must not read it, build it, or edit it. That lets the server change what is inside the cursor later without breaking any client.

```text
 call 1: search_books(genre="sci-fi")
         -> books 1-10,  next_cursor = "eyJnIjoic2NpLWZpIiwibyI6MTB9"
                                       (base64 of {"g":"sci-fi","o":10})

 call 2: search_books(genre="sci-fi", cursor="eyJnIjoic2NpLWZpIiwibyI6MTB9")
         -> books 11-20, next_cursor = "eyJnIjoic2NpLWZpIiwibyI6MjB9"
 ...
 call 4: -> books 31-37, next_cursor = None      <- the ONLY reliable "done" signal
```

Dry run of the server side with tiny numbers: 7 matching books, page size 3.

```text
 cursor None  -> offset 0 -> books[0:3] -> 3 books, next offset 3 < 7 -> cursor for 3
 cursor (3)   -> offset 3 -> books[3:6] -> 3 books, next offset 6 < 7 -> cursor for 6
 cursor (6)   -> offset 6 -> books[6:9] -> 1 book,  next offset 9 >= 7 -> None
```

Never stop just because a page had fewer items than you expected. Stop only when `next_cursor` is `None`.

### Teaching a Model to Page

A model only pages correctly if you tell it how, in the tool's description and in the `next_cursor` field's description. Something like: *"Returns 10 books at a time. If `next_cursor` is not null, call this tool again with `cursor` set to that exact value to see more. Never make up a cursor."* Without this, models often stop after the first page and answer from partial data.

### Protocol-Level Pagination

The protocol's own list methods (`tools/list`, `resources/list`, and so on) also support cursors: `client.list_tools(cursor=...)` and `result.next_cursor`. `MCPServer` currently returns everything in one page, but a correct client loops until `next_cursor` is `None` anyway, because other servers may page their lists.

### Caching

List-like answers rarely change, so the server can say how long an answer stays fresh:

```python
mcp = MCPServer(
    "Bookstore",
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)
```

- `ttl_ms`: how many milliseconds the answer can be reused.
- `scope="public"`: safe to share across users. `"private"` means only for this one user.

The `Client` caches these answers **by default**, in memory, and respects the TTL. Each cacheable call accepts a `cache_mode`:

| `cache_mode` | Reads from cache? | Stores in cache? |
|---|---|---|
| `"use"` (default) | yes | yes |
| `"refresh"` | no, always asks the server | yes |
| `"bypass"` | no | no |

`tools/call` is never cached, whatever you set: calling a tool does work, and you would not want a "book flight" call answered from a cache.

---

## Theory 08: Multi Round-Trip Requests

### The Problem

Sometimes a tool cannot finish without asking a human something: "Confirm Rs. 4900?" In the older, session-based MCP, the server would send a question back to the client down a connection held open in the middle of the call. In stateless MCP there is no held-open connection and the server keeps no memory, so that cannot work.

### The Solution: Answer "I Need Input", Then Get Called Again

**MRTR** (Multi Round-Trip Requests) flips it around. The tool returns early with "I need this input first". The client asks the user, then sends the **same call again** with the answer attached. Two complete, independent requests:

```text
  CLIENT                                         SERVER
    |  tools/call book_flight(6E-202, Sanjoy)        |
    | ---------------------------------------------> |  round 1: input_responses is None
    |                                                |  quote fare = 4900
    |  resultType: "input_required"                  |
    |  inputRequests: {"confirm": "Book at 4900?"}   |
    |  requestState: "v1.<sealed blob>"              |
    | <--------------------------------------------- |  forgets everything
    |                                                |
    |  (client asks the user: y)                     |
    |                                                |
    |  tools/call book_flight(6E-202, Sanjoy)        |
    |    + inputResponses: {"confirm": accept}       |
    |    + requestState:   "v1.<same blob>"          |
    | ---------------------------------------------> |  round 2: input_responses is set
    |                                                |  check fare still 4900, book it
    |  result: booked, GOA-7F3K                      |
    | <--------------------------------------------- |
```

Nothing is held open between the two calls. Round 2 could even be answered by a different replica.

### Server Side

```python
async def book_flight(flight_id: str, passenger_name: str, ctx: Context):
    if ctx.input_responses is None:                      # round 1
        return InputRequiredResult(
            result_type="input_required",
            input_requests={
                "confirm": ElicitRequest(
                    method="elicitation/create",
                    params=ElicitRequestFormParams(
                        mode="form",
                        message="Book 6E-202 for Sanjoy at Rs. 4900?",
                        requested_schema={
                            "type": "object",
                            "properties": {"confirm": {"type": "boolean"}},
                            "required": ["confirm"],
                        },
                    ),
                )
            },
            request_state='{"quoted_price": 4900}',
        )
    answer = ctx.input_responses["confirm"]              # round 2
    quoted = json.loads(ctx.request_state)["quoted_price"]
    ...
```

`input_requests` is a plain dict keyed by a name you choose (`"confirm"`), and `ctx.input_responses["confirm"].action` is `"accept"`, `"decline"`, or `"cancel"`.

### What `request_state` Is For

The server forgets everything after round 1, so anything round 2 needs to know about round 1 must travel with the client. That is `request_state`: a string you give the client, which it sends back unchanged.

The SDK **encrypts** it and **binds** it to the exact call: it seals the method, the tool name, and a hash of the arguments together with your data. If round 2 arrives with different arguments (say a different `flight_id`) but the old `request_state`, the SDK rejects it with `-32602` before your function even runs. So you do not need to protect the arguments yourself.

What is left for you to put in `request_state` is **facts from round 1 that are not arguments**. The fare is the perfect example: the `flight_id` cannot change between rounds (the SDK guarantees that), but the *price* of that flight can. Round 2 compares the quoted price with the current one:

```text
 round 1 at 10:00:05   fare = 4900   request_state = {"quoted_price": 4900}
 user thinks for 40 seconds...
 round 2 at 10:00:45   fare = 5150   (it changed at 10:00:30)
                       4900 != 5150  -> ToolError("the fare changed, please reconfirm")
```

### Client Side: The Callback Does Both Rounds

With the SDK client, you never see round 1 or round 2. You hand `Client` an `elicitation_callback`, and one `await client.call_tool(...)` drives both rounds for you:

```text
 call_tool("book_flight", args)
    -> round 1 comes back input_required
    -> SDK calls YOUR elicitation_callback(context, params)
         you print params.message, ask the user, return ElicitResult
    -> SDK sends round 2 with your answer and the request_state
    -> returns the final result to you
```

So in your agent loop, the model sees one tool call and one result. The question to the user is between your app and the server. If you forget to pass a callback, `call_tool` raises `MCPError: Elicitation not supported` as soon as the tool asks for input. There is no silent "yes" by default, which is exactly what you want for something like a payment.

### `input()` Inside an Async Callback

The callback is `async def`, and `input()` blocks the whole event loop while it waits for you to type. Run it in a thread: `answer = await asyncio.to_thread(input, "Confirm? (y/n): ")`. This is the same trick as the async notebook's "blocking call inside async code" section.

### Declining Is Not an Error

If the user says no, the tool did its job: it asked and got an answer. So it returns a normal result (`is_error=False`) saying the booking was cancelled. Errors are for things going wrong, not for a user making a choice.

### Zooming Out: Three Actors, Not Two

The diagram above shows CLIENT and SERVER, but there is a third actor hiding inside "the client asks the user: y" — the actual human. Spelling all three out removes most of the confusion around "wait, is this a second question?":

```text
  HUMAN                    CLIENT (your agent)            SERVER (book_flight)
    |                            |                               |
    |                            |----- call 1: book_flight ---->|
    |                            |      (no answer yet)          |
    |                            |                                | quotes the fare,
    |                            |<--- InputRequiredResult -------|  builds ONE question,
    |                            |     (the question + fare)     |  returns, and is done --
    |                            |                               |  nothing is left running
    |                            |
    |   "Book 6E-202 for         |
    |<--- Sanjoy at Rs 4900? ----|   <- the client shows the server's
    |                            |      question to the human
    |----- "yes" --------------->|   <- the human types the answer
    |                            |
    |                            |----- call 2: book_flight ---->|
    |                            |      (same flight_id,         |
    |                            |       same passenger_name,    |
    |                            |       + the human's answer,   | checks the fare again,
    |                            |       + the SAME request_state| checks the answer,
    |                            |       string from call 1)     | books it, and is done
    |                            |<--- BookingResult -------------|
```

There is exactly **one** question in this whole exchange. The server asks it once, in round 1. Round 2 is not a second question — it is the client *delivering the answer* to the first one. The reason this needs two separate calls at all, instead of one function that "pauses and waits," is that a stateless server cannot pause: once `book_flight` returns, the Python function has fully exited and nothing about it is kept in memory. So "ask, then wait for a human, then finish" has to become two independent executions of the same function, connected only by `request_state`. From the human's side it feels like one conversation. From the server's side it is two unrelated invocations that happen to share one piece of paper passed between them.

### A Concrete Dry Run of Both Rounds

Using the same numbers as the Server Side example above, with the time-based fare formula `base_price + window * 25` from `_current_fare`:

```text
CALL 1
  ctx.input_responses = None
  flight found, base_price = 4900
  current_price = _current_fare(4900) = 4900   (window = 0 right now)
  -> branch taken: "if ctx.input_responses is None"
  -> returns InputRequiredResult(
         input_requests={"confirm": "Book 6E-202 for Sanjoy at Rs. 4900?"},
         request_state='{"quoted_price": 4900}'
     )

  [client shows the question, human waits 10 seconds, says "yes"]

CALL 2
  ctx.input_responses = {"confirm": <answer with .action = "accept">}
  ctx.request_state   = '{"quoted_price": 4900}'    <- unchanged, carried by the client

  flight found again (same lookup, redone from scratch)
  current_price = _current_fare(4900) = 4900        <- still window 0, only 10s passed
  -> branch skipped: input_responses is NOT None
  -> quoted_price = json.loads(request_state)["quoted_price"] = 4900
  -> quoted_price (4900) == current_price (4900)    <- no ToolError
  -> confirmation.action == "accept"                <- skip the cancel branch
  -> returns BookingResult(status="booked", confirmation="GOA-7F3K", price=4900)
```

And the version where the human takes too long, which is exactly what the fare-change check exists to catch:

```text
CALL 2 (human waited 40 seconds this time)
  current_price = _current_fare(4900) = 5150        <- the 30-second window moved
  quoted_price (4900) != current_price (5150)
  -> raise ToolError("the fare changed since you were quoted Rs. 4900 (it is now Rs. 5150). ...")
```

### Why `ctx.input_responses["confirm"]` Does Not Look Like a Plain Boolean

The `requested_schema` you wrote only asks for one boolean field, `confirm`. It is tempting to expect `ctx.input_responses["confirm"]` to simply be `True` or `False`. It is not — it is an **answer envelope** with an `.action` field: `"accept"`, `"decline"`, or `"cancel"`. That is because the human can do three things, not two: agree, refuse, or close the dialog without answering at all. `.action` captures which of those happened. If `.action == "accept"`, the actual form data you asked for (`confirm: true`) lives inside the envelope's `.content`, but `book_flight` never even needs to look there, because `.action == "accept"` already tells you everything it needs to know.

One gotcha worth stating out loud: do not build the cancellation message with something like `confirmation.action + "d"`. That turns `"decline"` into `"declined"` correctly, but turns `"cancel"` into `"canceld"` -- a bug that looks completely plausible until you say it out loud. A small lookup table (`{"decline": "declined", "cancel": "cancelled"}`) avoids it.

### The Client Callback, Line by Line

```python
async def elicitation_callback(context, params: ElicitRequestParams) -> ElicitResult:
    print(f"\n  [server asks] {params.message}")
    answer = await asyncio.to_thread(input, "   Confirm? (y/n): ")

    if answer.strip().lower().startswith("y"):
        return ElicitResult(action="accept", content={"confirm": True})

    return ElicitResult(action="decline")
```

`params: ElicitRequestParams` is the exact object the server built on the server side (`ElicitRequestFormParams(message=..., mode="form", requested_schema=...)`), handed to you by the SDK the moment it notices the server's result was `input_required`. `params.message` is the literal question text; `params.requested_schema` describes the shape of the expected answer.

`await asyncio.to_thread(input, "...")` matters because `input()` is a **blocking** call -- it freezes the entire thread until a human types something and hits Enter. Calling it directly inside an `async def` would freeze the whole asyncio event loop, not just this one coroutine, since there is only one event loop thread. `asyncio.to_thread` runs `input(...)` on a separate worker thread and awaits its result, so the event loop stays free to do other work while a human is busy typing. This is the same "blocking call inside async code" trick from the async notebook.

The return value's shape must match what `book_flight`'s round 2 expects: `action="accept"` with `content={"confirm": True}` matches the exact field name (`"confirm"`) the server's `requested_schema` asked for.

### Reading the Schema Instead of Hardcoding the Field Name

The callback above only works because you, the developer, already know by reading the server's code that `requested_schema` is `{"properties": {"confirm": {"type": "boolean"}}}`. That is a reasonable shortcut when you wrote both sides yourself, but a real client that talks to MCP servers it did not write cannot assume it knows the shape in advance -- it has to read `params.requested_schema` (a JSON Schema, the same shape as a tool's `inputSchema`) and build the answer dynamically:

```python
async def elicitation_callback(context, params: ElicitRequestParams) -> ElicitResult:
    print(f"\n  [server asks] {params.message}")
    schema = params.requested_schema
    answers = {}

    for field_name, field_schema in schema["properties"].items():
        prompt = f"   {field_schema.get('title', field_name)}: "
        if field_schema.get("type") == "boolean":
            raw = await asyncio.to_thread(input, prompt + "(y/n) ")
            answers[field_name] = raw.strip().lower().startswith("y")
        else:
            answers[field_name] = await asyncio.to_thread(input, prompt)

    return ElicitResult(action="accept", content=answers)
```

This walks whatever fields the server actually asked for, instead of assuming there is a field called `confirm`. This is the same principle a real product (a generic schema-to-form renderer) uses: read the JSON Schema, render one input per field, send back a dict keyed by whatever names the schema listed -- one generic function, not one hand-written callback per tool.

### A Real Bug This Pattern Exposes: Trusting `structured_content` Without Checking `is_error`

This is worth calling out because it produces a genuinely confusing failure if you miss it. A naive dispatcher looks like this:

```python
result = await mcp_client.call_tool(tool_call.function.name, arguments)
content = json.dumps(result.structured_content)     # BUG: no is_error check
```

When the fare-change `ToolError` fires on round 2, the SDK sets `result.is_error = True`, puts the real message in `result.content[0].text`, and leaves `result.structured_content = None` -- there is no structured output for a failed call. `json.dumps(None)` silently produces the **string** `"null"`. The model receives `"null"` as the tool result -- not an error, not a success, just a confusing token -- and may respond with a confident-sounding but false "your flight has been booked," because nothing in the message actually told it the booking failed.

The fix is the same error-first pattern used everywhere else in this chapter (Theory 05's `McpToolbox.call`):

```python
if result.is_error:
    content = "ERROR: " + result.content[0].text
else:
    content = json.dumps(result.structured_content)
```

With this in place, a stale-quote failure correctly shows the model the real message (`"ERROR: the fare changed since you were quoted Rs. 4900 (it is now Rs. 5150). call search_flights again, then try booking again."`), and a model that is actually reading its tool results will retry `search_flights` and `book_flight` on its own -- the same self-correcting behavior you already saw with mismatched genre casing in Problem 07.

---

## Theory 09: Progress Notifications

### The Problem

A tool that takes 30 seconds and says nothing until the end looks exactly like a tool that has hung. Progress notifications let the server send "3 of 10 done" messages *during* the call.

### How It Travels

When you pass a `progress_callback`, the client adds a `progressToken` to the request. The server sends progress notifications tagged with that token, then the final result, all in the same response stream:

```text
  CLIENT                                       SERVER
    | tools/call index_folder  (progressToken=7)  |
    | ------------------------------------------> |
    | <- notifications/progress  1/9 "apples.md"  |
    | <- notifications/progress  2/9 "bridges"    |
    |    ...                                      |
    | <- notifications/progress  9/9 "zebras"     |
    | <- result {files: 9, words: 2341}           |
```

Over Streamable HTTP, this is still **one** POST request. The server answers it with a `text/event-stream` response (the SSE format from Theory 03) and keeps that response open while the tool runs: each progress notification is one `data:` event, and the final result is the last event, after which the response ends. Remember the `Accept: application/json, text/event-stream` header every request carries? This is the reason: the client has to be ready for a streamed answer, because it cannot know in advance whether the tool will report progress.

```text
POST /mcp  (tools/call index_folder)
  <- HTTP 200, Content-Type: text/event-stream
  <- data: {"method": "notifications/progress", "params": {"progress": 1, "total": 9, ...}}
  <- data: {"method": "notifications/progress", "params": {"progress": 2, "total": 9, ...}}
     ...
  <- data: {"id": 4, "result": {...}}
  (response ends)
```

The server side is one line per step:

```python
await ctx.report_progress(progress=done, total=total_files, message=f"indexed {name}")
```

`progress` must go up every time. `total` is optional (leave it out if you do not know the total in advance). `message` is optional, a short human-readable note.

### The Callback Must Be `async def`

```python
async def on_progress(progress: float, total: float | None, message: str | None) -> None:
    ...
```

The SDK **awaits** your callback. If you write a plain `def`, Python still calls it (so your progress bar prints correctly), but it returns `None`, and `await None` fails with `TypeError: object NoneType can't be used in 'await' expression`. The SDK catches and logs that error instead of crashing, so you get correct-looking output with a pile of error noise mixed in. Easy to miss, easy to fix.

Running this on purpose shows exactly that split: the bar for file 1 prints, immediately followed by a traceback pointing at the SDK's own dispatch code, then the bar for file 2, then another traceback, one pair per file:

```text
  [##..................]  1/9  indexed apples.md
progress callback raised
Traceback (most recent call last):
  File ".../mcp/shared/jsonrpc_dispatcher.py", line 205, in _wrapped
    await fn(progress, total, message)
TypeError: object NoneType can't be used in 'await' expression
  [####................]  2/9  indexed bridges.md
progress callback raised
...
```

The `print()` inside your callback always runs first, because it is a normal synchronous statement -- the failure only happens *after* your function body has already finished, when the SDK tries to `await` whatever your function returned. A plain `def` with no `return` always returns `None`, and `None` is not awaitable, so every single call fails the same way, independently, without ever stopping the loop.

### `report_progress` Is One Specific Tool, Not "Notifications in General"

`ctx.report_progress` exists for exactly one job: telling the caller how far along a slow operation is. It is not a general-purpose "send any kind of notification" method. A different job -- telling a caller that some piece of *data* changed, not that an operation is progressing -- uses a different, dedicated method entirely: `ctx.notify_resource_updated(...)` (Theory 10). You would not reach for `report_progress` to announce "the inventory changed," and you would not reach for a resource-update notification to say "I am 40% done." Each kind of event in MCP has its own purpose-built method; there is no single generic "notify" call underneath that they all secretly share.

### `progress`, `total`, `message` Are a Fixed Shape, Reused by Every Tool

These three parameter names are not invented per tool -- every tool that reports progress, in any server, calls `report_progress` with this same shape: `progress` (how far along, a number that should only go up), `total` (optional -- the denominator, if you know it in advance), `message` (optional, a short human-readable note). What *is* specific to each tool is what `total` actually counts. In `index_folder`, `total` happens to equal `len(paths)` because the job here is naturally "one unit of work per file." A different slow tool might report progress against total bytes, total frames, or total API calls instead -- `report_progress`'s contract does not dictate what the unit is, only that whatever unit you pick should stay the same across every call within one run, so a client can always compute `progress / total` as a sensible fraction.

Likewise, `progress` itself is nothing magic -- it is just whatever number *you* choose to pass each time, usually a simple loop counter (`enumerate(paths, start=1)` in `index_folder`). The SDK does not compute it for you; it only carries whatever value you hand it to the client.

### The Client Side Is Just a Hook -- You Decide What Happens Inside It

Passing `progress_callback=on_progress` to `call_tool(...)` is the entire contract on the client side. The SDK's only responsibility is to call your function with `(progress, total, message)` every time a notification arrives, and `await` it. What the function body actually does is completely up to you -- print a text bar (as in this problem), update a GUI widget, write to a log file, push to a websocket -- the SDK never looks inside it or cares what it does, only whether it is awaitable.

### No Resuming

In older MCP, a dropped HTTP stream could be resumed with a `Last-Event-ID` header. In 2026-07-28 that is gone: if the connection drops, the call is cancelled on the server. For truly long jobs (minutes or hours), the protocol's answer is the separate **tasks** extension (see the last section), not a longer progress stream.

---

## Theory 10: Subscriptions and Where Statelessness Leaks

### The One Long-Lived Request

Everything so far has been one request in, one answer out. `subscriptions/listen` is different: the client opens it once and the stream stays open. The server pushes a short event every time something the client cares about changes.

```text
  WATCHER                 SERVER                 SHOPPER
     | listen(inventory://stock)                     |
     | ------------------> |                         |
     | <- ack              |                         |
     |                     | <---- sell(laptop, 1) --|
     |                     |  notify_resource_updated|
     | <- event: stock     |                         |
     |  changed            |                         |
     | read_resource ----> |                         |
     | <- laptop=4 ...     |                         |
```

The event only says "this changed". It does not carry the new data. The client reads the resource again to get it. If several changes happen quickly, you may get a single event for all of them, which is fine, because you always re-read the latest state anyway.

In code:

```python
async with client.listen(resource_subscriptions=["inventory://stock"]) as sub:
    async for event in sub:
        stock = await client.read_resource("inventory://stock")
        ...
```

You can also listen for `tools_list_changed=True` (the server's tool list changed, fetch it again), and the same for prompts and resources.

There is no replay: if the stream drops, events sent while you were away are gone. Open a new listen and read the resource again to catch up.

### Where Statelessness Leaks

A listen stream is attached to **one server process**. When `sell` runs, it notifies the listeners that *its own process* knows about. With two replicas:

```text
 watcher --listen--> replica A          (A knows about the watcher)
 shopper --sell----> replica B          (B changes stock, notifies ITS listeners: none)

 result: the watcher hears nothing, even though the stock really changed
```

(And in this toy server the stock dict itself is per-process too, the same trap as Theory 04.) Every other request in this chapter was happy on any replica. This one is not, because a listener is real, live state on one machine.

The fix is a shared message bus that every replica publishes to and subscribes from (Redis, NATS, or even a shared SQLite file), so that a change on B is delivered to listeners on A. In the SDK this is a constructor option on `MCPServer` (`subscriptions=`), and your tool code does not change at all. Building that bus is beyond this chapter, but now you know exactly why it exists.

---

## What Is Not Covered Here

- **Tasks** (`tasks/get`, `tasks/update`, `tasks/cancel`): for jobs that run for minutes or hours, a tool returns a task handle and the client polls it. In 2026-07-28 this moved out of the core protocol into an optional extension (`io.modelcontextprotocol/tasks`). The `mcp` 2.1.1 library has a general `Extension` base class but no ready-made tasks extension, so it is left out rather than built by hand.
- **URL-mode elicitation** (sending the user to a web page, for example to pay, instead of a form). Same MRTR mechanics as Problem 08, with a different kind of question.
- **Authorization** (OAuth for remote servers). Important for production, but a whole topic of its own.
- **Deprecated features** (Roots, Sampling, Logging, the old `initialize` handshake, sessions). You will still meet them in older code; the chapter 3 notes list what replaced each one.
