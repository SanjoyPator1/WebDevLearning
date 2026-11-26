# 19 — Performance & Scalability: Making It Fast, Then Making It Handle Load

> Phase 7 · Scale & synthesis · Builds on: 02, 04, 06, 08, 12, 14 (this topic is where they all converge)
> Approach: measurement-first — you already have the observability (14) and load tools (13) to do this right

---

## 1. Why this matters

"Make it faster" and "make it handle more" are different problems, and both are usually attacked
wrong — by guessing. This topic is the discipline of **measure → find the bottleneck → fix the
right thing → measure again**, plus the toolbox of scaling techniques (horizontal scaling, read
replicas, sharding, rate limiting) you reach for once you actually know where the limit is.

It's deliberately near the end because performance work is synthesis: the bottleneck is always in
something you already learned — the event loop (02), a missing index or connection pool (04), a
cold cache (06), a slow downstream (12) — and you find it with the tools from topic 14. This topic
ties the room together.

---

## 2. Concepts in depth

### 2.1 The performance mindset (internalize before touching anything)
- **Measure, don't guess** — Knuth's "premature optimization" in full context; the bottleneck is rarely where you think
- Latency vs throughput — different goals, sometimes opposed; optimize the one that matters for the use case
- **Percentiles, not averages** (topic 14, again): p50/p95/p99/p99.9 — why the average hides the users who are actually suffering; tail latency and why it dominates at scale (fan-out amplifies tails)
- **Little's Law** (`concurrency = throughput × latency`) — the one equation that connects them; use it to reason about capacity
- Define the goal first: a latency SLO (topic 14) or a throughput target — "fast" is not a target
- The USE/RED methods (topic 14) as the starting map for "what's saturated?"

### 2.2 Finding bottlenecks — the toolbox
- **Profiling**: CPU profilers (py-spy — sampling, works on running prod processes!, cProfile, Scalene), memory profilers (memray, tracemalloc), flame graphs (reading them)
- **Application-level**: the trace waterfall (topic 14) to spot serial-that-should-be-parallel (topic 02), N+1 (topics 03/05), slow dependencies (topic 12)
- **Database**: `EXPLAIN ANALYZE` + `pg_stat_statements` (topic 04) — usually the #1 backend bottleneck
- **System-level**: CPU vs memory vs I/O vs network bound — identifying which (the USE method); tools (top/htop, iostat)
- The method: reproduce under load (topic 13) → profile → find the ONE biggest cost → fix → re-measure (never fix two things at once)

### 2.3 Application-level performance
- Async correctly (topic 02): parallelize independent I/O (gather), don't block the loop — the single biggest FastAPI win
- N+1 elimination: eager loading / batching / DataLoader (topics 03/05)
- Serialization cost: Pydantic v2/orjson, response size, pagination (topic 03) — JSON encoding is real CPU at scale
- Connection reuse: HTTP keep-alive to downstreams (topic 01), pooled DB connections (topic 04), pooled clients
- Doing less: caching (topic 06), avoiding redundant work, precomputation (materialized views, topic 04), moving work off the request (topic 08)
- Right-sizing workers/threads (topic 02) and pods (topic 16) from real numbers

