# Chapter 5 Code Explanation — Pretraining on Unlabeled Data

This document walks through every code cell of `ch05.ipynb` from Sebastian Raschka's _Build a Large Language Model From Scratch_. Chapter 5 is where the GPT model you assembled in chapter 4 finally gets _trained_ — first from scratch on a tiny short story, then by loading OpenAI's actual pretrained GPT-2 weights so the model can produce coherent English.

The five book sections covered are:

- **5.1 Evaluating generative text models** — cross-entropy loss, perplexity, training/validation data loaders, and computing the initial loss before training.
- **5.2 Training an LLM** — the full training loop with `AdamW`, per-step evaluation, and per-epoch sample generation.
- **5.3 Decoding strategies** — temperature scaling, top-k filtering, and a new `generate` function that combines both.
- **5.4 Saving and loading model weights** — `state_dict`, checkpointing the optimizer too.
- **5.5 Loading pretrained weights from OpenAI** — downloading, reshaping, and copying OpenAI's GPT-2 weights into our model.

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

- **`torch`** — every layer, the optimizer (`AdamW`), the loss (`cross_entropy`), and `torch.multinomial` for sampling.
- **`tiktoken`** — OpenAI's BPE tokenizer for `gpt2`. Identical to what you used in chapters 2–4.
- **`numpy`** — only used once, when loading OpenAI's TensorFlow checkpoints. The downloaded weights come back as numpy arrays and need a `.T` (transpose) before going into PyTorch.
- **`matplotlib`** — for the loss curve plot in section 17 and the temperature comparison bar chart in section 20.
- **`tensorflow`** — surprising but necessary: OpenAI released GPT-2 weights as TensorFlow checkpoints. The `gpt_download.py` helper script in section 25 uses `tf.train.list_variables` and `tf.train.load_variable` to read them.

If you only care about training the small model from scratch and never plan to load OpenAI's weights, you can skip tensorflow — but doing so means missing the highlight of the chapter (coherent generation from a real pretrained model).

---

## 2 — Section 5.1.1: `text_to_token_ids` and `token_ids_to_text` Helpers

**Summary.** Two thin wrapper functions that bookend every generation call in the chapter: one converts a raw string into the `(1, seq_len)` integer tensor the model expects, and the other converts the model's `(1, seq_len)` output tensor back into a human-readable string. They are not novel architecture — they are the glue layer between Python strings and PyTorch tensors, and every later section calls them without comment.

**The problem they solve.** `GPTModel.forward` expects `(batch, seq_len)` integer token IDs. `tokenizer.encode` returns a plain Python list. `tokenizer.decode` expects a plain Python list. Neither end speaks the other's native type, and neither handles the batch dimension automatically. These two helpers are the adapters.

**The code.**

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

**Shape transformation story — `text_to_token_ids`.**

Using `"Every effort moves you"` as the input string (4 tokens):

```
"Every effort moves you"            ← raw Python str

       ↓  tokenizer.encode(text, allowed_special={'<|endoftext|>'})
       │  BPE tokenisation — each subword maps to an integer ID

[6109, 3626, 6100, 345]             ← Python list[int],  len = 4

       ↓  torch.tensor(encoded)

tensor([6109, 3626, 6100, 345])     ← shape (4,)
                                         ↑
                                       seq_len only — no batch dim yet

       ↓  .unsqueeze(0)              ← insert a size-1 dim at position 0

tensor([[6109, 3626, 6100, 345]])   ← shape (1, 4)
                                         ↑  ↑
                                       batch seq_len
```

The `.unsqueeze(0)` is non-negotiable. `GPTModel.forward` immediately does `batch_size, seq_len = in_idx.shape` — it unpacks exactly two dimensions. A bare `(4,)` tensor would make `batch_size=4` and crash on the missing `seq_len`.

**Shape transformation story — `token_ids_to_text`.**

After `generate_text_simple` appends 10 new tokens, the output has shape `(1, 14)`:

```
tensor([[6109, 3626, 6100, 345, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10]])
                                                        ← shape (1, 14)
                                                             ↑   ↑
                                                           batch seq_len

       ↓  .squeeze(0)              ← remove the size-1 batch dim

tensor([6109, 3626, 6100, 345, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10])
                                                        ← shape (14,)

       ↓  .tolist()                ← convert to Python list (decode requires it)

[6109, 3626, 6100, 345, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10]
                                                        ← list[int]

       ↓  tokenizer.decode(...)

"Every effort moves you ..."        ← Python str
```

The `.squeeze(0)` exactly undoes the `.unsqueeze(0)` from the encoder. The `.tolist()` is required because `tokenizer.decode` does not accept torch tensors — only Python lists.

**`allowed_special={'<|endoftext|>'}` — what it does and why it's here.**

GPT-2's tokenizer treats `<|endoftext|>` (token ID `50256`) as a special boundary token that separates documents in a pretraining corpus. By default `tiktoken` refuses to silently encode it if it appears in arbitrary text, raising `"Encountered text corresponding to disallowed special token"`. Passing `allowed_special={'<|endoftext|>'}` explicitly whitelists it. For the demo prompt `"Every effort moves you"` it makes no difference — the prompt doesn't contain that token — but the helper is written to be correct for the pretraining loop in sections 10–16, where documents are separated by `<|endoftext|>` tokens and those IDs must encode without errors.

**The full round-trip in one diagram.**

```
"Every effort moves you"
       ↓  text_to_token_ids
tensor([[6109, 3626, 6100, 345]])          shape (1, 4)
       ↓  generate_text_simple  (max_new_tokens=10)
tensor([[6109, 3626, 6100, 345,
         t1, t2, t3, t4, t5, t6,
         t7, t8, t9, t10]])                shape (1, 14)
       ↓  token_ids_to_text
"Every effort moves you ..."               Python str
```

**What the output looks like at this point.** The model is in `eval()` mode but completely untrained — the weights are the random values from `GPTModel(GPT_CONFIG_124M)`. The 10 appended tokens are argmax picks from random logit distributions. The book's run produces something like `"Every effort moves you rentingetic wasn?? refres RexMeCHicular stren"`. The prompt tokens decode correctly because the generation loop never overwrites them — it only appends.

**Gotchas.**

`.squeeze(0)` will silently do nothing if the batch dimension is not size 1. If you call `token_ids_to_text` on a `(2, 14)` batch result, it returns without squeezing and `tokenizer.decode` will receive a 2D list and fail. These helpers are explicitly designed for single-sequence use (`batch=1`).

`torch.tensor(encoded)` creates an integer tensor (`torch.int64` by default for lists of Python ints). The model's embedding layer expects integer indices — not floats. If you accidentally pass a float tensor, the embedding lookup will raise `"Expected tensor for argument #1 'indices' to have scalar type Long"`.

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

**Summary.** Two integer tensors of identical shape — `inputs` holds the context the model sees, `targets` holds the correct next token at every position. They are the same sequence, offset by one: targets is inputs shifted left by one column. This pair is the atomic unit of supervised language model training.

**The problem it solves.** The model needs a ground-truth signal at every position to learn from. A naïve approach would give the model a full sentence and ask "what comes next?" — one signal per sentence. The shift-by-one construction gives `seq_len` signals per sentence for free, because every token in the sequence is simultaneously the answer to the previous token's question.

**The intuition.** Imagine reading a sentence one word at a time and being asked, after each word, "what word do you think comes next?" That is exactly what inputs and targets encode: for every token the model reads (inputs), there is a known correct answer (targets).

**Shape annotation.**

```
inputs.shape  = (2, 3)    ← (batch, seq_len)
                 ↑  ↑
              batch seq_len

targets.shape = (2, 3)    ← (batch, seq_len) — same shape, values shifted left by one
                 ↑  ↑
              batch seq_len
```

**The shift-by-one construction — dry run for row 0.**

Start from the full source sequence `["every", " effort", " moves", " you"]` as token IDs `[16833, 3626, 6100, 345]`. Slice it into two overlapping windows:

```
full sequence:  [16833,  3626,  6100,   345]
                   ↑       ↑      ↑       ↑
                "every" "effort" "moves"  "you"

inputs  row 0:  [16833,  3626,  6100]    ← first 3 tokens  — what the model reads
targets row 0:  [ 3626,  6100,   345]    ← last  3 tokens  — what the model must predict
```

Aligned column by column:

```
Position 0:   input = 16833 ("every")      target = 3626  (" effort")
Position 1:   input = 3626  (" effort")    target = 6100  (" moves")
Position 2:   input = 6100  (" moves")     target = 345   (" you")
```

The same logic for row 1, source sequence `["I", " really", " like", " chocolate"]`:

```
full sequence:  [40,   1107,   588,   11311]
                  ↑      ↑      ↑       ↑
                 "I" "really" "like" "chocolate"

inputs  row 1:  [40,   1107,   588]    ← first 3 tokens
targets row 1:  [1107,  588,  11311]   ← last  3 tokens
```

**The matrix visualisation.**

```
inputs = [
           [16833,  3626,  6100],    ← Batch 0: "every  effort  moves"
           [   40,  1107,   588]     ← Batch 1: "I  really  like"
         ]

targets = [
            [ 3626,  6100,   345],   ← Batch 0: " effort  moves  you"
            [ 1107,   588, 11311]    ← Batch 1: " really  like  chocolate"
          ]
```

At every `(batch, position)` pair in `inputs`, the model will eventually output a probability distribution over the full vocabulary. The entry at `targets[batch, position]` is the one token index in that distribution that should have received probability 1. Every other token should have received probability 0. Cross-entropy loss (Section 4 onward) measures exactly how far from that ideal the model currently is.

**Why `seq_len` signals, not one.** A sequence of length 4 is sliced into inputs of length 3 and targets of length 3 — giving 3 `(input position, correct next token)` pairs instead of 1. Across a batch of 2 sentences that's 6 training signals from 8 total tokens. This is why language model training is so data-efficient compared to classification: no label annotation is needed and every token in the corpus is both a context and a target.

**Why the leading space on `" effort"` etc.** GPT-2's BPE tokeniser encodes the space as part of the following token rather than as a standalone token. The string `"effort"` (no space, token ID `25045`) and `" effort"` (with space, token ID `3626`) are entirely different vocabulary entries. This means the tokeniser can recover word boundaries from the token sequence alone during decoding — no separate whitespace token is needed, and the vocabulary does not double in size.

**Gotchas.**

`inputs` and `targets` must have identical shape. `cross_entropy` later zips them position-by-position — a shape mismatch raises an error immediately. The shift is handled outside the model by whoever constructs the batch; the model itself sees only `inputs` and has no knowledge that `targets` exists until the loss is computed.

The token IDs in `targets` are raw integer indices into the vocabulary, not one-hot vectors and not embeddings. `cross_entropy` directly indexes the logit at position `targets[b, t]` — no conversion needed and no `torch.long` cast required because `torch.tensor` infers `int64` from a Python list of ints automatically.

### Extra notes

Not every token has a space variant — it is more selective than that.

The rule in GPT-2 BPE is that a space is encoded as part of the token that **follows** it. So when the tokeniser sees the sentence `"every effort moves you"`, it encodes it roughly as `["every", " effort", " moves", " you"]` — the space migrates into the start of the next word. The first word of a sentence or the first word after punctuation typically has no leading space; every subsequent word does.

But BPE does not create pairs mechanically for every word. The vocabulary is built by a frequency-based merge algorithm run on a large corpus. A token like `" effort"` (with space) ends up in the vocabulary only if that space-prefixed form appeared frequently enough in the training text to earn its own merge. Common words like `" the"`, `" of"`, `" moves"` almost certainly have space variants. Rare words may not — they get split into subword pieces instead, and the space attaches to whichever piece comes first.

So the short answer is: yes, many common words do have both a no-space and a space-prefixed form as separate vocabulary entries with different IDs, but it is not a guaranteed pair for every token — it depends entirely on what the BPE merge algorithm found frequent enough to keep as a single unit during vocabulary construction.

The practical consequence for you as a user is simple: when you pass text to `tokenizer.encode`, you do not need to think about spaces at all. The tokeniser handles the space-absorption automatically. The only time it matters is when you manually construct token ID sequences by hand — as the book does with `inputs` and `targets` — and you need to be sure `3626` (` effort` with space) is the correct ID for a mid-sentence word, not `25045` (`effort` without space).

## 4 — Section 5.1.2: Logits and the Softmax Probabilities

```python
with torch.no_grad():
    logits = model(inputs)

probas = torch.softmax(logits, dim=-1)
print(probas.shape)  # torch.Size([2, 3, 50257])
```

**Summary.** A forward pass through the model turns the `(2, 3)` integer input tensor into a `(2, 3, 50257)` float tensor of logits — one raw score per vocabulary token per position. Softmax converts each 50257-dim logit row into a proper probability distribution. The result is a tensor where every entry is in `(0, 1)` and every row sums to exactly 1.

**The problem it solves.** The model's raw output (logits) is unbounded — values can be positive, negative, arbitrarily large. To compare the model's output against a target token ID using cross-entropy, we need each position's output to look like a probability distribution over the vocabulary. Softmax provides that conversion.

**The intuition.** Think of each logit as a raw "confidence score" the model assigns to each vocabulary token. Softmax exponentiates all 50257 scores (making them positive) and then normalises by their sum, so they become proportional weights that add to 1. The token with the highest logit gets the highest probability — but every other token gets at least a sliver.

**Shape transformation story.**

```
inputs.shape = (2, 3)              ← (batch, seq_len) — integer token IDs
       ↓  model(inputs)            ← full GPT forward pass: embed → 12× TransformerBlock → LayerNorm → out_head
logits.shape = (2,   3,    50257)       ← (batch, seq_len, vocab_size)
                ↑    ↑      ↑
            batch,  seq,  vocab_size
       ↓  torch.softmax(logits, dim=-1)    ← normalise along the vocab dimension
probas.shape = (2,   3,   50257)       ← same shape; each row [b, t, :] now sums to 1.0
                ↑    ↑      ↑
              batch seq  vocab_size
```

Expanding the matrix for batch 0 to see what the shape means concretely:

```
probas = [
           [                                      ← Batch 0
             [p_0, p_1, ..., p_50256],   ← Token 0 "every"    — dist over full vocab
             [p_0, p_1, ..., p_50256],   ← Token 1 " effort"  — dist over full vocab
             [p_0, p_1, ..., p_50256]    ← Token 2 " moves"   — dist over full vocab
           ],                                     ← end Batch 0
           [                                      ← Batch 1
             [p_0, p_1, ..., p_50256],   ← Token 0 "I"
             [p_0, p_1, ..., p_50256],   ← Token 1 " really"
             [p_0, p_1, ..., p_50256]    ← Token 2 " like"
           ]                                      ← end Batch 1
         ]
```

Each row `probas[b, t, :]` answers the question: "given everything the model has seen up to and including position `t` in sequence `b`, how likely is each vocabulary token to be the next one?"

**The softmax formula — dry run for one row.**

Take a simplified vocabulary of 4 tokens with logits `[2.0, 1.0, 0.1, -1.0]` (the real vocab has 50257 entries but the arithmetic is identical):

```
Step 1 — exponentiate each logit:
  e^2.0  = 7.389
  e^1.0  = 2.718
  e^0.1  = 1.105
  e^-1.0 = 0.368

Step 2 — sum:
  7.389 + 2.718 + 1.105 + 0.368 = 11.580

Step 3 — divide each by the sum:
  7.389 / 11.580 = 0.638    ← token 0 gets the highest prob (highest logit)
  2.718 / 11.580 = 0.235
  1.105 / 11.580 = 0.095
  0.368 / 11.580 = 0.032
                  ───────
  sum            = 1.000    ← guaranteed by construction
```

The general formula for entry `v` in position `(b, t)`:

$$\text{probas}[b, t, v] = \frac{e^{\text{logits}[b,t,v]}}{\displaystyle\sum_{v'=0}^{50256} e^{\text{logits}[b,t,v']}}$$

**Why `torch.no_grad()`.**

During a normal forward pass, PyTorch's autograd engine records every operation into a computation graph so that `.backward()` can later propagate gradients. That graph retains all intermediate activations — for a 124M model across 12 transformer blocks this is several hundred MB. Since we are only inspecting outputs here, not training, the graph is waste. `torch.no_grad()` tells autograd to skip graph construction entirely, so intermediate tensors are freed as soon as they are consumed.

**Why the probabilities are nearly uniform for an untrained model.**

Random initialisation sets each weight matrix to small values roughly following $\mathcal{N}(0, \sigma^2)$ where $\sigma$ is chosen per-layer. After 12 transformer blocks, the logits at `out_head` end up with similar small magnitudes across all 50257 entries — no token has been systematically pushed higher than the others. Softmax of nearly-equal values gives:

```
probas[b, t, v] ≈ 1 / 50257 ≈ 2 × 10⁻⁵   for every v
```

The model has no preference. Training will concentrate this distribution by pushing the logit of the correct next token much higher than all others, turning a flat plateau into a sharp peak at the right token ID.

**Gotchas.**

`dim=-1` is critical. `torch.softmax(logits, dim=0)` would normalise across the batch dimension — turning `probas[:, t, v]` into a distribution that sums to 1 over batches, which is meaningless. `dim=1` would normalise across sequence positions, also wrong. Only `dim=-1` (the vocab dimension) produces a valid next-token probability distribution at each `(b, t)` position.

`logits` going into `cross_entropy` later must be the raw pre-softmax values, not `probas`. PyTorch's `F.cross_entropy` applies `log_softmax` internally and is numerically more stable than doing `softmax → log` in two steps. If you pass `probas` instead of `logits` into `cross_entropy`, you get silently wrong loss values because softmax is applied twice.

## 5 — Section 5.1.2: Argmax Predictions vs Targets

```python
token_ids = torch.argmax(probas, dim=-1, keepdim=True)
print("Token IDs:\n", token_ids)
# tensor([[[16657],
#          [  339],
#          [42826]],
#
#         [[49906],
#          [29669],
#          [41751]]])

print(f"Targets batch 1: {token_ids_to_text(targets[0], tokenizer)}")
print(f"Outputs batch 1: {token_ids_to_text(token_ids[0].flatten(), tokenizer)}")
# Targets batch 1:  effort moves you
# Outputs batch 1: Armed heNetflix
```

**Summary.** For each `(batch, position)` pair, pick the vocabulary index with the highest probability — the model's single best guess at the next token. Compare those guesses against the ground-truth targets. For an untrained model the guesses are gibberish, which sets up the core question: how do we measure exactly how wrong these predictions are?

**The problem it solves.** `probas` is a `(2, 3, 50257)` tensor — a full distribution at every position. To see what the model actually predicts, we need to collapse the vocab dimension down to one number: the argmax. This is the greedy prediction — the token the model would generate if forced to pick one right now.

**Shape transformation story.**

```
probas.shape = (2, 3, 50257)       ← (batch, seq_len, vocab_size)
       ↓  torch.argmax(dim=-1, keepdim=True)
              collapse vocab dim to the index of its max value
              keepdim=True keeps the dim as size 1 instead of dropping it

token_ids.shape = (2, 3, 1)        ← (batch, seq_len, 1)
                   ↑  ↑  ↑
                batch seq  1  ← the winning vocab index at each position
```

Without `keepdim=True` the shape would collapse to `(2, 3)` — the vocab dimension disappears entirely. With it, the vocab slot stays open as a size-1 axis, preserving the tensor's rank. This matters when you later want to index or broadcast against `probas` without unsqueezing manually.

**Matrix visualisation — the full `token_ids` tensor.**

```
token_ids = [
              [                       ← Batch 0: "every effort moves"
                [16657],     ← Token 0 "every"   — model's best guess for next token
                [  339],     ← Token 1 " effort" — model's best guess for next token
                [42826]      ← Token 2 " moves"  — model's best guess for next token
              ],              ← end Batch 0
              [                       ← Batch 1: "I really like"
                [49906],     ← Token 0 "I"       — model's best guess for next token
                [29669],     ← Token 1 " really" — model's best guess for next token
                [41751]      ← Token 2 " like"   — model's best guess for next token
              ]               ← end Batch 1
            ]
```

**Comparing predictions to targets — dry run for batch 0.**

```
Position 0:   predicted = 16657 ("Armed")     target = 3626  (" effort")    ✗
Position 1:   predicted = 339   (" he")       target = 6100  (" moves")     ✗
Position 2:   predicted = 42826 ("Netflix")   target = 345   (" you")       ✗
```

All three wrong. This is expected — the model has random weights and assigns nearly uniform probability across 50257 tokens. The argmax just happens to land on `"Armed"`, `" he"`, `"Netflix"` — three tokens with marginally higher random logits at those positions.

**Why `.flatten()` is needed before `token_ids_to_text`.**

```
token_ids[0].shape = (3, 1)     ← one sequence, keepdim=True left the trailing 1
       ↓  .flatten()
shape = (3,)                    ← 1-D tensor required by tokenizer.decode via .tolist()
```

`token_ids_to_text` calls `.squeeze(0)` then `.tolist()` internally — it expects a 1-D tensor going in. A `(3, 1)` tensor passed to `.tolist()` produces `[[16657], [339], [42826]]`, a list of lists, which `tokenizer.decode` rejects. `.flatten()` collapses it to `[16657, 339, 42826]` first.

**Why this exercise matters.** The argmax comparison makes the failure of the untrained model viscerally clear: "Armed heNetflix" versus " effort moves you". But argmax gives us no gradient — it is not differentiable. We cannot directly tell the model "your argmax was wrong, adjust your weights." What we need is a differentiable scalar that measures how wrong the full probability distribution is, not just the top pick. That scalar is cross-entropy loss, which the next sections build up from scratch.

**Gotchas.**

`torch.argmax` with `dim=-1` operates on the vocab dimension. Using `dim=0` would return the batch index with the highest probability for each `(seq, vocab)` pair — meaningless. Using `dim=1` would return the token position with the highest probability for each `(batch, vocab)` pair — also meaningless. `dim=-1` is the only correct choice here.

`targets[0]` passed directly to `token_ids_to_text` works without `.flatten()` because `targets[0]` already has shape `(3,)` — it was created without a trailing size-1 dimension. `token_ids[0]` has shape `(3, 1)` because of `keepdim=True`, which is why it needs the extra step.

## 6 — Section 5.1.2: Pulling Target-Token Probabilities (Fancy Indexing)

```python
text_idx = 0
target_probas_1 = probas[text_idx, [0, 1, 2], targets[text_idx]]
print("Text 1:", target_probas_1)
# Text 1: tensor([7.4541e-05, 3.1061e-05, 1.1563e-05])

text_idx = 1
target_probas_2 = probas[text_idx, [0, 1, 2], targets[text_idx]]
print("Text 2:", target_probas_2)
# Text 2: tensor([1.0337e-05, 4.6163e-05, 5.5810e-05])
```

**Summary.** From the full `(2, 3, 50257)` probability tensor, extract only the six probabilities the model assigned to the correct next token at each position — one scalar per `(batch, position)` pair. These six numbers are the raw material for cross-entropy loss: training is the process of pushing all six toward 1.

**The problem it solves.** After softmax, `probas` holds 50257 probabilities at every position. Cross-entropy only needs one of them — the probability assigned to the token that was actually correct. Fancy indexing lets us reach into the vocab dimension and pull exactly that entry out, position by position, in one vectorised operation.

**The intuition.** Think of `probas[b, t, :]` as a row of 50257 slots. `targets[b, t]` is a column index pointing at one specific slot — the slot for the correct next token. Fancy indexing is just a way of saying "for each row, give me the value at this specific column" across all rows at once.

**The indexing expression unpacked.**

`probas[text_idx, [0, 1, 2], targets[text_idx]]` is PyTorch fancy indexing with three coordinate lists zipped together:

```
Dimension 0 (batch):    text_idx          →  scalar, broadcast to [0, 0, 0]
Dimension 1 (position): [0, 1, 2]         →  position indices
Dimension 2 (vocab):    targets[text_idx] →  [3626, 6100, 345]  for text_idx=0

Zipped element by element:

  element 0:  probas[0,  0,  3626]   ← prob assigned to " effort" at position 0
  element 1:  probas[0,  1,  6100]   ← prob assigned to " moves"  at position 1
  element 2:  probas[0,  2,   345]   ← prob assigned to " you"    at position 2

result: tensor of shape (3,)
```

For `text_idx=1`, `targets[1] = [1107, 588, 11311]`:

```
  element 0:  probas[1,  0,  1107]   ← prob assigned to " really"    at position 0
  element 1:  probas[1,  1,   588]   ← prob assigned to " like"      at position 1
  element 2:  probas[1,  2, 11311]   ← prob assigned to " chocolate" at position 2

result: tensor of shape (3,)
```

**Shape story.**

