# What MCP Actually Is

## Table of contents

- [One sentence](#one-sentence)
- [The problem it solves](#the-problem-it-solves)
  - [What MCP is not](#what-mcp-is-not)
- [The three roles](#the-three-roles)
- [What a server exposes](#what-a-server-exposes)
- [JSON-RPC 2.0, in five minutes](#json-rpc-20-in-five-minutes)
  - [The error codes you will meet](#the-error-codes-you-will-meet)
  - [Dry-run: one complete exchange, by hand](#dry-run-one-complete-exchange-by-hand)
- [The 2026-07-28 revision: what was deleted](#the-2026-07-28-revision-what-was-deleted)
  - [Why they did it](#why-they-did-it)
  - [The ten methods](#the-ten-methods)
  - [The line that explains everything else](#the-line-that-explains-everything-else)
  - [Deprecated, not removed](#deprecated-not-removed)
  - [Where state went](#where-state-went)
- [Transports](#transports)
- [Gotchas people hit here](#gotchas-people-hit-here)
- [Connection forward](#connection-forward)


## One sentence

The **Model Context Protocol** is a standard shape for the conversation between a program
that holds a language model and a program that holds a capability, so that neither has to
know anything about the other beyond the protocol.

## The problem it solves

Before MCP, wiring a model to a tool meant writing glue. If you had four tools and wanted
them available in three different applications — your own agent, a chat client, an IDE —
you wrote twelve pieces of glue. Each one hand-declared the tool's JSON Schema, each one
converted the model's tool-call request into a function call, each one formatted the
result back into something the model could read, and each one did it slightly
differently. Change a tool's arguments and you edited three files in three repositories.

That is the classic *N × M* integration problem, and the classic answer to it is a
protocol. You define the shape of "here is a tool you may call" once, and then any
tool-provider that speaks it works with any model-host that speaks it. Four tools, three
applications, seven programs, zero glue.

The analogy people use is USB-C, and it is a good one for a specific reason: USB-C did
not make your laptop understand your monitor. It standardised the *socket*, so that the
laptop and the monitor could negotiate what they were without either vendor phoning the
other. MCP standardises the socket between models and capabilities. It says nothing about
what your tool does.

### What MCP is not

It is worth being blunt about this early, because it removes a lot of confusion later.

MCP is not an agent framework. It has no opinion about loops, planning, memory or
retries. It does not call the model. Your agent loop still does all of that; MCP only
changes where the tool definitions and tool results come from.

MCP is also not a model API. It never talks to Anthropic or OpenAI. A server has no idea
which model — or whether any model at all — is on the other side.

## The three roles

```text
   ┌──────────────────────── HOST ────────────────────────┐
   │  the application: Claude Code, an IDE, your agent    │
   │  owns the model connection and the user's trust      │
   │                                                      │
   │   ┌─────────── CLIENT ───────────┐  ┌── CLIENT ──┐   │
   │   │  one per server connection   │  │            │   │
   │   └──────────────┬───────────────┘  └──────┬─────┘   │
   └──────────────────┼─────────────────────────┼─────────┘
                      │  MCP  (JSON-RPC 2.0)    │
                      v                         v
              ┌───────────────┐         ┌───────────────┐
              │    SERVER     │         │    SERVER     │
              │  cafe-mcp     │         │  a git server │
              │  tools        │         │               │
              │  resources    │         │               │
              │  prompts      │         │               │
              └───────────────┘         └───────────────┘
```

The **host** is the application a person is actually using. It holds the model
connection, it holds the user's attention, and it is the only one of the three that can
ask a human anything. The **client** is the host's protocol-speaking half — one client
instance per server it is connected to. The **server** is the thing you are going to
write: a process that exposes capabilities and knows nothing about models.

The split between host and client matters for one reason. When a server needs a human
decision — *is this order correct?* — it cannot ask. It has no user. It can only tell the
client "I need this before I can finish", and the client, which does have a user, decides
whether and how to ask. Topic 08 is entirely about the mechanics of that.

## What a server exposes

Three kinds of thing, and the difference between them is *who decides to use them*.

A **tool** is an action the model may choose to invoke. `add_to_order`, `place_order`.
The model sees a name, a description and a JSON Schema, and it decides. This is the
primitive you will spend the most time on, because it is the one where a bad description
costs you real behaviour.

A **resource** is data the *client* fetches and puts into context. `cafe://menu`. Nothing
about a resource is a decision the model makes — the host or the user attaches it, the
way you attach a file to a chat message. Resources are addressed by URI, and they can be
templated: `cafe://drinks/{slug}`.

A **prompt** is a reusable message template the *user* invokes, usually surfacing in the
host as a slash command. `/order_for_me`. The server supplies the wording; the user
supplies the arguments and triggers it.

The three-way split is a control question, not a technical one:

```text
   tool      →  the MODEL decides to use it
   resource  →  the HOST or USER attaches it
   prompt    →  the USER invokes it
```

## JSON-RPC 2.0, in five minutes

Every MCP message is a JSON-RPC 2.0 message. There are exactly three shapes and you
should be able to write all of them from memory by the end of this section.

A **request** has an `id`, and expects a reply:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

A **response** carries the same `id` back, with either `result` or `error` — never both:

```json
{"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
```

```json
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}
```

A **notification** is a request with no `id`, which means no reply is coming and none
should be sent:

```json
{"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 3}}
```

That is the whole of JSON-RPC that MCP uses. The `id` may be a string or a number; it
only has to be unique among the requests currently in flight on that connection.

### The error codes you will meet

JSON-RPC reserves a band of codes, and MCP 2026-07-28 formally carved up the
server-error range for itself.

| Code | Meaning | Where it comes from |
|------|---------|---------------------|
| `-32700` | Parse error — the body was not JSON | JSON-RPC |
| `-32600` | Invalid request — not a valid JSON-RPC envelope | JSON-RPC |
| `-32601` | Method not found | JSON-RPC |
| `-32602` | Invalid params | JSON-RPC |
| `-32603` | Internal error | JSON-RPC |
| `-32000` to `-32019` | implementation-defined, grandfathered for existing SDK use | MCP policy |
| `-32020` | `HeaderMismatch` — an HTTP header disagreed with the body | MCP spec |
| `-32021` | `MissingRequiredClientCapability` | MCP spec |
| `-32022` | `UnsupportedProtocolVersion` | MCP spec |
| `-32099` | end of the range reserved to the MCP specification | MCP policy |

Two of these are new in this revision and were renumbered during its draft period, so
older blog posts will show `-32001` and `-32004`. The current numbers are `-32020` and
`-32022`. Topic 12 makes the server emit `-32022` on purpose.

One more, which is a genuine change rather than a renumber: a missing resource used to be
`-32002`, and is now plain `-32602` *Invalid params*. The reasoning is that asking for a
resource that does not exist is a bad argument, not a special condition.

### Dry-run: one complete exchange, by hand

This is what the café will actually send and receive in topic 03. Read it slowly; every
field is explained below it.

**The client sends:**

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "get_drink",
    "arguments": {"slug": "flat-white"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": {"name": "cafe-raw-client", "version": "1.0"},
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

**The server replies:**

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "resultType": "complete",
    "isError": false,
    "content": [{"type": "text", "text": "{\"name\": \"Flat White\", \"caffeine_mg\": 130}"}],
    "structuredContent": {"name": "Flat White", "caffeine_mg": 130},
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {"name": "cafe-mcp", "version": "0.1.0"}
    }
  }
}
```

Walking the fields:

`id: 7` matches on both sides. If it did not, the client would have no way to know which
outstanding request this answered.

`params.name` is the tool being called, `params.arguments` is the object that must
validate against that tool's `inputSchema`.

`params._meta` is where MCP puts everything that is *about* the request rather than *in*
it. Note it is inside `params`, not at the top level of the envelope. This is the single
most common mistake when writing a client by hand. The keys are namespaced with
`io.modelcontextprotocol/` precisely so that your own `_meta` keys can never collide with
the protocol's.

`result.resultType` is `"complete"`. It is new in this revision and it is required. The
other legal value is `"input_required"`, which means *this is not the answer, it is a
question* — that is the MRTR pattern in topic 08. Every client must now check this field
before treating a result as an answer.

`result.content` is what goes into the model's context: a list of blocks, here one text
block. `result.structuredContent` is the same information as a typed object, for code
rather than for the model. You get both, and the SDK fills both in from one return value.

`result.isError` is `false`. When a tool fails in an expected way, this is `true` and
`content` carries the explanation — but the JSON-RPC envelope still says `result`, not
`error`. That distinction is the whole of topic 03.

`result._meta` carries `serverInfo`. The server identifies itself on every single result
now, because there is no longer a handshake in which it could have identified itself
once.

## The 2026-07-28 revision: what was deleted

Now the part that makes this folder necessary.

Every MCP tutorial written before August 2026 — including the older folder next to this
one — opens with a handshake. The client sends `initialize`, the server replies with its
capabilities, the client sends `notifications/initialized`, and from then on the
connection is a *session*. Over HTTP, the server minted an `Mcp-Session-Id` header and
the client echoed it on every subsequent request.

All of that is gone.

```text
BEFORE (2025-11-25 and earlier)          AFTER (2026-07-28)
─────────────────────────────────        ──────────────────────────────
client ──initialize──────────> server    client ──tools/list──────────> server
       <─capabilities─────────                    (version + capabilities
client ──initialized─────────>                     ride in _meta)
       <─Mcp-Session-Id: abc─                <─result + serverInfo──────
                                         
client ──tools/list──────────>            ...and that is the whole thing.
       (Mcp-Session-Id: abc)              Any instance can answer.
       <─result──────────────

    every later request must reach
    the instance holding session abc
```

### Why they did it

Because the session was a lie that cost money. A session pins a client to one server
process. Put three instances of your server behind a load balancer and every request
after `initialize` must reach the same one, so you need sticky sessions, or a shared
session store, or both. That rules out serverless functions, rules out edge deployment,
and rules out scaling to zero — for a protocol whose payload is almost always a single
self-contained question.

Removing sessions makes an MCP request an ordinary HTTP POST. Your existing
infrastructure — load balancers, gateways, CDNs, WAFs — can treat it like any other
traffic, because it now *is* like any other traffic.

### The ten methods

At 2026-07-28 there are exactly ten things a client can ask a server. You verified this
yourself in [SETUP.md](../SETUP.md):

```text
completion/complete          resources/read                server/discover
prompts/get                  resources/templates/list      subscriptions/listen
prompts/list                 resources/list                tools/call
                                                           tools/list
```

Relative to the previous revision, these were **removed**: `initialize`,
`notifications/initialized`, `ping`, `logging/setLevel`, `resources/subscribe`,
`resources/unsubscribe`, and `notifications/roots/list_changed`.

Two were **added**: `server/discover`, which replaces the discovery half of what
`initialize` used to do, and `subscriptions/listen`, which replaces the whole
GET-stream-plus-subscribe machinery with one long-lived POST.

`ping` being gone surprises people. Health checks now go to an ordinary HTTP route of
your own — which is why every server in this folder from topic 01 onward has a
`/healthz`.

### The line that explains everything else

In the other direction — server asking client — the count is zero. From
`mcp_types/methods.py`, in the SDK you have installed, verbatim:

```python
# 2026-07-28: none (no server-to-client requests at this version)
```

Sit with that. Previously a server could send the client three kinds of request:
`roots/list` (*what directories may I see?*), `sampling/createMessage` (*please ask your
model this for me*), and `elicitation/create` (*please ask your user this for me*). That
entire category of message no longer exists.

It did not get replaced feature-by-feature. It got *inverted*. A server that needs
something from the client no longer asks; it **returns**. It answers the original request
with `resultType: "input_required"` and a description of what it needs, and the client —
if it chooses to — retries the original call with the answers attached. That is **MRTR**,
Multi Round-Trip Requests, and it is the single most interesting idea in the revision.
Topic 08 builds it.

The reason this matters architecturally: a server-to-client *request* requires a
bidirectional channel that stays open, which requires a session, which is the thing being
deleted. Inverting the direction is what made removing sessions possible at all.

Notifications, note, still flow server-to-client. Those were never requests — nobody is
waiting for a reply — so they survive unchanged, riding on the response stream of the
request they belong to. Topic 10 covers that distinction properly.

### Deprecated, not removed

Three features remain in the specification but are on a twelve-month clock. Do not build
on them:

| Deprecated | What to do instead |
|------------|--------------------|
| **Roots** — server asks which directories it may access | Pass paths as tool arguments, resource URIs, or server configuration |
| **Sampling** — server borrows the client's model | Call the model provider's API directly from your server |
| **Logging** (`notifications/message`) | Write to stderr, or emit OpenTelemetry |
| HTTP+SSE transport (the 2024-11-05 two-endpoint design) | Streamable HTTP |
| OAuth Dynamic Client Registration (RFC 7591) | Client ID Metadata Documents |

There is an apparent contradiction here that is worth naming now, because you will trip
over it in topic 08. The MRTR mechanism can carry three kinds of input request, and its
type union still lists `CreateMessageRequest` and `ListRootsRequest` alongside
`ElicitRequest`. That is because MRTR is *how* you would carry sampling and roots if you
still used them. Both are deprecated, so a new server should not — leaving
`ElicitRequest` as the only member of that union worth reaching for. The union is wide for
backward compatibility; your usage should be narrow.

### Where state went

If sessions are gone, and a server needs to remember a shopping cart across four calls,
where does the cart live?

In an argument. The server mints a **handle** — an opaque, signed, expiring string — and
returns it. The client passes it back on the next call. The server verifies it, updates
it, and returns a new one. No instance ever remembers anything, and any instance can pick
up where another left off.

This folder does it three times, deliberately, so that the pattern stops looking like a
trick:

```text
topic 06   cursor         a pagination position
topic 07   order          the shopping cart itself
topic 08   requestState   where a half-finished request had got to
```

Same idea each time. Something that used to be server memory becomes a value on the wire.

## Transports

Two, and only one of them is interesting for this folder.

**stdio** — the server is a subprocess, requests arrive on its stdin, responses leave on
its stdout. This is how local tools are shipped, and it is why logging to stdout corrupts
everything: stdout *is* the protocol channel. Simple, no network, no auth, one client.

**Streamable HTTP** — the server is an HTTP server with a single endpoint, normally
`/mcp`. The client POSTs a JSON-RPC message; the response is either a plain JSON body or
a Server-Sent Events stream, depending on what the request asked for. Everything in this
folder uses this, because statelessness is only interesting when there is more than one
instance to spread across.

The word "streamable" refers to that second possibility: a single POST whose response can
arrive as a stream of events rather than one body. That is how progress notifications get
out during a long tool call, and topic 10 is where it stops being an abstraction.

The older **HTTP+SSE** transport — two endpoints, a GET that stays open for
server-to-client traffic and a POST for client-to-server — is deprecated. If you find a
tutorial with an `/sse` endpoint and a separate `/messages` endpoint, it is from 2024.

## Gotchas people hit here

**Reading a pre-August-2026 tutorial and wondering why `initialize` fails.** It does not
fail; the method simply does not exist at this revision. The SDK still contains
`InitializeRequest` because it supports older revisions too. Its presence in the package
is not permission to use it.

**Assuming stateless means the server cannot have state.** It can have all the state it
likes — a database, a queue, a cache. What it cannot have is state *keyed to a
connection*. The café has a menu, and instances share nothing to serve it.

**Putting `_meta` at the top level of the JSON-RPC envelope.** It goes inside `params`.
This is worth writing on your hand.

**Expecting a failing tool to produce a JSON-RPC `error`.** It normally does not. A tool
that fails in an expected way returns a *successful* JSON-RPC response whose `result` has
`isError: true`, because the failure is information for the model, not a protocol
violation. Topic 03.

**Thinking `stateless_http=True` is the default.** It is not, in this SDK. Get it wrong
and a well-behaved modern client falls down a legacy code path and gets told
`Bad Request: Missing session ID`. This is the first thing topic 01 makes you prove.

## Connection forward

You now know what the pieces are called and what the 2026-07-28 revision took away. What
you have not yet seen is a single byte on the wire.

Topic 01 fixes that: a thirty-line server, and then you POST to it by hand with `curl`
and read the raw JSON-RPC — including the request that deliberately omits the version
header, so you can watch the SDK route you into the legacy path and see what "not
stateless" actually looks like.

Does this make sense? Want me to go deeper on any part — the JSON-RPC framing, the
host/client/server split, or why inverting the request direction was the thing that
unlocked statelessness?
