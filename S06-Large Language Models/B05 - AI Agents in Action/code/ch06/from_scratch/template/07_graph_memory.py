# ============================================================
# LISTING: 07_graph_memory.py  (reference implementation -- FROM SCRATCH)
# BUILDING: A tiny hand-rolled graph memory -- nodes, labeled edges, and
#           observations -- answering multi-hop relationship questions end
#           to end by walking edges forward AND backward, plus a
#           demonstration of the entity-resolution failure mode that graph
#           memories are vulnerable to.
# REF: Chapter 6 notes, section 10 (Graph Memory: Remembering Relationships)
# ============================================================
#
# No embeddings, no vector database, no network calls anywhere in this
# file -- graph memory answers "who's on call for the team that owns
# payments-service" by literally walking two edges in sequence, not by
# comparing anything for similarity. The graph here is nothing more
# exotic than a dictionary of dictionaries: each node name maps to its
# own observations (free-standing facts) and its own outgoing edges
# (relationships to other nodes).
#
# An edge is stored ONCE, on the node it points FROM. Walking it
# forward is a dictionary lookup. Walking it BACKWARD ("who points at
# this node?") means scanning every node's edges, because nothing stores
# the reverse direction. This file does that scan honestly: the graph
# holds only real facts, and the backward walk is computed from them.
#
# This file also shows the OPPOSITE problem on purpose: a graph is only
# as good as the entity resolution feeding it, and the last demo shows
# exactly how two different spellings of the same person ("Priya K." and
# "Priya") silently fragment into two disconnected nodes with no warning.
#
# Finally, a memory that vanishes when the program stops is not long-term
# memory. The graph is saved to a plain JSON file and loaded back, the
# same way MCP's reference memory server keeps its graph in a JSONL file.
# The last demo restarts "from disk" and shows the answer, and a newly
# learned fact, surviving the restart.

import json
from pathlib import Path

# One shared file for solved/, template/ and solutions/: from_scratch/data/.
# It is output the script recreates, so from_scratch/.gitignore ignores it.
GRAPH_FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "graph_memory.json"


def add_fact(graph: dict, subject: str, relation: str, obj: str) -> None:
    """
    Records a directed relationship: subject --relation--> obj.
    Creates both nodes if they don't exist yet, then appends
    obj to the subject's list of edges under that relation type.
    """
    for node_name in (subject, obj):
        if node_name not in graph:
            graph[node_name] = {"observations": [], "edges": {}}

    if relation not in graph[subject]["edges"]:
        graph[subject]["edges"][relation] = []
    graph[subject]["edges"][relation].append(obj)


def add_observation(graph: dict, node_name: str, fact_text: str) -> None:
    """
    Attaches a free-standing fact to a node that isn't a
    relationship to another node -- e.g. an outage note.
    """
    if node_name not in graph:
        graph[node_name] = {"observations": [], "edges": {}}
    graph[node_name]["observations"].append(fact_text)


# Every node has the same shape: an "observations" list for free-standing
# facts, and an "edges" dict where each key is a relationship type and
# each value is a list of node names that relationship points to:
#     {"Priya": {"observations": [], "edges": {"member_of": ["payments-team"]}}}


def find_related(graph: dict, entity: str, relation: str) -> list:
    """
    Walks one edge FORWARD: returns every node that `entity` points to
    under the given relation type. Returns a copy, so a caller who changes
    the result cannot change the graph.
    """
    # your turn: if entity isn't in graph, return []; otherwise return a
    # COPY of graph[entity]["edges"].get(relation, []) -- list(...) around
    # it. (Returning the stored list itself would let a caller who appends
    # to the result silently corrupt the graph.)
    raise NotImplementedError


def find_incoming(graph: dict, entity: str, relation: str) -> list:
    """
    Walks one edge BACKWARD: returns every node whose `relation` edge
    points AT `entity`. The graph stores each edge only on the node it
    starts from, so this has to scan every node.
    """
    # your turn: loop over every (node_name, node) in graph.items() and
    # keep node_name when `entity` is in node["edges"].get(relation, [])
    # -- a list comprehension does it in one expression. No node stores
    # the reverse direction, which is why every node has to be checked.
    raise NotImplementedError


