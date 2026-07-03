# Topic 8 — LLM Evaluation & Observability

## Why This Topic

"It worked when I tried it" doesn't scale. By 2026, evaluation (testing
outputs against criteria, e.g. in CI) and observability (tracing what happens
in production: latency, cost, intermediate steps) are treated as standard
parts of the stack — tools like Langfuse, LangSmith, RAGAS, and "LLM-as-judge"
patterns. This topic builds a small evaluation harness for the agents/RAG
pipelines built in Topics 2-5, so you can quantify whether a change actually
improved things.

## Prerequisites

Topic 5 (Advanced RAG) — RAGAS metrics are most meaningful applied to a RAG
pipeline you've already built.

## Outline

1. **Evaluation vs Observability** — the distinction: evaluation = offline,
   pass/fail-style testing during development; observability = online tracing
   of production behavior (latency, token cost, error rates).
2. **Tracing a Chain/Graph** — instrumenting a LangGraph agent (Topic 2) with
   tracing (Langfuse, self-hostable) and inspecting a full trace: every LLM
   call, tool call, and intermediate state, with token counts and latency per
   step.
3. **RAG-Specific Metrics (RAGAS)** — faithfulness (is the answer supported by
   retrieved context?), answer relevance, context precision/recall; compute
   these by hand on one tiny example (3 retrieved chunks, 1 generated answer)
   before running RAGAS itself.
4. **LLM-as-Judge** — using a second LLM call to score outputs against a
   rubric; known pitfalls (self-preference bias, position bias in pairwise
   comparisons) and mitigations (randomizing order, using a different model
   as judge).
5. **Building a Regression Test Set** — curating a small set of
   (input, expected-properties) pairs for the agents built so far, and
   wiring them into a simple pass/fail eval script — a minimal "CI for
   prompts."
6. **Cost & Latency Tracking** — aggregating token usage/cost across a traced
   run; identifying the most expensive step in a multi-step agent.

## Planned Deliverables

- `code/template/llm-evaluation-and-observability.ipynb` — sections 1-4 built
  using the Topic 5 RAG pipeline as the system under test; **exercise cells**
  for section 5 (build a 5-10 example regression set for one of your agents)
  and section 6 (cost breakdown of a Topic 2 multi-agent run).
- `code/solutions/` — copy of the template.
- `notes/08-llm-evaluation-and-observability.md` — by-hand RAGAS metric
  dry-run (faithfulness/precision/recall on the 3-chunk example), plus a
  diagram of the trace tree for one agent run.
