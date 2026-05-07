# Chapter 12: Fine-Tuning Generation Models

## Hands-On Large Language Models — Chapter 12

> A pretrained model knows the world. A fine-tuned model knows what you need. The art of fine-tuning is bridging that gap as efficiently as possible — and in this chapter, we learn exactly how.

---

## Table of Contents

1. [The Three LLM Training Steps](#1-the-three-llm-training-steps)
   - [1a. Step 1 — Pretraining: Learning the World](#1a-step-1--pretraining-learning-the-world)
   - [1b. Step 2 — Supervised Fine-Tuning: Learning to Be Useful](#1b-step-2--supervised-fine-tuning-learning-to-be-useful)
   - [1c. Step 3 — Preference Tuning: Learning to Be Good](#1c-step-3--preference-tuning-learning-to-be-good)
2. [Supervised Fine-Tuning (SFT)](#2-supervised-fine-tuning-sft)
   - [2a. Full Fine-Tuning — Updating Everything](#2a-full-fine-tuning--updating-everything)
   - [2b. Parameter-Efficient Fine-Tuning and Adapters](#2b-parameter-efficient-fine-tuning-and-adapters)
   - [2c. Low-Rank Adaptation (LoRA)](#2c-low-rank-adaptation-lora)
   - [2d. Quantization and QLoRA](#2d-quantization-and-qlora)
3. [Instruction Tuning with QLoRA — Practical Walkthrough](#3-instruction-tuning-with-qlora--practical-walkthrough)
   - [3a. Dataset Preparation and Chat Templates](#3a-dataset-preparation-and-chat-templates)
   - [3b. Model Quantization — The BitsAndBytes Config](#3b-model-quantization--the-bitsandbytes-config)
   - [3c. LoRA Configuration — Every Parameter Explained](#3c-lora-configuration--every-parameter-explained)
   - [3d. Training Arguments — What They Actually Do](#3d-training-arguments--what-they-actually-do)
   - [3e. SFTTrainer and the Training Loop](#3e-sfttrainer-and-the-training-loop)
   - [3f. Merging LoRA Weights for Inference](#3f-merging-lora-weights-for-inference)
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

Before a single line of fine-tuning code is written, it helps to understand the full journey a language model takes from random weights to a polished assistant. The journey has three distinct stages, and each stage solves a problem that the previous stage left unsolved. Understanding why each stage exists — not just what it does — is the key to understanding every technique in this chapter.

### 1a. Step 1 — Pretraining: Learning the World

The first stage is **pretraining**, and it is where the model learns almost everything it will ever know. The training data is enormous — hundreds of billions of tokens scraped from books, websites, code repositories, academic papers, Wikipedia, and countless other sources. The training objective is deceptively simple: given the previous words in a sentence, predict the next word. That is it. No labels, no human annotations, no structured questions and answers. Just next-token prediction repeated billions of times.

This simple objective forces the model to become extraordinarily good at language. To predict the next word well, you need to understand grammar, facts about the world, reasoning patterns, coding conventions, mathematical relationships, and much more. The model that emerges from pretraining is called a **base model** or **foundation model**. It has absorbed the structure and content of human language at a scale no human will ever read in a lifetime.

But here is the critical problem with base models: they cannot follow instructions. If you type "What is reinforcement learning?" into a raw base model, it will not answer your question. Instead, it will continue the pattern of whatever text looks like it belongs after that question. It might output "What is recurrent neural network? What is residual connection?" — because the training data contained many lists of "What is X?" questions. The model is completing a text pattern, not responding to a query. Think of it like a student who has read every textbook in the library, but has never once been asked to answer an exam question. They have all the knowledge — but no practice converting that knowledge into a useful response.

```
[Unlabeled Internet Text — billions of tokens]
        │
        ▼
  [Pretraining: next-token prediction]
        │
        ▼
  Base Model
  ✓ Knows language deeply
  ✓ Knows facts about the world
  ✗ Will not follow instructions
  ✗ Will complete patterns instead of answering
```

### 1b. Step 2 — Supervised Fine-Tuning: Learning to Be Useful

The second stage is **Supervised Fine-Tuning (SFT)**, sometimes called **instruction tuning**. The goal is to teach the model to respond to instructions rather than merely continue text. The training data is completely different: instead of raw internet text, we use a curated set of question–answer pairs, instruction–response pairs, and multi-turn conversations. The training objective is the same (predict the next token) but the context has fundamentally changed — the model now sees a user asking a question and must learn to generate the assistant's response.

The dataset is far smaller than pretraining data — perhaps a few thousand to a few hundred thousand examples, compared to billions of tokens. But the impact is dramatic. A model that was pattern-completing text becomes a model that actually answers questions, follows formatting instructions, summarises documents, and writes code. The result is an **instruction-tuned model**.

### 1c. Step 3 — Preference Tuning: Learning to Be Good

Even after instruction tuning, the model can still be unhelpful in subtle ways. It might give technically correct answers that are unnecessarily long, or give two answers to a question when one would do, or be evasive when the user wants directness. The model follows instructions but has no sense of *which* way of following them is better.

**Preference tuning** solves this. Also called **alignment** or — in its most famous form — **RLHF (Reinforcement Learning from Human Feedback)**, this third stage teaches the model to prefer certain kinds of responses over others. The training data is not instruction–response pairs but **preference pairs**: two responses to the same prompt, where one is labelled "chosen" (preferred) and one is labelled "rejected" (not preferred). The model learns to generate the kind of responses that humans prefer: helpful, honest, appropriately concise, and safe.

```
[Unlabeled Internet Text]
        │
        ▼
  [Pretraining] ─────────────────► Base Model
  (billions of tokens, self-supervised) (knows language, won't follow instructions)
        │
        ▼
  [Supervised Fine-Tuning] ──────► Instruction-Tuned Model
  (instruction–response pairs)          (follows prompts)
        │
        ▼
  [Preference Tuning] ───────────► Aligned Model
  (chosen vs rejected pairs)            (helpful, honest, safe)
```

This three-stage pipeline is how every major commercial LLM — ChatGPT, Claude, Gemini — is built. Pretraining provides the knowledge. SFT provides the interface. Preference tuning provides the character. The rest of this chapter teaches you to execute the last two stages yourself.

---

## 2. Supervised Fine-Tuning (SFT)

### 2a. Full Fine-Tuning — Updating Everything

The most straightforward approach to fine-tuning is to do exactly what was done during pretraining: compute a loss, compute gradients, and update every single parameter in the model. This is called **full fine-tuning**. The only difference from pretraining is the data: instead of raw internet text, the training signal comes from labelled instruction–response pairs.

The instruction data has a simple structure. Each example contains an instruction (the user's request) and a response (the ideal assistant reply). During training, the model sees the instruction and must predict each token of the response one at a time. The loss is computed only over the response tokens — we are teaching the model to generate the answer, not to predict the question that was already given.

```python
# A single instruction-tuning data point
{
    "instruction": "Explain what reinforcement learning is in two sentences.",
    "response": "Reinforcement learning is a type of machine learning where "
                "an agent learns by taking actions in an environment and "
                "receiving rewards or penalties. Over time, the agent learns "
                "a policy that maximises its cumulative reward."
}
```

Full fine-tuning produces the best results — the model adapts completely to the target task. But it has a severe practical problem. To update every parameter, you need to store every parameter's gradient in memory alongside the parameter values themselves. For GPT-3 with 175 billion parameters stored in float32 (4 bytes each), the parameters alone consume 700 GB of memory. The gradients consume another 700 GB. Add the optimizer state (Adam stores two momentum terms per parameter) and you need roughly 2.1 terabytes of GPU memory. No single GPU, and very few clusters, can accommodate that.

```
Full Fine-Tuning Memory Footprint (GPT-3, float32):

  Parameters:          175B × 4 bytes  =   700 GB
  Gradients:           175B × 4 bytes  =   700 GB
  Optimizer state:     175B × 8 bytes  = 1,400 GB
                                         ─────────
  Total required:                        2,800 GB
```

This memory wall is why the field developed parameter-efficient alternatives.

---

### 2b. Parameter-Efficient Fine-Tuning and Adapters

The key insight behind **Parameter-Efficient Fine-Tuning (PEFT)** is that you do not need to update all the parameters to make the model useful for a new task. Research by Houlsby et al. showed something surprising: fine-tuning only 3.6% of BERT's parameters on a target task achieved within 0.4% of the performance of full fine-tuning on the GLUE benchmark. Nearly all the task-specific information fits in a tiny fraction of the model's capacity.

Why does this work? Think about how you learn a new skill. When you learn to ride a bicycle, you do not rewire your entire brain. You build a small overlay of new coordination patterns on top of your existing motor system, vocabulary, and spatial reasoning. The vast majority of your neural infrastructure stays unchanged. Fine-tuning a transformer works the same way — the model's deep understanding of language is already encoded in the pretrained weights and largely does not need to change. Only a small task-specific component needs to be learned.

**Adapters** were the first major PEFT approach. An adapter is a small, trainable module inserted inside each transformer block. The rest of the transformer — all the attention layers and feed-forward networks — remains completely frozen. Only the adapter modules are updated during training.

```
A Transformer Block with Adapter Modules:

  Input
    │
    ▼
  [Multi-Head Attention]   ← FROZEN
    │
    ▼
  [Add & LayerNorm]        ← FROZEN
    │
    ▼
  [Adapter Module]         ← TRAINABLE (tiny bottleneck)
    │   down-proj (d → small_dim)
    │   nonlinearity
    │   up-proj (small_dim → d)
    ▼
  [Feed-Forward Network]   ← FROZEN
    │
    ▼
  [Add & LayerNorm]        ← FROZEN
    │
    ▼
  [Adapter Module]         ← TRAINABLE (tiny bottleneck)
    │
    ▼
  Output
```

Each adapter has a **bottleneck architecture**: it first projects the hidden representation down to a very small dimension (e.g., from 768 to 64), applies a nonlinearity, then projects back up to the original dimension. The down-projection and up-projection weights are the only trainable parameters. The bottleneck forces the adapter to learn a compressed, task-relevant transformation — it cannot simply memorise the training data because there are not enough parameters to do so.

The **AdapterHub** framework emerged as a community hub where researchers could share adapter weights for different tasks and languages, all compatible with the same base model. You could download an adapter trained on medical text classification and plug it into a frozen BERT, without touching the base model weights at all. This composability is a major architectural advantage.

---

### 2c. Low-Rank Adaptation (LoRA)

**Low-Rank Adaptation (LoRA)** is the technique that made fine-tuning accessible to everyone. It is now the dominant PEFT method used in practice, and understanding its mathematics will make every subsequent concept in this chapter click into place.

LoRA starts from a different observation than adapters. Rather than inserting new modules between frozen layers, LoRA asks: what if we directly model the *change* that fine-tuning would make to the weight matrices? If we understood the structure of that change, maybe we could represent it compactly.

The key insight is the concept of **intrinsic dimensionality**. When you fine-tune a large model on a specific task, the update to each weight matrix does not fill the entire high-dimensional space the matrix lives in. The meaningful changes cluster in a very small subspace. A weight matrix that has 12,288 × 12,288 = 150 million entries might only need to change in an 8-dimensional subspace to adapt to a new task. The rest of the change is effectively noise or redundancy.

LoRA exploits this by representing the weight update $\Delta W$ as the product of two much smaller matrices:

$$W' = W + \Delta W = W + \frac{\alpha}{r} \cdot A \cdot B$$

| Symbol | Meaning | Typical Value |
|--------|---------|---------------|
| $W \in \mathbb{R}^{d \times d}$ | Original frozen weight matrix | 12,288 × 12,288 in GPT-3 |
| $A \in \mathbb{R}^{d \times r}$ | Down-projection matrix, trainable | 12,288 × 8 |
| $B \in \mathbb{R}^{r \times d}$ | Up-projection matrix, trainable, **initialized to zero** | 8 × 12,288 |
| $r$ | Rank of the decomposition — controls capacity | 4 to 64 |
| $\alpha$ | Scaling factor for the magnitude of the update | typically $2r$ |

This says: instead of directly updating $W$, we learn two thin matrices $A$ and $B$ whose product approximates the weight update. The original $W$ is never touched. During the forward pass, the output is:

$$\text{output} = Wx + \frac{\alpha}{r} \cdot ABx = \left(W + \frac{\alpha}{r} AB\right)x$$

Initialising $B$ to all zeros ensures that at the very start of training, $\Delta W = AB = 0$, so the LoRA model begins as an exact copy of the pretrained model. Training then gradually fills in the $A$ and $B$ matrices to encode the task-specific update.

The $\alpha/r$ scaling factor keeps the effective magnitude of the update stable as you change $r$. If you double the rank, you double the capacity of $A$ and $B$, but dividing by $r$ in the scale keeps the total contribution to $W'$ proportional. The rule of thumb is to set $\alpha = 2r$.

```
LoRA inside a single linear layer:

         x  (input vector, shape d)
         │
    ┌────┴──────────────────────────────┐
    │                                   │
    ▼                                   ▼
  [W]  ← FROZEN                      [A]  ← trainable  (d × r)
    │    (d × d weight matrix)          │
    │                                   ▼
    │                                 [B]  ← trainable  (r × d)
    │                                   │
    │                   (A·B = low-rank update ΔW, shape d × d)
    │                                   │
    └────────────────► (+) ◄────────────┘
                        │
                        ▼
                output = Wx + (α/r)·ABx
```

**The parameter count difference is staggering.** For a single weight matrix in GPT-3 (d = 12,288) with rank r = 8:

| Method | Parameters per weight matrix | Compression |
|--------|------------------------------|-------------|
| Full fine-tuning | 12,288 × 12,288 = 150,994,944 | 1× |
| LoRA rank 8 | 12,288×8 + 8×12,288 = 196,608 | **768× fewer** |

**Dry-run — LoRA matrix decomposition with tiny numbers:**

```
Setup: d = 4 (toy model dimension), r = 1 (rank 1)

Original weight matrix W (frozen, shape 4×4):
  W = [[2, 0, 1, 0],
       [0, 3, 0, 1],
       [1, 0, 2, 0],
       [0, 1, 0, 3]]

LoRA matrices (trainable):
  A = [[0.5],      ← shape 4×1  (d × r)
       [0.3],
       [0.7],
       [0.1]]

  B = [[0.2, 0.4, 0.1, 0.3]]   ← shape 1×4  (r × d)

Step 1: Compute ΔW = A × B
  Each row of A multiplied by B:
  Row 0: 0.5 × [0.2, 0.4, 0.1, 0.3] = [0.10, 0.20, 0.05, 0.15]
  Row 1: 0.3 × [0.2, 0.4, 0.1, 0.3] = [0.06, 0.12, 0.03, 0.09]
  Row 2: 0.7 × [0.2, 0.4, 0.1, 0.3] = [0.14, 0.28, 0.07, 0.21]
  Row 3: 0.1 × [0.2, 0.4, 0.1, 0.3] = [0.02, 0.04, 0.01, 0.03]

  ΔW = [[0.10, 0.20, 0.05, 0.15],
         [0.06, 0.12, 0.03, 0.09],
         [0.14, 0.28, 0.07, 0.21],
         [0.02, 0.04, 0.01, 0.03]]

Step 2: Compute effective weight W' = W + ΔW
  W' = [[2.10, 0.20, 1.05, 0.15],
         [0.06, 3.12, 0.03, 1.09],
         [1.14, 0.28, 2.07, 0.21],
         [0.02, 1.04, 0.01, 3.03]]

Parameter count comparison:
  Full fine-tuning:  4 × 4 = 16 parameters to update
  LoRA rank-1:       4 + 4 =  8 parameters to update   (50% saving at toy scale)
  At d=12,288, r=8:  196,608 vs 150,994,944            (768× saving at real scale)
```

**Which layers to target** is a practical decision. A transformer block contains several weight matrices: the query projection (`q_proj`), key projection (`k_proj`), value projection (`v_proj`), and output projection (`o_proj`) in multi-head attention, plus the feed-forward network's gate-projection (`gate_proj`), up-projection (`up_proj`), and down-projection (`down_proj`). Applying LoRA to all of them gives the best results. Applying it to only `q_proj` and `v_proj` is faster and often good enough for many tasks.

---

### 2d. Quantization and QLoRA

LoRA dramatically reduces the number of *trainable* parameters, but it does not reduce the memory required to *load* the base model. A 7-billion-parameter model stored in float32 still requires 28 GB of VRAM just to hold the weights. Most consumer GPUs top out at 16–24 GB. The solution is **quantization** — compressing the model weights to a lower numerical precision before loading them.

To understand quantization, you first need to understand how floating-point numbers are stored. A float32 number uses 32 bits: one bit for the sign ($\pm$), eight bits for the exponent (the scale), and twenty-three bits for the mantissa (the significant digits). This gives extraordinary precision — numbers as small as $10^{-38}$ and as large as $10^{38}$ with seven decimal digits of accuracy. Float16 halves this to 16 bits. A 4-bit integer gives only 16 possible values total.

```
Floating-point bit layout:

  float32 (32 bits):
  ┌─┬────────┬───────────────────────┐
  │S│EEEEEEEE│MMMMMMMMMMMMMMMMMMMMMMM│
  └─┴────────┴───────────────────────┘
   1    8               23              → 7 decimal digits of precision

  float16 (16 bits):
  ┌─┬─────┬──────────┐
  │S│EEEEE│MMMMMMMMMM│
  └─┴─────┴──────────┘
   1   5       10                    → 3-4 decimal digits of precision

  4-bit NF4:
  ┌────┐
  │XXXX│   → 16 possible values (non-uniform, distribution-aware)
  └────┘
```

The idea behind quantization is that LLM weights do not need float32 precision to be useful. The model learned its knowledge from the *relative patterns* between weights, not from the precise seventh decimal digit of any single weight. If we can faithfully represent the *distribution* of weights with fewer bits, the model will behave nearly identically while consuming a fraction of the memory.

**Linear quantization** maps a range of floating-point values to a grid of integer values:

$$q = \text{round}\!\left(\frac{x - x_{\min}}{x_{\max} - x_{\min}} \times (2^b - 1)\right)$$

| Symbol | Meaning |
|--------|---------|
| $x$ | Original floating-point weight value |
| $x_{\min},\, x_{\max}$ | Minimum and maximum of the weight block |
| $b$ | Number of bits ($b=4$ gives $2^4 = 16$ levels) |
| $q$ | Quantized integer code |

**Dry-run — quantizing four weights to 2 bits:**

```
Original weights: [-1.2,  0.3,  0.7,  2.1]
  x_min = -1.2,  x_max = 2.1,  range = 3.3
  2 bits → 2² = 4 levels: {0, 1, 2, 3}

  Formula:  q = round((x − (−1.2)) / 3.3 × 3)

  x = −1.2:  round(( 0.0) / 3.3 × 3) = round(0.000) = 0
  x =  0.3:  round(( 1.5) / 3.3 × 3) = round(1.364) = 1
  x =  0.7:  round(( 1.9) / 3.3 × 3) = round(1.727) = 2
  x =  2.1:  round(( 3.3) / 3.3 × 3) = round(3.000) = 3

  Quantized codes: [0, 1, 2, 3]   ← stored as 2-bit integers

Reconstruction (dequantization):  x_hat = q/3 × 3.3 + (−1.2)
  q=0 → −1.200  (exact)
  q=1 → −0.100  (original was 0.3  → error = 0.4)
  q=2 →  1.000  (original was 0.7  → error = 0.3)
  q=3 →  2.100  (exact)

Some precision is lost for interior values, but the overall distribution is preserved.
```

**The outlier problem with naive quantization.** Imagine a weight matrix where 99% of weights cluster between −0.5 and +0.5, but one weight is +50.0. When we compute $x_{\min}$ and $x_{\max}$, that single outlier stretches the entire scale to cover [−0.5, 50.0]. All of the common weights near zero now get squeezed into the lowest two or three quantization bins, losing nearly all their precision. It is like designing a ruler to measure both a pencil and a flagpole — accurate for the flagpole and useless for the pencil.

**Blockwise quantization** solves this by dividing the weight tensor into small independent blocks (typically 64 weights each) and computing separate quantization constants for each block. Each block now uses its full dynamic range for its own local distribution, preventing any single outlier from polluting the precision of distant weights.

```
Blockwise Quantization:

  Full weight tensor (many values, possible outliers):
  ┌──────────────────────────────────────────────────────────┐
  │  -0.3  +0.1  +0.4  -0.2  …  -0.5  +0.3  -0.1  +50.0   │
  └──────────────────────────────────────────────────────────┘
                          │
              split into blocks of 64 weights each
                          │
  ┌───────────────┐  ┌───────────────┐  ┌──────────────────────┐
  │ Block 1       │  │ Block 2       │  │ Block N              │
  │ range: ±0.5   │  │ range: ±0.4   │  │ range: ±50.0         │
  │ fine precision│  │ fine precision│  │ coarse (outlier only)│
  └───────────────┘  └───────────────┘  └──────────────────────┘
```

**NormalFloat (NF4) quantization** goes one step further. Uniform quantization places bins at equal intervals across the range, but LLM weights are not uniformly distributed — they follow a roughly Normal (bell-curve) distribution, with most weights near zero and very few large-magnitude weights. NF4 uses **distribution-aware bins**: more quantization levels are placed near the center (where most weights are) and fewer levels are placed in the tails (where few weights are). This minimises the average quantization error across the actual distribution of weight values, squeezing more accuracy out of those 4 bits.

**QLoRA = Quantization + LoRA**, combined into one system:

1. Load the base model in **4-bit NF4 quantization** — read-only, frozen
2. Add **LoRA adapters in float16** — trainable, tiny
3. During the forward pass, **dequantize the 4-bit weights to float16 on the fly** for computation
4. Compute gradients only through the LoRA parameters — the base model weights never receive updates

```
QLoRA Memory Architecture:

  ┌──────────────────────────────────────────────┐
  │  Base Model Weights (4-bit NF4)              │  ← FROZEN, compressed
  │  7B params × 0.5 bytes ≈ 3.5 GB              │
  │  (vs 28 GB in float32 — an 8× reduction)     │
  └──────────────────────────────────────────────┘
                      │
           [Dequantize on-the-fly for each layer's forward pass]
                      │
                      ▼
  ┌──────────────────────────────────────────────┐
  │  LoRA Adapters (float16)                     │  ← TRAINABLE
  │  A and B matrices for each targeted layer    │
  │  ~10–50 MB for a 7B model with rank 16       │
  └──────────────────────────────────────────────┘
                      │
           [Gradients flow only through LoRA]
                      │
                      ▼
              Optimizer updates only A and B
```

The practical impact is transformative. Fine-tuning a 7B model without QLoRA requires approximately 28 GB of VRAM for the weights alone, plus gradients and optimizer state. With QLoRA, the entire fine-tuning process fits comfortably in 6–8 GB — a consumer-grade GPU. This is what democratised fine-tuning outside of large AI labs.

---

## 3. Instruction Tuning with QLoRA — Practical Walkthrough

The book uses **TinyLlama-1.1B** as the base model for its practical examples. TinyLlama is a small but capable open-source model, making it fast to fine-tune and easy to experiment with on limited hardware. Despite its small size, the patterns established here apply identically to 7B, 13B, and even 70B models — you would simply adjust batch size and gradient accumulation to compensate for memory.

### 3a. Dataset Preparation and Chat Templates

The training data for instruction tuning comes from the **UltraChat** dataset — a large collection of synthetic multi-turn conversations. The book uses a filtered subset of 3,000 conversations to keep training time manageable.

Before the data reaches the model, it must be formatted using a **chat template**. Chat templates exist because instruction-tuned models are trained to recognise specific token patterns that separate the user's message from the assistant's response. If you fine-tune a model without applying the template it was trained on, the model will not know where the user message ends and where it should start generating its reply.

TinyLlama uses the following template format:

```
<|user|>
[user message here]</s>
<|assistant|>
[assistant response here]</s>
```

The special tokens `<|user|>` and `<|assistant|>` are role markers. The `</s>` end-of-sequence token tells the model where each turn ends. Without these markers, the model cannot distinguish between reading a prompt and generating a response — it would just see an undifferentiated stream of tokens.

```python
from transformers import AutoTokenizer
from datasets import load_dataset

# Load TinyLlama's tokenizer — it carries the chat template
template_tokenizer = AutoTokenizer.from_pretrained(
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
)

def format_prompt(example):
    """Apply TinyLlama's chat template to a conversation example."""
    chat = example["messages"]
    # apply_chat_template is just smart string formatting with special tokens
    prompt = template_tokenizer.apply_chat_template(chat, tokenize=False)
    return {"text": prompt}

# Load 3,000 shuffled conversations from UltraChat
dataset = (
    load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft")
    .shuffle(seed=42)
    .select(range(3_000))
)
dataset = dataset.map(format_prompt)
```

After formatting, a training example looks like this:

```
<|user|>
Given the text: Knock, knock. Who's there? Hike.
Can you continue the joke based on the given text material?</s>
<|assistant|>
Of course! Knock, knock. Who's there? Hike. Hike who? Hike your way over
here and let's go for a walk!</s>
```

The model is trained to predict each token of the assistant's reply given the full preceding context. The loss is computed only on the assistant's tokens — we do not penalise the model for "predicting" the user message, since that is given context, not generated output.

---

### 3b. Model Quantization — The BitsAndBytes Config

With the data prepared, the next step is to load the base model in 4-bit quantized form using the `bitsandbytes` library. Every parameter in the `BitsAndBytesConfig` has a specific purpose:

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                # ① Store weights as 4-bit integers
    bnb_4bit_quant_type="nf4",        # ② Use NormalFloat quantization
    bnb_4bit_compute_dtype="float16", # ③ Dequantize to float16 for computation
    bnb_4bit_use_double_quant=True,   # ④ Quantize the quantization constants too
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
)

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = "<PAD>"
tokenizer.padding_side = "left"
```

`load_in_4bit=True` stores all model weights as 4-bit NF4 integers on the GPU. For a 1.1B parameter model this reduces the weight memory from ~4.4 GB (float32) to ~0.55 GB — an 8× reduction.

`bnb_4bit_quant_type="nf4"` selects NormalFloat-4 rather than plain 4-bit integer quantization. NF4's distribution-aware bins minimise error for the bell-curve-shaped weight distributions typical in LLMs.

`bnb_4bit_compute_dtype="float16"` means that even though weights are stored as 4-bit, matrix multiplications cannot be performed in 4-bit. Just before each computation, the relevant weights are dequantized to float16. The computation happens in float16, the result is passed forward, and the weights snap back to 4-bit storage.

`bnb_4bit_use_double_quant=True` applies **double quantization** — a second level of compression. The quantization constants themselves (the per-block scale factors) are stored as float32 by default. Double quantization re-quantizes those constants to 8-bit integers. This saves approximately 0.37 bits per parameter — small per weight, but adds up to hundreds of megabytes for large models.

---

### 3c. LoRA Configuration — Every Parameter Explained

With the quantized model loaded, the LoRA adapters are configured using the `peft` library:

```python
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model

peft_config = LoraConfig(
    lora_alpha=32,          # Scaling factor α
    lora_dropout=0.1,       # Dropout on adapter activations
    r=64,                   # Rank of the decomposition
    bias="none",            # Do not train bias terms
    task_type="CAUSAL_LM",  # Causal language modelling task
    target_modules=[        # Which weight matrices to add LoRA to
        "k_proj", "gate_proj", "v_proj", "up_proj",
        "q_proj", "o_proj", "down_proj"
    ]
)

model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)
```

| Parameter | What it controls | Guidance |
|-----------|-----------------|---------|
| `r` | Rank of A and B matrices | Higher → more capacity → more memory. Typical range: 4–64. Start at 16. |
| `lora_alpha` | Scale of the weight update ($\alpha/r$ multiplier) | Set to `2r` as a rule of thumb. |
| `lora_dropout` | Dropout probability on adapter activations | Regularisation; 0.05–0.1 typical. |
| `target_modules` | Which projections receive LoRA adapters | All attention + FFN projections for maximum quality. |
| `bias="none"` | Whether to train bias terms | Biases are tiny scalars — not worth training. |

The `target_modules` list maps directly to the weight matrices inside each transformer block. `q_proj`, `k_proj`, `v_proj` are the Query, Key, and Value projections in multi-head attention. `o_proj` is the output projection that combines attention heads. `gate_proj`, `up_proj`, and `down_proj` are the three weight matrices inside the feed-forward network (TinyLlama uses a gated FFN architecture).

---

### 3d. Training Arguments — What They Actually Do

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

`gradient_accumulation_steps=4` is a memory trick worth understanding deeply. Normally you update the weights after each batch of 2 examples. With accumulation steps of 4, you process 4 batches in sequence without updating weights, then apply one combined update using the sum of all 4 batches' gradients. This simulates a batch size of `2 × 4 = 8` while only holding 2 examples in GPU memory at once. Memory usage stays low; the effective learning signal per update step is richer.

`lr_scheduler_type="cosine"` uses a cosine annealing schedule. The learning rate starts at `2e-4`, ramps up briefly during a warm-up period, then gradually decreases following a cosine curve until it reaches near zero by the end of training. The slow decay at the end allows the model to settle into a good minimum without overshooting.

```
Cosine LR Schedule:

  2e-4 ─┐
         │╲
         │  ╲
         │    ╲
         │      ╲______
  ~0    ─┴──────────────►
         0            end of training
         (warm-up)
```

`gradient_checkpointing=True` is a memory-versus-compute trade-off. During the forward pass, all intermediate activations are normally stored so the backward pass can use them to compute gradients. For a long sequence, these stored activations consume enormous memory. Gradient checkpointing discards most of them during the forward pass and *recomputes* them on demand during the backward pass. Training takes roughly 30% longer but memory usage drops significantly — often enough to allow training that would otherwise run out of VRAM.

`fp16=True` enables **mixed-precision training**. The forward pass and gradient computation happen in float16, which is twice as fast on modern GPUs with hardware float16 support. The optimizer state (Adam's momentum and variance terms) is kept in float32 to prevent numerical instability during the weight update. The framework automatically handles conversions between precisions.

---

### 3e. SFTTrainer and the Training Loop

```python
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="text",
    tokenizer=tokenizer,
    args=training_arguments,
    max_seq_length=512,
    peft_config=peft_config,
)

trainer.train()

# Save only the LoRA adapter weights — not the full model
trainer.model.save_pretrained("TinyLlama-1.1B-qlora")
```

The `SFTTrainer` from the `trl` library wraps the standard HuggingFace `Trainer` with instruction-tuning defaults. Most importantly, it handles **data collation** — padding sequences of different lengths to the same length within a batch, and masking the user-turn tokens so the loss is computed only on the assistant's response tokens.

When training is complete, `save_pretrained` saves only the LoRA adapter weights, not the base model. The adapter checkpoint for a 1.1B model with rank-64 LoRA is typically 20–50 MB. This is one of LoRA's practical advantages: you can share many different fine-tuned versions of a model by distributing only tiny adapter files, all loading on top of the same shared base model.

---

### 3f. Merging LoRA Weights for Inference

For inference, you have two options. You can load the base model and the adapter separately and let PEFT handle the $Wx + ABx$ computation at every layer — with a small overhead per layer. Or you can **merge** the adapter into the base model, computing $W' = W + \frac{\alpha}{r}AB$ once and storing the result permanently.

```python
from peft import AutoPeftModelForCausalLM
from transformers import pipeline

# Load the quantized base model with the saved LoRA adapter attached
model = AutoPeftModelForCausalLM.from_pretrained(
    "TinyLlama-1.1B-qlora",
    low_cpu_mem_usage=True,
    device_map="auto",
)

# Fuse A·B into W for every targeted layer — no more separate adapter overhead
merged_model = model.merge_and_unload()

# Use the TinyLlama chat template for inference
prompt = """<|user|>
Tell me something about Large Language Models.</s>
<|assistant|>
"""

pipe = pipeline(task="text-generation", model=merged_model, tokenizer=tokenizer)
print(pipe(prompt, max_new_tokens=200)[0]["generated_text"])
```

`merge_and_unload()` computes $W' = W + \frac{\alpha}{r} \cdot AB$ for every targeted weight matrix and replaces the original $W$ with the merged $W'$. The adapter objects are then discarded. The resulting model is a standard transformer with no PEFT overhead — inference speed is identical to a model that was never fine-tuned with LoRA.

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
