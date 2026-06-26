# Chapter 4 Code Explanation — Implementing a GPT Model From Scratch

This document walks through every code cell of `ch04.ipynb` from Sebastian Raschka's _Build a Large Language Model From Scratch_. The notebook assembles a full 124M-parameter GPT-2-style model from the ground up: embeddings, layer normalisation, GELU feed-forward networks, residual connections, transformer blocks, and a greedy text-generation loop. Each section below corresponds to one cell (or a tight group of cells) of the notebook and explains the _what_, the _why_, and the _math_ behind it.

The section numbers match the linear flow of the notebook (0 → 25). Inside each section the corresponding book heading (Raschka's 4.1, 4.2, etc.) is referenced for cross-lookup with the notes.

---

## Table of Contents

- [0 — Notebook Setup and Imports](#0--notebook-setup-and-imports)
- [1 — Section 4.1: The GPT-2 Configuration Dictionary](#1--section-41-the-gpt-2-configuration-dictionary)
- [2 — Section 4.1: The DummyGPTModel Skeleton](#2--section-41-the-dummygptmodel-skeleton)
- [3 — Section 4.1: Tokenising a Batch of Two Sentences](#3--section-41-tokenising-a-batch-of-two-sentences)
- [4 — Section 4.1: Forward Pass Through DummyGPTModel](#4--section-41-forward-pass-through-dummygptmodel)
- [5 — Section 4.2: A Tiny Pre-LayerNorm Example](#5--section-42-a-tiny-pre-layernorm-example)
- [6 — Section 4.2: Computing Mean and Variance Per Token](#6--section-42-computing-mean-and-variance-per-token)
- [7 — Section 4.2: Manual Normalisation by Hand](#7--section-42-manual-normalisation-by-hand)
- [8 — Section 4.2: The LayerNorm Class](#8--section-42-the-layernorm-class)
- [9 — Section 4.3: The GELU Activation From Scratch](#9--section-43-the-gelu-activation-from-scratch)
- [10 — Section 4.3: GELU vs ReLU — Visual Comparison](#10--section-43-gelu-vs-relu--visual-comparison)
- [11 — Section 4.3: The FeedForward Class](#11--section-43-the-feedforward-class)
- [12 — Section 4.4: ExampleDeepNeuralNetwork and print_gradients](#12--section-44-exampledeepneuralnetwork-and-print_gradients)
- [13 — Section 4.4: Gradients Without Shortcuts — The Vanishing Problem](#13--section-44-gradients-without-shortcuts--the-vanishing-problem)
- [14 — Section 4.4: Gradients With Shortcuts — The Fix](#14--section-44-gradients-with-shortcuts--the-fix)
- [15 — Section 4.5: The TransformerBlock](#15--section-45-the-transformerblock)
- [16 — Section 4.5: Running the TransformerBlock](#16--section-45-running-the-transformerblock)
- [17 — Section 4.6: The Full GPTModel Class](#17--section-46-the-full-gptmodel-class)
- [18 — Section 4.6: Running the Real Model on the Batch](#18--section-46-running-the-real-model-on-the-batch)
- [19 — Section 4.6: Counting the Parameters](#19--section-46-counting-the-parameters)
- [20 — Section 4.6: Weight Tying and the 124M Number](#20--section-46-weight-tying-and-the-124m-number)
- [21 — Section 4.6: Model Size in Megabytes](#21--section-46-model-size-in-megabytes)
- [22 — Section 4.7: generate_text_simple — Greedy Decoding](#22--section-47-generate_text_simple--greedy-decoding)
- [23 — Section 4.7: Encoding the Prompt](#23--section-47-encoding-the-prompt)
- [24 — Section 4.7: Running Generation on an Untrained Model](#24--section-47-running-generation-on-an-untrained-model)
- [25 — Section 4.7: Decoding the Output Back to Text](#25--section-47-decoding-the-output-back-to-text)

---

## 0 — Notebook Setup and Imports

The very first executable cell of the notebook is purely a version check:

```python
from importlib.metadata import version
print("matplotlib version:", version("matplotlib"))
print("torch version:",      version("torch"))
print("tiktoken version:",   version("tiktoken"))
```

Three libraries do the heavy lifting throughout this chapter:

- **`torch`** — the actual neural network engine. Every layer (`nn.Linear`, `nn.Embedding`, `nn.LayerNorm` analogue, `nn.Dropout`) and tensor we touch lives in PyTorch.
- **`tiktoken`** — OpenAI's BPE tokenizer. It is used here in two places: tokenising the two demo sentences in section 3, and decoding the model's generated token IDs back to text at the very end of the notebook.
- **`matplotlib`** — only used once, to draw the GELU vs ReLU comparison plot.

Pinning the versions matters because PyTorch's API evolves: `unbiased=False` in `var`, the exact `torch.softmax` signature, and the device-handling on `torch.arange` have all shifted between minor releases. The book targets `torch >= 2.0`, `tiktoken >= 0.7`, and any modern matplotlib.

---

## 1 — Section 4.1: The GPT-2 Configuration Dictionary

```python
GPT_CONFIG_124M = {
    "vocab_size":     50257,    # BPE vocabulary size
    "context_length": 1024,     # max sequence length
    "emb_dim":        768,      # embedding / model dimension
    "n_heads":        12,       # attention heads per block
    "n_layers":       12,       # transformer blocks stacked
    "drop_rate":      0.1,      # dropout probability
    "qkv_bias":       False     # bias on Q, K, V projections
}
```

This dictionary is **the single source of truth** for every shape in the rest of the notebook. Every class (`DummyGPTModel`, `LayerNorm`, `FeedForward`, `TransformerBlock`, `GPTModel`) takes this `cfg` as its constructor argument and reads what it needs from it.

### Why a dictionary and not constructor arguments?

Hard-coding `768` into every class would force you to edit a dozen files if you ever wanted to try a bigger model (e.g. GPT-2 Medium with `emb_dim=1024`). The dictionary lets you swap one variable and rebuild the entire stack with new shapes.

### What each number actually controls

| Key              | Value | Used by                                                                                                        |
| ---------------- | ----- | -------------------------------------------------------------------------------------------------------------- |
| `vocab_size`     | 50257 | `nn.Embedding(vocab_size, emb_dim)` for token embeddings; `nn.Linear(emb_dim, vocab_size)` for the output head |
| `context_length` | 1024  | `nn.Embedding(context_length, emb_dim)` for positional embeddings; also the size of the causal attention mask  |
| `emb_dim`        | 768   | The "width" of every hidden state — embedding dim, MHA hidden dim, FFN input/output dim                        |
| `n_heads`        | 12    | Splits `emb_dim` into 12 attention heads, each of width `768 / 12 = 64`                                        |
| `n_layers`       | 12    | How many `TransformerBlock`s stacked sequentially                                                              |
| `drop_rate`      | 0.1   | Dropout on embeddings, attention weights, and after each sublayer                                              |
| `qkv_bias`       | False | GPT-2 omitted bias in the Q/K/V linear projections to match the original transformer                           |

### Where the "124M" comes from

Multiply out the parameter counts and you get **163M** total, not 124M. The 124M figure refers to the count **after weight tying** (sharing the token-embedding matrix with the output head). We'll see this exact arithmetic in section 20.

---

## 2 — Section 4.1: The DummyGPTModel Skeleton

**Summary.** This section assembles the outer skeleton of a GPT model and does a shape-correctness check before any of the real internals exist. The skeleton has token embeddings, positional embeddings, a stack of transformer blocks, a final layer norm, and an output projection head. Because `TransformerBlock` and `LayerNorm` have not been built yet, placeholder classes (`DummyTransformerBlock`, `DummyLayerNorm`) stand in for them. Every placeholder just returns its input unchanged, so the only thing being tested is that the surrounding wiring produces the right tensor shapes.

**The problem it solves.** When building a large system bottom-up, you naturally want to test each piece in isolation. But you also want to confirm that the whole pipeline fits together before any piece is real. The scaffolding pattern achieves this: write the outer shell with stubs in the slots you haven't filled yet, run a forward pass, and verify the output shape is correct. Once the shape is confirmed, you can replace the stubs one by one with real implementations.

**The intuition.** Think of the model as a factory assembly line. The raw material is a batch of token ID integers. By the end of the line, each token should have been converted into a vector of size `vocab_size` — one score ("logit") per word in the vocabulary — so the model can eventually say "the next token is most likely token 9374". The assembly line has four stations:

```
Token IDs (integers)
       │
       ▼  Station 1 — Embedding lookup
       │  Convert each integer to a dense vector. Add positional information.
       │  Shape becomes: (batch, seq_len, emb_dim)
       │
       ▼  Station 2 — Transformer blocks × 12
       │  Repeatedly refine the vectors so each token gathers context
       │  from its neighbours. Shape stays: (batch, seq_len, emb_dim)
       │
       ▼  Station 3 — Final layer norm
       │  Stabilise the activations before the output projection.
       │  Shape stays: (batch, seq_len, emb_dim)
       │
       ▼  Station 4 — Output head (linear projection)
          Project each emb_dim vector up to vocab_size scores.
          Shape becomes: (batch, seq_len, vocab_size)
```

The dummy model lets us confirm this shape story end-to-end before spending time building any real station.

**The two embedding tables.** Every token carries two independent pieces of information that the model needs to combine: what the token _is_ (its meaning) and _where_ it sits in the sequence (its position). GPT handles this with two separate learned lookup tables.

```
tok_emb  shape: (vocab_size=50257, emb_dim=768)
                 ↑                  ↑
               row index =        each row is a 768-dim
               token ID           meaning vector

pos_emb  shape: (context_length=1024, emb_dim=768)
                 ↑                     ↑
               row index =            each row is a 768-dim
               position 0..1023       position vector
```

For a given token at position `p` with ID `t`, the model looks up row `t` of `tok_emb` and row `p` of `pos_emb`, then **adds** them together element-wise to produce one combined vector. This addition is what `x = tok_embeds + pos_embeds` does.

**The code.**

```python
class DummyGPTModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        # Station 1a — token meaning lookup table
        # Shape: (vocab_size, emb_dim) = (50257, 768)
        self.tok_emb  = nn.Embedding(cfg["vocab_size"],     cfg["emb_dim"])

        # Station 1b — position lookup table
        # Shape: (context_length, emb_dim) = (1024, 768)
        self.pos_emb  = nn.Embedding(cfg["context_length"], cfg["emb_dim"])

        # Dropout applied once after the combined embedding
        self.drop_emb = nn.Dropout(cfg["drop_rate"])

        # Station 2 — stack of 12 transformer blocks (stubs for now)
        self.trf_blocks = nn.Sequential(
            *[DummyTransformerBlock(cfg) for _ in range(cfg["n_layers"])])

        # Station 3 — final layer norm (stub for now)
        self.final_norm = DummyLayerNorm(cfg["emb_dim"])

        # Station 4 — linear projection from emb_dim → vocab_size
        # bias=False follows the GPT-2 convention
        self.out_head   = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, in_idx):
        batch_size, seq_len = in_idx.shape         # e.g. (2, 4)

        # Look up meaning vectors for every token in the batch
        tok_embeds = self.tok_emb(in_idx)           # (batch, seq_len, emb_dim)

        # Build position indices [0, 1, ..., seq_len-1] fresh each call,
        # on the same device as the input
        pos_embeds = self.pos_emb(                  # (seq_len, emb_dim)
            torch.arange(seq_len, device=in_idx.device)
        )                                           # broadcasts to (batch, seq_len, emb_dim)

        x = tok_embeds + pos_embeds                 # (batch, seq_len, emb_dim) — fused vector
        x = self.drop_emb(x)                        # (batch, seq_len, emb_dim) — same shape
        x = self.trf_blocks(x)                      # (batch, seq_len, emb_dim) — stubs, pass-through
        x = self.final_norm(x)                      # (batch, seq_len, emb_dim) — stub, pass-through
        logits = self.out_head(x)                   # (batch, seq_len, vocab_size)
        return logits


class DummyTransformerBlock(nn.Module):
    def forward(self, x):
        return x    # ← stub: does nothing, preserves shape

class DummyLayerNorm(nn.Module):
    def __init__(self, normalized_shape, eps=1e-5): super().__init__()
    def forward(self, x):
        return x    # ← stub: does nothing, preserves shape
```

**Shape transformation story — worked example.**

We use a tiny config to keep the numbers traceable: `batch=2`, `seq_len=4`, `vocab_size=8`, `emb_dim=3`. The actual GPT-2 config uses `(50257, 1024, 768)` but the mechanics are identical — we just use small numbers so you can see every element.

The two input sentences (batch items) are:

```
Sentence 0: "Hi I love you"   → token IDs [3, 1, 5, 7]
Sentence 1: "Hey how are you" → token IDs [2, 4, 6, 7]
```

**Step 0 — The input tensor `in_idx`.**

```
in_idx.shape = (2, 4)    ← (batch, seq_len)
                ↑  ↑
              batch seq_len

in_idx = [
            [3, 1, 5, 7],    ← Batch 0: token IDs for "Hi I love you"
            [2, 4, 6, 7]     ← Batch 1: token IDs for "Hey how are you"
          ]
```

These are just integers. Nothing has a meaning yet — they are raw indices into the vocabulary table.

**Step 1a — Token embedding lookup: `tok_embeds = self.tok_emb(in_idx)`.**

`nn.Embedding(8, 3)` is a table with 8 rows (one per vocab item) and 3 columns (the embedding vector). Looking up `in_idx` replaces each integer with its corresponding row. We use letters to track exactly which row goes where.

```
tok_emb table (shape 8×3 — one row per vocabulary token):

  row 0 → [p, q, r]   ← "the"
  row 1 → [s, t, u]   ← "I"
  row 2 → [v, w, x]   ← "Hey"
  row 3 → [y, z, A]   ← "Hi"
  row 4 → [B, C, D]   ← "how"
  row 5 → [E, F, G]   ← "love"
  row 6 → [H, I, J]   ← "are"
  row 7 → [K, L, M]   ← "you"
```

For `in_idx[0] = [3, 1, 5, 7]` we look up rows 3, 1, 5, 7.  
For `in_idx[1] = [2, 4, 6, 7]` we look up rows 2, 4, 6, 7.

```
tok_embeds.shape = (2, 4, 3)    ← (batch, seq_len, emb_dim)
                    ↑  ↑  ↑
                  batch seq  emb_dim

tok_embeds = [
               [                         ← Batch 0 — "Hi I love you"
                 [y, z, A],    ← Position 0 — "Hi"   (row 3 of tok_emb)
                 [s, t, u],    ← Position 1 — "I"    (row 1 of tok_emb)
                 [E, F, G],    ← Position 2 — "love" (row 5 of tok_emb)
                 [K, L, M]     ← Position 3 — "you"  (row 7 of tok_emb)
               ],                        ← end Batch 0
               [                         ← Batch 1 — "Hey how are you"
                 [v, w, x],    ← Position 0 — "Hey" (row 2 of tok_emb)
                 [B, C, D],    ← Position 1 — "how" (row 4 of tok_emb)
                 [H, I, J],    ← Position 2 — "are" (row 6 of tok_emb)
                 [K, L, M]     ← Position 3 — "you" (row 7 of tok_emb)
               ]                         ← end Batch 1
             ]
```

Notice "you" appears in both sentences at position 3, so both batches end with `[K, L, M]`. That is correct — the same word maps to the same embedding row regardless of which sentence it appears in. Position has not been added yet.

**Step 1b — Positional embedding lookup: `pos_embeds = self.pos_emb(torch.arange(4))`.**

`torch.arange(4)` produces `[0, 1, 2, 3]` — not the token IDs, but the slot numbers. The positional embedding table `(1024, 3)` maps each slot to a 3-dim vector encoding "I am at position N".

```
pos_emb table (first 4 rows shown):

  row 0 → [α, β, γ]    ← "I am at position 0"
  row 1 → [δ, ε, ζ]    ← "I am at position 1"
  row 2 → [η, θ, ι]    ← "I am at position 2"
  row 3 → [κ, λ, μ]    ← "I am at position 3"
```

This lookup produces a `(4, 3)` tensor — one row per position, no batch dimension yet:

```
pos_embeds.shape = (4, 3)    ← (seq_len, emb_dim) — no batch axis yet
                    ↑  ↑
                  seq  emb_dim

pos_embeds = [
               [α, β, γ],    ← Position 0
               [δ, ε, ζ],    ← Position 1
               [η, θ, ι],    ← Position 2
               [κ, λ, μ]     ← Position 3
             ]
```

When PyTorch adds this to `tok_embeds` of shape `(2, 4, 3)`, it broadcasts the `(4, 3)` across the batch dimension automatically — position 0 gets `[α, β, γ]` added regardless of which sentence it belongs to. Both sentences share the exact same positional vectors.

**Step 1c — Fused embedding: `x = tok_embeds + pos_embeds`.**

Element-wise addition at every position, for every batch item. The token meaning vector and the position vector are simply summed into one combined vector.

```
x.shape = (2, 4, 3)    ← (batch, seq_len, emb_dim) — unchanged from tok_embeds
           ↑  ↑  ↑
         batch seq  emb_dim

x = [
      [                              ← Batch 0 — "Hi I love you"
        [y+α, z+β, A+γ],    ← Position 0 "Hi"   — meaning + position 0 fused
        [s+δ, t+ε, u+ζ],    ← Position 1 "I"    — meaning + position 1 fused
        [E+η, F+θ, G+ι],    ← Position 2 "love" — meaning + position 2 fused
        [K+κ, L+λ, M+μ]     ← Position 3 "you"  — meaning + position 3 fused
      ],                             ← end Batch 0
      [                              ← Batch 1 — "Hey how are you"
        [v+α, w+β, x+γ],    ← Position 0 "Hey" — meaning + position 0 fused
        [B+δ, C+ε, D+ζ],    ← Position 1 "how" — meaning + position 1 fused
        [H+η, I+θ, J+ι],    ← Position 2 "are" — meaning + position 2 fused
        [K+κ, L+λ, M+μ]     ← Position 3 "you" — meaning + position 3 fused
      ]                              ← end Batch 1
    ]
```

The key observation: "you" at position 3 now has a **different vector in the two batches** even though it was the same token. In Batch 0 it is `[K+κ, L+λ, M+μ]`; in Batch 1 it is also `[K+κ, L+λ, M+μ]`. They are identical here because "you" is at position 3 in both sentences. But if "you" appeared at position 1 in one sentence and position 3 in another, the positional component would differ and the fused vectors would be different — this is precisely the point of positional embeddings.

**Step 2 — Dropout: `x = self.drop_emb(x)`.**

Dropout randomly zeroes a fraction of elements during training (10% here, set by `drop_rate=0.1`). The shape does not change: still `(2, 4, 3)`. During inference (`.eval()` mode) dropout is disabled and `x` passes through unchanged.

**Step 3 — Transformer blocks: `x = self.trf_blocks(x)`.**

`nn.Sequential` calls all 12 `DummyTransformerBlock` instances in order. Each stub returns its input unchanged. Shape stays `(2, 4, 3)`. In the real model each block would run multi-head attention + feed-forward and refine every token vector — but the shape contract is the same: every block takes `(batch, seq_len, emb_dim)` in and returns `(batch, seq_len, emb_dim)` out. This is what makes stacking 12 (or 96) blocks possible.

**Step 4 — Final layer norm: `x = self.final_norm(x)`.**

The stub returns `x` unchanged. Shape stays `(2, 4, 3)`. The real `LayerNorm` would normalise each token vector to mean 0, std 1, then scale/shift via learnable parameters.

**Step 5 — Output head: `logits = self.out_head(x)`.**

`nn.Linear(emb_dim=3, vocab_size=8, bias=False)` is a weight matrix of shape `(8, 3)`. It projects each 3-dim token vector up into an 8-dim score vector — one score per vocabulary item.

```
Before: x.shape = (2, 4, 3)    ← (batch, seq_len, emb_dim)

After:  logits.shape = (2, 4, 8)    ← (batch, seq_len, vocab_size)
                        ↑  ↑  ↑
                      batch seq  vocab_size
```

Each position now holds 8 raw scores. For position 3 in Batch 0 ("you"), the 8 scores say how likely each vocabulary word is to follow "Hi I love you" in the full sequence. These are not probabilities yet — a `softmax` applied to the last dimension would convert them.

```
logits = [
           [                                      ← Batch 0 — "Hi I love you"
             [s0, s1, s2, s3, s4, s5, s6, s7],   ← Position 0 "Hi"   — 8 scores
             [s0, s1, s2, s3, s4, s5, s6, s7],   ← Position 1 "I"    — 8 scores
             [s0, s1, s2, s3, s4, s5, s6, s7],   ← Position 2 "love" — 8 scores
             [s0, s1, s2, s3, s4, s5, s6, s7]    ← Position 3 "you"  — 8 scores
           ],                                     ← end Batch 0
           [                                      ← Batch 1 — "Hey how are you"
             [s0, s1, s2, s3, s4, s5, s6, s7],   ← Position 0 "Hey" — 8 scores
             [s0, s1, s2, s3, s4, s5, s6, s7],   ← Position 1 "how" — 8 scores
             [s0, s1, s2, s3, s4, s5, s6, s7],   ← Position 2 "are" — 8 scores
             [s0, s1, s2, s3, s4, s5, s6, s7]    ← Position 3 "you" — 8 scores
           ]                                      ← end Batch 1
         ]
```

**Running it: expected output shape.**

```python
import torch
import torch.nn as nn

GPT_CONFIG_124M = {
    "vocab_size":     50257,
    "context_length": 1024,
    "emb_dim":        768,
    "n_heads":        12,
    "n_layers":       12,
    "drop_rate":      0.1,
    "qkv_bias":       False
}

tokenizer = tiktoken.get_encoding("gpt2")
batch = []
batch.append(torch.tensor(tokenizer.encode("Every effort moves you")))
batch.append(torch.tensor(tokenizer.encode("Every day holds a")))
batch = torch.stack(batch, dim=0)

torch.manual_seed(123)
model = DummyGPTModel(GPT_CONFIG_124M)
logits = model(batch)

print(logits.shape)
# torch.Size([2, 4, 50257])

print(logits)
# tensor([[[-1.2034,  0.3201, -0.7130,  ..., -1.5548, -0.2390, -0.4667],
#          [-0.1192,  0.4539, -0.4432,  ...,  0.2392,  1.3469,  1.2430],
#          [ 0.5307,  1.6720, -0.4695,  ...,  1.1966,  0.0683,  0.2647],
#          [ 1.2216, -0.7556,  1.2258,  ...,  1.0974,  1.5571,  0.1764]],
#
#         [[-0.9409, -0.6405,  0.2496,  ..., -0.8258, -0.4745, -0.2527],
#          [-0.9407,  0.5612, -0.7655,  ...,  0.8153, -0.1767, -0.9896],
#          [-0.5741, -1.1977,  0.9439,  ..., -0.7597,  0.6039, -0.0776],
#          [ 0.5977, -0.2682, -0.0908,  ..., -1.1480,  0.3750, -0.2171]]],
#        grad_fn=<UnsafeViewBackward0>)
```

The shape `(2, 4, 50257)` confirms the wiring is correct. Two sentences, four tokens each, 50257 scores per token.

**Gotchas.**

`torch.arange(seq_len, device=in_idx.device)` is computed fresh on every forward call, not stored as a fixed buffer. This has two consequences. First, it naturally handles variable-length inputs — a batch with 4 tokens uses positions `[0, 1, 2, 3]`, one with 512 tokens uses `[0, 1, ..., 511]`, and there is no mismatch. Second, the `device=` argument is critical: if you move the model to a GPU but forget this argument, the position indices would be generated on CPU while `in_idx` lives on GPU, and PyTorch would immediately throw a device-mismatch error.

The `bias=False` on `out_head` is a GPT-2 design decision. A per-vocabulary bias term would let the model say "always prefer token X regardless of context", but the layer norm before this projection already handles the centering, and in practice removing the bias made no measurable difference while saving 50,257 parameters.

---

### How the Running Code Works

This subsection traces the three things that happen when you run the model for the first time: building the batch of token IDs, constructing the model object, and triggering the forward pass through `model(batch)`.

**Building the batch.**

`tiktoken.get_encoding("gpt2")` returns the GPT-2 tokenizer. Calling `.encode()` on a string splits it into tokens and returns their integer IDs from the BPE vocabulary:

```python
tokenizer.encode("Every effort moves you")   # → [6109, 3226, 4769, 345]
tokenizer.encode("Every day holds a")        # → [6109, 1110, 6622, 257]
```

`torch.tensor(...)` wraps each list into a 1D tensor of shape `(4,)`. `torch.stack([s0, s1], dim=0)` then stacks two `(4,)` tensors along a new leading dimension, producing a single `(2, 4)` integer matrix:

```
batch.shape = (2, 4)    ← (batch_size, seq_len)
               ↑  ↑
             batch seq_len

batch = [
           [6109, 3226, 4769,  345],    ← Batch 0: "Every effort moves you"
           [6109, 1110, 6622,  257]     ← Batch 1: "Every day holds a"
         ]
```

No embeddings yet — just raw integers. The model has not seen these numbers at all.

**Constructing the model.**

`model = DummyGPTModel(GPT_CONFIG_124M)` calls `__init__`. This does **not** process any data. It only allocates weight tables and registers the submodules. Concretely, after `__init__` finishes, six things are sitting on `self`:

```
self.tok_emb    → nn.Embedding weight table,  shape (50257, 768)  — one row per vocab word
self.pos_emb    → nn.Embedding weight table,  shape (1024,  768)  — one row per position slot
self.drop_emb   → nn.Dropout(0.1)             — no weights, just remembers the rate
self.trf_blocks → nn.Sequential of 12 stubs   — no weights, each returns input unchanged
self.final_norm → DummyLayerNorm              — no weights, returns input unchanged
self.out_head   → nn.Linear weight matrix,    shape (50257, 768)  — projects emb_dim → vocab_size
```

The model is like a factory that has been built and equipped. The assembly line is ready but has not started — no token has been processed yet.

**How `model(batch)` calls `forward` without you calling `.forward()` directly.**

This is a core PyTorch design decision. `nn.Module` overrides Python's `__call__` method. When you write `model(batch)`, Python calls `model.__call__(batch)`, not `model.forward(batch)`. PyTorch's `__call__` wraps your `forward` inside a layer of infrastructure:

```
model(batch)
       ↓
model.__call__(batch)           ← Python triggers __call__, not forward
       ↓
  [PyTorch: run pre-hooks]
       ↓
  your forward(in_idx)          ← PyTorch calls your forward internally
       ↓
  [PyTorch: attach grad_fn, run post-hooks, handle train/eval mode]
       ↓
returns logits
```

The hooks are how PyTorch tracks gradients, how dropout knows whether to activate (`.train()` vs `.eval()` mode), and how device checks happen. If you called `model.forward(batch)` directly, all of that infrastructure would be bypassed — dropout would not respect the mode switch and no gradient graph would be attached. The `grad_fn=<UnsafeViewBackward0>` visible in your output is direct evidence that `__call__` ran: PyTorch attached a gradient computation graph to the returned tensor, which only happens through `__call__`.

The rule is therefore: always call `model(batch)`, never `model.forward(batch)`.

**The full forward pass, step by step.**

```
in_idx = batch                                 shape: (2, 4)

tok_embeds = self.tok_emb(in_idx)
    # Each integer in batch is used as a row index into the (50257, 768) table.
    # batch[0][0] = 6109 → fetch row 6109 → a 768-dim meaning vector
    # batch[0][1] = 3226 → fetch row 3226 → a 768-dim meaning vector
    # 8 lookups total: 2 sentences × 4 tokens each
    shape: (2, 4, 768)

pos_embeds = self.pos_emb(torch.arange(4, device=in_idx.device))
    # torch.arange(4) = [0, 1, 2, 3]  — position slot indices, not token IDs
    # Fetch rows 0, 1, 2, 3 of the (1024, 768) position table
    shape: (4, 768)    ← no batch axis yet

x = tok_embeds + pos_embeds
    # (2, 4, 768) + (4, 768)
    # PyTorch broadcasts (4, 768) across both batch items automatically
    shape: (2, 4, 768)

x = self.drop_emb(x)      shape: (2, 4, 768)  — some values zeroed during training
x = self.trf_blocks(x)    shape: (2, 4, 768)  — 12 stubs, all return x unchanged
x = self.final_norm(x)    shape: (2, 4, 768)  — stub, returns x unchanged

logits = self.out_head(x)
    # nn.Linear(768, 50257) computes x @ W.T for every token in every batch item
    # each 768-dim vector becomes a 50257-dim score vector
    shape: (2, 4, 50257)
```

`logits[0][3]` is a vector of 50257 scores — one per vocabulary word — representing the model's guess at what token should follow "Every effort moves you". The model is untrained, so the scores are random. But the shape `(2, 4, 50257)` is correct, and that is the entire purpose of this scaffolding step.

## 3 — Section 4.1: Tokenising a Batch of Two Sentences

**Summary.** This section converts two raw text strings into the integer tensor that gets handed to `DummyGPTModel`. It is the same GPT-2 BPE tokenizer from Chapter 2, used here just to build a concrete input for the shape-verification run.

**The code.**

```python
import tiktoken
tokenizer = tiktoken.get_encoding("gpt2")

batch = []
txt1 = "Every effort moves you"
txt2 = "Every day holds a"

batch.append(torch.tensor(tokenizer.encode(txt1)))
batch.append(torch.tensor(tokenizer.encode(txt2)))
batch = torch.stack(batch, dim=0)
print(batch)
# tensor([[6109, 3626, 6100,  345],
#         [6109, 1110, 6622,  257]])
```

**What `.encode()` does — tracing the two strings.**

`tokenizer.encode(txt1)` runs the GPT-2 BPE vocabulary (50,257 entries) over the string and returns a list of integers. Each integer is the index of a subword unit in that vocabulary. For these two four-word sentences, each word happens to map to exactly one token:

```
"Every effort moves you"
      ↓         ↓       ↓     ↓
    6109       3626    6100   345

"Every day holds a"
      ↓      ↓      ↓     ↓
    6109    1110   6622   257
```

`torch.tensor([6109, 3626, 6100, 345])` wraps that Python list into a 1D PyTorch tensor of shape `(4,)`. The same happens for the second sentence:

```
s0 = tensor([6109, 3626, 6100, 345])    shape: (4,)    ← "Every effort moves you"
s1 = tensor([6109, 1110, 6622, 257])    shape: (4,)    ← "Every day holds a"
```

**Why `torch.stack(..., dim=0)` and not `torch.tensor([list, list])`.**

`torch.tensor([[6109, 3626, ...], [6109, 1110, ...]])` would also work here because both inner lists happen to be the same length. But `torch.stack` is the correct general tool: it takes a list of already-formed tensors and stacks them along a new dimension. `dim=0` inserts the new batch axis at the front, turning two `(4,)` tensors into one `(2, 4)` tensor:

```
batch.shape = (2, 4)    ← (batch_size, seq_len)
               ↑  ↑
             batch seq_len

batch = [
           [6109, 3626, 6100, 345],    ← Batch 0: "Every effort moves you"
           [6109, 1110, 6622, 257]     ← Batch 1: "Every day holds a"
         ]
```

In real training, sentences in a batch will rarely be the same length. The standard practice is to pad shorter sentences with a special padding token ID so every row has the same width, making `torch.stack` work. Here both sentences are four tokens, so no padding is needed.

**Reading the token IDs.**

`6109` appears in both rows at position 0 — that is the BPE token for `"Every"`. BPE uses a leading-space convention internally: the token for `"Every"` at the start of a string encodes the space that would precede it in running text, so it gets its own unique ID rather than sharing one with `"every"` mid-sentence.

`345` ends Batch 0 — that is `"you"`. `257` ends Batch 1 — that is `"a"`. These are the integers that will be used as row indices into the token embedding table in the next step: `tok_emb[345]` fetches the 768-dim meaning vector for `"you"`, `tok_emb[257]` fetches the one for `"a"`, and so on for all eight positions.

## 4 — Section 4.1: Forward Pass Through DummyGPTModel

**Summary.** This section runs a single forward pass through the assembled `DummyGPTModel` and checks that the output shape is correct. The model weights are randomly initialised, so the logit values are meaningless — but the shape `(2, 4, 50257)` confirms the entire pipeline is wired correctly.

**The code.**

```python
torch.manual_seed(123)
model = DummyGPTModel(GPT_CONFIG_124M)

logits = model(batch)
print("Output shape:", logits.shape)
print(logits)
# Output shape: torch.Size([2, 4, 50257])
# tensor([[[-0.9289,  0.2748, -0.7557,  ...,  -1.5548, -0.2390, -0.4667],
#          [-0.1192,  0.4539, -0.4432,  ...,   0.2392,  1.3469,  1.2430],
#          [ 0.5307,  1.6720, -0.4695,  ...,   1.1966,  0.0111,  0.5835],
#          [ 0.0139,  1.6755, -0.3388,  ...,   1.1586, -0.0435, -1.0400]],
#         [[-1.0908,  0.1798, -0.9484,  ...,  -1.6047,  0.2439, -0.4530],
#          [-0.7860,  0.5581, -0.0610,  ...,   0.4835, -0.0077,  1.6621],
#          [ 0.3567,  1.2698, -0.6398,  ...,  -0.0162, -0.1296,  0.3717],
#          [-0.2407, -0.7349, -0.5102,  ...,   2.0057, -0.3694,  0.1814]]],
#        grad_fn=<UnsafeViewBackward0>)
```

**Why `torch.manual_seed(123)` matters.**

`nn.Embedding` and `nn.Linear` initialise their weights randomly when constructed. Without a seed, every run produces different values. Setting the seed to `123` pins the random number generator so that on a fresh interpreter you get the exact same output values printed in the book. This matters for debugging: if your output diverges from the book's, you know something in your code is different, not the random initialisation.

**Reading the output shape.**

```
logits.shape = (2, 4, 50257)
               ↑  ↑  ↑
               │  │  └─ 50,257 logits — one score per vocabulary entry
               │  └──── 4 tokens in the sequence
               └─────── 2 sentences in the batch
```

Each position in each sequence gets a full vector of 50,257 raw scores. Applying `softmax` across the last dimension at any position $t$ would give a probability distribution over the entire vocabulary — the model's answer to "given everything up to position $t$, how likely is each word to come next?"

**Why one output vector per input position, not one per sequence.**

This is a property of autoregressive transformers with causal masking. Each position attends only to itself and the tokens before it, so position $t$'s logits are a function of tokens $[0, t]$ only. Training exploits this: a single forward pass produces one next-token prediction per position, giving $T$ training signals per sequence in one pass rather than running the model $T$ times.

At inference time, when generating new text, only the last position's logits matter — that is what predicts the next token to append to the sequence. The model computes all positions anyway because the architecture does not distinguish between "last" and "earlier"; the generation loop simply reads `logits[:, -1, :]` and ignores the rest.

The logit values themselves are random noise here because no training has happened. The shape being correct is the only thing this cell is checking.

## 5 — Section 4.2: A Tiny Pre-LayerNorm Example

**Summary.** This cell steps outside the GPT model entirely and builds a small toy network — a linear layer followed by ReLU — to produce some raw activations. The sole purpose is to have a concrete tensor in hand whose mean and variance are arbitrary, so the next cells can demonstrate why layer normalisation is needed and how it works.

**The code.**

```python
torch.manual_seed(123)

# 2 training examples × 5 features each
batch_example = torch.randn(2, 5)

layer = nn.Sequential(nn.Linear(5, 6), nn.ReLU())
out = layer(batch_example)
print(out)
# tensor([[0.2260, 0.3470, 0.0000, 0.2216, 0.0000, 0.0000],
#         [0.2133, 0.2394, 0.0000, 0.5198, 0.3297, 0.0000]])
```

**What this cell is doing and why.**

The chapter is about to derive `LayerNorm` from scratch. To motivate it, we first needs a tensor whose activations are messy — arbitrary mean, arbitrary variance, some values zeroed out by ReLU. This toy network produces exactly that. The GPT model is not involved at all here; the point is purely to have raw numbers to normalise in the next few cells.

`torch.randn(2, 5)` draws two five-dimensional vectors from $\mathcal{N}(0, 1)$, giving a `(2, 5)` matrix where each row is one training example. `nn.Linear(5, 6)` projects each row from 5 features to 6 features via a learned weight matrix and bias. `nn.ReLU()` then zeros out every negative entry. The zeros in the output are exactly the entries that were negative before ReLU fired.

```
batch_example.shape = (2, 5)    ← (examples, features_in)
                       ↑  ↑
                examples  features_in

batch_example = [
                   [r0, r1, r2, r3, r4],    ← Example 0 — 5 random values
                   [r5, r6, r7, r8, r9]     ← Example 1 — 5 random values
                 ]

After nn.Linear(5, 6):
out_linear.shape = (2, 6)    ← (examples, features_out)

After nn.ReLU() — negatives become 0:
out.shape = (2, 6)    ← shape unchanged, some values zeroed

out = [
         [0.2260, 0.3470, 0.0000, 0.2216, 0.0000, 0.0000],    ← Example 0
         [0.2133, 0.2394, 0.0000, 0.5198, 0.3297, 0.0000]     ← Example 1
       ]
```

**The problem this exposes.**

Looking at Example 0's six values, the mean is not zero and the variance is not one — the values are clumped in a narrow positive range with three of the six entries dead at zero. Example 1 has a different mean and a different spread. Each forward pass through a different network would produce yet another arbitrary distribution. When you stack many such layers, these shifting means and variances accumulate, making gradients unstable during training. Layer normalisation fixes this by rescaling each row to mean 0 and variance 1 before passing it onward.

**Why statistics are taken over `dim=-1`.**

In this toy example each row is one training example and the 6 features sit along `dim=1` (the last dim). In the GPT model each `(batch, token)` pair is the equivalent of one training example, and the embedding features sit along `dim=2` (also the last dim). Taking statistics over `dim=-1` works identically in both cases — it always collapses the feature axis regardless of how many leading dimensions there are. The LayerNorm class built in the next section therefore uses `dim=-1` throughout and slots directly into the GPT pipeline without any changes.

## 6 — Section 4.2: Computing Mean and Variance Per Token

**Summary.** This cell computes a mean and a variance for each row of `out` — one scalar per training example, not one per feature. These two statistics are the ingredients LayerNorm uses to rescale each row to zero mean and unit variance in the next cell.

**The code.**

```python
mean = out.mean(dim=-1, keepdim=True)
var  = out.var (dim=-1, keepdim=True)

print("Mean:\n", mean)
print("Variance:\n", var)
# Mean:
#  tensor([[0.1324],
#          [0.2170]])
# Variance:
#  tensor([[0.0231],
#          [0.0398]])
```

**What `dim=-1` means and why it is the right choice.**

`dim=-1` tells PyTorch to collapse the last axis. For `out` of shape `(2, 6)`, the last axis is the feature axis, so each row gets reduced to a single scalar. The result has shape `(2, 1)` — one mean and one variance per training example.

The alternative, `dim=0`, would collapse along the batch axis instead, producing one mean per feature averaged across all examples. That is batch normalisation. Layer normalisation always reduces over features, keeping examples independent of each other. Using `dim=-1` rather than a hardcoded `dim=1` means the same line works whether the tensor is `(batch, features)` or `(batch, tokens, emb_dim)` — the feature axis is always last in both cases.

```
out.shape = (2, 6)    ← (examples, features)

Reducing along dim=-1 (features):

  Example 0: mean over [0.2260, 0.3470, 0.0000, 0.2216, 0.0000, 0.0000]
           = (0.2260 + 0.3470 + 0.0000 + 0.2216 + 0.0000 + 0.0000) / 6
           = 0.7946 / 6
           = 0.1324

  Example 1: mean over [0.2133, 0.2394, 0.0000, 0.5198, 0.3297, 0.0000]
           = (0.2133 + 0.2394 + 0.0000 + 0.5198 + 0.3297 + 0.0000) / 6
           = 1.3022 / 6
           = 0.2170

mean.shape = (2, 1)    ← (examples, 1) — one scalar per row

mean = [
          [0.1324],    ← Example 0's mean across its 6 features
          [0.2170]     ← Example 1's mean across its 6 features
        ]
```

Variance follows the same reduction — one scalar per row, measuring how spread out the six feature values are around that row's mean.

```
var.shape = (2, 1)    ← (examples, 1) — one scalar per row

var = [
         [0.0231],    ← Example 0's variance across its 6 features
         [0.0398]     ← Example 1's variance across its 6 features
       ]
```

**Why `keepdim=True`.**

Without `keepdim`, the reduced axis is dropped entirely:

```
out.mean(dim=-1, keepdim=True)   → shape (2, 1)
out.mean(dim=-1, keepdim=False)  → shape (2,)
```

A shape of `(2,)` is a 1D vector — it has no concept of rows and columns. Subtracting it from `out` of shape `(2, 6)` would require an explicit `.unsqueeze(-1)` call to restore the missing dimension before broadcasting could work. Keeping `keepdim=True` preserves the axis as size 1, so PyTorch's broadcasting rules expand it automatically:

```
out    shape: (2, 6)
mean   shape: (2, 1)    ← the 1 broadcasts across the 6 features

out - mean → (2, 6)    — each row has its own mean subtracted from all 6 of its values
```

Broadcasting expands `mean` by repeating each scalar six times across the feature axis, subtracting the right mean from the right row without any explicit reshaping code.

## 7 — Section 4.2: Manual Normalisation by Hand

**Summary.** This cell applies the z-score formula row-by-row to `out`, then recomputes the mean and variance to verify the result. After normalisation every row should have mean 0 and variance 1. The tiny residual `9.9341e-09` in the mean is floating-point rounding noise, not a bug.

**The code.**

```python
out_norm = (out - mean) / torch.sqrt(var)
print("Normalized layer outputs:\n", out_norm)

mean = out_norm.mean(dim=-1, keepdim=True)
var  = out_norm.var (dim=-1, keepdim=True)
print("Mean:\n", mean)
print("Variance:\n", var)
# Mean:
#  tensor([[ 9.9341e-09],
#          [ 0.0000e+00]])
# Variance:
#  tensor([[1.0000],
#          [1.0000]])
```

**The normalisation formula.**

$$\hat{x}_i = \frac{x_i - \mu}{\sqrt{\sigma^2}}$$

Subtracting the row mean centres the distribution around zero. Dividing by the standard deviation scales it so the spread becomes 1. This is the z-score transformation from elementary statistics, applied independently to each row. After this operation every row has mean 0 and variance 1 regardless of what its values looked like before.

**Dry-run on Example 0.**

Example 0's six feature values before normalisation:

```
out[0] = [0.2260, 0.3470, 0.0000, 0.2216, 0.0000, 0.0000]

mean[0] = 0.1324    (computed in Section 6)
var[0]  = 0.0231    (computed in Section 6)
std[0]  = sqrt(0.0231) ≈ 0.1520
```

Applying the formula to each of the six values — subtract the row mean, then divide by the row std:

```
feature 0:  (0.2260 - 0.1324) / 0.1520 =  0.0936 / 0.1520 ≈  0.616
feature 1:  (0.3470 - 0.1324) / 0.1520 =  0.2146 / 0.1520 ≈  1.412
feature 2:  (0.0000 - 0.1324) / 0.1520 = -0.1324 / 0.1520 ≈ -0.871
feature 3:  (0.2216 - 0.1324) / 0.1520 =  0.0892 / 0.1520 ≈  0.587
feature 4:  (0.0000 - 0.1324) / 0.1520 = -0.1324 / 0.1520 ≈ -0.871
feature 5:  (0.0000 - 0.1324) / 0.1520 = -0.1324 / 0.1520 ≈ -0.871

out_norm[0] ≈ [0.616, 1.412, -0.871, 0.587, -0.871, -0.871]
```

The values that were zero before ReLU are now negative — they have been pulled below the mean. The positive values have been stretched upward. The row is now centred at 0 with spread 1.

Verifying the mean of `out_norm[0]`:

```
(0.616 + 1.412 + (-0.871) + 0.587 + (-0.871) + (-0.871)) / 6
= 0.002 / 6
≈ 0.000    ← zero up to floating-point rounding noise
```

**Why the mean prints as `9.9341e-09` and not exactly `0.0000`.**

Mathematically, `(x - mean(x)).mean()` is identically zero. In float32 arithmetic, each subtraction and division introduces a tiny rounding error at the level of $10^{-7}$ or smaller. When those errors are summed and averaged across six values, the residual lands around $10^{-8}$ rather than exactly zero. This is normal and harmless — it is not a mistake in the normalisation. The next cell calls `torch.set_printoptions(sci_mode=False)` purely to make this residual display as `0.0000` instead of `9.9341e-09`, which is a cosmetic display change and has no effect on the underlying tensor values.

**The shape story — broadcasting does all the work.**

```
out.shape   = (2, 6)
mean.shape  = (2, 1)    ← keepdim=True from Section 6
var.shape   = (2, 1)    ← keepdim=True from Section 6

out - mean                            out / torch.sqrt(var)
  (2, 6) - (2, 1)                       (2, 6) / (2, 1)
  mean broadcasts across dim=-1         std broadcasts across dim=-1
  → (2, 6)                              → (2, 6)

out_norm.shape = (2, 6)    ← same shape as out, values rescaled
```

Each row gets its own mean subtracted and its own standard deviation divided — the two rows never interact with each other. This row-independence is the defining property of layer normalisation and is what makes it behave identically whether the batch has 1 example or 1000.

## 8 — Section 4.2: The LayerNorm Class

**Summary.** This section packages the manual normalisation from Section 7 into a reusable `nn.Module` with three additions: biased variance to match the original paper, an epsilon for numerical stability, and two learnable parameters `scale` and `shift` that let the model undo the normalisation if needed.

**The code.**

```python
class LayerNorm(nn.Module):
    def __init__(self, emb_dim):
        super().__init__()
        self.eps   = 1e-5
        self.scale = nn.Parameter(torch.ones (emb_dim))   # γ — initialised to 1
        self.shift = nn.Parameter(torch.zeros(emb_dim))   # β — initialised to 0

    def forward(self, x):
        mean  = x.mean(dim=-1, keepdim=True)
        var   = x.var (dim=-1, keepdim=True, unbiased=False)
        norm_x = (x - mean) / torch.sqrt(var + self.eps)
        return self.scale * norm_x + self.shift
```

**The full layer-norm formula.**

$$y_i = \gamma \cdot \frac{x_i - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta$$

This is the Section 7 formula with three additions. Each one is explained below.

**Addition 1 — `unbiased=False`: biased variance.**

PyTorch's `.var()` defaults to unbiased variance, dividing by $N - 1$ (Bessel's correction). The original LayerNorm paper (Ba et al. 2016) uses biased variance, dividing by $N$. For $N = 768$ features the numerical difference is negligible, but using the biased version is necessary for exact compatibility with pre-trained GPT-2 weights, which were trained with it. Setting `unbiased=False` switches to $\frac{1}{N}$.

Dry-run showing the difference for Example 0 from Section 6 with $N = 6$ features:

```
unbiased (default):  var = sum_of_squared_deviations / (6 - 1) = ... / 5
biased   (ours):     var = sum_of_squared_deviations / 6
```

The biased estimate is always slightly smaller. For $N = 768$ the ratio $\frac{N-1}{N} = \frac{767}{768} \approx 0.9987$, making the difference essentially invisible in practice.

**Addition 2 — `+ self.eps` inside the square root: numerical stability.**

If every feature of a token happens to be identical, the variance is exactly 0. Dividing by $\sqrt{0}$ produces infinity, which immediately propagates as `nan` through the rest of the network and kills training irreversibly. Adding $\epsilon = 10^{-5}$ guarantees the denominator is always at least $\sqrt{10^{-5}} \approx 0.003$, making a zero-variance catastrophe impossible at no measurable cost to accuracy.

```
Without eps:  norm_x = (x - mean) / sqrt(var)          ← explodes when var = 0
With eps:     norm_x = (x - mean) / sqrt(var + 1e-5)   ← denominator ≥ 0.003 always
```

**Addition 3 — trainable `scale` ($\gamma$) and `shift` ($\beta$).**

After dividing by $\sqrt{\text{var}}$, every row has been forced to mean 0 and variance 1. That is a very restrictive distribution. If the layer following LayerNorm would perform better with features centred at 5 or spread by a factor of 4, the network has no way to express that — unless LayerNorm hands control back.

`scale` and `shift` restore that control. They are both `nn.Parameter` tensors of shape `(emb_dim,)`, meaning PyTorch includes them in `model.parameters()` and the optimiser updates them during training:

```
scale  initialised to ones (emb_dim,)    → at init, multiplies norm_x by 1 everywhere
shift  initialised to zeros(emb_dim,)    → at init, adds 0 everywhere

At init:  output = 1 * norm_x + 0 = norm_x    ← pure normalisation
After training: scale and shift have been adjusted per feature
```

If pure normalisation is optimal, gradients drive `scale` toward 1 and `shift` toward 0 and they stay there. If the next sublayer prefers a different distribution, the optimiser shifts them away from their initial values. The model learns its own best per-feature rescaling.

**Shape story — tracing `x` through `forward`.**

Using the GPT context where `x` arrives from a transformer block:

```
x.shape = (2, 4, 768)    ← (batch, tokens, emb_dim)
           ↑  ↑  ↑
         batch tokens emb_dim

mean = x.mean(dim=-1, keepdim=True)
mean.shape = (2, 4, 1)    ← one scalar per (batch, token) pair

var = x.var(dim=-1, keepdim=True, unbiased=False)
var.shape = (2, 4, 1)     ← one scalar per (batch, token) pair

norm_x = (x - mean) / sqrt(var + eps)
  (2, 4, 768) - (2, 4, 1)  → broadcasts to (2, 4, 768)
  (2, 4, 768) / (2, 4, 1)  → broadcasts to (2, 4, 768)
norm_x.shape = (2, 4, 768)

self.scale * norm_x + self.shift
  scale.shape = (768,)        → broadcasts to (2, 4, 768)
  shift.shape = (768,)        → broadcasts to (2, 4, 768)

output.shape = (2, 4, 768)    ← same shape as input, values rescaled
```

Every `(batch, token)` pair is normalised independently. `scale` and `shift` are shared across all tokens and batch items — there is one set of learnable rescaling parameters per feature dimension, not one per token.

**Verifying it works.**

```python
ln = LayerNorm(emb_dim=6)
out_ln = ln(out)

mean = out_ln.mean(dim=-1, keepdim=True)
var  = out_ln.var (dim=-1, unbiased=False, keepdim=True)
print("Mean:\n", mean)
print("Variance:\n", var)
# Mean:
#  tensor([[    -0.0000],
#          [     0.0000]], grad_fn=<MeanBackward1>)
# Variance:
#  tensor([[0.9999],
#          [0.9999]], grad_fn=<VarBackward0>)
```

Mean is 0 (up to float32 rounding noise). Variance is 0.9999 rather than exactly 1.0 because the `+ eps` in the denominator makes the divisor slightly larger than the true standard deviation, producing output with variance fractionally below 1. The `grad_fn` tags on both tensors show the autograd graph is alive — `scale` and `shift` will receive gradients during backpropagation.

**Where LayerNorm sits in a GPT block.**

GPT-2 uses pre-LayerNorm: normalisation is applied before each sublayer rather than after. The arrangement inside one transformer block is:

```
x ──► LayerNorm ──► Multi-Head Attention ──► Dropout ──► + ──► LayerNorm ──► FeedForward ──► Dropout ──► +
└────────────────────────────────────────────────────────► │   └──────────────────────────────────────────► │
                                              (residual)                                        (residual)
```

The original 2017 transformer paper used post-LayerNorm (normalisation after the residual add). Pre-LayerNorm was found to train more stably for deep stacks because gradients flow directly through the residual connection without passing through a normalisation operation, making it the standard choice in every modern LLM.

## 9 — Section 4.3: The GELU Activation From Scratch

**Summary.** This section implements the GELU activation function used inside every feed-forward block in GPT-2. GELU is a smooth alternative to ReLU that gates activations gradually rather than hard-zeroing them, which empirically trains transformer models faster and to lower final loss.

**The code.**

```python
class GELU(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        return 0.5 * x * (1 + torch.tanh(
            torch.sqrt(torch.tensor(2.0 / torch.pi)) *
            (x + 0.044715 * torch.pow(x, 3))
        ))
```

**The problem GELU solves.**

ReLU zeros out every negative input with a hard threshold at exactly $x = 0$. That hard kink has two consequences. First, the derivative is undefined at zero and switches instantly from 0 to 1 — gradients either flow fully or not at all. Second, once a neuron's pre-activation falls below zero and stays there, its gradient is permanently zero and the neuron stops learning. This is the dying ReLU problem.

GELU fixes both issues by replacing the hard threshold with a smooth curve. For large negative inputs the output approaches zero gradually. For large positive inputs the output approaches the input itself. Around zero the transition is smooth, so the derivative never has a kink and gradients are never permanently killed.

**The exact formula and the tanh approximation.**

The mathematically exact GELU is:

$$\text{GELU}(x) = x \cdot \Phi(x)$$

where $\Phi(x)$ is the standard normal CDF — the probability that a standard normal random variable is less than $x$. Intuitively, the activation scales each input by the probability that it would be kept if noise were added to it. Inputs that are large and positive are almost certainly kept (probability near 1), so they pass through nearly unchanged. Inputs that are large and negative are almost certainly suppressed (probability near 0).

Computing $\Phi(x)$ exactly requires the error function `erf`, which is slow on GPUs. GPT-2 uses the tanh approximation fitted by Hendrycks and Gimpel (2016):

$$\text{GELU}(x) \approx 0.5 \cdot x \cdot \left(1 + \tanh\!\left[\sqrt{\frac{2}{\pi}} \cdot (x + 0.044715 \cdot x^3)\right]\right)$$

The constants $\sqrt{2/\pi} \approx 0.7979$ and $0.044715$ were fitted to match the exact CDF to high numerical precision using only multiply, add, and tanh — operations that are highly optimised on GPU hardware.

**Dry-run for $x = 1.0$.**

```
x     = 1.0
x^3   = 1.0

inner sum:  x + 0.044715 * x^3
          = 1.0 + 0.044715 * 1.0
          = 1.044715

sqrt(2/π):  sqrt(2 / 3.14159) ≈ 0.7979

scaled:     0.7979 * 1.044715 ≈ 0.8335

tanh:       tanh(0.8335) ≈ 0.6827

bracket:    1 + 0.6827 = 1.6827

output:     0.5 * 1.0 * 1.6827 = 0.8413

GELU(1.0) ≈ 0.8413
ReLU(1.0)  = 1.0
```

GELU returns 0.8413 where ReLU would return 1.0 — the positive value is slightly dampened. For large positive inputs like $x = 5.0$, GELU converges very close to $x$ itself because $\tanh$ saturates near 1 and the bracket approaches 2, giving $0.5 \cdot x \cdot 2 = x$.

**Dry-run for $x = -1.0$.**

```
x     = -1.0
x^3   = -1.0

inner sum:  -1.0 + 0.044715 * (-1.0)
          = -1.044715

scaled:     0.7979 * (-1.044715) ≈ -0.8335

tanh:       tanh(-0.8335) ≈ -0.6827

bracket:    1 + (-0.6827) = 0.3173

output:     0.5 * (-1.0) * 0.3173 = -0.1587

GELU(-1.0) ≈ -0.1587
ReLU(-1.0)  = 0.0000
```

ReLU hard-zeros the negative input. GELU returns $-0.1587$ — the neuron is suppressed but not dead. A small gradient still flows back through it, so it can recover during training if the weights shift to push this activation into the positive range.

**Comparing ReLU and GELU side by side.**

```
x        ReLU(x)    GELU(x)
──────────────────────────────
-3.0      0.000     -0.004    ← nearly zero but not exactly
-2.0      0.000     -0.045
-1.0      0.000     -0.159
-0.5      0.000     -0.154
 0.0      0.000      0.000    ← both are zero at the origin
 0.5      0.500      0.346
 1.0      1.000      0.841
 2.0      2.000      1.955    ← converging toward identity
 3.0      3.000      2.996
```

For large positive inputs the two functions converge. The difference is entirely in the transition zone around zero and in the negative region where GELU allows a small negative output rather than hard-zeroing.

**Why no parameters.**

`GELU` has no `nn.Parameter`. The two constants $0.7979$ and $0.044715$ are fixed mathematical values, not learned weights. The class is defined as an `nn.Module` purely so it can be passed into `nn.Sequential` as a slot in the feed-forward block built in the next section.

## 10 — Section 4.3: GELU vs ReLU — Visual Comparison

**Summary.** This cell plots both activation functions side by side to make the difference concrete. No new code concepts are introduced — it is purely a visual companion to the dry-run numbers from Section 9.

**The code.**

```python
import matplotlib.pyplot as plt

gelu, relu = GELU(), nn.ReLU()
x = torch.linspace(-3, 3, 100)
y_gelu, y_relu = gelu(x), relu(x)

plt.figure(figsize=(8, 3))
for i, (y, label) in enumerate(zip([y_gelu, y_relu], ["GELU", "ReLU"]), 1):
    plt.subplot(1, 2, i)
    plt.plot(x, y)
    plt.title(f"{label} activation function")
    plt.xlabel("x")
    plt.ylabel(f"{label}(x)")
    plt.grid(True)

plt.tight_layout()
plt.show()
```

**Reading the two plots.**

`torch.linspace(-3, 3, 100)` produces 100 evenly-spaced x-values from $-3$ to $3$. Both `gelu(x)` and `relu(x)` accept this 1D tensor and apply their `forward` method element-wise, returning a 1D tensor of the same shape. The loop uses `enumerate(zip(...), 1)` to place each curve in its own subplot starting at index 1.

The ReLU plot is two straight line segments meeting at a hard corner at the origin. Every negative input maps to exactly zero. Every positive input maps to itself. The kink at zero is the defining visual feature.

The GELU plot has no kink. Moving from left to right: for large negative $x$ the curve runs close to zero but with a gentle slope rather than snapping flat. Around $x \approx -0.17$ it dips to its minimum, which is a small negative value. It then rises, crosses zero at the origin, and curves upward to track closely alongside the ReLU line for large positive $x$.

The key values from the Section 9 dry-runs sit on these curves:

```
x = -1.0:  ReLU → 0.000,   GELU → -0.159    ← GELU is below zero here
x =  0.0:  ReLU → 0.000,   GELU →  0.000    ← both zero at origin
x =  1.0:  ReLU → 1.000,   GELU →  0.841    ← GELU slightly below ReLU
x =  3.0:  ReLU → 3.000,   GELU →  2.996    ← nearly identical for large positive x
```

**Why the dip below zero matters.**

With ReLU, once a feature value is negative it contributes exactly zero to everything downstream. A feature that was $-0.001$ and a feature that was $-100$ are indistinguishable — both become zero and the downstream layer loses that information entirely. In a 768-dimensional hidden state, roughly half the features are negative on any given token, so ReLU discards information from half the feature dimensions on every forward pass.

GELU preserves a small signed signal in the negative region. A feature at $-0.001$ produces an output of roughly $-0.0005$, while a feature at $-2.0$ produces roughly $-0.045$. The downstream layer can still distinguish between them — a gradient can flow back through both. This is the soft gating property: the activation is still suppressed for negative inputs, but not erased.

**Why this matters specifically for the GPT feed-forward block.**

The feed-forward block inside each transformer block applies a large up-projection first — from `emb_dim=768` to `4 * emb_dim=3072` — then passes every one of those 3072 features through the activation. With ReLU, 1536 of those 3072 features would be zeroed out on average. With GELU, all 3072 features carry some signal, giving the subsequent down-projection a richer input to compress back to 768 dimensions. The performance improvement in pre-training perplexity is modest but appears consistently across model sizes, which is why every major LLM after GPT-2 kept GELU or a close variant.

## 11 — Section 4.3: The FeedForward Class

**Summary.** This section builds the feed-forward sublayer that sits inside every transformer block. It is a two-layer MLP that expands the hidden dimension by a factor of 4, applies GELU in the wider space, then contracts back to the original dimension. Input and output shapes are identical, which is required for the residual connection that wraps it.

**The code.**

```python
class FeedForward(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(cfg["emb_dim"], 4 * cfg["emb_dim"]),   # expand: 768 → 3072
            GELU(),                                            # activate in wide space
            nn.Linear(4 * cfg["emb_dim"], cfg["emb_dim"]),   # contract: 3072 → 768
        )

    def forward(self, x):
        return self.layers(x)
```

**The expand-and-contract pattern.**

Every transformer FFN follows the same shape journey. Using `emb_dim=768` from `GPT_CONFIG_124M`:

```
Input          First Linear       GELU          Second Linear      Output
(batch, T, 768) → (batch, T, 3072) → (batch, T, 3072) → (batch, T, 768)
       ↑                 ↑                  ↑                  ↑
  emb_dim          4 × emb_dim        same shape           emb_dim
```

The first linear layer projects each token's 768-dim vector up into a 3072-dim space, giving the non-linearity more room to work. GELU is applied to all 3072 features independently. The second linear layer compresses the result back down to 768, selecting which combinations of those 3072 features are most useful to carry forward.

**Shape transformation story — tracing a batch through every step.**

Using `batch=2, num_tokens=3, emb_dim=768`:

```
x.shape = (2, 3, 768)    ← (batch, tokens, emb_dim)
           ↑  ↑  ↑
         batch tokens emb_dim

Step 1 — nn.Linear(768, 3072):
    Each token's 768-dim row is multiplied by the weight matrix (3072, 768)
    and a bias of size 3072 is added.
    One token: (768,) @ (768, 3072) → (3072,)
    Full batch: (2, 3, 768) → (2, 3, 3072)

    out1.shape = (2, 3, 3072)    ← (batch, tokens, 4 * emb_dim)
                  ↑  ↑  ↑
                batch tokens  4×emb_dim

Step 2 — GELU():
    Applied element-wise to all 3072 features of every token.
    Shape unchanged.

    out2.shape = (2, 3, 3072)    ← same shape, values gated by GELU

Step 3 — nn.Linear(3072, 768):
    Each token's 3072-dim row is compressed back to 768.
    One token: (3072,) @ (3072, 768) → (768,)
    Full batch: (2, 3, 3072) → (2, 3, 768)

    out3.shape = (2, 3, 768)    ← (batch, tokens, emb_dim) — back to input shape
```

**Why expand by exactly 4×.**

The factor of 4 is an empirical choice from the original 2017 transformer paper. The intuition is that the expansion gives the GELU room to perform a richer non-linear transformation before projecting back. With only 768 features in the narrow space, the model can only mix 768 dimensions at a time. With 3072 in the wide space, it can represent more complex combinations. The factor of 4 is not mathematically special — some modern architectures use $\frac{8}{3}$ or other ratios — but 4× has proven to be a reliable default for GPT-style models.

**Parameter count — where GPT-2's capacity actually lives.**

```
First Linear  weight: 768  × 3072 = 2,359,296
              bias:          3072 =     3,072
              subtotal:            2,362,368

Second Linear weight: 3072 ×  768 = 2,359,296
              bias:            768 =       768
              subtotal:            2,360,064

Total per FFN block:             ≈ 4,722,432    ← ~4.7 million parameters

× 12 transformer blocks:         ≈ 56,669,184   ← ~57 million parameters
```

The 12 FFN blocks alone account for roughly 57 million of GPT-2's 124 million total parameters — close to half. When the attention parameters are added, the FFN still represents the larger share. The common assumption that attention is where the model's capacity lives is misleading — the FFN is where the bulk of the weights are, and it is thought to act as a kind of key-value memory, storing factual associations that attention retrieves and routes.

**Position-wise independence.**

Each token's vector passes through the FFN completely independently. Token 0's computation never touches token 1's values inside the FFN — there is no cross-token operation here. Cross-token information exchange already happened in the multi-head attention sublayer earlier in the block. The FFN's role is to take each token's attention-updated representation and transform it non-linearly on its own terms: mix its own features, suppress some, amplify others, then write the result back.

**Running it.**

```python
ffn = FeedForward(GPT_CONFIG_124M)

x = torch.rand(2, 3, 768)    # (batch, num_tokens, emb_dim)
out = ffn(x)
print(out.shape)
# torch.Size([2, 3, 768])
```

Input shape `(2, 3, 768)` equals output shape `(2, 3, 768)`. This shape-preservation is not incidental — it is a hard requirement for the residual connection in the transformer block, where the FFN's input is added directly to its output. If the shapes differed, the addition would fail.

---

**What actually enters the FFN.**

By the time a token's vector reaches the FFN, it is no longer just "the embedding for the word you". The attention sublayer that ran just before the FFN has already mixed information from neighbouring tokens into it. So the 768-dim vector arriving at the FFN for "you" is more accurately described as "the word you, having already looked at and blended in context from the words before it". It is a contextualised representation, not a raw word embedding.

The FFN then processes this 768-dim vector completely on its own, with no awareness of any other token.

**What the FFN is actually learning.**

Think of the FFN as a lookup table of soft pattern matchers. The first linear layer (768 → 3072) projects the token's vector into a much wider space. Each of the 3072 neurons in that wider space is asking a question of the form "does this token's current representation match this particular pattern?". GELU then gates each neuron — strongly activating the ones whose pattern fired, suppressing the ones whose pattern didn't. The second linear layer (3072 → 768) then reads which patterns fired and uses that to write an update back into the 768-dim space.

Research (Geva et al. 2021, "Transformer Feed-Forward Layers Are Key-Value Memories") found that FFN neurons store factual associations. A neuron in an early layer might fire for "this token looks like it's part of a date expression". A neuron in a later layer might fire for "this token is the subject of a sentence about a European capital city". The second linear layer then writes the associated fact — "the capital of France is Paris" — into the representation.

**A small concrete example.**

Suppose the sentence is "The Eiffel Tower is located in" and the model is processing the token "in". By the time "in" reaches the FFN in a late transformer block, its 768-dim vector has already absorbed context from "Eiffel Tower" and "located" via attention. That contextualised vector might strongly activate a small cluster of the 3072 FFN neurons that learned during training to recognise "this is a location-completion context involving a famous landmark". The second linear layer, seeing those neurons fire, writes a strong signal toward Paris-like vocabulary directions into the output vector. When that vector eventually reaches the output head, "Paris" scores highest.

The FFN did not need to look at any other token to do this. All the relevant context had already been baked into the "in" vector by attention. The FFN's job was to recognise the pattern in that single vector and retrieve the associated fact.

**So to directly answer.**

Yes, each token's 768-dim vector goes through the FFN once, completely independently. But it is not learning "what comes after you" in a simple next-word sense. It is learning to recognise semantic and factual patterns in the contextualised representation and to fire the right output signal for each pattern. The weights that get trained are the two linear matrices — the 768×3072 first layer learns which patterns to detect, and the 3072×768 second layer learns what to write into the output when each pattern fires. Across 12 transformer blocks, each FFN layer handles increasingly abstract patterns: early blocks handle syntax and local phrases, later blocks handle facts, reasoning, and long-range semantic relationships.

## 12 — Section 4.4: ExampleDeepNeuralNetwork and print_gradients

**Summary.** This section is a self-contained experiment that has nothing to do with GPT directly. Its sole purpose is to demonstrate vanishing gradients in a 5-layer network without residual connections, then show that adding residual connections fixes the problem. The insight motivates why every transformer block wraps its sublayers in residual connections.

**The code.**

```python
class ExampleDeepNeuralNetwork(nn.Module):
    def __init__(self, layer_sizes, use_shortcut):
        super().__init__()
        self.use_shortcut = use_shortcut
        self.layers = nn.ModuleList([
            nn.Sequential(nn.Linear(layer_sizes[0], layer_sizes[1]), GELU()),
            nn.Sequential(nn.Linear(layer_sizes[1], layer_sizes[2]), GELU()),
            nn.Sequential(nn.Linear(layer_sizes[2], layer_sizes[3]), GELU()),
            nn.Sequential(nn.Linear(layer_sizes[3], layer_sizes[4]), GELU()),
            nn.Sequential(nn.Linear(layer_sizes[4], layer_sizes[5]), GELU()),
        ])

    def forward(self, x):
        for layer in self.layers:
            layer_output = layer(x)
            # add residual only when shapes match
            if self.use_shortcut and x.shape == layer_output.shape:
                x = x + layer_output
            else:
                x = layer_output
        return x


def print_gradients(model, x):
    output = model(x)
    target = torch.tensor([[0.]])
    loss = nn.MSELoss()(output, target)
    loss.backward()
    for name, param in model.named_parameters():
        if 'weight' in name:
            print(f"{name} has gradient mean of {param.grad.abs().mean().item()}")
```

**The problem this experiment demonstrates.**

Gradients flow backward through the network during `loss.backward()`. At each layer, the gradient is multiplied by that layer's local derivative before being passed further back. If those derivatives are consistently less than 1 — which they often are after GELU and linear projections — the gradient shrinks at every layer. By the time it reaches the first layer it can be so small that the weight update is effectively zero. That layer stops learning. This is vanishing gradients.

The deeper the network, the worse it gets. With 5 layers, gradients that start at 1.0 at the output might arrive at the input as $10^{-5}$ without residual connections.

**The architecture.**

`layer_sizes = [3, 3, 3, 3, 3, 1]` defines six sizes, giving five transition steps:

```
Layer 0: nn.Linear(3, 3) + GELU    input (3,) → output (3,)    shapes match → residual applies
Layer 1: nn.Linear(3, 3) + GELU    input (3,) → output (3,)    shapes match → residual applies
Layer 2: nn.Linear(3, 3) + GELU    input (3,) → output (3,)    shapes match → residual applies
Layer 3: nn.Linear(3, 3) + GELU    input (3,) → output (3,)    shapes match → residual applies
Layer 4: nn.Linear(3, 1) + GELU    input (3,) → output (1,)    shapes differ → residual skipped
```

The shape check `x.shape == layer_output.shape` is the guard that determines whether a residual is added. The first four layers pass 3-dim vectors through 3-dim outputs, so the addition works. The fifth layer projects down to 1-dim, so the shapes differ and the residual is skipped — the output replaces the input rather than being added to it.

**What the residual connection actually does — the addition visualised.**

For any of the first four layers, the forward pass with `use_shortcut=True` is:

```
Without residual:    x_next = layer(x)
With residual:       x_next = x + layer(x)
```

Visualised for a single 3-dim token vector passing through Layer 0:

```
x = [x0, x1, x2]                         ← input arriving at Layer 0

layer_output = Linear+GELU(x)
             = [f0, f1, f2]               ← transformed version

x_next = x + layer_output
       = [x0+f0, x1+f1, x2+f2]           ← input added back element-wise
```

The gradient flowing back through the addition splits into two paths: one through the layer's transformation and one directly through the addition with gradient 1.0 unchanged. Even if the transformation path produces a vanishingly small gradient, the direct path always delivers a gradient of at least 1.0 back to the earlier layers. This is the mechanism that defeats vanishing gradients.

**What `print_gradients` does.**

```
1. output = model(x)              — forward pass, builds the computation graph
2. loss = MSELoss(output, [[0.]]) — scalar loss, fake target of zero
3. loss.backward()                — backpropagation: populates .grad on every parameter
4. for each weight matrix:
       print mean of |gradient|   — one number per layer, large = healthy, tiny = vanishing
```

`param.grad.abs().mean()` computes the mean absolute gradient across all elements of the weight matrix. It is a single scalar summarising the overall strength of the learning signal reaching that layer. A healthy layer shows values on the order of $10^{-1}$ to $10^{-2}$. A vanishing gradient shows up as $10^{-5}$ or smaller — that layer receives essentially no signal and cannot update its weights meaningfully.

**Running both versions and reading the output.**

```python
layer_sizes = [3, 3, 3, 3, 3, 1]
sample_input = torch.tensor([[1., 0., -1.]])

# Without residual connections
model_without = ExampleDeepNeuralNetwork(layer_sizes, use_shortcut=False)
print_gradients(model_without, sample_input)
# layers.0.0.weight has gradient mean of 0.00020173191
# layers.1.0.weight has gradient mean of 0.00013988736
# layers.2.0.weight has gradient mean of 0.00005765429
# layers.3.0.weight has gradient mean of 0.00007730654
# layers.4.0.weight has gradient mean of 0.00504139643

# With residual connections
model_with = ExampleDeepNeuralNetwork(layer_sizes, use_shortcut=True)
print_gradients(model_with, sample_input)
# layers.0.0.weight has gradient mean of 0.22169792652
# layers.1.0.weight has gradient mean of 0.20392775536
# layers.2.0.weight has gradient mean of 0.32939490676
# layers.3.0.weight has gradient mean of 0.26559588313
# layers.4.0.weight has gradient mean of 1.32099163532
```

Without residuals, `layers.0.0.weight` receives a gradient of roughly $2 \times 10^{-4}$ — about 25 times smaller than the last layer's gradient of $5 \times 10^{-3}$. The signal degrades as it travels backward. With residuals, `layers.0.0.weight` receives a gradient of $0.22$ — the same order of magnitude as every other layer. The signal flows uniformly all the way to the first layer.

**Why this matters for GPT.**

A 12-layer GPT-2 is far deeper than this 5-layer toy. Without residual connections, gradients from the loss would shrink through 12 transformer blocks and the embedding layers would receive essentially no signal during training. Every transformer block in GPT-2 therefore wraps both its attention sublayer and its FFN sublayer in separate residual connections, ensuring that the gradient always has a direct path back to the earliest layers regardless of network depth. The `TransformerBlock` class built in the next section implements exactly this pattern.

## 13 — Section 4.4: Gradients Without Shortcuts — The Vanishing Problem

**Summary.** This cell runs the network without residual connections and prints the mean absolute gradient at each weight matrix. The numbers make the vanishing gradient problem concrete: the first layer receives a signal roughly 25 times weaker than the last layer, and in a real 12-layer network the ratio would be catastrophically larger.

**The code.**

```python
layer_sizes = [3, 3, 3, 3, 3, 1]
sample_input = torch.tensor([[1., 0., -1.]])

torch.manual_seed(123)
model_without_shortcut = ExampleDeepNeuralNetwork(layer_sizes, use_shortcut=False)
print_gradients(model_without_shortcut, sample_input)
# layers.0.0.weight has gradient mean of 0.00020173191
# layers.1.0.weight has gradient mean of 0.00012952960
# layers.2.0.weight has gradient mean of 0.00072653913
# layers.3.0.weight has gradient mean of 0.00139491090
# layers.4.0.weight has gradient mean of 0.00504139643
```

**What backpropagation is doing here.**

`loss.backward()` walks the computation graph in reverse, starting from the scalar loss at the output and computing `d_loss / d_weight` for every weight matrix. At each layer it applies the chain rule: the gradient arriving from the right is multiplied by the local derivative of that layer before being passed further left.

```
loss
  ↓  d_loss/d_output
Layer 4 gradient computed    → 0.00504
  ↓  × local derivative of Layer 4
Layer 3 gradient computed    → 0.00139
  ↓  × local derivative of Layer 3
Layer 2 gradient computed    → 0.00072
  ↓  × local derivative of Layer 2
Layer 1 gradient computed    → 0.00013
  ↓  × local derivative of Layer 1
Layer 0 gradient computed    → 0.00020
```

Each local derivative is a product of the GELU derivative and the weight matrix values at that layer. When those values are consistently less than 1 — as they typically are after random initialisation — each multiplication shrinks the gradient. By the time the signal reaches Layer 0 it is roughly 25 times smaller than it was at Layer 4.

**The numbers side by side.**

```
Layer    gradient mean    ratio vs Layer 4
──────────────────────────────────────────
  4       0.00504             1.0×       ← closest to the loss, strongest signal
  3       0.00139             3.6×
  2       0.00072             7.0×
  1       0.00013            38.8×
  0       0.00020            25.2×       ← furthest from loss, weakest signal
```

Layer 0 receives about 1/25th the learning signal that Layer 4 does. After a training step, Layer 4's weights shift meaningfully while Layer 0's weights barely move. Over thousands of steps, Layer 4 has learned a rich transformation while Layer 0 is still close to its random initialisation.

**Why this compounds catastrophically in a real GPT.**

This toy network has 5 layers. GPT-2 small has 12 transformer blocks, each containing two sublayers (attention and FFN), giving roughly 24 sequential transformations through which gradients must pass before reaching the token embeddings. If each sublayer multiplies the gradient by a factor of $0.7$ on average:

```
After  5 sublayers:  0.7^5  ≈ 0.168    ← gradient at 17% of original
After 12 sublayers:  0.7^12 ≈ 0.014    ← gradient at 1.4% of original
After 24 sublayers:  0.7^24 ≈ 0.0002   ← gradient at 0.02% of original
```

The embedding layer and the early transformer blocks effectively stop learning. The model reaches a mediocre plateau that no amount of extra training time can escape, because the weight updates for the front layers are too small to move them anywhere useful. This is why residual connections are not a convenience but a hard requirement for training networks of GPT's depth.

**What the next cell will show.**

Running the identical experiment with `use_shortcut=True` will produce gradients of roughly $0.2$ at every layer — all within the same order of magnitude. The residual connection's direct gradient path of 1.0 bypasses the shrinking multiplication chain and delivers a healthy signal to every layer regardless of depth.

## 14 — Section 4.4: Gradients With Shortcuts — The Fix

**Summary.** This cell reruns the identical experiment with `use_shortcut=True`. The gradient at Layer 0 jumps from $0.00020$ to $0.22$ — a 1000× increase. The residual connection provides a direct gradient path back through every layer that is immune to the shrinking chain rule multiplications.

**The code.**

```python
torch.manual_seed(123)
model_with_shortcut = ExampleDeepNeuralNetwork(layer_sizes, use_shortcut=True)
print_gradients(model_with_shortcut, sample_input)
# layers.0.0.weight has gradient mean of 0.22169792652
# layers.1.0.weight has gradient mean of 0.20392775536
# layers.2.0.weight has gradient mean of 0.32939490676
# layers.3.0.weight has gradient mean of 0.26559588313
# layers.4.0.weight has gradient mean of 1.32099163532
```

**The before-and-after comparison.**

```
Layer    without shortcut    with shortcut    ratio
────────────────────────────────────────────────────
  4          0.00504            1.321          262×
  3          0.00139            0.266          191×
  2          0.00072            0.329          457×
  1          0.00013            0.204         1569×
  0          0.00020            0.222         1100×
```

Every layer receives a gradient roughly three orders of magnitude larger. More importantly, the gradients across all five layers are now within the same order of magnitude — roughly $0.2$ to $1.3$. No layer is starved of signal relative to any other. The optimizer can move every layer's weights at a comparable rate, and the whole network can learn simultaneously.

**Why the math guarantees this.**

A residual block computes:

$$y = x + f(x)$$

During the backward pass, the gradient of the loss with respect to $x$ is computed via the chain rule:

$$\frac{\partial \mathcal{L}}{\partial x} = \frac{\partial \mathcal{L}}{\partial y} \cdot \frac{\partial y}{\partial x} = \frac{\partial \mathcal{L}}{\partial y} \cdot \left(1 + \frac{\partial f(x)}{\partial x}\right)$$

The term inside the bracket is $1 + \frac{\partial f(x)}{\partial x}$. No matter what $\frac{\partial f(x)}{\partial x}$ becomes — even if it shrinks to near zero — the full bracket never drops below 1. The gradient flowing backward is always at least as large as the gradient flowing in. There is no multiplicative shrinkage along the residual path.

Visualised as two separate paths during backpropagation:

```
gradient arriving from the right
           │
           ├──── through f(x) path ────► × (∂f/∂x)   ← can be small, shrinks gradient
           │
           └──── through residual path ─► × 1.0       ← always exactly 1.0, never shrinks
           │
           ↓
    sum of both paths = gradient passed further left
```

Even when the $f(x)$ path produces a near-zero contribution, the residual path delivers the full incoming gradient unchanged. This is the highway analogy: even if the lane through $f(x)$ is congested, the residual lane is always open and always moving at full speed.

**Why this is non-negotiable in GPT.**

In a transformer block, both the attention sublayer and the FFN sublayer are wrapped in their own separate residual connections:

```
x → LayerNorm → Attention → Dropout → + → LayerNorm → FFN → Dropout → +
└──────────────────────────────────────►   └─────────────────────────────►
        (residual 1 bypasses attention)         (residual 2 bypasses FFN)
```

With 12 such blocks, there are 24 residual paths threading all the way from the output loss back to the input embeddings. Regardless of what the attention and FFN sublayers do to the gradients, those 24 direct paths guarantee that every layer receives a healthy learning signal. Remove the residuals and GPT-2 would be untrainable at 12 blocks — let alone the 96 blocks in GPT-3.

**What the remaining difference between layers tells us.**

Layer 4 still has a noticeably larger gradient ($1.32$) than the earlier layers ($0.20$–$0.33$). The residual connections eliminate the catastrophic vanishing but do not make all gradients perfectly equal — layers closer to the loss naturally receive somewhat stronger signals because the chain from the loss to them is shorter. This mild imbalance is acceptable and does not impair training. The critical requirement is that early layers receive gradients large enough to produce meaningful weight updates, and with residuals that requirement is comfortably met.

## 15 — Section 4.5: The TransformerBlock

**Summary.** This section assembles the full transformer block — the unit that gets stacked 12 times in GPT-2. It wires together everything built so far: `MultiHeadAttention`, `FeedForward`, `LayerNorm`, dropout, and residual connections. The forward pass follows the pre-LN pattern: normalise first, run the sublayer, apply dropout, then add the original un-normalised input back.

**The code.**

```python
from previous_chapters import MultiHeadAttention

class TransformerBlock(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.att = MultiHeadAttention(
            d_in=cfg["emb_dim"],            # 768
            d_out=cfg["emb_dim"],           # 768 — shape-preserving
            context_length=cfg["context_length"],
            num_heads=cfg["n_heads"],       # 12 heads, each 64-dim
            dropout=cfg["drop_rate"],
            qkv_bias=cfg["qkv_bias"])       # False — GPT-2 convention
        self.ff            = FeedForward(cfg)          # 768 → 3072 → 768
        self.norm1         = LayerNorm(cfg["emb_dim"]) # before attention
        self.norm2         = LayerNorm(cfg["emb_dim"]) # before FFN
        self.drop_shortcut = nn.Dropout(cfg["drop_rate"])

    def forward(self, x):
        # Sub-block 1 — pre-LN attention with residual
        shortcut = x                   # (batch, seq_len, 768) — saved before any change
        x = self.norm1(x)              # (batch, seq_len, 768) — normalised copy
        x = self.att(x)                # (batch, seq_len, 768) — attention output
        x = self.drop_shortcut(x)      # (batch, seq_len, 768) — regularised
        x = x + shortcut               # (batch, seq_len, 768) — residual add

        # Sub-block 2 — pre-LN FFN with residual
        shortcut = x                   # (batch, seq_len, 768) — saved before any change
        x = self.norm2(x)              # (batch, seq_len, 768) — normalised copy
        x = self.ff(x)                 # (batch, seq_len, 768) — FFN output
        x = self.drop_shortcut(x)      # (batch, seq_len, 768) — regularised
        x = x + shortcut               # (batch, seq_len, 768) — residual add

        return x                       # (batch, seq_len, 768) — same shape as input
```

**The pre-LN pattern — exactly what each line does.**

The forward pass of each sub-block follows the same five-step sequence. Walking through Sub-block 1 in detail:

```
shortcut = x
```

A reference to the current tensor is saved. This is not a copy of the data — it is a second name pointing to the same tensor. No memory is allocated. When `x` is reassigned on the next line, `shortcut` still points to the original tensor.

```
x = self.norm1(x)
```

LayerNorm is applied to the original `x`, producing a normalised version. The original is now only reachable via `shortcut`. This is the "pre" in pre-LN — normalisation happens before the sublayer sees the data, not after.

```
x = self.att(x)
```

Multi-head attention runs on the normalised tensor. It can only see normalised activations, which stabilises the attention score computation. Shape is unchanged: `(batch, seq_len, 768)` in and out.

```
x = self.drop_shortcut(x)
```

Dropout randomly zeroes 10% of values during training, providing regularisation. During inference (`.eval()` mode) this is a no-op.

```
x = x + shortcut
```

The attention output is added back to the original un-normalised input. The residual guarantees a direct gradient path back to all earlier layers, as demonstrated in Sections 12–14.

Sub-block 2 is structurally identical with `self.norm2` and `self.ff` in place of `self.norm1` and `self.att`.

**Shape transformation story — tracing the full block.**

Using `batch=2, seq_len=4, emb_dim=768`:

```
x entering TransformerBlock:
x.shape = (2, 4, 768)    ← (batch, seq_len, emb_dim)

Sub-block 1:
  shortcut = x                         (2, 4, 768)  ← saved reference
  x = norm1(x)                         (2, 4, 768)  ← mean 0, var 1 per token
  x = att(x)                           (2, 4, 768)  ← each token gathers context
  x = drop_shortcut(x)                 (2, 4, 768)  ← 10% zeroed during training
  x = x + shortcut                     (2, 4, 768)  ← attention update added to original

Sub-block 2:
  shortcut = x                         (2, 4, 768)  ← saved reference (post-attention)
  x = norm2(x)                         (2, 4, 768)  ← mean 0, var 1 per token
  x = ff(x)        768→3072→768        (2, 4, 768)  ← each token re-mixes its own features
  x = drop_shortcut(x)                 (2, 4, 768)  ← 10% zeroed during training
  x = x + shortcut                     (2, 4, 768)  ← FFN update added to post-attention

x leaving TransformerBlock:
x.shape = (2, 4, 768)    ← identical to input shape
```

The block's output shape is exactly its input shape. This is what makes stacking 12 blocks possible — each one hands off `(batch, seq_len, 768)` to the next without any reshaping.

**Pre-LN vs post-LN — the key difference.**

The original 2017 transformer used post-LN, where normalisation is applied after the residual add:

```
Post-LN (original paper):        Pre-LN (GPT-2 and all modern models):

shortcut = x                      shortcut = x
x = sublayer(x)                   x = norm(x)          ← norm before sublayer
x = dropout(x)                    x = sublayer(x)
x = norm(x + shortcut)            x = dropout(x)
                                  x = x + shortcut      ← residual outside norm
```

In post-LN the residual gradient must pass through the LayerNorm on its way back. LayerNorm's normalisation step introduces its own scale that can interfere with gradient magnitude. In pre-LN the residual path is clean: `x = x + shortcut` means the gradient flows directly through the addition to `shortcut` with gradient exactly 1.0, completely bypassing both the LayerNorm and the sublayer. This is why pre-LN trains more stably for deep stacks and became universal after 2019.

**Why two separate LayerNorm instances.**

`norm1` and `norm2` each have their own independent `scale` and `shift` parameters of shape `(768,)`. They are not shared because the distribution of activations entering the attention sublayer and the distribution entering the FFN are different after training — the optimiser will push them to different values. Sharing them would force a single normalisation to serve two structurally different inputs, reducing the model's expressiveness for negligible parameter savings.

The parameter cost is small: each LayerNorm has $768 \times 2 = 1536$ parameters (scale + shift), so two per block adds 3072 parameters. Across 12 blocks that is 36,864 parameters — less than 0.03% of the 124M total.

**Running it.**

```python
torch.manual_seed(123)
x = torch.rand(2, 4, 768)    # (batch, seq_len, emb_dim)
block = TransformerBlock(GPT_CONFIG_124M)
output = block(x)
print("Input shape:", x.shape)
print("Output shape:", output.shape)
# Input shape:  torch.Size([2, 4, 768])
# Output shape: torch.Size([2, 4, 768])
```

Input and output shapes are identical. The block is a shape-preserving transformation — every operation inside it either preserves shape directly (LayerNorm, dropout, residual add) or is specifically designed to return to the input shape (attention with `d_out=d_in`, FFN with matching expand-and-contract dimensions).

## 16 — Section 4.5: Running the TransformerBlock

**Summary.** This cell instantiates a single `TransformerBlock`, passes a random input through it, and confirms the output shape matches the input shape. There is no new code here — it is a shape-correctness check identical in spirit to the `DummyGPTModel` run in Section 4.

**The code.**

```python
torch.manual_seed(123)

x = torch.rand(2, 4, 768)    # (batch, num_tokens, emb_dim)
block = TransformerBlock(GPT_CONFIG_124M)
output = block(x)

print("Input shape:",  x.shape)
print("Output shape:", output.shape)
# Input shape:  torch.Size([2, 4, 768])
# Output shape: torch.Size([2, 4, 768])
```

**Why this check matters.**

Shape-preservation is the contract every transformer block must honour. `nn.Sequential` in the full `GPTModel` will call 12 blocks one after another with no reshaping between them — the output tensor of block $i$ is passed directly as the input tensor of block $i+1$. If any operation inside a block silently changed the shape, the residual add in the very next block would throw a shape-mismatch error. The check here catches any such bug before it is buried inside a 12-block stack where the error message would be harder to trace.

**What changed inside the tensor even though the shape did not.**

The input `x` was a random `(2, 4, 768)` tensor — each token's 768-dim vector had no relationship to any other token. After passing through the block:

Sub-block 1 (attention) caused each token's vector to gather weighted information from the tokens it could see under the causal mask. Token at position 0 saw only itself. Token at position 3 saw positions 0, 1, 2, and 3 and blended their value vectors according to learned attention weights. Every token's 768-dim vector is now a mixture of earlier tokens' representations — cross-token information has been woven in.

Sub-block 2 (FFN) then took each token's attention-updated vector and transformed it independently — expanding to 3072 dimensions, applying GELU, contracting back to 768. No cross-token interaction happens here; each token re-mixes its own features non-linearly.

Both sub-blocks added their outputs back to their respective residual shortcuts. The final vector at each position is therefore the original input vector plus an additive update computed by attention plus an additive update computed by the FFN:

```
output[batch, t, :] = x[batch, t, :]           ← original input survives intact
                     + Δ_attention[batch, t, :] ← additive update from attention
                     + Δ_ffn[batch, t, :]       ← additive update from FFN
```

The shape `(2, 4, 768)` is identical but the content is fundamentally richer — each token now encodes context from its neighbourhood rather than being an isolated random vector.

**Stacking 12 blocks — what stays the same and what accumulates.**

Each of the 12 `TransformerBlock` instances in `GPTModel` applies the same structural pattern but has its own independent weights. Earlier blocks tend to capture lower-level patterns (local syntactic relationships, common word pairings). Later blocks tend to capture higher-level patterns (semantic roles, long-range dependencies). This specialisation emerges from training — the architecture does not impose it. What the architecture does impose is that every block operates on and returns the same `(batch, seq_len, emb_dim)` shape, so whatever each block has learned to compute, it contributes as an additive refinement to the same running representation.

## 17 — Section 4.6: The Full GPTModel Class

**Summary.** This section replaces the two dummy stubs from Section 2 with the real `TransformerBlock` and `LayerNorm` classes built in Sections 8 and 15. Everything else — the embeddings, dropout, sequential stack, final norm, output head, and the entire forward pass — is structurally identical to `DummyGPTModel`. This is the payoff of the scaffolding pattern: swap two class names and the full model is complete.

**The code.**

```python
class GPTModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.tok_emb    = nn.Embedding(cfg["vocab_size"],     cfg["emb_dim"])
        self.pos_emb    = nn.Embedding(cfg["context_length"], cfg["emb_dim"])
        self.drop_emb   = nn.Dropout(cfg["drop_rate"])

        # 12 real TransformerBlocks — replaces 12 DummyTransformerBlocks
        self.trf_blocks = nn.Sequential(
            *[TransformerBlock(cfg) for _ in range(cfg["n_layers"])])

        # real LayerNorm — replaces DummyLayerNorm
        self.final_norm = LayerNorm(cfg["emb_dim"])
        self.out_head   = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, in_idx):
        batch_size, seq_len = in_idx.shape
        tok_embeds = self.tok_emb(in_idx)
        pos_embeds = self.pos_emb(torch.arange(seq_len, device=in_idx.device))
        x = tok_embeds + pos_embeds        # (batch, seq_len, emb_dim)
        x = self.drop_emb(x)               # (batch, seq_len, emb_dim)
        x = self.trf_blocks(x)             # (batch, seq_len, emb_dim)
        x = self.final_norm(x)             # (batch, seq_len, emb_dim)
        logits = self.out_head(x)          # (batch, seq_len, vocab_size)
        return logits
```

**What changed from DummyGPTModel — nothing except the two swaps.**

```
DummyGPTModel                       GPTModel
─────────────────────────────────────────────────────────
DummyTransformerBlock(cfg)    →     TransformerBlock(cfg)
DummyLayerNorm(cfg["emb_dim"]) →    LayerNorm(cfg["emb_dim"])
everything else                     identical
```

The forward pass is word-for-word identical. The embedding lookups, positional addition, dropout, sequential application, final norm, and output projection are all unchanged. This is the direct benefit of the scaffolding pattern from Section 2: the skeleton was verified correct before any real internals existed, so dropping in the real classes requires zero structural changes.

**The complete forward pass shape story.**

Using `batch=2, seq_len=4, emb_dim=768, vocab_size=50257`:

```
in_idx.shape = (2, 4)    ← (batch, seq_len) — raw integer token IDs

Step 1 — tok_emb(in_idx):
    Each integer → row lookup in (50257, 768) table
    (2, 4) → (2, 4, 768)

Step 2 — pos_emb(arange(4)):
    [0, 1, 2, 3] → row lookup in (1024, 768) table
    → (4, 768)    ← no batch axis

Step 3 — tok_embeds + pos_embeds:
    (2, 4, 768) + (4, 768)
    pos_embeds broadcasts across batch axis
    → (2, 4, 768)    ← meaning + position fused

Step 4 — drop_emb:
    10% zeroed during training, no-op at inference
    → (2, 4, 768)    ← shape unchanged

Step 5 — trf_blocks (12 × TransformerBlock):
    Each block: norm → attention → residual → norm → FFN → residual
    Each block is shape-preserving: (2, 4, 768) → (2, 4, 768)
    Applied 12 times in sequence
    → (2, 4, 768)    ← shape unchanged, content deeply transformed

Step 6 — final_norm:
    LayerNorm over the last dim, per token
    → (2, 4, 768)    ← shape unchanged, activations stabilised

Step 7 — out_head (Linear 768 → 50257, bias=False):
    Each token's 768-dim vector projected to 50257 scores
    → (2, 4, 50257)  ← one logit per vocabulary word per token
```

The shape changes only twice: at Step 1 when the integer IDs become dense vectors, and at Step 7 when the dense vectors become vocabulary scores. Every step in between is shape-preserving.

**Why the final LayerNorm sits where it does.**

After 12 residual additions the hidden state at the last block's output has accumulated contributions from all 12 blocks. Each block adds its own update on top of the running representation:

```
h_12 = h_0 + Δ_block1 + Δ_block2 + ... + Δ_block12
```

If any individual $\Delta$ is consistently large, the cumulative sum drifts to a much larger scale than a single block's output. Feeding that drifted tensor directly into the output projection would produce logits with wildly varying magnitudes, making softmax numerically unstable and gradients erratic. `final_norm` centres and rescales the accumulated representation one last time before the projection, ensuring the output head always receives a well-behaved input regardless of how the residual sums have accumulated during training.

**The full architecture in one picture.**

```
in_idx (2, 4)
    │
    ▼
tok_emb + pos_emb → dropout          (2, 4, 768)
    │
    ▼
TransformerBlock 1                    (2, 4, 768)
  ├─ pre-LN → MultiHeadAttention → dropout → residual
  └─ pre-LN → FeedForward        → dropout → residual
    │
    ▼
TransformerBlock 2                    (2, 4, 768)
  ├─ pre-LN → MultiHeadAttention → dropout → residual
  └─ pre-LN → FeedForward        → dropout → residual
    │
   ...
    │
    ▼
TransformerBlock 12                   (2, 4, 768)
  ├─ pre-LN → MultiHeadAttention → dropout → residual
  └─ pre-LN → FeedForward        → dropout → residual
    │
    ▼
final LayerNorm                       (2, 4, 768)
    │
    ▼
out_head Linear(768 → 50257)          (2, 4, 50257)
    │
    ▼
logits
```

Every component in this diagram has been built and explained individually in Sections 8 through 15. `GPTModel` is their composition — nothing new is introduced here beyond the wiring.

## 18 — Section 4.6: Running the Real Model on the Batch

**Summary.** This cell runs the real `GPTModel` on the same batch used in Section 4 with the dummy model. The output shape is identical — `(2, 4, 50257)` — but the logit values are completely different because the input now passes through 12 real transformer blocks rather than 12 identity stubs. The model is untrained so the values are still meaningless noise, but the shape confirms the full pipeline is wired correctly.

**The code.**

```python
torch.manual_seed(123)
model = GPTModel(GPT_CONFIG_124M)

out = model(batch)
print("Input batch:\n", batch)
print("\nOutput shape:", out.shape)
print(out)
# Input batch:
#  tensor([[6109, 3626, 6100,  345],
#          [6109, 1110, 6622,  257]])
#
# Output shape: torch.Size([2, 4, 50257])
# tensor([[[ 0.3613,  0.4222, -0.0711,  ...,  0.3483,  1.0790,  0.2358],
#          [-0.4946, -0.1925,  0.7345,  ..., -0.6020,  0.2990, -0.4932],
#          [ 0.2731, -0.5522,  0.2360,  ...,  0.7144, -0.8184, -0.4492],
#          [-0.3859,  0.4774,  0.5085,  ..., -0.3339, -0.5697,  0.8504]],
#         [[ 0.3613,  0.4222, -0.0711,  ...,  0.3483,  1.0790,  0.2358],
#          [-0.7424, -0.1365,  0.4764,  ...,  0.1047,  0.8780, -0.3980],
#          [-0.1230, -0.2874,  0.6661,  ..., -0.8505, -0.8423, -0.3760],
#          [ 0.0196,  0.5307,  0.2088,  ...,  0.3447, -0.7280, -0.3948]]],
#        grad_fn=<UnsafeViewBackward0>)
```

**Why the output shape is identical to the dummy run.**

The shape `(2, 4, 50257)` is determined entirely by the model's architecture — `batch=2` sentences, `seq_len=4` tokens each, `vocab_size=50257` scores per token. That architecture is identical between `DummyGPTModel` and `GPTModel`. The dummy stubs were identity functions, but they still respected the shape contract: `(batch, seq_len, emb_dim)` in and `(batch, seq_len, emb_dim)` out. Swapping them for real transformer blocks changes the values at every position but cannot change the shape, because the real blocks honour the same contract.

**Why the logit values are different from the dummy run.**

In `DummyGPTModel`, the 12 stubs returned their input unchanged. The logits were therefore:

```
DummyGPTModel path:
tok_embeds + pos_embeds → dropout → [identity × 12] → DummyLayerNorm → out_head
                                         ↑
                              no transformation happened here
```

In `GPTModel`, the 12 real blocks each ran multi-head attention and an FFN with residuals, deeply transforming the hidden state:

```
GPTModel path:
tok_embeds + pos_embeds → dropout → [TransformerBlock × 12] → LayerNorm → out_head
                                              ↑
                          cross-token mixing, non-linear feature transformation,
                          12 sets of learned weight matrices applied here
```

The `out_head` in both cases projects whatever hidden state it receives onto vocabulary scores. In the dummy model it projected lightly processed embeddings. In the real model it projects 12-times-refined contextual representations. The values are completely different — but both are random noise because neither model has been trained.

**What `torch.manual_seed(123)` controls here.**

The seed pins the random initialisation of every weight matrix created during `GPTModel(GPT_CONFIG_124M)`: the two embedding tables, all Q/K/V and output projection matrices inside each of the 12 attention modules, all weight matrices and biases in each of the 12 FFN modules, all scale and shift parameters in the 26 LayerNorm instances (2 per block + 1 final), and the output head. Without the seed, every run would produce different logit values. With it, the output is reproducible and matches the book exactly.

**What training will change.**

Running `GPTModel(GPT_CONFIG_124M)` and calling it on a batch is already the complete inference pipeline. The only thing missing is meaningful weights. Chapter 5 will feed the model text, compute a cross-entropy loss comparing `out[:, :-1, :]` (the model's next-token predictions) against `batch[:, 1:]` (the actual next tokens), and use `loss.backward()` plus an optimiser to nudge every weight matrix in the direction that reduces that loss. After enough steps on enough text, the logit values will stop being noise and start reflecting genuine next-token probability distributions. The shape `(2, 4, 50257)` will remain exactly the same throughout.

## 19 — Section 4.6: Counting the Parameters

**Summary.** This cell counts every scalar value in the model that PyTorch will update during training. The result is 163 million parameters — higher than the advertised "GPT-2 124M" because the output head's weights are counted separately here rather than being tied to the token embedding table as they were in the original GPT-2 release.

**The code.**

```python
total_params = sum(p.numel() for p in model.parameters())
print(f"Total number of parameters: {total_params:,}")
# Total number of parameters: 163,009,536
```

`model.parameters()` returns a generator of every `nn.Parameter` tensor registered anywhere in the model tree. `.numel()` returns the total number of scalar elements in a tensor — for a weight matrix of shape `(768, 3072)` that is `768 × 3072 = 2,359,296`. Summing these across all parameters gives the total count.

**Building the count from scratch.**

```
Token embedding table:
  nn.Embedding(50257, 768)
  50257 × 768 = 38,597,376

Position embedding table:
  nn.Embedding(1024, 768)
  1024 × 768 = 786,432

Per TransformerBlock (repeated × 12):

  MultiHeadAttention:
    W_query:   nn.Linear(768, 768, bias=False) → 768 × 768 = 589,824
    W_key:     nn.Linear(768, 768, bias=False) → 768 × 768 = 589,824
    W_value:   nn.Linear(768, 768, bias=False) → 768 × 768 = 589,824
    out_proj:  nn.Linear(768, 768)             → 768 × 768 + 768 = 590,592
    subtotal attention:                                       2,360,064

  FeedForward:
    Linear(768, 3072):  768 × 3072 + 3072 = 2,362,368
    Linear(3072, 768):  3072 × 768 + 768  = 2,360,064
    subtotal FFN:                           4,722,432

  LayerNorm norm1:  scale (768) + shift (768) = 1,536
  LayerNorm norm2:  scale (768) + shift (768) = 1,536
  subtotal LayerNorm:                           3,072

  Total per block:  2,360,064 + 4,722,432 + 3,072 = 7,085,568

12 blocks:  7,085,568 × 12 = 85,026,816

Final LayerNorm:
  scale (768) + shift (768) = 1,536

Output head:
  nn.Linear(768, 50257, bias=False) → 768 × 50257 = 38,597,376

Grand total:
  38,597,376     token embedding
+    786,432     position embedding
+ 85,026,816     12 transformer blocks
+      1,536     final LayerNorm
+ 38,597,376     output head
─────────────────
 163,009,536     ✓
```

**Why this says 163M when GPT-2 is called "124M".**

The original GPT-2 paper used **weight tying**: the output head's weight matrix was set equal to the token embedding matrix rather than being a separate parameter. Both have shape `(50257, 768)`, so tying them saves 38,597,376 parameters and brings the total down to approximately 124M. This implementation keeps them separate — `self.tok_emb` and `self.out_head` are two independent weight matrices — which is simpler to implement and understand. The difference has a negligible effect on model quality.

```
With separate output head (this implementation):   163,009,536
Minus tok_emb shared with out_head (original GPT-2): -38,597,376
                                                   ─────────────
Approximate original GPT-2 parameter count:        124,412,160  ≈ 124M
```

**What 163 million parameters means for memory.**

Each parameter is a single floating-point scalar. The memory cost depends on the numeric format used:

```
fp32  (4 bytes per parameter):  163,009,536 × 4 ≈  652 MB   ← default PyTorch
bf16  (2 bytes per parameter):  163,009,536 × 2 ≈  326 MB   ← common for inference
int8  (1 byte  per parameter):  163,009,536 × 1 ≈  163 MB   ← quantised inference
```

Training with the Adam optimiser requires significantly more memory than inference alone. Adam maintains two extra buffers per parameter — a first-moment estimate (momentum) and a second-moment estimate (variance) — in addition to the gradients themselves:

```
Model weights (fp32):    1× → 652 MB
Gradients (fp32):        1× → 652 MB
Adam momentum (fp32):    1× → 652 MB
Adam variance (fp32):    1× → 652 MB
                        ─────────────
Total training memory:   4× → ~2.6 GB   (weights only — activations add more)
```

Activations stored during the forward pass for use in backpropagation add further memory on top, proportional to batch size and sequence length. This is why fine-tuning even a 124M model requires several gigabytes of GPU RAM, and why techniques like gradient checkpointing (recomputing activations during backward rather than storing them) and 4-bit quantisation (QLoRA) exist — to make larger models trainable on hardware with limited memory.

## 20 — Section 4.6: Weight Tying and the 124M Number

**Summary.** This cell prints the shapes of the token embedding table and the output head weight matrix, showing they are identical. This is not a coincidence — they perform inverse operations on the same vocabulary space. The original GPT-2 exploited this by sharing one matrix between both, reducing the parameter count by 38.6M and producing the famous "124M" figure.

**The code.**

```python
print("Token embedding layer shape:", model.tok_emb.weight.shape)
print("Output layer shape:",          model.out_head.weight.shape)
# Token embedding layer shape: torch.Size([50257, 768])
# Output layer shape:          torch.Size([50257, 768])

total_params_gpt2 = total_params - sum(p.numel() for p in model.out_head.parameters())
print(f"Number of trainable parameters considering weight tying: {total_params_gpt2:,}")
# Number of trainable parameters considering weight tying: 124,412,160
```

**Why the two matrices have the same shape.**

The token embedding table and the output head weight matrix both live in the space connecting token IDs to 768-dim vectors — they just traverse that space in opposite directions:

```
Token embedding:     token ID (integer) → 768-dim vector
                     implemented as row lookup: tok_emb.weight[token_id]
                     shape: (50257, 768) — one 768-dim row per vocabulary word

Output head:         768-dim hidden state → 50257 scores
                     implemented as dot product: hidden @ out_head.weight.T
                     shape: (50257, 768) — one 768-dim direction per vocabulary word
```

The token embedding asks "given this token ID, what vector represents it?" The output head asks "given this hidden state vector, how strongly does it point toward each vocabulary direction?" Both questions are answered by the same `(50257, 768)` matrix — one reads it row-by-row, the other multiplies against it as a projection.

**What weight tying does.**

Weight tying makes the two matrices literally the same object in memory:

```python
# Conceptually — not implemented in this notebook
model.out_head.weight = model.tok_emb.weight
```

After tying, there is only one `(50257, 768)` matrix instead of two. Gradients flow into it from both the embedding lookup (during the forward pass through `tok_emb`) and the output projection (during the forward pass through `out_head`). The optimiser updates a single set of 38,597,376 scalars that serve both roles simultaneously.

**How this produces the 124M figure.**

```
Full model with separate output head:    163,009,536
Minus output head parameters:           - 38,597,376
                                         ───────────
With weight tying (original GPT-2):      124,412,160  ← the published "124M" count
```

The subtraction `total_params - sum(p.numel() for p in model.out_head.parameters())` is exactly this arithmetic. The output head contributes `768 × 50257 = 38,597,376` scalars. Removing those from the count gives 124,412,160 — the parameter count Anthropic, OpenAI, and the research literature refer to when they say "GPT-2 Small has 124M parameters".

**Why this implementation keeps them separate.**

During from-scratch training in Chapter 5, the two matrices are learning to do different things from different gradient signals. The embedding matrix receives gradients from the token lookup — signals about which vectors should represent which words given the context the model has been building up. The output head receives gradients from the cross-entropy loss — signals about which 768-dim directions best discriminate between the correct next token and the incorrect ones. When tied, these two gradient streams compete: an update that improves the output projection may slightly harm the embedding lookup, and vice versa. Keeping them separate lets each matrix specialise independently, which converges faster and more stably during training.

Weight tying will become necessary again when loading OpenAI's pre-trained GPT-2 checkpoint in a later chapter, because that checkpoint was saved with tied weights. The loading code will need to explicitly copy `tok_emb.weight` into `out_head.weight` to match the checkpoint's structure.

## 21 — Section 4.6: Model Size in Megabytes

**Summary.** This cell converts the raw parameter count into a concrete file size and memory footprint. The arithmetic is simple — parameters times bytes per parameter — but the result grounds all subsequent discussion of hardware requirements, checkpoint sizes, and the practical constraints of training vs inference.

**The code.**

```python
total_size_bytes = total_params * 4       # fp32: 4 bytes per parameter
total_size_mb    = total_size_bytes / (1024 * 1024)
print(f"Total size of the model: {total_size_mb:.2f} MB")
# Total size of the model: 621.83 MB
```

**Where the number comes from.**

Each parameter is stored as a 32-bit float (fp32), which occupies exactly 4 bytes. The division by `1024 * 1024` converts bytes to mebibytes (the unit `torch.save` and most deep-learning tools report):

```
163,009,536 parameters
×          4 bytes per parameter (fp32)
─────────────────────────────────────
652,038,144 bytes
÷    1,048,576 bytes per MB  (1024 × 1024)
─────────────────────────────────────
       621.83 MB
```

**How the size changes across numeric formats.**

The same 163M parameters stored in different precisions:

```
Format    Bytes per param    Model size       Typical use
──────────────────────────────────────────────────────────────────
fp32           4             621.83 MB        default PyTorch training
bf16           2             310.92 MB        modern training pipelines
fp16           2             310.92 MB        older GPU inference
int8           1             155.46 MB        quantised inference
nf4 (4-bit)   0.5             77.73 MB        QLoRA fine-tuning
```

bf16 and fp16 both use 2 bytes but have different numeric ranges — bf16 matches fp32's exponent range, making it safer for training where gradient magnitudes vary widely. int8 and nf4 are used for inference or parameter-efficient fine-tuning, not full-precision training.

**Disk size vs GPU memory.**

When you call `torch.save(model.state_dict(), "gpt2.pt")`, the file on disk is approximately 622 MB — one fp32 scalar per parameter, plus a small overhead for the Python dictionary structure storing the parameter names. When you load that file and call `model.to("cuda")`, the GPU must allocate at least 622 MB of VRAM just to hold the weights.

In practice, running the model requires more than just the weights:

```
Inference memory breakdown (approximate):
  Model weights:          622 MB   ← the 621.83 MB computed here
  Activations (forward):  ~75 MB   ← intermediate tensors at batch=1, seq=1024
  Overhead and buffers:   ~50 MB
  ─────────────────────────────
  Total VRAM needed:      ~750 MB  ← roughly 1.2× model size

Training memory breakdown (approximate, fp32 + Adam):
  Model weights:          622 MB   ← 1× model size
  Gradients:              622 MB   ← 1× model size (same shape as weights)
  Adam momentum buffer:   622 MB   ← 1× model size (first moment)
  Adam variance buffer:   622 MB   ← 1× model size (second moment)
  Activations (stored
  for backward pass):    ~500 MB   ← depends on batch size and seq length
  ─────────────────────────────
  Total VRAM needed:     ~3 GB     ← roughly 4–5× model size
```

The practical consequence is that a GPU with 2 GB of VRAM can run this model for inference but cannot train it. A GPU with 8 GB can train it at small batch sizes. This is why the "4× rule" exists as a planning heuristic — if you know the model size in MB, multiply by 4 to estimate the minimum VRAM needed for a training run.

**How this scales to larger models.**

```
Model              Params     fp32 size    Min VRAM (training)
──────────────────────────────────────────────────────────────
GPT-2 Small         124M       474 MB         ~2 GB
GPT-2 Medium        355M      1.36 GB         ~5 GB
GPT-2 Large         774M      2.96 GB        ~12 GB
GPT-2 XL           1.5B       5.74 GB        ~23 GB
Llama-2 7B           7B        26.7 GB       ~107 GB
Llama-2 70B         70B       267 GB        ~1 TB
```

This is why QLoRA (4-bit weights plus low-rank adapters) was a significant advance — it brings a 7B model's training footprint down to roughly 10–15 GB, fitting on a single consumer GPU.

## 22 — Section 4.7: `generate_text_simple` — Greedy Decoding

**Summary.** This function is the autoregressive generation loop — the mechanism that turns a model trained to predict the next token into a text generator. It runs the model repeatedly, each time appending the most likely next token to the growing sequence, until the desired number of new tokens has been produced.

**The code.**

```python
def generate_text_simple(model, idx, max_new_tokens, context_size):
    for _ in range(max_new_tokens):
        # Step 1 — crop to the last context_size tokens
        idx_cond = idx[:, -context_size:]

        # Step 2 — forward pass, no gradients needed
        with torch.no_grad():
            logits = model(idx_cond)

        # Step 3 — keep only the last position's logits
        logits = logits[:, -1, :]          # (batch, vocab_size)

        # Step 4 — convert to probabilities
        probas = torch.softmax(logits, dim=-1)

        # Step 5 — greedy: pick the single highest-probability token
        idx_next = torch.argmax(probas, dim=-1, keepdim=True)  # (batch, 1)

        # Step 6 — append to the running sequence
        idx = torch.cat((idx, idx_next), dim=1)    # (batch, n_tokens+1)

    return idx
```

**The problem this solves.**

The model's `forward` method takes a sequence of token IDs and returns logits for every position. It does not generate text on its own — it only scores what comes next at each position given what came before. To generate a new token, you feed in the current sequence, read off the logit vector at the last position, pick a token from it, append that token to the sequence, and feed the longer sequence back in. This loop is what `generate_text_simple` implements.

**The shape story — tracing one full iteration.**

Suppose the prompt has been encoded to 4 tokens, `batch=1`, `context_size=1024`, `vocab_size=50257`:

```
idx.shape = (1, 4)    ← (batch, n_tokens) — the growing sequence of token IDs

Step 1 — crop to context window:
  idx_cond = idx[:, -1024:]
  idx_cond.shape = (1, 4)    ← shorter than 1024 so nothing is cropped yet

Step 2 — forward pass:
  logits = model(idx_cond)
  logits.shape = (1, 4, 50257)    ← (batch, n_tokens, vocab_size)
                                     one logit vector per input position

Step 3 — slice last position:
  logits = logits[:, -1, :]
  logits.shape = (1, 50257)    ← (batch, vocab_size)
                                  only position 3's prediction kept
                                  positions 0, 1, 2 discarded

Step 4 — softmax:
  probas = torch.softmax(logits, dim=-1)
  probas.shape = (1, 50257)    ← same shape, values now sum to 1.0 across dim=-1

Step 5 — argmax:
  idx_next = torch.argmax(probas, dim=-1, keepdim=True)
  idx_next.shape = (1, 1)    ← (batch, 1) — one token ID per batch item

Step 6 — append:
  idx = torch.cat((idx, idx_next), dim=1)
  idx.shape = (1, 5)    ← (batch, n_tokens+1) — sequence grew by one token
```

After the first iteration `idx` has shape `(1, 5)`. After the second `(1, 6)`. After `max_new_tokens` iterations `(1, 4 + max_new_tokens)`. The sequence grows by exactly one token per iteration.

**Why only the last position's logits are used.**

The model produces a logit vector at every position. Position 0's logit vector predicts what token should follow the first input token. Position 1's predicts what follows the first two. Position $t$'s predicts what follows all tokens from 0 through $t$. The last position therefore contains the prediction conditioned on the entire current sequence — exactly what is needed. All earlier positions' predictions are already obsolete; the causal mask ensures they could not see the tokens that followed them anyway.

```
logits[:, 0, :] → predicts token 1 given token 0 alone       ← not useful
logits[:, 1, :] → predicts token 2 given tokens 0, 1         ← not useful
logits[:, 2, :] → predicts token 3 given tokens 0, 1, 2      ← not useful
logits[:, 3, :] → predicts token 4 given tokens 0, 1, 2, 3   ← this is what we want
```

Slicing `logits[:, -1, :]` always picks the last position regardless of how long the sequence has grown.

**Why `keepdim=True` on the argmax.**

```
torch.argmax(probas, dim=-1, keepdim=False)  → shape (1,)    ← 1D vector
torch.argmax(probas, dim=-1, keepdim=True)   → shape (1, 1)  ← 2D, batch × 1

idx.shape      = (1, 4)    ← 2D
idx_next.shape = (1, 1)    ← 2D — dim=1 concatenation requires matching ndim

torch.cat((idx, idx_next), dim=1)  → (1, 5)    ← works cleanly
```

Without `keepdim=True`, `idx_next` would be shape `(1,)` — a 1D tensor — and `torch.cat` along `dim=1` would fail with a dimension mismatch error.

**Why context cropping is necessary.**

The positional embedding table has exactly `context_size=1024` rows, covering positions 0 through 1023. If the growing sequence exceeded 1024 tokens and was fed in without cropping, `torch.arange(seq_len)` inside the model's forward pass would produce indices up to 1024 or higher, which are out-of-bounds for the position table. Cropping `idx[:, -context_size:]` keeps only the most recent 1024 tokens, discarding older context but keeping the model within its trained positional range.

**Why softmax before argmax, even though it is redundant.**

`argmax(logits)` and `argmax(softmax(logits))` always return the same index because softmax is a monotone function — it preserves the ordering of values. The explicit softmax here is a teaching choice: the next chapter replaces greedy argmax with sampling from the probability distribution, and sampling genuinely requires probabilities rather than raw logits. Keeping softmax visible now makes that generalisation feel like a natural one-line change rather than a structural revision.

**Why greedy decoding is called greedy and what its weakness is.**

At each step the algorithm commits to the single highest-probability token with no lookahead. This is greedy in the algorithmic sense — locally optimal at every step, but not globally optimal across the whole sequence. The known failure mode is repetition: if token X is the most likely next token given the current context, and appending X makes X the most likely token again, the model loops. More sophisticated decoding strategies — top-k sampling, nucleus sampling, beam search — either sample stochastically from the distribution or maintain multiple candidate sequences in parallel. These arrive in Chapter 5, which is where `generate_text_simple` gets replaced with a more capable version.

## 23 — Section 4.7: Encoding the Prompt

**Summary.** This cell converts the raw string `"Hello, I am"` into the integer tensor the model expects. It is a two-step pipeline: the tokenizer maps the string to a list of token IDs, then `torch.tensor` and `.unsqueeze(0)` wrap that list into a `(1, 4)` batch tensor.

**The code.**

```python
start_context = "Hello, I am"

encoded = tokenizer.encode(start_context)
print("encoded:", encoded)

encoded_tensor = torch.tensor(encoded).unsqueeze(0)
print("encoded_tensor.shape:", encoded_tensor.shape)
# encoded: [15496, 11, 314, 716]
# encoded_tensor.shape: torch.Size([1, 4])
```

**What the tokenizer does to the string.**

`tokenizer.encode("Hello, I am")` runs the GPT-2 BPE vocabulary over the string and returns one integer per subword unit. This prompt happens to split cleanly — one token per visible unit:

```
"Hello, I am"
  ↓     ↓  ↓   ↓
15496  11 314  716

15496  →  "Hello"   — the word itself
   11  →  ","       — the comma as its own token
  314  →  " I"      — leading space kept attached to the word (BPE convention)
  716  →  " am"     — leading space kept attached to the word
```

The leading-space convention is important: BPE does not treat spaces as separate tokens. Instead, the space that precedes a word is merged into that word's token. `" I"` (space + I) and `"I"` (no space) are two different entries in the vocabulary with different IDs. This is why the comma gets its own token `11` — it breaks the space-attachment chain between `"Hello"` and `" I"`.

**The shape transformation from string to model input.**

```
"Hello, I am"                         ← raw Python string

tokenizer.encode("Hello, I am")
= [15496, 11, 314, 716]               ← Python list of ints, no shape

torch.tensor([15496, 11, 314, 716])
shape: (4,)                           ← 1D tensor, no batch dimension

.unsqueeze(0)                         ← inserts a new axis at position 0
shape: (1, 4)                         ← (batch=1, seq_len=4)

encoded_tensor = [
                   [15496, 11, 314, 716]    ← Batch 0: "Hello, I am"
                 ]
```

`.unsqueeze(0)` is the standard way to promote a single example into a batch of one. The model's `forward` method always expects a 2D input of shape `(batch, seq_len)` — it reads `batch_size, seq_len = in_idx.shape` on its first line. Passing a 1D tensor of shape `(4,)` would make that unpacking fail immediately with a "not enough values to unpack" error.

**Gotcha — `.unsqueeze(0)` vs `torch.tensor([encoded])`.**

Both produce the same `(1, 4)` tensor. `.unsqueeze(0)` is the idiomatic choice when you already have a 1D tensor and want to batch it. `torch.tensor([encoded])` wraps the list in an outer list before constructing the tensor, which achieves the same shape but reads less clearly at a glance. Either works; `.unsqueeze(0)` makes the "I am adding a batch dimension" intent explicit.

## 24 — Section 4.7: Running Generation on an Untrained Model

**Summary.** This cell calls `generate_text_simple` on the encoded prompt and checks that the output has the right length. The six generated tokens are gibberish because the model is untrained — every parameter is random initialisation noise — but the generation loop itself is working correctly. Training in Chapter 5 will give the same function meaningful output without changing a single line of generation code.

**The code.**

```python
model.eval()    # disable dropout for deterministic inference

out = generate_text_simple(
    model=model,
    idx=encoded_tensor,
    max_new_tokens=6,
    context_size=GPT_CONFIG_124M["context_length"]   # 1024
)

print("Output:", out)
print("Output length:", len(out[0]))
# Output: tensor([[15496,    11,   314,   716, 16833, 18892, 38734,  2901, 33655, 27608]])
# Output length: 10
```

**What `model.eval()` does and why it matters here.**

PyTorch modules carry an internal `training` flag that is `True` by default. Two module types behave differently depending on this flag: `nn.Dropout` and `nn.BatchNorm`. GPT-2 has no BatchNorm, so the only effect of `.eval()` here is disabling dropout.

During training, `nn.Dropout(0.1)` randomly zeroes 10% of activations on every forward pass. This is intentional — it prevents overfitting by forcing the model to be robust to missing signals. During generation, that same randomness is harmful: it injects noise into every layer, making the output non-deterministic and degrading quality. Calling `.eval()` switches all dropout layers to pass-through mode:

```
training=True  (default):   Dropout zeros 10% of values randomly each call
training=False (.eval()):   Dropout returns input unchanged — no zeroing
```

The complementary call `.train()` switches the flag back when you want to resume training. A common bug is forgetting `.eval()` before evaluation or generation, producing output that varies between runs even with a fixed seed.

**Tracing the six generation iterations.**

Starting from `encoded_tensor` of shape `(1, 4)`:

```
Iteration 1:
  idx.shape = (1, 4)    ← [15496, 11, 314, 716]
  idx_cond  = idx[:, -1024:] → shape (1, 4)     ← shorter than context, unchanged
  logits    = model(idx_cond) → shape (1, 4, 50257)
  logits    = logits[:, -1, :] → shape (1, 50257) ← last position only
  idx_next  → shape (1, 1)    ← one new token ID, e.g. 16833
  idx       = cat → shape (1, 5)    ← [15496, 11, 314, 716, 16833]

Iteration 2:
  idx.shape = (1, 5)
  ...
  idx       = cat → shape (1, 6)

Iteration 3:
  idx.shape = (1, 6)    → (1, 7)

Iteration 4:
  idx.shape = (1, 7)    → (1, 8)

Iteration 5:
  idx.shape = (1, 8)    → (1, 9)

Iteration 6:
  idx.shape = (1, 9)    → (1, 10)

Final idx.shape = (1, 10)    ← 4 prompt tokens + 6 generated tokens
```

`len(out[0])` is 10 because `out[0]` is the first (and only) batch item — a 1D tensor of 10 token IDs. The length check confirms the loop ran exactly 6 times.

**Why the output is gibberish.**

Every weight in the model was randomly initialised — the token embedding rows are random 768-dim vectors, every Linear weight matrix is filled with small random values drawn from a uniform distribution. The forward pass through 12 transformer blocks produces a hidden state that is 12 layers of random matrix multiplications applied to random embeddings. The logit vector at the last position is therefore essentially a random 50,257-dimensional vector, and `argmax` picks whichever vocabulary entry happened to land highest under that random projection.

There is no meaningful signal anywhere in the computation:

```
Random embedding → 12× random attention + random FFN → random logits → random argmax
```

Each of the six generated token IDs is effectively a random draw from the vocabulary, biased only by the random weight initialisation. The specific tokens produced — `16833, 18892, 38734, 2901, 33655, 27608` in the example — have no linguistic relationship to `"Hello, I am"` or to each other.

**What stays the same after training.**

Chapter 5 will update every weight matrix via gradient descent on a large text corpus. After training, the embedding vectors will encode genuine semantic relationships, the attention patterns will reflect real syntactic and semantic dependencies, and the logit vectors will produce sensible next-token predictions. But `generate_text_simple` itself will not change by a single character — the generation loop is already correct. The only difference between generating gibberish now and generating coherent English after training is the values stored in the weight matrices.

## 25 — Section 4.7: Decoding the Output Back to Text

**Summary.** This is the final cell of Chapter 4. It converts the integer tensor produced by `generate_text_simple` back into a readable string. The output is nonsense because the model is untrained, but the round-trip pipeline — text → token IDs → model → token IDs → text — is complete and correct. Chapter 5 will train the weights and bring the same pipeline to life.

**The code.**

```python
decoded_text = tokenizer.decode(out.squeeze(0).tolist())
print(decoded_text)
# Hello, I am Featureiman Byeswickattribute argue
```

**The three-step decode pipeline.**

```
out.shape = (1, 10)    ← (batch=1, seq_len=10) — the full output tensor

Step 1 — out.squeeze(0):
  Removes the batch dimension at position 0.
  (1, 10) → (10,)    ← a 1D tensor of 10 token IDs

Step 2 — .tolist():
  Converts the PyTorch tensor to a plain Python list of integers.
  tensor([15496, 11, 314, 716, 16833, 18892, 38734, 2901, 33655, 27608])
  → [15496, 11, 314, 716, 16833, 18892, 38734, 2901, 33655, 27608]
  tiktoken's decode method expects a Python list, not a tensor.

Step 3 — tokenizer.decode(...):
  Inverse BPE lookup — each integer is replaced by its subword string,
  then all subword strings are concatenated left to right.
  15496 → "Hello"
     11 → ","
    314 → " I"
    716 → " am"
  16833 → " Feature"
  18892 → "iman"
  38734 → " Byes"
   2901 → "wick"
  33655 → "attribute"
  27608 → " argue"
  → "Hello, I am Featureiman Byeswickattribute argue"
```

**Why `.squeeze(0)` and not just indexing with `out[0]`.**

Both `out.squeeze(0)` and `out[0]` produce a 1D tensor of shape `(10,)` from a `(1, 10)` input. `.squeeze(0)` is the idiomatic choice when the batch dimension is known to be 1 and you want to remove it cleanly. `out[0]` works identically here — it is a matter of style.

If `out` had shape `(2, 10)` — a batch of two sentences — `squeeze(0)` would do nothing because the batch dimension is not size 1, while `out[0]` would still extract the first sentence. In generation contexts where `batch=1` is guaranteed, the two are equivalent.

**The full round-trip from text to text.**

```
"Hello, I am"                           ← raw input string
       ↓ tokenizer.encode
[15496, 11, 314, 716]                   ← token IDs, shape (4,)
       ↓ torch.tensor(...).unsqueeze(0)
tensor([[15496, 11, 314, 716]])          ← shape (1, 4)
       ↓ generate_text_simple (6 iterations)
tensor([[15496, 11, 314, 716,
         16833, 18892, 38734,
          2901, 33655, 27608]])          ← shape (1, 10)
       ↓ .squeeze(0).tolist()
[15496, 11, 314, 716, 16833,
 18892, 38734, 2901, 33655, 27608]      ← Python list
       ↓ tokenizer.decode
"Hello, I am Featureiman Byeswickattribute argue"   ← output string
```

Every step in this pipeline has now been built from scratch across the chapter. The tokenizer came from Chapter 2. The model — embeddings, LayerNorm, GELU, FeedForward, TransformerBlock, GPTModel — was assembled across Sections 2 through 17. The generation loop was built in Section 22. This final decode call closes the loop.

**Why the generated text is nonsense but the prompt is preserved correctly.**

The first four tokens `[15496, 11, 314, 716]` decode back to `"Hello, I am"` exactly. They are the original prompt — the model never modified them, the generation loop only appended to `idx`, never overwrote it. The six appended tokens are random argmax selections from an untrained model, so their decoded strings — `"Featureiman"`, `"Byeswick"`, `"attribute argue"` — are vocabulary items that happened to score highest under random weight projections. The subword tokens are real entries in the GPT-2 vocabulary and decode to real character sequences, which is why the output is readable English letters rather than garbage characters — it is just semantically incoherent.

**What changes in Chapter 5.**

The decode call, the generation loop, the tokenizer, and the model architecture all stay exactly as they are. The only thing Chapter 5 changes is the values stored in the weight matrices — by computing a cross-entropy loss against real text and running gradient descent. After sufficient training, the same `tokenizer.decode(generate_text_simple(...).squeeze(0).tolist())` call will produce coherent English continuations of the prompt rather than random vocabulary fragments.

## What You've Built

Chapter 4 started with a `DummyGPTModel` full of identity stubs and ended with a fully wired GPT-2-style architecture that can run a complete text generation loop. Every component was built from scratch and motivated before it was coded.

The construction order mirrors the dependency chain. `LayerNorm` was needed before `TransformerBlock`. `GELU` was needed before `FeedForward`. `FeedForward` and `MultiHeadAttention` (carried over from Chapter 3) were needed before `TransformerBlock`. The vanishing gradient experiment established why residual connections are non-negotiable before they appeared in `TransformerBlock.forward`. `TransformerBlock` was needed before `GPTModel`. And `GPTModel` was needed before `generate_text_simple` had anything to run.

What you have at the end of the notebook:

```
GPTModel
  ├── nn.Embedding          tok_emb     (50257 × 768)
  ├── nn.Embedding          pos_emb     (1024  × 768)
  ├── nn.Dropout            drop_emb
  ├── nn.Sequential         trf_blocks  (× 12)
  │     └── TransformerBlock
  │           ├── MultiHeadAttention    (Chapter 3)
  │           ├── FeedForward
  │           │     └── Linear(768→3072) → GELU → Linear(3072→768)
  │           ├── LayerNorm             norm1
  │           ├── LayerNorm             norm2
  │           └── nn.Dropout            drop_shortcut
  ├── LayerNorm             final_norm
  └── nn.Linear             out_head    (768 → 50257, bias=False)

generate_text_simple
  └── autoregressive loop: crop → forward → slice last → softmax → argmax → append
```

163 million parameters. 621 MB in fp32. A generation loop that runs correctly on random weights and will run identically on trained weights. The architecture is complete — nothing structural changes in any later chapter. Chapter 5 feeds this model real text, computes cross-entropy loss, and runs gradient descent until the weights produce coherent language instead of random vocabulary fragments.
