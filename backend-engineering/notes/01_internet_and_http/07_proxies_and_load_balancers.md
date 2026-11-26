# 07 — Proxies & Load Balancers

## Why this matters

Your backend almost never faces the internet directly. Between the client and your uvicorn process
sits at least one **proxy** — usually a load balancer and a reverse proxy. They do TLS termination
(file 04), spread traffic across instances, health-check, and handle failover. Getting their config
right (especially forwarded headers and timeouts) is a huge chunk of real backend/ops work, and
misconfiguring them causes outages and security holes.

---

## Forward proxy vs reverse proxy — which side is hidden

Both sit in the middle, but they hide *different* ends:

- **Forward proxy** — sits in front of **clients**, hides the clients from the server. (Corporate
  proxy, VPN egress.) The server sees the proxy, not the real client.
- **Reverse proxy** — sits in front of **servers**, hides the servers from clients. The client thinks
  it's talking to one machine; really the proxy is routing to a fleet behind it. **This is the one you
  care about** — nginx, Traefik, Caddy, and cloud load balancers are all reverse proxies.

```
Forward proxy:   [clients] → (proxy) → server        proxy speaks for the clients
Reverse proxy:   client → (proxy) → [servers]        proxy speaks for the servers
```

Your nginx labs are reverse proxies: one public endpoint, multiple todo-app instances behind it.

---

## What a reverse proxy / load balancer does for you

- **TLS termination** (file 04) — holds the cert, decrypts once at the edge.
- **Load balancing** — spreads requests across healthy backend instances.
- **Health checking** — stops sending traffic to dead instances.
- **Routing** — path/host-based (`/api` → backend A, `/` → frontend).
- **Buffering, compression, rate limiting** (topic 19), caching (topic 06).
- **A single stable address** — clients hit one place; you can add/remove/replace backends freely.

That last point is the deep value: the proxy **decouples** the public address from the actual servers,
which is what makes horizontal scaling and zero-downtime deploys possible (topics 16, 17).

---

## L4 vs L7 load balancing ⭐ (the key distinction)

Recall from file 01 that **L4 = transport (TCP)** and **L7 = application (HTTP)**. A load balancer
operates at one of these layers, and it determines what it can *see* and therefore *do*:

