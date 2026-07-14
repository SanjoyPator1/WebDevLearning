# 02 — Python Concurrency & Async: What Your Server Is Actually Doing

> Phase 1 · Foundations · Builds on: 01 (you know what a connection is)

---

## 1. Why this matters

You already write `async def` routes — but *why*? The single most common way FastAPI apps fall
over in production is someone blocking the event loop with a sync call, and nobody noticing
until traffic arrives. Worker-count tuning, "should this be async?", "why is one slow endpoint
freezing the whole service?" — all of it comes down to this topic.

This is also the topic that separates "uses FastAPI" from "understands FastAPI". Everything
here transfers: the same event-loop model powers Node.js, and the same worker-process model
powers almost every deployed Python service.

---

## 2. Concepts in depth

### 2.1 Processes vs threads — the mental model
- What a process owns (memory space, file descriptors) vs what a thread owns (stack, registers)
- Context switching cost; why "just add threads" doesn't scale to 10k connections
- Shared state: threads share memory (dangerous + convenient), processes don't (safe + expensive IPC)

### 2.2 The GIL — precisely, not folklore
- What the Global Interpreter Lock actually locks (bytecode execution, refcounts)
- Why threads still help for **I/O-bound** work: the GIL is *released* during blocking I/O
- Why threads do NOT help for **CPU-bound** work — and why multiprocessing does
- The future: free-threaded Python (PEP 703, 3.13+ `--disable-gil` builds) — know it's coming
- Rule of thumb table: CPU-bound → processes · I/O-bound many conns → asyncio · I/O-bound few → threads fine

### 2.3 Blocking vs non-blocking I/O
- What "blocking" means at the syscall level (thread parked until data arrives)
- Non-blocking sockets + an event notification mechanism (`epoll`/`kqueue`) = one thread, many sockets
- This is the entire trick behind asyncio, Node, nginx — one loop watching thousands of sockets

### 2.4 asyncio — the machinery
- Coroutines: `async def` defines one, calling it creates it, **nothing runs until awaited**
- The event loop: a scheduler that runs coroutines until they hit `await` on something pending
- `await` = "I'm waiting on I/O, run someone else" — **cooperative** scheduling, nobody preempts you
- Tasks (`asyncio.create_task`) vs bare coroutines vs Futures
- Consequence of cooperative scheduling: one CPU-heavy or sync-blocking coroutine starves EVERYONE

### 2.5 asyncio — the patterns you'll actually use
- Fan-out: `asyncio.gather` (and its `return_exceptions` trap)
- Timeouts: `asyncio.wait_for` / `asyncio.timeout` (3.11+) — every awaited network call needs one
- Concurrency limits: `asyncio.Semaphore` (e.g., "max 10 concurrent calls to that API")
- TaskGroups (3.11+) & structured concurrency — why "spawn and forget" is a bug factory
- Cancellation: what happens at the `await` point, `CancelledError`, `asyncio.shield`
- Escape hatch for blocking code: `asyncio.to_thread` / `run_in_executor`
- Async generators & `async for`; async context managers & `async with`

### 2.6 The classic pitfalls (learn to smell these in review)
- `time.sleep`, `requests`, sync DB drivers (`psycopg2`) inside `async def` → loop frozen
- CPU-heavy work (JSON of huge payloads, password hashing, image resize) inside `async def`
- `create_task` without keeping a reference → task garbage-collected mid-flight
- Swallowed exceptions in fire-and-forget tasks (nobody awaits them → nobody sees the traceback)
- Shared mutable state across coroutines — still needs care even without threads

### 2.7 Threads & processes in practice
- `concurrent.futures` — `ThreadPoolExecutor` / `ProcessPoolExecutor`; when each
- `threading.Lock` and why you need it even WITH the GIL (check-then-act races)
- `multiprocessing` gotchas: pickling, start methods (fork vs spawn), shared memory basics

### 2.8 How FastAPI actually runs your code
- `async def` route → runs **on** the event loop (must never block)
- `def` route → FastAPI runs it in a **threadpool** (anyio, default cap ~40 threads) — so sync
  routes don't block the loop, but the threadpool is a hidden concurrency ceiling
- Same rule applies to dependencies and background tasks
- Decision rule: async lib available → `async def` + await it · only sync lib → plain `def` and
  let the threadpool handle it · never mix (sync calls inside `async def`)

### 2.9 Servers & workers — from dev to production
- WSGI vs ASGI — one-request-per-worker vs event loop; why ASGI enables WebSockets/SSE
- uvicorn: the event loop host (uvloop = faster loop implementation)
- Multi-core: gunicorn (or uvicorn `--workers`) forking N worker **processes**, each with its own
  loop and its own GIL