def walk_one_hop(graph: dict, entity: str, relation: str, direction: str = "out") -> list:
    """
    One hop in either direction: "out" follows the stored edge forward
    (find_related), "in" follows it backward (find_incoming).
    """
    if direction == "out":
        return find_related(graph, entity, relation)
    if direction == "in":
        return find_incoming(graph, entity, relation)
    raise ValueError(f"direction must be 'out' or 'in', got {direction!r}")


def find_related_two_hops(
    graph: dict,
    entity: str,
    relation1: str,
    relation2: str,
    direction1: str = "out",
    direction2: str = "out",
) -> list:
    """
    Walks two edges in sequence: first relation1 from entity,
    then relation2 from each resulting node. This is the shape
    a multi-hop question needs -- the output of hop one becomes
    the input to hop two. Each hop can go "out" (forward) or "in"
    (backward). The combined result has no repeats.
    """
    # your turn: use walk_one_hop (already written above) for both hops.
    #   1. first_hop_results = walk_one_hop(graph, entity, relation1, direction1)
    #   2. for EACH intermediate node, walk_one_hop(graph, node, relation2,
    #      direction2) and add every node it returns to one combined
    #      results list -- but only if it is not already in that list, so
    #      a person reached through two different teams appears once
    #   3. return the combined list
    raise NotImplementedError


def build_ops_assistant_graph() -> dict:
    """Builds the exact example graph from section 10's dry run: a
    payments team that owns payments-service, Priya as a member and the
    on-call person, Alice as a member reporting to Priya, and an
    observation about a past outage on payments-service. Only real facts
    go in: every reverse question ("who owns this service?") is answered
    by walking these same edges backward, never by storing a second,
    hand-typed copy of them."""
    # your turn: start with graph = {} and reproduce section 10's exact
    # example graph:
    #   add_fact(graph, "payments-team", "owns", "payments-service")
    #   add_fact(graph, "Priya", "member_of", "payments-team")
    #   add_fact(graph, "Alice", "member_of", "payments-team")
    #   add_fact(graph, "Priya", "on_call_for", "payments-team")
    #   add_fact(graph, "Alice", "reports_to", "Priya")
    #   add_observation(graph, "payments-service",
    #                   "had a 20-minute outage on 2026-08-01")
    # Those are ALL the facts. Do not add "owned_by" or "..._reverse"
    # edges: find_incoming answers those questions from the facts above.
    # Return the graph.
    raise NotImplementedError


def run_two_hop_demo(graph: dict) -> None:
    """Answers three two-hop questions as literal edge walks, printing
    each hop's result on the way: one that follows the stored edges
    forward, one that follows them backward, and one that mixes both."""
    # your turn: print a banner and a heading for each demo, then:
    #   DEMO A (forward, forward) "who does Alice report to, and which team
    #   is that person on call for?"
    #     hop 1: find_related(graph, "Alice", "reports_to")      -> ['Priya']
    #     hop 2: find_related(graph, <hop 1 result>, "on_call_for")
    #                                                            -> ['payments-team']
    #     then find_related_two_hops(graph, "Alice", "reports_to",
    #     "on_call_for") and print that it gives the same answer in one call
    #
    #   DEMO B (backward, backward) "who's on call for the team that owns
    #   payments-service?"
    #     first print what the obvious FORWARD walk finds:
    #       find_related(graph, "payments-service", "owns")      -> []
    #       (the "owns" edge is stored on payments-team, pointing AT the
    #        service, so nothing leaves the service)
    #     hop 1: find_incoming(graph, "payments-service", "owns")  -> ['payments-team']
    #     hop 2: find_incoming(graph, <hop 1 result>, "on_call_for") -> ['Priya']
    #     then find_related_two_hops(graph, "payments-service", "owns",
    #     "on_call_for", direction1="in", direction2="in"), and print the
    #     final answer ("Priya")
    #
    #   DEMO C (forward, then backward) "who's on call for Alice's team?"
    #     hop 1: find_related(graph, "Alice", "member_of")        -> ['payments-team']
    #     hop 2: find_incoming(graph, <hop 1 result>, "on_call_for") -> ['Priya']
    raise NotImplementedError


