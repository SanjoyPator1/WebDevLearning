## Table of Contents

- [0 — Understanding Data Types: float32, float16, bfloat16, int8, and NF4](#section-0)
  - [Why Does the Data Type Even Matter?](#why-does-the-data-type-even-matter)
  - [How a Floating Point Number is Built](#how-a-floating-point-number-is-built)
  - [The Four Types, Side by Side](#the-four-types-side-by-side)
    - [float32 — The Safe Default](#float32-the-safe-default)
    - [float16 — Half Precision (The Problematic One)](#float16-half-precision-the-problematic-one)
    - [bfloat16 — Brain Float 16 (Google's Solution)](#bfloat16-brain-float-16-googles-solution)
    - [int8 — 8-bit Integer](#int8-8-bit-integer)
    - [NF4 — NormalFloat 4-bit (The QLoRA Secret Weapon)](#nf4-normalfloat-4-bit-the-qlora-secret-weapon)
  - [Side-by-Side Summary](#side-by-side-summary)
  - [Where Each Type Appears in This Notebook](#where-each-type-appears-in-this-notebook)
- [1 - T1: LoRA Parameter Count Calculator](#section-1)
    - [The Core Concept](#the-core-concept)
    - [The Variables](#the-variables)
    - [Breaking Down the Formulas](#breaking-down-the-formulas)
    - [Walkthrough of the GPT-3 Example](#walkthrough-of-the-gpt-3-example)
- [2 - T1b: Manual LoRA Forward Pass](#section-2)
    - [1. The Standard Output ($Wx$)](#1-the-standard-output-wx)
    - [2. The LoRA Update ($\frac{\alpha}{r} \cdot ABx$)](#2-the-lora-update-fracalphar-cdot-abx)
    - [3. The Combined Output](#3-the-combined-output)
- [3 - T2: Linear Quantization From Scratch](#section-3)
    - [1. The Quantization Formula (Squishing the Float)](#1-the-quantization-formula-squishing-the-float)
    - [2. The Dequantization Formula (Reconstructing the Float)](#2-the-dequantization-formula-reconstructing-the-float)
    - [3. Walkthrough: The Normal Weights](#3-walkthrough-the-normal-weights)
    - [4. Walkthrough: The Outlier Problem](#4-walkthrough-the-outlier-problem)
    - [Result](#result)
- [4 - T3: Bradley-Terry Reward Loss From Scratch](#section-4)
    - [Step 1: The Gap ($r_{\text{chosen}} - r_{\text{rejected}}$)](#step-1-the-gap-r_textchosen---r_textrejected)
    - [Step 2: The Sigmoid ($\sigma$)](#step-2-the-sigmoid-sigma)
    - [Step 3: The Negative Log ($-\log$)](#step-3-the-negative-log--log)
    - [Walkthrough: The Two Scenarios](#walkthrough-the-two-scenarios)
- [5 - T4: Token-Level Log-Prob Aggregation](#section-5)
    - [1. The Core Concept: The Product Rule of Probability](#1-the-core-concept-the-product-rule-of-probability)
    - [2. The Problem with Multiplication](#2-the-problem-with-multiplication)
    - [3. The Math Hack: Taking the Log](#3-the-math-hack-taking-the-log)
    - [Walkthrough of the Task Scenarios](#walkthrough-of-the-task-scenarios)
      - [Scenario 1: The Confident Model](#scenario-1-the-confident-model)
      - [Scenario 2: The Confused Model](#scenario-2-the-confused-model)
    - [The Grand Strategic Picture](#the-grand-strategic-picture)
- [6 - T5: DPO Loss From Scratch](#section-6)
  - [T5: Direct Preference Optimization (DPO) Loss From Scratch](#t5-direct-preference-optimization-dpo-loss-from-scratch)
    - [The Variables](#the-variables)
    - [Breaking Down the Math (Step-by-Step)](#breaking-down-the-math-step-by-step)
      - [Step 1: The Ratios](#step-1-the-ratios)
      - [Step 2: The DPO Implicit Reward Gap](#step-2-the-dpo-implicit-reward-gap)
      - [Step 3: The Bradley-Terry Polish](#step-3-the-bradley-terry-polish)
    - [The Code Task Ahead](#the-code-task-ahead)
- [7 - Supervised Fine-Tuning with LoRA](#section-7)
  - [1.1 Dataset Preparation and Chat Templates](#11-dataset-preparation-and-chat-templates)
    - [The Big Picture: Training on Behavior, Not Language](#the-big-picture-training-on-behavior-not-language)
    - [Why is the Chat Template Crucial?](#why-is-the-chat-template-crucial)
    - [Breaking Down the Code Tasks](#breaking-down-the-code-tasks)
      - [1. Load the Tokenizer](#1-load-the-tokenizer)
      - [2. The formatting function: `format_prompt(example)`](#2-the-formatting-function-formatpromptexample)
      - [3. Dataset Manipulation Loop](#3-dataset-manipulation-loop)
  - [Extra](#extra)
    - [1. Are we just using it as a shortcut to insert the tags?](#1-are-we-just-using-it-as-a-shortcut-to-insert-the-tags)
    - [2. Does it turn the chat into numbers right away?](#2-does-it-turn-the-chat-into-numbers-right-away)
    - [3. Can we use our own custom chat template?](#3-can-we-use-our-own-custom-chat-template)
    - [4. Can we use a tokenizer from a completely different model?](#4-can-we-use-a-tokenizer-from-a-completely-different-model)
    - [1. The Tokenizer Dictionary is Pre-Baked](#1-the-tokenizer-dictionary-is-pre-baked)
    - [2. The Problem with Custom Text Templates](#2-the-problem-with-custom-text-templates)
    - [3. The Problem with Adding _New_ Special Tokens](#3-the-problem-with-adding-_new_-special-tokens)
    - [1. `load_dataset("HuggingFaceH4/ultrachat_200k", split="test_sft")`](#1-loaddatasethuggingfaceh4ultrachat200k-splittestsft)
    - [2. `.shuffle(seed=42)`](#2-shuffleseed42)
    - [3. `.select(range(3_000))`](#3-selectrange3000)
    - [The Final Code](#the-final-code)
- [8 - 1.2 Load Model in bfloat16](#section-8)
    - [1. The VRAM Math: Why `bfloat16`?](#1-the-vram-math-why-bfloat16)
    - [2. Loading the Base Model](#2-loading-the-base-model)
    - [3. The Padding Trick (Left vs. Right)](#3-the-padding-trick-left-vs-right)
  - [Extra terms](#extra-terms)
    - [1. Causal (Blind to the Future)](#1-causal-blind-to-the-future)
    - [2. Autoregressive (Eating its own tail)](#2-autoregressive-eating-its-own-tail)
    - [Seeing it in Action](#seeing-it-in-action)
    - [Why this breaks Right Padding](#why-this-breaks-right-padding)
- [9 - 1.3 LoRA Configuration](#section-9)
    - [1. The Power Dynamics: `r` and `lora_alpha`](#1-the-power-dynamics-r-and-loraalpha)
    - [2. The Injection Sites: `target_modules`](#2-the-injection-sites-targetmodules)
    - [3. The Missing Step (bfloat16 vs. QLoRA)](#3-the-missing-step-bfloat16-vs-qlora)
    - [4. The Hidden Gotcha: `enable_input_require_grads()`](#4-the-hidden-gotcha-enableinputrequiregrads)
- [10 - 1.4 Training Arguments](#section-10)
    - [1. The Effective Batch Size Trick](#1-the-effective-batch-size-trick)
    - [2. Gradient Checkpointing](#2-gradient-checkpointing)
    - [3. The Optimizer: `adamw_torch` vs. Paged](#3-the-optimizer-adamwtorch-vs-paged)
    - [Your Code](#your-code)
    - [1. `learning_rate=2e-4` (The Step Size)](#1-learningrate2e-4-the-step-size)
    - [2. `lr_scheduler_type="cosine"` (The Brakes)](#2-lrschedulertypecosine-the-brakes)
    - [3. `num_train_epochs=1` (The Read-Throughs)](#3-numtrainepochs1-the-read-throughs)
    - [4. `logging_steps=10` (The Heartbeat)](#4-loggingsteps10-the-heartbeat)
    - [5. `bf16=True` (The Math Engine)](#5-bf16true-the-math-engine)
    - [6. `save_strategy="steps"`, `save_steps=75`, `save_total_limit=3` (Crash Recovery)](#6-savestrategysteps-savesteps75-savetotallimit3-crash-recovery)
    - [7. `report_to="tensorboard"` (Live Training Dashboard)](#7-reporttotensorboard-live-training-dashboard)
- [11 - 1.5 Train and Save LoRA Weights](#section-11)
    - [1. The `SFTTrainer` vs. Standard Trainers](#1-the-sfttrainer-vs-standard-trainers)
    - [2. The Context Window: `max_seq_length=512`](#2-the-context-window-maxseqlength512)
    - [3. The Grand Finale: Saving the Weights](#3-the-grand-finale-saving-the-weights)
    - [Your Final Part 1 Code](#your-final-part-1-code)
    - [1. `model=model` (The Brain)](#1-modelmodel-the-brain)
    - [2. `train_dataset=dataset` (The Curriculum)](#2-traindatasetdataset-the-curriculum)
    - [3. `tokenizer=tokenizer` (The Translator)](#3-tokenizertokenizer-the-translator)
    - [4. `args=training_arguments` (The Physics Engine)](#4-argstrainingarguments-the-physics-engine)
    - [5. Why `peft_config` is NOT passed to `SFTTrainer` here](#5-why-peftconfig-is-not-passed-to-sfttrainer-here)
- [12 - 1.6 Merge Adapter and Run Inference](#section-12)
    - [The "Two-Brain" Problem (Before Merging)](#the-two-brain-problem-before-merging)
    - [The Solution: The Fusion Math](#the-solution-the-fusion-math)
    - [The Unloading Phase](#the-unloading-phase)
    - [The Final Test (Step 4)](#the-final-test-step-4)
    - [Your Code](#your-code)
    - [Why `AutoPeftModelForCausalLM` Works Here (and Why Part 2 Uses a Different Pattern)](#why-autopeftmodelforcausallm-works-here-and-why-part-2-uses-a-different-pattern)
    - [What `low_cpu_mem_usage=True` Does](#what-lowcpumemusagetrue-does)
- [13 - Part 2: Supervised Fine-Tuning with QLoRA](#section-13)
  - [2.1 Dataset Preparation and Chat Templates](#21-dataset-preparation-and-chat-templates)
    - [1. The "Q": What is 4-bit NF4?](#1-the-q-what-is-4-bit-nf4)
    - [2. The Trade-Off: The Two Extra Steps](#2-the-trade-off-the-two-extra-steps)
    - [3. Deja Vu: Section 2.1](#3-deja-vu-section-21)
- [14 - 2.2 Model Quantization — BitsAndBytes Config](#section-14)
    - [1. `load_in_4bit=True` (The Vault)](#1-loadin4bittrue-the-vault)
    - [2. `bnb_4bit_quant_type="nf4"` (The Smart Compression)](#2-bnb4bitquanttypenf4-the-smart-compression)
    - [3. `bnb_4bit_compute_dtype=torch.bfloat16` (The Unzipping Engine)](#3-bnb4bitcomputedtypetorchbfloat16-the-unzipping-engine)
    - [4. `bnb_4bit_use_double_quant=True` (The "Inception" Trick)](#4-bnb4bitusedoublequanttrue-the-inception-trick)
    - [The Tokenizer Reminder](#the-tokenizer-reminder)
- [15 - 2.3 LoRA Configuration](#section-15)
    - [The Problem: 4-Bit Math is Fragile](#the-problem-4-bit-math-is-fragile)
    - [The Solution: `prepare_model_for_kbit_training`](#the-solution-preparemodelforkbittraining)
    - [The Workflow Order](#the-workflow-order)
    - [⚠️ The Hidden Bug: `prepare_model_for_kbit_training` Wipes the Base Model Name](#the-hidden-bug-preparemodelforkbittraining-wipes-the-base-model-name)
- [16 - 2.4 Training Arguments](#section-16)
    - [The Star of the Show: `optim="paged_adamw_32bit"`](#the-star-of-the-show-optimpagedadamw32bit)
    - [Your Code](#your-code)
    - [The Updated Parameters vs Part 1](#the-updated-parameters-vs-part-1)
    - [`bf16=True` — Not `fp16=True`](#bf16true-not-fp16true)
    - [`save_steps=75` — Why 75 and not 50?](#savesteps75-why-75-and-not-50)
- [17 - 2.5 Train and Save QLoRA Weights](#section-17)
    - [The Key Differences from Part 1](#the-key-differences-from-part-1)
    - [Why NOT to pass `peft_config` to `SFTTrainer`](#why-not-to-pass-peftconfig-to-sfttrainer)
    - [`trainer.save_state()` — The Resumable Checkpoint](#trainersavestate-the-resumable-checkpoint)
    - [Your Code](#your-code)
    - [The Adapter Size](#the-adapter-size)
- [18 - 2.6 Merge Adapter and Run Inference (QLoRA)](#section-18)
    - [Why Not `AutoPeftModelForCausalLM` Here?](#why-not-autopeftmodelforcausallm-here)
    - [`AutoPeftModelForCausalLM` vs `PeftModel.from_pretrained` — When to Use Which](#autopeftmodelforcausallm-vs-peftmodelfrompretrained-when-to-use-which)
    - [Why Load in bfloat16 (Not 4-bit) for Inference?](#why-load-in-bfloat16-not-4-bit-for-inference)
- [19 — Part 3: Evaluating the Fine-Tuned Model](#section-19)
    - [The Four Metrics at a Glance](#the-four-metrics-at-a-glance)
- [20 — 3.1 Perplexity From Scratch](#section-20)
    - [The Formula](#the-formula)
    - [What the Number Actually Means](#what-the-number-actually-means)
    - [Your Code](#your-code)
    - [Reading the Results](#reading-the-results)
    - [The Key Limitation of Perplexity](#the-key-limitation-of-perplexity)
- [21 — 3.2 BLEU Unigram Precision](#section-21)
    - [The Formula (Unigram Version)](#the-formula-unigram-version)
    - [Your Code](#your-code)
    - [Why the Paraphrase Scores So Low](#why-the-paraphrase-scores-so-low)
    - [When BLEU Still Matters](#when-bleu-still-matters)
- [22 — 3.3 BERTScore Semantic Overlap](#section-22)
    - [The Idea](#the-idea)
    - [Cosine Similarity](#cosine-similarity)
    - [Your Code](#your-code)
    - [What the Toy Embeddings Show](#what-the-toy-embeddings-show)
    - [In Real Usage](#in-real-usage)
    - [BERTScore's Own Limitations](#bertscores-own-limitations)
- [23 — 3.4 Elo Update From Pairwise Wins](#section-23)
    - [Why Pairwise Comparison?](#why-pairwise-comparison)
    - [The Elo Rating System](#the-elo-rating-system)
    - [Your Code](#your-code)
    - [Reading the Two Scenarios](#reading-the-two-scenarios)
    - [Why Elo Is Hard to Game](#why-elo-is-hard-to-game)
- [24 — 3.5 Qualitative Comparison](#section-24)
    - [Why Qualitative Evaluation Can't Be Skipped](#why-qualitative-evaluation-cant-be-skipped)
    - [Three Prompt Types to Test](#three-prompt-types-to-test)
    - [What to Look For When Comparing](#what-to-look-for-when-comparing)
- [25 — Part 4: Preference Tuning with DPO](#section-25)
  - [What SFT Did — and What It Left Unfinished](#what-sft-did-and-what-it-left-unfinished)
  - [RLHF vs DPO — Two Ways to Learn from Preferences](#rlhf-vs-dpo-two-ways-to-learn-from-preferences)
  - [What the Loss Is Actually Doing — Step by Step](#what-the-loss-is-actually-doing-step-by-step)
- [26 — 4.1 DPO Dataset Preparation](#section-26)
  - [The Dataset: `argilla/distilabel-intel-orca-dpo-pairs`](#the-dataset-argilladistilabel-intel-orca-dpo-pairs)
  - [The Three Filters — Why Each One Matters](#the-three-filters-why-each-one-matters)
  - [The `format_prompt` Function](#the-formatprompt-function)
- [27 — 4.2 Load Quantized SFT Model](#section-27)
  - [Why DPO Starts from the SFT Model, Not the Base Model](#why-dpo-starts-from-the-sft-model-not-the-base-model)
  - [What This Cell Does](#what-this-cell-does)
- [28 — 4.3 LoRA Configuration for DPO](#section-28)
  - [Your Code](#your-code)
  - [⚠️ The `name_or_path` Fix Applies Here Too](#the-nameoror_path-fix-applies-here-too)
- [29 — 4.4 DPO Training Configuration](#section-29)
  - [`learning_rate=1e-5` — 20× Lower Than SFT](#learningrate1e-5-20-lower-than-sft)
  - [`warmup_ratio=0.1` — Specifically Critical for DPO](#warmupratio01-specifically-critical-for-dpo)
  - [`max_steps=200` — Short Demo Run](#maxsteps200-short-demo-run)
  - [Full Config](#full-config)
  - [`save_steps=50` — Why 50?](#savesteps50-why-50)
  - [`report_to="tensorboard"`](#reporttotensorboard)
- [30 — 4.5 Train with DPOTrainer](#section-30)
  - [The Four Forward Passes](#the-four-forward-passes)
  - [The `beta` Parameter](#the-beta-parameter)
  - [What Loss Looks Like During DPO Training](#what-loss-looks-like-during-dpo-training)
  - [Plotting the DPO Training Curve](#plotting-the-dpo-training-curve)
- [31 — 4.6 Stack and Merge Both Adapters](#section-31)
  - [Why Stack Adapters Instead of Training One Adapter for Everything?](#why-stack-adapters-instead-of-training-one-adapter-for-everything)
  - [The Two-Step Merge](#the-two-step-merge)
  - [What the Final Folder Structure Looks Like](#what-the-final-folder-structure-looks-like)
- [32 — 4.7 Final Aligned Model Inference](#section-32)
  - [What DPO Should Have Changed](#what-dpo-should-have-changed)
  - [Temperature Sampling](#temperature-sampling)
  - [The Definitive Test](#the-definitive-test)
  - [What We Actually Observed — Real Results from This Run](#what-we-actually-observed-real-results-from-this-run)
    - [What the loss curve told us](#what-the-loss-curve-told-us)
    - [Why small models behave this way](#why-small-models-behave-this-way)
    - [The Key Practical Lesson: Checkpoint Selection](#the-key-practical-lesson-checkpoint-selection)
    - [What You Would Do Differently on a Larger Model](#what-you-would-do-differently-on-a-larger-model)

<a id="section-0"></a>
# 0 — Understanding Data Types: float32, float16, bfloat16, int8, and NF4

Before anything else, let's build a solid mental model of data types. This chapter uses at least four of them, and the reason each is chosen where it is will make complete sense once you understand the foundation.

---

## Why Does the Data Type Even Matter?

Every number stored on your GPU occupies a fixed number of **bits** (binary digits — 0s and 1s). A bit is the smallest unit of computer memory. More bits = more precision = more memory.

Here's the core tension:

- **More bits** → more accurate numbers → more memory → slower training → costs more
- **Fewer bits** → less accurate numbers → less memory → faster training → costs less

For a model with **1.1 billion parameters** (like TinyLlama), the data type you choose has a massive real-world impact:

| Data type   | Bits per number | Bytes per number | TinyLlama-1.1B total |
| ----------- | --------------- | ---------------- | -------------------- |
| float32     | 32              | 4 bytes          | **4.4 GB**           |
| float16     | 16              | 2 bytes          | **2.2 GB**           |
| bfloat16    | 16              | 2 bytes          | **2.2 GB**           |
| int8        | 8               | 1 byte           | **1.1 GB**           |
| NF4 (4-bit) | 4               | 0.5 bytes        | **0.55 GB**          |

That's the reason this chapter obsesses over data types — a single choice cuts VRAM usage by up to 8×.

---

## How a Floating Point Number is Built

Before comparing types, you need to understand how a decimal number (like `3.14`) is actually stored as bits. Every floating-point format divides its bits into **three parts**:

```
┌──────────┬────────────────┬────────────────────────────────────────┐
│  Sign    │   Exponent     │             Mantissa                   │
│  1 bit   │   N bits       │             M bits                     │
│  +/-     │   "how big"    │  "the actual digits after the decimal" │
└──────────┴────────────────┴────────────────────────────────────────┘
```

Think of it exactly like scientific notation:

```
  3.14159  ×  10^6
  ───────     ───
  Mantissa    Exponent
```

- **Sign (1 bit):** Is the number positive (+) or negative (-)?
- **Exponent (N bits):** How big or how small is the number? This controls the **range** — how large the largest number can be, and how small the smallest non-zero number can be.
- **Mantissa (M bits):** What are the actual digits? This controls the **precision** — how many decimal places you can represent.

---

## The Four Types, Side by Side

### float32 — The Safe Default

```
 Sign  Exponent (8 bits)    Mantissa (23 bits)
  1   │ 0 1 1 1 1 1 1 1 │ 0 1 0 0 1 0 0 0 1 1 1 1 0 1 0 1 1 0 0 1 1 0 0
```

- **Total bits:** 32 (4 bytes)
- **Range:** ~1.2×10⁻³⁸ to ~3.4×10³⁸ (gigantic — almost nothing overflows)
- **Precision:** ~7 significant decimal digits
- **Used for:** PyTorch default weight initialization, optimizer states (Adam's momentum buffers), layer norms in QLoRA

**In plain English:** float32 is the "safe" format. It can represent enormous numbers and tiny numbers without breaking. The downside is it uses the most memory.

---

### float16 — Half Precision (The Problematic One)

```
 Sign  Exponent (5 bits)   Mantissa (10 bits)
  1   │ 0 1 1 1 1 │ 0 1 0 0 1 0 0 0 1 1
```

- **Total bits:** 16 (2 bytes)
- **Range:** ~6×10⁻⁸ to **65,504** (very narrow — large numbers OVERFLOW to `inf`)
- **Precision:** ~3–4 significant decimal digits
- **Used for:** Older GPU training (pre-2020), NVIDIA T4/V100 inference

**The critical problem:** The exponent only has **5 bits**, which gives it a maximum value of about **65,504**. In deep learning, gradients during backpropagation can temporarily spike to much larger values. When a float16 number exceeds 65,504, it becomes `inf`. Once you have `inf` in your gradients, the entire training step is corrupted — your weights update to `nan` and training collapses. This is why float16 training requires a "gradient scaler" — a watchdog that constantly shrinks gradients down into the safe float16 range before the backward pass.

**The error you saw in this notebook:**

```
ValueError: Attempting to unscale FP16 gradients.
```

This happened when `fp16=True` was set but the model was actually in bfloat16. The gradient scaler designed for float16 tried to manage bfloat16 gradients and crashed.

---

### bfloat16 — Brain Float 16 (Google's Solution)

```
 Sign  Exponent (8 bits)    Mantissa (7 bits)
  1   │ 0 1 1 1 1 1 1 1 │ 0 1 0 0 1 0 0
```

- **Total bits:** 16 (2 bytes) — same memory as float16
- **Range:** Same as float32 (~3.4×10³⁸) — **gradient overflow problem SOLVED**
- **Precision:** ~2–3 significant decimal digits — lower than float16
- **Used for:** All modern GPU training (A100, RTX 30/40 series), this entire notebook

**Why does bfloat16 fix float16's problem?** Look at the bit layout — bfloat16 has **8 exponent bits** (same as float32), while float16 only has **5**. Google simply took float32, kept its full exponent, and shrank the mantissa from 23 bits down to 7. The result: same memory footprint as float16, but the gradient overflow problem is completely gone. No gradient scaler needed.

**The trade-off:** Because the mantissa went from 10 bits (float16) to 7 bits (bfloat16), the decimal precision is slightly lower. For neural network training this doesn't matter — models are surprisingly tolerant of imprecise decimal digits, but they break catastrophically if the exponent range is too narrow.

**Visual comparison of all three:**

```
float32:   ─ ████████ ███████████████████████   (8 exponent + 23 mantissa)
float16:   ─ █████ ██████████                   (5 exponent + 10 mantissa)
bfloat16:  ─ ████████ ███████                   (8 exponent +  7 mantissa)
           │    │          └─ precision (more = better decimal accuracy)
           │    └──────────── range (more = can handle larger gradient spikes)
           └────────────────── sign
```

bfloat16 has the **same exponent column as float32**. That one design choice is why it replaced float16 for training.

---

### int8 — 8-bit Integer

```
 Sign  Value (7 bits)
  1   │ 0 0 1 0 1 1 0
```

- **Total bits:** 8 (1 byte)
- **Range:** -128 to 127 (whole numbers only — no decimals at all)
- **Used for:** Post-training quantization, fast inference on CPU/mobile, int8 training with bitsandbytes

**The key difference from everything above:** This is an **integer** format, not floating-point. There are no decimals. The number 3.7 would be stored as either 3 or 4. Neural network weights are small, smooth decimal numbers, so int8 is always used with a scaling factor that maps the full range of weights onto -128→127.

int8 is less common in this chapter — it's mainly used in the `LLM.int8()` method from bitsandbytes for efficient inference. QLoRA uses 4-bit NF4 instead.

---

### NF4 — NormalFloat 4-bit (The QLoRA Secret Weapon)

- **Total bits:** 4 (0.5 bytes)
- **Not a standard IEEE format** — it's a custom quantization scheme designed specifically for neural network weights

**The problem with naive 4-bit quantization:** With only 4 bits, you can represent just 16 distinct values (2⁴ = 16). If you spread those 16 values evenly across the range of a model's weights (say, -2.0 to +2.0), most weights will be poorly represented. Why? Because neural network weights follow a **bell curve (normal distribution)** — the vast majority of weights are clustered near zero, with very few extreme values near -2.0 or +2.0.

```
     Normal distribution of neural network weights:

          ████
        ████████
      ████████████
    ████████████████
  ████████████████████
 ████████████████████████
─────────────────────────────
-2.0   -1.0    0    +1.0   +2.0
```

**Naive 4-bit quantization** would space those 16 bins evenly:

```
  |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
-2.0                         0                                    +2.0
  ↑ Only a few weights here, but wasting bins         ↑ Only a few weights here too
```

Most bins would be nearly empty near the extremes. The dense region near zero gets very few bins → poor precision where it matters most.

**NF4's solution:** Place the 16 bins according to the **percentiles** of the normal distribution. More bins near zero (where most weights live), fewer bins at the extremes.

```
  | ||| |||||||||| ||| |
-2.0                  +2.0
  ↑ sparse         ↑ sparse
         ↑ dense bins where most weights actually are
```

This is why it's called _NormalFloat_ — it's a floating-point system optimised specifically for the normal distribution of neural network weights. The result: 4× less memory with almost no loss in model quality.

**The decompression step:** Because the GPU can't do calculus on 4-bit numbers, during the forward/backward pass `bitsandbytes` temporarily expands each 4-bit weight back to `bfloat16`, does the math, then immediately discards the expanded copy. The 4-bit version stays permanently in VRAM; only a tiny temporary slice is ever 16-bit at any moment.

---

## Side-by-Side Summary

| Format       | Bits | Memory (1.1B params) | Range       | Precision   | Key use                               |
| ------------ | ---- | -------------------- | ----------- | ----------- | ------------------------------------- |
| **float32**  | 32   | 4.4 GB               | Huge        | High        | Optimizer states, layer norms         |
| **float16**  | 16   | 2.2 GB               | Narrow ⚠️   | Medium      | Old training (needs GradScaler)       |
| **bfloat16** | 16   | 2.2 GB               | Huge ✅     | Medium      | Modern training — used in Parts 1 & 2 |
| **int8**     | 8    | 1.1 GB               | -128 to 127 | Low         | Fast inference / LLM.int8()           |
| **NF4**      | 4    | 0.55 GB              | Custom ✅   | Low (smart) | QLoRA base model storage              |

---

## Where Each Type Appears in This Notebook

| Notebook section             | Data type                               | Why                                                                                                                        |
| ---------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **1.2** — Model loading      | `torch.bfloat16`                        | Base model sits in VRAM in bfloat16                                                                                        |
| **1.4** — Training args      | `bf16=True`                             | Forward + backward pass run in bfloat16                                                                                    |
| **2.2** — BitsAndBytesConfig | `load_in_4bit=True` + NF4               | Base model stored in 4-bit to save VRAM                                                                                    |
| **2.2** — BitsAndBytesConfig | `bnb_4bit_compute_dtype=torch.bfloat16` | Dequantized to bfloat16 for the actual math                                                                                |
| **2.4** — Training args      | `bf16=True`                             | Same as Part 1 — training happens in bfloat16                                                                              |
| Optimizer states (all parts) | float32                                 | Adam's momentum/variance buffers stay in float32 inside the optimizer; `paged_adamw_32bit` makes these pageable to CPU RAM |

The one rule to remember: **whatever dtype you dequantize to in `bnb_4bit_compute_dtype`, you must match with `bf16=True` or `fp16=True` in your TrainingArguments.** Mismatching them is the exact cause of the `ValueError: Attempting to unscale FP16 gradients` error you hit.

---

<a id="section-1"></a>
# 1 - T1: LoRA Parameter Count Calculator

This is a great approach. Understanding the math before writing the code makes the actual implementation trivial.

Let's break down exactly what this task is asking you to do and why the math works this way, using the concepts from the chapter notes.

### The Core Concept

During full fine-tuning, if you want to update a neural network layer, you have to create a new matrix of "updates" ($\Delta W$) that is the exact same size as the original weight matrix ($W$). For modern LLMs, these matrices are massive squares.

LoRA's trick is saying, "We don't need a massive square matrix to learn this task. We can approximate that big square update by multiplying two very thin rectangular matrices together: Matrix $A$ and Matrix $B$".

### The Variables

- **$d$ (Dimension):** This is the size of the original, massive square weight matrix. For example, if $d$ is 2,048, the original matrix is a grid of 2,048 by 2,048 numbers.
- **$r$ (Rank):** This is the size of the "bottleneck". It dictates how thin those new $A$ and $B$ matrices are. A smaller rank means thinner matrices, which means fewer parameters to train.

---

### Breaking Down the Formulas

**1. Full Fine-Tuning Parameters**
If you update the whole original matrix, the number of parameters is simply the area of that square:

- **Formula:** $d \times d = d^2$
- **What it means:** This calculates the millions of weights you would have to train if you weren't using LoRA.

**2. LoRA Parameters**
Instead of the big square, LoRA creates two thin matrices:

- **Matrix A** has $d$ rows and $r$ columns, so it holds $d \times r$ parameters.
- **Matrix B** has $r$ rows and $d$ columns, so it holds $r \times d$ parameters.
- **Formula:** $(d \times r) + (r \times d) = 2dr$
- **What it means:** This is the actual number of weights your GPU will need to train.

**3. Compression Ratio**
This tells you how many times smaller your LoRA update is compared to a full fine-tuning update. You just divide the big number by the small number.

- **Formula:** $\frac{d^2}{2dr}$
- **Simplified Formula:** If you cancel out one of the $d$'s on the top and bottom, you get $\frac{d}{2r}$.

---

### Walkthrough of the GPT-3 Example

Let's look at the GPT-3 numbers provided in your notebook to see the math in action:

- **Given:** $d = 12288$, $r = 8$
- **Full FT params:** $12288 \times 12288 =$ **150,994,944** parameters
- **LoRA params:** $2 \times 12288 \times 8 =$ **196,608** parameters
- **Compression:** $150994944 / 196608 =$ **768.0**

By doing this math, you prove that LoRA shrinks the trainable parameters by exactly 768 times for this specific layer layer.

Your task is just to write a Python function that takes in `d` and `r`, calculates those three simple formulas, and prints them out nicely formatted!

<a id="section-2"></a>
# 2 - T1b: Manual LoRA Forward Pass

This is where the theory turns into real, executable math! You are essentially simulating exactly what happens inside a single layer of a neural network during a forward pass, just scaled down to a tiny $4 \times 4$ matrix.

Here is the breakdown of the three operations you need to compute, step-by-step.

### 1. The Standard Output ($Wx$)

This represents the prediction the original, unfrozen base model would make _without_ any fine-tuning.

- Mathematically, this is the dot product of the weight matrix $W$ and the input vector $x$.
- In NumPy, you can compute this using the matrix multiplication operator `@` or the `np.dot()` function.
- **Logic:** `standard_out = W @ x`

### 2. The LoRA Update ($\frac{\alpha}{r} \cdot ABx$)

This represents the new, task-specific behavior that your adapter has learned. There are two ways to calculate this in NumPy, and understanding the difference is the secret to why LoRA is so efficient:

**The Slow Way:** `(A @ B) @ x`
First, you multiply matrix $A$ ($4 \times 1$) by matrix $B$ ($1 \times 4$). This creates a full $4 \times 4$ matrix ($\Delta W$). Then, you multiply that massive new matrix by your input $x$. This requires a lot of math operations.

**The Fast Way:** `A @ (B @ x)`
First, you multiply matrix $B$ ($1 \times 4$) by the input vector $x$ ($4 \times 1$). This immediately collapses the math down to a single number (a scalar). Then, you multiply matrix $A$ by that single number. This is computationally incredibly cheap, and it is the exact reason LoRA saves so much memory and time!

Once you have that result, you multiply the whole thing by your scale factor ($\frac{\alpha}{r}$).

- **Logic:** `lora_update = scale * (A @ (B @ x))`

### 3. The Combined Output

This is the final result that gets passed to the next layer of the neural network. You simply take the base model's prediction and add the adapter's learned update on top of it.

- **Logic:** `combined = standard_out + lora_update`

Once you plug those three logic steps into your code block, the math will execute perfectly!

<a id="section-3"></a>
# 3 - T2: Linear Quantization From Scratch

This is a brilliant exercise because it mathematically proves exactly what we were just talking about with the "outlier problem" in QLoRA.

Here is the breakdown of the formulas and the logic before you write the code.

### 1. The Quantization Formula (Squishing the Float)

When we quantize, we are taking a highly precise decimal number and assigning it to an integer "bucket".

Let's look at the formula from the inside out:

$$q = \text{round}\!\left(\frac{x - x_{\min}}{x_{\max} - x_{\min}} \times (2^b - 1)\right)$$

- **The Range:** $x_{\max} - x_{\min}$ calculates the total "spread" between your highest and lowest weights.
- **The Percentage:** $\frac{x - x_{\min}}{x_{\max} - x_{\min}}$ calculates exactly where your current weight $x$ sits within that spread, returning a fraction between **0.0** and **1.0**.
- **The Max Bucket Index:** $2^b$ gives you the total number of buckets. Because we start counting at 0, the highest bucket number is $2^b - 1$. For **2 bits**, you have $2^2 = 4$ buckets total, so your bucket labels are `0, 1, 2, 3`. The multiplier here is **3**.
- **The Final Step:** You multiply the percentage by 3, and `round()` it to the nearest whole number to get your integer code $q$.

### 2. The Dequantization Formula (Reconstructing the Float)

The GPU can't do matrix math with the bucket numbers; it needs to "unpack" them back into floats. We just run the formula in reverse:

$$\hat{x} = \frac{q}{2^b - 1} \times (x_{\max} - x_{\min}) + x_{\min}$$

- **Reverse the Percentage:** $\frac{q}{2^b - 1}$ takes your bucket number (like `1`) and turns it back into a percentage (like $1/3 \approx 0.333$).
- **Scale it Back:** Multiply that percentage by the total spread ($x_{\max} - x_{\min}$) and add the starting point ($x_{\min}$) to slide the number back to its original scale.

### 3. Walkthrough: The Normal Weights

Let's trace one weight from step 1 of the task: **0.3**.
Your array is `[-1.2, 0.3, 0.7, 2.1]`.

- $x_{\min} = -1.2$
- $x_{\max} = 2.1$
- Spread = $2.1 - (-1.2) = 3.3$

**Quantizing 0.3:**

1. Percentage: $(0.3 - (-1.2)) / 3.3 = 1.5 / 3.3 \approx 0.454$
2. Bucket: $0.454 \times 3 = 1.36$
3. Round it: **1**

**Dequantizing Bucket 1:**

1. Percentage: $1 / 3 \approx 0.333$
2. Scale back: $0.333 \times 3.3 = 1.1$
3. Add minimum: $1.1 + (-1.2) = \mathbf{-0.1}$

**The Error:** The original weight was `0.3`. The reconstructed weight is `-0.1`. The error is **0.4**.

### 4. Walkthrough: The Outlier Problem

Step 3 asks you to add `50.0` to the array. Think about what this does to the formula:

- $x_{\max}$ is now **50.0**.
- The Spread is now $50.0 - (-1.2) = \mathbf{51.2}$.

If we try to quantize that same **0.3** weight again:

1. Percentage: $(0.3 - (-1.2)) / 51.2 = 1.5 / 51.2 \approx \mathbf{0.029}$
2. Bucket: $0.029 \times 3 = 0.08$
3. Round it: **0**

Because of one massive outlier, `0.3` got crushed into Bucket 0. In fact, `-1.2`, `0.3`, and `0.7` will _all_ round to Bucket 0. When you dequantize them, they will all come back as `-1.2`. Your error for `0.3` just skyrocketed from `0.4` to `1.5`!

This exercise perfectly proves why standard linear quantization destroys LLM precision and why QLoRA invented the "Blockwise" trick to quarantine outliers.

### Result

Spot on! This output is the absolute perfect mathematical proof of the "outlier problem."

Take a close look at exactly what happened in Step 3:
`Codes (2-bit): [0 0 0 0 3]`

Because that single `50.0` outlier stretched the ruler, your first bucket (Code `0`) now covers everything from `-1.2` all the way up to roughly `15.8`.

So, when the model looks at your carefully tuned weights of `0.3`, `0.7`, and `2.1`, it just throws them all into the `0` bucket. When the GPU tries to dequantize them later to do math, it just spits out `-1.2` for all of them. The unique signals of those weights are completely destroyed, which is exactly why standard linear quantization ruins language models.

By doing this from scratch, you've just proved exactly why we need the advanced tricks in QLoRA:

1. **Blockwise Quantization:** If we put `50.0` in its own block, it wouldn't ruin the buckets for the other four numbers.
2. **NF4:** If we spaced the buckets on a bell curve instead of evenly, we would have more buckets clustered near `0` to protect those small decimal numbers.

You have officially conquered the theory and manual math sections of the notebook! What does the next cell have in store? Is it time to start loading the real model with `bitsandbytes`?

<a id="section-4"></a>
# 4 - T3: Bradley-Terry Reward Loss From Scratch

Before we can understand DPO (Direct Preference Optimization), we have to understand the old-school way of doing things: training a **Reward Model**.

In classical RLHF, before you fine-tune your chatbot, you first train a separate "Judge" model. You give this Judge a prompt and two possible answers (one good, one bad). The Judge looks at both and spits out a score for each.

The **Bradley-Terry loss** is the mathematical formula used to train that Judge. Let's break down the formula from the inside out to see exactly how it forces the Judge to learn.

$$\mathcal{L}_{\text{RM}} = -\log \sigma\!\left(r_{\text{chosen}} - r_{\text{rejected}}\right)$$

### Step 1: The Gap ($r_{\text{chosen}} - r_{\text{rejected}}$)

The very first thing we do is subtract the bad response's score from the good response's score.

- If the Judge is smart, it gives the good response a 10 and the bad a 2. The gap is **+8**.
- If the Judge is confused, it might give the good response a 2 and the bad a 10. The gap is **-8**.
- **The Goal:** We want this gap to be as large and positive as possible.

### Step 2: The Sigmoid ($\sigma$)

Neural networks hate unbounded numbers like +8 or -8. We need to convert that gap into a **probability** (a percentage between 0% and 100% confidence). That is exactly what the Sigmoid function does.

- It takes any positive number and pushes it toward **1.0** (100% confidence the chosen is better).
- It takes any negative number and pushes it toward **0.0** (0% confidence).
- It takes exactly 0 and turns it into **0.5** (a 50/50 coin toss; the Judge has no idea).

### Step 3: The Negative Log ($-\log$)

In machine learning, "Loss" means "Error." A perfect model should have an error of **0**.
If our Sigmoid spits out `1.0` (100% confidence the Judge got it right), we need to turn that `1.0` into a `0` for the optimizer.

The negative log function is perfect for this:

- $-\log(1.0) = \mathbf{0}$ (Perfect! No error to penalize).
- $-\log(0.5) \approx \mathbf{0.69}$ (The Judge is guessing blindly. Slap it with an error!).
- $-\log(0.01) \approx \mathbf{4.6}$ (The Judge is confidently wrong. Slap it with a massive error!).

---

### Walkthrough: The Two Scenarios

Now let's look at the numbers you are about to code up to see this in action.

**Scenario 1: The Wide Gap**

- The Judge scores the chosen response **+5.2** and the rejected response **-3.1**.
- The Gap: $5.2 - (-3.1) = \mathbf{8.3}$. (The Judge is very confident!)
- Sigmoid of 8.3: **0.9997** (99.97% probability the chosen is better).
- $-\log(0.9997)$: **0.0003**
- _Result:_ The loss is basically zero. The optimizer says, "Great job, Judge, keep doing what you are doing. No weights need to be updated."

**Scenario 2: The Narrow Gap**

- The Judge scores the chosen response **+0.1** and the rejected response **0.0**.
- The Gap: $0.1 - 0.0 = \mathbf{0.1}$. (The Judge is basically shrugging its shoulders).
- Sigmoid of 0.1: **0.525** (Only a 52.5% probability. Just slightly better than a coin toss).
- $-\log(0.525)$: **0.644**
- _Result:_ The loss is high! The optimizer says, "You barely knew the difference. I am sending an error signal backward to update your weights so you don't guess next time."

This tiny formula is the engine that teaches AI how to have "taste" and prefer helpful answers over unhelpful ones. Whenever you are ready, go ahead and drop in your Python code for `bt_loss`! (Hint: `np.exp` and `np.log` will be your best friends here).

<a id="section-5"></a>
# 5 - T4: Token-Level Log-Prob Aggregation

This is the final math concept you need before we stitch everything together for the grand finale: the DPO loss! It answers a very practical question: **How does an LLM score an entire paragraph of text rather than just a single word?**

Let's break down the probability theory, the log trick, and the numbers you are about to code.

---

### 1. The Core Concept: The Product Rule of Probability

When an LLM is writing a response like `"I have no idea !"`, it doesn't choose the whole sentence at once. It predicts token-by-token.

According to basic probability theory, if you want to find the chance of multiple sequential events happening together, you **multiply** their individual probabilities:

$$\pi(y \mid x) = P(\text{"I"}) \times P(\text{"have"} \mid \text{"I"}) \times P(\text{"no"} \mid \text{"I have"}) \times \dots$$

### 2. The Problem with Multiplication

Imagine a realistic response that is 100 tokens long. If the model is 90% confident at every token, the calculation becomes $0.9 \times 0.9 \times 0.9 \dots$ one hundred times.

$$0.9^{100} = 0.00002656$$

By the time you get to the end of a long sentence, the product shrinks down into a tiny decimal with dozens of trailing zeros. Computers hate this. It triggers an error called **numerical underflow**, where the number becomes so close to zero that the computer's memory rounds it down to exactly `0.0`. Once your probability is `0.0`, your training loop completely breaks because you cannot do division or math on absolute zero.

### 3. The Math Hack: Taking the Log

To save the computer from breaking, we take the **Logarithm** of the probabilities.

A magical property of logarithms is that they convert multiplication into addition:

$$\log(A \times B) = \log(A) + \log(B)$$

So, instead of multiplying tiny raw probabilities, we can **sum up their log-probabilities**:

$$\log \pi(y \mid x) = \sum_{t=1}^{T} \log \pi(y_t \mid x,\, y_{<t})$$

Because log-probabilities are negative numbers (e.g., $\log(0.5) = -0.69$), adding them together just makes a larger negative number (like `-4.90` or `-14.50`). A computer can easily store `-14.50` without any memory or underflow issues!

---

### Walkthrough of the Task Scenarios

Now let's look at the numbers you are about to plug in to see how this measures model certainty.

#### Scenario 1: The Confident Model

This model feels comfortable with its output. Let's add its token log-probs:

- `(-1.20) + (-0.90) + (-1.40) + (-0.60) + (-0.80) = -4.90`
- To convert this back to a regular probability to show humans, we undo the log by using the exponent function ($e^{x}$):
- $e^{-4.90} \approx \mathbf{0.00744}$ (An overall sequence probability of about 0.74%).

#### Scenario 2: The Confused Model

This model is deeply unsure about this sentence path. It is stumbling through every word:

- `(-3.80) + (-2.50) + (-3.10) + (-2.90) + (-2.20) = -14.50`
- Let's convert this back to a regular probability:
- $e^{-14.50} \approx \mathbf{0.0000005}$ (An overall sequence probability of 0.00005%).

### The Grand Strategic Picture

As the notebook tip points out, during a single step of **DPO training**, your GPU will process four total sequences:

1. What the _Active Model_ thinks of the _Chosen response_ ($\log \pi_\theta(y_w \mid x)$)
2. What the _Active Model_ thinks of the _Rejected response_ ($\log \pi_\theta(y_l \mid x)$)
3. What the _Frozen Reference Model_ thinks of the _Chosen response_ ($\log \pi_{ref}(y_w \mid x)$)
4. What the _Frozen Reference Model_ thinks of the _Rejected response_ ($\log \pi_{ref}(y_l \mid x)$)

For each of those four, the model extracts the log-probs of every individual token, sums them up, and passes those four final numbers into the DPO loss function.

Your task is to implement `sequence_logprob(token_logprobs)` which handles this summation, and use `np.exp()` to decode it back into raw probabilities.

<a id="section-6"></a>
# 6 - T5: DPO Loss From Scratch

Got it! If NumPy is already imported globally in an earlier cell, then your code is **100% correct**.

`np.sum()` handles standard Python lists perfectly by converting them under the hood, so it will execute flawlessly and print out the exact values you need.

---

## T5: Direct Preference Optimization (DPO) Loss From Scratch

Now we arrive at the absolute peak of the theory section. DPO is a massive milestone because it completely removed the need to train a separate reward model (Judge) or deal with the unstable reinforcement learning loops of PPO.

The math looks intense, but it is actually beautifully elegant when you break it down into parts. Here is the DPO loss formula:

$$\mathcal{L}_{\text{DPO}} = -\log \sigma \left( \beta \log \frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)} - \beta \log \frac{\pi_\theta(y_l \mid x)}{\pi_{\text{ref}}(y_l \mid x)} \right)$$

Let's demystify what this formula is doing using the token aggregation concepts you just learned.

### The Variables

- $\pi_\theta$: Your **Active Model** (the LoRA adapters you are currently training).
- $\pi_{\text{ref}}$: Your **Reference Model** (the frozen base model before alignment).
- $y_w$: The winning (**chosen**) response.
- $y_l$: The losing (**rejected**) response.
- $\beta$: A scaling hyperparameter (usually set between `0.1` and `0.5`) that controls how much we penalize the model for drifting too far from the reference model.

---

### Breaking Down the Math (Step-by-Step)

Instead of looking at it as a giant equation, let's look at the two identical structures inside the sigmoid:

#### Step 1: The Ratios

Look at the first term: $\log \frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)}$.
Using logarithm rules, a log fraction is just subtraction:

$$\text{chosen\_logratio} = \log \pi_\theta(y_w \mid x) - \log \pi_{\text{ref}}(y_w \mid x)$$

- If this value is **positive**, it means your active model likes the chosen response _more_ than the starting model did. (Good behavior!)
- If this value is **negative**, it means your active model is starting to dislike the chosen response compared to where it started. (Bad behavior!)

The second term does the exact same calculation but for the **rejected** response:

$$\text{rejected\_logratio} = \log \pi_\theta(y_l \mid x) - \log \pi_{\text{ref}}(y_l \mid x)$$

#### Step 2: The DPO Implicit Reward Gap

Now, DPO subtracts the rejected log-ratio from the chosen log-ratio and scales it by $\beta$:

$$\text{implicit\_reward\_gap} = \beta \cdot (\text{chosen\_logratio} - \text{rejected\_logratio})$$

This is the absolute genius of DPO. The authors proved mathematically that this exact subtraction _behaves exactly like a reward model score gap_! By tracking whether the active model is pushing the chosen response up and the rejected response down relative to the baseline, the model implicitly creates its own internal reward signal.

#### Step 3: The Bradley-Terry Polish

Once you have that `implicit_reward_gap`, you pass it through the exact same Bradley-Terry loss pipeline you built in T3:

$$\mathcal{L}_{\text{DPO}} = -\log \sigma(\text{implicit\_reward\_gap})$$

---

### The Code Task Ahead

You are going to write a function `dpo_loss(logps_active_chosen, logps_ref_chosen, logps_active_rejected, logps_ref_rejected, beta=0.1)`.

The notebook asks you to calculate the loss for two scenarios:

1. **Alignment progressing well:** The active model is giving higher probabilities to the winning text and lower to the losing text compared to the reference model.
2. **Alignment regressing:** The active model is accidentally learning to prefer the bad answer over the good answer.

<a id="section-7"></a>
# 7 - Supervised Fine-Tuning with LoRA

## 1.1 Dataset Preparation and Chat Templates

We are officially moving from pure mathematics into building a real, executable Hugging Face pipeline.

This section transitions you from theoretical abstractions to real software design pattern engineering, laying the foundation for everything else in the notebook. Let’s break down exactly what this task is asking you to set up.

---

### The Big Picture: Training on Behavior, Not Language

As we discussed during the theory section, the base version of TinyLlama is an incredible "text-completer," but it has no concept of a conversational structure. If you type `"What is the capital of France?"`, it might complete it with `"What is the capital of Spain?"`.

Our goal in Part 1 is to use **Supervised Fine-Tuning (SFT)** to overlay conversational behavior onto the model. To do this, we are loading **3,000 conversational logs** from `UltraChat`.

### Why is the Chat Template Crucial?

An LLM doesn't actually see a separation between "User input" and "AI response." To the model's engine, it's just one massive, continuous string of text tokens. If we don't clearly demarcate who is speaking, the model won't learn _when_ it's supposed to sit quietly and read or _when_ it's supposed to open its mouth and generate text.

To fix this, every modern instruction-tuned model utilizes a **Chat Template**. This template inserts highly specific, invisible control tokens directly into the text sequence.

For TinyLlama, the template structure wraps text like this:

- `<|user|>`: Tells the model, "Pay attention, a human prompt starts here."
- `</s>`: The standard **EOS (End of Sequence)** token. It tells the engine, "The speaker is completely finished with this turn."
- `<|assistant|>`: Tells the model, "This is your turn! Start predicting next-tokens right after this marker."

---

### Breaking Down the Code Tasks

Here is exactly what you need to implement in the upcoming code cells:

#### 1. Load the Tokenizer

You will load the tokenizer using Hugging Face's `AutoTokenizer.from_pretrained()`.

- **Crucial Detail:** Even though we are fine-tuning a _base_ model, the instructions specify loading the tokenizer from the **`TinyLlama-1.1B-Chat-v1.0`** repository. Why? Because the _base_ model repository doesn't have a chat template configured in its settings, but the _Chat_ model repository does! We borrow the chat configuration from the chat tokenizer so we can train our base model to mimic it.

#### 2. The formatting function: `format_prompt(example)`

The raw `UltraChat` dataset stores its data as a nested list of dictionaries inside a column called `"messages"`:

```json
"messages": [
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there, how can I help you today?"}
]

```

Your function needs to take this row, feed the list of messages into the tokenizer's built-in utility: `tokenizer.apply_chat_template(example["messages"], tokenize=False)`, and return it under a new dictionary key named `{"text": ...}`. Setting `tokenize=False` ensures it returns a readable string rather than raw token IDs.

#### 3. Dataset Manipulation Loop

Using Hugging Face's `datasets` library, you will stitch together a standard pipeline:

- `.shuffle(seed=42)`: Shuffles the array randomly so the model doesn't get stuck learning patterns from the dataset's original layout order.
- `.select(range(3000))`: Slices off exactly the first 3,000 samples to keep your training fast and clean.
- `.map(format_prompt)`: Runs every single row in the dataset through your string formatter function, creating a brand new column named `"text"` that contains our perfectly structured, templated prompt strings.

When you execute this, printing out `dataset["text"][0]` will let you confirm visually that the raw user and assistant words are wrapped in TinyLlama's control tokens.

## Extra

Let's break down your specific questions one by one because they hit on the most important rules of fine-tuning:

### 1. Are we just using it as a shortcut to insert the tags?

**Yes, exactly.** Instead of writing our own messy Python code to inject `<|user|>` and `<|assistant|>` into 3,000 conversations, we are just borrowing the Chat model's tokenizer because it already has those exact insertion rules built into its configuration.

### 2. Does it turn the chat into numbers right away?

It _can_, but in this specific notebook step, **no**.
When you write the code for this step, you will use `tokenizer.apply_chat_template(..., tokenize=False)`.

- By saying `tokenize=False`, you are telling the tool: _"Just inject the tags and hand me back a readable text string so I can verify it looks right."_ \* The actual conversion into numbers (token IDs) will happen automatically inside the `SFTTrainer` engine right before the GPU does the math.

### 3. Can we use our own custom chat template?

**Yes!** If you didn't like TinyLlama's default `<|user|>` tags, you could absolutely write your own custom Jinja template string and force the tokenizer to use it. However, if you do that, you are forcing the model to learn a brand new conversational format from scratch, which might take more data and training time.

### 4. Can we use a tokenizer from a completely different model?

**Absolutely not. Never.** A tokenizer is essentially a dictionary that maps a specific word to a specific number.

- TinyLlama's tokenizer might map the word `"science"` to the number `405`.
- Mistral's tokenizer might map `"science"` to the number `9082`.

The base model's neural network weights are hardwired to its specific dictionary. If you swap the tokenizer, the text numbers will scramble, and the model will output pure gibberish. You **must** use the tokenizer built for your base model family.

**Important Point on 3 (extra explantion)**

The base model has never seen an instruction conversation before, so it has to learn _any_ template we give it from scratch.

So why did I say a custom template would take more time and data? It comes down to a hidden mechanical problem: **Token Fragmentation** and **Embedding Matrix Resizing**.

Here is why sticking to the official template is the "easiest" path for the base model to learn:

### 1. The Tokenizer Dictionary is Pre-Baked

When the creators built the TinyLlama Base model, they built a specific dictionary (the tokenizer) that locked in exactly 32,000 "words" (tokens).
Even though the Base model hasn't been fine-tuned on conversations yet, the creators _reserved_ specific, single-token spots in that dictionary for things like `<|user|>` and `<|assistant|>`.

- Because they are official special tokens, the tokenizer reads `<|user|>` as exactly **one single number** (e.g., Token ID 32001).
- It is very easy for a neural network to learn a rule that says: _"Whenever I see Token 32001, I act this way."_

### 2. The Problem with Custom Text Templates

If you decide to write your own custom template and use a string like `### HUMAN:` or `[User Input]:`, the official tokenizer doesn't have a reserved single-number spot for those exact phrases.

Instead, it chops your custom tag into "sub-words." `[User Input]:` might get chopped into five separate tokens: `[` + `User` + ` Input` + `]` + `:`.

- Now, instead of learning a single trigger token, the model has to learn: _"Whenever I see the exact sequence of Tokens 54, 892, 4012, 55, and 29... I act this way."_ \* Learning a complex, multi-step pattern takes significantly more training examples and epochs to memorize reliably.

### 3. The Problem with Adding _New_ Special Tokens

You might think, _"Okay, I'll just add `[HUMAN]` to the tokenizer as a brand new special token so it's a single number!"_

You can do this in Hugging Face, but it causes a massive structural issue. If the base model was built to understand exactly 32,000 tokens, and you add a 32,001st token, you have to resize the model's foundational weight matrix.

- That brand new token starts with **completely random, zero-knowledge math**.
- The rest of the model has read 3 trillion tokens of internet data, but this new token has read 0. Training a randomly initialized token from absolute zero to catch up with the rest of the model requires a massive amount of high-quality data.

**The TL;DR:**
By using the official Chat tokenizer's template, we are using special control tokens that are already cleanly defined as single concepts in the model's dictionary. It gives the base model the cleanest, simplest target to aim for during fine-tuning.

This code block is a classic Hugging Face data pipeline. It uses **method chaining**, meaning the output of one step flows directly into the next.

Let's break down exactly what each of those three lines is doing to your data.

### 1. `load_dataset("HuggingFaceH4/ultrachat_200k", split="test_sft")`

This line reaches out to the Hugging Face Hub and downloads the `UltraChat` dataset.

- **The Split:** Massive datasets are usually chopped into different "splits" (like `train`, `test`, `validation`). The author specifically chose the `"test_sft"` split, which contains about 23,000 high-quality conversational rows formatted perfectly for Supervised Fine-Tuning.

### 2. `.shuffle(seed=42)`

This takes those 23,000 rows and shuffles them like a deck of cards.

- **Why shuffle?** Datasets are often organized by topic or length. If the first 5,000 rows are all about math, and the next 5,000 are all about cooking, the model might "forget" math by the time it finishes learning about cooking. Shuffling ensures an even mix of topics.
- **Why `seed=42`?** By setting a seed, you "lock" the randomness. If you restart your notebook and run this cell again, it will shuffle the deck into the _exact same order_ every single time. This is critical for debugging—if your model breaks, you know it wasn't because you accidentally drew a weird batch of data.

### 3. `.select(range(3_000))`

This acts like a slice. It looks at your freshly shuffled deck of 23,000 rows and says, _"Just give me the first 3,000."_

- **Why not use all 23,000?** Because training an LLM is mathematically heavy and time-consuming. You are doing this on a single GPU. Since we are just trying to teach the model how to follow conversational _behavior_ (not trying to teach it brand new facts), 3,000 examples is the sweet spot. It is enough data to learn the pattern without making you sit at your computer for 12 hours waiting for the progress bar to finish!

### The Final Code

When you stitch it all together with the formatting function from the previous step, your complete code for this cell should look like this:

```python
from datasets import load_dataset

# Load, shuffle, and slice the dataset
dataset = (
    load_dataset("HuggingFaceH4/ultrachat_200k", split="test_sft")
    .shuffle(seed=42)
    .select(range(3000))
)

# Apply the template to every row
dataset = dataset.map(format_prompt)

# Print the first row to verify the template worked!
print(dataset["text"][0])

```

Give that a run! If everything worked, the printout should show a conversation neatly wrapped in `<|user|>` and `<|assistant|>` tags. Let me know if you hit any errors.

<a id="section-8"></a>
# 8 - 1.2 Load Model in bfloat16

This is a fantastic section. You are about to pull the actual "brain" of the AI into your GPU's memory.

Before we write the code, there are two major concepts hidden in this text block that are crucial to understand: **Precision Math** and **Padding Mechanics**. Let's break them down.

### 1. The VRAM Math: Why `bfloat16`?

When a neural network is trained from scratch by massive companies, they usually use **`float32`** (32-bit floating point numbers). This gives the highest mathematical precision, but each single number takes up **4 bytes** of memory.

If TinyLlama has 1.1 Billion parameters:
`1,100,000,000 * 4 bytes = 4.4 Gigabytes (GB)`

4.4 GB just to hold the frozen model is a lot, especially because during training, you also need memory for the LoRA adapter matrices, the optimizer states, and the data batches.

By telling Hugging Face to load the model in **`bfloat16`**, we chop the memory requirement exactly in half down to **~2.2 GB**. The model loses a tiny fraction of mathematical precision, but it is completely unnoticeable for text generation, and it gives your GPU plenty of room to breathe!

**Why `bfloat16` and not `float16`?** Both are 16-bit formats and use the same amount of memory, but they allocate their bits differently:

| Format     | Exponent bits | Mantissa bits | Dynamic range          | Precision |
| ---------- | ------------- | ------------- | ---------------------- | --------- |
| `float16`  | 5             | 10            | Narrow                 | Higher    |
| `bfloat16` | 8             | 7             | Wide (same as float32) | Lower     |

`bfloat16` has the same exponent range as `float32`, which means gradients are far less likely to overflow or underflow during the backward pass. `float16`'s narrow range causes gradients to go to zero (underflow) or infinity (overflow) which crashes training. Modern GPUs like the RTX A6000 support `bfloat16` natively, making it the standard choice for training today.

### 2. Loading the Base Model

Notice the repository name: `TinyLlama-1.1B-intermediate-step-1431k-3T`.
This proves exactly what we talked about in the last section! We are loading the raw, base model that has read 3 trillion tokens but has absolutely no idea how to have a conversation. We will use the Chat tokenizer's template to teach these raw weights how to behave.

### 3. The Padding Trick (Left vs. Right)

This is one of the most common stumbling blocks for beginners. The instructions say: `pad_token = "<PAD>"` and `padding_side = "left"`. Why?

**Why do we pad?**
GPUs are highly optimized to process matrices (perfect squares or rectangles). If you send a batch of two conversations to the GPU, and one is 10 tokens long but the other is 15 tokens long, the GPU throws an error. It needs them to be exactly the same length. So, we add "dummy" tokens (`<PAD>`) to the shorter one until it reaches 15.

**Why LEFT padding?**
Let's look at what happens if we pad on the right (the default behavior for many old models):

```text
Conversation 1: [Hello] [how] [are] [you] [?] [PAD] [PAD] [PAD] ➔ GENERATE NEXT TOKEN

```

Language models are **causal** (autoregressive). They predict the next word based on the _very last word_. If we pad on the right, the model looks at `[PAD]` and gets completely confused about what it is supposed to generate next!

By forcing **Left Padding**, we shift the dummy tokens to the front:

```text
Conversation 1: [PAD] [PAD] [PAD] [Hello] [how] [are] [you] [?] ➔ GENERATE NEXT TOKEN

```

Now, the actual last token of the conversation `[?]` sits exactly at the generation boundary. The model can seamlessly read the sentence and generate the response.

## Extra terms

These two terms sound like heavy academic jargon, but they actually describe a very simple, repetitive loop. They are the absolute foundational concepts of how models like GPT, Claude, and Llama actually work.

Let's break them down one by one.

### 1. Causal (Blind to the Future)

In statistics, "causal" means that the current step is strictly caused by the _past_ steps. The model is completely blind to the future.

If you ask a model to predict the 5th word in a sentence, it is only allowed to look at words 1, 2, 3, and 4. It cannot peek ahead. It is exactly like reading a book with an index card covering the rest of the page, sliding it down one word at a time.

### 2. Autoregressive (Eating its own tail)

- **Auto** = Self
- **Regressive** = Predicting a value based on previous values

An autoregressive model is one that takes its own newly generated output, glues it to the end of the original prompt, and feeds that whole chunk _back into itself_ as a new input to predict the next word. It builds the bridge while walking on it.

### Seeing it in Action

When you combine these two concepts, you get the standard LLM generation loop. If your prompt is **"The cat sat"**, here is exactly what the model does:

**Step 1:**

- **Input:** `[The] [cat] [sat]`
- **Action:** The model looks at the past (Causal) and calculates probabilities for the next word.
- **Output:** `[on]`

**Step 2 (The Autoregressive Loop):**

- **New Input:** `[The] [cat] [sat] [on]` _(It glued its last answer to the prompt)_
- **Action:** It looks at this new past sequence.
- **Output:** `[the]`

**Step 3:**

- **New Input:** `[The] [cat] [sat] [on] [the]`
- **Action:** It looks at the past again.
- **Output:** `[mat]`

This loop runs thousands of times per second until the model eventually predicts the `</s>` (End of Sequence) token, at which point it stops and prints the final paragraph to your screen.

### Why this breaks Right Padding

Now think about this causal, autoregressive loop in the context of our padding problem from earlier!

If you put padding on the right:

- **Input:** `[Hello] [how] [are] [you] [PAD] [PAD] [PAD]`
- **Action:** The model looks at its immediate causal past... which is `[PAD]`.

Because it is autoregressive, it thinks, _"The last three things I said were nothing. I guess I should keep saying nothing?"_ and it gets totally lost. By putting the padding on the left, the immediate causal past is the actual human question, and the loop can start cleanly.

<a id="section-9"></a>
# 9 - 1.3 LoRA Configuration

This is where the actual "LoRA" magic gets attached to the model. Up until now, your 2.2 GB TinyLlama model has been entirely frozen. If you tried to train it, PyTorch would throw an error because 0% of the weights are set to "trainable."

By creating a `LoraConfig` and passing it through `get_peft_model`, Hugging Face is going to surgically inject tiny, trainable matrices ($A$ and $B$) next to the frozen layers of the model.

Let’s break down the most important parameters in this configuration before you code it.

### 1. The Power Dynamics: `r` and `lora_alpha`

These two numbers control how "loud" your fine-tuning is.

- **`r=64` (Rank):** This determines the size of the trainable bottleneck matrices. A rank of 8 is considered small and fast, while 64 is considered quite large and expressive. By choosing 64, you are giving the adapters a lot of "memory capacity" to learn the complex conversational behaviors of the UltraChat dataset.
- **`lora_alpha=32` (Scale):** When the adapter ($A \times B$) generates a new signal, that signal is multiplied by a scaling factor before being added to the base model. The math for this scale is $\alpha / r$.
- Here, $32 / 64 = 0.5$.
- This means the output of your adapters is scaled by exactly half before merging. This prevents the new, untrained weights from violently overriding the base model's pre-trained knowledge during the first few steps of training.

### 2. The Injection Sites: `target_modules`

An LLM is made up of dozens of identical layers, and each layer has specific sub-modules. You are instructing the PEFT library to attach LoRA adapters to **all 7 linear projections** inside the transformer block:

- **The Attention Mechanism:** `q_proj`, `k_proj`, `v_proj` (Query, Key, Value) and `o_proj` (Output). This helps the model learn _where_ to pay attention in a conversational format.
- **The Feed-Forward Network:** `gate_proj`, `up_proj`, `down_proj`. These are the dense layers that act as the model's factual memory and logic center.

By targeting all 7, you are ensuring the model can adapt both its attention and its reasoning capabilities to the chat format.

### 3. The Missing Step (bfloat16 vs. QLoRA)

The instructions specifically point out that you do **not** need to call `prepare_model_for_kbit_training()`.

When working with standard `bfloat16` precision (like you are now), PyTorch inherently understands how to do math on the weights. The adapters can just be snapped on.

When you get to Part 2 and compress the model down to 4-bit (`QLoRA`), PyTorch cannot naturally do calculus on 4-bit numbers. That `prepare` function is required to cast the frozen 4-bit numbers back up to 16-bit just in time for the backward pass. Since you aren't doing 4-bit quantization yet, you get to skip that headache!

### 4. The Hidden Gotcha: `enable_input_require_grads()`

After calling `get_peft_model`, there is one more line you must add:

```python
model.enable_input_require_grads()
```

This line exists because of an interaction between **LoRA** and **gradient checkpointing** (which is turned on in section 1.4).

Here is the problem gradient checkpointing creates: instead of storing every intermediate calculation from the forward pass in memory, it throws most of them away and recomputes them on demand during the backward pass. This saves a huge amount of VRAM. However, PyTorch's recomputation mechanism only kicks in for a layer if at least one of its input tensors has `requires_grad=True`.

With LoRA, the base model's embedding layer is completely frozen — its output tensors have `requires_grad=False`. PyTorch sees no differentiable input, skips the checkpointing hooks, and then cannot reconstruct the gradient path during the backward pass. The result is a crash:

```
RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn
```

`enable_input_require_grads()` registers a forward hook on the embedding layer that forces its output to carry a gradient, even though the embedding weights themselves remain frozen. This gives gradient checkpointing the hook it needs to do its job, without unfreezing anything.

**Why don't you see this problem in Part 2 (QLoRA)?** Because `prepare_model_for_kbit_training` calls `enable_input_require_grads()` internally. In Part 1, since you skip that function, you must call it yourself.

<a id="section-10"></a>
# 10 - 1.4 Training Arguments

This is the control panel for your entire training engine! These arguments dictate exactly how the model will learn, how fast it will learn, and how it will manage your GPU's memory.

Before you write the code, let's look at the "Big Three" mechanical concepts hidden in this configuration, especially regarding memory. Even though you are sitting on a massive 48 GB A6000 and have VRAM to spare, these are the exact tricks engineers use to cram models onto much smaller 16 GB gaming GPUs:

### 1. The Effective Batch Size Trick

You are setting `per_device_train_batch_size=2` and `gradient_accumulation_steps=4`.

- The GPU will load **2** conversations, run the forward pass, and calculate the errors (gradients). But instead of updating the weights immediately, it just holds those numbers in memory.
- It does this **4** times in a row.
- After 8 total conversations ($2 \times 4$), it sums all the errors together and updates the weights once.
- **The Result:** You get the smooth, stable learning of a batch size of 8, but you only ever need enough VRAM to hold 2 conversations at a time!

### 2. Gradient Checkpointing

During a forward pass, the model normally saves every single intermediate math calculation in memory so it can reuse them during the backward pass. This takes up a monstrous amount of VRAM.

- Setting `gradient_checkpointing=True` tells the GPU: _"Don't save everything. Just save a few 'checkpoints.' If you need an intermediate number during the backward pass, just recalculate it on the fly."_ \* **The Trade-off:** It slows down training by about 20% (because it has to do the math twice), but it drastically reduces memory usage.

### 3. The Optimizer: `adamw_torch` vs. Paged

The optimizer is the algorithm that actually nudges the weights up and down based on the loss. `adamw_torch` is the gold standard.

- As the notebook tip points out, `adamw` keeps a "state" in memory for every single weight. Because you are using `bfloat16`, this state is very stable.
- When you get to Part 2 and compress the model to 4-bit, the math gets messy, and the optimizer can suddenly demand huge spikes of memory. If you were on a smaller GPU, that spike would crash your machine. A `paged` optimizer acts as a safety valve, temporarily shoving that extra memory into your CPU's normal RAM so the GPU doesn't suffocate.

---

### Your Code

Here is the exact implementation to define these rules for the Hugging Face trainer:

```python
from transformers import TrainingArguments

training_arguments = TrainingArguments(
    output_dir="./results/sft-lora",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    optim="adamw_torch",
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    num_train_epochs=1,
    logging_steps=10,
    bf16=True,
    gradient_checkpointing=True,
    save_strategy="steps",
    save_steps=75,
    save_total_limit=3,
    report_to="tensorboard",
)

```

Once you lock this in, you have everything you need to build the `SFTTrainer` (Supervised Fine-Tuning Trainer) and actually start the training loop!

Let's break down the rest of those arguments, because they are exactly what controls _how_ the AI learns.

Here is the breakdown of the remaining parameters:

### 1. `learning_rate=2e-4` (The Step Size)

The learning rate (0.0002) controls how drastically the optimizer changes the model's weights after every batch.

- If it is **too high**, the model takes wild, erratic jumps and forgets everything it knows.
- If it is **too low**, the model learns so slowly that it would take weeks to see any improvement.
- **Why 2e-4?** When doing normal full-model fine-tuning, you usually use a tiny number like 1e-5. But because we are using **LoRA**—which means we are training brand-new, randomly initialized adapter weights rather than the established base weights—we can afford to use a slightly higher learning rate to teach them faster.

### 2. `lr_scheduler_type="cosine"` (The Brakes)

You don't actually want your learning rate to stay at `2e-4` the entire time.

- At the beginning of training, your adapters are totally random, so you want big, fast updates (high learning rate).
- But as you get closer to the end of training, the model is almost perfect. If you keep taking massive steps, you will "overshoot" the optimal weights.
- A **cosine scheduler** gradually curves the learning rate down to near zero by the end of the training run, acting like a smooth braking system so the model can perfectly settle into the ideal weights.

### 3. `num_train_epochs=1` (The Read-Throughs)

An "epoch" is one complete pass through your entire dataset. We are only doing **1**.

- **Why not 5 or 10?** We only have 3,000 conversations. If we force the model to read those same 3,000 conversations 10 times in a row, it will stop learning _how to converse_ and start simply _memorizing_ those exact specific sentences (a problem called **overfitting**). One pass is enough to teach it the `<|user|>` and `<|assistant|>` template pattern.

### 4. `logging_steps=10` (The Heartbeat)

Training can take a long time, and staring at a blank screen is terrifying. This parameter tells the trainer: _"Every time you process 10 batches, print the current Loss to the screen."_ It acts as a heartbeat. As long as that printed loss number keeps slowly going down, you know your training is succeeding.

### 5. `bf16=True` (The Math Engine)

Back in Step 1.2, you loaded the base weights in `bfloat16`. Setting `bf16=True` here tells the training engine to also perform all of its forward and backward pass math in `bfloat16`. This keeps the whole pipeline perfectly synced — same dtype end to end, low memory, fast computation.

**Why not `fp16=True`?** Using `fp16=True` enables PyTorch's `GradScaler`, which is designed to rescale `float32` gradients before and after the backward pass. When the model and its LoRA adapters are in `bfloat16`, their gradients are also `bfloat16` — and the scaler explicitly rejects non-float32 gradients, crashing with:

```
ValueError: Attempting to unscale FP16 gradients.
```

`bfloat16` does not use a gradient scaler at all (its wider dynamic range makes one unnecessary), so the crash never happens.

### 6. `save_strategy="steps"`, `save_steps=75`, `save_total_limit=3` (Crash Recovery)

By default, the trainer only saves a checkpoint at the very end of training. If your machine crashes at step 370 out of 375, you lose everything.

- `save_strategy="steps"` — save a checkpoint periodically during training, not just at the end.
- `save_steps=75` — save every 75 steps. With 375 total steps, this lands exactly on: 75, 150, 225, 300, **375**. The final step is always captured.
- `save_total_limit=3` — keep only the last 3 checkpoints on disk (225, 300, 375). Older ones are deleted automatically to save disk space. Each checkpoint is ~290 MB (adapter weights + optimizer state), so 3 costs ~870 MB total.

Each saved checkpoint folder contains everything needed to **resume training** from that exact step: adapter weights, optimizer state, scheduler state, and RNG state.

### 7. `report_to="tensorboard"` (Live Training Dashboard)

Tells the trainer to write loss and learning rate logs to TensorBoard event files inside `output_dir`. See the TensorBoard instructions in section 1.5 for how to view them in your browser during training.

<a id="section-11"></a>
# 11 - 1.5 Train and Save LoRA Weights

This is it—the finish line for Part 1! Everything you have built so far (the dataset, the base weights, the LoRA adapters, and the hyperparameter engine) is about to get plugged into the master controller: the **`SFTTrainer`**.

Before you write the final execution block, let's look at what this trainer is actually doing and why the save step is so mathematically elegant.

### 1. The `SFTTrainer` vs. Standard Trainers

If you have used Hugging Face before, you might have seen the standard `Trainer` class. The `SFTTrainer` (Supervised Fine-Tuning Trainer) comes from the `trl` (Transformer Reinforcement Learning) library.

- It is purpose-built for Large Language Models.
- By explicitly passing `dataset_text_field="text"`, you are telling the engine exactly where to find those perfectly formatted `<|user|>` and `<|assistant|>` strings you built back in Step 1.1. It will automatically tokenize them and feed them to the GPU.

### 2. The Context Window: `max_seq_length=512`

This is a massive hidden memory saver. TinyLlama technically has a maximum context window of 2048 tokens.

- If you set the training length to 2048, the self-attention mechanism inside the GPU requires exponentially more memory (Attention math squares as length increases: $N^2$).
- By capping it at `512`, you keep training lighting-fast. If a conversation in your UltraChat dataset happens to be 600 tokens long, the trainer will just cleanly chop off the last 88 tokens to make it fit.

### 3. The Grand Finale: Saving the Weights

When `.train()` finishes, you will call `trainer.model.save_pretrained("my_lora_folder")`.

Because you used LoRA, this save function does something incredibly smart: **It completely ignores the 2.2 GB base model.** It only saves the 55.5 million parameter adapter weights (the $A$ and $B$ matrices) that you just trained.

- The resulting folder will only be about 100 to 200 Megabytes!
- This is why LoRA revolutionized AI. You can build 50 different chatbots for 50 different tasks, and store all of them on a tiny USB thumb drive, plugging them into the frozen base model whenever you need them.

---

### Your Final Part 1 Code

Here is the exact implementation to wire everything together, start the engine, and save your new AI's brain:

```python
from trl import SFTTrainer

# 1. Initialize the Trainer
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="text",
    tokenizer=tokenizer,
    args=training_arguments,
    max_seq_length=512,
)

# 2. Fire up the training loop!
# (This will print a progress bar and your logging_steps heartbeat)
trainer.train()

# 3. Save final checkpoint — includes optimizer + scheduler state, needed to resume training
trainer.save_state()

# 4. Save only the LoRA adapter weights inside the results folder
adapter_save_path = "./results/sft-lora-adapter"
trainer.model.save_pretrained(adapter_save_path)
tokenizer.save_pretrained(adapter_save_path)

print(f"Training complete! Adapters saved to {adapter_save_path}")

```

Go ahead and run this! You will see a progress bar appear. Watch the **Loss** column closely. It should start around `2.0` or higher, and over the next few minutes, it should slowly grind its way down toward `1.2`.

Depending on the exact specs of your cloud setup, this might take 10 to 30 minutes to chew through the 3,000 rows.

Let’s do a rapid-fire breakdown of those remaining parameters so you know exactly what the engine is doing with them under the hood:

### 1. `model=model` (The Brain)

This isn't just the raw 2.2 GB TinyLlama you downloaded anymore. Because you passed it through `get_peft_model` in Step 1.3, this is now your **hybrid model**—the frozen base weights with your 55.5 million trainable LoRA adapters glued to the sides. The trainer uses this to execute the forward and backward passes.

### 2. `train_dataset=dataset` (The Curriculum)

This is the `UltraChat` dataset you built in Step 1.1. You already shuffled it and sliced it down to exactly 3,000 rows. The trainer will automatically pull from this, chunk it into batches of 2 (based on your `TrainingArguments`), and feed it to the GPU.

### 3. `tokenizer=tokenizer` (The Translator)

This is a crucial one! You might wonder: _"Wait, didn't we already use the tokenizer to format the text in Step 1.1?"_ Yes, but you told it to return **readable strings** (`tokenize=False`). The GPU cannot do math on English letters. By passing the tokenizer into the trainer here, the trainer automatically grabs those strings, converts them into integer Token IDs right before they hit the GPU, and automatically adds those Left-Padding `<PAD>` tokens we set up earlier so the batches are perfectly squared off.

### 4. `args=training_arguments` (The Physics Engine)

This is the master control board you built in Step 1.4. You are handing the trainer your specific rules for the learning rate, the cosine scheduler, the 1-epoch limit, and the bfloat16 precision. Without this, the trainer would default to standard, unoptimized Hugging Face settings and likely crash your memory.

### 5. Why `peft_config` is NOT passed to `SFTTrainer` here

You might notice the notebook instructions say to pass `peft_config` to `SFTTrainer`, and many tutorials online do the same. **Do not do that in this flow.** Here is why.

`SFTTrainer` has two valid modes:

| Mode                               | When to use                                                                                                             |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Pass `peft_config` to `SFTTrainer` | You hand it a **raw base model** and let `SFTTrainer` wrap it with LoRA itself                                          |
| Do NOT pass `peft_config`          | You already called `get_peft_model` yourself in Step 1.3 and hand `SFTTrainer` a model that is **already LoRA-wrapped** |

In this notebook, Step 1.3 explicitly calls `get_peft_model(model, peft_config)`. The model is already a `PeftModel` by the time it reaches Step 1.5. If you also pass `peft_config` to `SFTTrainer`, the trainer calls `get_peft_model` a second time on a model that is already wrapped. This causes `bitsandbytes` to be imported twice, which triggers a crash:

```
RuntimeError: Tried to register an operator (bitsandbytes::int8_mixed_scaled_mm) with the same name
and overload name multiple times.
```

PyTorch's operator registry does not allow the same custom op to be registered twice in the same process. The second import of `bitsandbytes` hits this wall immediately.

**The rule:** whichever calls `get_peft_model` first owns the wrapping. If you do it in Step 1.3 (as this notebook does), `SFTTrainer` must receive only `model` — no `peft_config`. `SFTTrainer` will detect that the model is already a `PeftModel` and skip its own wrapping step automatically.

<a id="section-12"></a>
# 12 - 1.6 Merge Adapter and Run Inference

Let's break down exactly what this text is telling you, piece by piece, without a single line of code.

### The "Two-Brain" Problem (Before Merging)

Right now, your model exists in your GPU's memory as two completely separate pieces:

1. **The Base Model ($W$):** The massive, 2.2 GB frozen "brain" that knows the English language but doesn't know how to chat.
2. **The LoRA Adapters ($A$ and $B$):** The tiny, 55.5 MB "sticky notes" you just trained that contain the conversational rules.

If you try to run inference right now, the GPU has to do double the work. For every single word it generates, it has to calculate the math for the Base Model, calculate the math for the Adapters, and then add them together on the fly. This extra calculation time is what the text refers to as **"PEFT overhead."**

### The Solution: The Fusion Math

The command `merge_and_unload()` acts like a forge. It permanently bakes your tiny sticky notes directly into the massive base brain.

The text gives you the exact formula the GPU uses to do this: $W' = W + \frac{\alpha}{r}AB$

Here is what those letters actually mean in plain English:

- **$W$**: Your frozen, pre-trained base model weights.
- **$A$ and $B$**: The two tiny LoRA matrices you just spent the last 20 minutes training. When multiplied together ($AB$), they represent the new "conversational" knowledge.
- **$\frac{\alpha}{r}$**: This is the scale factor we set up way back in step 1.3 (`lora_alpha=32`, `r=64`). It dictates exactly how "loud" the new knowledge should be when it gets added to the base brain.
- **$W'$**: The brand new, upgraded base model.

### The Unloading Phase

Once the math is done and $W'$ is created, the original $A$ and $B$ adapter objects are completely useless. The `unload()` part of the command permanently deletes them from your GPU's memory.

Your new model ($W'$) takes up the exact same amount of memory as the original base model, but it is now permanently transformed into a conversational AI. It runs at maximum speed because it doesn't have to do that double-math anymore.

### The Final Test (Step 4)

The text mentions comparing the output to a base model. This is the ultimate proof that your training worked.

- If you feed the prompt `<|user|> How do I make tea? </s>` to a raw base model, it will just try to autocomplete the pattern. It might say: _"How do I make coffee? How do I make water?"_
- If you feed it to your newly merged model, it will recognize the tags and respond with a step-by-step recipe.

---

### Your Code

```python
from peft import AutoPeftModelForCausalLM
from transformers import pipeline

# Load LoRA adapter — AutoPeftModelForCausalLM reads base model name from adapter_config.json
model = AutoPeftModelForCausalLM.from_pretrained(
    "./results/sft-lora-adapter",
    low_cpu_mem_usage=True,
    torch_dtype=torch.bfloat16,   # keep merged model in bfloat16 — matches training dtype
    device_map="auto",
)
merged_model = model.merge_and_unload()   # fuse adapters into W, discard A and B

# Run inference
prompt = """<|user|>
Tell me something about Large Language Models.</s>
<|assistant|>
"""

pipe = pipeline(task="text-generation", model=merged_model, tokenizer=tokenizer)
print(pipe(prompt, max_new_tokens=200)[0]["generated_text"])
```

### Why `AutoPeftModelForCausalLM` Works Here (and Why Part 2 Uses a Different Pattern)

`AutoPeftModelForCausalLM.from_pretrained(path)` is a convenience loader. It opens `adapter_config.json`, reads `base_model_name_or_path`, downloads and loads that base model, then attaches the adapter — all in one call.

**This works perfectly in Part 1** because the entire training sequence preserved `model.config.name_or_path` intact:

```
from_pretrained("TinyLlama/...")  →  name_or_path = "TinyLlama/..."
get_peft_model(model, config)     →  reads name_or_path → writes it to adapter_config.json ✅
```

**Part 2 (QLoRA) requires the explicit `PeftModel` pattern** because `prepare_model_for_kbit_training` sits between `from_pretrained` and `get_peft_model` and silently wipes `name_or_path`. See Section 15 for the full explanation and the one-line fix.

|                   | Part 1 (1.6)                             | Part 2 (2.6)                            |
| ----------------- | ---------------------------------------- | --------------------------------------- |
| Loading class     | `AutoPeftModelForCausalLM`               | `PeftModel.from_pretrained(base, path)` |
| Base model source | Read silently from `adapter_config.json` | Written explicitly in code              |
| `torch_dtype`     | `torch.bfloat16`                         | `torch.bfloat16`                        |

### What `low_cpu_mem_usage=True` Does

Without this flag, Hugging Face allocates the full 2.2 GB as a contiguous CPU RAM buffer, copies the weights in, then transfers to GPU — requiring 4.4 GB of headroom (buffer + GPU copy coexist briefly). With `low_cpu_mem_usage=True`, weights are memory-mapped and land directly in their final location — the large intermediate buffer never exists. On machines with limited CPU RAM this is essential; on machines with plenty it's still good practice.

<a id="section-13"></a>
# 13 - Part 2: Supervised Fine-Tuning with QLoRA

## 2.1 Dataset Preparation and Chat Templates

Welcome to Part 2! You are about to dive into **QLoRA** (Quantized LoRA), which is arguably the most important breakthrough in modern open-source AI. This is the exact technique that allows massive 7-Billion and 70-Billion parameter models to be fine-tuned on standard, cheap consumer graphics cards instead of million-dollar server farms.

Before you write any code, let's break down the actual theory of what the text is introducing, specifically the "Q" and why Step 2.1 looks so familiar.

### 1. The "Q": What is 4-bit NF4?

In Part 1, you loaded the base model in `bfloat16`. Every single parameter (weight) in the model took up 16 bits (2 bytes) of memory.

- **Quantization** is the process of compressing those numbers.
- By compressing the model to **4-bit**, you are cramming each parameter into just 0.5 bytes. That is a massive 75% reduction in size compared to Part 1, which is how you drop the VRAM footprint from 2.2 GB down to just 550 MB!

**NF4** stands for _NormalFloat 4-bit_. It is a highly mathematically optimized way of doing this compression. Instead of just chopping off the decimal points haphazardly (which would make the AI stupid), NF4 looks at the bell curve (normal distribution) of the model's weights and compresses them in a way that preserves almost 100% of the original logic and accuracy.

### 2. The Trade-Off: The Two Extra Steps

If compressing the model saves that much memory and keeps it smart, why don't we always do it?
Because GPUs cannot natively perform calculus (the backward pass of training) on 4-bit numbers. They need 16-bit or 32-bit numbers to calculate gradients.

To solve this, QLoRA introduces a brilliant workaround using two extra steps you'll code later:

1. **`BitsAndBytesConfig`:** This tells the model to store itself in the compressed 4-bit format while sitting idle in memory.
2. **`prepare_model_for_kbit_training`:** This adds a secret mechanism to the model. During the training loop, right as a batch of data passes through a layer, it instantly uncompresses (dequantizes) that specific layer back to 16-bit, does the math to train your LoRA adapters, and then instantly compresses the layer back to 4-bit.

### 3. Deja Vu: Section 2.1

Look closely at the instructions and the skeleton code for Section 2.1. You might notice it is **exactly identical** to Section 1.1!

Why? Because your dataset preparation has absolutely nothing to do with how the model's weights are compressed in memory. The model still needs to see the exact same `<|user|>` and `<|assistant|>` Jinja template strings to learn how to chat. The data pipeline remains completely untouched.

Since you've already mastered the theory behind this data formatting step, are you ready to copy over your code from 1.1 to knock this cell out, or do you have any questions about the 4-bit compression mechanics first?

<a id="section-14"></a>
# 14 - 2.2 Model Quantization — BitsAndBytes Config

This configuration block is the true engine of QLoRA. It represents one of the most clever engineering tricks in modern machine learning.

Instead of just forcing the model to be smaller and accepting that it will get dumber, the engineers behind QLoRA created a dynamic "zipping and unzipping" system.

Here is exactly what these four parameters are doing mechanically inside your computer:

### 1. `load_in_4bit=True` (The Vault)

This is the master switch. It tells Hugging Face to take the massive 2.2 GB base model and crush every single weight down from 16 bits to 4 bits before putting it into the GPU memory. This is what shrinks the footprint to ~550 MB. You can think of this as putting the model into cold storage.

### 2. `bnb_4bit_quant_type="nf4"` (The Smart Compression)

If you just compress numbers normally (like turning a high-res image into a low-res JPEG), you lose a lot of detail, and the AI starts to hallucinate.

- Neural network weights naturally form a bell curve (a normal distribution). Most numbers are clustered around zero.
- **NF4 (NormalFloat 4-bit)** is a mathematically optimized compression format specifically built for neural networks. It allocates more "data buckets" near zero where the majority of the weights live, and fewer buckets at the extreme ends. This means you can compress the model by 75% while retaining virtually 100% of its original accuracy.

### 3. `bnb_4bit_compute_dtype=torch.bfloat16` (The Unzipping Engine)

This solves the fundamental hardware problem: GPUs cannot do calculus on 4-bit numbers.
When your training loop feeds a conversation into the model, the GPU temporarily "unzips" the specific layer it is currently looking at back up to a 16-bit format for the math.

- The GPU does the high-precision math to train your LoRA adapters.
- As soon as the math is done, it instantly deletes the unzipped version and moves to the next layer. This keeps the model small in memory but allows for highly accurate learning.

**Why `bfloat16` instead of `float16`?** The notebook table suggests `"float16"`, but `torch.bfloat16` is the better choice — and it must match `bf16=True` in your `TrainingArguments`. Using `bfloat16` here and `fp16=True` in training would create a dtype mismatch that can cause numerical instability. `bfloat16` has a wider dynamic range (same exponent as `float32`), making gradients far less likely to overflow during the backward pass. This is the same lesson we learned in Part 1 — once you commit to `bfloat16` as your compute dtype, keep it consistent everywhere.

### 4. `bnb_4bit_use_double_quant=True` (The "Inception" Trick)

When you compress millions of numbers into NF4, the algorithm has to create "metadata" (quantization constants) to remember how to uncompress them later.
For a 1.1 Billion parameter model, that metadata alone can take up hundreds of megabytes of VRAM. Setting this to `True` tells the system: _"Take the metadata that compresses the model, and compress the metadata too."_ It is an extreme, deep-level optimization that saves you even more memory for free.

### The Tokenizer Reminder

Just like in Part 1, the instructions remind you to load the tokenizer for the **Base Model** (not the Chat model) and set up the Left-Padding. Because the actual neural network is about to enter the GPU, its token dictionary needs to perfectly match its foundational embedding matrix.

<a id="section-15"></a>
# 15 - 2.3 LoRA Configuration

This section should give you major déjà vu! If you look at that table of parameters (`r=64`, `lora_alpha=32`, `target_modules`), it is **exactly identical** to the configuration you built in Step 1.3.

Why? Because the "sticky notes" (the LoRA adapters) we are attaching to the model haven't changed at all. We are still training them in standard 16-bit precision. The _only_ thing that changed is the massive base brain we are attaching them to, which is now sitting in compressed 4-bit storage.

However, there is **one massive, critical difference** in the instructions this time: the inclusion of the `prepare_model_for_kbit_training()` function.

Let's break down exactly why this function is the secret sauce that makes QLoRA possible.

### The Problem: 4-Bit Math is Fragile

In neural network training, the "backward pass" relies heavily on calculus (gradients) to figure out how to update the weights.

- In Part 1 (`bfloat16`), calculating gradients is smooth and stable.
- In Part 2 (`4-bit`), the numbers are so compressed that if you try to push a raw calculus gradient through them, the math breaks. The gradients will either explode to infinity or vanish to zero, and your training will instantly crash.

### The Solution: `prepare_model_for_kbit_training`

Before we attach the LoRA adapters, we have to run the base model through this specific preparation function. Under the hood, it performs three highly specific "surgery" steps to keep the math stable:

1. **Freezing:** It explicitly locks down all the 4-bit weights so PyTorch doesn't accidentally try to update them.
2. **Float32 Layer Norms:** Every transformer layer has a tiny sub-component called a "Layer Norm" that keeps the data balanced as it flows through the network. This function surgically converts _just_ those tiny Layer Norms into hyper-precise 32-bit floats. This acts as a mathematical anchor, ensuring the data doesn't get corrupted as it moves between the 4-bit base weights and the 16-bit LoRA adapters.
3. **Gradient Checkpointing Prep:** It wires the model to perfectly support the memory-saving gradient checkpointing we will use in the training arguments later, ensuring gradients can successfully pass _through_ the frozen 4-bit layers to reach your LoRA adapters.

### The Workflow Order

Because of this delicate math, the order in which you write your code here is strictly enforced by Hugging Face:

1. You build the `LoraConfig`.
2. You run the base model through `prepare_model_for_kbit_training(model)`.
3. **Restore `model.config.name_or_path = model_name`** — explained below.
4. _Then_, you attach the config to the prepared model using `get_peft_model(model, peft_config)`.

### ⚠️ The Hidden Bug: `prepare_model_for_kbit_training` Wipes the Base Model Name

This is a known gotcha that is not documented anywhere in the official Hugging Face tutorials, but it will silently break your saved adapter.

When `prepare_model_for_kbit_training(model)` runs, it internally rewraps the model. During that process, it loses the `name_or_path` attribute — the string `"TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T"` that was stored in `model.config` after `from_pretrained`. After this function returns, `model.config.name_or_path` is `None`.

`get_peft_model` immediately reads that attribute to write `base_model_name_or_path` into the adapter's `adapter_config.json` when you save. If it reads `None`, it writes `null`.

The symptom shows up later — not at training time but at inference time, when you try to load the adapter:

```
RepositoryNotFoundError: 404 Client Error.
Repository Not Found for url: https://huggingface.co/None/resolve/main/config.json.
```

`AutoPeftModelForCausalLM` looked inside your `adapter_config.json`, found `base_model_name_or_path: null`, and tried to download from `https://huggingface.co/None/...` — which obviously doesn't exist.

**Why Part 1 doesn't have this bug:** In Part 1, the sequence is `from_pretrained` → `get_peft_model` directly. There is no `prepare_model_for_kbit_training` in between to wipe the name. Part 2 (QLoRA) is the only path that goes through this function.

**The fix — one line between the two calls:**

```python
model = prepare_model_for_kbit_training(model)

# Restore name_or_path — prepare_model_for_kbit_training wipes it.
# Without this, adapter_config.json will have base_model_name_or_path: null
# and loading the adapter later will crash with a 404 error.
model.config.name_or_path = model_name

model = get_peft_model(model, peft_config)
```

This ensures the saved `adapter_config.json` always contains:

```json
{
  "base_model_name_or_path": "TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T",
  ...
}
```

<a id="section-16"></a>
# 16 - 2.4 Training Arguments

You are going to look at that table and think, _"Wait, didn't I just do this?"_ You are exactly right. 9 out of the 10 parameters here are identical to the `TrainingArguments` you built in Step 1.4. You are still using an effective batch size of 8, a cosine scheduler, and a learning rate of 2e-4 because you are still training the exact same LoRA adapters.

However, there is **one massive difference**, and it is the entire reason QLoRA works without crashing your computer:

### The Star of the Show: `optim="paged_adamw_32bit"`

In Part 1, you used standard `"adamw_torch"`. Because the whole model was in bfloat16, the memory usage was very predictable.

In QLoRA, things get chaotic. Your GPU is rapidly unzipping 4-bit weights into 16-bit, calculating gradients, updating the LoRA adapters, and throwing away the unzipped weights. This intense mathematical juggling act can cause sudden, massive spikes in VRAM usage. If a spike hits your GPU's memory limit, your training loop instantly crashes with a dreaded `CUDA Out Of Memory` error.

**The "Paged" Safety Valve:**
By switching to a "paged" optimizer, you are giving the system permission to use your standard computer RAM as an overflow valve.

- If the optimizer detects a memory spike about to happen, it temporarily "pages" (moves) some of its background data off the GPU and into your CPU's RAM.
- Once the math is done and the VRAM clears up, it pulls the data back.
- It slows down training slightly when a spike happens, but it guarantees your training will never crash from an out-of-memory error.

### Your Code

```python
from transformers import TrainingArguments

training_arguments = TrainingArguments(
    output_dir="./results/sft-qlora",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    optim="paged_adamw_32bit",
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    num_train_epochs=1,
    logging_steps=10,
    bf16=True,
    gradient_checkpointing=True,
    save_strategy="steps",
    save_steps=75,
    save_total_limit=3,
    report_to="tensorboard",
)
```

### The Updated Parameters vs Part 1

| Parameter       | Part 1 (LoRA)   | Part 2 (QLoRA)        | Why it changed                                |
| --------------- | --------------- | --------------------- | --------------------------------------------- |
| `optim`         | `"adamw_torch"` | `"paged_adamw_32bit"` | 4-bit model causes unpredictable VRAM spikes  |
| everything else | same            | same                  | LoRA adapters and training loop are identical |

### `bf16=True` — Not `fp16=True`

The notebook table says `fp16=True` but the correct value is `bf16=True`. Here is why this matters specifically for QLoRA:

You set `bnb_4bit_compute_dtype=torch.bfloat16` in section 2.2. This means every time a 4-bit layer is dequantized for computation, it becomes `bfloat16`. If you then set `fp16=True` in training arguments, you are telling the training engine to operate in a different 16-bit format — a mismatch that causes the gradient scaler to crash with:

```
ValueError: Attempting to unscale FP16 gradients.
```

Setting `bf16=True` keeps the dtype consistent end-to-end: 4-bit storage → `bfloat16` compute → `bfloat16` training.

### `save_steps=75` — Why 75 and not 50?

With 3,000 samples, batch size of 2, and gradient accumulation of 4, the effective batch size is 8. That gives exactly **375 total steps** per epoch. `save_steps=75` divides evenly into 375 (375 ÷ 75 = 5), so checkpoints land at 75, 150, 225, 300, **375** — the final step is always saved. Using `save_steps=50` would miss the final step since 375 is not divisible by 50.

---

<a id="section-17"></a>
# 17 - 2.5 Train and Save QLoRA Weights

This section is structurally identical to Section 1.5, with two important differences.

### The Key Differences from Part 1

|                             | Part 1 (LoRA)                      | Part 2 (QLoRA)                |
| --------------------------- | ---------------------------------- | ----------------------------- |
| Adapter save path           | `./results/sft-lora-adapter`       | `./results/sft-qlora-adapter` |
| Base model in memory        | bfloat16 (~2.2 GB)                 | 4-bit NF4 (~0.55 GB)          |
| `peft_config` in SFTTrainer | Not passed (model already wrapped) | Not passed (same reason)      |

### Why NOT to pass `peft_config` to `SFTTrainer`

Same rule as Part 1: you already called `get_peft_model` in section 2.3, so the model is already a `PeftModel`. If you also pass `peft_config` to `SFTTrainer`, it calls `get_peft_model` a second time. This causes `bitsandbytes` to try to register its custom CUDA operators twice in the same Python process, crashing with:

```
RuntimeError: Tried to register an operator with the same name multiple times.
```

Pass only `model` — `SFTTrainer` detects it is already a `PeftModel` and skips its own wrapping.

### `trainer.save_state()` — The Resumable Checkpoint

After `trainer.train()`, call `trainer.save_state()`. This writes the full training state (optimizer, scheduler, RNG) to `output_dir` as a proper `checkpoint-375` folder. Without it, if you want to continue training later, you only have `checkpoint-300` (the last periodic save) and would have to retrain the final 75 steps.

### Your Code

```python
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="text",
    tokenizer=tokenizer,
    args=training_arguments,
    max_seq_length=512,
)

trainer.train()

# Save final checkpoint — includes optimizer + scheduler state, needed to resume training
trainer.save_state()

# Save only the QLoRA adapter weights inside the results folder
adapter_save_path = "./results/sft-qlora-adapter"
trainer.model.save_pretrained(adapter_save_path)
tokenizer.save_pretrained(adapter_save_path)

print(f"Training complete! Adapters saved to {adapter_save_path}")
```

After training your `results/` folder will look like:

```
results/
├── sft-lora/                       ← Part 1 (LoRA) training artifacts
│   ├── checkpoint-225/             ← resumable
│   ├── checkpoint-300/             ← resumable
│   ├── checkpoint-375/             ← resumable (final step)
│   └── runs/                       ← Part 1 TensorBoard event files
├── sft-qlora/                      ← Part 2 (QLoRA) training artifacts
│   ├── checkpoint-225/             ← resumable
│   ├── checkpoint-300/             ← resumable
│   ├── checkpoint-375/             ← resumable (final step)
│   └── runs/                       ← Part 2 TensorBoard event files
├── sft-lora-adapter/               ← Part 1 final adapter weights
├── sft-qlora-adapter/              ← Part 2 final adapter weights
└── plots/
    ├── training_curve.png          ← Part 1 loss curve
    └── qlora_training_curve.png    ← Part 2 loss curve
```

**Why separate subfolders?** With both parts writing to the same `./results/`, their checkpoints (`checkpoint-75`, `checkpoint-150`...) would be indistinguishable. Worse, TensorBoard would mix the two training runs into a single noisy curve. Separate `output_dir` values keep everything clean: `tensorboard --logdir results/` reads both `sft-lora/runs/` and `sft-qlora/runs/` as two distinct named runs you can compare side by side.

### The Adapter Size

Both `sft-lora-adapter` and `sft-qlora-adapter` will be roughly the same size (~97 MB). That makes sense — both train the same 55.5 million LoRA adapter parameters at the same rank. The only difference between them is the base model they were trained on top of (bfloat16 vs 4-bit frozen weights). The adapters themselves are always stored in full 16-bit precision.

---

<a id="section-18"></a>
# 18 - 2.6 Merge Adapter and Run Inference (QLoRA)

This section is structurally the same as Part 1's 1.6, but the inference code uses a **different loading pattern** — and understanding why is important.

### Why Not `AutoPeftModelForCausalLM` Here?

In Part 1, the inference cell used `AutoPeftModelForCausalLM.from_pretrained(adapter_path)`. That class is a convenience wrapper that does two things automatically:

1. Opens `adapter_config.json` and reads `base_model_name_or_path`
2. Downloads and loads that base model, then attaches the adapter on top

This works perfectly in Part 1 because `adapter_config.json` has the correct base model name.

In Part 2, if you forgot to add `model.config.name_or_path = model_name` before `get_peft_model` in section 2.3, the saved `adapter_config.json` will have `base_model_name_or_path: null`. `AutoPeftModelForCausalLM` will then try to load from `https://huggingface.co/None/...` and crash with a `RepositoryNotFoundError`.

Even with the fix in place, Part 2 uses the **explicit `PeftModel` pattern** — which is considered better practice for local development because the base model is clearly visible in the code:

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, pipeline
import torch

# Step 1: Load the clean base model in bfloat16
# For inference after merging, bfloat16 is correct — no need for 4-bit
base_model = AutoModelForCausalLM.from_pretrained(
    "TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Step 2: Load the saved adapter weights on top of the base model
model = PeftModel.from_pretrained(base_model, "./results/sft-qlora-adapter")

# Step 3: Fuse adapter matrices into base weights permanently
merged_model = model.merge_and_unload()
```

### `AutoPeftModelForCausalLM` vs `PeftModel.from_pretrained` — When to Use Which

|                                        | `AutoPeftModelForCausalLM`          | `PeftModel.from_pretrained`        |
| -------------------------------------- | ----------------------------------- | ---------------------------------- |
| You need to know base model            | No — reads from adapter_config.json | Yes — you pass it explicitly       |
| Works if adapter_config.json is broken | ❌ Crashes                          | ✅ Works fine                      |
| Code clarity                           | Less clear (base model is implicit) | More clear (base model is visible) |
| Common use case                        | Sharing adapters on HuggingFace Hub | Local development and research     |

### Why Load in bfloat16 (Not 4-bit) for Inference?

During **training**, the 4-bit base model is essential — it's what lets the whole thing fit in VRAM. But during **inference after merging**, the 4-bit compression is irrelevant. `merge_and_unload()` fuses the adapter matrices directly into the base weights ($W' = W + \frac{\alpha}{r}AB$). Once merged, the result is a standard model with no adapter overhead. Loading the base model in bfloat16 for this merge step gives you a clean, full-precision merged model at roughly 2.2 GB — exactly like Part 1's output.

---

<a id="section-19"></a>
# 19 — Part 3: Evaluating the Fine-Tuned Model

This section is different from everything before it. Parts 1 and 2 were about _building_ — writing training code and watching loss go down. Part 3 is about _measuring_ — figuring out whether the model actually got better, and by how much.

The honest answer is: **there is no single correct metric**. Researchers use several, each catching things the others miss. This section builds all four from scratch so you understand exactly what each one measures and where it fails.

None of these exercises need a GPU. They use only `math` and `numpy` — they are about the math of evaluation, not the mechanics of inference.

### The Four Metrics at a Glance

| Metric         | What it measures                      | Input it needs                  | Main failure                                                            |
| -------------- | ------------------------------------- | ------------------------------- | ----------------------------------------------------------------------- |
| **Perplexity** | Model confidence / fluency            | Token log-probs from the model  | Only measures the model — not the quality of its outputs vs a reference |
| **BLEU**       | Surface word overlap with a reference | Model output + reference string | Penalises paraphrases — semantically identical text can score near zero |
| **BERTScore**  | Semantic overlap with a reference     | Pre-computed token embeddings   | Requires a BERT model; slower; still imperfect for hallucinations       |
| **Elo**        | Relative quality vs other models      | Human pairwise preference votes | Requires human judges; expensive at scale                               |

---

<a id="section-20"></a>
# 20 — 3.1 Perplexity From Scratch

Perplexity is the most fundamental metric in language modelling. It answers the question: _"How surprised is the model by this text?"_ Lower perplexity means the model found the text predictable — which means it is generating fluent, confident output.

### The Formula

$$\text{PPL}(W) = \exp\!\left(-\frac{1}{N}\sum_{i=1}^{N} \log P(w_i \mid w_1, \ldots, w_{i-1})\right)$$

Breaking it apart:

- $\log P(w_i \mid w_1, \ldots, w_{i-1})$ — the log-probability the model assigned to token $i$, given all previous tokens. This is what models output directly as "logits".
- $\frac{1}{N}\sum$ — the **average** log-prob per token. Averaging normalises for sequence length so you can compare a 4-token sequence to a 400-token one.
- The negative sign — log-probs are always negative numbers (because probabilities are between 0 and 1, and `log(0.x) < 0`). Negating gives a positive number.
- `exp(...)` — converts from the log scale back to a "how many times more surprised" scale that humans find easier to interpret.

### What the Number Actually Means

Perplexity has a direct intuitive interpretation: **it is the effective number of equally likely choices the model was deciding between at each step.**

- **PPL = 1** → The model was 100% certain about every single token. Perfect (and impossible in practice).
- **PPL = 8.3** → On average, the model behaved as if it had 8.3 equally probable choices to pick from at each step.
- **PPL = 2.7** → Only ~2.7 choices on average. Much more confident, much more fluent.

### Your Code

```python
import math

def perplexity(log_probs: list) -> float:
    avg_log_prob = sum(log_probs) / len(log_probs)   # average log-prob per token
    return math.exp(-avg_log_prob)                    # negate and exponentiate

base_log_probs = [-2.3, -1.8, -2.1, -1.5]
sft_log_probs  = [-1.2, -0.9, -0.8, -0.6]

print(f"Base model PPL: {perplexity(base_log_probs):.2f}")   # ~8.3
print(f"SFT model PPL:  {perplexity(sft_log_probs):.2f}")    # ~2.7
```

### Reading the Results

The base model's log-probs are all around -2, meaning it assigned roughly `exp(-2) ≈ 14%` probability to each correct token — it was quite uncertain. The SFT model's log-probs are around -0.8, meaning roughly `exp(-0.8) ≈ 45%` — much more confident.

This improvement makes sense: the base model has read 3 trillion tokens of general text and is only 14% sure what comes next in any conversational exchange. The SFT model has been specifically trained on thousands of `<|user|>` / `<|assistant|>` exchanges and has learned the format well.

### The Key Limitation of Perplexity

Perplexity only tells you how confident the model was — it says nothing about whether the answer was _correct_ or _helpful_. A model that confidently outputs fluent nonsense will have low perplexity. This is why the section uses perplexity alongside BLEU, BERTScore, and Elo rather than in isolation.

---

<a id="section-21"></a>
# 21 — 3.2 BLEU Unigram Precision

BLEU (Bilingual Evaluation Understudy) was invented in 2002 for machine translation, where a translated sentence should match a professional reference translation. The core idea: count how many words (n-grams) in the model's output also appear in the reference.

### The Formula (Unigram Version)

$$p_1 = \frac{\text{number of candidate unigrams that appear in the reference}}{\text{total unigrams in the candidate}}$$

"Unigram" means single words. Full BLEU extends this to bigrams, trigrams, and 4-grams combined with a brevity penalty (to stop the model from gaming the score by outputting one very common word). For this exercise we only implement unigram precision — enough to see both the mechanism and the critical flaw.

### Your Code

```python
def bleu_unigram(candidate: str, reference: str) -> float:
    cand_tokens = candidate.split()
    ref_set     = set(reference.split())
    matches     = sum(1 for w in cand_tokens if w in ref_set)
    return matches / len(cand_tokens)

reference      = "the cat sat on the mat"
candidate_near = "the cat sat on a mat"       # only "a" differs
candidate_para = "A feline rested on the rug" # same meaning, different words

print(bleu_unigram(candidate_near, reference))  # ~0.833  (5/6 words match)
print(bleu_unigram(candidate_para, reference))  # ~0.333  (only "on" + "the" match)
```

### Why the Paraphrase Scores So Low

The word `"feline"` means exactly the same as `"cat"` — but BLEU has no vocabulary. It only does exact string matching. `"feline" in {"the","cat","sat","on","mat"}` is `False`.

The 0.333 score comes entirely from two function words: `"on"` and `"the"`. None of the meaningful content words — `"feline"` → `"cat"`, `"rested"` → `"sat"`, `"rug"` → `"mat"` — are credited at all.

This is not a bug; it is a fundamental limitation of any metric based on surface overlap. When fine-tuning for conversational quality, your model will constantly rephrase and paraphrase. BLEU will systematically underrate it.

### When BLEU Still Matters

Despite this limitation, BLEU remains widely used because:

1. It is **deterministic** — the same candidate always gets the same score
2. It is **fast** — no model inference needed
3. For machine translation, where reference translations are typically close paraphrases of the correct answer, it correlates reasonably well with human judgment

For evaluating open-ended chat quality, it is a weak signal. This motivates the next section.

---

<a id="section-22"></a>
# 22 — 3.3 BERTScore Semantic Overlap

BERTScore (Zhang et al., 2019) was designed specifically to solve BLEU's paraphrase problem. Instead of comparing raw strings, it compares the **meanings** of tokens using contextual embeddings from BERT.

### The Idea

Each word in the candidate and each word in the reference is converted to a high-dimensional vector by a BERT model. Semantically similar words land close together in that space — `"feline"` and `"cat"` end up nearly co-located.

BERTScore precision: for each candidate token, find the reference token it is most similar to (highest cosine similarity), and average those maximum similarities across the whole candidate:

$$\text{BERTScore}_P = \frac{1}{|\hat{x}|} \sum_{\hat{x}_i \in \hat{x}} \max_{x_j \in x} \cos(e_{\hat{x}_i},\; e_{x_j})$$

### Cosine Similarity

The building block is cosine similarity — a measure of how aligned two vectors are, regardless of their magnitude:

$$\cos(u, v) = \frac{u \cdot v}{\|u\| \cdot \|v\|}$$

- **1.0** → vectors point in exactly the same direction → tokens are semantically identical
- **0.0** → vectors are perpendicular → tokens are unrelated
- **-1.0** → vectors point in opposite directions → tokens are semantic opposites (rare in practice)

### Your Code

```python
import numpy as np

def cosine_similarity(u: np.ndarray, v: np.ndarray) -> float:
    return np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))

def bertscore_precision(cand_emb: np.ndarray, ref_emb: np.ndarray) -> float:
    scores = []
    for c in cand_emb:                           # for each candidate token
        sims = [cosine_similarity(c, r) for r in ref_emb]  # similarity to every reference token
        scores.append(max(sims))                 # keep only the best match
    return sum(scores) / len(scores)             # average over all candidate tokens
```

### What the Toy Embeddings Show

The exercise provides 4-dimensional toy embeddings where semantically related words are given nearly-aligned vectors:

- `"feline"` and `"cat"` → very similar vectors → cosine ≈ 1.0
- `"rested"` and `"sat"` → very similar vectors → cosine ≈ 1.0
- `"rug"` and `"mat"` → very similar vectors → cosine ≈ 1.0

The result: BERTScore-P ≈ 0.999 for the paraphrase that BLEU scored only 0.333. Same input text. Same reference. ~3× higher score because BERTScore actually sees the semantic similarity.

### In Real Usage

In production, you replace the toy embeddings with a BERT forward pass:

```python
from transformers import BertTokenizer, BertModel
# embeddings = bert_model(tokenised_text).last_hidden_state
```

The `bert_score` library wraps this for you. Common practice is to use the DeBERTa-xlarge model which has the highest correlation with human judgment.

### BERTScore's Own Limitations

BERTScore is not perfect either:

- It can miss **factual errors** — "The capital of France is Berlin" and "The capital of France is Paris" have almost identical semantic structure, so their BERTScores would be very similar
- It is **slower** than BLEU — requires a full BERT forward pass
- It measures semantic closeness to a _specific_ reference, which means it can still penalise a perfectly good answer that approaches the topic differently

---

<a id="section-23"></a>
# 23 — 3.4 Elo Update From Pairwise Wins

Elo is the most trusted LLM evaluation method in active use today, powering **Chatbot Arena** (lmsys.org/chat) which has accumulated millions of human preference votes. It solves a fundamental problem that perplexity, BLEU, and BERTScore all have: they compare a model to a fixed reference. Elo compares models _to each other_ based on which one humans actually prefer.

### Why Pairwise Comparison?

Ask a human "is this response good?" and they'll struggle — "good" is vague and context-dependent. Ask "which of these two responses is better?" and they can answer reliably within a few seconds. This is the insight behind Chatbot Arena: show two anonymous model responses, collect the "A or B?" vote, repeat millions of times.

### The Elo Rating System

Originally designed for chess, Elo turns pairwise wins and losses into a continuous rating scale. Two formulas:

**Expected score (win probability):**
$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$$

**Rating update after one comparison:**
$$R'_A = R_A + K \cdot (S_A - E_A)$$

| Symbol     | Meaning                                                              |
| ---------- | -------------------------------------------------------------------- |
| $R_A, R_B$ | Current ratings (typically initialised at 1000 or 1500)              |
| $E_A$      | How likely $A$ was expected to win, given the rating gap             |
| $S_A$      | Actual result: 1 = win, 0 = loss, 0.5 = tie                          |
| $K$        | How much a single vote can move the rating (Chatbot Arena uses K=32) |

### Your Code

```python
def expected_score(R_A: float, R_B: float) -> float:
    return 1 / (1 + 10 ** ((R_B - R_A) / 400))

def elo_update(R_A: float, R_B: float, S_A: float, K: int = 32) -> float:
    E_A = expected_score(R_A, R_B)
    return R_A + K * (S_A - E_A)
```

### Reading the Two Scenarios

**Upset win** — lower-rated A (1500) beats higher-rated B (1600):

- $E_A = 1 / (1 + 10^{100/400}) = 1 / (1 + 10^{0.25}) \approx 0.36$ — A was only expected to win 36% of the time
- $R'_A = 1500 + 32 \times (1 - 0.36) = 1500 + 20.5 \approx 1520$ — wins 20 rating points

**Expected win** — higher-rated A (1600) beats lower-rated B (1500):

- $E_A \approx 0.64$ — A was expected to win 64% of the time, so no surprise
- $R'_A = 1600 + 32 \times (1 - 0.64) = 1600 + 11.5 \approx 1612$ — wins only 12 rating points

**The key property:** beating a stronger opponent earns more points than beating a weaker one. The same $K=32$ budget is split differently based on how surprising the result was. After enough votes, a strong model that only ever beats weak ones will plateau, while a model that can beat top opponents will keep climbing.

### Why Elo Is Hard to Game

Unlike BLEU (which you can hack by outputting common words) or perplexity (which rewards confidently wrong text), Elo is resistant to gaming because:

1. Your rating reflects _relative_ quality — you can only go up by beating models that already have high ratings
2. Each vote is independent — buying 1,000 fake votes for yourself doesn't help if the voters consistently prefer your opponent

The main cost is **human time**. At scale (millions of comparisons), it is expensive. For a single fine-tuning project like this one, the practical alternative is to run your own small-scale Elo evaluation using a handful of test prompts and either human judges or GPT-4 as a judge.

---

<a id="section-24"></a>
# 24 — 3.5 Qualitative Comparison

After four automated metrics, this section asks you to do the one thing none of them can: actually read the outputs and judge whether your model improved in ways that matter for the task.

### Why Qualitative Evaluation Can't Be Skipped

Consider these two responses to "What is the capital of France?":

- **Response A:** "The capital of France is Paris, which has been the country's political centre since the 10th century and is home to the Élysée Palace where the President resides."
- **Response B:** "Paris is a city in Europe."

Both responses contain the word "Paris". BLEU would give them very similar scores if "Paris" was in the reference. BERTScore would rate them both highly. Perplexity would depend entirely on the training distribution — if "Paris is a city in Europe" is more common in the training data, it might score lower perplexity (more confident) despite being a worse answer.

A human reading both responses knows immediately which one is useful.

### Three Prompt Types to Test

The exercise asks you to design prompts that probe three different dimensions of improvement SFT should have produced:

**1. Factual question**

_What to check:_ Does the fine-tuned model actually answer the question, or does it autocomplete the prompt pattern the way a base model would? A base model given `<|user|> What is photosynthesis? </s> <|assistant|>` might continue with more user questions instead of an answer, because it learned from raw internet text where Q&A patterns are unpredictable.

**2. Formatting instruction**

_What to check:_ Does the fine-tuned model follow explicit output format instructions like "list 3 examples" or "summarise in one sentence"? Base models often ignore formatting requests because they were not trained on instruction-following pairs. An SFT model trained on UltraChat should follow them reliably.

**3. Reasoning question**

_What to check:_ Does the model attempt a reasoned explanation, or does it regurgitate patterns? Try "Why does gradient checkpointing slow down training?" — a good SFT model should explain the memory/speed trade-off; a base model might repeat fragments of text it saw about training.

### What to Look For When Comparing

When you run the same prompt through your base model, your LoRA-fine-tuned model, and your QLoRA-fine-tuned model, look for these specific changes:

| Signal                | Base model               | After SFT                                |
| --------------------- | ------------------------ | ---------------------------------------- | ----------------------------------------- | ---------------------------------------- |
| Follows `<            | assistant                | >` tag                                   | Often ignored — continues user-style text | Reliably generates an assistant response |
| Response completeness | Trails off mid-sentence  | Ends with `</s>` cleanly                 |
| Instruction following | Ignores format requests  | Attempts to follow "list X", "explain Y" |
| Factual density       | Vague pattern-completion | More specific and structured             |

None of these signals show up in any automated metric score. They are the actual things that make a model useful — and they are why qualitative evaluation, even if done manually on just 10-20 prompts, is an essential part of any fine-tuning run.

<a id="section-25"></a>
# 25 — Part 4: Preference Tuning with DPO

## What SFT Did — and What It Left Unfinished

After Parts 1 and 2, your model knows how to follow instructions. It recognises `<|user|>` tags, produces `<|assistant|>` responses, and stops cleanly at `</s>`. That is SFT's job and it did it.

But SFT has a blind spot: it learns by **imitation**. The training signal is "produce text that looks like this dataset." It has no concept of "this response is better than that response." If your training data contains one very detailed helpful answer and one vague lazy answer to similar questions, SFT averages across both — it learns a mediocre middle ground.

**The problem in concrete terms:** Imagine two responses to "Explain how neural networks learn":

- **Chosen (preferred):** "Neural networks learn by adjusting weights through backpropagation. When a prediction is wrong, the error signal flows backward through each layer, nudging the weights in the direction that would have made the prediction less wrong. Repeat this for thousands of examples and the weights converge to values that generalise well."
- **Rejected:** "Neural networks are a type of machine learning. They have layers and weights. The weights get updated during training."

Both responses follow the chat template correctly. SFT sees both as valid targets. DPO teaches the model that the first response is _better than_ the second — a fundamentally different kind of signal.

---

## RLHF vs DPO — Two Ways to Learn from Preferences

The classical approach to learning from human preferences is **RLHF (Reinforcement Learning from Human Feedback)**. It works in three steps:

1. Collect human preference votes on pairs of responses
2. Train a **reward model** — a separate neural network that scores any response with a single number
3. Use **PPO (Proximal Policy Optimization)** to fine-tune the LLM to maximise that reward score while not drifting too far from the SFT baseline

This works, but it is expensive and fragile:

- You need to train _and maintain_ a separate reward model
- PPO involves multiple models running simultaneously (policy, reference, reward, value) — 4× the VRAM
- PPO is notoriously unstable and sensitive to hyperparameters

**DPO (Direct Preference Optimization, Rafailov et al. 2023) is a mathematical shortcut.** It proves that the optimal RLHF policy can be computed directly from the preference pairs — no reward model, no PPO, no RL at all.

The derivation shows that the reward function is implicitly encoded in the log-probability ratio between the trainable model and a frozen reference:

$$r(x, y) = \beta \log \frac{\pi_\theta(y \mid x)}{\pi_{\text{ref}}(y \mid x)}$$

Plugging this back into the RLHF objective and simplifying gives the DPO loss — exactly what you implemented in T5:

$$\mathcal{L}_{\text{DPO}} = -\log \sigma\!\left(\beta \left[\log \frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)} - \log \frac{\pi_\theta(y_l \mid x)}{\pi_{\text{ref}}(y_l \mid x)}\right]\right)$$

| Symbol             | Meaning                                                      |
| ------------------ | ------------------------------------------------------------ |
| $\pi_\theta$       | The trainable model (your LoRA-wrapped SFT model)            |
| $\pi_{\text{ref}}$ | The frozen reference model (the merged SFT model, unchanged) |
| $y_w$              | The **chosen** (preferred, "winner") response                |
| $y_l$              | The **rejected** (worse, "loser") response                   |
| $\beta$            | How much divergence from the reference is allowed            |
| $\sigma$           | Sigmoid function — converts the gap to a probability         |

---

## What the Loss Is Actually Doing — Step by Step

Take a single preference pair:

```
Prompt:    "What is backpropagation?"
Chosen:    "Backpropagation computes gradients by applying the chain rule..."
Rejected:  "Backpropagation is a training algorithm."
```

**Step 1 — Measure how much more the trainable model likes the chosen response compared to the reference model:**
$$\log \frac{\pi_\theta(\text{chosen} \mid x)}{\pi_{\text{ref}}(\text{chosen} \mid x)}$$
If the trainable model assigns higher log-prob to chosen than the reference did → positive number (good)

**Step 2 — Measure how much more the trainable model likes the rejected response compared to the reference:**
$$\log \frac{\pi_\theta(\text{rejected} \mid x)}{\pi_{\text{ref}}(\text{rejected} \mid x)}$$
If the trainable model assigns higher log-prob to rejected than the reference did → positive number (bad — we want this to go negative)

**Step 3 — The loss rewards the gap between these two ratios:**
$$\text{gap} = \text{step 1} - \text{step 2}$$
A large positive gap means "the trainable model improved on chosen more than it improved on rejected" → low loss → good.
A negative gap means the opposite → high loss → gradient pushes back.

The $\beta$ scaling and $\sigma$ (sigmoid) turn this gap into a probability-like value and stabilise the gradient magnitude.

**The practical effect:** Each training step simultaneously nudges the model toward producing "Backpropagation computes gradients by applying the chain rule..." style responses and away from producing "Backpropagation is a training algorithm." style responses — relative to its SFT baseline.

---

<a id="section-26"></a>
# 26 — 4.1 DPO Dataset Preparation

## The Dataset: `argilla/distilabel-intel-orca-dpo-pairs`

This dataset was created by running many prompts through multiple LLMs, then using a stronger model (GPT-4) to judge which response was better. Each row has:

| Field            | Content                                                    |
| ---------------- | ---------------------------------------------------------- |
| `system`         | System message prefix (e.g. "You are a helpful assistant") |
| `input`          | The user's question                                        |
| `chosen`         | The preferred response (the one GPT-4 rated higher)        |
| `rejected`       | The worse response                                         |
| `chosen_score`   | GPT-4's quality score for the chosen response (1–10)       |
| `status`         | `"chosen"` or `"tie"`                                      |
| `in_gsm8k_train` | Whether this prompt appears in the GSM8k math benchmark    |

## The Three Filters — Why Each One Matters

**1. Remove ties (`status != "tie"`)**

A "tie" means the judge couldn't decide which response was better. The DPO loss trains on the _gap_ between chosen and rejected. If there is no real gap (both are equally good), the loss has no meaningful signal — the gradient would point in a random direction and pollute the adapter weights with noise.

**2. Keep only high-confidence chosen (`chosen_score >= 8`)**

Even among non-tie rows, some "chosen" responses are only marginally better than "rejected." If the margin is tiny, the gradient is tiny, and you need many more steps to learn anything. Keeping only rows where the chosen response scored 8 or above (on a 1–10 scale) ensures every training example has a clear, unambiguous preference signal. This filter drops roughly half the dataset (~13,000 → ~6,000 rows).

**3. Remove GSM8k contamination (`not in_gsm8k_train`)**

GSM8k is a popular math reasoning benchmark. If your training data contains the same prompts that appear in that benchmark, your evaluation scores on GSM8k become meaningless — the model has seen the answers. This is called **benchmark contamination** and it is a serious problem in LLM evaluation. Removing these rows keeps your benchmark results honest.

## The `format_prompt` Function

DPOTrainer expects exactly three string fields in every row: `"prompt"`, `"chosen"`, `"rejected"`. The function maps the raw dataset columns into this structure:

```python
def format_prompt(example):
    system   = "<|system|>\n"   + example["system"]   + "</s>\n"
    prompt   = "<|user|>\n"     + example["input"]    + "</s>\n<|assistant|>\n"
    chosen   = example["chosen"]   + "</s>\n"
    rejected = example["rejected"] + "</s>\n"
    return {"prompt": system + prompt, "chosen": chosen, "rejected": rejected}
```

**Why the system prefix goes into `"prompt"` and not a separate field:** DPOTrainer concatenates `prompt + chosen` and `prompt + rejected` to form the two full sequences it scores. The system message is part of the context for both, so it belongs in `"prompt"`.

**Why `</s>` at the end of chosen and rejected:** The `</s>` end-of-sequence token is the model's signal to stop generating. Without it, the trainer would compute log-probs over an incomplete sequence — the model would never learn when to stop.

After `dpo_dataset.map(format_prompt, remove_columns=dpo_dataset.column_names)` every row looks like:

```
{
  "prompt":   "<|system|>\nYou are a helpful assistant...</s>\n<|user|>\nWhat is backprop?</s>\n<|assistant|>\n",
  "chosen":   "Backpropagation computes gradients by applying the chain rule...</s>\n",
  "rejected": "Backpropagation is a training algorithm.</s>\n"
}
```

---

<a id="section-27"></a>
# 27 — 4.2 Load Quantized SFT Model

## Why DPO Starts from the SFT Model, Not the Base Model

DPO needs **two** models:

1. A **trainable model** — gets updated by gradients (LoRA adapters on top of frozen base)
2. A **frozen reference model** ($\pi_{\text{ref}}$) — never updated, represents the SFT baseline

The reference model is the anchor. The DPO loss measures "how much did the trainable model move relative to the reference?" If both models started from the raw base (before SFT), the reference would have no instruction-following capability — the loss would be comparing a trained model to a completely untrained one, which doesn't produce useful preference gradients.

By starting from the **SFT-merged model** for both, the reference already knows how to follow instructions. DPO then refines the _quality_ of those instructions on top of the SFT behaviour.

**The DPOTrainer handles this automatically:** when you pass the model and a `peft_config`, it keeps a frozen copy of the model at init time as $\pi_{\text{ref}}$ and only updates the LoRA adapter in the trainable copy.

## What This Cell Does

The loading sequence in this section is:

1. Load `sft-qlora-adapter` in **bfloat16** — `torch_dtype=torch.bfloat16`, no `quantization_config`
2. Call `merge_and_unload()` — fuses the adapter into the base weights, producing a clean bfloat16 model
3. Define `bnb_config` — ready for section 4.3, **not used here**

**Why load in bfloat16 and not 4-bit?** `merge_and_unload()` computes $W' = W + \frac{\alpha}{r}AB$ — full matrix arithmetic. Doing this on clean bfloat16 weights gives an accurate merged model. If you passed `quantization_config` here, the base model would load in 4-bit and `merge_and_unload()` would have to dequantize everything back to bfloat16 anyway to do the math — pointless overhead.

**Where does `bnb_config` actually get used?** In section 4.3, `prepare_model_for_kbit_training(model)` re-quantizes the bfloat16-merged model to 4-bit NF4 for DPO training. Defining `bnb_config` here keeps it close to where it is conceptually introduced (same config as section 2.2) and makes it available in the notebook's global scope when section 4.3 runs.

```python
from peft import AutoPeftModelForCausalLM
from transformers import BitsAndBytesConfig, AutoTokenizer
import torch

# Define bnb_config here — used in section 4.3, NOT passed to from_pretrained
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# Load in bfloat16 for a clean merge — no quantization_config here
model = AutoPeftModelForCausalLM.from_pretrained(
    "./results/sft-qlora-adapter",
    low_cpu_mem_usage=True,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
model = model.merge_and_unload()   # SFT weights now baked in as clean bfloat16

model_name = "TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
tokenizer.pad_token = "<PAD>"
tokenizer.padding_side = "left"
```

---

<a id="section-28"></a>
# 28 — 4.3 LoRA Configuration for DPO

The LoRA config is **identical** to the one used in SFT (section 2.3): same rank, same alpha, same target modules.

This makes sense — you are still training a small set of adapter matrices on top of a frozen base model. The difference is _what_ those adapters will learn:

|                      | SFT LoRA (sections 1.3 / 2.3)    | DPO LoRA (section 4.3)                         |
| -------------------- | -------------------------------- | ---------------------------------------------- |
| **Attached to**      | Raw frozen base model            | SFT-merged frozen model                        |
| **Learns from**      | `(prompt, ideal_response)` pairs | `(prompt, chosen, rejected)` triplets          |
| **What it learns**   | How to follow the chat format    | How to prefer better responses over worse ones |
| **Starting weights** | A=random, B=0                    | A=random, B=0 (fresh adapter)                  |

The fresh `B=0` initialisation is important. At step 1, both the trainable model and the reference model produce **identical** outputs (since the LoRA update is $\frac{\alpha}{r}AB = 0$). This is why `warmup_ratio=0.1` in the training config is specifically critical for DPO — explained in section 29.

### Your Code

```python
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model

peft_config = LoraConfig(
    lora_alpha=32,
    lora_dropout=0.1,
    r=64,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=['k_proj', 'gate_proj', 'v_proj', 'up_proj', 'q_proj', 'o_proj', 'down_proj']
)

model = prepare_model_for_kbit_training(model)
model.config.name_or_path = model_name  # restore after prepare_model_for_kbit_training wipes it
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()
```

### ⚠️ The `name_or_path` Fix Applies Here Too

This is the same fix from section 2.3. `prepare_model_for_kbit_training` wipes `model.config.name_or_path` every time it is called — regardless of whether the model is a freshly downloaded base model or a merged SFT model. Without the restore line, the saved `dpo-adapter/adapter_config.json` will have `base_model_name_or_path: null`, and loading the adapter later will crash with the same `RepositoryNotFoundError: https://huggingface.co/None/...` you saw in section 2.6.

`model_name` is already in scope from the line you defined it in section 4.2 — no need to redefine it here.

---

<a id="section-29"></a>
# 29 — 4.4 DPO Training Configuration

DPO uses `DPOConfig` instead of `TrainingArguments`. Most parameters are the same as SFT, but three are different — and each change has a specific mathematical reason.

### `learning_rate=1e-5` — 20× Lower Than SFT

SFT uses `2e-4`. DPO uses `1e-5`.

During SFT, the adapter matrices start from random initialisation and need large steps to learn the basic chat format from scratch. A learning rate of `2e-4` is fast enough to converge in one epoch.

During DPO, the model already knows how to follow instructions — the SFT adapter is baked in. DPO is making **subtle adjustments** to preference ordering, not teaching the model a new skill. With `2e-4`, a single step could catastrophically overwrite the SFT-learned instruction-following by over-adjusting the log-probability ratios. `1e-5` makes each step tiny, preserving what SFT built while carefully nudging preferences.

**The analogy:** SFT is learning to drive a car from scratch — you need large corrections. DPO is parallel parking a car you can already drive — tiny, careful adjustments.

### `warmup_ratio=0.1` — Specifically Critical for DPO

At step 1 of DPO training, the LoRA adapter has `B=0`. This means:

$$\pi_\theta(y \mid x) = \pi_{\text{ref}}(y \mid x) \quad \text{(identical at step 1)}$$

So the log-probability ratios in the DPO loss are both exactly 0:
$$\log \frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)} = 0 \qquad \log \frac{\pi_\theta(y_l \mid x)}{\pi_{\text{ref}}(y_l \mid x)} = 0$$

The gap is 0 − 0 = 0. There is no informative gradient direction — it is pure noise from floating-point arithmetic. If you apply full-strength updates (`learning_rate=1e-5`) to a purely noise gradient for the first 10% of steps, those noisy updates accumulate and damage the adapter before it has any real signal.

`warmup_ratio=0.1` linearly scales the learning rate from 0 up to `1e-5` over the first 10% of steps (first 20 steps out of 200). By the time the learning rate reaches full strength, the adapter has picked up a coherent initial direction from many small updates.

### `max_steps=200` — Short Demo Run

A full DPO epoch over 6,000 examples with batch size 2 and gradient accumulation 4 would be 750 steps. `max_steps=200` runs only the first 200 steps — enough to see the loss decreasing and the preference mechanism working, without waiting the full training time. For production, remove `max_steps` and use `num_train_epochs=1` instead.

### Full Config

```python
from trl import DPOConfig

training_arguments = DPOConfig(
    output_dir="./results/dpo",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    optim="paged_adamw_32bit",
    learning_rate=1e-5,           # 20× lower than SFT
    lr_scheduler_type="cosine",
    max_steps=200,
    logging_steps=10,
    bf16=True,
    gradient_checkpointing=True,
    warmup_ratio=0.1,             # warm up for first 10% of steps
    save_strategy="steps",
    save_steps=50,                # 200 ÷ 50 = 4 checkpoints; final step 200 always saved
    save_total_limit=3,
    report_to="tensorboard",
)
```

### `save_steps=50` — Why 50?

With `max_steps=200`, checkpoints land at 50, 100, 150, **200** — the final step is always captured (200 is divisible by 50). `save_total_limit=3` keeps the last three on disk (100, 150, 200), deleting the oldest automatically.

This mirrors the same crash-recovery logic from Parts 1 and 2 (`save_steps=75` there, because 375 ÷ 75 = 5). The rule is the same: choose a `save_steps` that divides evenly into the total step count so the final step is always checkpointed.

### `report_to="tensorboard"`

Same as Parts 1 and 2 — writes loss and LR logs to `results/dpo/runs/`. Running `tensorboard --logdir results/` from the `code/` directory shows all three training runs (SFT LoRA, SFT QLoRA, DPO) as separate named curves you can compare side by side.

---

<a id="section-30"></a>
# 30 — 4.5 Train with DPOTrainer

## The Four Forward Passes

Every single training step, `DPOTrainer` runs **four forward passes** before computing any gradient:

```
One batch = {prompt, chosen, rejected}

Pass 1:  trainable model  (π_θ)  →  log π_θ(chosen  | prompt)
Pass 2:  trainable model  (π_θ)  →  log π_θ(rejected | prompt)
Pass 3:  reference model  (π_ref) →  log π_ref(chosen  | prompt)
Pass 4:  reference model  (π_ref) →  log π_ref(rejected | prompt)
```

These four scalars are plugged into the DPO loss formula. Then one backward pass runs through only the trainable model (pass 1 and 2 paths) — the reference model is frozen so no gradient flows through passes 3 and 4.

This is why DPO training is roughly 2× slower per step than SFT: SFT runs one forward + one backward; DPO runs four forwards + one backward.

## The `beta` Parameter

`beta=0.1` controls how strongly the KL-divergence penalty (the "don't drift too far from reference" term) is enforced.

| `beta`  | Behaviour                                                                                                                |
| ------- | ------------------------------------------------------------------------------------------------------------------------ |
| 0.01    | Very aggressive — model can drift far from SFT. Strong preference alignment but risk of forgetting instruction-following |
| **0.1** | **Balanced — standard for most DPO runs**                                                                                |
| 0.5+    | Conservative — model stays very close to SFT output. Safer but weaker preference alignment                               |

Mathematically, $\beta$ scales the implicit reward: $r(x, y) = \beta \log \frac{\pi_\theta(y|x)}{\pi_{\text{ref}}(y|x)}$. A larger $\beta$ means you are willing to pay a larger KL penalty for the same reward gain — which discourages large divergences from the reference.

## What Loss Looks Like During DPO Training

Unlike SFT where loss decreases monotonically from ~1.6 toward ~1.2, DPO loss behaves differently:

- It starts near `log(2) ≈ 0.69` — the value when chosen and rejected are indistinguishable (random 50/50)
- It decreases as the model learns to separate chosen from rejected
- It typically plateaus around 0.3–0.5 for a 200-step run

A decreasing DPO loss means the model is getting better at assigning higher probability to chosen responses relative to rejected ones — relative to the frozen reference baseline.

## Plotting the DPO Training Curve

After training, run the plot cell to visualise the loss and LR schedule. It reads the `trainer_state.json` from the latest checkpoint in `results/dpo/` — the same pattern as Parts 1 and 2.

```python
%matplotlib inline
import json, os
import matplotlib.pyplot as plt

checkpoints = sorted(
    [d for d in os.listdir("./results/dpo") if d.startswith("checkpoint-")],
    key=lambda x: int(x.split("-")[1])
)
latest = f"./results/dpo/{checkpoints[-1]}/trainer_state.json"

with open(latest) as f:
    state = json.load(f)

steps  = [e["step"] for e in state["log_history"] if "loss" in e]
losses = [e["loss"] for e in state["log_history"] if "loss" in e]
lrs    = [e["learning_rate"] for e in state["log_history"] if "loss" in e]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
fig.suptitle("TinyLlama DPO Training — Part 4", fontsize=13, fontweight="bold")

ax1.plot(steps, losses, color="steelblue", linewidth=1.5, alpha=0.8)
ax1.axhline(y=0.69, color="gray", linestyle="--", linewidth=1, label="log(2) ≈ 0.69 (random baseline)")
ax1.set_ylabel("DPO Loss")
ax1.set_xlabel("Step")
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.set_title("DPO Loss Curve")

ax2.plot(steps, lrs, color="darkorange", linewidth=1.5)
ax2.set_ylabel("Learning Rate")
ax2.set_xlabel("Step")
ax2.grid(True, alpha=0.3)
ax2.set_title("Cosine LR Schedule with Warmup")

os.makedirs("./results/plots", exist_ok=True)
plt.tight_layout()
plt.savefig("./results/plots/dpo_training_curve.png", dpi=150, bbox_inches="tight")
plt.show()
plt.close(fig)
print("Saved to results/plots/dpo_training_curve.png")
```

**What to look for in the DPO loss curve:**

| Pattern | What it means |
|---------|---------------|
| Loss starts near 0.69 and decreases | Normal — model is learning to separate chosen from rejected |
| Loss drops sharply then flattens | Warmup working correctly — big gains in early steps after warmup ends |
| Loss stays flat at 0.69 | No learning — check that chosen and rejected are actually different strings |
| Loss goes below 0.3 quickly | Possible overfitting — model too aggressively diverging from reference |

The dashed `log(2) ≈ 0.69` reference line marks the "random baseline" — what the loss equals when the model treats chosen and rejected as equally likely. Any value below this line means the model is successfully preferring chosen responses.

---

<a id="section-31"></a>
# 31 — 4.6 Stack and Merge Both Adapters

This section implements the complete two-stage merge pipeline that produces the final aligned model. After this cell, you have a single standard `AutoModelForCausalLM` with both SFT knowledge and DPO preference alignment permanently baked in.

## Why Stack Adapters Instead of Training One Adapter for Everything?

You could theoretically train one LoRA adapter that does both SFT and DPO simultaneously. But the two training objectives conflict:

- **SFT loss** wants the model to match a target response character-by-character — maximise log-probability of every token in the ideal answer
- **DPO loss** wants the model to increase the _ratio_ of chosen vs rejected probabilities — it doesn't care about absolute token probabilities, only relative preference

Training both losses on the same adapter at the same time produces a muddy compromise. Stacking them sequentially — first SFT, then DPO on top of a frozen SFT-merged model — keeps the objectives clean and lets each adapter specialise.

## The Two-Step Merge

```
Step 1: Load SFT adapter  →  merge into base  →  get SFT-merged model (bfloat16)
Step 2: Load DPO adapter on top of SFT-merged  →  merge  →  get final model (bfloat16)
```

**Step 1 in code:**

```python
from peft import AutoPeftModelForCausalLM, PeftModel

# Load SFT adapter and fuse it permanently into base weights
model = AutoPeftModelForCausalLM.from_pretrained(
    "./results/sft-qlora-adapter",
    low_cpu_mem_usage=True,
    device_map="auto",
)
sft_model = model.merge_and_unload()
# sft_model is now a plain AutoModelForCausalLM — no PEFT overhead
```

**Step 2 in code:**

```python
# Load DPO adapter on top of the already-SFT-merged model
dpo_model = PeftModel.from_pretrained(
    sft_model,
    "./results/dpo-adapter",
    device_map="auto",
)
final_model = dpo_model.merge_and_unload()
# final_model has both SFT and DPO baked in — ready for inference
```

**Why bfloat16 for both merge steps?** At inference time there is no need for 4-bit compression — you are not training. `merge_and_unload()` does the matrix arithmetic $W' = W + \frac{\alpha}{r}AB$ in full precision. Loading in bfloat16 gives a clean, accurate merged model at ~2.2 GB — the same size as the original bfloat16 base model.

## What the Final Folder Structure Looks Like

```
results/
├── sft-lora/                   ← Part 1 training checkpoints
├── sft-lora-adapter/           ← Part 1 final adapter
├── sft-qlora/                  ← Part 2 training checkpoints
├── sft-qlora-adapter/          ← Part 2 final adapter
├── dpo/                        ← Part 4 training checkpoints
├── dpo-adapter/                ← Part 4 final DPO adapter
└── plots/
    ├── training_curve.png
    └── qlora_training_curve.png
```

---

<a id="section-32"></a>
# 32 — 4.7 Final Aligned Model Inference

## What DPO Should Have Changed

The SFT model (from Parts 1/2) knows how to follow the `<|user|>` / `<|assistant|>` format and can produce coherent answers. The DPO model has been additionally trained to prefer responses that a stronger judge (GPT-4) rated as higher quality. Concretely, you should see:

| Aspect                     | SFT model                              | DPO-aligned model                                                                                |
| -------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **Response length**        | Can be brief or vague                  | Tends toward more complete, structured answers                                                   |
| **Instruction following**  | Follows format                         | Also follows implicit quality expectations                                                       |
| **Hedging on uncertainty** | May state uncertain things confidently | More likely to qualify claims it is unsure about                                                 |
| **Refusals / safety**      | Minimal — SFT data was not adversarial | Slightly more likely to decline harmful requests if training data included such preference pairs |

These differences are subtle, especially after only 200 training steps. With a full epoch over 6,000 preference pairs, the gap becomes more pronounced.

## Temperature Sampling

The notebook suggests trying different `temperature` values. Temperature controls how "peaked" the probability distribution is at each generation step:

```python
# Deterministic — always picks the highest-probability token
pipe(prompt, max_new_tokens=200, temperature=0.1, do_sample=True)

# Balanced — standard for chat
pipe(prompt, max_new_tokens=200, temperature=0.7, do_sample=True)

# Creative — more diverse, occasionally surprising word choices
pipe(prompt, max_new_tokens=200, temperature=0.9, do_sample=True)
```

- **Low temperature (0.1):** The model almost always picks the most likely token at each step. Responses are consistent, often repetitive, safe.
- **High temperature (0.9):** Less likely tokens get more chances. Responses are more varied and sometimes more creative, but also more prone to going off-topic.

For evaluating whether DPO actually helped, use **low temperature** — you want the model's most confident output, not a lucky high-temperature sample. Temperature only affects generation, not what the model learned.

## The Definitive Test

Run the same prompt through three models and compare:

```python
prompt = """<|user|>
Tell me something about Large Language Models.</s>
<|assistant|>
"""

# Base model (no fine-tuning) — loads from HuggingFace fresh
# SFT model — your Part 1 or Part 2 merged model
# DPO model — your final_model from 4.6
```

What to look for:

- **Base:** likely autocompletes in a non-conversational way, ignores the `<|assistant|>` tag
- **SFT:** produces a valid assistant response, follows the format
- **DPO:** same format, but the content should be more detailed, better structured, with clearer explanations — the qualities that GPT-4 consistently rated higher in the training data

---

## What We Actually Observed — Real Results from This Run

This is what the three models actually produced on the prompt `"Tell me something about Large Language Models."`:

### QLoRA SFT model output (baseline):
- Correctly followed the `<|assistant|>` format ✅
- Mentioned "trained on Wikipedia" — a vague and slightly inaccurate description
- Three paragraphs covering: what LLMs are, applications (NLP, translation, chatbots), advantages (human-like language, understanding context)
- Repetitive — "generate human-like language" appears multiple times

### DPO model — 200 steps:
- Same format ✅
- **Corrected "Wikipedia" to "text, speech, or images"** — more accurate ✅
- Added a new section on "learning from experience"
- Added multilingual capability section
- Less repetitive, slightly more varied structure ✅

### DPO model — full epoch (750 steps):
- Same format ✅
- **Regressed back to "trained on Wikipedia"** — less accurate than the 200-step version ❌
- More repetitive than the 200-step version
- Structurally similar to the SFT baseline

### What the loss curve told us

Looking at the DPO training plot:

| Phase | Steps | What happened |
|-------|-------|---------------|
| Warmup | 0–75 | LR ramps from 0 → 1e-5; loss drops from 0.69 → 0.58 cleanly |
| Fast learning | 75–200 | Full LR kicks in; loss drops sharply to ~0.50 — biggest preference gains here |
| Noisy mid-training | 200–400 | High variance; spike to 0.75 around step 330 (above the 0.69 random baseline) |
| Late training | 400–670 | Settles around 0.55–0.60 but never smooths out |

The spike above 0.69 at step 330 means the model briefly assigned higher probability to the *rejected* response than the *chosen* one for that batch — a sign of gradient instability. The persistent noise throughout training (loss oscillating 0.45–0.75) indicates the model is struggling to consistently learn from the preference pairs.

### Why small models behave this way

TinyLlama at 1.1B parameters is near the lower limit for DPO to be stable. The problem is capacity:

* **SFT** is relatively forgiving — even if the model can't perfectly imitate every response, it averages across the dataset and arrives at a reasonable middle ground.
* **DPO** requires the model to simultaneously maintain high probability on chosen responses *and* low probability on rejected responses *relative to the reference model*. With only 1.1B parameters, there are not enough independent weight dimensions to encode 6,000 distinct preference relationships without some of them interfering with each other.

The result: the model learns some preferences well (the 200-step checkpoint correctly drops "Wikipedia"), but as training continues on more varied pairs, later updates partially overwrite earlier ones. The final checkpoint is an average of all 750 update steps — not always better than an intermediate one.

**On a 7B+ model** (like Mistral-7B or Llama-3-8B), the same training recipe typically produces a monotonically improving loss curve and a clearly better final model. The larger weight space gives each preference pair room to be encoded without trampling over others.

### The Key Practical Lesson: Checkpoint Selection

This is something most tutorials skip, but it is critical in real fine-tuning work:

> **The final training checkpoint is not always the best model.** Evaluate several checkpoints and keep the one that performs best on your actual use case — not just the one with the lowest final loss.

In this run, checkpoint-200 produced a better factual description than checkpoint-750. Because `save_total_limit=3` discarded checkpoint-200 automatically, we cannot go back to it without retraining. This is why for production DPO runs you should:

1. Set a higher `save_total_limit` (e.g. 5–10) so more intermediate checkpoints survive
2. Run a quick qualitative evaluation on 10–20 representative prompts at each saved checkpoint
3. Only then pick the adapter to ship

The loss curve is a useful signal but is not the final word. A checkpoint with slightly higher final loss can still produce better outputs for your specific task if the evaluation prompts happen to align better with what that checkpoint learned.

### What You Would Do Differently on a Larger Model

| Decision | TinyLlama-1.1B (this run) | 7B model (production) |
|----------|--------------------------|----------------------|
| DPO epochs | 1 (already noisy) | 1–3 |
| `beta` | 0.1 (standard) | 0.1–0.3 (can afford more conservative) |
| `save_total_limit` | 3 (too few) | 5–10 |
| Loss curve shape | Noisy, spikes above baseline | Smooth monotonic decrease |
| Checkpoint selection | Critical — intermediate often better | Final usually best |
| Expected improvement | Subtle, sometimes regresses | Clear, measurable gains |
