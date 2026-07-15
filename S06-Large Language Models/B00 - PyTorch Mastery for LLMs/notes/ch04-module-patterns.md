# Chapter 4: Module Patterns

## Table of Contents

1. [Why nn.Module Exists](#1-why-nnmodule-exists)
2. [Registration: Parameter vs Buffer vs Plain Attribute](#2-registration-parameter-vs-buffer-vs-plain-attribute)
3. [nn.Linear Internals](#3-nnlinear-internals)
4. [Weight Initialization and the Variance Story](#4-weight-initialization-and-the-variance-story)
5. [The Containers: Sequential vs ModuleList vs ModuleDict](#5-the-containers-sequential-vs-modulelist-vs-moduledict)
6. [__call__ vs forward](#6-__call__-vs-forward)
7. [model.apply and Parameter Counting](#7-modelapply-and-parameter-counting)
8. [Freezing Layers for Fine-Tuning](#8-freezing-layers-for-fine-tuning)
9. [Key Takeaways + Master Decision Table](#9-key-takeaways--master-decision-table)

---

# 1: Why nn.Module Exists

## What This Chapter Is Really About

Nothing stops you from building a neural network out of raw tensors: create
weight tensors with `requires_grad=True`, write the math, keep the tensors in
a list for the optimizer. It works — for about two layers. Then the
bookkeeping eats you alive: every new weight must be added to the optimizer
list by hand, moved to the GPU by hand, saved to disk by hand, and switched
between train/eval behavior by hand.

**`nn.Module` is an accounting system.** Its one job is to *know about* every
learnable tensor, every piece of persistent state, and every submodule inside
your model — automatically — so that `model.parameters()`,
`model.to(device)`, `model.state_dict()`, and `model.train()/eval()` each do
the right thing to the whole tree with one call.

The flip side: state the accounting system doesn't know about is
**invisible**. It won't be trained, won't move to the GPU, won't be saved.
The nastiest bugs in this chapter are all "I created state that PyTorch never
registered" — and they never crash; they just silently do nothing.

---

# 2: Registration: Parameter vs Buffer vs Plain Attribute

## The Intuition

Think of a module as an office with a **payroll list** and an **inventory
list**. When you assign something to `self.<name>` inside a module,
`nn.Module.__setattr__` inspects what you assigned:

- an **`nn.Parameter`** goes on the payroll: it is learned (appears in
  `parameters()`, gets gradients, the optimizer updates it) *and* on the
  inventory (saved in `state_dict()`, moved by `.to()`).
- a **buffer** (registered via `self.register_buffer("name", tensor)`) goes
  only on the inventory: not learned, no gradients — but saved and moved.
  This is for state that *belongs to* the model without being trainable: a
  causal mask, positional encodings, running statistics.
- a **plain tensor attribute** (`self.thing = torch.zeros(...)`) goes on
  *neither list*. PyTorch does not see it. It stays on CPU when the model
  moves, vanishes from checkpoints, never trains.

`nn.Parameter` itself is nothing exotic: a tensor subclass whose only powers
are `requires_grad=True` by default and *triggering the registration*.

## Dry-Run: The Three Kinds of State

```
class ToyBlock(nn.Module):
    def __init__(self):
        super().__init__()
        self.scale      = nn.Parameter(torch.ones(2))          # payroll + inventory
        self.register_buffer("positions", torch.linspace(0, 1, 4))  # inventory only
        self.stash      = torch.zeros(3)                        # ← invisible!

block = ToyBlock()

list(block.parameters())        → [scale]                only the Parameter
block.state_dict().keys()       → ['scale', 'positions'] buffer saved, stash NOT
block.to(torch.float64)
  block.scale.dtype             → float64   moved ✓
  block.positions.dtype         → float64   moved ✓
  block.stash.dtype             → float32   left behind ✗  ← the silent bug
```

## Decision Guide: Which Kind of State

| The tensor is... | Use | Because |
|---|---|---|
| Learned by gradient descent | `nn.Parameter` | optimizer + checkpoint + device movement |
| Fixed but part of the model (masks, positional tables, running stats) | `register_buffer` | checkpoint + device movement, no gradients |
| Pure configuration (ints, flags, shapes) | plain attribute | it's not a tensor concern |
| A tensor you assign as a plain attribute | — almost never right | invisible to `.to()`, `state_dict`, optimizer |

## Key Takeaways for Section 2

Assignment inside a module is registration. Parameter = learned + saved +
moved; buffer = saved + moved; plain tensor = none of the above. When a
tensor "mysteriously stayed on the CPU" or "was missing from the checkpoint,"
it was a plain attribute that should have been a buffer.

*Next: the workhorse module, opened up.*

---

# 3: nn.Linear Internals

## The Math

`nn.Linear(in_features, out_features)` computes an **affine transform**:

$$y = x W^\top + b$$

Every symbol: $x$ is the input of shape `(..., in_features)`, $W$ is the
weight of shape **`(out_features, in_features)`**, $b$ the bias of shape
`(out_features,)`, and $y$ the output of shape `(..., out_features)`.

The shape of $W$ trips everyone up once: it is `(out, in)`, not `(in, out)`.
The mental model: **row $i$ of $W$ is the recipe for output neuron $i$** — a
vector of `in_features` mixing weights. Because rows are recipes, the forward
pass needs the transpose: `x @ W.T`.

## Dry-Run with Tiny Numbers

```
in_features = 3, out_features = 2

x = [1, 2, 3]                    shape (1, 3)
W = [[ 1.0, 0.0, -1.0],          shape (2, 3) — row 0: recipe for output 0
     [ 0.5, 0.5,  0.5]]                        row 1: recipe for output 1
b = [0.1, -0.1]

y = x @ W.T + b
  y[0] = 1·1.0 + 2·0.0 + 3·(−1.0) + 0.1  = −2.0 + 0.1 = −1.9
  y[1] = 1·0.5 + 2·0.5 + 3·0.5  − 0.1    =  3.0 − 0.1 =  2.9
  → y = [−1.9, 2.9]              shape (1, 2) ✓
```

A manual implementation is four lines — and building it once (exercise 1)
permanently demystifies every `Linear` you'll ever read:

```
self.weight = nn.Parameter(torch.randn(out_features, in_features) * scale)
self.bias   = nn.Parameter(torch.zeros(out_features))
def forward(self, inputs):                 # (..., in) @ (in, out) → (..., out)
    return inputs @ self.weight.T + self.bias
```

## Key Takeaways for Section 3

Linear = `x @ W.T + b`; weight is `(out, in)` because each row is one output
neuron's recipe. Everything else about `nn.Linear` is registration (section
2) and initialization (next).

*Next: why that `* scale` in the manual version is not optional.*

---

# 4: Weight Initialization and the Variance Story

## The Problem It Solves

Two initializations kill a network before training starts. **All zeros**
makes every neuron in a layer identical — identical outputs, identical
gradients, identical updates, forever (the **symmetry problem**: neurons can
never differentiate). **Too-large random values** make activations *grow*
layer by layer until they overflow or saturate every nonlinearity.

## The Math

For one output $y = \sum_{i=1}^{d_{\text{in}}} w_i x_i$ with independent,
zero-mean weights and inputs:

$$\text{Var}(y) = d_{\text{in}} \cdot \text{Var}(w) \cdot \text{Var}(x)$$

Every symbol: $d_{\text{in}}$ is how many terms the sum has, $\text{Var}(w)$
the variance of each weight, $\text{Var}(x)$ the variance of each input.
The variance of a sum of independent terms is the sum of their variances —
so it grows *linearly with width*. For the signal to pass through unchanged
($\text{Var}(y) = \text{Var}(x)$) we need:

$$\text{Var}(w) = \frac{1}{d_{\text{in}}} \quad\Longleftrightarrow\quad \sigma_w = \frac{1}{\sqrt{d_{\text{in}}}}$$

*(Nonlinearities adjust the constant — ReLU zeroes half the signal, so
Kaiming init uses $2/d_{\text{in}}$ — but the $1/d_{\text{in}}$ shape of the
rule is the whole story. `nn.Linear` ships with a Kaiming-style default.)*

## Dry-Run: Watching a Stack Explode

```
5 linear layers, width d = 20, input std 1.0

With σ_w = 1.0:   each layer multiplies std by √(d·Var(w)) = √20 ≈ 4.47
  layer 1: std ≈ 4.5      layer 3: std ≈ 89
  layer 2: std ≈ 20       layer 5: std ≈ 1786     ← exploded

With σ_w = 1/√20 ≈ 0.224: each layer multiplies std by √(20 · 1/20) = 1
  layer 1..5: std ≈ 1     ← stable, gradients can flow
```

One mechanical note for exercise 5: initialization mutates parameters
in place, and autograd forbids in-place writes on requiring leaves (chapter
3). Init surgery therefore always sits inside `torch.no_grad()`:

```
with torch.no_grad():
    layer.weight.normal_(mean=0.0, std=d_in ** -0.5)
```

## Key Takeaways for Section 4

Zeros can't train (symmetry); big weights explode (variance scales with
width). $\sigma_w \sim 1/\sqrt{d_{\text{in}}}$ keeps signal variance
constant through depth. Init in place, inside `no_grad`.

*Next: assembling layers — and the container decision everyone gets wrong
first.*

---

# 5: The Containers: Sequential vs ModuleList vs ModuleDict

## The Problem It Solves

A model is a *tree* of modules, and PyTorch gives three containers for the
branches. They differ on exactly two questions: **does it write `forward`
for you?** and **does it register your submodules?** Choosing wrong is
either a small inconvenience (you wrote a forward you didn't need) or a
silent catastrophe (your layers never trained at all).

## The Three Containers

**`nn.Sequential`** — a fixed straight pipe. It registers the layers *and*
provides the forward: each layer feeds the next, no branches, no skips.

```
Input → [Linear] → [ReLU] → [Linear] → [ReLU] → [Linear] → Output
        exactly this, nothing else expressible
```

**`nn.ModuleList`** — registration *only*. It looks like a Python list, but
it has no forward: you write the loop yourself, which is exactly what makes
residual connections, per-layer conditions, and collecting intermediate
activations possible:

```
for layer in self.layers:
    layer_output = layer(x)
    x = x + layer_output          # ← a shortcut Sequential cannot express
```

**`nn.ModuleDict`** — registration by *name*. For models with named branches:
a shared encoder feeding a `{"sentiment": head1, "topic": head2}` pair of
task heads, chosen at runtime by key.

## The Plain-List Catastrophe

The container question has one wrong answer that fails silently:

```
class BrokenStack(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = [nn.Linear(8, 8) for _ in range(3)]    # plain Python list!

registration only happens on __setattr__ of a Module/Parameter —
a *list of* modules is just a list. Consequences:

  sum(p.numel() for p in model.parameters())  → 0        nothing on payroll
  optimizer = SGD(model.parameters(), ...)    → optimizer over NOTHING
  model.to("cuda")                            → layers stay on CPU
  model.state_dict()                          → {}       checkpoint is empty

The forward pass still runs and produces numbers. The loss just never
improves — the most expensive way to discover this bug is after a week of
"training."
```

The fix is one word: `nn.ModuleList([...])` instead of `[...]`.

## Decision Guide: The Container Tree

```
Is the data flow a straight pipe (each layer feeds the next, nothing else)?
 ├── YES → nn.Sequential                 (forward comes free)
 └── NO  → do branches have meaningful NAMES chosen at runtime?
            ├── YES → nn.ModuleDict      (self.heads["sentiment"])
            └── NO  → nn.ModuleList      (you write the loop: residuals,
                                          per-layer logic, collecting states)
Never: a plain Python list/dict of modules — invisible parameters.
```

## Key Takeaways for Section 5

`Sequential` = registration + forward; `ModuleList`/`ModuleDict` =
registration only, loop yourself. A plain list of modules produces a model
with zero parameters that trains nothing and saves nothing — check
`count_parameters` whenever a model learns suspiciously slowly.

*Next: why you call `model(x)` and never `model.forward(x)`.*

---

# 6: __call__ vs forward

You write the math in `forward`, but you invoke the module as `model(x)`.
The difference is not style: `model(x)` runs `nn.Module.__call__`, which
wraps your `forward` with the module machinery — forward/backward **hooks**
(used by debuggers, profilers, feature extractors), and internal bookkeeping
that tooling relies on. Calling `model.forward(x)` directly skips all of it.
Today that might cost you nothing; the day you attach a hook to inspect
activations (chapter 8 uses this for NaN hunting) or hand the model to a
library that registers hooks, the direct-`forward` call site becomes a bug
that's very hard to spot.

**Rule: define `forward`, call `model(x)`. No exceptions worth learning.**

---

# 7: model.apply and Parameter Counting

## model.apply

`model.apply(fn)` walks the module tree and calls `fn(submodule)` on **every
node**, children first. It is the idiomatic way to run type-dispatched
initialization over a whole model:

```
def init_weights(module):
    if isinstance(module, nn.Linear):
        with torch.no_grad():
            module.weight.normal_(0.0, module.in_features ** -0.5)
            module.bias.zero_()

model.apply(init_weights)        # hits every Linear at every depth
```

## Reading Parameter Names

`model.named_parameters()` yields `(name, tensor)` pairs where the name is
the **path through the attribute tree**:

```
"layers.2.0.weight"
  layers   → self.layers (a ModuleList)
  2        → its third entry (a Sequential)
  0        → that Sequential's first module (a Linear)
  weight   → the Linear's weight Parameter
```

Being able to read these paths is what makes checkpoint surgery (chapter 8)
and selective freezing (next section) possible. The standard counting
utility is three lines and worth having memorized:

```
def count_parameters(model, trainable_only=False):
    return sum(p.numel() for p in model.parameters()
               if p.requires_grad or not trainable_only)
```

---

# 8: Freezing Layers for Fine-Tuning

## The Problem It Solves

Fine-tuning usually means: keep a large pretrained body fixed, train a small
new head. "Fixed" must mean *provably fixed* — no gradients computed, no
optimizer updates — or you are silently fine-tuning everything at 100× the
memory cost.

## The Tool (and the Famous Non-Tool)

Freezing is chapter 3's fourth gradient-stopper applied per submodule:

```
for param in model.encoder.parameters():
    param.requires_grad_(False)

optimizer = torch.optim.AdamW(
    (p for p in model.parameters() if p.requires_grad),   # only the payroll's active part
    lr=1e-4,
)
```

**The misconception to kill permanently: `model.eval()` does not freeze
anything.** `eval()` switches *behavioral* modes — dropout stops dropping,
norm layers use running statistics (chapter 5) — but gradients still flow
and the optimizer still updates every parameter. A model can be in `eval()`
mode and training its weights at the same time; exercise 7 proves it.

| | gradients still computed? | optimizer still updates? | what it actually changes |
|---|---|---|---|
| `model.eval()` | **yes** | **yes** | dropout/norm behavior only |
| `requires_grad_(False)` | no | no | freezing — the real thing |

## Key Takeaways for Section 8

Freeze with `requires_grad_(False)` per parameter/submodule, then build the
optimizer over only the still-requiring parameters. `eval()` is about layer
*behavior*, never about freezing.

---

# 9: Key Takeaways + Master Decision Table

`nn.Module` is an accounting system: what it registers, it trains, moves,
and saves; what it doesn't register does not exist. Every pattern in this
chapter is about getting the right state onto the right list.

| I want to... | Reach for | Why |
|---|---|---|
| A learnable tensor | `nn.Parameter` | payroll + inventory |
| Fixed model state (masks, positional tables) | `register_buffer` | inventory only — saved & moved, no grads |
| Plain configuration values | ordinary attributes | not tensor state |
| A straight-pipe stack | `nn.Sequential` | forward for free |
| Residuals / per-layer logic / collect activations | `nn.ModuleList` + hand-written loop | registration without a fixed pipe |
| Named, runtime-selected branches | `nn.ModuleDict` | `self.heads[task]` |
| Store layers in a plain Python list | — never | zero registered parameters, silent failure |
| Run the model | `model(x)` | hooks + machinery; never `.forward(x)` directly |
| Initialize a whole tree by layer type | `model.apply(fn)` + `no_grad` + `isinstance` | recursive, idiomatic |
| Keep signal variance stable through depth | $\sigma_w = 1/\sqrt{d_{\text{in}}}$-style init | variance grows with width otherwise |
| Count / audit what will train | `count_parameters`, `named_parameters()` | paths reveal the tree |
| Freeze a body for fine-tuning | `requires_grad_(False)` + optimizer over requiring params | provably fixed |
| "Freeze" via `model.eval()` | — never | eval changes behavior, not trainability |

**Connection forward:** you can now *assemble* models. Chapter 5 fills the
toolbox with the specific layers NLP models are assembled from — `Embedding`,
`LayerNorm`, `Dropout`, the activation zoo — and the loss functions that
train them, each with its own decision guide.
