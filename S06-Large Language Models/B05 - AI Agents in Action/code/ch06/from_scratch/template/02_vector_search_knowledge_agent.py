# ============================================================
# LISTING: 02_vector_search_knowledge_agent.py  (reference implementation -- FROM SCRATCH)
# BUILDING: A vector-search knowledge agent over the Ops Assistant's
#           runbook -- real embeddings, a real Chroma vector database,
#           and a grounded-generation call constrained to answer only
#           from retrieved chunks.
# REF: Chapter 6 notes, section 4 (Building a Vector-Search Knowledge
#      Agent, and Where It Breaks)
# ============================================================
#
# This is the star file of the chapter: everything earlier sections
# explained by hand -- embed, store, search by cosine distance, augment
# the prompt -- gets wired together here into something you can actually
# run against a live embedding model and a live vector database. The
# demo at the bottom is deliberately honest about where this simple
# design starts to strain, per section 4's "Where It Breaks" discussion.

import asyncio
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


async def search_runbook(query: str, top_k: int = 3) -> list[dict]:
    """Embed the query and search the Chroma collection for its top_k
    closest chunks by cosine distance.

    Chroma's HttpClient is synchronous, so runbook_collection.query(...)
    below is a plain blocking call even though this function is async --
    a deliberate simplification for this learning script, not a bug.
    """
    # your turn:
    #   1. embed `query` with embed_text()
    #   2. call runbook_collection.query(query_embeddings=[query_embedding],
    #      n_results=top_k) directly -- no await, Chroma's HttpClient is
    #      synchronous
    #   3. zip together results["ids"][0], results["documents"][0], and
    #      results["distances"][0] into a list of dicts shaped like
    #      {"id": ..., "text": ..., "distance": ...} and return it
    raise NotImplementedError


async def answer_from_runbook(question: str) -> str:
    """Retrieve the top 3 runbook chunks for `question` and generate a
    STRONGLY grounded answer -- the model is told to answer only from the
    retrieved chunks and to cite which chunk id backs each claim
    (Chapter 6 notes section 4)."""
    # your turn:
    #   1. retrieve the top 3 chunks via search_runbook(question, top_k=3)
    #   2. build a context block listing each chunk labeled by its id,
    #      e.g. "[Chunk deploy-rollback-1]: <text>"
    #   3. build a system prompt instructing the model to answer ONLY from
    #      the retrieved chunks, to say "I couldn't find that in the
    #      runbook." if the chunks don't contain the answer, and to cite
    #      which chunk id supports each claim it makes (strong grounding,
    #      per notes section 4)
    #   4. call client.chat.completions.create(model=CHAT_MODEL,
    #      messages=[...]) with that system prompt and the question, and
    #      return response.choices[0].message.content
    raise NotImplementedError


async def main() -> None:
    """Entry point: ingest, then compare a precise query against a
    deliberately vague one, showing raw distances and grounded answers."""
    # your turn:
    #   a. await ensure_runbook_ingested()
    #   b. run search_runbook("ERR_5023 payment gateway timeout fix") and
    #      print each retrieved chunk's id, its raw distance (remember:
    #      Chroma reports cosine DISTANCE, lower is better, not
    #      similarity -- print the raw numbers so this is visible, not
    #      just asserted), and a preview of its text
    #   c. await answer_from_runbook("ERR_5023 payment gateway timeout
    #      fix") and print the grounded answer -- this query should
    #      retrieve cleanly, an almost-exact match
    #   d. repeat (b) and (c) for a deliberately vague query, e.g.
    #      "things seem broken, what do I do?", and print both the
    #      retrieved distances and the generated answer, so you can watch
    #      retrieval quality degrade on a vague question compared to a
    #      precise one
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
