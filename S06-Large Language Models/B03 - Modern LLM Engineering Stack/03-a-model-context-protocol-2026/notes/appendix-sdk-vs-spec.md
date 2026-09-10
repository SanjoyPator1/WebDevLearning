# Appendix — Where mcp 2.1.1 and the Spec Disagree

## Table of contents

- [Why this file exists](#why-this-file-exists)
- [Genuine SDK deviations from the spec](#genuine-sdk-deviations-from-the-spec)
  - [`GET /mcp` does not return 405](#get-mcp-does-not-return-405)
  - [`resources.subscribe: true` is still advertised](#resourcessubscribe-true-is-still-advertised)
  - [`elicitationId` still exists on URL-mode elicitation params](#elicitationid-still-exists-on-url-mode-elicitation-params)
  - [A prompt's argument-validation failure is an opaque `-32603`](#a-prompts-argument-validation-failure-is-an-opaque--32603)
  - [`extensions` is omitted rather than emitted empty](#extensions-is-omitted-rather-than-emitted-empty)
- [Places where circulating advice about 2026-07-28 is wrong](#places-where-circulating-advice-about-2026-07-28-is-wrong)
  - ["The SDK accepts a header/body mismatch"](#the-sdk-accepts-a-headerbody-mismatch)
  - ["Sending an older protocol version returns `-32022`"](#sending-an-older-protocol-version-returns--32022)
  - ["You must HMAC-sign `requestState` yourself" — and "the SDK doesn't bind it to the request"](#you-must-hmac-sign-requeststate-yourself-and-the-sdk-doesnt-bind-it-to-the-request)
  - ["`InputRequests` and `InputRequest` are RootModel wrappers you must construct"](#inputrequests-and-inputrequest-are-rootmodel-wrappers-you-must-construct)
  - ["`ctx.input_responses` is an `InputResponses` RootModel — use `.root[key].root`"](#ctxinput_responses-is-an-inputresponses-rootmodel-use-rootkeyroot)
  - ["`RequestedSchema` is exported from `mcp_types`"](#requestedschema-is-exported-from-mcp_types)
  - ["`x-mcp-header: True` marks a parameter for header mirroring"](#x-mcp-header-true-marks-a-parameter-for-header-mirroring)
  - ["You must declare `InputRequiredResult` in a tool's return annotation"](#you-must-declare-inputrequiredresult-in-a-tools-return-annotation)
  - [`RequestedSchema`'s top-level-only restriction is not enforced](#requestedschemas-top-level-only-restriction-is-not-enforced)
  - [A `Union` return type wraps under a synthetic `"result"` key in `outputSchema`](#a-union-return-type-wraps-under-a-synthetic-result-key-in-outputschema)
  - ["The `subscriptions/listen` ack tells you which filters the server actually supports"](#the-subscriptionslisten-ack-tells-you-which-filters-the-server-actually-supports)
  - ["`httpx` arrives transitively with the SDK"](#httpx-arrives-transitively-with-the-sdk)
- [A base64 gotcha this project's own tests tripped over](#a-base64-gotcha-this-projects-own-tests-tripped-over)
- [Things the SDK gets right that look wrong](#things-the-sdk-gets-right-that-look-wrong)
- [`mcp.client.Client` drives MRTR for you — given a callback (topic 15)](#mcpclientclient-drives-mrtr-for-you-given-a-callback-topic-15)


## Why this file exists

Every fact in this folder was checked against the installed packages by running a server
and posting to it, not by reading documentation. That process turned up a set of places
where the SDK's behaviour and the specification's prose do not match, plus a set of places
where widely-circulated advice about MCP 2026-07-28 is simply wrong.

Both are worth writing down, because both will cost you time otherwise.

Verified against: `mcp` 2.1.1, `mcp-types` 2.1.1, `httpx2` 2.12.0, Python 3.12.

## Genuine SDK deviations from the spec

### `GET /mcp` does not return 405

**Spec:** a GET to the streamable-HTTP endpoint should be rejected with
`405 Method Not Allowed`. The old two-endpoint HTTP+SSE design used a long-lived GET for
server-to-client traffic, and that design is gone — `subscriptions/listen` replaced it
with a POST.

**mcp 2.1.1:** opens an SSE stream and holds it. Your `curl -N` hangs until it times out.

```text
$ curl -sS -m 4 -i http://127.0.0.1:3010/mcp -H 'Accept: text/event-stream'
HTTP/1.1 200 OK
content-type: text/event-stream
...
curl: (28) Operation timed out after 4005 milliseconds
```

Harmless, but it will waste ten minutes of your life if you meet it without warning.
It is SDK-level, not something your server did.

### `resources.subscribe: true` is still advertised

`server/discover` reports `"resources": {"listChanged": true, "subscribe": true}`, but
`resources/subscribe` and `resources/unsubscribe` were **removed** at 2026-07-28 —
`subscriptions/listen` replaced them. The capability flag is a leftover. Do not read it as
permission to send `resources/subscribe` — verified:

```text
resources/subscribe  ->  -32601  "Method not found"  data: "resources/subscribe"
```

(Curiously the HTTP status on that one is 404 rather than 200, unlike other `-32601`
replies. The JSON-RPC error is what matters.)

### `elicitationId` still exists on URL-mode elicitation params

The spec removed `elicitationId` from URL-mode elicitation requests at this revision,
along with the `notifications/elicitation/complete` notification it correlated with. Under
MRTR the client learns the outcome by retrying, so a server-initiated completion signal
no longer fits.

`mcp_types.ElicitRequestURLParams` still has the field:

```text
elicitation_id: alias=elicitationId  required=False  type=str | None
```

It is optional, so ignoring it is correct. Correlate across retries by putting your own
identifier in `requestState` instead. (Topic 09.)

### A prompt's argument-validation failure is an opaque `-32603`

Found while building topic 05. `MCPServer.get_prompt` re-raises only `MCPError`; everything
else is flattened:

```python
except MCPError:
    raise
except Exception as e:
    raise ValueError(str(e)) from e     # -> -32603 "Internal server error"
```

That `except Exception` also catches **pydantic argument validation**, so a bad `Literal`
or a missing required argument on a prompt produces:

```text
prompts/get p {"budget": "nonsense"}   ->  -32603  "Internal server error"
prompts/get p {}   (missing required)  ->  -32603  "Internal server error"
```

Compare a *tool*, where the identical pydantic failure comes back in full detail. Tools and
resources each have a dedicated exception type that discloses (`ToolError`,
`ResourceError` / `ResourceNotFoundError`); prompts have none, and their default is the
worst of the three. Validate prompt arguments yourself and raise
`MCPError(code=INVALID_PARAMS, ...)`, which is the one thing that gets through intact.

The symptom is worth recognising: "Internal server error" with no detail sends you looking
for a crash that is not there.

### `extensions` is omitted rather than emitted empty

The spec adds an `extensions` field to `ClientCapabilities` and `ServerCapabilities` — the
slot where `io.modelcontextprotocol/tasks` and similar would be advertised. mcp 2.1.1 omits
the key entirely when there are none, rather than sending `{}`.

So absence means "no extensions", not "does not understand extensions". A client that
requires the key to be present will misread every 2.1.1 server.

## Places where circulating advice about 2026-07-28 is wrong

These are worth listing separately, because several of them appear in otherwise-careful
write-ups and one of them is a security-relevant misunderstanding.

### "The SDK accepts a header/body mismatch"

**False.** mcp 2.1.1 enforces all three routing headers, correctly, with `-32020`:

```text
Mcp-Method: tools/call  + body method tools/list
  -> -32020  "mcp-method header does not match the request body's method"

Mcp-Name: list_drinks   + params.name = get_drink
  -> -32020  "mcp-name header does not match the request body's 'name' parameter"

MCP-Protocol-Version: 2026-07-28  + _meta version 2025-06-18
  -> -32020  "mcp-protocol-version header does not match the request envelope's protocol version"
```

Missing `Mcp-Method` and *wrong* `Mcp-Method` produce the same message, which is
momentarily confusing — the SDK treats absent and mismatched identically. The headers are
required, not advisory.

### "Sending an older protocol version returns `-32022`"

**Only if the server has never heard of it.** A version the server *can* serve is served,
in that revision's shape, with no error at all:

```text
MCP-Protocol-Version: 2025-06-18  ->  HTTP 200, a 2025-11-25-shaped result
MCP-Protocol-Version: 2099-01-01  ->  -32022, with data.supported = ["2026-07-28"]
```

The SDK is dual-era on purpose. Your headers select which revision you get, and the
*result shape changes with it* — a legacy result has no `resultType`, no `ttlMs`, no
`cacheScope`, and no `_meta.serverInfo`. That last detail is the fastest way to tell which
era a response came from.

### "You must HMAC-sign `requestState` yourself" — and "the SDK doesn't bind it to the request"

**Both false, and the second one is a correction to an earlier draft of this very file.**
`MCPServer` takes a `request_state_security` argument, defaulting to a
`RequestStateSecurity` that uses AES-GCM with HKDF-derived keys, a TTL, and principal
binding. Return a plaintext string from a tool and watch the wire:

```python
return InputRequiredResult(
    result_type="input_required",
    input_requests={...},
    request_state=json.dumps({"order": order}),   # plaintext, on purpose
)
```

```text
on the wire:  "requestState": "v1._B9UYDKx5Tcsr9O-e7yOnhVVEBeL2CIxtFw6CvmoGSSe0P7pz..."
on the retry: ctx.request_state == '{"order": "latte"}'
```

Authenticated encryption, round-tripped for you. Rolling your own HMAC on top of that
would be redundant.

An earlier version of this file also claimed the SDK does **not** bind `requestState` to
the rest of the request — that a client could legitimately pair a valid `requestState`
from a small order with a much larger cart on the retry, and that you had to guard against
that yourself with your own arguments digest. **That claim was wrong**, and building topic
08 caught it: `MCPServer` installs a `RequestStateBoundary` middleware, on by default, in
front of every `input_required`-capable method (`tools/call`, `prompts/get`,
`resources/read`). It computes `(method, tool-name-or-uri, sha256(arguments))` at seal time
and re-verifies all three at unseal time, refusing any mismatch with
`-32602 "Invalid or expired requestState"` before your handler ever runs. Verified: a
retry carrying a completely different, validly-signed order token against a real
`requestState` from a different cart's round 1 is rejected outright, with no
`[server] place_order` line ever appearing in the server's own log — the tool body simply
never executes.

So: do not hand-roll an arguments-digest check. It already exists, automatically, for
every argument, with no code from you. What genuinely is left for `requestState` to carry
is anything true at round 1 that is **not** an argument — a price quote that could drift
between rounds even though the order token itself cannot change. Topic 08 covers both the
correction and the real remaining use in full, including the wire proof.

### "`InputRequests` and `InputRequest` are RootModel wrappers you must construct"

**No.** `InputRequiredResult.input_requests` is annotated as a plain dict:

```python
dict[str, CreateMessageRequest | ListRootsRequest | ElicitRequest] | None
```

So this is what works:

```python
input_requests={
    "confirm": ElicitRequest(
        method="elicitation/create",
        params=ElicitRequestFormParams(message=..., mode="form", requested_schema={...}),
    )
}
```

Not `InputRequests({"confirm": InputRequest(ElicitRequest(...))})`. The wrapper types
exist in `mcp_types`, but the field does not want them.

### "`ctx.input_responses` is an `InputResponses` RootModel — use `.root[key].root`"

**No.** The property is *annotated* `InputResponses | None`, but what you actually receive
is a plain dict of already-unwrapped results:

```text
type(ctx.input_responses)          -> <class 'dict'>
hasattr(ctx.input_responses,'root')-> False
ctx.input_responses["confirm"]     -> ElicitResult(action='accept', content={...})
```

So the access is one hop, not three: `ctx.input_responses["confirm"].action`.

### "`RequestedSchema` is exported from `mcp_types`"

It is not. The name is `ElicitRequestedSchema`, and `requested_schema` on
`ElicitRequestFormParams` is typed `dict[str, Any]` anyway — a plain dict is what you
pass. (The nesting restriction is real: top-level primitive properties only.)

### "`x-mcp-header: True` marks a parameter for header mirroring"

**Wrong type — and the failure is silent, which is worse than an error.** The annotation
value is the **header token name**, a string:

```python
drink: Annotated[str, Field(json_schema_extra={"x-mcp-header": "Drink"})]
#                                                              ^^^^^^^ -> Mcp-Param-Drink
```

It must be an RFC 9110 token, must sit on an integer/string/boolean property reachable by
a pure `properties` chain, and must be case-insensitively unique across the whole schema.

Now the part that matters. I expected `True` to be rejected, because
`mcp.shared.inbound.find_invalid_x_mcp_header` produces exactly the message
`"x-mcp-header must be a string, not bool"`. It is not rejected. `tools/list` publishes the
annotation verbatim:

```json
"drink": {"title": "Drink", "type": "string", "x-mcp-header": true}
```

And `validate_mcp_param_headers` opens with this, whose docstring is worth quoting:

```python
# "A schema find_invalid_x_mcp_header rejects validates nothing:
#  conforming clients drop the tool and emit no headers."
if find_invalid_x_mcp_header(input_schema) is not None:
    return None
```

So an invalid annotation makes the server **skip header validation for that tool
entirely**, on the assumption that a conforming client will have dropped the tool rather
than call it. Nothing errors. Nothing warns. The `Mcp-Param-*` machinery simply never
engages, and a gateway you built to route on that header sees nothing to route on.

That is a real trap: the observable symptom of a typo here is "my header-based routing
mysteriously does nothing", with no error anywhere to lead you to the cause. If you use
`x-mcp-header`, assert on the published schema in a test. Topic 13 does.

### "You must declare `InputRequiredResult` in a tool's return annotation"

**No.** A widely-repeated claim, and it reads plausibly because the SDK genuinely does
reject one specific combination at registration time:

```python
if resolved_params and returns_input_required(fn):
    raise InvalidSignature(f"Tool {func_name!r} combines Resolve(...) parameters with an "
                            "InputRequiredResult return; ...")
```

But `returns_input_required` only matters when the tool *also* uses `Resolve(...)`-typed
parameters — a different, resolver-driven multi-round-trip mechanism this folder does not
use. Verified directly: a tool annotated `-> Done` (no `InputRequiredResult` arm anywhere
in its signature, no `Resolve()` parameters) that returns an actual
`InputRequiredResult` instance at runtime works exactly the same as one that declares it —
the check is an `isinstance(result, InputRequiredResult)` at call time, not a static
annotation check. Declare it anyway, for an accurate `outputSchema`; just do not treat its
absence as a bug in inherited code.

### `RequestedSchema`'s top-level-only restriction is not enforced

The spec restricts an elicitation's `requestedSchema` to top-level primitive properties —
no nested objects, so a confirmation form cannot ask for a structured sub-object. mcp
2.1.1 does not check this. A `requestedSchema` with a `"type": "object"` property nested
inside its `properties` is published to the wire completely unmodified — no rejection, no
warning, nothing. Following the restriction is entirely on you.

### A `Union` return type wraps under a synthetic `"result"` key in `outputSchema`

A tool returning `A | B` (two `BaseModel` variants) does not publish a bare top-level
`anyOf` — a tool's `outputSchema` must itself be a JSON Schema *object*, and a bare union
is not one. The SDK wraps it:

```json
{"type": "object", "required": ["result"],
 "properties": {"result": {"anyOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}]}}}
```

and `structuredContent` on the wire mirrors that wrapper: `{"result": {...}}`, not a flat
object. A single-model return type does not get this wrapper — only a genuine union does.
Easy to assume the two behave the same; they do not. (If the return type additionally
includes an `InputRequiredResult` arm, that arm is stripped from `outputSchema` entirely —
it is a protocol-level result shape, not part of the tool's own success contract.)

### "The `subscriptions/listen` ack tells you which filters the server actually supports"

**No — it is a truthy echo, not a capability negotiation.** `_honored_subset` (in
`mcp.server.subscriptions`) drops falsy flags (`promptsListChanged: false` never appears
in the ack at all) and passes every truthy flag and every requested URI straight through
**unconditionally**, including a URI naming a resource that does not exist. Verified: a
listen request naming `cafe://this-resource-does-not-exist` gets it echoed back in the ack
exactly like a real one. The SDK's own source is explicit about why: "whether an event
kind ever fires depends on what the server publishes, exactly as a subscription to a
nonexistent resource URI is honored and never fires." "Honored" means *the server will
tell you if this happens*, not *the server verified this can happen*. (Topic 11.)

### "`httpx` arrives transitively with the SDK"

It does, but under a **different name**. `mcp` 2.1.1 depends on `httpx2>=2.5.0` — httpx 2.x
is published as a new distribution, and the importable module is `httpx2`:

```python
import httpx2 as httpx
```

`import httpx` gets you httpx 0.x if something else happened to install it, or an
`ImportError` if not. Either way, not the library the SDK is using.

## A base64 gotcha this project's own tests tripped over

Not an SDK-vs-spec disagreement — a genuine encoding property that produced a real,
intermittent test failure while building topics 06-08, worth recording so nobody
rediscovers it the hard way.

**Flipping the LAST character of a base64url string does not always change the decoded
bytes.** A 32-byte HMAC-SHA256 signature is 256 bits; base64url needs 43 characters
(258 bits of capacity) to carry it, leaving 2 bits of the final character unused —
canonically zero, but never checked on decode. Concretely:

```python
sig = hashlib.sha256(b"anything").digest()          # 32 bytes
b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")   # 43 chars, last char has 2 spare bits

# Of the 64 possible characters for that LAST position, how many decode to
# byte-IDENTICAL data as the original?
same_count = sum(
    1 for c in ALPHABET
    if base64.urlsafe_b64decode(pad(b64[:-1] + c)) == sig
)
# same_count == 4    (exactly 2**2, matching the 2 spare bits)
```

Four of 64 possible replacement characters (6.25%) leave the decoded bytes unchanged. A
test that tampers a token by replacing its last character with a fixed value (`"x"` unless
already `"x"`, then `"y"`) therefore has roughly a 1-in-16 chance of producing a
byte-identical token — no tampering occurred at all, and an assertion expecting rejection
fails with "DID NOT RAISE". This is exactly what happened: three tests across
`test_tokens.py`, `test_wire_order_token.py` and two curl scripts used this pattern, and
the full test suite flaked at roughly the predicted rate over dozens of runs before the
cause was tracked down.

**The fix**: tamper a character that is never subject to this slack — the first character
of the signature segment, not the last character of the whole token. The first character
of any base64 group is always fully significant regardless of how the total byte count
divides by 3; only trailing characters near the very end of a non-multiple-of-3 payload
can have unused bits. `token.split(".", 2)` to isolate the signature, flip
`sig_b64[0]`, rejoin — unconditionally reliable, verified across dozens of repeated runs
with zero further flakes.

The broader lesson: when writing a test (or a demo script) that "tampers" encoded data by
mutating a character, know *which* character positions in that encoding are guaranteed
significant. The end of a base64 string is the one place that is not automatically safe.

## Things the SDK gets right that look wrong

Worth listing so you do not "fix" them.

**An unknown tool name is a result with `isError: true`, not `-32601`.** The spec's prose
reads like a protocol error. The SDK's choice is better: the model asked for a tool that
does not exist, and only the model can fix that by re-reading `tools/list` — so the
failure belongs where the model will see it. (Topic 03.)

**A bare exception's message is withheld from the model.** Full traceback to stderr,
`"Error executing tool <name>"` to the model. This is a disclosure boundary, not
unhelpfulness. `ToolError` is how you assert a particular message is safe. (Topic 03.)

**A failing resource read is a JSON-RPC `error` while a failing tool call is not.** It looks
inconsistent and is not: a tool argument was chosen by the model (which can fix it, so the
failure goes in `result`), a resource URI was chosen by the client (which can fix it, so the
failure goes in `error`). Verified both ways in `tests/test_wire_resources_prompts.py`.

**`stateless_http` defaults to `False`.** Annoying, arguably wrong for a stateless
protocol, but it is what preserves compatibility with pre-2026 clients that still expect
sessions. You must opt in. (Topic 01.)

**`request_state_security` binds automatically; you cannot opt out of it per-tool.** Every
`MCPServer` installs it for every `input_required`-capable method. If you ever need two
tools' confirmation flows to be interchangeable (unusual, and probably a design smell),
that is not something this middleware will let you do quietly.

**`input_required` is legal only from `tools/call`, `resources/read` and `prompts/get`.**
Derived from `INPUT_REQUIRED_METHODS` in `mcp_types.methods`. A paginated *resource* may
ask a question; a `custom_route` may not, because it is not an MCP method at all.

## `mcp.client.Client` drives MRTR for you — given a callback (topic 15)

Every earlier topic's tests drove `input_required` by hand: read `requestState` out of
round 1's result, resend the unchanged argument, build `inputResponses` in the exact wire
shape, as a genuinely separate JSON-RPC request. `mcp.client.Client.call_tool(...)` does
not require any of that from a caller — given an `elicitation_callback` (a coroutine
matching `ElicitationFnT`: `(context, params) -> ElicitResult | ErrorData`), it drives
BOTH rounds internally and returns the final, committed result from one `await`. Verified
directly against `cafe_project.py`'s `place_order`: `input_required`, `requestState`, and
the round-2 retry never appear in caller code at all when a callback is supplied.

Without a callback, `call_tool` raises `mcp.shared.exceptions.MCPError: Elicitation not
supported` the instant a tool returns `input_required` — there is no silent default
accept, and no way to get the bare `InputRequiredResult` back through `call_tool` itself
(that is exactly what `tests/wire.py`'s raw `rpc()`/`call_tool()` helpers are for). The
driver is also bounded: `input_required_max_rounds` (default 10) — not exercised directly
in this project, since nothing here asks more than once, but real if a tool kept asking
forever (`InputRequiredRoundsExceededError`).

**`progress_callback` must be a coroutine function, not a plain `def`.** `ProgressFnT` is
awaited internally by the SDK's dispatcher, inside a shield (`_shielded_progress`) that
logs rather than raises on failure. Pass a plain `def` and it still gets CALLED correctly
— your prints fire, in order, with the right values — but its `None` return value then
fails to `await`, logging `"progress callback raised" ... TypeError: object NoneType
can't be used in 'await' expression"` once per event, while the visible output still looks
completely correct. Caught by deliberately reproducing it while building
`solved/sdk_client.py`, then fixing the callback to `async def` and reverifying zero
traceback noise. A genuinely silent-looking mistake — the callback *works*, only the
await around it fails, logged rather than raised.
