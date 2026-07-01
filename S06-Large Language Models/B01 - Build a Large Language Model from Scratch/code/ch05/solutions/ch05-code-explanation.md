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
split_idx   = int(train_ratio * len(text_data))
train_data  = text_data[:split_idx]
val_data    = text_data[split_idx:]

torch.manual_seed(123)

train_loader = create_dataloader_v1(
    train_data,
    batch_size=2,
    max_length=GPT_CONFIG_124M["context_length"],   # 256
    stride=GPT_CONFIG_124M["context_length"],       # 256 — no overlap
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

**Summary.** Split `text_data` into a 90% training portion and a 10% validation portion, then wrap each in a `DataLoader` that yields `(inputs, targets)` batches of shape `(2, 256)`. The train loader shuffles and drops the last incomplete batch; the val loader is deterministic and keeps every sample.

**The problem it solves.** The model needs a repeatable supply of `(inputs, targets)` tensor pairs drawn from the training text. It also needs a held-out validation set — text the model never trains on — to measure whether it is generalising or merely memorising. The `DataLoader` handles the sliding window, the batching, and the shuffling automatically each epoch.

**The train/val split — dry run.**

```
len(text_data) = 20,479 characters

split_idx = int(0.90 × 20,479) = int(18,431.1) = 18,431

train_data = text_data[:18,431]    ← 18,431 characters  ≈ 90%
val_data   = text_data[18,431:]   ←  2,048 characters  ≈ 10%
```

In tokens (applying the 4 chars/token rule of thumb):

```
train_data  ≈ 18,431 / 4 ≈ 4,608 tokens
val_data    ≈  2,048 / 4 ≈   512 tokens
```

**What `create_dataloader_v1` does — the sliding window.**

The function tokenises the text string and slides a window of `max_length=256` tokens across it with step `stride=256`. Each window position produces one `(input, target)` pair: input is the window, target is the same window shifted left by one token. Using small numbers to illustrate — say `max_length=4, stride=4` on a 12-token sequence `[t0, t1, ..., t11]`:

```
Window 0:  input = [t0,  t1,  t2,  t3]    target = [t1,  t2,  t3,  t4]
Window 1:  input = [t4,  t5,  t6,  t7]    target = [t5,  t6,  t7,  t8]
Window 2:  input = [t8,  t9, t10, t11]    target = [t9, t10, t11,  t12]  ← needs t12
```

The last window needs one token beyond the sequence end, so a sequence of $N$ tokens yields $\lfloor (N - 1) / \text{stride} \rfloor$ complete windows.

Applied to the real numbers:

```
train tokens ≈ 4,608    max_length = 256    stride = 256

windows = floor((4,608 - 1) / 256) = floor(4,607 / 256) = floor(17.99) = 17

val tokens ≈ 512

windows = floor((512 - 1) / 256) = floor(511 / 256) = floor(1.996) = 1
```

So the train loader has 17 windows and the val loader has 1 window.

**Why `stride == max_length` — non-overlapping windows.**

With `stride=256` and `max_length=256` every token appears in exactly one window. No token is seen twice in a single epoch:

```
stride = max_length = 256   (this section — non-overlapping):

Window 0:  [t0   …  t255]
Window 1:  [t256 …  t511]
Window 2:  [t512 …  t767]
           ↑
           no overlap — each token in exactly one window
```

If `stride < max_length`, windows overlap and the same token appears in multiple windows within one epoch:

```
stride = 128, max_length = 256   (overlapping):

Window 0:  [t0   …  t255]
Window 1:  [t128 …  t383]   ← tokens t128–t255 appear again
Window 2:  [t256 …  t511]
           ↑
           overlap region — same tokens seen twice per epoch
```

Overlapping gives the model more training signal per epoch but risks overfitting faster on a tiny dataset. Non-overlapping is the safer choice here.

**Batch shapes produced by each loader.**

With `batch_size=2` and `max_length=256`, each `(inputs, targets)` batch has shape:

```
inputs.shape  = (2, 256)    ← (batch_size, max_length)
                 ↑  ↑
              batch seq_len

targets.shape = (2, 256)    ← same shape, each row shifted left by one token
```

17 training windows with `batch_size=2` gives 8 complete batches of 2, with 1 window left over. `drop_last=True` discards that leftover, so the train loader yields exactly 8 batches per epoch. The val loader has 1 window, which is below `batch_size=2` but `drop_last=False` keeps it anyway — it yields one partial batch of size 1.

**Why `drop_last=True` for train but `False` for val.**

During training, the optimiser's gradient statistics (especially Adam's running variance estimate) become noisier on a batch that is smaller than expected. Discarding the last incomplete training batch keeps every gradient update based on the same batch size. For validation there is no gradient computation — we are only measuring loss — so throwing away any validation samples would give a slightly inaccurate val loss. `drop_last=False` keeps every sample.

**Why `shuffle=True` for train but `False` for val.**

Shuffling the training windows each epoch prevents the model from memorising the order of samples and ensures each batch is a random draw from the training distribution. Validation must not be shuffled — the val loss should be identical on every evaluation pass for fair comparison across epochs, and determinism makes debugging easier.

**`torch.manual_seed(123)` before creating the loaders.**

The seed pins the internal random number generator that the train loader uses for shuffling. Without it, the window order changes every time the notebook is run, making the loss curve non-reproducible. The seed must be set before `create_dataloader_v1` is called — setting it afterward has no effect on the already-created loader's shuffle state.

Sure. Let me build it from scratch with tiny numbers.

**The setup — think of windows first, batches second.**

The sliding window runs across the tokenised text and cuts it into independent chunks of `max_length` tokens. Each chunk is one window. With `max_length=4` and `stride=4` on a 16-token training text:

```
full token sequence:
[t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15]

Window 0:  [t0,  t1,  t2,  t3]
Window 1:  [t4,  t5,  t6,  t7]
Window 2:  [t8,  t9,  t10, t11]
Window 3:  [t12, t13, t14, t15]

total windows = 4
```

Each window immediately produces one `(input, target)` pair by shifting left one token:

```
Window 0:  input = [t0,  t1,  t2,  t3]    target = [t1,  t2,  t3,  t4]
Window 1:  input = [t4,  t5,  t6,  t7]    target = [t5,  t6,  t7,  t8]
Window 2:  input = [t8,  t9,  t10, t11]   target = [t9,  t10, t11, t12]
Window 3:  input = [t12, t13, t14, t15]   target = [t13, t14, t15, t16]
```

So at this point we have 4 individual samples, each of length 4 tokens. The DataLoader has not been involved yet — these are just the raw pairs.

**Now the DataLoader groups windows into batches.**

With `batch_size=2`, the DataLoader stacks two windows side by side into one tensor:

```
Batch 0:
  inputs  = [[t0,  t1,  t2,  t3],    ← Window 0
              [t4,  t5,  t6,  t7]]    ← Window 1
  shape: (2, 4)   ← (batch_size=2, max_length=4)

Batch 1:
  inputs  = [[t8,  t9,  t10, t11],   ← Window 2
              [t12, t13, t14, t15]]   ← Window 3
  shape: (2, 4)   ← (batch_size=2, max_length=4)
```

