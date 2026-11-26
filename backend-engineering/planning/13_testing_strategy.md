# 13 — Testing Strategy: Confidence to Ship, Not Coverage Theater

> Phase 5 · Quality & operations · Builds on: everything (you now have DB, cache, queues, events, services to test)
> Playground: uses **testcontainers** to spin real dependencies per test run

---

## 1. Why this matters

You already have a `tests/` folder in the todo-app — this topic is about testing like an engineer,
not chasing a coverage number. Tests exist to let you **change code without fear** and to **catch
regressions before users do**. The wrong tests (brittle, mock-everything, slow) actively slow you
down; the right ones are the thing that lets a small team move fast safely.

Everything you've built — Postgres (04), Redis (06), auth (07), jobs (08), realtime (09), events
(11), multiple services (12) — is hard to test naively. This topic covers how to test each layer
with real dependencies, plus load testing to know your limits before production finds them.

---

## 2. Concepts in depth

### 2.1 The philosophy (settle this before writing tests)
- Tests give **confidence per unit of maintenance cost** — optimize that ratio, not coverage %
- **Test behavior, not implementation**: tests coupled to internals break on every refactor and test nothing real
- The **test pyramid** vs the **testing trophy**: many fast/isolated tests, fewer integration, fewest e2e — and why the modern trophy weights integration heavily for web backends
- What NOT to test (framework internals, third-party libs, trivial getters); the diminishing returns curve
- Flaky tests are worse than no tests — they train you to ignore red; zero tolerance

### 2.2 pytest mastery (your tool, in depth)
- **Fixtures**: scope (function/class/module/session), composition, `yield` for setup/teardown, factory fixtures
- Parametrization (`@pytest.mark.parametrize`) — one test, many cases; where it beats loops
- Markers, `conftest.py` layering, plugins (`pytest-asyncio` for your async code!, `pytest-cov`, `pytest-xdist` for parallel, `pytest-mock`)
- Assertion introspection, `pytest.raises`, approximate comparisons, snapshot testing (when useful/dangerous)
- Testing **async** code correctly (topic 02): event-loop fixtures, async fixtures, common `pytest-asyncio` pitfalls

