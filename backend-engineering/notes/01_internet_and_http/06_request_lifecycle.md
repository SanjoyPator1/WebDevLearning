# 06 — Life of a Request (the synthesis) + Timeouts

## Why this matters

This is where files 01–05 come together. If you can narrate everything that happens between pressing
Enter and getting JSON back — naming each protocol and where latency lives — you've genuinely
understood this topic. And the **timeout taxonomy** at the end is the single most practical debugging
skill in the whole file: most mystery `502`/`504`s are a timeout mismatch, and now you'll be able to find them.

---

## The full journey: `https://api.example.com/todos`

Let's trace one request end to end, tying each step back to the file that explained it.

```
 1. DNS lookup        api.example.com → 93.184.216.34      (file 03)
 2. TCP handshake     SYN / SYN-ACK / ACK                  (file 02)  — 1 round trip
 3. TLS handshake     agree cipher, verify cert, key exch  (file 04)  — 1 round trip (TLS 1.3)
 4. CDN / edge        maybe served from cache here         (file 07, topic 06)
 5. Load balancer     picks a backend instance             (file 07)
 6. Reverse proxy     nginx: routing, TLS termination      (file 07)
 7. uvicorn (ASGI)    hands the request to your app        (topic 02)
 8. Middleware        auth, logging, CORS                  (topic 07/05)
 9. Route handler     your code runs                       (FastAPI)
10. Database          query Postgres                       (topic 04)
11. Response          JSON travels the reverse path back
```

### Narrating it in words (practise this out loud)

> "I resolve `api.example.com` to an IP via DNS — stub resolver, then a recursive resolver walking
> root → .com → authoritative, cached along the way. I open a TCP connection (one round trip for the
> handshake), then negotiate TLS on top (another round trip, verifying the server's certificate against
> a CA I trust, and via ALPN we agree to speak HTTP/2). The request may be answered by a CDN at the
> edge; if not, it reaches a load balancer that picks one healthy backend, behind which a reverse proxy
> terminates TLS and forwards plain HTTP to uvicorn, which passes it through my middleware to my route
> handler, which queries Postgres. The JSON response retraces the path back to me."

If you can say that unprompted, you've got the topic.

---

## Per-request vs amortised costs

Not every step happens every time — this is why connection reuse (file 02) matters so much:

| Step | Per request? | Notes |
|---|---|---|
| DNS lookup | Amortised | Cached for the TTL; not repeated per request |
| TCP handshake | **Amortised** with keep-alive | Paid once per connection, then reused |
| TLS handshake | **Amortised** with keep-alive | Same — the expensive part is setup, reuse skips it |
| The actual request/response | Per request | Always |

So a "cold" first request pays DNS + TCP + TLS setup (could be 200ms+ over distance), while every
subsequent request on the same warm connection skips all of it. **This is the entire justification for
connection pools (topic 04) and reused HTTP clients** — you're avoiding steps 1–3 on every call.

---

## The timeout taxonomy ⭐ (the most useful part of this file)

Every hop in the journey can have its *own* timeout, and they're **different kinds of timeout**.
Confusing them is how you get baffling production behaviour. The four you must distinguish:

| Timeout | Fires when... | Typical owner |
|---|---|---|
| **Connect timeout** | Can't establish the TCP connection in time (server down/unreachable) | HTTP clients, LBs |
| **Read timeout** | Connected, but the response bytes don't arrive in time (slow backend) | HTTP clients, proxies |
| **Idle timeout** | A kept-alive connection sits unused too long and gets closed | Proxies, LBs, servers |
| **Overall / request deadline** | Total time budget for the whole operation, regardless of phase | Your app, gateways |

### Why timeouts must be *ordered*

Here's the rule that prevents a huge class of bugs:

> **Each layer's timeout should be slightly longer than the layer beneath it, and the client's should
> be the longest** — so the layer closest to the actual work is the one that gives up first, and it
> can return a *meaningful* error instead of the outer layer killing a connection mid-work.

If they're mis-ordered, you get mysteries. The classic:

- nginx `proxy_read_timeout` is 60s. Your backend has no timeout and takes 90s on a slow query.
- At 60s, **nginx gives up** and returns **`504 Gateway Timeout`** to the client — but your backend is
  *still running the query*, oblivious. The client sees a 504; your app logs show the request
  eventually "succeeding." Nobody's story matches. → "clients see 504 after exactly 60s" is a
  dead giveaway of a proxy read-timeout shorter than the backend's work.

### `502` vs `504` — read them as clues

- **`504 Gateway Timeout`** = the proxy/LB *waited* for the backend and it was **too slow** (a timeout fired). Look at read timeouts and slow queries.
- **`502 Bad Gateway`** = the proxy got an **invalid/empty response** — backend crashed, closed the
  connection, or spoke garbage. Look at backend errors/restarts, not timeouts.

Knowing which one you're seeing tells you *which direction to look* — timeout vs crash.

**Lab connection:** planning Lab 6 has you set `proxy_read_timeout 5s`, hit a `/slow?seconds=10`
endpoint, and watch the 504 appear while the backend keeps running. Do it — manufacturing the bug
once makes you recognise it forever.

---

## The debugging drill this enables

When someone says "the API is slow/broken," you now have an ordered checklist by layer:

1. **DNS** resolving correctly and fast? (`dig`)
2. **TCP** connecting? (connect timeout / refused = server down or wrong port)
3. **TLS** valid? (expired cert / chain error = handshake fails)
4. **LB/proxy** — which backend, is it healthy, what are its timeouts?
5. **App** — is the handler slow (profile it, topic 19) or erroring (logs, topic 14)?
6. **DB** — slow query? (topic 04's `EXPLAIN`)

You're no longer guessing — you're walking the path.

---

## Check yourself

1. Narrate the full journey of `https://api.example.com/todos` from Enter to JSON, naming every protocol.
2. Which steps are paid *per request* vs *amortised by keep-alive*, and what's the practical consequence?
3. Define connect vs read vs idle vs overall timeout — what triggers each?
4. State the timeout-ordering rule and explain the bug you get when it's violated.
5. A client reports "504 after exactly 60 seconds." What's your hypothesis and which config do you check?
6. What's the difference in meaning between `502` and `504`, and which way does each send you looking?
