# ============================================================
# LISTING: 08_hybrid_memory_architecture.py  (reference implementation -- FROM SCRATCH)
# BUILDING: The hybrid semantic-plus-graph memory workflow (section 11,
#           Part A) plus a small, working illustration of OS-inspired
#           paging (section 11, Part B) -- five steps that turn one
#           incoming message into an answer that neither store alone
#           could give.
# REF: Chapter 6 notes, sections 9 (Memory: Architecture, Not Metaphor)
#      and 11 (Modern Memory Architectures: From Graphs to Memory
#      Operating Systems)
# ============================================================
#
# Graph memory (file 7) only knows what someone explicitly wired in:
# nobody ever added an edge between "cold weather" and "deploy
# timeouts". Semantic memory works on meaning, so it can find that
# pattern in old chat -- but old chat can't reliably say who is on call
# RIGHT NOW, because chat goes stale and nothing marks which message is
# the latest truth. This file runs both side by side:
#
#   1. semantic search finds similar past chat (the fuzzy PATTERN)
#   2. entities are pulled from the new message AND from those hits
#   3. the graph walks out from those entities, both directions, up to
#      two hops, and collects the connected facts (the CURRENT structure)
#   4. one model call combines both
#   5. the message is written back to semantic memory, and an on-call
#      handoff REPLACES the old on-call edge in the graph
#
# The third demo message asks who to page after a handoff. Semantic
# memory then holds BOTH the old "moved to Priya" chat and the new
# "Marcus is now on-call" chat; only the graph says which one is current.

# ============================================================
# CHROMA SETUP (run once, before running this script; this is the same
# Chroma server used by files 2-5, just a different collection so the
# demos don't interfere with each other):
#   docker run -d --name ch06-chroma -p 8000:8000 chromadb/chroma
# This starts a real Chroma vector database server on localhost:8000.
# To stop it later: docker stop ch06-chroma && docker rm ch06-chroma
# ============================================================
#
# Calls per run with the default settings (chat = Gemini, embeddings = a
# local Ollama model):
#   - 3 Gemini chat calls, one per message. This is all that uses quota.
#   - 7 local embedding requests, free: 1 for the 5 seed snippets, then 2 per
#     message (the message as a SEARCH QUERY, and again as a stored
#     DOCUMENT, because the local model wants a different prefix for each).
# With EMBEDDING_PROVIDER = "gemini" (no prefixes) the stored copy reuses the
# query vector, so it is 1 + 3 = 4 Gemini embedding requests plus the 3 chat
# calls.

# NOTE:
# Chroma  = old chat TEXT + its number-list, found by "sounds like"
# graph   = exact FACTS between names, found by "is connected to"


import asyncio
import os
import re

import chromadb
from dotenv import load_dotenv
from openai import APIConnectionError, AsyncOpenAI, NotFoundError

load_dotenv()

chroma_client = chromadb.HttpClient(host="localhost", port=8000)

# Two separate settings, because the two jobs are different. The chat model
# WRITES the answer. The embedding model turns text into numbers so Chroma can
# compare meanings. The embedding side is the one that runs many times, so it
# defaults to a free local model.
CHAT_PROVIDER = "gemini"  # "gemini" or "ollama": writes the final answer
EMBEDDING_PROVIDER = "ollama"  # "ollama" or "gemini": text -> numbers

# The local embedding model Ollama serves. Pull it once before running:
#   ollama pull qwen3-embedding:0.6b     (639 MB, needs Ollama 0.12.1 or newer)
#   ollama pull nomic-embed-text         (274 MB, also works on older Ollama)
OLLAMA_EMBEDDING_MODEL = "qwen3-embedding:0.6b"

# Many embedding models want a short prefix that says whether a text is a
# stored DOCUMENT or a search QUERY. Each entry is (document_prefix,
# query_prefix). The prefix is part of the text that gets embedded.
EMBEDDING_PREFIXES = {
    "gemini-embedding-001": ("", ""),
    "nomic-embed-text": ("search_document: ", "search_query: "),
    "qwen3-embedding:0.6b": (
        "",
        "Instruct: Given a chat message, retrieve relevant past chat messages\nQuery:",
    ),
}


def make_client(provider: str) -> AsyncOpenAI:
    """Both providers speak the OpenAI-compatible API, so only the address
    and the key differ."""
    if provider == "gemini":
        return AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.environ["GEMINI_API_KEY"],
        )
    if provider == "ollama":
        return AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    raise ValueError(f"unknown provider: {provider!r}")


chat_client = make_client(CHAT_PROVIDER)
embedding_client = make_client(EMBEDDING_PROVIDER)
CHAT_MODEL = os.environ["GEMINI_MODEL"] if CHAT_PROVIDER == "gemini" else "qwen3:8b"
EMBEDDING_MODEL = (
    "gemini-embedding-001" if EMBEDDING_PROVIDER == "gemini" else OLLAMA_EMBEDDING_MODEL
)
if EMBEDDING_MODEL not in EMBEDDING_PREFIXES:
    raise ValueError(
        f"add {EMBEDDING_MODEL!r} to EMBEDDING_PREFIXES as (document_prefix, query_prefix)"
    )
