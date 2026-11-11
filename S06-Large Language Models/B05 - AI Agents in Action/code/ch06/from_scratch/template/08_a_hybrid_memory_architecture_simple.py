# ============================================================
# LISTING: 08_a_hybrid_memory_architecture_simple.py  (reference implementation -- FROM SCRATCH)
# BUILDING: The hybrid semantic-plus-graph memory workflow and nothing
#           else: one fixed setup, five steps, three messages.
# REF: Chapter 6 notes, section 11 (Modern Memory Architectures), Part A
# ============================================================
#
# A focused version of file 8. Same idea, without the provider switches,
# the prefix table or the paging demo.
#
#   1. semantic search finds similar past chat         (the fuzzy PATTERN)
#   2. entities are pulled from the message and those hits
#   3. the graph walks out from those entities          (the CURRENT facts)
#   4. one chat call reads both and answers
#   5. write back: the message into Chroma, and an on-call handoff
#      REPLACES the old on-call edge in the graph
#
# Setup, once:
#   docker run -d --name ch06-chroma -p 8000:8000 chromadb/chroma
#   ollama pull qwen3-embedding:0.6b      (with the Ollama app open)
#
# Calls per run: 3 Gemini chat calls (one per message) and 7 local,
# free embedding requests (1 for the seeds, then 2 per message).

import asyncio
import os
import re

import chromadb
from chromadb.errors import NotFoundError
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# --- Two clients, two jobs. The chat model WRITES the answer; the
# embedding model turns text into numbers so Chroma can compare meanings.
chat_client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
CHAT_MODEL = os.environ["GEMINI_MODEL"]

embedding_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
EMBEDDING_MODEL = "qwen3-embedding:0.6b"

# Qwen3 embedding wants this instruction in front of a SEARCH text only.
# Stored texts are embedded plain.
QUERY_INSTRUCTION = "Instruct: Given a chat message, retrieve relevant past chat messages\nQuery:"

chroma_client = chromadb.HttpClient(host="localhost", port=8000)
COLLECTION_NAME = "ops_assistant_memory_simple"


async def embed(texts: list[str]) -> list[list[float]]:
    """Turns every text into a vector, all in ONE request.
    Returns: one list of 1024 numbers per text, in the same order."""
    response = await embedding_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


# --- Semantic memory: old chat snippets.
PAST_CHAT = {
    "mem-1": "EU deploys keep failing whenever it's below freezing there, something about the data-center cooling throttling network I/O",
    "mem-2": "cold snap in the EU region again, deploys flaking",
    "mem-3": "payments-service on-call rotation moved to Priya this week after Marcus's shift ended",
    "mem-4": "restarted the connection pool for payments after ECONNREFUSED errors this morning",
    "mem-5": "reminder: the EU cluster shares a caching layer with the US-East cluster, so EU slowdowns can bleed into US traffic",
}


async def reset_semantic_memory():
    """Deletes the collection an earlier run left on the Chroma server,
    creates it fresh, and stores the 5 snippets. Every run starts the same.
    Returns: the Chroma collection."""
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except NotFoundError:
        pass  # first run: nothing to delete
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    vectors = await embed(list(PAST_CHAT.values()))  # stored texts: no instruction
    collection.add(ids=list(PAST_CHAT.keys()), documents=list(PAST_CHAT.values()), embeddings=vectors)
    print(f"Semantic memory: {collection.count()} snippets, {len(vectors[0])} numbers per vector")
    return collection


# --- Graph memory: the same node shape as file 7.
#     {"Priya": {"observations": [], "edges": {"on_call_for": ["payments-service"]}}}
def add_fact(graph: dict, subject: str, relation: str, obj: str) -> None:
    """Records subject --relation--> obj, creating both nodes if needed."""
    for node_name in (subject, obj):
        graph.setdefault(node_name, {"observations": [], "edges": {}})
    graph[subject]["edges"].setdefault(relation, []).append(obj)


def add_observation(graph: dict, node_name: str, note: str) -> None:
    """Attaches a free-standing note to a node."""
    graph.setdefault(node_name, {"observations": [], "edges": {}})
    graph[node_name]["observations"].append(note)


