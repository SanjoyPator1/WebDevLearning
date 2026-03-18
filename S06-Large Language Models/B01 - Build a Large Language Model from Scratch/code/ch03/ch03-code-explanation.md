# Chapter 3 Code Explanation — Coding Attention Mechanisms

This document walks through every section of `ch03.ipynb` from Sebastian Raschka's *Build a Large Language Model From Scratch*. The notebook builds attention from scratch in six stages: from the naive dot-product idea, through trainable projections, causal masking, dropout, and finally the full multi-head attention used in real GPT models. Each section below explains what the code does, why it does it, and what the numbers mean.

---

## Section 3.1 — The Problem with Modeling Long Sequences

Before transformers, sequence-to-sequence tasks (like machine translation) used **encoder-decoder RNNs**. The encoder reads the entire input sentence one token at a time and compresses it into a single fixed-size hidden state. The decoder then uses that one vector to generate the output.

The compression is the bottleneck. Imagine reading a 500-word paragraph and being asked to summarize it in a single sentence — you inevitably lose detail. Long-range dependencies (like the subject of a verb that appeared 20 tokens ago) become especially hard to preserve.

This is the problem attention was invented to solve.

---

## Section 3.2 — Capturing Dependencies with Attention

The key insight: instead of compressing the entire input into one vector, let the decoder **look back at all encoder hidden states** and decide which ones are relevant for the current output step. Certain tokens are more relevant than others — a relevance score is computed and used to take a weighted combination.

**Self-attention** takes this further: a token attends not just to encoder outputs but to *all other tokens in its own sequence*. Each token can ask "which other tokens in this sequence are most relevant to understanding me?" This is what allows the model to capture long-range dependencies without the bottleneck.

---

## Section 3.3 — Simple Self-Attention (No Trainable Weights)

### The Setup

The notebook uses a toy sentence — "Your journey starts with one step" — embedded as six 3-dimensional vectors. These aren't real embeddings; they're hand-picked values for illustrative arithmetic.

```python
inputs = torch.tensor(
  [[0.43, 0.15, 0.89],  # Your     x^(1)
   [0.55, 0.87, 0.66],  # journey  x^(2)
   [0.57, 0.85, 0.64],  # starts   x^(3)
   [0.22, 0.58, 0.33],  # with     x^(4)
   [0.77, 0.25, 0.10],  # one      x^(5)
   [0.05, 0.80, 0.55]]  # step     x^(6)
)
```

### Step 1 — Compute Unnormalized Attention Scores

The **attention score** between token $i$ and token $j$ is the dot product of their embedding vectors:

$$\omega_{ij} = x^{(i)} \cdot x^{(j)}$$

Intuition: dot product measures how aligned two vectors are. If two tokens point in similar directions in embedding space, their dot product is large — they are "similar" or "relevant" to each other.

The notebook computes scores for token 2 ("journey") as query against all six tokens:

```python
query = inputs[1]   # "journey"
attn_scores_2 = torch.empty(inputs.shape[0])
for i, x_i in enumerate(inputs):
    attn_scores_2[i] = torch.dot(x_i, query)
# Output: tensor([0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865])
```

Notice "journey" scores highest with itself (1.4950) and "starts" (1.4754) — semantically related tokens.

**Dry-run for the first score (Your · journey):**

```
x^(1) = [0.43, 0.15, 0.89]
query  = [0.55, 0.87, 0.66]

dot product = (0.43×0.55) + (0.15×0.87) + (0.89×0.66)
            = 0.2365 + 0.1305 + 0.5874
            = 0.9544 ✓
```

### Step 2 — Normalize to Attention Weights

Raw scores are not bounded — we need them to sum to 1 so they act as a proper probability distribution (a **weighted average**). The book first shows simple division:

$$\alpha_{2i} = \frac{\omega_{2i}}{\sum_j \omega_{2j}}$$

But **softmax** is preferred in practice for two reasons: it handles negative scores without producing negative weights, and its gradient properties are more suitable for backpropagation.

$$\alpha_{2i} = \text{softmax}(\omega_{2i}) = \frac{e^{\omega_{2i}}}{\sum_j e^{\omega_{2j}}}$$

