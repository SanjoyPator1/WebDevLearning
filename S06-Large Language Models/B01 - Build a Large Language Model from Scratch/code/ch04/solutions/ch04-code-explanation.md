# Chapter 4 Code Explanation — Implementing a GPT Model From Scratch

This document walks through every code cell of `ch04.ipynb` from Sebastian Raschka's *Build a Large Language Model From Scratch*. The notebook assembles a full 124M-parameter GPT-2-style model from the ground up: embeddings, layer normalisation, GELU feed-forward networks, residual connections, transformer blocks, and a greedy text-generation loop. Each section below corresponds to one cell (or a tight group of cells) of the notebook and explains the *what*, the *why*, and the *math* behind it.

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

* **`torch`** — the actual neural network engine. Every layer (`nn.Linear`, `nn.Embedding`, `nn.LayerNorm` analogue, `nn.Dropout`) and tensor we touch lives in PyTorch.
* **`tiktoken`** — OpenAI's BPE tokenizer. It is used here in two places: tokenising the two demo sentences in section 3, and decoding the model's generated token IDs back to text at the very end of the notebook.
* **`matplotlib`** — only used once, to draw the GELU vs ReLU comparison plot.

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

| Key | Value | Used by |
|-----|-------|---------|
| `vocab_size` | 50257 | `nn.Embedding(vocab_size, emb_dim)` for token embeddings; `nn.Linear(emb_dim, vocab_size)` for the output head |
| `context_length` | 1024 | `nn.Embedding(context_length, emb_dim)` for positional embeddings; also the size of the causal attention mask |
| `emb_dim` | 768 | The "width" of every hidden state — embedding dim, MHA hidden dim, FFN input/output dim |
| `n_heads` | 12 | Splits `emb_dim` into 12 attention heads, each of width `768 / 12 = 64` |
| `n_layers` | 12 | How many `TransformerBlock`s stacked sequentially |
| `drop_rate` | 0.1 | Dropout on embeddings, attention weights, and after each sublayer |
| `qkv_bias` | False | GPT-2 omitted bias in the Q/K/V linear projections to match the original transformer |

### Where the "124M" comes from

Multiply out the parameter counts and you get **163M** total, not 124M. The 124M figure refers to the count **after weight tying** (sharing the token-embedding matrix with the output head). We'll see this exact arithmetic in section 20.

---

## 2 — Section 4.1: The DummyGPTModel Skeleton

```python
class DummyGPTModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.tok_emb   = nn.Embedding(cfg["vocab_size"],     cfg["emb_dim"])
        self.pos_emb   = nn.Embedding(cfg["context_length"], cfg["emb_dim"])
        self.drop_emb  = nn.Dropout(cfg["drop_rate"])

        self.trf_blocks = nn.Sequential(
            *[DummyTransformerBlock(cfg) for _ in range(cfg["n_layers"])])

        self.final_norm = DummyLayerNorm(cfg["emb_dim"])
        self.out_head   = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, in_idx):
        batch_size, seq_len = in_idx.shape
        tok_embeds = self.tok_emb(in_idx)
        pos_embeds = self.pos_emb(torch.arange(seq_len, device=in_idx.device))
        x = tok_embeds + pos_embeds
        x = self.drop_emb(x)
        x = self.trf_blocks(x)
        x = self.final_norm(x)
        logits = self.out_head(x)
        return logits


class DummyTransformerBlock(nn.Module):
    def forward(self, x):
        return x  # passes input through unchanged

class DummyLayerNorm(nn.Module):
    def __init__(self, normalized_shape, eps=1e-5): super().__init__()
    def forward(self, x):
        return x  # passes input through unchanged
```

### Why a "dummy" model first?

Raschka uses a software pattern called **scaffolding**. The real `TransformerBlock` and `LayerNorm` haven't been built yet — they take the next 50+ cells to develop. But to verify that the *overall skeleton* (embeddings + N blocks + final norm + output head) produces tensors with the right shapes, we need *something* sitting in those slots.

`DummyTransformerBlock` and `DummyLayerNorm` are placeholder modules whose `forward()` returns the input **unchanged**. This lets us:

* Confirm that `in_idx` of shape `(batch=2, seq_len=4)` flows through the model and produces `logits` of shape `(2, 4, 50257)`.
* Catch any obvious wiring mistakes (typo in a dimension, forgotten `super().__init__()`, etc.) before we drop in the real implementations later.

### The two embedding tables

| Embedding | Shape | What it learns |
|-----------|-------|----------------|
| `tok_emb` | `(50257, 768)` | One 768-dim vector per **vocabulary item** — captures the meaning of each token |
| `pos_emb` | `(1024, 768)` | One 768-dim vector per **position** — captures "I am the 0th token", "I am the 1st token", ... up to position 1023 |

The forward pass adds them element-wise: `x = tok_embeds + pos_embeds`. Both have shape `(batch, seq_len, emb_dim)` after the lookup, so the addition is straightforward broadcasting.

### Why `torch.arange(seq_len, device=in_idx.device)` and not a stored buffer?

The positional indices `[0, 1, 2, ..., seq_len-1]` are computed fresh on every forward pass. This is intentional:

1. It supports **variable-length input** — if the batch has 4 tokens, we look up positions 0–3; if it has 1023, we look up 0–1022. A pre-stored buffer would be fixed length.
2. `device=in_idx.device` ensures the position indices live on the same device (CPU or GPU) as the input, avoiding silent device-mismatch errors when you move the model to GPU.

### Why `bias=False` on the output head?

GPT-2 follows the original *Attention Is All You Need* paper, which used `nn.Linear(emb_dim, vocab_size, bias=False)`. The reasoning: each logit is a learned dot product between the final hidden state and a row of the output weight matrix. Adding a per-vocabulary scalar bias would let the model express "always prefer token X regardless of context", which the layer-norm-then-softmax pipeline already handles via the scale/shift parameters and the implicit zero-mean property of normalised activations. In practice the bias term made no measurable difference, so it was dropped to save 50k parameters.

---

## 3 — Section 4.1: Tokenising a Batch of Two Sentences

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
```

Expected output:

```
tensor([[6109, 3626, 6100,  345],
        [6109, 1110, 6622,  257]])
