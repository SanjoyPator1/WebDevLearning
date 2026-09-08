# Chapter 2: Core Components — Large Language Models, Prompting, and Agents

## Table of Contents

1. [Where This Sits in the Five-Layer Stack](#1-where-this-sits-in-the-five-layer-stack)
2. [LLMs Are Probabilistic Token Machines](#2-llms-are-probabilistic-token-machines)
3. [What a Token Actually Costs You](#3-what-a-token-actually-costs-you)
4. [The Sampling Knobs: Temperature, Top-p, and Penalties](#4-the-sampling-knobs-temperature-top-p-and-penalties)
5. [Prompt Engineering as Persona Design](#5-prompt-engineering-as-persona-design)
6. [Common Prompt Pitfalls](#6-common-prompt-pitfalls)
7. [Building the Agent: The OpenAI Agents SDK, Provider-Agnostically](#7-building-the-agent-the-openai-agents-sdk-provider-agnostically)
8. [Typed Outputs and the Strict-JSON Wall](#8-typed-outputs-and-the-strict-json-wall)
9. [Tracing: What the Dashboard Shows, and What We Substitute](#9-tracing-what-the-dashboard-shows-and-what-we-substitute)
10. [Giving the Agent Tools](#10-giving-the-agent-tools)
11. [Chapter 2 Code Map](#11-chapter-2-code-map)
12. [Key Takeaways](#12-key-takeaways)

---

# 1: Where This Sits in the Five-Layer Stack

Chapter 1 introduced the five functional layers every agent decomposes into — persona, tools, reasoning, memory, evaluation. This chapter is where the first two of those layers stop being diagrams and start being code. Everything through section 6 below is about the **persona layer**: the large language model itself, and the prompt that shapes what it does. Everything from section 7 onward is where persona becomes an actual running `Agent` object, and where the **tools layer** gets its first, minimal foothold — a single `@function_tool` bolted onto an otherwise pure-prompt pipeline. Chapter 3 (which you've already read, in the B04 track) goes deep on tool *design*; this chapter only needs tool *mechanics*, so tool-design questions below point back to that material rather than repeating it.

```text
   PERSONA LAYER                    TOOLS LAYER
  (sections 2-6)                   (sections 7-10)
+------------------+          +--------------------------+
| tokens, sampling |   feeds  | Agent(instructions=...,   |
| knobs, prompt    | -------> |   output_type=...,        |
| engineering      |          |   tools=[...])            |
+------------------+          +--------------------------+
        |                                |
        v                                v
  "what the model                 "what the model
   is told to be"                  is allowed to do"
```

One deliberate choice for our own setup: the reference implementation for this material assumes an `OPENAI_API_KEY` and calls the real OpenAI API throughout. We're not paying for that — instead every exercise wires the same `Agent`/`Runner` primitives to **Gemini by default**, with **Ollama as a free local fallback**, switched with one variable (`PROVIDER = "gemini"` or `"ollama"`) at the top of each file. Section 7 covers exactly how that switch works. The concepts are identical no matter which of the three backends answers the prompt — a persona is a persona regardless of which model reads it — but a couple of things (the tracing dashboard, structured-output enforcement) behave differently without a real OpenAI key, and those spots are called out explicitly as we hit them.

---

# 2: LLMs Are Probabilistic Token Machines

## The One-Sentence Summary

An LLM does exactly one thing, over and over: given the tokens so far, it produces a probability distribution over "what token comes next," and a separate sampling step picks one.

## The Problem This Framing Solves

It's tempting to treat an LLM's fluent output as evidence of something like understanding sitting behind it — a lookup table of facts, a plan being executed. Neither is true, and believing otherwise leads directly to bad prompts and worse agents. If you think the model "knows" your task the way a colleague would, you under-specify the instructions. If you think a temperature-0 setting "locks in" one deterministic answer, you get surprised the fifth time a run drifts. The token-machine framing isn't pedantry — it's the thing that tells you *why* prompting techniques work at all.

## The Intuition

Think of the model as an enormously well-read autocomplete: at every step it looks at everything typed so far and asks "of all the ways I've seen text like this continue, which continuation is most likely?" It never looks ahead, never revises a token once it's chosen, and never consults a fact database. It recomputes its answer to "what comes next" completely from scratch on every single token, using billions of weights that encode statistical regularities absorbed during training — not a stored answer key.

## Training vs. Inference

```text
TRAINING (happens once, offline)              INFERENCE (happens every time you call it)
+------------------------------+               +------------------------------------------+
| billions of documents        |               | your prompt: "Plan research on X"         |
|        |                     |               |        |                                  |
|        v                     |               |        v                                  |
| tokenize -> feed through     |               | tokenize -> feed through the SAME frozen   |
| transformer -> predict next  |               | transformer weights -> probability         |
| token -> compare to actual   |               | distribution over next token               |
| next token -> compute loss   |               |        |                                  |
|        |                     |               |        v                                  |
| backpropagate error into     |               | sample one token (greedy / top-k / top-p)  |
| billions of weights          |               |        |                                  |
|        |                     |               |        v                                  |
| repeat for ~trillions        |               | append token, repeat until EOS token       |
| of tokens                    |               |                                            |
+------------------------------+               +------------------------------------------+
        |
        v
  ALIGNMENT PASS (RLHF, etc.) -- teaches the model to follow
  instructions and be helpful. Does NOT add knowledge or improve
  reasoning; those come from separate techniques (chain-of-thought
  fine-tuning, process reward models).
```

The distinction between training and alignment matters for prompting specifically: when a model ignores your instructions, that's an alignment-layer problem your prompt can work around (be more explicit, use delimiters). When a model gets a fact wrong, that's a base-training-layer problem no amount of clever prompting fixes — you need retrieval, a tool call, or a different model.

## Why This Matters for Prompting

Because generation is genuinely probabilistic, "the same prompt always produces the same output" is false even at temperature 0 (more on why in section 4). Because the model recomputes everything from the tokens it can see, anything not in the prompt (or fetched via a tool) simply isn't available to it — there's no "remembering" a fact you forgot to include. And because inference is fast token-by-token prediction rather than deliberation, an agent that "seems" to reason step by step is really just a model that was prompted or trained to *emit* reasoning-shaped tokens before its answer — which is itself a real and useful technique (chain-of-thought, section 5), just not evidence of an internal reasoning process separate from the tokens on the page.

**Does this make sense? Want me to go deeper on any part** — e.g., how the attention mechanism actually builds the "context" a prediction is conditioned on, or how RLHF's reward model is trained?

---

# 3: What a Token Actually Costs You

## The Problem

"How long is this prompt" and "how many tokens is this prompt" are different questions with different answers, and every cost and context-window decision from here on runs on the second one, not the first.

## The Intuition

A tokenizer doesn't split on whitespace — it splits on whatever sub-word chunks appeared often enough during training to earn their own vocabulary slot. Common words get one token; rare words get chopped into pieces; structural characters (`{`, `"`, `:`) each typically cost their own token too. This is why the same *information* can cost wildly different token counts depending on how it's formatted.

## The Dry Run: Same Data, Two Formats

```text
Plain text (≈6 tokens):
  "Alice, 32, Engineer"
  ["Alice", ",", " ", "32", ",", " Engineer"]   (tokenizer-dependent, illustrative)

Equivalent JSON (≈13 tokens):
  {"name": "Alice", "age": 32, "role": "Engineer"}
  ["{", "\"", "name", "\"", ":", " \"", "Alice", "\"", ",", " \"", "age", "\"", ":"] ... (continues)
```

Same underlying data, more than double the token count — every brace, quote, and field name is a token the model pays for on input and you pay for in the bill. This doesn't mean "never use JSON" (structured data is easier for a model to produce reliably, which is the entire subject of section 8) — it means treat JSON-in-a-prompt as a cost you're consciously accepting, not a free convenience.

## Why This Compounds in Agents Specifically

Two facts multiply together in an agentic system: output tokens are priced two-to-five times higher than input tokens (provider-dependent), and every tool you register (section 10) adds its JSON schema to *every single call*, whether or not that tool gets used. A five-tool agent that runs a twenty-step loop is paying the input-token cost of all five tool schemas twenty times over — a fixed tax you accept the moment you register a tool, independent of how often it's actually invoked. Measuring this isn't optional at scale: `tiktoken` (OpenAI's tokenizer library) lets you count tokens for a given prompt before you send it, and the OpenAI Agents SDK reports actual input/output token counts on every `Runner.run_sync` result — check `result.raw_responses` for the usage figures rather than guessing from character counts.

---

# 4: The Sampling Knobs: Temperature, Top-p, and Penalties

## The Intuition

Section 2 said the model produces a probability distribution and a separate step samples from it. This section is about that separate step — the knobs that decide *how* the sample gets picked, all of which change the die you're rolling without changing whether you're rolling one at all.

## Temperature: Sharpening or Flattening the Distribution

**The problem it solves.** A raw probability distribution over 100,000+ vocabulary tokens might assign 40% to the single best token and spread the rest thin. Sampled directly, that's already fairly deterministic. Temperature lets you push further in either direction — toward "always pick the top choice" (good for code, structured output) or toward "let low-probability tokens have a real shot" (good for brainstorming).

**The math.** The model outputs raw scores called logits, $z_1, \dots, z_n$, one per vocabulary token. Softmax turns logits into probabilities:

$$P(\text{token}_i) = \frac{e^{z_i}}{\sum_{j} e^{z_j}}$$

Temperature $T$ divides every logit before the softmax is applied:

$$P(\text{token}_i \mid T) = \frac{e^{z_i / T}}{\sum_{j} e^{z_j / T}}$$

Every symbol: $z_i$ is the raw, unnormalized score the model computed for candidate token $i$; $T$ is the temperature (default $\approx 1$, meaning "leave the logits alone"); the denominator is just the sum of all exponentiated, temperature-scaled logits, so the numerator and denominator together guarantee the outputs sum to 1 and form a valid probability distribution. As $T \to 0$, dividing by a tiny number makes the largest logit's exponential dwarf all others, so the distribution collapses toward "pick the single highest-scoring token with near-certainty" (greedy decoding). As $T$ grows past 1, dividing shrinks the *differences* between logits, flattening the distribution toward uniform — every token becomes more equally likely, including ones the model originally scored low.

**The dry run.** Say the model's raw logits over just 3 candidate next-tokens are:

```
Candidates: "the" = 2.0, "a" = 1.0, "an" = 0.1
```

At $T = 1$ (no scaling), softmax directly:
```
e^2.0 = 7.389,  e^1.0 = 2.718,  e^0.1 = 1.105
sum = 11.212
P("the") = 7.389 / 11.212 = 0.659
P("a")   = 2.718 / 11.212 = 0.242
P("an")  = 1.105 / 11.212 = 0.099
```

At $T = 0.1$ (sharpen — this is roughly what `temperature=0` approximates in practice, since dividing by exactly 0 is undefined and providers clamp it to a very small value):
```
scaled logits: 2.0/0.1=20, 1.0/0.1=10, 0.1/0.1=1
e^20 = 4.85e8,  e^10 = 2.2e4,  e^1 = 2.72
sum ≈ 4.85e8 (the other two terms are negligible in comparison)
P("the") ≈ 0.99998
P("a")   ≈ 0.00002 (approximately)
P("an")  ≈ negligible
```

"the" is now picked almost every time — this is why low temperature makes output consistent, not identical: there's still a non-zero (if tiny) chance of the second-place token, which is exactly why five runs at `temperature=0.0` on a five-task plan can differ on task five and agree on the first four, exactly as `exercise2_model_tuning.py` is designed to surface.

At $T = 3$ (flatten):
```
scaled logits: 2.0/3=0.667, 1.0/3=0.333, 0.1/3=0.033
e^0.667=1.948, e^0.333=1.395, e^0.033=1.034
sum = 4.377
P("the") = 0.445,  P("a") = 0.319,  P("an") = 0.236
```
All three are now much closer to equally likely — this is the "creative but less factually reliable" mode.

## Top-p (Nucleus Sampling): Filtering the Tail

**The intuition.** Temperature reshapes the whole distribution but never *removes* options — even at high temperature, a wildly implausible token still has some nonzero chance. Top-p instead throws away the improbable tail entirely before sampling: it sorts tokens by probability, keeps adding them from most to least likely until the cumulative probability crosses $p$, discards everything after that cutoff, and renormalizes what's left.

**The math.** Given tokens sorted by probability descending, top-p selects the smallest set $V_p$ such that:

$$\sum_{i \in V_p} P(\text{token}_i) \geq p$$

then resamples only within $V_p$, renormalizing so those probabilities sum to 1 again.

**The dry run.** Using our earlier $T=1$ distribution — "the"=0.659, "a"=0.242, "an"=0.099 — with $p = 0.9$:

```
Sorted: "the" (0.659) -> cumulative 0.659  (< 0.9, keep going)
        "a"   (0.242) -> cumulative 0.901  (>= 0.9, STOP — "a" is included)
        "an"  (0.099) -> excluded, cumulative already met the threshold

Nucleus = {"the", "a"}
Renormalize: total = 0.659 + 0.242 = 0.901
P("the") = 0.659 / 0.901 = 0.731
P("a")   = 0.242 / 0.901 = 0.269
"an" now has ZERO chance of being sampled, regardless of temperature.
```

This is the mechanical reason OpenAI's own guidance says adjust temperature *or* top-p, not both: stacking them means you're reshaping a distribution and then throwing part of it away, and the combined effect on "how random is this actually" becomes hard to reason about.

## Everything Else, In One Table

| Parameter | Typical range | What it actually does | Raise it when... |
|---|---|---|---|
| `temperature` | 0–2 (default ≈1) | Scales logits before softmax — see math above | brainstorming, creative writing (lower for code/consistency) |
| `top_p` | 0–1 (default ≈1) | Truncates the sampling pool to the smallest set covering cumulative probability $p$ | you want variety without letting implausible tokens in (lower ≈0.9 for tight prose) |
| `max_tokens` | model-dependent | Hard ceiling on response length — not a sampling knob, a guardrail | set just above the expected length; caps cost and rambling |
| `presence_penalty` | −2…+2 | Flat penalty applied once a token has appeared at all — pushes toward new topics | 0.6–1.0 to stop the model re-treading the same ground |
| `frequency_penalty` | −2…+2 | Penalty that scales with *how many times* a token has already appeared — discourages repeated phrases | 0.2–0.8 to reduce looping in long answers |
| `seed` | any integer | Same seed + prompt + params → same output; useful for debugging/eval, not a substitute for typed output | when you need a reproducible run to compare against |

In practice you'll touch `temperature` and `max_tokens` most: temperature to match the agent's role (0 for a planner or coder, higher for a brainstorming agent), max_tokens as a cost and rambling guardrail. Everything else is usually left at defaults, with a note on **reasoning-effort**: newer models (OpenAI, Anthropic, and others) expose a `reasoning_effort`/`thinking` parameter controlling how much internal deliberation happens before the answer. For most agent steps this should be `none`/`minimal` — an agent runs many small, prompt-and-tool-constrained steps where extra deliberation adds latency and cost without changing the answer. Reserve higher effort for genuinely hard steps (planning, ambiguous tool selection, debugging a stuck loop). This is exactly the qwen3 thinking-mode gotcha called out in the exercise scaffolds: unconstrained thinking on a routine planner step can burn an entire `max_tokens` budget on reasoning tokens and leave nothing for the actual answer.

## Provider Comparison: Setting These Knobs

The knobs themselves are universal — every major chat-completions-style API exposes `temperature`, `max_tokens`, and friends by roughly the same names. What differs is how you plug them into `Agent(...)`.

**Gemini (our default) — via `OpenAIChatCompletionsModel`, same adapter as Ollama:**
```python
from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from openai import AsyncOpenAI

set_tracing_disabled(True)
gemini_client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model=os.environ["GEMINI_MODEL"], openai_client=gemini_client),
    model_settings=ModelSettings(temperature=0.0, max_tokens=150),
)
```

**Ollama (our free local fallback) — identical adapter, different `base_url`:**
```python
ollama_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model="qwen3:8b", openai_client=ollama_client),
    model_settings=ModelSettings(temperature=0.0, max_tokens=150),
)
```

**Real OpenAI (not what we're using — no paid key for this track) — model string is enough:**
```python
from agents import Agent, ModelSettings

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model="gpt-4.1",
    model_settings=ModelSettings(temperature=0.0, max_tokens=150),
)
```

**Anthropic via Bedrock — via the SDK's LiteLLM extension** (the officially documented way for the Agents SDK to reach a non-OpenAI-compatible provider; needs `pip install "openai-agents[litellm]"`):
```python
from agents import Agent, ModelSettings
from agents.extensions.models.litellm_model import LitellmModel

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=LitellmModel(model="bedrock/us.anthropic.claude-sonnet-4-6"),
    model_settings=ModelSettings(temperature=0.0, max_tokens=150),
)
```

The `Agent`/`Runner`/`ModelSettings` code around it never changes — only the `model=` value does. That's the whole point of the SDK's model abstraction, and it's why our exercises can flip between Gemini and Ollama with one `PROVIDER` variable (section 7) without rewriting any of the actual agent logic, just the few lines that construct the client.

---

# 5: Prompt Engineering as Persona Design

## The Reframe

Chapter 1 named "persona" as the first functional layer — the answer to "who is this agent." Prompt engineering is simply the practical craft of writing that answer well. It has a reputation as hype, but the actual claim is narrow and testable: a handful of concrete techniques measurably reduce variance and rule-violations in an LLM's output, across essentially every model family, because they lean on patterns present in how all of these models were trained and aligned.

## The Techniques, Applied to Our Research Planner

| Technique | What it means | Applied to our Research Planner agent |
|---|---|---|
| Clear role/persona | State a role that sets vocabulary, tone, depth | "You are a research planning assistant" — swapping this string alone repurposes the same code into a critic, a summarizer, a planner |
| Front-load instructions + delimiters | Directive first, user data fenced with unique markers | Put the TASK INSTRUCTIONS block before the topic; wrap the topic in a Markdown fence (exercise 4) |
| Be specific and detailed | Concrete length, audience, objective | "5 concise tasks, 5 words or less" — not "a short plan" |
| Define exact output format | Give a schema | Handled by `output_type=ResearchPlanModel` (section 8) instead of prose formatting instructions — this is one technique the SDK makes largely unnecessary |
| Few-shot examples | Show labeled input→output pairs | Not used in the minimal planner, but this is how you'd show "good" vs "bad" task phrasing |
| Chain-of-thought | Ask the model to reason step by step, silently, before answering | "Think step-by-step silently (do NOT reveal reasoning) before answering" |
| Positive instructions | Say what to do, not what to avoid | "Use clear, non-jargon language" rather than "don't use jargon" |
| Eliminate ambiguity | Replace fuzzy words with numeric bounds | "Exactly 5 articles, each ≤150 words" rather than "a few short summaries" |

## A Structural Note: Prompt Caching

Most providers cache the *static* portion of a prompt — system instructions, persona, tool schemas — and charge a fraction of the input rate on a cache hit. Putting stable content (persona, instructions) at the top and dynamic content (the actual user query) at the bottom maximizes how often that cache gets hit, which on a high-traffic agent can cut input costs by an order of magnitude. This is a free win that costs nothing but prompt ordering discipline.

## Thinking Like the Model Reading the Prompt

The most reliable mental trick for writing agent instructions: read the prompt as if you were a new hire with zero context, encountering it cold, and unable to ask a follow-up question. If a step in your instructions assumes prior knowledge the model can't have, or leaves a decision point implicit ("search appropriately"), that's exactly where the model will guess — and guessing, unlike a confused new hire, produces confident-looking output with no visible hesitation. This is the same principle Chapter 3 applies to tool schemas specifically (a schema is a UI whose user is a model); here it's applied to the persona prompt as a whole, including multi-step workflows with decision points baked directly into prose instructions.

---

# 6: Common Prompt Pitfalls

| Pitfall | What it looks like | The fix |
|---|---|---|
| Too complicated | One long, multi-topic prompt overwhelms context and creates conflicting instructions | Split into smaller, role-specific steps that hand off to each other |
| Contradictory | "Be concise" and "explain in depth" in the same prompt | Read it end-to-end as the model would; remove the conflict explicitly |
| Too simple | Micro-prompts trigger excessive round-trips | Consolidate related micro-tasks, or let the agent branch internally via tool use |
| Inconsistent delimiters | Mixing `"""`, `<<<>>>`, and Markdown fences in one prompt | Pick one delimiter style per prompt and stick to it |
| Overly explicit | Dozens of rules crammed into one prompt | Keep only the critical constraints; split the rest into chained steps or a validating guardrail |
| Variable output despite `temperature=0` | Output still drifts run to run | Temperature 0 *reduces* variance, it doesn't eliminate it (section 4's dry run shows why) — tighten the instructions and delimiters, don't just chase the temperature knob |

That last row is exactly what exercise 2 is designed to make you observe firsthand: run the same `temperature=0.0` planner twice and the tasks won't be byte-identical, because there's always a nonzero probability mass left on the second-best token.

---

# 7: Building the Agent: The OpenAI Agents SDK, Provider-Agnostically

## Why This SDK, Mechanically

`Agent` and `Runner` are the two objects that matter. An `Agent` bundles a name, an instructions string (the persona from sections 5–6), optionally a model and `model_settings` (section 4), optionally an `output_type` (section 8), and optionally a list of `tools` (section 10). `Runner.run_sync(agent, input=...)` actually executes it — sends the instructions plus input to the model, handles any tool-calling round-trips automatically, and returns a `RunResult` whose `.final_output` is the answer (either raw text, or an instance of your `output_type` model).

This is the concrete reason we're using the OpenAI Agents SDK for this material specifically, rather than writing the loop by hand the way an earlier track in this repo did: `Agent`/`Runner` *are* that loop, packaged — tool-call round-trips, message threading, and typed-output parsing all happen inside `Runner.run_sync` instead of in code we write ourselves. The trade we're making by adopting a framework here is exactly the one worth understanding rather than skipping past: less code to write, at the cost of not seeing the mechanics directly — mechanics that are worth having already seen once, by hand, before trusting a framework to do them for you.

## What `AsyncOpenAI` Actually Is

**The one-sentence summary.** `AsyncOpenAI` is a plain HTTP client shaped to speak one specific wire protocol — the OpenAI chat-completions REST API — and nothing about its name means the request has to reach an OpenAI server; it means the request is *formatted the way OpenAI's API expects*, which any provider willing to accept that same shape can serve.

**The problem it solves.** Every LLM provider exposes some HTTP API, but the JSON shapes differ — different field names, different auth headers, different endpoint paths. Rather than hand-rolling `requests.post(...)` calls yourself (which is closer to what raw HTTP would look like), the `openai` Python package gives you a typed client object: call `client.chat.completions.create(model=..., messages=[...])` and it builds the correct request, sends it, and parses the response into a typed Python object for you. `AsyncOpenAI` and its sibling `OpenAI` (the synchronous version used in the raw-loop track) do exactly the same job — build and send that one specific request shape — the only difference is *how* they wait for the network.

**Sync vs. async, concretely.** `OpenAI().chat.completions.create(...)` blocks: your program stops on that line until the HTTP response comes back. `AsyncOpenAI().chat.completions.create(...)` returns a coroutine you `await`, which lets Python's event loop go do other work while the network round-trip is in flight. We need the async version specifically because the Agents SDK's `Runner` is itself built on `asyncio` internally — `Runner.run_sync` is a thin wrapper that starts an event loop and drives an async run through it — so every model call it makes has to be an awaitable, not a blocking call. This is also the exact reason `Agent(model=...)` won't accept a plain `openai.OpenAI` client if you tried to pass one in directly: the `Runner` needs something it can `await`.

**What it's constructed with.** Two arguments matter here: `base_url` (which server to send the HTTP request to) and `api_key` (sent as an `Authorization` header on every request). Change only those two values and the exact same `client.chat.completions.create(...)` call gets routed to a completely different backend — that's the entire trick behind swapping Gemini and Ollama.

**What actually goes over the wire, for each branch:**

```text
PROVIDER = "gemini"                                PROVIDER = "ollama"
POST https://generativelanguage.googleapis.com/    POST http://localhost:11434/v1
     v1beta/openai/chat/completions                     /chat/completions
Headers: Authorization: Bearer <real GEMINI_API_KEY>   Headers: Authorization: Bearer ollama
Body:   {"model": "gemini-3.6-flash",               Body:   {"model": "qwen3:8b",
         "messages": [...]}                                  "messages": [...]}
     |                                                    |
     v                                                    v
Google's server checks the key, translates this      Ollama's local server, running on your
request into Gemini's native call shape, runs         own machine, matches this shape directly
the model, translates the response back into           against its own OpenAI-compatibility
OpenAI's response shape, sends it back.                 layer and runs qwen3:8b.
```

Same client class, same method call, same JSON shape leaving your machine — the only things that differ are the URL, the header value, and which server is listening.

## Our Setup: One Switch, Two Free Providers

None of the code in this folder uses a real, paid OpenAI key. Every file wires the same `Agent`/`Runner` objects to one of two backends behind a single `PROVIDER` variable:

```text
                    PROVIDER = "gemini"  (default)                  PROVIDER = "ollama"  (fallback)
                    +----------------------------------+            +----------------------------------+
                    | AsyncOpenAI(                     |            | AsyncOpenAI(                     |
                    |   base_url=".../v1beta/openai/", |            |   base_url="localhost:11434/v1", |
                    |   api_key=GEMINI_API_KEY)        |            |   api_key="ollama")              |
                    +----------------------------------+            +----------------------------------+
                                    \                                    /
                                     \                                  /
                                      v                                v
                          OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)
                                                    |
                                                    v
                                    Agent(name=..., instructions=..., model=...)
```

**Gemini is the default** because Google ships a genuine, first-party OpenAI-compatible endpoint at `https://generativelanguage.googleapis.com/v1beta/openai/` — no adapter library needed, and a real API key is already available for it. **Ollama stays wired in as a fallback** for offline work or when avoiding any network call entirely matters more than answer quality. Both branches produce the exact same kind of object — an `AsyncOpenAI` client pointed at a different `base_url` — which is then handed to `OpenAIChatCompletionsModel`, the SDK's own adapter for "any backend that speaks the OpenAI chat-completions shape." Nothing about `Agent`, `instructions`, `output_type`, or `tools` changes between the two branches; only the six-ish lines that build `client` and `MODEL_NAME` do.

## The Minimal Agent

```python
import os
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
set_tracing_disabled(True)  # no real OpenAI key -> no trace export attempts

PROVIDER = "gemini"  # "gemini" or "ollama"

if PROVIDER == "gemini":
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    MODEL_NAME = os.environ["GEMINI_MODEL"]
elif PROVIDER == "ollama":
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL_NAME = "qwen3:8b"

instructions = """
You are a research planning assistant.

**TASK INSTRUCTIONS**
- You will be given a research topic.
- Your task is to provide a plan on how to research this topic.
- Output 5 concise tasks (5 words or less) to your plan.
"""

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)

result = Runner.run_sync(agent, input="learn about AI agents")
print(result.final_output)
```

That's the entire persona layer turned into a runnable agent — no tools yet, no typed output yet, just a prompt wrapped in an object the SDK knows how to call and re-call. This is exactly the shape of `01_first_agent.py` in our own `code/ch02/` folder; the only addition versus a plain, key-based setup is the provider-switch block at the top, since we don't have a real `OPENAI_API_KEY` set and `load_dotenv()` alone won't get us anywhere without one.

## Every Piece of the Minimal Agent, One at a Time

| Line(s) | What it is | Why it's there |
|---|---|---|
| `import os` | Standard library | Lets us read `os.environ["GEMINI_API_KEY"]` — the OS-level environment variables for this process |
| `from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled` | Four names from the `openai-agents` package | `Agent`/`Runner` are the framework's core objects (above); `OpenAIChatCompletionsModel` is the adapter connecting a raw client to the framework; `set_tracing_disabled` is a module-level setting, not tied to any one agent |
| `from dotenv import load_dotenv` | A utility from the separate `python-dotenv` package | Knows how to read a `.env` file's `KEY=value` lines and inject them into `os.environ`, so you don't have to `export` them in your shell manually |
| `from openai import AsyncOpenAI` | The transport client class covered above | This is what actually sends HTTP requests — to Gemini or Ollama, per the switch |
| `load_dotenv()` | A function call, run once at import time | Performs the actual `.env` → `os.environ` injection; without this line, `os.environ["GEMINI_API_KEY"]` would raise a `KeyError` even with a correctly filled-in `.env` file |
| `set_tracing_disabled(True)` | A global SDK setting | Turns off the SDK's default behavior of trying to upload trace spans to OpenAI's dashboard — see section 9 for why that upload would fail without a real key anyway |
| `PROVIDER = "gemini"` and the `if`/`elif` block | Plain Python, nothing SDK-specific | Decides which `client` object and which `MODEL_NAME` string get built; this is the entire "switch" |
| `client = AsyncOpenAI(base_url=..., api_key=...)` | One instance of the transport class, per branch | The object that will actually make the network call once the agent runs |
| `MODEL_NAME = ...` | Just a string | Names which model on that backend to request — `"qwen3:8b"` is a tag Ollama recognizes locally; the Gemini value comes from your `.env`'s `GEMINI_MODEL` |
| `instructions = """..."""` | A plain Python string — the persona | Everything from sections 5–6: role, task instructions, output constraints. Notice this line doesn't reference `client`, `PROVIDER`, or anything provider-specific at all — the persona is completely decoupled from which backend answers it |
| `agent = Agent(name=..., instructions=..., model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client))` | Construction of the actual `Agent` object | This is where the transport (`client`) and the persona (`instructions`) finally meet. `OpenAIChatCompletionsModel` wraps `client` into the shape the SDK's internals expect — when `Runner` needs a completion, it calls into this wrapper, which calls `client.chat.completions.create(...)` underneath |
| `result = Runner.run_sync(agent, input="learn about AI agents")` | The actual execution | `Runner` reads `agent.instructions`, combines it with `input`, calls the model through `agent.model`, and (once tools or typed output are involved, sections 8 and 10) manages any follow-up round-trips automatically. The return value is a `RunResult` object, not just a string |
| `print(result.final_output)` | Accessing one field of that `RunResult` | `.final_output` is the actual answer — plain text here, or a typed object once `output_type` is set (section 8) |

The one-sentence version of the whole chain: **persona (`instructions`) is pure text, transport (`client`) is pure HTTP plumbing, and `OpenAIChatCompletionsModel` is the only piece whose entire job is gluing those two together into something `Agent`/`Runner` know how to drive.**

## The `api_key` Field Is Still Required Either Way

The `AsyncOpenAI` client constructor requires a non-empty `api_key` string even when `base_url` points somewhere with its own auth. In the Ollama branch, the value is never actually checked — Ollama's OpenAI-compatible endpoint ignores it entirely, but omitting it still makes the client raise before a request is ever sent, so `"ollama"` (the conventional placeholder Ollama's own docs use) fills that requirement. In the Gemini branch, the value *is* checked — it's your real `GEMINI_API_KEY` from `.env`, doing actual authentication, not a placeholder.

---

# 8: Typed Outputs and the Strict-JSON Wall

## Why Typed Output Exists

Section 2 established that generation is probabilistic — even a well-written prompt asking for "5 tasks" can occasionally come back as prose, a numbered list with different formatting, or four tasks instead of five. In a single standalone agent that's mildly annoying; in a multi-agent pipeline where one agent's output feeds directly into the next agent's input, that variability is a broken pipe. Typed output solves this not by asking nicely, but by constraining what tokens the model is *allowed* to sample at each step, so the output is structurally guaranteed to match a schema — not just probably going to match it.

## Building It Up: Basic → Broken → Fixed

**Basic (`output_type=ResearchPlanModel` with `tasks: List[str]`)** — works cleanly, the model returns a plain list of strings.

**Broken (`tasks: dict[int, str]`)** — this looks like a reasonable "numbered tasks" representation, but raises:

```
UserError: Strict JSON schema is enabled, but the output type is not valid.
Either make the output type strict, or pass output_schema_strict=False to your Agent()
```

This error fires **before any network call happens** — it's the SDK's own schema builder rejecting the type while converting your Pydantic model into a strict JSON Schema, because a `dict` with arbitrary integer keys can't be expressed as a fixed, closed set of properties the way strict mode requires. This means the error reproduces identically whether you're pointed at Ollama, OpenAI, or Bedrock — swapping providers will never fix it, because no provider is involved yet.

**Fixed** — replace the dict with a list of a `TypedDict`, and forbid extra fields:

```python
from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

class Task(TypedDict):
    id: int
    description: str

class ResearchPlanModel(BaseModel):
    tasks: list[Task]
    model_config = ConfigDict(extra='forbid')
```

`list[Task]` is a closed, enumerable shape — exactly the same number and names of fields on every element — which strict JSON Schema can express as a fixed `properties` object with `additionalProperties: false`, `required` listing every field. This is the same "strict mode" contract covered in depth on the tool-schema side back in the B04 tools chapter: no additional properties, everything required, no open-ended keys.

## What Changes Without a Real OpenAI Key

Structured-output *enforcement* — the part that makes malformed output structurally impossible rather than merely unlikely — is implemented server-side by the provider. Ollama's OpenAI-compatible endpoint accepts the same request shape but doesn't apply the same generation-time constraint the way OpenAI's own API does. In practice this means: the `UserError` above still fires identically (client-side, pre-network), but *after* the fix, Ollama is more likely than real OpenAI to occasionally return a response that fails Pydantic validation on our end, because nothing forced its token sampling to stay inside the schema — it's following the schema because the prompt and type hints ask it to, not because it's structurally unable to do otherwise. If exercise 3's final run throws a Pydantic validation error rather than a clean parse, that's the model wandering off-schema, not a bug in the wiring.

## Provider Comparison

| | OpenAI (real) | Gemini (our default) | Ollama (our fallback) | Anthropic / Bedrock |
|---|---|---|---|---|
| Mechanism | `response_format` / SDK-native `output_type`, generation-time constrained | Same OpenAI-compatible request shape, constraint strength not guaranteed | Same request shape accepted, generation-time constraint not guaranteed | `output_config` with `type: "json_schema"` |
| Guarantee | Structurally impossible to violate schema | Best-effort; validate on receipt | Best-effort; validate on receipt | Structurally impossible to violate schema |
| Strict-mode rules | `additionalProperties: false`, all fields `required`, optional fields via `anyOf [..., null]` | Same rules recommended, not enforced | Same rules recommended, not enforced | Same three rules apply |

---

# 9: Tracing: What the Dashboard Shows, and What We Substitute

## What Tracing Is For

As agents grow past "one prompt, one answer" into multi-step tool-using workflows, understanding *what actually happened* during a run stops being obvious from `result.final_output` alone. Tracing records every LLM call and tool invocation in a run as a named, inspectable timeline — which tool got called, with what arguments, what it returned, and where the final answer came from.

```text
with trace("Deep Research Workflow"):
    result = Runner.run_sync(agent, input=input)

                    +-----------------------------------+
                    |  TRACE: "Deep Research Workflow"   |
                    +-----------------------------------+
                    |  1. LLM call  -> instructions+input |
                    |  2. tool_call -> get_research_...  |
                    |  3. tool_result -> ["Wikipedia",..] |
                    |  4. LLM call  -> final answer       |
                    +-----------------------------------+
```

With a real OpenAI key, this uploads to `platform.openai.com`'s Traces dashboard automatically — no extra setup beyond wrapping the run in `with trace("name"):`.

## Why This Doesn't Work Here, and What We Do Instead

The Traces dashboard is an OpenAI-hosted service authenticated with a real `OPENAI_API_KEY`, entirely separate from which model actually answered the prompt. Since we're not paying for OpenAI access for this chapter, our scaffolds call `set_tracing_disabled(True)`, which makes every `with trace(...):` block a safe no-op instead of erroring on a missing key.

The local substitute is `result.new_items` — a `RunResult` attribute listing every step of the run, in chronological order, as typed items (`ToolCallItem`, `ToolCallOutputItem`, `MessageOutputItem`, and others):

```python
result = Runner.run_sync(agent, input=input)
for item in result.new_items:
    print(type(item).__name__)

# Expected order for a tool-using agent:
# ToolCallItem
# ToolCallOutputItem
# MessageOutputItem
```

Seeing that exact order is the same claim the dashboard screenshot would prove — a tool call happened, produced a result, and *then* the model produced its final message — just read programmatically instead of visually. For production multi-provider agents, the OpenAI dashboard is a starting point, not the destination anyway: framework-agnostic tools like LangSmith, Langfuse, Arize Phoenix, and Weights & Biases Weave trace OpenAI, Anthropic, and local models through one unified view, which is the direction to look once tracing needs to span more than one provider.

---

# 10: Giving the Agent Tools

## From Prompt Chaining to Agency

A pure persona-plus-typed-output agent, however well-prompted, is still just one prompt step — wiring several such steps together is called **prompt chaining**, and it's a perfectly legitimate pattern, but it isn't agency. Agency specifically means the ability to decide, at runtime, to take an action — and the cheapest way to grant that is `@function_tool`.

```python
from agents import function_tool

@function_tool
def get_research_sources() -> list[str]:
    """Provides a list of research sources."""
    return ["Wikipedia", "Google", "YouTube"]

agent = Agent(
    name="Research Planner",
    instructions=instructions,   # now tells the model to call the tool first
    output_type=ResearchPlanModel,
    tools=[get_research_sources],
)
```

The decorator does the work Chapter 3 covers in depth on the schema side — it inspects the function's signature and docstring and auto-generates the JSON tool description the model sees. Once registered, that description is included on **every** LLM call for this agent, used or not, which is precisely the token-overhead point from section 3: five tools means five schemas paid for on every single turn.

## Tool Chaining

`08_agent_with_tools_tracing.py` extends this to two tools where the second depends on the first's output — `get_resource_url(source)` needs a source name that only `get_research_sources()` can supply. This pattern, where the agent uses one tool call's output to drive another tool's input, is called **tool chaining**, and it's usually left for the model to figure out from context rather than hard-coded in the prompt as an explicit sequence. Modern frontier models can also fire independent tool calls *in parallel* within one turn (a search tool and a calendar tool that don't depend on each other, say) — chaining and parallelism are both decisions the model makes based on whether one tool's output is a prerequisite for another's input.

## The Four Costs of Every Tool You Add

Tools are never free, and the trade-offs are worth internalizing before reaching for a sixth or seventh tool on one agent:

Tools are overhead — every registered tool's JSON schema rides along on every LLM call regardless of use, a fixed input-token tax. Tools add complexity — each one adds instructions describing when and how to use it, and more instructions in a longer prompt raises the odds of ambiguity or conflicting guidance. Tools can fail — each is a new point of failure and a new surface the agent needs a recovery path for (retries with backoff for transient failures, structured errors the agent can read rather than a raw crash, timeouts so a hanging tool doesn't stall the whole run). And tools are decisions — registering a tool means trusting the model's judgment about *when* to use it, which is fine for a read-only search tool and considerably less fine for a delete-files tool; assume that if an agent *can* take a destructive action, it eventually *will*, and design the tool set accordingly.

This is intentionally the shallow end of tool design — mechanics, not schema craft. The deep dive on naming, granularity, return-value shape, error-message design, and destructive-action flags lives in the Chapter 3 notes (`ch03-tools-as-interfaces.md`) from the B04 track, and everything there applies unchanged to tools registered here via `@function_tool`.

---

# 11: Chapter 2 Code Map

All of the following live in `code/ch02/` (`template/` = pristine scaffold, `solutions/` = your handwritten fill-in). Every file already has the provider-switch wiring done at the top (`PROVIDER = "gemini"` by default, `"ollama"` as the fallback branch); what's left is the persona, schema, and tool logic each one is named for.

| File | What it builds | Section above |
|---|---|---|
| `01_first_agent.py` | Minimal persona agent, no settings/types/tools | §7 |
| `02_setting_agent_model_parameters.py` | Adds explicit model + `ModelSettings` | §4, §7 |
| `03_output_types_basic.py` | `output_type=ResearchPlanModel` with `tasks: List[str]` | §8 |
| `04_output_types.py` | Deliberately broken: `tasks: dict[int, str]` → `UserError` | §8 |
| `05_output_types_fixed.py` | Fixed with `TypedDict` + `extra='forbid'` | §8 |
| `06_agent_with_tracing.py` | Same agent wrapped in `with trace(...)` | §9 |
| `07_agent_with_tool.py` | Adds `get_research_sources()` as a tool | §10 |
| `07x_agent_with_tool_extended.py` | Same, but the tool returns structured `ResearchSource` objects instead of plain strings | §10 |
| `08_agent_with_tools_tracing.py` | Two chained tools + tracing together | §9, §10 |
| `exercise1_minimal_agent.py` … `exercise5_tool_and_tracing.py` | The graded exercise progression, same shape as above, five words tighter and one prompt-engineering pass added in exercise 4 | all of the above |

---

# 12: Key Takeaways

LLMs are probabilistic next-token predictors, not lookup tables — everything about prompting and sampling exists to manage that probabilistic core, not to work around some deeper "understanding" the model doesn't have. Token count, not character count, drives cost and context-window budgeting, and structured formats like JSON carry a real, measurable token tax. The sampling knobs (temperature, top-p, penalties) reshape or truncate the probability distribution the model samples from — they bias the model's behavior, they don't impose hard guarantees, which is why `temperature=0` reduces variance without eliminating it. Prompt engineering is the practical craft behind the persona layer: role, delimiters, specificity, examples, chain-of-thought, positive phrasing, and eliminated ambiguity all measurably steer output, and each has a matching pitfall to watch for when a prompt is over-engineered instead of well-engineered. The `Agent`/`Runner` pair from the OpenAI Agents SDK turns a persona into a runnable object, and the SDK's model abstraction (a plain string for OpenAI, `OpenAIChatCompletionsModel` for any OpenAI-compatible endpoint — which is how we reach both Gemini, our default, and Ollama, our fallback — `LitellmModel` for Anthropic/Bedrock and others) means the persona-and-tool code underneath never has to change when the provider does. Typed outputs via Pydantic close the gap between "probably formatted right" and "structurally guaranteed" — with the caveat that the guarantee itself is provider-enforced, not something the type declaration alone provides on every backend. Tracing exposes the full timeline of a run for debugging, and its dashboard form is one convenience among several, easily substituted locally via `result.new_items` when no key is configured. Tools are the cheapest path to real agency, at a real and compounding cost in tokens, complexity, failure surface, and risk — and tool *design*, as opposed to tool *mechanics*, is a whole chapter of its own.
