# B03 — Modern LLM Engineering Stack: Roadmap

## Why This Folder Exists

Books B01 (Build a Large Language Model from Scratch) and B02 (Hands-On Large
Language Models) build the *foundations*: tokenization, attention, training a
GPT from scratch, fine-tuning, embeddings, and basic RAG. What they don't
cover is the **application layer** that most real-world LLM systems are built
on top of in 2026 — orchestration frameworks, agent runtimes, the Model
Context Protocol, production RAG patterns, evaluation/observability tooling,
and local serving.

This folder, B03, covers that application layer. Each topic gets its own plan
file (this directory) and, once we start working on it, its own subfolder
with `notes/`, `code/template/`, and `code/solutions/`.

## Working Convention

For each topic, the workflow is:

1. We discuss the topic plan file below and refine the outline if needed.
2. I create `code/template/<topic>.ipynb` — a notebook with structure,
   explanations, and **TODO/exercise cells left empty** for you to fill in.
3. I copy the template **as-is** into `code/solutions/<topic>.ipynb` — same
   empty exercise cells. This is your working copy to solve.
4. Once you've worked through it (or want to check), I create a separate
   `code/solutions/<topic>-solved.ipynb` (or a `-code-explanation.md`) as the
   reference answer key with full explanations.
5. A `notes/<topic>.md` file follows the repo's mandatory note style
   (intuition → math → dry-run → diagrams) for any conceptual material.

## Topic List & Order

| # | Topic | File | Status |
|---|-------|------|--------|
| 1 | LangChain Fundamentals | [01-langchain-fundamentals.md](01-langchain-fundamentals.md) | Done — see [01-langchain-fundamentals/](01-langchain-fundamentals/) |
| 2 | LangGraph | [02-langgraph.md](02-langgraph.md) | Done — see [02-langgraph/](02-langgraph/) |
| 3 | Model Context Protocol (MCP) | [03-model-context-protocol-mcp.md](03-model-context-protocol-mcp.md) | Done — see [03-model-context-protocol-mcp/](03-model-context-protocol-mcp/) |
| 4 | AI Agent Patterns & Frameworks | [04-ai-agent-patterns-and-frameworks.md](04-ai-agent-patterns-and-frameworks.md) | Done — see [04-ai-agent-patterns-and-frameworks/](04-ai-agent-patterns-and-frameworks/) |
| 5 | Advanced RAG | [05-advanced-rag.md](05-advanced-rag.md) | Done — see [05-advanced-rag/](05-advanced-rag/) |
| 6 | Vector Databases | [06-vector-databases.md](06-vector-databases.md) | Done — see [06-vector-databases/](06-vector-databases/) |
| 7 | Structured Outputs & Tool Calling | [07-structured-outputs-and-tool-calling.md](07-structured-outputs-and-tool-calling.md) | Not started |
| 8 | LLM Evaluation & Observability | [08-llm-evaluation-and-observability.md](08-llm-evaluation-and-observability.md) | Not started |
| 9 | Quantization & Local Serving | [09-quantization-and-local-serving.md](09-quantization-and-local-serving.md) | Not started |
| 10 | Prompt Optimization (DSPy) | [10-prompt-optimization-dspy.md](10-prompt-optimization-dspy.md) | Not started |

## Rationale for the Order

Topics 1-4 form the **orchestration & agent core**: LangChain gives the
vocabulary (prompts, parsers, retrievers, runnables), LangGraph builds stateful
graphs on top of that vocabulary, MCP is how those graphs/agents talk to tools
and external systems in a standardized way, and topic 4 zooms out to compare
agent frameworks (LangGraph vs CrewAI vs Claude Agent SDK) using everything
learned so far.

Topics 5-6 are the **retrieval layer**: advanced RAG patterns (hybrid search,
reranking, agentic/GraphRAG) and the vector database mechanics underneath them
(HNSW indexing, filtering, hybrid queries) — a natural follow-on from B02
chapter 8's basic semantic search.

Topics 7-8 are **production hygiene**: structured outputs/tool calling
(needed for reliable agents) and evaluation/observability (RAGAS,
LangSmith/Langfuse, LLM-as-judge) — how you know your system actually works.

Topics 9-10 are **efficiency & optimization**: running models locally with
quantization (GGUF/llama.cpp/Ollama/vLLM, leveraging the RTX A6000) and
automatic prompt optimization with DSPy.

## Cross-References to Existing Work

Note: `projects/P02-companion-ai` already implements RAG, memory, DPO, GRPO,
and serving **from scratch**. B03 deliberately does NOT repeat that —
instead it covers the same problem space using the standard frameworks
(LangChain/LangGraph/vector DBs/eval tools) so you understand both "how it
works under the hood" (P02) and "how it's done with the industry-standard
toolchain" (B03).
