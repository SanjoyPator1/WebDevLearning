"""
Layer 8 — Day 9: RAG Knowledge Base
=====================================
Builds a retrieval index over CBT/DBT techniques, grounding exercises,
psychoeducation, and crisis resources — knowledge that is accurate,
updatable, and citable at inference time.

Uses the therapy embedder from Layer 2 for domain-aware retrieval.
Adds a cross-encoder reranker for precision on the final top-k.

Distinction: model weights (implicit knowledge) vs RAG index (explicit
knowledge). Crisis resource phone numbers go in the index, not the
weights — they change and need to be updatable without retraining.

Produces:
    checkpoints/rag_index.faiss    ← FAISS vector index
    checkpoints/rag_chunks.json    ← document text (parallel to index)

Run:
    python day09_rag.py --build          # chunk, embed, index all RAG docs
    python day09_rag.py --test           # test retrieval on therapy queries
    python day09_rag.py --compare        # domain embedder vs general embedder
    python day09_rag.py --all            # build then test
"""

import argparse
import json
import time
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

THERAPY_EMBEDDER = CHECKPOINT_DIR / "therapy_embedder"
GENERAL_EMBEDDER = "BAAI/bge-base-en-v1.5"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

INDEX_PATH = CHECKPOINT_DIR / "rag_index.faiss"
CHUNKS_PATH = CHECKPOINT_DIR / "rag_chunks.json"

CHUNK_SIZE = 120    # words per chunk
CHUNK_OVERLAP = 20  # word overlap between consecutive chunks


# Chunking