So with 4 windows and `batch_size=2` you get exactly 2 batches per epoch. Each batch covers `2 × 4 = 8` tokens. Two batches cover all `16` tokens — the full training text, nothing skipped.

**Now scaling back to the real numbers.**

```
train tokens  ≈ 4,608
max_length    = 256
stride        = 256

windows = floor((4,608 - 1) / 256) = 17 windows
```

17 windows, `batch_size=2`:

```
Batch 0:   Window 0  + Window 1     → inputs shape (2, 256)
Batch 1:   Window 2  + Window 3     → inputs shape (2, 256)
Batch 2:   Window 4  + Window 5     → inputs shape (2, 256)
...
Batch 7:   Window 14 + Window 15    → inputs shape (2, 256)
──────────────────────────────────────────────────────────
Window 16  ← leftover, only 1 window, can't fill a batch of 2
            drop_last=True discards it
```

Result: 8 complete batches per epoch, 1 window discarded. Each batch covers `2 × 256 = 512` tokens. 8 batches cover `8 × 512 = 4,096` tokens out of the ~4,608 available — the discarded window accounts for the missing ~512.

The key thing to hold onto: `batch_size` controls how many windows are stacked together into one tensor. It does not change the length of each sequence — that is always `max_length`. The shape `(2, 256)` means "2 independent sequences, each 256 tokens long, processed in parallel in one forward pass."

**Gotchas.**

`num_workers=0` uses the main Python process for data loading. On Windows, any `num_workers > 0` requires wrapping the training loop inside `if __name__ == "__main__":` — without it, each worker process re-imports the script and spawns more workers recursively, causing a crash. For a 20 KB text file the overhead of forking workers would exceed any loading benefit anyway.

The `split_idx` cuts on a character boundary, not a token boundary. The tokeniser sees `train_data` and `val_data` as independent strings and re-tokenises from the start of each — so the first token of `val_data` is always a clean token start, never a broken subword fragment from splitting mid-token.

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

## 13 — Section 5.1.3: `calc_loss_batch` and `calc_loss_loader`

```python
def calc_loss_batch(input_batch, target_batch, model, device):
    input_batch  = input_batch.to(device)
    target_batch = target_batch.to(device)
    logits = model(input_batch)
    loss   = torch.nn.functional.cross_entropy(
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

**Summary.** Two utility functions that will be called from the training loop on every evaluation step. `calc_loss_batch` computes the cross-entropy loss for a single `(inputs, targets)` batch — one forward pass, one scalar. `calc_loss_loader` iterates a DataLoader and averages the loss across multiple batches, with an option to stop early for a cheap mid-training estimate.

**The problem they solve.** The training loop needs to evaluate loss on both training and validation data repeatedly — at the end of every epoch and optionally mid-epoch. Without these helpers the loop body would be cluttered with repeated flatten-and-cross-entropy boilerplate, device management, and accumulation logic. Bundling them as named functions keeps the loop readable and the device handling in one place.

**`calc_loss_batch` — shape story for one batch.**

```
input_batch.shape  = (2, 256)    ← (batch_size, seq_len)  on CPU from DataLoader
       ↓  .to(device)            ← move to GPU if available, no-op if already on device
input_batch.shape  = (2, 256)    ← same shape, now on the correct device

       ↓  model(input_batch)
logits.shape = (2, 256, 50257)   ← (batch_size, seq_len, vocab_size)

       ↓  logits.flatten(0, 1)
shape = (512, 50257)             ← (batch_size × seq_len, vocab_size)

target_batch.shape = (2, 256)
       ↓  target_batch.flatten()
shape = (512,)                   ← (batch_size × seq_len,)

       ↓  F.cross_entropy(logits_flat, targets_flat)
loss   = scalar tensor           ← mean negative log probability over 512 positions
```

This is mathematically identical to what Section 8 did manually — flatten both tensors, pass to `F.cross_entropy`, get a scalar. The only addition here is the `.to(device)` calls.

**Why `.to(device)` lives inside `calc_loss_batch` and not in the DataLoader.**

The DataLoader runs on CPU by default — it loads data from disk and constructs tensors in CPU memory. The model's weights live on whichever device was chosen (`cuda`, `mps`, or `cpu`). PyTorch requires that both the input tensor and the model weights be on the same device before a forward pass, otherwise it raises a device mismatch error immediately.

Putting `.to(device)` inside `calc_loss_batch` means the transfer happens as late as possible — just before the forward pass — which is the standard pattern. It also means the same function works unchanged regardless of device: pass `device="cpu"` for debugging, `device="cuda"` for training, no other change needed.

**`calc_loss_loader` — accumulation logic dry run.**

Say the train loader has 8 batches and we call `calc_loss_loader(train_loader, model, device, num_batches=3)`:

```
num_batches = min(3, 8) = 3      ← cap at loader length

i=0:  loss = calc_loss_batch(...)   → e.g. 10.81   total_loss = 10.81
i=1:  loss = calc_loss_batch(...)   → e.g. 10.79   total_loss = 21.60
i=2:  loss = calc_loss_batch(...)   → e.g. 10.83   total_loss = 32.43
i=3:  i < num_batches is False      → break

return 32.43 / 3 = 10.81   ← average loss over 3 batches
```

With `num_batches=None`:

```
num_batches = len(data_loader) = 8   ← iterate every batch

return total_loss / 8                ← accurate full-loader average
```

The two modes serve different purposes. During training, evaluating all 8 batches every few steps would be slow — `num_batches=5` gives a quick noisy estimate cheap enough to run frequently. At the end of training, `num_batches=None` gives the accurate final number reported in the results.

**Why `loss.item()` and not `loss` directly.**

`loss` returned by `F.cross_entropy` is a 0-dimensional PyTorch tensor with a full autograd computation graph attached — the graph records every operation from input through the model to the loss, ready for `.backward()`. Summing 8 such tensors into `total_loss` would keep all 8 graphs alive in memory simultaneously, potentially several GB of activations for a 124M model.

`loss.item()` extracts the scalar value as a plain Python float and lets the graph be garbage-collected immediately. The running sum `total_loss` is then just a Python float — cheap, graph-free, and safe to accumulate across many batches.

**The three guard cases at the top of `calc_loss_loader`.**

```
len(data_loader) == 0   →  return float("nan")
                               ↑
                   empty loader — total_loss / 0 would crash;
                   nan is a visible signal that the split was misconfigured

num_batches is None     →  num_batches = len(data_loader)
                               ↑
                   evaluate every batch — used for final accurate reporting

num_batches provided    →  num_batches = min(num_batches, len(data_loader))
                               ↑
                   cap at loader length — prevents requesting more batches
                   than exist (e.g. asking for 10 batches from a 1-batch val loader)
