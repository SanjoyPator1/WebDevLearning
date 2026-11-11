# ============================================================
# LISTING: 05_smarter_chunking.py  (reference implementation -- FROM SCRATCH)
# BUILDING: Contextual retrieval -- an LLM-generated blurb prepended to a
#           chunk before it gets embedded -- plus REAL late chunking: one
#           forward pass of a local long-context embedding model over the
#           whole passage, then mean-pooling the per-token vectors by
#           chunk span. Both are demonstrated on the Ops Assistant's
#           ambiguous drain-then-restart runbook passage.
# REF: Chapter 6 notes, section 7 (Smarter Chunking: Context-Aware Splits)
# SETUP: late chunking needs torch and transformers (already in the repo's
#   .venv). The embedding model (nomic-ai/modernbert-embed-base, ~600 MB)
#   downloads from Hugging Face the first time it is used, then loads from
#   the local cache. It runs on this machine -- the late-chunking half of
#   this file makes NO API call.
# ============================================================
#
# Fixed-size chunking cuts a document by word/token count without ever
# looking at what the text says, and that is exactly what breaks the
# "deploy-drain-restart" runbook passage below: a 20-word cut lands
# right after the word "Once," leaving the second half of the sentence
# -- "it completes, restart the deploy service..." -- with no visible
# antecedent for "it." This file builds that broken chunk on purpose,
# then fixes it two different ways: contextual retrieval (add words
# that spell out what "it" refers to, before embedding) and late
# chunking (add no words at all: embed the WHOLE passage first, so every
# token's vector has already seen its neighbors, then average the token
# vectors that belong to each chunk).
#
# Late chunking needs one vector PER TOKEN out of the embedding model.
# The /embeddings endpoint used elsewhere in this file only returns one
# pooled vector per text, so it cannot expose them -- a local model can.

# ============================================================
# CHROMA SETUP (run once, before running this script):
#   docker run -d --name ch06-chroma -p 8000:8000 chromadb/chroma
# This starts a real Chroma vector database server on localhost:8000.
# To stop it later: docker stop ch06-chroma && docker rm ch06-chroma
# ============================================================

import asyncio
import os

import chromadb
import torch
from dotenv import load_dotenv
from openai import AsyncOpenAI
from transformers import AutoModel, AutoTokenizer

load_dotenv()

chroma_client = chromadb.HttpClient(host="localhost", port=8000)

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


# --- The late-chunking model: a real long-context embedding model, run locally ---
# ModernBERT-based, 768-dim vectors, reads up to 8192 tokens at once, and
# was trained with MEAN pooling -- averaging its token vectors is exactly
# how it normally makes one vector per text, which is what lets us reuse
# that same averaging over a chunk's tokens only. It REQUIRES a task
# prefix on every input: passages get DOCUMENT_PREFIX, queries get
# QUERY_PREFIX. Its vectors live in their own space, so a query must be
# embedded with THIS model to be compared against these chunk vectors --
# never against the Gemini vectors used in the contextual demo.
LATE_CHUNKING_MODEL_NAME = "nomic-ai/modernbert-embed-base"
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "

print("-" * 60)
print(f"Loading late-chunking embedding model: {LATE_CHUNKING_MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(LATE_CHUNKING_MODEL_NAME)
embedding_model = AutoModel.from_pretrained(LATE_CHUNKING_MODEL_NAME).eval()
print("  model loaded (runs locally, no API call)")

# Questions for the late-chunking demo. The first three mention only the
# DRAIN step, which chunk 2 alone never names; the last two also use
# chunk 2's own words ("restart the deploy service", "flag").
LATE_CHUNKING_QUERIES = [
    "what do I do after the drain step finishes?",
    "what happens once the load balancer drain completes?",
    "what should I do when the lb-drain command is done?",
    "how do I restart the deploy service after the drain finishes?",
    "which flag do I add when restarting the deploy service after the drain?",
]


# --- The Ops Assistant's runbook corpus (shared with 06_agentic_rag.py --
# duplicated rather than imported, since these files stay self-contained) ---
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
    {
        "id": "deploy-drain-restart",
        "text": (
            "Drain traffic from the load balancer using lb-drain --host "
            "prod-3. This takes about 90 seconds while in-flight requests "
            "finish. Once it completes, restart the deploy service using "
            "the same command from step 2, adding the --skip-migrations "
            "flag this time."
        ),
    },
]

DRAIN_RESTART_DOC = next(doc for doc in RUNBOOK_DOCS if doc["id"] == "deploy-drain-restart")


