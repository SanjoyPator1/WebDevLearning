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

*Everything below is demonstrated against Anthropic's Messages API wire
format — `tool_use` blocks, `stop_reason` values, `tool_result` matching —
because those are the actual mechanics this chapter teaches, not an
implementation detail to abstract away. Every code example, and this
chapter's whole notebook, connects to one concrete target: **Claude Sonnet,
through AWS Bedrock.** The loop concept itself — think, act, observe, in a
growing message list — is not unique to Anthropic; most current
tool-calling models work this way, each with its own field names for the
same handful of ideas. This chapter doesn't try to teach those other
vocabularies side by side with this one — it teaches one real wire format
all the way through, on the theory that a single mechanism you deeply
understand transfers to a second one far more easily than a shallow tour of
three at once.*

## Why This Chapter Is Bedrock + Claude Sonnet, and Nothing Else

An earlier pass at these notes taught this chapter's loop against three
parallel vocabularies at once — Anthropic, Gemini, and a generic Bedrock
API — on the theory that seeing the same idea expressed three ways builds a
more general mental model. In practice this produced the opposite effect:
three sets of field names for the same five concepts is a lot to hold in
your head while you're still learning the concepts themselves, and hedging
across three surfaces ends up teaching all three shallowly instead of one
deeply. This chapter, and every notebook and note in this folder from here
forward, commits to one concrete target instead.

This is a smaller simplification than it might sound, for a specific
technical reason worth stating precisely: this project's Bedrock access
goes through `anthropic.AnthropicBedrockMantle`, part of Anthropic's own
Python SDK, which exposes **the exact same request and response shape** as
calling Anthropic directly — the same `tool_use`/`tool_result` blocks, the
same `stop_reason` values, the same `messages.create()` call signature.
Bedrock, in this setup, is not a different wire format to learn — it's a
different *transport and billing layer* underneath an identical API: AWS
credentials and AWS's infrastructure stand in for an Anthropic API key and
Anthropic's own servers, and nothing about the shapes described in this
chapter changes as a result. (Worth contrasting with AWS's own, separate
Converse API, which really does use different field names — `toolUse`,
`toolResult`, `stopReason` in camelCase. This course does not use that API
at all, specifically to avoid that exact difference.)

*If you go on to work with Gemini, OpenAI, or any other tool-calling model
later, the underlying loop in Section 3 — send everything, read a stop
signal, branch, execute, append, repeat — still applies unchanged. Only the
field names differ. This chapter is teaching you that loop once, all the
way through, on real infrastructure, rather than teaching it three times
shallowly.*

## How This Chapter's Notebook Actually Connects to Claude

Every notebook in this folder connects to Claude the same simple way, in
plain code at the very top of the notebook — no shared config module to
import, no provider-selection variable to set. Four values, read from
environment variables (via a `.env` file, never hardcoded) into
plainly-named constants:

```python
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_NAME = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-5")
```

These four feed directly into `AnthropicBedrockMantle(...)`, and the
resulting `client` is exactly the `client` every code example in this
chapter already assumes — `client.messages.create(model=MODEL_NAME, ...)`.
There is no wrapper function standing between this chapter and the real SDK
call; what you read in these notes is what actually runs.

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
    {"role": "user", "content": "What does report.txt say?"},
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
                    ┌───────────────────────────────────────────────────────┐
                    │                                                       │
                    ▼                                                       │
        ┌────────────────────┐                                              │
        │  Send full message │   POST /v1/messages                          │
        │  list + tools to   │───────────────────────┐                      │
        │  the model         │                       ▼                      │
        └────────────────────┘              ┌───────────────────┐           │
                                            │  Read stop_reason │           │
                                            └─────────┬─────────┘           │
                              ┌───────────────────────┼──────────┐          │
                              ▼                       ▼          ▼          │
                    stop_reason ==            stop_reason ==   other        │
                    "tool_use"                "end_turn"      (max_tokens,  │
                              │                       │        refusal, …)  │
                              ▼                       ▼                     │
                  ┌────────────────────┐    ┌───────────────────┐           │
                  │ Append assistant   │    │  Done. Return the │           │
                  │ turn to messages   │    │  final text.      │           │
                  │ (BEFORE executing  │    └───────────────────┘           │
                  │  anything)         │                                    │
                  └─────────┬──────────┘                                    │
                            ▼                                               │
                  ┌───────────────────┐                                     │
                  │ Execute every     │                                     │
                  │ tool_use block    │                                     │
                  └─────────┬─────────┘                                     │
                            ▼                                               │
                  ┌────────────────────┐                                    │
                  │ Append ALL results │                                    │
                  │ as ONE user turn   │────────────────────────────────────┘
                  └────────────────────┘        loop back to top
