# ============================================================
# LISTING: 04_reranking.py  (reference implementation -- FROM SCRATCH)
# BUILDING: A second, smarter reranking pass on top of vector search --
#           a REAL cross-encoder model (sentence-transformers'
#           CrossEncoder, ms-marco-MiniLM-L-6-v2) scoring each
#           (query, chunk) pair together, run locally.
# REF: Chapter 6 notes, section 6 (Reranking: A Second, Smarter Pass)
# SETUP (one time, inside the repo's .venv):
#   pip install sentence-transformers
# The model weights (~90 MB) download from Hugging Face the first time
# they are used, then load from the local cache. The reranker itself
# makes NO API call -- it runs on this machine, so the only live call in
# this file is the one query embedding in the first-pass search.
# ============================================================
#
# Every retrieval method built so far in this chapter's from-scratch
# track -- TF-IDF, vector search, hybrid RRF fusion -- is a bi-encoder
# under the hood: query and document get scored independently, then
# compared. A cross-encoder is a dedicated, smaller model trained
# specifically to read a query and a document TOGETHER, as one input,
# and output one relevance number. This file loads a real one and uses
# it to re-order the vector-search candidates. Because it never sees the
# query ahead of time, its scores cannot be precomputed -- it has to run
# once per (query, chunk) pair, which is why it only ever re-scores a
# short candidate list, never the whole corpus.

import asyncio
import math
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from sentence_transformers import CrossEncoder

load_dotenv()

PROVIDER = "gemini"  # "gemini" or "ollama"

if PROVIDER == "gemini":
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    CHAT_MODEL = os.environ["GEMINI_MODEL"]
    EMBEDDING_MODEL = "gemini-embedding-001"
elif PROVIDER == "ollama":
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    CHAT_MODEL = "qwen3:8b"
    EMBEDDING_MODEL = "nomic-embed-text"  # run `ollama pull nomic-embed-text` first
else:
    raise ValueError(f"unknown PROVIDER: {PROVIDER!r}")


async def embed_text(text: str) -> list[float]:
    """Embed one piece of text using the configured provider's embedding
    model. Both Gemini and Ollama expose this through the same
    OpenAI-compatible /embeddings endpoint, so this function never
    changes based on PROVIDER -- only the client/model above does."""
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


# --- The reranker: a real cross-encoder, loaded once and run locally ---
# This model was fine-tuned on the MS MARCO passage-ranking dataset to
# score a (query, passage) pair. Its output is a raw LOGIT: higher means
# more relevant, and it is normal for every score to be negative. Only
# the ORDER matters, not the sign or size.
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
print("-" * 60)
print(f"Loading cross-encoder reranker: {RERANKER_MODEL_NAME}")
reranker = CrossEncoder(RERANKER_MODEL_NAME)
print("  reranker loaded (runs locally, no API call)")


# ============================================================
# CHROMA SETUP (run once, before running this script):
#   docker run -d --name ch06-chroma -p 8000:8000 chromadb/chroma
# This starts a real Chroma vector database server on localhost:8000.
# To stop it later: docker stop ch06-chroma && docker rm ch06-chroma
# ============================================================

import chromadb

chroma_client = chromadb.HttpClient(host="localhost", port=8000)

# metadata={"hnsw:space": "cosine"} makes this collection use cosine
# distance for search -- the same metric worked through by hand in
# Chapter 6 notes section 2 (distance = 1 - cosine similarity).
runbook_collection = chroma_client.get_or_create_collection(
    name="ops_assistant_runbook",
    metadata={"hnsw:space": "cosine"},
)