def split_into_fixed_size_word_chunks(text: str, words_per_chunk: int) -> list[str]:
    """Naive fixed-size chunking: cut on a raw word count, never looking
    at sentence boundaries. This is the exact mechanism section 7's
    notes walk through by hand -- a stand-in for real subword tokens,
    but close enough that the mechanism (and where it breaks) is
    visible."""
    words = text.split()
    return [
        " ".join(words[start : start + words_per_chunk])
        for start in range(0, len(words), words_per_chunk)
    ]


# Splitting the drain-restart passage every 20 words reproduces the
# notes' dry run exactly: 39 words total, word 20 is "Once," so the cut
# falls mid-sentence and CHUNK_2_TEXT starts with a dangling "it."
_fixed_size_chunks = split_into_fixed_size_word_chunks(
    DRAIN_RESTART_DOC["text"], words_per_chunk=20
)
CHUNK_1_TEXT, CHUNK_2_TEXT = _fixed_size_chunks[0], _fixed_size_chunks[1]

print("-" * 60)
print("Fixed-size chunking of the deploy-drain-restart passage (20 words/chunk):")
print(f"  CHUNK 1: {CHUNK_1_TEXT!r}")
print(f"  CHUNK 2: {CHUNK_2_TEXT!r}   <- 'it' has no antecedent in this chunk alone")

# Two Chroma collections, distinct from file 02's knowledge-agent
# collection, so this demo doesn't interfere with it.
PLAIN_COLLECTION_NAME = "ops_assistant_runbook_chunking_demo_plain"
CONTEXTUAL_COLLECTION_NAME = "ops_assistant_runbook_chunking_demo_contextual"

plain_collection = chroma_client.get_or_create_collection(
    name=PLAIN_COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
)
contextual_collection = chroma_client.get_or_create_collection(
    name=CONTEXTUAL_COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
)
# chromadb.HttpClient's methods (get_or_create_collection, add, query) are
# all synchronous -- calling them without `await` inside an async function
# below is intentional, not a mistake.


async def build_contextual_chunk(chunk_text: str, document_summary: str) -> str:
    """Generate a short 'where does this chunk live' blurb and prepend it
    to the chunk's own text, producing the string that should actually
    be passed to the embedding model.

    Args:
        chunk_text: the raw chunk as produced by fixed-size splitting.
        document_summary: a short description of the whole source
            document, used so the LLM can place this chunk within it.

    Returns:
        A single string: the generated blurb followed by the original
        chunk text, ready to be sent to the embedding model.

    Math note: this changes what gets embedded, not how embedding
    itself works -- embed(blurb + chunk) instead of embed(chunk).
    """
    print("-" * 60)
    print("Generating context blurb for chunk:")
    print(f"  Chunk preview: {chunk_text[:60]!r}...")

    response = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You place a short excerpt within its source document. "
                    "In 2-3 sentences, state which section this excerpt is "
                    "from, what step or topic it covers, and what "
                    "immediately precedes and follows it. Do not repeat "
                    "the excerpt itself."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Document summary: {document_summary}\n\nExcerpt:\n{chunk_text}"
                ),
            },
        ],
        temperature=0.0,
    )

    context_blurb = response.choices[0].message.content.strip()
    print(f"  Generated blurb: {context_blurb[:80]}...")

    contextual_chunk = f"{context_blurb}\n\n{chunk_text}"
    print(
        f"  Combined length: {len(contextual_chunk)} characters "
        f"(vs {len(chunk_text)} for the raw chunk)"
    )
    return contextual_chunk


