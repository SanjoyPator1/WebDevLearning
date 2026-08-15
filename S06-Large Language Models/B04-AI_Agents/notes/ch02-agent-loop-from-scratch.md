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

## What is a Dispatch Table?

A dispatch table is simply a Python dictionary that maps string names (like `"get_weather"`) to actual Python functions. When the model decides to use a tool, it outputs a string name. Your code uses this dictionary to "dispatch" (or route) that string name to the real code that does the work.

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

## The Tool Schema (What the Model Actually Sees)

While the dictionary above maps names to Python functions, the model itself never sees your Python code. You must define a `tools` list containing JSON Schema objects for each tool.

**Where is this used?** This exact array is passed to the API on every turn in the main loop (as seen in Section 3):
`client.messages.create(..., tools=tools, ...)`

This list is the bridge between the model's choices and your dispatch table. When the model reads this list, it learns what tools exist, what they do, and what arguments they require.

```python
tools = [
    {
        "name": "get_weather",
        "description": "Look up the current weather for a city. Call this when the user asks for the weather in a specific location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "read_file",
        "description": "Return the contents of a file at `path`. Use this to inspect code or read reports.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file"
                }
            },
            "required": ["path"]
        }
    }
]
```

## Definitions Are a User Interface Whose User Is a Model

The `name`, `description`, and `input_schema` you declare for each tool in the JSON array above are
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

### The Five Guards in Code (Applying the Theory)

To see how these concepts connect to actual code, look at how the guards are distributed. Pre-flight checks (like budget and time) happen *before* calling the API, while response checks (natural stop or a `finish` tool) happen *after*.

```python
MAX_STEPS = 20
MAX_TOKENS_BUDGET = 50_000
start_time = time.monotonic()
cumulative_tokens = 0

for step in range(MAX_STEPS):
    # 1. Wall-clock guard (Pre-flight check)
    if time.monotonic() - start_time > 300:
        print("Hit wall-clock limit.")
        break
        
    # 2. Budget guard (Pre-flight check)
    if cumulative_tokens > MAX_TOKENS_BUDGET:
        print("Hit token budget limit.")
        break

    response = client.messages.create(...)
    cumulative_tokens += response.usage.input_tokens + response.usage.output_tokens

    # 3. Natural stop (Post-flight check)
    if response.stop_reason == "end_turn":
        print("Model completed its turn naturally.")
        break
        
    # 4. Explicit 'finish' tool (Checking tool_use blocks)
    if response.stop_reason == "tool_use":
        # Check if the model called our explicit termination tool
        is_finished = any(block.name == "finish" for block in response.content if block.type == "tool_use")
        if is_finished:
            print("Model explicitly called the 'finish' tool.")
            break
            
        # ... otherwise, handle normal tools, append results, and continue

# 5. Max-iteration guard (The loop itself)
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

Here is a visual representation of how a tool failure becomes a self-correction opportunity:

```text
   [Model]                                [Loop]                               [Tool]
      │                                     │                                    │
      │   tool_use(path="reports.txt")      │                                    │
      │────────────────────────────────────▶│                                    │
      │                                     │  execute read_file("reports.txt")  │
      │                                     │───────────────────────────────────▶│
      │                                     │                                    │
      │                                     │    Exception: FileNotFoundError    │
      │                                     │◀───────────────────────────────────│
      │                                     │                                    │
      │                                     │ (Catch exception, set is_error=True)
      │                                     │                                    │
      │   user msg + tool_result (Error)    │                                    │
      │◀────────────────────────────────────│                                    │
      │                                     │                                    │
      │   tool_use(path="report.txt")       │                                    │
      │────────────────────────────────────▶│    <-- Self Correction!            │
```

### Catching Errors in Code (Applying the Theory)

To see this in practice, look at the `execute_tool_call` function. This is where the Python exception is caught and converted into a clean string, rather than crashing your script.

```python
def execute_tool_call(block):
    fn = TOOL_DISPATCH.get(block.name)
    if fn is None:
        # Tool doesn't exist? That's an error for the model to fix.
        return f"Error: no such tool '{block.name}'", True
        
    try:
        # Attempt to run the real Python function
        result = fn(**block.input)
        return str(result), False                            # Success! is_error=False
    except Exception as exc:
        # We caught an error! Do NOT raise it.
        # Instead, return it as a string so the model can read it.
        return f"Error: {type(exc).__name__}: {exc}", True   # Failure! is_error=True
