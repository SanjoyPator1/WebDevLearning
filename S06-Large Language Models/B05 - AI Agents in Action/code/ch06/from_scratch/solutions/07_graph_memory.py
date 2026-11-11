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

import json
from pathlib import Path

# EXAMPLE Graph data
# graph = {
#   "payments-team":    {"observations": [],
#                        "edges": {"owns": ["payments-service"]}},

#   "payments-service": {"observations": ["had a 20-minute outage on 2026-08-01"],
#                        "edges": {}},

#   "Priya":            {"observations": [],
#                        "edges": {"member_of": ["payments-team"],
#                                  "on_call_for": ["payments-team"]}},

#   "Alice":            {"observations": [],
#                        "edges": {"member_of": ["payments-team"],
#                                  "reports_to": ["Priya"]}},
# }

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

    # relation is the variable e.g add_fact i.e. key in edges of that subject
    if relation not in graph[subject]["edges"]:
        # create an empty relation for this subject edges
        graph[subject]["edges"][relation] = []

    # add the new object i.e. target node for this subjects -> edges relation []
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
    
    if entity not in graph:
        return []

    # list returns a copy instead of the original graph
    return list(graph[entity]["edges"].get(relation,[]))


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
    return [
        node_name
        for node_name, node_value in graph.items()
        # entity is the target node and relation is the edge name
        if entity in node_value["edges"].get(relation,[])
    ]


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
    
    # first hop result - what the relation1 gives for the entity
    # first hop contains all the node thats gets connected to entity by edge relation1

    # NOTE: only the second hop should be found by 2 hop using relation 1 and 2
    # entity ──relation1──► intermediate nodes ──relation2──► second-hop nodes
    #                   (stepping stones,                 (the ONLY thing
    #                    not returned)                     we return)

    first_hop_results = walk_one_hop(graph, entity, relation1, direction1)

    # start with second hop result empty
    second_hop_results = []

    # we will loop through all the intermediate 
    for intermediate_node in first_hop_results:

        # do the second hop and loop through it
        for found_node in walk_one_hop(graph, intermediate_node, relation2, direction2):
            # to remove dublication
            if found_node not in second_hop_results:
                # add the found node in the second hop result list
                second_hop_results.append(found_node)

    return second_hop_results


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
    graph: dict = {}

    add_fact(graph, "payments-team", "owns", "payments-service")
    add_fact(graph, "Priya", "member_of", "payments-team")
    add_fact(graph, "Alice", "member_of", "payments-team")
    add_fact(graph, "Priya", "on_call_for", "payments-team")
    add_fact(graph, "Alice", "reports_to", "Priya")

    add_observation(graph, "payments-service", "had a 20-minute outage on 2026-08-01")

    return graph


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
    
    print("-" * 60)
    print("TWO-HOP DEMO A (forward, forward): who does Alice report to,")
    print("and which team is that person on call for?")
    print("-" * 60)
    hop_1 = find_related(graph, "Alice", "reports_to")
    print("Hop 1 -- find_related(graph, 'Alice', 'reports_to')")
    print(f"         -> {hop_1}      (Alice --reports_to--> Priya)")
    
    hop_2 = find_related(graph, hop_1[0], "on_call_for")
    print(f"Hop 2 -- find_related(graph, {hop_1[0]!r}, 'on_call_for')")
    print(f"         -> {hop_2}      (Priya --on_call_for--> payments-team)")
    
    combined = find_related_two_hops(graph, "Alice", "reports_to", "on_call_for")
    print(f"One call: find_related_two_hops(graph, 'Alice', 'reports_to', 'on_call_for') -> {combined}")


    print("-" * 60)
    print("TWO-HOP DEMO B (backward, backward): who's on call for the")
    print("team that owns payments-service?")
    print("-" * 60)
    forward_try = find_related(graph, "payments-service", "owns")
    print("First, the obvious forward walk finds nothing, because the 'owns' edge is")
    print("stored on payments-team, pointing AT payments-service:")
    print(f"         find_related(graph, 'payments-service', 'owns') -> {forward_try}")
    
    hop_1 = find_incoming(graph, "payments-service", "owns")
    print("Hop 1 -- find_incoming(graph, 'payments-service', 'owns')")
    print(f"         -> {hop_1}      (read 'payments-team --owns--> payments-service' backward)")
    if not hop_1:
        print("Hop 1 found nothing -- cannot take hop 2.")
        return
    
    owning_team = hop_1[0]
    hop_2 = find_incoming(graph, owning_team, "on_call_for")
    print(f"Hop 2 -- find_incoming(graph, {owning_team!r}, 'on_call_for')")
    print(f"         -> {hop_2}      (read 'Priya --on_call_for--> payments-team' backward)")
    combined = find_related_two_hops(
        graph, "payments-service", "owns", "on_call_for", direction1="in", direction2="in"
    )
    print("One call: find_related_two_hops(graph, 'payments-service', 'owns', 'on_call_for',")
    print(f"          direction1='in', direction2='in') -> {combined}")
    print(f"Answer: {combined[0] if combined else 'not found'}")
    print(
        "No similarity scoring anywhere -- the answer dropped out because the two "
        "facts already existed as edges, and the traversal followed them backward."
    )


    print("-" * 60)
    print("TWO-HOP DEMO C (forward, then backward): who's on call for Alice's team?")
    print("-" * 60)
    hop_1 = find_related(graph, "Alice", "member_of")
    print(f"Hop 1 -- find_related(graph, 'Alice', 'member_of')            -> {hop_1}")
    hop_2 = find_incoming(graph, hop_1[0], "on_call_for")
    print(f"Hop 2 -- find_incoming(graph, {hop_1[0]!r}, 'on_call_for') -> {hop_2}")




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
    print("-" * 60)
    print("ENTITY RESOLUTION FAILURE MODE DEMO")
    print("-" * 60)

    entity_resolution_demo_graph: dict = {}
    # An early conversation introduces her by full name...
    add_fact(entity_resolution_demo_graph, "Priya K.", "on_call_for", "payments-team")
    # ...weeks later, a different conversation uses just her first name.
    add_fact(entity_resolution_demo_graph, "Priya", "handling", "incident-482")

    print("Facts stored:")
    print(f"  'Priya K.' --on_call_for--> payments-team")
    print(f"  'Priya'    --handling-----> incident-482")

    lookup_result = find_related(entity_resolution_demo_graph, "Priya", "on_call_for")
    print("-" * 60)
    print(f"find_related(graph, 'Priya', 'on_call_for') -> {lookup_result}")
    print(
        "Note: this returns an empty list even though 'Priya K.' has an "
        "on_call_for edge to payments-team in this very same graph. "
        "'Priya K.' and 'Priya' are two different dictionary keys -- "
        "add_fact and find_related never compare or merge strings, so a "
        "traversal that starts from 'Priya' has no way of knowing "
        "'Priya K.' is the same person. This is exactly the "
        "entity-resolution gap section 10 names: fixing it requires an "
        "explicit resolution/merge step, not a smarter query."
    )