```

The `min` in the third case is important for the val loader specifically. The val loader has only 1 batch. If the training loop calls `calc_loss_loader(val_loader, ..., num_batches=5)`, without the `min` the loop would try to iterate 5 batches from a loader that only has 1, iterate only once, and then divide by 5 — returning a loss that is 5× too small. The `min` prevents this silently wrong result.

**Gotchas.**

`model` must be in `eval()` mode when these functions are called for validation. `model.eval()` disables dropout and switches BatchNorm to use running statistics — without it, the val loss includes random dropout noise and is not a fair measure of the model's actual performance. The training loop is responsible for calling `model.eval()` before evaluation and `model.train()` before resuming training updates.

`total_loss` is initialised as `0.` (a Python float) rather than `0` (an integer) or `torch.tensor(0.)`. This ensures the accumulated sum stays a Python float throughout and never accidentally triggers tensor semantics or holds a gradient.

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

Let me first check what section number we're on and read the existing notes style carefully.Good — I have the full context. Now writing the rewritten section 15 with full data flow tracing and a concrete mini-example throughout.

---

## 15 — Section 5.2: The Training Loop — `train_model_simple`

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

**Summary.** The canonical PyTorch training loop. Every neural network you will ever train uses this same skeleton — the only things that change between projects are the model, the loss function, and the data. This function wraps that skeleton with two extras: periodic evaluation of train and val loss every `eval_freq` steps, and a qualitative text sample generated after every epoch.

**The problem it solves.** The model currently has random weights and produces gibberish. This function feeds it real text batch by batch, computes how wrong its predictions are, and nudges every weight in the direction that reduces that error. After enough repetitions the weights encode real statistical patterns of English.

**The four-step optimisation rhythm — what happens for every batch.**

Every batch goes through exactly these four steps in order:

```
Step 1 — optimizer.zero_grad()
Step 2 — loss = calc_loss_batch(input_batch, target_batch, model, device)
Step 3 — loss.backward()
Step 4 — optimizer.step()
```

To make this concrete, use a toy setup: `batch_size=2`, `seq_len=4`, `vocab_size=5`. The batch arrives as:

```
input_batch  = [[t0, t1, t2, t3],    shape: (2, 4)
                 [t4, t5, t6, t7]]

target_batch = [[t1, t2, t3, t4],    shape: (2, 4)  ← shifted left by one
                 [t5, t6, t7, t8]]
```

**Step 1 — `optimizer.zero_grad()`.**

PyTorch accumulates gradients by default — every call to `.backward()` adds to whatever is already stored in each parameter's `.grad` attribute rather than overwriting it. This is intentional: it enables gradient accumulation across multiple small batches when GPU memory is too tight to fit one large batch. For standard training where every batch is a fresh independent update, the accumulated gradients from the previous batch must be cleared before computing new ones. Zeroing at the start of the batch (rather than after `optimizer.step()`) is safer: if the loop ever exits early via a `break` or exception, the stale gradients are gone before the next iteration begins.

**Step 2 — `loss = calc_loss_batch(...)`.**

The data flows through the model:

```
input_batch  (2, 4)
       ↓  model(input_batch)          ← full GPT forward pass
logits       (2, 4, 5)                ← (batch, seq_len, vocab_size)
       ↓  logits.flatten(0, 1)
             (8, 5)                   ← 8 independent token predictions
       ↓  target_batch.flatten()
             (8,)                     ← 8 correct next-token labels
       ↓  F.cross_entropy(...)
loss         scalar                   ← mean negative log probability over 8 positions
```

While this forward pass runs, PyTorch's autograd engine silently records every operation into a computation graph — a map of exactly how `loss` depends on every weight in the model. This graph is what makes Step 3 possible.

**Step 3 — `loss.backward()`.**

Autograd walks the computation graph in reverse — from the scalar `loss` all the way back to every weight matrix — and applies the chain rule at each node. The result is that every parameter `p` in the model now has `p.grad` populated: a tensor of the same shape as `p` telling the optimiser which direction to move that parameter to reduce the loss.

Conceptually:

```
loss
  ↑ chain rule applied at each node travelling backwards
out_head weights        → .grad populated
LayerNorm scale/shift   → .grad populated
FFN weight matrices     → .grad populated   (× 12 blocks)
Attention Q/K/V/O       → .grad populated   (× 12 blocks)
token embedding table   → .grad populated
positional embedding    → .grad populated
```

Every trainable parameter in the 124M model receives its gradient in this single call. No weight is updated yet — `.backward()` only computes and stores the gradients.

**Step 4 — `optimizer.step()`.**

The optimiser reads every parameter's `.grad` and updates the parameter value. For AdamW — the optimiser used here — the update for each parameter $w$ is:

$$w \leftarrow w - \eta \cdot \frac{\hat{m}}{\sqrt{\hat{v}} + \epsilon} - \eta \cdot \lambda \cdot w$$

where $\eta$ is the learning rate, $\hat{m}$ is the bias-corrected running mean of past gradients (momentum — smooths noisy updates), $\hat{v}$ is the bias-corrected running mean of squared gradients (adapts the step size per parameter), and $\lambda$ is the weight decay coefficient (shrinks large weights slightly each step). The net effect is that every weight shifts by a small amount in the direction that reduces the loss on this batch.

**Bookkeeping variables — what they track and why.**

```
tokens_seen  ← running total of tokens the model has trained on
               updated by input_batch.numel() = batch_size × seq_len = 2 × 256 = 512
               per batch — useful as a device-independent x-axis on the loss plot
               (wall-clock time varies by hardware; tokens seen does not)

global_step  ← counts every gradient update, starting from -1 so the first
               update lands on step 0 and triggers an eval immediately
               used to decide when to evaluate: if global_step % eval_freq == 0
```

**The full epoch loop — tracing one epoch with real numbers.**

With 8 training batches, `eval_freq=5`, `eval_iter=5`:

```
epoch 0 begins  →  model.train()

  batch 0:  zero_grad → forward → backward → step
            tokens_seen = 512,  global_step = 0
            0 % 5 == 0  →  evaluate_model() called
            print "Ep 1 (Step 000000): Train loss X.XXX, Val loss X.XXX"

  batch 1:  zero_grad → forward → backward → step
            tokens_seen = 1024, global_step = 1
            1 % 5 != 0  →  no evaluation

  batch 2:  global_step = 2,  no evaluation
  batch 3:  global_step = 3,  no evaluation
  batch 4:  global_step = 4,  no evaluation

  batch 5:  zero_grad → forward → backward → step
            tokens_seen = 3072, global_step = 5
            5 % 5 == 0  →  evaluate_model() called
            print "Ep 1 (Step 000005): Train loss X.XXX, Val loss X.XXX"

  batch 6:  global_step = 6,  no evaluation
  batch 7:  global_step = 7,  no evaluation

epoch 0 ends  →  generate_and_print_sample() called
                 prints 50 generated tokens from start_context

epoch 1 begins  →  model.train()   ← re-enables dropout, which eval turned off
  ...
```

**`evaluate_model` — the inner evaluation helper.**

```python
def evaluate_model(model, train_loader, val_loader, device, eval_iter):
    model.eval()
    with torch.no_grad():
        train_loss = calc_loss_loader(train_loader, model, device, num_batches=eval_iter)
        val_loss   = calc_loss_loader(val_loader,   model, device, num_batches=eval_iter)
    model.train()
    return train_loss, val_loss
