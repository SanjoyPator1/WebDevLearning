# Topic 2 — LangGraph

## Why This Topic

By 2026, LangGraph is the most-deployed framework for production agentic
systems (cited as holding roughly a 40% lead over alternatives in production
deployments as of March 2026). It replaces ad-hoc "while loop calling an LLM"
agent code with an explicit, typed **state graph**: nodes that read/write a
shared state object, edges (including conditional edges) that route between
them, and checkpointers that persist state so an agent can pause, resume, or
be inspected mid-run.

## Prerequisites

Topic 1 (LangChain Fundamentals) — LangGraph nodes are typically LangChain
runnables/chains.

## Outline

1. **State Schema** — defining a `TypedDict` or Pydantic model as the graph
   state; reducers (e.g. `Annotated[list, add_messages]`) and why they matter
   for fields multiple nodes write to.
2. **Nodes & Edges** — `StateGraph.add_node`, `add_edge`, `add_conditional_edges`;
   building a simple linear graph, then adding a branch.
3. **Cycles & the ReAct Loop** — building a tool-calling agent as a graph with
   a cycle (LLM node → tool node → back to LLM node) instead of a library
   black box, so the control flow is fully visible.
4. **Checkpointers & Persistence** — `MemorySaver` for dev, `SqliteSaver` /
   `PostgresSaver` for production; resuming a graph run from a thread ID;
   what's actually stored at each checkpoint (dry-run on a tiny state dict).
5. **Human-in-the-Loop** — `interrupt()`, approving/editing tool calls before
   execution, time-travel (replaying from an earlier checkpoint).
6. **Multi-Agent Graphs** — supervisor pattern (a router node dispatching to
   specialist sub-graphs) vs swarm pattern (agents handing off directly to
   each other).
7. **Streaming** — token-level and node-level streaming of graph execution,
   relevant for any chat UI.

## Planned Deliverables

- `code/template/langgraph-fundamentals.ipynb` — sections 1-4 worked through
  with a tiny "research assistant" graph (search tool + summarizer node);
  **exercise cells** for section 5 (add a human-approval interrupt before the
  search tool runs) and section 6 (extend into a 2-agent supervisor graph).
- `code/solutions/langgraph-fundamentals.ipynb` — copy of the template.
- `notes/02-langgraph.md` — diagram (Mermaid) of the state graph plus a
  dry-run table showing how the state dict mutates after each node executes.
