# Backend Engineering — Learning Plan Index

A phase-based (not time-based) roadmap to go from "knows FastAPI" to "confident backend engineer".
Work through it at your own pace. Depth matters more than speed.

---

## How this system works

Everything lives under `backend-engineering/` — three folders, always matching by number:

```
backend-engineering/
  planning/   ← you are here. The syllabus: WHAT to learn, labs to build, checklists.
  notes/      ← created topic-by-topic WHILE studying. The actual deep-dive notes.
  labs/       ← runnable code + docker-compose files per topic.
```

Example flow for one topic:

1. Open `planning/09_realtime.md`
2. Study the concepts, write your own notes into `notes/09_realtime/`
3. Build the labs + mini-project into `labs/09_realtime/` (or extend `todo-app`)
4. Pass the self-check at the bottom of the planning file
5. Tick it off in the progress tracker below, move on

> Notes written while doing the labs stick. Don't just read — build everything.

---

## Every planning file follows the same template

| Section | What it gives you |
|---|---|
| 1. Why this matters | Where the topic sits in a real production system |
| 2. Concepts in depth | Full subtopic breakdown — the theory to master |
| 3. Hands-on labs | Runnable docker-compose based exercises |
| 4. AWS mapping | The managed equivalent + how it differs from local |
| 5. Mini-project | Usually extends the todo-app so learning compounds |
| 6. Self-check | "You're done when you can..." list |
| 7. Resources | Few, high-quality links — not link dumps |

---

## Phase map

Ordered by dependency. Go in order the first time; dip back in anytime after.

### Phase 1 — Foundations (how the machine actually works)

| # | File | One-liner |
|---|---|---|
| 01 | [01_internet_and_http.md](01_internet_and_http.md) | TCP/IP, DNS, TLS, HTTP/1.1→3, life of a request, proxies & load balancers |
| 02 | [02_python_concurrency_and_async.md](02_python_concurrency_and_async.md) | GIL, threads vs processes vs asyncio, event loop, uvicorn/gunicorn worker models |
| 03 | [03_api_design.md](03_api_design.md) | REST done properly, pagination, idempotency, error contracts, gRPC, GraphQL, webhooks |

### Phase 2 — Data layer

| # | File | One-liner |
|---|---|---|
| 04 | [04_postgres_deep_dive.md](04_postgres_deep_dive.md) | Indexes, EXPLAIN, transactions & isolation, locking, PgBouncer, partitioning, replication |
| 05 | [05_nosql_and_data_modeling.md](05_nosql_and_data_modeling.md) | Modeling tradeoffs, Redis structures, MongoDB, DynamoDB, OpenSearch — when to use what |
| 06 | [06_caching.md](06_caching.md) | Redis cache patterns, invalidation, stampede, HTTP caching/ETags, CDNs |

### Phase 3 — Core application concerns

| # | File | One-liner |
|---|---|---|
| 07 | [07_auth_and_security.md](07_auth_and_security.md) | Sessions vs JWT, OAuth2/OIDC, RBAC, OWASP Top 10, secrets · Keycloak / Cognito |
| 08 | [08_background_jobs_and_scheduling.md](08_background_jobs_and_scheduling.md) | Celery/ARQ, brokers, retries/DLQs, idempotency, cron · Redis/RabbitMQ / SQS |
| 09 | [09_realtime.md](09_realtime.md) | WebSockets, SSE, Redis pub/sub, scaling websockets, presence, push notifications |
| 10 | [10_file_storage_and_media.md](10_file_storage_and_media.md) | Object storage, presigned URLs, multipart, media pipelines · MinIO / S3 |

### Phase 4 — Distributed & event-driven

| # | File | One-liner |
|---|---|---|
| 11 | [11_event_driven_architecture.md](11_event_driven_architecture.md) | Kafka concepts, outbox pattern, event sourcing, CQRS, delivery semantics · Redpanda / MSK |
| 12 | [12_microservices_and_distributed_systems.md](12_microservices_and_distributed_systems.md) | Service boundaries, gateways, sagas, CAP, distributed locks, circuit breakers |

### Phase 5 — Quality & operations

| # | File | One-liner |
|---|---|---|
| 13 | [13_testing_strategy.md](13_testing_strategy.md) | pytest depth, testcontainers, integration/e2e, contract tests, k6/Locust load testing |
| 14 | [14_observability.md](14_observability.md) | Structured logging, metrics, OpenTelemetry tracing, alerting, SLOs · Grafana stack / CloudWatch |