def save_graph(graph: dict, file_path: Path) -> None:
    """
    Writes the whole graph to a JSON file. The dict is already made of
    strings, lists and dicts, so json.dump stores it exactly as it is.
    Writes to a temporary file first and then renames it over the real
    one, so a crash halfway through never leaves a half-written file.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with open(temporary_path, "w", encoding="utf-8") as file_handle:
        json.dump(graph, file_handle, indent=2)
    temporary_path.replace(file_path)


def load_graph(file_path: Path) -> dict:
    """
    Reads a graph saved by save_graph. A missing file means nothing has
    been remembered yet, so it returns an empty graph instead of failing.
    """
    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as file_handle:
        return json.load(file_handle)


def run_persistence_demo(graph: dict, file_path: Path) -> None:
    """Shows the graph surviving a restart: session 1 saves it, session 2
    loads it from disk, answers the two-hop question from the loaded copy,
    learns one new fact and saves again, and session 3 loads that new
    fact back."""
    display_path = f"{file_path.parent.name}/{file_path.name}"

    print("-" * 60)
    print("PERSISTENCE DEMO: does the memory survive a restart?")
    print("-" * 60)
    print(f"Session 1 -- save_graph(graph, {display_path!r})")
    save_graph(graph, file_path)
    print(f"  wrote {len(graph)} nodes, {file_path.stat().st_size} bytes. The file on disk:")
    print(file_path.read_text(encoding="utf-8"))
    print("  (imagine the program stops here: session 2 reads ONLY the file)")

    print(f"Session 2 -- load_graph({display_path!r})")
    loaded_graph = load_graph(file_path)
    print(f"  loaded {len(loaded_graph)} nodes; same contents as what was saved: {loaded_graph == graph}")
    print(f"  but a brand-new dict built from the file, not the old one: (loaded_graph is graph) = {loaded_graph is graph}")
    answer = find_related_two_hops(
        loaded_graph, "payments-service", "owns", "on_call_for", direction1="in", direction2="in"
    )
    print(f"  who's on call for the team that owns payments-service? -> {answer}")
    print("  a new fact comes up in this conversation: Bob joined payments-team")
    add_fact(loaded_graph, "Bob", "member_of", "payments-team")
    save_graph(loaded_graph, file_path)
    print(f"  saved again: {len(loaded_graph)} nodes now")

    print(f"Session 3 -- load_graph({display_path!r})")
    reloaded_graph = load_graph(file_path)
    members = find_incoming(reloaded_graph, "payments-team", "member_of")
    print(f"  find_incoming(graph, 'payments-team', 'member_of') -> {members}")
    print(
        "Bob was learned in session 2 and is still known in session 3. Each "
        "run of this script rebuilds session 1 from scratch, so running it "
        "again gives the same output instead of adding Bob twice."
    )

    print(f"Missing file -> load_graph returns {load_graph(file_path.with_name('does_not_exist.json'))}")


def main() -> None:
    """Entry point: build the graph, show how two nodes are stored, then
    run both demos."""
    # your turn: build the graph and print the stored shape of two nodes
    # with json.dumps(..., indent=2): "payments-service" (it has an
    # observation and NO outgoing edges) and "payments-team" (the "owns"
    # edge is stored here). Then call run_two_hop_demo(graph) and
    # run_entity_resolution_demo()
    graph = build_ops_assistant_graph()
    print("Graph built. Each edge is stored on the node it points FROM.")
    print("payments-service (an observation, no outgoing edges):")
    print(json.dumps(graph["payments-service"], indent=2))
    print("payments-team (owns the service, so the edge lives here):")
    print(json.dumps(graph["payments-team"], indent=2))

    run_two_hop_demo(graph)
    run_entity_resolution_demo()
    run_persistence_demo(graph, GRAPH_FILE_PATH)


if __name__ == "__main__":
    main()


# TERMINAL OUTPUT

# python 07_graph_memory.py 
# Graph built. Each edge is stored on the node it points FROM.
# payments-service (an observation, no outgoing edges):
# {
#   "observations": [
#     "had a 20-minute outage on 2026-08-01"
#   ],
#   "edges": {}
# }
# payments-team (owns the service, so the edge lives here):
# {
#   "observations": [],
#   "edges": {
#     "owns": [
#       "payments-service"
#     ]
#   }
# }
# ------------------------------------------------------------
# TWO-HOP DEMO A (forward, forward): who does Alice report to,
# and which team is that person on call for?
# ------------------------------------------------------------
# Hop 1 -- find_related(graph, 'Alice', 'reports_to')
#          -> ['Priya']      (Alice --reports_to--> Priya)
# Hop 2 -- find_related(graph, 'Priya', 'on_call_for')
#          -> ['payments-team']      (Priya --on_call_for--> payments-team)
# One call: find_related_two_hops(graph, 'Alice', 'reports_to', 'on_call_for') -> ['payments-team']
# ------------------------------------------------------------
# TWO-HOP DEMO B (backward, backward): who's on call for the
# team that owns payments-service?
# ------------------------------------------------------------
# First, the obvious forward walk finds nothing, because the 'owns' edge is
# stored on payments-team, pointing AT payments-service:
#          find_related(graph, 'payments-service', 'owns') -> []
# Hop 1 -- find_incoming(graph, 'payments-service', 'owns')
#          -> ['payments-team']      (read 'payments-team --owns--> payments-service' backward)
# Hop 2 -- find_incoming(graph, 'payments-team', 'on_call_for')
#          -> ['Priya']      (read 'Priya --on_call_for--> payments-team' backward)
# One call: find_related_two_hops(graph, 'payments-service', 'owns', 'on_call_for',
#           direction1='in', direction2='in') -> ['Priya']
# Answer: Priya
# No similarity scoring anywhere -- the answer dropped out because the two facts already existed as edges, and the traversal followed them backward.
# ------------------------------------------------------------
# TWO-HOP DEMO C (forward, then backward): who's on call for Alice's team?
# ------------------------------------------------------------
# Hop 1 -- find_related(graph, 'Alice', 'member_of')            -> ['payments-team']
# Hop 2 -- find_incoming(graph, 'payments-team', 'on_call_for') -> ['Priya']
# ------------------------------------------------------------
# ENTITY RESOLUTION FAILURE MODE DEMO
# ------------------------------------------------------------
# Facts stored:
#   'Priya K.' --on_call_for--> payments-team
#   'Priya'    --handling-----> incident-482
# ------------------------------------------------------------
# find_related(graph, 'Priya', 'on_call_for') -> []
# Note: this returns an empty list even though 'Priya K.' has an on_call_for edge to payments-team in this very same graph. 'Priya K.' and 'Priya' are two different dictionary keys -- add_fact and find_related never compare or merge strings, so a traversal that starts from 'Priya' has no way of knowing 'Priya K.' is the same person. This is exactly the entity-resolution gap section 10 names: fixing it requires an explicit resolution/merge step, not a smarter query.
# ------------------------------------------------------------
# PERSISTENCE DEMO: does the memory survive a restart?
# ------------------------------------------------------------
# Session 1 -- save_graph(graph, 'data/graph_memory.json')
#   wrote 4 nodes, 578 bytes. The file on disk:
# {
#   "payments-team": {
#     "observations": [],
#     "edges": {
#       "owns": [
#         "payments-service"
#       ]
#     }
#   },
#   "payments-service": {
#     "observations": [
#       "had a 20-minute outage on 2026-08-01"
#     ],
#     "edges": {}
#   },
#   "Priya": {
#     "observations": [],
#     "edges": {
#       "member_of": [
#         "payments-team"
#       ],
#       "on_call_for": [
#         "payments-team"
#       ]
#     }
#   },
#   "Alice": {
#     "observations": [],
#     "edges": {
#       "member_of": [
#         "payments-team"
#       ],
#       "reports_to": [
#         "Priya"
#       ]
#     }
#   }
# }
#   (imagine the program stops here: session 2 reads ONLY the file)
# Session 2 -- load_graph('data/graph_memory.json')
#   loaded 4 nodes; same contents as what was saved: True
#   but a brand-new dict built from the file, not the old one: (loaded_graph is graph) = False
#   who's on call for the team that owns payments-service? -> ['Priya']
#   a new fact comes up in this conversation: Bob joined payments-team
#   saved again: 5 nodes now
# Session 3 -- load_graph('data/graph_memory.json')
#   find_incoming(graph, 'payments-team', 'member_of') -> ['Priya', 'Alice', 'Bob']
# Bob was learned in session 2 and is still known in session 3. Each run of this script rebuilds session 1 from scratch, so running it again gives the same output instead of adding Bob twice.
# Missing file -> load_graph returns {}


