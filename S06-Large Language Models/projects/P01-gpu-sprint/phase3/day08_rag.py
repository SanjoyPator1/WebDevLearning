"""
Day 8 — Advanced RAG
Pipeline: baseline bi-encoder → +reranker → +HyDE → ColBERT
Corpus: Wikipedia Simple English (easy to download, good for testing)

Run:
    python day08_rag.py --build_index          # embed corpus and save FAISS index
    python day08_rag.py --compare              # compare all retrieval methods
    python day08_rag.py --method hyde          # test HyDE specifically
    python day08_rag.py --method colbert       # test ColBERT specifically
"""

import argparse
import json
import time
from pathlib import Path

import faiss
import numpy as np
import torch
from datasets import load_dataset
from sentence_transformers import CrossEncoder, SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

RESULTS_DIR = Path(__file__).parent / "results"
INDEX_DIR = Path(__file__).parent / "rag_index"
RESULTS_DIR.mkdir(exist_ok=True)
INDEX_DIR.mkdir(exist_ok=True)

EMBED_MODEL = "BAAI/bge-large-en-v1.5"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
GENERATOR_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # for HyDE hypothesis generation

N_CORPUS_DOCS = 10_000   # Wikipedia Simple articles to index
CHUNK_SIZE = 300          # tokens per chunk (approximate chars)


# Build corpus and index

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size) if len(words[i:i + chunk_size]) > 30]


def build_index() -> tuple[list[str], np.ndarray, faiss.Index]:
    print("Loading Wikipedia Simple English corpus...")
    ds = load_dataset("wikimedia/wikipedia", "20231101.simple", split="train")
    ds = ds.select(range(min(N_CORPUS_DOCS, len(ds))))

    docs = []
    for article in ds:
        chunks = chunk_text(article["text"])
        docs.extend(chunks[:5])   # max 5 chunks per article

    print(f"Corpus: {len(docs):,} chunks from {N_CORPUS_DOCS} articles")

    embedder = SentenceTransformer(EMBED_MODEL)
    print(f"Embedding with {EMBED_MODEL}...")
    embeddings = embedder.encode(docs, batch_size=256, show_progress_bar=True, normalize_embeddings=True)
    embeddings = embeddings.astype(np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    # Save
    np.save(INDEX_DIR / "embeddings.npy", embeddings)
    faiss.write_index(index, str(INDEX_DIR / "faiss.index"))
    with open(INDEX_DIR / "docs.json", "w") as f:
        json.dump(docs, f)

    print(f"Index saved to {INDEX_DIR}/")
    return docs, embeddings, index


def load_index() -> tuple[list[str], faiss.Index]:
    with open(INDEX_DIR / "docs.json") as f:
        docs = json.load(f)
    index = faiss.read_index(str(INDEX_DIR / "faiss.index"))
    print(f"Loaded index: {len(docs):,} documents")
    return docs, index


# Retrieval methods

class RAGPipeline:
    def __init__(self, docs: list[str], index: faiss.Index):
        self.docs = docs
        self.index = index
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self.reranker = None
        self.generator = None
        self.tokenizer = None

    def _embed(self, text: str) -> np.ndarray:
        emb = self.embedder.encode([text], normalize_embeddings=True)
        return emb.astype(np.float32)

    def retrieve_baseline(self, query: str, k: int = 5) -> tuple[list[str], float]:
        t0 = time.time()
        emb = self._embed(query)
        _, indices = self.index.search(emb, k)
        docs = [self.docs[i] for i in indices[0] if i < len(self.docs)]
        return docs, (time.time() - t0) * 1000

    def retrieve_rerank(self, query: str, k_retrieve: int = 20, k_final: int = 5) -> tuple[list[str], float]:
        if self.reranker is None:
            print(f"  Loading reranker: {RERANK_MODEL}")
            self.reranker = CrossEncoder(RERANK_MODEL)
        t0 = time.time()
        candidates, _ = self.retrieve_baseline(query, k=k_retrieve)
        pairs = [(query, doc) for doc in candidates]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(scores, candidates), reverse=True)
        docs = [doc for _, doc in ranked[:k_final]]
        return docs, (time.time() - t0) * 1000

    def retrieve_hyde(self, query: str, k_final: int = 5) -> tuple[list[str], float]:
        if self.generator is None:
            print(f"  Loading generator: {GENERATOR_MODEL}")
            self.generator = AutoModelForCausalLM.from_pretrained(
                GENERATOR_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(GENERATOR_MODEL)
        t0 = time.time()
        prompt = f"Write a short factual paragraph that answers the question: {query}"
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=200, truncation=True).to("cuda")
        with torch.no_grad():
            out = self.generator.generate(**inputs, max_new_tokens=100, do_sample=False)
        hypothesis = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        docs, _ = self.retrieve_rerank(hypothesis, k_retrieve=20, k_final=k_final)
        return docs, (time.time() - t0) * 1000, hypothesis

    def retrieve_colbert(self, query: str, k: int = 5) -> tuple[list[str], float]:
        try:
            from ragatouille import RAGPretrainedModel
        except ImportError:
            return [], 0.0
        t0 = time.time()
        index_path = INDEX_DIR / "colbert_index"
        if not index_path.exists():
            print("  Building ColBERT index (first time, takes a few minutes)...")
            colbert = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")
            colbert.index(
                collection=self.docs[:5000],  # subset for speed
                index_name="wiki_simple",
                index_root=str(INDEX_DIR),
            )
        else:
            colbert = RAGPretrainedModel.from_index(str(index_path))
        results = colbert.search(query, k=k)
        docs = [r["content"] for r in results]
        return docs, (time.time() - t0) * 1000


