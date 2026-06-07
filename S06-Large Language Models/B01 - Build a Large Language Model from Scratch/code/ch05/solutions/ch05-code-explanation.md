# Chapter 5 Code Explanation — Pretraining on Unlabeled Data

This document walks through every code cell of `ch05.ipynb` from Sebastian Raschka's *Build a Large Language Model From Scratch*. Chapter 5 is where the GPT model you assembled in chapter 4 finally gets *trained* — first from scratch on a tiny short story, then by loading OpenAI's actual pretrained GPT-2 weights so the model can produce coherent English.

The five book sections covered are:

* **5.1 Evaluating generative text models** — cross-entropy loss, perplexity, training/validation data loaders, and computing the initial loss before training.
* **5.2 Training an LLM** — the full training loop with `AdamW`, per-step evaluation, and per-epoch sample generation.
* **5.3 Decoding strategies** — temperature scaling, top-k filtering, and a new `generate` function that combines both.
* **5.4 Saving and loading model weights** — `state_dict`, checkpointing the optimizer too.
* **5.5 Loading pretrained weights from OpenAI** — downloading, reshaping, and copying OpenAI's GPT-2 weights into our model.

Section numbers in this document (0 → 30) match the linear flow of the notebook. Each section header also names the corresponding Raschka book subsection for cross-lookup with the notes.

---

## Table of Contents

