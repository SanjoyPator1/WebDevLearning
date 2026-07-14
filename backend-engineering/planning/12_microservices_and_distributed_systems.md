# 12 — Microservices & Distributed Systems: When One Process Isn't Enough

> Phase 4 · Distributed & event-driven · Builds on: 01 (network), 03 (APIs/gRPC), 04 (locks/tenancy), 08 (queues), 11 (events)
> Playground: introduces a **second service** alongside the todo-app

---

## 1. Why this matters

Everything before this assumed one deployable service. The moment you split into multiple
services — or even just run multiple replicas of one — you inherit the **eight fallacies of
distributed computing**: the network is unreliable, latency isn't zero, calls fail halfway, and
"did that write succeed?" becomes genuinely unanswerable. Most production outages are distributed-
systems problems wearing a microservices costume.

This topic is two things at once: the *architecture* decision (should you even split? where are the
boundaries?) and the *distributed-systems fundamentals* (consistency, consensus, resilience) that
you need **even in a monolith with replicas**. The fundamentals matter more than the buzzword.

---

## 2. Concepts in depth

### 2.1 Monolith vs microservices — the honest version
- Start with the monolith. Why "microservices by default" is how startups die (ops overhead, distributed debugging, no product yet)
- The **modular monolith** — clean module boundaries in one deployable; get 80% of the benefit first
- What actually justifies a split: independent scaling (your GPU workers from topic 08!), independent deploy cadence, team autonomy (Conway's Law), fault isolation, polyglot needs
- The costs you take on: network in place of function calls, distributed transactions, eventual consistency, operational surface, testing complexity
- Distributed monolith = the worst of both (services that must deploy together) — how to avoid it

### 2.2 Finding service boundaries
- Domain-Driven Design essentials: bounded contexts, aggregates, ubiquitous language — the sane way to draw lines
- Boundaries follow business capabilities, not technical layers ("orders" not "the database service")
- Data ownership: **each service owns its data**; no shared database (contrast topic 04's shared-DB — that's a monolith pattern); the anti-pattern of the shared DB between services
- How services get each other's data without a shared DB: API calls, or (better) events + local read replicas (topic 11)

### 2.3 Inter-service communication
- **Sync** (request/response): REST (topic 03), gRPC (topic 03 — usually the internal choice); pros: simple, immediate; cons: temporal coupling, cascading failures
- **Async** (messaging/events): queues (topic 08), event log (topic 11); pros: decoupling, resilience; cons: eventual consistency, harder debugging
- Choosing per interaction: "does the caller need an answer now?" (echoes topic 08's decision tree)
- **Service discovery**: how service A finds service B — DNS (topic 01!), client-side vs server-side discovery, service registries; in k8s it's just Service DNS (topic 16)
- **API gateway**: single entry point — routing, auth offload (topic 07), rate limiting (topic 19), aggregation; gateway vs BFF (backend-for-frontend, topic 03 GraphQL)

### 2.4 Distributed data & consistency ⭐ (the intellectual core)
- **CAP theorem, correctly**: during a network **partition**, choose consistency or availability — not a general "pick 2 of 3"; what CP and AP systems actually do when partitioned
- **PACELC**: the part CAP forgets — Else (no partition), trade Latency vs Consistency; the more useful framing
- **Consistency models spectrum**: strong / linearizable → sequential → causal → **eventual** — with a real example of each and what a user observes
- Read-your-own-writes, monotonic reads, monotonic writes — the "session guarantees" that matter for UX (ties to topic 04 replication lag & topic 06 caching)
- **Distributed transactions**: why 2-phase commit (2PC) is avoided (blocking, coordinator failure); the modern answer → sagas
- **Saga pattern** (deep dive, promised in topic 11): a workflow as a sequence of local transactions
  + **compensating actions** for rollback. **Orchestration** (a coordinator drives) vs **choreography**
  (services react to events) — trade-offs, and when each. Worked example: create-order → reserve-stock
  → charge-card → on failure, compensate backwards.
- **Idempotency & exactly-once, again** (topics 03/08/11): the recurring primitive — at-least-once
  delivery + idempotent handlers is how sagas survive retries

### 2.5 Consensus & coordination (working knowledge)
- Why agreement is hard: no global clock, partial failure, the FLP result (awareness, not proof)
- **Raft/Paxos** — what consensus buys (a replicated, agreed-upon log) and where it's used (etcd/k8s, Kafka controller, Consul) — conceptual
- **Distributed locks / leader election**: the topic-08 distributed-cron problem, generalized. Options:
  Redis (Redlock — and the well-known debate about its safety), etcd/ZooKeeper leases, Postgres
  advisory locks (topic 04). Fencing tokens and why a naive lock isn't safe under GC pauses.
- Clocks: wall-clock vs monotonic vs **logical clocks** (Lamport, vector clocks) — why "just use timestamps to order events" is a bug; awareness level

### 2.6 Resilience patterns ⭐ (survive partial failure)
- **Timeouts** everywhere (topic 01's timeout taxonomy applied) — no unbounded waits, ever
- **Retries** with exponential backoff + **jitter** (topic 08) — and the retry-storm / cascading-failure danger of naive retries
- **Circuit breaker**: stop hammering a failing dependency; closed/open/half-open states; what to do when open (fallback, fail-fast)
- **Bulkheads**: isolate resources (separate pools/threads) so one slow dependency can't sink the whole service (ties to topic 02 threadpool, topic 04 connection pools)
- **Fallbacks & graceful degradation**: cached/stale response (topic 06), default value, reduced feature — decide per dependency
- **Load shedding & backpressure** (topic 08): reject early when overloaded rather than collapse
- **Rate limiting** between services (topic 19)
- **The failure that teaches it all**: the cascading failure / retry storm — one slow service → callers pile up → thread/conn exhaustion → callers' callers fail. How each pattern above breaks the chain.

### 2.7 Observability across services (sets up topic 14)
- Why single-service logs are useless here: one user request fans out across N services
- **Distributed tracing** (topic 14): trace id + span ids propagated across every hop (sync and async!) — the only way to debug "where did the 3 seconds go?"
- Correlation ids from topic 03 threaded through everything, including events (topic 11) and jobs (topic 08)

### 2.8 Service mesh & platform concerns (awareness)
- What a service mesh (Istio/Linkerd) offloads from your code: mTLS (topic 07), retries/timeouts/circuit-breaking, traffic shifting, telemetry — sidecar model
- The trade: less code, more platform complexity; when a mesh is worth it (many services) vs overkill
- Ties forward to topic 16 (k8s) where the mesh actually lives

### 2.9 Testing distributed systems (sets up topic 13)
- Contract testing (topic 03) so services can deploy independently without integration-testing the world
- Fault injection / chaos engineering: deliberately kill dependencies, add latency, partition the network — verify your resilience patterns actually work
- The test pyramid shifts: more contract + component tests, fewer full-system e2e (topic 13)

---

## 3. Hands-on labs

> Code in `labs/12_microservices_and_distributed_systems/`. Extract ONE service from the todo-app (e.g., a **notifications service**) to make things concrete — don't over-split.

**Lab 1 — Extract a service (and feel the cost).**
Pull notifications out of the todo-app into its own FastAPI service with its own database.
The todo-app talks to it two ways: once via sync gRPC/REST, once via events (topic 11). Write down
everything that got harder (deploy, local dev, debugging, a new failure mode).

**Lab 2 — Make a sync call fail, then survive it.**
Call the notifications service synchronously. Kill it. Watch the todo-app hang/error. Now add:
timeout → retry-with-jitter → circuit breaker → fallback (queue the notification for later). Prove
the todo-app stays healthy with the dependency dead.

**Lab 3 — Cause a cascading failure, then stop it.**
Add artificial latency to the notifications service under load. Watch the todo-app's connection/
thread pool (topics 02/04) exhaust and its OWN unrelated endpoints start failing. Fix with
bulkheads (isolated pool + circuit breaker + timeout). Re-run; unrelated endpoints stay up.

**Lab 4 — Implement a Saga.**
A multi-step workflow across the two services (e.g., "complete todo" → "award points" → "send
badge notification") where step 2 can fail. Implement it as a **choreographed saga** over events
(topic 11) with compensating actions. Then discuss what an orchestrated version would look like.
Kill a service mid-saga and prove the system reaches a consistent state (forward or compensated).

**Lab 5 — Observe eventual consistency.**
With the event-driven path, deliberately measure the window where the todo-app says "done" but the
notifications service hasn't caught up. Add a read-your-own-writes guarantee where the UX needs it.

**Lab 6 — Distributed lock done right.**
Two replicas of a worker both try to run a "daily rollup". Coordinate with a distributed lock
(Postgres advisory lock and/or etcd/Redis). Explore the failure case: lock holder pauses (simulate
GC), lock expires, second holder starts — introduce a fencing token to make it safe.

**Lab 7 — Distributed tracing across the hop.**
Propagate a trace id from the todo-app through the sync call AND through the event to the
notifications service. View one trace spanning both services (sets up topic 14's OpenTelemetry lab).

**Lab 8 — Chaos drill.**
Script fault injection: randomly kill the dependency, add latency, drop events. Verify your
resilience patterns from Labs 2–4 hold. Write a short chaos report.

---

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| Service discovery | **Cloud Map** / ECS Service Connect / EKS DNS | DNS-based discovery (topic 01) |
| API gateway | **API Gateway** / ALB / App Mesh ingress | Edge routing + auth + throttling |
| Service mesh | **App Mesh** / Istio on EKS | mTLS, retries, traffic shifting |
| Saga orchestration | **Step Functions** | Managed workflow orchestrator with compensation |
| Distributed lock/coordination | DynamoDB conditional writes / etcd on EKS | Locks via conditional put + TTL |
| Async between services | **SQS / SNS / EventBridge / MSK** (topics 08, 11) | The decoupling layer |
| Tracing across services | **X-Ray** / OTel → managed backends | Topic 14 |
| Config/secrets across services | **AppConfig / Parameter Store / Secrets Manager** | Topic 07 |

---

## 5. Mini-project — "Two-service, resilient, traceable system"

In `labs/12_microservices_and_distributed_systems/`:

1. todo-app + a separate notifications service, each owning its data, communicating both sync (gRPC) and async (events, topic 11)
2. Every sync call wrapped in the full resilience stack: timeout, retry+jitter, circuit breaker, bulkhead, fallback
3. One saga (with compensation) spanning both services, provably consistent after a mid-flight crash
4. Distributed lock (with fencing) guarding a scheduled cross-service job
5. Trace ids propagated across sync + async hops; one end-to-end trace viewable (feeds topic 14)
6. A chaos script that injects failures in CI-style, plus a `RESILIENCE.md` documenting every failure
   mode, the pattern that handles it, and the CAP/consistency choice made for each data flow

Done = you can kill either service, add latency, or partition the event bus, and the system degrades predictably and recovers to a consistent state — and you can prove it with a trace.

---

## 6. Self-check — you're done when you can…

1. Argue for a modular monolith over microservices for a young product, and list what would later justify splitting.
2. Draw service boundaries for a domain using bounded contexts, and explain why services don't share a database.
3. State CAP correctly (it's about partitions) and explain PACELC's addition.
4. Place strong/causal/eventual consistency on a spectrum with a user-observable example of each.
5. Explain why 2PC is avoided and walk a saga (orchestration vs choreography) with compensation for a 3-step workflow.
6. Explain a cascading failure end to end and how timeout + retry-jitter + circuit breaker + bulkhead each break the chain.
7. Explain why naive distributed locks are unsafe and what a fencing token fixes.
8. Explain why logical clocks exist and why ordering distributed events by wall-clock timestamp is buggy.
9. Explain what distributed tracing propagates and why it's mandatory across async hops.
10. Explain what a service mesh offloads and when it's worth the complexity.

---

## 7. Resources

- **Designing Data-Intensive Applications, ch. 5–9** — replication, partitioning, transactions, consistency, consensus: THE text for §2.4–2.5
- **microservices.io** (Chris Richardson) — pattern catalog: decomposition, saga, API gateway, service discovery
- **"Building Microservices" — Sam Newman (2nd ed.)** — the pragmatic architecture book; boundaries & communication
- **release-it! — Michael Nygard** — the resilience-patterns bible (circuit breaker, bulkhead originate here)
- **AWS Builders' Library** — "Timeouts, retries, and backoff with jitter", "Avoiding fallback in distributed systems" — short, canonical, production-grade
- **Marc Brooker's blog + Kyle Kingsbury's "Jepsen" analyses** — how distributed systems actually break; sobering and excellent
- **Martin Kleppmann — "How to do distributed locking"** — the Redlock debate and fencing tokens (Lab 6)
