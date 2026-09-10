# MRTR: The Pattern That Replaced Server-Initiated Requests

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [The shape of the two calls](#the-shape-of-the-two-calls)
  - [The code](#the-code)
  - [`ctx.input_responses` is a plain dict, not the wrapped type its annotation suggests](#ctxinput_responses-is-a-plain-dict-not-the-wrapped-type-its-annotation-suggests)
  - [`ElicitResult.action` has three values, and only one of them proceeds](#elicitresultaction-has-three-values-and-only-one-of-them-proceeds)
- [The central lesson: request-state binding is automatic, and it is not what you think it protects](#the-central-lesson-request-state-binding-is-automatic-and-it-is-not-what-you-think-it-protects)
  - [The naive assumption](#the-naive-assumption)
  - [What actually happens, verified](#what-actually-happens-verified)
  - [Proving it: the attack that never reaches your code](#proving-it-the-attack-that-never-reaches-your-code)
  - [The message is deliberately uninformative](#the-message-is-deliberately-uninformative)
- [What `requestState` is actually for, then](#what-requeststate-is-actually-for-then)
- [`RequestedSchema`: a spec rule the SDK does not enforce](#requestedschema-a-spec-rule-the-sdk-does-not-enforce)
- [Declaring `InputRequiredResult` in the return type: helpful, not required](#declaring-inputrequiredresult-in-the-return-type-helpful-not-required)
- [A quiet detail: the output schema wraps a Union under `"result"`](#a-quiet-detail-the-output-schema-wraps-a-union-under-result)
- [Layer 3 — Dry-run: the full round trip, one process handing off to another](#layer-3-dry-run-the-full-round-trip-one-process-handing-off-to-another)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Optional capstone: a real LLM driving this](#optional-capstone-a-real-llm-driving-this)
- [Connection forward](#connection-forward)


## One sentence

A server that needs an answer before it can finish does not ask the client a question —
it *answers* the call it received with a question, and the client, if it wants to proceed,
reissues the exact same call a second time carrying the answer.

## Where this sits

Topic 00 ended with a line from the SDK's own source, quoted verbatim because it is the
single most important fact in this whole folder:

```python
# 2026-07-28: none (no server-to-client requests at this version)
```

Every prior revision let a server send the client three kinds of request:
`roots/list`, `sampling/createMessage`, and — the one that matters here —
`elicitation/create`, meaning *please ask your user this for me*. All three are gone. A
server cannot send the client anything and wait for a reply.

`place_order` needs exactly that: a customer's confirmation before it commits real money
to a cart. This chapter is where that need meets that constraint, and the resolution —
**Multi Round-Trip Requests**, MRTR — is the single most interesting idea in the 2026-07-28
revision.

## The problem this topic solves

Topics 06 and 07 already answered "where does state live once sessions are gone?" twice —
a page position, then a shopping cart. Both times the answer was: mint a token, hand it
back, let the client carry it.

MRTR asks the same question about something new: not *data*, but a *conversation in
progress*. Round 1 of `place_order` is not finished — it is *waiting* for a customer's
answer. Where does "I am in the middle of asking something" live, with no session to hold
it?

Same answer as always. It lives in a token.

## Layer 1 — The intuition

Go back to the counter one final time, because the analogy that explains this is the same
one from topic 00, completed.

Under the old model, the temp could pick up the phone and ask the kitchen a question,
and stand there holding the line until the kitchen answered. That is a *server-initiated
request* — the temp (the server) reaches out to someone else (the client) and blocks.

There is no phone anymore. So instead, when the temp needs an answer, they write the
question on the back of the customer's own receipt and hand it back: *"Please confirm:
2× Latte, $8.60. What name goes on the cup? — bring this back to me."* The customer walks
away, thinks about it, comes back, and hands the *same receipt* back with the answer
filled in. The temp reads the answer off the receipt they themselves wrote.

Notice what makes this work with no phone call at all: the temp never held the line open.
Between handing over the receipt and getting it back, the temp could go on break, another
temp could take over the counter, the whole shop could close and reopen — none of it
matters, because the entire "I asked X and I'm waiting for an answer" state is written on
a piece of paper the customer is carrying, not held in anyone's head.

That piece of paper is `requestState`.

## Layer 2 — The mechanics

### The shape of the two calls

**Round 1** — the client calls `place_order` normally:

```json
{"method": "tools/call",
 "params": {"name": "place_order", "arguments": {"order": "v1.eyJl...fOs"}}}
```

**The reply is not an answer — it is a question:**

```json
{"result": {
  "resultType": "input_required",
  "inputRequests": {
    "confirm": {
      "method": "elicitation/create",
      "params": {
        "message": "Confirm 2x Latte (L) — $8.60. What name should go on the cup?",
        "mode": "form",
        "requestedSchema": {
          "type": "object",
          "properties": {
            "name": {"type": "string", "title": "Name for the cup"},
            "confirm": {"type": "boolean", "title": "Place this order?"}
          },
          "required": ["name", "confirm"]
        }
      }
    }
  },
  "requestState": "v1.Gk9oAj6nzSrikg4Blrjgt8e_MlW4gsDr..."
}}
```

**Round 2** — the client (via its host, via a human) fills in the form and reissues the
*same call*, now carrying the answer and the state token:

```json
{"method": "tools/call",
 "params": {
   "name": "place_order",
   "arguments": {"order": "v1.eyJl...fOs"},
   "inputResponses": {"confirm": {"action": "accept", "content": {"name": "Sanjoy", "confirm": true}}},
   "requestState": "v1.Gk9oAj6nzSrikg4Blrjgt8e_MlW4gsDr..."
 }}
```

**The reply is now a real answer:**

```json
{"result": {"resultType": "complete", "isError": false,
            "structuredContent": {"result": {"ticket": "A-915", "name": "Sanjoy",
              "lines": [{"slug": "latte", "name": "Latte", "size": "L", "qty": 2,
                         "unit_price": 4.3, "line_total": 8.6}],
              "total": 8.6, "served_by": "single"}}}}
```

Two ordinary `tools/call` requests. No new methods, no new transport behaviour. The whole
mechanism lives inside the `result` shape and two new top-level `params` fields.

### The code

```python
async def place_order(order: str, ctx: Context) -> OrderPlaced | OrderNotPlaced | InputRequiredResult:
    cart_lines = orders.load_cart(order)          # runs on BOTH rounds
    priced_lines = orders.reprice(cart_lines)      # runs on BOTH rounds
    total = orders.total_of(priced_lines)          # runs on BOTH rounds

    if ctx.input_responses is None:
        # ROUND 1
        return InputRequiredResult(
            result_type="input_required",
            input_requests={"confirm": ElicitRequest(...)},
            request_state=f'{{"quoted_total": {total}}}',
        )

    # ROUND 2
    quoted_total = json.loads(ctx.request_state)["quoted_total"]
    ...
    confirmation = ctx.input_responses["confirm"]
    confirmation = getattr(confirmation, "root", confirmation)
    if confirmation.action != "accept":
        return OrderNotPlaced(reason=f"customer {confirmation.action}d")
    ...
    return OrderPlaced(...)
```

`ctx.input_responses` is the single switch on which the entire function branches. `None`
means *this is the first call*; populated means *this is the answer to a question I asked
last time*. Everything above that `if` runs identically on both rounds — loading and
pricing the cart is not part of "the question", it is just work the function needs done
either way, and doing it twice (once per round) is both harmless and unavoidable, since a
fresh server instance may handle round 2 with no memory of having handled round 1.

### `ctx.input_responses` is a plain dict, not the wrapped type its annotation suggests

Its declared type is `InputResponses | None`, and `InputResponses` is a pydantic
`RootModel` in `mcp_types`. You might reasonably write `ctx.input_responses.root["confirm"].root`
to unwrap it. Do not — verified on the wire:

```python
type(ctx.input_responses)              # <class 'dict'>
hasattr(ctx.input_responses, "root")   # False
ctx.input_responses["confirm"]         # ElicitResult(action='accept', content={...})
```

One hop: `ctx.input_responses["confirm"]`. The `getattr(x, "root", x)` in the code above
is defensive — it costs nothing and protects against a future SDK version that *does*
return the wrapped type — but as of mcp 2.1.1, the plain dict access already works.

### `ElicitResult.action` has three values, and only one of them proceeds

```python
class ElicitResult:
    action: Literal["accept", "decline", "cancel"]
    content: dict | None
```

`accept` — the customer answered and agreed. `content` carries the form data.

`decline` — the customer answered *no*. This is not an error. Verified:

```json
{"resultType": "complete", "isError": false,
 "structuredContent": {"result": {"placed": false, "reason": "customer declined"}}}
```

`cancel` — the customer dismissed the question without answering either way. Also not an
error, and worth handling *separately* from `decline` in your own reasoning even though
both take the same code path here — "no" and "never mind" are different customer
intentions a real system might want to log differently.

The one bug this file actually shipped with, caught by its own test: the first draft
built the reason string as `f"customer {confirmation.action}d"` — string concatenation
that turns `"decline"` into `"declined"` correctly and `"cancel"` into `"canceld"`
*incorrectly*. It reads as plausible and is wrong. The fix is a small lookup table:

```python
past_tense = {"decline": "declined", "cancel": "cancelled"}
reason = past_tense.get(confirmation.action, confirmation.action)
```

This is worth keeping in mind as a class of bug: `action != "accept"` is easy to get
right; the *English* describing which non-accept action happened is easy to get subtly
wrong, and a test that only checks `action != "accept"` half-heartedly would never have
caught it. `tests/test_wire_mrtr.py` checks the exact string for both `decline` and
`cancel` separately for this reason.

## The central lesson: request-state binding is automatic, and it is not what you think it protects

This is the part of the chapter that overturns something you might reasonably assume from
reading the type signature of `request_state`. It is worth walking through carefully,
because the naive assumption is genuinely wrong and the real mechanism is more interesting.

### The naive assumption

`request_state` is a string your tool controls entirely. A plausible first design is: "I
should embed a digest of the order token into `request_state` myself, so that on round 2 I
can check the retry's `order` argument still matches what round 1 was confirming." That is
exactly the kind of thing topic 07 trained you to think about — HMAC everything that
matters, check it yourself.

**Do not build this. The SDK already does it, and does it more thoroughly than a
hand-rolled check would.**

### What actually happens, verified

`MCPServer` installs a middleware — `RequestStateBoundary` — in front of every method that
can return `input_required` (`tools/call`, `prompts/get`, `resources/read`). Every time
your tool returns an `InputRequiredResult`, before the result reaches the wire, this
middleware:

1. Computes the **tool name** and a **SHA-256 digest of the entire `arguments` object**
   for the *current* request.
2. Seals your plaintext `request_state` together with that name, that digest, the method,
   an expiry, and (if authenticated) a principal — into an encrypted, signed envelope.
3. That envelope — not your plaintext — is what actually goes out on the wire as
   `requestState`.

On the retry, before your tool is even entered, the same middleware:

1. Unseals the envelope.
2. Recomputes the tool name and arguments digest **from this new request**.
3. Compares them to what was sealed in step 1. **Any mismatch — a different tool name, a
   different `arguments` object, an expired envelope, a different principal — is rejected
   outright**, with a JSON-RPC error, before your function runs at all.
4. Only if everything matches does `ctx.request_state` receive your original plaintext,
   and `ctx.input_responses` receive the parsed answer.

Here is the source, read once rather than trusted secondhand:

```python
target, args_digest = _request_identity(ctx.method, ctx.params)
if claims.get("m") != ctx.method or claims.get("t") != target or claims.get("a") != args_digest:
    _reject(ctx.method, "request binding")
```

And `_request_identity`:

```python
def _request_identity(method, params):
    if method == "resources/read":
        target = str(p.get("uri", ""))
    else:
        target, args = str(p.get("name", "")), p.get("arguments") or {}
    return target, sha256(compact_json(args, sort_keys=True))[:16]
```

**This is not a feature you opt into. It is on by default, for every `MCPServer`, for
every tool that can return `input_required`.**

### Proving it: the attack that never reaches your code

Two carts, both real, both legitimately signed by topic 07's mechanism:

```text
round1_order  = a token for 2x Latte, $8.60
different_order = a token for 5x Mocha, a much bigger total
```

Start a confirmation for the first cart, then retry with the **second cart's token** and
the **first cart's `requestState`**:

```bash
bash curl/08_swap_order.sh <requestState from a round-1 call>
```

```json
{"error": {"code": -32602, "message": "Invalid or expired requestState",
           "data": {"reason": "invalid_request_state"}}}
```

Read what did *not* happen: `place_order` never ran. There is no `[server] place_order`
line in the server's stderr for this call at all — the rejection happens in middleware,
before dispatch. The customer's "yes, place the $8.60 order" can never be silently
redirected onto a $30+ order, and you did not write a single line of code to make that
true.

Contrast this with a *tampered* token from topic 07 — a real order token with one
character flipped. That still gets refused the *same way* here, for the *same reason*:
from the binding's point of view, a tampered `order` argument is simply a *different*
`arguments` object, and any different `arguments` object fails the digest check.
Domain-separation and request-binding are two independent protections stacked on top of
each other, and either one alone would have caught this particular attack.

### The message is deliberately uninformative

`"Invalid or expired requestState"` never says *which* of the four checks failed —
wrong method, wrong tool, wrong arguments, or genuinely expired. That is the same
disclosure-boundary reasoning from topic 07's token messages, applied by the SDK itself
this time: telling an attacker *why* their forgery failed narrows their next attempt.

## What `requestState` is actually for, then

If it is not the security mechanism, what should you put in it?

**Anything true at round 1 that is not already an argument, and that round 2 needs to
compare against.** The automatic binding guarantees round 2's *arguments* are byte-for-byte
identical to round 1's. It says nothing about the *world* — menu prices, inventory,
anything that lives outside the call itself.

Here, that gap is real: `place_order`'s only argument is the order token, and the order
token cannot change between rounds (the binding forbids it). But the **price** of the
drinks inside that token is looked up fresh, from the live menu, on *every* call — and
nothing stops the café's prices from changing in the seconds between round 1 and round 2.
`request_state` is where the quote made to the customer at round 1 gets written down, so
round 2 can check it against reality:

```python
request_state=f'{{"quoted_total": {total}}}'         # round 1: write down what we quoted

quoted_total = json.loads(ctx.request_state)["quoted_total"]     # round 2: read it back
if abs(quoted_total - total) > 0.001:
    raise ToolError(f"The price changed since you were quoted ${quoted_total:.2f} "
                     f"(it is now ${total:.2f}). Call `view_order` to see the new "
                     f"total, then call `place_order` again to reconfirm.")
```

Verified end to end: mint a cart, get quoted $8.60 at round 1, bump the café's own price
for that exact drink+size before round 2 runs (the *same* order token, genuinely
unchanged), and:

```json
{"isError": true,
 "content": [{"text": "Error executing tool place_order: The price changed since you "
              "were quoted $8.60 (it is now $10.60). Call `view_order` to see the new "
              "total, then call `place_order` again to reconfirm."}]}
```

The automatic binding was satisfied — the `order` argument never changed. `request_state`
caught the thing the binding structurally cannot see, because it lives outside the request
entirely.

## `RequestedSchema`: a spec rule the SDK does not enforce

The spec restricts `requestedSchema` to **top-level primitive properties only** — no
nested objects, so a confirmation form cannot ask for a structured sub-object. mcp 2.1.1
does **not** check this. Add a `"type": "object"` property inside `requestedSchema` and it
is published to the wire unmodified, no rejection, no warning. Following the restriction
is on you, not the SDK — see `notes/appendix-sdk-vs-spec.md`.

## Declaring `InputRequiredResult` in the return type: helpful, not required

A widely-repeated claim about this pattern is that a tool's return annotation *must*
include `InputRequiredResult` for a returned `InputRequiredResult` to be honoured — that
omitting it is an error. Verified false in mcp 2.1.1: a tool annotated
`-> Done` (no `InputRequiredResult` arm at all) that returns an `InputRequiredResult` at
runtime works exactly the same as one that declares it. The check is an `isinstance` at
runtime, not a static annotation check.

Declare it anyway. It is what makes `place_order`'s published `outputSchema` accurate —
and it is the one case where the *combination* of `InputRequiredResult` and a
`Resolve(...)`-typed parameter genuinely is rejected at registration time, because both
mechanisms would fight over the same single input-required channel. `place_order` uses
neither `Resolve`, so this does not bite here, but knowing the boundary matters if you
ever reach for the resolver pattern instead of a hand-written round trip.

## A quiet detail: the output schema wraps a Union under `"result"`

`place_order` returns `OrderPlaced | OrderNotPlaced | InputRequiredResult`. Check the
published `outputSchema`:

```json
{"type": "object", "required": ["result"],
 "properties": {"result": {"anyOf": [{"$ref": "#/$defs/OrderPlaced"},
                                      {"$ref": "#/$defs/OrderNotPlaced"}]}}}
```

Note `InputRequiredResult` is **absent** from this schema entirely — it is a
protocol-level result shape, not part of the tool's own "I completed successfully" output
contract, so the SDK strips it before publishing. And note the two real arms are wrapped
under a synthetic `"result"` key rather than appearing as a bare top-level `anyOf` — a
tool's `outputSchema` must itself be a JSON Schema object, and a bare union is not one, so
the SDK gives it a home. The consequence reaches the wire: `structuredContent` on a
successful call is `{"result": {"ticket": ..., ...}}`, not the flat object you would get
from a single-model return type. `tests/test_wire_mrtr.py` pins this shape so it is not
mistaken for a bug later.

## Layer 3 — Dry-run: the full round trip, one process handing off to another

**Round 1, on process A.** The client calls `place_order(order="v1.eyJl...fOs")`.

```text
cart_lines = orders.load_cart("v1.eyJl...fOs")   -> [{"slug":"latte","size":"L","qty":2}]
priced_lines = orders.reprice(cart_lines)        -> [OrderLine(Latte, L, 2, 4.30, 8.60)]
total = 8.60
ctx.input_responses is None -> ROUND 1
return InputRequiredResult(
    input_requests={"confirm": ...ask for name + confirm...},
    request_state='{"quoted_total": 8.6}',
)
```

The middleware, wrapping this return, computes
`(target="place_order", args_digest=sha256({"order":"v1.eyJl...fOs"}))`, seals
`'{"quoted_total": 8.6}'` together with that identity and an expiry into an encrypted
envelope, and *that* envelope is what leaves the wire as `requestState`. Process A can
now terminate.

**Round 2, on a completely different process B.** The client reissues the call:

```text
tools/call place_order(order="v1.eyJl...fOs")     <- byte-identical to round 1
  + inputResponses: {"confirm": {"action":"accept","content":{"name":"Sanjoy","confirm":true}}}
  + requestState: <the sealed envelope from round 1>
```

**Before `place_order` is entered**, process B's own copy of the middleware:

```text
unseal the envelope -> plaintext '{"quoted_total": 8.6}', claims{m, t, a, exp}
recompute (target, args_digest) from THIS request's params
  target      == "place_order"                              -> matches
  args_digest == sha256({"order": "v1.eyJl...fOs"})           -> matches (unchanged argument)
exp check -> not yet expired -> pass
```

Only now does `place_order` run, with `ctx.request_state == '{"quoted_total": 8.6}'` and
`ctx.input_responses == {"confirm": ElicitResult(action="accept", content={"name": "Sanjoy", "confirm": True})}`.

```text
cart_lines, priced_lines, total recomputed identically -> 8.60 again (menu unchanged)
quoted_total = 8.6, matches total -> no price-drift error
confirmation.action == "accept" -> proceed
name = "Sanjoy"
return OrderPlaced(ticket="A-915", name="Sanjoy", lines=[...], total=8.6, served_by="single")
```

Process B never spoke to process A. It never saw round 1. Every fact it needed —
what was quoted, what was ordered, whether this retry is even legitimate — arrived
entirely inside the two strings the client carried back: the order token and the sealed
`requestState`. This is topic 07's lesson, proven a second time at a harder problem.

## Gotchas

**Do not build your own digest-of-arguments check.** The SDK's request-state binding
already covers every argument, automatically, for every `input_required`-capable method.
Duplicating it is redundant at best.

**`request_state` is for facts outside the call, not for binding the call.** Prices,
inventory, anything the world could change between rounds — that is its job.

**`ctx.input_responses` is a plain dict**, despite its `InputResponses` type annotation.
One hop of indexing, not two.

**`decline` and `cancel` are both successful outcomes.** Never branch on them as errors,
and be careful writing the English for each — `"cancel" + "d"` is not `"cancelled"`.

**`RequestedSchema`'s top-level-only restriction is not enforced by the SDK.** Follow it
in your own schema regardless; a client obeying the spec will assume you have.

**`InputRequiredResult` does not have to appear in the return annotation to work.** It
should appear anyway, for an accurate `outputSchema` — but do not treat its absence as a
bug you must chase if you inherit code that omits it.

**A `Union` return type wraps under `{"result": ...}`** in both `outputSchema` and
`structuredContent`. A single-model return type does not. Know which one you are looking
at before writing a client that reads `structuredContent` directly.

**MRTR round 2 uses a fresh JSON-RPC id.** Nothing about id continuity links the two
calls; `requestState` is the entire connective tissue.

## Your turn

`solutions/t08_mrtr.py`, six TODOs. TODO 3 and TODO 4 are the real exercise — everything
else is wiring you have done before.

Before you write `request_state`, answer the question the chapter spent most of its words
on: *what does the automatic binding already guarantee, and what is left over for you to
protect?* If your answer is "nothing is left over, the binding covers everything," go
re-read the price-drift section — there is a real gap, and it is the reason
`request_state` exists as a feature at all rather than being redundant with the binding.

TODO 5 asks you to predict `curl/08_swap_order.sh`'s output before running it. Do that
honestly — the value of this topic is in being surprised once, deliberately, by how much
protection you get without writing any of it yourself.

## Optional capstone: a real LLM driving this

`solved/agent_client.py` proves the same round trip with an actual model in the loop
instead of a hand-crafted curl request, and makes one architectural point concrete: **the
model never sees `input_required` at all.** In a real host, the client library intercepts
that interim result, gets the missing answer from a human, and retries — the model is
shown only the final `complete` result, as if the tool had answered on the first try. The
script plays the role of that host: one model call decides to invoke `place_order`, and
every following byte of the MRTR exchange is plain HTTP with no model involved.

It supports Ollama (local, free, tried first if reachable) or Gemini (via `GEMINI_API_KEY`
in a repo-root `.env`, a real network call), and a `--dry-run` mode that exercises the
identical code path with a scripted fake model response and zero network access — verified
working end to end. It is a demonstration, not a graded exercise; there is no
`solutions/` stub for it.

## Connection forward

`place_order`'s confirmation form asked for a name and a yes/no — small, safe data that is
fine for a model to see and relay. Topic 09 asks what happens when the thing needing
confirmation is not safe for a model to see at all: a card number, a password, anything
that should never enter an LLM's context in the first place. The mechanism is the same
`InputRequiredResult`, but the elicitation mode changes from `"form"` to `"url"` — the
server hands back a link, the *human* navigates it directly, and the model learns only
whether the human said yes. Same round trip, same automatic binding underneath it,
completely different trust boundary on top.

Does this make sense? Want me to go deeper on any part — exactly how the request-state
seal is constructed, why decline/cancel must never be treated as errors, or the reasoning
behind wrapping Union returns under a synthetic key?