```

## Reading `stop_reason` Correctly

Every response carries a `stop_reason` field, and the entire branching logic
of an agent loop is a switch on this one value. As of the current API
surface, there are **seven** values, not six — one was added recently
specifically to close a gap this chapter's own advice ("never assume the
loop only ever ends in exactly two ways") warns about:

| `stop_reason` | What it means | What the loop does |
|---|---|---|
| `end_turn` | The model finished its answer naturally | Exit the loop, return the text |
| `tool_use` | The model wants to call one or more tools | Execute them, append results, loop again |
| `max_tokens` | Hit the output token cap mid-generation | Retry with a higher cap, or treat as a failure — never silently accept a truncated answer |
| `stop_sequence` | Hit one of your configured `stop_sequences` strings | The specific string is in the `stop_sequence` field; usually treated like `end_turn` |
| `pause_turn` | A server-side tool loop (web search, code execution) hit its default 10-iteration cap mid-task and can be resumed | Append the response's own `content` back as a new assistant turn — **add no new user message** — and resend; the server picks up where it left off |
| `refusal` | Safety classifiers declined the request | Normal HTTP 200, not an exception — check `stop_reason` before touching `content`, because `content` may be empty; a `stop_details` object gives the policy category (`cyber`, `bio`, `frontier_llm`, `reasoning_extraction`, `general_harms`) |
| `model_context_window_exceeded` | Generation filled the model's entire context window before hitting `max_tokens` | Treat exactly like `max_tokens` — the output is truncated, not complete |

*A precise correction worth calling out, because it's easy to get subtly
wrong even after reading the docs once: `pause_turn` does **not** mean
"resend the identical request." It means take the paused response's
`content` array, append it to `messages` as one more `assistant` turn (on
top of whatever was already there), and call `messages.create` again with
that longer list — no extra user text, no re-typing the original question.
The request body is one message longer than before, not byte-identical.*

Three of these seven values are easy to forget exist at all until a loop
trips over them in production: `pause_turn` (specific to Anthropic's
server-side tools hitting an internal iteration cap — it does not apply to
the custom `read_file`/`word_count`-style tools this chapter's dispatch
table runs, since those never touch the server-side loop at all),
`refusal` (a normal HTTP 200, not an exception), and
`model_context_window_exceeded` (newer than the other six, and — on models
older than Sonnet 4.5 — gated behind a beta header; on the current-generation
model this chapter targets it needs no special flag). The lesson underneath
the whole table stays the same regardless of how many rows it has:
**enumerate every value `stop_reason` can take before you ship, never just
the two you expect.**

The single most common bug in a first agent loop is treating `content[0].text`
as always present. It is not, on two different `stop_reason` values: `tool_use`
(the useful content is a `tool_use` block, which has no `.text` attribute at
all) and `refusal` (content can be empty). **Always branch on `stop_reason`
first; only reach into `content` after you know what kind of turn you're
holding.** Concretely, the naive version breaks like this:

```python
# BAD: assumes content[0] is always a text block
answer = response.content[0].text

# stop_reason == "tool_use"  → content[0] is a ToolUseBlock → AttributeError:
#     'ToolUseBlock' object has no attribute 'text'
# stop_reason == "refusal"   → content may be [] entirely     → IndexError:
#     list index out of range
```

```python
# GOOD: branch first, only then reach into content
if response.stop_reason == "end_turn":
    answer = response.content[0].text
elif response.stop_reason == "refusal":
    answer = "(request declined by safety classifiers)"
elif response.stop_reason == "tool_use":
    ...  # see below — this is not a final answer yet
