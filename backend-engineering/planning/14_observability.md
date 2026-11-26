# 14 — Observability: Knowing What Your System Is Doing in Production

> Phase 5 · Quality & operations · Builds on: 03 (request ids), 08/09/11 (things to watch), 12 (tracing across services)
> Playground: adds **prometheus + grafana + loki + jaeger** (the local observability stack)

---

## 1. Why this matters

In development you have a debugger. In production you have logs, metrics, and traces — and if you
didn't add them *before* the incident, you're flying blind at 3am while users churn. The
difference between "the site is slow" and "the p99 on `/search` tripled because Postgres connection
wait time spiked after the 14:02 deploy" is observability.

You've now built a lot of moving parts — jobs, events, caches, multiple services — each of which
fails in its own way. This topic is how you *see* all of it: the three pillars (logs, metrics,
traces), how to instrument a FastAPI app properly, and how to turn signals into alerts that page a
human only when they should.

---

## 2. Concepts in depth

### 2.1 Observability vs monitoring (the framing)
- Monitoring = watching known failure modes (is CPU high?); observability = being able to ask NEW
  questions about your system without shipping new code ("why are *these specific* users slow?")
- The three pillars — **logs** (discrete events), **metrics** (aggregatable numbers), **traces**
  (causal request flow) — and how they complement each other; when you reach for which
