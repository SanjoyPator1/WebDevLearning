# Advanced RAG

B02's RAG chapter and B01's embedding work both ended at the same place: embed
your chunks once, embed the query, take the top-k by cosine similarity, and
hand those chunks to the LLM. That pipeline is the *minimum viable* version of
retrieval-augmented generation, and it is also where most production RAG
systems start failing — not because the idea is wrong, but because "one
ranking signal, one retrieval pass, one fixed k" is a much narrower assumption
than it looks. This note builds a small 14-document corpus drawn from this
repo's own material (tokenization from B01, RLHF/DPO/GANs from B02,
LangGraph/MCP internals from B03 Topics 1-3) and uses it to *empirically*
surface two concrete ways naive RAG breaks, then fixes each one with a
standard technique: hybrid search, cross-encoder reranking, query
transformation, agentic retrieval, and GraphRAG.

---

## Table of Contents

1. [Where This Sits](#where-this-sits)
2. [The Limits of Naive RAG](#1-the-limits-of-naive-rag)
3. [Hybrid Search — BM25 + Dense + RRF](#2-hybrid-search--bm25--dense--rrf)
4. [Cross-Encoder Reranking](#3-cross-encoder-reranking)
5. [Query Transformation — Multi-Query & HyDE](#4-query-transformation--multi-query--hyde)
6. [Agentic RAG](#5-agentic-rag)
7. [GraphRAG](#6-graphrag)
8. [Putting It All Together](#putting-it-all-together)
9. [Summary & Connection Forward](#summary--connection-forward)

---

## Where This Sits

```
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 4 — AI Agent Patterns & Frameworks                      │
│  ReAct: agent <-> tool, in a Thought/Action/Observation loop       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  treat *retrieval* as one of those tools,
                              │  and ask: how good is the retriever itself?
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 5 — Advanced RAG  (THIS NOTE)                           │
│  naive RAG's failure modes -> hybrid search -> reranking ->        │
│  query transformation -> agentic RAG -> GraphRAG                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 6 — Vector Databases                                    │
│  how dense_search / hybrid search are actually implemented at      │
│  scale: HNSW indexing, metadata filtering, native hybrid queries    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. The Limits of Naive RAG

**Summary**: Naive RAG embeds every document chunk once with a *bi-encoder*
(a model that maps text to a fixed-size vector with no knowledge of the
query), embeds the user's query the same way, and ranks chunks by cosine
similarity. It is cheap and usually "good enough" — but it can fail in ways
that are invisible until you test it on the right query.

**The problem it solves (and where it stops solving it)**: Before embeddings,
search meant keyword matching — fast, exact, but blind to synonyms and
paraphrasing ("car" vs "automobile"). Dense embeddings fixed that by mapping
semantically similar text to nearby vectors regardless of exact wording. But
"semantically similar" is a *learned, approximate* notion, and two things fall
through the cracks: exact tokens that carry little independent semantic weight
(numbers, identifiers, rare proper nouns), and questions whose full answer is
spread across more than one chunk.

**The intuition**: Imagine asking a librarian "which book has exactly 50,257
words in its glossary?" A librarian who only remembers what each book is
*about* (tokenization, search algorithms, fine-tuning...) might point you to
the wrong book if two books are about similar-sounding topics — the specific
number "50,257" doesn't change what a book is "about" enough to shift their
mental map. A librarian who can *also* search the literal text for "50,257"
would find the right book instantly. Dense embeddings are the first
librarian; keyword search (Section 2) is the second.

**The math**: A bi-encoder maps the query $q$ and each document $d_i$ to
vectors $\mathbf{q}, \mathbf{d}_i \in \mathbb{R}^{384}$ (for
`all-MiniLM-L6-v2`). Ranking uses cosine similarity:

$$\text{score}(q, d_i) = \cos(\mathbf{q}, \mathbf{d}_i) = \frac{\mathbf{q} \cdot \mathbf{d}_i}{\|\mathbf{q}\| \, \|\mathbf{d}_i\|}$$

When every vector is **L2-normalized** ($\|\mathbf{v}\| = 1$, which
`encode(..., normalize_embeddings=True)` guarantees), this reduces to a plain
dot product: $\text{score}(q, d_i) = \mathbf{q} \cdot \mathbf{d}_i$. Naive RAG
then returns the $k$ documents with the highest score.

**Dry-run (toy 2D vectors)**: Suppose $d_k = 2$ and we have two documents,
$\mathbf{d}_1 = [1, 0]$ (points "east") and $\mathbf{d}_2 = [0, 1]$ (points
"north"), both already unit length. A query $\mathbf{q} = [0.8, 0.6]$ (also
unit length, since $0.8^2 + 0.6^2 = 1$) points mostly east with a bit of
north.

```
Step 1: score(q, d1) = q . d1 = (0.8)(1) + (0.6)(0) = 0.8
Step 2: score(q, d2) = q . d2 = (0.8)(0) + (0.6)(1) = 0.6
Step 3: 0.8 > 0.6, so d1 ranks first.
```

This is exactly what `doc_embeddings @ query_embedding` computes in the
notebook, just with 384 dimensions instead of 2 — every dimension contributes
one multiply-and-add to the final score.

**Dry-run (real corpus, failure mode 1 — exact terms get diluted)**: The
notebook's corpus includes `gpt2_tokenizer` ("GPT-2 uses a BPE tokenizer with
a vocabulary of 50,257 tokens...") and `bm25_doc` ("BM25 is a sparse,
keyword-based ranking function built on term frequency and inverse document
frequency"). For the query *"Which model has a vocabulary size of exactly
50257 tokens?"*, dense search returns:

```
0.401  bm25_doc           BM25 is a sparse, keyword-based ranking function...
0.363  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens...
```

`bm25_doc` ranks **first**, even though it has nothing to do with GPT-2. Both
documents talk about "tokens" and "vocabulary" in a generic statistical sense,
so their *embeddings* land close together — the embedding model has no special
representation for the literal digit string `50257`; it's just a number among
many. A bag-of-words method, by contrast, would notice instantly that `50257`
appears verbatim in exactly one document.

**Dry-run (real corpus, failure mode 2 — multi-hop questions span chunks)**:
For the query *"What tokenizer does GPT-2 use, and what algorithm does that
tokenizer implement?"*, dense search returns:

```
0.726  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens...
0.404  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm...
```

Here the *ranking* is correct — both relevant documents are at the top. The
problem is `k`. The question has two parts ("which tokenizer" and "what does
that tokenizer's algorithm do"), and a naive pipeline with `k=1` retrieves only
`gpt2_tokenizer`, which answers the first part but says nothing about what BPE
actually *does* — that explanation lives in `bpe`, a separate chunk.

**The gotcha**: It's tempting to "fix" failure mode 2 by just increasing `k`.
That helps here, but doesn't generalize — for a corpus with thousands of
chunks, a question needing 2 specific chunks out of 5000 might need `k` in the
hundreds before both appear, at which point most of the LLM's context window
is irrelevant filler. Section 4's query transformation is a more targeted fix.

**Connection forward**: Both failures share the same root cause — one ranking
signal, one retrieval pass, one fixed $k$. Section 2 adds a second ranking
signal (fixing failure mode 1). Section 4 changes what gets sent to the
retriever in the first place (fixing failure mode 2).

---

## 2. Hybrid Search — BM25 + Dense + RRF

**Summary**: Hybrid search runs **two** retrievers — a sparse, keyword-based
one (BM25) and the dense bi-encoder from Section 1 — and merges their rankings
with **Reciprocal Rank Fusion (RRF)**, a simple formula that combines rank
*positions* rather than raw scores.

**The problem it solves**: Section 1 showed dense embeddings missing an exact
numeric match. The natural fix is to add back a keyword-based signal — but
dense and BM25 scores live on completely different, incomparable scales
(cosine similarity is bounded in $[-1, 1]$; BM25 is an unbounded sum that
depends on corpus statistics). You can't just average them. RRF sidesteps this
by only ever looking at *where* a document ranks in each list, never *how
high* its score is.

**The intuition**: Imagine two critics ranking the same 10 restaurants. Critic
A (dense) is great at "vibe" but sometimes misses a restaurant's signature
dish. Critic B (BM25) is great at spotting that signature dish by name but
doesn't care about ambiance. If a restaurant is critic B's #1 *and* critic A's
#2, it's probably excellent overall — even if you can't directly compare "B's
score of 9.4" to "A's score of 0.81". RRF formalizes "give weight to a high
position in *either* list, and extra weight if it's high in *both*."

**The math — BM25**: For a query $q$ with terms $t \in q$, BM25 scores a
document $d$ as

$$\text{BM25}(q, d) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, d)\,(k_1 + 1)}{f(t, d) + k_1 \left(1 - b + b \cdot \dfrac{|d|}{\text{avgdl}}\right)}$$

where $f(t, d)$ is how many times term $t$ appears in $d$, $|d|$ is $d$'s
length in tokens, $\text{avgdl}$ is the average document length across the
whole corpus, and $\text{IDF}(t)$ (inverse document frequency) is large when
$t$ is rare across the corpus and small (even negative, in some formulations)
when $t$ is common. `rank_bm25`'s `BM25Okapi` defaults to $k_1 = 1.5$ (controls
how quickly extra occurrences of $t$ stop adding score — *term-frequency
saturation*) and $b = 0.75$ (controls how much longer-than-average documents
are penalized).

**Dry-run — BM25 (toy 2-document corpus)**: Let $d_1 = $ "the cat sat" (3
tokens) and $d_2 = $ "the cat sat on the mat" (6 tokens), so
$\text{avgdl} = (3+6)/2 = 4.5$. Query: "cat mat" (2 documents total, so
$N = 2$).

```
IDF(cat): df(cat) = 2 (appears in both docs)
  IDF(cat) = ln((N - df + 0.5)/(df + 0.5) + 1) = ln((2-2+0.5)/(2+0.5) + 1)
           = ln(0.5/2.5 + 1) = ln(1.2) ~= 0.182

IDF(mat): df(mat) = 1 (appears only in d2)
  IDF(mat) = ln((2-1+0.5)/(1+0.5) + 1) = ln(1.5/1.5 + 1) = ln(2) ~= 0.693

Score(d1, "cat mat"):
  "cat": f=1, |d1|=3
    term = 0.182 * (1 * 2.5) / (1 + 1.5*(1 - 0.75 + 0.75*3/4.5))
         = 0.182 * 2.5 / (1 + 1.5*0.75) = 0.455 / 2.125 ~= 0.214
  "mat": f=0 -> term = 0
  Score(d1) ~= 0.214

Score(d2, "cat mat"):
  "cat": f=1, |d2|=6
    term = 0.182 * 2.5 / (1 + 1.5*(1 - 0.75 + 0.75*6/4.5))
         = 0.455 / (1 + 1.5*1.25) = 0.455 / 2.875 ~= 0.158
  "mat": f=1, |d2|=6
    term = 0.693 * 2.5 / 2.875 = 1.7325 / 2.875 ~= 0.603
  Score(d2) ~= 0.158 + 0.603 = 0.761
```

$d_2$ scores higher overall (0.761 vs 0.214), even though $d_1$ is shorter and
"cat" appears in both — because $d_2$ is the *only* document containing the
rarer query term "mat", and IDF rewards that heavily. This is precisely the
mechanism that lets BM25 find `gpt2_tokenizer` via the rare token `50257` in
the real corpus:

```
7.426  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens...
2.391  rlhf               Reinforcement Learning from Human Feedback (RLHF)...
```

`gpt2_tokenizer` wins by a wide margin, and `bm25_doc` (dense's incorrect #1)
doesn't even appear in the top 5.

**The math — Reciprocal Rank Fusion**: For each ranker $r$ (dense, BM25),
let $\text{rank}_r(d) \in \{1, 2, 3, \dots\}$ be document $d$'s 1-indexed
position in that ranker's full ranking (1 = best). RRF's combined score is

$$\text{RRF}(d) = \sum_{r} \frac{1}{k_{\text{rrf}} + \text{rank}_r(d)}$$

with $k_{\text{rrf}}$ a constant (commonly 60) that flattens the curve — the
difference between rank 1 and rank 2 contributes much less to the *sum* than
it would to the raw rank, so one ranker placing a document at rank 1 doesn't
automatically dominate the other ranker placing it at rank 50.

**Dry-run — RRF (real corpus, $k_{\text{rrf}} = 60$)**: For the query *"Which
model has a vocabulary size of exactly 50257 tokens?"*, the notebook computes:

| document | dense_rank | bm25_rank | RRF score |
|---|---|---|---|
| `gpt2_tokenizer` | 2 | 1 | $\frac{1}{62} + \frac{1}{61} = 0.01613 + 0.01639 = 0.03252$ |
| `self_attention` | 3 | 3 | $\frac{1}{63} + \frac{1}{63} = 0.01587 + 0.01587 = 0.03175$ |
| `rlhf` | 5 | 2 | $\frac{1}{65} + \frac{1}{62} = 0.01538 + 0.01613 = 0.03151$ |
| `bm25_doc` | 1 | 11 | $\frac{1}{61} + \frac{1}{71} = 0.01639 + 0.01408 = 0.03048$ |
| `bpe` | 6 | 7 | $\frac{1}{66} + \frac{1}{67} = 0.01515 + 0.01493 = 0.03008$ |

`gpt2_tokenizer` is now ranked **first overall** — RRF recovered it using
BM25's rank-1 placement, even though dense alone ranked it 2nd (behind
`bm25_doc`, which RRF correctly demotes using its poor BM25 rank of 11).
**Hybrid search fixed failure mode 1.**

**The gotcha**: Look at the RRF *scores* themselves: 0.03252, 0.03175,
0.03151, 0.03048 — all within about 0.002 of each other. RRF gets the
*ordering* right, but the scores don't express much confidence; the top
candidate isn't obviously "much better" than the next three. Section 3 adds a
second pass that produces a far more decisive signal.

---

## 3. Cross-Encoder Reranking

**Summary**: A **cross-encoder** takes a `(query, document)` pair as a single
joint input and produces one relevance score, in contrast to the **bi-encoder**
used everywhere so far, which encodes the query and each document
*independently*. Cross-encoders are far more accurate but too slow to run over
an entire corpus, so they're used to **rerank** a short candidate list (e.g.
RRF's top-5) rather than to search the whole corpus.

**The problem it solves**: A bi-encoder must compress all of a document's
meaning into one fixed vector *before* it ever sees the query — it has to
"guess" in advance which aspects of the document might matter. A cross-encoder
gets to look at the query and document *together*, so it can directly check
"does this specific document answer this specific question" instead of
"are these two independently-computed summaries similar".

**The intuition**: A bi-encoder is like asking two people to each write a
one-paragraph summary of what they know — one summarizing the question, one
summarizing a document — and then comparing the two summaries for overlap. A
cross-encoder is like handing one person *both* the question and the document
together and asking "on a scale, how well does this document answer this
question?" The second approach is obviously more accurate (the person can
cross-reference details directly) but you can't ask that person to do it for
every document in your library for every query — too slow. So: use the cheap
two-summary approach (bi-encoder + BM25 + RRF) to get a shortlist, then spend
the expensive joint read (cross-encoder) only on that shortlist.

**The math**: Internally, a cross-encoder concatenates the query and document
into one sequence — `[CLS] query [SEP] document [SEP]` — and runs it through a
transformer (Topic 3 from B01: full self-attention, every token attends to
every other token, query tokens included). The `[CLS]` token's final hidden
state is passed through a small classification head to produce a single
scalar **logit** (an unbounded real number, *not* a probability or a cosine
similarity — it has no fixed range and is only meaningful *relative to other
logits from the same model on the same query*).

**Dry-run (real corpus)**: Reranking RRF's top-5 candidates for *"Which model
has a vocabulary size of exactly 50257 tokens?"* with
`cross-encoder/ms-marco-MiniLM-L-6-v2`:

```
  1.250  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens...
-10.090  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm...
-10.205  self_attention     Self-attention computes a weighted sum over all tokens...
-10.577  bm25_doc           BM25 is a sparse, keyword-based ranking function...
-10.804  rlhf               Reinforcement Learning from Human Feedback (RLHF)...
```

Compare this to RRF's scores (0.03252, 0.03175, 0.03151, 0.03048, 0.03008) —
all clustered within 0.002. The cross-encoder gives `gpt2_tokenizer` a score
around **+1.25** while everything else scores **below -10**: a gap of more
than 11, trivially thresholdable. Because the cross-encoder reads the query
and document *together*, it can directly notice that the literal substring
`50257` appears in both — something neither the bi-encoder's independent
embeddings nor BM25's bag-of-words score represents this cleanly.

**The gotcha**: A cross-encoder can only rerank documents that are *already in
its candidate list* — it cannot "find" a document that retrieval missed
entirely. If the true answer wasn't in RRF's top-5 at all, no amount of
reranking recovers it. This is why retrieval *recall* (Sections 1-2: did the
right document make it into the candidate list at all?) and reranking
*precision* (Section 3: of the candidates, which is best?) are complementary,
not substitutes.

---

## 4. Query Transformation — Multi-Query & HyDE

**Summary**: Sections 2-3 changed *how documents are ranked* for a fixed
query. This section changes **the query itself** before retrieval runs, using
two techniques: **multi-query decomposition** (split one question into several
focused sub-questions) and **HyDE** — Hypothetical Document Embeddings (embed
a hypothetical *answer* instead of the question).

**The problem it solves**: Multi-query directly targets failure mode 2 from
Section 1 (multi-hop questions spanning chunks) without resorting to a large
`k`. HyDE targets a subtler issue: corpus documents are written in "answer"
register (definitions, statements of fact), while user queries are written in
"question" register ("why does X...", "how do I..."). Embedding similarity is
sensitive to this register gap even when the topic matches.

**The intuition (multi-query)**: If a teacher asks "what tokenizer does GPT-2
use, and what algorithm does that tokenizer implement?", a good research
assistant doesn't try to find one source that answers both halves — they split
it into "look up GPT-2's tokenizer" and "look up how that tokenizer's
algorithm works", search for each separately, then combine the findings.

**The intuition (HyDE)**: Imagine searching a library's card catalog (which
contains book *summaries*, written formally) using your own *question*,
phrased casually. A casual question and a formal summary about the same topic
might use different enough wording that the catalog's similarity search
underperforms. HyDE's trick: first write your *own* one-paragraph "summary"
that *would* answer your question, in the same formal register as the catalog
— then search the catalog using *that* paragraph instead of your original
question. Even if your hand-written summary isn't perfectly accurate, its
*phrasing* is now closer to what the catalog actually contains.

**Dry-run — multi-query (real corpus)**: For the multi-hop question from
Section 1, an LLM (here, a scripted `GenericFakeChatModel`) decomposes it:

```
Original: What tokenizer does GPT-2 use, and what algorithm does that
          tokenizer implement?

Sub-queries:
  - What tokenizer does GPT-2 use?
  - What algorithm does the BPE tokenizer implement?

Retrieval per sub-query (top-1 each):
  'What tokenizer does GPT-2 use?'          -> gpt2_tokenizer (0.744)
  'What algorithm does the BPE tokenizer
   implement?'                              -> bpe (0.661)

Single-query top-1 retrieval would only return: {'gpt2_tokenizer'}
Multi-query retrieval returns:                  {'gpt2_tokenizer', 'bpe'}
```

Each sub-question retrieves *its own* best match at `k=1`; the union covers
both documents needed for a complete answer. **Multi-query fixed failure mode
2** without increasing `k` for the original query at all.

**Dry-run — HyDE (real corpus)**: For the layperson question *"Why does
ChatGPT split words into pieces instead of using whole words?"*, direct
retrieval on the raw query gives:

```
0.318  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens...
0.299  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm...
```

`gpt2_tokenizer` edges out `bpe` — but the question is really asking about
*why subword tokenization exists*, which `bpe` (the algorithm definition)
answers more directly than `gpt2_tokenizer` (a fact about one specific model).
A scripted LLM writes a hypothetical answer:

> "Language models break text into smaller subword units rather than whole
> words because a fixed vocabulary cannot cover every possible word. Subword
> tokenization algorithms merge frequently occurring pairs of characters into
> larger tokens, producing an efficient vocabulary."

Embedding *this* passage instead of the original question gives:

```
0.384  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm...
0.372  bm25_doc           BM25 is a sparse, keyword-based ranking function...
0.332  self_attention     Self-attention computes a weighted sum over all tokens...
```

`bpe` moves to first place. The hypothetical passage — written in the same
"definitional" register as the corpus — pulled the more directly explanatory
document to the top. Neither ranking is "wrong"; HyDE simply closed the
phrasing gap between an informal question and formal documents.

**The gotcha**: HyDE's hypothetical document is generated by an LLM and is
**never shown to the user or checked for factual accuracy** — it exists only
to be embedded. If the LLM's hypothetical answer is *confidently wrong* in a
way that shifts its phrasing toward an unrelated part of the corpus, HyDE can
make retrieval *worse*. In practice HyDE works best for queries where the
*topic* is clear but the *phrasing* mismatch is the dominant problem — exactly
the situation in this dry-run.

---

## 5. Agentic RAG

**Summary**: Every retrieval pipeline so far runs **unconditionally, exactly
once, before generation**. Agentic RAG instead wraps the hybrid-search-plus-
rerank pipeline (Sections 2-3) as a `retrieve` **tool**, gives it to an LLM
inside the same ReAct-style loop from Topic 4
(`agent` → `tools_condition` → `tools` → `agent` → ... → `END`), and lets the
model decide *whether* to call it, and *how many times*.

**The problem it solves**: Multi-query (Section 4) requires deciding *up
front* how to decompose a question — a fixed, one-shot transformation. Agentic
RAG instead lets retrieval happen *interactively*: the model can retrieve once,
read the result, realize it needs more information, and retrieve again with a
*refined* query informed by what it just learned — directly addressing
multi-hop questions (failure mode 2) without a separate decomposition step,
and gracefully doing *zero* retrievals for questions that don't need any.

**The intuition**: This is exactly Topic 4's ReAct loop (Thought → Action →
Observation), with `retrieve` as one of the available actions alongside
whatever other tools the agent has. Nothing new is introduced *mechanically* —
the novelty is purely in treating "search my knowledge base" as just another
tool call, subject to the same "does the model think it needs this?"
reasoning as a calculator or a web search.

**Dry-run (real corpus, two-hop case)**: For the multi-hop query from Sections
1 and 4, a scripted agent makes **two** sequential tool calls:

```
HumanMessage  What tokenizer does GPT-2 use, and what algorithm does that
              tokenizer implement?
AIMessage     tool_call -> retrieve("What tokenizer does GPT-2 use?")
ToolMessage   GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens...
AIMessage     tool_call -> retrieve("What algorithm does the BPE tokenizer
              implement?")
ToolMessage   Byte Pair Encoding (BPE) is a subword tokenization algorithm
              that iteratively merges the most frequent pair of adjacent
              symbols into a new token.
AIMessage     GPT-2 uses a BPE tokenizer, and BPE works by iteratively
              merging the most frequent pair of adjacent symbols into a
              new token.
```

The second `retrieve` call's query — "What algorithm does the BPE tokenizer
implement?" — is informed by the *first* observation (which named "BPE" as the
tokenizer). A one-shot multi-query decomposition (Section 4) would have had to
guess this sub-question *before* seeing any results; the agent derives it
*from* the first result.

**The gotcha**: This flexibility costs determinism and latency — a
two-hop question now takes two LLM calls plus two retrievals instead of one of
each, and an LLM that's *too* eager to call `retrieve` can loop unnecessarily
(mitigated in practice with a `max_steps` cap, exactly as in Topic 4's ReAct
implementation).

---

## 6. GraphRAG

**Summary**: GraphRAG represents the corpus as a **knowledge graph** — nodes
are entities, edges are labeled relations, typically extracted from documents
by an LLM — and answers questions by **traversing** the graph rather than
ranking and retrieving chunks.

**The problem it solves**: Agentic RAG (Section 5) solves multi-hop questions
by letting the model *retrieve repeatedly*, stitching chunks together itself.
GraphRAG instead makes the relationships between facts **explicit and
structured** ahead of time, so a multi-hop question becomes a graph-traversal
query — no repeated retrieval, no risk of the model failing to "connect the
dots" between chunks it has retrieved.

**The intuition**: Chunk-based retrieval (every technique in Sections 1-5) is
like searching a pile of index cards, each with one fact written on it. Even
with perfect retrieval, you get back a *pile* of relevant cards — connecting
"card A says X uses Y" to "card B says Y implements Z" to answer "what does X
ultimately do?" is left to the reader (the LLM). GraphRAG instead pre-draws the
arrows between cards: "X --uses--> Y", "Y --implements--> Z" — turning "what
does X ultimately do?" into "follow the arrows from X".

**The math**: A knowledge graph is a directed graph $G = (V, E)$ where each
edge $(u, v) \in E$ carries a relation label $\rho(u, v)$. Answering a
$k$-hop question reduces to finding a path
$u = n_0 \to n_1 \to \dots \to n_k = v$ such that each edge $(n_{i-1}, n_i)$
exists in $E$, e.g. via shortest-path search.

**Dry-run (real corpus, 3-hop)**: The notebook encodes 9 triples, including:

```
("GPT-2", "uses", "BPE_tokenizer")
("BPE_tokenizer", "implements", "BPE_algorithm")
("BPE_algorithm", "merges", "frequent_symbol_pairs")
```

For *"What does GPT-2's tokenizer actually do under the hood?"*,
`nx.shortest_path` from `"GPT-2"` to `"frequent_symbol_pairs"` returns:

```
GPT-2 --uses--> BPE_tokenizer
BPE_tokenizer --implements--> BPE_algorithm
BPE_algorithm --merges--> frequent_symbol_pairs
```

No single chunk in the corpus contains this whole chain — `gpt2_tokenizer`
never mentions "merging frequent symbol pairs". The graph makes the 3-hop
connection explicit and traversable.

**Dry-run (real corpus, branching)**: The corpus also encodes:

```
("LangGraph", "has_component", "tools_condition")
("tools_condition", "routes_to", "tools_node")
("tools_condition", "routes_to", "END")
```

`tools_condition` has **two** outgoing `routes_to` edges — reflecting that
it's a *conditional* router (Topic 2/4: "route to `tools` if there are tool
calls, else route to `END`"). Querying both targets from `"LangGraph"` returns
two separate 2-hop paths:

```
Path to tools_node:
  LangGraph --has_component--> tools_condition
  tools_condition --routes_to--> tools_node

Path to END:
  LangGraph --has_component--> tools_condition
  tools_condition --routes_to--> END
```

**The gotcha**: GraphRAG's quality is entirely bounded by the **triple
extraction step** — if the LLM that builds the graph misses a relation, mislabels
it, or hallucinates one that doesn't exist in the source text, every downstream
traversal inherits that error *silently* (a missing edge just makes a path
"not exist", which looks identical to "this relationship genuinely isn't in
the corpus"). Building and maintaining the graph is also a substantial
upfront and ongoing cost compared to chunk-based retrieval, which only
requires re-embedding changed documents.

---

## Putting It All Together

```
Naive RAG:
  Query --[bi-encoder]--> dense top-k --------------------> [LLM + chunks] --> Answer
         (fails: exact terms diluted, multi-hop spans chunks)

Hybrid + Rerank:
  Query --+--[bi-encoder]--> dense top-N --+
          |                                 |--> [RRF] --> top-k --> [cross-encoder] --> top-m --> [LLM + chunks] --> Answer
          +--[BM25]---------> sparse top-N -+
         (fixes: exact-term recall + low-confidence margins)

Query Transformation:
  Query --[LLM: decompose / HyDE]--> {sub-queries | hypothetical doc} --> (hybrid + rerank, per query) --> [LLM + chunks] --> Answer
         (fixes: multi-hop coverage, question/document phrasing gap)

Agentic RAG:
       +-----------------------------------------------+
       |                                                 |
       v                                                 |
  [agent: LLM] --(tool call?)--> [retrieve: hybrid+rerank] --> Observation --+
       |
       (no tool call)
       |
       v
     Answer
         (fixes: multi-hop, decided at runtime, zero retrievals when unneeded)

GraphRAG:
  Query --[LLM: extract triples, offline]--> Knowledge Graph
  Query --[graph traversal]--> path of (entity --relation--> entity) --> [LLM + path] --> Answer
         (fixes: explicit multi-hop chains the embedding space doesn't expose)
```

| Stage | What changed | Failure it addresses |
|---|---|---|
| Naive RAG | dense embeddings, top-k | baseline |
| + Hybrid search (BM25 + RRF) | add a sparse, exact-term ranking signal | exact term/number matches diluted by dense embeddings |
| + Cross-encoder reranking | second pass with full query-document attention | narrow, low-confidence margins after fusion |
| + Multi-query | decompose the question before retrieving | multi-hop questions spanning several chunks |
| + HyDE | embed a hypothetical answer, not the raw question | question/document phrasing & register mismatch |
| Agentic RAG | LLM decides whether/how often to retrieve | multi-hop, decided at runtime |
| GraphRAG | traverse explicit entity-relation edges | multi-hop chains the embedding space doesn't expose |

Each row is a strict addition on top of the previous one. A production system
would typically run hybrid search + reranking as the *default* retriever for
every query, and reach for query transformation, agentic loops, or graph
traversal only for the query patterns that need them — each of those three
adds latency and/or upfront cost, so they're applied selectively, not
universally.

---

## Summary & Connection Forward

Naive RAG's two failure modes — exact terms diluted by dense embeddings, and
multi-hop questions spanning chunks — aren't bugs in any one component; they're
consequences of committing to *one ranking signal, one retrieval pass, and one
fixed k* before generation even starts. Every technique in this note relaxes
one of those three commitments: hybrid search adds a second ranking signal,
reranking adds a second *pass*, and multi-query/HyDE/agentic RAG/GraphRAG all,
in different ways, change what gets retrieved and how many times.

Topic 6 (Vector Databases) goes one level lower: `dense_search` and
`bm25_search` in this notebook are two separate Python data structures
(a NumPy matrix and a `BM25Okapi` index) searched independently and merged in
Python. Real vector databases implement **HNSW** indexing for sub-linear-time
approximate nearest-neighbor search at million-document scale, support
**metadata filtering** (e.g. "only search documents tagged `chapter: 3`"), and
increasingly support **native hybrid queries** — the BM25 + dense + RRF
pipeline from Section 2, but running as a single database query instead of two
separate searches glued together in application code.
