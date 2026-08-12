# Chapter 9: Agent Memory

## Table of Contents

1. [Why This Chapter Exists: Memory vs Context vs Storage](#1-why-this-chapter-exists-memory-vs-context-vs-storage)
2. [The Three-Scope Taxonomy: Episodic, Semantic, Procedural](#2-the-three-scope-taxonomy-episodic-semantic-procedural)
3. [Working Memory: the In-Context Scratchpad](#3-working-memory-the-in-context-scratchpad)
4. [The OS Analogy: Core, Archival, and Recall Memory](#4-the-os-analogy-core-archival-and-recall-memory)
5. [The 2026 Production Pattern: Hot Path / Cold Path](#5-the-2026-production-pattern-hot-path--cold-path)
6. [Framework Landscape: Mem0, Zep/Graphiti, Letta, LangMem, DIY](#6-framework-landscape-mem0-zepgraphiti-letta-langmem-diy)
7. [Retrieval for Memory Is Not RAG for Documents](#7-retrieval-for-memory-is-not-rag-for-documents)
8. [Forgetting, Staleness, and Conflict](#8-forgetting-staleness-and-conflict)
9. [Memory Evaluation](#9-memory-evaluation)
10. [Continual Learning Framing](#10-continual-learning-framing)
11. [Memory as an Attack Surface](#11-memory-as-an-attack-surface)
12. [Dry-Run: Salience Scoring, Ranked by Hand](#12-dry-run-salience-scoring-ranked-by-hand)
13. [Key Takeaways + Master Decision Table](#13-key-takeaways--master-decision-table)

---

# 1: Why This Chapter Exists: Memory vs Context vs Storage

## Starting From Plain Language

Three words get used almost interchangeably in casual agent discussion, and
conflating them is where most memory-system designs go wrong before a line
of code is written. **Context** is what's in the message list *right now*,
for *this* run — Chapter 2's whole subject, gone the instant the process
exits unless something else saved it. **Storage** is any durable place bytes
can live — a database, a file, a blob store — with no opinion at all about
*what* is worth keeping or *how* it should be found again. **Memory** is the
narrower, harder thing sitting between them: a *deliberate policy* about
what survives from one session into the next, written to storage, and
retrieved back into context only when it's actually relevant.

```
        CONTEXT                    MEMORY                    STORAGE
   ┌──────────────┐         ┌──────────────────┐       ┌──────────────┐
   │ this run's    │         │ a POLICY: what    │       │ any durable   │
   │ message list  │◀───────▶│ survives, in what  │◀─────▶│ place bytes   │
   │ (Chapter 2)   │ write/  │ shape, retrieved   │ CRUD  │ can live       │
   │ gone at exit  │ read    │ how, forgotten how │       │ (no opinion)   │
   └──────────────┘         └──────────────────┘       └──────────────┘
```

*(`[DIAGRAM]` — this is the one distinction the rest of the chapter assumes
you've internalized: a Postgres table is storage; a vector index over that
table is still just storage with a different lookup shape; *memory* is the
decision layer on top that decides what goes in, what comes out, and when
something gets forgotten.)*

## Why the Conflation Is the Actual Failure Mode

"We added a vector database, so the agent has memory now" is the single
most common version of this mistake. A vector database is storage with
similarity search — it has no opinion about whether a fact is still true,
whether it's worth keeping past 90 days, or whether it contradicts
something written last week. Memory is not a product you install; it's a
set of decisions — what to write, what to keep, what to forget, how to
retrieve — that this chapter walks through one at a time, several of which
have nothing to do with vectors at all (Section 7's central argument).

## Key Takeaways for Section 1

Context is this run's message list, gone at exit. Storage is any durable
place with no retrieval policy attached. Memory is the deliberate policy
layer connecting the two — what gets written, kept, forgotten, and
retrieved, and why. Installing a vector database answers none of those
questions by itself; it just gives you a place to put an answer once
you've made it.

*Next: memory isn't one thing even once you've drawn this boundary — it
splits into three genuinely different kinds.*

---

# 2: The Three-Scope Taxonomy: Episodic, Semantic, Procedural

## Starting From Plain Language

Ask a long-time colleague what they remember about working with you, and
the answer comes back in three different flavors without them ever
noticing the seam. They remember *specific things that happened* ("we
shipped the v2 migration together in March, and it broke on a Friday").
They remember *facts about you* ("you prefer terse code review comments").
And they remember *how to do things around you* ("I know not to merge
without running your test suite first, because that bit me once"). Cognitive
science names these episodic, semantic, and procedural memory respectively,
and the field converged on borrowing the same three-way split for agents,
because the three kinds genuinely need different storage shapes and
different retrieval logic.

## The Three Scopes, Precisely

**Episodic memory** is *what happened* — a specific interaction, a
timestamped event, a particular conversation. It's written as a log entry
and is most useful when a later question specifically needs "what did we
discuss last Tuesday," not a general fact. **Semantic memory** is *facts
and preferences*, stripped of the specific episode that revealed them —
"the user prefers dark-mode diagrams," independent of which conversation
that came up in. **Procedural memory** is *learned behaviors and rules* —
not a fact about the world, but a rule about how the agent itself should
act ("always run tests before proposing a merge in this repo"), closer to
Chapter 5's instruction files than to a fact lookup.

| Scope | Answers | Example | Typical store shape |
|---|---|---|---|
| Episodic | "What happened, and when?" | "On 2026-03-04 we shipped the v2 migration" | Append-only log, timestamped |
| Semantic | "What's true, generally?" | "The user prefers terse code review comments" | Key-value or small relational table |
| Procedural | "How should I behave here?" | "Always run tests before proposing a merge in this repo" | Instruction text, versioned like Chapter 5's `CLAUDE.md` |

## Why the Split Matters Operationally, Not Just Conceptually

Each scope has a different write trigger, a different decay rate, and a
different retrieval query shape — collapsing all three into one flat table
of "memories" is exactly what makes contradiction handling (Section 8) and
retrieval quality (Section 7) hard later. An episodic entry is written
once and essentially never edited (you don't rewrite history — you can only
add a new entry that references or corrects an old one). A semantic fact
is *the same key*, potentially overwritten as it changes — Section 8's
supersession problem lives almost entirely here. A procedural rule changes
rarely and deliberately, the same hill-climbing discipline Chapter 5,
Section 10 required of a harness version.

## Key Takeaways for Section 2

Episodic memory answers "what happened," semantic memory answers "what's
true," procedural memory answers "how should I act" — and treating all
three as one undifferentiated bucket of "memories" is the root cause of
several failures the rest of this chapter names precisely (contradiction
handling in Section 8, retrieval quality in Section 7). Each scope gets a
different store shape and a different update rule.

*Next: before any of this reaches durable storage, there's a memory that
never leaves the current run at all.*

---

# 3: Working Memory: the In-Context Scratchpad

## Starting From Plain Language

Working memory is what you're holding in your head *right now*, mid-task —
the running total you haven't written down yet, the three things you still
need to check before you're done. It's real, it's useful, and it
disappears the instant you stop thinking about it unless you write it
somewhere durable.

## Working Memory Is Chapter 4's Token Budget, Not a New Mechanism

For an agent, working memory *is* the in-context scratchpad — the portion
of the message list actively being used for the task at hand, subject to
exactly the same token-budget accounting Chapter 4, Section 3 already
built. This is not a fourth memory scope alongside episodic, semantic, and
procedural; it's the *live, in-context copy* of whatever the agent is
currently reasoning about, some of which may get promoted to one of the
three durable scopes (Section 2) before the run ends, and the rest of which
simply evaporates when the context window closes or compacts.

```
   durable memory (episodic / semantic / procedural)
        │  read (retrieval, Section 7)
        ▼
   ┌─────────────────────────┐
   │  WORKING MEMORY           │   <-- Chapter 4's token budget,
   │  (in-context scratchpad)  │       nothing new here
   └─────────────────────────┘
        │  write (promotion -- hot path, Section 5)
        ▼
   durable memory
```

## Why This Section Is Short, and Deliberately So

Working memory doesn't need its own storage model or retrieval logic — it
needs exactly the eviction and budgeting policy Chapter 4 already
established, plus one new question this chapter adds: *what, if anything,
gets promoted out of it into durable storage before it's evicted or
compacted away?* That promotion decision is Section 5's hot path, and it's
the actual seam between "context management" (Chapter 4) and "memory" (this
chapter).

## Key Takeaways for Section 3

Working memory is the live, in-context portion of whatever the agent is
currently reasoning about — governed by Chapter 4's token budget, not a
new mechanism. The one new question this chapter adds is what gets
promoted from working memory into durable storage before it's evicted;
everything else about managing it was already covered.

*Next: one specific, historically influential way of organizing the
boundary between what's in context and what's on disk.*

---

# 4: The OS Analogy: Core, Archival, and Recall Memory

## Starting From Plain Language

An operating system doesn't treat all memory the same way, and the analogy
maps onto agent memory closely enough that it's worth taking seriously
rather than treating as a metaphor. RAM is small, fast, and always
immediately available — but everything in it disappears without a
deliberate save. Disk is huge and durable, but you have to explicitly ask
for something before it's usable. A well-designed OS moves data between the
two deliberately, not by accident.

## The Three Tiers, From the Letta/MemGPT Lineage

This framing — introduced under the name MemGPT and continued under the
Letta project — names three tiers directly: **core memory** is the RAM
tier, always resident in context, small by necessity, and — the genuinely
novel part of the original idea — **self-editing**: the model itself can
issue an edit to its own core memory block mid-conversation, the same way
a person might jot a note to themselves without being told to. **Archival
memory** is the disk tier — a searchable, effectively unbounded store the
model queries explicitly when core memory doesn't have what's needed.
**Recall memory** sits in between: the raw conversation history itself,
kept but not necessarily in the always-visible core block, retrievable on
demand the way you'd scroll back up a long chat log rather than holding
the whole thing in your head.

```
   ┌─────────────────────────────────────────────┐
   │  CORE MEMORY (RAM)                            │
   │  small, always in-context, self-editable       │
   │  by the model mid-conversation                 │
   └───────────────┬───────────────────────────────┘
                    │ explicit query when core memory
                    │ doesn't have the answer
        ┌───────────┴────────────┐
        ▼                        ▼
┌────────────────────┐  ┌─────────────────────────┐
│ RECALL MEMORY        │  │ ARCHIVAL MEMORY          │
│ raw conversation      │  │ searchable, effectively  │
│ history, on demand    │  │ unbounded, disk-like     │
└────────────────────┘  └─────────────────────────┘
```

## Why "Self-Editing" Is the Detail Worth Keeping

It would be easy to read this as just a three-tier cache hierarchy with
different names. The detail that made the original idea more than a
renaming exercise is that the *model itself* decides what belongs in the
small, always-resident core block, and can rewrite that block as
priorities shift mid-task — not a fixed system prompt, not an external
process deciding for it, but the agent managing its own RAM the way it
would manage a real scratchpad. This is the direct ancestor of Section
5's hot-path writer: something has to decide, turn by turn, what's worth
promoting into the fast tier, and MemGPT's answer was "let the model
decide, and give it the tool to act on that decision immediately."

## Key Takeaways for Section 4

The OS analogy names three tiers — core (RAM, always resident,
self-editable by the model), archival (disk, searchable, queried on
demand), and recall (the raw conversation history, retrievable but not
always resident). The detail worth carrying forward is self-editing: the
model actively curates its own core memory rather than a fixed process
doing it for the model.

*Next: how this actually gets implemented as a running system, not just a
mental model — the pattern most 2026 production agents converged on.*

---

# 5: The 2026 Production Pattern: Hot Path / Cold Path

## Starting From Plain Language

A restaurant kitchen has two very different rhythms running at once. The
line cook plating tonight's orders works in seconds — anything that slows
that rhythm down ruins the table waiting on their food. The person updating
next season's menu, cross-referencing which dishes actually sold and which
ingredients to drop, works in days, and nobody at tonight's table is
waiting on that work to finish. Both are real, necessary work; conflating
their timelines would either slow down dinner service or rush the menu
redesign into something sloppy.

## The Two Paths, Named

The **hot path** runs synchronously, after every single turn, and does the
absolute minimum: append the raw turn to episodic memory (Section 2), maybe
extract one or two obviously-important facts with a cheap, fast check, and
nothing more. It cannot be slow — it's sitting directly in the latency path
of every response the user is waiting on. The **cold path** runs
asynchronously, on its own schedule (after N turns, at session end, or on a
background timer), and does the expensive work: consolidating a batch of
episodic entries into durable semantic facts, resolving contradictions
against what's already stored (Section 8), pruning stale entries, and
re-scoring salience across the whole memory store. Nobody is waiting on the
cold path to finish before the next turn can proceed.

```
   every turn                          every N turns / on a schedule
        │                                          │
        ▼                                          ▼
  ┌──────────────┐                        ┌──────────────────────┐
  │  HOT PATH     │                        │  COLD PATH             │
  │  synchronous  │                        │  asynchronous           │
  │  cheap, fast  │───(batched entries)──▶│  extraction, contradiction│
  │  raw append   │                        │  resolution, pruning     │
  └──────────────┘                        └──────────────────────┘
```

## Why This Split Is the Actual 2026 Consensus, Not One Vendor's Opinion

This exact two-speed shape shows up, under different names, across the
framework landscape Section 6 surveys: a background consolidation job that
runs independently of the request/response cycle is the common thread
between Letta's archival-memory promotion, Mem0's asynchronous extraction
pipeline, and LangMem's explicit "hot path tools" versus "background memory
manager" split. The convergence is not a coincidence — it's the same
verify-cheap-first instinct Chapter 6's verifier ladder already
established, applied to memory writes: do the fast, cheap thing
immediately, and defer anything that requires real judgement (Is this fact
still true? Does it contradict something else? Is it actually worth
keeping?) to a path where taking longer doesn't cost the user anything.

## Key Takeaways for Section 5

The hot path writes cheap, immediate, synchronous updates on every turn —
raw episodic entries, maybe one obvious fact. The cold path runs
asynchronously and does the expensive work — consolidation, contradiction
resolution, pruning. Nearly every production memory framework in 2026
converged on this exact two-speed shape, for the same reason Chapter 6's
verifier ladder puts cheap checks first: don't make the user wait on work
that doesn't need to happen synchronously.

*Next: which real frameworks implement this, and how to actually choose
between them.*

---

# 6: Framework Landscape: Mem0, Zep/Graphiti, Letta, LangMem, DIY

## The Frameworks, by What They Actually Optimize For

**Mem0** is the most widely deployed drop-in semantic-memory layer — a
managed service (with an open-source core) optimized for fast adoption and
personalization: hand it conversation turns, it extracts and stores facts,
you query it back. Its graph-relationship features sit behind a paid tier,
which matters if relationship-shaped queries (Chapter 10's subject) are
central to your use case. **Zep**, built on the **Graphiti** engine, takes
a structurally different approach: a genuine **temporal knowledge graph**,
where facts carry validity windows (a fact can be true from one date until
superseded on another, Section 8's problem solved architecturally rather
than by overwriting) and provenance (which conversation a fact came from).
It's the strongest open-source choice specifically for *temporal* queries —
"what did the user believe last quarter, versus now" — at real
implementation cost compared to a flat key-value store. **Letta**
(the continuation of the MemGPT project, Section 4) is the reference
implementation of the OS-tiered, self-editing approach, and is the natural
choice when you want that specific model — the agent actively curating its
own core memory — rather than an external process making all the
promotion decisions. **LangMem** is the natural choice specifically inside
a LangGraph-based system (Chapter 11), because it integrates directly with
LangGraph's own storage layer (`BaseStore`) and ships the hot-path/
background-manager split (Section 5) as first-class primitives rather than
something you wire up yourself. **DIY on Postgres** — a plain relational
table plus `pgvector` for the semantic-similarity piece — remains a fully
legitimate option, and is often the right one when your memory needs are
genuinely simple (Section 7's warning against reaching for a vector index
when a key-value row would do applies here directly).

```
   Query shape you actually have           Framework to reach for
   ──────────────────────────────          ─────────────────────────
   "just remember facts, fast to adopt"  →  Mem0
   "when did this become true / change?" →  Zep / Graphiti
   "let the model manage its own memory" →  Letta
   "I'm already all-in on LangGraph"     →  LangMem
   "my needs are genuinely simple"       →  DIY on Postgres (+pgvector)
```

*(`[DIAGRAM]` comparison — the table above is the decision surface; none of
these is "best" in the abstract, each optimizes a different axis, and
picking on hype rather than on which axis matches your actual query shape
is Section 6's whole warning.)*

## Selection Criteria, Not Hype

The honest selection process asks four questions in order: does the task
need temporal/relationship reasoning (Zep/Graphiti) or is flat semantic
recall enough (Mem0, DIY)? Does the model need to actively self-edit its
own memory mid-task (Letta) or is an external consolidation process fine
(any of the others)? Is the rest of the stack already LangGraph-based
(LangMem) or not (any of the others, with roughly equal integration cost)?
And — the question every one of these frameworks' marketing pages
underweights — is the actual memory need small enough that a Postgres
table and a cron job would have solved it in an afternoon, with none of the
operational surface area a dedicated memory service adds?

## Key Takeaways for Section 6

Five real options, each optimizing a different axis: Mem0 for fast,
managed semantic recall; Zep/Graphiti for temporal and relationship
queries; Letta for the self-editing OS model; LangMem for LangGraph-native
stacks; DIY on Postgres when the actual need is simple. Choose by matching
your query shape to the framework's actual strength, not by which one has
the most attention this quarter.

*Next: retrieval, specifically — and the several ways it's a genuinely
different problem from document RAG, not a smaller version of the same
problem.*

---

# 7: Retrieval for Memory Is Not RAG for Documents

## Starting From Plain Language

Searching a library for a book on a topic and asking a close friend "what
did I tell you about my sister last month" are both "retrieval," but they
are not the same task. The library doesn't care when the book was
published relative to now, doesn't need to reconcile two books that
disagree with each other, and has no idea who "I" refers to. A friend's
memory retrieval is shaped by all three of those things, constantly,
without being asked.

## Where the Two Problems Genuinely Diverge

**Recency** matters for memory in a way it structurally doesn't for a
static document corpus: a fact from an hour ago usually outranks a
similar-looking fact from six months ago, even at equal semantic
similarity, because people's stated preferences and circumstances change —
document RAG has no equivalent notion that an older, still-published
document is *less true* than a newer one on the same topic. **Salience**
— how important a memory is, independent of how well it matches the
current query — has no clean analogue in document retrieval either; a
document's relevance is usually assumed proportional to its similarity
score, while a memory can be highly similar to the query and still be a
low-value thing to surface (a one-off passing comment) versus a memory
that's less textually similar but was flagged as important when it was
written. **Contradiction handling** is close to nonexistent in document
RAG (two documents disagreeing is just... two documents; you return both
and let the reader sort it out) but is central to memory (Section 8):
if a stored memory says "the user prefers tabs" and a newer one says
"the user prefers spaces," returning both with no resolution is a
retrieval failure, not a neutral outcome. **Identity and entity
resolution** — realizing that "my manager," "Priya," and "the person I
mentioned on Tuesday" all refer to the same entity — barely exists as a
concern in document search, where the query terms are what they are, but
is routine and load-bearing in memory retrieval, because people refer to
the same thing multiple inconsistent ways across a long relationship with
an agent.

## Why This Matters Practically

Bolting a document-RAG pipeline directly onto memory storage — embed
everything, retrieve by cosine similarity, done — will pass a quick demo
and then quietly return stale, contradicted, or low-value memories in
production, because none of the four properties above are handled by
similarity search alone. Section 12's salience formula is the concrete
mechanism this section has been building toward: retrieval score has to be
a function of *more than* similarity, specifically because memory's
retrieval problem is a strict superset of document RAG's, not a special
case of it.

## Key Takeaways for Section 7

Memory retrieval differs from document RAG on four axes that similarity
search alone doesn't address: recency (newer often outranks older at equal
similarity), salience (importance independent of query match), contradiction
handling (resolving disagreement, not just returning both), and identity
resolution (recognizing the same entity referred to inconsistently).
Treating memory retrieval as "RAG, but for personal facts" misses all four.

*Next: memories don't just need to be found correctly — some of them need
to stop being found at all.*

---

# 8: Forgetting, Staleness, and Conflict

## Starting From Plain Language

A person who remembers every single thing anyone has ever told them,
including things that stopped being true years ago, with no ability to
update or discard any of it, is not admirable — they're exhausting and
frequently wrong, confidently repeating something that changed long ago.
Forgetting isn't a limitation of memory; it's a required feature of a
memory system that stays useful over time.

## The Three Mechanisms

**TTLs (time-to-live)** expire a memory automatically after a fixed window
— appropriate for facts with a known natural shelf life ("the user's
current sprint deadline" has an obvious expiration; "the user's name" does
not, and should never carry a TTL). **Decay** is TTLs' softer cousin: a
memory's *salience* score (Section 12) fades continuously with age rather
than cutting off sharply, so an old memory doesn't vanish outright but
becomes progressively less likely to surface unless something re-confirms
it. **Supersession** is the mechanism specifically for Section 2's semantic
scope: when a new fact arrives with the same subject and predicate as an
existing one ("prefers: Python" replaced by "prefers: Rust"), the old
value is marked superseded — not deleted outright, since the *history* of
what the user used to prefer can itself be a useful episodic fact, but
excluded from active retrieval so it stops being served as current truth.

```
   new fact arrives: (user, prefers_language, "Rust")
                    │
                    ▼
   existing fact: (user, prefers_language, "Python") ── same (subject, predicate)?
                    │ yes
                    ▼
   mark existing fact SUPERSEDED (not deleted)
   insert new fact as ACTIVE
```

## Why a Memory System With No Deletion Path Becomes a Liability

This is the sharpest way to state Section 8's overall point: a memory
store that only ever grows is not more capable than one that prunes and
supersedes — it's *worse*, because every retrieval query now has to sift
through an ever-larger pile of potentially-stale, potentially-contradicted
facts, and Section 7 already established that similarity alone can't tell
current truth from expired truth. Unbounded accumulation isn't a scaling
problem you solve later with a bigger database; it's a *correctness*
problem from the first contradicted fact onward. A memory system's
deletion (or supersession) path is not an optional cleanup feature — it's
as load-bearing as the write path itself.

## Key Takeaways for Section 8

TTLs handle facts with a known, fixed shelf life. Decay softens a memory's
salience continuously rather than cutting it off. Supersession replaces
(without necessarily deleting) a fact when a newer, contradicting one
arrives for the same subject and predicate. A memory system that never
deletes or supersedes anything degrades into a liability, not an asset,
because every future retrieval has to sort current truth from accumulated
staleness with no help from the store itself.

*Next: how do you actually know if any of this is working?*

---

# 9: Memory Evaluation

## Starting From Plain Language

You cannot tell, from a single cherry-picked conversation, whether a
memory system genuinely works — the same way you can't judge a search
engine's quality from one query that happened to go well. Evaluating
memory needs a benchmark shaped like the actual failure mode: long,
multi-session conversations, with specific questions whose answers require
recalling something said sessions ago, sometimes correctly, sometimes
across several sessions at once, sometimes not at all (a well-designed
memory system should recognize when it *doesn't* know something rather
than confabulating an answer).

## LoCoMo, as a Concrete Reference Point

**LoCoMo** (Long-term Conversational Memory) is the standard reference
benchmark for exactly this shape of evaluation: ten long conversations,
each spanning 19 to 32 separate sessions (on the order of 9,000 tokens per
full dialogue), generating roughly 2,000 question-answer pairs across five
categories — **single-hop** (retrieve one specific fact), **multi-hop**
(synthesize information that only becomes an answer once you combine facts
from multiple separate sessions), **temporal** (reasoning about *when*
something happened or changed, directly testing Section 8's supersession
handling), **open-domain** (a longer, more contextual answer rather than a
single fact), and **adversarial** (questions the system should correctly
refuse to answer, because the conversation genuinely never covered it —
testing whether the system confabulates rather than admitting it doesn't
know). The category breakdown itself is the useful part to internalize,
independent of any specific framework's current leaderboard position: a
memory system can score well on single-hop recall while failing badly on
temporal and adversarial categories, and those are two entirely different
production risks (giving stale answers, and confidently inventing facts).

## Building Your Own Memory Regression Set

A standard benchmark measures general capability; it does not tell you
whether *your* agent's memory works for *your* actual usage pattern. The
practical complement — directly analogous to Chapter 14's eventual
regression harness, applied narrowly to memory — is a small, hand-built
set of question/expected-answer pairs drawn from your own real usage:
does the system correctly recall a preference stated three sessions ago;
does it correctly report "I don't know" for something never mentioned;
does it correctly prefer the newer of two contradicting facts. Ten
well-chosen cases, re-run after every change to the memory pipeline, catch
regressions a general benchmark has no way to know to check for.

## Key Takeaways for Section 9

LoCoMo's five question categories — single-hop, multi-hop, temporal,
open-domain, adversarial — name five genuinely different memory failure
modes, and a system can pass one while failing another. A small,
hand-built regression set drawn from your own actual usage catches the
failures a general benchmark has no way to anticipate, the same role
Chapter 14's regression suite will later play for the harness as a whole.

*Next: memory writes don't only correct facts — they can, in a sense,
correct the agent's own behavior over time.*

---

# 10: Continual Learning Framing

## Starting From Plain Language

A junior engineer who gets corrected once on a coding-style mistake and
then simply never makes that mistake again has *learned* something, in the
ordinary sense of the word, without any of their underlying training
having changed — nobody retrained their brain, they just updated a
personal rule and kept it. Procedural memory (Section 2) is exactly this
kind of learning, applied to an agent.

## Procedural Memory as the Agent Improving Its Own Instructions

When an agent writes "always run tests before proposing a merge in this
repo" to its own procedural memory after being corrected once, and that
rule genuinely changes its behavior on every future run in that repo
without anyone retraining anything, this is functionally a (very narrow,
very shallow) form of continual learning — the system's *behavior* has
measurably improved from experience, persisted across sessions, with no
change to model weights at all.

## Where the Line to "Training" Actually Sits

It is worth being precise about where this framing stops applying, because
the phrase "continual learning" invites overclaiming. What's happening
here is closer to **configuration that accumulates** than to genuine
learning in the machine-learning sense: the underlying model's weights are
completely unchanged; only a piece of text (an instruction, a preference, a
rule) that gets prepended to future context has changed. This has real,
practical value — it's cheap, immediately effective, fully inspectable, and
trivially reversible — but it is bounded by whatever the base model can
already do when given that instruction. A model that genuinely cannot
perform a task no procedural-memory note will fix that; contrast this with
Chapter 18's actual agentic RL, where the model's weights themselves change
based on accumulated experience — a fundamentally different mechanism,
capable of things text-based procedural memory structurally cannot reach.

## Key Takeaways for Section 10

Procedural memory functions as a shallow, text-based form of continual
learning: behavior improves from experience, persisted across sessions,
with zero change to model weights. That's real and valuable, but it's
accumulating configuration, not training — bounded by what the base model
can already do given the right instruction. Chapter 18's agentic RL is the
genuinely different mechanism, where weights themselves change.

*Next: everything durable is, by definition, something an attacker can
also write to.*

---

# 11: Memory as an Attack Surface

## Starting From Plain Language

A shared whiteboard that everyone trusts and nobody ever double-checks is
exactly the kind of surface a bad actor targets, precisely because
everyone downstream treats what's written on it as already-vetted truth.
Anything an agent later retrieves as "memory" and trusts without
re-verification has become exactly this kind of whiteboard.

## Poisoned Memories, and Why They're Worse Than a Single Bad Turn

A single malicious instruction hidden in one document an agent reads is
bad, but its damage is typically bounded to that one session. A malicious
or manipulated fact written into *durable memory* — "the user has
pre-approved all wire transfers over $10,000," planted by a prompt
injection in a document the agent processed once, months ago — persists
and gets retrieved as trusted context in every future session, long after
the original attack vector is gone and forgotten. This is Chapter 1's
**lethal trifecta** (private data access, untrusted content, an
exfiltration vector) with a fourth property layered on top: **persistence
across sessions**, which turns a one-time exposure into a standing
liability nobody is actively looking for anymore, because the attack
already happened, succeeded, and is now just sitting quietly in storage
waiting to be retrieved.

## Why This Chapter Only Names It

The actual defenses — provenance tracking (which source wrote this
memory, and was that source trusted at write time), write-access
permissioning on the memory store itself, and treating memory writes as
requiring the same scrutiny as any other side-effecting action — belong to
Chapter 16's full security treatment, not here. This section's job is
narrower: making sure the risk is visible at the moment memory is being
designed, rather than discovered later as an incident. Every mechanism
this chapter built — the hot path's fast writes (Section 5), the
frameworks' automatic extraction pipelines (Section 6) — is a place an
attacker's content can enter the durable store just as easily as a genuine
user fact can, unless something explicitly checks.

## Key Takeaways for Section 11

A poisoned memory persists across sessions in a way a single bad turn
doesn't, turning a one-time content-injection attack into a standing
liability that outlives the original exposure. This is Chapter 1's lethal
trifecta with persistence added on top. Chapter 16 covers the actual
defenses (provenance, write-access permissioning); this section's job is
making sure the risk is designed around, not discovered after the fact.

*Next: putting real numbers under the retrieval-scoring function Section
7 promised.*

---

# 12: Dry-Run: Salience Scoring, Ranked by Hand

## The Formula, Every Symbol Explained

$$s = \alpha \cdot \text{sim} + \beta \cdot e^{-\lambda \Delta t} + \gamma \cdot \text{importance}$$

$s$ is the final salience score a memory receives for a given query — the
number retrieval actually ranks by, not similarity alone. $\text{sim}$ is
the semantic similarity between the query and the memory's content (a
cosine similarity, conventionally in $[0, 1]$ for normalized embeddings).
$\Delta t$ is the memory's age in days at query time. $\lambda$ (lambda) is
the **decay rate** — how fast a memory's recency contribution fades with
age; a larger $\lambda$ means faster decay, a smaller $\lambda$ means
recency barely matters. $e^{-\lambda \Delta t}$ is the exponential decay
term itself: it equals $1$ at $\Delta t = 0$ (a brand-new memory gets the
full recency bonus) and decays toward $0$ as $\Delta t$ grows, at a rate
set by $\lambda$. $\text{importance}$ is a stored, query-independent score
for how significant this memory was judged to be when it was written
(Section 5's cold path is typically what assigns it). $\alpha$, $\beta$,
$\gamma$ (alpha, beta, gamma) are the weights balancing the three terms'
relative influence, conventionally chosen to sum to $1$ so $s$ stays in a
comparable range across memories.

## Five Candidate Memories

| ID | Content | $\text{sim}$ | $\Delta t$ (days) | $\text{importance}$ |
|---|---|---|---|---|
| M1 | "User prefers Python over JavaScript" | 0.90 | 2 | 0.6 |
| M2 | "User's manager is named Priya" | 0.40 | 30 | 0.9 |
| M3 | "User mentioned the deadline is Friday" | 0.70 | 1 | 0.8 |
| M4 | "User likes coffee, not tea" | 0.30 | 60 | 0.2 |
| M5 | "User's project uses PostgreSQL" | 0.85 | 15 | 0.7 |

Weights fixed at $\alpha = 0.5$, $\beta = 0.3$, $\gamma = 0.2$ throughout
(summing to 1).

## Ranking at a Slow Decay Rate: $\lambda = 0.05$

$$e^{-0.05 \Delta t}: \quad \text{M1}=e^{-0.10}=0.905 \quad \text{M2}=e^{-1.50}=0.223 \quad \text{M3}=e^{-0.05}=0.951 \quad \text{M4}=e^{-3.00}=0.050 \quad \text{M5}=e^{-0.75}=0.472$$

```
M1: 0.5(0.90) + 0.3(0.905) + 0.2(0.6) = 0.450 + 0.2715 + 0.120 = 0.8415
M2: 0.5(0.40) + 0.3(0.223) + 0.2(0.9) = 0.200 + 0.0669 + 0.180 = 0.4469
M3: 0.5(0.70) + 0.3(0.951) + 0.2(0.8) = 0.350 + 0.2853 + 0.160 = 0.7953
M4: 0.5(0.30) + 0.3(0.050) + 0.2(0.2) = 0.150 + 0.0150 + 0.040 = 0.2050
M5: 0.5(0.85) + 0.3(0.472) + 0.2(0.7) = 0.425 + 0.1416 + 0.140 = 0.7066
```

**Ranking ($\lambda = 0.05$): M1 (0.8415) > M3 (0.7953) > M5 (0.7066) > M2
(0.4469) > M4 (0.2050).** At slow decay, similarity and importance
dominate; M1's very high similarity keeps it on top even though M3 is
almost twice as recent.

## Ranking at a Fast Decay Rate: $\lambda = 1.0$

$$e^{-1.0 \Delta t}: \quad \text{M1}=e^{-2}=0.135 \quad \text{M2}=e^{-30}\approx 0 \quad \text{M3}=e^{-1}=0.368 \quad \text{M4}=e^{-60}\approx 0 \quad \text{M5}=e^{-15}\approx 0$$

```
M1: 0.5(0.90) + 0.3(0.135) + 0.2(0.6) = 0.450 + 0.0405 + 0.120 = 0.6105
M3: 0.5(0.70) + 0.3(0.368) + 0.2(0.8) = 0.350 + 0.1104 + 0.160 = 0.6204
M5: 0.5(0.85) + 0.3(0.000) + 0.2(0.7) = 0.425 + 0.0000 + 0.140 = 0.5650
M2: 0.5(0.40) + 0.3(0.000) + 0.2(0.9) = 0.200 + 0.0000 + 0.180 = 0.3800
M4: 0.5(0.30) + 0.3(0.000) + 0.2(0.2) = 0.150 + 0.0000 + 0.040 = 0.1900
```

**Ranking ($\lambda = 1.0$): M3 (0.6204) > M1 (0.6105) > M5 (0.5650) > M2
(0.3800) > M4 (0.1900).** The top two positions have **swapped**: M3's
extra day of freshness now outweighs M1's similarity edge, because at this
decay rate anything more than a day or two old contributes almost nothing
from the recency term at all.

## Why This Reordering Is the Entire Point

Nothing about the memories themselves changed between the two rankings —
not their content, not their similarity to the query, not their stored
importance. The only thing that changed was $\lambda$, a single tuning
knob, and it was enough to flip which memory a retriever would have
surfaced first. This is the concrete, numeric version of Section 7's
abstract claim that memory retrieval is not document RAG: a document
retrieval system tuned purely on similarity has no equivalent knob that
reorders results this way, because it has no recency term to tune in the
first place.

## Key Takeaways for Section 12

The salience formula blends similarity, exponential recency decay, and
stored importance under three tunable weights. On five concrete memories,
a slow decay rate ($\lambda=0.05$) ranks a highly-similar-but-two-days-old
memory first; a fast decay rate ($\lambda=1.0$) flips the top two
positions in favor of a slightly-less-similar memory that's a full day
fresher. The reordering demonstrates, numerically, that $\lambda$ is a real
design decision with real consequences for what an agent actually recalls
— not a cosmetic parameter.

*Next: closing the loop on the whole chapter.*

---

# 13: Key Takeaways + Master Decision Table

The single mental model for this chapter: **memory is a policy, not a
product** — a set of deliberate decisions about what gets written, in
which of three scopes, how it's retrieved, how it decays or gets
superseded, and how it's kept safe from poisoning, sitting on top of
whatever storage technology happens to hold the bytes.

| I want to know... | Reach for | Key fact |
|---|---|---|
| What's the actual difference between context, memory, and storage | Section 1 | Context is this run's message list; storage is durable bytes with no policy; memory is the deliberate policy connecting them |
| Which "kind" of memory a given fact is | Section 2 | Episodic (what happened), semantic (what's true), procedural (how to behave) — each needs a different store shape and update rule |
| Whether working memory needs its own new mechanism | Section 3 | No — it's Chapter 4's token budget, applied to the in-context scratchpad; the only new question is what gets promoted out of it |
| A mental model for tiered memory | Section 4 | Core (RAM, always resident, self-editable by the model), archival (disk, queried on demand), recall (raw history, on demand) -- the Letta/MemGPT lineage |
| How real systems actually wire memory into the loop | Section 5 | Hot path: synchronous, cheap, every turn. Cold path: asynchronous, expensive, consolidation and contradiction resolution |
| Which framework to reach for | Section 6 | Match your query shape: Mem0 (fast semantic), Zep/Graphiti (temporal/relationship), Letta (self-editing OS model), LangMem (LangGraph-native), DIY Postgres (genuinely simple needs) |
| Why memory retrieval isn't just RAG | Section 7 | Four axes document RAG doesn't need: recency, salience, contradiction handling, identity resolution |
| How memories get forgotten on purpose | Section 8 | TTLs (fixed shelf life), decay (soft salience fade), supersession (newer fact replaces older for the same subject/predicate) |
| How to know if memory is actually working | Section 9 | LoCoMo's five categories (single-hop, multi-hop, temporal, open-domain, adversarial) name five distinct failure modes; build your own small regression set on top |
| Whether procedural memory is "real" learning | Section 10 | It's accumulating configuration, not weight change — real and valuable, but bounded by what the base model can already do; Chapter 18's RL is the genuinely different mechanism |
| Why memory needs its own security thinking | Section 11 | A poisoned memory persists across sessions, turning a one-time exposure into a standing liability -- Chapter 1's lethal trifecta plus persistence |
| How to compute and reorder salience by hand | Section 12 | $s = \alpha \cdot \text{sim} + \beta \cdot e^{-\lambda \Delta t} + \gamma \cdot \text{importance}$ -- changing $\lambda$ alone can flip which memory ranks first |

**Connection forward:** Chapter 10 picks up exactly where Section 7 and
Section 6's Zep/Graphiti entry left off — once memory needs to represent
*relationships between facts*, not just facts in isolation, a flat
key-value or vector store stops being enough, and the question becomes
when a graph actually earns the added complexity it brings.
