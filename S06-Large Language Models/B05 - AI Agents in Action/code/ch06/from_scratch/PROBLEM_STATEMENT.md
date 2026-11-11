# Chapter 6 — From Scratch: Problem Statements

## Table of Contents

1. [TF-IDF From Scratch — and Its Blind Spot](#1-tf-idf-from-scratch--and-its-blind-spot)
2. [A Real Vector-Search Knowledge Agent](#2-a-real-vector-search-knowledge-agent)
3. [Hybrid Search: Keyword + Vector, Fused by Rank](#3-hybrid-search-keyword--vector-fused-by-rank)
4. [Reranking: A Second, Smarter Pass](#4-reranking-a-second-smarter-pass)
5. [Smarter Chunking: Contextual Retrieval and Late Chunking](#5-smarter-chunking-contextual-retrieval-and-late-chunking)
6. [Agentic RAG: Judge the Retrieval, Then Retry](#6-agentic-rag-judge-the-retrieval-then-retry)
7. [Graph Memory: Walking Relationships](#7-graph-memory-walking-relationships)
8. [Hybrid Semantic + Graph Memory, Plus OS-Inspired Paging](#8-hybrid-semantic--graph-memory-plus-os-inspired-paging)
   - [8a: Hybrid Memory, the Simple Version](#8a-hybrid-memory-the-simple-version)
9. [Memory Augmentation, Compression, and Forgetting](#9-memory-augmentation-compression-and-forgetting)

**Theory**

- [Theory 01: TF-IDF, Scoring Words by How Special They Are](#theory-01-tf-idf-scoring-words-by-how-special-they-are)
- [Theory 02: Vector Search and Grounded Answers](#theory-02-vector-search-and-grounded-answers)
- [Theory 03: Hybrid Search and Reciprocal Rank Fusion](#theory-03-hybrid-search-and-reciprocal-rank-fusion)
- [Theory 04: Reranking With a Cross-Encoder](#theory-04-reranking-with-a-cross-encoder)
- [Theory 05: Smarter Chunking: Contextual Retrieval and Late Chunking](#theory-05-smarter-chunking-contextual-retrieval-and-late-chunking)
- [Theory 06: Agentic RAG, Judging the Retrieval Before Answering](#theory-06-agentic-rag-judging-the-retrieval-before-answering)
- [Theory 07: Graph Memory, Facts as Connected Dots](#theory-07-graph-memory-facts-as-connected-dots)
- [Theory 08: Hybrid Memory and Paging, Two Stores and a Small Window](#theory-08-hybrid-memory-and-paging-two-stores-and-a-small-window)
- [Theory 08a: Hybrid Memory, the Simple Version](#theory-08a-hybrid-memory-the-simple-version)
- [Theory 09: Keeping a Memory Store Healthy](#theory-09-keeping-a-memory-store-healthy)

Each entry below is one file under `template/`. Work through them roughly in order — search techniques build on each other (1 → 6), then memory techniques build on each other (7 → 9). Every file uses a raw `AsyncOpenAI` client (Gemini by default, Ollama as a fallback) — never an agents framework. When you're done with a file, compare it against `solved/` of the same name. Don't peek before you try.

**Before running anything in files 2–5, 8 and 8a**, start a real Chroma vector database in Docker (file 6 keeps its vectors in memory and does not need it). Files 8, 8a and 9 also need Ollama running with an embedding model pulled (`ollama pull qwen3-embedding:0.6b`), because they turn text into numbers locally and only use Gemini for the chat calls (see Problem 8):
```
docker run -d --name ch06-chroma -p 8000:8000 chromadb/chroma
```
Stop it later with `docker stop ch06-chroma && docker rm ch06-chroma`. Files 1 and 7 make no network calls at all. File 9 keeps its store in a Python list, so it needs Ollama but not Chroma.

**Files 4 and 5 each run a small model locally.** File 4 needs one extra package (a real reranker): `pip install sentence-transformers`. File 5 needs no extra package, but its first run downloads a ~600 MB embedding model from Hugging Face (details in problem 5).

The whole set shares one running example: the Ops Assistant's own runbook and incident memory for a fictional set of services (`payments-service`, an EU deploy cluster, and so on) — the same seven-chunk runbook corpus reappears, verbatim, in files 2 through 4. Files 5 and 6 add an eighth chunk, the drain-then-restart passage.

---

## 1: TF-IDF From Scratch — and Its Blind Spot

**File:** `01_tfidf_from_scratch.py`

### The Intuition

This file has no embeddings and no network calls — pure arithmetic, so TF-IDF's specific failure mode is something you compute yourself, not something you're told about. The goal is to build the exact mechanism semantic search is meant to improve on, then watch it fail on a real query.

### What You're Building

1. `term_frequency(term, document) -> float`: `(count of term in document) / (total words in document)`.
2. `inverse_document_frequency(term, corpus) -> float`: `ln(N / df(t))`, where `N` is the corpus size and `df(t)` is how many documents contain the term at least once (guard against `df(t) == 0` to avoid a division error).
3. `tfidf_score(term, document, corpus) -> float`: `TF(t, d) * IDF(t)`.
4. `search_by_tfidf(query, corpus, top_k) -> list[tuple[str, float]]`: tokenize the query into a set of unique terms, sum each document's TF-IDF score across every query term, sort descending, return the top `top_k` (including documents that score exactly `0.0`).

### Example

**Input:** a 5-document runbook corpus about deploys/rollbacks/on-call, searched for `"rollback"`.

**Expected output (hand-verifiable):**
```
TF('rollback', doc-2)     = 0.0769   (i.e. 1/13)
TF('rollback', doc-4)     = 0.0833   (i.e. 1/12)
IDF('rollback')           = 0.9163   (i.e. ln(5/2))
TF-IDF('rollback', doc-2) = 0.0705
TF-IDF('rollback', doc-4) = 0.0764

STEP 2: Searching the runbook corpus for 'rollback'
  doc-4: score=0.0764
  doc-2: score=0.0705
  doc-1: score=0.0000
  doc-3: score=0.0000
  doc-5: score=0.0000
```

**Now search the exact same corpus for `"revert"` instead:**
```
STEP 3: Searching the runbook corpus for 'revert' -- TF-IDF's blind spot
  doc-1: score=0.0000
  doc-2: score=0.0000
  doc-3: score=0.0000
  doc-4: score=0.0000
  doc-5: score=0.0000
```

Every score is exactly `0.0`, even though doc-2 and doc-4 are precisely the entries a human would point to for "revert a bad deploy" — TF-IDF only ever counts literal token matches, with zero notion that "revert" and "rollback" mean nearly the same thing.

---

## 2: A Real Vector-Search Knowledge Agent

**File:** `02_vector_search_knowledge_agent.py`

### The Intuition

This is the file where everything explained by hand elsewhere gets wired into something you actually run: real embeddings, a real Chroma server, and a generation call that's told to answer *only* from what it retrieved. It's also deliberately honest about where this simple design starts to strain — watch how retrieval quality changes between a precise query and a vague one.

### What You're Building

1. `embed_text(text) -> list[float]`: one call to `client.embeddings.create(model=EMBEDDING_MODEL, input=text)`.
2. `ensure_runbook_ingested()`: if the Chroma collection (`ops_assistant_runbook`, `hnsw:space: "cosine"`) is already non-empty, skip; otherwise embed and `.add(...)` all 7 fixed `RUNBOOK_DOCS` entries.
3. `search_runbook(query, top_k) -> list[dict]`: embed the query, call `.query(query_embeddings=..., n_results=top_k)` on the collection, and zip `ids`/`documents`/`distances` back into a list of `{"id", "text", "distance"}` dicts.
4. `answer_from_runbook(question) -> str`: retrieve the top 3 chunks, build a system prompt that instructs the model to answer *only* from the provided excerpts (with an exact fallback sentence — `"I couldn't find that in the runbook."` — if the excerpts don't cover it), and cite which chunk id backs each claim.

### Example

**Input (precise query):** `"ERR_5023 payment gateway timeout fix"`

**Expected shape:** the top hit should be `err-5023` at a noticeably small distance, and the grounded answer should reference restarting the retry worker, citing that chunk id.

**Input (vague query):** `"things seem broken, what do I do?"`

**Expected shape:** the top hit's distance should be visibly larger (a worse match) than the precise query's top hit — a vague question gives the embedding model less to latch onto, and retrieval quality degrades measurably, not just in theory.

Remember: Chroma reports cosine **distance**, not similarity — lower means closer. If your printed distances look backwards (a "worse" match reporting a smaller number than a "better" one), double check you're not accidentally sorting or comparing the wrong direction.

---

## 3: Hybrid Search: Keyword + Vector, Fused by Rank

**File:** `03_hybrid_search_rrf.py`

### The Intuition

Keyword search and vector search fail in complementary, predictable ways — one catches exact tokens the other blurs past, the other catches paraphrases the first can't see at all. Reciprocal Rank Fusion (RRF) reconciles the two ranked lists using only rank *position*, deliberately never trying to force a TF-IDF score and a cosine similarity onto one shared scale (they aren't comparable numbers at all).

### What You're Building

1. A local (self-contained, not imported) copy of the TF-IDF functions from file 1, plus `search_keyword(query, top_k) -> list[str]`: rank the runbook corpus by summed TF-IDF score, returning **only** doc ids with a nonzero score (a document sharing no literal token with the query has no business appearing in a keyword-ranked list at all).
2. `search_vector(query, top_k) -> list[str]`: embed the query, query Chroma, return just the ranked doc ids (Chroma already returns closest-first).
3. `reciprocal_rank_fusion(keyword_ranked_ids, vector_ranked_ids, k=60) -> list[tuple[str, float]]`: for every doc id appearing in either list, sum `1 / (k + rank)` across whichever list(s) contain it — a list that never contains a given id simply contributes nothing to its score, not an artificially large rank penalty.

### Example

**Input:** `"database connection pool exhausted, need restart steps"`

**Expected output (shape):**
```
KEYWORD RESULTS (TF-IDF), best first: ['db-connection-pool', ...]
VECTOR RESULTS (cosine distance), best first: ['db-connection-pool', 'err-5023', ...]

doc_id                keyword rank   vector rank    fused score
db-connection-pool     1              1              0.0327869
...
```

The doc that ranks well in **both** lists should win the fused ranking outright — watch for a doc that's the single best result in only one list, or entirely absent from the keyword list (because it shares no literal token with the query), ending up further down once its absence from the other list is properly accounted for.

---

## 4: Reranking: A Second, Smarter Pass

**File:** `04_reranking.py`

### The Intuition

Every retrieval method built so far (TF-IDF, vector search, hybrid RRF) is a **bi-encoder** under the hood: query and document get scored independently, then compared, without either one ever "seeing" the other. A **cross-encoder** reads a query and one document **together**, as a single input, and outputs one relevance number. This file loads a real one, `cross-encoder/ms-marco-MiniLM-L-6-v2` from the `sentence-transformers` library, and uses it to re-order the vector-search candidates. It runs on your own machine, so the reranking step makes no API call and costs nothing; the only live call in the file is the one query embedding in the first-pass search.

### What You're Building

1. `search_top_candidates(query, top_k) -> list[dict]` (given): the usual embed-and-query bi-encoder pass, converting each returned distance back into a similarity (`1 - distance`).
2. `rerank_with_cross_encoder(query, candidates, top_n) -> list[dict]` (you write it): build one `(query, chunk_text)` pair per candidate, score all the pairs with a **single** `reranker.predict(pairs)` call, and attach two values to each candidate: `rerank_score` (the raw score the model returns, called a *logit*) and `rerank_relevance` (the sigmoid of that logit, squashed into 0 to 1 for readability). Sort by `rerank_score` descending and return the top `top_n`. It is a plain synchronous function, because the model runs locally and there is nothing to await.
3. `main()`: ingest, run the first pass, rerank, and print both orderings side by side.

The raw scores are **logits**: higher means more relevant, and it is completely normal for all of them to be negative. Only the order matters. The sigmoid, $\sigma(z) = 1 / (1 + e^{-z})$, never changes the order; it only makes the numbers easier to read.

**Setup (one time, inside the repo's `.venv`):**
```
pip install sentence-transformers
```
The model weights (about 90 MB) download from Hugging Face the first time they are used, then load from the local cache.

### Example

**Input:** `"how do we roll back a bad deploy"`

**Expected output (shape; your exact numbers will differ):**
```
STEP 2: Bi-encoder first pass (vector search)
  id=...   similarity=0.xxxx   <- cosine similarity, between 0 and 1
  ...

STEP 3: Cross-encoder second pass (real model, runs locally)
  id=...   rerank_score=  x.xxxx   relevance=0.xxxx   <- raw logit, may be negative
  ...

STEP 4: Comparing the two rankings
  bi-encoder order:     [...]
  cross-encoder order:  [...]
```

Watch `deploy-new-release` specifically. It shares heavy vocabulary with the query ("deploy", "release") so it can score respectably on raw cosine similarity, but it describes pushing a **new** release forward, the opposite of a rollback. The cross-encoder reads the query and that chunk together, so it has the chance to notice that and move it down.

Be honest about what you see. This model was trained on web-search passages, not runbooks, so it may not demote that chunk as hard as a large language model would. If the order barely changes, that is a finding about the model and this tiny corpus, not a bug in your code. Compare the two **orderings**, not the raw numbers: cosine similarity and a logit are on different scales.

---

## 5: Smarter Chunking: Contextual Retrieval and Late Chunking

**File:** `05_smarter_chunking.py`

### The Intuition

Fixed-size chunking cuts a document by word count without ever looking at what the text says — and this file builds a chunk that breaks *because* of that, on purpose, then fixes it two different ways. **Contextual retrieval** adds words: an LLM writes a short note saying what an ambiguous pronoun refers to, and that note is stuck onto the chunk before embedding. **Late chunking** adds no words at all: it runs the *whole* passage through a local embedding model in one pass, keeps one vector per token, and only then averages the token vectors that belong to each chunk. Because every token was processed next to every other token, chunk 2's vector was computed while the model could still see the drain sentence in chunk 1.

```text
CONTEXTUAL RETRIEVAL                      LATE CHUNKING
split, then add words, then embed         embed everything, then split

 chunk 2 ──► LLM writes a note             whole passage ──► ONE model pass
              │                                              │
              ▼                                              ▼
   embed( note + chunk 2 )                 64 token vectors (one per token)
                                                             │
                                          chunk 1 tokens │ chunk 2 tokens
                                                             │
                                                  average each group ──► one vector per chunk
```

### What You're Building

1. `split_into_fixed_size_word_chunks(text, words_per_chunk) -> list[str]` *(given)*: naive word-count chunking, no sentence-boundary awareness. Applied at 20 words/chunk to a specific runbook passage, the cut lands right after the word "Once," — leaving chunk 2 starting with a dangling "it" that has no antecedent inside that chunk alone.
2. `build_contextual_chunk(chunk_text, document_summary) -> str`: one LLM call generating a 2–3 sentence note describing where this excerpt sits in its source document, put in front of the original chunk text — `embed(note + chunk)` instead of `embed(chunk)`.
3. `run_contextual_chunking_demo()`: ingests the **same** chunk 2 twice into two separate Chroma collections — once plain, once with the note in front — then queries both with the same ambiguous question and compares similarity scores side by side. This half uses Gemini embeddings and Chroma, like files 2 to 4.
4. `embed_all_tokens(text, prefix) -> (token_vectors, token_offsets)`: the "embed first" half of late chunking. One forward pass of the local model over the whole text, returning one 768-number vector per token and the character span each token covers.
5. `pool_span(token_vectors, token_offsets, char_span) -> list[float]`: the "split late" half. Averages the vectors of the tokens whose characters fall inside one chunk's span.
6. `cosine_similarity(vector_a, vector_b) -> float`: plain dot-product-over-norms, used to compare the local-model vectors directly.
7. `run_late_chunking_demo()`: embeds the passage once, pools chunk 2's span, also embeds chunk 2 on its own for comparison, then scores both against five questions. Everything here runs on your machine: no API call, no Chroma.

`embed_text_locally` (ordinary embedding with the same local model), the model loading, and the list of five questions are already written for you.

**Setup:** this file needs no extra package (it uses `torch` and `transformers`, already in the repo's `.venv`), but the first run downloads the embedding model `nomic-ai/modernbert-embed-base` (about 600 MB) from Hugging Face. After that it loads from the local cache. It reads up to 8192 tokens at once, produces 768-number vectors, and was trained to average its token vectors into one text vector — which is exactly what late chunking needs. It **requires** a prefix on every input: `search_document: ` in front of passages and `search_query: ` in front of questions. Its vectors live in their own space, so questions must be embedded with this same model to be compared against these chunk vectors, never against the Gemini vectors from the contextual demo.

### Example

**Input query (contextual demo):** `"what do I do after the drain step finishes?"`

**Expected fixed-size split:**
```
CHUNK 1: 'Drain traffic from the load balancer using lb-drain --host prod-3. This takes about 90 seconds while in-flight requests finish. Once'
CHUNK 2: 'it completes, restart the deploy service using the same command from step 2, adding the --skip-migrations flag this time.'   <- 'it' has no antecedent in this chunk alone
```

**Expected contextual-retrieval result (shape):**
```
plain chunk        similarity = 0.7xxx
contextual chunk   similarity = 0.8xxx
-> the contextual version scores higher: spelling out what 'it' refers
   to gave the embedding something to hold onto.
```

**How the late-chunking pass splits the passage (one real run):**
```
64 tokens in total = 1 start marker + 4 prefix tokens + 31 tokens of chunk 1
                     + 27 tokens of chunk 2 + 1 end marker
chunk 2 span (133, 254) covers 27 tokens   <- the same 27 words as chunk 2 alone
late vs. alone vector for the SAME words: cosine = 0.7233
```
That last line is the point: the same 27 tokens give two clearly different vectors, because in one case the model had also seen chunk 1.

**Late-chunking result over five questions (one real run; your last digits may differ slightly):**
```
query                                                              alone    late    late - alone
what do I do after the drain step finishes?                        0.4056   0.4023   -0.0033
what happens once the load balancer drain completes?               0.3346   0.5754   +0.2407
what should I do when the lb-drain command is done?                0.3851   0.5720   +0.1869
how do I restart the deploy service after the drain finishes?      0.6357   0.6137   -0.0220
which flag do I add when restarting the deploy service ...?        0.6381   0.5743   -0.0638
late chunking scored higher on 2 of 5 queries; mean (late - alone) = +0.0677
```

Read this honestly rather than as a victory lap. Late chunking made a big difference on the two questions that talk only about the drain, which chunk 2 never names: the late vector carries the drain meaning in from chunk 1. It was roughly level or slightly worse on the questions that already use chunk 2's own words ("restart the deploy service", "flag"), because mixing in the drain meaning dilutes words the chunk matched well on its own. The very first question came out as a tie. So the lesson is not "late chunking always wins" but "late chunking helps most when the question depends on context the chunk alone is missing", and one number from one question tells you very little — the trend across several questions is what matters. Contextual retrieval is the same kind of fix, and the contextual demo above should be read the same way.

---

## 6: Agentic RAG: Judge the Retrieval, Then Retry

**File:** `06_agentic_rag.py`

### The Intuition

Naive RAG retrieves once and generates once, no matter how weak the retrieval was, so a poor match gets answered just as confidently as a good one. This file adds one deliberate step in between: an explicit judgment call asking "does this retrieved context contain what is needed to answer the question?", and a rewritten search query when the answer is no. It is run on four kinds of question so you can *see* what the judge does instead of assuming it. The fourth is the case a rewrite really exists for: a follow-up like "what if that doesn't work?", which has no searchable content on its own, because what "that" means lives only in the earlier conversation.

```text
question ──► search ──► JUDGE: is this enough? ──┬─ yes ──► answer from these chunks
   +             ▲                               │
 earlier         │                               └─ no ──► a NEW query? ─┬─ yes ─► search again
 conversation    └──────────────────────────────────────────────────────┘        (max 3 tries)
                                                                         └─ no ──► stop, say so
```

Three rules keep the loop honest. Only the **search** uses the rewritten query: the judge and the final answer always use the user's original question (and the conversation it came from). A rewrite can add information that exists somewhere, such as the earlier conversation, but it cannot invent what nobody said. And the loop stops when another attempt could not help: the judge offers no new query, or a rewritten query brings back exactly the same chunks as the attempt before.

### What You're Building

Already written for you: `embed_text`, `cosine_similarity`, `build_vector_store` (an in-memory list of `(chunk_id, chunk_text, embedding)`, so this file needs no Chroma; all 8 chunks are embedded in **one** request), `search_runbook(query, top_k) -> list[tuple[str, str, float]]`, the `JudgeVerdict` model and its `JUDGE_VERDICT_SCHEMA`, `format_history`, `build_escalation_result`, the example conversation `FOLLOW_UP_HISTORY`, and the four `SCENARIOS`.

You write:

1. `parse_judge_verdict(raw_reply) -> dict`: turns the judge's JSON reply into `{"sufficient": bool, "better_query": str | None, "parsed_ok": bool}`. The judge is asked for JSON through `response_format`, so this is normally a plain `json.loads`, but it still **validates** with `JudgeVerdict.model_validate(..., strict=True)` instead of trusting: a provider can ignore the schema and return prose, or wrap the JSON in a code fence. `parsed_ok` is `False` when the reply is not a valid verdict, so a formatting problem is never mistaken for a real "insufficient" verdict.
2. `judge_retrieval(question, retrieved_chunks, history=None) -> dict`: one chat call (`temperature=0.0`) with a **generic** prompt that names no runbook and hints at no answer, sent with `response_format={"type": "json_schema", ...}` so the reply comes back as JSON. When there is a conversation, the prompt includes it and tells the judge that the search engine cannot see it, so any rewritten query must make sense on its own. Then `parse_judge_verdict`, with a printed warning if the reply was not a valid verdict.
3. `generate_final_answer(question, retrieved_chunks, history=None) -> str`: the grounded "answer only from these excerpts" call from Problem 2, with the earlier turns passed in as prior chat messages and `temperature=0.0`. When there is a history, the system prompt also says that the earlier messages are only there to explain what the question refers to, and that every fact must still come from the excerpts.
4. `answer_with_agentic_retrieval(question, max_attempts=3, history=None) -> dict`: the loop. It returns `{"answer", "attempts", "model_calls", "outcome"}`, where `outcome` is `"answered"`, `"stopped_no_new_query"`, `"stopped_same_results"` or `"exhausted_attempts"`, and `model_calls` counts every embedding or chat call for that question.
5. `main()`: builds the store, runs all four scenarios, and prints a summary table.

### Example

**The four scenarios:**
```
clear question                         "ERR_5023 payment gateway timeout, how do I fix it?"
ambiguous question                     "the deploy is stuck, what do I do"
question the runbook cannot answer     "how do I rotate the TLS certificate on the load balancer?"
follow-up that needs the conversation  "what if that doesn't work?"
    earlier in the conversation:
      User: How do I roll back a bad deploy?
      Assistant: Run `deploy rollback --service <name> --to-version <last-good-tag>`. It reverts traffic within 90 seconds.
```

**One real run of the finished file with Gemini (yours will differ a little, since a language model is involved):**
```
scenario                                attempts  model calls  outcome
clear question                          1         3            answered
ambiguous question                      1         3            answered
question the runbook cannot answer      3         6            exhausted_attempts
follow-up that needs the conversation   2         5            answered
```
Naive RAG would use 2 model calls per question (one search embedding and one answer). The 8-chunk store is built once at the start of a run, in a single request, and is not counted in these per-question numbers.

**The follow-up, in detail (this is the rewrite in action):**
```
ATTEMPT 1: searching with the message exactly as typed: "what if that doesn't work?"
    retrieved err-5023            0.5416     <- three near-tied scores: nothing to latch onto
    retrieved deploy-rollback-2   0.5367
    retrieved deploy-rollback-1   0.5350
    judge reply: {"sufficient": false, "better_query": "what to do if deploy rollback fails or does not work"}

ATTEMPT 2: searching with the rewrite
    retrieved deploy-rollback-2   0.7846
    retrieved deploy-rollback-1   0.7476
    retrieved oncall-escalation   0.6722     <- the chunk that answers it, now in the top 3
    judge reply: {"sufficient": true, "better_query": ""}
    answer: "If a rollback fails, page the on-call engineer via PagerDuty using the #incidents
             channel. Do not attempt further changes without on-call sign-off during an
             active incident."
```
On its own, "what if that doesn't work?" ranked the on-call chunk only 4th, outside the top 3, with every score near 0.54. The judge read the conversation, saw that "that" meant the rollback, and put it into the query. That is information the search could not see, which is what a rewrite is for.

**What the runs showed, read honestly:**

- **Follow-up.** The rewrite helped, and it is the only scenario where it clearly did. The judge's rewrite wording is its own and varies: four different runs wrote four different rewrites, and all four brought the on-call chunk into the top 3.
- **A "sufficient" verdict does not guarantee a good answer.** In one real run the judge said "sufficient" with the on-call chunk in the top 3, and then the answer step replied "I couldn't find that in the runbook", at `temperature=0.0` too. The cause was the answer prompt: it said "answer ONLY from the excerpts" without saying why the earlier conversation was there, so the model could not resolve "that". One sentence in the system prompt fixed it. The judge and the answer are two separate model calls, and they can disagree.
- **Clear question.** The judge said "sufficient" on attempt 1, so the loop cost 3 calls where naive RAG costs 2. The extra call bought nothing, which is exactly the trade-off the chapter notes describe.
- **Ambiguous question.** It was not actually ambiguous for this corpus. The top-ranked chunk was `deploy-new-release`, the wrong one, but `oncall-escalation` ("If a deploy is stuck...") was also in the top 3, so the judge passed it and the answer was correct. A naive pipeline would have sent those same three chunks to the same answer prompt, so it would very likely have answered the same way for one call fewer. (That is an inference. This file does not run naive RAG.)
- **Unanswerable question.** The judge kept rewording the question and never found anything, so the loop ended with an honest "escalating to a human". In this run it used all 3 attempts and ended as `exhausted_attempts`: the last rewrite ("how to rotate TLS certificate load balancer") differed from the one before ("...certificate on load balancer") by a single word, so the exact-match check counted it as new, and the chunk sets differed too, so the "same chunks" rule did not fire. Other runs of the same question ended as `stopped_no_new_query`, after 2 attempts and 4 calls or after 3 attempts and 6, so even at `temperature=0.0` a hosted model's rewrites vary between runs.
- **The "same chunks" stop rule** did not fire in these live runs. It was tested with a scripted stand-in for the judge and the search, not against Gemini.

A rewrite helps when the missing information exists somewhere the search cannot see. When the question simply lacks the information, the rewrite can only guess words, and it drifts.

---

## 7: Graph Memory: Walking Relationships

**File:** `07_graph_memory.py`

### The Intuition

No embeddings, no vector database, no network calls anywhere in this file. A question like "who's on call for the team that owns payments-service?" has a chain inside it, and it gets answered by literally walking two edges in a dictionary of dictionaries, not by comparing anything for similarity. An edge is stored once, on the node it points *from*, so walking it forward is a lookup, and walking it *backward* ("who points at this?") means scanning every node. This file also shows the opposite problem on purpose: a graph is only as good as its entity resolution, and two different spellings of the same person silently fragment into two disconnected nodes with zero warning. Last, a memory that disappears when the program stops is not long-term memory, so the graph is saved to a JSON file and loaded back, and the answer survives a restart.

```text
payments-team ──owns──────────► payments-service
Priya ────────member_of───────► payments-team
Priya ────────on_call_for─────► payments-team
Alice ────────member_of───────► payments-team
Alice ────────reports_to──────► Priya

"who's on call for the team that owns payments-service?"
   payments-service ◄──owns── payments-team ◄──on_call_for── Priya
        (hop 1, walked backward)    (hop 2, walked backward)
```

### What You're Building

Already written for you: `add_fact`, `add_observation`, `walk_one_hop` (a one-hop walk that goes forward with `"out"` or backward with `"in"`), and `GRAPH_FILE_PATH`, which points at `from_scratch/data/graph_memory.json`. That one file is shared by `solved/`, `template/` and `solutions/`, and `from_scratch/.gitignore` ignores the `data/` folder because the script recreates it on every run.

You write:

1. `find_related(graph, entity, relation) -> list`: walks **one** edge **forward**, returning every node `entity` points to under that relation. It returns a **copy** of the stored list, so a caller who changes the result cannot corrupt the graph.
2. `find_incoming(graph, entity, relation) -> list`: walks one edge **backward**, returning every node whose `relation` edge points *at* `entity`. Nothing stores the reverse direction, so this scans every node.
3. `find_related_two_hops(graph, entity, relation1, relation2, direction1="out", direction2="out") -> list`: walks relation1 from `entity`, then relation2 from **each** resulting node, with each hop going forward or backward. The output of hop one becomes the input to hop two, and the combined result has no repeats.
4. `build_ops_assistant_graph() -> dict`: the six real facts only (a payments team that owns payments-service, its members, who is on call, who reports to whom, and an outage observation). There are **no** hand-typed reverse edges: every reverse question is answered by walking these same edges backward.
5. `run_two_hop_demo(graph)`: three two-hop questions, one forward-forward, one backward-backward (the "who's on call for the team that owns payments-service?" question) and one mixed, with each hop printed.
6. `run_entity_resolution_demo()`: a second, separate demo graph with one fact recorded under `"Priya K."` and a different fact recorded under just `"Priya"`, and a lookup starting from `"Priya"` that comes back empty even though the *same person* clearly has an on-call edge under the other spelling.
7. `save_graph(graph, file_path) -> None`: writes the graph with `json.dump`. It writes to a `.tmp` file first and then renames it over the real file, so a crash halfway through never leaves a half-written memory file behind. It also creates the `data/` folder if it is missing.
8. `load_graph(file_path) -> dict`: reads the file back with `json.load`. A missing file means nothing has been remembered yet, so it returns `{}` instead of raising an error.
9. `run_persistence_demo(graph, file_path)`: three "sessions". Session 1 saves the graph. Session 2 loads it as a brand-new dict, answers the backward-backward question from the loaded copy, learns one new fact (Bob joined payments-team) and saves again. Session 3 loads the file and finds Bob.
10. `main()`: builds the graph, shows how two nodes are stored, and runs the three demos.

### Example

**How the graph is stored.** The `owns` edge lives on `payments-team`, the node it points *from*, so `payments-service` has no outgoing edges at all:
```
payments-service (an observation, no outgoing edges):
{ "observations": ["had a 20-minute outage on 2026-08-01"], "edges": {} }

payments-team (owns the service, so the edge lives here):
{ "observations": [], "edges": { "owns": ["payments-service"] } }
```

**Forward, forward:** "who does Alice report to, and which team is that person on call for?"
```
Hop 1 -- find_related(graph, 'Alice', 'reports_to')    -> ['Priya']
Hop 2 -- find_related(graph, 'Priya', 'on_call_for')   -> ['payments-team']
One call: find_related_two_hops(graph, 'Alice', 'reports_to', 'on_call_for') -> ['payments-team']
```

**Backward, backward:** "who's on call for the team that owns payments-service?"
```
The obvious forward walk finds nothing:
         find_related(graph, 'payments-service', 'owns')  -> []
Hop 1 -- find_incoming(graph, 'payments-service', 'owns')  -> ['payments-team']
Hop 2 -- find_incoming(graph, 'payments-team', 'on_call_for') -> ['Priya']
One call: find_related_two_hops(graph, 'payments-service', 'owns', 'on_call_for',
          direction1='in', direction2='in') -> ['Priya']

Answer: Priya
```

**Forward, then backward:** "who's on call for Alice's team?"
```
Hop 1 -- find_related(graph, 'Alice', 'member_of')                 -> ['payments-team']
Hop 2 -- find_incoming(graph, 'payments-team', 'on_call_for')      -> ['Priya']
```

**Entity-resolution failure mode:**
```
Facts stored:
  'Priya K.' --on_call_for--> payments-team
  'Priya'    --handling-----> incident-482

find_related(graph, 'Priya', 'on_call_for') -> []
```

That empty list is the correct, expected output, not a bug to fix in this file. `"Priya K."` and `"Priya"` are two different dictionary keys; nothing in `add_fact`/`find_related` ever compares or merges strings, so a traversal starting from `"Priya"` genuinely has no way to know `"Priya K."` is the same person. Fixing this takes an explicit resolution step (deciding that two names are one person, then merging the nodes), not a smarter query. This file only shows the failure. Writing the merge itself is easy; deciding *which* nodes to merge is the hard part, because two different people can share a first name.

**Persistence (the memory survives a restart):**
```
Session 1 -- save_graph(graph, 'data/graph_memory.json')
  wrote 4 nodes, 578 bytes. The file on disk:
{
  "payments-team": { "observations": [], "edges": { "owns": ["payments-service"] } },
  "payments-service": { "observations": ["had a 20-minute outage on 2026-08-01"], "edges": {} },
  "Priya": { "observations": [], "edges": { "member_of": ["payments-team"], "on_call_for": ["payments-team"] } },
  "Alice": { "observations": [], "edges": { "member_of": ["payments-team"], "reports_to": ["Priya"] } }
}
Session 2 -- load_graph('data/graph_memory.json')
  loaded 4 nodes; same contents as what was saved: True
  but a brand-new dict built from the file, not the old one: (loaded_graph is graph) = False
  who's on call for the team that owns payments-service? -> ['Priya']
  a new fact comes up in this conversation: Bob joined payments-team
  saved again: 5 nodes now
Session 3 -- load_graph('data/graph_memory.json')
  find_incoming(graph, 'payments-team', 'member_of') -> ['Priya', 'Alice', 'Bob']
Missing file -> load_graph returns {}
```

The real script prints the JSON with `indent=2`, one item per line; it is squeezed onto one line per node here to save space. Because the graph is only strings, lists and dicts, `json.dump` and `json.load` give back exactly the same dict, in the same key order, so `find_incoming` returns names in the same order after a restart. Each run rebuilds session 1 from scratch and overwrites the file, so running the script twice gives the same output instead of adding Bob twice.

### Why a Dict and a JSON File, Not a Graph Database?

A dict where each node holds lists of its outgoing edges is called an **adjacency list**, and it is the standard way to store a graph, not a toy shortcut. MCP's reference memory server (`@modelcontextprotocol/server-memory`) works the same way: it keeps entities, relations and observations in memory and saves them to a `memory.jsonl` file. It has no graph database, no multi-hop tool and no fuzzy matching. It skips an entity whose name already exists, which points to exact-name matching, though its README does not spell out how its search matches. So the dict plus a JSON file in this problem is close to what that server actually does.

A real graph database such as Neo4j, FalkorDB, Memgraph or the embedded Kuzu stores the same thing, and adds four things on top. It keeps the graph on disk, so it can be bigger than memory. It keeps an index for *both* directions of every edge, so a backward walk is a lookup instead of the full scan `find_incoming` does. It has a query language (Cypher), so demo B becomes one line, `MATCH (p)-[:ON_CALL_FOR]->(t)-[:OWNS]->(s {name: 'payments-service'}) RETURN p`. And it lets many users read and write safely at once. Those matter at scale, but the Cypher line hides the very walk this problem is about, which is why the walk is written by hand here.

In production, the harder parts are around the storage, not the storage itself. An LLM has to turn messy conversation into clean `(subject, relation, object)` facts, and that extraction is where most of the cost goes, because it can take several model calls per message. Entity resolution (is "Doc" the same as "Doc Brown"?) is widely reported as the hardest problem. Facts go stale, so some systems give each edge a time window and close old facts instead of deleting them. And graph memory is usually paired with vector search instead of replacing it: the vector side finds fuzzy matches by meaning, and the graph side follows exact chains. Problem 8 builds that pairing.

---

## 8: Hybrid Semantic + Graph Memory, Plus OS-Inspired Paging

**File:** `08_hybrid_memory_architecture.py`

### The Intuition

Graph memory only knows what someone explicitly wired in. Nobody ever added an edge between "cold weather" and "deploy timeouts", so the graph has nothing to say about that pattern. Semantic memory works on meaning, so it finds the pattern in old chat, but old chat can't reliably say who is on call *right now*: chat goes stale, and nothing marks which message is the latest truth. This file runs both side by side, so each one covers what the other misses. It also includes a small, separate demo of paging, where text is moved out of the model's active context and back in.

```text
incoming message
   │
   ├─[1] SEMANTIC SEARCH ── Chroma, cosine ──► 3 similar past chat snippets  (the PATTERN)
   │                                                 │
   ├─[2] ENTITIES ◄──── names found in the message AND in those snippets
   │        │
   ├─[3] GRAPH WALK ── out from those entities, both directions, up to 2 hops
   │        └──► connected facts: what runs where, who owns it, who is on call  (the CURRENT structure)
   │
   ├─[4] ONE MODEL CALL ── snippets + graph facts ──► combined answer
   │
   └─[5] WRITE BACK ── the message ──► semantic memory
                    └─ "X is now on-call for S" ──► graph: REPLACE the old on-call edge
```

### What You're Building

Already written for you:

- The provider setup, with **two separate settings**: `CHAT_PROVIDER = "gemini"` (writes the answer) and `EMBEDDING_PROVIDER = "ollama"` (turns text into numbers, locally and free). Each has its own client, `chat_client` and `embedding_client`. The local model is `OLLAMA_EMBEDDING_MODEL` (`qwen3-embedding:0.6b` by default, or `nomic-embed-text`), and `EMBEDDING_PREFIXES` holds the prefix each model wants.
- `embed_texts` (all texts in one request), `embed_query` (a search, with the model's query prefix) and `embed_document` (a stored text, with its document prefix). If the server is not running, or the model has not been pulled, they stop with a message that says what to run.
- `reset_semantic_memory()`. It deletes the collection an earlier run left on the Chroma server, creates it fresh, and stores the 5 seed snippets with one embedding request. Without the reset, each run's write-backs stay on the server, and the next run's search finds its own old message at similarity 1.0.
- The file 7 graph helpers: `add_fact`, `add_observation`, `find_related` (returns a copy) and `find_incoming`.
- `build_ops_graph()`, which has three groups of facts:
  - **EU:** payments-service runs in eu-cluster, which uses eu-cache-layer. Priya is on call for it.
  - **US-East:** us-east-cluster also uses eu-cache-layer, and search-service runs there with Dana on call.
  - **APAC:** a billing service that connects to neither, so you can check that a walk never reaches it.
- `ENTITY_ALIASES`, `NEW_ON_CALL_PATTERN`, `context_word_count` and `run_paging_demo`.

You write:

1. `facts_touching(graph, node_name) -> list[(source, relation, target)]`. This returns **every** edge that touches a node, whatever its label and whichever way it points: the node's own outgoing edges, plus every edge pointing *at* it. In file 7 you knew the exact relation to follow. Here the question could be about anything, so you take all of them.
2. `collect_facts_near(graph, start_entities, max_hops=2) -> list[(hop, fact_text)]`. This is a **breadth-first walk**: it collects the facts touching the start entities (hop 1), then the facts touching the nodes those reached (hop 2), plus any notes on the nodes it passes. A `visited` set stops it from going back over nodes, and a `seen` set stops the same fact being listed twice.
3. `extract_entities(text, graph) -> list[str]`. This finds graph node names and aliases in text as **whole words**, so "eu" matches "the EU cluster" but not "queue", and "eu-cache-layer" is not read as "eu".
4. `record_on_call_change(graph, person, service) -> list[str]`. "Marcus is now on-call" **replaces** whoever was on call before. It removes the old edge, adds the new one, and leaves a note on the service ("on-call changed: Priya -> Marcus"). It returns who was on call before.
5. `page_out(active_context, archive, topic, turn_count)`. This really removes the oldest turns from the context list and stores them in the archive under a topic.
6. `page_in(active_context, archive, query) -> list[str]`. This finds archived entries that share a word with the query (so `"DNS"` finds the `db-connection-incident` entry) and appends them back onto the context. When nothing matches it returns `[]` and adds nothing.
7. `handle_incoming_message(message, collection, graph) -> str`. This runs the five steps shown above.
8. `main()`. It resets semantic memory, builds the graph, runs the paging demo, and sends three messages through the workflow.

**Calls per run with the defaults:** 3 Gemini chat calls (one per message), which is all that uses your Gemini quota, plus 7 local embedding requests that are free: 1 for the 5 seeds, then 2 per message. The 2 per message are the search (embedded as a query) and the write-back (embedded again as a stored document, because the local model wants a different prefix for each). With `EMBEDDING_PROVIDER = "gemini"` there are no prefixes, so the write-back reuses the search vector: 4 Gemini embedding requests plus the 3 chat calls.

**Before the first run:** open the Ollama app (`qwen3-embedding` needs Ollama 0.12.1 or newer; the app on your Mac is 0.34), pull the model once with `/usr/local/bin/ollama pull qwen3-embedding:0.6b` (639 MB), and start Chroma. Embedding vectors from different models cannot be compared (Qwen3 gives 1024 numbers per text, nomic 768, Gemini 3072), which is safe here because `reset_semantic_memory` rebuilds the collection every run.

### Example

These parts of the output are fixed by the code and come out the same with any model. The semantic hits and their similarity scores depend on the embedding model, and the answer text depends on the chat model.

**Message 1:** `"deploy to the EU cluster is timing out again, third time this month."`
```
STEP 2: extract entities from the message and from the hits
    from the message: ['eu-cluster']
    added by the hits: [...]            <- depends on which 3 snippets were retrieved

STEP 3: walk the graph from those entities (up to 2 hops, both directions)
    hop 1: eu-cluster uses eu-cache-layer
    hop 1: payments-service runs_in eu-cluster
    hop 1: payments-service (note): had a 20-minute outage on 2026-08-01
    hop 2: us-east-cluster uses eu-cache-layer
    hop 2: payments-team owns payments-service
    hop 2: Priya on_call_for payments-service
```
Starting from `eu-cluster` alone, those are the 6 lines. Priya is two hops away: eu-cluster, then payments-service, then Priya. If the US-East snippet (`mem-5`) is among the hits, `us-east-cluster` is added as a second start. That also brings in `search-service runs_in us-east-cluster` and `Dana on_call_for search-service`, the people who might feel the impact through the shared cache. Kenji and the APAC billing service never appear, because no path connects them.

**Message 2:** `"Marcus is now on-call for payments-service."`
```
STEP 5: write back
    wrote the message into semantic memory as [mem-live-7] (7 snippets now)
    on-call handoff found -> record_on_call_change(graph, 'Marcus', 'payments-service')
    removed: ['Priya'] on_call_for payments-service   added: Marcus on_call_for payments-service
    now on call for payments-service: ['Marcus']
```

**Message 3:** `"who should I page about payments-service right now?"`

Semantic memory now holds both `mem-3` ("on-call rotation moved to Priya this week") and `mem-live-7` ("Marcus is now on-call"), with nothing marking which is newer. The graph has only one current fact, and it keeps the history as a note:
```
    hop 0: payments-service (note): on-call changed: Priya -> Marcus
    hop 1: Marcus on_call_for payments-service
```
The system prompt tells the model to trust the graph when the two disagree, so the answer should be Marcus.

**Paging demo** (no model calls; these numbers are exact):
```
4 turns about the DB incident: 43 words in context
2 new turns arrive: 58 words (over the 50-word budget: True)
[page_out] moved 4 turns to the archive under topic='db-connection-incident'
after page_out: 15 words, 2 turns in context, 1 entry in the archive
...later...
[page_in] query='DNS' -> 1 archived entry put back
after page_in('DNS'): 74 words; the last turn in context is now:
  [recalled: db-connection-incident] user: payments API is throwing ... root cause was a DNS misconfiguration
[page_in] query='kubernetes' -> 0 archived entries put back
```

### What Is Real and What Is Simplified

| Part | Status |
|---|---|
| Semantic search, the graph walk, write-back to both stores | **Real.** A live Chroma collection, live embeddings, a real walk over the stored facts. |
| The on-call handoff | **Real replacement.** The old edge is removed, so the graph has exactly one current on-call person, with the change kept as a note. This is a small step toward a temporal graph, where each fact carries the dates it was true. |
| Entity extraction | **A hand-written alias table**, matched as whole words. A real system uses an LLM or a named-entity model, and that step can make mistakes. |
| Fact extraction | **One regex** for one sentence shape. A real system uses an LLM. |
| The graph walk | **Two hops, any relation, both directions,** then the model reads the facts. It is not a targeted query like file 7's two-hop walk. |
| Paging | **Real list operations, triggered by a fixed rule** in the demo. In MemGPT-style systems such as Letta, the model decides for itself by calling tools (`archival_memory_insert`, `archival_memory_search`). The archived turns are stored word for word; writing a short summary instead is the compression idea in Problem 9. |
| Semantic memory between runs | **Reset at the start of each run,** so every run starts from the same 5 snippets. |

**What gets sent to the model:** each message makes one chat call, carrying the 3 snippets and the graph facts. The graph facts are only the ones connected to the entities in the message and the hits, not the whole graph.

---

## 8a: Hybrid Memory, the Simple Version

**File:** `08_a_hybrid_memory_architecture_simple.py`

### The Intuition

This is Problem 8 cut down to the one idea it teaches: **two kinds of memory answer one message together**. Old chat (semantic memory) finds the *pattern*. The graph finds the *current facts*. One chat call reads both. Everything that is not about that idea is gone: there are no provider switches, no prefix table and no paging demo. The setup is fixed: Gemini writes the answer and a local `qwen3-embedding:0.6b` (through Ollama) turns text into numbers. The file is about 290 lines instead of 620. Theory: [Theory 08a](#theory-08a-hybrid-memory-the-simple-version).

```text
message ──► [1] Chroma: 3 similar old snippets ─────────────────────────────┐
        └─► [2] entities named in the message + snippets                     │
                 └─► [3] graph: facts within 2 hops ────────────────────────┼─► [4] ONE chat call ─► answer
                                                                             │
            [5] write back: message ──► Chroma;  "X is now on-call for S" ──► graph (replace the edge)
```

### What You're Building

Already written for you:

- The two clients. `chat_client` (Gemini, `CHAT_MODEL` from `.env`) writes the answer. `embedding_client` (Ollama, `qwen3-embedding:0.6b`) makes the vectors.
- `embed(texts)`, which sends all texts in one request and returns one vector of 1024 numbers per text. `QUERY_INSTRUCTION` is the line Qwen3 wants in front of a **search** text. Stored texts go in plain.
- `PAST_CHAT` (5 old snippets) and `reset_semantic_memory()`, which deletes the old collection, creates it again and stores the 5 snippets.
- The graph helpers from file 7: `add_fact`, `add_observation`, `find_incoming`.
- `build_ops_graph()`, which holds 8 nodes, 6 edges and 1 note:
  - payments-team owns payments-service
  - Priya is on call for payments-service
  - payments-service runs in eu-cluster
  - eu-cluster and us-east-cluster both use eu-cache-layer
  - billing-service runs in apac-cluster, which connects to nothing else
- `ENTITY_ALIASES` (5 everyday names) and `NEW_ON_CALL_PATTERN` (one regex for "Marcus is now on-call for payments-service").

You write:

1. `facts_touching(graph, node_name)`: every edge touching a node, both directions. It's the same function as file 8.
2. `collect_facts_near(graph, start_entities, max_hops=2) -> list[str]`: the breadth-first walk. It's simpler than file 8: it returns plain text lines with no hop numbers, uses one list that also catches repeats, and collects the notes of each node it expands.
3. `extract_entities(text, graph)`: node names and aliases, matched as whole words. It's the same function as file 8.
4. `record_on_call_change(graph, person, service)`: removes the old on-call edge, adds the new one, keeps a note, and returns who was on call before.
5. `handle_incoming_message(message, collection, graph)`: the five steps. Step 2 is a single `extract_entities` call on the message and the hits joined together.
6. `main()`: reset, build the graph, and send the three messages.

If you already did Problem 8, functions 1 and 3 are the same, so you can copy your own code.

**Calls per run:** 3 Gemini chat calls, plus 7 local embedding requests that are free. The 7 are 1 for the 5 snippets, then 2 per message: the search, with the instruction in front, and the stored copy, plain.

### Example

The similarity scores and the hits depend on the embedding model, and the answer depends on the chat model. The graph part is fixed by the code.

**Message 1:** `"deploy to the EU cluster is timing out again, third time this month."`

Starting from `eu-cluster` alone, the walk returns:
```
STEP 3: graph facts within 2 hops of those entities
    eu-cluster uses eu-cache-layer
    payments-service runs_in eu-cluster
    us-east-cluster uses eu-cache-layer
    payments-service (note): had a 20-minute outage on 2026-08-01
    payments-team owns payments-service
    Priya on_call_for payments-service
```
If the hits add more starts, such as `us-east-cluster` or `payments-service`, the lines may come in a different order, but the set is the same. `billing-service runs_in apac-cluster` never appears, because no path leads to it.

**Message 2:** `"Marcus is now on-call for payments-service."`
```
STEP 5: write back
    stored the message in Chroma as [mem-live-7]
    graph: on call for payments-service was ['Priya'], now ['Marcus']
```

**Message 3:** `"who should I page about payments-service right now?"`

Chroma now holds both `mem-3` ("moved to Priya") and `mem-live-7` ("Marcus is now on-call"). If `mem-3` is a hit, `Priya` even turns up as an entity, but the graph has no current edge for her. These are the lines that matter:
```
    payments-service (note): on-call changed: Priya -> Marcus
    Marcus on_call_for payments-service
```
The prompt says to trust the graph when the two disagree, so the answer should be Marcus.

### What Is Real and What Is Simplified

| Part | Status |
|---|---|
| Semantic search, graph walk, write-back to both stores | **Real.** A live Chroma collection, local embeddings, a real walk. |
| The handoff | **Real replacement,** with the history kept as a note. |
| Entity and fact extraction | **Hand-written** (5 aliases and one regex). A real system uses an LLM. |
| Semantic memory and the graph between runs | **Reset or rebuilt each run,** so every run starts the same. |

---

## 9: Memory Augmentation, Compression, and Forgetting

**File:** `09_memory_augmentation_compression_forgetting.py`

### The Intuition

A memory store that only ever grows gets noisier, not smarter. There are three different ways it goes wrong, and each one has its own fix:

```text
problem                                          fix            what happens to the store
a memory is worded nothing like the question     AUGMENTATION   + rows: questions that point back at it
many near-copies crowd the top results           COMPRESSION    - rows: one summary replaces the copies
an out-of-date memory still wins the search      FORGETTING     - rows: stale rows are deleted (unless a rule says keep)
```

Picking the wrong fix doesn't help. Summarising the stale "Priya is on-call in March" note still leaves a wrong answer in the store. Deleting the 12 deploy notes throws away true history. So all three jobs run on **one** store in this file, and each one sits between a search **before** and a search **after**, so you can see what it fixed. Theory: [Theory 09](#theory-09-keeping-a-memory-store-healthy).

### What You're Building

Already written for you:

- The two clients, the same as file 8a. Gemini writes (`chat_client`) and a local `qwen3-embedding:0.6b` embeds (`embedding_client`).
- `embed(texts)`, which embeds in one request and scales every vector to length 1, so cosine similarity is a plain dot product. `embed_query(question)` adds the Qwen3 search instruction.
- The store: a plain Python list of row dicts, with no Chroma, so you can see every row. It starts with 20 memories:
  - 12 near-identical deploy notes
  - 3 **different** incidents
  - 2 on-call notes; the March one has `valid_until`
  - 2 ownership notes; the old one has `superseded_by`
  - 1 billing record that is out of date but has `keep_until`, a retention rule
- `build_store()`, `show_search()`, `key_numbers(texts)` (what a summary must still contain), `must_keep(row, date)`, and `main()`, which runs the three before/after demos.
- The settings `NUM_CLUSTERS = 4`, `MIN_CLUSTER_SIZE = 4` and `MIN_SIMILARITY_TO_CENTRE = 0.90`.

You write:

1. `search_memories(store, query_vector, top_k=3)`. This scores every row and returns the top memories. A question row counts for the memory it `points_to`, and each memory appears once, at its best score. This is what makes augmentation work.
2. `augment_memory(store, memory_id)`. One chat call writes 3 questions. Each question is embedded (plain, because it is stored) and appended as a row with `"points_to": memory_id`.
3. `kmeans(vectors, k)`, written by hand in numpy. The centres start spread out, then two steps repeat until no label changes: give each vector its nearest centre, then move each centre to the mean of its vectors.
4. `compress_store(store)`. Cluster the original memories, and merge a cluster only if it has at least 4 rows **and** every row is at least 0.90 similar to the centre. One chat call per merged cluster writes the summary. Python then checks that the summary still contains the count and the shortest and longest duration. The summary row replaces the originals.
5. `is_stale(entry, date)`. True if `superseded_by` is set or `valid_until` has passed.
6. `forget_stale(store, date)`. Delete stale rows unless `must_keep` says no, plus any question rows pointing at a deleted memory.

**Calls per run:** 2 Gemini chat calls (the 3 questions, and the 1 summary) and 6 local embedding requests, which are free. The 6 are: the store, 3 search questions, the new questions, and the summary.

### Example

This is a real run: the local embedding model, and Gemini's own replies (the augmentation questions and the compression summary come from a real Gemini run). The **BEFORE** searches and the clusters depend only on the embedding model, so you will see the same numbers. The questions, the summary and the scores that come from them can differ a little with Gemini's wording.

**1. Augmentation.** The question says "down", but the incident note says "returned 500s". Before augmenting, an ownership note wins:
```
  BEFORE  'how long was payments down?':
    0.644  owner-2      matched: Marcus owns payments-service since August 2026
    0.629  inc-1        matched: payments-service returned 500s for 12 minutes at 3am due to a bad config push
    0.609  owner-1      matched: Priya owns payments-service
  added row inc-1-q1 -> inc-1: Why did the payments-service return 500s?
  added row inc-1-q2 -> inc-1: How long was the payments-service down?
  added row inc-1-q3 -> inc-1: When did the payments-service incident happen?
  AFTER:
    0.834  inc-1        matched: How long was the payments-service down?
    0.644  owner-2      matched: Marcus owns payments-service since August 2026
    0.609  owner-1      matched: Priya owns payments-service
```
`inc-1` now wins through one of its question rows, and the original row did not change. The store has 20 + 3 = 23 rows. Gemini's questions can differ from run to run. Augmentation only helps when one of them is closer to the search than the note itself, so a different search can show no change at all (see the gotchas in Theory 09).

**2. Compression.** Before compressing, three single deploy notes fill the top 3. Each is one fragment of the story.
```
  BEFORE  'how have deploys been going lately?':
    0.640  deploy-247   matched: deploy #247 succeeded, 3m54s, no rollback
    0.633  deploy-249   matched: deploy #249 succeeded, 5m08s, no rollback
    0.631  deploy-244   matched: deploy #244 succeeded, 3m33s, no rollback
  k-means: k=4, no label changed in round 2, so it stopped
  cluster 0: 12 rows, lowest similarity to centre 0.945: ['deploy-241', ..., 'deploy-252']
    -> merged into one summary: 12 deployments (#241 to #252) succeeded with no rollbacks, with durations ranging from the shortest of 3m12s to the longest of 5m47s.
       summary still says '12'? True
       summary still says '3m12s'? True
       summary still says '5m47s'? True
  cluster 1: 4 rows, lowest similarity to centre 0.820: ['oncall-1', 'oncall-2', 'owner-1', 'owner-2']
    -> kept as they are (too few, or not near-copies)
  cluster 2: 1 rows, lowest similarity to centre 1.000: ['audit-1']
    -> kept as they are (too few, or not near-copies)
  cluster 3: 3 rows, lowest similarity to centre 0.850: ['inc-1', 'inc-2', 'inc-3']
    -> kept as they are (too few, or not near-copies)
  AFTER:
    0.588  summary-1    matched: 12 deployments (#241 to #252) succeeded with no rollbacks, ...
    0.516  oncall-1     matched: Priya is on-call for the week of March 3rd
    0.483  inc-1        matched: How long was the payments-service down?
  store: 23 rows -> 12 rows
```
The three incidents did form a cluster, but they are different events (0.850 is below the 0.90 bar), so they are **not** merged. The clusters and their similarities come from the local model and are fixed. The summary text is Gemini's, so the three `True` checks are what tell you whether the numbers survived. After the merge the summary is the top result, but the next two rows are weak matches (0.516 and 0.483), because the top 3 always come back even when little else is relevant.

**3. Forgetting** (today is `2026-09-22`). Before forgetting, the March on-call note beats the current one:
```
  BEFORE  'who is on call right now?':
    0.656  oncall-1     matched: Priya is on-call for the week of March 3rd
    0.577  oncall-2     matched: Marcus is on-call for payments-service starting September 15th
    0.528  owner-1      matched: Priya owns payments-service
  oncall-1     stale, DELETED: valid only until 2026-03-10
  owner-1      stale, DELETED: replaced by owner-2
  audit-1      stale, but KEPT: retention until 2033-02-14
  AFTER:
    0.577  oncall-2     matched: Marcus is on-call for payments-service starting September 15th
    0.507  owner-2      matched: Marcus owns payments-service since August 2026
    0.483  inc-3        matched: billing-service lost its database connection for 6 minutes during a failover
  store: 12 rows -> 10 rows (deleted ['oncall-1', 'owner-1'])
```

The store goes from 20 to 23 rows after augmentation, then 12 after compression, then 10 after forgetting.

### What Is Real and What Is Simplified

| Part | Status |
|---|---|
| Embeddings, searches, k-means, the number check, the deletes | **Real.** Real vectors from a local model, k-means written by hand, rows really added and removed. |
| The store | **A Python list**, so every row is visible. A real system does the same adds and deletes on a vector database. |
| Choosing k and the 0.90 bar | **Picked by looking at this data.** k=3 would put two incidents in with the deploys. See Theory 09. |
| When the jobs run | **Once each, by hand.** A real system augments at write time and runs compression and forgetting on a schedule. |
| Forgetting rules | **Two date fields and one link.** Real systems also weigh how old a memory is and how often it is retrieved, and retention rules come from law, not from the code. |

---

# Theory

## Theory 01: TF-IDF, Scoring Words by How Special They Are

**Used by:** [Problem 1](#1-tf-idf-from-scratch--and-its-blind-spot), and again inside [Problem 3](#3-hybrid-search-keyword--vector-fused-by-rank)

### The Idea in One Sentence

**TF-IDF** scores how well each document matches a search word by counting how often the word appears in that document, and giving extra credit when the word is rare across all the documents. In Problem 1 you build it by hand and then watch it fail on a synonym.

### The Problem It Solves

Say you have five runbook lines and someone searches for "rollback". The simplest possible search asks only "does the word appear?", and that has two flaws:

- A long document that mentions the word once looks just as good as a short document that is entirely about it.
- A word like "the" appears everywhere, so matching it tells you nothing about which document is the right one.

TF-IDF fixes both flaws, and each of its two parts handles one of them.

### The Intuition

Picture a highlighter. You highlight the search word in each document and ask two questions:

```text
TF  (term frequency)          "How much of THIS document is about the word?"
                               -> highlighted words / total words in the doc

IDF (inverse doc frequency)   "How special is this word across ALL documents?"
                               -> rare word = big boost, word in every doc = zero

TF-IDF = TF x IDF             "talks about it a lot" AND "it's a rare, meaningful word"
```

"the" is common, so IDF crushes it to zero and it can never win. "rollback" is rare, so IDF boosts it, and any document that talks about it rises to the top.

### The Math

**Term frequency** measures how much one document is about the word:

$$\text{TF}(t, d) = \frac{\text{count of } t \text{ in } d}{\text{total words in } d}$$

Here $t$ is the term (the search word) and $d$ is one document. The top is a plain count of how many times the term appears. The bottom is the document's length. Dividing by length means a long document gets no unfair advantage: one mention in 10 words and ten mentions in 100 words both give 10%.

**Inverse document frequency** measures how rare the word is across the whole collection:

$$\text{IDF}(t) = \ln\left(\frac{N}{\text{df}(t)}\right)$$

Here $N$ is how many documents are in the collection (the **corpus**), which is 5 in Problem 1. $\text{df}(t)$ is the **document frequency**: how many documents contain $t$ at least once. It is *not* the total number of times the word appears, so a document that says "deploy" twice still counts once. And $\ln$ is the natural logarithm, which does two jobs:

- If the word is in every document, then $N / \text{df}(t) = 1$ and $\ln(1) = 0$, so the word is worth nothing, which is exactly what we want for "the".
- It softens large ratios, so a very rare word gets a real boost without dominating absurdly.

The two parts multiply into the final score:

$$\text{TF-IDF}(t, d) = \text{TF}(t, d) \times \text{IDF}(t)$$

*Note that IDF depends only on the word and the corpus, never on the document being scored. TF depends on both the word and the document.*

### Dry Run: Scoring "rollback" Across the Five Documents

The corpus, with word counts (treating "on-call" as one token):

```text
doc-1: "To deploy the service run the deploy script and monitor logs."      11 words
doc-2: "If the deploy breaks the service use rollback to the last
        stable release."                                                   13 words
doc-3: "The on-call engineer must acknowledge every alert within
        five minutes."                                                     10 words
doc-4: "Rollback is safer than a hotfix when the deploy causes an outage."  12 words
doc-5: "Contact the on-call engineer before you deploy on a Friday."        10 words
```

Score the word "rollback" in doc-2:

```text
Step 1  TF:    "rollback" appears 1 time in doc-2, which has 13 words
               TF = 1/13 = 0.0769

Step 2  df:    "rollback" is in doc-2 and doc-4  ->  df = 2, and N = 5

Step 3  IDF:   ln(5/2) = ln(2.5) = 0.9163

Step 4  Score: 0.0769 x 0.9163 = 0.0705
```

Doc-4 has 12 words, so its TF is 1/12 = 0.0833. IDF is still 0.9163, because it belongs to the word and not to any one document. So the doc-4 score is 0.0833 x 0.9163 = **0.0764**. Doc-4 edges out doc-2 only because it is one word shorter, so its single mention carries slightly more weight.

Docs 1, 3 and 5 never contain "rollback", so the count on top of TF is 0, and 0 times anything is 0.

**Why "the" scores zero.** "the" appears in all five documents, so df = 5 and IDF = ln(5/5) = ln(1) = 0. Whatever its TF is, the final score is 0.

**A query with several words adds the scores.** Take the query "rollback deploy". The word "deploy" is in docs 1, 2, 4 and 5, so df = 4 and IDF = ln(5/4) = 0.2231. Each document's total is the sum of its score for each query word:

```text
doc-4: rollback 0.0764 + deploy (1/12 x 0.2231 = 0.0186)  = 0.0950
doc-2: rollback 0.0705 + deploy (1/13 x 0.2231 = 0.0172)  = 0.0877
doc-1: rollback 0      + deploy (2/11 x 0.2231 = 0.0406)  = 0.0406
doc-5: rollback 0      + deploy (1/10 x 0.2231 = 0.0223)  = 0.0223
doc-3: no query word appears                              = 0.0000
```

Notice that doc-1 mentions "deploy" twice, yet it still ranks below docs 2 and 4. The rare word "rollback" is worth far more than the common word "deploy".

### How Search Uses It

Searching is just scoring every document and sorting:

```text
 query --> unique words --> for each doc: sum of TF-IDF per word --> sort high to low --> top_k
```

The query is turned into a **set** of unique words first, so a word repeated in the query is not counted twice. Documents that match nothing still appear in the results with a score of exactly 0.0.

### The Blind Spot

TF-IDF only matches exact words. Now search the same corpus for "revert":

```text
 query "rollback"  -->  doc-4 0.0764, doc-2 0.0705, the rest 0.0    (works well)

 query "revert"    -->  every doc 0.0000                            (total failure)
                         ^
                         a human would point at doc-2 and doc-4, but the
                         word "revert" never appears in either of them
```

"revert" is not in the corpus, so df = 0 and TF is 0 for every document. All the scores are 0. TF-IDF has no idea that "revert" and "rollback" mean nearly the same thing, because it only compares letters, never meaning. This is not a bug in your code; it is the lesson. It is also exactly the gap that embeddings (Problem 2) are built to close.

### Gotchas

- **Use a set of query words**, otherwise a repeated query word gets double credit.
- **Do not drop zero-score documents.** Return them with `0.0`.
- **Tie order comes for free.** Python's `sorted` is stable, so documents with equal scores keep their original order (doc-1, doc-3, doc-5 for the zeros).
- **Compare floats loosely.** Check `abs(score - 0.0705) < 0.0001`, never `==`.
- **IDF is per word, not per document.** The same word has the same IDF in every document.
- **The guard for df = 0 only avoids a division by zero.** The final score would be 0 anyway, since TF is 0 everywhere.
- **The tokenizer only strips `.` and `,`.** A word followed by `?` or `!` would not match. That is fine for this corpus, but it matters for real text.

### Connection Forward

Problem 2 swaps word-counting for embeddings, which fix the "revert" failure by matching meaning. TF-IDF is not thrown away, though. Problem 3 copies these same functions back in, because exact-match search still beats embeddings for things like an error code (`ERR_5023`) or a rare hostname. The two methods fail in opposite ways, which is why they are fused.

---

## Theory 02: Vector Search and Grounded Answers

**Used by:** [Problem 2](#2-a-real-vector-search-knowledge-agent), and again in Problems 3, 4, 5, 6 and 8, which all start from this retrieval step

### The Idea in One Sentence

**Vector search** turns every runbook chunk and the user's question into a list of numbers that captures meaning, finds the chunks whose numbers are closest to the question's, and then makes the chat model answer using only those chunks. In Problem 2 you build this whole loop, which is called **RAG** (retrieval-augmented generation), against a real vector database.

### The Problem It Solves

Problem 1 ended with "revert" scoring 0.0 against documents that are clearly about rolling back, because TF-IDF only compares letters and never meaning. Vector search compares meaning, so "revert last night's release" can land on the rollback chunk even though the two share no words.

There is a second problem too. A chat model on its own knows nothing about *your* runbook. If you ask it how to fix `ERR_5023`, it will happily invent a plausible answer. RAG fixes this by looking up the real text first and putting it in the prompt, so the model reads your runbook instead of guessing.

### The Intuition

An **embedding model** is a neural network that turns text into a long list of numbers (a **vector**). Texts that mean similar things get vectors that point in similar directions. Think of a map: each chunk is a pin dropped where its meaning belongs, the question gets a pin too, and you read off the nearest pins.

```text
          INGESTION (once, before any question)                  <- given in the template
 runbook chunks --> [embedding model] --> vectors --> [Chroma database]
                                                       stores (id, text, vector)

          QUESTION TIME (every question)                         <- you write this
 question --> [SAME embedding model] --> query vector
                                              |
                          Chroma: "which stored vectors are closest?"
                                              |
                                      top 3 chunks (with distances)
                                              |
                 system prompt: "answer ONLY from these chunks, cite ids"
                                              |
                                        [chat model] --> grounded answer
```

Two different models do two different jobs. The embedding model only turns text into numbers. The chat model only writes the final answer. A **vector database** (here, Chroma) stores the vectors and answers "which stored vectors are nearest to this one?" quickly. Inside Chroma, one named bucket of rows is called a **collection**, much like a table in SQL, and ours is `ops_assistant_runbook`.

### The Math

How close are two vectors? **Cosine similarity** measures the angle between them and ignores their length:

$$\cos(\theta) = \frac{A \cdot B}{\|A\|\,\|B\|}$$

Here $A$ is the query vector and $B$ is a chunk vector. $A \cdot B$ is the **dot product**: multiply the numbers in matching positions, then add them up. $\|A\|$ and $\|B\|$ are the vector lengths: square each number, add them up, take the square root. The result is 1 when the two point the same way, 0 when they are unrelated, and -1 when they are opposite.

Chroma reports **cosine distance** instead, so that smaller means closer, like any other distance:

$$\text{distance} = 1 - \cos(\theta)$$

*Lower distance is a better match. Mixing this up is the most common mistake in this problem.*

### Dry Run: Three Chunks, Two Queries

Real embeddings have hundreds or thousands of numbers with no labels. To keep the arithmetic visible, pretend there are only 3 dimensions with these made-up meanings: `[undo-a-deploy, payment-stuff, on-call-people]`.

```text
Query  Q = "revert last night's release"   = [3, 0, 1]
Chunk  D = deploy-rollback-1               = [4, 1, 1]
Chunk  E = err-5023 (payment timeout)      = [0, 5, 0]
Chunk  O = oncall-escalation               = [1, 0, 4]
```

The query against the rollback chunk D:

```text
Step 1  dot product  Q.D = 3x4 + 0x1 + 1x1 = 13
Step 2  ||Q|| = sqrt(9 + 0 + 1)  = sqrt(10) = 3.162
        ||D|| = sqrt(16 + 1 + 1) = sqrt(18) = 4.243
Step 3  cos = 13 / (3.162 x 4.243) = 13 / 13.416 = 0.969
Step 4  distance = 1 - 0.969 = 0.031          <- very close
```

The same steps for the other two chunks:

```text
E: dot = 0               -> cos = 0.000                -> distance 1.000   (unrelated)
O: dot = 3x1 + 0 + 1x4 = 7 -> cos = 7/(3.162x4.123) = 0.537 -> distance 0.463
```

Ranked by smallest distance: D 0.031, O 0.463, E 1.000. The rollback chunk wins on meaning, with no shared words, which is exactly what TF-IDF could not do.

Now a vague query, "things seem broken, what do I do?". It points a little at everything, so say V = [1, 1, 1], with length $\sqrt{3} = 1.732$:

```text
D: dot = 4+1+1 = 6 -> cos = 6/(1.732x4.243) = 0.816 -> distance 0.184
O: dot = 1+0+4 = 5 -> cos = 5/(1.732x4.123) = 0.700 -> distance 0.300
E: dot = 0+5+0 = 5 -> cos = 5/(1.732x5.000) = 0.577 -> distance 0.423
```

Side by side:

```text
                    best distance     gap between 1st and 2nd
 precise query         0.031                 0.432      <- clear winner
 vague query           0.184                 0.116      <- everything looks "sort of" close
```

A vague question gives the embedding model nothing to latch onto, so the best match is worse and the top results crowd together. That is the effect the demo makes you see with real numbers.

### What a Real Run Looks Like

These are real distances from one run with Gemini embeddings. Yours will differ a little, but the shape should match:

```text
 query "ERR_5023 payment gateway timeout fix"
     err-5023            0.1170      <- clear winner
     db-connection-pool  0.3586
     deploy-rollback-1   0.4430

 query "things seem broken, what do I do?"
     deploy-new-release  0.4286      <- nearly a three-way tie
     err-5023            0.4347
     deploy-rollback-1   0.4372
```

The precise query has a small best distance and a big gap to second place. The vague query has no clear winner, and its top hit is arguably the wrong chunk.

### Grounding: Making the Model Answer From the Chunks

Retrieval only finds paragraphs. The second half of RAG hands them to the chat model with strict instructions:

- Answer **only** from the excerpts, using no outside knowledge.
- If the excerpts do not contain the answer, say exactly `I couldn't find that in the runbook.`
- Cite the chunk id behind each claim.

Together these make the answer **strongly grounded**: every claim can be traced to a chunk. A looser prompt ("use these as a starting point") gives **weak grounding**, where the model quietly mixes in its own guesses, such as a plausible but invented timeout value. For anything with real consequences you want strong grounding. An instruction in a prompt is a request, not a guarantee, so you still check the citations against the chunks.

In the vague-query run above, the retrieval was weak and the model correctly fell back to the exact "couldn't find" sentence instead of guessing from three poor matches.

### Gotchas

- **Distance is not similarity.** Lower is better. If your printout looks backwards, check which way you compared.
- **Chroma returns lists of lists.** There is one inner list per query, so read `results["ids"][0]`, not `results["ids"]`.
- **`hnsw:space: cosine` matters.** Chroma's default metric is squared Euclidean distance, so without this setting the numbers would not be the cosine distances worked out by hand. It only applies when the collection is first created. If a collection with the same name already exists, Chroma keeps the old metric.
- **Use the same embedding model for ingesting and querying.** Different models do not share a coordinate space. `ensure_runbook_ingested()` skips when the collection already has documents, so if you ingest with Gemini and later switch `PROVIDER` to Ollama, you would compare Ollama-shaped query vectors to Gemini-shaped stored ones. Delete the collection before switching.
- **Retrieval always returns something.** With `top_k=3` you get three chunks even for a nonsense question, and nothing says "no good match". That is why the grounding prompt needs its fallback sentence, and why Problem 6 builds a judge for retrieval quality.
- **The collection name is just a label that ties files together.** Every file in this set that uses the knowledge store opens `ops_assistant_runbook`, so whichever file ingests first fills it for the others. A new name means a new, empty collection and a fresh round of embedding calls.
- **The data lives in the Docker container.** The `docker run` command has no volume, so removing the container deletes the collection.
- **Calling the synchronous Chroma client inside `async` code is fine here.** It is a deliberate simplification for a learning script.
- **The model can ignore the citation rule.** Read the cited ids against the chunks that were actually retrieved.

### Connection Forward

This design is simple and works, and it has real weaknesses: an exact code like `ERR_5023` can get blurred by embeddings, near-duplicate chunks can crowd the results, jargon can miss, and old data can go stale. Problem 3 patches the exact-token weakness by running the TF-IDF search from Problem 1 and this vector search together, then fusing the two rankings by rank.

---

## Theory 03: Hybrid Search and Reciprocal Rank Fusion

**Used by:** [Problem 3](#3-hybrid-search-keyword--vector-fused-by-rank)

### The Idea in One Sentence

**Hybrid search** runs a keyword search (TF-IDF, from Problem 1) and a vector search (from Problem 2) on the same question, then merges the two ranked lists into one using **Reciprocal Rank Fusion (RRF)**. RRF looks only at each document's *position* in each list, never at the raw scores.

### The Problem It Solves

The two searches fail in opposite ways:

| Search | Good at | Bad at |
|---|---|---|
| **Keyword (TF-IDF)** | exact tokens: `ERR_5023`, `ECONNREFUSED`, a hostname, a command name | different words for the same idea: "revert" never matches "rollback" |
| **Vector (embeddings)** | meaning and paraphrase: "revert last night's release" finds the rollback chunk | exact rare tokens: an error code can get blurred into "something about errors" |

You saw both failures already. Problem 1 ended with "revert" scoring 0.0 everywhere, and Theory 02 noted that embeddings can blur an exact code like `ERR_5023`. Running both searches gives each one a chance to catch what the other misses. That leaves one question: **how do you merge two ranked lists into one?**

### The Intuition

Picture two coworkers helping you find a runbook page. One is a stickler for exact wording: she only brings pages that literally contain your words, but she never misses one. The other is a big-picture thinker: she brings pages that are *about* your problem, even if they word it differently. Each hands you a ranked list. A page that **both** of them put near the top is very likely the right one.

```text
                 question
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
 keyword search (TF-IDF)    vector search (Chroma)
        │                        │
 ranked list of ids         ranked list of ids
 ['db-...', 'err-...']      ['db-...', 'err-...', 'deploy-...', ...]
        │                        │
        └───────────┬────────────┘
                    ▼
     Reciprocal Rank Fusion: score each id by its POSITIONS
                    │
                    ▼
     one fused list, best first
```

### Why Not Just Add the Two Scores?

The obvious idea is "add the TF-IDF score and the cosine similarity". It doesn't work, because the two numbers are on completely different scales. In the real run below, the best TF-IDF score is 0.4265, while a cosine similarity is usually somewhere around 0.6 to 0.8. A TF-IDF score has no fixed top (it grows with rare, repeated words), while a cosine similarity is capped at 1. Adding them is like adding a temperature to a price. Whichever scale happens to be larger would quietly dominate.

What **is** comparable is position. "1st in this list" means the same thing whatever the scoring method. RRF uses only that.

### The Math

For one document $d$:

$$\text{RRF}(d) = \sum_{\text{list} \,\ni\, d} \frac{1}{k + \text{rank}_{\text{list}}(d)}$$

- $d$ is one document id, like `db-connection-pool`.
- The sum runs over **each list that contains $d$**. Here there are at most two: the keyword list and the vector list.
- $\text{rank}_{\text{list}}(d)$ is $d$'s position in that list, **counting from 1**: the top result has rank 1.
- $k$ is a constant, conventionally **60**.
- If $d$ is **missing** from a list, that list adds **nothing**. Being absent is not treated as some huge rank, and it isn't a penalty. It's simply one fewer term in the sum.

#### What $k = 60$ does

$1/\text{rank}$ on its own would make rank 1 worth double rank 2. Adding 60 flattens that:

```text
rank      1/rank (k=0)      1/(60+rank) (k=60)
  1          1.000             0.0163934
  2          0.500             0.0161290
  3          0.333             0.0158730
  4          0.250             0.0156250
  5          0.200             0.0153846
 10          0.100             0.0142857
```

With $k=0$, the single top spot in one list would outweigh almost everything else. With $k=60$, neighbouring ranks are worth almost the same, so **appearing in both lists matters more than being 1st in one**:

```text
rank 5 in BOTH lists:   1/65 + 1/65 = 0.0307692
rank 1 in ONE list:     1/61        = 0.0163934      <- loses, by almost half
```

That is the behaviour you want, because two independent methods agreeing is strong evidence.

#### Fusion keeps every document; cutting to top-k is a separate step

RRF scores the **union** of the two lists: every id that appears in either one. Nothing is dropped. The fused list is simply all of them sorted by fused score. If you only want the best few, you slice the fused list afterwards (`fused[:3]`). That cut is a separate decision from the fusion itself.

### Dry Run: The Real Problem 3 Query

The question is `"database connection pool exhausted, need restart steps"`, searched over the 7-chunk runbook corpus.

#### Part 1: why the keyword list has only 2 documents

The query becomes 7 unique words. Each word's IDF (from Theory 01) depends on how many of the 7 chunks contain it:

```text
word         chunks containing it (df)    IDF = ln(7 / df)
connection   2                            ln(3.5) = 1.2528
database     1                            ln(7)   = 1.9459
pool         1                            ln(7)   = 1.9459
restart      2                            ln(3.5) = 1.2528
exhausted    0                            0   (no chunk has it)
need         0                            0
steps        0                            0
```

"exhausted" scores nothing even though `db-connection-pool` is titled "Connection Pool **Exhaustion**". TF-IDF has no **stemming** (cutting words down to a shared root), so "exhausted" and "exhaustion" are just two different strings.

Only two chunks contain any of the matching words:

```text
db-connection-pool   (30 words)
  connection 3/30 x 1.2528 = 0.1253
  database   2/30 x 1.9459 = 0.1297
  pool       2/30 x 1.9459 = 0.1297
  restart    1/30 x 1.2528 = 0.0418
                     total = 0.4265

err-5023   (25 words)
  connection 1/25 x 1.2528 = 0.0501
  restart    1/25 x 1.2528 = 0.0501
                     total = 0.1002

the other 5 chunks share no query word   total = 0.0000  -> left out of the list
```

So the keyword list is `['db-connection-pool', 'err-5023']`. `search_keyword` drops zero-score chunks on purpose, because a chunk with none of the words has no business in a keyword ranking. (`restart-pool` in the db chunk counts as one token, so it doesn't add to "restart" or "pool".)

#### Part 2: the vector list

Vector search always returns `top_k` results, here 5, ranked by meaning. From your real run:

```text
['db-connection-pool', 'err-5023', 'deploy-rollback-2', 'deploy-rollback-1', 'deploy-new-release']
```

#### Part 3: fusing

```text
db-connection-pool   keyword rank 1 -> 1/61 = 0.0163934
                     vector  rank 1 -> 1/61 = 0.0163934
                     RRF = 0.0327869

err-5023             keyword rank 2 -> 1/62 = 0.0161290
                     vector  rank 2 -> 1/62 = 0.0161290
                     RRF = 0.0322581

deploy-rollback-2    keyword: absent -> 0
                     vector  rank 3 -> 1/63 = 0.0158730
                     RRF = 0.0158730

deploy-rollback-1    keyword: absent -> 0
                     vector  rank 4 -> 1/64 = 0.0156250
                     RRF = 0.0156250

deploy-new-release   keyword: absent -> 0
                     vector  rank 5 -> 1/65 = 0.0153846
                     RRF = 0.0153846
```

Sorted, this is exactly your terminal output:

```text
doc_id              keyword rank   vector rank    fused score
db-connection-pool  1              1              0.0327869
err-5023            2              2              0.0322581
deploy-rollback-2   --             3              0.0158730
deploy-rollback-1   --             4              0.0156250
deploy-new-release  --             5              0.0153846
```

The fused list has 5 entries, the union of the two lists. The two chunks found by **both** searches score about twice as much as the three found by only one.

#### When the two lists disagree

In your run both lists agreed on the top two, so fusion only confirmed them. RRF earns its keep when the lists **disagree**. The chapter notes' example has four chunks, R12, R31, R7 and R19:

```text
KEYWORD:  1 R12    2 R31    3 R7     (R19 absent: shares no literal word)
VECTOR:   1 R19    2 R12    3 R7     4 R31

R12: 1/61 + 1/62 = 0.0325225     <- good in BOTH: wins
R31: 1/62 + 1/64 = 0.0317540
R7 : 1/63 + 1/63 = 0.0317460
R19: 0    + 1/61 = 0.0163934     <- #1 in vector alone, but last after fusion
```

R19 was the top result of the vector search, a plausible-sounding but wrong guess. With no keyword support, it falls to last. R12, which both methods liked, wins. No raw score was ever compared.

### Walking Through the Code With Real Values

#### `search_keyword(query, top_k)`

```python
query_terms = set(_tokenize(query))
# {'database', 'connection', 'pool', 'exhausted', 'need', 'restart', 'steps'}

scored_docs = []
for doc in RUNBOOK_DOCS:
    score = sum(_tfidf_score(term, doc["text"], RUNBOOK_DOCS) for term in query_terms)
    if score > 0.0:
        scored_docs.append((doc["id"], score))
# scored_docs = [('err-5023', 0.1002), ('db-connection-pool', 0.4265)]   corpus order

scored_docs.sort(key=lambda pair: pair[1], reverse=True)
# [('db-connection-pool', 0.4265), ('err-5023', 0.1002)]

return [doc_id for doc_id, _score in scored_docs[:top_k]]
# ['db-connection-pool', 'err-5023']
```

- `set(...)` removes repeated query words, so a word typed twice isn't counted twice.
- `if score > 0.0` leaves out the 5 chunks with no matching word.
- Only the ids are returned, not the scores. RRF never needs the scores.

#### `search_vector(query, top_k)`

```python
query_embedding = await embed_text(query)        # 1 embedding API call
results = runbook_collection.query(query_embeddings=[query_embedding], n_results=top_k)
return results["ids"][0]
# ['db-connection-pool', 'err-5023', 'deploy-rollback-2', 'deploy-rollback-1', 'deploy-new-release']
```

Chroma already returns ids closest-first, so there is nothing to sort. `[0]` picks the result list for the first (and only) query, as in Theory 02.

#### `reciprocal_rank_fusion(keyword_ranked_ids, vector_ranked_ids, k=60)`

```python
scores = {}

for rank, doc_id in enumerate(keyword_ranked_ids, start=1):
    scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

for rank, doc_id in enumerate(vector_ranked_ids, start=1):
    scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

fused_ranking = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
return fused_ranking
```

- `enumerate(..., start=1)` hands out `(1, first_id), (2, second_id), ...`, so ranks count from 1 as the formula needs.
- `scores.get(doc_id, 0.0)` means "the score so far, or 0 if this id hasn't been seen yet". This one line is what makes a missing list add nothing: an id that never appears in a list is never touched by that loop.

How `scores` grows, with the real lists:

```text
after the keyword loop:
  {'db-connection-pool': 0.0163934,          <- 1/61
   'err-5023':           0.0161290}          <- 1/62

after the vector loop:
  {'db-connection-pool': 0.0327869,          <- 0.0163934 + 1/61
   'err-5023':           0.0322581,          <- 0.0161290 + 1/62
   'deploy-rollback-2':  0.0158730,          <- new id: 0 + 1/63
   'deploy-rollback-1':  0.0156250,          <- new id: 0 + 1/64
   'deploy-new-release': 0.0153846}          <- new id: 0 + 1/65
```

`scores.items()` turns the dict into `(id, score)` pairs, and `sorted(..., reverse=True)` orders them by score, highest first. The return value is a list of 5 tuples, the union, best first.

#### The table printed in `main`

```python
keyword_rank = keyword_ranked.index(doc_id) + 1 if doc_id in keyword_ranked else "--"
```

`.index(...)` gives a 0-based position, so `+ 1` turns it back into a rank. An id missing from the keyword list prints `--`.

### Gotchas

- **Ranks start at 1.** `enumerate` starts at 0 unless you pass `start=1`. Starting at 0 would make the top result worth `1/60` instead of `1/61`.
- **Absent means "adds nothing", not "huge rank".** Don't invent a rank for a missing id.
- **Never add the raw scores.** A TF-IDF score and a cosine similarity are on different scales. RRF exists to avoid exactly that.
- **RRF throws away how *much* better one result was.** In the keyword list, `db-connection-pool` scored 0.4265, about four times `err-5023`'s 0.1002, yet RRF only sees "1st and 2nd". That is the price of comparing positions only.
- **Fusion returns the union.** Cutting to the top few is a separate slice afterwards.
- **The keyword list can be short.** It only holds chunks that share a word with the question, while the vector list always has `top_k` entries.
- **No stemming.** "exhausted" doesn't match "Exhaustion". Real keyword engines (like BM25 in a search server) usually reduce words to a shared root first.

### Connection Forward

Fusion decides the order using positions alone, and none of the three methods so far ever reads the question and a chunk *together*. Problem 4 adds a second pass that does: a reranker that looks at each (question, chunk) pair as one input, and can notice that a chunk about pushing a *new* release does not answer "how do we roll back".

---

## Theory 04: Reranking With a Cross-Encoder

**Used by:** [Problem 4](#4-reranking-a-second-smarter-pass)

### The Idea in One Sentence

A **reranker** takes the short list of candidates that a fast first search already found, reads the question and each candidate **together**, gives each pair a relevance score, and re-sorts the list. Problem 4 does this with a real **cross-encoder** model running locally.

### The Problem It Solves

Every search so far compares two things that were prepared **separately**. The chunk's vector was made when the chunk was stored, long before the question existed. The question's vector is made without looking at any chunk. Only then are the two vectors compared. That is fast, but it can only measure "are these two about similar topics?", not "does this chunk answer this question?".

Your real first pass for `"how do we roll back a bad deploy"` shows the problem:

```text
id                    cosine similarity
deploy-rollback-2     0.7862
deploy-rollback-1     0.7739
deploy-new-release    0.6880     <- rank 3: shares "deploy", "release" with the question,
oncall-escalation     0.6543        but it is about pushing a NEW release,
feature-flags         0.6529        the opposite of a rollback
```

### The Intuition: Bi-Encoder vs Cross-Encoder

```text
BI-ENCODER (the first pass: vector search)
  question ──► [model] ──► question vector ─┐
                                            ├──► cosine similarity ──► score
  chunk    ──► [model] ──► chunk vector ────┘
              (stored long ago, reused for every question)

CROSS-ENCODER (the second pass: reranking)
  [question + chunk together] ──► [ONE model, words of both look at each other] ──► ONE score
              (made fresh for every question, cannot be stored ahead of time)
```

Think of judging whether two people would get along. A bi-encoder looks at their two profile photos separately. A cross-encoder puts them in a room together and watches them talk.

#### What the cross-encoder actually reads

The model takes the question and one chunk glued into a single input, with separator markers. This is the real input for the question and the `deploy-new-release` chunk, 56 tokens:

```text
[CLS] how do we roll back a bad deploy [SEP] deploy run ##book : how to push a new
release . merge to main , wait for ci to pass , then run ` deploy push - - service
< name > ` . monitor error rates for 10 minutes after a push completes . [SEP]
```

(`##book` means "attached to the previous piece": "run" + "##book" is "runbook".)

Because both texts are in **one** input, attention (Theory 05, building block 3) lets "roll back" in the question look directly at "push a new release" in the chunk. The model notices they don't fit. At the end, a small final layer turns the whole input into **one number**, the relevance score. This model, `cross-encoder/ms-marco-MiniLM-L-6-v2`, is small: 6 layers, 384 numbers per token vector, about 90 MB. It was trained on **MS MARCO**, a large set of real web-search questions paired with passages people judged relevant or not.

### Why Two Stages, Not One

A cross-encoder's score depends on the question, so nothing can be computed ahead of time. It has to run once **per (question, chunk) pair**, on every question. On a corpus of 5,000 chunks that would be 5,000 model runs per question, far too slow. So real systems split the work:

```text
STAGE 1  fast first pass (vector / keyword / hybrid)    whole corpus  ──► 20-50 candidates
         job: RECALL     "don't miss anything plausible"

STAGE 2  cross-encoder reranker                         20-50 pairs   ──► best 5-10
         job: PRECISION  "of these, which actually answer the question?"
```

Problem 4 uses 5 candidates, so the reranker runs on 5 pairs.

A reranker can only **reorder** what stage 1 found. If the right chunk never made the candidate list, no reranker can bring it back. That is why stage 1 casts a wide net.

### The Math: Logits and the Sigmoid

The model outputs a **logit**: a raw score that can be any number, positive or negative. Higher means more relevant. Negative is completely normal and just means "not relevant". It is **not** a probability and **not** a cosine similarity.

To show it as a number between 0 and 1, the code passes it through the **sigmoid**:

$$\sigma(z) = \frac{1}{1 + e^{-z}}$$

- $z$ is the logit.
- $e \approx 2.718$, and $e^{-z}$ is computed with `math.exp(-z)`.
- A large positive $z$ makes $e^{-z}$ tiny, so $\sigma \to 1$. A large negative $z$ makes $e^{-z}$ huge, so $\sigma \to 0$. $z = 0$ gives exactly 0.5.

The sigmoid always goes up when $z$ goes up, so it **never changes the order**. It only makes the numbers easier to read.

#### Dry run with your real logits

```text
deploy-rollback-1    z =  5.529   e^-5.529 = 0.00397    σ = 1 / 1.00397  = 0.9960
deploy-rollback-2    z =  4.808   e^-4.808 = 0.00816    σ = 1 / 1.00816  = 0.9919
feature-flags        z =  4.278   e^-4.278 = 0.01387    σ = 1 / 1.01387  = 0.9863
oncall-escalation    z =  3.854   e^-3.854 = 0.02119    σ = 1 / 1.02119  = 0.9792
deploy-new-release   z = -8.641   e^8.641  = 5659       σ = 1 / 5660     = 0.0002
```

Notice that the sigmoid squeezes the top four into 0.98 to 0.996, so they look almost equal. Their logits (5.5 vs 3.9) show the gap more clearly. Sort and compare on the logit, and use the sigmoid only for display.

### Walking Through the Code With Real Values

#### `search_top_candidates(query, top_k)` (given): the first pass

It embeds the question, asks Chroma for the 5 closest chunks, and builds one dict per candidate, in Chroma's closest-first order:

```python
candidates = [
    {"id": "deploy-rollback-2",  "text": "Deploy Runbook: Rolling Back a Release...",  "distance": 0.2138, "similarity": 0.7862},
    {"id": "deploy-rollback-1",  "text": "Rollback procedure: if a deploy causes...",  "distance": 0.2261, "similarity": 0.7739},
    {"id": "deploy-new-release", "text": "Deploy Runbook: How to Push a New Release...", "distance": 0.3120, "similarity": 0.6880},
    {"id": "oncall-escalation",  "text": "On-Call Runbook: Paging the Deploy Owner...",  "distance": 0.3457, "similarity": 0.6543},
    {"id": "feature-flags",      "text": "Feature Flag Runbook: Toggling Flags...",      "distance": 0.3471, "similarity": 0.6529},
]
```

`similarity = 1 - distance`, as in Theory 02.

#### `rerank_with_cross_encoder(query, candidates, top_n)`: the second pass

**Step 1: build the pairs.**

```python
pairs = [(query, candidate["text"]) for candidate in candidates]
```

```text
pairs = [
  ("how do we roll back a bad deploy", "Deploy Runbook: Rolling Back a Release..."),     # rollback-2
  ("how do we roll back a bad deploy", "Rollback procedure: if a deploy causes..."),     # rollback-1
  ("how do we roll back a bad deploy", "Deploy Runbook: How to Push a New Release..."),  # new-release
  ("how do we roll back a bad deploy", "On-Call Runbook: Paging the Deploy Owner..."),   # oncall
  ("how do we roll back a bad deploy", "Feature Flag Runbook: Toggling Flags..."),       # feature-flags
]
```

There are 5 tuples, all with the same question, in **the same order as `candidates`**. Step 3 depends on that order.

**Step 2: score every pair in one call.**

```python
raw_scores = reranker.predict(pairs)
# numpy array, shape (5,): [4.808, 5.529, -8.641, 3.854, 4.278]    <- candidate order
```

`reranker` is the `CrossEncoder` loaded at the top of the file. One `predict` call scores all 5 pairs at once, as a batch, which is faster than 5 separate calls. Each score sits at the same position as its pair.

**Step 3: attach the scores to copies of the candidates.**

```python
scored_candidates = []
for candidate, raw_score in zip(candidates, raw_scores):
    logit = float(raw_score)                       # numpy float32 -> plain Python float
    relevance = 1.0 / (1.0 + math.exp(-logit))     # sigmoid, display only
    scored_candidates.append({**candidate, "rerank_score": logit, "rerank_relevance": relevance})
```

- `zip` walks the two lists side by side: candidate 1 with score 1, candidate 2 with score 2, and so on. It is only correct because both lists are in the same order.
- `float(...)` converts numpy's number type into a normal Python float, which prints and saves cleanly.
- `{**candidate, ...}` builds a **new** dict: it copies every key of the old one, then adds two keys. The caller's `candidates` list stays untouched. Writing `candidate["rerank_score"] = logit` instead would quietly change the caller's data.

One finished entry looks like:

```python
{"id": "deploy-new-release", "text": "...", "distance": 0.3120, "similarity": 0.6880,
 "rerank_score": -8.6413, "rerank_relevance": 0.0002}
```

**Step 4: sort by the logit and keep the top `top_n`.**

```python
scored_candidates.sort(key=lambda item: item["rerank_score"], reverse=True)
return scored_candidates[:top_n]
```

```text
before sort (candidate order)          after sort (highest logit first)
rollback-2       4.808                 rollback-1          5.529
rollback-1       5.529                 rollback-2          4.808
new-release     -8.641       ──►       feature-flags       4.278
oncall           3.854                 oncall-escalation   3.854
feature-flags    4.278                 deploy-new-release -8.641
```

`[:top_n]` keeps the first `top_n`. With `top_n=5` all five come back. A `top_n` bigger than the list simply returns everything, with no error.

#### `main`: comparing the two orders

```python
bi_encoder_order = [c["id"] for c in sorted(candidates, key=lambda c: c["similarity"], reverse=True)]
rerank_order     = [c["id"] for c in reranked]
bi_encoder_rank    = bi_encoder_order.index("deploy-new-release") + 1    # 3
cross_encoder_rank = rerank_order.index("deploy-new-release") + 1        # 5
```

### What the Real Run Shows

```text
rank   bi-encoder (cosine)               cross-encoder (logit)
 1     deploy-rollback-2    0.7862       deploy-rollback-1     5.5288
 2     deploy-rollback-1    0.7739       deploy-rollback-2     4.8076
 3     deploy-new-release   0.6880       feature-flags         4.2779
 4     oncall-escalation    0.6543       oncall-escalation     3.8541
 5     feature-flags        0.6529       deploy-new-release   -8.6413

'deploy-new-release' moved from rank 3 (bi-encoder) to rank 5 (cross-encoder)
```

- **`deploy-new-release` dropped to last, with a strongly negative logit (-8.64).** Reading the question and the chunk together, the model saw that pushing a new release does not answer "how do we roll back". The first pass couldn't, because to it the shared words "deploy" and "release" looked like a good match.
- **`feature-flags` rose from 5th to 3rd.** Turning a feature flag off is a real alternative to a full rollback, and the cross-encoder picked up on that connection.
- **The two rollback chunks swapped places.** Both are correct answers, so either order is fine.

The model was trained on web search, not runbooks, so this clean result was not guaranteed. On a different corpus it might demote less sharply. Judge it by the orderings, and never compare a cosine similarity with a logit directly, because they are on different scales.

### A Note on Using an LLM as the Reranker

You can also prompt a large language model to judge "is this chunk relevant to this question?". That is a legitimate technique, but it is **not** a cross-encoder. It is a big general-purpose model reached through an API, so it is slower and costs money per call. A cross-encoder is a small model trained specifically to score (question, passage) pairs, and it runs locally for free. Hosted reranking APIs and other open reranker models exist too. All of them fit the same two-stage shape.

### Where the Reranked List Goes

File 04 stops after reranking. It makes **no chat call**, and its only API call is the one question embedding in the first pass. It prints the two orders so the effect of reranking is visible on its own, with no LLM wording to hide it. In a full pipeline, the top reranked chunks would go into the "answer only from these excerpts" prompt from Problem 2:

```text
RAG = retrieve  ──►  rerank  ──►  generate
      Probs 1-3      Prob 4       Prob 2's grounded answer, Prob 6's agentic loop
```

### Gotchas

- **A logit is not a probability.** Negative is normal. Only the order matters.
- **Keep the pairs in candidate order.** `zip` matches scores to candidates by position. Re-sorting the candidates between building the pairs and zipping would attach scores to the wrong chunks, silently.
- **Copy, don't change, the candidate dicts.** `{**candidate, ...}` leaves the caller's list as it was.
- **Cast the numpy number** with `float(...)` before storing or printing it.
- **Call `predict` once with all the pairs.** It scores them as a batch.
- **It is a plain function, not `async`.** The model runs locally, so there is nothing to await.
- **Sort on the logit, show the sigmoid.** The sigmoid squeezes high scores together.
- **Cosine similarity and logits are different scales.** Compare the two orderings, never the numbers.
- **A reranker cannot find what stage 1 missed.** It only reorders the candidates it is given.
- **Extreme logits could overflow `math.exp`** (around -750 or below). This model's scores stay roughly within ±12, so it is not a concern here.

### Connection Forward

Problems 1 to 4 all improve how chunks are **ranked**. Problem 5 turns to what the chunks **are**: how a document is cut into pieces in the first place, and how a bad cut can hide a chunk's meaning from every one of these search methods.

---

## Theory 05: Smarter Chunking: Contextual Retrieval and Late Chunking

**Used by:** [Problem 5](#5-smarter-chunking-contextual-retrieval-and-late-chunking)

### The Idea in One Sentence

When a long document is cut into pieces for search, a piece can lose the meaning it depended on. **Contextual retrieval** fixes that by writing the missing context into the piece before embedding it, and **late chunking** fixes it by letting the embedding model read the whole document before the piece's vector is taken out. Problem 5 builds both and measures them honestly.

### The Problem It Solves

#### Why documents get cut into chunks

Search does not store a long document as one vector. One vector for a 40-page runbook would be a blurry average of everything in it, and a question about one small step would match it only weakly. So the document is cut into smaller pieces called **chunks**. Each chunk gets its own vector, and search compares the question against every chunk.

The simplest way to cut is **fixed-size chunking**: count words (or tokens) and cut every N of them, without reading what the text says.

#### The passage and the two chunks

Problem 5 uses one runbook passage, 39 words long:

```text
Drain traffic from the load balancer using lb-drain --host prod-3. This takes
about 90 seconds while in-flight requests finish. Once it completes, restart the
deploy service using the same command from step 2, adding the --skip-migrations
flag this time.
```

`split_into_fixed_size_word_chunks(text, 20)` cuts it every 20 words:

```text
CHUNK 1 = words 1-20
  "Drain traffic from the load balancer using lb-drain --host prod-3. This takes
   about 90 seconds while in-flight requests finish. Once"

CHUNK 2 = words 21-39 (the 19 words left over)
  "it completes, restart the deploy service using the same command from step 2,
   adding the --skip-migrations flag this time."
```

The cut lands right after "Once". Chunk 2 now starts with "it", and nothing inside chunk 2 says what "it" is. The answer, the drain, is in chunk 1.

#### Why that hurts search

A teammate asks "what happens once the load balancer drain completes?". Chunk 2 is the right answer, but its vector is built from "restart", "deploy service", "command" and "flag". The word "drain" is nowhere in it, so the question's vector and chunk 2's vector point in fairly different directions, and the right chunk can score low.

```text
question:  "...the load balancer DRAIN completes?"        about: drain
chunk 2:   "it completes, RESTART the deploy service..."   about: restart
            ^
            "it" = the drain, but chunk 2 alone cannot say so
```

### Two Fixes That Are Never Mixed

The two fixes solve the same problem in opposite ways, and they are separate techniques. The note belongs only to contextual retrieval. Reading the whole document first belongs only to late chunking.

```text
FIX A: CONTEXTUAL RETRIEVAL                 FIX B: LATE CHUNKING
"add words"                                 "add no words, read more first"

 split into chunks                           embed the WHOLE passage in one pass
      │                                           │
      ▼                                           ▼
 an LLM writes a short note                  one vector per token (64 rows)
 for each chunk                                   │
      │                                           ▼
      ▼                                      pick each chunk's rows,
 embed( note + chunk )                       then average them
```

| | Contextual retrieval | Late chunking |
|---|---|---|
| When the split happens | before embedding | after embedding |
| Extra text added | yes, a 2-3 sentence note from an LLM | none |
| How "drain" reaches chunk 2's vector | it is written into the text | it flows in from neighbouring tokens |
| Cost | one LLM call per chunk, paid once when storing | no API call, but needs a model that exposes one vector per token |
| In the file | `build_contextual_chunk`, `run_contextual_chunking_demo` | `embed_all_tokens`, `pool_span`, `run_late_chunking_demo` |

### Fix A: Contextual Retrieval

#### How the note gets written

For each chunk you make one chat call. The model gets a short description of the whole document plus that one chunk. It is told to write 2-3 sentences saying which section the chunk is from, what it covers, and what comes before and after it, without repeating the chunk. The note is put in front of the chunk, and the combination is what gets embedded:

```text
LLM input :  document summary  +  chunk 2
LLM output:  'This excerpt is from the fourth step of the "Deploy Runbook: Rolling
              Back a Release"...'                       <- start of a real note

embedded  :  note + "\n\n" + chunk 2                    <- 550 characters in a real run
instead of:  chunk 2 alone                              <- 121 characters
```

It is one call per chunk, not one call for the whole document. In this file only chunk 2 gets a note, so one run of the contextual demo makes:

```text
1 chat call         write the note for chunk 2
3 embedding calls   plain chunk 2, note + chunk 2, the question
```

In a real system with 500 chunks, that is 500 chat calls, but they happen once, when the documents are stored, not on every question. Sending a summary instead of the whole document, using a small cheap model, and caching the repeated document part of the prompt (where the provider supports it) all bring the cost down.

The note is only there to help search find the chunk. When the chunk is later handed to the LLM to answer a question, it gets the original chunk text.

#### Dry run with 2 numbers per vector

Real vectors have hundreds of numbers. Pretend there are only two, `(how much it is about the drain, how much it is about restarting)`. The numbers are invented to show the arithmetic.

```text
question q          = (1.0, 1.0)    "after the drain, what do I restart?"
plain chunk 2       = (0.2, 1.0)    nearly all about restart
note + chunk 2      = (0.9, 1.0)    the note added the drain

||q||        = sqrt(1 + 1)       = 1.414
||plain||    = sqrt(0.04 + 1)    = 1.020
||note+c2||  = sqrt(0.81 + 1)    = 1.345

plain:     q . plain   = 1x0.2 + 1x1.0 = 1.2    cos = 1.2 / (1.414 x 1.020) = 0.832
with note: q . note+c2 = 1x0.9 + 1x1.0 = 1.9    cos = 1.9 / (1.414 x 1.345) = 0.999
```

It is the same chunk text, but the version with the note scores higher because the drain is now in the text.

#### What a real run looks like

One real run with Gemini embeddings and the question "what do I do after the drain step finishes?":

```text
plain chunk        similarity = 0.6347
contextual chunk   similarity = 0.6627
```

The note helped, by a small amount, on this one question. One question is weak evidence. The chapter notes put typical measured gains for this technique at around 5 to 15 percent in retrieval precision, across many questions.

### Fix B: Late Chunking

Late chunking needs four building blocks. Each one is explained before it is used.

#### Building block 1: tokens and token IDs

An embedding model does not read whole words, and it does not read single letters. A **tokenizer** first cuts the text into small pieces from a fixed list of about 50,000 pieces (the **vocabulary**). Each piece is a **token**, and each token has an ID number in that list. Common words are one token. Rarer ones are split:

```text
"deploy"    -> deploy                 (1 token)
"balancer"  -> bal + ancer            (2 tokens)
"lb-drain"  -> lb + - + d + rain      (4 tokens)
```

The tokenizer also adds two **special markers** to every input, `[CLS]` at the start and `[SEP]` at the end. They are not text.

This model also requires a short **prefix** in front of every input, which tells it what kind of text it is reading: `search_document: ` for passages and `search_query: ` for questions. The prefix becomes 4 tokens: `search`, `_`, `document`, `:`.

So the full passage, with its prefix, becomes 64 tokens. These are the real tokens from a run:

```text
row  0      [CLS]                                     start marker
rows 1-4    search  _  document  :                    the prefix
rows 5-35   Drain traffic from the load bal ancer using lb - d rain -- host
            prod - 3 . This takes about 90 seconds while in - flight requests
            finish . Once                             CHUNK 1: 31 tokens from 20 words
rows 36-62  it completes , restart the deploy service using the same command
            from step 2 , adding the -- skip - m igr ations flag this time .
                                                      CHUNK 2: 27 tokens from 19 words
row  63     [SEP]                                     end marker

total: 1 + 4 + 31 + 27 + 1 = 64
```

Chunk 2 on its own becomes 33 tokens: its 27, plus the 4 prefix tokens, plus the 2 markers.

#### Building block 2: one vector per token, the (64, 768) table

The model turns each token into a list of 768 numbers. 768 is fixed by how this model was built (its width), and the code does not choose it. Each number is a "dial" the model learned in training. No single dial means anything a person can name, but together they describe what the token means **in this text**.

All the token vectors together form a table: one row per token, 768 columns per row. For the full passage the table has shape `(64, 768)`. Here is a real one for the tiny text `"it completes"`, which has 8 tokens, showing the first 5 of the 768 numbers in each row:

```text
row 0  [CLS]        [-2.013, -1.782, -1.529, -0.838,  2.703, ...763 more]
row 1  search       [-0.616, -1.235, -0.852,  0.614,  1.067, ...]
row 2  _            [-1.322, -1.516, -0.895, -0.004,  2.283, ...]
row 3  document     [-0.186, -2.349, -0.371,  0.500,  2.237, ...]
row 4  :            [ 0.208, -0.024,  0.239, -0.024,  0.019, ...]
row 5  Ġit          [-0.299,  0.450, -3.203, -0.521,  1.842, ...]
row 6  Ġcompletes   [ 2.135,  0.136, -0.170, -0.859,  1.828, ...]
row 7  [SEP]        [ 0.488, -0.099,  0.260,  0.084, -0.138, ...]
shape (8, 768)
```

The `Ġ` means the token begins with a space. The number of rows changes with the text (64, 33, 16 and so on). The 768 never changes.

#### Building block 3: attention, why a token's row depends on its neighbours

The model reads all the tokens of one input **at the same time**. While it builds each token's row, it lets that token look at every other token in the input and mix in some of their meaning. This is **attention**. A simplified picture of it:

$$\mathbf{h}'_{\text{it}} = \sum_{j} w_j \, \mathbf{h}_j \qquad \text{where } \sum_j w_j = 1$$

Here $\mathbf{h}_j$ is the current vector for token $j$, $w_j$ is how much attention "it" pays to token $j$ (the weights add up to 1), and $\mathbf{h}'_{\text{it}}$ is the new vector for "it". The real model repeats this through many layers with learned weights, but the effect is the same: each row ends up carrying meaning from the tokens around it.

With 2 numbers per vector, `(drain, restart)`:

```text
"drain" = (1, 0)        "it" = (0, 1)

When "drain" is in the same input, the model can work out that "it" refers to it,
so "it" pays attention: 70% to "drain", 30% to itself

new "it" = 0.7 x (1, 0) + 0.3 x (0, 1) = (0.7, 0.3)    <- now mostly about the drain

When "drain" is NOT in the input (chunk 2 alone), "it" has nothing to look at:
new "it" stays near (0, 1)                             <- no drain meaning
```

This is the whole reason late chunking works. What a token's row contains depends on which other tokens were in the same input.

#### Building block 4: pooling, many rows into one vector

Search needs **one** vector per chunk, not one per token. **Pooling** merges a group of rows into one. This model uses **mean pooling**, which averages the rows column by column:

$$\mathbf{c} = \frac{1}{n} \sum_{i \in S} \mathbf{h}_i$$

Here $S$ is the set of row numbers that belong to the chunk, $n$ is how many rows that is, $\mathbf{h}_i$ is row $i$ of the table, and $\mathbf{c}$ is the chunk's single vector. Using rows 5 and 6 from the table above (first 3 numbers only):

```text
row 5  Ġit          [-0.299,  0.450, -3.203]
row 6  Ġcompletes   [ 2.135,  0.136, -0.170]
                    -------------------------
average             [ 0.918,  0.293, -1.687]     e.g. (-0.299 + 2.135) / 2 = 0.918
```

Pooling 27 rows of 768 numbers works exactly the same way, and gives one vector of 768 numbers, shape `(768,)`.

#### Putting the blocks together: normal vs late

Normal embedding and late chunking use the same tokenizer, the same model and the same averaging. The only difference is **what text the model reads** before the averaging:

```text
NORMAL (chunk 2 alone):
  model reads  [CLS] prefix  chunk-2 tokens  [SEP]                 -> table (33, 768)
  average the 27 chunk-2 rows                                      -> vector (768,)

LATE (chunk 2 out of the whole passage):
  model reads  [CLS] prefix  chunk-1 tokens  chunk-2 tokens  [SEP] -> table (64, 768)
  average the 27 chunk-2 rows                                      -> vector (768,)
                             ^^^^^^^^^^^^^^
                             chunk 1 is read but NOT averaged in. It only
                             changes the chunk-2 rows, through attention.
```

Both vectors are averages of the same 27 words. They come out different because, in the late version, those 27 rows were computed while the model could also see "Drain traffic from the load balancer...". The averaging happens after the reading, which is why it is called **late** chunking.

### Dry Run: Late vs Alone With 2 Numbers

Same made-up dimensions, `(drain, restart)`. Chunk 2 has two important tokens, "it" and "restart".

```text
ALONE (the model saw only chunk 2):
  "it"      = (0.0, 1.0)
  "restart" = (0.0, 1.0)
  alone vector = average = (0.0, 1.0)

LATE (the model also saw "drain" in chunk 1):
  "it"      = (0.7, 0.3)       <- attention pulled in the drain
  "restart" = (0.4, 0.8)       <- a little drain meaning too
  late vector  = average = ((0.7 + 0.4) / 2, (0.3 + 0.8) / 2) = (0.55, 0.55)
```

Now two questions:

```text
Question 1: "what happens after the drain? what do I restart?"     q1 = (1, 1)
  ||q1|| = 1.414    ||alone|| = 1.000    ||late|| = sqrt(0.55² + 0.55²) = 0.778

  alone:  q1 . alone = 0 + 1.0 = 1.0       cos = 1.0 / (1.414 x 1.000) = 0.707
  late :  q1 . late  = 0.55 + 0.55 = 1.1   cos = 1.1 / (1.414 x 0.778) = 1.000
  -> late wins: the question needs the drain context, and only late has it

Question 2: "how do I restart the deploy service?"                  q2 = (0, 1)
  ||q2|| = 1.000

  alone:  q2 . alone = 1.0                 cos = 1.0  / (1.000 x 1.000) = 1.000
  late :  q2 . late  = 0.55                cos = 0.55 / (1.000 x 0.778) = 0.707
  -> alone wins: the question uses chunk 2's own words, and the drain
     meaning inside the late vector only dilutes the match
```

The real run below shows exactly this pattern, with real vectors.

### Why a Local Model, and Which One

Late chunking needs the per-token table. The embedding API used elsewhere in this chapter (Gemini or Ollama, through the `/embeddings` endpoint) returns only one already-pooled vector per text, so the rows are never visible. A model loaded locally with the `transformers` library hands back the whole table as `last_hidden_state`.

The file uses `nomic-ai/modernbert-embed-base`:

- **149 million parameters.** It is about a 600 MB download from Hugging Face the first time, then loads from the local cache. It runs locally, so the late-chunking demo makes no API call at all.
- **Reads up to 8192 tokens at once**, so a whole document (not just this short passage) fits in one pass, which late chunking needs.
- **768 numbers per vector.**
- **Trained with mean pooling.** Averaging its token rows is exactly how it normally makes one vector per text, so averaging only a chunk's rows is a fair use of it.
- **Loads with plain `transformers`**, without running any custom code from the model's repository.
- **Requires the prefixes** `search_document: ` and `search_query: `.

Its vectors live in their own space. A question must be embedded with this same model to be compared against these chunk vectors, never against the Gemini vectors from the contextual demo.

### Walking Through the Code With Real Values

#### Where chunk 2 sits: the character span

Late chunking reads the whole passage, then has to pick out only chunk 2's rows. Rows are matched to the text by **character position**, so first you need chunk 2's character positions inside the passage.

A tiny example first:

```text
index:  0123456789012345678901
text:   cats sleep. they purr.

passage.index("they purr.")   -> 12          where the piece first appears
len("they purr.")             -> 10
span = (12, 12 + 10)          -> (12, 22)    start included, end excluded
```

The real code:

```python
passage = DRAIN_RESTART_DOC["text"]            # the 39-word passage, 254 characters
chunk_2_start = passage.index(CHUNK_2_TEXT)    # 133
chunk_2_span = (chunk_2_start, chunk_2_start + len(CHUNK_2_TEXT))   # (133, 133 + 121) = (133, 254)
```

```text
character:  0 ................ 131 | 132 | 133 ................ 253 | 254
            [  chunk 1, 132 chars   ] space [  chunk 2, 121 chars    ]  end
```

`DRAIN_RESTART_DOC` is the one runbook entry with the id `deploy-drain-restart`, a dict with `"id"` and `"text"`. `str.index` raises an error if the piece is not found, unlike `str.find`, which quietly returns `-1`. Raising is what you want: a wrong span would silently average the wrong rows. It finds chunk 2 word for word because the splitter joined the words back with single spaces.

The span is only a ruler. No model has run yet.

#### `embed_all_tokens(text, prefix)`: read once, keep every row

**Job:** run the model over the text once and return two things, the table of token vectors and where each token sits in the text. Traced on the tiny text `"it completes"`:

**Stage 1, the tokenizer: text into numbered pieces.**

```python
encoded = tokenizer(prefix + text, return_tensors="pt", return_offsets_mapping=True)
```

```text
in :  "search_document: it completes"

out:  encoded = {
        input_ids      : [[50281, 8716, 64, 3306, 27, 352, 29141, 50282]]   shape (1, 8)
        attention_mask : [[1, 1, 1, 1, 1, 1, 1, 1]]                         shape (1, 8)
        offset_mapping : [[(0,0), (0,6), (6,7), (7,15), (15,16),
                           (16,19), (19,29), (0,0)]]                        shape (1, 8, 2)
      }

      50281=[CLS]  8716=search  64=_  3306=document  27=:
      352=Ġit      29141=Ġcompletes      50282=[SEP]
```

- `input_ids` are the token ID numbers, which are the model's actual input.
- `attention_mask` marks real tokens with 1. It only contains 0s when several inputs are padded to the same length, which never happens here.
- `offset_mapping` says which characters each token covers.
- `return_tensors="pt"` makes these PyTorch tensors. The leading `1` in each shape means one text was given.

**Stage 2, the model: one vector per token.**

```python
offset_mapping = encoded.pop("offset_mapping")      # take it out: the model must not receive it
with torch.no_grad():                               # reading only, skip training bookkeeping
    model_output = embedding_model(**encoded)       # = embedding_model(input_ids=..., attention_mask=...)
token_vectors = model_output.last_hidden_state[0]   # (1, 8, 768) -> (8, 768)
```

- `.pop` removes the offsets from the bundle and hands them back. They must come out, because the next line passes everything left in `encoded` to the model, and the model only accepts `input_ids` and `attention_mask`.
- `**encoded` unpacks the bundle into named arguments.
- This one call is where all the tokens are read together and attention happens.
- `last_hidden_state` is the model's final table, shape `(1, 8, 768)`: one text, 8 tokens, 768 numbers each. `[0]` drops the leading 1.

**Stage 3, the offsets: point them into your own text.**

```python
token_offsets = [
    (start - len(prefix), end - len(prefix)) for start, end in offset_mapping[0].tolist()
]
```

An **offset pair** `(start, end)` is the token's position written as a slice: the token is `string[start:end]`. The tokenizer measured these on the prefixed string, but every later step works with positions in **your** text, where 0 is your first character. So each position moves left by `len(prefix)`, which is 17 for `"search_document: "`. Written as a plain loop, the same line is:

```python
token_offsets = []
for start, end in offset_mapping[0].tolist():   # [0]: (1, 8, 2) -> (8, 2);  .tolist(): plain Python pairs
    token_offsets.append((start - 17, end - 17))
```

```text
token         before (prefixed string)    after (your text)
[CLS]         (0, 0)                      (-17, -17)   zero width: a marker
search        (0, 6)                      (-17, -11)   negative: prefix
_             (6, 7)                      (-11, -10)   negative: prefix
document      (7, 15)                     (-10, -2)    negative: prefix
:             (15, 16)                    (-2, -1)     negative: prefix
Ġit           (16, 19)                    (-1, 2)      your text (the -1 is the space before "it")
Ġcompletes    (19, 29)                    (2, 12)      your text
[SEP]         (0, 0)                      (-17, -17)   zero width: a marker
```

Only the positions change. The vectors are not touched.

**What it returns, and why both.**

```text
token_vectors   (8, 768)    WHAT each token means
token_offsets   8 pairs     WHERE each token sits        row i  <->  pair i
```

A row on its own is just 768 numbers, and nothing in it says which part of the text it came from. The offsets are the labels that let the next function turn "chunk 2 is characters 133 to 254" into "chunk 2 is rows 36 to 62". That is why the function returns both.

For the full passage the same function prints:

```text
[tokens] 64 tokens (prefix and 2 special markers included)
[tokens] token_vectors shape: (64, 768)
```

#### `pool_span(token_vectors, token_offsets, char_span)`: pick the rows, then average

**Job 1: pick the rows inside the span.**

```python
span_start, span_end = char_span
token_indexes_in_span = [
    token_index
    for token_index, (token_start, token_end) in enumerate(token_offsets)
    if token_end > token_start
    and span_start <= (token_start + token_end) / 2 < span_end
]
```

Each token is tested twice:

1. `token_end > token_start`: does the token have any width? The markers are `(-17, -17)`, which is zero width, so they are dropped.
2. Is its **midpoint** inside the span? The midpoint is $m_i = (s_i + e_i) / 2$, where $s_i$ and $e_i$ are the token's start and end. The token is kept when $a \le m_i < b$ for the span $(a, b)$. Prefix tokens have negative midpoints, so they are dropped too.

Why the midpoint and not the start? Look at the real boundary between the chunks:

```text
token 35   ' Once'   offsets (127, 132)   midpoint 129.5   -> chunk 1 (below 133)
token 36   ' it'     offsets (132, 135)   midpoint 133.5   -> chunk 2 (133 or more)
```

` it` starts at 132 because the space before it is part of the token. A test on the start would put 132 below chunk 2's start (133), and it would also fail chunk 1's end (132 is not below 132), so "it" would belong to neither chunk. And "it" is the most important word in chunk 2.

The result is a plain list of row numbers. For chunk 2 in the full passage:

```python
token_indexes_in_span = [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
                         50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62]   # 27 rows
```

For chunk 1's span `(0, 132)` the same code would give rows 5 to 35, which is 31 rows.

**Job 2: average those rows.**

```python
chunk_vector = token_vectors[token_indexes_in_span].mean(dim=0)
return chunk_vector.tolist()
```

```text
token_vectors          token_indexes_in_span       selected rows      .mean(dim=0)
(64, 768)        +     [36, 37, ... 62]       ->   (27, 768)    ->    (768,)
the whole table        which rows to keep          chunk 2 only       one vector
```

Putting a list of numbers inside the square brackets picks those rows, in that order. `.mean(dim=0)` averages down the rows, column by column. `.tolist()` turns the result into an ordinary list of 768 Python floats.

```text
64 rows          span (133, 254)                        27 rows            1 vector
[CLS]        x   zero width
search .. :  x   negative midpoints (prefix)
Drain..Once  x   chunk 1, midpoints below 133
it .. "."    ✓   chunk 2  ──────────────────────────►   average  ───────►  [768 numbers]
[SEP]        x   zero width
```

#### `embed_text_locally(text, prefix)`: ordinary embedding from the same pieces

```python
token_vectors, token_offsets = embed_all_tokens(text, prefix)
return pool_span(token_vectors, token_offsets, (0, len(text)))
```

The span `(0, len(text))` means "the whole text", so this averages every real token. That is ordinary embedding: one text in, one vector out. For `"it completes"` it keeps rows 5 and 6 and returns their average.

It shows that ordinary embedding and late chunking are the same two functions with different inputs:

```text
               text the model reads        span that gets pooled
ORDINARY       chunk 2 only                the whole text     (0, 121)
LATE           the whole passage           chunk 2's span     (133, 254)
```

The demo uses it twice: for chunk 2 alone (with `DOCUMENT_PREFIX`), and for every question (with `QUERY_PREFIX`). The `prefix` argument exists because those two need different prefixes.

#### `run_late_chunking_demo()`: the whole flow

```text
run_late_chunking_demo
 ├─ setup   chunk_2_span = (133, 254)                           the ruler, no model yet
 ├─ STEP 1  embed_all_tokens(passage, DOCUMENT_PREFIX)         model run 1     table (64, 768)
 ├─ STEP 2  pool_span(..., chunk_2_span)                       27 rows -> late vector
 ├─ STEP 3  embed_text_locally(CHUNK_2_TEXT, DOCUMENT_PREFIX)
 │            ├─ embed_all_tokens                               model run 2     table (33, 768)
 │            └─ pool_span(..., (0, 121))                       27 rows -> alone vector
 │          cosine_similarity(late, alone)                      0.7233
 └─ STEP 4  for each of the 5 questions:
              ├─ embed_text_locally(question, QUERY_PREFIX)     model runs 3 to 7
              ├─ cosine_similarity(question, alone)
              └─ cosine_similarity(question, late)              print both and the difference
            print the win count and the mean difference
```

What each variable holds when the function finishes:

| Variable | Holds | Shape or size |
|---|---|---|
| `passage` | the 39-word passage | 254 characters |
| `chunk_2_span` | where chunk 2 sits in it | `(133, 254)` |
| `token_vectors` | one row per token of the whole passage | `(64, 768)` |
| `token_offsets` | one `(start, end)` per token | 64 pairs |
| `late_chunk_2_vector` | average of rows 36 to 62 of the whole-passage table | 768 floats |
| `alone_chunk_2_vector` | average of chunk 2's 27 rows when chunk 2 is read alone | 768 floats |
| `vectors_agreement` | cosine between the late and alone vectors | `0.7233` |
| `query_vector` | the current question, embedded the ordinary way | 768 floats |
| `differences` | `late - alone` for each question | 5 floats |
| `late_wins` | how many questions late scored higher on | `2` |

The late and alone vectors are built once and reused for all 5 questions. Only the question vector changes on each pass of the loop. In total the model runs 7 times, all locally.

Two small Python details in the loop:

- `late_wins += late_similarity > alone_similarity` works because `True` counts as 1 and `False` as 0.
- The mean difference is `sum(differences) / len(differences)`.

### What the Real Run Shows

```text
late vs. alone vector for the SAME words: cosine = 0.7233
```

This line is a check, not a verdict. Both vectors average the same 27 words, yet they agree only at 0.7233, not 1.0. That proves reading chunk 1 really changed chunk 2's rows. It does not say which vector is better. The questions decide that:

```text
question                                                        alone    late     late - alone
what do I do after the drain step finishes?                     0.4056   0.4023   -0.0033   tie
what happens once the load balancer drain completes?            0.3346   0.5754   +0.2407   late wins
what should I do when the lb-drain command is done?             0.3851   0.5720   +0.1869   late wins
how do I restart the deploy service after the drain finishes?   0.6357   0.6137   -0.0220   alone wins
which flag do I add when restarting the deploy service ...?     0.6381   0.5743   -0.0638   alone wins

late chunking scored higher on 2 of 5 questions;  mean (late - alone) = +0.0677
```

The pattern matches the dry run:

- **Questions that name only the missing context** (the drain, the lb-drain command) gain a lot. The late vector carries the drain meaning in from chunk 1, and the alone vector has none.
- **Questions that use chunk 2's own words** ("restart the deploy service", "flag") already match the alone vector well, and the drain meaning mixed into the late vector dilutes that slightly.
- The first question is a tie.

The positive mean comes from two big wins outweighing three small losses. The honest summary is that late chunking helps most when the question depends on context the chunk alone is missing, and it is not a guaranteed win on every question. One question tells you very little. The trend across several questions is what matters.

These scores (around 0.3 to 0.6) also cannot be compared with the Gemini scores from the contextual demo, because each model has its own scale.

### What a Real System Does With This

The demo only compares. A real pipeline uses the same pieces to store and to search:

```text
STORING (once per document)
  document ──► embed_all_tokens(whole document)            one pass, the full table
           ──► pool_span for EVERY chunk's span            chunk 1, chunk 2, ... all of them
           ──► store each chunk vector + its original text in the vector database

SEARCHING (every question)
  question ──► embed_text_locally(question, QUERY_PREFIX)  the SAME model
           ──► cosine against the stored chunk vectors
           ──► top few chunks ──► their ORIGINAL text goes to the LLM
```

The late vector is only used to **find** the chunk. The LLM still reads chunk 2's plain text, unchanged. The same is true of the note in contextual retrieval.

### Gotchas

- **The two fixes are separate.** The note belongs only to contextual retrieval, and reading the whole document first belongs only to late chunking. Mixing them up is the most common confusion.
- **Contextual retrieval costs one LLM call per chunk**, paid once when storing, not on every question. In this file that is 1 chat call and 3 embedding calls per run. The late-chunking half makes no API call.
- **Don't show the note to the answering LLM.** It is a search aid, not part of the runbook.
- **Late chunking needs per-token vectors.** Most embedding APIs return only one pooled vector per text, so the table is never visible. That is why the file loads a model locally.
- **The whole document must fit in the model's window.** This model reads up to 8192 tokens. A longer document has to be split into large sections first, and each section late-chunked on its own.
- **Use the right prefix.** Passages get `search_document: ` and questions get `search_query: `. Leaving them off quietly lowers quality.
- **Never compare vectors from different models.** The local model's vectors and Gemini's vectors live in different spaces, so you can't compare them directly or by the size of their scores.
- **Offsets measure characters, not tokens.** They are shifted left by the prefix length, so 0 means the first character of your text. Prefix tokens land at negative positions, and the markers have zero width.
- **Test the midpoint, not the start.** This tokenizer attaches the leading space to a token, so a start test drops the first word of a chunk. Here, that would be the crucial "it".
- **Pop the offsets before calling the model.** The model only accepts `input_ids` and `attention_mask`.
- **Use `str.index`, not `str.find`.** A missing piece should raise an error, not return `-1` and silently produce a wrong span.
- **Late chunking is not always a win.** In the real run it won 2 of 5 questions. Judge it across several questions, never by one number.

### Connection Forward

Problems 1 to 4 improved how search ranks chunks. Problem 5 improves what goes into the index, so the right chunk has a better vector to be found by. Problem 6 adds a different safety net: instead of trusting whatever comes back, the agent judges whether the retrieved chunks are good enough, and searches again with a better question when they are not.

---

## Theory 06: Agentic RAG, Judging the Retrieval Before Answering

**Used by:** [Problem 6](#6-agentic-rag-judge-the-retrieval-then-retry)

### The Idea in One Sentence

**Agentic RAG** adds a checkpoint between searching and answering: a **judge** reads what the search found and says whether it is enough to answer the question. If not, the system searches again with a better query, and if that can't help, it says so instead of guessing.

### The Problem It Solves

Every search so far (keyword, vector, hybrid, reranked) always returns *something*. Ask a nonsense question and you still get your top 3. Naive RAG then answers from whatever came back, in the same confident tone whether the chunks were perfect or irrelevant:

```text
NAIVE RAG:   question ──► search once ──► answer from whatever came back
                                           ^
                                           no step ever asks "was that a good search?"
```

The chapter notes name two research patterns for fixing this, **Self-RAG** and **Corrective RAG (CRAG)**. Both mean the same thing in practice: don't trust a retrieval just because it returned something. Check it.

There is a second problem that only shows up in chat. A follow-up message like "what if that doesn't work?" is meaningless to a search engine, because **"that" is defined by an earlier message the search never sees**. Searched as typed, it returns near-random chunks.

### The Intuition

Think of a research assistant answering from a filing cabinet. A naive assistant grabs the first three folders and starts writing. A careful one glances at the folders first and asks "do these actually contain the answer?". If not, they try a different search term, one that uses what they remember from the conversation so far. And if the searches keep turning up nothing, they come back and say "it isn't in the cabinet", rather than inventing something.

```text
question  ──►  search with current_query  ──►  JUDGE (one LLM call): is this enough?
(+ earlier           ▲                                     │
 conversation)       │                     ┌───────────────┴───────────────┐
                     │                    yes                              no
                     │                     │                               │
                     │          answer from these chunks        did the judge give a NEW query?
                     │                                          ┌──────────┴──────────┐
                     │                                         yes                    no
                     │                                          │                     │
                     │                          same chunks as last attempt?     stop: "couldn't find it,
                     │                              ┌───────────┴───────────┐     escalating to a human"
                     │                             no                      yes
                     └────── search again ◄─────────┘                       │
                              (at most max_attempts)                stop: no new evidence
```

The notes describe three abilities an agentic retriever can have:

| Ability | What it means | In Problem 6? |
|---|---|---|
| **Decide whether to search at all** | skip the search for questions that need no runbook ("what is 15% of 20?") | no, it always searches |
| **Rewrite or split the question** | turn one vague or double question into sharper searches | rewrite only: the judge proposes one new query, using the conversation |
| **Judge the result** | check the retrieved text before answering | yes, this is the core of the file |

#### Three rules that keep the loop honest

1. **Only the search uses the rewritten query.** The judge and the final answer always see the user's *original* question, plus the conversation it came from. Otherwise a rewrite could quietly change what is being asked.
2. **A rewrite adds information that exists somewhere, never information that doesn't.** The earlier conversation counts: it holds what "that" means. But if the missing detail was never said by anyone, a rewrite can only guess extra words, and the guesses drift.
3. **Stop when another attempt could not help.** If the judge gives no new query, or a rewritten query returns exactly the same chunks as the attempt before, the search has produced no new evidence. Repeating it and calling it "progress" would be fake effort.

### The Order of Events: A Common Misreading

A natural first guess is that the system writes an answer and the judge then marks it. It does not. The judge reads **evidence**, not an answer, and the answer is written once, at the very end.

```text
THE COMMON GUESS                          WHAT THE CODE DOES

question                                  question
   ▼                                         ▼
search ──► ANSWER written                 search ──► 3 chunks
   ▼                                         ▼
judge reads the answer                    judge reads: question + 3 chunks (+ the conversation)
   ▼                                         ▼
good? ── no ──► ask judge to rewrite      ONE reply: {"sufficient": ..., "better_query": ...}
   ▼ yes                                     │
 done                                        ├─ sufficient ──► NOW write the answer (once) ──► done
                                             │
                                             └─ not sufficient ──► search again with better_query
```

Two corrections to the guess:

1. **The judge checks the evidence, not the answer.** It decides "is there enough in these chunks to answer?". Only when the answer to that is yes does the code make the answer call.
2. **There is no separate "now fix it" request.** The judge's single reply carries both things: the verdict (`sufficient`) and, when it says no, the new query (`better_query`). The loop simply uses the query it was handed.

Why check before answering:

- **It saves calls.** A failed attempt costs 2 calls (a search and a judge). If an answer were written first, every failed attempt would cost 3, and the answer would be thrown away.
- **It avoids a confident wrong answer.** Nothing is written until the evidence has passed a check.
- **Grading a finished answer is a different pattern.** That is the self-critique idea from Chapter 5, where a model grades its own work. It is less trustworthy, because the same kind of model that wrote the answer is marking it.

In the follow-up example below, the five model calls go in this order: embedding, judge, embedding, judge, answer. Only the last one writes an answer.

### What Is Real and What Is Simplified

| Part | Status |
|---|---|
| Embeddings, cosine scores, the judge call, the final answer call | **Real.** They are live Gemini calls, and the whole file has been run end to end. |
| The judge's reply | **Real, structured, and validated.** It comes back as JSON and is checked, never trusted. |
| Stop rules, attempt counting, call counting | **Real.** None of the outcomes is scripted. |
| The vector store | **Simplified.** It is a Python list in memory, not a vector database. |
| Search method | **Simplified.** Vector search only, with none of the keyword fusion or reranking from Problems 3 and 4. |
| "Agentic" | **Partly.** The control flow is a fixed loop. It always searches, and it never decides to skip a search or split a question. The model only judges and proposes a query. |
| The judge | **A model checking evidence.** It can be wrong, and it is not an independent check. |
| The conversation | **A hard-coded example** (`FOLLOW_UP_HISTORY`), not a live chat. |
| "Naive RAG would answer the same" | **An inference.** The file does not run naive RAG. |

### The Math: What It Costs

There is no new formula here. The cost is just a count of model calls. Each attempt makes one embedding call (to search) and one chat call (the judge), and a successful answer adds one more chat call:

$$\text{calls}_{\text{naive}} = 2 \qquad \text{calls}_{\text{agentic, answered on attempt } a} = 2a + 1 \qquad \text{calls}_{\text{agentic, gave up after } a \text{ attempts}} = 2a$$

When the loop stops because a rewrite returned the same chunks, the judge call for that attempt is skipped, so that case costs $2a - 1$.

```text
                                          calls
naive RAG (1 search + 1 answer)             2
agentic, answered on attempt 1              3      <- 1.5x naive
agentic, answered on attempt 2              5      <- 2.5x naive
agentic, answered on attempt 3              7      <- 3.5x naive
agentic, gave up after 2 attempts           4      <- no answer produced
agentic, gave up after 3 attempts           6      <- no answer produced
agentic, stopped on "same chunks" at 2      3      <- the judge call of attempt 2 is skipped
plus, once per run:  build_vector_store = 1 embedding request (all 8 chunks in one call)
```

The notes' rule of thumb follows: spend the extra calls in proportion to how costly a wrong answer would be. For "where's the on-call schedule?" the loop is pure overhead. For "which service do I restart at 2 a.m.?" it is cheap insurance.

### How History Works: What Goes In and Comes Out of Each Step

The model remembers nothing between calls. Every call is a blank page. "History" is just a list of earlier messages that **our code pastes into** the calls that need it. Here is the follow-up scenario, one step at a time.

**What the code holds at the start:**

```python
history  = [ {"role": "user",      "content": "How do I roll back a bad deploy?"},
             {"role": "assistant", "content": "Run `deploy rollback --service <name> --to-version <last-good-tag>`. It reverts traffic within 90 seconds."} ]
question = "what if that doesn't work?"
```

**Step 1: search (the embedding model)**

```text
IN : only the string "what if that doesn't work?"          <- NO history here
OUT: a vector of 3072 numbers, compared with every stored chunk:
       err-5023 0.5416,  deploy-rollback-2 0.5367,  deploy-rollback-1 0.5350
```

The search only turns one string into numbers. It cannot know what "that" means, so every score sits near 0.54, which is close to random.

**Step 2: the judge (a chat model)**

```text
IN : ONE message, built by judge_retrieval, containing:
       Conversation so far:
       User: How do I roll back a bad deploy?
       Assistant: Run `deploy rollback ...`. It reverts traffic within 90 seconds.

       Latest question: what if that doesn't work?

       Retrieved runbook context:
       <the err-5023 chunk>  <the rollback-2 chunk>  <the rollback-1 chunk>

       Decide whether this context contains what is needed... Be strict...
       Reply with a JSON object with two fields: sufficient, better_query
       (the query must make sense on its own, including anything the conversation says...)
     + response_format = the JSON schema
OUT: {"sufficient": false, "better_query": "what to do if deploy rollback fails or does not work"}
```

The judge could write "rollback" into the query only because the conversation was pasted into its prompt. This is where the history gets used.

**Step 3: search again**

```text
IN : only the rewrite "what to do if deploy rollback fails or does not work"
OUT: deploy-rollback-2 0.7846,  deploy-rollback-1 0.7476,  oncall-escalation 0.6722   <- the answer chunk is back
```

The rewrite is the way history reaches the search. It is the question rewritten so that it needs no history.

**Step 4: the judge again.** The same layout, now with the new chunks. It returns `{"sufficient": true, "better_query": ""}`.

**Step 5: the final answer (a chat model)**

```text
IN : [ system   : "Answer ONLY using the runbook excerpts below..." + a note about the history + the 3 chunks,
       user     : "How do I roll back a bad deploy?"           <- history turn
       assistant: "Run `deploy rollback ...`"                   <- history turn
       user     : "what if that doesn't work?" ]                <- the ORIGINAL question, not the rewrite
OUT: "If a rollback fails, page the on-call engineer via PagerDuty using the #incidents channel.
      Do not attempt further changes without on-call sign-off during an active incident."
```

**Who sees what:**

| Step | The question it receives | Sees the history? |
|---|---|---|
| search | the query string only: first the original, then the rewrite | no |
| judge | the original question | yes, pasted into the prompt as text |
| final answer | the original question | yes, as earlier chat turns |

The judge gets the history as text inside one instruction message, because its job is a task about the conversation. The answer step gets it as normal chat turns, the way any chat model expects. Either works. The final answer gets the original question and not the rewrite, so the reply answers what the user actually asked.

The history list does not fill itself. In a real chat app, the caller adds both sides of every exchange to it after each reply. That loop is not in the file, but it would look like this:

```python
history = []
for message in incoming_messages:
    result = await answer_with_agentic_retrieval(message, history=history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": result["answer"]})
```

With no history (`history=None`, as in the first three scenarios), the conversation block, the "Latest question" label and the history note are simply left out. Everything else is the same.

### Dry Run: Four Real Scenarios

These are values from one run of the finished file, with all four scenarios and the judge replying in JSON. Scores are cosine similarity, as in Theory 02. The store was built once at the start, in one request, and is not counted in the per-question calls.

#### 1. A clear question

```text
question      = "ERR_5023 payment gateway timeout, how do I fix it?"

ATTEMPT 1
  search_runbook(...) -> [ ("err-5023",            0.8871),
                           ("db-connection-pool",  0.6373),
                           ("deploy-drain-restart",0.5536) ]
  judge reply   : {"sufficient": true, "better_query": ""}
  parsed        : {"sufficient": True, "better_query": None, "parsed_ok": True}
  answer        : "Fix: restart the retry worker with `restart-worker --name payment-retry`."

return {"attempts": 1, "model_calls": 3, "outcome": "answered"}      (1 embed + 1 judge + 1 answer)
```

The top score is 0.8871, far above the rest. The loop needed 3 calls where naive RAG needs 2, so the judge call was pure overhead here.

#### 2. An "ambiguous" question

```text
question = "the deploy is stuck, what do I do"

ATTEMPT 1
  search_runbook(...) -> [ ("deploy-new-release",   0.6509),    <- top-1: a guide for pushing a NEW release
                           ("oncall-escalation",    0.6454),    <- the chunk that says "if a deploy is stuck..."
                           ("deploy-drain-restart", 0.6405) ]
  judge reply   : {"sufficient": true, "better_query": ""}
  answer        : "Page the on-call engineer via PagerDuty using the #incidents channel. ..."

return {"attempts": 1, "model_calls": 3, "outcome": "answered"}
```

The three scores are within 0.01 of each other, so the search had no clear winner, and its top-1 was the wrong kind of chunk. But the right chunk was inside the top 3. The judge saw it, passed, and the answer was correct. A naive pipeline would have sent those same three chunks to the same answer prompt, so it would very likely have answered the same way for one call fewer. (That is an inference. The file does not run naive RAG.)

#### 3. A question the runbook cannot answer

```text
question = "how do I rotate the TLS certificate on the load balancer?"

ATTEMPT 1   query = the question
  retrieved: deploy-drain-restart 0.6631, deploy-new-release 0.5926, deploy-rollback-1 0.5821
  judge: {"sufficient": false, "better_query": "load balancer TLS certificate rotation runbook"}

ATTEMPT 2   query = "load balancer TLS certificate rotation runbook"
  retrieved: deploy-drain-restart 0.6572, deploy-rollback-2 0.6542, deploy-new-release 0.6406
  judge: {"sufficient": false, "better_query": "how to rotate TLS certificate on load balancer"}

ATTEMPT 3   query = "how to rotate TLS certificate on load balancer"
  retrieved: deploy-drain-restart 0.6533, deploy-rollback-1 0.5903, deploy-new-release 0.5875
  judge: {"sufficient": false, "better_query": "how to rotate TLS certificate load balancer"}
  -> attempts used up

return {"attempts": 3, "model_calls": 6, "outcome": "exhausted_attempts"}
```

The runbook has nothing about TLS certificates. The judge was right to say no every time, and its rewrites only reworded the same question, pulling in whichever deploy chunks happened to share words with it. The loop ended with an honest "escalating to a human" instead of an answer made up from the drain chunk.

Why it used all three attempts: the last rewrite differs from the one before it by a single word ("on"), so the exact-match check counted it as a new query. And the three chunk sets were all different (`deploy-rollback-1` in attempts 1 and 3, `deploy-rollback-2` in attempt 2), so the "same chunks" rule did not fire either. Other runs of this same question ended as `stopped_no_new_query`, after 2 attempts and 4 calls or after 3 attempts and 6, so even at `temperature=0.0` a hosted model's rewrites vary from run to run.

#### 4. A follow-up that needs the conversation (the rewrite in action)

```text
earlier in the conversation:
  User:      How do I roll back a bad deploy?
  Assistant: Run `deploy rollback --service <name> --to-version <last-good-tag>`.
             It reverts traffic within 90 seconds.
question = "what if that doesn't work?"

ATTEMPT 1   query = "what if that doesn't work?"        <- searched exactly as typed
  retrieved: err-5023 0.5416, deploy-rollback-2 0.5367, deploy-rollback-1 0.5350
  judge reply: {"sufficient": false, "better_query": "what to do if deploy rollback fails or does not work"}
  -> new query, new chunk set: reformulate

ATTEMPT 2   query = "what to do if deploy rollback fails or does not work"
  retrieved: deploy-rollback-2 0.7846, deploy-rollback-1 0.7476, oncall-escalation 0.6722
  judge reply: {"sufficient": true, "better_query": ""}
  answer: "If a rollback fails, page the on-call engineer via PagerDuty using the #incidents
           channel. Do not attempt further changes without on-call sign-off during an
           active incident."

return {"attempts": 2, "model_calls": 5, "outcome": "answered"}      (2 embeds + 2 judges + 1 answer)
```

This is the case the loop exists for. Searched alone, "what if that doesn't work?" matches nothing: all three scores sit near 0.54, and the chunk that answers it (`oncall-escalation`) ranked 4th, outside the top 3. The judge read the conversation, understood that "that" meant the rollback, and wrote it into the query. The search then found the on-call chunk (0.6722), and the answer is correct and grounded. The 5 calls compare with naive RAG's 2, but naive RAG would have answered from the three near-random chunks of attempt 1. The judge's wording varies from run to run: four different runs wrote four different rewrites, and all four brought the on-call chunk into the top 3.

#### Putting the four together

```text
scenario                                attempts  model calls  outcome                naive calls
clear question                          1         3            answered               2
ambiguous question                      1         3            answered               2
question the runbook cannot answer      3         6            exhausted_attempts     2
follow-up that needs the conversation   2         5            answered               2
```

Only the follow-up shows the rewrite paying off. In the other three, the loop cost more calls than naive RAG for no better outcome, apart from the honest "I don't know" in the unanswerable case. With an 8-chunk corpus, the right chunk is nearly always in the top 3. The loop earns its cost when the question lacks something the search needs, and a rewrite can supply it from somewhere the search cannot look.

#### A contrast: when nothing is hidden, a rewrite drifts

As an experiment (not part of the file), the "stuck deploy" question was run with the search limited to a single result. Its top-1 was the wrong chunk (`deploy-new-release`), so the judge said no and rewrote the question. Three attempts went like this:

```text
attempt 1  'the deploy is stuck, what do I do'                  -> deploy-new-release  0.6509
attempt 2  'how to troubleshoot stuck deployment runbook'       -> deploy-rollback-2   0.7001
attempt 3  'deploy stuck troubleshooting runbook'               -> deploy-rollback-2   0.7238
```

The scores rose, but the search never reached `oncall-escalation`. The question contained no missing detail for the rewrite to add. The model could only guess words like "troubleshoot", "runbook" and "guide", and none of them appear in the chunk that answers it. Compare this with scenario 4, where the missing detail ("that" means the rollback) really existed in the conversation.

### Walking Through the Code With Real Values

#### `build_vector_store()` (given): one request for all chunks

```python
response = await client.embeddings.create(model=EMBEDDING_MODEL, input=[doc["text"] for doc in RUNBOOK_DOCS])
```

The endpoint accepts a **list** of texts, so all 8 chunks are embedded in one request instead of eight, which matters on a rate-limited plan. Each returned item is a vector of 3072 numbers (for the Gemini model). The vectors come back in the order the texts were sent. Some providers also number each item (`item.index`), but Gemini leaves it `None`, so the code only sorts by it when every item has a number.

#### `search_runbook(query, top_k)` (given)

It embeds the query and scores every stored chunk with plain-Python cosine similarity (no Chroma here), then sorts and returns the top `top_k`:

```python
[("err-5023", "ERR_5023: payment gateway timeout...", 0.8871),
 ("db-connection-pool", "Database Connection Pool Exhaustion...", 0.6373),
 ("deploy-drain-restart", "Drain traffic from the load balancer...", 0.5536)]
```

Three tuples, `(chunk_id, chunk_text, score)`, best first. The loop then keeps only the texts for the judge and the answer:

```python
retrieved_texts = [chunk_text for _, chunk_text, _ in retrieved]     # ids and scores dropped
```

#### Why the judge answers in JSON, and how it is checked

The judge has to return two facts: a yes/no and an optional new query. Asking for free text and picking it apart with string tricks is fragile (markdown bold, different capitalisation, extra sentences). Instead the file asks the provider for **structured output**: it sends a JSON schema as `response_format`, and the model returns JSON of exactly that shape.

```python
class JudgeVerdict(BaseModel):
    sufficient: bool
    better_query: str | None = ""

JUDGE_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {"sufficient": {"type": "boolean"}, "better_query": {"type": "string"}},
    "required": ["sufficient", "better_query"],
}
```

`JudgeVerdict` is the Pydantic model the code validates against. `JUDGE_VERDICT_SCHEMA` is the same shape written out by hand, so you can see exactly what is sent to the provider. `better_query` is an empty string, not `null`, when no query is needed, which keeps the schema as plain as possible.

#### `parse_judge_verdict(raw_reply)`: validate, don't trust

Gemini honoured the schema in all twelve live judge calls made with it. Not every provider does: some accept `response_format` without enforcing it, so a reply can still arrive as prose or wrapped in a code fence. So the function still validates:

```python
cleaned_reply = raw_reply.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
verdict = JudgeVerdict.model_validate(json.loads(cleaned_reply), strict=True)
```

`strict=True` means a value must already have the right type: the string `"yes"` is rejected for a boolean field instead of being quietly turned into `True`. What it returns for replies of different shapes:

```text
reply                                              sufficient  better_query    parsed_ok
{"sufficient": false, "better_query": "deploy.."}  False       "deploy.."      True
{"sufficient": true, "better_query": ""}           True        None            True
the same JSON inside a ```json fence               (same)      (same)          True
{"sufficient": true, "better_query": null}         True        None            True    <- null tolerated
{"sufficient": false, "better_query": "None."}     False       None            True    <- the word "none" means no query
{"sufficient": "yes", "better_query": ""}          False       None            False   <- a string is not a boolean
{"better_query": "x"}                              False       None            False   <- missing field
"I think the context is fine."                     False       None            False   <- prose
"SUFFICIENT: yes\nBETTER_QUERY: none"              False       None            False   <- a different format is refused
```

The last rows are why `parsed_ok` exists. A reply that is not a valid verdict must not silently count as "the retrieval was poor", or as "sufficient". `judge_retrieval` prints a warning in that case, and the loop stops.

#### `judge_retrieval(question, retrieved_chunks, history)`: two prompt layouts

The prompt is deliberately generic: it names no runbook and hints at no answer, so the verdict is the model's own. Without a conversation it is:

```text
Question: <question>

Retrieved runbook context:
<the chunks, separated by blank lines>

Decide whether this retrieved context contains the specific information needed to answer the
question. Be strict: ... Reply with a JSON object with two fields: sufficient (true or false),
and better_query (if sufficient is false, a more specific search query that would find what is
missing; if sufficient is true, an empty string).
```

With a conversation, three things are added: a `Conversation so far:` block (built by `format_history`), the label becomes `Latest question`, and the judge is told that the search engine cannot see the conversation, so the query must "make sense on its own, including anything the conversation says that the latest question leaves out". That last sentence is what turns "what if that doesn't work?" into a query that mentions the rollback. The call uses `temperature=0.0` and `response_format={"type": "json_schema", "json_schema": {"name": "judge_verdict", "schema": JUDGE_VERDICT_SCHEMA}}`, and `response.choices[0].message.content or ""` guards against a provider returning `None`.

#### `generate_final_answer(question, retrieved_chunks, history)`

The chat messages are sent in this order, so the model reads the follow-up the way the user meant it:

```text
[ system : "Answer ONLY using the runbook excerpts below..." + (history note) + the 3 chunks,
  user   : "How do I roll back a bad deploy?"            <- history turn
  assistant : "Run `deploy rollback ...`"                <- history turn
  user   : "what if that doesn't work?" ]                <- the original question
```

When there is a history, the system prompt gains one sentence: the earlier messages "are only there so you can understand what the latest question refers to; every fact in your answer must still come from the excerpts". Without it, a model told to answer ONLY from the excerpts can refuse a follow-up, because "that" is not defined in them. That happened in a real run: the judge said "sufficient" with the on-call chunk present, and the answer step still replied "I couldn't find that in the runbook", even at `temperature=0.0`. With the sentence, the same chunks gave the correct on-call answer. The call also uses `temperature=0.0`, like the judge, so the same chunks are answered the same way on each run.

#### `answer_with_agentic_retrieval`: the loop, step by step

The variables that change as it runs, traced for the follow-up scenario:

```text
start      current_query     = "what if that doesn't work?"
           tried_queries     = ["what if that doesn't work?"]
           previous_chunk_ids = None            model_calls = 0

attempt 1  search_runbook(...)                  model_calls = 1
           chunk_ids = {err-5023, deploy-rollback-2, deploy-rollback-1}
           previous_chunk_ids is None -> nothing to compare yet; remember chunk_ids
           judge_retrieval(question, texts, history)   model_calls = 2
             better_query = "what to do if deploy rollback fails or does not work"
           not None, not in tried_queries -> record it; current_query = that rewrite

attempt 2  search_runbook(current_query)        model_calls = 3
           chunk_ids = {deploy-rollback-2, deploy-rollback-1, oncall-escalation}
           differs from previous_chunk_ids -> new evidence, carry on
           judge_retrieval(...)                 model_calls = 4    sufficient = True
           generate_final_answer(question, texts, history)   model_calls = 5
           return {"outcome": "answered", "attempts": 2, "model_calls": 5}
```

Notice that `judge_retrieval` and `generate_final_answer` always receive `question` and `history`, never `current_query`. The queries are lowercased and stripped before comparing, so a rewrite that only changes capital letters still counts as "already tried". The "same chunks" check compares **sets** of ids, so a different order of the same three chunks still counts as no new evidence.

The four possible outcomes:

| outcome | meaning |
|---|---|
| `answered` | the judge said sufficient, and an answer was generated |
| `stopped_no_new_query` | the judge said insufficient but offered nothing new to try |
| `stopped_same_results` | a rewritten query brought back exactly the same chunks, so the judge call was skipped |
| `exhausted_attempts` | every one of the `max_attempts` was used, each with a query the loop had not tried and a chunk set it had not seen, none sufficient (the TLS run above) |

### Gotchas

- **The judge reads the evidence, not an answer.** The answer is written once, only after the judge approves. A failed attempt costs 2 calls, not 3.
- **The search never sees the conversation.** Only the judge and the answer step do. The rewrite is the only way history reaches the search, so a rewrite must make sense on its own.
- **The model remembers nothing between calls.** Whatever it needs, including the history, has to be in that call's input.
- **An exact string match is a weak test for "same query".** In the TLS run the last rewrite differed from the one before it by one word, so it counted as new. The "same chunks" rule is the stronger test, because it looks at what the search returned, not how the query was worded, though it did not fire in that run either.
- **Judge and answer use the original question, plus the conversation.** Only the search uses the rewrite.
- **A rewrite can only add what exists.** The conversation counts. A detail nobody ever said doesn't, so the rewrite just guesses words and drifts, as in the TLS case and the single-result experiment.
- **The first search uses the message exactly as typed.** For a follow-up that is the weak spot, and the loop exists to repair it.
- **A "sufficient" verdict is not a good answer.** The judge and the answer step are two separate model calls, and they can disagree. In a real run the judge passed the right chunks and the answer step still refused, because its prompt didn't explain what the earlier conversation was for.
- **Ask for structured output, then validate anyway.** `response_format` makes JSON very likely, but a provider can ignore it. Use strict validation so that `"yes"` is not accepted as `True`, and treat an invalid reply as a visible failure rather than as an answer.
- **The judge is a language model, so it can be wrong in both directions.** It can pass a weak retrieval, or reject a good one. It is also the same kind of model that writes the answer, so it is not an independent check. Chapter 5's deterministic verifier (re-adding the prices) is stronger because it uses no model at all.
- **Results vary between runs, even at `temperature=0.0`.** The same TLS question took 2 attempts in one run and 3 in the next. Don't expect your outcomes to match these exactly.
- **The loop can't fix a missing document.** If the answer isn't in the corpus, no rewrite will find it. The best outcome is an honest "I couldn't find it".
- **Top-1 is not always right.** In the stuck-deploy run the top score belonged to the wrong chunk, by a margin of 0.005. Taking the top 3 and answering from excerpts absorbed that mistake.
- **Compare sets, not lists, to detect "no new evidence".** The same three chunks in a different order is still the same evidence.
- **Don't assume a batch embedding response is numbered.** Gemini returns `index = None`, and sorting by it crashes. Rely on input order, and sort only when every index is present.
- **`model_calls` leaves out the one-time store build.** This file rebuilds its in-memory store on every run (1 request); a real vector database would keep it between runs.
- **For clear questions the loop is pure overhead:** 3 calls instead of 2, for the same answer.
- **Always cap the attempts.** Without `max_attempts`, a judge that keeps saying "no" would loop forever.

### Connection Forward

Problems 1 to 6 are all about finding the right *text*. The next problems turn to the agent's own memory, starting with Problem 7, where some facts are better stored as relationships than as paragraphs: "who owns this service?" is a link to follow, not a passage to retrieve.

---

## Theory 07: Graph Memory, Facts as Connected Dots

**Used by:** [Problem 7](#7-graph-memory-walking-relationships)

### The Idea in One Sentence

A **graph memory** stores facts as named things (**nodes**) joined by labeled one-way arrows (**edges**), and it answers a question by following arrows from node to node instead of searching for text that looks similar.

### The Problem It Solves

Problems 1 to 6 all find *text that looks like the question*. That works when one passage holds the whole answer. It breaks when the answer is a **chain**: two facts that only make sense together, where you can only find the second fact once you have read the first.

```text
question: "who's on call for the team that owns payments-service?"

fact 1:  payments-team  owns         payments-service    <- mentions payments-service: easy to find
fact 2:  Priya          on_call_for  payments-team       <- never mentions payments-service
                                     ▲
                                     the link between the two facts is "payments-team",
                                     and that word is not in the question at all
```

To find fact 2 you need the word "payments-team", and you only learn that word by reading fact 1. A similarity search compares the question with each fact separately, all in one go, so there is no step where fact 1's answer becomes fact 2's search term.

*To be fair to vector search:* with five short facts it would probably return both, because every fact mentions "payments". The trouble starts as the memory grows. With hundreds of teams and on-call facts, fact 2 looks no more similar to the question than any other on-call fact, and the model is left to guess the join. A graph does the join explicitly: the output of hop 1 is the input of hop 2.

### The Intuition

Think of an org chart printed on a wall. To answer "who is on call for Alice's team?" you put your finger on Alice, follow her line to her team, and then look for the line that says "on call" pointing at that team. You never compare words. You follow lines. That is a **graph walk**.

The words you need:

| Word | Meaning | Example in Problem 7 |
|---|---|---|
| **node** | a thing: a person, team, service | `Priya`, `payments-team` |
| **edge** | a labeled one-way arrow from one node to another | `Priya --on_call_for--> payments-team` |
| **relation** | the label on an edge | `on_call_for` |
| **source / target** | where an edge starts / where it points | source `Priya`, target `payments-team` |
| **triple** | one edge written as `(source, relation, target)` | `("Priya", "on_call_for", "payments-team")` |
| **observation** | a note stuck on one node that points nowhere | `"had a 20-minute outage on 2026-08-01"` |
| **outgoing / incoming** | edges that leave a node / edges that arrive at it | `payments-team` has 1 outgoing, 3 incoming |
| **hop** | following one edge, in either direction | Alice → payments-team |

The whole Problem 7 graph, drawn as a picture:

```text
            ┌───────┐   reports_to   ┌───────┐
            │ Alice │───────────────►│ Priya │
            └───┬───┘                └─┬───┬─┘
                │                      │   │
      member_of │            member_of │   │ on_call_for
                │                      │   │
                ▼                      ▼   ▼
            ┌──────────────────────────────────┐   owns   ┌──────────────────┐
            │          payments-team           │─────────►│ payments-service │
            └──────────────────────────────────┘          └──────────────────┘
                                                            observation:
                                                            "had a 20-minute outage
                                                             on 2026-08-01"

  4 nodes, 5 edges, 1 observation.
  payments-team: 1 outgoing edge (owns), 3 incoming (member_of x2, on_call_for).
  payments-service: 0 outgoing edges, 1 incoming (owns).
```

**Direction is the key idea.** Every edge points one way. "payments-team owns payments-service" is stored as an arrow *from* the team *to* the service. Asking "what does payments-team own?" follows the arrow. Asking "who owns payments-service?" walks *against* the arrow. Both questions use the same single fact, but as the next section shows, the two directions cost very different amounts of work.

### How the Graph Is Stored: Three Options

The same five edges can be laid out in three common ways.

```text
1. EDGE LIST: one list of triples
   [("payments-team", "owns",        "payments-service"),
    ("Priya",         "member_of",   "payments-team"),
    ("Alice",         "member_of",   "payments-team"),
    ("Priya",         "on_call_for", "payments-team"),
    ("Alice",         "reports_to",  "Priya")]
   Any question = read every triple.

2. ADJACENCY MATRIX: one grid per relation, a 1 where an arrow exists
   on_call_for      payments-team  payments-service  Priya  Alice
   payments-team          0               0            0      0
   payments-service       0               0            0      0
   Priya                  1               0            0      0
   Alice                  0               0            0      0
   Forward = read a row. Backward = read a column. But almost every cell is 0.

3. ADJACENCY LIST: each node keeps its own outgoing arrows   <- Problem 7 uses this
   graph = {
     "payments-team":    {"observations": [], "edges": {"owns": ["payments-service"]}},
     "payments-service": {"observations": ["had a 20-minute outage on 2026-08-01"], "edges": {}},
     "Priya":            {"observations": [], "edges": {"member_of": ["payments-team"],
                                                        "on_call_for": ["payments-team"]}},
     "Alice":            {"observations": [], "edges": {"member_of": ["payments-team"],
                                                        "reports_to": ["Priya"]}},
   }
```

How they compare, in plain words:

| Layout | Forward ("what does X point to?") | Backward ("who points at X?") | Space |
|---|---|---|---|
| Edge list | read every triple | read every triple | one entry per edge |
| Adjacency matrix | read one row | read one column | a whole grid per relation, nearly all zeros |
| **Adjacency list** | **one dict lookup** | check every node | one entry per node and per edge |

Problem 7's graph has 4 nodes, 4 relation types and 5 edges. A grid per relation would need 4 x 4 x 4 = 64 cells to hold 5 ones. With 1,000 nodes it would be 1,000,000 cells *per relation*, nearly all zero. The adjacency list stores only the ones, which is why it is the usual choice. Its weak spot is the backward hop, and Problem 7 shows that cost on purpose.

### How a Hop Works

The graph is a pile of facts shaped "source, relation, target". A **hop** answers one question: "what sits at the other end of the arrows with this label?" There are three versions, one for each function you write:

```text
find_related(graph, "Alice", "reports_to")             -> ['Priya']
   forward: start at Alice and follow her reports_to arrow, WITH the arrow

find_incoming(graph, "payments-team", "on_call_for")   -> ['Priya']
   backward: find every node whose on_call_for arrow points AT payments-team, AGAINST the arrow

find_related_two_hops(...)
   do hop 1, then do hop 2 from EACH node hop 1 found, and pool the answers, each one once
```

Both directions read the same stored facts. The only difference is which end you start from.

#### Dry run with the real graph

**Demo A (forward, forward):** "who does Alice report to, and which team is that person on call for?"

```text
Step 1: Alice reports_to   ->  Priya           (the stored edge Alice -reports_to-> Priya)
Step 2: Priya on_call_for  ->  payments-team   (the stored edge Priya -on_call_for-> payments-team)
Answer: payments-team
```

**Demo B (backward, backward):** "who's on call for the team that owns payments-service?"

```text
Step 1: who points at payments-service with "owns"?        payments-team
Step 2: who points at payments-team with "on_call_for"?    Priya
Answer: Priya
```

Nothing leaves payments-service, so a forward walk from it finds nothing. The "owns" arrow is stored on payments-team, pointing at the service. That is why Demo B has to go backward.

**Why a result can be reached twice.** Say a service `svc` is `owned_by` both `team-a` and `team-b`, Sam is on call for both teams, and Lee is on call for `team-b` only:

```text
Hop 1 (out, owned_by):    team-a, team-b
Hop 2 (in, on_call_for):  from team-a: Sam        from team-b: Sam, Lee
find_related_two_hops returns ['Sam', 'Lee']
```

Sam turns up twice, because he is reached through two different teams. The "skip it if it is already in the list" check keeps him once.

#### What each hop costs

- **Forward hop:** one dict lookup, `graph[v]["edges"][r]`, plus copying the names found. The size of the graph does not matter.
- **Backward hop:** `find_incoming` checks every node in the graph, because nothing stores the reverse direction.
- **Two hops:** the cost of hop 1, plus one more hop for each node hop 1 found.

```text
Demo B on the Problem 7 graph:      2 backward hops x 4 nodes          = 8 node checks
the same question, 1,000,000 nodes: 2 backward hops x 1,000,000 nodes  = 2,000,000 node checks
```

The usual fix is a **reverse index**: every node also keeps an `"incoming"` dict, so a backward hop becomes a lookup too:

```text
graph["payments-team"] = {
    "observations": [],
    "edges":    {"owns": ["payments-service"]},
    "incoming": {"member_of": ["Priya", "Alice"], "on_call_for": ["Priya"]},   <- extra copy
}
```

The price is that every `add_fact` now writes in two places, and the two copies must never disagree. Graph databases do this bookkeeping for you. Problem 7 leaves it out on purpose, so you can see why it exists. It also avoids the hand-typed shortcut mistake this file used to make (see "What Is Real and What Is Simplified" below).

### Dry Run: Watching `find_incoming` Scan

`find_incoming(graph, "payments-service", "owns")`, hop 1 of Demo B:

```text
node checked        node["edges"].get("owns", [])    "payments-service" in it?   kept
payments-team       ["payments-service"]             yes                         payments-team
payments-service    []                               no
Priya               []                               no
Alice               []                               no
result: ['payments-team']                            (4 nodes checked)
```

`find_incoming(graph, "payments-team", "on_call_for")`, hop 2:

```text
node checked        node["edges"].get("on_call_for", [])   "payments-team" in it?   kept
payments-team       []                                     no
payments-service    []                                     no
Priya               ["payments-team"]                      yes                      Priya
Alice               []                                     no
result: ['Priya']                                          (4 nodes checked)
```

The same walk drawn on the picture. Both hops go *against* the arrows:

```text
   Priya ──on_call_for──► payments-team ──owns──► payments-service      (how the facts are stored)

   Priya ◄────────────── payments-team ◄──────── payments-service      (how Demo B walks them)
          hop 2 (in)                     hop 1 (in)                    start here
```

**Demo C (forward, then backward):** "who's on call for Alice's team?"

```text
hop 1 (out): graph["Alice"]["edges"]["member_of"]        -> ['payments-team']     (1 lookup)
hop 2 (in):  find_incoming(graph, 'payments-team', 'on_call_for') -> ['Priya']   (4 node checks)
```

### Walking Through the Code With Real Values

#### `add_fact` (given): both nodes always exist

Starting from `graph = {}`, after the first call `add_fact(graph, "payments-team", "owns", "payments-service")`:

```python
{"payments-team":    {"observations": [], "edges": {"owns": ["payments-service"]}},
 "payments-service": {"observations": [], "edges": {}}}       # created too, with no edges
```

The **target** node is created even though nothing is stored on it. That matters later: `payments-service` is a real key, so you can attach an observation to it, and asking `find_related` about it returns `[]` instead of raising a `KeyError`. Edges are stored **once**, on the source. After all five facts, `payments-service` still has `"edges": {}`.

#### `find_related`: return a copy

```python
return list(graph[entity]["edges"].get(relation, []))
```

`list(...)` makes a new list. Without it the function hands out the graph's own list, and anyone who edits the result edits the memory. This was checked with the code as it was before the fix:

```python
result = find_related(graph, "Priya", "on_call_for")    # the old version: no list(...)
result.append("search-team")                            # the caller only meant to edit its result
graph["Priya"]["edges"]                                 # {'on_call_for': ['payments-team', 'search-team']}
```

```text
WITHOUT list(...)                                   WITH list(...)
graph["Priya"]["edges"]["on_call_for"] ──┐          graph[...]["on_call_for"] ──► ['payments-team']
                                         ├─► ['payments-team']
result ──────────────────────────────────┘          result ──────────────────────► ['payments-team']   (separate copy)
two names, ONE list: append to one, both change     two lists: appending to result leaves the graph alone
```

`.get(relation, [])` returns an empty list when the node has no edges with that label, and the `if entity not in graph: return []` line handles a node that doesn't exist at all.

#### `find_incoming`: the scan, in one expression

```python
return [node_name for node_name, node in graph.items()
        if entity in node["edges"].get(relation, [])]
```

It reads every `(node_name, node)` pair and keeps the name when that node's `relation` list contains `entity`. The results come out in the order the nodes were added (Python dicts keep insertion order), so `find_incoming(graph, "payments-team", "member_of")` is always `['Priya', 'Alice']`. An unknown entity simply matches nothing and returns `[]`.

#### `walk_one_hop` (given): choosing a direction

`"out"` calls `find_related`, `"in"` calls `find_incoming`, and anything else raises `ValueError`. It exists so `find_related_two_hops` can take a direction for each hop without its own `if`/`else`.

#### `find_related_two_hops`: the variables, step by step

For Demo B, `find_related_two_hops(graph, "payments-service", "owns", "on_call_for", "in", "in")`:

```text
first_hop_results  = walk_one_hop(graph, "payments-service", "owns", "in")  = ['payments-team']
second_hop_results = []

intermediate_node = "payments-team"
    walk_one_hop(graph, "payments-team", "on_call_for", "in")              = ['Priya']
    "Priya" not in second_hop_results -> append      second_hop_results = ['Priya']

return ['Priya']
```

For the co-owned example, `("svc", "owned_by", "on_call_for", "out", "in")`:

```text
first_hop_results = ['team-a', 'team-b']
intermediate "team-a" -> ['Sam']            -> append Sam           ['Sam']
intermediate "team-b" -> ['Sam', 'Lee']     -> Sam already there, skip; append Lee   ['Sam', 'Lee']
return ['Sam', 'Lee']
```

If hop 1 finds nothing, the loop never runs and the result is `[]`. Nothing crashes. The question simply has no answer in this graph.

#### `save_graph` and `load_graph`: memory that survives

The graph contains only strings, lists and dicts, which are exactly the types JSON stores. So `json.dump` and then `json.load` give back an equal dict, with the keys in the same order. The real run printed `same contents: True` and `(loaded_graph is graph) = False`: the loaded graph is equal to the saved one, but it is a brand-new object built from the file.

Why write to a `.tmp` file and rename it:

```text
WRITING STRAIGHT TO THE FILE                    WRITE TO .tmp, THEN RENAME (what save_graph does)
open graph_memory.json for "w"                  write everything to graph_memory.json.tmp
  -> the old contents are wiped at once         temporary_path.replace(file_path)
write node 1, node 2, ...                         -> one step: the name now points at the new file
   *** crash here ***                           crash BEFORE the rename: the old file is untouched
  -> a half-written file that json.load         crash AFTER the rename: the new file is complete
     cannot read: the whole memory is gone      either way, a readable file
```

On the same disk, a rename is all-or-nothing, so a reader sees either the whole old file or the whole new one. The MCP reference memory server saves its graph the same way.

`load_graph` returns `{}` when the file doesn't exist. On the very first run nothing has been remembered yet, and "an empty memory" is the honest answer, not an error.

The three sessions in `run_persistence_demo`:

```text
 one run of the script
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ session 1   build_ops_assistant_graph() ──save_graph──► data/graph_memory.json   │  4 nodes, 578 bytes
 │                                                                                  │
 │ session 2   load_graph ◄── file          (a new dict, equal to the saved one)    │
 │             two-hop question             -> ['Priya']                            │
 │             add_fact("Bob", "member_of", "payments-team")                        │
 │             save_graph ──► file                                                  │  5 nodes
 │                                                                                  │
 │ session 3   load_graph ◄── file                                                  │
 │             find_incoming(..., 'payments-team', 'member_of') -> Priya, Alice, Bob│
 └──────────────────────────────────────────────────────────────────────────────────┘
 the next run starts again from session 1 and overwrites the file, so Bob is never added twice
```

### Entity Resolution: The Weak Spot

**Entity resolution** means deciding when two different names refer to the same real thing. A graph keys its nodes by exact string, so it does not do this on its own:

```text
what really happened                        what the graph stores

        one person                          ┌──────────┐  on_call_for   ┌───────────────┐
  (introduced as "Priya K.",                │ Priya K. │───────────────►│ payments-team │
   later called "Priya")                    └──────────┘                └───────────────┘
                                            ┌──────────┐  handling      ┌──────────────┐
                                            │ Priya    │───────────────►│ incident-482 │
                                            └──────────┘                └──────────────┘
                                            two nodes, no link between them

find_related(graph, "Priya", "on_call_for")  ->  []        (correct for this data, wrong for the world)
```

The merge itself is mechanical: move every edge and observation from `"Priya K."` onto `"Priya"`, change every edge that points at `"Priya K."` to point at `"Priya"`, and then delete `"Priya K."`. The hard part is **deciding** to merge:

| Pair of names | Same thing? | Why it's hard |
|---|---|---|
| `Priya K.` / `Priya` | probably | a missing surname looks the same as a different person who shares the first name |
| `Sam` on payments / `Sam` on search | probably not | identical strings, two different people |
| `IBM` / `International Business Machines` | yes | no overlapping letters at all |
| `Doc` / `Doc Brown` | yes | a nickname versus a full name |

Real systems use clues such as a shared team, email or ID, ask an LLM to compare the two nodes' facts, or ask a human. Every one of those can be wrong, and a wrong merge is worse than a missed one, because it glues two people's facts together. Problem 7 only shows the failure. It does not attempt a fix.

### Graph Memory vs Vector Memory

| Question | Better tool | Why |
|---|---|---|
| "who's on call for the team that owns payments-service?" | graph | a chain where hop 1's answer is hop 2's input |
| "what has Priya been working on lately?" | vector | fuzzy and about meaning; nothing names an exact edge |
| "who reports to Alice's manager?" | graph | two exact hops through an org chart |
| "did anyone mention cache problems before?" | vector | the wording varies; similarity finds paraphrases |
| "is Priya still on call?" | graph | one exact edge, easy to change when the fact changes |
| "does Priya work somewhere cold?" | neither alone | the graph has no "cold" edge, and vector search needs the right text |

A graph can also explain itself. The path `payments-service ◄─owns─ payments-team ◄─on_call_for─ Priya` *is* the reason for the answer. A vector search can only tell you "this chunk scored 0.81".

### Where This Sits in a Real Agent

```text
WRITE PATH (after each message)
  user message ──► LLM extracts triples ──► entity resolution ──► add_fact / add_observation ──► save
  "Bob just joined     ("Bob", "member_of",     is "Bob" a node we      the step Problem 7      file or
   payments"            "payments-team")        already know?           does by hand            database

READ PATH (when a question arrives)
  question ──► find the entities in it ──► walk the graph ──► facts ──┐
           └─► vector search over past text ──────────────► chunks ──┴──► model writes the answer
```

Problem 7 builds only the middle of the write path (with the facts typed in by hand), the graph walk, and the save. Extraction and resolution are LLM steps that cost money and can make mistakes. Pairing the graph with vector search is Problem 8.

### What Is Real and What Is Simplified

| Part | Status |
|---|---|
| The graph, the forward and backward walks, the two-hop walk | **Real.** Plain Python with no network calls; everything is computed from the stored facts. |
| Saving and loading | **Real.** A JSON file, written to a temp file and then renamed, just as the MCP reference memory server does. |
| The facts | **Typed by hand** in `build_ops_assistant_graph`. A real agent extracts them from conversation with an LLM. |
| Reverse lookups | **Real but slow.** A full scan, not an index. Before the fix, this file answered "who owns payments-service?" with two hand-typed shortcut edges (`owned_by`, `on_call_for_reverse`) that already held the answer, so nothing was really walked. Delete those shortcuts and the answer became `[]`. They are gone, and an offline test now checks that removing the real `owns` fact removes the answer. |
| Entity resolution | **Not done.** It is only shown as a failure. |
| Relation names | **Free strings.** Nothing stops `on_call_for` and `oncall_for` from both existing. |
| Storage | **The whole file is rewritten on every save**, with no locking. Fine for thousands of nodes and one writer. |

### Gotchas

- **Direction matters.** An edge is stored on its source. `find_related(graph, "payments-service", "owns")` is `[]` because the arrow points *at* the service. Before writing a walk, ask yourself which node the arrow starts from.
- **Store each fact once.** Hand-typing a reverse edge (`owned_by`) for every forward edge looks helpful, but now two facts must stay in sync, and the answer may come from the copy rather than the truth. Walk backward instead, or keep a proper reverse index that `add_fact` updates automatically.
- **Return copies of stored lists.** Otherwise a caller's `.append` silently changes the memory.
- **An unknown entity returns `[]`, not an error.** A missing answer is normal in a memory.
- **Relation names must match exactly.** `on_call_for`, `oncall_for` and `on-call-for` are three different relations. So are `"Priya"` and `"priya"`.
- **Two hops can reach the same node twice.** Keep a result once, or the answer lists a person twice.
- **An empty hop 1 means an empty answer,** not a crash. Demo B checks `if not hop_1` before reading `hop_1[0]`.
- **Backward walks scan everything.** That is fine at this size and slow at a million nodes; that is the reason for reverse indexes.
- **Never write a file in place.** A crash mid-write destroys the whole memory. Write to a temp file and rename it.
- **Rewriting the whole file has limits.** Two processes saving at once means the last one wins and the other's facts are lost. The MCP server adds a lock file for this; a database handles it for you.
- **A graph cannot match fuzzily.** No edge means no answer, even when the meaning is "obviously" there.
- **Entity resolution failures are silent.** Nothing warns you that "Priya K." and "Priya" were split. You only notice when an answer comes back empty.

### Connection Forward

A graph answers exact chains but can't match by meaning, and vector search matches by meaning but can't follow chains. Problem 8 puts the two together. Vector search finds similar past incident chat, the entities named in the new message are looked up in the graph, and the model answers from both. Then the new message is written back to both stores. It also adds a small illustration of OS-style paging: a fact is moved out of the active context and recalled later by a topic label.


---

## Theory 08: Hybrid Memory and Paging, Two Stores and a Small Window

**Used by:** [Problem 8](#8-hybrid-semantic--graph-memory-plus-os-inspired-paging)

### The Idea in One Sentence

**Hybrid memory** keeps two kinds of memory side by side, a **semantic** store that finds old text by meaning and a **graph** that holds the current structured facts, and uses both to answer one message. **Paging** is a separate idea about the model's small window: move text out of it to make room, and bring it back when it is needed.

### The Problem It Solves

Each store alone has a hole, and the holes are opposite:

| Question | Semantic memory alone | Graph memory alone |
|---|---|---|
| "EU deploy is timing out again" (is this a known pattern?) | **Yes.** Old chat about cold snaps and failing EU deploys is close in meaning, even though no message says "timing out". | **No.** Nobody wired an edge from "EU cluster" to "cold weather", so the graph has nothing to follow. |
| "Who is on call for payments-service now?" | **Unreliable.** It finds chat that *mentions* on-call, but chat goes stale and nothing marks the latest message as the truth. | **Yes.** One edge, and it can be changed when the fact changes. |
| "What else might this problem hit?" | **No.** Nothing in the text says the EU cluster shares a cache with US-East unless a message happened to. | **Yes**, by walking: eu-cluster, then eu-cache-layer, then us-east-cluster. |

```text
            SEMANTIC MEMORY                          GRAPH MEMORY
   finds text that MEANS the same             follows facts that are CONNECTED
   good at: patterns, fuzzy recall            good at: who, what, current state
   weak at: "which one is current?"           weak at: anything nobody wired in
                     \                              /
                      '------- use BOTH ----------'
```

There is a second, separate problem. The model's **context window** (the text it can see on one call) is small and the conversation keeps growing. Something has to decide what stays in the window and what is kept outside it. That is the paging half of the problem.

### The Intuition

Picture an on-call manager with two things on the desk. The first is a **notebook of old chat logs**: huge, searchable by "sounds like", and full of things people said at different times, some of them out of date. The second is a **wall chart** of who owns what and who is on call today: small, exact, and always kept current. When a message comes in, the manager skims the notebook for similar past incidents, looks at the wall chart for the services involved, and writes one reply using both.

```text
 incoming message: "deploy to the EU cluster is timing out again"
        │
   [1]  ├── notebook search ──► 3 similar old chat lines   "EU deploys fail when below freezing" ...
        │
   [2]  ├── who/what is named? ─► eu-cluster  (from the message)  + names inside those 3 lines
        │
   [3]  ├── wall chart walk ───► eu-cluster uses eu-cache-layer
        │                        payments-service runs_in eu-cluster
        │                        Priya on_call_for payments-service       (2 hops from eu-cluster)
        │
   [4]  ├── ONE model call ────► "Looks like the recurring EU cold-weather issue. It shares a
        │                         cache with US-East. Priya is on call for payments-service."
        │
   [5]  └── write back ────────► message into the notebook; a handoff UPDATES the wall chart
```

The **paging** idea comes from how a computer handles its memory. Programs run in fast, small **RAM** and keep the rest on a big, slow **disk**. When RAM fills up, the operating system moves old pages to disk and brings them back when something asks for them. Replace "RAM" with "the context window" and "disk" with "an archive", and you have paging for an agent:

```text
   CONTEXT WINDOW  ("RAM": small, the model sees ALL of it, every call)
   ┌──────────────────────────────────────────┐
   │ turn 5   turn 6   turn 7   new question  │
   └──────────────▲───────────────┬───────────┘
                  │ page_in       │ page_out
                  │ (find by      │ (oldest turns move out
                  │  keyword)     │  when over budget)
   ┌──────────────┴───────────────▼───────────┐
   │ ARCHIVE  ("disk": big, outside the prompt)│
   │ topic "db-connection-incident": turns 1-4 │
   └──────────────────────────────────────────┘
```

### Part A: Why Both Stores, With Real Numbers

#### Why a Handoff Needs the Graph

After "Marcus is now on-call for payments-service" is written back, semantic memory holds both of these, with nothing to say which is newer:

```text
SEMANTIC MEMORY (kept forever, never edited)             GRAPH (edited when a fact changes)
  mem-3     "...on-call rotation moved to Priya..."        Marcus --on_call_for--> payments-service
  mem-live-7 "Marcus is now on-call for payments-service"  payments-service (note): on-call changed: Priya -> Marcus
```

A search for "who should I page about payments-service right now?" can bring back either snippet, or both. The graph has exactly one current answer and the history as a note. The system prompt tells the model: when an old snippet disagrees with a graph fact, trust the graph. This is the reason the handoff **replaces** the old edge. If it only added Marcus's edge, the graph would say two people are on call and would be no better than the chat.

#### How the Search Score Works

Semantic search is the same cosine search as Theory 02, so this is only a reminder of the last step. Chroma reports a **distance**: how far apart two vectors point, where 0 means pointing the same way. The file prints a **similarity**, which is easier to read: it is `1 - distance`, so higher means closer. The collection is created with `{"hnsw:space": "cosine"}`, which is what tells Chroma to use this kind of distance.

A tiny example with 2 numbers per vector. The message is `[1, 0]` and one stored snippet is `[0.6, 0.8]`. Both vectors have length 1, so the score is just "multiply the matching numbers and add them up":

```text
Step 1  multiply and add     1 x 0.6 + 0 x 0.8 = 0.6       (how much the two agree)
Step 2  that is the similarity: 0.6
Step 3  Chroma reports distance = 1 - 0.6 = 0.4
Step 4  the file prints similarity = 1 - 0.4 = 0.6
```

A stored copy of the query itself scores 1.0000 (distance 0). That is exactly what a second run used to find before the reset: its own old message at the top.

#### How Far the Graph Walk Reaches

Start from the entities, take every fact that touches them, then take every fact that touches the nodes those facts reached. Each round is one **hop**. The hop limit stops the walk from collecting the whole graph. An edge counts whichever way it points and whatever it is called. With `max_hops=2` the walk expands the start nodes (hop 1) and then the nodes they reached (hop 2). The nodes found during hop 2 are not expanded.

Dry run on the real graph, starting from `eu-cluster`:

```text
reached after hop 1:  eu-cluster, eu-cache-layer, payments-service
reached after hop 2:  + us-east-cluster, payments-team, Priya

max_hops = 1:  the facts touching eu-cluster ................. 2 edges + 1 note   = 3 lines
max_hops = 2:  + the facts touching the 2 nodes hop 1 found .. 5 edges + 1 note   = 6 lines   <- what the file uses
max_hops = 3:  + the facts touching the 3 nodes hop 2 found .. 6 edges + 1 note   = 7 lines   (adds search-service runs_in us-east-cluster)
```

These counts were measured by running the code. The whole graph has 9 edges and 1 note (10 lines), so the 2-hop walk returns 6 of them and leaves out the US-East search team and the APAC billing group, which hold facts that have nothing to do with this message.

The walk uses `facts_touching`, which has to scan **every** node to find edges pointing in (Theory 07's backward walk). The cost is the number of nodes expanded times the number of nodes in the graph:

```text
nodes expanded:  eu-cluster (hop 1), then eu-cache-layer and payments-service (hop 2)  = 3
node checks:     3 x 11 nodes = 33
```

With a million nodes, those same three expansions would cost 3,000,000 checks. A real graph database keeps a reverse index for this. The file does not, on purpose.

### Two Settings: The Chat Model and the Embedding Model

The file uses two different jobs from a model, and each gets its own setting:

```text
 CHAT_PROVIDER = "gemini"        writes the ONE answer per message        3 calls per run
 EMBEDDING_PROVIDER = "ollama"   turns text into numbers for Chroma       7 requests per run, local, free
```

The embedding side runs more often and needs no clever model, only one that places similar meanings close together, so a small local model does it well. A local `qwen3-embedding:0.6b` is 639 MB. The chat side stays on Gemini, because a model that writes good answers is much larger.

**Document and query prefixes.** Embedding models expect a short label in front of the text, so they know what role it plays. `qwen3-embedding:0.6b` labels only the **query**, with an instruction that says what the search is for. Stored texts are plain:

```text
stored in Chroma:   "cold snap in the EU region again, deploys flaking"
used to search:     "Instruct: Given a chat message, retrieve relevant past chat messages
                     Query:deploy to the EU cluster is timing out again..."
```

The prefix is part of the text that is embedded, so the numbers change with it. Qwen's model card says leaving the instruction off costs about 1 to 5% in most retrieval tests. `nomic-embed-text` labels **both** sides instead (`search_document: ` and `search_query: `). `EMBEDDING_PREFIXES` holds each model's pair, and a model that isn't in the table is refused at start-up rather than run without its prefix.

**The write-back needs a second embedding.** In step 1 the message is embedded as a **query**. In step 5 the same message is stored, and a stored text should be embedded as a **document**. When the two prefixes are the same (Gemini: both empty), the step 1 vector is reused. When they differ (Qwen3 and nomic), the message is embedded again. That is why a run is 7 local requests: 1 for the seeds, then a query and a document for each of 3 messages.

**Vectors from different models never mix.** `qwen3-embedding:0.6b` gives 1024 numbers per text, `nomic-embed-text` 768 and Gemini's model 3072. Chroma would reject a mix, and even with equal sizes the numbers would mean different things. The collection is rebuilt every run, so changing the setting is safe here.

### The Five Steps, With Real Values

#### `reset_semantic_memory()` (given): the same start every run

The Chroma server is a separate process, so what a run writes is still there for the next run. Without the reset:

```text
run 1, message 1 top hits:   mem-5, mem-2, mem-1
run 2, message 1 top hits:   mem-live-7 (similarity 1.0000: run 1's own message), mem-5, mem-2     <- mem-1 pushed out
```

The ids and their order above came from a test with stand-in embeddings, so a real Gemini run will rank the other snippets differently. The part that does not depend on the model is the top row: the second run stored the same text as the first, so the old copy is an exact match and always scores 1.0000. The function deletes the collection if it exists, creates it again, and stores the 5 seed snippets with one embedding request (`embed_texts` sends a list, with the document prefix on each text. `qwen3-embedding:0.6b` returns 1024 numbers per snippet; Gemini would return 3072 and leaves `item.index` empty, so the items are only sorted when every index is present).

#### `facts_touching(graph, node_name)`: every edge that touches a node

For `"payments-service"`:

```text
OUTGOING (its own edges):
    payments-service --runs_in--> eu-cluster                      -> ("payments-service", "runs_in", "eu-cluster")
INCOMING (scan every other node, keep edges that point at it):
    payments-team   --owns------> payments-service                -> ("payments-team", "owns", "payments-service")
    Priya           --on_call_for-> payments-service              -> ("Priya", "on_call_for", "payments-service")
```

```text
                     owns          ┌──────────────────┐   runs_in
   payments-team ───────────────► │ payments-service │ ───────────► eu-cluster
                                   └──────────────────┘
   Priya ───────── on_call_for ──────────▲
```

This is the missing piece in the old file: it only read the outgoing line, so "Priya on_call_for payments-service" was never found.

#### `collect_facts_near`: the walk, round by round

The three things it keeps track of, traced from `["eu-cluster"]` with `max_hops=2`:

```text
start       frontier = [eu-cluster]     visited = {eu-cluster}     collected = []

hop 1       expand eu-cluster:  facts_touching -> (eu-cluster uses eu-cache-layer)
                                                  (payments-service runs_in eu-cluster)
            new neighbours: eu-cache-layer, payments-service   -> frontier for hop 2
            payments-service has a note                        -> collected too
            collected: (1, eu-cluster uses eu-cache-layer)
                       (1, payments-service runs_in eu-cluster)
                       (1, payments-service (note): had a 20-minute outage on 2026-08-01)

hop 2       expand eu-cache-layer:  (eu-cluster uses eu-cache-layer)       already seen, skip
                                    (us-east-cluster uses eu-cache-layer)  NEW
            expand payments-service: (payments-service runs_in eu-cluster)  already seen, skip
                                    (payments-team owns payments-service)  NEW
                                    (Priya on_call_for payments-service)   NEW
            new neighbours: us-east-cluster, payments-team, Priya  (the loop ends: max_hops reached)
```

- **`visited`** stops the walk from expanding a node twice. Without it, eu-cluster and eu-cache-layer would send the walk back and forth between them forever.
- **`seen_fact_texts`** stops the same fact being listed twice, because an edge between two reached nodes is found from both ends.
- The hop number on each line tells the model (and you) how far from the start that fact was found.

#### `extract_entities(text, graph)`: which graph nodes does this text name?

It builds a table of 18 spellings to look for: the 11 node names in lowercase (`"eu-cluster"`, `"priya"` ...) plus the 7 aliases in `ENTITY_ALIASES` (`"eu cluster"`, `"eu region"`, `"eu"`, `"us-east"`, `"payments"`, `"search"`, `"billing"`). Each spelling is searched with:

```python
pattern = rf"(?<![\w-]){re.escape(surface_form)}(?![\w-])"
```

`(?<![\w-])` means "the character before is not a letter, digit, underscore or hyphen", and `(?![\w-])` means the same for the character after. Together they say "this must be a whole word". The results:

```text
text                                                      result
"deploy to the EU cluster is timing out again, ..."       ['eu-cluster']      alias "eu cluster" hits (and "eu" hits too, same entity, kept once)
"the queue is backed up"                                  []                  "eu" inside qu-EU-e: the letter before it is a word character
"eu-cache-layer is hot"                                   ['eu-cache-layer']  node name matches; alias "eu" is followed by "-", so it does not
"who should I page about payments-service right now?"     ['payments-service']
```

Step 2 runs this on the message and then on each of the 3 retrieved snippets, and keeps the new names from the snippets separately, so the output shows which entities came from where.

#### `NEW_ON_CALL_PATTERN` and `record_on_call_change`: a handoff replaces

```python
r"(?P<person>(?-i:[A-Z])[\w.\-]*) is now on[- ]call for (?P<service>[\w\-]+)"      # with re.IGNORECASE
```

`(?-i:[A-Z])` switches case-insensitivity **off** for that one letter, so the name has to start with a capital. Without it, "it is now on call for billing" would record a person called "it".

```text
"Marcus is now on-call for payments-service."  ->  person='Marcus', service='payments-service'
"ok so it is now on call for billing"          ->  no match
```

Before and after `record_on_call_change(graph, "Marcus", "payments-service")`:

```text
BEFORE                                        AFTER
Priya   edges: {on_call_for: [payments-service]}     Priya   edges: {}                       (edge removed, key deleted when empty)
Marcus  (does not exist)                              Marcus  edges: {on_call_for: [payments-service]}
payments-service notes: [outage note]                 payments-service notes: [outage note, "on-call changed: Priya -> Marcus"]
find_incoming(graph, "payments-service", "on_call_for") == ['Priya']        == ['Marcus']
```

It returns `['Priya']` (who was on call before). Doing the same handoff twice changes nothing a second time except adding another history note.

#### `handle_incoming_message`: the variables

```text
message              the user's text
message_embedding    the message as a vector (computed once in step 1, reused in step 5)
semantic_hits        3 snippet texts from Chroma, best first
from_message         entities named in the message
from_hits            entities named only in the snippets
entities             from_message + from_hits
near_facts           [(hop, fact_text), ...] from the graph walk
system_prompt        two labelled lists (snippets, graph facts) + the rule "trust the graph"
combined_answer      the model's reply
```

Step 4 is **one** chat call (`temperature=0.0`, through `chat_client`). Each message therefore makes one Gemini chat call, plus two local embedding requests (the search, and the stored copy). The run makes 3 chat calls and 7 embedding requests: 1 batched request for the seeds plus 2 for each of 3 messages. Only the 3 chat calls use Gemini quota.

The third message, after the handoff, walking from `["payments-service"]` (the real run may also add entities from the hits):

```text
hop 0: payments-service (note): had a 20-minute outage on 2026-08-01
hop 0: payments-service (note): on-call changed: Priya -> Marcus
hop 1: payments-service runs_in eu-cluster
hop 1: payments-team owns payments-service
hop 1: Marcus on_call_for payments-service
hop 2: eu-cluster uses eu-cache-layer
```

Priya is not in it. Her node still exists, but with no edges nothing leads to her.

### Part B: Paging

#### A Word Budget

Count how full the window is, in words, and when the count goes over `CONTEXT_BUDGET_WORDS` (50 here), move the oldest turns out. Words stand in for **tokens**. Real systems count tokens, which are not the same thing as words, but the logic is identical.

The numbers below come from running `run_paging_demo`:

```text
4 turns about the DB incident ................ used = 43         <= 50, fine
+ 2 unrelated turns (7 + 8 words) ............ used = 43 + 15 = 58   > 50, over budget -> page out
page_out the oldest 4 turns .................. used = 15, 2 turns left, 1 archive entry
+ new question "user: DNS errors again ..." .. used = 15 + 11 = 26
page_in("DNS") appends the recalled entry .... used = 26 + 48 = 74
```

Why 48? The recalled turn is `"[recalled: db-connection-incident] "` (2 words) plus the 4 archived turns joined with `" | "` (the 43 words, plus 3 separator marks that count as words): 2 + 43 + 3 = 48. Paging brings everything back, so the window grows again. This demo stores turns **word for word**. Real systems usually store a short **summary** so that coming back is cheap; summaries are the compression idea in Problem 9.

#### `page_out` and `page_in`, step by step

```text
page_out(active_context, archive, topic="db-connection-incident", turn_count=4)
   paged_turns = active_context[:4]            # the oldest 4 turns
   del active_context[:4]                      # REMOVED from the caller's own list
   archive.append({"topic": ..., "text": "turn 1 | turn 2 | turn 3 | turn 4"})

page_in(active_context, archive, query="DNS")
   query_words = {"dns"}
   entry words = every word in the topic + the stored text, lowercased
   {"dns"} shares a word with the entry -> append "[recalled: db-connection-incident] ..." to the context
page_in(..., query="kubernetes") -> no shared word -> returns [], adds nothing
```

`del active_context[:4]` changes the very list the caller passed in, which is why the demo can print a smaller word count afterwards. The old version only copied a string into a dict, so the "context" never shrank.

### Who Decides to Page?

In this file a **fixed rule** decides: over the word budget, so page out; and the demo calls `page_in` by hand. In MemGPT-style systems such as Letta, the **model** decides, by calling memory tools during its turn (`archival_memory_insert` to archive something, `archival_memory_search` to look it up). The difference matters: a fixed rule is predictable but blind to what matters, and a model can keep the important lines and drop the rest, but it can also forget to call the tool.

### Where This Sits in Real Systems

- **Mem0** describes using the graph as a **ranking signal**, not as text for the prompt: it finds the entities in the query, matches them to the graph, boosts memories linked to them, and combines that with vector and keyword scores into one score per result. This file does it the plainer way, by walking the graph and handing the facts to the model as text.
- **Zep** keeps a graph where each fact carries the dates it was true, so "who was on call in March?" can still be answered. Our handoff throws the old edge away and keeps only a note, which is a small step in that direction but not the same thing.
- **Letta** is the paging idea above: a small window the model manages itself, with an archive it searches.

### What Is Real and What Is Simplified

| Part | Status |
|---|---|
| Semantic search, the 2-hop walk, write-back to both stores | **Real.** Live embeddings and Chroma, a real walk over stored facts. |
| The handoff | **Real replacement,** with the history kept as a note. |
| Entity and fact extraction | **Hand-written** (an alias table and one regex). A real system uses an LLM, which can be wrong. |
| The graph walk | **Takes everything nearby** and lets the model read it, instead of following one exact path. |
| Paging | **Real list operations,** triggered by a fixed rule, matching by shared words, storing text word for word. |
| The graph | **Rebuilt on every run,** not saved. File 7 shows saving it. |

### Gotchas

- **Chroma outlives your script.** Anything a run writes is still there next time, so reset at the start or runs contaminate each other.
- **The top 3 always come back,** even when none of them is close. A weak hit can still add an entity.
- **Alias matching has limits.** Whole-word matching fixes "queue", but the word `search` still maps to `search-service` even in "neural search model is slow". A real extractor reads the sentence.
- **A graph direction trap.** `Priya on_call_for payments-service` points *at* the service, so a walk that only follows outgoing edges never finds it. That is why `facts_touching` reads both directions.
- **Hubs make walks grow fast.** `eu-cache-layer` connects several things, so each extra hop can pull in many more facts. Keep `max_hops` small.
- **Semantic memory never updates.** The old "moved to Priya" line stays next to the new "Marcus" line forever. Only the graph is edited. Forgetting is Problem 9.
- **A replaced person still has a node.** Priya's node stays, with no edges.
- **The model can still pick the stale snippet,** even when told to trust the graph. It is a prompt, not a rule the code enforces.
- **A fixed budget can page out the wrong thing.** The oldest turns are not always the least important.
- **Keyword recall has no stemming.** `page_in("lookup")` does not find an entry that says "lookups".
- **Paging brings back everything it stored.** Recalling a whole thread can use more room than it saved, which is why systems page summaries.
- **The graph is not saved between runs here,** so a handoff only lasts for the run.
- **Write-back ids must be unique.** Using the collection's count as the id keeps them so; a fixed number overwrote an earlier message.

### Connection Forward

Both stores here only grow: every message is added and nothing is ever merged or dropped, and the archive keeps text word for word. Problem 9 deals with that growth: **augmentation** (store a memory together with questions that should find it), **compression** (merge many similar memories into one), and **forgetting** (drop what is no longer worth keeping).

---

## Theory 08a: Hybrid Memory, the Simple Version

**Used by:** [Problem 8a](#8a-hybrid-memory-the-simple-version)

### The Idea in One Sentence

**Hybrid memory** answers a message using two stores at once: a **semantic** store (Chroma) that finds old chat by *meaning*, and a **graph** that holds the *current* facts, and one chat call reads both.

### The Problem It Solves

Each store is blind where the other one sees:

```text
                         semantic memory (old chat)        graph (current facts)
"is this a known         YES: "cold snap in the EU,        NO: nobody wired "cold" to
 pattern?"               deploys flaking" is close          "timeouts", so there is no
                         in meaning                         edge to follow
"who is on call          UNSURE: it finds both "moved      YES: exactly one on_call_for
 right now?"             to Priya" and "Marcus is now      edge, replaced on every
                         on-call", with no dates            handoff
```

Use one store alone and one of these two questions goes wrong. Use both and each covers the other's gap.

### The Intuition

Think of an on-call manager with two things on the desk. One is a **pile of old chat logs**: big, searchable by "sounds like", partly out of date. The other is a **whiteboard** listing who owns what and who is on call today: small, exact, always current. A message comes in. The manager skims the pile for similar past incidents, reads the whiteboard for the services named, and writes one reply using both. Then they file the message on the pile, and if it says "Marcus is now on call", they wipe Priya's name off the whiteboard and write Marcus.

### What Each Store Actually Holds

**Chroma (semantic memory).** One row per snippet. The vector below is made-up numbers, only to show the shape. A real one has 1024 numbers.

```text
id        document (the text)                                     embedding (the meaning as numbers)
mem-2     "cold snap in the EU region again, deploys flaking"     [0.012, -0.044, 0.091, ..., 0.031]   1024 numbers
mem-3     "payments-service on-call rotation moved to Priya..."   [-0.067, 0.020, 0.008, ..., -0.015]  1024 numbers
...       (5 seed rows, plus one row per message written back)
```

You never search by the text. You search by the vector. The text only rides along so you can read what came back.

**The graph.** A plain dict. Each node has notes and outgoing edges:

```text
"payments-team":    {"observations": [], "edges": {"owns": ["payments-service"]}}
"Priya":            {"observations": [], "edges": {"on_call_for": ["payments-service"]}}
"payments-service": {"observations": ["had a 20-minute outage on 2026-08-01"],
                     "edges": {"runs_in": ["eu-cluster"]}}
"eu-cluster":       {"observations": [], "edges": {"uses": ["eu-cache-layer"]}}
"us-east-cluster":  {"observations": [], "edges": {"uses": ["eu-cache-layer"]}}
"billing-service":  {"observations": [], "edges": {"runs_in": ["apac-cluster"]}}
"eu-cache-layer", "apac-cluster": no notes, no edges of their own
```

```text
payments-team ──owns──► payments-service ──runs_in──► eu-cluster ──uses──► eu-cache-layer ◄──uses── us-east-cluster
Priya ──on_call_for──────────┘

billing-service ──runs_in──► apac-cluster              (connected to nothing above)
```

### How the Score and the Walk Work

There are two small ideas here: how Chroma scores a snippet, and how far the graph walk reaches.

#### Search score: how alike are two texts?

Two texts mean similar things when their vectors point in a similar direction. Cosine similarity measures that: 1 means the same direction, 0 means unrelated. Every vector here has length 1, so the score is just "multiply the matching numbers and add them up". Chroma returns a **distance**, which is `1 - similarity` because the collection was made with `{"hnsw:space": "cosine"}`. The file prints `1 - distance` to get the similarity back.

A dry run with 2 numbers per vector instead of 1024. The search is `[0.6, 0.8]`, snippet A is `[0.8, 0.6]` and snippet B is `[-0.8, 0.6]`:

```text
                     snippet A = [0.8, 0.6]            snippet B = [-0.8, 0.6]
multiply and add     0.6x0.8 + 0.8x0.6 = 0.96          0.6x(-0.8) + 0.8x0.6 = 0.00
similarity           0.96                              0.00
Chroma's distance    1 - 0.96 = 0.04                   1 - 0.00 = 1.00
the file prints      similarity=0.960                  similarity=0.000
```

Chroma sorts by distance, smallest first, so A comes back first. With `n_results=3` you always get 3 rows, even when the third one is a weak match.

#### How far the graph walk reaches

Start from the entities named in the message. Expand each one: take every fact touching it. The other end of each fact is a new node. Expand those on the next round. Each round is one **hop**, and `max_hops` says how many rounds to do. The nodes found on the last round are collected but never expanded.

Dry run from `eu-cluster`:

```text
round 1   expand: eu-cluster
          facts touching it:  eu-cluster uses eu-cache-layer           NEW
                              payments-service runs_in eu-cluster      NEW
          new nodes: eu-cache-layer, payments-service

round 2   expand: eu-cache-layer, payments-service
          eu-cache-layer:    eu-cluster uses eu-cache-layer              already in the list
                             us-east-cluster uses eu-cache-layer         NEW
          payments-service:  note "had a 20-minute outage on 2026-08-01" NEW
                             payments-service runs_in eu-cluster         already in the list
                             payments-team owns payments-service         NEW
                             Priya on_call_for payments-service          NEW
          new nodes: us-east-cluster, payments-team, Priya   (never expanded: max_hops=2)

result    6 lines.  max_hops=1 would give only the first 2.
```

The graph has 7 lines in total (6 edges and 1 note). The walk returns 6 and leaves out `billing-service runs_in apac-cluster`, because no path leads there. In a graph with thousands of nodes, the hop limit is what keeps the prompt small.

### The Five Steps: What Goes In, What Comes Out

Message 1, `"deploy to the EU cluster is timing out again, third time this month."`:

| Step | Input | Output |
|---|---|---|
| 1. Search | `QUERY_INSTRUCTION + message` → 1 vector, then `collection.query(..., n_results=3)` | `hits`: 3 snippet texts, best first, such as "cold snap in the EU region again..." |
| 2. Entities | the message and the 3 hits, joined into one string | `entities`, e.g. `['eu-cluster', 'us-east-cluster', 'payments-service']` |
| 3. Graph | `entities`, `max_hops=2` | `facts`: the 6 lines above |
| 4. Chat | system prompt = hits + facts + "trust the graph"; user = message | `answer`: one short reply (the only Gemini call) |
| 5. Write back | the message, embedded **plain** | a new Chroma row `mem-live-6`; the graph changes only on a handoff |

Steps 1 to 3 run locally. Step 4 is the only call that leaves your machine. Step 2 reads the hits as well as the message, because an old snippet can name something the message did not. "EU cluster shares a caching layer with the US-East cluster" brings in `us-east-cluster` even though the message never says "US".

### Why the Search Gets an Instruction and the Stored Text Does Not

Qwen3 embedding was trained on pairs of (search text, matching stored text), with the search side labelled by an instruction. Doing the same thing at run time gives the numbers the model was trained to compare:

```text
step 1, searching:   "Instruct: Given a chat message, retrieve relevant past chat messages\nQuery:Marcus is now on-call ..."
step 5, storing:     "Marcus is now on-call for payments-service."
```

This is also why each message costs 2 embedding requests: the same text has to be embedded once each way. Qwen's model card reports about 1 to 5% worse retrieval without the instruction. This file has not measured that.

### The Handoff: Why the Graph Wins

After message 2, the two stores look like this:

```text
CHROMA (only ever added to)                              GRAPH (edited)
  mem-3      "...on-call rotation moved to Priya..."       Marcus --on_call_for--> payments-service
  mem-live-7 "Marcus is now on-call for payments-service." Priya: edges {"on_call_for": []}
                                                           payments-service note: "on-call changed: Priya -> Marcus"
```

For message 3, Chroma can return both snippets, and `Priya` can even become an entity through `mem-3`. But the walk finds no edge from her, so the only on-call fact in the prompt is Marcus. If the handoff had only *added* Marcus's edge, the graph would list two people on call, and it would be no better than the chat.

### Gotchas

- **The query and the stored copy are embedded differently.** Embedding the stored message with the instruction in front can make later searches worse, and nothing errors.
- **Chroma outlives the script.** Rows written by one run are still there next run. That is why `reset_semantic_memory` deletes the collection first.
- **Top 3 always returns 3.** A weak third hit can still add an entity, and through it, extra facts.
- **Direction matters in the graph.** `Priya on_call_for payments-service` is stored on Priya. A walk that only reads a node's own edges never finds it from `payments-service`. `facts_touching` reads both directions.
- **"Trust the graph" is a prompt, not code.** The model can still repeat the stale snippet.
- **Extraction is hand-written.** An alias missing from `ENTITY_ALIASES`, or a handoff phrased differently ("Marcus took over on-call"), is silently missed.

### Connection Forward

[Problem 8](#8-hybrid-semantic--graph-memory-plus-os-inspired-paging) is the same workflow with the extras: switchable providers, a prefix table for several embedding models, hop numbers on each fact, and a paging demo that manages the model's small context window. [Problem 9](#9-memory-augmentation-compression-and-forgetting) deals with what this file ignores: Chroma only grows, and nothing is ever merged or forgotten.

---

## Theory 09: Keeping a Memory Store Healthy

**Used by:** [Problem 9](#9-memory-augmentation-compression-and-forgetting)

### The Idea in One Sentence

A memory store needs upkeep: **augmentation** adds extra rows so a memory can be found by the questions people will really ask, **compression** replaces many near-copies with one summary, and **forgetting** deletes memories that are no longer true, unless a retention rule says they must be kept.

### The Problem It Solves

An agent writes a memory every time something happens, and it never stops. After a while the store has three problems, and you can see each one in a search:

| Problem | What the search shows (real run) | Fix |
|---|---|---|
| Wording gap | "how long was payments down?" ranks an **ownership** note above the **incident** note, because the incident says "returned 500s for 12 minutes", not "down" | Augmentation |
| Crowding | "how have deploys been going lately?" returns three single deploy notes, each one fragment of the same story | Compression |
| Out of date | "who is on call right now?" ranks Priya's **March** shift above Marcus's current one | Forgetting |

### The Intuition

Think of a card catalogue in a library.

- **Augmentation** is writing extra cards for one book under the other names people search for ("how long was payments down?", "3am payments incident"), each saying "see inc-1". The original stays as it was.
- **Compression** is noticing 12 cards that all say "deploy #N went fine" and replacing them with one card: "12 deploys, all fine, 3m12s to 5m47s".
- **Forgetting** is pulling the card for last March's on-call rota. Some cards, such as billing records, must stay for years by law, even when nobody needs them.

```text
STORE ROWS                                         after AUGMENT   after COMPRESS   after FORGET
deploy-241 ... deploy-252   (12 near-copies)       same            1 summary row    same
inc-1  "bad config push"                           + 3 rows -> inc-1  same           same
inc-2, inc-3                (different incidents)   same            same (not merged) same
oncall-1 (valid_until March), owner-1 (superseded)  same            same             DELETED
oncall-2, owner-2                                   same            same             same
audit-1 (stale, keep_until 2033)                    same            same             KEPT
rows                         20                      23              12               10
```

### Augmentation: Why Extra Rows Help

A memory is found by its own row **or** by any question row that points at it, whichever is closest to the search. The best row counts. More rows can only add more chances to match, so adding them never lowers a memory's score. That is the `seen_memory_ids` loop in `search_memories`: rows are walked best first, so the first row seen for a memory is its best.

A dry run with 2 numbers per vector. Each score is the two vectors multiplied number by number and added up (every vector has length 1):

```text
search                = [0.6, 0.8]
rival note            = [0.0, 1.0]    0.6x0.0 + 0.8x1.0 = 0.80   <- wins before
inc-1 own row         = [1.0, 0.0]    0.6x1.0 + 0.8x0.0 = 0.60
question row -> inc-1 = [0.8, 0.6]    0.6x0.8 + 0.8x0.6 = 0.96

before:  inc-1 scores 0.60 (its own row only)           rival 0.80   the rival wins
after:   inc-1 scores 0.96 (its best row, the question) rival 0.80   inc-1 wins
```

In the real run, "How long was the payments-service down?" scored 0.834 against the search "how long was payments down?", above the ownership note's 0.644, so `inc-1` moved to first place. The note itself still scores 0.629.

**A question only helps if it lands closer to the search than the note does.** For the search "any outages caused by configuration changes?", the same three questions scored 0.482, 0.492 and 0.514, all below the note's own 0.568, so nothing changed. The questions are the chat model's guess at what people will ask, and a guess can miss.

**Why the questions are stored plain.** Qwen3 embedding puts its instruction only on the *search* side. The generated questions are stored rows, so they are embedded plain, like every other stored text. They are written as questions so their wording is close to future searches. That is the whole trick.

### Compression: k-means, Written by Hand

k-means finds groups of similar memories. Put a few centre points among the vectors. Give each memory to its nearest centre. Move each centre to the middle of its memories. Repeat until no memory changes group. Memories that say nearly the same thing sit close together, so they end up in one group.

The steps, as the code does them:
- **Start:** centre 1 is vector 0. Each next centre is the vector least similar to every centre picked so far, so the centres start far apart.
- **Repeat, step 1:** give each vector the label of its most similar centre.
- **Repeat, step 2:** move each centre to the average of its vectors, and scale it back to length 1.
- **Stop** when no label changes.

A dry run: 4 points, 2 groups.

```text
a = [1.0, 0.0]   b = [0.8, 0.6]   c = [0.0, 1.0]   d = [0.6, 0.8]

START     centre A = a.  Similarity to A: b 0.8, c 0.0, d 0.6.  Lowest is c, so centre C = c.

ROUND 1   b: b.A = 0.8   b.C = 0.6  -> A        d: d.A = 0.6   d.C = 0.8  -> C
          move A: average of a, b = [0.9, 0.3], scaled to length 1  -> A = [0.949, 0.316]
          move C: average of c, d = [0.3, 0.9], scaled to length 1  -> C = [0.316, 0.949]

ROUND 2   b: 0.949 vs 0.822 -> A        (nobody changes group)
          stop: no label changed

TIGHTNESS  a.A = 0.949,  b.A = 0.949   -> lowest similarity to centre = 0.949
```

#### k-means always returns the number of groups you ask for

k-means never says "these don't belong together". It always fills exactly the number of groups you ask for. Measured on the 20 real memories:

```text
3 groups   deploys + inc-2 + inc-3 land in ONE group (lowest similarity 0.608)  -> two incidents mixed in
4 groups   deploys alone (0.945) | on-call + owners (0.820) | audit (1.000) | 3 incidents (0.850)
5 groups   like 4, but on-call + owners split into two pairs
```

That is why merging has **two** extra checks after k-means:

```text
merge a group only if   size >= 4   AND   lowest similarity to centre >= 0.90
deploys      12 rows, 0.945   -> MERGE
incidents     3 rows, 0.850   -> keep   (same topic, different events)
on-call       4 rows, 0.820   -> keep
```

With 3 groups the mixed group's lowest similarity is 0.608, so the bar refuses to merge it. A bad number of groups loses the compression, but it never wrongly merges different incidents.

#### Checking that the summary kept the numbers

A summary can quietly drop exactly the numbers that mattered. `key_numbers` works out in Python what the summary must still contain:

```text
count          12
durations      3m12s = 192 s (shortest)   ...   5m47s = 347 s (longest)
must contain   ['12', '3m12s', '5m47s']
```

It compares in seconds, because comparing the strings would rank "10m01s" below "3m12s". A summary such as "Many deploys succeeded with no rollbacks." fails all three checks. The file prints the failure, so you can see what was lost. It does not fix it.

### Forgetting: Stale, Unless a Rule Says Keep

```text
for each row:
   is_stale?  (superseded_by set)  or  (valid_until < today)
        │ no  -> keep
        │ yes
   must_keep? (keep_until >= today)
        │ yes -> KEEP   audit-1: the record is stale, but the law says keep it until 2033
        │ no  -> DELETE oncall-1 (valid until 2026-03-10), owner-1 (replaced by owner-2)
then delete any question rows whose points_to was deleted
```

**Why `<` works on dates here.** `"2026-03-10" < "2026-09-22"` compares character by character. The first difference is `3` against `9`, which is the month, so string order is date order. That only holds when every date is written `YYYY-MM-DD` with zeros (`2026-09-05`, not `2026-9-5`).

**Why retention wins.** In the run, `audit-1` is stale (the double charge was settled in March) and nobody searches for it, but payment records must be kept for years. A retention rule is a hard limit that comes from law, not from search quality, so it is checked last and overrides everything else.

### Gotchas

- **Augmentation is a bet, not a guarantee.** It only helps when one generated question is closer to the real search than the note is. Asking for questions that use different words from the note (synonyms, the cause, the effect) makes a hit more likely. Check it by searching before and after, as this file does.
- **The question rows must point somewhere.** If a memory is deleted or merged, its question rows have to go too, or a search would return a memory that no longer exists. Both `compress_store` and `forget_stale` remove them.
- **Store the questions plain, search with the instruction.** Embedding stored rows with the search instruction mixes up the two roles the model was trained on. Search can get worse, and nothing shows an error.
- **k-means is not a "same thing" detector.** It always returns the number of groups you ask for. The size and tightness bar is what decides "these are copies".
- **The 0.90 bar was picked by looking at this data.** Deploys are at 0.945 and the incidents at 0.850. Another embedding model would need its bar checked again.
- **Compressing loses detail on purpose.** After the merge, "how long did deploy #247 take?" can no longer be answered. Compress repetitive things, not records you may need one by one.
- **Forgetting by date needs dates.** A memory written without `valid_until` never expires. Real systems also look at how old a memory is and how often it is retrieved.
- **The summary is checked, not trusted.** The number check prints `False` when Gemini drops a number, and it is up to you (or a retry) to act on it.

### Connection Forward

This finishes the memory half of the chapter. Problem 7 stored facts as a graph, Problem 8 used the graph together with semantic search, and Problem 9 keeps the semantic store useful as it grows. The on-call handoff in Problem 8 was a small case of forgetting: one graph edge replaced by a newer one. Here the same idea is applied to whole memories, with dates and retention rules.