# --- The Ops Assistant's runbook corpus -- the exact same seven chunks
# used by every file in this set that touches the knowledge store, so
# whichever file ingests first, every file searches the same collection.
RUNBOOK_DOCS = [
    {
        "id": "deploy-rollback-1",
        "text": (
            "Rollback procedure: if a deploy causes errors, run "
            "`deploy rollback --service <name> --to-version <last-good-tag>`. "
            "This reverts traffic within 90 seconds. Always check the "
            "#incidents channel before rolling back a shared service."
        ),
    },
    {
        "id": "deploy-rollback-2",
        "text": (
            "Deploy Runbook: Rolling Back a Release. If a new release causes "
            "500 errors, use the rollback command immediately rather than "
            "attempting a hotfix under pressure. Rollback is always safer "
            "than a rushed forward fix during an active incident."
        ),
    },
    {
        "id": "deploy-new-release",
        "text": (
            "Deploy Runbook: How to Push a New Release. Merge to main, wait "
            "for CI to pass, then run `deploy push --service <name>`. "
            "Monitor error rates for 10 minutes after a push completes."
        ),
    },
    {
        "id": "err-5023",
        "text": (
            "ERR_5023: payment gateway timeout. This means the retry worker "
            "lost its connection to the payment gateway. Fix: restart the "
            "retry worker with `restart-worker --name payment-retry`."
        ),
    },
    {
        "id": "oncall-escalation",
        "text": (
            "On-Call Runbook: Paging the Deploy Owner. If a deploy is stuck "
            "or a rollback fails, page the on-call engineer via PagerDuty "
            "using the #incidents channel. Do not attempt further changes "
            "without on-call sign-off during an active incident."
        ),
    },
    {
        "id": "feature-flags",
        "text": (
            "Feature Flag Runbook: Toggling Flags in Incidents. If a bad "
            "deploy is caused by a new feature, toggling its feature flag "
            "off is often faster than a full rollback and does not require "
            "redeploying. Check the flags dashboard for the flag name."
        ),
    },
    {
        "id": "db-connection-pool",
        "text": (
            "Database Connection Pool Exhaustion. Symptoms: ECONNREFUSED "
            "errors from the payments database. Fix: restart the connection "
            "pool with `restart-pool --db payments`. Usually caused by a "
            "leaked connection in a recent deploy."
        ),
    },
]


async def ensure_runbook_ingested():
    """Ingest RUNBOOK_DOCS into Chroma if the collection is empty. Safe to
    call from any file in this set -- if another file already ingested
    the corpus, this is a no-op, matching the real ingest-once-then-reuse
    shape from Chapter 6 notes section 2."""
    if runbook_collection.count() > 0:
        print(f"    [ingest] collection already has {runbook_collection.count()} docs, skipping")
        return

    print(f"    [ingest] embedding and storing {len(RUNBOOK_DOCS)} runbook chunks...")
    for doc in RUNBOOK_DOCS:
        embedding = await embed_text(doc["text"])
        runbook_collection.add(
            ids=[doc["id"]],
            embeddings=[embedding],
            documents=[doc["text"]],
        )
    print(f"    [ingest] done, collection now has {runbook_collection.count()} docs")


async def search_top_candidates(query: str, top_k: int = 5) -> list[dict]:
    """Bi-encoder first pass: embed the query, search Chroma for its
    top_k closest chunks by cosine distance, and convert each distance
    back into a cosine similarity (similarity = 1 - distance, per
    Chapter 6 notes section 2) so the first-pass ranking can be printed
    next to the cross-encoder's re-ranking below. (The two scores are on
    different scales -- cosine similarity vs. a raw logit -- so compare
    the ORDERINGS, not the raw numbers.)"""
    query_embedding = await embed_text(query)
    results = runbook_collection.query(query_embeddings=[query_embedding], n_results=top_k)

    candidates = []
    for chunk_id, chunk_text, distance in zip(
        results["ids"][0], results["documents"][0], results["distances"][0]
    ):
        candidates.append(
            {
                "id": chunk_id,
                "text": chunk_text,
                "distance": distance,
                "similarity": 1.0 - distance,
            }
        )
    return candidates


