# Pagination: The Opaque Cursor

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [The token: `v1.<base64url(json)>`](#the-token-v1base64urljson)
  - ["Opaque" is a promise about usage, not a claim about secrecy](#opaque-is-a-promise-about-usage-not-a-claim-about-secrecy)
  - [Validating a cursor is caller-supplied input](#validating-a-cursor-is-caller-supplied-input)
  - [Why a bad cursor's message is different from a bad slug's](#why-a-bad-cursors-message-is-different-from-a-bad-slugs)
  - [The one termination signal that is actually reliable](#the-one-termination-signal-that-is-actually-reliable)
- [Layer 3 — Dry-run: walking all twelve drinks](#layer-3-dry-run-walking-all-twelve-drinks)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

A pagination cursor is a server-minted token encoding "where you were", handed back on
the next call so that any instance of the server can pick up exactly where the last one
left off — without either instance remembering anything.

## Where this sits

Topic 00 ended on a question and deliberately did not answer it:

> If sessions are gone, and a server needs to remember something across two calls, where
> does it live?

This topic is the smallest possible answer. "Something" here is only a position in a
list — twelve drinks, a page of five, where was I? Topic 07 answers the same question for
a real shopping cart, and topic 08 for a half-finished request. All three are the same
shape. This one is worth building first because it is small enough to see whole.

## The problem this topic solves

`list_drinks` in Part 1 and Part 2 returns all twelve drinks in one call. Fine for twelve.
Not fine for twelve thousand — the response would be enormous, most of it wasted if the
model only needed the first few, and there would be no way to ask for "the rest" without
resending everything.

The obvious old-world fix is a session: the server remembers "this client was at position
5" and a follow-up call just says "continue". But sessions are exactly what got removed at
2026-07-28, and for a good reason — that memory pins the client to one process. So the
fix cannot be "the server remembers". It has to be "the client carries what would have
been remembered", handed to it in a form it cannot misuse.

## Layer 1 — The intuition

You are at a deli counter with a numbered-ticket machine. You take ticket 47. The counter
does not remember that *you specifically* hold ticket 47 — no camera, no name on a list.
The ticket itself carries everything that matters: "the next call is 48". Any employee at
any counter, on any day, can look at ticket 47 and know exactly what to do next. The
information lives in your hand, not in the shop's memory.

A cursor is that ticket. `list_drinks()` returns five drinks and a cursor that means "next
call: offset 5". You bring that cursor back, and it does not matter which process of the
café's server answers — the cursor alone tells it where to resume.

## Layer 2 — The mechanics

### The token: `v1.<base64url(json)>`

```python
def encode_cursor(offset: int) -> str:
    payload = json.dumps({"offset": offset}, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"v1.{token}"
```

```text
encode_cursor(5)  ->  "v1.eyJvZmZzZXQiOjV9"
```

Three deliberate choices, each earning its keep somewhere else in this folder.

**A version tag.** `v1.` costs four characters and buys a migration path. If the encoding
ever changes — say, to carry a filter alongside the offset — a `v2.` cursor can be
rejected cleanly instead of silently misread as `v1.` and producing garbage. Verified:

```text
decode_cursor("v2.eyJvZmZzZXQiOjV9")  ->  CursorError: unrecognised cursor format
```

**Base64url, not base64.** URL-safe alphabet (`-_` instead of `+/`), because this string
travels inside JSON inside an HTTP body — plain base64's `+` and `/` are legal there too,
but url-safe removes an entire category of "which encoding did this actually use" bugs the
moment a cursor ever needs to travel inside a URL query string instead.

**Padding stripped, then restored on decode.** `rstrip("=")` on encode,
`"=" * (-len(token) % 4)` on decode. Trailing `=` padding is redundant information — the
length modulo 4 tells you how much is missing — and stripping it makes cursors a few bytes
shorter for no cost. This is a real but minor detail; the reason to notice it is that
forgetting the padding restoration is the single most common reason a hand-rolled base64
decode fails on an otherwise-correct string.

### "Opaque" is a promise about usage, not a claim about secrecy

Try this yourself:

```bash
bash curl/06_decode_cursor.sh 'v1.eyJvZmZzZXQiOjV9'
```

```text
token part:  eyJvZmZzZXQiOjV9
{"offset":5}
```

Plain JSON. Nothing hidden, nothing signed. Anyone with a terminal can read a café cursor
in one command.

And the client must still never construct one, or edit one, or read it and act on the
value. "Opaque" here means *the contract between client and server is: copy this back
exactly, and treat its contents as none of your business* — not *this is a secret*. The
café's contract is honoured by the client's good behaviour, not by cryptography, because
there is nothing here worth protecting: an offset into a public menu is not sensitive, and
forging one costs an attacker nothing (worst case, a wrong page of drinks).

That is a genuinely different situation from topic 07's order token, where the payload
*is* worth protecting — a cart total, an amount owed — and the token really is
HMAC-signed. Building the plain version first is what makes the signed version legible
later: you will be able to say exactly what changed and why, instead of the signing
looking like unexplained ceremony.

### Validating a cursor is caller-supplied input

The moment a cursor leaves the server, it is data from an untrusted source — the fact that
*your* server produced it does not mean the next request actually carries what you sent,
because clients can be buggy, and models can hallucinate one. Every failure mode gets a
name and a clean rejection rather than a crash:

```python
def decode_cursor(cursor: str) -> int:
    prefix, _, token = cursor.partition(".")
    if prefix != "v1" or not token:
        raise CursorError(f"unrecognised cursor format: {cursor!r}")

    padding = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(token + padding)
        data = json.loads(raw)
    except Exception as exc:
        raise CursorError(f"cursor does not decode to valid data: {cursor!r}") from exc

    if not isinstance(data, dict) or "offset" not in data:
        raise CursorError(f"cursor is missing the 'offset' field: {cursor!r}")

    offset = data["offset"]
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise CursorError(f"cursor offset is not a non-negative integer: {offset!r}")

    return offset
```

Verified, every branch:

```text
"garbage-not-base64-at-all!!"         -> CursorError: unrecognised cursor format
"v2.eyJvZmZzZXQiOjV9"                 -> CursorError: unrecognised cursor format (wrong version)
"v1."                                 -> CursorError: unrecognised cursor format (empty token)
well-formed base64 of {"not_offset":5} -> CursorError: missing the 'offset' field
well-formed base64 of {"offset": -1}   -> CursorError: not a non-negative integer
well-formed base64 of {"offset": "5"}  -> CursorError: not a non-negative integer
well-formed base64 of {"offset": true} -> CursorError: not a non-negative integer
```

That last one is worth a beat: `isinstance(True, int)` is `True` in Python, because `bool`
subclasses `int`. Without the explicit `isinstance(offset, bool)` check, a cursor carrying
`{"offset": true}` would silently become `offset=1`. This is the kind of bug that a type
checker will never flag and a test absolutely will — `test_pagination.py` has a case for
exactly this.

`CursorError` lives in `cafe_mcp/pagination.py`, and it is a plain Python exception — the
module knows nothing about MCP or ToolError, same discipline as `menu.py`'s `KeyError` and
`render.py`'s `KeyError`. The *tool* converts it:

```python
except pagination.CursorError as exc:
    raise ToolError(
        f"That cursor is not valid for this server ({exc}). Cursors are opaque "
        f"and must be copied exactly from a previous `next_cursor` — call "
        f"`list_drinks` again with no `cursor` argument to start from the "
        f"beginning."
    ) from None
```

### Why a bad cursor's message is different from a bad slug's

Compare the two error messages side by side.

```text
bad slug    ->  "There is no drink with slug 'no-such-drink'. Call `list_drinks`
                 to see the twelve slugs that exist."

bad cursor  ->  "That cursor is not valid for this server. Cursors are opaque and
                 must be copied exactly from a previous `next_cursor` — call
                 `list_drinks` again with no `cursor` argument to start from
                 the beginning."
```

A bad slug has an obvious next step: *try a real one*, and `list_drinks` will show you
some. A bad cursor has no such step. It is opaque, by design — there is nothing in a
cursor a model could reason about to construct a *better* one. The only honest recovery is
*start over*, so that is the only thing the message offers. Writing "try a valid cursor" here
would be actively misleading, because there is no way for the reader to know what a valid
one looks like without simply asking for a fresh one.

### The one termination signal that is actually reliable

```python
def page(items: list, cursor: str | None, limit: int) -> tuple[list, str | None]:
    offset = decode_cursor(cursor) if cursor else 0
    chunk = items[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < len(items) else None
    return chunk, next_cursor
```

`next_cursor is None` is the only signal a caller should use to know it has reached the
end. This deserves emphasis because the tempting shortcut — *if the page came back shorter
than `limit`, that must be the last page* — is wrong whenever the total happens to divide
evenly by the page size.

Twelve drinks, page size six:

```text
call 1 (limit=6, no cursor)  -> 6 drinks, next_cursor NOT null
call 2 (limit=6, cursor=...)  -> 6 drinks, next_cursor IS null
```

The first page is completely full and is still not the last one. A client that stopped
because "the page was full-size" — reasoning that a partial page means the end, so a full
page must mean there's more, which sounds right until you realize a full page can *also* be
the actual end — would only be caught out here, not on an unevenly-sized menu, which is
exactly why this test exists rather than being left to chance:
`test_page_of_exactly_limit_size_is_not_necessarily_last`.

## Layer 3 — Dry-run: walking all twelve drinks

**Call 1.** `list_drinks()`, no cursor.

```text
offset = 0 (no cursor to decode)
chunk = DRINKS[0:5]  = espresso, macchiato, cortado, flat-white, latte
next_offset = 5, and 5 < 12, so:
next_cursor = encode_cursor(5) = "v1.eyJvZmZzZXQiOjV9"
```

**Call 2.** `list_drinks(cursor="v1.eyJvZmZzZXQiOjV9")`.

```text
decode_cursor("v1.eyJvZmZzZXQiOjV9") -> 5
chunk = DRINKS[5:10] = cappuccino, americano, mocha, cold-brew, oat-latte
next_offset = 10, and 10 < 12, so:
next_cursor = encode_cursor(10) = "v1.eyJvZmZzZXQiOjEwfQ"
```

**Call 3.** `list_drinks(cursor="v1.eyJvZmZzZXQiOjEwfQ")`.

```text
decode_cursor(...) -> 10
chunk = DRINKS[10:15] = creme-brulee-latte, chai   (only 2 exist)
next_offset = 15, and 15 is NOT < 12, so:
next_cursor = None
```

The client sees `next_cursor: null` and stops — not because the page had only two drinks
(a page can legitimately be short and *not* be last, if the menu had thirteen), but
because the signal that matters said so explicitly. `bash curl/06_walk_all_pages.sh` does
exactly this loop and prints all three pages.

## Gotchas

**A short page is not proof of the end.** Only `next_cursor is None` is.

**A full page is not proof there's more.** Same rule, other direction — twelve items at
page size six produces a full first page that is genuinely not the last.

**`bool` is an `int` in Python.** Check for it explicitly wherever you validate that
something "is an integer", or a cursor carrying `true` silently becomes `1`.

**Opaque does not mean secret.** It means "the client's only job is to copy this back
exactly". Whether the *contents* also need protecting is a separate design question — this
topic says no, topic 07 says yes for a different payload.

**A bad cursor's error message can only ever say "start over".** There is no partial fix
to suggest, unlike a bad slug.

**The cursor encodes a position, not a page size.** `limit` can change between calls
without breaking anything — `test_cursor_from_a_different_limit_still_works` proves it.
Fetch at `limit=5`, continue at `limit=3`, and you neither skip nor repeat a drink.

**Constrain `limit` in the schema, not in code.** `Field(ge=1, le=10)` rejects an
out-of-range value before your function runs — the same call you already made in topic 03
for `qty`.

## Your turn

`solutions/t06_pagination.py`, four TODOs. `cafe_mcp/pagination.py` is given to you
complete and already tested — you are writing the tool that wraps it.

The one worth taking seriously is the `ToolError` message for a bad cursor. Before you
write it, answer out loud: *what is the one thing I can honestly tell the model to do
next?* If your answer is anything other than "start over with no cursor", you have not
yet internalised why a cursor is opaque.

Prove it with the walking script first — `bash curl/06_walk_all_pages.sh` — before you
try to break it with `06_bad_cursor.sh`. Seeing the happy path work end to end makes the
failure path easier to appreciate.

## Connection forward

The cursor remembers a *position* — read-only, disposable, worth nothing to anyone who
might forge one. Topic 07 asks the same question about something that actually matters: a
shopping cart, carrying items and a running total. The shape of the solution barely
changes — mint a token, hand it back, decode it next time — but the stakes do, and that is
exactly why this one had to come first: everything that is new in topic 07 is now visible
by contrast, instead of buried under new mechanics.

Does this make sense? Want me to go deeper on any part — why versioning a token costs so
little and buys so much, the bool-is-an-int trap, or why "opaque" and "secret" are
different properties?