### L4 (transport) load balancer
- Works at the TCP level. Sees IPs, ports, and raw bytes — **not** HTTP.
- Just forwards TCP connections to a backend. Fast, simple, protocol-agnostic.
- **Cannot** read URLs, headers, or cookies (they're inside the encrypted/opaque byte stream).
- **Can** pass TLS straight through to the backend without decrypting (file 04) — good when you need
  end-to-end encryption or the traffic isn't HTTP.

### L7 (application) load balancer
- Understands HTTP. Sees the method, path, headers, cookies.
- **Can** route by URL (`/api/*` → one pool), add headers, terminate TLS, do sticky sessions, retry
  failed requests, rate-limit per route.
- **Must** terminate TLS to read the HTTP inside (file 04) — it can't route on a URL it can't decrypt.
- Slightly more overhead, vastly more capable.

### Choosing (a common interview question)

| Workload | Pick | Why |
|---|---|---|
| REST API needing path routing, header inspection | **L7** | Needs to read HTTP |
| WebSocket service (file: topic 09) | Often **L4** (or L7 with WS support) | Long-lived connections; L4 just pipes bytes |
| Raw TCP / non-HTTP protocol, or end-to-end TLS | **L4** | Nothing to read at L7; pass bytes through |
| Game server, database proxy | **L4** | Not HTTP |

> Rule of thumb: **need to make decisions based on the HTTP content → L7. Just need to spread
> connections fast, or it's not HTTP → L4.**

---

## Balancing algorithms

How the LB picks *which* backend:

- **Round robin** — next backend in rotation. Simple, default, fine when backends are equal and requests are uniform.
- **Weighted** — bigger backends get more traffic (`weight=3`).
- **Least connections** — send to the backend with the fewest active connections. Better when request durations vary a lot.
- **IP hash** — same client IP always → same backend. A crude way to get session stickiness.
- **Consistent hashing** — hash the key (e.g. a cache key) to a backend such that adding/removing a
  backend only remaps a small fraction of keys. Crucial for distributed caches (topic 06) and sharding
  (topic 19) — remember the term.

---

## Health checks & graceful deploys

- **Active health check:** the LB periodically probes each backend (e.g. `GET /health`). Fails N times → mark it down, stop sending traffic. Recovers → back in rotation.
- **Passive health check:** the LB notices failing *real* requests and ejects the backend.
- **Connection draining / graceful shutdown:** when you remove a backend (deploy, scale-down), the LB
  stops sending *new* requests but lets in-flight ones finish before killing it. This is how you deploy
  without dropping requests — the same concept reappears as readiness probes and `preStop` in
  Kubernetes (topic 16) and graceful worker shutdown (topic 08/09).

**Lab connection:** planning Lab 4 has you run nginx over two todo-app instances, add health checks,
then `docker stop` one mid-traffic and watch failover. That's this section, live.

---

## The forwarded-headers problem ⭐ (a real bug + a security hole)

Here's a subtle one that bites everyone. When a reverse proxy forwards a request to your backend, the
backend sees the connection coming from **the proxy's IP**, not the real client's. So your app logs
show the proxy's IP for every request, rate limiting keys everyone as one client, etc. — all broken.

The fix: proxies add headers carrying the original info:
- `X-Forwarded-For: <client IP>` — the real client's IP (and the chain of proxies).
- `X-Forwarded-Proto: https` — the original scheme (so your app knows it was HTTPS even though the
  proxy forwarded plain HTTP after terminating TLS).
- `Forwarded:` — the standardised modern version of the above.

Your app must be told to **trust and read** these headers. In uvicorn:
```
uvicorn app.main:app --proxy-headers --forwarded-allow-ips="<proxy IP>"
```

### The security hole

Here's why `--forwarded-allow-ips` has an allowlist and isn't just "trust always":

`X-Forwarded-For` is **just a header a client can set**. If your app blindly trusts it from *anyone*,
an attacker sends `X-Forwarded-For: <victim IP>` (or `127.0.0.1`) and spoofs their apparent IP —
bypassing IP-based rate limits, allow-lists, or audit logs. So you must only trust the header when it
comes from **your own proxy** (a known, trusted IP). Everything from an untrusted source is ignored.

> **Principle:** forwarded headers are trustworthy *only* from infrastructure you control. Trusting
> them from the open internet is a spoofing vulnerability. This is a recurring security theme (topic 07).

**Lab connection:** planning Lab 6's second half — configure `--proxy-headers`, verify your app logs
the *real* client IP and `https` scheme, and articulate why the allowlist exists.

---

## Sticky sessions (and why stateless is better)

**Sticky sessions** pin a client to the same backend (via IP hash or a cookie) so that
backend-local state (an in-memory session) stays available. It works, but it's a smell:
- It defeats even load distribution (a heavy client is stuck on one backend).
- It breaks when that backend dies (the client's state is gone).
- It complicates scaling and deploys.

The better answer, which this whole course pushes: **make your app stateless** — keep session state in
Redis/DB (topic 06/07), files in object storage (topic 10) — so *any* backend can serve *any* request
and you never need stickiness. Statelessness is the precondition for clean horizontal scaling (topic 19).
(One real exception: WebSockets are inherently sticky — topic 09 deals with that via a backplane.)

---

## The tools landscape (one line each)

- **nginx** — the ubiquitous, battle-tested reverse proxy / L7 LB. What you're using. Config-file driven.
- **HAProxy** — the specialist load balancer, excellent at L4 and L7, very high performance.
- **Traefik** — cloud-native, auto-discovers services (great with Docker/Kubernetes), automatic Let's Encrypt.
- **Caddy** — simplest config, automatic HTTPS out of the box; lovely for small deployments.
- **Envoy** — the modern, programmable proxy underpinning service meshes (topic 12/16).

Pick nginx to learn the fundamentals (you already are); recognise the others by their niche.

---

## Mental model

> A reverse proxy is a **receptionist for a building full of identical workers.** Clients only know the
> receptionist's address; the receptionist checks IDs (TLS), decides which worker is free (load
> balancing), stops routing to workers who've gone home (health checks), and writes the real visitor's
> name on the message slip (forwarded headers) — but only trusts slips from its own staff, not from
> random people off the street (the security allowlist).

---

## Check yourself

1. Forward vs reverse proxy — which end does each hide, and which is the one you deploy?
2. What can an L7 load balancer do that an L4 one can't, and what must it do (re: TLS) to do it?
3. Pick L4 or L7 for: a REST API with path routing, a WebSocket service, a raw-TCP database proxy — with reasons.
4. What's consistent hashing and why does it matter for distributed caches?
5. Explain active health checks and connection draining, and how they enable zero-downtime deploys.
6. Why does your app log the proxy's IP by default, and how do you fix it correctly?
7. Explain the `X-Forwarded-For` spoofing attack and why `--forwarded-allow-ips` needs an allowlist.
8. Why are sticky sessions a smell, and what's the stateless alternative?
