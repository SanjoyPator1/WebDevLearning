# Chapter 6: Text Data Pipeline

## Table of Contents

1. [Why the Data Pipeline Is Its Own Skill](#1-why-the-data-pipeline-is-its-own-skill)
2. [Dataset: Map-Style vs Iterable](#2-dataset-map-style-vs-iterable)
3. [DataLoader: The Batch Factory](#3-dataloader-the-batch-factory)
4. [Why the Default Collate Crashes on Text](#4-why-the-default-collate-crashes-on-text)
5. [collate_fn: Padding a Variable-Length Batch](#5-collate_fn-padding-a-variable-length-batch)
6. [Building the Attention Mask](#6-building-the-attention-mask)
7. [Shuffling, Sampling, and drop_last](#7-shuffling-sampling-and-drop_last)
8. [Performance Knobs: num_workers and pin_memory](#8-performance-knobs-num_workers-and-pin_memory)
9. [Key Takeaways + Master Decision Table](#9-key-takeaways--master-decision-table)

---

# 1: Why the Data Pipeline Is Its Own Skill

## What This Chapter Is Really About

The previous chapters built the *model* side of PyTorch — tensors, ops,
autograd, modules, layers, losses. But a model is useless until something
feeds it batches. And text is the hardest thing to batch, for one stubborn
reason: **sentences have different lengths, but a tensor is a rectangle**.

Every LLM training loop hides the same three-stage pipeline: a **Dataset**
that knows how to produce one example, a **DataLoader** that groups examples
into batches and parallelizes the loading, and a **collate function** that
solves the ragged-rectangle problem by padding. Chapter 5's exercise 8
consumed a padded batch with an `ignore_index` loss; *this* chapter is where
that padded batch is born.

The thesis: the pipeline is a clean separation of concerns. Dataset = "how do
I get example *i*?" DataLoader = "how do I group, shuffle, and parallelize?"
collate_fn = "how do I turn a list of ragged examples into rectangular
tensors?" Get the boundaries right and the whole thing composes; blur them
and you get the silent bugs this chapter teaches you to avoid.

---

# 2: Dataset: Map-Style vs Iterable

## The Two Kinds

PyTorch has two `Dataset` base classes, and the choice is about **whether your
data has a known length and supports random access**.

A **map-style dataset** (`torch.utils.data.Dataset`) implements `__len__` and
`__getitem__(index)`. It is a *map* from an integer index to an example —
random access, known size. This is what you want 95% of the time: a CSV of
labeled sentences, a folder of files, anything that fits the "give me example
#37" model.

An **iterable dataset** (`torch.utils.data.IterableDataset`) implements
`__iter__` and yields examples one at a time, like a Python generator. No
length, no random access — for **streams**: reading a 500 GB text file line
by line, consuming a Kafka topic, anything too big to index or of unknown
size.

## Dry-Run: A Map-Style Text Dataset

```
class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer):
        self.texts, self.labels, self.tokenizer = texts, labels, tokenizer

    def __len__(self):
        return len(self.texts)                       # DataLoader needs this to plan batches

    def __getitem__(self, index):
        token_ids = self.tokenizer(self.texts[index])    # ONE example: a 1-D LongTensor
        return torch.tensor(token_ids), self.labels[index]

ds[0] → (tensor([5, 12, 7]),      0)     # example 0: 3 tokens, label 0
ds[1] → (tensor([3, 9]),          1)     # example 1: 2 tokens, label 1  ← different length!
```

Notice `__getitem__` returns **one example, un-padded, un-batched**. That is
deliberate: a Dataset never knows about batches or padding. It answers exactly
one question — "what is example *i*?" — and hands off. Its examples are ragged
by nature, and that raggedness is somebody else's problem (section 5).

## Decision Guide: Which Dataset

| Situation | Use | Why |
|---|---|---|
| Data fits in memory / on disk with an index (CSV, file list) | map-style `Dataset` | random access + shuffling + known length |
| A stream of unknown or unbounded size | `IterableDataset` | no `__len__`, no random access needed |
| You want DataLoader to shuffle for you | map-style | shuffling needs random access by index |
| Reading a huge file line-by-line, or a live feed | `IterableDataset` | you can't index a stream |

## Key Takeaways for Section 2

Map-style = `__len__` + `__getitem__`, random access, the default choice.
Iterable = `__iter__`, streaming, no length. `__getitem__` returns **one raw,
un-padded example** — batching and padding happen downstream.

*Next: the machine that turns single examples into batches.*

---

# 3: DataLoader: The Batch Factory

## What It Does

The `DataLoader` wraps a `Dataset` and turns it into an iterable of
**batches**. On each step it (1) decides which indices go in the next batch
(the *sampler*), (2) fetches those examples by calling
`dataset[i]`, (3) hands the list of examples to a **collate function** that
stacks them into batched tensors, and optionally (4) does all of this in
parallel worker processes.

```
DataLoader(dataset, batch_size=32, shuffle=True, collate_fn=my_collate,
           num_workers=4, pin_memory=True, drop_last=False)

for batch in loader:            # each iteration:
    ...                         #  sampler → [i1, i2, ..., i32]
                                #  fetch   → [dataset[i1], ..., dataset[i32]]
                                #  collate → one batched tensor (or tuple)
```

## The Anatomy

The arguments split into three jobs, which map onto the next three sections:

- **What's in a batch** — `batch_size`, `collate_fn` (sections 4–6)
- **Which examples, in what order** — `shuffle`, `sampler`, `drop_last`
  (section 7)
- **How fast** — `num_workers`, `pin_memory` (section 8)

The single most important thing to understand: the DataLoader **calls
`collate_fn` on a Python list of whatever `__getitem__` returned**. If
`__getitem__` returns `(tensor, label)`, then `collate_fn` receives a list of
`(tensor, label)` tuples. Everything about text batching lives in that one
hand-off.

## Key Takeaways for Section 3

DataLoader = sampler (pick indices) → fetch (`dataset[i]`) → collate (stack
into a batch), optionally parallelized. It passes a *list of examples* to
`collate_fn`. The rest of this chapter is the three jobs its arguments do.

*Next: what happens when you let it collate text with the default.*

---

# 4: Why the Default Collate Crashes on Text

## The Problem It Solves

If you don't pass a `collate_fn`, the DataLoader uses `default_collate`, whose
core move is `torch.stack` — glue the examples along a new batch dimension.
`torch.stack` demands **identical shapes** (chapter 2). For images resized to
224×224 that's fine. For sentences, it is an immediate crash.

## Dry-Run: The Crash

```
batch of three tokenized sentences (from __getitem__):
  [ tensor([1, 2, 3]),       length 3
    tensor([4, 5]),          length 2
    tensor([6, 7, 8, 9]) ]   length 4

default_collate → torch.stack([...])
→ RuntimeError: stack expects each tensor to be equal size, but got [3] at
  entry 0 and [2] at entry 1
```

This crash is *good news* — it fails loudly, right at the boundary, pointing
exactly at the fix. (Contrast the silent bugs of earlier chapters.) The fix
is to supply your own `collate_fn` that pads before stacking.

## Key Takeaways for Section 4

The default collate is `torch.stack`, which requires equal shapes. Ragged text
crashes it immediately and loudly. The cure is a custom `collate_fn`.

*Next: writing that function.*

---

# 5: collate_fn: Padding a Variable-Length Batch

## The Intuition

A `collate_fn` is just a function `list_of_examples → batched_tensors`. For
text, its job is to find the longest sequence in *this* batch and pad every
shorter one up to that length with a `PAD_ID`, producing a rectangle.

**The critical design choice: pad per-batch, not globally.** If you padded
every sequence to the dataset's global maximum length (say 512) inside
`__getitem__`, a batch of all-short sentences would waste enormous compute on
padding. Padding inside `collate_fn` means each batch is only as wide as *its
own* longest member — this is **dynamic padding**, and it's why collation is
the right home for it: it's the first place that sees a whole batch at once.

## The Tool

`torch.nn.utils.rnn.pad_sequence` does the padding. With
`batch_first=True` it produces `(batch, max_len)`; the `padding_value` fills
the gaps.

## Dry-Run with Tiny Numbers

```
examples = [ tensor([1, 2, 3]), tensor([4, 5]), tensor([6, 7, 8, 9]) ]
PAD_ID = 0

max_len in THIS batch = 4

pad_sequence(examples, batch_first=True, padding_value=0):
  [[1, 2, 3, 0],       ← padded with one 0
   [4, 5, 0, 0],       ← padded with two 0s
   [6, 7, 8, 9]]       ← the longest, untouched
  shape (3, 4)                                    a rectangle at last ✓
```

A complete text `collate_fn` also carries the labels and the true lengths
through:

```
def collate_batch(examples):                 # examples: list of (token_ids, label)
    sequences = [tokens for tokens, _ in examples]
    labels    = torch.tensor([label for _, label in examples])
    lengths   = torch.tensor([len(s) for s in sequences])   # BEFORE padding — for masks
    padded    = pad_sequence(sequences, batch_first=True, padding_value=PAD_ID)
    return padded, labels, lengths            # (B, max_len), (B,), (B,)
```

Capturing `lengths` *before* padding is the small discipline that makes the
next section — masks — trivial.

## Key Takeaways for Section 5

`collate_fn: list → batch`. Pad per-batch (dynamic padding) with
`pad_sequence(..., batch_first=True)` so batches are only as wide as their own
longest member. Record true lengths before padding.

*Next: telling the model which of those positions are real.*

---

# 6: Building the Attention Mask

## The Problem It Solves

Padding created fake tokens. The model must ignore them — in attention
(chapter 2's `masked_fill`), in pooling (chapter 1's masked mean), and in the
loss (chapter 5's `ignore_index`). The **attention mask** is the boolean
record of which positions are real, and it is built right after padding, in
the same `collate_fn`.

## Two Equivalent Constructions

**From the pad value:** any position not equal to `PAD_ID` is real.

$$\text{mask}[b, t] = \big(\text{padded}[b, t] \neq \text{PAD\_ID}\big)$$

**From the lengths** (safer if `PAD_ID` could be a legitimate token): position
$t$ in row $b$ is real iff $t < \text{length}[b]$.

$$\text{mask}[b, t] = \big(t < \text{length}[b]\big)$$

## Dry-Run with Tiny Numbers

```
padded  = [[1, 2, 3, 0],       lengths = [3, 2, 4]      PAD_ID = 0
           [4, 5, 0, 0],
           [6, 7, 8, 9]]

Construction 1 — (padded != 0):
  [[T, T, T, F],
   [T, T, F, F],
   [T, T, T, T]]

Construction 2 — arange(4)[None, :] < lengths[:, None]:
  arange     = [0, 1, 2, 3]
  lengths    = [[3],[2],[4]]              (unsqueezed to (3,1) — ch01 broadcasting!)
  0<3,1<3,2<3,3<3 → [T,T,T,F]
  0<2,1<2,2<2,3<2 → [T,T,F,F]
  0<4,1<4,2<4,3<4 → [T,T,T,T]            identical ✓
```

The mask flows straight into everything downstream: `~mask` marks the
positions `masked_fill` should set to $-\infty$ before attention softmax, and
`lengths` (or `mask.sum(dim=1)`) is the denominator for masked mean pooling.
The whole toolbox connects here.

## Key Takeaways for Section 6

The attention mask (built in `collate_fn`) records real vs pad positions,
either as `padded != PAD_ID` or `arange(L) < lengths[:, None]`. It feeds
attention masking, pooling, and the loss — the pipeline hands the model
exactly what chapters 1, 2, and 5 need.

*Next: the order and grouping of examples.*

---

# 7: Shuffling, Sampling, and drop_last

## Shuffling and Samplers

`shuffle=True` reshuffles the example order every epoch — essential for
training (it decorrelates consecutive gradients) and pointless for
validation. Under the hood, `shuffle=True` just installs a `RandomSampler`;
`shuffle=False` a `SequentialSampler`. For finer control you pass a
`sampler=` directly:

- a **`WeightedRandomSampler`** oversamples rare classes to fight imbalance
  (an alternative to chapter 5's `weight=` loss argument — you rebalance the
  *data* instead of the *loss*);
- a **length-based batch sampler** groups similarly-lengthed sequences into
  the same batch so there is little padding to waste compute on (**length
  bucketing**).

*You cannot combine `shuffle=True` with a custom `sampler` — the sampler
already decides order. It's one or the other.*

## drop_last

`drop_last=True` discards the final short batch when the dataset size isn't a
multiple of `batch_size`.

## Dry-Run

```
dataset of 10 examples, batch_size = 4

drop_last=False → batches of size [4, 4, 2]     keep the ragged tail
drop_last=True  → batches of size [4, 4]         drop it
```

When does the tail matter? Drop it when a partial batch would break something
size-dependent (BatchNorm on a batch of 1 misbehaves; some fused kernels
assume a fixed batch). Keep it (the default) when every example counts — which
is almost always true for evaluation, where dropping examples silently
corrupts your metric.

## Decision Guide

| Situation | Setting |
|---|---|
| Training order | `shuffle=True` |
| Validation / test order | `shuffle=False` |
| Class imbalance, rebalance the data | `sampler=WeightedRandomSampler(...)` |
| Minimize padding waste | length-bucketed batch sampler |
| A partial last batch would break a layer | `drop_last=True` |
| Every example must count (eval!) | `drop_last=False` |

## Key Takeaways for Section 7

`shuffle=True` for training only; it's a `RandomSampler` under the hood.
Custom samplers handle imbalance (weighted) and padding waste (length
bucketing) — but exclude `shuffle`. `drop_last` trades the ragged tail for
uniform batch sizes; never drop during eval.

*Next: making it fast.*

---

# 8: Performance Knobs: num_workers and pin_memory

## num_workers

By default (`num_workers=0`) data loading runs in the **main process**,
serially, *between* training steps — so your expensive GPU sits idle while the
CPU tokenizes the next batch. `num_workers=N` spawns N subprocesses that
prepare batches **in parallel, ahead of time**, so a batch is ready the moment
the GPU wants it. For tokenization-heavy text pipelines this is often the
single biggest speedup.

The cost: each worker is a separate process with startup overhead and its own
memory. Too many workers thrash the CPU and can *slow things down*. A common
starting point is "number of CPU cores," tuned by measuring.

*A worker gotcha worth knowing now (chapter 8 revisits it): each worker gets
its own copy of the dataset and its own RNG seed, so careless randomness
inside `__getitem__` can duplicate across workers — seed with
`torch.utils.data.get_worker_info()` if you generate randomness there.*

## pin_memory

`pin_memory=True` allocates each batch in **page-locked** host memory, which
makes the CPU→GPU transfer faster and allows it to overlap with computation
(via `.to(device, non_blocking=True)`). It only helps when you're actually
moving data to a GPU — pure CPU training gains nothing.

## Decision Guide

| Situation | Setting | Why |
|---|---|---|
| GPU training, CPU-heavy loading (tokenizing) | `num_workers > 0` | parallel prefetch keeps the GPU fed |
| Quick debugging / tiny data | `num_workers=0` | simpler tracebacks, no process overhead |
| Any GPU training | `pin_memory=True` | faster, overlappable host→device copy |
| CPU-only training | `pin_memory=False` | nothing to transfer |
| Workers slow to start each epoch | `persistent_workers=True` | keep them alive between epochs |

## Key Takeaways for Section 8

`num_workers>0` prefetches batches in parallel so the GPU never waits — the
top speedup for text. `pin_memory=True` speeds the host→GPU copy (GPU only).
Both are pure performance; they never change *what* a batch contains.

---

# 9: Key Takeaways + Master Decision Table

The pipeline is three separated concerns: **Dataset** produces one raw
example, **DataLoader** groups and parallelizes, **collate_fn** turns ragged
examples into padded rectangles plus a mask. Keep those boundaries clean and
text batching stops being scary.

| I want to... | Reach for | Why |
|---|---|---|
| Serve indexable, in-memory data | map-style `Dataset` (`__len__`+`__getitem__`) | random access, shuffling |
| Stream huge/unbounded data | `IterableDataset` (`__iter__`) | no length, no random access |
| Return one example | un-padded tensor(s) from `__getitem__` | Dataset knows nothing of batches |
| Batch variable-length text | custom `collate_fn` + `pad_sequence` | default collate crashes on ragged |
| Waste minimal compute on padding | pad per-batch (dynamic padding) | batch only as wide as its longest |
| Tell the model which tokens are real | attention mask in `collate_fn` | feeds attention/pooling/loss |
| Randomize training order | `shuffle=True` | decorrelates gradients |
| Keep eval order fixed & complete | `shuffle=False`, `drop_last=False` | reproducible, no dropped examples |
| Fight class imbalance via data | `WeightedRandomSampler` | rebalance data instead of loss |
| Minimize padding across a batch | length-bucketed sampler | similar lengths together |
| Keep the GPU fed | `num_workers>0` | parallel batch prefetch |
| Speed up host→GPU copies | `pin_memory=True` | page-locked transfer, GPU only |

**Connection forward:** the pipeline now emits exactly the batches a model
consumes — padded token IDs, labels, and a mask. Chapter 7 assembles the
final piece: the training loop that pulls these batches, runs the
forward/backward/step dance in the right order, and drives everything you've
built across chapters 1–6.
