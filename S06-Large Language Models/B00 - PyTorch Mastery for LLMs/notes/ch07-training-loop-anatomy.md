# Chapter 7: Training Loop Anatomy

## Table of Contents

1. [Why the Loop's Order Is Not Negotiable](#1-why-the-loops-order-is-not-negotiable)
2. [The Canonical Loop, Line by Line](#2-the-canonical-loop-line-by-line)
3. [train() vs eval(): The Behavior Switch, Revisited](#3-train-vs-eval-the-behavior-switch-revisited)
4. [The Optimizer Zoo: SGD vs Adam vs AdamW](#4-the-optimizer-zoo-sgd-vs-adam-vs-adamw)
5. [Parameter Groups: Who Pays the Weight-Decay Tax?](#5-parameter-groups-who-pays-the-weight-decay-tax)
6. [Learning Rate Schedules: Warmup + Cosine Decay](#6-learning-rate-schedules-warmup--cosine-decay)
7. [Gradient Clipping: The Circuit Breaker](#7-gradient-clipping-the-circuit-breaker)
8. [Gradient Accumulation, Inside the Loop This Time](#8-gradient-accumulation-inside-the-loop-this-time)
9. [Checkpointing: Save Points That Actually Resume](#9-checkpointing-save-points-that-actually-resume)
10. [Bonus: bf16 Autocast on the A6000](#10-bonus-bf16-autocast-on-the-a6000)
11. [Key Takeaways + Master Decision Table](#11-key-takeaways--master-decision-table)

---

# 1: Why the Loop's Order Is Not Negotiable

Think of the training loop like a **recipe with seven steps that must happen
in exactly one order**: clear the bowl, mix the forward-pass ingredients,
measure how wrong the result tastes, work backward to find out whose fault
that was, trim anything that got out of hand, apply the fix, and adjust the
oven temperature for next time. Swap two steps and the dish isn't just
worse — it's a different, broken recipe. Try to "trim" before you've measured
anything, and there's nothing to trim. Try to "apply the fix" before you've
worked backward, and there's no fix to apply.

Every chapter so far handed you one ingredient: chapter 3 gave you
`backward()` and the accumulation trap, chapter 4 gave you modules with
`train()`/`eval()`, chapter 5 gave you loss functions, chapter 6 gave you
batches. This chapter is the recipe that uses all of them, in the one order
that actually works — and it explains *why* that order is the only one that
works, so a scrambled loop stops being a mystery and starts being something
you can read line by line and predict.

---

# 2: The Canonical Loop, Line by Line

## The Seven Steps

```python
for inputs, targets in dataloader:                     # from ch06's DataLoader
    optimizer.zero_grad(set_to_none=True)               # 1. clear the bowl
    outputs = model(inputs)                             # 2. forward pass
    loss = criterion(outputs, targets)                  # 3. measure how wrong
    loss.backward()                                     # 4. work backward — fills .grad
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # 5. trim runaway grads
    optimizer.step()                                    # 6. apply the fix — moves the weights
    scheduler.step()                                     # 7. adjust the "oven temperature" (lr)
```

## Why Each Step Depends on the One Before It

**Step 1 must come before step 4**, not after — chapter 3's whole
"accumulation is the default" lesson. If you clear the bowl *after*
`backward()` instead of before, you erase the very gradients you just
computed and `optimizer.step()` moves nothing.

**Step 4 must come before step 5 and step 6.** Clipping (step 5) rescales
`.grad` — there is nothing to rescale until backward has filled it in.
Stepping (step 6) reads `.grad` to know which direction to move each
parameter — call it before backward and you're applying yesterday's
gradient, or none at all.

**Step 5 must come before step 6.** This is the one people get backward
(pun intended): clip first, *then* step. If you step first, the update has
already happened with the runaway gradient — clipping afterward is
closing the barn door after the horse has bolted.

**Step 7 comes last**, and it adjusts the learning rate **for the *next*
step**, not this one — `optimizer.step()` already used whatever `lr` the
scheduler set on the *previous* call.

## Dry-Run: What Happens If You Get the Order Wrong

```
Correct:   zero_grad → forward → loss → backward → clip → step → scheduler.step

Swap 1: step BEFORE backward
  optimizer.step() reads .grad — but .grad is either None (first ever call,
  RuntimeError-free but does nothing) or STALE from the previous iteration
  (if you forgot to zero_grad too). The model updates using yesterday's
  mistake, not today's.

Swap 2: clip BEFORE backward
  clip_grad_norm_ reads .grad to compute the norm — with no backward yet,
  .grad is None for every fresh parameter. Either a silent no-op or a
  crash, depending on the tensor's history. Nothing got trimmed.

Swap 3: forgot zero_grad
  loss.backward() ADDS into whatever was left in .grad from last time
  (ch03). Two iterations' worth of signal pushes one step. Training still
  "runs" — it just slowly diverges from correct.
```

## Key Takeaways for Section 2

Seven steps, one valid order: clear → forward → measure → backward → clip →
step → schedule. Every dependency is mechanical (you can't rescale, read, or
adjust what doesn't exist yet) — which means a scrambled loop is always
debuggable by asking "what does this line need, and has it been produced
yet?"

*Next: the switch that changes what `forward` even computes.*

---

# 3: train() vs eval(): The Behavior Switch, Revisited

Chapters 4 and 5 already introduced the two rules — worth stating once more
because the training loop is where forgetting them actually costs you:

`model.train()` and `model.eval()` flip the `.training` flag on every
submodule. `Dropout` reads it (drop-and-scale vs identity); `BatchNorm`
reads it (batch statistics vs running statistics); `LayerNorm` does **not**
read it at all (chapter 5 — it never depended on the batch in the first
place). The loop calls `model.train()` once before the training loop starts
each epoch and `model.eval()` before the validation loop — and, per chapter
4, **neither one freezes a single weight**. `eval()` changes behavior;
`requires_grad_(False)` freezes.

```python
for epoch in range(num_epochs):
    model.train()                     # dropout ON, batchnorm uses batch stats
    for inputs, targets in train_loader:
        ...                            # the seven steps from section 2

    model.eval()                      # dropout OFF, batchnorm uses running stats
    with torch.no_grad():             # ch03: no graph needed, nothing to backward
        for inputs, targets in val_loader:
            val_loss = criterion(model(inputs), targets)
```

*Next: what step 6, `optimizer.step()`, actually computes.*

---

# 4: The Optimizer Zoo: SGD vs Adam vs AdamW

## The Intuition: Walking Downhill, Blindfolded

Gradient descent is walking downhill on a landscape you cannot see, feeling
only the slope under your feet (the gradient) and taking a step in the
steepest downhill direction. The optimizers in this section are three
increasingly clever strategies for *how big a step to take, and in exactly
what direction*.

**SGD** takes a fixed-size step directly downhill, every time:
$$\theta_{t+1} = \theta_t - \eta \, g_t$$
where $\theta_t$ is the parameter, $\eta$ the learning rate, and $g_t$ the
gradient at this step. Simple, but it has no memory — on a landscape with a
narrow, steep-walled valley, it oscillates wall to wall instead of gliding
along the valley floor.

**SGD with momentum** remembers the direction it was already moving, like a
heavy ball rolling downhill instead of a person taking discrete steps: it
picks up speed in a consistent direction and damps out the wall-to-wall
oscillation.

**Adam** goes further: it keeps a per-parameter *running average of the
gradient* (which way, and how consistently, has this specific parameter been
told to move — the first moment $m_t$) and a per-parameter *running average
of the squared gradient* (how bumpy has the terrain been for this parameter —
the second moment $v_t$). Parameters on bumpy terrain get smaller effective
steps; parameters on smooth, consistent terrain get to move faster. Every
parameter gets its own adaptive stride.

## The Math

$$m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t, \qquad v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$$
$$\hat{m}_t = \frac{m_t}{1-\beta_1^t}, \qquad \hat{v}_t = \frac{v_t}{1-\beta_2^t}, \qquad \theta_{t+1} = \theta_t - \eta \, \frac{\hat{m}_t}{\sqrt{\hat{v}_t} + \epsilon}$$

Every symbol: $g_t$ the raw gradient at step $t$; $\beta_1, \beta_2$
(typically $0.9, 0.999$) how much the running averages favor history over the
newest gradient; $\hat{m}_t, \hat{v}_t$ are *bias-corrected* versions of
$m_t, v_t$ (early on, $m_t$ and $v_t$ start at 0 and are biased toward 0 — the
$1-\beta^t$ divisor compensates, mattering most in the first few steps);
$\epsilon$ (tiny, e.g. $10^{-8}$) prevents division by zero when a parameter's
gradient has been consistently near zero.

## The AdamW Fix: Decoupling Weight Decay

**Weight decay** — shrinking every weight slightly toward zero each step,
independent of the gradient — fights overfitting by discouraging any single
weight from growing huge. The classical way to add it to SGD is called **L2
regularization**: add $\lambda \theta$ to the gradient before the update,
where $\lambda$ is the decay strength. For plain SGD this is mathematically
identical to a real, direct shrink of $\theta$.

For Adam it is *not* identical — and this is the bug **AdamW** fixes. If you
fold $\lambda\theta$ into $g_t$ before Adam computes $m_t$ and $v_t$, the
decay term gets divided by $\sqrt{\hat v_t}$ along with everything else. A
parameter with a large, noisy "real" gradient has a large $\hat v_t$, which
**swamps the decay signal** — it barely decays at all. AdamW's fix: apply the
decay as a *separate, direct* multiplicative shrink, decoupled from the
adaptive machinery entirely:

$$\theta_{t+1} = \theta_t - \eta \frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon} - \eta\lambda\theta_t$$

## Dry-Run: Watching the Bug, With Only Decay and No Real Gradient

```
w starts at 2.0, lr = 0.1, weight_decay = 0.5, gradient = 0 every step
(isolating the decay term completely)

Adam  (decay folded into the gradient):
  1.9000, 1.8002, 1.7006, 1.6015, 1.5030, 1.4051, ...   ← roughly LINEAR decay
  (the adaptive 1/sqrt(v_hat) term re-normalizes the tiny decay-only
   "gradient" back up toward a fixed step size each time)

AdamW (decoupled decay, θ *= (1 − lr·λ) = θ * 0.95 every step):
  1.9000, 1.8050, 1.7147, 1.6290, 1.5476, 1.4702, ...   ← clean GEOMETRIC decay
  1.9 × 0.95 = 1.805 ✓   1.805 × 0.95 = 1.71475 ✓
```

Both shrink `w` — but AdamW's shrink is the mathematically clean one you'd
actually design on purpose. This is why virtually every transformer trains
with AdamW, never plain Adam.

## Decision Guide: Which Optimizer

| Situation | Use | Why |
|---|---|---|
| Simple baselines, full control over the schedule | SGD (+ momentum) | predictable, well-understood, one adaptive-free step size |
| Almost anything else, especially transformers | AdamW | adaptive per-parameter steps + correctly decoupled weight decay |
| You see "Adam" with `weight_decay` in old code | treat as a smell | it's the coupled, swamped version — prefer AdamW |
| No regularization needed at all | Adam (`weight_decay=0`) | with zero decay, Adam and AdamW are identical |

## Key Takeaways for Section 4

SGD = fixed downhill step; momentum = a rolling ball; Adam = a per-parameter
adaptive stride from running averages of gradient and squared gradient.
AdamW decouples weight decay from that adaptive machinery so decay actually
decays. Default to AdamW.

*Next: not every parameter should pay the decay tax.*

---

# 5: Parameter Groups: Who Pays the Weight-Decay Tax?

## The Idea

Weight decay assumes a parameter's *size* is meaningful — a huge weight is
suspicious, so shrink it. That assumption breaks for two kinds of parameters:
**biases** (a bias is just an offset; there's nothing wrong with a bias of
17) and **norm layers' `gamma`/`beta`** (chapter 5 — `gamma` starts at 1 and
is *supposed* to be near 1; decaying it toward 0 fights the layer's own
purpose). The convention across virtually every transformer codebase: apply
weight decay only to genuine weight *matrices* (2-D+ parameters), and exempt
every 1-D parameter (biases, norm scales/shifts).

## The Code

`optimizer.param_groups` lets you hand the optimizer a *list* of parameter
groups, each with its own hyperparameters:

```python
decay_params, no_decay_params = [], []
for name, param in model.named_parameters():
    if param.ndim >= 2:              # weight matrices (Linear, Embedding, ...)
        decay_params.append(param)
    else:                            # biases, LayerNorm gamma/beta — all 1-D
        no_decay_params.append(param)

optimizer = torch.optim.AdamW([
    {"params": decay_params,    "weight_decay": 0.1},
    {"params": no_decay_params, "weight_decay": 0.0},
], lr=3e-4)
```

Everything else (`lr`, `betas`, `eps`) is inherited from the outer call
unless a group overrides it — the same mechanism lets you give, say, a
pretrained encoder a smaller learning rate than a freshly initialized head.

## Key Takeaways for Section 5

Decay weight *matrices*, exempt 1-D parameters (biases, norm scale/shift).
`param_groups` is how one optimizer applies different hyperparameters to
different slices of the model.

*Next: the "oven temperature" that step 7 was adjusting.*

---

# 6: Learning Rate Schedules: Warmup + Cosine Decay

## The Intuition

Starting a training run at full learning rate is like sprinting the instant
you get out of bed — the model's weights are freshly initialized, gradients
are large and noisy, and a big step in a bad direction early on can be hard
to recover from. **Warmup** eases in: the learning rate ramps up linearly
from near-zero over the first handful of steps. Once warmed up, **cosine
decay** glides the learning rate back down to near-zero by the end of
training, smoothly, rather than dropping it off a cliff — like a runner
slowing gradually into the finish line instead of stopping dead.

## The Math

$$\eta(t) = \begin{cases} \eta_{\max} \cdot \dfrac{t}{T_{\text{warmup}}} & t < T_{\text{warmup}} \\[4pt] \dfrac{\eta_{\max}}{2}\left(1 + \cos\left(\pi \cdot \dfrac{t - T_{\text{warmup}}}{T_{\text{total}} - T_{\text{warmup}}}\right)\right) & t \geq T_{\text{warmup}} \end{cases}$$

Every symbol: $t$ the current step, $T_{\text{warmup}}$ how many steps the
ramp-up lasts, $T_{\text{total}}$ the whole training run's step count, and
$\eta_{\max}$ the peak learning rate reached right at the end of warmup. The
cosine term smoothly carries $\eta$ from $\eta_{\max}$ (at
$t=T_{\text{warmup}}$, where $\cos(0)=1$) down to $0$ (at $t=T_{\text{total}}$,
where $\cos(\pi)=-1$).

## Dry-Run with Tiny Numbers

```
eta_max = 0.001, T_warmup = 10, T_total = 100

step   0: still warming up → 0.001 * 0/10   = 0.000000
step   5: still warming up → 0.001 * 5/10   = 0.000500
step  10: warmup complete  → peak            = 0.001000
step  20: cosine, progress=(20-10)/(90)=0.111 → 0.000970
step  55: cosine, progress=(55-10)/90=0.5     → 0.000500   (halfway down)
step 100: cosine, progress=1.0                → 0.000000
```

In PyTorch this is almost always installed as a `LambdaLR` (or the
`transformers` library's `get_cosine_schedule_with_warmup`) wrapping exactly
this formula — a function of `step` returning a *multiplier* on the base
`lr`, called once per `scheduler.step()`.

## Key Takeaways for Section 6

Warmup ramps up linearly to protect against a bad first move; cosine decay
glides back down to near-zero instead of a hard stop. `scheduler.step()`
runs once per optimizer step, always after it (section 2).

*Next: capping how hard any single step is allowed to push.*

---

# 7: Gradient Clipping: The Circuit Breaker

## The Intuition

A circuit breaker doesn't care *which* appliance caused a power surge — it
just caps the current before it fries anything. Gradient clipping does the
same for a training step: if the combined gradient across *every* parameter
is unusually large (a batch with a pathological example, an early or unstable
training regime), clipping rescales the whole thing down to a safe maximum
before `optimizer.step()` can act on it.

## The Math

$$\|g\| = \sqrt{\sum_{i} \|g_i\|^2}, \qquad g_i \leftarrow g_i \cdot \min\left(1, \frac{\text{max\_norm}}{\|g\|}\right)$$

Every symbol: $g_i$ is the gradient of the $i$-th *parameter tensor* in the
model (so $\|g\|$ is one **global** norm computed over every parameter's
gradient at once, not per-tensor); `max_norm` the cap. If $\|g\|$ is already
under the cap, the scaling factor is 1 and nothing changes. If it's over, every
gradient shrinks by the *same* ratio — direction is preserved, only magnitude
is capped.

## Dry-Run with Tiny Numbers

```
Two parameter tensors' gradients: g1 = [3, 4], g2 = [0]  (irrelevant, adds 0)
global norm ‖g‖ = sqrt(3² + 4²) = sqrt(25) = 5.0

max_norm = 2.0:
  scale = min(1, 2.0/5.0) = 0.4
  g1 → [3*0.4, 4*0.4] = [1.2, 1.6]
  new norm = sqrt(1.2² + 1.6²) = sqrt(1.44+2.56) = sqrt(4.0) = 2.0  ✓ exactly capped

max_norm = 10.0 (already under):
  scale = min(1, 10.0/5.0) = 1.0   → nothing changes
```

`torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)` does exactly
this, in place, across every parameter's `.grad` at once — which is why it
sits **after `backward()`, before `step()`** (section 2): it needs `.grad`
populated, and it needs to finish rescaling before the optimizer reads it.

## Key Takeaways for Section 7

One global norm across every parameter, rescaled down (never up) to a cap,
direction preserved. Sits between backward and step — nowhere else makes
sense.

*Next: accumulation, back with the rest of the loop around it.*

---

# 8: Gradient Accumulation, Inside the Loop This Time

Chapter 3 proved the math: scale each micro-batch's loss by $1/k$, backward
each one, and the accumulated `.grad` equals the full-batch gradient exactly.
The piece that chapter couldn't show yet is *where the other five steps go*
when a "step" spans several micro-batches:

```python
optimizer.zero_grad(set_to_none=True)              # ONCE per real step
for micro_step, (inputs, targets) in enumerate(micro_batches):
    outputs = model(inputs)
    loss = criterion(outputs, targets) / ACCUM_STEPS
    loss.backward()                                 # accumulates — this is the point
    if (micro_step + 1) % ACCUM_STEPS == 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # on the FULL accumulated grad
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)       # reset for the NEXT real step
```

The rule this makes concrete: **clip, step, schedule, and zero_grad all
happen on real-step boundaries, never per micro-batch.** Clipping every
micro-batch would rescale a partial, incomplete gradient sum against the
same `max_norm` meant for the *full* accumulated gradient — capping it far
too aggressively, long before the sum you actually care about is complete.

## Key Takeaways for Section 8

A "step" made of $k$ micro-batches still has exactly one clip, one step, one
schedule tick, one zero_grad — all after the $k$-th backward, never before.

*Next: surviving a crash without losing the run.*

---

# 9: Checkpointing: Save Points That Actually Resume

## The Naive Bug

Saving `model.state_dict()` alone and calling it a checkpoint is a video game
save file that only remembers your character's position — not their
inventory, quest progress, or stats. Adam's `m_t`/`v_t` running averages
(section 4) live inside `optimizer.state_dict()`, **not** the model. Resuming
from weights alone silently restarts every parameter's momentum from zero —
training doesn't crash, it just takes a visible little stumble right after
resume as the adaptive estimates re-warm from scratch.

## What an Honest Checkpoint Saves

```python
torch.save({
    "epoch": epoch,
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),      # Adam's m_t, v_t per parameter
    "scheduler": scheduler.state_dict(),      # where the LR schedule left off
    "best_val_loss": best_val_loss,
}, "checkpoint.pt")

checkpoint = torch.load("checkpoint.pt", map_location=device)   # ch08 covers map_location
model.load_state_dict(checkpoint["model"])
optimizer.load_state_dict(checkpoint["optimizer"])
scheduler.load_state_dict(checkpoint["scheduler"])
start_epoch = checkpoint["epoch"] + 1
```

Resuming this way is bit-for-bit continuous: the optimizer's momentum, the
scheduler's position on the warmup/cosine curve, and the model's weights all
pick up exactly where they left off — no stumble.

## Key Takeaways for Section 9

A checkpoint is model **+** optimizer **+** scheduler **+** the training
position (epoch/step). Model-only is a smaller file and a broken resume.

*Next: an optional two-line speedup, now that the loop is solid.*

---

# 10: Bonus: bf16 Autocast on the A6000

Chapter 1 introduced `bfloat16`'s range advantage over `float16`. Using it
during training is two lines, and — because bf16 keeps fp32's exponent
range — needs **none of fp16's `GradScaler` machinery**:

```python
with torch.autocast(device_type="cuda", dtype=torch.bfloat16):   # or "cpu"
    outputs = model(inputs)
    loss = criterion(outputs, targets)
loss.backward()             # backward runs OUTSIDE the autocast block
optimizer.step()
```

`autocast` runs eligible ops (mostly matmuls) in bf16 for speed and memory,
while keeping numerically sensitive ops (like reductions inside a loss) in
fp32 automatically. The Ampere architecture (RTX A6000 included) has native
bf16 tensor cores, so this is close to a free speedup with no stability
tax — contrast fp16, which needs a `GradScaler` wrapping `backward()`/`step()`
specifically to survive the overflow risk chapter 1 demonstrated.

---

# 11: Key Takeaways + Master Decision Table

The loop is a strict seven-step recipe; every optimizer, scheduler, and
clipping choice slots into steps 5–7 without disturbing steps 1–4.

| I want to... | Reach for | Why |
|---|---|---|
| The right loop order | zero_grad → forward → loss → backward → clip → step → schedule | each step needs what the last one produced |
| Toggle dropout/batchnorm behavior | `model.train()` / `model.eval()` | ch04/5: behavior switch, never a freeze |
| A default optimizer for almost anything NLP | `AdamW` | correctly decoupled weight decay |
| A simple, predictable baseline | `SGD` (+ momentum) | fixed step, well understood |
| Exempt biases/norm params from decay | split into `param_groups` by `ndim` | decaying a bias or `gamma` fights the layer's purpose |
| Protect the first few steps | linear warmup | avoids a bad early large step |
| Wind the LR down smoothly | cosine decay | no hard stop at the end of training |
| Cap a runaway gradient | `clip_grad_norm_(..., max_norm)` | one global norm, direction preserved, magnitude capped |
| Simulate a bigger batch | gradient accumulation | clip/step/schedule/zero_grad only on real-step boundaries |
| Resume training exactly | save model **+** optimizer **+** scheduler **+** epoch | optimizer holds momentum; scheduler holds LR position |
| A quick, mostly-free speedup on Ampere+ GPUs | `torch.autocast(dtype=torch.bfloat16)` | bf16's range needs no GradScaler |

**Connection forward:** the loop now runs correctly and efficiently.
Chapter 8 covers what happens when it *doesn't* — reading shape-error
tracebacks, hunting NaNs, device placement mistakes, and the
`state_dict` surgery needed when a checkpoint doesn't load cleanly.
