# 04 — Postgres Deep Dive: The Database Is Where Outages Live

> Phase 2 · Data layer · Builds on: 01, 02, 03 · Playground: adds **postgres + pgbouncer**

---

## 1. Why this matters

You already *use* Postgres through SQLAlchemy — this topic is about what the ORM hides.
In real systems, the database is where most performance problems, most outages, and most
"we can't scale" moments come from: a missing index found in production, a migration that
locked a table for 40 seconds, a connection storm that hit `max_connections`, an isolation
bug that double-charged a customer.

A backend engineer who can read an `EXPLAIN` plan, reason about isolation levels, and do
connection math is dramatically more valuable than one who can only write ORM queries.

---

## 2. Concepts in depth

### 2.1 How Postgres executes a query
- Parse → rewrite → **plan** → execute; where the planner's row estimates come from (statistics, `ANALYZE`)
- MVCC: readers don't block writers — every UPDATE writes a **new row version**; xmin/xmax intuition
- Consequences of MVCC: dead tuples, why `VACUUM` exists, what autovacuum does and when it falls behind (bloat)

### 2.2 Storage model (just enough)
- Heap, 8KB pages, tuples; TOAST for large values
- Why "SELECT count(*) is slow" and "UPDATE = new row" both follow from the storage model
- `fillfactor`, HOT updates — know they exist

### 2.3 Indexes — the biggest lever you have
- B-tree mechanics; what "the index is sorted" buys you (equality, ranges, ORDER BY, keyset pagination from 03)
- **Composite index column order** — the leftmost-prefix rule; designing for your queries, not your tables
- Covering indexes (`INCLUDE`) and index-only scans (and why VACUUM affects them)
- Partial indexes (`WHERE deleted_at IS NULL`) and expression indexes (`lower(email)`)
- GIN (jsonb, arrays, full-text), GiST, BRIN (huge append-only tables), hash — when each
- When indexes get IGNORED: functions on columns, type mismatches, low selectivity, stale stats
- Index costs: write amplification, size — why you don't index everything

