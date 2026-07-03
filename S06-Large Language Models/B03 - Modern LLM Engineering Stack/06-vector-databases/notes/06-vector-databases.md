# Vector Databases

Topic 5 treated retrieval as a function called `dense_search`: embed the
query, take the dot product against every stored embedding, sort, return the
top-k. That function was *correct*, and for a 14-document corpus it was also
*fast* — but it quietly assumed the entire corpus fits in memory and can be
scanned in full for every query. This note opens that box. It starts by
making the brute-force cost explicit and naming the **recall/speed tradeoff**
that every approximate method makes. It then builds, by hand, the graph
structure behind **HNSW** (Hierarchical Navigable Small World) — the
algorithm underneath almost every modern vector database — and traces a
search through it one step at a time with real numbers. From there it moves
to FAISS's real implementation, two real databases (Chroma and Qdrant), how
metadata filtering interacts with approximate search, and finally vector
*quantization*, which compresses the index itself.

---

## Table of Contents

1. [Where This Sits](#where-this-sits)
2. [From Brute-Force to ANN](#1-from-brute-force-to-ann)
3. [HNSW Intuition](#2-hnsw-intuition)
4. [FAISS Hands-On](#3-faiss-hands-on)
5. [Embedded vs Server Databases](#4-embedded-vs-server-databases)
6. [Metadata Filtering](#5-metadata-filtering)
7. [Vector Quantization for Storage](#6-vector-quantization-for-storage)
8. [Comparison Table](#comparison-table)
9. [Summary & Connection Forward](#summary--connection-forward)

---

## Where This Sits

```
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 5 — Advanced RAG                                        │
│  dense_search / bm25_search treated the vector store as a          │
│  black box: "give me the top-k by similarity"                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  open the box: how is "top-k by similarity"
                              │  actually computed at scale?
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 6 — Vector Databases  (THIS NOTE)                       │
│  brute-force -> HNSW -> FAISS -> Chroma/Qdrant -> filtering ->      │
│  quantization                                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 7 — Structured Outputs & Tool Calling                   │
│  now that retrieval is fast, filtered, and scalable: how does an    │
│  LLM reliably consume retrieved chunks and produce structured       │
│  output?                                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. From Brute-Force to ANN

**Summary**: Brute-force nearest-neighbor search computes the distance from
a query to *every* stored vector and sorts. It is exact, but its cost grows
linearly with the number of stored vectors. Approximate nearest-neighbor
(ANN) methods pre-organize the vectors into a structure that lets a query
skip most of them, accepting a small chance of missing the true answer
(measured as **recall**) in exchange for a large speedup.

**The problem it solves**: `dense_search` in Topic 5 computed
`doc_embeddings @ query_embedding` — a single matrix-vector product covering
all 14 documents — then sorted. That's brute force, and at 14 documents it's
effectively free. The moment the corpus grows to tens of thousands or
millions of documents, the same operation becomes the dominant cost of
answering a query.

**The intuition**: Brute-force search is like finding the closest restaurant
to you by calling every restaurant in the city, asking for its address, and
computing the distance — for *every single search*. It always gives the
correct answer, but it doesn't scale. ANN search is like a GPS that
pre-computed a road network once, so that finding "closest" no longer
requires contacting every restaurant — it requires following a few
well-chosen roads.

**The math**: For $N$ stored vectors of dimension $D$, computing the
distance from a query $\mathbf{q}$ to every stored vector $\mathbf{v}_i$
costs $O(D)$ per vector, so $O(N \cdot D)$ total, plus $O(N \log k)$ to find
the top-$k$ by sorting (or a partial sort/heap). The Euclidean (L2) distance
used throughout this note is

$$\text{dist}(\mathbf{v}, \mathbf{q}) = \|\mathbf{v} - \mathbf{q}\|_2 = \sqrt{\sum_{j=1}^{D} (v_j - q_j)^2}$$

**Recall@k** is the fraction of an approximate method's top-$k$ results that
also appear in the *exact* top-$k$:

$$\text{Recall@}k = \frac{|\,\text{ApproxTopK} \cap \text{TrueTopK}\,|}{k}$$

A recall of 1.0 means the approximate method found exactly the same $k$
neighbors as brute force (possibly in a different order); a recall of 0.5
means only half of the approximate results were "really" in the true top-k.

**Dry-run**: The template notebook builds a synthetic dataset of 50,000
vectors in 128 dimensions, organized into 5 topic clusters (`physics`,
`biology`, `history`, `cooking`, `sports`) — each cluster is a random center
plus Gaussian noise, a rough stand-in for how a sentence embedding model
places same-topic documents near each other. A plain-numpy brute-force search
(`vectors - query`, then `np.linalg.norm`, then `argsort`) over this dataset
took roughly **13 ms per query** on the test machine. That's
$50{,}000 \times 128 \approx 6.4$ million multiply-subtracts, plus a full sort
over 50,000 distances, *every time*. At even 50 queries/second this would
consume more than half a second of CPU time per second on distance
computation alone — and production corpora are often 100-1000x larger than
this toy example. Section 2 builds, by hand, the data structure that lets ANN
search avoid almost all of that work.

---

## 2. HNSW Intuition

**Summary**: HNSW (Hierarchical Navigable Small World) organizes vectors into
several stacked graphs called *layers*. Every vector is in the bottom layer,
connected to a handful of its nearest neighbors; progressively smaller random
subsets appear in higher layers, connected more sparsely. A search starts at
a fixed entry point in the top layer and *greedily walks* toward the query —
following whichever neighbor is closest — dropping down a layer each time the
walk gets stuck, until a walk on the bottom layer produces the final answer.

**The problem it solves**: Section 1 established that scanning all $N$
vectors is too slow at scale. A graph where "close" vectors are connected to
each other lets a search start anywhere and *follow edges toward the query*
without ever touching most of the graph — but only if the graph has the right
structure. A graph where every node only connects to its immediate neighbors
would still require many hops to cross the space (like only having local
streets — crossing a country one block at a time). HNSW's layering fixes this
by also providing long-range "express" connections.

**The intuition**: Picture a road network. The top layer is the interstate
highway system — a handful of long-range connections that let you cross the
country in a few hops, but with very few on/off ramps. The middle layer is
state highways — denser, shorter-range. The bottom layer is local streets —
every house connected to its immediate neighbors. To drive from one specific
house to another far away, you don't take local streets the whole way: local
streets to a highway on-ramp, the highway for most of the distance, then
local streets again at the destination. HNSW search runs this in reverse —
it starts on the highway (the top layer, where the fixed entry point lives)
and exits onto progressively more local roads as the walk gets close to the
query.

**The math**: A **greedy walk** within one layer is: given a current node
$c$ and its neighbor set $N(c)$ in that layer, compute
$\text{dist}(\mathbf{n}, \mathbf{q})$ for every $n \in N(c)$, and move to
$\arg\min_n \text{dist}(\mathbf{n}, \mathbf{q})$ if that distance is smaller
than $\text{dist}(\mathbf{c}, \mathbf{q})$; otherwise stop. The full search is
this walk repeated once per layer, from the top layer down to layer 0, always
starting each new layer's walk from where the previous layer's walk stopped.

**Dry-run**: Six points in 2D, plus a query $Q = (7.5, 1.5)$:

```
|                                        |
|                                    C   |
|                                        |
|                                        |
|                                        |
|                                        |
|                                        |
|                                        |
|                                        |
|    B               D                   |
|                                        |
|                                        |
|                                        |
|                                        |
|                                        |
|                                E       |
|                              Q         |
|                                        |
|                        F               |
|A                                       |
+----------------------------------------+
  0                                  x=9
```

The points are $A=(0,0)$, $B=(1,5)$, $C=(9,9)$, $D=(5,5)$, $E=(8,2)$,
$F=(6, 0.5)$. The distance from each point to $Q$:

| Point | Distance to Q |
|---|---|
| E | 0.707 |
| F | 1.803 |
| D | 4.301 |
| B | 7.382 |
| A | 7.649 |
| C | 7.649 |

So $E$ is the true nearest neighbor, by a wide margin.

The pairwise distances between all six points (computed once, used to build
every layer):

```
A-B=5.10  A-C=12.73  A-D=7.07  A-E=8.25  A-F=6.02
B-C=8.94  B-D=4.00   B-E=7.62  B-F=6.73
C-D=5.66  C-E=7.07   C-F=9.01
D-E=4.24  D-F=4.61
E-F=2.50
```

**Layer 0** (every point, $M=2$ nearest neighbors each, read directly off the
table above): $A \to \{B, F\}$, $B \to \{D, A\}$, $C \to \{D, E\}$,
$D \to \{B, E\}$, $E \to \{F, D\}$, $F \to \{E, D\}$.

**Layer 1** (sparse subset $\{C, D, F\}$, each connected to its nearest
neighbor *within the subset*): $C$'s closest is $D$ (5.66), $D$'s closest is
$F$ (4.61) — giving the chain $C - D - F$.

**Layer 2** (single entry point): $C$ — deliberately the farthest point from
$Q$ (tied with $A$ at 7.649), so the search has real ground to cover.

**The walk**:

```
Layer 2: entry = C (dist 7.649). No neighbors here -> drop down with current=C.

Layer 1: at C (7.649). Neighbor D = 4.301, closer -> move to D.
         at D (4.301). Neighbors {C=7.649, F=1.803}; F closer -> move to F.
         at F (1.803). Neighbor D=4.301, not closer -> stop. Result: F.

Layer 0: at F (1.803). Neighbors {E=0.707, D=4.301}; E closer -> move to E.
         at E (0.707). Neighbors {F=1.803, D=4.301}, neither closer -> stop.
         Result: E.

HNSW final answer: E (dist 0.707) == brute-force true nearest neighbor: E
```

The walk visited only 4 of the 6 points ($C \to D \to F \to E$) and found the
exact same answer as scanning all 6. That's the appeal of HNSW: a small
fraction of the work, often the right answer.

**The gotcha**: The walk worked *because* every step happened to have a
neighbor strictly closer to $Q$ than the current node, all the way down to
$E$. This is not guaranteed. If $E$'s only layer-0 connections pointed to
nodes *farther* from $Q$ than $E$ itself — a **local minimum** in the graph —
the greedy walk would stop early and report the wrong answer, even with $E$
sitting right there. This is precisely why FAISS's `IndexHNSWFlat` (Section
3) doesn't always achieve 100% recall, and why its `efSearch` parameter
exists: instead of tracking a single "current best" node, the real algorithm
keeps a list of the best `efSearch` candidates seen so far, exploring several
promising directions in parallel rather than committing to one. A larger
`efSearch` means a longer candidate list, fewer chances of getting stuck in a
local minimum, and therefore higher recall — at the cost of visiting more
nodes per query.

---

## 3. FAISS Hands-On

**Summary**: [FAISS](https://github.com/facebookresearch/faiss) is the
library most vector databases build their indexing on top of. `IndexFlatL2`
implements exact brute-force search (Section 1) in optimized C++; it is the
ground truth used to measure recall. `IndexHNSWFlat` implements the layered
graph from Section 2, automatically built and searched.

**The problem it solves**: Sections 1-2 established the concepts in numpy
and by hand. FAISS provides production-grade implementations of both, so the
recall/speed tradeoff can be measured on a realistically sized dataset rather
than a 6-point toy example.

**The intuition**: `IndexFlatL2` is "the librarian who checks every book."
`IndexHNSWFlat` is "the librarian who follows the layered road-network from
Section 2." Two parameters tune that road network: `M` is how many roads
(neighbor connections) each location gets per layer — more roads means a
denser, more accurate but larger graph. `efSearch` is the size of the
candidate list the greedy walk keeps at *query* time — the direct knob on the
recall/speed tradeoff described in Section 2's gotcha.

**The math**: Recall@k is computed exactly as in Section 1, comparing
`IndexHNSWFlat`'s returned indices against `IndexFlatL2`'s for the same
queries. Speedup is the ratio of per-query latencies.

**Dry-run (measured results)**: On the 50,000-vector, 128-dimensional
dataset from Section 1, with 20 query vectors:

| Index | ms/query | Top-10 recall |
|---|---|---|
| `IndexFlatL2` (exact) | 0.317 | 1.000 (ground truth) |
| `IndexHNSWFlat` (M=32, efSearch=16) | 0.036 | 0.530 |

That's an **~8.9x speedup** for ~53% recall at the default `efSearch=16`.
Sweeping `efSearch` on the *same* graph (rebuilding the graph is expensive;
`efSearch` only changes query-time behavior) traces out the tradeoff curve:

| efSearch | recall@10 | ms/query |
|---|---|---|
| 4 | 0.285 | 0.263 |
| 8 | 0.390 | 0.018 |
| 16 | 0.530 | 0.021 |
| 32 | 0.720 | 0.033 |
| 64 | 0.870 | 0.051 |

Recall climbs steadily from 0.285 to 0.870 as `efSearch` increases from 4 to
64, while latency stays well under the exact search's 0.317 ms/query across
the whole sweep. (The `efSearch=4` row's latency is an outlier from JIT/cache
warm-up on the first call in the sweep — the underlying trend, confirmed by
the later rows, is that larger `efSearch` costs more per query.)

**The gotcha**: Recall here tops out around 0.87 even at `efSearch=64` — it
does not cleanly approach 1.0 the way it might on some datasets. This
particular dataset's five Gaussian clusters in 128 dimensions produce many
near-ties in distance (many points roughly equidistant from a query near a
cluster boundary), which makes "the true top-10" somewhat arbitrary at the
margins — small floating-point differences can reorder near-tied candidates.
The *qualitative* lesson — recall increases monotonically with `efSearch` at
a real but modest latency cost — is the one that generalizes; the exact
numbers are dataset-dependent.

---

## 4. Embedded vs Server Databases

**Summary**: FAISS is a library — index data structures and search
algorithms, with no persistence, no metadata, and no client/server boundary.
Vector *databases* wrap an ANN index with those production features.
**Chroma** is *embedded*: it runs in the same process as the application,
backed by SQLite plus a local HNSW index. **Qdrant** is *server-based*:
normally a separate process your application talks to over HTTP/gRPC
(though its Python client also offers an in-memory mode for testing).

**The problem it solves**: A raw FAISS index is just a binary blob in memory.
Real applications need to associate each vector with metadata (a document
ID, a category, a timestamp), persist the index across restarts, and often
share it across multiple application processes or machines. Vector databases
solve these problems so the application doesn't have to.

**The intuition**: Chroma is to vector search what SQLite is to relational
data — an embedded, zero-configuration database that lives inside your
application's process, perfect for prototyping and small-to-medium local
datasets. Qdrant is to vector search what PostgreSQL is to relational data —
a server your application connects to, designed for production deployments
with sharding, replication, and a stable API surface independent of any
single application process.

**Dry-run**: The template notebook loads a 2,000-vector subset of the
Section 1 dataset (with each vector's `category` as metadata) into both a
Chroma `Collection` and a Qdrant `:memory:` client, then runs the same top-5
query against both. Both return the **same 5 ids in the same order** — at
2,000 vectors, both libraries' default indices are exact (or close enough to
exact) that there's no observable difference yet. The interesting
differences — persistence guarantees, filtering implementation, and scaling
model — are structural, not visible in a single small query, which is why
the comparison table at the end of this note summarizes them directly.

**The gotcha**: "Embedded" vs "server-based" is about *deployment*, not
*algorithm* — both Chroma and Qdrant use HNSW-family indices internally.
Don't confuse "Chroma is simpler to set up" with "Chroma is less capable" —
for a single-process application with a moderate dataset, embedded is
usually the *better* choice, not just the easier one. The decision to move to
a server-based database is driven by needing to share the index across
processes/machines or needing production operational features (replication,
backups, access control), not by raw search quality.

---

## 5. Metadata Filtering

**Summary**: Real queries are rarely "find the 5 nearest vectors" in
isolation — they're "find the 5 nearest vectors *where category =
'biology'*." There are two naive ways to combine vector search with a
metadata filter, and one better way. **Post-filtering** searches first,
filters after — simple, but can return fewer results than requested, or
zero. **Pre-filtering** restricts the search to matching vectors first — always
correct, but can be slow if the candidate set is large. **Filterable HNSW**
(Qdrant's approach) integrates the filter into the graph traversal itself.

**The problem it solves**: Suppose a corpus is 80% `cooking` documents and
20% `biology` documents, and a query's nearest neighbors by raw vector
distance happen to all be `cooking`. A user who asked for "the 5 nearest
*biology* documents" needs 5 biology results — but the 5 *globally* nearest
vectors contain zero of them.

**The intuition**: Post-filtering is "search the whole city for the 5
closest restaurants, *then* check which of those 5 happen to serve
vegetarian food" — if none of the 5 closest restaurants are vegetarian, you
get zero results, even if there's a great vegetarian place six blocks away.
Pre-filtering is "first get the list of every vegetarian restaurant in the
city, *then* find the 5 closest among just those" — correct, but if there are
10,000 vegetarian restaurants, that's a lot to search through directly.
Filterable HNSW is "follow the road network from Section 2, but only ever
step onto roads that lead to a vegetarian restaurant" — it gets pre-filtering's
guarantee of a correct answer without pre-filtering's need to enumerate every
match up front.

**The math**: For post-filtering, if $p$ is the fraction of the unfiltered
top-$k'$ results that match the filter, the post-filtered result count is
$\approx p \cdot k'$ — which can be far less than the requested $k$, or zero,
if $p = 0$ for that particular query and top-$k'$.

**Dry-run**: The template notebook's exercise runs an *unfiltered* top-5
query against the 2,000-vector Qdrant collection from Section 4. With this
particular query and dataset, the unfiltered top-5 all share **one**
category — meaning a request for top-5 filtered to any *other* category,
applied as post-filtering, returns **0 results** (0 out of 5 requested).
Re-running the same filter as a *pre-filter* — Qdrant's native
`query_filter=Filter(must=[FieldCondition(key="category",
match=MatchValue(value=...))])` — returns the full 5 requested results, all
correctly matching the target category. Same query, same filter, same
database — the only difference is *when* the filter is applied, and that
difference is the gap between 0 results and 5.

**The gotcha**: This failure mode is silent and data-dependent — it doesn't
raise an error, it just returns fewer results than asked for (or none), and
whether it triggers depends on how "clustered" the unfiltered top-$k'$
happens to be for a given query. A system using naive post-filtering can work
fine in testing (where filters happen to match common categories) and then
intermittently return empty results in production for less common filter
values — exactly the kind of bug that's easy to miss until a user hits it.

---

## 6. Vector Quantization for Storage

**Summary**: Every index so far stores each vector as raw float32 numbers —
512 bytes per 128-dimensional vector. **Vector quantization** compresses each
stored vector into a smaller code, trading some search accuracy for a much
smaller index. **Scalar quantization (SQ8)** maps each dimension
independently to one byte (4x compression). **Product quantization (PQ)**
splits each vector into $M$ sub-vectors and replaces each with a single-byte
codebook index (up to 64x compression at $M=8$).

**The problem it solves**: At billions of vectors, raw float32 storage
becomes a major memory cost — often *larger* than the graph structure
(Section 2) built on top of it. Quantization shrinks the dominant cost.

**The intuition**: Scalar quantization is like rounding every measurement on
a map from "37.7749295, -122.4194155" to "37.77, -122.42" — each individual
number takes less space, and for most purposes the rounded version is still
useful. Product quantization is more like replacing a long, precise
description of a face ("eyes: hazel-green, slightly almond-shaped...") with a
short code into a catalog of pre-defined face types ("face #214") — far less
data per face, but now every face that's "close enough" to type #214 looks
identical to the system.

**The math**: For $D=128$ dimensions, float32 storage is $4D = 512$
bytes/vector. SQ8 maps each dimension to a `uint8` (1 byte), giving $D = 128$
bytes/vector — a $4\times$ reduction. PQ splits the $D$ dimensions into $M$
sub-vectors of $D/M$ dimensions each, runs k-means with 256 centroids
(learned from the dataset) on each sub-vector's values across all stored
vectors, and stores each vector as $M$ single-byte centroid indices — $M$
bytes/vector, a $\frac{4D}{M}\times$ reduction.

**Dry-run (measured results)**, on the 50,000-vector, 128-dimensional
dataset from Section 1:

| Index | Bytes/vector | Compression | Recall@10 |
|---|---|---|---|
| `IndexFlatL2` | 512 | 1x (baseline) | 1.000 |
| `IndexScalarQuantizer` (SQ8) | 128 | 4x | 0.980 |
| `IndexPQ`, $M=64$ | 64 | 8x | 0.760 |
| `IndexPQ`, $M=32$ | 32 | 16x | 0.350 |
| `IndexPQ`, $M=16$ | 16 | 32x | 0.145 |
| `IndexPQ`, $M=8$ | 8 | 64x | 0.055 |

For all 50,000 vectors, total index size drops from **25,000 KB** (FlatL2)
to **6,250 KB** (SQ8) to **3,125 KB** (PQ, $M=64$).

**The gotcha**: SQ8's $4\times$ compression costs almost nothing (recall
0.980 vs 1.000) — each dimension still gets its own byte, just at lower
precision. PQ's compression/recall tradeoff is far steeper and highly
sensitive to $M$: going from $M=64$ to $M=8$ is an 8x further size reduction
but drops recall from 0.760 to 0.055 — at $M=8$, each sub-vector spans 16
original dimensions compressed into a single byte (256 possible codes), which
is too coarse for this 128-dimensional dataset to distinguish vectors well.
In production, PQ is typically paired with a coarse pre-filtering index
(`IndexIVFPQ`) and/or a re-ranking pass over a small set of candidates using
the uncompressed vectors — using raw PQ distances alone, as this dry-run
does, is the worst case for PQ's accuracy.

**Connection forward**: This is the *same idea*, applied to a different kind
of data, as Topic 9's model quantization — replacing high-precision float32
weights with low-precision integers plus a small lookup table (or, for PQ
specifically, a learned codebook), accepting a controlled accuracy loss for a
large memory win. The recall-vs-compression curve here is the same shape as
the perplexity-vs-bit-width curve you'll see for quantized LLM weights.

---

## Comparison Table

| Tool | Persistence | Metadata filtering | Scaling | Ease of setup |
|---|---|---|---|---|
| FAISS | None built-in (manual save/load of index files) | None — pure vector index | Single machine; very large indices via PQ/IVF | `pip install faiss-cpu`, pure library |
| Chroma | Local on-disk (SQLite + index files), embedded | Yes — `where` filters on metadata | Single machine | `pip install chromadb`, runs in-process |
| Qdrant | Server-managed (disk-backed collections), or in-memory for testing | Yes — native filterable HNSW (`query_filter`) | Horizontal — sharding & replication across nodes | Run as a server (Docker), or `:memory:` client for testing |

---

## Summary & Connection Forward

This note opened the box that Topic 5's `dense_search` left closed. Brute
force is exact but $O(N \cdot D)$ — fine at 14 documents, prohibitive at
millions. HNSW trades a small, controllable amount of recall for a large
speedup by organizing vectors into a layered graph and walking it greedily,
with `efSearch` directly controlling how much of that tradeoff you accept.
FAISS implements this for real; Chroma and Qdrant wrap it with persistence,
metadata, and (for Qdrant) a server boundary and native filtering. Metadata
filtering interacts with ANN search in a way that's easy to get silently
wrong — post-filtering can return empty results for filters that have plenty
of true matches, simply because the filter was applied *after* the search
instead of *during* it. And quantization shrinks the index itself, at a
recall cost that depends sharply on how aggressively you compress.

Topic 7 (Structured Outputs & Tool Calling) moves up a layer: retrieval can
now return the right chunks efficiently, with the right filters, at scale —
the next question is how to get an LLM to reliably *consume* those chunks and
produce machine-parseable output, the foundation for the agentic tool-calling
loops from Topic 4.
