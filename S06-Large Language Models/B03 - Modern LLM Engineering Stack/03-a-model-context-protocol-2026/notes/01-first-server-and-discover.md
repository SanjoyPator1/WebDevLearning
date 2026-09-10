# First Server, and `server/discover`

## Table of contents

- [One sentence](#one-sentence)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — What actually travels](#layer-2-what-actually-travels)
  - [The endpoint](#the-endpoint)
  - [The request](#the-request)
  - [The `_meta` envelope](#the-_meta-envelope)
  - [The response](#the-response)
  - [`server/discover`](#serverdiscover)
- [Layer 3 — Dry-run: framing one request by hand](#layer-3-dry-run-framing-one-request-by-hand)
- [The code](#the-code)
  - [`MCPServer(name=..., version=..., instructions=...)`](#mcpservername-version-instructions)
  - [The `@mcp.tool()` decorator does four jobs](#the-mcptool-decorator-does-four-jobs)
  - [`@mcp.custom_route("/healthz", methods=["GET"])`](#mcpcustom_routehealthz-methodsget)
  - [`stateless_http=True`](#stateless_httptrue)
- [The experiment that teaches the most](#the-experiment-that-teaches-the-most)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

An MCP server over streamable HTTP is an ordinary HTTP server with one endpoint that
accepts JSON-RPC POSTs, and `server/discover` is how a client finds out what it can do
now that there is no handshake in which to be told.

## The problem this topic solves

Topic 00 said the `initialize` handshake is gone. That leaves a hole. `initialize` was
doing two jobs at once, and it is worth separating them because the revision treats them
completely differently.

Job one was **discovery**: *what version do you speak, what features do you have, who
are you?* Job two was **session establishment**: *remember me, here is a session id, we
now have a conversation.*

Job two was deleted outright. Job one moved to a new method, `server/discover`, and — the
part people miss — was also made *optional to call*, because everything discovery
returned now travels on every request anyway.

```text
     initialize  (2025 and earlier)
     ├── discovery ─────────────► server/discover  (2026, and optional)
     └── session ───────────────► deleted
```

## Layer 1 — The intuition

Think of the old handshake as checking in at a hotel desk. You give your name, they give
you a room key, and from then on the key is what identifies you. Lose the key and you are
nobody. Worse, the key only works at *that* hotel — if the chain opens a second building
you cannot walk into it.

The new model is closer to showing your passport every time you buy something. It feels
wasteful — you repeat yourself constantly — but it means any till in any branch can serve
you, and there is no key to lose, expire, or leak. The repetition is a few hundred bytes
of `_meta`; what it buys is that any process can answer any request.

`server/discover` is then the equivalent of the sign in the window listing what the shop
sells. You *can* read it before you walk in. You do not have to.

## Layer 2 — What actually travels

### The endpoint

One URL, by convention `/mcp`. Every method — `tools/list`, `tools/call`, all ten of them
— is a POST to that same URL. The method name is in the JSON body, and *also* in a
header. We will get to why in a moment.

### The request

Here is a complete, minimal, legal 2026-07-28 request. Nothing can be removed from it.

```json
POST /mcp HTTP/1.1
Host: 127.0.0.1:3010
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/list

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

Four headers and one body. Taking them in turn:

**`Content-Type: application/json`** — the body is a JSON-RPC message.

**`Accept: application/json, text/event-stream`** — you must accept *both*, because the
server chooses. A quick tool call comes back as one JSON body; a tool that reports
progress comes back as a stream of SSE events on the same response. This is what
"streamable HTTP" means and it is the whole of topic 10.

**`MCP-Protocol-Version: 2026-07-28`** — the revision you are speaking. Required on
modern requests, and it must agree with the copy inside `_meta`.

**`Mcp-Method: tools/list`** — the JSON-RPC method, mirrored into a header. This is new in
this revision and it exists for exactly one reason: a gateway or load balancer can route,
rate-limit, or authorise on the method **without parsing the JSON body**. Body parsing at
the edge is expensive and, for a proxy, often impossible. There is a companion header,
`Mcp-Name`, for the three methods that target something by name — topic 13 covers both
properly.

Then the body. `jsonrpc`, `id`, `method`, `params` are plain JSON-RPC 2.0. The interesting
part is `params._meta`.

### The `_meta` envelope

`_meta` is where MCP puts everything that is *about* the request rather than *in* it.
Two keys are **required** and one is a SHOULD:

| Key | Required? | What it is |
|-----|-----------|------------|
| `io.modelcontextprotocol/protocolVersion` | **required** | the revision this request speaks |
| `io.modelcontextprotocol/clientCapabilities` | **required** | what the client can do; `{}` is legal |
| `io.modelcontextprotocol/clientInfo` | SHOULD | `{"name": ..., "version": ...}` |

I checked all three against the running server rather than trusting the spec prose. Omit
`clientCapabilities` and you get:

```json
{"code": -32602, "message": "params._meta is missing the required envelope key(s): io.modelcontextprotocol/clientCapabilities"}
```

Omit `clientInfo` and the request succeeds. So the SDK enforces the two MUSTs and lets
the SHOULD slide, which is exactly right.

The `io.modelcontextprotocol/` prefix is deliberate: it reserves a namespace, so your own
`_meta` keys — trace ids, tenant hints, whatever — can never collide with a future
protocol key.

**`_meta` goes inside `params`.** Not at the top level of the JSON-RPC envelope. This is
the most common hand-rolled-client bug there is, and the error message you get is
unhelpfully identical to having no `_meta` at all:

```text
params._meta must be an object carrying the required
'io.modelcontextprotocol/protocolVersion' and
'io.modelcontextprotocol/clientCapabilities' envelope keys
```

If you see that and you are *sure* you sent `_meta` — check which level you put it on.

### The response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "tools": [ ... ],
    "ttlMs": 0,
    "cacheScope": "private",
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {"name": "cafe-hello", "version": "0.1.0"}
    }
  }
}
```

`resultType: "complete"` is required and new. The alternative is `"input_required"`,
meaning *this is a question, not an answer* — topic 08. Every client must check.

`ttlMs` and `cacheScope` are also new and required on list-shaped results. `ttlMs: 0`
means "do not cache"; `cacheScope: "private"` means "no shared intermediary may cache
this". Topic 02 turns them into something useful.

`_meta.serverInfo` identifies the server. On **every** reply. There is no handshake in
which to say it once, so it is repeated forever. That is the honest cost of
statelessness, and it is cheap.

### `server/discover`

The one RPC a server **MUST** implement. Here is the real reply from `t01_hello.py`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "supportedVersions": ["2026-07-28"],
    "capabilities": {
      "tools":     {"listChanged": true},
      "resources": {"listChanged": true, "subscribe": true},
      "prompts":   {"listChanged": true}
    },
    "instructions": "A throwaway server used to demonstrate MCP request framing. ...",
    "ttlMs": 0,
    "cacheScope": "private",
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {"name": "cafe-hello", "version": "0.1.0"}
    }
  }
}
```

`supportedVersions` is a list, not a single value, because a server can serve several
revisions at once. This one serves only 2026-07-28.

Note the asymmetry, which is the point of the whole method: implementing it is
**mandatory for the server**, calling it is **optional for the client**.

To understand why, compare it to the old pre-2026 protocol:

- **Old `initialize` handshake:** Was mandatory for both sides on every single
  connection. The client and server were forced to exchange greetings and establish
  a session ID before any tool could be called. If a client sent a tool call first,
  the server rejected it.
- **New `server/discover` method:** Acts like a menu board hanging outside a shop.
  - The **server must** hang the menu board up (in code, `MCPServer` in `t01_hello.py`
    handles `server/discover` automatically).
  - But reading it is **optional for the client**. A client that already knows what
    tools and version the server uses can skip discovery entirely and send
    `tools/call` on its very first packet (try running `bash curl/01_call_hello.sh`
    directly without running `01_discover.sh` first — it works immediately!).

```text
OLD (Pre-2026: Mandatory handshake & session)
Client                                    Server
  |--- 1. initialize ---------------------->|  (Mandatory)
  |<-- 2. initialize result (session_id) ---|  (Mandatory)
  |--- 3. initialized notification -------->|  (Mandatory)
  |--- 4. tools/call ---------------------->|  (Finally work happens)
  |<-- 5. result ---------------------------|

NEW (2026-07-28: Stateless & Asymmetric)
Client (already knows the tool)           Server
  |--- 1. tools/call (with _meta) --------->|  (Directly on 1st packet!)
  |<-- 2. result ---------------------------|
```

There is no `extensions` key in that output. The spec adds an `extensions` slot to
capabilities — that is where `io.modelcontextprotocol/tasks` and friends would be
advertised — but mcp 2.1.1 omits the key rather than emitting an empty object. Absent
means "none", not "does not support extensions".

## Layer 3 — Dry-run: framing one request by hand

Let us build the `tools/call` request for `hello(name="Sanjoy")` from nothing, deciding
each piece.

**Step 1 — which URL?** One endpoint for everything: `http://127.0.0.1:3010/mcp`.

**Step 2 — which JSON-RPC shape?** We want a reply, so a *request*, so it needs an `id`.
Pick `3`. It only has to be unique among requests currently in flight.

**Step 3 — the method.** `tools/call`. Goes in the body as `"method"`, and mirrored into
the `Mcp-Method` header.

**Step 4 — the params.** `tools/call` takes `name` (which tool) and `arguments` (an
object that must validate against that tool's `inputSchema`).

```json
"params": {"name": "hello", "arguments": {"name": "Sanjoy"}}
```

Note `name` appears twice with two different meanings: `params.name` is the *tool's* name,
`arguments.name` is the tool's *parameter* called name. Coincidence, not structure.

**Step 5 — `Mcp-Name`.** `tools/call` is a name-bearing method, so `params.name` must be
mirrored into the `Mcp-Name` header. Get this wrong and the server rejects the request
before your tool is ever reached — verified:

```text
Mcp-Name: wrong_tool  ->  -32020  "mcp-name header does not match the request body's 'name' parameter"
no Mcp-Name at all    ->  -32020  same message
```

**Step 6 — `_meta`.** Two required keys, inside `params`.

**Step 7 — assemble.**

```bash
curl -sS http://127.0.0.1:3010/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: hello' \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "hello",
      "arguments": {"name": "Sanjoy"},
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}
      }
    }
  }'
```

**Step 8 — read the reply.**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "resultType": "complete",
    "isError": false,
    "content": [{"type": "text", "text": "Hello, Sanjoy! You are talking to an MCP server."}],
    "structuredContent": {"result": "Hello, Sanjoy! You are talking to an MCP server."},
    "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "cafe-hello", "version": "0.1.0"}}
  }
}
```

`content` is for the model. `structuredContent` is the same information for code. The SDK
produced both from one `return` statement — and wrapped the bare string in
`{"result": ...}` because a JSON object was needed and a string is not one.

## The code

`solved/t01_hello.py` is about a hundred lines, most of it comments. Four things in it
are worth pausing on.

### `MCPServer(name=..., version=..., instructions=...)`

`name` and `version` become `serverInfo` on every reply. `instructions` is free text
handed to the model by clients that ask for it — a place to say things that do not fit in
any one tool's description. Write it for a model.

### The `@mcp.tool()` decorator does four jobs

It registers the function so it shows up in `tools/list`; it converts the type hints into
`inputSchema`; it converts the return hint into `outputSchema`; and it uses the
**docstring as the tool's description**.

That last one deserves emphasis. The docstring is not documentation — it is the prompt
the model reads when deciding whether to call your tool. Look at what came back on the
wire:

```json
"description": "Greet someone by name.\n\n    Use this only to check that the connection to this server works. ...
```

Indentation and all. It goes to the model verbatim. So write docstrings that say *when to
reach for this tool*, not just what the arguments mean. Topic 02 goes further into this,
because it is the highest-leverage thing about writing MCP tools and it looks like a
detail.

### `@mcp.custom_route("/healthz", methods=["GET"])`

`ping` was removed in this revision, so there is no protocol-level liveness check. Health
checks need an ordinary HTTP route, mounted on the same Starlette app as `/mcp`.
Verified: sending `ping` now gets you

```json
{"code": -32601, "message": "Method not found", "data": "ping"}
```

Every server from here on has a `/healthz` for this reason.

### `stateless_http=True`

The most important argument in the file, because **it is not the default**:

```python
mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)
```

`run_streamable_http_async` declares `stateless_http: bool = False`. Leave it off and the
SDK keeps the legacy session machinery alive.

Here is what that actually looks like. Same request, no `MCP-Protocol-Version` header, two
servers:

```text
stateless_http=True   ->  HTTP 200, a working tools/list result

stateless_http=False  ->  HTTP 400
                          mcp-session-id: b63071cfb770477199385ac25b3d2aa7
                          {"error": {"code": -32600,
                                     "message": "Bad Request: Missing session ID"}}
```

Note the cruelty of it: the failing server *mints a session id and puts it in the error
response*, which tells you exactly nothing useful and sends you hunting for a bug in your
client. The client was fine. The server was in the wrong era.

## The experiment that teaches the most

Run `bash curl/01_no_version_header.sh` against the stateless server and look at what
comes back. Two things change at once.

**The framing changes.** With modern headers you get `content-type: application/json` and
one JSON body. Without them you get `content-type: text/event-stream` and:

```text
event: message
data: {"jsonrpc":"2.0","id":4,"result":{"tools":[...]}}
```

Same information, different envelope. The headers you send decide which. Any client you
write by hand must parse both — which is why every client in this folder has a
`_parse_jsonrpc` helper that checks the content type first.

**The result shape changes.** This is the subtle one. Compare the `result` keys:

```text
with modern headers  ->  ['_meta', 'cacheScope', 'resultType', 'tools', 'ttlMs']
without              ->  ['tools']
```

No `resultType`. No `ttlMs` or `cacheScope`. No `_meta.serverInfo`. You did not get a
degraded 2026 response — you got a **2025-11-25 response**. The SDK is dual-era: it looks
at your headers, decides which revision you are speaking, and serves that revision's
result shape.

This is worth internalising, because it is how the whole ecosystem will behave for the
next year. The same server serves old and new clients, and it is your headers that pick
which one you are. That also explains a result that looks wrong at first: send
`MCP-Protocol-Version: 2025-06-18` and you do **not** get an error — you get a legacy
response, cheerfully. You only get `-32022` for a version the server has never heard of:

```json
{"code": -32022, "message": "Unsupported protocol version",
 "data": {"supported": ["2026-07-28"], "requested": "2099-01-01"}}
```

Note that the error hands you the list of versions it *does* support, so the client's
recovery is a single retry. Topic 12 makes a whole lesson of that two-request loop, since
it is the entirety of version negotiation now that there is no handshake to negotiate in.

## Gotchas

**`stateless_http=True` is not the default.** Said three times in this chapter on purpose.

**`_meta` goes inside `params`.** Also said twice.

**`clientCapabilities` is required even when empty.** `{}` is the correct value for a
client that can do nothing special. Omitting the key entirely is an error.

**The header version and the `_meta` version must agree.** Disagree and you get `-32020`:
`"mcp-protocol-version header does not match the request envelope's protocol version"`.
The duplication is not redundant — the header exists for proxies that do not parse
bodies, and the body copy exists for transports that have no headers, like stdio.

**`Mcp-Method` is required, not optional.** Omit it and you get `-32020`, with a message
that says "does not match" rather than "missing", which is momentarily confusing. The SDK
treats absent and wrong identically.

**`GET /mcp` does not return 405.** The specification says a GET to the endpoint should be
rejected with 405 Method Not Allowed, because the old two-endpoint HTTP+SSE design used a
long-lived GET and that design is gone. mcp 2.1.1 instead opens an SSE stream and holds
it, so your `curl` hangs until it times out. This is an SDK deviation from the spec, not
something your server did. It is harmless, but it will waste ten minutes of your life if
you meet it without warning.

**An unknown tool name is not a JSON-RPC error.** It comes back as a *successful*
response whose result has `isError: true`:

```json
{"result": {"content": [{"type": "text", "text": "Unknown tool: nope"}],
            "isError": true, "resultType": "complete"}}
```

The spec's prose reads as though this should be a protocol-level error. In mcp 2.1.1 it is
not. Topic 03 explains why that is actually the better design.

## Your turn

Open `solutions/t01_hello.py`. Five TODOs. The one that matters is TODO 5 — if
`curl/01_no_version_header.sh` gives you "Bad Request: Missing session ID", you have
reproduced the single most common 2026-era MCP bug in your own code, which is the best
possible way to learn it.

## Connection forward

You can now frame a request and read a reply. What you have is a server with one useless
tool.

Topic 02 makes it a café. The subject is `tools/list` in earnest: how a Python signature
becomes a JSON Schema, what the four `ToolAnnotations` hints actually promise, and why
the spec now asks you to return tools in a *deterministic order* — a two-line change that
turns out to be about the model's prompt cache and therefore about your bill.

Does this make sense? Want me to go deeper on any part — the `_meta` envelope, the
dual-era response shapes, or why `Mcp-Method` duplicates something already in the body?
