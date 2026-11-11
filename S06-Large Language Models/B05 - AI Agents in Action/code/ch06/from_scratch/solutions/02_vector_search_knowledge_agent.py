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


# --- Your turn ---
# 1. Write an async search_runbook(query: str, top_k: int = 3) -> list[dict]
#    that:
#      - embeds `query` with embed_text() (note: Chroma's HttpClient is
#        synchronous -- it's fine to call runbook_collection.query(...)
#        directly inside this async function without awaiting it, that's
#        a deliberate simplification for this learning script, not a bug)
#      - calls runbook_collection.query(query_embeddings=[query_embedding],
#        n_results=top_k)
#      - zips together results["ids"][0], results["documents"][0], and
#        results["distances"][0] into a list of dicts shaped like
#        {"id": ..., "text": ..., "distance": ...} and returns it
#
# 2. Write an async answer_from_runbook(question: str) -> str that:
#      - retrieves the top 3 chunks via search_runbook(question, top_k=3)
#      - builds a context block listing each chunk labeled by its id,
#        e.g. "[Chunk deploy-rollback-1]: <text>"
#      - builds a system prompt instructing the model to answer ONLY from
#        the retrieved chunks, to say "I couldn't find that in the
#        runbook." if the chunks don't contain the answer, and to cite
#        which chunk id supports each claim it makes (strong grounding,
#        per notes section 4)
#      - calls client.chat.completions.create(model=CHAT_MODEL,
#        messages=[...]) with that system prompt and the question, and
#        returns response.choices[0].message.content
#
# 3. Write an async main() that:
#      a. calls await ensure_runbook_ingested()
#      b. runs search_runbook("ERR_5023 payment gateway timeout fix") and
#         prints each retrieved chunk's id, its raw distance (remember:
#         Chroma reports cosine DISTANCE, lower is better, not
#         similarity -- print the raw numbers so this is visible, not
#         just asserted), and a preview of its text
#      c. calls await answer_from_runbook("ERR_5023 payment gateway
#         timeout fix") and prints the grounded answer -- this query
#         should retrieve cleanly, an almost-exact match
#      d. repeats (b) and (c) for a deliberately vague query, e.g.
#         "things seem broken, what do I do?", and prints both the
#         retrieved distances and the generated answer, so you can watch
#         retrieval quality degrade on a vague question compared to a
#         precise one

async def search_runbook(query: str, top_k: int = 3) -> list[dict]:
    """Embed the query and search the Chroma collection for its top_k
    closest chunks by cosine distance.

    Chroma's HttpClient is synchronous, so runbook_collection.query(...)
    below is a plain blocking call even though this function is async --
    a deliberate simplification for this learning script, not a bug.
    """
    query_embedding = await embed_text(query)

    results = runbook_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    retrieved_chunks = []
    for chunk_id, chunk_text, distance in zip(
        results["ids"][0], results["documents"][0], results["distances"][0]
    ):
        retrieved_chunks.append({"id": chunk_id, "text": chunk_text, "distance": distance})
    return retrieved_chunks

async def answer_from_runbook(question: str) -> str:
    """Retrieve the top 3 runbook chunks for `question` and generate a
    STRONGLY grounded answer -- the model is told to answer only from the
    retrieved chunks and to cite which chunk id backs each claim
    (Chapter 6 notes section 4)."""
    top_chunks = await search_runbook(question, top_k=3)

    context_block = "\n\n".join(
        f"[Chunk {chunk['id']}]: {chunk['text']}" for chunk in top_chunks
    )

    system_prompt = (
        "You are the Ops Assistant. Answer ONLY using the runbook excerpts "
        "provided below. Do not use any outside knowledge, even if you are "
        "confident about it. If the excerpts do not contain the answer, "
        "say exactly: \"I couldn't find that in the runbook.\" "
        "When you do answer, mention which chunk id supports each claim."
        f"\n\nRunbook excerpts:\n{context_block}"
    )

    response = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


