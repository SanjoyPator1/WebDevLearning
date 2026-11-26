# 03 — DNS

## Why this matters

DNS turns `api.example.com` into an IP address. It feels like magic infrastructure you never touch —
until a deploy "isn't taking effect" (DNS cache), a cert won't validate (wrong record), or you're
wiring up service discovery in Docker/Kubernetes (which is *literally* DNS). Understanding DNS also
demystifies your own `todo.local` hosts hack.

---

## The core idea

Humans remember names; machines route to numbers. DNS is a giant, distributed, cached lookup table
from names to IP addresses (and other records). "Distributed and cached" is the whole story — nobody
owns the full table, and answers are cached everywhere.

---

## The resolution path — who answers your query

When your app resolves `api.example.com`, it's usually not one lookup but a chain:

```
Your app
  │  "what's api.example.com?"
  ▼
Stub resolver (your OS)  ── checks local cache, /etc/hosts first
  │
  ▼
Recursive resolver  (your ISP's, or 8.8.8.8 / 1.1.1.1)
  │  does the legwork, caches aggressively
  │
  ├──►  Root servers      "who handles .com?"        → "ask the .com TLD servers"
  │
  ├──►  TLD servers (.com) "who handles example.com?" → "ask example.com's authoritative servers"
  │
  └──►  Authoritative servers (example.com)  "what's api.example.com?" → "93.184.216.34"
  ▲
  │ answer flows back, cached at each step
Your app gets 93.184.216.34
```

- **Stub resolver**: the thin client in your OS. Checks `/etc/hosts` and local cache before asking anyone.
- **Recursive resolver**: does the actual walking of the tree and **caches** results. This is where most caching lives.
- **Root → TLD → Authoritative**: the hierarchy. Root knows who runs each TLD (`.com`, `.org`); the TLD knows who's authoritative for each domain; the authoritative server has the real answer.

The `dig +trace google.com` lab (planning Lab 2) walks this exact chain by hand — do it once and it clicks permanently.

---

## Record types that matter

A DNS zone holds different **record types**:

| Record | Maps name to | Notes |
|---|---|---|
| `A` | IPv4 address | The most common — `example.com → 93.184.216.34` |
| `AAAA` | IPv6 address | Same idea, IPv6 |
| `CNAME` | another **name** (alias) | `www.example.com → example.com`. Resolver then looks up *that* name |
| `MX` | mail server | Where email for the domain goes |
| `TXT` | arbitrary text | Domain verification, SPF/DKIM (email auth), Let's Encrypt challenges |
| `NS` | authoritative name servers | "who is authoritative for this zone" |
| `SRV` | service host+port | Service discovery (used by some systems) |

You'll mostly create `A`, `CNAME`, and `TXT` records in real work (pointing a domain at a load
balancer, aliasing `www`, proving domain ownership for a TLS cert).

---

## TTL & caching — why "DNS propagation" is mostly a myth

Every DNS record has a **TTL** (time-to-live, in seconds) — "you may cache this answer for this long."
Every resolver along the chain caches until the TTL expires.

**The "propagation" misconception:** when you change a DNS record, people say "waiting for DNS to
propagate." There's no active propagation — you're just **waiting for old cached answers to expire**
across the world's resolvers (up to the old TTL). This is why:
- You **lower the TTL in advance** (e.g. to 60s) before a planned DNS change, so caches expire fast.
- After the change, some clients see the new value immediately (cache expired) and some see the old
  one (cache still warm) — not a bug, just caching.

---

## The zone apex + CNAME gotcha

You can't put a `CNAME` at the **zone apex** (the bare domain, `example.com` with no subdomain). The
DNS spec forbids a CNAME coexisting with the other records a zone apex must have (like `NS` and `SOA`).

This bites everyone deploying to a cloud load balancer, because the LB gives you a *name*
(`my-lb-123.elb.amazonaws.com`), not an IP, and you want `example.com` to point at it. Solutions:
- Use a subdomain (`www.example.com` → CNAME → the LB name) — allowed.
- Use your DNS provider's **ALIAS / ANAME** record (Route 53 calls it "Alias") — a CNAME-like record
  that's legal at the apex because the provider resolves it server-side into an `A` record.

You don't need to memorise the RFC — just remember: **bare domain + CNAME = not allowed; use ALIAS or a subdomain.**

---

## `/etc/hosts` — and your `todo.local` hack explained

`/etc/hosts` is a local file the stub resolver checks *before* going to any DNS server. A line like:

```
127.0.0.1   todo.local
```

...short-circuits resolution: `todo.local` resolves to `127.0.0.1` without ever touching real DNS.
That's exactly what your Kubernetes setup did (`echo "127.0.0.1 todo.local" >> /etc/hosts`) — it let
you use a real-looking hostname for local ingress without registering a domain. Now you can explain
*which step of the resolution path it intercepts*: the very first one, in the stub resolver.

---

## DNS *is* service discovery (the forward reference)

Hold onto this, because it pays off later:
- In **Docker Compose** (topic 15), a service named `db` is reachable at the hostname `db` — Docker
  runs an embedded DNS server that resolves service names to container IPs.
- In **Kubernetes** (topic 16), a Service is reachable at `my-svc.my-namespace.svc.cluster.local` —
  again, DNS (CoreDNS) resolving a stable name to the current pod IPs.

So "how does service A find service B?" in modern infra is answered by the same mechanism you're
learning here. DNS isn't just for the public internet — it's the backbone of internal service discovery.

---

## Tools

- `dig example.com` — the DNS Swiss army knife; shows records, TTLs, which server answered.
- `dig +trace example.com` — walk the full root → TLD → authoritative chain yourself.
- `dig example.com MX` (or `TXT`, `NS`) — query a specific record type.
- `nslookup` — simpler, more portable, less detail.

---

## Mental model

> DNS is a **cached, hierarchical phone book**. Nobody holds the whole book; you ask a librarian (the
> recursive resolver) who knows how to walk from "the .com section" down to the exact entry, and
> everyone writes down answers on sticky notes (caches) that expire after the TTL.

---

## Check yourself

1. Name the four tiers a recursive resolver walks (root → ? → ? → answer) and what each knows.
2. Which component does most of the caching, and why is that where "propagation delay" comes from?
3. What's the difference between an `A` record and a `CNAME`? What does each resolve *to*?
4. Why can't you put a CNAME on `example.com` itself, and what do you use instead?
5. Explain your `todo.local` `/etc/hosts` entry in terms of the resolution path — which step does it intercept?
6. How does a Docker Compose service named `db` become reachable as the hostname `db`? What's the general principle?
