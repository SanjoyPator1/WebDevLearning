# Chapter 13: Multi-Agent Systems & Protocols

## Table of Contents

1. [The One Real Reason for Multi-Agent: Context Isolation](#1-the-one-real-reason-for-multi-agent-context-isolation)
2. [Topologies](#2-topologies)
3. [Subagents as a Harness Primitive](#3-subagents-as-a-harness-primitive)
4. [What Multi-Agent Is Bad At](#4-what-multi-agent-is-bad-at)
5. [Handoffs vs Delegation vs Fan-Out](#5-handoffs-vs-delegation-vs-fan-out)
6. [Parallelism Patterns That Work](#6-parallelism-patterns-that-work)
7. [MCP in a Multi-Agent World](#7-mcp-in-a-multi-agent-world)
8. [A2A v1.0](#8-a2a-v10)
9. [Agent Identity, Attribution, and Authorization Across Boundaries](#9-agent-identity-attribution-and-authorization-across-boundaries)
10. [Cost and Latency Modeling for Multi-Agent](#10-cost-and-latency-modeling-for-multi-agent)
11. [Debugging Multi-Agent Runs](#11-debugging-multi-agent-runs)
12. [Dry-Run: 5 Subtopics, Two Architectures, and the Case Where Single-Agent Wins](#12-dry-run-5-subtopics-two-architectures-and-the-case-where-single-agent-wins)
13. [Key Takeaways + Master Decision Table](#13-key-takeaways--master-decision-table)

---

# 1: The One Real Reason for Multi-Agent: Context Isolation

## Starting From Plain Language

Asking one person to research five unrelated topics back-to-back, in one
sitting, with no break, means every later topic gets researched by someone
whose head is already full of the first four — genuinely useful
background sometimes, genuine interference other times, and always more
mental clutter than starting topic five fresh would have carried. Handing
each topic to five different researchers, then having one person read
their five short summaries, avoids the clutter entirely — at the very
real cost of five researchers' worth of overhead instead of one.

## The Actual Mechanism, Not the Vibe

Multi-agent systems get proposed for all sorts of reasons — it sounds more
sophisticated, it feels like "real" AI engineering, a second agent seems
like it should double capability. **None of those are the real reason
multi-agent ever pays for itself.** The one mechanism that actually
justifies the cost is **context isolation**: each subagent gets its own
window, its own tools, its own instructions, works the sub-problem
entirely inside that isolated space, and returns only a **summary** —
never its full working transcript — back to whatever spawned it. This is
Chapter 4's whole subject (the token budget, context rot with position)
solved by the most direct method available: instead of managing what
stays in one window, give the sub-problem an entirely separate window that
never has to hold anything else.

## The Anthropic Research-System Result

The concrete, load-bearing empirical result behind this entire chapter:
Anthropic's own multi-agent research system reported roughly **+90%
higher success rate** than a comparable single-agent system on the same
class of task — at roughly **15× the token cost**. Both halves of that
number matter equally, and the chapter's job is teaching you to reason
about both, not just the flattering half: isolation genuinely buys real
capability (the +90%), and it is genuinely expensive (the 15×). Neither
number is a reason to always use multi-agent or to never use it — they're
the two inputs to a real cost-benefit decision, made concrete in this
chapter's dry-run (Section 12).

```
        SINGLE AGENT                      MULTI-AGENT (ISOLATED)

   ┌─────────────────────┐          ┌───────┐ ┌───────┐ ┌───────┐
   │  one window, growing  │          │ sub 1  │ │ sub 2  │ │ sub 3  │  ...
   │  to hold ALL 5         │          │isolated│ │isolated│ │isolated│
   │  subtopics' full        │          │ window │ │ window │ │ window │
   │  research history       │          └───┬───┘ └───┬───┘ └───┬───┘
   └─────────────────────┘                  │ summary  │ summary  │ summary
                                             ▼          ▼          ▼
                                        ┌─────────────────────────┐
                                        │   ORCHESTRATOR             │
                                        │   (small window: just the  │
                                        │   summaries, never the raw │
                                        │   research)                 │
                                        └─────────────────────────┘
```

*(`[DRY-RUN]` — Section 12 puts real numbers under exactly this picture.)*

## Key Takeaways for Section 1

Context isolation — a separate window, tools, and instructions per
subagent, with only a summary returned — is the one mechanism that
actually justifies multi-agent's cost; everything else is aesthetic.
Anthropic's own reported result, ~+90% success at ~15× tokens, names both
sides of the real tradeoff honestly: genuine capability gain, genuine
expense, neither one a reason to skip the cost-benefit reasoning this
chapter builds toward.

*Next: isolation is the mechanism, but there's more than one way to wire
several isolated agents together.*

---

# 2: Topologies

## Starting From Plain Language

A single cashier serving one line, versus a manager routing customers to
whichever of five open registers fits their need, versus an assembly line
where each station only ever does one step, versus a panel of judges each
independently scoring the same performance — none of these are "better"
in the abstract. Each fits a genuinely different shape of work.

## Six Topologies, and the Shape Each One Fits

**Single agent** is still a topology, and the honest default — no
coordination overhead, one context, Chapter 2 through Chapter 12 built
this deeply for a reason. **Orchestrator–worker** is Section 1's picture:
one coordinating agent, several isolated subagents doing independent
sub-work, results returned as summaries — fits fan-out over genuinely
independent subtopics. **Pipeline** chains agents sequentially, each one's
output becoming the next one's input — fits a task that's naturally a
sequence of distinct transformation stages (extract, then structure, then
format), where each stage benefits from its own focused context rather
than one agent holding the whole pipeline's concerns at once.
**Debate/panel** runs several agents independently on the *same* question
and compares or synthesizes their answers — fits exactly Chapter 6,
Section 11's best-of-N and this chapter's own diverse-lens verification
(Section 6), where the value is in genuinely independent perspectives on
one question, not division of labor across several questions.
**Hierarchical** nests orchestrator–worker recursively — an orchestrator's
own "worker" is itself an orchestrator over further subagents — fitting a
task whose natural decomposition has more than one level of structure.
**Blackboard/event-driven swarm** has no fixed control flow at all: agents
read and write to a shared space (the "blackboard") and react to what
appears there, fitting genuinely open-ended, emergent coordination where
no single orchestrator can or should pre-plan the whole interaction.

```
   SINGLE          ORCHESTRATOR-      PIPELINE           DEBATE/PANEL
                   WORKER

   [Agent]         [Orchestrator]     [A]→[B]→[C]→[D]    [A] [B] [C]
                    /    |    \                            \  |  /
                [W1]  [W2]  [W3]                          [compare/
                                                            synthesize]

   HIERARCHICAL                    BLACKBOARD / SWARM

   [Orchestrator]                  ┌─────────────┐
    /         \                    │  shared space │
  [Sub-Orch] [Sub-Orch]            └──┬───┬───┬───┘
   /   \       /   \                 │   │   │
 [W] [W]     [W]  [W]              [A] [B] [C]  (react to what appears)
```

*(`[DIAGRAM]` — selection by task shape, not by which topology sounds most
advanced, is this section's entire point.)*

## Key Takeaways for Section 2

Six topologies, each fitting a genuinely different task shape: single
(the default), orchestrator-worker (independent subtopics), pipeline
(sequential transformation stages), debate/panel (independent perspectives
on one question), hierarchical (multi-level decomposition), and
blackboard/swarm (emergent, no fixed control flow). Choosing by task shape,
not by sophistication, is the entire discipline this section asks for.

*Next: however you wire them together, spawning a subagent is itself a
specific harness mechanism with its own design rules.*

---

# 3: Subagents as a Harness Primitive

## Starting From Plain Language

Delegating a task to a colleague works well when you hand them a clear
brief and expect a written report back — it works badly when you expect
them to just casually chat back at you the way you'd chat with someone who
already knows everything you know about the project.

## Spawning

A subagent is spawned with its own isolated context: its own system
prompt, its own tool set (possibly narrower than the parent's — Chapter
3's granularity question, applied per-subagent), and a specific task
description, not the parent's full conversation history. Nothing about the
parent's own accumulated context, prior decisions, or ongoing chat gets
implicitly carried over; anything the subagent genuinely needs has to be
stated explicitly in what it's handed at spawn time.

## Prompt Design for a Subagent: It Returns Data, Not Conversation

The single most consequential design decision, and the direct fix for one
of this chapter's named gotchas (**subagents returning prose instead of
data**): a subagent's prompt should make unmistakably clear that its job
is to *return a specific, structured result* the orchestrator can act on
programmatically — not to produce a conversational reply the way it would
if it were talking directly to a human. "Research topic X and tell me what
you find" invites prose; "Research topic X and return a JSON object with
fields `key_findings` (list of strings, max 5), `confidence` (0-1), and
`sources_checked` (int)" invites exactly what the orchestrator needs to
consume without another parsing step in between.

## Result Schemas

Following directly from that: a subagent's return value should conform to
an explicit schema, the same discipline Chapter 3, Section 6 already
established for structured tool output — an orchestrator receiving five
subagents' results in five subtly different shapes has to write brittle,
special-cased handling for each one; an orchestrator receiving five
results in the *same* schema can process them identically, regardless of
which subtopic each one actually covered.

## Key Takeaways for Section 3

Spawning a subagent means giving it its own context from scratch — nothing
implicit carries over from the parent. Its prompt must make clear it
returns structured data for the orchestrator to consume, not a
conversational reply, and a shared result schema across subagents is what
lets the orchestrator process results uniformly rather than
special-casing each one.

*Next: the honest limits of this whole approach, before the chapter gets
any further into what it's good at.*

---

# 4: What Multi-Agent Is Bad At

## Starting From Plain Language

A team of five people each independently editing their own paragraph of
the same shared document, at the same time, with no coordination about who
owns what, produces a document that doesn't read as one voice and
sometimes directly contradicts itself paragraph to paragraph. Some kinds
of work are just not divisible this way, no matter how good each
individual editor is.

## The Failure Modes, Named

**Shared mutable state** — multiple subagents that need to read *and*
write the same evolving resource (a single file, a single database
record) hit exactly the race-condition problem distributed systems have
always had, and isolation (Section 1's whole selling point) becomes a
liability here instead of a benefit, because isolated agents can't see
each other's in-flight changes to shared state. **Tightly coupled edits**
— a refactor that touches the same function's signature in ten call
sites — genuinely needs one consistent view of the whole change; splitting
it across isolated subagents risks five internally-consistent but
mutually-contradictory edits landing on the same codebase. **Tasks needing
global consistency** — anything where a decision made in one part of the
task must be known and honored everywhere else in the task — fights
directly against context isolation's core premise, because the whole
point of isolation is that subagents *don't* see each other's context.

## The Coordination-Overhead Curve

The pattern underlying all three: as the amount of genuine
cross-cutting dependency between subtasks rises, the coordination
mechanism needed to keep isolated agents consistent gets more expensive,
and past some point that coordination overhead exceeds whatever isolation
was supposed to save. Multi-agent's actual sweet spot — Section 1's
context-isolation payoff — assumes subtasks are genuinely independent;
the more that assumption is false, the more multi-agent's real cost
(coordination) creeps toward, and eventually past, the benefit it was
supposed to buy.

## Key Takeaways for Section 4

Multi-agent struggles specifically where subtasks aren't actually
independent: shared mutable state, tightly coupled edits, and any task
needing one consistent global view. The coordination overhead needed to
keep isolated agents consistent rises with how much they actually depend
on each other — past some point, that overhead costs more than isolation
saved, which is exactly why "genuinely independent subtasks" is the
precondition for everything this chapter argues works.

*Next: not every way of transferring control between agents carries the
same risk.*

---

# 5: Handoffs vs Delegation vs Fan-Out

## Starting From Plain Language

Transferring a phone call to a colleague who then owns the conversation
entirely, asking a colleague to handle one specific sub-errand and report
back to you, and sending the same request to five colleagues at once to
see who comes back with the best answer are three genuinely different
kinds of "getting someone else involved" — confusing which one you're
doing is how context gets lost or work gets duplicated.

## Three Distinct Control Transfers

A **handoff** transfers the *entire* ongoing interaction to a different
agent, which takes over with full context and the original agent steps
out of the loop — Chapter 11, Section 8's OpenAI Agents SDK pattern,
recapped here as one of three shapes rather than the only one.
**Delegation** hands off one bounded sub-task, expects a result back, and
the delegating agent remains in control of the overall interaction — this
is Section 3's subagent-spawning pattern by another name. **Fan-out**
sends the same or related work to multiple agents simultaneously,
expecting to combine or select among several results — Section 2's
orchestrator-worker and debate/panel topologies, generalized.

## The Failure Mode of Each

A handoff's specific failure mode is **lost context at the boundary** —
this chapter's own named gotcha — if the receiving agent doesn't actually
get everything the interaction needs, the handoff silently degrades
quality right at the transfer point, and nobody upstream necessarily
notices, because the *conversation* continues even though information was
dropped. Delegation's specific failure mode is exactly Section 3's
"returns prose instead of data" problem — a delegated result that isn't
actually structured enough for the delegator to use it programmatically.
Fan-out's specific failure mode is uncontrolled cost — Section 4's
coordination-overhead curve compounds with fan-out's own linear-in-N token
cost, and without **per-agent budget caps** (this chapter's third named
gotcha), a fan-out to more agents than the task actually warranted just
multiplies spend with no corresponding multiplication of value.

## Key Takeaways for Section 5

Handoffs transfer the whole interaction and risk losing context at the
boundary; delegation hands off one bounded sub-task and risks getting back
unstructured prose instead of usable data; fan-out sends work to multiple
agents at once and risks uncontrolled cost without per-agent budget caps.
Each is a genuinely different control transfer with its own specific
failure mode, not three names for the same thing.

*Next: the parallelism patterns that actually earn their cost, in
practice.*

---

# 6: Parallelism Patterns That Work

## Fan-Out Over Independent Items

The cleanest case: a genuinely independent list of items (documents to
summarize, files to review, questions to answer), each handed to its own
subagent concurrently, results collected at the end. This is Section 1's
whole premise in its purest form — no coordination needed at all, because
"independent" is not an assumption here, it's actually true.

## Diverse-Lens Verification Panels

Rather than N identical agents independently checking the same thing (pure
redundancy, catching only random variance), a **diverse-lens panel**
assigns each agent a genuinely different angle on the same question — a
correctness lens, a security lens, a performance lens — so that panel
disagreement reflects real, different failure modes rather than the same
check rolled five times. This directly extends Chapter 6, Section 11's
best-of-N idea: more perspectives, not just more attempts.

## Best-of-N With Verifiers

Generate N independent candidate solutions, and select among them using a
**real** verifier (Chapter 6's ladder) — never a vote or a vibe. This is
Chapter 6, Section 11 again, now explicitly framed as a multi-agent
pattern: the "N" can be N independent subagents rather than N sequential
attempts from one agent.

## Map-Reduce Research

The direct generalization of Section 1's dry-run scenario: **map** a
research task across N independent subtopics (each subagent researches
its own isolated slice), then **reduce** — an orchestrator combines the
N summaries into one coherent answer. This is literally the shape
Anthropic's own reported research-system result (Section 1) was measured
on.

## Worktree/Sandbox Isolation for Parallel File Edits

The concrete fix for Section 4's shared-mutable-state problem, when
multiple agents genuinely do need to edit files concurrently: give each
agent its own **git worktree** (or equivalent sandboxed filesystem copy)
so their edits can't collide mid-flight, then merge the results — the same
principle Chapter 8's code-mode sandboxing established, applied to
concurrent agents instead of one agent's generated code. This turns
Section 4's genuine limitation into a solvable problem specifically for
the file-editing case, by removing the *shared* part of "shared mutable
state" rather than trying to coordinate access to a single copy.

## Key Takeaways for Section 6

Fan-out over genuinely independent items is the cleanest case. Diverse-
lens panels get real value from *different* angles, not identical
redundancy. Best-of-N with a real verifier extends Chapter 6's pattern
into multi-agent form. Map-reduce research is Section 1's dry-run scenario
generalized. Worktree/sandbox isolation directly solves Section 4's
shared-mutable-state problem for the specific case of concurrent file
edits, by eliminating the sharing rather than coordinating around it.

*Next: the protocol layer that makes any of this work across process and
organizational boundaries, not just inside one codebase.*

---

# 7: MCP in a Multi-Agent World

## Starting From Plain Language

A single office with one filing cabinet is easy to keep organized. Five
departments each maintaining their own filing cabinet, all technically
accessible to everyone, is a coordination problem the moment two
departments happen to label something the same way.

## AAIF Governance, and What Changed

Chapter 3, Section 10 already introduced this; the specific facts worth
having precisely, since multi-agent systems are exactly where MCP's
governance status starts to matter operationally: the Linux Foundation
formed the **Agentic AI Foundation (AAIF)** on **December 9, 2025**,
anchored by three donated projects — Anthropic's MCP, Block's `goose`, and
OpenAI's `AGENTS.md` — co-founded by Anthropic, OpenAI, and Block, with
over 150 member organizations. Governance now runs through a Governing
Board (chaired, as of February 2026, by AWS's David Nalley) and a
Technical Steering Committee, with working groups covering identity,
security, observability, commerce, workflows, accuracy, and regulatory
alignment — several of which map directly onto problems this very chapter
raises (Section 9's identity and audit questions, Section 4's coordination
questions).

## Tool Namespacing Across Servers

Once a multi-agent system connects to several MCP servers — potentially
one per subagent, potentially several shared across all of them — the
same tool name can legitimately appear from two different servers (two
different `search_tickets` tools, from two different systems). **Tool
namespacing** — qualifying each tool's identity by which server it came
from, not just its bare name — is what keeps an orchestrator (or a
subagent) from silently calling the wrong system's tool when names
collide.

## MCP Server Sprawl as a Context Problem

The multi-agent-specific version of Chapter 8's capability-scaling problem:
where a single agent connecting to too many MCP servers degrades tool
selection accuracy and burns context on unused schemas (Chapter 3, Section
9; Chapter 8, Section 1), a multi-agent system connecting *each* subagent
to its own set of servers multiplies that same risk across every subagent
independently — and if subagents share a common pool of servers rather
than each getting only what its specific task needs, the sprawl compounds
rather than isolating cleanly, quietly undermining Section 1's whole
isolation premise.

## Key Takeaways for Section 7

MCP now lives inside the AAIF, a neutral, Linux-Foundation-governed body
with 150+ members and working groups covering exactly the problems this
chapter's later sections raise. Tool namespacing prevents same-named tools
from different servers colliding. Server sprawl is Chapter 8's
capability-scaling problem, now multiplied across every subagent
independently unless each one is deliberately scoped to only the servers
its specific task actually needs.

*Next: MCP connects agents to tools -- a different, newer protocol
connects agents to each other.*

---

# 8: A2A v1.0

## Starting From Plain Language

A business card tells you who someone is and how to reach them, without
either party needing to have met before or agree on a shared employer
first. A2A gives agents the equivalent: a way to discover what another
agent can do and how to talk to it, without either side needing prior,
bespoke integration.

## AgentCards and Discovery

An **AgentCard** is a JSON document published at a well-known,
standardized path — `/.well-known/agent-card.json` — that a client agent
fetches *before* sending anything, reading off the target agent's name,
version, supported transports, input/output modalities, and the specific
skills it exposes. This is discovery as a protocol-level guarantee rather
than something every pair of integrating agents has to negotiate from
scratch.

## Capability Negotiation and Streaming-First Transport

Once an AgentCard is fetched, **capability negotiation** is the client
agent checking what the target actually supports (which transport —
JSON-RPC, gRPC, or HTTP+JSON as of v1.0 — which security scheme, which
skills) before committing to an interaction shape the target can't
actually fulfill. The protocol is **streaming-first**: built around
incremental, in-progress results as the default expectation, not a
same-request/same-response call-and-wait model bolted on as an
afterthought — matching how a genuinely long-running agent task actually
behaves.

## Signed Cards for Verifiable Identity

The single most consequential change v1.0 (released early 2026) actually
added: **cryptographically signed AgentCards**. A signature on the card
lets a receiving agent verify the card was genuinely issued by the domain
it claims to represent — the direct fix for a spoofing risk that a plain,
unsigned JSON file at a predictable URL would otherwise carry. This is
the mechanism Section 9's identity and attribution questions actually
depend on operationally; without a verifiable card, "which agent, acting
on behalf of which principal, is on the other end of this request" has no
trustworthy answer at all.

## Task Delegation Lifecycle

A2A defines the lifecycle of a delegated task explicitly — submitted,
working, input-required, completed, failed — rather than leaving task
state as an implicit, protocol-agnostic assumption each implementation
invents its own version of. This gives Section 5's "delegation" pattern a
standardized, cross-vendor state machine instead of a bespoke one per
integration.

## How A2A and MCP Compose

The clean division of labor, worth stating precisely because it resolves
what would otherwise be a confusing overlap: **A2A operates between
agents**, across trust boundaries, where the parties may belong to
different organizations entirely; **MCP operates from an agent down to
its tools**, within one agent's own execution. A single system routinely
uses both at once — an orchestrator reaching another organization's agent
via A2A, while that remote agent itself reaches its own tools via MCP —
and neither protocol tries to do the other's job.

```
   Your orchestrator  ──── A2A ────▶  Someone else's agent
        │                                    │
        │ MCP                                │ MCP
        ▼                                    ▼
   your tools/servers                  their tools/servers
```

*(`[DIAGRAM]` — A2A between agents, MCP down to tools, is the entire
composition rule.)*

## Key Takeaways for Section 8

AgentCards, published at a standard well-known path, make agent discovery
and capability negotiation protocol-level guarantees rather than bespoke
integration work. v1.0's genuinely consequential addition is
cryptographically signed cards, which is what makes agent identity
actually verifiable rather than assumed. A2A operates between agents
across trust boundaries; MCP operates from an agent down to its own
tools — the same system uses both, for different legs of the same
interaction.

*Next: signed cards make identity verifiable at the protocol level -- the
next question is what that identity is actually good for, operationally.*

---

# 9: Agent Identity, Attribution, and Authorization Across Boundaries

## Starting From Plain Language

A courier who shows up with a signed letter from your bank, asking you to
hand over a package "on the bank's behalf," raises an obvious question a
verified signature alone doesn't answer: did the bank actually authorize
*this specific* request, or did someone merely prove they work for a bank?

## Persistent Verifiable Identity

Section 8's signed AgentCards solve *"is this genuinely Agent B, not an
impersonator"* — a necessary foundation, but a different question from
*"was Agent B actually authorized to do this, on whose behalf, right
now."* **Persistent verifiable identity** means an agent's identity is
stable and checkable across many separate interactions, not re-established
from scratch (and potentially inconsistently) every single time.

## Delegated Credentials

The mechanism that actually answers the authorization question: **delegated
credentials** — a scoped, checkable proof that a specific principal (a
user, an organization) actually authorized a specific agent to act on
their behalf, for a specific scope of actions, not a blanket "trust
whoever holds a valid signature." This is the direct extension of Chapter
3, Section 7's idempotency-and-permissions thinking and Chapter 16's
permission-gate subject, now applied across an organizational boundary
instead of within one team's own tools.

## Audit Trails When Agent A Acts on Behalf of User U via Agent B

The concrete scenario this section is built around, worth stating exactly:
user U asks Agent A to get something done; Agent A delegates part of it to
Agent B, across a trust boundary, via A2A. When something later needs
investigating — a wrong action taken, a dispute about who authorized what
— the audit trail needs to answer, unambiguously: which user's original
request started this chain, which agent took which specific action, and
under what delegated authority each hop in the chain actually operated.
Without this, a multi-agent, multi-organization interaction becomes
genuinely un-auditable the moment more than one hop is involved — not
because anyone was careless, but because nothing in the interaction
recorded the chain of authority as it happened.

## Key Takeaways for Section 9

Verifiable identity (Section 8's signed cards) answers "is this genuinely
who it claims to be"; delegated credentials answer the separate question
of "was this specific action actually authorized, by whom, for what
scope." An audit trail spanning a multi-hop, cross-boundary delegation
needs to record the full chain — originating user, each agent's specific
action, and the delegated authority behind each hop — or the interaction
becomes un-auditable the moment it crosses more than one boundary.

*Next: back to the number every multi-agent decision actually turns on.*

---

# 10: Cost and Latency Modeling for Multi-Agent

## Starting From Plain Language

Estimating a road trip's cost and duration *before* leaving — not
discovering both only once you're already on the road with no way to turn
back cheaply — is the entire discipline this section asks for, applied to
an architectural decision instead of a drive.

## The Token Multiplier

Directly computable, before writing a line of code, using exactly Chapter
1 and Chapter 4's fixed-prefix-and-accumulation math applied per-agent
(Section 12 works a full example): sum each subagent's own accumulating
context cost, add the orchestrator's cost (its own small prefix plus every
summary it receives), and compare the total against a single agent
handling the same work in one shared, accumulating window. This is a
calculation, not a guess — the exact inputs (fixed prefix size, expected
steps per subagent, summary size) are all things you can estimate from a
task's own shape before ever running it for real.

## Critical-Path Latency

Cost and latency are not the same axis, and conflating them misses half
the picture: if N subagents genuinely run concurrently, **wall-clock time**
is bounded by the *slowest* subagent plus the orchestrator's own
before/after work — not by the sum of all subagents' individual
durations. This is the direct multi-agent analogue of Chapter 7, Section
7's critical-path concept: parallelism buys latency, even when (as
Section 1 already established) it doesn't buy cost — the two benefits are
independent, and a design can win on one while losing on the other.

## Computing Both Before You Build

The discipline this section names directly: estimate the token multiplier
and the critical-path latency *before* committing to a multi-agent
architecture, using a task's own known shape (how many subtopics, how deep
each one plausibly goes, how large a summary genuinely needs to be) —
exactly Section 12's dry-run, but as a planning tool applied to your own
task rather than a worked example applied to a hypothetical one.

## Key Takeaways for Section 10

The token multiplier is directly computable from a task's own shape —
per-subagent accumulation plus orchestrator overhead, compared against a
single shared-window baseline — not something you have to discover only
after building it. Critical-path latency is a genuinely separate axis from
token cost: parallelism can improve wall-clock time even in architectures
where it doesn't improve (or actively worsens) total token spend.

*Next: multi-agent systems fail in ways a single agent's own trace can't
show you at all.*

---

# 11: Debugging Multi-Agent Runs

## Starting From Plain Language

A single detective following one case has one notebook to check when
something doesn't add up. Five detectives working different angles of the
same case, each with their own separate notebook, need someone to
physically collect and cross-reference all five notebooks before anyone
can reconstruct what actually happened across the whole investigation.

## Why This Is Structurally Harder Than Single-Agent Debugging

Chapter 2, Section 9's trajectory log gives a single agent's run a
complete, linear record. A multi-agent run has no such single linear
record by default — each subagent has its *own* trajectory, in its *own*
isolated context, and the orchestrator's own trace only shows what it sent
each subagent and what summary came back, not what actually happened
*inside* any of them.

## Per-Agent Traces, Stitched Into One Parent Trace

The fix this section names, and the direct forward pointer to Chapter 15's
full observability treatment: every subagent needs its own trace,
correlated back to the parent orchestrator's own trace via a shared
identifier, so that a debugging session can reconstruct the *whole*
interaction — which subagent ran when, what it actually did internally,
what it returned, and how the orchestrator used that result — as one
coherent tree, not five disconnected logs someone has to manually
cross-reference after the fact. Without this correlation, a multi-agent
failure is often invisible from the orchestrator's trace alone: the
orchestrator's log might show nothing more informative than "subagent 3
returned an empty summary," with the actual cause buried in subagent 3's
own isolated, otherwise-disconnected trace.

## Key Takeaways for Section 11

A multi-agent run has no single linear trace by default — each subagent's
own trajectory is isolated exactly the way its context is. Correlating
every subagent's trace back to the parent orchestrator's trace via a
shared identifier is what turns five disconnected logs into one coherent,
debuggable tree; Chapter 15 covers the full mechanism.

*Next: putting real numbers under this whole chapter's central tradeoff.*

---

# 12: Dry-Run: 5 Subtopics, Two Architectures, and the Case Where Single-Agent Wins

## The Setup

A research task with **5 independent subtopics**. Each subtopic requires
**10 research steps** (tool calls) to explore thoroughly. Fixed prefix
(system prompt + tool schemas) is **600 tokens** per call, and each
observation returned averages **800 tokens** — the same per-call
assumptions Chapter 1 and Chapter 2's own dry-runs used, applied here at
multi-agent scale.

## Design (a): Single Agent, One Accumulating Window

All 5 subtopics researched sequentially, in one shared window that never
resets — Chapter 1's exact accumulation pattern, now across 50 total steps
($5 \times 10$). Step $i$'s input cost is the fixed prefix plus every prior
step's observation, still sitting in context:

$$\text{total} = \sum_{i=0}^{49} \left(600 + 800 \cdot i\right) = 50 \times 600 + 800 \times \frac{49 \times 50}{2} = 30{,}000 + 980{,}000 = 1{,}010{,}000 \text{ tokens}$$

## Design (b): Orchestrator + 5 Isolated Subagents

Each subagent researches exactly one subtopic, in its **own** window that
never sees the other four subtopics' history — 10 steps, accumulating only
within its own isolated context:

$$\text{per-subagent} = \sum_{i=0}^{9}\left(600 + 800 \cdot i\right) = 10 \times 600 + 800 \times \frac{9 \times 10}{2} = 6{,}000 + 36{,}000 = 42{,}000 \text{ tokens}$$

Five subagents: $5 \times 42{,}000 = 210{,}000$ tokens. The orchestrator's
own context stays small — its own 600-token prefix plus five 500-token
summaries, and nothing else:

$$\text{orchestrator} = 600 + 5 \times 500 = 3{,}100 \text{ tokens}$$

$$\text{total (b)} = 210{,}000 + 3{,}100 = 213{,}100 \text{ tokens}$$

## Where the Multiplier Comes From

$$\frac{1{,}010{,}000}{213{,}100} \approx 4.74\times$$

The mechanism, precisely: design (a)'s cost grows **quadratically** in
total step count, because every single step re-pays for every prior step
still sitting in the one shared window. Design (b) breaks that same total
step count into 5 separate, much shorter accumulations — each subagent
only ever re-pays for *its own* prior steps, never the other four
subtopics' — so its cost grows quadratically *within* 10 steps, not across
50. For this specific shape (5 equal-sized subtopics, quadratic
accumulation), the ratio converges toward roughly the subtopic count
itself as each subtopic gets deeper, which is the direct mechanism behind
why isolating $N$ independent pieces of work saves *roughly* $N\times$ on
this component of cost. Anthropic's own reported ~15× reflects additional
real-world factors this clean toy model doesn't include — more subtopics
per task in their actual workload, redundant re-exploration when one
shared context loses track of what it already covered, and the cost of
retries driven by the accuracy difference itself — but the *direction* and
the *core mechanism* (isolating quadratic growth into smaller, parallel
pieces) are exactly what this arithmetic demonstrates.

## The Case Where Single-Agent Is Cheaper and Better

Shrink the task: **2 subtopics, 1 step each** — genuinely trivial work.

$$\text{single-agent} = \sum_{i=0}^{1}\left(600 + 800 \cdot i\right) = 600 + 1{,}400 = 2{,}000 \text{ tokens}$$

$$\text{multi-agent} = 2 \times 600 + \left(600 + 2 \times 500\right) = 1{,}200 + 1{,}600 = 2{,}800 \text{ tokens}$$

**Single-agent wins here — 2,000 versus 2,800 tokens.** The mechanism
flips because, at this scale, the *fixed* cost of isolation (each subagent
independently re-paying the 600-token prefix, plus the orchestrator's own
separate overhead) is no longer being amortized over enough steps to be
worth it — accumulation within one small shared window barely grew in the
first place, so there was nothing expensive to isolate away from.

## Key Takeaways for Section 12

On 5 subtopics × 10 steps, isolating each subtopic into its own subagent
saves roughly 4.74× the tokens a single shared-accumulating window would
have cost — the direction and mechanism behind Anthropic's own larger
reported multiplier, even though this clean model doesn't reproduce their
exact number. On a genuinely trivial task (2 subtopics, 1 step each),
the same architecture costs *more* — 2,800 versus 2,000 tokens — because
isolation's fixed per-agent overhead isn't amortized by enough
accumulated savings to pay for itself. The lesson isn't "multi-agent is
worth it" or "multi-agent isn't worth it" — it's that the answer is a
genuine function of task depth, computable in advance, exactly as Section
10 argued.

*Next: closing the loop on the whole chapter.*

---

# 13: Key Takeaways + Master Decision Table

The single mental model for this chapter: **use a second agent only when
context isolation is solving a real, measured problem** — quadratic
accumulation genuinely being split into smaller, parallel pieces — and
wire whatever you build with the identity and discovery standards (A2A,
MCP) that actually exist now, rather than a bespoke integration that
won't interoperate with anyone else's agents.

| I want to know... | Reach for | Key fact |
|---|---|---|
| Why multi-agent ever pays for itself at all | Section 1 | Context isolation, specifically -- not sophistication. Anthropic's own number: ~+90% success at ~15x tokens, both halves real |
| Which topology fits my task | Section 2 | Single (default), orchestrator-worker (independent subtopics), pipeline (sequential stages), debate/panel (independent perspectives), hierarchical (multi-level), blackboard/swarm (emergent) |
| How to design a subagent's prompt | Section 3 | It returns structured data, not conversation -- and a shared result schema across subagents lets the orchestrator process results uniformly |
| Where multi-agent structurally fails | Section 4 | Shared mutable state, tightly coupled edits, tasks needing global consistency -- coordination overhead rises with real cross-task dependency |
| Handoff vs delegation vs fan-out | Section 5 | Three distinct control transfers, three distinct failure modes: lost context at the boundary, prose instead of data, uncontrolled cost without budget caps |
| Which parallelism pattern actually works | Section 6 | Fan-out over truly independent items, diverse-lens panels (not identical redundancy), best-of-N with real verifiers, map-reduce research, worktree isolation for concurrent file edits |
| Where MCP fits in a multi-agent world | Section 7 | Governed by the AAIF (Linux Foundation, Dec 2025, 150+ members) -- tool namespacing and server sprawl both compound across every subagent independently |
| What A2A v1.0 actually adds | Section 8 | Signed AgentCards for verifiable identity, at `/.well-known/agent-card.json` -- A2A between agents, MCP down to tools, both used together |
| Identity vs authorization across boundaries | Section 9 | A signed card proves WHO; delegated credentials prove WHETHER this specific action was authorized -- an audit trail needs the full multi-hop chain, not just the endpoints |
| How to estimate cost and latency before building | Section 10 | The token multiplier is directly computable from task shape; critical-path latency is a genuinely separate axis parallelism can win even when cost doesn't |
| Why multi-agent debugging is structurally harder | Section 11 | No single linear trace by default -- per-agent traces must be stitched to the parent via a shared identifier, or failures are invisible from the orchestrator's own log |
| How the 4.74x-ish multiplier is actually computed | Section 12 | Quadratic accumulation in one shared window vs. quadratic accumulation split into N smaller isolated pieces -- and the same math flips in single-agent's favor on genuinely trivial tasks |

**Connection forward:** Chapters 14 through 17 turn from *building*
agentic systems to *trusting* them — evaluation, observability, security,
and production hardening. Multi-agent systems make every one of those four
concerns harder (which trace do you check, which agent's identity do you
verify, which cost do you attribute to which run), which is exactly why
this chapter's own cost-benefit discipline matters before adding the
complexity those next four chapters now have to account for.