```

`model.eval()` disables dropout — during evaluation, predictions must be deterministic so the loss is comparable across calls. `torch.no_grad()` disables autograd graph construction for the evaluation forward passes — no gradients are needed and skipping graph construction saves the memory those intermediate activations would have occupied. `num_batches=eval_iter` stops after `eval_iter` batches rather than running the full loader — a quick noisy estimate is cheap enough to run every few steps without slowing training. `model.train()` at the end restores dropout before returning so the very next training batch is regularised correctly.

**`generate_and_print_sample` — qualitative monitor after each epoch.**

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

After each epoch, generate 50 tokens from `start_context` and print them. This is a qualitative sanity check — watching the output progress from random gibberish in epoch 1 to recognisable English in epoch 5 to near-verbatim story text by epoch 10 confirms the model is learning without needing to interpret any numbers. `context_size = model.pos_emb.weight.shape[0]` reads the positional embedding table's first dimension rather than hard-coding `256` — if you later swap in a GPT-2 model with a 1024-token context, this line keeps working without modification.

**Gotchas.**

`model.train()` must be called at the top of every epoch, not just once before the outer loop. `evaluate_model` calls `model.eval()` mid-loop and then calls `model.train()` before returning — but `generate_and_print_sample` also calls `model.eval()` at the end of each epoch and restores `model.train()` at its end. If either helper forgot its `model.train()` call, all subsequent training batches would run without dropout. The explicit `model.train()` at the top of each epoch is a belt-and-suspenders guard against this.

`optimizer.zero_grad()` must come before `calc_loss_batch`, never after `optimizer.step()`. Placing it after the step feels logical — "clean up after yourself" — but if the loop breaks between `step()` and the next iteration's `zero_grad()`, the stale gradients survive into the next epoch and corrupt the first update of that epoch.

`input_batch.numel()` returns `batch_size × seq_len = 2 × 256 = 512` — the total number of integer token IDs in the batch. This counts input tokens only, not target tokens, even though both tensors are the same size. The convention is to count inputs: each input token corresponds to one forward-pass position and one gradient signal, so `numel()` of `input_batch` is the natural measure of "how much text the model processed this step."

### Extra Notes

`track_tokens_seen` is the list that accumulates `tokens_seen` at every evaluation point — every time `global_step % eval_freq == 0`, the current value of `tokens_seen` gets appended to it alongside the train and val losses for that step.

```python
track_tokens_seen.append(tokens_seen)
```

So after training finishes, you have three parallel lists of equal length, one entry per evaluation:

```
train_losses      = [10.81, 9.32, 7.14, ...]
val_losses        = [10.79, 9.41, 7.30, ...]
track_tokens_seen  = [512,   3072, 5632, ...]
```

The reason it exists is for plotting. Section 17 (the next section in the chapter, the loss curve visualisation) plots train and val loss against `track_tokens_seen` on the x-axis instead of against epoch number or step number. The book uses this specifically:

```python
fig, ax1 = plt.subplots()
ax1.plot(epochs_seen, train_losses, label="Training loss")
ax1.plot(epochs_seen, val_losses, linestyle="-.", label="Validation loss")
ax1.set_xlabel("Epochs")

ax2 = ax1.twiny()  # second x-axis sharing the same y-axis
ax2.plot(track_tokens_seen, train_losses, alpha=0)  # invisible plot for tick alignment
ax2.set_xlabel("Tokens seen")
```

It is plotted as a _second_, parallel x-axis at the top of the same chart — epochs on the bottom axis, tokens seen on the top axis, both describing the same points.

Why tokens seen matters as a metric: epoch number and step number are both dependent on your specific configuration — batch size, sequence length, dataset size all change what one "step" or one "epoch" represents. Tokens seen is a config-independent measure of how much actual data the model has processed, which is the standard way training progress is reported and compared across different LLM training runs in research papers — you'll see this same x-axis convention ("tokens seen" or "tokens trained") in essentially every scaling-law or pretraining paper.

We will use it — it gets returned from `train_model_simple` precisely so the next section (the loss plotting section) can consume it.

#### Quick Summary

A quick walkthrough of what each line is doing:

`optimizer.zero_grad()` — clears out the gradients left over from the previous batch, so this batch starts with a clean slate.

`loss = calc_loss_batch(...)` — runs the batch through the model (forward pass) and computes a single number: how wrong the model's predictions were on this batch.

`loss.backward()` — this is where PyTorch figures out, for every single weight in the model, "if I nudge this weight up or down a tiny bit, does the loss go up or down, and by how much." It stores that answer in each weight's `.grad`. No weights change yet — this step only calculates the directions.

`optimizer.step()` — now the actual update happens. The optimiser looks at every weight's `.grad` from the step above and actually moves the weight a small amount in the direction that reduces the loss.

`tokens_seen += input_batch.numel()` — just counting how many tokens we've fed the model so far, for tracking/plotting later.

`global_step += 1` — counting how many batches (updates) we've done in total, across all epochs.

`if global_step % eval_freq == 0:` — every `eval_freq` steps, pause training briefly and check how the model is doing on both train and val data, then print it and save it for the loss curve plot later.

`generate_and_print_sample(...)` — once per epoch (after going through all batches), generate some sample text so you can eyeball how the model's output is improving.

So in one sentence per pair: `zero_grad` resets, `loss = calc_loss_batch` measures how wrong, `backward` calculates how to fix it, `step` actually fixes it.

#### Step Count

`global_step` increases by 1 every single time the inner `for input_batch, target_batch in train_loader:` loop runs one iteration. One iteration of that loop = one batch = one full forward pass + backward pass + weight update.

Let's trace it concretely with your earlier example: 8 batches per epoch, 2 epochs total.

```
global_step starts at -1   (before any batch is processed)

Epoch 1:
  batch 0 processed (zero_grad → forward → backward → step)  → global_step becomes 0
  batch 1 processed                                            → global_step becomes 1
  batch 2 processed                                            → global_step becomes 2
  batch 3 processed                                            → global_step becomes 3
  batch 4 processed                                            → global_step becomes 4
  batch 5 processed                                            → global_step becomes 5
  batch 6 processed                                            → global_step becomes 6
  batch 7 processed                                            → global_step becomes 7
  ← end of epoch 1, 8 batches processed, global_step = 7

Epoch 2:
  batch 0 processed                                            → global_step becomes 8
  batch 1 processed                                            → global_step becomes 9
  ...
  batch 7 processed                                            → global_step becomes 15
  ← end of epoch 2, global_step = 15
