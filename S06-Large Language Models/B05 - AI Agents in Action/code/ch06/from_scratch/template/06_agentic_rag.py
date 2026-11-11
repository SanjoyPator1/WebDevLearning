# ============================================================
# LISTING: 06_agentic_rag.py  (reference implementation -- FROM SCRATCH)
# BUILDING: The retrieve-judge-reformulate loop -- an agent that decides
#           whether a retrieval was actually good enough before
#           answering, rewrites its own search query when it wasn't, and
#           gives up honestly when a rewrite cannot help. It is run on
#           four kinds of question (clear, ambiguous, unanswerable, and a
#           follow-up that needs the conversation) so the judge's
#           behaviour is observed, not assumed.
# REF: Chapter 6 notes, section 8 (Agentic RAG: When the Agent Controls
#      Its Own Retrieval)
# ============================================================
#
# Naive RAG retrieves once and generates once, no matter how vague the
# question was, so a weak retrieval gets answered just as confidently as
# a strong one. The loop below adds one extra step in between retrieval
# and generation: an explicit judgment call asking "does this retrieved
# context contain what is needed to answer the question?", and a
# rewritten search query when the answer is no.
#
# Three rules keep the loop honest. First, only the SEARCH uses the
# rewritten query -- the judge and the final answer always use the user's
# ORIGINAL question. Second, a rewrite can only add information that
# exists somewhere: in the model's general sense of what the question
# probably means, or in the earlier conversation (a follow-up like "what if
# that doesn't work?" is unsearchable until "that" is spelled out). It
# cannot invent what nobody ever said. Third, the loop stops when another
# attempt could not help: the judge offers no new query, or a rewritten
# query brings back exactly the same chunks as before.

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

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


# --- The Ops Assistant's runbook corpus (shared with 05_smarter_chunking.py --
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


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Plain-Python cosine similarity (section 2's formula): dot product
    over the product of the two vectors' norms."""
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = sum(a * a for a in vector_a) ** 0.5
    norm_b = sum(b * b for b in vector_b) ** 0.5
    return dot_product / (norm_a * norm_b)


# This file uses a simple in-memory store (a plain list of
# (chunk_id, chunk_text, embedding) tuples, computed once at startup) so
# that the judge-and-retry LOOP is the focus, not the storage backend --
# see 02_vector_search_knowledge_agent.py for the same retrieval idea
# against a real Chroma server.
VECTOR_STORE: list[tuple[str, str, list[float]]] = []


async def build_vector_store() -> None:
    """One-time ingestion pass: embed every runbook doc and append it to
    the in-memory VECTOR_STORE. This is Phase 1 from section 2, done for
    real, just without a database sitting underneath it. All the chunks go
    to the embedding model in ONE request (the endpoint accepts a list of
    texts), so building the store costs 1 API call, not one per chunk."""
    print("-" * 60)
    print(f"Embedding all {len(RUNBOOK_DOCS)} runbook chunks in one request...")
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL, input=[doc["text"] for doc in RUNBOOK_DOCS]
    )
    # The API returns the vectors in the same order as the texts sent. Some
    # providers also number each item (item.index); Gemini leaves it None,
    # so only sort when every item actually has a number.
    items = response.data
    if all(item.index is not None for item in items):
        items = sorted(items, key=lambda item: item.index)
    for doc, item in zip(RUNBOOK_DOCS, items):
        VECTOR_STORE.append((doc["id"], doc["text"], item.embedding))
        print(f"  stored [{doc['id']}]  ({len(item.embedding)} numbers)")


async def search_runbook(query: str, top_k: int = 3) -> list[tuple[str, str, float]]:
    """Embed the query and rank every stored chunk by cosine similarity
    to it, exactly the same shape as section 4's search_runbook, just
    backed by a Python list instead of Chroma.

    Returns: list of (chunk_id, chunk_text, score), highest score first.
    """
    query_embedding = await embed_text(query)
    scored_chunks = [
        (chunk_id, chunk_text, cosine_similarity(query_embedding, chunk_embedding))
        for chunk_id, chunk_text, chunk_embedding in VECTOR_STORE
    ]
    scored_chunks.sort(key=lambda entry: entry[2], reverse=True)
    return scored_chunks[:top_k]


class JudgeVerdict(BaseModel):
    """The judge's verdict, as structured data. better_query is an empty
    string (not null) when sufficient is true, which keeps the schema sent
    to the provider as small and plain as possible."""

    sufficient: bool
    better_query: str | None = ""


# The same shape as JudgeVerdict, written out by hand as a JSON schema. It is
# sent to the provider as `response_format`, which asks the model to return
# JSON of exactly this shape instead of free text we would have to parse.
JUDGE_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "sufficient": {"type": "boolean"},
        "better_query": {"type": "string"},
    },
    "required": ["sufficient", "better_query"],
}


def format_history(history: list[dict]) -> str:
    """Render earlier conversation turns as plain 'User: ...' and
    'Assistant: ...' lines, for the judge prompt."""
    return "\n".join(
        f"{'User' if turn['role'] == 'user' else 'Assistant'}: {turn['content']}"
        for turn in history
    )