def find_incoming(graph: dict, entity: str, relation: str) -> list[str]:
    """Every node whose `relation` edge points AT `entity` (scans all nodes)."""
    return [name for name, node in graph.items() if entity in node["edges"].get(relation, [])]


def build_ops_graph() -> dict:
    """The current, structured facts: 8 nodes, 6 edges, 1 note. The APAC
    billing line is connected to nothing else, so no walk should reach it."""
    graph: dict = {}
    add_fact(graph, "payments-team", "owns", "payments-service")
    add_fact(graph, "Priya", "on_call_for", "payments-service")
    add_fact(graph, "payments-service", "runs_in", "eu-cluster")
    add_fact(graph, "eu-cluster", "uses", "eu-cache-layer")
    add_fact(graph, "us-east-cluster", "uses", "eu-cache-layer")
    add_fact(graph, "billing-service", "runs_in", "apac-cluster")
    add_observation(graph, "payments-service", "had a 20-minute outage on 2026-08-01")
    return graph


def facts_touching(graph: dict, node_name: str) -> list[tuple[str, str, str]]:
    """
    Every edge that touches `node_name`, whichever way it points: its own
    outgoing edges, plus every edge on another node that points AT it.

    Returns: (source, relation, target) triples.
    """
    # your turn (the same function as file 8):
    #   1. if node_name is not in graph, return []
    #   2. OUTGOING: for each (relation, targets) in
    #      graph[node_name]["edges"].items(), add (node_name, relation, target)
    #      for every target
    #   3. INCOMING: for each (other_name, other_node) in graph.items(), skip
    #      other_name == node_name; for each (relation, targets) in
    #      other_node["edges"].items(), if node_name is in targets, add
    #      (other_name, relation, node_name)
    #   4. return the list
    # Check: facts_touching(build_ops_graph(), "payments-service") ->
    #   [("payments-service", "runs_in", "eu-cluster"),
    #    ("payments-team", "owns", "payments-service"),
    #    ("Priya", "on_call_for", "payments-service")]
    raise NotImplementedError


def collect_facts_near(graph: dict, start_entities: list[str], max_hops: int = 2) -> list[str]:
    """
    Breadth-first walk: expands the start entities (hop 1), then the nodes
    they reached (hop 2), and collects each expanded node's notes and every
    fact touching it, as plain text lines with no repeats.

    Returns: e.g. ["eu-cluster uses eu-cache-layer", "payments-service (note): ...", ...]
    """
    # your turn:
    #   facts = []                       the answer; also how repeats are spotted
    #   frontier = the start entities that are in graph   (nodes to expand now)
    #   visited = set(frontier)          every node ever put on a frontier
    #   repeat max_hops times:
    #       next_frontier = []
    #       for each node_name in frontier:
    #           for each note in graph[node_name]["observations"]:
    #               add f"{node_name} (note): {note}" to facts if not already there
    #           for each (source, relation, target) in facts_touching(graph, node_name):
    #               add f"{source} {relation} {target}" to facts if not already there
    #               for neighbour in (source, target): if not in visited, add it
    #               to visited AND to next_frontier
    #       frontier = next_frontier
    #   return facts
    # Check: collect_facts_near(build_ops_graph(), ["eu-cluster"]) ->
    #   ["eu-cluster uses eu-cache-layer",
    #    "payments-service runs_in eu-cluster",
    #    "us-east-cluster uses eu-cache-layer",
    #    "payments-service (note): had a 20-minute outage on 2026-08-01",
    #    "payments-team owns payments-service",
    #    "Priya on_call_for payments-service"]
    raise NotImplementedError


# --- Entities: graph node names, plus everyday ways of saying them.
ENTITY_ALIASES = {
    "eu cluster": "eu-cluster",
    "eu region": "eu-cluster",
    "eu": "eu-cluster",
    "us-east": "us-east-cluster",
    "payments": "payments-service",
}