```

So `global_step` does **not** reset at the start of each epoch — it just keeps climbing across the entire training run, epoch after epoch. After 2 epochs of 8 batches each, you've done 16 total weight updates, and `global_step` ends at 15 (because it started at -1, not 0).

That's also exactly why it starts at `-1` instead of `0` — so that the very first batch (`global_step` becomes `0` after incrementing) immediately satisfies `0 % eval_freq == 0` and triggers an evaluation right at the start of training, giving you a baseline loss before any meaningful training has happened.

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

## 22 — Section 5.3.3: The Full `generate()` Function

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

**Summary.** The production-grade generation function that replaces `generate_text_simple` from Chapter 4. It keeps the same autoregressive skeleton — crop context, forward pass, append, repeat — but adds three independent controls layered on top: top-k filtering to restrict the candidate pool, temperature to control how random the sampling is within that pool, and early stopping when an end-of-sequence token is produced.

**The problem it solves.** `generate_text_simple` always picks the single highest-probability token (pure argmax). This is deterministic and often repetitive — the same prompt always produces the exact same continuation, and the model tends to loop into repeated phrases. `generate` introduces controlled randomness so the same prompt can produce varied, more natural-sounding continuations, while still letting you dial the randomness down to near-deterministic when you want reliability.

**The five-step loop, traced with concrete numbers.**

Use a toy vocabulary of 5 tokens to make every transformation visible. Say at one generation step the model produces these raw logits for the last position:

```
logits = [1.2, 3.5, 0.8, 4.1, 2.0]    ← one score per vocab token (indices 0-4)
```

**Step 1 — crop context, forward pass, keep last position.**

The model has a fixed maximum context length it can accept at once — `context_size`. As generation proceeds, `idx` grows by one token every iteration, so it will eventually exceed `context_size`. Step 1 solves two separate problems: trimming the input down to a size the model can accept, and then extracting only the one prediction we actually need from the model's output.

**Dry run — trimming the input with `idx[:, -context_size:]`.**

Say `context_size = 5`, and generation has already produced 8 tokens so far:

```
idx = [[5, 12, 3, 47, 9, 21, 6, 30]]        shape: (1, 8)
        ↑                        ↑
   oldest tokens              newest token (just appended last iteration)
```

The model was trained with a maximum window of 5 tokens — it has no positional embedding beyond position 4, so feeding it all 8 tokens would crash. `idx[:, -context_size:]` slices off everything except the last 5 tokens:

```
idx[:, -5:]

idx_cond = [[47, 9, 21, 6, 30]]             shape: (1, 5)
              ↑               ↑
        5th-from-last      most recent token
```

Tokens `5, 12, 3` are dropped — they fell outside the sliding window and the model never sees them at this step. Only the 5 most recent tokens go into the forward pass.

**Dry run — the forward pass and what the output shape means.**

```
idx_cond.shape = (1, 5)                     ← (batch, seq_len)
       ↓  model(idx_cond)
logits.shape   = (1, 5, vocab_size)         ← one prediction PER input position
```

A transformer predicts "what comes next" at every single input position simultaneously, not just at the end. So this `logits` tensor actually contains 5 separate predictions:

```
logits[0, 0, :]  ← prediction for what comes after token 47   (position 0)
logits[0, 1, :]  ← prediction for what comes after token 9    (position 1)
logits[0, 2, :]  ← prediction for what comes after token 21   (position 2)
logits[0, 3, :]  ← prediction for what comes after token 6    (position 3)
logits[0, 4, :]  ← prediction for what comes after token 30   (position 4, LAST)
```

During training, all 5 of these predictions are useful — we have a ground-truth target at every position and compute loss against all of them at once (this is exactly the `(batch, seq_len, vocab)` flattening you saw back in Section 8). But during generation there are no targets for positions 0 through 3 — those tokens are already fixed, already part of the sequence. The only question we're actually asking right now is "what token comes after the most recent one, token 30?" — and that answer lives only in `logits[0, 4, :]`.

> ## Quick Reference: PyTorch Slicing Syntax
>
> **The comma splits dimensions.** For a tensor `x[A, B]`, everything before the comma controls dim 0, everything after controls dim 1 (and so on for more dims).
>
> **A bare colon `:` means "keep everything" along that dimension.**
>
> **`start:stop` is a slice range.** Negative numbers count backward from the end.
>
> ```
> my_list = [10, 20, 30, 40, 50, 60, 70, 80]
> # index:     0   1   2   3   4   5   6   7
> # neg idx:  -8  -7  -6  -5  -4  -3  -2  -1
>
> my_list[-5:]   →  [40, 50, 60, 70, 80]    ← last 5 elements
> ```
>
> **Applied to `idx[:, -context_size:]`** (a 2D tensor, shape `(batch, seq_len)`):
>
> ```
> idx.shape = (1, 8)
> idx       = [[5, 12, 3, 47, 9, 21, 6, 30]]
>
> idx[:, -5:]
>      ↑   ↑
>    keep   take last 5 along seq_len
>    all
>    rows
>
> → [[47, 9, 21, 6, 30]]    shape: (1, 5)
> ```
>
> `:` before the comma → keep all rows (batch). `-5:` after the comma → slice the last 5 positions of the sequence dimension.
>
> **A single number (no colon) removes that dimension; a slice keeps it.** This matters for `logits[:, -1, :]` (a 3D tensor, shape `(batch, seq_len, vocab)`):
>
> ```
> logits[:, -1, :]
>         ↑   ↑   ↑
>       dim0 dim1 dim2
>
> dim0 → ":"   = keep all rows (batch)
> dim1 → "-1"  = single INDEX, not a slice → grabs just the last position AND collapses that dimension
> dim2 → ":"   = keep all columns (full vocab)
> ```
>
> ```
> logits.shape = (1, 5, 50257)
>        ↓  logits[:, -1, :]
> logits.shape = (1, 50257)        ← seq_len dimension is gone, not size-1
> ```
>
> Compare to `-1:` (with trailing colon) — that would be a slice from the last position to the end, which keeps the dimension as size 1 instead of removing it: `logits[:, -1:, :]` would give shape `(1, 1, 50257)`.

**Dry run — extracting the last position with `logits[:, -1, :]`.**

```
logits[:, -1, :]   ← keep only index 4 (the last position) along the seq_len dimension

logits.shape = (1, vocab_size)              ← the 4 other predictions are discarded
```

This single row is what gets passed on to Steps 2 and 3 (top-k filtering and temperature/sampling) to decide the actual next token to append.

**Putting both slicing operations together.**

```
idx.shape       = (1, 8)                    ← full sequence generated so far
       ↓  idx[:, -context_size:]            ← trim to the model's max window (an INPUT problem)
idx_cond.shape  = (1, 5)
       ↓  model(idx_cond)
logits.shape    = (1, 5, vocab_size)        ← one prediction per position in idx_cond
       ↓  logits[:, -1, :]                  ← keep only the prediction for the newest token (an OUTPUT problem)
logits.shape    = (1, vocab_size)           ← exactly what's needed to pick the next token
```

The first slice (`idx[:, -context_size:]`) solves "the input is too long for the model." The second slice (`logits[:, -1, :]`) solves "the model gives me more predictions than I need — I only want the one for the very last token I gave it."

**Step 2 — top-k filtering (only if `top_k` is set).**

With `top_k=3` on `logits = [1.2, 3.5, 0.8, 4.1, 2.0]`:

```
torch.topk(logits, 3)  → top_logits = [4.1, 3.5, 2.0]   ← 3 largest values, sorted descending

