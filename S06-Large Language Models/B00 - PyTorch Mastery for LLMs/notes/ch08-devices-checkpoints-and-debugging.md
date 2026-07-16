# Chapter 8: Devices, Checkpoints & Debugging

## Table of Contents

1. [The Survival Skills Chapter](#1-the-survival-skills-chapter)
2. [Device Management Patterns](#2-device-management-patterns)
3. [map_location: Loading a Checkpoint on the Wrong Machine](#3-map_location-loading-a-checkpoint-on-the-wrong-machine)
4. [state_dict Surgery: strict=False and Key Renaming](#4-state_dict-surgery-strictfalse-and-key-renaming)
5. [Reading a Shape-Error Traceback Like a Detective](#5-reading-a-shape-error-traceback-like-a-detective)
6. [NaN Hunting](#6-nan-hunting)
7. [Reproducibility: Seeds and Determinism](#7-reproducibility-seeds-and-determinism)
8. [GPU Memory Basics and OOM Anatomy](#8-gpu-memory-basics-and-oom-anatomy)
9. [Key Takeaways + Master Decision Table](#9-key-takeaways--master-decision-table)

---

# 1: The Survival Skills Chapter

Every chapter so far handed you a tool that works when everything is
cooperating: a tensor that reshapes cleanly, a model that trains, a
checkpoint that saves. This chapter is about the day one of those things
*doesn't* — the model you downloaded was trained on a different machine, the
checkpoint you're loading came from a slightly different architecture, a
shape error appears three function calls away from where you actually made
the mistake, or the loss quietly turns into `nan` on step 4,000 of an
overnight run.

None of this is exotic. It's the normal texture of real training work, and
it has a normal toolkit — you're about to learn all of it. Think of this
chapter as a mechanic's toolbox: you don't open it because something is
*definitely* broken, you open it because something *might* be, and you want
to find out fast instead of guessing.

---

# 2: Device Management Patterns

## The One Rule, Restated

Chapter 1 already gave you the core trap: `.to(device)` doesn't move a
tensor, it hands you a **photocopy** on the new device, and if you don't
save that photocopy to a variable the original stays exactly where it was.
This section is about doing that correctly at the *scale of a whole
training script*, not just one tensor.

## The Standard Pattern

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = model.to(device)                       # move ALL parameters + buffers, once

for inputs, targets in dataloader:
    inputs = inputs.to(device)                  # move EVERY batch, every iteration
    targets = targets.to(device)
    outputs = model(inputs)                      # now everyone's in the same room
```

Two habits keep this pattern from becoming a maintenance headache. First,
compute `device` **once**, at the top of the script, and never hardcode
`"cuda"` again — a script written this way runs unmodified on a CPU-only
laptop and an 8-GPU box. Second, **new tensors you create yourself** (a
mask, a positional table, anything not already living on a tensor from the
batch) need an explicit `device=` or a `*_like` call (chapter 1) — they
default to CPU regardless of where the model lives.

## Reading the Classic Error

```
RuntimeError: Expected all tensors to be on the same device, but found at
least two devices, cuda:0 and cpu!
```

Read this literally: *some* input to *this specific operation* is still on
CPU. The two usual suspects are a freshly created tensor (creation defaults
to CPU) and a batch you forgot to `.to(device)` inside the loop — the model
moved once at the top, but every new batch arrives fresh from the
`DataLoader`, on the CPU, every single time.

## Key Takeaways for Section 2

Move the model once; move every batch, every iteration. `.to(device)` never
mutates in place — always reassign. New tensors default to CPU unless told
otherwise.

*Next: what happens when the device you trained on isn't the device you're
loading on.*

---

# 3: map_location: Loading a Checkpoint on the Wrong Machine

## The Problem

A checkpoint file doesn't just contain numbers — each tensor inside it
remembers *which device it was saved from*. `torch.load(path)` tries to
restore tensors to that **same** device by default. Train on a GPU machine,
save a checkpoint, then try to load it on a laptop with no GPU, and:

```
RuntimeError: Attempting to deserialize object on a CUDA device but
torch.cuda.is_available() is False.
```

The checkpoint isn't corrupted — it's simply trying to reserve a GPU that
doesn't exist here.

## The Fix

`map_location` tells `torch.load` where to put every tensor **regardless of
where it was saved from** — a universal remapping instruction, not a
guess:

```python
checkpoint = torch.load("model_trained_on_gpu.pt", map_location="cpu")
# or, to load onto whatever device this script decides to use:
checkpoint = torch.load("model_trained_on_gpu.pt", map_location=device)
```

`map_location="cpu"` is the safe default for *any* checkpoint you didn't
just save yourself in the same process — it always works, and you can always
`.to(device)` the model afterward if you do have a GPU.

## Key Takeaways for Section 3

A checkpoint remembers its origin device; loading tries to recreate it.
`map_location` overrides that, and `"cpu"` is the universally safe choice
when you're not sure what hardware saved the file.

*Next: what happens when the checkpoint's contents don't match the model
you're loading it into.*

---

# 4: state_dict Surgery: strict=False and Key Renaming

## The Problem

`load_state_dict` is picky by default: every key in the checkpoint must
exist in the model, every key in the model must exist in the checkpoint, and
every matching tensor must be the exact same shape. This is the right
default — a silent partial load could leave half your model at its random
initialization without telling you. But it means any legitimate architecture
change breaks a plain load.

## Dry-Run: A Renamed Head

```
Old checkpoint has:         New model expects:
  encoder.weight               encoder.weight     ← name matches, loads fine
  encoder.bias                 encoder.bias       ← name matches, loads fine
  classifier.weight            regressor.weight   ← renamed! no match either way
  classifier.bias              regressor.bias     ← renamed!

new_model.load_state_dict(old_checkpoint, strict=True)
→ RuntimeError: Error(s) in loading state_dict for NewModel:
    Missing key(s) in state_dict: "regressor.weight", "regressor.bias".
    Unexpected key(s) in state_dict: "classifier.weight", "classifier.bias".
```

## The Two Repair Tools

**`strict=False`** relaxes the all-or-nothing rule: matching keys load
normally, and PyTorch hands back a small report of what it *couldn't*
match, instead of raising.

```python
result = new_model.load_state_dict(old_checkpoint, strict=False)
print(result)
# _IncompatibleKeys(missing_keys=['regressor.weight', 'regressor.bias'],
#                    unexpected_keys=['classifier.weight', 'classifier.bias'])
```

`result.missing_keys` are parameters that stayed at their fresh
initialization (in this example: `regressor`, which never got trained
weights — this is expected here, since it's a genuinely new head, but check
this list every time). `result.unexpected_keys` are checkpoint tensors that
had nowhere to go and were silently dropped.

**Key renaming** fixes the actual mismatch — a dictionary comprehension
over `state_dict()` before loading, when you *know* the correspondence:

```python
old_state = torch.load("old_checkpoint.pt", map_location="cpu")
renamed = {key.replace("classifier.", "regressor."): value
           for key, value in old_state.items()}
new_model.load_state_dict(renamed)          # now strict=True can succeed
```

## The Error That strict=False Cannot Fix

A shape mismatch on a **matching name** is a different problem entirely, and
`strict=False` does not help:

```
Error(s) in loading state_dict for ShapeMismatch:
  size mismatch for encoder.weight: copying a param with shape
  torch.Size([4, 4]) from checkpoint, the shape in current model is
  torch.Size([8, 4]).
```

This means the architecture itself changed (a layer got wider or narrower) —
the fix is architectural, not a loading flag. You cannot pour a `(4,4)`
tensor into an `(8,4)` slot no matter how you ask.

## Decision Guide

| Symptom | Tool | Why |
|---|---|---|
| Checkpoint has extra/missing keys, matching ones fine | `strict=False` | loads what matches, reports the rest |
| Keys mismatch by a known renaming | key-renaming dict comprehension, then load | fixes the actual mismatch |
| Same key name, different shape | neither — fix the architecture | shapes must match; no flag overrides this |

## Key Takeaways for Section 4

`load_state_dict` is strict by default for good reason. `strict=False`
reports mismatches instead of raising; renaming keys fixes a known
correspondence; a shape mismatch on a matching name is an architecture
problem no loading flag can paper over.

*Next: the error message that shows up when nothing about checkpoints is
even involved.*

---

# 5: Reading a Shape-Error Traceback Like a Detective

## The Method

A shape error's traceback is a *crime scene*, and the exception message is
the only witness. The method that works every time: **read the message for
the two shapes involved, then walk backward through the traceback to find
the line that produced the *wrong* one** — the crash site is rarely the
crime scene.

```
RuntimeError: mat1 and mat2 shapes cannot be multiplied (32x768 and 512x256)
```

Break this down like reading a witness statement: `mat1` is `(32, 768)`,
`mat2` is `(512, 256)` — a matmul needs the *inner* dimensions to match
(chapter 2), and `768 ≠ 512`. The question is never "why did the matmul
fail" (you already know: mismatched inner dims) — it's **"which of these two
numbers is the impostor, and where did it come from?"** If the model's
hidden size is meant to be `512` everywhere, then `768` is the intruder —
now go look at whatever produced that `32x768` tensor a few lines up:
a wrong `Linear` output size, a `view` that merged the wrong dimensions, an
`nn.Embedding` with the wrong `embedding_dim`.

## The Habit: Print Shapes at Every Suspect Line

Rather than staring at the traceback, the fast path is almost always to
insert `print(tensor.shape)` (or set a debugger breakpoint) right before the
line the traceback names, and one or two calls upstream of it. Chapter 1's
lesson pays off directly here: if you've been naming dimensions in comments
the whole way through (`# (batch, seq, d_model)`), a shape error is just a
place where the comment and the printed shape disagree — and that disagreement
tells you exactly which upstream line lied.

## Key Takeaways for Section 5

The error names the two shapes in conflict — that's the "what," not the
"where." Walk backward from the crash site to find which tensor's *actual*
shape betrays its *intended* shape, using the shape comments you've been
writing since chapter 1.

*Next: an error message you won't get — because nothing crashes at all.*

---

# 6: NaN Hunting

## Why This Is Harder Than a Shape Error

A shape error is a loud, immediate failure. A `NaN` is the opposite: it can
be born on step 4,000, silently propagate through every downstream
computation (anything touching a `NaN` becomes `NaN`), and the training loop
keeps running — printing `nan` as the loss, updating every weight to `nan`,
for hours, if nobody's watching.

## Where NaNs Are Actually Born

Three repeat offenders, all things you've already met:

**`log(0)`.** Any loss with a `log` inside it (cross-entropy is one, written
out) hits `-inf`, and the *gradient* of `log` at 0 is `1/0 = inf` — the very
first backward pass after a probability collapses to exactly 0 produces an
`inf`, and one arithmetic step later, an `inf` minus an `inf` is `nan`.

**An all-`-inf` row before softmax (chapter 2's exact trap).** If every
position in a row is masked to $-\infty$ (a sequence that's entirely
padding, or an off-by-one mask bug), softmax's denominator is
$\sum e^{-\infty} = 0$, and $\frac{0}{0} = \text{nan}$:

```
scores = [[1.0, 2.0], [-inf, -inf]]        # row 1: everything masked
softmax(scores, dim=-1)
→ tensor([[0.2689, 0.7311],
          [   nan,    nan]])                row 1 is nan, row 0 is fine
```

**A learning rate that's simply too large.** An update that overshoots
catastrophically can push a weight to a value large enough that its next
forward pass produces `inf`, and `inf * 0` or `inf - inf` downstream becomes
`nan`.

## The Tools

**Cheap and constant: check every loss.**

```python
if not torch.isfinite(loss):
    print(f"non-finite loss at step {step}: {loss.item()}")
    break                        # stop before you save 50 nan checkpoints
```

**Precise: `torch.autograd.detect_anomaly()`.** Wrapping the training step
in this context manager makes PyTorch check every backward operation's
*output* for `NaN`/`inf`, and raise **immediately at the operation that
produced it** — not three layers downstream where you'd otherwise notice:

```python
with torch.autograd.detect_anomaly():
    loss.backward()
# RuntimeError: Function 'SoftmaxBackward0' returned nan values in its 0th output.
```

That message names the exact op — in this example, confirming the all-masked
softmax row theory directly, instead of you guessing. It runs noticeably
slower, so it's a debugging tool you switch on, not a permanent fixture of
every training run.

## Decision Guide

| Symptom | First suspect | Check |
|---|---|---|
| NaN appears very early (first few steps) | learning rate too high, or bad init | try a smaller `lr`; re-check chapter 4's init |
| NaN appears after a specific batch, reproducibly | a mask/data issue in that batch | look for all-padding sequences, `log(0)` targets |
| NaN appears late, irregularly | gradual weight blow-up | add `clip_grad_norm_` (ch07); check for missing `no_grad` in eval |
| Need to find the exact operation | `torch.autograd.detect_anomaly()` | names the backward function that produced it |

## Key Takeaways for Section 6

NaNs are silent and self-propagating — check `torch.isfinite(loss)` every
step, cheaply, always. `detect_anomaly()` is the expensive-but-precise tool
that names the exact culprit operation when a cheap check isn't enough.

*Next: making sure a bug, once found and fixed, stays fixed the same way
every time you check.*

---

# 7: Reproducibility: Seeds and Determinism

## The Layers of Randomness

`torch.manual_seed(42)` (used at the top of every notebook in this track)
seeds PyTorch's own random number generator — `torch.randn`, `nn.Linear`'s
default init, `nn.Dropout`'s mask, all become reproducible. But a real
pipeline has *other* sources of randomness that a single seed call doesn't
touch: Python's own `random` module, NumPy's generator (chapter 1's
`from_numpy` boundary), and — chapter 6's gotcha — **each DataLoader worker
gets its own process and its own default seed**, so randomness generated
*inside* `__getitem__` can silently repeat across workers unless you seed
each worker explicitly via `worker_init_fn`.

## The Full Recipe

```python
import random
import numpy as np
import torch

def set_all_seeds(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)        # no-op safely if no GPU present
```

## The Speed Trade-Off

`torch.use_deterministic_algorithms(True)` goes one step further: it forces
even GPU operations that normally have several valid low-level
implementations (which can each round floating-point results slightly
differently) to always pick the same one. This buys bit-for-bit
reproducibility between runs — genuinely useful when debugging "why did
this run diverge from that one" — at a real performance cost, because the
deterministic implementation isn't always the fastest one. Leave it off for
normal training; turn it on when you're specifically hunting a
reproducibility bug.

## Key Takeaways for Section 7

One seed call covers PyTorch; Python's `random`, NumPy, and DataLoader
workers each need their own. Full determinism is available but costs speed
— reach for it only while debugging, not by default.

*Next: the resource everything in this chapter has been quietly competing
for.*

---

# 8: GPU Memory Basics and OOM Anatomy

## What's Actually on the GPU

Four things compete for GPU memory during training, and only one of them is
obvious: the **model weights** (fixed size, one copy), the **optimizer
state** (Adam holds two extra tensors — $m_t$ and $v_t$ — the same size as
every parameter, so Adam alone roughly *triples* memory versus the weights
alone), the **gradients** (one more copy, same size as the weights, filled
in by `backward()`), and the **activations** — every intermediate tensor
chapter 3 showed the graph keeping alive until backward runs, and for a deep
model with a long sequence, this is very often the *largest* of the four.

## Reading the Numbers

```python
torch.cuda.memory_allocated()      # bytes actually holding live tensors right now
torch.cuda.memory_reserved()       # bytes PyTorch's allocator has claimed from the OS
                                    # (reserved >= allocated; the gap is a re-usable pool)
torch.cuda.max_memory_allocated()  # the high-water mark since the process started
```

The gap between `memory_allocated` and `memory_reserved` is not a leak —
PyTorch's allocator deliberately keeps freed memory in a pool to hand back
out quickly next time, rather than returning it to the OS and paying
allocation overhead again on the very next batch.

## Reading an OOM Message

```
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB (GPU 0; 23.99
GiB total capacity; 20.1 GiB already allocated; ...)
```

This is arithmetic, not mystery: `already allocated` + the new `Tried to
allocate` amount exceeds `total capacity`. The fix is always one of the same
handful of levers, roughly in order of how much they cost you: shrink the
batch size (fewer activations at once), use gradient accumulation (chapter 7
— same effective batch size, a fraction of the peak activation memory), use
bf16 `autocast` (chapter 7 — half the bytes per activation), or, if
available, **gradient checkpointing** (recompute activations during backward
instead of storing them — a pure memory-for-compute trade, beyond this
track's scope but worth knowing the name of).

## The Myth of `del` and `torch.cuda.empty_cache()`

`del tensor` removes a Python reference; the memory is only actually freed
once *no* references remain and Python garbage-collects it — usually
immediate for a simple case, not guaranteed in general.
`torch.cuda.empty_cache()` returns the *unused, reserved* pool back to the
OS — it does **not** free anything currently in use, and it does not make
more memory available for your *own* process's next allocation (that memory
was already available from the pool). Neither is a fix for a model that
genuinely doesn't fit; they're for cases where you want to hand memory back
to other processes sharing the GPU, or for debugging what's actually
allocated right now.

## Key Takeaways for Section 8

Weights + gradients + optimizer state (Adam: ×2 more) + activations, and
activations are often the biggest of the four. An OOM message is arithmetic
you can read directly. `del`/`empty_cache()` manage the *pool*, not a fix for
insufficient memory — accumulation, bf16, smaller batches, or gradient
checkpointing actually reduce the peak.

---

# 9: Key Takeaways + Master Decision Table

This chapter's tools share one theme: **read the exact message, then reason
backward to the cause** — a shape error, a device mismatch, an OOM, and a
`state_dict` key error are all, underneath, the same kind of puzzle.

| Symptom | Tool | Why |
|---|---|---|
| "tensors on different devices" | check every fresh tensor's `device=` | new tensors default to CPU |
| Checkpoint won't load, wrong device | `torch.load(path, map_location="cpu")` | overrides the checkpoint's saved origin device |
| Checkpoint has renamed/missing/extra keys | `load_state_dict(..., strict=False)`, inspect the report | matches what it can, tells you the rest |
| Same key, different shape | fix the architecture | no loading flag overrides a real shape mismatch |
| "shapes cannot be multiplied" / similar | read both shapes, walk back to find the impostor | the crash site ≠ the cause site |
| Loss becomes `nan` | check `torch.isfinite(loss)` every step | cheap, catches it immediately |
| Need to find which op produced a NaN | `torch.autograd.detect_anomaly()` | names the exact backward function |
| A run won't reproduce | seed `random`, `numpy`, `torch`, **and** DataLoader workers | one seed call doesn't cover all of them |
| Need bit-for-bit determinism | `torch.use_deterministic_algorithms(True)` | costs speed; debugging tool, not a default |
| Out of GPU memory | shrink batch, accumulate, bf16 autocast, gradient checkpointing | in order of cost; `del`/`empty_cache` don't create memory |

**Connection forward:** every decision guide from chapters 1–8 is now in
your hands. Chapter 9's capstone assembles them into one small, real
project — a text classifier built from a blank file, with one deliberately
planted bug for you to find using exactly the tools this chapter just gave
you.
