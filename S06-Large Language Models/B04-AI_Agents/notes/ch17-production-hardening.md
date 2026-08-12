# Chapter 17: Production Hardening — Cost, Latency, Drift, Resilience

## Table of Contents

1. [Cost Discipline](#1-cost-discipline)
2. [Prompt Caching in Anger](#2-prompt-caching-in-anger)
3. [Model Routing and the Open-Model Threshold](#3-model-routing-and-the-open-model-threshold)
4. [Latency Engineering](#4-latency-engineering)
5. [Throughput and Concurrency](#5-throughput-and-concurrency)
6. [Drift Detection](#6-drift-detection)
7. [Self-Healing in Production](#7-self-healing-in-production)
8. [Rollout Practice](#8-rollout-practice)
9. [Capacity and the GPU You Own](#9-capacity-and-the-gpu-you-own)
10. [Operational Runbook](#10-operational-runbook)
11. [Dry-Run: Full Cost Model for a 20-Step Agent, and the GPU Break-Even](#11-dry-run-full-cost-model-for-a-20-step-agent-and-the-gpu-break-even)
12. [Key Takeaways and Master Decision Table](#12-key-takeaways-and-master-decision-table)

---

# 1: Cost Discipline

## Starting From Plain Language

Every chapter before this one optimized for correctness, safety, or observability, largely treating cost as a number to report rather than a number to actively manage. This chapter's premise is that once an agent is running in production, at real volume, cost stops being a footnote and starts being one of the two or three numbers that determine whether the project survives contact with a budget review — and the single most important discipline in this section is picking the *right* cost number to optimize, because the wrong one actively rewards making the system worse.

## Cost Per Solved Task Is the Only Metric That Matters

Chapter 14 Section 6 already introduced "cost per solved task" as a trajectory metric, and Chapter 15 Section 8 built the attribution machinery to compute it live. This chapter promotes it from "one useful metric among several" to "the only cost metric that should ever drive a decision," and the reason is a trap the README's own gotchas name directly: **optimizing token price while step count explodes**. Cost per *token* or cost per *run* can both be driven down while the system gets net worse — route every step to the cheapest possible model and cost-per-token drops, but if the cheap model fails more often and needs more retries and more steps to reach the same answer (or fails outright and needs a human to finish the job), the *task* got more expensive even though every individual token got cheaper. Cost per solved task is the one denominator that closes this loophole by construction: it divides total spend by the number of tasks that actually succeeded, so a change that saves money per token but increases failures or step count fails to look like a win the moment you divide by a smaller number of successes.

## The Levers, Named

**Caching** (Section 2) reduces the price of tokens you'd be sending anyway, by exploiting the fact that a large fraction of an agent's context is identical across consecutive calls. **Model routing** (Section 3) reduces the price of tokens by sending easier sub-tasks to a cheaper model instead of paying frontier-model rates for every step regardless of difficulty. **Context budget** (Chapter 4's territory, revisited here through a cost lens) bounds how large the context is allowed to grow at all, which caps the token volume every other lever is applied to — a context budget violated is a cost multiplier applied to every subsequent step in the run, not just the step that violated it. **Step count** is, per Section 4 below, the single biggest lever of all for both cost and latency simultaneously, because every step carries its own fixed overhead (a full round-trip, a full re-send of whatever context isn't cached) on top of whatever that step's own work costs. **Subagent count** (Chapter 13's fan-out pattern, revisited through Chapter 15 Section 8-Bis's finding that an orchestrator's synthesis step can be the single largest cost driver in a multi-agent run) is a lever specifically because more subagents means more parallel branches *and* a larger aggregation cost at the point they're combined — the tradeoff isn't free just because the branches run concurrently. **Early stopping** — recognizing, mid-run, that continuing is unlikely to produce a better outcome than stopping now and either returning a partial answer or escalating (Chapter 16 Section 7's HITL territory) — directly caps the cost of the worst-case runs, which are disproportionately expensive precisely because they're the ones that keep going without making progress.

## Key Takeaways for Section 1

Cost per *solved task*, not cost per token or cost per run, is the metric to optimize, because it's the only one of the three that penalizes a "cheaper" change that actually increases failures or step count. Six levers move it: caching and model routing lower the price of tokens you send, context budget and step count cap how many tokens get sent at all, subagent count trades parallelism for aggregation cost, and early stopping caps the cost of the runs most likely to be wasting money without making progress.

---

# 2: Prompt Caching in Anger

## Starting From Plain Language

Chapter 4 already established the mechanics of prompt caching and flagged a tension with context compaction. This section is that same tension revisited specifically as a cost-engineering problem, with real, current pricing numbers attached, because "prompt caching helps" is not actionable until you know exactly *how much* it helps for a specific prefix-design choice, and exactly what breaks it.

## Stable Prefix Design and Cache Breakpoints

A cache **breakpoint** is a marker in your request telling the API "everything up to here is a candidate for caching" — on Bedrock and the Claude API, you can mark up to **4** such breakpoints in a single prompt, meaning you can cache up to four independently-stable regions (a system prompt, a tool-definitions block, a long reference document, and a growing-but-still-partially-stable conversation history, for instance) rather than being limited to one all-or-nothing cached prefix. **Stable prefix design** is the discipline of arranging your prompt so that the content most likely to stay byte-identical across consecutive calls — system instructions, tool schemas, reference material — comes first and is marked with a breakpoint, while content that changes every call (the newest turn, the freshest tool result) comes after the last breakpoint and is never expected to hit the cache at all. Get this ordering wrong — interleave stable and volatile content, or put the volatile part first — and the cache has nothing byte-identical to match against on the next call, silently paying full price while looking, from the code, like caching should be working.

## TTL Behavior and Its Direct Cost Tradeoff

A cache entry expires after its TTL if unused. Bedrock offers two tiers as of early 2026: a **5-minute TTL**, where writing to the cache costs **1.25×** the normal input token price and reading from it costs **0.1×** (a 90% discount) — and a longer **1-hour TTL**, which went generally available on Bedrock in January 2026 for Claude Sonnet 4.5, Haiku 4.5, and Opus 4.5, where the write premium rises to **2×** normal input price, meaning a 1-hour cache write needs **at least two reads** before it's cheaper than not caching at all, exactly twice the break-even bar of the 5-minute tier's 1.25× write. The choice between the two tiers is a direct bet on your traffic pattern: bursty traffic with gaps longer than 5 minutes between calls to the same prefix wastes a 5-minute-TTL cache (it expires before the next hit arrives) but might still profit from the 1-hour tier if calls land within an hour of each other; steady, frequent traffic profits from the cheaper 5-minute write premium since the cache rarely has a chance to expire unused anyway.

## The Compaction/Caching Tension, Quantified

Chapter 4 flagged, in general terms, that compacting context (rewriting or summarizing older turns to keep the context window manageable) and caching context (keeping a prefix byte-identical so it matches) pull in opposite directions — compaction, by definition, changes the prefix, and a changed prefix is a cache miss on every single call downstream of the point where compaction happened, until a new stable region re-forms and gets re-cached from scratch. Concretely: a 20-step agent that compacts its history once, at step 10, pays the *full* 1.25× (or 2×) write premium again at step 10 for content that used to be sitting in a cheap 0.1×-read cache, and every call from step 10 onward starts re-accumulating cache benefit from zero rather than continuing to build on the savings steps 1–9 had already established. This isn't an argument against ever compacting — Chapter 4's own reasons for compacting (bounding context growth, avoiding degraded attention over a bloated window) remain valid — but it is a real, quantifiable cost every compaction event incurs, and Section 11's dry-run below shows the scale of the savings a stable, uncompacted prefix design can produce over just 20 steps, which is exactly the savings a poorly-timed compaction event would erase.

## Key Takeaways for Section 2

Design prompts with the most stable content first, marked with one of up to 4 available cache breakpoints, and volatile content last, never interleaved. Pick the 5-minute TTL (1.25× write, break-even after roughly 1–2 reads) for steady traffic and the 1-hour TTL (2× write, break-even needs at least 2 reads) for bursty traffic with longer gaps. And treat every context-compaction event as a real, quantifiable cost — it invalidates the cache on everything downstream of it, resetting accumulated savings back to zero exactly at the moment it fires, which is the concrete mechanism behind the README's "caching that breaks on every run" gotcha whenever compaction (or any other prefix-mutating step) happens more often than the caching discipline assumes.

---

# 3: Model Routing and the Open-Model Threshold

## Starting From Plain Language

Not every step in an agent's loop is equally hard, and paying frontier-model prices for a step that's really just classification, extraction, or summarization is spending the same dollar-per-token rate on a task a much cheaper model would solve just as reliably. **Model routing** is the discipline of sending each step to the cheapest model that can be trusted to do that specific step's job correctly, reserving the frontier model specifically for the steps whose difficulty actually needs it — the hard reasoning, planning, or judgment calls where a cheaper model's error rate would cost more (in retries, in wrong answers, in Section 1's cost-per-solved-task terms) than the price difference saves.

## The Routing Split in Practice

A typical split routes early-pipeline, well-defined steps — classifying a request's type, extracting a structured field from unstructured text, summarizing a long tool result before it re-enters context — to a cheap model (in this repo's Bedrock setup, Haiku-class pricing), while routing the steps that require multi-step reasoning, nuanced judgment, or synthesis across multiple sources of information to the frontier model (Sonnet- or Opus-class pricing). Section 11's dry-run below uses an illustrative 30% cheap / 70% frontier split across a 20-step agent as a concrete worked example, but the *right* split for any specific harness is an empirical question, not a fixed ratio — which is exactly why the next paragraph exists.

## When Self-Hosted Open Models on Your Own GPU Are the Right Call

This repo's setup includes an RTX A6000 with 94GB of RAM specifically because, for a fraction of an agent's steps — the cheapest, highest-volume, least-judgment-demanding ones — a quantized open-weight model served locally via something like vLLM can be cost-competitive with, or dramatically cheaper than, even the cheapest hosted API tier, once you're already paying for the GPU's existence regardless of utilization. Section 9 develops this threshold in full, and Section 11's dry-run computes a concrete break-even utilization number for it, but the routing-relevant point here is narrower: self-hosting only makes sense for the *routed-to-cheap* fraction of steps, never as a blanket replacement for the frontier model's steps, both because a locally-served open model is competing against Haiku-class pricing (already cheap) rather than Sonnet/Opus-class pricing (where the API's per-token price is high enough that almost any volume favors self-hosting sooner), and because the steps you'd route to a cheap model in the first place are, by construction, the steps where a smaller, locally-hosted model's lower ceiling on reasoning quality matters least.

## The Routing Eval You Need to Justify It

The README's gotchas name a specific and common failure directly: **routing chosen by vibes, with no eval**. Deciding "step type X feels easy enough for the cheap model" without measuring it is exactly Chapter 14's single-run-comparison mistake, applied to a routing decision instead of a harness change — a routing rule that quietly increases the failure rate of one step type by even a few points can erase the entire savings Section 1's cost-per-solved-task metric was supposed to protect, and you will not notice unless you specifically built an eval comparing the cheap-model and frontier-model success rates on exactly the step type you're proposing to route. The correct process is a direct instance of Chapter 14's whole apparatus: build (or reuse) a golden set of that specific step type, run both candidate models against it with enough seeds to clear Chapter 14 Section 7's minimum-detectable-difference bar, and only adopt the routing rule if the cheap model's success rate on that specific step type is statistically indistinguishable from the frontier model's — not merely "seems fine" from a handful of anecdotal spot-checks.

## Key Takeaways for Section 3

Route each step to the cheapest model that can be trusted to do that step's specific job — cheap models for classification/extraction/summarization, frontier models for multi-step reasoning and judgment — and treat a locally-served open model on your own GPU as a viable third tier specifically for the cheap-eligible steps, not a frontier-model replacement. Never adopt a routing rule without an eval proving the cheap-model tier's success rate on that specific step type is statistically indistinguishable from the frontier tier's; "vibes-based" routing is a direct path to the cost-per-solved-task trap Section 1 describes, just with the extra step of not even noticing it happened.

---

# 4: Latency Engineering

## Starting From Plain Language

Cost and latency are related but distinct problems, and a change that helps one can hurt the other — this section is specifically about the levers that move latency, and the single header fact worth internalizing before any of them: **cutting the step count is the biggest lever by far**, bigger than any of the more technically interesting levers below, because every step's latency floor is a full model round-trip regardless of how small that step's actual work is.

## p50 vs. p95, and Why They Need Separate Attention

**p50** (median) latency describes the typical run; **p95** describes the tail — the run that's slow for a reason that usually isn't visible in the median at all: a retry, an unusually long tool call, a step that needed more reasoning than most. Optimizing only for p50 can leave p95 completely unaddressed (a change that shaves 200ms off every run's typical path does nothing for the run that's slow because of a retry storm), and a user's experience of "this feels unreliable" is disproportionately driven by p95, not p50 — a system that's fast 95% of the time and occasionally very slow reads as flaky even if its median latency looks excellent on a dashboard. Chapter 15 Section 9 already established p50/p95 as a dashboard metric worth tracking continuously for exactly this reason; this section is about what to actually *do* once that dashboard shows a gap between the two worth closing.

## Streaming to First Token

Perceived latency and actual completion latency are different things a user experiences differently: a response that streams its first token in 300ms but takes 8 seconds to fully complete *feels* far more responsive than one that produces nothing visible for 8 seconds and then appears all at once, even though the total wall-clock time is identical. Streaming to first token doesn't reduce the actual work being done — it changes when the user starts perceiving progress, which for any interactive agent surface is often the single highest-leverage, lowest-engineering-cost latency intervention available.

## Speculative Prefetch of Likely Tools

If a harness can predict, with reasonable confidence, which tool a step is likely to call before the model's response confirming that choice has fully arrived (e.g., a step that's almost always followed by the same lookup, or a tool call whose arguments can be partially inferred from context already available), prefetching that tool's result speculatively — canceling and discarding it on the rare miss — overlaps a tool's latency with the model call's latency instead of paying for them sequentially. This is a genuinely speculative technique in the literal sense (it does wasted work on a miss), and its value is entirely a function of how predictable the harness's tool-call pattern actually is — a harness with highly varied, unpredictable tool choice gets little benefit and pays a real cost in wasted prefetch calls.

## Parallel Tool Calls and Batching

When a step's model response includes multiple independent tool calls (not dependent on each other's results), executing them concurrently rather than sequentially collapses their combined latency down to the slowest single call instead of their sum — directly Chapter 15 Section 11's critical-path logic, now applied within a single step rather than across a multi-agent fan-out. **Batching**, distinctly, groups multiple *separate* requests (across different users or different runs) into a single underlying model call where the provider supports it, trading a small amount of added latency per individual request for significantly better throughput and, often, a meaningfully lower per-token price (Bedrock's batch inference tier, mentioned in Section 9, offers roughly a 50% discount specifically in exchange for this latency tradeoff) — batching is therefore as much a cost lever as a latency one, and the two need to be weighed against each other explicitly for any given traffic pattern.

## Cutting Step Count: The Biggest Lever

Every one of the techniques above optimizes the latency *of* a step or the latency *between* steps. Cutting the number of steps a task needs at all removes an entire round-trip's worth of fixed overhead — the network latency, the time-to-first-token, the portion of the prompt that has to be re-processed even under caching — and that fixed-per-step overhead is why halving a task's step count from, say, 20 to 10 typically buys far more latency improvement than any single one of streaming, prefetching, parallelizing, or batching applied to the original 20-step version. This is also, not coincidentally, the same lever Section 1 named as a cost lever — fewer steps means both less total token volume and less accumulated per-step latency overhead simultaneously, which is exactly why a harness redesign that genuinely reduces step count (a better single-shot tool, a smarter planning step that avoids unnecessary intermediate lookups) tends to dominate every other optimization in this section combined.

## Key Takeaways for Section 4

Track p50 and p95 as genuinely separate problems — a p95 gap is invisible in the median and disproportionately drives a "this feels unreliable" user perception. Streaming to first token improves perceived latency without touching actual completion time; speculative prefetch and parallel tool calls overlap work that would otherwise run sequentially; batching trades a little latency for better throughput and often a real cost discount. But cutting the step count is the biggest lever of all, by a wide margin, because it's the only technique here that removes fixed per-step overhead entirely rather than optimizing around it.

---

# 5: Throughput and Concurrency

## Starting From Plain Language

Latency (Section 4) is about how long one run takes. Throughput and concurrency are about how many runs your system can sustain *simultaneously*, at scale, without degrading — a different problem that shows up specifically once real traffic volume arrives, and one that a system tested only with a handful of sequential runs during development will not have surfaced at all.

## Rate Limits and Retry With Jitter

Every model provider enforces rate limits (requests per minute, tokens per minute), and a harness that doesn't explicitly plan for hitting them will eventually get a rejected call in production, exactly when traffic is highest and a failure is most visible. **Retry with jitter** — retrying a rate-limited or transiently-failed call after a randomized delay, rather than a fixed delay — exists specifically to avoid the failure mode where every client that got rate-limited at the same instant retries at exactly the same instant, recreating the same spike that caused the original rejection; the randomization spreads retries out in time, which a fixed delay cannot do no matter how well-chosen the delay value is.

## Queue Depth and Backpressure

**Queue depth** is how many requests are currently waiting to be processed rather than being processed right now — a rising queue depth under steady incoming traffic is the earliest, most direct signal that the system is falling behind demand, well before that shows up as a user-visible latency spike. **Backpressure** is the deliberate choice to slow down or reject new incoming work once queue depth crosses a threshold, rather than accepting unbounded work and letting the queue grow without limit — counterintuitively, a system with backpressure that occasionally rejects a request cleanly and immediately provides a *better* experience in aggregate than a system with no backpressure that accepts everything and lets every request's latency degrade together as the queue grows unboundedly, because a clean, fast rejection is recoverable (the caller can retry with jitter) in a way that a slow, degraded response for everyone is not.

## Per-Tenant Fairness

In any system serving more than one user or customer concurrently, an unfair scheduler lets one tenant's burst of traffic degrade every other tenant's latency, even though those other tenants did nothing to cause the load — the classic "noisy neighbor" problem, well known from other multi-tenant systems and equally real for an agent harness. Per-tenant fairness (rate limits, queue priority, or capacity reservations scoped to each tenant individually rather than pooled globally) is what prevents one customer's spike from becoming every customer's incident, and it needs to be designed in deliberately — a naive global queue, first-in-first-out across all tenants, is fair in a narrow technical sense but provides zero actual isolation between tenants' traffic patterns.

## Key Takeaways for Section 5

Retry with jitter (not fixed delay) avoids synchronized retry storms after a shared rate-limit event; rising queue depth is the earliest signal of falling behind demand, well before it becomes a visible latency spike; backpressure that cleanly rejects excess load produces a better aggregate experience than accepting everything and letting quality degrade for everyone; and per-tenant fairness, designed deliberately rather than assumed from a shared FIFO queue, is what prevents one tenant's traffic burst from becoming every tenant's incident.

---

# 6: Drift Detection

## Starting From Plain Language

Every control up to this point assumes the world you tested against is the world you're still running in. **Drift** is what happens when that assumption quietly stops being true — the model, the tools, or the data your agent operates on changed underneath you, without any change on your side, and your success rate degrades for a reason that has nothing to do with your own harness code.

## Three Sources of Drift

**Model version changes underneath you** happen when a provider updates a model version you're calling — even a version string you didn't explicitly request to change, or a "latest" alias that silently points somewhere new — and the new version's behavior, while presumably better on the provider's own benchmarks, is not guaranteed to be better (or even equivalent) on your *specific* harness's specific prompts and tools, which is exactly the model-plus-harness distinction Chapter 14 Section 9 established for public benchmarks, now recurring as a live production risk instead of a benchmarking caveat. **Tool/API changes** happen when an external API your tools depend on changes its response shape, deprecates a field, or alters rate limits — your tool's code may not even error, if the change is subtle enough (a renamed field silently returning `None` instead of raising), which makes this category of drift specifically dangerous: silent degradation with no exception to catch it. **Data distribution shift** happens when the population of tasks your agent actually receives in production drifts away from what your golden dataset (Chapter 14 Section 3) was built to represent — not because anything about the model or tools changed, but because the world your users are asking about changed, and your evals, frozen at the moment they were built, don't reflect that shift until someone notices the gap.

## Canary Tasks Running Continuously Against Production

The detection mechanism for all three drift sources is the same: **canary tasks** — a small, fixed set of golden-set-style tasks (Chapter 14 Section 3's discipline, reused here for a different purpose) run continuously, on a schedule, directly against the live production configuration, with their outcomes tracked over time on exactly the kind of version-attributable dashboard Chapter 15 Section 8 built. A canary task's value comes specifically from being unrelated to any deliberate harness change — its pass/fail history should be flat over time under normal operation, and a departure from that flat baseline, correlated with a provider's own model-version rollout or a third-party API's changelog rather than anything in your own deploy history, is the signature that distinguishes drift (something external changed) from a regression (something you changed, Chapter 14 Section 2's fourth eval type). Running canaries *continuously*, not just after a deploy, is what makes them able to catch drift at all — a regression check gates your own deploys; a canary catches changes that happen on someone else's schedule, entirely outside your own deploy pipeline.

## Key Takeaways for Section 6

Drift has three distinct sources — silent model-version changes, silent tool/API changes, and data distribution shift — and none of them are caused by anything in your own deploy history, which is exactly why Chapter 14's regression harness (gated on *your* changes) cannot catch them on its own. Continuously-running canary tasks, tracked on a flat historical baseline, are the detection mechanism specifically because a departure from that baseline correlates with something external changing, not with anything you deployed yourself.

---

# 7: Self-Healing in Production

## Starting From Plain Language

Section 6 covers detecting that something is wrong. This section covers the more ambitious idea of an agent that notices its *own* failure patterns and repairs them without a human in the loop for every instance — and the honest framing, matching the README's own careful phrasing, is that this capability is exactly as valuable as it is dangerous, which is why the guardrails matter as much as the mechanism itself.

## Agents That Detect Their Own Failure Patterns and Repair Them

A concrete example: an agent whose trajectory metrics (Chapter 14 Section 6) show a specific tool call failing with the same error repeatedly across many runs — a stale cached credential, a rate limit being hit in a predictable pattern — can, in principle, detect that pattern from its own trace history and adjust its own behavior (refresh the credential preemptively, add a backoff before that specific call) without waiting for a human to notice the pattern in a dashboard and ship a fix. This is a genuinely useful capability specifically because the alternative — every recurring failure pattern requiring a human to notice it, diagnose it, and ship a manual fix — doesn't scale to the volume and variety of failure modes a production agent fleet eventually encounters.

## The Guardrails That Keep Self-Healing From Becoming Self-Destroying

The risk is structural and symmetric to everything Chapter 16 built: an agent empowered to modify its *own* behavior in response to observed failures is, definitionally, an agent with write access to something that shapes every future run's behavior — precisely Chapter 16 Section 4's persistent-injection category, except the "attacker" here can be an honest misdiagnosis rather than malice, and the blast radius is identical either way. A self-healing mechanism that (mistakenly) concludes a currently-correct behavior is the cause of a failure, and "fixes" it, can silently degrade every future run in a way that looks, from the outside, exactly like the model got worse — a genuine, self-inflicted instance of Section 6's drift. The concrete guardrails, following directly from patterns established earlier: any self-modification a self-healing mechanism proposes should be gated behind Chapter 14's regression harness before it takes effect broadly — treat a self-proposed fix exactly like a human-proposed harness change, requiring the same eval-suite pass before rollout that Section 8 requires for any harness version at all; self-modifications should themselves be logged and version-attributed (Chapter 15's full observability discipline, applied to changes the *system* made to itself, not just changes a human made); and a self-healing mechanism should have its own scope of authority bounded by least privilege (Chapter 16 Section 6) — a mechanism that can adjust a retry backoff parameter is a fundamentally different risk than one that can rewrite its own system prompt or grant itself new tools, and the two should never share the same authority level by default.

## Key Takeaways for Section 7

Self-healing — an agent detecting and repairing its own recurring failure patterns — is valuable specifically because it scales past what a human noticing every dashboard anomaly can keep up with, but it is a write-access-to-own-future-behavior capability with the same blast-radius profile as Chapter 16's persistent-injection risk, just with an honest misdiagnosis standing in for malice. Gate every self-proposed fix behind the regression harness before broad rollout, log and version-attribute every self-modification the same way a human-authored change would be, and bound the mechanism's own authority with least privilege so a retry-backoff tweak and a system-prompt rewrite are never treated as the same risk tier.

---

# 8: Rollout Practice

## Starting From Plain Language

Section 7 argued that even a self-proposed change needs the same rollout discipline a human-proposed change gets. This section is what that discipline actually consists of — the practices that turn "we changed the harness" from an all-or-nothing bet into a controlled, reversible process.

## Shadow Runs

A **shadow run** executes the new harness version on real production traffic *in parallel* with the currently-live version, comparing their outputs, without the new version's output ever actually being shown to a user or acted on. This is the lowest-risk way to validate a change against real, current traffic (as opposed to only the static golden set, which per Chapter 14 Section 10's contamination discussion and Section 6's drift discussion here, is always somewhat stale relative to what's actually arriving right now) — a shadow run can surface a problem the golden set never anticipated, entirely without user-facing risk, because the new version's output is discarded (or only logged for comparison) rather than delivered.

## Canary Percentage

Once a shadow run looks healthy, a **canary rollout** exposes the new version to a small, deliberately limited percentage of real traffic — 1%, 5%, whatever the organization's risk tolerance dictates — whose outcomes are actually delivered to real users, but whose scale is small enough that a genuine problem affects a bounded, small number of people rather than everyone at once. The percentage should ramp up gradually and only after the smaller percentage has run long enough, and with enough traffic volume, to clear Chapter 14 Section 7's statistical-significance bar on whatever metric the rollout is being judged by — ramping a canary up based on a handful of early data points is the same single-run-comparison mistake Chapter 14 has warned about throughout, just applied to a live rollout instead of an offline eval.

## Harness-Version Pinning

Every request, once it enters a canary or shadow run, needs to be tagged with exactly which harness version handled it — the same discipline Chapter 15 Section 4 established for spans, now load-bearing for rollout decisions specifically: without harness-version pinning on every trace, there is no way to compute "the canary's success rate" as distinct from "the baseline's success rate," because you cannot tell which traffic belongs to which version after the fact. This is what makes the canary's comparison meaningful at all, not an optional nicety.

## A Rollback Playbook for Failing Checkpoints

Every rollout needs a pre-written, tested rollback procedure — not one improvised for the first time during an actual incident — specifying exactly how to revert the canary percentage to zero, which harness version becomes live again, and how quickly that reversion can actually take effect. The word "playbook" matters specifically because a rollback procedure that exists only as institutional knowledge in one person's head is not a rollback procedure that reliably executes at 2 a.m. when that person is unavailable — this is the direct rollout-practice analog of Chapter 16 Section 12's kill switch, built and tested before it's needed rather than designed for the first time during a live incident.

## Key Takeaways for Section 8

Shadow runs validate a new harness version against real, current traffic with zero user-facing risk; canary rollouts then expose it to a small, real slice of traffic, ramped up only once each stage clears a real statistical-significance bar, never based on a handful of early data points. Harness-version pinning on every trace is the prerequisite that makes a canary's comparison meaningful at all, and a pre-written, pre-tested rollback playbook — not an improvised one — is what makes reverting a failing rollout fast and reliable exactly when it's needed most.

---

# 9: Capacity and the GPU You Own

## Starting From Plain Language

This section is where the repo's own hardware — an RTX A6000 with 94GB of RAM — stops being a training-time asset (its role throughout most of this repo's earlier specializations) and becomes a production-serving asset, specifically for the cheap, high-volume, low-judgment steps Section 3's routing discipline identifies.

## Running Open Models Locally: vLLM and Quantization

**vLLM** is the dominant open-source serving framework for exactly this use case — high-throughput batched inference of an open-weight model, with the memory-efficiency techniques (PagedAttention chief among them) needed to serve many concurrent requests against a single GPU's fixed memory budget rather than one request at a time. **Quantization** (running a model at reduced numeric precision — 8-bit or 4-bit rather than the original 16-bit weights) trades a small amount of output quality for a large reduction in the GPU memory a given model size requires, which is frequently the difference between a model fitting on a single 48GB card at all and needing multiple GPUs — for the cheap-eligible, lower-judgment-demand steps Section 3 already scoped this option to, that quality tradeoff is specifically the one this repo's routing discipline is designed to tolerate.

## Measuring the Cost Crossover Point

The core question this section exists to answer precisely, not vaguely, is: at what traffic volume does serving locally on the A6000 you already own become cheaper than paying per-token for the same traffic via API? The answer is emphatically **not** "always" or "never" — it's a crossover point defined by two numbers that don't move in the same direction: the GPU's own operating cost (dominated, once you already own the hardware rather than renting it, by electricity draw — a comparatively small, roughly-fixed monthly figure) versus the API cost of the *same volume* of traffic at whatever per-token rate you'd otherwise pay. Below the crossover volume, the API is cheaper because you're not yet using enough of the GPU's capacity to justify its fixed cost; above it, local serving wins, and it keeps winning by a widening margin as volume grows further, because the GPU's cost doesn't scale up with volume the way API spend does. Section 11's dry-run computes this crossover concretely, with real numbers, rather than leaving it as an abstract "it depends."

## Key Takeaways for Section 9

vLLM plus quantization is what makes serving a genuinely useful model on a single 48GB card practical at all, and the crossover question — at what volume does local serving on hardware you already own beat per-token API pricing — has a computable answer, not a vibes-based one, driven by the GPU's largely-fixed operating cost against API spend that scales linearly with volume. Section 11 works this out with concrete numbers for exactly this repo's hardware.

---

# 10: Operational Runbook

## Starting From Plain Language

Every prior section in this chapter assumes someone, at 2 a.m. or on a Tuesday afternoon, is actually watching the system and knows what to do when something looks wrong. This final section is that "what to do" made explicit, because an on-call rotation handed a dashboard with no accompanying runbook is handed the *ability* to notice a problem without the *knowledge* of how to respond to one.

## What Alerts, What to Check First

Chapter 15 Section 9 already specified which six metrics belong on a dashboard and why. An operational runbook turns each of those into an explicit, ordered first-response procedure: when success rate drops, check whether it correlates with a specific harness-version deploy (a regression, Chapter 14 Section 2) or with no deploy at all (drift, Section 6, and specifically whether a canary task's flat baseline moved); when p95 spikes, check queue depth and retry rates before assuming a model-quality problem (Section 5's throughput concerns, distinct from Section 4's latency-engineering concerns, and easy to conflate under pressure); when cost per solved task jumps, check whether caching's hit rate dropped (Section 2 — did something start invalidating the cache) before assuming volume alone explains it.

## How to Freeze a Misbehaving Agent

This is Chapter 16 Section 12's kill switch, generalized from a security incident specifically to any misbehaving-agent scenario — the on-call runbook needs the exact, tested procedure (not a description of one) for immediately halting a misbehaving agent's ability to take further action, reachable and executable by whoever is on call, not gated behind a person who happens to know how because they built the original mechanism.

## How to Explain an Incident to a Non-Technical Stakeholder

The skill this closing item names is easy to underrate: an incident explanation aimed at an engineer can lean on span trees, p95 numbers, and regression deltas; an incident explanation aimed at a non-technical stakeholder needs to answer three questions in plain language, in this order, without requiring any of the preceding technical vocabulary — what happened (in terms of user-visible impact, not internal mechanism), how many people or how much of the traffic was affected (a number, not a hand-wave), and what's being done about it right now plus when it will be fully resolved. A runbook that only trains an on-call engineer to fix the problem, and not to communicate about it in these terms while they're fixing it, leaves a real gap that surfaces at exactly the worst moment — during the incident itself, under time pressure, when clear communication matters most and is hardest to produce from scratch.

## Key Takeaways for Section 10

An operational runbook turns Chapter 15's dashboard metrics into explicit, ordered first-response procedures — what to check first for each kind of anomaly, and specifically how to tell a regression (correlates with your own deploy) from drift (doesn't) under time pressure. It needs a tested, executable kill-switch procedure reachable by whoever is on call, not gated behind original-author knowledge, and it needs to train the specific, different skill of explaining an incident's user-visible impact, scope, and resolution timeline to a non-technical stakeholder in plain language, since that communication is exactly as real a job requirement during an incident as the technical fix itself.

---

# 11: Dry-Run — Full Cost Model for a 20-Step Agent, and the GPU Break-Even

## Setting Up the 20-Step Agent

Take an agent whose loop grows its context every step (Chapter 4's territory): a **stable prefix** of 2,000 tokens (system instructions plus tool schemas — unchanging across every step) plus a **growing history** that starts at 500 tokens and grows by 300 tokens per step as new turns accumulate, with each step producing 150 output tokens. The total input-token size of step $i$ (for $i = 1, \ldots, 20$) is:

$$\text{total}_i = 2000 + 500 + 300(i-1) = 2500 + 300(i-1)$$

giving $\text{total}_1 = 2500$ tokens and $\text{total}_{20} = 2500 + 300 \times 19 = 8200$ tokens. Summed across all 20 steps, the total input-token volume for one complete run, with no caching at all, is:

$$\sum_{i=1}^{20} \text{total}_i = 20 \times 2500 + 300 \sum_{i=1}^{20}(i-1) = 50000 + 300 \times 190 = 107{,}000 \text{ tokens}$$

Total output volume across the run is $150 \times 20 = 3{,}000$ tokens. (Rates below use this repo's illustrative 2026 Bedrock Claude pricing: Sonnet-class "frontier" at **\$3 / \$15 per million input/output tokens**, and Haiku-class "cheap" at **\$1 / \$5 per million**.)

## Scenario 1: All-Frontier, Uncached (the Baseline)

$$\text{Input cost} = \frac{107{,}000}{1{,}000{,}000} \times \$3 = \$0.321 \qquad \text{Output cost} = \frac{3{,}000}{1{,}000{,}000} \times \$15 = \$0.045$$

$$\text{Total per run} = \$0.366 \qquad \text{Per 1,000 runs} = \boxed{\$366.00}$$

## Scenario 2: All-Frontier, WITH Caching

With a cache breakpoint placed right after each step's content, every step after the first reads the *entire previous* total as a cached hit (0.1× price) and writes only that step's *new* 300-token increment at the 5-minute-TTL write premium (1.25× price); step 1 has nothing to read yet and writes its full 2,500 tokens at the write premium.

Cached-read volume (sum of $\text{total}_{i-1}$ for $i = 2, \ldots, 20$, i.e. $\sum_{j=1}^{19}\text{total}_j$): $19 \times 2500 + 300\sum_{j=1}^{19}(j-1) = 47{,}500 + 300 \times 171 = 98{,}800$ tokens.

New-write volume: step 1's 2,500 tokens plus 19 steps of 300-token increments $= 2{,}500 + 5{,}700 = 8{,}200$ tokens. (Sanity check: $98{,}800 + 8{,}200 = 107{,}000$ — matches Scenario 1's total exactly, as it must, since every token is either a cache read or a fresh write.)

In price-equivalent units (multiples of the base per-token input price):

$$\text{Cached-read units} = 98{,}800 \times 0.1 = 9{,}880 \qquad \text{Write units} = 8{,}200 \times 1.25 = 10{,}250$$

$$\text{Total price-units} = 9{,}880 + 10{,}250 = 20{,}130 \quad \text{vs. } 107{,}000 \text{ uncached} \;\Rightarrow\; 81.2\% \text{ input-cost reduction}$$

$$\text{Input cost} = \frac{20{,}130}{1{,}000{,}000}\times\$3 = \$0.0604 \qquad \text{Output cost (unchanged)} = \$0.045$$

$$\text{Total per run} = \$0.1054 \qquad \text{Per 1,000 runs} = \boxed{\$105.39}$$

Total-run savings versus Scenario 1: $(366.00 - 105.39)/366.00 = 71.2\%$ — meaningfully less than the 81.2% *input*-only savings, because caching does nothing for output-token cost, which is exactly the mechanism behind this repo's earlier chapters' observation that a savings percentage on one cost component never survives unchanged into the blended total. This also lands squarely inside the real, independently-published 2026 range for this pattern — an 8K-stable-prefix, 2K-per-turn setup was measured saving 72% of input spend over 10 turns and 86% over 50 turns; this dry-run's 20-turn, 81%-input-savings result sits exactly between those two published data points, which is a reassuring sanity check that the arithmetic above is modeling a real, not a hypothetical, effect.

## Scenario 3: Routed (30% Cheap / 70% Frontier), Uncached

Using a blended rate — $0.3 \times \$1 + 0.7 \times \$3 = \$2.40$ per million input tokens, $0.3\times\$5 + 0.7\times\$15 = \$12.00$ per million output tokens — applied to the same uncached token volumes as Scenario 1:

$$\text{Input cost} = \frac{107{,}000}{1{,}000{,}000}\times\$2.40 = \$0.2568 \qquad \text{Output cost} = \frac{3{,}000}{1{,}000{,}000}\times\$12.00 = \$0.036$$

$$\text{Total per run} = \$0.2928 \qquad \text{Per 1,000 runs} = \boxed{\$292.80}$$

## Scenario 4: Routed + Cached (Both Levers Together)

Applying the same blended rates to Scenario 2's cached price-units (20,130 for input, unchanged 3,000 output tokens):

$$\text{Input cost} = \frac{20{,}130}{1{,}000{,}000}\times\$2.40 = \$0.0483 \qquad \text{Output cost} = \$0.036$$

$$\text{Total per run} = \$0.0843 \qquad \text{Per 1,000 runs} = \boxed{\$84.31}$$

$$\text{Total savings, baseline} \to \text{routed+cached} = \frac{366.00 - 84.31}{366.00} = 76.97\%$$

```
              COST PER 1,000 RUNS, ACROSS ALL FOUR CONFIGURATIONS
   ┌─────────────────────────────────────────────────────────────┐
   │ all-frontier, uncached (baseline)          $366.00            │
   │ all-frontier, cached                        $105.39  (-71.2%) │
   │ routed (30/70), uncached                    $292.80  (-20.0%) │
   │ routed + cached  (BOTH levers)                $84.31  (-77.0%) │
   └─────────────────────────────────────────────────────────────┘
   Neither lever alone gets close to what the two combined achieve --
   caching and routing are complementary, not substitutes for each other.
```

## The GPU Break-Even: Owning an A6000 vs. Paying Per Token

For the cheap-eligible traffic specifically (the 30% of steps this dry-run routes to Haiku-class pricing), assume an illustrative blended API rate of **\$2 per million combined input+output tokens** (a simplification of Haiku's separate \$1/\$5 rates, weighted toward a typical short-classification-task input:output ratio). Assume the owned A6000's only *marginal* operating cost is electricity — roughly 300W under load at an illustrative \$0.15/kWh, i.e. $0.3\text{kW} \times \$0.15/\text{kWh} = \$0.045$ per hour — but, following the search-confirmed real-world finding that the honest cost of dedicating a GPU to a workload also includes an amortized/opportunity-cost component (comparable to what renting an equivalent A6000 would cost, roughly \$400–700/month as of 2026), use an illustrative **\$500/month fixed cost** $F$ for the GPU's dedicated availability to this workload, independent of how many tokens actually flow through it below its capacity ceiling.

**Local throughput ceiling**: a quantized ~8B-parameter model served via vLLM on a 48GB card sustains, illustratively, **2,000 output tokens/sec**, i.e. $2{,}000 \times 3{,}600 = 7{,}200{,}000$ tokens/hour, or a monthly ceiling (running continuously) of $7.2\text{M} \times 24 \times 30 = 5{,}184\text{M}$ tokens/month.

**Break-even volume** — the traffic volume $X$ (in millions of tokens/month) at which the API-equivalent cost of routing that traffic through the cheap API tier equals the GPU's fixed monthly cost:

$$X \times \$2/\text{million} = \$500 \quad\Rightarrow\quad X = 250 \text{ million tokens/month}$$

$$\text{Break-even utilization} = \frac{250\text{M}}{5{,}184\text{M}} \approx 4.8\% \text{ of the GPU's full-time capacity}$$

**Reading this result**: below 250 million tokens/month of cheap-eligible traffic, paying per-token via the Haiku-class API is cheaper than dedicating the A6000 to it, because the GPU's fixed \$500/month cost isn't yet justified by volume; above 250 million tokens/month, local serving wins, and it wins by a widening margin as volume grows further, since the GPU's cost stays fixed while API spend keeps scaling linearly. The strikingly low 4.8% utilization figure at break-even is the concrete, numeric version of Section 9's claim that self-hosting can pay off well before the GPU is anywhere close to fully loaded — this matches the same order of magnitude as an independently-published 2026 finding of roughly 100 million tokens/month as a break-even point for a larger (70B) model against a pricier API baseline; this dry-run's 250M figure, for a smaller 8B model against a cheaper Haiku-class baseline, is a different (and directionally sensible) point on the same underlying curve, not a contradiction of it.

## Key Takeaways for Section 11

Combining model routing and prompt caching (77% total savings) achieves far more than either lever alone (20% and 71% respectively) on the same 20-step agent — they attack different, complementary parts of the cost equation (which model handles a step vs. how much of that step's context is billed at full price), which is why Section 1 lists them as separate, stackable levers rather than alternatives to choose between. The GPU break-even calculation turns Section 9's "it depends" into a concrete number — 250 million cheap-eligible tokens/month, or roughly 4.8% of one A6000's full-time capacity — below which per-token API pricing wins and above which owning the hardware wins by a widening margin, a threshold now specific enough to actually decide against rather than debate abstractly.

---

# 12: Key Takeaways and Master Decision Table

Cost per *solved task*, never cost per token or per run, is the metric every lever in this chapter should be judged against, because it's the only one that penalizes a "cheaper" change that quietly increases failures or step count — exactly the trap the README calls "optimizing token price while step count explodes." Caching and model routing are complementary, stackable levers, not competing choices — Section 11's dry-run shows them combining to a 77% cost reduction on the same 20-step agent where either lever alone only reaches 20–71%, and caching's savings apply to input tokens only, never surviving unchanged into a blended total that includes output cost. Latency's biggest lever, by a wide margin, is cutting step count itself, since every other technique (streaming, prefetch, parallel calls, batching) optimizes around a step's fixed overhead rather than removing it; p50 and p95 need separate attention because a p95 gap is invisible in the median and disproportionately drives a "feels unreliable" perception. Throughput and concurrency are a distinct problem from latency, solved with retry jitter, backpressure, and deliberate per-tenant fairness rather than assuming a shared queue is inherently fair. Drift — silent model, tool/API, or data-distribution changes with no corresponding entry in your own deploy history — needs continuously-running canary tasks specifically because Chapter 14's regression harness, gated on your own changes, structurally cannot catch a change nobody on your team made. Self-healing is valuable at scale but carries the same blast-radius profile as a persistent security compromise, and needs the identical guardrails: gate every self-proposed fix behind the regression harness, log and version-attribute every self-modification, and bound the mechanism's own authority with least privilege. Rollout practice — shadow runs, then a gradually-ramped canary percentage, both meaningless without harness-version pinning on every trace, backed by a pre-written, pre-tested rollback playbook — turns a harness change from an all-or-nothing bet into a controlled, reversible process. The GPU-ownership crossover has a computable answer, not a vibes-based one: Section 11 put it at roughly 250 million cheap-eligible tokens/month for this repo's A6000, a mere ~4.8% of its full-time capacity. And an operational runbook is only complete once it trains both the technical first-response procedure for each dashboard anomaly *and* the separate, equally real skill of explaining an incident's impact, scope, and resolution timeline to a non-technical stakeholder in plain language.

| Situation | What to reach for | Why |
|---|---|---|
| Deciding whether a cost-cutting change is actually a win | Cost per *solved task*, recomputed after the change | Cheaper tokens with more failures or more steps can be a net loss the token-price number alone hides |
| Designing a prompt that will be sent many times with a growing history | Stable content first with a cache breakpoint, volatile content last, never interleaved | Interleaving stable and volatile content gives the cache nothing byte-identical to match |
| Choosing a cache TTL tier | 5-minute (1.25x write) for steady traffic, 1-hour (2x write, needs 2+ reads to break even) for bursty traffic | Matches TTL cost structure to how often calls actually land within the window |
| About to compact/summarize context mid-run | Budget for a full cache-invalidation cost at that exact step | Compaction changes the prefix; every call downstream restarts cache savings from zero |
| Considering routing a step to a cheaper model | Build a golden-set eval comparing cheap vs. frontier on THAT step type first | "Vibes"-based routing can silently increase failures enough to erase the savings |
| A run feels slow but median latency looks fine | Check p95 and its correlation with retries/tail cases, not p50 | p95 problems are structurally invisible in a p50 number |
| Wanting the single biggest latency win available | Reduce step count itself, before streaming/prefetch/parallel/batching | Every other technique optimizes around fixed per-step overhead; cutting steps removes it entirely |
| Traffic volume is rising and quality is starting to wobble | Check queue depth and backpressure behavior, then per-tenant isolation | A shared, backpressure-free queue lets one burst degrade everyone; per-tenant fairness needs deliberate design |
| Success rate drops with no corresponding deploy on your side | Check a canary task's historical baseline for a departure correlated with an external change | Chapter 14's regression harness only catches YOUR changes; drift is external by definition |
| Building an agent that can adjust its own behavior on failure | Gate every self-proposed fix behind the regression harness; log/version-attribute every self-change; bound its authority with least privilege | Self-modification carries the same blast-radius risk as a persistent compromise, honest-mistake version |
| Shipping any harness change (human- or self-proposed) | Shadow run -> ramped canary (with version pinning on every trace) -> pre-tested rollback playbook | Turns an all-or-nothing bet into a controlled, statistically-gated, reversible rollout |
| Deciding whether to serve a model locally on your own GPU | Compute the break-even volume against the GPU's fixed monthly cost, not gut feel | Section 11: ~250M tokens/month, ~4.8% utilization, is a computable threshold, not a guess |

**Gotchas, collected.** Optimizing token price while step count explodes (Section 1 — the trap cost-per-solved-task is specifically designed to catch); caching that breaks on every run (Section 2 — usually a stable-prefix-design mistake or an under-budgeted compaction event silently invalidating the cache every time); and routing chosen by vibes with no eval (Section 3 — the same single-run-comparison mistake Chapter 14 warned about, applied to a routing decision instead of a harness change, with the same risk of erasing the savings it was supposed to produce).
