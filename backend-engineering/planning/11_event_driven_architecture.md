# 11 — Event-Driven Architecture: Kafka, Logs, and Getting Data to Move Reliably

> Phase 4 · Distributed & event-driven · Builds on: 05 (streams), 06 (invalidation), 08 (queues/idempotency), 09 (backplane)
> Playground: adds **redpanda + redpanda-console**

---

## 1. Why this matters

At some point "service A calls service B's API" stops scaling: A must know B exists, wait for it,
and handle B being down — and when C, D, E also need to know when something happened, A ends up
calling everyone. Event-driven architecture inverts this: A **publishes a fact** ("todo.completed")
to a log, and anyone interested consumes it, now or later, without A knowing they exist.

This is the backbone of modern systems: analytics, search indexing (fixing topic 05's staleness),
audit logs, cache invalidation (topic 06), notifications (topic 09), and cross-service workflows
(topic 12). Kafka (and its lighter twin Redpanda) is the dominant tool, and its **log** model is a
genuinely different mental model from the task queues you learned in topic 08 — worth real depth.

---

## 2. Concepts in depth

### 2.1 Queue vs log — the mental model shift (do this first)
- Task queue (topic 08): a message is *consumed and removed*; one worker gets each message; it's about **work distribution**
- Log (Kafka): messages are *appended and retained*; many independent consumers read the same records at their own position; it's about **fact distribution**
- Why the difference matters: replay, multiple independent consumers, event history — a log can do things a queue structurally can't
- "Kafka as a queue" is a common misuse — know when a queue (SQS/RabbitMQ) is actually the right tool

### 2.2 Kafka core concepts (depth)
- **Topics** — named streams of records; **partitions** — the unit of parallelism and ordering
- **Ordering guarantee**: only *within* a partition, never across — so the partition key decides ordering (all events for one entity → same partition)
- **Offsets** — a consumer's position in a partition; committed offsets = "how far I've processed"
- **Consumer groups** — partitions distributed across group members; the rebalance dance; scaling consumers = up to #partitions (the ceiling)
- **Producers** — keys, partitioners, `acks` (0/1/all), idempotent producer, batching/linger, compression
- **Retention** — time/size based; log compaction (keep latest value per key — a changelog/table-as-a-stream)
- **Replication** — leader/followers, ISR (in-sync replicas), `min.insync.replicas`, durability vs availability trade
- Delivery semantics in Kafka: at-least-once (default), exactly-once (transactions + idempotent producer) — what it really costs

### 2.3 Redpanda (the local/production alternative)
- Kafka-API-compatible (same clients, same concepts), single binary, no ZooKeeper/JVM — why it's ideal for local labs and increasingly production
- Redpanda Console for inspecting topics/consumer groups visually
- What transfers 1:1 to Kafka/MSK and what doesn't (ops differences only; app code is identical)

### 2.4 Event design — the part that ages well or badly
- **Event types**: event **notification** (thin: "todo 42 changed, go look") vs event-**carried state
  transfer** (fat: the whole todo in the event) vs **event sourcing** events — trade-offs of each
- Naming & schema: past-tense facts (`TodoCompleted`), not commands; versioning events; additive evolution
- **Schema registry** + Avro/Protobuf/JSON Schema: enforcing compatibility so producers can't break consumers (ties to topic 03's contract thinking)
- Keys & partitioning strategy: choosing a key for ordering + even distribution; the hot-partition problem (echoes topic 05 DynamoDB)
- Idempotent consumers (topic 08 again): consumers WILL see duplicates — dedup by event id / idempotency table

