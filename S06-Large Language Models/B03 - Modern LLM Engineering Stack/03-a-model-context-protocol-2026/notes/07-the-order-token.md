# The Order Token: A Cart That Lives in a Tool Argument

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [The shape: `v1.<payload>.<signature>`](#the-shape-v1payloadsignature)
  - [The three fields every token carries](#the-three-fields-every-token-carries)
  - [Verification, in the order that matters](#verification-in-the-order-that-matters)
  - [`hmac.compare_digest`, never `==`](#hmaccompare_digest-never)
  - [`kind` — domain separation, and why it is the field that matters most](#kind-domain-separation-and-why-it-is-the-field-that-matters-most)
  - [The message never says *which* check failed, in detail](#the-message-never-says-which-check-failed-in-detail)
  - [Same rule as a bad cursor, restated for a bigger stake](#same-rule-as-a-bad-cursor-restated-for-a-bigger-stake)
  - [Never trust a stored price — reprice on every read](#never-trust-a-stored-price-reprice-on-every-read)
  - [`view_order` refreshes the expiry — with a wrinkle worth knowing](#view_order-refreshes-the-expiry-with-a-wrinkle-worth-knowing)
  - [Reading `add_to_order`'s validation order](#reading-add_to_orders-validation-order)
- [Layer 3 — Dry-run: two calls, one cart, across "two instances"](#layer-3-dry-run-two-calls-one-cart-across-two-instances)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

An order token is topic 06's cursor with the stakes turned up — the same "state as a
value, not as server memory" idea, now HMAC-signed because the payload is a shopping cart
someone will actually be charged for.

## Where this sits

Topic 06 built a token for something worthless to forge: an offset into a public menu.
This topic builds one for something that is not — line items and a total. The shape barely
changes. What changes is that forging this one is now the whole game, so the token has to
prove it came from this server, untouched.

```text
topic 06   cursor   v1.<payload>              opaque, unsigned — nothing worth protecting
topic 07   order    v1.<payload>.<signature>   opaque, SIGNED   — a real total at stake
```

One more segment. That segment is the entire chapter.

## The problem this topic solves

`add_to_order` needs to remember a cart across several calls — add a latte, then an
espresso, then check the total — with no session to hold it in. Topic 06 already showed
the pattern: mint a token, hand it back, decode it next time.

But now think about what a forged token would buy an attacker. A forged *cursor* gets you,
at worst, the wrong five drinks out of a public menu. A forged *order* token could claim a
cart contains one cheap drink when the customer actually wants three expensive ones, or
resurrect a stale cart from last week with today's different prices. The payload has a
real total on the other end of it. That is the difference that makes signing worth its
cost.

## Layer 1 — The intuition

Back to the deli-counter ticket from topic 06. That ticket just said "next: 48" — nobody
loses anything if you scribble a different number on your own ticket at home, because the
counter would just hand you the wrong sandwich, not someone else's money.

Now imagine the ticket is a gift card with a stored balance printed on it. Suddenly a
photocopier is a serious threat. The store cannot stop you *holding* a piece of paper that
says "$50" — but it can make sure that only a card it genuinely issued, unaltered, is
honoured at the register. That is a signature: not secrecy (the balance is printed in
plain sight, same as topic 06's cursor was readable with `base64 -d`), but **proof of
origin and integrity** — *this exact card, unaltered, came from us*.

## Layer 2 — The mechanics

### The shape: `v1.<payload>.<signature>`

```python
def sign(kind: str, payload: dict, ttl_s: int) -> str:
    now = int(time.time())
    body = {"kind": kind, "iat": now, "exp": now + ttl_s, **payload}
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body_b64 = _b64encode(raw)
    signature = hmac.new(_secret(), body_b64.encode("ascii"), hashlib.sha256).digest()
    signature_b64 = _b64encode(signature)
    return f"v1.{body_b64}.{signature_b64}"
```

```text
sign("order", {"lines": [{"slug": "latte", "size": "L", "qty": 2}]}, ttl_s=900)
  -> "v1.eyJleHAiOjE3ODg2MjU3NDgsImlhdCI6MTc4ODYyNDg0OCwia2luZCI6Im9yZGVyIiwibGluZXMiOlt7InF0eSI6Miwic2l6ZSI6IkwiLCJzbHVnIjoibGF0dGUifV19.95krq4HFGifGxhhLScoLgproeHxl3GmQ4nv5ZF3yfOs"
```

Three dot-separated parts: a version tag (same reason as topic 06 — a future
encoding change fails cleanly instead of silently), the base64url payload, and a
base64url HMAC-SHA256 signature over that *exact payload string*.

### The three fields every token carries

```python
body = {"kind": kind, "iat": now, "exp": now + ttl_s, **payload}
```

**`kind`** — what this token is *for*. Explained fully below; it is the single most
important field in the whole scheme.

**`iat`** (issued-at) and **`exp`** (expires-at) — a self-contained expiry. The server
never has to look anything up to know a token is stale; the token says so about itself.

### Verification, in the order that matters

```python
def verify(kind: str, token: str) -> dict:
    parts = token.split(".", 2)
    if len(parts) != 3 or parts[0] != "v1":
        raise TokenError("this token is not in a format this server recognises")

    _, body_b64, signature_b64 = parts
    given_signature = _b64decode(signature_b64)
    expected_signature = hmac.new(_secret(), body_b64.encode("ascii"), hashlib.sha256).digest()

    if not hmac.compare_digest(expected_signature, given_signature):
        raise TokenError("this token's signature does not match — it was not "
                          "issued by this server, or has been altered")

    body = json.loads(_b64decode(body_b64))
    if body.get("kind") != kind:
        raise TokenError(f"this token was not issued as a {kind!r} token "
                          f"(it is {body.get('kind')!r}) — it cannot be used here")

    if time.time() > body.get("exp", 0):
        raise TokenError(f"this {kind} token has expired — start again")

    return body
```

The order is not arbitrary. **Signature first**, because nothing else about an unsigned
token can be trusted — not even "this parses as valid JSON" is proof of anything, since
anyone can construct valid JSON. Verifying the signature *before* trusting the payload is
what makes every check after it meaningful.

### `hmac.compare_digest`, never `==`

```python
if not hmac.compare_digest(expected_signature, given_signature):
```

Plain `==` on two byte strings in CPython short-circuits at the first differing byte, so
comparing a forged signature byte-by-byte takes measurably less time the earlier it
diverges from the real one. That timing difference is a **side channel**: an attacker who
can measure response latency precisely enough could forge a valid signature one byte at a
time, trying all 256 values for byte 0, keeping whichever took longest, then moving to
byte 1. `hmac.compare_digest` runs in time that does not depend on where the strings first
differ, closing that channel entirely. This is not paranoia for a learning project — it is
the standard-library function that exists *specifically* for comparing secrets, and using
plain `==` here would be the one security mistake in this file that a reviewer should
flag immediately.

### `kind` — domain separation, and why it is the field that matters most

Here is the scenario `kind` exists to prevent. Topic 08 introduces a second signed token —
`requestState`, carrying a place-order confirmation in flight. Both tokens are, to the
codec, nothing more than *some signed JSON*. Without a `kind` check, a client could take a
valid `requestState` token from topic 08 and hand it to `view_order` here, or the reverse,
and the signature would verify perfectly — because the signature only proves *this server
signed this exact byte string*, not *this byte string means what you're about to assume it
means*.

```python
body.get("kind") != kind    # e.g. "place_order_state" != "order"
```

catches exactly that. Verified on the wire:

```text
view_order(order=<a token signed as kind="place_order_state">)
  -> isError: true, "That order token is not valid (this token was not issued as
     an 'order' token (it is 'place_order_state') — it cannot be used here)."
```

The signature was completely valid. The token was still refused, because it was signed for
a different *purpose*. This is worth remembering as the reason `kind` exists at all: a
signature answers "did this come from me, unaltered?"; `kind` answers the question the
signature cannot — "was this the thing I meant to accept *here*?"

### The message never says *which* check failed, in detail

```python
raise TokenError("this token's signature does not match — it was not issued by "
                  "this server, or has been altered")
```

Compare this to a bad slug's message, which happily says exactly what was wrong
("Espresso is not sold in size 'L'. It comes in: S, M"). The order token's failure message
is deliberately vaguer for a reason that has nothing to do with being unhelpful: telling an
attacker *which specific check* failed — bad signature vs. wrong kind vs. expired — hands
them a map of what to try next. "Signature invalid" narrows an attacker's search space far
less than "signature valid but expired" would, because the second tells them their forgery
attempt actually *worked* and only timing was the problem. One `TokenError` type, one
level of detail, for every failure mode.

### Same rule as a bad cursor, restated for a bigger stake

```python
except tokens.TokenError as exc:
    raise ToolError(
        f"That order token is not valid ({exc}). Start a new order by "
        f"calling `add_to_order` again with no `order` argument."
    ) from None
```

Exactly the reasoning from topic 06: a token is opaque, so there is nothing in it a model
could reason about to construct a *better* one. The only honest recovery is starting over,
so — as with the cursor — that is the only thing the message offers. What is new here is
that "starting over" now means losing a cart, not just re-fetching a page, which is why the
15-minute TTL exists: long enough that a real conversation is not derailed by a slow
customer, short enough that a forgotten cart from yesterday cannot resurface today at
yesterday's prices.

### Never trust a stored price — reprice on every read

```python
def _reprice(cart_lines: list[dict]) -> list[OrderLine]:
    for line in cart_lines:
        unit_price = menu.price_of(line["slug"], line["size"])
        if unit_price is None:
            raise ToolError(f"{line['slug']} is no longer sold in size {line['size']!r}. "
                             f"The menu changed since this item was added — start a new "
                             f"order with `add_to_order`.")
        ...
```

The token stores **what** was ordered — slug, size, qty — never what it cost at the
moment it was added. Every call to `view_order` or `add_to_order` recomputes every line's
price from the *current* menu. If the café's prices change between adding a latte and
checking out, the customer sees today's price, honestly, rather than a stale one frozen
inside an old token. This also means a cart can legitimately become un-priceable — a drink
discontinued between adding it and viewing it — and that failure gets exactly the same
`ToolError` treatment as any other menu mismatch.

### `view_order` refreshes the expiry — with a wrinkle worth knowing

```python
def view_order(order: str) -> OrderResult:
    body = tokens.verify(ORDER_KIND, order)
    return _order_result({"lines": body["lines"]})
```

`_order_result` always signs a **brand-new** token, even for a read that changes nothing.
That is deliberate: it means simply *checking* on a cart resets its 15-minute clock, so a
customer who is still deciding does not lose their cart mid-conversation just because they
asked to see it again.

Here is the wrinkle. `sign()` embeds `iat = int(time.time())`, and with
`sort_keys=True` the same logical payload always produces the same JSON bytes. So two
calls landing in the **same wall-clock second** produce a byte-identical token —
"refreshed", but unchanged in appearance. Verified:

```text
add_to_order, then immediately view_order        -> token UNCHANGED (same second)
add_to_order, then view_order 1.2 seconds later   -> token CHANGED
```

Neither is a bug. The clock genuinely did refresh both times; it just has one-second
resolution, so a refresh that happens to land in the same tick is invisible from the
outside. `test_tokens.py` pins this exact behaviour so nobody "fixes" it into something
more surprising later — a truly-fresh-every-time signature would need sub-second precision
or a random nonce, neither of which this token needs for what it is protecting.

### Reading `add_to_order`'s validation order

```python
if menu.find(slug) is None:
    raise ToolError(...)                    # 1. does the drink exist?
if menu.price_of(slug, size) is None:
    raise ToolError(...)                    # 2. is it sold in that size?
if order is None:
    cart = _empty_cart()
else:
    try:
        body = tokens.verify(ORDER_KIND, order)
    except tokens.TokenError as exc:
        raise ToolError(...)                # 3. is the existing cart valid?
cart["lines"].append({"slug": slug, "size": size, "qty": qty})
```

Both menu checks run **before** the cart is touched at all. A bad line can never corrupt
an otherwise-good cart, because the cart is not even looked at until the new line has
already proven valid. Verified: a bad-size call returns `isError: true` with **no**
`structuredContent` key at all — there is nothing to show, because nothing was built.

## Layer 3 — Dry-run: two calls, one cart, across "two instances"

There is no load balancer yet (that is topic 14), but the whole design only makes sense if
you can picture it working across processes that share nothing. Walk it that way.

**Call 1 — a fresh process, `add_to_order(slug="latte", size="L", qty=2)`, no `order`.**

```text
menu.find("latte")          -> found
menu.price_of("latte","L")  -> 4.30, not None
order is None -> cart = {"lines": []}
cart["lines"].append({"slug": "latte", "size": "L", "qty": 2})
_order_result(cart):
  _reprice -> [OrderLine(name="Latte", size="L", qty=2, unit_price=4.30, line_total=8.60)]
  total = 8.60
  new_token = sign("order", {"lines": [{"slug":"latte","size":"L","qty":2}]}, ttl_s=900)
            = "v1.eyJl...fQ.95kr...fOs"
```

The client walks away with that token. This process could now vanish.

**Call 2 — a DIFFERENT process, `add_to_order(slug="espresso", size="S", qty=1, order="v1.eyJl...fOs")`.**

```text
menu.find("espresso")            -> found
menu.price_of("espresso","S")    -> 2.20, not None
order is not None:
  tokens.verify("order", "v1.eyJl...fOs")
    signature check: recompute HMAC over the payload segment, compare_digest
      against the given signature -> MATCH (this process shares the same secret)
    kind check: body["kind"] == "order" -> yes
    exp check: not yet expired -> yes
  body = {"kind": "order", "iat": ..., "exp": ..., "lines": [{"slug":"latte","size":"L","qty":2}]}
cart = {"lines": [{"slug":"latte","size":"L","qty":2}]}
cart["lines"].append({"slug": "espresso", "size": "S", "qty": 1})
_order_result(cart):
  _reprice -> [Latte L×2 @ 4.30 = 8.60, Espresso S×1 @ 2.20 = 2.20]
  total = 10.80
  new_token = sign("order", {"lines": [...(two lines)...]}, ttl_s=900)
```

Note what made this work with zero shared memory between the two processes: **the same
`_secret()`**. Any instance that can compute the same HMAC key can verify a token any
other instance minted. That single shared value — not a session, not a database row, not
sticky routing — is the entire coordination mechanism, and it is exactly why topic 14's
load balancer demo will be able to route this flow across three separate server processes
and have it still work.

## Gotchas

**`hmac.compare_digest`, never `==`.** The one line in this file where getting it wrong is
a genuine vulnerability, not a style choice.

**`kind` is not optional ceremony.** The moment a second signed-token kind exists (topic
08), an unchecked kind is a replay vector between them.

**A token's message can only ever say "start over".** Same reasoning as topic 06's cursor,
higher stakes.

**Reprice on every read.** Never trust a price baked into an old token.

**A same-second refresh looks like no refresh.** `iat` has one-second resolution; that is
a real property of this design, not a bug to chase.

**Validate everything about the new line before touching the existing cart.** Order of
operations is what keeps a bad call from corrupting a good cart.

**The signing key must be shared across every instance.** `_secret()` reads
`CAFE_MCP_SECRET`, with a loud fallback. Miss this in a real deployment and instance B
cannot verify a token instance A minted — which looks exactly like "random tampering
detected" and is much harder to diagnose.

## Your turn

`solutions/t07_order_token.py`, six TODOs. `cafe_mcp/tokens.py` is given to you complete
and fully tested — you are writing the café-specific tool logic on top of a
generic signing mechanism.

TODO 4 is the one worth the most thought: decide the validation order for
`add_to_order` yourself before looking at the solved version, and be able to say why
checking the *new line* has to happen before touching the *existing cart*.

Run `bash curl/07_walk_order.sh` once as a sanity check, then deliberately break it with
`bash curl/07_tamper.sh` — flipping one character of a real token and watching a
completely valid-looking string get refused is the moment this topic actually lands.

## Connection forward

The café can now hold a cart across calls with zero server memory, and it can prove that
cart was not tampered with. What it still cannot do is **commit** the order — because
committing needs one more thing that has been unavailable since topic 00: asking a human
for confirmation.

That used to be a server-initiated request — `elicitation/create` — but topic 00 already
told you that direction is gone. Zero server-to-client requests at 2026-07-28. So how does
a server that cannot ask, ask?

Topic 08 answers that, and it is the single most interesting idea in the whole revision:
**MRTR**. A tool that needs an answer does not send a request — it *returns* one, packaged
as the reply to the very call that needed it, and the client retries the same call a
second time carrying the answer. The order token you just built is exactly the mechanism
that makes the retry safe: the half-finished confirmation state gets signed the same way,
with its own `kind`, and the `kind` check you just wrote is precisely what stops it from
being confused with the cart it is about to place.

Does this make sense? Want me to go deeper on any part — why signature verification has to
run before every other check, the timing-attack reasoning behind `compare_digest`, or how
`kind` will extend to a second token type in topic 08?
