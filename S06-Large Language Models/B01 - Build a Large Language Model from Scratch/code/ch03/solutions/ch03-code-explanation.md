# Chapter 3 — Coding Attention Mechanisms

This chapter builds the single most important mechanism in modern deep learning: **self-attention**, and its practical form, **multi-head attention**. Everything here is pure PyTorch — no `nn.Transformer`, no shortcuts. We start from a parameter-free toy version that just measures "how similar are these two word vectors?", and by the end of the chapter we have a fully batched, causally-masked, dropout-regularized, multi-head attention module that is _exactly_ the block GPT-style models stack 12, 24, or 96 times.

The reference notebook is `ch03-coding-attention-mechanisms-solution-solved.ipynb`. Five classes in that notebook are left as exercises in the practice template (`SelfAttention_v1`, `SelfAttention_v2`, `CausalAttention`, `MultiHeadAttentionWrapper`, `MultiHeadAttention`); this document explains the canonical implementations of all five, with real numbers produced by actually running the code.

---

## Table of Contents

0. [Setup](#0-setup)
1. [3.1 & 3.2 — Why Attention? From RNN Bottlenecks to Self-Attention](#1-31--32--why-attention-from-rnn-bottlenecks-to-self-attention)
2. [3.3.1 — A Simple Self-Attention Mechanism Without Trainable Weights](#2-331--a-simple-self-attention-mechanism-without-trainable-weights)
3. [3.3.2 — Computing Attention Weights for All Input Tokens](#3-332--computing-attention-weights-for-all-input-tokens)
4. [3.4.1 — Self-Attention with Trainable Weights: Q, K, V](#4-341--self-attention-with-trainable-weights-q-k-v)
5. [3.4.2 — `SelfAttention_v1` and `SelfAttention_v2`](#5-342--selfattention_v1-and-selfattention_v2)
6. [3.5.1 — Causal Attention: Hiding Future Words](#6-351--causal-attention-hiding-future-words)
7. [3.5.2 — Masking with Dropout](#7-352--masking-with-dropout)
8. [3.5.3 — `CausalAttention`: A Compact Causal Attention Class](#8-353--causalattention-a-compact-causal-attention-class)
9. [3.6.1 — `MultiHeadAttentionWrapper`: Stacking Heads](#9-361--multiheadattentionwrapper-stacking-heads)
10. [3.6.2 — `MultiHeadAttention`: The Efficient, Production Implementation](#10-362--multiheadattention-the-efficient-production-implementation)
11. [Putting It All Together & Where This Leads](#11-putting-it-all-together--where-this-leads)

---

## 0 — Setup

The whole chapter runs in pure PyTorch:

```python
import torch
print("PyTorch version:", torch.__version__)
# PyTorch version: 2.12.0+cu130
```

Every example in this chapter operates on one fixed sentence, embedded as 3-dimensional vectors (in the real GPT model these would be 768+ dimensional, but 3 dimensions let us print and reason about every number by hand):

```python
inputs = torch.tensor(
  [[0.43, 0.15, 0.89], # Your     (x^1)
   [0.55, 0.87, 0.66], # journey  (x^2)
   [0.57, 0.85, 0.64], # starts   (x^3)
   [0.22, 0.58, 0.33], # with     (x^4)
   [0.77, 0.25, 0.10], # one      (x^5)
   [0.05, 0.80, 0.55]] # step     (x^6)
)
print("inputs.shape:", inputs.shape)
# inputs.shape: torch.Size([6, 3])
```

Six tokens (`Your journey starts with one step`), each represented by a 3-dimensional embedding vector. We will use this exact tensor — and especially the second row, `journey` — as the running example for the entire chapter.

---

## 1 — 3.1 & 3.2 — Why Attention? From RNN Bottlenecks to Self-Attention

**Summary**: Self-attention lets every word in a sentence directly look at every other word and decide how relevant each one is, instead of being forced through a single compressed "memory" vector.

**The problem it solves**: Before attention, sequence-to-sequence models (encoder-decoder RNNs) worked by squeezing an entire input sentence into one fixed-size context vector at the end of the encoder, and then asking the decoder to generate the whole output sentence from that single vector. This is like reading an entire paragraph, closing the book, and then trying to write a translation from memory alone — fine for a short sentence, but for a 50-word sentence, information about the _first_ word has been overwritten many times by the time the encoder reaches the _last_ word. Long-range dependencies get lost.

**The intuition**: Attention removes the bottleneck by giving the decoder access to _all_ of the encoder's hidden states, not just the last one, and lets it learn — for each word it's about to produce — which input words matter most right now. Think of it like a search engine: when generating the German word for "started", the model doesn't need to remember the whole sentence equally; it can "search" the input and find that "starts" is the most relevant word, "journey" is somewhat relevant (it's the subject), and "Your" is barely relevant at all.

**Self-attention** takes this one step further: instead of relating a _decoder_ word to _encoder_ words (cross-attention), it relates words _within the same sequence_ to each other. "Self" means the queries, keys, and values all come from the same input sequence. This is the mechanism that powers GPT: when processing the word "it" in "The animal didn't cross the street because it was too tired", self-attention lets the model figure out that "it" refers to "animal" by directly attending to that word's embedding, regardless of how far away it is in the sentence.

The rest of this chapter builds self-attention up in four stages of increasing sophistication:

```
Stage 1 (3.3.1)  Simple attention, no weights      → just dot products of embeddings
Stage 2 (3.4)    Trainable Q, K, V projections     → scaled dot-product attention
Stage 3 (3.5)    + Causal mask + dropout           → GPT can't "cheat" by looking ahead
Stage 4 (3.6)    + Multiple heads in parallel      → multi-head attention (the real thing)
```

---

## 2 — 3.3.1 — A Simple Self-Attention Mechanism Without Trainable Weights

**Summary**: Before introducing any learnable parameters, we compute a "context vector" for the word "journey" by measuring how similar its embedding is to every other word's embedding (via dot product), turning those similarities into weights that sum to 1, and using those weights to blend all the word embeddings together.

**The problem it solves**: A plain embedding for "journey" is _static_ — it's the same vector no matter what sentence it appears in. But the meaning of "journey" should shift slightly depending on context ("journey" in "Your journey starts" vs. "journey" in "a journey through time"). A **context vector** is an embedding that has been _enriched_ by mixing in information from the surrounding words, weighted by relevance.

**The intuition**: Imagine you're trying to describe the word "journey" to someone, but you're only allowed to do it by pointing at other words in the sentence and saying "it's a bit like this one, mostly like that one, and a little like this other one." The dot product is your "bit like" measurement — two vectors that point in similar directions have a large dot product (they're "similar"), and two vectors pointing in different directions have a small or negative dot product (they're "dissimilar"). Words that are "similar" to "journey" (in this raw, untrained sense) get a bigger say in the final blended representation.

### Step 1 — Attention scores via dot product

We pick `journey` (index 1, so `x^(2)` in 1-indexed math notation) as our **query**. We compute its dot product against every word in the sentence, including itself:

**Layer 2 — Math**: For query vector $x^{(2)}$ and every input vector $x^{(i)}$, the unnormalized attention score is

$$\omega_{2i} = x^{(2)} \cdot x^{(i)} = \sum_{d=1}^{3} x^{(2)}_d \, x^{(i)}_d$$

Here $\omega_{2i}$ ("omega") is the raw attention score between query token 2 and key token $i$, and the sum runs over the 3 embedding dimensions.

You are completely right to call me out. When you are meticulously documenting complex ML models and architectures, you need the full depth of the explanation preserved in your reference material, not just a condensed summary. I over-edited trying to match the visual length of your original file instead of giving you the comprehensive breakdown you actually needed.

Here is the fully expanded version with the table, the code breakdown, and the sanity check, formatted exactly so you can drop it straight into your markdown file:

---

**Layer 3 — Dry run: Measuring Word Similarity**

At this stage, the mechanism of "attention" is essentially asking: _"If I am currently looking at the word 'journey', how much attention should I pay to the word 'Your'?"_ We measure this similarity using a **dot product**—multiplying matching dimensions and summing the results. A higher dot product means the vectors point in roughly the same direction.

Take $x^{(2)} = [0.55, 0.87, 0.66]$ (the word "journey") and $x^{(1)} = [0.43, 0.15, 0.89]$ (the word "Your"):

```text
ω_21 = (0.55 × 0.43) + (0.87 × 0.15) + (0.66 × 0.89)
     = 0.2365 + 0.1305 + 0.5874
     = 0.9544

```

**Automating the Math in PyTorch**

Instead of calculating this by hand for every word, the PyTorch code automates it. The script isolates the query word (`inputs[1]`), then loops through the entire sentence. For every word in the sentence (`x_i`), it runs `torch.dot(x_i, query)`.

```python
query = inputs[1]  # "journey", x^(2)

attn_scores_2 = torch.empty(inputs.shape[0])
for i, x_i in enumerate(inputs):
    attn_scores_2[i] = torch.dot(x_i, query)

print(attn_scores_2)
# tensor([0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865])

```

**Decoding the Output**

When you print `attn_scores_2`, here is what those numbers actually represent when mapped back to the original sentence:

| Word Index  | Word    | Raw Score vs. "journey"                                |
| ----------- | ------- | ------------------------------------------------------ |
| `inputs[0]` | Your    | **0.9544** (The exact manual calculation we did above) |
| `inputs[1]` | journey | **1.4950**                                             |
| `inputs[2]` | starts  | **1.4754**                                             |
| `inputs[3]` | with    | **0.8434**                                             |
| `inputs[4]` | one     | **0.7070**                                             |
| `inputs[5]` | step    | **1.0865**                                             |

Notice the highest scores:

- **1.4950** (`inputs[1]`, "journey" vs. itself): A vector is perfectly aligned with itself, yielding the maximum possible similarity.
- **1.4754** (`inputs[2]`, "starts" vs. "journey"): These trained embeddings happen to point in very similar directions compared to words like "one" (0.7070) or "with" (0.8434).

This raw dot product calculation is the foundational engine that allows the model to "know" which words to pay attention to _before_ any trainable weights are introduced.

**The Sanity Check Explained**

The manual `for` loop is included to prove that PyTorch isn't doing any hidden magic behind the scenes. It computes the dot product using standard Python to show it produces the exact same result as the highly optimized `torch.dot()` function.

```python
# Manual sanity check:
res = 0.  # Create an empty bucket to keep a running total

for idx, element in enumerate(inputs[0]):
    # Loop 1 (idx=0): res = 0 + (0.43 * 0.55)
    # Loop 2 (idx=1): res = 0.2365 + (0.15 * 0.87)
    # Loop 3 (idx=2): res = 0.3670 + (0.89 * 0.66)
    res += inputs[0][idx] * query[idx]

print(res)                              # tensor(0.9544)
print(torch.dot(inputs[0], query))      # tensor(0.9544)

```

For every step in the loop, it takes the number at position `idx` in the "Your" vector, multiplies it by the number at the exact same position in the `query` vector ("journey"), and adds that result to the running total. The final `res` output is exactly **0.9544**, confirming the math is identical.

### Step 2 — Normalizing the scores into weights

Raw dot products can be any real number (negative, large, small). For them to act as a sensible "blend ratio", they need to (a) sum to 1, and (b) ideally all be positive. Two ways to do this:

**Naive sum-normalization**:

$$\alpha_{2i} = \frac{\omega_{2i}}{\sum_{j=1}^{6} \omega_{2j}}$$

```python
attn_weights_2_tmp = attn_scores_2 / attn_scores_2.sum()
print("Attention weights:", attn_weights_2_tmp)
# tensor([0.1455, 0.2278, 0.2249, 0.1285, 0.1077, 0.1656])
print("Sum:", attn_weights_2_tmp.sum())
# tensor(1.0000)
```

**Softmax normalization** (the one actually used everywhere):

$$\alpha_{2i} = \text{softmax}(\omega_{2i}) = \frac{e^{\omega_{2i}}}{\sum_{j=1}^{6} e^{\omega_{2j}}}$$

```python
def softmax_naive(x):
    return torch.exp(x) / torch.exp(x).sum(dim=0)

attn_weights_2_naive = softmax_naive(attn_scores_2)
print("Attention weights:", attn_weights_2_naive)
# tensor([0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581])
print("Sum:", attn_weights_2_naive.sum())
# tensor(1.)

attn_weights_2 = torch.softmax(attn_scores_2, dim=0)
print("Attention weights:", attn_weights_2)
# tensor([0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581])
print("Sum:", attn_weights_2.sum())
# tensor(1.)
```

**Why softmax instead of plain division?** Two reasons. First, the exponential `e^x` is _always positive_, so softmax guarantees every weight is in `(0, 1)` even if some raw scores are negative — plain sum-normalization would break (or produce negative "weights") if any score were negative. Second, softmax is differentiable everywhere and has well-behaved gradients, which matters once these weights are produced by a trainable network. `torch.softmax` is the production version (numerically stable for large/small values via internal max-subtraction); `softmax_naive` is shown only to demystify what's happening — both produce identical results here because our numbers are small.

### Step 3 — The context vector

The context vector $z^{(2)}$ is the weighted sum of _all_ input vectors, using the attention weights as the mixing coefficients:

$$z^{(2)} = \sum_{i=1}^{6} \alpha_{2i} \, x^{(i)}$$

**Layer 3 — Dry run** (just the first dimension, to keep it short): the first coordinates of the six input vectors are `[0.43, 0.55, 0.57, 0.22, 0.77, 0.05]`, and the weights are `[0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581]`:

```
z^(2)_1 = 0.1385×0.43 + 0.2379×0.55 + 0.2333×0.57
        + 0.1240×0.22 + 0.1082×0.77 + 0.1581×0.05
        = 0.0596 + 0.1308 + 0.1330 + 0.0273 + 0.0833 + 0.0079
        = 0.4419
```

```python
query = inputs[1]  # "journey"
context_vec_2 = torch.zeros(query.shape)
for i, x_i in enumerate(inputs):
    context_vec_2 += attn_weights_2[i] * x_i

print(context_vec_2)
# tensor([0.4419, 0.6515, 0.5683])
```

The original embedding for "journey" was `[0.55, 0.87, 0.66]`; its _context-aware_ version is `[0.4419, 0.6515, 0.5683]` — a blend dominated by "journey" itself and "starts" (the two largest weights), with smaller contributions from every other word.

---

## 3 — 3.3.2 — Computing Attention Weights for All Input Tokens

**Summary**: We just computed one context vector (for "journey"). To build a full self-attention layer we need a context vector for _every_ token, which means computing a full 6×6 grid of attention scores — and this entire grid can be computed with a single matrix multiplication.

### Step 1 — All pairwise scores

**Layer 1 — Intuition**: Stage 2 above only asked "how does _journey_ relate to everything else?" Now we ask that same question for _every_ word simultaneously: "how does _Your_ relate to everything else? How does _step_ relate to everything else?" — and so on, for all 6 words. The result is a 6×6 table where entry `(i, j)` answers "how relevant is token `j` to token `i`?"

**Layer 2 — Math**: For all $i, j \in \{1, \dots, 6\}$,

$$\omega_{ij} = x^{(i)} \cdot x^{(j)} \quad\Longleftrightarrow\quad \Omega = X X^T$$

where $X \in \mathbb{R}^{6\times 3}$ is the whole `inputs` matrix and $\Omega \in \mathbb{R}^{6\times 6}$ is the matrix of all pairwise dot products. Matrix multiplication $X X^T$ computes _exactly_ the dot product of every row of $X$ with every row of $X^T$ (= every row of $X$) — i.e. every pairwise dot product, all at once.

```python
# Slow version: nested loop
attn_scores = torch.empty(6, 6)
for i, x_i in enumerate(inputs):
    for j, x_j in enumerate(inputs):
        attn_scores[i, j] = torch.dot(x_i, x_j)

# Fast version: one matmul, identical result
attn_scores = inputs @ inputs.T
print(attn_scores)
# tensor([[0.9995, 0.9544, 0.9422, 0.4753, 0.4576, 0.6310],
#         [0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865],
#         [0.9422, 1.4754, 1.4570, 0.8296, 0.7154, 1.0605],
#         [0.4753, 0.8434, 0.8296, 0.4937, 0.3474, 0.6565],
#         [0.4576, 0.7070, 0.7154, 0.3474, 0.6654, 0.2935],
#         [0.6310, 1.0865, 1.0605, 0.6565, 0.2935, 0.9450]])
```

Row 1 of this matrix (index 1, 0-indexed) is exactly `attn_scores_2` from Section 2 — `[0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865]`. The matmul version just computes all 6 rows of that calculation in parallel.

### Step 2 — Softmax over each row

We apply softmax along `dim=-1` (the last dimension, i.e. across each row), so that _each row_ of weights sums to 1 — each token gets its own independent probability distribution over "which tokens matter to me".

```python
attn_weights = torch.softmax(attn_scores, dim=-1)
print(attn_weights)
# tensor([[0.2098, 0.2006, 0.1981, 0.1242, 0.1220, 0.1452],
#         [0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581],
#         [0.1390, 0.2369, 0.2326, 0.1242, 0.1108, 0.1565],
#         [0.1435, 0.2074, 0.2046, 0.1462, 0.1263, 0.1720],
#         [0.1526, 0.1958, 0.1975, 0.1367, 0.1879, 0.1295],
#         [0.1385, 0.2184, 0.2128, 0.1420, 0.0988, 0.1896]])

print("All row sums:", attn_weights.sum(dim=-1))
# tensor([1., 1., 1., 1., 1., 1.])
```

`dim=-1` is critical here: `attn_scores` is a 6×6 _square_ matrix, so it's easy to accidentally apply softmax down columns (`dim=0`) instead of across rows (`dim=-1`) and not notice the bug because the shape doesn't change. The semantic meaning is: row `i` = "token `i`'s attention distribution over all tokens (including itself)", and that distribution is what must sum to 1.

### Step 3 — All context vectors

$$Z = A X, \qquad Z \in \mathbb{R}^{6\times 3}$$

where $A$ is the 6×6 attention-weight matrix and $X$ is the 6×3 input matrix. Each row of $Z$ is one token's context vector — a weighted blend of all 6 input embeddings, using that token's own row of attention weights.

```python
all_context_vecs = attn_weights @ inputs
print(all_context_vecs)
# tensor([[0.4421, 0.5931, 0.5790],
#         [0.4419, 0.6515, 0.5683],
#         [0.4431, 0.6496, 0.5671],
#         [0.4304, 0.6298, 0.5510],
#         [0.4671, 0.5910, 0.5266],
#         [0.4177, 0.6503, 0.5645]])

print("Previous 2nd context vector:", context_vec_2)
# tensor([0.4419, 0.6515, 0.5683])
```

Row 1 of `all_context_vecs` (`[0.4419, 0.6515, 0.5683]`) is **identical** to `context_vec_2` computed by hand in Section 2 — confirming that the matrix formulation $Z = \text{softmax}(XX^T)X$ is just a vectorized version of the loop-based calculation, applied to every token at once.

**Gotcha**: This entire section uses **no trainable parameters** — `Q`, `K`, and `V` are all literally just `inputs` itself. This is a useful pedagogical stepping stone, but it has a fundamental limitation: the model has no way to _learn_ what "relevant" means. The next section fixes this by introducing three trainable projection matrices.

---

## 4 — 3.4.1 — Self-Attention with Trainable Weights: Q, K, V

**Summary**: We introduce three trainable weight matrices — $W_q$, $W_k$, $W_v$ — that project each input embedding into a **query**, **key**, and **value** vector. Attention scores become _query · key_ dot products (instead of _input · input_), and the context vector becomes a weighted sum of _value_ vectors (instead of raw inputs). We also introduce **scaling by $\sqrt{d_k}$**, which is essential for stable training.

**The problem it solves**: In Section 3, the same vector $x^{(i)}$ played three different roles simultaneously — it was compared against other tokens (as a "key"), it was the thing being compared (as a "query"), and it was the thing being blended into the output (as a "value"). Forcing one vector to serve three roles is restrictive. By learning three _separate_ linear projections, the model can learn, e.g., "the query representation of a word should emphasize what it's _looking for_, the key representation should emphasize what it _offers_, and the value representation should emphasize what it _contributes_ to the output" — three different, independently-learnable views of the same word.

**The intuition**: Think of this like a library search system. Every book has (1) a **query** — not really, books don't search — okay, better analogy: think of a video recommendation system. _Query_ = "what kind of video is this user looking for right now" (derived from their watch history). _Key_ = "what is this candidate video about" (a tag/embedding for each video in the catalog). _Value_ = "the actual content of the video that gets shown to the user". The match score between a user and a video is `query · key` (how well does what the user wants match what this video offers?), but the thing that actually gets _returned_ to the user is the _value_. Query, key, and value being separate learned projections is what lets "what I'm looking for" and "what I have to offer" and "what I actually contain" be different things.

### Step 1 — Project inputs into Q, K, V

We work through this with `x_2 = inputs[1]` ("journey") as the query, with `d_in = 3` (embedding dimension of the input) and `d_out = 2` (embedding dimension of Q/K/V — kept small here so we can print everything; in GPT-2 this would be 768).

```python
x_2 = inputs[1]
d_in = inputs.shape[1]   # 3, the input embedding size
d_out = 2                # the output embedding size (d_out = d_in in GPT, but kept small here)

torch.manual_seed(123)
W_query = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
W_key   = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
W_value = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
```

These produce the following 3×2 matrices:

```
W_query = [[0.2961, 0.5166],     W_key = [[0.1366, 0.1025],     W_value = [[0.0756, 0.1966],
           [0.2517, 0.6886],               [0.1841, 0.7264],               [0.3164, 0.4017],
           [0.0740, 0.8665]]               [0.3153, 0.6871]]               [0.1186, 0.8274]]
```

(`requires_grad=False` here only because we're hand-computing values for inspection — in a real model these would be trainable parameters, exactly what `nn.Linear` gives us in Section 5.)

```python
query_2 = x_2 @ W_query
key_2   = x_2 @ W_key
value_2 = x_2 @ W_value
print(query_2)  # tensor([0.4306, 1.4551])

keys = inputs @ W_key
values = inputs @ W_value
print("keys.shape:", keys.shape)      # torch.Size([6, 2])
print("values.shape:", values.shape)  # torch.Size([6, 2])
```

**Layer 3 — Dry run** for `query_2`: $x^{(2)} = [0.55, 0.87, 0.66]$, and $W_q$'s first column is $[0.2961, 0.2517, 0.0740]$:

```
query_2[0] = 0.55×0.2961 + 0.87×0.2517 + 0.66×0.0740
           = 0.1629 + 0.2190 + 0.0488
           = 0.4306   ✓ matches query_2[0] = 0.4306
```

The full `keys` and `values` matrices (6×2 each, one row per token):

```
keys   = [[0.3669, 0.7646],      values = [[0.1855, 0.8812],
          [0.4433, 1.1419],                 [0.3951, 1.0037],
          [0.4361, 1.1156],                 [0.3879, 0.9831],
          [0.2408, 0.6706],                 [0.2393, 0.5493],
          [0.1827, 0.3292],                 [0.1492, 0.3346],
          [0.3275, 0.9642]]                 [0.3221, 0.7863]]
```

### Step 2 — Attention score: query · key

```python
keys_2 = keys[1]
attn_score_22 = query_2.dot(keys_2)
print(attn_score_22)  # tensor(1.8524)

attn_scores_2 = query_2 @ keys.T
print(attn_scores_2)
# tensor([1.2705, 1.8524, 1.8111, 1.0795, 0.5577, 1.5440])
```

This is the same idea as Section 3's $\omega_{2i} = x^{(2)} \cdot x^{(i)}$, except now both sides are _projected_ vectors: $\omega_{2i} = q^{(2)} \cdot k^{(i)}$.

### Step 3 — Scaling by $\sqrt{d_k}$ (the most important new idea)

> **Why do we divide by $\sqrt{d_k}$ before softmax?**

**Summary**: We scale attention scores down by $\sqrt{d_k}$ (where $d_k$ is the dimensionality of the key/query vectors) before applying softmax, to prevent the dot products from growing too large in magnitude.

**The problem it solves**: When $d_k$ is large (e.g. 768 in GPT-2, or even just our toy $d_k=2$), the dot product $q \cdot k = \sum_{d=1}^{d_k} q_d k_d$ is a sum of $d_k$ terms — and the larger $d_k$ is, the larger the _magnitude_ of this sum tends to be, simply because there are more terms being added together. Large raw scores pushed into softmax produce an extremely "peaked" distribution — one weight close to 1 and all others close to 0 — and in that regime, the gradient of softmax with respect to its inputs is nearly zero almost everywhere ("saturation"). A nearly-zero gradient means backpropagation can barely update $W_q$ and $W_k$ — training stalls.

**The intuition**: Imagine rating how much you like 6 movies on a scale from 1–5 vs. a scale from 1–1000. On the 1–5 scale, your ratings `[3, 5, 4, 2, 1, 4]` produce a fairly "spread out" softmax — several movies get meaningful probability. But if you instead use scores `[300, 500, 400, 200, 100, 400]` (same relative ordering, just bigger numbers), softmax will assign _almost all_ probability to the single highest score (500) and essentially zero to everything else — even though the _relative preferences_ are identical to the 1–5 case! Dividing by a constant brings the scores back to a "1–5"-like range where softmax produces a sensibly spread-out distribution that still respects the relative ordering.

**Layer 2 — Math**: If the entries of $q$ and $k$ are independent random variables with mean 0 and variance 1 (a reasonable assumption right after random initialization), then for the dot product $q \cdot k = \sum_{d=1}^{d_k} q_d k_d$:

$$\text{Var}(q \cdot k) = \sum_{d=1}^{d_k} \text{Var}(q_d k_d) = \sum_{d=1}^{d_k} \text{Var}(q_d)\,\text{Var}(k_d) = \sum_{d=1}^{d_k} 1 \cdot 1 = d_k$$

So the variance of the raw dot product _grows linearly with $d_k$_ — and its standard deviation grows with $\sqrt{d_k}$. Dividing every score by $\sqrt{d_k}$ brings the variance back down to exactly 1, regardless of how large $d_k$ is:

$$\text{Var}\left(\frac{q\cdot k}{\sqrt{d_k}}\right) = \frac{\text{Var}(q\cdot k)}{d_k} = \frac{d_k}{d_k} = 1$$

This is exactly the **scaled dot-product attention** formula from "Attention Is All You Need":

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

**Layer 3 — Dry run** with our actual numbers, $d_k = 2$ so $\sqrt{d_k} = \sqrt{2} \approx 1.4142$:

```
attn_scores_2 = [1.2705, 1.8524, 1.8111, 1.0795, 0.5577, 1.5440]

scaled = attn_scores_2 / sqrt(2):
  1.2705 / 1.4142 = 0.8984
  1.8524 / 1.4142 = 1.3098
  1.8111 / 1.4142 = 1.2806
  1.0795 / 1.4142 = 0.7633
  0.5577 / 1.4142 = 0.3944
  1.5440 / 1.4142 = 1.0918
```

```python
d_k = keys.shape[-1]  # 2
attn_weights_2 = torch.softmax(attn_scores_2 / d_k**0.5, dim=-1)
print(attn_weights_2)
# tensor([0.1500, 0.2264, 0.2199, 0.1311, 0.0906, 0.1820])
```

**Why $\sqrt{d_k}$ and not, say, $d_k$ itself?** Because we computed $\text{Var}(q\cdot k) = d_k$ — to bring the variance back to 1, we divide the _standard deviation_, $\sqrt{d_k}$, not the variance. (Dividing the scores by $d_k$ would _over_-correct, shrinking the variance to $1/d_k$ instead of 1.)

### Step 4 — Context vector via value vectors

$$z^{(2)} = \sum_{i=1}^{6} \alpha_{2i} \, v^{(i)} \quad\Longleftrightarrow\quad z^{(2)} = \alpha_2 V$$

```python
context_vec_2 = attn_weights_2 @ values
print(context_vec_2)
# tensor([0.3061, 0.8210])
```

Note this is a _different_ number from Section 2's `context_vec_2 = [0.4419, 0.6515, 0.5683]` — that's expected and correct! Here, the context vector lives in the $d_{out}=2$ dimensional **value space**, not the original $d_{in}=3$ dimensional input space, and it's computed using _learned_ (here, randomly-initialized) projections rather than raw inputs.

---

## 5 — 3.4.2 — `SelfAttention_v1` and `SelfAttention_v2`

This section packages the four steps from Section 4 into reusable `nn.Module` classes. Both classes implement the _exact same algorithm_; the difference is purely in how the weight matrices $W_q, W_k, W_v$ are stored and initialized.

### `SelfAttention_v1`: raw `nn.Parameter` matrices

```python
import torch.nn as nn

class SelfAttention_v1(nn.Module):
    """First version of self-attention, using raw nn.Parameter matrices
    for the query, key, and value projections.
    """
    def __init__(self, d_in, d_out):
        super().__init__()
        self.W_query = nn.Parameter(torch.rand(d_in, d_out))
        self.W_key   = nn.Parameter(torch.rand(d_in, d_out))
        self.W_value = nn.Parameter(torch.rand(d_in, d_out))

    def forward(self, x):
        queries = x @ self.W_query
        keys    = x @ self.W_key
        values  = x @ self.W_value

        attn_scores = queries @ keys.T
        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)

        context_vec = attn_weights @ values
        return context_vec

torch.manual_seed(123)
sa_v1 = SelfAttention_v1(d_in, d_out)
print(sa_v1(inputs))
# tensor([[0.2996, 0.8053],
#         [0.3061, 0.8210],
#         [0.3058, 0.8203],
#         [0.2948, 0.7939],
#         [0.2927, 0.7891],
#         [0.2990, 0.8040]], grad_fn=<MmBackward0>)
```

`forward` is _line-for-line_ the algorithm from Section 4, just generalized from one query (`x_2`) to all 6 tokens at once: `x @ self.W_query` projects _every_ row of `x`, `queries @ keys.T` computes the full 6×6 score matrix (Section 3's trick), and `attn_weights @ values` produces all 6 context vectors in one matmul.

**Sanity check**: row 1 of the output is `[0.3061, 0.8210]` — _identical_ to `context_vec_2` computed by hand at the end of Section 4. This confirms `SelfAttention_v1` correctly reproduces the manual calculation when given the same weight matrices (it does, because `torch.manual_seed(123)` followed by three `torch.rand(d_in, d_out)` calls reproduces the exact same `W_query`, `W_key`, `W_value` as Section 4).

### `SelfAttention_v2`: `nn.Linear` layers

```python
class SelfAttention_v2(nn.Module):
    """Same self-attention mechanism as v1, but using nn.Linear layers
    instead of raw nn.Parameter matrices.
    """
    def __init__(self, d_in, d_out, qkv_bias=False):
        super().__init__()
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key   = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)

    def forward(self, x):
        queries = self.W_query(x)
        keys    = self.W_key(x)
        values  = self.W_value(x)

        attn_scores = queries @ keys.T
        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)

        context_vec = attn_weights @ values
        return context_vec

torch.manual_seed(789)
sa_v2 = SelfAttention_v2(d_in, d_out)
print(sa_v2(inputs))
# tensor([[-0.0739,  0.0713],
#         [-0.0748,  0.0703],
#         [-0.0749,  0.0702],
#         [-0.0760,  0.0685],
#         [-0.0763,  0.0679],
#         [-0.0754,  0.0693]], grad_fn=<MmBackward0>)
```

**Why `nn.Linear` instead of `nn.Parameter`?** Two reasons. First, `nn.Linear(d_in, d_out, bias=False)` computes `x @ W.T` with `W` initialized using PyTorch's carefully-tuned default scheme (a variant of Kaiming/He initialization), which empirically leads to more stable training than `torch.rand` (uniform on $[0,1)$) — `torch.rand` gives every weight a _positive_ value with no zero-mean centering, which is a poor initialization for deep networks. Second, `nn.Linear` is the standard building block, so it composes cleanly with the rest of PyTorch (optimizers, `state_dict`, device transfers, etc.) without any special-casing.

**Gotcha**: `sa_v1` and `sa_v2` produce _completely different numbers_ (`[0.30, 0.81]` vs. `[-0.07, 0.07]`) even though the _algorithm_ is identical. This is purely because (a) different random seeds were used (123 vs. 789) and (b) `nn.Linear`'s initialization differs from `torch.rand`. The book notes that if you manually copy `nn.Linear`'s weight matrices into `sa_v1`'s parameters (`sa_v1.W_query.data = sa_v2.W_query.weight.T.data`, etc.), both classes produce identical outputs — confirming they implement the same math.

---

## 6 — 3.5.1 — Causal Attention: Hiding Future Words

**Summary**: For a language model that predicts the _next_ token, a token must never be allowed to attend to tokens that come _after_ it — otherwise the model could "cheat" by looking at the answer. **Causal** (a.k.a. masked, or autoregressive) attention enforces this by zeroing out the upper-triangular part of the attention weight matrix.

**The problem it solves**: Self-attention as built so far is _bidirectional_ — token 2 ("journey") freely attends to token 5 ("one") and token 6 ("step"), which haven't "happened yet" from token 2's point of view during next-token-prediction training. If we train a language model this way, at inference time (where future tokens genuinely don't exist yet) the model would behave inconsistently with how it was trained, and worse, during training it could trivially learn to "predict" the next token by just copying it from its own attention output — a shortcut that produces zero useful learning signal.

**The intuition**: Imagine taking a multiple-choice reading-comprehension test where the answer key is printed directly below each question. Bidirectional self-attention is like being allowed to read the entire page, including answers to questions you haven't gotten to yet. Causal attention is like covering everything below the current question with a sheet of paper — you can look back at everything you've already read, but nothing ahead.

### Building the mask, two ways

We start from `sa_v2`'s attention weights:

```python
# Reuse the query and key weight matrices of the
# SelfAttention_v2 object from the previous section for convenience
queries = sa_v2.W_query(inputs)
keys    = sa_v2.W_key(inputs)
attn_scores  = queries @ keys.T
attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
print(attn_weights)
# tensor([[0.1921, 0.1646, 0.1652, 0.1550, 0.1721, 0.1510],
#         [0.2041, 0.1659, 0.1662, 0.1496, 0.1665, 0.1477],
#         [0.2036, 0.1659, 0.1662, 0.1498, 0.1664, 0.1480],
#         [0.1869, 0.1667, 0.1668, 0.1571, 0.1661, 0.1564],
#         [0.1830, 0.1669, 0.1670, 0.1588, 0.1658, 0.1585],
#         [0.1935, 0.1663, 0.1666, 0.1542, 0.1666, 0.1529]],
#        grad_fn=<SoftmaxBackward0>)
```

**Approach 1 — Mask after softmax, then renormalize.** Build a lower-triangular mask of 1s (`torch.tril`), multiply it elementwise with the attention weights (zeroing out every "future" entry), and then divide each row by its new sum so the row sums to 1 again:

```python
context_length = attn_scores.shape[0]
mask_simple = torch.tril(torch.ones(context_length, context_length))
print(mask_simple)
# tensor([[1., 0., 0., 0., 0., 0.],
#         [1., 1., 0., 0., 0., 0.],
#         [1., 1., 1., 0., 0., 0.],
#         [1., 1., 1., 1., 0., 0.],
#         [1., 1., 1., 1., 1., 0.],
#         [1., 1., 1., 1., 1., 1.]])

masked_simple = attn_weights * mask_simple
print(masked_simple)
# tensor([[0.1921, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.2041, 0.1659, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.2036, 0.1659, 0.1662, 0.0000, 0.0000, 0.0000],
#         [0.1869, 0.1667, 0.1668, 0.1571, 0.0000, 0.0000],
#         [0.1830, 0.1669, 0.1670, 0.1588, 0.1658, 0.0000],
#         [0.1935, 0.1663, 0.1666, 0.1542, 0.1666, 0.1529]],
#        grad_fn=<MulBackward0>)

row_sums = masked_simple.sum(dim=-1, keepdim=True)
masked_simple_norm = masked_simple / row_sums
print(masked_simple_norm)
# tensor([[1.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.5517, 0.4483, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.3800, 0.3097, 0.3103, 0.0000, 0.0000, 0.0000],
#         [0.2758, 0.2460, 0.2462, 0.2319, 0.0000, 0.0000],
#         [0.2175, 0.1983, 0.1984, 0.1888, 0.1971, 0.0000],
#         [0.1935, 0.1663, 0.1666, 0.1542, 0.1666, 0.1529]],
#        grad_fn=<DivBackward0>)
```

Look at row 0: it's `[1, 0, 0, 0, 0, 0]` — token 0 ("Your") attends _only to itself_, because it's the first token and there's nothing before it. Row 1 splits roughly 55/45 between tokens 0 and 1. Row 5 (the last token) is unchanged from the original `attn_weights`, because the last token is allowed to see everything.

**Approach 2 — Mask with $-\infty$ before softmax (the efficient, correct way).** Instead of computing the full softmax and then zeroing things out, we set the _future_ positions of the **raw scores** to $-\infty$ _before_ softmax:

```python
mask = torch.triu(torch.ones(context_length, context_length), diagonal=1)
print(mask)
# tensor([[0., 1., 1., 1., 1., 1.],
#         [0., 0., 1., 1., 1., 1.],
#         [0., 0., 0., 1., 1., 1.],
#         [0., 0., 0., 0., 1., 1.],
#         [0., 0., 0., 0., 0., 1.],
#         [0., 0., 0., 0., 0., 0.]])

masked = attn_scores.masked_fill(mask.bool(), -torch.inf)
print(masked)
# tensor([[0.2899,   -inf,   -inf,   -inf,   -inf,   -inf],
#         [0.4656, 0.1723,   -inf,   -inf,   -inf,   -inf],
#         [0.4594, 0.1703, 0.1731,   -inf,   -inf,   -inf],
#         [0.2642, 0.1024, 0.1036, 0.0186,   -inf,   -inf],
#         [0.2183, 0.0874, 0.0882, 0.0177, 0.0786,   -inf],
#         [0.3408, 0.1270, 0.1290, 0.0198, 0.1290, 0.0078]],
#        grad_fn=<MaskedFillBackward0>)

attn_weights = torch.softmax(masked / keys.shape[-1]**0.5, dim=-1)
print(attn_weights)
# tensor([[1.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.5517, 0.4483, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.3800, 0.3097, 0.3103, 0.0000, 0.0000, 0.0000],
#         [0.2758, 0.2460, 0.2462, 0.2319, 0.0000, 0.0000],
#         [0.2175, 0.1983, 0.1984, 0.1888, 0.1971, 0.0000],
#         [0.1935, 0.1663, 0.1666, 0.1542, 0.1666, 0.1529]],
#        grad_fn=<SoftmaxBackward0>)
```

**Layer 2 — Math**: $e^{-\infty} = 0$, so any position set to $-\infty$ before softmax contributes _exactly_ $0$ to both the numerator and the denominator of $\text{softmax}(x)_i = e^{x_i} / \sum_j e^{x_j}$ — which is _precisely_ what "zero out and renormalize" (Approach 1) does, but in a single pass.

The two approaches produce **identical** results (`masked_simple_norm == attn_weights`, both shown above). But Approach 2 is strictly better:

**Gotcha — why not Approach 1 in practice?** In Approach 1, the _first_ softmax is computed over **all 6 positions**, including future ones — meaning every denominator $\sum_j e^{\omega_{ij}}$ already "knows about" future tokens' scores, even though their contributions are zeroed out afterward and the rows are renormalized. While the _final numbers_ happen to come out the same here (because renormalization exactly cancels the effect), Approach 1 does unnecessary work (a full 6×6 softmax, vs. an effectively triangular one) and is the kind of pattern that's easy to get subtly wrong if the masking step is ever forgotten or misapplied. Approach 2 is the standard, and the only one used going forward.

---

## 7 — 3.5.2 — Masking with Dropout

**Summary**: **Dropout** randomly zeroes out a fraction of the attention weights _during training only_, and rescales the surviving weights by $\frac{1}{1-p}$ to keep their expected sum unchanged. This is a regularization technique that prevents the model from over-relying on any single attention connection.

**The problem it solves**: Without dropout, a model can learn to depend very heavily on a small number of specific attention weights — e.g., always routing 90% of attention to one particular token. This is a form of overfitting: the model becomes brittle, because it hasn't learned _redundant_ pathways for getting the same information.

**The intuition**: It's like training a sports team by randomly benching a few players in every practice session. No single player can become the team's _only_ way of scoring — the team is forced to develop multiple players who can all contribute, making the team more robust when (at "test time", i.e. inference, when dropout is off) everyone is available.

**Layer 2 — Math**: Given dropout probability $p$, each element $a_{ij}$ of the attention-weight matrix is independently set to 0 with probability $p$, and otherwise _scaled up_ by $\frac{1}{1-p}$:

$$a'_{ij} = \begin{cases} 0 & \text{with probability } p \\ \dfrac{a_{ij}}{1-p} & \text{with probability } 1-p \end{cases}$$

The $\frac{1}{1-p}$ scaling keeps $\mathbb{E}[a'_{ij}] = a_{ij}$ — i.e., on average across many forward passes, dropout doesn't change the expected value of the sum, so the model doesn't need to "compensate" for dropout being switched off at inference time.

**Layer 3 — Dry run**, $p=0.5$ applied to a $6\times6$ matrix of all 1s:

```python
torch.manual_seed(123)
dropout = torch.nn.Dropout(0.5)  # 50% dropout rate
example = torch.ones(6, 6)
print(dropout(example))
# tensor([[2., 2., 0., 2., 2., 0.],
#         [0., 0., 0., 2., 0., 2.],
#         [2., 2., 2., 2., 0., 2.],
#         [0., 2., 2., 0., 0., 2.],
#         [0., 2., 0., 2., 0., 2.],
#         [0., 2., 2., 2., 2., 0.]])
```

With $p=0.5$, $\frac{1}{1-p} = \frac{1}{0.5} = 2$. Every surviving `1` becomes `2`, and roughly half the entries become `0` — exactly matching the formula above (each `1` either becomes `0` or `1/(1-0.5) = 2`).

Applying the same dropout to the real (causally-masked) attention weights from Section 6:

```python
torch.manual_seed(123)
print(dropout(attn_weights))
# tensor([[2.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
#         [0.7599, 0.6194, 0.6206, 0.0000, 0.0000, 0.0000],
#         [0.0000, 0.4921, 0.4925, 0.0000, 0.0000, 0.0000],
#         [0.0000, 0.3966, 0.0000, 0.3775, 0.0000, 0.0000],
#         [0.0000, 0.3327, 0.3331, 0.3084, 0.3331, 0.0000]],
#        grad_fn=<MulBackward0>)
```

**Gotcha**: Dropout is applied to the attention weights _after_ softmax and masking, not to the raw scores. Also, dropout zeroes out entries that are _already_ zero from causal masking just as readily as nonzero ones — that's fine, since `0 → 0` either way. And critically, `nn.Dropout` only does anything when the module is in `.train()` mode; in `.eval()` mode (inference), `dropout(x)` is the identity function — no scaling, no zeroing.

**Gotcha — OS-dependent dropout**: PyTorch's RNG for `nn.Dropout` can produce slightly different masks on different operating systems for the same seed (a [known PyTorch issue](https://github.com/pytorch/pytorch/issues/121595)) — if you re-run this cell on a different machine, expect the _pattern_ of zeros to differ even though the scaling factor (here, 2×) and overall behavior stay the same.

---

## 8 — 3.5.3 — `CausalAttention`: A Compact Causal Attention Class

**Summary**: `CausalAttention` packages everything so far — Q/K/V projection, scaling, causal masking, dropout — into a single `nn.Module` that additionally handles **batches** of sequences (shape `(batch, num_tokens, d_in)`) instead of a single sequence.

### Batched input

So far every example used a single sentence, shape `(6, 3)`. In practice we train on _batches_ of sequences simultaneously. We simulate a batch of 2 identical sentences:

```python
batch = torch.stack((inputs, inputs), dim=0)
print(batch.shape)
# torch.Size([2, 6, 3])   →  (batch_size=2, num_tokens=6, d_in=3)
```

### The class

```python
class CausalAttention(nn.Module):
    """Single-head causal self-attention with dropout, supporting batched
    input.
    """
    def __init__(self, d_in, d_out, context_length, dropout, qkv_bias=False):
        super().__init__()
        self.d_out = d_out
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key   = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.dropout = nn.Dropout(dropout)
        self.register_buffer(
            'mask',
            torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape
        queries = self.W_query(x)
        keys    = self.W_key(x)
        values  = self.W_value(x)

        attn_scores = queries @ keys.transpose(1, 2)
        attn_scores.masked_fill_(
            self.mask.bool()[:num_tokens, :num_tokens], -torch.inf
        )
        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
        attn_weights = self.dropout(attn_weights)

        context_vec = attn_weights @ values
        return context_vec

torch.manual_seed(123)
context_length = batch.shape[1]   # 6
d_in_ca, d_out_ca = inputs.shape[1], 2
ca = CausalAttention(d_in_ca, d_out_ca, context_length, 0.0)

context_vecs = ca(batch)
print(context_vecs)
# tensor([[[-0.4519,  0.2216],
#          [-0.5874,  0.0058],
#          [-0.6300, -0.0632],
#          [-0.5675, -0.0843],
#          [-0.5526, -0.0981],
#          [-0.5299, -0.1081]],
#
#         [[-0.4519,  0.2216],
#          [-0.5874,  0.0058],
#          [-0.6300, -0.0632],
#          [-0.5675, -0.0843],
#          [-0.5526, -0.0981],
#          [-0.5299, -0.1081]]], grad_fn=<UnsafeViewBackward0>)
print("context_vecs.shape:", context_vecs.shape)
# context_vecs.shape: torch.Size([2, 6, 2])
```

Three changes from `SelfAttention_v2`, all driven by the new batch dimension:

The first change is `keys.transpose(1, 2)` instead of `keys.T`. With a batch dimension, `keys` has shape `(b, num_tokens, d_out)`. `.T` would reverse _all_ dimensions (turning `(b, n, d)` into `(d, n, b)` — wrong!). `.transpose(1, 2)` swaps only the last two dimensions, giving `(b, d_out, num_tokens)`, so `queries @ keys.transpose(1, 2)` computes shape `(b, n, d) @ (b, d, n) → (b, n, n)` — a separate $n \times n$ score matrix _for each item in the batch_, computed in one batched matmul.

The second change is `self.register_buffer('mask', ...)`. The causal mask is _not_ a learnable parameter — it never changes during training — but we still want PyTorch to (a) move it to the correct device automatically when we call `.to(device)` on the model, and (b) include it in `state_dict()` for checkpointing if desired, while (c) excluding it from the optimizer's parameter list. `register_buffer` gives us exactly this: a tensor that "lives with" the module but isn't trained.

The third change is `masked_fill_` with a trailing underscore — an _in-place_ operation (modifies `attn_scores` directly, saving memory), versus the non-underscore `masked_fill` used in Section 6 which returns a new tensor. Both are valid; the in-place version is slightly more memory-efficient and is what's typically used inside `forward()`.

Both items in the batch produce identical output — expected, since `batch` was constructed by stacking two copies of the same `inputs`.

---

## 9 — 3.6.1 — `MultiHeadAttentionWrapper`: Stacking Heads

**Summary**: A single attention "head" learns _one_ notion of relevance between tokens. **Multi-head attention** runs several independent attention heads _in parallel_, each with its own $W_q, W_k, W_v$, and concatenates their outputs — letting the model attend to different _kinds_ of relationships simultaneously (e.g. one head might learn syntactic relationships, another might learn coreference).

**The intuition**: Picture a panel of expert reviewers reading the same document, each with a different specialty (one focused on grammar, one on factual consistency, one on tone). Each reviewer ("head") produces their own independent assessment ("context vector") of every sentence; the final report concatenates all their notes side by side. No single reviewer needs to capture _everything_ — they specialize, and their combined output is richer than any one of them alone.

### The simplest possible implementation: a `ModuleList` of `CausalAttention`s

```python
class MultiHeadAttentionWrapper(nn.Module):
    """Multi-head attention built by stacking `num_heads` independent
    CausalAttention modules side by side.
    """
    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        self.heads = nn.ModuleList(
            [CausalAttention(d_in, d_out, context_length, dropout, qkv_bias)
             for _ in range(num_heads)]
        )

    def forward(self, x):
        return torch.cat([head(x) for head in self.heads], dim=-1)

torch.manual_seed(123)
context_length = batch.shape[1]  # 6 — number of tokens
d_in, d_out = 3, 2
mha = MultiHeadAttentionWrapper(d_in, d_out, context_length, 0.0, num_heads=2)

context_vecs = mha(batch)
print(context_vecs)
# tensor([[[-0.4519,  0.2216,  0.4772,  0.1063],
#          [-0.5874,  0.0058,  0.5891,  0.3257],
#          [-0.6300, -0.0632,  0.6202,  0.3860],
#          [-0.5675, -0.0843,  0.5478,  0.3589],
#          [-0.5526, -0.0981,  0.5321,  0.3428],
#          [-0.5299, -0.1081,  0.5077,  0.3493]],
#
#         [[-0.4519,  0.2216,  0.4772,  0.1063],
#          [-0.5874,  0.0058,  0.5891,  0.3257],
#          [-0.6300, -0.0632,  0.6202,  0.3860],
#          [-0.5675, -0.0843,  0.5478,  0.3589],
#          [-0.5526, -0.0981,  0.5321,  0.3428],
#          [-0.5299, -0.1081,  0.5077,  0.3493]]], grad_fn=<CatBackward0>)
print("context_vecs.shape:", context_vecs.shape)
# context_vecs.shape: torch.Size([2, 6, 4])
```

With `num_heads=2` and `d_out=2` per head, `torch.cat(..., dim=-1)` concatenates the two `(2, 6, 2)` outputs along the last dimension into `(2, 6, 4)`. Notice the first 2 columns of the output (`[-0.4519, 0.2216, ...]`) are _identical_ to Section 8's `CausalAttention` output — that's `head[0]`, constructed with the exact same `manual_seed(123)` as the standalone example. The remaining 2 columns are `head[1]`, a second independent attention computation with different (also seeded) weights.

**Gotcha — this is computationally wasteful**. Each of the `num_heads` `CausalAttention` instances performs its _own_ separate `nn.Linear` projections and its _own_ separate matmuls — `num_heads` independent, sequential (in the Python `for` loop inside `torch.cat`) passes through nearly-identical code. On a GPU, launching many small operations sequentially is much slower than launching one large batched operation. Section 10 fixes this.

---

## 10 — 3.6.2 — `MultiHeadAttention`: The Efficient, Production Implementation

**Summary**: Instead of running `num_heads` separate small attention computations, we run **one** attention computation with `d_out`-dimensional Q/K/V projections, then _reshape_ the result to "split" the `d_out` dimension into `num_heads` heads of size `head_dim = d_out / num_heads`, each of which gets its own causal-masked, softmax'd attention — all via batched tensor operations with no Python-level loop over heads.

**The intuition**: Section 9's wrapper is like hiring `num_heads` separate analysts, each doing their own complete data pipeline from scratch. Section 10 is like hiring _one_ analyst who pulls all the data once, then mentally partitions their notes into `num_heads` separate notebooks and analyzes each notebook independently — same end result, but the expensive "pull all the data" step happens only once.

### The class

```python
class MultiHeadAttention(nn.Module):
    """Efficient multi-head attention computed with a single batched
    matrix multiplication instead of a Python loop over heads.
    """
    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        assert d_out % num_heads == 0, "d_out must be divisible by num_heads"

        self.d_out = d_out
        self.num_heads = num_heads
        self.head_dim = d_out // num_heads  # Reduce the projection dim to match desired output dim

        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key   = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.out_proj = nn.Linear(d_out, d_out)  # Linear layer to combine head outputs
        self.dropout = nn.Dropout(dropout)
        self.register_buffer(
            'mask',
            torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape

        keys    = self.W_key(x)    # Shape: (b, num_tokens, d_out)
        queries = self.W_query(x)
        values  = self.W_value(x)

        # Split d_out into (num_heads, head_dim)
        keys    = keys.view(b, num_tokens, self.num_heads, self.head_dim)
        values  = values.view(b, num_tokens, self.num_heads, self.head_dim)
        queries = queries.view(b, num_tokens, self.num_heads, self.head_dim)

        # Group by num_heads
        keys    = keys.transpose(1, 2)
        queries = queries.transpose(1, 2)
        values  = values.transpose(1, 2)

        attn_scores = queries @ keys.transpose(2, 3)  # Dot product for each head

        mask_bool = self.mask.bool()[:num_tokens, :num_tokens]
        attn_scores.masked_fill_(mask_bool, -torch.inf)

        attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
        attn_weights = self.dropout(attn_weights)

        context_vec = (attn_weights @ values).transpose(1, 2)
        context_vec = context_vec.contiguous().view(b, num_tokens, self.d_out)
        context_vec = self.out_proj(context_vec)  # optional projection

        return context_vec

torch.manual_seed(123)
batch_size, context_length, d_in = batch.shape
d_out = 2
mha = MultiHeadAttention(d_in, d_out, context_length, 0.0, num_heads=2)

context_vecs = mha(batch)
print(context_vecs)
# tensor([[[0.3190, 0.4858],
#          [0.2943, 0.3897],
#          [0.2856, 0.3593],
#          [0.2693, 0.3873],
#          [0.2639, 0.3928],
#          [0.2575, 0.4028]],
#
#         [[0.3190, 0.4858],
#          [0.2943, 0.3897],
#          [0.2856, 0.3593],
#          [0.2693, 0.3873],
#          [0.2639, 0.3928],
#          [0.2575, 0.4028]]], grad_fn=<ViewBackward0>)
print("context_vecs.shape:", context_vecs.shape)
# context_vecs.shape: torch.Size([2, 6, 2])
```

### Walking through the shape transformations

This is the trickiest part of the chapter, so let's track the shape after every line, with `b=2, num_tokens=6, d_in=3, d_out=2, num_heads=2, head_dim=1`:

```
x                            : (2, 6, 3)
queries = W_query(x)         : (2, 6, 2)            ← d_out=2, "flat", not yet split into heads

queries.view(b, n, h, hd)    : (2, 6, 2, 1)          ← split last dim 2 into (num_heads=2, head_dim=1)
queries.transpose(1, 2)      : (2, 2, 6, 1)          ← (batch, num_heads, num_tokens, head_dim)

attn_scores = q @ k.transpose(2,3)
            (2,2,6,1) @ (2,2,1,6)  → (2, 2, 6, 6)    ← (batch, num_heads, num_tokens, num_tokens)

attn_weights @ values
 (2,2,6,6) @ (2,2,6,1) → (2, 2, 6, 1)                ← (batch, num_heads, num_tokens, head_dim)

.transpose(1, 2)             : (2, 6, 2, 1)          ← back to (batch, num_tokens, num_heads, head_dim)
.contiguous().view(b, n, d_out) : (2, 6, 2)          ← merge (num_heads, head_dim) back into d_out

out_proj(...)                : (2, 6, 2)             ← final linear mix across heads
```

**Why `.view()` to split, and `.transpose()` to group?** `.view(b, num_tokens, num_heads, head_dim)` is a _free_ operation — it reinterprets the existing contiguous `(b, num_tokens, d_out)` memory as `(b, num_tokens, num_heads, head_dim)` without copying any data, because `d_out = num_heads * head_dim` and the last dimension is the one being split (splitting the _last_, contiguous dimension never requires a copy). `.transpose(1, 2)` then swaps `num_tokens` and `num_heads` to bring `num_heads` next to `batch` — this _does_ break contiguity (transpose only swaps strides, doesn't move data), which is exactly why `.contiguous()` is required later before the final `.view()` (you cannot `.view()` a non-contiguous tensor; `.reshape()` would work too but might silently copy).

**Why `keys.transpose(2, 3)` (not `(1, 2)` like in `CausalAttention`)?** Because `keys` now has _4_ dimensions, `(b, num_heads, num_tokens, head_dim)`. We want $QK^T$ _per head_, i.e. a matmul over the last two dimensions `(num_tokens, head_dim)`, treating `(b, num_heads)` as "batch" dimensions that PyTorch's batched matmul (`@`/`torch.matmul`) automatically broadcasts over. `transpose(2, 3)` swaps exactly those last two dims, turning `(b, h, n, hd)` into `(b, h, hd, n)`, so `(b,h,n,hd) @ (b,h,hd,n) → (b,h,n,n)`.

### A tiny concrete example of 4D batched matmul

To build intuition for "matmul on the last two dims, broadcast over the rest":

```python
a = torch.tensor([[[[0.2745, 0.6584, 0.2775, 0.8573],
                     [0.8993, 0.0390, 0.9268, 0.7388],
                     [0.7179, 0.7058, 0.9156, 0.4340]],

                    [[0.0772, 0.3565, 0.1479, 0.5331],
                     [0.4066, 0.2318, 0.4545, 0.9737],
                     [0.4606, 0.5159, 0.4220, 0.5786]]]])
print(a.shape)
# torch.Size([1, 2, 3, 4])    →  (batch=1, num_heads=2, num_tokens=3, head_dim=4)

print(a @ a.transpose(2, 3))
# tensor([[[[1.3208, 1.1631, 1.2879],
#           [1.1631, 2.2150, 1.8424],
#           [1.2879, 1.8424, 2.0402]],
#
#          [[0.4391, 0.7003, 0.5903],
#           [0.7003, 1.3737, 1.0620],
#           [0.5903, 1.0620, 0.9912]]]])

# Verify: head 0's matmul, computed in isolation, matches a[0,0] @ a[0,0].T
first_head = a[0, 0, :, :]
first_res = first_head @ first_head.T
print("First head:\n", first_res)
# tensor([[1.3208, 1.1631, 1.2879],
#         [1.1631, 2.2150, 1.8424],
#         [1.2879, 1.8424, 2.0402]])

second_head = a[0, 1, :, :]
second_res = second_head @ second_head.T
print("Second head:\n", second_res)
# tensor([[0.4391, 0.7003, 0.5903],
#         [0.7003, 1.3737, 1.0620],
#         [0.5903, 1.0620, 0.9912]])
```

`a @ a.transpose(2, 3)` on a 4D tensor computes, _for each combination of the leading dimensions_ (here, for each of the 2 "heads"), the matmul of the trailing $3\times4$ matrix with its own transpose — exactly equivalent to looping over `a[0, h, :, :] @ a[0, h, :, :].T` for `h in {0, 1}`, but done in one vectorized call. This is the same mechanism `attn_scores = queries @ keys.transpose(2, 3)` relies on inside `MultiHeadAttention.forward`.

### `MultiHeadAttentionWrapper` vs. `MultiHeadAttention` — what's the same, what's different

```
MultiHeadAttentionWrapper(d_in, d_out=2, num_heads=2)
  → output dim = d_out * num_heads = 4   (each head outputs d_out, then concatenated)

MultiHeadAttention(d_in, d_out=2, num_heads=2)
  → output dim = d_out = 2               (d_out is split across heads: head_dim = d_out / num_heads = 1)
```

In `MultiHeadAttention`, `d_out` is the _total_ output dimension you want (matching `d_in` so blocks can be stacked), and each head operates on a `head_dim = d_out / num_heads` slice — this is why the constructor asserts `d_out % num_heads == 0`. `MultiHeadAttention` also adds a final `out_proj` linear layer, an extra learned mixing step across the concatenated heads that the wrapper version doesn't have. This is why the two classes' outputs (`[0.3190, 0.4858]`, ... vs. the wrapper's `[-0.4519, 0.2216, 0.4772, 0.1063]`, ...) differ — different shapes, different weights, and an extra projection layer.

---

## 11 — Putting It All Together & Where This Leads

The full journey of this chapter, in one diagram:

```
inputs (b, n, d_in)
       │
       ▼
 ┌─────────────────────────────────────────────────────────┐
 │  W_query, W_key, W_value  (nn.Linear, no bias)           │
 │       Q, K, V  each (b, n, d_out)                        │
 └─────────────────────────────────────────────────────────┘
       │
       ▼  split into heads: view + transpose
 (b, num_heads, n, head_dim)
       │
       ▼
 attn_scores = Q @ K^T                  (b, num_heads, n, n)
       │
       ▼  scale by 1/sqrt(head_dim)
       │  causal mask: future positions → -inf
       │  softmax(dim=-1)
       │  dropout
       ▼
 attn_weights                            (b, num_heads, n, n)
       │
       ▼
 context = attn_weights @ V              (b, num_heads, n, head_dim)
       │
       ▼  transpose + merge heads back
 (b, n, d_out)
       │
       ▼
 out_proj (nn.Linear)
       │
       ▼
 context_vecs (b, n, d_out)
```

Every numeric example in this document was produced by `MultiHeadAttention` and its building blocks exactly as shown — this _is_ the attention block used inside a GPT transformer block. What's still missing, and what Chapter 4 builds next: wrapping this attention block together with a feed-forward network, **layer normalization**, **residual ("skip") connections**, and **GELU activations** into a complete **transformer block** — and then stacking many of those blocks (12 for GPT-2 small) to form the full GPT architecture. The `d_out`, `context_length`, and `num_heads` hyperparameters introduced here become the `emb_dim`, `context_length`, and `n_heads` entries of the GPT config dictionary in Chapter 4.

**Connection forward**: notice that `MultiHeadAttention.__init__` takes `d_in` and `d_out` as _separate_ arguments, but in GPT they're always equal (`d_in == d_out == emb_dim`) — this is what makes it possible to stack transformer blocks: the output of one block has the same shape as its input, so it can be fed directly into the next block.