min_val = top_logits[:, -1] = 2.0    ← the smallest value among the top 3

torch.where(logits < min_val, -inf, logits):
  1.2 < 2.0  → -inf      ← token 0 eliminated
  3.5 < 2.0  → False     → stays 3.5
  0.8 < 2.0  → -inf      ← token 2 eliminated
  4.1 < 2.0  → False     → stays 4.1
  2.0 < 2.0  → False     → stays 2.0   (equal, not less than, so kept)

logits after filtering = [-inf, 3.5, -inf, 4.1, 2.0]
```

Three candidates survive: tokens 1, 3, and 4. The other two are mathematically impossible to sample, because `softmax(-inf) = 0` exactly.

**Step 3 — temperature, then softmax, then sample (or argmax if `temperature=0.0`).**

With `temperature=0.8` applied to `[-inf, 3.5, -inf, 4.1, 2.0]`:

```
logits / temperature:
  -inf / 0.8 = -inf
   3.5 / 0.8 = 4.375
  -inf / 0.8 = -inf
   4.1 / 0.8 = 5.125
   2.0 / 0.8 = 2.5

scaled logits = [-inf, 4.375, -inf, 5.125, 2.5]
```

Then the stability subtraction (explained below), then softmax converts these into a probability distribution that sums to 1 across the three surviving tokens, with `-inf` entries becoming exactly `0`. `torch.multinomial(probs, num_samples=1)` then draws one token randomly, weighted by these probabilities — token 3 is most likely to be drawn since it has the highest probability, but tokens 1 and 4 still have a real chance.

If instead `temperature=0.0`, the `else` branch fires: plain `torch.argmax`, which always picks token 3 (the highest logit) with no randomness at all. This is identical to Chapter 4's `generate_text_simple` behaviour.

**The MPS/numerical stability fix.**

```python
logits = logits - logits.max(dim=-1, keepdim=True).values
```

This is the log-sum-exp trick from Section 8, applied here for the same reason. After dividing by a small temperature, logits can become very large — `5.125` divided by a temperature of `0.1` instead of `0.8` would give `51.25`, and $e^{51.25}$ is large enough to risk overflow on some backends, especially Apple's MPS. Subtracting the row-wise maximum before exponentiating shifts every value down so the largest becomes exactly `0`:

```
scaled logits        = [-inf, 4.375, -inf, 5.125, 2.5]
row max               = 5.125
after subtraction     = [-inf, -0.75, -inf, 0.0, -2.625]
```

Softmax of this shifted version is mathematically identical to softmax of the original — subtracting a constant from every entry in a row does not change the resulting probabilities, because the constant cancels out in the numerator and denominator of softmax. The only thing that changes is numerical safety: `e^0 = 1` instead of `e^5.125 ≈ 168`, keeping every intermediate value small and well within float32's safe range.

**Step 4 — early stopping on `eos_id`.**

```python
if idx_next == eos_id:
    break
```

If `eos_id=50256` (GPT-2's `<|endoftext|>` token) is passed and the sampled `idx_next` equals it, generation stops immediately rather than continuing to `max_new_tokens`. This matters for tasks with a natural stopping point — like answering a question — where padding the output with extra tokens past the natural end would be wasteful or incoherent.

**Step 5 — append and repeat.**

```python
idx = torch.cat((idx, idx_next), dim=1)
```

`idx_next` has shape `(1, 1)`. Concatenating along `dim=1` (the sequence dimension) grows `idx` by one token, exactly as `generate_text_simple` did in Chapter 4. The loop then repeats with the newly extended `idx`.

**Calling the full function.**

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

`torch.manual_seed(123)` is necessary here because `torch.multinomial` is stochastic — without seeding, every run would produce a different output even with identical inputs. With `top_k=25` and `temperature=1.4` (mild flattening, moderate randomness), the output has noticeably more variety than greedy decoding while still being constrained to plausible high-probability tokens. On the small overfit model trained earlier in the chapter, the output remains nonsensical in meaning — it only ever saw one short story — but the generation mechanics themselves are now identical to what production LLM serving systems use.

**Gotchas.**

`temperature=0.0` is the trigger for the deterministic `else` branch, not `temperature=1.0`. A temperature of exactly `1.0` still goes through the sampling branch — it is the natural, unscaled softmax distribution sampled randomly, not equivalent to argmax.

The `top_k` filtering happens before temperature scaling, not after. If you applied temperature first and top-k second, you would compute softmax probabilities on the full vocabulary at the wrong scale before restricting the field — the order in this function (filter the candidate pool first, then reshape the competition among survivors) is the only correct sequence.

`idx_next == eos_id` compares a `(1, 1)` tensor to a Python int. PyTorch broadcasts this correctly into an element-wise boolean tensor, and the `if` statement implicitly calls `.item()` on a single-element tensor — but this only works because `idx_next` has exactly one element. If `generate` were ever modified to support `batch_size > 1`, this comparison would need to change to check each sequence in the batch independently.

## 23 — Section 5.4: Saving and Loading the Model `state_dict`

```python
torch.save(model.state_dict(), "model.pth")
```

**Summary.** `model.state_dict()` returns every learnable tensor in the model — every weight matrix, bias, scale, and shift — bundled into a single Python dictionary keyed by parameter name. `torch.save` serialises that dictionary to disk. This is the standard, recommended way to persist a trained model in PyTorch, as opposed to pickling the entire model object.

**The problem it solves.** Training takes time and compute. Once a model is trained, its weights need to survive past the Python process that trained them — to be reloaded later for inference, to resume training, or to be shared with someone else. `state_dict` is the portable container for exactly that: the learned numbers, with no dependency on how the training script was written.

**The intuition.** Think of `GPTModel` as a blueprint (the class definition — empty drawers and labels, no actual values) and `state_dict()` as the contents of every drawer (the actual numbers). Saving `state_dict` saves only the contents, not the blueprint. To use it again later you need the same blueprint (the class code) available, then you pour the saved contents back into a freshly built set of drawers.

**What's actually inside `state_dict` — a concrete look.**

```python
sd = model.state_dict()
print(list(sd.keys())[:4])
print(sd["tok_emb.weight"].shape)
print(sd["trf_blocks.0.att.W_query.weight"].shape)
```

```
['tok_emb.weight', 'pos_emb.weight',
 'trf_blocks.0.att.W_query.weight', 'trf_blocks.0.att.mask']