### 2.4 Reading EXPLAIN — a required skill
- `EXPLAIN (ANALYZE, BUFFERS)` — costs vs actual, rows estimated vs actual (the #1 red flag)
- Scan types: seq scan, index scan, index-only scan, bitmap scan — when the planner picks each
- Join strategies: nested loop vs hash join vs merge join — and what makes each fast/awful
- `pg_stat_statements` — finding what's actually slow in production, not what you guess

### 2.5 Transactions & isolation — precision required
- ACID, precisely (atomicity vs durability vs isolation confusion is an interview classic)
- Anomalies: dirty read, non-repeatable read, phantom read, lost update, **write skew**
- Postgres levels: Read Committed (default!), Repeatable Read, Serializable (SSI) — what each prevents
- What Read Committed default really means for your code: two reads in one txn can differ
- Patterns: `SELECT ... FOR UPDATE` (pessimistic), optimistic locking via version column, retry-on-serialization-failure
- Idempotency keys from 03 + transactions = the correct "create exactly once" implementation

### 2.6 Locking
- Row locks vs table locks; lock queue behavior — a waiting `ALTER TABLE` blocks everything BEHIND it too
- Deadlocks: how they form, how Postgres resolves, how consistent lock ordering prevents them
- `FOR UPDATE SKIP LOCKED` — the Postgres job-queue pattern (reused in topic 08)
- Advisory locks: app-defined locks (e.g., "only one instance runs this cron") — preview of distributed locks (12)
- `lock_timeout` / `statement_timeout` — the seatbelts every production app should wear

### 2.7 Connection management at scale ⭐
The most under-taught production topic. Work through it in layers:

**Why connections are expensive.** Each Postgres connection = a forked backend **process**
(~5–10MB + scheduler overhead). `max_connections` is small (default 100) for a reason;
1000 real connections can strangle a beefy server.

**Layer 1 — app-level pool (what you have now).** SQLAlchemy/asyncpg pool per app instance:
`pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`, `pool_pre_ping` — what each does,
what the defaults are, symptoms of each misconfiguration (e.g., `QueuePool limit reached`).

**Layer 2 — the connection math.** The equation nobody writes down:
```
total = services × replicas_per_service × workers_per_replica × pool_size(+overflow)
```
4 services × 4 replicas × 4 workers × pool 10 = **640 connections** — already dead at default
settings. Autoscaling makes it worse (scale-out = connection storm). This math is why
poolers exist.

**Layer 3 — external pooler (PgBouncer).** One shared funnel in front of Postgres:
- Modes: **session** (1 client = 1 server conn, safe, weak multiplexing), **transaction**
  (server conn borrowed per txn — the big win), statement (rare)
- What transaction mode BREAKS: session state — `SET search_path`, prepared statements
  (asyncpg caveats!), advisory locks held across transactions, LISTEN/NOTIFY
- Sizing: many client connections in → few dozen server connections out
- Alternatives: pgcat, Odyssey; Supavisor — know the landscape, learn PgBouncer

**Layer 4 — many applications, one database.** When several services/apps share a DB:
- Separate **roles per application** with `CONNECTION LIMIT` per role — per-app budgets so one
  service's leak can't starve the others
- Schemas as namespaces per app; explicit `GRANT`s instead of everything-as-superuser
- Observability: `pg_stat_activity` — who holds what, idle-in-transaction (the silent killer), long-running queries
- When shared-DB stops being okay and you split databases (ownership boundaries — foreshadows topic 12)

**Layer 5 — serverless callers.** Lambda-style compute has no stable process to pool in →
this is exactly what RDS Proxy exists for (see §4).

### 2.8 Multi-tenancy patterns ⭐
How one backend serves many customers ("tenants") — the SaaS bread-and-butter question:

| Model | Isolation | Migrations | Scales to | Noisy neighbor |
|---|---|---|---|---|
| Shared tables + `tenant_id` column | Weakest (app-enforced) | 1× | Millions of tenants | Shared everything |
| Schema per tenant | Medium | N× (painful at 1000s) | ~Hundreds–low thousands | Shared instance |
| Database per tenant | Strongest | N× + orchestration | ~Dozens–hundreds | Isolated |

- **Row-Level Security (RLS)**: `CREATE POLICY ... USING (tenant_id = current_setting('app.tenant_id'))`
  — DB-enforced isolation even if app code forgets the WHERE clause
- The **RLS × pooling interplay** (this is the exam question): `SET` is session state — with
  PgBouncer transaction mode you must use `SET LOCAL` inside the transaction, every transaction
- Composite indexes must lead with `tenant_id`; primary keys often become `(tenant_id, id)`
- Tenant lifecycle: onboarding (create schema/db/rows), offboarding (export + delete), per-tenant backups in schema/db-per-tenant models
- Noisy neighbor mitigation: per-tenant rate limits (topic 19), statement timeouts, separate pools for big tenants
- Hybrid reality: shared tables for the masses + dedicated DB for the whale customer

### 2.9 Power SQL (stop working around the database)
- CTEs (and materialization behavior), window functions (`row_number`, `lag`, running totals)
- `LATERAL` joins (top-N-per-group), `RETURNING`, upserts with `ON CONFLICT`
- JSONB: operators, indexing with GIN, when jsonb is right vs "you wanted a column"
- Native full-text search: `tsvector`/`tsquery` — enough to know when you DON'T need OpenSearch (05)

### 2.10 Migrations without downtime
- Why `ALTER TABLE` can lock everything (2.6's lock queue) — and `lock_timeout` as the guard
- Zero-downtime playbook: additive changes → backfill in batches → validate → switch → drop later
- `CREATE INDEX CONCURRENTLY` (and its caveats); adding NOT NULL safely; splitting a column rename into 5 deploys
- Alembic discipline: autogenerate is a draft, not a truth; always read the SQL

### 2.11 Replication, backups, partitioning (working knowledge)
- WAL — the log everything else is built on (backups, replication, CDC in topic 11)
- Streaming replication; read replicas + **replication lag** (read-your-own-writes problem — reappears in 19)
- Backups: pg_dump vs physical (wal-g/pgBackRest), PITR; "a backup you haven't restored is a hope, not a backup"
- Declarative partitioning: when tables get huge (time-series, logs); partition pruning

---

## 3. Hands-on labs

> Code in `labs/04_postgres_deep_dive/`. Add **postgres + pgbouncer** to the playground compose.
> First step: seed a `todos` table with **5M rows** (script provided by you) — small data lies.

**Lab 1 — Planner forensics.**
On 5M rows: run 6 queries (point lookup, range, sort+limit, join, aggregate, `ILIKE '%x%'`).
`EXPLAIN (ANALYZE, BUFFERS)` each **before and after** adding proper indexes. Keep a log of
plan changes: seq→index, sort→index order, the ILIKE one that no B-tree can save (→ trigram/GIN).

**Lab 2 — Composite index puzzles.**
Query `WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT 20`.
Test index column orders: `(user_id, created_at)`, `(user_id, status, created_at)`,
`(status, user_id)`. Predict each plan before running. Connect to keyset pagination from 03.

**Lab 3 — See the anomalies with your own eyes.**
Two `psql` terminals side by side. Reproduce: non-repeatable read under Read Committed;
lost update; then fix with `FOR UPDATE`, then with optimistic version column, then with
Repeatable Read (observe the serialization error and write the retry loop).

**Lab 4 — Build a job queue on SKIP LOCKED.**
`jobs` table + 3 worker processes claiming with `FOR UPDATE SKIP LOCKED`. Prove no job is
processed twice, and killing a worker mid-job releases its row. (You'll reuse this in 08.)

**Lab 5 — Connection storm + PgBouncer.**
Set `max_connections = 30`. Hammer the todo-app with 4 uvicorn workers × pool 10 → watch
`too many connections`. Put PgBouncer (transaction mode) in front → same load succeeds.
Then break it on purpose: use a session-level `SET` through transaction pooling and observe
state leaking across requests. Fix with `SET LOCAL`.

**Lab 6 — Multi-tenant with RLS.**
Add `tenant_id` to todos + RLS policy + `SET LOCAL app.tenant_id` middleware in FastAPI.
Prove tenant A can't read tenant B **even with a buggy query with no WHERE clause**.
Run it through PgBouncer transaction mode to confirm the `SET LOCAL` discipline holds.

**Lab 7 — Zero-downtime migration drill.**
While a script hammers writes: (a) naive `ALTER TABLE ... ADD COLUMN ... DEFAULT` + index —
measure the pause; (b) the safe playbook: additive column, batched backfill,
`CREATE INDEX CONCURRENTLY`, `lock_timeout` — measure again. Write down both timings.

---

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| postgres container | **RDS Postgres** | Managed backups, patching, Multi-AZ failover |
| — | **Aurora Postgres** | Storage-compute separation, faster replicas & failover; know the pitch |
| PgBouncer | **RDS Proxy** | Managed pooler; the answer to Lambda + Postgres |
| Streaming replica | RDS read replicas | Same replication-lag caveats you saw locally |
| wal-g / PITR | RDS automated backups + PITR | Same WAL concepts underneath |
| postgresql.conf tuning | Parameter groups | Same knobs, different UI |
| pg_stat_statements | Performance Insights | Same job: find the slow query |

---

## 5. Mini-project — "The performance clinic"

Take your todo-app, seed 5M todos / 100k users, then run a full clinic in
`labs/04_postgres_deep_dive/clinic/`:

1. Enable `pg_stat_statements`; capture the top 10 queries under a locust load test
2. Fix the worst 3 with indexes/query rewrites — document before/after `EXPLAIN` + p95 latency
3. Add PgBouncer to the stack; document the connection math for "4 replicas × 4 workers"
4. Make the app multi-tenant with RLS (Lab 6 hardened into the real app)
5. Add `statement_timeout`, `lock_timeout`, and pool settings with a comment justifying each number
6. Write `CLINIC.md` — the before/after story. (This document is a portfolio piece.)

---

## 6. Self-check — you're done when you can…

1. Read an `EXPLAIN ANALYZE` plan aloud and point at the line that's wrong (bad estimate, wrong scan, spilled sort).
2. Design the composite index for a given query, justify the column order, and name a query it will NOT help.
3. Explain MVCC in two minutes: what UPDATE really does, why VACUUM must exist, what bloat is.
4. Name the default isolation level and demonstrate an anomaly it allows — then fix it three different ways.
5. Explain why a blocked `ALTER TABLE` can take down an app even though it's "just waiting".
6. Do the connection math for: 3 services × 5 replicas × 4 workers × pool 10, against `max_connections=100` — and design the fix.
7. Explain PgBouncer transaction mode: what it multiplexes, and THREE things it breaks.
8. Compare the three multi-tenancy models and pick one for: a B2B SaaS with 40 enterprise customers vs a B2C app with 2M users.
9. Write an RLS policy and explain the SET LOCAL discipline it needs behind a transaction-mode pooler.
10. Sequence a zero-downtime column rename as a series of deploys.

---

## 7. Resources

- **postgresql.org docs** — genuinely excellent; read: Indexes, MVCC/Concurrency Control, Performance Tips chapters
- **Use The Index, Luke** ([use-the-index-luke.com](https://use-the-index-luke.com)) — THE indexing book, free; covers 2.3–2.4
- **pgexercises.com** — SQL fluency drills for 2.9
- **The Art of PostgreSQL** — Dimitri Fontaine · "stop treating the DB as a dumb store"
- **postgres.fm podcast + pganalyze blog** — production war stories, one topic per episode
- **AWS: RDS Proxy & Aurora docs** — after the local labs, read how AWS packages the same ideas
- **Designing Data-Intensive Applications, ch. 7 (Transactions)** — the isolation-levels chapter is the best ever written
