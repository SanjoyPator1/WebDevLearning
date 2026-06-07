# Chapter 6 Code Explanation — Finetuning for Text Classification

This document walks through every code cell of `ch06.ipynb` from Sebastian Raschka's *Build a Large Language Model From Scratch*. Chapter 6 is the **first practical finetuning chapter** of the book: you take the pretrained GPT-2 from chapter 5 and re-purpose it into a **binary spam classifier**.

The transformation is surprisingly small:

1. Freeze the base model so its 124M parameters stop changing.
2. Replace the output head (which mapped 768 → 50257 vocab tokens) with a tiny new head (768 → 2 classes).
3. Unfreeze just the **last transformer block + final LayerNorm + new output head** so they can adapt to the classification task.
4. Train with **cross-entropy on the last token's logits** — same loss as pretraining, but applied to only one position per sequence.

The result: a 95%+ accurate SMS spam classifier in about 5 minutes of training on a CPU.

The five book sections are:

* **6.1 Different categories of finetuning** — conceptual overview.
* **6.2 Preparing the dataset** — download SMS spam corpus, balance, split.
* **6.3 Creating data loaders** — `SpamDataset` class with right-padding to a fixed length.
* **6.4 Initializing a model with pretrained weights** — load GPT-2 small.
* **6.5 Adding a classification head** — freeze base, replace `out_head`, unfreeze last block.
* **6.6 Calculating the classification loss and accuracy** — switch from per-token cross-entropy to last-token-only cross-entropy.
* **6.7 Finetuning the model on supervised data** — `train_classifier_simple` with accuracy tracking.
* **6.8 Using the LLM as a spam classifier** — single-text inference via `classify_review`.

Section numbers in this doc (0 → 29) match the linear flow of the notebook.

---

## Table of Contents

