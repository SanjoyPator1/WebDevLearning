# 06 — Caching: The Cheapest Win and the Nastiest Bugs

> Phase 2 · Data layer · Builds on: 01 (HTTP), 04 (what's slow), 05 (Redis) · Playground: adds **redis** (as cache)

---

## 1. Why this matters

Caching is the highest-leverage performance tool you have: a Redis hit is ~0.5ms while the
Postgres query it replaced was 50ms. It's also the source of the industry's most famous quote
("there are only two hard things: cache invalidation and naming things") — because a cache is
a **deliberately stale copy of the truth**, and every bug in this topic comes from forgetting that.

There are caches at every layer: browser, CDN, reverse proxy, application, database buffer pool.
A backend engineer needs to know which layer to cache at, how staleness will show up, and how
the whole thing fails under load (stampedes, hot keys). This topic covers all layers end to end.

---

## 2. Concepts in depth

### 2.1 Caching theory — the vocabulary
- Hit ratio and why it's THE metric; latency math (hit% × 1ms + miss% × 50ms)
- The cache hierarchy: browser → CDN → reverse proxy → app cache (Redis) → DB buffer pool —
  each with different staleness, scope, and invalidation powers
- What's cacheable: read-heavy + tolerates-staleness + expensive-to-compute; what's not (per-user unless keyed so, money balances, anything read-after-write critical)
- Eviction policies: LRU, LFU, FIFO, TTL-based — and Redis's `maxmemory-policy` flavors (`allkeys-lru`, `volatile-ttl`, …)

### 2.2 Application caching patterns
- **Cache-aside (lazy loading)** — the default 90% pattern: read cache → miss → read DB → fill cache
  - Its failure modes: first-request penalty, stampede on expiry, stale window after writes
- Read-through / write-through — cache library owns the loading/writing; where you meet these (DAX, ORM caches)
- Write-behind (write-back) — fast writes, buffered flush; the data-loss trade
- Refresh-ahead — proactively refresh hot keys before TTL expiry
- For each: a sequence diagram in your notes + one sentence on when it's the right choice

### 2.3 Invalidation — the actual hard part
- Strategy 1: **TTL only** — embrace bounded staleness; choosing TTLs deliberately (how stale can this data be, as a product question, not a guess)
- Strategy 2: **explicit invalidation on write** — delete (not set!) cache keys in the write path;
  why delete-then-write-DB vs write-DB-then-delete both have races (and which race is worse)
- Strategy 3: **versioned/namespaced keys** — `user:42:v7:todos`; bump the version, old keys age out — invalidation without enumeration
- Strategy 4: event-driven invalidation — pub/sub fanout to subscribers (preview: 09 pub/sub, 11 CDC)
- Key design discipline: naming conventions (`{entity}:{id}:{facet}`), key TTL jitter, never unbounded key cardinality

### 2.4 Failure modes under load (interview + production classics)
- **Stampede / thundering herd**: hot key expires → 500 concurrent requests all miss → DB dies.
  Fixes: per-key mutex/lock ("one fetches, rest wait"), stale-while-revalidate, probabilistic early expiry, request coalescing
- **Cache penetration**: requests for keys that don't exist (or attackers guessing IDs) always miss → DB hammered.
  Fixes: negative caching (cache the 404, short TTL), bloom filter of valid keys
- **Hot key**: one celebrity key takes all traffic on one Redis node. Fixes: local cache layer, key replication (`key:{1..N}`)
- **Avalanche**: many keys expire simultaneously (deploy warmed them together). Fix: TTL jitter
- Cache consistency vs DB after crashes: the cache is ALWAYS allowed to be wrong — design so wrong = slightly stale, never = corrupt

### 2.5 Redis as a cache in practice
- Serialization choices: JSON vs msgpack vs pickle (never pickle untrusted); size/speed trade-offs
- Pipelining and `MGET` — round trips matter more than command cost (ties to 01 latency thinking)
- `maxmemory` + eviction policy configuration; monitoring hit ratio (`INFO stats`: keyspace_hits/misses)
- Local in-process cache ON TOP of Redis (two-tier): `functools.lru_cache` / cachetools —
  microsecond hits, but **per-replica coherence problem** (replica A invalidates, replica B's copy lives on)
  → short TTLs on tier-1, or pub/sub invalidation broadcast (09)
- What NOT to cache in-process: anything needing coherence across replicas (ties back to 01 statelessness)

### 2.6 HTTP caching — the cache you don't operate
- `Cache-Control` directives that matter: `max-age`, `s-maxage`, `no-cache` (≠ `no-store`!), `private` vs `public`, `stale-while-revalidate`
- Validators: `ETag`/`If-None-Match`, `Last-Modified`/`If-Modified-Since` → the `304 Not Modified` flow (no body = bandwidth win even when stale)
- Strong vs weak ETags; generating ETags cheaply (updated_at hash, version column from 04)
- `Vary` — the header that makes caches key correctly (Accept-Encoding, Authorization) and the footgun of over-varying
- What's safe to cache for authed APIs (`private`, per-user cache keys) vs what leaks data if you get it wrong

### 2.7 CDN & edge caching
- What a CDN actually is: reverse proxy caches at the edge (01's concepts, geographically distributed)
- Cache keys at the CDN (URL + Vary + configured headers/cookies); why cookies murder your hit ratio
- Invalidation: purge APIs vs versioned asset URLs (`app.v123.js` — the frontend build trick)
- `s-maxage` vs `max-age` (CDN vs browser lifetimes); `stale-while-revalidate` / `stale-if-error` at the edge
- Caching APIs (not just assets): anonymous GETs at the edge — when it works, when auth kills it
- Nginx as micro-cache: `proxy_cache` — a CDN node you run yourself (and the lab we'll use)

### 2.8 Database-side caches (know they exist)
- Postgres buffer pool (`shared_buffers`) — why "second run is fast" in your 04 labs
- Materialized views as query-result caches with explicit refresh — sometimes the honest answer

---

## 3. Hands-on labs

> Code in `labs/06_caching/`. Redis joins the playground as a cache (separate logical DB or instance from 05's usage).

**Lab 1 — Cache-aside, measured.**
Cache `GET /todos` (per-user, per-tenant key from 04's RLS setup) with a 60s TTL.
Load test before/after: p50/p95/p99 + DB query count (pg_stat_statements from 04).
Then update a todo and watch the stale window with your own eyes. Add delete-on-write invalidation. Re-measure.

**Lab 2 — Cause a stampede, then cure it.**
Endpoint with an artificially slow query (500ms) cached with 10s TTL. Fire 200 concurrent
requests right as the key expires — graph DB connections spiking. Fix twice:
(a) per-key Redis lock (`SET NX` + wait-and-retry), (b) stale-while-revalidate (serve old value, refresh in background task).
Compare both fixes' p99 during expiry.

**Lab 3 — Penetration and negative caching.**
Script requests random non-existent todo IDs. Watch every one hit Postgres. Add negative
caching (short-TTL "not found" marker). Bonus: sketch where a bloom filter would sit.

**Lab 4 — ETags and 304s.**
Add `ETag` (from `updated_at`) to `GET /todos/{id}` + `If-None-Match` handling → `304`.
Verify with curl. Then put nginx `proxy_cache` in front (micro-cache, 5s) for the anonymous
endpoints and inspect `X-Cache-Status: HIT/MISS/STALE` headers under load.

**Lab 5 — Two-tier cache and its coherence problem.**
Add an in-process TTL cache (cachetools) in front of Redis. Run 2 app replicas behind your
nginx LB from topic 01. Update a todo via replica A; demonstrate replica B serving stale from
tier-1 while Redis is already correct. Fix with Redis pub/sub invalidation broadcast (your first taste of 09).

**Lab 6 — Watch Redis behave.**
Fill Redis to `maxmemory` with `allkeys-lru`; watch evictions in `INFO stats`. Compute your
hit ratio from keyspace_hits/misses before and after sizing changes. Add TTL jitter to Lab 1's
keys and explain what avalanche scenario it prevents.

---

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| redis container (cache) | **ElastiCache Redis / Valkey** | Same everything; multi-AZ + failover managed |
| nginx proxy_cache / CDN sim | **CloudFront** | `s-maxage`, invalidations ($ per purge path!), origin shield |
| Versioned asset URLs | CloudFront + S3 static hosting | The standard frontend deploy pattern (topic 10 touches S3) |
| Negative caching | CloudFront error caching TTLs | Same idea at the edge |
| API edge caching | **API Gateway caching** | Per-stage TTL cache in front of your API |
| Read-through cache for DynamoDB | **DAX** | Managed read-through/write-through — the 2.2 patterns productized |

---

## 5. Mini-project — "Caching layer with a design doc"

Productionize caching in the todo-app, in `labs/06_caching/`:

1. Cache-aside on the 3 heaviest read endpoints (found via 04's pg_stat_statements), keyed per tenant+user, TTL + jitter
2. Delete-on-write invalidation wired into every write path in the service layer (not scattered in routes)
3. Stampede protection (stale-while-revalidate) on the hottest endpoint
4. ETag/304 on item GETs; `Cache-Control: private, max-age=…` headers chosen per endpoint with justification
5. A `/internal/cache-stats` endpoint: hit ratio, per-key-prefix counts
6. **`CACHING.md`** — the design doc: per endpoint → key schema, TTL, invalidation trigger, acceptable staleness,
   failure mode analysis (what happens if Redis dies? → app must degrade to DB, not 500)

Done = Redis can be killed mid-load-test and the app slows down but stays correct.

---

## 6. Self-check — you're done when you can…

1. Draw the full cache hierarchy from browser to buffer pool and state what each layer can and can't invalidate.
2. Whiteboard cache-aside including BOTH write-order races, and say which one you accept and why.
3. Explain three stampede cures and choose one for a given traffic pattern.
4. Explain penetration vs stampede vs avalanche vs hot key — different problems, different fixes, no hand-waving.
5. Explain why you DELETE cache keys on write instead of SETting the new value (hint: what does the setter not know under concurrency?).
6. Design a key schema + TTL policy for a multi-tenant API and defend each TTL as a product decision.
7. Explain `no-cache` vs `no-store`, `max-age` vs `s-maxage`, `private` vs `public`, and what `Vary` does to a cache key.
8. Walk through the ETag/304 flow and say what it saves (and does not save) compared to a cache hit.
9. Explain the two-tier coherence problem across replicas and two ways to bound it.
10. Describe how the app must behave when Redis is down — and how you'd verify it does.

---

## 7. Resources

- **web.dev "HTTP cache" + MDN `Cache-Control` docs** — the authoritative 2.6 references
- **Redis docs: eviction policies, `INFO`, pipelining** — short, canonical
- **"Scaling Memcache at Facebook" (paper)** — THE production caching paper: leases (stampede), pools, invalidation at scale; very readable
- **Cloudflare & AWS CloudFront caching docs** — how real CDNs compute cache keys and purge
- **Designing Data-Intensive Applications** — §"Problems with Replication Lag" pairs perfectly with stale-cache reasoning
- **Stripe/GitHub API docs (revisited)** — notice their `Cache-Control`/`ETag` usage on real endpoints