### Phase 6 — Infrastructure & delivery

| # | File | One-liner |
|---|---|---|
| 15 | [15_docker_deep_dive.md](15_docker_deep_dive.md) | Image layers & internals, multi-stage builds, networking, security scanning, registries |
| 16 | [16_kubernetes.md](16_kubernetes.md) | Workloads, ingress, probes, HPA, StatefulSets, Helm/Kustomize, operators · KIND / EKS |
| 17 | [17_cicd_and_iac.md](17_cicd_and_iac.md) | GitHub Actions, blue/green & canary deploys, Terraform, GitOps with ArgoCD |
| 18 | [18_aws_for_backend.md](18_aws_for_backend.md) | IAM, VPC, EC2 vs ECS vs EKS vs Lambda, RDS, SQS/SNS, cost awareness · LocalStack labs |

### Phase 7 — Scale & synthesis

| # | File | One-liner |
|---|---|---|
| 19 | [19_performance_and_scalability.md](19_performance_and_scalability.md) | Profiling, load balancing, read replicas, sharding, rate limiting, capacity planning |
| 20 | [20_system_design_practice.md](20_system_design_practice.md) | A repeatable design method + classic problems mapped back to phases 1–6 |
| 21 | [21_capstone_projects.md](21_capstone_projects.md) | 2–3 large projects combining everything, deployed on k8s with full observability |

---

## Progress tracker

Tick these off only after passing the topic's self-check.

- [ ] 01 — Internet & HTTP
- [ ] 02 — Python concurrency & async
- [ ] 03 — API design
- [ ] 04 — Postgres deep dive
- [ ] 05 — NoSQL & data modeling
- [ ] 06 — Caching
- [ ] 07 — Auth & security
- [ ] 08 — Background jobs & scheduling
- [ ] 09 — Realtime
- [ ] 10 — File storage & media
- [ ] 11 — Event-driven architecture
- [ ] 12 — Microservices & distributed systems
- [ ] 13 — Testing strategy
- [ ] 14 — Observability
- [ ] 15 — Docker deep dive
- [ ] 16 — Kubernetes
- [ ] 17 — CI/CD & IaC
- [ ] 18 — AWS for backend
- [ ] 19 — Performance & scalability
- [ ] 20 — System design practice
- [ ] 21 — Capstone projects

---

## The playground stack

One `docker-compose.yml` (will live in `labs/playground/`) that **grows as you progress**.
Each topic adds its service; by the end you have a mini production environment on your laptop:

| Added in topic | Service(s) |
|---|---|
| 04 | Postgres (+ PgBouncer) |
| 05 | MongoDB, DynamoDB Local, OpenSearch |
| 06 | Redis |
| 07 | Keycloak |
| 08 | RabbitMQ, ElasticMQ |
| 09 | (reuses Redis pub/sub) |
| 10 | MinIO |
| 11 | Redpanda (+ Redpanda Console) |
| 14 | Prometheus, Grafana, Loki, Jaeger |
| 18 | LocalStack, Mailpit |

---

## Local ↔ AWS mapping (reference)

Everything is learned locally with Docker first; AWS is the "managed equivalent" layer on top.

| AWS service | Local equivalent | Learned in |
|---|---|---|
| S3 | MinIO | 10 |
| MSK / Kinesis (Kafka) | Redpanda | 11 |
| SQS | ElasticMQ / LocalStack | 08 |
| SNS, Lambda, DynamoDB | LocalStack / DynamoDB Local | 05, 18 |
| Cognito | Keycloak | 07 |
| CloudWatch / X-Ray | Prometheus + Grafana + Loki + Jaeger | 14 |
| RDS Postgres | postgres container | 04 |
| ElastiCache | redis container | 06 |
| OpenSearch Service | opensearch container | 05 |
| SES | Mailpit | 08, 18 |
| EKS | KIND (already set up in `k8s/`) | 16 |
| ECR | local registry container | 15 |

---

## Guiding principles

1. **Build > read.** Every topic has labs. If you only read, you didn't do the topic.
2. **Depth over coverage.** Better to truly understand isolation levels than to "finish" three topics.
3. **Everything compounds.** Mini-projects extend the todo-app; the playground stack grows; capstones reuse it all.
4. **Local first, cloud second.** Understand the open-source thing before the AWS wrapper around it.
5. **No calendar.** Phases, not weeks. Life happens; the plan doesn't expire.
6. **Self-checks are the gate.** Explaining out loud (or in notes) is the test of understanding.
