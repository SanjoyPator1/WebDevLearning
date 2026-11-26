# 09 — Realtime: Pushing Data to Clients as It Happens

> Phase 3 · Core application concerns · Builds on: 01 (HTTP/WS, LB), 02 (async), 06 (pub/sub), 08 (job progress)
> Playground: reuses **redis** (pub/sub + streams)

---

## 1. Why this matters

Some features can't wait for the client to ask: chat, live notifications, presence ("who's
online"), collaborative editing, live dashboards, and the job-progress bar you started in
topic 08. HTTP is request-response by design, so realtime means picking the right push
mechanism — and then the hard part: **making it work when you have more than one server**.

The single-server WebSocket demo is easy. The thing that trips up most engineers — and the
thing that makes this a real topic — is scaling it: a message must reach a user whose
connection is pinned to a *different* replica than the one that produced the event.

---

## 2. Concepts in depth

### 2.1 The options and how to choose
- **Short polling**: client asks every N seconds. Simple, works everywhere, wasteful, laggy. When it's genuinely fine.
- **Long polling**: server holds the request open until data or timeout. Better latency, one-shot per message, connection churn.
- **Server-Sent Events (SSE)**: server→client stream over one HTTP connection; auto-reconnect, event ids, text only, unidirectional. Underrated and simple.
- **WebSockets**: full-duplex, persistent, binary or text; the general answer for bidirectional realtime.
- **WebTransport / WebRTC** — know they exist (low-latency/media, datachannels); out of scope depth.
- Decision framework: direction (one-way vs two-way), frequency, payload, client reach, infra cost — a table you can defend

### 2.2 SSE in depth
- The wire format (`data:`, `event:`, `id:`, `retry:`); `text/event-stream`; how the browser auto-reconnects with `Last-Event-ID`
- FastAPI implementation via a streaming response / async generator; keeping the connection alive (heartbeats)
- Where SSE beats WebSockets: notifications, live feeds, job progress, LLM token streaming — one-way and dead simple
- Limits: unidirectional, text-only, per-domain connection caps (HTTP/1.1 6-connection limit from topic 01 — HTTP/2 fixes it)

### 2.3 WebSockets in depth
- Upgrade handshake (HTTP `Upgrade: websocket` → 101 Switching Protocols) — it *starts* as HTTP (topic 01)
- Frames, ping/pong (heartbeat/liveness), close codes
- FastAPI/Starlette WebSocket API: accept, receive/send, disconnect handling
- Application-level protocol design: your own message envelope (`{type, payload, id}`), versioning, JSON vs binary (msgpack)
- **Authentication over WS**: you can't send `Authorization` headers from browser WS easily —
  token in query string (logged! bad) vs ticket/short-lived token vs cookie-based; auth on connect
  vs per-message (ties to topic 07)
- Connection lifecycle: reconnection with backoff, resuming state, missed-message replay (needs buffering — 2.6)

### 2.4 The scaling problem (the heart of this topic) ⭐
- **Why one server is a lie**: WS connections are *stateful and sticky* — a connection lives on one
  replica's memory. Behind the load balancer from topic 01, user A is on replica 1, user B on replica 2.
- The core problem: an event produced on replica 1 (or by a background worker from topic 08) must
  reach user B on replica 2. Replica 1 doesn't know about B's socket.
- **The solution: a backplane / pub/sub bus.** Every replica subscribes to a shared channel
  (Redis pub/sub, or Redis Streams / Kafka for durability). Publish once → all replicas receive →
  each forwards to its own connected clients that care. Decouples "who produced it" from "who's connected where".
- LB requirements: sticky sessions or connection-based routing for WS (from topic 01 L4/L7); WS
  timeouts on the proxy (idle-timeout kills silent connections — heartbeats prevent it)
- Horizontal scale math: connections per node (file descriptors, memory per socket), when you shard
  connections, graceful deploy/drain of a node full of live sockets (clients must reconnect elsewhere)