```

## A Full Turn, Traced with Real Object Shapes

The diagram above is the shape of the cycle; here is what it actually looks
like in memory, using the same `read_file` tool Section 11's longer dry-run
builds on, so the two sections connect directly. One user question, one
tool call, one final answer — no mistakes yet, so the mechanics are visible
without the error-recovery detail Section 11 adds on top.

Every state below is shown as the literal JSON `messages` actually holds (or
becomes, over the wire, the instant it's sent) — not a paraphrase of it. The
Python SDK hands you typed objects (`TextBlock`, `ToolUseBlock`) rather than
raw dicts when it *receives* a response, but those objects serialize to
exactly this JSON shape, and it's this JSON shape the API is checking on the
way back in — so tracing it in JSON, not in SDK-object notation, is tracing
the thing that's actually true of the wire, independent of which language's
SDK you're holding.

**Before any call**, `messages` holds exactly one entry:

```json
{
  "messages": [
    {"role": "user", "content": "What does report.txt say?"}
  ]
}
```

**Call 1.** `client.messages.create(model=MODEL_NAME, max_tokens=1024, tools=tools, messages=messages)`
comes back with `stop_reason == "tool_use"` and a `content` array holding
*two* blocks — a short text aside, then the tool call itself:

```json
{
  "stop_reason": "tool_use",
  "content": [
    {
      "type": "text",
      "text": "Let me check that file."
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "read_file",
      "input": {"path": "report.txt"},
      "caller": {"type": "direct"}
    }
  ]
}
```

*(`caller` marks whether this call came straight from the model — `direct`
— or was generated by a server-side tool instead. Every tool this chapter's
dispatch table runs is called directly, so `caller` will always read
`{"type": "direct"}` here and you can ignore the field for now.)*

Per the rule above, the **full** `content` array — text block and all — gets
appended as one assistant turn *before* anything is executed:

```python
messages.append({"role": "assistant", "content": response.content})
```

`messages` is now this — two entries, the second one holding both blocks
from `response.content` untouched:

```json
{
  "messages": [
    {"role": "user", "content": "What does report.txt say?"},
    {
      "role": "assistant",
      "content": [
        {"type": "text", "text": "Let me check that file."},
        {
          "type": "tool_use",
          "id": "toolu_01A09q90qw90lq917835lq9",
          "name": "read_file",
          "input": {"path": "report.txt"},
          "caller": {"type": "direct"}
        }
      ]
    }
  ]
}
```

**Executing the tool.** Pull the `tool_use` block(s) out of `content`, look
`name` up in `TOOL_DISPATCH` (Section 4 builds this dictionary), and run it:

```python
tool_use_block = next(b for b in response.content if b.type == "tool_use")
result_text, is_error = execute_tool_call(tool_use_block)   # -> ('Quarterly revenue grew ...', False)

tool_result = {
    "type": "tool_result",
    "tool_use_id": tool_use_block.id,   # MUST match the tool_use block's id exactly
    "content": result_text,
    "is_error": is_error,
}
```

`tool_result` itself, as JSON — note `tool_use_id` is a copy of the *same*
`toolu_01A09...` string from the block above, not a new id of its own:

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
  "content": "Quarterly revenue grew twelve percent driven by strong demand in the enterprise segment and continued expansion in international markets.",
  "is_error": false
}
```

**Append the result as one user turn**, and the state going into the next
call is now three messages deep:

```python
messages.append({"role": "user", "content": [tool_result]})
```

```json
{
  "messages": [
    {"role": "user", "content": "What does report.txt say?"},
    {
      "role": "assistant",
      "content": [
        {"type": "text", "text": "Let me check that file."},
        {
          "type": "tool_use",
          "id": "toolu_01A09q90qw90lq917835lq9",
          "name": "read_file",
          "input": {"path": "report.txt"},
          "caller": {"type": "direct"}
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
          "content": "Quarterly revenue grew twelve percent driven by strong demand in the enterprise segment and continued expansion in international markets.",
          "is_error": false
        }
      ]
    }
  ]
}
```

This exact JSON blob — all three messages, in full — is what gets sent as
the `messages` field of Call 2's request body. Nothing from Call 1 is
dropped, summarized, or referenced by pointer; the whole transcript rides
along again, which is Section 2's stateless-API point made concrete in JSON
instead of in prose.

### Why the Tool Result Is a `user` Turn, Not an `assistant` Turn

