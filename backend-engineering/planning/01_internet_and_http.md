# 01 — Internet & HTTP: How a Request Actually Works

> Phase 1 · Foundations · No prerequisites — this is the ground floor.

---

## 1. Why this matters

Every backend problem at scale eventually drops below the framework: timeouts that fire at the
wrong layer, connection pools exhausting, load balancers marking healthy nodes dead, TLS
handshakes eating your p99 latency, an app logging the proxy's IP instead of the client's.

FastAPI hands you a parsed request object — this topic is about everything that happened
**before** your route function ran. Once you can narrate the full journey
(browser → DNS → TCP → TLS → load balancer → reverse proxy → uvicorn → your code),
debugging production issues stops being guesswork.

This topic also plants seeds you'll harvest later: Docker networking (15), k8s Services &
ingress (16), VPCs (18), CDNs (06) are all "this topic, applied".

---

## 2. Concepts in depth

### 2.1 The layered model (just enough)
- TCP/IP model: link → internet (IP) → transport (TCP/UDP) → application (HTTP)
- Encapsulation — what a packet actually contains, layer by layer
- OSI model: know it exists, know "L4 vs L7" terminology comes from it

### 2.2 IP, ports & addressing
- IPv4 vs IPv6, public vs private ranges (`10.x`, `172.16–31.x`, `192.168.x`)
- CIDR notation (`10.0.0.0/16`) — you'll need this for VPCs and k8s CIDRs later
- NAT — why your laptop can reach the internet but the internet can't reach your laptop
- Ports, ephemeral ports, why "address already in use" happens

### 2.3 TCP (and its trade-offs)
- Three-way handshake (SYN / SYN-ACK / ACK) — what a "connection" actually is
- Reliability machinery: sequence numbers, ACKs, retransmission
- Flow control vs congestion control (high-level; know slow start exists)
- Connection lifecycle states you WILL meet in production: `TIME_WAIT`, `CLOSE_WAIT`
- Keep-alive: why reusing connections matters (handshake + slow start cost)
- Head-of-line blocking at the TCP level — remember this for HTTP/2's limits
- UDP contrast: no handshake, no ordering, no retransmission — why DNS and QUIC choose it

### 2.4 DNS
- Full resolution path: stub resolver → recursive resolver → root → TLD → authoritative
- Record types that matter: `A`, `AAAA`, `CNAME`, `TXT`, `MX`, `NS`, `SRV`
- TTL & caching at every layer; why "DNS propagation" is mostly a myth about caches
- Why the zone apex can't be a CNAME (and ALIAS/ANAME workarounds)
- `/etc/hosts` (you already used this for `todo.local`), `dig`, `nslookup`
- Preview: DNS **is** service discovery — Docker DNS and k8s `Service` names build on this

### 2.5 TLS
- The three guarantees: confidentiality, integrity, authenticity — and which part provides each
- Handshake flow; TLS 1.2 vs 1.3 (1.3 = one less round trip, only strong ciphers)
- Certificates & the chain of trust: leaf → intermediate → root CA
- Let's Encrypt / ACME — how free automated certs work
- SNI (many domains, one IP) and ALPN (how HTTP/2 gets negotiated)
- mTLS — both sides present certs (preview: service-to-service auth, service mesh)
- TLS termination strategies: at the load balancer vs end-to-end — trade-offs

### 2.6 HTTP/1.1 — the workhorse
- Anatomy of request & response on the wire (start line, headers, blank line, body)
- Methods + semantics: safe vs idempotent vs neither — **why PUT is idempotent and POST isn't**
- Status code families + the ones that matter:
  `200/201/204`, `301/302/304/307/308`, `400/401/403/404/409/422/429`, `500/502/503/504`
- Headers that matter: `Host`, `Content-Type`, `Content-Length` vs `Transfer-Encoding: chunked`,
  `Connection`, `Authorization`, `Accept`, `User-Agent`
- Cookies: `Set-Cookie` attributes (`HttpOnly`, `Secure`, `SameSite`) — preview of topic 07
- Keep-alive & pipelining; HTTP-level head-of-line blocking; the 6-connections-per-origin hack

### 2.7 HTTP/2
- Binary framing, streams, multiplexing — many requests on ONE TCP connection
- HPACK header compression
- Server push (know it existed and why it was removed)
- The remaining flaw: TCP head-of-line blocking still applies under packet loss

### 2.8 HTTP/3 & QUIC
- QUIC = transport over UDP with TLS 1.3 built in
- 0-RTT resumption, no transport HOL blocking, connection migration (wifi → cellular)
- Where it matters (mobile, lossy networks) and current adoption reality

### 2.9 Life of a request — the synthesis
Narrate every hop and **where latency/timeouts live at each one**:
```
browser → DNS lookup → TCP handshake → TLS handshake → CDN/LB → reverse proxy
        → uvicorn (ASGI) → middleware → route handler → DB → response (reverse path)
```
- Which hops are per-request vs amortized by connection reuse
- Timeout taxonomy: connect timeout vs read timeout vs idle timeout vs LB timeout —
  and how a mismatch produces mystery 502/504s

### 2.10 Proxies & load balancers
- Forward proxy vs reverse proxy — direction of "who is hidden"
- L4 vs L7 load balancing: what each can see and therefore what each can do
- Algorithms: round robin, weighted, least-connections, IP-hash; consistent hashing (preview: caching)
- Health checks (active vs passive), connection draining, graceful deploys
- The forwarded-headers problem: `X-Forwarded-For`, `X-Forwarded-Proto`, `Forwarded` —
  and why blindly trusting them is a security hole