DOCUMENT_PREFIX, QUERY_PREFIX = EMBEDDING_PREFIXES[EMBEDDING_MODEL]


async def embed_texts(texts: list[str], is_query: bool = False) -> list[list[float]]:
    """Embed several texts in ONE request (the endpoint accepts a list). Each
    text gets the model's document prefix, or its query prefix when
    `is_query` is True, in front of it first. The vectors come back in the
    same order as the texts. Some providers also number each item
    (item.index); Gemini leaves it None, so the items are only sorted when
    every one of them has a number."""
    prefix = QUERY_PREFIX if is_query else DOCUMENT_PREFIX
    try:
        response = await embedding_client.embeddings.create(
            model=EMBEDDING_MODEL, input=[prefix + text for text in texts]
        )
    except APIConnectionError:
        raise SystemExit(
            f"Cannot reach the {EMBEDDING_PROVIDER} embedding server. For Ollama, open "
            "the Ollama app, then check: curl localhost:11434/api/version"
        ) from None
    except NotFoundError:
        raise SystemExit(
            f"The embedding model {EMBEDDING_MODEL!r} is not available. "
            f"For Ollama, run: ollama pull {EMBEDDING_MODEL}"
        ) from None
    items = list(response.data)
    if all(item.index is not None for item in items):
        items = sorted(items, key=lambda item: item.index)
    return [item.embedding for item in items]


async def embed_query(text: str) -> list[float]:
    """Embed one text as a SEARCH QUERY (what you compare against stored texts)."""
    return (await embed_texts([text], is_query=True))[0]


async def embed_document(text: str) -> list[float]:
    """Embed one text as a stored DOCUMENT (what gets saved in Chroma)."""
    return (await embed_texts([text]))[0]


# --- Semantic memory: a small made-up corpus of past "incident chat"
# snippets, in its OWN Chroma collection (conversational memory, not
# runbook knowledge).
MEMORY_COLLECTION_NAME = "ops_assistant_memory"

PAST_INCIDENT_SNIPPETS = [
    {
        "id": "mem-1",
        "text": (
            "EU deploys keep failing whenever it's below freezing there, "
            "something about the data-center cooling throttling network I/O"
        ),
    },
    {
        "id": "mem-2",
        "text": "cold snap in the EU region again, deploys flaking",
    },
    {
        "id": "mem-3",
        "text": (
            "payments-service on-call rotation moved to Priya this week "
            "after Marcus's shift ended"
        ),
    },
    {
        "id": "mem-4",
        "text": (
            "restarted the connection pool for payments after ECONNREFUSED "
            "errors this morning"
        ),
    },
    {
        "id": "mem-5",
        "text": (
            "reminder: the EU cluster shares a caching layer with the "
            "US-East cluster, so EU slowdowns can bleed into US traffic"
        ),
    },
]


