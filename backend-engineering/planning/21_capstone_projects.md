# 21 — Capstone Projects: Prove It All, End to End

> Phase 7 · Scale & synthesis · Builds on: literally everything (01–20)
> This is where the whole course becomes a portfolio you can show and defend

---

## 1. Why this matters

You've done 20 topics of concepts, labs, and mini-projects — each one extending the todo-app or a
focused lab. A capstone is different: a **large, from-scratch (or scaled-up) system** that forces
you to combine many topics under one coherent design, make real architectural decisions, and carry
it all the way to "deployed, observable, tested, secure, and documented."

Two reasons this matters more than any single topic:
1. **Integration is the real skill.** Knowing caching (06) and events (11) and k8s (16) separately
   is not the same as making them work together correctly. The bugs live in the seams.
2. **It's your evidence.** "I understand backend" is a claim; a running, documented, load-tested,
   multi-tenant system with a design doc is proof. This is what you show in interviews and link on your CV.

Pick **one** capstone and take it all the way, or do a smaller one then a bigger one. Depth and
completion beat breadth — a finished, polished project outshines three half-built ones.

---

## 2. What "done" means for a capstone (the bar)

Every capstone must hit these — they're the synthesis of the whole course. Treat it as a checklist:

- **Designed first** (topic 20): a real design doc — requirements, estimates, API, data model, architecture, trade-offs — written before the code
- **Solid API** (topic 03): versioned, paginated, idempotent where needed, RFC-9457 errors, polished OpenAPI
- **Real data layer** (topics 04/05): proper schema + indexes, the right store(s) for each job, **multi-tenant with isolation** (a recurring course theme)
- **Auth & security** (topic 07): real authN/authZ (OIDC and/or sessions), object-level authorization, tenant isolation, secrets managed, OWASP pass
- **Async & events** (topics 08/11): background jobs with retries/DLQ, event-driven flows via outbox where state must stay consistent
- **Realtime** (topic 09) where the product calls for it, correct across multiple replicas (backplane)
- **Caching** (topic 06) with a real invalidation strategy and graceful degradation
- **Object storage** (topic 10) for files, with secure per-tenant/user access
- **Distributed-systems correctness** (topic 12): resilience patterns on every external call; saga where multi-step
- **Tested** (topic 13): integration tests on real deps (testcontainers), security regression tests, a load test with a reported knee
- **Observable** (topic 14): structured logs, RED/USE metrics, distributed tracing across async hops, SLOs + alerts
- **Containerized & deployed** (topics 15/16): hardened images, running on k8s (KIND locally, cloud-ready), autoscaling on the right signal
- **Automated delivery** (topic 17): CI/CD pipeline with scans + signing, IaC for the infra, GitOps or scripted deploy
- **Scaled & rate-limited** (topic 19): stateless + horizontally scalable, per-tenant rate limits, a validated capacity model
- **Cloud-mapped** (topic 18): runs on/deployable to AWS, with a cost estimate; local-first via the playground stack
- **Documented** (all topics): a README that lets someone run it, an architecture doc, and the per-topic decision docs you wrote along the way

> Not every project needs every feature to make product sense — but you should hit the vast majority,
> and *consciously decide and document* any you skip.

---

## 3. Capstone options (pick one; each exercises a slightly different mix)

### Option A — "Collabora": realtime collaborative workspace ⭐ (recommended — broadest coverage)
A multi-tenant Notion/Trello-style workspace: teams, projects, documents/tasks, comments, file
attachments, live collaboration, notifications.
- **Realtime** (09): live cursors/presence, collaborative edits across replicas via backplane
- **Events** (11): every change is an event (outbox) → search index, notifications, activity feed, cache invalidation
- **Search** (05): full-text search over documents/tasks (OpenSearch, kept fresh via events)
- **Files** (10): attachments in object storage, per-tenant secure access, thumbnails via a media job
- **Jobs** (08): notifications, exports (PDF/CSV report generation), thumbnail/scan pipeline
- **Auth** (07): OIDC login + org/team RBAC, strict tenant isolation (04 RLS)
- Exercises the most topics; the "if you do one, do this" choice.

### Option B — "PixelForge": async media/AI processing platform ⭐ (best for the GPU/long-job theme)
Users upload media (or prompts); a worker fleet runs heavy processing (transcode / image ops / a
real small ML inference); results delivered when ready.
- **Heavy background jobs** (08 §2.7): the full GPU/long-job pattern — 202 + job id, dedicated worker
  pool, progress, cancellation, checkpointing, results to object storage
- **Realtime** (09): live progress bars via SSE/WS
- **Files** (10): presigned multipart uploads, secure per-user results, CDN delivery with signed access
- **Events** (11): upload → pipeline stages orchestrated via events; saga for multi-step processing
- **Scaling** (19) + **k8s** (16): autoscale the worker fleet on queue depth, GPU node scheduling, scale-to-zero for cost
- Directly builds on the GPU scenario you asked about in topic 08.

### Option C — "Ledger": event-sourced fintech-style transaction system (best for correctness/consistency)
Accounts, transfers, balances, a full audit trail — where **correctness under concurrency** is the point.
- **Data & transactions** (04): isolation levels, locking, the money-must-be-right constraints
- **Event sourcing + CQRS** (11): the ledger IS the event log; read models projected from it
- **Idempotency** (03/08): idempotent transfers, exactly-once effects, saga for multi-account transfers (12)
- **Auth & security** (07): strong auth, authorization, audit (who did what), tenant isolation
- **Testing** (13): property-based tests for invariants (balances never negative, sum conserved), heavy concurrency tests
- Fewer bells, but the deepest distributed-correctness workout.