- Sticky sessions — how they work and why stateless services avoid needing them
- Tools landscape: nginx, HAProxy, Traefik, Caddy — one paragraph each, when you'd pick which

---

## 3. Hands-on labs

> Code goes in `labs/01_internet_and_http/`. Your todo-app is the guinea pig throughout.

**Lab 1 — Watch the wire.**
Run todo-app locally. Use `tcpdump`/Wireshark (or `mitmproxy`) to capture a `curl` request.
Identify: handshake packets, the HTTP request bytes, ACKs, connection close.
Then send two requests with `curl --keepalive` vs two separate `curl` runs — count handshakes.

**Lab 2 — DNS spelunking.**
`dig +trace google.com` and follow the delegation chain by hand. Inspect `A`, `CNAME`, `TXT`,
`MX` records of a few real domains. Check TTLs. Explain your existing `todo.local` hosts entry
in terms of the resolution path (which step does it short-circuit?).

**Lab 3 — TLS up close.**
`openssl s_client -connect google.com:443` — read the cert chain, protocol version, cipher.
Then use `mkcert` to mint a local CA + cert and serve the todo-app over HTTPS via nginx.
Verify the padlock; inspect your own chain with `openssl`.

**Lab 4 — Build a load balancer (the core lab).**
docker-compose: nginx in front of **two** todo-app containers. Add a `/whoami` endpoint
returning an instance id. Watch round-robin happen. Add health checks, then `docker stop`
one backend mid-traffic and observe nginx's failover behavior and error codes.

**Lab 5 — HTTP/1.1 vs HTTP/2.**
Enable `http2` in nginx. Compare `curl -v --http1.1` vs `curl -v --http2` (note the ALPN
negotiation in verbose output). Load a page with many assets through both; compare waterfall.

**Lab 6 — Timeout forensics.**
Add a `/slow?seconds=n` endpoint. Set nginx `proxy_read_timeout 5s`. Call with n=3 and n=10 —
observe who gives up, and what status the client sees (this is where 504s are born).
Then fix client IP logging: uvicorn `--proxy-headers` + `--forwarded-allow-ips` so FastAPI
sees the real client IP, and explain why that flag has an allowlist.

---

## 4. AWS mapping

| Concept you learned locally | AWS equivalent | Key differences |
|---|---|---|
| DNS, records, TTL | **Route 53** | Adds health-checked routing policies (failover, latency, weighted) |
| nginx as L7 LB | **ALB** | Managed, target groups = your upstream blocks, integrates with ACM |
| nginx as L4 / HAProxy TCP | **NLB** | Preserves source IP, millions of conns, static IPs |
| mkcert / Let's Encrypt | **ACM** | Free public certs, auto-renewal, but only usable on AWS services |
| Forwarded headers handling | Same problem on ALB | ALB sets `X-Forwarded-For`; you still must configure trust |
| Health checks & draining | Target group health checks, deregistration delay | Same concepts, YAML→console/IaC |

*(VPC/subnets/security groups belong to topic 18 — but the CIDR + NAT foundations are from here.)*

---

## 5. Mini-project — "Production-shaped todo-app"

Make your local todo-app deployment look like a real production edge, in
`labs/01_internet_and_http/production-shaped/`:

1. nginx reverse proxy, TLS via mkcert, HTTP→HTTPS redirect (301)
2. Two backend replicas, round-robin, active health checks on `/health`
3. Correct forwarded headers end-to-end — app logs must show real client IP and `https` scheme
4. Sane timeouts at each layer (client < nginx < uvicorn), documented in a comment: which fires first and why
5. `/whoami` endpoint + a small script that hammers it and prints the distribution across replicas
6. Bonus: HTTP/2 enabled, verified with `curl --http2 -v`

Done = you can draw the whole request path on paper and point at where each config line acts.

---

## 6. Self-check — you're done when you can…

1. Narrate everything that happens when you hit `https://api.example.com/todos` — from keyboard to JSON — naming every protocol involved.
2. Explain the difference between `301`, `302`, `304`, `307`, `308` and when a `POST` body survives a redirect.
3. Explain what `TIME_WAIT` is and why a server under heavy short-connection load accumulates thousands of them.
4. Explain why TLS 1.3 is faster than 1.2, and what SNI and ALPN each do.
5. Argue L4 vs L7 load balancing trade-offs and pick one for: a WebSocket service, a REST API, a game server.
6. Explain what HTTP/2 multiplexing fixes, and which head-of-line blocking problem it does NOT fix (and how HTTP/3 does).
7. Explain how your app behind two proxies determines the real client IP — and how an attacker exploits naive `X-Forwarded-For` trust.
8. Explain why a CNAME can't live at the zone apex, and what an A record vs CNAME actually resolves to.
9. Diagnose from symptoms: "clients see 504 after exactly 60s" — list the layers you'd check, in order.
10. Explain when UDP is the right choice, with two real examples.

---

## 7. Resources

- **High Performance Browser Networking** — Ilya Grigorik, free at [hpbn.co](https://hpbn.co) · the canonical book for 2.3–2.8; read chapters 1–4 and 9–13
- **The Illustrated TLS 1.3 Connection** — [tls13.xargs.org](https://tls13.xargs.org) · every byte of a handshake, annotated
- **Cloudflare Learning Center** — short, excellent explainers on DNS, TLS, HTTP/3, load balancing
- **Julia Evans — "Life of an HTTP request" & networking zines** — [jvns.ca](https://jvns.ca) · best intuition-builders around
- **MDN HTTP docs** — reference for methods, status codes, headers (keep open during labs)
- **RFC 9110 (HTTP Semantics)** — don't read cover to cover; use it to settle arguments