This trips almost everyone up the first time: the model asked for the tool
call, so it feels like the *answer* to that request should also come from
"the model's side" — an `assistant` message. It doesn't. It goes back in as
`user`, and the reason is simpler than it looks once you say it plainly:
**only the model can speak as `assistant`.** That role means "this content
was generated by the model" — full stop. Your Python code executing
`read_file("report.txt")` is not the model generating anything; it's *your
side* of the conversation handing something back, exactly the same way a
human typing a follow-up message is "your side" handing something back.
There is no third role for "stuff the developer's code produced" — the API
only has two conversational participants, `user` and `assistant`, and
whichever side didn't just speak as the model has to be `user`, tool results
included.

Think of it like the notebook-passed-across-a-table picture from Section 2:
the model wrote "please flip to page 12 and tell me what it says" (that's
the `tool_use` block, correctly labeled `assistant` — the model said it).
You flip to page 12, read it, and write the answer into the notebook
yourself. From the model's point of view, reading that page 12 content
back on the next turn is indistinguishable from a human having typed it in
— both are things that showed up in the conversation that the model did not
itself generate. That's exactly what `user` means here: not "a human typed
this" specifically, but "this did not come from the model."

One more detail this explains for free: that's also *why* `tool_result`
blocks are only ever valid inside a `user`-role message, never inside an
`assistant` one — the schema enforces the same rule the role names already
imply, so there is no way to accidentally put a tool result on the wrong
side even if you tried.

**Call 2.** The same `messages.create(...)` call, now sent with the
three-message JSON body above instead of the original one-message body,
comes back with `stop_reason == "end_turn"` and a plain text answer — the
loop reads that, appends nothing further, and exits:

```json
{
  "stop_reason": "end_turn",
  "content": [
    {"type": "text", "text": "Revenue grew 12% on strong enterprise demand."}
  ]
}
```

### What `messages` Looks Like After This — Still Just 3 Entries

Here's the detail worth stopping on, because it's easy to expect a fourth
entry to appear and be confused when it doesn't: **`messages` stays exactly
as it was going into Call 2 — three entries, unchanged.** The `end_turn`
branch never runs an `append`. Look back at "The One Rule" section's code:
the `messages.append(...)` call only happens *inside* the `if
response.stop_reason == "tool_use":` branch, and the actual loop code this
chapter's notebook runs (`run_agent_loop`) makes the same choice explicitly —
on `end_turn` it pulls the text out of `response_2.content` and `return`s
immediately, never touching `messages` at all:

```python
if response.stop_reason == "end_turn":
    final_text = next((b.text for b in response.content if b.type == "text"), "")
    return final_text, step, cumulative_tokens   # messages is untouched — the loop just exits
```

The reason this is correct, not an oversight, is a scope choice, not an
efficiency one — worth being precise about, because the efficiency framing
is actually wrong: appending to a Python list costs nanoseconds, no API
call, no tokens billed. There is no real cost being saved by skipping it.
`run_agent_loop`'s actual contract is "take a prompt, run to completion,
return the answer" — nothing inside that function will ever read `messages`
again after it `return`s, so whether it appends the final turn is invisible
to that function's own correctness. That's a narrow, single-task shape, not
a general rule about when appending is worth doing — see the note right
below.

*This changes the moment there **is** a next call — for instance, if your
program hands the finished answer back to a human and the human types a
follow-up question. In that case you'd append the final assistant turn
yourself, immediately before adding the human's new message, precisely
because now a future call does exist and does need to see it:*

```python
messages.append({"role": "assistant", "content": response_2.content})
messages.append({"role": "user", "content": "Thanks — and what about business.txt?"})
# only now does messages grow to 5 entries; nothing forces this append to
# happen automatically, because the loop itself has no idea whether a human
# is waiting on the other end of this run or not
```

`messages` at that point — the original three entries, untouched, plus the
two new ones just appended:

```json
{
  "messages": [
    {"role": "user", "content": "What does report.txt say?"},
    {
      "role": "assistant",
      "content": [
        {"type": "text", "text": "Let me check that file."},
        {
          "type": "tool_use",
          "id": "toolu_01A09q90qw90lq917835lq9",
          "name": "read_file",
          "input": {"path": "report.txt"},
          "caller": {"type": "direct"}
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
          "content": "Quarterly revenue grew twelve percent driven by strong demand in the enterprise segment and continued expansion in international markets.",
          "is_error": false
        }
      ]
    },
    {
      "role": "assistant",
      "content": [
        {"type": "text", "text": "Revenue grew 12% on strong enterprise demand."}
      ]
    },
    {
      "role": "user",
      "content": "Thanks — and what about business.txt?"
    }
  ]
}
```

