# 02 — TCP & UDP

## Why this matters

TCP is the transport your API runs on. Almost every production networking mystery — connections
piling up, "why is my p99 latency spiky", pools exhausting, servers refusing connections — is
really a TCP behaviour you didn't know about. This file makes TCP concrete.

---

## The problem TCP solves

IP (the layer below) is **unreliable by design**: it sends packets and hopes. Packets can be lost,
duplicated, reordered, or corrupted. TCP is a layer on top that turns this chaos into a **reliable,
ordered byte stream**. When you `await reader.read()`, you get bytes in the exact order they were
sent, with nothing missing — TCP did that work.

TCP provides four guarantees:
1. **Reliability** — lost packets are retransmitted.
2. **Ordering** — bytes arrive in send order (via sequence numbers).
3. **Connection** — a set-up handshake and tear-down, so both sides agree they're talking.
4. **Flow & congestion control** — it won't overwhelm the receiver or the network.

UDP (later in this file) provides *none* of these — and that's sometimes exactly what you want.

---

## The three-way handshake — what "a connection" actually is

Before any data flows, TCP does a three-step greeting. A "connection" is just both sides agreeing on
starting sequence numbers and that they're ready.

```
Client                          Server
  │                                │
  │ ──────── SYN (seq=x) ────────► │   "Let's talk. My sequence starts at x."
  │                                │
  │ ◄──── SYN-ACK (seq=y,ack=x+1) ─│   "OK. Mine starts at y. Got your x."
  │                                │
  │ ──────── ACK (ack=y+1) ──────► │   "Got your y. We're connected."
  │                                │
  │ ═══════ data flows ══════════► │
```

**Why you care:** this handshake is **one full round trip** before *any* useful data moves. If the
server is 100ms away, that's 100ms of pure setup cost, every time you open a new connection. Add
TLS (file 04) and it's more. This is the entire reason **connection reuse** (keep-alive) matters so
much — see below.

---

## Sequence numbers, ACKs, retransmission (the reliability machinery)

- Every byte has a **sequence number**. The receiver sends back **ACKs** ("I've received everything up to byte N").
- If the sender doesn't get an ACK within a timeout, it **retransmits**. This is automatic and invisible to your app — but it's why a lossy network shows up as *latency* (waiting for retransmits) rather than *errors*.
- **Flow control** (the receiver's "window"): the receiver tells the sender "I can only buffer this much right now, slow down." Prevents a fast sender drowning a slow receiver.
- **Congestion control** (slow start): TCP starts cautiously and ramps up, backing off when it detects loss. This is why a fresh connection is *slower* for the first few round trips — another reason to reuse connections.

> You rarely touch these directly, but they explain observed behaviour: "the API is slow but not
> erroring" under packet loss = retransmissions; "new connections are slow, warm ones are fast" = slow start.

---

## Connection lifecycle states you WILL meet

TCP connections move through states. Two show up in real production debugging (`ss -tan` or `netstat` shows them):

### `TIME_WAIT`
After a connection closes, the side that closed **first** holds the connection in `TIME_WAIT` for a
while (typically ~60s) to make sure any straggler packets are handled before the 4-tuple is reused.

**The production symptom:** a server (or client) that opens and closes *many short-lived connections*
accumulates thousands of `TIME_WAIT` entries, which can exhaust ephemeral ports (file 01) and start
refusing new connections. **The fix is almost always: reuse connections** (keep-alive, connection
pools) instead of open-close-open-close. This directly motivates DB connection pools (topic 04) and
HTTP client reuse.

### `CLOSE_WAIT`
The *other* side closed, and your app hasn't finished closing its end. **Lots of `CLOSE_WAIT` = a bug
in your code** — you're not closing connections/sockets you should be (a leaked client, an
unclosed response). If you see these piling up, hunt for the resource you forgot to close.

---

## Keep-alive — the single biggest practical lesson

Given the handshake (+ TLS) cost, opening a new TCP connection per request is wasteful. **Keep-alive**
keeps a connection open and reuses it for many requests.

```
Without keep-alive:  [handshake][req/resp][close]  [handshake][req/resp][close] ...
With keep-alive:     [handshake][req/resp][req/resp][req/resp]...[close]
                                  ↑ every request after the first skips setup
```

This is why:
- HTTP clients (httpx, requests.Session) should be **reused**, not created per request.
- DB drivers use **connection pools** (topic 04) — the handshake to Postgres is paid once, then reused.
- HTTP/1.1 defaults to keep-alive; HTTP/2 takes it further (file 05).

**Lab connection:** Lab 1 in the planning file has you send two `curl` requests with and without
keep-alive and count the handshakes in a packet capture. Do it — seeing two SYNs collapse into one is the "aha".

---

## Head-of-line blocking (at the TCP level)

Because TCP guarantees *order*, if one packet is lost, everything behind it must wait for the
retransmit — even if those later bytes already arrived. This is **head-of-line (HOL) blocking**.

Remember this term. It comes back twice in file 05:
- HTTP/1.1 has HOL blocking at the *request* level.
- HTTP/2 fixes that but still suffers TCP-level HOL blocking under packet loss.
- HTTP/3 (QUIC over UDP) is specifically designed to eliminate it.

---

## UDP — the opposite trade-off

**UDP** is the bare minimum: send a datagram to an IP:port, no handshake, no ordering, no
retransmission, no connection. Fire and forget.

Why would you ever want something so unreliable? Because **reliability costs latency**, and some
workloads prefer speed and can tolerate (or handle themselves) loss:

| Use case | Why UDP |
|---|---|
| **DNS** (file 03) | One tiny request/response — a handshake would double the cost |
| **Video/voice calls** | A dropped frame is better than a late frame; no point retransmitting old audio |
| **Gaming** | Latest position matters; a lost old position is worthless |
| **QUIC / HTTP/3** (file 05) | Builds its *own* reliability on UDP, avoiding TCP's HOL blocking |

> **Mental model:** TCP is a phone call (connection established, ordered conversation, you notice
> dropouts). UDP is postcards (throw them in the mail, no guarantee of arrival or order, but no setup).

---

## Check yourself

1. Draw the three-way handshake and explain why it means new connections have a latency cost.
2. Under packet loss, does TCP typically show up as errors or as latency? Why?
3. What is `TIME_WAIT`, why does it exist, and what's the production problem when it piles up? What's the fix?
4. You see thousands of `CLOSE_WAIT` connections — whose problem is it, and what does it usually indicate?
5. Explain keep-alive and give two places in a backend where connection reuse is critical.
6. Define head-of-line blocking in one sentence (you'll reuse this in file 05).
7. Give two real cases where UDP is the *right* choice, and say what you're giving up.
