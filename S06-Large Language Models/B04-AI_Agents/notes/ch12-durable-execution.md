# Chapter 12: Durable Execution & Long-Running Agents

## Table of Contents

1. [Why This Chapter Exists](#1-why-this-chapter-exists)
2. [Durable Execution Primitives](#2-durable-execution-primitives)
3. [Determinism Requirements](#3-determinism-requirements)
4. [Idempotency Keys and Exactly-Once Side Effects](#4-idempotency-keys-and-exactly-once-side-effects)
5. [Sessions, Sandboxes, and the Runtime Triad](#5-sessions-sandboxes-and-the-runtime-triad)
6. [Resume Semantics for Agents](#6-resume-semantics-for-agents)
7. [Queues, Schedules, and Event-Driven Triggers](#7-queues-schedules-and-event-driven-triggers)
8. [Timeouts and Heartbeats](#8-timeouts-and-heartbeats)
9. [Frameworks: Temporal, Inngest, and LangGraph's Checkpointer](#9-frameworks-temporal-inngest-and-langgraphs-checkpointer)
10. [Migration and Versioning of In-Flight Runs](#10-migration-and-versioning-of-in-flight-runs)
11. [Dry-Run: Expected Steps, Full-Restart vs Checkpoint-and-Resume](#11-dry-run-expected-steps-full-restart-vs-checkpoint-and-resume)
12. [Key Takeaways + Master Decision Table](#12-key-takeaways--master-decision-table)

---

# 1: Why This Chapter Exists

## Starting From Plain Language

A novelist writing a book longhand, with no copy anywhere else, loses the
entire manuscript if the one notebook burns. A novelist who mails a copy
of each finished chapter to a friend as they go loses, at worst, whatever
they were mid-sentence on when disaster struck. Neither novelist writes
differently, sentence by sentence — the difference is entirely in what
happens to their work when something outside their control goes wrong.

## The Actual Claim

A production agent — Chapter 11's graph, or Chapter 6's plain loop — is,
whether or not anyone designed it this way on purpose, **a distributed
system that happens to think in natural language**. It runs on a machine
that can be rebooted for a routine security patch, behind a deploy pipeline
that ships new code while requests are in flight, talking to a network
that occasionally just drops a connection for no discoverable reason. None
of this is exotic or rare — it is the unremarkable, everyday operating
reality of any process running on real infrastructure for more than a few
seconds. **Without durability, any one of these ordinary infrastructure
events silently destroys all progress on whatever the agent was doing** —
not because the agent's own logic was wrong, but because nothing outside
the agent's own memory ever wrote down what had already been accomplished.

```
        WITHOUT DURABILITY                  WITH DURABILITY

  step 1 ... step 46 ... [CRASH]      step 1 ... step 46 ... [CRASH]
       │                                    │
       ▼                                    ▼
  entire 46 steps of work            steps 1-46 already checkpointed --
  gone. next run starts              resume picks up at step 47,
  completely from scratch            costing seconds, not the whole run
```

## Why Chapter 11 Almost, But Doesn't Quite, Already Solve This

Chapter 11's checkpointer gave a graph runtime automatic, per-node
persistence essentially for free — a genuine structural advantage over a
plain loop. This chapter exists because two real gaps remain even with
that advantage available: first, not every agent is built as a graph —
Chapter 6's plain loop has no checkpointer to lean on, and needs the exact
same durability property built by hand. Second, even a graph's automatic
checkpointing doesn't, by itself, answer the harder questions this chapter
covers — what happens to a *side-effecting* tool call (an email actually
sent) when the process dies right after it fires but before that fact gets
recorded (Section 4), or how a scheduler handles 200 queued runs competing
for the same resources (Section 7). Durability is necessary but not
sufficient; this chapter is what "sufficient" actually requires.

## Key Takeaways for Section 1

A production agent is a distributed system whether or not it was designed
as one — ordinary infrastructure events (a crash, a deploy, a dropped
connection) will eventually happen, and without durability, any single one
of them destroys all progress made so far. Chapter 11's graph checkpointer
solves part of this for free; this chapter builds the same property by
hand for a plain loop, and covers the harder problems (exactly-once side
effects, scheduling under load) a checkpointer alone doesn't solve.

*Next: the actual architectural split that makes any of this tractable.*

---

# 2: Durable Execution Primitives

## Starting From Plain Language

A recipe card that says "add the eggs" is instructions; the eggs
themselves, sitting in the refrigerator, are a physical fact about the
world that either happened or didn't. Confusing the two — treating the
instruction as if it were the same kind of thing as the fact — is exactly
the mistake durable execution frameworks are built to prevent.

## Orchestration as a Replayable Workflow

**Workflow code** is the recipe — pure orchestration logic describing what
should happen and in what order — and it must be **replayable**: capable
of being re-executed from the beginning, deterministically, to reconstruct
exactly where execution had gotten to, without actually re-performing any
of the real-world effects along the way. This is the single most
counterintuitive idea in this chapter, worth sitting with: replay doesn't
mean "redo the work" — it means "re-run the *decision-making* code so the
runtime can figure out which step it was on," while the actual
already-completed effects are served from a record instead of happening
again.

## Model/Tool Calls as Retryable Activities

**Activities** are the eggs — the actual, real-world, potentially-failing
operations: an LLM call, a tool execution, a database write, a network
request. Activities are explicitly allowed to be non-deterministic (an LLM
call can return something different on a retry; a network call can time
out once and succeed the next time) specifically *because* they sit
outside the replay path — the workflow doesn't re-run an activity's actual
logic during replay, it looks up what that activity already returned, the
first and only time it genuinely executed.

## State as an Event-History Log

The mechanism that makes replay possible at all: every meaningful thing
that happened — an activity started, an activity completed with a specific
result, a timer fired — gets appended to an **event-history log**, and
replaying a workflow means re-running the workflow's own code while
feeding it the *recorded* results from that log instead of actually
re-invoking each activity. The log, not the process's live memory, is the
actual source of truth for "how far did this workflow get."

```
        THE TEMPORAL-STYLE SPLIT

   ┌─────────────────────────┐         ┌──────────────────────────┐
   │      WORKFLOW              │         │        ACTIVITIES           │
   │  (orchestration logic)      │◀───────▶│  (real, non-deterministic   │
   │  MUST be deterministic,     │  calls   │   effects: LLM calls, tool  │
   │  replayable from the        │          │   execution, DB writes)     │
   │  event-history log          │          │  automatically retried      │
   └─────────────┬───────────┘         └──────────────────────────┘
                 │ every start/complete event appended
                 ▼
        ┌─────────────────────────┐
        │   EVENT-HISTORY LOG       │  <- the actual source of truth;
        │  (append-only, durable)   │     replay reads from here, not
        └─────────────────────────┘     from live process memory
```

*(`[DIAGRAM]` — this split is the chapter's organizing idea: everything
from Section 3 onward is a direct consequence of workflow code needing to
replay against this log correctly.)*

## Key Takeaways for Section 2

Workflow code is pure, replayable orchestration; activities are the actual
non-deterministic effects, executed once for real and retried
automatically on failure; the event-history log is the durable source of
truth that replay reconstructs progress from. Nothing in this split is
optional — get workflow code accidentally non-deterministic, and replay
itself breaks, which is exactly Section 3's subject.

*Next: what "the workflow must be deterministic" actually forbids, concretely.*

---

# 3: Determinism Requirements

## Starting From Plain Language

A movie script that says "the actor improvises a joke here" cannot be
re-performed identically on the second night — a different joke happens,
because the script itself introduced a choice point with no fixed answer.
Workflow code has to be the opposite of that kind of script: given the
same recorded history, it must make the exact same decisions, every single
time it's replayed.

## Why `random()`, `now()`, and Direct Network Calls Are Forbidden Inside Workflow Code

If workflow code calls `random()` directly, a replay produces a
*different* random value than the original run did — and if that value
ever influenced a branching decision, replay reconstructs a different
execution path than what actually happened, silently. The same logic
applies to `now()` (the wall-clock time is different on replay than it was
during the original run, by definition) and to calling the network
directly from workflow code (a live network call is exactly the kind of
non-deterministic, possibly-failing operation Section 2 said belongs in an
Activity, not in orchestration logic). Each of these isn't merely
discouraged — it's the specific, concrete way "the workflow must be
deterministic" fails in practice, and each one is exactly the kind of bug
that produces no error message at all, just a replay that quietly
diverges from what really happened.

*This is precisely why a workflow harness's own scripting rules forbid
calling `Date.now()`, `Math.random()`, or an argless `new Date()` directly
inside orchestration code, and require timestamps or randomness to be
passed in from outside instead — not an arbitrary restriction, but the
exact determinism requirement this section describes, enforced by the
harness rather than left to the workflow author's discipline.*

## How This Constraint Reshapes Agent Code

The practical consequence for an agent: anything that needs a timestamp,
a random ID, or a live network round-trip has to happen *inside an
activity*, which then returns that value back to the workflow as an
ordinary, recorded result — from that point on, the workflow just treats
it as data, not as something it computed itself. This is a real
architectural discipline, not a minor style preference: an agent loop
written without this separation in mind typically has timestamps and
random choices scattered throughout its own decision logic, and every one
of those calls is a landmine the moment that logic needs to become
durable and replayable.

## Key Takeaways for Section 3

Workflow code cannot call `random()`, `now()`, or the network directly,
because each one produces a different result on replay than it did during
the original run, silently diverging execution from what actually
happened. Anything needing a timestamp, random value, or live network call
belongs in an activity, whose *result* — not the live call itself — is
what the workflow code ever sees.

*Next: an activity is allowed to be retried automatically — which raises
an uncomfortable question about what happens when the thing it did can't
safely happen twice.*

---

# 4: Idempotency Keys and Exactly-Once Side Effects

## Starting From Plain Language

Pressing an elevator call button that's already lit doesn't summon a
second elevator — the button (or the system behind it) recognizes the
request is already in flight and doesn't duplicate the effect. A tool
call inside a durable agent needs exactly this same recognition, because
Section 2 already established that activities get retried automatically
on failure — and a retry of an *already-completed* side effect is a
duplicate, not a retry.

## The Hard Part, Named Precisely

The scenario this section is built entirely around: the model calls
`send_email`, the email genuinely goes out, and the process dies *before*
that success gets recorded anywhere durable. On resume, the workflow sees
no record of `send_email` having completed — because none was ever
written — and, following ordinary retry logic, calls it again. The
customer now has two emails. Nothing about the retry logic was wrong in
isolation; the actual bug is that the side effect and the durable record
of the side effect happening were not atomic with each other, and a crash
landed in the gap between them.

## Idempotency Keys as the Fix

An **idempotency key** is a unique identifier attached to a specific
attempted operation, checked by the receiving system (or by your own
activity wrapper) *before* the effect happens: "has this exact key already
been processed? If so, return the previously recorded result instead of
doing it again." This turns "call this activity, possibly more than once
due to retries" into "this effect provably happens at most once,
regardless of how many times the activity itself gets invoked" — the
retry mechanism keeps working exactly as designed, but duplicate side
effects become structurally impossible rather than merely unlikely.

```
   WITHOUT an idempotency key            WITH an idempotency key

   send_email() fires --                 send_email(key="req-4471") fires --
   process dies before                   receiving system already saw
   success is recorded --                key "req-4471" from the FIRST
   retry calls send_email()              attempt -- returns the recorded
   AGAIN -- customer gets                result instead of sending again --
   two emails                            customer gets exactly one email
```

## Key Takeaways for Section 4

A retried activity is indistinguishable from a duplicate call unless
something checks first — the specific failure mode is a side effect firing
successfully right before the process dies, before that success is
durably recorded. An idempotency key, checked before the effect happens,
makes "at most once" a structural guarantee rather than a hope, without
requiring the retry mechanism itself to change at all.

*Next: durability doesn't only apply to the workflow's own bookkeeping —
the environment an agent runs inside needs the same discipline.*

---

# 5: Sessions, Sandboxes, and the Runtime Triad

## Starting From Plain Language

A hotel guest's room key, the room itself, and the guest's actual stay are
three related but genuinely different things — losing track of which one
you're managing (is the *key* still valid, is the *room* still theirs, did
the *stay* itself end) is how a guest ends up locked out of a room they
haven't checked out of, or billed for a room they already left.

## The Three Concerns, Distinguished

**Session identity** is the durable handle for "this particular
long-running task," independent of which specific machine or process is
currently executing it — the thing a resume operation (Section 6) actually
resumes. **Sandbox lifecycle** — in the Modal/E2B style this book has
referenced since Chapter 8's code-mode sandboxing — is the actual compute
environment: provisioned, kept warm for some period, and eventually torn
down, on its own schedule, which does not automatically match the
session's own lifetime. **Checkpoint boundaries** for an hour-long run are
the specific points where enough state gets durably recorded that
resuming from that point is actually possible — and these three concerns
interact in a way that's easy to get wrong: a session can outlive its
original sandbox (Section 6, Section 10's migration concern), and a
checkpoint taken *inside* a sandbox that's since been torn down is only
useful if resuming means provisioning a fresh sandbox and restoring into
it, not assuming the old one is still there.

## Why This Is Its Own Named Concern

It's tempting to assume "durability" means only the workflow's own
event-history log, and treat the sandbox as an incidental implementation
detail. It isn't: a sandbox holds real state of its own (files written
mid-task, installed dependencies, a running process's memory) that the
event-history log does not automatically capture, and one of this
chapter's named gotchas — **resuming into a stale sandbox** — is exactly
what happens when a resume operation successfully restores the workflow's
logical state but reconnects to (or recreates) a sandbox whose actual
filesystem no longer matches what the workflow believes it left behind.

## Key Takeaways for Section 5

Session identity, sandbox lifecycle, and checkpoint boundaries are three
distinct concerns that don't automatically stay in sync with each other.
A sandbox holds real state the event-history log doesn't capture on its
own; resuming a session's logical state without accounting for what
actually happened to its sandbox is exactly how a resume operation
succeeds on paper while breaking in practice.

*Next: what "resuming" a session actually means, mechanically.*

---

# 6: Resume Semantics for Agents

## Starting From Plain Language

Picking up a half-finished jigsaw puzzle two different ways: dumping all
the pieces back on the table and starting over from the box, or picking up
exactly where the assembled sections already stand and continuing from
there. Both eventually finish the puzzle; only one of them wastes zero
work already done.

## Resuming With Cached Prior Steps vs Re-Deriving

**Resuming with cached prior steps** means treating every already-recorded
activity result as ground truth and skipping straight to the first step
that doesn't have one — Section 2's replay mechanism doing exactly its
job. **Re-deriving** means recomputing from scratch, ignoring whatever was
previously recorded — sometimes genuinely necessary (Section 10's
migration case, where the old recorded results may no longer even be valid
against new code), but expensive by default and not the common case.

## "Longest Unchanged Prefix Replays"

The concrete mechanism worth understanding precisely: when resuming a
multi-step run after some steps were edited or added, the resume logic
finds the **longest prefix of steps whose inputs are unchanged from the
previous run** and serves *those* results straight from the cache,
re-executing only from the first step that's actually new or different
onward. This is not a hypothetical description — it is, concretely, how
this course's own workflow-orchestration tool already resumes a run: the
same script and same arguments produce a 100% cache hit on every prior
step, and editing one step in the middle re-executes that step and
everything after it, while everything *before* the edit replays from
cache, untouched. The principle generalizes directly to any durable-agent
resume mechanism: identify what's provably unchanged, trust it, and spend
real compute only on what genuinely needs re-deriving.

```
   Original run:  [step1] [step2] [step3] [step4] [step5]
                     ✓        ✓       ✓       ✓       ✓     (all cached)

   Script edited at step3, re-run with resumeFromRunId:

                  [step1] [step2] [step3'] [step4'] [step5']
                     ✓ from     ✓ from     re-run,   re-run,   re-run,
                     cache      cache      NEW input  fresh     fresh
                                (unchanged prefix)     (everything after
                                                        the edit reruns)
```

## Why This Makes Iterating on a Harness Cheap

The direct payoff, and the reason this section matters beyond the
mechanics: if every change to a harness — a tweaked prompt, an added
guard, a fixed bug — forced a full re-run from step one to validate, the
cost of iterating on the harness itself would scale with the *entire*
run's length every single time, discouraging exactly the kind of small,
frequent, attributable changes Chapter 5, Section 10's hill-climbing
method depends on. Longest-unchanged-prefix resume turns "did my one-line
fix work" into a cost proportional to *what changed*, not to how long the
overall run happens to be — which is precisely what makes iterating fast
and cheap rather than something to be dreaded and batched up.

## Key Takeaways for Section 6

Resuming with cached prior steps trusts already-recorded results and
re-executes only what's new; re-deriving recomputes from scratch and is
the expensive exception, not the default. "Longest unchanged prefix
replays" is the concrete mechanism — find the longest run of
still-valid, unchanged steps, serve those from cache, and re-execute only
from the first genuinely new or different step onward. This is what turns
harness iteration into something cheap enough to do constantly rather than
something to batch and dread.

*Next: a durable agent doesn't run in isolation — something has to decide
when it runs at all, and what happens when many want to run at once.*

---

# 7: Queues, Schedules, and Event-Driven Triggers

## Starting From Plain Language

A single toll booth handles a trickle of cars without incident and turns
into a mile-long backup the instant a stadium lets out — the booth's own
processing logic didn't change; what changed is that arrivals stopped
being spread out and started arriving all at once.

## Three Trigger Shapes

A **cron agent** runs on a fixed schedule, independent of any external
event — a nightly report, a weekly cleanup. A **webhook agent** runs in
direct response to an external event arriving — a support ticket created,
a payment processed. An **event-driven trigger** generalizes the webhook
case to any message arriving on a queue or event bus, not just an HTTP
callback specifically. All three share the same underlying question this
chapter has been building toward: whatever triggers a run, that run still
needs to be durable once it starts, for exactly the reasons Section 1
established.

## Backpressure

The scenario worth planning for explicitly: 200 agent runs get queued at
once (a batch import, a viral spike in webhook traffic, a scheduled job
whose previous run hadn't finished when the next one fired). **Backpressure**
is the deliberate policy for this moment — bounding how many runs execute
concurrently, queuing or rejecting the rest rather than attempting to
start all 200 simultaneously and exhausting whatever shared resource
(API rate limits, database connections, sandbox capacity) the runs
actually compete for. A system with durable execution but no backpressure
policy doesn't crash outright the way an undurable one might — but it can
still degrade badly, with 200 runs all competing for the same rate-limited
model API and each one taking far longer than it would have running
alone.

## Key Takeaways for Section 7

Cron, webhook, and event-driven triggers all answer "what starts a run,"
but every run they start still needs the durability this whole chapter
builds. Backpressure — deliberately bounding concurrent execution rather
than starting every queued run at once — is what keeps a burst of 200
simultaneous triggers from degrading shared resources for everyone, even
when durability itself is already solved.

*Next: not every failure mode looks like a crash — some look like nothing
happening at all.*

---

# 8: Timeouts and Heartbeats

## Starting From Plain Language

A phone call that's gone completely silent is a different problem than a
phone call that ended — the line is still open, nobody hung up, but
nothing is happening either, and without some signal you can't tell
"still thinking" from "frozen" from "the other person walked away and
forgot to hang up."

## Per-Activity Timeouts

A **timeout** on an activity is a hard ceiling: if the activity hasn't
completed within this window, treat it as failed and let the normal retry
logic (Section 4) take over — without a timeout, a single hung tool call
(a network request that never times out on its own, an infinite loop in a
sandbox) can block a workflow indefinitely, with no automatic recovery
path at all.

## Heartbeating Long Tool Calls

A timeout alone is a blunt instrument for anything that's expected to
genuinely take a long time — a large file processing job, a long-running
model generation. **Heartbeating** solves this: the activity periodically
signals "I'm still alive and making progress" while it runs, and the
orchestrator only declares it dead if heartbeats *themselves* stop
arriving, rather than timing out the whole activity just because it's
naturally slow. This is the same distinction Chapter 6, Section 6 drew
between "working slowly" and "actually stuck" — heartbeats give a
long-running activity a way to prove it's the former.

## Detecting a Wedged Agent

The combination — timeouts on operations with a genuinely bounded
expected duration, heartbeats on operations that are expected to run long
— is what lets an orchestrator distinguish a **wedged agent** (heartbeats
have stopped; something is actually broken) from a legitimately
long-running one (heartbeats keep arriving on schedule; it's just a big
job). Without either mechanism, both cases look identical from the
outside: silence.

## Key Takeaways for Section 8

Timeouts bound operations with a known expected duration and hand off to
retry logic when exceeded. Heartbeats let a genuinely long-running
activity prove it's still making progress, so it isn't mistaken for stuck.
Together, they're what lets an orchestrator tell "wedged" from
"legitimately slow" — silence alone can't distinguish the two.

*Next: which real systems actually implement everything this chapter has
described, and how they compare.*

---

# 9: Frameworks: Temporal, Inngest, and LangGraph's Checkpointer

## Temporal

Temporal is the reference implementation of Section 2's exact split:
deterministic, replayable workflow code and retryable activities, backed
by an event-history log that is itself the durable source of truth. It's
the most mature, longest-running production track record among the
options here, with a broad multi-language SDK surface — and, as of early
2026, a funding and product signal ($300M Series D at a $5B valuation)
specifically repositioning the platform around agentic workloads rather
than only traditional business-process orchestration, reflecting how
central this chapter's whole subject has become to the field.

## Inngest

Inngest takes a lighter-weight, more developer-ergonomic approach to the
same underlying problem: a `step.run()` primitive checkpoints the output
of each individual step to Inngest's own backend, and if a function fails
mid-run, only the failed step actually retries — completed steps replay
straight from the checkpoint store rather than re-executing. This is
Section 2's workflow/activity split again, expressed with a much smaller
API surface and no separate stateful infrastructure for you to run
yourself. Inngest also ships **AgentKit**, a first-party multi-agent
framework with built-in MCP tooling support, aimed specifically at the
agent use case rather than general workflow orchestration adapted to fit
it.

## LangGraph's Built-In Checkpointer

Chapter 11, Section 5 already covered this in depth: a checkpointer
attached to a compiled graph, persisting full state after every node
transition automatically. Positioned against Temporal and Inngest, it
covers a meaningfully narrower slice of this chapter's full scope — it
gives you durability and resumability *within LangGraph's own graph
execution model* specifically, without Temporal's or Inngest's
general-purpose activity retry semantics, idempotency tooling, or
scheduling/backpressure features. It overlaps with the other two
precisely on "does my state survive a crash" and diverges everywhere this
chapter's other sections (idempotency, queues, heartbeats) go beyond that
one property.

## Where They Overlap, and Where They Don't

All three solve "state survives a crash." Temporal and Inngest additionally
solve activity-level idempotency tooling, flexible scheduling and
event-driven triggers, and cross-language/cross-framework durability that
doesn't assume you're inside any particular agent framework's own runtime.
LangGraph's checkpointer wins on zero additional infrastructure if you're
already committed to LangGraph specifically, at the cost of that
durability not extending naturally beyond a graph-shaped agent.

## Key Takeaways for Section 9

Temporal is the mature, broad reference implementation of the workflow/
activity split, now explicitly repositioning around agentic workloads.
Inngest offers the same underlying guarantee with a lighter developer
surface and a first-party agent framework (AgentKit). LangGraph's
checkpointer covers durability specifically within its own graph
execution model, without the general-purpose scheduling and idempotency
tooling the other two provide. All three overlap on "state survives a
crash"; each diverges beyond that in a different direction.

*Next: durability has a blind spot even the best of these three doesn't
automatically cover.*

---

# 10: Migration and Versioning of In-Flight Runs

## Starting From Plain Language

Renovating a house while a family is still living in it requires a
different plan than renovating an empty one — you can't just tear out the
staircase they're currently walking up, even if the new staircase design
is objectively better, without first getting everyone to a safe landing.

## The Actual Problem

Deploying new harness code while runs are genuinely mid-flight — some
workflows paused mid-execution, waiting to resume from an event-history
log written against the *old* code's logic — creates a real hazard
Section 3's determinism requirement makes concrete: if the new code
replays differently than the old code would have, for the same recorded
history, replay itself produces a corrupted reconstruction of what
actually happened. This isn't a hypothetical edge case; it is the direct,
mechanical consequence of changing workflow code while event histories
written against the old version still need replaying.

## What Actually Has to Be True

A safe migration needs the new code to remain capable of correctly
replaying event histories written by the old code — which typically means
versioning workflow definitions explicitly (so a specific in-flight run
keeps replaying against the exact logic version it started with, even
after new runs start using a newer version), and treating a workflow
definition change with the same one-change-at-a-time, individually
attributable discipline Chapter 5, Section 10 already established for a
harness in general. The version that shipped a given run is not a detail
to discard once the run finishes migrating — it's the only thing that
makes that run's own eventual replay meaningful.

## Key Takeaways for Section 10

Deploying new harness code while runs are mid-flight risks the new code
replaying old event histories differently than the code that actually
produced them — a silent corruption of the reconstructed past, not a
crash. Versioning workflow definitions explicitly, so an in-flight run
keeps replaying against the logic it actually started with, is what
prevents this; it's the same one-change-at-a-time attributability
discipline this book has argued for since Chapter 5, now applied to
workflow definitions specifically.

*Next: putting exact numbers under the chapter's central claim about why
checkpointing is worth the trouble at all.*

---

# 11: Dry-Run: Expected Steps, Full-Restart vs Checkpoint-and-Resume

## The Setup

A 60-step run. Each step independently has a $p = 0.5\%$ chance of
crashing (surviving with probability $q = 1 - p = 0.995$). Compare two
recovery strategies: **full-restart-on-crash** (any crash sends the entire
run back to step 1) against **checkpoint-and-resume** (a crash only costs
the one step that failed; everything before it is durably recorded and
never re-executed).

## Checkpoint-and-Resume, Computed

Each of the 60 steps, independently, needs a **Geometric($q$)**-distributed
number of attempts to eventually succeed — try, and if it fails, simply
try that same step again, at mean cost $\frac{1}{q}$ attempts per step:

$$\mathbb{E}[\text{total steps, checkpoint-and-resume}] = \frac{n}{q} = \frac{60}{0.995} \approx 60.30$$

## Full-Restart-on-Crash, Computed

This is meaningfully more involved, because a single "attempt" now means
"run from step 1 until either finishing all 60 steps or crashing
somewhere along the way" — and a crash discards every step completed in
that attempt, not just the one that failed. The probability one full
attempt completes clean is $q^{n}$:

$$P(\text{clean attempt}) = q^{60} = 0.995^{60} \approx 0.7403$$

The expected number of steps actually executed within a single attempt —
whether that attempt ultimately succeeds or crashes partway — sums the
probability of *reaching* each step:

$$\mathbb{E}[\text{steps per attempt}] = \sum_{k=1}^{60} k \cdot q^{k-1}p \;+\; 60 \cdot q^{60} \approx 51.95$$

Since attempts are independent and identically distributed, the expected
number of attempts needed until the first clean one is $\frac{1}{q^{60}}$,
and (by Wald's identity, since the number of attempts needed doesn't
depend on any future attempt's own outcome) the expected total steps
executed is that count multiplied by the expected steps burned per
attempt:

$$\mathbb{E}[\text{total steps, full-restart}] = \frac{1}{q^{60}} \times 51.95 \approx 1.3509 \times 51.95 \approx 70.17$$

*(Verified numerically: a 20,000-trial Monte Carlo simulation of exactly
this process reproduces 70.19 for full-restart and 60.30 for
checkpoint-and-resume, matching the closed-form results to within
simulation noise.)*

## The Multiple, at This Chapter's Own Numbers

$$\frac{70.17}{60.30} \approx 1.16\times$$

At a realistic $0.5\%$ per-step crash rate, checkpoint-and-resume costs
about **16% fewer total steps executed**, on average, than full-restart —
real, but modest, because a $60$-step run at this crash rate still has a
$74\%$ chance of completing with zero crashes at all, leaving comparatively
little room for the two strategies to diverge.

## How the Multiple Actually Grows

The real argument for checkpointing shows up once crash probability climbs
even modestly — computing the identical arithmetic at higher per-step
crash rates:

| Per-step crash rate | $P(\text{clean run})$ | Full-restart, expected steps | Checkpoint-resume, expected steps | Multiple |
|---|---|---|---|---|
| 0.5% | 74.0% | 70.17 | 60.30 | 1.16x |
| 1.0% | 54.7% | 82.76 | 60.61 | 1.37x |
| 2.0% | 29.8% | 118.04 | 61.22 | 1.93x |
| 5.0% | 4.6% | 414.12 | 63.16 | 6.56x |

Checkpoint-and-resume's expected cost barely moves across this entire
range — it only ever pays for the *one* step that failed, so the crash
rate mostly just changes how many times, on average, any given step needs
retrying. Full-restart's cost, by contrast, explodes, because a higher
crash rate means a clean 60-step run becomes rare, and *every single
failed attempt discards everything completed in it, no matter how far it
got.* At a 5% per-step crash rate — not an exotic number for, say, a flaky
external API — full-restart costs **6.56 times** more total steps than
checkpoint-and-resume.

## Key Takeaways for Section 11

At a realistic 0.5% per-step crash rate on 60 steps, checkpoint-and-resume
saves about 16% of total steps executed versus full-restart — real, but
modest, because most 60-step runs at this rate complete clean anyway. The
advantage grows sharply, not linearly, as crash probability rises, because
full-restart's cost is dominated by how *rare* a fully clean run becomes,
while checkpoint-and-resume's cost barely changes at all. This is the
precise, numeric version of Section 1's claim: durability matters more,
not less, exactly as infrastructure gets less reliable or runs get longer
— the two conditions where you can least afford to be without it.

*Next: closing the loop on the whole chapter.*

---

# 12: Key Takeaways + Master Decision Table

The single mental model for this chapter: **treat a long-running agent as
the distributed system it actually is** — orchestration logic that must
replay deterministically, real effects isolated into retryable activities,
and an event-history log as the one source of truth progress is measured
against, so that a crash costs the one step that failed, not the work that
came before it.

| I want to know... | Reach for | Key fact |
|---|---|---|
| Why any of this matters | Section 1 | A production agent is a distributed system whether or not it was designed as one; without durability, any ordinary infra failure destroys all progress |
| What the actual architectural split is | Section 2 | Deterministic, replayable workflow code; non-deterministic, retryable activities; an event-history log as the durable source of truth |
| Why my workflow code can't call `random()`/`now()`/the network | Section 3 | Each produces a different result on replay than during the original run, silently diverging reconstructed history from what actually happened |
| How to stop a retry from duplicating a side effect | Section 4 | An idempotency key, checked before the effect happens -- "at most once" becomes structural, not hopeful |
| Why my resumed session looks wrong even though state "restored" | Section 5 | Session identity, sandbox lifecycle, and checkpoint boundaries are three distinct concerns -- a stale sandbox can silently not match restored logical state |
| How resuming actually decides what to skip | Section 6 | "Longest unchanged prefix replays" -- trust everything provably unchanged, re-execute only from the first genuinely new/different step |
| What to do about a flood of triggered runs | Section 7 | Backpressure -- bound concurrent execution deliberately rather than starting every queued run at once |
| How to tell "stuck" from "just slow" | Section 8 | Timeouts for bounded operations; heartbeats for long-running ones -- silence alone can't distinguish a wedged agent from a big job |
| Which framework to reach for | Section 9 | Temporal (mature, broad, agent-repositioned), Inngest (lighter, AgentKit built in), LangGraph checkpointer (durability within the graph model only) |
| Why deploying mid-flight is dangerous | Section 10 | New code replaying old event histories differently is silent corruption of reconstructed history, not a crash -- version workflow definitions explicitly |
| How much checkpointing actually saves, numerically | Section 11 | ~16% fewer steps at a realistic 0.5% crash rate, growing to 6.56x at 5% -- the benefit compounds precisely as reliability gets worse, not better |

**Connection forward:** Chapter 13 leaves single-agent durability behind
and asks a cost question one level up — once a single agent can run
reliably for hours, when does adding a *second* agent, with its own
isolated context, actually pay for the extra tokens it costs, versus just
being a more complicated way to do the same job.
