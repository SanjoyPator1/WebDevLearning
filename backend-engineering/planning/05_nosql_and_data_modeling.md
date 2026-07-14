# 05 — NoSQL & Data Modeling: The Right Store for the Job

> Phase 2 · Data layer · Builds on: 04 · Playground: adds **mongodb, dynamodb-local, opensearch**

---

## 1. Why this matters

"Should this go in Postgres?" is a question you'll answer for the rest of your career.
Usually yes — but the times it's *no* (a leaderboard, a session store, product search,
100k writes/sec of telemetry) are exactly the times naive choices melt down.

This topic gives you a taxonomy of data stores, hands-on depth in the three you'll actually
meet (Redis, MongoDB, DynamoDB) plus search (OpenSearch), and — more important than any tool —
the **access-pattern-first modeling method** that decides between them.

---

## 2. Concepts in depth

### 2.1 Data modeling fundamentals (the part that transfers everywhere)
- Normalization speed-run: 1NF→3NF, what each rule prevents; anomaly types
- **Denormalization as a deliberate trade**: duplicate data to kill joins — pay with write complexity and drift risk
- The method: list access patterns FIRST ("get user's todos sorted by due date", "count open per project"),
  then choose structure — relational models entities; NoSQL models **queries**
- Estimating: rows × row size × growth; read/write ratio; cardinality — back-of-envelope skills

### 2.2 A taxonomy of stores
- Key-value (Redis) · document (MongoDB) · wide-column (Cassandra — conceptual only) ·
  search (OpenSearch) · graph (Neo4j — conceptual only) · time-series (Timescale/Influx — conceptual only)