async def reset_semantic_memory():
    """Start every run from the same semantic memory: delete the
    collection if an earlier run left one behind, create it fresh, and
    store the 5 seed snippets (all embedded in ONE request). Without the
    reset, the Chroma server keeps the messages an earlier run wrote back,
    and the next run's search finds its own old message at similarity 1.0.

    Returns: the fresh Chroma collection."""
    print("-" * 60)
    print("Resetting semantic memory and storing the seed snippets...")
    existing_names = [
        c if isinstance(c, str) else c.name for c in chroma_client.list_collections()
    ]
    if MEMORY_COLLECTION_NAME in existing_names:
        chroma_client.delete_collection(MEMORY_COLLECTION_NAME)
        print(f"  deleted the collection an earlier run left behind: {MEMORY_COLLECTION_NAME}")
    collection = chroma_client.create_collection(
        name=MEMORY_COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    # chromadb.HttpClient's methods are synchronous -- calling them without
    # `await` inside async functions is intentional.
    embeddings = await embed_texts([snippet["text"] for snippet in PAST_INCIDENT_SNIPPETS])
    collection.add(
        ids=[snippet["id"] for snippet in PAST_INCIDENT_SNIPPETS],
        documents=[snippet["text"] for snippet in PAST_INCIDENT_SNIPPETS],
        embeddings=embeddings,
    )
    for snippet in PAST_INCIDENT_SNIPPETS:
        print(f"  stored [{snippet['id']}]: {snippet['text'][:60]!r}...")
    print(f"  {collection.count()} snippets, {len(embeddings[0])} numbers per vector, 1 embedding request")
    return collection


# --- Graph memory: the same node shape and helpers as 07_graph_memory.py,
# copied here so this file runs on its own.
def add_fact(graph: dict, subject: str, relation: str, obj: str) -> None:
    """Records a directed relationship: subject --relation--> obj."""
    for node_name in (subject, obj):
        if node_name not in graph:
            graph[node_name] = {"observations": [], "edges": {}}
    if relation not in graph[subject]["edges"]:
        graph[subject]["edges"][relation] = []
    graph[subject]["edges"][relation].append(obj)


def add_observation(graph: dict, node_name: str, fact_text: str) -> None:
    """Attaches a free-standing note to one node."""
    if node_name not in graph:
        graph[node_name] = {"observations": [], "edges": {}}
    graph[node_name]["observations"].append(fact_text)


def find_related(graph: dict, entity: str, relation: str) -> list:
    """One hop FORWARD. Returns a copy, so callers can't change the graph."""
    if entity not in graph:
        return []
    return list(graph[entity]["edges"].get(relation, []))


def find_incoming(graph: dict, entity: str, relation: str) -> list:
    """One hop BACKWARD: every node whose `relation` edge points at
    `entity`. Scans every node, because edges are stored on their source."""
    return [
        node_name
        for node_name, node in graph.items()
        if entity in node["edges"].get(relation, [])
    ]


def build_ops_graph() -> dict:
    """The structured, current facts the Ops Assistant keeps. Three
    groups: the EU side (payments), the US-East side (search, which shares
    the EU cache), and an APAC service connected to neither, so you can see
    that a walk only returns facts that are actually connected."""
    graph: dict = {}

    add_fact(graph, "payments-team", "owns", "payments-service")
    add_fact(graph, "Priya", "on_call_for", "payments-service")
    add_fact(graph, "payments-service", "runs_in", "eu-cluster")
    add_fact(graph, "eu-cluster", "uses", "eu-cache-layer")
    add_observation(graph, "payments-service", "had a 20-minute outage on 2026-08-01")

    add_fact(graph, "us-east-cluster", "uses", "eu-cache-layer")
    add_fact(graph, "search-service", "runs_in", "us-east-cluster")
    add_fact(graph, "Dana", "on_call_for", "search-service")

    add_fact(graph, "billing-service", "runs_in", "apac-cluster")
    add_fact(graph, "Kenji", "on_call_for", "billing-service")

    return graph


# NOTE: facts_touching answers one question: "what do we know that involves this node?" 
# It collects every edge that touches the node, whichever way the edge points.
def facts_touching(graph: dict, node_name: str) -> list[tuple[str, str, str]]:
    """
    Every edge that touches `node_name`, whatever its label and whichever
    way it points: the node's own outgoing edges, plus every edge that
    points AT it from another node.

    Returns: (source, relation, target) triples.
    """
    # your turn:
    #   1. if node_name is not in graph, return []
    #   2. OUTGOING: for each (relation, targets) in
    #      graph[node_name]["edges"].items(), add (node_name, relation, target)
    #      for every target
    #   3. INCOMING: for each (other_name, other_node) in graph.items(),
    #      skip other_name == node_name (step 2 already added its edges);
    #      for each (relation, targets) in other_node["edges"].items(), if
    #      node_name is in targets, add (other_name, relation, node_name)
    #   4. return the list of triples
    # Example: facts_touching(build_ops_graph(), "payments-service") ->
    #   [("payments-service", "runs_in", "eu-cluster"),
    #    ("payments-team", "owns", "payments-service"),
    #    ("Priya", "on_call_for", "payments-service")]
    if node_name not in graph:
        return []
    
    triples = []

    # Loop 1 (outgoing) reads the node's (e.g : payment-service) own edges:
    for relation, targets in graph[node_name]["edges"].items():
        for target in targets:
            triples.append((node_name, relation, target))

    # Loop 2 (incoming) visits every other node and asks "do your targets include payments-service?":
    for other_name, other_node in graph.items():
        # loop 1 already got this
        if other_name == node_name:
            continue  # its own edges were added above

        for relation, targets in other_node["edges"].items():
            if node_name in targets:
                triples.append((other_name, relation, node_name))
    
    return triples


def collect_facts_near(graph: dict, start_entities: list[str], max_hops: int = 2) -> list[tuple[int, str]]:
    """
    Walks outward from the start entities, in both directions and along
    any relation, for up to `max_hops` hops (a breadth-first walk), and
    collects every fact it passes. In file 7 you knew the exact path
    ("owns", then "on_call_for"); here the question can be anything, so
    the walk gathers the neighbourhood and lets the model read it.

    Returns: (hop, fact_text) pairs. Hop 0 = notes on a start entity,
    hop 1 = facts touching a start entity, hop 2 = one step further.
    """
    # your turn (a breadth-first walk, one ring of neighbours at a time):
    #   collected = []            # (hop, fact_text) pairs, the return value
    #   seen_fact_texts = set()   # so the same edge is never listed twice
    #   frontier = the start entities that exist in graph
    #   visited  = set(frontier)  # nodes already reached, never re-expanded
    #
    #   hop 0: for each start entity, add (0, f"{entity} (note): {note}")
    #          for each of its observations
    #
    #   for hop in 1 .. max_hops:
    #       next_frontier = []
    #       for each node_name in frontier:
    #           for (source, relation, target) in facts_touching(graph, node_name):
    #               fact_text = f"{source} {relation} {target}"
    #               if it is not in seen_fact_texts: remember it, and add
    #               (hop, fact_text) to collected
    #               for neighbour in (source, target): if not visited yet,
    #               mark visited, add to next_frontier, and add
    #               (hop, f"{neighbour} (note): {note}") for its observations
    #       frontier = next_frontier
    #   return collected
    #
    # From ["eu-cluster"] with max_hops=2 you should get, in this order:
    #   (1, eu-cluster uses eu-cache-layer), (1, payments-service runs_in
    #   eu-cluster), (1, payments-service (note): had a 20-minute outage...),
    #   (2, us-east-cluster uses eu-cache-layer), (2, payments-team owns
    #   payments-service), (2, Priya on_call_for payments-service)
    # Dana's on-call fact only turns up at hop 4, and Kenji is not connected at all,
    # so neither may appear.

    collected: list[tuple[int, str]] = []
    seen_fact_texts: set[str] = set()
    frontier = [entity for entity in start_entities if entity in graph]
    visited = set(frontier)

    for entity in frontier:
        for note in graph[entity]["observations"]:
            collected.append((0, f"{entity} (note): {note}"))

    for hop in range(1, max_hops + 1):
        next_frontier = []

        for node_name in frontier:

            for source, relation, target in facts_touching(graph, node_name):
                fact_text = f"{source} {relation} {target}"
                if fact_text not in seen_fact_texts:
                    seen_fact_texts.add(fact_text)
                    collected.append((hop, fact_text))

                # loops only 2 times - 1st neighbour =s ource and 2nd neighbour = target
                for neighbour in (source, target):
                    if neighbour not in visited:
                        visited.add(neighbour)
                        next_frontier.append(neighbour)
                        for note in graph[neighbour]["observations"]:
                            collected.append((hop, f"{neighbour} (note): {note}"))

        frontier = next_frontier

    return collected


# --- Entity extraction: a small alias table plus every graph node name,
# matched as whole words. Still a stand-in for a real extraction step
# (an LLM or a named-entity model), but each alias maps to the thing it
# really names, and "eu" no longer matches inside "queue".
ENTITY_ALIASES = {
    "eu cluster": "eu-cluster",
    "eu region": "eu-cluster",
    "eu": "eu-cluster",
    "us-east": "us-east-cluster",
    "payments": "payments-service",
    "search": "search-service",
    "billing": "billing-service",
}


def extract_entities(text: str, graph: dict) -> list[str]:
    """
    Finds graph entities named in `text`: any graph node name, or any
    alias from ENTITY_ALIASES, matched case-insensitively as a whole word
    (letters, digits or "-" on either side mean it is part of a longer word).

    Returns: entity names, in the order they were found, no repeats.
    """
    # your turn:
    #   1. text_lower = text.lower()
    #   2. lookup = {node_name.lower(): node_name for node_name in graph},
    #      then lookup.update(ENTITY_ALIASES)
    #   3. for each (surface_form, entity) in lookup.items(): build
    #        pattern = rf"(?<![\w-]){re.escape(surface_form)}(?![\w-])"
    #      -- (?<![\w-]) means "the character before is not a letter, digit,
    #      _ or -", and (?![\w-]) the same for the character after -- and if
    #      re.search(pattern, text_lower) matches and entity is not already
    #      found, append it
    #   4. return the found list
    # Checks: "deploy to the EU cluster ..." -> ["eu-cluster"]
    #         "the queue is backed up"      -> []   ("eu" inside "queue")
    #         "eu-cache-layer is hot"       -> ["eu-cache-layer"], not eu-cluster
    
    text_lower = text.lower()
    lookup = {node_name.lower(): node_name for node_name in graph}
    lookup.update(ENTITY_ALIASES)
    found = []
    
    for surface_form, entity in lookup.items():
        pattern = rf"(?<![\w-]){re.escape(surface_form)}(?![\w-])"
        if re.search(pattern, text_lower) and entity not in found:
            found.append(entity)
    return found


# A hardcoded pattern for the write-back step: "<Name> is now on-call for
# <service>". The name must start with a capital letter -- the (?-i:...)
# switches case-insensitivity off for that one character -- so "it is now
# on call for billing" doesn't record a person called "it". A real system
# would use an LLM extraction step here, as section 10 discusses.
NEW_ON_CALL_PATTERN = re.compile(
    r"(?P<person>(?-i:[A-Z])[\w.\-]*) is now on[- ]call for (?P<service>[\w\-]+)",
    re.IGNORECASE,
)


def record_on_call_change(graph: dict, person: str, service: str) -> list[str]:
    """
    "X is now on call for S" REPLACES whoever was on call before: their
    on_call_for edge to S is removed, X's edge is added, and a note on S
    keeps the history. (Simply adding X's edge would leave two people on
    call, and the graph would no longer say which one is current.)

    Returns: the people who were on call before the change.
    """
    # your turn:
    #   1. previous = find_incoming(graph, service, "on_call_for")
    #   2. for each old_person in previous (skip it if old_person == person):
    #        graph[old_person]["edges"]["on_call_for"].remove(service)
    #        if that list is now empty, del the "on_call_for" key
    #   3. if person not in previous: add_fact(graph, person, "on_call_for", service)
    #   4. add_observation(graph, service,
    #        f"on-call changed: {', '.join(previous) or 'nobody'} -> {person}")
    #   5. return previous
    # After record_on_call_change(graph, "Marcus", "payments-service"):
    #   find_incoming(graph, "payments-service", "on_call_for") -> ["Marcus"]
    
    previous = find_incoming(graph, service, "on_call_for")
    
    for old_person in previous:
        if old_person == person:
            continue
        graph[old_person]["edges"]["on_call_for"].remove(service)
        if not graph[old_person]["edges"]["on_call_for"]:
            del graph[old_person]["edges"]["on_call_for"]
    if person not in previous:
        add_fact(graph, person, "on_call_for", service)
    add_observation(graph, service, f"on-call changed: {', '.join(previous) or 'nobody'} -> {person}")
    return previous



async def handle_incoming_message(message: str, collection, graph: dict) -> str:
    """The full hybrid workflow from section 11, Part A:
      1. embed the message and search semantic memory for similar past chat.
      2. extract entities from the message AND from the semantic hits.
      3. walk the graph out from those entities (2 hops, both directions).
      4. synthesize one answer from both kinds of memory.
      5. write back: the message into semantic memory, and an on-call
         handoff into the graph (replacing the old edge).
    """
    # your turn: implement the five printed STEPs (print a dash banner and
    # the message first).
    #
    # STEP 1 -- semantic search: message_embedding = await embed_query(message)  (the search side);
    #   results = collection.query(query_embeddings=[message_embedding], n_results=3).
    #   For each (id, text, distance) in zip(results["ids"][0],
    #   results["documents"][0], results["distances"][0]) print the id,
    #   similarity (1 - distance) and text; collect the texts in semantic_hits.
    #
    # STEP 2 -- entities: from_message = extract_entities(message, graph);
    #   then for each hit text, extract_entities(hit_text, graph) and add any
    #   entity not already in from_message or from_hits to from_hits.
    #   entities = from_message + from_hits; print both lists.
    #
    # STEP 3 -- graph walk: near_facts = collect_facts_near(graph, entities,
    #   max_hops=2); print "hop N: fact" for each; graph_facts = the fact texts.
    #
    # STEP 4 -- synthesize: ONE chat call (chat_client, model=CHAT_MODEL, temperature=0.0)
    #   with a system prompt that labels the two memories:
    #     past conversation snippets = old chat, good for spotting a recurring
    #       PATTERN, can be out of date
    #     graph facts = CURRENT structured facts; when they disagree with an
    #       old snippet, trust the graph
    #   and lists both (one "- item" per line), plus the user message.
    #   combined_answer = response.choices[0].message.content or ""
    #
    # STEP 5 -- write back:
    #   new_id = f"mem-live-{collection.count() + 1}"  (unique: the count grows)
    #   the stored copy must be embedded the way DOCUMENTS are: if
    #   QUERY_PREFIX == DOCUMENT_PREFIX reuse message_embedding, otherwise
    #   document_embedding = await embed_document(message)
    #   collection.add(ids=[new_id], documents=[message], embeddings=[document_embedding])
    #   then on_call_match = NEW_ON_CALL_PATTERN.search(message); if it
    #   matches, call record_on_call_change(graph, person, service) and
    #   print who was removed, who was added, and
    #   find_incoming(graph, service, "on_call_for"); otherwise print that
    #   the graph is unchanged.
    #
    # Return combined_answer.
    print("-" * 60)
    print(f"INCOMING MESSAGE: {message}")
    print("-" * 60)

    print("\nSTEP 1: search semantic memory for similar past messages")
    message_embedding = await embed_query(message)
    results = collection.query(query_embeddings=[message_embedding], n_results=3)
    semantic_hits = []
    for doc_id, doc_text, distance in zip(
        results["ids"][0], results["documents"][0], results["distances"][0]
    ):
        print(f"    hit [{doc_id}] similarity={1 - distance:.4f}: {doc_text}")
        semantic_hits.append(doc_text)

    print("\nSTEP 2: extract entities from the message and from the hits")
    from_message = extract_entities(message, graph)
    from_hits = []
    for hit_text in semantic_hits:
        for entity in extract_entities(hit_text, graph):
            if entity not in from_message and entity not in from_hits:
                from_hits.append(entity)
    entities = from_message + from_hits
    print(f"    from the message: {from_message}")
    print(f"    added by the hits: {from_hits}")

    print("\nSTEP 3: walk the graph from those entities (up to 2 hops, both directions)")
    near_facts = collect_facts_near(graph, entities, max_hops=2)
    for hop, fact_text in near_facts:
        print(f"    hop {hop}: {fact_text}")
    if not near_facts:
        print("    (no graph facts found for these entities)")
    graph_facts = [fact_text for _, fact_text in near_facts]

    print("\nSTEP 4: synthesize a combined answer")
    semantic_context = "\n".join(f"- {hit}" for hit in semantic_hits) or "(none)"
    graph_context = "\n".join(f"- {fact}" for fact in graph_facts) or "(none)"
    system_prompt = (
        "You are the Ops Assistant. Answer the teammate's message using ONLY "
        "the two kinds of memory below.\n"
        "- Past conversation snippets: old chat, found because it is similar "
        "in meaning. Use them to spot a recurring PATTERN. They can be out of date.\n"
        "- Graph facts: the CURRENT structured facts (who owns what, who is "
        "on call, what runs where, what uses what). When an old snippet "
        "disagrees with a graph fact, trust the graph.\n"
        "Name any recurring pattern, and name who to contact using the graph "
        "facts. Keep it to a few sentences.\n\n"
        f"Past conversation snippets:\n{semantic_context}\n\n"
        f"Graph facts:\n{graph_context}"
    )
    response = await chat_client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )
    combined_answer = response.choices[0].message.content or ""
    print(f"    synthesized answer:\n{combined_answer}")

    print("\nSTEP 5: write back")
    new_id = f"mem-live-{collection.count() + 1}"
    # The stored copy must be embedded the way stored DOCUMENTS are embedded.
    # If the model uses the same recipe for queries and documents, the vector
    # from step 1 can be reused. If the prefixes differ, embed it again.
    if QUERY_PREFIX == DOCUMENT_PREFIX:
        document_embedding = message_embedding
        how_embedded = "reused the query vector"
    else:
        document_embedding = await embed_document(message)
        how_embedded = "embedded again as a document"
    collection.add(ids=[new_id], documents=[message], embeddings=[document_embedding])
    print(f"    wrote the message into semantic memory as [{new_id}] ({how_embedded}; {collection.count()} snippets now)")

    on_call_match = NEW_ON_CALL_PATTERN.search(message)
    if on_call_match:
        person = on_call_match.group("person")
        service = on_call_match.group("service")
        previous = record_on_call_change(graph, person, service)
        print(f"    on-call handoff found -> record_on_call_change(graph, {person!r}, {service!r})")
        print(f"    removed: {previous} on_call_for {service}   added: {person} on_call_for {service}")
        print(f"    now on call for {service}: {find_incoming(graph, service, 'on_call_for')}")
    else:
        print("    no on-call handoff in this message -- graph unchanged")

    return combined_answer