### 2.3 Test doubles — used deliberately
- Vocabulary precisely: dummy, stub, spy, mock, fake — and stop calling all of them "mocks"
- **Mock at boundaries you don't own** (third-party HTTP, payment providers, email) — NOT your own DB
- The over-mocking trap: mocking your repository/DB means you test your mocks, not your SQL (topic 04's index bugs sail right through)
- `unittest.mock` / `pytest-mock`; faking external HTTP with `respx`/`responses`/VCR-style cassettes
- Dependency injection (FastAPI's `Depends` + `app.dependency_overrides`) as the clean seam for test doubles

### 2.4 Integration testing with real dependencies ⭐
- Why: your bugs live in the SQL, the migration, the cache invalidation, the transaction boundary — mocks hide all of it
- **Testcontainers**: spin a real Postgres/Redis/Kafka/MinIO in Docker, per test session, throwaway — the single biggest upgrade to your testing
- Database test strategies: transaction-rollback-per-test (fast, isolated) vs truncate-per-test vs fresh-schema; migration testing (run Alembic against a real DB — topic 04)
- Testing the FastAPI app: `TestClient`/`httpx.AsyncClient` + real DB via testcontainers; testing dependencies, middleware, auth (topic 07)
- Test data: factories (`factory_boy`), builders, and why fixtures-as-giant-SQL-dumps rot
- Seeding realistic volume for perf-sensitive tests (topic 04's 5M rows lesson)

### 2.5 Testing the hard stuff you built
- **Async & concurrency** (topic 02): deterministic tests for race conditions; testing that the loop isn't blocked
- **Background jobs** (topic 08): eager/synchronous execution mode, fake brokers, or real broker via testcontainers; asserting retries/DLQ behavior
- **Events** (topic 11): produce → assert consumer effect; testing idempotency (deliver twice, assert once); embedded/testcontainer Redpanda
- **WebSockets/SSE** (topic 09): the WS test client, asserting broadcast across a (test) backplane
- **External APIs & webhooks** (topic 03): cassettes/mock servers; testing your webhook signature verification and retry logic
- **Time & randomness**: freeze time (`freezegun`/`time-machine`), seed randomness — the classic flakiness sources
- **Multi-tenancy/authz** (topics 04/07): tests that assert tenant A CANNOT see tenant B (turn the security labs into permanent tests)

### 2.6 Contract testing (essential once you have >1 service — topic 12)
- The problem: service A and B deploy independently; full e2e is slow and flaky; how do you know A didn't break B?
- **Consumer-driven contracts** (Pact): consumer declares expectations → provider verifies them in its own CI
- Schema/contract checks against OpenAPI (topic 03) and event schemas (topic 11 schema registry)
- Where contract tests sit vs integration vs e2e — and how they let teams move independently

### 2.7 End-to-end & component testing
- Component tests: one service fully wired (real DB/cache via testcontainers) but external services stubbed — the sweet spot for backends
- True e2e: the whole system up (docker-compose/k8s) — valuable but few, slow, flaky-prone; reserve for critical user journeys
- Test environments: ephemeral environments per PR (ties to topic 17 CI/CD)

### 2.8 Load & performance testing ⭐ (know your limits before prod does)
- Types: **load** (expected traffic), **stress** (find the breaking point), **spike** (sudden surge — topic 09 reconnect storms), **soak** (memory leaks over hours)
- Tools: **k6** (scriptable, modern — recommended), **Locust** (Python, you'll feel at home), wrk/vegeta for quick blasts
- Designing a realistic test: think in user journeys and ratios, not "hit one endpoint"; open vs closed models
- Metrics that matter: throughput (RPS), latency percentiles (p50/p95/p99 — averages lie), error rate under load, saturation
- Finding the knee: where latency explodes; connecting results back to topics 02 (workers), 04 (connections/queries), 06 (cache)
- Load testing the things that aren't HTTP: WebSocket connections (topic 09), queue throughput (topic 08), event consumers (topic 11)

### 2.9 Coverage, mutation & quality signals
- Coverage as a **floor and a map** (find untested branches), never a target to game
- **Mutation testing** (`mutmut`/`cosmic-ray`): does your test suite actually fail when code breaks? The real quality signal
- Property-based testing (`hypothesis`): generate inputs, assert invariants — finds edge cases you'd never write by hand
- Snapshot/approval testing — powerful for complex outputs, dangerous when rubber-stamped

### 2.10 Testing culture & CI
- Fast feedback: unit/integration in seconds-to-a-minute; the slow suite gated separately (topic 17)
- Test isolation & parallelism (`pytest-xdist`) — tests must not share state (echoes statelessness, topic 01)
- TDD as a design tool (not a religion): when the red-green-refactor loop genuinely helps
- Deterministic, hermetic tests; quarantining flakes; test code IS production code (review it, refactor it)

---

## 3. Hands-on labs

> Code in `labs/13_testing_strategy/`, mostly hardening the todo-app's own suite.

**Lab 1 — Testcontainers integration base.**
Replace any mocked-DB tests with a real Postgres via testcontainers. Set up transaction-rollback-
per-test. Prove it catches a bug a mock can't: write a query that works in SQLite/mocks but fails
on a real Postgres constraint or index (topic 04).

**Lab 2 — The over-mocking autopsy.**
Take one heavily-mocked test; rewrite it as an integration test with real deps. Introduce a real
bug (a wrong `WHERE` clause) and show the mocked version stays green while the integration version goes red.

**Lab 3 — Test the hard stuff you built.**
Write tests for: a background job's retry+DLQ (topic 08), an idempotent event consumer delivered
twice (topic 11), a WebSocket broadcast (topic 09), and a webhook signature verifier (topic 03).
Use testcontainers for the real Redis/Redpanda.

**Lab 4 — Security regression tests.**
Turn topic 07's BOLA exploit and topic 10's tenant-isolation attacker script into permanent tests
that fail loudly if isolation ever regresses. (Security bugs you've fixed should never come back silently.)

**Lab 5 — Time, randomness, and flakiness.**
Find or introduce a time-dependent test; make it deterministic with frozen time. Add a
property-based test with `hypothesis` for a validation/serialization function and let it find an edge case.

**Lab 6 — Contract testing two services.**
Between the todo-app and topic 12's notifications service: write a consumer-driven contract (Pact)
so the provider's CI verifies it. Break the provider's response shape and watch the contract test catch it.

**Lab 7 — Load test to the knee (the eye-opener).**
With k6 (or Locust), model a realistic user journey against the todo-app. Ramp load until p99
explodes. Identify the bottleneck (workers? connections? a missing index? cache?) and tie it back
to the exact earlier topic. Fix one thing, re-run, quantify the improvement.

**Lab 8 — Mutation testing reality check.**
Run `mutmut` on a core module. Find the surviving mutants (bugs your tests DON'T catch). Add tests
to kill them. Compare the insight to what line coverage told you.

## 4. AWS / CI mapping

| Local concept | Cloud/CI equivalent | Notes |
|---|---|---|
| testcontainers | Same, in CI (GitHub Actions services / Docker-in-CI) | Topic 17 wires this into the pipeline |
| Ephemeral test env | Per-PR preview envs (ECS/EKS namespaces) | Topic 16/17 |
| Load test runner | **Distributed k6 / Locust**, or managed (Grafana Cloud k6) | Run from multiple nodes for real scale |
| Contract broker | Self-hosted Pact Broker / PactFlow | Shared contract verification |
| Coverage/quality gates | Codecov / SonarQube in CI | Topic 17 gates |

---

## 5. Mini-project — "A test suite you'd trust on a Friday deploy"

Harden the todo-app's testing to production standard, in `labs/13_testing_strategy/`:

1. Full integration suite on real dependencies via testcontainers (DB, Redis, Redpanda, MinIO)
2. The hard-to-test features all covered: jobs, events (incl. idempotency), realtime, webhooks, auth flows
3. Security regression tests locking in the topic-07 and topic-10 isolation guarantees
4. Contract test(s) with the second service (topic 12)
5. A k6 load-test script + a `LOAD.md` reporting the knee, the bottleneck, and the fix
6. Fast suite (<1 min) vs slow suite split, ready for CI (topic 17); mutation-tested core module
7. **`TESTING.md`**: the strategy — what's tested at which level and WHY, what's deliberately not
   tested, and how to run each suite. (This doc signals senior-level thinking.)

Done = you can refactor a core module freely and trust that green means safe-to-ship.

---

## 6. Self-check — you're done when you can…

1. Explain the test pyramid vs trophy and justify where you invest for a web backend.
2. Explain "test behavior not implementation" with an example of a test that breaks on refactor but catches no bug.
3. State the rule for what to mock vs use real, and explain the over-mocking trap with a concrete failure it hides.
4. Set up testcontainers-backed integration tests and choose a DB isolation strategy with reasoning.
5. Test an idempotent event consumer and a job's retry/DLQ behavior deterministically.
6. Turn a security fix into a regression test that proves isolation holds.
7. Eliminate flakiness from time/randomness/shared-state and explain each source.
8. Explain consumer-driven contract testing and why it lets services deploy independently.
9. Design a realistic load test, name the four load-test types, and interpret p99 vs average.
10. Explain what mutation testing reveals that line coverage cannot.

---

## 7. Resources

- **"Architecture Patterns with Python" (Percival & Gregory, free online)** — testing, DI, and the seams that make FastAPI apps testable; read this
- **pytest docs + "Python Testing with pytest" (Brian Okken)** — fixtures/parametrization mastery
- **testcontainers-python docs** — the integration-testing upgrade (§2.4)
- **Martin Fowler — "Mocks Aren't Stubs", "Test Pyramid", "TestDouble"** — the vocabulary and philosophy canon
- **k6 docs + "Grafana k6 examples"** and **Locust docs** — load testing (§2.8)
- **Pact docs (pact.io)** — consumer-driven contract testing
- **hypothesis docs** — property-based testing; the tutorial finds bugs in your code within minutes
- **Kent C. Dodds — "Testing Trophy"** — the modern integration-weighted counterpoint to the pyramid
