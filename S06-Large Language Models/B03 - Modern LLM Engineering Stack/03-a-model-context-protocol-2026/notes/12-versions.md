# Version Negotiation With No Handshake to Negotiate In

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [The SDK's own vocabulary: handshake, modern, known](#the-sdks-own-vocabulary-handshake-modern-known)
  - [Every known version genuinely works](#every-known-version-genuinely-works)
  - [`server/discover` only advertises the modern version](#serverdiscover-only-advertises-the-modern-version)
  - [The irony: `discover` does not exist under an older version](#the-irony-discover-does-not-exist-under-an-older-version)
  - [`ping` is the mirror image of `discover`](#ping-is-the-mirror-image-of-discover)
  - [The recovery loop for a genuinely unknown version](#the-recovery-loop-for-a-genuinely-unknown-version)
  - [`ctx.protocol_version`: seeing your own era from inside a tool](#ctxprotocol_version-seeing-your-own-era-from-inside-a-tool)
- [Layer 3 — Dry-run: three clients, three eras, one server](#layer-3-dry-run-three-clients-three-eras-one-server)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)

## One sentence

There is no handshake left to negotiate a version during — every one of the ten methods
carries its own version claim on every single call, and the server decides, per request,
which era's rules to apply, which turns "version negotiation" from a one-time ceremony
into something closer to a passport check at every door.

## Where this sits

You have been declaring `2026-07-28` in every request since topic 01, and every one of
those requests has worked. This topic finally asks the questions that arrangement was
quietly answering the whole time: what if you declared something else? What if you
declared nothing at all? What if you declared a version that predates this revision by two
years, or one that has never existed? Four different answers, and they are not the
answer you might guess.

## The problem this topic solves

Pre-2026 MCP negotiated a version once, during `initialize`, and every later message on
that connection inherited it. That mechanism is gone along with the rest of the handshake
— topic 00 covered the deletion. What replaced it is not a *smaller* negotiation; it is a
different question entirely. Instead of "what version will this whole connection speak?"
the protocol now asks, on every single message, "what version does *this one message*
speak?" — and a server has to be able to answer that question correctly even for a
message declaring a version several revisions old.

## Layer 1 — The intuition

Picture a government office with four separate counters, one per form-year: 2024's forms,
2025's two revisions, and this year's. Each counter is staffed and fully capable — hand a
2024 form to the 2024 counter and it processes it exactly as it always has, no different
from someone submitting the current year's form at the current counter. What does not
exist is a single "which counter should I go to?" desk that works for a form from *any*
year — the front desk itself only speaks this year's forms, because it was built this year,
for people who already know they are filling in this year's version.

## Layer 2 — The mechanics

### The SDK's own vocabulary: handshake, modern, known

The SDK's own `mcp_types.version` module names these eras precisely, and it is worth
using its words rather than inventing your own:

```python
KNOWN_PROTOCOL_VERSIONS  = ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25', '2026-07-28')
HANDSHAKE_PROTOCOL_VERSIONS = ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25')
MODERN_PROTOCOL_VERSIONS = ('2026-07-28',)
LATEST_HANDSHAKE_VERSION = '2025-11-25'
LATEST_MODERN_VERSION    = '2026-07-28'
```

Five revisions are **known** to this SDK. Four of them are **handshake** era — they used
`initialize`/`initialized`, and this SDK still speaks them correctly on request. Exactly
one is **modern** — the stateless one this entire folder has been built against. "Legacy"
is a fine word for the handshake group in casual conversation, but the SDK's own name for
it is more precise, and it is the name that will make sense of the next two sections.

### Every known version genuinely works

```bash
bash curl/12_whoami.sh 2026-07-28
bash curl/12_whoami.sh 2025-11-25
bash curl/12_whoami.sh 2025-06-18
bash curl/12_whoami.sh 2024-11-05
```

All four succeed. Verified directly, the same tool, four separate requests, no session
between them:

```text
2026-07-28  ->  This request declared protocol version: '2026-07-28'
2025-11-25  ->  This request declared protocol version: '2025-11-25'
2025-06-18  ->  This request declared protocol version: '2025-06-18'
2024-11-05  ->  This request declared protocol version: '2024-11-05'
```

Nothing about "old" here means "broken" or "degraded." A 2024-11-05 request gets a
2024-11-05-shaped response — no `resultType`, no `ttlMs`, no `_meta.serverInfo`, exactly
as topic 01 first showed — because that is what a 2024-11-05 client actually expects, and
the SDK produces it faithfully rather than forcing every caller through one shape.

### `server/discover` only advertises the modern version

```bash
bash curl/12_discover.sh
```

```json
{"resultType": "complete", "supportedVersions": ["2026-07-28"], ...}
```

One entry. Not five, even though the same server just proved it speaks four other
versions perfectly well two paragraphs ago. Read this precisely: `supportedVersions` is
`MODERN_PROTOCOL_VERSIONS`, not `KNOWN_PROTOCOL_VERSIONS`. `server/discover` is not a
report of everything this server *can* do — it is a statement of what this server *offers
under discovery*, and discovery, as a mechanism, is a 2026-07-28 feature. It says nothing
about what a client speaking an older dialect will find if it never calls `discover` at
all and just tries its own version directly.

### The irony: `discover` does not exist under an older version

```bash
bash curl/12_discover_wrong_era.sh
```

```json
{"error": {"code": -32601, "message": "Method not found", "data": "server/discover"}}
```

Sent under `MCP-Protocol-Version: 2025-06-18` — a version that works perfectly for every
other method on this server — `server/discover` itself is simply **not there**. Not
unsupported, not degraded: absent, the same way any method never added to that era's
method map is absent. `-32601`, not `-32022` — the version was completely valid; this
particular *method* just does not exist under it, because it was added at 2026-07-28 and
has no entry anywhere earlier.

Sit with what that means for a client that genuinely knows nothing yet. `discover` exists
specifically to help a client find out what a server supports — and it only answers a
client that has already decided to speak the one version it exists for. A client cannot
safely open with `discover` as a universal "tell me what you speak" probe, because a
server that only speaks 2025-11-25 and earlier would refuse that exact call with
`-32601`, and a naive implementer reading that error would reasonably conclude "this
server has no discovery mechanism at all" rather than "I asked in the wrong dialect."

The practical answer: a client with no prior information should not open with `discover`.
It should try its own preferred version directly, on the real call it actually wants —
and read the next section's recovery path only if that fails.

### `ping` is the mirror image of `discover`

`discover` is missing from every version *older* than 2026-07-28, because it is *new*.
`ping` shows the opposite shape:

```bash
bash curl/12_whoami.sh 2025-06-18       # -> works
```

```python
from mcp_types.methods import CLIENT_REQUESTS
{v for m, v in CLIENT_REQUESTS if m == "ping"}
# -> {'2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25'}   -- 2026-07-28 absent
```

`ping` works, unchanged, at all four handshake-era versions — it is not merely tolerated,
it returns a genuine `EmptyResult`, exactly as it always has. It disappears at exactly one
point: 2026-07-28, where it was removed and replaced with the ordinary `/healthz` route
every server in this folder has carried since topic 01. Two different kinds of "missing,"
worth being able to tell apart on sight: `discover` is missing from the old end because
it is new; `ping` is missing from the new end because it was retired. Neither is a bug in
either direction — a version genuinely either has a method or it does not, and which side
of history it is missing from tells you why.

### The recovery loop for a genuinely unknown version

```bash
bash curl/12_unknown_version.sh
```

```json
{"error": {"code": -32022, "message": "Unsupported protocol version",
           "data": {"supported": ["2026-07-28"], "requested": "not-a-real-version"}}}
```

This is the one genuinely new error in the whole story, and it fires only when the
requested version is not in `KNOWN_PROTOCOL_VERSIONS` at all — none of the four handshake
versions ever trigger it, because the SDK genuinely knows them. `data.supported` is the
entire negotiation loop, compressed into one field: read it, pick an entry, retry. Note it
names `MODERN_PROTOCOL_VERSIONS`, the same list `discover` advertises — the error is
steering you toward the version worth targeting going forward, not toward every dialect
this particular SDK build happens to still accept.

### `ctx.protocol_version`: seeing your own era from inside a tool

```python
@mcp.tool()
async def whoami(ctx: Context) -> str:
    return f"This request declared protocol version: {ctx.protocol_version!r}"
```

One property, read from inside ordinary tool code, tells you which era the *current*
request declared — with no session anywhere holding that fact between calls. This is what
makes the dual-era behavior something your own code can react to, not just something the
transport layer quietly handles beneath you: a tool that needed to behave differently for
callers who cannot use a feature added after their declared version could branch on this
exact property.

## Layer 3 — Dry-run: three clients, three eras, one server

**Client X**, built in 2025, sends every request with `MCP-Protocol-Version: 2025-06-18`.
It calls `whoami`. The server recognizes `2025-06-18` as a known handshake-era version,
serves the result in that era's shape (no `resultType`, no `ttlMs`), and `whoami` reports
`protocol_version='2025-06-18'`. Client X never notices anything unusual, because from its
side, nothing is.

**Client Y**, built against this folder, sends `MCP-Protocol-Version: 2026-07-28` on every
call. It calls `server/discover` first, gets `supportedVersions: ["2026-07-28"]`, confirms
its own choice was already right, and proceeds.

**Client Z** is a brand-new implementation with no prior knowledge of this server at all,
and its author read a two-year-old tutorial that said "call `initialize` first." It has no
`initialize` to call — but suppose, instead, it guesses at the *new* discovery pattern and
tries `server/discover` under whatever version its guess landed on, say `2025-11-25`
(a real, known version, just not this call's right one):

```json
{"error": {"code": -32601, "message": "Method not found", "data": "server/discover"}}
```

Client Z's author, reading only this error, might reasonably conclude the server has no
discovery mechanism. The actual fix is one line: change the header to `2026-07-28` and the
identical `server/discover` call succeeds. The lesson embedded in that: **the error a
client gets for "wrong version for this method" and "this method plain does not exist" are
the same JSON-RPC code**, `-32601`, and distinguishing them requires knowing, independently,
whether the method you called is version-gated at all.

## Gotchas

**"Known" and "modern" are not the same set.** Five versions are known; one is modern.
`discover`'s `supportedVersions` names only the second group.

**`-32601` on `server/discover` does not mean "no discovery support."** It can just as
easily mean "wrong version header for this particular method." Check the version you sent
before concluding the method is unsupported.

**`-32022` only fires for a version outside `KNOWN_PROTOCOL_VERSIONS` entirely.** An old
but recognized version is served, silently, in its own shape — never an error.

**A legacy-shaped result is not a degraded modern one.** No `resultType`, no `ttlMs`, no
`_meta.serverInfo` — that absence is correct for that era, not a sign that something failed
to attach.

**There is no version "sticking" across calls.** Change the header on your very next
request and the server's behavior changes with it, mid conversation, because there is no
conversation-level state to hold a version in.

**`ping`'s absence and `discover`'s absence are opposite phenomena.** One is missing from
old eras because it is new; the other is missing from the new era because it was retired.

## Your turn

`solutions/t12_versions.py`, two TODOs — the shortest server in this folder, on purpose.
Before writing `whoami`, predict what four separate calls, one per known version, will do.
Then TODO 3 asks the harder prediction: what error code fires for `server/discover` under
an old version — the same `-32022` you already know, or something else? Getting this one
wrong and then seeing why is the actual point of the exercise.

## Connection forward

Topic 13 is about a different axis entirely: how a *gateway* — something sitting in front
of your server, routing traffic without necessarily parsing every JSON-RPC body — decides
what to do with a request, using headers alone. `Mcp-Method` and `Mcp-Name` have appeared
in every script since topic 01; topic 13 is where you finally build the custom header
mirroring (`Mcp-Param-*`) that lets an *argument* reach that same gateway layer, and where
the café's one non-ASCII drink name finally earns its keep.

Does this make sense? Want me to go deeper on any part — why `discover`'s asymmetry is a
deliberate design rather than an oversight, the exact difference between `-32601` and
`-32022`, or what a real client library's version-selection strategy should look like?
