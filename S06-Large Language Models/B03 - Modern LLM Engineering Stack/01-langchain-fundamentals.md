# Topic 1 — LangChain Fundamentals

## Why This Topic

LangChain is the vocabulary layer that almost every other tool in this folder
builds on (LangGraph, agent frameworks, RAG pipelines all reuse its prompts,
output parsers, retrievers, and the LangChain Expression Language, LCEL).
Even though the ecosystem is moving toward LangGraph for orchestration, you
still construct individual nodes using LangChain primitives, so this is the
right starting point.

## Prerequisites

Comfort with B02 chapters 6-8 (prompt engineering, advanced text generation,
semantic search/RAG) — LangChain formalizes patterns you've already touched
manually.

## Outline

1. **Models & Messages** — `ChatModel` interface, `HumanMessage`,
   `AIMessage`, `SystemMessage`; connecting to a local model (Ollama) vs an
   API model, and why the interface is unified across providers.
2. **Prompt Templates** — `PromptTemplate` / `ChatPromptTemplate`, partial
   variables, few-shot prompt templates built from example selectors.
3. **Output Parsers** — `StrOutputParser`, `JsonOutputParser`,
   `PydanticOutputParser`; why parsing matters for chaining steps reliably.
4. **LangChain Expression Language (LCEL)** — the `|` pipe operator, how a
   chain is really a composed `Runnable`, `RunnableLambda`,
   `RunnableParallel`, `RunnablePassthrough`. Dry-run tracing what data flows
   through each `|` stage.
5. **Memory** — conversation buffer memory, summary memory, and why LangChain
   has been moving memory responsibility into LangGraph's checkpointer
   (sets up Topic 2).
6. **Retrievers as Runnables** — wrapping a vector store (from B02 ch08) as a
   `Retriever` and composing it into an LCEL chain — a minimal RAG chain in
   ~10 lines.
7. **Tools** — `@tool` decorator, binding tools to a chat model
   (`bind_tools`), inspecting tool-call objects in the model response (sets
   up Topics 3 and 7).

## Planned Deliverables

- `code/template/langchain-fundamentals.ipynb` — walks through sections 1-7
  with worked examples for 1-4 and 6, and **exercise cells** for 5 (build a
  summary-memory chatbot) and 7 (define two custom tools and inspect the
  model's tool-call output).
- `code/solutions/langchain-fundamentals.ipynb` — copy of the template for
  you to solve.
- `notes/01-langchain-fundamentals.md` — intuition + dry-run for LCEL
  composition (how `|` actually threads a dict/string through each
  `Runnable.invoke`).