# Evaluation

# 20 test queries with known relevant topic (used to measure recall)
TEST_QUERIES = [
    ("Who invented the telephone?", "Alexander Graham Bell"),
    ("What is photosynthesis?", "plants convert sunlight"),
    ("When did World War II end?", "1945"),
    ("What is the capital of Japan?", "Tokyo"),
    ("How does a black hole form?", "massive star collapses"),
    ("What language do Brazilians speak?", "Portuguese"),
    ("Who wrote Romeo and Juliet?", "Shakespeare"),
    ("What is the speed of light?", "299,792"),
    ("What is DNA?", "deoxyribonucleic acid"),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci"),
    ("What causes earthquakes?", "tectonic plates"),
    ("How many planets are in the solar system?", "eight"),
    ("What is the largest ocean?", "Pacific"),
    ("Who was the first US president?", "George Washington"),
    ("What is climate change?", "greenhouse gases"),
    ("How does the immune system work?", "white blood cells"),
    ("What is machine learning?", "algorithms learn from data"),
    ("Who invented the internet?", "ARPANET"),
    ("What is the Pythagorean theorem?", "right triangle"),
    ("How do vaccines work?", "immune response"),
]


def precision_at_k(docs: list[str], gold_keyword: str, k: int = 5) -> float:
    relevant = sum(1 for d in docs[:k] if gold_keyword.lower() in d.lower())
    return relevant / k


def evaluate_method(pipeline: RAGPipeline, method: str) -> dict:
    precisions = []
    latencies = []

    for query, gold in TEST_QUERIES:
        if method == "baseline":
            docs, latency = pipeline.retrieve_baseline(query)
        elif method == "rerank":
            docs, latency = pipeline.retrieve_rerank(query)
        elif method == "hyde":
            docs, latency, _ = pipeline.retrieve_hyde(query)
        elif method == "colbert":
            docs, latency = pipeline.retrieve_colbert(query)
        else:
            raise ValueError(f"Unknown method: {method}")

        p5 = precision_at_k(docs, gold)
        precisions.append(p5)
        latencies.append(latency)

    return {
        "method": method,
        "precision_at_5": round(np.mean(precisions), 3),
        "avg_latency_ms": round(np.mean(latencies), 1),
    }


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build_index", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--method", choices=["baseline", "rerank", "hyde", "colbert"])
    args = parser.parse_args()

    if args.build_index:
        build_index()
        return

    if not (INDEX_DIR / "docs.json").exists():
        print("Index not found. Run --build_index first.")
        return

    docs, index = load_index()
    pipeline = RAGPipeline(docs, index)

    if args.compare:
        results = []
        for method in ["baseline", "rerank", "hyde", "colbert"]:
            print(f"\nEvaluating {method}...")
            r = evaluate_method(pipeline, method)
            results.append(r)
            print(f"  Precision@5: {r['precision_at_5']}  |  Latency: {r['avg_latency_ms']} ms")

        print(f"\n{'─'*55}")
        print(f"  {'Method':<12} {'Precision@5':<14} {'Avg Latency (ms)'}")
        for r in results:
            print(f"  {r['method']:<12} {r['precision_at_5']:<14} {r['avg_latency_ms']}")

        out = RESULTS_DIR / "day08_comparison.json"
        out.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved → {out}")

    elif args.method:
        print(f"\nTesting {args.method} on 5 sample queries:")
        for query, gold in TEST_QUERIES[:5]:
            if args.method == "hyde":
                docs_out, latency, hyp = pipeline.retrieve_hyde(query)
                print(f"\n  Q: {query}")
                print(f"  Hypothesis: {hyp[:100]}")
            else:
                fn = getattr(pipeline, f"retrieve_{args.method.replace('rerank','rerank')}")
                docs_out, latency = fn(query) if args.method != "colbert" else pipeline.retrieve_colbert(query)
                print(f"\n  Q: {query}")
            for i, d in enumerate(docs_out[:2]):
                print(f"  [{i+1}] {d[:120].strip()}")
            print(f"  Latency: {latency:.1f} ms  |  Gold '{gold}' found: {any(gold.lower() in d.lower() for d in docs_out)}")


if __name__ == "__main__":
    main()
