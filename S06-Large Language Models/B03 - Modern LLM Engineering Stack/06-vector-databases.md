# Topic 6 — Vector Databases

## Why This Topic

Topic 5 treats the vector store as a black box ("top-k similarity search").
This topic opens that box: how does approximate nearest-neighbor search
actually work at scale (HNSW graphs), how do metadata filters interact with
vector search, and what are the practical differences between an in-memory
index (FAISS), an embedded DB (Chroma), and a server-based DB (Qdrant)?

## Prerequisites

B02 chapter 8 (embeddings basics) and Topic 5 (why hybrid/filtered search
matters).

## Outline

1. **From Brute-Force to ANN** — exact nearest-neighbor (brute-force cosine
   similarity, what you likely did in B02) vs **Approximate Nearest Neighbor
   (ANN)**; the recall/speed tradeoff.
2. **HNSW Intuition** — Hierarchical Navigable Small World graphs: layered
   graph structure, greedy search from the top layer down. Build a *tiny*
   HNSW-like graph by hand (5-6 points in 2D) and manually trace a search.
3. **FAISS Hands-On** — `IndexFlatL2` (exact) vs `IndexHNSWFlat` (approximate)
   on the same dataset; measure recall and latency difference.
4. **Embedded vs Server DBs** — Chroma (embedded, good for prototyping) vs
   Qdrant (server-based, production features: payload filtering, sharding,
   quantization of the vectors themselves).
5. **Metadata Filtering** — pre-filtering vs post-filtering vs the
   "filterable HNSW" approach Qdrant uses; why naive post-filtering can return
   too few (or zero) results.
6. **Vector Quantization for Storage** — scalar/product quantization to
   shrink index memory footprint, and the accuracy tradeoff (connects forward
   to Topic 9's model quantization, same underlying idea applied to vectors
   instead of weights).

## Planned Deliverables

- `code/template/vector-databases.ipynb` — sections 1-3 fully built (FAISS
  flat vs HNSW benchmark on a synthetic dataset); **exercise cells** for
  section 4-5 (load the same data into Chroma and Qdrant, implement a filtered
  query in each, compare results).
- `code/solutions/` — copy of the template.
- `notes/06-vector-databases.md` — the by-hand HNSW dry-run from section 2,
  plus a comparison table (FAISS vs Chroma vs Qdrant: persistence, filtering,
  scaling, ease of setup).
