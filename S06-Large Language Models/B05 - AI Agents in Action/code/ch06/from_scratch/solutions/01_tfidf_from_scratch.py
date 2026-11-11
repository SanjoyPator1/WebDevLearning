# ============================================================
# LISTING: 01_tfidf_from_scratch.py  (reference implementation -- FROM SCRATCH)
# BUILDING: TF-IDF keyword search implemented by hand: term frequency,
#           inverse document frequency, and a full corpus search that
#           reproduces the chapter's worked "rollback" example exactly.
# REF: Chapter 6 notes, section 3 (From Keyword Counting to Semantic
#      Meaning: TF-IDF and Embeddings)
# ============================================================
#
# This file has no embeddings, no vector database, and no network calls
# at all -- it is pure Python arithmetic. The point is to build the exact
# mechanism a vector database's semantic search is eventually meant to
# improve on, so its specific failure (matching "rollback" but never
# "revert") is something you've seen happen with your own numbers, not
# something you're told about secondhand.

import math

# --- The Ops Assistant's five-entry runbook corpus, exactly as scored by
# hand in the chapter notes. Word counts below assume "on-call" tokenizes
# as one hyphenated token, matching the notes' own tokenization choice.
DEPLOY_ROLLBACK_CORPUS = [
    {
        "id": "doc-1",
        "text": "To deploy the service run the deploy script and monitor logs.",
    },
    {
        "id": "doc-2",
        "text": (
            "If the deploy breaks the service use rollback to the last "
            "stable release."
        ),
    },
    {
        "id": "doc-3",
        "text": (
            "The on-call engineer must acknowledge every alert within "
            "five minutes."
        ),
    },
    {
        "id": "doc-4",
        "text": "Rollback is safer than a hotfix when the deploy causes an outage.",
    },
    {
        "id": "doc-5",
        "text": "Contact the on-call engineer before you deploy on a Friday.",
    },
]


def tokenize(text: str) -> list[str]:
    """Lowercase a piece of text and split it into word tokens, treating a
    hyphenated pair like "on-call" as a single token rather than splitting
    it into "on" and "call". This is a simplified stand-in for a real
    tokenizer, but it reproduces the notes' word counts exactly (e.g.
    doc-3 has 10 tokens, not 11)."""
    cleaned = text.lower().replace(".", "").replace(",", "")
    return cleaned.split()


def term_frequency(term: str, document: str) -> float:
    """How often `term` appears in `document`, relative to the document's
    own length -- so a long document doesn't win just by repeating words
    more times in total.

    Math: TF(t, d) = (count of term t in document d) / (total words in d)
    """
    tokens = tokenize(document)
    return tokens.count(term.lower()) / len(tokens)


def inverse_document_frequency(term: str, corpus: list[dict]) -> float:
    """How rare `term` is across the whole corpus -- a word that shows up
    in every document (like "the") contributes nothing, a word that shows
    up in only one or two documents out of many gets a large boost.

    Math: IDF(t) = ln(N / df(t)), where N is the number of documents in
    the corpus and df(t) is the number of documents containing t at
    least once.
    """
    term = term.lower()
    document_frequency = sum(1 for doc in corpus if term in tokenize(doc["text"]))
    if document_frequency == 0:
        # The term never appears anywhere in the corpus. Term frequency
        # will be 0 for every document too, so the final TF-IDF score is
        # 0 regardless -- this guard only exists to avoid a division by
        # zero in the ratio below.
        return 0.0
    return math.log(len(corpus) / document_frequency)


# --- Your turn ---
# 1. Write tfidf_score(term: str, document: str, corpus: list[dict]) -> float,
#    combining the two functions above:
#        TF-IDF(t, d) = term_frequency(t, document) * inverse_document_frequency(t, corpus)
#    Note `document` is passed as its raw text (a string), while `corpus`
#    is still the full list of doc dicts -- IDF needs to see every
#    document, not just the one currently being scored.
#
# 2. Write search_by_tfidf(query: str, corpus: list[dict], top_k: int = 5)
#    -> list[tuple[str, float]] that:
#      - tokenizes the query into a SET of unique terms (tokenize() above
#        works fine for this too)
#      - for every document in corpus, sums tfidf_score(term, doc["text"], corpus)
#        over every unique query term
#      - returns the top_k (doc_id, score) pairs, highest score first
#    A document that never contains any query term should end up with a
#    score of exactly 0.0 in the returned list, not be silently dropped.
#
# 3. Write a demo, guarded by `if __name__ == "__main__":`, that:
#      a. Prints tfidf_score("rollback", <doc-2 text>, DEPLOY_ROLLBACK_CORPUS)
#         and tfidf_score("rollback", <doc-4 text>, DEPLOY_ROLLBACK_CORPUS),
#         and checks they land at approximately 0.0705 and 0.0764 -- the
#         exact numbers worked out by hand in the chapter notes.
#      b. Runs search_by_tfidf("rollback", DEPLOY_ROLLBACK_CORPUS) and
#         prints the ranked results -- doc-2 and doc-4 should be the only
#         two entries with a nonzero score.
#      c. Runs search_by_tfidf("revert", DEPLOY_ROLLBACK_CORPUS) and prints
#         the ranked results too, to demonstrate TF-IDF's literal-token
#         limitation: "revert" and "rollback" mean nearly the same thing
#         to a human, but every score here comes back 0.0, because
#         TF-IDF only ever counts exact character-for-character matches.

