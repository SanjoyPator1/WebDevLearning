# Gateway Headers: `Mcp-Param-*`, `x-mcp-header`, and Non-ASCII

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [Marking an argument for mirroring](#marking-an-argument-for-mirroring)
  - [What actually goes out on the wire](#what-actually-goes-out-on-the-wire)
  - [Enforcement: header and body must agree, in both directions](#enforcement-header-and-body-must-agree-in-both-directions)
  - [Why non-ASCII needs a sentinel at all](#why-non-ascii-needs-a-sentinel-at-all)
  - [The one gotcha this topic exists to warn about](#the-one-gotcha-this-topic-exists-to-warn-about)
- [Layer 3 — Dry-run: announcing the Crème Brûlée Latte](#layer-3-dry-run-announcing-the-crème-brûlée-latte)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)

## One sentence

`x-mcp-header` marks one tool argument for mirroring into its own `Mcp-Param-<Token>`
HTTP header, so a gateway sitting in front of your server can route, rate-limit, or log on
that argument's value without ever parsing the JSON-RPC body — and because an HTTP header
cannot carry raw non-ASCII bytes, any value that would not survive the trip gets wrapped in
a small base64 sentinel first.

## Where this sits

Every script since topic 01 has sent `Mcp-Method`, and every name-bearing call has sent
`Mcp-Name` — both mirroring something from the JSON-RPC body into a header, purely so
infrastructure in front of the server can act on it cheaply. Those two headers are fixed by
the protocol: every server gets them, for free, with no configuration. This topic is about
the version of that idea *you* control: marking your own tool's own argument for the exact
same treatment.

## The problem this topic solves

A gateway routing MCP traffic wants to make decisions — which backend gets this request,
should this caller be rate-limited, is this argument worth logging — without paying the
cost of parsing a JSON body on every single request, especially at the volume a real
gateway sees. `Mcp-Method` and `Mcp-Name` solve this for the method and the target. Neither
helps if the decision needs to look at a specific *argument* — the drink being ordered, the
tenant ID embedded in a call, anything domain-specific. `x-mcp-header` extends the same
header-mirroring idea to any argument you choose.

## Layer 1 — The intuition

A parcel courier does not open every box to read the invoice inside before deciding which
truck it goes on — the address is printed on the *outside*, specifically so the sorting
step never has to open anything. `Mcp-Method` and `Mcp-Name` are the address label every
MCP parcel already carries. `x-mcp-header` is how you print one more line on the outside
of your own parcels — "contains: Crème Brûlée Latte" — so anyone sorting them can act on it
without ever opening the box.

## Layer 2 — The mechanics

### Marking an argument for mirroring

```python
name: Annotated[
    str,
    Field(
        description="The drink's exact display name, e.g. 'Latte' or 'Crème Brûlée Latte'.",
        json_schema_extra={"x-mcp-header": "DrinkName"},
    ),
],
```

`json_schema_extra` is an ordinary pydantic mechanism for adding arbitrary keys to a
field's generated JSON Schema; `x-mcp-header` is simply a key the MCP SDK looks for and
treats specially. The **value** — `"DrinkName"` — is the token that becomes the header
name: `Mcp-Param-DrinkName`. This is worth saying twice, because it is the one thing that
goes wrong silently: the value is a **string naming the header**, never a boolean saying
"yes, mirror this."

Verified on the wire, `tools/list` publishes the annotation exactly as written:

```json
{"name": {"type": "string", "title": "Name", "x-mcp-header": "DrinkName",
          "description": "The drink's exact display name, e.g. 'Latte' or 'Crème Brûlée Latte'."}}
```

### What actually goes out on the wire

Call `announce_drink(name="Latte")` and the request carries both the ordinary body
argument and the mirrored header:

```text
Mcp-Param-DrinkName: Latte

{"params": {"name": "announce_drink", "arguments": {"name": "Latte"}, "_meta": {...}}}
```

A gateway can read `Mcp-Param-DrinkName` directly off the request line and headers, with
zero JSON parsing, and already knows which drink this call concerns.

### Enforcement: header and body must agree, in both directions

The SDK does not merely publish the annotation and leave enforcement to you. Every
`tools/call` for an annotated argument is checked, and the check runs *before* your tool
function is ever entered — this is the same rejection family as `Mcp-Method` and
`Mcp-Name` from topic 01, extended to a third kind of mismatch.

**Header disagrees with body:**

```bash
bash curl/13_mismatched_param.sh
```

```json
{"error": {"code": -32020,
           "message": "Mcp-Param-DrinkName header does not match the request body's 'name' argument"}}
```

**Header absent, argument present:**

```bash
bash curl/13_missing_param.sh
```

```json
{"error": {"code": -32020,
           "message": "Mcp-Param-DrinkName header is missing but the request body's 'name' argument is present"}}
```

Both fail with `-32020`, the same code as a wrong `Mcp-Method`. A conforming client that
supports `x-mcp-header` is expected to mirror an annotated argument every time, not
opportunistically — "sometimes attach the header" is not a legal client behavior any more
than "sometimes send the right `Mcp-Method`" would be.

### Why non-ASCII needs a sentinel at all

This is not an SDK design choice — it is a hard limit of HTTP itself. A header field's
value, per the underlying transport rules, is restricted to a narrow band of characters;
raw UTF-8 bytes for "è", "û", "é" simply are not legal there. `encode_header_value` handles
this:

```python
def encode_header_value(value: str) -> str:
    if _HEADER_SAFE.fullmatch(value) and value == value.strip() and not _B64_SENTINEL.fullmatch(value):
        return value
    return f"=?base64?{base64.b64encode(value.encode('utf-8')).decode('ascii')}?="
```

Plain printable ASCII, with no leading or trailing whitespace, and not already shaped like
the sentinel itself, passes through completely unchanged. Anything else — non-ASCII,
control characters, edge whitespace, or a value that happens to already look like
`=?base64?...?=` — gets wrapped. Verified, side by side:

```text
encode_header_value("Latte")               -> "Latte"                                    (unchanged)
encode_header_value("Crème Brûlée Latte")   -> "=?base64?Q3LDqG1lIEJyw7tsw6llIExhdHRl?="   (wrapped)
```

`curl/13_announce.sh` computes this sentinel by hand, in plain Python, the exact way the
SDK does — not to reproduce the SDK's implementation, but so the encoding is never a black
box you take on faith. Run it with `'Latte'` and the header value printed is the name
itself; run it with `'Crème Brûlée Latte'` and you can watch the sentinel appear.

`decode_header_value` is the inverse, and it fails **closed**: malformed base64,
non-canonical base64 (bytes that re-encode to a different string than what was sent — a
sign of tampering or a buggy encoder), or bytes that are not valid UTF-8 all decode to
`None` rather than silently returning something wrong. A corrupted header is never allowed
to accidentally match a body value it was not actually equal to.

### The one gotcha this topic exists to warn about

`x-mcp-header` expects a string. Write `True` instead — an easy slip, since every other
boolean-flavoured schema key in this SDK (`readOnlyHint`, and so on) really is a boolean —
and here is what actually happens:

```python
find_invalid_x_mcp_header(input_schema) is not None:
    return None    # <- skip header validation for this tool ENTIRELY
```

Nothing rejects the schema. `tools/list` publishes `"x-mcp-header": true` completely
unmodified — verified directly. But `validate_mcp_param_headers` opens with exactly the
check above: if the schema's `x-mcp-header` annotation is malformed in *any* way, header
validation for that **entire tool** is skipped, on the theory that a conforming client
would have noticed the malformed annotation and simply never emitted the header at all.

The practical consequence, verified as an automated test in this topic: a tool with
`x-mcp-header: True` accepts *any* `Mcp-Param-*` header, or none at all, with **no error,
no warning, and no behavioral difference whatsoever**. A gateway built to route on that
header sees a mechanism that looks wired up — the schema key is right there — and silently
never engages. There is nowhere this fails loudly. If you use `x-mcp-header`, assert on the
*published schema* in a test, the way `tests/test_wire_param_headers.py` does — do not
trust that writing the annotation correctly once means it stayed correct.

## Layer 3 — Dry-run: announcing the Crème Brûlée Latte

**Step 1.** A human, or a model relaying for one, wants the counter to announce the
seasonal drink. The tool's argument description says to use the exact display name, so the
caller reaches for `"Crème Brûlée Latte"`, not the slug `creme-brulee-latte`.

**Step 2.** The client checks: is this argument non-ASCII, or does it contain edge
whitespace, or does it already look like the sentinel? `"Crème Brûlée Latte"` contains `è`
and `û` and `é` — not ASCII at all. The header cannot carry it raw.

**Step 3.** The client computes the sentinel:

```text
utf-8 bytes of "Crème Brûlée Latte"  ->  base64  ->  "Q3LDqG1lIEJyw7tsw6llIExhdHRl"
wrapped                              ->  "=?base64?Q3LDqG1lIEJyw7tsw6llIExhdHRl?="
```

**Step 4.** The request goes out:

```text
Mcp-Param-DrinkName: =?base64?Q3LDqG1lIEJyw7tsw6llIExhdHRl?=

{"params": {"name": "announce_drink",
            "arguments": {"name": "Crème Brûlée Latte"},
            "_meta": {...}}}
```

**Step 5.** The SDK's inbound check decodes the header's sentinel back to
`"Crème Brûlée Latte"`, compares it byte-for-byte against `arguments.name`, finds them
equal, and only then does `announce_drink` actually run.

**Step 6.** A gateway sitting in front of the server, watching only headers, saw
`Mcp-Param-DrinkName: =?base64?...?=` go by and — if it cared to — could decode that one
header itself and know exactly which drink this call concerned, without ever touching the
JSON body at all.

**Step 7.** `announce_drink` matches the decoded name against the menu and replies:
`"Now serving: Crème Brûlée Latte!"`.

## Gotchas

**`x-mcp-header`'s value is a token string, never a boolean.** Getting this wrong produces
no error anywhere — the mechanism simply never engages for that tool. Assert on the
published schema in a test if you rely on this at all.

**Header and body must agree in both directions.** Present-but-different and
present-header-absent-argument both fail the same way as absent-header-present-argument;
there is no "optional" mode.

**Non-ASCII in a header is not merely discouraged — it is not legal HTTP.** The sentinel
is not the SDK being cautious; it is the only way the value can travel at all.

**A malformed sentinel decodes to `None`, not to garbage.** Fail-closed by design, so a
corrupted header can never accidentally pass a comparison it should have failed.

**The header check does not validate that the *value* is real.** It only checks that
header and body *agree*. `Mcp-Param-DrinkName: Unicorn Frappe` matching a body argument of
`"Unicorn Frappe"` passes the header check fine; the tool itself is what rejects a drink
that does not exist.

## Your turn

`solutions/t13_param_headers.py`, three TODOs. TODO 1 is the one to get exactly right —
write the annotation, then **check the published schema yourself** before assuming it
worked, the same discipline `tests/test_wire_param_headers.py` uses to catch the
silent-failure case.

Before running `curl/13_announce.sh 'Crème Brûlée Latte'`, predict what the
`Mcp-Param-DrinkName` header value will look like. If your prediction is the drink's name
in plain UTF-8, go back to the non-ASCII section — that value is not a legal header at all.

## Connection forward

Every topic so far has run a single instance, on its own, on port 3010. Topic 14 finally
puts three copies of the assembled café behind a real round-robin proxy and proves, for
real rather than by argument, that topics 06 through 08's tokens genuinely do not care
which instance answers a given request — and, just as concretely, that topic 11's
subscription leak is exactly as real across three processes as it was across two. It also
fixes it: swapping `InMemorySubscriptionBus` for a shared one, with zero changes to any
tool's own code.

Does this make sense? Want me to go deeper on any part — why the enforcement runs before
the tool rather than after, the exact reasoning behind failing closed on a malformed
sentinel, or how a real gateway would actually use these headers to route traffic?
