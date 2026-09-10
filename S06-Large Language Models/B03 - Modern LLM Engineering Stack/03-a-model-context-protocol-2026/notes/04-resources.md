# Resources and Resource Templates

## Table of contents

- [One sentence](#one-sentence)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [A static resource](#a-static-resource)
  - [`resources/read`](#resourcesread)
  - [Resource templates](#resource-templates)
  - [Cache hints, where they finally earn their keep](#cache-hints-where-they-finally-earn-their-keep)
  - [Failure: the rule is the *opposite* of topic 03](#failure-the-rule-is-the-opposite-of-topic-03)
  - [The disclosure boundary applies here too](#the-disclosure-boundary-applies-here-too)
- [Layer 3 — Dry-run: reading `cafe://drinks/flat-white`](#layer-3-dry-run-reading-cafedrinksflat-white)
- [Design notes worth stealing](#design-notes-worth-stealing)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)


## One sentence

A resource is a document your server publishes at a URI, which the **host or the user**
attaches to the model's context — as opposed to a tool, which the **model** decides to
call.

## The problem this topic solves

The café already has `list_drinks`. It returns the whole menu. So why publish the same
menu again as `cafe://menu`?

Three reasons, and the third is the real one.

**Cost.** `list_drinks` returns twelve pydantic objects rendered as JSON. `cafe://menu`
returns a markdown table containing the same facts in roughly a third of the tokens. When
something is going to sit in context for a whole conversation, that ratio matters.

**Repetition.** A model with a tool will call it again. And again — three turns later it
has forgotten and calls it a fourth time, and you have paid four times for information
that never changed. A document read once and pinned to context is read once.

**Control.** This is the one that actually explains why resources exist as a separate
primitive. A tool is something you *offer to the model's judgement*. A resource is
something the *host puts in front of it*. Those are different powers, held by different
parties, and collapsing them into one mechanism would mean giving up the distinction.

## Layer 1 — The intuition

Back to the counter and the temp.

The **tool** is the phone on the wall. You have told them: *if you need to know something
about a drink, you may ring the kitchen.* Whether to ring, and when, is their call. You
gave them a capability and trusted their judgement about using it.

The **resource** is the laminated menu you taped to the counter before you left. They did
not choose to have it. You decided it should be in front of them, and it is, permanently,
whether they look at it or not.

The **prompt** — topic 05 — is the third case: a card in a drawer labelled "if a customer
asks for a recommendation, read this out". The temp does not use it on their own
initiative, and you did not tape it up. The *customer* triggers it.

```text
   tool      →  the MODEL decides to use it        "you may ring the kitchen"
   resource  →  the HOST or USER attaches it       "this menu is taped to the counter"
   prompt    →  the USER invokes it                "customer asked? read this card"
```

If you can place a new feature in that table, you know which primitive it is. Most
uncertainty about "should this be a tool or a resource?" is really uncertainty about who
you want holding the decision.

## Layer 2 — The mechanics

### A static resource

```python
@mcp.resource(
    "cafe://menu",
    name="menu",
    title="The café menu",
    mime_type="text/markdown",
)
def menu_document() -> str:
    """The full menu as a markdown table: every drink, its slug, its price per
    size, its caffeine content and whether it is dairy-free.

    Read this once at the start of a conversation. ...
    """
    return render.menu_markdown()
```

A URI with no `{placeholder}` is a static resource. It appears in `resources/list`:

```json
{
  "uri": "cafe://menu",
  "name": "menu",
  "title": "The café menu",
  "mimeType": "text/markdown",
  "description": "The full menu as a markdown table: every drink, its slug, ..."
}
```

Four fields worth attention:

**`uri`** — the address. The scheme is yours to invent; `cafe://` is not registered
anywhere and does not need to be. Pick a scheme that names your server, then a path that
makes the hierarchy obvious. `cafe://menu` and `cafe://menu/dairy-free` read as related,
which is a hint to a human browsing them and costs nothing.

**`name`** vs **`title`** — same split as tools. `name` is the machine identifier,
`title` is what a host shows in a "attach a resource" picker for a human to click.

**`mimeType`** — how the client should treat the bytes. `text/markdown` is a strong
default for anything a model will read: models handle markdown structure well, and a host
can also render it for a person. Use `application/json` when the consumer is code, as the
café does for single drinks.

**`description`** — the docstring, again, verbatim. Same rule as topic 02: this is prompt
text. But the question it should answer is different. A tool description answers *when
should I call this?* A resource description answers *when should this be in my context?*

### `resources/read`

```json
{
  "resultType": "complete",
  "contents": [
    {
      "uri": "cafe://menu",
      "mimeType": "text/markdown",
      "text": "# The Café Menu\n\nPrices in dollars. A dash means that size is not sold.\n\n| Drink | Slug | S | M | L | ..."
    }
  ],
  "ttlMs": 600000,
  "cacheScope": "public"
}
```

`contents` is a **list**, which surprises people who expect one document per URI. One URI
may legitimately return several pieces — a directory-ish resource returning each file, or
a record plus its attachments. Each entry carries its own `uri` and `mimeType`, so a
single read can mix markdown and JSON.

Entries are either text (`text`) or binary (`blob`, base64-encoded). The café only ever
returns text.

### Resource templates

```python
@mcp.resource("cafe://drinks/{slug}", mime_type="application/json")
def drink_document(slug: str) -> str:
    ...
```

One `{placeholder}` changes two things, and both catch people.

**It moves to a different RPC.** Templates appear in `resources/templates/list`, *not*
`resources/list`. A client that only calls `resources/list` will never learn the template
exists. Verified:

```text
resources/list            -> ["cafe://menu", "cafe://menu/dairy-free"]
resources/templates/list  -> ["cafe://drinks/{slug}"]
```

**The key changes name.** A template entry has `uriTemplate`, not `uri`:

```json
{
  "uriTemplate": "cafe://drinks/{slug}",
  "name": "drink_detail",
  "title": "One drink, in full",
  "mimeType": "application/json",
  "description": "The full record for a single drink as JSON, ..."
}
```

The placeholder becomes a function parameter. Reading `cafe://drinks/latte` calls
`drink_document(slug="latte")`, and the result's `contents[0].uri` is the **resolved**
URI, not the template:

```json
{"uri": "cafe://drinks/flat-white", "mimeType": "application/json", "text": "{\n  \"slug\": \"flat-white\", ..."}
```

Templates are how you expose a family of documents without enumerating it. Twelve drinks
would be perfectly fine to list individually; twelve thousand orders would not be, and
twelve million rows in a database certainly would not.

There is a gap here that is worth naming, because it motivates half of topic 05: nothing
in `resources/templates/list` tells you what values `{slug}` may take. The template says
the shape of the address and nothing about the address space. Filling that gap is exactly
what `completion/complete` is for.

### Cache hints, where they finally earn their keep

There are exactly six cacheable methods at this revision, and you should get the list from
the SDK rather than from prose:

```bash
python -c "from mcp_types.methods import CACHEABLE_METHODS as C; print(sorted(C))"
```

```text
['prompts/list', 'resources/list', 'resources/read',
 'resources/templates/list', 'server/discover', 'tools/list']
```

Notice what is **absent**: `tools/call` and `prompts/get`. Caching a tool call would mean
caching a side effect, which is incoherent. `prompts/get` renders against arguments and
may itself do work. Only the *descriptive* surface plus `resources/read` is cacheable.

`resources/read` being on that list is the interesting entry, and it is the highest-value
hint on this whole server:

```python
cache_hints={
    "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
    "resources/list": CacheHint(ttl_ms=600_000, scope="public"),
    "resources/templates/list": CacheHint(ttl_ms=600_000, scope="public"),
    "resources/read": CacheHint(ttl_ms=600_000, scope="public"),
}
```

A resource read is a **document fetch**. That is precisely the thing HTTP caching was
invented for, and the whole point of the 2026-07-28 statelessness work is that ordinary
HTTP infrastructure can now handle MCP traffic. Give a document a real TTL and a shared
proxy in front of three server instances serves the menu from memory. That is not a
micro-optimisation; it is the payoff of the architecture.

The `scope="public"` judgement is the same one as topic 02, and here it is *more* dangerous
because the payload is bigger and more interesting. `cafe://menu` is byte-identical for
every caller, so `"public"` is correct and useful. The instant you add
`cafe://orders/{id}`, that resource must be `"private"` — a shared cache serving one
customer's order to another is not a subtle failure. Cache scope is per-method, not
per-URI, so the moment any resource on a server is caller-dependent you must drop
`resources/read` to `"private"` for the whole server, or split the caller-dependent
documents onto a different server.

### Failure: the rule is the *opposite* of topic 03

This is the section to remember.

Topic 03 established that a failing **tool** returns a *successful* JSON-RPC response
whose result carries `isError: true`. A failing **resource read** does the opposite — a
genuine JSON-RPC `error`:

```text
resources/read  cafe://drinks/no-such-drink
  -> {"error": {"code": -32602,
                "message": "There is no drink with slug 'no-such-drink'. Read `cafe://menu` for the list of valid slugs.",
                "data": {"uri": "cafe://drinks/no-such-drink"}}}

tools/call      get_drink(slug="no-such-drink")
  -> {"result": {"isError": true,
                 "content": [{"type": "text",
                              "text": "Error executing tool get_drink: There is no drink with slug 'no-such-drink'. Call `list_drinks` first."}]}}
```

Same missing drink. Same server. Opposite envelopes. Run
`bash curl/04_tool_vs_resource.sh` to see them back to back.

This is not an inconsistency, and it is not the SDK being sloppy. Apply topic 03's test —
**who can fix this?**

```text
  A tool call was chosen by the MODEL.
    The model can choose differently next turn.
    So the failure must reach the model  ->  it goes in `result`, where the model looks.

  A resource URI was chosen by the CLIENT or the USER.
    The model was not involved and cannot fix it.
    It is the client's mistake  ->  it goes in `error`, where the client looks.
```

Same question, opposite answers, because a different party is holding the wheel. Once you
see it that way the two rules stop being two rules.

Note also the error code. `-32602 Invalid params` — not a bespoke code. Missing resources
used to be `-32002`, and were **renumbered to `-32602` at 2026-07-28** on the grounds that
a URI which does not exist is a bad argument, not a special condition. If you find code
checking for `-32002`, it is pre-August-2026.

### The disclosure boundary applies here too

Topic 03's rule — your exception message is withheld unless you assert it is safe — holds
for resources, with resource-shaped exception types. All three verified:

| You raise | Client sees |
|-----------|-------------|
| a bare exception | `-32603` `"Error reading resource cafe://x"` — **message withheld** |
| `ResourceError("upstream menu service is down; try again shortly")` | `-32603` with **your message** |
| `ResourceNotFoundError("There is no drink with slug 'x'. ...")` | `-32602` with **your message** |

So the mapping is clean:

```text
  TOOLS                          RESOURCES
  ─────                          ─────────
  bare exception  -> withheld    bare exception          -> withheld
  ToolError       -> forwarded   ResourceError           -> forwarded, -32603
                                 ResourceNotFoundError   -> forwarded, -32602
```

Which is why `render.drink_json` raises a plain `KeyError` and the *resource layer*
converts it. The domain module should not know which envelope its caller lives in. Keep the
conversion at the boundary, where you know both the failure and the audience.

## Layer 3 — Dry-run: reading `cafe://drinks/flat-white`

**Step 1.** The client wants one drink's detail. It has called
`resources/templates/list` at some point and knows the shape `cafe://drinks/{slug}`. It
has a slug from having read `cafe://menu`, where the Slug column showed `` `flat-white` ``.

**Step 2.** It substitutes: `cafe://drinks/flat-white`.

**Step 3.** It builds the POST. `resources/read` is a name-bearing method, and for *this*
method the mirrored value is `params.uri`, not `params.name`:

```text
tools/call     -> Mcp-Name mirrors params.name
prompts/get    -> Mcp-Name mirrors params.name
resources/read -> Mcp-Name mirrors params.uri     <-- this one
```

```bash
curl -sS http://127.0.0.1:3010/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: resources/read' \
  -H 'Mcp-Name: cafe://drinks/flat-white' \
  -d '{"jsonrpc":"2.0","id":205,"method":"resources/read",
       "params":{"uri":"cafe://drinks/flat-white",
                 "_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28",
                          "io.modelcontextprotocol/clientCapabilities":{}}}}'
```

**Step 4.** The server matches the URI against its registered patterns. `cafe://menu`? No.
`cafe://menu/dairy-free`? No. `cafe://drinks/{slug}`? Yes, with `slug="flat-white"`.

If nothing matched, we would stop here with `-32602 "Unknown resource: cafe://..."` — and
note that this comes from the *SDK*, before your function runs, so its wording is the
SDK's, not yours.

**Step 5.** `drink_document(slug="flat-white")` runs. It calls
`render.drink_json("flat-white")`, which finds the drink, dumps the model, adds
`available_sizes`, and returns a JSON string.

**Step 6.** The SDK wraps it:

```json
{"jsonrpc": "2.0", "id": 205,
 "result": {"resultType": "complete",
            "contents": [{"uri": "cafe://drinks/flat-white",
                          "mimeType": "application/json",
                          "text": "{\n  \"slug\": \"flat-white\",\n  \"name\": \"Flat White\",\n  ...\n  \"available_sizes\": [\n    \"S\",\n    \"M\",\n    \"L\"\n  ]\n}\n"}],
            "ttlMs": 600000, "cacheScope": "public",
            "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "cafe-mcp", "version": "0.4.0"}}}}
```

**Step 7.** The client caches it for ten minutes and attaches the text to context.

Now replay with `slug="no-such-drink"`. Step 4 still matches the template — the pattern
does not know which slugs are real. Step 5 gets a `KeyError` from `render.drink_json`, and
the resource layer converts it to `ResourceNotFoundError`. Step 6 becomes an `error`
envelope with `-32602` and the message intact, plus `data.uri` naming the URI that failed.

The lesson in that replay: **a template matching is not a template resolving.** The URI
space a template describes is always larger than the set of documents that exist, so every
template resource needs a not-found path.

## Design notes worth stealing

Two choices in `render.py` that are about the reader, not the code.

**The slug is in the menu table, in backticks.** A model that has read `cafe://menu` and
now wants one drink already holds the exact argument. Without that column it would have to
guess `flat-white` from "Flat White", or spend a turn on `list_drinks`. One column removes
a whole failure mode.

**An unavailable size is a dash, not a blank.** Blank cells read as *unknown*; a dash
reads as *not sold*. The header even says so: "A dash means that size is not sold." When
you are writing for a model, absence is the most easily misread thing you can put on a
page — so mark it explicitly.

## Gotchas

**Templates are in a different RPC.** `resources/templates/list`, with `uriTemplate`
instead of `uri`. A client that calls only `resources/list` sees nothing.

**`contents` is a list.** Even for one document.

**A failing resource read is a JSON-RPC `error`, not `isError`.** Opposite of tools, for a
reason.

**Missing resource is `-32602`, not `-32002`.** Renumbered at this revision.

**`Mcp-Name` mirrors `params.uri` for `resources/read`,** not `params.name`.

**A bare exception's message is withheld here too.** Use `ResourceNotFoundError` or
`ResourceError` to disclose.

**Cache scope is per-method, not per-URI.** One caller-dependent resource forces
`resources/read` to `"private"` for the entire server.

**A template matching is not a template resolving.** Always write the not-found path.

**Resource docstrings answer a different question from tool docstrings.** "When should this
be in my context?", not "when should I call this?"

## Your turn

`solutions/t04_resources.py`, six TODOs.

TODO 5 is the one that matters, and it is a writing exercise as much as a coding one:
convert the `KeyError` to the right exception, then **write the comment explaining why
`ToolError` is correct for `get_drink` and wrong here**. If you can write that paragraph,
you have topics 03 and 04 as one idea instead of two rules.

For TODO 1, find the cacheable-methods list from the SDK yourself, and be able to say why
`tools/call` is not on it.

## Connection forward

Topic 05 finishes Part 2 and, with it, the whole protocol surface — the last two of the
ten methods.

**Prompts** are the third control case from that table: templates the *user* invokes,
which usually surface in a host as slash commands. And **`completion/complete`** closes the
gap this chapter opened: it is how a client discovers that `{slug}` in
`cafe://drinks/{slug}` can be `latte`, `espresso` or `flat-white` — argument autocomplete
for both prompt arguments and template placeholders, from one small handler.

After that, Part 3 is where the revision gets genuinely interesting: the café learns to
remember an order without remembering anything.

Does this make sense? Want me to go deeper on any part — the tool/resource/prompt control
split, why the failure rules are opposites, or how cache scope interacts with
multi-tenancy?