tok_emb.weight.shape                       = (50257, 768)   ← vocab_size, emb_dim
trf_blocks.0.att.W_query.weight.shape      = (768, 768)     ← d_in, d_out, block 0's query projection
```

Every key is a dotted path mirroring the module hierarchy you defined in `__init__`: `trf_blocks.0.att.W_query.weight` means "inside `self.trf_blocks`, block index 0, inside `self.att`, the `W_query` linear layer's weight matrix." This is exactly why the class definition still matters even though it isn't saved — the dictionary keys only make sense relative to a model built with that exact structure.

`state_dict` contains two kinds of entries. Every `nn.Parameter` — weights, biases, LayerNorm's scale and shift — is included because these are what the optimiser updates during training. It also includes every registered buffer, such as the causal attention mask (`trf_blocks.0.att.mask`) — buffers are tensors that move with the model (e.g. `.to(device)`) and get saved/loaded with it, but are not trained by the optimiser since they hold fixed values like the mask, not learned ones.

`state_dict` deliberately excludes the model's Python code (the `GPTModel` class definition itself — you must have that available separately to reconstruct the blueprint), anything about the optimiser's internal state (covered separately in Section 24), and any training metadata like the loss curve or epoch count.

**Why `state_dict` instead of `torch.save(model)` directly.**

`torch.save(model)` pickles the entire Python object, including a reference to the class itself. This creates a brittle dependency: if you ever rename the `GPTModel` class, move it to a different file, or even just change the Python/PyTorch version between saving and loading, unpickling can fail outright. `state_dict` sidesteps this entirely — it is just tensors and string keys, nothing executable, nothing tied to a specific class location. As long as you can instantiate a `GPTModel` with matching architecture, the saved weights will load into it regardless of how the surrounding code has changed.

**Loading it back — step by step.**

```python
model = GPTModel(GPT_CONFIG_124M)   # fresh model, random weights — the empty blueprint

if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

model.load_state_dict(torch.load("model.pth", map_location=device, weights_only=True))
model.eval()
```

```
GPTModel(GPT_CONFIG_124M)
       ↓  fresh instance — all weights random, same architecture as the saved one
       ↓  torch.load("model.pth", ...)
state_dict   ← the saved dictionary of tensors, loaded into memory
       ↓  model.load_state_dict(state_dict)
       ↓  every tensor in state_dict overwrites the matching-named tensor in model
model        ← now has the trained weights instead of random initialisation
```

A fresh `GPTModel` instance must be created first, built with the identical config (`GPT_CONFIG_124M`) used during training. The `state_dict` itself carries no information about layer sizes, depth, or vocabulary size — it is purely a flat dictionary of tensors. If you instantiate the model with a different config (say, a different number of layers), `load_state_dict` will raise a key mismatch or shape mismatch error rather than silently loading wrong-shaped weights.

`map_location=device` controls which device the loaded tensors are placed on. Without it, PyTorch defaults to recreating tensors on whatever device they were saved from — a `.pth` file saved from a CUDA-equipped machine would attempt to allocate CUDA tensors when loaded on a CPU-only machine, and fail immediately with a device error. `map_location` redirects every tensor to the target device during the load itself, regardless of where it was originally saved.

`weights_only=True` is a security flag. By default (`False` in PyTorch versions before 2.6), `torch.load` uses Python's `pickle` module, which can execute arbitrary code embedded in the file during deserialisation. A malicious `.pth` file could exploit this to run attacker-controlled code the moment you call `torch.load`. `weights_only=True` restricts deserialisation to only tensors and basic Python types (lists, dicts, numbers), which is all a legitimate `state_dict` should ever contain. There is essentially no legitimate reason to disable this for loading model weights.

**File size — what to expect.**

```
124M parameters × 4 bytes/parameter (float32)
= 496,000,000 bytes
≈ 473 MB
```

This matches the parameter count established in Chapter 4's parameter-counting section. The saved `.pth` file size scales linearly with parameter count and precision — switching to float16 storage would roughly halve it.

**Gotchas.**

`model.eval()` after loading is easy to forget and produces subtly wrong results rather than an error. If the model still has dropout active (the default `model.train()` mode), inference outputs become non-deterministic and degraded — running the same input twice gives different results, and generated text quality drops because random units are still being zeroed out.

Calling `load_state_dict` on a model whose architecture doesn't exactly match the saved one (different number of layers, different embedding dimension, a renamed module) raises a `RuntimeError` listing every missing or unexpected key. This is usually the correct failure mode — but if you intentionally want to load a partial state dict (e.g. transferring only the embedding layer into a differently-sized model), you need `model.load_state_dict(state_dict, strict=False)`, which silently skips non-matching keys instead of raising.

`torch.load(..., map_location=device)` loads tensors onto `device`, but the freshly instantiated `model = GPTModel(GPT_CONFIG_124M)` is created on CPU by default before the weights are loaded into it. After `load_state_dict`, the model's parameters take on the device of the loaded tensors — but it is safer and more explicit to also call `model.to(device)` after loading, especially if any submodules construct new tensors at runtime that wouldn't automatically follow the loaded weights' device.

## 24 — Section 5.4: Checkpointing the Optimizer Too

```python
torch.save({
    "model_state_dict":     model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
}, "model_and_optimizer.pth")
```

**Summary.** A single `.pth` file holding two state dictionaries bundled into one Python dict: the model's weights and the optimiser's internal state. This is the checkpoint format needed to truly resume training later, as opposed to Section 23's model-only save, which is sufficient only for inference.

**The problem it solves.** Section 23 saves the model's weights, which is enough to generate text or continue using the model for inference. But it is not enough to resume _training_ without a quality hit. AdamW does not just look at the current gradient — it maintains running statistics across every previous step, and those statistics are lost if you only save the weights.

**The intuition.** Think of training as walking down a hill with momentum — you're not just reacting to the slope directly under your feet right now, you're also carrying speed and direction built up from your last several steps. The model weights are your current position on the hill. The optimiser state is your current speed and direction. Saving only the weights and resuming training is like teleporting to the same spot on the hill but with zero momentum — you have to build that momentum back up from scratch before you're moving efficiently again.

**What AdamW actually tracks per parameter.**

For every single trainable parameter, AdamW maintains two running buffers:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1)\, g_t \qquad \text{(first moment — momentum, an exponential moving average of past gradients)}$$

$$v_t = \beta_2 v_{t-1} + (1-\beta_2)\, g_t^2 \qquad \text{(second moment — adapts the step size per parameter, an exponential moving average of squared past gradients)}$$

where $g_t$ is the gradient at step $t$. These are not derived from the current weights — they are a running history accumulated across every batch seen so far. If you reload only the weights and start a fresh `AdamW` optimiser, both $m$ and $v$ reset to zero, and it takes many steps of training before they re-stabilise into useful estimates again. During that re-stabilisation window, the updates are noisier and less effective — research and practice both show this shows up as a small but real spike or stall in the loss curve immediately after a naive resume.

**Dry run — what gets stored, sizes included.**

```
124M parameters in the model

model_state_dict        ≈ 124M params × 4 bytes (float32) ≈ 473 MB

optimizer_state_dict:
  exp_avg   (m, first moment)   ≈ 124M params × 4 bytes  ≈ 473 MB
  exp_avg_sq (v, second moment) ≈ 124M params × 4 bytes  ≈ 473 MB
                                                            ─────────
                                  optimizer total         ≈ 946 MB

model_and_optimizer.pth total    ≈ 473 MB + 946 MB ≈ 1.4 GB
```

The optimiser state alone is roughly double the model size, because it stores two full-sized buffers ($m$ and $v$) per parameter, on top of the parameter itself. This is why full training checkpoints for large models are often 3× the size of an inference-only weights file.

**Loading both back — step by step.**

```python
checkpoint = torch.load("model_and_optimizer.pth", weights_only=True)