### 2.5 Pub/Sub and the backplane, precisely
- Redis **pub/sub**: fire-and-forget, no persistence — a subscriber that's down misses messages (fine for presence, risky for "important" events)
- Redis **Streams**: durable log with consumer groups + replay — when you need missed-message delivery (bridges to topic 11's Kafka concepts)
- Channel/topic design: per-user (`user:{id}`), per-room (`room:{id}`), per-tenant fan-out; wildcard subscriptions
- Fan-out patterns: to one user (multi-device), to a room, broadcast; the "thundering fan-out" cost of huge rooms
- When you outgrow Redis: Kafka/Redpanda backplane (topic 11), or a managed realtime service

### 2.6 Realtime feature patterns
- **Presence**: online/offline/last-seen — heartbeats + TTL keys in Redis; the "flaky connection" flap problem
- **Rooms/channels & authorization**: who may subscribe to what (authz from topic 07 applies to subscriptions, not just endpoints)
- **Message history & replay**: sockets are lossy; durable store + "give me messages since id" on reconnect (Streams/DB)
- **Delivery guarantees for realtime**: at-most-once is usually acceptable for presence; important events need ack + persistence
- **Ordering & consistency**: per-channel ordering; the collaborative-editing hard mode (OT / CRDTs — conceptual awareness only)
- **Backpressure to slow clients**: a client that reads slowly can bloat server buffers — drop, coalesce, or disconnect policies

### 2.7 Push notifications (client isn't even connected)
- The distinction: in-app realtime (WS/SSE) vs OS push when the app is closed/backgrounded
- **Web Push** (VAPID + browser Push API + service worker) — how it works end to end
- **Mobile**: APNs (Apple) and FCM (Android/Firebase) — token registration, sending, feedback/expiry
- Architecture: notification service + device-token registry + provider fan-out; this is a
  background-jobs consumer (topic 08) reacting to events (topic 11) — realtime's asynchronous cousin
- Preferences, quiet hours, dedup across channels (don't push + WS + email the same thing)

### 2.8 Operating realtime systems
- Metrics: concurrent connections, messages/sec, fan-out ratio, delivery latency, reconnect storms (topic 14)
- The reconnect-storm failure mode: a deploy drops 100k sockets → all reconnect at once → thundering herd (jitter the reconnect backoff)
- Testing realtime: scripted WS clients, load testing connections (not just requests) with k6/artillery (topic 13)
- Cost & complexity honesty: don't reach for WebSockets when SSE or even polling would do

---

## 3. Hands-on labs

> Code in `labs/09_realtime/`. Reuse **redis** as the backplane; reuse the nginx LB from topic 01.

**Lab 1 — Three ways to do the same thing.**
A "live todo count" feature implemented as: short polling, SSE, and WebSocket. Compare code
complexity, latency, and network traffic (devtools). Write the decision table from §2.1 in your own words.

**Lab 2 — SSE job progress (connects to topic 08).**
Stream the heavy-job progress from topic 08's Lab 5 to the browser via SSE instead of polling.
Handle reconnection with `Last-Event-ID`. Note how little code this takes vs WebSockets.

**Lab 3 — WebSocket chat, single server.**
A room-based chat in the todo-app (e.g., per-project comments live). Message envelope, join/leave,
broadcast to room. Authenticate the connection with a short-lived ticket (not a header) — apply topic 07.

**Lab 4 — Break it with two servers (the key lab).**
Run 2 app replicas behind the nginx LB. Open two browsers; observe they land on different replicas
and **can't see each other's messages**. This is the scaling problem, live. Then fix it with a
**Redis pub/sub backplane** so every replica forwards room messages. Re-test — messages cross replicas.

**Lab 5 — Durability with Streams.**
Redis pub/sub loses messages if a replica is briefly down. Switch the backplane to Redis Streams
with consumer groups; implement "replay messages since last id" on reconnect. Prove a client that
disconnects and reconnects gets the messages it missed.

**Lab 6 — Presence + the flap problem.**
Online/offline presence per project using heartbeats + Redis TTL keys. Simulate a flaky
connection (drop/reconnect every few seconds) and fix the on/off flapping with a grace period.

**Lab 7 — Graceful deploy of live sockets.**
With clients connected across 2 replicas, do a rolling restart. Observe dropped connections;
implement client reconnect-with-jittered-backoff and a server drain signal. Prove no reconnect storm.

**Lab 8 — Web Push (bonus).**
Register a service worker + VAPID, send a web push notification when a todo is assigned while the
tab is closed. Wire it as a topic-08 background consumer.

---

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| WebSockets behind nginx | **API Gateway WebSocket APIs** | Managed connections + routes; `@connections` API to push |
| SSE / long-lived HTTP | ALB (sticky) → ECS/EKS | ALB supports WS/SSE with idle-timeout tuning |
| Redis pub/sub backplane | **ElastiCache Redis pub/sub** | Same code; or... |
| Durable backplane (Streams) | **MSK / Kinesis** | When you need replay at scale (topic 11) |
| Presence TTL keys | ElastiCache | Same pattern |
| Web Push / APNs / FCM fan-out | **SNS mobile push** | Managed fan-out to APNs/FCM/Web Push |
| Connection state store | DynamoDB (connectionId table) | The standard API-GW-WebSocket pattern |

---

## 5. Mini-project — "Realtime, multi-server todo collaboration"

In `labs/09_realtime/`, make the todo-app collaborative and multi-replica-correct:

1. Live updates: when anyone in a tenant/project changes a todo, all connected members see it instantly
2. Runs correctly across **2+ replicas** behind the LB via a Redis backplane (Streams for durability)
3. Presence: who's currently viewing each project, with flap-proof heartbeats
4. Job progress (topic 08's heavy job) streamed live to the UI
5. WS auth via short-lived tickets; subscription authorization per tenant/project (topic 07)
6. Graceful deploy: rolling restart with client reconnect + missed-message replay, no storm
7. **`REALTIME.md`**: chosen transport per feature and why, the backplane design, the scaling
   math (connections/node), and the failure-mode analysis (replica dies, Redis dies, deploy, slow client)

Done = two browsers on two different replicas collaborate seamlessly, survive a rolling deploy, and catch up on reconnect.

---

## 6. Self-check — you're done when you can…

1. Choose polling vs long-polling vs SSE vs WebSockets for five features and defend each.
2. Explain the SSE wire format and how browser auto-reconnect + `Last-Event-ID` work.
3. Explain the WebSocket upgrade handshake and how it relates to plain HTTP from topic 01.
4. Explain exactly why a single-server WebSocket chat breaks at two replicas — and draw the backplane fix.
5. Contrast Redis pub/sub vs Redis Streams for a backplane and say when the durability matters.
6. Design channel/topic naming for per-user, per-room, and per-tenant fan-out.
7. Explain how you authenticate and authorize a WebSocket connection and why the token-in-query-string approach is risky.
8. Explain presence with heartbeats + TTL and how you stop on/off flapping.
9. Explain the reconnect-storm failure mode and how jittered backoff + draining prevent it.
10. Explain the difference between in-app realtime and OS push, and sketch a notification service architecture.

---

## 7. Resources

- **MDN — Server-Sent Events & WebSockets guides** — the canonical client-side references
- **Ably & Ably's "WebSockets vs SSE vs Long Polling" articles** — best vendor-neutral scaling writeups (they run this for a living)
- **"Scaling WebSockets" talks/posts (Figma, Slack, Discord engineering blogs)** — real multi-replica backplane war stories
- **Redis docs — Pub/Sub & Streams** — the backplane primitives
- **web.dev — Web Push notifications + MDN Push API / VAPID** — for §2.7 and Lab 8
- **Starlette WebSocket & FastAPI WebSocket docs** — the implementation surface
- **RFC 6455 (WebSocket protocol)** — reference for frames/close codes when debugging
