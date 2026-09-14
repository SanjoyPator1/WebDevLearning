# Model Context Protocol — 2026-07-28, From Scratch

This folder replaces the earlier `03-model-context-protocol-mcp/`, which was written
against the 2025-era protocol and teaches a handshake that no longer exists. Nothing
here reuses it.

The subject is the **2026-07-28 revision** of MCP — the largest change since the
protocol launched, and the one that removed sessions from it entirely. We learn it by
building one thing: **cafe-mcp**, an MCP server that runs a coffee shop counter. Every
protocol feature is introduced because the café needs it, not because a spec section
exists.

## How this folder is meant to be used

Each topic is a pair: a notes chapter that explains the concept before any code exists,
then a small server you write yourself. You read `notes/NN-*.md` first, then open
`solutions/tNN_*.py`, which is a stub with the shape laid out and the interesting lines
left as `TODO`. When you are stuck or finished, `solved/tNN_*.py` holds a complete
working version with heavy print narration.

```text
notes/NN-topic.md         read this first  — theory, diagrams, dry-run
        |
        v
solutions/tNN_topic.py    you write this   — stub with TODOs
        |
        v
solved/tNN_topic.py       my version       — complete, printed, runnable
        |
        v
curl/NN_*.sh              prove it on the wire, by hand, with no SDK
```

The `curl/` scripts matter more than they look. MCP is a wire protocol, and almost every
misunderstanding people have about it comes from only ever seeing it through an SDK
client that hides the headers. Each script prints what it expects to see before it runs.

## Folder layout

```text
03-a-model-context-protocol-2026/
├── README.md                  this file — the map
├── SETUP.md                   environment, and how to check it is right
├── pyproject.toml             one dependency that matters: mcp[cli] v2
├── notes/                     one chapter per topic, theory first
├── solved/                    my complete code
│   ├── cafe_mcp/              the shared package, grows one module per topic
│   └── tNN_*.py               one runnable server per topic
├── solutions/                 YOUR code — same tree, stubs with TODOs
│   ├── cafe_mcp/
│   └── tNN_*.py
├── curl/                      one script per RPC, run against a live server
└── tests/                     pytest, no server process needed
```

`solved/` and `solutions/` are deliberately separate trees with the same shape, so you
can run either one and diff them.

## The ladder

### Part 0 — Foundations

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 00 | [What MCP actually is](notes/00-what-is-mcp.md) | Why a protocol beats hand-written tool glue, what JSON-RPC 2.0 is, and what the 2026-07-28 revision deleted |

### Part 1 — The wire

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 01 | [First server, and `server/discover`](notes/01-first-server-and-discover.md) | How a request is framed, what travels in `_meta`, why `stateless_http=True` is not the default, and how a client learns what a server can do without a handshake |
| 02 | [`tools/list`](notes/02-tools-list.md) | How a Python function becomes a JSON Schema the model reads, what annotations promise, and why deterministic ordering plus cache hints are worth money |
| 03 | [`tools/call`](notes/03-tools-call.md) | How arguments are validated, what `structuredContent` is for, the difference between `isError` and a JSON-RPC error, and why `ToolError` is the only exception you should raise on purpose |

### Part 2 — Data the model can read

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 04 | [Resources and templates](notes/04-resources.md) | Why a resource is not a tool, how a `{placeholder}` URI works, why cache hints suddenly matter, and why a failing resource read is a JSON-RPC `error` when a failing tool call is not |
| 05 | [Prompts and `completion/complete`](notes/05-prompts-and-completion.md) | How much a prompt's wording steers the model, why prompts are the one primitive with no error type, and how context-aware completion turns validation into prevention |

With topic 05, nine of the ten 2026-07-28 client methods are exercised. Only
`subscriptions/listen` is left — it waits for topic 11, because it is the one place where
everything else here stops being true.