model = GPTModel(GPT_CONFIG_124M)
model.load_state_dict(checkpoint["model_state_dict"])

optimizer = torch.optim.AdamW(model.parameters(), lr=0.0005, weight_decay=0.1)
optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
model.train()
```

```
torch.load("model_and_optimizer.pth")
       ↓
checkpoint = {"model_state_dict": {...}, "optimizer_state_dict": {...}}
       ↓
GPTModel(GPT_CONFIG_124M)              ← fresh model, random weights
       ↓  model.load_state_dict(checkpoint["model_state_dict"])
model now has the trained weights

torch.optim.AdamW(model.parameters(), ...)   ← fresh optimiser, zero momentum buffers
       ↓  optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
optimizer now has the saved m and v buffers, matched back to model's parameters
       ↓
model.train()                          ← ready to resume exactly where training left off
```

The optimiser must still be freshly instantiated with `torch.optim.AdamW(model.parameters(), ...)` before loading its state — `load_state_dict` does not construct the optimiser object itself, only populates an already-constructed one's internal buffers. This also means `optimizer.parameters()` at construction time must point to the same `model` whose weights were just loaded, so the optimiser's saved per-parameter buffers correctly match up with the actual parameter tensors by identity, not just by name.

**What's missing for full resumability — and why it usually doesn't matter here.**

A complete training resume that reproduces the exact same training run bit-for-bit would also need the learning rate scheduler's state (`scheduler.state_dict()`, if one is used — it tracks where in the schedule, e.g. warmup or decay, training currently is), the random number generator state (`torch.get_rng_state()` and `torch.cuda.get_rng_state_all()`, which determine the exact shuffle order of the DataLoader and the exact dropout mask pattern on each forward pass), and the loop counters (`epoch` and `global_step`, so the resumed loop knows where to pick up rather than restarting epoch numbering from zero).

For the simple notebook in this chapter, saving just the model and optimiser state is the practical minimum — training continues effectively even without RNG and scheduler state, just not bit-for-bit identically to an uninterrupted run.

### Extra Notes

Let me build it from scratch with tiny numbers so it's concrete.

**The problem AdamW is solving.**

Plain gradient descent updates each weight like this:

```
w = w - learning_rate × gradient
```

The problem is the raw gradient is noisy — it jumps around wildly from batch to batch because each batch is a random sample of the data. You end up zigzagging toward the minimum rather than moving smoothly.

Adam fixes this by never using the raw gradient directly. Instead it maintains two running averages that it updates every step.

**First moment $m$ — smoothed gradient (momentum).**

Instead of using the raw gradient from this one batch, keep a running average of all past gradients:

```
Step 1:  gradient = 0.8
         m = 0.9 × 0    + 0.1 × 0.8  = 0.08      ← mostly zero (cold start), small pull from 0.8

Step 2:  gradient = 0.6
         m = 0.9 × 0.08 + 0.1 × 0.6  = 0.072 + 0.06 = 0.132

Step 3:  gradient = 0.9
         m = 0.9 × 0.132 + 0.1 × 0.9 = 0.119 + 0.09 = 0.209

Step 4:  gradient = 0.4
         m = 0.9 × 0.209 + 0.1 × 0.4 = 0.188 + 0.04 = 0.228
```

The `0.9` (called $\beta_1$) is the "memory" — how much weight to give past history. The `0.1` is `(1 - 0.9)` — how much weight to give the new gradient. So $m$ is a slow-moving average that dampens the noisy jumps in the raw gradient. If the gradient consistently points in one direction, $m$ builds up and the weight moves faster (like a ball rolling downhill gaining speed). If the gradient flips direction every step, $m$ stays near zero and barely moves.

**Second moment $v$ — smoothed squared gradient (adaptive step size).**

```
Step 1:  gradient = 0.8,   gradient² = 0.64
         v = 0.999 × 0      + 0.001 × 0.64  = 0.00064

Step 2:  gradient = 0.6,   gradient² = 0.36
         v = 0.999 × 0.00064 + 0.001 × 0.36 = 0.00064 + 0.00036 = 0.001

Step 3:  gradient = 0.9,   gradient² = 0.81
         v = 0.999 × 0.001  + 0.001 × 0.81  = 0.000999 + 0.00081 = 0.00181
```

$v$ tracks how large the gradients have been historically for this specific parameter. The actual weight update divides by $\sqrt{v}$:

```
update = learning_rate × m / sqrt(v)
```

If a parameter has been getting consistently large gradients (large $v$), the update is scaled down — it doesn't need big nudges because it's already in an active region. If a parameter has been getting tiny gradients (small $v$), the update is scaled up — it needs bigger nudges to move at all. This is the "adaptive" part of Adam: every single parameter gets its own personalised step size.

**Now you can see what happens if you lose the optimiser state.**

Say you trained for 10,000 steps and your $m$ and $v$ for one particular weight look like:

```
m = 0.023    ← the gradient has been consistently pointing slightly positive
v = 0.0041   ← gradients have been small and stable for this weight
```

The update Adam would compute: `lr × 0.023 / sqrt(0.0041) = lr × 0.359`

Now you save only the weights and reload. Fresh AdamW starts with:

```
m = 0.0     ← no history
v = 0.0     ← no history
```

First update after reload: `lr × raw_gradient / sqrt(near_zero)` — dividing by something near zero produces a huge, destabilising update. For the first ~100 steps Adam is essentially thrashing until $m$ and $v$ build back up to meaningful values. That's the loss spike you see after a naive resume — it's not that the weights got worse, it's that the optimiser is temporarily blind to the scale of gradients it should be working with.

Saving `optimizer.state_dict()` preserves the exact $m$ and $v$ for every one of the 124M parameters, so when you reload, Adam picks up from step 10,001 as if training was never interrupted.

**Gotchas.**

The order of operations matters: `model.load_state_dict` must happen before `torch.optim.AdamW(model.parameters(), ...)` is constructed, or more precisely, the optimiser must be built on the same parameter tensors that will hold the loaded weights. Calling `optim.AdamW(model.parameters())` _before_ `load_state_dict` is actually fine too, since `load_state_dict` modifies the existing tensors in place rather than replacing them — but constructing the optimiser on a _different_ model instance than the one weights were loaded into will silently produce an optimiser whose buffers don't correspond to the model actually being trained.

`weights_only=True` on a checkpoint that bundles both model and optimiser state still works correctly, because both dictionaries contain only tensors and basic Python types (the AdamW state dict includes plain Python floats and ints for step counts, alongside the tensor buffers) — nothing in a standard checkpoint requires unsafe deserialisation.

If you change the learning rate or `weight_decay` when reconstructing the optimiser before loading (e.g. `lr=0.0005` here versus a different value used originally), the loaded `m` and `v` buffers are still valid, but the optimiser will immediately start applying updates at the new learning rate from the next step onward — this is sometimes intentional (e.g. resuming with a lower LR for fine-tuning) but easy to do by accident if you don't match the original training configuration.

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
