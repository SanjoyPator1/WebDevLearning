# 20 — System Design Practice: Putting It All Together on a Whiteboard

> Phase 7 · Scale & synthesis · Builds on: ALL of 01–19 — this topic is the synthesis exercise
> No new tools — this is a thinking-and-communicating topic

---

## 1. Why this matters

System design is where everything you've learned gets used *together*, under the constraint of a
blank whiteboard and a vague requirement. It's also the interview that gates senior/staff backend
roles — not because interviewers love trivia, but because "design a system that does X for Y users"
genuinely tests whether you can reason about trade-offs across all 19 previous topics at once.

This topic is deliberately near the end: you can't design systems you don't understand, and you now
understand the pieces. The goal here is a **repeatable method** so you're never staring blankly, plus
enough worked classic problems that the patterns become instinct. Every design maps back to a topic
you've done hands-on — that's your unfair advantage over people who only memorized diagrams.

---

## 2. Concepts in depth

### 2.1 A repeatable design method ⭐ (use this every single time)
A framework so you always know the next move:

1. **Clarify requirements** (don't design yet):
   - **Functional**: what must it do? (the features)
   - **Non-functional**: scale (users, RPS, data size), latency SLO, availability target, consistency needs, read/write ratio — the numbers that decide everything
   - Explicitly scope: what's in, what's out (you can't design "all of Twitter" in 45 min)
2. **Back-of-envelope estimation**: QPS, storage/year, bandwidth, cache size — order-of-magnitude
   (topics 04/05 estimation, 19 capacity). These numbers justify every later choice.
3. **API design** (topic 03): the core endpoints/contracts — makes it concrete
4. **Data model** (topics 04/05): entities, access patterns first, then store choice(s)
5. **High-level architecture**: the boxes (clients, LB, services, stores, queues) and data flow — start simple, one line per box
6. **Deep-dive** the interesting parts (interviewer-led): where the hard problems are
7. **Identify & resolve bottlenecks**: scale it (topic 19), add caching (06), async (08), replicas/shards — driven by the §1 numbers
8. **Trade-offs & wrap-up**: state what you chose, what you gave up, what you'd do with more time/scale

> The discipline that separates seniors: **drive with requirements and numbers**, not with a memorized
> diagram. Every component must earn its place from a requirement.

### 2.2 The building blocks (you've built every one — now name them fast)
A mental palette to compose from, each tagged to its topic:
- Load balancer / reverse proxy / API gateway (01, 03, 12, 18)
- Stateless app tier + horizontal scaling + autoscaling (01, 16, 19)
- Relational DB, replicas, partitioning, sharding (04, 19)
- NoSQL / KV / document / search / wide-column (05)
- Cache (client, CDN, app, DB) + invalidation (06)
- Object storage + CDN + signed access (10)
- Auth / identity / authorization (07)
- Async: queues, workers, scheduled jobs (08)
- Realtime: WS/SSE + backplane (09)
- Event log / streaming / outbox / CQRS (11)
- Service decomposition, saga, resilience patterns (12)
- Rate limiting, load shedding (19)
- Observability, SLOs (14)
- The cloud primitives they map to (18)

### 2.3 The recurring trade-offs (name them explicitly in every design)
- **Consistency vs availability vs latency** (CAP/PACELC — topic 12): pick per data flow, not globally
- **SQL vs NoSQL** (topics 04/05): access patterns and consistency decide it
- **Sync vs async** (topics 08/12): does the caller need it now?
- **Normalization vs denormalization** (topic 05): read speed vs write complexity
- **Push vs pull** (topics 09/11): realtime delivery, feed generation, cache refresh
- **Monolith vs services** (topic 12): don't split without a reason
- **Strong vs eventual consistency** with a concrete user-facing example each time
- **Cost vs performance vs complexity** (topics 18/19): the cheapest thing that meets the SLO
- **Build vs buy/managed** (topic 18)
- The senior move: there's no "right" answer — there's a defended answer with acknowledged downsides

### 2.4 Cross-cutting concerns to always address
- **Scale**: where's the bottleneck as it grows 10×/100×? (topic 19)
- **Reliability**: what happens when each component fails? single points of failure? (topic 12)
- **Consistency**: what does a user observe under lag/partition? (topics 04/12)
- **Security**: authN/authZ, tenant isolation, data protection (topics 07/10)
- **Observability**: how would you know it's broken? (topic 14)
- **Cost**: the rough bill and the big cost drivers (topic 18)
- **Multi-tenancy** where relevant (topics 04/10) — a theme through the whole course

### 2.5 Estimation fluency (drill until automatic)
- Powers of two & latency numbers every engineer should know (memory ns, SSD µs, network ms, cross-region — topic 01)
- QPS from DAU (daily actives → requests/day → average & peak QPS); the peak-to-average ratio
- Storage sizing (rows × size × retention × replication — topics 04/05)
- Bandwidth, cache working-set sizing (topic 06), connection counts (topic 04)
- The point: numbers turn hand-waving into engineering — practice them cold

### 2.6 Communication & the interview meta
- Think out loud; drive the conversation; manage the clock (don't rat-hole)
- Start simple, then scale — don't over-engineer the v1 (the topic 12 "modular monolith first" instinct)
- State assumptions explicitly; ask before diving; handle "now 100× the traffic" curveballs gracefully
- Draw clearly (boxes + arrows + the data flow); label the data on each arrow
- Know your depth: when the interviewer probes a component, go as deep as the hands-on labs took you (your edge)
- Read levels: a junior lists components; a senior justifies each from requirements and names the trade-offs

### 2.7 Classic problems to work through (each = a synthesis of specific topics)
Work each with the §2.1 method. Listed with the topics they exercise:
- **URL shortener** — hashing, KV store, cache, read-heavy scaling, analytics (03/05/06/19)
- **Rate limiter (as a service)** — algorithms, distributed Redis state, edge placement (06/19)
- **News feed / timeline** — fan-out on write vs read, push/pull, cache, ranking (05/06/09/11/19)
- **Chat / messaging** — WebSockets + backplane, presence, delivery/ordering, history (09/11)
- **Notification system** — multi-channel fan-out, queues, dedup, preferences, push (08/09/11)
- **Realtime collaborative editing** — WS, conflict resolution (OT/CRDT awareness), presence (09/12)
- **Job scheduler / task queue** — queues, workers, retries/DLQ, distributed cron, idempotency (08/12)
- **Ride-hailing / geo-proximity** — geospatial indexing, realtime location, matching (05/09)
- **Video/media platform** — object storage, transcoding pipeline, CDN, signed access (08/10)
- **E-commerce checkout** — inventory consistency, saga, idempotent payments, hot keys (03/04/11/12)
- **Search autocomplete / typeahead** — tries, ranking, caching, low latency (05/06)
- **Distributed metrics/logging system** — ingestion, time-series, sampling, retention (11/14)
- **Multi-tenant SaaS control plane** — tenancy models, isolation, per-tenant limits & cost (04/07/10/19)

### 2.8 Deepening: read how real systems are built
- Read a few canonical designs (below) and, for each, map every component to a topic you did — this converts "I studied it" into "I can design it"
- Practice explaining YOUR todo-app platform (topics 1–19) as a system design — you built it, so you can defend every box; it's your best rehearsal

---

## 3. Hands-on practice (this topic's "labs" are designs + writeups)

> Write-ups go in `labs/20_system_design_practice/` — one markdown per problem, with a diagram.

**Drill 1 — Estimation reps.**
Ten estimation questions cold (QPS for a 50M-DAU app, storage for 5 years of X, cache size for Y).
Time-box each to 3 minutes. Build the muscle before the designs.

**Drill 2 — Design your own system, formally.**
Write up your todo-app platform (everything from topics 1–19) using the §2.1 method as if it were an
interview answer — requirements, estimates, API, data model, architecture, bottlenecks, trade-offs.
This is the highest-leverage exercise: you have hands-on depth on every component.

**Drill 3–8 — Six classic problems (§2.7).**
Pick six spanning different topic-clusters (e.g., URL shortener, news feed, chat, notification system,
video platform, multi-tenant SaaS). For each, produce a design doc with the 8-step method, a diagram,
explicit numbers, and a trade-offs section. For each component, cite the topic that taught you it.

**Drill 9 — The 100× curveball.**
Take two of your Drill 3–8 designs and re-do the "now scale it 100×" step in depth: where does it
break first, and what's the next scaling move (topic 19's ladder)?

**Drill 10 — Explain it out loud.**
Present two designs verbally (record yourself or a rubber duck / a peer). Practice driving the clock,
thinking aloud, and handling probes. The communication is half the skill.

**Drill 11 — Critique real architectures.**
Read two entries from the resources below; write a one-page "what they chose and why, and what I'd
ask them" — mapping each decision to the trade-offs in §2.3.

## 4. AWS / real-world mapping

Not a service topic, but every design should be able to name the managed realization (topic 18):
"stateless app tier → ECS/EKS; queue → SQS; log → MSK/Kinesis; cache → ElastiCache; object store →
S3+CloudFront; DB → RDS/Aurora + replicas/DynamoDB; auth → Cognito; observability → CloudWatch/X-Ray."
Being able to go from whiteboard boxes to concrete services (and their costs) is a senior signal.

---

## 5. Milestone — "A system design portfolio"

In `labs/20_system_design_practice/`, assemble:

1. An estimation cheat-sheet (latency numbers, QPS/storage formulas) you can reproduce from memory
2. Your todo-app platform written up as a formal system design (Drill 2)
3. Six classic-problem design docs (Drill 3–8), each with diagram, numbers, trade-offs, and topic citations
4. Two "100× scaling" deep-dives (Drill 9)
5. Two critiques of real-world architectures (Drill 11)
6. **`METHOD.md`**: your personalized version of the §2.1 framework and the §2.3 trade-off checklist —
   the one page you'd review before any design interview

Done = handed any "design X for Y users", you can drive a clear, numbers-justified design in 45 minutes and defend every trade-off — because you've built the pieces.

---

## 6. Self-check — you're done when you can…

1. Run the 8-step method from memory on a problem you've never seen, without freezing.
2. Do QPS and storage estimation cold, with the peak-to-average reasoning.
3. Design the API and data model for a new problem, choosing stores from access patterns.
4. Name the recurring trade-offs (§2.3) and apply the right ones to a given design, with downsides stated.
5. Take any design to "now 100×" and articulate the next scaling move and where it breaks.
6. Address all cross-cutting concerns (scale/reliability/consistency/security/observability/cost) unprompted.
7. For every box you draw, cite how you'd actually build it (a topic you did hands-on) and its managed AWS form.
8. Handle an interviewer probe by going genuinely deep on a component (not hand-waving).
9. Explain your own todo-app platform as a rigorous system design.
10. Communicate clearly under a clock: assumptions, out-loud reasoning, clean diagram, crisp trade-offs.

---

## 7. Resources

- **"System Design Interview" Vol 1 & 2 — Alex Xu** — the standard problem walkthroughs; do them WITH the §2.1 method
- **ByteByteGo (Alex Xu) newsletter/site** — visual system breakdowns
- **"Grokking the System Design Interview" (DesignGurus)** — structured problem set
- **The System Design Primer (github.com/donnemartin/system-design-primer)** — free, comprehensive, includes the estimation numbers
- **Designing Data-Intensive Applications — Kleppmann** — still the deepest "why" behind every design decision; you've cited it all course, now it's the capstone reference
- **Real engineering blogs**: Discord, Figma, Stripe, Uber, Netflix, Cloudflare, Dropbox — read how production systems are actually built
- **"Latency numbers every programmer should know"** (Jeff Dean / interactive versions) — memorize the orders of magnitude
