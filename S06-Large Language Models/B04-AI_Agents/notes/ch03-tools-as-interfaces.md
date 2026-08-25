# Chapter 3: Tools as Interfaces

## Table of Contents

1. [Why This Chapter Exists](#1-why-this-chapter-exists)
2. [The Schema Is a UI Whose User Is a Model](#2-the-schema-is-a-ui-whose-user-is-a-model)
3. [Granularity: Consolidate Over Fragment](#3-granularity-consolidate-over-fragment)
4. [Return-Value Design: Give the Model What It Needs Next](#4-return-value-design-give-the-model-what-it-needs-next)
5. [Error Messages as Instructions, Not Postmortems](#5-error-messages-as-instructions-not-postmortems)
6. [Structured Output and Schema-Constrained Generation](#6-structured-output-and-schema-constrained-generation)
7. [Idempotency, Side Effects, and the Destructive Flag](#7-idempotency-side-effects-and-the-destructive-flag)
8. [Dry-Run: The Token Bill of a 40-Tool Library Across a 20-Step Loop](#8-dry-run-the-token-bill-of-a-40-tool-library-across-a-20-step-loop)
9. [Tool Selection Failures as the Library Grows](#9-tool-selection-failures-as-the-library-grows)
10. [Model Context Protocol (MCP), In Depth](#10-model-context-protocol-mcp-in-depth)
11. [Advanced Tool Use: Search, Deferred Loading, Programmatic Calling](#11-advanced-tool-use-search-deferred-loading-programmatic-calling)
12. [What Good Tool Design Still Can't Fix](#12-what-good-tool-design-still-cant-fix)
13. [Key Takeaways + Master Decision Table](#13-key-takeaways--master-decision-table)

---

# 1: Why This Chapter Exists

## What This Chapter Is Really About

Chapter 2 built the loop and treated the tools inside it as given — a
dictionary from name to function, a list of JSON schemas, done. That was the
right call at the time; you cannot design a good interface before you have a
consumer for it. Now you do. This chapter goes back to those tool definitions
and asks the question Chapter 2 skipped: what makes one tool schema good and
another one quietly sabotage the exact same model, running the exact same
loop, on the exact same task?

The claim this chapter defends, stated once so it can be referred back to
throughout: **a tool schema is a user interface, and its user happens to be a
language model instead of a human.** Every intuition you already have about
good API and UI design — clear naming, sensible defaults, error messages that
tell you what to do next, not overwhelming the user with two hundred menu
items — transfers almost unchanged. What changes is *who* is reading the
interface and *how* they fail when it's bad. A human facing a confusing form
gets annoyed and asks a colleague. A model facing a confusing tool schema
doesn't get annoyed — it silently guesses, calls the wrong tool with
plausible-looking arguments, and produces an error three steps later that
looks like a completely different bug. Anthropic's own applied-AI team,
writing about the tools they ship inside Claude Code and their MCP
connectors, put it directly: tools are "a fundamentally new kind of software
that requires new tools and new intuitions to develop well" because "unlike
traditional software... agent-computer interfaces... require exhaustive
testing with real models" — a contract between deterministic code and a
non-deterministic reader, not between two deterministic systems.

**Example: The Schema as a UI**
If you give a human a text box labeled `Update`, they might be confused but can ask questions. If you give a model a "Bad UI" schema, it doesn't ask questions; it just hallucinates whatever JSON string it thinks belongs there.

**A "Bad UI" Tool (Vague, no constraints)**
```json
{
  "name": "update_db",
  "description": "Updates the database.",
  "input_schema": {
    "type": "object",
    "properties": {
      "data": {"type": "string"}
    }
  }
}
```

**A "Good UI" Tool (Anthropic Format)**
```json
{
  "name": "set_user_status",
  "description": "Updates a user's active status. Do not use for passwords.",
  "input_schema": {
    "type": "object",
    "properties": {
      "user_id": {"type": "string", "description": "Must be format USR-XXXX"},
      "status": {"type": "string", "enum": ["active", "suspended"]}
    }
  }
}
```

**A "Good UI" Tool (OpenAI/Ollama Format)**
```json
{
  "type": "function",
  "function": {
    "name": "set_user_status",
    "description": "Updates a user's active status. Do not use for passwords.",
    "parameters": {
      "type": "object",
      "properties": {
        "user_id": {"type": "string", "description": "Must be format USR-XXXX"},
        "status": {"type": "string", "enum": ["active", "suspended"]}
      }
    }
  }
}
```
*Notice how both formats ultimately rely on the exact same JSON Schema `properties` to enforce constraints (like `enum`) and prevent model hallucination.*

*Note on formats: Everything in this chapter will be demonstrated against both major industry standards: Anthropic's wire format (using `input_schema` and `tool_result`, connecting via `AnthropicBedrockMantle`) AND the standard OpenAI format (using `parameters` and `role: "tool"`, connecting via a local Ollama instance). The core principles — clear names, right-sized granularity, lean return values, actionable errors — remain exactly the same regardless of which SDK you are using. Whenever we look at a JSON payload, we will point out how it looks in both systems.*

## Connection Back to Chapter 1's Failure Modes

Two of the three failure modes named in Chapter 1 — victory declaration bias
and context anxiety — are partly *tool-design* failures wearing a different
name. A model that "context anxiety"-re-reads a file it already has in
context is often reacting to a `read_file` tool that returns an opaque blob
with no indication of what's already been seen. A model that declares victory
prematurely is sometimes trusting a tool result that itself lied by omission
— a `write_file` tool that returns `{"status": "ok"}` with no detail to
verify against. Fixing the loop (Chapter 2) doesn't fix either of these;
fixing the tools does. That is the entire economic case for a chapter this
narrow.

*Next: the central metaphor for the rest of this chapter — reading a schema
the way a model actually has to.*

---

# 2: The Schema Is a UI Whose User Is a Model

## The Intuition

Imagine handing a new hire a paper form with a field labeled `id` and no
further description, sitting next to another field labeled `type`. A human
new hire pauses, looks around the office, and asks someone "id of what,
exactly?" A model gets no such pause. It has exactly one shot at filling in
that field correctly, informed only by the field's name, its JSON-Schema
type, and whatever the tool's top-level `description` string told it — and it
will confidently produce *something*, because refusing to guess is not a
behavior anyone trained into it as a default. Every ambiguity you leave in a
schema becomes a coin flip the model makes on your behalf, silently, inside a
single forward pass you cannot see.

This reframes "write a good docstring" (something every engineer already
half-believes they should do) into something sharper: **the tool description
is the entire specification the model will ever see.** There is no README,
no Stack Overflow thread, no colleague at the next desk. If the description
doesn't say that `user_id` must be the internal UUID and not the
user-facing email, the model will eventually pass an email, because nothing
told it not to.

## Naming and Namespacing

Anthropic's own guidance, refined through building and shipping their
internal Slack and Asana integrations, converges on a few concrete rules.
Name tools the way you'd name a well-factored function: `get_current_weather`
reads unambiguously; `weather` does not, especially once a second tool named
`weather_v2` or `check_weather` shows up beside it. When an agent has access
to *multiple* systems that could each plausibly have a `search` tool — a
ticketing system, a wiki, a CRM — namespace by prefixing with the system and
grouping by resource: `asana_projects_search`, `asana_users_search`,
`jira_search`, rather than five same-named `search` tools distinguished only
by which server registered them. Anthropic's engineering team specifically
notes that even the *choice between prefix-style and suffix-style*
namespacing (`asana_search_projects` vs `search_asana_projects`) produced
measurable differences in tool-selection accuracy on their internal
evaluations — a reminder that this isn't taste, it's an empirical question
you should be willing to actually measure against your own tool set rather
than assume.

parameter names deserve the same discipline. `user` is ambiguous between "a
user object," "a username string," and "a user ID" — `user_id` is not. This
sounds trivial in isolation; it stops being trivial the moment a model has
eleven tools in context and three of them accept something loosely called
`id`.

### Code Example: Naming and Namespacing

Notice how the `properties` block (which is identical whether you use Anthropic's `input_schema` or OpenAI's `parameters`) changes the model's accuracy just by fixing the names.

```json
// BAD: Ambiguous names
"name": "search",
"properties": {
  "user": {"type": "string"} 
}

// GOOD: Namespaced tools and explicit variables
"name": "asana_search_users",
"properties": {
  "user_id": {"type": "string"}
}
```

## Description Length and What the Model Can Infer

A description should do for the model what onboarding documentation does for
a new engineer: state things that are true but not derivable from the name
alone. "Search Asana tasks" adds nothing beyond the tool's own name. "Search
Asana tasks by assignee, due date, or project. Returns up to 50 matches;
use `cursor` from a previous response to page further; prefer narrow filters
over broad ones — an unfiltered search on a large workspace will be
truncated and cost you a wasted call" tells the model something it could not
have guessed: the pagination contract, the truncation behavior, and a
failed attempt. The gain compounds with the size of the tool library — one
vague description is a minor cost with three tools in context; it is a
serious cost with thirty, because on turn one the model is deciding which of
those thirty best fits, and a vague description makes every tool it's
attached to look slightly more interchangeable than the others.

### Code Example: The Tool Description

This top-level string is the *only* onboarding document the model ever reads.

```json
// BAD: Useless description
"description": "Search Asana tasks"

// GOOD: Onboarding documentation for the model
"description": "Search Asana tasks by assignee, due date, or project. Returns up to 50 matches; use `cursor` from a previous response to page further; prefer narrow filters over broad ones — an unfiltered search on a large workspace will be truncated and cost you a wasted call."
```

Anthropic reports that on the SWE-bench Verified coding benchmark, careful,
iterative refinement of tool descriptions and argument names — with no change
to the underlying tools' *capabilities* — measurably reduced the model's
error rate and contributed to a state-of-the-art result at the time. The
tools did not get more powerful. The interface got clearer. That distinction
is the entire argument for taking this chapter seriously instead of treating
tool descriptions as an afterthought written once and never revisited.

## Argument Shape

Prefer flat, explicit parameters over deeply nested or overloaded ones
whenever the underlying operation allows it. A `filters: {status: "open",
assignee: "me", ...}` nested object asks the model to correctly construct
JSON *inside* JSON with no schema validation on the inner shape (JSON Schema
validates the outer `filters` object's declared properties, but a model
still has to get the nesting exactly right on every call). A flatter
`status`, `assignee` at the top level of `input_schema.properties` is both
easier for the model to fill in correctly and easier for you to validate.
Nesting still has a place — grouping five related optional fields that only
ever travel together is a legitimate use — but it should be a deliberate
choice, not an accident of mirroring your internal database schema onto the
tool definition.

### Code Example: Flat vs Nested Arguments

Nested objects force the model to construct raw JSON inside the arguments, increasing the chance of syntax errors. Flat properties are validated perfectly by the schema.

```json
// BAD: Deeply nested object
"properties": {
  "filters": {
    "type": "string", 
    "description": "A JSON string like {'status': 'open', 'assignee': 'me'}"
  }
}

// GOOD: Flat, explicit schema parameters
"properties": {
  "status": {"type": "string", "enum": ["open", "closed"]},
  "assignee": {"type": "string", "description": "The assignee's user_id"}
}
```



## Key Takeaways for Section 2

A tool's name, its parameter names, and its description string are the
*entire* specification a model has — there is no fallback channel for it to
ask a clarifying question. Namespace tools by system and resource when
multiple similar tools coexist; write descriptions that state what isn't
derivable from the name (pagination, truncation, when to prefer this tool
over a similar one); and keep argument shapes flat unless nesting genuinely
groups related fields. None of this requires touching what the tool *does* —
Anthropic's SWE-bench result came entirely from clarifying what the tool
*says*.

*Next: a single tool that does more, or many tools that each do less — which
one actually serves the model better?*

---

# 3: Granularity: Consolidate Over Fragment

## The Problem

When building normal APIs, we usually create small, single-purpose tools like `list_users`, `list_events`, or `create_event`. They are clean and do one thing well. But if you give these tiny tools to an AI agent, you actually make the agent worse. 

Why? Because every single tool is a new choice the model has to make. If it has to use five tools to book a meeting, that means five chances to make a mistake, and five expensive round-trips to the server (burning tokens every time), when a human would just say "book a meeting."

## The Intuition

Think of the difference between handing a new employee a fully itemized
parts catalog and a work order form. The parts catalog is more *composable*
in principle — you could build anything from those parts — but for the one
task actually in front of you ("schedule a meeting with Alex next Tuesday
afternoon"), the work order form is strictly better: one field for who, one
for when, one submit action, and the assembly of primitives underneath it
happens in code you control, not in five separate guesses the model has to
get right in sequence.

## The Guidance

Anthropic's advice, based on building their own tools, is simple: combine common multi-step tasks into a single "macro" tool, instead of making the model call several small tools to get the job done.

| Instead of (fragmented) | Prefer (consolidated) | Why |
|---|---|---|
| `list_users`, `list_events`, `create_event` | `schedule_event(attendees, time_range, title)` | One decision, one call, no ordering to get wrong |
| `read_logs` (returns everything) | `search_logs(query, time_range)` | Filtering happens server-side, not by the model reading and discarding |
| `get_customer_orders`, `get_customer_tickets`, `get_customer_profile` | `get_customer_context(customer_id)` bundling all three | One round trip instead of three; the model gets the full picture without deciding to ask three separate questions |

### Code Example: Consolidating Endpoints

If you give the model three separate tools, it has to decide to call them in parallel or sequentially, burning tokens either way. Give it one "macro" tool that does the assembly for it.

**BAD UI: Fragmented**
```json
[
  {
    "type": "function",
    "function": {
      "name": "get_customer_orders",
      "parameters": { "type": "object", "properties": { "customer_id": {"type": "string"} }, "required": ["customer_id"] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "get_customer_tickets",
      "parameters": { "type": "object", "properties": { "customer_id": {"type": "string"} }, "required": ["customer_id"] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "get_customer_profile",
      "parameters": { "type": "object", "properties": { "customer_id": {"type": "string"} }, "required": ["customer_id"] }
    }
  }
]
```

**GOOD UI: Consolidated (OpenAI format)**
One call, one round-trip, one block of unified context returned.
```json
{
  "type": "function",
  "function": {
    "name": "get_customer_context",
    "description": "Fetches a unified view of a customer including their profile, recent orders, and open support tickets.",
    "parameters": {
      "type": "object",
      "properties": {
        "customer_id": {"type": "string"}
      },
      "required": ["customer_id"]
    }
  }
}
```

### The Messages Array (Dry Run)

Here is how the token usage and network round-trips explode when using fragmented tools compared to a consolidated macro tool.

**1. Using Fragmented Tools (3 Round Trips)**
```json
[
  {"role": "user", "content": "Tell me everything about customer CUST-99."},
  {"role": "assistant", "content": null, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_customer_profile", "arguments": "{\"customer_id\": \"CUST-99\"}"}}]},
  {"role": "tool", "tool_call_id": "call_1", "content": "{\"name\": \"Alice\", \"email\": \"alice@example.com\"}"},
  {"role": "assistant", "content": null, "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "get_customer_orders", "arguments": "{\"customer_id\": \"CUST-99\"}"}}]},
  {"role": "tool", "tool_call_id": "call_2", "content": "[{\"order_id\": \"ORD-123\", \"total\": 45.00}]"},
  {"role": "assistant", "content": null, "tool_calls": [{"id": "call_3", "type": "function", "function": {"name": "get_customer_tickets", "arguments": "{\"customer_id\": \"CUST-99\"}"}}]},
  {"role": "tool", "tool_call_id": "call_3", "content": "[]"}
]
// Total: 3 separate model invocations, 3 network round-trips.
```

**2. Using a Consolidated Tool (1 Round Trip)**
```json
[
  {"role": "user", "content": "Tell me everything about customer CUST-99."},
  {"role": "assistant", "content": null, "tool_calls": [{"id": "call_4", "type": "function", "function": {"name": "get_customer_context", "arguments": "{\"customer_id\": \"CUST-99\"}"}}]},
  {"role": "tool", "tool_call_id": "call_4", "content": "{\"profile\": {\"name\": \"Alice\", \"email\": \"alice@example.com\"}, \"orders\": [{\"order_id\": \"ORD-123\", \"total\": 45.00}], \"tickets\": []}"}
]
// Total: 1 model invocation, 1 network round-trip. Fast and reliable.
```

### Backend Implementation Example

Here is how you orchestrate the consolidation on the backend. You do the heavy lifting in Python so the LLM doesn't have to guess the order of operations.

```python
import json

def get_customer_context(customer_id: str) -> str:
    """Tool: Fetches a unified view of a customer."""
    
    # 1. Fetch data from different internal systems
    # (In a real app, you could even do these fetches in parallel to save time!)
    profile = db.get_profile(customer_id)
    orders = shopify_api.get_recent_orders(customer_id)
    tickets = zendesk_api.get_open_tickets(customer_id)
    
    # 2. Assemble it into a single clean dictionary
    unified_context = {
        "profile": profile,
        "recent_orders": orders,
        "open_tickets": tickets
    }
    
    # 3. Return the consolidated view as a JSON string to the model
    return json.dumps(unified_context)
```

## The Actual Rule: "One Task" in a Human's Head

The code above is not an argument for always using fewer tools. It's more specific than that.

The actual rule is: **combine the steps a human would think of as "one task," and keep truly different tasks as completely separate tools.**

Here is why `schedule_event` is the right consolidation target: when you ask someone to "schedule a meeting with Alex next Tuesday," they do not think of it as three steps — check who is free, find a slot, create the event. That whole bundle is one action in their head. So from the agent's point of view, there should be one tool call for it. The assembly of the steps underneath happens in code you control, not in three separate guesses the model has to get right in sequence.

By contrast, `search_logs` and `delete_logs` should stay as completely separate tools — even though they both touch the same logs and sound very similar. The reason is not that they are "different tasks" in an abstract sense. It is that one of them is **safe to call just to look around**, and the other **permanently destroys data** and must never be called by accident. Combining them into one tool with a `mode` parameter (like `logs_tool(mode="delete")`) would make it far too easy for a misread parameter to cause irreversible damage. Keep dangerous operations physically separate, with their own names, their own descriptions, and their own warning labels.

## The Trade-off, Stated Precisely

When you consolidate small tools into one macro tool, you are trading away flexibility in exchange for fewer decision points. Fewer decision points means the model makes fewer mistakes and fewer wasted round-trips. But it also means that if a future task needs only *part* of what the macro tool does, you cannot get just that part — you pay for the whole thing.

To find the right balance, **do not guess — look at your agent's actual conversation logs.** If you see the model calling the same three tools in the same order on virtually every run, that is a strong signal those three should be merged into one. If you see the model only occasionally needing one of the three, merging would hurt more than it helps.

## The Read vs. Write Trade-off (When to stay Granular)

This does not mean "always use fewer tools" as a blind rule. The industry consensus points to a critical distinction: **Read (Observation) vs. Write (Mutation)**.

1. **For Read-Only Data Fetching:** Consolidation is almost always better. If the agent needs to look at a user's profile, tickets, and orders, combining them into one `get_customer_context` tool saves tokens, reduces round-trips, and prevents the agent from forgetting to check one of the sources.

2. **For Complex Mutations (Writes):** You must stick to **Atomic, Granular tools**. If a task requires the agent to "Create a folder, move a file into it, and then rename the file", you should *not* create a `do_all_file_ops` macro tool. Why? Because if the folder creation fails, or the file ID changes, the agent needs to **observe that failure** immediately and replan. 

When an agent attempts a complex, multi-step mutation in one massive tool call, it cannot "see" the intermediate state of the system. This leads to **"plan corruption"**—subsequent steps fail because they rely on assumptions from earlier steps that didn't execute exactly as expected. For writes, force the agent to execute one atomic step, observe the result, and then take the next step.

## Key Takeaways for Section 3

For data gathering (reads), consolidate tools around what a human would call "one task" to reduce context bloat and network round-trips. For complex system changes (writes), keep tools atomic and granular to preserve the agent's critical "thought-action-observation" loop and prevent plan corruption.

*Next: once a tool call succeeds, what should it actually hand back — and why
is "the whole record" almost always the wrong answer?*

---

# 4: Return-Value Design: Give the Model What It Needs Next

## The Intuition

A tool should only return exactly what the model needs to see next. Remember from Chapter 2: every single word a tool returns gets added to the chat history and sent back to the model on *every single future turn*. If your tool returns 8 KB of raw JSON when the model only needed to know a single status field, you aren't being "helpful"—you are just wasting money and tokens by bloating the context window.

## Verbosity as a Parameter, Not a Fixed Choice

Anthropic's own worked example (from tools built for Claude Code and internal
integrations) exposes a `response_format` enum with `"concise"` and
`"detailed"` variants on the *same* tool, letting the calling agent choose
per call:

```
"detailed" response (includes full metadata, needed when the result
feeds a later tool call that requires an ID):
  { "id": "task_9f2a", "title": "Fix login bug", "status": "open",
    "assignee": "user_442", "created": "2026-07-30T14:02:00Z",
    "project": "proj_11", "labels": ["bug", "auth"], ... }
  ≈ 206 tokens

"concise" response (same task, when only a human-readable summary
is needed for the model to reason about, not act on further):
  "Fix login bug (open, assigned to Alex)"
  ≈ 72 tokens
```

### Code Example: Verbosity Parameter

There are two parts to this: defining the tool schema (so the model knows the option exists) and the model actually making the call.

**1. The Tool Schema Definition**
Here is how you fully define the tool in your codebase so the model knows it can choose verbosity. Notice how the inner `properties` block is exactly the same, but the outer structure matches the specific API.

**Anthropic format:**
```json
{
  "name": "get_ticket",
  "description": "Fetches a customer support ticket.",
  "input_schema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "string",
        "description": "The ID of the ticket"
      },
      "response_format": {
        "type": "string",
        "enum": ["concise", "detailed"],
        "description": "Use 'concise' for a summary, or 'detailed' if you need the full metadata to pass to another tool."
      }
    },
    "required": ["task_id"]
  }
}
```

**OpenAI / Ollama format:**
```json
{
  "type": "function",
  "function": {
    "name": "get_ticket",
    "description": "Fetches a customer support ticket.",
    "parameters": {
      "type": "object",
      "properties": {
        "task_id": {
          "type": "string",
          "description": "The ID of the ticket"
        },
        "response_format": {
          "type": "string",
          "enum": ["concise", "detailed"],
          "description": "Use 'concise' for a summary, or 'detailed' if you need the full metadata to pass to another tool."
        }
      },
      "required": ["task_id"]
    }
  }
}
```

**2. The Model's Tool Call (What the model actually returns)**
When the model decides to use the tool, it doesn't return the schema definition above. It returns the actual values! 
```json
{
  "name": "get_ticket",
  "arguments": {
    "task_id": "ticket_123",
    "response_format": "concise"
  }
}
```

The concise form costs roughly a third of the detailed one — a real,
measured 65% reduction on that one call, and it compounds across every
subsequent call in the run the way Section 7's growing tail does.

### The Messages Array (Dry Run)

To understand why verbosity matters, let's look at the `messages` array for an agent investigating a customer issue. We will show how the data changes in the actual context window for both Anthropic and OpenAI formats.

**1. If the tool only returns `detailed` JSON (Context Window Explosion)**

*OpenAI Format Example:*
```json
[
  {"role": "user", "content": "Why is ticket 123 delayed?"},
  {
    "role": "assistant", 
    "content": null,
    "tool_calls": [{"id": "call_abc1", "type": "function", "function": {"name": "get_ticket", "arguments": "{\"task_id\": \"123\"}"}}]
  },
  {
    "role": "tool", 
    "tool_call_id": "call_abc1",
    "content": "{\"id\": 123, \"status\": \"delayed\", \"created_at\": \"2026-07-30\", \"updated_at\": \"...\", \"description\": \"...\", \"comments\": [...huge array...], \"metadata\": {...}}"
  }
]
// Total context so far: ~1,500 tokens of mostly useless JSON noise just for one call.
```

*Anthropic Format Example:*
```json
[
  {"role": "user", "content": "Why is ticket 123 delayed?"},
  {
    "role": "assistant", 
    "content": [{"type": "tool_use", "id": "toolu_abc1", "name": "get_ticket", "input": {"task_id": "123"}}]
  },
  {
    "role": "user", 
    "content": [{"type": "tool_result", "tool_use_id": "toolu_abc1", "content": "{\"id\": 123, \"status\": \"delayed\", \"created_at\": \"2026-07-30\", \"updated_at\": \"...\", \"description\": \"...\", \"comments\": [...huge array...], \"metadata\": {...}}"}]
  }
]
// Total context so far: ~1,500 tokens. The model is flooded with data it didn't ask for.
```

**2. If the model requests `response_format: "concise"` (Clean Context)**

Notice how the model explicitly passes the `"concise"` parameter, and the tool returns a tiny, human-readable string instead of a huge JSON blob.

*OpenAI Format Example:*
```json
[
  {"role": "user", "content": "Why is ticket 123 delayed?"},
  {
    "role": "assistant", 
    "content": null,
    "tool_calls": [{"id": "call_abc2", "type": "function", "function": {"name": "get_ticket", "arguments": "{\"task_id\": \"123\", \"response_format\": \"concise\"}"}}]
  },
  {
    "role": "tool", 
    "tool_call_id": "call_abc2",
    "content": "Ticket 123 is delayed due to part shortage. Customer ID: cust_99."
  }
]
// Total context so far: ~45 tokens. The history stays perfectly clean.
```

*Anthropic Format Example:*
```json
[
  {"role": "user", "content": "Why is ticket 123 delayed?"},
  {
    "role": "assistant", 
    "content": [{"type": "tool_use", "id": "toolu_abc2", "name": "get_ticket", "input": {"task_id": "123", "response_format": "concise"}}]
  },
  {
    "role": "user", 
    "content": [{"type": "tool_result", "tool_use_id": "toolu_abc2", "content": "Ticket 123 is delayed due to part shortage. Customer ID: cust_99."}]
  }
]
// Total context so far: ~45 tokens. The model is vastly less likely to get confused on turn 10.
```

### Implementation Code

Here is how you actually write the backend Python code to handle that choice:

```python
def get_ticket(ticket_id: str, response_format: str = "concise"):
    # 1. Fetch the giant record from your database
    ticket_record = db.fetch_ticket(ticket_id)
    
    # 2. Return the massive JSON object ONLY if explicitly asked
    if response_format == "detailed":
        return json.dumps(ticket_record)
        
    # 3. Otherwise, return a tiny, human-readable summary
    summary = f"Ticket {ticket_id} is {ticket_record['status']}. Assigned to {ticket_record['assignee']}."
    return summary
```

## Truncation With a Continuation Handle, Not a Silent Cliff

If a tool returns a massive amount of text (like reading a huge file or database), you usually have to cut it off (truncate it) to save tokens. But **never cut it off silently**. If you just chop the text, the model will assume it saw the whole thing and give you wrong answers based on partial data. Instead, cut it off and explicitly tell the model: "There are 50 more results. Call the tool again with `page=2` to see them." This lets the model decide if it wants to keep reading.

```
BAD:  search_logs(...) → first 500 lines, no indication 4,500 more exist
GOOD: search_logs(...) → first 50 matching lines +
      "47 more matches. Call again with cursor='eyJvZmZzZXQiOjUwfQ=='
       to continue, or narrow your query with a time range."
```

### Code Example: Continuation Handle

**1. The Tool Schema Definition**
To support this kind of safe truncation, your tool schema must give the model a way to ask for the next page!

**Anthropic format:**
```json
{
  "name": "search_logs",
  "description": "Searches the system error logs.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The term to search for (e.g. 'crash', 'timeout')"
      },
      "page": {
        "type": "integer",
        "description": "The page number to fetch. Defaults to 1. If a previous tool response told you there were more results, increment this number to see them."
      }
    },
    "required": ["query"]
  }
}
```

**OpenAI / Ollama format:**
```json
{
  "type": "function",
  "function": {
    "name": "search_logs",
    "description": "Searches the system error logs.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The term to search for (e.g. 'crash', 'timeout')"
        },
        "page": {
          "type": "integer",
          "description": "The page number to fetch. Defaults to 1. If a previous tool response told you there were more results, increment this number to see them."
        }
      },
      "required": ["query"]
    }
  }
}
```

**2. The Model's Tool Call**
When the model hits the truncation limit and decides to fetch the next page, here is the actual tool call it will emit:
```json
{
  "name": "search_logs",
  "arguments": {
    "query": "crash",
    "page": 2
  }
}
```

### The Messages Array (Dry Run)

When the model receives a truncated response with a handle, here is how the chat history naturally progresses. (We will show the OpenAI format here for brevity, but the Anthropic `tool_result` flow is identical in principle).

```json
[
  {
    "role": "assistant", 
    "content": "I'll search the error logs for the crash.",
    "tool_calls": [{"id": "call_log1", "type": "function", "function": {"name": "search_logs", "arguments": "{\"query\": \"crash\", \"page\": 1}"}}]
  },
  {
    "role": "tool",
    "tool_call_id": "call_log1",
    "content": "Line 12: Connection timeout...\nLine 45: Retry failed...\n\n[TRUNCATED. 400 more matches found. Call this tool again with page=2 to see the next 50.]"
  },
  {
    "role": "assistant", 
    "content": "I didn't find the root cause in the first batch. I'll check the next page.",
    "tool_calls": [{"id": "call_log2", "type": "function", "function": {"name": "search_logs", "arguments": "{\"query\": \"crash\", \"page\": 2}"}}]
  },
  {
    "role": "tool", 
    "tool_call_id": "call_log2",
    "content": "Line 98: Out of memory exception...\n\n[TRUNCATED. 350 more matches found. Call this tool again with page=3...]"
  }
]
```

### Implementation Code

Here is the Python code that makes this happen safely on the backend:

```python
def search_logs(query: str, page: int = 1):
    PAGE_SIZE = 50
    offset = (page - 1) * PAGE_SIZE
    
    # 1. Ask the backend for just the slice we need (do NOT fetch all rows into memory)
    page_results = db.search(query, limit=PAGE_SIZE, offset=offset)
    
    # 2. Get the total count of matches efficiently
    total_matches = db.count_matches(query)
    
    # 3. Format the results into a string
    response = "\n".join(page_results)
    
    # 4. If there are more results, append the continuation handle!
    end_idx = offset + PAGE_SIZE
    remaining = total_matches - end_idx
    
    if remaining > 0:
        response += f"\n\n[TRUNCATED. {remaining} more matches found. Call this tool again with page={page + 1} to see the next {PAGE_SIZE}.]"
        
    return response
```

## IDs the Model Can Actually Reason About

Long, random UUIDs like `a3f29c1e-b832-4d1a-8c9e-1f8d42a9b3d1` are terrible for language models. The model treats them as arbitrary tokens, struggles to tell them apart, and often hallucinates wrong IDs if it tries to remember them a few turns later. 

Instead, you should translate real database IDs into simple, human-readable local IDs before handing them to the model, and translate them back when the model makes a request. 

### Code Example: ID Translation Layer

Here is an example of how you can create an "ID map" for the current agent session. The model only ever sees `item_1`, but your backend knows exactly which UUID it refers to.

```python
class AgentSession:
    def __init__(self):
        self.id_map = {}
        self.next_id = 1

    def _to_agent_id(self, real_uuid: str) -> str:
        """Translates a real database UUID into a simple ID for the agent."""
        # E.g. 'a3f29c1e...' -> 'item_1'
        agent_id = f"item_{self.next_id}"
        self.id_map[agent_id] = real_uuid
        self.next_id += 1
        return agent_id

    def _to_real_uuid(self, agent_id: str) -> str:
        """Translates the agent's simple ID back into the real database UUID."""
        return self.id_map.get(agent_id)

    # --- Tool Endpoints ---

    def list_tasks(self) -> str:
        """Tool: Lists open tasks."""
        tasks = db.get_open_tasks()
        
        # Give the model 'item_1', 'item_2' instead of raw UUIDs
        formatted_tasks = []
        for task in tasks:
            agent_id = self._to_agent_id(task["uuid"])
            formatted_tasks.append(f"{agent_id}: {task['title']}")
            
        return "\n".join(formatted_tasks)

    def close_task(self, agent_id: str) -> str:
        """Tool: Closes a task using the simple ID."""
        real_uuid = self._to_real_uuid(agent_id)
        if not real_uuid:
            return f"Error: Invalid task ID '{agent_id}'."
            
        db.close_task(real_uuid)
        return f"Successfully closed {agent_id}."
```

If you absolutely *must* expose real IDs (for example, if the ID is also a URL slug the user needs to see), try to use prefixed IDs like `task_9f2a` (like Stripe does with `ch_123` for charges) rather than raw UUIDs. The prefix gives the model context about what the ID represents.

## Key Takeaways for Section 4

Every word your tool returns costs you tokens on every single future turn. Don't dump data; let the model ask for detailed mode vs concise mode. Never truncate long data silently (always give the model a `cursor` or `page` to keep going). And don't force the model to memorize UUIDs—give it short, readable IDs.

*Next: the other kind of return value — the one that shows up when
something goes wrong, and why most tool error messages are written for the
wrong reader entirely.*

---

# 5: Error Messages as Instructions, Not Postmortems

## The Intuition

A normal API error message is written for a human programmer who can read the docs and fix the code. But when an AI agent gets an error, there is no human around to help. The model has to fix its own mistake on the very next turn. 

If your error just says "HTTP 400: Bad Request", the model doesn't know what it did wrong, so it will probably just guess again and fail again. Your error messages must tell the model exactly how to fix the problem. Chapter 2 showed us the *mechanics* of returning an error; this section is about what words you should actually put inside that error string.

### Code Example: The Error Payload

In both Anthropic and OpenAI, you return the error text inside the tool response block.

**Anthropic format:**
```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_123",
  "is_error": true,
  "content": "Invalid date format for 'due_date': got '07/30/2026'. Use ISO 8601: 'YYYY-MM-DD' (e.g. '2026-07-30')."
}
```

**OpenAI / Ollama format:**
*(OpenAI doesn't have an `is_error` flag; you just return the instructional error text as the content.)*
```json
{
  "role": "tool",
  "tool_call_id": "call_123",
  "content": "Invalid date format for 'due_date': got '07/30/2026'. Use ISO 8601: 'YYYY-MM-DD' (e.g. '2026-07-30')."
}
```

The bad version tells you that something broke, but it doesn't give the model any clues on how to fix it. The good version explains exactly what went wrong and shows an exact example of what a correct date looks like. This almost guarantees the model will succeed on its next try.

## Steering, Not Just Correcting

You can also use errors to teach the model better strategies. If the model tries to do something super inefficient (like asking for 14,000 rows from a database), don't just crash or silently cut the data off. Throw an error that tells the model exactly how to be more efficient:

### Code Example: Steering the Model

Don't just fail; teach the model how to use the tool correctly on its next try.

```json
// Inside the content field of your tool response block:
"content": "Query returned 14,203 rows and was rejected. Add a 'status' or 'date_range' filter, or set 'limit' (max 200) if you only need a sample."
```

This stops a huge, expensive database query, and it teaches the model right in the chat that it should always use filters instead of brute force.

## Include a Correctly Shaped Example When the Fix Isn't Obvious

If the model messes up something complicated (like a nested object or an enum choice), don't just say "invalid input". Actually show the model what the valid inputs are. This gives the model the exact answer it needs to succeed.

### Code Example: Explicit Enums

If the model guesses a wrong enum, give it the exact list of right ones.

```json
// Inside the content field of your tool response block:
"content": "Invalid value for 'priority': got 'urgent'. Valid values: 'low', 'medium', 'high', 'critical'."
```

### The Messages Array (Dry Run)

Here is what this "Correction Loop" looks like in the actual message array. Notice how the model receives the semantic error, reflects on it, and immediately fixes its own mistake on the very next turn.

```json
[
  {
    "role": "assistant", 
    "content": "I will update the due date.",
    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "update_task", "arguments": "{\"due_date\": \"07/30/2026\"}"}}]
  },
  {
    "role": "tool",
    "tool_call_id": "call_1",
    "content": "Error: Invalid date format for 'due_date': got '07/30/2026'. Use ISO 8601: 'YYYY-MM-DD'."
  },
  {
    "role": "assistant", 
    "content": "My previous tool call failed because of the date format. I will correct it to ISO 8601.",
    "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "update_task", "arguments": "{\"due_date\": \"2026-07-30\"}"}}]
  },
  {
    "role": "tool",
    "tool_call_id": "call_2",
    "content": "{\"status\": \"success\"}"
  }
]
```

### Backend Implementation Example

Here is how you catch normal Python exceptions and translate them into "Semantic Errors" for the LLM. 

```python
from datetime import datetime

def update_task(task_id: str, due_date: str) -> str:
    try:
        # 1. Try to parse the date (this will throw a ValueError if wrong)
        parsed_date = datetime.strptime(due_date, "%Y-%m-%d")
        
        # 2. Do the actual work
        db.update_task_date(task_id, parsed_date)
        return '{"status": "success"}'
        
    except ValueError:
        # 3. Catch the technical error and return an INSTRUCTION to the model
        return f"Error: Invalid date format: got '{due_date}'. Use ISO 8601: 'YYYY-MM-DD'."
        
    except Exception as e:
        # Generic fallback
        return f"Error: {str(e)}. Please check your arguments and try again."
```

> [!WARNING]
> **Infinite Loop Protection:** If the model gets confused, it might try the exact same wrong arguments 10 times in a row, burning massive amounts of tokens. Always implement a "hard counter" in your orchestration loop (e.g., `if retries > 3: break`) to cut the model off if it can't figure out the error instruction.

## Key Takeaways for Section 5

Your error messages are read by AI models, not humans. Write them as direct instructions (Semantic Errors) telling the model how to fix its mistake right now. Include the exact format you expect, give strategy hints if it is doing something inefficient, and **always use a hard retry limit** to prevent infinite loops.

*Next: what happens when you stop asking the model to describe its output in
prose and start constraining the shape of the answer itself.*

---

# 6: Structured Output and Schema-Constrained Generation

## The Problem This Solves

Everything so far in this chapter has been about tool *calls* — the model
deciding to invoke something and shaping its input. Structured output solves
a related but distinct problem: forcing the model's *final answer* (not a
tool call, the actual response text) into a schema you control, so that
downstream code parsing that response never has to handle "the model
almost returned valid JSON but wrapped it in a sentence and used single
quotes." Before this existed, a common workaround was prompting "respond
only in JSON" and then wrapping the parse in a retry loop for the times it
didn't listen — workable, but fragile, and it burns a full extra round trip
every time the model gets creative with formatting.

## The Mechanism

The key thing to understand here is that this is **not the same as prompting the model to respond in JSON.** When you prompt it, the model tries its best but can still wrap the JSON in a sentence, use single quotes, or add a trailing comment — and then your `json.loads()` call crashes.

With structured output, the **decoding process itself is constrained.** The model's token sampling is restricted at generation time so that only tokens that form a valid instance of your schema can be produced. It is physically impossible for the model to output something that violates the schema — not unlikely, impossible.

Alongside this, `strict: true` can also be applied directly to a **tool's own `input_schema`**, giving the same generation-time guarantee for tool call arguments specifically. This closes the exact class of failure that Sections 2 and 5 were working around with careful descriptions and forgiving error messages — with `strict: true` on a tool, certain classes of malformed input become structurally impossible rather than merely less likely.

The recommended entry point in the Python SDK is `client.beta.chat.completions.parse()` for OpenAI, which sends the schema, validates the response automatically, and returns a typed Python object rather than a raw string you parse yourself. This is the API-level equivalent of Section 4's principle: hand the caller exactly what they need next, not a raw blob they have to further process.

Both major SDKs expose this feature — here is how each one looks:

*   **OpenAI:** Uses `response_format` with `type: "json_schema"` and explicitly requires a `strict: true` flag.
*   **Anthropic:** Uses `output_config` with `type: "json_schema"`.

### Code Example: The API Payloads

Here is how you configure the API to force a structured output.

**OpenAI Format (`response_format` with `strict: true`):**
```json
{
  "model": "gpt-4o",
  "messages": [{"role": "user", "content": "Extract event info."}],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "event_extraction",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "date": { "type": "string" }
        },
        "required": ["name", "date"],
        "additionalProperties": false
      }
    }
  }
}
```

**Anthropic Format (`output_config`):**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "messages": [{"role": "user", "content": "Extract event info."}],
  "output_config": {
    "format": {
      "type": "json_schema",
      "schema": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "date": { "type": "string" }
        },
        "required": ["name", "date"],
        "additionalProperties": false
      }
    }
  }
}
```

## The "Strict" Rules (What JSON Schema Can and Can't Express)

The constrained-decoding path supports a solid but not unlimited subset of JSON Schema. Here is exactly what is and is not allowed.

**What IS supported:** the basic types (`string`, `number`, `boolean`, `array`, `object`), `enum`, `const`, `anyOf`/`allOf`, `$ref`/`$defs` for reuse across the schema, and a set of recognized string formats like `date-time`, `email`, and `uuid`.

**What is NOT supported:** recursive schemas, and numeric or string *constraints* like `minimum`, `maximum`, `minLength`, or `maxLength`. If you need those, you must validate them yourself in your application code after the response arrives — the same way you'd validate tool inputs in Section 5's world.

On top of that, to achieve 100% generation-time guarantees (especially in OpenAI's `strict: true` mode), three extra rules apply:

1. **`additionalProperties: false` is mandatory** on every object. You cannot allow the model to generate arbitrary extra keys.
2. **All fields must be `required`**.
3. **Optional fields require `null`**: If a field might not exist, declare it as `{"anyOf": [{"type": "string"}, {"type": "null"}]}` instead of leaving it out of the `required` array.

```json
// SUPPORTED (Strict Mode Valid):
{
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["open", "closed"]}
  },
  "required": ["status"], 
  "additionalProperties": false
}

// NOT SUPPORTED (Will throw an API error):
// - Missing `additionalProperties: false`
// - Using numeric constraints like `minLength`, `maxLength`, `minimum`, `maximum`
// - Recursive schemas
```

Here is how that same valid schema looks when plugged into a real request for each API:

**Anthropic format (`output_config`):**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "messages": [{"role": "user", "content": "What is the current status of task T-42?"}],
  "output_config": {
    "format": {
      "type": "json_schema",
      "schema": {
        "type": "object",
        "properties": {
          "status": {"type": "string", "enum": ["open", "closed"]}
        },
        "required": ["status"],
        "additionalProperties": false
      }
    }
  }
}
```
The model's response will always be exactly `{"status": "open"}` or `{"status": "closed"}` — never anything else.

**OpenAI / Ollama format (`response_format` with `strict: true`):**
```json
{
  "model": "gpt-4o",
  "messages": [{"role": "user", "content": "What is the current status of task T-42?"}],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "task_status",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "status": {"type": "string", "enum": ["open", "closed"]}
        },
        "required": ["status"],
        "additionalProperties": false
      }
    }
  }
}
```
Notice the extra `name` wrapper inside `json_schema` — that is required by the OpenAI format but not by Anthropic.



### Backend Implementation Example (Pydantic)

Manually writing those strict JSON schemas is tedious. The industry best practice in Python is to use `Pydantic` models, which the OpenAI SDK natively parses into the correct `strict: true` format for you.

```python
from pydantic import BaseModel
from openai import OpenAI

# 1. Define your schema purely in Python
class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

client = OpenAI()

# 2. Pass the Pydantic model directly to the SDK
completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Alice and Bob are going to a science fair on Friday."}],
    response_format=CalendarEvent,
)

# 3. The SDK returns a fully typed Python object! No JSON.loads() needed.
event = completion.choices[0].message.parsed
print(event.name) # Output: Science Fair
```

## Where This Fits Relative to Tool Use

Structured output and tool use solve adjacent but different problems:
*   **Tool Use (Agents):** The model decides *whether* to call a tool, *which* tool to call from a list, and *when* to stop. Use this for workflows, actions, and data gathering.
*   **Structured Output (Data Extraction):** The model is forced to return a single JSON object matching your schema as its final answer. No tools are called. Use this when you are doing data extraction or text-to-JSON formatting.

A single agent turn can use **both**: the model calls tools to gather data across several turns, and once the loop finishes, the final answer is forced into a structured schema. That is a perfectly valid and common pattern.

The mistake to avoid is **targeting the wrong knob**. If you want a tool's *input arguments* to be schema-strict, use `strict: true` on that tool's own `input_schema`. Do not try to force that via `output_config` — that parameter controls the model's final prose response, not the arguments it passes to tools. Using the wrong one gives you no guarantee and a confusing debugging experience.

## Key Takeaways for Section 6

Structured Output features (like `strict: true` and `output_config`) guarantee the model's final response will perfectly match your schema, eliminating the need for fragile retry loops. However, this comes at the cost of strict schema rules (everything must be required, no additional properties, no length constraints). Whenever possible, use an SDK helper like Pydantic rather than handwriting the raw JSON schemas.


*Next: what happens when a tool call itself is risky to repeat — and how the
schema should say so.*

---

# 7: Idempotency, Side Effects, and the Destructive Flag

## The Intuition

A read-only tool can be called speculatively, retried after a timeout, and
called twice by mistake with zero consequence beyond wasted tokens. A tool
that sends an email, charges a card, or deletes a record cannot be treated
the same way — and yet, from the model's point of view inside Chapter 2's
loop, both are just a `tool_use` block it decided to emit. Nothing in the
mechanics of the loop itself distinguishes "safe to retry" from "catastrophic
to retry," which means that distinction has to be designed into the tool,
not assumed from context.

## Idempotency: Design for Safe Retries

**Idempotent** just means: *safe to call twice.* If you call it again with the same inputs, nothing extra happens — you get the same result and the same final state.

A good example: `set_status(task_id, "closed")` is idempotent. If the task is already closed and you call it again, it just stays closed. Nothing breaks, nothing doubles.

A bad example: `increment_counter(task_id)` is NOT idempotent. Call it twice and the counter goes up by 2 instead of 1. The second call created a real, extra effect.

**Why does this matter for AI agents?** Because your agent loop from Chapter 2 *will* retry things when something goes wrong. Here is the dangerous scenario:

1. The model calls `send_email()`.
2. The email is actually sent successfully on the server.
3. But before the response comes back to the agent, the network times out.
4. The agent loop sees an error and retries the call.
5. The email is sent **again**. Alice gets two identical emails.

The agent didn't "choose" to send two emails. It simply couldn't tell the difference between "the first call failed" and "the first call succeeded but the response got lost." A retry policy — which is completely reasonable to have — will blindly fire the tool again.

The fix for operations that *can't* be naturally idempotent (like payments or emails) is an **idempotency key**: a unique ID the model passes with every call. The server stores that key and, if it sees the same key again on a retry, it returns the original result instead of repeating the action.



### The Double-Call Problem (Messages Dry Run)

Here is what the problem looks like in the actual message array. The model calls `send_email` once. A network timeout fires. The loop retries. The email is now sent twice.

```json
[
  {"role": "user", "content": "Send a confirmation email to alice@example.com."},
  {
    "role": "assistant", "content": null,
    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "send_email", "arguments": "{\"to\": \"alice@example.com\", \"subject\": \"Confirmation\"}"}}]
  },
  {
    "role": "tool", "tool_call_id": "call_1",
    "content": "Error: Request timed out after 30s."
  },
  {
    "role": "assistant", "content": null,
    "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "send_email", "arguments": "{\"to\": \"alice@example.com\", \"subject\": \"Confirmation\"}"}}]
  },
  {
    "role": "tool", "tool_call_id": "call_2",
    "content": "{\"status\": \"sent\"}"
  }
]
// Alice just received two identical emails. The first call DID succeed —
// only the response was lost in transit. The retry had no way to know that.
```

### Code Example: Idempotency Key in the Tool Schema

The fix is to expose an `idempotency_key` parameter in the tool schema. A best practice is to use the API's own `tool_call_id` as the key — it is unique per logical intent, and the model carries it forward on retries.

**Anthropic format:**
```json
{
  "name": "send_email",
  "description": "Sends an email. Pass the same idempotency_key on retry to prevent duplicate sends.",
  "input_schema": {
    "type": "object",
    "properties": {
      "to":      {"type": "string", "description": "Recipient email address"},
      "subject": {"type": "string"},
      "body":    {"type": "string"},
      "idempotency_key": {
        "type": "string",
        "description": "A unique key for this send operation. Use the tool_use_id from this call. Re-use the same key on retries."
      }
    },
    "required": ["to", "subject", "body", "idempotency_key"]
  }
}
```

**OpenAI / Ollama format:**
```json
{
  "type": "function",
  "function": {
    "name": "send_email",
    "description": "Sends an email. Pass the same idempotency_key on retry to prevent duplicate sends.",
    "parameters": {
      "type": "object",
      "properties": {
        "to":      {"type": "string", "description": "Recipient email address"},
        "subject": {"type": "string"},
        "body":    {"type": "string"},
        "idempotency_key": {
          "type": "string",
          "description": "A unique key for this send operation. Use the tool_call_id from this call. Re-use the same key on retries."
        }
      },
      "required": ["to", "subject", "body", "idempotency_key"]
    }
  }
}
```

**Real Tool Call Example (What the model actually sends):**

When the model decides to use this tool, it generates the arguments and maps its unique call ID to the `idempotency_key` field.

*Anthropic:*
```json
{
  "type": "tool_use",
  "id": "toolu_01A8",
  "name": "send_email",
  "input": {
    "to": "alice@example.com",
    "subject": "Welcome!",
    "body": "Thanks for signing up.",
    "idempotency_key": "toolu_01A8"
  }
}
```

*OpenAI / Ollama:*
```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {
    "name": "send_email",
    "arguments": "{\"to\": \"alice@example.com\", \"subject\": \"Welcome!\", \"body\": \"Thanks for signing up.\", \"idempotency_key\": \"call_abc123\"}"
  }
}
```

### Backend Implementation: Idempotency Key Check

```python
import redis

_redis = redis.Redis()

def send_email(to: str, subject: str, body: str, idempotency_key: str) -> str:
    redis_key = f"idem:{idempotency_key}"
    
    # 1. Check if we already processed this key (within a 24-hour TTL)
    status = _redis.get(redis_key)
    if status == b"sent":
        return '{"status": "already_sent", "note": "Duplicate detected, email not re-sent."}'
    if status == b"in_progress":
        return '{"status": "error", "note": "Call currently in progress."}'

    # 2. Mark as in-progress BEFORE sending (prevents concurrent race conditions)
    _redis.setex(redis_key, 86400, "in_progress")

    try:
        # 3. Now actually send
        email_api.send(to=to, subject=subject, body=body)
        
        # 4. Mark as fully complete ONLY if it succeeded
        _redis.setex(redis_key, 86400, "sent")
        return '{"status": "sent"}'
        
    except Exception as e:
        # 5. If it failed, delete the lock so the agent CAN retry it safely
        _redis.delete(redis_key)
        return f'{{"status": "error", "note": "{str(e)}" }}'
```

The loop can now retry as many times as it wants. Only the first call with a given key will actually send the email. Every subsequent retry gets `"already_sent"` back immediately.

## Dry-Run Modes

For any tool with a real side effect, a `dry_run: true` parameter that
returns exactly what *would* happen without doing it is disproportionately
cheap to build and disproportionately valuable — it lets the model (or a
human reviewing the model's plan before approving it, foreshadowing Chapter
16's permission layer) verify intent before commitment. `dry_run` on
`schedule_event` might return "would book Alex, Priya for 2026-08-12
14:00–15:00; no conflicts detected" without touching any calendar, which is
both a safety mechanism and, incidentally, a cheap way to catch a
misunderstood request before it costs a real action to undo.

### Code Example: `dry_run` Parameter in the Tool Schema

**Anthropic format:**
```json
{
  "name": "schedule_event",
  "description": "Books a calendar event. Set dry_run=true to preview what WOULD be booked without actually creating it.",
  "input_schema": {
    "type": "object",
    "properties": {
      "title":     {"type": "string"},
      "attendees": {"type": "array", "items": {"type": "string"}},
      "start_time":{"type": "string", "description": "ISO 8601 datetime"},
      "dry_run":   {"type": "boolean", "description": "If true, returns a preview without booking anything."}
    },
    "required": ["title", "attendees", "start_time"]
  }
}
```

**OpenAI / Ollama format:**
```json
{
  "type": "function",
  "function": {
    "name": "schedule_event",
    "description": "Books a calendar event. Set dry_run=true to preview what WOULD be booked without actually creating it.",
    "parameters": {
      "type": "object",
      "properties": {
        "title":     {"type": "string"},
        "attendees": {"type": "array", "items": {"type": "string"}},
        "start_time":{"type": "string", "description": "ISO 8601 datetime"},
        "dry_run":   {"type": "boolean", "description": "If true, returns a preview without booking anything."}
      },
      "required": ["title", "attendees", "start_time"]
    }
  }
}
```

### Dry-Run Messages Array

Here is how a safe agent uses `dry_run` before committing. It checks first, gets human confirmation, then acts.

```json
[
  {"role": "user", "content": "Book a 1-hour sync with Alex and Priya for next Tuesday at 2pm."},
  {
    "role": "assistant", "content": "Let me check if that slot works before booking.",
    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "schedule_event", "arguments": "{\"title\": \"Sync\", \"attendees\": [\"alex\", \"priya\"], \"start_time\": \"2026-08-19T14:00:00\", \"dry_run\": true}"}}]
  },
  {
    "role": "tool", "tool_call_id": "call_1",
    "content": "[DRY RUN] Would book: 'Sync' on 2026-08-19 14:00–15:00. Alex: available. Priya: available. No conflicts."
  },
  {
    "role": "assistant", "content": "Alex and Priya are both free. Shall I go ahead and book it?"
  },
  {"role": "user", "content": "Yes, go ahead."},
  {
    "role": "assistant", "content": null,
    "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "schedule_event", "arguments": "{\"title\": \"Sync\", \"attendees\": [\"alex\", \"priya\"], \"start_time\": \"2026-08-19T14:00:00\"}"}}]
  },
  {
    "role": "tool", "tool_call_id": "call_2",
    "content": "{\"status\": \"booked\", \"event_id\": \"evt_88\"}"
  }
]
```

### Backend Implementation: `dry_run` Handler

```python
def schedule_event(title: str, attendees: list, start_time: str, dry_run: bool = False) -> str:
    conflicts = calendar_api.check_conflicts(attendees, start_time)
    
    if dry_run:
        if conflicts:
            return f"[DRY RUN] Conflict detected: {conflicts}. No event created."
        return f"[DRY RUN] Would book: '{title}' on {start_time}. All attendees available."
    
    # Only reaches here if dry_run is False
    event = calendar_api.create_event(title=title, attendees=attendees, start=start_time)
    return f'{{"status": "booked", "event_id": "{event.id}"}}'
```

## Marking Tools Destructive

The schema itself should carry a signal for which tools are safe to call
freely and which are not — commonly an `annotations` field or a
project-level convention such as `"destructive": true` alongside the tool
definition. This isn't cosmetic: it's the concrete hook the permission
system Chapter 16 builds attaches to. A loop that checks
`if tool.destructive: require_approval()` before executing a call needs
somewhere to read "destructive" from, and the tool definition — written once,
here, in this chapter's spirit — is that source of truth. Getting this flag
right now costs one boolean per tool; getting it wrong is the difference
between an approval gate that actually gates something and one that
silently no-ops because nothing told it which calls mattered.

### Code Example: The `destructive` Annotation

**Anthropic format** (using the `metadata` convention):
```json
{
  "name": "delete_customer_record",
  "description": "Permanently deletes a customer record. THIS CANNOT BE UNDONE.",
  "input_schema": {
    "type": "object",
    "properties": {
      "customer_id": {"type": "string"}
    },
    "required": ["customer_id"]
  },
  "metadata": {
    "destructive": true
  }
}
```

**OpenAI / Ollama format** (using top-level convention your orchestrator reads):
```json
{
  "type": "function",
  "function": {
    "name": "delete_customer_record",
    "description": "Permanently deletes a customer record. THIS CANNOT BE UNDONE.",
    "parameters": {
      "type": "object",
      "properties": {
        "customer_id": {"type": "string"}
      },
      "required": ["customer_id"]
    }
  },
  "destructive": true
}
```

### How Your Orchestrator Uses the Flag

```python
TOOLS = [
    {"name": "get_customer_context", "destructive": False, "fn": get_customer_context},
    {"name": "delete_customer_record", "destructive": True,  "fn": delete_customer_record},
]

def run_tool(tool_call):
    tool = next(t for t in TOOLS if t["name"] == tool_call["name"])

    if tool["destructive"]:
        # Pause the agent loop and ask for human approval before proceeding
        approved = human_approval_gate(tool_call)
        if not approved:
            return "Action cancelled by human reviewer."

    return tool["fn"](**tool_call["arguments"])
```

## Key Takeaways for Section 7

Design tools to be idempotent wherever the underlying operation allows it,
because Chapter 2's loop will retry on error and cannot itself distinguish
a safe repeat from a harmful one; use idempotency keys where true
idempotency isn't achievable; offer `dry_run` on anything with a real side
effect; and mark destructive tools explicitly in the schema, since that flag
is exactly what Chapter 16's permission layer will need to find later.

*Next: everything in this chapter so far has been about individual tools —
now the arithmetic of having many of them at once, paid for on every single
turn.*

---


# 8: Dry-Run: The Token Bill of a 40-Tool Library Across a 20-Step Loop

## The Setup

Take an agent with a **40-tool library** — a realistic size once you connect
a couple of MCP servers (an issue tracker, a wiki, a calendar). Assume each tool schema takes about **250 tokens** to define (name, description, and properties). 

**The Total Schema Size:** 40 tools × 250 tokens = **10,000 tokens**. Every time the agent takes a turn, it has to read these 10,000 tokens.

Run a **20-step loop**, using this project's illustrative Anthropic Sonnet-class pricing: 
*   **$3.00** / 1M tokens (Standard Base Rate)
*   **$3.75** / 1M tokens (Cache Write Rate - a 25% premium for saving the data to memory the first time)
*   **$0.30** / 1M tokens (Cache Read Rate - a massive 90% discount for reading the saved data)

Just like Chapter 2's system prompt, the full tool list is part of the fixed
prefix sent on *every single call* in the loop, because the API is stateless.

## Case 1 — All 40 Tools, No Caching

Every one of the 20 calls pays the full $3.00 base rate on the entire 10,000-token schema block:

$$\text{total schema cost} = 20 \text{ turns} \times 10{,}000 \text{ tokens} \times \frac{\$3.00}{1{,}000{,}000} = 20 \times \$0.03 = \$0.60$$

## Case 2 — All 40 Tools, With Prompt Caching

The tool list doesn't change between calls, so it is completely cacheable.
*   **Step 1 (The Write):** The API writes the 10,000 tokens to the cache (paying the $3.75 premium rate).
*   **Steps 2–20 (The 19 Reads):** The API reads the 10,000 tokens from the cache 19 times (paying the deeply discounted $0.30 rate).

```
1 cache WRITE:  10,000 tokens × $3.75 / 1,000,000 = $0.0375
19 cache READs: 190,000 tokens (10,000 × 19) × $0.30/1,000,000 = $0.0570

TOTAL (40 tools, cached) = $0.0375 + $0.0570 = $0.0945
```

Caching alone cuts the schema bill from $0.60 to $0.0945 — an **84% drop**,
for a simple reason: a static block of 10,000 tokens is read 19 times at a 90% discount.

## Case 3 — Just-in-Time Loading (Tool Search, `defer_loading`)

Now suppose this 40-tool library is realistic in a second way: any *given* task only ever actually calls a handful of them. Let's assume that across the entire 20-step run, the agent only actually needs to use **4 tools**. 

Instead of loading all 40 tools upfront, we load a tiny **50-token** "Tool Search" tool. When the model searches for the 4 tools it actually needs, those 4 tools (**250 tokens each**) are appended to the context.

**The Total Schema Size:** (4 tools × 250 tokens) + 50 search tokens = **1,050 tokens**.

Because these newly discovered tools are appended to the end of the context (not swapped in/out), they coexist with prompt caching perfectly:

*   **Step 1 (The Write):** The API writes the much smaller 1,050 token footprint to the cache.
*   **Steps 2–20 (The 19 Reads):** The API reads those 1,050 tokens 19 times at the deeply discounted rate.

```
1 cache WRITE:  1,050 tokens × $3.75 / 1,000,000 = $0.0039
19 cache READs: 19,950 tokens (1,050 × 19) × $0.30/1,000,000 = $0.0060

TOTAL (JIT + cached) = $0.0039 + $0.0060 ≈ $0.0099
```

## The Ratio

```
All 40 tools, uncached:        $0.6000
All 40 tools, cached:          $0.0945   (84% cheaper than uncached)
JIT (4 tools) + cached:        $0.0099   (90% cheaper than all-cached,
                                          ~98% cheaper than uncached baseline)
```

> [!NOTE]
> **What about OpenAI and Local Models (Ollama)?**
> The math above uses Anthropic's pricing model (where cache reads are 90% cheaper). The exact same *concept* applies universally, but the numbers differ slightly:
> *   **OpenAI:** Offers a **50% discount** on cached input tokens. They do not charge a premium to write to the cache initially.
> *   **Ollama (Local Models):** Because you run Ollama locally, you aren't paying in dollars. But local models use **K-V Cache Reuse**. If the 10,000 token prefix stays exactly the same, the model skips evaluating those tokens again. This saves you massive amounts of **time and GPU compute**, resulting in significantly faster turn-around times.

This is not a rounding effect — it is the entire economic argument for
Chapter 8 (Context Engineering's "select" operation, and the specific
`defer_loading` mechanic covered in Section 11 below): **paying for tool
schemas the current task will never touch is one of the largest, most
avoidable line items in an agent's token bill**, and it gets *worse*, not
better, as you connect more MCP servers. Anthropic's own published numbers land in the same range —
an ~85% token reduction and, notably, an *accuracy* improvement (not just a
cost one) when moving a large tool library behind Tool Search rather than
loading it all upfront.

### Visualizing the Cache Benefit

Here is why Just-In-Time (JIT) loading preserves your cache discount. If you swapped the tools out entirely, you would break the cache on every turn. But by **appending** discovered tools to the end of the context window, the massive system prompt and base tool list remain perfectly cached.

```text
[ TURN 1 ]
  +-----------------+
  | System Prompt   |  (Written to Cache)
  | + Tool_Search   |
  +-----------------+
          |
          v
  +-----------------+
  | User: Delete 42 |
  +-----------------+

[ TURN 2 ]
  +-----------------+
  | System Prompt   |  (CACHED! 90% cheaper)
  | + Tool_Search   |
  +-----------------+
          |
          v
  +-----------------+
  | User: Delete 42 |  (CACHED!)
  +-----------------+
          |
          v
  +-----------------+
  | Asst: Calls Search
  | Tool: Returns Delete_User Schema
  +-----------------+

[ TURN 3 ]
  +-----------------+
  | System Prompt   |  (CACHED! 90% cheaper)
  | + Tool_Search   |
  +-----------------+
          |
          v
  +-----------------+
  | User: Delete 42 |  (CACHED!)
  +-----------------+
          |
          v
  +-----------------+
  | Asst: Calls Search (CACHED!)
  | Tool: Returns Delete_User Schema (CACHED!)
  +-----------------+
          |
          v
  +-----------------+
  | Asst: Calls Delete_User Tool
  +-----------------+
```

### Code Example: The Tool Search Tool

To make this work, your initial payload only includes a single, tiny tool that lets the model search the broader registry.

```json
{
  "name": "tool_search_tool_bm25",
  "description": "Search for available tools in the workspace by describing what you need to do.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language description of the tool you are looking for (e.g. 'delete customer record')"
      }
    },
    "required": ["query"]
  }
}
```

### The Messages Array (Dry Run)

Here is how the model actually discovers and loads tools on the fly. 

```json
[
  {"role": "user", "content": "I need to permanently delete customer CUST-123."},
  
  // 1. Model realizes it doesn't have a delete tool, so it searches for one
  {
    "role": "assistant", "content": null,
    "tool_calls": [{"id": "search_1", "type": "function", "function": {"name": "tool_search_tool_bm25", "arguments": "{\"query\": \"delete customer\"}"}}]
  },
  
  // 2. The orchestrator returns the FULL JSON SCHEMA of the requested tool!
  {
    "role": "tool", "tool_call_id": "search_1",
    "content": "{\"found_tools\": [{\"name\": \"delete_customer_record\", \"description\": \"Permanently deletes a customer.\", \"input_schema\": {\"type\": \"object\", \"properties\": {\"customer_id\": {\"type\": \"string\"}}, \"required\": [\"customer_id\"]}}]}"
  },
  
  // 3. The model now knows how to use the tool, and calls it on the very next turn
  {
    "role": "assistant", "content": null,
    "tool_calls": [{"id": "action_1", "type": "function", "function": {"name": "delete_customer_record", "arguments": "{\"customer_id\": \"CUST-123\"}"}}]
  },
  {
    "role": "tool", "tool_call_id": "action_1",
    "content": "{\"status\": \"deleted\"}"
  }
]
```

## Key Takeaways for Section 8

A 40-tool, 250-token-each library costs $0.60 uncached and $0.09 cached
across a 20-step loop just in schema tokens — before a single tool has been
called. Loading only the handful of tools a task actually touches, via
`defer_loading` and the Tool Search Tool, cuts that further to roughly a
cent, because the appended (not swapped) discovery mechanism preserves the
caching benefit instead of trading it away. The ratio between "declare
everything upfront" and "load on demand" only grows as your tool library
grows — which is exactly the argument the next section makes from the
accuracy side instead of the cost side.

*Next: tokens are only half of what a bloated tool library costs you — the
other half is the model picking the wrong tool more often.*

---

# 9: Tool Selection Failures as the Library Grows

## The Intuition

Handing a new employee a drawer with 6 clearly labeled tools and asking them
to pick the right one is easy. Handing them a warehouse with 150 similarly
labeled tools and asking the same question is a different task entirely —
not because any individual tool got harder to understand, but because
*discriminating between many plausible-looking options* is itself a
cognitive load that scales with the size of the option set.

```text
[ THE COGNITIVE LOAD OF SELECTION ]

Small Library (High Accuracy)      Massive Library (Prompt Bloat)
+-----------------------+          +-----------------------+
| 1. get_weather        |          | 1. search_jira        |
| 2. send_email         |          | 2. search_confluence  |
| 3. delete_user        |  ====>   | 3. search_github_prs  |
| 4. create_user        |          | 4. search_slack_msgs  |
| 5. get_time           |          | ... 45 more tools ... |
+-----------------------+          +-----------------------+
Model: "Ah, 'delete_user'."        Model: "Wait, do I search 
                                   Jira or Github for this?"
```

Tool selection inside a model's forward pass works exactly this way: every additional tool in context is one more candidate the model has to weigh against the others on every single decision. 

## Where Degradation Shows Up (The 13% Cliff)

Current 2024/2025 research on **"Prompt Bloat"** shows a measurable drop-off when models are forced to parse massive lists of tool schemas. While models handle 5-15 tools exceptionally well, accuracy degrades meaningfully in the **20–50 tool** range. In unoptimized tests with 50+ tools, accuracy can plummet to as low as **~13%** because of "Semantic Confusion" and the "Lost-in-the-Middle" phenomenon.

This happens most often when near-duplicate or overlapping tools are present. 

### The Messages Array (Dry Run: Semantic Confusion)

Here is exactly what that failure mode looks like in the API. The user asks to update a billing address, but the model is overwhelmed by too many overlapping search/update tools and picks the wrong one.

```json
[
  {"role": "user", "content": "Update the billing address for Alice to 123 Main St."},
  
  // The system provided 50 tools, including these two confusing options:
  // 1. update_customer_crm_profile (Updates marketing data)
  // 2. update_stripe_billing_record (Updates actual billing data)
  
  // The model gets confused by the overlapping names and picks the wrong one:
  {
    "role": "assistant", "content": null,
    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "update_customer_crm_profile", "arguments": "{\"address\": \"123 Main St\"}"}}]
  },
  
  // The backend executes it, but the actual credit card billing address isn't updated.
  // The agent has silently failed.
  {
    "role": "tool", "tool_call_id": "call_1",
    "content": "{\"status\": \"success, CRM updated\"}"
  }
]
```

## Why This Isn't Just a Cost Problem

It would be a much smaller issue if a bloated tool library only cost money (Section 8) — you could simply decide to spend more. The reason it's treated as its own critical failure mode is that Anthropic's own measurements on the Tool Search Tool showed *accuracy* improving alongside token reduction when a large library moved behind on-demand discovery. 

The cost and the confusion share a root cause: **too many candidates visible at once.**

## What Actually Helps (Tool-RAG)

The modern (2025+) solution to this is treating tools like database documents using **Tool-RAG** (Retrieval-Augmented Generation) or "Dynamic Tool Retrieval". 

Three levers, in the order this chapter has built them:
1.  **Sharper Descriptions (Section 2):** Reduce ambiguity between similar tools directly.
2.  **Consolidating Primitives (Section 3):** Reduce the *count* of tools competing for attention by turning 5 small tools into 1 macro tool.
3.  **On-Demand Tool Discovery (Section 11):** This is Tool-RAG. Remove tools from the decision entirely until they're actually relevant, rather than asking the model to ignore 145 irrelevant options on every turn.

## Key Takeaways for Section 9

Tool-selection accuracy degrades as the number of visible tools grows,
roughly in the 20–50 tool range for current models, and the degradation is
worse when tools overlap in name or purpose. This isn't a separate problem
from Section 8's token cost — they share a cause — which is why sharper
descriptions, consolidation, and on-demand loading all show up as fixes for
both at once.

*Next: a short recap of where these many tools actually come from in the
first place, and why MCP doesn't make tool *design* optional.*

---

# 10: Model Context Protocol (MCP), In Depth

## Prerequisites: What You Need Before This Section Makes Sense

Everything from Section 1 onward has quietly assumed one thing: that the
tool's JSON schema and the code that actually executes it live *in the same
process* as your agent loop — you wrote a Python function, you wrote a
matching schema, you put both in the same dictionary Chapter 2 built. MCP is
the answer to a narrower, more mechanical question sitting underneath that
assumption: **what happens when the tool's code lives somewhere else** — a
different process, a different machine, written by someone you've never
talked to — **and your agent still needs to call it as if it were local?**
That is a transport and standardization problem, not a tool-design problem,
and keeping that distinction sharp is the single most important thing this
section will argue.

To follow the rest of this section you need two small pieces of background
that the chapter hasn't needed until now, because Sections 1–9 worked
entirely at the level of the Anthropic and OpenAI wire formats, not at the
level of the protocol underneath them.

**The client-server model, restated precisely.** One program (the
**client**) initiates a connection and sends requests; another program (the
**server**) listens, receives those requests, and sends back responses. This
is not new to you — a web browser is a client, a website's backend is a
server — but it's worth stating because MCP's entire vocabulary (host,
client, server) is built on top of this one relationship, applied to tools
instead of web pages.

**JSON-RPC 2.0, the wire format MCP is built on.** This is a small, older
(2010) specification for how two programs exchange function calls as JSON
over any transport. It defines exactly three message shapes, and MCP does
not add a fourth:

1. A **request** — has a `method` (the function name), optional `params`,
   and an `id` the sender picks so it can match the eventual response.
2. A **response** — has the *same* `id` as the request it answers, and
   either a `result` (success) or an `error` (failure), never both.
3. A **notification** — looks like a request but has *no* `id`, which is
   the signal "don't bother replying." Fire-and-forget.

**Dry-run, generic JSON-RPC (nothing MCP-specific yet):**

```json
// A client asks a server to add two numbers — a REQUEST (has an id):
{"jsonrpc": "2.0", "id": 1, "method": "add", "params": {"a": 2, "b": 3}}

// The server's RESPONSE — same id, carries a "result":
{"jsonrpc": "2.0", "id": 1, "result": 5}

// A NOTIFICATION — no id, no response will ever come back for this one:
{"jsonrpc": "2.0", "method": "log", "params": {"message": "server started"}}
```

Hold onto that `id`-based request/response pairing and the id-less
notification — every MCP message you'll see for the rest of this section is
one of these three shapes, just with MCP-specific `method` names like
`tools/list` and `tools/call` in place of `add`.

## Why MCP Exists: The N×M Problem, Restated

If you've been through this repository's earlier module on protocols (B03),
you've already seen this problem in general form: without a shared standard,
connecting $N$ agent applications (Claude, ChatGPT, your own script) to $M$
external systems (Slack, GitHub, Postgres) requires up to $N \times M$
bespoke integrations — every agent framework writing its own Slack wrapper,
its own GitHub wrapper, repeated $N$ times.

Anthropic open-sourced the **Model Context Protocol** in November 2024 as a
fix specifically for this integration arithmetic: one client implementation
per agent application, one server implementation per external system, and
any MCP client can talk to any MCP server. $N \times M$ collapses to
$N + M$. The standard was subsequently adopted well beyond Anthropic's own
products — other model providers and agent frameworks ship MCP client
support, and the server ecosystem (community and vendor-maintained) now
numbers in the thousands. That scale is precisely what makes Sections 8 and
9's warnings not theoretical: it is trivially easy to connect three or four
popular MCP servers and hand your agent 150 tools by accident.

```text
[ THE N×M PROBLEM vs THE N+M SOLUTION ]

Without MCP (N×M)                  With MCP (N+M)
Agent A \ / Server X               Agent A \       / Server X
Agent B - - Server Y               Agent B - (MCP) - Server Y
Agent C / \ Server Z               Agent C /       \ Server Z

Result: Tangled mess of custom     Result: One standard protocol
API wrappers, one per pair.        connecting everything, one per side.
```

## The Three Roles: Host, Client, Server

MCP's vocabulary is more precise than "client and server," and the precision
matters once you're debugging a real setup.

The **Host** is the user-facing application — Claude Desktop, Claude Code,
an IDE like Cursor, or your own Python agent script. This is the thing a
human actually opens.

The **Client** is a connector object that lives *inside* the Host. A Host
that talks to three different MCP servers (a GitHub server, a Postgres
server, a Slack server) holds three separate Client instances internally —
each Client maintains exactly one stateful connection to exactly one Server.
This is the detail people most often get wrong: "the MCP client" is not the
same thing as "the Host application"; it's the narrower networking object
the Host creates once per server it connects to.

The **Server** is the standalone program — often someone else's code
entirely — that actually knows how to talk to Postgres, or GitHub's API, or
your local filesystem, and exposes that capability through the MCP wire
format instead of its own bespoke API.

```text
[ HOST / CLIENT / SERVER — ONE CLIENT PER SERVER CONNECTION ]

                    +-----------------------------+
                    |     MCP HOST                |
                    |  (Claude Desktop / your     |
                    |   own agent script)         |
                    |                             |
                    |  +--------+  +--------+     |
                    |  |Client 1|  |Client 2|     |
                    |  +---+----+  +----+---+     |
                    +------|------------|---------+
                           |            |
                    (stdio pipe)   (Streamable HTTP)
                           |            |
                    +------v----+  +----v------+
                    | GitHub    |  | Postgres  |
                    | MCP Server|  | MCP Server|
                    +-----------+  +-----------+
```

## Transports: How the Bytes Actually Move

JSON-RPC says nothing about *how* the bytes travel between processes — that
is the **transport**, and MCP standardizes exactly two.

**stdio** is for a server running as a local subprocess of the Host on the
same machine — a filesystem tool, a local git wrapper. The Host spawns the
server process and the two talk by writing newline-delimited JSON-RPC
messages to each other's standard input and standard output. This is the
transport your own agent scripts will use most often while learning MCP,
because it needs no networking setup at all — just a command to run.

> [!WARNING]
> **The stdout gotcha.** Every other section of this chapter has told you to
> print liberally — narration is part of how this repository teaches. On a
> stdio-transport MCP *server*, stdout is not your console; it is the wire.
> A stray `print("debugging here")` inside a tool function interleaves plain
> text into the JSON-RPC stream and corrupts every message after it, and the
> client-side error you get back looks nothing like "you printed to
> stdout" — it looks like a mysterious JSON parse failure three calls later.
> If you need to narrate what an MCP server is doing while it's running,
> write to `stderr` (or use Python's `logging` module configured to a file
> or stderr) — never `print()` to stdout inside a stdio-transport server.

**Streamable HTTP** is for a server that runs remotely, or that multiple
clients need to reach concurrently. It's a single HTTP endpoint that accepts
`POST` requests carrying JSON-RPC messages, and can optionally upgrade the
response into a Server-Sent-Events stream when the server needs to send
multiple messages back for one request (progress updates, then a final
result). Streamable HTTP replaced an earlier, clunkier two-endpoint
"HTTP+SSE" transport (one endpoint to send, a separate one to receive) —
that older transport is now formally deprecated; if you see it in an older
tutorial, mentally substitute Streamable HTTP.

## The Six Primitives

An MCP connection exposes capabilities in both directions, not just
server-to-client. There are three primitives a **Server** offers, and three
a **Client** can offer back to the Server — and this chapter, until now, has
only ever talked about the first row.

| Side | Primitive | One-line definition |
|---|---|---|
| Server → Client | **Tools** | Executable functions the model can call to take action. Everything Sections 1–9 covered. |
| Server → Client | **Resources** | Read-only, addressable data the Host can pull in as context — a file, a DB schema, a live API snapshot — identified by a URI. |
| Server → Client | **Prompts** | Server-authored, reusable prompt templates a *user* can invoke (e.g. a "/summarize-ticket" slash command a Jira MCP server ships alongside its tools). |
| Client → Server | **Roots** | The Client tells the Server which filesystem or URI boundaries it's allowed to operate within. |
| Client → Server | **Sampling** | The Server asks the Client's own LLM to generate a completion on its behalf, so the server doesn't need its own model API key or SDK. |
| Client → Server | **Elicitation** | The Server asks the Host to prompt the human user for a missing piece of information mid-call. |

**Resources**, worked example: instead of a `read_config_file` tool, a
server can expose `file:///etc/app/config.json` as a Resource. The Host
lists available resources, a human (or the model, depending on the Host's
UI) picks the ones relevant to the current task, and their contents get
added to context the same way an attached file would — no tool call
required at all. The dividing line the spec draws is intent: Tools are for
the *model* to invoke to *do* something; Resources are data meant to be
*attached* as context, closer to a file picker than a function call.

**Prompts**, worked example: a Slack MCP server might ship a prompt named
`summarize-channel` that expands into "Summarize the last 50 messages in
#channel, highlighting decisions and action items" — a template a *human*
selects from a menu in the Host's UI, parameterized once, rather than
something the model decides to call on its own.

**Roots, Sampling, and Elicitation** are the client-side mirror: a
filesystem MCP server, before touching anything, can ask the Client "what
directories am I actually allowed to touch?" (Roots); a server that wants to
summarize text without shipping its own LLM API key can ask the Client's
already-connected model to do it (Sampling); and a server midway through a
multi-step booking flow that's missing a checkout date can pause and ask the
Host to prompt the human directly (Elicitation) instead of guessing or
erroring out.

## The Lifecycle Handshake (Dry Run)

Before any of the six primitives can be used, the Client and Server run a
one-time handshake to agree on a protocol version and which capabilities
each side actually supports — you cannot call `tools/list` on a connection
that hasn't introduced itself yet. This is the classic, currently
widely-deployed lifecycle (protocol revisions `2025-06-18` /
`2025-11-25` — see the note at the end of this section for what changes
next). Three phases: **Initialization**, **Operation**, **Shutdown**.

```text
[ THE MCP LIFECYCLE: THREE PHASES, CLIENT <-> SERVER ]

   CLIENT                                         SERVER
     |                                               |
     |---- initialize (protocolVersion, ------------>|   PHASE 1
     |      capabilities, clientInfo) -------------->|   Initialization
     |                                               |
     |<--- result (protocolVersion, -----------------|
     |      capabilities, serverInfo) ---------------|
     |                                               |
     |---- notifications/initialized --------------->|   (no reply — fire and forget)
     |                                               |
     |========= handshake complete ==================|
     |                                               |
     |---- tools/list ------------------------------>|   PHASE 2
     |<--- result: { tools: [get_weather, ...] } ----|   Operation
     |                                               |   (repeat for as many
     |---- tools/call (name, arguments) ------------>|    calls as the loop needs)
     |<--- result: { content: [...] } ---------------|
     |                                               |
     |---- close transport (stdin/stdout or -------->|   PHASE 3
     |      HTTP connection) ------------------------|   Shutdown
```

**Step 1 — the Client sends `initialize`,** stating the protocol version it
speaks and which client-side primitives it supports:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": { "roots": { "listChanged": true }, "sampling": {} },
    "clientInfo": { "name": "my-agent-host", "version": "1.0.0" }
  }
}
```

**Step 2 — the Server responds** with its own protocol version and which
server-side primitives it actually offers — a server with no Resources
simply omits that key, and the Client now knows not to bother calling
`resources/list` on it:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true }
    },
    "serverInfo": { "name": "weather-server", "version": "1.0.0" }
  }
}
```

**Step 3 — the Client confirms with a notification** (note: no `id` — this
is fire-and-forget, matching the notification shape from the Prerequisites
section above). Only after this may normal operation begin:

```json
{"jsonrpc": "2.0", "method": "notifications/initialized"}
```

**Step 4 — normal operation.** Only now does the Section-8-and-9-familiar
`tools/list` / `tools/call` exchange happen:

```json
[
  // Host asks the Server what tools it has
  {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},

  // Server replies with the JSON Schema for its tools
  {
    "jsonrpc": "2.0", "id": 2,
    "result": {
      "tools": [{
        "name": "get_weather",
        "description": "Returns current weather.",
        "inputSchema": {
          "type": "object",
          "properties": {"city": {"type": "string"}}
        }
      }]
    }
  },

  // Later, when the model decides to call it:
  {
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "get_weather", "arguments": {"city": "London"}}
  },

  // Server executes the logic and returns the result
  {
    "jsonrpc": "2.0", "id": 3,
    "result": {"content": [{"type": "text", "text": "It is raining in London."}]}
  }
]
```

Notice that step 4's `result.content` block is exactly the kind of thing
Section 4 spent an entire section on — whether the Server returns lean text
or a bloated JSON dump here is a *tool-design* decision the transport has no
opinion about, which is precisely the point the next subsection makes
explicit.

## Bridging MCP to the Model: One Schema, Two Model-Facing Formats

Everything in the dry-run above — `inputSchema`, `tools/list`, `tools/call`
— is the MCP wire format between the Host and the Server. It is neither
Anthropic's format nor OpenAI's; it's a third, separate vocabulary. The
Host's job, once it has an MCP tool definition in hand, is to translate it
into whichever of the two formats this chapter has used everywhere else,
depending on which model API the Host is actually calling. This is the same
dual-format convention Section 1 established, applied to a tool that
happened to arrive over MCP instead of being hand-written.

### Code Example: The Same MCP Tool, Translated Two Ways

**The MCP tool, exactly as received from `tools/list`:**
```json
{
  "name": "get_weather",
  "description": "Returns current weather.",
  "inputSchema": {
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"]
  }
}
```

**Translated to Anthropic format** — `inputSchema` simply becomes
`input_schema`; nothing inside `properties` changes:
```json
{
  "name": "get_weather",
  "description": "Returns current weather.",
  "input_schema": {
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"]
  }
}
```

**Translated to OpenAI / Ollama format** — `inputSchema` becomes
`parameters`, wrapped in the `type: "function"` envelope this chapter has
used since Section 1:
```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Returns current weather.",
    "parameters": {
      "type": "object",
      "properties": {"city": {"type": "string"}},
      "required": ["city"]
    }
  }
}
```

The result flows back through the same fork in reverse: MCP's raw
`tools/call` result is neither wire format either, and the Host wraps it
into whichever one the model expects before it goes into the messages
array.

### Code Example: The Result Round-Trip in Both Formats

**MCP's raw `tools/call` result, from the Server:**
```json
{"content": [{"type": "text", "text": "It is sunny in London."}]}
```

**Anthropic format** — the Host lifts the text out of MCP's `content` array
and wraps it in a `tool_result` block:
```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01A8",
  "content": "It is sunny in London."
}
```

**OpenAI / Ollama format** — the same MCP content, wrapped as a `tool` role
message instead:
```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "It is sunny in London."
}
```

Nothing about this translation step is MCP-specific — it's the identical
fork every dry-run in Sections 1 through 9 already walked through for
hand-written tools. MCP only changes where the `name`/`description`/schema
triple originally came from.

## Minimal Working Code: A Real Server and a Real Client

This is the current (2026) official Python SDK's high-level decorator API —
you write a plain typed function, the SDK derives the JSON Schema and wires
up the `tools/list` / `tools/call` handling for you, the same trade-off
Section 6 made with Pydantic for structured output.

**The server** (`weather_server.py`) — runs over stdio, so per the warning
above it must never `print()` to stdout:

```python
# ============================================================
# TOPIC: A minimal MCP server exposing one tool and one resource
# REF:   S06-B04 Chapter 3, Section 10
# ============================================================
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("weather-server")

@mcp.tool()
def get_weather(city: str) -> str:
    """Returns the current weather for a city."""
    # A real tool would call a weather API here.
    return f"It is sunny in {city}."

@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """A read-only Resource, not a Tool — data to attach, not an action to invoke."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    # stdio: the Host will spawn this file as a subprocess and speak
    # JSON-RPC over its stdin/stdout — do not print() anything else here.
    mcp.run(transport="stdio")
```

**The client, low-level (stdio)** — this is the shape your own agent
script's Client role would actually take when spawning the server above as
a subprocess:

```python
# ============================================================
# TOPIC: Connecting to the server above over stdio, listing and
#        calling its tools
# ============================================================
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Tells the client HOW to launch the server subprocess
server_params = StdioServerParameters(
    command="python",
    args=["weather_server.py"],
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # the handshake from the dry-run above

            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")
            # -> Available tools: ['get_weather']

            result = await session.call_tool("get_weather", arguments={"city": "London"})
            print(f"Tool result: {result.content[0].text}")
            # -> Tool result: It is sunny in London.

asyncio.run(run())
```

Note that this client script's own `print()` calls are perfectly fine — the
stdout restriction from the warning above applies only to the *server*
process talking over stdio; the client is a normal Python program with a
normal stdout.

**The client, high-level (remote HTTP)** — if you instead ran the server
with `mcp.run(transport="streamable-http")` and exposed it over the network,
connecting is a single line, no manual handshake code required — the SDK
performs `initialize` internally:

```python
import asyncio
from mcp import Client

async def main() -> None:
    async with Client("http://localhost:8000/mcp") as client:
        result = await client.call_tool("get_weather", {"city": "London"})
        print(result.structured_content)

asyncio.run(main())
```

## MCP Solves Transport, Not Design

MCP standardizes *how* a tool's schema and results travel between a server
and a model-calling client. It says nothing at all about whether the tool
*behind* that wire format is well-named, right-sized, or returns a lean
response.

This matters concretely given the scale of the MCP ecosystem described
above. Connecting a handful of popular MCP servers can trivially put fifty
or a hundred tools in front of your agent — precisely the regime Section 9
described as degrading accuracy, and precisely the token bill Section 8
priced out. A `tools/list` response is still just a JSON array of the exact
same `name` / `description` / `inputSchema` objects Section 2 spent an
entire section teaching you to write well; MCP did not make that job
optional, it just changed who's typing the function body.

**"I used MCP" is an answer to "how do tools arrive"; it is not an answer to
"are these good tools," and conflating the two is the single most common way
an agent ends up with a bloated, confusing tool set.**

## Client-Side Filtering (The Code Example)

Treat every MCP server you connect the same way you'd treat a new
dependency: read what it actually exposes before wiring it in wholesale.

If an MCP server offers 40 tools but your agent only needs 2, filter them
explicitly at the client configuration level rather than exposing all 40 to
the LLM's context. Modern MCP clients support `includeTools` and
`excludeTools` arrays in their configuration files (e.g. `mcp.json`):

```json
{
  "mcpServers": {
    "github-server": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],

      // We explicitly allow only the two our agent actually needs,
      // protecting the model's context from prompt bloat.
      "includeTools": [
        "search_repositories",
        "get_issue"
      ]
    }
  }
}
```

## Security and Trust: Connecting a Server Is Not Free

An MCP Tool is arbitrary code execution wearing a JSON Schema — the official
spec is explicit that a tool's `description` and `annotations` should be
treated as **untrusted input** unless they come from a server you've
personally vetted, because nothing stops a malicious or careless server
author from writing a description engineered to manipulate the model (a
"tool poisoning" attack) or from silently swapping a tool's behavior after
you've already approved it once. The spec's own governing principles, worth
holding onto as a checklist:

1. **User consent and control** — a human must explicitly approve connecting
   a server and invoking any of its tools; nothing should happen silently.
2. **Data privacy** — a Host must not forward a Resource's contents to a
   server the user hasn't consented to sharing it with.
3. **Tool safety** — treat every tool as capable of arbitrary action;
   Section 7's `destructive` flag and Chapter 16's approval gate are the
   concrete mechanisms this principle is asking you to build.
4. **Sampling controls** — if a server uses the Sampling primitive to ask
   your model to generate something, the human should be able to see and
   approve the actual prompt being sent, not just that a sampling request
   occurred.

For remote servers (Streamable HTTP), authorization is handled via OAuth
2.1 — the server acts as an OAuth resource server, the Host's Client
performs a standard authorization-code flow before it can call any tool.
None of this is enforced by the protocol itself; MCP defines the *messages*
for consent and authorization, not a runtime that forces you to check them,
which is exactly the same gap Section 12 names for tool design generally:
the mechanism exists, but something in your Host still has to actually read
and act on it.

## What Changed on July 28, 2026: MCP Goes Stateless

A framing correction, stated up front: everything taught above — the
`initialize`/`initialized` handshake, one persistent connection per server —
is **not** "the current thing, with a newer one coming later." The
specification took its biggest revision yet on **July 28, 2026** and it is
already the final, ratified spec, not a preview. Anthropic's own
announcement calls it "one of the most significant spec releases to date"
and explicitly tells developers building *new* MCP servers to build against
it now, and Claude became the first major client to ship support for it,
rolling out across Claude products within days of the spec going final. The
handshake model above is genuinely legacy as of this writing — it's taught
first in this section because it's the simpler mental model for
understanding *what* capability negotiation is, not because it's what you
should target if you're starting a server today.

The one honest reason the old handshake still shows up everywhere —
tutorials, existing community servers, possibly your own SDK's examples —
is **SDK lag, not spec status**: as of this writing the C# and Rust SDKs
have caught up to 2026-07-28 fastest, while Python and TypeScript are still
catching up. If you're writing a Python MCP server today and its version of
the `mcp` package predates this, it will still speak the old handshake
underneath the same `@mcp.tool()` decorator — check your SDK's version
before assuming which protocol revision you're actually running.

**What changed, mechanically:** MCP became **stateless at the protocol
level**. The `initialize`/`notifications/initialized` handshake and the
session ID that pinned a client to one specific server instance are both
gone. Every single request now carries its protocol version and
capabilities inline, in a `_meta` field, and a new `server/discover` method
lets a client ask "what do you support?" before its very first real call,
without needing a standing session to ask it in. The practical payoff: any
server instance can now answer any request, so a remote MCP server can sit
behind a plain round-robin load balancer the way a normal stateless REST API
does — no sticky sessions, no shared session store, serverless deployments
"just work" in a way they structurally could not under the handshake model
above. This part is almost entirely SDK-internal — the same way you never
hand-wrote the old `initialize` JSON once you used the decorator API, you
won't hand-write `server/discover` either.

## MRTR: The Pattern That Actually Replaces Your Own Code

Three primitives from this section's table — **Roots, Sampling, and
Logging** — are formally deprecated under this revision (still functional,
scheduled for removal no sooner than twelve months out). Their replacements
are mostly a design habit, not new code: pass directories via ordinary tool
parameters instead of Roots, call the LLM provider's API directly instead of
routing through Sampling, and log to `stderr` or OpenTelemetry instead of
the Logging primitive.

One deprecation *does* require writing genuinely different code, and it's
the one the rest of this subsection slows all the way down for:
**Elicitation** — a server pausing mid-call to ask the human a question — is
replaced by something called **Multi Round-Trip Requests**, or **MRTR** for
short.

### What MRTR Actually Is, in Plain English

**Summary:** MRTR is just a name for "the server says *I need one more
thing from you*, the client goes and gets it, and then the client repeats
the *entire original request* again — not a follow-up, the same request —
this time with the missing piece attached."

**The everyday analogy.** Think of an online flight-booking form. You fill
in your name, your dates, your destination, and hit Submit — but you forgot
to pick a seat. A well-built website doesn't crash and doesn't silently pick
a middle seat for you. It sends the form back with "please choose a seat"
highlighted. Critically: you don't start a fresh form. You fill in the *one*
missing field on the *same* form — name, dates, destination are all still
sitting there filled in — and hit Submit again. The website never had to
"remember" you were mid-conversation with it; the whole form travels
together, every single time you submit it. MRTR is exactly this, except the
"form" is a tool call like `provision_db(name="orders-db")`, and "please
choose a seat" is the server replying `resultType: "input_required"`
instead of a normal answer.

**Why this exists — the old way vs. the new way.** Before this section's
"stateless" change, a server that needed to ask you something mid-task
worked like a **phone call**: the connection between client and server
stayed open the whole time, so the server could interrupt — "hold on, let me
ask you something" — get your answer, and carry on the *same* call. That's
what the deprecated Elicitation primitive did. But Section 10 already
established that the new protocol has **no open connection to interrupt** —
every request is independent, the way an **email** is independent. You
can't "put someone on hold" over email. So instead, the reply to an
incomplete email is a new email saying "I'm missing your order number" —
and the fix is to send one more complete email that includes everything
from before *plus* the order number. MRTR is the email version of asking a
question mid-task; Elicitation was the phone-call version.

### The New Vocabulary, Defined Before You See Any Code

The code below uses five names that haven't shown up anywhere earlier in
this chapter. Knowing what each one means before reading the code makes the
code close to self-explanatory:

- **`CallToolResult`** — the normal, everyday reply a tool sends back when
  it's actually done: "here's your answer."
- **`InputRequiredResult`** — a *different kind* of reply a tool can send
  instead of `CallToolResult`, meaning "not done yet — here's exactly what
  I'm still missing." This is not an error. It's a completely normal,
  expected response shape under the current spec.
- **`ElicitRequest`** — the actual *question* being asked, written as data
  instead of a sentence: a `message` string to show the human ("Which
  region should the database live in?") plus a JSON Schema describing the
  shape of a valid answer. This is the exact same idea Section 2 taught
  about tool schemas — "the schema is the whole spec" — except here the
  *reader* of the schema is a human filling in a form, not a model filling
  in arguments.
- **`ElicitResult`** — the human's answer, once it comes back.
- **`input_requests`** / **`input_responses`** — two dictionaries that use
  the *same keys* on purpose. `input_requests` is the server saying "here's
  what I still need, and I'm calling it `'region'`." `input_responses` is
  the client saying "here's your answer to `'region'`" on the retry. The
  matching key is how the server recognizes its own question coming back.
- **`request_state`** — your own sticky note. The server writes something
  onto it the first time ("I was in the middle of provisioning a
  database"), and the client hands it back completely unchanged on the
  retry. This exists because the server itself has no memory between the
  two calls anymore — the sticky note is the only thing carrying that
  memory forward, and it travels *with* the client, not inside the server.

### The Code, Explained Piece by Piece

This is the actual, current Python SDK code for a `provision_db` tool that
needs a `region` the model didn't provide — verified directly against the
SDK's own published source rather than paraphrased, so you can trust the
names and structure below are real, not illustrative:

```python
# ============================================================
# TOPIC: Multi Round-Trip Requests (MRTR) — the 2026-07-28
#        replacement for the deprecated Elicitation primitive
# ============================================================
from mcp.types import (
    CallToolResult, ElicitRequest, ElicitRequestFormParams,
    ElicitResult, InputRequiredResult, TextContent,
)

# This is the "question," built once, up front. It is not code that RUNS —
# it's a data object describing what to ask and what a valid answer looks like.
ASK_REGION = ElicitRequest(
    params=ElicitRequestFormParams(
        message="Which region should the database live in?",
        requested_schema={
            "type": "object",
            "properties": {"region": {"type": "string"}},
            "required": ["region"],
        },
    )
)

async def call_tool(ctx, params) -> CallToolResult | InputRequiredResult:
    # Look for an answer to "region" inside whatever the client sent this time.
    # On the very FIRST call nobody has answered anything yet, so
    # params.input_responses is empty and .get("region") comes back None.
    answer = (params.input_responses or {}).get("region")

    if not isinstance(answer, ElicitResult) or answer.content is None:
        # No usable answer yet -> STOP HERE and ask for it.
        # Returning InputRequiredResult instead of CallToolResult IS the
        # entire mechanism — there is no separate "pause" API to call.
        return InputRequiredResult(
            input_requests={"region": ASK_REGION},
            request_state="provision-v1",  # our sticky note for next time
        )

    # Only reachable on the RETRY: the client re-sent this same tool call,
    # this time with input_responses["region"] filled in, so we can finish.
    name = (params.arguments or {})["name"]
    text = f"Provisioned {name!r} in {answer.content['region']}."
    return CallToolResult(content=[TextContent(type="text", text=text)])
```

Read the function as one `if` doing all the work: *"Do I already have an
answer to `region`? No → hand back a polite `InputRequiredResult` asking for
it. Yes → finish the job and hand back a normal `CallToolResult`."* The
function runs from the top **every single time** it's called — including on
the retry — which is exactly why the check has to come first: the function
has no memory of its own that it already asked once.

### The Dry Run, as a Story

Say a user tells the agent: *"Set up a new database called orders-db."*
Here is exactly what happens, matched step-by-step to the code above:

```text
[ MRTR: ONE LOGICAL TASK, TWO SEPARATE, COMPLETE REQUESTS ]

  CLIENT (the Host)                              SERVER (your tool)
    |                                                 |
    | 1. Model decides to call the tool.              |
    |-- tools/call provision_db(name="orders-db") --> |
    |                                                 | 2. Code runs top to
    |                                                 |    bottom. input_responses
    |                                                 |    is empty -> region is
    |                                                 |    missing.
    |<- result: input_required, -------------------   |
    |     needs "region" (via ASK_REGION), ---------  |   3. Returns InputRequiredResult
    |     sticky note = "provision-v1" -------------  |      WITH the sticky note
    |                                                 |      (request_state) attached.
    | 4. Host sees "input_required" and shows         |
    |    the human the question from ASK_REGION:      |
    |    "Which region should the database live in?"  |
    |    The Host holds onto the sticky note "as is" —|
    |    it never reads or changes what's on it.      |
    |                                                 |
    | 5. Human types: "us-east-1"                     |
    |                                                 |
    |-- tools/call provision_db(name="orders-db", --> |   6. SAME tool, SAME
    |     input_responses={"region": "us-east-1"}, -> |      "name" argument,
    |     request_state="provision-v1") ------------->|      PLUS the new answer
    |                                                 |      AND the sticky note
    |                                                 |      handed back exactly
    |                                                 |      as it was given out.
    |                                                 | 7. Code runs top to
    |                                                 |    bottom AGAIN. This time
    |                                                 |    input_responses has
    |                                                 |    "region" -> the if is
    |                                                 |    false -> falls through.
    |<- result: "Provisioned 'orders-db' in --------  |   8. Returns a normal
    |            us-east-1." ------------------------ |      CallToolResult. Done.
```

Three things worth noticing, because they're the most common points of
confusion: first, step 6 is **not** a new tool call with a follow-up
question tacked on — it is the *entire original call*, `name="orders-db"`
and all, sent again from scratch, just with `input_responses` (and the
sticky note) added. Second, the function body in step 7 does not "resume"
from where it left off; there is no saved position to resume from. It
re-runs completely, and the only reason it behaves differently the second
time is that `input_responses` now has something in it that wasn't there
before. Third — and this is the one it's easy to miss — the **sticky note
makes the round trip too**. The server hands it out in step 3, and the
client's *only* job with it is to echo it back byte-for-byte in step 6,
exactly like copying a confirmation code from one screen to the next
without needing to understand what it means. The Host never opens it, never
edits it, and doesn't need to — only the server that wrote it ever reads it.
This example's code doesn't bother re-checking `request_state` on the way
back in (it only reads `input_responses`), which is a valid simplification
for something this small, but the SDK's real, production-grade `MCPServer`
seals that note cryptographically before sending it and verifies the seal
on the way back, precisely because it's the client — someone outside the
server's control — handing it back to you, and a value you can't verify is
a value you can't trust.

If you're using the high-level `Client` from this section's earlier code
example rather than writing this low-level loop by hand, you don't have to
manage any of the two-call mechanics yourself — you register a callback for
"how do I ask the human a question," and `Client` performs the retry loop
internally, handing your code back one final `CallToolResult` as if the
pause had never happened.

None of this changes anything this section taught about Tools, Resources,
or Prompts, and it changes nothing at all about Sections 1–9's design
guidance — a stateless handshake and an MRTR retry both still carry the
exact same `name`/`description`/`inputSchema` object a well- or
badly-designed tool always had. It is transport plumbing evolving
underneath a stable set of primitives, which is itself the cleanest
illustration of this section's central claim: MCP's version number can
change completely without a single one of Section 2 through Section 9's
rules changing at all.

## Key Takeaways for Section 10

MCP is a client-server protocol, built on plain JSON-RPC 2.0, that collapses
$N \times M$ integration work into $N + M$ by giving every agent Host and
every external system a common wire format to speak instead of a bespoke
one. It defines six primitives — Tools, Resources, and Prompts from the
server; Roots, Sampling, and Elicitation from the client — of which this
chapter's first nine sections only ever needed the first. As of this
writing, the **2026-07-28 spec is the current, final revision**, not an
upcoming one — it made the protocol stateless, dropped the
`initialize`/`initialized` handshake, deprecated Roots, Sampling, and
Logging, and replaced server-initiated Elicitation with the client-driven
MRTR retry pattern; you'll still meet the older stateful handshake
everywhere in the wild because SDK support (especially Python and
TypeScript) is still catching up to the spec, not because the spec itself
is still pending. Either way, getting the transport right (stdio for local,
Streamable HTTP for remote; never `print()` to a stdio server's stdout) is
necessary and, on its own, *insufficient* — every tool arriving over an MCP
connection, no matter how old or new the protocol revision behind it, is
still fully subject to the naming, granularity, return-value, and
error-message rules Sections 2 through 9 already built.

*Next: the concrete platform features built specifically to survive a
tool library too large to declare all at once.*

---

# 11: Advanced Tool Use: Search, Deferred Loading, Programmatic Calling

## Tool Search and `defer_loading`

Section 8's dry-run already built the arithmetic; this section names the
actual mechanism. Any tool can be marked `"defer_loading": true` in its
definition — it's still declared in the request's `tools` array (so it's
known to exist and can be found), but its full schema is *not* expanded into
the model's context until it's actually needed. A small, always-resident
tool search tool lets the model look up and pull in just the tools
relevant to the current step, and it comes in two variants: a regex-based
one (`tool_search_tool_regex_20251119`, where Claude writes a Python
`re.search()` pattern) and a BM25 one
(`tool_search_tool_bm25_20251119`, where Claude writes a natural-language
query instead) — both searching the same fields (tool name, description,
argument names, argument descriptions), and both generally available on
the Claude API. Pick regex when you can predict the keywords Claude
should search for (namespaced tool names like `github_list_prs`); pick
BM25 when tool descriptions vary in phrasing and a fuzzy natural-language
match will surface more of what's relevant. Anthropic's own measurements,
across a 50-plus tool setup: roughly **85% less token consumption** (about
8.7K tokens versus about 77K for the same tool count declared upfront), and
—the result worth remembering over the cost saving — a genuine **accuracy
improvement**: Opus 4 went from 49% to 74%, and Opus 4.5 from 79.5% to
88.1%, on their internal MCP tool-selection evaluation, simply by not
showing the model tools it didn't need yet. Use this once your tool
definitions exceed roughly 10K tokens or your library passes roughly 10
tools; skip it for small, frequently-all-used tool sets, where the search
tool itself is pure overhead.

### Code Example: A Minimal `defer_loading` Request

**Anthropic format:**

```json
{
  "tools": [
    { "type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex" },
    {
      "name": "get_weather",
      "description": "Get current weather for a location",
      "input_schema": {
        "type": "object",
        "properties": { "location": { "type": "string" } },
        "required": ["location"]
      },
      "defer_loading": true
    },
    {
      "name": "search_files",
      "description": "Search files in the workspace",
      "input_schema": {
        "type": "object",
        "properties": { "query": { "type": "string" } },
        "required": ["query"]
      },
      "defer_loading": true
    }
  ]
}
```

Both `get_weather` and `search_files` are declared in full — the API needs
the complete schema server-side to run the search and to later expand a
match — but neither one enters Claude's context until Claude's own search
names it. At least one tool (normally the search tool itself) must stay
non-deferred, or the request is rejected outright.

**OpenAI / Ollama format:**

```python
response = client.responses.create(
    model="gpt-4o",
    input="What is the weather in San Francisco?",
    tools=[
        {"type": "tool_search"},   # the always-resident search tool
        get_weather_tool,          # ordinary function tool
        search_files_tool,         # ordinary function tool
    ],
)
```

```json
// get_weather_tool and search_files_tool each carry the same
// "defer_loading": true flag Anthropic uses -- the field name is
// identical across both formats:
{
  "type": "function",
  "name": "get_weather",
  "description": "Get current weather for a location",
  "parameters": {
    "type": "object",
    "properties": { "location": { "type": "string" } },
    "required": ["location"]
  },
  "defer_loading": true
}
```

The field name is a rare point of agreement between the two ecosystems,
but the mechanics differ in two ways worth knowing before you switch
between them. First, OpenAI draws no regex/BM25 distinction — there's a
single `{"type": "tool_search"}` tool, and the model decides which
deferred tools are relevant from their descriptions rather than writing
an explicit search query. Second, where Anthropic expands a matched tool
inline (as a `tool_reference` block right where the search happened),
OpenAI injects newly-discovered tools at the *end* of the context window
instead — a deliberate choice to keep the cached prefix untouched, the
same caching motivation Anthropic's inline-but-prefix-preserving
expansion is solving for, just implemented differently.

### Dry Run: What Actually Loads

```text
[ TOOL SEARCH: WHAT LOADS WHEN ]

  REQUEST declares (all three, every time)     MODEL'S CONTEXT after the request lands
    tool_search_tool_regex_20251119       -->   tool_search_tool_regex_20251119 (always resident)
    get_weather        (defer_loading)     x    (not loaded -- just a name the model can search for)
    search_files       (defer_loading)     x    (not loaded)

  Model searches: pattern="weather"  (Anthropic: a Python regex, case-insensitive
                                       OpenAI: no query at all -- it just picks by description)
    |
    v
  tool_search_tool_result: tool_references = [ get_weather ]
    |
    v
  Anthropic expands inline, right where the search happened:
    get_weather's full input_schema  ------------> loaded now, purely because it matched
  OpenAI appends it at the end of the context window instead (same effect,
    different position -- both keep the cached prefix untouched)
  search_files was never mentioned -> never loaded, never billed as a resident schema

  Model calls get_weather(location="San Francisco")
```

The prefix (system prompt plus non-deferred tools) never changes shape
across this exchange in either format, which is exactly why
`defer_loading` and prompt caching coexist without invalidating each
other — the deferred tools live outside the cached prefix entirely.

## Programmatic Tool Calling

### The Problem, in Plain English

**One-sentence summary:** normally, every tool result has to travel back
through the model's own context before the model can decide what to do
next; programmatic tool calling instead lets the model write a **short
script**, run it in a sandboxed code environment, and let *that script*
call the tools directly — so only the script's final printed answer comes
back to the model, not every intermediate result along the way.

Think about a task like *"How many of my last 50 open PRs are approved?"*
Here is exactly how that plays out with the ordinary, round-trip tool use
this whole chapter has used so far:

1. The model calls `list_open_prs()` and gets back a JSON blob describing
   50 pull requests. That entire blob gets added to the conversation
   history.
2. The model now has to call `get_review_status(pr_id)` for *each* of those
   50 PRs, one at a time.
3. Every one of those 50 results also gets appended to the conversation
   history.
4. Only once all 50 results are sitting in context does the model count
   them up and answer "7 are approved."

The model never actually needed to *see* the full details of 50 separate
review-status lookups — it only ever needed the final number. But ordinary
tool calling has no way to skip showing the model that intermediate junk,
because the rule has always been "call → result goes into context → model
reads it → model decides the next step." This is Section 4's "give the
model only what it needs" problem, just repeated 50 times in a row instead
of once.

### The Analogy

Imagine asking an assistant: *"Check these 50 invoices and tell me how many
are overdue."*

**Ordinary tool calling** is like the assistant reading every invoice out
loud to you, one at a time — amount, due date, status — and only after all
50 have been read aloud do *you* do the counting in your head. You had to
sit through all 50, even though you only ever cared about the final number.

**Programmatic tool calling** is like handing the assistant a checklist
instead: *"Go through the invoices yourself, tally up how many are overdue,
and just tell me the total."* The assistant flips through all 50 privately
and only ever reports back "7." You never had to hear about the other 49.

### How It Actually Works

Instead of emitting one `tool_use` block, waiting for the result, then
emitting the next one, the model writes something closer to real code —
for our PR example, something like:

```python
prs = await list_open_prs()
approved = 0
for pr in prs:
    status = await get_review_status(pr["id"])
    if status == "approved":
        approved += 1
print(approved)
```

This runs inside a **code-execution container** the model has access to.
The important part: when this script calls `list_open_prs()` or
`get_review_status(...)`, those are *real* tool calls that actually hit
your backend — but the JSON result of each call lands straight into a
**variable inside the running script**, not into the model's chat history.
The container just pauses, performs the tool call, plugs the result back
into the script, and resumes — 50 times over, silently, without the model
ever seeing any of those 50 results. Only the script's final `print(approved)`
— literally just the number `7` — is what comes back into the model's
context.

```text
ORDINARY TOOL USE                        PROGRAMMATIC TOOL CALLING
--------------------------------         --------------------------------
Model's context grows by:                Model's context grows by:
  - the full 50-PR list                    - the script it wrote
  - 50x individual review results          - one line: "7"
  = thousands of tokens                    = a handful of tokens

51 separate model "turns"                1 model turn (writing the script),
(each one a full, costly                 then the container does 51 tool
inference pass)                          calls internally with no inference
                                          needed for any of them
```

Anthropic reports this cutting token usage by **37%** on a real multi-step
research task — 43,588 tokens down to 27,297 — purely from routing
intermediate tool results through running code instead of through the
model's own context, plus the latency win from collapsing dozens of
separate inference passes into one script execution. This is the more
powerful sibling of Section 4's "give the model what it needs next, not
everything": instead of trusting each individual tool's return-value design
to keep things lean, the *entire aggregation step* moves outside the
model's context altogether.

### The Mechanism: `allowed_callers` and the `caller` Field

So how does the platform know which tools are allowed to be called *from
inside a script* versus only directly by the model? You mark a tool with
`"allowed_callers": ["code_execution_20260120"]` in its definition — the
code-execution tool's version string doubles as the name of the permitted
caller. Once marked this way, the model's running script sees that tool as
an ordinary `async` Python function it can `await` (exactly like
`get_review_status(...)` in the snippet above). Every time it gets invoked,
the resulting `tool_use` block is tagged with a `caller` field, so your
server can always tell a direct call from a programmatic one instead of
guessing:

```python
tools = [
    {"type": "code_execution_20260120", "name": "code_execution"},
    {
        "name": "get_review_status",
        "description": "Look up the review status of one pull request by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"pr_id": {"type": "string"}},
            "required": ["pr_id"],
        },
        "allowed_callers": ["code_execution_20260120"],  # not ["direct"] --
    },                                                    # the model is guided
]                                                          # to call this only from code
```

```json
// A tool_use block produced from inside the running script carries this:
{
  "type": "tool_use", "name": "get_review_status", "input": {"pr_id": "PR-42"},
  "caller": { "type": "code_execution_20260120", "tool_id": "srvtoolu_abc123" }
}
// A direct call (no code involved) would instead carry:
// "caller": { "type": "direct" }
```

**OpenAI / Ollama format:** there is no equivalent field here — OpenAI's
Responses API code interpreter runs self-contained Python, but it has no
mechanism for that code to call *your* function tools mid-script the way
`allowed_callers` does. A script running in OpenAI's sandbox can't pause,
hand control back to your server for one tool result, and resume with that
result available to the next line — the round trip Anthropic's `caller`
field exists to track simply isn't there to track. The common workaround in
that ecosystem is to intercept the model's `code_interpreter` tool call
yourself (frameworks like LiteLLM do this against sandboxes such as E2B),
run the code in infrastructure you control instead of OpenAI's, and splice
in calls to your own functions from inside that script — which gets you the
same *effect* but as something you build and operate, not a declarative
field on a tool definition.

### Dry Run: One Script, Many Paused Round Trips

```text
[ PROGRAMMATIC TOOL CALLING: THE SCRIPT PAUSES, NOT THE MODEL ]

  MODEL writes:                               CONTAINER runs it           YOUR SERVER
  prs = await list_open_prs()          ---- pauses, emits tool_use ---->  (you execute it)
                                        <---------- tool_result ----------|  the 50-PR list
                                             lands INSIDE the running          lands inside the
                                             script, NOT in the model's        script, not the
                                             own context                      model's context
  for pr in prs:                        (this loop runs entirely inside the container —
      status = await get_review_status(...)  the model is not "watching" or being re-run
      if status == "approved":               for each of the 50 iterations)
          approved += 1
  # loop repeats 50 times total, same container, same script -- the model
  # is not re-sampled between iterations
  print(approved)                       ---- only this line reaches ---->  the model's next turn
```

Two restrictions worth naming because they touch chapters already covered:
tools sourced from Section 10's MCP connector cannot be enabled for
programmatic calling — only directly-declared tools qualify — and a tool
carrying Section 6's `strict: true` cannot carry `allowed_callers` either.
Where either restriction bites, keep that one tool direct-only; the rest of
your library can still use programmatic calling normally.

## Tool Use Examples

### The Problem, in Plain English

**One-sentence summary:** sometimes a model can fill in every field of a
tool call *correctly by the rules* and still get it *wrong*, because the
mistake isn't about type or spelling — it's about an unwritten convention
that JSON Schema has no way to state, and the fix is simply to show the
model a couple of real, correct examples instead of trying to describe the
rule in words.

Here's a concrete case. Say you have a `book_flight` tool with three
fields: `trip_type` (`"one_way"` or `"round_trip"`), `departure_date`, and
`return_date`. There's an obvious real-world rule here: a one-way trip
should **never** include a `return_date`, and a round trip should
**always** include one. But look at what the schema can actually enforce —
`required: ["trip_type", "departure_date"]` only says "these two fields
must be present." It has no clean way to say "and `return_date` must be
present *only when* `trip_type` is `"round_trip"`, never otherwise." That
"only when" relationship — one field's presence depending on another
field's *value* — is exactly the kind of thing a plain JSON Schema `type`
and `required` list cannot express (the more powerful conditional keywords
that could express it, like `if`/`then`, are the same ones Section 6 told
you many structured-output pipelines don't support). So a model working off
the schema alone is left to guess, and it guesses inconsistently: sometimes
it invents a `return_date` for a one-way trip because "every flight probably
needs one," sometimes it forgets `return_date` on a genuine round trip
because nothing in the schema shouted "don't forget this one."

### The Analogy

Think of a paper form at a government office. Near the bottom it says:
*"If you checked 'Married' in Section 2, also fill in Section 4. Otherwise,
leave Section 4 blank."* That instruction is written in plain English right
there on the form — and people still get it wrong constantly, filling in
Section 4 by habit or skipping it when they shouldn't have. What actually
fixes this in practice isn't a clearer sentence — it's the office clerk
keeping two filled-out **sample forms** pinned to the wall: one showing a
married applicant with Section 4 filled in, one showing a single applicant
with Section 4 left empty. People glance at the sample that matches their
situation and copy the pattern. `input_examples` is that pinboard, attached
directly to the tool definition instead of the wall.

### The Fix: `input_examples` on a Tool Definition

An `input_examples` array is just a short list of real, correct calls
attached to the tool schema, so the model has actual worked examples to
pattern-match against instead of having to infer the unwritten rule from a
sentence. It's the exact same idea as this repository's own dry-run
convention — "don't just describe it, show the arithmetic with real
numbers" — aimed at a tool schema instead of a chapter's notes.

**Anthropic format:**

```json
{
  "name": "book_flight",
  "description": "Books a flight. A one-way trip must NOT include return_date; a round trip MUST include it.",
  "input_schema": {
    "type": "object",
    "properties": {
      "trip_type": { "type": "string", "enum": ["one_way", "round_trip"] },
      "departure_date": { "type": "string" },
      "return_date": { "type": "string" }
    },
    "required": ["trip_type", "departure_date"]
  },
  "input_examples": [
    { "trip_type": "one_way", "departure_date": "2026-09-10" },
    { "trip_type": "round_trip", "departure_date": "2026-09-10", "return_date": "2026-09-17" }
  ]
}
```

Notice what each example is doing: the first one shows, *by leaving it out*,
that `return_date` genuinely does not belong on a one-way booking — not "it
happened to be omitted this once," but "this is the shape a correct one-way
call takes." The second shows the opposite shape for a round trip. Neither
example needed a single word of extra explanation; the model can compare
its own draft call against whichever example matches the situation and copy
the pattern, the same way the office clerk's applicant copies whichever
sample form matches theirs.

### The Dry Run: Same Schema, With and Without Examples

```text
[ WHY THE EXAMPLES CHANGE THE OUTCOME ]

WITHOUT input_examples (schema + description only):
  User: "Book me a one-way flight to Tokyo on Sept 10."
  Model's call: {"trip_type": "one_way", "departure_date": "2026-09-10",
                 "return_date": null}
  -- WRONG: nothing in the schema told the model that including
     return_date at all (even as null) breaks the one-way convention.

WITH input_examples (the same schema, plus the two worked examples above):
  User: "Book me a one-way flight to Tokyo on Sept 10."
  Model's call: {"trip_type": "one_way", "departure_date": "2026-09-10"}
  -- CORRECT: the model matched the shape of the first example, which
     simply never mentions return_date for a one-way trip.
```

Anthropic reports this closing a real gap on exactly this class of
complex-parameter task — 72% to 90% accuracy in their internal testing.
Each example costs roughly 20-50 tokens for a simple input like this one,
more (100-200 tokens) for a deeply nested one — cheap relative to that
accuracy gain, but not free, so reach for it only once a plain description
has demonstrably failed, the same "don't pay for what you don't need"
discipline Section 4 already applied to return values.

**OpenAI / Ollama format:** there is no dedicated `input_examples` field —
OpenAI's tool schema has no formal slot for worked examples the way
Anthropic's does. The standard workaround in that ecosystem is to fold the
same worked examples directly into the `description` string as plain text
(`"One-way example: {'trip_type': 'one_way', 'departure_date': '...'}. Round
trip example: {..., 'return_date': '...'}."`), or to show a correct call
once earlier in the conversation history itself — a technique called
**few-shot prompting**, where "shot" just means "one worked example" and
"few-shot" means you've shown a handful of them so the model can pattern
match. Same intent — concrete examples the model can copy the shape of —
carried by plain prose instead of a structured field, which costs the same
description tokens you're already spending and gets no schema validation on
the examples themselves.

## Choosing Between These Three

| Bottleneck you're actually seeing | Reach for |
|---|---|
| Tool schemas alone consume tens of thousands of tokens before the task starts | Tool Search + `defer_loading` |
| Intermediate tool results (not the schemas) are large and mostly get thrown away | Programmatic tool calling |
| The model keeps constructing subtly wrong arguments for one or two specific tools | Tool use examples |

These compose — a large MCP-sourced library behind `defer_loading`, with
programmatic calling for the multi-step aggregation task built on top of it,
is a completely normal combination for a serious agent, not an either/or
choice.

## Key Takeaways for Section 11

Tool Search (`defer_loading`, now GA, in both regex and BM25 variants) cuts
both token cost and — measurably — selection accuracy when the library is
large, by hiding unneeded schemas until a search names one via a
`tool_reference`; programmatic tool calling (`allowed_callers`, the
`caller` field) keeps large intermediate results out of the model's
context entirely by pausing and resuming a script inside a code-execution
container instead of round-tripping through the model; tool use examples
(`input_examples`) close the specific gap where a schema's types are
satisfied but the *convention* isn't obvious. All three are 2025–2026-era
platform features built directly in response to the exact cost and
accuracy problems Sections 8 and 9 derived from first principles — and,
like Section 10's MCP revision, worth re-checking against current docs
periodically, since exact field names and GA status are exactly the kind
of detail that shifts under a fast-moving API. Coverage across the two
ecosystems is uneven: OpenAI's Responses API ships its own tool search
(`{"type": "tool_search"}`, and — genuinely — the identical
`defer_loading` field name), but has no equivalent to `allowed_callers`
or `input_examples`; both gaps are closed with prose (a hand-built
sandbox-interception pattern, and worked examples folded into the
description) rather than a dedicated field.

*Next: everything this chapter fixed, and the one thing good tool design
was never going to fix on its own.*

---

# 12: What Good Tool Design Still Can't Fix

## The Honest Limit

Every technique in this chapter — clear naming, right-sized granularity,
lean return values, actionable errors, structured output, idempotency,
deferred loading — makes an individual tool call, and a set of tool calls,
easier for a model to get right. None of it decides *when* the model should
stop calling tools and check its own work, *what* an agent should remember
between one session and the next, or *who* is allowed to approve a
destructive call before it executes. Those are not tool-design questions —
they're loop-level and system-level questions, and naming them precisely
here is this chapter's actual final job, the same discipline Chapter 2
closed with.

### Diagram: The Boundary, Drawn Once

```text
[ WHAT TOOL DESIGN COVERS, AND WHERE THE REST LIVES ]

  +------------------------------------------------------+
  |   THIS CHAPTER: MAKE ONE TOOL CALL EASY TO GET RIGHT |
  |   naming * granularity * return values * errors *    |
  |   structured output * idempotency * deferred loading |
  +------------------------------------------------------+
        |             |              |               |
        v             v              v               v
  "was this call   "did we learn  "who approves   "what about the
   even correct?"   from last      a destructive    rest of the
                     session?"      call?"          context window?"
        |             |              |               |
        v             v              v               v
    Chapter 6      Chapter 9      Chapter 16        Chapter 4
  (verification)    (memory)     (permissions)    (context mgmt)
```

Every arrow above starts from a well-formed tool call that still isn't
enough on its own — the table that follows names each gap precisely.

| Missing capability | Symptom without it | Where it's built |
|---|---|---|
| **Deciding tool calls are trustworthy at all** | A well-designed tool can still return a *wrong but well-formatted* answer; nothing here verifies correctness | Chapter 6 |
| **Remembering which tools worked well last time** | Every session re-discovers the same tool-selection lessons from scratch | Chapter 9 (Memory) |
| **Approving a destructive call before it runs** | Section 7's `destructive` flag is inert until something reads it and gates on it | Chapter 16 |
| **Managing the *rest* of the context window** (not just tool schemas) | Section 8 only priced the tool-schema slice; the growing transcript tail is still Chapter 2 Section 11's unsolved problem | Chapter 4 |
| **Handling a library too large even for search to disambiguate cleanly** | Thousands of near-duplicate MCP tools across many servers | Chapter 4 (context engineering at scale) / multi-agent delegation (B04 later chapters) |

## Key Takeaways for Section 12

Good tool design is necessary and, on its own, insufficient — it makes each
individual decision easier for the model to get right, but it does not
verify outcomes, remember across sessions, gate destructive actions, or
manage the context window beyond the tool schemas themselves. Each of those
gaps has an exact chapter where it gets addressed, the same way Chapter 2
closed its own gap list.

*Next: the whole chapter, compressed into one table you can use as a
checklist the next time you write a tool definition.*

---

# 13: Key Takeaways + Master Decision Table

The single mental model for this chapter: **a tool schema is a user
interface, its user is a model with exactly one shot at reading it
correctly, and every ambiguity you leave in it becomes a silent guess made
on your behalf.** Everything else — granularity, return values, errors,
structured output, idempotency, and the platform features in Section 11 —
is a specific consequence of taking that one sentence seriously.

### Diagram: The Chapter, Compressed

```text
[ CHAPTER 3, ONE PICTURE ]

        "a tool schema is a UI; its user is a model
              with exactly one shot at reading it right"
                             |
       +---------------------+---------------------+
       |                     |                     |
  DESIGN THE CALL       DESIGN THE COST        DESIGN AROUND SCALE
   (Sections 2-7)        (Sections 8-9)         (Sections 10-11)
  naming, granularity,   token cost of a tool    MCP transport,
  returns, errors,       library nobody fully    search/defer,
  strict output,         uses; accuracy decay    programmatic calls,
  idempotency             past ~20-50 tools       tool use examples
       |                     |                     |
       +---------------------+---------------------+
                             |
                             v
              Section 12: none of this verifies outcomes,
              remembers across sessions, or gates a destructive
              call -- that's Chapter 6, Chapter 9, Chapter 16
```

| I want to know... | Reach for | Key fact |
|---|---|---|
| Why the model keeps misusing a tool that "should" be obvious | Section 2 | The name, parameters, and description are the *entire* spec — nothing else is visible to the model |
| Whether to split one operation into many tools or bundle it | Section 3 | Consolidate around what a human would call "one task"; keep genuinely distinct or dangerous operations separate |
| What a tool should actually return | Section 4 | Only what's needed next; offer a verbosity control; truncate with a continuation handle, never silently |
| How to write a tool error message | Section 5 | State what was wrong and what a correct call looks like — it's read by a model with one retry, not a human debugging later |
| How to force a well-formed final answer or tool call | Section 6 | `output_config.format` for final answers, `strict: true` on `input_schema` for tool arguments — neither supports the full JSON Schema spec |
| How to make a tool safe to retry | Section 7 | Design for idempotency or use an idempotency key; offer `dry_run`; mark destructive tools explicitly for Chapter 16 |
| What a large tool library actually costs | Section 8 | ~$0.60 uncached → ~$0.09 cached → ~$0.01 with JIT loading, for a 40-tool/20-step example — cost scales with declared tools, not used tools |
| Why more tools can make the model worse, not just slower | Section 9 | Selection accuracy degrades past roughly 20–50 visible tools, worse with overlapping names/purposes |
| Whether MCP alone guarantees good tools | Section 10 | No — MCP standardizes transport (N×M → N+M); every design principle above still applies to an MCP-sourced tool |
| Which platform feature fixes which bottleneck | Section 11 | Tool Search/`defer_loading` for schema bloat, programmatic calling for large intermediate results, tool use examples for convention gaps |
| What tool design alone will never fix | Section 12 | Verification, cross-session memory, permission gating, and context management beyond schemas — each has its own later chapter |

**Connection forward:** Chapter 4 goes back to Section 8's dry-run and
Chapter 2's uncacheable growing tail and generalizes both into a single
problem — the context window as a finite, managed resource with an explicit
budget — introducing the four operations (write, select, compress, isolate)
that every context-management technique in this repository, from here
forward, turns out to be one instance of.