### 2.4 Database performance & scaling ⭐ (the usual real bottleneck)
- Query optimization first (topic 04) — indexes, query rewrites, N+1 — before ANY scaling (scaling a slow query just scales the slowness)
- Connection management at scale (topic 04's §2.7) — pooling, PgBouncer, the connection math
- **Vertical scaling** (bigger box) — the simplest lever, real ceiling, know when you've hit it
- **Read replicas** (topic 04): offload reads; the **replication lag / read-your-writes** problem (topics 04/12) and how to route around it (read-after-write to primary)
- **Caching** as DB-load-reduction (topic 06) — often cheaper than scaling the DB
- **Partitioning** (topic 04): splitting a big table; partition pruning
- **Sharding** ⭐: horizontal split across DBs by a shard key; choosing the key (even distribution + query locality — echoes topics 05/11 partitioning); the hard parts: cross-shard queries, rebalancing, hot shards, distributed transactions (topic 12); when you genuinely need it (usually later than people think)
- CQRS / read models (topic 11) as a scaling strategy; the write-scaling problem specifically (harder than reads)

### 2.5 Horizontal scaling & statelessness
- Scale out vs up: the trade-offs; why stateless (topic 01) is the precondition for horizontal scaling (nothing in local memory/disk — topics 06 two-tier cache, 10 files-in-object-storage, 09 backplane all enforced this)
- Load balancing algorithms (topic 01) revisited for even distribution; the hot-instance problem
- Autoscaling (topic 16 HPA/KEDA): scaling on the RIGHT signal (queue depth/lag/latency, not just CPU — topics 08/11); scale-up vs scale-down asymmetry, thrashing, cooldowns
- Where state actually lives when the app is stateless: DB, cache, object store, backplane — the map

### 2.6 Rate limiting & throttling ⭐ (protecting the system from load)
- Why: protect resources, ensure fairness across tenants (topic 04 noisy neighbor), prevent abuse/DoS, cost control
- Algorithms in depth: **token bucket** (bursty-friendly), **leaky bucket**, **fixed window** (the boundary-spike flaw), **sliding window log/counter** (topic 05 Lab 2 built one) — trade-offs and when each
- Distributed rate limiting: shared state in Redis (topic 06), atomicity via Lua, the accuracy-vs-latency trade
- Scope & keys: per-user, per-IP, per-tenant, per-endpoint, global; tiered limits (free vs paid)
- Client contract (topic 03): `429`, `Retry-After`, `RateLimit-*` headers; graceful client backoff (topic 12)
- Where it lives: edge/gateway (topic 03/18 WAF/API GW) vs app; load shedding & backpressure (topics 08/12) as the overload cousins

### 2.7 Frontend-adjacent & delivery performance
- CDN (topics 06/10) for static + cacheable dynamic; edge caching wins
- Compression (gzip/brotli), HTTP/2-3 (topic 01), payload minimization, pagination (topic 03)
- The full latency budget from topic 01 revisited: where the milliseconds actually go end-to-end

### 2.8 Capacity planning & load modeling
- From load tests (topic 13) to a capacity model: RPS per instance, headroom, Little's Law (§2.1)
- Planning for peak (spikes, topic 09 reconnect storms), growth, and failure (N+1 redundancy — lose an AZ, topic 18)
- Cost/performance trade (topic 18): the cheapest architecture that meets the SLO, not the fastest possible
- Benchmarking honestly: warm vs cold, realistic data volume (topic 04's 5M rows), representative traffic mix

### 2.9 Common scalability patterns & anti-patterns
- Patterns: cache-aside (06), read replicas, async/queue offload (08), event-driven decoupling (11), CQRS (11), sharding, edge/CDN (10)
- Anti-patterns: scaling before measuring, sharding too early, cache as a crutch for a missing index, chatty services (topic 12), unbounded queries/fan-out, synchronous everything
- The scalability ladder: single box → vertical → stateless + horizontal + cache → read replicas → async/CQRS → shard → (rarely) full distribution — climb only as far as you must

---

## 3. Hands-on labs

> Code in `labs/19_performance_and_scalability/`. Use topic 13's load tools + topic 14's observability throughout — this whole topic is measure-driven.

**Lab 1 — Profile and fix (CPU).**
Add a deliberately hot endpoint (heavy serialization / a wasteful loop). Profile with py-spy under
load; read the flame graph; find and fix the hotspot. Measure p99 before/after. No guessing allowed —
the profiler must justify the fix.

**Lab 2 — The N+1 hunt.**
Reintroduce an N+1 (topics 03/05) in a list endpoint. Find it via the trace waterfall (topic 14),
NOT by reading code. Fix with eager loading/batching. Quantify the query-count and latency drop.

**Lab 3 — DB scaling ladder.**
On the 5M-row todo-app (topic 04): (a) optimize the worst query with an index; (b) add a read
replica and route reads to it; (c) demonstrate the replication-lag read-your-writes bug and fix it;
(d) add caching (topic 06) and compare which lever gave the most per-effort. Tabulate.

**Lab 4 — Prove statelessness enables scaling.**
Try to horizontally scale a version of the app that holds state in memory (in-process cache/session)
behind the LB (topic 01) — watch it misbehave across replicas. Fix by externalizing state (Redis/
object store/backplane — topics 06/09/10). Now scale to N replicas cleanly.

**Lab 5 — Build all four rate limiters.**
Implement fixed-window, sliding-window, token-bucket, and leaky-bucket rate limiters (distributed,
Redis+Lua). Load-test each; demonstrate fixed-window's boundary spike and token-bucket's burst
handling. Add `429` + `Retry-After` + `RateLimit-*` headers. Make it per-tenant (topic 04).

**Lab 6 — Autoscale on the right signal.**
With KEDA (topic 16): autoscale the API on latency/RPS and the workers on queue depth/lag (topics
08/11). Load-test a spike; watch scaling. Then misconfigure to scale on CPU only and show it
reacting too slowly for an I/O-bound spike. Tune cooldowns to stop thrashing.

**Lab 7 — Capacity model from a load test.**
Load-test to find RPS-per-instance and the latency knee (topic 13). Build a capacity model with
Little's Law: "to serve X RPS at p99<Y with N+1 redundancy, I need Z instances." Validate by
scaling to Z and hitting X. Add the cost number (topic 18).

**Lab 8 — Sharding (awareness lab).**
Shard the todos table across 2 logical databases by tenant_id. Implement shard routing. Demonstrate
a cross-shard query's pain and a hot-shard scenario. Write when you'd actually do this vs simpler options.

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| Read replicas | RDS/Aurora read replicas | Aurora replicas have lower lag |
| Autoscaling (HPA/KEDA) | EKS + KEDA / ECS Service Auto Scaling / Lambda | Scale on the right metric |
| Rate limiting at edge | **WAF rate rules / API Gateway throttling** | Topic 18; before it hits your app |
| DDoS protection | **Shield / Shield Advanced** | Volumetric protection |
| CDN performance | CloudFront (topics 06/10) | Edge offload |
| Caching layer | ElastiCache / DAX | Topic 06 |
| Sharding-friendly serverless DB | DynamoDB (auto-partitions) | Topic 05's contract = built-in sharding |
| Capacity/cost | Compute Optimizer + Cost Explorer | Right-sizing (topic 18) |

---

## 5. Mini-project — "Scale the todo-app platform to a target, with proof"

In `labs/19_performance_and_scalability/`:

1. Set an explicit goal: "serve N RPS at p99 < X ms, survive a 5× spike, tolerate one AZ loss"
2. Load-test the baseline (topic 13); profile and fix the top 3 bottlenecks with before/after evidence (topic 14)
3. Make it fully stateless and horizontally scalable; autoscale API and workers on the right signals
4. DB scaling: query optimization + caching + a read replica with read-your-writes handling
5. Per-tenant distributed rate limiting (token bucket) with proper `429`/headers
6. A validated capacity model (Little's Law) + cost analysis (topic 18); a spike test proving the 5× survives
7. **`SCALE.md`**: the goal, the measurement-driven bottleneck story, every scaling decision + its
   evidence, the capacity model, and the cost. (This is the artifact that proves you scale by data, not vibes.)

Done = you hit a stated throughput/latency target, can prove where every bottleneck was and how you found it, and never once optimized by guessing.

---

## 6. Self-check — you're done when you can…

1. Explain latency vs throughput and Little's Law, and use the law to size a service.
2. Explain why you optimize p99 not the average, and why tail latency worsens with fan-out.
3. Describe your measurement-first method and name the tool you'd reach for at each layer (app/DB/system).
4. Explain why query optimization must precede DB scaling, and walk the DB scaling ladder.
5. Explain read replicas and the read-your-writes problem, with a concrete fix.
6. Explain why statelessness is the precondition for horizontal scaling, and where state lives instead.
7. Compare the four rate-limiting algorithms and pick one for a bursty API, justifying it.
8. Explain distributed rate limiting with Redis and why atomicity (Lua) matters.
9. Explain sharding, how to choose a shard key, and the three hard problems it introduces — and when NOT to shard.
10. Build a capacity model from a load test and turn it into an instance count + cost.

---

## 7. Resources

- **"Systems Performance" — Brendan Gregg** — the definitive performance-methodology book (USE method, profiling); heavy but the reference
- **Designing Data-Intensive Applications, ch. 5–6** — replication & partitioning (read replicas, sharding) done right
- **py-spy, Scalene, memray docs + "Flame Graphs" (Brendan Gregg)** — the profiling toolkit (§2.2)
- **"The Tail at Scale" (Dean & Barroso, Google paper)** — why p99 dominates at scale; short and foundational
- **Stripe / Cloudflare / Figma engineering blogs on rate limiting** — real token-bucket/sliding-window implementations (§2.6)
- **AWS Builders' Library — "Using load shedding to avoid overload"** — the backpressure/overload companion to scaling
- **Little's Law + queueing-theory primers** — the math behind capacity planning (§2.8)