def tfidf_score(term: str, document: str, corpus: list[dict]) -> float:
    """The full TF-IDF score for one term in one document.

    Math: TF-IDF(t, d) = TF(t, d) * IDF(t)
    """
    return term_frequency(term, document) * inverse_document_frequency(term, corpus)

def search_by_tfidf(query: str, corpus: list[dict], top_k: int = 5) -> list[tuple[str, float]]:
    """Score every document in `corpus` against a (possibly multi-word)
    query and return the top_k best matches.

    Math: score(q, d) = sum, over each unique term t in q, of
          TF-IDF(t, d) -- a document's score against the query is just
          the sum of its TF-IDF scores for every distinct query word.

    Returns: a list of (doc_id, score) pairs, highest score first. A
    document that shares no term with the query still appears, with a
    score of exactly 0.0.
    """
    query_terms = set(tokenize(query))

    scored_documents = []
    for doc in corpus:
        score = sum(tfidf_score(term, doc["text"], corpus) for term in query_terms)
        scored_documents.append((doc["id"], score))

    scored_documents.sort(key=lambda pair: pair[1], reverse=True)
    return scored_documents[:top_k]


if __name__ == "__main__":
    print("-" * 60)
    print("STEP 1: Verifying the chapter's hand-worked 'rollback' scores")
    print("-" * 60)

    doc_2_text = next(d["text"] for d in DEPLOY_ROLLBACK_CORPUS if d["id"] == "doc-2")
    doc_4_text = next(d["text"] for d in DEPLOY_ROLLBACK_CORPUS if d["id"] == "doc-4")

    tf_doc_2 = term_frequency("rollback", doc_2_text)
    tf_doc_4 = term_frequency("rollback", doc_4_text)
    idf_rollback = inverse_document_frequency("rollback", DEPLOY_ROLLBACK_CORPUS)
    score_doc_2 = tfidf_score("rollback", doc_2_text, DEPLOY_ROLLBACK_CORPUS)
    score_doc_4 = tfidf_score("rollback", doc_4_text, DEPLOY_ROLLBACK_CORPUS)

    print(f"  TF('rollback', doc-2)     = {tf_doc_2:.4f}   (expected ~0.0769, i.e. 1/13)")
    print(f"  TF('rollback', doc-4)     = {tf_doc_4:.4f}   (expected ~0.0833, i.e. 1/12)")
    print(f"  IDF('rollback')           = {idf_rollback:.4f}   (expected ~0.9163, i.e. ln(5/2))")
    print(f"  TF-IDF('rollback', doc-2) = {score_doc_2:.4f}   (expected ~0.0705)")
    print(f"  TF-IDF('rollback', doc-4) = {score_doc_4:.4f}   (expected ~0.0764)")

    print()
    print("-" * 60)
    print("STEP 2: Searching the runbook corpus for 'rollback'")
    print("-" * 60)
    rollback_results = search_by_tfidf("rollback", DEPLOY_ROLLBACK_CORPUS)
    for doc_id, score in rollback_results:
        print(f"  {doc_id}: score={score:.4f}")

    print()
    print("-" * 60)
    print("STEP 3: Searching the runbook corpus for 'revert' -- TF-IDF's blind spot")
    print("-" * 60)
    revert_results = search_by_tfidf("revert", DEPLOY_ROLLBACK_CORPUS)
    for doc_id, score in revert_results:
        print(f"  {doc_id}: score={score:.4f}")

    print(
        "\n  Every score above is 0.0, even though doc-2 and doc-4 are "
        "exactly the entries a human would point to for 'revert a bad "
        "deploy'. TF-IDF only ever counts literal character-for-character "
        "token matches -- it has no notion that 'revert' and 'rollback' "
        "mean nearly the same thing. This is precisely the gap semantic "
        "embeddings are built to close (see "
        "02_vector_search_knowledge_agent.py)."
    )

# TERMINAL OUTPUT

# python 01_tfidf_from_scratch.py 
# ------------------------------------------------------------
# STEP 1: Verifying the chapter's hand-worked 'rollback' scores
# ------------------------------------------------------------
#   TF('rollback', doc-2)     = 0.0769   (expected ~0.0769, i.e. 1/13)
#   TF('rollback', doc-4)     = 0.0833   (expected ~0.0833, i.e. 1/12)
#   IDF('rollback')           = 0.9163   (expected ~0.9163, i.e. ln(5/2))
#   TF-IDF('rollback', doc-2) = 0.0705   (expected ~0.0705)
#   TF-IDF('rollback', doc-4) = 0.0764   (expected ~0.0764)

# ------------------------------------------------------------
# STEP 2: Searching the runbook corpus for 'rollback'
# ------------------------------------------------------------
#   doc-4: score=0.0764
#   doc-2: score=0.0705
#   doc-1: score=0.0000
#   doc-3: score=0.0000
#   doc-5: score=0.0000

# ------------------------------------------------------------
# STEP 3: Searching the runbook corpus for 'revert' -- TF-IDF's blind spot
# ------------------------------------------------------------
#   doc-1: score=0.0000
#   doc-2: score=0.0000
#   doc-3: score=0.0000
#   doc-4: score=0.0000
#   doc-5: score=0.0000

#   Every score above is 0.0, even though doc-2 and doc-4 are exactly the entries a human would point to for 'revert a bad deploy'. TF-IDF only ever counts literal character-for-character token matches -- it has no notion that 'revert' and 'rollback' mean nearly the same thing. This is precisely the gap semantic embeddings are built to close (see 02_vector_search_knowledge_agent.py).

