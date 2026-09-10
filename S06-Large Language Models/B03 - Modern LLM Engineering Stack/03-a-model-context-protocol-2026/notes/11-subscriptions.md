# `subscriptions/listen`: Where Statelessness Leaks

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [Opening a stream](#opening-a-stream)
  - [The ack: honoring is a truthy echo, not a capability check](#the-ack-honoring-is-a-truthy-echo-not-a-capability-check)
  - [Publishing: one line, on the server that received the call](#publishing-one-line-on-the-server-that-received-the-call)
  - [Fan-out: several listeners, one instance, one event](#fan-out-several-listeners-one-instance-one-event)
  - [The bus is a `Protocol`, and the default is `InMemorySubscriptionBus`](#the-bus-is-a-protocol-and-the-default-is-inmemorysubscriptionbus)
  - [The central proof: the same event, a different instance, silence](#the-central-proof-the-same-event-a-different-instance-silence)
  - [Why a bigger token cannot fix this](#why-a-bigger-token-cannot-fix-this)
  - [No resumability here either](#no-resumability-here-either)
  - [A testing wrinkle worth knowing about](#a-testing-wrinkle-worth-knowing-about)
- [Layer 3 — Dry-run: one sell-out, two listeners, one leak](#layer-3-dry-run-one-sell-out-two-listeners-one-leak)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)

## One sentence

`subscriptions/listen` is a single request whose response never really finishes — it
streams a notification every time something the client asked about changes — and because
that stream lives entirely inside one server process's memory, it is the one place in the
whole 2026-07-28 protocol where running more than one instance of your server genuinely
breaks something.

## Where this sits

Every RPC since topic 01 has had the same shape: the client asks, the server answers, the
connection can close a microsecond later, and nothing is lost by the answer coming from a
completely different process next time. `subscriptions/listen` is the last of the ten
2026-07-28 methods, and it is the one exception to all of that. Topic 10's progress
notifications rode a stream too, but that stream belonged to *one call* and ended when
the call did. This one has no call to end — a client opens it once and expects to keep
hearing from it for as long as it cares to listen, which could be the length of an entire
conversation.

## The problem this topic solves

The café's menu can change — a drink sells out. A client watching the counter wants to
know the moment that happens, not by asking `resources/read` over and over and comparing
answers (that is what everyone did before this method existed, and it is wasteful and
laggy in equal measure). It wants to be *told*.

Being told requires something every other topic in this folder has spent nine topics
proving is *not required*: a live channel that stays open, held by one specific process,
for as long as the client cares. That is a real, unavoidable piece of state, and this
topic is about looking directly at what it costs.

## Layer 1 — The intuition

Every earlier topic's answer to "how do I know something without asking every time?" was
a receipt in your pocket — a token, checkable by anyone at the register, no matter who is
standing behind the counter that day. A live subscription is not a receipt. It is closer
to standing at one specific counter with your hand raised, having told *that cashier*
"tell me if the espresso runs out." Walk away and come back to a different till, and the
new cashier has never heard your request — your raised hand meant something to one
person, not to the whole shop.

## Layer 2 — The mechanics

### Opening a stream

```bash
curl -N http://127.0.0.1:3010/mcp \
  -H 'MCP-Protocol-Version: 2026-07-28' -H 'Mcp-Method: subscriptions/listen' \
  -d '{"jsonrpc":"2.0","id":1100,"method":"subscriptions/listen",
       "params":{"notifications":{"resourceSubscriptions":["cafe://menu"]}, "_meta":{...}}}'
```

`params.notifications` is a filter with up to four fields: `toolsListChanged`,
`promptsListChanged`, `resourcesListChanged` (all booleans), and `resourceSubscriptions`
(a list of specific URIs). You ask for exactly the change categories you care about.

### The ack: honoring is a truthy echo, not a capability check

The first frame back is always an acknowledgement, never an event:

```json
{"jsonrpc":"2.0","method":"notifications/subscriptions/acknowledged",
 "params":{"_meta":{"io.modelcontextprotocol/subscriptionId":1100},
           "notifications":{"resourceSubscriptions":["cafe://menu"]}}}
```

It is worth being precise about what "honored" means here, because it reads like the
server might be telling you which of your requested filters it actually *supports*. It is
not. Verified on the wire, requesting a real URI, a made-up one, and a `false` flag
together:

```json
"notifications": {"toolsListChanged": true,
                   "promptsListChanged": false,
                   "resourceSubscriptions": ["cafe://menu", "cafe://this-resource-does-not-exist"]}
```

comes back as:

```json
"notifications": {"toolsListChanged": true,
                   "resourceSubscriptions": ["cafe://menu", "cafe://this-resource-does-not-exist"]}
```

`promptsListChanged: false` was simply dropped — falsy flags never appear in the ack at
all, rather than being echoed back as `false`. And the nonexistent URI was echoed back
**exactly like the real one**. The SDK's own source states the reasoning directly:
"whether an event kind ever fires depends on what the server publishes, exactly as a
subscription to a nonexistent resource URI is honored and never fires." Honoring a filter
means *the server will tell you if this happens* — it says nothing about whether "this"
is even possible. A subscription to a URI that will never change is a completely valid,
fully "honored" subscription that simply produces silence forever, and that is not a bug
to detect.

### Publishing: one line, on the server that received the call

```python
async def sell_out(slug: str, ctx: Context) -> str:
    SOLD_OUT.add(slug)
    await ctx.notify_resource_updated("cafe://menu")
    return f"{menu.find(slug).name} is now marked sold out."
```

That single `await` is the entire publish side of this topic. It hands a `ResourceUpdated`
event to whatever `SubscriptionBus` this `MCPServer` instance holds, and the bus fans it
out to every listener currently subscribed *on that same instance*. Verified end to end:
open a listen stream, call `sell_out` on the same process, and the stream receives

```json
{"jsonrpc":"2.0","method":"notifications/resources/updated",
 "params":{"_meta":{"io.modelcontextprotocol/subscriptionId":1100},"uri":"cafe://menu"}}
```

tagged with the *listen request's own id*, not the tool call's — that tag is how a client
juggling several open subscriptions tells which one a given event belongs to.

### Fan-out: several listeners, one instance, one event

```bash
bash curl/11_two_listeners.sh
```

opens two independent listen streams against one running server, then calls `sell_out`
once. Both streams receive the event, each stamped with **its own** `subscriptionId` —
1110 for one, 1111 for the other — never the other stream's id and never the tool call's
id. One publish, delivered independently to every open stream on that process. This is the
part of the mechanism that works exactly the way you would hope: any number of clients can
watch the same server and all hear the same news.

### The bus is a `Protocol`, and the default is `InMemorySubscriptionBus`

```python
class SubscriptionBus(Protocol):
    async def publish(self, event: ServerEvent) -> None: ...
    def subscribe(self, listener) -> Callable[[], None]: ...
```

`MCPServer` constructs an `InMemorySubscriptionBus()` for you automatically if you pass
nothing — which is exactly why the previous section's demo needed zero configuration to
work. Read what "in-memory" means literally: a plain Python dict of listener callables,
living in this one process's heap, gone the instant the process exits, invisible to any
other process that happens to be running the exact same code on the exact same machine.

### The central proof: the same event, a different instance, silence

```bash
bash curl/11_cross_instance_leak.sh
```

starts **two real, separate copies** of this server — instance A on port 3010, instance B
on port 3011, each with its own `InMemorySubscriptionBus` because each is its own Python
process with its own memory. Open a listen stream on A. Call `sell_out` on B. Verified:

```text
>>> Opening a listen stream on instance A (port 3010)...
>>> Calling sell_out on instance B (port 3011) — a DIFFERENT process...
  instance-B says: Latte is now marked sold out.
  [listening on instance-A] event: message
  [listening on instance-A] data: {"jsonrpc":"2.0","method":"notifications/subscriptions/acknowledged", ...}
```

That is the entire output from instance A's listener. The ack, and then four full seconds
of nothing, while a real, successful `sell_out` ran on the other instance. Grep both
servers' own logs and the asymmetry is exact:

```text
grep '\[server' /tmp/cafe_instance_A.log   ->  nothing
grep '\[server' /tmp/cafe_instance_B.log   ->  "sell_out('latte') -- notifying subscribers"
```

Instance B genuinely did the work. Instance A genuinely never heard about it, for the
entire time its connection was open.

### Why a bigger token cannot fix this

Every earlier topic's answer to "how does one instance know what another instance did?"
was: it doesn't need to, because the *client* carries a signed token proving what
happened. That pattern cannot be stretched to cover this problem, and it is worth being
precise about why, because the instinct to reach for it here is natural given the last
nine topics.

A token is a piece of *data*, handed to the client once, checkable by any instance later,
on demand, when the client chooses to present it. A subscription is not data — it is a
**live, open, held-open socket connection** to one specific process, established the
moment the listen request arrived and lasting exactly as long as that TCP connection
survives. There is no way to sign "please push me events" the way you sign "this cart
contains two lattes," because a signature is a *fact you can check later*, and what is
missing here is not a fact — it is delivery. Instance A has no socket to instance B's
listener to push through, no matter what any token says. Fixing this needs the actual fix:
a bus that is not in one process's memory, shared across every replica — which is exactly
what topic 14 does, replacing `InMemorySubscriptionBus` with a Redis- or NATS-backed one
implementing the identical `SubscriptionBus` Protocol, with zero changes anywhere in this
file. The `Protocol` seam is *why* that swap costs nothing: `sell_out`'s
`ctx.notify_resource_updated(...)` call does not know or care what kind of bus is behind
it.

### No resumability here either

Consistent with topic 10: a `subscriptions/listen` stream that gets dropped is simply
gone. There is no id to resume from, no backlog delivered on reconnect. A client that
loses its connection for thirty seconds and reopens a fresh listen stream has genuinely
missed anything that happened in that gap — which is the practical reason `cafe://menu`
still carries a short cache-hint TTL in this topic's server even though it is
subscribable: the TTL is the client's fallback for exactly the window a dropped
subscription cannot see across.

### A testing wrinkle worth knowing about

Every earlier topic's automated tests drove the server through `httpx.ASGITransport` — an
in-process fake that calls the ASGI app directly, with no real socket. That stopped
working here, and it is worth understanding why rather than just working around it
silently. `ASGITransport` waits for the ASGI application callable to *return* before
handing anything back to the caller. Every prior RPC's handler returns almost immediately.
`subscriptions/listen`'s handler does not return until the stream ends — which, for an
open subscription, is never, until the client disconnects. The two expectations are
incompatible: verified directly, a listen request sent over `ASGITransport` hangs
indefinitely, timing out with **not even the acknowledgement** delivered.

`tests/test_wire_subscriptions.py` runs a real `uvicorn.Server` as a background asyncio
task, bound to an actual TCP port, and talks to it with a genuine `httpx.AsyncClient` —
the same shape of test as every other file, just with a real socket underneath instead of
a shortcut. It is measurably slower (this file alone takes several seconds; the rest of
the suite together takes about one) and that cost is honest: it is the price of testing
something that is actually, unavoidably, about time and open connections rather than
instantaneous request/response.

## Layer 3 — Dry-run: one sell-out, two listeners, one leak

**T+0.0s.** Client X opens `subscriptions/listen` against instance A, filtering on
`cafe://menu`. Instance A's `ListenHandler` subscribes a callback to instance A's
`InMemorySubscriptionBus`, then sends the ack: `subscriptionId: 1100`.

**T+0.3s.** Client Y opens the identical listen request against instance A. A second
callback subscribes to the *same* bus. Ack: `subscriptionId: 1101`.

**T+1.0s.** A member of staff calls `sell_out("espresso")` — against instance A.

```text
instance A's bus.publish(ResourceUpdated(uri="cafe://menu"))
  -> callback for subscriptionId 1100 fires -> client X receives the event
  -> callback for subscriptionId 1101 fires -> client Y receives the event
```

Both clients see it, correctly tagged, independently.

**T+1.5s.** A *different* staff member, hitting instance B by chance (perhaps a load
balancer picked it), calls `sell_out("latte")`.

```text
instance B's bus.publish(ResourceUpdated(uri="cafe://menu"))
  -> instance B's bus has NO listeners at all (neither X nor Y ever connected to B)
  -> nothing happens, anywhere
```

Client X and client Y are both still connected to instance A, both still believe they are
subscribed to `cafe://menu`, and neither ever learns that lattes sold out. Their own
future `resources/read` calls will eventually show it — if that read happens to land on
instance B, or once instance A's data somehow converges with B's (it will not, on its
own, ever) — but the *notification* they were promised never arrives, silently, with no
error anywhere to say so.

## Gotchas

**"Honored" is not "verified real."** A subscription to a URI that will never exist is
honored exactly like a real one. Silence is the only feedback you get either way.

**Falsy filter flags are dropped from the ack, not echoed as `false`.** Check for the
key's *presence*, not its truth value, if your client needs to distinguish "not honored"
from "honored as false."

**The default bus is in-memory and per-process, with zero configuration required.** That
is precisely what makes the leak invisible in local development — a single instance never
shows a single symptom of it.

**A token cannot fix this.** The missing piece is a live socket to push through, not a
fact to check later. Different problem, different fix.

**A dropped listen stream has no replay**, same as topic 10's progress streams. A cache
hint on the underlying resource is the honest fallback for whatever window a reconnect
cannot see across.

**`httpx.ASGITransport` cannot test this RPC at all.** It buffers the whole response
before returning any of it, and this response never naturally ends. Use a real server —
`uvicorn.Server` as a background task is enough; a subprocess is not required.

## Your turn

`solutions/t11_subscriptions.py`, five TODOs. TODO 5 is not code — it is a prediction,
made *before* running `curl/11_cross_instance_leak.sh`, and the value of this topic lives
entirely in whether that prediction was right and whether you can say, out loud, why no
amount of signing could have made it come out differently.

## Connection forward

Every one of the ten client methods of 2026-07-28 has now been exercised somewhere in this
folder. The remaining topics stop being about *new protocol surface* and start being about
*operating* what you have already built: how a version gets negotiated with no handshake
to negotiate in, how a gateway routes on a header without touching JSON, and — the payoff
that finally puts a real load balancer in front of three copies of this server and proves,
for real, that nine of the ten RPCs do not care which instance answers while this tenth
one visibly does.

Does this make sense? Want me to go deeper on any part — why the bus is shaped as a
`Protocol` rather than a concrete class, the exact reasoning behind dropping falsy filter
flags, or what a Redis-backed bus implementation would actually look like?