async def run_contextual_chunking_demo() -> None:
    """Ingest CHUNK_2_TEXT twice -- once plain, once wrapped with a
    contextual blurb -- into two separate Chroma collections, then run
    the same ambiguous query against both and compare similarity
    scores side by side."""
    print("=" * 60)
    print("CONTEXTUAL RETRIEVAL: plain chunk vs. blurb-prepended chunk")
    print("=" * 60)

    document_summary = (
        "Deploy Runbook: Rolling Back a Release -- step 4 of 6, which "
        "drains traffic from the load balancer and then restarts the "
        "deploy service"
    )
    contextual_chunk_text = await build_contextual_chunk(CHUNK_2_TEXT, document_summary)

    print("-" * 60)
    print("Embedding and ingesting both versions of the same chunk...")
    plain_embedding = await embed_text(CHUNK_2_TEXT)
    contextual_embedding = await embed_text(contextual_chunk_text)

    plain_collection.add(
        ids=["chunk2-plain"], documents=[CHUNK_2_TEXT], embeddings=[plain_embedding]
    )
    contextual_collection.add(
        ids=["chunk2-contextual"],
        documents=[contextual_chunk_text],
        embeddings=[contextual_embedding],
    )
    print(f"  plain_collection now has {plain_collection.count()} chunk(s)")
    print(f"  contextual_collection now has {contextual_collection.count()} chunk(s)")

    query = "what do I do after the drain step finishes?"
    print("-" * 60)
    print(f"Querying both collections with: {query!r}")
    query_embedding = await embed_text(query)

    plain_result = plain_collection.query(query_embeddings=[query_embedding], n_results=1)
    contextual_result = contextual_collection.query(
        query_embeddings=[query_embedding], n_results=1
    )

    # Chroma reports cosine DISTANCE (1 - similarity, section 2); convert
    # back to similarity here purely so the two numbers read the same way
    # the rest of this chapter's dry runs report cosine similarity.
    plain_distance = plain_result["distances"][0][0]
    contextual_distance = contextual_result["distances"][0][0]
    plain_similarity = 1 - plain_distance
    contextual_similarity = 1 - contextual_distance

    print("-" * 60)
    print("RESULTS (side by side):")
    print(f"  plain chunk        similarity = {plain_similarity:.4f}")
    print(f"  contextual chunk   similarity = {contextual_similarity:.4f}")
    if contextual_similarity > plain_similarity:
        print(
            "  -> the contextual version scores higher: spelling out what "
            "'it' refers to gave the embedding something to hold onto."
        )
    else:
        print(
            "  -> scores were close/mixed this run; embedding models vary "
            "run to run, but the contextual version should trend higher "
            "across repeated queries like this one."
        )


def embed_all_tokens(text: str, prefix: str) -> tuple[torch.Tensor, list[tuple[int, int]]]:
    """Run the WHOLE text through the embedding model in ONE forward pass
    and keep a vector for every token, instead of letting the model
    squash them into a single vector. Every token is processed alongside
    every other token (attention), so each token's vector already
    reflects the words around it.

    Args:
        text: the full passage (or query) to embed.
        prefix: the task prefix this model requires -- DOCUMENT_PREFIX for
            passages, QUERY_PREFIX for queries. Added in front of the text
            before tokenizing.

    Returns:
        token_vectors: shape (num_tokens, 768), one row per token.
        token_offsets: one (start_char, end_char) per token, measured on
            the ORIGINAL text (prefix not counted). Special markers like
            [CLS] and [SEP] get zero-width offsets and prefix tokens land
            before position 0, so pool_span() can skip both.

    Math note: no pooling happens here -- this is the per-token matrix
    that late chunking averages over a chunk's span afterwards.
    """
    encoded = tokenizer(prefix + text, return_tensors="pt", return_offsets_mapping=True)
    offset_mapping = encoded.pop("offset_mapping")  # shape: (1, num_tokens, 2)
    print(f"  [tokens] {encoded['input_ids'].shape[1]} tokens (prefix and 2 special markers included)")

    with torch.no_grad():  # inference only, no gradients needed
        model_output = embedding_model(**encoded)
    token_vectors = model_output.last_hidden_state[0]  # shape: (num_tokens, 768)
    print(f"  [tokens] token_vectors shape: {tuple(token_vectors.shape)}")

    token_offsets = [
        (start - len(prefix), end - len(prefix)) for start, end in offset_mapping[0].tolist()
    ]
    return token_vectors, token_offsets


def pool_span(
    token_vectors: torch.Tensor,
    token_offsets: list[tuple[int, int]],
    char_span: tuple[int, int],
) -> list[float]:
    """Average the vectors of every token inside one chunk's character
    span -- the "split late" half of late chunking.

    Args:
        token_vectors: shape (num_tokens, 768), from embed_all_tokens().
        token_offsets: one (start_char, end_char) per token, same call.
        char_span: (start_char, end_char) of the chunk in the original text.

    Returns:
        One vector of length 768 for that chunk.

    Math: chunk_vector = (1 / n) * sum of the n token vectors in the span.
    """
    span_start, span_end = char_span
    token_indexes_in_span = [
        token_index
        for token_index, (token_start, token_end) in enumerate(token_offsets)
        # token_end > token_start drops the zero-width special markers. The
        # MIDPOINT is tested, not the start, because this tokenizer's
        # offsets include a word's leading space -- a start test would
        # drop the first word of a chunk from both neighbouring chunks.
        if token_end > token_start
        and span_start <= (token_start + token_end) / 2 < span_end
    ]
    print(f"  [pool] span {char_span} covers {len(token_indexes_in_span)} tokens")

    chunk_vector = token_vectors[token_indexes_in_span].mean(dim=0)  # shape: (768,)
    return chunk_vector.tolist()