```

This is the exact GPT-2 BPE tokenizer from chapter 2 — `tiktoken.get_encoding("gpt2")` returns the same merges and vocabulary OpenAI used to train GPT-2. Each four-word sentence happens to tokenise to exactly **4 tokens**, which keeps the batch perfectly rectangular without needing to pad.

### Why `torch.stack(..., dim=0)` and not a single `torch.tensor(...)`?

`torch.tensor` of a list of lists works only when the inner lists are the same length **and** PyTorch can infer the dtype. `torch.stack` is more explicit: it takes a list of 1-D tensors and stacks them into a 2-D tensor along a new dimension. The result has shape `(batch=2, seq_len=4)`.

### Looking at the actual token IDs

* `6109` appears in both rows — that's the token for `"Every"` (with the leading space convention BPE uses internally).
* `345 = "you"`, `257 = "a"` — the last token of each sentence.

These integer IDs are what the embedding layer will look up in section 4.

---

## 4 — Section 4.1: Forward Pass Through DummyGPTModel

```python
torch.manual_seed(123)
model = DummyGPTModel(GPT_CONFIG_124M)

logits = model(batch)
print("Output shape:", logits.shape)
print(logits)
```

Expected output:

```
Output shape: torch.Size([2, 4, 50257])
tensor([[[-0.9289,  0.2748, -0.7557,  ...,  ...]]])
```

### Why `torch.manual_seed(123)` matters

`nn.Embedding` and `nn.Linear` initialise their weights randomly. The seed pins the random number generator so that on a fresh interpreter, you get the *exact same* output values printed in the book. Reproducibility makes debugging far easier — if your output diverges from the book's, you know something in *your code* is different, not the random init.

### Reading the output shape

```
(2, 4, 50257)
 ↑  ↑   ↑
 │  │   └─ 50,257 logits per token (one per vocabulary entry)
 │  └───── 4 tokens in the sequence
 └──────── 2 samples in the batch
```

This is the canonical LLM output shape. Every position in every sequence gets a **distribution over the full vocabulary** — the model is computing "given everything I've seen up to position $t$, what's the score for each of the 50,257 possible next tokens?"

### Why one output per input position (not one per sequence)?

This is a property of **autoregressive transformers with causal masking**. Each position attends only to itself and earlier positions, so position $t$'s logits are a function of tokens $[0, t]$. Training exploits this by computing the next-token loss at every position simultaneously — a single forward pass produces $T$ training signals per sequence, not just 1.

At **inference time** (when we generate text in section 22) we only care about the *last* position's logits, since that's what predicts the next token to append. But the model produces all of them either way; it just costs the same matmul.

---

## 5 — Section 4.2: A Tiny Pre-LayerNorm Example

```python
torch.manual_seed(123)

# 2 training examples × 5 features each
batch_example = torch.randn(2, 5)

layer = nn.Sequential(nn.Linear(5, 6), nn.ReLU())
out = layer(batch_example)
print(out)
```

Expected output (mean unnormalised across the 6 features):

```
tensor([[0.2260, 0.3470, 0.0000, 0.2216, 0.0000, 0.0000],
        [0.2133, 0.2394, 0.0000, 0.5198, 0.3297, 0.0000]])
```

### What is this cell actually doing?

We're stepping completely *out* of the GPT model and setting up a toy 5-input, 6-output linear layer followed by ReLU. The goal of section 4.2 is to **derive layer normalisation from scratch** — start with raw network outputs, observe that their means and variances are arbitrary, then build the LayerNorm class step by step to normalise them.

* `torch.randn(2, 5)` — 2 examples, 5 features each, drawn from $\mathcal{N}(0, 1)$.
* `nn.Linear(5, 6)` — maps each 5-dim row to a 6-dim row.
* `nn.ReLU()` — zeros out the negative entries. That's why so many entries in the output are `0.0000`.

### What "training example" means here vs in the GPT model

In the toy example each row is a single training example, so the feature dim is dim 1 (the *last* dim). In the GPT model each `(batch, token)` pair is effectively a training example, and the feature dim is *also* the last dim (`emb_dim`). That's why we'll soon take statistics over `dim=-1` — it works for both cases without changes.

---

## 6 — Section 4.2: Computing Mean and Variance Per Token

```python
mean = out.mean(dim=-1, keepdim=True)
var  = out.var (dim=-1, keepdim=True)

print("Mean:\n", mean)
print("Variance:\n", var)
```

Expected output:

```
Mean:
 tensor([[0.1324],
         [0.2170]])
Variance:
 tensor([[0.0231],
         [0.0398]])
```

### Why `dim=-1` and not `dim=0`?

`dim=-1` says "reduce along the *last* dimension." For a tensor of shape `(2, 5)` that's the feature dimension. We get **one mean per row** (per training example), not one mean per feature. This matches the definition of layer normalisation: normalise across the features of each example independently.

Compare with batch normalisation, which would use `dim=0` (one mean per feature, averaged across the batch).

### Why `keepdim=True`?

It preserves the reduced dimension as size 1 instead of dropping it:

```
out.mean(dim=-1, keepdim=True)  →  shape (2, 1)
out.mean(dim=-1, keepdim=False) →  shape (2,)
```

Keeping it as `(2, 1)` lets us **broadcast** the mean back against the original `(2, 5)` tensor in the next cell:

```
out      shape (2, 5)
mean     shape (2, 1)
out - mean   →  (2, 5)  — broadcasting expands mean to (2, 5)
```

Without `keepdim`, you would need an explicit `mean.unsqueeze(-1)` to reshape it before subtracting.

---

## 7 — Section 4.2: Manual Normalisation by Hand

```python
out_norm = (out - mean) / torch.sqrt(var)
print("Normalized layer outputs:\n", out_norm)

mean = out_norm.mean(dim=-1, keepdim=True)
var  = out_norm.var (dim=-1, keepdim=True)
print("Mean:\n", mean)
print("Variance:\n", var)
```

Expected output:

```
Mean:      tensor([[ 9.9341e-09],
                   [ 0.0000e+00]])
Variance:  tensor([[1.0000],
                   [1.0000]])