async def print_retrieved_chunks(query: str):
    """Demo helper: runs search_runbook and prints each hit's id,
    distance, and a text preview, so retrieval quality is visible
    directly rather than just asserted in a comment."""
    print(f"  query: {query!r}")
    retrieved_chunks = await search_runbook(query, top_k=3)
    for chunk in retrieved_chunks:
        # Chroma reports cosine DISTANCE here, not similarity -- lower is
        # a closer match. distance = 1 - cosine_similarity, per Chapter 6
        # notes section 2.
        print(
            f"    id={chunk['id']!r}  distance={chunk['distance']:.4f}  "
            f"text={chunk['text'][:70]!r}..."
        )


async def main():
    print("-" * 60)
    print("STEP 1: Ensuring the runbook corpus is ingested into Chroma")
    print("-" * 60)
    await ensure_runbook_ingested()

    print()
    print("-" * 60)
    print("STEP 2: A precise query -- an almost-exact match ('ERR_5023 ...')")
    print("-" * 60)
    precise_query = "ERR_5023 payment gateway timeout fix"
    await print_retrieved_chunks(precise_query)
    precise_answer = await answer_from_runbook(precise_query)
    print(f"\n  grounded answer:\n  {precise_answer}")

    print()
    print("-" * 60)
    print("STEP 3: A deliberately vague query -- no exact tokens to latch onto")
    print("-" * 60)
    vague_query = "things seem broken, what do I do?"
    await print_retrieved_chunks(vague_query)
    vague_answer = await answer_from_runbook(vague_query)
    print(f"\n  grounded answer:\n  {vague_answer}")

    print(
        "\n  Compare the distances above: the precise query's top hit should "
        "sit clearly closer (a smaller distance) than the vague query's top "
        "hit -- a vague question gives the embedding model less to latch "
        "onto, and retrieval quality degrades accordingly (Chapter 6 notes "
        "section 4)."
    )


if __name__ == "__main__":
    asyncio.run(main())


# TERMINAL OUTPUT

# python 02_vector_search_knowledge_agent.py 
# ------------------------------------------------------------
# STEP 1: Ensuring the runbook corpus is ingested into Chroma
# ------------------------------------------------------------
#     [ingest] embedding and storing 7 runbook chunks...
#     [ingest] done, collection now has 7 docs

# ------------------------------------------------------------
# STEP 2: A precise query -- an almost-exact match ('ERR_5023 ...')
# ------------------------------------------------------------
#   query: 'ERR_5023 payment gateway timeout fix'
#     id='err-5023'  distance=0.1170  text='ERR_5023: payment gateway timeout. This means the retry worker lost it'...
#     id='db-connection-pool'  distance=0.3586  text='Database Connection Pool Exhaustion. Symptoms: ECONNREFUSED errors fro'...
#     id='deploy-rollback-1'  distance=0.4430  text='Rollback procedure: if a deploy causes errors, run `deploy rollback --'...

#   grounded answer:
#   To fix ERR_5023 (payment gateway timeout), restart the retry worker with `restart-worker --name payment-retry` (Chunk err-5023).

# ------------------------------------------------------------
# STEP 3: A deliberately vague query -- no exact tokens to latch onto
# ------------------------------------------------------------
#   query: 'things seem broken, what do I do?'
#     id='deploy-new-release'  distance=0.4286  text='Deploy Runbook: How to Push a New Release. Merge to main, wait for CI '...
#     id='err-5023'  distance=0.4347  text='ERR_5023: payment gateway timeout. This means the retry worker lost it'...
#     id='deploy-rollback-1'  distance=0.4372  text='Rollback procedure: if a deploy causes errors, run `deploy rollback --'...

#   grounded answer:
#   I couldn't find that in the runbook.

#   Compare the distances above: the precise query's top hit should sit clearly closer (a smaller distance) than the vague query's top hit -- a vague question gives the embedding model less to latch onto, and retrieval quality degrades accordingly (Chapter 6 notes section 4).

