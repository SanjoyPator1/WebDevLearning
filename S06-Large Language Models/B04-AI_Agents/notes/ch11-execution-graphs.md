# Chapter 11: Execution Graphs & Agent Runtimes

## Table of Contents

1. [Two Philosophies: Graph Control vs Model-Driven Loops](#1-two-philosophies-graph-control-vs-model-driven-loops)
2. [The Graph Runtime in Depth](#2-the-graph-runtime-in-depth)
3. [State Schema Design](#3-state-schema-design)
4. [Middleware as the Customization Layer](#4-middleware-as-the-customization-layer)
5. [Checkpointers and Persistence](#5-checkpointers-and-persistence)
6. [Interrupts and Human-in-the-Loop](#6-interrupts-and-human-in-the-loop)
7. [Deep Agents](#7-deep-agents)
8. [Model-Driven Loops in Production](#8-model-driven-loops-in-production)
9. [Framework Decision Framework](#9-framework-decision-framework)
10. [Escaping the Framework](#10-escaping-the-framework)
11. [Dry-Run: State Evolution Through a 5-Node Graph](#11-dry-run-state-evolution-through-a-5-node-graph)
12. [Key Takeaways + Master Decision Table](#12-key-takeaways--master-decision-table)

---

# 1: Two Philosophies: Graph Control vs Model-Driven Loops

## Starting From Plain Language

A train runs on fixed tracks — the driver controls speed and can stop at
any signal, but the train physically cannot leave the rails and end up
somewhere the track doesn't go. A car has no tracks at all — the driver
decides the route turn by turn, in real time, capable of going anywhere a
road connects to, at the cost of nobody but the driver being able to
predict the route in advance. Chapter 2 through Chapter 8 built agents as
cars: a `while` loop where the model decides, every single step, what
happens next. This chapter introduces the train: a graph where the
*possible* transitions are fixed in advance by you, the developer, and the
model's freedom is scoped to *which of the pre-declared tracks* to take,
not whether to invent a new one.

## The Two Philosophies, Named

**Graph-based explicit control** (LangGraph, Microsoft Agent Framework)
compiles the agent's control flow into a structure you author beforehand —
nodes, edges, conditional branches — and the model's decisions happen
*inside* that structure, not instead of it. **Model-driven loops** (the
Claude Agent SDK, OpenAI Agents SDK, Strands, and everything this book
built through Chapter 8) give the model the entire next-step decision:
which tool, which reasoning path, whether to stop — with no externally
pre-declared shape constraining what sequence of actions is even possible.

```
   GRAPH-BASED EXPLICIT CONTROL          MODEL-DRIVEN LOOP

   ┌───────┐    ┌───────┐                ┌─────────────────────┐
   │ Node A │──▶│ Node B │                │   while not done:     │
   └───────┘    └───┬───┘                │     model decides      │
                     │ conditional         │     next action,       │
              ┌──────┴──────┐             │     every single step   │
              ▼             ▼             └─────────────────────┘
         ┌───────┐    ┌───────┐
         │ Node C │    │ Node D │          the SHAPE of the run is
         └───────┘    └───────┘           not fixed in advance --
                                           it emerges from the model's
   the SHAPE of every possible            own decisions, step by step
   run is fixed before any run
   starts -- the model chooses
   WHICH path, not whether a
   new path can exist
```

*(`[DIAGRAM]` — this contrast is the chapter's entire organizing question:
not "which is better" in the abstract, but which one fits a given task's
actual need for predictability versus adaptability.)*

## What Each Buys, and What Each Forfeits

Graph control buys **predictability and debuggability at the structural
level** — you can look at the graph definition itself and know every
possible path a run could take, before a single run ever executes, which
is exactly what Chapter 5's hill-climbing method and Chapter 14's
regression harness want from a system whose behavior needs to be
attributable to a specific version. It forfeits **adaptability to genuinely
unanticipated situations** — a task that needs a step nobody drew an edge
for simply cannot happen, no matter how clearly the model can see that it's
needed. Model-driven loops buy exactly the opposite: **full adaptability**
— the model can chain any sequence of available tools in any order a
problem calls for — at the cost of **structural unpredictability**: the
set of possible execution paths is, in the general case, as large as the
model's own creativity, which is precisely why Chapter 6's entire subject
(verification, stop rules, oscillation detection) exists as compensating
control from *outside* the loop rather than from a pre-declared shape.

## Key Takeaways for Section 1

Graph-based control fixes the possible transitions in advance and lets the
model choose among them; model-driven loops give the model the entire
next-step decision with no pre-declared shape. Graphs buy structural
predictability and debuggability at the cost of adaptability to the
unanticipated; model-driven loops buy full adaptability at the cost of
needing external verification (Chapter 6) to compensate for having no
structural ceiling on what a run could do.

*Next: what a graph-based runtime actually looks like once you open it up.*

---

# 2: The Graph Runtime in Depth

## Starting From Plain Language

A flowchart on a whiteboard has boxes and arrows; a real graph runtime is
that same picture, but every box is executable code, every arrow can carry
a condition, and the whole thing runs against real, typed data flowing
between the boxes rather than being a static diagram someone draws once
and never touches again.

## The Primitives

A **node** is a unit of work — typically a function that reads the current
state and returns an update to it (an LLM call, a tool execution, a
routing decision). An **edge** is a fixed transition from one node to
another, always taken. A **conditional edge** replaces a fixed transition
with a function that inspects the current state and returns *which* node
to go to next — this is the mechanism that gives a graph any adaptive
behavior at all, since without it a graph would just be a single fixed
sequence, no different from a plain script.

**State reducers** govern what happens when a node's output needs to be
merged into the graph's shared state — Section 3 covers this in full, but
the short version: a node doesn't necessarily *overwrite* a field, it can
*combine* its update with whatever was already there, and the reducer is
the function that defines "combine" for that specific field. A node
returning a **`Command`** object bundles two decisions into one return
value that would otherwise need two separate mechanisms: *both* a state
update *and* an explicit routing decision (which node runs next) — useful
specifically when the routing decision can't be cleanly separated from the
state the node just computed (a node that both updates a counter and,
based on that exact counter, decides to loop or exit, without needing a
second conditional-edge function to re-derive the same decision from the
state it just wrote).

A **subgraph** is an entire graph embedded as a single node inside a
larger graph — the same composition idea Chapter 8, Section 10 covered for
skills, one level up: a well-tested, self-contained control-flow unit
reused inside a bigger one rather than inlined and duplicated. **Streaming
semantics** describe how partial results surface while a graph is still
running — a graph can stream a node's own token-by-token output the same
way Chapter 2, Section 8 covered for a plain loop, or stream at a coarser
grain, emitting a complete state update every time a node finishes, which
matters for anything showing live progress across a multi-node run rather
than just live tokens within one call.

## Key Takeaways for Section 2

Nodes do work and return state updates; edges are fixed transitions;
conditional edges are functions that choose the next node from the current
state, and are the only source of real branching in a graph. Reducers
define how a node's update merges into shared state; a `Command` return
bundles a state update and a routing decision together when they're
naturally the same decision. Subgraphs let a whole graph act as one node
inside a larger graph; streaming can surface either token-level or
node-level progress.

*Next: of everything just introduced, one decision matters more than the
rest combined.*

---

# 3: State Schema Design

## Starting From Plain Language

A shared spreadsheet used by five different people editing different
columns works fine if everyone agrees, in advance, what happens when two
people try to update the same cell at once — does the last save win, does
it merge, does it get flagged as a conflict? A graph's state schema is
exactly this agreement, made explicit and enforced by the runtime instead
of left to chance.

## Reducers vs Overwrites

By default, when a node returns an update to a state field, the simplest
possible reducer is **last-write-wins** — the new value replaces whatever
was there, full stop. This is correct for fields representing a single
current value that should only ever reflect the most recent node's
judgement (a confidence score, a current phase name). It is *catastrophic*
for fields meant to accumulate — most famously, a **message list**: if the
message-list field uses last-write-wins, every node that returns a new
message *replaces the entire prior conversation* with just that one
message, and the agent silently loses everything that happened before the
current node ran. The fix is an **append reducer** — often provided as a
first-class option specifically for message lists (commonly a helper
function that concatenates the new messages onto the existing list rather
than replacing it) — and getting this one choice wrong, for the one field
almost every agent graph has, is the single most common state-schema bug
in a first LangGraph agent: the model appears to "forget" everything after
its first tool call, and the actual cause is a reducer silently discarding
history that was never actually lost, just overwritten.

```
   LAST-WRITE-WINS (correct for a single current value)

   node A returns: {"phase": "retrieving"}     state.phase = "retrieving"
   node B returns: {"phase": "critiquing"}     state.phase = "critiquing"  <- B's value replaces A's

   APPEND (correct for accumulating history)

   node A returns: {"messages": [msgA]}        state.messages = [msgA]
   node B returns: {"messages": [msgB]}        state.messages = [msgA, msgB]  <- B's value is ADDED, not swapped
```

## Channel Design

A state schema is really a set of independent **channels**, each with its
own type and its own reducer, and designing it well means asking, for
*every single field*, "should a new value here replace the old one, or
combine with it?" — never assuming one answer covers the whole schema.
Getting this granular, field-by-field, is what prevents the single most
damaging failure mode: applying an accumulating reducer to a field that
should have been overwritten (a "current retry count" that never resets
because it's stuck on append-only accumulation) is just as broken as the
reverse case above, in the opposite direction.

## Why This Is the Most Consequential Decision in a Graph Agent

Every other design choice in this chapter — which nodes exist, how edges
route, which middleware wraps execution — is comparatively easy to change
later, because none of it touches what data actually persists between
runs or survives a checkpoint (Section 5). The state schema is different:
it's the shape every checkpoint is serialized against, the shape every
subgraph has to interoperate with, and the shape every piece of middleware
reads and writes through. Changing a reducer's semantics after a system
has real checkpointed state in production risks corrupting or silently
misinterpreting every already-persisted run — this is the graph-runtime
analogue of Chapter 5, Section 8's harness-versioning discipline, and it's
the one place in this chapter where "just refactor it later" is
meaningfully more expensive than everywhere else.

## Key Takeaways for Section 3

Every state field needs an explicit answer to "replace or combine": last-
write-wins for single current values, append for accumulating history —
and the single most common first-agent bug is a message list stuck on the
wrong one of the two, which looks exactly like the agent forgetting its
own conversation. Design reducers per-channel, not as one blanket policy.
This is the most consequential decision in the whole graph specifically
because checkpoints (Section 5) serialize against it, making it expensive
to change once real state exists.

*Next: where do cross-cutting concerns like retries, guardrails, and
logging actually live, if not inside every node?*

---

# 4: Middleware as the Customization Layer

## Starting From Plain Language

Building airport security into the design of every single gate — rebuilt
from scratch, individually, at each one — would be an obviously bad way to
run an airport. The actual answer is one shared security checkpoint every
passenger passes through on the way to *any* gate, built once, applied
uniformly. Middleware is that shared checkpoint, applied to graph nodes
instead of airport gates.

## The 2026 Idiom

Cross-cutting concerns — automatic conversation summarization when context
grows too large (Chapter 4), guardrails that block or rewrite certain
outputs, retry policies for a flaky node, permission checks before a
side-effecting tool call (Chapter 16, previewed here), and structured
logging — used to mean either duplicating that logic inside every node
that needed it, or performing invasive "graph surgery": manually inserting
extra nodes and edges around every point where a concern applied. The
2026 LangGraph/`deepagents` idiom replaces both with **composable
middleware**: a piece of logic that wraps node execution generically,
declared once and attached to the graph (or a subgraph) as a whole, the
same separation-of-concerns instinct behind HTTP middleware in a web
framework — request/response interceptors that never need to know what
any specific route handler does.

```
        request into the graph
                 │
                 ▼
        ┌─────────────────┐
        │  MIDDLEWARE:      │   <- summarization, guardrails,
        │  wraps EVERY       │      retries, permissions, logging --
        │  node's execution  │      written ONCE, not per-node
        └────────┬──────────┘
                  ▼
             [ Node A ]
                  │
        (middleware wraps this transition too)
                  ▼
             [ Node B ]
```

## Why This Beats Reimplementing the Same Logic Inside Every Node

The failure mode this section directly targets — one of this chapter's
named gotchas — is **reimplementing middleware inside nodes**: a guardrail
check pasted into five different node functions independently, which then
drifts out of sync the instant one of the five gets updated and the other
four don't. Middleware, attached once at the graph level, is updated once
and applies everywhere it's attached automatically — the same
hill-climbing attributability Chapter 5, Section 10 wanted from a harness
version: one middleware change, one measurable effect, rather than five
scattered edits whose combined effect nobody can cleanly attribute.

## Key Takeaways for Section 4

Middleware wraps node execution generically for cross-cutting concerns —
summarization, guardrails, retries, permissions, logging — declared once
rather than duplicated inside every node that needs it or hand-inserted as
extra graph structure. This is directly what prevents one of this
chapter's named failure modes: the same concern reimplemented five
different, slowly-diverging ways across five different nodes.

*Next: none of a graph's state is worth anything if the process holding it
can die.*

---

# 5: Checkpointers and Persistence

## Starting From Plain Language

A video game that only saves your progress when you manually choose "Save"
is one accidental crash away from losing everything since the last save
point. A game with autosave after every level transition loses, at worst,
the current level in progress — a fundamentally different risk profile,
purchased by making persistence automatic rather than something the player
has to remember to trigger.

## What a Checkpointer Actually Does

A **checkpointer** is a persistence layer attached to a compiled graph
that writes the *entire current state* after every single node transition
— not manually triggered, not optional, automatic by default. This is a
direct structural advantage graph runtimes have over a hand-rolled loop:
Chapter 12 will build durability into a plain loop by hand, one JSONL
event at a time; a graph runtime gets the equivalent property essentially
for free, as a consequence of the graph structure itself defining natural
checkpoint boundaries (the space between one node finishing and the next
one starting).

## Thread State, Namespaces, and Time-Travel

A **thread** is one continuous, identified run of a graph — its own
independent stream of checkpoints, addressable later by that thread's ID,
which is what makes resuming a specific conversation or task (rather than
starting fresh) possible at all. **Checkpoint namespaces** scope
checkpoints so that a subgraph's internal checkpoints don't collide with
or get confused for the parent graph's — the same nested-scoping instinct
Chapter 7's plan-file-per-subtask idea reflected, applied to persistence
instead of planning. **Time-travel / replay** — being able to rewind a
thread to any prior checkpoint and either inspect exactly what the state
was at that point or *resume execution from there* with a modified
input — turns debugging a bad run from "re-run the whole thing and hope
you can reproduce the bug" into "load the exact state right before things
went wrong and try again from there," a debugging capability a plain
loop's own linear message list has no equivalent for without Chapter 9's
own memory-log machinery bolted on by hand.

## Resuming After a Crash or a Deploy

Because every node transition is checkpointed automatically, a crashed
process (or a mid-run deploy of new code) doesn't have to mean restarting
a thread from scratch — the checkpointer already has the state as of the
last completed node, and resuming means loading that checkpoint and
continuing forward, which is exactly the property Chapter 12's entire
durable-execution chapter builds from first principles for the
hand-rolled-loop case. A graph runtime's checkpointer is this same
guarantee, provided by the framework rather than hand-built.

## Key Takeaways for Section 5

A checkpointer automatically persists full state after every node
transition — no manual save step. Threads are independently resumable
runs; namespaces keep a subgraph's checkpoints from colliding with its
parent's; time-travel lets you rewind to any prior checkpoint, inspect it,
or resume from it with a changed input. This gives graph runtimes a
durability property Chapter 12 has to build by hand for a plain loop, more
or less for free, as a structural consequence of the graph itself.

*Next: sometimes the next step in a graph shouldn't be a model or a tool
at all -- it should be a person.*

---

# 6: Interrupts and Human-in-the-Loop

## Starting From Plain Language

A form that submits itself the instant you finish typing, with no "Are you
sure?" confirmation step, is unnerving for exactly the actions that matter
most — deleting an account, sending a payment. A well-designed form pauses
at precisely those points and waits for a deliberate human confirmation
before continuing.

## `interrupt()` Semantics

An **interrupt** pauses graph execution at a specific point, mid-run,
surfacing whatever context is needed for a human decision, and — this is
the detail that makes it more than "the graph stopped" — the graph's
*entire state at that exact point* is checkpointed (Section 5) as part of
pausing, so resuming later picks up exactly where execution left off, not
from some approximation of it. This is Chapter 6, Section 10's
human-in-the-loop primitive, given a first-class runtime mechanism instead
of being hand-rolled as a special stop condition inside a plain loop.

## Approval Payload Design

What actually gets shown to the human at an interrupt point is itself a
design surface, not an afterthought: a well-designed approval payload
shows exactly what's about to happen (the specific tool call, its exact
arguments, the blast radius) in a form a human can evaluate in seconds —
the same "cheap for the human to grant" principle Chapter 6, Section 10
already named. A poorly-designed one dumps a wall of raw internal state
and expects the human to reverse-engineer what's actually being asked.

## Resuming With Edited State

The detail that goes beyond a simple pause/resume toggle: because the full
state is available at the interrupt point, a human isn't limited to a
binary approve/reject — they can **edit the state directly** before
resuming (correcting a tool call's arguments, adjusting a plan, striking
an item) and the graph continues from that *edited* state rather than the
original one. This is meaningfully more powerful than an approval gate
bolted onto a plain loop as an if-statement, because the loop's own
in-flight variables generally aren't exposed for a human to reach in and
change — the graph's checkpointed state, by contrast, already *is* the
complete, editable picture.

## Key Takeaways for Section 6

An interrupt pauses execution with the full state checkpointed, not
approximated, at that exact point. Approval payload design matters as much
as the interrupt mechanism itself — show exactly what's about to happen,
cheaply evaluable. Resuming with edited state, not just approve/reject, is
the capability a checkpointed graph offers that a plain loop's in-flight
variables structurally can't match.

*Next: one specific, influential pattern for combining several of this
chapter's pieces into a reference architecture worth studying directly.*

---

# 7: Deep Agents

## Starting From Plain Language

A single competent generalist handling an entire complex project alone
works up to a point; a small team with one person planning and delegating,
a shared project folder everyone reads and writes to, and clear rules
about who checks whose work scales further, for the same underlying
reason chapters 5 through 9 have been building toward all along:
externalizing plans and context beats holding everything in one person's
(or one agent's) head.

## The Pattern

**Deep agents** is the name given to a specific, recurring architecture
combining four pieces this book already built separately: a **planning
agent** that owns the overall task decomposition (Chapter 7), a
**filesystem** used as durable working memory and a plan artifact store
rather than relying on context alone (Chapter 7, Section 1's whole
argument, plus Chapter 9's memory), **subagents** for isolated,
delegated sub-tasks (a forward pointer to Chapter 13's multi-agent
subject), and **middleware** (Section 4) handling the cross-cutting
concerns — summarization, guardrails — that would otherwise need
reimplementing across every subagent independently.

```
        ┌─────────────────────┐
        │   PLANNING AGENT      │  owns decomposition (Ch 7)
        └──────────┬───────────┘
                    │ writes/reads
                    ▼
        ┌─────────────────────┐
        │     FILESYSTEM        │  durable plan + working memory
        │  (plan files, notes)  │  (Ch 7 + Ch 9), not just context
        └──────────┬───────────┘
                    │ delegates
                    ▼
        ┌─────────────────────┐
        │      SUBAGENTS         │  isolated sub-tasks (Ch 13 preview)
        └──────────┬───────────┘
                    │ wrapped by
                    ▼
        ┌─────────────────────┐
        │      MIDDLEWARE        │  summarization, guardrails (Sec 4)
        └─────────────────────┘
```

## LangChain's `deepagents` as a Reference Harness

Rather than a novel invention, `deepagents` is best read as a *reference
implementation* of a pattern several teams converged on independently once
they'd internalized the lessons of this book's earlier chapters — proof
that Chapters 5 through 9's individual pieces (harness anatomy, loop
control, planning artifacts, skills, memory) combine coherently into one
architecture rather than existing as separate, unrelated techniques.
Reading its source is a useful exercise specifically *because* every piece
maps cleanly back to a chapter already covered, which makes it a genuine
comprehension check on the book so far rather than new material to learn
from scratch.

## Key Takeaways for Section 7

Deep agents combine a planning agent, a filesystem for durable plan and
memory storage, delegated subagents, and middleware for cross-cutting
concerns — four pieces this book built separately in Chapters 5-9, now
shown to compose into one coherent reference architecture.
`deepagents` is worth reading precisely because every piece of it should
already be recognizable.

*Next: graphs aren't the only production answer -- model-driven loops have
their own real, current production story.*

---

# 8: Model-Driven Loops in Production

## Starting From Plain Language

Not every problem that could be solved by a train needs one — sometimes a
fleet of cars, each one free to route itself in real time, gets more
passengers to more destinations faster than laying track for every
possible route in advance ever could.

## Handoffs

The OpenAI Agents SDK's signature pattern is the **handoff**: one agent
transfers an entire in-progress conversation to a different, more
specialized agent, which takes over with full context rather than
starting cold. This is a genuinely different shape than Section 1's graph
edges — a handoff isn't a pre-declared transition between two fixed nodes
in a diagram; it's a *decision the first agent makes at runtime*, choosing
which specialist to hand off to based on what the conversation actually
needs, which fits naturally with use cases whose specialization boundaries
are clear in principle but whose *routing* genuinely depends on the
specific conversation's content — tiered customer support, multi-provider
conversational routing.

## Sessions and Managed Agents

**Sessions** provide the always-append conversation persistence Chapter 2,
Section 3 already covered as the production-standard pattern, as a
first-class SDK primitive rather than something you write yourself.
**Managed agents** go a step further, hosting the agent's execution
environment as a separate product layer entirely (briefly named back in
Chapter 2, Section 10) — you don't provision or maintain the runtime at
all, only the agent's configuration and tools.

## Where Model-Driven Loops Beat Graphs on Iteration Speed

The concrete, practical edge model-driven loops hold over graphs: changing
an agent's behavior means changing a prompt or a tool, not redrawing a
graph's structure and re-validating every edge and conditional function
still makes sense against the new behavior. For a genuinely open-ended
coding or ops agent (the Claude Agent SDK's own sweet spot) where the
right *sequence* of actions is different on every single run, a
pre-declared graph structure would either need an edge for every
conceivable sequence (defeating the point of a graph's predictability) or
force the agent into a narrower set of behaviors than the model is
actually capable of — model-driven loops simply don't pay this cost,
because there's no pre-declared structure to keep consistent with the
agent's evolving behavior in the first place.

## Key Takeaways for Section 8

Handoffs (OpenAI Agents SDK) are a runtime decision transferring full
conversation context between specialist agents — not a pre-declared graph
edge. Sessions and managed agents productize patterns this book already
covered (always-append persistence, hosted execution) as first-class SDK
primitives. Model-driven loops win decisively on iteration speed for
genuinely open-ended tasks, because there's no graph structure that needs
to stay consistent with the agent's own evolving behavior.

*Next: turning "graph vs loop" from a philosophical preference into an
actual, fillable decision table.*

---

# 9: Framework Decision Framework

## Starting From Plain Language

Choosing a car by test-driving it against your actual commute, not by
reading a spec sheet in the abstract, is the only way to know whether it
actually fits your life. The same discipline applies here: a framework
comparison is only useful once you've filled it in against your own real
task, not accepted as someone else's abstract ranking.

## The Table to Fill In Yourself

| Dimension | What to actually measure |
|---|---|
| Controllability | Can you enumerate every possible path a run could take, before running it? |
| Debuggability | When a run fails, how quickly can you find *which* step and *why* — time-travel/replay (Section 5) vs re-running and hoping |
| Persistence | Is checkpointing automatic (Section 5) or something you build yourself |
| Multi-agent | How naturally does the framework express delegation — subgraphs (Section 2), handoffs (Section 8), or bolted on |
| MCP/A2A support | First-class, or an integration you write and maintain yourself |
| Lock-in | How much of your agent's logic is expressed in framework-specific primitives that don't translate elsewhere |
| Lines of code for the same task | The most concrete, least arguable number of all -- measured on one real task, not estimated |

## Why This Chapter Deliberately Doesn't Fill It In For You

Every one of the frameworks this chapter names — LangGraph, Microsoft
Agent Framework, Claude Agent SDK, OpenAI Agents SDK, Strands — genuinely
wins on some rows and loses on others, and no fixed ranking survives
contact with an actual project's specific constraints (which MCP servers
you already depend on, how much of your team already knows one
framework's idioms, whether your task is closer to Section 1's train or
car). This table's value is entirely in the *measuring*, on your own real
task — Section 11's dry-run gives you practice reading a graph's state
evolution precisely so that when you do fill this table in for real, "how
debuggable is this" is something you can answer from direct experience
with the mechanism, not from a vendor's claim about it.

## Key Takeaways for Section 9

The decision table has seven concrete, measurable dimensions —
controllability, debuggability, persistence, multi-agent support,
protocol support, lock-in, and lines of code — each answerable by direct
measurement on your own task, not by accepting someone else's abstract
framework ranking. No framework wins every dimension; the table's job is
making the tradeoff visible, not resolving it for you.

*Next: whichever framework you pick, one discipline protects you from
having picked wrong.*

---

# 10: Escaping the Framework

## Starting From Plain Language

A well-built house has plumbing and wiring that could, in principle, be
serviced or replaced by a different contractor later, because it follows
standard fittings rather than every pipe being custom-welded specifically
to one plumber's proprietary tools. A harness built the same way survives
a framework migration; one that doesn't, can't.

## The Parts That Must Stay Framework-Independent

Not everything needs to be portable — the actual graph wiring, the
specific middleware implementation, the checkpointer's storage backend can
all be framework-specific without much cost, because replacing them is
mechanical once the decision to migrate is made. What genuinely needs to
stay independent is **the parts a migration can't cheaply regenerate**:
your tool definitions and their business logic (Chapter 3) — these should
be plain functions with clear schemas, callable from *any* framework's
tool-calling convention, not written against one SDK's specific decorator
API in a way that couples the logic itself to the framework. Your
**evaluation suite** (Chapter 14, previewed here) — a set of real tasks
and checkable outcomes that exists *outside* any framework's own test
harness, so a migration is judged against the same yardstick before and
after. Your **prompts and instructions** — plain text, versioned in your
own repository, not embedded inside framework-specific configuration that
would need translating. And your **trajectory logs** (Chapter 2, Section
9) — a plain JSONL format your own analysis tooling reads, not a
framework's proprietary trace format your tooling can't parse without that
framework's SDK installed.

## Why This Matters Even If You Never Actually Migrate

The discipline pays for itself even in the world where you never switch
frameworks: keeping tool logic, evals, prompts, and logs framework-
independent is *also* exactly what makes a framework upgrade (a new major
version of the same framework, not a switch to a different one)
low-risk, and framework upgrades happen far more often than full
migrations. The insurance is cheap to buy and expensive to have skipped
the one time you actually need it — the same "measure twice" logic behind
Chapter 6's verification discipline, applied to architectural decisions
instead of individual agent steps.

## Key Takeaways for Section 10

Tool logic, your evaluation suite, prompts, and trajectory logs should
stay framework-independent — plain functions, plain checkable tasks, plain
text, plain JSONL — because these are the parts a migration can't cheaply
regenerate. Graph wiring, middleware implementation, and checkpointer
backends can be framework-specific without much migration cost. This
discipline pays for itself even without a full migration, because it's
the same thing that makes ordinary framework upgrades low-risk.

*Next: putting exact state dictionaries under Section 2 and Section 3's
abstract claims about reducers and conditional edges.*

---

# 11: Dry-Run: State Evolution Through a 5-Node Graph

## The Setup

A small agentic-RAG graph (Chapter 10, Section 5's pattern, now expressed
as an explicit graph rather than a plain loop) with **two reducers** and
**one conditional edge**. State schema: `messages` (list, **append**
reducer), `retrieved_docs` (list, **append** reducer), `confidence`
(float, **last-write-wins**), `current_step` (string, **last-write-wins**).
Five nodes: `Retrieve1`, `Critique`, `Rewrite`, `Retrieve2`, `Generate`.
One conditional edge, at `Critique`: if `confidence >= 0.8`, go straight to
`Generate`; otherwise, go to `Rewrite`. We trace the branch where the first
retrieval isn't good enough, so all five nodes actually execute.

**Initial state:**

```
messages=["user: what's the 2024 pricing?"], retrieved_docs=[], confidence=0.0, current_step="start"
```

## Node-by-Node, Full State After Each

**Node 1 -- `Retrieve1`** returns `{"messages": ["assistant: retrieved D1 (2023 pricing doc)"], "retrieved_docs": ["D1"], "confidence": 0.3, "current_step": "retrieve1"}`.

```
messages       = ["user: what's the 2024 pricing?", "assistant: retrieved D1 (2023 pricing doc)"]   <- APPENDED
retrieved_docs = ["D1"]                                                                                <- APPENDED
confidence     = 0.3                                                                                   <- OVERWRITTEN (was 0.0)
current_step   = "retrieve1"                                                                           <- OVERWRITTEN (was "start")
```

**Node 2 -- `Critique`** returns `{"messages": ["assistant: D1 covers 2023, not 2024 -- insufficient"], "confidence": 0.3, "current_step": "critique"}` (no `retrieved_docs` key returned at all -- the append reducer on an *absent* key simply leaves the list unchanged).

```
messages       = [..., "assistant: D1 covers 2023, not 2024 -- insufficient"]   <- APPENDED (3 entries now)
retrieved_docs = ["D1"]                                                          <- UNCHANGED (nothing returned for this key)
confidence     = 0.3                                                            <- OVERWRITTEN (same value, still a real overwrite)
current_step   = "critique"                                                     <- OVERWRITTEN
```

**Conditional edge fires here:** `confidence (0.3) < 0.8` → route to `Rewrite`, not `Generate`.

**Node 3 -- `Rewrite`** returns `{"messages": ["assistant: rewriting query -> '2024 pricing specifically'"], "current_step": "rewrite"}`.

```
messages       = [..., "assistant: rewriting query -> '2024 pricing specifically'"]   <- APPENDED (4 entries)
retrieved_docs = ["D1"]                                                                <- UNCHANGED
confidence     = 0.3                                                                   <- UNCHANGED (not returned this node)
current_step   = "rewrite"                                                             <- OVERWRITTEN
```

**Node 4 -- `Retrieve2`** returns `{"messages": ["assistant: retrieved D2 (2024 pricing doc)"], "retrieved_docs": ["D2"], "confidence": 0.9, "current_step": "retrieve2"}`.

```
messages       = [..., "assistant: retrieved D2 (2024 pricing doc)"]   <- APPENDED (5 entries)
retrieved_docs = ["D1", "D2"]                                          <- APPENDED (D2 added, D1 still there)
confidence     = 0.9                                                   <- OVERWRITTEN
current_step   = "retrieve2"                                           <- OVERWRITTEN
```

**Node 5 -- `Generate`** returns `{"messages": ["assistant: 2024 pricing is $49/mo, per D2"], "current_step": "generate"}`.

```
messages       = [..., "assistant: 2024 pricing is $49/mo, per D2"]   <- APPENDED (6 entries, full history intact)
retrieved_docs = ["D1", "D2"]                                          <- UNCHANGED
confidence     = 0.9                                                   <- UNCHANGED (not returned this node)
current_step   = "generate"                                            <- OVERWRITTEN
```

## Why This Trace Is the Point

Every single message from all five nodes is still present in the final
`messages` list — the append reducer never drops anything, which is
exactly Section 3's point about why message lists need this reducer and
not last-write-wins. `retrieved_docs` shows the same accumulation,
independently. `confidence` and `current_step`, by contrast, only ever
show their *most recent* value in the final state — there is no history of
every confidence score the graph ever computed, because last-write-wins
was the correct choice for both fields (nothing about "what was the
confidence three nodes ago" is a question this schema was designed to
answer, correctly). The conditional edge's decision — visible only at the
one moment `confidence` was checked against the `0.8` threshold — is not
itself stored anywhere in state; it's a transient routing decision, not
data, which is worth noticing precisely because it's easy to assume
everything a graph "decides" gets persisted, and it doesn't unless a node
explicitly writes it to a field.

## Key Takeaways for Section 11

Tracing five real nodes shows unambiguously what Sections 2 and 3 argued
abstractly: append-reducer fields (`messages`, `retrieved_docs`) retain
every node's contribution in order; last-write-wins fields (`confidence`,
`current_step`) retain only the most recent value, by design. The
conditional edge's routing decision itself leaves no trace in state unless
a node deliberately writes it there — a graph only remembers what its
reducers were told to remember.

*Next: closing the loop on the whole chapter.*

---

# 12: Key Takeaways + Master Decision Table

The single mental model for this chapter: **a graph trades the model's
freedom to invent a new path for your ability to know, in advance, every
path that could exist** — and that trade is worth making exactly when
predictability matters more than adaptability for the task at hand, never
as a default assumed to be "more sophisticated" than a plain loop.

| I want to know... | Reach for | Key fact |
|---|---|---|
| Graph or loop, for this task | Section 1 | Graphs buy structural predictability at the cost of adaptability; loops buy full adaptability at the cost of needing external verification to compensate |
| What a graph runtime is actually made of | Section 2 | Nodes do work, edges are fixed transitions, conditional edges are the only source of branching, `Command` bundles a state update with a routing decision |
| Why my agent "forgot" its own conversation | Section 3 | A message-list field almost certainly needs an append reducer, not last-write-wins -- the single most common first-agent state bug |
| Where cross-cutting concerns belong | Section 4 | Composable middleware, applied once at the graph level -- never reimplemented independently inside every node that needs it |
| What durability a graph gives you for free | Section 5 | Automatic checkpointing after every node transition; threads, namespaces, and time-travel/replay come from this same mechanism |
| How to pause for a human safely | Section 6 | `interrupt()` checkpoints full state at the pause point; resuming can use edited state, not just approve/reject |
| A reference architecture worth reading | Section 7 | Deep agents = planning agent + filesystem + subagents + middleware -- four ideas this book already built separately, shown composing |
| When model-driven loops win | Section 8 | Genuinely open-ended tasks where the right action sequence differs every run -- no graph structure to keep consistent with evolving behavior |
| How to actually compare frameworks | Section 9 | Seven measurable dimensions, filled in against your own real task -- controllability, debuggability, persistence, multi-agent, protocol support, lock-in, LOC |
| What must survive a framework migration | Section 10 | Tool logic, eval suite, prompts, trajectory logs -- kept plain and framework-independent; graph wiring and middleware can be framework-specific |
| How reducers actually behave, traced exactly | Section 11 | Append reducers retain every contribution in order; last-write-wins retains only the latest; a routing decision leaves no trace unless a node writes it to state |

**Connection forward:** Chapter 12 stays inside the world of durable,
resumable execution but shifts the question from "what does a graph give
me for free" to "what do I have to build by hand when there's no graph
runtime underneath me at all" -- taking Chapter 6's plain loop and making
it survive a crash, a deploy, and a queue of 200 waiting runs, using
exactly the primitives (event logs, replay, idempotency) a graph's
checkpointer was quietly providing all along.