```

Then, back in your main loop, you use that boolean flag to build the JSON object exactly as the API expects:

```python
# Inside the main loop...
content_str, is_error = execute_tool_call(block)

tool_result = {
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": content_str,   # Contains the error string if it failed!
    "is_error": is_error,     # Crucial flag that tells the model it messed up
}

messages.append({"role": "user", "content": [tool_result]})
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

Parallel tool use is the default behavior — one assistant message may legitimately contain several `tool_use` blocks. 

Here is what the flow looks like when the model asks for two weather checks at once:

```text
  [Model]                                  [Loop]
     │                                       │
     │  tool_use(location="Paris")           │
     │  tool_use(location="Tokyo")           │
     │──────────────────────────────────────▶│ (Loop executes both tools)
     │                                       │
     │  [tool_result("72F and sunny"),       │ 
     │   tool_result("65F and raining")]     │
     │◀──────────────────────────────────────│ (Returned together in ONE user message)
```

### Implementing Parallel Calls in Code (Applying the Theory)

When the API returns a `tool_use` stop reason, it doesn't just return one tool—it returns an array of them inside `response.content`. To handle this correctly, we gather *all* tool calls from that single turn, execute them, and pack *all* the results into a single list before appending it to `messages`. 

Here is exactly where this fits into our loop from Section 5:

```python
    if response.stop_reason == "tool_use":
        # ... (check for the explicit 'finish' tool) ...
        
        # 1. Extract ALL tool requests the model made in this turn
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        
        # 2. Execute and gather ALL results
        results = []
        for block in tool_use_blocks:
            content_str, is_error = execute_tool_call(block)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content_str,
                "is_error": is_error,
            })

        # 3. Append them together as exactly ONE user turn
        messages.append({"role": "user", "content": results})
```

### [DRY-RUN] The Message State Before and After

To make this completely concrete, let's look at the actual JSON of the `messages` list during this process. 

**Before appending the results**, the message list contains the user's initial request, followed by the assistant asking for two things at once:

```json
[
  {
    "role": "user",
    "content": "What's the weather like in Paris and Tokyo?"
  },
  {
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_paris",
        "name": "get_weather",
        "input": {"location": "Paris"}
      },
      {
        "type": "tool_use",
        "id": "toolu_tokyo",
        "name": "get_weather",
        "input": {"location": "Tokyo"}
      }
    ]
  }
]
```

**After appending the results** using the Python code above, we append exactly **one** new user message that contains an array of both results:

```json
[
  {
    "role": "user",
    "content": "What's the weather like in Paris and Tokyo?"
  },
  {
    "role": "assistant",
    "content": [ ... the two tool calls from above ... ]
  },
  {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_paris",
        "content": "72F and sunny",
        "is_error": false
      },
      {
        "type": "tool_result",
        "tool_use_id": "toolu_tokyo",
        "content": "65F and raining",
        "is_error": false
      }
    ]
  }
]
```

### The "Silent Regression" Bug Explained

A very common mistake developers make is appending a separate user message for *each* tool result, which looks like this:

```json
// INCORRECT: Splitting results into separate turns
[
  { "role": "user", "content": "What's the weather like in Paris and Tokyo?" },
  { "role": "assistant", "content": [ ... two tool calls ... ] },
  { "role": "user", "content": [ { "type": "tool_result", "tool_use_id": "toolu_paris"... } ] },
  { "role": "user", "content": [ { "type": "tool_result", "tool_use_id": "toolu_tokyo"... } ] }
]
```

If you do this, the API won't crash. It is syntactically valid. However, **it silently trains the model to stop making parallel calls.**

Why? Because models learn how to behave from the transcript (the `messages` list). When the model asks for two things at once, but the transcript shows it getting the answers back in separate disconnected turns, the model assumes its parallel request wasn't supported by the system. In future turns, it will "adapt" by making tool calls one at a time, making your agent frustratingly slow. 

If you are ever debugging the question, "Why did my agent stop batching tool calls?", check this exact spot in your code. Ensure all tool results are packed into a single `user` message.

## Key Takeaways for Section 7

