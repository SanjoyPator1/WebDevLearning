# ============================================================
# LISTING: 09_memory_augmentation_compression_forgetting.py  (reference implementation -- FROM SCRATCH)
# BUILDING: Three upkeep jobs on ONE growing memory store, each shown by
#           a search BEFORE and AFTER it runs:
#             augmentation -- store questions that point back at a memory
#             compression  -- k-means (written by hand) finds a group of
#                             near-copies; one summary replaces them
#             forgetting   -- delete stale memories, unless a retention
#                             rule says they must be kept
# REF: Chapter 6 notes, section 12 (Memory Augmentation, Compression,
#      and Forgetting)
# ============================================================
#
# The three jobs fix three DIFFERENT problems, so each gets its own search:
#   augmentation  a memory is worded nothing like the question that needs it
#   compression   many near-copies crowd the top results
#   forgetting    an out-of-date memory still wins the search
#
# Setup, once (with the Ollama app open):
#   ollama pull qwen3-embedding:0.6b
#
# Calls per run: 2 Gemini chat calls (write 3 questions, write 1 summary)
# and 6 local, free embedding requests. No Chroma: the store is a plain
# Python list, so you can see every row.

import asyncio
import os
import re

import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# --- Two clients, two jobs (the same setup as file 8a).
chat_client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
CHAT_MODEL = os.environ["GEMINI_MODEL"]

embedding_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
EMBEDDING_MODEL = "qwen3-embedding:0.6b"
# Qwen3 embedding wants this in front of a SEARCH text only. Stored texts go in plain.
QUERY_INSTRUCTION = "Instruct: Given a question, retrieve stored memories that answer it\nQuery:"

TODAY = "2026-09-22"

# Compression settings. k-means always returns exactly NUM_CLUSTERS groups,
# so a group only gets merged when it is big AND tight (every member very
# close to the group's centre). Distinct memories that merely share a
# topic, like three different incidents, are not tight enough.
NUM_CLUSTERS = 4
MIN_CLUSTER_SIZE = 4
MIN_SIMILARITY_TO_CENTRE = 0.90


async def embed(texts: list[str]) -> list[np.ndarray]:
    """Turns every text into a vector in ONE request, and scales each
    vector to length 1, so cosine similarity is just a dot product.
    Returns: one vector (1024 numbers) per text, in the same order."""
    response = await embedding_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    vectors = [np.array(item.embedding) for item in response.data]
    return [vector / np.linalg.norm(vector) for vector in vectors]


async def embed_query(question: str) -> np.ndarray:
    """One search text, with the instruction in front."""
    return (await embed([QUERY_INSTRUCTION + question]))[0]


# --- The memory store: a list of rows. Every row has "id", "text" and
# "vector". Optional keys:
#   "points_to"     this row is a generated question; the memory it answers
#   "merged_from"   this row is a summary; the ids it replaced
#   "valid_until"   the date after which the fact stops being true
#   "superseded_by" the id of a newer memory that replaces this one
#   "keep_until"    a retention rule: must not be deleted before this date
DEPLOY_MEMORIES = [
    {"id": f"deploy-{241 + i}", "text": f"deploy #{241 + i} succeeded, {3 + i % 3}m{(12 + i * 7) % 60:02d}s, no rollback"}
    for i in range(12)
]
OTHER_MEMORIES = [
    {"id": "inc-1", "text": "payments-service returned 500s for 12 minutes at 3am due to a bad config push"},
    {"id": "inc-2", "text": "search-service latency spiked to 4 seconds after the Elasticsearch heap filled up"},
    {"id": "inc-3", "text": "billing-service lost its database connection for 6 minutes during a failover"},
    {"id": "oncall-1", "text": "Priya is on-call for the week of March 3rd", "valid_until": "2026-03-10"},
    {"id": "oncall-2", "text": "Marcus is on-call for payments-service starting September 15th"},
    {"id": "owner-1", "text": "Priya owns payments-service", "superseded_by": "owner-2"},
    {"id": "owner-2", "text": "Marcus owns payments-service since August 2026"},
    {
        "id": "audit-1",
        "text": "40 customers were double-charged on 2026-02-14; refunds were issued the same day",
        "valid_until": "2026-03-01",
        "keep_until": "2033-02-14",  # payment records must be kept for years
    },
]


async def build_store() -> list[dict]:
    """Embeds all 20 starting memories in one request.
    Returns: the store, a list of row dicts, each with its "vector"."""
    memories = DEPLOY_MEMORIES + OTHER_MEMORIES
    vectors = await embed([memory["text"] for memory in memories])
    store = [{**memory, "vector": vector} for memory, vector in zip(memories, vectors)]
    print(f"Store built: {len(store)} rows, {len(vectors[0])} numbers per vector")
    return store