### Part 3 — State without sessions

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 06 | [Pagination: the opaque cursor](notes/06-pagination.md) | The smallest instance of "state as a value, not server memory" — a cursor, versioned, validated, and readable by hand yet never meant to be hand-edited |
| 07 | [The order token](notes/07-the-order-token.md) | The same idea with real stakes: HMAC signing, domain separation via `kind`, timing-safe comparison, and why the token stores what was ordered, never what it cost |
| 08 | [MRTR: `input_required` and `requestState`](notes/08-mrtr.md) | How a server asks a question with zero server-to-client requests, why the SDK binds `requestState` to your arguments automatically, and what is genuinely left for you to protect that the automatic binding cannot see |
| 09 | [MRTR in URL mode](notes/09-url-mode.md) | Why sensitive consent needs a link instead of a form, how a nonce and a receipt do the correlating work a session would have done, and why `action: "accept"` is a claim, never proof |

### Part 4 — Streams

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 10 | [Progress on the response stream](notes/10-progress-and-streaming.md) | Why "streamable" HTTP means what it means, why progress reporting is entirely the client's opt-in, and why a dropped connection genuinely cancels the work rather than merely losing visibility into it |
| 11 | [`subscriptions/listen`](notes/11-subscriptions.md) | The one place statelessness genuinely leaks — proved with two real server processes, a listener on one, a change on the other, and silence |

With topic 11 every one of the ten 2026-07-28 client methods has been exercised somewhere
in this folder.

### Part 5 — Operations

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 12 | [Version negotiation with no handshake](notes/12-versions.md) | The difference between "known" and "modern" versions, why `server/discover` cannot serve as a universal bootstrap probe, and why `-32601` on that method can mean "wrong version" rather than "no discovery support" |

### Part 5, continued

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 13 | [Gateway headers, `Mcp-Param-*`, non-ASCII encoding](notes/13-param-headers.md) | How one tool argument gets mirrored into its own HTTP header for a gateway to route on, why a wrong-typed `x-mcp-header` fails with no error anywhere, and why non-ASCII cannot travel in a header at all without a base64 sentinel |

### Part 6 — the project

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 14 | [Three instances behind a round-robin proxy](notes/14-load-balancer.md) | Why the order token needed zero changes to survive three real processes, why the subscription fix is one constructor argument, and the backlog trade-off a shared-file bus introduces that an in-memory one cannot have |

| # | Topic | What you will be able to explain afterwards |
|---|-------|---------------------------------------------|
| 15 | [The assembled café, raw client vs SDK client](notes/15-the-project.md) | Everything `mcp.client.Client` automates that every earlier topic's raw client built by hand — the `_meta` envelope, header mirroring, SSE detection, version negotiation — and the one thing it will not do for you: answer an MRTR confirmation without an `elicitation_callback` |

The ladder is complete at fifteen topics.

## Status

| | Built | Notes | Solved code | Your stub | curl | Tests |
|---|---|---|---|---|---|---|
| 00 | yes | yes | — (theory only) | — | — | — |
| 01 | yes | yes | `solved/t01_hello.py` | `solutions/t01_hello.py` | 5 scripts | yes |
| 02 | yes | yes | `solved/t02_tools.py` | `solutions/t02_tools.py` | 3 scripts | yes |
| 03 | yes | yes | `solved/t03_calls_and_errors.py` | `solutions/t03_calls_and_errors.py` | 6 scripts | yes |
| 04 | yes | yes | `solved/t04_resources.py` | `solutions/t04_resources.py` | 6 scripts | yes |
| 05 | yes | yes | `solved/t05_prompts.py` | `solutions/t05_prompts.py` | 6 scripts | yes |
| 06 | yes | yes | `solved/t06_pagination.py` | `solutions/t06_pagination.py` | 6 scripts | yes |
| 07 | yes | yes | `solved/t07_order_token.py` | `solutions/t07_order_token.py` | 6 scripts | yes |
| 08 | yes | yes | `solved/t08_mrtr.py` | `solutions/t08_mrtr.py` | 6 scripts | yes |
| 09 | yes | yes | `solved/t09_url_mode.py` | `solutions/t09_url_mode.py` | 6 scripts | yes |
| 10 | yes | yes | `solved/t10_progress.py` | `solutions/t10_progress.py` | 4 scripts | yes |
| 11 | yes | yes | `solved/t11_subscriptions.py` | `solutions/t11_subscriptions.py` | 6 scripts | yes |
| 12 | yes | yes | `solved/t12_versions.py` | `solutions/t12_versions.py` | 4 scripts | yes |
| 13 | yes | yes | `solved/t13_param_headers.py` | `solutions/t13_param_headers.py` | 4 scripts | yes |
| 14 | yes | yes | `solved/t14_load_balancer.py` + `solved/loadbalancer.py` | `solutions/t14_load_balancer.py` | 2 scripts | yes |
| 15 | yes | yes | `solved/cafe_project.py` + `solved/raw_client.py` + `solved/sdk_client.py` | — (read, not written; see below) | — | yes |

