# Chapter 2 — From Scratch: Problem Statements

## Table of Contents

1. [First Agent: One System Message, One Call](#1-first-agent-one-system-message-one-call)
2. [Setting Model Parameters](#2-setting-model-parameters)
3. [Structured Output, By Hand](#3-structured-output-by-hand)
4. [The Strict-JSON Wall](#4-the-strict-json-wall)
5. [Fixing the Broken Shape](#5-fixing-the-broken-shape)
6. [Tracing Without a Dashboard](#6-tracing-without-a-dashboard)
7. [Giving the Agent a Tool](#7-giving-the-agent-a-tool)
8. [The Same Tool, Structured Return Value](#8-the-same-tool-structured-return-value)
9. [Capstone: Two Chained Tools Plus Tracing](#9-capstone-two-chained-tools-plus-tracing)
10. [Bonus: Asking vs Forcing — Native Structured Output](#10-bonus-asking-vs-forcing-native-structured-output)

Each entry below is one file under `from_scratch/template/`. Work through them in order — each one reuses something built in the last. Every file uses a raw `AsyncOpenAI` client (Gemini by default, Ollama as a fallback) — never an agents framework. When you're done with a file, compare it against `from_scratch/solved/` of the same name. Don't peek before you try.

---

## 1: First Agent: One System Message, One Call

**File:** `01_first_agent.py`

### The Intuition

An "agent" at its simplest is not a framework object — it's a system prompt (the persona) plus a user message, sent to the model in one call. This file proves that by building the whole thing by hand, with nothing hidden underneath.

### What You're Building

A "Research Planner" persona is already written out for you as the `instructions` string. Your job is to:

1. Build a `messages` list: one `"system"` message using `instructions`, one `"user"` message with the topic `"learn about AI agents"`.
2. Call `client.chat.completions.create(model=MODEL_NAME, messages=messages)`.
3. Pull the model's reply out of the response and print it.

### Example

**Input** (the topic you send as the user message):
```
"learn about AI agents"
```

**Expected output** (shape — exact wording will vary by model):
```
1. Define AI agents
2. Research agent architectures
3. Study tool-use patterns
4. Compare agent frameworks
5. Read production case studies
```

Five short tasks, one per line, nothing else — that's what the persona asks for.

---

## 2: Setting Model Parameters

**File:** `02_setting_agent_model_parameters.py`

### The Intuition

Sampling parameters like `temperature` and `max_tokens` aren't special SDK objects — they're plain keyword arguments on the same `chat.completions.create` call from file 1. This file also asks you to notice something people often assume incorrectly: `temperature=0.0` makes output *more consistent*, not *perfectly identical*.

### What You're Building

1. Reuse the same persona and topic as file 1.
2. Write a function that calls the model with two extra keyword arguments: `temperature=0.0` and `max_tokens=150`.
3. Call that function **twice in a row**, with identical inputs both times.
4. Compare the two raw outputs and print whether they're byte-for-byte identical.

### Example

**Input:** same topic, `"learn about AI agents"`, called twice at `temperature=0.0`.

**Expected output (shape):**
```
Call 1 output:
1. Define AI agents
2. Research agent architectures
...

Call 2 output:
1. Define AI agents
2. Research agent architectures
...

Identical byte-for-byte? False
```

Don't be surprised if `False` shows up even though both calls used the exact same settings — providers clamp `temperature=0.0` to a tiny nonzero value internally, so there's still a sliver of randomness left. The point of this file is to *see* that firsthand, not to force a `True`.

---

## 3: Structured Output, By Hand

**File:** `03_output_types_basic.py`

### The Intuition

An agent-framework's "typed output" feature is really just three plain steps: tell the model the exact JSON shape you want in the prompt, parse the raw text back with `json.loads`, then validate it into a Pydantic model. This file builds all three steps yourself, with no framework helping.

### What You're Building

1. A Pydantic model `ResearchPlanModel` with one field: `tasks: list[str]`.
2. A system prompt that is the persona **plus** an explicit instruction: respond with *only* a JSON object of the shape `{"tasks": [...]}`, no extra text, no markdown fences.
3. A function that calls the model, then does `json.loads(raw_text)` followed by `ResearchPlanModel.model_validate(parsed_json)`, wrapped in a `try/except` that prints the raw text and re-raises if parsing fails.

### Example

**Input:** `"learn about AI agents"`

**Model's raw text response (expected shape):**
```json
{"tasks": ["Define AI agents", "Research agent architectures", "Study tool-use patterns", "Compare agent frameworks", "Read production case studies"]}
```

**Expected printed output:**
```
ResearchPlanModel.tasks (5 tasks):
  1. Define AI agents
  2. Research agent architectures
  3. Study tool-use patterns
  4. Compare agent frameworks
  5. Read production case studies
```

---

## 4: The Strict-JSON Wall

**File:** `04_output_types.py`

### The Intuition

Agent frameworks that support "strict JSON mode" reject certain Pydantic shapes *before ever making a network call* — for example, `dict[int, str]` (a dictionary with arbitrary integer keys) can't be expressed as a strict JSON Schema, because strict mode requires a fixed, closed set of named properties, and an arbitrary-keys dict has no such fixed set. This file has **no LLM call in it at all** — it's a pure schema-validation exercise proving the rejection is 100% client-side.

### What You're Building

A recursive function, `assert_strict_json_schema(schema: dict) -> None`, that walks a JSON Schema dict and enforces two rules at every object-typed node (a node with `"type": "object"` or a `"properties"` key):

1. `additionalProperties` must be present **and** be exactly `False` — not missing, not a nested sub-schema.
2. Every key listed under `properties` must also appear in `required`.

The function must recurse into nested schemas (values under `properties`, the `items` of an array, etc.), and raise `ValueError` with a message naming *where* in the schema the violation is and *why*, the moment it finds the first violation (rule 1 checked before rule 2, at each node).

Two helper functions are provided for you to test against: `build_valid_strict_schema()` (a closed, fully-required shape — should pass) and `build_broken_arbitrary_keys_schema()` (models `tasks: dict[int, str]` — should raise).

### Example

**Input 1 — a valid schema** (closed `list[Task]` shape):
```python
{
    "type": "object",
    "properties": {"tasks": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "description": {"type": "string"}},
        "required": ["id", "description"],
        "additionalProperties": False,
    }}},
    "required": ["tasks"],
    "additionalProperties": False,
}
```
**Expected output:** no exception raised.

**Input 2 — the broken schema** (arbitrary-keys dict):
```python
{
    "type": "object",
    "properties": {"tasks": {
        "type": "object",
        "additionalProperties": {"type": "string"},   # <-- open-ended, not False
        "properties": {},
        "required": [],
    }},
    "required": ["tasks"],
    "additionalProperties": False,
}
```
**Expected output:** a `ValueError` is raised, with a message naming the path (e.g. `$.properties.tasks`) and explaining that an open `additionalProperties` sub-schema can't be expressed as a fixed set of properties.

---

## 5: Fixing the Broken Shape

**File:** `05_output_types_fixed.py`

### The Intuition

The fix for file 4's broken shape isn't a framework workaround — it's a schema-design change: replace the open-ended `dict[int, str]` with a closed, enumerable `list[Task]`, where every `Task` has the *same* named fields. This file goes back to making a real LLM call (same pattern as file 3), just with the corrected shape.

### What You're Building

1. A `Task` model with two fields: `id: int`, `description: str`.
2. A `ResearchPlanModel` with `tasks: list[Task]`.
3. The same JSON-prompt → call → `json.loads` → `model_validate` pattern from file 3, but asking for the new shape: `{"tasks": [{"id": 1, "description": "..."}, ...]}`.

### Example

**Input:** `"learn about AI agents"`

**Expected output:**
```
task 1: Define AI agents
task 2: Research agent architectures
task 3: Study tool-use patterns
task 4: Compare agent frameworks
task 5: Read production case studies
```

---

## 6: Tracing Without a Dashboard

**File:** `06_agent_with_tracing.py`

### The Intuition

A framework's "trace" isn't a separate thing it computes behind the scenes — it's just the ordered list of messages that already exists the moment you build a `messages` list and call the model with it. There's nothing extra to construct. This file proves that by writing a `print_trace(messages)` function that walks a plain list and narrates what happened.

### What You're Building

1. Reuse file 5's fixed agent (same persona, same JSON shape, no tools yet).
2. After getting the model's response, append it back onto `messages` as an `{"role": "assistant", "content": ...}` entry — this one append *is* the entire "recording" step.
3. Write `print_trace(messages)`: iterate over `messages` and print one line per assistant message, one line per tool call (none exist yet in this file), and one line per tool result (also none yet). For this file, the trace should just show the final assistant message — the *absence* of any `[tool]` line is itself proof no tool was called.

### Example

**Expected output (end of run):**
```
task 1: Define AI agents
...

  [trace] assistant produced a message: '{"tasks": [...]}'
```

---

## 7: Giving the Agent a Tool

**File:** `07_agent_with_tool.py`

### The Intuition

A "tool" is just two things: a JSON schema describing the tool's name/parameters (which a framework's decorator would normally auto-generate for you — here you write it by hand), and a plain Python function that actually runs when the model asks for it. Driving the call → tool-call → dispatch → re-call loop is also just a `while`/`for` loop you write yourself — there's no hidden orchestration.

### What You're Building

1. A tool schema dict for `get_research_sources` (already given), and its handler function (already given, returns `["Wikipedia", "Google", "YouTube"]`).
2. `run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6)`: calls the model with `tools=tools_schema`; if the response has no `tool_calls`, append the final assistant message and return; otherwise append the assistant's tool-call message, then for each tool call: parse its arguments, look up and call the matching handler, append a `{"role": "tool", ...}` message with the result, and loop again.
3. In `main()`: run the tool loop first (free-form plan in prose comes back). Then append **one more** user message onto the *same* `messages` history asking the model to convert the plan into JSON of the shape `{"tasks": [{"id": ..., "description": ..., "source": ...}, ...]}` — note the new `source` field, naming which tool result each task relied on. Call the model once more, **without** `tools=` this time, and parse the result into a `ResearchPlanModel` (now with a `Task` that has an extra `source: str` field).

### Example

**Expected console flow:**
```
STEP 1: Building messages and running the tool loop
  user message: 'learn about AI agents'
    [tool] get_research_sources({}) -> ['Wikipedia', 'Google', 'YouTube']

  free-form plan text after the tool loop:
  1. Search Wikipedia for AI agent definitions
  2. Use Google to find recent agent research
  ...

STEP 2: PHASE TWO -- one more, tool-less call to extract JSON
  raw JSON text back from the model:
  {"tasks": [{"id": 1, "description": "...", "source": "Wikipedia"}, ...]}

STEP 3: Parsing into the typed, tool-informed ResearchPlanModel
  task 1: Search Wikipedia for AI agent definitions  (source: Wikipedia)
  ...
```

---

## 8: The Same Tool, Structured Return Value

**File:** `07x_agent_with_tool_extended.py`

### The Intuition

A tool's return value can be anything JSON-serializable — a string, a list of strings, a list of dicts, whatever. Nothing about the dispatch mechanism changes based on what shape a handler returns. This file proves that by changing `get_research_sources`'s return type from `list[str]` to `list[dict]` (each a `{"name": ...}` record) and showing that `run_tool_loop` doesn't need a single line changed.

### What You're Building

1. Change `get_research_sources()` to return `[{"name": "Wikipedia"}, {"name": "Google"}, {"name": "YouTube"}]` instead of plain strings.
2. Update the persona's instructions to mention that each source is now a record with a `"name"` field.
3. Reuse `run_tool_loop` completely unchanged from file 7.
4. In the phase-two JSON-extraction prompt, tell the model to use each source's `"name"` value as the plain `source` string in the output (the output `Task` shape itself doesn't change — still `id`, `description`, `source: str`).

### Example

**Expected console flow (compare against file 7's output):**
```
    [tool] get_research_sources({}) -> [{'name': 'Wikipedia'}, {'name': 'Google'}, {'name': 'YouTube'}]

  ...

  task 1: Search Wikipedia for AI agent definitions  (source: Wikipedia)
```

Notice the tool now returns structured records, but the final printed output looks identical in shape to file 7's — that's the point.

---

## 9: Capstone: Two Chained Tools Plus Tracing

**File:** `08_agent_with_tools_tracing.py`

### The Intuition

**Tool chaining** means the second tool needs information that only the first tool's result can supply — and there's no special API for this. Both tools just get registered together in the same list; the *model* decides, on its own, to call the first tool, read its result out of the conversation history, and then call the second tool using something it just saw. This capstone combines everything from files 1–8: two tools, structured output, and tracing, all in one file.

### What You're Building

1. Two tool schemas + handlers: `get_research_sources()` (same as file 7, returns plain source-name strings) and a **new** `get_resource_url(source: str) -> str`, which looks up a hardcoded URL for a known source name (with a fallback URL for unknown names, so it never crashes even if the model passes something unexpected).
2. Register **both** tools together in one `tools_schema` list and one `tool_handlers` dict, and pass them to the same `run_tool_loop` from file 7 — unchanged, since it already handles however many tools/tool-calls show up.
3. Update the persona: first call `get_research_sources`, then call `get_resource_url` for at least one of the returned names, then produce the plan.
4. Extend `Task` with a second new field: `source_url: str`.
5. After getting the typed, tool-informed plan, call `print_trace(messages)` and confirm — by reading the printed trace, not by guessing — that both tool calls appear **in order**, before the final assistant message. That ordering is your proof that chaining actually happened.

### Example

**Expected console flow:**
```
STEP 1: Building messages and running the tool loop (2 tools)
    [tool] get_research_sources({}) -> ['Wikipedia', 'Google', 'YouTube']
    [tool] get_resource_url({'source': 'Wikipedia'}) -> https://wikipedia.org

  free-form plan text after the tool loop:
  ...

STEP 3: Parsing into the typed, tool-informed ResearchPlanModel
  task 1: Search Wikipedia for AI agent definitions  (source: Wikipedia, url: https://wikipedia.org)
  ...

STEP 4: print_trace(messages) -- confirm BOTH tool calls appear, in order
    [trace] assistant called tool: get_research_sources({})
    [trace] tool result: ["Wikipedia", "Google", "YouTube"]
    [trace] assistant called tool: get_resource_url({"source": "Wikipedia"})
    [trace] tool result: "https://wikipedia.org"
    [trace] assistant produced a message: '{"tasks": [...]}'
```

If your trace ever showed `get_resource_url` called *before* `get_research_sources`, that would mean the model guessed a source name instead of actually chaining — worth noticing if it happens, since the handler's fallback URL means it wouldn't crash, it would just silently not be "real" chaining.

---

## 10: Bonus: Asking vs Forcing — Native Structured Output

**File:** `09_native_structured_output.py`

This entry is not part of the numbered sequence above (it isn't built on by any later file) — it exists to let you *feel* the difference between the "asking" and "forcing" mechanisms described in the chapter 2 notes (section 8, "How Strict Mode Actually Works"), rather than just read about it.

### The Intuition

Every file so far (3, 5, 7, 8) used the ASKING path: describe the target shape in plain English inside the system prompt, call the model, then parse and validate the raw text yourself afterward, inside a `try/except` for when the model doesn't comply. Nothing in that pipeline stops the model from writing a sentence of prose before the JSON — the `try/except` exists precisely because nothing enforces compliance.

The alternative is FORCING: send the schema itself with the request, and let the provider constrain which tokens the model is even allowed to generate, so invalid output becomes structurally impossible rather than just unlikely.

### What You're Building

Run the same persona and topic through three paths, and print each one's result so you can compare them directly:

1. **Path A (asking)** — reuse file 5's approach: append an `**OUTPUT FORMAT**` block to the persona, call `gemini_client.chat.completions.create(...)`, then `json.loads` + `ResearchPlanModel.model_validate(...)` the raw text, inside a `try/except (json.JSONDecodeError, ValidationError)` that prints the raw text and re-raises.
2. **Path B (Gemini, forcing)** — call `await gemini_client.chat.completions.parse(model=GEMINI_MODEL_NAME, messages=[...], response_format=ResearchPlanModel)` with the persona's plain instructions (no hand-written JSON-format block needed). Check `response.choices[0].message.refusal` first; if truthy, raise naming it. Otherwise `.parsed` is already a validated `ResearchPlanModel` instance.
3. **Path C (Ollama, forcing)** — call `await ollama_client.chat(model=OLLAMA_MODEL_NAME, messages=[...], format=ResearchPlanModel.model_json_schema(), think=False)` on a *separate* client (`ollama.AsyncClient`, not `AsyncOpenAI`). Read the raw text off `response.message.content` (Ollama's `ChatResponse` has a single `message` field, no `.choices` list), then run it through `ResearchPlanModel.model_validate_json(...)` yourself. Pass `think=False` — with thinking left on, qwen3:8b has been observed returning a schema-valid but empty `{"tasks": []}`, since the grammar only promises well-formed JSON, never a non-empty list.
4. Run all three, print each one's tasks, and print a one-line summary per path noting which mechanism it used and whether it needed a `try/except` for shape errors.

### Example

**Expected console flow (shape):**
```
PATH A: ASKING (Gemini, prompt text + json.loads + model_validate)
  raw text back from the model:
  {"tasks": [...]}
  task 1: ...

PATH B: FORCING (Gemini, response_format=ResearchPlanModel)
  task 1: ...

PATH C: FORCING (Ollama, format=ResearchPlanModel.model_json_schema())
  raw text back from the model:
  {"tasks": [...]}
  task 1: ...

SUMMARY
  Path A (Gemini, asking)  : prompt text only -- needed try/except for shape errors
  Path B (Gemini, forcing) : response_format=  -- no try/except needed for shape
  Path C (Ollama, forcing) : format=            -- no try/except needed for shape
```