Notice entries `[0]` through `[2]` are byte-for-byte the same JSON as the
body Call 2 already sent — nothing about them changes just because a new
turn started. `[3]` is the assistant's finished answer, appended for the
first time only now that a follow-up exists to need it. `[4]` is the new
human question — a plain string, exactly like `[0]` was, because a fresh
human turn is not a tool result and gets no `tool_result` wrapping. This
five-entry list is what Call 3 would send in full, and the cycle from the
top of this section — send, read `stop_reason`, branch — starts over
unchanged on top of it.

### Two Legitimate Patterns — and Which One Is Actually Standard

Given that appending is free, a fair question is: why not just *always*
append the final turn the instant it arrives, so the caller never has to
remember to do it themselves before adding a follow-up? **That's exactly
what most real agent frameworks do, and it's the better default to reach
for outside this specific notebook exercise.**

| Pattern | `messages` is owned by | Append on `end_turn`? | Continuing later means |
|---|---|---|---|
| **Task-scoped run** (this chapter's `run_agent_loop`) | The caller, for the duration of one `run` only | No — the function returns before it matters | The caller decides from scratch what to send next |
| **Always-append thread** (OpenAI Assistants "threads," Claude Agent SDK sessions, LangChain memory, chat apps generally) | A persistent session object, for the conversation's whole lifetime | Yes — every turn, any `stop_reason`, appended the instant it's produced | Append one new user message, call again — no conditional logic anywhere |

The always-append version of this exact loop looks like this — note the
single `self.messages.append(...)` line right after every `create()` call,
with no `if stop_reason == ...` guard in front of it:

```python
class Conversation:
    def __init__(self, client, model, tools):
        self.client = client
        self.model = model
        self.tools = tools
        self.messages = []

    def ask(self, user_text):
        self.messages.append({"role": "user", "content": user_text})
        while True:
            response = self.client.messages.create(
                model=self.model, max_tokens=1024,
                tools=self.tools, messages=self.messages,
            )
            self.messages.append({"role": "assistant", "content": response.content})  # ALWAYS — every stop_reason

            if response.stop_reason == "end_turn":
                return next(b.text for b in response.content if b.type == "text")

            # stop_reason == "tool_use": execute every block, append one user turn, loop
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                content_str, is_error = execute_tool_call(block)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content_str,
                    "is_error": is_error,
                })
            self.messages.append({"role": "user", "content": results})
```

```python
convo = Conversation(client, MODEL_NAME, tools)
convo.ask("What does report.txt say?")             # convo.messages ends at 3 entries, already appended
convo.ask("Thanks — and what about business.txt?")  # only need to hand it the new question — no manual bookkeeping
```

Both patterns are correct — a task-scoped run function that hands its answer
back to a caller who may or may not ever call it again is a perfectly
reasonable shape for a one-shot job (a batch script, a CI check, a single
tool invocation from another program). But the moment you're building
anything that looks like a conversation — a chat UI, an assistant a human
keeps talking to, a coding agent resumed across several prompts — the
always-append thread is the pattern actually used in production, precisely
because it eliminates the exact bug class Section 3 keeps returning to:
forgetting to append the right thing at the right moment before the next
call goes out.

That is the entire cycle, traced in the literal JSON the API actually sends
and receives at every step: one call produced two content blocks, `messages`
grew by one entry on each of two appends (1 → 2 → 3), and the second call's
`tool_use_id` match is what let the model connect its own request to the
answer it asked for. Section 11 walks this same shape through four steps
instead of two, with an intentional wrong filename in the mix and running
token totals attached to every step.

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
turn with all the results → loop. Seven `stop_reason` values exist now
(`model_context_window_exceeded` joined the original six), and each demands
different handling — the three that trip people up in production are
`tool_use` (content isn't text), `refusal` (content might be empty), and
`pause_turn` (resend means "append the response and continue," not "send an
identical request"). Traced at the object level, one successful tool call
costs exactly two `messages.append` calls and one matched `tool_use_id` —
everything Section 11's longer, messier trace builds on is this same shape
repeated with an error and a token counter attached.

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

Streaming itself is not unique to this API — most current providers offer
some form of incremental token delivery. What follows is written against
Anthropic's specific event names, the ones this chapter's notebook actually
uses.

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