```
probas.shape          = (2, 3, 50257)   ← (batch, seq_len, vocab_size)

probas[0, [0,1,2], targets[0]].shape = (3,)   ← one prob per position, batch 0
probas[1, [0,1,2], targets[1]].shape = (3,)   ← one prob per position, batch 1
```

**Dry-run arithmetic — what the values mean.**

```
Text 1 (batch 0):
  probas[0, 0, 3626]  = 7.4541e-05   ← model gave " effort"    this much probability
  probas[0, 1, 6100]  = 3.1061e-05   ← model gave " moves"     this much probability
  probas[0, 2,  345]  = 1.1563e-05   ← model gave " you"       this much probability

Text 2 (batch 1):
  probas[1, 0, 1107]  = 1.0337e-05   ← model gave " really"    this much probability
  probas[1, 1,  588]  = 4.6163e-05   ← model gave " like"      this much probability
  probas[1, 2, 11311] = 5.5810e-05   ← model gave " chocolate" this much probability

Uniform baseline:  1 / 50257 ≈ 2e-05
```

All six values hover around $2 \times 10^{-5}$ — the untrained model spreads probability nearly equally across all 50257 tokens, so the correct token receives no more attention than any random entry in the vocabulary. A perfectly trained model would have all six values at or near 1.0.

**Why this is what training optimises.** Cross-entropy loss is computed directly from these six numbers. The loss is $-\log$ of each, averaged:

```
ideal (trained):     prob = 1.0   →  -log(1.0) = 0.0    ← zero loss
current (untrained): prob ≈ 2e-05 →  -log(2e-05) ≈ 10.8 ← high loss
```

Every gradient update to the model's weights is in the direction that increases these six probabilities — equivalently, decreasing their negative logs. Watching these values climb from $10^{-5}$ toward $1.0$ over training is what learning looks like from the inside.

**Gotchas.**

`targets[text_idx]` used in the third index position must be a 1-D integer tensor of length `seq_len`. If `targets` is on a different device than `probas` (one on CPU, one on GPU), the indexing silently fails or raises a device mismatch error. Both tensors must be on the same device.

The expression `[0, 1, 2]` in the second index position is a Python list, not a slice. Writing `probas[0, :, targets[0]]` would not give the same result — `:` selects all 3 positions but the broadcast semantics differ when `targets[0]` is a 1-D tensor rather than a scalar. The explicit list `[0, 1, 2]` makes the element-wise pairing with `targets[text_idx]` unambiguous.

## 7 — Section 5.1.2: From Probabilities to Log-Probs to Loss

```python
# Step 1: concatenate the 6 target probabilities and take their log
log_probas = torch.log(torch.cat((target_probas_1, target_probas_2)))
print(log_probas)
# tensor([ -9.5042, -10.3796, -11.3677, -11.4798,  -9.7764, -12.2561])

# Step 2: average them
avg_log_probas = torch.mean(log_probas)
print(avg_log_probas)
# tensor(-10.7940)

# Step 3: flip the sign — this is the loss
neg_avg_log_probas = avg_log_probas * -1
print(neg_avg_log_probas)
# tensor(10.7940)
```

**Summary.** Three lines of arithmetic that build cross-entropy loss by hand: concatenate the six target probabilities from Section 6, take their natural log, average, negate. The result `10.7940` is the loss value — the same number PyTorch's `F.cross_entropy` will produce in Section 8 from a single function call.

**The problem it solves.** We have six small probabilities — the model's confidence in the correct next token at each position. We need a single scalar that increases when those probabilities are low (model is wrong) and decreases when they are high (model is right), and that is differentiable so gradients can flow backward. Negative average log probability is that scalar.

**Step 1 — concatenate and log.**

```
target_probas_1 = tensor([7.4541e-05, 3.1061e-05, 1.1563e-05])   ← batch 0, 3 positions
target_probas_2 = tensor([1.0337e-05, 4.6163e-05, 5.5810e-05])   ← batch 1, 3 positions

torch.cat((target_probas_1, target_probas_2))
  = tensor([7.4541e-05, 3.1061e-05, 1.1563e-05, 1.0337e-05, 4.6163e-05, 5.5810e-05])
                                                                    shape: (6,)

torch.log(...)   ← natural log (base e) applied element-wise

log_probas = tensor([ -9.5042, -10.3796, -11.3677, -11.4798,  -9.7764, -12.2561])
                                                                    shape: (6,)
```

Dry-run for the first entry:

```
prob  = 7.4541e-05
log(7.4541e-05) = log(7.4541 × 10⁻⁵)
                = log(7.4541) + log(10⁻⁵)
                = 2.008 + (-11.513)
                = -9.505   ≈ -9.5042  ✓
```

All six values are large negative numbers in the range `[-9.5, -12.3]`. The more confident the model is in the wrong answer, the more negative the log — and log of near-zero probabilities dives toward $-\infty$.

**Step 2 — average.**

```
log_probas = [-9.5042, -10.3796, -11.3677, -11.4798, -9.7764, -12.2561]

sum  = -9.5042 + (-10.3796) + (-11.3677) + (-11.4798) + (-9.7764) + (-12.2561)
     = -64.7638

mean = -64.7638 / 6 = -10.7940   ✓
```

Averaging treats every `(batch, position)` pair equally — the loss is not dominated by any single sequence or token position.

**Step 3 — negate.**

```
avg_log_probas   = -10.7940
neg_avg_log_probas = -10.7940 × -1 = 10.7940
```

The loss formula in full:

$$L = -\frac{1}{N} \sum_{i=1}^{N} \log P(\text{target}_i \mid \text{context}_i)$$

where $N = 6$ here (2 sequences × 3 positions each). Written out:

```
L = -(1/6) × (log(7.4541e-05) + log(3.1061e-05) + log(1.1563e-05)
            + log(1.0337e-05) + log(4.6163e-05) + log(5.5810e-05))
  = -(1/6) × (-9.5042 + -10.3796 + -11.3677 + -11.4798 + -9.7764 + -12.2561)
  = -(1/6) × (-64.7638)
  = 10.7940
```

**Why log and not the raw probability.**

The natural instinct is to measure the model's overall correctness by multiplying the probability it assigned to each correct token — the joint probability of being right at every position simultaneously. For our six positions:

```
7.4541e-05 × 3.1061e-05 × 1.1563e-05 × 1.0337e-05 × 4.6163e-05 × 5.5810e-05
≈ 7.3 × 10⁻²⁸
```

This is already dangerous with just six positions. Now consider a realistic sequence of 1024 tokens where the untrained model assigns $\approx 2 \times 10^{-5}$ to each correct token:

$$\left(2 \times 10^{-5}\right)^{1024} = 2^{1024} \times 10^{-5120} \approx 10^{-5050}$$

float32 can represent numbers down to about $10^{-38}$. A result of $10^{-5050}$ is thousands of orders of magnitude below that floor — it underflows to exactly `0.0` with no warning, no error, and no way to recover:

```python
import torch
p = torch.tensor(2e-5)
print(p ** 1024)   # tensor(0.)  ← silent underflow
```

Once the product is `0.0`, its gradient with respect to every weight in the model is also `0.0`. The optimiser receives zero signal and does nothing. Training is dead before it starts.

Taking the log rescues this entirely. The key identity is exact — not an approximation:

$$\log(p_1 \times p_2 \times \dots \times p_N) = \log p_1 + \log p_2 + \dots + \log p_N$$

The same 1024-token example with log:

$$1024 \times \log(2 \times 10^{-5}) = 1024 \times (-10.82) = -11{,}079.7$$

$-11079.7$ is a perfectly ordinary float32 number. Its gradient is non-zero, well-defined, and training proceeds normally.

Beyond numerical safety, log gradients also scale better with how wrong the model is. The derivative of $\log(p)$ with respect to $p$ is $\frac{1}{p}$:

$$\frac{d}{dp}\left[\log(p)\right] = \frac{1}{p}$$

So the gradient magnitude is inversely proportional to how much probability the model assigns to the correct token:

$$p = 2 \times 10^{-5}\ (\text{untrained, very wrong}) \quad\Rightarrow\quad \frac{1}{p} = 50{,}000 \quad \leftarrow \text{strong push}$$

$$p = 0.50\ (\text{getting better}) \quad\Rightarrow\quad \frac{1}{p} = 2 \quad \leftarrow \text{moderate push}$$

$$p = 0.99\ (\text{nearly correct}) \quad\Rightarrow\quad \frac{1}{p} = 1.01 \quad \leftarrow \text{gentle nudge}$$