Topic 15 has no `solutions/` stub. Like `solved/loadbalancer.py` and `solved/agent_client.py`
before it, its three files are meant to be *read* — the value is in the side-by-side
comparison between `raw_client.py` and `sdk_client.py`, not in filling in new tool logic.

`pytest` currently runs 186 tests, all green. Every file except
`tests/test_wire_subscriptions.py` and `tests/test_wire_load_balancer.py` needs no server
process at all; those two files run a real `uvicorn.Server` on an actual port, because a
stream with no natural end (`subscriptions/listen`) cannot be tested through the
in-process ASGI shortcut every other file uses. `tests/test_cafe_project.py` is the only
file in the whole folder that uses the official SDK client (`mcp.client.Client`) rather
than a hand-built request — on purpose, since topic 15's entire subject is that client.

The shared package grows one module per part, and every module imports **nothing** from
MCP — so the café's rules, documents and state mechanics can all be tested at the speed of
a function call:

| Module | Added in | What it holds |
|--------|----------|---------------|
| `cafe_mcp/menu.py` | topic 02 | twelve drinks, prices, sizes, lookups |
| `cafe_mcp/render.py` | topic 04 | the menu as markdown, one drink as JSON |
| `cafe_mcp/pagination.py` | topic 06 | the opaque, unsigned page cursor |
| `cafe_mcp/tokens.py` | topic 07 | the generic HMAC-signed, `kind`-separated token codec |
| `cafe_mcp/orders.py` | topic 07 (refactored for topic 08) | cart pricing and the order-token-specific wrapper over `tokens.py` — shared by `add_to_order`/`view_order` (07), `place_order` (08), `pay_for_order` (09), `brew` (10) and again (14) |
| `cafe_mcp/shared_bus.py` | topic 14 | `SqliteSubscriptionBus` — a `SubscriptionBus` Protocol implementation backed by one shared SQLite file, replacing the default in-memory bus so `sell_out`/`un_sell_out` (11) notify listeners across separate processes |

`solved/cafe_project.py` (topic 15) is not a new module in this table — it imports and
re-registers tool/resource/prompt functions from nine earlier topic files directly (03, 04,
05, 06, 07, 08, 10, 11, 13) onto one fresh `MCPServer`, using the fact that
`@mcp.tool(...)`/`@mcp.resource(...)`/`@mcp.prompt(...)` are decorator factories that hand
the original function back unchanged. No tool logic is written twice.

## Ground truth

Every API in this folder was checked against the installed packages, not against
documentation or memory:

| Package | Version |
|---------|---------|
| `mcp` | 2.1.1 |
| `mcp-types` | 2.1.1 |
| `httpx2` | 2.12.0 |
| Protocol revision targeted | `2026-07-28` |

Where the SDK and the specification disagree, the notes say so and name which one you
are looking at. There are a few such places and they are interesting rather than
annoying.

## Where the SDK and the spec disagree

There are a handful of places, and they are interesting rather than annoying. They are
collected in [notes/appendix-sdk-vs-spec.md](notes/appendix-sdk-vs-spec.md), each one
reproduced against a running server rather than quoted from a changelog.

## Ports

The café uses **3010**. The load-balancer topic adds **3011, 3012, 3013** for the three
instances, with the proxy on 3010. Nothing here uses 3001 or 8000.
