# 03 — API Design: Contracts People Can Build On

> Phase 1 · Foundations · Builds on: 01 (HTTP semantics), 02 (async fan-out for gateways/webhooks)

---

## 1. Why this matters

Your API is the one part of your system you **can't refactor freely** — the moment a client
integrates, every sloppy decision is frozen. Good API design is what makes the difference
between "we shipped v2 additively" and "we broke mobile for three days".

This topic covers REST done properly (most of your career), plus enough gRPC, GraphQL, and
webhooks to choose between them with reasons instead of fashion. Everything here gets applied
to your todo-app, which currently has a decent but unexamined API — perfect raw material.

---

## 2. Concepts in depth

### 2.1 REST — the actual idea
- Resources & representations: nouns, not verbs; the URL identifies, the method acts
- Richardson Maturity Model (levels 0–3) — where real-world APIs sensibly stop (level 2)
- HATEOAS: understand it, know why almost nobody fully does it, steal the good part (links for pagination)
- Statelessness and why it matters for load balancing (ties back to 01's sticky sessions)

### 2.2 Resource & URL design
- Collections and items: `/todos`, `/todos/{id}`; plural naming, kebab-case, no trailing verbs
- Nesting: `/users/{id}/todos` — when it helps, why deeper than 2 levels hurts
- Actions that don't fit CRUD: `/todos/{id}/complete` vs PATCH state field — the trade-off, pick a house style
- Query params for filtering/sorting/searching: `?status=done&sort=-created_at&q=milk` — conventions
- Sparse fieldsets & expansion: `?fields=`, `?include=` — when payload size starts to matter

### 2.3 HTTP semantics, applied correctly
- Method choice: GET/POST/PUT/PATCH/DELETE, safe vs idempotent (from 01, now applied)
- PUT (full replace) vs PATCH (partial) — and PATCH's two flavors: JSON Merge Patch (RFC 7386) vs JSON Patch (RFC 6902)
- Status codes as contract: `201`+`Location` for create, `204` for delete, `409` conflict,
  `422` validation, `429` throttle — and never `200` with `{"error": ...}` inside
- Content negotiation basics; `Accept` / `Content-Type` discipline

### 2.4 Pagination — deeper than it looks
- Offset/limit: simple, but O(n) skips and **drifts under concurrent writes** (rows shift between pages)
- Cursor/keyset: stable, index-friendly — encode `(created_at, id)` into an opaque cursor token
- Contract shape: `{"items": [...], "next_cursor": "...", "has_more": true}` — why opaque cursors preserve freedom
- Total counts: why `total` is expensive and often dropped or estimated
- This ties directly into topic 04 (the index that makes keyset fast)

### 2.5 Idempotency for unsafe operations
- The retry problem: client timeout ≠ server didn't do it — networks make "exactly once" impossible naively
- Idempotency keys (the Stripe pattern): client sends `Idempotency-Key` header on POST;
  server stores key → response, replays the stored response on retry
- Scoping (per user), TTL, handling "same key, different body" (409)
- Preview: this same idea returns in 08 (job retries) and 11 (message delivery) — it's THE distributed-systems primitive

### 2.6 Error contract
- One envelope everywhere — RFC 9457 `application/problem+json`: `type`, `title`, `status`, `detail`, `instance`
- Validation errors: consistent field-level shape (map FastAPI/Pydantic's format into yours deliberately)
- Correlation/request IDs in every error response (foreshadows topic 14 — tracing)
- What NOT to leak: stack traces, SQL, internal service names

### 2.7 Versioning & evolution
- Strategies: URI (`/v1/`), header, media-type — trade-offs; URI wins on pragmatism, know why people argue
- The better goal: **avoid v2** — additive, backward-compatible changes; tolerant readers
- What's breaking vs non-breaking (add optional field = fine; rename/retype = breaking)
- Deprecation process: `Deprecation`/`Sunset` headers, docs, timelines

### 2.8 OpenAPI as a first-class artifact
- Code-first (FastAPI generates it) vs schema-first — when contracts precede code (teams, public APIs)
- Making FastAPI's output professional: tags, summaries, examples, response models per status code, error schemas
- Generated clients (openapi-generator / openapi-ts) — the contract becomes tooling
- Preview: contract testing against the spec (topic 13)

### 2.9 gRPC — internal RPC done fast
- Protobuf: schema, field numbers, why they must never be reused (wire compatibility)
- Runs on HTTP/2 (from 01: multiplexing, ALPN) — binary, typed, fast
- Four call types: unary, server-streaming, client-streaming, bidi
- Where it wins: service-to-service (topic 12), polyglot teams, streaming; where it loses: browsers, public APIs
- Deadlines/cancellation propagation (gRPC bakes in what REST leaves to you)

### 2.10 GraphQL — query language for frontends
- Schema, types, resolvers; one endpoint, client picks the shape
- The N+1 resolver problem and DataLoader batching (must-know interview topic)
- Where it fits: BFF/aggregation layer over many sources, complex frontends; where it hurts: caching, rate limiting, unbounded queries (depth/complexity limits)
- Honest comparison table REST vs gRPC vs GraphQL — by consumer, not by hype

### 2.11 Webhooks — APIs in reverse
- You as provider: event selection, payload design, **HMAC signing** (`X-Signature` over body + timestamp), retries with backoff, dead-letter handling, ordering caveats
- You as consumer: verify signature, respond `2xx` fast then process async (ties to 08), handle duplicates (idempotency again)
- Replay attacks and the timestamp check
- Polling vs webhooks vs streaming — decision framework

---

## 3. Hands-on labs

> Code goes in `labs/03_api_design/`, and much of this lands directly in the todo-app.

**Lab 1 — API review of your own work.**
Write a design checklist from 2.1–2.3 (methods, codes, naming, envelope). Audit the todo-app
API against it. Produce `AUDIT.md` listing every violation and its fix. (Painful, valuable.)

**Lab 2 — Cursor pagination, for real.**
Implement keyset pagination on `GET /todos` with an opaque base64 cursor over `(created_at, id)`.
Write a script that inserts rows *while* paginating; demonstrate offset pagination
skipping/duplicating items and cursor pagination staying stable.

**Lab 3 — Idempotency middleware.**
`Idempotency-Key` support on `POST /todos`: store key→response (Redis or a table), replay on
retry, `409` on key-reuse-with-different-body. Prove it with a client that fires the same
create 5× concurrently — exactly one todo must exist.

**Lab 4 — Problem+json everywhere.**
Global exception handlers: every error your API can emit (404, 409, 422, 429, 500) speaks
RFC 9457 with a request ID. Reshape Pydantic validation errors into your envelope.

**Lab 5 — A gRPC sibling.**
`todos.proto` (CRUD + a server-streaming `WatchTodos`). Implement with `grpcio`; call from a
Python client. Note what you got for free (types, streaming) and what got harder (debugging, curl).

**Lab 6 — GraphQL BFF.**
Strawberry GraphQL over the same DB: `me { todos { title, project { name } } }`.
Log SQL, demonstrate the N+1 explosion, fix with a DataLoader. Add a query-depth limit.

**Lab 7 — Webhooks end to end.**
todo-app emits `todo.completed` to registered webhook URLs: HMAC-signed, retried with
exponential backoff on non-2xx. Build a tiny receiver service that verifies the signature,
rejects stale timestamps, dedupes by event ID. Kill the receiver, complete todos, restart —
watch retries deliver.

---

## 4. AWS mapping

| Concept | AWS equivalent | Notes |
|---|---|---|
| Your nginx + FastAPI edge | **API Gateway** (HTTP/REST APIs) | Adds auth, throttling, usage plans, keys at the edge |
| Rate limiting per client | API GW usage plans / throttling | You'll build it yourself in 19; here know it's buyable |
| GraphQL server | **AppSync** | Managed GraphQL incl. resolvers to DynamoDB |
| Webhook delivery infra | **EventBridge** / SNS→HTTP | Managed retries + DLQs for outbound events |
| gRPC service-to-service | ALB supports gRPC; common on EKS | Usually internal, behind the mesh |
| OpenAPI artifact | API GW can import/export OpenAPI | The spec doubles as deployment config |

---

## 5. Mini-project — "todo-app API v2 (the portfolio version)"

Apply the whole topic to the todo-app in one deliberate pass:

1. `/api/v1` prefix + a written one-page API style guide (your house rules)
2. Cursor pagination + filtering + sorting on all collections
3. `Idempotency-Key` on every unsafe POST
4. RFC 9457 errors everywhere, with request IDs
5. Webhook subscriptions resource (`POST /webhooks`) + signed `todo.completed` delivery
6. OpenAPI polished: tags, examples, documented error responses — then generate a TypeScript
   client and use it in your `todo-app-frontend`
7. `STYLE.md` documenting every decision and the rejected alternative (this doc is interview gold)

---

## 6. Self-check — you're done when you can…

1. Design a resource layout for a new domain (e.g., projects/tasks/comments/assignees) and defend every URL and method choice.
2. Explain why offset pagination breaks under concurrent writes and how keyset pagination fixes it — including the index it needs.
3. Walk through the idempotency-key flow for a payment POST: first call, timeout-retry, duplicate with different body.
4. Recite your error envelope and justify each field; explain what problem+json standardizes.
5. List three backward-compatible changes and three breaking ones, and describe a deprecation rollout.
6. Choose REST vs gRPC vs GraphQL for: a public API, internal microservices, a mobile BFF — with two reasons each.
7. Explain protobuf field numbers and why deleting-and-reusing one corrupts old clients.
8. Explain the N+1 problem in GraphQL resolvers and how DataLoader batches it away.
9. Design webhook delivery as the provider: signing, retries, duplicates, ordering — and the consumer's verification steps.
10. Explain why "respond 2xx fast, process async" is the webhook consumer rule (and what happens if you don't).

---

## 7. Resources

- **Stripe & GitHub API references** — read as *exemplars*: pagination, errors, idempotency, versioning done well
- **Zalando RESTful API Guidelines** — the best public, opinionated REST rulebook; skim fully
- **RFC 9457 (Problem Details)** + **RFC 9110 (HTTP Semantics)** — the two you'll actually cite
- **"API Design Patterns" — JJ Geewax** — the book for 2.2–2.7 depth
- **gRPC docs (grpc.io) — Python basics + core concepts** — enough for Lab 5
- **GraphQL: graphql.org/learn + Strawberry docs** — schema thinking and the Python implementation
- **Stripe blog: "Designing robust and predictable APIs with idempotency"** — the canonical idempotency-key writeup