One assistant turn can carry several `tool_use` blocks. You must execute all of them and return all their `tool_result` blocks together, in **exactly one** user message. Splitting them across multiple messages is syntactically valid but silently wrong — it trains the model that parallel tools aren't supported, degrading performance over time without ever throwing an error.

*Next: everything so far assumed a plain, blocking request-response call —
here's what changes when tokens arrive incrementally and the model reasons
between tool calls.*

---

# 8: Streaming and Interleaved Thinking

## The Intuition

A blocking call is like sending a letter and waiting for the full reply before you read any of it. Streaming is like a phone call — words arrive as they're spoken, and you can react (or at least render them to a screen) as they come in, instead of staring at a blank page until the other person finishes their entire thought.

## What Changes About the Loop

Streaming itself is not unique to this API — most current providers offer some form of incremental token delivery. What follows is written against Anthropic's specific event names.

To understand what changes, we have to look at how data actually arrives over the network. 

**In a Blocking Call:**
You ask the API for a response. Your code freezes and waits in silence for 5 seconds. Finally, the API returns **one massive, complete JSON object** all at once.

**In a Streaming Call:**
You ask the API for a response. Instantly, the API starts firing dozens of tiny "events" at your code, piece by piece, as the model generates them. 

Here is an example of what those tiny events look like as they arrive one by one over the wire:

```text
Event 1: content_block_start  (The model is starting to speak)
Event 2: content_block_delta  "I "
Event 3: content_block_delta  "will "
Event 4: content_block_delta  "check "
Event 5: content_block_delta  "the weather."
Event 6: content_block_stop   (The model finished its sentence)
Event 7: tool_use_start       (The model decided to use a tool)
Event 8: input_json_delta     "{\"location\": "
Event 9: input_json_delta     "\"Paris\"}"
Event 10: message_stop        (The model is completely done with its turn)
```

The core point is this: **Streaming doesn't change the *logic* of your agent loop.** Whether you wait 5 seconds for the massive object, or you catch 50 tiny events over 5 seconds, the end result is exactly the same. You still read a final `stop_reason`, you still branch on `tool_use` vs `end_turn`, and you still append the exact same data to your `messages` array. What changes is merely *how you get there*.

### Streaming in Code (Applying the Theory)

Instead of manually parsing all those JSON chunk events, almost every agent loop uses the SDK's convenience wrapper. It lets you stream the live text, but critically, it automatically reconstructs the final `Message` object for you so your loop logic doesn't have to change:

```python
with client.messages.stream(model=MODEL, max_tokens=4096,
                             tools=tools, messages=messages) as stream:
    # 1. Yield live tokens to the UI as they arrive
    for text in stream.text_stream:
        print(text, end="", flush=True)
        
    # 2. Wait for the stream to close, then grab the reconstructed message
    response = stream.get_final_message()
    
# 3. Resume your normal loop logic!
if response.stop_reason == "tool_use":
    # ...
```

Streaming is also the practical answer to a very mundane problem: **large `max_tokens` values on a non-blocking call risk hitting HTTP request timeouts** before the model finishes. Once your loop produces long tool inputs or long reasoning, streaming becomes mandatory just to keep the connection alive.

## Interleaved Thinking

On models with adaptive thinking (like Claude 3.7+), the model can reason *between* tool calls within a single multi-step turn. This is called "interleaved thinking." 

Practically, this means a single assistant turn's `content` array can now contain a `thinking` block, then a `tool_use` block, and (after you return the tool result) another `thinking` block before the following action. The model is visibly "thinking out loud" at each decision point.

### [DRY-RUN] The Message State with Thinking Blocks

To see what this actually looks like under the hood, here is the JSON of an assistant message that thought before acting. Notice the `signature` field—this is a cryptographic hash generated by the API:

```json
{
  "role": "assistant",
  "content": [
    {
      "type": "thinking",
      "thinking": "I need to fetch the weather first to answer this.",
      "signature": "sig_01abc123xyz..."
    },
    {
      "type": "tool_use",
      "id": "toolu_01",
      "name": "get_weather",
      "input": {"location": "Paris"}
    }
  ]
}
```