```

### The normalisation formula

$$\hat{x}_i = \frac{x_i - \mu}{\sqrt{\sigma^2}}$$

* Subtract the row mean → result has mean 0.
* Divide by the row standard deviation → result has variance 1.

This is exactly the **z-score** transformation from elementary statistics, applied per-row.

### Dry-run on the first row

Take the first training example: `[0.2260, 0.3470, 0.0000, 0.2216, 0.0000, 0.0000]`.

* Mean: $(0.2260 + 0.3470 + 0 + 0.2216 + 0 + 0)/6 = 0.7946 / 6 = 0.1324$ ✓
* Variance (PyTorch's *unbiased* default — divides by $N-1$): we'll cover this in section 8.
* Standard deviation: $\sqrt{0.0231} \approx 0.1520$.
* Subtract mean from first entry: $0.2260 - 0.1324 = 0.0936$.
* Divide by std: $0.0936 / 0.1520 \approx 0.6158$. (This is roughly what the normalised first entry will be — the exact value depends on whether unbiased=True/False.)

### Why the printed mean is `9.9341e-09` and not exactly 0

Floating-point arithmetic is approximate. `(x - mean(x)).mean()` should mathematically equal 0, but the cumulative rounding errors across six float32 operations leave a residual on the order of $10^{-8}$. This is fine — the next cell sets `sci_mode=False` purely so the printed output reads as `0.0000` rather than scientific notation.

```python
torch.set_printoptions(sci_mode=False)
```

This is purely a display setting; it changes nothing about the underlying numbers.

---

## 8 — Section 4.2: The LayerNorm Class

```python
class LayerNorm(nn.Module):
    def __init__(self, emb_dim):
        super().__init__()
        self.eps   = 1e-5
        self.scale = nn.Parameter(torch.ones (emb_dim))
        self.shift = nn.Parameter(torch.zeros(emb_dim))

    def forward(self, x):
        mean = x.mean(dim=-1, keepdim=True)
        var  = x.var (dim=-1, keepdim=True, unbiased=False)
        norm_x = (x - mean) / torch.sqrt(var + self.eps)
        return self.scale * norm_x + self.shift
```

### The full layer-norm formula

$$y_i = \gamma \cdot \frac{x_i - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta$$

Three changes from the manual version in cell 7:

#### 1. `unbiased=False` — biased variance

PyTorch's `.var()` defaults to **unbiased** variance ($\frac{1}{N-1}$ — Bessel's correction). LayerNorm in the original Ba et al. 2016 paper uses the **biased** variance ($\frac{1}{N}$). The difference for $N=768$ features is utterly negligible numerically, but matching the paper exactly is important for compatibility with pre-trained GPT-2 weights (which were trained with the biased version).

#### 2. `+ self.eps` inside the square root — numerical stability

If a token's features happen to all be identical, the variance is 0. Dividing by $\sqrt{0}$ gives infinity, which immediately propagates as `nan` and kills training. Adding $\epsilon = 10^{-5}$ guarantees the denominator is always at least $\sqrt{\epsilon} \approx 0.003$, which avoids the catastrophe at no real cost.

#### 3. Trainable `scale` ($\gamma$) and `shift` ($\beta$)

After dividing by $\sqrt{\text{var}}$, every token's features have mean 0 and variance 1. That's a *very* restrictive output distribution. If the layer that follows would actually benefit from features with mean 5 and variance 4, the model needs a way to undo the normalisation.

That's what `scale` and `shift` do:

* `scale` is initialised to all 1s — initial behaviour: pure normalisation.
* `shift` is initialised to all 0s — no offset.
* Both are `nn.Parameter`, meaning they appear in `model.parameters()` and get updated by the optimiser during training.

The model learns its own optimal per-feature scale and shift. If pure normalisation is best, the gradients drive them to stay near $(1, 0)$. If the next layer prefers a different distribution, they shift accordingly.

### Verifying it works

```python
ln = LayerNorm(emb_dim=6)
out_ln = ln(out)

mean = out_ln.mean(dim=-1, keepdim=True)
var  = out_ln.var (dim=-1, unbiased=False, keepdim=True)
print("Mean:\n", mean)
print("Variance:\n", var)
```

Expected:

```
Mean:      tensor([[    -0.0000],
                   [     0.0000]], grad_fn=<MeanBackward1>)
Variance:  tensor([[0.9999],
                   [0.9999]], grad_fn=<VarBackward0>)
```

Mean 0, variance 0.9999 (not exactly 1.0 because of the `+ eps` we added before the square root). The `grad_fn` attached to the tensors shows the autograd graph is alive — `scale` and `shift` are receiving gradients.

### Where LayerNorm sits in a GPT block

GPT-2 uses **pre-LayerNorm** (LayerNorm applied *before* each sublayer, not after). The sequence inside one transformer block is:

```
x ──► LayerNorm ──► Attention ──► Dropout ──► + ──► next layer
└──────────────────────────────────────────► │
                                              (residual add)