def run_entity_resolution_demo() -> None:
    """Demonstrates the entity-resolution failure mode from section 10:
    a fact recorded under 'Priya K.' is invisible to any traversal that
    starts from the differently-spelled key 'Priya', because nothing in
    this data structure ever merges two node names that refer to the
    same real person."""
    # your turn: build a SEPARATE, small graph (don't reuse
    # build_ops_assistant_graph()'s graph, so this doesn't collide with
    # the Priya node already defined there):
    #   add_fact(demo_graph, "Priya K.", "on_call_for", "payments-team")
    #   add_fact(demo_graph, "Priya", "handling", "incident-482")
    # then call find_related(demo_graph, "Priya", "on_call_for"), print
    # that it comes back empty, and print an explicit note explaining
    # why: "Priya K." and "Priya" are two different dictionary keys, and
    # nothing in add_fact or find_related ever merges or fuzzy-matches
    # strings, so a traversal starting from "Priya" never sees the fact
    # stored under "Priya K."
    raise NotImplementedError


def save_graph(graph: dict, file_path: Path) -> None:
    """
    Writes the whole graph to a JSON file. The dict is already made of
    strings, lists and dicts, so json.dump stores it exactly as it is.
    Writes to a temporary file first and then renames it over the real
    one, so a crash halfway through never leaves a half-written file.
    """
    # your turn:
    #   1. file_path.parent.mkdir(parents=True, exist_ok=True) -- the data/
    #      folder may not exist yet
    #   2. temporary_path = file_path.with_suffix(file_path.suffix + ".tmp")
    #   3. open temporary_path for writing (encoding="utf-8") and
    #      json.dump(graph, file_handle, indent=2)
    #   4. temporary_path.replace(file_path) -- the rename swaps the whole
    #      file in one step, so readers see the old file or the new one,
    #      never half of one
    raise NotImplementedError


def load_graph(file_path: Path) -> dict:
    """
    Reads a graph saved by save_graph. A missing file means nothing has
    been remembered yet, so it returns an empty graph instead of failing.
    """
    # your turn: if not file_path.exists(), return {}. Otherwise open it
    # (encoding="utf-8") and return json.load(file_handle).
    raise NotImplementedError


def run_persistence_demo(graph: dict, file_path: Path) -> None:
    """Shows the graph surviving a restart: session 1 saves it, session 2
    loads it from disk, answers the two-hop question from the loaded copy,
    learns one new fact and saves again, and session 3 loads that new
    fact back."""
    # your turn: print a banner, then:
    #   Session 1: save_graph(graph, file_path); print the node count, the
    #     file size (file_path.stat().st_size) and the file's text
    #     (file_path.read_text(encoding="utf-8")) so you see what is on disk
    #   Session 2: loaded_graph = load_graph(file_path)
    #     print (loaded_graph == graph)  -> True   (same contents)
    #     print (loaded_graph is graph)  -> False  (a new dict from the file)
    #     answer the demo B question from loaded_graph:
    #       find_related_two_hops(loaded_graph, "payments-service", "owns",
    #       "on_call_for", direction1="in", direction2="in")  -> ['Priya']
    #     learn a new fact: add_fact(loaded_graph, "Bob", "member_of",
    #     "payments-team"), then save_graph(loaded_graph, file_path)
    #   Session 3: reloaded_graph = load_graph(file_path)
    #     find_incoming(reloaded_graph, "payments-team", "member_of")
    #                                       -> ['Priya', 'Alice', 'Bob']
    #   Last: show load_graph on a file that doesn't exist returns {}
    #     (file_path.with_name("does_not_exist.json"))
    raise NotImplementedError


def main() -> None:
    """Entry point: build the graph, show how two nodes are stored, then
    run the three demos."""
    # your turn: build the graph and print the stored shape of two nodes
    # with json.dumps(..., indent=2): "payments-service" (it has an
    # observation and NO outgoing edges) and "payments-team" (the "owns"
    # edge is stored here). Then call run_two_hop_demo(graph),
    # run_entity_resolution_demo() and
    # run_persistence_demo(graph, GRAPH_FILE_PATH)
    raise NotImplementedError


if __name__ == "__main__":
    main()
