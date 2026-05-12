# Chapter 12: Fine-Tuning Generation Models

## Hands-On Large Language Models — Chapter 12

> A pretrained model knows the world. A fine-tuned model knows what you need. The art of fine-tuning is bridging that gap as efficiently as possible — and in this chapter, we learn exactly how.

---

## Table of Contents

1. [The Three LLM Training Steps](#1-the-three-llm-training-steps)
   - [1a. Why Three Stages? The Doctor-in-Training Analogy](#1a-why-three-stages-the-doctor-in-training-analogy)
   - [1b. Stage 1 — Pretraining: Reading Every Book in the Library](#1b-stage-1--pretraining-reading-every-book-in-the-library)
   - [1c. The Pattern-Completion Problem — Why a Base Model Cannot Follow Instructions](#1c-the-pattern-completion-problem--why-a-base-model-cannot-follow-instructions)
   - [1d. Stage 2 — Supervised Fine-Tuning: Learning the Q&A Format](#1d-stage-2--supervised-fine-tuning-learning-the-qa-format)
   - [1e. Stage 3 — Preference Tuning: Learning Taste, Not Just Format](#1e-stage-3--preference-tuning-learning-taste-not-just-format)
   - [1f. The Full Pipeline End-to-End](#1f-the-full-pipeline-end-to-end)
2. [Supervised Fine-Tuning (SFT)](#2-supervised-fine-tuning-sft)
   - [2a. Full Fine-Tuning — The Direct Approach](#2a-full-fine-tuning--the-direct-approach)
   - [2b. The Memory Wall — Why Full Fine-Tuning Does Not Scale](#2b-the-memory-wall--why-full-fine-tuning-does-not-scale)
   - [2c. The Parameter-Efficient Idea — Why Tiny Updates Are Enough](#2c-the-parameter-efficient-idea--why-tiny-updates-are-enough)
   - [2d. Adapters — Trainable Bottleneck Modules](#2d-adapters--trainable-bottleneck-modules)
   - [2e. LoRA — Approximating the Update with Two Thin Matrices](#2e-lora--approximating-the-update-with-two-thin-matrices)
   - [2f. LoRA Dry-Run and Parameter Count Comparison](#2f-lora-dry-run-and-parameter-count-comparison)
   - [2g. Quantization — Compressing the Base Model's Weights](#2g-quantization--compressing-the-base-models-weights)
   - [2h. QLoRA — Blockwise NF4 Quantization Combined with LoRA](#2h-qlora--blockwise-nf4-quantization-combined-with-lora)
3. [Instruction Tuning with QLoRA — Practical Walkthrough](#3-instruction-tuning-with-qlora--practical-walkthrough)
   - [3a. The Walkthrough Pipeline — What We're Building](#3a-the-walkthrough-pipeline--what-were-building)
   - [3b. Dataset Preparation and Chat Templates](#3b-dataset-preparation-and-chat-templates)
   - [3c. Model Quantization — The BitsAndBytes Config](#3c-model-quantization--the-bitsandbytes-config)
   - [3d. LoRA Configuration — Every Parameter Explained](#3d-lora-configuration--every-parameter-explained)
   - [3e. Training Arguments — What They Actually Do](#3e-training-arguments--what-they-actually-do)
   - [3f. SFTTrainer and the Training Loop](#3f-sfttrainer-and-the-training-loop)
   - [3g. Merging LoRA Weights for Inference](#3g-merging-lora-weights-for-inference)
4. [Evaluating Generative Models](#4-evaluating-generative-models)
   - [4a. Word-Level Metrics — Perplexity, BLEU, ROUGE, BERTScore](#4a-word-level-metrics--perplexity-bleu-rouge-bertscore)
   - [4b. Benchmarks — The Public Leaderboards](#4b-benchmarks--the-public-leaderboards)
   - [4c. Automated Evaluation — LLM-as-a-Judge](#4c-automated-evaluation--llm-as-a-judge)
   - [4d. Human Evaluation and Chatbot Arena](#4d-human-evaluation-and-chatbot-arena)
5. [Preference Tuning and RLHF](#5-preference-tuning-and-rlhf)
   - [5a. Why Instruction Tuning Is Not Enough](#5a-why-instruction-tuning-is-not-enough)
   - [5b. The Reward Model](#5b-the-reward-model)
   - [5c. Proximal Policy Optimization (PPO)](#5c-proximal-policy-optimization-ppo)
6. [Direct Preference Optimization (DPO)](#6-direct-preference-optimization-dpo)
   - [6a. The Core Insight — No Reward Model Needed](#6a-the-core-insight--no-reward-model-needed)
   - [6b. How DPO Works — The Four Players](#6b-how-dpo-works--the-four-players)
   - [6c. The DPO Loss Function](#6c-the-dpo-loss-function)
   - [6d. DPO vs PPO — Why DPO Won](#6d-dpo-vs-ppo--why-dpo-won)
   - [6e. ORPO — Combining SFT and DPO in One Pass](#6e-orpo--combining-sft-and-dpo-in-one-pass)
7. [Preference Tuning with DPO — Practical Walkthrough](#7-preference-tuning-with-dpo--practical-walkthrough)
   - [7a. DPO Dataset Format](#7a-dpo-dataset-format)
   - [7b. DPO Training Configuration](#7b-dpo-training-configuration)
   - [7c. DPOTrainer and the Beta Parameter](#7c-dpotrainer-and-the-beta-parameter)
   - [7d. Stacking SFT and DPO Adapters](#7d-stacking-sft-and-dpo-adapters)
8. [Key Takeaways](#8-key-takeaways)

---

## 1. The Three LLM Training Steps

Fine-tuning is the headline topic of this chapter, but you cannot understand fine-tuning without first understanding the larger pipeline it lives inside. Every modern LLM is trained in three distinct stages, and each fine-tuning technique we will meet is designed to do its job within one of those stages. We need a clear mental model of the full journey before we start engineering pieces of it.

### 1a. Why Three Stages? The Doctor-in-Training Analogy

Consider how a doctor becomes good at their job. They do not arrive at competence in a single stage. First they spend years in **medical school**, memorising every system of the body — anatomy, biochemistry, pharmacology. They absorb an enormous body of factual knowledge. But a fresh medical school graduate cannot run a clinic. They know what is in every textbook, but they have never actually structured a consultation, taken a patient history, or delivered a difficult diagnosis. So they enter **residency** — years of supervised practice where senior doctors teach them how to *apply* their knowledge: how to phrase a question, how to write a discharge summary, how to act in an emergency. After residency they can practise medicine. But there is still a third skill that separates good doctors from great ones: **bedside manner**. Two doctors with identical factual knowledge can deliver the same correct answer in very different ways — one is calm and concrete, the other is brusque and evasive. Patients can tell the difference, even when both are technically right.

Large language models are trained almost identically, and for almost the same reasons. Each of the three LLM training stages fixes something the previous stage cannot. Skip any one and the resulting model will fail in a specific, predictable way.

```
The three LLM training stages mapped onto the doctor analogy:

  Stage 1: Pretraining            ── Medical school   (learn everything)
  Stage 2: Supervised Fine-Tuning ── Residency        (learn to apply it)
  Stage 3: Preference Tuning      ── Bedside manner   (learn to do it well)
```

The next four subsections take each stage in turn, explaining *what* the training looks like, *why* it is needed, and *what is still broken* when that stage is complete.

### 1b. Stage 1 — Pretraining: Reading Every Book in the Library

The first stage is **pretraining**, and it is where the model acquires almost everything it will ever know. The training data is enormous — hundreds of billions of tokens scraped from books, websites, code repositories, academic papers, Wikipedia, and countless other sources. The model that emerges is called a **base model** or **foundation model**.

The training objective is deceptively simple: given a sequence of words, predict the next word. Then shift the sequence by one position and do it again. No human labels, no curated questions and answers — just raw text where the "label" for every position is whatever word actually came next. This is **next-token prediction**, and it is **self-supervised** because the labels come for free from the text itself.

Formally, we want to minimise the negative log-probability that the model assigns to the *actual* next token at every position:

$$\mathcal{L}_{\text{pretrain}} = - \sum_{t=1}^{T} \log P_\theta(x_t \mid x_1, x_2, \ldots, x_{t-1})$$

| Symbol | Meaning |
|--------|---------|
| $x_t$ | the $t$-th token in the training sequence (the word at position $t$) |
| $T$ | total number of tokens in the sequence |
| $\theta$ | all parameters of the model — billions of weights being trained |
| $P_\theta(x_t \mid x_1, \ldots, x_{t-1})$ | model's predicted probability for the true next token, given everything that came before |
| $\mathcal{L}_{\text{pretrain}}$ | total loss — we want this small, which means the model is confident on the right token |

**Tiny dry-run.** Suppose the model is shown the sentence "The car is red" tokenised as four tokens — "The", "car", "is", "red". The model walks left-to-right and at each position predicts a probability distribution over the entire vocabulary:

```
Position 1: see "The"          → predict next → assigns probability to every word
Position 2: see "The car"      → predict next → ideal: high probability on "is"
Position 3: see "The car is"   → predict next → ideal: high probability on "red"
```

Imagine at position 3 the model produces this distribution over a toy 4-word vocabulary:

| Candidate next word | Predicted probability $P_\theta$ |
|--------------------|----------------------------------|
| red                | 0.55                             |
| blue               | 0.20                             |
| fast               | 0.15                             |
| broken             | 0.10                             |

The true next token is "red", so the loss contributed at this position is:

$$-\log P_\theta(\text{red} \mid \text{"The car is"}) = -\log(0.55) \approx 0.598$$

If the model had been completely certain — probability 1.0 on "red" — the loss would be $-\log(1.0) = 0$. If the model had thought "red" was nearly impossible — probability 0.01 — the loss would be $-\log(0.01) \approx 4.605$, a much larger penalty. The gradient of this loss flows backward through every layer, nudging the parameters so that next time "red" gets slightly more probability mass after "The car is".

Repeat this trillions of times across the entire internet, and the model effectively absorbs the structure of language: grammar, factual knowledge, reasoning patterns, code conventions, mathematical relationships, conversational rhythms.

```
Pretraining in one picture:

  [Unlabeled internet text]
        │   (hundreds of billions of tokens)
        ▼
  [Next-token prediction × trillions of training steps]
        │
        ▼
   Base Model
     ✓ Vast factual knowledge
     ✓ Grammar, syntax, reasoning patterns
     ✗ Will not follow instructions  ← see 1c
```

The base model is impressive — but unusable as a chat assistant. The next subsection explains *why*.

### 1c. The Pattern-Completion Problem — Why a Base Model Cannot Follow Instructions

Here is the single most important fact about base models: **they do not answer questions, they complete patterns**. If you type a question into a raw base model, it will try to figure out what kind of text typically follows that question in the corpus it was trained on — and that is often *not* an answer.

The book gives a perfect illustration. Type "What is 1+1?" into a base model and instead of seeing the answer "2", you might see a continuation like this:

```
Input :  What is 1+1?
Output:  2.
         What is 1+1+1?
         3.
         What is 1+1+1+1?
         4.
         What is 1+1+1+1+1?
         ...
```

That "2." is not the answer to the arithmetic question. It is the *list-item number* of the next question in what the model has decided is a numbered list of practice problems. This is not stupidity — it is exactly what pretraining trained the model to do. The training data contained many textbook-style numbered problem sets, so when the model sees "What is 1+1?", the most statistically likely continuation in the corpus is **another question on the next line**, not an answer.

```
The mechanism, made explicit:

  Training data contained many sequences like:
     "1. What is X?
      2. What is Y?
      3. What is Z?"

  At inference: model sees  "What is 1+1?"
                model thinks: "This looks like the first item of a problem set."
                model predicts: "2.\nWhat is 1+1+1?..."
```

The base model is being completely loyal to the distribution it learned. The fault is not in the model — the fault is in the mismatch between the training objective ("continue this text") and what we want at deployment time ("answer this question"). The model knows that 1+1 = 2. It just has no reason to think we want it to *tell us*.

This is the **pattern-completion problem**, and it is what Stage 2 exists to solve. The fix is not to teach the model more facts — it already knows the answer. The fix is to teach it a new *behaviour*: when you see a question-shaped input, produce an answer-shaped output.

### 1d. Stage 2 — Supervised Fine-Tuning: Learning the Q&A Format

The second stage is **Supervised Fine-Tuning (SFT)**, also called **instruction tuning**. The training objective is identical to pretraining — predict the next token — but the *data* changes completely. Instead of raw internet text, we use a curated set of **instruction–response pairs**:

```python
# A single SFT training example
{
    "instruction": "Tell me something about reinforcement learning.",
    "response":    "Reinforcement learning (RL) is a type of machine learning "
                   "where an agent learns to make decisions by taking actions "
                   "in an environment to maximize a reward signal."
}
```

During training, the model is shown the full "instruction + response" sequence concatenated together and asked to predict each next token. But — and this is the critical detail — the **loss is computed only over the response tokens**. We do not want the model to learn to invent user questions; we want it to learn how to *produce answers given questions*.

```
SFT loss masking (X = loss computed at this position, _ = position is ignored):

  Tokens:  [ Tell me something about reinforcement learning . | RL is a type of ML ... ]
  Mask:    [  _   _      _       _         _              _  _ |  X  X  X  X  X  X  X  ]
                            (instruction — ignored)              (response — supervised)
```

Why ignore the instruction tokens? Because the user wrote them — they are inputs, not things the model should generate. Computing loss over them would push the model toward producing more user-style inputs, which is the opposite of what we want. By masking them out we make the training signal sharp and unambiguous: "given this instruction, produce *exactly* this response."

The SFT dataset is far smaller than the pretraining corpus — typically a few thousand to a few hundred thousand examples, against the trillions of tokens used in pretraining — but the behavioural change is dramatic. A model that was pattern-completing question lists becomes a model that actually answers questions, summarises documents, follows formatting constraints, and converses across multiple turns.

```
SFT in one picture:

  [ Base Model ] ─── trained on instruction–response pairs ───► [ Instruction-Tuned Model ]
        ▲                                                                  │
        │                                                                  ▼
  Pretrained knowledge                                          Knows when to stop pattern-
   (entirely preserved)                                         completing and answer instead

  Data scale:    thousands to hundreds of thousands of pairs
  Loss target:   response tokens only
  Compute cost:  hours to days on a few GPUs (vs months on thousands of GPUs for pretraining)
```

SFT can also be used for narrower tasks like classification or summarisation, but its iconic use case — and the one we will execute in Section 3 — is converting a base generative model into a chat-capable assistant.

### 1e. Stage 3 — Preference Tuning: Learning Taste, Not Just Format

After SFT the model can follow instructions. So what is still missing? *Taste*. The instruction-tuned model has no sense of *which way* of following an instruction is better. Asked to explain something, it might produce a correct but unnecessarily long answer, or give two parallel answers when one would do, or be evasive when the user wanted directness, or sound preachy when they wanted concision. It is doing what was asked — it is just not doing it *well*.

This is precisely the gap that separates two equally knowledgeable doctors with different bedside manners. Both know the answer. One delivers it with calm and precision; the other rambles or hedges. SFT trains the model to *answer*; it does not train it to answer *well*.

**Preference tuning** addresses this. Also called **alignment**, or in its most famous form **RLHF (Reinforcement Learning from Human Feedback)**, this stage uses a different kind of training data: **preference pairs**. For a single prompt, humans (or another model acting as judge) provide two candidate responses and label one as **chosen** (preferred) and the other as **rejected** (not preferred):

```python
# A single preference-tuning training example
{
    "prompt":   "Explain reinforcement learning in two sentences.",
    "chosen":   "Reinforcement learning is a paradigm where an agent learns "
                "by trial and error, receiving rewards for good actions and "
                "penalties for bad ones. Over time it learns a policy that "
                "maximises cumulative reward.",
    "rejected": "Reinforcement learning is a complex subfield of machine "
                "learning with many algorithms and applications. It is widely "
                "studied. A complete explanation would require much more space."
}
```

Both responses are technically valid English answers to the prompt. The chosen one is direct, concrete, and respects the two-sentence constraint. The rejected one is vague, evasive, and ignores the requested length. The training objective is to **increase the probability the model assigns to the chosen response** and **decrease the probability it assigns to the rejected response** — for this same prompt.

The crucial thing to notice is that the model does not learn any new *facts* in this stage. It already knew what reinforcement learning is. What it learns is *preferences* about how to express what it already knows: how long to be, when to be direct, when to hedge, when to refuse, how concrete to make examples. The result is an **aligned model** (also called a **preference-tuned model**), and this is the kind of model you actually interact with when you use ChatGPT, Claude, or Gemini.

We will see in Sections 5 and 6 that there are two main families of techniques for executing this stage: classical RLHF with a reward model and PPO (older, more complex), and Direct Preference Optimization or DPO (newer, simpler, now dominant in practice). Section 7 walks through a full DPO run.

### 1f. The Full Pipeline End-to-End

Putting the three stages together gives the complete training pipeline that every major commercial LLM follows:

```
                         The full LLM training pipeline:

  ┌────────────────────────┐
  │ Untrained LLM          │   random weights, knows nothing
  └───────────┬────────────┘
              │  Pretraining (next-token prediction on raw internet text)
              │  Hundreds of billions of tokens, weeks–months on thousands of GPUs
              ▼
  ┌────────────────────────┐
  │ Base / Foundation      │   knows language and facts, will not follow instructions
  │ Model                  │
  └───────────┬────────────┘
              │  Supervised Fine-Tuning (instruction–response pairs)
              │  Thousands to hundreds of thousands of examples, hours–days on a few GPUs
              ▼
  ┌────────────────────────┐
  │ Instruction-Tuned      │   follows prompts, but lacks taste for quality
  │ Model                  │
  └───────────┬────────────┘
              │  Preference Tuning (chosen vs rejected pairs)
              │  Thousands of preference pairs, hours on a few GPUs
              ▼
  ┌────────────────────────┐
  │ Aligned /              │   helpful, honest, appropriately concise — production-ready
  │ Preference-Tuned LLM   │
  └────────────────────────┘
```

Pretraining provides the **knowledge**. SFT provides the **interface**. Preference tuning provides the **character**. Each stage builds on the last, and each addresses a problem the previous stage cannot solve on its own.

This chapter assumes pretraining is already done — we start from an open-source base model and execute the last two stages ourselves. Section 2 sets up the theoretical foundation for the techniques (full fine-tuning, adapters, LoRA, QLoRA) that make Stage 2 affordable on a single GPU; Section 3 turns that theory into a working instruction-tuning run.

---

## 2. Supervised Fine-Tuning (SFT)

Stage 2 of the pipeline is where this chapter actually rolls up its sleeves. We have a base model that has read most of the internet, and a curated dataset of instruction–response pairs. How do we update the model? The naive answer — "update every parameter, exactly like pretraining did" — turns out to be impossible on any single GPU for any modern model. This section walks through the ladder of techniques the field developed to climb around that wall: from full fine-tuning at the top (best but unaffordable), down through adapters and LoRA, and finally to QLoRA at the bottom (drastically cheaper, almost as good).

### 2a. Full Fine-Tuning — The Direct Approach

Think of a base model as a fully printed and bound textbook — every page, every sentence, every figure already in place. **Full fine-tuning** is the equivalent of opening that textbook and editing every single page to specialise it for your domain. Nothing is off-limits; every word can be rewritten. It is the most thorough form of adaptation possible.

Mechanically, full fine-tuning is identical to pretraining. The training loop, the optimizer, the gradient flow — all unchanged. The only thing that changes is the data: instead of raw internet text, we feed in labelled instruction–response pairs, and (as discussed in 1d) we mask the loss so only the response tokens contribute.

```python
# A single full-fine-tuning training example
{
    "instruction": "Explain what reinforcement learning is in two sentences.",
    "response":    "Reinforcement learning is a type of machine learning where "
                   "an agent learns by taking actions in an environment and "
                   "receiving rewards or penalties. Over time, the agent learns "
                   "a policy that maximises its cumulative reward."
}
```

Full fine-tuning gives the highest performance ceiling — the model can adjust every single weight to the new task. If you have unlimited compute, this is what you would always choose. The catch is that the compute is *not* unlimited for anyone except a handful of well-funded labs, and the next subsection makes the size of that catch precise.

### 2b. The Memory Wall — Why Full Fine-Tuning Does Not Scale

When you fine-tune a model, the GPU has to hold four distinct things in memory simultaneously: the **parameters** (the weights themselves), the **gradients** (one floating-point value per parameter), the **optimizer state** (Adam stores two extra running averages per parameter), and the **activations** (intermediate hidden states needed for backpropagation). For float32 precision — the default during pretraining — that adds up to roughly **16 bytes per parameter** before counting activations.

Why 16? Because each of the four items is the same size as the parameter tensor itself, and at float32 each entry of that tensor is 4 bytes. The parameters cost 4 bytes per entry; the gradients cost another 4; Adam's first moment $m$ another 4; Adam's second moment $v$ another 4. Sum: 16 bytes per parameter.

For GPT-3, with its 175 billion parameters, the math is brutal:

| Component | Per-parameter cost | Total (GPT-3, fp32) |
|-----------|--------------------|---------------------|
| Parameters | 4 bytes | $175\text{B} \times 4 = 700$ GB |
| Gradients | 4 bytes | $175\text{B} \times 4 = 700$ GB |
| Adam first moment ($m$) | 4 bytes | $175\text{B} \times 4 = 700$ GB |
| Adam second moment ($v$) | 4 bytes | $175\text{B} \times 4 = 700$ GB |
| **Total (before activations)** | **16 bytes** | **≈ 2,800 GB** |

```
GPT-3 full fine-tuning memory footprint (float32, before activations):

  Parameters       ████████████████  700 GB
  Gradients        ████████████████  700 GB
  Adam m           ████████████████  700 GB
  Adam v           ████████████████  700 GB
                   ────────────────  ──────────
  Total                              ~2,800 GB

A single high-end A100 GPU holds 80 GB.
You would need 35 of them just to hold the training state for one model —
and that is before activations, which add still more.
```

The problem does not disappear at smaller scales. A 7-billion-parameter model — which sounds modest by 2023 standards — needs $7\text{B} \times 16 = 112$ GB of training state, comfortably more than any consumer GPU can hold (RTX 4090: 24 GB; A100: 80 GB). The memory wall is real for almost every practitioner, and it is what motivated every technique in the rest of this section.

### 2c. The Parameter-Efficient Idea — Why Tiny Updates Are Enough

Suppose you are a classically trained violinist who has spent twenty years mastering posture, intonation, bowing technique, and the entire Bach repertoire. Now someone asks you to play folk music at a friend's wedding. Do you have to rewire your understanding of music from scratch? Of course not. Almost everything you have learned transfers directly. What you need to absorb is a small *overlay*: a few new bowing patterns, a couple of rhythmic conventions, the feel of the genre. Ninety-nine percent of what makes you a violinist stays exactly the same; only a small folk-specific layer gets added on top.

This is precisely the insight that drives **Parameter-Efficient Fine-Tuning (PEFT)**. A pretrained model already contains the vast majority of what it needs to perform a new task. The job of fine-tuning is not to teach it language from scratch — language is already there. The job is to nudge a small task-specific overlay into place. So why not train *just* that overlay and leave the rest frozen?

The empirical evidence for this is striking. The Houlsby et al. paper that introduced adapters (2019) showed that fine-tuning only **3.6% of BERT's parameters** for a target task reached within **0.4% of the performance** of full fine-tuning on the GLUE benchmark. Nearly all the task-specific information that fine-tuning would learn fits in a tiny fraction of the model's capacity. The remaining 96.4% of the parameters can stay frozen with almost no measurable loss.

```
PEFT in one picture:

  ┌─────────────────────────────────────────────┐
  │  Pretrained Model (96–99% of parameters)    │  ❄️ FROZEN
  │   - language understanding                  │
  │   - factual knowledge                       │
  │   - reasoning patterns                      │
  └─────────────────────────────────────────────┘
                       +
  ┌─────────────────────────────────────────────┐
  │  Task-Specific Overlay (1–4% of parameters) │  🔥 TRAINABLE
  │   - learns the new behaviour                │
  └─────────────────────────────────────────────┘
                       │
                       ▼
                 Fine-Tuned Model
```

The remaining question is *how to structure that small trainable overlay*. The next three subsections walk through the three answers the field has converged on: adapters, LoRA, and QLoRA.

### 2d. Adapters — Trainable Bottleneck Modules

**Adapters** were the first major PEFT approach, introduced in Houlsby et al.'s 2019 paper. The idea is structural: insert small trainable modules — **adapters** — at specific points inside each transformer block, and freeze everything else.

Each adapter is a tiny feedforward network with a **bottleneck architecture**: it first projects the hidden state *down* to a very small dimension, applies a nonlinearity, then projects it *back up* to the original dimension. A residual connection adds the original hidden state back at the end, so a freshly initialised adapter does almost nothing — it passes the input through nearly unchanged, and only diverges from the identity as training fills in its weights.

$$\text{Adapter}(h) = h + W_{\text{up}} \cdot \sigma(W_{\text{down}} \cdot h)$$

| Symbol | Meaning | Shape |
|--------|---------|-------|
| $h$ | Hidden state entering the adapter | $d$ |
| $W_{\text{down}}$ | Down-projection weight matrix | $m \times d$ with $m \ll d$ |
| $\sigma$ | Nonlinearity (typically GELU or ReLU) | — |
| $W_{\text{up}}$ | Up-projection weight matrix | $d \times m$ |
| $m$ | Bottleneck dimension (e.g., 64 when $d = 768$) | — |

The bottleneck is the entire reason this works. Forcing the adapter to compress the hidden state into $m$ dimensions before re-expanding it means the only thing it can learn is a *low-capacity, task-relevant* transformation. There simply are not enough parameters in $W_{\text{down}}$ and $W_{\text{up}}$ to memorise the training data — so the adapter is forced into learning a useful, compressed signal.

The Houlsby architecture places one adapter after the multi-head attention block and another after the feed-forward network, in every transformer block:

```
A single transformer block with adapters:

  Input
    │
    ▼
  [Multi-Head Attention]   ❄️ FROZEN
    │
    ▼
  [Add & LayerNorm]        ❄️ FROZEN
    │
    ▼
  [Adapter Module]         🔥 TRAINABLE — bottleneck (d → m → d) + residual
    │
    ▼
  [Feed-Forward Network]   ❄️ FROZEN
    │
    ▼
  [Add & LayerNorm]        ❄️ FROZEN
    │
    ▼
  [Adapter Module]         🔥 TRAINABLE
    │
    ▼
  Output
```

Because every transformer block contains the same two adapter slots, an "adapter" for the whole model is really a collection of small modules sprinkled across all the blocks. A 12-block transformer therefore has 24 adapter modules, all trained jointly.

One elegant consequence is **composability**. Because adapters are small and modular, you can train one set on (say) medical-text classification and another set on (say) French named-entity recognition, and you can swap them in and out of the same frozen base model at will. The community resource **AdapterHub** (https://adapterhub.ml) hosts thousands of pre-trained adapter modules that anyone can download and plug into a compatible base. The original adapters work was BERT-focused; later papers such as **LLaMA-Adapter** ported the same idea to decoder-only generation models like LLaMA.

Adapters are a great PEFT starting point, but they have one structural drawback: at inference time, the adapter modules sit inline in the forward pass and add their own computation. The next technique — LoRA — is mathematically more clever and avoids that overhead entirely.

### 2e. LoRA — Approximating the Update with Two Thin Matrices

**Low-Rank Adaptation (LoRA)**, introduced by Edward Hu et al. in 2021, is the technique that made fine-tuning genuinely accessible. It is now the dominant PEFT method in practice, and understanding its mathematics will make every subsequent concept in this chapter click.

LoRA starts from a different question than adapters. Rather than asking "where should I insert a new module?", LoRA asks: "What if I directly model the *change* that fine-tuning would make to each existing weight matrix?" If we understood the structure of that change, perhaps we could represent it far more compactly than the change itself.

The justification comes from a 2020 paper titled *"Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning"* (Aghajanyan, Zettlemoyer, Gupta). The paper shows that when you fine-tune a large model on a specific task, the update $\Delta W$ to each weight matrix does not fill the full high-dimensional space the matrix lives in. The meaningful changes are concentrated in a very small subspace. A weight matrix with $d^2 \approx 150$ million entries might only need to change in an *8-dimensional* subspace to adapt to a new task. The rest of the change is effectively noise or redundancy.

LoRA exploits this by representing the weight update as the product of two thin matrices:

$$W' = W + \Delta W = W + \frac{\alpha}{r} \cdot A \cdot B$$

| Symbol | Meaning | Typical Value |
|--------|---------|---------------|
| $W \in \mathbb{R}^{d \times d}$ | Original frozen weight matrix | $12{,}288 \times 12{,}288$ in GPT-3 |
| $A \in \mathbb{R}^{d \times r}$ | Down-projection, **trainable** | $12{,}288 \times 8$ |
| $B \in \mathbb{R}^{r \times d}$ | Up-projection, **trainable, initialised to zero** | $8 \times 12{,}288$ |
| $r$ | Rank of the decomposition — controls capacity | 4 to 64 |
| $\alpha$ | Scaling factor for the magnitude of the update | typically $2r$ |

Instead of directly updating $W$, we learn two thin matrices $A$ and $B$ whose product $AB$ approximates the weight update. The original $W$ is never touched. During the forward pass, the output of the layer is computed as:

$$\text{output} = Wx + \frac{\alpha}{r} \cdot ABx = \left(W + \frac{\alpha}{r} AB\right)x$$

Two subtle design choices matter:

**Why $B$ is initialised to zero.** If $B$ starts at all zeros, then $AB = 0$ at the very first training step, so $\Delta W = 0$ and the LoRA-augmented model behaves exactly like the unmodified base model. Training then gradually grows $B$ away from zero in whatever direction the gradient points, filling in the task-specific update. This guarantees a clean, stable starting point — a random initialisation of both $A$ and $B$ would inject random noise into the pretrained weights from step one.

**Why the $\alpha / r$ scaling.** When you change the rank $r$, you change the capacity of $A$ and $B$. The $\alpha / r$ scaling keeps the *magnitude* of the effective update stable across rank choices: doubling $r$ doubles the available capacity but also halves the scaling, so the contribution to $W'$ stays in roughly the same range. The conventional rule of thumb is $\alpha = 2r$, but the two are tunable separately.

```
LoRA inside a single linear layer:

         x  (input vector, shape d)
         │
    ┌────┴──────────────────────────────┐
    │                                   │
    ▼                                   ▼
  [W]  ❄️ FROZEN                     [A]  🔥 trainable  (d × r)
    │   (d × d weight matrix)           │
    │                                   ▼
    │                                 [B]  🔥 trainable  (r × d, init = 0)
    │                                   │
    │                   (A·B = low-rank update ΔW, shape d × d)
    │                                   │
    └────────────────► (+) ◄────────────┘
                        │
                        ▼
                output = Wx + (α/r)·ABx
```

**Which layers does LoRA target?** A transformer block has many weight matrices: the query, key, value, and output projections inside multi-head attention (`q_proj`, `k_proj`, `v_proj`, `o_proj`) and the gate, up, and down projections inside the feed-forward network (`gate_proj`, `up_proj`, `down_proj`). Applying LoRA to *all* of them gives the highest performance. Applying it only to `q_proj` and `v_proj` (the most commonly tuned attention projections) is cheaper and often good enough for many tasks. We will see the practical configuration in Section 3.

A second practical advantage of LoRA over adapters: once training is complete, the product $AB$ can be folded directly into $W$ (set $W \leftarrow W + (\alpha/r) AB$), producing a single weight matrix indistinguishable in shape from the original. This means **LoRA adds zero inference-time overhead** — unlike adapters, which sit in the forward pass forever.

### 2f. LoRA Dry-Run and Parameter Count Comparison

The parameter savings from LoRA are dramatic when you look at concrete numbers. The book uses a clean toy example to build intuition: a $10 \times 10$ weight matrix has $100$ entries. A rank-1 decomposition of it uses two thin matrices of shapes $10 \times 1$ and $1 \times 10$ — only $20$ entries total. A rank-2 decomposition uses $10 \times 2 + 2 \times 10 = 40$ entries. Even at rank 2, you have cut the parameter count by more than half.

Scale this up to GPT-3 and the numbers become extraordinary:

| Method | Parameters per weight matrix | Compression |
|--------|------------------------------|-------------|
| Full fine-tuning | $12{,}288 \times 12{,}288 = 150{,}994{,}944$ | $1\times$ |
| LoRA rank 8 | $12{,}288 \times 8 + 8 \times 12{,}288 = 196{,}608$ | **$768\times$ fewer** |

Multiply that $768\times$ saving across every weight matrix in all 96 transformer blocks of GPT-3 and you have shrunk the trainable parameter count from 175 billion to a few hundred million. The optimizer state and gradient memory shrink proportionally — precisely the wall we were trying to climb in 2b.

**Dry-run with tiny numbers ($d = 4$, $r = 1$).** Let us watch the decomposition arithmetic step by step:

```
Original frozen weight matrix W (shape 4×4):
  W = [[2, 0, 1, 0],
       [0, 3, 0, 1],
       [1, 0, 2, 0],
       [0, 1, 0, 3]]

LoRA matrices (trainable; both shown populated for illustration —
B would actually start at all zeros at the beginning of training):
  A = [[0.5],      ← shape 4×1  (d × r)
       [0.3],
       [0.7],
       [0.1]]

  B = [[0.2, 0.4, 0.1, 0.3]]   ← shape 1×4  (r × d)

Step 1 — Compute ΔW = A × B
  Each row of A multiplied by B gives one row of ΔW:
  Row 0:  0.5 × [0.2, 0.4, 0.1, 0.3] = [0.10, 0.20, 0.05, 0.15]
  Row 1:  0.3 × [0.2, 0.4, 0.1, 0.3] = [0.06, 0.12, 0.03, 0.09]
  Row 2:  0.7 × [0.2, 0.4, 0.1, 0.3] = [0.14, 0.28, 0.07, 0.21]
  Row 3:  0.1 × [0.2, 0.4, 0.1, 0.3] = [0.02, 0.04, 0.01, 0.03]

  ΔW = [[0.10, 0.20, 0.05, 0.15],
         [0.06, 0.12, 0.03, 0.09],
         [0.14, 0.28, 0.07, 0.21],
         [0.02, 0.04, 0.01, 0.03]]

Step 2 — Compute effective weight W' = W + ΔW  (using α/r = 1 for simplicity)
  W' = [[2.10, 0.20, 1.05, 0.15],
         [0.06, 3.12, 0.03, 1.09],
         [1.14, 0.28, 2.07, 0.21],
         [0.02, 1.04, 0.01, 3.03]]

Parameter count comparison at this toy scale:
  Full fine-tuning:  4 × 4   = 16 parameters to update
  LoRA rank-1:       4 + 4   =  8 parameters to update    (50% saving)
  At d = 12,288, r = 8:  196,608 vs 150,994,944           (768× saving)
```

Notice the structure of $\Delta W$ in the dry-run: every row is a *scaled copy of the single row of $B$*, weighted by the corresponding entry of $A$. This is what *rank 1* means in concrete terms — a single direction of update, broadcast across the matrix. At rank 8, you would have eight such directions added together. Eight directions is empirically enough to capture most of what task-specific fine-tuning needs to do.

### 2g. Quantization — Compressing the Base Model's Weights

LoRA is brilliant at one thing: shrinking the count of *trainable* parameters. But it does not shrink the *base model itself*. A 7-billion-parameter model stored in float32 still occupies $7\text{B} \times 4 = 28$ GB of VRAM just to be loaded into memory, before any training begins. Consumer GPUs (RTX 3090, 4090) top out at 24 GB; entry-level training cards sit at 16 GB. We have closed the gradient-and-optimizer-state gap but not the gap of loading the model in the first place.

**Quantization** is the technique that closes that remaining gap. The core idea is to store the weights at lower numerical precision, so they take fewer bytes. Floating-point numbers are stored as three fields — a sign bit, exponent bits, and mantissa bits — and dropping bits from the mantissa or exponent shrinks the representation at the cost of precision:

```
Floating-point bit layouts:

  float32 (32 bits, ~7 decimal digits of precision):
    ┌─┬────────┬───────────────────────┐
    │S│EEEEEEEE│MMMMMMMMMMMMMMMMMMMMMMM│
    └─┴────────┴───────────────────────┘
     1    8               23

  float16 (16 bits, ~3–4 decimal digits of precision):
    ┌─┬─────┬──────────┐
    │S│EEEEE│MMMMMMMMMM│
    └─┴─────┴──────────┘
     1   5       10

  NF4 (4 bits, only 16 possible values total — distribution-aware):
    ┌────┐
    │XXXX│
    └────┘
```

The book illustrates the precision tradeoff vividly with the number $\pi$:

```
π represented at different precisions:

  float32:  3.1415927    ← ~7 digits of precision
  float16:  3.141        ← ~3–4 digits of precision
  4-bit:    one of 16 levels — only the rough magnitude survives
```

For most numerical computing applications, dropping from float32 to 4 bits would be catastrophic. Why does it not destroy the model? Because LLM weights do not encode information in their seventh decimal digit. The model's intelligence lives in the *relative patterns* between weights — which weight is bigger than which other, and by roughly how much. If we can faithfully preserve the *distribution* of weight magnitudes using fewer bits, the model will behave nearly identically while occupying a fraction of the memory.

The simplest quantization scheme is **linear (uniform) quantization**: map the range $[x_{\min}, x_{\max}]$ to $2^b$ evenly spaced integer levels.

$$q = \text{round}\!\left(\frac{x - x_{\min}}{x_{\max} - x_{\min}} \times (2^b - 1)\right)$$

| Symbol | Meaning |
|--------|---------|
| $x$ | Original floating-point weight value |
| $x_{\min}, x_{\max}$ | Minimum and maximum of the weight block being quantized |
| $b$ | Number of bits ($b = 4$ gives $2^4 = 16$ levels) |
| $q$ | Quantized integer code |

**Dry-run — quantizing four weights to 2 bits:**

```
Original weights:  [-1.2,  0.3,  0.7,  2.1]
  x_min = -1.2,   x_max = 2.1,   range = 3.3
  2 bits → 2² = 4 levels: {0, 1, 2, 3}

  Formula:  q = round((x − (−1.2)) / 3.3 × 3)

  x = −1.2:  round(( 0.0) / 3.3 × 3) = round(0.000) = 0
  x =  0.3:  round(( 1.5) / 3.3 × 3) = round(1.364) = 1
  x =  0.7:  round(( 1.9) / 3.3 × 3) = round(1.727) = 2
  x =  2.1:  round(( 3.3) / 3.3 × 3) = round(3.000) = 3

  Quantized codes: [0, 1, 2, 3]   ← each stored as 2 bits

Reconstruction (dequantization):  x̂ = q/3 × 3.3 + (−1.2)
  q = 0 →  −1.200   (exact match)
  q = 1 →  −0.100   (original was 0.3 → error = 0.4)
  q = 2 →   1.000   (original was 0.7 → error = 0.3)
  q = 3 →   2.100   (exact match)

The two extreme values reconstruct exactly; interior values suffer some
quantization error, but the overall distribution is preserved.
```

Linear quantization works in the textbook case where the input distribution is well-behaved. But real LLM weights are not well-behaved, and the next subsection shows why this scheme fails on them — and what QLoRA does to fix it.

### 2h. QLoRA — Blockwise NF4 Quantization Combined with LoRA

Naive linear quantization breaks down for real LLM weights in two ways. The first failure is **outliers**.

Imagine a weight matrix where 99% of the weights cluster between $-0.5$ and $+0.5$, but one weight is $+50.0$. The quantization range $[x_{\min}, x_{\max}]$ now spans $[-0.5, 50.0]$. With only 16 levels available, almost all of those levels are spread across the empty region between $0.5$ and $50.0$, while *all* of the common near-zero weights get crushed into the first two or three levels. It is like designing a single ruler to measure both a pencil and a flagpole — accurate for the flagpole, useless for the pencil.

```
Naive linear quantization with one outlier (range -0.5 to +50.0):

  Real weight distribution:
    -0.5 ─────────────────────────────────────── +50.0
     ●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●     ●     ← almost everything is here,
                                                         outlier is far right

  Available 4-bit levels (16 of them, equally spaced):
     ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲   ▲   ▲   ▲   ▲   ▲

  Result: nearly all weights round into the leftmost 1–2 levels.
          Precision in the near-zero region is destroyed.
```

The second failure is the **density mismatch**. Even without outliers, LLM weights are not uniformly distributed across their range — they follow a roughly Normal (bell-curve) distribution centred near zero. Uniform quantization places equal numbers of levels in dense regions (near zero) and in sparse regions (the tails), which is exactly the wrong allocation.

**QLoRA**, introduced by Tim Dettmers and colleagues in 2023, fixes both problems and combines the result with LoRA. It has three key components.

**Component 1 — Blockwise quantization.** Instead of computing $x_{\min}$ and $x_{\max}$ over the entire weight tensor, split the tensor into small independent blocks (typically 64 consecutive weights) and compute separate quantization constants per block. Each block now uses its 16 levels for its *own* local distribution, so a far-away outlier in some other block cannot pollute the precision here.

```
Blockwise quantization:

  Full weight tensor (with one outlier far to the right):
    [-0.3  +0.1  +0.4  -0.2  …  -0.5  +0.3  -0.1  +50.0]
                           │
              split into blocks of 64 weights
                           │
    ┌───────────────┐  ┌───────────────┐  ┌──────────────────────┐
    │ Block 1       │  │ Block 2       │  │ Block N              │
    │ range: ±0.5   │  │ range: ±0.4   │  │ range: ±50.0         │
    │ fine precision│  │ fine precision│  │ coarse (outlier only)│
    └───────────────┘  └───────────────┘  └──────────────────────┘
```

**Component 2 — NormalFloat 4-bit (NF4) quantization.** Uniform 16-level quantization wastes bins on rare extreme values. NF4 instead places its 16 levels with **distribution-aware spacing**: many levels packed near zero (where most weights are) and few levels spread into the tails (where weights are rare). The exact level positions are derived analytically from the assumption that weights follow a standard normal distribution. This squeezes the maximum information out of those 4 bits because every level is placed where it has the most weights to represent.

```
NF4 level placement vs uniform 4-bit:

  Uniform 4-bit (16 equally spaced levels):
    ▲      ▲      ▲      ▲      ▲      ▲      ▲      ▲
    -1                   0                          +1

  NF4 (16 levels, packed where the weight density is high):
    ▲         ▲      ▲   ▲  ▲ ▲▲▲▲▲ ▲  ▲   ▲      ▲         ▲
    -1                   0                          +1
         ↑                  ↑                  ↑
       few in tail    many near zero        few in tail
```

**Component 3 — LoRA on top of the quantized base.** The 4-bit-quantized base model is loaded as a *read-only* frozen object. On top of it, we attach the usual LoRA adapter matrices $A$ and $B$ in float16, exactly as in 2e. During the forward pass, the 4-bit base weights are dequantized to float16 on-the-fly for each layer's matrix multiply; gradients flow only through the LoRA matrices.

```
QLoRA memory architecture:

  ┌──────────────────────────────────────────────┐
  │  Base model weights (4-bit NF4, blockwise)   │  ❄️ FROZEN, compressed
  │  7B params × 0.5 bytes ≈ 3.5 GB              │
  │  (vs 28 GB at float32 — an 8× reduction)     │
  └──────────────────────────────────────────────┘
                       │
        [dequantize on-the-fly to float16 for each forward pass]
                       │
                       ▼
  ┌──────────────────────────────────────────────┐
  │  LoRA adapters (A and B, float16)            │  🔥 TRAINABLE
  │  ~10–50 MB for a 7B model with rank 16       │
  └──────────────────────────────────────────────┘
                       │
        [gradients flow only through the LoRA matrices]
                       │
                       ▼
              Optimizer updates only A and B
```

The practical impact is transformative. Fine-tuning a 7B model with full fine-tuning needs roughly 112 GB of training state (parameters + gradients + Adam moments at float32) and is impossible on any consumer GPU. With QLoRA, the entire fine-tuning workflow fits comfortably in **6–8 GB** of VRAM — well within the budget of a single RTX 3090 or even an RTX 4060. This single shift — from "rent a multi-GPU cluster" to "use the laptop you already own" — is what democratised LLM fine-tuning outside the largest AI labs.

With the theory of LoRA, quantization, and QLoRA in place, we are ready to actually fine-tune a model. Section 3 walks through a complete instruction-tuning run with TinyLlama, including every line of the `bitsandbytes` config, the LoRA config, the training arguments, and the `SFTTrainer` itself.

---

## 3. Instruction Tuning with QLoRA — Practical Walkthrough

Theory in hand, this section turns the QLoRA stack into a working instruction-tuning run on a real model. The book — and these notes — use **TinyLlama-1.1B** as the base. TinyLlama is small enough to fine-tune end-to-end on a single consumer GPU in well under an hour, but it shares the LLaMA architecture, so every line of code we write here applies identically to 7B, 13B, or 70B LLaMA-family models. The only adjustments at larger scale are `per_device_train_batch_size` and `gradient_accumulation_steps`, which we will meet shortly.

### 3a. The Walkthrough Pipeline — What We're Building

Before we descend into individual config knobs, it helps to see the whole pipeline laid out. Instruction tuning a base model with QLoRA is a seven-step recipe, and the rest of Section 3 is one subsection per step. Each subsection adds one layer of capability to a model that starts out unable to follow instructions and ends up answering them coherently.

```
                  The QLoRA instruction-tuning pipeline:

  [1] Load UltraChat dataset                              (3b)
          │   (3,000 multi-turn conversations from HuggingFaceH4/ultrachat_200k)
          ▼
  [2] Apply TinyLlama chat template                       (3b)
          │   (wrap each turn in <|user|>, </s>, <|assistant|>)
          ▼
  [3] Load TinyLlama base in 4-bit NF4                    (3c)
          │   (BitsAndBytesConfig — Q in QLoRA)
          ▼
  [4] Attach trainable LoRA adapters                      (3d)
          │   (PEFT LoraConfig — the LoRA in QLoRA)
          ▼
  [5] Configure training hyperparameters                  (3e)
          │   (TrainingArguments + paged AdamW optimizer)
          ▼
  [6] Train with SFTTrainer                               (3f)
          │   (loss masking, batching, gradient updates on A and B only)
          ▼
  [7] Merge adapters and run inference                    (3g)
          │   (W ← W + (α/r)·AB; deploy as a normal model)
          ▼
        Instruction-tuned TinyLlama
```

Each box is one design decision plus a few lines of code. The next seven subsections go through them in order.

### 3b. Dataset Preparation and Chat Templates

Think of a chat template like the stage directions in a play script. Without them, the actors would have no idea who is speaking which line — the script would read like an undifferentiated wall of text. Stage directions ("ALICE:", "BOB:") make every role unambiguous. A **chat template** does the same thing for an LLM: it inserts special tokens that explicitly mark which span of text is the user's message and which span is the assistant's response. Without these markers, the model would just see one long sequence and have no idea where it is supposed to start generating.

TinyLlama's chat template uses three special tokens:

| Token | Role |
|-------|------|
| `<|user|>` | Beginning of a user message |
| `<|assistant|>` | Beginning of an assistant response |
| `</s>` | End-of-sequence — closes each turn |

A formatted single-turn conversation looks like this:

```
<|user|>
What is 1 + 1?</s>
<|assistant|>
The answer to 1 + 1 is 2!</s>
```

The training data comes from **UltraChat** (Ning Ding et al., 2023, *"Enhancing chat language models by scaling high-quality instructional conversations"*), specifically the filtered subset hosted as `HuggingFaceH4/ultrachat_200k`. The full dataset has roughly 200,000 multi-turn conversations; the book selects 3,000 shuffled examples to keep training time manageable. Increase that number for better quality at the cost of training time.

```python
from transformers import AutoTokenizer
from datasets import load_dataset

# Load TinyLlama's chat tokenizer purely to borrow its chat template
template_tokenizer = AutoTokenizer.from_pretrained(
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
)

def format_prompt(example):
    """Wrap a multi-turn conversation in TinyLlama's chat template."""
    chat = example["messages"]
    prompt = template_tokenizer.apply_chat_template(chat, tokenize=False)
    return {"text": prompt}

dataset = (
    load_dataset("HuggingFaceH4/ultrachat_200k", split="test_sft")
    .shuffle(seed=42)
    .select(range(3_000))
)
dataset = dataset.map(format_prompt)
```

Notice a subtle point: we load the *chat* version of TinyLlama only to access its tokenizer (for the template), but we will fine-tune the *base* (non-chat) version. The base model has never seen the tokens `<|user|>`, `<|assistant|>`, or `</s>` in this structural role before — through SFT, we are teaching it to recognise these markers and respond appropriately when it sees them.

After mapping, a real training example from UltraChat looks like:

```
<|user|>
Given the text: Knock, knock. Who's there? Hike.
Can you continue the joke based on the given text material "Knock, knock.
Who's there? Hike"?</s>
<|assistant|>
Sure! Knock, knock. Who's there? Hike. Hike who? Hike up your pants, it's cold
outside!</s>
<|user|>
Can you tell me another knock-knock joke based on the same text material
"Knock, knock. Who's there? Hike"?</s>
<|assistant|>
Of course! Knock, knock. Who's there? Hike. Hike who? Hike your way over here
and let's go for a walk!</s>
```

Two structural things to notice. First, this is a *multi-turn* conversation — the template can repeat user/assistant pairs as many times as needed. Second, every turn ends with `</s>`, including the assistant's; during training, the model learns to predict `</s>` when its response is done, which is how it knows to stop generating at inference time.

The next subsection turns this formatted text into something a model can actually train on.

### 3c. Model Quantization — The BitsAndBytes Config

Think of quantization like shipping a piece of disassembled furniture. The flat-packed form is 8× smaller and fits in your car (4-bit storage on the GPU), but you cannot use it as furniture until you reassemble each piece at the destination (dequantize to float16 for each matrix multiply). The disassembled and assembled forms hold the same information; we only ever materialise the assembled form briefly, for as long as we need it.

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                # ① Store weights as 4-bit integers
    bnb_4bit_quant_type="nf4",        # ② Use NormalFloat-4 (distribution-aware)
    bnb_4bit_compute_dtype="float16", # ③ Dequantize to float16 for computation
    bnb_4bit_use_double_quant=True,   # ④ Quantize the quantization constants too
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
)
model.config.use_cache = False        # ⑤ Disable KV cache (it's for inference)
model.config.pretraining_tp = 1       # ⑥ No tensor parallelism on a single GPU

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = "<PAD>"         # TinyLlama has no pad token by default
tokenizer.padding_side = "left"       # Left-pad so generation continues from the right edge
```

Now the *why* behind each setting.

**① `load_in_4bit=True`.** Every weight matrix is stored as a 4-bit NF4 integer code on the GPU. The memory savings on TinyLlama are concrete:

| Precision | Bytes per param | TinyLlama-1.1B total |
|-----------|-----------------|----------------------|
| float32 | 4 bytes | $1.1\text{B} \times 4 = 4.4$ GB |
| float16 | 2 bytes | $1.1\text{B} \times 2 = 2.2$ GB |
| 4-bit NF4 | 0.5 bytes | $1.1\text{B} \times 0.5 = 0.55$ GB |
| 4-bit NF4 + double-quant | ~0.52 bytes | ~0.57 GB |

The book reports ~1 GB total VRAM use after loading the quantized model — slightly above the 0.55 GB raw weight estimate because of embedding tables, layer norm parameters (kept at float32 for stability), and bookkeeping overhead.

**② `bnb_4bit_quant_type="nf4"`.** Picks **NormalFloat-4** from 2h: 16 quantization levels positioned with distribution-aware spacing (dense near zero, sparse in the tails) rather than uniform spacing. The only other realistic choice is `"fp4"`, a standard 4-bit float; NF4 is empirically better for normally-distributed LLM weights.

**③ `bnb_4bit_compute_dtype="float16"`.** Modern GPU tensor cores cannot do matrix multiplications in 4-bit directly — they need at least float16. So just before each matrix multiply in the forward pass, `bitsandbytes` dequantizes the relevant block of weights to float16, runs the multiplication, and discards the float16 version. The 4-bit storage stays untouched. This is the "shipping/reassembly" cycle from the analogy.

**④ `bnb_4bit_use_double_quant=True`.** This is **double quantization**, an extra trick from the QLoRA paper that squeezes out the last bit of overhead. Recall that blockwise quantization stores one floating-point *scale factor* per block of 64 weights. Naively those scale factors are float32 (4 bytes each), and the total storage works out to:

```
Plain 4-bit blockwise quantization (block size = 64):
  64 weights × 4 bits   =  32 bytes (the quantized weights)
   1 scale × 32 bits    =   4 bytes (the float32 scale factor)
                          ────────
  Total                  =  36 bytes per 64 weights
                          = 36 × 8 / 64
                          = 4.5 bits per weight  ← not 4!
```

Double quantization re-quantizes those scale factors themselves into 8-bit integers (with one small float32 scale per *meta-block* of 256 inner scales). The new accounting:

```
4-bit + double quantization (block size = 64):
  64 weights × 4 bits           =  32 bytes
   1 quantized scale × 8 bits   =   1 byte
   (shared meta-scale, amortised across 256 blocks ≈ 0.016 bytes)
                                  ────────
  Total                          ≈ 33 bytes per 64 weights
                                  ≈ 4.13 bits per weight
```

The saving is about 0.37 bits per parameter. Negligible per weight, but on a 7B model it adds up to roughly 325 MB — enough to be worth turning on by default.

**⑤ `model.config.use_cache = False`.** The KV-cache is a generation-time optimisation (cache past keys and values so each new token does not recompute them). It is irrelevant during training and consumes memory; switch it off.

**⑥ `model.config.pretraining_tp = 1`.** Tensor-parallelism flag for splitting computations across multiple GPUs. We are on a single GPU, so set it to 1.

The two final tokenizer lines deserve a brief note. TinyLlama's tokenizer ships without a pad token, so we add one (`<PAD>`); we set `padding_side="left"` because for causal LMs we want the real content sitting at the right edge of the context — generation always continues from the rightmost position.

### 3d. LoRA Configuration — Every Parameter Explained

Think of LoRA configuration like a film director planning targeted reshoots of a finished movie. You decide three things: *which scenes* to reshoot (`target_modules`), *how much creative latitude* the rewrite team has (`r`, the rank), and *how strongly* the reshoots should override the original takes (`lora_alpha`, the scaling factor).

```python
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model

peft_config = LoraConfig(
    lora_alpha=32,
    lora_dropout=0.1,
    r=64,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "k_proj", "gate_proj", "v_proj", "up_proj",
        "q_proj", "o_proj", "down_proj"
    ]
)

model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)
```

| Parameter | What it controls | This run's value |
|-----------|------------------|------------------|
| `r` | Rank of $A$ and $B$ — capacity of the update | 64 |
| `lora_alpha` | Scaling factor $\alpha$ in $\Delta W = (\alpha/r) AB$ | 32 |
| `lora_dropout` | Dropout on adapter activations during training | 0.1 |
| `bias` | Whether to also train bias terms ("none" / "lora_only" / "all") | "none" |
| `task_type` | Tells PEFT this is causal LM | "CAUSAL_LM" |
| `target_modules` | List of weight matrices to wrap with LoRA | All 7 LLaMA projections |

`r=64` is unusually high — for larger models, rank 8–16 is the norm. The book uses 64 here precisely because TinyLlama is so small that the absolute trainable-parameter count of a rank-64 LoRA stays modest. The effective scaling is $\alpha / r = 32 / 64 = 0.5$, which means the LoRA update is *halved* before being added to the base weights — a deliberately conservative setting. (The conventional $\alpha = 2r$ rule from 2e would have given $\alpha = 128$ and a scaling of 2; the book chose to be gentler.)

`target_modules` lists all seven trainable matrices inside each TinyLlama transformer block:

```
Attention projections (4):    q_proj   k_proj   v_proj   o_proj
Gated FFN projections (3):    gate_proj   up_proj   down_proj
```

Targeting all seven gives the highest fine-tuning quality. Targeting only a subset (e.g. just `q_proj` and `v_proj`) is faster but gives up some quality.

**Concrete LoRA parameter count for this run.** TinyLlama has hidden dimension $d = 2048$, FFN intermediate dimension $d_{\text{ff}} = 5632$, and 22 transformer blocks. With $r = 64$:

```
Per transformer block:

  Attention LoRAs (4 matrices, each d × d shape, rank r):
    4 × (2048 × 64 + 64 × 2048)
    = 4 × 262,144
    = 1,048,576

  FFN gate_proj + up_proj (2 matrices, each d_ff × d shape, rank r):
    2 × (2048 × 64 + 64 × 5632)
    = 2 × (131,072 + 360,448)
    = 2 × 491,520
    = 983,040

  FFN down_proj (1 matrix, d × d_ff shape, rank r):
    5632 × 64 + 64 × 2048
    = 360,448 + 131,072
    = 491,520

  Block total:  1,048,576 + 983,040 + 491,520  =  2,523,136

Across all 22 blocks:  22 × 2,523,136  ≈  55.5 M trainable LoRA params

As a fraction of TinyLlama:  55.5 M / 1.1 B  ≈  5%
```

The 5% trainable-parameter ratio is a deliberate choice driven by the high rank — the empirical "1–4%" range from 2c assumes typical ranks of 8–16, not 64. For this small model the book trades some efficiency for stronger adaptation capacity.

`prepare_model_for_kbit_training(model)` is more than a no-op despite its bland name. It performs four pieces of setup that make a quantized model trainable in the first place:

1. Casts every **LayerNorm** to float32. Layer norms compute very small variances; in low precision those compute paths suffer from numerical instability.
2. Casts the **LM head** to float32 for the same reason.
3. Enables **gradient checkpointing** on the model.
4. Sets `requires_grad` correctly across all modules (freezing the quantized base weights, allowing inputs to propagate gradients to the LoRA matrices that have not yet been added).

`get_peft_model(model, peft_config)` then does the actual LoRA wrapping: it walks the model, finds every layer whose name matches a `target_modules` entry, and replaces it with a `LoraLayer` containing the original frozen $W$ plus newly initialised trainable $A$ (random) and $B$ (zero). The returned model is the full base model plus all the freshly attached LoRA modules, ready for training.

### 3e. Training Arguments — What They Actually Do

Think of `TrainingArguments` like the dial settings on a lab instrument. Each individual knob looks unassuming, but a wrong setting on any one of them can ruin the run.

```python
from transformers import TrainingArguments

training_arguments = TrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    optim="paged_adamw_32bit",
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    num_train_epochs=1,
    logging_steps=10,
    fp16=True,
    gradient_checkpointing=True
)
```

**`per_device_train_batch_size=2`.** Only two examples per forward pass, despite using small inputs. Why so tiny? Because each example is up to 512 tokens, and the activations for backprop at length 512 on a 1.1B model in fp16 already consume several gigabytes per example. Pushing the batch size higher is the fastest way to run out of VRAM.

**`gradient_accumulation_steps=4`.** This is the crucial trick that recovers a useful *effective* batch size without paying the memory cost. The mechanism:

```
Without accumulation:
  for batch in loader:           # batch size = 2
      loss = model(batch).loss
      loss.backward()
      optimizer.step()           # update after every 2 examples

With accumulation_steps = 4:
  for i, batch in enumerate(loader):     # batch size = 2
      loss = model(batch).loss / 4       # divide so summed grads average correctly
      loss.backward()                    # ACCUMULATE gradient
      if (i + 1) % 4 == 0:
          optimizer.step()               # update once every 4 micro-batches
          optimizer.zero_grad()

Effective batch size: 2 × 4 = 8 examples per update step
Peak memory:          still only 2 examples worth
```

The gradient signal is now averaged over 8 examples, which is more stable than over 2 alone, but the GPU only ever holds 2 examples worth of activations at a time. This is the workhorse memory-vs-compute trade that makes single-GPU fine-tuning viable.

**`optim="paged_adamw_32bit"`.** This is a special optimizer from the QLoRA paper. The "32bit" suffix means Adam's $m$ and $v$ moment buffers themselves are stored at full float32 precision (we do not quantize the optimizer state — only the base model weights). The "paged" prefix is what is interesting: during the optimizer step, Adam's buffers experience temporary memory spikes (it has to materialise several large intermediate tensors). Normally that spike could overshoot the GPU's memory limit and crash the run. Paged AdamW hooks into NVIDIA's unified memory: when the GPU is about to overflow, parts of the optimizer state are automatically paged out to CPU RAM, used, and paged back. Training continues without crashing.

**`learning_rate=2e-4`.** $2 \times 10^{-4}$, which is roughly 10× higher than the typical `2e-5` used for full BERT fine-tuning in Chapter 11. The reason is that LoRA only trains a tiny fraction of parameters, so we need a faster per-step learning rate to make any meaningful progress in a single epoch. The QLoRA paper reports that even higher learning rates work better for >33B models.

**`lr_scheduler_type="cosine"`.** Cosine annealing schedule. Starts at $\sim 0$, ramps linearly up to `learning_rate` during a brief warm-up phase, then decays following a cosine curve to near zero by the end of training. The slow decay at the end lets the model settle into a good local minimum without overshooting.

```
Cosine learning rate schedule (with brief warmup):

  learning rate
       ▲
   2e-4│         ╱╲                                ← peak after warmup
       │        ╱   ╲╲
       │      ╱        ╲╲
       │    ╱              ╲╲                      ← cosine decay
       │  ╱                    ╲╲___
       │ ╱                          ╲___
     0 └───────────────────────────────────►  training step
       0   warmup                        end
```

**`num_train_epochs=1`.** Only one pass through the 3,000 examples. The book justifies this directly: more epochs of instruction tuning on a small dataset tends to degrade performance through overfitting. The model starts memorising specific responses instead of learning the general behaviour.

**`logging_steps=10`.** Print the running loss every 10 update steps. With 3,000 examples, effective batch size 8, that is $3000/8 = 375$ total update steps, so logs print 37 times across the run.

**`fp16=True`.** Mixed-precision training. The forward and backward passes run in float16 (roughly $2\times$ faster on modern GPUs with tensor cores); the optimizer state stays in float32 to prevent numerical instability during weight updates. The framework handles all conversions automatically.

**`gradient_checkpointing=True`.** A memory-vs-compute trade. During the forward pass, intermediate activations are *not* stored. Instead, when the backward pass needs them, they are recomputed from saved checkpoints at layer boundaries. Training takes roughly 30% longer (because of the extra forward computation during backprop), but peak memory drops substantially — often the difference between fitting and not fitting.

### 3f. SFTTrainer and the Training Loop

With data, model, LoRA config, and training args all assembled, we are at the *mise en place* moment: everything is prepped, and we hand it off to the chef (`SFTTrainer`) to actually cook.

```python
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="text",   # which column of `dataset` to train on
    tokenizer=tokenizer,
    args=training_arguments,
    max_seq_length=512,           # truncate any conversation longer than this
    peft_config=peft_config,      # SFTTrainer can apply PEFT itself
)

trainer.train()

trainer.model.save_pretrained("TinyLlama-1.1B-qlora")
```

`SFTTrainer` from the `trl` library wraps the standard HuggingFace `Trainer` with everything specific to instruction tuning baked in. Conceptually, on every step it performs five things:

1. **Tokenization.** Reads the formatted text from `dataset["text"]`, calls the tokenizer, truncates to `max_seq_length=512`.
2. **Loss masking.** Sets the `labels` tensor so that the user-turn tokens are marked with `-100` (the PyTorch convention for "ignore in loss"). Only the assistant tokens contribute to the cross-entropy.
3. **Batching and padding.** Collates `per_device_train_batch_size=2` examples into a single batch, pads them to a shared length, builds the attention mask.
4. **Forward pass with QLoRA.** Runs the model; the base weights are dequantized on-the-fly per layer; the LoRA adapters $A$ and $B$ contribute their $\Delta W$ via the standard $Wx + (\alpha/r)ABx$ path.
5. **Backward + optimizer step.** Computes gradients (which only flow into the LoRA matrices and any other unfrozen parameters like layer norms); the paged AdamW optimizer applies the update.

`max_seq_length=512` is a hard truncation. TinyLlama's architectural maximum is 2048; you could push the limit higher at the cost of memory and per-step time.

`peft_config=peft_config` here is the same object we built in 3d. Passing it to `SFTTrainer` is a convenience — if you have already wrapped your model with `get_peft_model`, you can leave this out; if you have not, `SFTTrainer` will apply it for you.

When `trainer.train()` finishes, `save_pretrained` writes *only the LoRA adapter weights* to disk. For TinyLlama with rank-64 LoRA on all seven target modules, that checkpoint is ~50 MB. Compare that to saving a fully fine-tuned TinyLlama in fp16, which would be ~2.2 GB — about 40× larger. This is one of LoRA's biggest practical wins: you can ship many fine-tuned variants of the same base model by distributing only the tiny adapter files.

Wall-clock time on the free Tesla T4 in Google Colab (the book's reference hardware) is roughly an hour. On the RTX A6000 (94 GB VRAM, 48 GB compute) it drops to roughly 10–15 minutes for the same 3,000-conversation run.

### 3g. Merging LoRA Weights for Inference

Once a LoRA model is trained, you have two ways to use it. Think of it like applying a watercolour wash over a pencil sketch: while the paint is still wet, you can still scrape it back to reveal the pencil (option A — keep adapters separate). Once it dries and the painting is framed, the two layers are inseparable and the picture is a single finished work (option B — merge).

**Option A — Keep adapter separate.** Load the base model and the LoRA adapter as two distinct objects. At every targeted layer, compute $Wx + (\alpha/r) ABx$ as two matrix multiplies and add the results. There is a small per-layer overhead for the extra multiply, but you can hot-swap different adapters on top of the same base model without reloading the base. Useful for serving multiple specialised models from one shared base.

**Option B — Merge.** Fold the LoRA contribution into the base weights: $W' = W + (\alpha/r) AB$, replace each $W$ with $W'$, and throw away $A$ and $B$. The merged model is now a standard transformer with no PEFT code path — inference speed is identical to a model that was never fine-tuned with LoRA. This is what we do for deployment.

```python
from peft import AutoPeftModelForCausalLM
from transformers import pipeline

# IMPORTANT: reload in float16, NOT 4-bit, for a clean merge
model = AutoPeftModelForCausalLM.from_pretrained(
    "TinyLlama-1.1B-qlora",
    low_cpu_mem_usage=True,
    device_map="auto",
)

# Fuse A·B into W for every targeted layer, then discard the adapters
merged_model = model.merge_and_unload()
```

The book underlines a subtle but important point: **reload the model in 16-bit (not 4-bit) before merging**. Why? Because if $W$ is sitting in 4-bit storage at the moment of the merge, then $W + (\alpha/r) AB$ must be rounded back to the nearest 4-bit quantization grid point per block. Every weight you merge introduces a fresh rounding error against that grid. Done across millions of weights, those errors accumulate and the merged model degrades measurably. Merging into float16 is essentially lossless, and you can always re-quantize the merged model afterwards if you need to deploy in 4-bit.

What `merge_and_unload()` does mechanically, layer by layer:

```
For each LoRA-wrapped layer:
    compute  ΔW  ←  (α/r) · A · B          # shape d × d
    update   W   ←  W + ΔW                  # the original matrix is overwritten
    delete   A, B, scaling factor           # adapter object is unloaded

After: the model is a plain transformer with W' = W + ΔW everywhere.
```

For inference, we must use the *same* chat template the model was trained with — otherwise the model has no idea it is expected to behave like an assistant.

```python
prompt = """<|user|>
Tell me something about Large Language Models.</s>
<|assistant|>
"""

pipe = pipeline(task="text-generation", model=merged_model, tokenizer=tokenizer)
print(pipe(prompt, max_new_tokens=200)[0]["generated_text"])
```

The book shows the resulting output:

```
Large Language Models (LLMs) are artificial intelligence (AI) models that
learn language and understand what it means to say things in a particular
language. They are trained on huge amounts of text…
```

Compare that to what the *unfine-tuned* base TinyLlama would have done with the same prompt: it would have continued the pattern of the formatted text — possibly generating more `<|user|>` blocks, or wandering into unrelated text — exactly the pattern-completion failure mode we diagnosed back in 1c. The instruction tuning has worked: the model now stops, recognises that `<|assistant|>` is its cue, generates a coherent answer, and emits `</s>` when done.

We have a working instruction-tuned model. The natural next question is: *is it any good?* That turns out to be a much harder question than evaluating a classifier, and Section 4 explores the surprisingly thin set of tools available for answering it.

---

## 4. Evaluating Generative Models

Evaluating generative models is genuinely difficult. Unlike classification tasks where there is one correct label, a generative model can answer "What is gravity?" in thousands of ways, and many of them are valid. No single metric captures all the dimensions of quality we care about: factual accuracy, fluency, helpfulness, honesty, appropriate length, and safety. This section surveys the full evaluation toolkit and is honest about each tool's limitations.

### 4a. Word-Level Metrics — Perplexity, BLEU, ROUGE, BERTScore

**Perplexity** measures how surprised the model is when it reads a piece of text. A model that assigns high probability to each word as it reads through a document has low perplexity — it is not surprised, because the text makes sense given what it has learned. A model that assigns low probability to the words it sees has high perplexity — it is consistently confused by the text.

$$\text{PPL}(W) = \exp\!\left(-\frac{1}{N}\sum_{i=1}^{N} \log P(w_i \mid w_1, \ldots, w_{i-1})\right)$$

| Symbol | Meaning |
|--------|---------|
| $W = (w_1, \ldots, w_N)$ | The sequence of $N$ tokens being evaluated |
| $P(w_i \mid w_1, \ldots, w_{i-1})$ | Model's predicted probability for token $w_i$ given all prior tokens |
| $\exp(\cdot)$ | Exponentiation to convert from log-space back to a natural scale |

This says: compute the average log-probability the model assigns to each token, negate it (so higher probability → smaller value → better), and exponentiate. Lower perplexity means the model was more confident and more correct. A perplexity of 10 means the model behaved on average as if choosing uniformly among 10 equally likely options at each step.

**Dry-run — perplexity on a 3-token sequence:**

```
Sentence: "The cat sat"
N = 3 tokens

Model assigns:
  P("The")               = 0.20
  P("cat"  | "The")      = 0.15
  P("sat"  | "The cat")  = 0.30

Step 1: Log probabilities
  log(0.20) = −1.609
  log(0.15) = −1.897
  log(0.30) = −1.204

Step 2: Average negative log-probability
  avg = −( (−1.609) + (−1.897) + (−1.204) ) / 3
      = −(−4.710) / 3
      = 1.570

Step 3: Exponentiate
  PPL = exp(1.570) ≈ 4.81

Interpretation: On average, the model behaves as if choosing among
~5 equally likely tokens at each step. Lower is better.
```

**BLEU (Bilingual Evaluation Understudy)** was developed for machine translation. It measures the overlap of n-grams (sequences of n consecutive words) between a generated text and one or more reference texts. BLEU works when there is a clearly correct answer (as in translation) but fails badly for open-ended generation, where paraphrases score near zero despite being valid responses.

**ROUGE (Recall-Oriented Understudy for Gisting Evaluation)** is the recall-focused counterpart to BLEU, widely used in summarisation evaluation. Where BLEU asks "how much of what was generated also appears in the reference?", ROUGE asks "how much of the reference appears in what was generated?"

**BERTScore** takes a more sophisticated approach. Rather than comparing exact word sequences, it embeds both the generated text and the reference using BERT and measures cosine similarity between their token representations. This allows BERTScore to recognise that "automobile" and "car" are equivalent, whereas BLEU would count them as completely different.

Despite their differences, all four metrics share a fundamental limitation expressed by **Goodhart's Law**: *when a measure becomes a target, it ceases to be a good measure.* A model can achieve high BLEU scores by copying chunks of the reference text verbatim — excellent BLEU, terrible model. A model with low perplexity might be confidently wrong. None of these metrics tell you whether the model actually solved the user's problem.

---

### 4b. Benchmarks — The Public Leaderboards

Benchmarks try to go beyond word-level metrics by testing the model on tasks that require real understanding. The most widely used benchmarks for generative models are:

| Benchmark | What It Tests | Format |
|-----------|--------------|--------|
| **MMLU** (Massive Multitask Language Understanding) | 57 academic subjects: law, medicine, history, physics, coding, and more | 4-choice multiple choice |
| **GLUE** | General language understanding: sentence similarity, entailment, grammaticality | Classification tasks |
| **TruthfulQA** | Whether the model answers truthfully on topics where humans commonly hold false beliefs | 817 questions |
| **GSM8k** | Grade-school math word problems requiring multi-step arithmetic reasoning | 8,500 open-answer problems |
| **HellaSwag** | Common-sense inference — which of four sentence completions is plausible? | 4-choice multiple choice |
| **HumanEval** | Code generation: write a Python function from its docstring | 164 programming problems |

The **Open LLM Leaderboard** aggregates several of these benchmarks and publicly ranks open-source models. A model that tops the leaderboard is generally considered the best open model at that time. However, there is a serious risk: **benchmark overfitting**. Since these benchmarks are public, model developers can — deliberately or accidentally — include benchmark test data in their training sets, or fine-tune specifically to perform well on benchmark tasks. A model can climb the leaderboard without actually becoming more useful in practice. This is Goodhart's Law applied at the benchmark level.

---

### 4c. Automated Evaluation — LLM-as-a-Judge

A more recent and increasingly popular approach is to use a powerful LLM as an automated evaluator. Rather than measuring n-gram overlap or benchmark accuracy, you ask GPT-4 or another frontier model to read a model's response and rate it on dimensions like helpfulness, accuracy, clarity, and safety.

The **LLM-as-a-judge** methodology comes in two forms. In the first, the judge scores a single response on a scale (e.g., 1–10) against stated criteria. In the second — **pairwise comparison** — the judge sees two responses to the same prompt and must declare which is better. Pairwise comparison tends to produce more reliable judgements because relative comparisons are easier to make consistently than absolute ratings.

```
Pairwise Evaluation Example:

  Prompt: "Explain gradient descent to a 10-year-old."

  Response A (Model X):
    "Gradient descent is an optimisation algorithm that minimises a loss
     function by iteratively adjusting parameters in the negative gradient
     direction until convergence..."

  Response B (Model Y):
    "Imagine you're blindfolded on a hilly landscape and you want to find
     the lowest valley. With each step, you feel which way the ground slopes
     downward and take a small step in that direction. Gradient descent
     works the same way!"

  Judge (GPT-4): "Response B is significantly better for the target audience.
                  It uses a concrete, age-appropriate analogy, while Response A
                  uses technical language inappropriate for a 10-year-old."

  → Model Y wins this comparison
```

LLM-as-a-judge scales beautifully and improves automatically as evaluator models improve. The main limitation is that LLM judges have their own biases: they tend to prefer longer responses, responses that match their own style, and responses that appear first in the prompt (positional bias).

---

### 4d. Human Evaluation and Chatbot Arena

Despite all automated approaches, the gold standard for evaluating generative models remains **human evaluation**. Humans can judge helpfulness, honesty, tone, creativity, and safety in ways that no automated metric currently replicates.

The most influential human evaluation platform is **Chatbot Arena** — a website where users submit any question to two anonymous chatbots simultaneously, receive both responses, and vote for the better one without knowing which models they are comparing. The anonymity eliminates branding bias. The variety of user-submitted questions covers a wider and more natural range than any curated benchmark.

Chatbot Arena uses the **Elo rating system**, originally designed for chess, to rank models from pairwise comparisons. In Elo, your rating increases when you beat a highly-rated opponent and barely moves when you beat a poorly-rated one. The system converges to a stable ranking that reflects true relative ability. With over 800,000 human votes collected, the statistical confidence of the Chatbot Arena rankings is very high.

The honest conclusion is that there is no perfect evaluation method. Word-level metrics are fast but shallow. Benchmarks are comprehensive but gameable. LLM-as-a-judge scales but carries biases. Human evaluation is the ground truth but is slow and expensive. For your specific use case, the most valuable evaluation you can run is: take the real prompts your users will send, run them through the model, and judge the outputs yourself.

---

## 5. Preference Tuning and RLHF

### 5a. Why Instruction Tuning Is Not Enough

After supervised fine-tuning, the model follows instructions. It will attempt to answer any question, complete any task, engage in any conversation. But following an instruction and giving a *good* answer are not the same thing. Consider two responses to the prompt "What are large language models?":

*Response A*: "They are large language models." *(Technically correct, completely useless.)*

*Response B*: "Large language models are neural networks trained on vast amounts of text data to understand and generate human language. They learn statistical patterns across billions of words, enabling them to answer questions, write code, summarise documents, and engage in open-ended conversation."

An instruction-tuned model could produce either response — both are valid next-token-prediction sequences. The model has no mechanism to prefer the informative answer over the tautological one.

**Preference tuning** is where we teach the model to distinguish between these two responses and reliably generate the better one. It does not add new knowledge — the model already knows how to write both kinds of response. It teaches the model to *prefer* certain qualities: depth, accuracy, appropriate length, helpfulness, honesty, and safety. The key insight is that preference tuning is not about correct versus incorrect — it is about better versus worse among valid responses.

### 5b. The Reward Model

The central tool in classical preference tuning is the **reward model** — a separate neural network trained to score the quality of a language model's output.

The reward model is built from a copy of the instruction-tuned model with one critical architectural change: the language modelling head — the final layer that outputs a probability distribution over the entire vocabulary — is replaced with a **regression head** that outputs a single scalar quality score.

```
Standard Instruction-Tuned LLM:

  [Prompt + Response tokens]
         │
         ▼
  [Transformer Layers ×N]
         │
         ▼
  [Language Model Head]      ← shape: (vocab_size,) e.g. 32,000 values
         │
         ▼
  Probability distribution over next token

─────────────────────────────────────────────────────────────

Reward Model (same transformer, different final layer):

  [Prompt + Response tokens]
         │
         ▼
  [Transformer Layers ×N]    ← identical to SFT model, weights initialised from SFT
         │
         ▼
  [Reward Head]              ← shape: (1,)  — single scalar output
         │
         ▼
  Quality score, e.g. −5.0 (poor) to +5.0 (excellent)
```

The reward model is trained on a **preference dataset**: a collection of triplets each containing a prompt, a chosen response, and a rejected response. The labels do not say "good" and "bad" absolutely — they say "chosen is better than rejected." Sometimes both responses are good; one is simply better.

The training objective uses the **Bradley-Terry model** for pairwise comparisons, which converts a score difference into a probability through the sigmoid function:

$$\mathcal{L}_{RM} = -\log \sigma\!\left(r_\theta(\text{prompt},\, y_w) - r_\theta(\text{prompt},\, y_l)\right)$$

| Symbol | Meaning |
|--------|---------|
| $r_\theta$ | Reward model with parameters $\theta$ |
| $y_w$ | The winning (chosen) response |
| $y_l$ | The losing (rejected) response |
| $\sigma(x) = 1/(1+e^{-x})$ | Sigmoid function, maps any real number to (0, 1) |

Minimising this loss pushes the model to assign higher scores to chosen responses and lower scores to rejected ones.

**Dry-run — reward model training loss:**

```
Example 1: Model clearly distinguishes good from bad
  Prompt:   "What is an LLM?"
  Chosen:   "A large language model is a neural network trained on vast text data..."
  Rejected: "I don't know."

  r(chosen)   = +5.2
  r(rejected) = −3.1

  diff = 5.2 − (−3.1) = 8.3
  σ(8.3)     = 1 / (1 + e^{−8.3}) ≈ 0.9997
  loss       = −log(0.9997) ≈ 0.0003   ← nearly zero; model got it right

Example 2: Model barely distinguishes them
  r(chosen)   = 0.1
  r(rejected) = 0.0

  diff = 0.1 − 0.0 = 0.1
  σ(0.1)     = 1 / (1 + e^{−0.1}) ≈ 0.525
  loss       = −log(0.525) ≈ 0.644   ← large; model cannot tell them apart

Training will push r(chosen) higher and r(rejected) lower
until the score gap is wide and the loss is small.
```

Once trained, the reward model acts as an automatic judge. Given any `[prompt, response]` pair, it outputs a quality score. This score is the training signal for the next stage.

---

### 5c. Proximal Policy Optimization (PPO)

With a reward model in hand, the instruction-tuned LLM can be further fine-tuned using **Proximal Policy Optimization (PPO)**, a reinforcement learning algorithm. PPO is how the original ChatGPT was trained, and it remains the "classical" RLHF algorithm.

PPO casts language generation as a reinforcement learning problem. The LLM is the **policy** — an agent that generates tokens (actions) in response to prompts (states). After the full response is generated, the reward model assigns a scalar reward. The policy is then updated to make high-reward generations more likely.

The "proximal" constraint prevents the policy from changing too drastically in a single update. Without it, the LLM might discover token sequences that fool the reward model into giving high scores while generating nonsense — a phenomenon called **reward hacking**. The PPO clipping objective limits this:

$$\mathcal{L}^{\text{CLIP}} = \mathbb{E}\!\left[\min\!\left(r_t(\theta)\,\hat{A}_t,\;\;\text{clip}\!\left(r_t(\theta),\,1-\epsilon,\,1+\epsilon\right)\hat{A}_t\right)\right]$$

| Symbol | Meaning |
|--------|---------|
| $r_t(\theta) = \pi_\theta(a_t \mid s_t)\,/\,\pi_{\theta_\text{old}}(a_t \mid s_t)$ | Probability ratio of new policy vs old policy |
| $\hat{A}_t$ | Advantage estimate — how much better this action was than expected |
| $\text{clip}(r_t,\,1-\epsilon,\,1+\epsilon)$ | Caps the ratio; $\epsilon = 0.2$ is typical |

The clip says: if the policy ratio exceeds $1+\epsilon$ (new policy is pushing much harder on this token than the old policy), stop benefiting from further increases. This keeps updates moderate and prevents wild divergence.

PPO requires three models in GPU memory simultaneously: the trainable policy (the LLM being updated), a frozen reference copy of the policy (to compute probability ratios), and the reward model. This three-model setup demands significant memory and engineering complexity, and training is sensitive to hyperparameters. These practical difficulties motivated the search for simpler alternatives — which led to DPO.

---

## 6. Direct Preference Optimization (DPO)

### 6a. The Core Insight — No Reward Model Needed

**Direct Preference Optimization (DPO)** is one of the most elegant ideas in recent LLM research, introduced by Rafailov et al. in 2023. It asks: do we actually need to train a separate reward model and then use reinforcement learning to optimise the LLM against it? Can we somehow do the whole thing directly?

The theoretical breakthrough is the realisation that the optimal language model policy *implicitly defines* the reward function. The reward that PPO is trying to maximise can be expressed analytically in terms of the log-probabilities of the LLM being trained and a frozen reference LLM. This means that instead of training a reward model and then a policy, we can directly optimise the LLM on the preference data — no reward model, no reinforcement learning required.

DPO is simpler, more stable, requires less memory, and achieves comparable or better results than PPO on most benchmarks. It has become the dominant approach for preference tuning in open-source pipelines.

### 6b. How DPO Works — The Four Players

Every DPO training step involves four components:

1. **The prompt** — the question or instruction
2. **The chosen response** — the preferred answer from the preference dataset
3. **The rejected response** — the less preferred answer
4. **The reference model** — a frozen copy of the instruction-tuned model, never updated

```
DPO Training Step:

  Prompt: "What are LLMs?"
  Chosen:   "Large language models are neural networks trained on vast text..."
  Rejected: "They are large."

           ┌──────────────────────────────────┐
           │   Reference Model (FROZEN)        │
           │   (copy of SFT model)             │
           └──────────────────────────────────┘
                          │
         ┌────────────────┴───────────────────┐
         ▼                                    ▼
  log P_ref(chosen | prompt)      log P_ref(rejected | prompt)
         │                                    │
         └────────────────┬───────────────────┘
                          │  (reference baseline)
           ┌──────────────────────────────────┐
           │   Trainable Model                 │
           │   (being preference-tuned)        │
           └──────────────────────────────────┘
                          │
         ┌────────────────┴───────────────────┐
         ▼                                    ▼
  log P_train(chosen | prompt)    log P_train(rejected | prompt)
         │                                    │
         └────────────────┬───────────────────┘
                          │
                     DPO Loss:
         Does trainable model prefer chosen MORE than
         the reference model did?

                          │
                          ▼
              Update trainable model only
```

The reference model exists to prevent the trainable model from drifting too far from its original behaviour. Without it, the model could learn to assign absurdly high probabilities to the chosen responses by forgetting most of what it knew — collapsing its distribution to a narrow set of "preferred" patterns. The reference model acts as an anchor: updates are measured not in absolute terms, but relative to where the model started.

### 6c. The DPO Loss Function

$$\mathcal{L}_{\text{DPO}} = -\log \sigma\!\left(\beta \log \frac{\pi_\theta(y_w \mid x)}{\pi_\text{ref}(y_w \mid x)} - \beta \log \frac{\pi_\theta(y_l \mid x)}{\pi_\text{ref}(y_l \mid x)}\right)$$

| Symbol | Meaning |
|--------|---------|
| $\pi_\theta(y \mid x)$ | Trainable model's probability of generating response $y$ given prompt $x$ |
| $\pi_\text{ref}(y \mid x)$ | Reference model's probability (frozen) |
| $y_w$ | The winning (chosen) response |
| $y_l$ | The losing (rejected) response |
| $\beta$ | Temperature — how much the trainable model may diverge from the reference. Typical: 0.1 |

Reading from the inside out: the term $\log \pi_\theta(y_w \mid x) - \log \pi_\text{ref}(y_w \mid x)$ measures how much *more* the trainable model likes the chosen response compared to the reference model's baseline. If this is positive, the trainable model has already started preferring the chosen response relative to where it started. The term for the rejected response measures how much *less* the trainable model now likes the rejected response. The loss minimises when the trainable model simultaneously increases its relative preference for chosen *and* decreases its relative preference for rejected.

**Dry-run — DPO loss with concrete log-probabilities:**

```
Prompt:   "Explain gradient descent simply."
Chosen:   "Imagine rolling a ball downhill — gradient descent always takes
           a step in the direction the ground slopes downward."
Rejected: "Gradient descent computes the gradient of the loss and updates
           the parameters proportionally."

(Both valid — Chosen is better for a simple explanation due to the analogy)

Reference model log-probabilities:
  log P_ref(chosen   | prompt) = −12.4
  log P_ref(rejected | prompt) = −10.1   ← ref slightly prefers rejected (more textbook-like)

Trainable model (after some DPO training):
  log P_train(chosen   | prompt) = −10.0  ← model now prefers chosen more
  log P_train(rejected | prompt) = −12.8  ← model now disfavours rejected

Ratio for chosen:
  log P_train − log P_ref = −10.0 − (−12.4) = +2.4
  (trainable model is 2.4 log-units more likely to generate chosen than reference was)

Ratio for rejected:
  log P_train − log P_ref = −12.8 − (−10.1) = −2.7
  (trainable model is 2.7 log-units less likely to generate rejected than reference was)

β = 0.1

Inner value = β × (ratio_chosen − ratio_rejected)
            = 0.1 × (2.4 − (−2.7))
            = 0.1 × 5.1 = 0.51

σ(0.51) = 1 / (1 + e^{−0.51}) ≈ 0.625

Loss = −log(0.625) ≈ 0.470

As training continues:
  ratio_chosen rises (model prefers chosen more)
  ratio_rejected falls (model prefers rejected less)
  inner value grows → σ → 1.0 → loss → 0
```

---

### 6d. DPO vs PPO — Why DPO Won

| Dimension | PPO | DPO |
|-----------|-----|-----|
| Separate reward model required? | Yes | No |
| Models in memory simultaneously | 3 (policy, reference, reward model) | 2 (trainable, reference) |
| Training stability | Sensitive to hyperparameters, often unstable | Stable — behaves like supervised learning |
| Implementation complexity | High — requires RL infrastructure | Low — standard gradient descent |
| Memory requirements | High | Moderate |
| Results quality | Baseline | Comparable or better |

DPO simplifies the entire alignment pipeline to something that resembles supervised fine-tuning — which means it benefits from all the stability properties and existing tooling of that well-understood paradigm. The most significant practical advantage is that you do not need to separately train, validate, and tune a reward model before beginning preference tuning.

---

### 6e. ORPO — Combining SFT and DPO in One Pass

**Odds Ratio Preference Optimization (ORPO)**, introduced by Hong et al. (2024), is the most recent step in this sequence of simplifications. While DPO eliminated the separate reward model, it still requires a separately trained SFT model as its reference — meaning you must first do supervised fine-tuning, then do DPO on top of it. That is two training loops, two sets of hyperparameters to tune, and twice the engineering overhead.

ORPO fuses both stages into a single training objective. It modifies the standard next-token-prediction loss used in SFT by adding a preference term that uses the **odds ratio** between the chosen and rejected responses:

$$\mathcal{L}_{\text{ORPO}} = \mathcal{L}_{\text{SFT}} + \lambda \cdot \mathcal{L}_{\text{OR}}$$

The odds ratio term $\mathcal{L}_{\text{OR}}$ compares the model's odds of generating the chosen response versus the rejected response at each training step, and penalises the model for not preferring the chosen response strongly enough. Since the SFT loss and the odds ratio loss are optimised simultaneously, the model learns to follow instructions *and* to prefer better responses in a single pass through the data.

ORPO is fully compatible with QLoRA. You can run ORPO on a 4-bit quantized model with LoRA adapters, achieving the full preference-tuning pipeline — instruction following plus alignment — in a single training run on consumer hardware.

---

## 7. Preference Tuning with DPO — Practical Walkthrough

### 7a. DPO Dataset Format

DPO requires a preference dataset: examples with a prompt, a chosen response, and a rejected response. The book uses the `distilabel-intel-orca-dpo-pairs` dataset from Argilla, which contains instruction–response pairs where two responses have been generated and one has been labelled preferred by a scoring process.

```python
from datasets import load_dataset

def format_prompt(example):
    """Format a DPO example with system prompt and TinyLlama chat template."""
    system = "[system]\n" + example["system"] + "\n"
    prompt = "<|user|>\n" + example["input"] + "\n</s>\n<|assistant|>\n"

    chosen   = example["chosen"]   + "</s>\n"
    rejected = example["rejected"] + "\n"

    return {
        "prompt":   system + prompt,
        "chosen":   chosen,
        "rejected": rejected,
    }

dpo_dataset = load_dataset(
    "argilla/distilabel-intel-orca-dpo-pairs", split="train"
)

dpo_dataset = dpo_dataset.filter(
    lambda r: (
        r["status"] != "tie"           # Remove examples where neither is better
        and r["chosen_score"] != 0     # Remove zero-scored examples
        and not r["in_gsm8k_train"]    # Remove examples overlapping GSM8k test set
    )
)

dpo_dataset = dpo_dataset.map(
    format_prompt, remove_columns=dpo_dataset.column_names
)
```

The filtering step is important. **Ties** are removed because DPO requires one response to be strictly better — tie examples send a contradictory training signal. **Zero-scored examples** were likely labelled carelessly. The **GSM8k contamination filter** removes examples from the GSM8k math benchmark's training set to ensure that later evaluation on GSM8k measures genuine reasoning rather than memorisation.

---

### 7b. DPO Training Configuration

DPO uses the same basic training infrastructure as SFT, with a few important differences:

```python
from trl import DPOConfig

training_arguments = DPOConfig(
    output_dir="./results",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    optim="paged_adamw_32bit",
    learning_rate=1e-5,         # ← 20× lower than SFT's 2e-4
    lr_scheduler_type="cosine",
    max_steps=200,              # ← short run for illustration
    logging_steps=10,
    fp16=True,
    gradient_checkpointing=True,
    warmup_ratio=0.1            # ← warm up for first 10% of steps
)
```

The learning rate is a full order of magnitude lower than in SFT (1e-5 vs 2e-4). In SFT, we are teaching the model a fundamentally new behaviour — following instructions — and large updates are appropriate. In DPO, we are making subtle refinements to a model that already behaves well. Large updates would destroy the model's instruction-following capabilities in exchange for marginal preference alignment gains.

`warmup_ratio=0.1` linearly increases the learning rate from 0 to `1e-5` during the first 10% of training steps. At the very start of DPO training, the model has not yet learned anything about the preference data, and gradient estimates are noisy. A warm-up period lets the model stabilise before full-strength updates are applied, preventing early catastrophic forgetting of the SFT model's capabilities.

---

### 7c. DPOTrainer and the Beta Parameter

```python
from trl import DPOTrainer

dpo_trainer = DPOTrainer(
    model,
    args=training_arguments,
    train_dataset=dpo_dataset,
    tokenizer=tokenizer,
    peft_config=peft_config,
    beta=0.1,             # ← controls distance from reference model
    max_prompt_length=512,
    max_length=512,
)

dpo_trainer.train()
dpo_trainer.model.save_pretrained("TinyLlama-1.1B-dpo-qlora")
```

The `beta` parameter ($\beta$ in the DPO loss formula) is the most important DPO-specific hyperparameter. Think of it as the "leash length" keeping the trainable model close to the reference model.

A small $\beta$ (e.g., 0.1) allows the model to deviate substantially from its reference. The preference signal dominates, and the model can make large shifts in its response distribution. A large $\beta$ (e.g., 0.5 or higher) keeps the model conservative — small adjustments, staying close to SFT behaviour. The value $\beta = 0.1$ is the most commonly used starting point.

---

### 7d. Stacking SFT and DPO Adapters

The full fine-tuning pipeline — SFT followed by DPO — requires loading two separate LoRA adapters and merging them in sequence:

```python
from peft import AutoPeftModelForCausalLM, PeftModel

# Step 1: Merge the SFT LoRA adapter into the base model
sft_base = AutoPeftModelForCausalLM.from_pretrained(
    "TinyLlama-1.1B-qlora",
    low_cpu_mem_usage=True,
    device_map="auto",
)
sft_model = sft_base.merge_and_unload()
# sft_model is now a standard model with SFT baked in — no adapter overhead

# Step 2: Load the DPO adapter on top of the merged SFT model
dpo_peft_model = PeftModel.from_pretrained(
    sft_model,
    "TinyLlama-1.1B-dpo-qlora",
    device_map="auto",
)
final_model = dpo_peft_model.merge_and_unload()
# final_model has both SFT and DPO permanently merged
```

```
Full Pipeline — From Base Model to Aligned Assistant:

  TinyLlama Base Model (pretrained)
          │
          ▼
  ┌────────────────────────────────────────┐
  │  SFT with QLoRA                        │
  │  Dataset: UltraChat (3,000 examples)   │
  │  Learns: follow instructions           │
  │  Saved: TinyLlama-1.1B-qlora/          │
  └────────────────────────────────────────┘
          │
          ▼
  merge_and_unload()   ←  A·B fused into W for every targeted layer
          │
          ▼
  Instruction-Tuned Model (SFT baked in)
          │
          ▼
  ┌────────────────────────────────────────┐
  │  DPO with QLoRA                        │
  │  Dataset: distilabel-intel-orca pairs  │
  │  Learns: prefer helpful responses      │
  │  Saved: TinyLlama-1.1B-dpo-qlora/      │
  └────────────────────────────────────────┘
          │
          ▼
  merge_and_unload()   ←  DPO A·B fused into SFT-merged weights
          │
          ▼
  Final Aligned Model
  ✓ Follows instructions (from SFT)
  ✓ Prefers helpful, clear, accurate responses (from DPO)
  ✓ No PEFT overhead at inference time
```

The two-stage pipeline is more powerful than either stage alone, but it has costs: two training runs, two sets of hyperparameters to tune, and twice the experimentation overhead. This is precisely the problem that ORPO was designed to solve — collapsing both stages into a single training loop while preserving the benefits of both.

---

## 8. Key Takeaways

The central arc of this chapter is the journey from a raw pretrained model — which knows everything but can do nothing useful — to a fine-tuned, aligned model that follows instructions and consistently produces high-quality responses. Every technique in the chapter is a solution to a specific bottleneck in that journey.

**LoRA is the key enabler.** By decomposing weight updates as the product of two thin matrices ($W' = W + AB$), LoRA reduces the number of trainable parameters by 768× or more for large models. The intrinsic-dimensionality insight behind LoRA — that meaningful fine-tuning changes live in a low-dimensional subspace — is one of the most important empirical discoveries in the field. B is initialised to zero so the model starts as an exact copy of the pretrained model; only the combination $AB$ gradually encodes the task-specific adaptation.

**QLoRA extends LoRA with 4-bit quantization.** Loading the frozen base model in 4-bit NF4 reduces memory by 4–8× with minimal accuracy loss. The combination of quantized base weights and float16 LoRA adapters makes it possible to fine-tune a 7B model on a single 8 GB GPU. Without QLoRA, fine-tuning was the exclusive territory of organisations with data-centre GPU clusters.

**Evaluation remains the unsolved problem.** Word-level metrics (BLEU, ROUGE, perplexity) are fast but shallow. Benchmarks are useful but gameable — Goodhart's Law applies relentlessly. LLM-as-a-judge scales but carries biases. Human evaluation is the gold standard but expensive. The honest answer is that you must combine multiple evaluation signals, and ultimately test your model on the actual prompts your users will send.

**DPO replaced PPO as the dominant alignment algorithm.** PPO requires three simultaneous models, reinforcement learning infrastructure, and careful hyperparameter tuning. DPO achieves the same goal — aligning model outputs with human preferences — using a simple supervised loss computed over the trainable model and a frozen reference. The key mathematical insight is that the optimal reward function is *implicit* in the LLM's log-probability ratios, so no separate reward model training is needed.

**ORPO collapses two stages into one.** If you want to push further, ORPO combines supervised fine-tuning and preference tuning into a single training loop, reducing engineering complexity while maintaining the alignment benefits of DPO. It is fully compatible with QLoRA.

The papers underlying these techniques are worth reading in full:
- *"LoRA: Low-Rank Adaptation of Large Language Models"* — Hu et al., 2021
- *"QLoRA: Efficient Finetuning of Quantized LLMs"* — Dettmers et al., 2023
- *"Direct Preference Optimization: Your Language Model is Secretly a Reward Model"* — Rafailov et al., 2023
- *"ORPO: Monolithic Preference Optimization without Reference Model"* — Hong et al., 2024

---

*Chapter 12 of Hands-On Large Language Models (O'Reilly) · Notes by sp-techv*