```

This is different from the original transformer paper's "post-LayerNorm" arrangement. Pre-LayerNorm trains much more stably for deep stacks — it's why every modern LLM uses it.

---

## 9 — Section 4.3: The GELU Activation From Scratch

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

### The exact vs approximate GELU

The mathematically-exact GELU is:

$$\text{GELU}(x) = x \cdot \Phi(x)$$

where $\Phi(x)$ is the standard normal CDF. Computing $\Phi(x)$ requires the error function, which is slow on a GPU.

GPT-2 (and Raschka's implementation here) uses the **tanh approximation**:

$$\text{GELU}(x) \approx 0.5 \cdot x \cdot \left(1 + \tanh\!\left[\sqrt{\frac{2}{\pi}} \cdot (x + 0.044715 \cdot x^3)\right]\right)$$

The constants ($\sqrt{2/\pi} \approx 0.7979$, $0.044715$) were fitted by Hendrycks and Gimpel (2016) to match the exact CDF to high precision while using only operations that are cheap on the GPU (multiply, add, tanh).

### Dry-run for $x = 1.0$

* $x^3 = 1.0$
* $x + 0.044715 \cdot x^3 = 1.044715$
* $\sqrt{2/\pi} \cdot 1.044715 \approx 0.7979 \cdot 1.044715 \approx 0.8335$
* $\tanh(0.8335) \approx 0.6826$
* $1 + 0.6826 = 1.6826$
* $0.5 \cdot 1.0 \cdot 1.6826 = 0.8413$

So `GELU(1.0) ≈ 0.8413`. Compare with `ReLU(1.0) = 1.0` — GELU "dampens" positive values slightly.

### Why GELU instead of ReLU?

**Smoothness.** ReLU has a kink at $x = 0$ — its derivative is 1 for $x > 0$, 0 for $x < 0$, and undefined exactly at 0. That kink makes gradients suddenly turn off when a neuron crosses into the negative region (the "dying ReLU" problem).

GELU is smooth everywhere: its derivative transitions gradually from near 0 (large negative inputs) to near 1 (large positive inputs). This gives a softer "gating" effect — small negative inputs get pushed down but not zeroed out — which empirically trains GPT-style models faster and to lower final loss.

### Why no parameters?

`GELU` has no `nn.Parameter` — its behaviour is fixed by those two constants. It is a pure mathematical transformation. We define it as an `nn.Module` only because we want to plug it into an `nn.Sequential` later.

---

## 10 — Section 4.3: GELU vs ReLU — Visual Comparison

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

### What the plot tells you

* **ReLU** — a perfect "kink" at $x = 0$. Flat zero for negatives, identity for positives. The kink is the source of the dying-ReLU problem.
* **GELU** — smooth S-shape through the origin. For large positive $x$ it looks linear, like ReLU. For large negative $x$ it asymptotes to zero gently rather than snapping to it. Around $x = 0$ it dips slightly *below* zero before rising — this is the "soft gating" property: GELU lets small negative values squeak through with a tiny negative contribution.

### Why this matters for transformers specifically

A typical transformer hidden state has ~768 to 12288 features. After the up-projection in the FFN, each feature gets passed through the activation. With ReLU, **half** of those features get zeroed out on any given token. The hard zeroing means later layers cannot distinguish between "this feature was slightly negative" and "this feature was very negative" — the information is gone.

GELU preserves a small signal in the negative region, giving the model more representational capacity to use. The performance improvement is modest (~1% perplexity) but it shows up reliably in pre-training runs.

---

## 11 — Section 4.3: The FeedForward Class

```python
class FeedForward(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(cfg["emb_dim"], 4 * cfg["emb_dim"]),
            GELU(),
            nn.Linear(4 * cfg["emb_dim"], cfg["emb_dim"]),
        )

    def forward(self, x):
        return self.layers(x)
```

### The expand-and-contract pattern

Every transformer FFN follows the same shape pattern:

```
emb_dim ──► 4·emb_dim ──► GELU ──► emb_dim
   768   ►    3072    ►        ►    768
```

The first linear layer **expands** the hidden dimension by a factor of 4 (768 → 3072). The activation is applied in the expanded space. The second linear layer **contracts** back to the original dimension.

### Why expand by 4×?

The expansion provides extra capacity for the non-linear transformation to "spread out" the input. With more dimensions in the middle, the model can represent richer combinations of features before projecting back down. The factor of 4 isn't sacred — it's an empirical sweet spot that the original transformer paper landed on. Some modern models use 8/3 or different ratios, but 4× remains the default for GPT-style architectures.

### Where the FFN parameters come from

* First Linear: $768 \times 3072 + 3072 = 2{,}362{,}368$ weights + biases
* Second Linear: $3072 \times 768 + 768 = 2{,}360{,}064$ weights + biases
* Total per FFN: $\approx 4.7$ million parameters

With 12 transformer blocks, the FFN parameters alone are roughly $4.7\text{M} \times 12 \approx 56$ million — about **two thirds** of the entire 124M model. The FFN, not attention, is where the bulk of GPT-2's capacity lives.

### Position-wise — what this means

Each token's vector passes through the FFN **independently**. There is no cross-token interaction inside the FFN — that already happened in the attention sublayer. You can think of the FFN as "each token re-reads its own features, mixes them non-linearly, and rewrites them."

### Running the FFN

```python
ffn = FeedForward(GPT_CONFIG_124M)

# input shape: (batch, num_tokens, emb_dim)
x = torch.rand(2, 3, 768)
out = ffn(x)
print(out.shape)
# torch.Size([2, 3, 768])
```

Input and output shapes match. The FFN is **shape-preserving** — that's a requirement for it to fit inside a residual block where the input gets added back to the output.

---

## 12 — Section 4.4: ExampleDeepNeuralNetwork and print_gradients

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

### What this demo is illustrating

Before plugging the real transformer block together, Raschka wants to make sure you *deeply understand* one concept: **deep networks without residual (shortcut) connections suffer from vanishing gradients**. This is a self-contained toy experiment that does nothing GPT-related — it just stacks 5 linear layers and observes what happens to the gradients during backpropagation.

### The architecture

`layer_sizes = [3, 3, 3, 3, 3, 1]` — 5 layers, the first four are Linear(3→3) + GELU, the last is Linear(3→1) + GELU. With `use_shortcut=True`, the input to each layer is added back to its output (provided the shapes match).

### The `use_shortcut and x.shape == layer_output.shape` guard

A residual connection only works if the input and output of the layer have the same shape. The first 4 layers are Linear(3→3) so shapes match. The 5th layer is Linear(3→1) — the shapes do *not* match, so the residual is skipped for that layer. This mirrors how real transformer blocks handle the issue: every sublayer is designed to preserve the embedding dimension, so the residuals always work.

### What `print_gradients` does

1. Forward pass on the model with input `x`.
2. Define a fake target of 0.
3. Compute MSE loss.
4. `loss.backward()` — populates `.grad` on every parameter.
5. For every weight matrix (skipping biases), print the mean of its **absolute** gradient.

The mean-absolute gradient is a rough proxy for "how strong is the learning signal reaching this layer?" A vanishing gradient shows up as numbers like $10^{-5}$ — that layer is effectively dead and can't learn.

---

## 13 — Section 4.4: Gradients Without Shortcuts — The Vanishing Problem

```python
layer_sizes = [3, 3, 3, 3, 3, 1]
sample_input = torch.tensor([[1., 0., -1.]])

