# Prompts, and `completion/complete`

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem prompts solve](#the-problem-prompts-solve)
- [Layer 1 — The intuition, and the thing worth noticing](#layer-1-the-intuition-and-the-thing-worth-noticing)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [Declaring a prompt](#declaring-a-prompt)
  - [The return value is messages, not a string](#the-return-value-is-messages-not-a-string)
  - [Embedded resources in messages](#embedded-resources-in-messages)
  - [How a prompt fails — and the trap](#how-a-prompt-fails-and-the-trap)
  - [`prompts/get` is not cacheable](#promptsget-is-not-cacheable)
- [`completion/complete`](#completioncomplete)
  - [The gap it fills](#the-gap-it-fills)
  - [One handler, two reference types](#one-handler-two-reference-types)
  - [Completing a template placeholder](#completing-a-template-placeholder)
  - [Context-aware completion — the part worth building](#context-aware-completion-the-part-worth-building)
  - [`total` and `has_more`](#total-and-has_more)
  - [Keep the vocabulary in one place](#keep-the-vocabulary-in-one-place)
- [Layer 3 — Dry-run: a slash command, end to end](#layer-3-dry-run-a-slash-command-end-to-end)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

A prompt is a message template the **user** invokes and the **server author** words, and
`completion/complete` is the autocomplete that tells a client what may go in an argument
or a URI placeholder.

## Where this sits

Topic 04 built the control table. Here is the third row.

```text
   tool      →  the MODEL decides to use it        topics 02, 03
   resource  →  the HOST or USER attaches it       topic 04
   prompt    →  the USER invokes it                THIS TOPIC
```

With this chapter, all ten client-to-server methods of 2026-07-28 have been exercised
somewhere in topics 01 to 05:

```text
server/discover           topic 01
tools/list                topic 02
tools/call                topic 03
resources/list            topic 04
resources/read            topic 04
resources/templates/list  topic 04
prompts/list              topic 05
prompts/get               topic 05
completion/complete       topic 05
subscriptions/listen      topic 11   <- the only one left
```

## The problem prompts solve

A tool description can say *when* to call something. It cannot say *how to answer*.

There is no field in a tool schema for "explain this to someone who has never ordered
coffee beyond instant, in two or three sentences, and do not use the word 'microfoam'
without explaining it". That is not a description of a capability; it is a description of
a *style of reply*. It belongs in a message, not a schema.

Prompts are where a server author gets to write messages.

## Layer 1 — The intuition, and the thing worth noticing

Back to the counter one last time. A prompt is the card in the drawer labelled *"if a
customer asks for a recommendation, read this out"*. The temp does not use it on their own
initiative. You did not tape it to the wall. The **customer** triggers it, by asking.

Now the part worth pausing on.

The user types one word — `/order_for_me sleepy`. What the model receives is this:

```text
[user] <the whole menu, as an embedded markdown resource>
[user] The customer is sleepy — needs caffeine, the more the better.

       Recommend exactly one drink from the menu above, and a size. Give one
       sentence of reasoning that refers to how they are feeling. Do not list
       alternatives unless they ask.
```

The user supplied `sleepy`. **You supplied everything else.** "Exactly one drink." "And a
size." "One sentence." "Do not list alternatives." Every one of those constraints is a
behavioural decision made by the server author, invisible to the person who typed the
command, and not overridable by them.

That is a lot of power sitting in a function that looks like a template helper. It is also
the reason a vague prompt is worse than no prompt: the user gets a vague assistant and has
no way to see why, because they never see the text you wrote.

So the exercise in this topic is only half about API calls. The other half is: *write a
good sentence.*

## Layer 2 — The mechanics

### Declaring a prompt

```python
@mcp.prompt(name="order_for_me", title="Order something for me")
def order_for_me(
    mood: Annotated[str, Field(description="How the customer feels right now. One of: sleepy, sweet-tooth, ...")],
    dairy_free: Annotated[bool, Field(description="Set true to restrict the recommendation to dairy-free drinks.")] = False,
) -> list[Message]:
    """Recommend a drink based on how the customer is feeling.

    Invoke this when a customer says something like "surprise me" or "what should I
    get?" rather than naming a drink. ...
    """
```

`prompts/list` publishes it:

```json
{
  "name": "order_for_me",
  "title": "Order something for me",
  "description": "Recommend a drink based on how the customer is feeling. ...",
  "arguments": [
    {"name": "mood", "required": true,
     "description": "How the customer feels right now. One of: sleepy, sweet-tooth, ..."},
    {"name": "dairy_free", "required": false,
     "description": "Set true to restrict the recommendation to dairy-free drinks."}
  ]
}
```

Three things to take from that.

**`required` comes from having a Python default.** `mood` has none, so `required: true`.
`dairy_free = False`, so `required: false`. There is no separate declaration.

**Argument descriptions come from `Annotated[..., Field(description=...)]`,** exactly as
they do for tools. They are *especially* important here, because the consumer is often a
human staring at a slash-command form. Without a description a host shows a bare argument
name and no hint about what to type, and the command is unusable. This is the single most
commonly skipped thing in MCP prompts.

**Arguments arrive as strings.** There is no JSON typing in `params.arguments` for prompts
the way there is for tools — a boolean is the *string* `"true"`. Your type hint coerces it
back. Verified:

```text
{"mood": "sleepy", "dairy_free": "true"}   ->  Python dairy_free is True
{"mood": "sleepy", "dairy_free": "false"}  ->  Python dairy_free is False
```

So `bool` is a safe hint. Do not write your own `== "true"` parsing.

### The return value is messages, not a string

```python
return [
    {
        "role": "user",
        "content": {
            "type": "resource",
            "resource": {"uri": menu_uri, "mimeType": "text/markdown", "text": menu_text},
        },
    },
    UserMessage(
        f"The customer is {mood} — {MOODS[mood]}.{constraint}\n\n"
        f"Recommend exactly one drink from the menu above, and a size. ..."
    ),
]
```

You are handing the client a **conversation opener**, and it can have several turns. The
SDK accepts `UserMessage`, `AssistantMessage`, or plain dicts, and normalises them.

A multi-turn return is occasionally exactly right — an `AssistantMessage` can seed the
model's own voice, e.g. `AssistantMessage("Let me check the menu.")` — but be sparing.
Putting words in the assistant's mouth is a strong technique and an easy way to produce
something that reads as stilted.

### Embedded resources in messages

The first message above is not text. Its content type is `"resource"`:

```json
{
  "role": "user",
  "content": {
    "type": "resource",
    "resource": {"uri": "cafe://menu", "mimeType": "text/markdown", "text": "# The Café Menu\n\n| Drink | Slug | S | M | L | ..."}
  }
}
```

This is better than pasting the markdown into a string, for a reason worth stating: the
client learns **which URI the text came from**. Which means it can cache it under that URI,
deduplicate it against a copy it already holds from topic 04's `resources/read`, or show a
human where the data came from. A pasted string is anonymous — the client sees characters
and can do none of those things.

Rule of thumb: if the text you are embedding *has* a URI on your server, send it as a
resource. If you generated it for this prompt alone, send it as text.

Note the dairy-free branch changes the URI too, not just the text:

```text
dairy_free=false  ->  messages[0].content.resource.uri == "cafe://menu"             (1176 chars)
dairy_free=true   ->  messages[0].content.resource.uri == "cafe://menu/dairy-free"  ( 633 chars)
```

Half the tokens, and a URI the client can recognise.

### How a prompt fails — and the trap

Prompts have **no dedicated exception type**. There is no `PromptError` to match
`ToolError` and `ResourceError`, and that absence is a real trap, because the default
behaviour is the worst of the three primitives.

Look at `MCPServer.get_prompt` in the SDK:

```python
try:
    prompt = self._prompt_manager.get_prompt(name)
    if not prompt:
        raise ValueError(f"Unknown prompt: {name}")
    rendered = await prompt.render(arguments, context)
    ...
except MCPError:
    raise                              # <-- passed through untouched
except Exception as e:
    raise ValueError(str(e)) from e     # <-- becomes -32603 at the dispatcher
```

Everything except `MCPError` is flattened into a `ValueError` and surfaces as:

```json
{"error": {"code": -32603, "message": "Internal server error"}}
```

And this swallows *more* than your own exceptions. A **pydantic argument-validation
failure** — a bad `Literal`, a missing required argument — also comes back as the opaque
`-32603`. Verified:

```text
prompts/get p {"budget": "nonsense"}    ->  -32603  "Internal server error"
prompts/get p {}   (missing required)   ->  -32603  "Internal server error"
```

Compare with a tool, where the pydantic message came through in full. This is an SDK
inconsistency, not a spec requirement, and it is worth knowing because the symptom —
"Internal server error" with no detail — sends you looking for a crash that is not there.

**The escape hatch is `MCPError`,** which `get_prompt` re-raises untouched, so you choose
the code, the message and the data:

```python
raise MCPError(
    code=INVALID_PARAMS,
    message=f"{mood!r} is not a mood this prompt understands. Choose one of: {', '.join(MOODS)}.",
    data={"argument": "mood", "allowed": sorted(MOODS)},
)
```

```json
{"error": {"code": -32602,
           "message": "'grumpy' is not a mood this prompt understands. Choose one of: sleepy, sweet-tooth, sad, celebratory, focused, cold.",
           "data": {"argument": "mood", "allowed": ["celebratory", "cold", "focused", "sad", "sleepy", "sweet-tooth"]}}}
```

Note `data.argument`. A host rendering a slash-command form can highlight the *specific*
field that was wrong, which a bare message cannot support.

So the failure table across all three primitives now reads:

```text
  TOOLS                        RESOURCES                      PROMPTS
  ─────                        ─────────                      ───────
  bare       -> withheld       bare      -> withheld          bare       -> -32603 opaque
  ToolError  -> isError:true   ResourceError         -> -32603 with msg   pydantic -> -32603 opaque (!)
                               ResourceNotFoundError -> -32602 with msg   MCPError -> your code + msg
```

Prompts are the odd one out. Validate arguments yourself and raise `MCPError`.

### `prompts/get` is not cacheable

```python
cache_hints={
    ...,
    "prompts/list": CacheHint(ttl_ms=600_000, scope="public"),
}
```

`prompts/list` is on the cacheable list; `prompts/get` is not. Confirm it yourself:

```bash
python -c "from mcp_types.methods import CACHEABLE_METHODS as C; print(sorted(C))"
```

```text
['prompts/list', 'resources/list', 'resources/read',
 'resources/templates/list', 'server/discover', 'tools/list']
```

The reasoning is the same as for `tools/call`: `prompts/get` renders against arguments and
may do work, so there is nothing stable to cache. You can see the consequence on the wire —
a `prompts/list` result carries `ttlMs` and `cacheScope`, and a `prompts/get` result
carries neither.

## `completion/complete`

### The gap it fills

Topic 04 ended on an unanswered question. `resources/templates/list` told the client this:

```json
{"uriTemplate": "cafe://drinks/{slug}", "mimeType": "application/json"}
```

The **shape** of the address, and nothing about the **address space**. Nothing there says
`{slug}` can be `latte` but not `Flat White`.

`completion/complete` is the answer. It is argument autocomplete, and it works for two
different kinds of target from one handler.

### One handler, two reference types

```python
@mcp.completion()
async def complete(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
```

**`ref` — what is being completed.** Discriminated on `type` on the wire:

```json
{"type": "ref/prompt",   "name": "order_for_me"}
{"type": "ref/resource", "uri":  "cafe://drinks/{slug}"}
```

Note the resource ref carries the **template**, placeholder and all — not a resolved URI.
You are asking what can go in the hole, so the hole has to still be there.

**`argument` — which one, and what has been typed.** `argument.name` and
`argument.value`. The value is a *partial* — the user has typed `"c"` and wants the rest.

**`context` — what has already been filled in.** `None`, or a `CompletionContext` with an
`arguments` dict. This is what makes completion interesting, and it gets its own section.

**Returning `None`** means "I have no suggestions here". The SDK turns it into an empty
completion. That is the correct answer for arguments you do not recognise — a wrong
suggestion is worse than no suggestion, because a client will show it to a human or feed
it to a model as though it were authoritative.

### Completing a template placeholder

```python
if isinstance(ref, ResourceTemplateReference):
    if ref.uri == "cafe://drinks/{slug}" and argument.name == "slug":
        return _prefix(all_slugs, typed)
    return None
```

```text
typed "c"  ->  ["cortado", "cappuccino", "cold-brew", "creme-brulee-latte", "chai"]
```

Neither RPC is sufficient alone: `resources/templates/list` gives the shape,
`completion/complete` gives the values. Together they let a client offer a URI picker for a
resource space of any size without the server ever enumerating it.

### Context-aware completion — the part worth building

`compare_drinks(first, second)` compares two drinks. Comparing a cortado with a cortado is
nonsense, so completing `second` should not offer whatever `first` already is.

```python
if argument.name == "second":
    already = (context.arguments or {}).get("first") if context else None
    candidates = [slug for slug in all_slugs if slug != already]
    return _prefix(candidates, typed)
```

Same request, twice:

```text
complete second, typed "c", no context
  -> 5 values: cortado, cappuccino, cold-brew, creme-brulee-latte, chai

complete second, typed "c", context {"first": "cortado"}
  -> 4 values: cappuccino, cold-brew, creme-brulee-latte, chai
```

`cortado` is gone, and `total` dropped with it.

This is the difference between completion as a **static enum** and completion as a
**function of state**. A client filling a form top to bottom gets suggestions that are
already consistent with its earlier answers — so an entire class of invalid input never
gets typed. You are moving validation earlier: instead of rejecting
`compare_drinks(cortado, cortado)` at `prompts/get` time with an `MCPError`, you make it
un-selectable.

Both are still worth having. Completion is a *convenience*, never a *guarantee* — nothing
stops a client skipping it and sending anything it likes. So the validation in
`compare_drinks` stays. Completion improves the common path; validation defends the
boundary.

### `total` and `has_more`

```python
def _prefix(candidates: list[str], typed: str) -> Completion:
    matches = [c for c in candidates if c.startswith(typed)]
    return Completion(values=matches, total=len(matches), has_more=False)
```

Fill these in honestly. A client that believes it received the full list will **stop
asking** — so a `has_more=False` on a truncated list means the user can never reach the
values you left out. If you cap results, say so.

They are also just useful: a host showing "7 of 12" to a human is better than one showing
nothing, and it costs one field.

### Keep the vocabulary in one place

```python
MOODS: dict[str, str] = {
    "sleepy": "needs caffeine, the more the better",
    "sweet-tooth": "wants something dessert-like",
    ...
}
```

`order_for_me` validates against `MOODS`, its argument description lists `MOODS`, and the
completion handler suggests `MOODS`. Three consumers, one definition. Hardcode that list in
three places and one copy will be wrong within a month — and the copy that goes stale will
be the argument description, which is the one you never look at.

## Layer 3 — Dry-run: a slash command, end to end

A user types `/order_for_me` in a host that supports prompts. Follow every RPC.

**Step 1 — the host needs the form.** It has `prompts/list` cached (ten minutes, public)
and finds:

```json
{"name": "order_for_me",
 "arguments": [{"name": "mood", "required": true, "description": "How the customer feels right now. One of: sleepy, ..."},
               {"name": "dairy_free", "required": false, "description": "Set true to restrict ..."}]}
```

It renders two fields. `mood` is marked required; both show their descriptions as hints.

**Step 2 — the user types `s` in the mood field.** The host fires:

```json
{"method": "completion/complete",
 "params": {"ref": {"type": "ref/prompt", "name": "order_for_me"},
            "argument": {"name": "mood", "value": "s"}}}
```

Our handler: `ref` is a `PromptReference`, `ref.name == "order_for_me"`,
`argument.name == "mood"` → filter `sorted(MOODS)` by prefix `"s"`.

```json
{"completion": {"values": ["sad", "sleepy", "sweet-tooth"], "total": 3, "hasMore": false}}
```

The host shows three options. The user picks `sleepy`.

**Step 3 — the user leaves `dairy_free` alone and submits.** The host sends:

```json
{"method": "prompts/get",
 "params": {"name": "order_for_me",
            "arguments": {"mood": "sleepy"},
            "_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                      "io.modelcontextprotocol/clientCapabilities": {}}}}
```

with `Mcp-Method: prompts/get` and `Mcp-Name: order_for_me`.

**Step 4 — pydantic binds the arguments.** `mood="sleepy"`. `dairy_free` is absent, so its
default `False` applies.

**Step 5 — validation.** `"sleepy" in MOODS` → yes. (Had the user typed `grumpy` past the
autocomplete, this is where `MCPError(INVALID_PARAMS, ...)` fires, and the host highlights
the `mood` field using `data.argument`.)

**Step 6 — build the messages.** `dairy_free` is `False`, so `menu_uri` is `cafe://menu`
and `constraint` is the empty string. Two messages: the embedded menu resource, then the
instruction with `MOODS["sleepy"]` interpolated.

**Step 7 — the reply.**

```json
{"result": {"resultType": "complete",
            "description": "Recommend a drink based on how the customer is feeling. ...",
            "messages": [
              {"role": "user", "content": {"type": "resource",
                 "resource": {"uri": "cafe://menu", "mimeType": "text/markdown", "text": "# The Café Menu\n\n..."}}},
              {"role": "user", "content": {"type": "text",
                 "text": "The customer is sleepy — needs caffeine, the more the better.\n\nRecommend exactly one drink from the menu above, and a size. ..."}}
            ]}}
```

No `ttlMs`, no `cacheScope` — `prompts/get` is not cacheable.

**Step 8 — the host injects both messages and calls the model.** The model reads the menu,
sees Cold Brew at 200mg, and recommends a large cold brew with one sentence about being
sleepy. It does not list alternatives, because you told it not to.

Count the round trips: one cached `prompts/list`, one `completion/complete`, one
`prompts/get`. Three RPCs, none of them stateful, any of them answerable by any instance.

## Gotchas

**Prompt arguments are strings on the wire.** `"true"`, not `true`. Let your type hint
coerce; do not parse by hand.

**An ordinary exception from a prompt becomes an opaque `-32603`.** So does a pydantic
validation failure. Validate yourself and raise `MCPError`.

**There is no `PromptError`.** `MCPError(code=INVALID_PARAMS, ...)` is the mechanism.

**`prompts/get` is not cacheable.** Only `prompts/list`.

**A resource completion ref carries the template, not a resolved URI.** Keep the
`{placeholder}`.

**Return `None` for arguments you do not recognise.** Never guess.

**`has_more=False` on a truncated list hides values permanently.** A client will stop
asking.

**Argument descriptions are not optional in practice.** A host renders your slash command
from them, for a human.

**Completion is a convenience, not a constraint.** Keep validating in the prompt itself.

**Embedded resources beat pasted text** when the text has a URI.

## Your turn

`solutions/t05_prompts.py`, seven TODOs.

Two of them are the real work. **TODO 3** asks you to write the instruction message — and
that is a writing exercise. Before you write it, decide: how many drinks should the model
name? Should it give a size? How much reasoning? Alternatives or not? If you do not decide,
the model will, differently each time, and the user cannot see why.

**TODO 4** asks you to do the wrong thing first. Raise a `ValueError`, run
`bash curl/05_get_order_for_me.sh grumpy`, look at the `-32603 "Internal server error"`,
*then* go and find the exception type that gets through. Meeting that opaque error once
deliberately is worth more than being told about it.

**TODO 7** is the payoff — make `second` exclude `first`, then run
`bash curl/05_complete_with_context.sh` and watch five values become four.

## Connection forward

Part 2 is done, and so is the protocol surface. Nine of the ten methods have been
exercised; only `subscriptions/listen` is left, and it waits for topic 11 because it is the
one place where everything else in this folder stops being true.

Everything so far has been **read-only**. The café can describe itself in three different
registers, and it cannot remember a single thing. No order exists. Nothing accumulates.

Part 3 is where that changes, and where the 2026-07-28 revision stops being trivia and
becomes the point. The question it answers is the one topic 00 raised and left hanging:

> If sessions are gone, and a server needs to remember a shopping cart across four calls,
> where does the cart live?

Topic 06 answers it in the gentlest possible form — a pagination cursor, which is state
that only has to survive one step. Topic 07 puts the actual cart in the same shape. Topic
08 does it a third time, for a half-finished request, and that one is called MRTR and is
the most interesting idea in the revision.

Does this make sense? Want me to go deeper on any part — how much steering a prompt's
wording really does, why prompts lack an error type, or context-aware completion as
early validation?
