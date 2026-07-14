# 08 — Background Jobs & Scheduling: Work That Outlives the Request

> Phase 3 · Core application concerns · Builds on: 02 (concurrency), 04 (SKIP LOCKED queue), 03 (idempotency)
> Playground: adds **rabbitmq, elasticmq** (and reuses redis)

---

## 1. Why this matters

An HTTP request should return in milliseconds. But real apps must do slow things: send email,
process an uploaded video, run a GPU inference, generate a report, call a flaky third party.
If you do that work *in the request*, you hold a worker hostage (topic 02's threadpool
ceiling), time out the client, and can't retry cleanly.

The universal answer: **move the work off the request path** onto a separate process/fleet that
consumes from a queue. This topic covers the whole spectrum — from "no library, just don't block
the loop" up to a production worker fleet with retries, dead-letter queues, idempotency,
backpressure, and progress reporting — with your GPU-inference scenario as a running example.

---

## 2. Concepts in depth

### 2.1 The core idea & vocabulary
- Producer → **broker/queue** → consumer/worker; why the queue decouples them (independent scaling, buffering, retries)
- Task vs job vs message; enqueue, ack/nack, visibility timeout, prefetch, concurrency
- Sync vs async vs deferred work — a decision tree: does the caller need the result now? can it wait? can it be told later (webhook/poll)?
- Why "just use a thread" fails in production: no durability (process restart loses it), no retry, no backpressure, no visibility, shares the machine with your API

### 2.2 The spectrum of "run it in the background" — from simplest to production ⭐
Walk the full ladder; know the ceiling of each rung:

1. **FastAPI `BackgroundTasks`** — runs *after response* but **in the same process/event loop**.
   Fine for: fire-and-forget, fast, non-critical (send one email). Ceiling: no durability (dies with
   the process), no retries, still competes with your API for CPU/threads — **never** for GPU/long/critical work.
2. **`asyncio.create_task` / a background coroutine** — same process, cooperative. Same durability
   ceiling; plus the fire-and-forget dangers from topic 02 (lost reference, swallowed errors).
3. **`ProcessPoolExecutor` / `run_in_executor`** — moves CPU work off the event loop to *other
   processes on the same box* (topic 02). Better isolation, but still no durability/retry, and
   bounded by that one machine's cores/GPUs.
4. **A separate worker process on the same host** consuming a queue (Redis/DB/RabbitMQ) — now you
   have durability + retry + the API process is fully protected. This is the real dividing line.
5. **A dedicated worker fleet** on other machines (GPU boxes!), scaled independently from the API,
   pulling from a broker. This is the production target — and what k8s (16) + autoscaling (19) deploy.

> The GPU case (your example) lives at rung 4–5: the API just **enqueues** a job and returns a
> job id immediately; a separate GPU-worker process/fleet pulls the job, runs inference, writes
> the result, and reports progress. The API never touches the GPU or blocks. See §2.7.

### 2.3 Brokers & backends — the landscape
- **Redis** as broker: fast, simple, at-least-once-ish; persistence caveats (from 05) — great default for many apps
- **RabbitMQ**: real message broker — exchanges, queues, bindings, routing keys, acks, prefetch, DLX (dead-letter exchange), priority queues. The "proper" AMQP option
- **Postgres as a queue** (`FOR UPDATE SKIP LOCKED` from topic 04): no new infra, transactional with your data — underrated for moderate volume
- **Kafka/Redpanda** — a log, not a task queue; different semantics (topic 11) — know why it's usually the wrong tool for task-queue-style work
- Cloud: **SQS** (managed queue) + **ElasticMQ** (local SQS-compatible) — §4
- Choosing: volume, durability needs, ordering, existing infra, ops budget

### 2.4 Python job frameworks
- **Celery** — the incumbent: tasks, workers, broker+result backend, routing to queues, `chain`/`group`/`chord` (canvas), `acks_late`, prefetch, concurrency pools (prefork/thread/gevent). Heavy but battle-tested
- **ARQ** — async-native (asyncio), Redis-based, lightweight — pairs naturally with FastAPI
- **Dramatiq / RQ / TaskIQ / Huey** — the alternatives, one line each on where they fit
- **APScheduler** — in-process scheduling (careful: multiple replicas = duplicate runs unless coordinated)
- Recommendation for this course: build one job on raw Postgres/Redis first (to understand the mechanics), then do the real work in ARQ or Celery

### 2.5 Reliability — the hard part (this is where the topic earns its keep)
- **Delivery semantics**: at-most-once vs at-least-once vs exactly-once — and why exactly-once
  delivery is a myth; you get **at-least-once delivery + idempotent processing** = effectively-once
- **Idempotency** (from topic 03, now applied to workers): a job may run twice — design handlers so
  the second run is a no-op (idempotency key / dedup table / natural upsert)