torch.manual_seed(123)
model_without_shortcut = ExampleDeepNeuralNetwork(layer_sizes, use_shortcut=False)
print_gradients(model_without_shortcut, sample_input)
```

Expected output:

```
layers.0.0.weight has gradient mean of 0.00020...
layers.1.0.weight has gradient mean of 0.00012...
layers.2.0.weight has gradient mean of 0.00072...
layers.3.0.weight has gradient mean of 0.00139...
layers.4.0.weight has gradient mean of 0.00504...
```

### Reading the output

Look at the gradients from **layer 0 (deepest from the output, closest to input)** to **layer 4 (closest to the output)**:

```
Layer 0:  ~0.00020
Layer 1:  ~0.00012
Layer 2:  ~0.00072
Layer 3:  ~0.00139
Layer 4:  ~0.00504
```

The gradient for layer 0 is roughly **25× smaller** than for layer 4. This is the **vanishing gradient problem** in miniature. The gradient signal has to flow backward through 5 layers of multiplications-and-activations, and each layer multiplies the gradient by its local derivative. If those derivatives are below 1 (which they are most of the time for GELU on typical inputs), the gradient shrinks exponentially.

### Why this would break training

The optimizer's step size for layer 0 is proportional to its gradient. With a gradient 25× smaller than layer 4's, layer 0 effectively never updates. After many training steps, layer 4 has learned a lot; layer 0 is still nearly at its random initialisation. The model can't get the front layers to learn useful features, so the whole stack underperforms.

In a real GPT-2 with 12 layers, vanishing gets dramatically worse — gradients can drop by $1000\times$ across the depth.

---

## 14 — Section 4.4: Gradients With Shortcuts — The Fix

```python
torch.manual_seed(123)
model_with_shortcut = ExampleDeepNeuralNetwork(layer_sizes, use_shortcut=True)
print_gradients(model_with_shortcut, sample_input)
```

Expected output:

```
layers.0.0.weight has gradient mean of 0.2217...
layers.1.0.weight has gradient mean of 0.2068...
layers.2.0.weight has gradient mean of 0.3289...
layers.3.0.weight has gradient mean of 0.2666...
layers.4.0.weight has gradient mean of 1.3258...
```

### The transformation

Compare layer 0:
* Without shortcuts: $0.00020$
* With shortcuts:    $0.22$

That's a **1000× larger** gradient for the earliest layer. The shortcut connections give the gradient a "highway" to flow backward without being repeatedly squashed by every layer's local derivative.

### The math behind why shortcuts fix this

A residual block computes:

$$y = x + f(x)$$

where $f$ is the layer's transformation. During backward pass, the gradient of $y$ with respect to $x$ is:

$$\frac{\partial y}{\partial x} = 1 + \frac{\partial f(x)}{\partial x}$$

The crucial term is the **`+ 1`**. Even if the layer's local derivative $\partial f / \partial x$ goes to 0, the gradient still flows backward through the `+ 1` term unchanged. There is always a path from the loss back to every earlier layer that doesn't get squashed.

### Why this is the single most important architectural innovation in modern deep learning

Without residual connections, you cannot train networks deeper than maybe 10 layers reliably. With residual connections, networks of 100+ layers (ResNet-101, ResNet-152) and even 1000+ layers train fine. Every transformer block in GPT, Llama, Claude, and Gemini contains residuals around both the attention sublayer and the FFN sublayer — they are non-negotiable.

---

## 15 — Section 4.5: The TransformerBlock

```python
from previous_chapters import MultiHeadAttention

class TransformerBlock(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.att = MultiHeadAttention(
            d_in=cfg["emb_dim"],
            d_out=cfg["emb_dim"],
            context_length=cfg["context_length"],
            num_heads=cfg["n_heads"],
            dropout=cfg["drop_rate"],
            qkv_bias=cfg["qkv_bias"])
        self.ff             = FeedForward(cfg)
        self.norm1          = LayerNorm(cfg["emb_dim"])
        self.norm2          = LayerNorm(cfg["emb_dim"])
        self.drop_shortcut  = nn.Dropout(cfg["drop_rate"])

    def forward(self, x):
        # Sub-block 1: pre-LN attention + residual
        shortcut = x
        x = self.norm1(x)
        x = self.att(x)
        x = self.drop_shortcut(x)
        x = x + shortcut

        # Sub-block 2: pre-LN FFN + residual
        shortcut = x
        x = self.norm2(x)
        x = self.ff(x)
        x = self.drop_shortcut(x)
        x = x + shortcut

        return x
```

### The "pre-LN" pattern in detail

Look carefully at the forward pass. The pattern for each sub-block is:

```
shortcut = x                  # save the original input
x = norm(x)                   # normalise BEFORE the sublayer
x = sublayer(x)               # attention or FFN
x = dropout(x)
x = x + shortcut              # residual add with the ORIGINAL (un-normalised) x
```

The residual is added with the **original** `x`, not the normalised one. This is critical — it means that the un-modified hidden state always survives across the entire stack of 12 blocks. Each block contributes an additive update on top of it. The whole stack computes:

$$h_L = h_0 + \sum_{i=1}^{L} \text{block}_i(h_{i-1})$$

This **additive composition** is what gives modern transformers their stable training behaviour.

### Pre-LN vs post-LN

The original "Attention Is All You Need" paper used **post-LN**:

```
shortcut = x
x = sublayer(x)
x = dropout(x)
x = norm(x + shortcut)
```

The normalisation goes *after* the residual add. This trains poorly for deep stacks because the gradient through the residual passes through a LayerNorm which has its own normalisation effect.

**Pre-LN** (used here, used by GPT-2, Llama, all modern models) moves the LayerNorm *before* the sublayer and *outside* the residual add. The gradient now has a clean path back through the residual without any normalisation step interfering. This was discovered around 2019–2020 and is now universal.

### Why two separate LayerNorms (`norm1` and `norm2`)?

Each sublayer (attention, FFN) gets its own LayerNorm with its own `scale` and `shift` parameters. They are not shared because the input distribution to attention and the input distribution to FFN are different — they need different normalisation parameters.

Per block, this adds $2 \times 2 \times 768 = 3072$ parameters (two LayerNorms, each with a 768-dim scale and a 768-dim shift). Across 12 blocks: $\approx 37{,}000$. The 768-dim final LN before the output head adds another $1536$. LayerNorm parameters are a tiny fraction of the model.

### Why `drop_shortcut` (not `drop_after_sublayer` and `drop_before_residual`)?

A single dropout module is reused after both the attention and the FFN output. Same dropout rate (`drop_rate = 0.1` from the config), same regularisation effect. Reusing one module is purely a code-organisation choice — PyTorch dropout has no internal state to share or worry about.

### What the MultiHeadAttention does (1-paragraph refresher)

From chapter 3: `MultiHeadAttention` takes input of shape `(batch, seq_len, emb_dim)`, splits the embedding dim into `n_heads` equal chunks (each of size `emb_dim / n_heads = 64`), computes scaled dot-product attention with a causal mask within each head, concatenates the heads back together, and returns output of the same shape. The `qkv_bias=False` matches GPT-2's choice to drop biases on the Q/K/V projections.

---

## 16 — Section 4.5: Running the TransformerBlock

```python
torch.manual_seed(123)

x = torch.rand(2, 4, 768)  # (batch, num_tokens, emb_dim)
block = TransformerBlock(GPT_CONFIG_124M)
output = block(x)

print("Input shape:",  x.shape)
print("Output shape:", output.shape)
```

Expected:

```
Input shape:  torch.Size([2, 4, 768])
Output shape: torch.Size([2, 4, 768])
```

### Shape-preservation is the whole point

A transformer block takes `(batch, seq, emb_dim)` in and returns `(batch, seq, emb_dim)` out. This shape invariance is what allows us to stack 12 of them in `nn.Sequential` without any reshaping between blocks — output of block 1 plugs directly into input of block 2, and so on.

If you ever introduce a bug where the output shape doesn't match the input, the residual connection inside the *next* block will explode with a shape-mismatch error, which is your signal that something inside the block isn't shape-preserving.

### What just happened mathematically

Inside the block, the 4 tokens at positions 0, 1, 2, 3 each computed attention over each other (with the causal mask), updated their hidden states, then passed through the FFN. The output is still 4 tokens × 768 features per token — but each token's features now encode information from the other tokens it could see (plus a non-linear transformation).

---

## 17 — Section 4.6: The Full GPTModel Class

```python
class GPTModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.tok_emb    = nn.Embedding(cfg["vocab_size"],     cfg["emb_dim"])
        self.pos_emb    = nn.Embedding(cfg["context_length"], cfg["emb_dim"])
        self.drop_emb   = nn.Dropout(cfg["drop_rate"])

        self.trf_blocks = nn.Sequential(
            *[TransformerBlock(cfg) for _ in range(cfg["n_layers"])])

        self.final_norm = LayerNorm(cfg["emb_dim"])
        self.out_head   = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, in_idx):
        batch_size, seq_len = in_idx.shape
        tok_embeds = self.tok_emb(in_idx)
        pos_embeds = self.pos_emb(torch.arange(seq_len, device=in_idx.device))
        x = tok_embeds + pos_embeds
        x = self.drop_emb(x)
        x = self.trf_blocks(x)
        x = self.final_norm(x)
        logits = self.out_head(x)
        return logits