- For each: data model, how it scales (replication/sharding), consistency posture, killer use case
- CAP theorem *correctly* stated (it's about behavior **during a partition**) — deep dive comes in 12

### 2.3 Redis — the multitool (more than a cache)
- Single-threaded event loop (ties to 02!) — why commands are atomic and why one slow command (`KEYS *`) stalls everything
- Data structures + canonical use per type:
  - string (cache, counters), hash (objects), list (simple queue), set (tags, uniques)
  - **sorted set** (leaderboards, rate limiters, delayed jobs) — the star of the show
  - streams (log/queue with consumer groups — preview of 11's Kafka concepts in miniature)
  - HyperLogLog (approximate uniques), bitmaps, TTL mechanics
- Persistence: RDB snapshots vs AOF — what you lose on crash with each
- Transactions (`MULTI`/`EXEC`), Lua scripts for atomic read-modify-write
- Topologies at a glance: standalone → Sentinel (HA) → Cluster (sharding); hash slots concept
- Caching patterns deliberately deferred to 06 — here Redis is a *database*

### 2.4 MongoDB — the document model
- Documents/collections; `_id`; BSON types
- **The one modeling decision: embed vs reference** — embed what you read together, reference
  what grows unboundedly or is shared; the 16MB document limit as a design smell detector
- Indexes (same B-tree intuitions from 04 transfer), compound indexes, the ESR rule
- Aggregation pipeline: `$match → $group → $project` — MongoDB's GROUP BY
- Replica sets, read/write concerns (`w: majority`) — your first taste of tunable consistency
- Schema validation; when "schemaless" becomes "schema is in your app code, unversioned" (the honest critique)
- When Mongo genuinely fits: heterogeneous documents, prototyping speed, hierarchical data read as a unit

### 2.5 DynamoDB — designing for guaranteed scale
- The contract: partition key (+ optional sort key) → single-digit-ms at ANY scale — because it
  forbids everything that doesn't scale (no joins, no ad-hoc queries)
- Partitions, hot-partition problem, why high-cardinality keys matter
- Query vs Scan (and why Scan in production is a bug report waiting to happen)
- GSIs/LSIs — buying back query patterns; eventual consistency of GSIs
- **Single-table design** mindset: overloaded keys (`PK=USER#1, SK=TODO#2026-07-01#42`) — model ALL
  access patterns into one table; when to NOT bother (few patterns, small scale)
- Capacity modes (on-demand vs provisioned), item size limits, TTL, streams (→ topic 11)
- Local: `amazon/dynamodb-local` container — full API, zero AWS bill

### 2.6 Search — OpenSearch/Elasticsearch
- The inverted index: why search engines answer "contains word" in ms while Postgres `ILIKE '%x%'` dies (Lab 1 of topic 04 proved this)
- Analysis pipeline: tokenizers, filters, stemming; mappings (`keyword` vs `text` — the classic confusion)
- Query DSL essentials: `match`, `term`, `bool`, filters vs queries (scoring vs yes/no), fuzziness (typo tolerance)
- Relevance basics: TF-IDF/BM25 intuition
- Aggregations (facets); pagination pitfalls (`from/size` vs `search_after`)
- It's a cluster: shards/replicas — but deep cluster ops are out of scope; **it's a secondary index,
  never the source of truth** — sync strategies (app-dual-write now, outbox/CDC properly in 11)
- Honest decision: Postgres FTS (from 04) is enough until it isn't — know the line

### 2.7 Choosing — the decision framework
- A worked decision table: access patterns × consistency needs × scale × ops budget → store
- Polyglot persistence: Postgres (truth) + Redis (speed) + OpenSearch (search) — the standard trio, each store doing its one job
- The cost nobody prices in: every extra store = another thing to sync, back up, monitor, and page you at 3am

---

## 3. Hands-on labs

> Code in `labs/05_nosql_and_data_modeling/`. Add **mongodb, dynamodb-local, opensearch** to the playground compose.

**Lab 1 — Redis structures tour (redis-cli only, no code).**
Build with raw commands: a page-view counter, a user object as hash, a tag set with
intersection ("todos tagged work AND urgent"), a leaderboard (zset) with rank lookup,
a delayed-job queue (zset scored by timestamp). Feel the data structures before wrapping them in Python.

**Lab 2 — Rate limiter on Redis (production pattern).**
Sliding-window rate limiter as FastAPI middleware: zset of timestamps per user, atomic via Lua.
Load test to prove the limit holds under concurrency. (Reused in 19.)

**Lab 3 — Embed vs reference, measured.**
Blog model in MongoDB twice: (a) comments embedded, (b) comments referenced.
Benchmark "load post page" and "user's last 10 comments across posts" on both.
Write down which access pattern each design optimizes — that's the whole lesson.

**Lab 4 — DynamoDB single-table todo.**
Model users + projects + todos in ONE table against 5 access patterns you write first
(e.g., "all todos for user by due date", "todos in project", "single todo by id").
Design PK/SK + one GSI on paper, then implement against dynamodb-local with boto3.
Then try the query you did NOT design for — experience the wall, understand the contract.

**Lab 5 — Search your todos.**
Index todos into OpenSearch (mapping: `title` as text + keyword subfield, `status` keyword,
`due_date` date). Build `/search?q=` with: fuzzy match (typo tolerance), status filter,
highlight, facet counts by project. Compare result quality vs Postgres FTS from topic 04 on the same data.

**Lab 6 — The sync problem (honest preview).**
Your Lab 5 index goes stale when todos change. Implement app-level dual-write, then write
in `NOTES.md` every way it can break (crash between writes, ordering, backfill). You'll fix
this properly with the outbox pattern in topic 11 — here you just need to *feel* the problem.

---

## 4. AWS mapping

| Local container | AWS service | Notes |
|---|---|---|
| redis | **ElastiCache (Redis/Valkey)** | Same commands; Sentinel/Cluster become checkboxes |
| mongodb | **DocumentDB** | Mongo-compatible API, not Mongo internals; also MongoDB Atlas on AWS |
| dynamodb-local | **DynamoDB** | The real thing; local is API-identical for dev |
| opensearch | **OpenSearch Service / Serverless** | Managed cluster, same Query DSL |
| — | **Keyspaces** | Cassandra-compatible, maps to the wide-column concepts from 2.2 |

*(DynamoDB is the one store here that has no real self-hosted production equivalent — it IS an AWS service; dynamodb-local is dev-only.)*

---

## 5. Mini-project — "Todo-app goes polyglot"

Extend the todo-app so each store does its one job, in `labs/05_nosql_and_data_modeling/polyglot/`:

1. Postgres stays the source of truth (from 04, multi-tenant and tuned)
2. **OpenSearch**: `/api/v1/search` endpoint — fuzzy, filtered, highlighted, faceted (Lab 5, hardened)
3. **Redis**: rate-limiter middleware (Lab 2) + a "recently viewed todos" list per user (capped list)
4. Sync via dual-write with the failure modes documented (Lab 6)
5. `DECISIONS.md`: for each store — the access patterns it serves, why the others were wrong,
   and what it costs you (sync, ops, consistency). Write it like an ADR (architecture decision record).

---

## 6. Self-check — you're done when you can…

1. Take a feature description and produce an access-pattern list BEFORE any schema — then justify a store choice from it.
2. Explain when denormalization is correct, and name the two costs you accepted.
3. Explain why Redis being single-threaded makes operations atomic — and name a command that can stall it.
4. Design a leaderboard and a sliding-window rate limiter with zsets, from memory.
5. Decide embed vs reference for: order+items, user+followers, post+comments — with the growth argument for each.
6. Explain DynamoDB's contract: what it forbids and what that buys; design a single-table layout for 4 access patterns.
7. Explain what a hot partition is and how key design prevents it.
8. Explain the inverted index and why `ILIKE '%term%'` can't be saved by a B-tree.
9. Explain `text` vs `keyword` mappings and filters vs queries in OpenSearch.
10. Argue when Postgres FTS is enough vs when OpenSearch earns its ops cost — and state the source-of-truth rule.

---

## 7. Resources

- **Designing Data-Intensive Applications, ch. 2–3** — data models & storage engines; the backbone of this topic
- **Redis docs + Redis University (free courses)** — data-structure docs are short and superb
- **Alex DeBrie — "The DynamoDB Book" / dynamodbguide.com** — THE single-table design resource
- **MongoDB University M320 (Data Modeling)** — free, focused exactly on embed-vs-reference
- **Elastic: "Elasticsearch: The Definitive Guide" (concepts) + OpenSearch docs (current APIs)** — inverted index & analysis chapters
- **Martin Kleppmann — "Please stop calling databases CP or AP"** — pre-reading for topic 12's consistency deep dive
