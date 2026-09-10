# MRTR in URL Mode: Consent Outside the Model's Context

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [The shape of round 1: a link, not a schema](#the-shape-of-round-1-a-link-not-a-schema)
  - [The link is itself a signed token — because there is nowhere else to put the memory](#the-link-is-itself-a-signed-token-because-there-is-nowhere-else-to-put-the-memory)
  - [The pay page: the one place a receipt gets minted](#the-pay-page-the-one-place-a-receipt-gets-minted)
  - [Round 2: the answer arrives as `content`, exactly like form mode](#round-2-the-answer-arrives-as-content-exactly-like-form-mode)
  - [The check a naive integration skips](#the-check-a-naive-integration-skips)
  - [Two checks, not one: signature, then content](#two-checks-not-one-signature-then-content)
  - [`request_state` is still doing its topic-08 job, unrelated to the receipt](#request_state-is-still-doing-its-topic-08-job-unrelated-to-the-receipt)
- [`elicitationId`: present, optional, and not how you correlate anything](#elicitationid-present-optional-and-not-how-you-correlate-anything)
- [A different mechanism that looks similar and is not: `UrlElicitationRequiredError`](#a-different-mechanism-that-looks-similar-and-is-not-urlelicitationrequirederror)
- [Layer 3 — Dry-run: from link to receipt to placed order](#layer-3-dry-run-from-link-to-receipt-to-placed-order)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

URL-mode elicitation sends the human a *link* instead of a *form*, so that whatever
happens on the other end of it — a card number, a password, an OAuth grant — never enters
the model's context at all; the model learns only whether the human said yes.

## Where this sits

Topic 08 built the confirmation form for `place_order`: a name and a yes/no. Perfectly
safe data — a model reading "the customer's name is Sanjoy" changes nothing about what
that model can do with it. `pay_for_order` needs a different kind of confirmation, and the
difference is not the plumbing, it is the *trust boundary*.

## The problem this topic solves

Imagine `pay_for_order` had used form mode, the way topic 08's `place_order` did:

```json
"requestedSchema": {"properties": {"card_number": {"type": "string"}, "cvv": {"type": "string"}}}
```

Walk through what that would actually mean. The host would render this form, the human
would type their card number into it, the host would package it as `content`, and that
`content` would travel back to the server as part of a `tools/call` — which means it
passes through exactly the same pipe as everything else in this conversation, including
whatever the model itself sees of the request and response. A card number typed into an
MCP form is, structurally, no different from a card number typed into the chat. Neither
belongs in a model's context, a transcript, a log line, or anywhere a summarization step
might later touch.

URL mode exists to take the sensitive part *out of the pipe entirely*.

## Layer 1 — The intuition

You are back at the counter, and this time the customer wants to pay. You do not shout
"read me your card number" across the room — that is form mode's mistake, transplanted
onto something it was never meant for. Instead you say: *"there's a card reader by the
door — go tap your card there, and come back when you're done."* The customer walks over,
taps, and the reader itself — not you, not the customer describing it to you — is the only
thing that ever touches the card number. When they come back, you do not ask them to
recite anything private. You ask the reader: *did that tap actually happen?* And the
reader hands you a receipt, which is the only thing you actually check.

That is the whole chapter. The **link** is the walk to the card reader. The **receipt** is
what makes "did that tap actually happen?" answerable without the reader and the counter
sharing a single byte of memory.

## Layer 2 — The mechanics

### The shape of round 1: a link, not a schema

Form mode's `InputRequiredResult`:

```python
ElicitRequestFormParams(message=..., mode="form", requested_schema={...})
```

URL mode's:

```python
ElicitRequestURLParams(mode="url", message=..., url=pay_url)
```

No `requestedSchema` at all. There is nothing to validate, because the server is not
asking for structured data back — it is asking the client to *navigate somewhere*.
Verified on the wire:

```json
{"inputRequests": {"pay": {"method": "elicitation/create",
   "params": {"message": "Open this link to pay $8.60 for 2x Latte (L). Do not enter any card details in this chat.",
              "mode": "url", "url": "http://127.0.0.1:3010/pay/v1.eyJl...fOs"}}},
 "requestState": "v1.vwA6hd...Y",
 "resultType": "input_required"}
```

Read the message again. *"Do not enter any card details in this chat."* That sentence is
not decoration — it is the one thing standing between a well-behaved model and one that
"helpfully" tries to collect a card number itself because the human typed one into the
conversation by mistake. Say the boundary explicitly; do not assume a model infers it.

### The link is itself a signed token — because there is nowhere else to put the memory

The URL is `http://127.0.0.1:3010/pay/{nonce}`, and `{nonce}` is not a random string you
could look up in a database. It is a token, minted by `tokens.sign()`, carrying exactly
the two facts the pay page will need:

```python
nonce = tokens.sign("pay_nonce", {"order": order, "total": total}, ttl_s=NONCE_TTL_S)
```

This is the same lesson from topics 06 through 08, applied one more time, and it is worth
naming explicitly why it has to be this way. `/pay/{nonce}` is a *separate HTTP route*,
handled by a *separate request*, quite possibly on a *separate server instance* than the
one that answered `pay_for_order`'s round 1. There is no session connecting them, no shared
memory, nothing except whatever bytes travel in the URL itself. So the URL has to be
self-describing, exactly the way the order token and the requestState token are.

### The pay page: the one place a receipt gets minted

```python
@mcp.custom_route("/pay/{nonce}", methods=["GET", "POST"])
async def pay_page(request: Request):
    nonce_body = tokens.verify("pay_nonce", request.path_params["nonce"])
    if request.method == "GET":
        return HTMLResponse(f"<h1>Pay ${nonce_body['total']:.2f}</h1>...")
    receipt = tokens.sign("payment_receipt", {"order": nonce_body["order"], "total": nonce_body["total"]}, ttl_s=RECEIPT_TTL_S)
    return JSONResponse({"paid": True, "receipt": receipt})
```

Notice this is not an MCP method at all — no `_meta`, no `Mcp-Method` header, no JSON-RPC
envelope. `custom_route` mounts an ordinary Starlette route on the same app, and this is
where it earns its keep: the human's browser hits a plain web page, exactly as if this
café had a real payment processor. `GET` renders something a person would actually read.
`POST` — standing in for "the human clicked the Pay button" — is the *only* code path in
this entire server that mints a `payment_receipt` token. That concentration matters: if you
can name the one function that mints receipts, you can audit it; scatter that logic across
several places and you cannot.

### Round 2: the answer arrives as `content`, exactly like form mode

```json
"inputResponses": {"pay": {"action": "accept", "content": {"receipt": "v1.eyJl...Ts"}}}
```

URL mode does not get its own result shape. It reuses `ElicitResult` — the same `action`
field, the same optional `content` dict — because from the *protocol's* point of view,
form and URL elicitation both resolve to "the client answered a question with some
data or none." What differs is entirely a design decision on your side: form mode's
`content` came from a schema-validated form; URL mode's `content` is wherever you decided
to put your own proof. Here, that is one key: `receipt`.

### The check a naive integration skips

Here is the reasoning failure this chapter exists to prevent, stated as plainly as
possible: **`action == "accept"` is a claim, not evidence.**

```python
if confirmation.action != "accept":
    return PaymentNotCompleted(...)
# if we stopped here, "accept" alone would place the order — WRONG
```

Nothing enforces that whoever sent this retry is telling the truth. A buggy client, a
compromised host, or a model that decided to "help" by auto-accepting could send
`action: "accept"` with no receipt at all, and if `pay_for_order` trusted that alone, the
order would be placed for free, with no payment having occurred. Verified:

```bash
bash curl/09_no_receipt.sh <order token> <requestState>
```

```json
{"error": {"code": -32602, "message": "No payment receipt was provided. The customer must complete the payment page before this can be confirmed.", "data": {"argument": "receipt"}}}
```

The fix is to require the one artifact only the pay page can produce, and then verify it
properly — which turns out to be *two* checks, not one.

### Two checks, not one: signature, then content

```python
receipt = (confirmation.content or {}).get("receipt")
if not receipt:
    raise MCPError(code=INVALID_PARAMS, message="No payment receipt was provided. ...")

receipt_body = tokens.verify("payment_receipt", receipt)     # CHECK 1: is this signature genuine?

if receipt_body["order"] != order or abs(receipt_body["total"] - total) > 0.001:
    raise ToolError("This payment receipt does not match the current order. ...")  # CHECK 2: does its CONTENT match?
```

Check 1 asks *did this server really mint this token, unaltered?* Check 2 asks *was it
minted for what is actually being paid for right now?* These are genuinely different
questions, and skipping the second is a real vulnerability, not a theoretical one. Proof:

```bash
bash curl/09_wrong_order_receipt.sh <order token A> <requestState for A>
```

This mints a **completely real** receipt — genuinely signed by this server, for a genuine
payment — of a *different, cheaper* order, then replays it against order A's confirmation.
Check 1 passes: the signature is perfect, because it really is this server's signature.
Check 2 catches it:

```json
{"isError": true, "content": [{"type": "text",
  "text": "Error executing tool pay_for_order: This payment receipt does not match the current order. It may have been issued for a different order or a different total."}]}
```

If `pay_for_order` had stopped at "does `tokens.verify` raise?", this attack would have
succeeded — pay for the cheap thing, use the receipt to authorise the expensive thing. This
is the exact same shape of lesson as topic 08's cross-cart `requestState` replay, and
topic 07's `kind`-confusion check before that: **a valid signature answers "who signed
this", never "does this apply here."** That second question is always yours to ask.

### `request_state` is still doing its topic-08 job, unrelated to the receipt

```python
request_state=f'{{"quoted_total": {total}}}'
```

is unchanged from topic 08 — it still exists purely to catch a price drifting between
round 1 and round 2, which the automatic argument-binding cannot see (the `order` argument
is unchanged either way; the *menu* is what might have moved). The receipt mechanism and
the `request_state` price-drift check are solving two unrelated problems that happen to
live in the same function: one is about proving an external event occurred, the other is
about the world changing underneath an unchanged argument. Do not conflate them, and do
not try to fold the receipt into `request_state` — the receipt has to travel as
`inputResponses.pay.content`, because that is what the *client* actually has in hand after
the human returns from the payment page; `request_state` is what the *server* carries
forward, and the server never sees the receipt until the client sends it.

## `elicitationId`: present, optional, and not how you correlate anything

`ElicitRequestURLParams` still has an `elicitation_id` field in mcp 2.1.1 — a holdover
from the previous revision, where a server-initiated `notifications/elicitation/complete`
notification used it to say "the thing with this ID is done." That notification is gone at
2026-07-28 (there are no server-to-client requests left to notify the completion *of*), so
the field is vestigial: optional, and this chapter's design does not set it. Correlation
across the round trip is handled entirely by `request_state` (for what the server needs to
remember) and the nonce-as-token pattern (for what the pay page needs to know) — the same
two mechanisms doing the same jobs they did in topic 08, extended to a case with an actual
external hop in the middle.

## A different mechanism that looks similar and is not: `UrlElicitationRequiredError`

Worth knowing this exists so you do not confuse it with the pattern above. `mcp` exports
`UrlElicitationRequiredError`, a raisable `MCPError` subclass:

```python
raise UrlElicitationRequiredError([
    ElicitRequestURLParams(message="Authorization required", url="https://example.com/oauth/authorize"),
])
```

Raising this produces a genuine top-level JSON-RPC **error** (`-32042`), not an
`InputRequiredResult`. There is no round 2, no `requestState`, no retry-with-answers dance
— it is a one-shot "you cannot do this yet, go handle this URL first" signal, appropriate
when the server itself can independently verify completion through some *other* channel
(an OAuth provider's own token endpoint, for instance) rather than needing the client to
carry proof back. This chapter's pattern — `InputRequiredResult` in URL mode — is the
right choice whenever *you* control the completion signal (as with this fake payment
page); `UrlElicitationRequiredError` is the right choice when a third party does.

## Layer 3 — Dry-run: from link to receipt to placed order

**Round 1.** `pay_for_order(order="v1.eyJl...fOs")`. Cart loads and prices to $8.60.
`ctx.input_responses is None`.

```text
nonce = sign("pay_nonce", {"order": "v1.eyJl...fOs", "total": 8.6}, ttl_s=300)
      = "v1.eyJl...4Y"
pay_url = "http://127.0.0.1:3010/pay/v1.eyJl...4Y"
return InputRequiredResult(
    input_requests={"pay": ElicitRequest(..., ElicitRequestURLParams(mode="url", message=..., url=pay_url))},
    request_state='{"quoted_total": 8.6}',
)
```

**The human's browser (or curl, standing in for one).** `GET /pay/v1.eyJl...4Y` — verifies
the nonce, renders "Pay $8.60" with a button. `POST /pay/v1.eyJl...4Y` — "clicked Pay" —
re-verifies the nonce, mints:

```text
receipt = sign("payment_receipt", {"order": "v1.eyJl...fOs", "total": 8.6}, ttl_s=300)
        = "v1.eyJl...Ts"
```

and hands it back as `{"paid": true, "total": 8.6, "receipt": "v1.eyJl...Ts"}`.

**Round 2, quite possibly on a different process.** The client retries:

```text
pay_for_order(order="v1.eyJl...fOs")      <- unchanged, SDK verifies the binding automatically
  + inputResponses: {"pay": {"action": "accept", "content": {"receipt": "v1.eyJl...Ts"}}}
  + requestState: <round 1's sealed envelope>
```

Inside the handler:

```text
cart reloads and reprices -> total 8.6 again (menu unchanged)
quoted_total (from request_state) == 8.6 -> no price drift
confirmation.action == "accept"
receipt = "v1.eyJl...Ts"
tokens.verify("payment_receipt", receipt) -> {"order": "v1.eyJl...fOs", "total": 8.6}
receipt_body["order"] == order            -> matches
abs(receipt_body["total"] - total) < 0.001 -> matches
return PaymentAccepted(ticket="P-269", ...)
```

Count what never happened anywhere in that trace: the model never read a card number,
never rendered the pay page's HTML, never saw the receipt's contents, never even saw that
a `request_state` price check occurred. It asked one question — "did the customer pay?" —
and got one answer back.

## Gotchas

**`action == "accept"` is never proof by itself.** It is a claim from whoever sent the
retry. Require and verify your own artifact.

**Signature-valid is not the same as content-valid.** Check both, always, for any signed
token whose *payload* could legitimately apply to something other than the current call —
which is every token in this folder except the very simplest cursor.

**URL mode has no `requestedSchema`.** There is nothing to validate; the "answer" is
whatever your own design decided to put in `content`.

**The nonce must be self-describing.** No server memory connects the route that issues it
to the route that later reads it.

**`elicitation_id` is optional and does no correlating work here.** `request_state` and
signed nonces already cover it.

**`UrlElicitationRequiredError` is a different mechanism** — a one-shot protocol error, not
part of the MRTR round trip. Reach for the `InputRequiredResult` pattern above whenever
you, the server, are the one who will produce the completion proof.

## Your turn

`solutions/t09_url_mode.py`, seven TODOs. TODO 5 — the receipt check — is where the actual
thinking is; everything before it is wiring you have written before, in a slightly new
shape.

Before you write the two-check verification, predict `curl/09_wrong_order_receipt.sh`'s
output. If your prediction is "it should fail because the receipt is invalid," you have
not yet separated the two checks in your head — the receipt in that script is entirely
valid. Reread the section above until your prediction is "it fails because the receipt is
for the wrong order," which is a different and more precise claim.

## Connection forward

Every tool built so far — pagination, the cart, both confirmation flows — answers a
question and returns. Topic 10 changes that shape for the first time: `brew()` is a tool
that takes several seconds and reports *progress* while it runs, using the other half of
"streamable" HTTP that nothing so far has touched. It is also where you will watch
something genuinely disappear: SSE resumability, removed at this revision, meaning a
connection dropped mid-brew cannot be reattached — the client's only recourse is to start
the whole request over, with a new id, from nothing.

Does this make sense? Want me to go deeper on any part — why the nonce and the receipt
need to be different token `kind`s, the two-check verification pattern, or when
`UrlElicitationRequiredError` is the better tool for the job?