```python
attn_weights_2 = torch.softmax(attn_scores_2, dim=0)
# Output: tensor([0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581])
# Sum = 1.0000 ✓
```

The convention Raschka establishes: unnormalized scores are called **attention scores** ($\omega$); after normalization, they become **attention weights** ($\alpha$).

### Step 3 — Compute Context Vector

The **context vector** $z^{(2)}$ is a weighted sum of all input vectors, where the weights are the attention weights:

$$z^{(2)} = \sum_{i=1}^{T} \alpha_{2i} \cdot x^{(i)}$$

```python
context_vec_2 = torch.zeros(query.shape)
for i, x_i in enumerate(inputs):
    context_vec_2 += attn_weights_2[i] * x_i
# Output: tensor([0.4419, 0.6515, 0.5683])
```

This is a blend of all six input vectors, but weighted so that more relevant tokens (like "starts") contribute more. The context vector for "journey" carries information about the whole sentence, with emphasis on semantically close neighbours.

### Computing All Context Vectors at Once

The pairwise dot products form a 6×6 **attention score matrix** which can be computed in one shot via matrix multiplication:

$$A = X \cdot X^T \quad \in \mathbb{R}^{T \times T}$$

```python
attn_scores = inputs @ inputs.T           # (6,3) @ (3,6) = (6,6)
attn_weights = torch.softmax(attn_scores, dim=-1)  # normalize each row
all_context_vecs = attn_weights @ inputs  # (6,6) @ (6,3) = (6,3)
```

Row $i$ of `attn_weights` holds the attention distribution for token $i$ over all tokens. Multiplying by `inputs` computes all six context vectors in one matrix multiply. The `dim=-1` in softmax means "normalize along the last dimension" — i.e., each row sums to 1.

---

## Section 3.4 — Self-Attention with Trainable Weights

The simple version above computes attention directly from the raw embeddings. There are no learnable parameters — every sentence will always produce the same attention pattern for the same inputs.

Real transformers introduce three **trainable projection matrices**: $W_Q$, $W_K$, $W_V$. Each input token is projected into three separate roles:

$$q^{(i)} = x^{(i)} W_Q \quad \text{(what am I looking for?)}$$
$$k^{(i)} = x^{(i)} W_K \quad \text{(what do I offer?)}$$
$$v^{(i)} = x^{(i)} W_V \quad \text{(what do I actually contribute?)}$$

The intuition: a query asks a question, keys are answers to that question, and values are the actual content retrieved if the key matches the query. This separation lets the network learn *what to compare* independently of *what to return*.

### Scaled Dot-Product Attention

The full formula, from "Attention Is All You Need":

$$\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

The scaling factor $\sqrt{d_k}$ prevents the dot products from growing too large in high-dimensional spaces. If $q$ and $k$ have entries drawn from $\mathcal{N}(0,1)$, their dot product has variance $d_k$. Without scaling, softmax receives very large inputs and saturates — gradients vanish and training stalls. Dividing by $\sqrt{d_k}$ normalizes the variance back to 1.

**Dry-run (d_in=3, d_out=2):**

```
x^(2) = [0.55, 0.87, 0.66]

W_query (random, seed=123):
  [[0.2961, 0.5166],
   [0.2517, 0.6886],
   [0.0740, 0.8665]]

query_2 = x^(2) @ W_query
        = 0.55×[0.2961, 0.5166]
        + 0.87×[0.2517, 0.6886]
        + 0.66×[0.0740, 0.8665]
        = [0.163, 0.284] + [0.219, 0.599] + [0.049, 0.572]
        = [0.431, 1.455]  ← matches notebook output [0.4306, 1.4551] ✓

d_k = 2,  sqrt(d_k) = 1.414
attn_scores_2 / 1.414  →  softmax  →  attn_weights_2
context_vec_2 = attn_weights_2 @ values = [0.3061, 0.8210]
```

### SelfAttention_v1 — Using nn.Parameter

The first class wraps the three weight matrices as `nn.Parameter` tensors (raw learnable parameters):