- Sizing intuition: I/O-bound async app → ~1 worker per core; CPU work → move it out of the API
- Worker lifecycle: graceful shutdown, timeouts, max-requests recycling; where this maps to
  k8s replicas later (16) — replicas of small pods vs one pod with many workers

---

## 3. Hands-on labs

> Code goes in `labs/02_python_concurrency_and_async/`. Install `hey` or use `locust` for load.

**Lab 1 — Prove the GIL.**
A CPU-bound function (e.g., sum of squares to 10^7). Run it 4× sequentially, 4× in threads,
4× in processes. Time all three. Explain the numbers. Then repeat with an I/O-bound function
(sleep or HTTP call) and watch threads suddenly "work".

**Lab 2 — Freeze the event loop (the vaccine lab).**
FastAPI app, two endpoints: `/bad` does `time.sleep(2)` in `async def`, `/good` does
`await asyncio.sleep(2)`. Fire 20 concurrent requests at each with `hey -c 20`.
Compare total wall time. Now add `/health` and watch it die while `/bad` is under load.

**Lab 3 — `def` vs `async def` under load.**
Same 2-second wait implemented three ways: sync `def` (threadpool), `async def` + await,
`async def` + blocking call. Load test each at concurrency 10, 50, 100. Find the threadpool
ceiling. Write down the resulting decision rule in your own words.

**Lab 4 — Fan-out with control.**
Endpoint that must call three fake upstream services (250ms each, one flaky).
v1: sequential awaits. v2: `gather`. v3: `gather` + per-call `timeout` + `Semaphore(2)` +
graceful partial failure. Measure each version's latency.

**Lab 5 — The escape hatch.**
Wrap a genuinely blocking library call (e.g., `bcrypt` password hash, or PIL image resize)
with `asyncio.to_thread` and prove — under load — that the loop stays responsive.

**Lab 6 — Worker models.**
CPU endpoint (hash 100k iterations). Run uvicorn with 1 worker, then `--workers 4`.
Load test; watch CPU cores with `htop`. Then kill a worker mid-load and observe recovery.
Bonus: same test inside Docker with `cpus: 1.0` limit — see topic 15/16 foreshadowed.

---

## 4. AWS mapping

Lighter here — this topic is mostly cloud-agnostic, but the concepts map:

| Local concept | AWS parallel |
|---|---|
| Worker processes per machine | ECS/Fargate task sizing (vCPU) × container count |
| "How many workers?" | Lambda sidesteps it: 1 request per execution environment, scaling = more environments |
| Blocking the loop | Lambda: blocking just bills you longer; containers: same failure you saw in Lab 2 |
| CPU work doesn't belong in the API | Offload to SQS + worker (topic 08) — the cloud version of `to_thread` |

---

## 5. Mini-project — "The benchmark report"

In `labs/02_python_concurrency_and_async/benchmark/`: extend the todo-app with three endpoints —
`/io-async` (async DB/HTTP call), `/io-sync` (same via blocking client), `/cpu` (real hashing).

Produce a short `RESULTS.md`: a table of throughput + p95 latency for each endpoint across
configs (1 vs 4 workers · concurrency 10/50/200), plus **one paragraph per row explaining WHY**.
The explanation is the deliverable — numbers without the why don't count.

---

## 6. Self-check — you're done when you can…

1. Explain what the GIL locks, and why threads speed up I/O-bound but not CPU-bound code.
2. Explain what happens, step by step, when the event loop hits `await` — and what "cooperative" implies about a misbehaving coroutine.
3. State what FastAPI does differently with `def` vs `async def` routes, and the hidden limit of each.
4. Spot the bug: an `async def` route calls `requests.get()` — describe the exact production symptom this causes.
5. Explain why `asyncio.create_task` without saving the reference is dangerous, twice over.
6. Choose and justify: threads vs processes vs asyncio for (a) resizing 10k images, (b) calling 50 APIs, (c) a chat server with 5k idle connections.
7. Explain what gunicorn adds on top of uvicorn, and how many workers you'd start with on a 4-core box for an I/O-bound API — and why.
8. Explain how cancellation propagates in a TaskGroup and what `asyncio.shield` is for.
9. Describe two ways to run blocking library code from async context without freezing the loop.
10. Explain WSGI vs ASGI and why WebSockets need the latter.

---

## 7. Resources

- **FastAPI docs — "Concurrency and async / await"** — the official mental model; short, read it first
- **Łukasz Langa — "import asyncio" YouTube series** — asyncio internals from a CPython core dev
- **David Beazley — "Understanding the GIL" (talk)** — the classic; old but the intuition is timeless
- **Real Python — asyncio & GIL guides** — good structured walkthroughs of 2.2–2.5
- **superfastpython.com** — encyclopedic reference for threading/multiprocessing/asyncio recipes
- **anyio docs** — what FastAPI/Starlette actually use under the hood; read the "structured concurrency" page