Two critical rules apply to these blocks, and both are easy to get wrong quietly:
1. **Thinking blocks must be passed back unchanged:** When you append this assistant message to your history for the next turn, you cannot edit the `thinking` text. The API uses the `signature` to validate the block's integrity; if you tamper with it, the API will throw a hard 400 error.
2. **Forks drop thinking:** If you ever fork the conversation onto a *different* model (like passing the history to a cheaper model for a sub-task), that model will simply **drop** the thinking blocks it doesn't recognize. It won't error, but that reasoning won't survive the fork.

## Key Takeaways for Section 8

Streaming changes *how* you receive a response, not the loop's branching logic. Always resolve to the same final, accumulated `Message` before making a `stop_reason` decision. Interleaved thinking lets the model reason between tool calls; pass thinking blocks (and their signatures) back unmodified, and expect them to vanish harmlessly if you switch models.

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

### Logging in Code (Applying the Theory)

First, define the function that writes a single step to the file:

```python
import json, time

def log_step(step_num, response, tool_results):
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

Crucially, **where does this go in your loop?** It belongs at the very end of your iteration step, right after you've collected all the tool results, but before the loop repeats for the next turn:

```python
# ... inside your main loop from Section 5 ...

    response = client.messages.create(...)
    
    if response.stop_reason == "end_turn":
        log_step(step, response, tool_results=[])
        break
        
    if response.stop_reason == "tool_use":
        # ... execute tools and collect results ...
        
        # Log the step with the results we just got back!
        log_step(step, response, tool_results=results)
        
        messages.append({"role": "user", "content": results})
```

### [DRY-RUN] Inside `trajectory.jsonl`

If you open the resulting `trajectory.jsonl` file after the first step, you will see exactly one long string of JSON. If you format it for readability, it looks like this:

```json
{"step": 0, "timestamp": 1718293041.5, "stop_reason": "tool_use", "input_tokens": 152, "output_tokens": 48, "assistant_content": [{"type": "tool_use", "id": "toolu_paris", "name": "get_weather", "input": {"location": "Paris"}}], "tool_results": [{"type": "tool_result", "tool_use_id": "toolu_paris", "content": "72F and sunny", "is_error": false}]}
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

Think of this like **three ways to get a pizza**: cook it yourself from raw ingredients (Manual loop), order a meal-kit where someone gives you pre-portioned ingredients and you bake it (Tool Runner), or order delivery where someone else cooks it and brings it to your door (Agent SDK). 

Here is a visual breakdown of what you actually have to write in each approach:

```text
  [1. Manual Loop]       [2. Tool Runner]        [3. Agent SDK]
     You Write               You Write             You Write
   ┌────────────┐          ┌────────────┐        ┌────────────┐
   │   Tools    │          │   Tools    │        │   Prompt   │
   ├────────────┤          ├┈┈┈┈┈┈┈┈┈┈┈┈┤        ├┈┈┈┈┈┈┈┈┈┈┈┈┤
   │    Loop    │          │  SDK Loop  │        │  SDK Loop  │
   ├────────────┤          ├────────────┤        ├────────────┤
   │  Mem/Logs  │          │  Mem/Logs  │        │ SDK Tools  │
   └────────────┘          └────────────┘        └────────────┘
   (Full Control)       (SDK Automation)     (Batteries Included)
```

None of these is "the right one" — they trade control for convenience along a real spectrum, and the right choice depends entirely on how much of the process you actually need to see and steer.

## The Three Real Options

| # | Approach | You write | Who supplies the loop | Tools available | Reach for this when |
|---|---|---|---|---|---|
| 1 | **Manual loop** | The `while` loop yourself | You do — full ownership, full visibility | Only tools you define | You want to own the *entire* loop, or want zero framework dependency |
| 2 | **Tool Runner** (SDK helper) | Just the tool functions, decorated | The SDK — it drives the request → execute → feed-back cycle for you | Only tools you define | You want a custom-tool agent without hand-writing the `while` loop |
| 3 | **Claude Agent SDK** (Separate product) | A prompt plus configuration options | The SDK — it supplies the full Claude Code harness | Built-in file read/write/edit, bash, grep, web search, plus MCP and subagents | You want a batteries-included coding/filesystem agent and don't need to define your own tools from scratch |

### Option 2 in Code: The Tool Runner (Applying the Theory)

Instead of the `while` loop we wrote in Section 5, you define your tools, and tell the SDK to run the loop for you. The SDK handles formatting the `tool_result` array and appending it to messages automatically.