def build_escalation_result(attempts: int, model_calls: int, outcome: str) -> dict:
    """The honest 'no confident answer' result, shared by every way the
    loop can give up."""
    return {
        "answer": (
            "I could not find a confident answer in the runbook "
            f"after {attempts} attempt(s). Escalating to a human."
        ),
        "attempts": attempts,
        "model_calls": model_calls,
        "outcome": outcome,
    }


def parse_judge_verdict(raw_reply: str) -> dict:
    """Turn the judge's reply into a dict. The provider is asked to return
    JSON matching JUDGE_VERDICT_SCHEMA, so this is normally a plain
    json.loads. It still validates instead of trusting: a provider that
    ignores the schema can return prose, or JSON wrapped in a code fence.

    Returns: {"sufficient": bool, "better_query": str | None,
              "parsed_ok": bool}
    better_query is None when the judge gave no query (empty, "none" or
    "n/a"). parsed_ok is False when the reply is not a valid verdict --
    in that case "sufficient" is False and the caller should say so out
    loud, because a formatting problem must not look like a genuine
    "the retrieval was poor" verdict.
    """
    # your turn:
    #   1. clean the reply: strip whitespace, then remove a leading ```json
    #      or ``` fence and a trailing ``` fence if present
    #      (str.removeprefix / str.removesuffix)
    #   2. inside a try/except catching (json.JSONDecodeError,
    #      ValidationError): verdict = JudgeVerdict.model_validate(
    #      json.loads(cleaned_reply), strict=True). On failure return
    #      {"sufficient": False, "better_query": None, "parsed_ok": False}.
    #      (strict=True matters: it stops the string "yes" from being
    #      accepted as the boolean True.)
    #   3. better_query = (verdict.better_query or "").strip(); if it is
    #      empty, "none" or "n/a" (ignoring case and a trailing period) it
    #      becomes None
    #   4. return {"sufficient": verdict.sufficient, "better_query":
    #      better_query, "parsed_ok": True}
    raise NotImplementedError


async def judge_retrieval(
    question: str, retrieved_chunks: list[str], history: list[dict] | None = None
) -> dict:
    """Calls a raw chat-completions model and asks it to judge whether
    the retrieved chunks contain what is needed to answer the question.
    The prompt is deliberately generic: it names no runbook and gives no
    hint about which answer is right, so the verdict is the model's own.
    The reply is requested as JSON through `response_format`.

    When `history` (earlier conversation turns) is given, the judge also
    reads it, because a follow-up like "what if that doesn't work?" can
    only be understood in the light of what came before. The search
    engine cannot see that conversation, so the judge is told that any
    rewritten query must make sense on its own.

    Returns: {"sufficient": bool, "better_query": str | None,
              "parsed_ok": bool}  (see parse_judge_verdict)
    """
    # your turn:
    #   1. join retrieved_chunks into one context_text block
    #   2. build the judge prompt. With NO history it is: "Question: ...",
    #      the retrieved context, "decide whether this retrieved context
    #      contains the specific information needed to answer the
    #      question", be strict (loosely related context, or a question
    #      that could mean different things with no way to tell which,
    #      counts as "no"), and ask for a JSON object with two fields:
    #      sufficient (true or false) and better_query (a more specific
    #      search query that would find what is missing if sufficient is
    #      false, otherwise an empty string).
    #      With history, ALSO: put "Conversation so far:" (use
    #      format_history(history)) before the question and call it the
    #      "Latest question", tell the judge to read it in the light of the
    #      conversation, and tell it the search engine cannot see the
    #      conversation, so the better query must make sense on its own and
    #      include anything the conversation says that the latest question
    #      leaves out. Do NOT mention any particular runbook in the prompt.
    #   3. send one raw chat-completions call: model=CHAT_MODEL,
    #      temperature=0.0, and response_format={"type": "json_schema",
    #      "json_schema": {"name": "judge_verdict", "schema":
    #      JUDGE_VERDICT_SCHEMA}}
    #   4. raw_reply = response.choices[0].message.content or "" and print it
    #   5. judgment = parse_judge_verdict(raw_reply); if parsed_ok is False,
    #      print a clear WARNING that the reply was not a valid verdict
    #   6. return judgment
    raise NotImplementedError


async def generate_final_answer(
    question: str, retrieved_chunks: list[str], history: list[dict] | None = None
) -> str:
    """One raw chat-completions call that writes the final answer,
    strongly grounded in the retrieved chunks -- same grounding shape as
    section 4's answer_from_runbook. Earlier conversation turns, when
    given, go in as prior chat messages so the model can read a follow-up
    question the way the user meant it."""
    # your turn:
    #   1. system prompt: answer ONLY from the given excerpts, or say
    #      exactly "I couldn't find that in the runbook." When there IS a
    #      history, add one sentence saying the earlier messages are only
    #      there so the model can understand what the latest question
    #      refers to, and that every fact in the answer must still come from
    #      the excerpts. (Without that sentence a model told to answer ONLY
    #      from the excerpts can refuse a follow-up like "what if that
    #      doesn't work?", because "that" is not defined in the excerpts.)
    #   2. messages = the system prompt, then any history turns, then the
    #      question as the final user message
    #   3. one chat call with temperature=0.0 (like the judge, so the same
    #      chunks are answered the same way each run); return the text
    raise NotImplementedError


