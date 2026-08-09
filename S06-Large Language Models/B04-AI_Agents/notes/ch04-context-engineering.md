# Chapter 4: Context Engineering

## Table of Contents

1. [Why This Chapter Exists](#1-why-this-chapter-exists)
2. [Context Rot: What the Research Actually Shows](#2-context-rot-what-the-research-actually-shows)
3. [The Token Budget as a Design Artifact](#3-the-token-budget-as-a-design-artifact)
4. [The Four Operations: Write, Select, Compress, Isolate](#4-the-four-operations-write-select-compress-isolate)
5. [Compaction in Depth: The Actual API Mechanism](#5-compaction-in-depth-the-actual-api-mechanism)
6. [What Compaction Silently Destroys](#6-what-compaction-silently-destroys)
7. [Tool-Result Clearing: The Lightest-Touch Compaction](#7-tool-result-clearing-the-lightest-touch-compaction)
8. [Prompt Caching vs. Compaction: A Direct Tension](#8-prompt-caching-vs-compaction-a-direct-tension)
9. [Structured Note-Taking and Agentic Memory](#9-structured-note-taking-and-agentic-memory)
10. [Context Isolation, Previewed](#10-context-isolation-previewed)
11. [Dry-Run: Softmax Dilution as Context Rot's Mechanism](#11-dry-run-softmax-dilution-as-context-rots-mechanism)
12. [Dry-Run: A 200K-Window Budget Table Across 30 Steps](#12-dry-run-a-200k-window-budget-table-across-30-steps)
13. [What This Chapter Still Leaves Open](#13-what-this-chapter-still-leaves-open)
14. [Key Takeaways + Master Decision Table](#14-key-takeaways--master-decision-table)

---

# 1: Why This Chapter Exists

## The Reframe

Chapters 2 and 3 both quietly deferred the same question. Chapter 2's Section
11 dry-run showed a modest 15-step agent processing over 160,000 input tokens
because the transcript resends in full every step, and closed by naming
exactly this — "the cure for growth is Chapter 4's entire subject." Chapter
3's Section 8 dry-run showed a 40-tool schema library costing real money on
every turn regardless of whether that turn used any of those tools. Both
chapters were really asking the same question from different angles: *what
occupies the context window right now, and does it deserve to be there?*

This chapter makes that question the whole subject, and asks you to make one
mental shift first: stop thinking about a prompt as "what do I say to the
model" and start thinking about the context window as **a managed, finite,
adversarially degrading resource** — adversarial in the specific sense that
its contents don't just sit there neutrally; stale tool results, resolved
errors, and superseded instructions actively compete for the model's
attention against whatever actually matters *right now*, and more tokens
does not mean more capability, it means more competition.

## Why "Just Use a Bigger Window" Doesn't Fix This

It's tempting to treat context length as a problem that model providers are
solving for you — every year the advertised window gets larger, so why
budget carefully at all? Section 2 answers this directly with real measured
research: a larger context window changes the *ceiling*, not the *rate of
degradation* within it. A model with a one-million-token window can still
degrade well before that ceiling, on the same task, the same way a warehouse
ten times larger doesn't make it easier to find one specific box — it makes
it easier to lose one.

*Everything mechanical in this chapter — the compaction API, tool-result
clearing, the caching interaction — is demonstrated against Anthropic's
Messages API, because that's the concrete, currently-documented mechanism
`ai_config`'s reference path can reach. But the underlying problem (a
transformer's attention has to spread itself across everything in the
window) and the four-operation framework in Section 4 are not
Anthropic-specific — they are the same reason every major agent harness in
2026, regardless of vendor, ships some version of compaction, memory files,
and sub-agent delegation.*

## Key Takeaways for Section 1

Context engineering treats the window as a finite, actively degrading
resource, not a larger-is-better buffer — this reframe from "what do I say"
to "what occupies the window and does it still deserve to" is the lens for
every section that follows.

*Next: what the actual research says happens as that window fills up — and
where a widely-repeated older claim about the shape of that degradation
needs updating.*

---

# 2: Context Rot: What the Research Actually Shows

## The Intuition

Picture a single overworked assistant taking notes in a meeting that never
ends. For the first twenty minutes, they can recall anything said, in order,
with full confidence. By hour four, everything is still technically "in
their notes" — but finding the one decision that matters means wading
through hours of superseded discussion, and their confidence in any single
recalled fact quietly drops, even though nothing was ever erased. **Context
rot** is the name for this phenomenon in language models: performance
degrading as input length grows, not because information falls out of the
window, but because a fixed amount of attention has to spread across an
ever-larger amount of content.

## What Changed Since the Original "Lost in the Middle" Result

The now-classic finding, from Liu et al.'s 2023 "Lost in the Middle" study,
was a clean **U-shape**: models retrieve information best when it sits near
the *start* or *end* of the context, and worst when it sits buried in the
*middle* — the mental model this chapter's notes started from and the one
most engineers still carry. It's a genuinely useful first approximation, and
it's why "put your most important instructions first and last" became
standard agent-prompting advice.

Chroma's July 2025 "Context Rot" technical report is worth citing directly
here because it complicates that picture in a way any current curriculum
should reflect: testing **18 frontier models** across Anthropic (Claude Opus
4, Sonnet 4, Sonnet 3.7/3.5, Haiku 3.5), OpenAI (o3, the GPT-4.1 family,
GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo), Google (Gemini 2.5 Pro/Flash, Gemini
2.0 Flash), and Alibaba (the Qwen3 family), Chroma found that **degradation
as input length grows is closer to monotonic than a clean U-shape** — every
one of the 18 models got measurably less reliable simply as input length
increased, independent of exactly where the needed information sat, and a
single distractor already measurably hurt performance relative to a
no-distractor baseline. One especially striking side finding: refusal
behavior itself diverged enormously under long input — GPT-3.5 Turbo
refused **60.29%** of tasks in the hardest condition, while Claude Opus 4
refused **2.89%** and GPT-4.1 refused **2.55%** — a reminder that "the model
got worse" sometimes literally means "the model gave up," a distinct failure
mode from a wrong answer confidently given.

*A note on doing this research correctly, for anyone extending this chapter
later: an earlier draft of this repository's own roadmap cited a specific
"98.1% → 64.1%" needle-position figure for this phenomenon. That exact pair
of numbers could not be traced to a verifiable primary source during this
chapter's research pass, so it has been deliberately dropped rather than
repeated — the Chroma figures above are the ones this chapter can actually
stand behind. If you ever find yourself repeating a specific statistic in
these notes, verify it traces to a named study before it goes in the
dry-run, not after.*

## Why This Matters for an Agent Specifically, Not Just a Single Prompt

A single long document is one thing; an agent's transcript is a *worse*
case, because Chapter 2's loop is append-only — every tool observation,
every intermediate "let me check that" completion, every resolved error,
stays in the window forever unless something actively removes it. Coding
agents are cited as the primary real-world instance of this: a long tool-use
session accumulates exactly the kind of low-signal, high-volume content
(stack traces, file dumps, retried commands) that Section 3 of Chapter 3
already flagged as a return-value design problem, and Section 2's research
says that content doesn't just sit there costing tokens — it measurably
degrades the model's reliability on everything else in the window too.

## Key Takeaways for Section 2

The classic "lost in the middle" U-shape is a useful first approximation but
not the full current picture — Chroma's 2025 study across 18 models found
degradation that tracks input length more than position specifically, plus
wildly divergent refusal behavior under long input as its own distinct
failure mode. A bigger context window raises the ceiling this degradation
operates under; it does not remove the degradation itself.

*Next: turning "the window is finite" from a fact you know into a table you
actually maintain.*

---

# 3: The Token Budget as a Design Artifact

## The Intuition

A household with a fixed monthly income that never writes a budget doesn't
usually run out of money on the same day every month — it runs out
unpredictably, exactly when a rarely-tracked category (car repairs, a
subscription nobody canceled) quietly grew larger than anyone was watching.
An agent's context window is the same: without a written-down allocation,
"we ran out of context" always seems to happen at a surprising moment,
because nothing was tracking which category actually consumed it.

## Writing the Budget Down

Every occupant of the context window belongs to one of a small number of
categories, and a serious agent design states, in writing, roughly how much
of the window each one is allowed:

| Category | Example content | Grows per step? | Illustrative hard cap |
|---|---|---|---|
| System prompt | Durable instructions, persona, output format | No (fixed) | 3,000 tokens |
| Tool schemas | Every callable tool's `input_schema` (Ch 3) | No, unless tools change mid-run | 10,000 tokens (or far less with `defer_loading`, Ch 3 §11) |
| Memory / notes | An injected `NOTES.md`-style summary (Section 9) | Occasionally (on refresh, not per step) | 2,000 tokens |
| Retrieved documents | RAG chunks, search results | Per retrieval call | 20,000 tokens per call |
| Working files | Full file contents currently open for editing | While a file is "open" | 15,000 tokens per file |
| Trajectory (the growing tail) | Every prior completion + tool observation | **Yes, every step** | No hard cap — this is what compaction exists to bound |

Writing this table down does two things a mental estimate can't: it turns
"context feels full" into "the trajectory row is at 140,000 of an allotted
150,000," a specific, actionable number: and it makes the one row that
*can't* have a hard cap — the trajectory — visible as the one row that needs
an active eviction policy, which is exactly what Sections 5 through 10
build.

## Key Takeaways for Section 3

Every occupant of the context window fits one of a small number of
categories, and writing down an explicit budget per category turns "we ran
out of context" from a surprising event into a monitored, predictable one —
with the trajectory row flagged as the one category that structurally cannot
have a fixed cap and therefore needs an active eviction policy.

*Next: the one framework every context-management technique in this chapter
turns out to be an instance of.*

---

# 4: The Four Operations: Write, Select, Compress, Isolate

## The Intuition

Imagine managing a shared team whiteboard during a long, complex project.
You have exactly four moves available: **write** something down somewhere
*other* than the whiteboard so you don't have to keep it in your head
(a notebook); **select** just the sticky notes relevant to today's meeting
out of the box of everything ever written; **compress** yesterday's cluttered
half of the board down to one summary line before today's work starts; or
**isolate** a sub-problem onto its own separate whiteboard in another room so
its mess never touches the main one. Anthropic's applied AI team, writing
about the techniques behind Claude Code and their own agent harnesses,
frames essentially every context-management technique as one of these four
moves — which matters practically because it means you don't need a new
mental category every time you meet a new technique; you need to ask which
of these four it is.

## The Four, With a Concrete Example Each

**Write** — externalizing information out of the context window into
persistent storage (a file, a database, a scratchpad) so it exists without
occupying tokens until it's needed. The clearest illustration Anthropic
gives is Claude playing Pokémon across thousands of game steps spanning
multiple context resets, by maintaining an external `NOTES.md`-style file
with precise tallies, a location map, and strategy — knowledge that survives
a reset because it was never *only* in the context window to begin with.
Section 9 goes deeper on this specific pattern.

**Select** — retrieving just-in-time instead of loading everything upfront.
Chapter 3, Section 11's Tool Search Tool is a select operation applied to
tool schemas specifically; the identical idea applies to documents (RAG:
retrieve the 3 relevant chunks, not the whole corpus) and to memory (pull
back only the notes relevant to the current subtask, not the entire
accumulated notes file).

**Compress** — reducing what's *already* in the window down to the tokens
that still matter: summarizing resolved turns, trimming raw tool output down
to its conclusion, dropping a finished sub-task's scaffolding once its
result has been recorded. Compaction (Section 5) and tool-result clearing
(Section 7) are both compress operations — they differ in how aggressively
they compress and what they're willing to lose.

**Isolate** — splitting work across genuinely separate context windows so
one task's noise never contaminates another's. A sub-agent dispatched to
explore a codebase and report back returns a condensed 1,000–2,000-token
summary to the lead agent's context, while every file it opened and every
dead end it explored along the way stays confined to its own, disposable
context. Section 10 previews this; Chapter 13 builds it properly.

## Why This Taxonomy Is Worth Having

Without it, "context management" reads as an unordered grab-bag of
unrelated tricks — summarization here, RAG there, sub-agents somewhere else,
each learned as its own special case. With it, a new technique you encounter
later in this field gets classified in one sentence ("that's a select
technique — it's just RAG applied to memory instead of documents") instead
of feeling like new territory every time.

## Key Takeaways for Section 4

Write, select, compress, and isolate are not four separate techniques to
memorize — they're the four available moves, and every concrete
context-management mechanic in Sections 5 through 10 (compaction, tool-result
clearing, memory files, sub-agents) is one or more of these four applied to
a specific part of the window.

*Next: compress, in its heaviest and most automated form — what actually
happens, mechanically, when a real API compacts a conversation.*

---

# 5: Compaction in Depth: The Actual API Mechanism

## The Intuition

Compaction is the agent equivalent of a meeting chair periodically saying
"let's pause and summarize where we are before we keep going" — not because
the earlier discussion was worthless, but because carrying every word of it
forward verbatim costs more than carrying forward what was *decided*.

## The Mechanism, Precisely

Anthropic's Messages API exposes this as a beta content-management
operation. You enable it via `context_management.edits` with an entry of
type `compact_20260112` (beta header `compact-2026-01-12`), configured with
a `trigger` — by default `{"type": "input_tokens", "value": 150000}`, with a
platform-enforced floor of 50,000 tokens on that value. When the request's
input tokens cross that trigger, the API runs one **additional sampling
pass** that generates a `compaction` content block — a summary of everything
in the conversation up to that point — and prepends it to the assistant's
response, before any of the model's normal text for that turn.

```
{"content": [
    {"type": "compaction", "content": "Summary of the conversation so far: ..."},
    {"type": "text", "text": "Based on what we've established, ..."}
]}
```

The contract on the *next* request is what makes this a real compress
operation and not just a summary appended on top of everything: once you
append that response (compaction block included) back onto `messages` and
send the next request, **the API drops every content block that came before
the compaction block.** The summary isn't extra — it's a replacement for
everything it summarizes.

```python
response = client.beta.messages.create(
    messages=[{"role": "user", "content": "..."}],
    betas=["compact-2026-01-12"],
    context_management={"edits": [{"type": "compact_20260112"}]},
)
messages.append({"role": "assistant", "content": response.content})
# next request: everything before the compaction block is gone from the
# model's effective input, even though you're still storing it locally
```

Two operational details worth internalizing before you rely on this:
compaction can optionally pause immediately after generating the summary
(`pause_after_compaction: true` returns `stop_reason: "compaction"`, letting
your harness inject fresh instructions before continuing — a direct hook for
Section 6's re-injection fix) and, per Chapter 1's cost-accounting habits,
**compaction is not free** — it costs one extra sampling call over the
*entire* pre-compaction context, and the response's `usage.iterations`
breaks that cost out separately from the normal turn's tokens specifically
so you don't accidentally undercount it (Section 12's dry-run prices this
exactly).

## Compaction as a Product Feature vs. Compaction as an API Primitive

It's worth distinguishing the raw API primitive above from what a shipped
product like Claude Code builds *on top of* it: layered, cheaper
interventions that fire before the expensive `compact_20260112`-style
summarization is needed at all — clearing bulky tool results to disk early
(a lightweight, continuous form of Section 7's tool-result clearing), then
a full summarization pass only once headroom actually runs low, then a
user-triggered `/compact` at a natural task boundary as a manual escape
hatch. The lesson generalizes past any one product: **compaction is best
treated as a ladder of increasingly aggressive interventions, not a single
on/off switch** — reach for the cheapest one that solves the problem before
reaching for a full-context summarization pass.

## Key Takeaways for Section 5

`compact_20260112` triggers on an input-token threshold (150,000 by
default), generates one summary via an extra sampling pass, and the API
then drops everything before that summary on subsequent requests — a real
compress operation, not decoration. It costs a real extra call, billed
separately in `usage.iterations`, and production harnesses generally layer
cheaper interventions (tool-result clearing, manual triggers) ahead of a
full compaction pass rather than relying on one threshold alone.

*Next: summarization is lossy by construction — what, specifically, does it
tend to lose, and how do you get it back?*

---

# 6: What Compaction Silently Destroys

## The Intuition

Ask a colleague to summarize a two-hour meeting in three sentences, and
you'll get the *decisions* — but you will very rarely get *why* a rejected
option was rejected, or the exact phrasing of an instruction someone gave at
minute four that quietly shaped everything after it. Summarization
optimizes for "what happened," and what happened is usually not the same
information as "what constraint must every future step obey."

## The Concrete Loss List

Compaction's summary, generated by the model itself, tends to systematically
under-preserve four things: the **original system-level instructions and
style rules** the user gave at the very start of the session (they were true
on turn 1 and are still true on turn 200, but nothing marks them as
load-bearing the way a resolved decision from turn 50 gets marked);
**intermediate reasoning** that led to a decision, as opposed to the
decision itself (useful when a later step needs to reconsider that decision
under new information, and finds only the conclusion, not the argument);
**why-decisions** specifically — "we chose Postgres over SQLite because the
task requires concurrent writes" compresses far more easily to "using
Postgres" than the reasoning survives; and, most dangerously per Section 5's
mechanics, **any error the agent was mid-way through investigating right as
compaction triggered** — a summary generated *during* debugging often
records "encountered an error in module X" and drops the specific stack
trace or reproduction steps that made the error tractable in the first
place, which is exactly the Gotcha this chapter opens with in Section 13.

## Two Concrete Mitigations

**Durable instruction re-injection**: since compaction's `pause_after_compaction`
hook (Section 5) gives you a clean point to act before the conversation
continues, use it to re-append the original system-level constraints
verbatim immediately after the summary, rather than trusting the summary to
have preserved them faithfully. This is cheap — a few hundred tokens — and
converts "the instructions might have survived summarization" into "the
instructions are guaranteed to be present regardless of what the summary
kept."

**On-disk decision logs**: apply Section 4's "write" operation specifically
to *decisions and their reasoning*, not just to task state — a running,
append-only log entry per significant choice ("chose X over Y because Z"),
written to disk the moment the decision is made, independent of whether
compaction ever touches the conversation containing it. This is strictly
cheaper than trying to make the *summary* smarter, because it sidesteps the
lossy-compression problem entirely: the reasoning was never only inside the
part of the context that gets thrown away.

## Key Takeaways for Section 6

Compaction reliably loses four things — durable instructions, intermediate
reasoning, why-decisions, and whatever error was mid-investigation at
trigger time — because a summary optimizes for "what happened," not "what
must still be obeyed" or "why." Re-inject durable instructions right after
compaction rather than trusting the summary, and write decision reasoning to
an on-disk log at decision time rather than hoping it survives a later
summarization pass.

*Next: the smallest, safest compress operation available — one that never
needs a model call at all.*

---

# 7: Tool-Result Clearing: The Lightest-Touch Compaction

## The Intuition

If compaction (Section 5) is "summarize the whole meeting," tool-result
clearing is "once we've acted on last week's delivery receipt, shred the
receipt but keep the line in the ledger that says the delivery happened."
The raw tool output that led to a decision is usually worthless the moment
the decision is made and recorded — but unlike a full compaction pass,
clearing it doesn't require a model call, a summary, or any judgment at all,
which is exactly why it's the cheapest tool in this chapter's kit.

## The Mechanism

Anthropic exposes this as a distinct, separate beta from compaction — beta
header `context-management-2025-06-27`, configured via
`context_management.edits` with a strategy of `clear_tool_uses_20250919`
(clears old `tool_result` content; an optional `clear_tool_inputs: true`
also clears the corresponding `tool_use` arguments that produced them) or
`clear_thinking_20251015` (clears extended-thinking blocks once they're no
longer needed). This is a **prune**, not a summarize: the cleared content is
simply removed, leaving the surrounding conversation structure — including
the fact that a tool was called and roughly what it returned, if you choose
to leave a short marker — intact.

## Recency Bias and Where to Put What Matters

Clearing old tool results interacts with a second phenomenon worth naming
directly: models weight *recent* context more heavily than older context,
all else equal — which is generally desirable (the most recent tool result
usually is the most relevant one) but has a specific failure mode: a
critical constraint stated once, early, and never repeated, competes on
unequal footing against whatever was said three turns ago. This is a second,
independent reason (beyond Section 6's compaction-loss argument) to
re-inject durable instructions periodically rather than trusting a single
early mention to stay salient across a long, tool-result-heavy transcript.

## Choosing Between Clearing and Compaction

| Question | Reach for |
|---|---|
| Is this tool result stale, but everything else is fine? | `clear_tool_uses_20250919` — no model call, no summary needed |
| Extended-thinking blocks from resolved sub-problems piling up? | `clear_thinking_20251015` |
| The *whole conversation* is approaching the window limit, not just one category | `compact_20260112` (Section 5) — this needs an actual summary, not a prune |

## Key Takeaways for Section 7

Tool-result clearing (`clear_tool_uses_20250919` / `clear_thinking_20251015`)
is a prune, not a summary — cheaper than compaction because it requires no
model call, appropriate when specific stale content is the problem rather
than the whole transcript. Recency bias means anything genuinely durable
should be re-stated periodically regardless of which compress mechanism is
in play, not left to a single early mention.

*Next: the one place these compress operations actively fight against
another technique you should already be using on every request.*

---

# 8: Prompt Caching vs. Compaction: A Direct Tension

## The Intuition

Prompt caching (Chapter 1, Section 11; Chapter 3, Section 8) works by
betting that a prefix will stay byte-for-byte identical across many calls,
so it's worth paying a small write premium once to get a 90% discount on
every read after. Compaction's entire purpose is to *change* the content
sitting in that same region of the conversation. These two techniques are
not just unrelated — they are, by construction, in tension: the moment
compaction rewrites the earlier part of a conversation into a summary, any
cache built on the old version of that prefix is invalidated, and the very
next call pays a full cache-write premium on content that, moments ago, was
costing 90% less.

## The Concrete Fix

The API-level mitigation is specific and worth using exactly as documented:
put a `cache_control: {"type": "ephemeral"}` breakpoint at the **end of the
system prompt**, separate from wherever the compaction block will land, and
optionally another on the compaction block itself once it exists. This keeps
the system prompt — genuinely stable across the whole run — cached
independently of the conversation body, so a compaction event invalidates
only the part of the cache that was going to change anyway, not the
durable prefix sitting in front of it.

```python
{"system": [{"type": "text", "text": "You are a coding assistant...",
             "cache_control": {"type": "ephemeral"}}]}
# compaction rewrites the conversation body; the system block above,
# cached separately, survives that rewrite untouched
```

## Why This Still Doesn't Fully Resolve the Tension

Splitting the cache breakpoint helps the *system prompt* survive compaction
cheaply — it does nothing for the conversation body itself, which is exactly
the part compaction just changed and therefore exactly the part whose cache
was already going to be paid for fresh. The honest framing, and the one
worth carrying into Chapter 17's cost-hardening work: caching optimizes for
*stability*, compaction optimizes for *change*, and no configuration makes
both free at once on the same content — you are choosing, deliberately,
which region of the window gets which property.

## Key Takeaways for Section 8

Caching bets on a stable prefix; compaction changes the conversation
specifically to keep it small — applied to the same content, they fight.
Isolating the system prompt behind its own `cache_control` breakpoint
protects that one durable region from a compaction event's cache
invalidation, but the conversation body itself unavoidably pays a fresh
cache-write cost the moment it's compacted; this is a real trade-off, not a
bug to configure away entirely.

*Next: the "write" operation from Section 4, built out into a full pattern
for surviving far longer than any single context window.*

---

# 9: Structured Note-Taking and Agentic Memory

## The Intuition

A field researcher on a six-month expedition doesn't try to hold every
observation in active memory — they keep a field notebook, written
continuously, that outlives any single day's attention span and gets
re-read at the start of the next. **Structured note-taking** is this same
habit applied to an agent: maintaining an external file (commonly a
`NOTES.md`, a to-do list, or a structured JSON scratchpad) that the agent
writes to during the task and reads back from at the start of later turns
or after a context reset — a "write" operation (Section 4) specifically
aimed at surviving longer than any single context window ever will.

## Why This Beats Trying to Keep Everything in Context

The clearest illustration is Claude playing Pokémon across *thousands* of
game steps spanning many separate context windows and resets — nowhere near
survivable by keeping everything in one conversation, however large. What
made it work was an external notes file tracking precise tallies, a
location map, and current strategy: knowledge that was never *only* inside
the context window, so a reset cost nothing more than the price of reading
that file back in. This is the load-bearing insight of the whole pattern:
**the file is the actual long-term state; the context window is a cache of
whatever part of it the current turn needs**, not the other way around.
Anthropic has also shipped this as a first-class capability — a memory tool
that gives Claude direct, structured file-based read/write access for
exactly this purpose, rather than relying on the notes convention living
entirely in your own prompt engineering.

## Where This Sits Relative to Everything Else in This Chapter

Structured notes solve a different problem than compaction (Section 5) or
tool-result clearing (Section 7): those two are about *safely discarding*
content that's still, technically, only ever been in the conversation.
Notes are about *never having relied on the conversation being the only copy
in the first place*. A mature agent uses both: notes for anything that must
survive past this session's context entirely, compaction and clearing for
managing what's left once you've decided the conversation itself is the
right home for it.

## Key Takeaways for Section 9

Structured note-taking externalizes knowledge into a file the agent reads
and writes across turns and resets, so a context reset costs nothing more
than re-reading the file — the concrete, working version of Section 4's
"write" operation, and the specific pattern that let Claude's Pokémon run
survive thousands of steps across many separate context windows.

*Next: the "isolate" operation, previewed here and built properly two
chapters from now.*

---

# 10: Context Isolation, Previewed

## The Intuition

Sometimes the cheapest way to compress a mess is to never let it accumulate
in your context at all. If a task genuinely decomposes into "go explore this
large, noisy space and come back with a short answer," the cleanest design
is often not a clever compression scheme applied after the fact — it's
giving that exploration its own, disposable context window from the start.

## The Mechanism, Briefly

A **sub-agent** is dispatched with its own clean context, does its exploring
— reading files, running searches, hitting dead ends, whatever the task
requires — entirely inside that isolated window, and returns only a
condensed result, typically in the **1,000–2,000-token range**, to the
parent agent's context. Every dead end, every intermediate file the
sub-agent opened, every retry it needed, stays confined to a context that
gets discarded once the sub-agent finishes. The parent's context grows by
one clean summary, not by the sum of everything the exploration touched.

## Why This Is Genuinely a Different Move, Not Just Aggressive Compression

It's tempting to see this as "compression, just done by a second model
instead of a summarization call" — but the distinction matters:
compression (Sections 5–7) acts on content that *already entered* the
parent's context and now needs shrinking. Isolation prevents that content
from ever entering the parent's context to begin with. The parent never
pays the "lost in the middle" tax (Section 2) on the sub-agent's noisy
exploration, because that noise was never in the parent's window at any
point to compete for attention.

## Key Takeaways for Section 10

Isolation dispatches noisy, exploratory work to its own disposable context
and returns only a short, clean summary (roughly 1,000–2,000 tokens) to the
parent — a structurally different move from compression, since the noise
never enters the parent's window in the first place rather than entering
and later being shrunk. Chapter 13 builds this into a full multi-agent
architecture.

*Next: the two arithmetic sections this chapter owes you — first, the
mechanism-level intuition for why a diluted context genuinely produces worse
attention, not just a vaguer feeling of "too much stuff."*

---

# 11: Dry-Run: Softmax Dilution as Context Rot's Mechanism

## The Intuition

Recall from B01's attention chapter: every token's attention distribution
comes from a **softmax** over raw scores, and softmax is a *competition* —
every candidate's share of attention is its own score relative to the sum
of everyone else's. This dry-run asks a narrow, concrete question: if one
token in context is genuinely the relevant one, and everything else has a
roughly comparable (but slightly lower) raw score, what happens to the
relevant token's actual attention weight as the number of competing
tokens grows from 10 to 1,000? This is *not* a full account of measured
context rot (Section 2's Chroma findings involve many additional factors —
training-length mismatch, positional encoding effects, distractor content)
— it is the one clean, mechanism-level piece of the story that pure
attention math can show you directly, with pen and paper.

## The Math

For one relevant token with score $s_{\text{rel}}$ competing against $N$
irrelevant tokens each with score $s_{\text{irr}}$, softmax gives the
relevant token's attention weight as:

$$w_{\text{rel}} = \frac{e^{s_{\text{rel}}}}{e^{s_{\text{rel}}} + N \cdot e^{s_{\text{irr}}}}$$

Here $e^{s_{\text{rel}}}$ is the (unnormalized) preference for the relevant
token, and the denominator is that same preference plus the combined
preference of every one of the $N$ distractors — exactly B01's
$\text{softmax}(QK^T/\sqrt{d_k})$ mechanism, with the distractor count $N$
pulled out as the variable of interest instead of held fixed.

## The Dry-Run

Fix $s_{\text{rel}} = 5.0$ and $s_{\text{irr}} = 4.0$ — a real, meaningful
gap (the relevant token is genuinely preferred over any *one* distractor),
computed by hand with $e^5 \approx 148.41$ and $e^4 \approx 54.60$:

```
N = 10 competing (irrelevant) tokens:
  numerator   = e^5.0                = 148.41
  denominator = e^5.0 + 10 * e^4.0   = 148.41 + 10 * 54.60
              = 148.41 + 546.00 = 694.41
  weight = 148.41 / 694.41 = 0.2138  ->  ~21.4% attention on the relevant token

N = 1,000 competing (irrelevant) tokens, SAME per-token scores:
  numerator   = e^5.0                  = 148.41
  denominator = e^5.0 + 1000 * e^4.0   = 148.41 + 1000 * 54.60
              = 148.41 + 54,600.00 = 54,748.41
  weight = 148.41 / 54,748.41 = 0.002712  ->  ~0.27% attention on the relevant token
```

## The Counterintuitive Result — Read This Twice

Nothing about the relevant token changed — its raw score is still exactly
5.0, still the single highest score in the entire context, still
*unambiguously* the right answer if you were to rank every candidate by
score alone. And yet its actual share of attention collapsed by roughly
**79×**, from about 21% down to about 0.27%, purely because the number of
mediocre competitors grew. This is the mechanism-level version of "a bigger
window doesn't fix rot" from Section 1: adding more context — even
context that's individually *worse* than what you're looking for — doesn't
just fail to help, it actively dilutes attention away from the token that
matters, through nothing more exotic than what the softmax denominator does
to every other candidate's share.

## Key Takeaways for Section 11

Softmax attention is a zero-sum competition for a fixed total of 1.0 —
holding the relevant token's score fixed while growing the number of
competing tokens from 10 to 1,000 collapses its attention weight from about
21% to about 0.27%, a roughly 79× drop, with the token's own quality
completely unchanged. This is one concrete, hand-computable mechanism behind
context rot, not the complete empirical picture Section 2 describes, but the
part that explains *why* more tokens in the window is never neutral.

*Next: the same arithmetic habit Chapters 1–3 have used for cost, applied
here to the one number that actually decides when compaction fires.*

---

# 12: Dry-Run: A 200K-Window Budget Table Across 30 Steps

## The Setup

Take a 200,000-token context window and an agent whose fixed prefix —
system prompt, tool schemas, and an injected memory-notes summary (Section
9) — totals **15,000 tokens** (3,000 system + 10,000 tools, the same figures
Chapters 1 and 3 already used, + 2,000 for notes). This agent is doing
heavier work than Chapter 1's modest example — it's reading real files and
search results, not short observations — averaging **6,200 tokens per step**
(6,000 tokens of tool observation + 200 tokens of completion). Use
`compact_20260112`'s actual default trigger from Section 5: compaction fires
once input tokens cross **150,000**.

$$\text{context}_k = 15{,}000 + (k - 1) \times 6{,}200$$

## Stepping Through the Run

```
Step  1: context = 15,000 + (0)(6,200)  =  15,000 tokens
Step  5: context = 15,000 + (4)(6,200)  =  39,800 tokens
Step 10: context = 15,000 + (9)(6,200)  =  70,800 tokens
Step 15: context = 15,000 + (14)(6,200) = 101,800 tokens
Step 20: context = 15,000 + (19)(6,200) = 132,800 tokens
Step 22: context = 15,000 + (21)(6,200) = 145,200 tokens   <- still under trigger
Step 23: context = 15,000 + (22)(6,200) = 151,400 tokens   <- crosses 150,000: COMPACTION FIRES
```

Solving $15{,}000 + (k-1)(6{,}200) \geq 150{,}000$ directly gives $k - 1 \geq
21.77$, so $k = 23$ is the first integer step where the threshold is
crossed — matching the step-by-step table exactly, and giving you the
general formula for where a compaction trigger lands for *any* fixed prefix
and per-step growth rate, not just this example's numbers.

## After Compaction

Per Section 5's mechanics, step 23's response includes a compaction block —
here, illustratively, a **1,500-token summary** (in the same range as
Section 10's sub-agent-return-summary size, since both are "condense
everything that just happened into a short brief") — and everything before
that block is dropped on the next request. The system prompt and tool
schemas survive untouched (Section 8's separate `cache_control` breakpoint),
so the new baseline is:

$$\text{context}_{24} = \underbrace{15{,}000}_{\text{system + tools, unchanged}} + \underbrace{1{,}500}_{\text{compaction summary}} = 16{,}500 \text{ tokens}$$

```
Step 24: context = 16,500 + (1)(6,200) =  22,700 tokens
Step 25: context = 16,500 + (2)(6,200) =  28,900 tokens
Step 30: context = 16,500 + (7)(6,200) =  59,900 tokens
```

## The Takeaway This Table Is Actually For

By step 30, this run has processed 30 real steps of heavy tool use, crossed
the compaction trigger exactly once, and sits at 59,900 tokens — comfortably
under the 150,000 threshold again, with 22 more steps of headroom before
it would need to compact a second time. Two things worth internalizing from
this specific arithmetic: first, the trigger point ($k=23$) is exactly
solvable from your own fixed-prefix and per-step numbers before you ever run
the agent, which means you can *predict* — not just observe after the fact —
when a given task shape will hit compaction; second, per Section 5's cost
note, step 23 itself was more expensive than a normal step, since it paid
for one extra sampling pass over the full 151,400-token pre-compaction
context specifically to produce that 1,500-token summary — a real, billed
cost that a naive per-step cost estimate (Chapter 1, Section 11's style)
would miss entirely if you forgot to add compaction's `usage.iterations`
line item on top of the normal turn.

## Key Takeaways for Section 12

Given a fixed prefix and a per-step growth rate, the step at which
`compact_20260112`'s default 150,000-token trigger fires is exactly solvable
in closed form, not something you discover by surprise mid-run. Compaction
resets the trajectory back down to (fixed prefix + summary size) rather than
zero, and that reset step itself costs one extra, separately-billed sampling
pass over the entire pre-compaction context — a cost easy to leave out of a
naive per-step budget.

*Next: everything this chapter's techniques fix, and the mistakes that show
up specifically when you reach for them without care.*

---

# 13: What This Chapter Still Leaves Open

## Real Gotchas, Named Precisely

**Summarizing away the error you were about to fix.** Section 6 named this
directly: if compaction triggers while the agent is mid-investigation of a
bug, the resulting summary tends to record "there was an error in module X"
and drop the specific stack trace, reproduction steps, and ruled-out
hypotheses that made the bug tractable — turning one more debugging step
into starting over. Mitigation: where your harness allows it, avoid
triggering compaction mid-investigation (a `pause_after_compaction` check
at a natural boundary, not an arbitrary token count, is worth the extra
engineering).

**Compaction breaking your cache prefix and tripling cost.** Section 8's
tension isn't theoretical — a harness that compacts frequently without
isolating the system prompt behind its own `cache_control` breakpoint pays a
full cache-write premium on the *entire* prefix every single time, turning
what should be a 90%-discounted read into a 25%-premium write, repeatedly,
across a long run.

**Assuming bigger windows fix rot.** Section 1 and Section 2 both said this
directly, and it's worth restating as a gotcha because it's the single most
common wrong inference from "the model now supports 1M tokens": window size
is a ceiling on how much content *can* fit, not a fix for what happens to
attention quality as that content grows, per Section 11's mechanism and
Section 2's measured results across 18 real models.

## What's Still Missing, By Design

| Missing capability | Symptom without it | Where it's built |
|---|---|---|
| **Knowing what to select without a full sub-agent** | Section 4's "select" is named but not implemented as its own retrieval system yet | Chapter 10 (Graphs for Knowledge / Agentic RAG) |
| **A real, structured, multi-agent isolation architecture** | Section 10 is a preview, not a working system | Chapter 13 |
| **Skills and progressive disclosure as a select mechanism for capabilities, not just documents** | This chapter only covered tools (Ch 3) and documents; capability-loading is its own pattern | Chapter 8 |
| **Verifying that compaction preserved what mattered** | Nothing here checks a summary's quality before trusting it | Chapter 6 (Loop Engineering) / Chapter 14 (Evals) |
| **Durable, crash-surviving state beyond one process's memory file** | Section 9's notes file helps across resets within a run; it doesn't address a killed process resuming cleanly | Chapter 12 |

## Key Takeaways for Section 13

The three gotchas — losing an in-progress error to summarization, breaking
prompt-cache economics through careless compaction, and trusting window size
alone to solve rot — are the concrete failure modes this chapter's
techniques introduce if applied mechanically rather than deliberately. What
this chapter leaves open (structured retrieval, real multi-agent isolation,
verifying compaction quality, crash-durable state) each has an exact later
chapter, the same discipline Chapters 2 and 3 closed with.

*Next: the whole chapter, compressed into one table.*

---

# 14: Key Takeaways + Master Decision Table

The single mental model for this chapter: **the context window is a finite,
actively degrading resource, and every technique here is one of four moves
— write, select, compress, isolate — applied to deciding what occupies it
right now.** Nothing in this chapter makes the window bigger; everything in
it makes better use of the size you already have.

| I want to know... | Reach for | Key fact |
|---|---|---|
| Whether a bigger context window fixes reliability | Section 2 | No — Chroma's 18-model study shows degradation tracking input length itself, not just position; window size raises the ceiling, not the rate of decay |
| How to stop being surprised by "we ran out of context" | Section 3 | Write down a per-category token budget with hard caps; only the trajectory category structurally can't have one |
| Which of the four moves a new technique actually is | Section 4 | Write (externalize), select (retrieve JIT), compress (shrink what's present), isolate (separate context entirely) |
| What actually happens when Claude compacts a conversation | Section 5 | `compact_20260112` triggers at 150K input tokens by default, generates one summary via an extra billed sampling pass, and the API drops everything before it on the next request |
| What a compaction summary reliably loses | Section 6 | Durable instructions, intermediate reasoning, why-decisions, and whatever error was mid-investigation — re-inject instructions and log decisions to disk separately |
| The cheapest way to shrink context without a summary | Section 7 | `clear_tool_uses_20250919` / `clear_thinking_20251015` — a prune, not a summary, no model call needed |
| Why compaction and caching fight each other | Section 8 | Caching bets on a stable prefix; compaction changes the conversation — isolate the system prompt behind its own `cache_control` breakpoint to limit the damage |
| How an agent survives past any single context window | Section 9 | Structured notes (`NOTES.md` / the memory tool) — the file is the real state, the context window is a cache of it |
| When to isolate instead of compress | Section 10 | When work is genuinely exploratory and noisy — give it its own disposable context and return only a ~1,000–2,000-token summary |
| Why more (even lower-quality) context actively hurts | Section 11 | Softmax dilution — a fixed-score relevant token's attention weight drops ~79× (21% → 0.27%) as competing tokens grow from 10 to 1,000 |
| When a specific agent design will hit its first compaction | Section 12 | Solve `fixed_prefix + (k-1) × per_step_growth ≥ trigger` for $k$ directly — don't wait to find out at runtime |

**Connection forward:** Chapter 5 zooms out from context specifically to the
full **harness** surrounding the loop — the system prompt, the permission
layer, the tool-execution sandbox, and the observability hooks — treating
everything this chapter and Chapter 3 built as components that live inside
a larger, deliberately designed shell around Chapter 2's core loop.
