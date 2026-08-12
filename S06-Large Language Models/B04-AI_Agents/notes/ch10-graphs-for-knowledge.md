# Chapter 10: Graphs for Knowledge — Agentic RAG, GraphRAG, Temporal KGs

## Table of Contents

0. [Prerequisite: Graph Theory Basics](#0-prerequisite-graph-theory-basics)
1. [The Failure Mode Vector Search Cannot Fix](#1-the-failure-mode-vector-search-cannot-fix)
2. [Knowledge-Graph Basics for Agents](#2-knowledge-graph-basics-for-agents)
3. [GraphRAG: Communities, Hierarchies, and the Cost of Indexing](#3-graphrag-communities-hierarchies-and-the-cost-of-indexing)
4. [Temporal Knowledge Graphs](#4-temporal-knowledge-graphs)
5. [Agentic RAG: Retrieval as a Tool the Loop Calls Repeatedly](#5-agentic-rag-retrieval-as-a-tool-the-loop-calls-repeatedly)
6. [Hybrid Architectures](#6-hybrid-architectures)
7. [Graph Traversal as Tool Design](#7-graph-traversal-as-tool-design)
8. [Building the Graph Incrementally](#8-building-the-graph-incrementally)
9. [Evaluating Graph Retrieval](#9-evaluating-graph-retrieval)
10. [Choosing Not to Use a Graph](#10-choosing-not-to-use-a-graph)
11. [Dry-Run: A 6-Node Graph, a 2-Hop Answer, and PageRank by Hand](#11-dry-run-a-6-node-graph-a-2-hop-answer-and-pagerank-by-hand)
12. [Key Takeaways + Master Decision Table](#12-key-takeaways--master-decision-table)

---

# 0: Prerequisite: Graph Theory Basics

## Why This Section Exists

Everything from Section 1 onward assumes you can read a sentence like "a
directed edge from ProjectAtlas to TeamPlatform" and immediately picture
what that means, and that terms like *node*, *hop*, *traversal*, and
*degree* don't slow you down. If graph theory is new territory, this
section is the on-ramp — plain-language first, one small concrete example
carried through every concept, no prior math background assumed beyond
counting.

## The Core Picture: Dots and Arrows

A graph is nothing more than **things** (dots) and **connections between
things** (lines or arrows). That's the entire concept before any
vocabulary gets attached to it. The formal names just give you a precise
way to talk about which dots, which connections, and in which direction.

```
        (Alice) ────────── (Bob)

   Two "things" (nodes), one "connection" (edge) between them.
```

## Nodes and Edges

A **node** (also called a **vertex** — the two words mean exactly the same
thing, and you'll see both in the wild) is one "thing" in the graph — a
person, a project, a document, a city, anything with its own identity that
other things can point at. An **edge** is a connection between two nodes.
That's the entire vocabulary needed to describe the picture above: two
nodes, `Alice` and `Bob`, joined by one edge.

## Directed vs Undirected: Does the Arrow Have a Direction?

This is the single most important distinction to get comfortable with,
because this whole chapter lives almost entirely on the directed side of
it. An **undirected** edge is symmetric — "Alice and Bob are friends" is
true in both directions at once; there's no meaningful sense in which the
friendship "points" one way. A **directed** edge has a direction, drawn as
an arrow, and the direction *changes the meaning* — "Alice works on
ProjectAtlas" is not the same statement as "ProjectAtlas works on Alice"
(which doesn't even make sense). Every relationship this chapter cares
about — `works_on`, `owned_by`, `manages` — is directed, because *who did
what to whom* is exactly the information a flat, undirected connection
would throw away.

```
   UNDIRECTED (symmetric)              DIRECTED (has a direction)

   Alice ────friends──── Bob           Alice ──works_on──▶ ProjectAtlas

   "Alice and Bob are friends"          "Alice works on ProjectAtlas" --
   reads the same either direction      reversed, this would claim
                                        something completely different
                                        (and false)
```

## A Path, and What "Hop" Means

A **path** is a sequence of edges connecting one node to another, following
the arrows in their given direction. A **hop** is just one single edge
traversed along that path — "a 2-hop path" means you crossed exactly two
edges to get from the start to the end. Take the small graph this chapter
uses throughout:

```
   Alice ──works_on──▶ ProjectAtlas ──owned_by──▶ TeamPlatform
```

Going from `Alice` to `ProjectAtlas` is a **1-hop** path — one edge,
`works_on`. Going from `Alice` all the way to `TeamPlatform` is a **2-hop**
path — first the `works_on` edge, then the `owned_by` edge, two edges
total. This is the exact mechanism behind every "multi-hop question" this
chapter discusses: the answer isn't sitting at the end of one edge, it's
sitting at the end of a *chain* of edges, and finding it means walking that
chain step by step rather than looking at any single connection in
isolation.

## Neighbors, Degree, and In/Out-Degree

A node's **neighbors** are the other nodes directly connected to it by one
edge — no chain, just the immediate, one-hop connections. In the graph
above, `ProjectAtlas`'s only neighbor (following the arrow outward) is
`TeamPlatform`. A node's **degree** is simply *how many* edges touch it.
Once edges have direction, degree splits into two separate counts: **out-
degree** is how many edges point *away* from a node (how many things it
"does" or "has"), and **in-degree** is how many edges point *into* it (how
many things "happen to it" or reference it). `ProjectAtlas` has an
out-degree of 1 (its one `owned_by` edge, pointing to `TeamPlatform`) and
an in-degree of 2 in the fuller version of this chapter's graph (both
`Alice` and `Bob` have `works_on` edges pointing *into* it). This
distinction matters concretely in Section 11's PageRank dry-run: a node's
importance is computed by looking at what flows *into* it (in-links),
weighted by how thinly each source spreads its own importance across its
*out*-degree.

## Traversal: Actually Walking the Graph

**Traversal** is the general term for the process of moving through a
graph, edge by edge, to find something — a specific node, a path between
two nodes, or every node reachable from a starting point. Two traversal
strategies come up constantly, and it's worth knowing the difference by
name even though this chapter's own `find_path` tool only needs one of
them:

**Breadth-First Search (BFS)** explores *outward in rings* — visit every
neighbor 1 hop away first, then every node 2 hops away, then 3, and so on,
guaranteeing that the *first* time you reach a target node, you've found a
**shortest** path to it (fewest hops). **Depth-First Search (DFS)** instead
commits to one path and follows it as far as it goes before backing up and
trying a different branch — it will eventually find a path too, but not
necessarily the shortest one, and it explores in a completely different
order. This chapter's `find_path` tool (Section 7) uses BFS specifically
*because* "which team owns the project Alice works on" wants the most
direct connection, not just *some* connection buried behind a longer,
more roundabout chain.

```
   BFS explores ring by ring:              DFS commits to one branch first:

        (start)                                  (start)
        ╱   │   ╲                                   │
     ring1 ring1 ring1   <- visit all               ▼
       │     │     │        of these              branch A
     ring2 ring2 ring2   <- before any               │
                              of these                ▼
                              (further out)         deeper...
                                                      │
                                                      ▼
                                              (only THEN backtrack
                                               to try branch B)
```

## Adjacency: How a Graph Actually Gets Stored

Practically, a graph is almost never stored as a picture — it's stored as
a lookup structure. An **adjacency list** stores, for each node, the list
of edges going out from it — exactly the shape this chapter's own
`graph[subject] = [(predicate, object), ...]` dictionary uses. This is the
overwhelmingly common choice for real, sparse graphs (most nodes connect
to only a few others), because it only stores the edges that actually
exist. The alternative, an **adjacency matrix** — a full grid with a row
and column for every node, marking a 1 or 0 for whether an edge exists
between each pair — is simple to reason about mathematically (and is
exactly the structure PageRank's underlying linear algebra is usually
described in terms of) but wastes enormous amounts of space on a large,
sparse, real-world graph, where the overwhelming majority of node pairs
have no direct edge at all.

## A Tiny Worked Example, Start to Finish

Take a 4-node graph: `Alice → ProjectAtlas`, `Bob → ProjectAtlas`,
`ProjectAtlas → TeamPlatform`.

```
   Alice ──▶ ProjectAtlas ──▶ TeamPlatform
              ▲
   Bob ───────┘
```

Reading off every term just introduced, on this one example: **Nodes** —
`Alice`, `Bob`, `ProjectAtlas`, `TeamPlatform` (four of them). **Edges** —
three directed edges, `Alice→ProjectAtlas`, `Bob→ProjectAtlas`,
`ProjectAtlas→TeamPlatform`. **`ProjectAtlas`'s neighbors** (outward) —
just `TeamPlatform`; (inward) — `Alice` and `Bob`. **`ProjectAtlas`'s
out-degree** — 1. **`ProjectAtlas`'s in-degree** — 2. **A path from `Alice`
to `TeamPlatform`** — `Alice→ProjectAtlas→TeamPlatform`, a **2-hop** path.
**As an adjacency list** —
`{"Alice": [("works_on", "ProjectAtlas")], "Bob": [("works_on", "ProjectAtlas")], "ProjectAtlas": [("owned_by", "TeamPlatform")]}`
(note `TeamPlatform` has no entry at all — it has no *outgoing* edges,
only incoming ones, which is exactly the shape a lookup-by-subject
adjacency list naturally produces).

## Key Takeaways for Section 0

A graph is nodes (things) and edges (connections). Directed edges have a
meaningful direction — this chapter's relationships (`works_on`,
`owned_by`, `manages`) are all directed. A path is a chain of edges; a hop
is one edge crossed along that chain — a "2-hop question" needs exactly
two edges combined to answer. Degree counts how many edges touch a node,
split into out-degree (edges leaving) and in-degree (edges arriving) once
direction is involved. BFS explores ring-by-ring and finds the shortest
path first, which is why this chapter's `find_path` tool uses it. An
adjacency list — a dictionary from each node to its outgoing edges — is
how this chapter's code actually stores every graph you'll build.

*Next: with this vocabulary in hand, the actual chapter starts — the
specific failure mode in vector search that graphs exist to fix.*

---

# 1: The Failure Mode Vector Search Cannot Fix

## Starting From Plain Language

Ask a librarian "which book is most similar in topic to this one" and a
similarity search does exactly what's asked. Ask the same librarian "which
of our members have borrowed a book by an author who once co-wrote
something with the author of *this* book" and similarity search cannot
help at all — not because it's tuned badly, but because the answer isn't a
property of any single document's *content*. It's a property of a
**relationship** connecting several documents, and a relationship is
structurally invisible to a method that only ever asks "how similar is
this chunk's embedding to the query's embedding."

## Three Question Shapes, Named Precisely

**Multi-hop questions** require chaining facts across documents that never
co-occur in the same chunk — "which team owns the project that Alice works
on" needs one fact linking Alice to a project and a second, entirely
separate fact linking that project to a team; no single passage contains
both, so no embedding similarity score can be high for the right answer
and low for wrong ones, because the right answer was never *written down
as one continuous piece of text* anywhere in the corpus. **Aggregation
questions** — "which customers are affected by the outage described in
this ticket" — require enumerating every entity connected to a given node
by a specific relationship, which is a graph traversal by definition, not
a ranking of documents by relevance. **Global questions** — "what are the
recurring themes across this entire document set" — require a summary of
*structure across the whole corpus*, not a ranking of the top-k most
relevant individual passages, because no single passage or fixed-size
group of passages contains "the whole dataset's themes" as content to be
retrieved.

```
                    "Which team owns the project Alice works on?"

   VECTOR SEARCH SEES:                    THE ANSWER ACTUALLY LIVES IN:

   [Doc: Alice's bio]     sim=0.4         Alice --works_on--> ProjectAtlas
   [Doc: TeamPlatform     sim=0.3               (fact 1, one document)
    charter]                                            │
   [Doc: ProjectAtlas     sim=0.6                        ▼
    overview]                              ProjectAtlas --owned_by--> TeamPlatform
                                                   (fact 2, a DIFFERENT document)
   Highest-similarity doc alone
   never contains the answer --
   it requires COMBINING two
   separately-written facts.
```

*(`[DIAGRAM]` — this is the picture the rest of the chapter exists to fix:
three question shapes similarity ranking cannot answer *by construction*,
independent of how good the embedding model or the chunking strategy is.)*

## Key Takeaways for Section 1

Vector search ranks documents by content similarity; it has no mechanism
for combining two separately-written facts into a chained answer
(multi-hop), enumerating every entity connected by a relationship
(aggregation), or summarizing structure across an entire corpus (global
questions). These aren't tuning problems — no amount of better embeddings
or chunking fixes a category mismatch between what similarity search
computes and what the question actually needs.

*Next: the structure that makes these three question shapes answerable in
the first place.*

---

# 2: Knowledge-Graph Basics for Agents

## Starting From Plain Language

A knowledge graph is nothing more exotic than a very disciplined way of
writing down "X relates to Y, specifically like this" — the same shape as
a family tree, or an org chart, made explicit and machine-traversable
instead of implicit in prose.

## Entities, Relations, Properties

An **entity** is a node — a person, a project, a document, a concept —
with a stable identity that other facts can point at. A **relation** is a
directed, typed edge between two entities — `works_on`, `owned_by`,
`manages` — and the *type* of the edge is what makes traversal meaningful
rather than just "these two things are somehow connected." A **property**
is an attribute attached to either a node or an edge — a person's start
date, a project's status, the confidence score attached to an extracted
relation — carrying detail that doesn't need its own node.

```
   (Alice)──works_on──▶(ProjectAtlas)──owned_by──▶(TeamPlatform)
     │ entity              │ entity                    │ entity
     └─ property: role="engineer"     edge property: since="2025-01"
```

## Extraction Pipelines: How the Graph Actually Gets Built

Turning unstructured text into entities and relations is itself a pipeline
with real design choices. **Schema-guided extraction** fixes the allowed
entity types and relation types in advance (`Person`, `Project`, `Team`;
`works_on`, `owned_by`, `manages`) and asks an extraction model to fit
whatever it finds into that fixed vocabulary — higher precision, easier to
query consistently, but blind to relationship types nobody anticipated.
**Open extraction** lets the model name whatever entity and relation types
it finds directly in the text, with no fixed schema constraining it —
higher recall on genuinely novel relationship types, at the cost of a
graph that can end up with a dozen near-duplicate relation names
(`works_on`, `is_working_on`, `contributes_to`) meaning the same thing,
which is exactly Section 8's entity-resolution problem one layer up.

## Key Takeaways for Section 2

A knowledge graph is entities (nodes with stable identity), relations
(typed, directed edges), and properties (attributes on either). Extraction
is schema-guided (constrained vocabulary, consistent queries, blind spots
for the unanticipated) or open (catches novel relationships, at real risk
of near-duplicate relation types needing later reconciliation).

*Next: one specific, highly influential way of turning a raw graph into
something queryable at both a local and a global level.*

---

# 3: GraphRAG: Communities, Hierarchies, and the Cost of Indexing

## Starting From Plain Language

A single sprawling graph of ten thousand entities is not, by itself,
answerable at the "what are the themes here" level any more than a giant
pile of index cards is — you need someone to have already grouped related
cards into folders, and written a one-paragraph summary of each folder,
*before* anyone asks a global question, or the question has to re-read the
entire pile from scratch every single time.

## The Pipeline

Microsoft's GraphRAG (the reference design most 2026 implementations still
trace back to) runs a fixed sequence: **documents → entity extraction →
graph construction → community detection → hierarchical summarization**.
The community-detection step uses the **Leiden algorithm**, applied
*recursively* — it finds tightly-connected clusters of entities (a
"community"), then re-applies itself *inside* each community to find
sub-communities, continuing until a cluster can no longer be meaningfully
split. This produces a hierarchy of coarseness levels (commonly labeled
C0 through C3, root to leaf) rather than one flat clustering.

```
   Level C0 (root):     [ Entire product engineering org ]
                                │
   Level C1:      [ Platform team ]      [ Growth team ]
                          │
   Level C2:   [ Checkout squad ]   [ Auth squad ]
                       │
   Level C3 (leaf):  [ Alice, Bob, ProjectAtlas, ... ]
```

## The Genuinely Load-Bearing Detail: Summaries Are Written at Index Time

The entire economic argument for GraphRAG rests on one design choice, not
on the graph structure itself: a natural-language summary of *each
community, at each level*, is generated **once, during indexing** — not
regenerated per query. A global question then retrieves a small number of
pre-written community summaries rather than re-reading the underlying
source text at query time. Measured results back this up concretely:
root-level community summaries required **roughly 97% fewer tokens** than
processing the equivalent source text directly, at query time, per query —
because the expensive summarization work already happened once, up front,
and every subsequent query reuses it.

## Local vs Global Search Modes

**Local search** starts from specific entities relevant to the query and
walks outward a limited number of hops, pulling in their immediate
neighborhood and any directly-relevant community summaries — well suited
to Section 1's multi-hop and aggregation shapes, where the question names
or implies specific entities to start from. **Global search** starts from
the *top* of the community hierarchy and works with the pre-written,
high-level summaries directly, optionally descending a level when a
summary alone isn't specific enough — the only mode capable of answering
Section 1's "what are the themes" shape at all, since no single local
neighborhood contains a corpus-wide theme.

## Honest Cost Accounting for Index Construction

None of the query-time savings above are free — they're paid for entirely
upfront, at indexing time, and that cost is real: extraction across the
whole corpus, graph construction, hierarchical community detection, and a
summarization pass *at every level of the hierarchy*, all before a single
query is answered. This is the central tradeoff Section 10 returns to: a
GraphRAG index pays a real, sometimes substantial, one-time cost precisely
to make every future global or multi-hop query cheap — a bet that only
pays off if the corpus is queried enough times, in ways vector search
genuinely can't serve, to amortize that upfront cost.

## Key Takeaways for Section 3

GraphRAG's pipeline is extraction → graph construction → recursive Leiden
community detection → hierarchical summarization written once at index
time. Local search walks outward from specific entities; global search
works top-down from pre-written community summaries and is the only mode
that can answer corpus-wide theme questions at all. The ~97% token
reduction at the root level is real, but it's purchased entirely by
upfront indexing cost — Section 10 covers when that trade is actually
worth making.

*Next: a graph that only ever grows and never revises what it believed in
the past is a static snapshot, not a memory.*

---

# 4: Temporal Knowledge Graphs

## Starting From Plain Language

A court record doesn't erase a fact when new evidence contradicts it — it
notes when the earlier belief was recorded, and when it was superseded,
preserving both. A knowledge graph that wants to serve as genuine memory
(Chapter 9) needs the same discipline: not just "what's true," but "what
was believed true, and when did that change."

## Bi-Temporal Edges: Two Independent Clocks, Not One

The Graphiti/Zep approach (already previewed in Chapter 9, Section 6)
tracks **two separate timelines per fact**, not one. **Valid time** —
`valid_at` and `invalid_at` — records when a fact was actually true *in
the world*, independent of when anyone found out about it. **Transaction
time** — `created_at` and `expired_at` — records when the system itself
learned or stopped trusting the fact. These are genuinely independent:
a fact can have a valid-time window from three months ago (it was true
then) while its transaction-time `created_at` is today (the system only
just learned about it, perhaps from a document written after the fact).
Chapter 9, Section 8's supersession mechanism tracked only one axis — a
new fact replacing an old one at write time — a single-clock simplification
that a true bi-temporal graph does not make.

```
              VALID TIME (was it true in the world?)
   ───────────────────────────────────────────────────────▶
        valid_at=Jan          invalid_at=Mar
        "Bob leads Atlas" ────────────┤
                                       └── "Alice leads Atlas" (valid_at=Mar)

              TRANSACTION TIME (when did the system learn it?)
   ───────────────────────────────────────────────────────▶
        created_at=Jan 5           expired_at=Mar 20
        (system recorded it            (system recorded the
         5 days after it                replacement 20 days
         became true)                   after it became true)
```

## Invalidation, Not Deletion

When a new fact contradicts an existing edge, Graphiti sets that edge's
`expired_at` timestamp — the edge is **invalidated**, never deleted. This
is the same principle Chapter 9, Section 8 argued for at the level of a
single semantic fact, now generalized to an entire graph: the old edge
remains queryable for historical questions ("what did we believe about
this in January"), while ordinary present-tense queries filter to only
currently-valid edges and never see the invalidated one as current truth.

## Why This Fits Agent Memory Better Than a Static Knowledge Graph

A static KG answers "what is true" well and has no principled way to
answer "what changed, and when" at all — updating a static graph typically
means overwriting or deleting the old edge outright, which destroys
exactly the historical-reconstruction capability an agent's own memory
(Chapter 9) needs the most: a long-running agent's understanding of a
project, a person, or a system genuinely evolves over weeks and months,
and a memory system that can't distinguish "this used to be true" from
"this was never true" is actively worse than one that admits nothing at
all in that slot.

## Key Takeaways for Section 4

Bi-temporal edges track valid time (was it true in the world) and
transaction time (when did the system learn it) as two independent
clocks — not the single-clock supersession Chapter 9 covered at the fact
level. Contradicted edges are invalidated (an `expired_at` timestamp is
set), never deleted, preserving the ability to reconstruct what was
believed at any past point. This is precisely why Graphiti/Zep is a
better fit for agent memory than a static knowledge graph that can only
ever represent the present.

*Next: a graph — temporal or not — is only useful if something knows when
to query it, and how many times.*

---

# 5: Agentic RAG: Retrieval as a Tool the Loop Calls Repeatedly

## Starting From Plain Language

A junior researcher handed one search query and told "come back with the
final answer, no matter what you find" will confidently report whatever
that single search turned up, right or wrong. A senior researcher treats
the first search as a *draft* — reads what came back, notices exactly what
it's missing, searches again with a sharper question, and keeps going
until they're actually confident, not just done searching once.

## Retrieval Moves Inside the Loop

Classic RAG retrieves once, up front, and generates from whatever came
back — retrieval sits *before* the loop, not inside it. **Agentic RAG**
puts retrieval itself behind a tool the agent can call repeatedly, exactly
the shape Chapter 6 already built for any other verified loop: **trigger →
retrieve → critique the evidence → decide whether to retrieve again or
stop.** This is Chapter 6's verifier ladder, applied specifically to "is
the evidence I have good enough," rather than to "did the code pass its
tests."

```
        ┌──────────┐      ┌───────────┐      ┌────────────────┐      ┌──────────┐
        │  QUERY    │ ──▶ │ RETRIEVE  │ ──▶ │ SELF-CRITIQUE   │ ──▶ │ ENOUGH?   │
        └──────────┘      └───────────┘      │ what's missing?  │      └────┬─────┘
                                 ▲             └────────────────┘           │ no
                                 └───────────── rewrite query ◀─────────────┘
                                                                             │ yes
                                                                             ▼
                                                                      generate answer
```

## Why Generic Self-Critique Fails, and What Fixes It

The single most common failure mode in a naive implementation of this loop
is a critique step that produces something like "I need more information"
— true, but useless, because it gives the next retrieval call nothing to
change, and the loop re-issues an *identical* query and gets back the same
evidence. This is Chapter 6, Section 4's retry-with-changed-context
principle, restated for retrieval: **a useful critique names specifically
what's missing** ("covers last year's pricing but not this year's
update"), which is the concrete, actionable input the next query rewrite
needs. The practical fix that measurably improves loop convergence is
forcing the critique into a **structured schema** — explicit fields for
what was answered, what was missing, and a proposed next query — rather
than letting the model free-write a vague assessment, the same
structured-output discipline Chapter 3, Section 6 already argued for tool
outputs generally.

## The Stop Rule, and the Real Cost

"Enough evidence" needs the same explicit stop-rule treatment Chapter 6,
Section 5 gave every other loop: a confidence threshold on the critique
(stop once the self-assessed confidence clears a bar), a maximum retrieval
count (never loop forever chasing marginal evidence), and — for high-
stakes domains — a dedicated faithfulness check attached to the final
answer rather than trusting the critique loop alone. None of this is
free: multi-step retrieval-critique loops typically cost **three to ten
times** the tokens of a single-pass RAG call, so the honest sweet spot is
large, dynamic knowledge bases where a single retrieval genuinely can't be
trusted to surface everything relevant — not high-volume FAQ lookups or
single-document question answering, where classic single-pass RAG is both
faster and cheaper for the same or better accuracy.

## Key Takeaways for Section 5

Agentic RAG moves retrieval inside a Chapter-6-style verified loop:
retrieve, critique what's missing, rewrite the query specifically to
address that gap, repeat until a stop rule fires. A vague critique
("need more info") stalls the loop by producing an unchanged next query;
a structured critique schema naming exactly what's missing is what
actually improves convergence. The technique costs 3-10x a single-pass
RAG call, so it earns its keep on large, dynamic knowledge bases — not on
lookups a single retrieval already handles well.

*Next: no single retrieval mechanism is right for every query shape — the
practical answer is usually more than one, chosen per query.*

---

# 6: Hybrid Architectures

## Starting From Plain Language

A city's transportation system doesn't run one mode of transit for every
trip — a subway for long, high-volume routes, a bus for flexible
mid-range coverage, a taxi for a specific door-to-door need. Retrieval
architectures converge on the same shape once a real system has to serve
more than one kind of question.

## Four Retrieval Modes, Each Fitting a Different Query Shape

**Vector search** handles fuzzy, semantic recall — "find things *like*
this," where the exact wording doesn't matter and approximate topical
similarity is the actual need. **Graph traversal** (Sections 2-4) handles
structural, relationship-shaped queries — multi-hop, aggregation, "what's
connected to what." **SQL** handles exact aggregation over structured
data — "how many," "what's the average," "list all rows where X" —
queries a graph or a vector index will answer clumsily at best, because
they were never designed for precise numerical aggregation in the first
place. **Keyword search** handles exact-ID and exact-term lookups — a
part number, an error code, a proper noun that must match precisely, where
semantic similarity is actively the wrong tool because "close in meaning"
is not the same as "the exact string that appears in the log."

## The Router

A production system routes each incoming query to whichever mode (or
combination) fits, rather than forcing every query through one pipeline:

```
              incoming query
                    │
                    ▼
        ┌─────────────────────┐
        │   ROUTER (classify    │
        │   the query SHAPE)    │
        └───────────┬──────────┘
        ┌────────────┼────────────┬─────────────┐
        ▼            ▼            ▼             ▼
   "like this"   "connected   "how many /   "exact code
   VECTOR         to what"     average"      / ID"
                  GRAPH         SQL          KEYWORD
```

The router itself can be as simple as a small classifier prompt ("does
this question ask about a relationship, an aggregate, an exact term, or
general similarity?") or as involved as a learned model, but the principle
is the same one Chapter 3, Section 3 established for tool granularity:
match the mechanism to the shape of the actual need, rather than making
one general-purpose tool absorb every query type poorly.

## Key Takeaways for Section 6

Vector, graph, SQL, and keyword retrieval each fit a genuinely different
query shape — fuzzy similarity, relationships, precise aggregation, and
exact-term lookup, respectively — and none of the four is a good
substitute for another on its home turf. A router classifies each query
by shape and dispatches to the matching mode, the same "match the tool to
the task" discipline Chapter 3 already established for tool design.

*Next: once a graph is in the mix, how should it actually be exposed to
the model calling it?*

---

# 7: Graph Traversal as Tool Design

## Starting From Plain Language

Handing someone the master key to a filing system and a request "find
what you need yourself" is more powerful, in principle, than handing them
a labeled index card that says "ask the front desk for record #4471" — but
the labeled card is what actually gets the right answer reliably, from
someone who doesn't know the filing system's internals.

## Purpose-Built Tools, Not Raw Query Language

This is Chapter 3's whole subject, applied specifically to a graph
backend: exposing `get_neighbors(entity_id)`, `find_path(entity_a,
entity_b)`, and `subgraph_summary(entity_id, hops)` as named tools —
each with a narrow, well-described purpose and a bounded, predictable
output shape — is almost always the better default over handing the model
a `run_cypher(query)` tool and trusting it to write correct, efficient
graph-query-language on the fly. The purpose-built tools are easier to
get right on the first attempt (Chapter 3, Section 2's whole argument
about schemas being a UI for a model), impossible to accidentally write as
an unbounded, corpus-scanning query, and their return shape can be
truncated and paginated deliberately (Chapter 3, Section 4) rather than
however much a raw query happens to return.

## When Raw Cypher (in a Sandbox) Is Actually Better

The exception is genuinely open-ended graph exploration where the *shape*
of the needed traversal can't be anticipated in advance — a data analyst
persona asking arbitrary structural questions of the graph, where forcing
every possible question through three fixed tool shapes would be more
limiting than useful. This is Chapter 8's code-mode tradeoff, recast for
graphs: a `run_cypher` tool executed inside a real sandbox (query
timeouts, read-only credentials, row-limit ceilings) trades the safety and
predictability of fixed tools for the flexibility of a full query
language, and is worth that trade specifically when the traversal shapes
genuinely can't be enumerated ahead of time — not as a default, the same
way Chapter 8, Section 7 argued code mode is a deliberate choice, not a
strict upgrade.

## Key Takeaways for Section 7

Purpose-built traversal tools (`get_neighbors`, `find_path`,
`subgraph_summary`) are the better default: predictable shapes, bounded
output, harder to get wrong — the same tool-design discipline Chapter 3
established generally. Raw Cypher in a sandbox earns its place only for
genuinely open-ended exploration where the traversal shape can't be
anticipated — Chapter 8's code-mode tradeoff, not a default choice.

*Next: where does the graph's content actually come from, and what's the
hardest part of keeping it correct?*

---

# 8: Building the Graph Incrementally

## Starting From Plain Language

A shared team wiki that gets edited by whoever's working at the moment,
rather than rebuilt from scratch by one person every month, stays current
in a way a periodically-regenerated document never quite manages — at the
cost of needing real discipline about not creating five slightly different
pages that all describe the same thing.

## The Agent Writes to Its Own Graph

Rather than building the graph purely as an offline batch pipeline
(Section 3's index-time construction), an agent can extract and write new
entities and relations to its own graph *as it works* — a natural
extension of Chapter 9's hot-path writer, applied to structured
relationships instead of flat semantic facts. This keeps the graph current
with the agent's own accumulating experience without a separate,
periodically-scheduled re-indexing job.

## Deduplication and Entity Resolution: the Actually Hard Part

The hard part isn't extraction — it's recognizing that "Priya," "the
platform team's manager," and "P. Sharma" mentioned across three different
sessions are the *same node*, not three separate ones. This is Chapter 9,
Section 7's identity-resolution problem, now with a concrete, structural
consequence attached: an unresolved duplicate doesn't just cause a slightly
redundant memory entry — it **breaks traversal outright**. A `find_path`
query between "Alice" and "Priya-the-manager" silently fails to find a
real, existing path if half the edges connecting them were actually
written against a duplicate node named "P. Sharma" that traversal never
crosses into. Reliable entity resolution — usually a combination of exact
match, alias tracking, and a similarity threshold with human or model
confirmation above a fixed uncertainty band — isn't a nice-to-have cleanup
step; it's the difference between a graph that answers multi-hop questions
correctly and one that silently, invisibly cannot.

## Key Takeaways for Section 8

An agent can write new entities and relations to its own graph
incrementally, as it works, rather than only through offline batch
indexing — a structural extension of Chapter 9's hot-path idea. The hard
part isn't extraction; it's entity resolution — an unresolved duplicate
node doesn't just add redundancy, it silently breaks traversal for any
path that should have crossed through it.

*Next: how do you actually know any of this is working better than not
having a graph at all?*

---

# 9: Evaluating Graph Retrieval

## Starting From Plain Language

A graph that looks impressively large and well-connected in a diagram
tells you nothing about whether it actually answers questions correctly —
the same way a beautifully organized filing cabinet tells you nothing
about whether the right document comes out when someone asks for it.

## Three Metrics, Each Answering a Different Question

**Multi-hop accuracy** measures whether the system's final answer to a
genuinely multi-hop question (Section 1) is correct — the outcome metric,
analogous to Chapter 14's final-outcome eval category. **Path precision**
measures something more specific: when the system traverses a path to
justify its answer, is that path actually a real, correct path in the
graph, or a plausible-sounding but wrong hop sequence — this catches a
failure multi-hop accuracy alone can miss, an answer that happens to be
right for the wrong traversal, which won't generalize to the next similar
question. **Cost-per-answer against plain hybrid RAG** is the metric that
actually settles Section 10's question in practice: given the real,
measured indexing and query cost of the graph approach, does it produce
a *better* answer per dollar than a well-tuned hybrid vector/keyword
pipeline on the same question set — not "is the graph technically more
sophisticated," but "does it win on the metric that was the whole point."

## Key Takeaways for Section 9

Multi-hop accuracy measures whether the final answer is right; path
precision measures whether the *justifying traversal* was actually valid,
catching right-answer-wrong-reasoning cases accuracy alone misses;
cost-per-answer against a hybrid RAG baseline is the metric that actually
decides whether the graph was worth building, on the terms that matter.

*Next: after nine sections building the case for graphs, the honest
closing argument for when not to bother.*

---

# 10: Choosing Not to Use a Graph

## Starting From Plain Language

A specialist tool that does one narrow thing extremely well is the right
call exactly when that narrow thing is what's actually needed, and the
wrong call — an expensive, high-maintenance answer to a question nobody
was asking — every other time. Nine sections of "here's what graphs are
good at" can easily read as "therefore build one"; that's not this
chapter's actual conclusion.

## The Honest Default

**Hybrid vector + keyword + reranker** (Section 6, minus the graph and SQL
legs, which apply when structured/relational data specifically calls for
them) covers the substantial majority of real retrieval needs: most
questions are single-hop, most corpora don't require corpus-wide theme
summarization, and a well-tuned reranker closes much of the precision gap
a naive top-k vector search leaves open. This default earns its
"default" status specifically because it has none of GraphRAG's upfront
indexing cost (Section 3) and none of a graph's ongoing entity-resolution
burden (Section 8).

## When a Graph Actually Earns Its Keep

Reach for a graph specifically when the question set is genuinely
**relationship-shaped** — real, recurring multi-hop and aggregation
questions (Section 1), not a one-off request that could be answered by
reading two documents by hand — and when Section 9's cost-per-answer
comparison, measured on your own actual query mix, comes out ahead of the
hybrid baseline. Building a knowledge graph because relationship questions
are *theoretically possible* against your corpus, without evidence they're
actually asked often enough to justify the indexing and maintenance cost,
is Section 3's cost accounting and Section 8's entity-resolution burden
paid for a benefit that was never real to begin with — a graph nobody
queries is the single most common way this technology gets adopted for
the wrong reason.

## Key Takeaways for Section 10

Hybrid vector + keyword + reranker is the honest default, covering most
retrieval needs with none of a graph's indexing or entity-resolution
overhead. Build a graph when relationship-shaped questions are a real,
recurring, *measured* part of your actual query mix — not because they're
theoretically answerable against your data. A graph nobody queries is a
cost with no corresponding benefit, no matter how well-built it is.

*Next: putting exact numbers under two of this chapter's central claims.*

---

# 11: Dry-Run: A 6-Node Graph, a 2-Hop Answer, and PageRank by Hand

## The Graph

Six nodes, six directed edges — small enough to trace completely by hand,
large enough to show real structure:

```
   Alice ──works_on──▶ ProjectAtlas ──owned_by──▶ TeamPlatform ──managed_by──▶ Priya
                              ▲                          ▲
   Bob ──works_on────────────┘                           │
    │                                                     │
    └──works_on──▶ ProjectOrion ──owned_by────────────────┘
```

Edges: `Alice→ProjectAtlas` (works_on), `Bob→ProjectAtlas` (works_on),
`Bob→ProjectOrion` (works_on), `ProjectAtlas→TeamPlatform` (owned_by),
`ProjectOrion→TeamPlatform` (owned_by), `TeamPlatform→Priya`
(managed_by).

## Part A: A 2-Hop Question Vector Search Provably Cannot Answer

**Question:** "Which team owns the project Alice works on?"

**By hand:** start at `Alice`. Hop 1, follow `works_on`: `Alice →
ProjectAtlas`. Hop 2, follow `owned_by`: `ProjectAtlas → TeamPlatform`.
**Answer: TeamPlatform**, reached in exactly 2 hops.

**Why vector search cannot answer this, provably, not just poorly:** the
string "Alice" and the string "TeamPlatform" never co-occur in the same
source document — Alice's mention is in a project-assignment record, and
TeamPlatform's ownership of ProjectAtlas is in a completely separate team
charter document. A retriever ranking documents by similarity to "which
team owns the project Alice works on" can, at best, retrieve *both*
individual documents (Alice's assignment; ProjectAtlas's ownership record)
if the embeddings happen to be good enough — but nothing in a similarity
score performs the **join** between them. The answer only exists as the
*composition* of two separately-written facts, which is precisely
Section 1's claim made concrete on six nodes.

## Part B: PageRank-Style Importance, Two Iterations by Hand

Standard PageRank recurrence, damping factor $d = 0.85$, $N = 6$ nodes:

$$PR(n) = \frac{1-d}{N} + d \sum_{m \,\in\, \text{in-links}(n)} \frac{PR(m)}{L(m)}$$

$PR(n)$ is node $n$'s importance score. $\frac{1-d}{N}$ is the baseline
share every node gets regardless of structure — $\frac{0.15}{6} = 0.025$
throughout this dry-run. $\text{in-links}(n)$ is the set of nodes with an
edge pointing *into* $n$. $L(m)$ is node $m$'s **out-degree** — how many
outgoing edges it splits its own importance across. *(For this
hand-computable toy graph, Priya's zero out-degree — a "dangling node" —
is left unredistributed, a standard implementation detail simplified here
so the arithmetic stays followable on paper.)*

Out-degrees: $L(\text{Alice})=1$, $L(\text{Bob})=2$,
$L(\text{ProjectAtlas})=1$, $L(\text{ProjectOrion})=1$,
$L(\text{TeamPlatform})=1$, $L(\text{Priya})=0$.

Initial scores (uniform): $PR_0(n) = \frac{1}{6} \approx 0.1667$ for all
six nodes.

**Iteration 1:**

```
PR1(Alice)        = 0.025 + 0                                              = 0.0250
PR1(Bob)          = 0.025 + 0                                              = 0.0250
PR1(ProjectAtlas) = 0.025 + 0.85*(0.1667/1 + 0.1667/2)                     = 0.2375
PR1(ProjectOrion) = 0.025 + 0.85*(0.1667/2)                                = 0.0958
PR1(TeamPlatform) = 0.025 + 0.85*(0.1667/1 + 0.1667/1)                     = 0.3084
PR1(Priya)        = 0.025 + 0.85*(0.1667/1)                                = 0.1667
```

**Iteration 2**, using $PR_1$:

```
PR2(Alice)        = 0.025 + 0                                              = 0.0250
PR2(Bob)          = 0.025 + 0                                              = 0.0250
PR2(ProjectAtlas) = 0.025 + 0.85*(0.0250/1 + 0.0250/2)                     = 0.0569
PR2(ProjectOrion) = 0.025 + 0.85*(0.0250/2)                                = 0.0356
PR2(TeamPlatform) = 0.025 + 0.85*(0.2375/1 + 0.0958/1)                     = 0.3084
PR2(Priya)        = 0.025 + 0.85*(0.3084/1)                                = 0.2871
```

**Ranking after iteration 2: TeamPlatform (0.3084) > Priya (0.2871) >
ProjectAtlas (0.0569) > ProjectOrion (0.0356) > Alice ≈ Bob (0.0250).**

## Why This Is the Concrete Mechanism Behind Community Summarization

Notice what actually rose to the top: not the nodes with the most raw
edges touching them, but the nodes sitting *downstream* of the most
structural flow — `TeamPlatform` and `Priya` accumulate importance because
multiple paths converge through them, not because either has an unusually
high edge count on its own. This is precisely the intuition GraphRAG's
community-and-importance weighting (Section 3) is built on: when a
hierarchical summarizer has to decide which entities deserve mention in a
community's summary, importance-style scoring — not raw degree, not
alphabetical order — is what should decide, because it's the nodes
structurally central to a community's relationships that actually
characterize what that community is *about*.

## Key Takeaways for Section 11

A 6-node, 6-edge graph makes Section 1's abstract claim concrete: the
2-hop answer to "which team owns Alice's project" requires composing two
facts that never appear in the same document, which no similarity score
can perform. Two hand-computed PageRank iterations show `TeamPlatform` and
`Priya` rising to the top not from raw edge count but from structural
convergence — the same importance signal GraphRAG's community
summarization leans on when deciding what a cluster of entities is really
about.

*Next: closing the loop on the whole chapter.*

---

# 12: Key Takeaways + Master Decision Table

The single mental model for this chapter: **reach for a graph when the
question is about relationships between facts, not facts in isolation** —
and treat that as a measured, evidenced decision (Section 9, Section 10),
not a default reached for because the technology exists.

| I want to know... | Reach for | Key fact |
|---|---|---|
| Why vector search fails on some questions, provably | Section 1 | Multi-hop, aggregation, and global questions require combining or enumerating facts that similarity scoring structurally cannot join |
| What a knowledge graph actually is | Section 2 | Entities (nodes), relations (typed directed edges), properties (attributes); extraction is schema-guided (precise, blind spots) or open (broad recall, duplicate-prone) |
| How GraphRAG actually works | Section 3 | Extraction → graph → recursive Leiden community detection → summaries written once at index time; ~97% token savings at the root level, paid for by real upfront indexing cost |
| Why a static graph isn't enough for memory | Section 4 | Bi-temporal edges track valid time and transaction time independently; contradicted edges are invalidated (not deleted), preserving historical reconstruction |
| How retrieval becomes a loop instead of a single call | Section 5 | Retrieve → structured self-critique (what's missing, specifically) → rewrite → repeat until a real stop rule fires; costs 3-10x single-pass RAG, so it earns its keep on large, dynamic corpora |
| Which retrieval mode fits which question | Section 6 | Vector (fuzzy similarity), graph (relationships), SQL (aggregation), keyword (exact terms) -- a router dispatches by query shape |
| How to expose a graph to a model safely | Section 7 | Purpose-built tools (`get_neighbors`, `find_path`, `subgraph_summary`) by default; raw Cypher in a sandbox only for genuinely open-ended exploration |
| What's actually hard about building a graph incrementally | Section 8 | Not extraction -- entity resolution; an unresolved duplicate node silently breaks traversal, not just adding redundancy |
| How to know if a graph is actually working | Section 9 | Multi-hop accuracy (is the answer right), path precision (was the traversal actually valid), cost-per-answer vs hybrid RAG (did it actually win) |
| When to skip the graph entirely | Section 10 | Hybrid vector + keyword + reranker by default; build a graph only when relationship-shaped questions are a real, measured, recurring part of your query mix |
| How to compute traversal and importance by hand | Section 11 | A 2-hop join across two documents that never co-occur; PageRank rewards structural convergence, not raw edge count -- the mechanism behind community summarization |

**Connection forward:** Chapter 11 leaves knowledge representation behind
and turns to **execution** representation — the graph/state-machine
runtime layer that controls an agent's own control flow, not the facts it
reasons over. The word "graph" reappears, but the question changes from
"what do these nodes mean" to "what happens next, and who decides."