- Cardinality: the concept that governs cost and design across all three (high-cardinality data
  belongs in traces/logs, not metric labels — the #1 way people blow up their metrics bill)

### 2.2 Structured logging (fix this first)
- Unstructured strings vs **structured JSON logs** — why machines must parse logs, and how string logs make aggregation impossible
- What every log line needs: timestamp, level, message, **correlation/request id** (topic 03),
  service name, and relevant context — but NOT secrets/PII (ties to topic 07)
- Log **levels** used correctly (DEBUG/INFO/WARN/ERROR) and per-environment configuration
- **Context propagation**: request-scoped context (contextvars) so every log in a request carries
  the trace id automatically — including across async (topic 02), jobs (topic 08), and events (topic 11)
- Python: `structlog` / stdlib `logging` with a JSON formatter; FastAPI/uvicorn access logs; sampling noisy logs
- The cost trap: logging is not free (I/O, storage, and it can block — topic 02); what to log vs count as a metric

### 2.3 Metrics (the numbers you alert on)
- Metric types: **counter** (monotonic — requests, errors), **gauge** (point-in-time — queue depth,
  connections), **histogram/summary** (distributions — latency) — and when each is correct
- **Prometheus model**: pull-based scraping, time series identified by name + labels, `/metrics`
  endpoint exposition; the client library for Python/FastAPI
- **PromQL** basics: rate(), histogram_quantile() for percentiles, aggregation by label — enough to build a dashboard and an alert
- **The RED method** (Rate, Errors, Duration) for request-driven services and **USE method**
  (Utilization, Saturation, Errors) for resources — the two frameworks that tell you WHAT to measure
- The **four golden signals** (Google SRE): latency, traffic, errors, saturation
- Business metrics too (signups, todos completed) — not just infra; the ones that tell you the product is healthy
- Instrumenting what you built: request metrics, DB pool/query metrics (04), cache hit ratio (06),
  queue depth & job outcomes (08), consumer lag (11), WS connections (09)
- Percentiles over averages (again) — why you alert on p99, and the histogram that makes it possible

### 2.4 Distributed tracing ⭐ (the microservices superpower)
- The model: **trace** (one request's whole journey) → **spans** (each operation) → parent/child
  causal tree; span attributes, events, status
- **Context propagation**: the trace id/span id passed across every hop — HTTP headers (W3C
  `traceparent`), and crucially across **async boundaries**: queues (08), events (11), WS (09) — so
  a trace spans "API → job → event → other service" (delivers on topic 12's promise)
- **Sampling**: head vs tail sampling; why you can't trace 100% at scale and how to keep the interesting traces (errors, slow ones)
- Reading a trace to answer "where did the time go?" — the waterfall view; spotting N+1 (topic 03/05), serial calls that should be parallel (topic 02), a slow dependency

### 2.5 OpenTelemetry (the standard that ties it together) ⭐
- What OTel is: a vendor-neutral standard + SDKs for traces, metrics, AND logs — instrument once, export anywhere
- **Auto-instrumentation** for FastAPI/SQLAlchemy/httpx/Redis/Kafka — huge amount of visibility for
  near-zero code; then manual spans for your business logic
- The **Collector**: receive → process (batch, sample, redact) → export; why you route through it instead of hardcoding a backend
- Signals unified: correlating a log line → its trace → the metrics around it (the "single pane" dream)
- Migration reality: OTel is where the industry is going; learn it rather than a vendor SDK

### 2.6 The stack & storage
- **Metrics**: Prometheus (+ long-term stores like Thanos/Mimir — awareness); Grafana for dashboards
- **Logs**: Loki (Grafana's log store, cheap, label-indexed) or the ELK/OpenSearch stack (topic 05!) — trade-offs
- **Traces**: Jaeger / Tempo; how traces link to logs and metrics in Grafana
- **Dashboards**: Grafana — designing dashboards people actually use (RED/USE panels, not 200 random graphs); dashboards as code
- Data lifecycle & cost: retention, downsampling, sampling, cardinality control — observability bills are real and sneak up

### 2.7 Alerting & on-call (turning signals into action)
- **Alert on symptoms, not causes**: page on "users see errors / latency SLO burning", not "CPU 80%" (CPU high might be fine)
- **SLI / SLO / SLA**: service level *indicator* (the measurement) → *objective* (the target, e.g. 99.9%)
  → *agreement* (the contract) — and the **error budget** that turns reliability into a decision tool (ship features vs fix reliability)
- **Burn-rate alerting** on error budgets — the modern alternative to threshold spam
- Alert quality: actionable, documented (runbooks), routed (Alertmanager/PagerDuty), and the war
  against **alert fatigue** (a pager that cries wolf gets ignored — then the real one is missed)
- Health checks (topic 01/16): liveness vs readiness vs startup — what each means and why conflating them causes outages

### 2.8 Using it: the incident workflow
- From alert → dashboard (which golden signal?) → trace (which hop?) → logs (what exactly failed?) — the drill-down path the three pillars enable
- **Debugging with correlation ids** across services/jobs/events (the payoff of all the context propagation)
- Profiling in production (continuous profiling — Pyroscope/Parca, awareness) for CPU/memory hotspots (ties to topic 19)
- Blameless **postmortems**: what happened, why, and what systemic fix prevents recurrence — the culture that makes reliability compound

---

## 3. Hands-on labs

> Code in `labs/14_observability/`. Add **prometheus + grafana + loki + jaeger** to the playground (the big compose addition).

**Lab 1 — Structured logging with context.**
Convert the todo-app to structured JSON logs via `structlog`. Inject a request id (topic 03)
into a contextvar so every log line in a request carries it — automatically, including inside a
background job (topic 08) and an event consumer (topic 11). Ship logs to Loki; query by request id in Grafana.

**Lab 2 — Metrics + a RED dashboard.**
Expose `/metrics`; add Prometheus. Instrument RED (rate/errors/duration histogram) for all
endpoints. Build a Grafana dashboard with p50/p95/p99 (via `histogram_quantile`), request rate,
and error rate. Add the resource USE panels (DB connections from topic 04, cache hit ratio from 06).

**Lab 3 — OpenTelemetry auto + manual instrumentation.**
Add OTel auto-instrumentation (FastAPI + SQLAlchemy + httpx + Redis). Export traces to Jaeger.
Add manual spans around a business operation. Open a trace and read the waterfall.

**Lab 4 — Trace across the async gap (the key lab).**
Propagate trace context from an API request → a background job (topic 08) → an event (topic 11) →
the second service (topic 12). View ONE trace spanning API + job + event + service. This is the
"where did the time go across my whole system" superpower.

**Lab 5 — Find a real bottleneck with a trace.**
Reintroduce an N+1 query or a serial-instead-of-parallel set of calls. Use the trace waterfall to
spot it (not by reading code). Fix it; confirm in the trace and the p99 metric. Tie back to topics 02/03/05.

**Lab 6 — Instrument the moving parts.**
Add metrics for: queue depth + oldest-message age + job success/failure (topic 08), consumer lag
(topic 11), and live WebSocket connections (topic 09). Dashboard them. Load them up and watch the graphs move.

**Lab 7 — SLOs, error budgets, and a good alert.**
Define an SLO (e.g., 99.5% of `/todos` requests < 300ms). Implement a burn-rate alert in
Prometheus/Alertmanager. Trigger it by injecting latency; confirm it fires. Then create a
deliberately noisy CPU-threshold alert and articulate in `NOTES.md` why the symptom-based SLO alert is better.

**Lab 8 — The 3am drill.**
Break something non-obvious (e.g., cache returning stale + a slow dependency). Starting only from
the alert, use dashboard → trace → logs to diagnose it, timing yourself. Write a mini blameless postmortem.

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| Prometheus | **Amazon Managed Prometheus (AMP)** / CloudWatch metrics | AMP speaks PromQL |
| Grafana | **Amazon Managed Grafana** | Same dashboards |
| Loki / log store | **CloudWatch Logs** | Logs Insights for querying |
| Jaeger / traces | **X-Ray** (or OTel → AMP/Grafana) | X-Ray is AWS-native tracing |
| OTel Collector | **ADOT** (AWS Distro for OpenTelemetry) | AWS's OTel distribution |
| Alertmanager | **CloudWatch Alarms + SNS** → PagerDuty | Symptom-based alerting |
| Continuous profiling | **CodeGuru Profiler** | §2.8 |

*(The whole point of OpenTelemetry: instrument once locally, and switching to any of these is a config change, not a code change.)*

---

## 5. Mini-project — "Full observability for the todo-app system"

In `labs/14_observability/`, make the whole multi-service system observable:

1. Structured logs with automatic request/trace-id context across API, jobs, events (Loki)
2. RED + USE metrics for the API and every dependency you built (DB, cache, queue, consumers, WS) — Grafana dashboards as code
3. OTel tracing that spans API → job → event → second service in a single trace (Jaeger/Tempo)
4. Defined SLOs with burn-rate alerts (Alertmanager) — symptom-based, with a runbook per alert
5. A documented incident drill: from alert to root cause using the three pillars, with a postmortem
6. **`OBSERVABILITY.md`**: the instrumentation strategy, the golden signals per service, the SLOs
   and their rationale, and the drill-down runbook. (This is exactly what an SRE interviewer wants to see.)

Done = given only a page ("SLO burning"), you can reach root cause via dashboard → trace → logs in minutes, not hours.

---

## 6. Self-check — you're done when you can…

1. Explain observability vs monitoring and give a question only observability (not monitoring) can answer.
2. Explain the three pillars, what each is best at, and how correlation ids/trace ids link them.
3. Explain why structured logs beat string logs and what every log line must (and must not) contain.
4. Explain counter vs gauge vs histogram and which you'd use for latency, queue depth, and error count.
5. Explain the RED and USE methods and the four golden signals, and instrument a service by them.
6. Explain distributed tracing and how context propagates across an async/queue/event boundary.
7. Explain what OpenTelemetry standardizes and why "instrument once, export anywhere" matters.
8. Explain cardinality and how a bad metric label blows up cost.
9. Define SLI/SLO/SLA and error budgets, and explain burn-rate alerting vs threshold alerting.
10. Explain "alert on symptoms not causes" with an example of a cause-based alert that should NOT page.

---

## 7. Resources

- **Google SRE Book + SRE Workbook (free online)** — SLIs/SLOs/error budgets, golden signals, alerting philosophy: the canon for §2.7
- **"Observability Engineering" (Majors, Fong-Jones, Miranda — Honeycomb)** — the modern definition & high-cardinality argument
- **OpenTelemetry docs + opentelemetry-python** — auto & manual instrumentation (§2.5)
- **Prometheus docs + "PromQL for humans"** and **Grafana tutorials** — metrics & dashboards
- **Brendan Gregg — USE method; Tom Wilkie — RED method** — the two measurement frameworks, from the source
- **Charity Majors' blog / talks** — observability culture and why "test in prod" isn't heresy
- **structlog docs** — structured logging in Python (Lab 1)