```python
# 1. Define your tools
def get_weather(location: str): ...
def read_file(path: str): ...

# 2. Let the SDK handle the loop!
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=4096,
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    # We pass the functions directly, the SDK extracts their schemas and runs the loop
    tool_choice={"type": "auto"},
    tools=[get_weather, read_file] # Notice these are the actual functions, not JSON schemas!
)
# The SDK handles catching errors, sending tool_results back, and repeating the cycle.
```

### Option 3 in Code: The Agent SDK

The Claude Agent SDK is a completely different library (`claude-agent`). It has built-in tools (like bash and file editing) so you don't even need to define your own.

```python
from claude_agent import Agent

# You just provide a prompt and let it loose on your filesystem
agent = Agent(
    tools=["bash", "file_editor"], 
    system_prompt="You are a helpful coding assistant."
)
agent.run("Find the error in my python script and fix it.")
```

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

```json
[
  { "role": "user", "content": "How many words are in report.txt? It's in the current directory." } 
]
```

**Step 1 — API call 1.** Input = 600 (fixed prefix) + 20 (user msg) = **620 tokens**. The model, guessing at a filename, responds with a short text aside plus a `tool_use` block:

```json
// The API returns this to your loop:
{
  "role": "assistant",
  "content": [
    { "type": "text", "text": "Let me look for that file." },
    { "type": "tool_use", "id": "toolu_01", "name": "read_file", "input": {"path": "reports.txt"} }
  ]
}
```

*Applying the Code:* Back in Python, your loop hits the `if response.stop_reason == "tool_use":` block, and runs `execute_tool_call("read_file", {"path": "reports.txt"})`. This hits a `FileNotFoundError`. Per Section 6, this becomes an error `tool_result`, not a crash. You append it:

```json
// The state of your messages list after Step 1 finishes:
[
  { "role": "user", "content": "How many words are in report.txt? It's in the current directory." },
  { "role": "assistant", "content": [ ... text block ..., ... tool_use block ... ] },
  { "role": "user", "content": [
      { "type": "tool_result", "tool_use_id": "toolu_01", "content": "Error: reports.txt not found.", "is_error": true }
    ] 
  }
]
```

**Step 2 — API call 2.** Input = 620 + 25 (assistant turn 1) + 20 (error result) = **665 tokens**. The model sees its own error in the transcript and self-corrects on the very next step, exactly as Section 6 predicted — no extra prompting needed:

```json
// The API returns:
{
  "role": "assistant",
  "content": [
    { "type": "tool_use", "id": "toolu_02", "name": "read_file", "input": {"path": "report.txt"} }
  ]
}
```

> [!NOTE]
> **How did it know the correct spelling without running `ls`?**
> Because the stateless API receives the *entire* `messages` array every single time, the model can simply look up at the very first message where you explicitly typed `"How many words are in report.txt?"`. It recognizes its own typo and fixes it. If you hadn't provided the filename in the prompt, the agent would indeed be stuck here unless you had given it a `list_directory` tool.

*Applying the Code:* Your loop runs `execute_tool_call` again. `read_file("report.txt")` succeeds this time, returning the file's contents. Let's say the report is **200 tokens** long. Your loop appends it:

```json
// End of Step 2:
[
  ... previous history ...,
  { "role": "assistant", "content": [ ... tool_use_2 ... ] },
  { "role": "user", "content": [ { "type": "tool_result", "content": "<200-token file content>", "is_error": false } ] }
]
```

**Step 3 — API call 3.** Input = 665 + 15 + 200 = **880 tokens**. The model now calls `word_count`. Here is the detail worth stopping on: to pass the file's content *into* `word_count`, the model must **re-emit that entire 200-token string as the tool's input argument** — it cannot simply point at what `read_file` already returned.

```json
{
  "role": "assistant",
  "content": [
    { "type": "tool_use", "id": "toolu_03", "name": "word_count", "input": {"text": "<the same 200-token content, re-typed by the model>"} }
  ]
}
```

**The file content now exists twice in the transcript** — once as `read_file`'s `tool_result`, once again as `word_count`'s `tool_use` input. That's not a mistake in this trace; it's the honest, measurable cost of chaining two tools through the model. 

*Applying the Code:* Your Python loop runs `execute_tool_call` one last time. `word_count` executes locally against that string and returns `"142 words"` (5 tokens), which gets appended.

