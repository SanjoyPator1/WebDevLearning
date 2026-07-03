# LangChain Fundamentals

LangChain is a library that gives every large language model the same shape: a function that takes a list of messages and returns a message back. Once every model — whether it lives on OpenAI's servers, Anthropic's servers, or on your own RTX A6000 via Ollama — looks the same from the outside, you can build reusable pieces around it: prompt templates that fill in variables, output parsers that turn raw text into structured Python objects, retrievers that fetch relevant documents, and tools that let the model ask your code to do something on its behalf. LangChain's job is to standardize the *interfaces* between these pieces so they snap together with the `|` operator, the way Unix pipes snap `grep`, `sort`, and `uniq` together.

This note builds up that vocabulary from the ground up: messages and chat models, prompt templates, output parsers, the LangChain Expression Language (LCEL) that composes everything with `|`, conversation memory, retrievers, and tools. Every concept is demonstrated with a tiny, fully offline example using `GenericFakeChatModel` — a chat model that returns pre-scripted responses instead of calling a real API — so you can trace every input and output by hand before pointing the same code at a real model (Ollama, OpenAI, Claude, etc.).

---

## Table of Contents

1. [Where This Sits](#where-this-sits)
2. [Models & Messages](#1-models--messages)
3. [Prompt Templates](#2-prompt-templates)
4. [Output Parsers](#3-output-parsers)
5. [LCEL — The LangChain Expression Language](#4-lcel--the-langchain-expression-language)
6. [Memory](#5-memory)
7. [Retrievers as Runnables](#6-retrievers-as-runnables)
8. [Tools](#7-tools)
9. [Summary & Connection Forward](#summary--connection-forward)

---

## Where This Sits

Books B01 and B02 taught you what happens *inside* a transformer — attention, embeddings, training, fine-tuning. LangChain sits one layer above all of that: it assumes you already have a model that can take text in and produce text out (whether that model is the GPT you built from scratch in B01, GPT-2 loaded via HuggingFace in B02, or a hosted model like Claude), and gives you a standard set of building blocks for wiring that model into an application.

```
┌─────────────────────────────────────────────────────────────────┐
│  B01 / B02 — what happens INSIDE the model                       │
│  tokens → embeddings → attention → ... → next-token logits       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  the model is now a black box:
                              │  invoke(messages) -> AIMessage
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 1 — LangChain Fundamentals (THIS NOTE)                 │
│  messages, prompts, parsers, LCEL, memory, retrievers, tools     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  B03 Topic 2 — LangGraph                                          │
│  wires these same primitives into a stateful graph with cycles   │
└─────────────────────────────────────────────────────────────────┘
```

Everything in this note is a small, composable Python object. The skill being taught is not "how do I call an LLM" — that's one line, `model.invoke(messages)`. The skill is "how do I compose many small, swappable pieces (prompt → model → parser → retriever → tool) into a pipeline I can reason about, test offline, and later upgrade to a real model without rewriting the pipeline."

---

## 1. Models & Messages

**Summary**: A chat model in LangChain is an object with one essential method — `invoke` — that takes a *list of messages* and returns a *single message* back.

**The problem it solves**: Every LLM provider has its own API: different function names, different JSON shapes for "the conversation so far," different ways of marking who said what. If your application code called the OpenAI SDK directly, switching to Claude or a local Ollama model would mean rewriting every call site. LangChain defines one interface — `BaseChatModel` — that every provider's integration implements, so your application code never needs to know which provider is underneath.

**The intuition**: Think of a chat model as a function with the signature

$$\text{invoke} : \text{List}[\text{Message}] \rightarrow \text{Message}$$

A "message" is a small object with two important fields: who said it (`role` — system, human, or AI) and what they said (`content` — a string). You hand the model the entire conversation so far as a list of these objects, and it hands back exactly one new message: its reply. The model itself is *stateless* — it has no memory between calls. Every piece of context the model should "remember" must be present in the list you pass to `invoke` each time. (Section 5, Memory, is entirely about managing that list so it doesn't grow forever.)

**The three message types**:

```
SystemMessage  — instructions ABOUT how the model should behave
                 (not part of the visible "conversation", set once at the top)

HumanMessage   — something the user said

AIMessage      — something the model said (in a previous turn, or the
                 model's current reply)
```

```
┌──────────────────────────────────────────────────────────┐
│ messages = [                                              │
│   SystemMessage("You are a terse math tutor."),          │
│   HumanMessage("What is 12 * 4?"),                        │
│   AIMessage("48."),                                       │
│   HumanMessage("And divided by 6?"),                      │
│ ]                                                          │
│                     │                                      │
│                     ▼  model.invoke(messages)              │
│            AIMessage("8.")                                 │
└──────────────────────────────────────────────────────────┘
```

**Dry run with `GenericFakeChatModel`**: `GenericFakeChatModel` is a chat model that ships with `langchain-core` and returns pre-scripted responses from an iterator — one response per call to `invoke`, in order — regardless of what messages it receives. It implements the *exact same* `BaseChatModel` interface as `ChatOpenAI`, `ChatAnthropic`, or `ChatOllama`, which is the entire point: every example in this note runs with zero API keys and zero network access, and the code is line-for-line identical to what you'd write against a real model.

```
fake_model = GenericFakeChatModel(messages=iter(["48.", "8."]))

Call 1: fake_model.invoke([SystemMessage(...), HumanMessage("What is 12 * 4?")])
        → AIMessage(content="48.")     ← first item from the iterator

Call 2: fake_model.invoke([..., HumanMessage("And divided by 6?")])
        → AIMessage(content="8.")      ← second item from the iterator

Call 3: fake_model.invoke([...])
        → StopIteration (iterator exhausted — script ran out of lines)
```

The fake model never looks at its input — it just plays back the script. A real model's output would *depend* on the input messages, but the shape of the call (`list of messages in`, `one AIMessage out`) is identical. This is the contract every other piece in this note is built on top of.

### Gotcha — `print(ai_message)` vs `ai_message.content`

`AIMessage` is an object, not a string. `print(ai_message)` shows a representation like `AIMessage(content='48.', ...)` including metadata (token usage, model name, response id). To get just the text, access `.content`. New LangChain users frequently pass the whole `AIMessage` object somewhere a plain string is expected and get a confusing type error — `StrOutputParser` (Section 3) exists specifically to make this conversion automatic at the end of a chain.

---

## 2. Prompt Templates

**Summary**: A prompt template is a string (or list of messages) with `{placeholders}` that get filled in with real values at call time — the LangChain equivalent of an f-string, but as a reusable, inspectable object.

**The problem it solves**: Hardcoding `f"Translate this to French: {user_text}"` works for a one-off script. But once that prompt needs to be reused across a chain, combined with few-shot examples, partially filled in at setup time and finished later, or swapped out entirely (Alpaca-style vs Phi-3-style, as in B01 chapter 7), a plain f-string gives you nothing to grab onto. A `PromptTemplate` is a first-class object: it knows its own input variables, can be partially filled, can be composed with `|`, and can be serialized/logged.

**`PromptTemplate` — for plain-text prompts**:

```
template = PromptTemplate.from_template(
    "Translate the following English text to {language}:\n\n{text}"
)

template.input_variables  →  ['language', 'text']

template.format(language="French", text="Good morning")
  →  "Translate the following English text to French:\n\nGood morning"
```

`from_template` scans the string for `{name}` placeholders and records them as `input_variables`. `.format(**kwargs)` does the substitution — it's a thin, validated wrapper around Python's own `str.format`, with the benefit that LangChain can now introspect what variables this template needs *before* anything runs.

**`ChatPromptTemplate` — for a list of messages**:

A chat model expects a *list of messages*, not a single string, so `ChatPromptTemplate` is built from a list of `(role, template_string)` pairs:

```
chat_template = ChatPromptTemplate.from_messages([
    ("system", "You are a {persona}."),
    ("human",  "{question}"),
])

chat_template.invoke({"persona": "terse math tutor", "question": "What is 9*9?"})
  →  ChatPromptValue(messages=[
        SystemMessage(content="You are a terse math tutor."),
        HumanMessage(content="What is 9*9?"),
     ])
```

Notice the output is a *list of message objects*, with `{persona}` and `{question}` substituted into the right messages — exactly the input shape `model.invoke(...)` expects from Section 1. This is the first hint of why `|` composition (Section 4) works: the *output type* of a prompt template (`ChatPromptValue`, which behaves like a list of messages) matches the *input type* of a chat model.

### Partial Variables

Sometimes one variable is known early (e.g., the persona is fixed for this whole application) and another is only known per-request (the user's question). `.partial()` bakes in the known value and returns a new template that only needs the rest:

```
base_template = ChatPromptTemplate.from_messages([
    ("system", "You are a {persona}."),
    ("human",  "{question}"),
])

tutor_template = base_template.partial(persona="terse math tutor")

tutor_template.input_variables  →  ['question']   # persona is already filled in

tutor_template.invoke({"question": "What is 9*9?"})
  →  [SystemMessage("You are a terse math tutor."), HumanMessage("What is 9*9?")]
```

### Few-Shot Prompt Templates

**The problem it solves**: For many tasks, *showing* the model 2-3 examples of input → output pairs works far better than just *describing* the task. A few-shot prompt template formats a list of example dicts using a small `example_prompt` template, then concatenates all the formatted examples in front of the real input.

```
example_prompt = PromptTemplate.from_template("Input: {input}\nOutput: {output}")

examples = [
    {"input": "happy",   "output": "sad"},
    {"input": "tall",    "output": "short"},
]

few_shot = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    suffix="Input: {adjective}\nOutput:",
    input_variables=["adjective"],
)

few_shot.format(adjective="fast")
  →
  """Input: happy
  Output: sad

  Input: tall
  Output: short

  Input: fast
  Output:"""
```

**Dry run, piece by piece**: `FewShotPromptTemplate` loops over `examples`, calling `example_prompt.format(**example)` for each one — producing `"Input: happy\nOutput: sad"` and `"Input: tall\nOutput: short"` — joins them with blank lines, then appends `suffix.format(adjective="fast")` = `"Input: fast\nOutput:"`. The model, having just seen two complete "opposite word" examples, is far more likely to continue with `" slow"` than if it had only been told "give me the opposite of a word" in English.

### Gotcha — `PromptTemplate` vs `ChatPromptTemplate`

`PromptTemplate.format(...)` returns a plain Python **string**. `ChatPromptTemplate.invoke(...)` returns a **`ChatPromptValue`** — an object that wraps a list of `BaseMessage` objects (call `.to_messages()` to get the list directly, or `.to_string()` to get a flattened string). Mixing these up — e.g., passing a raw string where a chat model expects a `ChatPromptValue`/list of messages — is one of the most common first errors. In practice almost all modern chat-model code uses `ChatPromptTemplate`; `PromptTemplate` mainly survives for older "completion-style" models and as the building block (`example_prompt`) inside few-shot templates.

---

## 3. Output Parsers

**Summary**: An output parser takes the raw `AIMessage` a model returns and converts it into the Python type your application actually wants — a plain string, a dict, or a validated object.

**The problem it solves**: A chat model's `.invoke()` always returns an `AIMessage`. But your application rarely wants an `AIMessage` object — it wants a string to display, a dict to store in a database, or a typed object (`MovieReview(title=..., rating=..., summary=...)`) to pass to the next function. Output parsers are the standardized "last step" of a chain that performs this conversion — and, for the structured parsers, they also *tell the model what format to produce* via `get_format_instructions()`.

### `StrOutputParser` — the simplest case

```
parser = StrOutputParser()
parser.invoke(AIMessage(content="The capital of France is Paris."))
  →  "The capital of France is Paris."     # plain str, not AIMessage
```

This is nothing more than `.content` extraction wrapped as a `Runnable` (so it can be composed with `|` — see Section 4). It is the single most common last step of a chain: "give me the model's reply as plain text."

### `JsonOutputParser` — parsing into a dict

```
parser = JsonOutputParser()
parser.invoke(AIMessage(content='{"title": "Inception", "rating": 9}'))
  →  {"title": "Inception", "rating": 9}     # plain dict
```

`JsonOutputParser` calls `json.loads` on the message content (with some leniency for models that wrap JSON in markdown code fences). If the model's output isn't valid JSON, this raises an error — which is exactly the failure mode Topic 7 (Structured Outputs & Tool Calling) digs into in depth, including retry strategies.

### `PydanticOutputParser` — parsing into a validated object

This is the parser that closes the loop between "tell the model what shape to produce" and "validate what it actually produced."

```
class MovieReview(BaseModel):
    title: str = Field(description="The movie's title")
    rating: int = Field(description="Rating out of 10")
    summary: str = Field(description="One-sentence summary")

parser = PydanticOutputParser(pydantic_object=MovieReview)

print(parser.get_format_instructions())
```

`get_format_instructions()` returns a block of text — generated automatically from the Pydantic model's fields and their `description`s — that explains to the model exactly what JSON schema to produce. This string is meant to be inserted into your prompt template (often via a partial variable), so the model is told what shape of output is expected *before* it generates anything.

```
parser.invoke(AIMessage(content='{"title": "Inception", "rating": 9, "summary": "A heist within dreams."}'))
  →  MovieReview(title="Inception", rating=9, summary="A heist within dreams.")
```

**Dry run of the validation step**: suppose the model instead returned `'{"title": "Inception", "rating": "nine", "summary": "A heist within dreams."}'` — `"rating"` as the string `"nine"` instead of the integer `9`. `json.loads` would succeed (it's valid JSON), but Pydantic's validation would then fail with a `ValidationError`, because `rating: int` cannot accept the string `"nine"`. This two-stage failure mode — *valid JSON, but invalid against your schema* — is exactly why `PydanticOutputParser` is preferred over `JsonOutputParser` whenever you have a known shape: it catches type mistakes that plain JSON parsing would silently let through.

### Gotcha — format instructions are a *request*, not a *guarantee*

`get_format_instructions()` only changes the *prompt* — it asks the model nicely to produce JSON matching the schema. Nothing stops a model from ignoring this and returning prose. `PydanticOutputParser` will then raise a parsing error. Some providers offer a stronger guarantee (constrained decoding / JSON mode, where invalid tokens are made impossible rather than just discouraged) — this is the subject of Topic 7.

---

## 4. LCEL — The LangChain Expression Language

**Summary**: LCEL is the `|` (pipe) operator applied to `Runnable` objects. `chain = a | b | c` builds a new `Runnable` whose `.invoke(x)` is equivalent to `c.invoke(b.invoke(a.invoke(x)))`.

**The problem it solves**: Sections 1-3 introduced three kinds of objects — prompt templates, chat models, output parsers — each with their own `.invoke()` method and their own input/output types. Without LCEL, using all three together means writing boilerplate:

```python
prompt_value = chat_template.invoke({"question": "What is 9*9?"})
ai_message   = model.invoke(prompt_value)
answer       = parser.invoke(ai_message)
```

This works, but it's verbose, and every new pipeline repeats the same "invoke, pass result to next invoke" pattern. LCEL recognizes that **every one of these objects already implements the same `Runnable` interface** (`.invoke()`, `.batch()`, `.stream()`, `.ainvoke()`, ...), so it overloads `|` on `Runnable` to mean "feed my output as your input."

**The math**: if $f$, $g$, $h$ are runnables (functions), then

$$\text{chain} = f \mid g \mid h \quad \Longleftrightarrow \quad \text{chain}(x) = h(g(f(x)))$$

This is exactly function composition, written left-to-right instead of the usual mathematical right-to-left ($h \circ g \circ f$). The boilerplate above collapses to:

```python
chain  = chat_template | model | parser
answer = chain.invoke({"question": "What is 9*9?"})
```

**Dry run — tracing data through `chain.invoke({"question": "What is 9*9?"})`**:

```
INPUT:  {"question": "What is 9*9?"}
   │
   │  chat_template.invoke(...)
   ▼
STAGE 1 OUTPUT (ChatPromptValue):
   [SystemMessage("You are a terse math tutor."),
    HumanMessage("What is 9*9?")]
   │
   │  model.invoke(...)              ← GenericFakeChatModel returns next scripted line
   ▼
STAGE 2 OUTPUT (AIMessage):
   AIMessage(content="81.")
   │
   │  parser.invoke(...)             ← StrOutputParser
   ▼
STAGE 3 OUTPUT (str):
   "81."
```

Each `|` is a type-compatible handoff: `ChatPromptTemplate` outputs a `ChatPromptValue` (which `BaseChatModel.invoke` accepts as input), `BaseChatModel` outputs an `AIMessage` (which `StrOutputParser.invoke` accepts as input). LCEL doesn't add any new capability over calling `.invoke()` three times by hand — its value is making this composition a single, named, reusable object that *also* automatically gets `.batch()`, `.stream()`, and async versions of all three, for free, because the underlying pieces already support them.

### `RunnableLambda` — wrapping a plain function

**The problem it solves**: Sometimes a step in your pipeline isn't a prompt, model, or parser — it's a small piece of plain Python (e.g., uppercase a string, look up a value in a dict). `RunnableLambda` wraps any function so it can participate in `|` chains.

```
shout = RunnableLambda(lambda text: text.upper() + "!")

chain = chat_template | model | parser | shout
chain.invoke({"question": "What is 9*9?"})
  →  "81.!"
```

`shout` receives whatever the previous stage (`StrOutputParser`) produced — a plain string `"81."` — and returns `"81.!"`. Because `RunnableLambda` implements the same `Runnable` interface, it slots into the `|` chain exactly like a prompt or parser would.

### `RunnableParallel` and `RunnablePassthrough`

**The problem it solves**: A linear `|` chain passes *one* value from stage to stage. But many real chains need to run several things on the *same* input and combine the results — the canonical example is RAG (Section 6): retrieve documents *and* keep the original question, then feed both into a prompt.

`RunnableParallel` (often written as a plain dict — LangChain auto-wraps `{...}` in `RunnableParallel` when it appears in a `|` chain) runs each of its values on the *same* input and returns a dict of their outputs:

```
RunnableParallel({
    "upper": RunnableLambda(lambda x: x.upper()),
    "length": RunnableLambda(lambda x: len(x)),
}).invoke("hello")
  →  {"upper": "HELLO", "length": 5}
```

`RunnablePassthrough` is the identity function as a `Runnable` — `.invoke(x) -> x` — used inside a `RunnableParallel` when you want one branch to be *the original input, unchanged*, alongside other branches that transform it:

```
RunnableParallel({
    "original": RunnablePassthrough(),
    "upper":    RunnableLambda(lambda x: x.upper()),
}).invoke("hello")
  →  {"original": "hello", "upper": "HELLO"}
```

**Dry run of the math**: formally, `RunnableParallel({"k1": f1, "k2": f2})` is the function

$$x \mapsto \{\,k_1: f_1(x),\ k_2: f_2(x)\,\}$$

— every branch receives an *identical copy* of $x$ (not a shared mutable reference that one branch could corrupt for another), and the results are collected into a single dict keyed by the names you chose. This dict then becomes the *single input* to whatever comes next in the `|` chain — typically a `ChatPromptTemplate` whose `{original}` and `{upper}` placeholders are filled from exactly these keys.

```
┌──────────────────────────────────────────────────────────────────┐
│  INPUT: "hello"                                                    │
│     │              │                                               │
│     │ (copy)       │ (copy)                                        │
│     ▼              ▼                                               │
│  RunnablePassthrough   RunnableLambda(str.upper)                  │
│     │              │                                               │
│     ▼              ▼                                               │
│  "hello"          "HELLO"                                          │
│     └──────┬───────┘                                               │
│            ▼                                                        │
│  {"original": "hello", "upper": "HELLO"}   ← single dict, passed   │
│                                                onward in the chain  │
└──────────────────────────────────────────────────────────────────┘
```

### Gotcha — `|` only works between `Runnable`s

`object_a | object_b` only does the LCEL composition if both objects implement the `Runnable` interface. Plain functions must be wrapped in `RunnableLambda` first; plain dicts `{...}` are auto-wrapped in `RunnableParallel` *only* when they appear directly as an operand of `|` inside LangChain's own code paths — assigning a raw dict to a variable and trying to call `.invoke()` on it directly will fail. When in doubt, wrap explicitly.

---

## 5. Memory

**Summary**: "Memory" in LangChain means *managing the list of messages you pass to `invoke` each turn* — deciding what to keep, what to summarize, and what to drop, since the model itself remembers nothing between calls.

**The problem it solves**: Section 1 established that a chat model is stateless — `invoke(messages) -> AIMessage`, with no hidden state carried over. A multi-turn conversation therefore requires *your application* to keep the growing list of `HumanMessage`/`AIMessage` pairs and re-send the entire list on every turn. Two problems emerge as the conversation grows: the list eventually exceeds the model's context window, and even before that, cost and latency grow with every token re-sent on every turn (since nothing is cached across the growing prefix in this naive scheme).

**The intuition**: Picture a sticky-note pad. Each turn, you write down what was said and stick it to a growing pile. A chat model only ever reads "the current pile" — it has no memory of *previous* piles. If the pile gets too tall, you can't keep handing over the whole thing forever — at some point you need to take the oldest notes, write a one-line summary of them on a fresh note ("earlier, we discussed X and Y"), throw away the originals, and put the summary at the bottom of the (now much shorter) pile.

**`InMemoryChatMessageHistory`**: the simplest possible "pile" — an object holding a Python list of messages, with `.add_message(msg)` to append and `.messages` to read the whole list. By itself it never shrinks.

**Summarizing memory — the mechanism**:

```
┌─────────────────────────────────────────────────────────────────┐
│  history.messages BEFORE add_message (5 messages, max=4)         │
│  [Human0, AI0, Human1, AI1, Human2]                                │
│                                                                     │
│  add_message(AI2)  →  now 6 messages, exceeds max=4              │
│                                                                     │
│  Step 1: split into "old" = [Human0, AI0, Human1, AI1]            │
│                  and "keep" = [Human2, AI2]   (last 2 messages)   │
│                                                                     │
│  Step 2: model.invoke(summarize_prompt(old))                      │
│          → AIMessage("User asked about X and Y; assistant         │
│             explained both.")                                     │
│                                                                     │
│  Step 3: history.messages  =                                      │
│    [SystemMessage("Summary of earlier conversation: User asked    │
│       about X and Y; assistant explained both."),                 │
│     Human2, AI2]                                                   │
│                                                                     │
│  AFTER: 3 messages — shrunk from 6, but the gist of the first      │
│  4 is preserved as a single SystemMessage                          │
└─────────────────────────────────────────────────────────────────┘
```

**Dry run with tiny numbers**: with `max_messages=4`, after turns 0 and 1 the history has 4 messages — at the limit, no summarization yet. After turn 2's `HumanMessage` is added (5 messages), still under the *trigger* (the implementation in this note's exercise checks `len(self.messages) > max_messages` *after* each `add_message`, so it fires once the count reaches 5). The 5 messages get split into the oldest 3 (`Human0, AI0, Human1`) — summarized into one `SystemMessage` — plus the most recent 2 (`AI1, Human2`) kept verbatim, leaving 3 messages total. The conversation can now continue for two more turns before crossing the threshold again.

### Gotcha — this is *not* what production systems use in 2026

This note teaches the *mechanism* of memory because understanding "the message list is the only state" is foundational. In practice, by 2026 most production agents manage conversational state via **LangGraph's checkpointer** (Topic 2) rather than these `ChatMessageHistory` classes — the checkpointer persists the *entire graph state* (not just messages) and supports resuming, branching, and time-travel. The `SummarizingChatMessageHistory` exercise here is the conceptual stepping stone: once you've built summarization by hand once, LangGraph's more powerful persistence will make immediate sense.

---

## 6. Retrievers as Runnables

**Summary**: A retriever is a `Runnable` whose `.invoke(query: str)` returns `List[Document]` — the most relevant documents to the query, from whatever store of documents it wraps.

**The problem it solves**: B02 chapter 8 covered embedding-based semantic search: encode documents and queries into vectors, find nearest neighbors. That's *one way* to implement a retriever. LangChain's `BaseRetriever` interface doesn't care *how* relevance is computed — embeddings, keyword overlap, a SQL query, a web search API — as long as the object exposes `.invoke(query) -> List[Document]`. Once it does, it's a `Runnable` and can be `|`-composed into an LCEL chain exactly like a prompt template or parser.

**The intuition**: A `Document` is just a container for a piece of text plus optional metadata: `Document(page_content="...", metadata={"source": "..."})`. A retriever is a function $\text{retrieve}: \text{query} \mapsto [\text{doc}_1, \text{doc}_2, \dots]$ — it doesn't generate anything, it just *finds and ranks*. Generation happens later, when those documents are stuffed into a prompt for the model.

**A tiny keyword-overlap retriever (the worked example in the notebook)**: rather than embeddings (covered properly in Topics 5-6), the notebook implements relevance as the count of words shared between the query and each document — simple enough to trace by hand, but enough to demonstrate the `BaseRetriever` interface and LCEL composition.

**Dry run with a 3-document corpus**:

```
Documents:
  doc_A: "Self-attention computes a weighted average of value vectors"
  doc_B: "LoRA fine-tunes a model using small low-rank matrices"
  doc_C: "Byte pair encoding merges frequent character pairs into subwords"

Query: "How does attention compute weighted values?"

Step 1 — lowercase + split query into a set of words:
  query_words = {how, does, attention, compute, weighted, values}

Step 2 — for each document, lowercase + split into a set of words,
         then count the overlap with query_words:

  doc_A words = {self-attention, computes, a, weighted, average, of,
                  value, vectors}
  overlap(A) = |{"weighted"} ∩ ...|  → "weighted" matches → score = 1
  (note: "attention" ≠ "self-attention", "value" ≠ "values" as exact
   string matches — keyword overlap is exact-match, a real limitation
   that motivates embeddings in Topic 5/6)

  doc_B words = {lora, fine-tunes, a, model, using, small, low-rank,
                  matrices}
  overlap(B) = 0

  doc_C words = {byte, pair, encoding, merges, frequent, character,
                  pairs, into, subwords}
  overlap(C) = 0

Step 3 — sort by score descending, return top-k (k=1):
  [doc_A]   ← score 1, the only document with any overlap
```

**Building a minimal RAG chain with `RunnableParallel`**:

```
rag_chain = (
    RunnableParallel({
        "context":  retriever | RunnableLambda(format_docs),
        "question": RunnablePassthrough(),
    })
    | rag_prompt
    | model
    | StrOutputParser()
)
```

```
┌────────────────────────────────────────────────────────────────────┐
│ INPUT: "How does attention compute weighted values?"                 │
│      │                              │                                 │
│      │ retriever.invoke(...)        │ (passthrough, unchanged)        │
│      ▼                              ▼                                 │
│  [Document(doc_A)]            "How does attention..."                │
│      │                              │                                 │
│      │ format_docs(...)             │                                 │
│      ▼                              ▼                                 │
│  "Self-attention computes..."  "How does attention..."               │
│      └─────────────┬───────────────┘                                  │
│                     ▼                                                  │
│  {"context": "Self-attention computes...",                            │
│   "question": "How does attention compute weighted values?"}          │
│                     │  rag_prompt.invoke(...)                          │
│                     ▼                                                  │
│  ChatPromptValue: [SystemMessage("Answer using ONLY this context:     │
│   Self-attention computes..."), HumanMessage("How does attention...")]│
│                     │  model.invoke(...) | StrOutputParser()           │
│                     ▼                                                  │
│  "Attention computes a weighted average of value vectors, using      │
│   weights derived from query-key dot products."                       │
└────────────────────────────────────────────────────────────────────┘
```

`format_docs` is a small `RunnableLambda` that turns `List[Document]` into a single string (e.g., joining `doc.page_content` with newlines) — necessary because the prompt template's `{context}` placeholder expects a string, not a list of objects.

### Gotcha — retrieval quality is *separate* from chain wiring

This section's point is the *wiring*: retriever → format → prompt → model → parser, all as one `Runnable`. The keyword-overlap retriever used here is deliberately naive (it would fail on `"attention"` vs `"self-attention"`, as shown in the dry run above). Swapping it for an embedding-based retriever (B02 ch08) or a hybrid/reranked retriever (Topic 5) changes *only* the `retriever` object — the rest of the chain is unchanged. This separation of concerns is exactly why LCEL composition is valuable.

---

## 7. Tools

**Summary**: A tool is a Python function with a name, a description, and a typed argument schema, packaged so a model can be told "here are the tools you may request" and can respond by *asking* for one of them to be called — the model never executes the function itself.

**The problem it solves**: A model can only generate text. If your application needs the model to "look up the weather," "query a database," or "do arithmetic," the model can't actually *do* any of that — it can only describe, in a structured way, that it *wants* one of those things done, with what arguments. Your application code is responsible for noticing this request, actually calling the function, and feeding the result back to the model. "Tools" are the standardized format for this request/response handshake.

### `@tool` — turning a function into a tool

```
@tool
def add_numbers(a: int, b: int) -> int:
    """Add two integers together and return the sum."""
    return a + b
```

The `@tool` decorator inspects the function's name (`add_numbers`), its type hints (`a: int, b: int -> int`), and its docstring (`"Add two integers together and return the sum."`), and builds a `BaseTool` object carrying all three as structured metadata — `add_numbers.name`, `add_numbers.description`, `add_numbers.args_schema`. This metadata is what gets shown to the model (typically via `model.bind_tools([...])`) so the model knows the tool exists, what it's for, and what arguments it expects.

### The tool-call message — what the model actually returns

When a model decides to use a tool, it doesn't return normal text — it returns an `AIMessage` whose `content` may be empty and whose `.tool_calls` attribute is a list of dicts:

```
AIMessage(
    content="",
    tool_calls=[
        {"name": "add_numbers", "args": {"a": 12, "b": 30}, "id": "call_001"},
        {"name": "reverse_text", "args": {"text": "hello"}, "id": "call_002"},
    ]
)
```

**Dry run of the dispatch loop** — this is the part *your application code* must implement:

```
Step 1: receive ai_message with the two tool_calls shown above

Step 2: for tool_call in ai_message.tool_calls:
           name = tool_call["name"]       # "add_numbers", then "reverse_text"
           args = tool_call["args"]       # {"a": 12, "b": 30}, then {"text": "hello"}
           id_  = tool_call["id"]         # "call_001", then "call_002"

           fn = tools_by_name[name]       # look up the actual Python function
           result = fn.invoke(args)       # add_numbers(a=12, b=30) -> 42
                                           # reverse_text(text="hello") -> "olleh"

           tool_message = ToolMessage(content=str(result), tool_call_id=id_)

Step 3: results:
   ToolMessage(content="42",    tool_call_id="call_001")
   ToolMessage(content="olleh", tool_call_id="call_002")
```

```
┌──────────────────────────────────────────────────────────────────┐
│  ROUND TRIP OF A SINGLE TOOL CALL                                  │
│                                                                      │
│  [HumanMessage("What is 12 + 30, and what is 'hello' reversed?")]  │
│        │  model.invoke(messages)  (model has tools bound)          │
│        ▼                                                            │
│  AIMessage(content="", tool_calls=[{...add_numbers...},            │
│                                     {...reverse_text...}])          │
│        │  YOUR CODE: dispatch loop (Step 2/3 above)                │
│        ▼                                                            │
│  [ToolMessage("42", call_001), ToolMessage("olleh", call_002)]     │
│        │  append all of the above to `messages` and call again     │
│        ▼                                                            │
│  model.invoke(messages + [ai_message] + tool_messages)             │
│        ▼                                                            │
│  AIMessage(content="12 + 30 = 42, and 'hello' reversed is 'olleh'.")│
└──────────────────────────────────────────────────────────────────┘
```

The `tool_call_id` is what lets the model match each `ToolMessage` result back to the specific request it made — essential when, as above, the model requests *multiple* tools in one turn (Topic 7 covers this "parallel tool calls" case in more depth).

### Gotcha — tools are *requested*, never *executed*, by the model

This is the single most important thing to internalize about tool calling: the model **cannot** run code. `AIMessage.tool_calls` is the model's text output, structured as a request. If your application code never implements the dispatch loop above, the model's request simply goes unanswered — there is no sandbox, no automatic execution, nothing happening "behind the scenes." Every agent framework in Topic 4 (LangGraph, CrewAI, etc.) is, underneath, running some version of exactly this loop — receive tool_calls, execute them, feed `ToolMessage`s back, repeat until the model stops requesting tools.

---

## Summary & Connection Forward

Seven pieces, each a `Runnable` with the same `.invoke()` interface:

```
SystemMessage / HumanMessage / AIMessage  →  the universal "conversation" data type
ChatPromptTemplate                         →  dict of variables  →  ChatPromptValue
BaseChatModel (real or Fake)               →  ChatPromptValue    →  AIMessage
Output Parsers (Str/Json/Pydantic)         →  AIMessage          →  str / dict / object
RunnableLambda / Parallel / Passthrough    →  glue for branching and custom logic
BaseRetriever                              →  str (query)        →  List[Document]
@tool + dispatch loop                      →  AIMessage.tool_calls → List[ToolMessage]
```

Every one of these compositions was built as a flat `|` chain — a single, static pipeline. The next topic, **LangGraph**, picks up exactly here and asks: what if the pipeline needs to *loop* (call a tool, see the result, decide to call another tool, repeat) or *branch* based on runtime conditions? LCEL chains are directed acyclic graphs (DAGs) — data flows one way, no cycles. LangGraph generalizes this to graphs *with* cycles and explicit, inspectable state — which is exactly what the tool-dispatch round-trip in Section 7 needs in order to *repeat* until the model is satisfied.
