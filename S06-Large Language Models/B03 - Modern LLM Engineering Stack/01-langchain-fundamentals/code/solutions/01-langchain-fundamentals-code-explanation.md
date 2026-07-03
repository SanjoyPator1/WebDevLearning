# Topic 1 — LangChain Fundamentals: Code Explanation

This file walks through every cell of `01-langchain-fundamentals-practice.ipynb`,
section by section, showing the actual output each cell produces and — for
the two exercise cells (Section 5 and Section 7) — the canonical
implementation with a line-by-line explanation and a dry run against the
exact numbers used in the notebook.

For the *why* behind each concept (intuition, formal notation, diagrams), see
[`../../notes/01-langchain-fundamentals.md`](../../notes/01-langchain-fundamentals.md)
and the topic plan,
[`../../../01-langchain-fundamentals.md`](../../../01-langchain-fundamentals.md).
This file stays close to the code.

---

## Table of Contents

- [1. Models & Messages](#1-models--messages)
- [2. Prompt Templates](#2-prompt-templates)
- [3. Output Parsers](#3-output-parsers)
- [4. LCEL](#4-lcel)
- [5. Memory — Exercise: `SummarizingChatMessageHistory`](#5-memory--exercise-summarizingchatmessagehistory)
- [6. Retrievers as Runnables](#6-retrievers-as-runnables)
- [7. Tools — Exercise: `add_numbers`, `reverse_text`, `execute_tool_calls`](#7-tools--exercise-add_numbers-reverse_text-execute_tool_calls)
- [Putting It All Together](#putting-it-all-together)
- [Where to Go Next](#where-to-go-next)

---

## 1. Models & Messages

```python
messages = [
    SystemMessage(content="You are a terse math tutor. Answer with just the number."),
    HumanMessage(content="What is 12 * 4?"),
]
fake_model = GenericFakeChatModel(messages=iter(["48.", "8."]))
ai_message_1 = fake_model.invoke(messages)
```

`GenericFakeChatModel(messages=iter([...]))` stores an *iterator* over
strings. Each call to `.invoke(...)` advances that iterator by one and wraps
the next string in an `AIMessage` — the input messages are completely
ignored. Output:

```
SystemMessage  | You are a terse math tutor. Answer with just the number.
HumanMessage   | What is 12 * 4?
content='48.' additional_kwargs={} response_metadata={} id='lc_run--...' tool_calls=[] invalid_tool_calls=[]
content: 48.
```

Note the extra fields on `AIMessage` even though we only constructed it from
a string: `id` (an auto-generated run id), `tool_calls=[]`,
`invalid_tool_calls=[]`. These are always present on `AIMessage` — they're
empty here because `GenericFakeChatModel` doesn't populate them, but
Section 7 shows what they look like when populated.

The second cell appends `ai_message_1` and a new `HumanMessage` to
`messages`, then calls `.invoke()` again. `fake_model`'s iterator yields
`"8."` this time — note that **the model never looked at `messages` at all**;
it would have returned `"8."` regardless of what was in the list. The third
cell calls `.invoke()` a third time, and since the iterator (`iter(["48.", "8."])`)
only had two items, Python raises `StopIteration` — caught and printed.

---

## 2. Prompt Templates

```python
translate_template = PromptTemplate.from_template(
    "Translate the following English text to {language}:\n\n{text}"
)
```

`from_template` scans the string for `{name}` tokens via Python's own
`string.Formatter` and records `input_variables = ['language', 'text']`.
`.format(language="French", text="Good morning")` is then a validated call to
`str.format(**kwargs)`:

```
Translate the following English text to French:

Good morning
```

`ChatPromptTemplate.from_messages([("system", "You are a {persona}."), ("human", "{question}")])`
builds one `PromptTemplate` per `(role, template_string)` pair internally.
`.invoke({"persona": "terse math tutor", "question": "What is 9*9?"})` formats
each one and wraps the results in the corresponding message class, returning
a `ChatPromptValue`:

```
input_variables: ['persona', 'question']
<class 'langchain_core.prompt_values.ChatPromptValue'>
SystemMessage  | You are a terse math tutor.
HumanMessage   | What is 9*9?
```

`.partial(persona="terse math tutor")` returns a **new** `ChatPromptTemplate`
whose `input_variables` no longer include `persona` — it's stored internally
and merged in automatically at `.invoke()` time:

```
input_variables: ['question']
SystemMessage  | You are a terse math tutor.
HumanMessage   | What is 7*8?
```

`FewShotPromptTemplate.format(adjective="fast")` loops over `examples`,
calling `example_prompt.format(**example)` for each dict
(`{"input": "happy", "output": "sad"}` → `"Input: happy\nOutput: sad"`, and
similarly for `"tall"/"short"`), joins them with blank lines, then appends
`suffix.format(adjective="fast")` = `"Input: fast\nOutput:"`:

```
Input: happy
Output: sad

Input: tall
Output: short

Input: fast
Output:
```

---

## 3. Output Parsers

```python
str_parser = StrOutputParser()
parsed = str_parser.invoke(AIMessage(content="The capital of France is Paris."))
print(repr(parsed))
print("isinstance(parsed, str):", isinstance(parsed, str))
```

```
'The capital of France is Paris.'
isinstance(parsed, str): True
```

### Gotcha — `type(parsed).__name__` is not `'str'`

In `langchain-core` 1.x, `StrOutputParser` actually returns a `TextAccessor`
object — a **subclass of `str`** that behaves identically to a plain string
in every way that matters (`==`, `.upper()`, f-string interpolation,
concatenation), but `type(parsed).__name__` prints `'TextAccessor'` instead
of `'str'`. This is why the notebook checks `isinstance(parsed, str)` (which
is `True`) rather than printing the type name. Don't be alarmed if you ever
print `type(...)` on a parsed value and see `TextAccessor` — for all
practical purposes, treat it as a string.

`JsonOutputParser().invoke(AIMessage(content='{"title": "Inception", "rating": 9}'))`
calls `json.loads` on `.content` and returns a genuine `dict`:

```
{'title': 'Inception', 'rating': 9}
<class 'dict'>
```

### `PydanticOutputParser`

```python
class MovieReview(BaseModel):
    title: str = Field(description="The movie's title")
    rating: int = Field(description="Rating out of 10")
    summary: str = Field(description="One-sentence summary")

pydantic_parser = PydanticOutputParser(pydantic_object=MovieReview)
```

`get_format_instructions()` introspects `MovieReview.model_json_schema()` and
renders a prompt fragment describing the expected JSON shape (truncated in
the notebook to the first 300 characters — it includes a generic example
schema followed by the actual schema for `MovieReview`).

`pydantic_parser.invoke(AIMessage(content='{"title": "Inception", "rating": 9, "summary": "A heist within dreams."}'))`
does two things in sequence: `json.loads(...)` to get a dict, then
`MovieReview(**that_dict)` to validate and construct the object:

```
title='Inception' rating=9 summary='A heist within dreams.'
review.title : Inception
review.rating: 9
```

The next cell feeds `'{"title": "Inception", "rating": "nine", "summary": "..."}'`
— valid JSON (`json.loads` succeeds), but `"nine"` cannot become an `int`.
Pydantic v2 raises a `ValidationError` during the `MovieReview(**dict)` step,
which `PydanticOutputParser` re-raises wrapped as an `OutputParserException`:

```
OutputParserException raised:
Failed to parse MovieReview from completion {"title": "Inception", "rating": "nine", "summary": "A heist within dreams."}. Got: 1 validation error for MovieReview
rating
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='nine', input_type=str]
```

This is the two-stage failure mode from the notes: *valid JSON, invalid
schema*.

---

## 4. LCEL

The manual trace cell calls each `Runnable`'s `.invoke()` by hand:

```python
stage1 = chat_template.invoke(inputs)              # ChatPromptValue
stage2 = fake_model_lcel.invoke(stage1)            # AIMessage(content='81.')
stage3 = str_parser.invoke(stage2)                 # '81.' (a TextAccessor / str)
```

```
stage1: [SystemMessage(content='You are a terse math tutor.', ...), HumanMessage(content='What is 9*9?', ...)]
stage2: content='81.' additional_kwargs={} response_metadata={} id='lc_run--...' tool_calls=[] invalid_tool_calls=[]
stage3: '81.'
```

The `|`-composed version produces the *same* `stage3` value:

```python
chain = chat_template | fake_model_lcel_2 | str_parser
result = chain.invoke({"persona": "terse math tutor", "question": "What is 9*9?"})
```

```
'81.'
matches manual trace: True
```

`__or__` is defined on `Runnable` (the common base class of
`ChatPromptTemplate`, `BaseChatModel`, and every output parser). `a | b`
returns a `RunnableSequence(a, b)` whose `.invoke(x)` is defined as
`b.invoke(a.invoke(x))`. Chaining three together,
`chat_template | model | str_parser`, is therefore
`RunnableSequence(chat_template, model, str_parser)`, whose `.invoke(x)`
equals `str_parser.invoke(model.invoke(chat_template.invoke(x)))` — exactly
the manual trace above, just written once and reusable.

`RunnableLambda(lambda text: text.upper() + "!")` wraps a plain function so it
has `.invoke()`. Appending it with `|` makes it the 4th stage:

```
'81.!'
```

`RunnableParallel({...})` runs every value in the dict against the *same*
input and collects the results into a dict keyed the same way:

```python
branch = RunnableParallel({
    "original": RunnablePassthrough(),
    "upper": RunnableLambda(lambda x: x.upper()),
    "length": RunnableLambda(lambda x: len(x)),
})
branch.invoke("hello")
```

```
{'original': 'hello', 'upper': 'HELLO', 'length': 5}
```

`RunnablePassthrough()` is `Runnable` whose `.invoke(x)` simply returns `x` —
each branch in `RunnableParallel` receives its own call with the same input
`"hello"`, so `"original"` gets it unchanged, `"upper"` gets it uppercased,
and `"length"` gets `len("hello") = 5`.

---

## 5. Memory — Exercise: `SummarizingChatMessageHistory`

### The docstring (as given in the template)

> A chat message history that automatically summarizes old messages once the
> history grows beyond `max_messages`. Declare three Pydantic fields —
> `model: BaseChatModel`, `max_messages: int`, `keep_last: int = 2` — then
> override `add_message(message)`: append as usual via
> `super().add_message(message)`; if `len(self.messages) <= self.max_messages`,
> stop; otherwise split into `old_messages = self.messages[:-keep_last]` and
> `recent_messages = self.messages[-keep_last:]`, ask `self.model` to
> summarize `old_messages` in 1-2 sentences, and replace `self.messages` with
> `[SystemMessage(summary)] + recent_messages`.

### Canonical implementation

```python
class SummarizingChatMessageHistory(InMemoryChatMessageHistory):
    model: BaseChatModel
    max_messages: int
    keep_last: int = 2

    def add_message(self, message):
        super().add_message(message)
        if len(self.messages) <= self.max_messages:
            return

        old_messages = self.messages[:-self.keep_last]
        recent_messages = self.messages[-self.keep_last:]

        lines = "\n".join(f"{type(m).__name__}: {m.content}" for m in old_messages)
        summary_request = [
            HumanMessage(content=f"Summarize the following conversation in 1-2 sentences:\n{lines}")
        ]
        summary_text = self.model.invoke(summary_request).content

        self.messages = (
            [SystemMessage(content=f"Summary of earlier conversation: {summary_text}")]
            + recent_messages
        )
```

**What each line does**:

- `model: BaseChatModel`, `max_messages: int`, `keep_last: int = 2` — these
  are Pydantic field declarations, not plain class attributes.
  `InMemoryChatMessageHistory` is itself a Pydantic `BaseModel` (its only
  declared field is `messages: List[BaseMessage]`), so subclassing it and
  adding new annotated fields automatically extends the generated
  `__init__`. After this, `SummarizingChatMessageHistory(model=m, max_messages=4, keep_last=2)`
  works with no `__init__` written by hand — Pydantic builds it from the
  field list (`messages` defaults to `[]` via the parent's
  `default_factory=list`).
- `super().add_message(message)` — calls `InMemoryChatMessageHistory.add_message`,
  which does `self.messages.append(message)`. After this line, the new
  message is already part of `self.messages`.
- `if len(self.messages) <= self.max_messages: return` — the *only* condition
  under which nothing further happens. With `max_messages=4`, this is `True`
  for lengths 1, 2, 3, 4 and `False` once length reaches 5.
- `old_messages = self.messages[:-self.keep_last]` — Python slice notation
  `[:-2]` means "everything except the last 2 elements". With 5 messages and
  `keep_last=2`, `old_messages` is messages `[0, 1, 2]` (the first 3).
- `recent_messages = self.messages[-self.keep_last:]` — `[-2:]` means "the
  last 2 elements", i.e. messages `[3, 4]`.
- `lines = "\n".join(f"{type(m).__name__}: {m.content}" for m in old_messages)`
  — builds a multi-line string, one line per old message, prefixed with its
  class name (`HumanMessage` or `AIMessage`).
- `summary_request = [HumanMessage(content=f"Summarize ...:\n{lines}")]` — a
  *brand-new*, single-message list. This is **not** appended to
  `self.messages`; it's a separate, throwaway request sent only to get a
  summary.
- `summary_text = self.model.invoke(summary_request).content` — calls the
  model with that one-message list and extracts `.content` (a string) from
  the returned `AIMessage`.
- `self.messages = [SystemMessage(...)] + recent_messages` — **replaces** the
  entire list (not appends): one new `SystemMessage` carrying the summary,
  followed by the 2 messages that were kept untouched.

### Dry run with the notebook's exact data

`summarizing_model = GenericFakeChatModel(messages=iter(["User asked about self-attention and LoRA; assistant explained both."]))`
— exactly one scripted response, because summarization should fire exactly
once across the 5 turns below.

`h = SummarizingChatMessageHistory(model=summarizing_model, max_messages=4, keep_last=2)`

| Step | `add_message(...)` called with | `len(self.messages)` after `super().add_message` | `<= max_messages (4)`? | Action | `self.messages` after |
|---|---|---|---|---|---|
| 1 | `HumanMessage("What is self-attention?")` | 1 | yes | none | `[H0]` |
| 2 | `AIMessage("It lets each token weigh every other token.")` | 2 | yes | none | `[H0, A0]` |
| 3 | `HumanMessage("And LoRA?")` | 3 | yes | none | `[H0, A0, H1]` |
| 4 | `AIMessage("It fine-tunes via small low-rank matrices.")` | 4 | yes | none | `[H0, A0, H1, A1]` |
| 5 | `HumanMessage("What about BPE?")` | 5 | **no** | summarize | see below |

At step 5, `old_messages = [H0, A0, H1]` (the first 3) and
`recent_messages = [A1, H2]` (`A1 = "It fine-tunes..."`,
`H2 = "What about BPE?"`). The summarization request sent to
`summarizing_model.invoke(...)` is:

```
Summarize the following conversation in 1-2 sentences:
HumanMessage: What is self-attention?
AIMessage: It lets each token weigh every other token.
HumanMessage: And LoRA?
```

`summarizing_model` ignores this content (as always) and returns its one
scripted reply: `"User asked about self-attention and LoRA; assistant
explained both."`. `self.messages` is then replaced with:

```
[
  SystemMessage("Summary of earlier conversation: User asked about self-attention and LoRA; assistant explained both."),
  AIMessage("It fine-tunes via small low-rank matrices."),
  HumanMessage("What about BPE?"),
]
```

— 3 messages, down from 5. The actual notebook output, message by message:

```
after message 1 (HumanMessage: 'What is self-attention?'):
  len(messages) = 1
    HumanMessage   | What is self-attention?

after message 2 (AIMessage: 'It lets each token weigh every other token.'):
  len(messages) = 2
    HumanMessage   | What is self-attention?
    AIMessage      | It lets each token weigh every other token.

after message 3 (HumanMessage: 'And LoRA?'):
  len(messages) = 3
    HumanMessage   | What is self-attention?
    AIMessage      | It lets each token weigh every other token.
    HumanMessage   | And LoRA?

after message 4 (AIMessage: 'It fine-tunes via small low-rank matrices.'):
  len(messages) = 4
    HumanMessage   | What is self-attention?
    AIMessage      | It lets each token weigh every other token.
    HumanMessage   | And LoRA?
    AIMessage      | It fine-tunes via small low-rank matrices.

after message 5 (HumanMessage: 'What about BPE?'):
  len(messages) = 3
    SystemMessage  | Summary of earlier conversation: User asked about self-attention and LoRA; assistant explained both.
    AIMessage      | It fine-tunes via small low-rank matrices.
    HumanMessage   | What about BPE?
```

### Gotcha — replace, don't mutate-in-place with `del` or `.pop()`

It's tempting to write `del self.messages[:-keep_last]` or loop with
`.pop(0)`. The reason the canonical solution builds a brand-new list and
*assigns* `self.messages = [...]` is that `old_messages` and
`recent_messages` are computed as **slices** (which copy references into new
lists) *before* any mutation — if you instead mutated `self.messages` while
also reading from it to build `old_messages`/`recent_messages`, you'd risk
reading a list that's already been partially modified. Building the new list
first and assigning it last avoids this entirely.

---

## 6. Retrievers as Runnables

```python
class SimpleKeywordRetriever(BaseRetriever):
    documents: List[Document]
    k: int = 1

    def _get_relevant_documents(self, query, *, run_manager=None):
        query_words = set(query.lower().split())
        scored = []
        for doc in self.documents:
            doc_words = set(doc.page_content.lower().split())
            overlap = len(query_words & doc_words)
            scored.append((overlap, doc))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for score, doc in scored[: self.k]]
```

`BaseRetriever` (also a `Runnable`) requires you to implement
`_get_relevant_documents` (the underscore-prefixed "do the actual work"
method); `BaseRetriever.invoke(query)` is the public method that calls it
(plus handles tracing/callbacks via `run_manager`, which this implementation
ignores).

### Dry run

```
query = "How does attention compute weighted values?"
query_words = {"how", "does", "attention", "compute", "weighted", "values?"}
```

(Note: `.split()` on punctuation-attached words keeps `"values?"` with its
question mark — `set.lower().split()` is a naive tokenizer, deliberately so;
this is the "exact-match only" limitation flagged in the notes.)

For each document, `doc_words & query_words`:

| doc | doc_words (lowercased) | overlap with query_words | score |
|---|---|---|---|
| A | {self-attention, computes, a, weighted, average, of, value, vectors} | `{"weighted"}` | 1 |
| B | {lora, fine-tunes, a, model, using, small, low-rank, matrices} | `{}` | 0 |
| C | {byte, pair, encoding, merges, frequent, character, pairs, into, subwords} | `{}` | 0 |
| D | {retrieval, augmented, generation, retrieves, documents, before, generating, an, answer} | `{}` | 0 |
| E | {direct, preference, optimization, trains, a, model, directly, on, preference, pairs} | `{}` | 0 |

Sorted descending by score, `scored[:1]` = `[(1, doc_A)]`. Output:

```
query words: {'how', 'does', 'attention', 'compute', 'weighted', 'values?'}
retrieved [A]: Self-attention computes a weighted average of value vectors
```

### RAG chain

```python
parallel_stage = RunnableParallel({
    "context": retriever | format_docs_runnable,
    "question": RunnablePassthrough(),
})
```

`retriever | format_docs_runnable` is itself a `RunnableSequence`:
`retriever.invoke(query)` returns `[Document(...)]` (a list with one
`Document`), and `format_docs_runnable.invoke([Document(...)])` runs
`"\n".join(d.page_content for d in docs)`, collapsing the list to a single
string. Inside `RunnableParallel`, this whole sequence is one branch;
`RunnablePassthrough()` is the other branch, returning `query` unchanged.

```
context : Self-attention computes a weighted average of value vectors
question: How does attention compute weighted values?
```

`rag_chain = parallel_stage | rag_prompt | rag_model | StrOutputParser()`
feeds `{"context": ..., "question": ...}` into `rag_prompt`'s two
placeholders, then `rag_model` (scripted with one canned answer) returns it,
and `StrOutputParser()` extracts `.content`:

```
Attention computes a weighted average of value vectors, using weights derived from query-key dot products.
```

---

## 7. Tools — Exercise: `add_numbers`, `reverse_text`, `execute_tool_calls`

### The docstrings (as given in the template)

> `add_numbers(a: int, b: int) -> int`: add two integers and return the sum.
> `reverse_text(text: str) -> str`: reverse a string, e.g. `"hello" -> "olleh"`.
> `execute_tool_calls(ai_message, tools_by_name)`: for each dict in
> `ai_message.tool_calls`, look up `tools_by_name[tool_call["name"]]`, call
> `.invoke(tool_call["args"])`, and wrap the result in
> `ToolMessage(content=str(result), tool_call_id=tool_call["id"])`. Return the
> list of `ToolMessage`s in order.

### Canonical implementation

```python
@tool
def add_numbers(a: int, b: int) -> int:
    """Add two integers together and return the sum."""
    return a + b


@tool
def reverse_text(text: str) -> str:
    """Reverse a string."""
    return text[::-1]


def execute_tool_calls(ai_message, tools_by_name):
    results = []
    for tool_call in ai_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        result = tool_fn.invoke(tool_call["args"])
        results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    return results
```

**What each line does**:

- `@tool` above `add_numbers` reads the function's name (`add_numbers`), type
  hints (`a: int, b: int -> int`), and docstring, and wraps the function in a
  `BaseTool`. The function body itself — `return a + b` — is completely
  ordinary Python; `@tool` doesn't change *how* the function runs, only how
  it's *described* to a model.
- `text[::-1]` is Python's slice-based string reversal: step `-1` walks the
  string backwards, producing `"hello"[::-1] == "olleh"`.
- `execute_tool_calls` loops over `ai_message.tool_calls` (a list of plain
  dicts — not objects). `tool_call["name"]` looks up the right `BaseTool` in
  `tools_by_name`; `.invoke(tool_call["args"])` calls it with the args dict
  unpacked as keyword arguments (`add_numbers.invoke({"a": 12, "b": 30})` is
  equivalent to calling `add_numbers(a=12, b=30)`); `str(result)` converts the
  return value (an `int` for `add_numbers`, a `str` for `reverse_text`) to a
  string, since `ToolMessage.content` is always a string;
  `tool_call_id=tool_call["id"]` preserves the link back to the specific
  request.

### Dry run with the notebook's exact data

```python
add_numbers.args   = {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}
reverse_text.args  = {'text': {'title': 'Text', 'type': 'string'}}

fake_tool_call_message = AIMessage(
    content="",
    tool_calls=[
        {"name": "add_numbers", "args": {"a": 12, "b": 30}, "id": "call_001"},
        {"name": "reverse_text", "args": {"text": "hello"}, "id": "call_002"},
    ],
)
```

`execute_tool_calls(fake_tool_call_message, tools_by_name)` iterates the two
`tool_calls`:

1. `tool_call = {"name": "add_numbers", "args": {"a": 12, "b": 30}, "id": "call_001", "type": "tool_call"}`.
   `tool_fn = add_numbers`. `result = add_numbers.invoke({"a": 12, "b": 30})`
   = `12 + 30` = `42` (an `int`). `ToolMessage(content=str(42), tool_call_id="call_001")`
   = `ToolMessage(content='42', tool_call_id='call_001')`.
2. `tool_call = {"name": "reverse_text", "args": {"text": "hello"}, "id": "call_002", "type": "tool_call"}`.
   `tool_fn = reverse_text`. `result = reverse_text.invoke({"text": "hello"})`
   = `"hello"[::-1]` = `"olleh"`. `ToolMessage(content="olleh", tool_call_id="call_002")`.

```
tool_calls: [{'name': 'add_numbers', 'args': {'a': 12, 'b': 30}, 'id': 'call_001', 'type': 'tool_call'}, {'name': 'reverse_text', 'args': {'text': 'hello'}, 'id': 'call_002', 'type': 'tool_call'}]
results: [ToolMessage(content='42', tool_call_id='call_001'), ToolMessage(content='olleh', tool_call_id='call_002')]
```

### Gotcha — `tool_fn.invoke(args_dict)`, not `tool_fn(**args_dict)`

`add_numbers` is a `BaseTool` object (because of `@tool`), not the original
Python function — calling `add_numbers(a=12, b=30)` directly raises a
`TypeError` (a `BaseTool` isn't callable that way in recent langchain-core
versions). Always call `.invoke(args_dict)` on a `@tool`-decorated function,
passing the *whole args dict* as a single argument, exactly as
`tool_call["args"]` is already shaped.

---

## Putting It All Together

```
┌──────────────────────────────────────────────────────────────────┐
│ {"persona": ..., "question": ...}                                  │
│        │ chat_template (Section 2)                                 │
│        ▼                                                            │
│ ChatPromptValue (list of messages)                                  │
│        │ model (Section 1: GenericFakeChatModel)                   │
│        ▼                                                            │
│ AIMessage                                                            │
│        │ StrOutputParser / JsonOutputParser / PydanticOutputParser  │
│        │ (Section 3)                                                │
│        ▼                                                            │
│ str / dict / MovieReview                                             │
└──────────────────────────────────────────────────────────────────┘
        all of the above wired together with | (Section 4 — LCEL)

┌──────────────────────────────────────────────────────────────────┐
│ query: str                                                          │
│   ├──▶ retriever | format_docs  ──▶ context: str  ─┐               │
│   └──▶ RunnablePassthrough()    ──▶ question: str ─┤ RunnableParallel│
│                                                      ▼               │
│                                              {"context", "question"} │
│                                                      │ rag_prompt     │
│                                                      ▼               │
│                                              ChatPromptValue         │
│                                                      │ rag_model      │
│                                                      ▼               │
│                                              AIMessage → StrOutputParser│
└──────────────────────────────────────────────────────────────────┘
        Section 6 — retriever as a Runnable inside an LCEL chain

┌──────────────────────────────────────────────────────────────────┐
│ messages: List[BaseMessage]  (Section 5 — SummarizingChatMessageHistory)│
│   add_message() x N  ──▶  bounded-length list, oldest collapsed     │
│                            into one SystemMessage summary            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ AIMessage(tool_calls=[...])  (Section 7)                            │
│   ──▶ execute_tool_calls() ──▶ [ToolMessage, ToolMessage, ...]      │
│   ──▶ append to messages, call model again ──▶ final AIMessage      │
└──────────────────────────────────────────────────────────────────┘
```

## Where to Go Next

- **Topic 2 — LangGraph**: the tool-call round trip at the bottom of the
  diagram above (`AIMessage.tool_calls → execute → ToolMessage → invoke
  again`) is exactly the loop LangGraph generalizes into a graph node that can
  repeat until the model stops requesting tools.
- **Topic 5 — Advanced RAG**: replace `SimpleKeywordRetriever` with an
  embedding-based retriever — the `retriever | format_docs_runnable` wiring
  in `parallel_stage` doesn't change at all.
- **Topic 7 — Structured Outputs & Tool Calling**: digs into what happens when
  `PydanticOutputParser` (Section 3) or tool-call arguments (Section 7) come
  back malformed, and how to build a retry/repair loop.
