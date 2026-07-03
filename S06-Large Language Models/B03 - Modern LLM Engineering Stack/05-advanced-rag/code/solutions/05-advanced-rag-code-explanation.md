# Topic 5 — Advanced RAG: Code Explanation

This file walks through every cell of `05-advanced-rag.ipynb`, showing the
actual code and the actual output it produces — everything in this notebook
ran end-to-end (sections 1-4 use real local models from
`sentence-transformers`; sections 5-6 use scripted `GenericFakeChatModel`
responses, exactly like Topics 1-4).

For the *why* behind each technique (naive RAG's failure modes, BM25/RRF math,
bi-encoder vs cross-encoder, HyDE/multi-query, agentic RAG, GraphRAG), see
[`../../notes/05-advanced-rag.md`](../../notes/05-advanced-rag.md) and the
topic plan, [`../../../05-advanced-rag.md`](../../../05-advanced-rag.md). This
file stays close to the code.

---

## Table of Contents

- [1. The Limits of Naive RAG](#1-the-limits-of-naive-rag)
- [2. Hybrid Search — BM25 + Dense + RRF](#2-hybrid-search--bm25--dense--rrf)
- [3. Cross-Encoder Reranking](#3-cross-encoder-reranking)
- [4. Query Transformation — Multi-Query & HyDE](#4-query-transformation--multi-query--hyde)
- [5. Agentic RAG (Exercise)](#5-agentic-rag-exercise)
- [6. GraphRAG (Exercise)](#6-graphrag-exercise)
- [Putting It All Together](#putting-it-all-together)

---

## 1. The Limits of Naive RAG

```python
CORPUS = {
    "bpe": "Byte Pair Encoding (BPE) is a subword tokenization algorithm that iteratively merges the most frequent pair of adjacent symbols into a new token.",
    "gpt2_tokenizer": "GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to convert raw text into integer token IDs.",
    "self_attention": "Self-attention computes a weighted sum over all tokens in a sequence, where the weights come from query-key dot products.",
    "transformer": "The Transformer architecture, introduced in 'Attention Is All You Need' (2017), relies entirely on attention and removes recurrence.",
    "langgraph": "LangGraph is a library for building stateful, graph-based LLM applications using nodes and edges.",
    "checkpointer": "A checkpointer in LangGraph persists the state of a graph after every step, identified by a thread_id.",
    "tools_condition": "The tools_condition function in LangGraph checks whether the latest AIMessage contains tool_calls and routes to the tools node if so, or to END otherwise.",
    "mcp": "The Model Context Protocol (MCP) standardizes how LLM applications connect to external tools, data, and prompts via JSON-RPC.",
    "tool_annotations": "MCP's ToolAnnotations type includes readOnlyHint, destructiveHint, idempotentHint, and openWorldHint fields that describe a tool's side effects.",
    "rlhf": "Reinforcement Learning from Human Feedback (RLHF) fine-tunes a language model using a reward model trained on human preference data.",
    "dpo": "Direct Preference Optimization (DPO) optimizes a policy directly on preference pairs, without training a separate reward model.",
    "gan": "Generative Adversarial Networks (GANs) consist of a generator and a discriminator trained in an adversarial min-max game.",
    "rag": "Retrieval-Augmented Generation (RAG) combines a retriever that fetches relevant documents with a generator that conditions on those documents.",
    "bm25_doc": "BM25 is a sparse, keyword-based ranking function built on term frequency and inverse document frequency.",
}

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

doc_keys = list(CORPUS.keys())
doc_texts = list(CORPUS.values())
doc_embeddings = embedding_model.encode(doc_texts, normalize_embeddings=True)
```

Output:

```
Corpus: 14 documents
Embedding matrix shape: (14, 384)
```

The 14 documents are deliberately drawn from material already covered in this
repo — B01 tokenization concepts (`bpe`, `gpt2_tokenizer`, `self_attention`,
`transformer`), B02-style fine-tuning/generative concepts (`rlhf`, `dpo`,
`gan`, `rag`), and B03 Topics 1-3's own subject matter (`langgraph`,
`checkpointer`, `tools_condition`, `mcp`, `tool_annotations`), plus `bm25_doc`
(a description of BM25 itself — used as a deliberate distractor in Section 1).
`all-MiniLM-L6-v2` maps each document to a 384-dimensional vector;
`normalize_embeddings=True` makes every row of `doc_embeddings` unit length, so
cosine similarity reduces to a dot product.

```python
def dense_search(query, k=5):
    query_embedding = embedding_model.encode([query], normalize_embeddings=True)[0]
    similarities = doc_embeddings @ query_embedding
    ranked = np.argsort(-similarities)[:k]
    return [(doc_keys[i], float(similarities[i]), doc_texts[i]) for i in ranked]


query_numeric = "Which model has a vocabulary size of exactly 50257 tokens?"
for key, score, text in dense_search(query_numeric):
    print(f"  {score:.3f}  {key:18s} {text[:70]}")
```

Output:

```
  0.401  bm25_doc           BM25 is a sparse, keyword-based ranking function built on term frequen
  0.363  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to conve
  0.309  self_attention     Self-attention computes a weighted sum over all tokens in a sequence,
  0.215  langgraph          LangGraph is a library for building stateful, graph-based LLM applicat
  0.210  rlhf               Reinforcement Learning from Human Feedback (RLHF) fine-tunes a languag
```

`np.argsort(-similarities)` sorts indices by *descending* similarity (argsort
is ascending by default, so negating flips it). **`bm25_doc` ranks first**,
even though the question is about GPT-2. The correct answer, `gpt2_tokenizer`,
is 2nd. This is **failure mode 1**: the literal token `50257` carries almost no
weight in a 384-dimensional semantic embedding — both documents talk about
"tokens"/"vocabulary" in the abstract, so they land close together regardless
of the specific number.

```python
query_multihop = "What tokenizer does GPT-2 use, and what algorithm does that tokenizer implement?"
for key, score, text in dense_search(query_multihop, k=3):
    print(f"  {score:.3f}  {key:18s} {text[:70]}")

top1_key, _, top1_text = dense_search(query_multihop, k=1)[0]
print("A naive top-1 retriever would hand the LLM only this chunk:")
print(f"  [{top1_key}] {top1_text}")
```

Output:

```
  0.726  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to conve
  0.404  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm that iter
  0.335  self_attention     Self-attention computes a weighted sum over all tokens in a sequence,

A naive top-1 retriever would hand the LLM only this chunk:
  [gpt2_tokenizer] GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to convert raw text into integer token IDs.
```

This is **failure mode 2**: the *ranking* is correct (`gpt2_tokenizer` and
`bpe` are the top two), but `k=1` only returns `gpt2_tokenizer`, which doesn't
explain what BPE *does*. The information needed to fully answer the question
is split across two chunks.

---

## 2. Hybrid Search — BM25 + Dense + RRF

```python
def tokenize(text):
    for ch in "'.,?":
        text = text.replace(ch, "")
    return text.lower().split()


bm25_index = BM25Okapi([tokenize(t) for t in doc_texts])


def bm25_search(query, k=5):
    scores = bm25_index.get_scores(tokenize(query))
    ranked = np.argsort(-scores)[:k]
    return [(doc_keys[i], float(scores[i]), doc_texts[i]) for i in ranked]


for key, score, text in bm25_search(query_numeric):
    print(f"  {score:.3f}  {key:18s} {text[:70]}")
```

Output:

```
  7.426  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to conve
  2.391  rlhf               Reinforcement Learning from Human Feedback (RLHF) fine-tunes a languag
  2.293  self_attention     Self-attention computes a weighted sum over all tokens in a sequence,
  1.968  dpo                Direct Preference Optimization (DPO) optimizes a policy directly on pr
  1.735  checkpointer       A checkpointer in LangGraph persists the state of a graph after every
```

`BM25Okapi` is built once over all 14 tokenized documents (defaults
$k_1=1.5$, $b=0.75$). For `query_numeric`, `gpt2_tokenizer` wins by a wide
margin (7.426 vs 2.391) because the term `50257` appears in exactly one
document — high inverse document frequency. `bm25_doc` (dense's incorrect #1)
isn't even in the top 5.

```python
def reciprocal_rank_fusion(query, k=5, rrf_k=60):
    dense_ranked = [key for key, _, _ in dense_search(query, k=len(doc_keys))]
    bm25_ranked = [key for key, _, _ in bm25_search(query, k=len(doc_keys))]

    dense_rank = {key: rank + 1 for rank, key in enumerate(dense_ranked)}
    bm25_rank = {key: rank + 1 for rank, key in enumerate(bm25_ranked)}

    rrf_scores = {
        key: 1 / (rrf_k + dense_rank[key]) + 1 / (rrf_k + bm25_rank[key])
        for key in doc_keys
    }
    ranked = sorted(doc_keys, key=lambda key: -rrf_scores[key])[:k]
    return [(key, rrf_scores[key], dense_rank[key], bm25_rank[key]) for key in ranked]


for key, rrf_score, d_rank, b_rank in reciprocal_rank_fusion(query_numeric):
    print(f"{key:18s} {rrf_score:>10.5f} {d_rank:>11d} {b_rank:>10d}")
```

Output:

```
document            rrf_score  dense_rank  bm25_rank
gpt2_tokenizer        0.03252           2          1
self_attention        0.03175           3          3
rlhf                  0.03151           5          2
bm25_doc              0.03048           1         11
bpe                   0.03008           6          7
```

`reciprocal_rank_fusion` first runs **both** retrievers over the *entire*
corpus (`k=len(doc_keys)`, i.e. a full ranking, not just a top-k) so every
document has a `dense_rank` and `bm25_rank`. Each document's RRF score is
$\frac{1}{60 + \text{dense\_rank}} + \frac{1}{60 + \text{bm25\_rank}}$.
`gpt2_tokenizer` (dense_rank=2, bm25_rank=1) edges out `self_attention`
(dense_rank=3, bm25_rank=3): $\frac{1}{62}+\frac{1}{61}=0.03252$ vs
$\frac{1}{63}+\frac{1}{63}=0.03175$. **`gpt2_tokenizer` is now #1 overall** —
hybrid search fixed failure mode 1. Note `bm25_doc` (dense's wrong #1) drops to
4th, dragged down by its poor `bm25_rank` of 11.

---

## 3. Cross-Encoder Reranking

```python
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(query, candidate_keys):
    pairs = [(query, CORPUS[key]) for key in candidate_keys]
    scores = reranker.predict(pairs)
    order = np.argsort(-scores)
    return [(candidate_keys[i], float(scores[i])) for i in order]


candidates = [key for key, *_ in reciprocal_rank_fusion(query_numeric, k=5)]
print(f"RRF top-5 candidates: {candidates}")

for key, score in rerank(query_numeric, candidates):
    print(f"  {score:7.3f}  {key:18s} {CORPUS[key][:65]}")
```

Output:

```
RRF top-5 candidates: ['gpt2_tokenizer', 'self_attention', 'rlhf', 'bm25_doc', 'bpe']

Cross-encoder reranking:
    1.250  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to
  -10.090  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm that
  -10.205  self_attention     Self-attention computes a weighted sum over all tokens in a seque
  -10.577  bm25_doc           BM25 is a sparse, keyword-based ranking function built on term fr
  -10.804  rlhf               Reinforcement Learning from Human Feedback (RLHF) fine-tunes a la
```

`rerank` takes the **5 candidates that already survived RRF** (not the whole
corpus — that's the point: a cross-encoder forward pass per pair is too slow to
run over all 14 documents, let alone a real corpus) and scores each
`(query, document)` pair *jointly* with `CrossEncoder.predict`, which returns
raw logits (unbounded reals). `gpt2_tokenizer` scores **+1.250**; every other
candidate scores **below -10** — a gap of more than 11, compared to RRF's
top-4 scores all sitting within 0.002 of each other. The cross-encoder's joint
attention over `(query, document)` lets it directly notice the shared
substring `50257`.

---

## 4. Query Transformation — Multi-Query & HyDE

```python
multi_query_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content=json.dumps([
        "What tokenizer does GPT-2 use?",
        "What algorithm does the BPE tokenizer implement?",
    ]))
]))

decompose_prompt = f"Break this question into independent sub-questions as a JSON list: {query_multihop}"
sub_queries = json.loads(multi_query_llm.invoke(decompose_prompt).content)

retrieved_keys = set()
for sub_query in sub_queries:
    key, score, text = dense_search(sub_query, k=1)[0]
    retrieved_keys.add(key)
    print(f"  '{sub_query}' -> {key} ({score:.3f})")

single_key, _, _ = dense_search(query_multihop, k=1)[0]
print(f"Single-query top-1 retrieval would only return: {{'{single_key}'}}")
print(f"Multi-query retrieval returns: {retrieved_keys}")
```

Output:

```
Sub-queries:
  - What tokenizer does GPT-2 use?
  - What algorithm does the BPE tokenizer implement?

Retrieval per sub-query (top-1 each):
  'What tokenizer does GPT-2 use?'
    -> gpt2_tokenizer (0.744): GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to
  'What algorithm does the BPE tokenizer implement?'
    -> bpe (0.661): Byte Pair Encoding (BPE) is a subword tokenization algorithm that

Single-query top-1 retrieval would only return: {'gpt2_tokenizer'}
Multi-query retrieval returns: {'bpe', 'gpt2_tokenizer'}
```

`GenericFakeChatModel(messages=iter([...]))` is the same scripted-LLM pattern
from Topics 1-4: `.invoke(...)` ignores its input and returns the next message
from the iterator — here, a JSON-encoded list of two sub-questions.
`json.loads` parses it back into a Python list. Retrieving `k=1` for *each*
sub-query independently yields `gpt2_tokenizer` and `bpe` — together the union
covers both documents needed to fully answer `query_multihop`, fixing failure
mode 2 without ever increasing `k` for the original query.

```python
layperson_query = "Why does ChatGPT split words into pieces instead of using whole words?"

hyde_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content=(
        "Language models break text into smaller subword units rather than whole "
        "words because a fixed vocabulary cannot cover every possible word. "
        "Subword tokenization algorithms merge frequently occurring pairs of "
        "characters into larger tokens, producing an efficient vocabulary."
    ))
]))

for key, score, text in dense_search(layperson_query, k=3):
    print(f"  {score:.3f}  {key:18s} {text[:65]}")

hypothetical_doc = hyde_llm.invoke(f"Write a short passage answering: {layperson_query}").content
hyde_embedding = embedding_model.encode([hypothetical_doc], normalize_embeddings=True)[0]
hyde_similarities = doc_embeddings @ hyde_embedding
for i in np.argsort(-hyde_similarities)[:3]:
    print(f"  {hyde_similarities[i]:.3f}  {doc_keys[i]:18s} {doc_texts[i][:65]}")
```

Output:

```
Direct retrieval on the raw query:
  0.318  gpt2_tokenizer     GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to
  0.299  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm that
  0.206  bm25_doc           BM25 is a sparse, keyword-based ranking function built on term fr

HyDE hypothetical document:
  Language models break text into smaller subword units rather than whole words because a fixed vocabulary cannot cover every possible word. Subword tokenization algorithms merge frequently occurring pairs of characters into larger tokens, producing an efficient vocabulary.

Retrieval using the HyDE embedding instead of the raw query:
  0.384  bpe                Byte Pair Encoding (BPE) is a subword tokenization algorithm that
  0.372  bm25_doc           BM25 is a sparse, keyword-based ranking function built on term fr
  0.332  self_attention     Self-attention computes a weighted sum over all tokens in a seque
```

On the raw query, `gpt2_tokenizer` (0.318) edges out `bpe` (0.299). After
embedding the scripted hypothetical passage instead, `bpe` jumps to first
(0.384), ahead of `gpt2_tokenizer` (now 0.320, outside the top 3 shown). The
hypothetical passage is written in the same definitional register as the
corpus, so its embedding lands closer to `bpe` — the document that actually
explains the *algorithm* the layperson question is implicitly asking about.

---

## 5. Agentic RAG (Exercise)

### Reference (provided)

```python
@tool
def retrieve(query: str) -> str:
    candidates = [key for key, *_ in reciprocal_rank_fusion(query, k=5)]
    top_key, _ = rerank(query, candidates)[0]
    return CORPUS[top_key]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


tool_node = ToolNode([retrieve])


def build_agent_graph(scripted_llm):
    def call_model(state):
        return {"messages": [scripted_llm.invoke(state["messages"])]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    return builder.compile()


single_hop_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[
        {"name": "retrieve", "args": {"query": "What does tools_condition check for in LangGraph?"}, "id": "call_1"},
    ]),
    AIMessage(content="tools_condition checks the latest AIMessage for tool_calls and routes to the "
                      "tools node if present, or to END otherwise."),
]))

graph = build_agent_graph(single_hop_llm)
result = graph.invoke({"messages": [HumanMessage(content="What does tools_condition check for in LangGraph?")]})
for msg in result["messages"]:
    label = type(msg).__name__
    payload = getattr(msg, "tool_calls", None) or msg.content
    print(f"{label:12s} {payload}")
```

Output:

```
HumanMessage What does tools_condition check for in LangGraph?
AIMessage    [{'name': 'retrieve', 'args': {'query': 'What does tools_condition check for in LangGraph?'}, 'id': 'call_1', 'type': 'tool_call'}]
ToolMessage  The tools_condition function in LangGraph checks whether the latest AIMessage contains tool_calls and routes to the tools node if so, or to END otherwise.
AIMessage    tools_condition checks the latest AIMessage for tool_calls and routes to the tools node if present, or to END otherwise.
```

This is exactly Topic 4's ReAct/`tools_condition` wiring, with `retrieve` as
the only tool. `retrieve` itself is the *entire Sections 2-3 pipeline* in two
lines: get RRF's top-5 candidates, rerank with the cross-encoder, return the
top result's text. The first scripted `AIMessage` has empty `content` and a
non-empty `tool_calls` list, so `tools_condition` routes to the `tools` node;
`ToolNode` executes `retrieve(query="What does tools_condition check for in
LangGraph?")` and appends the result as a `ToolMessage`; control returns to
`agent`, which emits the second scripted `AIMessage` (no `tool_calls`, so
`tools_condition` routes to `END`).

### Exercise solution — two-hop retrieval

```python
multihop_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[
        {"name": "retrieve", "args": {"query": "What tokenizer does GPT-2 use?"}, "id": "call_1"},
    ]),
    AIMessage(content="", tool_calls=[
        {"name": "retrieve", "args": {"query": "What algorithm does the BPE tokenizer implement?"}, "id": "call_2"},
    ]),
    AIMessage(content="GPT-2 uses a BPE tokenizer, and BPE works by iteratively merging the most "
                      "frequent pair of adjacent symbols into a new token."),
]))

multihop_graph = build_agent_graph(multihop_llm)
result = multihop_graph.invoke({"messages": [HumanMessage(content=query_multihop)]})
for msg in result["messages"]:
    label = type(msg).__name__
    payload = getattr(msg, "tool_calls", None) or msg.content
    print(f"{label:12s} {payload}")
```

Output:

```
HumanMessage What tokenizer does GPT-2 use, and what algorithm does that tokenizer implement?
AIMessage    [{'name': 'retrieve', 'args': {'query': 'What tokenizer does GPT-2 use?'}, 'id': 'call_1', 'type': 'tool_call'}]
ToolMessage  GPT-2 uses a BPE tokenizer with a vocabulary of 50,257 tokens to convert raw text into integer token IDs.
AIMessage    [{'name': 'retrieve', 'args': {'query': 'What algorithm does the BPE tokenizer implement?'}, 'id': 'call_2', 'type': 'tool_call'}]
ToolMessage  Byte Pair Encoding (BPE) is a subword tokenization algorithm that iteratively merges the most frequent pair of adjacent symbols into a new token.
AIMessage    GPT-2 uses a BPE tokenizer, and BPE works by iteratively merging the most frequent pair of adjacent symbols into a new token.
```

`build_agent_graph`'s loop (`agent` → `tools` → `agent` → ...) runs **twice**
before `tools_condition` finally routes to `END` on the third `AIMessage`
(which has no `tool_calls`). Each `ToolMessage` is the `retrieve` tool's return
value for that step's query — note the **second** `retrieve` call's query
("What algorithm does the BPE tokenizer implement?") is only knowable *after*
the first call's result named "BPE" as the tokenizer. This is the key
difference from Section 4's multi-query: there, both sub-queries were decided
*up front* in one LLM call; here, the second query is conditioned on the first
tool result.

---

## 6. GraphRAG (Exercise)

### Reference (provided)

```python
TRIPLES = [
    ("GPT-2", "uses", "BPE_tokenizer"),
    ("BPE_tokenizer", "implements", "BPE_algorithm"),
    ("BPE_algorithm", "merges", "frequent_symbol_pairs"),
    ("LangGraph", "has_component", "checkpointer"),
    ("LangGraph", "has_component", "tools_condition"),
    ("checkpointer", "identified_by", "thread_id"),
    ("tools_condition", "checks", "AIMessage.tool_calls"),
    ("tools_condition", "routes_to", "tools_node"),
    ("tools_condition", "routes_to", "END"),
]

knowledge_graph = nx.DiGraph()
for head, relation, tail in TRIPLES:
    knowledge_graph.add_edge(head, tail, relation=relation)


def describe_path(graph, path):
    return "\n  ".join(
        f"{u} --{graph[u][v]['relation']}--> {v}"
        for u, v in zip(path, path[1:])
    )


path = nx.shortest_path(knowledge_graph, "GPT-2", "frequent_symbol_pairs")
print("  " + describe_path(knowledge_graph, path))
```

Output:

```
Knowledge graph: 11 nodes, 9 edges

Worked example -- "What does GPT-2's tokenizer actually do under the hood?"
  GPT-2 --uses--> BPE_tokenizer
  BPE_tokenizer --implements--> BPE_algorithm
  BPE_algorithm --merges--> frequent_symbol_pairs
```

`nx.DiGraph.add_edge(head, tail, relation=relation)` stores each triple as a
directed edge with the relation as an edge attribute, accessed later via
`graph[u][v]['relation']`. `nx.shortest_path` does an unweighted
breadth-first search — with only 9 edges there's only one path from `"GPT-2"`
to `"frequent_symbol_pairs"`, but the function generalizes to larger graphs
with multiple possible routes. `describe_path` zips consecutive nodes in the
path (`zip(path, path[1:])`) to produce each `(u, v)` edge pair, then formats
`u --relation--> v` for each.

### Exercise solution — branching traversal

```python
for target in ["tools_node", "END"]:
    path = nx.shortest_path(knowledge_graph, "LangGraph", target)
    print(f"Path to {target}:")
    print("  " + describe_path(knowledge_graph, path))
```

Output:

```
Path to tools_node:
  LangGraph --has_component--> tools_condition
  tools_condition --routes_to--> tools_node
Path to END:
  LangGraph --has_component--> tools_condition
  tools_condition --routes_to--> END
```

`tools_condition` has **two** outgoing `routes_to` edges (`tools_node` and
`END`) — `nx.shortest_path` is called once per target, returning two distinct
2-hop paths that share their first edge (`LangGraph --has_component-->
tools_condition`). This mirrors `tools_condition`'s actual runtime behavior
(Topic 2/4): one node, two possible destinations depending on whether the
latest `AIMessage` has `tool_calls`.

---

## Putting It All Together

The notebook ends with a markdown table and ASCII pipeline diagram comparing
all six stages — reproduced and explained in
[`../../notes/05-advanced-rag.md`](../../notes/05-advanced-rag.md#putting-it-all-together).
The short version: each stage is a strict addition that relaxes one of naive
RAG's three implicit commitments (one ranking signal, one retrieval pass, one
fixed `k`) — hybrid search adds a signal, reranking adds a pass, and
multi-query/HyDE/agentic RAG/GraphRAG all change what gets retrieved and how
many times.