# --- OS-inspired paging (section 11, Part B). The context window is RAM
# (small, what the model sees), the archive is disk (big, outside the
# prompt). page_out moves turns OUT of the active context; page_in finds
# archived turns by keyword and puts them back IN. Here a fixed rule
# decides when to page; in MemGPT-style systems (Letta) the model itself
# decides, by calling tools such as archival_memory_insert and
# archival_memory_search.
CONTEXT_BUDGET_WORDS = 50


def context_word_count(active_context: list[str]) -> int:
    """How full the 'RAM' is, counted in words (a stand-in for tokens)."""
    return sum(len(turn.split()) for turn in active_context)


def page_out(active_context: list[str], archive: list[dict], topic: str, turn_count: int) -> None:
    """
    Moves the OLDEST `turn_count` turns out of the active context and into
    the archive under a topic label. The turns are really removed from the
    list, so the context gets smaller.
    """
    # your turn:
    #   1. paged_turns = active_context[:turn_count]
    #   2. del active_context[:turn_count]   -- removes them from the SAME
    #      list the caller holds, so the context really shrinks
    #   3. archive.append({"topic": topic, "text": " | ".join(paged_turns)})
    #   4. print how many turns were moved and under which topic
    paged_turns = active_context[:turn_count]
    del active_context[:turn_count]
    archive.append({"topic": topic, "text": " | ".join(paged_turns)})
    print(f"[page_out] moved {len(paged_turns)} turns to the archive under topic={topic!r}")