Raw probability gradients are always $\frac{d}{dp}[p] = 1$ regardless of how wrong the model is — uninformative and flat. Log probability gradients are large when the model needs the most correction and shrink naturally as it improves. This is exactly the shape a good loss function should have.

**Why negate.**

After taking the log, the six values are all negative numbers in $[-9.5,\ -12.3]$. Their average is $-10.7940$. As the model trains and assigns higher probabilities to the correct tokens, these log values climb toward $0$ — a perfect model with probability $1.0$ everywhere gives $\log(1.0) = 0.0$.

The problem is direction. PyTorch optimisers call `.step()` to descend — they subtract a scaled gradient from each parameter, reducing whatever scalar they are given. If you hand them $-10.7940$, they will push it toward more negative values, which means pushing the log probabilities down, which means making the model worse. The gradient points the wrong way.

Negating flips everything:

$$\text{bad model}\ (p \approx 2 \times 10^{-5}): \quad -\log(2 \times 10^{-5}) \approx +10.8 \quad \leftarrow \text{large positive loss}$$

$$\text{good model}\ (p \approx 1.0): \quad -\log(1.0) = 0.0 \quad \leftarrow \text{zero loss}$$

Now the optimiser descending on $+10.7940$ toward $0.0$ is exactly equivalent to the model improving. The negation costs one multiplication and makes the loss a positive scalar that decreases monotonically as training succeeds — the universal convention every PyTorch scheduler, logger, and early-stopping callback expects.

**Gotchas.**

`torch.log` is the natural logarithm (base $e$), not `log10` or `log2`. Cross-entropy is always defined in nats, not bits. The numerical values of the loss (`10.79`) are in nats — this is what `F.cross_entropy` also returns, and what you compare against `log(vocab_size)` = `log(50257) ≈ 10.82` as the theoretical maximum for a uniform distribution.

`torch.cat` requires both tensors to be on the same device and have the same dtype. If `target_probas_1` is on CPU and `target_probas_2` is on GPU (unlikely here, but possible in a multi-device training setup), the cat will raise a device mismatch error before any log is taken.

## 8 — Section 5.1.2: PyTorch's `cross_entropy` Function

```python
print("Logits shape:",  logits.shape)    # torch.Size([2, 3, 50257])
print("Targets shape:", targets.shape)   # torch.Size([2, 3])

logits_flat  = logits.flatten(0, 1)      # (6, 50257)
targets_flat = targets.flatten()         # (6,)

print("Flattened logits:",  logits_flat.shape)   # torch.Size([6, 50257])
print("Flattened targets:", targets_flat.shape)  # torch.Size([6,])

loss = torch.nn.functional.cross_entropy(logits_flat, targets_flat)
print(loss)   # tensor(10.7940)
```

**Summary.** `F.cross_entropy` computes the same negative-average-log-probability as Section 7's three manual steps, in a single fused call. The only preparation needed is flattening the 3-D logit tensor and 2-D target tensor into the 2-D and 1-D shapes the function expects. The result `10.7940` matches the hand-built value exactly.

**The problem it solves.** Section 7 computed loss by going through `softmax → log → gather → mean → negate` across five Python operations. Each step allocates a new tensor and, on GPU, launches a separate kernel. `F.cross_entropy` replaces all five with one numerically stable fused kernel — essential once you are running thousands of training steps on large batches.

**Why flattening is necessary — the shape contract.**

`F.cross_entropy` was designed with image classification in mind. Its expected shapes are:

```
logits:  (N, C)    ← N samples, C classes
targets: (N,)      ← N integer class labels, each in [0, C)
```

A language model's logit tensor has an extra sequence dimension. The fix is to treat every `(batch, position)` pair as an independent sample:

```
logits.shape  = (2, 3, 50257)    ← (batch, seq_len, vocab_size)
                 ↑  ↑
                 └──┴── merge these two dims
       ↓  logits.flatten(0, 1)
logits_flat.shape = (6, 50257)   ← (batch × seq_len, vocab_size)  = (N=6, C=50257)

targets.shape = (2, 3)           ← (batch, seq_len)
                 ↑  ↑
                 └──┴── merge these two dims
       ↓  targets.flatten()
targets_flat.shape = (6,)        ← (batch × seq_len,)  = (N=6,)
```

`.flatten(0, 1)` merges only dims 0 and 1, leaving dim 2 (vocab) untouched. `.flatten()` with no arguments merges all dims — safe here because `targets` is already 2-D with no vocab axis to protect.

**Matrix visualisation of the flatten.**

Before:

```
logits = [
           [                              ← Batch 0
             [l_0 … l_50256],   ← Token 0 "every"
             [l_0 … l_50256],   ← Token 1 " effort"
             [l_0 … l_50256]    ← Token 2 " moves"
           ],
           [                              ← Batch 1
             [l_0 … l_50256],   ← Token 0 "I"
             [l_0 … l_50256],   ← Token 1 " really"
             [l_0 … l_50256]    ← Token 2 " like"
           ]
         ]    shape: (2, 3, 50257)

targets = [
            [3626,  6100,   345],    ← Batch 0 targets
            [1107,   588, 11311]     ← Batch 1 targets
          ]    shape: (2, 3)
```

After `.flatten(0, 1)` and `.flatten()`:

```
logits_flat = [
                [l_0 … l_50256],   ← Sample 0  (was Batch 0, Token 0)
                [l_0 … l_50256],   ← Sample 1  (was Batch 0, Token 1)
                [l_0 … l_50256],   ← Sample 2  (was Batch 0, Token 2)
                [l_0 … l_50256],   ← Sample 3  (was Batch 1, Token 0)
                [l_0 … l_50256],   ← Sample 4  (was Batch 1, Token 1)
                [l_0 … l_50256]    ← Sample 5  (was Batch 1, Token 2)
              ]    shape: (6, 50257)

targets_flat = [3626, 6100, 345, 1107, 588, 11311]    shape: (6,)
```

**What `F.cross_entropy` does internally — dry run for sample 0.**

To make the internals concrete, use a toy vocabulary of 5 tokens instead of 50257 — the arithmetic is identical, just smaller numbers. Say the logit row for sample 0 is:

$$\text{logits\_flat}[0, :] = [2.0,\ 1.0,\ 0.5,\ -1.0,\ 3.0]$$

and the correct next token (from `targets_flat[0]`) is token index `4`, which has logit `3.0`.

**Step 1 — exponentiate every logit in the row.**

$$e^{2.0} = 7.389, \quad e^{1.0} = 2.718, \quad e^{0.5} = 1.649, \quad e^{-1.0} = 0.368, \quad e^{3.0} = 20.086$$

**Step 2 — sum all the exponentials (the softmax denominator).**

$$\sum_{v=0}^{4} e^{\text{logit}_v} = 7.389 + 2.718 + 1.649 + 0.368 + 20.086 = 32.21$$

**Step 3 — divide the target token's exponential by the sum (this is its softmax probability).**

$$P(\text{token } 4) = \frac{e^{3.0}}{32.21} = \frac{20.086}{32.21} = 0.6236$$

**Step 4 — take the negative log.**

$$L_0 = -\log(0.6236) = 0.4726$$

That is the loss for sample 0. Written as one formula:

$$L_i = -\log\!\left(\frac{e^{\text{logits}[i,\ \text{target}_i]}}{\displaystyle\sum_{v} e^{\text{logits}[i,\ v]}}\right)$$

which expands to:

$$L_i = -\text{logits}[i,\ \text{target}_i]\ +\ \log\sum_{v} e^{\text{logits}[i,\ v]}$$

In words: take the raw logit at the target index, subtract it from the log of the sum of all exponentiated logits. No explicit softmax object is constructed — the division happens inside the log analytically.

**The log-sum-exp trick for numerical stability.**

