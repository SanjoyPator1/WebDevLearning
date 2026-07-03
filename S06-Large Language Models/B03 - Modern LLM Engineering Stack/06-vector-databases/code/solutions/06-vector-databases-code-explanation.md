# Topic 6 — Vector Databases: Code Explanation

This file walks through every cell of `06-vector-databases.ipynb`, showing
the actual code and the actual output it produces — everything in this
notebook ran end-to-end (`faiss-cpu`, `chromadb` with the `pysqlite3-binary`
shim, and `qdrant-client` in `:memory:` mode, all real local libraries, no
mocking).

For the *why* behind each technique (recall/speed tradeoffs, HNSW's layered
graph, pre- vs post-filtering, quantization), see
[`../../notes/06-vector-databases.md`](../../notes/06-vector-databases.md)
and the topic plan,
[`../../../06-vector-databases.md`](../../../06-vector-databases.md). This
file stays close to the code.

---

## Table of Contents

- [1. From Brute-Force to ANN](#1-from-brute-force-to-ann)
- [2. HNSW Intuition](#2-hnsw-intuition)
- [3. FAISS Hands-On](#3-faiss-hands-on)
- [4. Embedded vs Server DBs (Exercise)](#4-embedded-vs-server-dbs-exercise)
- [5. Metadata Filtering (Exercise)](#5-metadata-filtering-exercise)
- [6. Vector Quantization for Storage](#6-vector-quantization-for-storage)

---

## 1. From Brute-Force to ANN

```python
np.random.seed(42)

N_VECTORS = 50_000
DIM = 128
CATEGORIES = ["physics", "biology", "history", "cooking", "sports"]

centers = np.random.randn(len(CATEGORIES), DIM).astype("float32")
category_ids = np.random.randint(0, len(CATEGORIES), size=N_VECTORS)
noise = np.random.randn(N_VECTORS, DIM).astype("float32") * 0.5
vectors = centers[category_ids] + noise
print(f"vectors.shape = {vectors.shape}")
print(f"Category counts: {np.bincount(category_ids)}")

N_QUERIES = 20
K = 10
query_category_ids = np.random.randint(0, len(CATEGORIES), size=N_QUERIES)
query_noise = np.random.randn(N_QUERIES, DIM).astype("float32") * 0.5
queries = centers[query_category_ids] + query_noise
print(f"queries.shape = {queries.shape}")
```

Output:

```
vectors.shape = (50000, 128)
Category counts: [ 9907 10086  9836 10066 10105]
queries.shape = (20, 128)
```

Five cluster centers are drawn once; every stored vector is `center + noise`
for its assigned category, and so is every query. This matters: a query
embedding in a real system lands *near a cluster* (a question about
photosynthesis embeds near other biology documents), not at a uniformly
random point in 128-dimensional space. Using randomly-placed queries instead
would make even brute-force "nearest neighbors" nearly meaningless, since in
high dimensions a uniform random point is roughly equidistant from
everything.

```python
def brute_force_topk(vectors, query, k=10):
    diffs = vectors - query  # (N, D)
    dists = np.linalg.norm(diffs, axis=1)  # (N,)
    return np.argsort(dists)[:k]


start = time.perf_counter()
brute_force_results = [brute_force_topk(vectors, q, k=K) for q in queries]
elapsed = time.perf_counter() - start
print(f"Brute-force search for {N_QUERIES} queries took {elapsed*1000:.2f} ms "
      f"({elapsed/N_QUERIES*1000:.4f} ms/query)")
print(f"Top-{K} neighbors for query 0: {brute_force_results[0]}")
```

Output:

```
Brute-force search for 20 queries took 259.90 ms (12.9950 ms/query)
Top-10 neighbors for query 0: [24762  4281 29230 34062 48673 34101 35600  5390 24329 45167]
```

`brute_force_topk` is the entire algorithm: subtract the query from every
stored vector, take the L2 norm of each row, and `argsort` to find the
smallest. At ~13 ms/query for 50,000 vectors, this is the cost Section 2-3
are trying to avoid. `brute_force_results[0]`'s top-10 indices become the
ground truth that Section 3's recall calculations are measured against.

---

## 2. HNSW Intuition

```python
POINTS = {
    "A": np.array([0.0, 0.0]),
    "B": np.array([1.0, 5.0]),
    "C": np.array([9.0, 9.0]),
    "D": np.array([5.0, 5.0]),
    "E": np.array([8.0, 2.0]),
    "F": np.array([6.0, 0.5]),
}
QUERY = np.array([7.5, 1.5])


def dist_to_query(node):
    return float(np.linalg.norm(POINTS[node] - QUERY))


print("Distance from each point to the query Q = (7.5, 1.5):")
for node in POINTS:
    print(f"  {node} = {POINTS[node]}  dist(Q) = {dist_to_query(node):.3f}")

print("\nTrue nearest neighbor (brute force), sorted by distance:")
for node in sorted(POINTS, key=dist_to_query):
    print(f"  {node}: {dist_to_query(node):.3f}")

print("\nPairwise distances between points:")
names = list(POINTS.keys())
for a in names:
    row = "  ".join(f"{a}-{b}={np.linalg.norm(POINTS[a] - POINTS[b]):.2f}" for b in names if a != b)
    print(f"  {a}: {row}")
```

Output:

```
Distance from each point to the query Q = (7.5, 1.5):
  A = [0. 0.]  dist(Q) = 7.649
  B = [1. 5.]  dist(Q) = 7.382
  C = [9. 9.]  dist(Q) = 7.649
  D = [5. 5.]  dist(Q) = 4.301
  E = [8. 2.]  dist(Q) = 0.707
  F = [6.  0.5]  dist(Q) = 1.803

True nearest neighbor (brute force), sorted by distance:
  E: 0.707
  F: 1.803
  D: 4.301
  B: 7.382
  A: 7.649
  C: 7.649

Pairwise distances between points:
  A: A-B=5.10  A-C=12.73  A-D=7.07  A-E=8.25  A-F=6.02
  B: B-A=5.10  B-C=8.94  B-D=4.00  B-E=7.62  B-F=6.73
  C: C-A=12.73  C-B=8.94  C-D=5.66  C-E=7.07  C-F=9.01
  D: D-A=7.07  D-B=4.00  D-C=5.66  D-E=4.24  D-F=4.61
  E: E-A=8.25  E-B=7.62  E-C=7.07  E-D=4.24  E-F=2.50
  F: F-A=6.02  F-B=6.73  F-C=9.01  F-D=4.61  F-E=2.50
```

Every distance the rest of Section 2 relies on is printed here, computed from
the same six 2D points. `E` is the unambiguous true nearest neighbor (0.707,
less than half the next-closest distance of 1.803). The pairwise table is
what the markdown cell right after this one uses to justify each layer's
edges — nothing in the graph below is arbitrary; every edge is "the nearest
point(s) by this table."

```python
LAYERS = {
    0: {
        "A": {"B", "F"},
        "B": {"D", "A"},
        "C": {"D", "E"},
        "D": {"B", "E"},
        "E": {"F", "D"},
        "F": {"E", "D"},
    },
    1: {"C": {"D"}, "D": {"C", "F"}, "F": {"D"}},
    2: {"C": set()},
}


def greedy_search_layer(layer, entry):
    current = entry
    current_dist = dist_to_query(current)
    print(f"    start at {current} (dist={current_dist:.3f})")
    while True:
        candidates = [(n, dist_to_query(n)) for n in LAYERS[layer][current]]
        for n, d in candidates:
            print(f"    check neighbor {n} (dist={d:.3f})")
        if not candidates:
            print("    no neighbors at this layer -> stop")
            return current, current_dist
        best_node, best_dist = min(candidates, key=lambda c: c[1])
        if best_dist < current_dist:
            print(f"    -> move to {best_node} (dist={best_dist:.3f} < {current_dist:.3f})")
            current, current_dist = best_node, best_dist
        else:
            print(f"    -> no neighbor closer than {current} ({current_dist:.3f}); stop")
            return current, current_dist


print("=== HNSW greedy search for Q = (7.5, 1.5) ===")
print("\nLayer 2 (entry point):")
current, current_dist = "C", dist_to_query("C")
print(f"  entry = {current} (dist={current_dist:.3f}), no neighbors at layer 2 -> drop down")

print("\nLayer 1:")
current, current_dist = greedy_search_layer(1, current)
print(f"  -> layer 1 result: {current} (dist={current_dist:.3f})")

print("\nLayer 0:")
current, current_dist = greedy_search_layer(0, current)
print(f"  -> layer 0 result: {current} (dist={current_dist:.3f})")

print(f"\nHNSW final answer: {current} (dist={current_dist:.3f})")
true_nn = min(POINTS, key=dist_to_query)
print(f"Brute-force true nearest neighbor: {true_nn} (dist={dist_to_query(true_nn):.3f})")
print(f"Match: {current == true_nn}")
```

Output:

```
=== HNSW greedy search for Q = (7.5, 1.5) ===

Layer 2 (entry point):
  entry = C (dist=7.649), no neighbors at layer 2 -> drop down

Layer 1:
    start at C (dist=7.649)
    check neighbor D (dist=4.301)
    -> move to D (dist=4.301 < 7.649)
    check neighbor C (dist=7.649)
    check neighbor F (dist=1.803)
    -> move to F (dist=1.803 < 4.301)
    check neighbor D (dist=4.301)
    -> no neighbor closer than F (1.803); stop
  -> layer 1 result: F (dist=1.803)

Layer 0:
    start at F (dist=1.803)
    check neighbor D (dist=4.301)
    check neighbor E (dist=0.707)
    -> move to E (dist=0.707 < 1.803)
    check neighbor D (dist=4.301)
    check neighbor F (dist=1.803)
    -> no neighbor closer than E (0.707); stop
  -> layer 0 result: E (dist=0.707)

HNSW final answer: E (dist=0.707)
Brute-force true nearest neighbor: E (dist=0.707)
Match: True
```

`LAYERS` is a plain dict of `{layer: {node: set(neighbors)}}`, built directly
from the pairwise distances above (layer 0 = each node's 2 nearest
neighbors; layer 1 = the chain $C-D-F$; layer 2 = entry point $C$ alone).
`greedy_search_layer` is the entire HNSW search algorithm in ~10 lines: look
at the current node's neighbors in this layer, move to whichever is closest
to the query if that's an improvement, otherwise stop. The driver code runs
this once per layer from layer 2 down to layer 0, threading `current` and
`current_dist` through each call. Note that within `LAYERS[1]["D"] = {"C",
"F"}`, set iteration order isn't guaranteed — the printed order of `C` and
`F` as candidates can vary between runs, but `min(candidates, key=...)`
always picks `F` regardless of order, since $1.803 < 7.649$. The walk visits
$C \to D \to F \to E$ — 4 of 6 points — and lands on `E`, matching brute
force exactly.

---

## 3. FAISS Hands-On

```python
index_flat = faiss.IndexFlatL2(DIM)
index_flat.add(vectors)

start = time.perf_counter()
flat_dists, flat_ids = index_flat.search(queries, K)
flat_elapsed = time.perf_counter() - start
print("--- IndexFlatL2 (exact) ---")
print(f"Search time for {N_QUERIES} queries: {flat_elapsed*1000:.3f} ms "
      f"({flat_elapsed/N_QUERIES*1000:.4f} ms/query)")
print(f"Top-{K} neighbors for query 0: {flat_ids[0]}")

index_hnsw = faiss.IndexHNSWFlat(DIM, 32)
index_hnsw.hnsw.efConstruction = 40
index_hnsw.add(vectors)
index_hnsw.hnsw.efSearch = 16

start = time.perf_counter()
hnsw_dists, hnsw_ids = index_hnsw.search(queries, K)
hnsw_elapsed = time.perf_counter() - start
print("\n--- IndexHNSWFlat (approximate, M=32, efSearch=16) ---")
print(f"Search time for {N_QUERIES} queries: {hnsw_elapsed*1000:.3f} ms "
      f"({hnsw_elapsed/N_QUERIES*1000:.4f} ms/query)")
print(f"Top-{K} neighbors for query 0: {hnsw_ids[0]}")

recalls = [len(set(flat_ids[q]) & set(hnsw_ids[q])) / K for q in range(N_QUERIES)]
print(f"\nRecall@{K} (HNSW vs FlatL2 ground truth): "
      f"mean={np.mean(recalls):.3f}, min={np.min(recalls):.3f}, max={np.max(recalls):.3f}")
print(f"Speedup (flat ms/query / hnsw ms/query): {flat_elapsed / hnsw_elapsed:.2f}x")
```

Output:

```
--- IndexFlatL2 (exact) ---
Search time for 20 queries: 7.519 ms (0.3760 ms/query)
Top-10 neighbors for query 0: [24762  4281 29230 34062 48673 34101 35600  5390 24329 45167]

--- IndexHNSWFlat (approximate, M=32, efSearch=16) ---
Search time for 20 queries: 4.197 ms (0.2099 ms/query)
Top-10 neighbors for query 0: [ 4281 48673 34101 45167 34148 16313 27095 34658 28325 24995]

Recall@10 (HNSW vs FlatL2 ground truth): mean=0.585, min=0.400, max=0.700
Speedup (flat ms/query / hnsw ms/query): 1.79x
```

`IndexFlatL2`'s top-10 for query 0 matches `brute_force_results[0]` from
Section 1 exactly — same algorithm, just in optimized C++. `IndexHNSWFlat`'s
top-10 for query 0 shares only 2 of those 10 ids (`4281` and `45167`)
despite `query 0` and `DIM`/`vectors` being identical — this single query
happens to land near the low end of the recall distribution (`min=0.400`).
Across all 20 queries, HNSW recovers **58.5%** of the true top-10 on average
while running about **1.8x faster**.

```python
print(f"{'efSearch':>10} | {'recall@'+str(K):>10} | {'ms/query':>10}")
for ef in [4, 8, 16, 32, 64]:
    index_hnsw.hnsw.efSearch = ef
    start = time.perf_counter()
    _, ids = index_hnsw.search(queries, K)
    elapsed = time.perf_counter() - start
    recalls = [len(set(flat_ids[q]) & set(ids[q])) / K for q in range(N_QUERIES)]
    print(f"{ef:>10} | {np.mean(recalls):>10.3f} | {elapsed/N_QUERIES*1000:>10.4f}")
```

Output:

```
  efSearch |  recall@10 |   ms/query
         4 |      0.240 |     0.0998
         8 |      0.410 |     0.0181
        16 |      0.585 |     0.0222
        32 |      0.725 |     0.0336
        64 |      0.895 |     0.0509
```

Same graph (`index_hnsw` is not rebuilt), only `efSearch` changes between
rows. Recall climbs from 0.240 to 0.895 as `efSearch` goes from 4 to 64, with
`ms/query` increasing roughly proportionally (the `efSearch=4` row's 0.0998
ms is a one-off warm-up cost on the first call of the loop — every later row
is faster despite a larger `efSearch`, confirming it's not part of the real
trend).

**A note on reproducibility**: `IndexHNSWFlat`'s graph construction has
internal randomness that `np.random.seed(42)` does not control, so re-running
this notebook produces slightly different recall numbers each time (a
previous run measured `mean=0.530` at `efSearch=16` instead of `0.585`). The
*shape* of the tradeoff — recall increases monotonically with `efSearch`, at
a real but modest latency cost, and HNSW is meaningfully faster than
`IndexFlatL2` at this dataset size — is the stable, reproducible takeaway.

---

## 4. Embedded vs Server DBs (Exercise)

```python
__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
import chromadb

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

N_SUBSET = 2000
subset_vectors = vectors[:N_SUBSET]
subset_categories = [CATEGORIES[c] for c in category_ids[:N_SUBSET]]
subset_ids = [str(i) for i in range(N_SUBSET)]

print(f"Subset: {N_SUBSET} vectors, dim={DIM}")

chroma_client = chromadb.Client()
chroma_collection = chroma_client.create_collection(name="topic6_demo")
chroma_collection.add(
    ids=subset_ids,
    embeddings=subset_vectors.tolist(),
    metadatas=[{"category": c} for c in subset_categories],
)
print(f"Chroma collection size: {chroma_collection.count()}")

qdrant_client = QdrantClient(":memory:")
qdrant_client.create_collection(
    collection_name="topic6_demo",
    vectors_config=VectorParams(size=DIM, distance=Distance.EUCLID),
)
qdrant_client.upsert(
    collection_name="topic6_demo",
    points=[
        PointStruct(id=i, vector=subset_vectors[i].tolist(), payload={"category": subset_categories[i]})
        for i in range(N_SUBSET)
    ],
)
print(f"Qdrant collection size: {qdrant_client.count('topic6_demo').count}")
```

Output:

```
Subset: 2000 vectors, dim=128
Chroma collection size: 2000
Qdrant collection size: 2000
```

The Chroma sqlite3 shim (`pysqlite3-binary` swapped in for the stdlib
`sqlite3` module) must run *before* `import chromadb`, since Chroma checks the
sqlite3 version at import time. Both databases get the same 2,000 vectors
with the same `category` payload/metadata, loaded via each library's native
batch-insert API (`collection.add` for Chroma, `client.upsert` with a list of
`PointStruct` for Qdrant).

### Exercise solution — query both databases

```python
query_vec = queries[0].tolist()

chroma_result = chroma_collection.query(query_embeddings=[query_vec], n_results=5)
print("Chroma top-5:")
print(f"  ids:        {chroma_result['ids'][0]}")
print(f"  categories: {[m['category'] for m in chroma_result['metadatas'][0]]}")

qdrant_result = qdrant_client.query_points(collection_name="topic6_demo", query=query_vec, limit=5).points
print("\nQdrant top-5:")
print(f"  ids:        {[p.id for p in qdrant_result]}")
print(f"  categories: {[p.payload['category'] for p in qdrant_result]}")

chroma_ids = {int(i) for i in chroma_result["ids"][0]}
qdrant_ids = {p.id for p in qdrant_result}
print(f"\nSame top-5 ids: {chroma_ids == qdrant_ids}")
```

Output:

```
Chroma top-5:
  ids:        ['1629', '1773', '807', '1112', '1431']
  categories: ['cooking', 'cooking', 'cooking', 'cooking', 'cooking']

Qdrant top-5:
  ids:        [1629, 1773, 807, 1112, 1431]
  categories: ['cooking', 'cooking', 'cooking', 'cooking', 'cooking']

Same top-5 ids: True
```

Chroma returns ids as strings (`"1629"`), Qdrant returns the integer ids
passed to `PointStruct(id=i, ...)` — converting Chroma's to `int` before
comparing sets shows both databases agree exactly on the top-5, in the same
order, all from the `cooking` category. At 2,000 vectors both libraries'
default indices are effectively exact, so this is expected; the next section
is where the two diverge in behavior.

---

## 5. Metadata Filtering (Exercise)

### Exercise solution — reproduce the post-filtering failure mode

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

unfiltered = qdrant_client.query_points(collection_name="topic6_demo", query=query_vec, limit=5).points
print("Unfiltered top-5:")
for p in unfiltered:
    print(f"  id={p.id:5d}  category={p.payload['category']:8s}  score={p.score:.4f}")

unfiltered_categories = {p.payload["category"] for p in unfiltered}
TARGET_CATEGORY = next(c for c in CATEGORIES if c not in unfiltered_categories)
print(f"\nTARGET_CATEGORY = '{TARGET_CATEGORY}' (absent from unfiltered top-5: {unfiltered_categories})")

post_filtered = [p for p in unfiltered if p.payload["category"] == TARGET_CATEGORY]
print(f"\nPost-filter result count: {len(post_filtered)} (requested 5)")

pre_filtered = qdrant_client.query_points(
    collection_name="topic6_demo", query=query_vec,
    query_filter=Filter(must=[FieldCondition(key="category", match=MatchValue(value=TARGET_CATEGORY))]),
    limit=5,
).points
print(f"\nPre-filter result count: {len(pre_filtered)} (requested 5)")
for p in pre_filtered:
    print(f"  id={p.id:5d}  category={p.payload['category']:8s}  score={p.score:.4f}")
```

Output:

```
Unfiltered top-5:
  id= 1629  category=cooking   score=7.9029
  id= 1773  category=cooking   score=7.9700
  id=  807  category=cooking   score=7.9819
  id= 1112  category=cooking   score=8.0150
  id= 1431  category=cooking   score=8.0423

TARGET_CATEGORY = 'physics' (absent from unfiltered top-5: {'cooking'})

Post-filter result count: 0 (requested 5)

Pre-filter result count: 5 (requested 5)
  id=  296  category=physics   score=18.8173
  id=  727  category=physics   score=18.8318
  id=  244  category=physics   score=18.9898
  id= 1546  category=physics   score=19.0688
  id=  950  category=physics   score=19.1253
```

`query_vec` (from Section 4) happens to have its 5 globally nearest neighbors
*all* in the `cooking` category — `unfiltered_categories` is the single-element
set `{'cooking'}`. `TARGET_CATEGORY` is then chosen automatically as the first
category in `CATEGORIES` that is *not* `cooking` — here, `physics`.
Post-filtering the unfiltered top-5 down to `category == "physics"` keeps
**zero** results, even though `physics` documents exist in the collection (and
are found, all 5 of them, by the pre-filter). The pre-filtered results' scores
(~18.8-19.1) are much larger than the unfiltered results' scores (~7.9-8.0) —
these physics-category vectors are genuinely far from `query_vec` (which was
built near the `cooking` cluster center), they're just the *closest available
physics vectors*, which is exactly what "find the 5 nearest vectors where
category = physics" should mean.

---

## 6. Vector Quantization for Storage

```python
print(f"Dataset: {N_VECTORS} vectors, dim={DIM}")
flat_bytes_per_vector = DIM * 4  # float32
print(f"IndexFlatL2 baseline:   {flat_bytes_per_vector:4d} bytes/vector  (recall@{K} = 1.000)")

index_sq = faiss.IndexScalarQuantizer(DIM, faiss.ScalarQuantizer.QT_8bit)
index_sq.train(vectors)
index_sq.add(vectors)
_, sq_ids = index_sq.search(queries, K)
sq_recalls = [len(set(flat_ids[q]) & set(sq_ids[q])) / K for q in range(N_QUERIES)]
sq_bytes_per_vector = DIM * 1
print(f"IndexScalarQuantizer:   {sq_bytes_per_vector:4d} bytes/vector  "
      f"({flat_bytes_per_vector / sq_bytes_per_vector:.1f}x smaller)  "
      f"recall@{K} = {np.mean(sq_recalls):.3f}")

NBITS = 8
print("\nProduct quantization (PQ): more sub-vectors M = finer codes = better recall, less compression")
for M in [8, 16, 32, 64]:
    index_pq = faiss.IndexPQ(DIM, M, NBITS)
    index_pq.train(vectors)
    index_pq.add(vectors)
    _, pq_ids = index_pq.search(queries, K)
    pq_recalls = [len(set(flat_ids[q]) & set(pq_ids[q])) / K for q in range(N_QUERIES)]
    pq_bytes_per_vector = M * NBITS // 8
    print(f"  IndexPQ (M={M:2d}): {pq_bytes_per_vector:4d} bytes/vector  "
          f"({flat_bytes_per_vector / pq_bytes_per_vector:5.1f}x smaller)  "
          f"recall@{K} = {np.mean(pq_recalls):.3f}")

print(f"\nTotal index size for all {N_VECTORS} vectors:")
print(f"  IndexFlatL2:             {N_VECTORS * flat_bytes_per_vector / 1024:8.1f} KB")
print(f"  IndexScalarQuantizer:    {N_VECTORS * sq_bytes_per_vector / 1024:8.1f} KB")
print(f"  IndexPQ (M=64):          {N_VECTORS * pq_bytes_per_vector / 1024:8.1f} KB")
```

Output:

```
Dataset: 50000 vectors, dim=128
IndexFlatL2 baseline:    512 bytes/vector  (recall@10 = 1.000)
IndexScalarQuantizer:    128 bytes/vector  (4.0x smaller)  recall@10 = 0.980

Product quantization (PQ): more sub-vectors M = finer codes = better recall, less compression
  IndexPQ (M= 8):    8 bytes/vector  ( 64.0x smaller)  recall@10 = 0.055
  IndexPQ (M=16):   16 bytes/vector  ( 32.0x smaller)  recall@10 = 0.145
  IndexPQ (M=32):   32 bytes/vector  ( 16.0x smaller)  recall@10 = 0.350
  IndexPQ (M=64):   64 bytes/vector  (  8.0x smaller)  recall@10 = 0.760

Total index size for all 50000 vectors:
  IndexFlatL2:              25000.0 KB
  IndexScalarQuantizer:      6250.0 KB
  IndexPQ (M=64):            3125.0 KB
```

`flat_ids` (Section 3's `IndexFlatL2` ground truth) is reused here as the
recall baseline for every quantized index, so all recall numbers in this
notebook are comparable against the same ground truth. `IndexScalarQuantizer`
with `QT_8bit` needs a `.train()` call to learn each dimension's value range
before `.add()`; `IndexPQ` needs `.train()` to run k-means for each
sub-vector's codebook. The PQ loop sweeps $M \in \{8, 16, 32, 64\}$ — each
doubling of $M$ halves the compression ratio and roughly doubles (or more)
the recall, from 0.055 at $M=8$ (64x smaller than `IndexFlatL2`) to 0.760 at
$M=64$ (8x smaller). `IndexScalarQuantizer`'s 4x compression at 0.980 recall
is a far better operating point than any of the PQ configurations tested
here — for this dataset, SQ8 is close to "free" compression, while PQ is a
much steeper tradeoff.
