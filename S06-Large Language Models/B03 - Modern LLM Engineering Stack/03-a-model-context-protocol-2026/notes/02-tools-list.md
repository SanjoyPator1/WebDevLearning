# `tools/list` — What the Model Actually Sees

## Table of contents

- [One sentence](#one-sentence)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The anatomy of a tool entry](#layer-2-the-anatomy-of-a-tool-entry)
  - [The docstring is prompt text, not documentation](#the-docstring-is-prompt-text-not-documentation)
  - [Argument descriptions are separate, and people forget them](#argument-descriptions-are-separate-and-people-forget-them)
  - [The four annotation hints](#the-four-annotation-hints)
  - [Return a pydantic model, not a dict](#return-a-pydantic-model-not-a-dict)
  - [A gotcha I hit while writing this file](#a-gotcha-i-hit-while-writing-this-file)
- [`ttlMs`, `cacheScope`, and why order matters](#ttlms-cachescope-and-why-order-matters)
  - [The cache hint](#the-cache-hint)
  - [Deterministic order](#deterministic-order)
- [Layer 3 — Dry-run: reading a schema the way a model does](#layer-3-dry-run-reading-a-schema-the-way-a-model-does)
- [The bad error path, on purpose](#the-bad-error-path-on-purpose)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

`tools/list` returns the menu card your server hands the language model, and almost
everything that makes an MCP server good or bad about tool use is decided in that one
response.

## The problem this topic solves

A model cannot call a tool it does not understand. It has no access to your code, your
tests, or your intentions. It has a name, a description, and a JSON Schema — and from
those three things it must decide *whether* to call your tool and *what to put in the
arguments*.

So `tools/list` is not a directory listing. It is a prompt. The fact that most of it is
generated for you from Python type hints makes it easy to forget that a model reads every
character of it.

This chapter is about controlling what ends up there.

## Layer 1 — The intuition

You are hiring a temp for the counter. You will not be there. You get one laminated card
to leave them.

A bad card says: `get_drink(slug)`. The temp has no idea what a slug is, where to get
one, or what happens if they guess wrong.

A good card says: *"Look up one drink by its slug — lowercase with hyphens, exactly as it
appears in `list_drinks`, e.g. `flat-white`. If you do not already know the exact slug,
call `list_drinks` first rather than guessing."*

Same function. The second card produces a temp who does the right thing on the first try;
the first produces one who guesses `"Flat White"`, gets an error, and guesses again.

That is the entire subject. The model is the temp, and `tools/list` is the card.

## Layer 2 — The anatomy of a tool entry

Here is one real entry from the café, trimmed:

```json
{
  "name": "get_drink",
  "description": "Look up the detail of a single drink by its slug.\n\n    Use this when the customer has named a drink and you need its price...",
  "annotations": {
    "title": "Get one drink",
    "readOnlyHint": true,
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false
  },
  "inputSchema": {
    "type": "object",
    "title": "get_drinkArguments",
    "properties": {
      "slug": {
        "type": "string",
        "title": "Slug",
        "description": "The drink's slug, lowercase with hyphens, exactly as it appears in `list_drinks` — for example 'flat-white' or 'cold-brew'. Not the display name."
      }
    },
    "required": ["slug"]
  },
  "outputSchema": { "...": "see below" }
}
```

Every one of those fields came from Python, and it is worth knowing exactly which piece
of Python produced which field.

```text
  @mcp.tool(annotations=ToolAnnotations(title="Get one drink", ...))
            └──────────────────────────────────────────────────┘
                          →  entry["annotations"]

  def get_drink(slug: Annotated[str, Field(description="...")]) -> DrinkResult:
      │         └──────┬─────┘  └──────────┬────────────────┘     └─────┬─────┘
      │                │                   │                           │
      │       inputSchema.properties        │                    outputSchema
      │       .slug.type = "string"         │
      │                          inputSchema.properties
      │                          .slug.description
      │
      └─────►  entry["name"] = "get_drink"

      """Look up the detail of a single drink by its slug. ..."""
      └──────────────────────────┬──────────────────────────┘
                       →  entry["description"]
```

### The docstring is prompt text, not documentation

This is the highest-leverage idea in the chapter, so let us be precise about it.

The docstring goes to the model **verbatim**, including the indentation. Here is the
literal bytes on the wire:

```text
"description": "Look up the detail of a single drink by its slug.\n\n    Use this when
the customer has named a drink and you need its price, its caffeine content, or which
sizes it comes in. If you do not already know the exact slug, call `list_drinks` first
rather than guessing.\n\n    Returns the drink plus `available_sizes` — the sizes it is
genuinely sold in, which is not always all three.\n    "
```

So the question to ask when writing a tool docstring is not *"have I documented this
function?"* It is *"if a competent assistant read only this, would they use the tool
correctly?"*

Three habits follow from that:

**Say when, not just what.** "Look up a drink" describes the function. "Use this when the
customer has named a drink and you need its price" tells the model which situation
triggers it. Models pick tools by matching situations, not by reading signatures.

**Name the recovery path.** "If you do not already know the exact slug, call
`list_drinks` first rather than guessing" removes an entire class of failed call. You are
writing the model's error-handling for it, in advance, for free.

**Warn about the thing that is not obvious.** "which is not always all three" is one
clause, and it prevents the model confidently offering a large espresso.

### Argument descriptions are separate, and people forget them

The docstring describes the *tool*. `Annotated[str, Field(description=...)]` describes
one *argument*. Both reach the model; only the first is automatic.

```python
slug: Annotated[
    str,
    Field(description=(
        "The drink's slug, lowercase with hyphens, exactly as it appears in "
        "`list_drinks` — for example 'flat-white' or 'cold-brew'. Not the display name."
    )),
]
```

That "Not the display name" is doing real work. Without it, a model that has seen
"Flat White" in conversation will pass `"Flat White"` roughly half the time.

Google-style `Args:` blocks in the docstring are *not* parsed into per-argument
descriptions by this SDK — they just become part of the description blob. They are still
worth writing for humans, but if you want the schema populated, use `Field`.

### The four annotation hints

```python
ToolAnnotations(
    title="Get one drink",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
```

These are **promises**, and the protocol does not enforce a single one of them. Hosts use
them to decide what needs a permission prompt and what can run silently. So a wrong hint
is not a cosmetic error — it is how you get a destructive tool executed without anyone
being asked.

| Hint | Question it answers | The café |
|------|---------------------|----------|
| `read_only_hint` | Does calling this change anything in the world? | `get_drink` → `True`; `place_order` → `False` |
| `destructive_hint` | If it does change things, can that change be undone? | Only meaningful when `read_only_hint` is `False`. `place_order` → `True` |
| `idempotent_hint` | Is calling it twice the same as calling it once? | `get_drink` → `True`; `place_order` → `False`, two calls make two orders |
| `open_world_hint` | Does it reach outside this server's own world? | The café is self-contained → `False`. A web-search tool → `True` |

`title` is the human-facing label a host shows in a permission dialog. `name` is the
machine identifier the model calls. Different audiences, so different strings.

A useful discipline: set `read_only_hint=True` only when you can say out loud "calling
this a thousand times in a row is harmless". Everything in this chapter passes that test;
nothing from topic 07 onwards does.

### Return a pydantic model, not a dict

Compare what the two produce.

Return `-> str` (topic 01's `hello`) and the SDK has to invent a shape, so it wraps it:

```json
"outputSchema": {"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]}
```

Return `-> MenuResult` and you get a real schema, with the nested `Drink` model hoisted
into `$defs` and referenced:

```json
"outputSchema": {
  "$defs": {
    "Drink": {
      "type": "object",
      "description": "One item on the café menu: a drink, its prices per size, and its properties.",
      "properties": {
        "slug":        {"type": "string",  "description": "Stable machine identifier, e.g. 'flat-white'."},
        "prices":      {"type": "object",  "additionalProperties": {"type": "number"},
                        "description": "Price per available size. A size absent here is not orderable."},
        "caffeine_mg": {"type": "integer", "description": "Approximate caffeine content in milligrams."},
        "dairy_free":  {"type": "boolean", "description": "True if the drink contains no dairy by default."}
      },
      "required": ["slug", "name", "description", "prices", "caffeine_mg", "dairy_free"]
    }
  },
  "properties": {
    "drinks": {"type": "array", "items": {"$ref": "#/$defs/Drink"}, "description": "Every drink, in stable menu order."},
    "count":  {"type": "integer", "description": "How many drinks are listed."}
  },
  "required": ["drinks", "count"]
}
```

Return `-> dict` and you get nothing useful at all: the model learns only that an object
comes back.

The knock-on effect shows up in the *result*, which carries two representations of the
same answer:

```json
"content": [{"type": "text", "text": "{\n  \"drink\": {...}\n}"}],
"structuredContent": {"drink": {"slug": "espresso", ...}, "available_sizes": ["S", "M"]}
```

`content` is for the model. `structuredContent` is for code — a client can validate it
against `outputSchema` and hand your caller a typed object instead of a string it has to
parse. One `return` statement produced both. In 2026-07-28, `structuredContent` may be
*any* JSON value, not only an object — the schema keywords were loosened at this revision.

### A gotcha I hit while writing this file

The `Drink` class originally had this docstring:

```python
class Drink(BaseModel):
    """One item on the menu.

    Being a pydantic model rather than a dict is not decoration: from topic 02
    onwards these get returned straight out of MCP tools, and the SDK turns the
    model's schema into the tool's `outputSchema`.
    """
```

That entire note-to-self came back on the wire, as the `description` of `Drink` inside
`outputSchema`, and would have been read by the model on every `tools/list`.

**A pydantic model's class docstring is published to the model.** So is a `Field`'s
description. Keep implementation commentary in `#` comments, which stay on your side of
the wire, and keep docstrings as text you would be happy for a model to read. `menu.py`
now carries exactly that warning above the class.

## `ttlMs`, `cacheScope`, and why order matters

### The cache hint

New in 2026-07-28: results from `tools/list`, `prompts/list`, `resources/list`,
`resources/read` and `resources/templates/list` **must** carry two fields.

```python
mcp = MCPServer(
    ...,
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)
```

Omit the argument and you get the safe default, which is also the useless one:

```text
topic 01 (no hint)  ->  "ttlMs": 0,      "cacheScope": "private"
topic 02 (hinted)   ->  "ttlMs": 300000, "cacheScope": "public"
```

`ttlMs` is a freshness hint in milliseconds: *you may reuse this for five minutes without
asking again*. It is a hint, not a guarantee, and it complements rather than replaces the
`listChanged` notification — the notification says "it changed now", the TTL says "if you
hear nothing, re-ask in five minutes".

`cacheScope` is the interesting one, because it is a **judgement you have to make** and
getting it wrong is a data leak.

- `"public"` — a shared intermediary may cache this and serve it to someone else.
- `"private"` — only the requesting client may hold it.

`"public"` is correct for the café's tool list because that list is byte-identical for
every caller: no per-user pricing, no auth-dependent filtering, no tenant-specific tools.
The moment any of those becomes true, `"public"` means a shared proxy will hand one
customer another customer's menu. The rule of thumb: if the response could differ based
on *who* asked, it is `"private"`.

### Deterministic order

The spec adds a SHOULD: return tools from `tools/list` in a deterministic order. It reads
like tidiness. It is about money.

The tool list sits near the front of the prompt sent to the model on every turn. Providers
cache prompt *prefixes* — if the first N tokens are identical to last time, you are billed
at a large discount for them. Reshuffle your tool list and the prefix changes, the cache
misses, and you pay full price for the entire prompt on every call.

The SDK preserves registration order, so determinism is free. You only lose it by
accident, and there are three classic ways:

```python
for name in set(tool_names):        # sets have no order
for name in os.listdir(plugin_dir): # filesystem order, varies by machine
tools = {**base, **extra}.values()  # fine in modern Python, but fragile
```

Prove it to yourself: swap `list_drinks` and `get_drink` in `solved/t02_tools.py`,
restart, run `curl/02_tools_list.sh`, and watch the wire order follow. Same reasoning
applies to the *contents* of a list a model sees, which is why `menu.py` uses a tuple with
a comment saying the order is load-bearing.

## Layer 3 — Dry-run: reading a schema the way a model does

Take `get_drink`'s schema and ask what a model can infer, step by step.

```json
{
  "type": "object",
  "required": ["slug"],
  "properties": {
    "slug": {"type": "string", "description": "... lowercase with hyphens, exactly as it appears in `list_drinks` ... Not the display name."}
  }
}
```

**Step 1.** `type: "object"` — arguments are a JSON object. Always true for MCP tools.

**Step 2.** `required: ["slug"]` — one mandatory field. If the model has no slug it must
get one before calling. `list_drinks` is named in the description, so it knows how.

**Step 3.** `slug` is a `string`. Not an enum — so the schema alone does not restrict the
value, and the *description* is doing all the constraining work. This is exactly the case
where a weak description costs you calls.

**Step 4.** "lowercase with hyphens" plus two examples plus "Not the display name". A
model that has "Flat White" in its context now has enough to produce `"flat-white"`.

Now do the same read on a schema with the description removed:

```json
{"type": "object", "required": ["slug"], "properties": {"slug": {"type": "string"}}}
```

Step 4 has nothing to work with. `"Flat White"`, `"flat white"`, `"FlatWhite"` and
`"flat-white"` are all equally consistent with that schema. You will see all four in
production traces.

If your slugs really are a closed set, say so in the schema rather than in prose — a
`Literal[...]` type hint becomes a JSON Schema `enum`, and then the argument cannot be
wrong. The café keeps `str` on purpose so that this lesson has something to land on, and
because a real menu changes without a code deploy.

## The bad error path, on purpose

`get_drink` in this topic raises a bare `ValueError` when the slug is unknown. That is
wrong, and it is here so you can see precisely how wrong. Run:

```bash
bash curl/02_get_drink.sh no-such-drink
```

```json
{
  "result": {
    "content": [{"type": "text", "text": "Error executing tool get_drink"}],
    "isError": true,
    "resultType": "complete"
  }
}
```

`"no such drink: no-such-drink"` is gone. The model is told that something failed and
nothing about what, so its options are to give up or retry the identical call. Both are
bad, and the second is worse.

Now contrast a *schema* failure:

```bash
bash curl/call.sh get_drink '{"slug": 123}'
```

```json
{"content": [{"type": "text", "text": "Error executing tool get_drink: 1 validation error for get_drinkArguments\nslug\n  Input should be a valid string [type=string_type, input_value=123, input_type=int]"}],
 "isError": true}
```

Here the message comes through in full. Notice that you did not write a single line of code to generate this message! 

The asymmetry is deliberate on the SDK's part. It uses a library called **Pydantic** under the hood to automatically validate incoming arguments against your Python type hints (like `slug: str`). 
Because this validation happens *before* your code ever runs, and because the SDK's validator generated the error text itself, its wording is known to be perfectly safe to reveal to the LLM. 

By contrast, a runtime exception thrown from *your* custom code (like `ValueError` or `KeyError`) is not safe to reveal by default — it might contain a connection string, an internal path, or a stack detail. Withholding custom exceptions is the right security default.

Which means the SDK is not being unhelpful; it is waiting for you to say "this particular
message is safe and useful for a model to read". The way you say that is `ToolError`, and
that is topic 03.

## Gotchas

**Docstrings are prompts.** If you would not want a model to read it, it is not a
docstring.

**Class docstrings and `Field` descriptions are published too.** Including on nested
models, via `$defs`.

**`Args:` in a docstring does not populate argument descriptions.** Use
`Annotated[T, Field(description=...)]`.

**Annotation hints are promises, not enforcement.** Nothing checks them. Getting
`read_only_hint` wrong is how a destructive tool runs without a prompt.

**`cacheScope: "public"` on anything caller-dependent is a data leak.** Ask "could this
differ by who asked?" before choosing.

**A no-argument tool still publishes a schema.** `{"type": "object", "properties": {}}`.
That is correct, not a bug.

**Returning `dict` throws away the output schema.** It costs five lines to define a
pydantic model and the model on the other end gets a real contract.

## Your turn

`solutions/t02_tools.py`, six TODOs. `cafe_mcp/menu.py` is given to you complete — it is
data, and copying twelve drinks teaches nothing.

The one worth taking seriously is TODO 2, the cache scope. Write the comment explaining
*why* you chose what you chose. If you cannot write that sentence, you do not yet know
whether the choice is safe.

When you finish, run `bash curl/02_tools_list.sh` and read the output as though you were
the model. Would you use `get_drink` correctly having read only that?

## Connection forward

You now control what the model sees. Topic 03 is about what happens when it calls: how
arguments are validated and by whom, what `structuredContent` is really for, and the
distinction that catches everyone — why a failing tool returns a **successful** JSON-RPC
response with `isError: true` rather than a JSON-RPC `error`, and why `ToolError` is the
only exception you should ever raise on purpose.

Does this make sense? Want me to go deeper on any part — how type hints become JSON
Schema, the annotation hints and their security role, or the prompt-cache argument for
deterministic ordering?