### Option D — "Pulse": multi-tenant SaaS analytics/metrics platform (best for data volume + streaming)
Ingest high-volume events from tenants, process/aggregate, serve dashboards with per-tenant isolation.
- **Streaming** (11): high-throughput ingestion via Kafka/Redpanda, stream aggregation
- **Data modeling** (05): time-series storage, the right stores for ingest vs query
- **Scaling** (19): the write-scaling problem, partitioning/sharding, rate limiting per tenant, capacity planning
- **Caching** (06): dashboard query caching; **multi-tenancy** (04) front and center
- **Observability** (14): you're basically building a mini version of your own observability stack — very meta, very instructive.

---

## 4. How to run a capstone (the process)

Do it like a real project, not a tutorial:

1. **Design phase** (topic 20): write the design doc first. Requirements, estimates, API, data model,
   architecture diagram, trade-offs. Get it coherent on paper before coding.
2. **Walking skeleton**: the thinnest end-to-end slice — one request path from client → API → DB →
   response, containerized and deployed to KIND with CI green from day one. Deploy early, deploy often.
3. **Vertical slices**: build feature by feature, each fully done (API + data + tests + observability +
   deployed) before the next. Resist building all the models then all the endpoints — go vertical.
4. **Layer in the cross-cutting concerns** as you go, not at the end: auth, tenancy, caching, events,
   resilience, metrics — retrofitting these hurts (you learned why in each topic).
5. **Harden**: load test (13/19), find and fix bottlenecks with evidence, security pass (07), chaos
   drill (12), SLOs + alerts (14).
6. **Document**: the README (how to run), the architecture doc, and the decision docs. Record a short
   demo/walkthrough. Write a "what I'd do differently / what's next" section — senior self-awareness.
7. **Retrospective**: for each of the 20 topics, note where it shows up in the capstone. Gaps you
   notice are your next study targets — the loop closes.

---

## 5. The playground stack, fully assembled

By now the `labs/playground/` compose has grown across the whole course. Your capstone runs on the
full local stack — a mini production environment on your laptop:

| Layer | Local service | Topic |
|---|---|---|
| Database | Postgres + PgBouncer | 04 |
| Cache / backplane | Redis | 06/09 |
| Document/KV/search | MongoDB / DynamoDB-local / OpenSearch | 05 |
| Object storage | MinIO | 10 |
| Identity | Keycloak | 07 |
| Queue | RabbitMQ / ElasticMQ | 08 |
| Event log | Redpanda + Console | 11 |
| Observability | Prometheus + Grafana + Loki + Jaeger | 14 |
| Cloud emulation | LocalStack + Mailpit | 18 |
| Orchestration | KIND (from `k8s/`) | 16 |

The same stack maps 1:1 to AWS (topic 18's consolidated table) — so "runs locally" and "deployable
to the cloud" are the same architecture, just a config/provider swap.

---

## 6. Self-check — you're done when you can…

1. Run the whole thing from a clean machine with the documented steps, and it works.
2. Hand someone your design doc and have them understand the system without reading code.
3. Point at any component and explain what it does, why it's there, what it'd do under 100× load, and how it fails.
4. Show integration tests on real dependencies, security regression tests, and a load-test report with a knee.
5. Open a Grafana dashboard and a distributed trace that spans an async hop, live.
6. Kill any single component (a replica, the cache, a worker, the event bus) and show graceful degradation + recovery.
7. Show the CI/CD pipeline building, scanning, signing, and deploying; and the IaC that defines the infra.
8. Prove multi-tenant isolation with an attacker script that fails at every layer.
9. Produce a cost estimate for running it on AWS and name the big cost drivers.
10. Give a 10-minute walkthrough that ties the system back to the concepts — and a short list of what you'd improve next.

---

## 7. After the capstone — you are here

If you've done the 20 topics with their labs and shipped one capstone to this bar, you can:
- Design, build, deploy, scale, secure, observe, and operate a real backend system — and defend every decision
- Hold your own in system-design and deep-dive interviews across the whole stack
- Learn any specific new tool fast, because you understand the category it belongs to

**Where to go deeper next** (optional specializations, each its own journey):
- **Platform/infra/SRE**: deeper k8s, service mesh, multi-cluster, chaos engineering, cost engineering
- **Data engineering**: batch/stream processing at scale, data lakes/warehouses, Spark/Flink, dbt
- **ML/AI backends**: model serving, vector databases, RAG systems, GPU orchestration, inference optimization
- **Distributed systems research**: consensus internals, formal methods (TLA+), building databases/queues from scratch
- **Security engineering**: deeper appsec, cloud security, threat modeling, detection engineering
- **Language breadth**: pick up Go or Rust for systems-level backend work — the concepts all transfer

Update `planning/00_index.md`'s progress tracker, keep the decision docs, and reuse this playground
stack for whatever you build next. The plan doesn't expire — come back to any topic anytime.

---

## 8. Resources

- Everything from topics 01–20 — a capstone is the application, not new material
- **"The Twelve-Factor App"** (revisit) — the operational checklist your capstone should satisfy
- **Real engineering blogs** (Discord/Figma/Stripe/Uber/Netflix) — for architecture inspiration on your chosen option
- **Your own decision docs** (`*.md` from every mini-project) — the record of what you learned; the capstone is where they converge
- **Designing Data-Intensive Applications** — the one book to keep on the desk through the whole build