```

### Comparing to DummyGPTModel

Structurally identical to section 2. The only differences:

* `DummyTransformerBlock` → real `TransformerBlock` (from section 15)
* `DummyLayerNorm` → real `LayerNorm` (from section 8)

That's it. All the scaffolding from `DummyGPTModel` (the embeddings, the dropout, the `nn.Sequential` stack, the final LN + output head) is unchanged. This is the payoff of using dummies: once the real classes are ready, you swap them in and the whole model just works.

### The complete forward-pass tour

For input `in_idx` of shape `(batch=2, seq_len=4)`:

| Step | Operation | Output shape |
|------|-----------|--------------|
| 0 | Input token ids | `(2, 4)` |
| 1 | `tok_emb(in_idx)` | `(2, 4, 768)` |
| 2 | `pos_emb(arange(4))` | `(4, 768)` — broadcasts to `(2, 4, 768)` during add |
| 3 | `tok_embeds + pos_embeds` | `(2, 4, 768)` |
| 4 | `drop_emb` | `(2, 4, 768)` |
| 5 | 12 × `TransformerBlock` | `(2, 4, 768)` (shape-preserving) |
| 6 | `final_norm` | `(2, 4, 768)` |
| 7 | `out_head` (Linear 768→50257) | `(2, 4, 50257)` |

The shape only changes at step 1 (lookup), step 5 (no change but heavy computation happens here), and step 7 (final projection to vocabulary scores).

### Why a final LayerNorm right before the output head?

The output of the last transformer block has been through 12 residual additions. Without a final normalisation, its scale could drift over training (the cumulative effect of 12 residual sums). The `final_norm` ensures the input to the output head is always centred and unit-variance — which keeps the logits in a sensible range and stabilises training.

---

## 18 — Section 4.6: Running the Real Model on the Batch

```python
torch.manual_seed(123)
model = GPTModel(GPT_CONFIG_124M)