**Step 4 — API call 4.** Input = 880 + 205 + 5 = **1,090 tokens**. The model produces its final answer:

```json
{
  "role": "assistant",
  "content": [ { "type": "text", "text": "The report contains 142 words." } ]
}
// stop_reason = "end_turn"
```

*Applying the Code:* Your Python loop hits `if response.stop_reason == "end_turn":`, logs the final step, and safely `break`s out of the loop.

## The Totals, and the One Thing Worth Remembering

```
Total input tokens across 4 calls:  620 + 665 + 880 + 1,090 = 3,255
Total completion tokens:             25 +  15 + 205 +   10 =   255
```

> [!IMPORTANT]
> **The Hidden Cost of Tool Chaining**
> Because the API is stateless, it has no memory. It only knows what is in the `messages` array. If `report.txt` was 10,000 tokens long, here is what happens to your context window:
> 1. In Step 2, you append the file contents to the array as a `tool_result` (10,000 tokens).
> 2. In Step 3, the model must re-type the entire file as the input argument for `word_count`. This gets appended as a `tool_use` JSON block (another 10,000 tokens).
>
> By Step 4, your `messages` array contains **20,000 tokens** of the exact same text! The model had to waste time generating it, and you have to pay for it sitting in the context window. 
>
> This is not a bug to route around inside this chapter's loop — it's the honest price of standard tool chaining. It's exactly why **Chapter 8** introduces Bash/Script execution tools. If the model can just run `cat report.txt | wc -w` in a terminal, the data flows locally. The 10,000 tokens never enter the API's context window, solving this massive duplication problem entirely.

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

| Missing capability | Symptom without it | Code Preview (How we'll fix it) | Where it's built |
|---|---|---|---|
| **Memory across sessions** | Every run starts from zero; nothing learned in run 1 carries into run 2 | `db.load_history(user_id)` before loop | Chapter 9 |
| **Verification beyond `end_turn`** | The model's own claim of success is the only signal | `if verify(result): break` | Chapter 6 |
| **Permissions / blast-radius** | Any tool this loop can call, it calls freely without asking | `if tool.unsafe and not approve():` | Chapter 16 |
| **Persistence across a crash** | Kill the process at step 30 of 60 and the entire run is gone | `save_state(step)` in the loop | Chapter 12 |
| **Formal evals** | You can *feel* if it went well; you cannot *measure* regressions | `assert evaluate(trajectory) > 0.9` | Chapter 14 |
| **Context management** | Nothing ever compacts, evicts, or externalizes | `messages = summarize(messages)` | Chapter 4 |

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

| I want to know... | Reach for | Key fact (Code Reminder) |
|---|---|---|
| What actually holds the conversation's state | Section 2 | The `messages = []` array itself — the API is stateless, nothing persists |
| Why `content[0].text` sometimes crashes | Section 3 | Check `if response.stop_reason == "tool_use":` first; it implies no text |
| How a tool call actually gets executed | Section 4 | A dict lookup: `dispatch_table[name](**args)`. The model never runs code |
| Why my loop never stops | Section 5 | `end_turn` isn't enough; add a `for _ in range(max):` iteration guard |
| What to do when a tool throws | Section 6 | Catch it and return `{"is_error": true, "content": "..."}`. Never crash |
| Why my agent stopped batching tool calls | Section 7 | Pack all results into a single `{"role": "user", "content": [results]}` message |
| What changes with streaming | Section 8 | Use `stream.get_final_message()` before running your standard loop logic |
| Why I should log every step | Section 9 | The `trajectory.jsonl` file is your debugger today, and your eval dataset later |
| Which of the three SDK options to use | Section 10 | Manual `while` loop (control) vs Tool Runner (automation) vs Agent SDK (built-in tools) |
| Why chaining two tools costs more than it looks | Section 11 | Duplicate text: 10k tokens in the `tool_result` + 10k re-typed in the `tool_use` |
| What this loop still can't do | Section 12 | Memory, verification, permissions, persistence, evals, and context limits |

**Connection forward:** Chapter 3 goes back to the tool definitions this
chapter treated as given — naming, schema shape, granularity, error-message
wording — and asks the question this chapter only gestured at: what actually
makes one tool design good and another one quietly sabotage the model calling
it correctly.
