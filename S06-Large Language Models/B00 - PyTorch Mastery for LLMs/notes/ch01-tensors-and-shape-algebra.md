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

## The Intuition: Views vs. Copies

When you ask PyTorch for a specific part of a tensor, you are asking for a new Display Window. PyTorch will respond in one of two ways depending on *how* you ask:

**1. The View (Free and Fast):** If your request follows a predictable, repeating pattern (like "give me every second row"), the warehouse worker can simply write a **new recipe card** (new offset, size, and stride) for the *exact same warehouse aisle*. We call this a **View**.

* *Danger/Superpower:* Because it shares the same physical boxes, if you change a number in a View, you instantly change the original tensor!

**2. The Copy (Slow and Safe):**
If your request is chaotic or out-of-order (like "give me row 2, then row 0, then row 1"), the worker *cannot* express this with a simple "take $X$ steps" stride recipe. They are forced to physically build a **brand new warehouse aisle** and duplicate the boxes. We call this a **Copy**.

* *Note:* Changing a Copy does *not* affect the original tensor.

## The Rules of Extraction

### 1. Basic Slicing is always a VIEW

Any time you use the standard colon `:` syntax (`start:stop:step`), PyTorch can calculate a new stride. It is free.

```python
batch = torch.arange(12).view(3, 4)      # Original warehouse setup
first_seq = batch[0]                     # VIEW: Just changes offset to 0
every_other_pos = batch[:, ::2]          # VIEW: Just multiplies the stride by 2

first_seq[0] = 999                       # Watch out! batch[0,0] is now 999 too.

```

### 2. "Fancy" (List) Indexing is always a COPY

If you pass a list or array of specific indices (e.g., `[2, 0, 1]`), PyTorch panics. No single stride pattern can jump backward and forward like that. It is forced to copy the data to a new memory block.

### 3. Boolean (Mask) Indexing is a COPY *and* FLATTENS

If you pass a mask of True/False values, PyTorch copies only the `True` values into a new tensor.

* **The NLP Feature:** Boolean indexing always returns a **1-Dimensional** tensor, destroying the original rows and columns. This is actually a massive feature for NLP: if you have a 2D batch of tokens and a pad mask, doing `tokens[mask]` instantly gives you a flat 1D list of *only the real tokens*, which is exactly what you need to calculate your loss function!

Here is the absolute simplest way to think about it.

Imagine a simple 2D grid, like an ice cube tray. Some slots have ice (real words), and some slots are empty (padding).

1. **The Rule:** In PyTorch, 2D grids *must* be perfect rectangles. Every row must have the exact same number of items.
2. **The Action:** You ask PyTorch to pull out only the ice (the real words) and leave the empty spaces behind.
3. **The Problem:** Row 1 might yield 3 pieces of ice, while Row 2 yields 4. You can no longer build a perfect rectangle out of this jagged data.
4. **The Solution:** Because PyTorch can't make a rectangle, it gives up on the 2D grid entirely. It dumps all the ice it collected into a single, straight 1D line.

**Why this is a superpower:**
When you are training an AI, you only want to penalize it for getting real words wrong. You don't want to waste time doing math on the empty padding. This flattening trick instantly throws the garbage away and gives you one solid, flat line of pure data to grade.


### 4. Two Small Power Tools

* **`None` (Adds a dimension):** `t[None, :]` instantly wraps your tensor in an extra dimension. (e.g., turning a single sequence into a batch of 1).
* **`...` (Ellipsis / Skip dimensions):** `t[..., 0]` means "I don't care how many dimensions this tensor has, just give me the very first element of the very last dimension."

## Dry-Run: View or Copy?

```python
t = torch.arange(6).view(2, 3)          # storage [0, 1, 2, 3, 4, 5]

# --- VIEWS ---
t[1]        # -> [3, 4, 5]              (View: offset=3, stride=(1,))
t[:, 1]     # -> [1, 4]                 (View: offset=1, stride=(3,))

# --- COPIES ---
t[[1, 0]]   # -> [[3,4,5], [0,1,2]]     (COPY: No stride can express "swap rows")
t[t > 3]    # -> [4, 5]                 (COPY: Flattened to 1D)

```

