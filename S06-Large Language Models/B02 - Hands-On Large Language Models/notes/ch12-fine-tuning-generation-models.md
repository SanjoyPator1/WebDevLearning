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
   - [4a. Why Evaluating Generative Models Is Genuinely Hard](#4a-why-evaluating-generative-models-is-genuinely-hard)
   - [4b. Perplexity — How Surprised Was the Model?](#4b-perplexity--how-surprised-was-the-model)
   - [4c. N-gram Overlap Metrics — BLEU, ROUGE, and Their Limits](#4c-n-gram-overlap-metrics--bleu-rouge-and-their-limits)
   - [4d. BERTScore — Semantic Overlap via Embeddings](#4d-bertscore--semantic-overlap-via-embeddings)
   - [4e. Public Benchmarks and the Overfitting Trap](#4e-public-benchmarks-and-the-overfitting-trap)
   - [4f. LLM-as-a-Judge — Automated Pairwise Comparison](#4f-llm-as-a-judge--automated-pairwise-comparison)
   - [4g. Human Evaluation and Chatbot Arena](#4g-human-evaluation-and-chatbot-arena)
5. [Preference Tuning and RLHF](#5-preference-tuning-and-rlhf)
   - [5a. Why Instruction Tuning Is Not Enough — Taste vs Format](#5a-why-instruction-tuning-is-not-enough--taste-vs-format)
   - [5b. The Preference Evaluator — From Human Rater to Automated Judge](#5b-the-preference-evaluator--from-human-rater-to-automated-judge)
   - [5c. The Reward Model — Anatomy and Architecture](#5c-the-reward-model--anatomy-and-architecture)
   - [5d. Building the Preference Dataset](#5d-building-the-preference-dataset)
   - [5e. Training the Reward Model — The Bradley-Terry Loss](#5e-training-the-reward-model--the-bradley-terry-loss)
   - [5f. Proximal Policy Optimization (PPO) — Optimising Against the Reward Signal](#5f-proximal-policy-optimization-ppo--optimising-against-the-reward-signal)
   - [5g. The Three-Model Memory Problem — Why PPO Hurts](#5g-the-three-model-memory-problem--why-ppo-hurts)
6. [Direct Preference Optimization (DPO)](#6-direct-preference-optimization-dpo)
   - [6a. The Core Insight — Your LLM Is Already a Reward Model](#6a-the-core-insight--your-llm-is-already-a-reward-model)
   - [6b. The Theoretical Bridge — How DPO Eliminates the Reward Model](#6b-the-theoretical-bridge--how-dpo-eliminates-the-reward-model)
   - [6c. The Four Players in a DPO Step](#6c-the-four-players-in-a-dpo-step)
   - [6d. Token-Level Scoring — How the Probabilities Are Computed](#6d-token-level-scoring--how-the-probabilities-are-computed)
   - [6e. The DPO Loss Function with Dry-Run](#6e-the-dpo-loss-function-with-dry-run)
   - [6f. DPO vs PPO — Why DPO Won](#6f-dpo-vs-ppo--why-dpo-won)
   - [6g. ORPO — Combining SFT and DPO in One Pass](#6g-orpo--combining-sft-and-dpo-in-one-pass)
7. [Preference Tuning with DPO — Practical Walkthrough](#7-preference-tuning-with-dpo--practical-walkthrough)
   - [7a. The DPO Walkthrough Pipeline — Mirror of Section 3, with Preferences](#7a-the-dpo-walkthrough-pipeline--mirror-of-section-3-with-preferences)
   - [7b. The Preference Dataset — distilabel-intel-orca-dpo-pairs](#7b-the-preference-dataset--distilabel-intel-orca-dpo-pairs)
   - [7c. Loading the SFT-Merged Quantized Base Model](#7c-loading-the-sft-merged-quantized-base-model)
   - [7d. LoRA Configuration for the DPO Stage](#7d-lora-configuration-for-the-dpo-stage)
   - [7e. DPOConfig — Training Arguments for Preference Tuning](#7e-dpoconfig--training-arguments-for-preference-tuning)
   - [7f. DPOTrainer and the Beta Parameter](#7f-dpotrainer-and-the-beta-parameter)
   - [7g. Stacking SFT and DPO Adapters into a Final Aligned Model](#7g-stacking-sft-and-dpo-adapters-into-a-final-aligned-model)
8. [Key Takeaways](#8-key-takeaways)
   - [8a. The Three-Stage Pipeline — Three Problems, Three Stages](#8a-the-three-stage-pipeline--three-problems-three-stages)
   - [8b. The Pattern-Completion Problem Is Why SFT Exists](#8b-the-pattern-completion-problem-is-why-sft-exists)
   - [8c. PEFT and LoRA — Why 1% Is Enough](#8c-peft-and-lora--why-1-is-enough)
   - [8d. QLoRA Democratised Fine-Tuning](#8d-qlora-democratised-fine-tuning)
   - [8e. Evaluation Has No Silver Bullet](#8e-evaluation-has-no-silver-bullet)
   - [8f. From PPO to DPO to ORPO — The Simplification Trajectory](#8f-from-ppo-to-dpo-to-orpo--the-simplification-trajectory)
   - [8g. Decision Guide and Papers to Read](#8g-decision-guide-and-papers-to-read)

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

#### Extra notes on Adapters

When you are reading through pages of theory, abstract concepts like "bottleneck architectures" can feel a bit disconnected from reality.

Let's break Adapters down into exactly what they are, where they go, and how the math works, using concrete numbers.

---

##### 1. What are Adapters and what do they do?

When you want to fine-tune a massive model, updating every single weight is computationally crushing (as you saw with the "Memory Wall"). **Adapters** are a solution to this: they are tiny, trainable neural network modules inserted into the massive, pre-existing (and frozen) layers of the model.

Instead of changing the model's original "brain" to learn a new task, you freeze the brain and force all the new learning to happen *only* inside these tiny new modules.

The secret to why they are so small is the **bottleneck architecture**. They take the high-dimensional data flowing through the network, squish it down to a very small dimension (the bottleneck), apply a non-linear transformation, and then expand it back to its original size. Because the bottleneck is so small, there simply aren't enough parameters to memorize the data; the adapter is forced to learn only the most essential, compressed, task-specific signals.

##### 2. Where do they sit in the architecture?

Imagine a single Transformer block in an LLM. Data normally flows from the Multi-Head Attention directly into a Feed-Forward Network.

The original Houlsby architecture interrupts this flow by dropping an Adapter in two specific places per block:

1. Right after the **Multi-Head Attention** (and its Add & LayerNorm).
2. Right after the **Feed-Forward Network** (and its Add & LayerNorm).

Here is a visual representation of a single block:

```text
  Input
    │
    ▼
  [Multi-Head Attention]   ❄️ FROZEN
    │
    ▼
  [Add & LayerNorm]        ❄️ FROZEN
    │
    ▼
  [ Adapter Module 1 ]     🔥 TRAINABLE (Sits here!)
    │
    ▼
  [Feed-Forward Network]   ❄️ FROZEN
    │
    ▼
  [Add & LayerNorm]        ❄️ FROZEN
    │
    ▼
  [ Adapter Module 2 ]     🔥 TRAINABLE (And sits here!)
    │
    ▼
  Output

```

*Note: Because every transformer block gets these two adapters, a 12-block transformer will have 24 adapter modules in total, which are all trained together.*

##### 3. How do they look? (The Math)

Let's look inside one of those `[ Adapter Module ]` boxes. The math formula for the data passing through an adapter is:

$$\text{Adapter}(h) = h + W_{\text{up}} \cdot \sigma(W_{\text{down}} \cdot h)$$

Here is what each piece means:

* $h$: The input vector (hidden state) coming into the adapter. Let's say it has a dimension $d$.
* $W_{\text{down}}$: A trainable weight matrix that projects the data *down* to the bottleneck dimension $m$ (where $m \ll d$). Its shape is $m \times d$.
* $\sigma$: A non-linear activation function (like ReLU or GELU).
* $W_{\text{up}}$: A trainable weight matrix that projects the data back *up* to the original dimension $d$. Its shape is $d \times m$.
* $+ h$: A residual connection. The original data $h$ is added back to the adapter's output.

**Why the residual connection ($+ h$) matters:** When you start training, the adapter weights are initialized so that $W_{\text{up}} \cdot \sigma(W_{\text{down}} \cdot h)$ is essentially zero. Because of the $+ h$, the adapter just outputs $h$. It acts like a bypassed wire. As training progresses, it gently adds its new task-specific knowledge to $h$.

##### 4. A Concrete Toy Example

Let's do a dry run with tiny numbers so you can see *why* this saves memory.

Imagine the input vector $h$ has a dimension of $d = 1000$.
If you wanted to do a standard full fine-tuning on a fully connected layer of that size, the weight matrix would be $1000 \times 1000$.

* **Full Fine-Tuning Parameters:** $1000 \times 1000 =$ **$1,000,000$ trainable parameters**.

Now, let's use an Adapter instead, and we set our bottleneck dimension to $m = 10$.

1. **The down-projection ($W_{\text{down}}$):** Takes the $1000$-dimensional vector and squishes it to $10$.
* Shape: $10 \times 1000$
* Parameters: $10,000$


2. **The non-linearity ($\sigma$):** Just applies a math function, $0$ parameters.
3. **The up-projection ($W_{\text{up}}$):** Takes the $10$-dimensional vector and expands it back to $1000$.
* Shape: $1000 \times 10$
* Parameters: $10,000$



* **Total Adapter Parameters:** $10,000 + 10,000 =$ **$20,000$ trainable parameters**.

**The Result:** By forcing the data through a bottleneck of $m=10$, you only have to train $20,000$ parameters instead of $1,000,000$. You just reduced your compute and memory footprint by **98%**, while still allowing the network to inject learned task-specific signals into the data flow.

#### Adapter math

If you are using that toy example on a 12-block transformer, here is exactly how the numbers shake out:

* **12 blocks** × **2 adapters per block** = **24 adapter modules** scattered throughout the model.
* **24 adapters** × **20,000 parameters each** = **480,000 total trainable parameters**.

To put into perspective just how much memory that saves, let's look at what would happen if you did a full fine-tuning on those same layers.

If the original frozen layers in those 12 blocks each had a 1000 × 1000 weight matrix (1,000,000 parameters), full fine-tuning those 24 layers would mean training **24,000,000 parameters**.

By using adapters, you drop the trainable parameter count from 24 million down to 480 thousand—while still letting the model learn new behaviors at every single stage of its computation. That is the magic of the bottleneck!

#### How Adapter actually learns

That is a brilliant follow-up question. It is one thing to know that the math saves memory, but it is another entirely to wrap your head around *how* a tiny 20,000-parameter bottleneck can teach a massive 1-billion-parameter model to do something completely new!

To understand how fine-tuning works with adapters, we have to look at the process of learning—specifically, how the flow of data and errors shapes those tiny modules.

##### 1. The Starting Point: The Base Model Already Knows "Everything"

The most important thing to remember is that we are not teaching the model the English language from scratch. During its original pretraining, the base model already spent months reading the entire internet. It already knows grammar, facts, coding syntax, and reasoning patterns.

As the notes mention, it is like a master classical violinist who has spent 20 years perfecting their craft. When we fine-tune it to be a chatbot, we are just asking that classical violinist to play folk music at a wedding. They don't need to relearn how to hold the bow; they just need a small "overlay" of new stylistic habits.

##### 2. The Forward Pass: How the Adapter Wakes Up

When training begins, the adapter is initialized so that it basically does nothing. Because of the residual connection, the data $h$ flows out of the frozen layer, passes through the adapter, and comes out exactly as $h$.

At this stage, if you ask the model a question, it will act exactly like the raw base model and make mistakes (like pattern-completing your question with more questions instead of answering it).

##### 3. The Backward Pass: How the Adapter Actually Learns

Here is where the magic of fine-tuning happens step-by-step:

1. **The Mistake (Loss):** We feed the model an instruction-response pair (e.g., "What is 1+1?" -> "2"). The model predicts the wrong next token. We calculate the mathematical error (the loss) based only on the response tokens.
2. **The Correction Signal (Backpropagation):** The optimizer sends a correction signal (the gradient) backward through the entire neural network, layer by layer, saying, "Change your weights so we get this right next time!"
3. **The Frozen Wall:** The signal hits the massive original layers of the model, but those layers are **frozen**. They say, "You can't change us!"
4. **The Sponge (The Adapter):** Because the massive layers refuse to change, **100% of the learning pressure is forced into the adapter's tiny $W_{\text{down}}$ and $W_{\text{up}}$ matrices**. The optimizer nudges the adapter's weights in the exact direction needed to fix the mistake.

##### 4. The Result: The Adapter Becomes a "Steering Wheel"

Over thousands of steps, those tiny adapters absorb the new task. They learn to act like little filters or steering wheels.

Now, when data flows through the network:

1. The massive frozen layer does the heavy lifting, outputting its raw understanding of the concepts as the vector $h$.
2. The adapter catches $h$ before it moves to the next layer.
3. The adapter recognizes, "Ah, this is a question! The frozen layer wants to pattern-complete it, but my new weights know we need to format this as an answer."
4. The adapter applies its learned transformation to $h$, slightly bending or shifting the vector so it points toward an "answering" behavior rather than a "pattern-completing" behavior.

Because the adapter forces the data through a bottleneck, it can't memorize the exact sentences in your training data. It is forced to learn the *general rule* of the task—the compressed, essential signal of how to behave like a helpful assistant.

#### Data in adapters

It is important to clarify that **adapters do not need a "special" type of data**. Because an adapter is just a tiny module inserted into the model, you train it using the exact same data you would use if you were doing a full fine-tuning.

What the data looks like depends entirely on which stage of the pipeline you are in. Since you are starting with **Stage 2: Supervised Fine-Tuning (SFT)** in your notebook, let's look at exactly what you will feed into the adapter.

##### What Data Do We Use?

For SFT, you use a curated set of **instruction–response pairs**.

You are no longer feeding the model raw, unlabeled internet text. Instead, you are giving it structured examples of what a human user might ask, paired with exactly how you want the AI assistant to reply.

Crucially, when this data is fed into the model, the training algorithm "masks" the instruction so that the adapter only learns from the *response* tokens. We want the adapter to learn how to produce answers, not how to invent user questions.

##### How Much Data Do We Need?

Because the base model already knows vocabulary, grammar, and facts from its pretraining, SFT requires very little data to change its behavior.

Typically, SFT datasets range from **a few thousand to a few hundred thousand examples**.

In the notebook you are working on, you will be using a dataset called `UltraChat`. To keep the training time under an hour on a standard GPU (and incredibly fast on your A6000), the walkthrough specifically selects just **3,000 multi-turn conversations**. The notes mention that you can increase this number if you want better quality, but it will cost you more training time.

##### Examples of the Data

Here is what a single raw SFT training example looks like before it is formatted:

```json
{
    "instruction": "Explain what reinforcement learning is in two sentences.",
    "response":    "Reinforcement learning is a type of machine learning where an agent learns by taking actions in an environment and receiving rewards or penalties. Over time, the agent learns a policy that maximises its cumulative reward."
}

```

However, before the model actually sees this data, you have to run it through a "Chat Template" so the model knows who is speaking. In Part 1.1 of your notebook, you will use TinyLlama's chat template, which wraps the text in special tokens (`<|user|>`, `<|assistant|>`, and `</s>`).

After formatting, the data the adapter actually trains on looks like this:

```text
<|user|>
What is 1 + 1?</s>
<|assistant|>
The answer to 1 + 1 is 2!</s>

```

#### Loss Masking

To understand "loss masking," we have to separate what the model **reads** from what the model is **graded on**.

##### The Problem: Predicting the User

Remember that the fundamental training objective of these models is always **next-token prediction**. The model looks at a sequence of words and tries to guess the very next word.

If you feed the model a full SFT training example:
`<|user|> What is 1+1? </s> <|assistant|> The answer is 2. </s>`

During training, the model walks through this text left-to-right, trying to predict every single token:

1. It sees `<|user|>` and tries to guess the next word. Let's say it guesses `"Hello"`. It is wrong; the real next word was `"What"`.
2. It sees `<|user|> What` and tries to guess the next word...

If we calculate an error (a "loss") for these mistakes and send an update to the adapter weights, **we are training the model to predict what the user is going to ask**.

If we do that, when you deploy the chatbot and wait for it to answer, it might just start generating fake user questions instead of giving you an answer! As the notes put it, computing loss over the instruction tokens pushes the model toward producing more user-style inputs, which is the exact opposite of what we want.

##### The Solution: Loss Masking (The "Ignore" Trick)

To fix this, we use a technique called **loss masking**.

The model still *reads* the entire sequence (it needs to read the user's question so it knows what to answer!), and it still makes predictions for every step.

However, when it is time to calculate the mathematical error (the loss) that updates the adapter weights, we **turn off the grading for the user's portion of the text**. We effectively mask them out.

Here is how the notes visualize it:

```text
Tokens:  [ <|user|> What is 1+1? </s> | <|assistant|> The answer is 2. </s> ]
Mask:    [   _       _   _   _    _  |       X        X    X      X  X   X  ]

```

* `_` = Position is ignored (No grading).
* `X` = Loss is computed here (Graded!).

##### How it actually works in PyTorch (and your Notebook)

When you get to **Part 3f: SFTTrainer and the Training Loop** in your Jupyter Notebook, `SFTTrainer` handles this masking automatically.

Mechanically, it sets the label for all the user-turn tokens to `-100`. In PyTorch, `-100` is a special code that means "ignore this token when calculating the cross-entropy loss".

Because the loss for the user's question is exactly zero, no correction signal (gradient) flows backward to the adapter for that part of the text. The adapter only gets updated based on how well it predicted the *assistant's* response tokens.

This makes the training signal incredibly sharp and unambiguous: *"Given this specific instruction that you just read, produce exactly this response"*.

Here is the exact breakdown of the three steps you just described, mapped to how the GPU actually processes it:

* **The Forward Pass:** The model is fed the entire sequence (both the user's question and the assistant's answer) concatenated together. It walks left-to-right and makes a next-token prediction at every single position, including the user's prompt.
* **The Loss Calculation:** Before we do any math on the errors, we apply the "mask." We look at all the predictions the model made during the user's question and artificially set their error (loss) to exactly zero. We only calculate the real mathematical error for the predictions it made during the assistant's response.
* **The Backward Pass (Backpropagation):** The optimizer takes the total loss and works backward through the network to update the adapter weights. Because the loss for the user's question was set to zero, there is no "correction signal" (gradient) for those tokens. The weights are only nudged to fix the mistakes it made while predicting the assistant's response.


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

#### Extra LoRA notes

Let's break down this topic using small examples to make it concrete.

##### 1. Is there only ONE pair of A and B matrices for the whole LLM?

**No.** There are hundreds of them!

Every single weight matrix you target gets its **own dedicated pair** of $A$ and $B$ matrices.

For example, in the TinyLlama walkthrough, there are 22 transformer blocks. In *each* block, you are targeting 7 different projections (`q_proj`, `k_proj`, etc.). That means there are $22 \times 7 = 154$ individual frozen $W$ matrices being targeted. Therefore, the code creates **154 separate $A$ matrices and 154 separate $B$ matrices**.

##### 2. How do we know which weights we are targeting, and how does it happen?

This is handled by the `peft` (Parameter-Efficient Fine-Tuning) library in Python.

When you define your `LoraConfig`, you pass a list called `target_modules` (e.g., `["q_proj", "v_proj"]`). When you call `get_peft_model()`, the library literally walks through the PyTorch architecture of the model like a tree.

Every time it finds a layer whose name matches something in your list (like `model.layers.0.self_attn.q_proj`), it rips out the standard Linear layer and replaces it with a special `LoraLayer`. This new `LoraLayer` acts as a wrapper that holds three things:

1. The original massive weight matrix $W$ (which it immediately freezes).
2. A newly created, small matrix $A$ (initialized with random numbers).
3. A newly created, small matrix $B$ (initialized with all zeros).

##### 3. Do we ONLY train the A and B arrays?

**Yes, absolutely.** The massive $W$ matrices have their gradients turned off (`requires_grad=False`). The optimizer only looks at the tiny $A$ and $B$ matrices to make updates.

##### 4. How do we calculate loss or predict if we only multiply it at the end? (The Step-by-Step)

This is a very common point of confusion. We do **not** wait until the end of training to combine them. We combine their *outputs* dynamically during every single step of training!

Here is the exact step-by-step of how a prediction is made **during training**:

Let's say a piece of data (a vector $x$) flows into our `q_proj` layer.

1. **The Frozen Path:** The data $x$ is multiplied by the massive, frozen $W$ matrix to get a result: $W \cdot x$.
2. **The LoRA Path:** Simultaneously, that exact same data $x$ is multiplied by $A$, and then by $B$: $A \cdot B \cdot x$. This result is then multiplied by your scaling factor ($\alpha/r$).
3. **The Combination:** The results of the two paths are added together: **$\text{Output} = Wx + \frac{\alpha}{r}(ABx)$**.

**How the loss is calculated:**
That combined output continues through the rest of the neural network until the model guesses the next word.

* If the guess is wrong, the loss is calculated based on that final, combined guess.
* The error signal (gradient) travels backward through the network.
* When the signal hits our `LoraLayer`, it flows right past the frozen $W$ matrix and goes entirely into updating the weights of $A$ and $B$.

**Small Example:**
Imagine we are just pushing the number `1` through a tiny 1x1 toy model.

* Frozen $W$ = `5`
* Trainable $A$ = `0.5`, Trainable $B$ = `0.0` (starts at zero!)
* Scale ($\alpha/r$) = `1`

**Step 1 (First pass):**

* Frozen path: $5 \times 1 = 5$
* LoRA path: $0.5 \times 0.0 \times 1 = 0$
* Total Output: $5 + 0 = 5$.
* *The model predicts something based on `5`. It gets it wrong. The loss says, "The output should have been `6`!"*

**Step 2 (The update):**

* The optimizer sees the error and nudges the trainable variables. It changes $B$ from `0.0` to `2.0`.

**Step 3 (Next pass):**

* Frozen path: $5 \times 1 = 5$
* LoRA path: $0.5 \times 2.0 \times 1 = 1$
* Total Output: $5 + 1 = 6$.
* *The model is now correct! Notice that $W$ is still exactly `5`. We fixed the output entirely by changing $B$.*

**What happens at the very end of all training?**
Only when you are completely done training and ready to deploy the model, you do a permanent math operation: you calculate the actual matrix $\Delta W = \frac{\alpha}{r}(A \cdot B)$, add it permanently to $W$ to create a new matrix $W'$, and then you delete $A$ and $B$ to save memory. This is called "merging".

#### Data in LoRA

Just like we discussed with adapters, **LoRA does not require any special or unique data format**. Because LoRA is just a mathematical method for calculating weight updates, it uses the exact same data you would use for a full-parameter fine-tuning or an adapter step.

Since you are currently in **Part 1: Supervised Fine-Tuning with QLoRA**, the data you use is identical to the SFT data we broke down earlier: **curated instruction-response pairs wrapped in a chat template**.

To make this completely crystal clear, let's look at the data timeline during a training step:

##### 1. The Raw Data (The `UltraChat` dataset)

You pull raw conversational text from your dataset. In its rawest form, it's just human text representing turns in a conversation:

* **User prompt:** *"Can you list three major branches of science?"*
* **Assistant response:** *"Yes! The three major branches are formal sciences, natural sciences, and social sciences."*

##### 2. The Tokenized Data (The Chat Template)

Before LoRA sees this data, your notebook runs it through the tokenizer's chat template. This transforms the raw text into a single long string interspersed with special markers so the model understands the conversational structure:

```text
<|user|>
Can you list three major branches of science?</s>
<|assistant|>
Yes! The three major branches are formal sciences, natural sciences, and social sciences.</s>

```

The tokenizer then converts these characters into a sequence of numbers (token IDs).

##### 3. How the Data Flows through the LoRA Layer

This sequence of token IDs is what gets passed into the model.

When it strikes a targeted layer (like a `q_proj` attention projection), the token values travel down **two parallel streams simultaneously**:

1. **Stream 1 (The Frozen Base):** The data passes through the massive, 4-bit quantized base model matrix $W$ to calculate the foundational representation.
2. **Stream 2 (The LoRA Adapter):** The exact same data passes through your thin, trainable $A$ and $B$ matrices.

The outputs are summed, next-token prediction happens, and thanks to **loss masking**, your model calculates the error *only* on the tokens that belong to the assistant's response.

##### The Data Volume Rule of Thumb

Because you are using **QLoRA** (which stands for Quantized LoRA), you are fine-tuning a compressed version of the base model while training a relatively small number of parameters ($\sim 5\%$ of the total model in your specific notebook setup).

Because the model isn't learning a brand new language but rather learning how to *behave* like a chat companion, you don't need petabytes of data. A few thousand rows is plenty—which is why your notebook uses **3,000 high-quality examples**.

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

#### Extra Notes

It makes total sense that QLoRA feels like a lot to chew on. In the previous explanations, we separated the ideas: **LoRA** shrinks the *trainable* parameters, and **Quantization** shrinks the *frozen base model*.

QLoRA (Quantized LoRA) is just the brilliant combination of both. But to understand why standard quantization ruins LLMs and why QLoRA's specific tricks (Blockwise and NF4) fix it, we need to look at how numbers are actually squished.

Let's break it down using small examples, just like we did with the adapters.

---

##### The Core Problem: Why "Normal" Quantization Fails

Imagine quantization as having exactly **16 buckets** (which is what 4-bit storage gives you) to sort all your weights into.

If you use normal, uniform quantization, you space those 16 buckets evenly between your lowest weight and your highest weight. But real LLM weights have two annoying habits that break this:

**1. The Outlier Problem**
Imagine 99% of a layer's weights are between `-0.5` and `+0.5`. But there is one random "outlier" weight sitting at `+50.0`.
If you space your 16 buckets evenly between `-0.5` and `+50.0`, the buckets are so wide that almost every single normal weight falls into the very first bucket.

* *The Notes Analogy:* It is like designing a single ruler to measure both a pencil and a flagpole. It works for the flagpole (the outlier), but it is useless for the pencil (the normal weights).

**2. The Bell Curve Problem (Density Mismatch)**
Even without outliers, LLM weights naturally cluster around zero like a bell curve. If you space your 16 buckets evenly, you waste a bunch of buckets on the edges where there are barely any weights, and you don't have enough buckets in the middle where millions of weights are fighting for space.

---

##### QLoRA's Two Brilliant Fixes

QLoRA introduces two specific tricks to solve these exact problems.

##### Fix 1: Blockwise Quantization (Solving the Outlier)

Instead of looking at the entire massive weight matrix and setting the buckets based on the absolute highest and lowest numbers, QLoRA chops the matrix into tiny blocks (usually 64 weights per block). **It creates a custom set of 16 buckets for every single block.**

* **Toy Example:** Imagine a tiny matrix chopped into two blocks of 4 weights.
* **Block 1:** `[0.1,  0.3, -0.2,  0.4]`
* **Block 2:** `[0.2, -0.1,  0.3, 50.0]` *(Uh oh, the outlier!)*



Because they are processed in blocks, **Block 1** sets its buckets tightly between `-0.2` and `+0.4`. It keeps perfectly high precision for those weights. **Block 2** is forced to stretch its buckets to fit `50.0`, so it loses precision, but the damage is *contained* only to those 64 weights. The outlier didn't ruin the rest of the model!

##### Fix 2: NF4 - NormalFloat 4-bit (Solving the Bell Curve)

Instead of spacing the 16 buckets evenly, NF4 places the buckets exactly where the weights actually live.

Since it knows LLM weights form a bell curve around zero, NF4 **packs a ton of buckets really close together near zero**, and spaces the outer buckets far apart.

```text
Visualizing the Buckets (16 levels):

Standard Uniform Quantization (Even spacing):
  |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
 -1                           0                          +1

NF4 Quantization (Packed where the weights actually are):
  |       |    |  | ||||| |  |    |       |
 -1                           0                          +1

```

This means the model can retain incredible detail for the millions of weights sitting near zero, squeezing the absolute maximum amount of information out of just 4 bits.

---

#### Putting it all together: How QLoRA runs in your architecture

Now let's zoom out and look at how this fits with the LoRA adapters we talked about earlier.

1. **The Base Model (Frozen):** You load your massive base model. It is compressed using NF4 and Blockwise quantization. It is sitting in 4-bit storage on your GPU, saving you massive amounts of VRAM (shrinking a 7B model from 28GB down to about 3.5GB).
2. **The Adapters (Trainable):** You attach your tiny $A$ and $B$ matrices. These are stored in high-precision 16-bit math.
3. **The Forward Pass (The "Unpacking"):** GPU processing chips cannot actually do math with 4-bit numbers. So, right at the exact millisecond the data is flowing through a specific layer, the 4-bit weights are **dequantized (unpacked) on-the-fly** back into 16-bit numbers.
4. **The Math:** The newly unpacked 16-bit base weights do their math with the data, the 16-bit LoRA matrices do their math with the data, the results are added together, and then the unpacked base weights are immediately thrown away to save space.
5. **The Backward Pass:** The error signal travels back, skips the frozen base model entirely, and only updates the 16-bit $A$ and $B$ matrices.

By combining NF4 blockwise quantization with LoRA, you get the intelligence of a massive model, the fine-tuning capability of high-precision math, and a footprint so small it runs comfortably on your single A6000 GPU!

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

We have an instruction-tuned model. Is it any good? That sounds like a simple question, but for generative models it is one of the hardest open questions in the field. This section walks through every tool in the modern evaluation toolkit — from the cheap-and-shallow (perplexity) to the slow-and-gold-standard (human voting in Chatbot Arena) — and is honest about what each one can and cannot tell you.

### 4a. Why Evaluating Generative Models Is Genuinely Hard

Imagine grading a math problem against grading a poem. The math problem has one correct answer; a quick comparison with the answer key gives an unambiguous right-or-wrong verdict. The poem is the opposite — thousands of equally good responses exist, and "good" is not even one dimension: it is a vector of fluency, originality, emotional resonance, technical craft, audience appropriateness, and many more. You cannot grade a poem by counting how many of its words match a reference poem.

Generative-model evaluation lives on the poem side. A classifier maps an input to one of $N$ labels, so accuracy and F1 are well-defined. A generative model maps an input to *arbitrary text*, and there is no single reference to compare against. Worse, the qualities we actually care about — **factual accuracy**, **fluency**, **helpfulness**, **honesty**, **appropriate length**, **tone**, **safety** — pull in different directions and resist measurement.

No single metric captures all of these, which is why a real evaluation pipeline stacks several tools, each with a different tradeoff between speed and reliability:

```
                  The evaluation toolkit, fastest to most reliable:

  ┌──────────────────────────────────────────────────────────────┐
  │  4b. Perplexity                  fast, automatic, shallow    │
  │  4c. BLEU / ROUGE                fast, automatic, n-gram     │
  │  4d. BERTScore                   automatic, embedding-based  │
  │  4e. Benchmarks (MMLU, GSM8k …)  automatic, task-specific    │
  │  4f. LLM-as-a-judge              automatic, flexible         │
  │  4g. Human evaluation            slow, gold-standard         │
  └──────────────────────────────────────────────────────────────┘
        cheap, shallow                       expensive, deep
```

The rest of Section 4 walks down that pyramid. None of these tools is sufficient on its own; together they give you a multi-angle picture, much like a doctor ordering several different tests to triangulate a diagnosis.

### 4b. Perplexity — How Surprised Was the Model?

Picture yourself reading a book in a language you mostly understand. As you read each word, you subconsciously predict what is likely to come next. When the book uses common phrasings, the next word matches your prediction and you breeze through with no surprise. When the book uses unexpected word choices, you feel a small jolt — the word you saw was not one you were predicting. **Perplexity** measures exactly this jolt-density for a language model reading a text.

A low-perplexity model assigns high probability to each next token as it reads — it is not surprised, because the text makes sense given what it has learned. A high-perplexity model assigns low probability to many of the tokens it sees — it is consistently confused. Formally:

$$\text{PPL}(W) = \exp\!\left(-\frac{1}{N}\sum_{i=1}^{N} \log P_\theta(w_i \mid w_1, \ldots, w_{i-1})\right)$$

| Symbol | Meaning |
|--------|---------|
| $W = (w_1, \ldots, w_N)$ | The sequence of $N$ tokens being evaluated |
| $P_\theta(w_i \mid w_1, \ldots, w_{i-1})$ | Model's predicted probability for token $w_i$ given all prior tokens |
| $\frac{1}{N} \sum_i \log P_\theta(\ldots)$ | Average log-probability across the sequence |
| $\exp(\cdot)$ | Exponentiation, converting from log-space back to a natural scale |

This says: compute the average log-probability the model assigns to each true token, negate it so that higher probability gives a smaller score, and exponentiate. **Lower perplexity is better.** A perplexity of $k$ means the model behaved as if choosing uniformly among $k$ equally likely tokens at each step. A perplexity of 1 means the model was completely certain at every step. A perplexity of 10 means it was, on average, hesitating among 10 options.

There is a useful shortcut connecting perplexity to the training loss you stare at in console logs:

$$\text{PPL} = \exp(\text{average cross-entropy loss})$$

So a training loss of $1.5$ corresponds to perplexity $e^{1.5} \approx 4.5$. The two are the same quantity, viewed through different lenses — log-space for training stability, exponential-space for human interpretability.

**Dry-run — perplexity on a 3-token sequence:**

```
Sentence: "The cat sat"
N = 3 tokens

Model assigns the following probabilities to each true next-token:
  P("The")                = 0.20
  P("cat"  | "The")       = 0.15
  P("sat"  | "The cat")   = 0.30

Step 1 — log-probabilities of each true next token:
  log(0.20)  = −1.609
  log(0.15)  = −1.897
  log(0.30)  = −1.204

Step 2 — average negative log-probability (i.e., the cross-entropy loss):
  L  =  −( (−1.609) + (−1.897) + (−1.204) ) / 3
     =  −(−4.710) / 3
     =   1.570

Step 3 — exponentiate to get perplexity:
  PPL  =  exp(1.570)  ≈  4.81

Interpretation: on average, the model behaved as if choosing among
~5 equally likely tokens at each step. Lower is better.
```

The book illustrates perplexity with a memorable sentence (Figure 12-20): *"When a measure becomes a target, it ceases to be a good measure."* Given the context "When a measure becomes a", the model is asked how probable the next word *target* is — and a good language model should assign it high probability, given the famous Goodhart quote.

**What perplexity does not measure.** Perplexity only measures the model's *confidence* on a given reference text. It is silent on whether the model would be useful when actually generating. A model can have low perplexity on a held-out corpus while being completely wrong about facts, unable to follow instructions, or generating fluent nonsense. Perplexity is necessary but very far from sufficient for evaluating a generative model. (Citation: Jelinek et al., 1977.)

### 4c. N-gram Overlap Metrics — BLEU, ROUGE, and Their Limits

Think of grading a translation by counting how many phrases the student used that appear in the teacher's reference translation. This works when there is a clearly correct answer — as in translation between two languages with stable conventions. It falls apart the moment the student's translation is equally valid but phrased differently. **BLEU** and **ROUGE** are exactly this kind of phrase-counting metric.

**BLEU (Bilingual Evaluation Understudy)** — Papineni et al., 2002 — was designed for machine translation. It measures **precision** of n-grams: of all the n-grams in the generated text, how many also appear in the reference? Precision is computed separately for unigrams ($n = 1$), bigrams ($n = 2$), trigrams ($n = 3$), and 4-grams ($n = 4$), then combined into a single score:

$$\text{BLEU} = \text{BP} \cdot \exp\!\left(\sum_{n=1}^{4} w_n \log p_n\right)$$

| Symbol | Meaning |
|--------|---------|
| $p_n$ | Precision of n-grams (fraction of generated n-grams that appear in the reference) |
| $w_n$ | Weight for n-gram order $n$ (typically uniform, $w_n = 1/4$) |
| $\text{BP}$ | Brevity penalty — discourages very short generations that game precision |

**Tiny dry-run with unigram precision:**

```
Reference:  "the cat sat on the mat"          (6 unigrams)
Generated:  "the cat sat on a mat"            (6 unigrams)

For each generated unigram, does it appear in the reference?
  "the"  → yes
  "cat"  → yes
  "sat"  → yes
  "on"   → yes
  "a"    → no
  "mat"  → yes

Unigram precision  p_1  =  5 / 6  ≈  0.833

(Real BLEU uses clipped precision so a repeated word cannot be
matched more times than it appears in the reference. The principle
is the same.)
```

**ROUGE (Recall-Oriented Understudy for Gisting Evaluation)** — Lin, 2004 — is the recall-focused mirror image of BLEU, widely used in summarisation. Where BLEU asks "how much of what was generated appears in the reference?", ROUGE asks "how much of the reference appears in what was generated?" The arithmetic is symmetric; the philosophical difference is which side of the comparison is treated as ground truth.

**Where both metrics fail: paraphrasing.** Consider two semantically identical responses that share no words:

```
Reference:  "The cat sat on the mat"
Generated:  "A feline rested on the rug"

Shared unigrams: zero.
BLEU ≈ 0.   ROUGE ≈ 0.   Yet the meaning is essentially identical.
```

This is the fundamental limit of n-gram overlap: it counts surface-level word matches, not meaning. For machine translation between languages with stable conventions, this is acceptable. For open-ended chat generation, where the same idea can be expressed in dozens of valid ways, n-gram metrics consistently underestimate genuine quality. The next subsection introduces the metric that was designed to fix exactly this problem.

### 4d. BERTScore — Semantic Overlap via Embeddings

Imagine that instead of grading two essays by counting shared exact words, you ask a literature professor to read them and check whether they are talking about the same *concepts*. Two essays — one about "automobile manufacturing", one about "car production" — should score as highly similar even though they share no key words. **BERTScore** (Zhang et al., 2019) is the embedding-based metric that captures this intuition.

The mechanism is direct:

1. Tokenize the candidate text and the reference text.
2. Run each through BERT (or any contextual embedding model) to get a vector for every token.
3. For each candidate token, find the reference token with the highest cosine similarity to it.
4. Average those maximum similarities — that average is the BERTScore.

The precision-style version of the formula:

$$\text{BERTScore}_P = \frac{1}{|\hat{x}|} \sum_{\hat{x}_i \in \hat{x}} \max_{x_j \in x} \cos(e_{\hat{x}_i},\; e_{x_j})$$

| Symbol | Meaning |
|--------|---------|
| $\hat{x}$ | Set of tokens in the candidate (generated) text |
| $x$ | Set of tokens in the reference text |
| $e_t$ | BERT contextual embedding of token $t$ |
| $\cos(\cdot, \cdot)$ | Cosine similarity between two embedding vectors |
| $\max_{x_j}$ | For each candidate token, pick the closest reference token |

**Dry-run on the paraphrased example from 4c:**

```
Candidate:  "A feline rested"     (3 tokens)
Reference:  "The cat sat"         (3 tokens)

For each candidate token, find max cosine similarity to any reference token.
(Numbers below are illustrative — real BERT embeddings give close to these.)

  candidate "A"        → max sim with "The"  → cos = 0.45
  candidate "feline"   → max sim with "cat"  → cos = 0.85
  candidate "rested"   → max sim with "sat"  → cos = 0.78

  BERTScore_P  =  (0.45 + 0.85 + 0.78) / 3  ≈  0.69

For comparison: BLEU on the same pair  ≈  0.

BERTScore correctly recognises the semantic similarity that BLEU's
exact-word matching completely misses.
```

**Limitations.** BERTScore is computationally heavier (you need a BERT forward pass on every text being scored). It inherits BERT's training-language biases — it works less reliably on languages BERT was not heavily trained on. And, like BLEU and ROUGE, it still requires a *reference text*; it cannot score fully open-ended generation where there is no canonical "correct" answer.

### 4e. Public Benchmarks and the Overfitting Trap

Public benchmarks are the LLM equivalent of standardised tests like the SAT or GRE. They give a fast, broad, comparable signal about general ability. But the same dynamic that warps standardised testing — high-priced test-prep that teaches you the test rather than the underlying competence — warps LLM benchmarks too. The book's table of the most-used benchmarks:

| Benchmark | Full Name (and Paper) | What It Tests | Format |
|-----------|----------------------|--------------|--------|
| **MMLU** | Massive Multitask Language Understanding (Hendrycks et al., 2020) | 57 academic subjects — law, medicine, physics, history, … | 4-choice MCQ |
| **GLUE** | General Language Understanding Evaluation (Wang et al., 2018) | Similarity, entailment, grammaticality | Classification |
| **TruthfulQA** | (Lin, Hilton, Evans, 2021) | Whether the model parrots common human misconceptions | 817 questions |
| **GSM8k** | Grade-School Math 8k (Cobbe et al., 2021) | Multi-step arithmetic word problems | Open-answer |
| **HellaSwag** | (Zellers et al., 2019) | Common-sense plausibility of sentence completions | 4-choice MCQ |
| **HumanEval** | (Chen et al., 2021) | Generating a Python function from its docstring | 164 programming problems |

The **Open LLM Leaderboard** aggregates several of these benchmarks into a single composite ranking of open-source models. A model at the top is "generally considered the best open model at that time" — with one heavy caveat.

**Benchmark overfitting.** Because the benchmark questions are public, model developers can — deliberately or accidentally — let benchmark questions leak into their training data, or fine-tune specifically on the benchmark's question format until the model learns the *test* rather than the underlying *skill*. The benchmark score climbs without genuine capability improvement. This is **Goodhart's Law** in action, summarised in a quote the book takes pains to call out:

> "When a measure becomes a target, it ceases to be a good measure."  
> — Strathern (1997), restating Goodhart

A trivial extreme: a model fine-tuned to output only the single sentence "This is a sentence" would score perfectly on a grammar benchmark — and be useless for anything else. Less extreme but still real versions of this happen quietly all the time. The leaderboard is useful, but a leaderboard-topping model is not automatically the best model for *your* task.

Two further practical downsides of public benchmarks. First, they are broad — they tell you nothing about how the model performs on the specific use case you actually care about. A model that aces MMLU may flop on your medical chatbot. Second, running a full benchmark suite can take many GPU-hours, making iteration slow during development.

### 4f. LLM-as-a-Judge — Automated Pairwise Comparison

Imagine grading a cooking competition by counting how many ingredients each dish shares with a reference recipe. The counting would miss everything that matters — texture, balance, surprise, technique. Now imagine instead bringing in an expert chef who tastes each dish and tells you which is better and why. The chef judges dimensions no n-gram counter ever could. **LLM-as-a-judge** is the equivalent: replace the n-gram counter with a powerful LLM that *reads* candidate responses and rates them.

The methodology comes from Zheng et al. (2024), *"Judging LLM-as-a-judge with MT-Bench and Chatbot Arena"*. It has two flavours:

1. **Single-response scoring.** The judge sees one prompt and one response, and rates the response on a fixed scale (e.g., 1–10) against stated criteria like helpfulness, accuracy, clarity.
2. **Pairwise comparison.** The judge sees one prompt and *two* candidate responses, and must declare which response is better. Empirically more reliable, because relative judgements ("A is clearer than B") are easier and more consistent for humans and LLMs alike than absolute ratings ("A is a 7/10").

```
Pairwise evaluation example:

  Prompt:  "Explain gradient descent to a 10-year-old."

  Response A (Model X):
    "Gradient descent is an optimisation algorithm that minimises a loss
     function by iteratively adjusting parameters in the negative gradient
     direction until convergence..."

  Response B (Model Y):
    "Imagine you're blindfolded on a hilly landscape and you want to find
     the lowest valley. With each step, you feel which way the ground
     slopes downward and take a small step in that direction. Gradient
     descent works the same way!"

  Judge (GPT-4):  "Response B is significantly better for the target
                   audience. It uses a concrete, age-appropriate analogy,
                   while Response A uses technical language inappropriate
                   for a 10-year-old."

  → Model Y wins this comparison.
```

**Strengths.** LLM-as-a-judge scales easily — automatable, no humans in the loop. It works on fully open-ended generation, where there is no reference. And critically, it *improves automatically over time*: as judge models get better at general reasoning, evaluation quality goes up without any change to your eval pipeline.

**Biases to be aware of.** LLM judges have well-documented systematic biases that you must mitigate when designing an evaluation:

- **Length bias** — judges tend to prefer longer responses, all else equal.
- **Style bias** — judges prefer responses that match their own training style (often verbose, hedging, polite).
- **Position bias** — in pairwise comparison, the response listed first often wins regardless of content.
- **Self-preference** — GPT-4 systematically prefers GPT-4 outputs over equally good outputs from other model families.

Standard mitigations: shuffle response order across runs, average across multiple judges, use a different model family as judge than the one being evaluated.

### 4g. Human Evaluation and Chatbot Arena

A movie's true rating is not the score from professional critics — it is whether real audiences enjoy it. Critics give one signal; audiences give the ground truth. **Human evaluation** is the audience-polling equivalent for LLMs, and it remains the gold standard despite being the slowest and most expensive tool in the toolkit.

The most influential platform is **Chatbot Arena** (Chiang et al., 2024). The design is elegant in its simplicity:

```
The Chatbot Arena protocol:

  [User submits any prompt]
            │
            ▼
  Two anonymous LLMs receive the prompt in parallel
            │
            ▼
  User sees both responses (without model names)
            │
            ▼
  User votes for the better response
            │
            ▼
  Only after voting are the model names revealed
            │
            ▼
  Vote is recorded; aggregated into Elo ratings
```

The anonymity is doing a lot of work. By hiding model names until after the vote, Chatbot Arena eliminates brand bias — a vote for the better answer cannot be subconsciously influenced by "well, this came from GPT-4, so it must be better." The prompt variety is also a strength: real users ask real questions across a much wider distribution than any curated benchmark.

**The Elo rating system.** Originally designed for chess by Arpad Elo, Elo converts a sequence of pairwise wins and losses into a single rating per player (or, here, per model) that converges to reflect true relative skill. The update rule after one comparison between model $A$ and model $B$:

$$R'_A \;=\; R_A + K \cdot (S_A - E_A), \qquad E_A \;=\; \frac{1}{1 + 10^{(R_B - R_A)/400}}$$

| Symbol | Meaning |
|--------|---------|
| $R_A, R_B$ | Current Elo ratings of models $A$ and $B$ |
| $S_A$ | Actual result for $A$: $1$ (win), $0$ (loss), $0.5$ (tie) |
| $E_A$ | Expected probability that $A$ wins given the rating gap |
| $K$ | Sensitivity constant — how much one game can move a rating; chess uses $K = 16$–$32$ |
| $R'_A$ | New rating of $A$ after this comparison |

The key insight is the expected-score term $E_A$. If you beat someone rated much higher than you, your expected score was tiny ($E_A$ near $0$), so $S_A - E_A$ is large and your rating jumps. If you beat someone rated much lower, your expected score was already nearly $1$, so $S_A - E_A$ is tiny and your rating barely moves. The system rewards genuine upsets and ignores expected outcomes.

**Dry-run — one Elo update:**

```
Setup:
  Model A rating: 1500
  Model B rating: 1600   (B is rated 100 points higher than A)
  K = 32

Step 1 — expected probability that A wins:
  E_A  =  1 / (1 + 10^((1600 - 1500) / 400))
       =  1 / (1 + 10^0.25)
       =  1 / (1 + 1.778)
       =  1 / 2.778
       ≈  0.36

Step 2 — A actually wins the comparison: S_A = 1.

Step 3 — apply the update:
  R'_A  =  1500  +  32 × (1 - 0.36)
        =  1500  +  32 × 0.64
        =  1500  +  20.48
        ≈  1520

A gained ~20 points for beating a higher-rated opponent.
Had B won, A would have lost about 12 points (32 × 0.36).
```

At the time the book was written, Chatbot Arena had aggregated more than **800,000 human votes**. With that many comparisons spread across many model pairings, the statistical confidence of the resulting Elo rankings is very high.

**Limitations.** Votes accumulate slowly, so a brand-new model takes time to settle into a stable rating. Crowd preferences may not match your specific use case — Chatbot Arena's audience leans toward general chat, not specialised domains like medicine or law. And the anonymity, while eliminating brand bias, also makes it hard to evaluate aspects like privacy or licensing that the user might genuinely care about in deployment.

**The honest conclusion** of all of Section 4 is that there is no perfect evaluation. Word-level metrics are fast but shallow. Embedding metrics catch paraphrases but still need a reference. Benchmarks are comprehensive but gameable. LLM-as-a-judge scales but carries biases. Human evaluation is the ground truth but is slow and expensive. The book's own punchline is direct: *"we believe that you are the best evaluator."* For your specific use case, the most valuable evaluation you can run is to take the real prompts your users will actually send, run them through the model, and read the outputs yourself. No benchmark replaces that.

With evaluation tools in place, we can now meaningfully measure the gap between an instruction-tuned model and an aligned, preference-tuned model. Section 5 turns to closing that gap — preference tuning, the third and final stage of the LLM pipeline.

---

## 5. Preference Tuning and RLHF

We left Section 4 with an evaluated instruction-tuned model: it follows instructions, but it has no taste. Section 5 covers the third and final stage of the LLM pipeline — **preference tuning** — using the classical implementation known as **RLHF (Reinforcement Learning from Human Feedback)**. RLHF is the path used by the original ChatGPT, and even though it has been partly displaced by DPO (Section 6), understanding its moving parts is non-negotiable: DPO is best understood as the answer to "what is painful about RLHF, and how could we get the same result without that pain?"

### 5a. Why Instruction Tuning Is Not Enough — Taste vs Format

Imagine two doctors with identical factual knowledge, both explaining the same diagnosis. The first says: *"You have hypercholesterolaemia; your low-density lipoprotein levels exceed clinical thresholds and we recommend pharmacological intervention with HMG-CoA reductase inhibitors."* The second says: *"Your cholesterol is high. We should start you on a medication called a statin — it's safe, well-studied, and should bring it down within a few months."* Both are correct. Both follow the instruction "explain the diagnosis." But the patient leaves the first consultation feeling dismissed and the second feeling informed. Same knowledge, very different **taste** in how to deliver it.

After SFT, our model is the first doctor. It follows instructions and gives technically correct answers — but it has no sense of which way of being technically correct is *better*. Consider two responses to "What are large language models?":

*Response A*: "They are large language models." *(Technically correct, completely useless.)*

*Response B*: "Large language models are neural networks trained on vast amounts of text data to understand and generate human language. They learn statistical patterns across billions of words, enabling them to answer questions, write code, summarise documents, and engage in open-ended conversation."

An instruction-tuned model could produce either response — both are valid next-token-prediction sequences. SFT gives the model no mechanism to prefer B over A.

**Preference tuning** closes this gap. It does not add new knowledge — the model already knows how to write both responses. It teaches the cluster of qualities we want: depth, accuracy, appropriate length, helpfulness, honesty, safety. Crucially, none of these qualities is ever defined as a hard rule. The training signal is not "this answer is right" but "this answer is *better than* that one." The model learns taste by example.

The next subsections walk through classical RLHF in order: who does the scoring (5b), what the scorer looks like architecturally (5c), where the training data comes from (5d), how the scorer is trained (5e), how the LLM is then optimised against the scorer (5f), and the practical cost of doing all this (5g, which sets up Section 6).

### 5b. The Preference Evaluator — From Human Rater to Automated Judge

Imagine training a junior writer. After each piece they produce, you read it and give it a score on a 1–10 scale. They use that score to revise: high score, do more of the same; low score, try a different approach. This is the basic loop of preference tuning, and the entity that produces the score is called the **preference evaluator** (book Figure 12-22).

```
The preference evaluator loop:

  [Input prompt]
        │
        ▼
  [   LLM   ]  ──► [Generation A] ────┐
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │ Preference Evaluator│
                            │   (score: e.g. 4)   │
                            └─────────────────────┘
                                       │
                                       ▼
                Update the LLM based on this score:
                   high score → do more of this
                   low score  → do less of this
```

Now scale this up. Producing a useful training signal for a modern LLM requires *millions* of preference scores across the training run. You cannot have human raters score every example in every training step — it would take years and cost a fortune. So the field's pragmatic solution is **two-phase**: first humans label a relatively small set of preference pairs as ground truth; then we train a separate neural network — a **reward model** — to *imitate* the humans. From that point on, the reward model is the evaluator, scoring at GPU speed.

```
Two-phase scaling of the evaluator:

  Phase 1 — slow, small, expensive:
      Humans label ~10k–100k pairs of (prompt, response_A, response_B)
      with which one is preferred. This is the preference dataset.

  Phase 2 — fast, large, automatic:
      Train a reward model to imitate human judgments on the preference
      dataset. The reward model then provides scores at GPU speed for
      the millions of training steps that preference tuning requires.
```

This two-phase architecture is the heart of classical RLHF: humans bootstrap the reward, a reward model amortises it across the rest of training. The next subsection looks at how that reward model is actually built.

### 5c. The Reward Model — Anatomy and Architecture

A sommelier and a wine critic both taste the same glass. The sommelier *describes* the wine — "Black currant, hints of leather, well-balanced tannins" — that is the LLM, producing free-form text. The critic *scores* the wine on a 100-point scale — that is the reward model. Both share the same trained palate; they only differ in what they *output*. A score, not a description.

This is exactly how a reward model is built. Start with a copy of the instruction-tuned LLM. Remove the language modelling head — the linear layer that produces a probability distribution over the entire vocabulary. Replace it with a **regression head** (the book calls this a "quality classification head" in Figure 12-25): a single linear layer that outputs one scalar. Same transformer body, swapped terminal layer. The transformer's understanding of language is fully preserved; only the *output format* changes.

```
Standard instruction-tuned LLM:

  [Prompt + Response tokens]
         │
         ▼
  [Transformer Layers ×N]
         │
         ▼
  [Language Model Head]      ← shape: (vocab_size,), e.g. 32,000 logits
         │
         ▼
  Probability distribution over the next token

────────────────────────────────────────────────────────────────

Reward Model (same transformer body, swapped terminal layer):

  [Prompt + Response tokens]
         │
         ▼
  [Transformer Layers ×N]    ← weights initialised from the SFT model
         │
         ▼
  [Reward Head]              ← shape: (1,), a single scalar
         │
         ▼
  Quality score, e.g. −5.0 (poor) to +5.0 (excellent)
```

The reward model's input is the **prompt concatenated with a candidate response**. Its output is a single number indicating how good that response is for that prompt — higher means better. The score has no intrinsic unit; it is only meaningful by comparison. A score of +3 is "good" only because the reward model has learned to assign +3 to better-than-average responses and -3 to worse-than-average ones.

**Multiple reward models in parallel.** A common pattern at scale (book Figure 12-31): Llama 2 trained **two** reward models — one tuned to score *helpfulness*, another tuned to score *safety*. The two scores were combined during preference tuning. Different axes of "good" can pull in different directions (a maximally helpful response on how to commit a crime is not maximally safe), and a single reward model often blurs them. Splitting the dimensions makes the trade-off explicit and tunable.

### 5d. Building the Preference Dataset

Before we can train the reward model, we need data. The preference dataset is the bottleneck of the entire RLHF pipeline — its quality is a hard ceiling on the quality of the aligned model that comes out the other end. Each training example is a triplet (prompt, chosen response, rejected response):

```
A single preference-dataset example:

  prompt:   "Explain reinforcement learning in two sentences."
  chosen:   "Reinforcement learning is a paradigm where an agent learns
             by trial and error, receiving rewards for good actions and
             penalties for bad ones. Over time it learns a policy that
             maximises cumulative reward."
  rejected: "Reinforcement learning is a complex subfield of machine
             learning with many algorithms and applications. It is widely
             studied. A complete explanation would require much more space."
```

A crucial nuance the book underlines: the labels do **not** mean "good" versus "bad" absolutely. Both responses can be perfectly good — the chosen one is simply *better* than the rejected one for this prompt. This relative framing is what makes preference data so much richer than absolute 1–10 ratings. Humans are bad at giving consistent absolute scores (one rater's "8" is another's "6") but very good at the relative judgement "A is better than B."

**Where does the data come from?** The book's Figure 12-28 illustrates the standard pipeline:

```
How preference data is generated:

  [Input prompt]
         │
         ▼
  [   LLM   ]  ── generates two different responses ──┐
                                                       │
                       ┌───────────────────────────────┘
                       ▼
              [Generation A]  [Generation B]
                       │
                       ▼
            Human labeller is shown both
               and answers: "Which do you prefer?"

  The pair  (prompt, preferred, not-preferred)  becomes one training row.
```

Practical realities at scale:

- The two candidate generations typically come from the *same* model with different sampling temperatures or different random seeds — small variations are what make the pair informative.
- Some preference datasets use **crowd workers** (Anthropic's HH-RLHF), others use **expert annotators** (OpenAI's earlier work), and a growing number use **LLM-as-a-judge** (from 4f) to auto-generate labels and then quality-check a sampled subset with humans.
- A typical preference dataset has 10k–100k labelled pairs — much smaller than an SFT dataset, but proportionally more expensive per example because each example requires a comparative judgement.

### 5e. Training the Reward Model — The Bradley-Terry Loss

With the dataset assembled, we are ready to train the reward model. The objective uses the **Bradley-Terry model** for pairwise comparisons, originally developed in 1952 for sports rankings (and the same theoretical foundation underneath Elo from 4g). The core idea is to convert a *score difference* into a *probability* using the sigmoid function: if the chosen response really is better, the reward model should assign it a higher score than the rejected response, and the sigmoid of that gap should be close to 1. We minimise the negative log of that probability.

$$\mathcal{L}_{\text{RM}} \;=\; -\log \sigma\!\left(r_\theta(\text{prompt},\, y_w) \;-\; r_\theta(\text{prompt},\, y_l)\right)$$

| Symbol | Meaning |
|--------|---------|
| $r_\theta$ | Reward model with parameters $\theta$ |
| $y_w$ | The winning (chosen) response |
| $y_l$ | The losing (rejected) response |
| $r_\theta(\text{prompt},\, y)$ | Reward model's scalar score for response $y$ given the prompt |
| $\sigma(x) = 1 / (1 + e^{-x})$ | Sigmoid — squashes any real number into $(0, 1)$ |
| $\mathcal{L}_{\text{RM}}$ | Loss to minimise — pushes the gap between $r(y_w)$ and $r(y_l)$ wider |

Minimising this loss pushes the model to assign higher scores to chosen responses and lower scores to rejected ones — automatically, with no hard ceiling, no fixed scale, no specific target value.

**Dry-run — reward model training loss in two regimes:**

```
Example 1 — Model already distinguishes good from bad clearly:
  prompt:   "What is an LLM?"
  chosen:   "A large language model is a neural network trained on vast text..."
  rejected: "I don't know."

  r(chosen)    =  +5.2
  r(rejected)  =  −3.1

  diff    =  5.2 − (−3.1)        =   8.3
  σ(8.3)  =  1 / (1 + e^(−8.3))   ≈   0.9997
  loss    =  −log(0.9997)         ≈   0.0003   ← nearly zero; model is confident

Example 2 — Model barely distinguishes the two:
  r(chosen)    =  0.1
  r(rejected)  =  0.0

  diff    =  0.1 − 0.0            =   0.1
  σ(0.1)  =  1 / (1 + e^(−0.1))   ≈   0.525
  loss    =  −log(0.525)          ≈   0.644    ← large; model uncertain

Training keeps pushing r(chosen) higher and r(rejected) lower until
the gap is wide and the loss is small.
```

A subtle and important property of this loss: it does **not** care about either score's absolute value. Only the *gap* matters. A reward model that outputs $\{+1000, +990\}$ for chosen/rejected is just as happy as one that outputs $\{+5, -5\}$ — both have a wide gap. This is why reward-model scores have no intrinsic unit and are only comparison-meaningful.

Once trained, the reward model becomes the **automated preference evaluator**: feed it any `(prompt, response)` pair and it returns a quality score. That score is the training signal for the next stage.

### 5f. Proximal Policy Optimization (PPO) — Optimising Against the Reward Signal

With a reward model in hand, the natural next step is: take our instruction-tuned LLM, generate responses to a stream of prompts, score each with the reward model, and update the LLM to produce higher-scoring responses. This is **reinforcement learning**, and the specific algorithm used in classical RLHF — the one that trained the original ChatGPT in November 2022 — is **Proximal Policy Optimization (PPO)** (Schulman et al., 2017).

Think of PPO as coaching a comedian. You record each set, have an expert critic rate each joke on a 1–10 scale, and ask the comedian to deliver more of the high-rated jokes and fewer of the low-rated ones. With one important caveat: *do not change your style too radically in one rehearsal*. If some wild new style happens to fool the critic for one show, an unconstrained comedian would commit to it overnight. The "proximal" guardrail forces the style to evolve gradually, so the critic keeps catching obvious gaming and the underlying quality genuinely improves.

In RL vocabulary, the LLM is the **policy** $\pi$ — it maps a state (the conversation so far) to a distribution over actions (the next token). After the full response is generated, the reward model assigns a scalar reward. The policy is then updated to make high-reward responses more likely. The guardrail — the *"proximal"* in PPO — is a clipping mechanism on how much the policy is allowed to shift in one update step:

$$\mathcal{L}^{\text{CLIP}}(\theta) \;=\; \mathbb{E}\!\left[\min\!\bigl(\,r_t(\theta)\,\hat{A}_t,\;\; \text{clip}\bigl(r_t(\theta),\, 1-\epsilon,\, 1+\epsilon\bigr)\,\hat{A}_t\,\bigr)\right]$$

| Symbol | Meaning |
|--------|---------|
| $\pi_\theta$ | Current (trainable) policy — the LLM being updated |
| $\pi_{\theta_\text{old}}$ | Snapshot of the policy from before this update step |
| $r_t(\theta) = \dfrac{\pi_\theta(a_t \mid s_t)}{\pi_{\theta_\text{old}}(a_t \mid s_t)}$ | Ratio of new policy probability to old policy probability for action $a_t$ at state $s_t$ |
| $\hat{A}_t$ | Advantage estimate — how much better action $a_t$ turned out than the policy's average |
| $\epsilon$ | Clipping range, typically $0.2$ |
| $\text{clip}(r_t,\,1-\epsilon,\,1+\epsilon)$ | Cap the ratio between $1-\epsilon$ and $1+\epsilon$ |

The intuition behind the clip: suppose the new policy is putting much more probability on a token than the old policy did ($r_t > 1 + \epsilon$) and the advantage on that token is positive (it was a good move). The unclipped loss would keep rewarding bigger pushes on that token indefinitely. The clipped version says "you have already moved enough on this token this step — take the gain, but no more rewards for further pushes until next update." This caps the per-step policy change.

**Why does the clip matter so much?** Without it, PPO is prone to a failure mode called **reward hacking**. The policy discovers token sequences that fool the reward model into very high scores while producing semantic nonsense — the LLM equivalent of a student who memorises the grading rubric and writes essays that score full marks while saying nothing. Reward models are imperfect approximations of human judgement; given freedom to wander far from sensible language, the policy will eventually find their blind spots. The clip is a guardrail that keeps the policy close to its previous self each step, preventing it from sprinting off into reward-hacked regions before the reward model can be retrained.

### 5g. The Three-Model Memory Problem — Why PPO Hurts

PPO works — well enough to ship the most consequential AI product of the decade — but it is expensive in a very specific way: it requires *three* large models to be in GPU memory simultaneously.

```
PPO's GPU memory footprint:

  ┌──────────────────────────────────────────────────────────────┐
  │ ① Policy LLM (trainable)                                     │
  │     - the model being preference-tuned                       │
  │     - needs gradients + Adam state, just like in SFT         │
  ├──────────────────────────────────────────────────────────────┤
  │ ② Reference LLM (frozen)                                     │
  │     - a snapshot of the policy from before this update       │
  │     - needed to compute the probability ratio r_t(θ)         │
  │     - same architecture and size as the trainable policy     │
  ├──────────────────────────────────────────────────────────────┤
  │ ③ Reward Model (frozen)                                      │
  │     - scores every generated response                        │
  │     - typically same architecture and size as the policy LLM │
  └──────────────────────────────────────────────────────────────┘

For a 7B-parameter LLM under PPO that is roughly
   7B + 7B + 7B  =  21B parameters' worth of GPU memory,
before counting gradients and Adam state on the trainable copy.
```

Memory is only half the story. PPO is also notoriously **hyperparameter-sensitive**: the clip range $\epsilon$, the KL penalty between policy and reference, the value function used for advantage estimation, the learning rate, the batch size, the rollout length — all need careful joint tuning, and a poor choice on any one of them can cause the policy to collapse, drift into nonsense, or stall. PPO-based RLHF is the kind of stack that demands a small team of experienced ML engineers to make work consistently.

This combination — large memory footprint plus high tuning complexity plus a fundamentally clunky two-stage architecture (train a reward model, then optimise against it) — motivated a search for a simpler alternative. Could we somehow get the same alignment outcome **without** training a separate reward model, **without** reinforcement learning, and **without** holding three models in memory at once? Section 6 introduces the answer: **Direct Preference Optimization (DPO)**, an algorithm whose theoretical insight allows it to skip the reward model entirely while consuming roughly the same compute as a normal SFT run.

---

## 6. Direct Preference Optimization (DPO)

Section 5 left us with a working but expensive RLHF stack: train a reward model, then optimise the LLM against it with PPO, while juggling three large models in memory. **Direct Preference Optimization (DPO)** (Rafailov et al., 2023) is the algorithm that collapses that whole machinery into a single supervised-style loss. In under two years it went from a single paper to the default preference-tuning algorithm in nearly every open-source pipeline. This section explains why — first as an intuition, then as a short mathematical bridge from PPO, then as a concrete training step you could code by hand.

### 6a. The Core Insight — Your LLM Is Already a Reward Model

Imagine you have already trained a music critic to recognise good songs. Then someone says: "instead of using the critic as a separate judge whenever your composer writes something, what if the *composer's own preferences* — what they would naturally write — already encode the reward signal you need?" The composer's preferences, compared to a fixed snapshot of those preferences from before the latest round of training, *are* the reward. You don't need a separate critic at all.

This is the core insight of DPO. The paper's evocative subtitle: *"Your language model is secretly a reward model."* DPO observes that under the standard RLHF framework, the optimal policy implicitly defines the reward function it is being optimised against. Crucially, that implicit reward can be expressed *analytically* in terms of two things you already have available without any extra training:

1. The log-probabilities of the LLM you are training, $\pi_\theta$.
2. The log-probabilities of a frozen copy of that LLM from before training began, $\pi_\text{ref}$.

If the reward is available in closed form, you do not need to train a separate reward model. And if you do not have a reward model, you do not need reinforcement learning to optimise against one. The whole RLHF pipeline collapses to **two models** and a **standard supervised-style loss**.

Stripped to the punchline: PPO is what you get when you do not realise the LLM and the reward model can be the same object. DPO is what you get when you do.

### 6b. The Theoretical Bridge — How DPO Eliminates the Reward Model

How does DPO actually pull the reward model out of the loop? The bridge is short — three formal steps that go from "PPO's optimal solution" to "DPO's loss function." This subsection sketches the logic at the level you can follow without reading the full proof.

**Step 1 — The optimal RLHF policy is known in closed form.** Classical RLHF maximises expected reward under a KL constraint that keeps the policy from drifting too far from the reference:

$$\pi^*(y \mid x) \;=\; \arg\max_\pi \;\; \mathbb{E}\!\left[r(x, y)\right] \;-\; \beta \,\text{KL}\!\left[\pi(y \mid x) \,\|\, \pi_\text{ref}(y \mid x)\right]$$

| Symbol | Meaning |
|--------|---------|
| $r(x, y)$ | Reward model's score for response $y$ to prompt $x$ |
| $\pi(y \mid x)$ | Policy's probability of generating $y$ given $x$ |
| $\pi_\text{ref}$ | Reference (frozen) policy — the SFT model |
| $\beta$ | Temperature controlling how much $\pi$ may diverge from $\pi_\text{ref}$ |
| $\text{KL}[\pi \,\|\, \pi_\text{ref}]$ | Kullback–Leibler divergence — penalises drift from $\pi_\text{ref}$ |

This optimisation has a known closed-form solution:

$$\pi^*(y \mid x) \;=\; \frac{1}{Z(x)} \, \pi_\text{ref}(y \mid x) \, \exp\!\left(\tfrac{1}{\beta}\, r(x, y)\right)$$

where $Z(x)$ is a normalising constant (a "partition function") that makes $\pi^*$ sum to 1 over all possible responses $y$.

**Step 2 — Invert the relationship.** Solving for $r(x, y)$ in the expression above:

$$r(x, y) \;=\; \beta \,\log \frac{\pi^*(y \mid x)}{\pi_\text{ref}(y \mid x)} \;+\; \beta \,\log Z(x)$$

The reward is now expressed entirely in terms of *probability ratios* between the optimal policy and the reference policy — no neural-network reward model needed anywhere on the right-hand side.

**Step 3 — Substitute into the Bradley-Terry preference loss.** Recall from 5e that the reward model is trained on pairwise preferences using $\mathcal{L} = -\log \sigma\!\left(r(x, y_w) - r(x, y_l)\right)$. Substituting our analytical reward into that loss, and letting $\pi_\theta$ stand in for the (yet-unknown) optimal policy $\pi^*$ we are trying to learn:

$$\mathcal{L}_{\text{DPO}} \;=\; -\log \sigma\!\left(\,\beta \,\log \frac{\pi_\theta(y_w \mid x)}{\pi_\text{ref}(y_w \mid x)} \;-\; \beta \,\log \frac{\pi_\theta(y_l \mid x)}{\pi_\text{ref}(y_l \mid x)}\,\right)$$

The crucial cancellation: $\log Z(x)$ appears in both the chosen and the rejected terms with the same value, and the subtraction wipes it out. What remains depends only on the *trainable* policy $\pi_\theta$ and the *reference* policy $\pi_\text{ref}$. The reward model has vanished from the math.

```
The trick in one picture:

  PPO path:   preferences ── train ──► reward model ── RL ──► aligned policy
                                  ▲                       ▲
                                reward                reward model
                                model                 also held in GPU
                                trained               memory + sampled

  DPO path:   preferences ─────────── one loss ──────────► aligned policy
                                   (no reward model trained,
                                    no reward model held in
                                    GPU memory, no RL rollouts)
```

This is the bridge. From here on out, DPO is just supervised learning with a slightly clever loss function. The next subsections walk through what that looks like step by step.

### 6c. The Four Players in a DPO Step

Every DPO training step involves four components — three pieces of data and one extra model:

1. **The prompt** $x$ — the question or instruction (from the preference dataset).
2. **The chosen response** $y_w$ — the preferred answer.
3. **The rejected response** $y_l$ — the less preferred answer.
4. **The reference model** $\pi_\text{ref}$ — a frozen copy of the SFT model, never updated during DPO training.

Two LLMs are held in memory: the **trainable** model $\pi_\theta$ (with gradients and optimizer state) and the **frozen reference** $\pi_\text{ref}$ (no gradients). Both score the chosen response and the rejected response. The DPO loss then compares their scores:

```
A single DPO training step:

  prompt:    "What are LLMs?"
  chosen:    "Large language models are neural networks trained on vast text..."
  rejected:  "They are large."

           ┌──────────────────────────────────┐
           │   Reference Model π_ref (FROZEN) │
           │   (copy of the SFT model)        │
           └──────────────────────────────────┘
                          │
         ┌────────────────┴───────────────────┐
         ▼                                    ▼
  log π_ref(chosen | prompt)         log π_ref(rejected | prompt)

           ┌──────────────────────────────────┐
           │   Trainable Model π_θ             │
           │   (being preference-tuned)        │
           └──────────────────────────────────┘
                          │
         ┌────────────────┴───────────────────┐
         ▼                                    ▼
  log π_θ(chosen | prompt)            log π_θ(rejected | prompt)

                          │
                          ▼
                     DPO Loss:
       "Does π_θ prefer 'chosen' more, and 'rejected' less,
        than π_ref did?"

                          │
                          ▼
              Update π_θ only — π_ref stays frozen
```

**Why the reference model is required.** Without it as an anchor, the trainable model could maximise the chosen-response probability by *collapsing its entire distribution* onto a narrow handful of "preferred" patterns — forgetting most of what it learned during SFT. The reference is a stake in the ground: every update is measured *relative* to where the model started, not in absolute terms. The trainable model is allowed to drift, but only as much as $\beta$ (in the loss) allows.

### 6d. Token-Level Scoring — How the Probabilities Are Computed

The DPO loss writes $\pi_\theta(y \mid x)$ — the probability of an *entire* response $y$ given the prompt $x$. But responses are often 100+ tokens long. How is "the probability of a whole response" actually computed in practice? The answer (book Figure 12-33) is the standard chain-rule factorisation used by every autoregressive language model: the joint probability across tokens is the product of the per-token conditional probabilities, which becomes a sum once we take logs.

$$\log \pi(y \mid x) \;=\; \sum_{t=1}^{T} \log \pi(y_t \mid x,\, y_1,\, \ldots,\, y_{t-1})$$

| Symbol | Meaning |
|--------|---------|
| $y = (y_1, \ldots, y_T)$ | The response, tokenised into $T$ tokens |
| $\pi(y_t \mid x, y_{<t})$ | Model's probability for token $y_t$ given the prompt and the response so far |
| Sum over $t$ | Summing log-probs is the same as multiplying probabilities |

**Concretely** — to score the candidate response "I have no idea !" against the prompt "What are LLMs?":

```
Token-by-token scoring with the trainable model π_θ:

  Token 1: π_θ("I"     | "What are LLMs?")                 → log p_1
  Token 2: π_θ("have"  | "What are LLMs? I")               → log p_2
  Token 3: π_θ("no"    | "What are LLMs? I have")          → log p_3
  Token 4: π_θ("idea"  | "What are LLMs? I have no")       → log p_4
  Token 5: π_θ("!"     | "What are LLMs? I have no idea")  → log p_5

  log π_θ(response | prompt)  =  log p_1 + log p_2 + log p_3 + log p_4 + log p_5
```

The same computation is performed once with $\pi_\theta$ and once with $\pi_\text{ref}$, for both the chosen and the rejected responses. That gives **four forward passes total per training example**:

```
  Forward pass 1:  π_θ   over chosen      →  Σ log π_θ(chosen)
  Forward pass 2:  π_θ   over rejected    →  Σ log π_θ(rejected)
  Forward pass 3:  π_ref over chosen      →  Σ log π_ref(chosen)
  Forward pass 4:  π_ref over rejected    →  Σ log π_ref(rejected)
```

Those four scalars are then fed into the DPO loss in 6e — and that is the entirety of one training step.

### 6e. The DPO Loss Function with Dry-Run

Putting it all together, the DPO loss in its final form:

$$\mathcal{L}_{\text{DPO}} \;=\; -\log \sigma\!\left(\beta \,\log \frac{\pi_\theta(y_w \mid x)}{\pi_\text{ref}(y_w \mid x)} \;-\; \beta \,\log \frac{\pi_\theta(y_l \mid x)}{\pi_\text{ref}(y_l \mid x)}\right)$$

| Symbol | Meaning |
|--------|---------|
| $\pi_\theta(y \mid x)$ | Trainable model's probability of response $y$ given prompt $x$ |
| $\pi_\text{ref}(y \mid x)$ | Reference model's (frozen) probability |
| $y_w$ | The winning (chosen) response |
| $y_l$ | The losing (rejected) response |
| $\beta$ | Temperature — controls how aggressively $\pi_\theta$ may diverge from $\pi_\text{ref}$. Typical: $0.1$ |
| $\sigma(x) = 1/(1+e^{-x})$ | Sigmoid — squashes any real number into $(0, 1)$ |

Reading from the inside out: the term $\log\pi_\theta(y_w \mid x) - \log\pi_\text{ref}(y_w \mid x)$ measures how much *more* the trainable model now prefers the chosen response compared to where the reference started. The corresponding term for the rejected response measures how much *less* the trainable model now prefers the rejected response. The loss minimises when these two relative preferences move in opposite directions: chosen up, rejected down.

**The role of $\beta$.** Beta acts as a temperature on the relative preference. A *small* $\beta$ (e.g. $0.1$) makes the loss insensitive to the size of the log-ratios — the trainable model is allowed to wander further from the reference. A *large* $\beta$ (e.g. $1.0$) makes the loss very sensitive — even small drifts from the reference incur a meaningful loss. In practice $\beta$ is the leash: too short and the model cannot move enough to learn the preferences; too long and the model drifts from its instruction-following ability into reward-hacked territory.

**Dry-run — DPO loss with concrete log-probabilities:**

```
Prompt:    "Explain gradient descent simply."
Chosen:    "Imagine rolling a ball downhill — gradient descent always takes
            a step in the direction the ground slopes downward."
Rejected:  "Gradient descent computes the gradient of the loss and updates
            the parameters proportionally."

(Both are valid; chosen is better for a simple explanation due to the analogy.)

Reference model log-probabilities (forward passes 3 and 4):
  log π_ref(chosen   | prompt)  =  −12.4
  log π_ref(rejected | prompt)  =  −10.1   ← reference slightly prefers rejected
                                              (it sounds more textbook-like)

Trainable model log-probabilities, after some DPO training (passes 1 and 2):
  log π_θ(chosen   | prompt)    =  −10.0   ← trainable now prefers chosen more
  log π_θ(rejected | prompt)    =  −12.8   ← trainable now disfavours rejected

Log-ratio for chosen:
  log π_θ − log π_ref  =  −10.0 − (−12.4)  =  +2.4
  (trainable is 2.4 log-units more likely to generate chosen than ref was)

Log-ratio for rejected:
  log π_θ − log π_ref  =  −12.8 − (−10.1)  =  −2.7
  (trainable is 2.7 log-units less likely to generate rejected than ref was)

β = 0.1

Inner value  =  β × (ratio_chosen − ratio_rejected)
             =  0.1 × (2.4 − (−2.7))
             =  0.1 × 5.1
             =  0.51

σ(0.51)  =  1 / (1 + e^(−0.51))  ≈  0.625

Loss  =  −log(0.625)  ≈  0.470

As training continues:
  ratio_chosen rises    (trainable prefers chosen more)
  ratio_rejected falls  (trainable prefers rejected less)
  inner value grows  →  σ → 1.0  →  loss → 0
```

Notice that the shape of the dry-run is the *same* shape as the reward-model loss in 5e — sigmoid of a gap, then negative log of that. DPO inherits the comparative-judgement structure directly; the only difference is *what* is being compared. The reward model compared its own scalar outputs; DPO compares log-probability ratios between two LLMs.

### 6f. DPO vs PPO — Why DPO Won

The empirical and practical results were decisive within about a year of DPO's publication. By 2024, almost every open-source preference-tuning recipe was DPO-based, with PPO retained mostly in well-resourced labs that already had the RL infrastructure built.

| Dimension | PPO | DPO |
|-----------|-----|-----|
| Separate reward model required? | Yes — trained on preference data first | No — trained directly on preference data |
| Models in GPU memory simultaneously | 3 (policy, reference, reward model) | 2 (trainable, reference) |
| Training paradigm | Reinforcement learning with policy gradient | Supervised-style maximum likelihood |
| Training stability | Sensitive to hyperparameters; can collapse | Stable — behaves like SFT |
| Hyperparameters that actually matter | $\epsilon$ clip range, KL penalty, value function, LR, batch, rollout length | $\beta$, learning rate, batch size |
| Implementation complexity | High — needs full RL infrastructure | Low — standard gradient descent |
| Reward hacking risk | High — clip is the only guardrail | Low — anchored to reference at every step |
| Results quality | Baseline (used to train original ChatGPT) | Comparable or better on most benchmarks |

The most consequential row is "training paradigm." DPO reduces preference tuning to *something that looks like SFT* — log-probability ratios, sigmoid, gradient descent, no on-policy sampling during training, no value functions, no rollouts. Anyone who can run an SFT loop can run a DPO loop. The whole field of preference tuning suddenly inherits the stability and tooling of supervised learning.

DPO also benefits practically from QLoRA. Because the reference model is frozen (no gradients, no optimizer state) and the trainable LLM can be 4-bit-quantized with LoRA adapters on top (just like Section 3), the full DPO pipeline fits comfortably on a single consumer GPU. Section 7 will execute exactly this configuration end-to-end on TinyLlama.

### 6g. ORPO — Combining SFT and DPO in One Pass

DPO is a substantial simplification of PPO. But it still requires *two sequential training loops*: first SFT (to produce $\pi_\text{ref}$, the reference model) and then DPO (to produce the aligned model). Two training loops, two sets of hyperparameters, double the engineering surface area. Could we go further and fuse the two stages into one?

**Odds Ratio Preference Optimization (ORPO)**, introduced by Hong, Lee, and Thorne in 2024 — paper subtitle *"Monolithic Preference Optimization Without Reference Model"* — does exactly that. ORPO modifies the standard next-token-prediction SFT loss by adding a preference term based on the **odds ratio** between the chosen and rejected responses:

$$\mathcal{L}_{\text{ORPO}} \;=\; \mathcal{L}_{\text{SFT}} \;+\; \lambda \cdot \mathcal{L}_{\text{OR}}$$

| Symbol | Meaning |
|--------|---------|
| $\mathcal{L}_{\text{SFT}}$ | Standard SFT loss — cross-entropy on the chosen response |
| $\mathcal{L}_{\text{OR}}$ | Odds-ratio term — penalises the model for not preferring chosen strongly enough |
| $\lambda$ | Hyperparameter weighting the preference term against the SFT term |

The odds-ratio loss $\mathcal{L}_{\text{OR}}$ uses the *odds* of the model generating each response (the ratio $p/(1-p)$) and pushes the odds of the chosen response to be much higher than the odds of the rejected. Because the SFT loss and the odds-ratio loss are optimised together, the model learns to **follow instructions and prefer better responses simultaneously**, in one pass through one combined dataset.

Two practical consequences:

- **No reference model needed.** ORPO does not need a frozen reference because the SFT loss itself anchors the model to the supervised data. This drops the GPU footprint back down to *one* LLM (plus its gradients and optimizer state) — the cheapest setting of the three.
- **Full compatibility with QLoRA.** Because ORPO is "just" a modified SFT loss, every QLoRA trick from Section 3 transfers directly. You can run the full pipeline — instruction following plus preference alignment — in one training run on a 4-bit-quantized model on consumer hardware.

ORPO is newer than DPO, and at the time the book was written DPO remained the workhorse of open-source pipelines. But the trajectory is clear: each successive generation of preference-tuning algorithms strips away one more thing classical RLHF required — first the reward model (DPO), then the reference model and the two-loop structure (ORPO). The destination is single-loop, single-model preference tuning on the same hardware budget as ordinary SFT.

Section 7 takes the dominant of these three algorithms — DPO — and walks through a complete end-to-end run on TinyLlama, including the dataset format, the `DPOConfig` arguments, and the `DPOTrainer`'s subtle handling of the $\beta$ parameter.

---

## 7. Preference Tuning with DPO — Practical Walkthrough

Theory in hand, this section turns DPO into a working preference-tuning run on the same TinyLlama we instruction-tuned in Section 3. The structure deliberately mirrors that section: dataset → quantization → LoRA → training args → trainer → merge. Most of the moving parts are familiar; what is new is the *preference* nature of the data, the four-pass scoring loop from 6d running under the hood, and three small but important differences in the training configuration. Each subsection focuses on what differs from the SFT walkthrough rather than re-explaining the entire stack.

### 7a. The DPO Walkthrough Pipeline — Mirror of Section 3, with Preferences

Section 3 was like teaching an apprentice chef *how to cook*. Section 7 is like teaching them to cook *food customers prefer*. The kitchen is the same, the tools are the same, and most of the recipes carry over — but the training signal is different (preferences, not reference outputs) and the dataset is different (chosen vs rejected pairs, not instruction–response pairs).

The full DPO walkthrough has seven steps, and each step has a near-direct counterpart in Section 3:

```
              The DPO walkthrough pipeline:

  [1] Load preference dataset                                  (7b)
          │   (argilla/distilabel-intel-orca-dpo-pairs)
          ▼
  [2] Apply chat template + filter                             (7b)
          │   (status != tie, chosen_score ≥ 8, GSM8k contam.)
          ▼
  [3] Load the SFT-merged TinyLlama in 4-bit NF4               (7c)
          │   (BitsAndBytesConfig, exactly as in 3c)
          ▼
  [4] Attach a FRESH set of LoRA adapters                      (7d)
          │   (same LoraConfig as 3d, but a new run from zero)
          ▼
  [5] Configure DPO training hyperparameters                   (7e)
          │   (DPOConfig — like TrainingArguments, plus 2 new fields)
          ▼
  [6] Train with DPOTrainer                                    (7f)
          │   (beta is the new knob; four forward passes per step)
          ▼
  [7] Stack and merge BOTH SFT and DPO adapters                (7g)
          │
          ▼
       Aligned TinyLlama, ready to deploy
```

Below, each subsection focuses on what is *different* from the SFT walkthrough — there is no need to re-explain `BitsAndBytesConfig` or `LoraConfig` in detail.

### 7b. The Preference Dataset — distilabel-intel-orca-dpo-pairs

The training data comes from Argilla's `distilabel-intel-orca-dpo-pairs`. The base instruction set is Intel's Orca; Argilla regenerated responses with multiple models and used their `distilabel` LLM-as-judge pipeline to score and label which of each pair is preferred. Roughly 13,000 raw triplets, narrowed by filtering to roughly 6,000 high-confidence examples after preprocessing.

```python
from datasets import load_dataset

def format_prompt(example):
    """Format a DPO example using the TinyLlama chat template with a system turn."""
    system = "<|system|>\n" + example["system"] + "</s>\n"
    prompt = "<|user|>\n"   + example["input"]  + "</s>\n<|assistant|>\n"

    chosen   = example["chosen"]   + "</s>\n"
    rejected = example["rejected"] + "</s>\n"

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
        r["status"] != "tie"            # remove tied judgements
        and r["chosen_score"] >= 8      # keep only confidently-better chosens
        and not r["in_gsm8k_train"]     # avoid GSM8k contamination
    )
)

dpo_dataset = dpo_dataset.map(
    format_prompt, remove_columns=dpo_dataset.column_names
)
```

Two structural details deserve unpacking.

**The chat template uses three roles, not two.** Compared to Section 3, the format adds a `<|system|>` block carrying a system-level instruction. The full per-example template looks like this:

```
<|system|>
[system-level instruction]</s>
<|user|>
[user message]</s>
<|assistant|>
[chosen response]</s>

with the rejected response stored separately:
[rejected response]</s>
```

`DPOTrainer` expects three explicit string fields — `prompt`, `chosen`, `rejected` — not one concatenated `"text"` field as `SFTTrainer` did. That is why `format_prompt` returns a dictionary with those three keys and `remove_columns=dpo_dataset.column_names` strips out everything else, leaving the dataset with exactly those three columns.

**The filter step is doing real work.** Three filters, each addressing a real failure mode in raw preference data:

- `status != "tie"` — if the labeller could not pick a winner, the example sends a contradictory training signal (neither is strictly preferred). Drop it.
- `chosen_score >= 8` — keep only examples where the labeller was confident the chosen response was clearly better. Marginal preferences (chosen by a hair) are noisier and add little signal.
- `not in_gsm8k_train` — drop examples that overlap with the **GSM8k** benchmark's training set. If we later evaluate on GSM8k, the test should measure genuine reasoning, not memorisation of GSM8k-flavoured items. This is the benchmark-hygiene principle from 4e applied in practice.

After filtering, the book's run lands on roughly **6,000 examples** from an initial ~13,000 — about half the data deliberately thrown away in the name of quality.

### 7c. Loading the SFT-Merged Quantized Base Model

DPO starts from the SFT model we built in Section 3 — not from a fresh base TinyLlama. The book's pipeline reloads the SFT-adapted model, merges its LoRA into the weights, then prepares that merged model as the new "base" for the DPO stage.

```python
import torch
from peft import AutoPeftModelForCausalLM
from transformers import BitsAndBytesConfig, AutoTokenizer

# 4-bit quantization — identical to Section 3
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype="float16",
    bnb_4bit_use_double_quant=True,
)

# Load the SFT adapter ON TOP of the base, then merge it down
model = AutoPeftModelForCausalLM.from_pretrained(
    "TinyLlama-1.1B-qlora",           # ← the SFT adapter from Section 3
    low_cpu_mem_usage=True,
    device_map="auto",
    quantization_config=bnb_config,   # ← re-quantize for DPO memory budget
)
merged_model = model.merge_and_unload()

# Tokenizer setup — same as Section 3
model_name = "TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token   = "<PAD>"
tokenizer.padding_side = "left"
```

Two things to notice that differ from a fresh SFT run.

**We are re-quantizing a model whose weights already absorbed the SFT update.** In Section 3 we merged the SFT LoRA into float16 weights (3g) precisely so the merge would be lossless. Now we re-quantize that merged float16 checkpoint to 4-bit NF4 — once — and the new 4-bit grid is computed from the SFT-adjusted weights. That is the right time to quantize: after every update we want preserved has been baked in.

**The merged SFT model becomes the new "reference" $\pi_\text{ref}$ for DPO.** When `DPOTrainer` initialises in 7f, it internally snapshots the model we pass in to create $\pi_\text{ref}$. Whatever weights we feed in here are what $\pi_\text{ref}$ will be locked to for the rest of preference tuning. Hence the importance of merging the SFT adapter *before* DPO — if we left it unmerged, the DPO loss would compute log-probabilities relative to the *unmodified base TinyLlama*, and the "drift" being penalised would include the entire SFT update we worked so hard to install. We would essentially be undoing the SFT.

### 7d. LoRA Configuration for the DPO Stage

We now attach a **fresh** set of LoRA adapters on top of the SFT-merged model. These are not the same adapters from Section 3 — those are gone, baked permanently into the merged weights. The new adapters will accumulate the DPO update.

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

model = prepare_model_for_kbit_training(merged_model)
model = get_peft_model(model, peft_config)
```

The config is **identical** to the SFT LoRA config from 3d — same rank ($r = 64$), same alpha ($\alpha = 32$), same dropout ($0.1$), same seven target modules. The book deliberately uses the same hyperparameters across both stages so the only differences in the training run come from the *loss function* (DPO vs SFT) and the *training arguments* (next subsection).

A subtle practical detail: the new adapter is again initialised with $A$ random and $B = 0$ (from 2e), so at the very first DPO step the model's output is *identical* to the SFT-merged reference. The DPO loss therefore starts at its initial value — both $\pi_\theta$ and $\pi_\text{ref}$ produce the same probabilities, so $\log \pi_\theta - \log \pi_\text{ref} = 0$ for both chosen and rejected — and the loss grows from there as the adapter learns to bend the policy toward chosen responses and away from rejected ones.

### 7e. DPOConfig — Training Arguments for Preference Tuning

DPO uses `DPOConfig` rather than `TrainingArguments`, but `DPOConfig` is a thin subclass of `TrainingArguments` and shares almost every field. The book's settings:

```python
from trl import DPOConfig

training_arguments = DPOConfig(
    output_dir="./results",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    optim="paged_adamw_32bit",
    learning_rate=1e-5,          # ← 20× smaller than SFT's 2e-4
    lr_scheduler_type="cosine",
    max_steps=200,               # ← short illustrative run
    logging_steps=10,
    fp16=True,
    gradient_checkpointing=True,
    warmup_ratio=0.1,            # ← new: linear ramp-up over first 10% of steps
)
```

Three settings that differ meaningfully from the SFT configuration in 3e are worth understanding mechanistically.

**`learning_rate=1e-5` — a full order of magnitude smaller than SFT's `2e-4`.** Why so cautious? In SFT we were teaching the model a *fundamentally new behaviour* (follow instructions instead of pattern-completing), so large updates were appropriate — the model needed substantial change. In DPO we are making **subtle refinements** to a model that already follows instructions well. The model already speaks coherently; we are just nudging its *preference* between two coherent answers. Large updates would damage the SFT-acquired instruction-following while moving the preference needle only marginally — a bad trade. The QLoRA paper reports that higher learning rates only become preferable for very large bases (>33B parameters); for a 1.1B model, $1\text{e-}5$ is squarely in the right zone.

**`max_steps=200`** replaces SFT's `num_train_epochs=1`. With effective batch size $2 \times 4 = 8$, that is $200 \times 8 = 1{,}600$ training examples seen — well under one full epoch over the 6,000-example filtered dataset. The book explicitly describes this as "for illustration purposes." A full DPO run would last considerably longer. Using `max_steps` instead of `num_train_epochs` is the right pattern when you want an exact stopping point regardless of dataset size.

**`warmup_ratio=0.1`** is the only entirely new field. It linearly increases the learning rate from $0$ to $1\text{e-}5$ across the first $20$ steps ($10\%$ of $200$), then hands off to the cosine schedule for the remaining $180$ steps:

```
DPO learning-rate schedule with warmup_ratio = 0.1 and max_steps = 200:

  1e-5  │             ╭─╮
        │           ╱      ╲╮
        │         ╱            ╲
        │       ╱                  ╲╮
        │     ╱                          ╲╮
        │   ╱                                  ╲╮
        │ ╱                                          ╲╮___
     0  └─────────────────────────────────────────────────►  step
        0      20                                          200
        ↑                                                  ↑
     warmup (linear 0 → 1e-5)                  cosine decay
```

Why warmup matters *specifically* for DPO: at the very start, the trainable model and the reference are *identical* (because $B = 0$ in the freshly initialised LoRA, as we noted in 7d). The log-probability ratios are exactly zero, the DPO loss is at its initial value, and the gradient direction is being inferred from very noisy signal. A warm-up period lets the adapter pick up a coherent initial direction with tiny updates before full-strength steps amplify any noise into damage to the SFT-acquired capabilities.

### 7f. DPOTrainer and the Beta Parameter

With everything in place, `DPOTrainer` is the actual training engine. It is the preference-tuning equivalent of `SFTTrainer` from 3f, but under the hood it runs the four-forward-pass pattern from 6d.

```python
from trl import DPOTrainer

dpo_trainer = DPOTrainer(
    model,
    args=training_arguments,
    train_dataset=dpo_dataset,
    tokenizer=tokenizer,
    peft_config=peft_config,
    beta=0.1,               # ← the DPO temperature from 6e
    max_prompt_length=512,  # ← truncate the prompt at 512 tokens
    max_length=512,         # ← truncate the full prompt+response at 512 tokens
)

dpo_trainer.train()

dpo_trainer.model.save_pretrained("TinyLlama-1.1B-dpo-qlora")
```

Three DPO-specific parameters appear here that did not exist in `SFTTrainer`.

**`beta=0.1` — the $\beta$ from the DPO loss in 6e.** This is the single most important DPO-specific hyperparameter. Think of it as the leash length between $\pi_\theta$ and $\pi_\text{ref}$. Concrete effects across realistic values:

| $\beta$ | Behaviour |
|---------|-----------|
| $0.01$ – $0.05$ | Very loose leash; trainable model can drift substantially. Risk: catastrophic forgetting of SFT capabilities. |
| **$0.1$** | **Conventional sweet spot.** Enough freedom to learn preferences, tight enough to preserve SFT skills. Used by the book and most papers. |
| $0.5$ – $1.0$ | Tight leash. The model can move only fractionally from $\pi_\text{ref}$. Preferences are learned weakly but SFT skills are very safe. |

Mechanically: in the loss formula from 6e, a smaller $\beta$ shrinks the inner term $\beta(\text{ratio}_w - \text{ratio}_l)$ for a given log-ratio gap. That means a given drift from the reference produces less sigmoid response, less gradient pressure pushing further, and therefore *more* room to drift before the loss saturates. The leash analogy is exact.

**`max_prompt_length=512` and `max_length=512`** are two distinct truncation limits. `max_prompt_length` caps the system + user prompt; `max_length` caps the *whole sequence* (prompt + response). With both set to 512, a long prompt would leave very little room for the response — in production runs you typically set `max_length` higher than `max_prompt_length` to give responses room to breathe.

`DPOTrainer` does several things under the hood that are worth knowing:

1. **Creates the reference model automatically.** It snapshots a frozen copy of `model` at construction time (after `prepare_model_for_kbit_training` and `get_peft_model` have run), which becomes $\pi_\text{ref}$.
2. **Runs the four-pass scoring loop from 6d.** Every step: forward chosen and rejected through both $\pi_\theta$ and $\pi_\text{ref}$, sum log-probs token-by-token, plug into the DPO loss.
3. **Masks the prompt tokens.** Just like `SFTTrainer` masks user-turn tokens, `DPOTrainer` computes log-probabilities only over the response tokens on each side. The prompt's log-probability would cancel from the chosen-vs-rejected subtraction anyway, but explicitly masking saves compute.
4. **Saves only the LoRA adapter** when you call `save_pretrained` — a few tens of MB, just like in 3f.

### 7g. Stacking SFT and DPO Adapters into a Final Aligned Model

When DPO finishes, you have *two* LoRA adapter checkpoints on disk: `TinyLlama-1.1B-qlora` (the SFT adapter from Section 3) and `TinyLlama-1.1B-dpo-qlora` (the DPO adapter from 7f). For deployment, you typically want to fold both of them into the base weights to get a single standalone model with no PEFT overhead.

The merge is **iterative**: apply and merge the SFT adapter first, then load and merge the DPO adapter on top.

```python
from peft import AutoPeftModelForCausalLM, PeftModel

# Step 1 — merge the SFT adapter into the base model (in float16 for a clean merge)
sft_base = AutoPeftModelForCausalLM.from_pretrained(
    "TinyLlama-1.1B-qlora",
    low_cpu_mem_usage=True,
    device_map="auto",
)
sft_model = sft_base.merge_and_unload()
# sft_model has SFT baked in — no adapter overhead remaining

# Step 2 — load the DPO adapter on top of the merged SFT model, then merge again
dpo_peft_model = PeftModel.from_pretrained(
    sft_model,
    "TinyLlama-1.1B-dpo-qlora",
    device_map="auto",
)
final_model = dpo_peft_model.merge_and_unload()
# final_model has both SFT and DPO permanently merged in
```

```
Full pipeline — from base model to aligned assistant:

  TinyLlama Base Model (pretrained)
          │
          ▼
  ┌────────────────────────────────────────┐
  │  SFT with QLoRA                         │
  │  Dataset: UltraChat (3,000 examples)    │
  │  Learns: follow instructions            │
  │  Saved: TinyLlama-1.1B-qlora/           │
  └────────────────────────────────────────┘
          │
          ▼
  merge_and_unload()    ←  A·B fused into W for every targeted layer
          │
          ▼
  Instruction-Tuned Model (SFT baked in)
          │
          ▼
  ┌────────────────────────────────────────┐
  │  DPO with QLoRA                         │
  │  Dataset: distilabel-intel-orca pairs   │
  │  Learns: prefer helpful responses       │
  │  Saved: TinyLlama-1.1B-dpo-qlora/       │
  └────────────────────────────────────────┘
          │
          ▼
  merge_and_unload()    ←  DPO A·B fused into the SFT-merged weights
          │
          ▼
  Final Aligned Model
   ✓ Follows instructions     (from SFT)
   ✓ Prefers helpful answers  (from DPO)
   ✓ Zero PEFT overhead at inference time
```

The order matters conceptually: SFT is applied to the base, then DPO is applied on top. Reversing the merge order would not be wrong mathematically (matrix addition commutes), but it would diverge from the training order and would also misalign with the precision story — at each merge step we want to be in float16 so the addition is essentially lossless (3g), and that ordering is cleanest when we apply each adapter in the same order training did.

The two-stage pipeline is more powerful than either stage alone, but the costs are real:

- **Two training loops** — two `Trainer` invocations, two log streams to monitor, two checkpoints stored.
- **Two sets of hyperparameters** — SFT's LR, epochs, batch *and* DPO's LR, max_steps, warmup_ratio, beta.
- **Two debugging surfaces** — a problem visible at the end might trace back to either stage.

This is exactly the engineering overhead that motivated **ORPO** (6g): collapse both stages into a single training loop with a single dataset and a single set of hyperparameters, at the cost of a slightly more complex loss. For a from-scratch project today, ORPO is increasingly the right starting point. For projects that already have a strong SFT model and want to add preference alignment without redoing the SFT, the two-stage pipeline shown here remains the cleanest path.

That is the end of the pipeline. Starting from a base TinyLlama that could not follow instructions, we now have an aligned model that follows instructions, gives helpful responses, and prefers good answers over bad — built entirely on a single consumer GPU using QLoRA and DPO. Section 8 closes the chapter with the high-level takeaways.

---

## 8. Key Takeaways

The central arc of the chapter was the journey from a raw pretrained model — which knows the world but cannot use that knowledge — to an aligned assistant that follows instructions and prefers helpful answers over unhelpful ones. Every technique we met is the answer to a specific bottleneck on that journey. The seven subsections below distil the chapter into its load-bearing ideas and end with a decision guide and the foundational papers.

### 8a. The Three-Stage Pipeline — Three Problems, Three Stages

The foundational mental model. Every modern LLM is built in three stages, and each stage exists because the previous one left something unfixed:

| Stage | Trains on | Fixes |
|-------|-----------|-------|
| 1. Pretraining | Hundreds of billions of tokens of raw text | Gives the model language and world knowledge |
| 2. Supervised Fine-Tuning | Thousands of instruction–response pairs | Teaches it to *answer* rather than pattern-complete |
| 3. Preference Tuning | Thousands of chosen-vs-rejected pairs | Teaches *taste* — to prefer better answers among valid ones |

Pretraining provides the **knowledge**, SFT provides the **interface**, preference tuning provides the **character**. Stage 1 is done for us — every fine-tuning project starts from an open-source base model. Stages 2 and 3 are this chapter's work.

### 8b. The Pattern-Completion Problem Is Why SFT Exists

The single most useful insight for understanding base models: they do not answer questions, they *complete patterns*. Given the prompt "What is 1+1?", a base model is just as likely to continue with "2. What is 1+1+1? 3. What is 1+1+1+1? …" as with the answer "2", because the training corpus contains many more numbered problem lists than answer keys.

The base model is not stupid; it is loyal to its training distribution. SFT exists to overwrite *that loyalty* with a new behaviour — when you see question-shaped input, produce answer-shaped output. Crucially, SFT is **not** teaching the model new facts: it already knows the answer. SFT is teaching it the conversational format. This is why a few thousand SFT examples can change behaviour dramatically while changing knowledge almost not at all.

### 8c. PEFT and LoRA — Why 1% Is Enough

The most important empirical finding in fine-tuning: **you do not need to update every parameter**. Houlsby et al. showed that fine-tuning 3.6% of BERT's parameters reaches within 0.4% of the full-fine-tuning performance on GLUE. The reason is **intrinsic dimensionality** — the meaningful changes during fine-tuning live in a tiny subspace of the weight matrix; the remaining capacity goes unused.

**LoRA** operationalises this by parameterising the weight update as the product of two thin matrices:

$$W' = W + \frac{\alpha}{r} \cdot A \cdot B$$

The original $W$ stays frozen; only $A$ and $B$ train. For GPT-3-scale matrices ($d = 12{,}288$) at rank $r = 8$, this is a **768× reduction** in trainable parameters per matrix. $B$ is initialised to zero so training begins as an exact copy of the pretrained model. The $\alpha/r$ scaling keeps the magnitude of the update stable across choices of rank.

### 8d. QLoRA Democratised Fine-Tuning

LoRA shrunk the *trainable* parameters; **QLoRA** also shrunk the *base model* by storing it in 4-bit NormalFloat. Combined with blockwise quantization and double quantization, the two together collapse the GPU memory budget by an order of magnitude:

```
Memory to fine-tune a 7B model:

  Full fine-tuning (float32):   ~112 GB    ── multi-GPU cluster only
  Full fine-tuning (float16):   ~56 GB     ── one H100 (80 GB) barely fits
  LoRA on float16 base:         ~16 GB     ── one A100 / RTX 6000
  QLoRA (4-bit base + LoRA):    ~6–8 GB    ── one RTX 3090 / 4060
```

That last row — moving from a data-centre cluster to a gaming GPU — is the practical inflection point that brought open-source fine-tuning to ordinary developers in 2023. None of the other techniques in this chapter would have had the same impact without it.

### 8e. Evaluation Has No Silver Bullet

There is no single correct way to evaluate a generative model. Each tool has a sharp tradeoff between speed and reliability:

| Tool | Speed | Depth | Failure mode |
|------|-------|-------|--------------|
| Perplexity | Fast | Shallow | A confidently-wrong model can score very well |
| BLEU / ROUGE | Fast | Surface n-gram overlap only | Penalises valid paraphrases |
| BERTScore | Medium | Semantic, embedding-based | Still needs a reference; inherits BERT's biases |
| Public benchmarks | Slow | Task-specific | Goodhart's Law — benchmark overfitting |
| LLM-as-a-judge | Fast | Flexible, no reference needed | Length / style / position / self-preference biases |
| Human eval (Chatbot Arena) | Slow | Gold standard | Expensive; crowd preferences may not match your use case |

The unifying lesson is Goodhart's Law: *every metric you optimise against eventually becomes gameable*. The most honest evaluation you can run is to take the actual prompts your users will send, run them through the model, and judge the outputs yourself — the book's own punchline is "you are the best evaluator."

### 8f. From PPO to DPO to ORPO — The Simplification Trajectory

Each generation of preference-tuning algorithms strips away one piece of the previous stack:

```
PPO  (2017→2022):    policy + reference + reward model + RL infrastructure
                     ── 3 large models in GPU memory, RL hyperparameters
DPO  (2023):         policy + reference + supervised-style loss
                     ── 2 large models, no reward model, no RL
ORPO (2024):         policy alone + modified SFT loss + one training loop
                     ── 1 large model, no separate SFT step, no reference
```

The mathematical breakthrough behind DPO — that the optimal RLHF policy implicitly defines its own reward, so $r(x, y) = \beta \log \pi^*(y \mid x)/\pi_\text{ref}(y \mid x) + \beta \log Z(x)$ can be substituted into the Bradley-Terry loss with $\log Z(x)$ cancelling between chosen and rejected terms — eliminated the reward model from the math entirely. This is one of the most consequential simplifications in recent LLM research.

DPO is now the default for open-source preference tuning. ORPO is increasingly the right starting point for from-scratch projects because it collapses SFT and DPO into a single training loop with QLoRA compatibility.

### 8g. Decision Guide and Papers to Read

**Which technique to pick when:**

| Your situation | Recommended approach |
|----------------|---------------------|
| Maximum quality, 8-GPU cluster available | Full fine-tuning |
| Strong quality, one high-end GPU | LoRA on float16 base |
| Single consumer GPU | **QLoRA** (the chapter's workhorse) |
| Many fine-tuned variants of one base model | LoRA — share tiny adapters, keep one shared base |
| Preference tuning, RL infrastructure already exists | PPO (more flexible, harder to tune) |
| Preference tuning, want SFT-style simplicity | **DPO** (current default) |
| SFT + preference in one training loop | ORPO |
| Only a few hundred labelled examples | Stay with prompt engineering or RAG — fine-tuning needs at least a few thousand examples to beat them |

For *evaluation*, combine at least three tools: perplexity for development, a public benchmark for absolute calibration, and either LLM-as-a-judge or human eval on the actual prompts your users will send.

**Papers worth reading in full** once the conceptual scaffolding is in place:

- **Intrinsic Dimensionality** — Aghajanyan, Zettlemoyer, Gupta (2020). *"Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning."* arXiv:2012.13255.
- **Adapters** — Houlsby et al. (2019). *"Parameter-Efficient Transfer Learning for NLP."* PMLR.
- **LoRA** — Hu et al. (2021). *"LoRA: Low-Rank Adaptation of Large Language Models."* arXiv:2106.09685.
- **QLoRA** — Dettmers et al. (2023). *"QLoRA: Efficient Finetuning of Quantized LLMs."* arXiv:2305.14314.
- **PPO** — Schulman et al. (2017). *"Proximal Policy Optimization Algorithms."* arXiv:1707.06347.
- **DPO** — Rafailov et al. (2023). *"Direct Preference Optimization: Your Language Model is Secretly a Reward Model."* arXiv:2305.18290.
- **ORPO** — Hong, Lee, Thorne (2024). *"ORPO: Monolithic Preference Optimization Without Reference Model."* arXiv:2403.07691.
- **LLM-as-a-Judge** — Zheng et al. (2024). *"Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena."* NeurIPS.

Three further directions worth exploring beyond the chapter:

- **Continued pretraining** on domain text (medical, legal, code) before SFT, to push the base model's knowledge toward your target domain.
- **Constitutional AI** (Bai et al., 2022) — an alternative alignment scheme that uses AI feedback instead of human preferences.
- **DPO variants** — KTO, IPO, sDPO — each addresses a specific empirical weakness of vanilla DPO.

---

*Chapter 12 of Hands-On Large Language Models (O'Reilly) · Notes by sp-techv*