out = model(batch)
print("Input batch:\n", batch)
print("\nOutput shape:", out.shape)
print(out)
```

Expected output shape: `(2, 4, 50257)` — identical to the DummyGPTModel run in section 4.

### Why is the output shape the same as the Dummy run?

Because the model is **untrained**. We have just instantiated all the parameters with their random initial values; no gradient steps have been taken. The logits are essentially noise — but they have the right *shape*. Training in chapter 5 will give the model meaningful logits; here we are just verifying the wiring.

### Will the actual logit *values* match those from the Dummy run?

No. The dummy blocks were identity functions, so the logits then were the output of `out_head(drop_emb(tok_embeds + pos_embeds))` directly. The real model passes the embeddings through 12 transformer blocks that mix, attend, and re-project everything before the final head sees the hidden state. The numerical values are completely different — but the *shape* of the output is what the API contract guarantees, and that hasn't changed.

---

## 19 — Section 4.6: Counting the Parameters

```python
total_params = sum(p.numel() for p in model.parameters())
print(f"Total number of parameters: {total_params:,}")
```

Expected output:

```
Total number of parameters: 163,009,536
```

### Where do 163 million parameters come from?

Let's count them roughly:

* **Token embedding:** `vocab_size × emb_dim = 50257 × 768 = 38{,}597{,}376`
* **Position embedding:** `context_length × emb_dim = 1024 × 768 = 786{,}432`
* **Per transformer block (×12):**
  * Attention: 4 linear layers of `768 × 768` each (Q, K, V, output projection) = $4 \times 589{,}824 = 2{,}359{,}296$
  * FFN: Linear(768, 3072) + Linear(3072, 768) = $768 \cdot 3072 + 3072 + 3072 \cdot 768 + 768 \approx 4{,}722{,}432$
  * LayerNorms: $2 \times (768 + 768) = 3072$
  * Total per block: $\approx 7{,}084{,}800$
* **All 12 blocks:** $\approx 85{,}017{,}600$
* **Final LN:** $1{,}536$
* **Output head:** `emb_dim × vocab_size = 768 × 50257 = 38{,}597{,}376`

Sum: $\approx 38.6M + 0.8M + 85.0M + 0.0M + 38.6M \approx 163M$ ✓

### What this number tells you

* **Memory at inference (fp32):** $163M \times 4 \text{ bytes} \approx 650$ MB.
* **Memory at inference (bf16):** $\approx 325$ MB.
* **Memory at training (fp32 with Adam):** roughly **4×** the model size because Adam keeps two extra buffers per parameter (momentum and variance) plus gradients — so $\approx 2.5$ GB just for the optimiser state.

These numbers explain why fine-tuning even a "small" 124M model requires at least a few GB of GPU RAM, and why bigger models (Llama-7B = 7 billion params) need either heavy compression (4-bit QLoRA) or many GPUs.

---

## 20 — Section 4.6: Weight Tying and the 124M Number

```python
print("Token embedding layer shape:", model.tok_emb.weight.shape)
print("Output layer shape:",          model.out_head.weight.shape)
```

Expected:

```
Token embedding layer shape: torch.Size([50257, 768])
Output layer shape:          torch.Size([50257, 768])
```

The token-embedding matrix and the output-head weight matrix are **the same shape**: $50257 \times 768$. This is not a coincidence — they represent fundamentally the same mapping in opposite directions:

* Token embedding: token id → 768-dim vector (lookup)
* Output head: 768-dim hidden state → 50257-dim logits (dot product against vocabulary directions)

### Weight tying

The original GPT-2 paper noticed this duality and decided to **share the same weight matrix** between the two. This is called **weight tying**:

```python
# (Conceptually — not implemented in this notebook)
model.out_head.weight = model.tok_emb.weight
```

### How weight tying produces the 124M figure

```python
total_params_gpt2 = total_params - sum(p.numel() for p in model.out_head.parameters())
print(f"Number of trainable parameters considering weight tying: {total_params_gpt2:,}")
```

Expected:

```
Number of trainable parameters considering weight tying: 124,412,160
```

If we subtract the entire output head's parameters ($38{,}597{,}376$) from the 163M total, we get $124{,}412{,}160$ — the famous **"124M" GPT-2 Small** parameter count. The output head's parameters effectively don't count separately because they share storage with the token embedding.

### Why doesn't Raschka implement weight tying here?

Per the notebook commentary: training is empirically easier *without* weight tying. The tied weights have to serve two purposes (lookup and projection), and gradients from both sides compete during training. Untied weights converge faster and more stably in the from-scratch training run that happens in chapter 5.

Weight tying *will* come back when we load OpenAI's pre-trained GPT-2 weights in a later chapter, because OpenAI's released checkpoints use tied weights — we'll have to copy the embedding into the output head explicitly.

---

## 21 — Section 4.6: Model Size in Megabytes

```python
total_size_bytes = total_params * 4    # fp32: 4 bytes per parameter
total_size_mb    = total_size_bytes / (1024 * 1024)
print(f"Total size of the model: {total_size_mb:.2f} MB")
```

Expected: `Total size of the model: 621.83 MB`.

### Reading the number

163M parameters × 4 bytes (float32) = ~622 MB. In **bfloat16** (used by every modern training pipeline), this halves to ~311 MB. In **4-bit NF4** (used by QLoRA), it drops further to about 78 MB.

### Why this matters

When you save a model with `torch.save` or `model.save_pretrained`, the file size on disk roughly matches this number (a little extra for metadata). When you load the model into GPU RAM, you need at least this much VRAM **plus** room for the activations (intermediate tensors during forward/backward), which can be several times the model size at typical batch sizes.

For training, the practical rule of thumb is **VRAM ≈ 4× model size** (model + gradients + Adam's two momentum buffers, all in the same dtype). For inference, **VRAM ≈ 1.2× model size** (model + activations). This is why a 622 MB model that fits comfortably for inference on a 2 GB GPU may not fit for training on the same GPU.

---

## 22 — Section 4.7: generate_text_simple — Greedy Decoding

```python
def generate_text_simple(model, idx, max_new_tokens, context_size):
    # idx is (batch, n_tokens) array of indices in the current context
    for _ in range(max_new_tokens):
        # 1. Crop current context to the last context_size tokens
        idx_cond = idx[:, -context_size:]

        # 2. Get the predictions (no gradients needed for inference)
        with torch.no_grad():
            logits = model(idx_cond)

        # 3. Focus only on the last time step
        # (batch, n_tokens, vocab_size) → (batch, vocab_size)
        logits = logits[:, -1, :]

        # 4. Apply softmax to get probabilities
        probas = torch.softmax(logits, dim=-1)

        # 5. Greedy: pick the highest-probability token
        idx_next = torch.argmax(probas, dim=-1, keepdim=True)  # (batch, 1)

        # 6. Append the new token to the running sequence
        idx = torch.cat((idx, idx_next), dim=1)  # (batch, n_tokens+1)

    return idx
