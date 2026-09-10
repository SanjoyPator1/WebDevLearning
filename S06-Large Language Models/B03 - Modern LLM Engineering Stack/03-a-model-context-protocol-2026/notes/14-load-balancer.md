# Three Instances Behind a Round-Robin Proxy

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [The proxy is deliberately dumb](#the-proxy-is-deliberately-dumb)
  - [What needed zero changes: the order token](#what-needed-zero-changes-the-order-token)
  - [What needed one line: the shared subscription bus](#what-needed-one-line-the-shared-subscription-bus)
  - [The trade-off: polling instead of pushing](#the-trade-off-polling-instead-of-pushing)
  - [A nuance the fix introduces: the backlog](#a-nuance-the-fix-introduces-the-backlog)
  - [Running it](#running-it)
- [Layer 3 — Dry-run: one cart, three replicas](#layer-3-dry-run-one-cart-three-replicas)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)

## One sentence

Nothing about the wire changes when you run three copies of a stateless MCP server behind
a load balancer instead of one — except the one place where state genuinely lived inside a
single process, which needs exactly one line of code to stop mattering.

## Where this sits

Thirteen topics built one server at a time and tested each one alone. This topic is the
payoff for that discipline: it takes topic 07's order token, topic 11's `sell_out`, and
runs them against **three separate operating-system processes** at once, with a real
round-robin proxy deciding which one answers each request. Nothing here introduces a new
JSON-RPC method or a new piece of the wire format — every RPC in this chapter was already
covered. What is new is the *deployment shape*, and what that shape reveals about which of
the last thirteen topics were actually solving the problem they claimed to solve.

## The problem this topic solves

A real service does not run as one process. It runs as several, so that one crashing, one
being redeployed, or one simply being too busy does not take the whole thing down — and so
that traffic can be split across more than one CPU. The moment you do that, a load
balancer sits in front, and it makes a promise almost no client can rely on: **it will not
send the same client to the same instance twice in a row.** A round-robin proxy, the
simplest kind, guarantees the *opposite* — consecutive requests almost never land on the
same replica.

Every topic in Part 3 ("state without sessions") was built around exactly this
possibility, on paper, without ever actually running more than one process to check. This
topic runs the check. Two outcomes are possible: either that story was true, and running
three instances changes nothing observable, or it was wishful thinking, and something
breaks the moment a real second process gets involved. Topic 11 already showed one thing
breaks. This topic is where you watch it break for real, and then fix it.

## Layer 1 — The intuition

Imagine three identical coffee-shop counters, side by side, sharing one till. A customer
who started an order at counter 1, got called away, and came back to finish paying at
counter 3 is not confused, and neither is the barista at counter 3 — the till (the signed
order token, carried by the customer) has the whole order on it, plain to read and
impossible to fake. Nobody had to walk over and tell counter 3 what happened at counter 1.

Now imagine a *different* kind of request: "tell me the moment you sell out of oat milk."
That is not a note you can hand someone — it is a promise that only the specific person
you asked can keep, because keeping it means staying near you and speaking up later. If
you made that request to the barista at counter 1 and then wandered over to counter 3, the
barista at counter 3 has no idea you ever asked, and the barista at counter 1 has no way to
shout across the room to reach you if you're gone. That is topic 11's leak, and it is the
one piece of this whole café that a load balancer breaks for real — everything else was
already a note on paper.

## Layer 2 — The mechanics

### The proxy is deliberately dumb

`solved/loadbalancer.py` spawns three real Python processes (`solved/t14_load_balancer.py`,
started three times with three different ports and an environment variable naming each
one) and runs a tiny Starlette app in front of them on port 3010 — the same port every
other topic in this folder has used for one server the whole time.

```text
                        client
                          |
                          v
              +---------------------+
              |  proxy   (:3010)    |   round-robin, no state,
              |  solved/loadbalancer|   no idea what MCP is
              +---------------------+
               /          |          \
              v           v           v
      +-----------+ +-----------+ +-----------+
      | replica-1 | | replica-2 | | replica-3 |
      |  (:3011)  | |  (:3012)  | |  (:3013)  |
      +-----------+ +-----------+ +-----------+
              \           |           /
               \          |          /
                v         v         v
          +-----------------------------+
          |  cafe_mcp_shared_bus.db      |  <- SqliteSubscriptionBus
          |  (one file, all three point  |     every replica shares
          |   at the same path)          |
          +-----------------------------+
```

The proxy's whole job is: pick the next backend port in rotation, forward the request
byte-for-byte (headers, body, and — because `subscriptions/listen` is a real streaming
response — the response as a stream too, not buffered), and forward the reply back
unchanged. It does not parse JSON-RPC. It does not know a tool from a resource. A real
load balancer (nginx, an AWS ALB, Envoy) works the same way: it moves bytes, and has no
opinion about what is inside them. That is *why* this topic exists — the interesting
question is never "does the proxy work," it's "does the protocol survive not being able to
rely on the proxy at all."

### What needed zero changes: the order token

`add_to_order` and `view_order` in `solved/t14_load_balancer.py` are topic 07's functions,
character for character. The only new thing in the whole file is a `served_by` field on
the response, added purely so *you* can see which replica answered — the tool code itself
never reads or branches on it.

Proven directly, not argued about: `curl/14_stateless_across_instances.sh` starts three
real replicas, calls `add_to_order` on replica-1, takes the token it gets back, calls
`add_to_order` again (adding a second drink) on replica-2 — a process that has never seen
this cart before — and then calls `view_order` on replica-3, a *third* process, and gets
back the complete, correctly-priced, two-item cart. Three different operating-system
processes, one cart, zero coordination between the processes beyond the token itself.

### What needed one line: the shared subscription bus

`sell_out` and `un_sell_out` are topic 11's functions, also character for character. The
one thing that changes is a single constructor argument:

```python
mcp = MCPServer(
    name="cafe-mcp",
    version="0.14.0",
    ...,
    subscriptions=SqliteSubscriptionBus(BUS_PATH),   # <-- this line
)
```

Every earlier server in this folder left `subscriptions` at its default, which is
`InMemorySubscriptionBus` — a bus that is nothing more than a Python dict living inside
one process's memory. `SqliteSubscriptionBus` (`solved/cafe_mcp/shared_bus.py`) implements
the exact same `SubscriptionBus` protocol (a `publish` method and a `subscribe` method,
nothing more), but backs it with a SQLite file on disk that every replica opens. `publish`
inserts one row. Each replica separately polls for rows newer than the last one it saw
(every 0.2 seconds) and, for every new row, calls its own in-process listener callbacks —
the exact same callbacks `InMemorySubscriptionBus` would have called, just fed by a poll
loop instead of a same-process dict lookup.

`sell_out`'s own code does not know or care which bus it is talking to. It still just
calls `await ctx.notify_resource_updated("cafe://menu")`. That is the entire point of the
`SubscriptionBus` being a small `Protocol` rather than a concrete class baked into the SDK:
swapping the implementation underneath a tool changes nothing the tool has to say about
it.

### The trade-off: polling instead of pushing

A poll loop is not free, and it is worth being honest about the cost rather than hiding
it. Measured directly (a publish on one process, a listener on another, timestamped on
both ends): the event arrives roughly **107 milliseconds** after `sell_out` returns,
consistent with the bus's 0.2-second poll interval (an event published right after a poll
just missed will wait almost the whole interval; one published right before a poll lands
almost immediately — the number above is roughly the middle of that range, averaged over
several runs). A real production system would replace this file with something that pushes
instead of polls — Redis's `PUBLISH`/`SUBSCRIBE`, or a message broker like NATS — and the
`SubscriptionBus` protocol is exactly the seam that would let you do that without touching
`sell_out` a second time. This file is a stand-in that is honest about being one: it proves
the *shape* of the fix (a shared bus behind a small protocol) without requiring you to
stand up Redis to see it work.

### A nuance the fix introduces: the backlog

Running `curl/14_subscription_fixed.sh` twice in a row surfaces something worth noticing
rather than treating as a bug. `SqliteSubscriptionBus` remembers, per bus *object*, the
highest row id it had seen **when that object was constructed** — not when a listener
first subscribes. If an event gets published to the file before any listener has ever
connected on that replica, and then a listener connects for the first time, the poll loop
delivers that old event as soon as it starts running, alongside anything genuinely new.

`InMemorySubscriptionBus` cannot do this — with nothing but a same-process dict of live
callbacks, an event published while nobody is subscribed has nowhere to go and is simply
gone. The shared bus's backlog is a direct consequence of the exact thing that makes it
work across processes at all: the "message" is a durable row in a shared file, not a
direct call to a callback, so it has to sit somewhere between being written and being
read. Whether a backlog like this is desirable depends entirely on what the resource
means — for a menu, seeing one stale "sold out" notification a fraction of a second late
is harmless; for something where an old notification would be actively misleading, a real
deployment would need to either track poll position per-listener (not per-bus-object, the
way this teaching version does) or accept the small window and design around it.

### Running it

```text
$ python solved/loadbalancer.py
--------------------------------------------------------------------
TOPIC 14 — three replicas behind a round-robin proxy
--------------------------------------------------------------------
  bus path : /tmp/cafe_mcp_shared_bus.db  (all three replicas share this file)
  replicas : [3011, 3012, 3013]
  proxy    : http://127.0.0.1:3010/mcp
--------------------------------------------------------------------
  all three replicas are up.
```

Leave that running, and in a second terminal, `curl/14_stateless_across_instances.sh` and
`curl/14_subscription_fixed.sh` each spin up their *own* pair or trio of replicas on
different ports (so they do not fight with `loadbalancer.py` over the same ports) and walk
through the two proofs directly, printing exactly which process answered each call.

## Layer 3 — Dry-run: one cart, three replicas

Walking `curl/14_stateless_across_instances.sh`'s exact numbers, by hand:

```
Call 1 -- add_to_order(latte, M, qty=1) on replica-1 (port 3011)
    replica-1 has never seen this cart. cart_lines = []
    appends {slug: latte, size: M, qty: 1}
    prices it: Latte/M = $3.10 (made up for this example)
    signs a token containing exactly that one line
    returns: served_by="replica-1", total=$3.10, order="v1.<payload1>.<sig1>"

Call 2 -- add_to_order(espresso, S, qty=2, order="v1.<payload1>.<sig1>") on replica-2 (port 3012)
    replica-2 has NEVER seen this cart before this call.
    it decodes the token -- no lookup, no request to replica-1, nothing --
    and gets back exactly the one line replica-1 put there: [latte, M, qty 1]
    appends {slug: espresso, size: S, qty: 2}
    prices both lines: Latte/M $3.10 + Espresso/S (2x) $2.20 x 2 = $4.40 -> total $7.50
    signs a NEW token containing BOTH lines
    returns: served_by="replica-2", total=$7.50, order="v1.<payload2>.<sig2>"

Call 3 -- view_order(order="v1.<payload2>.<sig2>") on replica-3 (port 3013)
    replica-3 has never seen either of the first two calls.
    decodes the token: two lines, latte and espresso, exactly as replica-2 left them
    reprices them against TODAY's menu (same prices, so nothing changes)
    returns: served_by="replica-3", total=$7.50, lines=2
```

Three processes, three different answers to "who served this," one consistent cart. The
signature on each token is the only thing that ever crossed a process boundary, and it
carried the entire cart with it.

Now the subscription half, from `curl/14_subscription_fixed.sh`, with instance-A and
instance-B sharing one `SqliteSubscriptionBus` file:

```
t=0.0s  instance-A: client opens subscriptions/listen for cafe://menu
                    instance-A's bus registers a listener callback, starts its
                    own 0.2s poll loop reading the SHARED file
                    instance-A sends the ack immediately (no poll needed for this part)

t=1.5s  instance-B: client calls sell_out("latte")
                    instance-B adds "latte" to ITS OWN SOLD_OUT set (module-level,
                    still per-process -- this never changed)
                    instance-B calls ctx.notify_resource_updated("cafe://menu")
                    instance-B's bus INSERTS one row into the shared sqlite file
                    instance-B returns "Latte is now marked sold out." to its caller

t=~1.5s-1.7s  instance-A's poll loop (running the whole time, independently)
                    wakes up, sees a new row it has not seen before,
                    decodes it back into a ResourceUpdated("cafe://menu") event,
                    calls instance-A's own listener callback with it
                    instance-A's stream emits notifications/resources/updated
```

The two processes never called each other directly. Both only ever talked to the same
file.

## Gotchas

Three real OS processes, not three async tasks, are the whole point of this topic — if the
three replicas were instead three `MCPServer` objects running as coroutines inside one
Python process, `SOLD_OUT` (still a plain module-level `set`, unchanged from topic 11)
would be shared by accident, because Python globals are per-*process*, not per-object, and
the leak this topic exists to demonstrate would quietly disappear without actually being
fixed. Every server in this folder that claims to prove something about multiple instances
(`curl/11_cross_instance_leak.sh`, both new `curl/14_*.sh` scripts, and
`tests/test_wire_load_balancer.py`'s streaming test) does it with `subprocess.Popen` or a
real `uvicorn.Server` on a real port — never a coroutine standing in for a process.

A round-robin proxy makes *no* promise about which replica gets any particular request.
Nothing in this chapter relies on a specific replica answering a specific call — the tests
and curl scripts call specific ports directly precisely so the proof is unambiguous
("replica-2 truly never saw this cart before"), not because the proxy could be told to
route that way.

`SOLD_OUT` itself is still exactly the same per-process `set[str]` topic 11 used. This
topic fixes the *notification* (the bus), not the *underlying fact* (which drinks are sold
out). A real deployment would need that fact itself to live somewhere shared too — a
database row, not a Python set — or two replicas could disagree about whether a drink is
actually sold out even after the notification problem is solved. This chapter deliberately
leaves that half unfixed, because fixing it teaches nothing new: it is exactly topic 07's
lesson (put the state in something every replica can read) applied to a second variable.

## Your turn

`solutions/t14_load_balancer.py` has six TODOs. The first five ask you to assemble a
server out of pieces you already wrote in topics 07 and 11 — the value of this topic is
in noticing how little there is to actually change, not in writing new logic. The sixth is
a no-code prediction exercise: guess what happens to an open `subscriptions/listen`
connection when a proxy sends the *next* call to a different replica, then run
`solved/loadbalancer.py` and check.

## Connection forward

Topic 15 assembles everything this folder has built — every topic's server, together, one
project — and looks at the same café from the other side: a raw hand-written client
(everything `tests/wire.py` has been doing since topic 01) next to the official SDK
client, to see plainly what the SDK is buying you and what it was quietly hiding the whole
time.