def search_memories(store: list[dict], query_vector: np.ndarray, top_k: int = 3) -> list[tuple[float, str, str]]:
    """
    Scores every row against the query (cosine = dot product, since all
    vectors have length 1) and returns the top_k MEMORIES. A question row
    counts for the memory it points to, and each memory appears once, at
    its best score.

    Returns: (similarity, memory_id, text_of_the_row_that_matched), best first.
    """
    # your turn:
    #   1. scored = every row as (similarity, row), similarity = float(row["vector"] @ query_vector),
    #      sorted best first
    #   2. walk scored; memory_id = row.get("points_to", row["id"])   <- a question row
    #      counts for the memory it points to
    #      skip it if that memory_id was already added (seen_memory_ids set)
    #      else append (similarity, memory_id, row["text"])
    #   3. stop at top_k results and return them
    # Check: a store with m1, a question row pointing to m1, and m2 returns
    #   m1 once (at the question's score, if that is higher), then m2.
    raise NotImplementedError


def show_search(store: list[dict], query_vector: np.ndarray, label: str) -> None:
    """Prints the top 3 memories for a query."""
    print(f"  {label}:")
    for similarity, memory_id, matched_text in search_memories(store, query_vector):
        print(f"    {similarity:.3f}  {memory_id:<12} matched: {matched_text}")


# ------------------------------------------------------------------
# 1. AUGMENTATION
# ------------------------------------------------------------------
async def augment_memory(store: list[dict], memory_id: str) -> list[str]:
    """
    Asks the chat model for 3 questions this memory answers, embeds them
    as stored texts, and appends one row per question with
    "points_to": memory_id. The original row is not changed.

    Returns: the 3 questions.
    """
    # your turn:
    #   1. memory = the row whose "id" == memory_id
    #   2. ask chat_client (CHAT_MODEL, temperature=0.0) with:
    #        "Given this incident memory, write 3 short questions a teammate might ask
    #         later that this memory should answer. One per line, no numbering.
    #
    #         Memory: <memory text>"
    #   3. split the reply into lines; strip a leading "1." / "2)" / "-" from each
    #      (re.sub(r"^\s*(\d+[.)]|[-*])\s*", "", line)); drop empty lines; keep 3
    #   4. vectors = await embed(questions)     <- plain: they are STORED, not searched
    #   5. for each question, append a row:
    #        {"id": f"{memory_id}-q{number}", "text": question, "vector": vector,
    #         "points_to": memory_id}
    #      and print it
    #   6. return the questions
    raise NotImplementedError