async def answer_with_agentic_retrieval(
    question: str, max_attempts: int = 3, history: list[dict] | None = None
) -> dict:
    """Answers a question by retrieving from the runbook, judging
    whether the retrieved text is sufficient, and reformulating the
    search query if it isn't -- up to max_attempts tries. The first search
    uses the question exactly as typed. Stops early, without answering,
    in two cases where another attempt could not help:
      - the judge offers no NEW query (a retry would repeat the search);
      - a rewritten query brings back exactly the same chunks as the
        previous attempt (no new evidence, so judging again would give the
        same verdict -- and the judge call is skipped).

    Returns: {"answer": str, "attempts": int, "model_calls": int,
              "outcome": "answered" | "stopped_no_new_query" |
                         "stopped_same_results" | "exhausted_attempts"}
    model_calls counts every embedding or chat call made for THIS
    question (not the one-time store build), so the cost of the loop can
    be compared with naive RAG's 2.
    """
    # your turn: implement the retrieve-judge-reformulate cycle from
    # section 8:
    #   1. current_query = question; tried_queries = [question.strip().lower()];
    #      previous_chunk_ids = None; model_calls = 0
    #   2. for attempt in range(1, max_attempts + 1): print an ATTEMPT
    #      banner with the current query, call
    #      search_runbook(current_query, top_k=3) and add 1 to model_calls
    #      (one embedding call), print each retrieved chunk's id/score
    #   3. chunk_ids = the SET of retrieved ids. If previous_chunk_ids is
    #      not None and chunk_ids equals it, the rewrite brought back
    #      nothing new: print that, and return
    #      build_escalation_result(attempt, model_calls,
    #      "stopped_same_results") WITHOUT calling the judge. Otherwise
    #      remember chunk_ids as previous_chunk_ids.
    #   4. call judge_retrieval(question, retrieved_texts, history) -- the
    #      ORIGINAL question, never the rewrite -- add 1 to model_calls
    #      (one chat call) and print the judgment
    #   5. if judgment["sufficient"] is True: call generate_final_answer
    #      (original question and history again), add 1 to model_calls, and
    #      return {"answer": ..., "attempts": attempt, "model_calls": ...,
    #      "outcome": "answered"} immediately
    #   6. otherwise read better_query. If it is None, or (lowercased and
    #      stripped) is already in tried_queries, print that the judge
    #      offered no NEW query, and return build_escalation_result(attempt,
    #      model_calls, "stopped_no_new_query")
    #   7. else record the new query in tried_queries, set current_query to
    #      it, print that you are reformulating, and loop again
    #   8. if every attempt is used, return build_escalation_result(
    #      max_attempts, model_calls, "exhausted_attempts")
    raise NotImplementedError


# An earlier exchange for the follow-up scenario. Its answer comes straight
# from the rollback runbook chunk, so nothing here is invented.
FOLLOW_UP_HISTORY = [
    {"role": "user", "content": "How do I roll back a bad deploy?"},
    {
        "role": "assistant",
        "content": (
            "Run `deploy rollback --service <name> --to-version <last-good-tag>`. "
            "It reverts traffic within 90 seconds."
        ),
    },
]

# Four kinds of question, so the judge's behaviour is observed rather than
# assumed. The last one is the case a rewrite exists for: on its own the
# message "what if that doesn't work?" has no searchable content, because
# what "that" refers to lives only in the earlier conversation. What each
# scenario actually does is printed in the summary -- none of the
# outcomes is scripted.
SCENARIOS = [
    ("clear question", "ERR_5023 payment gateway timeout, how do I fix it?", None),
    ("ambiguous question", "the deploy is stuck, what do I do", None),
    (
        "question the runbook cannot answer",
        "how do I rotate the TLS certificate on the load balancer?",
        None,
    ),
    ("follow-up that needs the conversation", "what if that doesn't work?", FOLLOW_UP_HISTORY),
]


async def main() -> None:
    """Entry point: build the in-memory store, run the agentic loop on
    each scenario, then print a summary of what each one cost."""
    # your turn:
    #   1. await build_vector_store()
    #   2. for each (label, question, history) in SCENARIOS: print the label
    #      and question (and the earlier conversation, if there is one), run
    #      answer_with_agentic_retrieval(question, max_attempts=3,
    #      history=history), print the answer and the attempts/outcome, and
    #      keep (label, result)
    #   3. print a SUMMARY table: one row per scenario with attempts,
    #      model_calls and outcome, headed by the reminder that naive RAG
    #      uses 2 model calls per question (1 search embedding + 1 answer)
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
