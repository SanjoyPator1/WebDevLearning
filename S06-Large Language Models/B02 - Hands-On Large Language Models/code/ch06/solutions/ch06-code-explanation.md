# Chapter 6 Code Explanation — Prompt Engineering

This document is a companion walkthrough to [ch06-prompt-engineering-practice.ipynb](../template/ch06-prompt-engineering-practice.ipynb) (and your working copy in [ch06-prompt-engineering-solution.ipynb](./ch06-prompt-engineering-solution.ipynb)) for *Hands-On Large Language Models* chapter 6 — Methods for improving model output through prompt design.

The numbering below mirrors the **Part 1 → Part 5** structure of the practice notebook, with sub-sections (1.1, 1.2, 2.1, ...) matching the notebook headings exactly. Each section explains the *why* behind the code, gives the math where useful, lists common pitfalls, and points at what the next step builds on.

---

## Table of Contents

- [0 — Notebook Setup](#0--notebook-setup)
- [1 — Loading the Model and Building the Pipeline](#1--loading-the-model-and-building-the-pipeline)
- [2 — Section 1.1: Basic Generation With the Messages API](#2--section-11-basic-generation-with-the-messages-api)
- [3 — Section 1.2: The Chat Template — What the Model Actually Sees](#3--section-12-the-chat-template--what-the-model-actually-sees)
- [4 — Section 1.3: Generation Parameters — Temperature and top_p](#4--section-13-generation-parameters--temperature-and-top_p)
- [5 — Section 2.1: Building a 7-Component Complex Prompt](#5--section-21-building-a-7-component-complex-prompt)
- [6 — Section 2.2: Ablation Study — Which Components Matter?](#6--section-22-ablation-study--which-components-matter)
- [7 — Section 3.1: In-Context Learning (One-Shot)](#7--section-31-in-context-learning-one-shot)
- [8 — Section 3.2: Chain Prompting — Breaking Up the Problem](#8--section-32-chain-prompting--breaking-up-the-problem)
- [9 — Section 3.2 Extended: Designing a 3-Step Chain](#9--section-32-extended-designing-a-3-step-chain)
- [10 — Section 4.1: Chain-of-Thought (Few-Shot)](#10--section-41-chain-of-thought-few-shot)
- [11 — Section 4.2: Zero-Shot Chain-of-Thought — The Magic Phrase](#11--section-42-zero-shot-chain-of-thought--the-magic-phrase)
- [12 — Section 4.2 Extended: Standard vs CoT Comparison](#12--section-42-extended-standard-vs-cot-comparison)
- [13 — Section 4.3: Tree-of-Thought — Parallel Reasoning Agents](#13--section-43-tree-of-thought--parallel-reasoning-agents)
- [14 — Section 5.1: Format Control via Examples (JSON Output)](#14--section-51-format-control-via-examples-json-output)
- [15 — Section 5.1 Extended: Parse and Validate](#15--section-51-extended-parse-and-validate)
- [16 — Section 5.2: Grammar-Based Constrained Sampling](#16--section-52-grammar-based-constrained-sampling)
- [17 — Section 5.2 Extended: Comparing All Three JSON Approaches](#17--section-52-extended-comparing-all-three-json-approaches)
- [18 — Chapter Summary and Key Takeaways](#18--chapter-summary-and-key-takeaways)

---

## 0 — Notebook Setup

```python
# %%capture
# !pip install transformers>=4.40.1 accelerate>=0.27.2
```

Two libraries do all the work in this chapter:

* **`transformers`** — HuggingFace's library. Gives you `AutoModelForCausalLM`, `AutoTokenizer`, and the `pipeline` abstraction. We'll use the high-level `pipeline("text-generation", ...)` rather than calling `.generate(...)` directly because it handles the chat-template formatting for us.
* **`accelerate`** — HuggingFace's device-management library. Required for `device_map="cuda"` (auto-placement of model layers on GPU). Without it, you'd have to call `model.to("cuda")` manually.

The chapter also briefly uses `llama-cpp-python` in section 5.2 for constrained sampling — but we install that only when we need it (saving setup time if you only want sections 1–4).

### Why Phi-3-mini-4k-instruct?

Throughout the chapter we use `microsoft/Phi-3-mini-4k-instruct`:

* **Small** — 3.8B parameters, fits comfortably in 8 GB VRAM in `bfloat16`.
* **Instruction-tuned** — already understands the chat template format, follows instructions reasonably well.
* **4k context** — enough for the long prompts we'll build in section 2.
* **Free and open weights** — no API costs, no rate limits.

Bigger models (Llama-3-70B, GPT-4) follow instructions more reliably, but the *techniques* this chapter teaches are model-independent. Anything that improves Phi-3's output usually improves bigger models' output too.

---

## 1 — Loading the Model and Building the Pipeline

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Phi-3-mini-4k-instruct",
    device_map="cuda",
    torch_dtype="auto",
    trust_remote_code=False,
)
tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    return_full_text=False,
    max_new_tokens=500,
    do_sample=False,
)
```

### What each argument does

| Argument | Purpose |
|----------|---------|
| `device_map="cuda"` | Places the whole model on GPU 0. Use `device_map="auto"` to split across multiple GPUs. |
| `torch_dtype="auto"` | Picks the dtype HuggingFace recommends for this model — bfloat16 for Phi-3, which halves VRAM vs float32 without quality loss. |
| `trust_remote_code=False` | Safety guard. `True` would let the model repo run arbitrary Python at load time. Always `False` unless you specifically need a custom architecture. |
| `return_full_text=False` | Returns *only* the generated tokens, not the prompt + generated tokens concatenated. Otherwise every output starts with the user's prompt repeated, which is noisy. |
| `max_new_tokens=500` | Cap on output length. Without it, generation continues until the model produces an EOS token *or* the context window fills up — which can be hundreds of tokens of waste. |
| `do_sample=False` | Greedy decoding by default. Deterministic — same input always gives the same output. Sampling is opt-in per call (section 4 below). |

### The two-step load: model + tokenizer

You need *both*:

* **Model** — the neural network weights (the 3.8B floating-point parameters).
* **Tokenizer** — the vocabulary mapping (string → token ids) and the **chat template** (how to format multi-turn conversations into a single string before tokenisation).

The tokenizer is small (a few MB) and free to instantiate. The model is the expensive download (~7 GB for Phi-3 in bfloat16, more for float32).

### Why use the `pipeline` abstraction here?

You could call `model.generate(input_ids, ...)` directly, but `pipeline` adds a layer of convenience:

1. **Chat-template formatting** — pass a list of `{"role": "user", "content": "..."}` dicts and `pipe` auto-applies the template.
2. **Automatic tokenisation + detokenisation** — input is a string (or messages), output is a string.
3. **Sensible defaults** — `return_full_text`, `do_sample`, `max_new_tokens` set once and reused.

For production you might drop down to `.generate()` for more control, but for prompt-engineering experimentation `pipeline` is the right level.

---

## 2 — Section 1.1: Basic Generation With the Messages API

```python
messages = [
    {"role": "user", "content": "Create a funny joke about chickens."}
]

output = pipe(messages)
print(output[0]["generated_text"])
```

### The `messages` format

A message is a Python dict with two keys:

* **`role`** — either `"user"` (a human turn), `"assistant"` (a model turn), or `"system"` (top-level instructions, not always supported).
* **`content`** — the actual text.

A conversation is a list of these dicts. The order matters — earliest messages are oldest.

### Why dicts instead of a single string?

A single string can't unambiguously represent multi-turn dialogue. Consider:

```
User: Hello
Bot: Hi
User: What's 2+2?
```

If you pass this as a flat string, the model has to *infer* where each turn ends. With the messages API, the model knows exactly which spans came from the user vs the assistant, and the chat template inserts the model-family-specific delimiters (we'll see these in section 3).

### What `pipe(messages)` returns

A list of dicts (one per generated sequence — pipeline supports batched generation but we only ask for one). Each dict has:

* `generated_text` — the model's reply as a string. With `return_full_text=False`, this is *only* the new tokens.

For our chicken joke, the output is something like:

```
"Sure! Here's a classic chicken joke for you: Why did the chicken
cross the playground? To get to the other slide!"
```

### Determinism

Because we set `do_sample=False` in the pipeline construction, running the same cell twice returns identical output. This is great for reproducibility — every reader of the notebook sees the same joke. It's also limiting for creative work, which is why we'll opt into sampling in section 4.

---

## 3 — Section 1.2: The Chat Template — What the Model Actually Sees

```python
prompt = pipe.tokenizer.apply_chat_template(messages, tokenize=False)
print(prompt)
```

This is one of the most clarifying single cells in the chapter — it lifts the curtain on what `pipe(messages)` does internally.

### What the chat template does

The model is a *text completion* engine. It cannot natively distinguish "user" from "assistant"; it sees one long string of tokens. To make multi-turn dialogue work, model creators embed **special delimiter tokens** that mark where each role begins and ends.

For Phi-3, the messages above expand to:

```
<s><|user|>
Create a funny joke about chickens.<|end|>
<|assistant|>
```

Three delimiters:
* `<s>` — Beginning of sequence (BOS). Tells the model "this is a fresh conversation."
* `<|user|>` and `<|assistant|>` — Role markers. The model has learned to predict the role-appropriate response after seeing these.
* `<|end|>` — End of turn. Tells the model "this speaker is done."

### Why each model family has its own template

| Model family | User marker | Assistant marker | End-of-turn |
|--------------|-------------|------------------|-------------|
| **Phi-3** | `<|user|>` | `<|assistant|>` | `<|end|>` |
| **Llama-3** | `<|start_header_id|>user<|end_header_id|>` | `<|start_header_id|>assistant<|end_header_id|>` | `<|eot_id|>` |
| **TinyLlama (chat)** | `<|user|>` | `<|assistant|>` | `</s>` |
| **Mistral** | `[INST]` | (no marker) | `[/INST]` |

Each family defined its own conventions when it was trained. You cannot use Llama-3's template with Phi-3 — the model wouldn't recognise the delimiters and would output gibberish.

### Why `tokenize=False` here

`apply_chat_template` does two things:
1. Apply the template (format the string).
2. Tokenise the string to a list of ids.

Setting `tokenize=False` stops at step 1 — we get the human-readable string back. Useful for debugging. In production you let it run all the way (`tokenize=True`) and feed the ids straight into the model.

### The practical implication

When you debug a model that's producing weird outputs, **always** print the templated prompt first. Misconfigured chat templates are the #1 cause of "the model just keeps repeating my prompt" or "the model never stops generating" bugs.

---

## 4 — Section 1.3: Generation Parameters — Temperature and top_p

```python
output = pipe(messages, do_sample=True, temperature=1)
output = pipe(messages, do_sample=True, top_p=1)
```

Two parameters control how the next token is sampled from the model's predicted distribution.

### Temperature scaling

The model outputs a vector of logits — one score per vocabulary entry. Before converting them to probabilities, we divide by **temperature** `T`:

$$P(\text{token } i) = \frac{e^{z_i / T}}{\sum_j e^{z_j / T}}$$

| `T` | Effect |
|-----|--------|
| `T < 1` | Sharper distribution. Top tokens dominate. More predictable output. |
| `T = 1` | Identity — softmax on raw logits. Standard sampling. |
| `T > 1` | Flatter distribution. Low-probability tokens get more chances. More creative / random. |
| `T → 0` | Effectively argmax (greedy). Highest-logit token always wins. |

In practice, common ranges:
* **Factual Q&A**: `T = 0` (greedy) or `T = 0.3`
* **Chat**: `T = 0.7`
* **Creative writing**: `T = 1.0` or higher

### top_p (nucleus sampling)

`top_p` filters the candidate tokens *before* sampling. After computing probabilities, sort tokens by descending probability and keep just enough of them to accumulate to `p`:

* `top_p = 0.9` — keep tokens until their cumulative probability reaches 90%. Then sample only from this "nucleus."
* `top_p = 1.0` — keep all tokens (no filtering — equivalent to plain temperature sampling).

The nucleus *adapts* to the model's confidence:
* When the model is very confident (one token has 0.95 probability), the nucleus is just that one token.
* When the model is uncertain (probability spread over 50 tokens at ~0.02 each), the nucleus expands to include all 50.

### The reflection question

The notebook asks: *"Why does `top_p=1` still produce different outputs from greedy decoding even though it includes all tokens in the nucleus?"*

Because `top_p=1` plus `do_sample=True` still **samples** from the distribution. Even though every token is *eligible*, the actual choice involves randomness. Greedy decoding (`do_sample=False`) picks the argmax — no randomness. They differ in the sampling mechanism, not in the candidate set.

### How temperature and top_p combine

You can use both:

```python
pipe(messages, do_sample=True, temperature=0.7, top_p=0.9)
```

The order PyTorch applies them: scale logits by temperature → softmax to probabilities → filter to top_p nucleus → renormalise → sample. This is the de facto standard for modern chatbots.

---

## 5 — Section 2.1: Building a 7-Component Complex Prompt

```python
persona      = "You are an expert in Large Language models. ..."
instruction  = "Summarise the key findings of the paper provided. ..."
context      = "Your summary should extract the most crucial points ..."
data_format  = "Create a bullet-point summary that outlines the method. ..."
audience     = "The summary is designed for ML graduate students. ..."
tone         = "The tone should be professional and clear."
data         = f"Text to summarize: {text}"

query = persona + instruction + context + data_format + audience + tone + data
```

### The 7 components

| Component | Job | Example |
|-----------|-----|---------|
| **Persona** | Sets the role and expertise the model should adopt | "You are an expert in LLMs..." |
| **Instruction** | The specific task | "Summarise this paper" |
| **Context** | Constraints on the output | "Focus on key findings, methodology, evaluation" |
| **Data format** | Structure of the output | "Use bullet points" |
| **Audience** | Who will read this | "Graduate students" |
| **Tone** | Style register | "Professional and clear" |
| **Data** | The actual input | The text to summarise |

### Why component-based prompts work better than free-form ones

A free-form prompt like *"summarise this for me"* gives the model no signal about audience, format, or depth. The model picks defaults — typically a chatty 1-2 paragraph summary aimed at a general audience.

A component-based prompt **constrains every degree of freedom**:

* Audience constraint → vocabulary level adjusts.
* Format constraint → bullet points vs paragraphs.
* Tone constraint → formal vs casual.
* Context constraint → which aspects of the source to emphasise.

Each constraint cuts out a chunk of the model's output space. By the time all 7 are applied, the remaining valid outputs are far closer to what you want.

### Why concatenate strings instead of structured separation?

The model sees one big input regardless. Structured separation (e.g. nested JSON) sometimes helps with very specific models trained on structured prompts, but for general use, plain string concatenation works fine. The model's instruction-tuning was overwhelmingly on plain English prompts.

### When 7 components is overkill

For trivial tasks (*"what's 2+2?"*), all 7 components is wasteful — and can actually *hurt* by adding noise. The next section's ablation study quantifies this.

---

## 6 — Section 2.2: Ablation Study — Which Components Matter?

```python
# Variant 2: Remove persona
query_no_persona = instruction + context + data_format + audience + tone + data

# Variant 3: Minimal prompt
query_minimal = instruction + data
```

### What an ablation study tells you

An **ablation study** is the experimental method of removing one component at a time to measure its individual contribution. It comes from neuroscience (literally "ablating" a brain region to see what stops working) and is borrowed everywhere in ML.

For prompts:
1. Start with the full prompt (the "control").
2. Remove one component at a time, keeping the others.
3. Compare outputs.

The component whose removal changes the output most is the most impactful.

### Two common findings

After running the ablation on summarisation tasks, you usually discover:

1. **Format constraint (`data_format`)** is hugely impactful. Remove it and the model produces prose instead of bullets — completely different output structure.
2. **Tone constraint (`tone`)** is mildly impactful. Removing it shifts the register slightly but the content is similar.
3. **Persona** has surprisingly little impact for technical tasks. The instruction itself already implies expertise. For creative tasks (writing poetry, role-play), persona matters more.

### Why this matters for production

Every token in your prompt costs:
* **Compute** — longer prompts mean longer prefill times.
* **Money** — API providers charge per input token.
* **Context budget** — every prompt token is one less token of model output space.

Pruning components that don't measurably improve quality is a direct cost saving. Ablation studies are how you know what to prune.

### The reflection question

*"Which components had the biggest impact on output quality and format?"*

Empirically: `data_format` and `instruction` always matter. `context` matters when the task is complex. The other four (`persona`, `audience`, `tone`, `data`) vary by task — for some tasks they're crucial, for others they're noise.

---

## 7 — Section 3.1: In-Context Learning (One-Shot)

```python
one_shot_prompt = [
    {
        "role": "user",
        "content": "A 'Gigamuru' is a type of Japanese musical instrument. "
                   "An example of a sentence that uses the word Gigamuru is:"
    },
    {
        "role": "assistant",
        "content": "I have a Gigamuru that my uncle gave me as a gift. I love to play it at parties."
    },
    {
        "role": "user",
        "content": "To 'screeg' something is to swing a sword at it. "
                   "An example of a sentence that uses the word screeg is:"
    },
]
```

### What's happening here

We give the model a **single worked example** ("Gigamuru" → sample sentence) and then a new prompt ("screeg" → ???). The model learns the *pattern* (define an invented word, then produce a natural sentence using it) from one example and applies it to the new word.

This is **in-context learning** — the model's ability to acquire new "skills" purely from examples in the prompt, without any gradient updates.

### Why this works at all

Large language models trained on the internet have seen countless dictionary entries, vocabulary lessons, language learning textbooks. The pattern "definition → example sentence" is deeply familiar. By providing one example, we activate that learned pattern.

Crucially, the model doesn't *understand* "screeg" — it's an invented word. It just imitates the structural pattern: *"verb that means X" → "I [verbed] my [object]. I felt [emotion]."*

### One-shot vs few-shot vs zero-shot

| Setting | Examples in prompt | When to use |
|---------|-------------------|-------------|
| **Zero-shot** | 0 | The task is common enough that the model already knows it (translation, summarisation) |
| **One-shot** | 1 | The task has a non-obvious pattern (custom output format, specific style) |
| **Few-shot** | 2–5 | The pattern is subtle or the model keeps making the same kind of mistake |
| **Many-shot** | 10+ | Almost-fine-tuning. Used when you have many examples and budget for long prompts |

### Token cost check

The notebook's "Token Count Check" exercise asks you to count how many tokens the one-shot prompt uses. Why this matters:

For Phi-3 with 4k context window:
* One-shot example (~50 tokens) leaves ~3950 tokens for response. Plenty.
* 10-shot example (~500 tokens) leaves ~3500 tokens for response. Still fine.
* 100-shot example (~5000 tokens) **doesn't fit**. You'd need to switch to a model with a larger context window or trim examples.

For API-based models (GPT-4, Claude) the same math holds but it's also a billing concern — every token is paid for.

### The reflection observation

*"The model correctly uses 'screeg' as a verb (past tense) applied to a physical object — behaviour it inferred entirely from one example. Notice how the model mirrors the sentence structure from the Gigamuru example."*

This sentence-structure mirroring is the canonical signature of in-context learning. The model didn't just copy "I have a Gigamuru" — it captured the **deeper pattern** of "first-person ownership / experience with the invented word."

---

## 8 — Section 3.2: Chain Prompting — Breaking Up the Problem

```python
# Step 1: Generate product name + slogan
product_prompt = [
    {"role": "user", "content": "Create a name and slogan for a chatbot that leverages LLMs."}
]
product_description = pipe(product_prompt)[0]["generated_text"]

# Step 2: Use Step 1's output to generate a sales pitch
sales_prompt = [
    {"role": "user", "content": f"Generate a very short sales pitch for the following product: '{product_description}'"}
]
sales_pitch = pipe(sales_prompt)[0]["generated_text"]
```

### What chain prompting is

Instead of asking the model to do *everything in one prompt*, you break the task into smaller, more focused sub-tasks and feed each step's output as input to the next step.

```
[Idea] → Step 1 → Product description → Step 2 → Sales pitch → Step 3 → Tweet
```

### Why this beats monolithic prompts

Three reasons:

1. **Each step is focused.** Generating "a name AND a slogan AND a sales pitch AND a tweet" in one prompt risks the model conflating constraints or skipping pieces. One step = one well-defined task.
2. **Intermediate results are inspectable.** If Step 2's output is bad, you can fix the Step 2 prompt without rerunning the entire chain.
3. **Each step has its own context budget.** A monolithic prompt that tries to do 10 things might run out of tokens before producing the final output.

### What it costs

Chain prompting has one drawback: **N steps means N model calls**. For local models this is just slower. For API-based models it's also N× the cost.

The trade-off is almost always worth it for tasks where one of these is true:
* Output quality matters more than latency.
* You need each intermediate step to be inspectable for debugging.
* Different steps need different prompt parameters (one creative, one factual).

### How chain prompting connects to "agent" architectures

If you take chain prompting to its logical conclusion — let the model itself decide which step comes next, what intermediate state to keep, when to stop — you get an **agent**. Agents are essentially "chains where the chain is dynamic." Chapter 7 of this book covers agents directly.

---

## 9 — Section 3.2 Extended: Designing a 3-Step Chain

The notebook asks you to extend the chain by adding a Step 3 that converts the sales pitch into a Twitter/X post under 280 characters.

```python
tweet_prompt = [
    {
        "role": "user",
        "content": (
            f"Based on this sales pitch: '{sales_pitch}'\n\n"
            f"Write a single Twitter/X post of under 280 characters promoting the product. "
            f"Include the product name and 1-2 relevant hashtags."
        ),
    }
]
tweet = pipe(tweet_prompt)[0]["generated_text"]
```

### The pattern

Each step's prompt has three pieces:

1. **The previous step's output**, injected via f-string interpolation.
2. **The new task**, clearly stated.
3. **Constraints specific to this step** (length cap, hashtags, etc.).

### Why this is more reliable than asking for all three at once

Try writing the original prompt as a single ask:

> *"Create a chatbot product. Give me a name, slogan, sales pitch, and a Twitter post under 280 characters with hashtags."*

Phi-3 typically produces something like:

* Name + slogan (good)
* Sales pitch (probably hits maybe 80% of what you want)
* Twitter post (often misses the 280-char limit, often forgets hashtags)

The model has limited attention budget for constraint-checking. When you stack constraints, the later ones get dropped first. Chain prompting splits the constraint set across steps, so each step only has to satisfy 2–3 constraints instead of 10.

### When you would *not* want to chain

For ultra-low-latency interactive use (e.g. a chat completion in a typing assistant), the N× latency hit kills the user experience. In those cases you prefer a single, carefully-engineered monolithic prompt and accept the quality drop.

---

## 10 — Section 4.1: Chain-of-Thought (Few-Shot)

```python
cot_prompt = [
    {
        "role": "user",
        "content": "Roger has 5 tennis balls. He buys 2 more cans of tennis balls. "
                   "Each can has 3 tennis balls. How many tennis balls does he have now?"
    },
    {
        "role": "assistant",
        "content": ("Roger started with 5 balls. 2 cans of 3 tennis balls each is 6 tennis balls. "
                    "5 + 6 = 11. The answer is 11.")
    },
    {
        "role": "user",
        "content": "The cafeteria had 23 apples. If they used 20 to make lunch and bought 6 more, "
                   "how many apples do they have?"
    },
]
```

### What chain-of-thought prompting is

We give the model a worked example where the **reasoning steps are spelled out** ("Roger started with 5... 2 cans of 3 = 6... 5+6=11"). Then we ask a new question. The model learns to mirror the *step-by-step explanation pattern* before producing the final answer.

### Why CoT helps with reasoning

Without CoT, the model has to compute the entire answer "in one shot" — its next-token prediction at the final position has to be the correct number. This works for simple problems but breaks down quickly as the number of intermediate steps grows.

With CoT, the model gets to **think out loud**. Each intermediate step is generated as text, and each step provides context for the next. The cumulative effect: the model converts a single difficult prediction (the final answer) into a sequence of easier predictions (each reasoning step).

### The empirical evidence

In the original CoT paper (Wei et al., 2022), large models showed dramatic improvements on math word problems:

| Model | Standard accuracy | CoT accuracy |
|-------|-------------------|--------------|
| GPT-3 175B | 18% | 57% |
| PaLM 540B | 18% | 58% |

The gap widens with model size — CoT is an "emergent ability" that mostly appears in models above ~60B parameters.

### Why few-shot CoT requires explicit examples

In few-shot CoT, the worked example *teaches* the reasoning pattern. The model sees "problem → reasoning → answer" and learns to reproduce the structure. The "Roger has tennis balls" example becomes a template the model fills in with the cafeteria problem's specifics.

For a model the size of Phi-3 (3.8B), few-shot CoT works reliably for arithmetic but struggles with multi-step logical reasoning. The zero-shot variant (next section) is often comparable or better for small models.

---

## 11 — Section 4.2: Zero-Shot Chain-of-Thought — The Magic Phrase

```python
zeroshot_cot_prompt = [
    {
        "role": "user",
        "content": "The cafeteria had 23 apples. If they used 20 to make lunch and bought 6 more, "
                   "how many apples do they have? Let's think step-by-step."
    }
]
```

### The discovery

Kojima et al. (2022) discovered that you don't need worked examples to trigger CoT — you just need to append a **single phrase**:

> *"Let's think step-by-step."*

That's it. Five words. The model produces step-by-step reasoning before answering, dramatically improving accuracy on reasoning tasks.

### Why this works

Large pretraining corpora contain millions of step-by-step explanations: math tutorials, how-to guides, scientific papers, Wikipedia derivations. The phrase "let's think step-by-step" is statistically associated with these patterns. Including it in the prompt **shifts the model's distribution toward "explain your reasoning" mode**.

It's not magic — it's the model conditioning on a specific text pattern it has learned. But the practical effect is remarkable: a 5-word phrase that you can add to any reasoning prompt and often see ~10–30% accuracy improvement.

### Variants that also work

* *"Let's work this out step by step."*
* *"Think through this carefully."*
* *"First, identify the key information. Then..."*

The exact phrasing matters less than the **intent signal**. Any phrase that strongly conditions on "this is a step-by-step explanation" works.

### The cost vs few-shot CoT

| | Few-shot CoT | Zero-shot CoT |
|---|---|---|
| **Prompt tokens** | High (worked examples) | Low (just the trigger phrase) |
| **Setup effort** | Need to write good examples | Just append "Let's think step-by-step" |
| **Reliability** | Higher — the example shows the exact format | Lower — model picks its own reasoning style |
| **When to use** | Complex domain-specific reasoning | General reasoning with budget-constrained prompts |

For most use cases, **start with zero-shot CoT**. If quality is insufficient, upgrade to few-shot.

---

## 12 — Section 4.2 Extended: Standard vs CoT Comparison

```python
# Standard prompt — no CoT trigger
standard_prompt = [
    {"role": "user", "content": "The cafeteria had 23 apples. If they used 20 to make lunch and bought 6 more, how many apples do they have?"}
]

# Harder multi-step problem
hard_problem = (
    "A train leaves Station A at 9:00 AM travelling at 80 km/h. "
    "Another train leaves Station B at 10:00 AM travelling toward Station A at 100 km/h. "
    "The two stations are 360 km apart. At what time do the two trains meet?"
)
```

### The empirical pattern

For the simple cafeteria problem (23 − 20 + 6 = 9):

* **Standard**: Phi-3 usually gets it right because it's a one-step problem.
* **CoT**: Same answer, just more verbose.

For the train problem:

* **Standard**: Phi-3 frequently gets it wrong. It has to track time differences, relative speeds, and a meeting condition simultaneously — too many things to hold in one prediction.
* **CoT**: Much higher success rate. The model decomposes:
  - At 10:00 AM, train A has already travelled 80 km. Remaining gap: 280 km.
  - Combined closing speed: 80 + 100 = 180 km/h.
  - Time to close 280 km: 280/180 ≈ 1.56 hours.
  - Meeting time: 10:00 AM + 1.56 hours ≈ 11:33 AM.

### Why the gap grows with problem difficulty

Each step in a multi-step problem introduces a potential failure point. For an $N$-step problem, if each step has independent success probability $p$, the joint probability of getting the whole thing right is $p^N$.

CoT effectively **decorrelates** the steps. Each reasoning step gets full attention from the model. With CoT, the per-step success probability $p$ is higher (because each step is simpler), and the cumulative drop with $N$ is less steep.

### Mathematical intuition

Without CoT, the model must predict the *final answer* directly. The space of possible answers for a complex problem can be enormous (any number, any combination of times, etc.). The probability mass spreads thin.

With CoT, the model predicts the *next reasoning step*, which has a much more constrained space (typical step is "use this operation on these numbers"). The probability mass concentrates on the correct continuation.

---

## 13 — Section 4.3: Tree-of-Thought — Parallel Reasoning Agents

```python
zeroshot_tot_prompt = [
    {
        "role": "user",
        "content": (
            "Imagine three different experts are answering this question. "
            "All experts will write down 1 step of their thinking, then share it with the group. "
            "Then all experts will go on to the next step, etc. "
            "If any expert realises they're wrong at any point, then they leave. "
            "The question is: The cafeteria had 23 apples. ..."
        ),
    }
]
```

### What Tree-of-Thought is

CoT generates **one chain** of reasoning. Tree-of-Thought generates **multiple chains in parallel** and lets them check each other.

Three experts each reason step-by-step. If an expert reaches an inconsistency, they "drop out." The surviving experts converge on a shared answer.

### Why this helps for hard problems

Single-chain CoT has a known weakness: **early-step errors compound**. If step 1 contains a subtle mistake, every subsequent step builds on the wrong foundation. The final answer can be confidently wrong.

Tree-of-Thought addresses this by exploring multiple reasoning paths simultaneously. If one expert makes an early error, the other experts (who took different paths) catch and correct it.

### The implementation here is purely prompt-based

This is a simulation. We're not actually running three separate models — we're prompting one model to *pretend* to be three experts. The model interleaves their reasoning in its output.

Real ToT implementations (the Yao et al. 2023 paper) run multiple actual model invocations, with each invocation exploring a different reasoning branch, and a separate "judge" prompt selecting the best one. That's much more expensive but also more reliable.

The prompt-only version is a useful approximation when you can't afford multiple model calls.

### Where ToT shines vs CoT

ToT outperforms CoT when:

* **Multiple valid reasoning paths exist** (constraint satisfaction problems, puzzles)
* **Early-step errors are catastrophic** (long deductive chains)
* **The problem benefits from "what-if" exploration** (planning tasks)

For straightforward arithmetic or single-path problems, CoT is sufficient and cheaper.

### The reflection question — when ToT > CoT

*"For what types of problems would ToT provide the most benefit over CoT?"*

The analysis dict in the practice notebook says:

> *"Problems with multiple plausible solution paths (e.g., constraint satisfaction, planning tasks) where a single chain of reasoning can go wrong early and compound the error."*

That's exactly right. The empirical literature also shows ToT helps with creative writing (different "experts" produce different narrative angles, then you pick the best).

---

## 14 — Section 5.1: Format Control via Examples (JSON Output)

```python
# Zero-shot
zeroshot_prompt = [
    {"role": "user", "content": "Create a character profile for an RPG game in JSON format."}
]

# One-shot with explicit template
one_shot_template = """Create a short character profile for an RPG game. Make sure to only use this format:

{
  "description": "A SHORT DESCRIPTION",
  "name": "THE CHARACTER'S NAME",
  "armor": "ONE PIECE OF ARMOR",
  "weapon": "ONE WEAPON"
}
"""
```

### The fundamental problem

Many real applications need **structured output** — JSON, YAML, CSV — that downstream code can parse. The model needs to produce this format consistently, with no extra text, no missing fields, no malformed quotes.

Three strategies are demonstrated in this chapter:

1. **Zero-shot** — just ask. Works some of the time.
2. **One-shot** — provide an example. Works most of the time.
3. **Constrained sampling** (next section) — enforce the format at the token level. Works always.

### What zero-shot JSON typically produces

```
Sure! Here's a JSON character profile:

```json
{
  "Name": "Aria Stormblade",
  "Race": "Half-elf",
  "Class": "Ranger",
  "Stats": { ... }
}
```

I hope you find this useful!
```

Three problems with this:
1. **Extra prose before and after** the JSON. Your downstream parser will fail.
2. **Inconsistent schema.** The next call might have different keys, capitalisation, or nesting.
3. **Code fence wrapping.** Sometimes there, sometimes not.

### How the one-shot template fixes this

The one-shot prompt embeds the exact schema you want. The model now has a strong cue: *"this is the structure of valid output."* It produces:

```
{
  "description": "A brave warrior who lost his family to dragons.",
  "name": "Roland Stoneheart",
  "armor": "Plate Mail",
  "weapon": "Greatsword"
}
```

Much better. The fields match the template, no extra prose, no code fences.

### Why this still isn't enough for production

Even one-shot with a good template, the model **occasionally** misbehaves:
* It might add a trailing comma (invalid JSON).
* It might switch a string for a number (`"armor": 1` instead of `"armor": "Plate Mail"`).
* It might generate a long description that includes unescaped quotes.

For a system that calls `json.loads()` on the output and crashes if parsing fails, "99% reliable" isn't good enough. That's what motivates section 5.2.

---

## 15 — Section 5.1 Extended: Parse and Validate

```python
import json

raw_output = outputs[0]["generated_text"].strip()

try:
    parsed = json.loads(raw_output)
    print("Parsed successfully:")
    print(json.dumps(parsed, indent=2))
except json.JSONDecodeError as e:
    print(f"Parse failed: {e}")
    print(f"Raw output: {raw_output}")
```

### The defensive pattern

Any code that consumes LLM output should treat it as untrusted input:

1. **Try to parse it** — wrap in `try/except`.
2. **On failure, log the actual output** so you can see what went wrong.
3. **Either retry with a corrected prompt, fall back to a default, or escalate to a human.**

### Common JSON parse failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Expecting value` | Extra prose before the `{` | Strip prefix or use regex to extract |
| `Extra data` | Extra prose after the `}` | Find the closing `}` and truncate |
| `Expecting ',' delimiter` | Missing comma between fields | Tighter prompt, more examples |
| `Invalid \escape` | Unescaped quote inside a string | Use constrained sampling |
| `Trailing comma` | The model added a comma after the last field | Reprompt or use constrained sampling |

### Why "just reprompt and retry" isn't always a great fix

The naive fallback is:

```python
for attempt in range(5):
    output = pipe(prompt)
    try:
        return json.loads(output[0]["generated_text"])
    except json.JSONDecodeError:
        continue
raise RuntimeError("Failed after 5 attempts")
```

Three problems:
1. **Cost** — every retry is another model call.
2. **Latency** — 5 retries can add seconds to your response time.
3. **No guarantee** — if the model is structurally producing bad output, retries don't fix it.

For applications where reliability is critical, constrained sampling (next section) is the right answer.

---

## 16 — Section 5.2: Grammar-Based Constrained Sampling

```python
from llama_cpp.llama import Llama

llm = Llama.from_pretrained(
    repo_id="microsoft/Phi-3-mini-4k-instruct-gguf",
    filename="*fp16.gguf",
    n_gpu_layers=-1,
    n_ctx=2048,
    verbose=False,
)

output = llm.create_chat_completion(
    messages=[{"role": "user", "content": "Create a warrior for an RPG in JSON format."}],
    response_format={"type": "json_object"},
    temperature=0,
)['choices'][0]['message']['content']
```

### What constrained sampling does

Instead of asking the model nicely to produce JSON, we **modify the sampling process itself**:

1. After the model outputs logits for the next token, we **mask out** every token that would lead to invalid JSON.
2. We only sample from the remaining (valid) tokens.

Result: the model **literally cannot** produce invalid JSON. The output is guaranteed to parse.

### How this works under the hood

The library (here `llama-cpp-python`) maintains a **grammar state machine**. After each generated token, it knows what tokens are syntactically valid next.

For JSON:
* At the start, only `{`, `[`, or whitespace are valid first tokens.
* After `{`, only `"` (start of a key) is valid.
* After a key like `"name"`, only `:` is valid.
* After `:`, valid values are strings, numbers, `true`/`false`/`null`, arrays, or objects.

When the model wants to sample the next token, the library:
1. Looks at all 32,000 logits the model produced.
2. Asks the grammar: which of these are valid right now?
3. Sets the logits of invalid tokens to `-inf`.
4. Samples from the remaining valid set.

### Why this requires `llama-cpp-python` and not `transformers`

HuggingFace `transformers` doesn't natively support grammar-constrained generation as of writing. `llama-cpp-python` does — it inherited the feature from llama.cpp's GBNF (Backus-Naur Form) grammar system.

The model itself is the same Phi-3-mini you've been using throughout the chapter — just loaded in a different format (GGUF, the llama.cpp format) and via a different library.

### The memory cleanup before loading

```python
del model, tokenizer, pipe
gc.collect()
torch.cuda.empty_cache()
```

Why this matters: we have two copies of Phi-3 about to be in memory (the HuggingFace one and the llama.cpp one). That's ~14 GB combined in bfloat16 — likely too much. Explicitly freeing the HF version before loading the GGUF version prevents OOM errors.

### `temperature=0` for constrained sampling

We pair constrained sampling with greedy decoding (`temperature=0`). Why?

* Constraints already remove freedom — the grammar narrows the choice set.
* With sampling on top, you'd add randomness on a near-deterministic process. Not useful.

For structured outputs, deterministic constrained sampling is the standard.

### The output is guaranteed valid

```python
import json
parsed = json.loads(output)  # this NEVER fails with constrained sampling
print(json.dumps(parsed, indent=4))
```

This is the entire point. The `json.loads()` call cannot raise `JSONDecodeError`. If the model wanted to produce invalid JSON, the grammar prevented it.

---

## 17 — Section 5.2 Extended: Comparing All Three JSON Approaches

The notebook closes by asking you to compare the three approaches you've now seen:

| Approach | Setup cost | Per-call cost | Reliability | Schema control |
|----------|-----------|---------------|-------------|----------------|
| **Zero-shot** | None | Low | ~70% — model picks arbitrary schema | None |
| **One-shot** | Need a good example | Low | ~95% — usually matches example | Specifies schema but doesn't enforce |
| **Constrained sampling** | Need llama-cpp + GGUF model | Slightly slower (grammar check per token) | **100%** — grammar makes invalid output impossible | Schema is a hard constraint |

### When to use which

* **Zero-shot** — prototyping, exploring whether the model can do the task at all.
* **One-shot** — most production cases. Cheap, reliable enough.
* **Constrained sampling** — when *any* parse failure is unacceptable (e.g. agents that programmatically execute model output, or financial / medical applications).

### The fourth option that's not in this chapter

**Tool-call APIs** (OpenAI's `function_calling`, Anthropic's `tool_use`) achieve similar guarantees as constrained sampling but with cleaner ergonomics. You define the schema, the API enforces it server-side, and you get back a parsed object. If you're API-bound rather than running locally, this is usually the way to go.

The local equivalent — constrained sampling in `llama-cpp-python` — gives you the same property without depending on an API provider.

### A useful mental model

The three approaches correspond to three layers of trust in the model:

* **Zero-shot** says: "Model, you've seen enough JSON on the internet to know what I want."
* **One-shot** says: "Here's an example. Match it."
* **Constrained sampling** says: "I don't trust you to follow the format. I'm going to make it impossible for you to break it."

The right layer depends on your tolerance for failure and your engineering budget.

---

## 18 — Chapter Summary and Key Takeaways

### Prompt anatomy (Part 2)

A complex prompt has up to **7 components**: persona, instruction, context, format, audience, tone, data. Each adds specificity. Ablation studies reveal which components matter for your specific task — typically `instruction` and `format` are most impactful.

### In-context learning (Part 3)

LLMs can learn new tasks from examples in the prompt:
* **Zero-shot** — no examples, only the task.
* **One-shot** — single example to anchor a pattern.
* **Few-shot** — multiple examples for tricky tasks.

Chain prompting decomposes complex tasks into a sequence of focused steps, with each step's output feeding into the next.

### Reasoning techniques (Part 4)

Three escalating techniques for problems that require multi-step thinking:

* **Few-shot CoT** — show worked example with explicit reasoning.
* **Zero-shot CoT** — just append *"Let's think step-by-step."*
* **Tree-of-Thought** — multiple parallel reasoning paths converging on a consensus answer.

The harder the problem, the more these techniques help.

### Output verification (Part 5)

For structured outputs:

* **Format control via examples** — embed schema in the prompt as a one-shot.
* **Parse and validate** — wrap consumer code in try/except, log failures.
* **Grammar-based constrained sampling** — guarantee valid output by masking invalid tokens during generation.

The path from "ask nicely" to "make it impossible to fail" is the path from prototyping to production.

### Key meta-takeaway

**Prompt engineering is empirical, not theoretical.** The techniques in this chapter are tools — which to use, in what combination, and how to phrase each piece depends on your model, your task, and your data. The right reflex is:

1. Start with the simplest approach.
2. Test on representative inputs.
3. Identify the failure mode.
4. Add the minimum complexity needed to fix it.
5. Repeat.

This loop is the same whether you're prompting Phi-3 locally, GPT-4 via API, or a frontier model two years from now.