def embed_text_locally(text: str, prefix: str) -> list[float]:
    """Ordinary (non-late) embedding with the same local model: run the
    text on its own, then average ALL of its tokens. Late chunking
    differs from this in only one way -- how much text the model has
    seen before the averaging happens."""
    token_vectors, token_offsets = embed_all_tokens(text, prefix)
    return pool_span(token_vectors, token_offsets, (0, len(text)))


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Plain-Python cosine similarity (section 2's formula), used below
    for the late-chunking demo since we compare two embeddings directly
    rather than going through Chroma.

    Math: cos(a, b) = (a . b) / (||a|| * ||b||)
    """
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = sum(a * a for a in vector_a) ** 0.5
    norm_b = sum(b * b for b in vector_b) ** 0.5
    return dot_product / (norm_a * norm_b)


def run_late_chunking_demo() -> None:
    """Late chunking: embed the whole passage in one pass, THEN split.

    Compares chunk 2 two ways against the same queries: embedded alone
    (it only ever sees its own words) vs. late-chunked (its token vectors
    were computed while the model could also see chunk 1). Everything
    here runs locally -- no API call, and no Chroma.
    """
    print("=" * 60)
    print("LATE CHUNKING: embed the whole passage first, split afterwards")
    print("=" * 60)

    passage = DRAIN_RESTART_DOC["text"]
    chunk_2_start = passage.index(CHUNK_2_TEXT)
    chunk_2_span = (chunk_2_start, chunk_2_start + len(CHUNK_2_TEXT))
    print(f"  Passage: {len(passage)} characters; chunk 2 spans characters {chunk_2_span}")

    print("-" * 60)
    print("STEP 1: ONE pass over the WHOLE passage (chunk 1 + chunk 2 together)")
    token_vectors, token_offsets = embed_all_tokens(passage, DOCUMENT_PREFIX)

    print("-" * 60)
    print("STEP 2: split late -- average only the tokens that belong to chunk 2")
    late_chunk_2_vector = pool_span(token_vectors, token_offsets, chunk_2_span)

    print("-" * 60)
    print("STEP 3: for comparison, embed chunk 2 ALONE (the model sees only its words)")
    alone_chunk_2_vector = embed_text_locally(CHUNK_2_TEXT, DOCUMENT_PREFIX)

    vectors_agreement = cosine_similarity(late_chunk_2_vector, alone_chunk_2_vector)
    print(
        f"  late vs. alone vector for the SAME words: cosine = {vectors_agreement:.4f} "
        "(below 1.0 means the surrounding text really changed the vector)"
    )

    print("-" * 60)
    print("STEP 4: score both against each query (cosine similarity)")
    late_wins = 0
    differences = []
    for query in LATE_CHUNKING_QUERIES:
        query_vector = embed_text_locally(query, QUERY_PREFIX)
        alone_similarity = cosine_similarity(query_vector, alone_chunk_2_vector)
        late_similarity = cosine_similarity(query_vector, late_chunk_2_vector)
        difference = late_similarity - alone_similarity
        differences.append(difference)
        late_wins += late_similarity > alone_similarity
        print(f"  Query: {query!r}")
        print(
            f"    alone = {alone_similarity:.4f}   late = {late_similarity:.4f}   "
            f"late - alone = {difference:+.4f}"
        )

    print("-" * 60)
    print("RESULTS:")
    print(f"  late chunking scored higher on {late_wins} of {len(LATE_CHUNKING_QUERIES)} queries")
    print(f"  mean (late - alone) = {sum(differences) / len(differences):+.4f}")
    print(
        "  Note: late chunking is not a guaranteed win on every query. It helps "
        "most when the question leans on context chunk 2 alone is missing (the "
        "drain), and it can slightly hurt when the question already uses chunk "
        "2's own words, because the surrounding text dilutes them."
    )


async def main() -> None:
    await run_contextual_chunking_demo()
    run_late_chunking_demo()


if __name__ == "__main__":
    asyncio.run(main())
