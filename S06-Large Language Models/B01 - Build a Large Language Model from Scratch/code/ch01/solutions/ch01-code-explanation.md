# Chapter 1 Code Explanation — PyTorch Fundamentals for LLM Development

This document walks through `01-pytorch_fundamentals_for_llms.ipynb` — a hands-on PyTorch primer that builds the foundation for every other chapter in this book. Unlike chapters 2–7 (which are tightly tied to Raschka's *Build a Large Language Model From Scratch*), this notebook is a custom-built warmup covering tensors, autograd, neural-network modules, training loops, and GPU usage.

The section numbers below (0 → 28) match the linear flow of the notebook, with each section pointing at the cells it covers.

---

## Table of Contents

- [0 — Notebook Setup and Environment Check](#0--notebook-setup-and-environment-check)
- [1 — Tensors: The Universal Data Structure](#1--tensors-the-universal-data-structure)
- [2 — Tensor Data Types (dtype)](#2--tensor-data-types-dtype)
- [3 — Common Tensor Creation Functions](#3--common-tensor-creation-functions)
- [4 — Random Seeds for Reproducibility](#4--random-seeds-for-reproducibility)
- [5 — NumPy ↔ PyTorch Interoperability](#5--numpy--pytorch-interoperability)
- [6 — Element-Wise Operations](#6--element-wise-operations)
- [7 — Shape Manipulation: reshape and view](#7--shape-manipulation-reshape-and-view)
- [8 — Transpose and Permute](#8--transpose-and-permute)
- [9 — Indexing and Slicing](#9--indexing-and-slicing)
- [10 — Matrix Multiplication](#10--matrix-multiplication)
- [11 — Aggregation Operations](#11--aggregation-operations)
- [12 — Broadcasting](#12--broadcasting)
- [13 — Autograd: requires_grad and the Computation Graph](#13--autograd-requires_grad-and-the-computation-graph)
- [14 — Computing Gradients With .backward()](#14--computing-gradients-with-backward)
- [15 — Gradient Accumulation and Zeroing](#15--gradient-accumulation-and-zeroing)
- [16 — Disabling Gradient Tracking](#16--disabling-gradient-tracking)
- [17 — Practice: Linear Regression From Scratch](#17--practice-linear-regression-from-scratch)
- [18 — Building Your First Neural Network: nn.Module](#18--building-your-first-neural-network-nnmodule)
- [19 — Common Layer Types](#19--common-layer-types)
- [20 — Activation Functions: ReLU, GELU, SiLU, Sigmoid](#20--activation-functions-relu-gelu-silu-sigmoid)
- [21 — nn.Sequential for Quick Models](#21--nnsequential-for-quick-models)
- [22 — Model Inspection: Counting Parameters](#22--model-inspection-counting-parameters)
- [23 — Dataset and DataLoader](#23--dataset-and-dataloader)
- [24 — Loss Functions for Each Task Type](#24--loss-functions-for-each-task-type)
- [25 — Optimizers: SGD, Adam, AdamW](#25--optimizers-sgd-adam-adamw)
- [26 — Complete Training Loop](#26--complete-training-loop)
- [27 — Saving and Loading Models](#27--saving-and-loading-models)
- [28 — GPU Usage and Memory Management](#28--gpu-usage-and-memory-management)
- [29 — Exercises](#29--exercises)

---

## 0 — Notebook Setup and Environment Check

```python
import sys
print(sys.executable)

import torch
import numpy as np
import matplotlib.pyplot as plt

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
```

These first two cells confirm three things before you write any real code:

1. **Which Python interpreter is running** — `sys.executable` shows the full path. This catches the classic "I installed PyTorch in conda env A but Jupyter is running env B" problem before it wastes hours.
2. **PyTorch version** — recent code (e.g. `weights_only=True` on `torch.load`) requires PyTorch ≥ 2.6. Older versions will silently behave differently.
3. **GPU availability** — `torch.cuda.is_available()` returns `True` only if both your hardware *and* your PyTorch build have CUDA support. If you installed PyTorch via `pip install torch` without the CUDA wheel, this will be `False` even on a machine with an NVIDIA GPU.

### Why we also import NumPy and matplotlib

* **NumPy** — PyTorch tensors and NumPy arrays interoperate cleanly via `torch.from_numpy` and `.numpy()`. Many real datasets land as NumPy arrays first.
* **matplotlib** — for the activation-function plots in section 20.

---

## 1 — Tensors: The Universal Data Structure

```python
scalar = torch.tensor(42)          # 0D
vector = torch.tensor([1, 2, 3])   # 1D
matrix = torch.tensor([[1, 2, 3],
                       [4, 5, 6]]) # 2D
tensor_3d = torch.tensor([[[1, 2], [3, 4]],
                          [[5, 6], [7, 8]]])  # 3D
```

A **tensor** is a multi-dimensional array. Everything in deep learning — inputs, weights, activations, gradients — lives in tensors.

### The ladder of dimensions

| Dim | Name | Shape example | Used for |
|-----|------|---------------|----------|
| 0 | Scalar | `()` | Loss values, single counts |
| 1 | Vector | `(d,)` | A single token embedding, a single row |
| 2 | Matrix | `(rows, cols)` | A weight matrix, a batch of vectors |
| 3 | 3D tensor | `(batch, seq_len, features)` | A batch of token embeddings — **the canonical LLM input shape** |
| 4 | 4D tensor | `(batch, channels, height, width)` | Image batches |
| 5+ | n-D | `(batch, num_heads, seq_q, seq_k)` | Attention scores in multi-head attention |

### The three attributes you'll check 100× a day

```python
tensor.shape    # tuple of dimensions, e.g. torch.Size([2, 3])
tensor.ndim     # number of dimensions, e.g. 2
tensor.dtype    # data type, e.g. torch.float32
```

Whenever a model crashes, the first reflex is to print `.shape` of the offending tensor. 90% of bugs are shape mismatches.

### Why "dimension" can mean two things

This is a common source of confusion:

* **Tensor dimension** = the *number of axes* (1 for a vector, 2 for a matrix). Sometimes called "rank."
* **Embedding dimension** = the *size* of a specific axis, usually the last one. When we say "embedding dim 768" we mean each vector has 768 components, *not* that the tensor has 768 axes.

The book uses both meanings depending on context — read carefully.

---

## 2 — Tensor Data Types (dtype)

```python
int_tensor   = torch.tensor([1, 2, 3])      # default: int64
float_tensor = torch.tensor([1.0, 2.0])     # default: float32
bool_tensor  = torch.tensor([True, False])  # bool

# Explicit specification
f64_tensor = torch.tensor([1.0, 2.0], dtype=torch.float64)
i32_tensor = torch.tensor([1, 2, 3],   dtype=torch.int32)

# Conversion
converted = int_tensor.to(torch.float32)
```

### Why dtype matters so much in LLMs

Every parameter and every activation occupies a fixed number of bytes. For a 1.1B-parameter TinyLlama:

| dtype | Bytes / param | Total VRAM |
|-------|---------------|------------|
| `float64` | 8 | 8.8 GB |
| `float32` | 4 | 4.4 GB |
| `float16` | 2 | 2.2 GB |
| `bfloat16` | 2 | 2.2 GB |
| `int8` | 1 | 1.1 GB |
| 4-bit (NF4) | 0.5 | 0.55 GB |

A single dtype choice cuts VRAM by up to **16×**. That is why every modern training pipeline runs in **bfloat16**, and 4-bit quantization (QLoRA) is the dominant fine-tuning approach.

### Common dtype gotchas

* **Mixing dtypes is an error.** `torch.tensor([1.0]) @ torch.tensor([1, 2])` will fail because one is float32 and the other is int64.
* **Integer tensors don't have gradients.** `requires_grad=True` only works on floating-point dtypes. If you try to track gradients on an int tensor PyTorch errors out.
* **`bool` is the right type for masks** (e.g. causal attention masks). Multiplying a bool by a float silently casts the bool to 0.0/1.0.

---

## 3 — Common Tensor Creation Functions

```python
torch.zeros(3, 4)                     # all zeros
torch.ones(2, 3)                      # all ones
torch.rand(2, 3)                      # uniform [0, 1)
torch.randn(2, 3)                     # normal N(0, 1)
torch.arange(0, 10, 2)                # 0, 2, 4, 6, 8 (like Python range)
torch.linspace(0, 1, 5)               # 5 evenly spaced points in [0, 1]
torch.eye(3)                          # 3x3 identity matrix
torch.zeros_like(some_tensor)         # same shape/device/dtype as input
```

### Which one for which scenario

| Function | When to reach for it |
|----------|----------------------|
| `zeros`, `ones` | Initialising buffers (e.g. position encoding scratch space, attention masks) |
| `rand` | Test data, dummy inputs for shape verification |
| `randn` | Weight initialisation (Gaussian init), random embeddings |
| `arange` | Position indices (e.g. `arange(seq_len)` for positional embedding lookup) |
| `linspace` | Plotting input ranges for activation function visualisation |
| `eye` | Identity matrices for testing attention (Q=K=I gives uniform attention) |
| `*_like` | Building output buffers that match an existing tensor's shape and dtype |

### `randn` vs `rand` — why GPT initialises weights with `randn`

Random uniform values from `rand` are confined to `[0, 1)` — they have non-zero mean and a small variance. Weights initialised this way have **bias built in from step 1**, which makes training slow.

Random *normal* values from `randn` come from $\mathcal{N}(0, 1)$ — symmetric around 0, with a known variance. Combined with **Xavier** or **Kaiming** scaling factors (PyTorch does this automatically inside `nn.Linear`), this gives the network a good starting point where activations stay roughly unit-variance through the layers.

---

## 4 — Random Seeds for Reproducibility

```python
# Without seed — different each time
torch.randn(3)
torch.randn(3)

# With seed — identical
torch.manual_seed(42)
torch.randn(3)
torch.manual_seed(42)
torch.randn(3)
```

### Why this matters more than people think

You will lose hours of your life to bugs that *seem* random until you realise they depended on initialisation order. Pin the seed at the top of every notebook:

```python
torch.manual_seed(42)
```

…and your output is byte-identical between runs. When the book's expected output is `tensor([0.3367, 0.1288, 0.2345])` and yours matches, you know your code is correct. When it doesn't match, you know your code is wrong — not that "training is stochastic."

### What `manual_seed` actually controls

* `torch.randn`, `torch.rand`, etc.
* `nn.Linear` weight initialisation
* `nn.Dropout` mask sampling

What it does **not** control by default:
* CUDA RNG (need `torch.cuda.manual_seed_all` separately)
* NumPy RNG (need `np.random.seed` separately)
* Python's `random` module
* `DataLoader` shuffling (uses its own RNG seeded from `torch.manual_seed`, but only at construction)

For full determinism you typically need all four seeded plus `torch.use_deterministic_algorithms(True)`. For most learning notebooks, just `torch.manual_seed(42)` is enough.

---

## 5 — NumPy ↔ PyTorch Interoperability

```python
import numpy as np
numpy_array = np.array([[1, 2], [3, 4]])

# Method 1: torch.from_numpy() — SHARES MEMORY
tensor_shared = torch.from_numpy(numpy_array)
numpy_array[0, 0] = 999
print(tensor_shared)   # Also shows 999 — they share the same buffer!

# Method 2: torch.tensor() — COPIES
numpy_array = np.array([[1, 2], [3, 4]])
tensor_copy = torch.tensor(numpy_array)
numpy_array[0, 0] = 999
print(tensor_copy)     # Still shows 1 — copy is independent
```

### The two-way street

```python
# Tensor → NumPy
arr = tensor.numpy()           # shares memory (CPU tensors only)

# NumPy → Tensor
t = torch.from_numpy(arr)      # shares memory
t = torch.tensor(arr)          # copies
```

### Why this matters in real LLM pipelines

* **Loading OpenAI's GPT-2 weights** (chapter 5 section 25) comes in as numpy arrays. We use `torch.tensor(arr)` to copy into PyTorch.
* **Saving generated text embeddings to disk** typically uses `tensor.cpu().numpy()` → `np.save(...)`.
* **Hugging Face datasets** return NumPy arrays which get converted to tensors inside `DataLoader`.

### Gotcha: GPU tensors can't go directly to NumPy

```python
gpu_tensor = torch.randn(3).cuda()
arr = gpu_tensor.numpy()        # RuntimeError!

arr = gpu_tensor.cpu().numpy()  # Works — move to CPU first
```

NumPy lives on CPU only. Any cross-conversion has to go via CPU.

---

## 6 — Element-Wise Operations

```python
a = torch.tensor([1, 2, 3])
b = torch.tensor([4, 5, 6])

a + b        # tensor([5, 7, 9])
a - b
a * b        # element-wise multiply (NOT matrix multiply)
a / b
a ** 2

# Equivalent function forms
torch.add(a, b)
torch.mul(a, b)
torch.pow(a, 2)
```

### Element-wise is the default for `*`, NOT matrix multiplication

This is the single most common source of subtle bugs for newcomers.

```python
A = torch.tensor([[1, 2], [3, 4]])
B = torch.tensor([[5, 6], [7, 8]])

A * B          # element-wise: [[5, 12], [21, 32]]
A @ B          # matrix multiply: [[19, 22], [43, 50]]
torch.matmul(A, B)   # same as @
```

The `@` operator (PEP 465) is the standard matmul. `*` is always element-wise.

### Why this distinction matters

In transformer math:

* **Element-wise multiplications** appear when you apply a mask (`scores * mask`) or scale (`q * 1/sqrt(d_k)`).
* **Matrix multiplications** are the heavy compute — Q × K^T, attention × V, the FFN linear layers, the output projection. Every dollar your GPU bills is being spent on these.

### Broadcasting works here too

```python
a = torch.tensor([1, 2, 3])
a + 10              # tensor([11, 12, 13]) — scalar broadcast
a + torch.tensor([10, 20, 30])
```

The scalar `10` is broadcast to match the shape of `a`. We'll cover broadcasting rules properly in section 12.

---

## 7 — Shape Manipulation: reshape and view

```python
x = torch.arange(12)                # shape (12,)
x_2d = x.reshape(3, 4)              # shape (3, 4)
x_3d = x.reshape(2, 2, 3)           # shape (2, 2, 3)
x_flat = x_2d.reshape(-1)           # shape (12,) — -1 means "infer"
```

### The `-1` shortcut

`-1` tells PyTorch to infer that dimension from the total size:

```python
x.reshape(2, -1)    # -1 becomes 6, giving shape (2, 6)
x.reshape(-1, 3)    # -1 becomes 4, giving shape (4, 3)
x.reshape(2, -1, 2) # -1 becomes 3, giving shape (2, 3, 2)
```

You can only have one `-1` per reshape.

### Direct Answer

"Inferring" a dimension simply means you are telling PyTorch: **"I know the total number of items, and I know *some* of the dimensions I want. You do the math to figure out the last one."**

#### Explanation of Method

When you reshape a tensor, the **total number of elements must always stay exactly the same**.

If you start with a 1D tensor of 12 items (`torch.arange(12)`), any new shape you create must also multiply out to exactly 12.

Instead of doing that division in your head every time, you can put a `-1` in exactly **one** spot in your `reshape()` command. PyTorch will look at the other dimensions you provided, multiply them together, and divide the total number of elements by that result to find the missing number.

Here is how the math breaks down for your examples:

* **`x.reshape(2, -1)`**
    * **Total elements:** 12
    * **Known dimensions:** 2
    * **PyTorch's math:** 12 ÷ 2 = 6
    * **Resulting shape:** `(2, 6)`


* **`x.reshape(-1, 3)`**
    * **Total elements:** 12
    * **Known dimensions:** 3
    * **PyTorch's math:** 12 ÷ 3 = 4
    * **Resulting shape:** `(4, 3)`


* **`x.reshape(2, -1, 2)`**
    * **Total elements:** 12
    * **Known dimensions:** 2 and 2 (which multiplies to 4)
    * **PyTorch's math:** 12 ÷ 4 = 3
    * **Resulting shape:** `(2, 3, 2)`



**Why can you only have one `-1`?**
If you tried to do `x.reshape(-1, -1)`, PyTorch wouldn't know what to do. For 12 elements, a shape of `(3, 4)` works, but so does `(2, 6)` or `(12, 1)`. Because there are multiple valid answers, PyTorch strictly limits you to a single `-1` per reshape.

Here is an interactive visualizer so you can see exactly how the grid reorganizes itself when you use the `-1` shortcut!

This trick is incredibly useful in real-world code, especially when you are processing batches of data where the batch size might change, but the features per item stay the same (e.g., `x.reshape(-1, 768)`).

### `reshape` vs `view` — the subtle difference

```python
tensor.view(2, 6)    # Only works if tensor is contiguous in memory
tensor.reshape(2, 6) # Always works — copies if necessary
```

After certain operations (especially `transpose` and `permute`) a tensor's memory is no longer contiguous. `view` will fail; `reshape` silently falls back to a copy.

**Rule of thumb:** use `reshape` unless you have a specific reason. The performance penalty is negligible for most workloads.

### Where you'll use this in LLM code

* Flattening logits for cross_entropy: `logits.flatten(0, 1)` to merge batch+seq dims for the loss.
* Splitting the embedding dim into heads in multi-head attention: `(B, T, d_out)` → `(B, T, num_heads, head_dim)` via reshape.
* Collapsing per-token features for pooling: `embedded.mean(dim=1)` on `(B, T, d)` gives `(B, d)`.

---

## 8 — Transpose and Permute

```python
matrix = torch.tensor([[1, 2, 3],
                       [4, 5, 6]])    # shape (2, 3)
matrix.T                              # shape (3, 2) — swap last two dims

# For higher-dim tensors, use permute
t = torch.randn(2, 3, 4)              # (batch, seq, features)
t.permute(0, 2, 1)                    # (batch, features, seq)
t.transpose(1, 2)                     # same effect — just swap two dims
```

### When to reach for each

| Operation | Use case |
|-----------|----------|
| `.T` | 2D matrices only. Quick and obvious. |
| `.transpose(d0, d1)` | Swap two specific dims of a higher-D tensor. |
| `.permute(*dims)` | Re-order dimensions arbitrarily (give the new ordering as args). |

### Permute in attention

The most common use in transformers is rearranging dims for multi-head attention:

```python
# After computing Q with shape (batch, seq_len, d_out)
# we want to split into heads: (batch, num_heads, seq_len, head_dim)

q = q.view(batch, seq_len, num_heads, head_dim)        # (B, T, H, D)
q = q.transpose(1, 2)                                    # (B, H, T, D)
```

This rearrangement is what allows the subsequent `q @ k.transpose(-2, -1)` matmul to run in parallel across all heads in a single batched call.

### Non-contiguous after permute

```python
t = torch.randn(2, 3, 4)
t_perm = t.permute(0, 2, 1)
t_perm.view(-1)        # Errors — memory is no longer contiguous
t_perm.reshape(-1)     # Works — does a silent copy
t_perm.contiguous().view(-1)   # Also works — explicit copy
```

Real code in chapter 3's `MultiHeadAttention` uses `.contiguous().view(...)` exactly because of this.

---

## 9 — Indexing and Slicing

```python
t = torch.arange(20).reshape(4, 5)

t[1, 2]              # single element — scalar
t[0]                 # row 0 — shape (5,)
t[:, 2]              # column 2 — shape (4,)
t[0:2, 1:4]          # sub-matrix — shape (2, 3)
t[::2]               # every other row — shape (2, 5)
```

PyTorch uses the same indexing conventions as NumPy.

### Negative indices count from the end

```python
t[-1]      # last row
t[-2:]     # last two rows
t[:, -1]   # last column
```

### Critical for LLM code: pulling the last token's logits

```python
logits = model(input_ids)           # shape (batch, seq_len, vocab_size)
last_token_logits = logits[:, -1, :]   # shape (batch, vocab_size)
```

This is exactly the slice in chapter 5's `generate_text_simple` and `generate` functions. At each generation step, you only care about the logits at the *final* position to pick the next token.

### Advanced ("fancy") indexing with lists

```python
t = torch.arange(20).reshape(4, 5)
t[[0, 2, 3]]          # rows 0, 2, 3 → shape (3, 5)
t[[0, 1], [2, 3]]     # elements (0, 2) and (1, 3) → shape (2,)
```

We use exactly this pattern in chapter 5 section 6 to pull the probability the model assigned to the *correct* next token at each position:

```python
target_probas = probas[batch_idx, [0, 1, 2], targets[batch_idx]]
```

---

## 10 — Matrix Multiplication

```python
A = torch.tensor([[1, 2], [3, 4], [5, 6]])   # (3, 2)
B = torch.tensor([[7, 8, 9], [10, 11, 12]])  # (2, 3)

C = A @ B          # (3, 3)
C = torch.matmul(A, B)   # same
```

### The shape rule

For `A @ B`:
* `A` has shape `(..., m, k)`
* `B` has shape `(..., k, n)`
* Result has shape `(..., m, n)`

The inner dimensions (`k`) must match; they get summed over.

### Batched matmul

```python
# Q has shape (batch, num_tokens, d_k)
# K has shape (batch, num_tokens, d_k)
attn_scores = Q @ K.transpose(-2, -1)
# K.transpose: (batch, d_k, num_tokens)
# Result: (batch, num_tokens, num_tokens)
```

PyTorch automatically broadcasts the leading dims. This is what makes "compute Q @ K^T for every sequence in a batch at once" a single line of code.

### Why matmul is the most expensive operation

The arithmetic cost of `(m, k) @ (k, n)` is `m × k × n` multiply-add operations. For a transformer FFN:

```
Linear(768, 3072) -- (batch, seq_len, 768) @ (768, 3072) → (batch, seq_len, 3072)
```

With `batch=32, seq_len=512, in=768, out=3072`: that's $32 \times 512 \times 768 \times 3072 \approx 38.6$ billion multiply-adds for **one layer**. Across 12 transformer layers, with 2 such linear layers each, plus 4 attention matmuls per layer — a single forward pass is hundreds of billions of operations.

This is why GPUs exist.

### Math intuition

#### Element-wise vs Matrix Multiplication — what's actually happening

#### Element-wise multiplication `*`

The rule is simple: **same position multiplies with same position**. That's it.

For this to work, both tensors must have the **exact same shape**.

Let's take A (2×3) and B (2×3):

```
A = [[1, 2, 3],       B = [[7, 8, 9],
     [4, 5, 6]]            [10, 11, 12]]
```

Result = A * B, same shape (2×3):

```
[[1×7,  2×8,  3×9 ],      [[7,  16, 27],
 [4×10, 5×11, 6×12]]   =   [40, 55, 72]]
```

Row 0, Col 0 → 1×7. Row 0, Col 1 → 2×8. And so on. No mixing across rows or columns.

**Math intuition:** There's no "combining" of information across features. Each position is independent. You're scaling one matrix by another, element by element.

---

#### Matrix multiplication `@` or `torch.matmul`

This is fundamentally different. Here **each output cell is a dot product** — it mixes an entire row from the left matrix with an entire column from the right matrix.

The rule for shapes: if A is (m×n), B must be **(n×p)** — the inner dimensions must match. Output shape is **(m×p)**.

Let's take A (2×3) and B (3×4):

```
A = [[1, 2, 3],        B = [[1, 2, 3, 4],
     [4, 5, 6]]             [5, 6, 7, 8],
                             [9, 10, 11, 12]]
```

Output shape = (2×4). Let's dry-run a few cells:

**Output[0,0]** = row 0 of A · col 0 of B = `1×1 + 2×5 + 3×9` = `1 + 10 + 27` = **38**

**Output[0,1]** = row 0 of A · col 1 of B = `1×2 + 2×6 + 3×10` = `2 + 12 + 30` = **44**

**Output[1,0]** = row 1 of A · col 0 of B = `4×1 + 5×5 + 6×9` = `4 + 25 + 54` = **83**

**Output[1,3]** = row 1 of A · col 3 of B = `4×4 + 5×8 + 6×12` = `16 + 40 + 72` = **128**

Full result:

```
[[38,  44,  50,  56 ],
 [83,  98,  113, 128]]
```

**Math intuition:** Every output cell is the result of one row "looking at" one column — combining information across the entire feature dimension. This is fundamentally about **mixing and projecting** information.

---

#### When do you use which?

**Element-wise `*`** — when the two tensors represent the same "thing" and you want to scale or gate one by the other. Position (i, j) in one maps directly to position (i, j) in the other.

Real examples:
- **Attention mask** — you multiply attention scores by a mask (0s and 1s) to zero out certain positions. The mask is the same shape; you're just suppressing specific cells.
- **Gating mechanisms** — in LSTMs, a forget gate (values between 0 and 1) is multiplied element-wise with the cell state to decide what to forget.
- **Dropout** — a binary mask of 0s and 1s, element-wise multiplied with activations to randomly zero them out.

**Matmul `@`** — when you want to **transform** or **project** data, or compute **similarity between all pairs** of two sets of vectors.

Real examples:
- **Linear layers** — `output = input @ W.T + b`. Your input (batch × features) is projected through a weight matrix (features × hidden). Each output neuron is a weighted combination of all input features.
- **Attention scores** — `scores = Q @ K.T`. Q is (seq_len × d_k), K.T is (d_k × seq_len). Every query position is compared against every key position — you get a (seq_len × seq_len) matrix of similarities.
- **Embedding lookup via matmul** — one-hot vector (1 × vocab_size) @ embedding matrix (vocab_size × d_model) gives you the embedding for that token.

---

#### The key mental check

Before you write `*` or `@`, ask yourself:

- "Am I scaling position (i,j) by some corresponding value?" → element-wise `*`
- "Am I combining/mixing across a feature dimension, or computing similarity between two sets of vectors?" → matmul `@`

The shape constraint itself often tells you which is right — if the two tensors are already the same shape and that makes semantic sense, element-wise. If one tensor needs to "go through" another to change its dimension, matmul.

---

#### What is matmul actually doing mathematically?

Think of each **row** in matrix A as a vector — a list of numbers representing something.

Think of each **column** in matrix B as another vector — representing something else.

The dot product of a row and a column is asking: **"how much do these two vectors align?"** You multiply corresponding elements and sum them all up. The result is a single number that captures the total relationship between the two vectors.

Matmul is just doing this for **every row of A against every column of B**, all at once.

---

#### Small dry run — (2×3) @ (3×2)

```
A = [[1, 0, 2],      B = [[3, 1],
     [0, 3, 1]]           [0, 2],
                           [1, 0]]
```

Output shape = (2×2). Four cells to compute:

**[0,0]** = row 0 of A · col 0 of B = `1×3 + 0×0 + 2×1` = `3 + 0 + 2` = **5**

**[0,1]** = row 0 of A · col 1 of B = `1×1 + 0×2 + 2×0` = `1 + 0 + 0` = **1**

**[1,0]** = row 1 of A · col 0 of B = `0×3 + 3×0 + 1×1` = `0 + 0 + 1` = **1**

**[1,1]** = row 1 of A · col 1 of B = `0×1 + 3×2 + 1×0` = `0 + 6 + 0` = **6**

```
Result = [[5, 1],
          [1, 6]]
```

Notice: A had 3 features, B had 3 rows — those 3s "cancel out" and what remains is the (2×2) output. The inner dimension always disappears.

---

#### Now the AI intuition — a single linear layer

This is the most fundamental building block in every neural network, including transformers.

Say you have **2 tokens**, each represented by a **3-dimensional embedding**:

```
X = [[0.5, 1.0, 0.2],    ← token 1 embedding
     [1.5, 0.1, 0.8]]    ← token 2 embedding

shape: (2, 3)
```

And you have a **weight matrix** W that projects from 3 dimensions down to 2:

```
W = [[0.4, 0.1],
     [0.9, 0.3],
     [0.2, 0.7]]

shape: (3, 2)
```

Now you do `output = X @ W`:

```
(2,3) @ (3,2) = (2,2)
```

**Output[0,0]** = `0.5×0.4 + 1.0×0.9 + 0.2×0.2` = `0.20 + 0.90 + 0.04` = **1.14**

**Output[0,1]** = `0.5×0.1 + 1.0×0.3 + 0.2×0.7` = `0.05 + 0.30 + 0.14` = **0.49**

**Output[1,0]** = `1.5×0.4 + 0.1×0.9 + 0.8×0.2` = `0.60 + 0.09 + 0.16` = **0.85**

**Output[1,1]** = `1.5×0.1 + 0.1×0.3 + 0.8×0.7` = `0.15 + 0.03 + 0.56` = **0.74**

```
Output = [[1.14, 0.49],    ← token 1, now in 2D space
          [0.85, 0.74]]    ← token 2, now in 2D space
```

---

#### What just happened mathematically?

Each row of W is a **direction** in the original 3D space. When you compute the dot product of a token with that column, you're asking **"how much does this token point in that direction?"**

Column 0 of W = `[0.4, 0.9, 0.2]` — think of this as a direction that picks up strongly on feature 2 (weight 0.9).

Token 1 = `[0.5, 1.0, 0.2]` — it has a strong feature 2 component, so it scores high (1.14) on that direction.

Token 2 = `[1.5, 0.1, 0.8]` — weaker on feature 2, so it scores lower (0.85) on that direction.

**Matmul is projection.** You're projecting your data from one vector space into another. The weight matrix W defines the new space. Each column of W is a new axis, and the dot product tells you the coordinate of the input along that axis.

This is exactly what `nn.Linear` does internally — it's just `X @ W.T + bias`. The entire expressive power of a neural network comes from learning the right W matrices through backpropagation, so that after projection, the data is arranged in a way that makes the task easy to solve.

---

#### Why this matters for attention specifically

In self-attention, you have three such projections:

```
Q = X @ W_q     # what am I looking for?
K = X @ W_k     # what do I contain?
V = X @ W_v     # what will I pass forward?
```

Then `scores = Q @ K.T` — this is matmul again, computing the dot product between every query and every key. That score is literally "how much should token i attend to token j?" — which is exactly what a dot product measures: alignment between two vectors.

So matmul shows up twice in attention: once to project inputs into Q/K/V spaces, and once to compute similarity between all pairs. Both uses are the same underlying idea — dot product as a measure of alignment or projection.

## 11 — Aggregation Operations

```python
t = torch.tensor([[1.0, 2.0, 3.0],
                  [4.0, 5.0, 6.0]])

t.sum()              # 21.0  -- scalar (sum of everything)
t.sum(dim=0)         # tensor([5, 7, 9])    -- sum down rows
t.sum(dim=1)         # tensor([6, 15])      -- sum across columns
t.sum(dim=1, keepdim=True)   # shape (2, 1) -- preserves dim
```

### What `dim=N` actually means

The dimension you specify is the one that gets **reduced** (collapsed):

* `dim=0` on a `(2, 3)` tensor → result has shape `(3,)`. The "row" dim disappeared.
* `dim=1` on a `(2, 3)` tensor → result has shape `(2,)`. The "column" dim disappeared.
* `dim=-1` always means "the last dim".

### Other reductions

| Op | What it does |
|----|--------------|
| `.sum(dim)` | Sum along dim |
| `.mean(dim)` | Average along dim |
| `.max(dim)` | Returns `(values, indices)` tuple |
| `.argmax(dim)` | Just the indices of the max |
| `.std(dim)`, `.var(dim)` | Standard deviation / variance |
| `.norm(dim)` | L2 norm |

### Why `keepdim=True` is so often what you want

```python
mean = t.mean(dim=-1, keepdim=True)   # shape (2, 1), not (2,)
centered = t - mean                    # broadcasts properly to (2, 3)
```

Without `keepdim`, you'd get shape `(2,)` for the mean, and `t - mean` would broadcast wrong. `keepdim` keeps the reduced dim as size 1, which is exactly what's needed for the subtraction.

LayerNorm in chapter 4 section 8 uses this pattern.

### Argmax — picking the most likely token

```python
probas = torch.softmax(logits, dim=-1)
next_token = probas.argmax(dim=-1)
```

This is the core of greedy decoding (chapter 5 section 18). Argmax gives you the *index* of the highest-probability vocabulary entry.

---

## 12 — Broadcasting

Broadcasting is PyTorch's automatic shape-matching for element-wise operations. Two tensors are *broadcastable* if, when comparing their shapes right-to-left:

1. Either dimension equals 1, **or**
2. The dimensions are equal, **or**
3. One tensor has fewer dimensions (treat missing dims as size 1)

The "missing" dimensions are stretched to match.

### Example: scalar + tensor

```python
t = torch.tensor([[1, 2, 3], [4, 5, 6]])     # (2, 3)
t + 10                                         # 10 broadcasts to (2, 3)
```

### Example: vector + matrix

```python
matrix = torch.tensor([[1, 2, 3], [4, 5, 6]])   # (2, 3)
vector = torch.tensor([10, 20, 30])              # (3,)
matrix + vector
# Aligns vector to (1, 3), broadcasts to (2, 3)
# Result: [[11, 22, 33], [14, 25, 36]]
```

### Example: column vector + matrix

```python
col = torch.tensor([[100], [200]])               # (2, 1)
matrix + col
# col broadcasts across columns
# Result: [[101, 102, 103], [204, 205, 206]]
```

### Where broadcasting saves your life in LLM code

* **LayerNorm**: `(x - mean) / sqrt(var)` where `x` is `(B, T, D)` and `mean`/`var` are `(B, T, 1)`.
* **Causal mask**: a `(T, T)` mask added to `(B, num_heads, T, T)` attention scores — broadcasts across batch and heads.
* **Positional embedding add**: `pos_emb` of shape `(T, D)` added to `tok_emb` of shape `(B, T, D)`.
* **Loss masking**: multiplying `(B, T)` losses by a `(B, T)` mask of 0s and 1s for padding tokens.

### Common broadcasting failure

```python
a = torch.randn(3, 4)
b = torch.randn(4, 3)
a + b   # RuntimeError: incompatible shapes
```

Right-to-left comparison: `(3, 4)` vs `(4, 3)`. Last dims: 4 vs 3 — neither is 1, neither matches. Broadcast fails.

If you actually wanted to add them after a transpose: `a + b.T`.

---

## 13 — Autograd: requires_grad and the Computation Graph

```python
x = torch.tensor([2.0], requires_grad=True)
w = torch.tensor([3.0], requires_grad=True)
b = torch.tensor([1.0], requires_grad=True)

# Forward pass
y = w * x + b
print(y.requires_grad)    # True — propagates from inputs
print(y.grad_fn)          # <AddBackward0 ...>
```

### What `requires_grad=True` actually does

It tells PyTorch's **autograd engine**: "track every operation involving this tensor so I can compute gradients later." Each time you use a `requires_grad=True` tensor in an op, PyTorch:

1. Records the operation in a hidden directed acyclic graph (DAG).
2. Stores enough information to compute the gradient of the output with respect to that tensor when `.backward()` is called.

### The computation graph

A graph like this is built behind the scenes:

```
x ── \
       ├── (multiply) ── w*x ── \
w ── /                            ├── (add) ── y
                          b ── /
```

Each node has a `grad_fn` pointing to the function that created it (`MulBackward0`, `AddBackward0`, etc.). The leaves of the graph are the original parameters; the root is the loss.

### Why only floating-point tensors can have `requires_grad`

Gradients are derivatives, which need continuous (differentiable) values. Integer tensors don't have a well-defined derivative; calling `.requires_grad_(True)` on an int tensor raises an error.

### "Leaf" vs "non-leaf" tensors

* **Leaf tensor**: directly created by you with `requires_grad=True` (the original weights, inputs).
* **Non-leaf tensor**: produced by an operation (e.g. `y = w * x + b`). Its `requires_grad` is automatically True if any input was.

You only access `.grad` on **leaf** tensors. Non-leaves don't store gradients by default (they'd waste memory).

---

## 14 — Computing Gradients With .backward()

```python
x = torch.tensor([2.0], requires_grad=True)
w = torch.tensor([3.0], requires_grad=True)
b = torch.tensor([1.0], requires_grad=True)

y = w * x + b      # y = 3*2 + 1 = 7
loss = y ** 2      # loss = 49

loss.backward()    # populate .grad on every leaf tensor

print(x.grad)      # 28  -- ∂loss/∂x = 2y * w = 2*7*3
print(w.grad)      # 28  -- ∂loss/∂w = 2y * x = 2*7*2
print(b.grad)      # 14  -- ∂loss/∂b = 2y * 1 = 2*7
```

### The chain rule in action

`loss.backward()` walks the computation graph from the loss back to every leaf, multiplying local gradients along the way. For our example:

$$\frac{\partial \text{loss}}{\partial w} = \frac{\partial \text{loss}}{\partial y} \cdot \frac{\partial y}{\partial w} = 2y \cdot x = 2 \cdot 7 \cdot 2 = 28$$

Each tensor's `.grad` is populated *in place* — no return value.

### Important rules

* `.backward()` only works on scalar outputs. To call it on a non-scalar `y`, you must pass `gradient=...` explicitly (almost never needed in practice — call `.backward()` on the *loss*, which is always scalar).
* The computation graph is **freed after one backward pass** by default. To call `.backward()` multiple times on the same graph, pass `retain_graph=True`.
* Gradients **accumulate** in `.grad` rather than overwriting. This is what makes `optimizer.zero_grad()` necessary at the start of each batch (next section).

### The thing autograd is really doing

PyTorch's autograd is **reverse-mode automatic differentiation**. For each elementary op (multiply, add, exp, ...) PyTorch has a hand-coded backward formula. The chain rule says: to compute the gradient of a composition, multiply the gradients of each step. `.backward()` traverses the graph and applies these formulas mechanically.

The beautiful property: you never have to derive backward formulas yourself. You write the forward pass; PyTorch handles the rest.

### Extra Explanation

It sounds like a total contradiction: *"How can PyTorch remember my gradients if it just deleted the computation graph?"*

The secret is realizing that **the computation graph and the `.grad` attributes are two completely separate things.** To understand how they work together, think of the computation graph as a **delivery route (a map)** and the `.grad` attribute as a **bucket** at the end of the route.

Here is exactly how they differ and interact:

#### 1. The Computation Graph (The Delivery Route)

When you do a forward pass (e.g., `y = w * x + b`), PyTorch builds a hidden web of operations. This graph's only job is to provide a path for the calculus chain rule to travel backwards.

When you call `loss.backward()`, PyTorch walks backward down this route, calculating the slopes (gradients) as it goes. Once it finishes delivering those calculations to the final parameters, **PyTorch shreds the map to save memory**. The graph is "freed." If you try to call `.backward()` a second time without doing a new forward pass first, PyTorch will throw an error because the route no longer exists.

#### 2. The `.grad` Attribute (The Bucket)

Your trainable parameters (like `w` and `b`) are permanent fixtures in your model. Each of these parameters has a special little bucket attached to it called `.grad`.

When the backward pass reaches `w` at the end of its delivery route, it drops the calculated gradient into `w.grad`.

* **Crucial detail:** The backward pass doesn't replace what's in the bucket; it **adds** the new gradient to whatever is already in there (accumulation).
* When the graph (the delivery route) is shredded, the parameter and its `.grad` bucket **are left completely untouched.**

---

#### Let's walk through 2 steps of training to see it in action:

**Step 1:**

1. **Forward pass:** You push data through. PyTorch builds a brand-new computation graph (Map #1).
2. **Backward pass:** `loss.backward()` walks down Map #1, calculates a gradient of `2.0`, and drops it into `w.grad`.
3. **Cleanup:** `w.grad` now holds `2.0`. Map #1 is instantly destroyed to free up RAM.

*(If we forget to empty the bucket here, look at what happens next...)*

**Step 2:**

1. **Forward pass:** You push new data through. PyTorch builds a brand-new computation graph (Map #2).
2. **Backward pass:** `loss.backward()` walks down Map #2, calculates a new gradient of `3.0`, and drops it into `w.grad`.
3. **Accumulation:** PyTorch **adds** this to the bucket. `w.grad` is now `2.0 + 3.0 = 5.0`. Map #2 is destroyed.

Because the bucket is now holding a mix of old and new gradients, your optimizer will step in the wrong direction.

**This is exactly why we call `optimizer.zero_grad()`!** It simply walks up to all those `.grad` buckets and dumps them out (sets them to 0) before the next forward pass begins, ensuring you are only ever stepping based on the freshest data.

---


## 15 — Gradient Accumulation and Zeroing

```python
x = torch.tensor([1.0], requires_grad=True)

y = x ** 2
y.backward()
print(x.grad)        # 2

y = x ** 2           # rebuild the graph
y.backward()
print(x.grad)        # 4 — ACCUMULATED, not 2 again!

```

### Why does PyTorch accumulate?

Because some training scenarios *want* accumulation:

* **Gradient accumulation for huge batches**: split a large logical batch into smaller physical batches, call `.backward()` on each, then `.step()` once. The gradients add up naturally — equivalent to having processed the whole batch at once.
* **Multi-task learning**: sum gradients from multiple loss heads before updating.

For *standard* training where each batch is independent, accumulation is a bug waiting to happen. We must zero out the gradients and step the weights.

### The Remedy: The "PyTorch Shortcut"

In earlier lessons (like basic linear regression), you had to handle the gradient clearing and weight updates entirely by hand:

```python
# The "Before" (Manual Math)
w.grad.zero_()                         # 1. Manual Zeroing
b.grad.zero_()

loss.backward()                        # 2. Manual Backward

with torch.no_grad():                  # 3. Manual Step (Math)
    w -= learning_rate * w.grad
    b -= learning_rate * b.grad

```

Imagine having to write out those `.zero_()` and `-=` lines for all **235,146 parameters** in a real Neural Network! It would be impossible.

Because doing that math manually is so tedious, PyTorch created the `torch.optim` library. When you instantiate an optimizer, you hand it a master key to all your model's parameters. Now, instead of writing 200,000 lines of math, you just issue three simple commands to the automated manager:

1. `w.grad.zero_()` becomes **`optimizer.zero_grad()`** (Empties all 235,146 trash cans at once).
2. `loss.backward()` stays exactly the same (Calculates all 235,146 slopes).
3. `w -= lr * w.grad` becomes **`optimizer.step()`** (Applies the math formula to all 235,146 weights at once).

### The canonical training loop

By plugging those three optimizer shortcuts into a loop, we get the standard PyTorch training rhythm:

```python
for input_batch, target_batch in train_loader:
    optimizer.zero_grad()                         # 1. clear gradients
    loss = criterion(model(input_batch), target_batch)
    loss.backward()                               # 2. compute gradients
    optimizer.step()                              # 3. update weights

```

This four-step rhythm (`zero_grad` → forward → `backward` → `step`) appears in every PyTorch training script you'll ever read. Chapter 5 section 15 walks through this in detail in the context of LLM pretraining.

### Why `zero_grad()` goes at the *start* of the loop, not the end

Placing it before the forward pass is a defensive choice: if you ever `return` or `break` mid-loop, the next iteration still starts cleanly. After-the-fact zeroing can leave stale gradients if you exit early.
## 16 — Disabling Gradient Tracking

```python
x = torch.tensor([2.0], requires_grad=True)

# Method 1: torch.no_grad() context manager
with torch.no_grad():
    y = x ** 2
    print(y.requires_grad)    # False — no graph built

# Method 2: .detach() — break the link manually
y = x.detach() ** 2

# Method 3: .requires_grad_(False) — permanently flip the flag
x.requires_grad_(False)
```

### Two big reasons to disable gradient tracking

#### 1. Inference

When you're not training, you don't need gradients. Disabling them:

* **Saves memory** — PyTorch no longer stores activations for the backward pass. For a 124M model this can be 1–2 GB saved.
* **Saves time** — no graph bookkeeping per op.

```python
model.eval()
with torch.no_grad():
    output = model(input)
```

Every `generate_text_simple`, `generate`, and evaluation loop in chapter 5 wraps the forward pass in `torch.no_grad()`.

#### 2. Detaching from a computation

Sometimes you compute something with autograd, then want to use the value without propagating gradients further. For example:

```python
# Standard reference model in DPO (chapter 12)
with torch.no_grad():
    ref_logits = reference_model(input)    # don't train the reference model

# Compare against trainable model
trained_logits = trainable_model(input)
loss = some_function(ref_logits, trained_logits)
loss.backward()    # gradients only flow into trainable_model
```

### `.eval()` vs `torch.no_grad()` — they're different things

* `model.eval()` — sets a mode flag. Affects `nn.Dropout` (disabled) and `nn.BatchNorm` (use running stats). **Does not disable gradient tracking.**
* `torch.no_grad()` — context manager. Disables autograd. **Does not affect dropout or batchnorm.**

For inference you usually want **both**: `model.eval()` to suppress dropout, plus `torch.no_grad()` to save memory.

---

## 17 — Practice: Linear Regression From Scratch

```python
# Synthetic data: y = 2x + 1 + noise
torch.manual_seed(42)
X = torch.randn(100, 1)
y_true = 2 * X + 1 + 0.1 * torch.randn(100, 1)

# Trainable parameters (initialised randomly)
w = torch.randn(1, requires_grad=True)
b = torch.randn(1, requires_grad=True)

learning_rate = 0.1

for epoch in range(100):
    y_pred = w * X + b
    loss = ((y_pred - y_true) ** 2).mean()

    loss.backward()

    with torch.no_grad():
        w -= learning_rate * w.grad
        b -= learning_rate * b.grad
        w.grad.zero_()
        b.grad.zero_()
```

### What this cell teaches in one shot

Everything from sections 13–16 used together:

1. **`requires_grad=True`** on `w` and `b` — they're the trainable parameters.
2. **Forward pass** builds the computation graph: `y_pred = w * X + b`, `loss = mean((y_pred - y_true)^2)`.
3. **`loss.backward()`** populates `w.grad` and `b.grad` via the chain rule.
4. **`with torch.no_grad():`** wraps the manual weight update so the update itself doesn't get tracked as part of the graph (otherwise the graph grows forever).
5. **`w -= lr * w.grad`** is the gradient descent rule.
6. **`w.grad.zero_()`** resets gradients for the next iteration (the trailing underscore means "in-place"). This is what `optimizer.zero_grad()` does for you in a normal training loop.

### The math

For mean squared error:

$$L = \frac{1}{N}\sum_{i=1}^{N} (y_{\text{pred},i} - y_{\text{true},i})^2$$

Gradients:

$$\frac{\partial L}{\partial w} = \frac{2}{N}\sum_i (y_{\text{pred},i} - y_{\text{true},i}) \cdot x_i$$
$$\frac{\partial L}{\partial b} = \frac{2}{N}\sum_i (y_{\text{pred},i} - y_{\text{true},i})$$

PyTorch derives these automatically. You only wrote the forward formula.

### Expected outcome

After 100 epochs, `w` should converge to ~2.0 and `b` to ~1.0 — matching the true data-generating coefficients. The noise term prevents perfect convergence but the answer should be close.

---

## 18 — Building Your First Neural Network: nn.Module

```python
import torch.nn as nn
import torch.nn.functional as F

class SimpleNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.layer1 = nn.Linear(input_size, hidden_size)
        self.layer2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = F.relu(self.layer1(x))
        return self.layer2(x)


model = SimpleNN(input_size=20, hidden_size=50, output_size=2)
```

### Why subclass `nn.Module`?

`nn.Module` gives you four things for free:

1. **Parameter tracking** — any `nn.Parameter` or `nn.Module` attribute is automatically registered. `model.parameters()` returns them all.
2. **`.to(device)`** moves every parameter to GPU at once.
3. **`.train()` / `.eval()`** propagate the mode flag to every child module (affects dropout, batchnorm).
4. **`.state_dict()`** returns a serialisable dict of all parameters for saving/loading.

Building a model without `nn.Module` (using raw tensors as we did in section 17) is fine for tiny demos but breaks down quickly for anything real.

#### The two-method contract

Every `nn.Module` subclass must define two methods:

* **`__init__`** — declare submodules (`self.layer1 = nn.Linear(...)`). This is where parameters live.
* **`forward`** — describe the forward computation. Never call this directly — call the module (`model(x)`), which invokes `__call__` which calls `forward` plus hooks.

The pattern `super().__init__()` at the top of `__init__` is mandatory — it sets up the internal bookkeeping that makes the magic work.

#### `nn.Linear(in, out)` under the hood

A `Linear` layer computes:

$$y = xW^T + b$$

where `W` has shape `(out, in)` and `b` has shape `(out,)`. PyTorch follows the (out, in) convention internally, which is why `nn.Linear(20, 50).weight.shape` is `(50, 20)`.

This catches everyone the first time they try to manually copy weights from another framework (e.g. TensorFlow stores weights as `(in, out)` — a transpose is required, exactly as we saw in chapter 5 section 29).

#### Why use `F.relu` for the activation here, instead of `nn.ReLU`?

Both work. The functional form is more concise (no module to instantiate), and ReLU has no parameters to track, so there's no advantage to wrapping it in a module. Many modern transformer codebases use functional activations to keep `__init__` shorter.


### Extra notes

#### Direct Answer

It ran automatically because of a special Python feature called the `__call__` "magic method." PyTorch's `nn.Module` uses this feature to intercept your call and route it to your `forward` method behind the scenes.

#### The Explanation

Here is exactly what happens when you write `output = model(dummy_input)`:

1. **The Python Magic:** In Python, if you make a class and give it a method named `__call__`, you can use the object itself like a function. When you write `model(x)`, Python secretly translates that to `model.__call__(x)`.
2. **The PyTorch Hand-off:** Because your `SimpleNN` class inherits from `nn.Module` (`class SimpleNN(nn.Module):`), it inherits PyTorch's massive, pre-written `__call__` method.
3. **The Background Work:** When PyTorch's `__call__` runs, it doesn't just calculate your math. It sets up internal tracking, registers "hooks" (special debugging tools), and prepares the autograd engine.
4. **The Execution:** Finally, after doing all that invisible prep work, PyTorch's `__call__` method looks for *your* custom `forward` function and runs it.

#### Why You Should Never Write `model.forward(x)`

You might be tempted to just write `output = model.forward(dummy_input)` to make the code more readable. **Don't do it!** As the notes explicitly warn: *"Never call this directly — call the module (`model(x)`), which invokes `__call__` which calls `forward` plus hooks."*

If you call `.forward()` directly, it will do the math, but it will completely bypass step 3 (the background work). For a simple network it might seem fine, but once you start using advanced features, tracking gradients, or training across multiple GPUs, your model will silently break because it missed that crucial setup step.


---

## 19 — Common Layer Types

Five layer types appear constantly in LLM code:

### Linear (fully connected)

```python
linear = nn.Linear(in_features=512, out_features=256)
x = torch.randn(32, 512)
output = linear(x)   # shape (32, 256)
```

Used everywhere: Q/K/V projections in attention, FFN up/down projections, the final LM head.

### Embedding (critical for LLMs!)

```python
vocab_size = 10000
embedding_dim = 512
embedding = nn.Embedding(vocab_size, embedding_dim)

token_ids = torch.randint(0, vocab_size, (32, 50))   # batch=32, seq_len=50
embedded = embedding(token_ids)                       # shape (32, 50, 512)
```

`nn.Embedding(V, D)` is a `(V, D)` lookup table. Given a token id (an integer), it returns the corresponding row.

In LLMs there are typically **two** embedding tables:

* **Token embedding** — `(vocab_size, emb_dim)`. Looks up "what does word X mean?"
* **Positional embedding** — `(context_length, emb_dim)`. Looks up "what does being at position N mean?"

The two get added element-wise to produce the model's input representation.

#### smaller example explanation

##### Concept Note: How `nn.Embedding` Works

The `nn.Embedding` layer acts as a simple **lookup table** (or dictionary) that translates integer word IDs into dense vectors of numbers so the neural network can process them.

**1. The Lookup Table Setup (`nn.Embedding`)**

* **`vocab_size = 5`**: The total number of unique words the model knows. Because computers start counting at 0, the valid IDs for these words are **0, 1, 2, 3, and 4**. If you pass an ID of `5` or higher, PyTorch will crash with an "index out of bounds" error.
* **`embedding_dim = 3`**: The number of features used to represent each word. The table is initialized with random weights, which the model will adjust during training to learn the word's "meaning".
* **The Matrix**: This creates a `(5, 3)` weight matrix. 5 rows (one for each word ID), 3 columns (the features).

**2. The Shape Transformation**
When passing text through an LLM, the embedding layer is always the first step, and it predictably changes the shape of your data:

* **Input Shape**: `(batch, seq_len)`. In this example, `(2, 4)` represents 2 sentences, each containing 4 word IDs.
* **Output Shape**: `(batch, seq_len, features)`. Every single integer is replaced by its corresponding 3-number vector. The output becomes a 3D block: `(2, 4, 3)`. This 3D shape is the standard input format for all subsequent Transformer layers.

**3. The Proof (Copy-Paste Mechanic)**
The embedding step is not doing any math; it is just doing a direct, 1-to-1 copy-paste from the lookup table.

* Notice that Row 2 in the lookup table (Index 1) is exactly `[ 1.6948, -0.1397,  0.2857]`.
* In the input, Sentence 1 starts with ID `1`. In the output, the first vector is exactly `[ 1.6948, -0.1397,  0.2857]`.
* Sentence 2 contains the ID `1` twice in a row. In the output, you can see that same vector printed twice in a row.

### LayerNorm (used in every transformer)

```python
layer_norm = nn.LayerNorm(512)
normalized = layer_norm(embedded)
```

Normalises each sample's features independently. Chapter 4 section 8 walks through the math; this layer is exactly the same as the custom `LayerNorm` class built there, but implemented in C++ for speed.

#### Explanation

Here is the "small" version of the LayerNorm code to continue your script, followed by a conceptual note you can add to your notes.

##### The Code

```python
# We use 3 because our embedding_dim_sm (the last dimension) is 3
layer_norm_sm = nn.LayerNorm(3)

# Pass our 3D tensor through the normalization layer
normalized_sm = layer_norm_sm(embedded_sm)

print("=== 4. AFTER LAYERNORM ===")
print(f"Shape: {normalized_sm.shape}")
print(normalized_sm)

```

*(If you print this out, you'll see the shape is still exactly `(2, 4, 3)`, but the numbers inside have completely changed!)*

---

##### Concept Note: How `nn.LayerNorm` Works

**1. What it does**
LayerNorm acts like a volume leveler for your data. It normalizes each sample's features independently so that they have a mean of 0 and a standard deviation of 1. In our `embedded_sm` tensor of shape `(2, 4, 3)`, LayerNorm looks at the **3 features** for every single word individually.

**2. The Math Intuition**
For a single word represented by 3 numbers (e.g., $x = [x_1, x_2, x_3]$), LayerNorm does the following:

1. Calculates the average (mean) of those 3 numbers: $\mu$
2. Calculates how spread out they are (variance/standard deviation): $\sigma$
3. Subtracts the mean from each number, and divides by the standard deviation:

$$x_{\text{norm}} = \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}}$$



*(Note: $\epsilon$ is just a tiny number added so we don't accidentally divide by zero).*

**3. Why we need it**
In deep neural networks (especially Transformers), as numbers are multiplied through dozens of layers, they can quickly explode to massive values or shrink to zero. LayerNorm forces the numbers back into a nice, stable range centered around 0, which keeps the training stable and healthy.

**4. The Shape Transformation**
LayerNorm does **not** change the shape of your tensor. A `(2, 4, 3)` tensor goes in, and a `(2, 4, 3)` tensor comes out. Only the values themselves are squished and scaled.

#### The Math Intuition of LayerNorm: Why Normalization Doesn't Destroy Data

Important Question: *"If the specific, raw numbers contain the information, doesn't squishing them into a standard box destroy that information?"*

The short answer is **no, we don't lose the meaning**. Here is the mathematical intuition behind why the information survives, which comes down to two big concepts: **Relative Patterns** and **The Secret Parameters**.

##### 1. We keep the "Melody" (Relative Patterns)

Imagine you are listening to a song, and suddenly someone turns the volume knob down by 50%. Did you lose the song? No. The *absolute* volume changed, but the *relative* distances between the loud drum beats and the quiet whispers stayed exactly the same. The melody is preserved.

In mathematics, LayerNorm is a **linear transformation**. It shifts and scales the data, but it strictly preserves the relative distances between the numbers.

* If feature $A$ was twice as big as feature $B$ before normalization, feature $A$ will still be proportionally larger than feature $B$ after normalization.
* The neural network doesn't care about the *absolute* size of the numbers; it cares about the *pattern* across the 512 features. The pattern is completely untouched.

##### 2. The Secret Safety Net: Gamma ($\gamma$) and Beta ($\beta$)

I kept the math formula simple in the last note, but PyTorch's `nn.LayerNorm` actually has a second step that I didn't show you.

After it squishes your data to a mean of 0 and a standard deviation of 1, LayerNorm multiplies the result by a weight called **Gamma ($\gamma$)** and adds a bias called **Beta ($\beta$)**.

The true formula looks like this:


$$y = \gamma \left( \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} \right) + \beta$$

**Here is the genius part:** $\gamma$ and $\beta$ are *trainable parameters* (they have `requires_grad=True`).

* $\gamma$ is initialized as `1`, and $\beta$ is initialized as `0`.
* But as the network trains, if it realizes, *"Hey, I actually really needed that specific variance and mean to understand this data!"*, it can adjust $\gamma$ and $\beta$ via backpropagation to completely **undo** the normalization and stretch the numbers back to their original scale!

##### Summary of the Intuition

We normalize the data because raw, un-normalized numbers often have wild variances that cause gradients to explode, making the network crash or fail to learn.

By forcing the data to a standard scale (mean 0, variance 1), we stabilize the math. But we give the network the $\gamma$ and $\beta$ knobs so that **it gets to choose** exactly what the optimal scale and shift should be for the next layer.

We don't lose the data; we just clean it up and let the network decide how loud the volume should be.




### Dropout (regularisation)

```python
dropout = nn.Dropout(p=0.1)   # drop 10% of activations
dropped = dropout(normalized)
```

During training, each activation is independently zeroed with probability `p`. During eval (`model.eval()`), dropout is a no-op. This prevents over-reliance on any single neuron and improves generalisation.

A subtle detail: dropout **scales the surviving values** by `1/(1-p)` during training so the expected sum is unchanged. This is what lets you switch between train and eval modes without re-tuning the network.

### Putting them together in a transformer block

```python
class TransformerBlock(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.norm1 = nn.LayerNorm(cfg["emb_dim"])
        self.attn  = MultiHeadAttention(...)
        self.norm2 = nn.LayerNorm(cfg["emb_dim"])
        self.ffn   = FeedForward(...)
        self.dropout = nn.Dropout(cfg["drop_rate"])
```

Every one of those layers appeared in this section. Chapter 4 builds the full block.

#### Small Example Dropout explanation

**How Dropout Works: Zeroing and Scaling**

Seeing a small example is actually highly recommended because Dropout does a **secret mathematical trick** that catches almost every beginner off guard.

If you just print the shape, you miss what happens to the actual numbers. Here is a tiny snippet to add to your notes so you can see the trick in action. I set the dropout to 50% (`p=0.5`) so the effect is super obvious.

### The Code

```python
# Create a Dropout layer that drops 50% of the values
dropout_sm = nn.Dropout(p=0.5)

# We must ensure the layer is in "training" mode (this is the default)
dropout_sm.train() 

dropped_sm = dropout_sm(normalized_sm)

print("=== 5. AFTER DROPOUT (p=0.5) ===")
print(f"Shape: {dropped_sm.shape}")
print(dropped_sm)

```

If you run this and compare `dropped_sm` to your previous `normalized_sm`, you will notice two massive changes:

1. **Zeroing:** About half of the numbers have been completely overwritten with `0.0000`.
2. **Scaling (The Secret Trick):** Look at the numbers that survived. **They have doubled in size!** ---

#### Concept Note: How `nn.Dropout` Works

**1. What it does (The "Zeroing")**
During training, Dropout randomly turns off a percentage of the activations (determined by `p`) by setting them to zero. This acts as regularization: it forces the network to distribute information across all neurons rather than relying too heavily on any single path, which prevents overfitting.

**2. The Secret Trick (The "Scaling")**
If you turn off 50% of your network's signals, the overall "volume" of the output drops by half. If you then tried to evaluate the model without dropout, the volume would suddenly be twice as loud, which would break the math.
To fix this, PyTorch automatically **scales the surviving values up** by `1 / (1 - p)` during training.

* If `p = 0.5`, surviving values are multiplied by `2`.
* If `p = 0.1` (10%), surviving values are multiplied by `1.11`.
Because of this scaling, the expected sum of the outputs remains exactly the same, allowing you to seamlessly switch between training and evaluation.

**3. Train vs. Eval Modes**
Dropout behaves completely differently depending on the model's mode.

* When running `model.train()`, dropout is **active** (zeroing and scaling happen).
* When running `model.eval()`, dropout is completely **disabled** (it acts as a pass-through and touches nothing).

---

## 20 — Activation Functions: ReLU, GELU, SiLU, Sigmoid

```python
x = torch.linspace(-3, 3, 100)

plt.figure(figsize=(15, 4))
plt.subplot(1, 4, 1); plt.plot(x, F.relu(x));        plt.title('ReLU')
plt.subplot(1, 4, 2); plt.plot(x, F.gelu(x));        plt.title('GELU')
plt.subplot(1, 4, 3); plt.plot(x, F.silu(x));        plt.title('SiLU')
plt.subplot(1, 4, 4); plt.plot(x, torch.sigmoid(x)); plt.title('Sigmoid')
plt.show()
```

### Each one in one sentence

| Activation | Formula | Use case |
|------------|---------|----------|
| **ReLU** | $\max(0, x)$ | The default for older networks. Cheap. Has a kink at 0 → "dying ReLU" problem. |
| **GELU** | $0.5x(1 + \tanh(\sqrt{2/\pi}(x + 0.044x^3)))$ | Used in GPT-2 and many modern LLMs. Smooth. |
| **SiLU** (aka Swish) | $x \cdot \sigma(x)$ | Used in Llama and modern open-weight LLMs. Smoother than GELU. |
| **Sigmoid** | $1/(1+e^{-x})$ | Binary classification heads, gates in older RNNs. Rare in transformer hidden layers. |

### Why activations matter

A neural network without activations is just a sequence of linear transformations — which by linearity collapses to a single linear transformation. Activations introduce **non-linearity**, letting the network represent arbitrary functions.

### Why GELU/SiLU beat ReLU for transformers

ReLU has zero gradient for any negative input. In a deep network, this means a fraction of neurons effectively die — their gradient is zero, they never update. Smooth alternatives (GELU, SiLU) always have *some* gradient, preserving information flow through deep stacks.

Chapter 4 section 9 builds GELU from scratch and visualises this comparison in detail.

---

## 21 — nn.Sequential for Quick Models

```python
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(128, 10),
)

output = model(input)
```

`nn.Sequential` chains modules in order. `output = model(x)` is equivalent to passing `x` through each module one at a time.

### When to use Sequential vs a custom Module

* **Use Sequential** when the architecture is a straight line — input flows through each layer in order, no skip connections, no branches.
* **Use a custom Module** when you need branching, residual connections, conditional logic, or multiple inputs/outputs.

Every transformer block needs the custom path because residual connections branch off and join back. Sequential can't express that.

### Indexing into Sequential

```python
model[0]      # first layer (the Linear(784, 256))
model[2]      # third layer (Dropout)
list(model.children())   # all children in order
```

This is how chapter 5's `load_weights_into_gpt` reaches into `ff.layers[0]` and `ff.layers[2]` to copy weights into specific positions of the FFN's `nn.Sequential`.

---

## 22 — Model Inspection: Counting Parameters

```python
def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

print(f"Total trainable parameters: {count_parameters(model):,}")

for name, param in model.named_parameters():
    print(f"  {name:20s} | shape: {tuple(param.shape)} | params: {param.numel():,}")
```

### `model.parameters()` vs `model.named_parameters()`

* `parameters()` — yields just the `nn.Parameter` tensors.
* `named_parameters()` — yields `(name, parameter)` tuples. Names like `"layer1.weight"`, `"layer1.bias"`.

Both walk the entire model recursively, finding every parameter in every nested submodule.

### Why `if p.requires_grad`?

Some scenarios freeze parts of a model (e.g. fine-tuning only the last layer, keeping the rest frozen). Counting only `requires_grad=True` parameters gives the **trainable** count, which is what determines:

* Memory required for optimizer state (Adam needs 2× per trainable param)
* Effective model capacity for the current task
* Training time per step

### Real LLM example

For GPT-2 small (124M total) fine-tuned with LoRA at rank 8:
* Total parameters: 124,439,808
* Frozen parameters: 124,162,560
* Trainable (LoRA only): 277,248 — about 0.22%

That ratio is the entire reason LoRA works — you can fine-tune a giant model by training a tiny adapter that's the size of a small file.

---

## 23 — Dataset and DataLoader

```python
from torch.utils.data import Dataset, DataLoader


class SimpleDataset(Dataset):
    def __init__(self, X, y):
        self.X = X
        self.y = y

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


dataset = SimpleDataset(X_train, y_train)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

for batch_X, batch_y in dataloader:
    print(batch_X.shape, batch_y.shape)
    break
```

### The two-class contract

PyTorch's data pipeline has a clean separation:

* **`Dataset`** — "how do I get one sample?". You implement `__len__` and `__getitem__`. Pure logic for indexing a single item.
* **`DataLoader`** — "how do I batch, shuffle, and parallelise?". Wraps a `Dataset` and adds batching, shuffling, multi-worker loading.

### Why this separation matters

You can build complex pipelines:

```python
DataLoader(dataset,
           batch_size=32,
           shuffle=True,            # randomise order each epoch
           num_workers=4,           # parallel data loading
           pin_memory=True,         # speed up CPU→GPU transfer
           drop_last=True)          # drop final partial batch
```

…without touching your `Dataset` class. Same dataset, different loader configurations for train vs val.

### How LLM data pipelines use this

Chapter 2's `GPTDatasetV1`:

```python
def __getitem__(self, idx):
    return self.input_ids[idx], self.target_ids[idx]
```

Returns a `(input_chunk, target_chunk)` pair for index `idx`. `DataLoader` then stacks these into batches automatically.

The customisation point: implementing `__getitem__` is where the next-token-prediction shift-by-one logic lives.

### `num_workers > 0` and the GIL

With `num_workers=0`, data loading happens in the main process — synchronous with training. The GPU sits idle waiting for the next batch.

With `num_workers=4`, four subprocesses prefetch batches in parallel. The GPU stays busy.

For very small datasets (like chapter 5's 5,000-token toy training set), the fork overhead dominates and `num_workers=0` is actually faster. For real datasets (millions of samples), `num_workers=4` or `8` is essential.

### Extra Notes

This code sets up PyTorch's official data pipeline! It solves a very specific problem: when you have millions of data points, you cannot feed them all into a neural network (or your GPU) at the exact same time. You need to feed them in small, randomized chunks called "batches".

PyTorch handles this by splitting the workload into a two-class contract: the **`Dataset`** and the **`DataLoader`**.

Here is exactly what is happening in our code and how `__getitem__` fits into the puzzle.

#### 1. The `Dataset` (The Librarian)

The `SimpleDataset` class has one job: **"How do I get a single sample of data?"**.
It doesn't know anything about batches or neural networks. It just holds your raw data (`X` and `y`) and knows how to fetch one specific item when asked.

* `__init__`: Saves your 1000 rows of features (`X_train`) and 1000 labels (`y_train`) inside the class.
* `__len__`: Tells PyTorch exactly how many items exist total (1000) so it knows when an "epoch" (one full pass over the data) is finished.

#### 2. How `__getitem__` works

You specifically asked how to use `__getitem__`. This is a special Python "magic method" (like `__init__` or `__call__`).

You **never** actually write `dataset.__getitem__(5)`. Instead, defining this method allows you to use standard bracket indexing on your object, just like a normal Python list! When you write `dataset[5]`, Python secretly translates that into `dataset.__getitem__(5)` behind the scenes.

Here is how you can use it manually to inspect your data:

```python
# 1. Fetch the very first row of data
first_x, first_y = dataset[0]  
print(f"Features: {first_x.shape}") # Will be [20]
print(f"Label: {first_y}")          # Will be 0 or 1

# 2. Fetch the 42nd row of data
random_x, random_y = dataset[41] 

```

In LLM development, `__getitem__` is exactly where you put your custom logic for fetching text tokens and creating the "shift-by-one" target sequences for next-token prediction.

#### 3. The `DataLoader` (The Delivery Truck)

While the `Dataset` gets one item, the `DataLoader` asks the question: **"How do I batch, shuffle, and parallelize?"**.

When you run this line:

```python
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

```

You are telling the DataLoader: *"Go to my Dataset, pick 32 random index numbers (because `shuffle=True`), use `__getitem__` 32 times to scoop up those specific rows, and stack them into a single block."*.

#### 4. The Output

```python
for batch_X, batch_y in dataloader:
    print(f"Batch X shape: {batch_X.shape}, Batch y shape: {batch_y.shape}")
    break

```

When this `for` loop runs, the DataLoader delivers the stacked blocks.

* Your original `X_train` had 20 features per row.
* Because `batch_size=32`, the DataLoader stacked 32 rows together.
* Therefore, `batch_X.shape` prints out as `(32, 20)`.

This clean separation means you can write your `__getitem__` logic once, and then easily test different batch sizes, shuffling rules, or multi-CPU loading strategies just by changing the `DataLoader` settings!

---

## 24 — Loss Functions for Each Task Type

```python
# Binary classification
loss_binary = F.binary_cross_entropy(predictions_binary, targets_binary)

# Multi-class classification
loss_multi = F.cross_entropy(logits, target_class_indices)

# Regression
loss_mse = F.mse_loss(predictions, targets)
loss_mae = F.l1_loss(predictions, targets)
```

### Which loss for which task

| Task | Loss | Input expectations |
|------|------|--------------------|
| Binary classification | `binary_cross_entropy` | Predictions in (0, 1), targets in {0, 1} |
| Binary classification (logits) | `binary_cross_entropy_with_logits` | Raw scores, targets in {0, 1} |
| Multi-class classification | `cross_entropy` | Raw logits `(N, C)`, target class indices `(N,)` |
| Regression (squared error) | `mse_loss` | Continuous predictions and targets |
| Regression (absolute error) | `l1_loss` | Continuous predictions and targets |

### Cross-entropy — the workhorse for LLMs

```python
logits = torch.randn(10, 5)            # 10 samples, 5 classes
targets = torch.randint(0, 5, (10,))   # class indices
loss = F.cross_entropy(logits, targets)
```

**Crucially**: PyTorch's `cross_entropy` expects **raw logits**, NOT softmax probabilities. It applies softmax internally (using the log-sum-exp trick for stability).

This is the loss for **every next-token prediction** in an LLM. Chapter 5 sections 7–9 build it up from first principles.

### MSE vs L1

* **MSE (squared error)** — penalises large errors quadratically. Mathematically convenient (smooth gradient). Sensitive to outliers.
* **L1 (absolute error)** — penalises errors linearly. More robust to outliers, gradients are constant (less smooth near the optimum).

For LLM training you almost never use these — cross-entropy is the universal choice.

---

## 25 — Optimizers: SGD, Adam, AdamW

```python
# SGD with momentum
optimizer_sgd = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)

# Adam (most popular)
optimizer_adam = torch.optim.Adam(model.parameters(), lr=0.001)

# AdamW (Adam with decoupled weight decay)
optimizer_adamw = torch.optim.AdamW(model.parameters(),
                                     lr=0.001,
                                     weight_decay=0.01)
```

### How each differs

#### SGD

The simplest. Update rule: `w -= lr * grad`. With `momentum=0.9`, it also tracks a running velocity to smooth out gradient noise. Still used in computer vision; rarely used for LLMs.

#### Adam

Maintains per-parameter running estimates of the gradient mean and variance. Adapts the effective learning rate for each parameter based on its history. Faster convergence than SGD on most problems.

Update rule (simplified):
$$m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t$$
$$v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$$
$$w \leftarrow w - \frac{\text{lr}}{\sqrt{v_t}+\epsilon} m_t$$

#### AdamW

The current default for every LLM. Identical to Adam except weight decay is applied **directly** to the weights rather than mixed into the gradient. This subtle change matters a lot when weight decay is large — Adam's coupling makes the decay strength scale with the learning rate in unintended ways.

### Memory cost

Each optimizer keeps state per parameter:

| Optimizer | State per param | Memory cost (model_size ×) |
|-----------|----------------|---------------------------|
| SGD | None (or 1 buffer with momentum) | 0–1× |
| Adam, AdamW | 2 buffers (m, v) | 2× |

For a 124M model in float32:
* Model weights: ~498 MB
* Gradients: ~498 MB (one float32 grad per param)
* Adam state: ~996 MB (two buffers)
* **Total**: ~2 GB just for optimisation

This is why training a large model requires far more VRAM than running inference on it.

### Learning rate tuning

The single hyperparameter to get right. Typical values:

* From-scratch pretraining: `1e-4` to `3e-4`
* Fine-tuning a pretrained model: `2e-5` to `2e-4`
* LoRA fine-tuning: `1e-4` to `5e-4` (LoRA can tolerate higher lr because adapters are random init)
* DPO / preference alignment: `1e-5` (very low — we don't want to disturb the SFT baseline)

### Extra Notes

This is one of the most brutal realities of deep learning hardware! It is exactly why you can run a massive 8-Billion parameter Llama model on your laptop (inference), but you need a giant server GPU to train it.

To understand why training eats up so much memory, think of **Inference** as *reading a book*, and **Training** as *rewriting and editing a book*.

#### 1. Inference (Reading the Book)

When you are just running inference (generating text), you only need two things in your GPU's memory (VRAM):

1. **The Model Weights:** The actual parameters of the model. For a 124 Million parameter model using `float32` (which takes 4 bytes per parameter), $124 \times 4 \approx 498$ Megabytes.
2. **Current Activations:** A tiny bit of scratchpad memory to hold the input you just passed in and the output it's generating.

Because we wrap inference in `with torch.no_grad():`, PyTorch turns off all the tracking and math history, keeping the memory footprint at roughly **~500 MB**.

#### 2. Training (Editing the Book)

When you train, you aren't just reading the numbers; you are actively calculating how to change them. To do this, PyTorch has to keep massive, invisible ledgers in the background.

Here is exactly where that **~2 GB** of VRAM goes for that same 124M model:

* **The Model Weights (~498 MB):** We still have to hold the actual model itself.
* **The Gradients (~498 MB):** When we call `loss.backward()`, PyTorch calculates the slope (direction to move) for *every single parameter*. It has to store those slopes in the `.grad` buckets. Because there is one gradient for every weight, this is an exact 1:1 copy of the model size.
* **The Optimizer State / Adam (~996 MB):** The Adam optimizer doesn't just look at the current gradient; it keeps a history of how the gradients have been moving to smooth out the updates. Specifically, it tracks two things for *every single weight*: the running mean (momentum) and the running variance. That requires **two more complete copies** of the model's size.
* **Forward Activations (Variable):** To do the calculus chain rule during the backward pass, PyTorch has to memorize the intermediate outputs of every single layer from the forward pass.

**The Final Math:**
1 copy (Weights) + 1 copy (Gradients) + 2 copies (Adam States) = **4x the memory just to hold the basic training data**.

Here is an interactive memory visualizer. You can toggle between Inference and Training, and switch the optimizer to see exactly how these invisible "copies" stack up and consume your GPU's VRAM!

This massive overhead is exactly why techniques like **LoRA** (which you'll see later in the book) were invented. LoRA freezes the main model and only tracks gradients and optimizer states for a tiny, 1% add-on, cutting that massive VRAM requirement down to something a consumer GPU can handle!

---

## 26 — Complete Training Loop

```python
model = SimpleNN(input_size=20, hidden_size=50, output_size=2)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

num_epochs = 10
for epoch in range(num_epochs):
    model.train()
    epoch_loss = 0.0
    correct = 0
    total = 0

    for batch_X, batch_y in dataloader:
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()
        _, predicted = outputs.max(dim=1)
        correct += (predicted == batch_y).sum().item()
        total += batch_y.size(0)

    avg_loss = epoch_loss / len(dataloader)
    accuracy = 100 * correct / total
    print(f"Epoch {epoch+1}/{num_epochs} | Loss: {avg_loss:.4f} | Acc: {accuracy:.2f}%")
```

### The structure

Two nested loops:

* **Outer (epochs)** — one pass over the entire dataset.
* **Inner (batches)** — one pass over one mini-batch.

Inside the inner loop, the four-step optimisation rhythm:

```
zero_grad → forward → backward → step
```

### Counting accuracy along the way

```python
_, predicted = outputs.max(dim=1)
correct += (predicted == batch_y).sum().item()
```

`outputs.max(dim=1)` returns a `(values, indices)` tuple. We discard the values (the underscore) and keep the predicted class indices. Comparing with `batch_y` gives a boolean tensor; `.sum()` counts the `True`s.

The `.item()` call extracts the Python int from the 0-D tensor. Always do this for running tallies to avoid keeping an autograd graph alive across the whole epoch.

### How this scales to LLMs

Chapter 5's `train_model_simple` is structurally identical, with three additions:

1. **Periodic evaluation** every `eval_freq` steps (not just per-epoch).
2. **Sample generation** at the end of each epoch to qualitatively check progress.
3. **Token tracking** for the secondary x-axis on the loss plot.

The core rhythm (`zero_grad → forward → backward → step`) never changes, regardless of model size.

### Extra Notes

#### 1. DataLoaders: "The Delivery Trucks"

In machine learning, you never test your model on the exact same data it used to study, otherwise it just memorizes the answers (overfitting). Therefore, we split our data into a **Study Guide** (Training Data) and a **Final Exam** (Testing Data).

The `DataLoader` acts as a delivery truck that scoops up rows of data and feeds them to the model in chunks (batches).

* **`train_loader` (`shuffle=True`):** Scoops up the Study Guide. We shuffle this so the model doesn't just memorize the order of the flashcards.
* **`test_loader` (`shuffle=False`):** Scoops up the Final Exam. We do *not* shuffle this because we want our evaluation to be deterministic and consistent every time we grade it.

#### 2. The "Cookie Cutter" Analogy (Understanding Batch Shapes)

When you define a neural network layer in PyTorch, it is always expecting an input tensor structured as: `(batch_size, input_size)`. It is crucial to understand the difference between these two numbers:

* **The `input_size` is a strict rule:** If you build `SimpleNN(input_size=20)`, you are defining the physical architecture of the network. The model has exactly 20 "doors" to let data in.
* **The `batch_size` is completely flexible:** PyTorch is built from the ground up to do parallel math. It does not care how many *examples* you feed it at once, as long as every single example has exactly 20 features.

**The Cookie Cutter Analogy:**
Think of your `SimpleNN` as a cookie cutter designed specifically for a 20-ingredient cookie.

* If you pass in `torch.randn(1, 20)`, you are sliding exactly 1 cookie under the cutter.
* If your DataLoader passes in `batch_x` with shape `(32, 20)`, you are sliding a massive tray of 32 cookies under the cutter.

Because GPUs are optimized for parallel processing, the model will instantly "stamp" all 32 cookies at the exact same time. It will then hand you back an output of shape `(32, 2)`—meaning it processed 32 examples in one shot, and gave you 2 output scores for each one.

#### 3. CrossEntropyLoss: The Shape Mismatch Magic

One of the most common points of confusion in PyTorch is how the loss function calculates the score when the prediction and the answer key are entirely different shapes:

* **`predictions` shape:** `(32, 2)`
* **`batch_y` shape:** `(32,)`

It feels like a mathematical mismatch, but it is actually a brilliant optimization!

**What `predictions [32, 2]` means:**
For every single one of the 32 examples in the batch, the model outputs **two raw scores** (called "logits"). Column 0 is how strongly it believes the answer is Class 0. Column 1 is how strongly it believes the answer is Class 1. (e.g., `[2.5, -1.2]`).

**What `batch_y [32]` means:**
Your labels are not probabilities; they are just a simple list of the **correct indices**. A single row is just the integer `0` or `1`.

**How PyTorch bridges the gap:**
In older frameworks, you had to "one-hot encode" your labels to make the shapes match (turning the label `0` into `[1.0, 0.0]`). PyTorch says: *"Don't waste memory doing that, I'll do the lookup for you!"*

When you run `loss = criterion(predictions, batch_y)`, PyTorch uses the 1D vector as instructions to grade the 2D matrix row-by-row:

1. It looks at Row 1 of your labels (`batch_y`). Let's say the true label is `1`.
2. It goes to Row 1 of your `predictions`.
3. Because the true label is `1`, it ignores the score in column 0, looks directly at the score in column 1, and penalizes the model based on whether that specific score was high enough.

#### 4. The `.item()` Memory Trap

In the training loop, you must write: `total_loss += loss.item()`.

* **Why not just `total_loss += loss`?** In PyTorch, `loss` is not just a number; it is a Tensor that has the *entire computation graph* attached to it so the `.backward()` pass can work. If you add the raw Tensor to your running total, PyTorch will keep every single computation graph from every single batch stored in your RAM. Your script will quickly crash with an **Out of Memory (OOM)** error.
* **What `.item()` does:** It acts as an extractor. It smashes the PyTorch Tensor shell open, leaves the heavy computation graph behind in the trash, and pulls out the lightweight, standard Python float (e.g., `0.45`).

#### 5. Calculating Accuracy (Vectorization vs. Python Loops)

Writing a standard Python loop like `for index, row in enumerate(predictions):` to calculate accuracy is logically correct, but it forces the GPU to sit idle and runs incredibly slowly.

Instead, we use PyTorch "idioms" (Vectorization) to do the math instantly across the whole batch. Here is how the condensed PyTorch code (`correct += (predicted == batch_y).sum().item()`) actually breaks down:

```python
# 1. Get the raw results from the model's output
# .max(dim=1) looks across columns. It returns the high scores (which we throw 
# in the '_' garbage variable) and the index of the winner (0 or 1).
_, predicted_classes = predictions.max(dim=1)

# 2. See which predictions match the answer key
# This creates a 1D Boolean Tensor of True/False values.
correct_guesses_tensor = (predicted_classes == batch_y)

# 3. Add up all the 'True' values 
# True counts as 1, False counts as 0. This collapses the array into a single 
# 0-Dimensional Integer Tensor (e.g., tensor(24)).
total_correct_tensor = correct_guesses_tensor.sum()

# 4. Extract the plain Python number
# Strip away the tensor shell and add the raw integer to the scoreboard.
correct_prediction_count += total_correct_tensor.item()

```

#### 6. The "Magic Shield" for Evaluation

During the evaluation phase, we do not want the model to learn, and we don't want to waste RAM building computation graphs.

* **`model.eval()`**: Changes the behavior of layers like Dropout and BatchNorm to "test mode" (e.g., it stops randomly dropping neurons).
* **`with torch.no_grad():`**: This is the magic shield. It completely shuts off PyTorch's autograd engine. No delivery routes (computation graphs) are built, saving massive amounts of memory and time.
* **No Optimizer:** We completely remove the `zero_grad`, `backward`, and `step` functions. The model is forced to guess using only what it already knows.


---

## 27 — Saving and Loading Models

```python
# Save just the weights (recommended)
torch.save(model.state_dict(), 'model.pth')

# Load into a fresh model
loaded_model = SimpleNN(input_size=20, hidden_size=50, output_size=2)
loaded_model.load_state_dict(torch.load('model.pth', weights_only=True))
loaded_model.eval()
```

### Why `state_dict` over `torch.save(model)`?

`state_dict` is a Python dict mapping parameter names to tensor values. It contains **only data**, no class code. This means:

* You can refactor `SimpleNN` (rename it, move it to a different file) without breaking saved checkpoints.
* You can load weights from older versions of your code into newer model architectures, as long as the parameter names still match.
* Saved files are portable across PyTorch versions in a way that pickled full objects are not.

In contrast, `torch.save(model)` pickles the entire Python object including the class definition. Rename your class and the old checkpoint becomes unloadable.

### `weights_only=True` — important security flag

Without it, `torch.load` calls `pickle.load` under the hood, which can execute arbitrary code from a malicious `.pth` file. With `weights_only=True`, only tensors and basic types are unpickled.

Default in PyTorch:
* < 2.6 → `False` (insecure)
* ≥ 2.6 → `True` (secure)

Set it explicitly for forward compatibility.

### Checkpointing the optimizer state too

For resumable training (covered in chapter 5 section 24):

```python
torch.save({
    'model_state_dict':     model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'epoch':                current_epoch,
}, 'checkpoint.pth')
```

Saving the optimizer state preserves Adam's running mean/variance buffers, which take many warmup steps to re-stabilise if lost. Without them, resumed training is unstable for the first ~100 steps.

---

## 28 — GPU Usage and Memory Management

### Device selection

```python
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")
```

The standard one-liner. Chapter 5 section 14 expands this to also check for Apple MPS (M1/M2/M3 GPUs).

### Moving things to the GPU

```python
# Tensors
tensor_gpu = tensor.to(device)
# Note: tensors need explicit reassignment

# Models
model = model.to(device)
# Note: nn.Module .to() returns self but also modifies in-place
```

**Both inputs AND the model must be on the same device** or matmul will error.

### Training on GPU

The training loop is *identical* — just add `.to(device)` for input and target inside the inner loop:

```python
for batch_X, batch_y in dataloader:
    batch_X = batch_X.to(device)
    batch_y = batch_y.to(device)
    # ... rest of the loop unchanged
```

Or push it into a helper function (as chapter 5's `calc_loss_batch` does).

### CPU vs GPU speed

For the 5000×5000 matrix multiplication in the notebook:

```
CPU time:  ~5–10 seconds
GPU time:  ~0.05 seconds
Speedup:   100–200×
```

### When GPU *doesn't* help much

* **Very small models** — kernel launch overhead dominates.
* **Lots of Python-level branching** — Python is single-threaded; GPU sits idle.
* **Data loading bottleneck** — if the CPU can't deliver batches fast enough, the GPU starves.

`num_workers > 0` in the DataLoader and `pin_memory=True` are the standard fixes for the third one.

### Memory management

```python
if torch.cuda.is_available():
    torch.cuda.empty_cache()    # release cached memory
    print(f"Allocated: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")
    print(f"Cached:    {torch.cuda.memory_reserved(0)  / 1e9:.2f} GB")
```

* **Allocated** = memory currently used by active tensors.
* **Cached** = memory PyTorch has claimed from the OS (some of it may not be allocated to anything *right now* but is reserved for fast reuse).

`empty_cache()` returns the cached memory to the OS. Useful in long-running notebooks where you've created and destroyed several large models.

---

## 29 — Exercises

The notebook ends with four exercises that exercise the patterns you just learned:

### Exercise 1 — Tensor operations

Create a random 3×3 tensor and a 3×3 identity matrix, then compute their element-wise product, matrix product, and transpose. The smallest possible exercise — but if you can do this without looking anything up, you've internalised the basic tensor API.

### Exercise 2 — MNISTClassifier

Build a 3-layer fully-connected classifier for MNIST: 784 → 128 → 64 → 10 with ReLU activations and dropout between layers. This is the smallest "real" neural network you can build with PyTorch — and the structure scales directly to far more complex networks.

### Exercise 3 — train_one_epoch

Implement the canonical training loop as a reusable function: iterate the dataloader, zero gradients, forward, compute loss, backward, step, accumulate loss, return the average. The same skeleton you'll see in every PyTorch training script.

### Exercise 4 — TextClassifier with embeddings

Build a bag-of-words style text classifier: input is `(batch, seq_len)` token IDs → `nn.Embedding` lookup → average over seq dimension → two fully-connected layers → class logits. This is your first taste of how token-level inputs become fixed-size representations — the conceptual building block of every LLM.

### A note on the exercises

These four collectively cover ~80% of PyTorch's day-to-day API. If you can do all four from memory after working through the rest of the notebook, you have a solid foundation for chapter 2 onward.