## Key Takeaways for Section 5

Basic slices (using `:`) are **views**; modifying them modifies the original data. Fancy indexing (using lists) and Boolean indexing (using `> < ==`) are **copies**. Boolean indexing flattens everything into a 1D line — a neat trick for extracting unpadded tokens. Use `None` to fake a batch dimension, and `...` to skip dimensions you don't want to type out.

*Next: the most feared error message in PyTorch, defused.*

---


# 6: The Reshaping Family: view vs reshape vs contiguous

## The Problem It Solves

You constantly need to change the shape of your data. You might need to flatten a 2D image into a 1D list, or fold sequence dimensions together. PyTorch gives you three tools that look like they do the exact same thing: `view`, `reshape`, and `contiguous`.

Knowing the difference between them is what separates beginners from pros.

## The Intuition: The Manager, The Worker, and The Warehouse

Remember our setup: The flat memory in your computer is a heavy row of boxes in the **Warehouse Aisle**. Your tensor is just a **Display Window** in the front of the store, managed by a worker with a **Recipe Card** (stride numbers).

**1. `view()` (The Strict Worker):** When you call `.view()`, you are asking the worker to write a *new* recipe card for the existing warehouse boxes. The worker is lazy. They will only do this if they can use a **single, consistent pattern** (stride) to walk down the aisle. If they have to jump back and forth randomly to fulfill your new shape, they will go on strike and throw a massive error. **`view` never copies data.**

**2. `contiguous()` (The Heavy Lifting):**
If your tensor is twisted up (like after a transpose), the worker's reading order is chaotic. Calling `.contiguous()` fires the worker and hires movers. The movers physically pack up all the boxes in the warehouse and line them up in a brand new, perfectly straight row that matches your current Display Window. **`contiguous` always copies data into a fresh memory block.**

**3. `reshape()` (The Shady Manager):**
When you call `.reshape()`, the manager takes over. The manager tries to just write a new recipe card (`view`). But if the worker goes on strike, the manager secretly hires the movers to build a new warehouse (`contiguous`), writes the recipe, and *doesn't tell you they spent the extra memory and time.* **`reshape` might be free, or it might be a slow copy. You never know.**

## Dry-Run: The Famous Crash, Explained

Let's see why `.view()` goes on strike.

```python
t = torch.arange(6).view(2, 3)     # Warehouse: [0, 1, 2, 3, 4, 5]
tt = t.t()                         # Transpose! Shape is now (3,2).

```

Because we transposed it, the matrix `tt` now looks like this in the Display Window:

```text
[[0, 3],
 [1, 4],
 [2, 5]]

```

Now, you ask to flatten it into a 1D line of 6 items: `tt.view(6)`.

* **The Worker's problem:** To flatten this left-to-right, top-to-bottom, the worker has to fetch boxes from the warehouse in this exact order: `0, 3, 1, 4, 2, 5`.
* **The Math:** To go from 0 to 3, the worker jumps **+3** boxes forward. To go from 3 to 1, the worker jumps **-2** boxes backward!
* **The Crash:** A recipe card can only hold *one* step size (stride). There is no single step size that means "jump forward 3, then backward 2". The worker goes on strike:

> `RuntimeError: view size is not compatible with input tensor's size and stride...`

**The Fix:**
You must physically rebuild the warehouse first so the boxes are physically in `0, 3, 1, 4, 2, 5` order.

```python
tt.contiguous().view(6)  # 1. Movers copy boxes to a new straight line. 2. Worker easily views it. 
tt.reshape(6)            # Does the exact same thing, but hides the copy from you.

```

## Two Extra Power Tools

1. **The Magic `-1`:** If you are reshaping and don't want to do the math for one of the dimensions, put a `-1`. PyTorch will figure it out for you. (e.g., `t.view(batch_size, -1)`).
2. **`.flatten()`:** A super readable shortcut for when you just want to squish dimensions together.

