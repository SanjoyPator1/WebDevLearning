# Topic 7 — Structured Outputs & Tool/Function Calling

## Why This Topic

Every agent (Topics 2-4) and every advanced RAG pipeline (Topic 5) depends on
the model returning data in a *predictable shape* — a tool call with the
right arguments, or a JSON object matching a schema — rather than free-form
prose you have to regex out. This topic covers how that reliability is
actually achieved: JSON mode, constrained decoding/grammars, and Pydantic
schema validation, plus how tool-calling differs subtly across providers
(OpenAI, Anthropic, open models via Ollama).

## Prerequisites

Topic 1 (saw `bind_tools` and `PydanticOutputParser` briefly).

## Outline

1. **The Reliability Problem** — demonstrate the failure mode first: ask a
   model to "return JSON" with a plain prompt and show how it occasionally
   adds prose, markdown fences, or malformed JSON.
2. **JSON Mode / Constrained Decoding** — provider-level guarantees (e.g.
   `response_format={"type": "json_object"}`) vs grammar-constrained decoding
   (used by local serving engines) that makes invalid tokens *impossible*,
   not just unlikely.
3. **Pydantic Schemas as Contracts** — defining a `BaseModel`, generating a
   JSON schema from it, and using `with_structured_output()` so the chain
   returns a validated Python object directly.
4. **Tool/Function Calling Mechanics** — the actual message format a model
   returns for a tool call (dry-run: show the raw JSON of a tool-call message
   from Anthropic vs OpenAI side-by-side, note the structural differences),
   and how LangChain normalizes both into one interface.
5. **Parallel & Nested Tool Calls** — handling a model response that requests
   multiple tool calls in one turn, and tools whose arguments are themselves
   structured objects.
6. **Validation & Repair Loops** — what to do when structured output still
   fails validation: retry with the validation error appended to the prompt
   ("self-healing" output parsing).

## Planned Deliverables

- `code/template/structured-outputs-and-tool-calling.ipynb` — sections 1-4
  built with side-by-side provider comparisons; **exercise cells** for
  section 5 (handle a multi-tool-call response end to end) and section 6
  (implement a retry-with-error-feedback loop).
- `code/solutions/` — copy of the template.
- `notes/07-structured-outputs-and-tool-calling.md` — side-by-side raw JSON
  of tool-call messages across providers, annotated.
