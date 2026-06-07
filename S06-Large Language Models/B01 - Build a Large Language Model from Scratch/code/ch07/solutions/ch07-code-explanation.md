# Chapter 7 Code Explanation — Finetuning To Follow Instructions

This document walks through every code cell of `ch07.ipynb` from Sebastian Raschka's *Build a Large Language Model From Scratch*. Chapter 7 is the final transformation: you take the pretrained GPT-2 you built in chapters 1–6 and teach it to **follow instructions** — turning a raw text-completion engine into something that behaves like ChatGPT or Claude.

The five things you'll do in this chapter:

1. Load 1,100 instruction-response pairs ("Rewrite this sentence using a simile", "Identify the verb in the following sentence", etc.).
2. Wrap them in the **Alpaca prompt format** and build a `DataLoader` with custom batching and target masking.
3. Load the 355M pretrained GPT-2 Medium (we step up from the 124M model used in chapter 5).
4. Fine-tune for 2 epochs using your `train_model_simple` from chapter 5.
5. **Evaluate** the finetuned model using a *second* LLM (Llama 3 via Ollama) as a judge.

By the end of the chapter you have an instruction-tuned model that scores around 50/100 on the Llama-3 judge — proof that the SFT-on-Alpaca pipeline works on a small dataset.

Section numbers (0 → 27) match the linear flow of the notebook. Each section header also names the Raschka book subsection (7.1, 7.2, ...) for cross-lookup with the notes.

---

## Table of Contents