- **Acknowledgement models**: ack-on-receive (fast, loses work on crash) vs ack-on-complete
  (`acks_late`, safe, risks duplicate on crash-after-work) — pick per task
- **Retries**: exponential backoff + jitter, max attempts, distinguishing retriable (timeout) vs
  permanent (bad input) failures — never retry a poison message forever
- **Dead-letter queue (DLQ)**: where messages go after max retries; monitoring & manual replay
- **Poison messages** and how one bad message can wedge a whole queue without a DLQ
- **Backpressure**: what happens when producers outrun consumers — queue depth as the signal,
  bounded queues, rejecting/shedding load, autoscaling workers on depth (ties to 19)
- **Visibility timeout / prefetch**: how a broker prevents two workers grabbing the same job, and
  the trap of a visibility timeout shorter than the task runtime (job runs twice)
- **Ordering**: most queues don't guarantee it; when you need it (per-key ordering) and how (partitioning — preview of 11)

### 2.6 Scheduled & periodic work
- Cron fundamentals (syntax, timezones, the DST trap)
- In-app schedulers (Celery Beat, APScheduler) vs external (k8s CronJob — topic 16, cloud EventBridge/scheduled Lambda)
- **The distributed-cron problem**: N replicas must not all fire the 2am job — leader election /
  advisory locks (Postgres advisory lock from topic 04!) / a single scheduler / distributed lock (topic 12)
- Idempotent scheduled jobs (a run might overlap the previous one — guard with locks + skip-if-running)
- Catch-up/misfire behavior after downtime — should a missed job run late or be skipped?

### 2.7 Long-running & resource-intensive jobs (the GPU pattern) ⭐
The scenario you asked about — a GPU/long inference — done production-grade:

- **Never in the request.** The endpoint validates input, creates a **job record**
  (`status=queued`, id, params) in Postgres, enqueues the job id, returns `202 Accepted` +
  the job id + a status URL. Client polls the status URL or gets a webhook/websocket on completion.
