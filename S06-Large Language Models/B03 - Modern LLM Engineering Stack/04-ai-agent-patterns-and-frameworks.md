# Topic 4 — AI Agent Patterns & Frameworks

## Why This Topic

Topics 1-3 give you the primitives (chains, graphs, MCP tools). This topic
zooms out: what are the canonical *reasoning patterns* agents use (ReAct,
Plan-and-Execute, reflection), and how do the major frameworks differ in how
they implement them? As of 2026 the landscape is roughly: **LangGraph**
(production-grade stateful graphs, what we built in Topic 2), **CrewAI**
(role-based "crews" of agents, lowest barrier to entry for team-style
workflows), **Claude Agent SDK** (Anthropic-native, used by Claude Code
itself), and **AutoGen** (now in maintenance mode, superseded by Microsoft
Agent Framework). Picking the right tool means understanding these tradeoffs
rather than defaulting to whichever is trendiest.

## Prerequisites

Topics 1-3.

## Outline

1. **ReAct Pattern** — "Reasoning + Acting" loop (Thought → Action →
   Observation → ...); implement it manually first (no framework) on a
   2-tool problem so the pattern is transparent before any framework hides it.
2. **Plan-and-Execute** — separating a planner LLM call (produces a step
   list) from an executor loop; tradeoffs vs ReAct (fewer LLM calls, less
   adaptive).
3. **Reflection / Self-Critique** — adding a critique step that re-evaluates
   the agent's own output before returning it; when this is worth the extra
   latency/cost.
4. **Framework Tour** — same small task ("research a topic and write a
   3-bullet summary with sources") implemented three ways:
   - in **LangGraph** (reusing Topic 2's graph),
   - in **CrewAI** (role-based: a "researcher" agent + "writer" agent),
   - using the **Claude Agent SDK** directly.
5. **Comparison & Decision Framework** — a short table you fill in yourself
   (lines of code, debuggability, persistence support, multi-agent support,
   MCP/A2A support) based on what you observed in section 4.
6. **Agent-to-Agent (A2A) Protocol** — brief overview of Google's A2A
   standard for agent-to-agent communication/discovery, and how it
   complements (not competes with) MCP.

## Planned Deliverables

- `code/template/agent-patterns-and-frameworks.ipynb` — section 1-3
  implemented manually with print-narrated traces; **exercise cells** for
  section 4 (you implement the CrewAI and Claude Agent SDK versions, with the
  LangGraph version provided as a reference since it reuses Topic 2).
- `code/solutions/` — copy of the template.
- `notes/04-ai-agent-patterns-and-frameworks.md` — the comparison table from
  section 5, plus an ASCII diagram of ReAct vs Plan-and-Execute control flow.