```python
class SelfAttention_v1(nn.Module):
    def __init__(self, d_in, d_out):
        super().__init__()
        self.W_query = nn.Parameter(torch.rand(d_in, d_out))
        self.W_key   = nn.Parameter(torch.rand(d_in, d_out))
        self.W_value = nn.Parameter(torch.rand(d_in, d_out))

    def forward(self, x):
        keys    = x @ self.W_key
        queries = x @ self.W_query
        values  = x @ self.W_value

        attn_scores  = queries @ keys.T
        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
        return attn_weights @ values
```

### SelfAttention_v2 — Using nn.Linear

The improved version replaces `nn.Parameter` with `nn.Linear(bias=False)`. They are mathematically equivalent — `nn.Linear` without bias is just a matrix multiplication — but `nn.Linear` uses **Kaiming uniform initialization** by default, which leads to more stable gradient flow at the start of training.

```python
class SelfAttention_v2(nn.Module):
    def __init__(self, d_in, d_out, qkv_bias=False):
        super().__init__()
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key   = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)

    def forward(self, x):
        keys    = self.W_key(x)
        queries = self.W_query(x)
        values  = self.W_value(x)

        attn_scores  = queries @ keys.T
        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
        return attn_weights @ values
```

The outputs of v1 and v2 differ numerically because the random seeds produce different weight initializations, but the architecture is identical.

---

## Section 3.5 — Causal Attention (Masking the Future)

### The Problem

The attention computed so far is **bidirectional**: when computing the context vector for token 3, the model can see tokens 4, 5, and 6 which come *after* it. This is fine for tasks like sentiment analysis, but not for language modeling.

In a language model (like GPT), the training objective is to predict the next token from all previous tokens. If the model can see future tokens, it trivially solves the prediction task by just looking ahead — it learns nothing. **Causal attention** enforces that position $i$ can only attend to positions $\leq i$.

### The Masking Strategy

The correct and efficient approach: before applying softmax, fill all above-diagonal positions with $-\infty$. Since $e^{-\infty} = 0$, softmax maps these to exactly zero — the normalization happens automatically and rows still sum to 1.

```
ASCII diagram of the mask pattern (6 tokens):

Position:     1    2    3    4    5    6
Token 1:  [score  -inf -inf -inf -inf -inf]
Token 2:  [score score -inf -inf -inf -inf]
Token 3:  [score score score -inf -inf -inf]
Token 4:  [score score score score -inf -inf]
Token 5:  [score score score score score -inf]
Token 6:  [score score score score score score]
```

The upper-triangular region is filled with $-\infty$, making the lower triangle a causal mask.

```python
mask = torch.triu(torch.ones(context_length, context_length), diagonal=1)
masked = attn_scores.masked_fill(mask.bool(), -torch.inf)
attn_weights = torch.softmax(masked / keys.shape[-1]**0.5, dim=-1)
```

`torch.triu(..., diagonal=1)` creates a matrix of ones strictly above the main diagonal. `masked_fill` replaces those positions with $-\infty$ in the score matrix.

**Why not mask after softmax?** Zeroing out attention weights after softmax breaks the sum-to-1 invariant — you'd then need to renormalize each row manually. Masking *before* softmax lets softmax do the normalization correctly in one pass.

### Dropout on Attention Weights

After masking and softmax, **dropout** is applied to the attention weights themselves (not to the final output). During training, each weight has a probability $p$ of being set to zero. The remaining weights are scaled by $\frac{1}{1-p}$ to preserve the expected sum.

Why: dropout on attention weights randomly disrupts which tokens attend to which others, preventing the model from over-relying on any particular attention pattern.

```python
torch.manual_seed(123)
dropout = torch.nn.Dropout(0.5)
print(dropout(attn_weights))
```

With `p=0.5`, roughly half the weights become zero and the survivors are doubled (scaled by 2 to preserve expectation). In practice, GPT-2 uses `dropout=0.1`.

### CausalAttention Class

The full class handles **batched input** (shape `[batch, seq_len, d_in]`) and uses `register_buffer` for the mask so it moves to GPU automatically with the model:

```python
class CausalAttention(nn.Module):
    def __init__(self, d_in, d_out, context_length, dropout, qkv_bias=False):
        super().__init__()
        self.d_out    = d_out
        self.W_query  = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key    = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value  = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.dropout  = nn.Dropout(dropout)
        self.register_buffer(
            'mask',
            torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape      # unpack batch dimension
        keys    = self.W_key(x)            # (b, T, d_out)
        queries = self.W_query(x)
        values  = self.W_value(x)

        # (b, T, d_out) @ (b, d_out, T) = (b, T, T)  — one score matrix per batch item
        attn_scores = queries @ keys.transpose(1, 2)
        attn_scores.masked_fill_(self.mask.bool()[:num_tokens, :num_tokens], -torch.inf)

        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
        attn_weights = self.dropout(attn_weights)

        return attn_weights @ values       # (b, T, d_out)
```

The key shape change from v1/v2: `keys.transpose(1, 2)` swaps dimensions 1 and 2 (seq_len and d_out), making the matrix multiply work along the token dimension for each batch item simultaneously. `transpose(0, 1)` would swap batch and seq_len — wrong.

The test uses `batch = torch.stack((inputs, inputs), dim=0)` which creates a batch of size 2 by stacking the same `inputs` twice. Output shape is `[2, 6, 2]` — two batch items, six tokens each, 2-dimensional context vectors.

---

## Section 3.6 — Multi-Head Attention

### Why Multiple Heads?

A single attention head produces one weighted combination of values — it learns one way of relating tokens. **Multi-head attention** runs several attention mechanisms in parallel, each with its own $W_Q$, $W_K$, $W_V$ projections. Each head can learn a different type of relationship: one head might track syntactic dependencies, another tracks coreference, another tracks proximity.

The outputs of all heads are concatenated and projected back to the model dimension.

```
Architecture:

Input x (b, T, d_in)
       │
   ┌───┴────────────────────────────┐
   │                                │
[Head 1]                        [Head 2]
W_q1, W_k1, W_v1              W_q2, W_k2, W_v2
   │  CausalAttention              │  CausalAttention
   │  → (b, T, d_out)              │  → (b, T, d_out)
   └──────────────┬─────────────────┘
                  │  torch.cat(dim=-1)
              (b, T, 2×d_out)
```

### MultiHeadAttentionWrapper — Naive Stacking

The first implementation simply creates `num_heads` separate `CausalAttention` modules in an `nn.ModuleList` and concatenates their outputs:

```python
class MultiHeadAttentionWrapper(nn.Module):
    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        self.heads = nn.ModuleList(
            [CausalAttention(d_in, d_out, context_length, dropout, qkv_bias)
             for _ in range(num_heads)]
        )

    def forward(self, x):
        return torch.cat([head(x) for head in self.heads], dim=-1)
```

With `num_heads=2, d_out=2`, output shape is `(2, 6, 4)` — four dimensions because two heads each contribute two dimensions. **Drawback**: runs each head sequentially in the Python loop; cannot parallelize.

### MultiHeadAttention — Efficient Weight Split

The production implementation uses a single set of weight matrices for all heads combined and splits them using `view` + `transpose`:

```python
class MultiHeadAttention(nn.Module):
    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        assert d_out % num_heads == 0, "d_out must be divisible by num_heads"

        self.d_out    = d_out
        self.num_heads = num_heads
        self.head_dim  = d_out // num_heads   # dimension per head

        self.W_query  = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key    = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value  = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.out_proj = nn.Linear(d_out, d_out)   # final projection
        self.dropout  = nn.Dropout(dropout)
        self.register_buffer(
            "mask",
            torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape

        # Project all tokens to full d_out dimension
        keys    = self.W_key(x)    # (b, T, d_out)
        queries = self.W_query(x)
        values  = self.W_value(x)

        # Reshape to split d_out into (num_heads, head_dim)
        # (b, T, d_out) → (b, T, num_heads, head_dim)
        keys    = keys.view(b, num_tokens, self.num_heads, self.head_dim)
        queries = queries.view(b, num_tokens, self.num_heads, self.head_dim)
        values  = values.view(b, num_tokens, self.num_heads, self.head_dim)

        # Move heads to batch dimension for parallel computation
        # (b, T, num_heads, head_dim) → (b, num_heads, T, head_dim)
        keys    = keys.transpose(1, 2)
        queries = queries.transpose(1, 2)
        values  = values.transpose(1, 2)

        # Attention scores: (b, num_heads, T, head_dim) @ (b, num_heads, head_dim, T)
        #                 = (b, num_heads, T, T)
        attn_scores = queries @ keys.transpose(2, 3)

        mask_bool = self.mask.bool()[:num_tokens, :num_tokens]
        attn_scores.masked_fill_(mask_bool, -torch.inf)

        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # (b, num_heads, T, head_dim) → (b, T, num_heads, head_dim)
        context_vec = (attn_weights @ values).transpose(1, 2)

        # Merge heads: (b, T, num_heads, head_dim) → (b, T, d_out)
        context_vec = context_vec.contiguous().view(b, num_tokens, self.d_out)

        # Final linear projection (optional but standard)
        context_vec = self.out_proj(context_vec)
        return context_vec
```