```

This is one of the most important functions in the book — it's the **autoregressive generation loop** that turns the static model into a text generator.

### The six steps of one generation iteration

| Step | What it does | Why |
|------|--------------|-----|
| 1 | `idx[:, -context_size:]` | Crop to the last 1024 tokens — model can't attend further back |
| 2 | `model(idx_cond)` | One forward pass, no autograd needed (saves memory) |
| 3 | `logits[:, -1, :]` | Discard logits for all but the *last* position — that's the one predicting the next token |
| 4 | `softmax` | Convert logits to a probability distribution |
| 5 | `argmax` | Pick the single most likely token (greedy) |
| 6 | `torch.cat` | Append the chosen token to the running sequence |

### Why crop the context?

The model's positional embedding only knows positions 0 through `context_length - 1 = 1023`. If we tried to feed it 1500 tokens, the positional lookup for position 1024+ would fail (out-of-bounds). Cropping to the most recent 1024 tokens preserves the model's local memory while staying within its trained context window.

### Why `torch.no_grad()`?

Two reasons:
1. **Memory** — autograd stores every intermediate activation for the backward pass. Disabling it lets PyTorch discard intermediates immediately, drastically cutting VRAM during generation.
2. **Speed** — no graph bookkeeping, so each forward pass is a little faster.

### Why softmax → argmax and not just argmax on the logits?

Mathematically equivalent. `argmax(logits)` gives the same index as `argmax(softmax(logits))` because softmax is monotonic. The notebook applies softmax explicitly because it's a teaching moment — once you understand greedy decoding, the next chapter generalises to **sampling from the softmax distribution** (which actually needs the probabilities, not just the argmax).

### Why this is called *greedy* decoding

At each step it makes the locally optimal choice — pick the single highest-probability token, period. This is greedy in the algorithmic sense.

Greedy decoding has a known weakness: it can get stuck in repetitive loops because if the highest-probability token at step $t$ leads to a context where the same token is again the highest-probability at step $t+1$, you loop forever. More sophisticated decoders (beam search, top-k sampling, nucleus sampling) explore multiple options and break ties stochastically — those come in chapter 5.

### Why `keepdim=True` on the `argmax`?

`argmax` over a `(batch, vocab)` tensor with `dim=-1` and `keepdim=False` would return shape `(batch,)`. We need `(batch, 1)` so that `torch.cat((idx, idx_next), dim=1)` can append along dim 1 without a shape mismatch.

---

## 23 — Section 4.7: Encoding the Prompt

```python
start_context = "Hello, I am"

encoded = tokenizer.encode(start_context)
print("encoded:", encoded)

encoded_tensor = torch.tensor(encoded).unsqueeze(0)
print("encoded_tensor.shape:", encoded_tensor.shape)
```

Expected output:

```
encoded: [15496, 11, 314, 716]
encoded_tensor.shape: torch.Size([1, 4])
```

### What the four token IDs are

* `15496` — `"Hello"`
* `11` — `","` (just the comma)
* `314` — `" I"` (with the leading space — BPE keeps the space attached to the next word)
* `716` — `" am"`

Four tokens for four words is unusually clean — many English words tokenise into multiple BPE pieces, but this happens to be a vocabulary-friendly prompt.

### Why `.unsqueeze(0)`?

`tokenizer.encode` returns a list of ints. `torch.tensor(list)` gives a 1-D tensor of shape `(4,)`. The model expects `(batch, seq_len)` — even a batch of one. `.unsqueeze(0)` adds a new dimension at position 0, turning `(4,)` into `(1, 4)`.

---

## 24 — Section 4.7: Running Generation on an Untrained Model

```python
model.eval()  # disable dropout

out = generate_text_simple(
    model=model,
    idx=encoded_tensor,
    max_new_tokens=6,
    context_size=GPT_CONFIG_124M["context_length"]
)

print("Output:", out)
print("Output length:", len(out[0]))
```

Expected:

```
Output: tensor([[15496,    11,   314,   716,  ...,  ...,  ...,  ...,  ...,  ...]])
Output length: 10
```

(The exact six generated tokens depend on the random initialisation — without training they are essentially random argmax choices.)

### Why `model.eval()`?

PyTorch modules have a `training` flag. When `training=True` (default), `nn.Dropout` randomly zeros some activations and `nn.BatchNorm` uses batch statistics. When `training=False` (set by `.eval()`), dropout becomes a no-op and BatchNorm uses its running statistics.

GPT-2 has no BatchNorm, so the only effect here is **disabling dropout**. During generation we want deterministic, sensible outputs — random dropout would inject noise into every layer and make the output worse and harder to reproduce.

### Output length check

Input was 4 tokens. We asked for 6 new tokens. Output is `4 + 6 = 10` tokens. The generation loop ran exactly 6 iterations, each appending one new token.

### Why the generated text will be gibberish

The model is **untrained**. Every parameter was just randomly initialised — `tok_emb.weight ~ N(0, 1)`, every Linear weight similarly random. The logits the model produces at the last position have no meaningful structure; argmax over them picks essentially a random token. After 6 such picks we have 6 random tokens.

Training (chapter 5) will give the model meaningful representations, and at that point the same `generate_text_simple` function will start producing coherent English.

---

## 25 — Section 4.7: Decoding the Output Back to Text

```python
decoded_text = tokenizer.decode(out.squeeze(0).tolist())
print(decoded_text)
```

Expected output (will differ from this exact string due to the untrained random model, but the shape of the result is identical):

```
Hello, I am Featureiman Byeswickattribute argue
```

### What's happening

1. `out` has shape `(1, 10)`. `.squeeze(0)` removes the batch dimension → shape `(10,)`.
2. `.tolist()` converts the tensor to a Python list of ints: `[15496, 11, 314, 716, <gen1>, <gen2>, ...]`.
3. `tokenizer.decode(...)` runs the **inverse BPE** — concatenates the byte-pair strings for each token id, restoring spaces and casing.

### Why the generated text reads as nonsense

This is the punchline of chapter 4: the model is built correctly (right shapes, right number of parameters, working generation loop), but it has not yet been trained. It can only output statistically random sequences. The original four tokens come through cleanly because they were the prompt; the six generated tokens are whatever the random initial weights happened to argmax.

Chapter 5 will train the model on real text and bring this loop to life — given `"Hello, I am"`, it should start producing reasonable English continuations.

---

## What You've Built

By the end of `ch04.ipynb` you have a fully wired GPT-2-style model:

* Token + positional embeddings
* 12 transformer blocks, each with pre-LN multi-head attention, pre-LN GELU FFN, and residual connections around each sublayer
* Final LayerNorm and untied output head
* A greedy autoregressive generation loop

That is **the entire GPT architecture**. Everything you'll do in later chapters (training in chapter 5, fine-tuning for classification in chapter 6, instruction-tuning in chapter 7) reuses this same `GPTModel` class without modification. The next step is to give it real weights — either by training on raw text (chapter 5) or by loading OpenAI's released checkpoint (also chapter 5).