- [0 — Notebook Setup and Imports](#0--notebook-setup-and-imports)
- [1 — Section 7.1: What "Instruction Finetuning" Means](#1--section-71-what-instruction-finetuning-means)
- [2 — Section 7.2: Downloading and Loading the Instruction Dataset](#2--section-72-downloading-and-loading-the-instruction-dataset)
- [3 — Section 7.2: Inspecting Dataset Entries](#3--section-72-inspecting-dataset-entries)
- [4 — Section 7.2: The Alpaca Prompt Format — format_input](#4--section-72-the-alpaca-prompt-format--format_input)
- [5 — Section 7.2: Train / Validation / Test Split](#5--section-72-train--validation--test-split)
- [6 — Section 7.3: The InstructionDataset Class](#6--section-73-the-instructiondataset-class)
- [7 — Section 7.3: Custom Collate Draft 1 — Padding Only](#7--section-73-custom-collate-draft-1--padding-only)
- [8 — Section 7.3: Custom Collate Draft 2 — Targets Shifted by One](#8--section-73-custom-collate-draft-2--targets-shifted-by-one)
- [9 — Section 7.3: Custom Collate Final — Masking Padding With -100](#9--section-73-custom-collate-final--masking-padding-with--100)
- [10 — Section 7.3: Why -100? cross_entropy's ignore_index](#10--section-73-why--100-cross_entropys-ignore_index)
- [11 — Section 7.4: Device Selection and functools.partial](#11--section-74-device-selection-and-functoolspartial)
- [12 — Section 7.4: Creating the DataLoaders](#12--section-74-creating-the-dataloaders)
- [13 — Section 7.4: Inspecting Batch Shapes](#13--section-74-inspecting-batch-shapes)
- [14 — Section 7.5: Loading the 355M GPT-2 Medium](#14--section-75-loading-the-355m-gpt-2-medium)
- [15 — Section 7.5: Generation Before Finetuning](#15--section-75-generation-before-finetuning)
- [16 — Section 7.6: Initial Loss Before Training](#16--section-76-initial-loss-before-training)
- [17 — Section 7.6: The 2-Epoch Training Run](#17--section-76-the-2-epoch-training-run)
- [18 — Section 7.6: Plotting the Loss Curve](#18--section-76-plotting-the-loss-curve)
- [19 — Section 7.7: Generating Responses for the Test Set](#19--section-77-generating-responses-for-the-test-set)
- [20 — Section 7.7: Saving the Finetuned Model](#20--section-77-saving-the-finetuned-model)
- [21 — Section 7.8: Why You Need an LLM Judge](#21--section-78-why-you-need-an-llm-judge)
- [22 — Section 7.8: Setting Up Ollama](#22--section-78-setting-up-ollama)
- [23 — Section 7.8: The check_if_running Utility](#23--section-78-the-check_if_running-utility)
- [24 — Section 7.8: The query_model Function](#24--section-78-the-query_model-function)
- [25 — Section 7.8: One-Response Evaluation Walkthrough](#25--section-78-one-response-evaluation-walkthrough)
- [26 — Section 7.8: generate_model_scores — Scoring the Whole Test Set](#26--section-78-generate_model_scores--scoring-the-whole-test-set)
- [27 — Section 7.9: Conclusions and What Comes Next](#27--section-79-conclusions-and-what-comes-next)

---

## 0 — Notebook Setup and Imports

```python
from importlib.metadata import version

pkgs = [
    "numpy",        # PyTorch dependency
    "matplotlib",   # plotting the loss curve
    "tiktoken",     # GPT-2 BPE tokenizer
    "torch",        # the engine
    "tqdm",         # progress bar for the test-set generation
    "tensorflow",   # used by gpt_download.py to read OpenAI's checkpoint
    "psutil",       # used to check if Ollama is running
]
```

Compared to chapter 5 there are two extra dependencies:

* **`tqdm`** — wraps the test-set loop with a progress bar. Generating 110 responses takes a few minutes; the bar tells you how much time is left.
* **`psutil`** — used by `check_if_running("ollama")` in section 7.8 to verify that the Ollama judge service is alive before we try to call it.

The other novelty: **no installation of anything heavy in this chapter**. By now you have all the tooling from chapters 5 and 6 — chapter 7 is mostly about how to *use* it for a new objective (instruction-following) rather than building new tooling.

---

## 1 — Section 7.1: What "Instruction Finetuning" Means

### Three regimes of LLM training

Your model has now been through (or is about to go through) three increasingly specialised training regimes:

| Stage | Data | Loss | What it produces |
|-------|------|------|-------------------|
| **Pretraining** (ch5) | Raw text | Next-token prediction | A text-completion engine |
| **Instruction finetuning** (ch7, this chapter) | (instruction, response) pairs | Next-token prediction on the response | A model that follows instructions |
| **Preference alignment** (DPO etc.) | (instruction, chosen, rejected) triplets | DPO loss (not covered in this book) | A model whose responses humans prefer |

The first two stages share an identical loss function — **next-token prediction**. What changes is the **shape of the training data**:

* Pretraining sees `"The capital of France is Paris."` → learn to predict each word from the previous ones.
* SFT sees `"### Instruction: What is the capital of France? ### Response: Paris."` → learn to predict the response given the instruction context.

The model learns the *pattern*: "after this instruction-shaped prefix, produce a helpful response." That's instruction-following in a sentence.

### Why pretraining alone isn't enough

A raw pretrained GPT-2 given the prompt `"What is the capital of France?"` is just as likely to continue with another question (`"What is the capital of Spain?"`) as with the answer. The internet has both patterns. Without SFT it has no preference between them.

SFT changes that. After training on 1,000 instruction-response pairs, the model has overwhelmingly seen `### Response:` followed by a sensible answer to whatever appeared in `### Instruction:`. It now strongly prefers that pattern.

### The book's choice: 1,100 examples, 2 epochs, GPT-2 Medium

| Choice | Why |
|--------|-----|
| **1,100 examples** | Big enough to learn the format. Small enough to train in 5–10 minutes on a single GPU. |
| **2 epochs** | Past 2 epochs the model starts memorising specific responses (overfitting). |
| **GPT-2 Medium (355M)** | Bigger than chapter 5's 124M (which is too small for nuanced instruction-following), but still fits comfortably in 8 GB VRAM. |

Real production SFT uses tens of thousands of examples, 3–5 epochs, and models of 7B+. The principles are identical; the scale is bigger.

---

## 2 — Section 7.2: Downloading and Loading the Instruction Dataset

```python
import json, os, requests

def download_and_load_file(file_path, url):
    if not os.path.exists(file_path):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        text_data = response.text
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text_data)
    else:
        with open(file_path, "r", encoding="utf-8") as file:
            text_data = file.read()
    return json.loads(text_data)

file_path = "instruction-data.json"
url = ("https://raw.githubusercontent.com/rasbt/LLMs-from-scratch/main/"
       "ch07/01_main-chapter-code/instruction-data.json")

data = download_and_load_file(file_path, url)
print("Number of entries:", len(data))
```

### The download-or-load pattern

This is the same defensive pattern from chapter 5 section 10: download once, cache to disk, reuse on every subsequent run. Three reasons:

1. **Re-running cells doesn't waste bandwidth.** The first run downloads; every later run reads the local file.
2. **Works offline.** Once you've downloaded the file, the notebook runs without internet.
3. **Reproducible.** If GitHub ever rate-limits or the URL changes, your local copy is the source of truth.

### Why `response.raise_for_status()`?

Without it, a failed download (404, 503, etc.) returns an HTML error page that gets written to disk as if it were valid JSON. The next `json.loads()` then crashes with a confusing parser error. Calling `raise_for_status()` makes failures loud and immediate.

### Why `timeout=30`?

A `requests.get` without a timeout can hang **forever** if the server stops responding mid-transfer. 30 seconds is enough for a 200 KB JSON file on any reasonable connection.

### What the dataset contains

The file is a list of 1,100 dicts. Each dict has three keys:

* **`instruction`** — the task description ("Rewrite this sentence using a simile")
* **`input`** — optional context ("The dog runs fast"); can be empty
* **`output`** — the desired response ("The dog runs like the wind")

This format is essentially the **Alpaca dataset** convention from Stanford's 2023 Alpaca paper, which became the de facto standard for SFT data.

---

## 3 — Section 7.2: Inspecting Dataset Entries

```python
print("Example entry:\n", data[50])
print("Another example entry:\n", data[999])
```

Two entries are shown — one with an `input` field, one without. The reason: ~40% of Alpaca-style entries are "instruction-only" (no extra context), and ~60% are "instruction + input" pairs. Our code in section 4 has to handle both cases cleanly.

### What's actually in those entries

Entry 50 (with input):

```json
{
    "instruction": "Identify the correct spelling of the following word.",
    "input": "Ocassion",
    "output": "The correct spelling is 'Occasion.'"
}
```

Entry 999 (no input):

```json
{
    "instruction": "What is an antonym of 'complicated'?",
    "input": "",
    "output": "An antonym of 'complicated' is 'simple'."
}
```

The model has to learn that:
* If `input` is non-empty, use it.
* If `input` is empty, just answer the instruction directly.

### Why this dataset is intentionally simple

These tasks (spelling correction, antonym finding, simile generation) are short and unambiguous. There is **one** clearly correct response per entry. This makes evaluation easier — the Llama-3 judge in section 7.8 can reliably score the model's responses without ambiguity.

Real instruction datasets (like Open Assistant or UltraChat) contain longer multi-turn conversations with no single "correct" answer. They are harder to learn from, harder to evaluate, and require larger models.

---

## 4 — Section 7.2: The Alpaca Prompt Format — format_input

```python
def format_input(entry):
    instruction_text = (
        f"Below is an instruction that describes a task. "
        f"Write a response that appropriately completes the request."
        f"\n\n### Instruction:\n{entry['instruction']}"
    )
    input_text = f"\n\n### Input:\n{entry['input']}" if entry["input"] else ""
    return instruction_text + input_text
```

### The Alpaca prompt template

This wraps the (instruction, input) pair into a structured string with explicit section delimiters:

```
Below is an instruction that describes a task. Write a response that appropriately
completes the request.

### Instruction:
<the instruction text>

### Input:                       <-- only if input is non-empty
<the input text>
```

The model learns to recognise `### Instruction:` and `### Input:` as **role markers** — exactly like the `<|user|>` and `<|assistant|>` tokens in chapter 6, but built out of plain ASCII characters that any GPT-2 tokenizer can handle.

### Why explicit section headers?

Without them, the model has to *infer* where the instruction ends and the response should start. With them, the contract is clear: "after `### Response:`, produce the answer to whatever came before."

The book then appends `### Response:\n<output>` during training (see cell 20). The model sees the full sequence:

```
Below is an instruction... ### Instruction: Rewrite this sentence... ### Input: The dog runs fast ### Response: The dog runs like the wind.
```

…and learns to continue from `### Response:` with the correct text.

### The conditional input field

```python
input_text = f"\n\n### Input:\n{entry['input']}" if entry["input"] else ""
```

When `input` is empty, the `### Input:` header is **omitted entirely** — not left blank. If we'd left an empty `### Input:` header, the model would learn that "sometimes there's an empty input section" — which is noise. Omitting it cleanly means the model only sees the `### Input:` header when it's actually informative.

### Why this format and not OpenAI's chat template?

GPT-2 was trained before chat templates existed. Its tokenizer has no `<|user|>` or `<|assistant|>` special tokens. So we use plain ASCII section headers that the BPE tokenizer encodes as ordinary sub-word tokens. This works perfectly well — the model just learns to associate the `### Response:` pattern with "answer goes here."

For modern models (Llama-3, Phi-3, etc.) you would use the official chat template instead. The Alpaca format is a relic of the early-2023 instruction-tuning era but it's still the cleanest way to demonstrate the technique on GPT-2.

---

## 5 — Section 7.2: Train / Validation / Test Split

```python
train_portion = int(len(data) * 0.85)   # 85% — 935 examples
test_portion  = int(len(data) * 0.1)    # 10% — 110 examples
val_portion   = len(data) - train_portion - test_portion   # 5% — 55 examples

train_data = data[:train_portion]
test_data  = data[train_portion : train_portion + test_portion]
val_data   = data[train_portion + test_portion:]
```

### Why 85 / 10 / 5?

A common research split is 80/10/10, but this notebook uses 85/5/10 (train/val/test) — biasing slightly toward more training data.

* **Train (85% = 935)**: what the model sees during gradient steps.
* **Val (5% = 55)**: tracked during training to detect overfitting. Used to stop training if val loss starts rising.
* **Test (10% = 110)**: held out completely until after training. Used in section 7.7 to generate responses that the judge will score in section 7.8.

### Why the test set is bigger than the val set

The val set just needs to give a stable loss estimate during training — 55 examples is enough.

The test set, on the other hand, is being judged one example at a time by Llama 3 in section 7.8. With 110 examples, you get a better-sampled aggregate score. The Llama judge is noisy (it might score the same response 70 one time and 75 another); averaging over more samples reduces this noise.

### No shuffling? Should there be?

The data was already shuffled before being saved to JSON, so a simple slice (`data[:885]`, etc.) gives an effectively random split. Calling `random.shuffle(data)` here would also work but isn't necessary.

In general, if you don't know whether your dataset is pre-shuffled, **always shuffle before splitting**. Otherwise you might accidentally have all the simple tasks in train and all the hard tasks in test, which would make your model look great in training and terrible in evaluation.

---

## 6 — Section 7.3: The InstructionDataset Class

```python
import torch
from torch.utils.data import Dataset


class InstructionDataset(Dataset):
    def __init__(self, data, tokenizer):
        self.data = data
        self.encoded_texts = []
        for entry in data:
            instruction_plus_input = format_input(entry)
            response_text = f"\n\n### Response:\n{entry['output']}"
            full_text = instruction_plus_input + response_text
            self.encoded_texts.append(tokenizer.encode(full_text))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.encoded_texts[index]
```

### Pre-tokenisation in __init__

Notice that `__init__` does **all the tokenisation up-front**. Every entry's full text (`instruction + input + response`) is encoded into a list of token IDs at construction time and stashed in `self.encoded_texts`.

Why eagerly? Two reasons:

1. **Tokenisation is slow.** Running `tokenizer.encode(text)` is maybe 100x slower than indexing a list. Pre-tokenising means the DataLoader (which calls `__getitem__` once per sample per epoch) hits a cheap list lookup, not a tokeniser call.
2. **The dataset fits in memory.** 1,100 entries × maybe 100 tokens each × 4 bytes per int = 440 KB. Trivial. For larger datasets that don't fit, you'd implement lazy tokenisation in `__getitem__`.

### Why concatenate instruction + response into one string

The training task is **next-token prediction over the full sequence**. The model sees every position — both the instruction part and the response part. We will mask the *target* on instruction positions later (this is one optional advanced technique mentioned in cell 54); for now, the model is asked to predict every token, including those in the instruction.

If you only wanted to "train on the response," you'd:
1. Tokenise the instruction part separately and remember its length.
2. In the collate function, set targets to `-100` for all instruction positions.

The book leaves this as a discussed extension because it makes the code more complex without dramatically changing the results for this small dataset.

### What `__getitem__` returns

A **Python list of ints**, not a tensor. Why? Because each entry has a **different length** — entry 50 might be 64 tokens, entry 999 might be 32 tokens. Tensors must be rectangular, so we can't pre-stack them. The padding-to-rectangular happens later in the collate function (next sections).

The DataLoader will call `__getitem__(i)` for each `i` in the batch, gather the resulting lists, and pass the list-of-lists to our custom `collate_fn` which handles the padding.

---

## 7 — Section 7.3: Custom Collate Draft 1 — Padding Only

```python
def custom_collate_draft_1(batch, pad_token_id=50256, device="cpu"):
    batch_max_length = max(len(item) + 1 for item in batch)
    inputs_lst = []

    for item in batch:
        new_item = item + [pad_token_id]        # add one EOS token
        padded = new_item + [pad_token_id] * (batch_max_length - len(new_item))
        inputs = torch.tensor(padded[:-1])      # drop last pad to get desired length
        inputs_lst.append(inputs)

    inputs_tensor = torch.stack(inputs_lst).to(device)
    return inputs_tensor


# Quick test:
inputs_1 = [0, 1, 2, 3, 4]      # length 5
inputs_2 = [5, 6]                # length 2
inputs_3 = [7, 8, 9]             # length 3
batch = (inputs_1, inputs_2, inputs_3)
print(custom_collate_draft_1(batch))
```

Expected output:

```
tensor([[    0,     1,     2,     3,     4],
        [    5,     6, 50256, 50256, 50256],
        [    7,     8,     9, 50256, 50256]])
```

### What this draft does

Three sequences of different lengths get padded to the same length so they can be stacked into a single rectangular tensor.

* `inputs_1` (length 5): unchanged.
* `inputs_2` (length 2): padded with three `50256` tokens at the right.
* `inputs_3` (length 3): padded with two `50256` tokens.

Final shape: `(batch_size=3, max_len=5)`.

### Why `+1` and then `[:-1]`?

Look carefully at the logic:

```python
batch_max_length = max(len(item) + 1 for item in batch)   # +1
...
new_item = item + [pad_token_id]                          # append one pad
padded = new_item + [pad_token_id] * (batch_max_length - len(new_item))
inputs = torch.tensor(padded[:-1])                        # drop last
```

This roundabout dance does one thing: it guarantees that **every sequence ends with at least one pad token** (which we'll use as the EOS marker). After the `+1`, the longest sequence in the batch (e.g. length 5) becomes length 6 (with one pad). After `[:-1]`, it goes back to length 5 but with the original last element preserved.

This matters because in draft 2 we'll compute targets as `inputs[1:]` — shifted by one. The pad we appended becomes the *target* for the original last input token. The model learns to predict EOS at the end of every sequence.

### Why `pad_token_id=50256`?

This is GPT-2's `<|endoftext|>` token. We're recycling it as both:
* **PAD token** — fills the right side of short sequences.
* **EOS token** — marks the end of meaningful content.

GPT-2 wasn't designed with separate PAD and EOS, so this reuse is the standard convention.

### What's missing from draft 1?

Targets. For training we need both `inputs` (what the model sees) and `targets` (what we want it to predict). Draft 2 adds targets.

---

## 8 — Section 7.3: Custom Collate Draft 2 — Targets Shifted by One

```python
def custom_collate_draft_2(batch, pad_token_id=50256, device="cpu"):
    batch_max_length = max(len(item) + 1 for item in batch)
    inputs_lst, targets_lst = [], []

    for item in batch:
        new_item = item + [pad_token_id]
        padded = new_item + [pad_token_id] * (batch_max_length - len(new_item))
        inputs = torch.tensor(padded[:-1])
        targets = torch.tensor(padded[1:])    # SHIFT BY ONE
        inputs_lst.append(inputs)
        targets_lst.append(targets)

    inputs_tensor = torch.stack(inputs_lst).to(device)
    targets_tensor = torch.stack(targets_lst).to(device)
    return inputs_tensor, targets_tensor
```

### The shift-by-one pattern

For input `[0, 1, 2, 3, 4]`:

| Position | Input | Target |
|----------|-------|--------|
| 0 | 0 | 1 |
| 1 | 1 | 2 |
| 2 | 2 | 3 |
| 3 | 3 | 4 |
| 4 | 4 | (next token, which is EOS-pad = 50256) |

The target at position `t` is whatever token the model should output *after* seeing tokens `[0..t]`. This is the canonical next-token-prediction setup.

### Where the `+1` finally pays off

Look at the original sequence `[0, 1, 2, 3, 4]` of length 5. After `+ [pad_token_id]` it becomes `[0, 1, 2, 3, 4, 50256]` of length 6. With `max_length = max(len+1) = 6` for the longest sequence, no padding is added for it (`6 - 6 = 0`).

Then:
* `inputs = padded[:-1]` → `[0, 1, 2, 3, 4]` (back to length 5)
* `targets = padded[1:]` → `[1, 2, 3, 4, 50256]` (length 5)

The last target is `50256` — the model is taught to predict EOS at the end. This is what tells the model when to stop generating during inference.

### Inspecting the output

For our toy batch:

```
inputs:
tensor([[    0,     1,     2,     3,     4],
        [    5,     6, 50256, 50256, 50256],
        [    7,     8,     9, 50256, 50256]])

targets:
tensor([[    1,     2,     3,     4, 50256],
        [    6, 50256, 50256, 50256, 50256],
        [    8,     9, 50256, 50256, 50256]])
```

### What's still wrong?

Look at row 2's targets: `[6, 50256, 50256, 50256, 50256]`. The model is being asked to predict 50256 at positions 2, 3, AND 4 — that's three identical predictions on padding.

In cross-entropy this drowns out the meaningful signal at position 1. The model spends most of its gradient learning to predict the padding token. Draft 3 fixes this.

---

## 9 — Section 7.3: Custom Collate Final — Masking Padding With -100

```python
def custom_collate_fn(
    batch,
    pad_token_id=50256,
    ignore_index=-100,
    allowed_max_length=None,
    device="cpu",
):
    batch_max_length = max(len(item) + 1 for item in batch)
    inputs_lst, targets_lst = [], []

    for item in batch:
        new_item = item + [pad_token_id]
        padded = new_item + [pad_token_id] * (batch_max_length - len(new_item))
        inputs = torch.tensor(padded[:-1])
        targets = torch.tensor(padded[1:])

        # Mask all but the first padding token in targets with -100
        mask = targets == pad_token_id
        indices = torch.nonzero(mask).squeeze()
        if indices.numel() > 1:
            targets[indices[1:]] = ignore_index

        # Optional truncation to allowed_max_length
        if allowed_max_length is not None:
            inputs = inputs[:allowed_max_length]
            targets = targets[:allowed_max_length]

        inputs_lst.append(inputs)
        targets_lst.append(targets)

    return (
        torch.stack(inputs_lst).to(device),
        torch.stack(targets_lst).to(device),
    )
```

### The key new logic

```python
mask = targets == pad_token_id
indices = torch.nonzero(mask).squeeze()
if indices.numel() > 1:
    targets[indices[1:]] = ignore_index
```

Three steps:

1. **`mask`** is a boolean tensor: True at every position where `targets[i] == 50256`.
2. **`indices`** lists the positions where the mask is True.
3. **`targets[indices[1:]] = -100`** replaces every padding-token target *except the first one* with `-100`.

### Why keep the *first* padding token?

The first 50256 in the targets is the **legitimate EOS** — the position where the model should learn to stop. We want gradient flowing through that target so the model learns to emit EOS at the right time.

Every padding token *after* the first is just filler — we don't want gradients flowing through those.

### What `-100` does

The next section explains in detail, but the short version: PyTorch's `cross_entropy` treats `-100` as a special "ignore me" value. Positions with target `-100` are skipped entirely — they contribute nothing to the loss and nothing to the gradient.

### After the mask, our toy batch becomes

```
targets:
tensor([[    1,     2,     3,     4, 50256],     # last 50256 = real EOS, kept
        [    6, 50256,  -100,  -100,  -100],     # 1st 50256 = EOS, rest masked
        [    8,     9, 50256,  -100,  -100]])    # 1st 50256 = EOS, rest masked
```

Only **one** EOS per sequence contributes to the loss. The model learns the right thing: predict the next real token, then predict EOS, then *do not* contribute to the loss for anything that follows.

### What `allowed_max_length` does

```python
if allowed_max_length is not None:
    inputs = inputs[:allowed_max_length]
    targets = targets[:allowed_max_length]
```

A safety cap. GPT-2 Medium has a 1024-token context window. If a particular batch had a 2000-token entry (which shouldn't happen with this small dataset but is possible in general), feeding it to the model would crash on a positional-embedding out-of-bounds error. Truncating to 1024 prevents this.

---

## 10 — Section 7.3: Why -100? cross_entropy's ignore_index

```python
# Without -100 — adding a third example raises the loss
logits_1 = torch.tensor([[-1.0, 1.0], [-0.5, 1.5]])
targets_1 = torch.tensor([0, 1])
loss_1 = torch.nn.functional.cross_entropy(logits_1, targets_1)
# tensor(1.1269)

logits_2 = torch.tensor([[-1.0, 1.0], [-0.5, 1.5], [-0.5, 1.5]])   # extra row
targets_2 = torch.tensor([0, 1, 1])
loss_2 = torch.nn.functional.cross_entropy(logits_2, targets_2)
# tensor(0.7936)  -- different because one more sample contributes

# Now mask the third target with -100
targets_3 = torch.tensor([0, 1, -100])
loss_3 = torch.nn.functional.cross_entropy(logits_2, targets_3)
# tensor(1.1269)  -- IDENTICAL to loss_1!
```

### The verification

This three-cell experiment is the punchline of section 7.3. It proves that **putting `-100` in targets makes those positions invisible to the loss**.

Cross-entropy internally:
1. Iterates over each position.
2. Skips positions where the target is `-100`.
3. Computes loss for the remaining positions only.
4. Returns the average over non-ignored positions.

The default `ignore_index` value is `-100`. You can change it if you need to (`cross_entropy(..., ignore_index=99999)`), but the convention is universally `-100`.

### Why `-100` specifically?

Two reasons:
1. **Negative numbers can't be valid class indices.** Class labels for vocabulary tokens are `[0, 50256]`. Negatives are out of range, so they're safe to repurpose as sentinel values.
2. **`-100` is the smallest "round" negative number that's clearly an unlikely accident.** If `ignore_index=-1`, you might collide with a `-1` in your real targets. `-100` is unambiguously a sentinel.

### The mathematical effect

For our case, ignoring padding positions means the loss is:

$$L = \frac{1}{N_{\text{real}}} \sum_{i \in \text{real positions}} -\log P(\text{target}_i)$$

where $N_{\text{real}}$ is the number of non-`-100` targets. The padding positions don't shift the average or the gradient.

### Why this matters for instruction tuning

Without `-100`, a batch with one short response and one long response would have the loss dominated by whichever sequence had more padding. The short sequence's padding positions would contribute as many loss terms as the long sequence's actual response — making the gradient strongly biased toward "predict EOS" rather than "predict useful response tokens."

With `-100`, every token-prediction position carries equal weight regardless of how much padding the batch contains. The loss is a true average over meaningful predictions.

---

## 11 — Section 7.4: Device Selection and functools.partial

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


from functools import partial

customized_collate_fn = partial(
    custom_collate_fn,
    device=device,
    allowed_max_length=1024,
)
```

### Device selection — same ladder as chapter 5

CUDA → MPS (Apple Silicon) → CPU. Identical to chapter 5 section 14. The MPS version check (`>= 2.9`) avoids a known PyTorch 2.4–2.8 bug on Apple Silicon where multinomial sampling produces different results than CUDA.

### What `partial` does

`functools.partial(func, **kwargs)` returns a new function that's `func` with some arguments **pre-filled**. So:

```python
customized_collate_fn = partial(
    custom_collate_fn,
    device=device,
    allowed_max_length=1024,
)
```

…creates a new callable `customized_collate_fn` that when called with `(batch)` is equivalent to:

```python
custom_collate_fn(batch, device=device, allowed_max_length=1024)
```

We need this because `DataLoader` calls its `collate_fn` with **only one argument** (the batch). We can't pass extra kwargs through it. `partial` lets us bake the device and length cap into the function signature.

### Why pin `allowed_max_length=1024`?

GPT-2 Medium's positional embedding table has 1024 entries. Sequences longer than 1024 would access positions 1024+ and crash. `allowed_max_length=1024` truncates anything that would otherwise overflow.

For this dataset, only a small fraction of entries are anywhere near 1024 tokens — most are 30-100. But the safety cap prevents a rare long entry from killing your training run.

---

## 12 — Section 7.4: Creating the DataLoaders

```python
from torch.utils.data import DataLoader

num_workers = 0
batch_size = 8

torch.manual_seed(123)

train_dataset = InstructionDataset(train_data, tokenizer)
train_loader = DataLoader(
    train_dataset,
    batch_size=batch_size,
    collate_fn=customized_collate_fn,
    shuffle=True,
    drop_last=True,
    num_workers=num_workers,
)

val_dataset = InstructionDataset(val_data, tokenizer)
val_loader = DataLoader(
    val_dataset,
    batch_size=batch_size,
    collate_fn=customized_collate_fn,
    shuffle=False,
    drop_last=False,
    num_workers=num_workers,
)
```

### What's new vs chapter 5's loaders

Two things:

1. **`collate_fn=customized_collate_fn`** — uses our custom batching with padding and -100 masking. Chapter 5 used the default collate (which assumes all samples have the same length).
2. **Variable-length sequences are supported.** Each batch can have a different max length (because the longest sequence in *that batch* sets the padding length). Earlier chapters fixed `max_length=context_length` for every batch.

### Why `batch_size=8`?

It's a compromise:
* Small batches train faster per step (fewer floats to crunch).
* Big batches give smoother gradient estimates and use the GPU better.

8 hits the sweet spot for GPT-2 Medium on a single 8 GB GPU. With smaller VRAM you might drop to 4; with more, you could go to 16 or 32 but the gains diminish quickly for a 1100-sample dataset.

### Why `num_workers=0`?

Same reason as chapter 5: the dataset is tiny (~1000 samples). The fork overhead of multiple data-loading workers is bigger than the time they'd save. For large datasets (millions of samples) you'd use `num_workers=4` or `8`.

### Why `shuffle=True` for train, `False` for val?

* **Train**: shuffling prevents the model from memorising the order of samples. Each epoch sees the data in a different random order.
* **Val**: not shuffled because we want deterministic loss measurement across epochs. If shuffled, val loss would depend on which subset got batched together.

### Why `drop_last=True` for train, `False` for val?

* **Train**: a half-full final batch has a less reliable gradient estimate. Skipping it avoids inserting noise.
* **Val**: we want loss on *all* validation samples, so we keep the final partial batch.

---

## 13 — Section 7.4: Inspecting Batch Shapes

```python
print("Train loader:")
for inputs, targets in train_loader:
    print(inputs.shape, targets.shape)
```

Expected output (a small sample):

```
torch.Size([8, 61])  torch.Size([8, 61])
torch.Size([8, 76])  torch.Size([8, 76])
torch.Size([8, 73])  torch.Size([8, 73])
torch.Size([8, 68])  torch.Size([8, 68])
...
```

### What's interesting here

Every batch has size 8 (because `batch_size=8`). But the **sequence length differs per batch** — 61, 76, 73, 68, ...

This is the **dynamic padding** behaviour we built. Each batch is padded only to the length of its own longest sequence, not to some global maximum. If a batch happens to contain only short sequences, it stays short. If it has a long one, all the others are padded up to match.

### Memory implications

Compared to fixed-length batches (every sequence padded to 1024), dynamic padding saves enormous memory. A batch where the longest sequence is 76 tokens uses `8 × 76 = 608` total token positions. With fixed-length padding it would be `8 × 1024 = 8192` — **13× more memory**.

This is what makes instruction tuning of medium-size models feasible on consumer GPUs. Without dynamic padding, the same batch size would OOM on machines with less VRAM.

### Inspecting one input and target

```python
print(inputs[0])
print(targets[0])
```

Expected:
```
inputs[0]: tensor([21106, 318, ..., 50256, 50256, ..., 50256])
targets[0]: tensor([318, 257, ..., 50256, -100, ..., -100])
```

You can directly see:
* The inputs end with multiple `50256` (padding).
* The targets end with `50256` once (the legitimate EOS), followed by `-100` (the ignored padding positions).

This is exactly what the collate function was designed to produce.

---

## 14 — Section 7.5: Loading the 355M GPT-2 Medium

```python
from gpt_download import download_and_load_gpt2
from previous_chapters import GPTModel, load_weights_into_gpt

BASE_CONFIG = {
    "vocab_size": 50257,
    "context_length": 1024,
    "drop_rate": 0.0,
    "qkv_bias": True,
}

model_configs = {
    "gpt2-small (124M)":  {"emb_dim":  768, "n_layers": 12, "n_heads": 12},
    "gpt2-medium (355M)": {"emb_dim": 1024, "n_layers": 24, "n_heads": 16},
    "gpt2-large (774M)":  {"emb_dim": 1280, "n_layers": 36, "n_heads": 20},
    "gpt2-xl (1558M)":    {"emb_dim": 1600, "n_layers": 48, "n_heads": 25},
}

CHOOSE_MODEL = "gpt2-medium (355M)"

BASE_CONFIG.update(model_configs[CHOOSE_MODEL])

model_size = CHOOSE_MODEL.split(" ")[-1].lstrip("(").rstrip(")")
settings, params = download_and_load_gpt2(model_size=model_size, models_dir="gpt2")

model = GPTModel(BASE_CONFIG)
load_weights_into_gpt(model, params)
model.eval()
```

### Why GPT-2 Medium instead of Small?

Chapter 5 used the 124M model because it was just for showing that *training* works. Chapter 7 is about whether the trained model can **actually do something useful** (instruction-following), so we step up to the 355M version.

The difference matters:
* **GPT-2 Small (124M)** — barely follows instructions even after SFT. Outputs are often incoherent.
* **GPT-2 Medium (355M)** — usable. Most responses make grammatical sense and often address the instruction correctly.
* **GPT-2 Large (774M)** — visibly better but takes 2× longer to train.
* **GPT-2 XL (1558M)** — best of the four but won't fit comfortably in 8 GB VRAM.

### The new config keys

| Key | Value | Why |
|-----|-------|-----|
| `drop_rate` | 0.0 | We disable dropout for SFT. With only 1100 samples, dropout's regularisation would hurt more than help. |
| `qkv_bias` | True | GPT-2's Q/K/V projections include bias terms. Our `MultiHeadAttention` class from chapter 3 supports this via the `qkv_bias` constructor argument. |

### What `load_weights_into_gpt` does

Exactly the same function from chapter 5 section 29 — it copies OpenAI's TensorFlow checkpoint into our PyTorch model. The function detects the model size automatically by examining the params dict, so it works equally for the small, medium, large, and XL variants.

### Why `model.eval()` here?

Before we even start training, we want to **demo the model's behaviour as a pretrained-only model**. Putting it in eval mode disables dropout (which wouldn't matter since `drop_rate=0.0` anyway) and makes generation deterministic.

We'll switch to `model.train()` when we begin SFT in section 17.

---

## 15 — Section 7.5: Generation Before Finetuning

```python
torch.manual_seed(123)
input_text = format_input(val_data[0])
print(input_text)

from previous_chapters import generate, text_to_token_ids, token_ids_to_text

token_ids = generate(
    model=model,
    idx=text_to_token_ids(input_text, tokenizer),
    max_new_tokens=35,
    context_size=BASE_CONFIG["context_length"],
    eos_id=50256,
)
generated_text = token_ids_to_text(token_ids, tokenizer)
response_text = (
    generated_text[len(input_text):]
    .replace("### Response:", "")
    .strip()
)
print(response_text)
```

### What this cell shows

We pick the first validation entry, format it with the Alpaca template, ask the **pretrained** (not yet SFT-tuned) model to continue, and print the result.

The expected response from this pretrained model is **gibberish** — something like:

```
The chef cooks the meal every day. ### Response: The chef has been cooking the meal every day.
The chef has been cooking the meal every day. ### Response: ...
```

The model echoes the structure but doesn't actually follow the instruction. It's been pretrained to do text completion, not to recognise the Alpaca instruction template.

### Why strip away `### Response:` from the printed output

The `generate` function from chapter 5 returns the full sequence (prompt + generated tokens). We want to show only what the model produced, so we:

1. Slice off the prompt: `generated_text[len(input_text):]`.
2. Remove the `### Response:` header (otherwise it'd show in every print).
3. `.strip()` whitespace.

What remains is purely what the model generated after the prompt.

### The eos_id=50256 argument

Our `generate` function from chapter 5 stops when it produces the EOS token. Without this, the model might generate until `max_new_tokens=35` even when it should have stopped much earlier.

### The takeaway

After this cell, you've **proven the model needs finetuning**. The pretrained weights know English grammar but have no idea that `### Response:` means "now produce a helpful answer." Sections 7.6 onward fix this.

---

## 16 — Section 7.6: Initial Loss Before Training

```python
from previous_chapters import calc_loss_loader, train_model_simple

model.to(device)

torch.manual_seed(123)

with torch.no_grad():
    train_loss = calc_loss_loader(train_loader, model, device, num_batches=5)
    val_loss   = calc_loss_loader(val_loader,   model, device, num_batches=5)

print("Training loss:", train_loss)
print("Validation loss:", val_loss)
```

### Why measure pre-training loss?

A pre-training-loss check tells you:
1. **Whether your data loader is working at all.** A loss of `nan` or `inf` here means something is broken in the pipeline.
2. **A baseline to measure improvement against.** If your loss after training is the same as before training, your training loop is broken.

Expected output: roughly `3.8`. For comparison, a perfectly random model would have loss `log(50257) ≈ 10.8`. Our pretrained model is already much better than random at predicting English next-tokens — but the format-specific predictions (which tokens come after `### Response:`) it's never seen.

### Why `num_batches=5` instead of the full loader?

The full validation loop runs every step during training (see section 7.6 below). At this preview stage we just want a rough estimate, not a precise one. 5 batches × 8 samples × ~70 tokens = ~2800 token predictions, which is plenty for a stable estimate.

### Why `torch.no_grad()`?

We're not training — just measuring. Disabling autograd avoids building the computation graph, which saves both memory and time.

### The same calc_loss_loader from chapter 5

This is *literally* the same function from chapter 5 section 13. The instruction-tuning loss is just next-token cross-entropy, exactly like pretraining. The only difference is the data we're training on. The training mechanism is identical.

---

## 17 — Section 7.6: The 2-Epoch Training Run

```python
import time

start_time = time.time()
torch.manual_seed(123)

optimizer = torch.optim.AdamW(model.parameters(), lr=0.00005, weight_decay=0.1)
num_epochs = 2

train_losses, val_losses, tokens_seen = train_model_simple(
    model, train_loader, val_loader, optimizer, device,
    num_epochs=num_epochs,
    eval_freq=5,
    eval_iter=5,
    start_context=format_input(val_data[0]),
    tokenizer=tokenizer,
)

end_time = time.time()
print(f"Training took {(end_time - start_time)/60:.2f} minutes")
```

### The hyperparameters and why

#### `lr=5e-5` — much lower than pretraining

Chapter 5 used `lr=4e-4` for pretraining. Chapter 7 drops to `lr=5e-5` — almost **10× lower**.

Why? SFT is about **fine adjustment**, not from-scratch learning. The pretrained model already knows English; we're just teaching it a format. Large learning rates would destabilise the well-learned weights. Small steps preserve them while nudging toward the desired behaviour.

This pattern is universal across all finetuning approaches (LoRA, QLoRA, full SFT): lower learning rates than pretraining. The smaller the conceptual change, the smaller the steps should be.

#### `weight_decay=0.1`

Stronger regularisation than usual. With only 1100 samples, overfitting is a real concern. Weight decay pulls weights toward zero, discouraging the model from memorising specific training pairs.

#### `num_epochs=2`

Empirically chosen. Past 2 epochs:
* Train loss keeps dropping (model memorises responses).
* Val loss plateaus or rises (no real generalisation gained).
* Outputs become noticeably "templated" — they echo training-data phrasings rather than producing novel responses.

For larger datasets (50k+ samples), 3-5 epochs is standard. For 1k samples, 2 is right.

#### `eval_freq=5` and `eval_iter=5`

Same conventions as chapter 5. Evaluate every 5 gradient steps using 5 batches of each loader. With ~116 training steps per epoch and 232 total over 2 epochs, this gives ~46 evaluation points.

### What you see during the run

```
Ep 1 (Step 000000): Train loss 3.808, Val loss 3.722
Ep 1 (Step 000005): Train loss 3.184, Val loss 3.276
...
Ep 1 (Step 000115): Train loss 0.671, Val loss 0.851
Ep 2 (Step 000005): Train loss 0.624, Val loss 0.842
...
```

Loss drops from ~3.8 to ~0.7 in the first epoch alone. By the end of epoch 2 you're at ~0.6 train / ~0.8 val.

### Why training time is longer than chapter 5

GPT-2 Medium has **3× more parameters** than GPT-2 Small (355M vs 124M). Combined with a smaller batch size (8 vs 2) and more samples per epoch (935 vs 9):

* Chapter 5: 90 total steps, ~5 minutes
* Chapter 7: ~232 total steps, ~10-15 minutes on a single GPU

---

## 18 — Section 7.6: Plotting the Loss Curve

```python
from previous_chapters import plot_losses

epochs_tensor = torch.linspace(0, num_epochs, len(train_losses))
plot_losses(epochs_tensor, tokens_seen, train_losses, val_losses)
```

### What the plot shows

The standard chapter-5-style figure: two curves (train and val), dual x-axis (epochs and tokens seen).

Three patterns are visible:

1. **Sharp drop in the first half-epoch.** Loss falls from ~3.8 to ~1.5 very quickly — the model is rapidly learning the *format* (where `### Response:` appears, what kind of text follows it).
2. **Slower decline through the rest of training.** Loss continues to fall but at a much slower rate. This is the model learning the *content patterns* of good responses.
3. **Small train/val gap.** Train loss is only slightly below val loss, suggesting the model isn't overfitting *yet*. Run for more epochs and this gap would widen.

### Sanity check — are the curves smooth?

If the loss is wildly noisy (one step at 1.2, next at 3.8), something is wrong: maybe learning rate too high, batch size too small, or one specific batch is corrupted. For correctly-set hyperparameters the curves should be smooth-ish with mild stochastic wobble.

### What plot_losses is doing

The same function from chapter 5 section 17. Takes the recorded loss values, plots them against epochs with a secondary tokens-seen axis, saves to a PDF. Reuses the existing tooling — no new code needed.

---

## 19 — Section 7.7: Generating Responses for the Test Set

```python
from tqdm import tqdm

for i, entry in tqdm(enumerate(test_data), total=len(test_data)):
    input_text = format_input(entry)
    token_ids = generate(
        model=model,
        idx=text_to_token_ids(input_text, tokenizer).to(device),
        max_new_tokens=256,
        context_size=BASE_CONFIG["context_length"],
        eos_id=50256,
    )
    generated_text = token_ids_to_text(token_ids, tokenizer)
    response_text = (
        generated_text[len(input_text):]
        .replace("### Response:", "")
        .strip()
    )
    test_data[i]["model_response"] = response_text

with open("instruction-data-with-response.json", "w") as file:
    json.dump(test_data, file, indent=4)
```

### What this cell does

For every test entry (110 of them):
1. Format the instruction using the Alpaca template.
2. Run `generate` with a max of 256 new tokens (more than enough for typical short responses).
3. Strip the prompt prefix and `### Response:` from the output.
4. Attach the cleaned response to the test entry under the new key `"model_response"`.

After the loop, the test entries have four keys: `instruction`, `input`, `output` (the ground truth), and `model_response` (what our finetuned model said). We save this enriched data to JSON for the judge in section 7.8.

### Why save to JSON?

Two reasons:
1. **Decouple generation from evaluation.** Generation is slow (the GPT-2 forward pass × 110 entries). Evaluation can happen anytime later without re-running generation.
2. **Inspect-by-eye check.** You can open the JSON file and read individual responses before letting the judge score them. This catches obvious failures (model outputting only padding tokens, all responses being identical, etc.).

### Why `max_new_tokens=256`?

Most responses in the dataset are 20-60 tokens. 256 is a comfortable upper bound that almost no response will hit. The `eos_id=50256` argument means the loop terminates early if the model outputs EOS, so 256 is just the safety cap.

### Why the progress bar matters

110 generations × ~1-2 seconds each = 2-4 minutes total. Without `tqdm`, you'd stare at a blank screen wondering if the process is alive. The progress bar shows you exactly how many entries are left and the ETA.

---

## 20 — Section 7.7: Saving the Finetuned Model

```python
import re

file_name = f"{re.sub(r'[ ()]', '', CHOOSE_MODEL) }-sft.pth"
torch.save(model.state_dict(), file_name)
print(f"Model saved as {file_name}")
```

Saves the trained model weights as `gpt2-medium355M-sft.pth` (note the `re.sub` strips spaces and parentheses from the model name).

### Why save only the state_dict?

Same reasons as chapter 5 section 23:
* Portable across code refactors.
* Smaller than pickling the full model object.
* Safer with `weights_only=True` on load.

### File size

GPT-2 Medium has 355M parameters in bfloat16 (assuming it was loaded as bfloat16). That's ~700 MB on disk. In float32 it would be ~1.4 GB.

### Loading it back

The notebook doesn't demonstrate it explicitly (`load-finetuned-model.ipynb` is a sibling notebook), but the pattern is:

```python
model_sft = GPTModel(BASE_CONFIG)
model_sft.load_state_dict(torch.load(file_name, weights_only=True))
model_sft.eval()
```

You get back a clean instance of the model with all the SFT improvements baked in.

---

## 21 — Section 7.8: Why You Need an LLM Judge

Chapter 5 evaluated quality with **perplexity** (chapter 7 section 9 of the book). That's a great metric for pretraining but a terrible one for instruction following. Here's why.

### The problem with perplexity for instructions

Perplexity measures **how confidently the model predicts the training tokens**. For instructions like *"What is the capital of France?"*:

* A model that confidently outputs "*Paris is the capital of France.*" has low perplexity. ✓
* A model that confidently outputs "*Berlin is the capital of France.*" *also* has low perplexity — confident, fluent, just wrong.

Perplexity can't distinguish "fluent and correct" from "fluent and wrong." It only measures fluency.

### What you actually want to measure

For an instruction-following model you want:

1. **Did it follow the instruction?** (relevance)
2. **Is the answer correct?** (accuracy)
3. **Is it the right length?** (verbosity)
4. **Is it well-written?** (style)

These are subjective. Until 2023 there was no good automated way to measure them — you'd send the model outputs to human raters.

### The Llama-3-as-judge approach

The breakthrough: use **another LLM** to score your model's responses. Send Llama 3 the (instruction, ground-truth, model-response) triplet and ask it to score on a 0-100 scale.

This works because:
* Llama 3 is much larger than our finetuned GPT-2 Medium, so it can sensibly judge whether a response addresses an instruction.
* Llama 3 has no stake in the outcome — it's not the one being evaluated.
* Llama 3 produces a *consistent* judgment (with `temperature=0`), so you can reproduce scores.

This is exactly the technique used in production: **AlpacaEval**, **MT-Bench**, **Arena-Hard** — all use stronger models as judges for weaker ones.

### Why Llama 3 specifically

It's:
* **Free and open** (run locally via Ollama).
* **Reasonably strong** at judging coherent English text.
* **Available in multiple sizes** (8B for fast judgment, 70B for higher quality).

For production research you'd use GPT-4 (more accurate but costs money). For this notebook, Llama 3 strikes the right balance.

---

## 22 — Section 7.8: Setting Up Ollama

The notebook directs you to install **Ollama** before continuing. Ollama is a local LLM server — like running OpenAI's API but on your own machine.

### What Ollama provides

* **Easy installation** — download from ollama.com, install, run.
* **One-line model downloads** — `ollama pull llama3` fetches and quantises the model.
* **HTTP API** — POST a prompt to `http://localhost:11434/api/chat`, get back a response. Identical pattern to OpenAI's API but local.

### Why Ollama instead of HuggingFace transformers?

The book has been using HuggingFace + PyTorch throughout. Why switch for the judge?

Three reasons:
1. **Llama 3 is huge.** The 8B model in float16 is 16 GB; even after 4-bit quantisation it's ~5 GB. HuggingFace + PyTorch would require all that VRAM at the same time as your GPT-2 Medium is loaded.
2. **Ollama auto-quantises.** It downloads pre-quantised GGUF versions of models, which fit in less memory.
3. **Decoupled deployment.** Ollama runs as a separate process; you don't have to coordinate model loading inside Python. Just call the HTTP API.

### Starting the Ollama server

The notebook expects you to have Ollama running in a separate terminal:

```bash
ollama serve         # starts the HTTP API on port 11434
ollama pull llama3   # downloads the Llama 3 model
```

Once running, the rest of the notebook calls the API via Python's `requests` library.

---

## 23 — Section 7.8: The check_if_running Utility

```python
import psutil

def check_if_running(process_name):
    running = False
    for proc in psutil.process_iter(["name"]):
        if process_name in proc.info["name"]:
            running = True
            break
    return running

ollama_running = check_if_running("ollama")
if not ollama_running:
    raise RuntimeError("Ollama not running. Launch ollama before proceeding.")
print("Ollama running:", ollama_running)
```

### What this does

Iterates every process on the system and checks if any of them has `"ollama"` in its name. If yes, returns True; otherwise False.

### Why this defensive check?

Without it, the next cell would attempt to call `http://localhost:11434/api/chat` and get a `ConnectionRefusedError`. The error would be cryptic — "connection refused" doesn't immediately tell you that you forgot to start Ollama.

This cell turns that into a clear "Ollama not running. Launch ollama before proceeding." error message — much more useful for debugging.

### Why `psutil.process_iter(["name"])`?

`psutil` is a cross-platform process inspection library. `process_iter` yields one entry per running process. We pass `["name"]` to limit what's collected to just the process name (faster than collecting everything).

### Limitations

This doesn't check whether Ollama is *responsive* — only that a process named "ollama" exists. The process could be a stale one that's not actually listening on port 11434. For a stricter check you'd send a test request to the API and verify a 200 response. For tutorial purposes, the simple process check is enough.

---

## 24 — Section 7.8: The query_model Function

```python
import requests, json

def query_model(prompt, model="llama3", url="http://localhost:11434/api/chat"):
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"seed": 123, "temperature": 0, "num_ctx": 2048},
    }
    response = requests.post(url, json=data, stream=True)

    response_data = ""
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            response_data += chunk["message"]["content"]

    return response_data
```

### What this function does

Sends a prompt to the Ollama-served Llama 3 model and collects the streamed response into a single string.

### The Ollama API contract

POST to `/api/chat` with this JSON body:

```json
{
    "model": "llama3",
    "messages": [{"role": "user", "content": "<your prompt>"}],
    "options": {"seed": 123, "temperature": 0, "num_ctx": 2048}
}
```

Three options:
* **`seed`** — RNG seed. With `temperature=0` it's irrelevant (greedy decoding is deterministic), but setting it anyway is good practice.
* **`temperature=0`** — greedy decoding. Critical for evaluation reproducibility. With any positive temperature, the same prompt could get scored 70 one time and 75 another.
* **`num_ctx=2048`** — context window. Long enough for the prompt + ground-truth + model-response to fit comfortably.

### Why streaming response?

Ollama returns responses as a sequence of newline-separated JSON chunks, one per generated token (or small batch of tokens). Each chunk looks like:

```json
{"model": "llama3", "message": {"role": "assistant", "content": "5"}}
{"model": "llama3", "message": {"role": "assistant", "content": "0"}}
{"model": "llama3", "message": {"role": "assistant", "content": "/"}}
{"model": "llama3", "message": {"role": "assistant", "content": "10"}}
...
```

The loop concatenates the `content` field of each chunk into one string. By the end, `response_data` is the full text Llama 3 generated.

### Why use streaming instead of waiting for the whole response?

Two reasons:
1. **Lower latency for long responses.** You can start processing while the model is still generating. (Not used here, but available.)
2. **It's the default API behaviour.** Setting `stream=False` would change the response format and require slightly different parsing. Following the default is simpler.

---

## 25 — Section 7.8: One-Response Evaluation Walkthrough

```python
for entry in test_data[:3]:
    prompt = (
        f"Given the input `{format_input(entry)}` "
        f"and correct output `{entry['output']}`, "
        f"score the model response `{entry['model_response']}` "
        f"on a scale from 0 to 100, where 100 is the best score."
    )
    print("\n" + "=" * 50)
    print("Instruction:", entry["instruction"])
    print("Correct response:", entry["output"])
    print("Model response:", entry["model_response"])
    print("Score:", query_model(prompt))
```

### The judge prompt template

```
Given the input <full Alpaca-formatted instruction>,
and correct output <ground-truth output>,
score the model response <our finetuned GPT-2's response>
on a scale from 0 to 100, where 100 is the best score.
```

Llama 3 reads this, considers all three pieces, and returns a score in plain text (e.g. `"75"` or `"The score is 60/100 because..."`).

### What you see from this cell

Three full evaluation walkthroughs printed to the screen. For example:

```
==================================================
Instruction: Rewrite the sentence to start with 'Although'.
Correct response: Although the cake is sweet, it is not my favourite.
Model response: Although the cake is sweet, it is not my favourite.
Score: 95

==================================================
Instruction: Convert the following sentence into the simple present tense.
Correct response: The chef cooks the meal every day.
Model response: The chef has been cooking the meal every day.
Score: 60
```

### Why preview the first 3 only?

Showing all 110 would flood the notebook with thousands of lines of output. Three is enough to:
* Verify the judge prompt works and produces reasonable scores.
* Sanity-check a few model responses by eye.
* Make sure the score format is what you expect (a number, not prose).

After this preview, the next cell scores the full test set.

### Why scoring on a 0-100 scale and not, say, 1-5?

Wider scales let the judge express finer distinctions ("not bad but missing detail" → 65 vs 70). Narrower scales tend to bunch scores at the extremes. 0-100 is the de facto standard for LLM evaluation.

---

## 26 — Section 7.8: generate_model_scores — Scoring the Whole Test Set

```python
def generate_model_scores(json_data, json_key, model="llama3"):
    scores = []
    for entry in tqdm(json_data, desc="Scoring entries"):
        prompt = (
            f"Given the input `{format_input(entry)}` "
            f"and correct output `{entry['output']}`, "
            f"score the model response `{entry[json_key]}` "
            f"on a scale from 0 to 100, where 100 is the best score. "
            f"Respond with the integer number only."
        )
        score = query_model(prompt, model=model)
        try:
            scores.append(int(score))
        except ValueError:
            print(f"Could not convert score: {score}")
            continue
    return scores

scores = generate_model_scores(test_data, "model_response")
print(f"Number of scores: {len(scores)} of {len(test_data)}")
print(f"Average score: {sum(scores) / len(scores):.2f}\n")
```

### Three improvements over the preview cell

1. **"Respond with the integer number only" suffix.** This nudges Llama 3 to output `60` instead of `"The score is 60/100 because..."`. Cuts down on parsing failures.
2. **`try/except` around the `int()` conversion.** Sometimes Llama still adds extra text. The except clause prints a warning and skips that entry rather than crashing the whole loop.
3. **`tqdm` progress bar.** 110 entries × ~1-2 seconds per Llama call = 2-4 minutes total.

### What `sum(scores) / len(scores)` reports

The **average** score across the whole test set. For GPT-2 Medium SFT-tuned on 1100 Alpaca examples, expect around **50-55**. For comparison, the book mentions:

* Open Assistant's pretrained Llama 2 70B: ~70.
* GPT-3.5: ~85.
* GPT-4: ~95.

We're nowhere near GPT-4, of course. But the fact that a 355M-parameter model finetuned on 1100 examples can produce *coherent* responses to instructions at all is itself a meaningful result. Two years before this book was written, no public 355M model could have done it.

### The pattern this teaches

This is the **production evaluation loop** for instruction-tuned models:

```
1. Generate test responses from your model.
2. Judge them with a stronger LLM.
3. Aggregate scores into one number.
4. Compare against baselines.
```

You can swap out the judge (GPT-4 instead of Llama 3) or the eval set (MT-Bench instead of held-out Alpaca) without changing the structure. The pipeline you built here works for *any* instruction-tuned model.

### Why the score is noisy

Llama 3 isn't a perfect judge. It scores the same response differently on different runs (even with `temperature=0`, slight numerical differences across hardware can shift outputs). The 50-55 average has a meaningful margin of error — ±5 points easily.

For more reliable judgments you'd:
* Use a larger judge (GPT-4 or Llama 3 70B).
* Average across multiple judges (ensemble judging).
* Average across multiple seeds for the *same* judge.

For learning purposes, the single-shot Llama 3 judge is plenty.

---

## 27 — Section 7.9: Conclusions and What Comes Next

By the end of chapter 7 you have:

### A working SFT pipeline

* **Custom dataset class** that pre-tokenises Alpaca-format entries.
* **Custom collate function** with dynamic padding and -100 masking.
* **Trained model** that follows instructions reasonably well for a 355M-parameter network.
* **Automated evaluation** using an LLM judge.

This is the complete production-grade SFT loop. Every commercial instruction-tuned LLM (ChatGPT, Claude, Gemini) goes through a version of this same pipeline — bigger models, much bigger datasets, more sophisticated judges, but the same architectural pattern.

### What this chapter intentionally skipped

Three improvements would push the model further but weren't worth the complexity for a teaching notebook:

1. **Loss masking on instruction tokens.** Currently the model computes loss on every token, including the instruction part. Masking those positions (`-100` for instruction tokens, real targets for response tokens) focuses the gradient on response generation. Mentioned in cell 54 but not implemented.
2. **LoRA / QLoRA finetuning.** Full finetuning updates all 355M parameters. LoRA would update ~1M parameters (the adapter weights) while keeping the base model frozen. Faster, less memory, almost as good. Covered in HandsOnLLM chapter 12.
3. **Multi-epoch with early stopping based on val loss.** Currently fixed at 2 epochs. A more careful approach would monitor val loss and stop the moment it starts rising.

### What comes after

The book itself ends here. The natural next steps are:

* **Preference alignment** — train on (chosen, rejected) preference pairs to improve quality further. The DPO loss from HandsOnLLM chapter 12 is the cleanest implementation.
* **Larger base models** — swap GPT-2 Medium for Llama 3 8B or Phi-3 Mini. Same code, much better starting point.
* **Bigger SFT datasets** — Alpaca-cleaned (52k examples), UltraChat (200k), Open Hermes (1M+) all build on the same principles.

But you now have the foundation. SFT, DPO, LoRA, QLoRA — all of these are variations on patterns you've seen in chapters 5, 6, and 7. The hard work was understanding the loss masking, the dynamic batching, the chat template, and the LLM-as-judge evaluation loop. Everything else is engineering.

### A final note on scale

Your model trained on 1100 examples in 10-15 minutes. Production SFT runs on millions of examples for days on hundreds of GPUs. The principles are identical — same loss, same optimisation, same evaluation methodology. What changes is the dataset quality and the engineering polish.

When you read about a new state-of-the-art instruction-tuned LLM, you can now decompose what's happening: SFT pipeline like the one you just built, scaled up. That's the value of having built it yourself — every future LLM release is decipherable in terms of the components you understand.