def page_in(active_context: list[str], archive: list[dict], query: str) -> list[str]:
    """
    Finds archived entries that share a word with `query` (in the topic
    or the text, case-insensitive), appends each one back onto the active
    context, and returns them. Nothing found -> nothing is added, and []
    is returned, so no placeholder text ever pretends to be a memory.
    """
    # your turn:
    #   1. query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
    #   2. for each entry in archive: entry_words = the same split of
    #      f"{entry['topic']} {entry['text']}".lower(); if the two sets
    #      share any word (query_words & entry_words), build
    #      f"[recalled: {entry['topic']}] {entry['text']}", append it to
    #      active_context, and add it to a `recalled` list
    #   3. print how many entries were put back, and return `recalled`
    #      (an empty list when nothing matched -- never a placeholder string)
    query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
    recalled = []
    for entry in archive:
        entry_words = set(re.findall(r"[a-z0-9]+", f"{entry['topic']} {entry['text']}".lower()))
        if query_words & entry_words:
            recalled_turn = f"[recalled: {entry['topic']}] {entry['text']}"
            active_context.append(recalled_turn)
            recalled.append(recalled_turn)
    print(f"[page_in] query={query!r} -> {len(recalled)} archived entr{'y' if len(recalled) == 1 else 'ies'} put back")
    return recalled



