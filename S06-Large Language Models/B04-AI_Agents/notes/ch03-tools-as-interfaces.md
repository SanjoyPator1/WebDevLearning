# Chapter 3: Tools as Interfaces

## Table of Contents

1. [Why This Chapter Exists](#1-why-this-chapter-exists)
2. [The Schema Is a UI Whose User Is a Model](#2-the-schema-is-a-ui-whose-user-is-a-model)
3. [Granularity: Consolidate Over Fragment](#3-granularity-consolidate-over-fragment)
4. [Return-Value Design: Give the Model What It Needs Next](#4-return-value-design-give-the-model-what-it-needs-next)
5. [Error Messages as Instructions, Not Postmortems](#5-error-messages-as-instructions-not-postmortems)
6. [Structured Output and Schema-Constrained Generation](#6-structured-output-and-schema-constrained-generation)
7. [Idempotency, Side Effects, and the Destructive Flag](#7-idempotency-side-effects-and-the-destructive-flag)
8. [Dry-Run: The Token Bill of a 40-Tool Library Across a 20-Step Loop](#8-dry-run-the-token-bill-of-a-40-tool-library-across-a-20-step-loop)
9. [Tool Selection Failures as the Library Grows](#9-tool-selection-failures-as-the-library-grows)
10. [MCP as Tool Transport, Revisited](#10-mcp-as-tool-transport-revisited)
11. [Advanced Tool Use: Search, Deferred Loading, Programmatic Calling](#11-advanced-tool-use-search-deferred-loading-programmatic-calling)
12. [What Good Tool Design Still Can't Fix](#12-what-good-tool-design-still-cant-fix)
13. [Key Takeaways + Master Decision Table](#13-key-takeaways--master-decision-table)

---

# 1: Why This Chapter Exists

## What This Chapter Is Really About

Chapter 2 built the loop and treated the tools inside it as given — a
dictionary from name to function, a list of JSON schemas, done. That was the
right call at the time; you cannot design a good interface before you have a
consumer for it. Now you do. This chapter goes back to those tool definitions
and asks the question Chapter 2 skipped: what makes one tool schema good and
another one quietly sabotage the exact same model, running the exact same
loop, on the exact same task?

The claim this chapter defends, stated once so it can be referred back to
throughout: **a tool schema is a user interface, and its user happens to be a
language model instead of a human.** Every intuition you already have about
good API and UI design — clear naming, sensible defaults, error messages that
tell you what to do next, not overwhelming the user with two hundred menu
items — transfers almost unchanged. What changes is *who* is reading the
interface and *how* they fail when it's bad. A human facing a confusing form
gets annoyed and asks a colleague. A model facing a confusing tool schema
doesn't get annoyed — it silently guesses, calls the wrong tool with
plausible-looking arguments, and produces an error three steps later that
looks like a completely different bug. Anthropic's own applied-AI team,
writing about the tools they ship inside Claude Code and their MCP
connectors, put it directly: tools are "a fundamentally new kind of software
that requires new tools and new intuitions to develop well" because "unlike
traditional software... agent-computer interfaces... require exhaustive
testing with real models" — a contract between deterministic code and a
non-deterministic reader, not between two deterministic systems.

*Everything in this chapter is demonstrated against Anthropic's tool-use wire
format (`input_schema`, `tool_use`, `tool_result`) — the same format this
course's notebooks connect to directly through `AnthropicBedrockMantle`
(Claude Sonnet, via AWS Bedrock). The principles themselves — clear names,
right-sized granularity, lean return values, actionable errors — aren't tied
to any one platform's exact field names; they apply to any tool-calling
model that expresses "the model wants to call a function" through a
JSON-Schema-shaped input contract, MCP-sourced tools included. This chapter
doesn't demonstrate that generality with a second vocabulary, for the same
reason Chapter 2 settled on one: depth on a single real wire format teaches
the underlying lesson better than a shallow tour of several. Where a
mechanic genuinely only exists on this platform — the Tool Search Tool's
`defer_loading` field in Section 11 is the clearest example — this chapter
says so explicitly.*

## Connection Back to Chapter 1's Failure Modes

Two of the three failure modes named in Chapter 1 — victory declaration bias
and context anxiety — are partly *tool-design* failures wearing a different
name. A model that "context anxiety"-re-reads a file it already has in
context is often reacting to a `read_file` tool that returns an opaque blob
with no indication of what's already been seen. A model that declares victory
prematurely is sometimes trusting a tool result that itself lied by omission
— a `write_file` tool that returns `{"status": "ok"}` with no detail to
verify against. Fixing the loop (Chapter 2) doesn't fix either of these;
fixing the tools does. That is the entire economic case for a chapter this
narrow.

*Next: the central metaphor for the rest of this chapter — reading a schema
the way a model actually has to.*

---

# 2: The Schema Is a UI Whose User Is a Model

## The Intuition

Imagine handing a new hire a paper form with a field labeled `id` and no
further description, sitting next to another field labeled `type`. A human
new hire pauses, looks around the office, and asks someone "id of what,
exactly?" A model gets no such pause. It has exactly one shot at filling in
that field correctly, informed only by the field's name, its JSON-Schema
type, and whatever the tool's top-level `description` string told it — and it
will confidently produce *something*, because refusing to guess is not a
behavior anyone trained into it as a default. Every ambiguity you leave in a
schema becomes a coin flip the model makes on your behalf, silently, inside a
single forward pass you cannot see.

This reframes "write a good docstring" (something every engineer already
half-believes they should do) into something sharper: **the tool description
is the entire specification the model will ever see.** There is no README,
no Stack Overflow thread, no colleague at the next desk. If the description
doesn't say that `user_id` must be the internal UUID and not the
user-facing email, the model will eventually pass an email, because nothing
told it not to.

## Naming and Namespacing

Anthropic's own guidance, refined through building and shipping their
internal Slack and Asana integrations, converges on a few concrete rules.
Name tools the way you'd name a well-factored function: `get_current_weather`
reads unambiguously; `weather` does not, especially once a second tool named
`weather_v2` or `check_weather` shows up beside it. When an agent has access
to *multiple* systems that could each plausibly have a `search` tool — a
ticketing system, a wiki, a CRM — namespace by prefixing with the system and
grouping by resource: `asana_projects_search`, `asana_users_search`,
`jira_search`, rather than five same-named `search` tools distinguished only
by which server registered them. Anthropic's engineering team specifically
notes that even the *choice between prefix-style and suffix-style*
namespacing (`asana_search_projects` vs `search_asana_projects`) produced
measurable differences in tool-selection accuracy on their internal
evaluations — a reminder that this isn't taste, it's an empirical question
you should be willing to actually measure against your own tool set rather
than assume.

Parameter names deserve the same discipline. `user` is ambiguous between "a
user object," "a username string," and "a user ID" — `user_id` is not. This
sounds trivial in isolation; it stops being trivial the moment a model has
eleven tools in context and three of them accept something loosely called
`id`.

## Description Length and What the Model Can Infer

A description should do for the model what onboarding documentation does for
a new engineer: state things that are true but not derivable from the name
alone. "Search Asana tasks" adds nothing beyond the tool's own name. "Search
Asana tasks by assignee, due date, or project. Returns up to 50 matches;
use `cursor` from a previous response to page further; prefer narrow filters
over broad ones — an unfiltered search on a large workspace will be
truncated and cost you a wasted call" tells the model something it could not
have guessed: the pagination contract, the truncation behavior, and a
strategy hint for using the tool well the first time instead of after one
failed attempt. The gain compounds with the size of the tool library — one
vague description is a minor cost with three tools in context; it is a
serious cost with thirty, because on turn one the model is deciding which of
those thirty best fits, and a vague description makes every tool it's
attached to look slightly more interchangeable than the others.

Anthropic reports that on the SWE-bench Verified coding benchmark, careful,
iterative refinement of tool descriptions and argument names — with no change
to the underlying tools' *capabilities* — measurably reduced the model's
error rate and contributed to a state-of-the-art result at the time. The
tools did not get more powerful. The interface got clearer. That distinction
is the entire argument for taking this chapter seriously instead of treating
tool descriptions as an afterthought written once and never revisited.

## Argument Shape

Prefer flat, explicit parameters over deeply nested or overloaded ones
whenever the underlying operation allows it. A `filters: {status: "open",
assignee: "me", ...}` nested object asks the model to correctly construct
JSON *inside* JSON with no schema validation on the inner shape (JSON Schema
validates the outer `filters` object's declared properties, but a model
still has to get the nesting exactly right on every call). A flatter
`status`, `assignee` at the top level of `input_schema.properties` is both
easier for the model to fill in correctly and easier for you to validate.
Nesting still has a place — grouping five related optional fields that only
ever travel together is a legitimate use — but it should be a deliberate
choice, not an accident of mirroring your internal database schema onto the
tool definition.

```
BAD:  { "query": { "filters": { "meta": { "assignee_id": "..." } } } }
      (four levels deep; the model must nest correctly with zero help
       from the schema about what belongs where)

GOOD: { "assignee_id": "...", "status": "open", "project": "..." }
      (flat, each field independently validated, each field's purpose
       readable from its name alone)
```

## Key Takeaways for Section 2

A tool's name, its parameter names, and its description string are the
*entire* specification a model has — there is no fallback channel for it to
ask a clarifying question. Namespace tools by system and resource when
multiple similar tools coexist; write descriptions that state what isn't
derivable from the name (pagination, truncation, when to prefer this tool
over a similar one); and keep argument shapes flat unless nesting genuinely
groups related fields. None of this requires touching what the tool *does* —
Anthropic's SWE-bench result came entirely from clarifying what the tool
*says*.

*Next: a single tool that does more, or many tools that each do less — which
one actually serves the model better?*

---

# 3: Granularity: Consolidate Over Fragment

## The Problem

A natural instinct, carried over from good microservice or REST API design,
is to expose small, single-purpose primitives: `list_users`, `list_events`,
`create_event`, `list_rooms`, `check_room_availability`. Each one is clean,
testable, and does exactly one thing. That instinct, applied unchanged to
agent tools, produces a subtly worse agent — because every one of those
primitives is a decision point, and every decision point is a place the model
can go slightly wrong, burn a wasted round trip, or chain them in an order
that technically works but costs five tool calls (five full context
round-trips, at Chapter 2's Section 11 cost) for something a human assistant
would just call "book a meeting."

## The Intuition

Think of the difference between handing a new employee a fully itemized
parts catalog and a work order form. The parts catalog is more *composable*
in principle — you could build anything from those parts — but for the one
task actually in front of you ("schedule a meeting with Alex next Tuesday
afternoon"), the work order form is strictly better: one field for who, one
for when, one submit action, and the assembly of primitives underneath it
happens in code you control, not in five separate guesses the model has to
get right in sequence.

## The Guidance

Anthropic's concrete recommendation, drawn from their internal tool-building
experience: consolidate high-leverage workflows into a single tool rather
than exposing the primitives that compose it.

| Instead of (fragmented) | Prefer (consolidated) | Why |
|---|---|---|
| `list_users`, `list_events`, `create_event` | `schedule_event(attendees, time_range, title)` | One decision, one call, no ordering to get wrong |
| `read_logs` (returns everything) | `search_logs(query, time_range)` | Filtering happens server-side, not by the model reading and discarding |
| `get_customer_orders`, `get_customer_tickets`, `get_customer_profile` | `get_customer_context(customer_id)` bundling all three | One round trip instead of three; the model gets the full picture without deciding to ask three separate questions |

This is not "always prefer fewer tools" as a blind rule — Section 9 covers
the opposite failure mode, where cramming unrelated operations into one
tool with a sprawling parameter list is its own kind of bad interface. The
actual principle is: **consolidate the operations a human would think of as
"one task,"** and keep genuinely distinct operations as genuinely distinct
tools. `schedule_event` bundles "find available people," "find an available
slot," and "create the event" because a human calls that whole bundle
"scheduling a meeting" and would never want to approve each sub-step
individually. `search_logs` and `delete_logs`, by contrast, should stay
separate tools no matter how related they sound — one is read-only and safe
to call speculatively, the other is destructive and belongs behind the
permission gate that Chapter 16 builds.

## The Trade-off, Stated Precisely

Every fragmented primitive you fold into one consolidated tool removes a
decision point (good — fewer chances to pick the wrong next call, fewer round
trips) but also removes flexibility (a cost — if some future task genuinely
needs to `list_events` without booking anything, that primitive no longer
exists as its own callable unit). The right granularity sits at whatever
level real tasks actually operate — which you find empirically, by looking
at your own agent's transcripts for chains of three or more tool calls that
always occur together, and asking whether they should have been one call all
along.

## Key Takeaways for Section 3

Fragmenting an agent's tools the way you'd fragment a REST API produces more
decision points, not more flexibility, because every extra tool call is a
place the model's guess can diverge from what you meant and a full context
round-trip you're paying for regardless of outcome. Consolidate around what a
human would call "one task"; keep genuinely distinct or genuinely dangerous
operations as separate tools.

*Next: once a tool call succeeds, what should it actually hand back — and why
is "the whole record" almost always the wrong answer?*

---

# 4: Return-Value Design: Give the Model What It Needs Next

## The Intuition

A tool's return value is not a database dump — it's the observation half of
the think-act-observe loop from Chapter 2, and everything in it becomes
prefill tokens on every subsequent call for the rest of the run (Section 7 of
Chapter 2's dry-run made this cost concrete: the growing tail, not the fixed
prefix, dominates a long run's bill). A tool that returns 8 KB of raw JSON
when the model needed one field is not being "thorough" — it is spending
your context budget on behalf of a decision the model never asked to make.

## Verbosity as a Parameter, Not a Fixed Choice

Anthropic's own worked example (from tools built for Claude Code and internal
integrations) exposes a `response_format` enum with `"concise"` and
`"detailed"` variants on the *same* tool, letting the calling agent choose
per call:

```
"detailed" response (includes full metadata, needed when the result
feeds a later tool call that requires an ID):
  { "id": "task_9f2a", "title": "Fix login bug", "status": "open",
    "assignee": "user_442", "created": "2026-07-30T14:02:00Z",
    "project": "proj_11", "labels": ["bug", "auth"], ... }
  ≈ 206 tokens

"concise" response (same task, when only a human-readable summary
is needed for the model to reason about, not act on further):
  "Fix login bug (open, assigned to Alex)"
  ≈ 72 tokens
```

The concise form costs roughly a third of the detailed one — a real,
measured 65% reduction on that one call, and it compounds across every
subsequent call in the run the way Section 7's growing tail does.

## Truncation With a Continuation Handle, Not a Silent Cliff

When a result is genuinely large — a log search, a file read, a database
query — never return it silently truncated with no signal that truncation
happened; the model will treat what it got as complete and reason wrong
conclusions from partial data (a direct contributor to Chapter 1's victory
declaration bias, one layer down). Claude Code's own file-reading and search
tools cap responses at a fixed budget (25,000 tokens, by default) and pair
truncation with an explicit continuation mechanism — a cursor, an offset, or
a stated "N more results, call again with `cursor=X`" — so the model can
choose to keep going instead of silently believing it saw everything.

```
BAD:  search_logs(...) → first 500 lines, no indication 4,500 more exist
GOOD: search_logs(...) → first 50 matching lines +
      "47 more matches. Call again with cursor='eyJvZmZzZXQiOjUwfQ=='
       to continue, or narrow your query with a time range."
```

## IDs the Model Can Actually Reason About

A raw UUID like `a3f29c1e-88b4-4d61-9c2e-771a0f3b9d42` is opaque to a model
in the same way it's opaque to a human skimming a log — indistinguishable
from any other UUID, easy to transpose a character in, and a frequent source
of hallucinated IDs when the model needs to reference something it saw
several turns back. Anthropic's guidance is to prefer identifiers that are
either semantically meaningful (`task_9f2a` reads as "a task," at least) or,
where the ID space is small and short-lived within one conversation, a
simple 0-indexed scheme (`item_1`, `item_2`, ...) that the model can track
far more reliably across a growing transcript than an opaque hash.

## Key Takeaways for Section 4

A tool's return value is priced in prefill tokens on every future call, not
just the current one — treat it as a budget, not a dump. Expose a verbosity
control when a tool serves both "just tell me" and "I need the full record
to chain into another call" use cases; truncate with an explicit
continuation handle, never silently; and prefer identifiers the model can
actually track over opaque UUIDs it's liable to mis-transcribe three turns
later.

*Next: the other kind of return value — the one that shows up when
something goes wrong, and why most tool error messages are written for the
wrong reader entirely.*

---

# 5: Error Messages as Instructions, Not Postmortems

## The Intuition

A traditional API error message is written for a human developer who will
read a stack trace, open the source, and fix their calling code once. An
agent's error message is read by the same model, inside the same run, with
one chance to *self-correct on its very next turn* — there is no human in
the loop to interpret `HTTP 400: Bad Request` and go read documentation. If
the error doesn't say what to do differently, the most likely next move is
the model retrying the exact same call, or a superficially different one
that fails for the same underlying reason. Chapter 2, Section 6 established
the *mechanics* of returning a tool error (`is_error: true`, never crash,
never drop it silently); this section is about what should actually be
*inside* that error string.

## Before and After

```
BAD (a postmortem for a human):
  {"is_error": true,
   "content": "ValidationError: 422 Unprocessable Entity"}

GOOD (an instruction for the model):
  {"is_error": true,
   "content": "Invalid date format for 'due_date': got '07/30/2026'.
                Use ISO 8601: 'YYYY-MM-DD' (e.g. '2026-07-30')."}
```

The bad version is technically informative — a human who already knows this
API would recognize a validation failure — but it hands the model nothing to
act on beyond "try something else, unspecified." The good version states
exactly what was wrong and exactly what a correct call looks like, which
means the very next `tool_use` block the model emits is far more likely to
succeed on the first retry rather than the third.

## Steering, Not Just Correcting

The same principle extends past pure validation errors into *strategy*
hints. A tool that's about to be called inefficiently can say so in its
error or warning text rather than silently doing the expensive thing:

```
{"is_error": true,
 "content": "Query returned 14,203 rows and was rejected before
             transfer. Add a 'status' or 'date_range' filter, or
             set 'limit' (max 200) if you only need a sample."}
```

This does two jobs at once: it prevents a genuinely wasteful call (14,203
rows would have been truncated anyway, per Section 4, after costing you the
full retrieval), and it teaches the model, inline, the specific strategy this
particular tool wants used — filters over brute force. This is the same
instinct as Section 2's description-writing guidance, just triggered at
failure time instead of at definition time.

## Include a Correctly Shaped Example When the Fix Isn't Obvious

For anything more structurally complex than a single bad field — a
malformed nested object, an enum value that's close-but-not-quite a valid
option — include one concrete, correctly formatted example directly in the
error text rather than only naming the rule that was violated. "Invalid
value for `priority`: got `'urgent'`. Valid values: `'low'`, `'medium'`,
`'high'`, `'critical'`" tells the model both what failed and exactly what a
working call looks like, collapsing what could be a second failed guess into
a corrected one.

## Key Takeaways for Section 5

A tool error message has exactly one reader with exactly one chance to
self-correct before the next turn — write it as an instruction for that
retry, not as a diagnostic for a human debugger who was never going to see
it. State what was wrong, state the expected shape, and where useful, steer
the model toward a better strategy for the tool generally, not just a fix
for this one call.

*Next: what happens when you stop asking the model to describe its output in
prose and start constraining the shape of the answer itself.*

---

# 6: Structured Output and Schema-Constrained Generation

## The Problem This Solves

Everything so far in this chapter has been about tool *calls* — the model
deciding to invoke something and shaping its input. Structured output solves
a related but distinct problem: forcing the model's *final answer* (not a
tool call, the actual response text) into a schema you control, so that
downstream code parsing that response never has to handle "the model
almost returned valid JSON but wrapped it in a sentence and used single
quotes." Before this existed, a common workaround was prompting "respond
only in JSON" and then wrapping the parse in a retry loop for the times it
didn't listen — workable, but fragile, and it burns a full extra round trip
every time the model gets creative with formatting.

## The Mechanism

The Messages API exposes this as `output_config.format`, letting you attach
a JSON Schema directly to the request so the response is constrained at
generation time (not merely validated after the fact) to conform to that
schema — the model is not "asked nicely" to produce this shape, decoding
itself is constrained so that shape is the only one it can produce. Alongside
this, `strict: true` on a *tool's* `input_schema` gives the same
generation-time guarantee for tool call arguments specifically, closing the
same class of failure Section 2 and Section 5 were both partly working
around by writing careful descriptions and forgiving error messages — with
`strict: true`, certain classes of malformed input become structurally
impossible rather than merely less likely.

The recommended entry point in the Python and TypeScript SDKs is
`client.messages.parse()`, which sends the schema, validates the response
against it automatically, and returns you a parsed object rather than a raw
string you validate yourself — the SDK equivalent of Section 4's principle
that a tool should hand back exactly what the caller needs next, applied to
the API client itself.

## What JSON Schema Can and Can't Express Here

This constrained-decoding path supports a solid but not unlimited subset of
JSON Schema: the basic types, `enum`, `const`, `anyOf`/`allOf`,
`$ref`/`$def` for reuse, and a set of recognized string formats (`date-time`,
`email`, `uuid`, and similar). It does **not** support recursive schemas, or
numeric/string *constraints* like `minimum`, `maximum`, `minLength`, or
`maxLength` — those need to be validated in your own code after the response
comes back, the same way you'd validate any other tool input in Section 5's
world. `additionalProperties: false` is required on every object in the
schema; a schema that allows arbitrary extra properties isn't something the
constrained decoder can commit to ahead of time.

```
SUPPORTED:   {"type": "object",
              "properties": {"status": {"enum": ["open", "closed"]}},
              "required": ["status"], "additionalProperties": false}

NOT SUPPORTED (needs post-hoc validation instead):
             {"type": "string", "minLength": 3, "maxLength": 50}
             (recursive schemas also unsupported)
```

## Where This Fits Relative to Tool Use

Structured output and tool use solve adjacent but different problems: tool
use is "the model decides *whether* and *what* to call, from a set of
options you defined" (Chapters 2–5's whole subject); structured output is
"the model's answer, once it has one, must conform to a schema you defined,"
with no tool call involved at all. A single agent turn can use both — a tool
call to fetch data, followed several turns later by a final structured
answer once the loop terminates — but conflating them (trying to force a
*tool call's arguments* to be schema-strict via `output_config` instead of
via `strict: true` on that tool's own `input_schema`) targets the wrong
knob for the job.

## Key Takeaways for Section 6

`output_config.format` constrains the model's final answer to a JSON Schema
at generation time, and `strict: true` does the equivalent for a specific
tool's input arguments — both close the same "the model almost got the
shape right" failure class that used to require a retry loop, but neither
supports the full generality of JSON Schema (no recursion, no numeric/string
length constraints), so real validation of those constraints still belongs
in your own code.

*Next: what happens when a tool call itself is risky to repeat — and how the
schema should say so.*

---

# 7: Idempotency, Side Effects, and the Destructive Flag

## The Intuition

A read-only tool can be called speculatively, retried after a timeout, and
called twice by mistake with zero consequence beyond wasted tokens. A tool
that sends an email, charges a card, or deletes a record cannot be treated
the same way — and yet, from the model's point of view inside Chapter 2's
loop, both are just a `tool_use` block it decided to emit. Nothing in the
mechanics of the loop itself distinguishes "safe to retry" from "catastrophic
to retry," which means that distinction has to be designed into the tool,
not assumed from context.

## Idempotency: Design for Safe Retries

An operation is **idempotent** if calling it twice with the same arguments
produces the same end state as calling it once. `set_status(task_id,
"closed")` is naturally idempotent — closing an already-closed task changes
nothing. `increment_counter(task_id)` is not — calling it twice doubles the
effect. Where the underlying operation is naturally non-idempotent but
important enough to make retry-safe anyway (payment processing is the
canonical example), the standard fix is an **idempotency key**: the caller
generates a unique token per logical operation and passes it alongside the
request; the server recognizes a repeated key and returns the original
result instead of repeating the side effect. This matters specifically
because Chapter 2's loop *will* retry things — a network timeout after the
side effect already landed server-side is exactly the scenario where a
non-idempotent tool creates a duplicate charge or a duplicate email, not
because the model "chose" to call it twice, but because a retry-after-error
policy (a completely reasonable thing to want) can't tell the difference
between "the first call never reached the server" and "the first call
succeeded and only the response was lost."

## Dry-Run Modes

For any tool with a real side effect, a `dry_run: true` parameter that
returns exactly what *would* happen without doing it is disproportionately
cheap to build and disproportionately valuable — it lets the model (or a
human reviewing the model's plan before approving it, foreshadowing Chapter
16's permission layer) verify intent before commitment. `dry_run` on
`schedule_event` might return "would book Alex, Priya for 2026-08-12
14:00–15:00; no conflicts detected" without touching any calendar, which is
both a safety mechanism and, incidentally, a cheap way to catch a
misunderstood request before it costs a real action to undo.

## Marking Tools Destructive

The schema itself should carry a signal for which tools are safe to call
freely and which are not — commonly an `annotations` field or a
project-level convention such as `"destructive": true` alongside the tool
definition. This isn't cosmetic: it's the concrete hook the permission
system Chapter 16 builds attaches to. A loop that checks
`if tool.destructive: require_approval()` before executing a call needs
somewhere to read "destructive" from, and the tool definition — written once,
here, in this chapter's spirit — is that source of truth. Getting this flag
right now costs one boolean per tool; getting it wrong is the difference
between an approval gate that actually gates something and one that
silently no-ops because nothing told it which calls mattered.

## Key Takeaways for Section 7

Design tools to be idempotent wherever the underlying operation allows it,
because Chapter 2's loop will retry on error and cannot itself distinguish
a safe repeat from a harmful one; use idempotency keys where true
idempotency isn't achievable; offer `dry_run` on anything with a real side
effect; and mark destructive tools explicitly in the schema, since that flag
is exactly what Chapter 16's permission layer will need to find later.

*Next: everything in this chapter so far has been about individual tools —
now the arithmetic of having many of them at once, paid for on every single
turn.*

---

# 8: Dry-Run: The Token Bill of a 40-Tool Library Across a 20-Step Loop

## The Setup

Take an agent with a **40-tool library** — a realistic size once you connect
a couple of MCP servers (an issue tracker, a wiki, a calendar) rather than
hand-writing four bespoke tools — at **~250 tokens per schema** (name,
description, `input_schema` with a handful of properties; consistent with
Chapter 2's smaller 6-tool, 200-token example, just a larger library). Run a
**20-step loop**, using this project's illustrative Sonnet-class pricing from
Chapter 1, Section 11: **$3 / 1M input tokens**, cache write at **1.25×**
that rate ($3.75/1M), cache read at **0.1×** that rate ($0.30/1M).

$$\text{schema tokens} = 40 \times 250 = 10{,}000 \text{ tokens}$$

Just like Chapter 2's system prompt, the full tool list is part of the fixed
prefix sent on *every single call* in the loop — Chapter 2's Section 2
established that the message list (and everything accompanying it, tools
included) is resent in full each turn, because the API is stateless.

## Case 1 — All 40 Tools, No Caching

Every one of the 20 calls pays the full $3/1M rate on the entire 10,000-token
schema block, independent of everything else in the prompt:

$$\text{total schema cost} = 20 \times 10{,}000 \times \frac{\$3}{1{,}000{,}000} = 20 \times \$0.03 = \$0.60$$

## Case 2 — All 40 Tools, With Prompt Caching

The tool list doesn't change between calls, so it's cacheable exactly like
Chapter 1's system prompt: one cache write on step 1, nineteen cache reads
on steps 2–20.

```
1 cache WRITE:  10,000 × $3.75 / 1,000,000 = $0.0375
19 cache READs: 10,000 × 19 = 190,000 tokens × $0.30/1,000,000 = $0.0570

TOTAL (40 tools, cached) = $0.0375 + $0.0570 = $0.0945
```

Caching alone cuts the schema bill from $0.60 to $0.0945 — an **84% drop**,
the same order of magnitude as Chapter 1's fixed-prefix caching discount,
for exactly the same reason: a static block, read many times, priced at the
0.1× cache-read rate almost every time it's read.

## Case 3 — Just-in-Time Loading (Tool Search, `defer_loading`)

Now suppose this 40-tool library is realistic in a second way: any *given*
task only ever actually calls a handful of them — say 4 tools end up used
across the whole 20-step run, even though 40 exist. With the Tool Search
Tool, all 40 are declared with `"defer_loading": true` except the small
always-visible search tool itself (~50 tokens), and Claude searches for and
progressively *appends* only the schemas it actually needs — appended, not
swapped in, which is the specific detail that lets this coexist with prompt
caching rather than fighting it.

$$\text{JIT schema footprint} = (4 \times 250) + 50 = 1{,}050 \text{ tokens}$$

```
1 cache WRITE:  1,050 × $3.75 / 1,000,000 = $0.0039
19 cache READs: 1,050 × 19 = 19,950 tokens × $0.30/1,000,000 = $0.0060

TOTAL (JIT + cached) = $0.0039 + $0.0060 ≈ $0.0099
```

## The Ratio

```
All 40 tools, uncached:        $0.6000
All 40 tools, cached:          $0.0945   (84% cheaper than uncached)
JIT (4 tools) + cached:        $0.0099   (90% cheaper than all-cached,
                                          ~98% cheaper than uncached baseline)
```

This is not a rounding effect — it is the entire economic argument for
Chapter 8 (Context Engineering's "select" operation, and the specific
`defer_loading` mechanic covered in Section 11 below): **paying for tool
schemas the current task will never touch is one of the largest, most
avoidable line items in an agent's token bill**, and it gets *worse*, not
better, as you connect more MCP servers, because every server you add
grows the 40 toward 100 without growing the 4 tools any single task
actually needs. Anthropic's own published numbers land in the same range —
an ~85% token reduction and, notably, an *accuracy* improvement (not just a
cost one) when moving a large tool library behind Tool Search rather than
loading it all upfront; Section 9 explains why accuracy, not just tokens, is
at stake here.

## Key Takeaways for Section 8

A 40-tool, 250-token-each library costs $0.60 uncached and $0.09 cached
across a 20-step loop just in schema tokens — before a single tool has been
called. Loading only the handful of tools a task actually touches, via
`defer_loading` and the Tool Search Tool, cuts that further to roughly a
cent, because the appended (not swapped) discovery mechanism preserves the
caching benefit instead of trading it away. The ratio between "declare
everything upfront" and "load on demand" only grows as your tool library
grows — which is exactly the argument the next section makes from the
accuracy side instead of the cost side.

*Next: tokens are only half of what a bloated tool library costs you — the
other half is the model picking the wrong tool more often.*

---

# 9: Tool Selection Failures as the Library Grows

## The Intuition

Handing a new employee a drawer with 6 clearly labeled tools and asking them
to pick the right one is easy. Handing them a warehouse with 150 similarly
labeled tools and asking the same question is a different task entirely —
not because any individual tool got harder to understand, but because
*discriminating between many plausible-looking options* is itself a
cognitive load that scales with the size of the option set, independent of
each option's individual clarity. Tool selection inside a model's forward
pass works the same way: every additional tool in context is one more
candidate the model has to weigh against the others on every single
decision, and near-duplicate or overlapping tools (two different
`search_tickets` tools from two different MCP servers, say) make that
discrimination measurably harder, not easier.

## Where Degradation Shows Up

Published guidance and practitioner reporting converge on a rough shared
range rather than one precise cliff-edge number: tool-selection accuracy is
widely reported to degrade meaningfully somewhere in the **20–50 tool**
range for current-generation models, with the exact threshold depending on
how distinct the tools' names and descriptions actually are (Section 2's
whole subject) — a library of 50 sharply-differentiated tools degrades more
gracefully than a library of 20 that overlap in purpose. This is consistent
with, not contradicted by, Section 8's cost arithmetic: a large tool library
is expensive in tokens *and* it is a harder selection problem, and both
costs point toward the same fix — keep the tools actually in front of the
model at any one moment small, whether by careful curation or by the
just-in-time loading Section 11 covers.

## Why This Isn't Just a Cost Problem

It would be a much smaller issue if a bloated tool library only cost money —
you could simply decide to spend more. The reason it's treated as its own
failure mode, distinct from Section 8's token bill, is that Anthropic's own
measurements on the Tool Search Tool (Section 11) showed *accuracy*
improving alongside token reduction when a large library moved behind
on-demand discovery — evidence that the cost and the confusion share a root
cause (too many candidates visible at once) rather than being two unrelated
side effects of scale.

## What Actually Helps

Three levers, in the order this chapter has already built them: sharper,
more differentiated names and descriptions (Section 2) reduce ambiguity
between similar tools directly; consolidating fragmented primitives into
task-shaped tools (Section 3) reduces the *count* of tools competing for
attention in the first place; and, once the library is large enough that
neither of those is sufficient on its own, on-demand tool discovery
(Section 11) removes tools from the decision entirely until they're
actually relevant, rather than asking the model to ignore ninety-six
irrelevant options on every turn.

## Key Takeaways for Section 9

Tool-selection accuracy degrades as the number of visible tools grows,
roughly in the 20–50 tool range for current models, and the degradation is
worse when tools overlap in name or purpose. This isn't a separate problem
from Section 8's token cost — they share a cause — which is why sharper
descriptions, consolidation, and on-demand loading all show up as fixes for
both at once.

*Next: a short recap of where these many tools actually come from in the
first place, and why MCP doesn't make tool *design* optional.*

---

# 10: MCP as Tool Transport, Revisited

## The Recap

If you've been through this repository's earlier module on protocols
(B03), you've already seen the **N×M problem**: without a shared standard,
connecting $N$ applications to $M$ external systems requires up to $N
\times M$ bespoke integrations — every agent framework writing its own
one-off connector to every tool provider. The **Model Context Protocol
(MCP)** turns that into an **$N + M$** problem: any MCP-compliant client can
talk to any MCP-compliant server, so $N$ clients and $M$ servers require $N +
M$ total integrations, not $N \times M$. This chapter doesn't re-derive that
argument; it exists in B03. What belongs here, specifically, is the
corollary this chapter's whole subject implies:

## MCP Solves Transport, Not Design

MCP standardizes *how* a tool's schema and results travel between a server
and a model-calling client — the wire format, the discovery handshake, the
protocol envelope. It says nothing at all about whether the tool *behind*
that wire format is well-named, right-sized, or returns a lean response.
A poorly designed tool, exposed over MCP by a third-party server you don't
control, is exactly as poorly designed as a poorly written function call —
every principle in Sections 2 through 7 applies completely unchanged,
whether the tool is one you wrote in this notebook or one an MCP server
handed you at connection time.

This matters concretely and immediately, given the 2026 MCP ecosystem's
scale: independent surveys of public MCP servers have catalogued well over
one hundred thousand distinct published tools. Connecting a handful of
popular MCP servers can trivially put fifty or a hundred tools in front of
your agent — precisely the regime Section 9 just described as degrading
accuracy, and precisely the token bill Section 8 just priced out — without
you having written a single tool definition yourself. **"I used MCP" is an
answer to "how do tools arrive"; it is not an answer to "are these good
tools," and conflating the two is the single most common way a
well-intentioned agent ends up with a bloated, confusing tool set it never
consciously chose.**

## The Practical Implication

Treat every MCP server you connect the same way you'd treat a new
dependency: read what it actually exposes before wiring it in wholesale.
If a server offers forty tools and your agent's task only ever needs four
of them, Section 11's `defer_loading` mechanism (which works identically
whether the underlying tool came from MCP or was hand-defined) is the right
tool for containing the cost — not avoiding MCP, and not silently accepting
a 40-tool context because the server offered 40 tools.

## Key Takeaways for Section 10

MCP is a transport and discovery standard — it collapses N×M integration
work into N+M — but it makes no claim about tool quality, and the scale of
the current MCP ecosystem means connecting even a few servers can easily
exceed the tool counts Section 9 flagged as degrading. Every tool arriving
over MCP is still subject to every design principle in this chapter.

*Next: the concrete platform features built specifically to survive a
tool library too large to declare all at once.*

---

# 11: Advanced Tool Use: Search, Deferred Loading, Programmatic Calling

## Tool Search and `defer_loading`

Section 8's dry-run already built the arithmetic; this section names the
actual mechanism. Any tool can be marked `"defer_loading": true` in its
definition — it's still declared in the request's `tools` array (so it's
known to exist and can be found), but its full schema is *not* expanded into
the model's context until it's actually needed. A small, always-resident
tool search tool (a regex- or BM25-based search over the deferred tools'
names and descriptions, currently exposed as the
`tool_search_tool_regex_20251119` type) lets the model look up and pull in
just the tools relevant to the current step. Anthropic's own measurements,
across a 50-plus tool setup: roughly **85% less token consumption** (about
8.7K tokens versus about 77K for the same tool count declared upfront), and
—the result worth remembering over the cost saving — a genuine **accuracy
improvement**: Opus 4 went from 49% to 74%, and Opus 4.5 from 79.5% to
88.1%, on their internal MCP tool-selection evaluation, simply by not
showing the model tools it didn't need yet. Use this once your tool
definitions exceed roughly 10K tokens or your library passes roughly 10
tools; skip it for small, frequently-all-used tool sets, where the search
tool itself is pure overhead.

## Programmatic Tool Calling

Standard tool use is a round trip per call: Claude calls, the result lands
back in Claude's own context, Claude reads it, decides, calls again. For a
task that chains many tool calls — fetch a list, then fetch details for each
item, then aggregate — every intermediate result passes through the
model's context even though only the final aggregate actually matters.
Programmatic tool calling lets Claude write a short script that runs inside
a code-execution container; when that script calls a tool, the container
pauses, the real tool call executes, and the *result returns to the running
code*, not to Claude's context — only the script's final printed output
comes back to the model. Anthropic reports a 37% token reduction on a
complex multi-step research task (43,588 → 27,297 tokens) purely from
routing the intermediate tool results through code instead of through the
model's own context, plus the latency savings from collapsing what would
have been many separate inference passes into one script execution. This is
the more powerful sibling of Section 4's "give the model what it needs
next, not everything" — instead of trusting each tool's return-value design
alone to keep the model's context lean, the aggregation step itself moves
outside the model's context entirely.

## Tool Use Examples

For tools with genuinely ambiguous or convention-heavy input shapes — nested
structures where a *valid* JSON payload isn't necessarily a *correct* one,
or several optional fields whose typical co-occurrence isn't obvious from
the schema alone — an `input_examples` array attached to the tool definition
gives the model concrete worked examples of correct calls, the same
principle as this repository's own dry-run convention, applied to a tool
schema instead of a chapter's notes. Anthropic reports this closing a real
gap on complex-parameter tasks — 72% to 90% accuracy in their internal
testing — specifically on the class of error that a schema's types alone
cannot express: two fields that are only ever both present or both absent,
or a nested object whose shape varies by a sibling field's value.

## Choosing Between These Three

| Bottleneck you're actually seeing | Reach for |
|---|---|
| Tool schemas alone consume tens of thousands of tokens before the task starts | Tool Search + `defer_loading` |
| Intermediate tool results (not the schemas) are large and mostly get thrown away | Programmatic tool calling |
| The model keeps constructing subtly wrong arguments for one or two specific tools | Tool use examples |

These compose — a large MCP-sourced library behind `defer_loading`, with
programmatic calling for the multi-step aggregation task built on top of it,
is a completely normal combination for a serious agent, not an either/or
choice.

## Key Takeaways for Section 11

Tool Search Tool (`defer_loading`) cuts both token cost and — measurably —
selection accuracy when the library is large by hiding unneeded schemas
until they're searched for; programmatic tool calling keeps large
intermediate results out of the model's context entirely by running the
orchestration as code; tool use examples close the specific gap where a
schema's types are satisfied but the *convention* isn't obvious. All three
are 2025–2026-era platform features built directly in response to the exact
cost and accuracy problems Sections 8 and 9 derived from first principles.

*Next: everything this chapter fixed, and the one thing good tool design
was never going to fix on its own.*

---

# 12: What Good Tool Design Still Can't Fix

## The Honest Limit

Every technique in this chapter — clear naming, right-sized granularity,
lean return values, actionable errors, structured output, idempotency,
deferred loading — makes an individual tool call, and a set of tool calls,
easier for a model to get right. None of it decides *when* the model should
stop calling tools and check its own work, *what* an agent should remember
between one session and the next, or *who* is allowed to approve a
destructive call before it executes. Those are not tool-design questions —
they're loop-level and system-level questions, and naming them precisely
here is this chapter's actual final job, the same discipline Chapter 2
closed with.

| Missing capability | Symptom without it | Where it's built |
|---|---|---|
| **Deciding tool calls are trustworthy at all** | A well-designed tool can still return a *wrong but well-formatted* answer; nothing here verifies correctness | Chapter 6 |
| **Remembering which tools worked well last time** | Every session re-discovers the same tool-selection lessons from scratch | Chapter 9 (Memory) |
| **Approving a destructive call before it runs** | Section 7's `destructive` flag is inert until something reads it and gates on it | Chapter 16 |
| **Managing the *rest* of the context window** (not just tool schemas) | Section 8 only priced the tool-schema slice; the growing transcript tail is still Chapter 2 Section 11's unsolved problem | Chapter 4 |
| **Handling a library too large even for search to disambiguate cleanly** | Thousands of near-duplicate MCP tools across many servers | Chapter 4 (context engineering at scale) / multi-agent delegation (B04 later chapters) |

## Key Takeaways for Section 12

Good tool design is necessary and, on its own, insufficient — it makes each
individual decision easier for the model to get right, but it does not
verify outcomes, remember across sessions, gate destructive actions, or
manage the context window beyond the tool schemas themselves. Each of those
gaps has an exact chapter where it gets addressed, the same way Chapter 2
closed its own gap list.

*Next: the whole chapter, compressed into one table you can use as a
checklist the next time you write a tool definition.*

---

# 13: Key Takeaways + Master Decision Table

The single mental model for this chapter: **a tool schema is a user
interface, its user is a model with exactly one shot at reading it
correctly, and every ambiguity you leave in it becomes a silent guess made
on your behalf.** Everything else — granularity, return values, errors,
structured output, idempotency, and the platform features in Section 11 —
is a specific consequence of taking that one sentence seriously.

| I want to know... | Reach for | Key fact |
|---|---|---|
| Why the model keeps misusing a tool that "should" be obvious | Section 2 | The name, parameters, and description are the *entire* spec — nothing else is visible to the model |
| Whether to split one operation into many tools or bundle it | Section 3 | Consolidate around what a human would call "one task"; keep genuinely distinct or dangerous operations separate |
| What a tool should actually return | Section 4 | Only what's needed next; offer a verbosity control; truncate with a continuation handle, never silently |
| How to write a tool error message | Section 5 | State what was wrong and what a correct call looks like — it's read by a model with one retry, not a human debugging later |
| How to force a well-formed final answer or tool call | Section 6 | `output_config.format` for final answers, `strict: true` on `input_schema` for tool arguments — neither supports the full JSON Schema spec |
| How to make a tool safe to retry | Section 7 | Design for idempotency or use an idempotency key; offer `dry_run`; mark destructive tools explicitly for Chapter 16 |
| What a large tool library actually costs | Section 8 | ~$0.60 uncached → ~$0.09 cached → ~$0.01 with JIT loading, for a 40-tool/20-step example — cost scales with declared tools, not used tools |
| Why more tools can make the model worse, not just slower | Section 9 | Selection accuracy degrades past roughly 20–50 visible tools, worse with overlapping names/purposes |
| Whether MCP alone guarantees good tools | Section 10 | No — MCP standardizes transport (N×M → N+M); every design principle above still applies to an MCP-sourced tool |
| Which platform feature fixes which bottleneck | Section 11 | Tool Search/`defer_loading` for schema bloat, programmatic calling for large intermediate results, tool use examples for convention gaps |
| What tool design alone will never fix | Section 12 | Verification, cross-session memory, permission gating, and context management beyond schemas — each has its own later chapter |

**Connection forward:** Chapter 4 goes back to Section 8's dry-run and
Chapter 2's uncacheable growing tail and generalizes both into a single
problem — the context window as a finite, managed resource with an explicit
budget — introducing the four operations (write, select, compress, isolate)
that every context-management technique in this repository, from here
forward, turns out to be one instance of.
