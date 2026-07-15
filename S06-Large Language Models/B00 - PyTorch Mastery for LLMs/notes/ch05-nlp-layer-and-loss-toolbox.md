# Chapter 5: NLP Layer & Loss Toolbox

## Table of Contents

1. [The Layers Every NLP Model Is Made Of](#1-the-layers-every-nlp-model-is-made-of)
2. [nn.Embedding: A Lookup Table with Gradients](#2-nnembedding-a-lookup-table-with-gradients)
3. [Normalization: LayerNorm vs BatchNorm (vs RMSNorm)](#3-normalization-layernorm-vs-batchnorm-vs-rmsnorm)
4. [Dropout and the train/eval Switch](#4-dropout-and-the-traineval-switch)
5. [Activations: ReLU vs GELU vs SiLU](#5-activations-relu-vs-gelu-vs-silu)
6. [The Loss Family: CrossEntropy and Its Relatives](#6-the-loss-family-crossentropy-and-its-relatives)
7. [Putting It Together: Padding-Aware Sequence Loss](#7-putting-it-together-padding-aware-sequence-loss)
8. [Key Takeaways + Master Decision Table](#8-key-takeaways--master-decision-table)

---

# 1: The Layers Every NLP Model Is Made Of

## What This Chapter Is Really About

Strip the attention mechanism out of a transformer and what's left is a
small, fixed cast: an **embedding** turning token IDs into vectors, **norm
layers** keeping activations tame, **activations** adding nonlinearity,
**dropout** fighting overfitting, and a **loss function** turning logits into
a training signal. Five kinds of layer, each with one or two look-alikes that
are wrong for NLP in specific, diagnosable ways.

This chapter gives each one the full treatment: what it computes (with the
arithmetic done by hand), what its knobs do, which look-alike to avoid, and a
decision guide. By the end, a line like
`nn.LayerNorm(d_model)` or `F.cross_entropy(logits, targets, ignore_index=-100)`
should read like prose — every argument a deliberate choice.

---

# 2: nn.Embedding: A Lookup Table with Gradients

## The Intuition

`nn.Embedding(vocab_size, embed_dim)` is a **matrix of shape
`(vocab_size, embed_dim)` where row $i$ is token $i$'s vector**. The forward
pass is nothing but row selection — no multiplication, no bias. That's why
it demands integer (`int64`) inputs: you cannot look up row 2.7.

Mathematically it is *equivalent* to one-hot encoding followed by a matrix
multiply — a fact worth proving once (exercise 1) because it explains why
embeddings are learnable like any Linear:

$$\text{Embedding}(i) = \text{onehot}(i) \cdot E, \qquad E \in \mathbb{R}^{V \times d}$$

Every symbol: $V$ is the vocabulary size, $d$ the embedding dimension, $E$
the weight matrix, and $\text{onehot}(i)$ a length-$V$ vector with a single
1 at position $i$. Multiplying by a one-hot just *selects a row* — the
lookup is the multiplication, done infinitely cheaper.

## Dry-Run with Tiny Numbers

```
V = 4 tokens, d = 2 dims

E = [[0.1, 0.2],      ← row 0: token 0's vector
     [0.3, 0.4],      ← row 1
     [0.5, 0.6],      ← row 2
     [0.7, 0.8]]      ← row 3

token_ids = [2, 0]
Embedding(token_ids) = [[0.5, 0.6],     just row 2
                        [0.1, 0.2]]     just row 0

The one-hot view of the same lookup for token 2:
  [0, 0, 1, 0] @ E = 0·row0 + 0·row1 + 1·row2 + 0·row3 = [0.5, 0.6] ✓
```

## The Two Knobs That Matter

**`padding_idx=PAD_ID`** does two things: row `PAD_ID` is initialized to
zeros, and — more importantly — **its gradient is always zero**, so no
matter how often pad tokens appear, their "vector" never trains away from
whatever it holds. Padding stays semantically inert.

**`nn.Embedding.from_pretrained(matrix, freeze=True)`** builds the layer
from an existing matrix (word2vec-style vectors, or weights from another
model). `freeze=True` is `requires_grad_(False)` applied for you — chapter
4's freezing, one keyword away.

## Key Takeaways for Section 2

Embedding = learnable row lookup = one-hot @ matrix, minus the waste. Inputs
must be `int64`. `padding_idx` keeps the pad row zero-gradient forever;
`from_pretrained(..., freeze=...)` imports and optionally freezes.

*Next: keeping the numbers flowing through those vectors well-behaved.*

---

# 3: Normalization: LayerNorm vs BatchNorm (vs RMSNorm)

## The Problem It Solves

Deep stacks drift: each layer's output distribution shifts as the layers
below it train, so every layer chases a moving target and learning slows.
Normalization re-centers and re-scales activations at fixed points in the
network, keeping each layer's input distribution roughly standard — which
smooths optimization enough to allow much higher learning rates.

The question is never *whether* to normalize a transformer — it's **across
which axis**. That one choice is the entire LayerNorm-vs-BatchNorm decision.

## The Math

Both compute the same standardize-then-rescale, differing only in which
elements share statistics:

$$\hat{x} = \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}}, \qquad y = \gamma \odot \hat{x} + \beta$$

Every symbol: $\mu$ and $\sigma^2$ are the mean and (biased) variance
computed **over the normalization axis**, $\epsilon$ a tiny constant (default
`1e-5`) preventing division by zero, and $\gamma, \beta$ *learned* per-feature
scale and shift — the layer's way of undoing the normalization wherever
undoing helps.

- **LayerNorm** computes $\mu, \sigma^2$ **across the feature dimension,
  separately for every token**. Each token normalizes itself; nothing depends
  on the batch.
- **BatchNorm** computes them **across the batch, separately for every
  feature**. Every sample's output depends on *who else is in the batch* —
  and at inference it switches to running statistics accumulated during
  training.

## Dry-Run: LayerNorm on One Token, by Hand

```
one token's features: x = [1, 2, 3]        (d = 3; γ = 1, β = 0)

μ  = (1 + 2 + 3) / 3 = 2
σ² = ((1−2)² + (2−2)² + (3−2)²) / 3 = 2/3 ≈ 0.6667      (biased: divide by d)
√(σ² + 1e-5) ≈ 0.8165

x̂ = [(1−2)/0.8165, (2−2)/0.8165, (3−2)/0.8165]
   = [−1.2247, 0, 1.2247]                                 mean 0, unit variance ✓
```

## Why BatchNorm Is Wrong for Sequence Models

```
                 BatchNorm normalizes ↓ this way        LayerNorm → this way
                 (across the batch, per feature)        (across features, per token)

  batch item 0:  [ x00  x01  x02  x03 ]                 [ ──────────────────→ ]
  batch item 1:  [ x10  x11  x12  x13 ]                 [ ──────────────────→ ]
  batch item 2:  [ x20  x21  x22  x23 ]                 [ ──────────────────→ ]
                    ↑    ↑    ↑    ↑
```

Three concrete failures for NLP: (1) **batch dependence** — the same
sentence gets different representations depending on its batch-mates
(exercise 4 demonstrates this directly); (2) **variable lengths** — padded
positions pollute the per-feature statistics; (3) **train/inference
mismatch** — the running-statistics switch adds a whole class of "works in
training, breaks in serving" bugs. LayerNorm has none of these: each token
is its own statistical universe.

**RMSNorm**, used by most current LLMs, is LayerNorm minus the
mean-subtraction and the bias: $y = \frac{x}{\text{RMS}(x)} \odot \gamma$
with $\text{RMS}(x) = \sqrt{\frac{1}{d}\sum_i x_i^2 + \epsilon}$. It turns
out the re-centering barely matters in practice, and dropping it saves a
measurable slice of compute at LLM scale. Same per-token philosophy as
LayerNorm; fewer moving parts.

## Decision Guide: Which Norm

| Situation | Use | Why |
|---|---|---|
| Transformers / any sequence model | `nn.LayerNorm(d_model)` | per-token, batch-independent, length-proof |
| Modern LLM from scratch, compute-conscious | RMSNorm | LayerNorm minus re-centering, cheaper |
| CNNs on fixed-size image batches | `nn.BatchNorm2d` | its home turf |
| Anything with batch size 1 or variable lengths | never BatchNorm | statistics collapse / get polluted |

## Key Takeaways for Section 3

Same formula, different axis: LayerNorm per token across features, BatchNorm
per feature across the batch. Sequence data → LayerNorm (or RMSNorm), full
stop. $\gamma, \beta$ are learned; $\epsilon$ just guards the divide.

*Next: the layer that behaves differently depending on a global switch.*

---

# 4: Dropout and the train/eval Switch

## The Intuition

**Dropout** fights overfitting by randomly zeroing each activation with
probability $p$ during training — every forward pass trains a slightly
different sub-network, so no single neuron can become load-bearing. At
inference, dropout must vanish: you want the full network, deterministically.

The subtlety is the scaling. If you zero activations at train time, the
surviving ones must be scaled **up** by $\frac{1}{1-p}$ so the *expected*
value seen by the next layer is unchanged (this is **inverted dropout**, what
PyTorch implements):

$$y_i = \frac{m_i \cdot x_i}{1 - p}, \qquad m_i \sim \text{Bernoulli}(1-p)$$

Every symbol: $m_i$ is the keep/drop coin flip (1 with probability $1-p$),
and the $\frac{1}{1-p}$ compensates so
$\mathbb{E}[y_i] = \frac{(1-p) \cdot x_i}{1-p} = x_i$.

## Dry-Run with Tiny Numbers

```
x = [2, 4, 6, 8],  p = 0.5,  coin flips → keep, drop, keep, drop

train mode: y = [2/0.5, 0, 6/0.5, 0] = [4, 0, 12, 0]
  E[y_i] = 0.5 · x_i/0.5 + 0.5 · 0 = x_i          expectation preserved ✓

eval mode:  y = [2, 4, 6, 8]                       dropout is a no-op
```

## The Switch — and the Classic Bug

`model.train()` and `model.eval()` flip a boolean (`module.training`) on
every module in the tree. Dropout reads it: drop-and-scale when `True`,
identity when `False`. (BatchNorm reads it too — batch stats vs running
stats.)

The classic bug: running inference **without calling `model.eval()`**. The
model keeps dropping random activations, so the same input produces
*different outputs on every call* — usually discovered as "my deployed model
is nondeterministic" or "eval metrics are mysteriously worse than training."
Exercise 5 builds the detector: call the model twice; if the outputs differ,
someone forgot `eval()`.

Keep the two inference switches straight — you need **both**, and they do
different jobs (chapter 3 vs this chapter):

| Call | Controls | Forgetting it costs |
|---|---|---|
| `model.eval()` | layer *behavior* (dropout, norm stats) | wrong, random outputs |
| `torch.no_grad()` / `inference_mode()` | autograd *recording* | wasted memory, slower |

## Key Takeaways for Section 4

Dropout: zero with probability $p$, scale survivors by $1/(1-p)$, vanish at
eval. `train()/eval()` is a behavior switch, not a gradient switch — pair
`eval()` *with* `no_grad()` at inference, and remember from chapter 4 that
neither one freezes weights.

*Next: the nonlinearities between the layers.*

---

# 5: Activations: ReLU vs GELU vs SiLU

## The Problem It Solves

Without a nonlinearity, a stack of Linears collapses into one Linear
($W_2(W_1 x) = (W_2 W_1) x$) — depth buys nothing. The activation *is* what
makes deep networks deep. The three that matter for NLP:

$$\text{ReLU}(x) = \max(0, x) \qquad \text{GELU}(x) = x \cdot \Phi(x) \qquad \text{SiLU}(x) = x \cdot \sigma(x)$$

Every symbol: $\Phi(x)$ is the standard normal CDF (the probability a
$\mathcal{N}(0,1)$ draw is below $x$), and $\sigma(x) = \frac{1}{1+e^{-x}}$
the logistic sigmoid. Both GELU and SiLU read as "**$x$, gated by how
positive $x$ is**" — smooth, probabilistic versions of ReLU's hard gate.

## Dry-Run: The Three Side by Side

```
x        −2        −1        0        1        2
ReLU      0         0        0        1.0      2.0
GELU    −0.0455   −0.1587    0        0.8413   1.9545
SiLU    −0.2384   −0.2689    0        0.7311   1.7616

GELU(−1) = −1 · Φ(−1) = −1 · 0.1587 = −0.1587
SiLU(−1) = −1 · σ(−1) = −1 · 0.2689 = −0.2689
```

The plot in words: all three are ≈identity for large positive $x$ and ≈zero
for large negative $x$. They differ in the middle — ReLU has a hard corner
at 0; GELU and SiLU dip slightly *below* zero and glide smoothly through.

## Why the Smooth Ones Won in Transformers

ReLU's hard zero has a failure mode: a neuron whose input is always negative
outputs 0 with **gradient exactly 0** — it can never recover (a **dead
neuron**). GELU and SiLU keep a small negative output and a nonzero gradient
there, so every neuron keeps learning. The cost is a slightly more expensive
function — negligible next to the matmuls. GPT-style models standardized on
GELU; many recent LLMs use SiLU (usually inside the SwiGLU feed-forward
variant).

## Decision Guide: Which Activation

| Situation | Use | Why |
|---|---|---|
| Transformer feed-forward blocks | `nn.GELU()` | the GPT-lineage standard, no dead neurons |
| Modern LLM blocks (SwiGLU-style) | `nn.SiLU()` | current-generation default |
| Cheap baselines, non-transformer MLPs | `nn.ReLU()` | fastest, fine when depth is modest |
| Hidden-layer gates needing (0,1) output | `nn.Sigmoid()` | but never before CrossEntropy — next section! |

## Key Takeaways for Section 5

No activation → no depth. ReLU is a hard gate with a dead-neuron risk; GELU
and SiLU are smooth gates ($x$ times a CDF/sigmoid) and are the transformer
defaults. Pick GELU unless you have a reason.

*Next: the layer that isn't a layer — the loss.*

---

# 6: The Loss Family: CrossEntropy and Its Relatives

## The Problem It Solves

Classification training needs a differentiable measure of "how wrong was
this distribution?" **Cross-entropy** is that measure: it punishes the model
by $-\log(\text{probability assigned to the correct class})$ — confident
and right costs nearly nothing; confident and wrong costs enormously.

## The Math

For one sample with logits $z \in \mathbb{R}^C$ and true class $t$:

$$\mathcal{L} = -\log\left(\frac{e^{z_t}}{\sum_{j=1}^{C} e^{z_j}}\right) = -z_t + \log\sum_{j} e^{z_j}$$

Every symbol: $C$ is the number of classes, $z_j$ the raw score for class
$j$, $z_t$ the score of the *correct* class, and the fraction is just
softmax. `F.cross_entropy` fuses the softmax and the log — which is the
source of both its numerical stability and its most famous gotcha.

## Dry-Run with Tiny Numbers

```
logits z = [2, 1, 0], true class t = 0

softmax: e² , e¹ , e⁰ = 7.389, 2.718, 1.000     sum = 11.107
p = [0.6652, 0.2447, 0.0900]

loss = −ln(p_t) = −ln(0.6652) = 0.4076

sanity checks:  perfectly confident & right  (p_t → 1)  → loss → 0
                confidently wrong            (p_t → 0)  → loss → ∞
```

## Gotcha #1 (the big one): CrossEntropy Eats Raw Logits

`F.cross_entropy` applies softmax **internally**. If your model's forward
ends with `softmax(...)`, the loss computes softmax-of-softmax: the loss is
still finite, gradients still flow, training still "runs" — just badly and
silently, because double-softmax squashes all the differences between
classes (probabilities get re-exponentiated as if they were scores).
**Models should return raw logits. Softmax belongs at inference time only**
(and even then, only if you need actual probabilities — `argmax` doesn't).

## The Relatives, and When Each Applies

**`F.nll_loss`** is cross-entropy's second half: it expects
**log-probabilities** (from `F.log_softmax`) and just picks and negates.
The identity `cross_entropy(z) == nll_loss(log_softmax(z))` is exercise 7's
proof. Use it when your pipeline already produces log-probs (some decoders
do); otherwise prefer the fused, stabler `cross_entropy`.

**`F.binary_cross_entropy_with_logits`** is for **binary and multi-label**
problems — each output is its own independent yes/no with a sigmoid, not a
competition over classes with a softmax. Multi-label ("this article is
*both* sports and politics") is exactly the case softmax cannot express.
Always use the `_with_logits` version — like `cross_entropy`, it fuses the
sigmoid in for numerical stability; `Sigmoid` + `BCELoss` is the unstable
spelling of the same thing.

The knobs on `cross_entropy` you'll actually use: **`ignore_index=-100`**
(positions with this target contribute nothing — the padding tool, chapter
2 built it by hand), **`label_smoothing=ε`** (soft targets, chapter 2 built
those too), **`weight`** (per-class weights for imbalanced data), and
**`reduction`** (`"mean"` default / `"sum"` / `"none"` for per-sample
losses).

## Decision Guide: Which Loss

| Situation | Use | Input must be |
|---|---|---|
| Multi-class, exactly one correct class | `F.cross_entropy` | **raw logits** `(B, C)` + int64 targets `(B,)` |
| Already have log-probabilities | `F.nll_loss` | log-probs |
| Binary yes/no, or multi-label | `F.binary_cross_entropy_with_logits` | raw logits, float targets |
| Sequences with padding | `cross_entropy(..., ignore_index=-100)` | flattened logits (§7) |
| Model ends with softmax + any of the above | — never | double-softmax trains badly, silently |

## Key Takeaways for Section 6

CE = $-\log p_{\text{correct}}$, computed from **raw logits** — never add
your own softmax. NLL is CE minus the softmax half; BCEWithLogits is the
independent-sigmoid world for binary/multi-label. `ignore_index` is the
padding tool.

*Next: wiring the loss to real, padded sequence batches.*

---

# 7: Putting It Together: Padding-Aware Sequence Loss

Language-model-style training produces logits of shape
`(batch, seq_len, vocab)` and targets `(batch, seq_len)` — but
`F.cross_entropy` wants classes in **dimension 1**: either `(N, C)` with 1-D
targets, or `(B, C, T)` with 2-D targets. Two equivalent spellings:

```
logits: (B, T, V)      targets: (B, T), padding marked with -100

Spelling 1 — flatten (the common one):
  loss = F.cross_entropy(
      logits.view(-1, V),        # (B·T, V)   every position is now a "sample"
      targets.view(-1),          # (B·T,)
      ignore_index=-100,         # padded positions vanish from the mean
  )

Spelling 2 — channels-second:
  loss = F.cross_entropy(
      logits.permute(0, 2, 1),   # (B, V, T)  classes moved to dim 1
      targets,                   # (B, T)
      ignore_index=-100,
  )
```

Both compute the same number (exercise 8 proves it). Note which chapters
just fired at once: `view` on a contiguous tensor (ch1), class-dim
convention and `ignore_index` (this chapter), and the reason the mean runs
over only real tokens (ch2's masking philosophy). The toolbox composes.

---

# 8: Key Takeaways + Master Decision Table

| I want to... | Reach for | Watch out for |
|---|---|---|
| Token IDs → vectors | `nn.Embedding(V, d)` | inputs must be int64 |
| Keep the pad token inert | `padding_idx=PAD_ID` | zero row, zero gradient, forever |
| Import existing vectors | `Embedding.from_pretrained(E, freeze=...)` | freeze decision is explicit |
| Normalize a sequence model | `nn.LayerNorm(d_model)` | per-token; batch plays no role |
| Normalize like a modern LLM | RMSNorm | LayerNorm minus re-centering |
| Normalize image batches | `BatchNorm2d` | never for sequences / batch of 1 |
| Regularize activations | `nn.Dropout(p)` | train-only; scaled by 1/(1−p) |
| Deterministic inference | `model.eval()` **and** `torch.no_grad()` | they are different switches |
| Nonlinearity in a transformer FFN | `nn.GELU()` (or `nn.SiLU()`) | ReLU risks dead neurons |
| Multi-class loss | `F.cross_entropy(logits, targets)` | RAW logits — no softmax in forward |
| Loss from log-probs | `F.nll_loss` | == CE ∘ log_softmax |
| Binary / multi-label loss | `F.binary_cross_entropy_with_logits` | never Sigmoid + BCELoss |
| Sequence loss with padding | flatten to `(B·T, V)` + `ignore_index=-100` | class dim must be dim 1 |
| Class imbalance | `cross_entropy(..., weight=w)` | per-class, not per-sample |

**Connection forward:** the model side of the toolbox is complete — tensors,
ops, autograd, module patterns, layers, and losses. Chapter 6 turns to the
*data* side: `Dataset`, `DataLoader`, and the collate function that turns
ragged text into exactly the padded batches this chapter's loss knows how to
handle.