def run_paging_demo() -> None:
    """The section 11 dry run, with a real context list: a resolved DNS
    sub-thread fills the context, new turns push it over budget, the old
    turns are paged out, and a later DNS question pages them back in."""
    print("-" * 60)
    print(f"OS-INSPIRED PAGING DEMO (budget: {CONTEXT_BUDGET_WORDS} words of active context)")
    print("-" * 60)
    active_context = [
        "user: payments API is throwing connection pool exhausted errors",
        "assistant: pool size looks fine, but connections are timing out on DNS lookups",
        "user: so the pool was never the problem?",
        "assistant: right, connection pool exhaustion ruled out, root cause was a DNS misconfiguration",
    ]
    archive: list[dict] = []
    print(f"4 turns about the DB incident: {context_word_count(active_context)} words in context")

    active_context.append("user: unrelated, can you summarize yesterday's deploys?")
    active_context.append("assistant: three deploys yesterday, all green, no rollbacks")
    print(f"2 new turns arrive: {context_word_count(active_context)} words "
          f"(over the {CONTEXT_BUDGET_WORDS}-word budget: {context_word_count(active_context) > CONTEXT_BUDGET_WORDS})")

    if context_word_count(active_context) > CONTEXT_BUDGET_WORDS:
        page_out(active_context, archive, topic="db-connection-incident", turn_count=4)
    print(f"after page_out: {context_word_count(active_context)} words, {len(active_context)} turns in context, "
          f"{len(archive)} entry in the archive")

    print("\n...later...")
    active_context.append("user: DNS errors again on the search API, seen this before?")
    page_in(active_context, archive, query="DNS")
    print(f"after page_in('DNS'): {context_word_count(active_context)} words; the last turn in context is now:")
    print(f"  {active_context[-1]}")

    page_in(active_context, archive, query="kubernetes")
    print(f"after page_in('kubernetes'): still {len(active_context)} turns -- nothing matched, nothing added")


