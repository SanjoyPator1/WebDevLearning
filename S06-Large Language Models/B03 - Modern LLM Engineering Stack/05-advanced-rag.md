# Topic 5 — Advanced RAG

## Why This Topic

B02 chapter 8 covers basic semantic search and RAG: embed a query, do
nearest-neighbor lookup, stuff results into a prompt. By 2026, production RAG
goes well beyond this single-shot pattern — hybrid search, reranking,
query rewriting, agentic retrieval (the model decides *whether* and *what* to
retrieve, possibly in multiple rounds), and graph-based retrieval (GraphRAG)
for multi-hop questions over connected entities.

## Prerequisites

B02 chapter 8 (semantic search & RAG). Topic 1 helps for chain composition;
Topic 2 helps for agentic retrieval (a retrieval loop is naturally a graph).

## Outline

1. **Limits of Naive RAG** — concrete failure cases: queries needing exact
   keyword matches (naive embeddings miss them), multi-hop questions (answer
   spans two non-adjacent chunks), and irrelevant-but-similar chunks drowning
   out the right one.
2. **Hybrid Search** — combining BM25 (sparse/keyword) with dense embedding
   search, and fusing results with **Reciprocal Rank Fusion (RRF)**; dry-run
   RRF on a tiny example with 3 documents from each retriever.
3. **Reranking** — using a cross-encoder reranker (e.g. a small
   `bge-reranker` model) as a second-pass filter over the top-k hybrid
   results; why cross-encoders are more accurate but too slow to run on the
   whole corpus.
4. **Query Transformation** — query rewriting/expansion (HyDE: generate a
   hypothetical answer, embed *that* instead of the raw query) and multi-query
   retrieval (generate N paraphrased queries, union the results).
5. **Agentic RAG** — wrapping retrieval as a *tool* the model can call
   zero-to-many times (reusing Topic 2's graph pattern), so the model decides
   when it has enough context vs needs another retrieval round.
6. **GraphRAG (Overview + Mini Implementation)** — building a small knowledge
   graph from a handful of documents (entities + relations extracted by an
   LLM), then answering a multi-hop question by traversing the graph instead
   of (or in addition to) vector search.

## Planned Deliverables

- `code/template/advanced-rag.ipynb` — sections 1-4 fully built on a small
  custom corpus (reuse text from your B01/B02 notes as the corpus — meta but
  useful); **exercise cells** for section 5 (agentic RAG graph) and section 6
  (mini GraphRAG over ~10 sentences).
- `code/solutions/` — copy of the template.
- `notes/05-advanced-rag.md` — RRF dry-run table, plus an ASCII pipeline
  diagram comparing naive RAG vs hybrid+rerank vs agentic RAG.
