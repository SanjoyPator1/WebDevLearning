# Chapter 8: Semantic Search and Retrieval-Augmented Generation

## Hands-On Large Language Models — Chapter 8

> Search was the first killer application of language models, and RAG is the technique that tames their greatest weakness — hallucination — by grounding every answer in retrieved facts.

---

## Table of Contents

1. [Overview: The Three Pillars of LLM-Powered Search](#1-overview-the-three-pillars-of-llm-powered-search)
2. [Dense Retrieval](#2-dense-retrieval)
   - [2a. The Geometry of Meaning](#2a-the-geometry-of-meaning)
   - [2b. The Search Pipeline](#2b-the-search-pipeline)
   - [2c. Dense Retrieval Example — Cohere + FAISS](#2c-dense-retrieval-example--cohere--faiss)
   - [2d. Dense vs. Keyword Search (BM25)](#2d-dense-vs-keyword-search-bm25)
   - [2e. Caveats of Dense Retrieval](#2e-caveats-of-dense-retrieval)
   - [2f. Chunking Long Texts](#2f-chunking-long-texts)
   - [2g. Nearest Neighbor Search vs. Vector Databases](#2g-nearest-neighbor-search-vs-vector-databases)
   - [2h. Fine-Tuning Embedding Models for Retrieval](#2h-fine-tuning-embedding-models-for-retrieval)
3. [Reranking](#3-reranking)
   - [3a. Why Rerankers Exist](#3a-why-rerankers-exist)
   - [3b. How Reranking Models Work — Cross-Encoders](#3b-how-reranking-models-work--cross-encoders)
   - [3c. Reranking Example — Cohere Rerank API](#3c-reranking-example--cohere-rerank-api)
4. [Retrieval Evaluation Metrics](#4-retrieval-evaluation-metrics)
   - [4a. The Test Suite](#4a-the-test-suite)
   - [4b. Precision@k](#4b-precisionk)
   - [4c. Average Precision — Single Query](#4c-average-precision--single-query)
   - [4d. Mean Average Precision (MAP)](#4d-mean-average-precision-map)
   - [4e. nDCG — When Relevance is Graded](#4e-ndcg--when-relevance-is-graded)
5. [Retrieval-Augmented Generation (RAG)](#5-retrieval-augmented-generation-rag)
   - [5a. The Hallucination Problem and the RAG Solution](#5a-the-hallucination-problem-and-the-rag-solution)
   - [5b. Grounded Generation — The Core RAG Pipeline](#5b-grounded-generation--the-core-rag-pipeline)
   - [5c. Example — RAG with the Cohere API](#5c-example--rag-with-the-cohere-api)
   - [5d. Example — Local RAG with Phi-3 + FAISS + LangChain](#5d-example--local-rag-with-phi-3--faiss--langchain)
   - [5e. Advanced RAG Techniques](#5e-advanced-rag-techniques)
   - [5f. Modern RAG Techniques (2024–2025)](#5f-modern-rag-techniques-20242025)
6. [RAG Evaluation](#6-rag-evaluation)
   - [6a. Why RAG is Hard to Evaluate](#6a-why-rag-is-hard-to-evaluate)
   - [6b. The Four Axes of Generative Search Evaluation](#6b-the-four-axes-of-generative-search-evaluation)
   - [6c. LLM-as-a-Judge](#6c-llm-as-a-judge)
   - [6d. The Ragas Library](#6d-the-ragas-library)
7. [Key Takeaways](#7-key-takeaways)

---

## 1. Overview: The Three Pillars of LLM-Powered Search

Months after the publication of the original BERT paper in 2018, Google announced it was using transformer models to power Google Search, calling it "one of the biggest leaps forward in the history of Search." Microsoft Bing followed with similar announcements. The reason these mature, billion-user systems benefited so dramatically from language models is a capability called **semantic search** — the ability to retrieve documents by meaning rather than by exact word matching. A keyword search engine can find the word "science" in a document. A semantic search system understands that the phrase "how precise was the science" is asking about scientific accuracy, even if no document uses those exact words.

On a separate track, the rise of generative LLMs created a new problem. These models answer questions fluently and confidently — but they sometimes answer incorrectly, confabulating facts that sound plausible but are false. This is called **hallucination**, and it is one of the most serious reliability concerns in deployed AI systems. The leading remedy is to build a system that can first retrieve the relevant information from a trusted source, and then pass that information to the LLM as context so it can generate a grounded, factual answer. This method is called **Retrieval-Augmented Generation**, or RAG.

This chapter covers the three major paradigms at the intersection of language models and search:

```
User Query
    │
    ├─► [Dense Retrieval] ─────────────► Top-k documents
    │    (embedding similarity)           (ranked by vector distance)
    │
    ├─► [Reranking] ──────────────────► Reordered shortlist
    │    (cross-encoder relevance)        (higher quality order)
    │
    └─► [RAG] ────────────────────────► Grounded answer + citations
         (retrieval + generation)         (LLM reads the retrieved docs)
```

Dense retrieval and reranking are both **search systems** — they return a ranked list of documents. RAG is a **generation system** — it goes one step further and produces a synthesised answer from those documents. In practice, all three are often combined: dense retrieval shortlists candidates, a reranker re-orders them, and an LLM reads the top results to generate the final answer.

---

## 2. Dense Retrieval

### 2a. The Geometry of Meaning

Recall from earlier chapters that an **embedding model** converts text into a high-dimensional vector — a list of numbers. These vectors are not arbitrary. The embedding model is trained so that texts with similar meanings produce vectors that are close together in that high-dimensional space, while texts with unrelated meanings produce vectors that are far apart.

Think of it like a city map, except instead of geography, the map encodes meaning. On this map, "puppy" and "dog" are in the same neighbourhood. "Kitten" and "cat" are nearby. "Accounting" and "tax return" cluster together on the other side of the city. "Interstellar" and "Christopher Nolan" are close together, far away from "accounting." The embedding model has learned this layout purely from patterns in text — no human designed it.

This geometric property is exactly what makes search possible. If a user asks "how precise was the science in that Nolan film?", we can embed that question into the same map. We then ask: which stored document vectors are closest to this query vector? Those are the most semantically similar documents — the best search results. We are not looking for documents that contain the words "precise" or "science." We are looking for documents that live in the same neighbourhood as the question.

```
                 Embedding Space (2D projection for illustration)

        [Text 2: Kip Thorne was a scientific consultant]
                         ●
                         
   [Text 1: Interstellar              [Query: how precise was the science?]
   is a 2014 sci-fi film]                         ●
            ●

                                                         [Text 3: The film
                                                         grossed $677 million]
                                                                   ●

→ Query is nearest to Text 2 (scientific accuracy topic)
→ Semantic search returns Text 2 as the top result
→ Keyword search would have returned Text 1 (shares the word "science")
```

The key insight is that **the query and all documents live in the same vector space**. The search operation is simply a distance calculation in that shared space.

---

### 2b. The Search Pipeline

A dense retrieval system has two phases: an **indexing phase** (done once, offline) and a **query phase** (done live, per request).

During indexing, you take your entire document corpus, break it into manageable chunks, embed each chunk using an embedding model, and store all those vectors in a search index. The index is an optimised data structure for finding nearest vectors quickly.

During querying, you take the user's search query, embed it using the same embedding model, and ask the index to return the chunk vectors that are nearest to the query vector. Those chunks are your search results.

```
────────── INDEXING PHASE (done once) ──────────

  Documents
      │
      ▼
  [Chunker] ─── split long docs into sentences / paragraphs / windows
      │
      ▼
  [Embedding Model] ─── each chunk becomes a dense vector
      │
      ▼
  [Vector Index] ─── store all chunk vectors, optimised for nearest-neighbour search

────────── QUERY PHASE (per request) ──────────

  User Query (text)
      │
      ▼
  [Embedding Model] ─── same model, same vector space
      │
      ▼
  [Nearest Neighbour Search] ─── find the stored vectors closest to the query vector
      │
      ▼
  Top-k Retrieved Chunks ─── returned as search results
```

The crucial constraint is that the **same embedding model** must be used for both indexing and querying. If you embed documents with model A and the query with model B, the vectors live in different spaces and distance calculations are meaningless.

---

### 2c. Dense Retrieval Example — Cohere + FAISS

The book demonstrates dense retrieval using the Wikipedia article about the film *Interstellar* as the document corpus. The four steps are:

**Step 1 — Get the text and chunk it into sentences.**

```python
text = """
Interstellar is a 2014 epic science fiction film co-written, directed, and produced by Christopher Nolan.
...
"""
# Split on periods to get individual sentences
texts = text.split('.')
# Clean up whitespace and newlines
texts = [t.strip(' \n') for t in texts]
```

Each sentence becomes one searchable chunk. This gives 15 sentences — 15 future vectors.

**Step 2 — Embed the sentences using Cohere's embedding API.**

```python
response = co.embed(
    texts=texts,
    input_type="search_document",   # ← tells Cohere these are docs, not queries
).embeddings

embeds = np.array(response)
print(embeds.shape)  # (15, 4096) — 15 sentences, each a 4096-dim vector
```

The `input_type` distinction matters. Cohere's embedding model has two modes: `search_document` for indexing and `search_query` for queries. This asymmetry is intentional — the model was fine-tuned to make query vectors geometrically compatible with document vectors even when they phrase things differently.

**Step 3 — Build the FAISS search index.**

```python
import faiss

dim = embeds.shape[1]           # 4096
index = faiss.IndexFlatL2(dim)  # L2 = Euclidean distance
index.add(np.float32(embeds))   # add all 15 document vectors
```

`IndexFlatL2` is the simplest FAISS index — it stores all vectors and computes exact Euclidean distance to find the nearest neighbours. "Flat" means no compression or approximation; "L2" means the distance metric is squared Euclidean:

$$d(u, v) = \|u - v\|^2 = \sum_{i} (u_i - v_i)^2$$

**Step 4 — Define a search function and query the index.**

```python
def search(query, number_of_results=3):
    # Embed the query using the query-mode input type
    query_embed = co.embed(
        texts=[query],
        input_type="search_query",
    ).embeddings[0]

    # Ask FAISS for the nearest document vectors
    distances, similar_item_ids = index.search(
        np.float32([query_embed]),
        number_of_results
    )

    # Format and return results
    texts_np = np.array(texts)
    results = pd.DataFrame({
        'texts': texts_np[similar_item_ids[0]],
        'distance': distances[0]
    })
    print(f"Query: '{query}'\nNearest neighbors:")
    return results

results = search("how precise was the science")
```

The output is striking. The top result is *"It has also received praise from many astronomers for its scientific accuracy and portrayal of theoretical astrophysics"* — which perfectly answers the question, despite sharing zero keywords with the query. This would be **impossible** with keyword search.

---

### 2d. Dense vs. Keyword Search (BM25)

To understand why dense retrieval is powerful, you need to see it compared to the alternative. **BM25** (Best Match 25) is the dominant keyword search algorithm and the engine behind most traditional search systems. It is not explained in the book, but you will see it in the code, so it deserves a clear explanation here.

BM25 is essentially a smarter version of word counting. For a given query, it asks two questions about each document: (1) How many of the query words appear in this document? and (2) How rare are those words across the whole corpus? Common words like "the" or "is" are down-weighted (they appear everywhere, so they carry little signal). Rare words like "astrophysics" are up-weighted (their presence strongly suggests relevance). The formula combines these factors to produce a relevance score.

The critical limitation of BM25 is that it is **purely lexical** — it only cares about exact word matches. It has no concept of meaning. If you search for "how precise was the science," BM25 has no idea that "precise" is related to "accurate" or that "science" in the query means "scientific accuracy." It will retrieve documents that happen to contain the word "science," regardless of context.

The results for the same query using BM25 confirm this:

```
Input question: how precise was the science
Top-3 lexical (BM25) hits:
  1.789  Interstellar is a 2014 epic science fiction film co-written...
  1.373  Caltech theoretical physicist and 2017 Nobel laureate in Physics[4] Kip Thorne...
  0.000  It stars Matthew McConaughey, Anne Hathaway...
```

Result #1 scored highest because it contains the word "science" — but it is talking about the genre "science fiction," not scientific accuracy. This is a classic false positive caused by keyword matching. Dense retrieval avoids this entirely by operating in meaning-space rather than word-space.

```
Pure Keyword (BM25):   Finds exact words.      Misses synonyms. Confused by context.
Pure Dense:            Finds meaning.          Misses exact phrases. Slower to index.
─────────────────────────────────────────────────────────────────────────────────────
Hybrid (both):         Best of both worlds.    Most production systems use this.
```

The hybrid approach runs both systems and combines their scores. It is the recommended approach for production search systems.

---

### 2e. Caveats of Dense Retrieval

Dense retrieval is powerful but not perfect. There are five important failure modes to understand.

**The no-answer problem.** If the corpus does not contain the answer to a query, the retrieval system will still return results — the nearest vectors it has, even if they are not actually relevant. A query like "What is the mass of the moon?" directed at the Interstellar article will return sentences about the film, because those are the nearest vectors available, despite being completely irrelevant. The standard mitigation is a **threshold**: if the nearest-neighbour distance exceeds some maximum, return no results rather than irrelevant ones. But choosing the right threshold is a design challenge specific to each system.

**Exact phrase matching.** If a user searches for "Christopher Nolan," a keyword search will find that exact string instantly. Dense retrieval, by contrast, might retrieve documents about "film directors" or "modern cinema" rather than the exact name, depending on how the embeddings were trained. This is why hybrid search — combining keyword and dense retrieval — outperforms either approach alone. For entity search and exact-match queries, keyword search remains superior.

**Domain mismatch.** Embedding models are trained on specific datasets. A model trained on Wikipedia and web text will not represent legal contracts or medical literature in the same geometric space. If you deploy a Wikipedia-trained embedding model on legal text without fine-tuning, the nearest-neighbour relationships will be less reliable. Whenever possible, fine-tune or select an embedding model trained on data similar to your target domain.

**Multi-sentence answers.** Dense retrieval retrieves individual chunks. If the answer to a question is spread across multiple sentences that happen to land in different chunks, no single chunk will contain the full answer. This is a fundamental limitation of chunk-level retrieval, and it is one of the reasons chunking strategy (covered next) matters so much.

**The hubness problem.** In high-dimensional embedding spaces, certain sentences become *hubs* — points that are geometrically close to a disproportionately large number of query vectors. These hub sentences crowd out more specific, relevant sentences by winning the nearest-neighbour race for almost every query, even when they are not the best answer.

The intuition is straightforward. Hub sentences tend to be generic, central descriptions of the topic — the kind of sentence that is "about everything and nothing specific." Because they sit near the centroid of the embedding cloud, they are naturally close to every query that shares the topic. Specific sentences — the ones that actually answer a particular question — sit further from the centroid and get buried.

*Concrete example from our Interstellar RAG system.* The corpus contains 39 sentences about Interstellar. Three of them are hubs:

```
Index  1: "Interstellar is a 2014 epic science fiction film directed by Christopher Nolan."
Index 15: "Interstellar received positive reviews from critics, who praised its ambition, visual effects, and performances."
Index 35: "Interstellar premiered at the TCL Chinese Theatre in Hollywood on October 26, 2014."
```

These three sentences dominated the top-3 results for every query we tested — "Who directed Interstellar?", "How much money did Interstellar make?", "Did Interstellar win any awards?", "What was special about the black hole?" — regardless of what the question was actually asking.

The sentence that actually answers "How much money did Interstellar make?" is:

```
Index 16: "The film grossed over 701 million dollars worldwide against a production budget of 165 million dollars."
```

With k=3, index 16 never appeared — the three hubs always won. Its distance from the query was 0.853, while the hubs sat at 0.512, 0.521, and 0.561. With k=10, index 16 appeared at rank 4 and the LLM could answer correctly.

The standard mitigations are:

- **Increase k** — retrieve more candidates so specific sentences can break through. The tradeoff is that you pass more noise to the LLM.
- **Two-stage retrieval** — use BM25 as a first stage. BM25 is immune to hubness because it matches keywords, not geometry. The box office sentence contains "701 million" and "grossed" — BM25 retrieves it immediately for a money-related query. The cross-encoder reranker then selects the best result from the BM25 candidates.
- **Better embedding models** — models fine-tuned specifically for retrieval (like `bge`, `e5`, or Cohere's `embed-v3`) are trained to push query vectors toward their specific answers, not just toward topic-central sentences. This directly reduces hubness.

---

### 2f. Chunking Long Texts

Transformer embedding models have a **context window limit** — they cannot process more tokens than their maximum context length. Models like BERT top out at 512 tokens; even longer models have limits. This means you cannot simply embed an entire multi-page document as one vector. You must break it into smaller pieces first.

This process is called **chunking**, and it is not as simple as it sounds. Chunking strategy directly affects retrieval quality. A poor chunking approach can make a great embedding model useless; a good chunking approach can make a mediocre embedding model perform well. It deserves serious thought.

#### One Vector Per Document

The simplest approach is to produce a single vector that represents the whole document. There are two ways to do this. The first is to embed only a representative part — typically the title or the opening paragraph. This is fast and easy, but it leaves most of the document unindexed and therefore unsearchable. If the relevant information is buried in paragraph eight, it will never be retrieved.

The second approach is to chunk the document, embed all chunks, and then aggregate those vectors into one — typically by averaging. The averaged vector is technically compact and complete, but it suffers from **information dilution**. Averaging the vectors of "Kip Thorne was a scientific consultant" and "The film grossed $677 million" produces a vector that represents neither concept cleanly. The resulting soup-vector is a poor representative of either specific fact.

#### Multiple Vectors Per Document

The better approach — and the one used in practice — is to index each chunk as its own separate vector. The search index then contains chunk embeddings, not document embeddings. Retrieval returns the most relevant chunks, which can be traced back to their source documents. This approach has full coverage and preserves the specificity of individual concepts.

The question becomes: how do you define a chunk?

**Character splitting** divides the text every N characters regardless of word boundaries. It is the crudest method and should be avoided — it cuts words mid-stream.

```
Input:   "Llama 2 was trained on 40% more data than Llama 1"

Character split (every 15 characters):
  [Llama 2 was tra] [ined on 40% mor] [e data than Lla] [ma 1]
   ← "trained" is cut in half: terrible for meaning
```

**Token splitting** divides the text every N tokens, which respects word boundaries because tokenizers operate at the subword level.

```
Token split (every 5 tokens, no overlap):
  [Llama 2 was trained on] [40% more data than] [Llama 1]
   ← clean cuts, but what about context?
```

This is cleaner, but it introduces the **boundary problem**. Imagine that the answer to a question spans the junction between two chunks. Neither chunk alone contains the full answer. A query about "Llama 2's training data size relative to Llama 1" would need to see both the "40% more data" chunk and the "than Llama 1" chunk together — but they were split apart.

**Token splitting with overlap** solves this by repeating some tokens in adjacent chunks.

```
Token split (every 5 tokens, 1 token overlap):
  [Llama 2 was trained on]
                         [on 40% more data than]   ← "on" repeated
                                              [than Llama 1]   ← "than" repeated
   ← shared tokens bridge the gaps, preserving local context
```

The overlap acts like a zipper — adjacent chunks share a small region of text, ensuring that no meaning is completely lost at the boundary.

#### Semantic Chunking Strategies

Beyond the mechanical split methods, there are semantically-motivated strategies:

**Sentence-level chunks** treat each sentence as one chunk. This is very granular, which means high precision on specific facts — but each chunk lacks the surrounding context that gives a sentence its full meaning. "It stars Matthew McConaughey" is ambiguous without knowing the subject is Interstellar.

**Paragraph-level chunks** are the sweet spot for most use cases. Paragraphs are natural units of thought — they typically discuss one idea — so a paragraph chunk has both specificity and sufficient context.

**Overlapping window chunks** extend the overlapping-token idea to sentences: chunk N includes the last sentence of chunk N-1 and the first sentence of chunk N+1. This is especially effective for dense, information-rich text where sentence boundaries frequently break apart related ideas.

```
Document pages (represented as coloured blocks):

Sentence-level:   [S1][S2][S3][S4][S5][S6]...
                  very granular, many tiny vectors, lacks context

Paragraph-level:  [S1 S2 S3][S4 S5 S6]...
                  fewer, richer vectors, better for most queries

Overlapping:      [S1 S2 S3][S2 S3 S4][S3 S4 S5]...
                  ↑ S2 S3  ↑ S3 S4  ← overlap preserves boundary context
```

The right chunking strategy depends on your data and your query patterns. Short-answer factual queries benefit from fine-grained chunks. Summarisation queries benefit from larger chunks. As the field matures, LLMs are increasingly being used to perform **semantic chunking** — letting the model itself decide where one idea ends and another begins, rather than using mechanical rules.

---

### 2g. Nearest Neighbor Search vs. Vector Databases

Once you have embedded your chunks, you need to find the nearest vectors to a query efficiently. The right approach depends on scale.

For small archives — up to a few tens of thousands of vectors — brute-force search with NumPy is perfectly adequate. You compute the dot product (or L2 distance) between the query vector and every stored vector, then sort:

```python
# Brute force: works fine for small archives
similarities = np.dot(query_vector, archive_vectors.T)
top_k_indices = np.argsort(similarities)[::-1][:k]
```

For archives in the millions, this becomes too slow. **Approximate Nearest Neighbour (ANN)** libraries like FAISS (Facebook AI Similarity Search) and Annoy (Spotify) solve this by trading a tiny amount of accuracy for massive speed. Instead of computing distance to every stored vector, they partition the vector space into regions — like neighbourhoods on a map — and only search the relevant neighbourhood when a query comes in. FAISS can serve results from an index of a billion vectors in milliseconds, and it supports GPU acceleration, which makes it very well-suited to environments like yours with an A6000.

For production systems that need to add and delete vectors without rebuilding the entire index, and that need additional features like metadata filtering, **vector databases** like Weaviate, Pinecone, and Qdrant are the right tool. A vector database allows you to say things like "find the 10 nearest vectors to this query, but only among documents tagged with category='legal' and uploaded after 2023-01-01." This kind of filtered semantic search is not possible with a raw FAISS index.

| Scale | Approach | Tools |
|-------|----------|-------|
| < 100K vectors | Brute-force (exact) | NumPy, scikit-learn |
| Millions | Approximate Nearest Neighbour | FAISS, Annoy |
| Production (CRUD + filtering) | Vector Database | Weaviate, Pinecone, Qdrant |

---

### 2h. Fine-Tuning Embedding Models for Retrieval

Off-the-shelf embedding models are trained to produce similar vectors for semantically similar text — but "similar" during pre-training usually means paraphrases and entailments. A query and its relevant answer are often not paraphrases. "When was Interstellar released?" and "Interstellar premiered on October 26, 2014" are not paraphrases — they are a question and its answer — but a retrieval system needs to recognise them as highly related.

To fix this, embedding models can be **fine-tuned for retrieval** using training data composed of (query, relevant document, irrelevant document) triplets. The fine-tuning process applies a **contrastive loss** that pulls the query vector closer to the relevant document vector and pushes it further from the irrelevant document vector.

Consider three possible queries for the sentence "Interstellar premiered on October 26, 2014, in Los Angeles":

- Relevant query 1: "Interstellar release date"
- Relevant query 2: "When did Interstellar premiere?"
- Irrelevant query: "Interstellar cast"

Before fine-tuning, all three queries might have similar distances to the target sentence, because they all discuss Interstellar and the general embedding model has no concept of "what answers what."

```
BEFORE FINE-TUNING:
  Vector space
  ┌───────────────────────────────────────────┐
  │  ● [release date query]                   │
  │                  ● [Interstellar premiered...]  │ ← document
  │  ● [when did it premiere?]                │
  │  ● [cast query]                           │
  │  All roughly equidistant from document    │
  └───────────────────────────────────────────┘

AFTER FINE-TUNING:
  ┌───────────────────────────────────────────┐
  │● [release date]● [when premiere?]         │
  │  ● [Interstellar premiered...]            │ ← relevant queries pulled close
  │                                           │
  │                      ● [cast query]       │ ← irrelevant pushed away
  └───────────────────────────────────────────┘
```

After fine-tuning, the embedding space is reorganised so that answerable queries cluster tightly around their relevant documents. This is why specialised retrieval models (like Cohere's `embed-v3` or BAAI's `bge` series) significantly outperform general-purpose embedding models on search tasks — they have been explicitly trained on this query-document geometry. Chapter 10 of this book covers the fine-tuning process in full detail.

---

## 3. Reranking

### 3a. Why Rerankers Exist

Dense retrieval is fast because embedding is a one-time operation: you embed every document once during indexing, and at query time you only need to embed the query and do a vector search. This speed is its great strength. But it is also a limitation: because the query and each document are embedded *independently* and then compared by simple distance, the model never directly sees the query and document side by side. It cannot reason about their specific relationship.

A **reranker** solves this by reading the query and each candidate document together and producing a relevance score that reflects their specific relationship. This is dramatically more accurate than embedding-based similarity, but it cannot be pre-computed — you must run the model for every (query, document) pair at query time. This makes rerankers too slow to run on millions of documents, but fast enough to run on a shortlist of dozens or hundreds.

The standard architecture is a **two-stage pipeline**: a fast first-stage retriever (keyword, dense, or hybrid) that shortlists perhaps 100 candidates, followed by a slower, more accurate reranker that re-orders those 100 into a final top-k ranking.

```
Text archive (millions of documents)
         │
         ▼
  ┌──────────────────┐     100 candidates
  │  First Stage:    │ ──────────────────► ┌──────────────────┐     Top-5 final results
  │  Dense/Keyword   │                     │  Second Stage:   │ ────────────────────────►
  │  Search          │ ◄── Query           │  Reranker        │ ◄── Query
  └──────────────────┘                     └──────────────────┘
    Fast, broad                               Slow, precise
    O(log n) search                           O(k) cross-encoder passes
```

Reranking is the technique Microsoft Bing added on top of its existing search infrastructure to achieve significant quality improvements — it did not replace the existing search; it added a second stage.

---

### 3b. How Reranking Models Work — Cross-Encoders

To understand rerankers, you must understand the architectural difference between a **bi-encoder** and a **cross-encoder**.

The embedding model used for dense retrieval is a **bi-encoder**: it encodes the query and the document through the *same* model architecture but as *separate inputs*, producing two independent vectors. The similarity score is computed as a distance between these two vectors after encoding. The advantage is that document encodings can be pre-computed and cached. The disadvantage is that the model never sees the query and document at the same time — it cannot reason about their specific relationship.

```
BI-ENCODER (Dense Retrieval):

  [Query text] ──► [Encoder] ──► q_vec ──┐
                                          ├── cosine_sim(q_vec, d_vec) → score
  [Doc text]   ──► [Encoder] ──► d_vec ──┘

  Documents can be pre-encoded offline → FAST at query time
  But: model never sees query and doc together → less nuanced
```

A **cross-encoder** (used in reranking) takes the query and the document as a *single concatenated input*. The model attends to both texts simultaneously — every word in the query can attend to every word in the document through the transformer's self-attention layers. This allows the model to reason about the specific relationship between the question and the answer, not just their general similarity.

```
CROSS-ENCODER (Reranker / monoBERT):

  [Query text | [SEP] | Doc text] ──► [Encoder] ──► relevance_score (0 to 1)

  Model sees query and doc together → high accuracy
  But: cannot pre-encode documents → must re-encode per query → SLOW
```

The cross-encoder formulation is essentially a **classification problem**: given this (query, document) pair, output a number between 0 (completely irrelevant) and 1 (highly relevant). **MonoBERT** is the name of the famous BERT-based cross-encoder reranker described in the "Multi-stage document ranking with BERT" paper, which established this two-stage retrieval-then-rerank paradigm as the industry standard.

The reason rerankers improve results so dramatically is that they can notice things embedding-based similarity cannot. For example, a dense retriever might give a high score to a document that uses similar vocabulary to the query but actually answers a different question. A cross-encoder, reading both texts together, will recognise the mismatch and score it lower.

#### The Math

**Bi-encoder scoring** (what you built in Part 1):

$$\text{score}_{\text{bi}}(q, d) = \cos\!\left(\mathbf{E}(q),\ \mathbf{E}(d)\right) = \frac{\mathbf{E}(q) \cdot \mathbf{E}(d)}{\|\mathbf{E}(q)\|\,\|\mathbf{E}(d)\|}$$

| Symbol | Meaning |
|--------|---------|
| $q$ | query text |
| $d$ | document text |
| $\mathbf{E}(\cdot)$ | encoder that maps text to a fixed-size vector |
| $\mathbf{E}(q)$ | query vector (e.g. shape `[384]`) |
| $\mathbf{E}(d)$ | document vector (pre-computed, stored in FAISS) |
| $\cos(\cdot, \cdot)$ | cosine similarity — dot product divided by both norms |

*Note: FAISS uses L2 distance rather than cosine similarity, but the idea is the same — a single number computed from two independent vectors.*

**Cross-encoder scoring** (the reranker):

$$\text{score}_{\text{cross}}(q, d) = f_\theta\!\left([\texttt{CLS}\ q\ \texttt{SEP}\ d\ \texttt{SEP}]\right)$$

| Symbol | Meaning |
|--------|---------|
| $[\texttt{CLS}\ q\ \texttt{SEP}\ d\ \texttt{SEP}]$ | query and document concatenated into one token sequence |
| $f_\theta$ | transformer encoder + linear layer, with learned weights $\theta$ |
| $\text{score}_{\text{cross}}$ | a single scalar relevance score (higher = more relevant) |

The critical difference: in the bi-encoder, $\mathbf{E}(q)$ and $\mathbf{E}(d)$ are computed independently — they never interact inside the model. In the cross-encoder, every token in $q$ can attend to every token in $d$ through transformer self-attention before the score is produced. This is where the precision gain comes from.

#### Dry-Run with Tiny Numbers

Imagine a 2-token query and a 3-token document, simplified to show the attention interaction:

```
Input sequence to cross-encoder:
  [CLS]  precise  science  [SEP]  accurate  simulation  [SEP]
    0       1        2       3        4           5        6

Self-attention (simplified — each token attends to all others):

  Token "precise"  (pos 1) attends to:
    → "accurate"   (pos 4)  — HIGH attention weight  (synonyms)
    → "simulation" (pos 5)  — LOW attention weight
    → "science"    (pos 2)  — MEDIUM attention weight

  Token "science"  (pos 2) attends to:
    → "simulation" (pos 5)  — MEDIUM attention weight
    → "accurate"   (pos 4)  — MEDIUM attention weight

After all attention layers, [CLS] (pos 0) aggregates:
  → rich signal that "precise" ↔ "accurate" are semantically linked
  → Linear layer maps [CLS] vector → scalar score

  score = sigmoid(w · CLS_vector + b) ≈ 0.89   ← high relevance

Now run the same query against a different document:
  [CLS]  precise  science  [SEP]  fiction  film  [SEP]

  Token "precise" attends to:
    → "fiction" — LOW attention weight  (no semantic link)
    → "film"    — LOW attention weight

  [CLS] aggregates weak cross-attention → score ≈ 0.12   ← low relevance
```

The bi-encoder would have given both documents a moderate score because both contain the word "science." The cross-encoder correctly separates them because it saw that "precise" has a strong semantic link to "accurate" but not to "fiction."

---

### 3c. Reranking Example — Cohere Rerank API

Cohere offers a managed reranking endpoint that requires no training or tuning. You pass a query and a list of documents, and it returns relevance scores.

```python
query = "how precise was the science"

# Pass query + all 15 document texts to the reranker
results = co.rerank(
    query=query,
    documents=texts,
    top_n=3,
    return_documents=True
)

# Print results with relevance scores
for idx, result in enumerate(results.results):
    print(idx, result.relevance_score, result.document.text)
```

Output:

```
0  0.1698  It has also received praise from many astronomers for its scientific
           accuracy and portrayal of theoretical astrophysics
1  0.0700  The film had a worldwide gross over $677 million...
2  0.0044  Caltech theoretical physicist and 2017 Nobel laureate in Physics[4]...
```

The reranker assigns a score of 0.17 to the top result and less than 0.01 to the others — it is very confident in its ranking. Notice that result #1 by the reranker is the same result that dense retrieval found. This is reassuring. But the order of positions 2 and 3 has changed, and in a production system with 1000 candidates instead of 15, the reranker's ability to discriminate between subtle relevance differences would be far more consequential.

**Combining keyword search with reranking** is where the two-stage pipeline really shines. BM25 retrieves 10 candidates (even though its top result was poor), and the reranker re-orders them:

```python
def keyword_and_reranking_search(query, top_k=3, num_candidates=10):
    # Stage 1: BM25 retrieves 10 candidates
    bm25_scores = bm25.get_scores(bm25_tokenizer(query))
    top_n = np.argpartition(bm25_scores, -num_candidates)[-num_candidates:]
    bm25_hits = sorted([{'corpus_id': idx, 'score': bm25_scores[idx]}
                        for idx in top_n], key=lambda x: x['score'], reverse=True)

    # Stage 2: reranker re-orders the 10 BM25 results
    docs = [texts[hit['corpus_id']] for hit in bm25_hits]
    results = co.rerank(query=query, documents=docs, top_n=top_k, return_documents=True)
    return results
```

On the MIRACL multilingual retrieval benchmark, adding a reranker to a BM25 first stage improves nDCG@10 from 36.5 to 62.8 — a dramatic improvement from a single additional model call.

---

## 4. Retrieval Evaluation Metrics

### 4a. The Test Suite

Start with the real problem: you build two search systems and you want to know which one is better. How do you measure that? You need three things — and together they form the **test suite**.

**Thing 1 — The Archive (the library)**

A fixed collection of documents that the search system will operate on. Think of it as a library that never changes during evaluation:

```
Archive:
  Doc #1 — "Interstellar is a 2014 sci-fi film"
  Doc #2 — "Kip Thorne was the scientific consultant"
  Doc #3 — "The film grossed $677 million"
  Doc #4 — "Christopher Nolan directed the film"
  Doc #5 — "The science was praised by astronomers"
  Doc #6 — "Anne Hathaway stars in the film"
```

**Thing 2 — The Queries (the exam questions)**

A set of questions that represent what real users would actually search for:

```
Query 1 — "how precise was the science?"
Query 2 — "who directed the film?"
```

**Thing 3 — Relevance Judgments (the answer key)**

A human sits down and manually marks: for each query, which documents are actually relevant answers? This is done once, by hand, and then frozen.

```
              Query 1   Query 2
  Doc #1   →    ✗         ✗
  Doc #2   →    ✓         ✗    ← Kip Thorne relevant to "science precision"
  Doc #3   →    ✗         ✗
  Doc #4   →    ✗         ✓    ← Nolan relevant to "who directed"
  Doc #5   →    ✓         ✗    ← astronomers relevant to "science precision"
  Doc #6   →    ✗         ✗
```

This grid is the answer key. It never changes. Now you can grade any search system: give it Query 1, look at what it returns, check those results against the answer key. Did it return Doc #2 and Doc #5? Good. Did it return Doc #1 instead? Bad.

```
Test Suite  =  Archive  +  Queries  +  Relevance Judgments
            =  library  +  questions  +  human-labeled answer key
```

The test suite is the fixed benchmark — both systems get the same archive, the same queries, and are graded against the same answer key. MAP and nDCG (sections 4b–4d) are simply the formulas for computing the grade from those results.

Creating relevance judgments is expensive — it requires humans to read every (query, document) pair and label it. This is why standard benchmark datasets like MS MARCO, BEIR, and MIRACL are so valuable: they provide pre-built test suites with thousands of queries and relevance judgments, enabling fair apples-to-apples comparison across different retrieval systems.

---

### 4b. Precision@k

#### The Real-World Analogy First

Imagine you ask a librarian for books about "deep learning." She brings you a stack of 5 books. You check each one — 3 are exactly what you wanted, 2 are completely off-topic. She got 3 out of 5 right.

That ratio — *how many of the returned results were actually useful* — is exactly what **Precision@k** measures. The `k` is simply how many results you asked for ("bring me the top 5 books").

```
Librarian returns 5 books (k = 5):
  Book 1 → ✓ relevant
  Book 2 → ✓ relevant
  Book 3 → ✗ not relevant
  Book 4 → ✓ relevant
  Book 5 → ✗ not relevant

Precision@5 = 3 relevant out of 5 returned = 3/5 = 0.6
```

#### The Formula

$$\text{Precision@k} = \frac{\text{number of relevant documents in top-k results}}{k}$$

| Symbol | Meaning |
|--------|---------|
| $k$ | How many top results we look at (the cutoff) |
| numerator | Count of truly relevant documents among those top-k |
| denominator | Always $k$ — even if only 1 result was relevant |

This says: *"Of the top k things the system showed you, what fraction were actually useful?"*

#### Dry-Run — Same Results, Different k

Using the same 5 returned books from above (✓ ✓ ✗ ✓ ✗):

```
Precision@1 = 1/1 = 1.0   → top 1 result: Book 1 is relevant  → perfect
Precision@2 = 2/2 = 1.0   → top 2 results: both relevant       → perfect
Precision@3 = 2/3 = 0.67  → top 3 results: 2 of 3 relevant
Precision@4 = 3/4 = 0.75  → top 4 results: 3 of 4 relevant
Precision@5 = 3/5 = 0.60  → top 5 results: 3 of 5 relevant
```

Notice Precision@k can go up or down as k increases — it depends on whether the next result is relevant or not.

#### Why Precision@k Alone Is Not Enough

Here is the catch. Consider two search systems, both returning 3 results for Query 1, with only 1 relevant document in the entire archive:

```
System A results:  [✓, ✗, ✗]   → Precision@3 = 1/3 = 0.33
System B results:  [✗, ✗, ✓]   → Precision@3 = 1/3 = 0.33
```

Both score **identically** on Precision@3. But System A put the relevant result at position 1 — the user sees it immediately. System B buried it at position 3 — the user has to scroll past two bad results first. Intuitively System A is much better. Precision@k cannot see this difference at all.

This is exactly why Average Precision exists — it rewards putting relevant results higher up.

---

### 4c. Average Precision — Single Query

#### The Problem We Are Solving

We just saw that Precision@k is blind to *where* relevant results appear. System A returning `[✓, ✗, ✗]` and System B returning `[✗, ✗, ✓]` both score Precision@3 = 0.33, even though System A is clearly better — it put the good result first.

**Average Precision (AP)** fixes this. The core idea is simple: instead of measuring precision once at the end, measure precision *at every position where a relevant document appears*, then average those snapshots. A relevant result at position 1 contributes a high precision value (1.0); a relevant result at position 3 contributes a low precision value (0.33). Systems that rank relevant documents early earn higher scores.

Think of it like a teacher grading an essay on a rolling basis. She marks a tick every time she hits a good paragraph. The earlier the good paragraphs appear, the higher the score. An essay where all the good paragraphs are at the beginning is better than one where they are all at the end — even if both essays have the same number of good paragraphs in total.

#### The Recipe (How to Compute AP Step by Step)

Before the formula, here is the algorithm in plain English:

```
Step 1 — Look at each position in your results list, one by one.
Step 2 — When you hit a relevant document, compute Precision@k at that position.
         (ignore irrelevant documents — just skip them)
Step 3 — Collect all those precision values into a list.
Step 4 — Average them by dividing by R (total relevant docs that EXIST for this query,
         not just the ones you found — missing docs penalise you too).
```

#### The Formula

$$\text{AP} = \frac{1}{R} \sum_{k=1}^{n} \text{Precision@k} \times \mathbb{1}[\text{doc}_k \text{ is relevant}]$$

| Symbol | Meaning |
|--------|---------|
| $R$ | Total relevant documents that exist for this query in the test suite |
| $n$ | Total number of results returned |
| $\text{Precision@k}$ | Precision computed at position $k$ |
| $\mathbb{1}[\text{doc}_k \text{ is relevant}]$ | 1 if position $k$ is a relevant doc, 0 if not — this is what makes us skip irrelevant positions |

This says: *"At every position where you placed a relevant document, note down the precision. Average those notes. Divide by how many relevant documents exist in total."*

#### Dry-Run 1 — One Relevant Document, at Position 1 (Perfect)

```
Setup:
  Total relevant docs that exist for this query: R = 1
  Results returned:  Position 1 → ✓   Position 2 → ✗   Position 3 → ✗

Walk the list:
  Position 1: RELEVANT → compute Precision@1 = (1 relevant so far) / 1 = 1.0  ← record this
  Position 2: not relevant → skip
  Position 3: not relevant → skip

Collected precision values: [1.0]
AP = sum / R = 1.0 / 1 = 1.0

→ Perfect score. The one relevant doc was shown first.
```

#### Dry-Run 2 — One Relevant Document, Buried at Position 3 (Penalty)

```
Setup:
  Total relevant docs that exist: R = 1
  Results returned:  Position 1 → ✗   Position 2 → ✗   Position 3 → ✓

Walk the list:
  Position 1: not relevant → skip
  Position 2: not relevant → skip
  Position 3: RELEVANT → compute Precision@3 = (1 relevant so far) / 3 = 0.33  ← record this

Collected precision values: [0.33]
AP = 0.33 / 1 = 0.33

→ The system found the right document, but made the user scroll past 2 bad results first.
  AP penalises this: 0.33 vs 1.0 for the same document found earlier.
```

This is the key power of AP: both systems found exactly 1 relevant document, but the one that ranked it higher scores 3× better.

#### Dry-Run 3 — Two Relevant Documents (Matches Book Figure 8-22)

```
Setup:
  The archive has exactly 2 relevant docs for this query → R = 2
  Results returned:  Position 1 → ✓   Position 2 → ✗   Position 3 → ✓

Walk the list:
  Position 1: RELEVANT → Precision@1 = (1 relevant so far) / 1 = 1/1 = 1.0  ← record
  Position 2: not relevant → skip
  Position 3: RELEVANT → Precision@3 = (2 relevant so far) / 3 = 2/3 = 0.67  ← record

Collected precision values: [1.0, 0.67]
AP = (1.0 + 0.67) / R = 1.67 / 2 = 0.84

→ R = 2 because 2 relevant docs exist in the archive. Divide by 2. That is all.
```

One important consequence of dividing by $R$ (the total that exist) rather than by the number of relevant docs you actually returned: a system that misses relevant documents is always penalised, even if every document it did return was ranked perfectly. This is intentional — AP measures both ranking quality *and* coverage of the relevant set.

#### Dry-Run 4 — Why the Denominator Must Be `len(relevant_ids)`, Not "Relevant Retrieved"

Dry-Runs 1, 2, and 3 have a subtle blind spot: in each case, every relevant document that exists in the archive was also retrieved. So dividing by R and dividing by "how many relevant docs you found" happen to give the same number. You cannot tell from those examples which one is correct.

This dry-run breaks that coincidence on purpose.

```
Setup:
  Archive has 5 relevant docs total → R = 5
  relevant_ids = {5, 6, 7, 10, 11}
  Retrieved list: [5, 0, 6]
  (docs 7, 10, 11 are relevant but were never retrieved — the system missed them)

Walk the list:
  Position 1: doc 5 is RELEVANT → P@1 = (1 relevant so far) / 1 = 1/1 = 1.0  ← record
  Position 2: doc 0 not relevant → skip
  Position 3: doc 6 is RELEVANT → P@3 = (2 relevant so far) / 3 = 2/3 = 0.67  ← record

Collected precision values: [1.0, 0.67]
num_sum = 1.67
relevant retrieved = 2   (only docs 5 and 6 were found)
R = 5                    (docs 5, 6, 7, 10, 11 all exist)

WRONG: AP = 1.67 / 2 = 0.83  ← pretends the system did a great job
RIGHT: AP = 1.67 / 5 = 0.33  ← correctly penalises missing 3 relevant docs
```

The system ranked its two retrieved relevant documents well, but it missed three entirely. Dividing by the number of relevant docs retrieved would reward it with 0.83 — almost perfect. Dividing by R = 5 gives 0.33, which reflects reality: this system found only 40% of what was relevant. That penalty is the whole point of the formula.

In code this means the denominator is always `len(relevant_ids)`, never the count of how many relevant docs appeared in the retrieved list.

---

### 4d. Mean Average Precision (MAP)

#### The Problem AP Alone Does Not Solve

AP gives you one score per query. But a search system is tested on many queries — maybe 100, maybe 10,000. System A might be great at Query 1 but terrible at Query 37. System B might be average on everything. Which is the better system overall?

You need a single number that summarises performance across all queries. **Mean Average Precision (MAP)** is that number — it is simply the arithmetic mean of the AP scores across every query in the test suite.

Think of it like a student's GPA. Each exam is one query, the exam score is the AP for that query, and the GPA (MAP) is the average across all exams. A student who scored 100 on one exam and 0 on all others has a low GPA — just as a search system that nails one query but fails the rest gets a low MAP.

#### The Formula

$$\text{MAP} = \frac{1}{|Q|} \sum_{q \in Q} \text{AP}(q)$$

| Symbol | Meaning |
|--------|---------|
| $\|Q\|$ | Total number of queries in the test suite |
| $\text{AP}(q)$ | The Average Precision score for query $q$ |

This says: *"Compute AP for every query. Add them all up. Divide by the number of queries."*

#### Dry-Run — MAP Across Three Queries (Matches Book Figure 8-23)

Step 1: Compute AP for each query individually, using the steps from section 4c.

```
Query 1 — "how precise was the science?"
  Archive has R = 2 relevant docs.
  Results returned: [✓, ✗, ✓]
  Position 1: RELEVANT → Precision@1 = 1/1 = 1.0  ← record
  Position 2: not relevant → skip
  Position 3: RELEVANT → Precision@3 = 2/3 = 0.67  ← record
  AP = (1.0 + 0.67) / 2 = 0.84

Query 2 — "who directed the film?"
  Archive has R = 1 relevant doc.
  Results returned: [✓, ✗, ✗]
  Position 1: RELEVANT → Precision@1 = 1/1 = 1.0  ← record
  AP = 1.0 / 1 = 1.0

Query 3 — "what did the film gross?"
  Archive has R = 1 relevant doc.
  Results returned: [✗, ✗, ✓]
  Position 1: not relevant → skip
  Position 2: not relevant → skip
  Position 3: RELEVANT → Precision@3 = 1/3 = 0.33  ← record
  AP = 0.33 / 1 = 0.33
```

Step 2: Average the three AP scores.

```
MAP = (AP_q1 + AP_q2 + AP_q3) / |Q|
    = (0.84  +  1.0  +  0.33) / 3
    = 2.17 / 3
    = 0.72
```

Step 3: Read what the number tells you.

```
Query 1  AP = 0.84  → good, found both relevant docs, one slightly late
Query 2  AP = 1.0   → perfect, the only relevant doc was returned first
Query 3  AP = 0.33  → poor, buried the only relevant doc at position 3

MAP = 0.72  → the system is solid overall but has a weak spot on query 3
```

MAP gives you one number you can use to compare any two search systems on the same test suite. The system with the higher MAP is better — across all queries, weighted equally.

*Why is it called "mean average precision" when mean and average mean the same thing?* It is a historical naming quirk from the information retrieval literature. MAP became the standard and no one changed it.

---

### 4e. nDCG — When Relevance is Graded

#### The Problem MAP Cannot Solve

MAP treats every relevant document equally — a document is either relevant (1) or not (0). But in real search, relevance is not binary. Ask "best Python libraries for NLP" and you might get:

```
Doc A — a comprehensive tutorial covering spaCy, HuggingFace, NLTK in depth   → very relevant
Doc B — a Stack Overflow answer mentioning spaCy in one line                   → somewhat relevant
Doc C — a blog post about Python web frameworks                                → not relevant
```

With MAP, Doc A and Doc B would both be labelled "1" and treated as equal. But clearly Doc A is a much better result. MAP has no way to express this difference. A metric that can say "Doc A is more relevant than Doc B" is more informative.

#### What nDCG Does

**nDCG (Normalized Discounted Cumulative Gain)** solves this with two ideas working together:

**Idea 1 — Graded relevance scores.** Instead of 0 or 1, each document in the test suite gets a relevance grade — for example 0 (not relevant), 1 (somewhat relevant), or 2 (highly relevant). These grades are assigned by human evaluators.

```
Doc A → grade 2  (highly relevant)
Doc B → grade 1  (somewhat relevant)
Doc C → grade 0  (not relevant)
```

**Idea 2 — Position discount.** Just like AP, nDCG rewards putting the best results at the top. But instead of computing precision at each position, it divides each document's relevance gain by the logarithm of its rank — so results lower down the list contribute less and less.

```
Position 1 discount:  log₂(1+1) = log₂(2) = 1.0    ← no penalty, this is the top
Position 2 discount:  log₂(2+1) = log₂(3) = 1.585  ← slightly penalised
Position 3 discount:  log₂(3+1) = log₂(4) = 2.0    ← more penalised
Position 5 discount:  log₂(5+1) = log₂(6) = 2.585  ← even more
Position 10 discount: log₂(10+1)           = 3.459  ← heavily penalised
```

A highly relevant document (grade 2) at position 10 contributes far less than the same document at position 1. This is the "discounted" part of DCG.

**The "Normalized" part** means the raw DCG score is divided by the ideal DCG — the score you would get if the human evaluator's perfect ranking (best docs first) was exactly what the system returned. This normalisation brings the final score between 0 and 1, making it easy to compare across queries with different numbers of relevant documents.

```
nDCG = DCG (what your system scored)
       ─────────────────────────────
       IDCG (what a perfect system would score)

nDCG = 1.0  → your system returned results in the perfect order
nDCG = 0.0  → your system got everything completely wrong
```

#### When to Use MAP vs nDCG

| Situation | Use |
|-----------|-----|
| Relevance is binary (relevant / not relevant) | MAP |
| Relevance is graded (highly / somewhat / not relevant) | nDCG |
| You care about position and ranking quality | Both do this |

The reranker benchmark result mentioned in the book — BM25 improving from 36.5 to 62.8 after adding a reranker — is measured in **nDCG@10**, meaning nDCG computed over the top 10 results. Chapter 10 uses nDCG extensively when evaluating and comparing embedding models on the MTEB leaderboard.

---

## 5. Retrieval-Augmented Generation (RAG)

### 5a. The Hallucination Problem and the RAG Solution

LLMs are trained on text from the internet, books, and other sources. After training, their knowledge is **frozen**. Ask a model trained in early 2023 about a news event from late 2023, and it genuinely does not know — but it may still produce a confident, fluent, and completely fabricated answer. This phenomenon is called **hallucination**, and it is not a bug that can be easily patched; it is an inherent consequence of how generative language models work. The model learns to produce plausible-sounding text, and plausible is not the same as true.

The foundational paper proposing RAG — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020) — framed the solution cleanly: instead of asking the model to answer from memory, give it the relevant documents and ask it to answer from those documents. The model's generation capability is now grounded in retrieved evidence, not in fuzzy parametric knowledge.

Think of it this way. Imagine asking a brilliant professor a detailed question about a recent court case. If she answers from memory, she might be wrong — law is complex and cases blur together over time. But if you hand her the case files before she answers, her answer will be grounded, specific, and accurate. Her role shifts from *memory* to *comprehension and synthesis*. RAG performs the same shift for language models: it transforms the LLM from a memory-retrieval system into a reading-comprehension system.

#### Dry-Run: Hallucination vs. Grounded Answer

The contrast between a bare LLM and a RAG-augmented LLM on the same question is stark:

```
Question: "What did Interstellar gross at the worldwide box office?"

─── WITHOUT RAG (LLM answers from training memory) ───────────────────
Prompt sent to LLM:
  "What did Interstellar gross at the worldwide box office?"

LLM output:
  "Interstellar grossed approximately $675 million worldwide."
  ← Plausible, but imprecise. The actual number is $677 million.
     The model is guessing from vague training memory.

─── WITH RAG (LLM answers from retrieved context) ─────────────────────
Stage 1 — Retrieval finds this chunk from the archive:
  "The film had a worldwide gross over $677 million (and $773 million
   with subsequent re-releases), making it the tenth-highest grossing
   film of 2014."

Stage 2 — Prompt sent to LLM:
  "Relevant information:
   The film had a worldwide gross over $677 million (and $773 million
   with subsequent re-releases), making it the tenth-highest grossing
   film of 2014.

   Answer this question: What did Interstellar gross at the worldwide
   box office?"

LLM output:
  "Interstellar grossed over $677 million worldwide, or $773 million
   including subsequent re-releases." [Source: doc_0]
  ← Exact, cited, verifiable. The LLM read it, not remembered it.
```

The LLM did not get smarter. It got a cheat sheet. That is the entire insight behind RAG.

---

### 5b. Grounded Generation — The Core RAG Pipeline

A RAG system has two stages: **retrieval** and **grounded generation**.

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                    RAG SYSTEM                           │
│                                                         │
│  ┌──────────────────────────────┐                       │
│  │  STAGE 1: Retrieval          │                       │
│  │  Dense/keyword/hybrid search │◄── Data Source        │
│  │  Returns top-k chunks        │    (vector database,  │
│  └──────────────┬───────────────┘     document store)   │
│                 │ relevant chunks                       │
│                 ▼                                       │
│  ┌──────────────────────────────┐                       │
│  │  STAGE 2: Grounded Generation│                       │
│  │                              │                       │
│  │  Prompt:                     │                       │
│  │  "Relevant information:      │                       │
│  │   {retrieved_chunks}         │                       │
│  │   Answer this question:      │                       │
│  │   {user_question}"           │                       │
│  │                              │                       │
│  │  LLM reads and synthesises   │                       │
│  └──────────────┬───────────────┘                       │
│                 │                                       │
└─────────────────┼───────────────────────────────────────┘
                  ▼
          Answer + [1][2][3] source citations
```

The generation step is called **grounded generation** because the retrieved documents establish a ground — a factual context — that the LLM is instructed to reason within. A well-designed RAG system also has the LLM cite which retrieved chunks support each claim, giving the user a way to verify the answer.

#### Why Context Stuffing Works — The Attention Mechanism View

You might wonder: why does simply pasting documents into the prompt make the LLM more accurate? The answer lies in how transformer attention works. When the LLM processes the full prompt, every token in the prompt can attend to every other token. The retrieved document text becomes part of the LLM's active working memory for that call — every word in the question can attend to every word in the retrieved context. The LLM is not "remembering" facts; it is *reading* them in real time through its attention mechanism.

#### The "Lost in the Middle" Problem

Research has shown that LLMs attend more strongly to information at the **beginning and end** of a long context window, and tend to "lose" information buried in the middle. This is called the **lost-in-the-middle** problem (Liu et al., 2023). It has a direct practical consequence for RAG prompt design:

```
GOOD prompt layout:
  [Retrieved context]      ← model reads this first, attends well
  [User question]          ← model reads this last, attends well

BAD prompt layout:
  [User question]
  [Retrieved context]      ← buried in the middle after a long question
  [More instructions]      ← model attends here, but context is fading
```

This is why every RAG prompt template you will see places `{context}` before `{question}`. It is not arbitrary — it is a known performance optimization.

This also enables the **"chat with your data"** use case: a company can embed its internal documentation, product manuals, or knowledge base into a vector store, and employees can query it conversationally. The LLM answers from the company's own documents, not from general internet knowledge.

---

### 5c. Example — RAG with the Cohere API

Cohere's managed API makes RAG straightforward. The `co.chat()` endpoint accepts a `documents` parameter — if you pass retrieved documents, the model will use them as grounded context and return citations alongside its answer.

```python
query = "income generated"

# Stage 1: Retrieval — use the embedding search from earlier
results = search(query)

# Stage 2: Grounded Generation — pass query + retrieved docs to Cohere chat
docs_dict = [{'text': text} for text in results['texts']]
response = co.chat(
    message=query,
    documents=docs_dict   # ← the grounding context
)
print(response.text)
```

Output:

```
The film generated a worldwide gross of over $677 million, or $773 million
with subsequent re-releases.
```

#### What Cohere Actually Sends to the LLM

Internally, Cohere assembles a prompt that looks roughly like this before calling its LLM:

```
The following SEARCH RESULTS may be useful when answering the user's question.

SEARCH RESULT [doc_0]:
The film had a worldwide gross over $677 million (and $773 million with
subsequent re-releases), making it the tenth-highest grossing film of 2014.

SEARCH RESULT [doc_1]:
Interstellar is a 2014 epic science fiction film...

USER QUESTION: income generated
ANSWER:
```

The LLM generates the answer and simultaneously tracks which spans of which `doc_N` it used. That tracking is returned to you as **citations**.

#### Understanding the Citation Object

```python
citations=[
  ChatCitation(start=21, end=36, text='worldwide gross',
               document_ids=['doc_0']),
  ChatCitation(start=40, end=57, text='over $677 million',
               document_ids=['doc_0'])
]
```

- `start` and `end` are character offsets in the *generated answer text* — they identify exactly which words in the output came from a source
- `document_ids=['doc_0']` links those words back to the first document you passed in (`docs_dict[0]`)
- This lets you build a UI that highlights cited text and links it to source documents — the same feature you see in Perplexity, Bing AI, and Google AI Overview

This citation mechanism is what separates grounded generation from standard generation. The system can tell you exactly which source each fact came from, enabling fact-checking and auditability.

**When to use managed API vs local models:**

| Factor | Managed API (Cohere) | Local (Phi-3 + FAISS) |
|--------|---------------------|----------------------|
| Setup complexity | Minimal | More setup |
| Cost | Per-API-call billing | Free after hardware |
| Data privacy | Data sent to Cohere | Stays on your machine |
| Citation quality | Built-in, high quality | Manual via prompt |
| Performance | Excellent | Good, limited by model size |

---

### 5d. Example — Local RAG with Phi-3 + FAISS + LangChain

For users who need to run RAG entirely locally — for privacy, cost, or customisation reasons — the book demonstrates a full local RAG pipeline. Understanding each component and why it was chosen is as important as understanding the code.

**Component 1 — The Generation Model: Phi-3-mini**

```python
from langchain import LlamaCpp

llm = LlamaCpp(
    model_path="Phi-3-mini-4k-instruct-fp16.gguf",
    n_gpu_layers=-1,    # -1 = offload ALL layers to GPU (your A6000 handles this easily)
    max_tokens=500,     # max tokens the model can generate in its answer
    n_ctx=2048,         # context window: retrieved docs + question must fit within this
    seed=42,
    verbose=False
)
```

**Why Phi-3-mini specifically?** Microsoft's Phi-3-mini is an *instruction-tuned* model, meaning it was trained to follow instructions like "answer the question using only the provided context." A base (non-instruction-tuned) model would just continue generating text without following your RAG prompt format. Additionally, at 3.8B parameters, it fits comfortably in GPU VRAM even at fp16 precision, making it practical for local inference.

**Why fp16 quantization?** At fp16 (16-bit floats), the model uses roughly half the VRAM of fp32 with near-identical answer quality. The GGUF format stores quantized weights efficiently for llama.cpp. The `n_ctx=2048` sets how many tokens fit in the context window — this budget must cover the retrieved documents AND the question AND the generated answer. Keep this in mind when tuning chunk sizes.

**Component 2 — The Embedding Model: bge-small**

```python
from langchain.embeddings.huggingface import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(
    model_name='thenlper/gte-small'
)
```

**Why bge-small?** The BAAI/bge family of models consistently ranks at the top of the MTEB (Massive Text Embedding Benchmark) leaderboard for retrieval tasks. Crucially, they are trained on *retrieval* data — query-document pairs — not just paraphrase data. This means the model knows that "income generated" (query style) should retrieve "The film had a worldwide gross over $677 million" (document style), even though they phrase the same fact differently. The `-small` variant keeps inference fast and the model small enough to run alongside the generation model.

**Component 3 — The Vector Store: FAISS**

```python
from langchain.vectorstores import FAISS

# Indexing phase — done once before any queries
db = FAISS.from_texts(texts, embedding_model)
```

`FAISS.from_texts` embeds every text chunk using `embedding_model` and stores all vectors in a FAISS index. When you later call `db.as_retriever()`, it returns a LangChain `Retriever` object that, by default, fetches the **top-4 nearest neighbours** (`k=4`) for any query. You can change this: `db.as_retriever(search_kwargs={"k": 6})` for top-6.

**Component 4 — The RAG Prompt Template**

```python
from langchain import PromptTemplate

template = """<|user|>
Relevant information:
{context}

Provide a concise answer the following question using the relevant information
provided above:
{question}<|end|>
<|assistant|>"""

prompt = PromptTemplate(
    template=template,
    input_variables=["context", "question"]
)
```

**Prompt Dry-Run — What the LLM Actually Sees**

When you call `rag.invoke('Income generated')`, LangChain retrieves the top-4 chunks from FAISS, concatenates them, fills the template, and sends this to Phi-3:

```
<|user|>
Relevant information:
The film had a worldwide gross over $677 million (and $773 million with
subsequent re-releases), making it the tenth-highest grossing film of 2014.

Interstellar premiered on October 26, 2014, in Los Angeles.

It was produced by Paramount Pictures and Warner Bros. Pictures.

Caltech theoretical physicist Kip Thorne was an executive producer and
scientific consultant on the film.

Provide a concise answer the following question using the relevant information
provided above:
Income generated<|end|>
<|assistant|>
```

Phi-3 reads this whole string, attends to all four retrieved chunks, and generates the answer after `<|assistant|>`. The `{context}` slot is filled by the concatenated chunks. The `{question}` slot is filled by your query. Everything else is the static template.

**Component 5 — The RetrievalQA Chain and chain_type**

```python
from langchain.chains import RetrievalQA

rag = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type='stuff',
    retriever=db.as_retriever(),
    chain_type_kwargs={"prompt": prompt},
    verbose=True
)

rag.invoke('Income generated')
```

The `chain_type` parameter determines how retrieved documents are handled if there are many of them:

| chain_type | How it works | When to use |
|------------|-------------|-------------|
| `'stuff'` | Concatenate ALL retrieved chunks into one prompt | Small corpora, short chunks, context fits in window |
| `'map_reduce'` | Run LLM once per chunk to summarise, then combine summaries | Many long chunks, need to stay within context limit |
| `'refine'` | Start with first chunk answer, iteratively refine with each next chunk | When answer quality matters more than speed |

For the Interstellar example with 15 short sentences, `'stuff'` is correct — all chunks fit comfortably in the 2048-token context window.

---

### 5e. Advanced RAG Techniques

Basic RAG is a single-shot retrieval + generation pipeline. For more complex real-world scenarios, several enhancements exist — all of them introduced in the book.

#### Query Rewriting

In a conversational RAG system, users often phrase their questions in ways that make poor search queries. A user might say: *"We have an essay due tomorrow. We have to write about some animal. I love penguins. I could write about them. But I could also write about dolphins. Are they animals? Maybe. Let's do dolphins. Where do they live for example?"* The actual information need is "where do dolphins live" — but that phrase is buried in chatter.

An LLM **query rewriter** solves this: before running retrieval, an LLM takes the conversational input and rephrases it into a clean, retrieval-optimised search query. The model is also given the option to decide that no retrieval is needed — if the question can be answered confidently from parametric knowledge (e.g., "what is 2+2?"), it can skip retrieval entirely.

```
Chatty conversational input
         │
         ▼
  [LLM Query Rewriter] ─── "where do dolphins live?"
         │                  (or: "no retrieval needed" for simple questions)
         ▼
  [Retrieval] → relevant chunks
         │
         ▼
  [Grounded Generation] → answer
```

Cohere's `co.chat()` endpoint has a native query-rewriting mode built in when using its `connectors` API, so you do not always need to implement this yourself.

#### Multi-Query RAG

Some questions require multiple independent pieces of information that exist in separate documents. "Compare the financial results of Nvidia in 2020 versus 2023" cannot be answered by a single retrieval — you need 2020 data and 2023 data from potentially different sources. Multi-query RAG decomposes the question, runs parallel retrievals, and merges the results before generation.

```
"Compare Nvidia financials 2020 vs 2023"
         │
         ▼
  [LLM Decomposer] ──► Query 1: "Nvidia financial results 2020"
                   ──► Query 2: "Nvidia financial results 2023"
         │                │
         │       [Retrieval × 2 in parallel]
         │                │
         └────── Deduplication (remove duplicate chunks) ──────┘
                          ▼
               Combined, deduplicated context
                          │
                          ▼
               [Grounded Generation] → comparative answer
```

*Important detail the book does not emphasise:* when two queries retrieve the same chunk, you must deduplicate before stuffing context into the prompt. Otherwise the LLM sees the same text twice, wastes context window budget, and may over-weight that information.

#### Multi-Hop RAG

Multi-hop RAG handles questions where the answer to the first retrieval step is needed to formulate the second retrieval query. The key concept is the **bridge entity** — a piece of information retrieved in hop 1 that becomes the search term for hop 2.

Consider: *"Who are the largest car manufacturers in 2023? Do they each make EVs?"* The bridge entities are "Toyota", "Volkswagen", "Hyundai" — extracted from hop 1, then used to construct hop 2 queries.

```
Hop 1 Query: "largest car manufacturers 2023"
         │
         ▼
  [Retrieval] → "Toyota, Volkswagen, Hyundai"   ← bridge entities extracted here
         │
         ▼
Hop 2 Queries (constructed using bridge entities):
  "Toyota Motor Corporation electric vehicles"
  "Volkswagen AG electric vehicles"
  "Hyundai Motor Company electric vehicles"
         │
         ▼
  [Retrieval × 3] → EV information per manufacturer
         │
         ▼
  [Grounded Generation] → full comparative answer
```

Each hop uses the previous hop's output to construct the next search. This mirrors how a human researcher works: find the answer to part one, then use that answer to look up part two.

#### Query Routing

A production system often has multiple knowledge bases — HR documents, product manuals, customer records, legal contracts. Searching all of them for every query wastes time and pollutes context with irrelevant results. **Query routing** directs each query to the right source.

There are two flavours:

**Keyword routing** — if the question contains certain keywords, route to the appropriate database:

```
"my salary slip" → HR database
"customer refund" → CRM
"API rate limits" → product docs
```

**Semantic routing** — embed the question, compare its vector against the embeddings of route descriptions, and choose the closest:

```
User question → embed → query_vector
Route A embedding: "HR and employee questions"  → similarity: 0.82  ← highest
Route B embedding: "Product and API questions"  → similarity: 0.31
Route C embedding: "Customer and sales data"    → similarity: 0.45

→ Route to HR database
```

Semantic routing is more flexible — it handles questions phrased in unexpected ways that keyword matching would miss.

#### Agentic RAG

Agentic RAG is the logical endpoint of all these enhancements. When a system can rewrite queries, run multiple retrievals, hop across retrieval steps, and route across data sources, it starts to look less like a pipeline and more like an **agent** that decides what actions to take in order to answer a question.

The connection to Chapter 7 is direct: Agentic RAG is the ReAct framework (Reason + Act) applied to retrieval. The LLM reasons about what information it needs, acts by issuing a retrieval query to a tool, observes the result, reasons again, and so on — until it has enough information to generate a grounded answer.

```
LLM Thought: "I need to find who the largest car manufacturers are."
LLM Action:  search_tool("largest car manufacturers 2023")
Observation: "Toyota, Volkswagen, Hyundai..."

LLM Thought: "Now I need to check each one for EVs."
LLM Action:  search_tool("Toyota EV lineup 2023")
Observation: "Toyota offers bZ4X, bZ3..."

LLM Thought: "I have enough to answer."
LLM Action:  generate_answer(...)
```

The data sources are tools — they can be vector databases, web search APIs, SQL databases, or any callable. Not all LLMs can do this reliably; at the time of the book's writing, only the largest managed models handle Agentic RAG well. Cohere's Command R+ is highlighted as a strong open-weights option.

---

### 5f. Modern RAG Techniques (2024–2025)

The techniques in 5e are from the book (published 2024). The field has moved fast since then. These six techniques represent the most widely adopted advances and are worth understanding before building any production RAG system.

---

#### HyDE — Hypothetical Document Embeddings

**The problem:** Queries and documents live in different parts of the embedding space. The question *"What year was Einstein born?"* embeds very differently from the answer *"Einstein was born in 1879."* The question is short and interrogative; the document is a factual statement. Even a retrieval-optimised embedding model feels this gap.

**The solution:** Instead of embedding the query directly, use an LLM to generate a *hypothetical answer document* first, then embed that. The hypothetical document lives in the same part of embedding space as real answer documents.

```
Standard dense retrieval:
  Query: "What year was Einstein born?"
    │
    ▼ embed query
  query_vec ───► nearest neighbours ───► retrieval results

HyDE:
  Query: "What year was Einstein born?"
    │
    ▼ LLM generates hypothetical answer (does NOT need to be correct)
  "Albert Einstein, the famous physicist, was born on March 14, 1879, in Ulm..."
    │
    ▼ embed hypothetical answer (not the query)
  hyde_vec ───► nearest neighbours ───► retrieval results
                                        (now much closer to real docs)
```

The key insight is that the hypothetical answer does not need to be factually correct — it just needs to be in the *style* of the documents in the corpus. If the corpus is Wikipedia articles, the LLM generates a Wikipedia-style passage, and that passage embeds close to actual Wikipedia passages.

**When to use it:** Zero-shot retrieval when you do not have query-document training pairs to fine-tune your embedding model.

---

#### Contextual Retrieval (Anthropic, 2024)

**The problem:** When you split a document into chunks, each chunk loses the context of where it came from. The chunk *"It was founded in 1923"* is meaningless without knowing it came from the Disney Wikipedia article. If this chunk is retrieved for a question about Disney's founding year, the LLM has no way to know which company it refers to.

**The solution:** Before indexing, use an LLM to prepend a short contextual explanation to each chunk. The context situates the chunk within its original document:

```
BEFORE Contextual Retrieval — raw chunk:
  "It was founded in 1923 by brothers Walt and Roy Disney."

AFTER Contextual Retrieval — contextualised chunk:
  "This chunk is from the Wikipedia article about The Walt Disney Company,
   discussing the company's founding history.
   
   It was founded in 1923 by brothers Walt and Roy Disney."
```

The contextualised version is now self-contained and retrieves correctly even when the original document is not available. According to Anthropic's internal benchmarks, this technique reduces retrieval failures by up to **67%**.

```
Indexing pipeline with Contextual Retrieval:

  Document
      │
      ▼
  [Chunker] ─── splits into raw chunks
      │
      ▼
  [LLM] ─── for each chunk: "Given this document, explain this chunk in 1-2 sentences"
      │
      ▼
  [Prepend context to chunk]
      │
      ▼
  [Embed contextualised chunk] → [Vector Index]
```

**Trade-off:** This adds LLM calls at indexing time — one call per chunk. For a document with 100 chunks, that is 100 LLM calls. But indexing is a one-time operation, so the cost is paid once and the quality improvement is permanent.

---

#### RAPTOR — Recursive Abstractive Processing for Tree-Organized Retrieval

**The problem:** Dense retrieval is good at finding specific facts inside individual chunks. But some questions require understanding the *big picture* across many documents — "What are the major themes in all company earnings reports from Q1 2024?" No single chunk contains this answer. Retrieving 50 chunks and stuffing them all into the prompt would exceed any context window.

**The solution:** Build a **summary tree** over your chunks. Cluster similar chunks, summarise each cluster, then cluster the summaries, summarise those, and so on — recursively until you have a single root summary. At query time, search across all levels of the tree simultaneously.

```
Raw chunks (leaf nodes):
  [Chunk 1][Chunk 2][Chunk 3][Chunk 4][Chunk 5][Chunk 6]
        │                │                │
        ▼                ▼                ▼
  Cluster A summary  Cluster B summary  Cluster C summary
        │                │                │
        └────────────────┴────────────────┘
                         │
                         ▼
                   Root summary
                   (whole document)

At query time: search ALL levels simultaneously
  Specific fact query → retrieves leaf chunks (high specificity)
  Broad theme query   → retrieves cluster/root summaries (high coverage)
```

RAPTOR lets a single RAG system handle both narrow factual questions and broad summarisation questions without needing different retrieval strategies for each.

---

#### Corrective RAG (CRAG)

**The problem:** Basic RAG blindly passes retrieved documents to the LLM even if they are completely irrelevant to the question. If retrieval fails — because the answer is not in the corpus, or the query embedding lands in the wrong neighbourhood — the LLM still generates an answer, but it is now hallucinating *using the irrelevant retrieved text as context*. This can actually produce more confident-sounding hallucinations than no retrieval at all.

**The solution:** Add a **relevance evaluator** between retrieval and generation. For each retrieved chunk, score it against the query. Then decide what to do:

```
Query
  │
  ▼
[Retrieval] → top-k chunks
  │
  ▼
[Relevance Evaluator] ─── scores each chunk: RELEVANT / AMBIGUOUS / IRRELEVANT
  │
  ├─── All RELEVANT ─────────────────────────────► [Generation] → answer
  │
  ├─── AMBIGUOUS ──► [Web Search for more info] ──► [Generation] → answer
  │
  └─── All IRRELEVANT ──► [Web Search instead] ──► [Generation] → answer
```

The web search fallback means CRAG can answer questions even when the local corpus does not contain the answer — instead of fabricating from irrelevant chunks, it fetches fresh information from the web.

**When to use it:** Any RAG system where the corpus might not always contain the answer (open-domain QA), or where retrieval quality is uncertain.

---

#### Self-RAG

**The problem:** Even with good retrieval, a standard RAG system has no mechanism for the LLM to assess whether it should retrieve in the first place, whether the retrieved content is actually useful, or whether its own answer is supported by what it retrieved. The LLM is passive — it just reads what it is given and generates.

**The solution:** Train the LLM to generate special **reflection tokens** alongside its regular output. These tokens are like the model talking to itself, evaluating its own behaviour:

| Token | What it asks |
|-------|-------------|
| `[Retrieve]` | Do I need to retrieve external information to answer this? |
| `[Relevant]` | Is this retrieved chunk actually relevant to the question? |
| `[Supported]` | Is my generated answer supported by the retrieved text? |
| `[Useful]` | Is my final answer actually useful to the user? |

```
Input: "What is the capital of France?"

Self-RAG model generates:
  [Retrieve] = No    ← model decides retrieval not needed for this
  Answer: "Paris."
  [Useful] = Yes

Input: "What were Nvidia's Q3 2024 earnings?"

Self-RAG model generates:
  [Retrieve] = Yes   ← model decides retrieval needed
  [retrieval happens]
  [Relevant] = Yes   ← retrieved chunk is relevant
  Answer: "Nvidia reported $18.1 billion in Q3 2024 revenue..."
  [Supported] = Yes  ← answer is grounded in retrieved text
  [Useful] = Yes
```

Self-RAG is trained end-to-end — the reflection tokens are part of the model's vocabulary. It outperforms standard RAG and CRAG on benchmarks like TriviaQA and MuSiQue because it can selectively skip retrieval for easy questions and self-correct when retrieval returns poor results.

---

#### GraphRAG (Microsoft, 2024)

**The problem:** Dense retrieval finds *locally* relevant chunks — chunks that are semantically close to the query. But it struggles with *global* questions that require synthesising information across the entire corpus. "What are the major themes across all these documents?" cannot be answered by any individual chunk, no matter how good the retrieval is.

**The solution:** Instead of a flat vector index, build a **knowledge graph** from the corpus. Extract entities (people, organisations, concepts) and the relationships between them. At query time, traverse the graph rather than searching the vector index.

```
Documents → [Entity Extraction] → Entities + Relationships
                                        │
                                        ▼
                               Knowledge Graph:
                     [Nvidia] ──revenue──► [$18B]
                     [Nvidia] ──CEO──────► [Jensen Huang]
                     [Jensen Huang] ──founded──► [Nvidia]
                     [Nvidia] ──competes──► [AMD]
                        │
                        ▼
              [Graph Traversal at query time]
                        │
                        ▼
                  Structured context → [LLM] → Answer
```

GraphRAG supports multi-hop reasoning naturally (follow the graph edges) and enables global theme detection by examining the graph's community structure. According to Microsoft's benchmarks, GraphRAG reduces token usage by 26–97% compared to naive document summarisation while producing higher-quality answers on global queries.

**Trade-off:** Building the knowledge graph requires significant preprocessing — entity extraction, relationship mapping, community detection. It is a higher upfront investment than a simple chunk-and-embed pipeline, but it pays off for large, complex corpora where global questions matter.

---

## 6. RAG Evaluation

### 6a. Why RAG is Hard to Evaluate

After building a RAG system, you face a question: is it actually good? For the search metrics in section 4, this was manageable — MAP and nDCG compare ranked lists against a fixed answer key. The output was a list; evaluation was arithmetic.

RAG outputs are **free text**. Two completely different sentences can be equally correct answers to the same question. "The Eiffel Tower is 330 metres tall" and "Standing at 330 metres, the Eiffel Tower is one of Paris's most iconic landmarks" are both correct — but they are completely different strings. A simple string match or keyword overlap score misses almost everything that matters.

What makes this worse is that a RAG system can fail in several *independent* ways at the same time:

```
RAG FAILURE MODES — each can happen independently:

  Retrieval failure:      Wrong documents retrieved → LLM has nothing to work with
  Faithfulness failure:   LLM ignores the context and hallucinates anyway
  Relevance failure:      LLM answers a different question than asked
  Citation failure:       LLM gives a correct answer but does not cite its sources
  Fluency failure:        Answer is accurate but poorly written and hard to read
```

A single accuracy number cannot tell you which of these is happening. You need a separate score for each axis — which is exactly what the paper described in 6b provides.

---

### 6b. The Four Axes of Generative Search Evaluation

The paper *"Evaluating verifiability in generative search engines"* (Liu et al., 2023) — studying systems like Perplexity, Bing AI, and Google AI Overview — identified four axes that together capture the full quality of a RAG answer. Each axis can fail independently of the others.

| Axis | Question It Asks | Can Fail While Others Pass? |
|------|-----------------|---------------------------|
| **Fluency** | Is the text readable, grammatical, cohesive? | Yes — accurate but poorly written |
| **Perceived utility** | Is the answer helpful and informative? | Yes — fluent but vacuous |
| **Citation recall** | Are all factual claims backed by a citation? | Yes — useful but uncited |
| **Citation precision** | Are all cited sources actually used? | Yes — over-cites irrelevant sources |

**Fluency** is the easiest axis to pass. Modern LLMs almost always produce grammatically correct text. If your system is failing on fluency, something is badly wrong at the generation stage.

**Perceived utility** is the hardest axis to evaluate automatically. It asks whether a real human would find the answer helpful — not just whether it is technically correct. A technically accurate answer that buries the key fact in three paragraphs of preamble may score low on perceived utility.

**Citation recall and precision** mirror the search metrics from section 4 but applied to source attribution rather than document retrieval. Think of them this way:

```
Generated answer: "The Eiffel Tower is 330m tall [1] and was built in 1889 [2][3]."

Citation recall:
  Fact "330m tall" is cited with [1]              ✓
  Fact "built in 1889" is cited with [2][3]        ✓
  All facts are cited → citation recall is high

Citation precision:
  [1] actually says "330 metres"                   ✓
  [2] actually mentions 1889                       ✓
  [3] is about the Eiffel Tower's paint colour  ✗ (irrelevant)
  2 out of 3 citations are genuinely used → precision = 0.67
```

High citation recall but low citation precision means the model is hedging — citing everything defensively whether or not the source is relevant. High citation precision but low recall means the model is making uncited claims in addition to properly cited ones.

---

### 6c. LLM-as-a-Judge

#### The Human Evaluation Bottleneck

Human evaluation is the gold standard for all four axes. A trained human evaluator can read an answer and immediately judge whether it is fluent, helpful, properly cited, and faithful to the source. The problem is scale. A production RAG system might need to evaluate thousands of answers — before and after every pipeline change, for every new model you consider, for every dataset you add. Hiring humans for this is slow, expensive, and inconsistent (different annotators disagree).

#### What LLM-as-a-Judge Does

**LLM-as-a-Judge** is the automated alternative: use a powerful LLM as the evaluator. The judge model receives a structured prompt containing the original question, the retrieved context, the generated answer, and the citations, then returns a score and reasoning for each evaluation axis.

```
JUDGE PROMPT EXAMPLE (simplified):

  You are an expert evaluator. Rate the following RAG system output.

  Question asked: "How tall is the Eiffel Tower?"

  Retrieved context:
    "The Eiffel Tower stands 330 metres (1,083 ft) tall."

  Generated answer:
    "The Eiffel Tower is approximately 330 metres tall. [Source 1]"

  Citation provided:
    Source 1: "The Eiffel Tower stands 330 metres (1,083 ft) tall."

  Score on a scale of 1-5:
  - Fluency: ___  (reasoning: ___)
  - Perceived utility: ___  (reasoning: ___)
  - Citation recall: ___  (reasoning: ___)
  - Citation precision: ___  (reasoning: ___)
```

The judge LLM returns scores and brief reasoning for each axis. This automates evaluation and makes it reproducible.

#### The Analogy and Its Limits

Think of LLM-as-a-Judge like having a very smart senior colleague review your work. They will catch obvious errors, assess whether the answer is useful, and notice when citations are missing. But they have their own preferences. If they tend to write long, detailed answers themselves, they will grade long answers higher than concise ones — even when concise is better. They also cannot audit their own reasoning for hidden biases.

This analogy points to the real risks of LLM-as-a-Judge:

```
Known biases of LLM judges:
  Verbosity bias:    longer answers tend to score higher, even if padded
  Confidence bias:   confident-sounding answers score higher, even if wrong
  Self-similarity:   GPT-4 judging GPT-4 outputs tends to be lenient
  Position bias:     when comparing two answers A vs B, order matters
```

None of these biases make LLM-as-a-Judge useless — it is far better than no evaluation. But they mean you should always pair automated LLM judgments with periodic human spot-checks, especially for high-stakes applications.

---

### 6d. The Ragas Library

**Ragas** is an open-source Python library that implements RAG evaluation using LLM-as-a-Judge. It operationalises the evaluation axes into computable metrics and handles the judge prompt construction automatically.

#### The Two Core Ragas Metrics

Beyond the four axes from the Liu et al. paper, Ragas introduces two metrics that are especially powerful for diagnosing RAG pipeline problems:

**Faithfulness** measures whether the generated answer is consistent with the retrieved context. An answer is faithful if every claim it makes is supported by — or at least not contradicted by — the retrieved documents. Crucially, faithfulness does not care about whether the answer is correct in the real world. It only measures consistency with *the context you provided*.

**Answer relevance** measures whether the generated answer actually addresses the question that was asked. A technically accurate, well-cited answer can still score low on answer relevance if it drifts to a related but different topic.

#### Dry-Run: The Four Cases

These two metrics fail independently, which is what makes them diagnostically useful. There are four possible combinations:

```
Context: "The Eiffel Tower is 330 metres tall and was completed in 1889."
Question: "How tall is the Eiffel Tower?"

─── Case 1: Both pass ─────────────────────────────────────────
Answer: "The Eiffel Tower is 330 metres tall."
  Faithfulness:    ✓  (330m is in the context)
  Answer relevance: ✓  (directly answers the height question)
  → Perfect. This is what a good RAG system produces.

─── Case 2: Faithfulness fails, relevance passes ──────────────
Answer: "The Eiffel Tower is 500 metres tall."
  Faithfulness:    ✗  (context says 330m, answer says 500m — contradiction)
  Answer relevance: ✓  (on topic, answered the height question)
  → Diagnosis: the LLM is not reading the context carefully,
    or is overriding context with its own (wrong) training memory.
    Fix: strengthen the prompt instruction ("only use the provided context").

─── Case 3: Faithfulness passes, relevance fails ──────────────
Answer: "The Eiffel Tower was completed in 1889."
  Faithfulness:    ✓  (1889 is in the context, not contradicted)
  Answer relevance: ✗  (doesn't answer the height question at all)
  → Diagnosis: retrieval returned the wrong chunk, or the prompt template
    is not focusing the model on the question.
    Fix: improve chunking, retrieval, or the prompt.

─── Case 4: Both fail ─────────────────────────────────────────
Answer: "The Eiffel Tower is located in Rome."
  Faithfulness:    ✗  (context says nothing about Rome)
  Answer relevance: ✗  (doesn't answer the height question)
  → Diagnosis: catastrophic retrieval failure — completely wrong documents
    were retrieved, and the LLM hallucinated on top of them.
    Fix: review the retrieval pipeline and the embedding model.
```

#### Using Ragas as a Diagnostic Loop

The power of Ragas is that it gives you a numeric signal after every pipeline change. You make a change — swap the embedding model, adjust chunk size, rewrite the prompt template — and run Ragas on your test set. If faithfulness goes up, the generation is getting more grounded. If answer relevance goes down, the retrieval got worse. This turns RAG development from guesswork into a measurable engineering process.

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

# Your test dataset: questions, retrieved contexts, generated answers
result = evaluate(
    dataset=test_dataset,
    metrics=[faithfulness, answer_relevancy]
)

print(result)
# {'faithfulness': 0.82, 'answer_relevancy': 0.76}
# → faithfulness is good; answer relevancy has room to improve
# → investigate: are we retrieving the right chunks?
```

The Ragas library handles constructing the LLM-as-a-Judge prompts for each metric, sending them to the judge model, parsing the scores, and returning aggregated results. The underlying formulas involve generating inverse questions from the answer and computing semantic similarity — the Ragas documentation covers these in detail for each metric.

---

## 7. Key Takeaways

Dense retrieval turns search into a geometry problem. Both queries and documents are embedded into the same vector space, and retrieval becomes finding the nearest vectors. This enables **semantic search** — finding relevant documents even when they share no keywords with the query.

Chunking strategy is a first-class engineering decision, not an afterthought. Character splits destroy words; token splits create boundary blindness; token splits with overlap prevent boundary blindness at the cost of redundancy. The right strategy depends on your documents and query types. In practice, paragraph-level chunks with overlap are the default starting point for most systems.

Rerankers (cross-encoders) and embedding models (bi-encoders) have complementary strengths. Bi-encoders are fast and scalable because document embeddings are pre-computed; cross-encoders are accurate because they see query and document together. The two-stage pipeline — retrieve many with a bi-encoder, rerank the shortlist with a cross-encoder — is the industry standard because it gets the best of both.

Mean Average Precision penalises ranking quality, not just recall. Putting a relevant document at rank 3 scores worse than putting it at rank 1, even if the total number of retrieved relevant documents is the same. MAP is the standard metric for binary-relevance search evaluation; nDCG extends this to graded relevance.

RAG reduces hallucinations by converting the LLM from a memory-retrieval system into a reading-comprehension system. The LLM reads retrieved documents rather than recalling from parametric memory. The quality of a RAG system depends on retrieval quality (does it find the right documents?), context quality (are the chunks informative?), and prompt design (does the LLM know how to use the context?). Ragas metrics — especially faithfulness and answer relevance — help diagnose which component is failing.

---

*Chapter 8 complete. The next chapter extends language models to multimodal inputs — images alongside text — building on the same architectural foundation.*
