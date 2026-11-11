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
    scored = sorted(
        ((float(row["vector"] @ query_vector), row) for row in store),
        key=lambda pair: pair[0],
        reverse=True,
    )
    results = []
    seen_memory_ids = set()
    for similarity, row in scored:
        memory_id = row.get("points_to", row["id"])
        if memory_id in seen_memory_ids:
            continue
        seen_memory_ids.add(memory_id)
        results.append((similarity, memory_id, row["text"]))
        if len(results) == top_k:
            break
    return results


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
    memory = next(row for row in store if row["id"] == memory_id)
    prompt = (
        "Given this incident memory, write 3 short questions a teammate might ask "
        "later that this memory should answer. One per line, no numbering.\n\n"
        f"Memory: {memory['text']}"
    )
    response = await chat_client.chat.completions.create(
        model=CHAT_MODEL, temperature=0.0, messages=[{"role": "user", "content": prompt}]
    )
    lines = (response.choices[0].message.content or "").splitlines()
    # Models sometimes number the lines anyway, so strip "1." or "-" from the front.
    questions = [re.sub(r"^\s*(\d+[.)]|[-*])\s*", "", line).strip() for line in lines]
    questions = [question for question in questions if question][:3]

    vectors = await embed(questions)  # stored texts: no instruction
    for number, (question, vector) in enumerate(zip(questions, vectors), start=1):
        store.append({"id": f"{memory_id}-q{number}", "text": question, "vector": vector, "points_to": memory_id})
        print(f"  added row {memory_id}-q{number} -> {memory_id}: {question}")
    return questions


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
    centre_indexes = [0]
    while len(centre_indexes) < k:
        best_similarity_to_a_centre = (vectors @ vectors[centre_indexes].T).max(axis=1)  # (n,)
        centre_indexes.append(int(np.argmin(best_similarity_to_a_centre)))
    centres = vectors[centre_indexes].copy()  # (k, d)

    labels = np.full(len(vectors), -1)
    for round_number in range(1, max_rounds + 1):
        new_labels = np.argmax(vectors @ centres.T, axis=1)  # (n, d) @ (d, k) -> (n, k) -> (n,)
        if np.array_equal(new_labels, labels):
            print(f"  k-means: k={k}, no label changed in round {round_number}, so it stopped")
            break
        labels = new_labels
        for cluster in range(k):
            members = vectors[labels == cluster]
            if len(members):  # an empty group keeps its old centre
                mean = members.mean(axis=0)
                centres[cluster] = mean / np.linalg.norm(mean)
    else:
        print(f"  k-means: k={k}, stopped at the {max_rounds}-round limit")
    return labels, centres


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
    originals = [row for row in store if "points_to" not in row and "merged_from" not in row]
    vectors = np.array([row["vector"] for row in originals])
    labels, centres = kmeans(vectors, NUM_CLUSTERS)

    replaced_ids: set[str] = set()
    summaries = []
    for cluster in range(NUM_CLUSTERS):
        member_indexes = np.flatnonzero(labels == cluster)
        members = [originals[i] for i in member_indexes]
        lowest_similarity = float((vectors[member_indexes] @ centres[cluster]).min())
        print(f"  cluster {cluster}: {len(members)} rows, lowest similarity to centre "
              f"{lowest_similarity:.3f}: {[row['id'] for row in members]}")
        if len(members) < MIN_CLUSTER_SIZE or lowest_similarity < MIN_SIMILARITY_TO_CENTRE:
            print("    -> kept as they are (too few, or not near-copies)")
            continue

        texts = [row["text"] for row in members]
        prompt = (
            "Summarize these similar memories into ONE memory, one sentence. "
            "Keep the count and the shortest and longest durations exactly as written.\n\n"
            + "\n".join(texts)
        )
        response = await chat_client.chat.completions.create(
            model=CHAT_MODEL, temperature=0.0, messages=[{"role": "user", "content": prompt}]
        )
        summary = (response.choices[0].message.content or "").strip()
        print(f"    -> merged into one summary: {summary}")
        for number in key_numbers(texts):
            print(f"       summary still says {number!r}? {number in summary}")

        [summary_vector] = await embed([summary])
        summaries.append({
            "id": f"summary-{len(summaries) + 1}", "text": summary,
            "vector": summary_vector, "merged_from": [row["id"] for row in members],
        })
        replaced_ids.update(row["id"] for row in members)

    # Drop the replaced rows, and any question rows that pointed at them.
    kept = [row for row in store if row["id"] not in replaced_ids and row.get("points_to") not in replaced_ids]
    return kept + summaries


# ------------------------------------------------------------------
# 3. FORGETTING
# ------------------------------------------------------------------
def is_stale(memory_entry: dict, current_date: str) -> bool:
    """
    True when a newer memory replaced this one, or its valid_until date has
    passed. Dates are "YYYY-MM-DD" strings, which sort the same way as the
    dates themselves, so < compares them correctly.
    """
    if memory_entry.get("superseded_by") is not None:
        return True
    if memory_entry.get("valid_until") and memory_entry["valid_until"] < current_date:
        return True
    return False


def must_keep(memory_entry: dict, current_date: str) -> bool:
    """A retention rule wins over staleness: True while keep_until is in the future."""
    return bool(memory_entry.get("keep_until")) and memory_entry["keep_until"] >= current_date


def forget_stale(store: list[dict], current_date: str) -> tuple[list[dict], list[str]]:
    """
    Deletes every stale row unless must_keep says no, plus any question
    rows that pointed at a deleted memory.

    Returns: (the new store, the ids that were deleted).
    """
    forgotten_ids = []
    for row in store:
        if not is_stale(row, current_date):
            continue
        if must_keep(row, current_date):
            print(f"  {row['id']:<12} stale, but KEPT: retention until {row['keep_until']}")
        else:
            reason = (f"replaced by {row['superseded_by']}" if row.get("superseded_by")
                      else f"valid only until {row['valid_until']}")
            print(f"  {row['id']:<12} stale, DELETED: {reason}")
            forgotten_ids.append(row["id"])
    kept = [row for row in store if row["id"] not in forgotten_ids and row.get("points_to") not in forgotten_ids]
    return kept, forgotten_ids


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
