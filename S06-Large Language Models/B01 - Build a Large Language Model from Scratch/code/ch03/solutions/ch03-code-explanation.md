# Chapter 3 — Coding Attention Mechanisms

This chapter builds the single most important mechanism in modern deep learning: **self-attention**, and its practical form, **multi-head attention**. Everything here is pure PyTorch — no `nn.Transformer`, no shortcuts. We start from a parameter-free toy version that just measures "how similar are these two word vectors?", and by the end of the chapter we have a fully batched, causally-masked, dropout-regularized, multi-head attention module that is _exactly_ the block GPT-style models stack 12, 24, or 96 times.

The reference notebook is `ch03-coding-attention-mechanisms-solution-solved.ipynb`. Five classes in that notebook are left as exercises in the practice template (`SelfAttention_v1`, `SelfAttention_v2`, `CausalAttention`, `MultiHeadAttentionWrapper`, `MultiHeadAttention`); this document explains the canonical implementations of all five, with real numbers produced by actually running the code.

---

## Table of Contents

0. [Setup](#0--setup)
1. [3.1 & 3.2 — Why Attention? From RNN Bottlenecks to Self-Attention](#1--31--32--why-attention-from-rnn-bottlenecks-to-self-attention)
2. [3.3.1 — A Simple Self-Attention Mechanism Without Trainable Weights](#2--331--a-simple-self-attention-mechanism-without-trainable-weights)
3. [3.3.2 — Computing Attention Weights for All Input Tokens](#3--332--computing-attention-weights-for-all-input-tokens)
4. [3.4.1 — Self-Attention with Trainable Weights: Q, K, V](#4--341--self-attention-with-trainable-weights-q-k-v)
5. [3.4.2 — `SelfAttention_v1` and `SelfAttention_v2`](#5--342--selfattention_v1-and-selfattention_v2)
6. [3.5.1 — Causal Attention: Hiding Future Words](#6--351--causal-attention-hiding-future-words)
7. [3.5.2 — Masking with Dropout](#7--352--masking-with-dropout)
8. [3.5.3 — `CausalAttention`: A Compact Causal Attention Class](#8--353--causalattention-a-compact-causal-attention-class)
9. [3.6.1 — `MultiHeadAttentionWrapper`: Stacking Heads](#9--361--multiheadattentionwrapper-stacking-heads)
10. [3.6.2 — `MultiHeadAttention`: The Efficient, Production Implementation](#10--362--multiheadattention-the-efficient-production-implementation)
11. [Putting It All Together & Where This Leads](#11--putting-it-all-together--where-this-leads)

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
W_query = [
    [0.2961, 0.5166],
    [0.2517, 0.6886],
    [0.0740, 0.8665]
]

W_key = [
    [0.1366, 0.1025],
    [0.1841, 0.7264],
    [0.3153, 0.6871]
]

W_value = [
    [0.0756, 0.1966],
    [0.3164, 0.4017],
    [0.1186, 0.8274]
]
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

#### Extra notes

##### What is `torch.nn.Parameter`?

In PyTorch, a `Parameter` is a special subclass of a standard `Tensor`.

When you wrap a regular tensor inside `torch.nn.Parameter()`, you are officially registering it with PyTorch's neural network module (`nn.Module`). You are essentially telling PyTorch: **"Hey, this isn't just random data. This is a weight matrix that I want the model to learn, track, and update during training."**

**Regular Tensor vs. Parameter:**

- **`torch.rand(d_in, d_out)`**: This is just a regular grid of random numbers (like scrap paper). The optimizer ignores it.
- **`nn.Parameter(torch.rand(d_in, d_out))`**: This turns that grid into an official, trainable weight. When you eventually call `optimizer.step()`, PyTorch will look through your model, find everything marked as a `Parameter`, and update its numbers to make the model smarter.

##### The Catch: Why `requires_grad=False`?

You might notice something weird in the code:

```python
W_query = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)

```

By default, an `nn.Parameter` has `requires_grad=True`, meaning PyTorch will start tracking every single math operation it touches so it can calculate gradients (the "learning" part of machine learning).

However, in this specific "Dry Run" chapter, we are not training the model yet. We are just doing manual math to see how the shapes and numbers move around.

- If `requires_grad` was left on, PyTorch would attach a bunch of messy gradient-tracking metadata to our print statements (like `grad_fn=<AddBackward0>`), making it harder to read the raw numbers.
- The author set it to `False` here purely to keep the printed output clean for the tutorial. In a real, training model, these are fully trainable weights with `requires_grad=True` (which is exactly what `nn.Linear` sets up for us automatically later in the chapter).

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

#### Extra notes

Keeping track of tensor shapes is arguably the most important (and sometimes most frustrating!) part of writing PyTorch code.

When you call `.shape` on a PyTorch tensor, it returns a list showing the size of the tensor in every dimension.

For a 2D matrix (like a standard spreadsheet or grid), the shape always follows this rule: **`[number_of_rows, number_of_columns]`**.

#### What `shape[0]` and `shape[1]` mean:

Because Python is zero-indexed (it starts counting at 0):

- **`shape[0]`** asks for the first number in that list. It tells you the **number of rows** (which usually represents the number of words/tokens or the batch size).
- **`shape[1]`** asks for the second number in that list. It tells you the **number of columns** (which usually represents the embedding dimension, or how many numbers make up a single word's vector).

---

#### Looking at your specific example:

In Step 1 of your notes, you printed the shape of the `keys` matrix:
`print(keys.shape) # torch.Size([6, 2])`

This means the `keys` matrix has 6 rows (one for each word in your sentence) and 2 columns (the $d_{out}$ or $d_k$ dimension we projected them into).

So, if you run:

- `keys.shape[0]`, PyTorch looks at `[6, 2]` and grabs the first number: **6**.
- `keys.shape[1]`, PyTorch looks at `[6, 2]` and grabs the second number: **2**.

#### Why `d_k = keys.shape[1]`?

You are trying to find $d_k$ so you can calculate $\sqrt{d_k}$ for the scaled dot-product attention. $d_k$ is the dimension of your key vectors.

Since each word is represented by a row of 2 numbers, the dimension is 2.
By writing `d_k = keys.shape[1]`, you are dynamically telling PyTorch: _"Look at the keys matrix, see how many columns it has, and save that number as $d_k$."_ This is much better than hardcoding `d_k = 2`, because if you change your model size later, this code will automatically adapt!

**_Note on your notes:_** _In the actual code block in your markdown, the author wrote `d_k = keys.shape[-1]`. In Python, an index of `-1` means "grab the very last item in the list." Since `keys.shape` only has two items `[6, 2]`, grabbing the second item `[1]` or the last item `[-1]` does the exact same thing!_

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

**The Intuition: What are we doing here?**
This step is the ultimate payoff of the entire self-attention mechanism. Everything we did before this (Query, Key, Dot Product, Softmax) was just preparation to figure out _how to mix the ingredients_.

- **Queries ($Q$)** were used to ask: _"What am I looking for?"_
- **Keys ($K$)** were used to answer: _"What do I have?"_
- **Values ($V$)** are the actual **"Content"**. The `values` matrix is a 6x2 grid holding the raw "meaning" each word contributes to the output.

Now, we "cash in" our Softmax percentages to build a new, enriched word vector. We blend the _content_ (Values) of all the words together using those exact attention percentages.

$$z^{(2)} = \sum_{i=1}^{6} \alpha_{2i} \, v^{(i)} \quad\Longleftrightarrow\quad z^{(2)} = \alpha_2 V$$

---

**The Dry Run: How the Dimensions are Calculated**
Let's build the final **Context Vector** ($z^{(2)}$) for the word "journey". We use the Attention Weights we calculated for "journey", and apply them to the Value Matrix.

- **The Attention Weights ($\alpha_2$):** `[0.1500, 0.2264, 0.2199, 0.1311, 0.0906, 0.1820]`
- **The Value Matrix ($V$):** A 6x2 grid. Column 1 holds the Dimension 1 values, and Column 2 holds the Dimension 2 values.

```text
               [Dim 1]   [Dim 2]
Value_0 (Your)    0.1855    0.8812
Value_1 (journey) 0.3951    1.0037
Value_2 (starts)  0.3879    0.9831
Value_3 (with)    0.2393    0.5493
Value_4 (one)     0.1492    0.3346
Value_5 (step)    0.3221    0.7863

```

**Calculating Dimension 1:**
We multiply the Attention Weights by **Column 1** of the Value Matrix and sum them up:

```text
z^(2)_1 = (Weight_0 × Value_0[Dim 1]) + (Weight_1 × Value_1[Dim 1]) + ...

        = (0.1500 × 0.1855)       # Your
        + (0.2264 × 0.3951)       # journey
        + (0.2199 × 0.3879)       # starts
        + (0.1311 × 0.2393)       # with
        + (0.0906 × 0.1492)       # one
        + (0.1820 × 0.3221)       # step

        = 0.0278 + 0.0894 + 0.0853 + 0.0313 + 0.0135 + 0.0586
        = 0.3059 (Rounds to 0.3061 with PyTorch's full precision)

```

**Calculating Dimension 2:**
The weights stay _exactly the same_, but we multiply them by **Column 2** of the Value Matrix:

```text
z^(2)_2 = (Weight_0 × Value_0[Dim 2]) + (Weight_1 × Value_1[Dim 2]) + ...

        = (0.1500 × 0.8812)       # Your
        + (0.2264 × 1.0037)       # journey
        + (0.2199 × 0.9831)       # starts
        + (0.1311 × 0.5493)       # with
        + (0.0906 × 0.3346)       # one
        + (0.1820 × 0.7863)       # step

        = 0.1322 + 0.2272 + 0.2162 + 0.0720 + 0.0303 + 0.1431
        = 0.8210

```

---

**Automating the Math in PyTorch**
When we put Dimension 1 and Dimension 2 together, we get our final, context-aware vector: `[0.3061, 0.8210]`. In PyTorch, the `@` symbol (matrix multiplication) executes those two large blocks of addition and multiplication simultaneously.

```python
context_vec_2 = attn_weights_2 @ values
print(context_vec_2)
# tensor([0.3061, 0.8210])

```

**Why are the numbers different from Section 2?**
If you look back at Section 2 (where we didn't use trainable weights), the context vector for "journey" was `[0.4419, 0.6515, 0.5683]`. Here, it is `[0.3061, 0.8210]`. This is completely expected for two reasons:

1. **The Shape:** The original context vector lived in the $d_{in}=3$ dimensional input space. Our new vector lives in the $d_{out}=2$ dimensional **Value space**.
2. **The Source:** We are no longer blending the raw, static input embeddings. We are blending the _learned_ (here, randomly-initialized) Value projections. The model has projected the words into a space specifically optimized for output.

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

#### Extra Notes

Here is exactly why the syntax changes from `x @ W` to `W(x)`. You can add this directly to your notes to explain the mechanics of `nn.Linear`:

##### Why `self.W_query(x)` instead of `x @ self.W_query`?

In `SelfAttention_v1`, our weight matrix was a raw **`nn.Parameter`**. Because it was just a grid of numbers, we had to manually tell PyTorch to perform matrix multiplication using the `@` operator:

```python
# v1: Manual matrix multiplication
queries = x @ self.W_query

```

In `SelfAttention_v2`, we upgraded to **`nn.Linear`**.
`nn.Linear` is not just a matrix; it is a complete PyTorch **Layer** (a class). It automatically creates the weight matrix inside itself, and it has a built-in `forward()` function that knows exactly how to do the math.

When you call an `nn.Linear` object like a function—passing `x` into it as an argument—PyTorch automatically runs the matrix multiplication behind the scenes.

```python
# v2: Calling the Linear layer
queries = self.W_query(x)

```

**Under the Hood:**
When you write `self.W_query(x)`, PyTorch is secretly executing this exact math for you:
`queries = x @ W_query.weight.T + W_query.bias`

**Why make this switch?**

1. **Cleaner Code:** You don't have to write out the `@` operations or manually handle transposing `.T` matrices.
2. **Bias Handling:** `nn.Linear` automatically handles adding a bias vector if `qkv_bias=True`. Doing that manually with raw parameters takes extra lines of code.
3. **Better Initialization:** `nn.Linear` uses a highly optimized default formula (Kaiming initialization) to generate its initial random numbers, which makes the model train much faster and more stably than using pure `torch.rand`.

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

#### The Code Breakdown

**Line 1: Building the "Future" Map**

```python
mask = torch.triu(torch.ones(context_length, context_length), diagonal=1)

```

- `torch.ones` creates a 6x6 grid of pure `1`s.
- `torch.triu` (Triangle Upper) isolates only the upper-right triangle of that grid (starting one step above the center diagonal because of `diagonal=1`). It leaves those as `1`s and turns everything else to `0`s.
- This creates a map of "Future Words". A `1` means "this word is in the future," and a `0` means "this word is in the past or present."

**Line 2: Applying the Mask (`masked_fill`)**

```python
masked = attn_scores.masked_fill(mask.bool(), -torch.inf)

```

- `.masked_fill()` takes our grid of raw `attn_scores` and overlays the triangle mask on top of it.
- Wherever the mask is `True` (a `1`), it rips out the raw attention score and replaces it with **Negative Infinity** (`-torch.inf`).
- Wherever the mask is `False` (a `0`), it leaves the original attention score completely alone.

Here is what the matrix looks like after `.masked_fill()` runs:

```text
# Word 0 only sees itself. Words 1-5 are blocked (-inf).
[ 0.2899,    -inf,    -inf,    -inf,    -inf,    -inf]

# Word 1 sees Word 0 and itself. Words 2-5 are blocked.
[ 0.4656,  0.1723,    -inf,    -inf,    -inf,    -inf]

# ...and so on.
[ 0.4594,  0.1703,  0.1731,    -inf,    -inf,    -inf]

```

#### The Magic: Why Negative Infinity?

Why don't we just replace the future scores with `0`?

Remember that immediately after this step, we push these scores through the **Softmax** function to turn them into percentages. Softmax uses exponents.

- If we fed it a raw score of `0`, $e^{0} = 1$, which would actually give the future word a chunk of the attention budget!
- By using Negative Infinity, we exploit the rule that $e^{-\infty} = 0$.

By setting future scores to $-\infty$ _before_ Softmax, we mathematically guarantee that Softmax will calculate the numerator as exactly `0`, assigning those future words **0% attention weight**. The model is mathematically forced to ignore them!

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

### Extra Notes

`register_buffer` is one of those "hidden gem" PyTorch features that you rarely see in beginner tutorials, but it is absolutely essential for writing robust, professional-grade models.

Most simple models only deal with trainable weights (like `nn.Linear`), which PyTorch handles automatically.

Here is the breakdown of exactly what it is and why the author used it here. This will make a great addition to your notes on PyTorch mechanics.

---

### What is `self.register_buffer`?

In PyTorch, `register_buffer` is used to tell your neural network: **"Here is a tensor that is extremely important to how the model works, but it is NOT a trainable weight, so do not update it during backpropagation."**

To understand why this is necessary, it helps to look at the alternatives. You might be wondering, _"Why didn't the author just write `self.mask = torch.triu(...)`?"_ or _"Why didn't they make it an `nn.Parameter` like the weights?"_

Here is exactly what would happen in those scenarios:

##### 1. Why not just a regular attribute? (`self.mask = torch.triu(...)`)

If you just assign the mask as a regular Python attribute, PyTorch's backend doesn't officially "know" about it. This causes two massive problems:

- **The GPU Crash:** When you eventually run `model.to('cuda')` to move your model to the GPU for fast training, PyTorch will move all your `nn.Linear` layers, but it will leave your `self.mask` sitting behind on the CPU. When the model tries to multiply the GPU tensors with the CPU mask, the code will crash with a device mismatch error.
- **Saving/Loading:** When you save your model using `model.state_dict()`, standard attributes are ignored. The mask wouldn't be saved in your model file.

##### 2. Why not an `nn.Parameter`?

As we discussed earlier, `nn.Parameter` tells PyTorch to track gradients and update the numbers to make the model "learn."

- The causal mask is a strict, permanent rule (1s in the upper triangle, 0s elsewhere). If we made it a `Parameter`, the optimizer would try to change those 1s and 0s during training, completely destroying our rule about hiding future words!

---

##### The Solution: The Buffer

By using `self.register_buffer('mask', tensor)`, you get the best of both worlds:

1. **It moves with the model:** When you call `model.to('cuda')`, PyTorch knows to pick up the mask and move it to the GPU right alongside your `W_query` and `W_key` matrices.
2. **It saves with the model:** It gets cleanly packed into your `state_dict` when you save your weights.
3. **It does not learn:** The optimizer completely ignores it, ensuring your triangular mask stays exactly as 1s and 0s forever.

##### How to use it later in the code

Because you registered it with the name `'mask'`, PyTorch automatically creates an attribute for you. Later in your `forward()` function, you don't need any special syntax to use it—you can just call `self.mask` exactly as if it were a normal variable!

---

### Why `keys.transpose(1, 2)` instead of `keys.T`?

**The Problem with `.T`**  
In earlier steps, our`keys`matrix was 2D:`[Sequence Length, Embedding Dimension]`. Calling `.T` simply flipped the rows and columns.

But in real training, we pass data in **Batches** (multiple sentences at once). This makes our `keys` tensor 3-Dimensional: `[Batch Size, Sequence Length, Embedding Dimension]`.
If you use `.T` on a 3D tensor, PyTorch reverses _all_ the dimensions. That destroys our batch structure! We want the Batch dimension to stay exactly where it is.

**The Solution: `.transpose()**`The`.transpose(dimA, dimB)` function lets us surgically choose exactly which two dimensions to swap.

In Python, dimensions are zero-indexed:

- **Dimension 0:** Batch Size (Number of sentences)
- **Dimension 1:** Sequence Length (Number of words)
- **Dimension 2:** Embedding Size ($d_k$, the features)

When we write `keys.transpose(1, 2)`, we are telling PyTorch:
_"Leave Dimension 0 (the batches) completely alone. Just swap Dimension 1 (Words) and Dimension 2 (Features)."_

##### The Shape Math (Dry Run)

Let's say we have a batch of **8 sentences**, each with **6 words**, and our projected key embedding size is **2**.

1. **The Starting Shapes:**

- `queries.shape`: `[8, 6, 2]` _(Batch, Words, Features)_
- `keys.shape`: `[8, 6, 2]` _(Batch, Words, Features)_

2. **The Transpose:**
   To do matrix multiplication (`@`), the inner dimensions must match. We need to multiply `[8, 6, 2]` by `[8, 2, 6]`.

```python
keys_transposed = keys.transpose(1, 2)
print(keys_transposed.shape)
# torch.Size([8, 2, 6])

```

3. **The Matrix Multiplication (`@`):**
   PyTorch automatically ignores the Batch dimension (8) and does the matrix multiplication on the rest: `(6 x 2) @ (2 x 6)`.

```python
attention_scores = queries @ keys.transpose(1, 2)
print(attention_scores.shape)
# torch.Size([8, 6, 6])

```

**The Result:** We perfectly output a shape of `[8, 6, 6]`. This means we successfully generated an isolated 6x6 attention grid for _all 8 sentences_ simultaneously!

---

### Dynamic Slicing: `[:num_tokens, :num_tokens]`

#### Code

```python
attention_scores.masked_fill(
            self.mask.bool()[:num_tokens:num_tokens], -torch.inf
        )
```

**The Problem: Max Length vs. Current Length**
When we initialized the `CausalAttention` class, we built the `self.mask` using the _maximum_ possible `context_length` the model can ever handle (for example, 1024 words). We do this once in `__init__` so we don't waste time rebuilding the mask on every single forward pass.

However, the specific batch of sentences we pass in right now might only be 6 words long (`num_tokens = 6`).
If we try to overlay a 1024x1024 mask onto a 6x6 `attn_scores` grid, PyTorch will immediately crash with a shape mismatch error!

**The Solution: Slicing**
The syntax `[ : , : ]` is how we crop matrices in PyTorch.

- The first side of the comma targets the **rows**.
- The second side of the comma targets the **columns**.
- Leaving the space before the colon blank means "start from 0".

So, `[:num_tokens, :num_tokens]` translates to: _"Start at row 0 and grab down to `num_tokens`. Then start at column 0 and grab across to `num_tokens`."_

It acts like a cookie cutter, stamping out the exact size we need from the top-left corner of our giant mask.

---

#### A Small Visual Example

Imagine our model has a maximum context length of 4. In `__init__`, we built this 4x4 mask:

```text
self.mask =
[[0, 1, 1, 1],
 [0, 0, 1, 1],
 [0, 0, 0, 1],
 [0, 0, 0, 0]]

```

Now, imagine we pass in the sentence "Your journey" (only **2 words**).
PyTorch calculates a 2x2 grid for `attn_scores`.

We apply the slice: `self.mask[:2, :2]`

PyTorch goes to the giant mask, grabs rows 0 and 1, and columns 0 and 1. It perfectly crops out the top-left 2x2 corner:

```text
Sliced Mask =
[[0, 1],
 [0, 0]]

```

Now, the sliced mask perfectly fits our 2x2 `attn_scores`, the negative infinities are applied correctly, and the code runs without crashing

---

### The Golden Rule of PyTorch: The Trailing Underscore (`_`)

In PyTorch, there is a strict, universal naming convention for how functions handle computer memory:

- **No Underscore (e.g., `masked_fill`):** Creates a **brand new** tensor. Think of this as clicking _"Save As"_ on a document.
- **Trailing Underscore (e.g., `masked_fill_`):** Modifies the **existing** tensor directly. Think of this as clicking _"Save"_ on your current document.

---

#### How it Looks in Code

#### 1. The "Save As" Mistake (Out-of-Place)

If you use the standard version without the underscore, PyTorch does the math and generates a new tensor. However, if you don't assign it to a variable, that new tensor immediately vanishes into the void!

```python
scores = torch.tensor([1, 2, 3])

# PyTorch creates a new tensor, but we didn't assign it to anything!
scores.masked_fill(mask, 0)

print(scores)
# tensor([1, 2, 3]) --> The original is completely unchanged!

```

#### 2. The Correct "Save As"

To keep the changes using the standard method, you _must_ overwrite the old variable or catch the output in a new variable.

```python
scores = torch.tensor([1, 2, 3])

# We explicitly save the new tensor over the old variable
scores = scores.masked_fill(mask, 0)

```

#### 3. The "In-Place" Fix (The Trailing Underscore)

By adding the underscore, you tell PyTorch to go into the computer's memory, rip out the old numbers in the original tensor, and replace them on the spot. No new tensor is created.

```python
scores = torch.tensor([1, 2, 3])

# Modifies the original tensor directly in memory
scores.masked_fill_(mask, 0)

print(scores)
# tensor([0, 0, 0]) --> Success!

```

---

> **Why use In-Place (`_`)? Memory Efficiency!**
> In Transformer models, attention matrices can become massive (e.g., a batch of 1024x1024 grids). Creating a brand new copy of that entire grid just to apply a causal mask wastes a huge amount of GPU memory (VRAM). Using `masked_fill_` alters the grid right where it sits, keeping your memory usage lean and helping prevent dreaded Out-Of-Memory (OOM) crashes!

---

## 9 — 3.6.1 — `MultiHeadAttentionWrapper`: Stacking Heads

**Summary**: A single attention "head" learns _one_ notion of relevance between tokens. **Multi-head attention** runs several independent attention heads _in parallel_, each with its own $W_q, W_k, W_v$, and concatenates their outputs — letting the model attend to different _kinds_ of relationships simultaneously (e.g. one head might learn syntactic relationships, another might learn coreference).

**The problem it solves**: A single head is forced to compress everything it needs to know about token relationships into one set of Q, K, V weights. Consider the word "it" in "The animal didn't cross the street because it was too tired" — to resolve this correctly, the model needs to think about syntax ("it" is a subject), semantics ("tired" applies to living things), and long-range structure ("animal" is far away). One head has to compromise across all of these. Multiple heads let each one specialize freely.

**The intuition**: Picture a panel of expert reviewers reading the same document, each with a different specialty — one focused on grammar, one on meaning, one on long-range references. Each reviewer produces their own independent assessment of every sentence. The final output stitches all their notes side by side. No single reviewer needs to capture _everything_ — they specialize, and their combined output is richer than any one of them alone.

**How heads actually learn differently**: All heads receive the same input `x` and are constructed with identical arguments — so why do they learn different things? Because every time you instantiate a `CausalAttention`, its `W_query`, `W_key`, `W_value` are freshly randomly initialized by `nn.Linear`. Head 1 and Head 2 start from completely different weight values. From that point, backpropagation nudges each head's weights based on the gradient flowing through _that specific head's_ path in the computation graph. Since they started differently, and since each head's output occupies a different slice of the final concatenated vector, the gradients they receive are different too. Over many training steps they naturally drift toward capturing different patterns — this specialization is not designed in, it _emerges_.

---

### Why `nn.ModuleList` and not a plain Python list?

If you stored your heads in a regular Python list, PyTorch would be completely unaware they exist. Their parameters would be invisible to `model.parameters()`, they wouldn't move to GPU when you call `.to(device)`, and they wouldn't appear in `state_dict()` for saving and loading. `nn.ModuleList` is PyTorch's way of properly registering a list of submodules so all of that works automatically.

---

### The class

```python
class MultiHeadAttentionWrapper(nn.Module):

    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()

        # Create num_heads independent CausalAttention modules and register
        # them with PyTorch via nn.ModuleList (a plain Python list would
        # hide them from PyTorch's parameter tracking, device handling, etc.)
        # Each head gets the same constructor arguments but lands on different
        # random weights because nn.Linear reinitializes every time it is called
        heads_list = []
        for _ in range(num_heads):
            single_head = CausalAttention(d_in, d_out, context_length, dropout, qkv_bias)
            heads_list.append(single_head)

        self.heads = nn.ModuleList(heads_list)

    def forward(self, x):

        # Run every head on the same input x independently
        # Each head produces (batch, num_tokens, d_out)
        head_outputs = []
        for head in self.heads:
            head_outputs.append(head(x))

        # Concatenate along the last dimension (the feature/embedding dim)
        # Two heads with d_out=2 each → (batch, num_tokens, 4)
        # We are making each token's representation WIDER, not adding more tokens
        combined = torch.cat(head_outputs, dim=-1)
        return combined
```

### Running it

```python
torch.manual_seed(123)
context_length = batch.shape[1]  # 6 — number of tokens
d_in, d_out = 3, 2
mhaw = MultiHeadAttentionWrapper(d_in, d_out, context_length, 0.0, num_heads=2)

context_vecs = mhaw(batch)
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

### Reading the output

The output shape is `(2, 6, 4)` — batch size 2, 6 tokens, 4-dimensional context vector per token. That 4 comes from `d_out * num_heads = 2 * 2`. Each token's 4-dim vector is literally two 2-dim slices placed side by side:

```
token "Your" → [-0.4519,  0.2216,  |  0.4772,   0.1063 ]
               └── Head 1's view ─┘  └─ Head 2's view ─┘
```

You can verify Head 1's output directly — the first 2 columns `[-0.4519, 0.2216, ...]` are _identical_ to the standalone `CausalAttention` output from Section 8. That's because `torch.manual_seed(123)` followed by the first `CausalAttention(...)` call produces the exact same weights as the standalone example. Head 2 gets the next random initialization and produces the remaining 2 columns.

Both batch items are identical because `batch` was constructed by stacking two copies of the same `inputs` tensor.

### Why `dim=-1` for the concatenation?

`dim=-1` always means the last dimension. For our `(batch, num_tokens, d_out)` tensors, that is the feature/embedding dimension. Concatenating there makes each token's representation _wider_ — you are not adding more tokens, you are adding more information per token. If you mistakenly used `dim=0` or `dim=1` you would be stacking along batch or token dimensions, which would scramble the structure entirely.

### The limitation of this approach

Each of the `num_heads` `CausalAttention` instances runs its own full `nn.Linear` projections and its own matmuls — completely separately, in a Python `for` loop. On a GPU, launching many small sequential operations is much slower than one large batched operation. The model is also parameter-heavier than it needs to be. Section 10 — `MultiHeadAttention` — fixes both of these by projecting Q, K, V once at full width and then reshaping to split into heads, achieving the same result in a single fused tensor operation.

---

## 10 — 3.6.2 — `MultiHeadAttention`: The Efficient, Production Implementation

**Summary**: Instead of running `num_heads` separate small attention computations
in a Python loop, we run **one** attention computation with `d_out`-dimensional
Q/K/V projections, then _reshape_ the result to split the `d_out` dimension into
`num_heads` heads — each of size `head_dim = d_out // num_heads` — and do all the
attention math in one big batched tensor operation with no Python-level loop over
heads.

---

### Why bother? The problem with the Wrapper

In `MultiHeadAttentionWrapper`, every head ran its own separate `nn.Linear`
projection and its own matmul — one after another in a Python `for` loop. On a
CPU this is merely inefficient. On a GPU it is much worse: GPUs are designed to
do one _massive_ parallel operation, not many small sequential ones. Launching 8
separate small matmuls is far slower than launching one matmul that is 8x larger,
even though the total arithmetic is identical. `MultiHeadAttention` fixes this by
doing everything in one shot.

---

### The Core Idea: Project Once, Then Split

This is the single most important thing to understand about this class.

**Wrapper approach** — project into small then run separately:

```

Head 1: x → W_q1 (3×1) → q1 then attention independently
Head 2: x → W_q2 (3×1) → q2 then attention independently

```

**Efficient approach** — project into big then split:

```

x → W_query (3×2) → queries (batch, 6, 2)
↓
split into 2 heads along last dim
↓
Head 1 gets: queries[:, :, 0:1] shape (batch, 6, 1)
Head 2 gets: queries[:, :, 1:2] shape (batch, 6, 1)
↓
both processed in ONE batched matmul

```

The math is identical — the weights that Head 1 sees in the efficient version
correspond exactly to what a standalone Head 1 would have learned in the wrapper
version. But now it all happens in one GPU call.

---

### Theory: What is `head_dim` and why must `d_out % num_heads == 0`?

In `MultiHeadAttention`, `d_out` is the **total** output width you want — it must
equal `d_in` in GPT so blocks can be stacked (output of one block feeds the next).

`head_dim = d_out // num_heads` is how wide each individual head's Q, K, V vectors
are. For example with `d_out=4, num_heads=2`: each head works in a 2-dimensional
space. With `d_out=768, num_heads=12` (GPT-2 small): each head works in a
64-dimensional space.

The divisibility requirement `d_out % num_heads == 0` is simply because you cannot
split 5 features evenly into 2 heads — the split must be exact. If it is not, the
`.view()` reshape will fail.

The scaling factor inside softmax also changes: instead of dividing by
`sqrt(d_out)` like before, we now divide by `sqrt(head_dim)`. This is correct
because each head's dot product is a sum over `head_dim` dimensions, not `d_out`
dimensions — and the variance argument from Section 4 applies to the actual dot
product dimension.

---

### The Shape Transformation Story

This is the trickiest part of the whole chapter. Every line changes the shape, so
let's track it carefully with `b=2, num_tokens=6, d_in=3, d_out=2, num_heads=2,
head_dim=1`. We use letters instead of real numbers so you can track exactly where
each value goes after every transformation.

---

**Step 1 — Project: `x → queries, keys, values`**

One big linear projection per Q, K, V. Nothing is split into heads yet — this is
identical to what `CausalAttention` did. Each token gets a 2-dim query vector.

```
x.shape = (2, 6, 3)          ← (batch, tokens, d_in)

queries = W_query(x)
queries.shape = (2, 6, 2)    ← (batch, tokens, d_out)  — not split yet

Batch 0:                        Batch 1:  (identical, since batch = stack of same input)
  token 0  "Your"    → [a, b]     token 0  "Your"    → [a, b]
  token 1  "journey" → [c, d]     token 1  "journey" → [c, d]
  token 2  "starts"  → [e, f]     token 2  "starts"  → [e, f]
  token 3  "with"    → [g, h]     token 3  "with"    → [g, h]
  token 4  "one"     → [i, j]     token 4  "one"     → [i, j]
  token 5  "step"    → [k, l]     token 5  "step"    → [k, l]

(keys and values follow the same shape — skipped here for brevity)
```

**Matrix Visualization:**

```
x.shape = (2, 6, 3)    ← (batch, tokens, d_in)

x = [
      [                                  ← Batch 0
        [0.43, 0.15, 0.89],      ← "Your"
        [0.55, 0.87, 0.66],      ← "journey"
        [0.57, 0.85, 0.64],      ← "starts"
        [0.22, 0.58, 0.33],      ← "with"
        [0.77, 0.25, 0.10],      ← "one"
        [0.05, 0.80, 0.55]       ← "step"
      ],
      [                                  ← Batch 1 (identical)
        [0.43, 0.15, 0.89],      ← "Your"
        [0.55, 0.87, 0.66],      ← "journey"
        [0.57, 0.85, 0.64],      ← "starts"
        [0.22, 0.58, 0.33],      ← "with"
        [0.77, 0.25, 0.10],      ← "one"
        [0.05, 0.80, 0.55]       ← "step"
      ]
    ]
```

After passing through `W_query` — each 3-dim token vector gets projected down to
2-dim. We use letters to track where each value goes in later steps.

```
queries = W_query(x)
queries.shape = (2, 6, 2)    ← (batch, tokens, d_out)
                                 d_out=2 is the FULL width, not yet split into heads

queries = [
            [                     ← Batch 0
              [a, b],    ← "Your"    — a is position 0, b is position 1
              [c, d],    ← "journey"
              [e, f],    ← "starts"
              [g, h],    ← "with"
              [i, j],    ← "one"
              [k, l]     ← "step"
            ],
            [                     ← Batch 1 (identical values, same input)
              [a, b],    ← "Your"
              [c, d],    ← "journey"
              [e, f],    ← "starts"
              [g, h],    ← "with"
              [i, j],    ← "one"
              [k, l]     ← "step"
            ]
          ]

keys   = W_key(x)     → same shape (2, 6, 2), different values (W_key ≠ W_query)
values = W_value(x)   → same shape (2, 6, 2), different values (W_value ≠ W_query)
```

At this point each token's 2-dim vector is just a flat row — `[a, b]` for "Your",
`[c, d]` for "journey", and so on. The split into Head 1 and Head 2 has NOT
happened yet. Both `a` and `b` are sitting side by side with no head assignment.
Step 2 is where those two numbers get separated into their respective heads.

---

**The batches are identical by construction** — remember in the chapter, `batch` was created like this:

```python
batch = torch.stack((inputs, inputs), dim=0)
```

You literally stacked the same `inputs` tensor twice. So Batch 0 and Batch 1 have the exact same token embeddings going in, and therefore the exact same projected values coming out. That is why both batches show `[a, b]` for "Your" — it is not a mistake, it is just reflecting the fact that the input data is identical. In real training, each batch item would be a different sentence with completely different values.

**The heads being different is a separate story** — that has nothing to do with the batch dimension. The heads differ because after Step 2 and Step 3, `a` goes to Head 1 and `b` goes to Head 2. Those two values came from the same `W_query` projection, but they end up in different heads which then have their own separate attention computations with different score matrices and different attention weight distributions.

So to be precise:

```
Batch 0 = Batch 1       ← because we stacked the same input twice (artificial setup)
Head 1 ≠ Head 2         ← because a ≠ b, and they go through different attention paths
```

The weight initialization difference I mentioned earlier was about `W_query`, `W_key`, `W_value` being different across heads in the **Wrapper** version — where each `CausalAttention` had its own separate weight matrices. In `MultiHeadAttention` the split happens differently via `.view()`, but the end result is the same — `a` and `b` are different numbers because `W_query` projects into a 2-dim space and those two dimensions naturally carry different information.

**Step 2 — Reshape: split `d_out` into `(num_heads, head_dim)`**

`.view(b, num_tokens, num_heads, head_dim)` reinterprets the last dimension.
`d_out=2` becomes `(num_heads=2, head_dim=1)`. No data moves in memory — PyTorch
just changes how it reads the same bytes. The two numbers that were side by side
in a flat row are now read as two separate heads.

Before `.view()` — each token owns a flat 2-dim row, no head assignment yet:

```
queries.shape = (2, 6, 2)    ← (batch, tokens, d_out)

queries = [
            [              ← Batch 0
              [a, b],    ← "Your"    — both a and b belong to no head yet
              [c, d],    ← "journey"
              [e, f],    ← "starts"
              [g, h],    ← "with"
              [i, j],    ← "one"
              [k, l]     ← "step"
            ],           ← end Batch 0
            [              ← Batch 1 (identical)
              [a, b],    ← "Your"
              [c, d],    ← "journey"
              [e, f],    ← "starts"
              [g, h],    ← "with"
              [i, j],    ← "one"
              [k, l]     ← "step"
            ]            ← end Batch 1
          ]
```

After `.view(b, num_tokens, num_heads, head_dim)` — same data, now the last dim
`d_out=2` is read as `(num_heads=2, head_dim=1)`. Each token's flat `[a, b]` row
becomes `[[a], [b]]` — `a` is now Head 1's slot, `b` is now Head 2's slot:

Two way of visualization:  
**1st**

```
queries.shape = (2, 6, 2, 1)    ← (batch, tokens, heads, head_dim)

queries = [
            [                     ← Batch 0
              [[a], [b]],    ← "Your"    — [a] = Head 1,  [b] = Head 2
              [[c], [d]],    ← "journey" — [c] = Head 1,  [d] = Head 2
              [[e], [f]],    ← "starts"  — [e] = Head 1,  [f] = Head 2
              [[g], [h]],    ← "with"    — [g] = Head 1,  [h] = Head 2
              [[i], [j]],    ← "one"     — [i] = Head 1,  [j] = Head 2
              [[k], [l]]     ← "step"    — [k] = Head 1,  [l] = Head 2
            ],                ← end Batch 0
            [                     ← Batch 1 (identical)
              [[a], [b]],    ← "Your"
              [[c], [d]],    ← "journey"
              [[e], [f]],    ← "starts"
              [[g], [h]],    ← "with"
              [[i], [j]],    ← "one"
              [[k], [l]]     ← "step"
            ]                 ← end Batch 1
          ]

Indexing is now: queries[batch, token, head, head_dim_position]
  queries[0, 0, 0, 0] = a   ← Batch 0, "Your",    Head 1
  queries[0, 0, 1, 0] = b   ← Batch 0, "Your",    Head 2
  queries[0, 1, 0, 0] = c   ← Batch 0, "journey", Head 1
  queries[0, 1, 1, 0] = d   ← Batch 0, "journey", Head 2
```

**2nd**

```
queries.shape = (2, 6, 2, 1)    ← (batch, tokens, heads, head_dim)

queries = [
            [                         ← Batch 0
              [                  ← "Your"
                [a],             ← Head 1's query for "Your"
                [b]              ← Head 2's query for "Your"
              ],
              [                  ← "journey"
                [c],             ← Head 1's query for "journey"
                [d]              ← Head 2's query for "journey"
              ],
              [                  ← "starts"
                [e],             ← Head 1's query for "starts"
                [f]              ← Head 2's query for "starts"
              ],
              [                  ← "with"
                [g],             ← Head 1's query for "with"
                [h]              ← Head 2's query for "with"
              ],
              [                  ← "one"
                [i],             ← Head 1's query for "one"
                [j]              ← Head 2's query for "one"
              ],
              [                  ← "step"
                [k],             ← Head 1's query for "step"
                [l]              ← Head 2's query for "step"
              ]
            ],                        ← end Batch 0
            [                         ← Batch 1 (identical)
              [
                [a],
                [b]
              ],
              [
                [c],
                [d]
              ],
              [
                [e],
                [f]
              ],
              [
                [g],
                [h]
              ],
              [
                [i],
                [j]
              ],
              [
                [k],
                [l]
              ]
            ]                         ← end Batch 1
          ]

Indexing is now: queries[batch, token, head, head_dim_position]
  queries[0, 0, 0, 0] = a   ← Batch 0, "Your",    Head 1
  queries[0, 0, 1, 0] = b   ← Batch 0, "Your",    Head 2
  queries[0, 1, 0, 0] = c   ← Batch 0, "journey", Head 1
  queries[0, 1, 1, 0] = d   ← Batch 0, "journey", Head 2
```

Notice the data is still grouped by token — "Your" owns both `[a]` and `[b]`,
"journey" owns both `[c]` and `[d]`, and so on. Each token is still carrying both
heads' values together. Head 1 and Head 2 are not yet separated into their own
independent groups. Step 3 fixes that by transposing so heads come before tokens.

---

**Step 3 — Transpose: bring `num_heads` next to `batch`**

`.transpose(1, 2)` swaps dim 1 (`num_tokens=6`) and dim 2 (`num_heads=2`). No data
moves — only the indexing order changes. After this, each `[batch, head]` slice
contains that head's queries for ALL tokens, which is exactly what one head needs
to compute its own attention scores independently.

Before `.transpose(1, 2)` — grouped by token, each token owns both heads:

```
queries.shape = (2, 6, 2, 1)    ← (batch, tokens, heads, head_dim)

queries = [
            [                         ← Batch 0
              [                  ← Token 0 "Your"    — owns both heads
                [a],             ← Head 1's query for "Your"
                [b]              ← Head 2's query for "Your"
              ],
              [                  ← Token 1 "journey" — owns both heads
                [c],             ← Head 1's query for "journey"
                [d]              ← Head 2's query for "journey"
              ],
              [                  ← Token 2 "starts"  — owns both heads
                [e],             ← Head 1's query for "starts"
                [f]              ← Head 2's query for "starts"
              ],
              [                  ← Token 3 "with"    — owns both heads
                [g],             ← Head 1's query for "with"
                [h]              ← Head 2's query for "with"
              ],
              [                  ← Token 4 "one"     — owns both heads
                [i],             ← Head 1's query for "one"
                [j]              ← Head 2's query for "one"
              ],
              [                  ← Token 5 "step"    — owns both heads
                [k],             ← Head 1's query for "step"
                [l]              ← Head 2's query for "step"
              ]
            ],                        ← end Batch 0
            [                         ← Batch 1 (identical)
              [[a], [b]],        ← Token 0 "Your"    (Head 1, Head 2)
              [[c], [d]],        ← Token 1 "journey" (Head 1, Head 2)
              [[e], [f]],        ← Token 2 "starts"  (Head 1, Head 2)
              [[g], [h]],        ← Token 3 "with"    (Head 1, Head 2)
              [[i], [j]],        ← Token 4 "one"     (Head 1, Head 2)
              [[k], [l]]         ← Token 5 "step"    (Head 1, Head 2)
            ]                         ← end Batch 1
          ]
```

After `.transpose(1, 2)` — now grouped by head, each head owns all tokens:

```
queries.shape = (2, 2, 6, 1)    ← (batch, heads, tokens, head_dim)
                 ↑   ↑  ↑  ↑
               batch  │  │  head_dim
                    heads tokens
                    (swapped!)

queries = [
            [                         ← Batch 0
              [                  ← Head 1 — owns ALL tokens
                [a],             ← Token 0 "Your"    — Head 1's query
                [c],             ← Token 1 "journey" — Head 1's query
                [e],             ← Token 2 "starts"  — Head 1's query
                [g],             ← Token 3 "with"    — Head 1's query
                [i],             ← Token 4 "one"     — Head 1's query
                [k]              ← Token 5 "step"    — Head 1's query
              ],
              [                  ← Head 2 — owns ALL tokens
                [b],             ← Token 0 "Your"    — Head 2's query
                [d],             ← Token 1 "journey" — Head 2's query
                [f],             ← Token 2 "starts"  — Head 2's query
                [h],             ← Token 3 "with"    — Head 2's query
                [j],             ← Token 4 "one"     — Head 2's query
                [l]              ← Token 5 "step"    — Head 2's query
              ]
            ],                        ← end Batch 0
            [                         ← Batch 1 (identical)
              [                  ← Head 1 — owns ALL tokens
                [a],             ← Token 0 "Your"    — Head 1's query
                [c],             ← Token 1 "journey" — Head 1's query
                [e],             ← Token 2 "starts"  — Head 1's query
                [g],             ← Token 3 "with"    — Head 1's query
                [i],             ← Token 4 "one"     — Head 1's query
                [k]              ← Token 5 "step"    — Head 1's query
              ],
              [                  ← Head 2 — owns ALL tokens
                [b],             ← Token 0 "Your"    — Head 2's query
                [d],             ← Token 1 "journey" — Head 2's query
                [f],             ← Token 2 "starts"  — Head 2's query
                [h],             ← Token 3 "with"    — Head 2's query
                [j],             ← Token 4 "one"     — Head 2's query
                [l]              ← Token 5 "step"    — Head 2's query
              ]
            ]                         ← end Batch 1
          ]

Indexing is now: queries[batch, head, token, head_dim_position]
  queries[0, 0, 0, 0] = a   ← Batch 0, Head 1, Token 0 "Your"
  queries[0, 0, 1, 0] = c   ← Batch 0, Head 1, Token 1 "journey"
  queries[0, 1, 0, 0] = b   ← Batch 0, Head 2, Token 0 "Your"
  queries[0, 1, 1, 0] = d   ← Batch 0, Head 2, Token 1 "journey"
```

Each `[batch, head]` slice is now a self-contained `(6, 1)` matrix — all of one
head's queries across every token. PyTorch's batched matmul treats `(batch=2,
heads=2)` as the outer batch dimensions and runs 4 independent matmuls in one call:

```
  queries[0, 0, :, :] — Batch 0, Head 1: [[a], [c], [e], [g], [i], [k]]  shape (6, 1)
  queries[0, 1, :, :] — Batch 0, Head 2: [[b], [d], [f], [h], [j], [l]]  shape (6, 1)
  queries[1, 0, :, :] — Batch 1, Head 1: [[a], [c], [e], [g], [i], [k]]  shape (6, 1)
  queries[1, 1, :, :] — Batch 1, Head 2: [[b], [d], [f], [h], [j], [l]]  shape (6, 1)
```

If you had NOT transposed — a `[batch, token]` slice would give `(heads, head_dim)`
meaning two heads' queries for just ONE token. The matmul would compute scores
between heads instead of between tokens — completely wrong.

---

**Step 4 — Attention scores: `queries @ keys.transpose(2, 3)`**

We want Q @ K^T per head. Keys after step 3 have shape `(2, 2, 6, 1)`. We need to
transpose the last two dims of K — turning `(tokens, head_dim)` into
`(head_dim, tokens)` — so the matmul works out to `(tokens, tokens)` per head.
That is `transpose(2, 3)`, not `transpose(1, 2)`.

First, what `keys.transpose(2, 3)` does — swaps the last two dims of keys,
turning each head's `(6, 1)` column into a `(1, 6)` row:

```
keys.shape = (2, 2, 6, 1)    ← (batch, heads, tokens, head_dim)  — after Step 3

keys = [
         [                        ← Batch 0
           [                 ← Head 1 — owns ALL tokens
             [a'],           ← Token 0 "Your"    — Head 1's key
             [c'],           ← Token 1 "journey" — Head 1's key
             [e'],           ← Token 2 "starts"  — Head 1's key
             [g'],           ← Token 3 "with"    — Head 1's key
             [i'],           ← Token 4 "one"     — Head 1's key
             [k']            ← Token 5 "step"    — Head 1's key
           ],
           [                 ← Head 2 — owns ALL tokens
             [b'],           ← Token 0 "Your"    — Head 2's key
             [d'],           ← Token 1 "journey" — Head 2's key
             [f'],           ← Token 2 "starts"  — Head 2's key
             [h'],           ← Token 3 "with"    — Head 2's key
             [j'],           ← Token 4 "one"     — Head 2's key
             [l']            ← Token 5 "step"    — Head 2's key
           ]
         ],                       ← end Batch 0
         [                        ← Batch 1 (identical)
           [                      ← Head 1 — owns ALL tokens
             [a'], [c'], [e'], [g'], [i'], [k']
           ],
           [                      ← Head 2 — owns ALL tokens
             [b'], [d'], [f'], [h'], [j'], [l']
           ]
         ]                        ← end Batch 1
       ]

Note: keys use primed letters (a', b', ...) to show they are different values
from queries (a, b, ...) — W_key ≠ W_query so the projections differ.
```

After `keys.transpose(2, 3)` — each head's token column flipped into a row:

```
keys.transpose(2, 3).shape = (2, 2, 1, 6)    ← (batch, heads, head_dim, tokens)

keys.transpose(2, 3) = [
                          [                             ← Batch 0
                            [                      ← Head 1
                              [a', c', e', g', i', k']  ← all 6 token keys in one row
                            ],
                            [                      ← Head 2
                              [b', d', f', h', j', l']  ← all 6 token keys in one row
                            ]
                          ],                            ← end Batch 0
                          [                             ← Batch 1 (identical)
                            [[a', c', e', g', i', k']],
                            [[b', d', f', h', j', l']]
                          ]                             ← end Batch 1
                        ]
```

Now the matmul `queries @ keys.transpose(2, 3)` — PyTorch treats `(batch=2,
heads=2)` as outer batch dims and runs 4 independent `(6,1) @ (1,6)` matmuls,
each producing a `(6, 6)` score matrix:

```
queries[0, 0] @ keys.transpose(2,3)[0, 0]
= [[a],   @   [[a', c', e', g', i', k']]
   [c],
   [e],
   [g],
   [i],
   [k]]

= [                                              ← each row = one query token
    [a*a', a*c', a*e', a*g', a*i', a*k'],   ← Token 0 "Your"    attends to all
    [c*a', c*c', c*e', c*g', c*i', c*k'],   ← Token 1 "journey" attends to all
    [e*a', e*c', e*e', e*g', e*i', e*k'],   ← Token 2 "starts"  attends to all
    [g*a', g*c', g*e', g*g', g*i', g*k'],   ← Token 3 "with"    attends to all
    [i*a', i*c', i*e', i*g', i*i', i*k'],   ← Token 4 "one"     attends to all
    [k*a', k*c', k*e', k*g', k*i', k*k']    ← Token 5 "step"    attends to all
  ]
  shape: (6, 6)    ← Batch 0, Head 1's score matrix
```

All 4 matmuls happen in one GPU call, giving:

```
attn_scores.shape = (2, 2, 6, 6)    ← (batch, heads, tokens, tokens)

attn_scores = [
                [                         ← Batch 0
                  [                  ← Head 1's score matrix (6×6)
                    [a*a', a*c', a*e', a*g', a*i', a*k'],   ← "Your"    vs all
                    [c*a', c*c', c*e', c*g', c*i', c*k'],   ← "journey" vs all
                    [e*a', e*c', e*e', e*g', e*i', e*k'],   ← "starts"  vs all
                    [g*a', g*c', g*e', g*g', g*i', g*k'],   ← "with"    vs all
                    [i*a', i*c', i*e', i*g', i*i', i*k'],   ← "one"     vs all
                    [k*a', k*c', k*e', k*g', k*i', k*k']    ← "step"    vs all
                  ],
                  [                  ← Head 2's score matrix (6×6)
                    [b*b', b*d', b*f', b*h', b*j', b*l'],   ← "Your"    vs all
                    [d*b', d*d', d*f', d*h', d*j', d*l'],   ← "journey" vs all
                    [f*b', f*d', f*f', f*h', f*j', f*l'],   ← "starts"  vs all
                    [h*b', h*d', h*f', h*h', h*j', h*l'],   ← "with"    vs all
                    [j*b', j*d', j*f', j*h', j*j', j*l'],   ← "one"     vs all
                    [l*b', l*d', l*f', l*h', l*j', l*l']    ← "step"    vs all
                  ]
                ],                        ← end Batch 0
                [                         ← Batch 1 (identical to Batch 0)
                  [... Head 1's score matrix ...],
                  [... Head 2's score matrix ...]
                ]                         ← end Batch 1
              ]

Head 1 and Head 2 produce DIFFERENT score matrices because a ≠ b and a' ≠ b'
— the two heads projected the same input tokens into different query and key
spaces, so they measure token similarity differently.
```

---

**Step 5 — Mask, scale, softmax, dropout**

Same logic as `CausalAttention`, just 4D now. The causal mask and softmax both
operate on the last two dimensions `(tokens, tokens)` — so nothing conceptually
new here, just one extra dimension to carry around.

We have 4 independent score matrices coming in — one per `(batch, head)` combo.
Each one gets masked, scaled, and softmaxed completely independently.

**Sub-step 5a — Apply causal mask (upper triangle → -inf)**

The mask prevents each token from attending to future tokens. Same `torch.triu`
mask from `CausalAttention`, just broadcast across the `(batch, heads)` dims:

```
mask = [            ← shape (6, 6), broadcast over (batch=2, heads=2) automatically
  [0, 1, 1, 1, 1, 1],   ← "Your"    can only see itself
  [0, 0, 1, 1, 1, 1],   ← "journey" can see "Your" and itself
  [0, 0, 0, 1, 1, 1],   ← "starts"  can see tokens 0-2
  [0, 0, 0, 0, 1, 1],   ← "with"    can see tokens 0-3
  [0, 0, 0, 0, 0, 1],   ← "one"     can see tokens 0-4
  [0, 0, 0, 0, 0, 0]    ← "step"    can see all tokens
]
where 1 → replace with -inf,  0 → keep the score

After masking — shown for Batch 0, Head 1:

attn_scores[0, 0] = [
  [a*a',   -inf,   -inf,   -inf,   -inf,   -inf],  ← "Your"    — only sees itself
  [c*a', c*c',     -inf,   -inf,   -inf,   -inf],  ← "journey" — sees 2 tokens
  [e*a', e*c',   e*e',     -inf,   -inf,   -inf],  ← "starts"  — sees 3 tokens
  [g*a', g*c',   g*e',   g*g',     -inf,   -inf],  ← "with"    — sees 4 tokens
  [i*a', i*c',   i*e',   i*g',   i*i',     -inf],  ← "one"     — sees 5 tokens
  [k*a', k*c',   k*e',   k*g',   k*i',   k*k' ]   ← "step"    — sees all 6
]

Batch 0, Head 2 gets the same mask pattern but on different score values:

attn_scores[0, 1] = [
  [b*b',   -inf,   -inf,   -inf,   -inf,   -inf],  ← "Your"
  [d*b', d*d',     -inf,   -inf,   -inf,   -inf],  ← "journey"
  [f*b', f*d',   f*f',     -inf,   -inf,   -inf],  ← "starts"
  [h*b', h*d',   h*f',   h*h',     -inf,   -inf],  ← "with"
  [j*b', j*d',   j*f',   j*h',   j*j',     -inf],  ← "one"
  [l*b', l*d',   l*f',   l*h',   l*j',   l*l' ]   ← "step"
]
```

**Sub-step 5b — Scale by `1 / sqrt(head_dim)`**

We divide by `sqrt(head_dim)=sqrt(1)=1` in our toy example, so the numbers do
not change here. In a real model with larger `head_dim` (e.g. 64 in GPT-2), this
scaling matters — it prevents dot products from growing too large and pushing
softmax into a saturated, near-zero-gradient region. We divide by `sqrt(head_dim)`
and NOT `sqrt(d_out)` because each head's dot product sums over `head_dim`
dimensions, not `d_out` dimensions — that is what controls the variance.

```
attn_scores[0, 0] after scaling (head_dim=1, so unchanged here):

[
  [a*a',   -inf,   -inf,   -inf,   -inf,   -inf],
  [c*a', c*c',     -inf,   -inf,   -inf,   -inf],
  [e*a', e*c',   e*e',     -inf,   -inf,   -inf],
  [g*a', g*c',   g*e',   g*g',     -inf,   -inf],
  [i*a', i*c',   i*e',   i*g',   i*i',     -inf],
  [k*a', k*c',   k*e',   k*g',   k*i',   k*k' ]
]
```

**Sub-step 5c — Softmax along `dim=-1`**

Softmax is applied row by row — each token gets its own probability distribution
over the tokens it is allowed to attend to. `-inf` entries become exactly `0`
after softmax (`e^-inf = 0`), so future tokens vanish cleanly without any
renormalization step needed.

```
attn_weights.shape = (2, 2, 6, 6)    ← same shape, values now sum to 1 per row

attn_weights[0, 0] = [          ← Batch 0, Head 1 — after softmax
  [1.0,    0,      0,      0,      0,      0   ],  ← "Your"    — 100% on itself
  [w_ca, w_cc,     0,      0,      0,      0   ],  ← "journey" — split over 2 tokens
  [w_ea, w_ec,   w_ee,     0,      0,      0   ],  ← "starts"  — split over 3 tokens
  [w_ga, w_gc,   w_ge,  w_gg,      0,      0   ],  ← "with"    — split over 4 tokens
  [w_ia, w_ic,   w_ie,  w_ig,   w_ii,      0   ],  ← "one"     — split over 5 tokens
  [w_ka, w_kc,   w_ke,  w_kg,   w_ki,     w_kk ]   ← "step"    — split over 6 tokens
]
where each row sums to 1.0

attn_weights[0, 1] = [          ← Batch 0, Head 2 — different values, same structure
  [1.0,    0,      0,      0,      0,      0   ],
  [w_db, w_dd,     0,      0,      0,      0   ],
  [w_fb, w_fd,   w_ff,     0,      0,      0   ],
  [w_hb, w_hd,   w_hf,  w_hh,      0,      0   ],
  [w_jb, w_jd,   w_jf,  w_jh,   w_jj,      0   ],
  [w_lb, w_ld,   w_lf,  w_lh,   w_lj,     w_ll ]
]

Head 1 and Head 2 have completely different weight values — same triangular
structure enforced by the mask, but different attention distributions because
their score matrices a*a', c*a'... vs b*b', d*b'... came from different
query and key projections.
```

**Sub-step 5d — Dropout**

Randomly zeroes out some attention weights during training and scales the
survivors by `1/(1-p)` to keep expected values unchanged. At `dropout=0.0`
(as in our test) nothing changes. The shape stays `(2, 2, 6, 6)` throughout.

```
attn_weights.shape = (2, 2, 6, 6)    ← unchanged by dropout at rate 0.0
```

---

**Step 6 — Context vectors: `attn_weights @ values`**

This is the exact same weighted-sum operation `CausalAttention` did, just
running once per `(batch, head)` slice instead of once per call. Each head
blends the value vectors of every token it is allowed to see, using the
attention weights it computed for itself in Step 5.

First, what `values` looks like after Step 3 — same shape and structure as
`keys`, but produced by `W_value`, so we use double-primed letters (`a''`,
`b''`, ...) to keep queries, keys, and values visually distinct:

```
values.shape = (2, 2, 6, 1)    ← (batch, heads, tokens, head_dim)
               ↑   ↑  ↑  ↑
             batch heads tokens head_dim

values = [
           [                        ← Batch 0
             [                 ← Head 1 — owns ALL tokens
               [a''],          ← Token 0 "Your"    — Head 1's value
               [c''],          ← Token 1 "journey" — Head 1's value
               [e''],          ← Token 2 "starts"  — Head 1's value
               [g''],          ← Token 3 "with"    — Head 1's value
               [i''],          ← Token 4 "one"     — Head 1's value
               [k'']           ← Token 5 "step"    — Head 1's value
             ],
             [                 ← Head 2 — owns ALL tokens
               [b''],          ← Token 0 "Your"    — Head 2's value
               [d''],          ← Token 1 "journey" — Head 2's value
               [f''],          ← Token 2 "starts"  — Head 2's value
               [h''],          ← Token 3 "with"    — Head 2's value
               [j''],          ← Token 4 "one"     — Head 2's value
               [l'']           ← Token 5 "step"    — Head 2's value
             ]
           ],                       ← end Batch 0
           [                        ← Batch 1 (identical)
             [                 ← Head 1 — owns ALL tokens
               [a''],          ← Token 0 "Your"    — Head 1's value
               [c''],          ← Token 1 "journey" — Head 1's value
               [e''],          ← Token 2 "starts"  — Head 1's value
               [g''],          ← Token 3 "with"    — Head 1's value
               [i''],          ← Token 4 "one"     — Head 1's value
               [k'']           ← Token 5 "step"    — Head 1's value
             ],
             [                 ← Head 2 — owns ALL tokens
               [b''],          ← Token 0 "Your"    — Head 2's value
               [d''],          ← Token 1 "journey" — Head 2's value
               [f''],          ← Token 2 "starts"  — Head 2's value
               [h''],          ← Token 3 "with"    — Head 2's value
               [j''],          ← Token 4 "one"     — Head 2's value
               [l'']           ← Token 5 "step"    — Head 2's value
             ]
           ]                        ← end Batch 1
         ]

Note: values use double-primed letters (a'', b'', ...) — different numbers
from both queries (a, b, ...) and keys (a', b', ...), since
W_value ≠ W_query ≠ W_key.
```

Now the matmul `attn_weights @ values` — PyTorch treats `(batch=2, heads=2)`
as outer batch dims and runs 4 independent `(6, 6) @ (6, 1)` matmuls, each
producing a `(6, 1)` column of context vectors:

```
attn_weights[0, 0] @ values[0, 0]      ← Batch 0, Head 1

  [1.0,    0,      0,      0,      0,      0   ]      [a'']
  [w_ca, w_cc,     0,      0,      0,      0   ]      [c'']
  [w_ea, w_ec,   w_ee,     0,      0,      0   ]   @  [e'']
  [w_ga, w_gc,   w_ge,  w_gg,      0,      0   ]      [g'']
  [w_ia, w_ic,   w_ie,  w_ig,   w_ii,      0   ]      [i'']
  [w_ka, w_kc,   w_ke,  w_kg,   w_ki,   w_kk  ]      [k'']

= [
    [1.0*a''                                                          ],  ← "Your"    — sees only itself
    [w_ca*a'' + w_cc*c''                                              ],  ← "journey" — blends 2 values
    [w_ea*a'' + w_ec*c'' + w_ee*e''                                   ],  ← "starts"  — blends 3 values
    [w_ga*a'' + w_gc*c'' + w_ge*e'' + w_gg*g''                        ],  ← "with"    — blends 4 values
    [w_ia*a'' + w_ic*c'' + w_ie*e'' + w_ig*g'' + w_ii*i''             ],  ← "one"     — blends 5 values
    [w_ka*a'' + w_kc*c'' + w_ke*e'' + w_kg*g'' + w_ki*i'' + w_kk*k'' ]   ← "step"    — blends 6 values
  ]
  shape: (6, 1)    ← Batch 0, Head 1's context vectors, one per token

We label these six results ca, cc, ce, cg, ci, ck — each name keeps the query
letter of the token it belongs to so you can trace it straight back to Step 1.
```

Head 2 runs the identical mechanics on its own numbers:

```
attn_weights[0, 1] @ values[0, 1]      ← Batch 0, Head 2

= [
    [1.0*b''                                                              ],  ← "Your"
    [w_db*b'' + w_dd*d''                                                  ],  ← "journey"
    [w_fb*b'' + w_fd*d'' + w_ff*f''                                       ],  ← "starts"
    [w_hb*b'' + w_hd*d'' + w_hf*f'' + w_hh*h''                            ],  ← "with"
    [w_jb*b'' + w_jd*d'' + w_jf*f'' + w_jh*h'' + w_jj*j''                 ],  ← "one"
    [w_lb*b'' + w_ld*d'' + w_lf*f'' + w_lh*h'' + w_lj*j'' + w_ll*l''     ]   ← "step"
  ]
  shape: (6, 1)    ← Batch 0, Head 2's context vectors

We label these cb, cd, cf, ch, cj, cl.
```

All 4 `(batch, head)` matmuls happen in one GPU call, giving:

```
context_vec.shape = (2, 2, 6, 1)    ← (batch, heads, tokens, head_dim)
                     ↑   ↑  ↑  ↑
                   batch heads tokens head_dim

context_vec = [
                [                         ← Batch 0
                  [                  ← Head 1 — owns ALL tokens
                    [ca],            ← Token 0 "Your"    — Head 1's context
                    [cc],            ← Token 1 "journey" — Head 1's context
                    [ce],            ← Token 2 "starts"  — Head 1's context
                    [cg],            ← Token 3 "with"    — Head 1's context
                    [ci],            ← Token 4 "one"     — Head 1's context
                    [ck]             ← Token 5 "step"    — Head 1's context
                  ],
                  [                  ← Head 2 — owns ALL tokens
                    [cb],            ← Token 0 "Your"    — Head 2's context
                    [cd],            ← Token 1 "journey" — Head 2's context
                    [cf],            ← Token 2 "starts"  — Head 2's context
                    [ch],            ← Token 3 "with"    — Head 2's context
                    [cj],            ← Token 4 "one"     — Head 2's context
                    [cl]             ← Token 5 "step"    — Head 2's context
                  ]
                ],                        ← end Batch 0
                [                         ← Batch 1 (identical)
                  [                  ← Head 1 — owns ALL tokens
                    [ca],            ← Token 0 "Your"    — Head 1's context
                    [cc],            ← Token 1 "journey" — Head 1's context
                    [ce],            ← Token 2 "starts"  — Head 1's context
                    [cg],            ← Token 3 "with"    — Head 1's context
                    [ci],            ← Token 4 "one"     — Head 1's context
                    [ck]             ← Token 5 "step"    — Head 1's context
                  ],
                  [                  ← Head 2 — owns ALL tokens
                    [cb],            ← Token 0 "Your"    — Head 2's context
                    [cd],            ← Token 1 "journey" — Head 2's context
                    [cf],            ← Token 2 "starts"  — Head 2's context
                    [ch],            ← Token 3 "with"    — Head 2's context
                    [cj],            ← Token 4 "one"     — Head 2's context
                    [cl]             ← Token 5 "step"    — Head 2's context
                  ]
                ]                         ← end Batch 1
              ]

Indexing is now: context_vec[batch, head, token, head_dim_position]
  context_vec[0, 0, 0, 0] = ca   ← Batch 0, Head 1, Token 0 "Your"
  context_vec[0, 0, 1, 0] = cc   ← Batch 0, Head 1, Token 1 "journey"
  context_vec[0, 1, 0, 0] = cb   ← Batch 0, Head 2, Token 0 "Your"
  context_vec[0, 1, 1, 0] = cd   ← Batch 0, Head 2, Token 1 "journey"
```

Each head has produced its own independent context vector for every token,
built entirely from its own query/key/value projections and its own attention
weights. The two heads are still sitting in separate slots — `ca` and `cb` both
describe "Your", but from two completely different points of view. They are not
yet combined. Step 7 starts putting them back together.

---

**Step 7 — Transpose back: bring `num_tokens` back to position 1**

`.transpose(1, 2)` swaps `heads` and `tokens` back. We are exactly reversing
Step 3 — putting tokens back at position 1 so the shape matches what the rest
of PyTorch expects `(batch, tokens, features)`. No data moves, only the indexing
order changes.

Before `.transpose(1, 2)` — this is exactly Step 6's output, grouped by head,
each head owning all tokens:

```
context_vec.shape = (2, 2, 6, 1)    ← (batch, heads, tokens, head_dim)
                     ↑   ↑  ↑  ↑
                   batch heads tokens head_dim

context_vec = [
                [                         ← Batch 0
                  [                  ← Head 1 — owns ALL tokens
                    [ca],            ← Token 0 "Your"    — Head 1's context
                    [cc],            ← Token 1 "journey" — Head 1's context
                    [ce],            ← Token 2 "starts"  — Head 1's context
                    [cg],            ← Token 3 "with"    — Head 1's context
                    [ci],            ← Token 4 "one"     — Head 1's context
                    [ck]             ← Token 5 "step"    — Head 1's context
                  ],
                  [                  ← Head 2 — owns ALL tokens
                    [cb],            ← Token 0 "Your"    — Head 2's context
                    [cd],            ← Token 1 "journey" — Head 2's context
                    [cf],            ← Token 2 "starts"  — Head 2's context
                    [ch],            ← Token 3 "with"    — Head 2's context
                    [cj],            ← Token 4 "one"     — Head 2's context
                    [cl]             ← Token 5 "step"    — Head 2's context
                  ]
                ],                        ← end Batch 0
                [                         ← Batch 1 (identical)
                  [                  ← Head 1 — owns ALL tokens
                    [ca],            ← Token 0 "Your"    — Head 1's context
                    [cc],            ← Token 1 "journey" — Head 1's context
                    [ce],            ← Token 2 "starts"  — Head 1's context
                    [cg],            ← Token 3 "with"    — Head 1's context
                    [ci],            ← Token 4 "one"     — Head 1's context
                    [ck]             ← Token 5 "step"    — Head 1's context
                  ],
                  [                  ← Head 2 — owns ALL tokens
                    [cb],            ← Token 0 "Your"    — Head 2's context
                    [cd],            ← Token 1 "journey" — Head 2's context
                    [cf],            ← Token 2 "starts"  — Head 2's context
                    [ch],            ← Token 3 "with"    — Head 2's context
                    [cj],            ← Token 4 "one"     — Head 2's context
                    [cl]             ← Token 5 "step"    — Head 2's context
                  ]
                ]                         ← end Batch 1
              ]
```

After `.transpose(1, 2)` — now grouped by token again, each token owns both
heads' results side by side:

```
context_vec.shape = (2, 6, 2, 1)    ← (batch, tokens, heads, head_dim)
                     ↑  ↑   ↑  ↑
                   batch tokens heads head_dim
                              (swapped back!)

context_vec = [
                [                         ← Batch 0
                  [                  ← Token 0 "Your"    — owns both heads
                    [ca],            ← Head 1's context for "Your"
                    [cb]             ← Head 2's context for "Your"
                  ],
                  [                  ← Token 1 "journey" — owns both heads
                    [cc],            ← Head 1's context for "journey"
                    [cd]             ← Head 2's context for "journey"
                  ],
                  [                  ← Token 2 "starts"  — owns both heads
                    [ce],            ← Head 1's context for "starts"
                    [cf]             ← Head 2's context for "starts"
                  ],
                  [                  ← Token 3 "with"    — owns both heads
                    [cg],            ← Head 1's context for "with"
                    [ch]             ← Head 2's context for "with"
                  ],
                  [                  ← Token 4 "one"     — owns both heads
                    [ci],            ← Head 1's context for "one"
                    [cj]             ← Head 2's context for "one"
                  ],
                  [                  ← Token 5 "step"    — owns both heads
                    [ck],            ← Head 1's context for "step"
                    [cl]             ← Head 2's context for "step"
                  ]
                ],                        ← end Batch 0
                [                         ← Batch 1 (identical)
                  [                  ← Token 0 "Your"
                    [ca],            ← Head 1's context for "Your"
                    [cb]             ← Head 2's context for "Your"
                  ],
                  [                  ← Token 1 "journey"
                    [cc],            ← Head 1's context for "journey"
                    [cd]             ← Head 2's context for "journey"
                  ],
                  [                  ← Token 2 "starts"
                    [ce],            ← Head 1's context for "starts"
                    [cf]             ← Head 2's context for "starts"
                  ],
                  [                  ← Token 3 "with"
                    [cg],            ← Head 1's context for "with"
                    [ch]             ← Head 2's context for "with"
                  ],
                  [                  ← Token 4 "one"
                    [ci],            ← Head 1's context for "one"
                    [cj]             ← Head 2's context for "one"
                  ],
                  [                  ← Token 5 "step"
                    [ck],            ← Head 1's context for "step"
                    [cl]             ← Head 2's context for "step"
                  ]
                ]                         ← end Batch 1
              ]

Indexing is now: context_vec[batch, token, head, head_dim_position]
  context_vec[0, 0, 0, 0] = ca   ← Batch 0, Token 0 "Your",    Head 1
  context_vec[0, 0, 1, 0] = cb   ← Batch 0, Token 0 "Your",    Head 2
  context_vec[0, 1, 0, 0] = cc   ← Batch 0, Token 1 "journey", Head 1
  context_vec[0, 1, 1, 0] = cd   ← Batch 0, Token 1 "journey", Head 2
```

Compare this directly to Step 2's "before transpose" picture — same shape
`(2, 6, 2, 1)`, same grouping by token, same nesting structure. We have come
full circle on the shape. But the values inside are completely different — in
Step 2 these slots held raw `W_query` projections (`a, b, c, d, ...`), now
they hold context vectors (`ca, cb, cc, cd, ...`) that have each been blended
across every token that head was allowed to see.

---

**Step 8 — Merge heads back into `d_out`**

`.contiguous()` first — `.transpose()` only changes stride metadata, not actual
memory layout, leaving the tensor non-contiguous. `.view()` requires contiguous
memory, so `.contiguous()` makes a proper copy with the right layout first.

Then `.view(b, num_tokens, d_out)` merges `(num_heads=2, head_dim=1)` back into
`d_out=2` — the exact inverse of Step 2's `.view()`. Each token's two
single-number head outputs become one flat 2-dim row again.

Before `.view()` — this is exactly Step 7's output, grouped by token, heads
still in their own slot:

```
context_vec.shape = (2, 6, 2, 1)    ← (batch, tokens, heads, head_dim)
                     ↑  ↑   ↑  ↑
                   batch tokens heads head_dim

context_vec = [
                [                         ← Batch 0
                  [                  ← Token 0 "Your"    — owns both heads
                    [ca],            ← Head 1's context for "Your"
                    [cb]             ← Head 2's context for "Your"
                  ],
                  [                  ← Token 1 "journey" — owns both heads
                    [cc],            ← Head 1's context for "journey"
                    [cd]             ← Head 2's context for "journey"
                  ],
                  [                  ← Token 2 "starts"  — owns both heads
                    [ce],            ← Head 1's context for "starts"
                    [cf]             ← Head 2's context for "starts"
                  ],
                  [                  ← Token 3 "with"    — owns both heads
                    [cg],            ← Head 1's context for "with"
                    [ch]             ← Head 2's context for "with"
                  ],
                  [                  ← Token 4 "one"     — owns both heads
                    [ci],            ← Head 1's context for "one"
                    [cj]             ← Head 2's context for "one"
                  ],
                  [                  ← Token 5 "step"    — owns both heads
                    [ck],            ← Head 1's context for "step"
                    [cl]             ← Head 2's context for "step"
                  ]
                ],                        ← end Batch 0
                [                         ← Batch 1 (identical)
                  [                  ← Token 0 "Your"
                    [ca],            ← Head 1's context for "Your"
                    [cb]             ← Head 2's context for "Your"
                  ],
                  [                  ← Token 1 "journey"
                    [cc],            ← Head 1's context for "journey"
                    [cd]             ← Head 2's context for "journey"
                  ],
                  [                  ← Token 2 "starts"
                    [ce],            ← Head 1's context for "starts"
                    [cf]             ← Head 2's context for "starts"
                  ],
                  [                  ← Token 3 "with"
                    [cg],            ← Head 1's context for "with"
                    [ch]             ← Head 2's context for "with"
                  ],
                  [                  ← Token 4 "one"
                    [ci],            ← Head 1's context for "one"
                    [cj]             ← Head 2's context for "one"
                  ],
                  [                  ← Token 5 "step"
                    [ck],            ← Head 1's context for "step"
                    [cl]             ← Head 2's context for "step"
                  ]
                ]                         ← end Batch 1
              ]
```

After `.contiguous().view(b, num_tokens, d_out)` — the `(heads=2, head_dim=1)`
last two dims collapse into a single flat `d_out=2` dim. Each token's two head
slots become one flat row again — the exact inverse of Step 2:

```
context_vec.shape = (2, 6, 2)    ← (batch, tokens, d_out)
                     ↑  ↑  ↑
                   batch tokens d_out

context_vec = [
                [                              ← Batch 0
                  [ca, cb],    ← Token 0 "Your"    — Head 1 || Head 2 (naively stitched)
                  [cc, cd],    ← Token 1 "journey" — Head 1 || Head 2 (naively stitched)
                  [ce, cf],    ← Token 2 "starts"  — Head 1 || Head 2 (naively stitched)
                  [cg, ch],    ← Token 3 "with"    — Head 1 || Head 2 (naively stitched)
                  [ci, cj],    ← Token 4 "one"     — Head 1 || Head 2 (naively stitched)
                  [ck, cl]     ← Token 5 "step"    — Head 1 || Head 2 (naively stitched)
                ],                             ← end Batch 0
                [                              ← Batch 1 (identical)
                  [ca, cb],    ← Token 0 "Your"
                  [cc, cd],    ← Token 1 "journey"
                  [ce, cf],    ← Token 2 "starts"
                  [cg, ch],    ← Token 3 "with"
                  [ci, cj],    ← Token 4 "one"
                  [ck, cl]     ← Token 5 "step"
                ]                              ← end Batch 1
              ]

Indexing is now: context_vec[batch, token, d_out_position]
  context_vec[0, 0, 0] = ca   ← Batch 0, Token 0 "Your",    Head 1's value
  context_vec[0, 0, 1] = cb   ← Batch 0, Token 0 "Your",    Head 2's value
  context_vec[0, 1, 0] = cc   ← Batch 0, Token 1 "journey", Head 1's value
  context_vec[0, 1, 1] = cd   ← Batch 0, Token 1 "journey", Head 2's value
```

Notice the shape is back to 3D — `(batch, tokens, d_out)` — same as what came
out of Step 1's projection. We have gone from 3D → 4D → 4D → 3D across steps
1 through 8. But the content is completely transformed: what started as raw
linear projections is now context-aware blended representations from two
independent attention heads.

At this point `ca` and `cb` are adjacent in memory but mathematically
untouched by one another — Head 1 has no idea what Head 2 found, and vice
versa. The values are naively stitched side by side with no mixing. Step 9
fixes that.

---

**Step 9 — Output projection: mix across heads**

`out_proj` is `nn.Linear(d_out, d_out)` — a learned `(2, 2)` weight matrix.
It takes all `d_out=2` features of each token and produces new `d_out=2`
features. Critically, every output value is a weighted combination of BOTH
heads' inputs — so information can finally flow between what Head 1 and Head 2
found independently.

Before `out_proj` — this is exactly Step 8's output, heads naively stitched:

```
context_vec.shape = (2, 6, 2)    ← (batch, tokens, d_out)
                     ↑  ↑  ↑
                   batch tokens d_out

context_vec = [
                [                              ← Batch 0
                  [ca, cb],    ← Token 0 "Your"    — Head 1 || Head 2 (not yet mixed)
                  [cc, cd],    ← Token 1 "journey" — Head 1 || Head 2 (not yet mixed)
                  [ce, cf],    ← Token 2 "starts"  — Head 1 || Head 2 (not yet mixed)
                  [cg, ch],    ← Token 3 "with"    — Head 1 || Head 2 (not yet mixed)
                  [ci, cj],    ← Token 4 "one"     — Head 1 || Head 2 (not yet mixed)
                  [ck, cl]     ← Token 5 "step"    — Head 1 || Head 2 (not yet mixed)
                ],                             ← end Batch 0
                [                              ← Batch 1 (identical)
                  [ca, cb],    ← Token 0 "Your"
                  [cc, cd],    ← Token 1 "journey"
                  [ce, cf],    ← Token 2 "starts"
                  [cg, ch],    ← Token 3 "with"
                  [ci, cj],    ← Token 4 "one"
                  [ck, cl]     ← Token 5 "step"
                ]                              ← end Batch 1
              ]
```

What `out_proj` does — for each token, it multiplies the token's full `d_out=2`
vector by `W_out` (shape `(2, 2)`). Every output dimension receives contributions
from BOTH head slots:

```
out_proj weight matrix W_out shape: (2, 2)

    W_out = [ [W[0,0], W[0,1]],     ← weights for producing output dim 0
              [W[1,0], W[1,1]] ]    ← weights for producing output dim 1

For any token with input [Head1_value, Head2_value]:

  new[0] = W[0,0] * Head1_value + W[0,1] * Head2_value   ← output dim 0 mixes BOTH heads
  new[1] = W[1,0] * Head1_value + W[1,1] * Head2_value   ← output dim 1 mixes BOTH heads
```

Applied to every token in Batch 0:

```
Token 0 "Your"    — input [ca, cb]:
  new[0] = W[0,0]*ca + W[0,1]*cb
  new[1] = W[1,0]*ca + W[1,1]*cb
  output → [new_a0, new_a1]

Token 1 "journey" — input [cc, cd]:
  new[0] = W[0,0]*cc + W[0,1]*cd
  new[1] = W[1,0]*cc + W[1,1]*cd
  output → [new_c0, new_c1]

Token 2 "starts"  — input [ce, cf]:
  new[0] = W[0,0]*ce + W[0,1]*cf
  new[1] = W[1,0]*ce + W[1,1]*cf
  output → [new_e0, new_e1]

Token 3 "with"    — input [cg, ch]:
  new[0] = W[0,0]*cg + W[0,1]*ch
  new[1] = W[1,0]*cg + W[1,1]*ch
  output → [new_g0, new_g1]

Token 4 "one"     — input [ci, cj]:
  new[0] = W[0,0]*ci + W[0,1]*cj
  new[1] = W[1,0]*ci + W[1,1]*cj
  output → [new_i0, new_i1]

Token 5 "step"    — input [ck, cl]:
  new[0] = W[0,0]*ck + W[0,1]*cl
  new[1] = W[1,0]*ck + W[1,1]*cl
  output → [new_k0, new_k1]

We label each result new_<letter>0 and new_<letter>1, keeping the query letter
of the token so it stays traceable back to Step 1.
```

After `out_proj` — same shape, but every value now carries information from
both heads:

```
context_vec.shape = (2, 6, 2)    ← (batch, tokens, d_out) — unchanged
                     ↑  ↑  ↑
                   batch tokens d_out

context_vec = [
                [                                   ← Batch 0
                  [new_a0, new_a1],    ← Token 0 "Your"    — both heads mixed
                  [new_c0, new_c1],    ← Token 1 "journey" — both heads mixed
                  [new_e0, new_e1],    ← Token 2 "starts"  — both heads mixed
                  [new_g0, new_g1],    ← Token 3 "with"    — both heads mixed
                  [new_i0, new_i1],    ← Token 4 "one"     — both heads mixed
                  [new_k0, new_k1]     ← Token 5 "step"    — both heads mixed
                ],                                  ← end Batch 0
                [                                   ← Batch 1 (identical)
                  [new_a0, new_a1],    ← Token 0 "Your"
                  [new_c0, new_c1],    ← Token 1 "journey"
                  [new_e0, new_e1],    ← Token 2 "starts"
                  [new_g0, new_g1],    ← Token 3 "with"
                  [new_i0, new_i1],    ← Token 4 "one"
                  [new_k0, new_k1]     ← Token 5 "step"
                ]                                   ← end Batch 1
              ]

Indexing is now: context_vec[batch, token, d_out_position]
  context_vec[0, 1, 0] = new_c0   ← Batch 0, "journey", output dim 0
                                      = W[0,0]*cc + W[0,1]*cd
                                        ↑ Head 1's answer for "journey"
                                                    ↑ Head 2's answer for "journey"

  context_vec[0, 1, 1] = new_c1   ← Batch 0, "journey", output dim 1
                                      = W[1,0]*cc + W[1,1]*cd
                                        ↑ Head 1's answer for "journey"
                                                    ↑ Head 2's answer for "journey"
```

The shape stays `(2, 6, 2)` — same as what entered `out_proj`. But the content
has completely transformed:

```
Before out_proj:   [cc, cd]          — Head 1's answer || Head 2's answer, untouched
After  out_proj:   [new_c0, new_c1]  — every dim is a learned mix of both heads
```

The model learns `W_out` during training — deciding which combinations of head
outputs are most useful. "Head 1 noticed a syntactic subject AND Head 2 noticed
a pronoun reference → these two together should produce a strong noun-like
output signal" is the kind of relationship `W_out` can learn to encode.

This `context_vec` is the final return value of `MultiHeadAttention.forward()`.
The shape `(batch, tokens, d_out)` matches the input shape `(batch, tokens,
d_in)` exactly — which is why transformer blocks can be stacked, the output
of one feeds directly into the next with no reshaping needed.

---

### Dry Run: Watching "journey" Flow Through Every Step

Let's trace just Token 1 "journey" through the full shape transformation, using
the same letters from the shape story above so you can cross-reference exactly.
Settings: `b=2, num_tokens=6, d_in=3, d_out=2, num_heads=2, head_dim=1`.

**Before anything — "journey"'s raw embedding (Step 1 input):**

```
x[0, 1, :] = [0.55, 0.87, 0.66]    shape: (3,)    ← d_in=3
```

**After `W_query` projection — flat row, no head assignment yet (end of Step 1):**

```
queries[0, 1, :] = [c, d]    shape: (2,)    ← d_out=2, using letters c and d
                               ↑  ↑            from the full shape story above
                               c  d
                         position 0  position 1
```

**After `.view(b, num_tokens, num_heads, head_dim)` — split into heads (end of Step 2):**

```
queries[0, 1, :, :] = [        shape: (2, 1)
                         [c],  ← Head 1's query for "journey"
                         [d]   ← Head 2's query for "journey"
                       ]
```

**After `.transpose(1, 2)` — indexed by head first (end of Step 3):**

```
indexing changes from queries[batch, token, head, hd]
                  to   queries[batch, head, token, hd]

queries[0, 0, 1, 0] = c    ← Batch 0, Head 1, Token 1 "journey"
queries[0, 1, 1, 0] = d    ← Batch 0, Head 2, Token 1 "journey"

"journey" is no longer addressable as one unit — its two values now live in
separate head slices, processed completely independently from here.
```

**After attention scores, mask, softmax (Steps 4 and 5):**

```
Head 1 computes its own 6×6 score matrix using c against all keys a', c', e'...
Head 2 computes its own 6×6 score matrix using d against all keys b', d', f'...

Each produces its own row of attention weights for "journey":
  attn_weights[0, 0, 1, :] = [0,  w_cc, 0, 0, 0, 0]   ← Head 1's weights for "journey"
                                ↑   ↑
                              masked  only sees tokens 0 and 1 (causal mask)
  attn_weights[0, 1, 1, :] = [0,  w_dd, 0, 0, 0, 0]   ← Head 2's weights for "journey"

Different score values → different weight distributions → different blending.
```

**After `attn_weights @ values` — each head produces its own context (end of Step 6):**

```
context_vec[0, 0, 1, 0] = cc    ← Batch 0, Head 1's context for "journey"
                                    = w_ca*a'' + w_cc*c''
context_vec[0, 1, 1, 0] = cd    ← Batch 0, Head 2's context for "journey"
                                    = w_db*b'' + w_dd*d''

Two completely independent blended results, still in separate head slots.
```

**After `.transpose(1, 2)` — token owns both heads again (end of Step 7):**

```
context_vec[0, 1, :, :] = [        shape: (2, 1)
                              [cc], ← Head 1's context for "journey"
                              [cd]  ← Head 2's context for "journey"
                            ]
```

**After `.contiguous().view(b, num_tokens, d_out)` — heads merged (end of Step 8):**

```
context_vec[0, 1, :] = [cc, cd]    shape: (2,)    ← naively stitched, not yet mixed
                          ↑   ↑
                        Head1 Head2
```

**After `out_proj` — cross-head mixed (end of Step 9):**

```
context_vec[0, 1, :] = [new_c0, new_c1]    shape: (2,)    ← final output

where:
  new_c0 = W[0,0]*cc + W[0,1]*cd    ← both heads contribute to output dim 0
  new_c1 = W[1,0]*cc + W[1,1]*cd    ← both heads contribute to output dim 1
```

"journey" entered as a static 3-dim embedding `[0.55, 0.87, 0.66]` and leaves
as a 2-dim context-aware representation `[new_c0, new_c1]` that has been
informed by two independent attention perspectives — each looking at the whole
sequence through its own learned query/key/value projections.

---

### Why `keys.transpose(2, 3)` and not `keys.transpose(1, 2)`?

After Step 3, `keys` has shape `(batch, num_heads, num_tokens, head_dim)` — 4
dimensions. We want the matmul to happen over the last two dimensions
`(num_tokens, head_dim)`. To do `Q @ K^T` in that space we need to transpose the
last two dims of K, turning `(num_tokens, head_dim)` into `(head_dim, num_tokens)`.
That is `transpose(2, 3)`. Using `transpose(1, 2)` would swap `num_heads` and
`num_tokens` instead — completely wrong shape.

---

### The class

```python
class MultiHeadAttention(nn.Module):

    def __init__(self, d_in, d_out, context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        assert d_out % num_heads == 0, "d_out must be divisible by num_heads"

        self.d_out = d_out
        self.num_heads = num_heads
        self.head_dim = d_out // num_heads  # width each head works in

        # One big projection for all heads combined — NOT one per head
        # The split into heads happens later via .view()
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key   = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)

        # Final linear layer to mix information across heads after concatenation
        self.out_proj = nn.Linear(d_out, d_out)

        self.dropout = nn.Dropout(dropout)

        # Causal mask — same as CausalAttention, registered as a buffer
        # so it moves with the model to GPU but is not a trainable parameter
        self.register_buffer(
            'mask',
            torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape

        # Step 1 — Project into Q, K, V (one big projection each)
        # shape: (b, num_tokens, d_out) — not yet split into heads
        queries = self.W_query(x)
        keys    = self.W_key(x)
        values  = self.W_value(x)

        # Step 2 — Split d_out into (num_heads, head_dim)
        # .view() is free — no data copied, just strides change
        # shape: (b, num_tokens, d_out) → (b, num_tokens, num_heads, head_dim)
        queries = queries.view(b, num_tokens, self.num_heads, self.head_dim)
        keys    = keys.view(b, num_tokens, self.num_heads, self.head_dim)
        values  = values.view(b, num_tokens, self.num_heads, self.head_dim)

        # Step 3 — Bring num_heads next to batch so matmul treats (batch, heads)
        # as the outer batch dims and runs each head independently
        # shape: (b, num_tokens, num_heads, head_dim) → (b, num_heads, num_tokens, head_dim)
        queries = queries.transpose(1, 2)
        keys    = keys.transpose(1, 2)
        values  = values.transpose(1, 2)

        # Step 4 — Attention scores: Q @ K^T over the last two dims
        # transpose(2, 3) flips (num_tokens, head_dim) → (head_dim, num_tokens) for K
        # shape: (b, num_heads, num_tokens, head_dim) @ (b, num_heads, head_dim, num_tokens)
        #      → (b, num_heads, num_tokens, num_tokens)
        attn_scores = queries @ keys.transpose(2, 3)

        # Step 5 — Apply causal mask, scale, softmax, dropout
        # Slice mask to num_tokens in case input is shorter than context_length
        mask_bool = self.mask.bool()[:num_tokens, :num_tokens]
        attn_scores.masked_fill_(mask_bool, -torch.inf)
        # Divide by sqrt(head_dim) NOT sqrt(d_out) — the dot product sums over
        # head_dim dimensions, so that is what controls variance (see Section 4)
        attn_weights = torch.softmax(attn_scores / self.head_dim**0.5, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # Step 6 — Weighted sum of values per head
        # shape: (b, num_heads, num_tokens, num_tokens) @ (b, num_heads, num_tokens, head_dim)
        #      → (b, num_heads, num_tokens, head_dim)
        context_vec = attn_weights @ values

        # Step 7 — Transpose back: tokens back to position 1
        # shape: (b, num_heads, num_tokens, head_dim) → (b, num_tokens, num_heads, head_dim)
        context_vec = context_vec.transpose(1, 2)

        # Step 8 — Merge heads back into d_out
        # .contiguous() needed because transpose only changes strides not memory layout
        # .view() then merges (num_heads, head_dim) → d_out
        # shape: (b, num_tokens, num_heads, head_dim) → (b, num_tokens, d_out)
        context_vec = context_vec.contiguous().view(b, num_tokens, self.d_out)

        # Step 9 — Mix across heads with the output projection
        # shape: (b, num_tokens, d_out) → (b, num_tokens, d_out) — same shape, cross-head mixed
        context_vec = self.out_proj(context_vec)

        return context_vec
```

### Running it

```python
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

---

### Wrapper vs Efficient — Side by Side

```
MultiHeadAttentionWrapper(d_in=3, d_out=2, num_heads=2)
  Each head projects: 3 → 2    (d_in → d_out)
  Output per head:    (batch, 6, 2)
  After concat:       (batch, 6, 4)   ← d_out * num_heads
  No out_proj

MultiHeadAttention(d_in=3, d_out=2, num_heads=2)
  One projection:     3 → 2    (d_in → d_out)
  head_dim:           2 // 2 = 1
  Each head works in: 1-dimensional space  ← only because d_out=2, num_heads=2
  Output:             (batch, 6, 2)        — in GPT-2 small this would be
  Has out_proj                               d_out=768, num_heads=12, head_dim=64
```

In real GPT usage you set `d_out` to whatever total output width you want (e.g.
768), and `MultiHeadAttention` handles the per-head splitting internally via
`head_dim = d_out // num_heads`. With the Wrapper, `d_out` per head × `num_heads`
gives the total, so you would set `d_out=384` to end up with 768 total.

This is why their numbers differ — different shapes, different weights, and an
extra `out_proj` in `MultiHeadAttention`.

---

### Gotcha — `.view()` vs `.reshape()`

`.view()` only works on contiguous tensors. After a `.transpose()`, the tensor is
non-contiguous (the memory layout no longer matches the logical shape), so
`.view()` will raise an error. Two ways to handle this:

- `.contiguous().view(...)` — make a proper memory copy first, then reshape. This
  is what the book uses and what you will see in most production code.
- `.reshape(...)` — does `.contiguous().view()` internally when needed, but may
  silently make a copy even when you don't expect it. Using `.contiguous().view()`
  explicitly is clearer about what is happening.

---

## 11 — Putting It All Together & Where This Leads

### The Full Pipeline in One Diagram

Every step from raw input to final context vectors, with shapes tracked at each
transition — using the same settings from this chapter: `b=2, n=6, d_in=3,
d_out=2, num_heads=2, head_dim=1`:

```
inputs (b, n, d_in)
  shape: (2, 6, 3)
       │
       ▼  Step 1 — W_query, W_key, W_value (nn.Linear, no bias)
       │           one big projection each, NOT one per head
       │
  Q, K, V  each (b, n, d_out)
  shape: (2, 6, 2)
       │
       ▼  Step 2 — .view(b, n, num_heads, head_dim)
       │           split d_out into (num_heads, head_dim)
       │           free reshape — no data copied
       │
  shape: (2, 6, 2, 1)
       │
       ▼  Step 3 — .transpose(1, 2)
       │           bring num_heads next to batch
       │           so matmul treats (batch, heads) as outer dims
       │
  shape: (2, 2, 6, 1)   ← (batch, num_heads, tokens, head_dim)
       │
       ▼  Step 4 — Q @ K.transpose(2, 3)
       │           4 independent (6,1)@(1,6) matmuls in one GPU call
       │
  attn_scores (b, num_heads, n, n)
  shape: (2, 2, 6, 6)
       │
       ▼  Step 5 — causal mask: upper triangle → -inf
       │           scale by 1/sqrt(head_dim)
       │           softmax(dim=-1) → rows sum to 1
       │           dropout
       │
  attn_weights (b, num_heads, n, n)
  shape: (2, 2, 6, 6)
       │
       ▼  Step 6 — attn_weights @ V
       │           4 independent (6,6)@(6,1) matmuls in one GPU call
       │
  context (b, num_heads, n, head_dim)
  shape: (2, 2, 6, 1)
       │
       ▼  Step 7 — .transpose(1, 2)
       │           bring tokens back to position 1
       │
  shape: (2, 6, 2, 1)
       │
       ▼  Step 8 — .contiguous().view(b, n, d_out)
       │           merge (num_heads, head_dim) back into d_out
       │           .contiguous() needed because transpose broke memory layout
       │
  shape: (2, 6, 2)   ← heads naively stitched, not yet mixed
       │
       ▼  Step 9 — out_proj (nn.Linear d_out → d_out)
       │           every output dim receives contributions from ALL heads
       │           model learns which head combinations are most useful
       │
  context_vecs (b, n, d_out)
  shape: (2, 6, 2)   ← same shape as Step 1 output — blocks can be stacked
```

---

### Why the Output Shape Matches the Input Shape

Notice that `inputs` came in as `(b, n, d_in)` and `context_vecs` goes out as
`(b, n, d_out)`. In GPT, `d_in` and `d_out` are always set equal to `emb_dim`
— so the shape going out of `MultiHeadAttention` is identical to the shape
going in. This is not accidental — it is what makes stacking transformer blocks
possible. Block 2 receives exactly the same shape that Block 1 received, so
you can chain as many blocks as you want without any reshaping between them.

```
Block 1:  (b, n, emb_dim) → MultiHeadAttention → (b, n, emb_dim)
                                    ↓
Block 2:  (b, n, emb_dim) → MultiHeadAttention → (b, n, emb_dim)
                                    ↓
Block 3:  (b, n, emb_dim) → MultiHeadAttention → (b, n, emb_dim)
                                    ↓
  ... × 12 for GPT-2 small, × 96 for GPT-4
```

---

### What Chapter 4 Adds

`MultiHeadAttention` on its own is one piece of a transformer block. Chapter 4
wraps it together with three more components to form a complete block:

```
input (b, n, emb_dim)
       │
       ▼  LayerNorm        — normalizes each token's vector to mean=0, std=1
       │                     stabilizes training, especially for deep stacks
       ▼  MultiHeadAttention  — what we built in this chapter
       │
       ▼  residual connection — adds the original input back to the output
       │                        (input + attention_output)
       │                        lets gradients flow directly to early layers
       ▼  LayerNorm
       │
       ▼  FeedForward       — two linear layers with GELU activation between them
       │                      expands to 4×emb_dim then back down
       │                      adds per-token non-linear computation
       ▼  residual connection
       │
output (b, n, emb_dim)   ← same shape, this block can be stacked
```

The hyperparameters we used throughout this chapter map directly to the GPT
config dictionary in Chapter 4:

```
this chapter          Chapter 4 GPT config
────────────────────────────────────────────
d_in / d_out      →   emb_dim        (768 for GPT-2 small)
context_length    →   context_length (1024 for GPT-2 small)
num_heads         →   n_heads        (12 for GPT-2 small)
head_dim          →   emb_dim // n_heads  (64 for GPT-2 small)
dropout           →   drop_rate      (0.1 for GPT-2 small)
```

So `MultiHeadAttention` is not a standalone module — it is the core of every
transformer block, and every transformer block is one floor of the full GPT
tower. What we built in this chapter is exactly what gets repeated 12, 24, or
96 times in real models.

---
