# 05 — HTTP/1.1, HTTP/2, HTTP/3

## Why this matters

HTTP is the protocol your API speaks. FastAPI hides most of it, but the semantics — methods, status
codes, headers, idempotency — *are* your API's contract (topic 03 goes deep on design; this file is
the protocol itself). And knowing the differences between HTTP versions explains real performance
behaviour you'll see in production.

---

## HTTP/1.1 — the workhorse

Despite HTTP/2 and /3 existing, HTTP/1.1 is still everywhere and is the clearest to learn because
it's **human-readable text**.

### Anatomy of a request and response

A request on the wire:
```
GET /todos?status=done HTTP/1.1      ← start line: method, path+query, version
Host: api.example.com                ← headers (key: value), one per line
Authorization: Bearer eyJhb...
Accept: application/json
                                     ← blank line separates headers from body
(body, if any — e.g. JSON for POST/PUT)
```

A response:
```
HTTP/1.1 200 OK                      ← status line: version, code, reason
Content-Type: application/json       ← headers
Content-Length: 42
                                     ← blank line
{"todos": [...]}                     ← body
```

That's it — HTTP/1.1 is genuinely this simple. You can type it by hand into a raw TCP connection.

### Methods and their semantics

Methods aren't arbitrary — they carry **semantic promises**. Two properties matter enormously:

- **Safe** = read-only, no side effects. `GET`, `HEAD`. A crawler can hit these freely.
- **Idempotent** = doing it N times has the same effect as doing it once.

| Method | Safe? | Idempotent? | Use |
|---|---|---|---|
| `GET` | ✅ | ✅ | Read a resource |
| `HEAD` | ✅ | ✅ | Like GET but headers only |
| `PUT` | ❌ | ✅ | Replace a resource entirely |
| `DELETE` | ❌ | ✅ | Remove a resource |
| `POST` | ❌ | ❌ | Create / arbitrary action |
| `PATCH` | ❌ | ❌* | Partial update |

**Why PUT is idempotent but POST isn't** — the classic question:
- `PUT /todos/42` with a full body sets todo 42 to that exact state. Do it 5 times → todo 42 is in
  that state. Same result. Idempotent.
- `POST /todos` creates a *new* todo each time. Do it 5 times → **five todos**. Not idempotent.

This matters because networks are unreliable (file 02): if a request times out, can the client safely
**retry**? For idempotent methods, yes. For `POST`, a blind retry might create duplicates — which is
exactly why **idempotency keys** exist (topic 03). File this away; it's a recurring theme.

### Status codes you must know cold

Grouped by first digit — the digit tells you the category:

