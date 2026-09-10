# The Assembled Café — Raw Client vs. SDK Client

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [Assembling one server out of nine topics' tools](#assembling-one-server-out-of-nine-topics-tools)
  - [What the SDK client builds for you, on every single call](#what-the-sdk-client-builds-for-you-on-every-single-call)
  - [The one thing it will not do for you: elicitation_callback](#the-one-thing-it-will-not-do-for-you-elicitation_callback)
  - [Progress: the callback must be a coroutine](#progress-the-callback-must-be-a-coroutine)
  - [A distinction the SDK does not paper over](#a-distinction-the-sdk-does-not-paper-over)
  - [Three ways to connect, one object](#three-ways-to-connect-one-object)
- [Layer 3 — Dry-run: place_order, side by side](#layer-3-dry-run-place_order-side-by-side)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)

## One sentence

Every fact this whole folder has spent fourteen topics extracting by hand — the `_meta`
envelope, the header mirroring, the SSE-vs-JSON detection, and above all the two-round
MRTR retry — is exactly what `mcp.client.Client` automates, and the only way to actually
see that clearly is to watch the same nine-topic café answer a raw hand-built client and
the official one, back to back.

## Where this sits

`tests/wire.py` said it plainly from topic 01 onward: *"there is deliberately NO SDK
client in here."* That was the right call for testing — an SDK client hides exactly the
things a wire-level test needs to see going wrong. It also meant this whole folder has
never actually used the thing almost everyone building against MCP will use in practice.
This topic closes that gap on purpose, last, after the wire itself holds no more
surprises: `solved/cafe_project.py` assembles nine earlier topics' tools into one real
server, and two client scripts — `solved/raw_client.py` and `solved/sdk_client.py` — walk
the identical sequence through it, one built entirely by hand and one through
`mcp.client.Client`.

## The problem this topic solves

Nobody should write `tests/wire.py`'s `rpc()` helper by hand in a real application, and
nobody should have to take on faith what a client library is doing with their requests
either. Both things are true at once, and the only way to hold both without contradiction
is to have actually built the raw version first — which this folder now has — and then
look at the SDK version with full knowledge of what it is standing in for, not as a black
box to trust blindly.

## Layer 1 — The intuition

Think of the raw client as driving with a paper map, and the SDK client as driving with a
GPS unit. Both get you to the same coffee shop. The GPS is obviously what you would use
every day — nobody navigates a real city with the paper map out of principle. But someone
who has never once read a paper map treats the GPS's instructions as unquestionable, and
when it says something confusing ("recalculating..."), they have no independent way to
tell if the GPS is right, glitching, or asking them to do something reasonable it just
explained badly. Fourteen topics of reading the paper map means the GPS's instructions in
this last topic land as *recognizable* — "oh, that's the `_meta` envelope, it just built
it for me" — rather than mysterious.

## Layer 2 — The mechanics

### Assembling one server out of nine topics' tools

`solved/cafe_project.py` does not reimplement a single tool. `@mcp.tool(...)`,
`@mcp.resource(...)`, and `@mcp.prompt(...)` are *decorator factories* — calling
`mcp.tool()` returns a decorator, and applying that decorator to a function registers it
and hands the exact same function back, unchanged. Nothing requires the function and the
`mcp` object doing the registering to have been defined in the same file. So the whole
project is, functionally, nine import lines and nine registration lines:

```python
import t07_order_token
...
mcp.tool()(t07_order_token.add_to_order)
mcp.tool()(t07_order_token.view_order)
```

`tests/test_wire_load_balancer.py` and `tests/test_wire_subscriptions.py` already used
this exact trick to build a second, independent `MCPServer` out of one topic's tools, to
prove something about two processes. This file uses it on purpose, across topics 03, 04,
05, 06, 07, 08, 10, 11, and 13, to build the one café a real client would actually want to
talk to — and because `add_to_order` (07), `place_order` (08), and `brew` (10) all read
and write the exact same signed-token shape from `cafe_mcp.orders`, assembling them
together produces something none of the individual topics ever demonstrated: a token
minted by one tool, handed to a second, handed to a third, in one real conversation.

### What the SDK client builds for you, on every single call

Everything `solved/raw_client.py` does by hand, `solved/sdk_client.py` never mentions:

- The `_meta` envelope (`protocolVersion`, `clientInfo`, `clientCapabilities`) — built
  once per call in the raw client's `meta()` helper; never appears in the SDK version at
  all.
- `Mcp-Method` and `Mcp-Name` header mirroring — the raw client's `headers_for()`
  function; the SDK client never touches an HTTP header directly.
- Detecting whether a response came back as plain JSON or a single-frame SSE stream — the
  raw client's `call()` checks `content-type` by hand; `client.call_tool(...)` just
  returns a `CallToolResult`, framing already resolved.
- Version negotiation itself. `client.protocol_version` reads `'2026-07-28'` after
  connecting with no code asking for it — the `mode="auto"` default (documented directly
  in the SDK's own source as *"discover, fall back to initialize"*) tries
  `server/discover` first and would fall back to the legacy handshake against an
  older-only server, the exact irony topic 12 built a whole chapter around, now handled
  silently underneath one `async with Client(...)`.
- Attribute naming. The wire JSON says `isError` and `structuredContent` (camelCase, per
  the spec). The SDK hands back a `CallToolResult` with `.is_error` and
  `.structured_content` (snake_case) — Pydantic field aliases doing the translation. Reach
  for `.isError` on an SDK result and you get a plain `AttributeError`, not a wire-shaped
  answer; this was hit directly while building `sdk_client.py`.

### The one thing it will not do for you: elicitation_callback

`place_order` returns `InputRequiredResult` on its first call — topic 08's whole subject.
Call it through the SDK client with no further setup and `call_tool` does not hand that
result back to you the way a raw call would. Verified directly:

```
mcp.shared.exceptions.MCPError: Elicitation not supported
```

`Client.call_tool` DRIVES the entire MRTR round trip internally, given an
`elicitation_callback` — a coroutine matching `ElicitationFnT`'s shape
(`(context, params) -> ElicitResult | ErrorData`). Supply one, and a single
`await client.call_tool("place_order", {"order": token})` produces the *final*, committed
result. Round 1's `input_required`, the `requestState` it carried, and round 2's retry
with `inputResponses` built in the exact wire shape `curl/08_place_round2.sh` always
sent by hand — none of it surfaces to your code. The SDK does not *invent* an answer to
"what name goes on the cup?" (there is no silent default accept) — it automates every
mechanical part of the round trip and asks your callback to supply only the one thing a
machine cannot: the actual decision. Declining through that same callback
(`ElicitResult(action="decline")`) still comes back as a normal, successful
`CallToolResult` with `is_error=False` — reconfirming topic 08's "declining is a normal
outcome, not a failure" finding, this time through the client that will actually get used.

### Progress: the callback must be a coroutine

`client.call_tool("brew", {...}, progress_callback=on_progress)` parses every
`notifications/progress` frame off the SSE stream and calls `on_progress(progress, total,
message)` once per event — no manual SSE line-splitting anywhere in `sdk_client.py`. One
real mistake, caught while building it and worth naming directly: `progress_callback` must
be an `async def`, matching `ProgressFnT`. A plain `def` version still gets *called*
correctly (the prints still fire), but the dispatcher `await`s its return value —
internally wrapped in a shield (`_shielded_progress`) that catches and logs rather than
crashing the whole call — so a synchronous callback produces a log line reading
`"progress callback raised" ... TypeError: object NoneType can't be used in 'await'
expression"` once per event, while looking, from the printed output alone, like it worked
perfectly. It did work — the logged failure is the *await*, not the call — but a mistake
that fails silently while continuing to appear to succeed is exactly the kind of thing
worth having actually triggered once, rather than only being told about.

### A distinction the SDK does not paper over

`client.list_resources()` on the assembled server returns exactly one resource: `menu`.
`cafe://drinks/{slug}` (topic 04's resource *template*) is invisible to that call and
only appears under `client.list_resource_templates()` — the SDK client does not merge the
two the way a more "helpful" client might. This is the same `resources/list` vs
`resources/templates/list` split topic 04 introduced at the wire level, reconfirmed here:
convenience did not erase a real distinction the protocol makes on purpose.

### Three ways to connect, one object

`Client(...)`'s first argument accepts an `MCPServer` object directly (the in-memory
transport `tests/test_cafe_project.py` uses — no socket, the fastest option, ideal for
tests), a URL string (real HTTP, what `solved/sdk_client.py` uses against a running
`cafe_project.py`), or `StdioServerParameters` (a subprocess talking over stdin/stdout,
the shape most desktop MCP clients actually use to launch a local server). The raw client
never had this choice to make — `tests/wire.py`'s `wire_client()` is permanently wired to
`httpx.ASGITransport`, one specific in-process shortcut, because that file's entire job is
testing one server's own process, not connecting to arbitrary ones.

## Layer 3 — Dry-run: place_order, side by side

Raw client, `place_order`, both rounds, in full:

```
ROUND 1 (id=4)
  build params: {"name": "place_order", "arguments": {"order": "<token>"}}
  build _meta by hand: {protocolVersion, clientInfo, clientCapabilities}
  build headers by hand: Mcp-Method: tools/call, Mcp-Name: place_order
  POST -> result.resultType == "input_required"
  READ BY HAND: result.inputRequests.confirm.params.message
  READ BY HAND: result.requestState  (a long opaque signed string)

ROUND 2 (id=5) -- a FRESH request, built by hand from round 1's own reply
  build params: {
    "name": "place_order",
    "arguments": {"order": "<token>"},        <- must be byte-identical to round 1
    "inputResponses": {"confirm": {"action": "accept",
                                    "content": {"name": "Sanjoy", "confirm": true}}},
    "requestState": "<the string read out of round 1>"
  }
  POST -> result.resultType == "complete", result.structuredContent.result.ticket
```

SDK client, same operation, in full:

```python
placed = await client.call_tool("place_order", {"order": token})
result = placed.structured_content["result"]
```

One awaited call. `elicitation_callback` (supplied once, at `Client(...)` construction,
not per-call) is invoked internally exactly where round 1's `input_required` would have
surfaced; everything between that invocation and the final result — reading
`requestState`, re-sending the unchanged argument, shaping `inputResponses` — happens
inside the SDK, never inside your code.

## Gotchas

`Client.call_tool`'s automatic MRTR driving has a ceiling: `input_required_max_rounds`
(default 10). A tool that kept returning `input_required` forever would eventually raise
`InputRequiredRoundsExceededError` rather than loop forever — not exercised directly here
(nothing in this café asks more than once), but worth knowing the automation is bounded,
not infinite.

The elicitation callback runs for *every* `input_required` result across the whole
`Client` instance, not just `place_order` — if this café had a second tool that also used
MRTR, the same callback would need to handle both, distinguishing them by
`params.message` or `params.requested_schema`, the same way a real host application
routing elicitation to an actual human would need a general-purpose form renderer, not one
hand-written prompt per tool.

`cafe_project.py`'s tools carry no `annotations` at all — `mcp.tool()(some_function)`
with no arguments does not carry over the `ToolAnnotations` (`read_only_hint`,
`destructive_hint`, etc.) each topic's *own* `@mcp.tool(annotations=...)` call set. That
metadata belongs to the original decorator call, not to the function object, and
re-declaring it nine times here would repeat what topics 03-13 already show in full for
no new teaching value — a real production assembly would want to carry it forward.

## Your turn

There is no `solutions/` stub for this topic. `cafe_project.py`, `raw_client.py`, and
`sdk_client.py` are, like `solved/loadbalancer.py` and `solved/agent_client.py` before
them, meant to be *read* rather than filled in — the value here is entirely in the
side-by-side comparison, not in writing new tool logic. Read both client scripts next to
each other, run both against a running `cafe_project.py`, and then try swapping
`solved/sdk_client.py`'s `elicitation_callback` for one that inspects `params.message` and
answers differently depending on the total — the same branch a real host application
would need to route a form to an actual human instead of auto-confirming it.

## Connection forward

There is no topic 16. Fifteen topics, in order, each answered exactly one question the
previous one raised: what a stateless request looks like, how a tool becomes something a
model can call, what a resource is that a tool is not, where state lives once sessions are
gone, what happens when a server needs to ask a question mid-call, what a stream
genuinely costs, where statelessness actually breaks, and — last — what a client library
is doing on your behalf once you finally stop building one by hand. `notes/appendix-sdk-vs-spec.md`
holds every place along the way where the installed SDK and the written specification
disagreed; everything else in this folder was checked directly against a running server,
not assumed from either one.
