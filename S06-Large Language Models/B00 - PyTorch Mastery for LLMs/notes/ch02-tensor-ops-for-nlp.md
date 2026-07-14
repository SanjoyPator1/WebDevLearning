# Chapter 2: Tensor Operations for NLP

## Table of Contents

1. [The Fifteen Ops That Are 90% of LLM Code](#1-the-fifteen-ops-that-are-90-of-llm-code)
2. [The Matmul Family](#2-the-matmul-family)
3. [Softmax and the Meaning of dim](#3-softmax-and-the-meaning-of-dim)
4. [gather and scatter](#4-gather-and-scatter)
5. [Masking Done Right](#5-masking-done-right)
6. [Selection and Sampling](#6-selection-and-sampling)
7. [Combining and Splitting](#7-combining-and-splitting)
8. [Key Takeaways + Master Op Table](#8-key-takeaways--master-op-table)

---

# 1: The Fifteen Ops That Are 90% of LLM Code

## What This Chapter Is Really About

Open any transformer implementation
and strip away the class boilerplate. What remains is a surprisingly short
list: matrix multiplies, softmaxes, masks, a `gather` hiding inside the loss,
some concatenation plumbing, and a sampler at the end. Perhaps fifteen
operations total.

The difference between reading that code and *owning* it is whether each op is
a deliberate choice or a cargo-culted incantation. Why `@` here but `einsum`
there? Why `masked_fill` with $-\infty$ instead of multiplying by zero? Why
does the loss use `gather` at all? This chapter makes every one of those a
decision you can defend — and each section ends with the decision guide that
tells you when to reach for which tool.

---

# 2: The Matmul Family

## The Problem It Solves

PyTorch offers five ways to multiply things, and they differ on the two axes
that cause real bugs: **elementwise vs true matrix product**, and **strict
shapes vs broadcasting**. Choosing the strict one when you wanted
broadcasting crashes (fine); choosing the broadcasting one when you wanted
strictness *silently computes the wrong thing* (not fine).

## The Five Members

**`*` is elementwise** — not a matrix product at all — and it broadcasts.
`attention_weights * values` multiplies matching positions. If you write `*`
where you meant `@` and the shapes happen to broadcast, nothing crashes and
everything is wrong.

**`@` / `torch.matmul` is the workhorse**: a true matrix product over the
last two dims that **broadcasts every batch dim in front**. This is why one
line handles `(B, H, T, d) @ (B, H, d, T)` — the `B` and `H` dims just ride
along.

**`torch.mm` is strict 2-D** and **`torch.bmm` is strict 3-D** (exactly one
batch dim, no broadcasting). They do less — which is exactly their value: use
them when a silently broadcast batch dim would be a bug you'd rather catch.

**`torch.einsum` names every dimension.** You write the index pattern; PyTorch
figures out the transposes and the batching.

## The Math

For 2-D operands, every member computes the same thing:

$$C_{ij} = \sum_{k} A_{ik} \, B_{kj}$$

where $i$ indexes rows of $A$, $j$ indexes columns of $B$, and $k$ is the
shared inner dimension being summed away. Everything else in the family is
bookkeeping about *which* dims are batch, and *who* is allowed to broadcast.

## Dry-Run: Attention Scores, Shapes First, Then Numbers

```
Q: (B=1, H=2, T=2, d=3)      K: (1, 2, 2, 3)

scores = Q @ K.transpose(-2, -1)
  step 1: K.transpose(-2, -1) → (1, 2, 3, 2)        stride swap, free
  step 2: matmul over last two dims: (2,3) @ (3,2) → (2,2)
  step 3: batch dims (1, 2) broadcast/ride along
  result: (1, 2, 2, 2)                               # (B, H, T_q, T_k)

Now one head with actual numbers (T=2, d=2 to keep it tiny):
  q = [[1, 0],        k = [[1, 2],        k^T = [[1, 3],
       [2, 1]]             [3, 0]]               [2, 0]]

  q @ k^T = [[1·1+0·2, 1·3+0·0],   = [[1, 3],
             [2·1+1·2, 2·3+1·0]]      [4, 6]]
  → scores[0][1] = 3 means: how much query-token-0 attends to key-token-1
    (before scaling and softmax)
```

## einsum Crash Course

Read the string left of `->` as "the dims of each input, named"; right of
`->` as "the dims I want kept". Any letter that vanishes was **summed over**;
letters appearing in both inputs are matched.

```
scores  = torch.einsum("btd,bsd->bts", Q, K)     # sum over d → (B, T_q, T_k)
                                                  # the transpose is implicit!
context = torch.einsum("bhqk,bhkd->bhqd", A, V)  # attention-weighted values
pooled  = torch.einsum("bt,btd->bd", weights, X) # weighted sum over positions
```

## Decision Guide: Which Multiply

| Situation | Use | Why |
|---|---|---|
| Elementwise scale/gate/mask | `*` | it's not a matmul — know which you mean |
| Everyday batched matmul | `@` | broadcasts batch dims, reads clean |
| Exactly 2-D, want shape strictness | `mm` | crashes loudly on any batch dim |
| Exactly 3-D, want strictness | `bmm` | refuses silent batch broadcasting |
| >2 batch dims, or implicit transposes obscure intent | `einsum` | names make the contraction readable |
| Inside reusable model code | `@` | it must batch; `mm` would crash |

## Key Takeaways for Section 2

`*` and `@` are different universes. `@` broadcasts batch dims — a
convenience in model code, a foot-gun in loss code. `mm`/`bmm` buy you
strictness; `einsum` buys you readable contraction over many dims.

*Next: the function that turns scores into probabilities — and the `dim`
argument everyone gets wrong once.*

---

# 3: Softmax and the Meaning of dim

## The Intuition

Softmax turns a vector of scores into a probability distribution:
big scores get big probabilities, everything positive, sums to one. The
`dim` argument answers one question: **which entries are competing with each
other?** `dim=k` means: entries along dimension $k$ fight for probability
mass; every other dimension is just a batch of independent contests.

## The Math

$$\text{softmax}(z)_i = \frac{e^{z_i}}{\sum_{j} e^{z_j}}$$

where $z$ is the score vector, $z_i$ the score of candidate $i$, and the sum
in the denominator runs over all competitors *along the chosen dim*. The
exponential makes everything positive and amplifies differences; the division
normalizes to sum 1.

## Dry-Run: The Same Matrix, Two dims

```
scores = [[1, 2, 3],
          [1, 1, 1]]                 shape (2, 3)

softmax(dim=-1): each ROW competes (3 candidates per contest)
  row 0: e^1, e^2, e^3 = 2.718, 7.389, 20.086   sum = 30.193
         → [0.090, 0.245, 0.665]                 sums to 1 across the row ✓
  row 1: → [0.333, 0.333, 0.333]

softmax(dim=0): each COLUMN competes (2 candidates per contest)
  col 0: e^1/(e^1+e^1) = 0.5             → column sums to 1, rows don't!
  col 1: e^2/(e^2+e^1) = 7.389/10.107 = 0.731
  col 2: e^3/(e^3+e^1) = 20.086/22.804 = 0.881
```

## The Silent Killer

Attention scores are `(B, T_q, T_k)`: for each query, the *keys* compete. The
correct call is `softmax(dim=-1)`. Write `dim=1` instead and each key column
competes across queries — semantically nonsense — but every number is still a
valid probability, nothing crashes, gradients flow, and the model still sort
of trains. Wrong-`dim` softmax is a *performance* bug, not a crash, which is
what makes it evil. The habit: for logits and attention scores, write
`dim=-1` and say to yourself "the candidates live in the last dim."

## Key Takeaways for Section 3

`dim` = the dimension whose entries compete = the dimension that sums to 1
afterwards. For scores/logits that's virtually always `dim=-1`. When
debugging, print `output.sum(dim=...)` — the dim that gives all-ones is the
dim you actually normalized.

*Next: the op hiding inside every cross-entropy.*

---

# 4: gather and scatter

## The Problem It Solves

Cross-entropy needs "the probability the model assigned to *the correct
token*, in every row." That is a **batched lookup with a different index per
row** — not a slice (indices differ per row), not fancy indexing along one
axis alone. `gather` is the purpose-built tool, and `scatter_` is its
write-direction twin.

## The Math

For `dim=1` on a 2-D tensor:

$$\text{out}[i][j] = \text{input}\big[i\big]\big[\text{index}[i][j]\big]$$

Every symbol: `input` is what you're reading from, `index` is an integer
tensor **with the same number of dims as input**, and `out` has exactly
`index`'s shape. Along `dim`, the index value *replaces* your position; along
every other dim you stay where you are.

## Dry-Run: The Heart of Cross-Entropy

```
logits = [[2.0, 0.5, 1.0, 3.0],        shape (2, 4) — batch of 2, vocab of 4
          [1.5, 2.5, 0.0, 1.0]]
targets = [3, 1]                        correct token per row

targets.unsqueeze(1) → [[3], [1]]       index must match input's rank (2-D)

logits.gather(dim=1, index=[[3],[1]]):
  row 0: stay in row 0, index 3 along dim 1 → logits[0][3] = 3.0
  row 1: stay in row 1, index 1 along dim 1 → logits[1][1] = 2.5
  → [[3.0], [2.5]]                       the correct-class logits, batched ✓
```

The equally common idiom for exactly-one-index-per-row is fancy indexing with
`arange`: `logits[torch.arange(2), targets]` → `[3.0, 2.5]`. Same numbers,
1-D result, arguably more readable — but it only does one-per-row, while
`gather` handles any number of lookups per row (top-k teacher logits, beam
candidates) and respects `dim`.

**`scatter_` writes instead of reads**: `out[i][index[i][j]] = src[i][j]`
along `dim=1`. Its canonical NLP jobs are building one-hot rows and label
smoothing:

```
smooth = torch.full((B, V), eps / (V - 1))
smooth.scatter_(1, targets.unsqueeze(1), 1 - eps)   # put 1-eps at the target column
```

## Decision Guide: Lookup Tools

| Situation | Use | Why |
|---|---|---|
| One index per row (the CE case) | `logits[arange(B), targets]` | shortest, clearest |
| Several indices per row, or need `dim` control | `gather` | built for it |
| Write values at indexed positions | `scatter_` | the write-inverse |
| Same one index for *every* row | plain slicing `t[:, k]` | no index tensor needed |

## Key Takeaways for Section 4

`gather` = batched per-row lookup; index rank must match input rank; output
shape = index shape. `scatter_` is the same map run backwards, for writes.
If you can say "for each row, pick *its own* column," you want one of these.

*Next: making tokens invisible — the right way for each situation.*

---

# 5: Masking Done Right

## The Problem It Solves

NLP tensors are full of positions that must not participate: padding tokens,
future tokens under a causal mask, pruned vocabulary entries during sampling.
PyTorch gives four masking tools, and they are **not interchangeable** — the
right one depends on what happens to the masked values downstream.

## The Four Tools

**`masked_fill(mask, value)`** — replace masked positions with a constant.
The tool for attention scores, because the constant can be $-\infty$.

**`torch.where(cond, a, b)`** — elementwise blend of two tensors: take from
`a` where `cond` is True, else from `b`. The tool when masked positions need
*different content*, not a constant.

**Boolean indexing `t[mask]`** — *removes* masked elements entirely,
returning a flat 1-D tensor of survivors (chapter 1). The tool when
downstream code should never even see the masked positions (e.g., computing
mean loss over real tokens only).

**Multiply by mask `t * mask`** — zeroes masked positions but *keeps them in
the tensor*. Cheap and differentiable-friendly; only correct when a zero is
genuinely neutral downstream (sums; things followed by their own
normalization).

## Why Attention Masks Use −∞, Not 0

Softmax happens *after* masking. Whatever you write into masked slots will be
exponentiated: $e^{-\infty} = 0$, so $-\infty$ slots get **exactly zero
probability** and the remaining slots renormalize among themselves. Write 0
instead and $e^0 = 1$ — a masked slot gets *more* probability than a slot
scoring $-2$!

## Dry-Run: Causal Masking, Correct vs Broken

```
scores (3×3, every row [1, 2, 3]) — token t may attend only to positions ≤ t

causal mask (True = BLOCK):        masked scores:
  [[F, T, T],                        [[1, -inf, -inf],
   [F, F, T],          →              [1,    2, -inf],
   [F, F, F]]                         [1,    2,    3]]

softmax(dim=-1) row by row:
  row 0: e^1 / e^1                    → [1.000, 0,     0    ]  sums to 1 ✓
  row 1: e^1, e^2 → 2.718, 7.389      → [0.269, 0.731, 0    ]  sums to 1 ✓
  row 2: 2.718, 7.389, 20.086         → [0.090, 0.245, 0.665]  sums to 1 ✓

THE BROKEN WAY — softmax first, zero after:
  softmax([1,2,3]) = [0.090, 0.245, 0.665]
  zero the future in row 0 → [0.090, 0, 0]      sums to 0.090 ✗
  → not a distribution; the value vectors get scaled by 0.09 instead of
    averaged; training limps
```

The construction idiom: `torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)`
is True strictly above the diagonal — exactly the future positions to block —
then `scores.masked_fill(causal_mask, float("-inf"))`.

*One trap for later: if masking ever leaves an entire row at $-\infty$ (e.g.,
a fully padded sequence), softmax returns NaN for that row — the sum in the
denominator is zero. Chapter 8 covers hunting that NaN; the fix is usually
masking the loss rather than feeding empty rows.*

## Decision Guide: Masking Tools

| Downstream need | Use | Why |
|---|---|---|
| Softmax comes next | `masked_fill(mask, -inf)` | e^{-inf}=0, survivors renormalize |
| Replace with per-position alternatives | `torch.where` | blends two tensors |
| Masked items must vanish from the computation | boolean indexing `t[mask]` | removes, flattens |
| A zero is genuinely neutral (sums, pre-normalized) | `t * mask` | cheapest, keeps shape |
| Max/argmax over valid entries only | `masked_fill(mask, -inf)` then max | -inf can never win |

## Key Takeaways for Section 5

Choose the mask tool by what happens *after* the mask. $-\infty$ before
softmax, `where` for blends, boolean indexing for removal, multiply only when
zero is neutral. Never zero *after* softmax — rows stop summing to one.

*Next: turning the final distribution into an actual token.*

---

# 6: Selection and Sampling

## The Problem It Solves

At the end of every generation step sits a vector of logits over the
vocabulary, and one question: **which token comes out?** Deterministic picking
(`argmax`) is repetitive and dull; raw sampling from the full distribution is
incoherent (there is *always* some probability mass on garbage tokens spread
across a 50k vocabulary). The knobs — temperature and top-k — reshape the
distribution between those extremes.

## The Toolbox

`argmax(dim=-1)` — index of the single best. `topk(k, dim=-1)` — the `k`
best **values and indices** in one call. `sort`/`argsort` — full ordering
(you rarely need more than `topk`). `multinomial(probs, num_samples)` — draw
indices according to probabilities; **it wants probabilities, not logits** —
feeding raw logits (which can be negative) is an error, and feeding
un-normalized positives silently skews the draw.

## Temperature: The Math

$$p_i = \frac{e^{z_i / T}}{\sum_j e^{z_j / T}}$$

$z_i$ is token $i$'s logit and $T$ is the temperature. Dividing by $T < 1$
stretches the gaps between logits apart, so the winner takes even more of the
mass (sharper, more deterministic). Dividing by $T > 1$ squeezes the gaps
shut, flattening the distribution (more random). $T \to 0$ becomes argmax;
$T \to \infty$ becomes uniform.

## Dry-Run: One Distribution, Three Temperatures

```
logits over a 5-token vocab: z = [2.0, 1.0, 0.5, 0.0, -1.0]

T = 1.0:  z/T = [2, 1, 0.5, 0, -1]
  exp:  7.389, 2.718, 1.649, 1.000, 0.368     sum = 13.124
  p  = [0.563, 0.207, 0.126, 0.076, 0.028]

T = 0.5 (sharper):  z/T = [4, 2, 1, 0, -2]
  exp:  54.598, 7.389, 2.718, 1.000, 0.135    sum = 65.840
  p  = [0.829, 0.112, 0.041, 0.015, 0.002]    ← winner grew 0.563 → 0.829

T = 2.0 (flatter):  z/T = [1, 0.5, 0.25, 0, -0.5]
  exp:  2.718, 1.649, 1.284, 1.000, 0.607     sum = 7.258
  p  = [0.375, 0.227, 0.177, 0.138, 0.084]    ← winner shrank to 0.375
```

## Top-k Sampling: The Four-Step Pipeline

Keep only the `k` most plausible tokens, *then* sample among them — the tail
of garbage tokens gets exactly zero probability:

```
logits (V,) ──topk(k)──▶ threshold = k-th best value
     │
     ├─ masked_fill(logits < threshold, -inf)     everything below the top-k → -inf
     ▼
softmax(dim=-1)                                    survivors renormalize (section 5!)
     ▼
multinomial(probs, num_samples=1)                  draw the token
```

Note how the pipeline is *assembled from this chapter*: `topk` (selection) +
`masked_fill` with $-\infty$ (masking) + softmax (normalization) +
`multinomial` (sampling). Nothing new — just composition.

## Decision Guide: Picking a Token

| Situation | Use | Why |
|---|---|---|
| Deterministic eval / greedy decoding | `argmax` | reproducible, no sampling noise |
| Need the k best *with* scores | `topk` | one call, values + indices |
| Need a full ranking | `sort` / `argsort` | rare; topk usually suffices |
| Sampling for generation | temperature → top-k mask → softmax → `multinomial` | controllable randomness, no garbage tail |
| Sampling from raw logits directly | — never | `multinomial` needs probabilities |

## Key Takeaways for Section 6

Temperature reshapes (divide logits *before* softmax); top-k truncates (mask
to $-\infty$ *before* softmax); `multinomial` draws from probabilities. The
whole sampler is five lines of ops you already know.

*Next: the plumbing — sticking tensors together and taking them apart.*

---

# 7: Combining and Splitting

## The Intuition

Two questions cover this whole section. When combining: **does the result
have a new axis with its own meaning?** When splitting: **do I know the piece
sizes, or the piece count?**

## cat vs stack

`torch.cat([a, b], dim=k)` joins along an **existing** axis — the result has
the same number of dims. `torch.stack([a, b], dim=k)` creates a **new** axis
— every input must be identical in shape, and the result has one more dim.

```
a, b each (2, 3):

cat([a, b], dim=0)   → (4, 3)     "more rows of the same kind of thing"
stack([a, b], dim=0) → (2, 2, 3)  "a new axis whose index means WHICH tensor"

NLP litmus tests:
  appending new tokens to a KV sequence      → same axis, cat(dim=1)
  collecting per-layer hidden states         → new "layer" axis, stack
  batching N equal-length sequences          → new "batch" axis, stack
```

## split vs chunk vs unbind

`split(sizes, dim)` cuts by **sizes** — pass an int (every piece that size)
or a list (`split([2, 5, 1])` for exact control). `chunk(n, dim)` cuts into a
**count** of `n` near-equal pieces. `unbind(dim)` removes an axis entirely,
returning a tuple of slices — the inverse of `stack`. All three return
**views** (no copies).

**The fused-QKV idiom** — one big projection, split three ways — is the
canonical use:

```
qkv = x @ W_qkv                      # (B, T, 3·d_model)   one matmul, GPU-friendly
q, k, v = qkv.chunk(3, dim=-1)       # 3 × (B, T, d_model)  "I know the COUNT"
# equivalently: qkv.split(d_model, dim=-1)          — "I know the SIZE"
```

## Decision Guide: Plumbing

| Situation | Use | Why |
|---|---|---|
| Extend an existing axis (tokens, batch rows) | `cat` | same rank out |
| Create an axis meaning "which one" (layers, heads, candidates) | `stack` | adds a dim |
| Cut into pieces of known sizes | `split` | exact control, uneven OK |
| Cut into a known number of equal pieces | `chunk` | count, not sizes |
| Explode an axis into a tuple (inverse of stack) | `unbind` | removes the dim |

## Key Takeaways for Section 7

`cat` extends, `stack` creates. `split` takes sizes, `chunk` takes a count,
`unbind` dissolves an axis. The QKV fused-projection split is the idiom to
recognize on sight.

---

# 8: Key Takeaways + Master Op Table

Every LLM forward pass is a composition of the ops in this chapter, and every
one of them is now a decision, not a habit:

| I want to... | Reach for | Watch out for |
|---|---|---|
| Elementwise scale / gate / apply mask weights | `*` | it broadcasts — assert shapes match |
| Batched matrix multiply | `@` | batch dims broadcast silently |
| Matmul with strict shape checking | `mm` (2-D) / `bmm` (3-D) | won't broadcast — by design |
| Readable contraction over many dims | `einsum` | vanished letters are summed |
| Scores → probabilities | `softmax(dim=-1)` | wrong dim trains badly, silently |
| Per-row lookup by index tensor | `gather` / `logits[arange(B), targets]` | index rank must match input |
| Per-row write by index tensor | `scatter_` | in-place; clone first if needed |
| Hide positions from an upcoming softmax | `masked_fill(mask, -inf)` | all-−inf rows → NaN |
| Blend two tensors elementwise | `torch.where` | all three args broadcast |
| Drop masked elements entirely | `t[mask]` | flattens to 1-D |
| Zero-out where zero is neutral | `t * mask` | wrong before softmax! |
| Greedy pick | `argmax(dim=-1)` | — |
| k best values + indices | `topk` | — |
| Sample a token | temperature → top-k → softmax → `multinomial` | multinomial needs probs, not logits |
| Join along an existing axis | `cat` | — |
| Join creating a new axis | `stack` | inputs must match exactly |
| Cut by sizes / by count / dissolve axis | `split` / `chunk` / `unbind` | all return views |

**Connection forward:** these two chapters covered tensors and the ops
*between* them — the forward pass vocabulary. Chapter 3 goes underneath:
what autograd records while all these ops run, and how `.backward()` turns
that recording into gradients — including the four ways to tell it *not* to.