## Decision Guide: Which one do I use?

| Situation | Use | Why |
| --- | --- | --- |
| **Default Choice** | `view()` | It acts as a safety alarm. If it crashes, it tells you your memory is messy, which is great information to have. |
| **You know it's messy, but want to fix it safely** | `.contiguous().view()` | Explicit is better than implicit. Anyone reading your code knows exactly where the slow memory copy happens. |
| **You don't care about memory, just make it work** | `reshape()` | Good for quick scripts or tests where performance doesn't matter. |
| **Squishing a matrix into a flat line** | `flatten()` | Much easier to read than `.view(-1)`. |

*Pro-Tip for NLP:* In Transformer models (like ChatGPT), the Multi-Head Attention mechanism constantly transposes data. Every serious AI researcher writes `.contiguous().view(...)` in their attention code to safely handle the twisted memory.

## Key Takeaways for Section 6

`view` only changes the recipe, and fails if the underlying memory is messy. `contiguous` physically copies and cleans up messy memory. `reshape` is a manager that tries `view`, but secretly uses `contiguous` if it fails. **Default to `view`, and when it crashes, use `contiguous().view()` so you know where your memory is being copied.**

---

# 7: Adding, Removing, and Faking Dimensions

## 1. Squeeze and Unsqueeze (The Fake Dimensions)

Sometimes you have a single sequence of 10 tokens: shape `(10,)`. But your neural network demands a *batch* of sequences: shape `(1, 10)`. You need to add a "fake" dimension of size 1.

* **`unsqueeze(dim)`:** Adds a fake size-1 dimension at the location you specify. `t.unsqueeze(0)` turns `(10,)` into `(1, 10)`.
* **`squeeze(dim)`:** Removes a fake size-1 dimension. `t.squeeze(0)` turns `(1, 10)` back into `(10,)`. Both are free **views**.

**The Dangerous Trap:** If you call `squeeze()` with *no arguments*, PyTorch will maliciously hunt down and destroy *every* size-1 dimension it can find.
Imagine you have a batch size of 1 during testing: `(batch=1, seq=10, features=128)`. If you run `squeeze()`, PyTorch crushes the batch dimension, leaving you with `(10, 128)`. Three steps later, your code crashes because the batch dimension vanished. **Rule: Always pass a specific number to `squeeze(dim)`.**

## 2. expand vs. repeat: The Hologram vs. The Photocopy

You have a single row of data, and you need 64 copies of it. You have two choices, and they are completely different under the hood. Here, our Warehouse / Recipe Card analogy is beautiful.

**`expand()` (The Free Hologram):**
You ask the worker to fill a 64-row Display Window using the 1 row in the warehouse. The worker writes a new recipe card and sets the **Row Stride to 0**.

* *The Logic:* "To go to the next row, take **0 steps** down the warehouse aisle."
* The worker literally stands perfectly still and reads the exact same boxes 64 times.
* **Cost:** 0 new bytes of memory. It's a free hologram.
* **Catch:** It is strictly read-only. If you try to change a number in one of the rows, PyTorch throws an error, because changing it would instantly change all 64 "rows" simultaneously!

**`repeat()` (The Physical Photocopy):**
You tell the movers to physically duplicate the boxes.

* *The Logic:* They build 63 brand new warehouse aisles and copy the heavy boxes into all of them.
* **Cost:** Massive. If that row had 50,000 floats, you just copied 12.8 Megabytes of data for no reason.
* **Catch:** You can edit these rows independently, because they are real copies.

**Rule of Thumb:** Use `expand` if you just need to *read* the data (like applying a mask). Only use `repeat` if you genuinely plan to *modify* the copied rows later.

## 3. The Canonical NLP Trick: Expanding a Mask

In Transformers, you often start with a simple 2D mask of valid tokens `(Batch, Sequence)` and need to stretch it to match a massive 4D Attention matrix `(Batch, Heads, Sequence, Sequence)`. Doing this with `repeat` would crash your computer's memory. With `unsqueeze` and `expand`, it is instantly free:

```text
1. Start with mask:            (B, T)          
2. unsqueeze(1).unsqueeze(2):  (B, 1, 1, T)    <- Free! Added fake dimensions.
3. expand(B, H, T, T):         (B, H, T, T)    <- Free! Row Strides set to 0.

```

You just turned a tiny 2D mask into a massive 4D mask without copying a single byte of memory.

## 4. transpose vs. permute vs. movedim

These are just three different ways to rewrite the recipe card to change the order of your dimensions. All of them are free **views**, and **all of them make your memory non-contiguous** (messy).

* **`transpose(dim0, dim1)`:** Swaps exactly two dimensions. Perfect for the standard Attention swap: `(Batch, Sequence, Heads, Features)` ↔ `(Batch, Heads, Sequence, Features)`.
* **`permute(*dims)`:** Lets you completely scramble all dimensions at once. If you have an image `(Batch, Channels, Height, Width)` and want it to be `(Batch, Height, Width, Channels)`, you use `permute(0, 2, 3, 1)`.
* **`movedim(source, destination)`:** Literally just slides one dimension to a new spot. Easiest to read, but less common in older codebases.

## Key Takeaways for Section 7

Never use `squeeze()` without a number. `expand` creates free "hologram" rows by setting the memory stride to 0 (read-only). `repeat` physically duplicates data and hogs memory. `transpose` and `permute` are free views that scramble your memory layout, meaning you'll probably need `.contiguous()` soon after.

# 8: Broadcasting and Reductions

## 1. Broadcasting: The Automatic Hologram

**Broadcasting** is PyTorch doing the `unsqueeze` + `expand` (hologram) trick for you, completely automatically, whenever you try to do math with two tensors of different shapes.

This is why you can do `matrix / 2.0` (dividing a massive tensor by a single scalar) or multiply a 3D token embedding by a 2D mask. PyTorch temporarily stretches the smaller tensor into a "hologram" to match the bigger one, doing the math without copying any memory.

### The Two Rules of Broadcasting

Whenever you do math (like `A + B`), PyTorch lines up the shapes **from the right to the left**. Then, it checks each pair of dimensions:

1. **Perfect Match:** If the numbers are the same, great.
2. **The Magic "1":** If one of the numbers is `1` (or missing), PyTorch *stretches* it (stride-0 hologram) to match the other number.
3. **Crash:** If the numbers are different and neither is `1`, it throws an error.

**Dry-Run:**

```text
A: shape (4, 1)        B: shape (3,)

Right-align them:      
A:     4      1
B:            3
------------------
Result: 
- Last dim: 1 vs 3. PyTorch stretches A to 3.
- Next dim: 4 vs missing. PyTorch stretches B to 4.
- Final Result Shape: (4, 3) Matrix!

```

## 2. The Silent Killer: Accidental Broadcasting

When shapes break the rules, PyTorch crashes. That is the *best case scenario* because it tells you you made a mistake.

The dangerous scenario is when your shapes are completely wrong, but they *accidentally follow the rules*.

```text
scores:   shape (4,)      (You have 4 scores)
baseline: shape (4, 1)    (You have 4 baselines)

You want to do: scores - baseline (Subtract the baseline from each score).
Right-align:  (4,) vs (4,1). 
Result: PyTorch stretches BOTH and gives you a (4, 4) matrix!

```

You wanted 4 numbers. PyTorch quietly gave you a 4x4 matrix of every possible pairwise combination. This matrix flows into your neural network, nothing crashes, but your AI learns absolute garbage.

**The Defense:** Before doing math between two tensors that *should* be the same shape, aggressively use assertions: `assert A.shape == B.shape` or explicitly squeeze them: `baseline.squeeze(1)`.

## 3. Reductions: The Trash Compactor

Functions like `sum()`, `mean()`, and `max()` are **reductions**. They are the opposite of broadcasting. Instead of stretching dimensions, they crush them.

When you pass `dim=X` to a reduction, you are telling PyTorch: **"Crush and destroy dimension X."**