### 2.5 The patterns that make it reliable ⭐
- **The dual-write problem**: "write to DB **and** publish to Kafka" is not atomic — a crash between
  them loses or phantoms an event. (This is exactly topic 05 Lab 6's staleness bug, generalized.)
- **The Outbox pattern (the fix)**: write the event to an `outbox` table *in the same DB transaction*
  as the state change; a separate relay publishes outbox rows to Kafka. Atomicity restored. (Builds
  on topic 04 transactions + topic 08's Postgres-drain idea.)
- **Change Data Capture (CDC)**: read the DB's WAL (topic 04!) and stream row changes as events —
  Debezium. Outbox vs CDC: when to use which.
- **Event sourcing**: the event log *is* the source of truth; state is a fold over events. Power
  (audit, time-travel, rebuild) and cost (versioning, snapshots, complexity). When it's worth it (rarely — be honest).
- **CQRS**: separate write model from read model(s), kept in sync via events; pairs with event
  sourcing but is independent. Solves "one schema can't serve all reads" (ties to topic 05 polyglot & topic 19 read scaling).
- **Saga pattern** (deep-dived in topic 12): multi-service workflows via events + compensating actions.
- **Inbox pattern**: consumer-side dedup/ordering guarantee companion to outbox.

### 2.6 Stream processing (awareness + a taste)
- Beyond consume-one-message: aggregations, joins, windowing over streams
- Kafka Streams / ksqlDB / Flink / Faust (Python) — the landscape, one line each
- Stateful processing, watermarks, exactly-once in stream processors — conceptual awareness; a small Faust/consumer lab
- When you need this vs a plain consumer + database

### 2.7 Operating event systems
- Consumer **lag** as THE health metric (are consumers keeping up?) — monitoring & alerting (topic 14)
- Rebalancing storms, poison messages in a log (can't just delete one — offset-skip / DLQ topic), reprocessing/replay strategy
- Topic design governance: partitions count (hard to increase meaningfully), retention, naming conventions
- Multi-tenancy in Kafka: topic-per-tenant vs shared-topic-with-key vs partition strategy — trade-offs (echoes topic 04/10 tenancy)
- Cost & complexity honesty: EDA adds eventual consistency, debugging-across-async-hops, and ops — don't event-ify a monolith that doesn't need it

---

## 3. Hands-on labs

> Code in `labs/11_event_driven_architecture/`. Add **redpanda + redpanda-console** to the playground.

**Lab 1 — Log vs queue, felt directly.**
Produce 1000 events to a topic. Attach TWO independent consumer groups; show both read ALL events
independently (unlike topic 08's queue where one worker consumed each). Reset one group's offset to
0 and replay. Write the queue-vs-log distinction in your own words.

**Lab 2 — Partitions, ordering, and consumer groups.**
Topic with 3 partitions. Produce events keyed by `tenant_id`; verify per-key ordering holds but
global ordering doesn't. Run 1, 2, 3, then 4 consumers in a group; watch partition assignment and
the 4th sit idle (the #partitions ceiling). Trigger a rebalance by killing a consumer.

**Lab 3 — Fix topic 05's stale search with the Outbox pattern (the key lab).**
When a todo changes, write a row to an `outbox` table in the SAME transaction. A relay process
publishes outbox rows to Redpanda; a consumer updates the OpenSearch index (topic 05). Kill the
relay mid-run and restart — prove no event is lost and the index catches up. Contrast with topic
05's broken dual-write.

**Lab 4 — Idempotent consumer.**
Make the Lab 3 consumer handle duplicate delivery (replay the same events) without double-applying,
using an inbox/dedup table keyed by event id.

**Lab 5 — CDC with Debezium (bonus/awareness).**
Point Debezium at Postgres' WAL; stream `todos` row changes into a topic automatically (no app
code). Compare the developer experience and trade-offs vs the explicit outbox from Lab 3.

**Lab 6 — Event-carried cache invalidation.**
Publish `todo.updated` events; a consumer invalidates the topic-06 Redis cache across all replicas.
This replaces ad-hoc invalidation with an event-driven one — connect the two topics explicitly.

**Lab 7 — A tiny stream processor.**
With Faust (or a stateful consumer): compute a live "todos completed per tenant per minute"
windowed aggregate from the event stream and expose it. Feel stateful stream processing.

**Lab 8 — Consumer lag under load.**
Produce faster than the consumer can process; watch lag grow in Redpanda Console. Scale consumers
(add partitions ahead of time), watch it drain. Define your lag alert threshold.

---

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| Redpanda / Kafka | **MSK** (managed Kafka) | Same Kafka API; MSK Serverless removes broker ops |
| Redpanda / lightweight streaming | **Kinesis Data Streams** | AWS-native log; shards ≈ partitions; different API |
| CDC (Debezium) | **DMS** / MSK Connect + Debezium | Managed change capture |
| Schema registry | **Glue Schema Registry** / Confluent on AWS | Compatibility enforcement |
| Stream processing | **Kinesis Data Analytics (Flink)** / MSK + Flink | Managed stream compute |
| Event bus (routing, not a log) | **EventBridge** | Rules/filtering/fan-out; contrast with a log |
| Fan-out pub/sub | **SNS → SQS** | The simple event fan-out (from topic 08) |

*(Key distinction to internalize: EventBridge/SNS = routing & fan-out; Kinesis/MSK = a retained, replayable log. Different jobs.)*

---

## 5. Mini-project — "Event-driven todo-app"

In `labs/11_event_driven_architecture/`, turn the todo-app into an event producer with several consumers:

1. Domain events (`TodoCreated/Updated/Completed/Deleted`) published via the **Outbox pattern** (atomic with the DB write)
2. Consumers, each independent and idempotent:
   - **Search indexer** → OpenSearch (finally fixes topic 05's staleness, correctly)
   - **Cache invalidator** → Redis across replicas (topic 06)
   - **Notification service** → triggers topic-09 realtime + push
   - **Analytics** → a windowed "activity per tenant" aggregate
3. A schema registry with versioned event schemas and a compatibility rule
4. Consumer lag dashboard + a replay script (reprocess all events to rebuild the search index from scratch)
5. **`EVENTS.md`**: the event catalog (each event's schema, key, producers, consumers), the outbox
   design, delivery-semantics choice, and the failure-mode analysis (relay crash, consumer crash, duplicate, replay).

Done = you can wipe the OpenSearch index and rebuild it entirely by replaying the event log, and no state change is ever lost even if the broker is briefly down.

---

## 6. Self-check — you're done when you can…

1. Explain the difference between a task queue and a log, and give a use case that needs a log specifically.
2. Explain Kafka partitions: how they give parallelism AND ordering, and why ordering is only per-partition.
3. Explain consumer groups and why you can't have more active consumers than partitions.
4. Explain the dual-write problem and how the outbox pattern makes event publishing atomic with the DB write.
5. Contrast outbox vs CDC and pick one for a given constraint.
6. Explain event notification vs event-carried state transfer vs event sourcing, with a trade-off each.
7. Explain why consumers must be idempotent and how you'd dedup with an inbox table.
8. Explain what a schema registry enforces and why event versioning must be additive.
9. Explain consumer lag and why it's the primary health metric for a streaming system.
10. Decide EventBridge/SNS vs Kinesis/Kafka for: fan-out notifications, an audit log, cross-service workflow, rebuildable search index.

---

## 7. Resources

- **Kafka: The Definitive Guide (2nd ed., free from Confluent)** — the core-concepts chapters are the canonical reference
- **Confluent developer courses (developer.confluent.io)** — free, excellent, hands-on for §2.2
- **Redpanda docs + Redpanda University** — Kafka concepts with the local-friendly tooling you'll use
- **microservices.io — Outbox, CDC, Saga, Event Sourcing, CQRS patterns** (Chris Richardson) — the pattern catalog; read these exact pages
- **Debezium docs** — CDC in practice (Lab 5)
- **Martin Kleppmann — "Turning the database inside out" (talk) + DDIA ch. 11 (Stream Processing)** — the deep "why" of logs and event-driven systems
- **Confluent blog — "Exactly-once semantics" & "The dual write problem"** — the reliability truths