async def main() -> None:
    """Entry point: reset semantic memory, build the graph, run the paging
    demo, then push three messages through the hybrid workflow."""
    # your turn:
    #   0. print the two providers: f"Chat model: {CHAT_PROVIDER} ({CHAT_MODEL})
    #      Embedding model: {EMBEDDING_PROVIDER} ({EMBEDDING_MODEL})"
    #   1. collection = await reset_semantic_memory()
    #   2. graph = build_ops_graph(); print how many nodes, and who is on
    #      call for payments-service (find_incoming)
    #   3. run_paging_demo()
    #   4. await handle_incoming_message(message, collection, graph) for
    #      these three messages, in order:
    #        "deploy to the EU cluster is timing out again, third time this month."
    #        "Marcus is now on-call for payments-service."
    #        "who should I page about payments-service right now?"
    print(f"Chat model: {CHAT_PROVIDER} ({CHAT_MODEL})   Embedding model: {EMBEDDING_PROVIDER} ({EMBEDDING_MODEL})")
    collection = await reset_semantic_memory()
    graph = build_ops_graph()
    print(f"Graph built: {len(graph)} nodes. Now on call for payments-service: "
          f"{find_incoming(graph, 'payments-service', 'on_call_for')}")

    run_paging_demo()

    # 1. The notes' own example: semantic memory finds the cold-weather
    #    pattern; the graph supplies who is on call and what else is
    #    connected to the EU cluster.
    await handle_incoming_message(
        "deploy to the EU cluster is timing out again, third time this month.", collection, graph
    )
    # 2. An on-call handoff: written back into BOTH stores.
    await handle_incoming_message("Marcus is now on-call for payments-service.", collection, graph)
    # 3. Old chat now says both "moved to Priya" and "Marcus is now
    #    on-call"; only the graph says which one is current.
    await handle_incoming_message(
        "who should I page about payments-service right now?", collection, graph
    )


if __name__ == "__main__":
    asyncio.run(main())


# TERMINAL OUTPUT

# python 08_hybrid_memory_architecture.py
# Chat model: gemini (gemini-3.5-flash-lite)   Embedding model: ollama (qwen3-embedding:0.6b)
# ------------------------------------------------------------
# Resetting semantic memory and storing the seed snippets...
#   stored [mem-1]: "EU deploys keep failing whenever it's below freezing there, "...
#   stored [mem-2]: 'cold snap in the EU region again, deploys flaking'...
#   stored [mem-3]: 'payments-service on-call rotation moved to Priya this week a'...
#   stored [mem-4]: 'restarted the connection pool for payments after ECONNREFUSE'...
#   stored [mem-5]: 'reminder: the EU cluster shares a caching layer with the US-'...
#   5 snippets, 1024 numbers per vector, 1 embedding request
# Graph built: 11 nodes. Now on call for payments-service: ['Priya']
# ------------------------------------------------------------
# OS-INSPIRED PAGING DEMO (budget: 50 words of active context)
# ------------------------------------------------------------
# 4 turns about the DB incident: 43 words in context
# 2 new turns arrive: 58 words (over the 50-word budget: True)
# [page_out] moved 4 turns to the archive under topic='db-connection-incident'
# after page_out: 15 words, 2 turns in context, 1 entry in the archive

# ...later...
# [page_in] query='DNS' -> 1 archived entry put back
# after page_in('DNS'): 74 words; the last turn in context is now:
#   [recalled: db-connection-incident] user: payments API is throwing connection pool exhausted errors | assistant:pool size looks fine, but connections are timing out on DNS lookups | user: so the pool was never the problem? | assistant: right, connection pool exhaustion ruled out, root cause was a DNS misconfiguration
# [page_in] query='kubernetes' -> 0 archived entries put back
# after page_in('kubernetes'): still 4 turns -- nothing matched, nothing added
# ------------------------------------------------------------
# INCOMING MESSAGE: deploy to the EU cluster is timing out again, third time this month.
# ------------------------------------------------------------