# ------------------------------------------------------------------
# 2. COMPRESSION
# ------------------------------------------------------------------
def kmeans(vectors: np.ndarray, k: int, max_rounds: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """
    k-means on length-1 vectors, written by hand.
      start:  centre 1 is vector 0; each next centre is the vector LEAST
              similar to every centre picked so far (spread them out)
      repeat: (1) give each vector the label of its most similar centre
              (2) move each centre to the mean of its vectors, rescaled to length 1
              until no label changes.

    Args: vectors with shape (n, d), k = number of groups.
    Returns: labels with shape (n,), centres with shape (k, d).
    """
    # your turn:
    #   START (spread the centres out):
    #     centre_indexes = [0]
    #     while fewer than k: best = (vectors @ vectors[centre_indexes].T).max(axis=1)
    #       -> each vector's similarity to its CLOSEST chosen centre, shape (n,)
    #       append int(np.argmin(best))   <- the vector farthest from all centres
    #     centres = vectors[centre_indexes].copy()          shape (k, d)
    #   REPEAT for round_number in 1..max_rounds:
    #     new_labels = np.argmax(vectors @ centres.T, axis=1)   (n, k) -> (n,)
    #     if new_labels equals labels: print that it stopped, break
    #     labels = new_labels
    #     for each cluster: members = vectors[labels == cluster]; if any,
    #       mean = members.mean(axis=0); centres[cluster] = mean / np.linalg.norm(mean)
    #   (start with labels = np.full(len(vectors), -1) so round 1 never matches)
    #   return labels, centres
    # Check: 3 vectors near [1, 0] and 2 near [0, 1] with k=2 -> two groups 3 + 2.
    raise NotImplementedError


def key_numbers(texts: list[str]) -> list[str]:
    """What a good summary of these texts must still contain: how many
    there were, and the shortest and longest durations if they have any
    (like "3m12s")."""
    durations = [match for text in texts for match in re.findall(r"\d+m\d{2}s", text)]
    numbers = [str(len(texts))]
    if durations:
        in_seconds = {d: int(d.split("m")[0]) * 60 + int(d[-3:-1]) for d in durations}
        numbers += [min(durations, key=in_seconds.get), max(durations, key=in_seconds.get)]
    return numbers


async def compress_store(store: list[dict]) -> list[dict]:
    """
    Clusters the original memories (not question or summary rows), and
    replaces each cluster that is big and tight with ONE summary row.
    Other clusters are left alone.

    Returns: the new store.
    """
    # your turn:
    #   1. originals = rows with no "points_to" and no "merged_from"
    #      vectors = np.array of their vectors; labels, centres = kmeans(vectors, NUM_CLUSTERS)
    #   2. for each cluster:
    #        member_indexes = np.flatnonzero(labels == cluster)
    #        lowest_similarity = min of (vectors[member_indexes] @ centres[cluster])
    #        print size, lowest_similarity and the ids
    #        if size < MIN_CLUSTER_SIZE or lowest_similarity < MIN_SIMILARITY_TO_CENTRE:
    #            print "kept as they are" and continue
    #        else: ONE chat call (temperature=0.0):
    #            "Summarize these similar memories into ONE memory, one sentence.
    #             Keep the count and the shortest and longest durations exactly as written."
    #            + the member texts, one per line
    #          for each number in key_numbers(texts): print whether it is in the summary
    #          embed the summary (plain) and make a row
    #            {"id": f"summary-{n}", "text": summary, "vector": ..., "merged_from": [ids]}
    #          remember the member ids as replaced
    #   3. return [rows not replaced, and not pointing at a replaced id] + the summary rows
    raise NotImplementedError


# ------------------------------------------------------------------
# 3. FORGETTING
# ------------------------------------------------------------------
def is_stale(memory_entry: dict, current_date: str) -> bool:
    """
    True when a newer memory replaced this one, or its valid_until date has
    passed. Dates are "YYYY-MM-DD" strings, which sort the same way as the
    dates themselves, so < compares them correctly.
    """
    # your turn:
    #   True if memory_entry.get("superseded_by") is not None
    #   True if memory_entry.get("valid_until") is set and it is < current_date
    #   otherwise False
    # Checks with current_date "2026-09-22":
    #   {"valid_until": "2026-03-10"} -> True    {"superseded_by": "owner-2"} -> True
    #   {"valid_until": "2026-09-22"} -> False   {} -> False
    raise NotImplementedError


def must_keep(memory_entry: dict, current_date: str) -> bool:
    """A retention rule wins over staleness: True while keep_until is in the future."""
    return bool(memory_entry.get("keep_until")) and memory_entry["keep_until"] >= current_date


def forget_stale(store: list[dict], current_date: str) -> tuple[list[dict], list[str]]:
    """
    Deletes every stale row unless must_keep says no, plus any question
    rows that pointed at a deleted memory.

    Returns: (the new store, the ids that were deleted).
    """
    # your turn:
    #   1. forgotten_ids = []
    #   2. for each row that is_stale(row, current_date):
    #        if must_keep(row, current_date): print "stale, but KEPT" with keep_until
    #        else: print "stale, DELETED" with the reason (superseded_by or
    #              valid_until) and add row["id"] to forgotten_ids
    #   3. kept = rows whose id is not forgotten AND whose "points_to" is not forgotten
    #   4. return kept, forgotten_ids
    raise NotImplementedError


async def main() -> None:
    """Builds one store, then runs the three jobs on it, each between a
    search before and a search after."""
    print(f"Chat: {CHAT_MODEL}   Embeddings: {EMBEDDING_MODEL} (local)")
    store = await build_store()

    print("-" * 60)
    print("1. AUGMENTATION: the memory is worded unlike the question")
    print("-" * 60)
    query_vector = await embed_query("how long was payments down?")
    show_search(store, query_vector, "BEFORE  'how long was payments down?'")
    await augment_memory(store, "inc-1")
    show_search(store, query_vector, "AFTER")
    print(f"  store: {len(store)} rows")

    print("-" * 60)
    print("2. COMPRESSION: near-copies crowd the results")
    print("-" * 60)
    query_vector = await embed_query("how have deploys been going lately?")
    show_search(store, query_vector, "BEFORE  'how have deploys been going lately?'")
    rows_before = len(store)
    store = await compress_store(store)
    show_search(store, query_vector, "AFTER")
    print(f"  store: {rows_before} rows -> {len(store)} rows")

    print("-" * 60)
    print(f"3. FORGETTING: out-of-date memories still win (today is {TODAY})")
    print("-" * 60)
    query_vector = await embed_query("who is on call right now?")
    show_search(store, query_vector, "BEFORE  'who is on call right now?'")
    rows_before = len(store)
    store, forgotten_ids = forget_stale(store, TODAY)
    show_search(store, query_vector, "AFTER")
    print(f"  store: {rows_before} rows -> {len(store)} rows (deleted {forgotten_ids})")


if __name__ == "__main__":
    asyncio.run(main())