- **2xx success:** `200 OK`, `201 Created` (+ a `Location` header pointing to the new resource), `204 No Content` (success, nothing to return — e.g. after DELETE).
- **3xx redirect:** `301` (moved permanently), `302`/`307` (temporary), `304 Not Modified` (your cached copy is still good — topic 06 caching), `308` (permanent, keep the method).
- **4xx client error (you sent something wrong):** `400` (malformed), `401` (not authenticated), `403` (authenticated but not allowed), `404` (not found), `409` (conflict), `422` (validation failed — FastAPI's default for bad body), `429` (rate limited — topic 19).
- **5xx server error (the server broke):** `500` (unhandled exception), `502` (bad gateway — the proxy got junk from upstream), `503` (unavailable — overloaded/down), `504` (gateway timeout — upstream too slow).

**The 4xx/5xx line is a blame line:** 4xx = "you (client) messed up," 5xx = "I (server) messed up."
`502`/`504` specifically come from a proxy/load balancer failing to get a good/timely response from
your backend — you'll cause and observe these in file 06's timeout lab.

### Redirects and the method-change trap

- `301`/`302` historically let clients change the method (a `POST` could become a `GET` on redirect) — surprising and a source of bugs.
- `307`/`308` were introduced to **preserve the method and body** across the redirect. Use these when you mean "same request, new location."
- A `POST` body does **not** always survive a redirect — know this before relying on it.

### Headers worth knowing

`Host` (which virtual host — pairs with SNI from file 04), `Content-Type` (what the body is),
`Content-Length` vs `Transfer-Encoding: chunked` (known size vs streamed), `Authorization` (topic 07),
`Accept` (what the client wants back), `Connection` (keep-alive control), `Cache-Control` (topic 06).

### Cookies (a first look — topic 07 goes deep)

`Set-Cookie` in a response stores state in the browser, sent back on subsequent requests. The
security attributes matter: `HttpOnly` (JS can't read it — blocks XSS theft), `Secure` (HTTPS only),
`SameSite` (CSRF protection). You'll use these properly in auth (topic 07).

### HTTP/1.1's limitation: head-of-line blocking

A single HTTP/1.1 connection handles **one request at a time** — the response must come back before
the next request goes out. This is request-level **head-of-line blocking** (recall the term from file
02). Browsers hacked around it by opening **~6 parallel connections** per origin. But 6 isn't many,
and each has its own handshake cost. This is the problem HTTP/2 was built to solve.

---

## HTTP/2 — multiplexing over one connection

HTTP/2 keeps the same *semantics* (same methods, status codes, headers — your API doesn't change) but
changes how bytes move on the wire:

- **Binary framing:** messages are binary frames, not text. Efficient to parse.
- **Multiplexing:** many requests and responses share **one** TCP connection, interleaved as
  independent **streams**. No more 6-connection hack; no more request-level HOL blocking. This is the
  headline feature.
- **HPACK header compression:** headers repeat a lot (same `Host`, cookies, user-agent every request);
  HPACK compresses them, a real saving when you make many requests.
- **Server push:** the server could proactively send resources the client would ask for next. It
  existed, was hard to use well, and has largely been **removed/deprecated** — know it existed, don't rely on it.

**How it's negotiated:** via **ALPN** during the TLS handshake (file 04). That's why HTTP/2 in
practice requires HTTPS, and why you see ALPN in `curl -v --http2`.

### HTTP/2's remaining flaw

Multiplexing solved HOL blocking *at the HTTP layer* — but all those streams still ride on **one TCP
connection**, and TCP guarantees order. So if a single TCP packet is lost, **TCP-level** HOL blocking
(file 02) stalls *all* the multiplexed streams until the retransmit arrives, even streams whose data
already made it. On a clean network you never notice; on a lossy/mobile network it hurts. Enter HTTP/3.

---

## HTTP/3 & QUIC — fixing TCP's HOL blocking

HTTP/3 runs over **QUIC**, a new transport built on **UDP** (file 02) instead of TCP.

Why rebuild transport on UDP? Because TCP's ordering guarantee is *baked into the OS kernel* and can't
be changed. QUIC implements its own reliability and ordering **per-stream** in user space, so a lost
packet only stalls *its own* stream, not all of them. That's the fix for TCP-level HOL blocking.

QUIC also folds in other wins:
- **TLS 1.3 is built in** (file 04) — the transport and crypto handshakes combine, so connection setup
  is faster (often **0-RTT** on resumption).
- **Connection migration:** a QUIC connection has a connection ID independent of IP, so it survives a
  network change (Wi-Fi → cellular) without re-handshaking — great for mobile.

**Where it matters:** mobile and lossy networks benefit most. Adoption is growing (major CDNs and
browsers support it). For your backend, it's usually terminated at the CDN/load balancer edge (file 07).

---

## Putting the three together

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transport | TCP | TCP | QUIC (UDP) |
| Format | Text | Binary frames | Binary frames |
| Concurrency | 1 req/conn (→ 6 conns) | Multiplexed streams | Multiplexed streams |
| HTTP HOL blocking | Yes | **No** | No |
| TCP HOL blocking | Yes | **Yes** (still TCP) | **No** (per-stream) |
| Setup | TCP + TLS | TCP + TLS (ALPN) | QUIC (TLS 1.3 built in), 0-RTT |

**The semantics never change** across versions — same methods, codes, headers. Only the wire
encoding and transport differ. That's why you can enable HTTP/2 in nginx (planning Lab 5) and your
FastAPI code doesn't change a line.

---

## Check yourself

1. Write out a raw HTTP/1.1 request and response by hand, labelling each part.
2. Explain why PUT is idempotent and POST isn't, and why that matters for retries on an unreliable network.
3. Give the meaning of `201`, `204`, `304`, `401` vs `403`, `409`, `422`, `429`, `502` vs `504`.
4. What's the difference between `301`/`302` and `307`/`308` regarding the method?
5. What problem does HTTP/2 multiplexing solve, and which head-of-line blocking does it *not* fix?
6. How does HTTP/3/QUIC eliminate TCP-level HOL blocking, and why did it need UDP to do it?
7. How is HTTP/2 negotiated, and why does enabling it not require changing your FastAPI code?