def extract_entities(text: str, graph: dict) -> list[str]:
    """
    Finds graph entities named in `text`, as whole words, ignoring case.
    A letter, digit, "_" or "-" right before or after a match means it is
    part of a longer word, so "eu" does not match inside "queue".

    Returns: entity names, no repeats.
    """
    # your turn (the same function as file 8):
    #   1. text_lower = text.lower()
    #   2. lookup = {node_name.lower(): node_name for node_name in graph},
    #      then lookup.update(ENTITY_ALIASES)
    #   3. for each (surface_form, entity) in lookup.items():
    #        pattern = rf"(?<![\w-]){re.escape(surface_form)}(?![\w-])"
    #      if re.search(pattern, text_lower) matches and entity is not
    #      already found, append it
    #   4. return the found list
    # Checks: "deploy to the EU cluster ..." -> ["eu-cluster"]
    #         "the queue is backed up"      -> []
    #         "eu-cache-layer is hot"       -> ["eu-cache-layer"]
    raise NotImplementedError


# --- Handoff: "<Name> is now on-call for <service>" (the name starts with
# a capital letter). A real system would use an LLM to pull facts out.
NEW_ON_CALL_PATTERN = re.compile(r"(?P<person>[A-Z]\w*) is now on-call for (?P<service>[\w-]+)")


def record_on_call_change(graph: dict, person: str, service: str) -> list[str]:
    """
    REPLACES whoever was on call for `service` with `person`: removes the
    old on_call_for edges, adds the new one, and keeps the change as a note.

    Returns: who was on call before.
    """
    # your turn:
    #   1. previous = find_incoming(graph, service, "on_call_for")
    #   2. for each old_person in previous:
    #        graph[old_person]["edges"]["on_call_for"].remove(service)
    #   3. add_fact(graph, person, "on_call_for", service)
    #   4. add_observation(graph, service,
    #        f"on-call changed: {', '.join(previous) or 'nobody'} -> {person}")
    #   5. return previous
    # Check: record_on_call_change(graph, "Marcus", "payments-service") ->
    #   ['Priya'], and afterwards
    #   find_incoming(graph, "payments-service", "on_call_for") == ['Marcus']
    raise NotImplementedError


async def handle_incoming_message(message: str, collection, graph: dict) -> str:
    """The five hybrid steps for one message. Returns: the model's answer."""
    # your turn: print a banner with the message, then print each step's
    # heading and what it produced.
    #
    # STEP 1, semantic search:
    #   [query_vector] = await embed([QUERY_INSTRUCTION + message])
    #   results = collection.query(query_embeddings=[query_vector], n_results=3)
    #   hits = results["documents"][0]
    #   print each hit with its id and similarity = 1 - distance
    #   (results["ids"][0], results["distances"][0])
    #
    # STEP 2, entities: extract_entities(message + " " + " ".join(hits), graph)
    #   (one call reads the message and the 3 hits together)
    #
    # STEP 3, graph: facts = collect_facts_near(graph, entities, max_hops=2)
    #
    # STEP 4, one chat call: build a system prompt with two labelled lists,
    #   "Past chat snippets" (the hits) and "Graph facts" (the facts, or
    #   "(none)"), plus the rule: snippets can be out of date, graph facts are
    #   current, trust the graph when they disagree. Call
    #   chat_client.chat.completions.create(model=CHAT_MODEL, temperature=0.0,
    #   messages=[system prompt, {"role": "user", "content": message}])
    #   answer = response.choices[0].message.content or ""
    #
    # STEP 5, write back:
    #   new_id = f"mem-live-{collection.count() + 1}"
    #   [document_vector] = await embed([message])   <- plain, no instruction:
    #                                                   it is stored, not searched
    #   collection.add(ids=[new_id], documents=[message], embeddings=[document_vector])
    #   match = NEW_ON_CALL_PATTERN.search(message); if it matched, call
    #   record_on_call_change(graph, match["person"], match["service"]) and
    #   print who was on call before and who is now
    #
    # return answer
    raise NotImplementedError


async def main() -> None:
    """Fresh memory, then three messages through the hybrid workflow."""
    # your turn:
    #   collection = await reset_semantic_memory()
    #   graph = build_ops_graph()
    #   print who is on call for payments-service now (find_incoming)
    #   then await handle_incoming_message(..., collection, graph) for:
    #     1. "deploy to the EU cluster is timing out again, third time this month."
    #        (the pattern comes from old chat; who to call comes from the graph)
    #     2. "Marcus is now on-call for payments-service."
    #        (stored in Chroma AND it replaces the graph edge)
    #     3. "who should I page about payments-service right now?"
    #        (old chat now says both Priya and Marcus; only the graph knows)
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