### The Shape Journey — Traced Step by Step

For `b=2, T=6, d_in=3, d_out=2, num_heads=2, head_dim=1`:

```
Input x:           (2, 6, 3)
After W_query:     (2, 6, 2)     ← project to d_out
After .view():     (2, 6, 2, 1)  ← split d_out into (num_heads, head_dim)
After .transpose(1,2): (2, 2, 6, 1)  ← move num_heads to batch dimension

attn_scores = queries @ keys.transpose(2,3)
            = (2, 2, 6, 1) @ (2, 2, 1, 6)
            = (2, 2, 6, 6)  ← one (T×T) score matrix per head per batch item

After softmax + dropout:   (2, 2, 6, 6)
attn_weights @ values:
  (2, 2, 6, 6) @ (2, 2, 6, 1) = (2, 2, 6, 1)

After .transpose(1,2):     (2, 6, 2, 1)
After .view(b, T, d_out):  (2, 6, 2)     ← merge heads
After out_proj:            (2, 6, 2)     ← final projection
```

The 4D `queries @ keys.transpose(2, 3)` is demonstrated explicitly in cells 139–141: PyTorch broadcasts the matmul across the first two dimensions (batch and heads) and computes the `(T, head_dim) @ (head_dim, T)` multiply independently for each head. This is equivalent to running all heads simultaneously on the GPU — no Python loop.

### The out_proj Layer

After concatenating (or merging via reshape) the head outputs, a final linear layer `out_proj` mixes information across heads. Intuitively, each head has learned to represent a different aspect of the input; `out_proj` learns how to combine those aspects into a coherent output representation. Raschka notes this layer is standard convention but recent research suggests it can sometimes be removed without significant performance loss.

### Difference Between the Two Implementations

| Property | MultiHeadAttentionWrapper | MultiHeadAttention |
|---|---|---|
| Weight matrices | Separate per head | Single shared, split by reshape |
| Computation | Sequential Python loop | Parallel via batched matmul |
| Output shape | (b, T, d_out × num_heads) | (b, T, d_out) |
| Has out_proj | No | Yes |
| Used in GPT | No | Yes |

Setting `d_out=4` in `MultiHeadAttention` (with `num_heads=2`) would produce the same output shape as `MultiHeadAttentionWrapper` with `d_out=2`. The difference in the notebook is just that Raschka keeps `d_out=2` in the efficient version, giving `(2, 6, 2)` output vs `(2, 6, 4)`.

---

## Summary — What Was Built and Why

The notebook builds five increasingly capable classes:

```
SimpleDotProduct (implicit, 3.3)
       ↓ add trainable W_Q, W_K, W_V
SelfAttention_v1  (nn.Parameter)
       ↓ better initialization
SelfAttention_v2  (nn.Linear)
       ↓ add causal mask + dropout + batch support
CausalAttention
       ↓ run in parallel with separate weights
MultiHeadAttentionWrapper
       ↓ merge into single efficient implementation
MultiHeadAttention   ← this is what GPT uses
```

The `MultiHeadAttention` class from this chapter will be plugged directly into the GPT-2 architecture in Chapter 4. The three design decisions that distinguish it from naive self-attention are:

1. **Trainable projections** ($W_Q$, $W_K$, $W_V$): separates what-to-search-for from what-to-return, making attention learnable.
2. **Causal masking**: enforces autoregressive generation — the model cannot cheat by looking at future tokens.
3. **Multiple heads with weight splitting**: lets the model attend to multiple types of relationships simultaneously, computed efficiently as batched matrix operations.