def rerank_with_cross_encoder(query: str, candidates: list[dict], top_n: int) -> list[dict]:
    """Second pass: score every (query, chunk) pair TOGETHER with a real
    cross-encoder, then re-sort the candidates by that score.

    Unlike the first-pass bi-encoder, the cross-encoder reads the query
    and the chunk as ONE input, so every word of the query can attend to
    every word of the chunk. That is how it can notice that a chunk
    about pushing a NEW release does not answer "how do we roll back"
    even though the two share words like "deploy" and "release"
    (Chapter 6 notes section 6).

    Math: relevance = sigmoid(logit) = 1 / (1 + e^(-logit)). The model
    outputs the raw logit; sigmoid only squashes it into 0-1 for
    readability and never changes the order.

    This is a plain synchronous function: CrossEncoder.predict() runs on
    this machine, so there is nothing to await.
    """
    # One (query, chunk_text) pair per candidate -- the cross-encoder
    # reads each pair as a single combined input.
    pairs = [(query, candidate["text"]) for candidate in candidates]
    print(f"    [rerank] scoring {len(pairs)} (query, chunk) pairs in one predict() call")

    # shape: (num_candidates,) -- one raw logit per pair, higher = more relevant
    raw_scores = reranker.predict(pairs)
    print(f"    [rerank] raw logits, in candidate order: {[round(float(s), 3) for s in raw_scores]}")

    scored_candidates = []
    for candidate, raw_score in zip(candidates, raw_scores):
        logit = float(raw_score)  # numpy float32 -> plain float
        relevance = 1.0 / (1.0 + math.exp(-logit))  # sigmoid: logit -> 0-1
        scored_candidates.append(
            {**candidate, "rerank_score": logit, "rerank_relevance": relevance}
        )

    scored_candidates.sort(key=lambda item: item["rerank_score"], reverse=True)
    return scored_candidates[:top_n]


async def main() -> None:
    print("-" * 60)
    print("STEP 1: Ensuring the runbook corpus is ingested into Chroma")
    print("-" * 60)
    await ensure_runbook_ingested()

    query = "how do we roll back a bad deploy"
    print()
    print("-" * 60)
    print(f"STEP 2: Bi-encoder first pass (vector search) for: {query!r}")
    print("-" * 60)
    candidates = await search_top_candidates(query, top_k=5)
    for candidate in candidates:
        print(
            f"  id={candidate['id']:<20} similarity={candidate['similarity']:.4f} "
            f"distance={candidate['distance']:.4f}"
        )

    print()
    print("-" * 60)
    print("STEP 3: Cross-encoder second pass (real model, runs locally)")
    print("-" * 60)
    reranked = rerank_with_cross_encoder(query, candidates, top_n=5)
    for candidate in reranked:
        print(
            f"  id={candidate['id']:<20} rerank_score={candidate['rerank_score']:8.4f} "
            f"relevance={candidate['rerank_relevance']:.4f}"
        )
    print("  (scores are raw logits: higher is better, negative is normal -- only the ORDER matters)")

    print()
    print("-" * 60)
    print("STEP 4: Comparing the two rankings")
    print("-" * 60)
    bi_encoder_order = [
        c["id"] for c in sorted(candidates, key=lambda c: c["similarity"], reverse=True)
    ]
    rerank_order = [c["id"] for c in reranked]
    print(f"  bi-encoder order (cosine similarity):   {bi_encoder_order}")
    print(f"  cross-encoder order (rerank logit):     {rerank_order}")

    bi_encoder_rank = bi_encoder_order.index("deploy-new-release") + 1
    cross_encoder_rank = rerank_order.index("deploy-new-release") + 1
    print(
        f"\n  'deploy-new-release' moved from rank {bi_encoder_rank} (bi-encoder) "
        f"to rank {cross_encoder_rank} (cross-encoder)."
    )
    print(
        "  It shares heavy vocabulary with the query ('deploy', 'release') but "
        "describes pushing a NEW release forward, the opposite of a rollback -- "
        "the cross-encoder reads the query and that chunk together, so it has "
        "the chance to notice that. (This model was trained on web-search "
        "passages, not runbooks, so judge the movement from the numbers above, "
        "mirroring the C1-C5 dry run in Chapter 6 notes section 6.)"
    )


if __name__ == "__main__":
    asyncio.run(main())