- **Dedicated worker fleet** on GPU nodes, separate from the API deployment, scaled independently
  (you don't want GPU boxes serving HTTP). Concurrency per worker = 1 (or = #GPUs) so you never
  oversubscribe the device.
- **Progress reporting**: worker updates the job record (`status=running`, `progress=42%`) and/or
  publishes progress over Redis pub/sub → WebSocket to the client (bridges to topic 09).
- **Chunking / checkpointing**: long tasks checkpoint so a crash resumes rather than restarts;
  visibility timeout must exceed the runtime, or use heartbeats to extend it.
- **Timeouts, cancellation & cleanup**: hard wall-clock cap, a way for the user to cancel
  (cooperative cancel flag the worker checks), and guaranteed GPU-memory cleanup on failure.
- **Result handling**: large outputs go to object storage (topic 10, presigned URL back to client),
  not through the queue or DB. The queue carries pointers, never payloads.
- **Resource-aware scheduling**: route GPU jobs to a GPU queue, CPU jobs to a CPU queue; different
  worker pools consume different queues (Celery routing / separate ARQ workers). Foreshadows k8s
  node selectors + resource requests (16) and queue-depth autoscaling (19).
- **Cost control**: GPU nodes are expensive → scale-to-zero when the queue is empty, batch where possible.

### 2.8 Observability & operations of a job system
- The metrics that matter: queue depth, oldest-message age, processing rate, success/failure/retry counts, p95 task duration (ties to 14)
- Correlation IDs from the request through the job (from topic 03's request IDs) — trace a job back to its trigger
- Flower (Celery) / dashboards; alerting on DLQ growth and queue-age (14)
- Testing background jobs: eager/synchronous mode in tests, fake brokers, testcontainers (topic 13)

---

## 3. Hands-on labs

> Code in `labs/08_background_jobs_and_scheduling/`. Add **rabbitmq** and **elasticmq** to the playground; reuse redis.

**Lab 1 — Climb the ladder (feel each rung's ceiling).**
Same task ("resize an image / hash slowly for 5s") implemented at rungs 1→4 of §2.2:
FastAPI `BackgroundTasks`, then a raw Postgres `SKIP LOCKED` worker (reuse topic 04 Lab 4).
For each: kill the process mid-task and observe what survives. Tabulate durability/retry/isolation.

**Lab 2 — Real worker with ARQ (or Celery).**
Move todo-app email/notification sending to ARQ workers on Redis. Enqueue from the API, process
in a separate worker container. Add retries with backoff + jitter and a max-attempts cap.

**Lab 3 — Retries, DLQ, and a poison message.**
RabbitMQ with a dead-letter exchange. Inject a message that always fails; prove it retries N
times then lands in the DLQ (not looping forever). Build a tiny "replay from DLQ" script.

**Lab 4 — Idempotent at-least-once.**
Configure `acks_late`/visibility so a crash *after* work but *before* ack causes redelivery.
Prove the job runs twice — then add an idempotency/dedup table so the effect happens once.
This is the whole "effectively-once" lesson in one lab.

**Lab 5 — The GPU/long-job pattern (the centerpiece).**
Simulate a "heavy inference" (CPU sleep + progress, or a real small model) as a dedicated worker
pool separate from the API:
- `POST /jobs` → creates job record, enqueues id, returns `202` + job id + status URL
- Worker pool (concurrency 1) pulls, runs, checkpoints, updates `progress`
- `GET /jobs/{id}` returns status/progress; result stored to MinIO (topic 10) with a presigned link
- Add cancellation (cooperative flag) and a hard timeout
- Bonus: stream progress to the browser via Redis pub/sub → WebSocket (link to topic 09)

**Lab 6 — Backpressure & autoscaling signal.**
Flood the queue faster than workers drain it. Graph queue depth and oldest-message age. Add more
workers and watch it drain. Write the scaling rule you'd use ("scale workers when oldest-age > 30s").

**Lab 7 — Distributed cron, safely.**
A "nightly cleanup" job. Run 3 scheduler replicas and prove it fires 3× (the bug). Fix with a
Postgres advisory lock (topic 04) so exactly one replica runs it. Make the job idempotent so an
overlap is harmless.

---

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| RabbitMQ / Redis broker | **SQS** (standard & FIFO) | Managed queue; visibility timeout & DLQ are first-class |
| ElasticMQ | (local SQS) | API-compatible SQS for dev/tests |
| DLQ (RabbitMQ DLX) | SQS redrive policy → DLQ | Same concept, one setting |
| Fan-out to many consumers | **SNS** (+ SQS fan-out) | Pub/sub; SNS→SQS is the standard pattern |
| Celery Beat / cron | **EventBridge Scheduler** | Managed cron → triggers Lambda/ECS/SQS |
| Worker fleet | ECS/Fargate or **EKS** workers, or **Lambda** (SQS-triggered) | Lambda auto-scales with queue; long/GPU jobs → ECS/EKS with GPU nodes |
| GPU worker pool | EKS GPU node groups / EC2 GPU / SageMaker jobs | GPU scheduling, scale-to-zero |
| Managed RabbitMQ | **Amazon MQ** | If you need AMQP specifically |

---

## 5. Mini-project — "Async job platform for todo-app"

In `labs/08_background_jobs_and_scheduling/`:

1. A generic `jobs` table + job-status API (`202` + poll/subscribe), reusable across job types
2. Email/notification jobs on ARQ/Celery with retries, backoff, and a DLQ
3. One **heavy job type** (report generation or a mock inference) using the full §2.7 pattern:
   dedicated worker pool, progress, cancellation, timeout, result to MinIO, live progress to the UI
4. A scheduled nightly job that's distributed-safe (advisory lock) and idempotent
5. Metrics endpoint / dashboard: queue depth, oldest-age, success/failure/retry counts
6. **`JOBS.md`**: the architecture, delivery-semantics choice per job type, and the failure-mode
   analysis (what happens on worker crash, broker restart, duplicate delivery, poison message)

Done = you can crash any worker mid-job and lose no work and cause no double-effect.

---

## 6. Self-check — you're done when you can…

1. Give the decision tree for sync vs background vs deferred work, with a real example of each.
2. Explain why FastAPI `BackgroundTasks` is wrong for a GPU job — name every property it lacks.
3. Walk the full GPU-job lifecycle: enqueue → 202 → worker → progress → result → client, and say where each piece of state lives.
4. Explain at-least-once + idempotent = effectively-once, and why true exactly-once delivery is impossible.
5. Explain `acks_late`/visibility timeout and the exact crash window that causes a double-run.
6. Describe a DLQ, how a poison message reaches it, and how you'd replay it.
7. Explain backpressure and which metric you'd autoscale workers on (and why not CPU).
8. Explain the distributed-cron duplicate-firing problem and two ways to solve it.
9. Explain why job results go to object storage and only pointers go through the queue.
10. Choose a broker (Redis vs RabbitMQ vs SQS vs Postgres) for three different workloads with reasons.

---

## 7. Resources

- **Celery docs — "Tasks", "Routing", "Optimizing", "acks_late & prefetch"** — even if you use ARQ, the concepts are canonical
- **ARQ docs** — async job queue that pairs with FastAPI; short and clean
- **AWS SQS Developer Guide — visibility timeout, redrive/DLQ, FIFO** — best written explanation of queue semantics anywhere
- **"What is a Dead Letter Queue" + "Idempotency" articles (AWS Builders' Library)** — production reliability patterns
- **CloudAMQP RabbitMQ guides + "RabbitMQ in Depth" (book)** — exchanges/bindings/DLX mental model
- **Brandur Leach — "Transactionally Staged Job Drains" & job-queue posts** ([brandur.org](https://brandur.org)) — Postgres-as-a-queue done right; also sets up the outbox pattern for topic 11