# STEP 1: search semantic memory for similar past messages
#     hit [mem-5] similarity=0.7395: reminder: the EU cluster shares a caching layer with the US-East cluster, so EU slowdowns can bleed into US traffic
#     hit [mem-1] similarity=0.6418: EU deploys keep failing whenever it's below freezing there, something about the data-center cooling throttling network I/O
#     hit [mem-2] similarity=0.6256: cold snap in the EU region again, deploys flaking

# STEP 2: extract entities from the message and from the hits
#     from the message: ['eu-cluster']
#     added by the hits: ['us-east-cluster']

# STEP 3: walk the graph from those entities (up to 2 hops, both directions)
#     hop 1: eu-cluster uses eu-cache-layer
#     hop 1: payments-service runs_in eu-cluster
#     hop 1: payments-service (note): had a 20-minute outage on 2026-08-01
#     hop 1: us-east-cluster uses eu-cache-layer
#     hop 1: search-service runs_in us-east-cluster
#     hop 2: payments-team owns payments-service
#     hop 2: Priya on_call_for payments-service
#     hop 2: Dana on_call_for search-service

# STEP 4: synthesize a combined answer
#     synthesized answer:
# There is a recurring pattern where EU deploys fail or flake during cold snaps because the data-center cooling throttles network I/O. Additionally, the EU cluster shares a caching layer with US-East, which can cause slowdowns tobleed over. You should contact Priya, who is on call for the payments-service running in the EU cluster.

# STEP 5: write back
#     wrote the message into semantic memory as [mem-live-6] (embedded again as a document; 6 snippets now)
#     no on-call handoff in this message -- graph unchanged
# ------------------------------------------------------------
# INCOMING MESSAGE: Marcus is now on-call for payments-service.
# ------------------------------------------------------------

# STEP 1: search semantic memory for similar past messages
#     hit [mem-3] similarity=0.6996: payments-service on-call rotation moved to Priya this week after Marcus's shift ended
#     hit [mem-4] similarity=0.4039: restarted the connection pool for payments after ECONNREFUSED errors this morning
#     hit [mem-5] similarity=0.3730: reminder: the EU cluster shares a caching layer with the US-East cluster, so EU slowdowns can bleed into US traffic

# STEP 2: extract entities from the message and from the hits
#     from the message: ['payments-service']
#     added by the hits: ['Priya', 'eu-cluster', 'us-east-cluster']

# STEP 3: walk the graph from those entities (up to 2 hops, both directions)
#     hop 0: payments-service (note): had a 20-minute outage on 2026-08-01
#     hop 1: payments-service runs_in eu-cluster
#     hop 1: payments-team owns payments-service
#     hop 1: Priya on_call_for payments-service
#     hop 1: eu-cluster uses eu-cache-layer
#     hop 1: us-east-cluster uses eu-cache-layer
#     hop 1: search-service runs_in us-east-cluster
#     hop 2: Dana on_call_for search-service

# STEP 4: synthesize a combined answer
#     synthesized answer:
# The graph shows that Priya is currently on-call for payments-service, following the recurring pattern where the on-call rotation shifts between team members. Please contact Priya using the graph facts.

# STEP 5: write back
#     wrote the message into semantic memory as [mem-live-7] (embedded again as a document; 7 snippets now)
#     on-call handoff found -> record_on_call_change(graph, 'Marcus', 'payments-service')
#     removed: ['Priya'] on_call_for payments-service   added: Marcus on_call_for payments-service
#     now on call for payments-service: ['Marcus']
# ------------------------------------------------------------
# INCOMING MESSAGE: who should I page about payments-service right now?
# ------------------------------------------------------------

# STEP 1: search semantic memory for similar past messages
#     hit [mem-3] similarity=0.6081: payments-service on-call rotation moved to Priya this week after Marcus's shift ended
#     hit [mem-live-7] similarity=0.5909: Marcus is now on-call for payments-service.
#     hit [mem-4] similarity=0.4705: restarted the connection pool for payments after ECONNREFUSED errors this morning

# STEP 2: extract entities from the message and from the hits
#     from the message: ['payments-service']
#     added by the hits: ['Priya', 'Marcus']

# STEP 3: walk the graph from those entities (up to 2 hops, both directions)
#     hop 0: payments-service (note): had a 20-minute outage on 2026-08-01
#     hop 0: payments-service (note): on-call changed: Priya -> Marcus
#     hop 1: payments-service runs_in eu-cluster
#     hop 1: payments-team owns payments-service
#     hop 1: Marcus on_call_for payments-service
#     hop 2: eu-cluster uses eu-cache-layer

# STEP 4: synthesize a combined answer
#     synthesized answer:
# Based on the recurring pattern of connection issues, you should page Marcus, who is currently on-call for `payments-service`.

# STEP 5: write back
#     wrote the message into semantic memory as [mem-live-8] (embedded again as a document; 8 snippets now)
#     no on-call handoff in this message -- graph unchanged

