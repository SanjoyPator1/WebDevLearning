# Chapter 1: Tensors & Shape Algebra

## Table of Contents

1. [Why Tensors Still Trip You Up](#1-why-tensors-still-trip-you-up)
2. [What a Tensor Really Is: Storage + Metadata](#2-what-a-tensor-really-is-storage--metadata)
3. [Creating Tensors](#3-creating-tensors)
4. [dtype and device](#4-dtype-and-device)
5. [Indexing and Slicing](#5-indexing-and-slicing)
6. [The Reshaping Family: view vs reshape vs contiguous](#6-the-reshaping-family-view-vs-reshape-vs-contiguous)
7. [Adding, Removing, and Faking Dimensions](#7-adding-removing-and-faking-dimensions)
8. [Broadcasting and Reductions](#8-broadcasting-and-reductions)
9. [Key Takeaways + Master Decision Table](#9-key-takeaways--master-decision-table)

---

# 1: Why Tensors Still Trip You Up

## What This Chapter Is Really About

Code like `.view(batch, num_heads, seq_len, head_dim).transpose(1, 2)`
appears in every transformer implementation, and it is easy enough to
*recognize*. But can you predict, before running the cell, whether the next
`.view()` you write will crash with
`RuntimeError: view size is not compatible with input tensor's size and stride`?
Can you say whether `expand` will blow up your GPU memory or cost nothing at
all? If not, you have been memorizing incantations instead of owning a mental
model.

The thesis of this chapter is that **one mental model — a tensor is a flat
block of memory plus a viewing recipe — replaces the entire pile of memorized
rules**. Once you see `view`, `reshape`, `contiguous`, `expand`, `transpose`,
and slicing as different ways of *re-describing the same flat memory*, every
"when do I use which?" question answers itself, and every shape error becomes
readable instead of scary.

*Everything in this chapter runs on tiny tensors you can check by hand. That
is deliberate: fluency comes from being able to simulate PyTorch in your
head.*

---

# 2: What a Tensor Really Is: Storage + Metadata

## The Intuition

Think of a tensor like a **warehouse aisle and a display window**.

The **storage** is the warehouse aisle itself: one long, flat sequence of boxes sitting on the floor in memory, with no rows, columns, or dimensions. These boxes are heavy and never move.

The **metadata** is a recipe card attached to the front display window: "To arrange these boxes into a 2×3 grid in the window, start at the beginning, take 3 steps forward down the warehouse aisle for the next row, and 1 step forward for the next column." Change the numbers on the recipe card, and the *same underlying boxes* instantly form a completely different layout in the display window — without moving a single physical box in the back.

The recipe card (metadata) always tracks three crucial things:

* **size** (shape): how many elements exist along each dimension of the display window.
* **stride**: how many slots down the flat warehouse aisle you must jump to move exactly one step along a given dimension.
* **storage offset**: the exact index in the flat warehouse aisle where the tensor's very first element `[0, 0, ...]` lives.

## The Math

For a tensor with strides $(s_0, s_1, \dots, s_{n-1})$ and offset $o$, the element at grid coordinate $(i_0, i_1, \dots, i_{n-1})$ is retrieved from this exact position down the flat warehouse aisle:

$$\text{position}(i_0, \dots, i_{n-1}) = o + \sum_{k=0}^{n-1} i_k \cdot s_k$$

Breaking down the recipe: $i_k$ is your target coordinate along dimension $k$, $s_k$ is that dimension's stride (the step size down the flat memory aisle), and $o$ is the starting point inside the storage block. That single formula handles all tensor indexing. Every shape modification in PyTorch is just a calculation updating $(s_k)$ and $o$.

## Dry-Run with Tiny Numbers

```
storage = [0, 1, 2, 3, 4, 5]        ← one flat block, made by torch.arange(6)

A = storage viewed as (2, 3), strides (3, 1), offset 0:

        col 0   col 1   col 2
row 0 [   0       1       2   ]     A[i][j] = storage[0 + i*3 + j*1]
row 1 [   3       4       5   ]     A[1][2] = storage[3+2] = storage[5] = 5 ✓

B = A.t()  → size (3, 2), strides (1, 3), offset 0 — SAME storage:

        col 0   col 1
row 0 [   0       3   ]            B[i][j] = storage[0 + i*1 + j*3]
row 1 [   1       4   ]            B[2][1] = storage[2+3] = storage[5] = 5 ✓
row 2 [   2       5   ]

```

Notice what transposing (`t()`) did: it **did not move a single number in memory**. It simply swapped the strides from `(3, 1)` to `(1, 3)`. The warehouse boxes remain untouched; only the recipe card changed. This is why transposing is free and instantaneous.

This also explains why the transposed tensor is called **non-contiguous**: reading it normally (left-to-right, top-to-bottom) no longer walks the flat warehouse aisle in order `0,1,2,3,4,5`. Instead, the worker has to jump around out of order: `0,3,1,4,2,5`.

```
                    ┌─────────────────────────────┐
                    │ storage: [0, 1, 2, 3, 4, 5] │   one flat memory block
                    └──────┬───────────────┬──────┘
                           │               │
              ┌────────────┴───┐       ┌───┴────────────┐
              │ A: size (2,3)  │       │ B: size (3,2)  │
              │    stride (3,1)│       │    stride (1,3)│
              │  [[0,1,2],     │       │  [[0,3],       │
              │   [3,4,5]]     │       │   [1,4],       │
              │  contiguous ✓  │       │   [2,5]]       │
              └────────────────┘       │  contiguous ✗  │
                                       └────────────────┘

```

You can inspect these internal recipe values at any time using standard PyTorch methods: `tensor.stride()`, `tensor.storage_offset()`, `tensor.is_contiguous()`, and `tensor.data_ptr()` (the direct memory address — if two tensors share the same `data_ptr()`, they point to the exact same warehouse storage).

## Key Takeaways for Section 2

A tensor is nothing more than a flat memory array bound to a `(size, stride, offset)` recipe. Because most "shape operations" simply rewrite the numbers on the recipe card without altering the flat array, they execute instantly. Consequently, modifying the values in one view will automatically mutate the values across all other views sharing that same storage block. A tensor is **contiguous** when reading its dimensions in standard order perfectly matches the physical order of the underlying flat memory.

*Next: the functions that create storage in the first place.*

# 3: Creating Tensors

## The Problem It Solves

Every pipeline starts by getting data *into* tensors — token IDs from a
tokenizer, weights from an init scheme, masks from padding logic. The creation
functions differ on two axes that matter constantly: **does it copy or share
memory?** and **what dtype/device does the result get?** Getting either wrong
produces bugs that don't crash — they just silently train on garbage.

## The Toolbox

**From existing data.** `torch.tensor(data)` always **copies** and infers
dtype from the data (Python ints → `int64`, Python floats → `float32`).
`torch.as_tensor(data)` and `torch.from_numpy(arr)` **share memory** with a
NumPy array when possible — mutate one side and the other changes too.

**Fresh allocations.** `torch.zeros(shape)`, `torch.ones(shape)`,
`torch.full(shape, value)` initialize every element. `torch.empty(shape)`
allocates but does **not** initialize — you get whatever bytes were already
in memory, which is why printing an `empty` tensor shows garbage values. Use
it only when you will immediately overwrite every element.

**Ranges.** `torch.arange(start, end, step)` counts by a *step size*
(end-exclusive, like Python's `range`); `torch.linspace(start, end, steps)`
places an exact *count* of points (end-inclusive).

**Random.** `torch.rand(shape)` is uniform on $[0, 1)$; `torch.randn(shape)`
is standard normal $\mathcal{N}(0, 1)$; `torch.randint(low, high, shape)`
gives integers — your go-to for fake token IDs in tests.

**The `*_like` family (The Blueprint).** Functions like `torch.zeros_like(t)`, `torch.ones_like(t)`, and `torch.randn_like(t)` treat an existing tensor `t` as a blueprint.

* **The confusion:** Why not just use `torch.zeros()`?
* **The explanation:** If you have a tensor `t` that is shape `(4, 4)`, made of `float16` data, and sitting on `GPU 1`, doing `torch.zeros((4, 4))` will give you a tensor on the **CPU** in `float32`. If you try to add them together, your program crashes.
* **The solution:** `torch.zeros_like(t)` tells PyTorch: "I don't care what numbers are inside `t`. Just give me a brand new tensor filled with zeros that matches `t`'s exact shape, exact data type, and lives on the exact same hardware." It guarantees compatibility.

## Dry-Run: Copy vs Share

```
import numpy as np
numpy_ids = np.array([10, 20, 30])

copied  = torch.tensor(numpy_ids)       # new storage
shared  = torch.from_numpy(numpy_ids)   # SAME storage as numpy_ids

numpy_ids[0] = 999                      # mutate the NumPy side

copied  → tensor([ 10, 20, 30])         # unchanged: it was a copy
shared  → tensor([999, 20, 30])         # changed: it shares the bytes
```

*This bites for real when a `Dataset` wraps a NumPy array with `from_numpy`
and something later mutates the array in place — your "fixed" training data
quietly changes under you.*

## Decision Guide: Which Creation Function

| You want... | Reach for | Why |
|---|---|---|
| A safe, independent copy of a list/array | `torch.tensor(data)` | always copies, infers dtype |
| Zero-copy wrapping of a NumPy array | `torch.from_numpy(arr)` / `as_tensor` | shares memory — fast, but aliased |
| A new tensor matching another's shape/dtype/device | `*_like(t)` | hygiene: can't be on wrong device |
| Sequential integers (positions, token indices) | `arange` | end-exclusive, step-based |
| Exactly $n$ evenly spaced floats | `linspace` | end-inclusive, count-based |
| Scratch space you'll fully overwrite | `empty` | skips initialization cost |
| Fake token IDs for a quick test | `randint(0, vocab, (B, T))` | right dtype (`int64`) for free |

## Key Takeaways for Section 3

`torch.tensor` copies; `from_numpy`/`as_tensor` share. Prefer `*_like` when a
tensor must match an existing one — it eliminates a whole class of
device/dtype mismatch bugs. `empty` is uninitialized by design.

*Next: what those dtypes actually are and why NLP is picky about them.*

---


# 4: dtype and device

## 1. The Integer vs. Float Rule (The Mailbox Analogy)

An LLM juggles three different types of data, and PyTorch does not tolerate mixing them up.

Think of `nn.Embedding` (your token vocabulary) like a wall of numbered **mailboxes** at a post office. Box 1 holds the embedding for "apple", Box 2 holds "banana".

If you ask PyTorch to open Box 1, it works. If you ask it to open Box 2, it works. **If you ask PyTorch to open Box 1.0 or Box 2.7, it will crash.** You cannot have a fraction of a mailbox.

This is the most common beginner error:

```python
emb = nn.Embedding(100, 8)
# CRASH: You passed a float (1.0), but mailboxes need integers (1)
emb(torch.tensor([1.0, 2.0])) 

```

**The Rule:** * **Token IDs & Indices:** Must be Integers (`torch.int64` / `torch.long`).

* **Masks:** Must be Booleans (`torch.bool`). They cost 1 byte instead of 8, saving massive amounts of memory.
* **Weights & Activations:** Must be Floats (`torch.float32`, `torch.bfloat16`). Neural networks run on continuous math.

## 2. The 16-bit Float Wars: fp16 vs bf16

By default, neural networks use `float32` (32 bits per number). To make models train faster and use less memory, we cut that in half to 16 bits. But *how* you spend those 16 bits changes everything.

Imagine you only have a budget of 16 bits to spend on a number. You must divide your budget between two things:

1. **Exponent Bits (The Range):** How massively huge (or microscopic) the number can get before breaking.
2. **Mantissa Bits (The Precision):** How many decimal places of accuracy you get.

Here is how the two formats spent their budget:

* **fp16 bought Precision:** It spent bits on the mantissa. It has great decimal accuracy, but terrible range. Its maximum value is only `65,504`. If your neural network generates a number like `70,000`, fp16 instantly explodes into `NaN` (Not a Number) and ruins your training.
* **bfloat16 (bf16) bought Range:** It kept the massive range of a 32-bit float but sacrificed precision. It can hold numbers in the trillions, but it rounds off the tiny decimals.

**Why LLMs choose bf16:** Deep learning is remarkably tolerant of rounding errors (noise). But deep learning is completely destroyed by `NaN` explosions (overflow). Therefore, we prefer the massive range of `bf16`.

## 3. The Device Trap

Moving data to your GPU (e.g., `cuda:0`) is required to make things fast. But the `.to(device)` command **does not move the tensor**. It makes a photocopy of the tensor and puts the photocopy on the GPU.

If you don't save the photocopy to a variable, you lose it, and your data stays on the CPU.

```python
# WRONG: Creates a GPU copy and immediately throws it in the trash
tensor.to('cuda') 

# RIGHT: Overwrites the variable with the new GPU copy
tensor = tensor.to('cuda') 

```

If you try to multiply a CPU tensor by a GPU tensor, PyTorch throws the famous `Expected all tensors to be on the same device` error.

## 4. Cheat Sheet: Which dtype to use?

| Data Type | Reach for... | Why |
| --- | --- | --- |
| **Tokens & Indices** | `int64` / `torch.long` | Lookup tables (Embeddings) require whole numbers. |
| **Masks** | `bool` | Extremely memory efficient (1 byte). |
| **Default Weights** | `float32` | Standard precision, completely safe from overflow. |
| **Fast LLM Training** | `bfloat16` | Won't overflow on large logits; natively supported on modern GPUs (Ampere/RTX 3000+). |
| **Older GPUs** | `float16` | Required if your GPU doesn't support bf16, but requires extra code to prevent NaN explosions. |

---

# 5: Indexing and Slicing

## The Intuition

Given the storage+strides model from Section 2, there are exactly two kinds of
"give me part of this tensor": selections that can be described by a new
`(size, stride, offset)` recipe over the *same* storage — these are free
**views** — and selections that cannot, which must **copy**. Regular slices
are regular enough to be recipes. Arbitrary index lists are not.

## The Rules

**Basic slicing is a view.** `t[1]`, `t[:, 2]`, `t[::2]`, `t[1:4]` — all just
adjust size/stride/offset. Writing into a slice writes into the original.

```
batch = torch.arange(12).view(3, 4)      # 3 sequences, 4 token positions
first_seq = batch[0]                     # view: offset 0, size (4,), stride (1,)
every_other_pos = batch[:, ::2]          # view: size (3,2), stride (4,2) ← stride trick!
first_seq[0] = 999                       # batch[0,0] is now 999 too
```

**Integer-array ("fancy") and boolean indexing copy.**
`t[[2, 0, 1]]` (reorder rows by an index list) and `t[mask]` (keep elements
where a `bool` mask is `True`) both gather scattered elements — no single
stride pattern can describe "rows 2, 0, 1 in that order", so PyTorch
materializes a new tensor.

**Boolean indexing flattens.** `t[mask]` returns a **1-D** tensor of the kept
elements, however many dimensions `t` had. This is a feature for NLP: with
`tokens` of shape `(batch, seq)` and a `bool` pad mask, `tokens[mask]` is the
flat list of *real* (non-pad) tokens — exactly what you want for computing
loss over non-padded positions.

**Two small power tools.** Indexing with `None` inserts a size-1 axis
(`t[None]` turns `(seq,)` into `(1, seq)` — instant batch dimension), and
`...` (ellipsis) means "all the dimensions I didn't mention"
(`t[..., 0]` grabs the first element of the last dim regardless of rank).

## Dry-Run: View or Copy?

```
t = torch.arange(6).view(2, 3)          # storage [0,1,2,3,4,5]

t[1]        → tensor([3, 4, 5])          view  (offset 3, stride (1,))
t[:, 1]     → tensor([1, 4])             view  (offset 1, stride (3,))
t[[1, 0]]   → tensor([[3,4,5],[0,1,2]])  COPY  (no stride can express "swap rows")
t[t > 3]    → tensor([4, 5])             COPY, flattened to 1-D
```

## Key Takeaways for Section 5

Slices are views (writes propagate!); fancy/boolean indexing copies. Boolean
indexing flattens to 1-D — perfect for "all real tokens" extraction. `None`
adds an axis; `...` skips axes. When you need per-row lookups by an index
*tensor* (e.g., "the target token's logit in every row"), that is `gather` —
chapter 2's territory.

*Next: the most feared error message in PyTorch, defused.*

---

# 6: The Reshaping Family: view vs reshape vs contiguous

## The Problem It Solves

You constantly need the same numbers under a different shape: flattening
`(batch, seq, heads, head_dim)` back to `(batch, seq, d_model)` after
attention, folding batch and sequence together before a linear layer, and so
on. PyTorch gives you three tools that look interchangeable — `view`,
`reshape`, `contiguous` — and one legendary crash. The difference between
them is exactly the storage/strides story.

## The One Rule

**`view` never copies.** It re-describes existing storage with new
size/stride — which is only possible when the elements, read in the new
shape's row-major order, already sit in that order in memory. If they don't,
`view` refuses:

```
RuntimeError: view size is not compatible with input tensor's size and
stride (at least one dimension spans across two contiguous subspaces).
Use .reshape(...) instead.
```

**`reshape` = "view if possible, otherwise silently copy."** It always
succeeds; you just don't know (without checking) whether you aliased the old
storage or paid for a copy.

**`contiguous()` materializes.** It copies the elements into fresh storage in
row-major order (or returns `self` untouched if already contiguous), after
which any `view` works.

## Dry-Run: The Crash, Explained by Strides

```
t = torch.arange(6).view(2, 3)     # storage [0,1,2,3,4,5], strides (3,1)
tt = t.t()                         # size (3,2), strides (1,3) — same storage

tt as a matrix:   [[0, 3],
                   [1, 4],
                   [2, 5]]

tt.view(6)  → RuntimeError!

Why: view(6) wants a recipe over the EXISTING storage that reads
     0, 3, 1, 4, 2, 5   ...in that order, with ONE constant stride.
     From 0→3 the memory jump is +3; from 3→1 the jump is −2.
     No single stride does both.  →  no valid recipe  →  loud failure.

tt.contiguous()          # copies into NEW storage [0,3,1,4,2,5]
  .view(6)               # now trivially a view of that new storage  ✓
tt.reshape(6)            # does exactly the same two steps, silently  ✓
```

Two conveniences round out the family: a single `-1` lets PyTorch infer one
dimension (`t.view(batch, -1)`), and `flatten(start_dim, end_dim)` is
readable shorthand for the common "merge these adjacent dims" case.

## The Multi-Head Attention Convention

This is where the rule earns its keep. The canonical MHA dance:

```
(B, T, d_model) ──view──▶ (B, T, H, d_head) ──transpose(1,2)──▶ (B, H, T, d_head)
                  free                            free, but now NON-contiguous
                                    ... attention happens ...
(B, H, T, d_head) ──transpose(1,2)──▶ (B, T, H, d_head) ──contiguous().view──▶ (B, T, d_model)
                       still non-contiguous              copy once, then free
```

The first `view` works because a fresh projection output is contiguous. After
the round-trip through `transpose`, the tensor is *not* contiguous, so
every serious implementation writes `.contiguous().view(B, T, d_model)` — an
explicit, visible copy — rather than `reshape`, which would hide it.

## Decision Guide: view vs reshape vs contiguous().view

| Situation | Use | Why |
|---|---|---|
| You believe no copy is needed and want a *guarantee* | `view` | fails loudly if you're wrong — a free correctness assert |
| You don't care whether a copy happens | `reshape` | always works, maybe copies silently |
| You know a copy is needed and want it *visible* | `.contiguous().view(...)` | the reader sees the cost |
| Merging adjacent dims readably | `flatten(i, j)` | intention-revealing |

*The habit worth building: default to `view`. When it crashes, that crash is
information — you just learned your tensor is non-contiguous, and now you get
to decide whether the copy is acceptable, instead of `reshape` deciding for
you.*

## Key Takeaways for Section 6

`view` = recipe change only, fails when memory order can't support the new
shape. `reshape` = `view`-or-silent-copy. `contiguous()` = explicit copy into
row-major order. After any `transpose`/`permute`, expect to need `contiguous`
before `view`.

*Next: dimensions that come, go, and pretend to exist.*

---

# 7: Adding, Removing, and Faking Dimensions

## squeeze and unsqueeze

`unsqueeze(dim)` inserts a size-1 axis (same as indexing with `None`);
`squeeze(dim)` removes axis `dim` *if* it has size 1. Both are views.

The trap is **no-argument `squeeze()`**, which removes *every* size-1
dimension. With batch size 1 — common at inference — `(1, seq, d)` becomes
`(seq, d)` and your batch dimension silently vanishes, usually crashing three
functions later where the error looks unrelated. *Always pass an explicit
`dim` to `squeeze`.*

## expand vs repeat: The Free Fake and the Real Copy

Here the stride model pays off most. **`expand` creates a view with
stride 0** along the expanded (size-1) dimension: moving along that axis jumps
zero slots in memory, so every "row" is literally the same memory read again.
**`repeat` physically tiles the data** into new storage.

## Dry-Run: The Memory Bill

```
row = torch.randn(1, 50000)                  # one vocab-sized row: 50,000 floats

expanded = row.expand(64, 50000)
  storage: unchanged, still 50,000 floats    → 0 new bytes
  size (64, 50000), stride (0, 1)            ← stride 0 = "re-read the same row"

repeated = row.repeat(64, 1)
  storage: brand new, 3,200,000 floats       → 64× the memory (12.8 MB in fp32)
```

The catch: an expanded tensor is **read-only in spirit** — writing to one
element would "write to all 64 rows" at once, so in-place writes raise an
error. Rule: `expand` for anything you only read (masks, broadcasting
helpers); `repeat` only when downstream code genuinely writes to each copy.

**The canonical NLP use** — growing a padding mask to attention-score shape
with zero copies:

```
pad_mask: (B, T)          "which positions are real tokens"
   │ unsqueeze(1).unsqueeze(2)         (both free: views)
   ▼
(B, 1, 1, T)
   │ expand(B, H, T, T)                (free: strides 0 on dims 1, 2)
   ▼
(B, H, T, T)              ready to mask attention scores — 0 bytes copied
```

## transpose vs permute vs movedim

All three are stride-swapping views; they differ only in how you *name* the
rearrangement. `transpose(d0, d1)` swaps exactly two dims — right for the MHA
`(B, T, H, d) ↔ (B, H, T, d)` swap. `permute(...)` takes the full new order —
right when more than two dims move at once, e.g. NCHW→NHWC style
`permute(0, 2, 3, 1)`. `movedim(src, dst)` slides one dim to a new spot and
reads most literally. All of them produce non-contiguous results — remember
Section 6 before the next `view`.

## Key Takeaways for Section 7

`unsqueeze`/`squeeze(dim)` add/remove size-1 axes as views; never call
`squeeze()` bare. `expand` is a stride-0 *free* broadcast view (read-only);
`repeat` is a real, memory-hungry copy. `transpose` for two dims, `permute`
for a full reorder — both leave you non-contiguous.

*Next: the machinery that makes most `expand` calls unnecessary.*

---

# 8: Broadcasting and Reductions

## The Intuition

**Broadcasting** is PyTorch doing the `unsqueeze`+`expand` dance for you,
implicitly, whenever an elementwise op receives mismatched shapes. It is the
reason `logits / temperature` works with a scalar and `embeddings * mask`
works with a mask one dimension short. **Reductions** (`sum`, `mean`, `max`)
are the inverse move — collapsing dimensions away. Mastering the pair means
you can write masked pooling, normalization, and attention plumbing without a
single Python loop.

## The Two Broadcasting Rules

Align the two shapes **from the right**. Then, for each aligned pair of
dimensions:

1. Equal sizes → fine.
2. One of them is 1 (or missing entirely) → the size-1 side is *stretched*
   (a stride-0 expand, no copy) to match the other.
3. Anything else → `RuntimeError`.

## Dry-Run: Right-Alignment Arithmetic

```
A: shape (4, 1)        B: shape (3,)

right-align:      A:  4   1
                  B:      3
compare last dim:     1 vs 3   → stretch A to 3     ✓
compare next:         4 vs (missing) → stretch B    ✓
result shape: (4, 3)

A = [[0],[1],[2],[3]],  B = [10, 20, 30]
A + B:
  row 0:  0+10  0+20  0+30   =  10  20  30
  row 1:  1+10  1+20  1+30   =  11  21  31
  row 2:  2+10  2+20  2+30   =  12  22  32
  row 3:  3+10  3+20  3+30   =  13  23  33
```

## The Silent Killer

Broadcasting fails loudly when shapes are incompatible — that's the *good*
case. The dangerous case is when they are compatible *by accident*:

```
scores  : shape (n,)      e.g. n = 4
baseline: shape (n, 1)

scores - baseline:
  right-align:  (4,) vs (4,1)  →  1 stretches → result (4, 4)   ← !!!

You wanted 4 numbers. You got a 4×4 matrix of every pairwise difference,
it flowed into the loss, nothing crashed, and the model just trains badly.
```

The defense is a one-line habit: `assert scores.shape == baseline.shape`
before elementwise ops between tensors that *should* already match — or an
explicit `baseline.squeeze(1)`.

## Reductions: dim Is "the Dimension That Disappears"

$$\text{sum over dim } k: \quad (d_0, \dots, d_k, \dots, d_{n-1}) \;\longrightarrow\; (d_0, \dots, \cancel{d_k}, \dots, d_{n-1})$$

`t.sum(dim=1)` on shape `(B, T)` yields `(B,)` — dimension 1 is the one
*consumed*. With `keepdim=True` it survives as size 1, `(B, 1)`, which is
precisely the shape broadcasting wants for the follow-up division. That is
the whole reason `keepdim` exists.

## The Worked NLP Example: Masked Mean Pooling

Average each sequence's token embeddings, ignoring padding — the standard way
to turn per-token vectors into one sentence vector:

```
embeddings: (B, T, D)      mask: (B, T)  — 1.0 for real tokens, 0.0 for pad

Step 1  mask.unsqueeze(-1)                  (B, T, 1)     free view
Step 2  embeddings * mask.unsqueeze(-1)     (B, T, D)     broadcast zeroes pad rows
Step 3  (…).sum(dim=1)                      (B, D)        sum over positions
Step 4  mask.sum(dim=1, keepdim=True)       (B, 1)        real-token counts
Step 5  step3 / step4                       (B, D)        broadcast divide  ✓

Tiny numbers, B=1, T=3, D=2, one pad position:
  emb  = [[1,2], [3,4], [9,9]]     mask = [1, 1, 0]
  step2 = [[1,2], [3,4], [0,0]]
  step3 = [4, 6]
  step4 = [2]
  step5 = [2, 3]      ← the pad row [9,9] never contaminated the mean ✓

(without keepdim, step4 would be shape (B,) — and dividing (B, D) by (B,)
 right-aligns D against B: either a crash or, if B == D, a silent disaster)
```

## Key Takeaways for Section 8

Right-align, stretch the 1s, no copies. Fear shape-*compatible* mistakes more
than shape errors — `(n,)` vs `(n,1)` is the classic. Reduction `dim` is the
dim that disappears; `keepdim=True` keeps it broadcastable for the very next
op. Masked mean pooling exercises the entire chapter in five lines.

---

# 9: Key Takeaways + Master Decision Table

The single mental model: **storage + (size, stride, offset)**. Views edit the
recipe (free, aliased); copies make new storage (costly, independent). Every
tool in this chapter is one or the other, and knowing which is the whole game.

| I want to... | Reach for | View or copy? |
|---|---|---|
| Wrap a Python list safely | `torch.tensor(...)` | copy |
| Wrap a NumPy array with zero copy | `from_numpy` / `as_tensor` | shares memory |
| Match another tensor's shape/dtype/device | `zeros_like` / `randn_like` | new storage |
| Store token IDs | dtype `int64` | — |
| Store masks | dtype `bool` | — |
| 16-bit training floats on modern GPUs | `bfloat16` | — |
| Take a row / slice / stride through | basic indexing `t[a:b:c]` | view |
| Reorder rows / select by index list | fancy indexing `t[idx_list]` | copy |
| Keep only elements where a condition holds | boolean mask `t[mask]` (flattens!) | copy |
| Reshape with a no-copy guarantee | `view` | view (or loud error) |
| Reshape, copy-if-needed silently | `reshape` | either |
| Make memory row-major before a `view` | `contiguous()` | copy (if needed) |
| Add / remove a size-1 axis | `unsqueeze(d)` / `squeeze(d)` — never bare `squeeze()` | view |
| Broadcast a tensor without memory cost | `expand` | view (stride 0, read-only) |
| Tile data that will be written per-copy | `repeat` | copy |
| Swap two dims | `transpose(d0, d1)` | view (non-contiguous) |
| Reorder many dims | `permute(...)` | view (non-contiguous) |
| Sum/average away a dimension | `sum(dim=k)` / `mean(dim=k)` | new tensor |
| Keep the reduced dim for broadcasting | `keepdim=True` | — |

**Connection forward:** Chapter 2 takes this vocabulary and covers the
*operations* between tensors — the matmul family, masking, `gather`, softmax,
and sampling — the fifteen ops that make up 90% of every LLM forward pass.
