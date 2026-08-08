# Chapter 2: The Agent Loop from Scratch

## Table of Contents

1. [Why This Chapter Exists](#1-why-this-chapter-exists)
2. [The Message List Is the State](#2-the-message-list-is-the-state)
3. [Anatomy of One Turn](#3-anatomy-of-one-turn)
4. [Writing the Dispatch Table](#4-writing-the-dispatch-table)
5. [Termination Conditions](#5-termination-conditions)
6. [Error Handling Inside the Loop](#6-error-handling-inside-the-loop)
7. [Parallel Tool Calls](#7-parallel-tool-calls)
8. [Streaming and Interleaved Thinking](#8-streaming-and-interleaved-thinking)
9. [Trajectory Logging](#9-trajectory-logging)
10. [The Same Loop, Three Surfaces](#10-the-same-loop-three-surfaces)
11. [Dry-Run: Hand-Tracing a 4-Step Loop](#11-dry-run-hand-tracing-a-4-step-loop)
12. [What the Loop Cannot Do Yet](#12-what-the-loop-cannot-do-yet)
13. [Key Takeaways + Master Decision Table](#13-key-takeaways--master-decision-table)

---

# 1: Why This Chapter Exists

## What This Chapter Is Really About

Chapter 1 gave you the vocabulary — Model + Harness, the three eras, the stack
map — but it never actually built anything. Every diagram in that chapter had
a box labeled "the loop" with nothing inside it. This chapter opens that box.

By the end, you will have written a real, working agent in one Python file,
maybe 200 lines, with no framework underneath it — just a `while` loop, a
list of messages, and a small dictionary mapping tool names to Python
functions. That is not a toy simplification of what LangGraph or the Claude
Agent SDK do internally; it is *structurally identical* to what they do
internally. Every chapter after this one — memory, verification, permissions,
persistence — is something you will bolt onto this exact loop. If you don't
own this file, you will spend the rest of the folder trusting a framework to
do something you can't picture, which makes every later bug a guessing game.

*Everything below is demonstrated against Anthropic's Messages API directly —
the raw wire format — because tool_use blocks, stop_reason values, and
tool_result matching are the actual mechanics being taught, not an
implementation detail to abstract away yet. But the loop itself — think, act,
observe, in a growing message list — is not an Anthropic idea. It's how every
current tool-calling model works, Gemini and the Bedrock-hosted Claude models
included. The next subsection gives you the vocabulary to translate what
follows onto whichever backend `ai_config` happens to be pointed at.*

## One Loop, Three Vocabularies

Chapter 1's shared `ai_config` module already lets a notebook pick
`'anthropic'`, `'gemini'`, or `'bedrock'` and get a connected client back. What
it does *not* yet do — and this is worth being honest about before going any
further — is normalize *tool calling* across the three. `ai_config.generate()`
today takes a `prompt` and an optional `system`; it has no `tools` parameter,
because the three providers express "the model wants to call a function" in
three genuinely different shapes, and collapsing those into one interface
without losing information is real design work, not a thin wrapper. That
work is worth doing eventually — precisely because everything in this chapter
is provider-agnostic in substance — but it isn't done yet, and pretending
otherwise here would just move the confusion from "which provider" to "why
doesn't this code run."

So this chapter teaches the loop using **Anthropic's wire format as the
reference implementation** (tool_use/tool_result blocks, `stop_reason`), the
way the roadmap always intended it — and gives you, right here, the
Rosetta Stone for reading the exact same concepts in Gemini's and Bedrock's
own vocabulary, so nothing below is Anthropic-only knowledge dressed up as
universal:

| Concept | Anthropic (Messages API) | Gemini (`google-genai`) | Bedrock (Converse API) |
|---|---|---|---|
| Conversation state | `messages: [...]` | `contents: [...]` | `messages: [...]` |
| The model's own turns | `role: "assistant"` | `role: "model"` | `role: "assistant"` |
| Human/tool-result turns | `role: "user"` | `role: "user"` | `role: "user"` |
| "Model wants to call a function" | a `tool_use` content block | a `Part` with `.function_call` (name, args, id) | a `toolUse` content block |
| "Here's what the function returned" | a `tool_result` content block, `tool_use_id`-matched | a `Part` with `.function_response`, name-matched | a `toolResult` content block, `toolUseId`-matched |
| Why the model stopped | `stop_reason`: `end_turn`, `tool_use`, `max_tokens`, `stop_sequence`, `pause_turn`, `refusal` | `finish_reason`: `STOP`, `MAX_TOKENS`, `SAFETY`, and others | `stopReason`: `end_turn`, `tool_use`, `max_tokens`, `stop_sequence`, `content_filtered`, `guardrail_intervened` |
| Multiple tools requested at once | several `tool_use` blocks in one assistant turn | several `function_call` parts in one turn | several `toolUse` blocks in one assistant turn |

Read that table once, then forget the middle two columns and read the rest
of this chapter in Anthropic's terms — the loop logic (Sections 3, 5, 6, 7)
is written generically enough that "swap the column" is the entire porting
exercise once `ai_config` grows a `tools` parameter. Anywhere this chapter
leans on a mechanic that is genuinely Anthropic-only (not just
differently-named, but structurally absent elsewhere — interleaved thinking,
the `refusal` stop reason, the Tool Runner), it's called out explicitly in an
**Anthropic-specific** note, so you always know which parts of your mental
model travel and which don't.

> **A note on which real Claude these Anthropic-specific demos will actually
> call.** When a later notebook needs to *run* one of the Anthropic-only
> mechanics named above — not just read about it — it does so through
> `ai_config.get_anthropic_reference_provider()`, not
> `ai_config.get_provider('anthropic')`. That helper resolves to Claude
> Sonnet **via AWS Bedrock**, because this project's real, funded path to
> Claude is Bedrock, not a separate Anthropic Console key (a Claude Pro/Team
> chat subscription doesn't carry API credit — see Chapter 1). Every time
> this chapter marks something "Anthropic-specific," that's the concrete
> reason the corresponding code reaches for Bedrock specifically rather than
> whatever `SELECTED_PROVIDER` the rest of the notebook is using.

---

# 2: The Message List Is the State

## The Intuition

Think of the message list like a **shared notebook passed back and forth
across a table**. The user writes a question. The model writes back — maybe
just an answer, maybe "hold on, let me check something" followed by a request
to flip to page 12 of a reference book. Whoever is holding the notebook next
writes the answer they found on page 12 into the notebook themselves, then
slides it back. The model never remembers anything between turns except
*what's physically written in the notebook* — there is no side channel, no
hidden memory, no session on the server holding context for you. The entire
state of the conversation, at every point, is the literal list of messages
you have accumulated and will send again, in full, on the next call.

This is the single fact that makes everything else in this chapter make
sense: **the API is stateless.** Every single request carries the *entire*
transcript from the beginning. If you don't append something to the list, the
model has no way of knowing it happened.

## What Actually Sits in the List

```python
messages = [
    {"role": "user", "content": "How many words are in report.txt?"},
    # ... the loop appends here, turn by turn, and never removes anything (yet)
]
```

Two roles alternate: `user` (which carries both real human input *and* tool
results — this surprises people the first time) and `assistant` (the model's
own turns, which carry both text *and* tool-call requests). A `role: "system"`
message can also appear mid-conversation on some models as a distinct
operator-authority channel, but the two workhorse roles for this chapter are
`user` and `assistant`.

## Why This Representation Is Both the Great Simplification and the Root Cause of Context Rot

The append-only message list is what makes the whole agent loop concept
tractable to reason about: state is just data, not some opaque object living
on a server you can't inspect. You can print it, save it to disk, replay it,
diff two versions of it. That simplicity is a genuine gift.

But notice what it costs: **every single API call re-sends the entire
history from the beginning.** Turn 1 costs you the system prompt and one user
message. Turn 15 costs you the system prompt, the tool schemas, and
*everything that happened in turns 1 through 14* — all of it, every time,
because nothing was ever removed. This is exactly the arithmetic Chapter 1's
Section 11 walked through by hand (the 15-step run that processed over
160,000 prefill tokens) — and now you can see precisely *why* the growth
happens: it isn't a bug, it's the direct, unavoidable consequence of state
being "the whole list, resent in full." Chapter 4 exists specifically to
manage this growth (compaction, eviction, externalization); this chapter is
about accepting it as the baseline and building the loop that produces it
correctly.

## Key Takeaways for Section 2

The API is stateless — the message list *is* the conversation, not a
reference to one. Two roles alternate (`user`, `assistant`), and `user`
carries both human input and tool results. Because the whole list resends on
every call, the loop's history only ever grows unless something later
actively shrinks it — which is precisely the context-rot mechanism from
Chapter 1, now seen from the code side instead of the arithmetic side.

*Next: what actually happens during one pass through the loop, step by step.*

---

# 3: Anatomy of One Turn

## The Cycle, Precisely

```
                    ┌─────────────────────────────────────────────┐
                    │                                              │
                    ▼                                              │
        ┌───────────────────┐                                     │
        │  Send full message │   POST /v1/messages                │
        │  list + tools to    │──────────────────────┐             │
        │  the model          │                       ▼             │
        └───────────────────┘             ┌───────────────────┐   │
                                            │  Read stop_reason  │   │
                                            └─────────┬─────────┘   │
                              ┌───────────────────────┼──────────┐  │
                              ▼                       ▼          ▼  │
                    stop_reason ==            stop_reason ==   other│
                    "tool_use"                "end_turn"      (max_tokens,  │
                              │                       │        refusal, …)  │
                              ▼                       ▼               │
                  ┌───────────────────┐    ┌───────────────────┐     │
                  │ Append assistant   │    │  Done. Return the  │     │
                  │ turn to messages   │    │  final text.        │     │
                  │ (BEFORE executing  │    └───────────────────┘     │
                  │  anything)         │                              │
                  └─────────┬─────────┘                              │
                            ▼                                        │
                  ┌───────────────────┐                              │
                  │ Execute every       │                              │
                  │ tool_use block      │                              │
                  └─────────┬─────────┘                              │
                            ▼                                        │
                  ┌───────────────────┐                              │
                  │ Append ALL results  │                              │
                  │ as ONE user turn    │──────────────────────────────┘
                  └───────────────────┘        loop back to top
```

## Reading `stop_reason` Correctly

Every response carries a `stop_reason` field, and the entire branching logic
of an agent loop is a switch on this one value:

| `stop_reason` | What it means | What the loop does |
|---|---|---|
| `end_turn` | The model finished its answer naturally | Exit the loop, return the text |
| `tool_use` | The model wants to call one or more tools | Execute them, append results, loop again |
| `max_tokens` | Hit the output token cap mid-generation | Retry with a higher cap, or treat as a failure — never silently accept a truncated answer |
| `stop_sequence` | Hit a configured stop string | Usually treated like `end_turn` for your use case |
| `pause_turn` | A server-side tool (like web search) hit its internal iteration limit and can be resumed | Re-send the *same* request unchanged — the server picks up where it left off; do **not** append an extra "continue" message |
| `refusal` | Safety classifiers declined the request | This is a normal HTTP 200, not an exception — check `stop_reason` before touching `content`, because `content` may be empty |

> **Provider note.** `end_turn` / `tool_use` / `max_tokens` / `stop_sequence`
> carry across almost unchanged — Gemini calls the first one `STOP` and
> nests it under `finish_reason` instead of `stop_reason`, Bedrock's Converse
> API keeps the exact same five names under `stopReason`. Two rows are
> **Anthropic-specific** and worth knowing that up front: `pause_turn` (a
> resumable pause specific to Anthropic's server-side tools like web search)
> and `refusal` as its own distinct value (Gemini folds a safety decline into
> `finish_reason: "SAFETY"`, Bedrock into `guardrail_intervened` or
> `content_filtered` — same idea, no dedicated "the model itself declined"
> signal). The lesson underneath all three vocabularies is identical either
> way: **never assume the loop only ever ends in exactly two ways.** Whatever
> field you're reading, enumerate every value it can take before you ship,
> not just the two you expect.

The single most common bug in a first agent loop is treating `content[0].text`
as always present. It is not, on two different `stop_reason` values: `tool_use`
(the useful content is a `tool_use` block, not text) and `refusal` (content can
be empty). **Always branch on `stop_reason` first; only reach into `content`
after you know what kind of turn you're holding.**

## The One Rule That Breaks the Most Loops

**Append the assistant's turn to `messages` *before* you execute any tool,
and always append the *full* `content` array — not just the text part.** The
assistant's message contains both a `text` block (its reasoning, if any) and
one or more `tool_use` blocks (the calls it wants made). If you only save the
text and throw away the `tool_use` blocks, or if you execute tools first and
forget to save the assistant turn at all, the next request you send is
missing the very thing the tool results are supposed to be *results of* — and
the API rejects it, because every `tool_result` must reference a `tool_use_id`
that actually appears earlier in the transcript.

```python
response = client.messages.create(model=MODEL, max_tokens=1024,
                                   tools=tools, messages=messages)

if response.stop_reason == "tool_use":
    messages.append({"role": "assistant", "content": response.content})  # FULL content, not just text
    # ... now, and only now, execute the tool_use blocks
```

## Key Takeaways for Section 3

One turn is: send the whole list → read `stop_reason` → branch → (if
`tool_use`) save the assistant turn in full, run the tools, append one user
turn with all the results → loop. Six `stop_reason` values exist and each
demands different handling; the two that trip people up are `tool_use`
(content isn't text) and `refusal` (content might be empty).

*Next: "run the tools" was doing a lot of work in that diagram — here's what
actually sits behind it.*

---

# 4: Writing the Dispatch Table

## The Intuition

Picture a **hotel concierge desk with a phone directory taped to the wall**.
A guest doesn't call housekeeping, room service, and the valet directly —
they tell the concierge what they need, and the concierge looks up the right
extension and places the call. The model plays the guest's role: it says "I
want `get_weather` called with `location: Paris`," and your code is the
concierge — it looks `get_weather` up in a directory (a plain dictionary),
finds the matching Python function, and calls it with the arguments the model
provided.

## The Table Itself

```python
def get_weather(location: str) -> str:
    """Look up the current weather for a city (stub — real impl would call an API)."""
    return f"72F and sunny in {location}"

def read_file(path: str) -> str:
    """Return the contents of a file at `path`."""
    with open(path) as f:
        return f.read()

TOOL_DISPATCH = {
    "get_weather": get_weather,
    "read_file": read_file,
}
```

The model never calls these functions directly — it can't, it has no
execution environment of its own. What it does is emit a `tool_use` content
block: `{"type": "tool_use", "id": "toolu_01abc", "name": "get_weather",
"input": {"location": "Paris"}}`. Your loop's entire job at this point is
mechanical: look `block.name` up in `TOOL_DISPATCH`, call the matching
function with `**block.input`, and capture whatever comes back as a string.

```python
def execute_tool_call(block):
    fn = TOOL_DISPATCH.get(block.name)
    if fn is None:
        return f"Error: no such tool '{block.name}'", True   # (content, is_error)
    try:
        result = fn(**block.input)
        return str(result), False
    except Exception as exc:
        return f"Error: {exc}", True
```

## Definitions Are a User Interface Whose User Is a Model

The `name`, `description`, and `input_schema` you declare for each tool are
not documentation for a human reading your code later — they are the *entire*
information the model has about what a tool does and how to call it. A vague
description ("processes text") produces vague, wrong tool calls just as
reliably as a vague API doc produces confused human developers. This whole
subject — how to size tools, how to word descriptions, when one fat tool
beats five thin ones — is deep enough to earn its own chapter (Chapter 3);
for now, the working rule is simple: **describe not just what the tool does,
but *when to call it***, since models on the current generation reach for
tools more conservatively than earlier ones and respond measurably better to
an explicit trigger condition in the description than to a bare
capability statement.

## Key Takeaways for Section 4

A dispatch table is just a dictionary from tool name to Python callable — the
"agentic" part is entirely on the model's side (deciding *which* tool and
*what arguments*); your code's job is pure, boring routing. The tool
`description` field is a user interface for the model, and its wording is a
real design surface, not an afterthought.

*Next: a loop that never stops is not an agent, it's a bug — five separate
guards keep this one honest.*

---

# 5: Termination Conditions

## The Intuition

Think of this like **the five separate reasons a marathon official will pull
a runner off the course**: they crossed the finish line (success), they hit
the course's official cutoff time (budget), they've been standing at the same
aid station for twenty minutes not moving (no progress), a medic waved them
down (external stop), or the course itself measured out at double the
advertised distance and something is clearly wrong (a hard safety ceiling).
Only one of these is the *good* outcome; a race with just that one condition
and nothing else is a race with no way to stop a runner who is lost, hurt, or
looping the same half-mile forever.

## The Five Guards

| Guard | What it catches | Typical implementation |
|---|---|---|
| **Natural stop** | The model is genuinely done | `stop_reason == "end_turn"` |
| **Max-iteration guard** | The model never converges — keeps calling tools forever | `if step >= MAX_STEPS: break` |
| **Budget guard** | The run is technically making progress but is burning money unacceptably fast | Track cumulative `usage.input_tokens + usage.output_tokens`; stop past a dollar or token ceiling |
| **Wall-clock guard** | A single step (or the whole run) is taking pathologically long | `time.monotonic()` checked at the top of each iteration |
| **Explicit `finish` tool** | You want the model itself to signal "I'm confident this is complete" as a deliberate, checkable action rather than inferring it from `end_turn` | A tool literally named `finish` or `submit_answer` that the loop treats as terminal when called |

```python
MAX_STEPS = 20
MAX_TOKENS_BUDGET = 50_000
start_time = time.monotonic()

for step in range(MAX_STEPS):
    if time.monotonic() - start_time > 300:          # wall-clock guard
        break
    if cumulative_tokens > MAX_TOKENS_BUDGET:          # budget guard
        break

    response = client.messages.create(...)
    cumulative_tokens += response.usage.input_tokens + response.usage.output_tokens

    if response.stop_reason == "end_turn":             # natural stop
        break
    # ... handle tool_use, append, continue
else:
    # the for/else fires only if MAX_STEPS was exhausted without a `break`
    print("Hit max-iteration guard without a natural stop.")
```

## Why You Need All Five, Not Just One

Each guard catches a genuinely different failure mode, and they don't
substitute for each other. A max-iteration guard alone doesn't stop a loop
that's cheap-but-slow (one very expensive tool call per step, only 20 steps,
but each step takes four minutes). A budget guard alone doesn't stop a loop
that's fast-but-endless (thousands of cheap steps that never converge). A
wall-clock guard alone doesn't catch a loop that's fast in wall-clock terms
but silently expensive in tokens because each step's context has grown huge.
Ship all five; each is cheap to write and catches something the others miss.

## Key Takeaways for Section 5

`stop_reason == "end_turn"` is necessary but never sufficient as your only
stop condition. Layer natural-stop with an iteration cap, a token/dollar
budget, a wall-clock ceiling, and — where you want deliberate self-reported
completion — an explicit `finish` tool. This is a direct answer to one of
this chapter's named gotchas: **`max_tokens` is a per-response output cap, not
a loop guard** — it bounds how long *one* completion can be, and says
nothing about how many completions the loop is allowed to make.

*Next: what happens when a tool call fails partway through the loop —
because it will, and the wrong reaction breaks the whole run.*

---

# 6: Error Handling Inside the Loop

## The Intuition

Imagine giving someone directions and they report back "that street is
closed for construction." A bad assistant would just stop and give up on the
whole errand. A good one says "okay, let me find another way" and keeps
going — the closed street *is* useful information, not a reason to quit.
That is exactly the right posture for a tool failure inside an agent loop:
**a tool exception is data for the next step, not a reason to crash the
process.**

## Errors Are Training Data for the Next Step

When `execute_tool_call` catches an exception, it does not propagate that
exception up and kill the Python process — it converts the exception into a
string and feeds it back to the model as a `tool_result`, marked with
`is_error: true`:

```python
tool_result = {
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": "Error: file 'reports.txt' not found. Did you mean 'report.txt'?",
    "is_error": True,
}
```

Section 11's dry-run walks through exactly this scenario end to end: the
model mistypes a filename, gets an error back, and *on its own* tries again
with the corrected name on the very next step. This is the single biggest
reason not to hand-hold the model with defensive pre-validation of every
possible input — a well-worded error message, marked as an error, is often
all the correction the model needs. Compare this to what happens if you
silently swallow the exception and return an empty string instead: the model
has no idea anything went wrong, treats the empty result as if the file were
empty, and confidently reports a wrong answer with no error surfaced anywhere.
**Never drop a failed tool call. Always return a `tool_result`, and always
set `is_error: true` on it** — the field's whole purpose is letting the model
distinguish "this came back empty because that's the real answer" from "this
came back empty because something broke."

## Key Takeaways for Section 6

Convert every tool exception into a `tool_result` with `is_error: true`
rather than letting it crash the loop or silently vanish. A model that sees
its own mistake, with a clear enough error string to act on, will often
self-correct on the very next step — which is the concrete mechanism behind
Chapter 6's later theme, verification loops, and it's already visible here in
its simplest possible form.

*Next: what happens when the model asks for more than one tool in the same
breath.*

---

# 7: Parallel Tool Calls

## The Intuition

If you ask a capable assistant to "check the weather in three different
cities," a good one doesn't check them one at a time and report back after
each — they check all three, then come back once with everything. A single
assistant turn from the model can contain *multiple* `tool_use` blocks for
exactly this reason: the model has decided several independent lookups are
needed and has asked for all of them in one shot, expecting you to run them
and report back together.

## The Rule That's Easy to Get Backwards

Parallel tool use is the default behavior — one assistant message may
legitimately contain several `tool_use` blocks. Your loop must execute all of
them (concurrently if they're independent — nothing stops you from using a
thread pool or `asyncio.gather` here) and then return **every** result in a
**single** user turn:

```python
tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
results = []
for block in tool_use_blocks:
    content, is_error = execute_tool_call(block)
    results.append({
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": content,
        "is_error": is_error,
    })

messages.append({"role": "user", "content": results})   # ONE turn, ALL results
```

**Splitting the results across multiple user messages — one per tool —
silently trains the model to stop making parallel calls.** This isn't a crash
or an error you'll see in a stack trace; it's a quiet behavioral regression
where the model, having apparently learned that its parallel requests don't
come back together the way it expects, starts making tool calls one at a
time instead, and your agent gets slower with no obvious cause. If you're
debugging "why did my agent stop batching tool calls," check this exact spot
first.

## Key Takeaways for Section 7

One assistant turn can carry several `tool_use` blocks; execute all of them
and return all their `tool_result` blocks together, in exactly one user
message. Splitting them across multiple messages is syntactically valid and
silently wrong — it degrades parallel tool use over time without ever
throwing an error.

*Next: everything so far assumed a plain, blocking request-response call —
here's what changes when tokens arrive incrementally and the model reasons
between tool calls.*

---

# 8: Streaming and Interleaved Thinking

## The Intuition

A blocking call is like sending a letter and waiting for the full reply
before you read any of it. Streaming is like a phone call — words arrive as
they're spoken, and you can react (or at least render them to a screen) as
they come in, instead of staring at a blank page until the other person
finishes their entire thought.

## What Changes About the Loop

Streaming itself is not an Anthropic idea — Gemini and Bedrock's Converse API
both support it, with their own event shapes in place of `content_block_delta`
/ `message_delta`. What follows is written against Anthropic's event names,
but the *principle* — accumulate to the same final message before making any
loop-control decision — is the part that transfers everywhere.

Streaming doesn't change the *logic* of the loop — you still read a final
`stop_reason`, still branch on `tool_use` vs `end_turn`, still append the
same shapes to `messages`. What changes is *how you get there*: instead of
one blocking call that returns a complete `Message`, you open a stream and
consume events (`content_block_start`, `content_block_delta`,
`content_block_stop`, `message_delta`, `message_stop`) as they arrive, and
either render the deltas live or simply collect them and ask for the fully
accumulated message once the stream ends. In practice, almost every agent
loop uses the SDK's convenience wrapper for exactly this reason — stream for
the live tokens if you want them, but always end with the complete,
accumulated `Message` object before making any loop-control decision, because
`stop_reason` and `tool_use` blocks only exist once a content block has fully
closed.

```python
with client.messages.stream(model=MODEL, max_tokens=4096,
                             tools=tools, messages=messages) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)     # live output, if you want it
    response = stream.get_final_message()    # the same Message object a blocking call would give you
```

Streaming is also the practical answer to a very mundane but real problem:
**large `max_tokens` values on a non-streaming call risk hitting HTTP request
timeouts** before the model finishes generating. Once your loop's steps start
producing long completions (long tool inputs, long reasoning), streaming
stops being an optional nicety and becomes the thing that keeps the request
from timing out at all.

## Interleaved Thinking

On models with adaptive thinking, the model can reason *between* tool calls
within a single multi-step turn, not only before its first action — this is
what "interleaved thinking" refers to, and on current-generation models it is
enabled automatically whenever adaptive thinking is on, with no separate
configuration. Practically, this means a single assistant turn's `content`
array can now contain a `thinking` block, then a `tool_use` block, and after
the *next* tool result comes back, another `thinking` block before the
following action — the model is visibly "thinking out loud" at each decision
point in the loop, not just once at the start.

Two rules matter here, and both are easy to get wrong quietly rather than
loudly: **thinking blocks must be passed back to the model unchanged** when
you continue a conversation on the *same* model (the API validates that you
haven't tampered with them, and a modification produces a hard error); and if
you ever fork the conversation onto a *different* model — a subagent, a
fallback, a cheaper model for a sub-step — that model will simply **drop**
the thinking blocks it doesn't recognize rather than erroring, so you never
need to strip them yourself, but you also can't rely on that reasoning
surviving the fork.

## Key Takeaways for Section 8

Streaming changes *how* you receive a response, not the loop's branching
logic — always resolve to the same final, accumulated `Message` before making
a `stop_reason` decision. Interleaved thinking lets the model reason between
tool calls, not just before the first one; pass thinking blocks back
unmodified on the same model, and expect them to vanish (harmlessly) if the
conversation ever continues on a different one.

*Next: none of this chapter's careful bookkeeping is worth anything if you
can't look back at what actually happened — which is the entire point of the
next section.*

---

# 9: Trajectory Logging

## The Problem It Solves

An agent loop that doesn't log itself is a black box the instant something
goes wrong. "Why did it call that tool with those arguments?" "Which step
introduced the bad file path?" "How many tokens did step 7 actually cost?" —
none of these questions are answerable after the fact unless you wrote down,
at the time, exactly what happened at every step. This isn't a nice-to-have
debugging aid you add later; write it from the very first version of the
loop, because you cannot reconstruct a trajectory retroactively once the run
is over.

## What to Write, and Why JSONL Specifically

JSON Lines — one complete JSON object per line, appended as the run
progresses — is the right format because it's append-only (safe to write
incrementally, no need to hold the whole file structure in memory or rewrite
it), trivially greppable, and trivially loadable a record at a time even from
a run that crashed partway through.

```python
import json, time

def log_step(step_num, request_messages, response, tool_results):
    record = {
        "step": step_num,
        "timestamp": time.time(),
        "stop_reason": response.stop_reason,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "assistant_content": [block.model_dump() for block in response.content],
        "tool_results": tool_results,
    }
    with open("trajectory.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")
```

## Why This File Is Your Debugger, Your Eval Dataset, and Later Your RL Rollout

This is not an incidental side effect of good logging hygiene — it's the
reason this section exists in a chapter about the loop itself rather than
being deferred to a later "observability" chapter. The exact same JSONL file
serves three completely different purposes across this folder, and you get
all three for free from one piece of instrumentation written now:

1. **Right now, it's your debugger.** When a run does something confusing,
   you read the trajectory file, not the live terminal output.
2. **In Chapter 14, it's your eval dataset.** A real, failed trajectory from
   your own agent — not a synthetic example you imagined — becomes a golden
   test case the moment you fix whatever went wrong in it.
3. **In Chapter 18, it's your RL rollout.** Reinforcement learning on agent
   behavior needs exactly this shape of data — a sequence of states, actions,
   and outcomes — and a trajectory logger you wrote for debugging in Chapter 2
   is, structurally, already a rollout collector.

## Key Takeaways for Section 9

Log every step to JSONL from the first version of the loop, not as an
afterthought — step number, timestamp, `stop_reason`, token usage, full
assistant content, and tool results. The same file that helps you debug
tonight becomes an eval case in Chapter 14 and an RL rollout in Chapter 18;
none of that is possible if the data was never written down in the first
place.

*Next: you've now built the loop by hand — here's what the exact same loop
looks like wearing three different framework costumes.*

---

# 10: The Same Loop, Three Surfaces

## The Intuition

Think of this like **three ways to get a pizza**: cook it yourself from raw
ingredients (you control everything, you own every step, you also do all the
work); order from a pizza-assembly kit where someone gives you pre-portioned
ingredients and you still bake it (less work, still your oven, still your
kitchen); or order delivery and have someone else's kitchen make the whole
thing and bring it to your door (almost no work, but it's not your kitchen
and you can't see inside it). None of these is "the right one" — they trade
control for convenience along a real spectrum, and the right choice depends
entirely on how much of the process you actually need to see and steer.

## The Three Real Options

| # | Approach | You write | Who supplies the loop | Tools available | Reach for this when |
|---|---|---|---|---|---|
| 1 | **Manual loop** (this chapter) | The `while` loop yourself, exactly as built above | You do — full ownership, full visibility | Only tools you define | You want to own the *entire* loop, need a control flow a framework's hooks don't fit, or want zero framework dependency |
| 2 | **Tool Runner** (SDK helper) | Just the tool functions, decorated | The SDK — it drives the request → execute → feed-back cycle for you | Only tools you define | You want a custom-tool agent without hand-writing the loop, and you're fine trusting the SDK's per-turn hooks for approval gates, retries, and streaming |
| 3 | **Claude Agent SDK** — *a separate product* | A prompt plus configuration options | The SDK — it supplies the full Claude Code harness | Built-in file read/write/edit, bash, grep, web search, plus MCP and subagents | You want a batteries-included coding/filesystem agent and don't need to define your own tool surface from scratch |

The Tool Runner is genuinely a thin convenience layer over exactly the loop
you just wrote — it automates the request/execute/feedback cycle for tools
*you* define, and still exposes per-turn hooks so you can intercept an
approval gate, retry a failed call, or modify a result before it goes back to
the model. It has no built-in tools and no filesystem access of its own; it
is option 1's mechanics with the bookkeeping done for you.

The Claude Agent SDK is a different thing entirely, and worth being precise
about the distinction: it is Claude Code itself, packaged as a library — the
full agent loop, built-in tools, context management, hooks, subagents,
permissions, and sessions all bundled together. Where the Tool Runner loops
over tools you supply, the Agent SDK ships its own substantial toolset and
its own harness decisions already made. Neither one manages *deployment* for
you (you still host and run both); that's what Chapter 1's fourth column —
Managed Agents, a separate hosted product — adds on top, and it's out of
scope for this folder.

## Filling In the Comparison Yourself

This folder's convention is that you build the same small task three ways
and fill in a table like this from what you actually observe — lines of code,
debuggability when something goes wrong, how much of the request shape you
can control, and how quickly you could ship a first version:

| Dimension | Manual loop | Tool Runner | Claude Agent SDK |
|---|---|---|---|
| Lines of code for a 2-tool agent | *(you measure this)* | | |
| Can you inspect every request/response? | Yes, trivially | Yes, via hooks | Partially — internal harness decisions are opaque |
| Built-in tools | None | None | File I/O, bash, grep, web search |
| Framework dependency | None | Beta SDK feature | A separate library |
| Best fit | Learning, or unusual control flow | Custom-tool agents, fast | Coding/filesystem agents |

## Key Takeaways for Section 10

Three real options exist along one spectrum of control versus convenience:
the manual loop (full ownership), the Tool Runner (same loop, SDK-automated
bookkeeping, tools you still define), and the Claude Agent SDK (a different
product entirely — Claude Code as a library, with its own built-in tools and
harness). None of the three manages deployment for you; that's a fourth,
separate axis (Managed Agents) this folder doesn't cover. Build the same task
three ways before trusting a comparison table someone else filled in for you.

*Next: the loop you've built is real, but it's also honestly incomplete — a
last, deliberately candid list of what it still can't do.*

---

# 11: Dry-Run: Hand-Tracing a 4-Step Loop

## The Setup

Task: *"How many words are in report.txt?"* Two tools available:
`read_file(path)` and `word_count(text)`. Fixed prefix (system prompt + both
tool schemas): **600 tokens** — the same fixed-prefix idea from Chapter 1's
Section 11, just with a smaller, concrete number this time.

We deliberately trace a run where the model makes a small mistake and
recovers from it, because that is the realistic case, not the clean one —
and it's exactly Section 6's error-handling principle made concrete.

## Step-by-Step, With the Message Array After Each Step

```
Before any call:
  messages = [
    user: "How many words are in report.txt? It's in the current directory."  (20 tok)
  ]
```

**Step 1 — API call 1.** Input = 600 (fixed prefix) + 20 (user msg) = **620
tokens**. The model, guessing at a filename, responds with a short text
aside plus a `tool_use` block:

```
assistant: [text: "Let me look for that file." (10 tok),
            tool_use: read_file(path="reports.txt") (15 tok)]     -- 25 tok completion
stop_reason: tool_use
```

We execute `read_file("reports.txt")` → `FileNotFoundError`. Per Section 6,
this becomes an error `tool_result`, not a crash:

```
messages now:
  [user(20), assistant(25),
   user: tool_result(is_error=true, "Error: reports.txt not found. Did you mean report.txt?") (20 tok)]
```

**Step 2 — API call 2.** Input = 620 + 25 (assistant turn 1) + 20 (error
result) = **665 tokens**. The model self-corrects on the very next step,
exactly as Section 6 predicted — no extra prompting needed:

```
assistant: [tool_use: read_file(path="report.txt")]     -- 15 tok completion
stop_reason: tool_use
```

`read_file("report.txt")` succeeds this time, returning the file's contents —
say the report is **200 tokens** long.

```
messages now:
  [..., assistant(15), user: tool_result("<200-token file content>") (200 tok)]
```

**Step 3 — API call 3.** Input = 665 + 15 + 200 = **880 tokens**. The model
now calls `word_count`, and here is the detail worth stopping on: to pass the
file's content *into* `word_count`, the model must **re-emit that entire
200-token string as the tool's input argument** — it cannot simply point at
what `read_file` already returned.

```
assistant: [tool_use: word_count(text="<the same 200-token content, re-typed>")]   -- ~205 tok completion
stop_reason: tool_use
```

**The file content now exists twice in the transcript** — once as
`read_file`'s `tool_result`, once again as `word_count`'s `tool_use` input.
That's not a mistake in this trace; it's the honest, measurable cost of
chaining two tools through the model. `word_count` executes locally against
that string and returns `"142 words"` (5 tokens).

**Step 4 — API call 4.** Input = 880 + 205 + 5 = **1,090 tokens**. The model
produces its final answer:

```
assistant: [text: "The report contains 142 words."]     -- 10 tok completion
stop_reason: end_turn   →   loop exits
```

## The Totals, and the One Thing Worth Remembering

```
Total input tokens across 4 calls:  620 + 665 + 880 + 1,090 = 3,255
Total completion tokens:             25 +  15 + 205 +   10 =   255
```

**The content-duplication cost is not a bug to route around inside this
chapter's loop — it's the honest price of tool chaining through a model's
context, and it's exactly what Chapter 8's code-execution pattern exists to
eliminate:** letting a tool's output flow to another tool's input via a
sandboxed script, never touching the model's output tokens at all. Seeing the
extra 200 tokens appear twice in this tiny four-step trace is the concrete,
felt reason that later chapter is worth its own weight.

## Key Takeaways for Section 11

A 4-step run over a genuinely small task still moves 3,255 input tokens and
recovers from one realistic tool error along the way — and one of its four
steps spends roughly 200 tokens purely re-emitting content the model had
already seen once, because chaining two tools through the model necessarily
means the content passes through the model's output twice. Both of these
facts — recoverable errors, and the true cost of tool-to-tool chaining — are
easy to state abstractly and much more convincing traced by hand once.

*Next: a candid list of everything this working loop still cannot do — which
is, not coincidentally, the rest of this folder's table of contents.*

---

# 12: What the Loop Cannot Do Yet

## The Honest List

The loop you've built in this chapter is a real, complete agent — it thinks,
acts, observes, handles errors, stops correctly, and logs itself. It is also,
deliberately, missing everything that turns a working demo into something you
would trust unattended, and naming that list precisely is more useful than
pretending it's already done:

| Missing capability | Symptom without it | Where it's built |
|---|---|---|
| **Memory across sessions** | Every run starts from zero; nothing learned in run 1 carries into run 2 | Chapter 9 |
| **Verification beyond `end_turn`** | The model's own claim of success is the only signal — Chapter 1's *victory declaration bias* in its purest form | Chapter 6 |
| **Permissions / blast-radius limits** | Any tool this loop can call, it calls freely — no approval gate exists yet | Chapter 16 |
| **Persistence across a crash** | Kill the process at step 30 of 60 and the entire run is gone, not resumed | Chapter 12 |
| **Formal evals** | You can *feel* whether a run went well; you cannot yet *measure* it against a benchmark or catch a regression | Chapter 14 |
| **Context management beyond "let it grow"** | Exactly Section 2's problem — nothing here ever compacts, evicts, or externalizes | Chapter 4 |

## Why Naming This List Matters More Than It Sounds

This isn't a disclaimer to feel bad about — it's the actual value of having
built the loop by hand at all. Now that every one of these six gaps sits on
top of a loop you fully understand, each later chapter has a precise, small
thing to attach: Chapter 6 adds one verifier call before you trust
`end_turn`; Chapter 9 adds a lookup and a write at the edges of this same
loop; Chapter 16 adds one `if tool_is_destructive: ask_approval()` check
inside `execute_tool_call`. None of that requires touching the core cycle
from Section 3 — it requires understanding it well enough to know exactly
where the seam is.

## Key Takeaways for Section 12

Six specific capabilities are absent from this chapter's loop by design, not
by accident, and each has an exact chapter number where it gets built. This
list is this folder's real table of contents, restated as gaps in a working
system instead of as abstract topics.

---

# 13: Key Takeaways + Master Decision Table

The single mental model for this chapter: **the loop is `send → read
stop_reason → branch → (execute + append) → repeat`, and the message list is
the entire state of the world.** Everything from here forward in B04 is a
deliberate addition to this exact cycle.

| I want to know... | Reach for | Key fact |
|---|---|---|
| What actually holds the conversation's state | Section 2 | The message list itself — the API is stateless, nothing persists server-side |
| Why `content[0].text` sometimes crashes | Section 3 | Branch on `stop_reason` first; `tool_use` means no top-level text, `refusal` can mean empty content |
| How a tool call actually gets executed | Section 4 | A plain dict from tool name → Python function; the model never calls code directly |
| Why my loop never stops | Section 5 | `end_turn` alone is not enough — layer an iteration cap, a budget, a wall-clock limit, and (optionally) an explicit finish tool |
| What to do when a tool throws | Section 6 | Catch it, return a `tool_result` with `is_error: true` — never crash, never drop it silently |
| Why my agent stopped batching tool calls | Section 7 | All `tool_result` blocks for one turn must go back in a single user message, not split across several |
| What changes with streaming | Section 8 | How you receive tokens, not the loop's branching logic; always resolve to the final accumulated message before deciding anything |
| Why I should log every step | Section 9 | The same JSONL file is your debugger today, your eval case in Ch 14, and your RL rollout in Ch 18 |
| Which of the three SDK options to use | Section 10 | Manual loop (full control) vs Tool Runner (same loop, less bookkeeping) vs Claude Agent SDK (a different product entirely) |
| Why chaining two tools costs more than it looks | Section 11 | Content the model must pass from one tool to another gets re-emitted as tool input — it appears twice in the transcript |
| What this loop still can't do | Section 12 | Memory, verification, permissions, persistence, evals, and context management — each with an exact later chapter |

**Connection forward:** Chapter 3 goes back to the tool definitions this
chapter treated as given — naming, schema shape, granularity, error-message
wording — and asks the question this chapter only gestured at: what actually
makes one tool design good and another one quietly sabotage the model calling
it correctly.
