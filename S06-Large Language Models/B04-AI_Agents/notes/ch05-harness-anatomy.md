# Chapter 5: Harness Anatomy

## Table of Contents

1. [Why This Chapter Exists](#1-why-this-chapter-exists)
2. [The Ten Components, Named](#2-the-ten-components-named)
3. [The Harness as an Operating System](#3-the-harness-as-an-operating-system)
4. [Determinism Where It Matters](#4-determinism-where-it-matters)
5. [Instruction Files and Repo Conventions](#5-instruction-files-and-repo-conventions)
6. [The Workspace/Filesystem as State](#6-the-workspacefilesystem-as-state)
7. [Hooks and Lifecycle Events](#7-hooks-and-lifecycle-events)
8. [Harness Versioning and Configuration](#8-harness-versioning-and-configuration)
9. [Reading a Real Harness: Claude Agent SDK and deepagents](#9-reading-a-real-harness-claude-agent-sdk-and-deepagents)
10. [The Hill-Climbing Method](#10-the-hill-climbing-method)
11. [Dry-Run: Why One-Change-Per-Version Is the Only Attributable Design](#11-dry-run-why-one-change-per-version-is-the-only-attributable-design)
12. [What This Chapter Still Leaves Open](#12-what-this-chapter-still-leaves-open)
13. [Key Takeaways + Master Decision Table](#13-key-takeaways--master-decision-table)

---

# 1: Why This Chapter Exists

## Starting From Plain Language

Here is "harness" with no jargon at all: take away the language model itself
— the part that actually reads text and predicts what comes next — and
**everything else in a working agent is the harness.** The loop that calls
the model again and again (Chapter 2), the tools it's allowed to touch and
how they're described (Chapter 3), what's sitting in its context window at
any moment (Chapter 4) — none of that is the model. All of it is code you
write, configure, and can change without retraining anything. That whole
surrounding structure has a name now, and this chapter's only job is to take
it apart into pieces small enough to build, test, and improve one at a time.

This matters practically, not just semantically. Chapter 1 introduced the
now-common shorthand **Agent = Model + Harness**, and the reason that
equation earns its own chapter is this: when an agent fails, there are
exactly two places the fix can live. You can wait for a better model — not
something you control on any useful timeline — or you can fix the harness
today, in code you own. A precise way to say what a good harness actually
does: it makes certain classes of failure **structurally impossible to
repeat**, rather than hoping a smarter model won't make that mistake again.
A harness that refuses to let a `Write` tool touch a path outside the
project folder hasn't made the model more careful — it has made "the model
carelessly overwrites a file outside the project" a category of bug that
literally cannot happen anymore, regardless of what the model decides to
attempt.

## Why "Harness" Deserves to Be a Real Word, Not a Buzzword

It would be reasonable to be skeptical of a new piece of jargon — plenty of
2026-era AI vocabulary is repackaging. This one earns its keep because it
names something you have already been building for four chapters without a
word for it: the tool schemas of Chapter 3, the context manager of Chapter
4, the message-list loop of Chapter 2. This chapter's job is to give that
accumulating pile of code an actual shape — roughly ten nameable parts —
so that "improve the harness" stops meaning "vaguely try things" and starts
meaning "change this one specific, named component, and measure what
happened."

*As with every prior chapter, the concrete Section 7 and Section 9 examples
below are demonstrated against the Claude Agent SDK, since it's the most
fully documented, currently-shipping harness available to study — but the
ten-component decomposition itself is not Anthropic-specific. Section 9
shows the same components appearing, independently, in LangChain's
`deepagents` project, which is good evidence the list describes something
real rather than one vendor's opinion.*

## Key Takeaways for Section 1

A harness is simply everything around the model that isn't the model —
code you own and can change today. Its purpose is making specific failure
classes structurally impossible, not making the model try harder, and this
chapter exists to turn that idea into roughly ten nameable, separately
improvable pieces.

*Next: the actual list.*

---

# 2: The Ten Components, Named

## Starting Simple: What You Already Built

Before the full list, notice that four of these ten already exist in this
folder's own code, under different section headings:

- Chapter 2's `while` loop, checking `stop_reason` every turn — that's
  **loop control**.
- Chapter 3's tool schemas and `TOOL_DISPATCH` table — that's the
  **tool interface**.
- Chapter 4's `ContextManager`, deciding what's visible each step — that's
  **context delivery**.
- Chapter 4's `NOTES.md`-style external file — that's **memory**.

Nothing new has to be learned to recognize these four; they just didn't have
a shared category name yet. The other six are new territory this chapter
opens up.

## The Full List

| # | Component | Plain-language job | Where it lives elsewhere in this folder |
|---|---|---|---|
| 1 | **Loop control** | Decide when to call the model again, and when to stop | Chapter 2 |
| 2 | **Tool interface** | Define what the model can do, and how those actions are described | Chapter 3 |
| 3 | **Context delivery** | Decide what's actually sitting in the window on a given turn | Chapter 4 |
| 4 | **Planning artifacts** | A durable, external plan the agent writes and checks off, not just holds in its head | Chapter 7 |
| 5 | **Memory** | Knowledge that survives past one run or one context window | Chapter 4 §9, Chapter 9 |
| 6 | **Verification** | Checking a claimed result is actually true before trusting it | Chapter 6, Chapter 14 |
| 7 | **Permissions** | Which actions require no approval, which require one, which are forbidden outright | Chapter 16 |
| 8 | **Sandbox** | Where code actually executes, and what it can and can't reach from there | Chapter 16 |
| 9 | **Persistence** | Surviving a crash or restart without losing all prior progress | Chapter 12 |
| 10 | **Observability** | Logs and traces that let a human see what actually happened, after the fact | Chapter 15 |

An eleventh item is worth naming even though it didn't make the roadmap's
own list as a separate row: **eval hooks** — a way to score whether a run
succeeded, wired into the harness itself rather than checked by hand. It
shows up bundled with verification and observability above, and gets its
own full chapter (14) once evals are the main subject rather than a
supporting one.

```
                    ┌─────────────────────────────────────────┐
                    │                 MODEL                     │
                    │   (reads context, predicts next action)   │
                    └───────────────────┬───────────────────────┘
                                         │  tool_use / text
                                         ▼
   ┌─────────────────────────── HARNESS ───────────────────────────┐
   │  ┌────────────┐  ┌───────────────┐  ┌──────────────────┐      │
   │  │Loop control│─▶│ Tool interface│─▶│  Permissions      │      │
   │  └────────────┘  └───────┬───────┘  └────────┬──────────┘      │
   │                          ▼                    ▼                │
   │                  ┌───────────────┐   ┌────────────────┐        │
   │                  │   Sandbox     │   │ Context delivery│◀──┐    │
   │                  └───────┬───────┘   └────────┬────────┘   │    │
   │                          ▼                    │            │    │
   │                  ┌───────────────┐            │            │    │
   │                  │  Persistence  │            │            │    │
   │                  └───────────────┘            │            │    │
   │  ┌────────────┐  ┌───────────────┐  ┌─────────▼────────┐   │    │
   │  │  Memory    │  │Planning       │  │  Verification    │───┘    │
   │  │            │  │artifacts      │  │  + Eval hooks    │        │
   │  └────────────┘  └───────────────┘  └─────────┬────────┘        │
   │                                                ▼                 │
   │                                      ┌──────────────────┐        │
   │                                      │  Observability   │        │
   │                                      └──────────────────┘        │
   └────────────────────────────────────────────────────────────────┘
```

## Key Takeaways for Section 2

Ten (arguably eleven, counting eval hooks) nameable components make up a
harness; four of them are things this folder already built in Chapters 2–4
under different names, and the rest — planning artifacts, memory,
verification, permissions, sandbox, persistence, observability — are the
territory the rest of B04 opens up, chapter by chapter.

*Next: a single analogy that makes all ten components click into place at
once, because most working engineers already have this mental model
installed from an unrelated subject.*

---

# 3: The Harness as an Operating System

## The Simple Version First

If you've ever wondered why an app can't just directly grab another app's
memory, or why deleting a file usually asks "are you sure" first — that's
your operating system stepping in between what a program *wants* to do and
what it's actually *allowed* to do. A harness plays exactly the same role
for a model: the model wants to do things (call a tool, read a file,
overwrite something), and the harness is the layer that decides what
actually happens as a result.

## The Analogy, Mapped Precisely

| Operating system concept | Harness equivalent | Concrete example from this folder |
|---|---|---|
| A running **process** | The agent loop | Chapter 2's `while` loop |
| **System calls** (`syscall`) | Tool calls | Chapter 3's `tool_use` blocks |
| The **filesystem** | The agent's workspace | Section 6 below |
| The **scheduler** | Whatever decides which task/subagent runs next | Chapter 13's multi-agent orchestration |
| **Permissions** (file modes, capabilities) | The permission layer | Chapter 16 |
| **System logs** | Traces and observability | Chapter 15 |

Two specific, sharper versions of this analogy are worth knowing by name,
because each highlights a different half of the picture. One framing treats
**the model as the CPU and the harness as the operating system**: the CPU
executes instructions fast and faithfully, but it has no opinion about
which process should run next, whether a write is authorized, or what
happens when something crashes — that's all the OS's job, and it's exactly
the harness's job around a model that only knows how to predict the next
token. A second, sharper framing treats **the model as an untrusted user**,
with tools and skills as the system calls and programs available to that
user — a framing worth sitting with because operating systems were designed,
from the start, around the assumption that the *user* might make mistakes
or attempt something harmful, and every permission check, sandbox boundary,
and audit log exists because of that assumption, not despite it. Applying
that same assumption to a language model — capable and well-intentioned, but
still worth bounding — is precisely the mindset Chapter 16 builds out fully.

## Why This Analogy Actually Pays Off (Not Just a Nice Picture)

The payoff is concrete: every time you're unsure which of the ten Section 2
components should own a new piece of behavior, ask the OS question first.
"Should the model decide whether a shell command is safe to run, or should
something outside the model decide?" — phrased as an OS question, the answer
is obvious (a program doesn't get to decide its own permissions; the OS
does), which makes the harness answer obvious too: that decision belongs in
the **permissions** component, enforced in code, not left to the model's own
judgment. This single analogy will get invoked again directly in Section 4
(determinism) and Chapter 16 (security) because it keeps producing the right
answer.

## Key Takeaways for Section 3

A harness relates to a model the way an operating system relates to a
running program: the model/CPU/process does the work, but the
harness/OS/kernel decides what it's allowed to touch, mediates every
request to the outside world, and keeps a record of what happened. When
unsure which harness component owns a decision, ask what an OS would do
with an equivalent request from an untrusted user process — the answer
usually transfers directly.

*Next: this analogy, made precise enough to actually write code from —
which parts of a harness must never be left to model judgment.*

---

# 4: Determinism Where It Matters

## The Simple Version First

Some things about an agent's behavior should be exactly the same every
single time, no matter how the model is feeling that day (models don't
have feelings, but they do have sampling randomness, and that's close
enough to the same practical problem). Other things genuinely benefit from
the model's judgment varying run to run — that's what makes it useful for
open-ended tasks in the first place. The hard part is knowing, precisely,
which category a given decision falls into, *before* you build it, not
after a model decides something surprising in production.

## A Rule of Thumb, Then a Boundary

Here's a rule of thumb worth internalizing before any formalism: **if
getting this wrong even once is unacceptable, it cannot be left to model
judgment alone — it needs to be enforced in deterministic code at the
harness boundary.** Whether a specific file path is inside or outside the
allowed workspace is a yes/no question with a right answer that doesn't
benefit from creativity; whether a given plan is a *good* plan for solving
an ambiguous task genuinely does benefit from judgment, and forcing a rigid
rule onto that decision would make the agent worse, not safer.

Recent research gives this instinct a name worth knowing, even though it's
one specific formalization rather than an industry-wide standard yet: the
2026 "Convergent AI Agent Framework" (CAAF) paper argues that a harness
should function as a **deterministic constraint boundary** — the specific
test it proposes is that authorization decisions, input validation, audit
logging, and the mapping from an approved action to what actually executes
must *all* be deterministic given the same inputs, even while the model's
own reasoning inside that boundary stays fully non-deterministic. Their
sharpest one-line version of the whole idea: **"systems can tolerate
nondeterminism inside reasoning; they cannot tolerate nondeterminism in
enforcement."** That sentence is worth remembering on its own, independent
of the rest of the paper's specific proposal.

## Applying the Boundary Test

| Decision | Deterministic (harness) or judgment (model)? | Why |
|---|---|---|
| Is this file path inside the workspace? | Deterministic | A path either resolves inside the allowed directory or it doesn't — no ambiguity to reason about |
| Does this tool call's JSON match its schema? | Deterministic | Chapter 3's `strict: true` — a validation question, not a judgment call |
| Is this the *right* tool to call for the current subtask? | Model judgment | Genuinely benefits from reasoning about the specific situation |
| Should a destructive call proceed without asking a human? | Deterministic (the gate itself) | Chapter 7's `destructive` flag either requires approval or it doesn't — the harness enforces this regardless of what the model "thinks" is fine |
| How should the final answer be worded? | Model judgment | No single correct phrasing exists to enforce |

## Key Takeaways for Section 4

Ask, for every new harness decision, whether getting it wrong even once is
acceptable. If not, it belongs in deterministic code at the harness
boundary, never in model judgment alone — the CAAF paper's framing of this
is worth keeping close: nondeterminism is fine inside reasoning, never
inside enforcement. This same test will resolve most "should this be a
prompt instruction or a code check" questions this folder raises from here
forward.

*Next: the specific durable-instruction mechanism every current coding
agent ships, and how it fits — or doesn't fit — this chapter's
determinism test.*

---

# 5: Instruction Files and Repo Conventions

## The Simple Version First

Imagine a company handbook, except instead of one document for the whole
company, there's a general one at the top, and then a shorter, more
specific one inside each department's folder that only applies once you're
working in that department. A new instruction file convention — `AGENTS.md`
(and Anthropic's own `CLAUDE.md`) — does exactly this for a coding agent's
durable instructions, and it exists because stuffing everything into one
giant system prompt (Chapter 4, Section 3's "right altitude" problem)
doesn't scale past a small project.

## What These Files Actually Are

`AGENTS.md` is a cross-tool, vendor-neutral standard, now governed under
the Linux Foundation, adopted across more than 60,000 open-source
repositories as of mid-2026. `CLAUDE.md` is Anthropic's own, Claude
Code–specific convention — and as of spring 2026, Claude Code also reads a
plain `AGENTS.md` when no `CLAUDE.md` is present, closing what used to be a
real cross-tool compatibility gap. This repository's own root `CLAUDE.md`
(the file governing how notes like this one get written) is a working
example of exactly this pattern, one level up from the code itself.

## Hierarchical Scoping

Both conventions support **nesting**: a repository can have one instruction
file at the root, plus more specific ones inside subdirectories, and an
agent that discovers these files walks the directory tree, composing them
together — with the file closest to whatever is actually being edited
taking precedence over a more general one further up, and an explicit
instruction from the user overriding all of them. Anthropic's own hierarchy
adds a third layer above the repo: a personal, global instruction file
(under the user's own home directory) for preferences that should apply
across *every* project, not just one.

```
~/.claude/CLAUDE.md          <- personal, global, every project
        │
repo-root/CLAUDE.md          <- project-wide conventions
        │
repo-root/frontend/CLAUDE.md <- only loaded when working in frontend/
        │
repo-root/backend/CLAUDE.md  <- only loaded when working in backend/
```

## Why This Beats One Long System Prompt

Chapter 4, Section 3 already established that the system prompt is a fixed,
non-shrinking line item in the token budget — every token in it is paid on
*every single call*, forever. A single, ever-growing system prompt trying
to cover an entire monorepo's conventions is exactly the kind of "too
prescriptive, brittle, doesn't scale" failure that Chapter 4's "right
altitude" guidance warned about. Hierarchical instruction files fix this
directly: a change working only in the `backend/` folder never pays for the
`frontend/` folder's conventions, because that file is never loaded into
context for that turn at all — this is Chapter 4's **select** operation
(Section 4 of that chapter), applied to instructions instead of documents.

## Key Takeaways for Section 5

`AGENTS.md` (cross-tool, Linux Foundation-governed) and `CLAUDE.md`
(Anthropic-specific, now also AGENTS.md-compatible) both externalize durable
instructions out of the system prompt and into nested files an agent
discovers by walking the directory tree, with the closest file to the
current work taking precedence. This is a direct application of Chapter 4's
"select" operation to instructions, and it scales in a way a single
ever-growing system prompt structurally cannot.

*Next: instruction files tell an agent how to behave — the workspace itself
is where it keeps track of what it's actually done.*

---

# 6: The Workspace/Filesystem as State

## The Simple Version First

Chapter 4, Section 9 already introduced the core idea: an agent that writes
its progress to a real file survives a context reset, because the file was
never only inside the context window to begin with. This section names the
*general* pattern that idea is one instance of: **the filesystem is a harness
component in its own right, not just a place tool results happen to land.**

## Three Concrete Uses, Beyond Chapter 4's Notes File

**Scratchpads** — a working file for the agent's own intermediate
reasoning or draft output, useful specifically because it doesn't cost
context tokens the way keeping the same content in the message list would
(Chapter 4's whole cost argument, applied here). **Plan files** — a
structured, checkable artifact (often literally a markdown checklist) that
the agent writes once at the start of a multi-step task and updates as it
goes; this is Section 2's "planning artifacts" component, and it gets a
full chapter of its own (Chapter 7) specifically because a plan that lives
only in a sentence buried in the transcript is exactly the kind of thing
Chapter 4's compaction can quietly lose. **Decision logs** — Chapter 4,
Section 6's mitigation for compaction losing why-reasoning, generalized: any
append-only file recording *why* a choice was made, independent of whatever
happens to the conversation containing that choice.

## Why This Belongs to the Harness, Not the Model

Section 3's OS analogy answers this directly: a process doesn't invent its
own filesystem layout — the OS provides one, with a directory structure,
permissions, and guarantees about what survives a crash. Equally, an agent
shouldn't be improvising *where* its plan file or scratchpad lives on each
run — the harness should own a fixed, predictable workspace layout (a
`.agent/` directory, say, with `plan.md`, `notes.md`, and `decisions.log`
as known, harness-guaranteed paths) so that every other component — hooks,
permissions, persistence — can rely on that layout being stable rather than
whatever the model happened to invent this time.

## Key Takeaways for Section 6

The filesystem is a full harness component, not incidental storage:
scratchpads, plan files, and decision logs all use it to hold state that
must survive longer than one context window, and the harness — not the
model — should own a fixed, predictable workspace layout so every other
component can depend on it.

*Next: the mechanism that actually lets the harness intervene at each of
these moments — hooks.*

---

# 7: Hooks and Lifecycle Events

## The Simple Version First

A hook is just a piece of your own code that the harness promises to run at
a specific, named moment — "right before any tool runs," "right after a
tool finishes," "right before the conversation gets compacted" — and that
code gets to look at what's about to happen and say yes, no, or "do this
slightly differently instead." It's the concrete mechanism behind Section
4's determinism rule: a hook is where you put a check that must never be
skipped, because unlike a prompt instruction, the model has no way to
"forget" or talk its way around a hook.

## A Worked Example, Traced Step by Step

The clearest real illustration is one Anthropic ships as a documented
pattern for the Claude Agent SDK: blocking any tool call that tries to
write to a `.env` file, regardless of what the model intended.

```python
async def protect_env_files(input_data, tool_use_id, context):
    file_path = input_data["tool_input"].get("file_path", "")
    file_name = file_path.split("/")[-1]
    if file_name == ".env":
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": "Cannot modify .env files",
            }
        }
    return {}  # empty object = allow the operation unchanged
```

Tracing this through Section 3's OS analogy: the model emits a `Write`
tool call (its "syscall"); before that syscall actually executes, the
**`PreToolUse`** event fires; the harness checks whether any hook is
registered for that event with a matching pattern (here, a `matcher` of
`"Write|Edit"` — hooks are filtered by tool name so they don't run on every
single event); the matching hook's callback runs *your* code, inspects the
one argument it cares about (`file_path`), and returns a decision object;
the harness obeys that decision unconditionally. The model never sees this
happen except as a result — it attempts the write, and the write simply
doesn't happen, with a stated reason. This is Section 1's "structurally
impossible to repeat" claim made completely literal: there is no phrasing
of "please write to `.env`, it's really necessary this time" that gets past
this hook, because the hook never reads the model's reasoning at all — only
the tool name and the file path.

## The Event Catalog, Selectively

The current Claude Agent SDK exposes roughly thirty distinct lifecycle
events — far more than any one project needs, but worth knowing the shape
of the full space rather than memorizing all of them:

| Event | Fires when | Typical use |
|---|---|---|
| `PreToolUse` | A tool is about to run | Block or rewrite a dangerous call (the example above) |
| `PostToolUse` | A tool just finished | Audit logging — note that by this point the action already happened, so this can log or react, never prevent |
| `PostToolUseFailure` | A tool call raised an error | Chapter 2, Section 6's `is_error` handling, from the harness side |
| `UserPromptSubmit` | The user (or a calling program) submits a new prompt | Inject additional context before the model ever sees the prompt |
| `PreCompact` / `PostCompact` | Right before / after Chapter 4's compaction runs | Archive the full transcript before it's summarized; log what the summary kept |
| `SubagentStart` / `SubagentStop` | A Chapter 13-style sub-agent starts or finishes | Track parallel work, aggregate results |
| `PermissionRequest` | A tool call needs an explicit approval decision | Chapter 16's permission layer, as an event rather than inline logic |
| `SessionStart` / `SessionEnd` | A session begins or ends | Initialize logging; clean up resources |
| `Stop` | The agent's run concludes | Persist final state (Section 2's "persistence" component) |

Every hook is filtered by a **matcher** — a pattern tested against the
event's target (usually the tool name), so a hook registered with
`matcher="Bash"` only ever fires for `Bash` calls, not every tool call in
the session. This filtering is itself a small, concrete example of the
"select" operation from Chapter 4: choosing which registered code actually
needs to run for a given event, rather than running everything on every
event.

## Key Takeaways for Section 7

A hook is your own code, guaranteed to run at a specific, named lifecycle
moment (`PreToolUse`, `PostToolUse`, `PreCompact`, and roughly thirty
others), filtered by a matcher pattern, returning a decision the harness
obeys unconditionally. This is the literal mechanism for Section 4's
determinism rule — a check placed in a hook cannot be talked around by the
model, because the hook never reads the model's reasoning, only the
concrete facts of the event itself.

*Next: once a harness has this many independently-changeable parts, how do
you keep track of which configuration you're actually running?*

---

# 8: Harness Versioning and Configuration

## The Simple Version First

If your harness is a recipe with ten ingredients (Section 2's ten
components), and you keep tweaking ingredients without writing down what
changed and when, you will eventually have no idea which version of the
recipe produced last Tuesday's good result. Harness versioning is just:
write it down, every time.

## Treating the Harness as a Real Artifact

Concretely, this means the harness's configuration — which hooks are
registered, what the permission rules are, which model and prompt-caching
settings are active, what the workspace layout looks like — should be
committed, versioned, and changelogged the same way application code is,
not left as ambient, undocumented state in whoever's terminal happens to be
running it. A harness version bump should read like any other changelog
entry: "v1.4: added a `PreToolUse` hook blocking writes outside the
workspace; tightened the token budget in `ContextManager` from 3,000 to
4,000 for the system prompt category." Specific, dated, attributable to one
commit.

## Why This Matters More Than It Sounds

The payoff isn't bookkeeping for its own sake — it's what makes Section 10
and Section 11 possible at all. An eval score is only useful if you can
answer "which harness produced this score," and that question is
unanswerable if the harness isn't a versioned, named thing in the first
place. This is the direct setup for the next two sections: Section 10
proposes a specific workflow built on top of harness versioning, and
Section 11 proves, with a concrete dry-run, exactly why that workflow has to
change one thing at a time to stay meaningful.

## Key Takeaways for Section 8

A harness configuration should be committed and changelogged like any other
code artifact — specific, dated, one commit per change — because every
later question of the form "did this change help or hurt" is unanswerable
unless the harness itself is a versioned, nameable thing you can point to.

*Next: what a real harness looks like once someone has actually built and
shipped one — a guided tour of two current examples.*

---

# 9: Reading a Real Harness: Claude Agent SDK and deepagents

## The Simple Version First

The best way to check whether Section 2's ten-component list is a real
description of how harnesses work, rather than something invented for this
chapter, is to take two actual shipped harnesses — built by different
teams, on different underlying frameworks — and check whether their
features map cleanly onto that same list. They do, which is itself
evidence worth noting.

## The Claude Agent SDK, Mapped

| SDK capability | Maps to component | Notes |
|---|---|---|
| Built-in tools (Read, Write, Edit, Bash, WebFetch, ...) | Tool interface | Chapter 3's whole subject, pre-built |
| Hooks | Determinism boundary (Section 4, 7) | ~30 lifecycle events |
| Subagents | Isolation (Chapter 4 §10) | Spawns a sub-agent with its own context |
| MCP | Tool interface, transport layer | Chapter 3, Section 10 |
| Permissions | Permission layer | Chapter 16 |
| Sessions | Persistence, context delivery | Resume or fork a prior run |
| Skills, commands, memory | Progressive disclosure, instruction files | Chapter 8; Section 5 above |
| Plugins | Harness versioning/packaging | Bundle skills, agents, hooks, and MCP servers together, loadable by path |

The SDK's own framing of itself is worth quoting directly because it names
the exact same "harness, not framework" distinction Section 12 below warns
about: it is "a library that runs the agent loop in your own process" —
you still own deployment, still choose what to configure, and the SDK is
explicit that it sits beside, not above, a fully manual Chapter 2-style
loop or a fully managed, Anthropic-hosted alternative, depending on how much
of the harness you want to own yourself.

## deepagents, Mapped

LangChain's `deepagents` project, built on top of LangGraph, converges on
strikingly similar territory independently:

| deepagents capability | Maps to component |
|---|---|
| Filesystem abstraction (pluggable local/sandboxed/remote backends) | Section 6 (workspace), Section 2 (sandbox) |
| Sub-agents with isolated context windows | Isolation (Chapter 4 §10) |
| Context management (summarization, tool-output offloading) | Chapter 4's entire subject |
| Human-in-the-loop approval | Permissions (Chapter 16) |
| Persistent memory (pluggable backends) | Memory (Chapter 9) |
| Skills system | Progressive disclosure (Chapter 8) |

Its construction API is a useful contrast point with Chapter 2's from-scratch
loop — the same underlying ten components, expressed as configuration
instead of hand-written code:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[my_custom_tool],
    system_prompt="You are a research assistant.",
)
result = agent.invoke({"messages": "Research LangGraph and write a summary"})
```

## What Converging Independently Actually Proves

Anthropic and LangChain did not coordinate on a shared harness
specification — they built for different underlying models and different
runtimes, and arrived at nearly the same component list anyway. That's
reasonably strong evidence the ten-component decomposition in Section 2
describes something structural about what *any* production agent needs, not
an arbitrary way of organizing this one course.

## Key Takeaways for Section 9

Two independently built, currently-shipping harnesses — the Claude Agent
SDK and LangChain's `deepagents` — map cleanly onto Section 2's same ten
components despite sharing no common codebase, which is real evidence the
decomposition describes something structural rather than one team's
opinion. Both are explicit that they are harnesses *you still deploy and
configure*, not managed black boxes.

*Next: given a harness this composable, what's the actual discipline for
improving it over time?*

---

# 10: The Hill-Climbing Method

## The Simple Version First

If you're adjusting a recipe and want to know whether adding more salt
actually improved it, you change the salt — and only the salt — cook it
again, and taste. Change the salt *and* the cooking time in the same
attempt, and a better result tells you nothing about which change deserves
credit. **Hill-climbing** is exactly this discipline, applied to a harness:
change one named component (Section 2's list), run your eval suite (Chapter
14 builds this properly; for now, any repeatable, scored task suite works),
and keep the change only if the score improved.

## The Workflow the Rest of This Folder Assumes

```
1. Pick ONE harness component to change (e.g. the permission rule set)
2. Bump the harness version, write down what changed (Section 8)
3. Run the eval suite against BOTH the old and new harness version
4. Compare scores
5. Score improved (or held steady with some other real benefit)?
     -> keep the change, this is now the new baseline
   Score got worse?
     -> revert, the old version is still the baseline
6. Repeat with the next single component
```

This is, deliberately, nothing more exotic than the scientific method's
core discipline — isolate one variable — applied to software you're
iterating on rather than a lab experiment. What makes it worth naming
explicitly as "the workflow the rest of the folder assumes" is that later
chapters (14's formal evals, 17's production hardening) both lean on this
exact loop already being in place; they add rigor to steps 3 and 4, not a
different workflow.

## Key Takeaways for Section 10

Hill-climbing is: change exactly one harness component, run the eval suite,
keep the change if it helped, revert if it didn't, repeat. It's the
scientific method's single-variable discipline applied to harness
iteration, and it's the assumed workflow behind every later chapter that
talks about improving an agent over time.

*Next: the concrete, worked reason changing one thing at a time isn't just
good practice — it's the only version of this workflow that produces a
result you can actually trust.*

---

# 11: Dry-Run: Why One-Change-Per-Version Is the Only Attributable Design

## The Intuition

If two suspects were both in the room when something went missing, and only
one of them actually did it, looking at "the thing went missing" tells you
nothing about which suspect is responsible — you needed to know who was in
the room *alone* at some point to ever pin it on one of them specifically.
Changing two harness components in the same version and watching the eval
score move is exactly this situation: the score changed, but you cannot
say which component deserves the credit or the blame.

## The Setup

Suppose five harness versions are tried in sequence, and — deliberately, to
make the failure mode concrete — **two components are changed in each
version** rather than one:

| Version | Components changed | Eval score | Score delta |
|---|---|---|---|
| v1 (baseline) | — | 62 | — |
| v2 | Permissions, Context delivery | 68 | +6 |
| v3 | Context delivery, Memory | 65 | -3 |
| v4 | Memory, Tool interface | 71 | +6 |
| v5 | Tool interface, Permissions | 69 | -2 |

## Why This Table Cannot Be Attributed, Even in Principle

Look specifically at v2's +6 and v5's -2. Both versions touch **Permissions**
and both touch **Tool interface** (once each), and both also touch a second
component each time. Did the +6 in v2 come from the permissions change, the
context-delivery change, or some interaction between the two working well
together? The table cannot answer this — and critically, **no amount of
additional analysis of this specific data can answer it either**, because
the information needed (a score for "permissions changed alone, nothing
else") was never produced. This is not a limitation of statistics or
cleverness; it's a limitation of the experiment design itself. With $C$
components and $k=2$ changed per version, distinguishing every component's
individual effect in the worst case requires on the order of $2^C$ separate
runs (every possible subset), not the 5 actually run here — hopelessly
expensive to ever actually do for $C = 10$.

## The Fix, and Why It's the *Only* Fix

Re-run the same five decisions, changing exactly one component per version
instead of two:

| Version | Component changed | Eval score | Score delta | Attributable to |
|---|---|---|---|---|
| v1 (baseline) | — | 62 | — | — |
| v2 | Permissions | 68 | +6 | Permissions, unambiguously |
| v3 | Context delivery | 65 | -3 | Context delivery, unambiguously |
| v4 | Memory | 71 | +6 | Memory, unambiguously |
| v5 | Tool interface | 69 | -2 | Tool interface, unambiguously |

Every single delta now has exactly one possible explanation, because
exactly one thing differs between each version and the one before it. This
is the same logic as a controlled experiment in any other field: **a delta
is only interpretable when everything except one variable was held fixed.**
It isn't that one-change-per-version is the *best practice* among several
reasonable options — Section 10's whole hill-climbing workflow only
produces a trustworthy signal at all under this constraint; change two
things per step, and every subsequent "keep or revert" decision in the
whole climb is built on a guess, not a measurement, even if every individual
score is measured perfectly.

## Key Takeaways for Section 11

Changing $k \geq 2$ harness components per version makes individual deltas
fundamentally unattributable, not just harder to interpret — the
information needed to assign credit was never collected, and no analysis
recovers it after the fact. Changing exactly one component per version is
the only design where every eval-score delta has exactly one possible
explanation, which is precisely why Section 10's hill-climbing method
requires it, not just recommends it.

*Next: the mistakes this chapter's ideas produce when applied carelessly.*

---

# 12: What This Chapter Still Leaves Open

## Real Gotchas, Named Precisely

**Treating the framework as the harness.** Adopting the Claude Agent SDK or
`deepagents` (Section 9) does not mean the harness work is done — both are
explicit that you still own deployment, still choose what permissions to
grant, still decide the workspace layout. A team that installs a framework
and stops thinking about Section 2's ten components has swapped "no
harness" for "an unexamined harness," which is not obviously safer.

**Changing five things at once.** Section 11 proved this in full — it isn't
merely undisciplined, it produces eval deltas with no possible correct
attribution, poisoning every subsequent hill-climbing decision built on top
of that data.

**Putting rules in the prompt that the harness should enforce in code.**
This is Section 4's determinism test, violated in the specific direction
that actually causes incidents: "please never write outside the `src/`
folder" as a system-prompt sentence is a request the model can be talked
out of, misread, or simply forget three thousand tokens later (Chapter 4's
recency-bias argument). The identical rule as a `PreToolUse` hook (Section
7) cannot be talked out of anything, because it never reads the model's
reasoning at all.

## What's Still Missing, By Design

| Missing capability | Symptom without it | Where it's built |
|---|---|---|
| **A real planning-artifact system** | Section 6 named plan files as a pattern; nothing here builds one properly | Chapter 7 |
| **Real verification, not just a hook that could hold one** | Section 7 gives the mechanism; nothing here decides what "verified" means | Chapter 6, Chapter 14 |
| **A working permission layer** | Section 4 and 7 both point at where it would live; nothing here implements one | Chapter 16 |
| **A real sandbox** | Section 3's OS analogy assumes tools run somewhere bounded; this chapter never builds that boundary | Chapter 16 |
| **Persistence across a crash, not just across a context reset** | Section 6's files survive a reset; they don't by themselves resume a killed process cleanly | Chapter 12 |
| **A formal eval suite** | Section 10 and 11 both assume one exists to run hill-climbing against | Chapter 14 |

## Key Takeaways for Section 12

The three gotchas — mistaking a framework for a finished harness, changing
multiple components per version, and enforcing in the prompt what belongs
in code — are the concrete failure modes of applying this chapter's ideas
carelessly. What remains unbuilt (planning artifacts, verification,
permissions, sandboxing, crash-durable persistence, formal evals) each has
an exact later chapter, continuing the discipline every chapter in this
folder has closed with so far.

*Next: the whole chapter, compressed into one table.*

---

# 13: Key Takeaways + Master Decision Table

The single mental model for this chapter: **a harness is everything around
the model that isn't the model, it decomposes into roughly ten independently
buildable components, and its entire purpose is making specific failures
structurally impossible rather than hoping the model tries harder next
time.**

| I want to know... | Reach for | Key fact |
|---|---|---|
| What "harness" actually means, concretely | Section 1 | Everything around the model that isn't the model — code you own and can change today |
| What the ten components are | Section 2 | Loop control, tool interface, context delivery, planning artifacts, memory, verification, permissions, sandbox, persistence, observability (+ eval hooks) |
| How to reason about a new harness design question | Section 3 | Ask what an OS would do with an equivalent request from an untrusted process — the answer usually transfers |
| Whether a decision belongs in code or in model judgment | Section 4 | If getting it wrong even once is unacceptable, it's deterministic code at the boundary, never model judgment alone |
| How to scale durable instructions past a monorepo | Section 5 | Hierarchical `AGENTS.md`/`CLAUDE.md` files, closest-to-the-work file wins — Chapter 4's "select" applied to instructions |
| Where an agent should keep state that must outlive one context window | Section 6 | The filesystem, in a harness-owned, predictable layout — not wherever the model happens to write |
| How to enforce a rule the model literally cannot talk its way around | Section 7 | A hook (`PreToolUse` and ~30 others) — it reads only the event's facts, never the model's reasoning |
| Why harness changes need a changelog | Section 8 | Every later "did this help" question is unanswerable unless the harness is a versioned, nameable thing |
| What a real, shipped harness looks like | Section 9 | Claude Agent SDK and `deepagents` converge independently on the same ten components |
| The actual workflow for improving a harness | Section 10 | Change one component, run the eval suite, keep or revert, repeat |
| Why "one change per version" isn't just tidy, it's required | Section 11 | With ≥2 changes per version, the information needed to attribute a delta was never collected — no analysis recovers it afterward |

**Connection forward:** Chapter 6 zooms into the single component this
chapter named but didn't open up — **loop control** — and asks the harder
question underneath Chapter 2's basic `while` loop: how does an agent decide
*when it's actually done*, catch itself before declaring premature victory,
and recover from a step that clearly went wrong, rather than just checking
`stop_reason` and moving on.
