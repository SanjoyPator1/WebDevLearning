# `tools/call` — And the Three Ways It Fails

## Table of contents

- [One sentence](#one-sentence)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [Kind 1: the schema rejects it](#kind-1-the-schema-rejects-it)
  - [Kind 2: `ToolError` — the failure you expected](#kind-2-toolerror-the-failure-you-expected)
  - [Kind 3: everything else — withheld, and logged](#kind-3-everything-else-withheld-and-logged)
  - [`content` and `structuredContent`](#content-and-structuredcontent)
  - [`isError: true` is *not* a JSON-RPC error](#iserror-true-is-not-a-json-rpc-error)
- [Layer 3 — Dry-run: `quote("espresso", "L", 1)`, step by step](#layer-3-dry-run-quoteespresso-l-1-step-by-step)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

A tool call is a validated function invocation whose result carries both a text form for
the model and a typed form for code, and whose *failure* modes are three genuinely
different things that a naive server collapses into one.

## The problem this topic solves

Topic 02 ended with a deliberate wrong answer. `get_drink("no-such-drink")` raised a
`ValueError` with a perfectly clear message, and what the model received was:

```json
{"content": [{"type": "text", "text": "Error executing tool get_drink"}], "isError": true}
```

The message vanished. A model reading that knows only that something failed. Its options
are to give up, or to retry the identical call. Both are bad; the second is worse, because
it burns a turn and produces the same nothing.

Meanwhile the *same server* handed back a schema error in full detail:

```text
1 validation error for get_drinkArguments
slug
  Input should be a valid string [type=string_type, input_value=123, input_type=int]
```

That asymmetry is not a bug. Understanding why it exists is the whole chapter.

## Layer 1 — The intuition

You are the temp on the counter again, and you have a phone with the manager on it. Three
things can go wrong with an order, and you would handle each differently without thinking
about it.

**"I'd like four sizzuls."** You do not need the manager. There is no such thing, and you
know what to say: *"We don't have those — here's the menu, what looks good?"* The customer
can fix it immediately.

**"A large espresso."** A real drink, a real size, but we do not sell that combination.
Again no manager needed, and again you know the useful reply: *"Espresso only comes in
small or medium — which would you like?"* Notice you did not just say no. You said no
**and gave the options**, so the customer fixes it in one step rather than guessing again.

**The till catches fire.** Now you say *"Sorry, something's wrong, give me a moment"* and
you call the manager. What you do **not** do is read the customer the till's internal
error log. It would not help them, and it might contain things that are none of their
business.

Those are the three kinds, and MCP handles them in three different places:

```text
   "four sizzuls"        ->  the SCHEMA rejects it     (you write no code)
   "large espresso"      ->  ToolError                 (your message goes through)
   till on fire          ->  any other exception       (message WITHHELD, logged)
```

## Layer 2 — The mechanics

### Kind 1: the schema rejects it

Constraints that are **fixed and knowable at import time** belong in the type hints,
because the SDK turns them into JSON Schema and the model reads them in `tools/list`
before it ever calls.

```python
size: Annotated[
    Literal["S", "M", "L"],
    Field(description="Cup size. Not every drink is sold in every size."),
],
qty: Annotated[
    int,
    Field(ge=1, le=10, description="How many cups, from 1 to 10."),
] = 1,
```

`Literal["S", "M", "L"]` becomes `{"enum": ["S", "M", "L"]}`. `ge`/`le` become
`minimum`/`maximum`. Verified on the wire:

```bash
bash curl/03_quote_bad_enum.sh   # size: "XL"
```

```text
isError: true
"Input should be 'S', 'M' or 'L' [type=literal_error, input_value='XL', input_type=str]"
```

```bash
bash curl/03_quote_bad_qty.sh    # qty: 50
```

```text
isError: true
"Input should be less than or equal to 10 [type=less_than_equal, input_value=50, input_type=int]"
```

Your function was never entered. You wrote zero validation code.

Two reasons this is better than checking in Python, and they are worth stating separately:

**It is cheaper.** A schema violation should be rare, because the model can see the
constraint up front. When a constraint lives only in your code, the model has no way to
know it and must discover it by failing — one wasted round trip every time.

**The message is trustworthy.** More on that in a moment.

### Kind 2: `ToolError` — the failure you expected

Some rules cannot go in the schema, because they depend on **data**. "Is espresso sold in
size L?" is a menu question, and the menu changes without a redeploy. So it is a runtime
check:

```python
unit_price = menu.price_of(slug, size)
if unit_price is None:
    available = ", ".join(menu.sizes_for(slug))
    raise ToolError(
        f"{drink.name} is not sold in size {size!r}. It comes in: {available}. "
        f"Ask the customer to pick one of those, or suggest a similar drink that "
        f"does come in {size!r}."
    )
```

`ToolError` means: *this failed in a way I anticipated, and the message is safe and useful
for a model to read.* The SDK forwards it. Verified:

```bash
bash curl/03_quote_bad_size.sh
```

```text
isError: true
"Error executing tool quote: Espresso is not sold in size 'L'. It comes in: S, M.
 Ask the customer to pick one of those, or suggest a similar drink that does come in 'L'."
```

Note the SDK prefixes your text with `Error executing tool quote: `. You do not need to
repeat the tool name in your own message.

#### The message is the whole job

Raising `ToolError` is one line. Writing a message worth forwarding is the actual skill,
and it has three tests:

| Test | Failing example | Passing example |
|------|-----------------|-----------------|
| Does it name what went wrong? | `"invalid input"` | `"Espresso is not sold in size 'L'"` |
| Does it quote the offending value? | `"bad size"` | `"size 'L'"` |
| Does it say what to do next? | `"size unavailable"` | `"It comes in: S, M. Ask the customer to pick one of those"` |

The third test is the one people skip, and it is the one that changes behaviour. A model
that reads *"there is no drink with slug 'no-such-drink'. Call `list_drinks` to see the
twelve slugs that exist"* does exactly that on its next turn. A model that reads *"invalid
slug"* guesses again.

Write these messages as if you were leaving a note for a capable colleague who cannot ask
you a follow-up question. That is literally the situation.

### Kind 3: everything else — withheld, and logged

`solved/t03_calls_and_errors.py` contains a tool that exists only to fail:

```python
def broken_on_purpose(slug: str) -> str:
    raise KeyError(f"{slug} not in /var/lib/cafe/internal-menu-cache.sqlite")
```

Run it and read both sides.

**What the model gets:**

```text
isError: true
"Error executing tool broken_on_purpose"
```

**What the server terminal gets:**

```text
ERROR  Tool 'broken_on_purpose' raised an unexpected exception
       ╭─ Traceback (most recent call last) ─╮
       │ .../solved/t03_calls_and_errors.py:260 in broken_on_purpose │
       ...
```

The information was **not lost**. It was deliberately not *sent*.

This is the right default and it is worth being able to defend. Your exception messages
are written for you, not for a model. In real code they contain connection strings, file
paths, row ids, internal hostnames, occasionally a token. Anything handed to a model may
end up in a transcript, in a log aggregator, in a summary shown to a user, or quoted back
in the model's own reply. The SDK cannot tell which of your exception messages are safe,
so it assumes none are.

Which reframes `ToolError`. It is not "the MCP way to raise an error". It is **the
mechanism by which you assert that a particular message is safe to disclose.** That is why
you should never write a blanket wrapper like this:

```python
# DO NOT DO THIS
try:
    ...
except Exception as exc:
    raise ToolError(str(exc)) from exc
```

That undoes the whole protection, one line, everywhere. If a message is safe, say so at
the specific place where you know it is safe.

And now the asymmetry from the start of the chapter resolves cleanly: the SDK reveals
**its own validator's** wording because it wrote that wording and knows it contains only
the schema and the offending value. It withholds **your** exception because it did not
write it.

### `content` and `structuredContent`

A successful result carries the same answer twice:

```json
{
  "resultType": "complete",
  "isError": false,
  "content": [{"type": "text", "text": "{\n  \"slug\": \"latte\",\n  \"name\": \"Latte\",\n  \"size\": \"L\",\n  \"qty\": 2,\n  \"unit_price\": 4.3,\n  \"total\": 8.6,\n  \"caffeine_mg_total\": 260\n}"}],
  "structuredContent": {"slug": "latte", "name": "Latte", "size": "L", "qty": 2,
                        "unit_price": 4.3, "total": 8.6, "caffeine_mg_total": 260}
}
```

`content` is a list of blocks destined for the model's context — text here, but it can be
images or embedded resources. `structuredContent` is the same information as JSON, for
code: a client can validate it against the tool's `outputSchema` and hand your application
a typed object rather than a string it has to parse.

Both came from one `return QuoteResult(...)`. This is the concrete payoff of topic 02's
"return a pydantic model": a tool returning `dict` gives the model a text blob and gives
your code no contract.

At 2026-07-28 `structuredContent` may be **any** JSON value, not just an object — the
schema keywords were loosened this revision, and `inputSchema`/`outputSchema` may now use
any JSON Schema 2020-12 keyword.

### `isError: true` is *not* a JSON-RPC error

This is the single most-misread thing in MCP, so it gets its own section.

All three failure kinds above produced **HTTP 200**, with a JSON-RPC **`result`**:

```json
{"jsonrpc": "2.0", "id": 31, "result": {"isError": true, "content": [...], "resultType": "complete"}}
```

Not this:

```json
{"jsonrpc": "2.0", "id": 31, "error": {"code": -32603, "message": "..."}}
```

The distinction is about **who the failure is addressed to**.

```text
  result.isError: true   ->  the TOOL failed.  Addressed to the MODEL.
                             "your call didn't work; here's why; try something else"
                             The protocol worked perfectly.

  error: {code, message} ->  the PROTOCOL failed. Addressed to the CLIENT.
                             "your request was malformed / unsupported / unauthorised"
                             The model is not involved and cannot fix it.
```

A tool failing is a *normal outcome* of a working protocol, the same way HTTP 404 is a
normal outcome of a working web server. It must reach the model, because only the model
can decide what to do next. If it came back as a JSON-RPC `error`, a client would likely
treat it as a transport problem and never show it to the model at all — which is exactly
the wrong outcome.

The corollary: **your client must check `isError` on every result.** An HTTP 200 with no
`error` key does not mean the tool worked.

Genuine JSON-RPC errors are the ones you met in topic 01: `-32020` header mismatch,
`-32022` unsupported version, `-32602` invalid params, `-32601` method not found.
Those are all things the *client* got wrong.

Which explains one more mcp 2.1.1 behaviour that looks like a deviation:

```bash
bash curl/03_unknown_tool.sh
```

```json
{"result": {"content": [{"type": "text", "text": "Unknown tool: not_a_tool"}], "isError": true}}
```

You might expect `-32601 Method not found` or `-32602 Invalid params`. The spec's prose
reads that way. But apply the test above — *who can fix this?* The model asked for a tool
that does not exist; the model can re-read `tools/list` and pick a real one. So the
failure is addressed to the model, and it belongs in the result. The SDK's choice is the
more useful one.

## Layer 3 — Dry-run: `quote("espresso", "L", 1)`, step by step

Follow one failing call all the way through, naming which component acts at each step.

**Step 1 — the client POSTs.** Headers include `Mcp-Method: tools/call` and
`Mcp-Name: quote`.

```json
{"jsonrpc": "2.0", "id": 31, "method": "tools/call",
 "params": {"name": "quote", "arguments": {"slug": "espresso", "size": "L", "qty": 1},
            "_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                      "io.modelcontextprotocol/clientCapabilities": {}}}}
```

**Step 2 — the transport layer checks the headers.** Does `Mcp-Method` match
`body.method`? Yes. Does `Mcp-Name` match `params.name`? Yes. If either failed we would
stop here with `-32020` and never look at the body. *No tool code has run.*

**Step 3 — the SDK looks up `quote`.** Found. If not, we would stop with a result carrying
`isError: true` and `"Unknown tool: quote"`.

**Step 4 — the SDK validates `arguments` against `inputSchema`.**

```text
slug: "espresso"  -> type string        OK
size: "L"         -> enum [S, M, L]     OK   <-- "L" IS legal. This is the crux.
qty:  1           -> integer, 1..10     OK
```

All three pass. *Still no tool code has run.* This is where `"XL"` would have died.

**Step 5 — `quote()` is finally entered.**

```python
drink = menu.find("espresso")          # -> Drink(slug="espresso", prices={"S": 2.20, "M": 2.60})
                                       #    not None, so no ToolError yet
unit_price = menu.price_of("espresso", "L")
                                       # -> DRINKS[0].prices.get("L") -> None
```

**Step 6 — the runtime rule fires.** `unit_price is None`, so:

```python
available = ", ".join(menu.sizes_for("espresso"))   # sizes_for -> ("S", "M") -> "S, M"
raise ToolError("Espresso is not sold in size 'L'. It comes in: S, M. Ask the customer to "
                "pick one of those, or suggest a similar drink that does come in 'L'.")
```

Note that `available` was computed *for the error message*. That is the difference between
an error and a useful error, and it cost one line.

**Step 7 — the SDK catches `ToolError`.** It recognises the type as "expected failure,
message is disclosable", prefixes the tool name, and builds a **successful** JSON-RPC
response:

```json
{"jsonrpc": "2.0", "id": 31,
 "result": {"resultType": "complete", "isError": true,
            "content": [{"type": "text",
              "text": "Error executing tool quote: Espresso is not sold in size 'L'. It comes in: S, M. ..."}],
            "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "cafe-mcp", "version": "0.3.0"}}}}
```

**Step 8 — the model reads it and recovers.** It has the drink, the fact that L is
unavailable, the two sizes that are, and an explicit suggestion. Its next turn is a
`quote` for size M, or a suggestion of a flat white. One round trip, no guessing.

Now replay steps 5–8 with `raise KeyError("espresso has no L")` instead. Step 7 becomes
"unknown exception → log the traceback to stderr, send `Error executing tool quote`", and
step 8 becomes "the model has nothing to work with". Same bug, same detection, completely
different outcome — decided entirely by which exception type you chose.

## Gotchas

**`isError: true` arrives inside `result`, not `error`.** Your client must check it
explicitly. HTTP 200 and no `error` key does not mean success.

**A bare exception's message is withheld.** Not logged-and-forwarded — withheld from the
model, logged on the server. If you are debugging "why does the model keep retrying", look
at your server's stderr.

**Never write `except Exception as e: raise ToolError(str(e))`.** It defeats the disclosure
boundary everywhere at once. Assert safety per-site, where you actually know.

**Constraints that could live in the schema should.** Every rule you keep in Python is a
rule the model must discover by failing.

**`Literal` gives you an enum; `Field(ge=, le=)` gives you a range.** Use them. They are
free and self-documenting.

**Unknown tool name is not `-32601`.** In mcp 2.1.1 it is a result with `isError: true`.

**The SDK prefixes your `ToolError` text** with `Error executing tool <name>: `. Do not
repeat the tool name yourself.

**Rounding.** `round(4.30 * 2, 2)` is fine; `0.1 + 0.2` is not. The café rounds money at
the point of computing a total. For anything real, use `Decimal` — floats are here because
the subject is MCP, not currency.

## Your turn

`solutions/t03_calls_and_errors.py`, five TODOs.

TODO 4 (`quote`) is the real exercise, and the decision inside it is the lesson: for each
of the three rules — `size` in S/M/L, `qty` in 1..10, and *this* drink sold in *that* size
— decide whether it belongs in the schema or in the code, and be able to say why.

TODO 5 asks you to write a deliberately broken tool. Do write it. Seeing
`Error executing tool broken_on_purpose` come back from *your own* code, while the
traceback sits in *your own* terminal, is worth more than reading about it.

## Connection forward

Part 1 is done: you can frame requests, publish tools, and fail well. The café can list
drinks, describe them, and price them — but it cannot yet remember anything, and it has
nothing for the *client* to read as data rather than call as an action.

Part 2 fixes the second half of that. Topic 04 is **resources**: data addressed by URI
that the host attaches to context rather than the model invoking — `cafe://menu` as a
markdown card, and `cafe://drinks/{slug}` as a template. It is also where `ttlMs` and
`cacheScope` start doing real work, because a resource is exactly the kind of thing worth
caching.

Then Part 3 is where statelessness gets interesting, and the café learns to remember an
order without remembering anything.

Does this make sense? Want me to go deeper on any part — the disclosure boundary and why
`ToolError` is really a security mechanism, the `isError` versus JSON-RPC-error split, or
how to decide what goes in a schema?