def chunk_document(doc: dict, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split a document into overlapping word-level chunks."""
    words = doc["content"].split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i : i + chunk_size]
        if len(chunk_words) < 20:   # skip very short trailing chunks
            continue
        chunks.append({
            "text": " ".join(chunk_words),
            "title": doc["title"],
            "category": doc.get("category", ""),
            "chunk_index": len(chunks),
        })
    return chunks


def load_and_chunk_rag_docs() -> list[dict]:
    """Load RAG documents from Layer 0 and chunk them."""
    rag_path = SPLITS_DIR / "rag.json"
    if not rag_path.exists():
        raise FileNotFoundError(
            f"RAG split not found at {rag_path}\n"
            "Run layer0_data_pipeline/day01_data_pipeline.py --all first."
        )

    docs = json.loads(rag_path.read_text())
    all_chunks = []
    for doc in docs:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)

    print(f"  {len(docs)} documents → {len(all_chunks)} chunks")
    print(f"  Avg chunk size: {sum(len(c['text'].split()) for c in all_chunks) // len(all_chunks)} words")

    # Print category breakdown
    from collections import Counter
    categories = Counter(c["category"] for c in all_chunks)
    for cat, count in categories.most_common():
        print(f"    {cat:<30} {count} chunks")

    return all_chunks


# Build index

def build_index(chunks: list[dict], embedder: SentenceTransformer) -> faiss.Index:
    texts = [c["text"] for c in chunks]
    print(f"  Embedding {len(texts)} chunks...")

    embeddings = embedder.encode(
        texts,
        batch_size=128,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = embeddings.astype(np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])   # inner product = cosine on normalised vecs
    index.add(embeddings)
    print(f"  Index built: {index.ntotal} vectors, dim={embeddings.shape[1]}")
    return index


def run_build() -> None:
    print("\n=== Build RAG Index ===")

    embedder_path = str(THERAPY_EMBEDDER) if THERAPY_EMBEDDER.exists() else GENERAL_EMBEDDER
    if not THERAPY_EMBEDDER.exists():
        print(f"  Therapy embedder not found, using {GENERAL_EMBEDDER}")
        print(f"  For best results, run layer2_embedder/day02_03_embedder.py --all first.")
    else:
        print(f"  Using therapy embedder: {embedder_path}")

    embedder = SentenceTransformer(embedder_path)
    chunks = load_and_chunk_rag_docs()
    index = build_index(chunks, embedder)

    faiss.write_index(index, str(INDEX_PATH))
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2))

    print(f"\n  Index saved → {INDEX_PATH}")
    print(f"  Chunks saved → {CHUNKS_PATH}  ({len(chunks)} entries)")


# Retrieval pipeline

class TherapyRAG:
    def __init__(self, embedder_path: str | None = None):
        ep = embedder_path or (str(THERAPY_EMBEDDER) if THERAPY_EMBEDDER.exists() else GENERAL_EMBEDDER)
        self.embedder = SentenceTransformer(ep)
        self.reranker = CrossEncoder(RERANKER_MODEL)

        if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
            raise FileNotFoundError("RAG index not found. Run --build first.")

        self.index = faiss.read_index(str(INDEX_PATH))
        self.chunks = json.loads(CHUNKS_PATH.read_text())
        print(f"  RAG loaded: {len(self.chunks)} chunks")

    def retrieve(
        self,
        query: str,
        k_retrieve: int = 15,
        k_final: int = 3,
    ) -> list[dict]:
        """Two-stage retrieval: bi-encoder → cross-encoder reranker."""
        # Stage 1: fast bi-encoder retrieval
        q_emb = self.embedder.encode([query], normalize_embeddings=True).astype(np.float32)
        scores, indices = self.index.search(q_emb, min(k_retrieve, self.index.ntotal))
        candidates = [self.chunks[i] for i in indices[0] if i < len(self.chunks)]

        # Stage 2: precise cross-encoder reranking
        pairs = [(query, c["text"]) for c in candidates]
        rerank_scores = self.reranker.predict(pairs)
        ranked = sorted(zip(rerank_scores, candidates), key=lambda x: x[0], reverse=True)

        return [c for _, c in ranked[:k_final]]

    def format_for_prompt(self, chunks: list[dict]) -> str:
        """Format retrieved chunks for injection into the system prompt."""
        if not chunks:
            return ""
        lines = ["Relevant techniques and resources:"]
        for c in chunks:
            lines.append(f"\n[{c['title']}]\n{c['text']}")
        return "\n".join(lines)


# Test queries

TEST_QUERIES = [
    ("patient is describing catastrophising thoughts", "Cognitive Restructuring", "CBT technique"),
    ("user feels urge to self-harm and needs grounding", "5-4-3-2-1", "Grounding technique"),
    ("breathing exercise for acute anxiety", "Box Breathing", "Grounding technique"),
    ("user struggling to accept a difficult situation", "Radical Acceptance", "DBT skill"),
    ("user wants help communicating assertively", "DEAR MAN", "DBT skill"),
    ("user describing anhedonia and low motivation", "Behavioural Activation", "CBT technique"),
    ("client in the UK needs crisis support", "116 123", "Crisis resources"),
    ("user in US saying they want to end their life", "988", "Crisis resources"),
    ("what is attachment anxiety", "Attachment Styles", "Psychoeducation"),
    ("user doesn't understand why they feel numb", "What is Depression", "Psychoeducation"),
]


def run_test() -> None:
    print("\n=== Test RAG Retrieval ===")
    rag = TherapyRAG()

    results = []
    correct = 0

    print(f"\n  {'Query':<45} {'Expected':<20} {'Found?'}")

    for query, expected_keyword, expected_category in TEST_QUERIES:
        t0 = time.time()
        retrieved = rag.retrieve(query, k_retrieve=15, k_final=3)
        latency_ms = round((time.time() - t0) * 1000, 1)

        found = any(
            expected_keyword.lower() in c["text"].lower() or
            expected_keyword.lower() in c["title"].lower()
            for c in retrieved
        )
        correct += int(found)
        mark = "✓" if found else "✗"

        print(f"  {query[:43]:<45} {expected_keyword:<20} {mark}  ({latency_ms}ms)")
        results.append({
            "query": query,
            "expected_keyword": expected_keyword,
            "found": found,
            "latency_ms": latency_ms,
            "top_results": [{"title": c["title"], "category": c["category"], "text": c["text"][:120]} for c in retrieved],
        })

    precision = round(100 * correct / len(TEST_QUERIES), 1)
    avg_latency = round(sum(r["latency_ms"] for r in results) / len(results), 1)
    print(f"\n  Precision@3: {correct}/{len(TEST_QUERIES)}  ({precision}%)")
    print(f"  Avg latency: {avg_latency} ms per query")

    out = RESULTS_DIR / "rag_test.json"
    out.write_text(json.dumps({"precision": precision, "avg_latency_ms": avg_latency, "results": results}, indent=2))
    print(f"\n  Results saved → {out}")


# Compare domain vs general embedder

def run_compare() -> None:
    print("\n=== Compare: Therapy Embedder vs General Embedder ===")

    if not THERAPY_EMBEDDER.exists():
        print("Therapy embedder not found. Run layer2 first.")
        return

    results = {}
    for label, ep in [("therapy_embedder", str(THERAPY_EMBEDDER)), ("general_embedder", GENERAL_EMBEDDER)]:
        print(f"\n  Building index with {label}...")
        embedder = SentenceTransformer(ep)
        chunks = load_and_chunk_rag_docs()
        index = build_index(chunks, embedder)

        # Temporarily swap out the index
        faiss.write_index(index, str(INDEX_PATH))

        rag = TherapyRAG(embedder_path=ep)
        correct = 0
        for query, kw, _ in TEST_QUERIES:
            retrieved = rag.retrieve(query, k_final=3)
            if any(kw.lower() in c["text"].lower() or kw.lower() in c["title"].lower() for c in retrieved):
                correct += 1
        precision = round(100 * correct / len(TEST_QUERIES), 1)
        results[label] = {"precision": precision}
        print(f"    Precision@3: {precision}%")

    print(f"\n  Therapy embedder improvement: {results['therapy_embedder']['precision'] - results['general_embedder']['precision']:+.1f}%")

    # Restore the therapy embedder index
    run_build()

    out = RESULTS_DIR / "rag_embedder_comparison.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"  Results saved → {out}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Chunk, embed, and index RAG docs")
    parser.add_argument("--test", action="store_true", help="Test retrieval on therapy queries")
    parser.add_argument("--compare", action="store_true", help="Domain embedder vs general embedder")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Build then test")
    args = parser.parse_args()

    if args.run_all:
        run_build()
        run_test()
    else:
        if args.build:
            run_build()
        if args.test:
            run_test()
        if args.compare:
            run_compare()
        if not any([args.build, args.test, args.compare]):
            parser.print_help()


if __name__ == "__main__":
    main()
