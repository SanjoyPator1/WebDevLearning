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
    if node_name not in graph:
        return []
    triples = []
    for relation, targets in graph[node_name]["edges"].items():
        for target in targets:
            triples.append((node_name, relation, target))
    for other_name, other_node in graph.items():
        if other_name == node_name:
            continue  # its own edges were added above
        for relation, targets in other_node["edges"].items():
            if node_name in targets:
                triples.append((other_name, relation, node_name))
    return triples


def collect_facts_near(graph: dict, start_entities: list[str], max_hops: int = 2) -> list[str]:
    """
    Breadth-first walk: expands the start entities (hop 1), then the nodes
    they reached (hop 2), and collects each expanded node's notes and every
    fact touching it, as plain text lines with no repeats.

    Returns: e.g. ["eu-cluster uses eu-cache-layer", "payments-service (note): ...", ...]
    """
    facts = []
    frontier = [entity for entity in start_entities if entity in graph]
    visited = set(frontier)
    for _ in range(max_hops):
        next_frontier = []
        for node_name in frontier:
            for note in graph[node_name]["observations"]:
                line = f"{node_name} (note): {note}"
                if line not in facts:
                    facts.append(line)
            for source, relation, target in facts_touching(graph, node_name):
                line = f"{source} {relation} {target}"
                if line not in facts:
                    facts.append(line)
                for neighbour in (source, target):
                    if neighbour not in visited:
                        visited.add(neighbour)
                        next_frontier.append(neighbour)
        frontier = next_frontier
    return facts


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
    text_lower = text.lower()
    lookup = {node_name.lower(): node_name for node_name in graph}
    lookup.update(ENTITY_ALIASES)
    found = []
    for surface_form, entity in lookup.items():
        pattern = rf"(?<![\w-]){re.escape(surface_form)}(?![\w-])"
        if re.search(pattern, text_lower) and entity not in found:
            found.append(entity)
    return found


# --- Handoff: "<Name> is now on-call for <service>" (the name starts with
# a capital letter). A real system would use an LLM to pull facts out.
NEW_ON_CALL_PATTERN = re.compile(r"(?P<person>[A-Z]\w*) is now on-call for (?P<service>[\w-]+)")


def record_on_call_change(graph: dict, person: str, service: str) -> list[str]:
    """
    REPLACES whoever was on call for `service` with `person`: removes the
    old on_call_for edges, adds the new one, and keeps the change as a note.

    Returns: who was on call before.
    """
    previous = find_incoming(graph, service, "on_call_for")
    for old_person in previous:
        graph[old_person]["edges"]["on_call_for"].remove(service)
    add_fact(graph, person, "on_call_for", service)
    add_observation(graph, service, f"on-call changed: {', '.join(previous) or 'nobody'} -> {person}")
    return previous


async def handle_incoming_message(message: str, collection, graph: dict) -> str:
    """The five hybrid steps for one message. Returns: the model's answer."""
    print("-" * 60)
    print(f"MESSAGE: {message}")
    print("-" * 60)

    print("STEP 1: semantic search (top 3 similar past snippets)")
    [query_vector] = await embed([QUERY_INSTRUCTION + message])
    results = collection.query(query_embeddings=[query_vector], n_results=3)
    hits = results["documents"][0]
    for doc_id, text, distance in zip(results["ids"][0], hits, results["distances"][0]):
        print(f"    [{doc_id}] similarity={1 - distance:.3f}  {text}")

    print("STEP 2: entities named in the message or in the hits")
    entities = extract_entities(message + " " + " ".join(hits), graph)
    print(f"    {entities}")

    print("STEP 3: graph facts within 2 hops of those entities")
    facts = collect_facts_near(graph, entities, max_hops=2)
    for fact in facts:
        print(f"    {fact}")

    print("STEP 4: one chat call with both kinds of memory")
    snippets_text = "\n".join(f"- {hit}" for hit in hits)
    facts_text = "\n".join(f"- {fact}" for fact in facts) or "(none)"
    system_prompt = (
        "You are the Ops Assistant. Answer using ONLY the memory below, in a few sentences.\n"
        "Past chat snippets are old and can be out of date; use them to spot a recurring pattern.\n"
        "Graph facts are CURRENT; when a snippet disagrees with a graph fact, trust the graph.\n\n"
        f"Past chat snippets:\n{snippets_text}\n\nGraph facts:\n{facts_text}"
    )
    response = await chat_client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.0,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
    )
    answer = response.choices[0].message.content or ""
    print(f"    answer: {answer}")

    print("STEP 5: write back")
    new_id = f"mem-live-{collection.count() + 1}"
    [document_vector] = await embed([message])  # stored text: no instruction
    collection.add(ids=[new_id], documents=[message], embeddings=[document_vector])
    print(f"    stored the message in Chroma as [{new_id}]")
    match = NEW_ON_CALL_PATTERN.search(message)
    if match:
        previous = record_on_call_change(graph, match["person"], match["service"])
        print(f"    graph: on call for {match['service']} was {previous}, "
              f"now {find_incoming(graph, match['service'], 'on_call_for')}")
    else:
        print("    graph: unchanged (no handoff in this message)")
    return answer


async def main() -> None:
    """Fresh memory, then three messages through the hybrid workflow."""
    print(f"Chat: {CHAT_MODEL}   Embeddings: {EMBEDDING_MODEL} (local)")
    collection = await reset_semantic_memory()
    graph = build_ops_graph()
    print(f"Graph: {len(graph)} nodes, on call for payments-service: "
          f"{find_incoming(graph, 'payments-service', 'on_call_for')}")

    # 1. The pattern comes from old chat; who to call comes from the graph.
    await handle_incoming_message("deploy to the EU cluster is timing out again, third time this month.", collection, graph)
    # 2. A handoff: stored in Chroma AND it replaces the graph edge.
    await handle_incoming_message("Marcus is now on-call for payments-service.", collection, graph)
    # 3. Old chat now says both "Priya" and "Marcus"; only the graph knows which is current.
    await handle_incoming_message("who should I page about payments-service right now?", collection, graph)


if __name__ == "__main__":
    asyncio.run(main())
