# ============================================================
# LISTING: 03_hybrid_search_rrf.py  (reference implementation -- FROM SCRATCH)
# BUILDING: Hybrid search -- a TF-IDF keyword search and a Chroma vector
#           search run side by side over the same runbook corpus, fused
#           into one ranked list with Reciprocal Rank Fusion (RRF).
# REF: Chapter 6 notes, section 5 (Hybrid Search: Combining Keyword and
#      Vector Retrieval)
# ============================================================
#
# Keyword search and vector search disagree in specific, predictable ways
# -- a keyword search catches exact tokens a vector search can blur past,
# and a vector search catches paraphrases a keyword search can't see at
# all. RRF reconciles two ranked lists using only rank position, never
# forcing a TF-IDF score and a cosine similarity onto the same scale.
# This file assumes 02_vector_search_knowledge_agent.py's
# ensure_runbook_ingested() has already been run against the shared
# Chroma collection, but calls it again itself too, so it is
# independently runnable either way.

import asyncio
import math
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

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


# --- TF-IDF keyword scoring, reimplemented locally rather than imported
# from 01_tfidf_from_scratch.py, per this chapter's self-contained-files
# convention. See that file for the fully worked-out version of the same
# math, including the hand-verified "rollback" example.
def _tokenize(text: str) -> list[str]:
    """Lowercase and split into word tokens, treating a hyphenated pair
    like "on-call" as one token."""
    cleaned = text.lower().replace(".", "").replace(",", "").replace("`", "")
    return cleaned.split()


def _term_frequency(term: str, document: str) -> float:
    """TF(t, d) = (count of t in d) / (total words in d)."""
    tokens = _tokenize(document)
    return tokens.count(term.lower()) / len(tokens)


def _inverse_document_frequency(term: str, corpus: list[dict]) -> float:
    """IDF(t) = ln(N / df(t))."""
    term = term.lower()
    document_frequency = sum(1 for doc in corpus if term in _tokenize(doc["text"]))
    if document_frequency == 0:
        return 0.0
    return math.log(len(corpus) / document_frequency)


def _tfidf_score(term: str, document: str, corpus: list[dict]) -> float:
    """TF-IDF(t, d) = TF(t, d) * IDF(t)."""
    return _term_frequency(term, document) * _inverse_document_frequency(term, corpus)


def search_keyword(query: str, top_k: int = 5) -> list[str]:
    """Rank RUNBOOK_DOCS against `query` using summed TF-IDF scores -- the
    "stickler for exact wording" coworker from Chapter 6 notes section 5.
    Only documents with a nonzero score are returned: a document that
    shares no literal token with the query has no business appearing in
    a keyword-search ranked list at all, matching how R19 was simply
    absent from the keyword list in the notes' dry run.

    Returns: a list of doc ids, best match first.
    """
    query_terms = set(_tokenize(query))
    scored_docs = []
    for doc in RUNBOOK_DOCS:
        score = sum(_tfidf_score(term, doc["text"], RUNBOOK_DOCS) for term in query_terms)
        if score > 0.0:
            scored_docs.append((doc["id"], score))

    scored_docs.sort(key=lambda pair: pair[1], reverse=True)
    return [doc_id for doc_id, _score in scored_docs[:top_k]]


async def search_vector(query: str, top_k: int = 5) -> list[str]:
    """Embed the query and ask Chroma for its top_k closest chunks by
    cosine distance, returning just the ranked doc ids -- the "big-picture
    thinker" coworker from Chapter 6 notes section 5. Chroma already
    returns hits ordered closest-first, so there's no re-sorting to do
    here."""
    # your turn: embed `query` with embed_text(), call
    # runbook_collection.query(query_embeddings=[...], n_results=top_k),
    # and return results["ids"][0] as a plain list of doc ids, best
    # (smallest cosine distance) match first -- this is mostly unpacking
    # the response shape
    raise NotImplementedError


def reciprocal_rank_fusion(
    keyword_ranked_ids: list[str], vector_ranked_ids: list[str], k: int = 60
) -> list[tuple[str, float]]:
    """Fuse two ranked lists of document IDs into one ranked list using
    Reciprocal Rank Fusion -- see Chapter 6 notes section 5 for the full
    derivation and a hand-worked dry run.

    Math: RRF(d) = sum, over each list containing d, of
          1 / (k + rank_in_list(d)) -- a list that never contains d
          simply contributes nothing to the sum, not a very large rank.
          k=60 is the conventional smoothing constant: it flattens the
          difference between adjacent ranks so being 40th instead of 41st
          barely matters, while still letting top positions dominate.
    """
    # your turn: match Chapter 6 notes section 5 EXACTLY:
    #     RRF(d) = sum over each list containing d of 1 / (k + rank_in_list(d))
    # where rank is the 1-indexed position of d in that list, and a list
    # that never contains d simply contributes nothing to the sum (not a
    # very large rank). Return (doc_id, fused_score) pairs sorted by
    # score descending.
    raise NotImplementedError


async def main() -> None:
    """Entry point: run keyword search and vector search side by side,
    fuse them with RRF, and print all three rankings."""
    # your turn:
    #   a. await ensure_runbook_ingested()
    #   b. define query = "database connection pool exhausted, need
    #      restart steps"
    #   c. compute keyword_ranked = search_keyword(query, top_k=5) and
    #      vector_ranked = await search_vector(query, top_k=5)
    #   d. compute fused = reciprocal_rank_fusion(keyword_ranked,
    #      vector_ranked)
    #   e. print keyword_ranked, vector_ranked, and fused side by side,
    #      with rank numbers and fused scores, so you can see where the
    #      two lists agree, where they disagree, and how RRF reconciles
    #      them -- mirroring the R12/R31/R7/R19 shape from the notes:
    #      expect at least one doc that ranks well in both lists (a clear
    #      winner), one that ranks well in only one list, and possibly
    #      one that's entirely absent from the keyword list because it
    #      shares no literal token with the query at all
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