- [0 — Notebook Setup and Imports](#0--notebook-setup-and-imports)
- [1 — Section 5.1.1: Model Setup and the Shortened Context Length](#1--section-511-model-setup-and-the-shortened-context-length)
- [2 — Section 5.1.1: text_to_token_ids and token_ids_to_text Helpers](#2--section-511-text_to_token_ids-and-token_ids_to_text-helpers)
- [3 — Section 5.1.2: The Training Pair — inputs and targets](#3--section-512-the-training-pair--inputs-and-targets)
- [4 — Section 5.1.2: Logits and the Softmax Probabilities](#4--section-512-logits-and-the-softmax-probabilities)
- [5 — Section 5.1.2: Argmax Predictions vs Targets](#5--section-512-argmax-predictions-vs-targets)
- [6 — Section 5.1.2: Pulling Target-Token Probabilities (Fancy Indexing)](#6--section-512-pulling-target-token-probabilities-fancy-indexing)
- [7 — Section 5.1.2: From Probabilities to Log-Probs to Loss](#7--section-512-from-probabilities-to-log-probs-to-loss)
- [8 — Section 5.1.2: PyTorch's cross_entropy Function](#8--section-512-pytorchs-cross_entropy-function)
- [9 — Section 5.1.2: Perplexity](#9--section-512-perplexity)
- [10 — Section 5.1.3: Loading the Training Text (the-verdict.txt)](#10--section-513-loading-the-training-text-the-verdicttxt)
- [11 — Section 5.1.3: Train/Val Split and DataLoaders](#11--section-513-trainval-split-and-dataloaders)
- [12 — Section 5.1.3: Sanity Checks on the Loaders](#12--section-513-sanity-checks-on-the-loaders)
- [13 — Section 5.1.3: calc_loss_batch and calc_loss_loader](#13--section-513-calc_loss_batch-and-calc_loss_loader)
- [14 — Section 5.1.3: Picking a Device and the Initial Loss](#14--section-513-picking-a-device-and-the-initial-loss)
- [15 — Section 5.2: The Training Loop — train_model_simple](#15--section-52-the-training-loop--train_model_simple)
- [16 — Section 5.2: Running the 10-Epoch Training](#16--section-52-running-the-10-epoch-training)
- [17 — Section 5.2: Plotting Train and Validation Loss Curves](#17--section-52-plotting-train-and-validation-loss-curves)
- [18 — Section 5.3.1: Why Greedy Decoding Is Deterministic](#18--section-531-why-greedy-decoding-is-deterministic)
- [19 — Section 5.3.1: Multinomial Sampling](#19--section-531-multinomial-sampling)
- [20 — Section 5.3.1: Temperature Scaling](#20--section-531-temperature-scaling)
- [21 — Section 5.3.2: Top-k Filtering](#21--section-532-top-k-filtering)
- [22 — Section 5.3.3: The Full generate() Function](#22--section-533-the-full-generate-function)
- [23 — Section 5.4: Saving and Loading the Model state_dict](#23--section-54-saving-and-loading-the-model-state_dict)
- [24 — Section 5.4: Checkpointing the Optimizer Too](#24--section-54-checkpointing-the-optimizer-too)
- [25 — Section 5.5: Downloading OpenAI's GPT-2 Weights](#25--section-55-downloading-openais-gpt-2-weights)
- [26 — Section 5.5: Inspecting the Parameter Dictionary](#26--section-55-inspecting-the-parameter-dictionary)
- [27 — Section 5.5: Reconfiguring the Model for GPT-2 Architecture](#27--section-55-reconfiguring-the-model-for-gpt-2-architecture)
- [28 — Section 5.5: The assign() Helper](#28--section-55-the-assign-helper)
- [29 — Section 5.5: Loading OpenAI's Weights Into Our Model](#29--section-55-loading-openais-weights-into-our-model)
- [30 — Section 5.5: Generating Text With Pretrained Weights](#30--section-55-generating-text-with-pretrained-weights)

---

## 0 — Notebook Setup and Imports

```python
from importlib.metadata import version

pkgs = ["matplotlib", "numpy", "tiktoken", "torch", "tensorflow"]
for p in pkgs:
    print(f"{p} version: {version(p)}")
```

Five dependencies show up across the chapter:

* **`torch`** — every layer, the optimizer (`AdamW`), the loss (`cross_entropy`), and `torch.multinomial` for sampling.
* **`tiktoken`** — OpenAI's BPE tokenizer for `gpt2`. Identical to what you used in chapters 2–4.
* **`numpy`** — only used once, when loading OpenAI's TensorFlow checkpoints. The downloaded weights come back as numpy arrays and need a `.T` (transpose) before going into PyTorch.
* **`matplotlib`** — for the loss curve plot in section 17 and the temperature comparison bar chart in section 20.
* **`tensorflow`** — surprising but necessary: OpenAI released GPT-2 weights as TensorFlow checkpoints. The `gpt_download.py` helper script in section 25 uses `tf.train.list_variables` and `tf.train.load_variable` to read them.

If you only care about training the small model from scratch and never plan to load OpenAI's weights, you can skip tensorflow — but doing so means missing the highlight of the chapter (coherent generation from a real pretrained model).

---

## 1 — Section 5.1.1: Model Setup and the Shortened Context Length

```python
import torch
from previous_chapters import GPTModel

GPT_CONFIG_124M = {
    "vocab_size":     50257,
    "context_length": 256,      # ← shortened from 1024 in chapter 4
    "emb_dim":        768,
    "n_heads":        12,
    "n_layers":       12,
    "drop_rate":      0.1,
    "qkv_bias":       False
}

torch.manual_seed(123)
model = GPTModel(GPT_CONFIG_124M)
model.eval()   # disable dropout for the first generation demo
```

This is the same `GPTModel` class you built in chapter 4 (imported here from `previous_chapters.py`) with **one critical change**: `context_length` is now **256 instead of 1024**.

### Why 256 and not 1024?

The training data for this chapter is *one short story* ("The Verdict") with only about 5,145 tokens. Training a model with a 1024-token context window on this text would give you only ~5 training samples — not enough to learn anything. With `context_length=256` the same text yields ~20 samples, which is still tiny but workable for a demo.

This is a **memory/data trade-off**, not a model-architecture change. The same `GPTModel` class supports any context length up to whatever the position-embedding table can hold. We rebuild the model from scratch later in section 27 with the full 1024 context when loading OpenAI's pretrained weights.

### Memory implications of the change

Attention memory scales as $O(\text{context\_length}^2 \times \text{n\_layers})$. Reducing the context from 1024 to 256 cuts attention memory by **16×**. That's the difference between this notebook fitting comfortably on a 4 GB laptop GPU and not running at all.

### Why `model.eval()` here?

The `.eval()` call switches `nn.Dropout` to a no-op. Dropout is great during training (it regularises) but we want **deterministic** outputs for the demo generation that follows. Calling `.eval()` ensures the printed text matches the book's output exactly.

The trailing semicolon (`model.eval();`) is purely cosmetic — it suppresses Jupyter from displaying the returned reference to the model object. Without it you would see a noisy printout of every layer.

---

## 2 — Section 5.1.1: text_to_token_ids and token_ids_to_text Helpers

```python
import tiktoken
from previous_chapters import generate_text_simple

def text_to_token_ids(text, tokenizer):
    encoded = tokenizer.encode(text, allowed_special={'<|endoftext|>'})
    encoded_tensor = torch.tensor(encoded).unsqueeze(0)   # add batch dim
    return encoded_tensor

def token_ids_to_text(token_ids, tokenizer):
    flat = token_ids.squeeze(0)   # drop batch dim
    return tokenizer.decode(flat.tolist())

start_context = "Every effort moves you"
tokenizer = tiktoken.get_encoding("gpt2")

token_ids = generate_text_simple(
    model=model,
    idx=text_to_token_ids(start_context, tokenizer),
    max_new_tokens=10,
    context_size=GPT_CONFIG_124M["context_length"]
)

print("Output text:\n", token_ids_to_text(token_ids, tokenizer))
```

These two helpers are nothing more than convenience wrappers — but they will appear in every other section, so it's worth understanding them in detail.

### `text_to_token_ids` — string in, batched tensor out

```
"Every effort moves you"
       │
       ▼
tokenizer.encode  →  [6109, 3626, 6100, 345]    # list[int]
       │
       ▼
torch.tensor(...)  →  tensor([6109, 3626, 6100, 345])     # shape (4,)
       │
       ▼
.unsqueeze(0)      →  tensor([[6109, 3626, 6100, 345]])   # shape (1, 4)
```

The `.unsqueeze(0)` is non-negotiable. The model expects `(batch, seq_len)` — even a batch of one. Without it, the model would interpret the 1-D tensor as `(seq_len,)`, mistake `seq_len` for `batch`, and crash on the very first matmul.

### `allowed_special={'<|endoftext|>'}` — what is it?

GPT-2's tokenizer treats `<|endoftext|>` (token id `50256`) as a **special token**. By default `tiktoken` refuses to encode it inside arbitrary input text, raising an error like "Encountered text corresponding to disallowed special token." Setting `allowed_special={'<|endoftext|>'}` whitelists it — useful when you want to deliberately insert document boundaries during pretraining. For this demo it makes no difference because the prompt doesn't contain that token.

### `token_ids_to_text` — the inverse

```
tensor([[6109, 3626, 6100, 345, <new>, <new>, ...]])   # (1, n)
       │
       ▼
.squeeze(0)        →  tensor([6109, 3626, ..., <new>])    # (n,)
       │
       ▼
.tolist()          →  [6109, 3626, ..., <new>]            # python list
       │
       ▼
tokenizer.decode   →  "Every effort moves you ..."        # string
```

The `.squeeze(0)` matches the `.unsqueeze(0)` from the encoder — drop the batch dimension we added earlier. `.tolist()` converts the tensor to a python list because `tokenizer.decode` doesn't accept torch tensors.

### What the printed output looks like

Since the model is untrained, the 10 generated tokens are essentially random argmax picks. The book's run produces something like `"Every effort moves you rentingetic wasn?? refres RexMeCHicular stren"`. Yours will differ slightly depending on PyTorch version and platform but will be equally nonsensical.

---

## 3 — Section 5.1.2: The Training Pair — inputs and targets

```python
inputs = torch.tensor([[16833, 3626, 6100],   # ["every effort moves",
                       [40,    1107,  588]])  #  "I really like"]

targets = torch.tensor([[3626, 6100,  345],   # [" effort moves you",
                        [1107,  588, 11311]]) #  " really like chocolate"]
```

### What the columns mean

For row 0:

| Position | Input token | Target (what we want predicted next) |
|----------|------------|--------------------------------------|
| 0 | `16833 = "every"` | `3626 = " effort"` |
| 1 | `3626 = " effort"` | `6100 = " moves"` |
| 2 | `6100 = " moves"` | `345 = " you"` |

This is the **next-token prediction** task in its cleanest form. Each column of `targets` is the column of `inputs` shifted left by one. The model sees `[every, effort, moves]` and we expect the predictions at those three positions to be `[effort, moves, you]` respectively.

### Why this is a "shift-by-one" task

GPT models are **causal language models**. They predict each token from the tokens that came before. To train this, given a sequence `[t0, t1, t2, t3]` we feed `[t0, t1, t2]` as input and `[t1, t2, t3]` as target. Every input position has its own target — that's why we get $T$ training signals per sequence of length $T$, not just one.

### Why the leading space on `" effort"` etc.

GPT-2 BPE treats the leading space as part of the token. The string `"effort"` (no space) and `" effort"` (with space) are **different tokens** with different ids. The encoder uses this trick to recover word boundaries during decoding without a separate whitespace token.

---

## 4 — Section 5.1.2: Logits and the Softmax Probabilities

```python
with torch.no_grad():
    logits = model(inputs)

probas = torch.softmax(logits, dim=-1)
print(probas.shape)  # (batch_size, num_tokens, vocab_size)
```

Expected output:

```
torch.Size([2, 3, 50257])
```

### What the model produced

For each of the `2 × 3 = 6` input positions, the model returned a `50257`-dim **logit vector** — one logit per vocabulary entry. Softmax along the last dim turns each logit vector into a probability distribution over the full vocabulary:

$$\text{probas}[b, t, v] = \frac{e^{\text{logits}[b, t, v]}}{\sum_{v'} e^{\text{logits}[b, t, v']}}$$

The constraint $\sum_v \text{probas}[b, t, v] = 1$ holds for every $(b, t)$ pair.

### Why `torch.no_grad()`?

We are not training — we are just inspecting the model's predictions. `torch.no_grad()` disables autograd's bookkeeping: PyTorch doesn't record this forward pass for a potential backward pass, so it can free intermediate activations as soon as they are consumed. For a 124M model this saves several hundred MB of VRAM.

### Why softmax of an untrained model is uniform-ish

Before training, every logit is essentially random with similar magnitudes — roughly $\mathcal{N}(0, 1)$ from the initialisation. Softmax of nearly-equal logits gives a nearly-uniform distribution: $\text{probas}[b, t, v] \approx 1/50257 \approx 2 \times 10^{-5}$. The model has no preference for any token. Training will push the distribution to be peaked around the correct next token.

---

## 5 — Section 5.1.2: Argmax Predictions vs Targets

```python
token_ids = torch.argmax(probas, dim=-1, keepdim=True)
print("Token IDs:\n", token_ids)
```

Expected output:

```
Token IDs:
 tensor([[[16657],
          [  339],
          [42826]],

         [[49906],
          [29669],
          [41751]]])
```

### What `argmax(dim=-1, keepdim=True)` returns

For each `(batch, position)` pair, pick the index of the maximum logit. With `keepdim=True` the result keeps the reduced dimension as size 1, so the shape stays `(batch=2, num_tokens=3, 1)` instead of collapsing to `(2, 3)`. This means each "predicted token" is wrapped in its own list — a quirk that doesn't matter for any downstream computation here but lets us reuse the tensor's broadcasting shape later.

### Comparing predictions to targets

```python
print(f"Targets batch 1: {token_ids_to_text(targets[0], tokenizer)}")
print(f"Outputs batch 1: {token_ids_to_text(token_ids[0].flatten(), tokenizer)}")
```

Expected:

```
Targets batch 1:  effort moves you
Outputs batch 1: Armed heNetflix
```

The predictions are gibberish — three arbitrary words from the vocabulary, completely unrelated to the targets. This is exactly what we expected for an untrained model. The point of this exercise is to set up the *measurement* problem: how do we quantify how wrong these predictions are, so the optimiser has a number to minimise? That's what cross-entropy answers.

### Why `.flatten()` on `token_ids[0]`?

`token_ids[0]` has shape `(3, 1)` because of `keepdim=True` in the previous cell. `tokenizer.decode` wants a 1-D list, so `.flatten()` collapses `(3, 1)` to `(3,)` before `.tolist()` is called inside `token_ids_to_text`.

---

## 6 — Section 5.1.2: Pulling Target-Token Probabilities (Fancy Indexing)

```python
text_idx = 0
target_probas_1 = probas[text_idx, [0, 1, 2], targets[text_idx]]
print("Text 1:", target_probas_1)

text_idx = 1
target_probas_2 = probas[text_idx, [0, 1, 2], targets[text_idx]]
print("Text 2:", target_probas_2)
```

### What this advanced indexing does

`probas` has shape `(2, 3, 50257)`. We want to pull out the probabilities the model assigned to the **correct** next token at each of the 6 positions — *not* the argmax probabilities, but the probabilities of whatever happened to be the right answer.

The indexing expression `probas[text_idx, [0, 1, 2], targets[text_idx]]` triggers PyTorch's **fancy indexing**. It is equivalent to:

```python
probas[text_idx, 0, targets[text_idx, 0]],  # prob the model assigned to target at position 0
probas[text_idx, 1, targets[text_idx, 1]],  # prob the model assigned to target at position 1
probas[text_idx, 2, targets[text_idx, 2]],  # prob the model assigned to target at position 2
```

Three scalars, returned as a 1-D tensor of length 3.

### Dry-run

For row 0, `targets[0] = [3626, 6100, 345]`. The indexing pulls:

* `probas[0, 0, 3626]` — probability the model assigned to token `3626 (" effort")` at position 0
* `probas[0, 1, 6100]` — probability for `6100 (" moves")` at position 1
* `probas[0, 2, 345]` — probability for `345 (" you")` at position 2

The output (approximately):

```
Text 1: tensor([7.4541e-05, 3.1061e-05, 1.1563e-05])
```

These are *tiny* — around $10^{-5}$ — which is exactly the uniform prior $1/50257 \approx 2 \times 10^{-5}$. The model hasn't learned anything, so it gives the correct answer no more probability than any random vocabulary token.

### Why this matters for the loss

These six probabilities are **what we want to push toward 1 during training**. Cross-entropy is built directly on them: it measures $-\log$ of each, sums them, and divides by the count. Training drives the loss down by making the model assign more probability to the correct token at each position.

---

## 7 — Section 5.1.2: From Probabilities to Log-Probs to Loss

The next three cells walk through cross-entropy by hand, one step at a time:

```python
# Step 1: concatenate the 6 target probabilities and take their log
log_probas = torch.log(torch.cat((target_probas_1, target_probas_2)))
print(log_probas)
# tensor([-9.5042, -10.3796, -11.3677, -11.4798, -9.7764, -12.2561])

# Step 2: average them
avg_log_probas = torch.mean(log_probas)
print(avg_log_probas)
# tensor(-10.7940)

# Step 3: flip the sign — this is the loss
neg_avg_log_probas = avg_log_probas * -1
print(neg_avg_log_probas)
# tensor(10.7940)
```

### The math we just executed

For a single $(prompt, target)$ pair the next-token loss is:

$$L = -\frac{1}{N} \sum_{i=1}^{N} \log P(\text{target}_i \mid \text{prompt}_i)$$

where $N = 6$ is the total number of `(batch, position)` pairs in this toy example.

### Why log and not the probability directly?

Three intertwined reasons:

1. **Log turns products into sums.** Probabilities of independent events multiply; their logs add. This matters because we want to combine the loss across 6 positions, and addition is computationally and numerically much friendlier than multiplication of many small numbers.
2. **Numerical stability.** The raw target probabilities are around $10^{-5}$. Multiplying six of them gives $10^{-30}$ — well past the precision of float32. Their logs are merely $-10$ to $-12$, easily representable.
3. **Convexity / nicer gradients.** Cross-entropy (the negative log) is **convex** in the predicted distribution; gradient descent on it has a single global minimum. The plain probability has a flat top near 1 — gradients vanish exactly where you want learning to slow down.

### Why negate?

Optimisers **minimise** a quantity. We want the model to **maximise** the probability it assigns to the correct token. Mathematically these are equivalent if you flip the sign — minimising $-\log P$ is identical to maximising $\log P$, which is identical to maximising $P$.

The convention "loss = negative log probability" became standard because all PyTorch / TensorFlow / JAX optimisers want a scalar to descend on.

---

## 8 — Section 5.1.2: PyTorch's cross_entropy Function

```python
# First, peek at the shapes we currently have
print("Logits shape:",  logits.shape)    # (2, 3, 50257)
print("Targets shape:", targets.shape)   # (2, 3)

# cross_entropy wants 2D logits and 1D targets
logits_flat  = logits.flatten(0, 1)      # (6, 50257)
targets_flat = targets.flatten()         # (6,)

print("Flattened logits:",  logits_flat.shape)
print("Flattened targets:", targets_flat.shape)

loss = torch.nn.functional.cross_entropy(logits_flat, targets_flat)
print(loss)   # tensor(10.7940)
```

### Why we have to flatten

PyTorch's `cross_entropy` was designed for image classification: input shape `(batch_size, num_classes)`, target shape `(batch_size,)`. For a language model the equivalent treats each `(batch, position)` pair as a separate "sample":

```
logits:  (batch=2, num_tokens=3, vocab=50257)
            └─────────┬─────────┘
                      ▼
                .flatten(0, 1)
                      │
                      ▼
        logits_flat: (6, 50257)   ← 6 samples, 50257 classes each

targets: (batch=2, num_tokens=3)
                      │
                      ▼
                .flatten()
                      │
                      ▼
        targets_flat: (6,)         ← 6 sample labels
```

`.flatten(0, 1)` merges dims 0 and 1 into one. `.flatten()` without arguments merges *all* dims.

### What cross_entropy is doing internally

For each sample $i$ in the flat batch:

$$L_i = -\log\!\left(\frac{e^{\text{logits}[i, \text{target}_i]}}{\sum_v e^{\text{logits}[i, v]}}\right) = -\text{logits}[i, \text{target}_i] + \log\sum_v e^{\text{logits}[i, v]}$$

The final returned value is the **mean** over all $N$ samples:

$$L = \frac{1}{N} \sum_{i=1}^{N} L_i$$

### Why not just call `softmax + log + negate` like we did manually?

Two reasons PyTorch's `cross_entropy` is preferred over the hand-built version:

1. **Numerical stability** — internally it uses the "log-sum-exp" trick (subtract the row-wise max from the logits before exponentiating) to avoid `inf` when any logit is very large.
2. **Speed** — it's a single fused CUDA kernel instead of three separate ones (softmax → log → gather).

The result we get back, `10.7940`, **exactly matches** what we computed by hand. Cross-entropy is not magic — it's just the same negative-average-log-probability calculation, wrapped in a fast and stable kernel.

---

## 9 — Section 5.1.2: Perplexity

```python
perplexity = torch.exp(loss)
print(perplexity)   # tensor(48725.8203)
```

### Definition

Perplexity is simply the exponential of the cross-entropy loss:

$$\text{PPL} = e^L = e^{-\frac{1}{N}\sum_i \log P(\text{target}_i)}$$

### Why bother — what does it tell you that loss doesn't?

Perplexity has a much more **intuitive interpretation**: it is the *effective vocabulary size* the model is choosing from at each step.

* **PPL = 1** → the model is 100% certain of the correct answer every time. Perfect.
* **PPL = 48,725** → the model is behaving as if it's choosing uniformly among about 49,000 equally likely tokens. With a vocabulary of 50,257, this means the model is essentially at maximum confusion — exactly what we expect for a fresh, untrained network.
* **PPL ≈ 20–50** → typical for a well-trained GPT-2-style model on its training distribution.

The relationship between loss and perplexity is **exponential**, so small differences in loss can be dramatic in perplexity terms:

| Loss | Perplexity |
|------|-----------|
| 0.0 | 1.0 |
| 1.0 | 2.7 |
| 3.0 | 20.1 |
| 5.0 | 148 |
| 10.8 | 48,725 |
| log(50257) ≈ 10.82 | 50,257 (uniform — max possible) |

When the chapter trains the model for 10 epochs, you'll see loss drop from ~10.8 to ~0.4 — perplexity from 48,725 down to ~1.5. That's the model essentially memorising the short story (we'll see why this is overfitting in section 17).

---

## 10 — Section 5.1.3: Loading the Training Text (the-verdict.txt)

```python
import os, requests

file_path = "the-verdict.txt"
url = "https://raw.githubusercontent.com/rasbt/.../the-verdict.txt"

if not os.path.exists(file_path):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    text_data = response.text
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text_data)
else:
    with open(file_path, "r", encoding="utf-8") as file:
        text_data = file.read()
```

### Why a single short story?

The book deliberately chose a tiny dataset — Edith Wharton's *The Verdict*, about 20 KB of text — for three reasons:

1. **Speed.** Training a 124M model on a real corpus (millions of tokens) takes hours on a GPU. With ~5,000 tokens, training to convergence takes a couple of minutes.
2. **Reproducibility.** A small fixed text means the loss curve is identical for every reader. With a stochastic, web-scraped corpus, results would diverge.
3. **It's a learning artefact, not a research artefact.** Section 17 will explicitly point out that this is severe overfitting — the model is memorising one short story, not learning general English. This is fine for pedagogy because the *training mechanics* are the focus, not the resulting language ability. Real language ability comes from loading OpenAI's pretrained weights in section 5.5.

### Quick sanity checks

```python
print(text_data[:99])     # first 99 chars — should start "I HAD always thought ..."
print(text_data[-99:])    # last 99 chars — story ends mid-paragraph

total_characters = len(text_data)
total_tokens     = len(tokenizer.encode(text_data))
print("Characters:", total_characters)   # ~20,479
print("Tokens:",     total_tokens)       # 5,145
```

### Character vs token ratio

20,479 characters tokenise to 5,145 tokens — a ratio of about **4 characters per BPE token**, which is the universal rule of thumb for English text in GPT-2's tokenizer. This conversion is helpful when budgeting context windows: a 1024-token context can hold roughly 4,000 characters of English (≈ 800 words).

---

## 11 — Section 5.1.3: Train/Val Split and DataLoaders

```python
from previous_chapters import create_dataloader_v1

train_ratio = 0.90
split_idx = int(train_ratio * len(text_data))
train_data = text_data[:split_idx]
val_data   = text_data[split_idx:]

torch.manual_seed(123)

train_loader = create_dataloader_v1(
    train_data,
    batch_size=2,
    max_length=GPT_CONFIG_124M["context_length"],   # 256
    stride=GPT_CONFIG_124M["context_length"],       # also 256 — no overlap
    drop_last=True,
    shuffle=True,
    num_workers=0,
)

val_loader = create_dataloader_v1(
    val_data,
    batch_size=2,
    max_length=GPT_CONFIG_124M["context_length"],
    stride=GPT_CONFIG_124M["context_length"],
    drop_last=False,
    shuffle=False,
    num_workers=0,
)
```

### What `create_dataloader_v1` does (recap from chapter 2)

It takes a long text string, tokenises it, and slides a window of `max_length` tokens across it with step `stride`. Each window becomes one input sequence; the corresponding target sequence is the same window shifted by one token to the right. The resulting `(input, target)` pairs are wrapped in a PyTorch `DataLoader` that yields them in batches.

### Why `stride == max_length` (non-overlapping windows)?

Two valid strategies exist:

* **stride == max_length** (used here) — every token appears in exactly one training sample. Cheaper, less data, no information seen twice per epoch.
* **stride < max_length** — windows overlap. Same token can appear in multiple training samples in different positions. More training data per epoch, but the model sees the same token multiple times per epoch — risk of overfitting.

For this tiny dataset, non-overlapping windows are perfectly fine. With ~5,000 tokens and `max_length=256`, we get **~20 windows per epoch**, which is meaningful with batch size 2.

### Why `drop_last=True` for train but `False` for val?

* **train:** `drop_last=True` discards an incomplete final batch. Adam's gradient statistics misbehave on batches of different sizes during training (the variance estimate gets noisier).
* **val:** `drop_last=False` keeps the last partial batch — we want to evaluate on *all* validation samples, not throw away a few.

### `shuffle=True` for train, `False` for val

* **train:** shuffling prevents the model from memorising the order of samples and helps each batch be a random sub-sample of the training distribution.
* **val:** unshuffled because the validation loss should be deterministic for fair comparison across epochs.

### `num_workers=0`

Use the main Python process to load data instead of forking helper processes. For a 20 KB text file, parallel data loading is pointless and the fork overhead would dominate. For large datasets you would bump this up to 4 or 8 to keep the GPU fed.

### `torch.manual_seed(123)` before creating loaders

Because `shuffle=True` uses an internal random number generator, seeding before creating the train loader pins the shuffle order. This makes every epoch reproducible.

---

## 12 — Section 5.1.3: Sanity Checks on the Loaders

```python
if total_tokens * train_ratio < GPT_CONFIG_124M["context_length"]:
    print("Not enough tokens for the training loader. ...")

if total_tokens * (1 - train_ratio) < GPT_CONFIG_124M["context_length"]:
    print("Not enough tokens for the validation loader. ...")
```

A defensive check. With `total_tokens = 5145`, `train_ratio = 0.9`, `context_length = 256`:

* Train tokens: $5145 \times 0.9 = 4630$, comfortably $\geq 256$. ✓
* Val tokens: $5145 \times 0.1 = 515$, also $\geq 256$. ✓

If either inequality flipped (e.g. if you increased `context_length` to 4096), the corresponding loader would yield zero batches and training would silently fail. The check prints a helpful message instead.

### Inspecting the actual batches produced

```python
print("Train loader:")
for x, y in train_loader:
    print(x.shape, y.shape)
```

Expected output:

```
Train loader:
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])
torch.Size([2, 256]) torch.Size([2, 256])

Validation loader:
torch.Size([2, 256]) torch.Size([2, 256])
```

Train loader yields **9 batches × 2 samples × 256 tokens = 4608 tokens** (close to the 4630 we predicted; the difference is the final partial batch that got dropped). Val loader yields **1 batch × 2 samples × 256 tokens = 512 tokens** of the 515 available.

---

## 13 — Section 5.1.3: calc_loss_batch and calc_loss_loader

```python
def calc_loss_batch(input_batch, target_batch, model, device):
    input_batch, target_batch = input_batch.to(device), target_batch.to(device)
    logits = model(input_batch)
    loss = torch.nn.functional.cross_entropy(
        logits.flatten(0, 1), target_batch.flatten()
    )
    return loss


def calc_loss_loader(data_loader, model, device, num_batches=None):
    total_loss = 0.
    if len(data_loader) == 0:
        return float("nan")
    elif num_batches is None:
        num_batches = len(data_loader)
    else:
        num_batches = min(num_batches, len(data_loader))

    for i, (input_batch, target_batch) in enumerate(data_loader):
        if i < num_batches:
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            total_loss += loss.item()
        else:
            break

    return total_loss / num_batches
```

These two utilities will be called from the training loop dozens of times per epoch — bundling them as functions keeps the loop readable.

### `calc_loss_batch` — one batch, one scalar loss

Identical mathematically to what we did manually in section 8: forward through the model, flatten logits + targets, run `cross_entropy`. The only addition is the `.to(device)` calls that move the batch to GPU (if available) before computation.

### Why `.to(device)` is inside this function, not in the loader

You could move data to the device inside the `DataLoader` (via a custom `collate_fn`). Putting it inside `calc_loss_batch` is more flexible: the same function works on any device, and you can call it on CPU for debugging without changing the loader.

### `calc_loss_loader` — average loss across (sampled) batches

Two patterns this function supports:

* **`num_batches=None`** — iterate every batch in the loader. Used at the *end* of training when you want an accurate final evaluation.
* **`num_batches=5`** — stop after 5 batches. Used *during* training every `eval_freq` steps to get a quick noisy estimate of train/val loss without spending too long on evaluation.

### Why `loss.item()` and not just `loss`?

`loss` is a 0-D PyTorch tensor with autograd graph attached. `loss.item()` extracts the underlying Python float and discards the autograd graph. Summing `.item()` values into `total_loss` keeps the running tally cheap and avoids accidentally keeping a giant autograd graph alive across all batches.

### Why guard against `len(data_loader) == 0`?

If someone passes an empty loader (e.g. mis-configured train/val split), `total_loss / num_batches` would divide by zero. Returning `float("nan")` is a clear signal that something is wrong without crashing the loop.

---

## 14 — Section 5.1.3: Picking a Device and the Initial Loss

```python
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    major, minor = map(int, torch.__version__.split(".")[:2])
    if (major, minor) >= (2, 9):
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
else:
    device = torch.device("cpu")

print(f"Using {device} device.")

model.to(device)

torch.manual_seed(123)
with torch.no_grad():
    train_loss = calc_loss_loader(train_loader, model, device)
    val_loss   = calc_loss_loader(val_loader,   model, device)

print("Training loss:", train_loss)   # ~10.99
print("Validation loss:", val_loss)   # ~10.98
```

### The device selection ladder

The pattern is: prefer NVIDIA → fall back to Apple GPU → fall back to CPU.

* **`cuda`** — NVIDIA GPU. Fastest by far for training.
* **`mps`** — Apple's Metal Performance Shaders backend for M1/M2/M3 chips. The check `>= (2, 9)` exists because earlier PyTorch versions had subtle correctness bugs on MPS (e.g. for `torch.multinomial` and softmax) that produced different results from CUDA/CPU. Using MPS on older PyTorch would make your output diverge from the book's.
* **`cpu`** — works everywhere but slow.

### `model.to(device)` — no reassignment needed

For `nn.Module` instances, `.to(device)` modifies the model **in place**. You don't need to write `model = model.to(device)` like you would for a tensor. (Tensors are different — for `tensor.to(device)` you *must* reassign.)

### What the initial loss tells us

Before any training, both train and val losses are ~10.99 — essentially $\ln(50257) \approx 10.82$. As we noted in section 9, this is the loss of a uniform distribution over the full vocabulary. The model has zero predictive power. From here, training should drive the loss down — substantially on the training set, less on the validation set (overfitting). That's exactly what section 17 will show.

---

## 15 — Section 5.2: The Training Loop — train_model_simple

```python
def train_model_simple(model, train_loader, val_loader, optimizer, device,
                       num_epochs, eval_freq, eval_iter, start_context, tokenizer):
    train_losses, val_losses, track_tokens_seen = [], [], []
    tokens_seen, global_step = 0, -1

    for epoch in range(num_epochs):
        model.train()

        for input_batch, target_batch in train_loader:
            optimizer.zero_grad()
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            loss.backward()
            optimizer.step()
            tokens_seen += input_batch.numel()
            global_step += 1

            if global_step % eval_freq == 0:
                train_loss, val_loss = evaluate_model(
                    model, train_loader, val_loader, device, eval_iter
                )
                train_losses.append(train_loss)
                val_losses.append(val_loss)
                track_tokens_seen.append(tokens_seen)
                print(f"Ep {epoch+1} (Step {global_step:06d}): "
                      f"Train loss {train_loss:.3f}, Val loss {val_loss:.3f}")

        generate_and_print_sample(model, tokenizer, device, start_context)

    return train_losses, val_losses, track_tokens_seen
```

This is the **canonical PyTorch training loop**. Every neural network you'll ever train uses this same skeleton.

### The four-step optimisation rhythm

For each batch:

```
1. optimizer.zero_grad()    # clear gradients from the previous batch
2. loss = calc_loss_batch(...)
3. loss.backward()          # populate .grad on every parameter via backprop
4. optimizer.step()          # update parameters using their .grad
```

#### Why `zero_grad()` is at the *start* of the loop (not the end)?

PyTorch **accumulates** gradients across `.backward()` calls by default. This is intentional — it's what enables **gradient accumulation** (chapter 12). For standard training where every batch is a fresh update, you have to zero them yourself. Placing the call at the start (rather than after `optimizer.step()`) is slightly safer: if you ever `return` or `break` out of the loop, the gradients are reset before the next iteration of the outer loop.

#### What `loss.backward()` actually does

Autograd traversed the computation graph that was built during the forward pass (from `loss` all the way back to every parameter). At each node it applies the chain rule, accumulating gradients into the `.grad` attribute of every parameter. After this call, every weight has a gradient telling it which direction to move to reduce the loss.

#### What `optimizer.step()` actually does

For AdamW (used here): update each parameter using its `.grad`, smoothed by per-parameter momentum and variance buffers, and scaled by the learning rate. The high-level update for parameter $w$ is:

$$w \leftarrow w - \eta \cdot \hat{m} / (\sqrt{\hat{v}} + \epsilon) - \eta \cdot \lambda \cdot w$$

where $\eta$ is the learning rate, $\hat{m}$ and $\hat{v}$ are bias-corrected first and second moments of the gradients, and $\lambda$ is the weight decay coefficient.

### The bookkeeping variables

* **`tokens_seen`** — running total of how many tokens the model has been trained on. Useful as a secondary x-axis on the loss plot (section 17).
* **`global_step`** — counts every gradient update across all epochs. Used to decide *when* to evaluate (every `eval_freq` steps).

### `model.train()` at the top of each epoch

This re-enables dropout, which gets disabled inside `evaluate_model` when we set `model.eval()`. Without re-enabling it, the second epoch onwards would train without regularisation. (Not catastrophic with `drop_rate=0.1`, but the practice of pairing `eval()` with a subsequent `train()` is standard.)

### `evaluate_model` — the inner helper

```python
def evaluate_model(model, train_loader, val_loader, device, eval_iter):
    model.eval()
    with torch.no_grad():
        train_loss = calc_loss_loader(train_loader, model, device, num_batches=eval_iter)
        val_loss   = calc_loss_loader(val_loader,   model, device, num_batches=eval_iter)
    model.train()
    return train_loss, val_loss
```

* `model.eval()` — disable dropout for evaluation.
* `torch.no_grad()` — disable autograd. Evaluation doesn't need gradients; saves memory and time.
* `num_batches=eval_iter` — evaluate on only the first `eval_iter` batches, not the full loader. This makes evaluation fast (otherwise we'd be evaluating every 5 steps for as long as evaluation takes, slowing training significantly).
* `model.train()` at the end — restore training mode for the next batch.

### `generate_and_print_sample` — at the end of every epoch

```python
def generate_and_print_sample(model, tokenizer, device, start_context):
    model.eval()
    context_size = model.pos_emb.weight.shape[0]
    encoded = text_to_token_ids(start_context, tokenizer).to(device)
    with torch.no_grad():
        token_ids = generate_text_simple(
            model=model, idx=encoded,
            max_new_tokens=50, context_size=context_size
        )
    decoded_text = token_ids_to_text(token_ids, tokenizer)
    print(decoded_text.replace("\n", " "))
    model.train()
```

After each epoch, generate 50 new tokens from the prompt and print them. This is a **qualitative monitor**: it lets you visually confirm the model is improving by watching the output progress from random gibberish to recognisable English fragments to (eventually) verbatim text from the training story.

### Why `context_size = model.pos_emb.weight.shape[0]`?

Instead of hard-coding 256, this reads the actual size of the positional embedding table from the model itself. If you ever swap in a different model (like the GPT-2 with 1024 context in section 27), this code keeps working without modification.

---

## 16 — Section 5.2: Running the 10-Epoch Training

```python
torch.manual_seed(123)
model = GPTModel(GPT_CONFIG_124M)
model.to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr=0.0004, weight_decay=0.1)

num_epochs = 10
train_losses, val_losses, tokens_seen = train_model_simple(
    model, train_loader, val_loader, optimizer, device,
    num_epochs=num_epochs, eval_freq=5, eval_iter=5,
    start_context="Every effort moves you", tokenizer=tokenizer,
)
```

### The hyperparameters that matter

#### `AdamW(lr=0.0004, weight_decay=0.1)`

**Why AdamW** — it's the de facto standard optimiser for transformers. "W" stands for "decoupled weight decay" — a fix to a subtle bug in the original Adam paper where the decay term and the adaptive learning rate interacted incorrectly. Every modern LLM (GPT, Llama, Claude) is trained with AdamW.

**Why `lr=0.0004`** — small enough that the first few updates don't destabilise the random initialisation, large enough that 10 epochs of 9 batches each (90 updates total) actually moves the loss. For comparison: SFT fine-tuning uses `2e-4`, DPO uses `1e-5`. Pretraining from random init can afford a slightly higher learning rate than fine-tuning.

**Why `weight_decay=0.1`** — encourages small weights, prevents overfitting. This is unusually high — production transformers usually use `0.01`. It's pumped up here because the training data is so small that overfitting is likely.

#### `num_epochs=10`

Ten passes over the entire training text. With 9 batches per epoch, that's 90 total gradient updates. Tiny by real-world standards but enough to see clear loss reduction.

#### `eval_freq=5`

Every 5 gradient updates, run the evaluation and log losses. With 90 total updates over 10 epochs, this gives 18 evaluation points — enough to plot a smooth loss curve.

#### `eval_iter=5`

When evaluating, use only the first 5 batches of each loader. Since the train loader only has 9 batches, this is a slight under-estimate; for the val loader (which has 1 batch) `min(eval_iter, len(loader))` clamps it to 1.

### What you see during the run

The print output evolves like this:

```
Ep 1 (Step 000000): Train loss 9.781, Val loss 9.933
Ep 1 (Step 000005): Train loss 8.111, Val loss 8.339
Every effort moves you,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,...
Ep 2 (Step 000010): Train loss 6.661, Val loss 7.048
...
Ep 5 (Step 000040): Train loss 1.422, Val loss 6.371
Every effort moves you, and the man's wife. Then I told. ...
...
Ep 10 (Step 000085): Train loss 0.391, Val loss 6.452
Every effort moves you?" "Yes--quite insensible to the irony.
She wanted him vindicated--and by me!" ...
```

Notice three patterns:

1. **Train loss drops dramatically** — from 9.78 to 0.39. The model is memorising the training text.
2. **Val loss plateaus around 6.4** — far above the train loss. This is the **overfitting gap**.
3. **Sample text becomes verbatim training text** — by epoch 10, the model is reciting passages from the story word-for-word. It hasn't learned English, it has memorised one short story.

### Why is this OK pedagogically?

The point of training from scratch on a tiny dataset is to show that the **training mechanics work** — losses go down, optimisers converge, the model learns *something*. The fact that it memorises rather than generalises is fine because we're going to load OpenAI's real pretrained weights in section 5.5 to get actual language capability.

---

## 17 — Section 5.2: Plotting Train and Validation Loss Curves

```python
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

def plot_losses(epochs_seen, tokens_seen, train_losses, val_losses):
    fig, ax1 = plt.subplots(figsize=(5, 3))
    ax1.plot(epochs_seen, train_losses, label="Training loss")
    ax1.plot(epochs_seen, val_losses, linestyle="-.", label="Validation loss")
    ax1.set_xlabel("Epochs")
    ax1.set_ylabel("Loss")
    ax1.legend(loc="upper right")
    ax1.xaxis.set_major_locator(MaxNLocator(integer=True))

    ax2 = ax1.twiny()
    ax2.plot(tokens_seen, train_losses, alpha=0)
    ax2.set_xlabel("Tokens seen")

    fig.tight_layout()
    plt.savefig("loss-plot.pdf")
    plt.show()

epochs_tensor = torch.linspace(0, num_epochs, len(train_losses))
plot_losses(epochs_tensor, tokens_seen, train_losses, val_losses)
```

### What the plot shows

Two curves on the same axes:
* **Train loss** (solid) — drops smoothly from ~10 toward ~0.4.
* **Val loss** (dashed) — drops to ~5.5 by epoch 3, then plateaus or *rises slightly* through epoch 10.

The growing gap between these two curves is the classic signature of **overfitting**: training loss keeps decreasing, validation loss stops decreasing (or starts increasing). The model is learning patterns specific to the training data that don't transfer to held-out text.

### The `ax1.twiny()` trick — dual x-axis

`ax1.twiny()` creates a *second* x-axis that shares the same y-axis. We plot `tokens_seen` against `train_losses` with `alpha=0` (invisible) just to set the x-range and tick alignment on the second axis. The visible result: bottom x-axis shows epochs (0–10), top x-axis shows tokens seen (0–~40,000).

This is a very common transformer-paper convention. Tokens seen is a more "scale-free" measure than epochs because it lets you compare runs with different batch sizes / context lengths fairly.

### `MaxNLocator(integer=True)` — clean integer ticks

Forces the x-axis to use whole integers for epoch ticks (0, 1, 2, ...) instead of fractional values (0.0, 1.5, 3.0). Purely cosmetic.

### Why overfitting is happening so aggressively here

Three reinforcing factors:

1. **Tiny training set** — ~4,600 tokens.
2. **Massive model relative to data** — 124M parameters vs 4,600 tokens. That's 27,000 parameters per token. Standard rule of thumb for pretraining: you want at least 1 token per parameter (Chinchilla scaling). We are 27,000× under-data.
3. **High capacity** — even with weight_decay=0.1, the model has more than enough capacity to memorise the entire training set.

The fix would be using a real corpus (millions of tokens) or a much smaller model. We do neither here because the goal is to demonstrate the *mechanics*, not to produce a useful model.

---

## 18 — Section 5.3.1: Why Greedy Decoding Is Deterministic

```python
inference_device = torch.device("cpu")

model.to(inference_device)
model.eval()
tokenizer = tiktoken.get_encoding("gpt2")

token_ids = generate_text_simple(
    model=model,
    idx=text_to_token_ids("Every effort moves you", tokenizer).to(inference_device),
    max_new_tokens=25,
    context_size=GPT_CONFIG_124M["context_length"]
)
print("Output text:\n", token_ids_to_text(token_ids, tokenizer))
```

### Why move to CPU for inference?

Two reasons:
1. **Determinism** — small differences between PyTorch's CUDA and MPS implementations of `torch.multinomial` and `softmax` can produce slightly different outputs on different hardware. Running on CPU eliminates this variation so every reader sees the same output.
2. **Inference is cheap** — generating 25 tokens through a 124M model is fast on CPU (< 1 second). For inference workloads at this scale, the GPU upload/download overhead can actually make CPU competitive.

### Why greedy decoding is deterministic

`generate_text_simple` uses `torch.argmax` at every step. Given the same model and the same prompt, `argmax` always returns the same index. There is no random sampling. Run the cell ten times — you get identical output every time.

This is also why greedy decoding is **boring**. The model can never explore alternative continuations even when the second-highest-probability token is nearly tied with the first. To get variety, we need sampling.

### A note on `torch.argmax` tie-breaking

In the unlikely event of an exact logit tie, PyTorch's argmax returns the **lowest index** among the tied values. This is a deterministic but somewhat arbitrary choice — the GPT-2 vocabulary order has no semantic meaning, so the resulting token is essentially random in such cases. Floating-point ties are exceedingly rare in practice, so this rarely matters.

---

## 19 — Section 5.3.1: Multinomial Sampling

```python
vocab = {
    "closer": 0, "every": 1, "effort": 2, "forward": 3,
    "inches": 4, "moves": 5, "pizza": 6, "toward": 7, "you": 8,
}
inverse_vocab = {v: k for k, v in vocab.items()}

next_token_logits = torch.tensor(
    [4.51, 0.89, -1.90, 6.75, 1.63, -1.62, -1.89, 6.28, 1.79]
)
probas = torch.softmax(next_token_logits, dim=0)
next_token_id = torch.argmax(probas).item()
print(inverse_vocab[next_token_id])    # "forward"
```

A tiny 9-word vocabulary lets us see the sampling mechanics clearly. Logits: `forward` (6.75) is highest, `toward` (6.28) is a close second. Argmax always picks `forward`.

### Switching to multinomial sampling

```python
torch.manual_seed(123)
next_token_id = torch.multinomial(probas, num_samples=1).item()
print(inverse_vocab[next_token_id])    # "forward" — but could differ with a different seed
```

`torch.multinomial(probas, num_samples=1)` draws **one** token, weighted by its probability:

* `forward` has probability ~50% → picked roughly half the time.
* `toward` has probability ~30% → picked about a third of the time.
* Each of the rest has < 5%.

Even though `forward` has the highest probability, the sampler will occasionally pick `toward` or even `inches` — that's where output variety comes from.

### Empirical demonstration

```python
def print_sampled_tokens(probas):
    torch.manual_seed(123)
    sample = [torch.multinomial(probas, num_samples=1).item() for _ in range(1_000)]
    sampled_ids = torch.bincount(torch.tensor(sample), minlength=len(probas))
    for i, freq in enumerate(sampled_ids):
        print(f"{freq} x {inverse_vocab[i]}")

print_sampled_tokens(probas)
```

Expected output:

```
73 x closer
0 x every
0 x effort
582 x forward
2 x inches
0 x moves
0 x pizza
343 x toward
0 x you
```

Out of 1000 samples: ~58% forward, ~34% toward, ~7% closer, ~0.2% inches, rest essentially never. This roughly matches the softmax probabilities (58%, 34%, 7%, ...). Drawing more samples would converge tighter to the true distribution.

### Why multinomial and not just a random uniform?

A uniform random would give each token a 1/9 chance, completely ignoring the model's confidence. Multinomial **respects the probabilities** — confident tokens get picked more often, less likely tokens get picked rarely but still occasionally. This gives controllable diversity.

---

## 20 — Section 5.3.1: Temperature Scaling

```python
def softmax_with_temperature(logits, temperature):
    scaled_logits = logits / temperature
    return torch.softmax(scaled_logits, dim=0)

temperatures = [1, 0.1, 5]
scaled_probas = [softmax_with_temperature(next_token_logits, T) for T in temperatures]
```

### The formula

$$\text{softmax}(z / T)_i = \frac{e^{z_i / T}}{\sum_j e^{z_j / T}}$$

* **T = 1** → identical to plain softmax (the `/T` is a no-op).
* **T < 1** → divides each logit by a small number, *amplifying* differences. Big logits become huge, small logits stay small. Distribution becomes **sharper** — close to argmax.
* **T > 1** → divides each logit by a large number, *compressing* differences. All logits become similar. Distribution becomes **flatter** — close to uniform.

### Dry-run with our 9-word example

Logits: `[4.51, 0.89, -1.90, 6.75, 1.63, -1.62, -1.89, 6.28, 1.79]`. Top three are `forward` (6.75), `toward` (6.28), `closer` (4.51).

| Temperature | `forward` prob | `toward` prob | `closer` prob | `inches` prob |
|-------------|----------------|---------------|---------------|---------------|
| **T = 0.1** | 0.993 | 0.007 | ~0 | ~0 |
| **T = 1.0** | 0.581 | 0.343 | 0.073 | 0.002 |
| **T = 5.0** | 0.165 | 0.149 | 0.103 | 0.058 |

The differences are dramatic. At T=0.1 the sampler is effectively greedy. At T=5 it's almost uniform over the top tokens.

### Verifying with empirical sampling

```python
print_sampled_tokens(scaled_probas[1])   # T=0.1
print_sampled_tokens(scaled_probas[2])   # T=5
```

* T=0.1 → ~993 `forward`, ~7 `toward`, 0 of everything else. Practically deterministic.
* T=5 → roughly 165 each of forward/toward/closer/inches/you — much more uniform.

### When to use which

* **T < 0.5** → use for factual / deterministic outputs (Q&A, code generation). Suppresses creativity but reduces hallucinations.
* **T = 0.7–1.0** → standard for chat. Balanced.
* **T > 1.0** → creative writing, brainstorming. More varied but more likely to drift off-topic.

### Why temperature alone isn't enough

Even at moderate temperature, the long tail of *very* low-probability tokens still gets a tiny nonzero chance. Across thousands of generation steps, those rare samples eventually fire and the model wanders into nonsense. That's why we combine temperature with top-k filtering (next section).

---

## 21 — Section 5.3.2: Top-k Filtering

```python
top_k = 3
top_logits, top_pos = torch.topk(next_token_logits, top_k)

print("Top logits:", top_logits)      # tensor([6.75, 6.28, 4.51])
print("Top positions:", top_pos)      # tensor([3, 7, 0])
```

### What `torch.topk` returns

`torch.topk(t, k)` returns a tuple `(values, indices)`:
* `values` — the k largest entries, sorted in descending order.
* `indices` — their positions in the original tensor.

For our 9-element logit vector with k=3, the top three are at positions 3 (`forward`), 7 (`toward`), 0 (`closer`).

### Masking everything else to -inf

```python
new_logits = torch.where(
    condition = next_token_logits < top_logits[-1],
    input     = torch.tensor(float("-inf")),
    other     = next_token_logits,
)
print(new_logits)
# tensor([4.510, -inf, -inf, 6.750, -inf, -inf, -inf, 6.280, -inf])
```

`torch.where(cond, a, b)` is element-wise: where `cond` is True, take `a`; where False, take `b`. We mask every logit *below* `top_logits[-1] = 4.51` (the smallest of the top-3) to `-inf`. The result: only the top-3 logits survive; all others become `-inf`.

### Why `-inf`?

Because we're about to apply softmax. $e^{-\infty} = 0$, so softmax will assign exactly **zero probability** to the masked tokens. The probability mass redistributes only among the top-k.

```python
topk_probas = torch.softmax(new_logits, dim=0)
print(topk_probas)
# tensor([0.0615, 0.0000, 0.0000, 0.5775, 0.0000, 0.0000, 0.0000, 0.3610, 0.0000])
```

Three nonzero probabilities (0.06 + 0.58 + 0.36 = 1.00), rest are 0.

### What top-k buys you

Top-k filtering **hard-rules out** the long tail of low-probability tokens. Combined with temperature, you get:

* **Top-k = 1** is identical to greedy (only the highest logit survives).
* **Top-k = 50** with high temperature is a common chat-bot default: enough variety to be interesting, but no chance of selecting one of the 50,000+ irrelevant vocabulary entries.

### Why not just use a probability threshold instead?

Two filtering strategies exist:
* **Top-k** — fixed number of tokens. Simple, deterministic count. Used in this notebook.
* **Top-p / nucleus** — keep tokens whose cumulative probability sums to at least `p` (typically 0.9 or 0.95). Adapts to the model's confidence: if the model is very confident in 2 tokens, only those 2 survive; if uncertain across 30 tokens, all 30 survive.

Top-p is generally considered slightly better because it adapts; top-k is simpler to implement and reason about. The book uses top-k for pedagogical clarity.

---

## 22 — Section 5.3.3: The Full generate() Function

```python
def generate(model, idx, max_new_tokens, context_size,
             temperature=0.0, top_k=None, eos_id=None):

    for _ in range(max_new_tokens):
        idx_cond = idx[:, -context_size:]
        with torch.no_grad():
            logits = model(idx_cond)
        logits = logits[:, -1, :]

        # Top-k filtering
        if top_k is not None:
            top_logits, _ = torch.topk(logits, top_k)
            min_val = top_logits[:, -1]
            logits = torch.where(
                logits < min_val,
                torch.tensor(float("-inf")).to(logits.device),
                logits,
            )

        # Temperature sampling
        if temperature > 0.0:
            logits = logits / temperature
            logits = logits - logits.max(dim=-1, keepdim=True).values  # mps stability
            probs = torch.softmax(logits, dim=-1)
            idx_next = torch.multinomial(probs, num_samples=1)
        else:
            idx_next = torch.argmax(logits, dim=-1, keepdim=True)

        if idx_next == eos_id:
            break

        idx = torch.cat((idx, idx_next), dim=1)

    return idx
```

This is **the** key takeaway function of the chapter. It generalises `generate_text_simple` from chapter 4 with three extra features: top-k filtering, temperature sampling, and early stopping on an end-of-sequence token.

### The branching structure

```
For each step:
    1. Crop context, forward pass, keep last position
    2. If top_k is set      → mask non-top-k logits to -inf
    3. If temperature > 0.0 → divide by T, softmax, multinomial sample
       Else                  → argmax (greedy)
    4. If next token is eos_id → break
    5. Append next token to idx
```

### The MPS stability fix

```python
logits = logits - logits.max(dim=-1, keepdim=True).values
```

This is the standard **log-sum-exp** trick. After dividing logits by `temperature`, very large logits can become huge (e.g. `6.75 / 0.1 = 67.5`), and `e^67.5` overflows even in float32. Subtracting the row-wise max before exponentiating shifts all values down so the largest is exactly 0, preventing overflow. Mathematically the softmax is unchanged (subtracting a constant from all logits doesn't affect the softmax). Numerically it's the difference between getting `nan` outputs and getting correct ones — especially on Apple's MPS backend where numerical edge cases are more common.

### The `eos_id` parameter

Pass `eos_id=tokenizer.eot_token` (50256 for GPT-2) and the loop terminates the moment the model emits the end-of-text token. Useful for sequence-to-sequence tasks where you want generation to stop at a natural endpoint rather than at a fixed `max_new_tokens`.

### Calling the full function

```python
torch.manual_seed(123)
token_ids = generate(
    model=model,
    idx=text_to_token_ids("Every effort moves you", tokenizer).to(inference_device),
    max_new_tokens=15,
    context_size=GPT_CONFIG_124M["context_length"],
    top_k=25,
    temperature=1.4,
)
print("Output text:\n", token_ids_to_text(token_ids, tokenizer))
```

With `top_k=25` and `temperature=1.4`, we get a moderate amount of variety. On the (overfit) model trained earlier, the output is still nonsensical because the model only knows the verbatim training story — but the *generation mechanics* now support real LLM-quality decoding.

---

## 23 — Section 5.4: Saving and Loading the Model state_dict

```python
torch.save(model.state_dict(), "model.pth")
```

### What is `state_dict`?

It's a Python `dict` mapping parameter names (strings like `"trf_blocks.0.att.W_query.weight"`) to their tensor values. It contains:

* Every `nn.Parameter` in the model (weights, biases, scales, shifts).
* Every persistent buffer (e.g. the causal attention mask, which is registered as a buffer rather than a parameter).

It does **not** contain:
* The model's *code* (your `GPTModel` class definition). To restore the model, you need the same class available.
* Anything about the optimiser, the loss curve, or training metadata.

### Why `state_dict` over `torch.save(model)`?

`torch.save(model)` pickles the whole Python object, including the class. If you ever rename the class or move it to a different module, the pickle can't be unpickled — your saved model is unusable. `state_dict` is **just tensors plus string keys** — portable across code refactors.

### Loading it back

```python
model = GPTModel(GPT_CONFIG_124M)   # instantiate a fresh model first

if torch.cuda.is_available(): device = torch.device("cuda")
elif torch.backends.mps.is_available(): ...
else: device = torch.device("cpu")

model.load_state_dict(torch.load("model.pth", map_location=device, weights_only=True))
model.eval()
```

Three things to notice:

* **You need a fresh `GPTModel` instance first** — the `state_dict` has no notion of the class. You instantiate with the same config, then overwrite the random weights with the saved ones.
* **`map_location=device`** — controls where the loaded tensors land. Without it, a `.pth` saved on a CUDA machine would try to recreate CUDA tensors when loaded on a CPU-only machine and fail. `map_location` redirects them to the right device.
* **`weights_only=True`** — security flag (default `False` in PyTorch < 2.6, default `True` in 2.6+). Tells PyTorch to refuse to unpickle anything except tensors and basic Python types. Without this, a malicious `.pth` file could execute arbitrary code at load time. Always set `True` unless you have a specific reason not to.

### File size

`model.pth` for the 124M parameter model is ~498 MB (124M × 4 bytes for float32). This matches what we computed in chapter 4 section 21.

---

## 24 — Section 5.4: Checkpointing the Optimizer Too

```python
torch.save({
    "model_state_dict":     model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
}, "model_and_optimizer.pth")
```

### Why save the optimizer?

If you want to **resume training**, restoring just the weights is not enough. Adam (and AdamW) keeps two **momentum buffers** per parameter — the running first moment ($m$) and second moment ($v$) of the gradients. These buffers take many warmup steps to stabilise. If you reload the model without them, the optimiser restarts from zero, and the first ~100 steps after resume are essentially destabilising the model.

Saving the optimiser state preserves these buffers so training continues smoothly. The size is roughly **2× the model size** because there are two buffers per parameter.

### Loading both back

```python
checkpoint = torch.load("model_and_optimizer.pth", weights_only=True)

model = GPTModel(GPT_CONFIG_124M)
model.load_state_dict(checkpoint["model_state_dict"])

optimizer = torch.optim.AdamW(model.parameters(), lr=0.0005, weight_decay=0.1)
optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
model.train()
```

The pattern: instantiate fresh `model` and `optimizer`, then overwrite both with the saved state.

### What about the learning rate scheduler, RNG state, etc.?

For full training resumability you would also save:
* `scheduler.state_dict()` — if you're using a learning rate scheduler.
* `torch.get_rng_state()` and `torch.cuda.get_rng_state_all()` — to make resumed training produce the same shuffle order and dropout patterns.
* `epoch` and `global_step` — so you know where to pick up.

Hugging Face's `Trainer` does all of this automatically inside its checkpoint folders (see chapter 12 for the structure). For the simple notebook here, just the model + optimiser is the minimum useful checkpoint.

---

## 25 — Section 5.5: Downloading OpenAI's GPT-2 Weights

```python
# pip install tensorflow tqdm
from gpt_download import download_and_load_gpt2

settings, params = download_and_load_gpt2(model_size="124M", models_dir="gpt2")
```

### What's actually downloaded

The script downloads five files from OpenAI's public storage bucket:

* `checkpoint`, `model.ckpt.data-00000-of-00001`, `model.ckpt.index` — the TensorFlow 1.x checkpoint format (binary weights + metadata).
* `encoder.json`, `vocab.bpe` — the BPE tokenizer files (not used here because we already have `tiktoken`).
* `hparams.json` — the model architecture configuration (n_layers, n_heads, etc.).

Total size: ~500 MB for the 124M model, scaling up to ~6 GB for the 1558M XL model.

### Why TensorFlow specifically?

OpenAI released GPT-2 in February 2019, well before PyTorch had reached parity with TensorFlow. They published the model as a TF 1.x checkpoint, and that format has remained the canonical source ever since. We use TensorFlow only to **read** the checkpoint into numpy arrays; once loaded, everything else happens in PyTorch.

### What `download_and_load_gpt2` returns

* **`settings`** — a dict with the model's hyperparameters (`n_vocab`, `n_ctx`, `n_embd`, `n_layer`, `n_head`).
* **`params`** — a nested dict of numpy arrays, structured like:
  ```
  params["wte"]              # token embeddings, shape (50257, 768)
  params["wpe"]              # positional embeddings, shape (1024, 768)
  params["g"], params["b"]   # final LayerNorm gain and bias
  params["blocks"]           # list of 12 dicts, one per transformer block
      params["blocks"][0]["attn"]["c_attn"]["w"]   # combined Q+K+V weight matrix
      params["blocks"][0]["attn"]["c_attn"]["b"]
      ...
  ```

### Available model sizes

```python
model_configs = {
    "gpt2-small (124M)":  {"emb_dim":  768, "n_layers": 12, "n_heads": 12},
    "gpt2-medium (355M)": {"emb_dim": 1024, "n_layers": 24, "n_heads": 16},
    "gpt2-large (774M)":  {"emb_dim": 1280, "n_layers": 36, "n_heads": 20},
    "gpt2-xl (1558M)":    {"emb_dim": 1600, "n_layers": 48, "n_heads": 25},
}
```

All four sizes share the same architecture; they differ only in width and depth. The 124M model is the smallest because it's the fastest to download, load, and run for an educational notebook.

---

## 26 — Section 5.5: Inspecting the Parameter Dictionary

```python
print("Settings:", settings)
print("Parameter dictionary keys:", params.keys())
print(params["wte"])
print("Token embedding weight tensor dimensions:", params["wte"].shape)
```

Expected output:

```
Settings: {'n_vocab': 50257, 'n_ctx': 1024, 'n_embd': 768, 'n_head': 12, 'n_layer': 12}
Parameter dictionary keys: dict_keys(['blocks', 'b', 'g', 'wpe', 'wte'])
[[ -0.11010301  -0.03926672   0.03310751 ...  ]]
Token embedding weight tensor dimensions: (50257, 768)
```

### Matching up to our `GPT_CONFIG_124M`

| OpenAI key | Our key | Same? |
|------------|---------|-------|
| `n_vocab = 50257` | `vocab_size = 50257` | ✓ |
| `n_ctx = 1024` | `context_length = 256` | ✗ — we shortened ours for training |
| `n_embd = 768` | `emb_dim = 768` | ✓ |
| `n_head = 12` | `n_heads = 12` | ✓ |
| `n_layer = 12` | `n_layers = 12` | ✓ |

The only mismatch is `context_length`. We'll fix this in the next cell.

### Why is `params["wte"]` already in shape `(50257, 768)`?

Because OpenAI's TF checkpoint stores token embeddings the same way PyTorch's `nn.Embedding` does — one row per vocabulary entry, columns are embedding features. This direct match is convenient. For other tensors (like attention weights) we'll need to transpose, as we'll see in section 29.

---

## 27 — Section 5.5: Reconfiguring the Model for GPT-2 Architecture

```python
model_configs = {
    "gpt2-small (124M)":  {"emb_dim":  768, "n_layers": 12, "n_heads": 12},
    "gpt2-medium (355M)": {"emb_dim": 1024, "n_layers": 24, "n_heads": 16},
    "gpt2-large (774M)":  {"emb_dim": 1280, "n_layers": 36, "n_heads": 20},
    "gpt2-xl (1558M)":    {"emb_dim": 1600, "n_layers": 48, "n_heads": 25},
}

model_name = "gpt2-small (124M)"
NEW_CONFIG = GPT_CONFIG_124M.copy()
NEW_CONFIG.update(model_configs[model_name])
NEW_CONFIG.update({"context_length": 1024, "qkv_bias": True})

gpt = GPTModel(NEW_CONFIG)
gpt.eval()
```

### Why the two `.update()` calls?

We start with `GPT_CONFIG_124M` (our local config with `context_length=256` and `qkv_bias=False`) and apply two adjustments:

1. **Merge in the size-specific values** from `model_configs[model_name]` — for gpt2-small these match our config anyway, but for gpt2-medium/large/xl they would override `emb_dim`, `n_layers`, `n_heads`.
2. **Override `context_length=1024` and `qkv_bias=True`** — these are properties of OpenAI's actual released model that differ from our local choices.

### Why `qkv_bias=True` for OpenAI's GPT-2?

In chapter 3 we built `MultiHeadAttention` with `bias=False` on the Q/K/V projections to match the conventions of modern LLMs. OpenAI's *original* GPT-2 (2019) used `bias=True` — they didn't drop the bias term until later models. To load their weights, our `MultiHeadAttention` must have the same bias parameters available to copy into.

### Why instantiate a *new* `gpt` model instead of reusing `model`?

The `model` from earlier sections has `context_length=256`. The positional embedding table is shape `(256, 768)`. OpenAI's `wpe` is shape `(1024, 768)`. Trying to load a `(1024, 768)` into a `(256, 768)` slot would fail with a shape mismatch. Building a fresh `gpt` with the correct config sidesteps this.

### Why doesn't `vocab_size` need to be overridden?

It doesn't — both configs already use `50257`. OpenAI standardised on this vocabulary size from GPT-2 onward.

---

## 28 — Section 5.5: The assign() Helper

```python
def assign(left, right):
    if left.shape != right.shape:
        raise ValueError(f"Shape mismatch. Left: {left.shape}, Right: {right.shape}")
    return torch.nn.Parameter(torch.tensor(right))
```

A two-line utility used throughout `load_weights_into_gpt`. Three things it does:

1. **Shape assertion** — if you ever transpose a tensor wrong (or forget to transpose), the assert catches it immediately rather than letting wrong-shaped weights silently get assigned.
2. **`torch.tensor(right)`** — converts the numpy array `right` to a PyTorch tensor.
3. **`torch.nn.Parameter(...)`** — wraps the tensor so it registers as a learnable parameter when assigned to a module attribute. (Even though we're not going to train these weights, assigning a plain tensor to an `nn.Module` attribute doesn't auto-register it as a parameter — you have to wrap it.)

### Why is the shape mismatch so common?

Two reasons:
1. **Transpose conventions differ.** TensorFlow stores Linear weights as `(in, out)`. PyTorch stores them as `(out, in)`. Almost every weight matrix needs a `.T` when transferring.
2. **OpenAI's attention combines Q, K, V into one matrix.** Their `c_attn["w"]` is `(emb_dim, 3*emb_dim)` — Q, K, V concatenated along the output dimension. Our model has three separate matrices, each `(emb_dim, emb_dim)`. We need `np.split` to break them apart.

The `assign` helper makes these mismatches **loud and immediate** instead of silently producing a model that runs but produces gibberish.

---

## 29 — Section 5.5: Loading OpenAI's Weights Into Our Model

```python
import numpy as np

def load_weights_into_gpt(gpt, params):
    gpt.pos_emb.weight = assign(gpt.pos_emb.weight, params['wpe'])
    gpt.tok_emb.weight = assign(gpt.tok_emb.weight, params['wte'])

    for b in range(len(params["blocks"])):
        # --- Split combined Q+K+V weight matrix into three ---
        q_w, k_w, v_w = np.split(
            params["blocks"][b]["attn"]["c_attn"]["w"], 3, axis=-1
        )
        gpt.trf_blocks[b].att.W_query.weight = assign(
            gpt.trf_blocks[b].att.W_query.weight, q_w.T)
        gpt.trf_blocks[b].att.W_key.weight = assign(
            gpt.trf_blocks[b].att.W_key.weight, k_w.T)
        gpt.trf_blocks[b].att.W_value.weight = assign(
            gpt.trf_blocks[b].att.W_value.weight, v_w.T)

        # --- Q+K+V biases ---
        q_b, k_b, v_b = np.split(
            params["blocks"][b]["attn"]["c_attn"]["b"], 3, axis=-1
        )
        gpt.trf_blocks[b].att.W_query.bias = assign(gpt.trf_blocks[b].att.W_query.bias, q_b)
        gpt.trf_blocks[b].att.W_key.bias   = assign(gpt.trf_blocks[b].att.W_key.bias,   k_b)
        gpt.trf_blocks[b].att.W_value.bias = assign(gpt.trf_blocks[b].att.W_value.bias, v_b)

        # --- Attention output projection ---
        gpt.trf_blocks[b].att.out_proj.weight = assign(
            gpt.trf_blocks[b].att.out_proj.weight,
            params["blocks"][b]["attn"]["c_proj"]["w"].T)
        gpt.trf_blocks[b].att.out_proj.bias = assign(
            gpt.trf_blocks[b].att.out_proj.bias,
            params["blocks"][b]["attn"]["c_proj"]["b"])

        # --- Feed-forward layers ---
        gpt.trf_blocks[b].ff.layers[0].weight = assign(
            gpt.trf_blocks[b].ff.layers[0].weight,
            params["blocks"][b]["mlp"]["c_fc"]["w"].T)
        gpt.trf_blocks[b].ff.layers[0].bias = assign(
            gpt.trf_blocks[b].ff.layers[0].bias,
            params["blocks"][b]["mlp"]["c_fc"]["b"])
        gpt.trf_blocks[b].ff.layers[2].weight = assign(
            gpt.trf_blocks[b].ff.layers[2].weight,
            params["blocks"][b]["mlp"]["c_proj"]["w"].T)
        gpt.trf_blocks[b].ff.layers[2].bias = assign(
            gpt.trf_blocks[b].ff.layers[2].bias,
            params["blocks"][b]["mlp"]["c_proj"]["b"])

        # --- LayerNorms ---
        gpt.trf_blocks[b].norm1.scale = assign(gpt.trf_blocks[b].norm1.scale, params["blocks"][b]["ln_1"]["g"])
        gpt.trf_blocks[b].norm1.shift = assign(gpt.trf_blocks[b].norm1.shift, params["blocks"][b]["ln_1"]["b"])
        gpt.trf_blocks[b].norm2.scale = assign(gpt.trf_blocks[b].norm2.scale, params["blocks"][b]["ln_2"]["g"])
        gpt.trf_blocks[b].norm2.shift = assign(gpt.trf_blocks[b].norm2.shift, params["blocks"][b]["ln_2"]["b"])

    # --- Final LayerNorm + output head (with weight tying) ---
    gpt.final_norm.scale = assign(gpt.final_norm.scale, params["g"])
    gpt.final_norm.shift = assign(gpt.final_norm.shift, params["b"])
    gpt.out_head.weight  = assign(gpt.out_head.weight, params["wte"])

load_weights_into_gpt(gpt, params)
gpt.to(device)
```

This is the longest function in the entire book. Let's break it into manageable parts.

### Part 1: Token + positional embeddings

```python
gpt.pos_emb.weight = assign(gpt.pos_emb.weight, params['wpe'])
gpt.tok_emb.weight = assign(gpt.tok_emb.weight, params['wte'])
```

Direct copy. `wpe` (word position embeddings) and `wte` (word token embeddings) already have the right shape in OpenAI's format — no transpose needed.

### Part 2: Splitting the combined Q+K+V matrix

```python
q_w, k_w, v_w = np.split(
    params["blocks"][b]["attn"]["c_attn"]["w"], 3, axis=-1
)
```

OpenAI's TF-1 GPT-2 stores Q, K, V **concatenated along the last axis** of a single matrix `c_attn["w"]` of shape `(emb_dim=768, 3 * emb_dim=2304)`. `np.split(arr, 3, axis=-1)` slices this into three `(768, 768)` arrays.

This is a **performance optimisation** — running one combined matmul of `(B, T, 768) @ (768, 2304)` is faster than three separate `(B, T, 768) @ (768, 768)` matmuls because GPUs are more efficient on larger matmuls. Our PyTorch model uses the three-separate-matrices approach (chapter 3's design), so we have to split OpenAI's combined matrix into three.

### Part 3: The transpose convention

```python
gpt.trf_blocks[b].att.W_query.weight = assign(... , q_w.T)
```

`q_w` is a numpy array of shape `(in=768, out=768)` — TensorFlow's convention for Linear layers. PyTorch's `nn.Linear` stores its weight as `(out=768, in=768)`. The `.T` (transpose) flips them. **Every weight matrix from OpenAI needs this transpose.** Biases are 1-D and don't need transposing.

### Part 4: FFN layers

```python
gpt.trf_blocks[b].ff.layers[0].weight = assign(..., params["blocks"][b]["mlp"]["c_fc"]["w"].T)
gpt.trf_blocks[b].ff.layers[2].weight = assign(..., params["blocks"][b]["mlp"]["c_proj"]["w"].T)
```

Why `layers[0]` and `layers[2]`, not `layers[1]`? Because our `FeedForward` from chapter 4 is:

```python
nn.Sequential(
    nn.Linear(emb_dim, 4*emb_dim),   # layers[0]   ← c_fc
    GELU(),                           # layers[1]   ← no weights
    nn.Linear(4*emb_dim, emb_dim),   # layers[2]   ← c_proj
)
```

The GELU has no parameters, so we skip it.

### Part 5: LayerNorms

```python
gpt.trf_blocks[b].norm1.scale = assign(..., params["blocks"][b]["ln_1"]["g"])
gpt.trf_blocks[b].norm1.shift = assign(..., params["blocks"][b]["ln_1"]["b"])
```

OpenAI calls them `g` (gain) and `b` (bias). We call them `scale` and `shift`. Same semantics, different names.

### Part 6: Final layers + weight tying

```python
gpt.final_norm.scale = assign(gpt.final_norm.scale, params["g"])
gpt.final_norm.shift = assign(gpt.final_norm.shift, params["b"])
gpt.out_head.weight  = assign(gpt.out_head.weight, params["wte"])
```

The very last line is **weight tying** — the output head's weight matrix is set to the same tensor as the token embeddings. This is the trick we discussed in chapter 4 section 20 that brings the parameter count from 163M down to 124M. OpenAI used weight tying, so to match their behaviour we copy `wte` into both `tok_emb` and `out_head`.

### Why this function is long but not complicated

It's just a name-mapping table written out as code. The structural complexity (Q+K+V splitting, transposing, weight tying) is all dictated by the differences between TensorFlow GPT-2 and our PyTorch GPT-2. Once you understand those three idioms, the function is mechanical.

### What happens if you make a mistake?

The `assign` helper's shape assertion will catch most errors. The remaining failure mode — assigning the *right* shape but the *wrong* tensor (e.g. confusing `c_fc` with `c_proj`) — produces a model that runs but outputs gibberish. The only way to detect that is to run inference and check whether the output is coherent. That's exactly what section 30 does.

---

## 30 — Section 5.5: Generating Text With Pretrained Weights

```python
torch.manual_seed(123)
token_ids = generate(
    model=gpt,
    idx=text_to_token_ids("Every effort moves you", tokenizer).to(device),
    max_new_tokens=25,
    context_size=NEW_CONFIG["context_length"],
    top_k=50,
    temperature=1.5,
)
print("Output text:\n", token_ids_to_text(token_ids, tokenizer))
```

Expected output:

```
Output text:
 Every effort moves you toward finding an ideal new way to practice something!

What makes us want to be on top of that?
```

### This is the payoff of the chapter

For the first time in this entire repository, we have a model that produces **coherent English**. The prompt was "Every effort moves you", and the model wrote a sensible motivational-quote continuation. None of this came from our training — it all came from the 40 GB of internet text that OpenAI trained GPT-2 on in 2019.

### The hyperparameters used

* **`top_k=50`** — fairly permissive, gives the model 50 candidate tokens at each step.
* **`temperature=1.5`** — quite high, encouraging diverse and creative outputs.

These are typical "creative writing" settings. For factual Q&A you would use `top_k=10` and `temperature=0.3` or lower.

### Sanity-check value of this cell

If `load_weights_into_gpt` had a subtle bug (e.g. swapped Q and K weights, or forgot to transpose `c_fc`), the model would still run — but the output would be incoherent or completely random. Coherent English is **strong evidence that the weight transfer worked correctly**.

### What you've actually built by the end of chapter 5

* A complete GPT-2 model architecture (chapter 4).
* A working training loop that you've used to overfit a tiny dataset (sections 15–17).
* A flexible inference engine with greedy, sampling, temperature, top-k, and early-stopping (sections 18–22).
* The ability to load arbitrary GPT-2 checkpoint sizes from OpenAI and run inference with them (sections 25–30).

This is, structurally, **everything an LLM library does**. From here, chapters 6 and 7 add fine-tuning (for classification and instruction following), but the core machine — the architecture, the training, the generation — is fully assembled.
