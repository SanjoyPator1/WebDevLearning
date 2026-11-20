# 01 The Node.js Runtime for Nest Developers

> **Topic 0.1** | Priority: Core | Prerequisites: none (you know Node already, so this is the sharp-edges version) | Time: 3 to 4 hours | Exercise: none, but every demo below is runnable | Next: [02 TypeScript Refresher](02_typescript_refresher.md)
>
> Every output in this doc was produced by running the code on macOS with Node v24.11.1 unless a different version is named. Other versions were installed with nvm 0.40.3 and selected per command with `nvm exec`: v22.11.0, v22.23.5, v24.22.3 and v26.13.1. Anything not run is marked "Not verified".

## Table of Contents

- [Why This Matters for Nest](#why-this-matters-for-nest)
- [The Mental Model](#the-mental-model)
  - [One Thread, Many Waiters](#one-thread-many-waiters)
  - [What Runs Where](#what-runs-where)
- [The Event Loop](#the-event-loop)
  - [The Phases](#the-phases)
  - [Microtasks, nextTick and the Ordering Experiment](#microtasks-nexttick-and-the-ordering-experiment)
  - [Starving the Loop](#starving-the-loop)
  - [Timers and Immediates](#timers-and-immediates)
- [What Blocking Does to In-Flight Requests](#what-blocking-does-to-in-flight-requests)
  - [The Experiment](#the-experiment)
  - [The Thread Pool](#the-thread-pool)
  - [What to Do About It](#what-to-do-about-it)
- [Promises and Errors](#promises-and-errors)
  - [How a Rejection Becomes a Crash](#how-a-rejection-becomes-a-crash)
  - [Where This Meets Nest](#where-this-meets-nest)
- [Streams and Backpressure](#streams-and-backpressure)
- [Scaling Beyond One Thread](#scaling-beyond-one-thread)
  - [worker_threads](#worker_threads)
  - [cluster](#cluster)
  - [Horizontal Scaling](#horizontal-scaling)
  - [Choosing Between Them](#choosing-between-them)
- [AsyncLocalStorage](#asynclocalstorage)
- [ESM and CommonJS](#esm-and-commonjs)
  - [The Differences That Bite](#the-differences-that-bite)
  - [require of ESM Across Versions](#require-of-esm-across-versions)
  - [Globals, import.meta.dirname and .js Extensions](#globals-importmetadirname-and-js-extensions)
  - [Node Runs TypeScript Directly](#node-runs-typescript-directly)
- [Node Release and LTS Policy](#node-release-and-lts-policy)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why This Matters for Nest

Nest is a structure and dependency-injection layer. It does not change how Node executes your code. Everything below the controller, which is the event loop, the thread pool, promise handling and the module system, is plain Node. Most "Nest is slow" and "Nest crashed in production" stories are Node stories:

- One synchronous loop in a handler stalls **every** in-flight request on that process.
- A promise nobody awaited can kill the whole process.
- A request-scoped context (user, tenant, trace ID) cannot live in a global variable, and that is exactly what `AsyncLocalStorage` solves (topic 10.3).
- Nest 12's packages are ESM, so how Node loads ESM from CommonJS decides whether an app boots at all.

You know Node. This doc is about the parts a senior interviewer pokes at, each backed by an experiment.

---

## The Mental Model

### One Thread, Many Waiters

A Node process runs your JavaScript on **one thread**. Concurrency comes from never waiting on that thread: you start an operation (a socket read, a file read, a timer), hand it to the operating system or a helper thread, and register a callback. When the result is ready the callback is queued, and the single JavaScript thread runs it when it is free.

```text
            your JavaScript (ONE thread)
                      │ starts operations, never waits
        ┌─────────────┼───────────────────┐
        ▼             ▼                   ▼
   OS kernel      libuv thread pool    timers
 (sockets, via    (fs, dns lookup,     (min-heap)
  epoll/kqueue)    crypto, zlib)
        │             │                   │
        └─────────────┴───────────────────┘
                      │ completed work becomes callbacks in queues
                      ▼
               event loop picks the next callback
```

The consequence for a server: a request handler is cheap while it awaits I/O, because the thread is free to serve other requests. It is expensive while it computes, because nothing else runs.

### What Runs Where

| Work | Where it runs | Does it block the JS thread |
|---|---|---|
| Your JavaScript, `JSON.parse`, regexes, loops | The main thread | Yes, for its whole duration |
| Network I/O (sockets, HTTP) | The OS, through the event loop | No |
| `fs`, `dns.lookup`, `crypto.pbkdf2`, `zlib` (async forms) | The libuv thread pool (4 threads by default) | No, but the pool is shared and finite |
| `fs.readFileSync` and every other `*Sync` call | The main thread | Yes |
| `worker_threads` code | A separate thread with its own event loop | No |

---

## The Event Loop

### The Phases

Each trip around the loop visits these phases in order:

```text
   ┌───────────────────────────┐
┌─>│          timers           │  setTimeout and setInterval callbacks that are due
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │     pending callbacks     │  some deferred system callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │       idle, prepare       │  internal use
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           poll            │  wait for I/O, run I/O callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           check           │  setImmediate callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
└──┤     close callbacks       │  socket.on('close') and similar
   └───────────────────────────┘

 Between callbacks: the process.nextTick queue, then the promise microtask queue.
```

Two queues sit outside the phases: the `process.nextTick` queue and the promise microtask queue. Both are drained after the current operation finishes and before the loop moves on.

### Microtasks, nextTick and the Ordering Experiment

This script schedules one of everything. The labels say what each line is, not what you expect:

```js
// order.mjs
import fs from 'node:fs';
console.log('sync: start');
setTimeout(() => console.log('timeout 0'), 0);
setImmediate(() => console.log('immediate'));
process.nextTick(() => console.log('nextTick'));
Promise.resolve().then(() => console.log('promise.then'));
queueMicrotask(() => console.log('queueMicrotask'));
fs.readFile(import.meta.filename, () => {
  console.log('fs.readFile callback');
  setTimeout(() => console.log('  timeout 0 scheduled inside I/O callback'), 0);
  setImmediate(() => console.log('  immediate scheduled inside I/O callback'));
});
(async () => { console.log('sync: async function body before first await'); await null; console.log('async function after await'); })();
console.log('sync: end');
```

Real output as an ES module (`node order.mjs`, v24.11.1):

```text
sync: start
sync: async function body before first await
sync: end
promise.then
queueMicrotask
async function after await
nextTick
timeout 0
immediate
fs.readFile callback
  immediate scheduled inside I/O callback
  timeout 0 scheduled inside I/O callback
```

The same code as CommonJS (`require` instead of `import`, `__filename` instead of `import.meta.filename`):

```text
sync: start
sync: async function body before first await
sync: end
nextTick
promise.then
queueMicrotask
async function after await
timeout 0
immediate
fs.readFile callback
  immediate scheduled inside I/O callback
  timeout 0 scheduled inside I/O callback
```

What to take from it:

1. **An `async` function runs synchronously until its first `await`.** The log line before the `await` appears between the two `sync:` lines. Code after the `await` is a microtask.
2. **All synchronous code finishes first**, then microtasks, then the loop proper (timers, I/O, check).
3. **`nextTick` versus promises depends on the module system.** In CommonJS, `nextTick` ran before the promise callbacks. In an ES module it ran **after** them. The folk rule "nextTick always beats promises" is true only in CommonJS main-module code. Our reading of why (not verified): an ES module is itself evaluated inside promise machinery, so the microtask queue is already draining when `nextTick` is queued. Do not write code that depends on this order.
4. **Inside an I/O callback, `setImmediate` always ran before `setTimeout(…, 0)`.** That is the one deterministic pair, because the loop goes from the poll phase straight to the check phase.
5. The order was identical on v22.23.5, v24.11.1 and v26.13.1 except for the `timeout 0` versus `immediate` pair in the main module, which is next.

### Starving the Loop

Microtasks are drained completely before the loop continues, and a microtask can queue another microtask. So a microtask chain can starve everything else:

```js
let n = 0;
setTimeout(() => console.log('timer finally ran after', n, 'microtasks'), 0);
function spin() { if (n++ < 2_000_000) queueMicrotask(spin); }
spin();
```

```text
timer finally ran after 2000001 microtasks
```

A `setTimeout(…, 0)` waited for two million microtasks. A recursive `Promise.resolve().then(...)` loop that never ends would block timers and I/O forever, with no `while (true)` in sight. `process.nextTick` recursion does the same thing.

### Timers and Immediates

From the main module, the order of `setTimeout(…, 0)` and `setImmediate` is **not guaranteed**, and we saw it vary:

| Script | Runs | Result |
|---|---|---|
| `order.mjs` on v24.11.1 | 10 | timeout first 9 times, immediate first once |
| minimal two-line script on v22.23.5 | 20 | immediate first 19 times, timeout first once |
| same on v24.11.1 | 20 | immediate first 20 times |
| same on v26.13.1 | 20 | immediate first 19 times, timeout first once |

Whether the 1 ms timer is due when the loop first checks depends on how long startup took. Never rely on it.

---

## What Blocking Does to In-Flight Requests

### The Experiment

One HTTP server, four routes. `/fast` replies immediately. The other three each take 2 seconds, but in different ways:

```js
// block_server.mjs (shortened)
function cpuBurn(ms) { const end = Date.now() + ms; let x = 0; while (Date.now() < end) x++; }

http.createServer(async (req, res) => {
  if (req.url === '/fast') return res.end('fast\n');
  if (req.url === '/block') { cpuBurn(2000); return res.end('blocked 2s\n'); }               // CPU on the main thread
  if (req.url === '/async-wait') { await new Promise(r => setTimeout(r, 2000)); return res.end('waited 2s\n'); }  // waiting, no CPU
  if (req.url === '/worker') { await runInWorker(cpuBurn, 2000); return res.end('worker 2s\n'); }  // CPU on another thread
}).listen(4100);
```

A probe starts the slow request, waits 200 ms, then asks for `/fast` and times it:

```text
async-wait  -> /fast issued 200ms later took   17 ms; slow request took 2023 ms
block       -> /fast issued 200ms later took 1804 ms; slow request took 2018 ms
worker      -> /fast issued 200ms later took    4 ms; slow request took 2034 ms
```

Read it carefully:

- All three slow requests took about 2 seconds. From the slow client's point of view they are identical.
- **`/block` made an unrelated `/fast` request wait 1804 ms**: the remaining part of the 2-second spin. One handler's CPU work was a 1.8 second outage for everyone else on the process.
- `/async-wait` took the same 2 seconds but cost other requests nothing, because the thread was free while waiting.
- `/worker` did the same CPU work and `/fast` took 4 ms, because the work ran on another thread.

The numbers are from a single run on one machine. The relative sizes are the lesson. This is why "Node is single-threaded" is a statement about **CPU work**, not about waiting.

### The Thread Pool

Async `fs`, `crypto`, `zlib` and `dns.lookup` calls run on libuv's thread pool, which has **4 threads** by default. The pool is shared by everything in the process. Eight async `pbkdf2` calls started at once:

```text
UV_THREADPOOL_SIZE = (unset, default 4) | completion times (ms, rounded to 100): 200 200 200 200 400 400 400 400
UV_THREADPOOL_SIZE = 8 | completion times (ms, rounded to 100): 100 100 100 100 100 100 100 200
```

With 4 threads, the calls finish in two waves of four. With 8 threads they mostly finish together. The practical risk: a burst of file or crypto work queues behind itself, and since DNS lookups use the same pool, an unrelated outbound HTTP call can be delayed by it. Set `UV_THREADPOOL_SIZE` before the process starts, not from inside the program (we only tested the environment variable).

### What to Do About It

| Situation | Fix |
|---|---|
| A CPU-heavy handler (image resize, large JSON transform, hashing a big file) | Move it to a worker thread or a queue worker (topics 7.3, 11.1). |
| A `*Sync` call in a request path | Use the async form. `*Sync` is acceptable at startup only. |
| A very large `JSON.parse` or `JSON.stringify` | Limit body size, or stream and parse in pieces. |
| A catastrophic regular expression | Validate input length first. Not tested here. |
| A suspected stall | Measure event loop delay in production (topic 11.1). |

---

## Promises and Errors

### How a Rejection Becomes a Crash

A rejected promise that has no handler by the time the microtask queue drains is an **unhandled rejection**. Since Node 15 the default is to treat it like an uncaught exception: print the error and exit with code 1. We checked six cases on v24.11.1 and recorded the exit code of each:

| Case | Exit code | What happened |
|---|---|---|
| `Promise.reject(new Error('boom'))` with no handler | 1 | Crashed. A timer set for 100 ms later never fired. |
| Same, but a `.catch` is attached 50 ms later | 1 | **Still crashed.** Attaching a handler late does not rescue it. |
| `process.on('unhandledRejection', …)` registered | 0 | Hook ran, process stayed alive. |
| An `async` function that throws, called without `await` or `.catch` | 1 | Crashed. |
| An `async` listener on an `EventEmitter` that throws | 1 | Crashed. `emit` does not await or observe the returned promise. |
| `node --unhandled-rejections=warn` with a bare rejection | 0 | Printed `UnhandledPromiseRejectionWarning`, and the timer ran. |

Rules that follow:

1. **Every promise needs an owner**: `await` it, return it, or attach `.catch`. This is exactly what the scaffold's lint rule `typescript/no-floating-promises` enforces (see [05 Tooling and Setup](05_tooling_and_setup.md)).
2. **Async functions passed where a callback is expected hide their rejections.** Event emitters, `setTimeout` callbacks and array `forEach` all ignore the returned promise.
3. **An `unhandledRejection` hook is for logging before dying, not for carrying on.** After an unknown failure the process state is not trustworthy. Log, flush, and let the supervisor (Kubernetes, systemd) restart it. Topic 2.8 covers graceful shutdown.
4. **`--unhandled-rejections=warn` hides bugs.** It exists for legacy code.

### Where This Meets Nest

Nest turns an error thrown inside an `await`ed handler into an HTTP response through its exception layer (topic 1.9). That cannot help with a promise you started and did not await: the handler has already returned, and nobody is listening. We did not run this inside a Nest app (Not verified), but it follows directly from the demos above. Treat "fire and forget" calls in services as a bug unless they are explicitly caught.

---

## Streams and Backpressure

A producer that is faster than its consumer fills memory. Streams solve this with **backpressure**: `writable.write()` returns `false` when its internal buffer is above the `highWaterMark`, which means "stop writing until `drain`".

Three ways to move 2000 chunks of 64 KiB (about 125 MB) into a slow writable:

```js
const chunk = Buffer.alloc(64 * 1024), TOTAL = 2000;
const slowSink = () => new Writable({ highWaterMark: 64 * 1024, write(_c, _e, cb) { setTimeout(cb, 0); } });

// A: ignore the return value of write()
for (let i = 0; i < TOTAL; i++) w.write(chunk);

// B: respect backpressure by hand
for (let i = 0; i < TOTAL; i++) { if (!w.write(chunk)) await once(w, 'drain'); }

// C: let pipeline() do B for you
await pipeline(source, w);
```

```text
A ignore write() result : 125.0 MB buffered in memory after the loop
B await drain           : peak 0.0 MB buffered | write() returned false 2000 times
C pipeline()            : peak 0.1 MB buffered (source + sink)
```

Case A copied the whole payload into memory before the sink had consumed any of it. In B and C memory stayed near zero. (B's `write()` returned `false` every time because each chunk is exactly the high water mark.)

Rules of thumb:

- Use `stream/promises` `pipeline()`. It propagates errors and destroys every stream on failure; `a.pipe(b)` does not.
- Never `readFile` a large file into a buffer to send it. Stream it.
- Node's HTTP request and response objects are streams. Piping a file into `res` through `pipeline` gets backpressure for free.
- Nest's `StreamableFile` and file-upload handling are built on this (topic 3.7).

---

## Scaling Beyond One Thread

### worker_threads

A worker is a separate thread with its own event loop and V8 heap. Use it for CPU work. Data you send is **copied** (structured clone) unless you share memory explicitly:

```js
const shared = new SharedArrayBuffer(4); const view = new Int32Array(shared);
const copied = { n: 0 };
const w = new Worker(new URL(import.meta.url), { workerData: { shared, copied } });
// in the worker: Atomics.add(new Int32Array(workerData.shared), 0, 5); workerData.copied.n = 99;
w.on('exit', () => console.log('main sees shared counter =', Atomics.load(view, 0), '| main sees copied.n =', copied.n));
```

```text
main sees shared counter = 5 | main sees copied.n = 0
```

The worker's change to the `SharedArrayBuffer` is visible; its change to the plain object touched only its own copy. Starting a worker costs real time and memory, so use a pool for repeated work, not one worker per request. Worker libraries such as Piscina are common; we did not test any here.

### cluster

`cluster` forks several **processes** that share one listening port. Three workers, 30 requests sent with `Connection: close`:

```text
availableParallelism: 11 | primary pid is a different pid from the workers
distinct worker pids that answered 30 requests: 3 | counts: 10, 10, 10
```

The primary distributed connections round-robin (10 each). Each worker is a separate process, so **in-memory state is per process**: a counter, a cache or a rate limiter held in a variable exists three times. That is the same constraint as running three replicas.

### Horizontal Scaling

Running more copies of the process on more machines or containers is the same idea as `cluster` with a load balancer instead of the primary process. It is the scaling model Kubernetes uses. It forces the right habits: no shared in-memory state, stateless handlers, shared stores (Redis, the database) for anything that must be consistent.

### Choosing Between Them

| | worker_threads | cluster | Separate containers or replicas |
|---|---|---|---|
| Unit | Thread | Process | Process on any host |
| Memory | Own heap, can share buffers | Fully separate | Fully separate |
| Best for | CPU-heavy tasks inside one request | Using all cores of one machine | Real scale and fault isolation |
| Failure | A worker can crash alone | A worker can crash alone | One replica can crash alone |
| Operational cost | Pooling code | Little | Orchestration |

Rule of thumb for a Nest service: scale **out** with replicas, use worker threads or queue workers for CPU-bound work, and treat `cluster` as a minor optimization when you are not on an orchestrator. Topic 11.3 covers deployment.

---

## AsyncLocalStorage

`AsyncLocalStorage` gives you a store that follows the **asynchronous call chain**, not a variable's scope. It is the way to carry a request ID, user or tenant down through awaits without passing it as a parameter.

```js
import { AsyncLocalStorage } from 'node:async_hooks';
const als = new AsyncLocalStorage();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (msg) => console.log(`[req ${als.getStore()?.id ?? 'none'}] ${msg}`);

async function deepService() { await sleep(Math.random() * 30); log('deep in the call stack, no params passed'); }
async function handle(id) { await als.run({ id }, async () => { log('start'); await deepService(); await sleep(10); log('end'); }); }

await Promise.all([handle('A'), handle('B'), handle('C')]);
log('outside run()');
```

```text
[req A] start
[req B] start
[req C] start
[req A] deep in the call stack, no params passed
[req B] deep in the call stack, no params passed
[req C] deep in the call stack, no params passed
[req A] end
[req B] end
[req C] end
[req none] outside run()
```

Three interleaved calls kept three separate contexts across `await`s and timers, and outside `run()` the store is empty. A global variable would have been overwritten by whichever request ran last.

One caveat we tested. `EventEmitter` listeners run in the context of whoever calls `emit`, **not** of whoever registered them:

```js
als.run({ id: 'listener-owner' }, () => ee.on('ping', () => log('listener runs')));
als.run({ id: 'emitter-caller' }, () => ee.emit('ping'));
```

```text
[req emitter-caller] listener runs
```

If you need the registering context, capture it explicitly.

Why Nest developers care: Nest's request-scoped providers (topic 2.4) build a new object graph per request, which costs performance. `AsyncLocalStorage` gives you per-request state with a singleton graph. The v10.0.0 release notes list "Support async local storage in interceptors" (PR #11142), and the official docs have an Async local storage recipe. Libraries such as `nestjs-cls` wrap it (topic 10.3). Do not build large amounts of logic on it before reading that topic.

---

## ESM and CommonJS

### The Differences That Bite

| | CommonJS | ES modules |
|---|---|---|
| Syntax | `require`, `module.exports` | `import`, `export` |
| Loading | Synchronous | Asynchronous graph, evaluated in dependency order |
| Top-level `await` | Not available | Available |
| `__dirname`, `__filename`, `require` | Defined | **Not defined** |
| Relative import specifiers | Extension optional | **Extension required** |
| Strict mode | Opt-in | Always on |
| Bindings | A copy of `module.exports` | Live bindings |
| How Node decides | `.cjs`, or `.js` without `"type": "module"` | `.mjs`, or `.js` with `"type": "module"` |

Nest 12's own packages are ESM only, and the scaffold project is ESM too (`"type": "module"` in `package.json`).

### require of ESM Across Versions

Historically `require()` could not load an ES module and threw `ERR_REQUIRE_ESM`. Modern Node allows it for synchronous graphs. This is how Nest 12 supports CommonJS applications even though its packages are ESM. We ran one test file on five versions:

```js
const lib = require('./esm-lib.mjs');        // export const answer = 42; export default function hello() {...}
require('./esm-tla.mjs');                    // an ES module that uses top-level await
```

| Node | `require()` of a normal ES module | `require()` of a module with top-level `await` |
|---|---|---|
| v22.11.0 | **Fails** with `ERR_REQUIRE_ESM` | `ERR_REQUIRE_ESM` |
| v22.23.5 | Works | `ERR_REQUIRE_ASYNC_MODULE` |
| v24.11.1 | Works | `ERR_REQUIRE_ASYNC_MODULE` |
| v24.22.3 | Works | `ERR_REQUIRE_ASYNC_MODULE` |
| v26.13.1 | Works | `ERR_REQUIRE_ASYNC_MODULE` |

Details observed:

- The namespace object returned on every version that worked had the keys `[ '__esModule', 'answer', 'default' ]`. Node adds `__esModule` when the module has a default export, so `lib.default()` is how you call it.
- **No warning was printed** on stderr by v22.11.0, v22.23.5 or v24.22.3 in our runs.
- The line between "fails" and "works" falls between 22.11.0 and 22.23.5. The v12.0.0 release notes put Nest 12's floor at Node 20.19+ or 22.12+ because both `require(esm)` and the ESM packages depend on it. We verified the two ends (22.11.0 fails, 22.23.5 works) but not v22.12.0 itself.
- A graph containing top-level `await` cannot be `require`d, because `require` is synchronous. That is the `ERR_REQUIRE_ASYNC_MODULE` the v12 migration guide mentions for Jest on Node versions older than 24.9 (topic 0.5).
- AWS Lambda disables `require(esm)` on its Node 20, 22 and 24 runtimes according to the same guide (Not verified here).

### Globals, import.meta.dirname and .js Extensions

In an ES module:

```text
typeof __dirname    : undefined
typeof require      : undefined
import.meta.dirname : demos/cjsesm        (path shortened)
import.meta.filename: cjsesm/esmglobals.mjs
createRequire works : function
```

- Use `import.meta.dirname` and `import.meta.filename`. We confirmed `import.meta.dirname` exists on v22.11.0, v22.23.5 and v24.22.3.
- If you truly need `require` (for example to load a CommonJS-only package or JSON), build one: `createRequire(import.meta.url)` from `node:module`.
- **Relative imports need the extension**, and TypeScript projects write `.js` even though the source file is `.ts`: `import { AppService } from './app.service.js'`. TypeScript with `module: nodenext` maps it back at compile time. This is why every import in the Nest 12 scaffold ends in `.js` (see [05 Tooling and Setup](05_tooling_and_setup.md)).
- Importing CommonJS from ESM works, and `import()` works from CommonJS. The interop edge is default exports, which is why `esModuleInterop` is on.

### Node Runs TypeScript Directly

Node can run `.ts` files with the types stripped out. We tested a file that has only type annotations and an `interface`:

| Node | `node file.ts` |
|---|---|
| v22.11.0 | Fails: `ERR_UNKNOWN_FILE_EXTENSION` |
| v22.23.5 | Runs |
| v24.11.1, v24.22.3, v26.13.1 | Run |

It strips types and nothing else, so syntax that needs generated code fails: an `enum` produced `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` ("TypeScript enum is not supported in strip-only mode") on v24.11.1. Node also ignores `tsconfig.json`. Nest cannot use this, because constructor injection depends on decorator metadata that needs a real compile step (topics 0.2 and 0.3).

---

## Node Release and LTS Policy

Facts from nodejs.org's release index (`https://nodejs.org/dist/index.json`), fetched 2026-11-20:

| Line | First release | Status | Latest release in the index |
|---|---|---|---|
| Node 20 "Iron" | earlier | End of life 2026-04-30 | v20.20.2 (2026-03-24) |
| Node 22 "Jod" | 2024-04-24 | Maintenance LTS, security fixes only | v22.23.5 (2026-11-11) |
| Node 24 "Krypton" | 2025-05-06 | LTS | v24.22.3 (2026-11-10) |
| Node 25 | earlier | Odd-numbered release, never LTS | v25.9.0 (2026-03-31) |
| Node 26 "Lithium" | 2026-05-05 | **LTS since 2026-10-28** (v26.13.0 was the first LTS release) | v26.13.1 (2026-11-10) |

The end-of-life dates (Node 20: 2026-04-30; Node 22: 2027-04-30; Node 24: 2028-04-30; Node 26: 2029-04-30) come from search results summarizing the Node.js release schedule, not from the index file, so treat them as Not verified against nodejs.org itself.

**The new cadence.** Sources we found report that starting with Node 27 the project moves to **one major release per year**, in April, with LTS promotion the following October and no more odd/even split. This was reported by search summaries (InfoQ, June 2026) and not independently verified, but it matches the schedule shape above.

What to do:

- **New projects: develop on the newest LTS** (Node 24 or 26) and use the same major in CI and production images.
- **Do not start on Node 20.** It is past end of life even though Nest 12 still runs on 20.19.
- **Nest 12's floors are not one number**: running an app needs 20.19+ or 22.12+, but the CLI's schematics need 22.22.3+, 24.15+ or 26+ (see [05 Tooling and Setup](05_tooling_and_setup.md)).
- **Production images pin the major and the OS**, for example `node:24-slim`. A moving `node:latest` tag is not a deployment policy.
- **Pin the version for humans** with `.nvmrc` and `engines` (topic 0.5).

---

## Common Pitfalls

- **One sync call in a hot path.** `fs.readFileSync`, `crypto.pbkdf2Sync`, a large `JSON.parse`, a CPU loop. It stalls every other request on the process, as the 1804 ms stall showed.
- **Unawaited promises.** Crash on default settings, silently lost on others. Turn on `no-floating-promises`.
- **Async callbacks to APIs that ignore promises**: `forEach(async …)`, event emitter listeners, timers.
- **Treating `nextTick` order as a rule.** It differs between CommonJS and ESM.
- **Relying on `setTimeout(…, 0)` versus `setImmediate` order** outside an I/O callback.
- **Module-level mutable state** in a multi-process or multi-replica deployment. Each process has its own copy.
- **Global variables for request context.** Use `AsyncLocalStorage`, or request-scoped providers if you must (topics 2.4 and 10.3).
- **`__dirname` in ESM.** It is undefined; use `import.meta.dirname`.
- **A relative import with no `.js`** under `nodenext`.
- **Ignoring `write()`'s return value** when copying large data.
- **Thinking the thread pool is infinite.** It has 4 threads unless you change it.
- **`unhandledRejection` as a safety net.** Log and exit.

---

## Interview Questions

**Q1. Node is single-threaded. How does it handle thousands of concurrent connections?**
The JavaScript runs on one thread, but waiting does not use it. Sockets are handled by the operating system (epoll or kqueue) through the event loop, file and crypto work runs on the libuv thread pool, and each completion becomes a callback queued for the main thread. Concurrency here means many operations in flight, not many things executing at the same instant. The limit is CPU work on the main thread.

**Q2. List the event loop phases and say where `setTimeout`, `setImmediate` and I/O callbacks run.**
Timers, pending callbacks, idle and prepare, poll, check, close callbacks. `setTimeout` and `setInterval` run in timers, I/O callbacks in poll, `setImmediate` in check. Inside an I/O callback `setImmediate` always runs before `setTimeout(…, 0)`. From the main module the order is not guaranteed, and we saw it vary between runs.

**Q3. What is the difference between `process.nextTick`, a promise `then` and `setImmediate`?**
`nextTick` and promise callbacks are queued between operations and run before the loop moves to its next phase. `nextTick` has its own queue and promises use the microtask queue. `setImmediate` runs in the check phase of a later loop turn. In CommonJS main code we saw `nextTick` first, then promises. In an ES module the promises ran first.

**Q4. Can microtasks block the event loop?**
Yes. The microtask queue is drained completely, including microtasks queued by microtasks. We ran two million chained microtasks and a `setTimeout(…, 0)` waited for all of them. An endless promise chain starves timers and I/O.

**Q5. A Nest endpoint sometimes takes 2 seconds and, while it runs, other endpoints become slow too. Why, and how do you fix it?**
The handler is doing synchronous CPU work on the main thread, so no other request can run until it finishes. In our experiment an unrelated request took 1804 ms behind a 2-second loop and 17 ms behind a 2-second `await`. The fix is to take the CPU work off the thread: a worker thread (our test: 4 ms), a queue worker, or a separate service. Confirm it with an event loop delay metric.

**Q6. What happens if a promise is rejected and nobody handles it?**
On default settings, Node prints the error and exits with code 1, the same as an uncaught exception. We saw that attaching a `.catch` 50 ms later does not save it. A hook on `unhandledRejection` prevents the exit, but the process is in an unknown state, so use it to log and then shut down.

**Q7. What is backpressure and what happens if you ignore it?**
It is the signal from a slow consumer to a fast producer. `write()` returns `false` when the buffer is over `highWaterMark`; the producer should wait for `drain`. Ignoring it buffers everything in memory: we wrote 125 MB in a loop and all of it sat in memory, versus 0.1 MB with `pipeline()`. `pipeline()` handles it and cleans up on errors.

**Q8. When do you use `worker_threads`, `cluster` and multiple replicas?**
Worker threads for CPU-bound tasks within a request (separate heap, optional shared memory). `cluster` to use all cores of one host with a shared port, as separate processes. Replicas behind a load balancer for real scale and fault isolation. For a Nest service, scale out with replicas and move heavy CPU work to workers or queues. In all process-based options, in-memory state is per process.

**Q9. What problem does `AsyncLocalStorage` solve, and what are its limits?**
It keeps a store that follows the async call chain, so you can carry request context without passing parameters or creating request-scoped providers. We ran three interleaved requests and each kept its own context across awaits. Limits: the store is empty outside `run()`, and an `EventEmitter` listener runs in the emitter's context, not the registrant's.

**Q10. Why does `require` of an ES module work on Node 22.23 and fail on 22.11?**
`require(esm)` was added and enabled by default in later releases (the Nest 12 floor is 22.12+). We saw `ERR_REQUIRE_ESM` on v22.11.0 and success on v22.23.5. It only works for synchronous module graphs. A module with top-level `await` fails with `ERR_REQUIRE_ASYNC_MODULE` on every version we tried.

**Q11. What changes when a project is `"type": "module"`?**
`.js` files are ES modules: `__dirname`, `__filename` and `require` are undefined (use `import.meta.dirname` and `createRequire`), relative imports need extensions (`.js` even for TypeScript sources), strict mode is always on, and top-level `await` is allowed.

**Q12. Which Node version would you choose for a new Nest 12 service today, and why?**
The newest LTS that your platform supports, Node 24 or Node 26. Node 20 is past end of life. The Nest CLI schematics need 22.22.3+, 24.15+ or 26+, and running the app needs 20.19+ or 22.12+. Use the same major in development, CI and the production image, and pin it with `.nvmrc`, `engines` and the Docker tag.

---

## Check Yourself

- [ ] I can draw the event loop phases and place timers, I/O callbacks, `setImmediate`, `nextTick` and promises on them.
- [ ] I can predict the output of a script that mixes `nextTick`, promises, timers and immediates, and I know which parts are not guaranteed.
- [ ] I can explain why one sync loop made an unrelated request take 1804 ms, and why `await` did not.
- [ ] I know the four rules for promises: await, return, catch, or lint it.
- [ ] I can show backpressure with `write()` returning `false`, and use `pipeline()`.
- [ ] I can choose between worker threads, cluster and replicas, and say what state each one shares.
- [ ] I can write an `AsyncLocalStorage` example from memory and name its pitfall.
- [ ] I know what `require(esm)` does on which Node versions, and what `ERR_REQUIRE_ASYNC_MODULE` means.
- [ ] I know which Node line I will use and why, and where Node 20 stands.

---

## Further Reading

- [The Node.js event loop, timers and process.nextTick (official)](https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick)
- [Backpressuring in streams (official)](https://nodejs.org/en/learn/modules/backpressuring-in-streams)
- [Asynchronous context tracking, AsyncLocalStorage (official API)](https://nodejs.org/api/async_context.html)
- [ECMAScript modules (official API)](https://nodejs.org/api/esm.html)
- [Loading ECMAScript modules using require (official API)](https://nodejs.org/api/modules.html#loading-ecmascript-modules-using-require)
- [Worker threads (official API)](https://nodejs.org/api/worker_threads.html)
- [Cluster (official API)](https://nodejs.org/api/cluster.html)
- [Unhandled rejections mode (official CLI docs)](https://nodejs.org/api/cli.html#--unhandled-rejectionsmode)
- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
- [Release index used for the version table](https://nodejs.org/dist/index.json)
- [NestJS v10.0.0 release notes](https://github.com/nestjs/nest/releases/tag/v10.0.0): includes async local storage support in interceptors.
- [NestJS v12.0.0 release notes](https://github.com/nestjs/nest/releases/tag/v12.0.0): Node floors and ESM packages.