- [0 — Notebook Setup and Imports](#0--notebook-setup-and-imports)
- [1 — Section 6.1: Different Categories of Finetuning](#1--section-61-different-categories-of-finetuning)
- [2 — Section 6.2: Downloading the SMS Spam Dataset](#2--section-62-downloading-the-sms-spam-dataset)
- [3 — Section 6.2: Loading the Dataset Into pandas](#3--section-62-loading-the-dataset-into-pandas)
- [4 — Section 6.2: Class Distribution and Why It Matters](#4--section-62-class-distribution-and-why-it-matters)
- [5 — Section 6.2: create_balanced_dataset — Downsampling the Majority Class](#5--section-62-create_balanced_dataset--downsampling-the-majority-class)
- [6 — Section 6.2: Mapping String Labels to Integers](#6--section-62-mapping-string-labels-to-integers)
- [7 — Section 6.2: random_split — Train / Val / Test Split](#7--section-62-random_split--train--val--test-split)
- [8 — Section 6.3: The SpamDataset Class](#8--section-63-the-spamdataset-class)
- [9 — Section 6.3: Constructing the Three Datasets](#9--section-63-constructing-the-three-datasets)
- [10 — Section 6.3: DataLoaders and Batch Inspection](#10--section-63-dataloaders-and-batch-inspection)
- [11 — Section 6.4: Loading the Pretrained GPT-2 Small](#11--section-64-loading-the-pretrained-gpt-2-small)
- [12 — Section 6.4: Baseline — Can the Pretrained Model Already Classify Spam?](#12--section-64-baseline--can-the-pretrained-model-already-classify-spam)
- [13 — Section 6.5: Inspecting the Model Architecture](#13--section-65-inspecting-the-model-architecture)
- [14 — Section 6.5: Freezing the Base Model](#14--section-65-freezing-the-base-model)
- [15 — Section 6.5: Replacing the Output Head](#15--section-65-replacing-the-output-head)
- [16 — Section 6.5: Unfreezing the Last Block and Final LayerNorm](#16--section-65-unfreezing-the-last-block-and-final-layernorm)
- [17 — Section 6.5: One Forward Pass Through the Modified Model](#17--section-65-one-forward-pass-through-the-modified-model)
- [18 — Section 6.6: Why Use the Last Token's Logits](#18--section-66-why-use-the-last-tokens-logits)
- [19 — Section 6.6: From Logits to Predicted Class](#19--section-66-from-logits-to-predicted-class)
- [20 — Section 6.6: calc_accuracy_loader](#20--section-66-calc_accuracy_loader)
- [21 — Section 6.6: Baseline Accuracy Before Training](#21--section-66-baseline-accuracy-before-training)
- [22 — Section 6.6: calc_loss_batch and calc_loss_loader](#22--section-66-calc_loss_batch-and-calc_loss_loader)
- [23 — Section 6.6: Initial Loss Before Training](#23--section-66-initial-loss-before-training)
- [24 — Section 6.7: train_classifier_simple — The Training Loop](#24--section-67-train_classifier_simple--the-training-loop)
- [25 — Section 6.7: Running the 5-Epoch Training](#25--section-67-running-the-5-epoch-training)
- [26 — Section 6.7: Plotting Loss and Accuracy Curves](#26--section-67-plotting-loss-and-accuracy-curves)
- [27 — Section 6.7: Final Accuracy on All Three Sets](#27--section-67-final-accuracy-on-all-three-sets)
- [28 — Section 6.8: classify_review — Single-Text Inference](#28--section-68-classify_review--single-text-inference)
- [29 — Section 6.8: Saving and Loading the Finetuned Classifier](#29--section-68-saving-and-loading-the-finetuned-classifier)

---

## 0 — Notebook Setup and Imports

```python
from importlib.metadata import version

pkgs = ["matplotlib",   # Plotting
        "numpy",        # PyTorch dependency
        "tiktoken",     # GPT-2 BPE tokenizer
        "torch",        # The engine
        "tensorflow",   # Used by gpt_download.py
        "pandas"]       # NEW for ch6 — reads the SMS CSV
for p in pkgs:
    print(f"{p} version: {version(p)}")
```

The only new dependency vs chapter 5 is **pandas**. The SMS spam dataset comes as a tab-separated file; pandas is the cleanest way to load it, balance the class distribution, shuffle, and slice into train/val/test CSVs.

Everything else (`torch`, `tiktoken`, `tensorflow` for loading OpenAI's checkpoint) carries over from chapter 5.

---

## 1 — Section 6.1: Different Categories of Finetuning

This section is purely conceptual (no code). The book introduces two main flavours of finetuning:

| Flavour | What it does | When you use it |
|---------|--------------|-----------------|
| **Classification finetuning** | Replace output head with a small classifier. Use cross-entropy on the *last* token's logits. | When you need a model that outputs **one label** per input (spam vs ham, sentiment, topic). |
| **Instruction finetuning** | Keep the LM head. Train on (instruction, response) pairs so the model continues generating the response. | When you need a model that **generates free-form text** following an instruction (chatbots, summarisation). |

This chapter is purely about the **classification** flavour. Chapter 7 covers the instruction-following flavour.

### Why classification finetuning first?

It's a simpler narrative:
* The training objective doesn't change — still cross-entropy.
* You only need to swap out one tiny layer (the head).
* Accuracy is easy to measure (correct vs incorrect, count, average).
* Datasets are widely available (any labeled-text corpus works).

Once you understand classification finetuning, instruction finetuning is the next conceptual step. Same training mechanics, more complex data.

---

## 2 — Section 6.2: Downloading the SMS Spam Dataset

```python
import requests, zipfile, os
from pathlib import Path

url = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
zip_path = "sms_spam_collection.zip"
extracted_path = "sms_spam_collection"
data_file_path = Path(extracted_path) / "SMSSpamCollection.tsv"


def download_and_unzip_spam_data(url, zip_path, extracted_path, data_file_path):
    if data_file_path.exists():
        print(f"{data_file_path} already exists. Skipping download.")
        return

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with open(zip_path, "wb") as out_file:
        out_file.write(response.content)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extracted_path)

    original_file_path = Path(extracted_path) / "SMSSpamCollection"
    os.rename(original_file_path, data_file_path)
    print(f"File downloaded and saved as {data_file_path}")


download_and_unzip_spam_data(url, zip_path, extracted_path, data_file_path)
```

### What is the SMS Spam Collection?

A classic NLP benchmark from the UCI Machine Learning Repository. It contains **5,574 SMS messages**, each labeled `ham` (not spam) or `spam`. The data was collected from real SMS users in Singapore in the late 2000s and has been a go-to dataset for binary text classification for over a decade.

### Why this dataset for the book?

Three reasons:

1. **Small.** ~5K rows fits in RAM with zero effort. Training takes minutes, not hours.
2. **Real.** The messages are actual SMS spam from the wild, with real slang, abbreviations, and punctuation chaos.
3. **Imbalanced.** ~87% ham, ~13% spam — the typical real-world classification scenario. This forces us to handle class imbalance properly (in cell 19).

### Why the file rename?

The zip extracts as `SMSSpamCollection` with **no extension**. Adding `.tsv` makes it obvious to humans and to text editors (which use the extension to apply syntax highlighting) that this is a tab-separated file. Pure ergonomics.

### Why `requests.get(..., timeout=30)`?

Same defensive pattern as chapters 5 and 7: without a timeout, a slow or broken server can hang your notebook indefinitely. 30 seconds is plenty for a 200 KB file.

### Why `response.raise_for_status()`?

Same reason: if UCI's server returns a 404 or 500 error, we don't want to silently save an HTML error page as if it were the dataset. Raising immediately stops the pipeline at the right place.

---

## 3 — Section 6.2: Loading the Dataset Into pandas

```python
import pandas as pd

df = pd.read_csv(data_file_path, sep="\t", header=None, names=["Label", "Text"])
df
```

Expected output (last few rows):

```
       Label                                              Text
0        ham  Go until jurong point, crazy.. Available only ...
1        ham                      Ok lar... Joking wif u oni...
2       spam  Free entry in 2 a wkly comp to win FA Cup fina...
...
5571     ham                         Will  b going to esplanade fr home?
5572     ham  Pity, * was in mood for that. So...any other s...
5573     ham                         The guy did some bitching but I ac...
5574     ham                                         Rofl. Its true to its name

[5572 rows x 2 columns]
```

### Three key arguments to `pd.read_csv`

* **`sep="\t"`** — the file uses tab-separated values, not commas. Without this argument, pandas would default to commas and parse the whole thing as a single column.
* **`header=None`** — the file has no header row. Without this, pandas would treat the very first SMS as column names.
* **`names=["Label", "Text"]`** — assign our own column names. Now `df["Label"]` and `df["Text"]` are accessible.

### Why pandas instead of plain Python?

You could read this with `open(file).readlines()` and `str.split("\t")` in 5 lines. But pandas gives us:

* `value_counts()` for the class distribution (cell 17).
* `sample(n)` for random downsampling (cell 19).
* `sample(frac=1)` for shuffling (cell 24).
* `to_csv()` for saving the splits (cell 24).

All of these are one-liners with pandas, 5-10 lines each in plain Python. For tabular data, pandas is the right tool.

---

## 4 — Section 6.2: Class Distribution and Why It Matters

```python
print(df["Label"].value_counts())
```

Output:

```
Label
ham     4825
spam     747
Name: count, dtype: int64
```

### The imbalance problem

Of the 5,572 messages, **86.6% are ham**. A model that *always* predicts "ham" — completely ignoring the actual content — would already be 86.6% accurate.

This is a problem because:
1. **Accuracy is a misleading metric** when classes are skewed. 87% accuracy could mean either "perfect spam detector that catches every spam" or "useless model that never predicts spam."
2. **Training dynamics get distorted.** With 6× more ham than spam, every gradient update sees mostly ham. The model learns a strong "default to ham" bias that's hard to overcome.

### Two standard fixes for class imbalance

1. **Downsample the majority class** — randomly drop ham messages until ham_count == spam_count. Used here, in cell 19.
2. **Upsample the minority class** — duplicate spam messages until spam_count == ham_count. Or use synthetic minority oversampling (SMOTE).
3. **Class-weighted loss** — leave the dataset imbalanced but make the loss function care more about spam mistakes (`weight=[1, 6]` to `CrossEntropyLoss`).

The book picks downsampling because it's the simplest and produces a dataset that trains fast. The trade-off: you throw away ~80% of your ham data.

### Why downsampling is OK here

Two reasons make downsampling fine for this notebook:

1. **The educational goal is the finetuning mechanics, not record-breaking accuracy.** We don't need every ham message to demonstrate that GPT-2 can be turned into a classifier.
2. **The remaining dataset is still substantial.** After downsampling we have 747 spam + 747 ham = 1,494 messages, which is plenty for training a small classifier.

For production you'd probably keep all the data and use class weights instead.

---

## 5 — Section 6.2: create_balanced_dataset — Downsampling the Majority Class

```python
def create_balanced_dataset(df):
    num_spam = df[df["Label"] == "spam"].shape[0]
    ham_subset = df[df["Label"] == "ham"].sample(num_spam, random_state=123)
    balanced_df = pd.concat([ham_subset, df[df["Label"] == "spam"]])
    return balanced_df


balanced_df = create_balanced_dataset(df)
print(balanced_df["Label"].value_counts())
```

Expected output:

```
Label
ham     747
spam    747
Name: count, dtype: int64
```

Equal counts now.

### How `df["Label"] == "spam"` works

This is a **boolean mask** — a Series of `True`/`False` the same length as `df`. Passing it as a row selector returns only the rows where the mask is `True`:

```python
df[df["Label"] == "spam"]   # 747 rows
df[df["Label"] == "ham"]    # 4825 rows
```

### `.sample(n, random_state=123)` — random subset

`Series.sample(n)` randomly picks `n` rows. The `random_state` argument fixes the RNG seed so the same set of rows is picked on every run — reproducible.

Why reproducibility matters: if every notebook run picked different ham rows, the train/val/test splits would also be different, and your accuracy numbers wouldn't match the book.

### `pd.concat([ham_subset, spam_rows])` — stack two DataFrames

Concatenation along axis=0 (the default). Output has 747 + 747 = 1,494 rows. **Order matters here**: ham rows first, then spam rows. The dataset is *not shuffled yet*. We shuffle in `random_split` (cell 24).

### Why this looks simpler than it is

Three lines of pandas hide a lot of work:
* Boolean masking (no need to iterate)
* Random sampling with a seeded RNG
* Concatenation that auto-aligns column types

If you wrote this in plain Python it would be 15-20 lines with manual index tracking.

---

## 6 — Section 6.2: Mapping String Labels to Integers

```python
balanced_df["Label"] = balanced_df["Label"].map({"ham": 0, "spam": 1})
balanced_df
```

### Why convert "ham"/"spam" to 0/1?

The classifier's output head produces logits of shape `(batch, num_classes=2)`. Training requires:

* **`F.cross_entropy(logits, targets)`** where `targets` is an integer tensor of class indices.
* `targets[i]` must be 0 or 1 for a 2-class problem.

PyTorch's `CrossEntropyLoss` doesn't accept string labels. You have to map them to integers first.

### Why 0 = ham and 1 = spam?

It's an arbitrary but conventional choice:
* **0 = negative class** (the "common" / "default" outcome → ham)
* **1 = positive class** (the "thing being detected" → spam)

This convention matters when you later compute precision, recall, F1, ROC-AUC, etc. By convention, "positive class" is what your metrics care about catching.

### `.map(dict)` — element-wise replacement

`Series.map({"ham": 0, "spam": 1})` returns a new Series where every "ham" becomes 0 and every "spam" becomes 1. We assign it back to `balanced_df["Label"]`, overwriting the strings.

After this cell:

| Label | Text |
|-------|------|
| 0 | Go until jurong point, crazy... |
| 1 | Free entry in 2 a wkly comp... |
| ... | ... |

---

## 7 — Section 6.2: random_split — Train / Val / Test Split

```python
def random_split(df, train_frac, validation_frac):
    df = df.sample(frac=1, random_state=123).reset_index(drop=True)   # shuffle
    train_end = int(len(df) * train_frac)
    validation_end = train_end + int(len(df) * validation_frac)

    train_df      = df[:train_end]
    validation_df = df[train_end:validation_end]
    test_df       = df[validation_end:]
    return train_df, validation_df, test_df


train_df, validation_df, test_df = random_split(balanced_df, 0.7, 0.1)

train_df.to_csv("train.csv", index=None)
validation_df.to_csv("validation.csv", index=None)
test_df.to_csv("test.csv", index=None)
```

### `df.sample(frac=1, random_state=123)` — shuffle the whole DataFrame

`sample(frac=1)` returns a random sample with the **same size as the original** — effectively a shuffle. Combined with `reset_index(drop=True)` to renumber rows 0...N-1 so the slice indices work.

This shuffle is essential. Remember `balanced_df` had all ham rows first and all spam rows second. Without shuffling, `df[:train_end]` would be all ham, and `df[train_end:]` would be all spam — useless for training.

### 70/10/20 split

```python
train_frac = 0.70   → 1045 examples
validation_frac = 0.10 → 149 examples
test_frac = 0.20    → 300 examples
```

This is more train-heavy than chapter 7's 85/5/10 split. Why? Because for **classification** with limited data, you want as much training signal as possible. The val set just needs to be big enough for stable measurement during training.

### Saving as CSV instead of pickling

We save to disk and reload from disk in cell 30's `SpamDataset.__init__`. Why round-trip through CSV?

1. **Decouples splitting from dataset loading.** The split happens once (here); the dataset reads the result. If you change the split fractions, you only need to re-run cell 24 — not re-tokenise everything.
2. **Human-readable.** You can open `train.csv` in any text editor and inspect what got split.
3. **Survives notebook restarts.** As long as the CSV files exist, you can re-create `train_dataset` without re-running anything earlier.

---

## 8 — Section 6.3: The SpamDataset Class

```python
import torch
from torch.utils.data import Dataset


class SpamDataset(Dataset):
    def __init__(self, csv_file, tokenizer, max_length=None, pad_token_id=50256):
        self.data = pd.read_csv(csv_file)

        # Pre-tokenise every Text entry
        self.encoded_texts = [
            tokenizer.encode(text) for text in self.data["Text"]
        ]

        # Determine the padding length
        if max_length is None:
            self.max_length = self._longest_encoded_length()
        else:
            self.max_length = max_length
            # Truncate any sequences longer than max_length
            self.encoded_texts = [
                t[:self.max_length] for t in self.encoded_texts
            ]

        # Right-pad shorter sequences with the EOS token (50256)
        self.encoded_texts = [
            t + [pad_token_id] * (self.max_length - len(t))
            for t in self.encoded_texts
        ]

    def __getitem__(self, index):
        encoded = self.encoded_texts[index]
        label = self.data.iloc[index]["Label"]
        return (
            torch.tensor(encoded, dtype=torch.long),
            torch.tensor(label, dtype=torch.long),
        )

    def __len__(self):
        return len(self.data)

    def _longest_encoded_length(self):
        max_length = 0
        for encoded_text in self.encoded_texts:
            encoded_length = len(encoded_text)
            if encoded_length > max_length:
                max_length = encoded_length
        return max_length
```

### Three responsibilities

The dataset class does three things, all in `__init__`:

1. **Read** the CSV.
2. **Tokenise** every text entry to a list of token IDs.
3. **Pad / truncate** every sequence to a uniform length so they can be stacked into rectangular batches.

By the time `__init__` returns, every row in `self.encoded_texts` is the same length — say, 120 tokens. Subsequent calls to `__getitem__` are pure list lookups (very fast).

### Why pre-tokenise in `__init__`?

Same reason as chapter 7's `InstructionDataset`: tokenisation is slow compared to indexing. With ~1000 rows, the one-time cost in `__init__` is fine (~1-2 seconds). After that, every batch is fetched at memory speed.

### Why right-pad with 50256?

GPT-2's BPE tokenizer treats `50256` as the `<|endoftext|>` token. There's no dedicated PAD token in vocabulary, so we recycle EOS as the padding marker. The model sees `<|endoftext|>` as "this sequence is done" — which is the right semantics for padding the right side of a short sequence.

### Why pad RIGHT here, not LEFT?

We're not generating text in this chapter — we're classifying. The classification head will look at the **last token's logits** (cell 68). For that to be meaningful:

* The "last meaningful token" of the actual text needs attention to flow into the rightmost positions.

Right-padding moves the actual text tokens to the *beginning* of the sequence, then puts padding tokens at the end. The causal-attention mechanism means the last position can attend to everything before it — including all the meaningful text. So even though we're using `outputs[:, -1, :]`, the last position has seen the whole sequence.

(Chapter 7's training, by contrast, uses left-padding because generation predicts the next token from the immediate context.)

### Why store the longest length from training in `self.max_length`?

A subtle but important detail. We want all three splits (train, val, test) to have the *same* sequence length. Why? Because:
* During training, the model learns "the classification signal lives at position max_length-1."
* If val and test use a different sequence length, "position max_length-1" means a different relative position — and the model can't generalise.

The pattern in cell 33 is:
```python
train_dataset = SpamDataset(csv_file="train.csv", tokenizer=tokenizer, max_length=None)
# train_dataset.max_length is now whatever the longest training sequence was.

val_dataset = SpamDataset(csv_file="validation.csv", tokenizer=tokenizer, max_length=train_dataset.max_length)
test_dataset = SpamDataset(csv_file="test.csv", tokenizer=tokenizer, max_length=train_dataset.max_length)
```

The training set determines the canonical length; the other two are matched to it.

---

## 9 — Section 6.3: Constructing the Three Datasets

```python
train_dataset = SpamDataset(
    csv_file="train.csv",
    max_length=None,
    tokenizer=tokenizer,
)
print(train_dataset.max_length)
# 120

val_dataset = SpamDataset(
    csv_file="validation.csv",
    max_length=train_dataset.max_length,
    tokenizer=tokenizer,
)
test_dataset = SpamDataset(
    csv_file="test.csv",
    max_length=train_dataset.max_length,
    tokenizer=tokenizer,
)
```

### What `120` means

The longest sequence in the training set was **120 tokens** when BPE-encoded. Every other training sequence gets right-padded with `<|endoftext|>` (50256) until it also has length 120. Val and test sequences are then *also* padded to 120, with anything longer being truncated.

### Why truncation might lose information

If a validation message happens to be 200 tokens long, truncating to 120 chops off the last 80 tokens. The classifier never sees those tokens.

For SMS spam this is fine — spam is usually short and the "spammy" features (FREE!, CLICK HERE, WIN, etc.) cluster at the start of the message. But for longer documents (e.g. email spam) this would be a serious limitation.

### Why not just pad everything to the model's full context (1024)?

Memory. With 1024-token sequences and batch size 8, every forward pass processes 8192 tokens. At 120 tokens, it's 960 tokens — almost 10× cheaper. Sticking to the actual length lets the model train fast on CPU.

---

## 10 — Section 6.3: DataLoaders and Batch Inspection

```python
from torch.utils.data import DataLoader

num_workers = 0
batch_size = 8

torch.manual_seed(123)

train_loader = DataLoader(
    dataset=train_dataset,
    batch_size=batch_size,
    shuffle=True,
    num_workers=num_workers,
    drop_last=True,
)
val_loader = DataLoader(
    dataset=val_dataset, batch_size=batch_size,
    num_workers=num_workers, drop_last=False,
)
test_loader = DataLoader(
    dataset=test_dataset, batch_size=batch_size,
    num_workers=num_workers, drop_last=False,
)
```

### Why no custom `collate_fn`?

Because every sequence is already the same length (120 tokens) thanks to the padding in `SpamDataset.__init__`. PyTorch's default collate function just stacks `(seq, label)` pairs into batched tensors of shape `(batch, 120)` and `(batch,)` — which is exactly what we want.

This is much simpler than chapter 7, where sequences had varying lengths and we needed a custom collate to do dynamic padding.

### Inspecting one batch

```python
for input_batch, target_batch in train_loader:
    pass    # just exhausts the iterator to get the last batch

print("Input batch dimensions:", input_batch.shape)   # torch.Size([8, 120])
print("Label batch dimensions:", target_batch.shape)  # torch.Size([8])
```

The trick `for x in loader: pass` is a Python idiom for "iterate to completion." After the loop, `input_batch` and `target_batch` hold the values from the **last** iteration. (Useful when you don't care about every batch, just the last one.)

### Why batch size 8?

A common default — large enough that gradient estimates are reasonably stable, small enough that even modest GPUs (or just CPU) can handle it comfortably. For this 1000-sample dataset, anything from 4 to 32 would also work fine.

### The three counts

```python
print(f"{len(train_loader)} training batches")        # 130
print(f"{len(val_loader)} validation batches")        # 19
print(f"{len(test_loader)} test batches")             # 38
```

* `len(train_loader)` = `len(train_dataset) // batch_size` = `1045 // 8 = 130` (with `drop_last=True`).
* For val and test, `len()` includes the final partial batch because `drop_last=False`.

---

## 11 — Section 6.4: Loading the Pretrained GPT-2 Small

```python
CHOOSE_MODEL = "gpt2-small (124M)"
INPUT_PROMPT = "Every effort moves"

BASE_CONFIG = {
    "vocab_size": 50257,
    "context_length": 1024,
    "drop_rate": 0.0,
    "qkv_bias": True,
}

model_configs = {
    "gpt2-small (124M)":  {"emb_dim": 768,  "n_layers": 12, "n_heads": 12},
    "gpt2-medium (355M)": {"emb_dim": 1024, "n_layers": 24, "n_heads": 16},
    "gpt2-large (774M)":  {"emb_dim": 1280, "n_layers": 36, "n_heads": 20},
    "gpt2-xl (1558M)":    {"emb_dim": 1600, "n_layers": 48, "n_heads": 25},
}
BASE_CONFIG.update(model_configs[CHOOSE_MODEL])

from gpt_download import download_and_load_gpt2
from previous_chapters import GPTModel, load_weights_into_gpt

model_size = CHOOSE_MODEL.split(" ")[-1].lstrip("(").rstrip(")")
settings, params = download_and_load_gpt2(model_size=model_size, models_dir="gpt2")

model = GPTModel(BASE_CONFIG)
load_weights_into_gpt(model, params)
model.eval()
```

### Why GPT-2 small (124M) for this chapter?

For classification, the model doesn't need to be huge. A 124M-parameter model is more than enough to extract spam vs ham signal. Bigger models would just be slower without meaningfully better accuracy on this task.

(Chapter 7 needed GPT-2 medium because instruction following genuinely benefits from more capacity.)

### Why `drop_rate=0.0` and `qkv_bias=True`?

Same reasons as chapter 7:
* `drop_rate=0.0` — dropout is for regularising large training runs. For a small finetune on a small dataset, dropout adds noise without meaningfully preventing overfitting (other techniques like weight decay are doing that).
* `qkv_bias=True` — OpenAI's actual GPT-2 has biases on the Q/K/V projections. To load their checkpoint we need our `MultiHeadAttention` to also have these biases.

### The model is in `eval()` mode initially

We just loaded the pretrained weights and want to use the model for inference (sanity check in cell 48). `eval()` disables dropout. We'll switch to `train()` inside the training loop later.

### What `load_weights_into_gpt` does

The same function from chapter 5 section 29. Copies OpenAI's TensorFlow-checkpoint weights into our PyTorch model with the right transposition and Q/K/V splitting. After this, `model` has real, capable weights — not random initialisation.

---

## 12 — Section 6.4: Baseline — Can the Pretrained Model Already Classify Spam?

```python
from previous_chapters import generate_text_simple, text_to_token_ids, token_ids_to_text

text_2 = (
    "Is the following text 'spam'? Answer with 'yes' or 'no':"
    " 'You are a winner you have been specially"
    " selected to receive $1000 cash or a $2000 award.'"
)

token_ids = generate_text_simple(
    model=model,
    idx=text_to_token_ids(text_2, tokenizer),
    max_new_tokens=23,
    context_size=BASE_CONFIG["context_length"],
)
print(token_ids_to_text(token_ids, tokenizer))
```

### What we're testing

Can we **prompt** the pretrained GPT-2 to classify the message — without any finetuning? We give it an explicit prompt asking for yes/no, then look at what it generates.

### Why this doesn't work

GPT-2 (pretrained on raw internet text) hasn't been **instruction-tuned**. It's never seen a prompt-response format. So when you ask it "Is this spam? Answer yes or no:", it doesn't recognise the question structure. It just continues whatever pattern it was seeing.

Typical output: gibberish or echoes of the prompt, not a clear "yes" or "no".

### Why this is in the chapter at all

To establish the **baseline**: without finetuning, a pretrained LLM is essentially useless for classification. This motivates the entire rest of the chapter — we need to *change* the model to make it good at this task.

Two ways to make it good:

1. **Replace the output head + finetune** (this chapter's approach).
2. **Instruction-tune the model on (prompt, label) pairs** (chapter 7's approach).

Option 1 is simpler and more efficient *for this task*. Option 2 generalises to any task. Both are valid.

---

## 13 — Section 6.5: Inspecting the Model Architecture

```python
print(model)
```

Expected output (abridged):

```
GPTModel(
  (tok_emb): Embedding(50257, 768)
  (pos_emb): Embedding(1024, 768)
  (drop_emb): Dropout(p=0.0)
  (trf_blocks): Sequential(
    (0-11): 12 x TransformerBlock(...)
  )
  (final_norm): LayerNorm(...)
  (out_head): Linear(in_features=768, out_features=50257, bias=False)
)
```

### Why print the model?

Two reasons:

1. **Verify the structure matches what you built in chapter 4.** If anything's wrong with `previous_chapters.py`, the printed model will look subtly different from what you expected.
2. **Identify exactly which layer to replace.** We want to swap out `out_head` (the final `Linear(768, 50257)`) for a new `Linear(768, 2)`. Printing the model confirms that `out_head` is the correct attribute name and shape.

### The crucial layer to remember

```
(out_head): Linear(in_features=768, out_features=50257, bias=False)
```

This is the **LM head**. It maps each token's 768-dim hidden state to 50257 logits (one per vocabulary entry). For classification, we don't need 50257 outputs — we need 2 (ham, spam). The next few cells make this swap.

### `final_norm` — the last LayerNorm

Right before `out_head` is `final_norm`, a `LayerNorm(768)`. We'll unfreeze this in cell 60 because the normalization parameters might need to adapt to the new classification objective.

---

## 14 — Section 6.5: Freezing the Base Model

```python
for param in model.parameters():
    param.requires_grad = False
```

### What "freezing" means

Every `nn.Parameter` has a boolean `requires_grad` attribute. Set it to `False` and PyTorch:

1. Doesn't compute gradients for that parameter during `.backward()`.
2. Doesn't update it during `optimizer.step()`.

The parameter still **participates in the forward pass** — its values are used to compute outputs — but they never change.

### Why freeze first, then unfreeze later?

It's clearer than the inverse (unfreeze first, freeze the rest). The pattern says:

> "Default: nothing is trainable. Then unfreeze just the parts we want to train."

In this chapter we'll unfreeze:
1. The new `out_head` (after replacing it in cell 57).
2. The last transformer block (`trf_blocks[-1]`).
3. The final LayerNorm.

Everything else — the embeddings, blocks 0-10, etc. — stays frozen at the pretrained values.

### Why only train the last block, not the whole model?

Trade-off between cost and quality:

* **Train everything (full finetune)**: ~5-10 hours on a single GPU. Best quality.
* **Train last block + head only**: ~5 minutes on CPU. ~95% accuracy.

The pretrained features (token embeddings, lower layers' representations) are **already very good** at understanding English text. We don't need to change them. We only need to change the *last few layers* that decide what to output.

This is the core idea behind transfer learning: the early layers learn general features that transfer across tasks; the later layers learn task-specific features.

---

## 15 — Section 6.5: Replacing the Output Head

```python
torch.manual_seed(123)

num_classes = 2
model.out_head = torch.nn.Linear(
    in_features=BASE_CONFIG["emb_dim"],
    out_features=num_classes,
)
```

### What this does

Replace `model.out_head` (the LM head) with a brand-new `Linear(768, 2)`. The new layer has:

* **`in_features=768`** — matches the embedding dim of the rest of the model.
* **`out_features=2`** — one logit per class (ham, spam).
* **Random initial weights** — different from the pretrained LM head, which had 768 × 50257 = 38.6M parameters; the new head has only 768 × 2 + 2 = 1,538 parameters.

### Why is `out_head.requires_grad = True` automatically?

When you assign a brand new `nn.Linear` to `model.out_head`, the new Linear's parameters default to `requires_grad=True`. So even though we just set everything else to `requires_grad=False`, the new head is trainable by default.

That's exactly what we want: the new classification head needs to learn from scratch since it has random init.

### Why `torch.manual_seed(123)` here?

The new Linear layer initialises its weights randomly. Seeding ensures every reader of the notebook gets the same random init, so accuracy numbers match the book's. Without this, your numbers would diverge from the book's by 1-2 percentage points just from initialisation noise.

### How tiny is the new head?

Compare:

| Layer | Parameters |
|-------|-----------|
| Old LM head (Linear 768 → 50257) | ~38.6M |
| New classifier head (Linear 768 → 2) | 1,538 |

We've replaced 38 million parameters with about 1500. The classifier is **20,000× smaller** than the LM head.

This is why classification finetuning is so cheap: the new task-specific component is trivially small.

---

## 16 — Section 6.5: Unfreezing the Last Block and Final LayerNorm

```python
for param in model.trf_blocks[-1].parameters():
    param.requires_grad = True

for param in model.final_norm.parameters():
    param.requires_grad = True
```

### Why unfreeze these two parts?

After freezing everything in cell 55 and replacing only `out_head` in cell 57, the model can technically be trained on classification — but only the tiny 1,538-parameter head would update. Performance would be capped because the upstream features remain fixed.

By unfreezing the **last transformer block** and the **final LayerNorm**, we let the model:

* Slightly reshape its last-block attention/FFN to emphasise features relevant for spam detection.
* Calibrate the final LayerNorm's scale/shift so the input to the new head is well-distributed.

Together these add ~7 million more trainable parameters (one transformer block) plus 1,536 (LayerNorm). Now the model has ~7M trainable parameters out of 124M — about 5.7% trainable.

### Why specifically the last block?

The classification head only sees the output of the last block (passed through `final_norm`). Earlier blocks' outputs go through subsequent blocks before reaching the head, so they have less direct influence on the final logits.

The closer a layer is to the output, the bigger its impact on the loss. Unfreezing layers from the output backward (last block first, then maybe 2nd-to-last, etc.) gives the biggest accuracy gain per unfrozen parameter.

### Trade-off: more unfreezing = better accuracy but slower training

| Unfrozen | Trainable params | Approx training time | Approx final accuracy |
|----------|------------------|----------------------|-----------------------|
| Just `out_head` | 1.5K | < 1 min | ~75% |
| `out_head` + `final_norm` | 3K | < 1 min | ~78% |
| `out_head` + `final_norm` + last block | 7M | ~5 min | ~95% |
| Everything (full finetune) | 124M | ~30 min | ~96% |

The book picks the third option as the sweet spot: dramatically better accuracy than head-only, dramatically faster than full finetune.

---

## 17 — Section 6.5: One Forward Pass Through the Modified Model

```python
inputs = tokenizer.encode("Do you have time")
inputs = torch.tensor(inputs).unsqueeze(0)
print("Inputs:", inputs)
print("Inputs dimensions:", inputs.shape)   # torch.Size([1, 4])

with torch.no_grad():
    outputs = model(inputs)

print("Outputs:\n", outputs)
print("Outputs dimensions:", outputs.shape)  # torch.Size([1, 4, 2])
```

### What changed in the output shape

Before (with the original LM head): output shape was `(1, 4, 50257)` — 50257 logits per position.

After (with our new classifier head): output shape is `(1, 4, 2)` — only 2 logits per position.

The model still outputs **one vector per position** (the per-token forward pass hasn't changed). Only the *size* of each per-position output vector changed: 50257 → 2.

### Why do we still get 4 outputs even though we only want one classification?

Because the model architecture hasn't changed structurally — it still attends to every position and produces a hidden state for every position. The new head is applied to **every** hidden state, producing one (ham, spam) logit pair per position.

We'll use only **the last position's** logits for classification (next section). The other positions' logits are simply ignored during loss calculation.

### Why not pool over positions instead of using only the last?

You could! Common alternatives:

* **Last token** (used here) — `outputs[:, -1, :]`
* **Mean pooling** — `outputs.mean(dim=1)`
* **CLS token** — prepend a `[CLS]` token and use its hidden state (BERT style)
* **Max pooling** — `outputs.max(dim=1)[0]`

For causally-masked language models like GPT-2, **last-token pooling** is the natural choice because:

* The causal mask means the last position has attended to *every* previous position. It has the most context.
* No architectural changes needed (we don't have to insert a CLS token).
* The pretrained model is already set up to "summarise everything seen so far" at each position.

For encoder models (BERT) you'd use the CLS token. For decoder-only (GPT-2), the last token is the standard choice.

---

## 18 — Section 6.6: Why Use the Last Token's Logits

```python
print("Last output token:", outputs[:, -1, :])
# tensor([[-0.7036,  0.5573]])
```

### The intuition

Recall from chapter 3: **causal self-attention** means each position can only attend to positions ≤ itself. So:

* Position 0 sees just itself.
* Position 1 sees positions 0 and 1.
* Position 2 sees 0, 1, 2.
* ...
* The **last position** sees *everything*.

The model's final hidden state at the last position is a learned summary of the entire input sequence. This summary, passed through our new classifier head, produces the classification logits.

### What `outputs[:, -1, :]` means

* **`:`** in dim 0 — all batches (shape `(batch_size,)`)
* **`-1`** in dim 1 — last position (shape `()` — collapsed)
* **`:`** in dim 2 — all class logits (shape `(num_classes,)`)

Result shape: `(batch_size, num_classes)` — one (ham, spam) logit pair per example.

This is exactly the shape `F.cross_entropy(logits, targets)` wants for classification.

### Why not the first token? Or middle?

* **First token** (`outputs[:, 0, :]`) — sees only itself. No context. Useless.
* **Middle tokens** — see some context but not all. Suboptimal.
* **Last token** — sees the whole input. Best summary.

This pattern (last-token logits for classification on decoder models) is standard everywhere — it's how GPT-3.5, Llama, etc. are used for classification tasks too.

---

## 19 — Section 6.6: From Logits to Predicted Class

```python
probas = torch.softmax(outputs[:, -1, :], dim=-1)
label = torch.argmax(probas)
print("Class label:", label.item())
# Class label: 1
```

### Two ways to get the predicted class

**With softmax (shown):**

```python
probas = torch.softmax(logits, dim=-1)     # convert to probabilities
label  = torch.argmax(probas)              # find class with highest probability
```

**Without softmax (also valid):**

```python
label = torch.argmax(logits, dim=-1)
```

### Why both work

Softmax is **monotonic**: a higher logit always means a higher probability. So `argmax(logits)` returns the same index as `argmax(softmax(logits))`. Skipping softmax saves a tiny amount of compute.

The book shows the softmax version first because it makes the **probabilistic interpretation** explicit: the model is saying "I'm X% confident this is ham and Y% confident this is spam."

For accuracy computation (next section), we use the version without softmax — same result, slightly faster.

### What `.item()` does

Extracts a Python scalar from a 0-D tensor. Without it, `label` is `tensor(1)`. With it, `label` is the plain Python int `1`. Useful for printing and comparing.

### Why this prediction is meaningless right now

The new classifier head was randomly initialised in cell 57 — its weights are pure noise. The output `tensor([[-0.7036, 0.5573]])` is essentially random, just leaning slightly toward class 1. Without training, the model's predictions are no better than chance (~50% on a balanced binary classification).

This is the baseline against which we'll measure improvement after training.

---

## 20 — Section 6.6: calc_accuracy_loader

```python
def calc_accuracy_loader(data_loader, model, device, num_batches=None):
    model.eval()
    correct_predictions, num_examples = 0, 0

    if num_batches is None:
        num_batches = len(data_loader)
    else:
        num_batches = min(num_batches, len(data_loader))

    for i, (input_batch, target_batch) in enumerate(data_loader):
        if i < num_batches:
            input_batch, target_batch = input_batch.to(device), target_batch.to(device)

            with torch.no_grad():
                logits = model(input_batch)[:, -1, :]
            predicted_labels = torch.argmax(logits, dim=-1)

            num_examples += predicted_labels.shape[0]
            correct_predictions += (predicted_labels == target_batch).sum().item()
        else:
            break

    return correct_predictions / num_examples
```

### Why an accuracy function is needed

Loss is a measurement of how confident the model is in the right answer (cross-entropy). Accuracy is a measurement of how often the model gets the answer right (0 or 1 per example, averaged).

For classification you want both:
* **Loss** tells you how to improve (loss is what gets backpropagated).
* **Accuracy** tells you how good the model is in human-interpretable terms.

A model can have decreasing loss but flat accuracy if it's becoming "more confident in the wrong answer." That's a useful signal to detect — only accuracy will reveal it.

### The core logic in one block

```python
logits = model(input_batch)[:, -1, :]              # (batch, 2) — last token's logits
predicted_labels = torch.argmax(logits, dim=-1)    # (batch,) — predicted class index
correct = (predicted_labels == target_batch).sum().item()
```

`predicted_labels == target_batch` is element-wise comparison returning a boolean tensor. `.sum()` counts the `True`s. `.item()` extracts a Python int.

### Three details about the function

1. **`model.eval()`** — disables dropout. Even though we set `drop_rate=0.0` in `BASE_CONFIG`, `eval()` is a good habit for deterministic measurement.
2. **`with torch.no_grad()`** — disables autograd. Saves memory and time during measurement.
3. **`num_batches=None`** — runs through the whole loader by default. Pass a smaller number during training to get a fast (slightly noisy) accuracy estimate.

### Why slice `[:, -1, :]` here?

Same reasoning as section 18: the classification signal lives at the last position because that's the only position whose hidden state has attended to the entire input sequence.

---

## 21 — Section 6.6: Baseline Accuracy Before Training

```python
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    major, minor = map(int, torch.__version__.split(".")[:2])
    device = torch.device("mps") if (major, minor) >= (2, 9) else torch.device("cpu")
else:
    device = torch.device("cpu")

model.to(device)

torch.manual_seed(123)

train_accuracy = calc_accuracy_loader(train_loader, model, device, num_batches=10)
val_accuracy   = calc_accuracy_loader(val_loader,   model, device, num_batches=10)
test_accuracy  = calc_accuracy_loader(test_loader,  model, device, num_batches=10)
```

Expected output:

```
Training accuracy: 46.25%
Validation accuracy: 45.00%
Test accuracy: 48.75%
```

### What ~50% means

Random chance on a balanced binary classification is 50%. The new classifier head has random weights, so its predictions are basically a coin flip. The slight variation around 50% is just the randomness of which batches got sampled.

This is the **floor**. Training has to do better than this.

### Why `num_batches=10`?

We only need a rough estimate at this stage — 10 batches × 8 samples = 80 predictions is plenty for confirming "yes, roughly 50%."

The full loaders are bigger (130 train batches, 19 val, 38 test). Running the full loaders would take 10× longer. For a baseline check, the faster approximate measurement is the right trade-off.

---

## 22 — Section 6.6: calc_loss_batch and calc_loss_loader

```python
def calc_loss_batch(input_batch, target_batch, model, device):
    input_batch, target_batch = input_batch.to(device), target_batch.to(device)
    logits = model(input_batch)[:, -1, :]
    loss = torch.nn.functional.cross_entropy(logits, target_batch)
    return loss


# Same as in chapter 5
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

### The key difference from chapter 5

In chapter 5 (pretraining), `calc_loss_batch` used `logits.flatten(0, 1)` and `target.flatten()`:

```python
# Chapter 5 — every position contributes
loss = F.cross_entropy(logits.flatten(0, 1), targets.flatten())
```

Here in chapter 6 (classification), we slice to the last position only:

```python
# Chapter 6 — only last position
logits = model(input_batch)[:, -1, :]   # (batch, num_classes)
loss = F.cross_entropy(logits, target_batch)  # target_batch shape: (batch,)
```

That's it. Two characters of difference (`[:, -1, :]` vs `.flatten(0, 1)`), but a completely different objective.

### Cross-entropy with the right shapes

For 2-class classification with batch size 8:

* `logits` shape: `(8, 2)` — 2 logits per sample.
* `target_batch` shape: `(8,)` — one integer class index per sample.

`F.cross_entropy(logits, targets)`:
1. Internally applies softmax along the class dim.
2. Computes `-log(prob[correct_class])` per sample.
3. Returns the mean over the batch.

### `calc_loss_loader` is unchanged from chapter 5

Iterates the loader, calls `calc_loss_batch` on each, averages. The mechanics are identical — the only thing that changed is what `calc_loss_batch` itself does internally.

This pattern of "small change at the leaf, reuse the higher-level structure" appears throughout the book. The training loop, optimiser, gradient accumulation, etc. all work for any cross-entropy task as long as the loss function returns a scalar.

---

## 23 — Section 6.6: Initial Loss Before Training

```python
with torch.no_grad():
    train_loss = calc_loss_loader(train_loader, model, device, num_batches=5)
    val_loss   = calc_loss_loader(val_loader,   model, device, num_batches=5)
    test_loss  = calc_loss_loader(test_loader,  model, device, num_batches=5)

print(f"Training loss: {train_loss:.3f}")
print(f"Validation loss: {val_loss:.3f}")
print(f"Test loss: {test_loss:.3f}")
```

Expected output:

```
Training loss: 2.453
Validation loss: 2.583
Test loss: 2.322
```

### Why ~2.5?

For a 2-class problem with random predictions, you'd expect loss ≈ `log(2) ≈ 0.693`. We're seeing ~2.5 instead because the **logits aren't centred** — they're random outputs from a newly-initialised Linear layer with arbitrary magnitudes.

After even one training step, this will drop dramatically as the optimiser pulls the random init toward something reasonable. By epoch 1 we'll be at ~0.3, by epoch 5 at ~0.05.

### The same template as chapter 5

This initial-loss measurement, the device selection, `torch.no_grad()`, `num_batches=5` — all identical to chapter 5 section 14. The book is intentionally reusing patterns you've already seen, so you can focus on the *one* thing that's new (classification loss).

---

## 24 — Section 6.7: train_classifier_simple — The Training Loop

```python
def train_classifier_simple(
    model, train_loader, val_loader, optimizer, device, num_epochs,
    eval_freq, eval_iter,
):
    train_losses, val_losses, train_accs, val_accs = [], [], [], []
    examples_seen, global_step = 0, -1

    for epoch in range(num_epochs):
        model.train()
        for input_batch, target_batch in train_loader:
            optimizer.zero_grad()
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            loss.backward()
            optimizer.step()
            examples_seen += input_batch.shape[0]
            global_step += 1

            if global_step % eval_freq == 0:
                train_loss, val_loss = evaluate_model(
                    model, train_loader, val_loader, device, eval_iter)
                train_losses.append(train_loss)
                val_losses.append(val_loss)
                print(f"Ep {epoch+1} (Step {global_step:06d}): "
                      f"Train loss {train_loss:.3f}, Val loss {val_loss:.3f}")

        train_accuracy = calc_accuracy_loader(train_loader, model, device, num_batches=eval_iter)
        val_accuracy   = calc_accuracy_loader(val_loader,   model, device, num_batches=eval_iter)
        print(f"Training accuracy: {train_accuracy*100:.2f}% | "
              f"Validation accuracy: {val_accuracy*100:.2f}%")
        train_accs.append(train_accuracy)
        val_accs.append(val_accuracy)

    return train_losses, val_losses, train_accs, val_accs, examples_seen
```

### Two differences from chapter 5's `train_model_simple`

1. **Tracks accuracy in addition to loss.** At the end of each epoch, computes train_acc and val_acc.
2. **Tracks `examples_seen` instead of `tokens_seen`.** For classification, the unit of progress is "how many texts has the model been trained on" rather than "how many tokens."

Everything else — the loop structure, `optimizer.zero_grad → forward → backward → step`, periodic evaluation, the eval/train mode switching — is identical.

### Why track accuracy per epoch instead of per evaluation step?

Computing accuracy is more expensive than computing loss (you need a final argmax + comparison per sample). Doing it every `eval_freq` steps would slow training noticeably.

Per-epoch is enough resolution: with 5 epochs total, you get 5 accuracy data points, which is plenty to plot a curve.

### `examples_seen` for the secondary x-axis

This will be used by the plotting function in cell 100 to provide a "Examples seen" axis on top of the "Epochs" axis. Useful for comparing different runs with different batch sizes — the X-axis scales meaningfully regardless of batching choices.

### `evaluate_model` (cell 96) is unchanged from chapter 5

```python
def evaluate_model(model, train_loader, val_loader, device, eval_iter):
    model.eval()
    with torch.no_grad():
        train_loss = calc_loss_loader(train_loader, model, device, num_batches=eval_iter)
        val_loss   = calc_loss_loader(val_loader,   model, device, num_batches=eval_iter)
    model.train()
    return train_loss, val_loss
```

Same template, just calling our updated `calc_loss_loader` that computes the last-token-only classification loss.

---

## 25 — Section 6.7: Running the 5-Epoch Training

```python
import time
start_time = time.time()

torch.manual_seed(123)

optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5, weight_decay=0.1)

num_epochs = 5
train_losses, val_losses, train_accs, val_accs, examples_seen = train_classifier_simple(
    model, train_loader, val_loader, optimizer, device,
    num_epochs=num_epochs, eval_freq=50, eval_iter=5,
)

end_time = time.time()
execution_time_minutes = (end_time - start_time) / 60
print(f"Training completed in {execution_time_minutes:.2f} minutes")
```

### The hyperparameters

* **`lr=5e-5`** — small learning rate (same as chapter 7's SFT). Same reasoning: pretrained features are good; we just need a fine adjustment.
* **`weight_decay=0.1`** — strong regularisation. Helps prevent overfitting on the small dataset.
* **`num_epochs=5`** — more epochs than chapter 7 (which used 2). Why? Because the classifier head was randomly initialised (vs chapter 7's pretrained head). It needs more steps to converge.
* **`eval_freq=50`** — evaluate every 50 steps (more frequent than chapter 5 because we have more batches per epoch).
* **`eval_iter=5`** — 5 batches per evaluation for fast measurement.

### `AdamW(model.parameters(), ...)` — why pass all parameters?

We froze 119M of the 124M parameters back in cell 55 (set `requires_grad=False`). PyTorch's optimiser **automatically ignores** parameters with `requires_grad=False` — they're not updated even if you pass them in.

So `model.parameters()` includes all 124M, but the optimiser only actually touches the ~7M that are still trainable. No filtering needed.

### Expected output during training

```
Ep 1 (Step 000000): Train loss 2.453, Val loss 2.583
Ep 1 (Step 000050): Train loss 0.617, Val loss 0.547
Ep 1 (Step 000100): Train loss 0.351, Val loss 0.444
Training accuracy: 70.00% | Validation accuracy: 72.50%
Ep 2 (Step 000150): Train loss 0.270, Val loss 0.378
...
Ep 5 (Step 000600): Train loss 0.034, Val loss 0.181
Training accuracy: 97.50% | Validation accuracy: 97.50%
Training completed in 5.45 minutes
```

The trajectory is dramatic:
* Loss drops from ~2.5 to ~0.03 over 5 epochs.
* Accuracy rises from ~50% baseline to ~97% by epoch 5.

### Why ~5 minutes on CPU is acceptable

124M parameters × forward+backward × ~650 steps could take 30+ minutes on CPU for the full chapter 7 finetune. The classifier version is fast because:

* Only ~7M trainable parameters (vs 124M in full finetune).
* Sequences are short (~120 tokens vs 256+ for instruction tuning).
* Batch size 8 with no accumulation.

Five minutes on a laptop is the target experience the book is going for.

---

## 26 — Section 6.7: Plotting Loss and Accuracy Curves

```python
import matplotlib.pyplot as plt

def plot_values(epochs_seen, examples_seen, train_values, val_values, label="loss"):
    fig, ax1 = plt.subplots(figsize=(5, 3))
    ax1.plot(epochs_seen, train_values, label=f"Training {label}")
    ax1.plot(epochs_seen, val_values, linestyle="-.", label=f"Validation {label}")
    ax1.set_xlabel("Epochs")
    ax1.set_ylabel(label.capitalize())
    ax1.legend()

    ax2 = ax1.twiny()
    ax2.plot(examples_seen, train_values, alpha=0)
    ax2.set_xlabel("Examples seen")

    fig.tight_layout()
    plt.savefig(f"{label}-plot.pdf")
    plt.show()


# Plot losses
epochs_tensor = torch.linspace(0, num_epochs, len(train_losses))
examples_seen_tensor = torch.linspace(0, examples_seen, len(train_losses))
plot_values(epochs_tensor, examples_seen_tensor, train_losses, val_losses)

# Plot accuracies
epochs_tensor = torch.linspace(0, num_epochs, len(train_accs))
examples_seen_tensor = torch.linspace(0, examples_seen, len(train_accs))
plot_values(epochs_tensor, examples_seen_tensor, train_accs, val_accs, label="accuracy")
```

### Why a single `plot_values` function for both loss and accuracy

The plotting code is identical except for the y-axis label. Passing `label="loss"` or `label="accuracy"` as an argument lets us reuse the same function for both — and the saved PDFs get distinct filenames (`loss-plot.pdf` and `accuracy-plot.pdf`).

### What the two plots show

**Loss plot:**
* Train loss drops sharply, plateaus near 0.
* Val loss also drops but plateaus at a slightly higher level (~0.18 vs ~0.03).
* The gap between them is small — no severe overfitting.

**Accuracy plot:**
* Both curves climb from ~50% to ~97% over 5 epochs.
* Val accuracy tracks train accuracy closely.

### Why slight train/val gap is OK here

A modest gap (train 97%, val 97%) suggests the model has learned a *generalisable* pattern, not just memorised the training set. If train accuracy were 99% and val accuracy were 80%, that would indicate overfitting — but we don't see that here.

The reasons we don't overfit despite a small dataset:
1. **Weight decay 0.1** is strong regularisation.
2. **Only 7M trainable parameters** vs 1,045 training examples → 6,700 parameters per example. For a much larger model this would be reckless, but with these numbers it's manageable.
3. **Only 5 epochs** — we stop before the model can memorise specific examples.

### The dual x-axis trick again

`ax2 = ax1.twiny()` creates a second x-axis that shares the y-axis. The invisible `alpha=0` plot aligns its tick marks with the visible one. Result: bottom axis shows epochs (0-5), top axis shows examples seen (0-~5000). Same data, two readings.

This is useful when comparing runs with different batch sizes: "epoch 1" means different amounts of training depending on batch size, but "examples seen" is comparable.

---

## 27 — Section 6.7: Final Accuracy on All Three Sets

```python
train_accuracy = calc_accuracy_loader(train_loader, model, device)
val_accuracy   = calc_accuracy_loader(val_loader,   model, device)
test_accuracy  = calc_accuracy_loader(test_loader,  model, device)

print(f"Training accuracy:   {train_accuracy*100:.2f}%")
print(f"Validation accuracy: {val_accuracy*100:.2f}%")
print(f"Test accuracy:       {test_accuracy*100:.2f}%")
```

Expected output:

```
Training accuracy:   97.21%
Validation accuracy: 97.32%
Test accuracy:       95.67%
```

### Why we measure all three sets

* **Train accuracy** — confirms the model has actually learned. (If this is low, training was broken.)
* **Validation accuracy** — proxy for "how well does the model generalise to data it hasn't seen?" Was tracked throughout training.
* **Test accuracy** — the *honest* final measurement. The test set was never used to make any decisions during training, so this is an unbiased estimate of real-world performance.

### Why test < val < train slightly is normal

The test set is the **strictest** measurement because the model has never seen any test examples — no training, no validation feedback. A small drop (here ~1.5%) is expected. If test accuracy were dramatically worse than val (e.g. 80% vs 97%), that would suggest you'd been "overfitting on the validation set" — making too many decisions based on val performance.

Here the gap is small, suggesting the model genuinely generalises.

### What 95% test accuracy means in context

For SMS spam detection:
* ~95% correct → 5% errors → 1 in 20 messages misclassified.
* On 5,000 messages a day, that's 250 wrong predictions.

Real production spam filters target 99%+ accuracy and use much more sophisticated models. For a learning exercise that took 5 minutes of training on a tiny dataset, 95% is excellent.

### `calc_accuracy_loader` with no `num_batches` argument

```python
calc_accuracy_loader(train_loader, model, device)
# num_batches=None → uses len(data_loader) → processes ALL batches
```

Earlier we passed `num_batches=10` for a fast estimate during baseline measurement. Now we want the *exact* number, so we let it default to processing every batch.

---

## 28 — Section 6.8: classify_review — Single-Text Inference

```python
def classify_review(text, model, tokenizer, device, max_length=None, pad_token_id=50256):
    model.eval()

    # Tokenise
    input_ids = tokenizer.encode(text)

    # Truncate to the smaller of: training max_length or model's context length
    supported_context_length = model.pos_emb.weight.shape[0]
    input_ids = input_ids[:min(max_length, supported_context_length)]

    # Right-pad to max_length
    input_ids += [pad_token_id] * (max_length - len(input_ids))

    # Make it a batch of 1
    input_tensor = torch.tensor(input_ids, device=device).unsqueeze(0)

    # Forward pass — take last token's logits
    with torch.no_grad():
        logits = model(input_tensor)[:, -1, :]
    predicted_label = torch.argmax(logits, dim=-1).item()

    return "spam" if predicted_label == 1 else "not spam"
```

### What this function is for

Demos and downstream applications. The training/eval flow uses `DataLoader`s that batch + pad automatically. But to classify a *single new message* — typed in at the keyboard or fetched from an API — you need this convenience function.

### Why it mirrors `SpamDataset` exactly

Inference must follow the **same preprocessing** as training:
* Tokenise with the same BPE tokenizer.
* Pad to the same `max_length`.
* Right-pad with `<|endoftext|>` (50256).
* Use the last-token logits.

If any of these differ from training, the model's predictions are garbage. The function explicitly takes `max_length` so you can pass `train_dataset.max_length` (= 120) and stay consistent.

### Two-tier truncation

```python
supported_context_length = model.pos_emb.weight.shape[0]   # 1024
input_ids = input_ids[:min(max_length, supported_context_length)]
```

We truncate to whichever is smaller:
* `max_length` — what training used (120). Going beyond would feed positions the model isn't used to seeing.
* `supported_context_length` — what the positional embedding table physically supports (1024). Going beyond would crash with an index-out-of-bounds error.

In practice `max_length` (120) is always smaller for this dataset, so the `min` always picks 120. The check is defensive — if someone trained with `max_length=2000` on a different dataset, this would still cap at 1024.

### Example usage

```python
text_1 = (
    "You are a winner you have been specially"
    " selected to receive $1000 cash or a $2000 award."
)
print(classify_review(text_1, model, tokenizer, device, max_length=train_dataset.max_length))
# spam

text_2 = (
    "Hey, just wanted to check if we're still on"
    " for dinner tonight? Let me know!"
)
print(classify_review(text_2, model, tokenizer, device, max_length=train_dataset.max_length))
# not spam
```

The model correctly identifies the first as spam (FREE! BIG PRIZE!) and the second as ham (casual dinner chat). The classifier works.

---

## 29 — Section 6.8: Saving and Loading the Finetuned Classifier

```python
# Save
torch.save(model.state_dict(), "review_classifier.pth")

# Load (in a new session)
model_state_dict = torch.load("review_classifier.pth", map_location=device, weights_only=True)
model.load_state_dict(model_state_dict)
```

### Why save with `state_dict`?

Same reasons as chapter 5 section 23:
* **Portable** across code refactors (no pickled class).
* **Smaller** than pickling the full model object.
* **Safer** with `weights_only=True` on load.

### File size

For the 124M parameter GPT-2 small in float32, the file is ~500 MB on disk. Most of that is the frozen base model weights — even though they didn't change during finetuning, they're still saved.

This is wasteful but practical: you don't have to keep track of "which weights changed" — you just snapshot the whole model.

### Loading requirements

To `load_state_dict` you need:
1. A `GPTModel` instance with the same `BASE_CONFIG` (especially `qkv_bias=True`).
2. The `model.out_head` already replaced with `nn.Linear(768, 2)` (otherwise the state_dict's `out_head.weight` shape won't match).

The `load-finetuned-model.ipynb` sibling notebook (in the GitHub repo) demonstrates this loading procedure end-to-end.

### Final thoughts on what you built

By the end of chapter 6 you have:

* **A working classification finetune pipeline** for any binary text classification task. Swap out the SMS spam dataset for sentiment, topic, etc. and the same code works.
* **Understanding of which layers to freeze** for transfer learning. The "freeze base, replace head, unfreeze last block + LN" recipe applies to any classifier built on top of any pretrained transformer.
* **The intuition for why the last token's logits are the right summary** of an entire sequence for decoder-only models.

The next chapter (7) generalises this in an important way: instead of replacing the head with a tiny classifier, we keep the LM head and finetune the model to generate **instruction-following text**. Different task, same building blocks.
