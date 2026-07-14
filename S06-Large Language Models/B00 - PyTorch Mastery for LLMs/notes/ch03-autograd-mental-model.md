# Chapter 3: The Autograd Mental Model

## Table of Contents

1. [What backward() Actually Does](#1-what-backward-actually-does)
2. [Backward Mechanics: A Dry-Run You Can Check by Hand](#2-backward-mechanics-a-dry-run-you-can-check-by-hand)
3. [Accumulation Is the Default](#3-accumulation-is-the-default)
4. [The Four Ways to Stop Gradients](#4-the-four-ways-to-stop-gradients)
5. [In-Place Operations and the Errors They Cause](#5-in-place-operations-and-the-errors-they-cause)
6. [Autograd and Memory](#6-autograd-and-memory)
7. [Key Takeaways + Master Decision Table](#7-key-takeaways--master-decision-table)

---

# 1: What backward() Actually Does

## What This Chapter Is Really About

`.backward()` is the most-called line in deep learning and the easiest to
treat as magic. The goal of
this chapter is that you can **predict** — before running anything — what
`.grad` will contain, which tensors will have one at all, why a given
RuntimeError fired, and where your GPU memory went. All of it follows from
one idea:

**While your forward pass runs, autograd is quietly recording a graph of
every operation.** `.backward()` walks that recording in reverse, applying
the chain rule at each node.

## The Cast of Characters

A **leaf tensor** is one *you* created (not the result of an op): parameters,
inputs, constants. A **non-leaf** is any op result. Every non-leaf carries a
**`grad_fn`** — the recipe for its backward step (`MulBackward0`,
`AddBackward0`, ...). Leaves have `grad_fn=None`; they are where the
recording *stops* and where gradients finally land.

The recording only happens for tensors with **`requires_grad=True`** (and
anything computed from them — the flag is infectious). After `backward()`,
gradients appear in **`.grad`** — but *only on leaves that require grad*.
Intermediate tensors get their gradients computed and then immediately
discarded (call `intermediate.retain_grad()` before backward if you want to
inspect one).

## The Graph, Drawn

For `loss = ((x @ w + b) ** 2).mean()`:

```
  x (leaf,           w (leaf,              b (leaf,
  requires_grad=F)   requires_grad=T)      requires_grad=T)
       │                  │                     │
       └───────┬──────────┘                     │
               ▼                                │
        [MmBackward]    x @ w                   │
               └───────────┬────────────────────┘
                           ▼
                    [AddBackward]    x @ w + b
                           │
                           ▼
                    [PowBackward]    (...)**2
                           │
                           ▼
                    [MeanBackward]
                           │
                           ▼
                         loss        (non-leaf; loss.grad_fn = MeanBackward)

backward() starts at loss, walks UP the arrows, multiplying local
derivatives (chain rule), and deposits results into w.grad and b.grad.
```

The graph is **dynamic**: it is rebuilt from scratch on every forward pass,
which is why Python `if`/`for` work naturally inside models — autograd only
ever sees the ops that actually ran *this* time.

## Key Takeaways for Section 1

Forward = compute *and record*. `backward()` = replay the recording in
reverse with the chain rule. Gradients land only in `.grad` of
requires-grad **leaves**. `grad_fn` is the breadcrumb trail; a tensor with
`grad_fn=None` is a leaf.

*Next: proving to yourself the numbers are exactly the chain rule.*

---

# 2: Backward Mechanics: A Dry-Run You Can Check by Hand

## The Scalar Convention

`loss.backward()` with no arguments only works when `loss` is a **scalar**.
That is not a technicality: "the gradient of a vector output" isn't a single
gradient — it's a Jacobian matrix. Calling `y.backward(v)` on a vector `y`
computes the *vector-Jacobian product* $v^\top J$ — which is why training
losses are always reduced (`.mean()` / `.sum()`) to a scalar first. In
practice: reduce, then backward.

## The Math

One data point of linear regression, the smallest model that has everything:

$$\hat{y} = w \cdot x + b, \qquad \mathcal{L} = (\hat{y} - y)^2$$

Every symbol: $x$ is the input, $y$ the true target, $w$ and $b$ the
parameters we want gradients for, $\hat{y}$ the prediction, $\mathcal{L}$ the
squared-error loss. The chain rule gives:

$$\frac{\partial \mathcal{L}}{\partial w} = \underbrace{2(\hat{y} - y)}_{\partial \mathcal{L} / \partial \hat{y}} \cdot \underbrace{x}_{\partial \hat{y} / \partial w}, \qquad \frac{\partial \mathcal{L}}{\partial b} = 2(\hat{y} - y) \cdot 1$$

## Dry-Run with Tiny Numbers

```
Given: x = 2.0,  y_true = 7.0,  w = 1.5,  b = 0.5

Forward:
  y_pred = w·x + b = 1.5·2.0 + 0.5 = 3.5
  error  = y_pred − y_true = 3.5 − 7.0 = −3.5
  loss   = error² = 12.25

Backward (chain rule, by hand):
  ∂loss/∂y_pred = 2·error = 2·(−3.5) = −7.0
  ∂loss/∂w = ∂loss/∂y_pred · ∂y_pred/∂w = −7.0 · x = −7.0 · 2.0 = −14.0
  ∂loss/∂b = ∂loss/∂y_pred · ∂y_pred/∂b = −7.0 · 1   =  −7.0

PyTorch:
  w = torch.tensor(1.5, requires_grad=True)
  b = torch.tensor(0.5, requires_grad=True)
  loss = (w * 2.0 + 0.5... ).backward()
  w.grad → tensor(-14.)     b.grad → tensor(-7.)     identical ✓
```

The signs even tell the story: the prediction (3.5) is *below* the target
(7.0), so the gradients are negative — "increase $w$ and $b$" — and gradient
*descent* subtracts them, moving the prediction up. When you can narrate the
sign of a gradient, you own this.

## Key Takeaways for Section 2

Reduce to a scalar, then `backward()`. What lands in `.grad` is exactly the
chain rule you'd compute by hand — verify once on paper and you'll trust it
forever. Intermediates need `retain_grad()` to keep theirs.

*Next: the design decision in autograd that is both a famous bug and a
famous feature.*

---

# 3: Accumulation Is the Default

## The Behavior

`backward()` does not *set* `.grad` — it **adds to it**:

```
w = torch.tensor(2.0, requires_grad=True)

loss = w * w ;  loss.backward()      # dloss/dw = 2w = 4
w.grad → 4.0

loss = w * w ;  loss.backward()      # same computation again
w.grad → 8.0        ← accumulated, not replaced!
```

Why design it this way? Because summing is exactly what multi-part losses and
multi-batch accumulation need — and PyTorch chose the primitive that
composes, leaving the clearing to you.

## The Bug Face: Forgetting zero_grad

A training loop without `optimizer.zero_grad()` never crashes. Each step's
gradient is added to a growing pile of stale ones; the effective update
direction is a decaying average of every gradient ever computed. Loss curves
wobble, learning slows, nothing obviously points at the cause. The modern
call is `optimizer.zero_grad(set_to_none=True)` (the default since PyTorch
2.0) — it sets `.grad = None` rather than filling with zeros, which skips a
memory write and lets the next backward allocate fresh.

## The Feature Face: Gradient Accumulation

When the batch you *want* (say 32) doesn't fit in memory, run 4 micro-batches
of 8 and step once. The math works out **only** with a scaling factor:

$$\mathcal{L}_{\text{full}} = \frac{1}{N}\sum_{i=1}^{N} \ell_i = \frac{1}{k}\sum_{j=1}^{k}\underbrace{\left(\frac{k}{N}\sum_{i \in B_j} \ell_i\right)}_{\mathcal{L}_j \;=\; \text{mean loss of micro-batch } j}$$

Every symbol: $N$ is the full batch size, $k$ the number of micro-batches,
$B_j$ the $j$-th micro-batch (size $N/k$), $\ell_i$ the per-sample loss, and
$\mathcal{L}_j$ the mean loss PyTorch's reduction gives you per micro-batch.
So the recipe is: **divide each micro-batch loss by $k$, backward each,
step once** — the accumulated `.grad` then equals the full-batch gradient
exactly.

## Dry-Run: Accumulated = Full-Batch

```
Model: pred = w·x, loss = (pred − y)², w = 1.0
Data (4 samples):  x = [1, 2, 3, 4],  y = [2, 4, 6, 8]
Per-sample gradient: ∂ℓᵢ/∂w = 2(w·xᵢ − yᵢ)·xᵢ = 2(xᵢ − 2xᵢ)·xᵢ = −2xᵢ²
  sample grads: −2, −8, −18, −32

FULL BATCH (mean loss): grad = mean(−2, −8, −18, −32) = −15

ACCUMULATION, k = 2 micro-batches of 2:
  micro-batch 1 mean grad: (−2 − 8)/2  = −5      backward(loss₁ / 2) adds −2.5
  micro-batch 2 mean grad: (−18 − 32)/2 = −25    backward(loss₂ / 2) adds −12.5
  accumulated w.grad = −2.5 − 12.5 = −15         = full batch ✓

Forget the ÷k and you get −30: a silently doubled learning rate.
```

## Key Takeaways for Section 3

`backward()` adds. Clear with `optimizer.zero_grad(set_to_none=True)` once
per *step* (not per micro-batch!). For gradient accumulation, scale each
micro-loss by $1/k$ — same numbers as the big batch, at a fraction of the
memory.

*Next: the four tools for the opposite job — keeping gradients out.*

---

# 4: The Four Ways to Stop Gradients

## The Problem It Solves

Half of real-world PyTorch is telling autograd what *not* to differentiate:
eval loops, frozen layers during fine-tuning, targets that must be treated as
constants, logging. PyTorch has four tools, they are **not** interchangeable,
and mixing them up produces silent bugs (a frozen layer that trains anyway)
or wasted memory (an eval loop that builds graphs).

## The Four Tools

**`tensor.detach()`** — *surgical, per-tensor.* Returns a view of the same
data that is cut out of the graph: `grad_fn=None`, `requires_grad=False`.
Gradients flowing backward hit the detached branch and stop. The original
tensor and the rest of the graph are unaffected.

**`with torch.no_grad():`** — *contextual.* Inside the block, autograd
records nothing at all — results have no `grad_fn`, no graph memory is
allocated. The classic wrapper for eval loops and manual weight updates.

**`with torch.inference_mode():`** — *no_grad, but stricter and faster.*
Tensors created inside can **never** be re-attached to autograd later (using
them in a recorded computation raises). Use it when you're certain nothing
downstream needs gradients — pure inference/serving.

**`param.requires_grad_(False)`** — *per-parameter and persistent.* The flag
lives on the tensor itself: no graph is built through it, `.grad` stays
`None`, and an optimizer step can't move it. This is **layer freezing** — the
fine-tuning tool. (Note: `model.eval()` does *not* do this! `eval()` only
switches layer behavior like dropout — chapter 5's territory.)

## The Math + Dry-Run: detach in Action

$$z = 3 \cdot \text{detach}(y) + y, \quad y = 2x \;\;\Rightarrow\;\; \frac{dz}{dx} = \underbrace{0}_{\text{detached branch}} + \underbrace{\frac{dy}{dx}}_{=2} = 2$$

```
x = 3.0 (requires_grad=True)
y = x·2 = 6.0
z = y.detach()·3 + y = 18.0 + 6.0 = 24.0
z.backward()

Through the LIVE branch:      dz/dy = 1, dy/dx = 2  → contributes 2
Through the DETACHED branch:  autograd sees a constant 6.0 → contributes 0
x.grad → 2.0

Without the detach: z = 3y + y = 4y → dz/dx = 8. The detach erased 6 of it.
```

The forward *values* are identical either way — `detach` only changes what
backward sees. That is exactly what you want for, e.g., training head B on
head A's outputs without updating A: `features_for_B = features_from_A.detach()`.

## Decision Guide: The Four Gradient-Stoppers

| Tool | Scope | Typical use | Failure mode if misused |
|---|---|---|---|
| `detach()` | one tensor, one use | stop-gradient targets; feed model A's output to model B's loss; safe logging | detaching too early kills gradients you needed |
| `torch.no_grad()` | code block | eval loops; manual param updates; init surgery | wrapping training code → "element 0 of tensors does not require grad" at backward |
| `torch.inference_mode()` | code block | pure inference / serving | outputs raise if a later op needs autograd |
| `requires_grad_(False)` | parameter, until flipped back | freezing layers for fine-tuning | forgetting to flip back; or freezing after the optimizer already has momentum on it |

## Key Takeaways for Section 4

`detach` cuts one edge; `no_grad` stops the recorder; `inference_mode` stops
it permanently for the tensors it creates; `requires_grad_(False)` freezes a
parameter. Pick by *scope*: tensor, block, block-forever, parameter.

*Next: the error messages that make people fear autograd, defused.*

---

# 5: In-Place Operations and the Errors They Cause

## The Problem It Solves

In-place ops (`add_`, `masked_fill_`, `+=`, `relu(inplace=True)`) overwrite a
tensor's storage instead of allocating a result. Sometimes that's free
memory savings; sometimes it destroys a value the backward pass still needed.
Autograd protects itself with a **version counter**: every tensor counts its
in-place modifications, and every graph node remembers which version of its
inputs it saved. If backward finds the version changed — the error below.

## The Two Classic RuntimeErrors

**Error 1 — in-place on a requiring leaf:**

```
w = torch.ones(3, requires_grad=True)
w += 1
→ RuntimeError: a leaf Variable that requires grad is being used in an
  in-place operation.
```

A leaf's `.data` is sacred while autograd watches it: mutating it would make
`.grad` correspond to values that no longer exist. This is why manual weight
updates are wrapped in `no_grad` — inside the block, the watching stops and
`w -= lr * w.grad` is legal (this is literally what optimizers do).

**Error 2 — modified a saved tensor:**

```
hidden = layer_one(x)          # PowBackward saved `hidden` for its backward
hidden += residual             # in-place bump — version counter increments
out = hidden.sum(); out.backward()
→ RuntimeError: one of the variables needed for gradient computation has
  been modified by an inplace operation: [torch.FloatTensor [...]], which
  is output 0 of PowBackward0, ... Hint: enable anomaly detection ...
```

The fix is almost always the out-of-place spelling: `hidden = hidden +
residual` allocates a new tensor, and the saved original survives untouched.

**When in-place is fine:** tensors autograd isn't tracking (buffers, masks,
anything under `no_grad`), and ops whose backward doesn't need the
overwritten value. `masked_fill_` on a `bool` mask you built yourself is
fine; `+=` mid-forward on an activation is Russian roulette.

*A related band-aid to distrust:* calling `backward()` twice raises
`Trying to backward through the graph a second time...` because the graph's
saved tensors are freed after the first pass. `retain_graph=True` makes the
error go away — but wanting two backwards through one forward is usually a
sign the loop structure is wrong (recompute the forward instead).

## Key Takeaways for Section 5

Version counters catch in-place writes that would corrupt backward. Never
`+=` a requiring leaf outside `no_grad`; prefer out-of-place ops mid-forward;
treat `retain_graph=True` as a smell, not a fix.

*Next: what all this recording costs — and the one-line leak everyone
writes once.*

---

# 6: Autograd and Memory

## The Intuition

The recorded graph isn't just bookkeeping — each node **keeps its saved input
tensors alive** (attention weights, pre-activations, everything backward will
need). For a transformer, those saved activations routinely outweigh the
weights themselves. The graph — and all those tensors — are freed only when
backward runs or when the last reference to the graph dies.

Two consequences ambush people:

**Eval without no_grad.** A validation loop that calls `model(inputs)` bare
builds a full graph per batch that nobody will ever backward through. The
graph does get garbage-collected each iteration, but at any moment you're
holding activations you don't need — on a big model, that's the difference
between fitting and OOM. Wrap eval in `torch.no_grad()` (or
`inference_mode`); nothing is recorded, activations are freed as the forward
proceeds.

**The loss-logging leak.** The classic:

```
losses = []
for inputs, targets in loader:
    ...
    loss = criterion(outputs, targets)
    loss.backward()
    optimizer.step()
    losses.append(loss)        # ← the leak
```

`loss` is a graph-carrying tensor: it holds `grad_fn`, which holds the whole
step's saved activations. Appending it to a list keeps **every step's entire
graph** alive forever — memory grows linearly with iterations until OOM,
usually mid-epoch, usually blamed on batch size. The fix costs nothing:

```
losses.append(loss.item())     # a Python float — no tensor, no graph
# or loss.detach() if you need it as a tensor
```

Rule of thumb: **anything that outlives the step — logs, running averages,
histories — must be `.item()`ed or `.detach()`ed.**

## Key Takeaways for Section 6

The graph pins every saved activation until backward or GC. Wrap all
non-training forwards in `no_grad`/`inference_mode`. Never store a
graph-carrying tensor beyond the step — `.item()` for scalars, `.detach()`
for tensors. *(Chapter 8 adds the tooling: `torch.cuda.memory_allocated`,
anomaly detection, OOM anatomy.)*

---

# 7: Key Takeaways + Master Decision Table

Autograd in four sentences: the forward pass records a dynamic graph of every
op touching a requires-grad tensor. `backward()` replays it in reverse with
the chain rule, *adding* results into requiring leaves' `.grad`. The graph
holds saved activations until then, so control what gets recorded. Four
tools stop recording at four different scopes.

| I want to... | Reach for | Why |
|---|---|---|
| Gradients for my parameters | scalar loss → `loss.backward()` | vector outputs need a Jacobian story |
| Inspect an intermediate's gradient | `intermediate.retain_grad()` before backward | non-leaf grads are discarded by default |
| Clear gradients between steps | `optimizer.zero_grad(set_to_none=True)` | backward *accumulates* |
| Train with a batch that doesn't fit | accumulate: `(loss / k).backward()` × k, one `step()` | matches full-batch grad exactly |
| Use a tensor as a constant in a loss | `detach()` | cuts one edge of the graph |
| Run an eval loop | `with torch.no_grad():` | no graph, no wasted memory |
| Serve / pure inference | `with torch.inference_mode():` | faster; outputs can't rejoin autograd |
| Freeze layers for fine-tuning | `param.requires_grad_(False)` | per-parameter, persists; `eval()` does NOT do this |
| Update weights by hand | inside `no_grad` | in-place on a watched leaf is forbidden outside |
| Fix "modified by an inplace operation" | use the out-of-place op (`x = x + r`) | the saved tensor must survive until backward |
| Log the loss | `loss.item()` | a stored `loss` tensor pins its whole graph |

**Connection forward:** you now own tensors (ch1), the ops between them
(ch2), and the gradient machinery underneath (ch3) — the complete *language*.
Chapter 4 starts the *model* block: how `nn.Module` packages parameters,
buffers, and submodules, and which container (`Sequential`, `ModuleList`,
`ModuleDict`) to reach for when.