* `t.sum(dim=1)` on a shape `(Batch, Sequence)` crushes the Sequence dimension. The result is just `(Batch,)`.
* **The `keepdim=True` Lifesaver:** If you crush the Sequence dimension, your shape shifts to the left `(Batch,)`. If you try to do math with the original tensor now, broadcasting will right-align them incorrectly!
* Adding `keepdim=True` tells PyTorch to crush the data, but leave a `1` as a placeholder: `(Batch, 1)`. Now, broadcasting lines up perfectly. **This is the only reason `keepdim` exists.**

## 4. The Worked NLP Example: Masked Mean Pooling

**The Problem:** You have a sentence of word embeddings, and you want to average them into a single summary vector. But your sentence has "padding" (fake words added to make the batch a perfect rectangle).
If you simply use PyTorch's built-in `.mean(dim=1)`, PyTorch will average the padding into your data, completely ruining the math. (Imagine calculating a class test average, but counting empty desks as zeros!).

**The Solution:** You have to calculate the average manually: `Sum / Count`. We use a **Mask** (1 for real words, 0 for padding) to filter the data without writing a single, slow Python `for` loop.

Here is the 5-step breakdown of how the data actually changes at every line of code.

### The Dry Run (Step-by-Step Data)

Imagine a tiny sentence with **3 words**, where each word is a **2D vector**.

* **Word 1:** `[10, 20]` (Real)
* **Word 2:** `[30, 40]` (Real)
* **Word 3:** `[99, 99]` (Padding — we want to completely ignore this!)

**Starting Data:**

* `embeddings` shape `(1, 3, 2)`: `[ [[10,20], [30,40], [99,99]] ]`
* `mask` shape `(1, 3)`: `[ [1, 1, 0] ]`

---

**Step 1: Align the Mask (Unsqueeze)**
We need to multiply the embeddings by the mask, but `(1, 3)` cannot multiply with `(1, 3, 2)`. We must add a fake dimension to the mask so broadcasting works.

```python
mask_expanded = mask.unsqueeze(-1)  
# Shape becomes (1, 3, 1)
# Data: [ [[1], 
#          [1], 
#          [0]] ]

```

**Step 2: Destroy the Padding (Multiply)**
We multiply the embeddings by our expanded mask. Broadcasting stretches the `1`s and `0`s across the 2D vectors. The real words are kept, the padding is crushed to zeros.

```python
masked_embeddings = embeddings * mask_expanded
# Shape remains (1, 3, 2)
# Data: [ [10, 20] * 1 = [10, 20] 
#         [30, 40] * 1 = [30, 40]
#         [99, 99] * 0 = [ 0,  0] ]  <-- Padding neutralized!

```

**Step 3: Get the Total Sum**
We crush the sequence dimension (`dim=1`) to add all the words together.

```python
summed = masked_embeddings.sum(dim=1)
# Shape becomes (1, 2)
# Math: [10+30+0, 20+40+0]
# Data: [ [40, 60] ]

```

**Step 4: Count the Real Words**
We can't divide by 3 (the total sequence length), because there are only 2 real words. We sum the mask to find out exactly how many real words exist. We use `keepdim=True` so it doesn't lose its batch dimension!

```python
real_word_count = mask.sum(dim=1, keepdim=True)
# Shape becomes (1, 1)
# Math: 1 + 1 + 0 = 2
# Data: [ [2] ]

```

**Step 5: Calculate the True Average (Divide)**
We divide the summed embeddings by the real word count.

```python
final_average = summed / real_word_count
# Shape becomes (1, 2)
# Math: [40/2, 60/2]
# Data: [ [20, 30] ]  <-- Perfect average of just Word 1 and Word 2!

```

---

## Key Takeaways for Section 8

Align shapes from the right, stretch the 1s, and it's free. Fear accidental broadcasting more than crashes (`(n,)` vs `(n, 1)` is the classic bug). When you reduce, `dim` is the axis that gets destroyed. Use `keepdim=True` to leave a size-1 placeholder so your math doesn't break on the next line.

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