The sum $\sum_v e^{\text{logit}_v}$ overflows to `inf` in float32 if any logit is large (e.g. `logit = 100` gives $e^{100} \approx 2.7 \times 10^{43}$, above float32's ceiling of $\approx 3.4 \times 10^{38}$). PyTorch subtracts the row maximum before exponentiating — this does not change the result because the $m$ cancels out:

$$\log \sum_{v} e^{\text{logit}_v} = m + \log \sum_{v} e^{\text{logit}_v - m}, \qquad m = \max_v(\text{logit}_v)$$

Dry run with our example where $m = 3.0$:

$$e^{2.0-3.0} + e^{1.0-3.0} + e^{0.5-3.0} + e^{-1.0-3.0} + e^{3.0-3.0}$$
$$= e^{-1.0} + e^{-2.0} + e^{-2.5} + e^{-4.0} + e^{0}$$
$$= 0.368 + 0.135 + 0.082 + 0.018 + 1.000 = 1.603$$

$$\log(1.603) = 0.472$$

$$m + 0.472 = 3.0 + 0.472 = 3.472$$

$$L_0 = -3.0 + 3.472 = 0.4726 \quad \checkmark \text{ — identical result, no overflow possible}$$

**The final loss is the mean over all six samples.**

$$L = \frac{1}{6}(L_0 + L_1 + L_2 + L_3 + L_4 + L_5) = 10.7940$$

**Why this matches Section 7 exactly.**

Section 7 went `softmax → log → gather → mean → negate` across five Python operations. `F.cross_entropy` skips constructing the softmax tensor entirely and instead uses the log-sum-exp form, which is mathematically equivalent:

$$-\log\!\left(\frac{e^{\text{logit}_{\text{target}}}}{\sum_v e^{\text{logit}_v}}\right) \quad=\quad -\text{logit}_{\text{target}} + \log\sum_v e^{\text{logit}_v}$$

Both paths compute the same number. The difference is purely implementation: `F.cross_entropy` is one fused numerically stable CUDA kernel; Section 7 was five separate operations each allocating an intermediate tensor.

**Gotchas.**

Pass `logits` to `F.cross_entropy`, not `probas`. The function applies log-softmax internally. If you pass already-softmaxed probabilities, it applies softmax again and silently returns a wrong (much lower) loss value with no error. This is one of the most common silent bugs in PyTorch training loops.

`targets_flat` must be `torch.int64` (long). `torch.tensor([[3626, 6100, 345], ...])` infers `int64` from Python ints automatically, so this is safe here. If targets were created from a numpy array with `int32` dtype, PyTorch will raise `"expected scalar type Long but found Int"`.

`.flatten(0, 1)` on `logits` and `.flatten()` on `targets` produce contiguous tensors — no `.contiguous()` call needed before passing to the kernel.

## 9 — Section 5.1.2: Perplexity

```python
perplexity = torch.exp(loss)
print(perplexity)   # tensor(48725.8203)
```

**Summary.** One line: exponentiate the cross-entropy loss. The result is perplexity — a unit that reframes the loss as an effective vocabulary size, making it intuitively interpretable in a way that raw nats cannot.

**The problem it solves.** Cross-entropy loss of `10.7940` is correct but opaque. Is that good? Bad? How bad? Without a reference frame the number is hard to interpret. Perplexity converts it into "the model is choosing as if it had this many equally likely options at every step" — a framing that immediately connects to what you know about the vocabulary.

**The math.**

Perplexity is the exponential of the cross-entropy loss:

$$\text{PPL} = e^{L} = e^{-\frac{1}{N}\sum_{i=1}^{N} \log P(\text{target}_i \mid \text{context}_i)}$$

Which is the same as:

$$\text{PPL} = \left(\prod_{i=1}^{N} \frac{1}{P(\text{target}_i \mid \text{context}_i)}\right)^{1/N}$$

The second form shows what perplexity actually is: the geometric mean of the reciprocal probabilities. At each position the model assigns probability $P$ to the correct token; $1/P$ is "how many equally likely options would produce the same uncertainty." Perplexity averages that across all positions.

**Dry run.**

```
loss       = 10.7940   (from Section 8)
perplexity = e^10.7940

e^10       = 22026.5
e^0.7940   ≈ 2.212

e^10.7940  = 22026.5 × 2.212 ≈ 48,723   ≈ 48725.8203  ✓  (small rounding from float32)
```

**How to read the number.**

```
PPL = 48,725

Vocabulary size = 50,257

48,725 / 50,257 ≈ 0.97
```

The model is almost as confused as it could possibly be — effectively choosing uniformly from 97% of the entire vocabulary at every step. This is the expected baseline for a randomly initialised model with no training.

**The loss-to-perplexity table — reading the exponential relationship.**

```
Loss               Perplexity          What it means
──────────────────────────────────────────────────────────────────────
0.0                1.0                 perfect — model assigns prob 1 to every correct token
1.0                2.7                 choosing between ~3 equally likely options
3.0                20.1                choosing between ~20 options
5.0                148                 choosing between ~150 options
10.8               48,725              near-uniform over the full vocabulary
log(50257) ≈ 10.82 50,257              exactly uniform — theoretical maximum confusion
```

The exponential relationship means a loss drop from `10.8` to `3.0` — which looks like a modest 7.8 reduction on the loss scale — translates from `48,725` down to `20` on the perplexity scale. Small loss improvements in the low-loss regime correspond to enormous perplexity improvements.

**Why `log(50257) ≈ 10.82` is the ceiling.**

A perfectly uniform distribution assigns probability $1/50257$ to every token. Its cross-entropy is:

$$L_{\text{uniform}} = -\log\!\left(\frac{1}{50257}\right) = \log(50257) \approx 10.825$$

$$\text{PPL}_{\text{uniform}} = e^{10.825} = 50257$$

Our untrained model's loss of `10.7940` is just barely below this ceiling, confirming it is almost but not quite perfectly ignorant — the random weight initialisation introduces tiny asymmetries that prevent exact uniformity.

**What happens across training in this chapter.**

```
Start of training:   loss ≈ 10.79   PPL ≈ 48,725   (random weights)
After 10 epochs:     loss ≈  0.40   PPL ≈   1.49   (memorised the short story)
```

The loss drop of `10.39` nats corresponds to a perplexity drop of `48,724` — the model goes from near-total confusion to near-perfect certainty on its training text. The low final PPL of `1.49` is a signal of overfitting: the model has memorised rather than generalised.

**Gotchas.**

Perplexity is only comparable between models evaluated on the same tokenisation and the same vocabulary. A model with vocab size 32,000 (LLaMA-style) has a lower theoretical maximum PPL (`32,000`) than GPT-2 (`50,257`), so their perplexities are not directly comparable even on the same text.

`torch.exp(loss)` uses the same float32 precision as the loss itself. For very high loss values (early in training on a large model), `exp(loss)` can overflow to `inf` before the model has improved at all — this is harmless as a display metric but should not be used as a training signal or logged as a finite number.

## 10 — Section 5.1.3: Loading the Training Text (`the-verdict.txt`)

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

print(text_data[:99])
print(text_data[-99:])

total_characters = len(text_data)
total_tokens     = len(tokenizer.encode(text_data))
print("Characters:", total_characters)   # 20479
print("Tokens:",     total_tokens)       # 5145
```

**Summary.** Download Edith Wharton's short story _The Verdict_ if it is not already on disk, otherwise read it from the local file. Run two sanity checks — a character count and a token count — to confirm the text loaded correctly before building the dataset.

**The problem it solves.** Every subsequent section needs `text_data` as a raw string in memory. This cell guarantees that string exists whether the notebook is being run for the first time (download path) or resumed after the file was already saved (read path). The `os.path.exists` guard prevents re-downloading on every kernel restart.

**The download-or-read pattern — step by step.**

```
os.path.exists("the-verdict.txt")
       │
       ├── False  →  requests.get(url)          ← fetch from GitHub
       │              response.raise_for_status() ← crash immediately on 404/timeout
       │              text_data = response.text   ← raw string
       │              open(file_path, "w") ...    ← cache to disk for next run
       │
       └── True   →  open(file_path, "r") ...    ← read from local cache
                      text_data = file.read()
```

`response.raise_for_status()` is a one-line guard that converts any HTTP error (404 file not found, 503 server down, etc.) into a Python exception immediately — without it, a failed download silently produces an empty or partial `text_data` and the error only surfaces much later as a confusing shape mismatch in the DataLoader.

**Sanity checks — what to expect.**

```python
print(text_data[:99])
# 'I HAD always thought Jack Gisburn rather a cheap genius--though a good
# fellow enough--so it was no'

print(text_data[-99:])
# 've been painting the
# donkey for they had been sitting
# there for a long time and Jack had t'
```

The story opens with `"I HAD always thought"` and ends mid-paragraph — both are expected. The trailing cut is not corruption; Wharton's story simply ends where it ends in the downloaded file.

**Character to token ratio — dry run.**

```
total_characters = 20,479
total_tokens     =  5,145

ratio = 20,479 / 5,145 = 3.98 ≈ 4 characters per token
```

This 4:1 ratio is the standard rule of thumb for English text in GPT-2's BPE tokeniser. It arises because common short words (`"the"`, `"a"`, `"I"`) are single tokens of 2–3 characters, while longer words are split into 2–3 subword tokens averaging 4–6 characters each — the two effects average out to roughly 4 characters per token across normal English prose.

The ratio is useful for quick mental arithmetic when working with context windows:

```
GPT_CONFIG_124M["context_length"] = 1024 tokens

1024 tokens × 4 chars/token ≈ 4,096 characters ≈ 800 words ≈ 1–2 pages of text
```

The entire story at 5,145 tokens fits inside exactly 5 context windows. The training loop will slide a window across it and extract overlapping `(inputs, targets)` pairs — which is what the next section builds.

**Why such a small dataset deliberately.**

The book chose _The Verdict_ for three reasons that are worth internalising before the training loop starts. First, speed: 5,145 tokens trains to convergence in minutes on CPU; a real pretraining corpus of billions of tokens takes weeks on hundreds of GPUs. Second, reproducibility: a fixed text produces identical loss curves for every reader. Third, pedagogical honesty: Section 17 will explicitly label the result as severe overfitting — the model memorises one short story, it does not learn general English. The training mechanics being demonstrated are identical to what runs on a real corpus; only the scale differs. General language ability comes from loading OpenAI's pretrained weights in Section 5.5.

**Gotchas.**

`open(file_path, "w", encoding="utf-8")` and `open(file_path, "r", encoding="utf-8")` both specify `utf-8` explicitly. Omitting the encoding on Windows causes Python to use the system default (often `cp1252`), which silently misreads any non-ASCII character in the story — em-dashes and curly quotes — producing a subtly corrupted `text_data` with no error raised.

`response.text` decodes the HTTP response using the encoding declared in the server's `Content-Type` header. For plain `.txt` files on GitHub this is reliably `utf-8`, so `response.text` and `open(..., encoding="utf-8")` produce identical strings. Using `response.content` (bytes) instead would require a manual `.decode("utf-8")` call.

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

- **stride == max_length** (used here) — every token appears in exactly one training sample. Cheaper, less data, no information seen twice per epoch.
- **stride < max_length** — windows overlap. Same token can appear in multiple training samples in different positions. More training data per epoch, but the model sees the same token multiple times per epoch — risk of overfitting.

For this tiny dataset, non-overlapping windows are perfectly fine. With ~5,000 tokens and `max_length=256`, we get **~20 windows per epoch**, which is meaningful with batch size 2.

### Why `drop_last=True` for train but `False` for val?

- **train:** `drop_last=True` discards an incomplete final batch. Adam's gradient statistics misbehave on batches of different sizes during training (the variance estimate gets noisier).
- **val:** `drop_last=False` keeps the last partial batch — we want to evaluate on _all_ validation samples, not throw away a few.

### `shuffle=True` for train, `False` for val

- **train:** shuffling prevents the model from memorising the order of samples and helps each batch be a random sub-sample of the training distribution.
- **val:** unshuffled because the validation loss should be deterministic for fair comparison across epochs.

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

- Train tokens: $5145 \times 0.9 = 4630$, comfortably $\geq 256$. ✓
- Val tokens: $5145 \times 0.1 = 515$, also $\geq 256$. ✓

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

- **`num_batches=None`** — iterate every batch in the loader. Used at the _end_ of training when you want an accurate final evaluation.
- **`num_batches=5`** — stop after 5 batches. Used _during_ training every `eval_freq` steps to get a quick noisy estimate of train/val loss without spending too long on evaluation.

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

- **`cuda`** — NVIDIA GPU. Fastest by far for training.
- **`mps`** — Apple's Metal Performance Shaders backend for M1/M2/M3 chips. The check `>= (2, 9)` exists because earlier PyTorch versions had subtle correctness bugs on MPS (e.g. for `torch.multinomial` and softmax) that produced different results from CUDA/CPU. Using MPS on older PyTorch would make your output diverge from the book's.
- **`cpu`** — works everywhere but slow.

### `model.to(device)` — no reassignment needed

For `nn.Module` instances, `.to(device)` modifies the model **in place**. You don't need to write `model = model.to(device)` like you would for a tensor. (Tensors are different — for `tensor.to(device)` you _must_ reassign.)

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

#### Why `zero_grad()` is at the _start_ of the loop (not the end)?

PyTorch **accumulates** gradients across `.backward()` calls by default. This is intentional — it's what enables **gradient accumulation** (chapter 12). For standard training where every batch is a fresh update, you have to zero them yourself. Placing the call at the start (rather than after `optimizer.step()`) is slightly safer: if you ever `return` or `break` out of the loop, the gradients are reset before the next iteration of the outer loop.

#### What `loss.backward()` actually does

Autograd traversed the computation graph that was built during the forward pass (from `loss` all the way back to every parameter). At each node it applies the chain rule, accumulating gradients into the `.grad` attribute of every parameter. After this call, every weight has a gradient telling it which direction to move to reduce the loss.

#### What `optimizer.step()` actually does

For AdamW (used here): update each parameter using its `.grad`, smoothed by per-parameter momentum and variance buffers, and scaled by the learning rate. The high-level update for parameter $w$ is:

$$w \leftarrow w - \eta \cdot \hat{m} / (\sqrt{\hat{v}} + \epsilon) - \eta \cdot \lambda \cdot w$$

where $\eta$ is the learning rate, $\hat{m}$ and $\hat{v}$ are bias-corrected first and second moments of the gradients, and $\lambda$ is the weight decay coefficient.

### The bookkeeping variables

- **`tokens_seen`** — running total of how many tokens the model has been trained on. Useful as a secondary x-axis on the loss plot (section 17).
- **`global_step`** — counts every gradient update across all epochs. Used to decide _when_ to evaluate (every `eval_freq` steps).

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

- `model.eval()` — disable dropout for evaluation.
- `torch.no_grad()` — disable autograd. Evaluation doesn't need gradients; saves memory and time.
- `num_batches=eval_iter` — evaluate on only the first `eval_iter` batches, not the full loader. This makes evaluation fast (otherwise we'd be evaluating every 5 steps for as long as evaluation takes, slowing training significantly).
- `model.train()` at the end — restore training mode for the next batch.

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

The point of training from scratch on a tiny dataset is to show that the **training mechanics work** — losses go down, optimisers converge, the model learns _something_. The fact that it memorises rather than generalises is fine because we're going to load OpenAI's real pretrained weights in section 5.5 to get actual language capability.

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

- **Train loss** (solid) — drops smoothly from ~10 toward ~0.4.
- **Val loss** (dashed) — drops to ~5.5 by epoch 3, then plateaus or _rises slightly_ through epoch 10.

The growing gap between these two curves is the classic signature of **overfitting**: training loss keeps decreasing, validation loss stops decreasing (or starts increasing). The model is learning patterns specific to the training data that don't transfer to held-out text.

### The `ax1.twiny()` trick — dual x-axis

`ax1.twiny()` creates a _second_ x-axis that shares the same y-axis. We plot `tokens_seen` against `train_losses` with `alpha=0` (invisible) just to set the x-range and tick alignment on the second axis. The visible result: bottom x-axis shows epochs (0–10), top x-axis shows tokens seen (0–~40,000).

This is a very common transformer-paper convention. Tokens seen is a more "scale-free" measure than epochs because it lets you compare runs with different batch sizes / context lengths fairly.

### `MaxNLocator(integer=True)` — clean integer ticks

Forces the x-axis to use whole integers for epoch ticks (0, 1, 2, ...) instead of fractional values (0.0, 1.5, 3.0). Purely cosmetic.

### Why overfitting is happening so aggressively here

Three reinforcing factors:

1. **Tiny training set** — ~4,600 tokens.
2. **Massive model relative to data** — 124M parameters vs 4,600 tokens. That's 27,000 parameters per token. Standard rule of thumb for pretraining: you want at least 1 token per parameter (Chinchilla scaling). We are 27,000× under-data.
3. **High capacity** — even with weight_decay=0.1, the model has more than enough capacity to memorise the entire training set.

The fix would be using a real corpus (millions of tokens) or a much smaller model. We do neither here because the goal is to demonstrate the _mechanics_, not to produce a useful model.

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

- `forward` has probability ~50% → picked roughly half the time.
- `toward` has probability ~30% → picked about a third of the time.
- Each of the rest has < 5%.

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

- **T = 1** → identical to plain softmax (the `/T` is a no-op).
- **T < 1** → divides each logit by a small number, _amplifying_ differences. Big logits become huge, small logits stay small. Distribution becomes **sharper** — close to argmax.
- **T > 1** → divides each logit by a large number, _compressing_ differences. All logits become similar. Distribution becomes **flatter** — close to uniform.

### Dry-run with our 9-word example

Logits: `[4.51, 0.89, -1.90, 6.75, 1.63, -1.62, -1.89, 6.28, 1.79]`. Top three are `forward` (6.75), `toward` (6.28), `closer` (4.51).

| Temperature | `forward` prob | `toward` prob | `closer` prob | `inches` prob |
| ----------- | -------------- | ------------- | ------------- | ------------- |
| **T = 0.1** | 0.993          | 0.007         | ~0            | ~0            |
| **T = 1.0** | 0.581          | 0.343         | 0.073         | 0.002         |
| **T = 5.0** | 0.165          | 0.149         | 0.103         | 0.058         |

The differences are dramatic. At T=0.1 the sampler is effectively greedy. At T=5 it's almost uniform over the top tokens.

### Verifying with empirical sampling

```python
print_sampled_tokens(scaled_probas[1])   # T=0.1
print_sampled_tokens(scaled_probas[2])   # T=5
```

- T=0.1 → ~993 `forward`, ~7 `toward`, 0 of everything else. Practically deterministic.
- T=5 → roughly 165 each of forward/toward/closer/inches/you — much more uniform.

### When to use which

- **T < 0.5** → use for factual / deterministic outputs (Q&A, code generation). Suppresses creativity but reduces hallucinations.
- **T = 0.7–1.0** → standard for chat. Balanced.
- **T > 1.0** → creative writing, brainstorming. More varied but more likely to drift off-topic.

### Why temperature alone isn't enough

Even at moderate temperature, the long tail of _very_ low-probability tokens still gets a tiny nonzero chance. Across thousands of generation steps, those rare samples eventually fire and the model wanders into nonsense. That's why we combine temperature with top-k filtering (next section).

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

- `values` — the k largest entries, sorted in descending order.
- `indices` — their positions in the original tensor.

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

`torch.where(cond, a, b)` is element-wise: where `cond` is True, take `a`; where False, take `b`. We mask every logit _below_ `top_logits[-1] = 4.51` (the smallest of the top-3) to `-inf`. The result: only the top-3 logits survive; all others become `-inf`.

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

- **Top-k = 1** is identical to greedy (only the highest logit survives).
- **Top-k = 50** with high temperature is a common chat-bot default: enough variety to be interesting, but no chance of selecting one of the 50,000+ irrelevant vocabulary entries.

### Why not just use a probability threshold instead?

Two filtering strategies exist:

- **Top-k** — fixed number of tokens. Simple, deterministic count. Used in this notebook.
- **Top-p / nucleus** — keep tokens whose cumulative probability sums to at least `p` (typically 0.9 or 0.95). Adapts to the model's confidence: if the model is very confident in 2 tokens, only those 2 survive; if uncertain across 30 tokens, all 30 survive.

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

With `top_k=25` and `temperature=1.4`, we get a moderate amount of variety. On the (overfit) model trained earlier, the output is still nonsensical because the model only knows the verbatim training story — but the _generation mechanics_ now support real LLM-quality decoding.

---

## 23 — Section 5.4: Saving and Loading the Model state_dict

```python
torch.save(model.state_dict(), "model.pth")
```

### What is `state_dict`?

It's a Python `dict` mapping parameter names (strings like `"trf_blocks.0.att.W_query.weight"`) to their tensor values. It contains:

- Every `nn.Parameter` in the model (weights, biases, scales, shifts).
- Every persistent buffer (e.g. the causal attention mask, which is registered as a buffer rather than a parameter).

It does **not** contain:

- The model's _code_ (your `GPTModel` class definition). To restore the model, you need the same class available.
- Anything about the optimiser, the loss curve, or training metadata.

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

- **You need a fresh `GPTModel` instance first** — the `state_dict` has no notion of the class. You instantiate with the same config, then overwrite the random weights with the saved ones.
- **`map_location=device`** — controls where the loaded tensors land. Without it, a `.pth` saved on a CUDA machine would try to recreate CUDA tensors when loaded on a CPU-only machine and fail. `map_location` redirects them to the right device.
- **`weights_only=True`** — security flag (default `False` in PyTorch < 2.6, default `True` in 2.6+). Tells PyTorch to refuse to unpickle anything except tensors and basic Python types. Without this, a malicious `.pth` file could execute arbitrary code at load time. Always set `True` unless you have a specific reason not to.

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

- `scheduler.state_dict()` — if you're using a learning rate scheduler.
- `torch.get_rng_state()` and `torch.cuda.get_rng_state_all()` — to make resumed training produce the same shuffle order and dropout patterns.
- `epoch` and `global_step` — so you know where to pick up.

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

- `checkpoint`, `model.ckpt.data-00000-of-00001`, `model.ckpt.index` — the TensorFlow 1.x checkpoint format (binary weights + metadata).
- `encoder.json`, `vocab.bpe` — the BPE tokenizer files (not used here because we already have `tiktoken`).
- `hparams.json` — the model architecture configuration (n_layers, n_heads, etc.).

Total size: ~500 MB for the 124M model, scaling up to ~6 GB for the 1558M XL model.

### Why TensorFlow specifically?

OpenAI released GPT-2 in February 2019, well before PyTorch had reached parity with TensorFlow. They published the model as a TF 1.x checkpoint, and that format has remained the canonical source ever since. We use TensorFlow only to **read** the checkpoint into numpy arrays; once loaded, everything else happens in PyTorch.

### What `download_and_load_gpt2` returns

- **`settings`** — a dict with the model's hyperparameters (`n_vocab`, `n_ctx`, `n_embd`, `n_layer`, `n_head`).
- **`params`** — a nested dict of numpy arrays, structured like:
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

| OpenAI key        | Our key                | Same?                              |
| ----------------- | ---------------------- | ---------------------------------- |
| `n_vocab = 50257` | `vocab_size = 50257`   | ✓                                  |
| `n_ctx = 1024`    | `context_length = 256` | ✗ — we shortened ours for training |
| `n_embd = 768`    | `emb_dim = 768`        | ✓                                  |
| `n_head = 12`     | `n_heads = 12`         | ✓                                  |
| `n_layer = 12`    | `n_layers = 12`        | ✓                                  |

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

In chapter 3 we built `MultiHeadAttention` with `bias=False` on the Q/K/V projections to match the conventions of modern LLMs. OpenAI's _original_ GPT-2 (2019) used `bias=True` — they didn't drop the bias term until later models. To load their weights, our `MultiHeadAttention` must have the same bias parameters available to copy into.

### Why instantiate a _new_ `gpt` model instead of reusing `model`?

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

The `assign` helper's shape assertion will catch most errors. The remaining failure mode — assigning the _right_ shape but the _wrong_ tensor (e.g. confusing `c_fc` with `c_proj`) — produces a model that runs but outputs gibberish. The only way to detect that is to run inference and check whether the output is coherent. That's exactly what section 30 does.

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

- **`top_k=50`** — fairly permissive, gives the model 50 candidate tokens at each step.
- **`temperature=1.5`** — quite high, encouraging diverse and creative outputs.

These are typical "creative writing" settings. For factual Q&A you would use `top_k=10` and `temperature=0.3` or lower.

### Sanity-check value of this cell

If `load_weights_into_gpt` had a subtle bug (e.g. swapped Q and K weights, or forgot to transpose `c_fc`), the model would still run — but the output would be incoherent or completely random. Coherent English is **strong evidence that the weight transfer worked correctly**.

### What you've actually built by the end of chapter 5

- A complete GPT-2 model architecture (chapter 4).
- A working training loop that you've used to overfit a tiny dataset (sections 15–17).
- A flexible inference engine with greedy, sampling, temperature, top-k, and early-stopping (sections 18–22).
- The ability to load arbitrary GPT-2 checkpoint sizes from OpenAI and run inference with them (sections 25–30).

This is, structurally, **everything an LLM library does**. From here, chapters 6 and 7 add fine-tuning (for classification and instruction following), but the core machine — the architecture, the training, the generation — is fully assembled.
