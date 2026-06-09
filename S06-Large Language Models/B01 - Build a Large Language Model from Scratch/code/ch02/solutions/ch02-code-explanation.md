# Chapter 2 Code Explanation — Working with Text Data

This document walks through `ch02-working-with-text-data-solution.ipynb` — the chapter 2 exercise notebook from Raschka's *Build a Large Language Model From Scratch*. The chapter answers one question: **how does raw English text become the tensors a transformer can actually consume?** By the end of the notebook you will have built every link in the chain — `Raw Text → Tokens → Token IDs → Sliding-Window Batches → Token Embeddings + Positional Embeddings → Input Embeddings` — almost entirely by hand, before swapping in the production-grade tools (`tiktoken`'s BPE tokenizer, `torch.utils.data.DataLoader`) that real GPT pipelines use.

Four cells in this notebook are **exercises**: `SimpleTokenizerV1`, `SimpleTokenizerV2`, `GPTDatasetV1`, and `create_dataloader_v1` are given to you only as docstrings with `# YOUR CODE HERE / pass`. Each section below explains exactly what the docstring is asking for, then walks through the canonical implementation line by line — the same implementation Raschka's reference solution uses — with a full dry-run against the actual sample text (`the-verdict.txt`, 20,479 characters) so you can check your own output against real numbers.

The section numbers below match the notebook's own `2.x` numbering.

---

## Table of Contents

- [0 — Setup: Packages, Imports, and the Source Text](#0--setup-packages-imports-and-the-source-text)
- [1 — 2.1 Understanding Word Embeddings](#1--21-understanding-word-embeddings)
- [2 — 2.2 Tokenizing Text: From Whitespace Splitting to a Real Regex](#2--22-tokenizing-text-from-whitespace-splitting-to-a-real-regex)
- [3 — 2.3 Converting Tokens into Token IDs: Building the Vocabulary and `SimpleTokenizerV1`](#3--23-converting-tokens-into-token-ids-building-the-vocabulary-and-simpletokenizerv1)
- [4 — 2.4 Adding Special Context Tokens: `<\|unk\|>`, `<\|endoftext\|>`, and `SimpleTokenizerV2`](#4--24-adding-special-context-tokens-unk-endoftext-and-simpletokenizerv2)
- [5 — 2.5 Byte Pair Encoding: Swapping in GPT-2's Real Tokenizer](#5--25-byte-pair-encoding-swapping-in-gpt-2s-real-tokenizer)
- [6 — 2.6 Data Sampling with a Sliding Window: `GPTDatasetV1` and `create_dataloader_v1`](#6--26-data-sampling-with-a-sliding-window-gptdatasetv1-and-create_dataloader_v1)
- [7 — 2.7 Creating Token Embeddings: `nn.Embedding` as a Lookup Table](#7--27-creating-token-embeddings-nnembedding-as-a-lookup-table)
- [8 — 2.8 Encoding Word Positions: Absolute Positional Embeddings](#8--28-encoding-word-positions-absolute-positional-embeddings)
- [9 — Putting It All Together & Where This Leads](#9--putting-it-all-together--where-this-leads)

---

## 0 — Setup: Packages, Imports, and the Source Text

```python
from importlib.metadata import version
print("torch version:", version("torch"))
print("tiktoken version:", version("tiktoken"))
```

Two packages drive this entire chapter:

* **`torch`** — needed from section 2.6 onward, once we move from "lists of integers" to actual tensors and `Dataset`/`DataLoader` objects.
* **`tiktoken`** — OpenAI's byte-pair-encoding (BPE) library, written in Rust with thin Python bindings. It is the *exact* tokenizer GPT-2 (and, with different merge tables, GPT-3/4) uses in production. We only reach for it in section 2.5, after building two hand-rolled tokenizers ourselves so that you understand precisely what `tiktoken` is doing under the hood.

### The source text

```python
with open("the-verdict.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

print("Total number of character:", len(raw_text))
print(raw_text[:99])
```

Output:

```
Total number of character: 20479
I HAD always thought Jack Gisburn rather a cheap genius--though a good fellow enough--so it was no
```

*The Verdict* by Edith Wharton is a public-domain short story — small enough (20,479 characters) to tokenize instantly on a laptop, yet long enough to contain real punctuation, contractions, dashes, and quotation marks: exactly the messy edge cases a tokenizer needs to survive. Every number you'll see for the rest of this document — vocabulary size, token counts, encoded IDs — is derived from this exact file, so if your output matches what's printed here, your code is correct.

> **Why `requests` instead of `urllib`?** The notebook's commented-out block shows the book's original `urllib.request.urlretrieve` approach. The active cell uses `requests` instead, because `urllib` relies on older SSL/TLS protocol negotiation that some VPNs and corporate proxies break, producing `ssl.SSLCertVerificationError`. `requests` handles certificate verification more robustly and is the safer default in 2024+ environments.

---

## 1 — 2.1 Understanding Word Embeddings

There is no code in this section — it's pure setup for everything that follows — but the concept it introduces is the spine of the entire chapter, so it's worth pausing on.

**Summary**: A word (or token) embedding is a mapping from a discrete symbol — a string like `"the"` or a token ID like `988` — into a point in a continuous vector space, e.g. $\mathbb{R}^{256}$.

**The problem it solves**: Neural networks are built entirely out of differentiable arithmetic — matrix multiplications, additions, activation functions. None of that arithmetic has any meaning applied directly to the *string* `"cheap"`. Computers (and the calculus that trains neural nets) only understand numbers. So before a single transformer layer can run, every token must become a vector of real numbers.

**The intuition**: Imagine a giant warehouse where every word in the English language has its own labeled shelf, and on that shelf sits not a single number but a whole *list* of numbers — its "coordinates" in meaning-space. Words that mean similar things (`"king"`, `"queen"`, `"prince"`) end up on nearby shelves; words that mean very different things (`"king"`, `"bicycle"`) end up far apart. Critically, *nobody manually decided where each shelf goes* — the warehouse rearranges itself during training, gradually moving similar words closer together as the model learns from data.

**The math**: Formally, an embedding is a function

$$E : V \to \mathbb{R}^{d}$$

where $V$ is the vocabulary (the finite set of distinct token strings) and $d$ is the embedding dimension. In practice $E$ is implemented as a lookup table — a matrix $W \in \mathbb{R}^{|V| \times d}$ — where row $i$ is the embedding vector for token ID $i$. We will build exactly this table in section 2.7 (`nn.Embedding`).

**Connection forward**: GPT-2 small uses $d = 768$; the GPT-3 family scales up to $d = 12288$. This notebook starts with a toy $d = 3$ in section 2.7 (so you can read every number by eye), then jumps to the realistic $d = 256$ for the rest of the chapter.

---

## 2 — 2.2 Tokenizing Text: From Whitespace Splitting to a Real Regex

**Summary**: Tokenization is the act of chopping a string of characters into the discrete units ("tokens") that will each get their own embedding vector.

**The problem it solves**: The naive approach — `text.split()` — only separates on whitespace. That leaves punctuation glued to words: `"Hello,"` and `"Hello"` would become two completely different vocabulary entries, doubling (or worse) the size of the vocabulary for no semantic gain, and preventing the model from recognizing that they're "the same word."

The notebook builds up the correct regular expression in three visible steps. Each step is a cell you can run and compare against the printed output.

### Step 1 — split on whitespace only

```python
import re
text = "Hello, world. This, is a test."
result = re.split(r'(\s)', text)
print(result)
```
```
['Hello,', ' ', 'world.', ' ', 'This,', ' ', 'is', ' ', 'a', ' ', 'test.']
```

`re.split` with a *capturing group* `(\s)` does something subtle and important: it keeps the delimiter (the whitespace) **in** the result list, interleaved with the surrounding text. This is exactly what we want — we don't want to throw the spaces away yet, we want to inspect and filter them ourselves.

### Step 2 — also split on commas and periods

```python
result = re.split(r'([,.]|\s)', text)
print(result)
```
```
['Hello', ',', '', ' ', 'world', '.', '', ' ', 'This', ',', '', ' ', 'is', ' ', 'a', ' ', 'test', '.', '']
```

Now `,` and `.` are split off as their own tokens — but notice the empty strings `''` that appear between consecutive delimiters (e.g. between the comma and the following space). `re.split` always produces an empty string between two adjacent matches.

### Step 3 — strip whitespace and drop the empties

```python
result = [item for item in result if item.strip()]
print(result)
```
```
['Hello', ',', 'world', '.', 'This', ',', 'is', 'a', 'test', '.']
```

A single list comprehension cleans everything up: `item.strip()` returns `''` (falsy) for both `''` and `' '`, so the filter `if item.strip()` removes both in one shot, while leaving real tokens untouched.

### Step 4 — handle the rest of the punctuation zoo

```python
text = "Hello, world. Is this-- a test?"
result = re.split(r'([,.:;?_!"()\']|--|\s)', text)
result = [item.strip() for item in result if item.strip()]
print(result)
```
```
['Hello', ',', 'world', '.', 'Is', 'this', '--', 'a', 'test', '?']
```

This is the **final regular expression** used for the rest of the chapter:

```
r'([,.:;?_!"()\']|--|\s)'
```

Reading it piece by piece:

| Pattern fragment | Matches |
|---|---|
| `[,.:;?_!"()\']` | any single character from: comma, period, colon, semicolon, question mark, underscore, exclamation mark, double-quote, parentheses, apostrophe |
| `\|--\|` | the two-character double-dash `--` (must come before `\s` in the alternation so it's matched as one unit, not two single dashes) |
| `\|\s` | any whitespace character |

Notice `"this--"` correctly becomes `["this", "--"]` rather than `["this", "-", "-"]` — the `--` alternative is checked as a whole unit before the regex engine falls through to matching individual characters.

### Applying it to the real text

```python
preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', raw_text)
preprocessed = [item.strip() for item in preprocessed if item.strip()]
print(preprocessed[:30])
print(len(preprocessed))
```
```
['I', 'HAD', 'always', 'thought', 'Jack', 'Gisburn', 'rather', 'a', 'cheap', 'genius', '--', 'though', 'a', 'good', 'fellow', 'enough', '--', 'so', 'it', 'was', 'no', ...]
4690
```

*The Verdict* tokenizes into **4,690 tokens**. This single number — `len(preprocessed)` — is the total length of the sequence we'll be working with for the rest of the chapter (until section 2.5, where we switch to the BPE tokenizer and get a *different* token count for the same text).

### Gotchas

* **Whitespace is thrown away by this scheme.** Notice the final list contains no `' '` entries. That's a deliberate simplification for this toy tokenizer — it means `decode(encode(text))` will not perfectly reproduce the original spacing (we'll see this concretely in section 2.3). GPT-2's BPE tokenizer, by contrast, treats the leading space of a word as *part of the token* (e.g. `" world"` vs `"world"` are different tokens), which is one of several reasons it round-trips text exactly.
* **Order matters in regex alternation.** `(--|\s)` must list `--` before `\s` (and the character class) — otherwise `re.split` would greedily match a single `-` first and never see the double-dash as one token.
* **`item.strip()` as a filter is a common Python idiom** worth internalizing: any string that is empty or pure-whitespace is falsy, so `if item.strip()` is a terse way to say "keep this only if it has real content," all without throwing away the *original* (un-stripped) string for tokens that legitimately contain leading/trailing characters you might want — though here we keep the stripped version too, since punctuation tokens never have meaningful surrounding whitespace.

---

## 3 — 2.3 Converting Tokens into Token IDs: Building the Vocabulary and `SimpleTokenizerV1`

**Summary**: Once text is split into token *strings*, each unique string is assigned a unique integer ID — its position in a sorted vocabulary — so that the rest of the pipeline can work with plain integers (which is all `nn.Embedding` and PyTorch tensors understand).

### Building the vocabulary

```python
all_words = sorted(set(preprocessed))
vocab_size = len(all_words)
print(vocab_size)
```
```
1130
```

Two operations are doing all the work here:

1. **`set(preprocessed)`** — collapses the 4,690-token sequence down to its **unique** members. Repeated words like `"the"` (which appears many times) collapse into a single entry.
2. **`sorted(...)`** — puts those unique strings into a deterministic (alphabetical/lexicographic) order. This determinism matters enormously: if you build the vocabulary in a different order each run, the integer assigned to `"the"` would change, and any model trained on one ordering would be useless with another.

The result: **1,130 unique tokens** across the whole story.

```python
vocab = {token: integer for integer, token in enumerate(all_words)}

for i, item in enumerate(vocab.items()):
    print(item)
    if i >= 50:
        break
```

`enumerate(all_words)` pairs each sorted word with its index — `(0, '!')`, `(1, '"')`, `(2, "'")`, `(3, '(')`, `(4, ')')`, … — and the dict comprehension flips that into the lookup table we actually want: `{string: integer}`. Notice that punctuation sorts *before* alphabetic characters in ASCII order, which is why `vocab['!'] == 0`.

A few concrete entries from the real vocabulary (you can verify these against your own run):

| token string | token ID |
|---|---|
| `'!'` | 0 |
| `'"'` | 1 |
| `"'"` | 2 |
| `'It'` | 56 |
| `'Mrs'` | 67 |
| `'know'` | 596 |
| `'painted'` | 746 |
| `'the'` | 988 |

### Exercise: `SimpleTokenizerV1`

The notebook gives you this docstring and asks you to fill in the implementation:

```python
class SimpleTokenizerV1:
    """A naive whitespace-and-punctuation tokenizer.

    __init__(self, vocab):
        Build a forward mapping (string -> id) and an inverse
        mapping (id -> string).

    encode(self, text):
        Split on whitespace/punctuation (same regex as 2.2), strip and
        drop empties, then look up every token in the forward mapping.

    decode(self, ids):
        Look up every id, join with spaces, then clean up spacing
        around punctuation so the text reads naturally.
    """
```

Here is the canonical implementation:

```python
class SimpleTokenizerV1:
    def __init__(self, vocab):
        self.str_to_int = vocab                              # forward: "the" -> 988
        self.int_to_str = {i: s for s, i in vocab.items()}   # inverse: 988 -> "the"

    def encode(self, text):
        preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', text)
        preprocessed = [item.strip() for item in preprocessed if item.strip()]
        ids = [self.str_to_int[s] for s in preprocessed]
        return ids

    def decode(self, ids):
        text = " ".join([self.int_to_str[i] for i in ids])
        # Remove the space that " ".join inserted before punctuation
        text = re.sub(r'\s+([,.?!"()\'])', r'\1', text)
        return text
```

Three things to notice about the design:

1. **Two dictionaries, not one.** `encode` needs *string → integer*; `decode` needs *integer → string*. Rather than searching `str_to_int` backwards (an $O(n)$ scan per lookup), we precompute the inverse mapping once in `__init__` — an $O(1)$ lookup forever after. This "build both directions up front" pattern shows up constantly in tokenizer code.
2. **`encode` re-runs the exact regex from section 2.2.** The tokenizer doesn't just *store* a vocabulary — it *owns* the splitting logic that produced it, because `encode` must turn arbitrary new text into the same kind of tokens the vocabulary was built from.
3. **`decode` has to undo `" ".join`'s side effect.** Joining tokens with `" "` puts a space in front of *everything*, including punctuation — producing `"painted , you"` instead of `"painted, you"`. The regex `re.sub(r'\s+([,.?!"()\'])', r'\1', text)` finds any run of whitespace **immediately followed by** one of the punctuation characters, and replaces the whole match with just the punctuation (the captured group `\1`), deleting the space. This is a "clean up after yourself" step — a recurring pattern any time you reconstruct text from tokens.

### Dry run

```python
tokenizer = SimpleTokenizerV1(vocab)

text = """"It's the last he painted, you know,"
           Mrs. Gisburn said with pardonable pride."""
ids = tokenizer.encode(text)
print(ids)
```
```
[1, 56, 2, 850, 988, 602, 533, 746, 5, 1126, 596, 5, 1, 67, 7, 38, 851, 1108, 754, 793, 7]
```

Let's trace the first few IDs by hand using the regex from section 2.2:

```
Step 1 — regex split + clean:
  '"It's the last he painted, you know," ...'
    -> ['"', 'It', "'", 's', 'the', 'last', 'he', 'painted', ',', 'you', 'know', ',', '"', ...]

Step 2 — dictionary lookup (string -> id), using the table above:
  '"'      -> 1
  'It'     -> 56
  "'"      -> 2
  's'      -> 850
  'the'    -> 988
  'last'   -> 602
  'he'     -> 533
  'painted'-> 746
  ','      -> 5
  ...
```

```python
print(tokenizer.decode(ids))
```
```
"It' s the last he painted, you know," Mrs. Gisburn said with pardonable pride.
```

### Gotcha — `"It' s"` instead of `"It's"`

Look closely at the decoded output: it reads **`It' s`**, with a space *after* the apostrophe rather than before it (or nowhere at all). This is not a bug in the cleanup regex — it's an honest reflection of how the *encode* step destroyed information.

`"It's"` was tokenized into three separate pieces: `'It'`, `"'"`, `'s'`. When `decode` rejoins them with `" "`, it produces `"It ' s"`. The cleanup regex `\s+([,.?!"()\'])` only strips whitespace that comes **before** a punctuation mark — so it removes the space before `'` (giving `"It' s"`), but has no rule for removing the space *after* an apostrophe that's acting as a contraction. The naive tokenizer simply has no concept of "this apostrophe glues the previous and next token together" — it treats `'` exactly like a comma or a period.

This is precisely the kind of lossy round-trip that motivates moving to a smarter tokenizer later (BPE in section 2.5 treats `"'s"` as part of a single subword unit and reproduces contractions perfectly).

---

## 4 — 2.4 Adding Special Context Tokens: `<|unk|>`, `<|endoftext|>`, and `SimpleTokenizerV2`

**The problem it solves**: `SimpleTokenizerV1.encode` does a *hard* dictionary lookup — `self.str_to_int[s]`. The moment it meets a word that wasn't in the original 1,130-token vocabulary, Python raises a `KeyError` and the whole pipeline crashes.

```python
tokenizer = SimpleTokenizerV1(vocab)
text = "Hello, do you like tea. Is this-- a test?"
tokenizer.encode(text)
```
```
KeyError: 'Hello'
```

`"Hello"` never appears anywhere in *The Verdict*, so it has no entry in `vocab`. Real-world text will always contain words a fixed, finite training-set vocabulary has never seen — proper nouns, neologisms, typos, foreign words. A production tokenizer must have *some* answer for "what do I do with a word I don't recognize?"

### The four classic special tokens

| Token | Meaning | Used by GPT-2? |
|---|---|---|
| `[BOS]` (beginning of sequence) | marks where a text begins | No |
| `[EOS]` (end of sequence) | marks where a text ends; used to glue independent documents together | No (uses `<\|endoftext\|>` for this role) |
| `[PAD]` (padding) | pads short sequences up to a uniform length for batching | No (also reuses `<\|endoftext\|>`, since attention masking makes the actual pad value irrelevant) |
| `[UNK]` (unknown) | stands in for any out-of-vocabulary word | No (BPE makes `[UNK]` unnecessary — see section 2.5) |

GPT-2 deliberately minimizes its special-token surface area to exactly **one** symbol, `<|endoftext|>`, reused for three different jobs (end-of-sequence, document separator, and padding). This notebook still introduces `<|unk|>` here because `SimpleTokenizerV2` is a *word-level* tokenizer — and word-level tokenizers genuinely need an escape hatch for unseen words. (BPE, as you'll see in the very next section, sidesteps the entire problem by never having an "unseen word" in the first place.)

### Extending the vocabulary

```python
all_tokens = sorted(list(set(preprocessed)))
all_tokens.extend(["<|endoftext|>", "<|unk|>"])
vocab = {token: integer for integer, token in enumerate(all_tokens)}

print(len(vocab.items()))
for i, item in enumerate(list(vocab.items())[-5:]):
    print(item)
```
```
1132
('younger', 1127)
('your', 1128)
('yourself', 1129)
('<|endoftext|>', 1130)
('<|unk|>', 1131)
```

Two new entries are appended **after** the sort, so they land at the highest IDs (`1130` and `1131`), growing the vocabulary from 1,130 to **1,132** tokens.

### Exercise: `SimpleTokenizerV2`

```python
class SimpleTokenizerV2:
    """Same as SimpleTokenizerV1 but handles unknown tokens via "<|unk|>",
    and supports "<|endoftext|>" at decode time.
    """
```

Canonical implementation — it differs from V1 by exactly one line, inserted between splitting and lookup:

```python
class SimpleTokenizerV2:
    def __init__(self, vocab):
        self.str_to_int = vocab
        self.int_to_str = {i: s for s, i in vocab.items()}

    def encode(self, text):
        preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', text)
        preprocessed = [item.strip() for item in preprocessed if item.strip()]
        # <-- the one new line: silently replace anything unknown
        preprocessed = [
            item if item in self.str_to_int else "<|unk|>"
            for item in preprocessed
        ]
        ids = [self.str_to_int[s] for s in preprocessed]
        return ids

    def decode(self, ids):
        text = " ".join([self.int_to_str[i] for i in ids])
        text = re.sub(r'\s+([,.?!"()\'])', r'\1', text)
        return text
```

The substitution list-comprehension is a **sanitization pass**: it walks the freshly split tokens and swaps out anything the vocabulary doesn't recognize for the literal string `"<|unk|>"` *before* the dictionary lookup ever runs — guaranteeing the lookup can never fail with a `KeyError`.

### Dry run

```python
tokenizer = SimpleTokenizerV2(vocab)

text1 = "Hello, do you like tea?"
text2 = "In the sunlit terraces of the palace."
text = " <|endoftext|> ".join((text1, text2))
print(text)
```
```
Hello, do you like tea? <|endoftext|> In the sunlit terraces of the palace.
```

```python
print(tokenizer.encode(text))
```
```
[1131, 5, 355, 1126, 628, 975, 10, 1130, 55, 988, 956, 984, 722, 988, 1131, 7]
```

```python
print(tokenizer.decode(tokenizer.encode(text)))
```
```
<|unk|> , do you like tea? <|endoftext|> In the sunlit terraces of the <|unk|> .
```

### Gotcha — two *different* unknown words become the *same* token

Trace what happened to the IDs `1131` in the output above: the **first** one stands in for `"Hello"`, and the **second** stands in for `"palace"`. Both words are absent from the original 1,130-word vocabulary, and both get mapped to the exact same integer, `1131` — the ID of `<|unk|>`.

This is the fundamental weakness of the `[UNK]`-token strategy laid bare in a single dry run: **`"Hello"` and `"palace"` are now indistinguishable to the model.** All the information that made them different words — their spelling, their meaning, their subword structure — has been collapsed into one undifferentiated "I don't know" symbol. A model trained this way can never learn anything about either word; at best it learns "something unfamiliar happened here."

This is *exactly* the gap that byte-pair encoding fills — which is why it's the very next section.

---

## 5 — 2.5 Byte Pair Encoding: Swapping in GPT-2's Real Tokenizer

**Summary**: Byte Pair Encoding (BPE) is a *subword* tokenization algorithm that builds its vocabulary not from whole words, but from the most frequently occurring pairs of characters (and character-sequences), merged iteratively until a target vocabulary size is reached.

**The problem it solves**: Word-level tokenizers face an impossible trade-off — a vocabulary large enough to cover every word in a language is enormous (hundreds of thousands of entries, mostly rare), yet even the largest realistic vocabulary will still meet unseen words at inference time (the `<|unk|>` problem from section 2.4). BPE escapes the trade-off entirely: **any** string, no matter how exotic, can always be represented as *some* sequence of subword pieces from a modest, fixed vocabulary (GPT-2 uses 50,257 entries) — falling back, in the absolute worst case, all the way down to individual bytes. There is no such thing as an "unknown" string for a byte-level BPE tokenizer.

**The intuition**: Imagine you only had a small set of LEGO brick shapes, but you needed to build models of arbitrarily complex objects. A word-level vocabulary is like having one giant, custom-molded brick for every possible object — efficient if you happen to have exactly the brick you need, useless otherwise. BPE is like having a smart, modest set of brick shapes (`some`, `un`, `known`, `Place`, …) where *any* shape can be assembled by snapping a few of them together. `"unfamiliarword"` becomes `["unfam", "iliar", "word"]` (or some similar split, depending on the trained merges) instead of crashing the system or collapsing into `<|unk|>`.

```python
import importlib
import tiktoken

print("tiktoken version:", importlib.metadata.version("tiktoken"))
tokenizer = tiktoken.get_encoding("gpt2")
```

`tiktoken.get_encoding("gpt2")` loads OpenAI's pretrained GPT-2 BPE merge table — the *exact same* tokenizer config GPT-2 was trained with — implemented in Rust for speed (the notebook's bonus directory `02_bonus_bytepair-encoder` shows it running roughly 5× faster than a pure-Python reimplementation on this same sample text).

### Dry run

```python
text = (
    "Hello, do you like tea? <|endoftext|> In the sunlit terraces"
    "of someunknownPlace."
)
integers = tokenizer.encode(text, allowed_special={"<|endoftext|>"})
print(integers)
```
```
[15496, 11, 466, 345, 588, 8887, 30, 220, 50256, 554, 262, 4252, 18250, 8812, 2114, 1659, 617, 34680, 27271, 13]
```

```python
strings = tokenizer.decode(integers)
print(strings)
```
```
Hello, do you like tea? <|endoftext|> In the sunlit terracesof someunknownPlace.
```

Two details worth slowing down on:

* **`allowed_special={"<|endoftext|>"}`** — by default, `tiktoken` treats `<|...|>`-shaped strings in your input as suspicious (potential prompt-injection of "special" control tokens) and refuses to encode them. Passing `allowed_special` is how you explicitly whitelist `<|endoftext|>` as a token GPT-2's vocabulary genuinely contains — its real ID is `50256`, visible right there in the middle of the `integers` list.
* **The decoded string round-trips *exactly*, including the missing space** between `"terraces"` and `"of"` (the original text really did have `"terraces" + "of"` glued together by string concatenation in the source cell — and BPE faithfully preserves that quirk rather than "fixing" it the way the naive `SimpleTokenizerV1` mangled spacing). This exactness is a direct consequence of BPE encoding *raw bytes* — including spaces — as part of its tokens, rather than throwing whitespace away the way our regex-based tokenizers did.

### What happened to `"someunknownPlace"`?

This compound, made-up word never appeared anywhere in GPT-2's training data, yet it encoded and decoded perfectly. Peeking at the individual subword pieces:

```python
[tokenizer.decode([t]) for t in tokenizer.encode("someunknownPlace")]
# ['some', 'unknown', 'Place']
```

BPE split the nonsense compound into three real, meaningful subwords it *does* recognize — `"some"`, `"unknown"`, `"Place"` — and represented the whole thing as their concatenation. No `<|unk|>`, no information loss, no crash. *This* is the payoff for the algorithmic complexity of BPE: it converts the brittle "did I see this exact word during training?" question into the much more answerable "can I assemble this string from pieces I've seen?" — and the answer to the second question is always yes, all the way down to single bytes if necessary.

> If you want to push this further yourself, try `tokenizer.encode("Akwirw ier")` — a string of complete nonsense — and decode each resulting ID individually with `tokenizer.decode([id])`. That experiment (and its full write-up) lives in `exercise-solutions.ipynb`, referenced at the end of this notebook.

---

## 6 — 2.6 Data Sampling with a Sliding Window: `GPTDatasetV1` and `create_dataloader_v1`

This is the section where everything becomes "real" — we go from "a long list of integers" to "the actual `(input, target)` tensor pairs a GPT model trains on," wrapped in PyTorch's official `Dataset`/`DataLoader` machinery.

### The next-token-prediction setup

**The intuition**: An LLM is trained to do exactly one thing — given some tokens, predict the *next* one. So for any chunk of text, the natural "label" for token at position $i$ is simply the token at position $i+1$. The **target sequence** is just the **input sequence shifted one position to the right**.

```python
with open("the-verdict.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

enc_text = tokenizer.encode(raw_text)
print(len(enc_text))
```
```
5145
```

Notice this number — **5,145** — is *different* from the 4,690 we got with the regex tokenizer in section 2.2. That's not a discrepancy to worry about; it's a direct, visible consequence of switching tokenization schemes. BPE's subword vocabulary slices the same raw text into a different number of pieces than a whole-word vocabulary does (sometimes more, when a word gets split into several subwords; sometimes fewer, when whitespace gets folded into adjacent tokens rather than becoming its own token). The token *count* is a property of the *tokenizer*, not just the text.

```python
enc_sample = enc_text[50:]    # skip the first 50 tokens, for a more interesting sample

context_size = 4
x = enc_sample[:context_size]
y = enc_sample[1:context_size + 1]
print(f"x: {x}")
print(f"y:      {y}")
```
```
x: [290, 4920, 2241, 287]
y:      [4920, 2241, 287, 257]
```

Lay the two lists side by side and the "shift by one" relationship is immediate:

```
x = [290, 4920, 2241, 287]
y =      [4920, 2241, 287, 257]
```

Every element of `y` is the element of `x` one position to its right, plus one new token (`257`) tacked on the end. `y[i] == x[i+1]` for `i` in range — this single shift relation is the entire supervisory signal for pretraining a language model.

```python
for i in range(1, context_size + 1):
    context = enc_sample[:i]
    desired = enc_sample[i]
    print(context, "---->", desired)
```
```
[290] ----> 4920
[290, 4920] ----> 2241
[290, 4920, 2241] ----> 287
[290, 4920, 2241, 287] ----> 257
```

Decoding both sides makes the prediction task viscerally clear:

```python
for i in range(1, context_size + 1):
    context = enc_sample[:i]
    desired = enc_sample[i]
    print(tokenizer.decode(context), "---->", tokenizer.decode([desired]))
```
```
 and ---->  established
 and established ---->  himself
 and established himself ---->  in
 and established himself in ---->  a
```

Read this as four separate training examples carved out of one sentence: *"given the words `' and'`, predict `' established'`. Given `' and established'`, predict `' himself'`."* …and so on. This is the literal mechanics of "next-token prediction" — every sub-prefix of a sentence is itself a training example, with the very next token as its label. (Notice, too, that the decoded strings carry their *leading* space — `" established"`, not `"established"` — which is exactly the BPE behavior mentioned in the previous section's gotcha: GPT-2's vocabulary encodes whitespace as part of the token.)

### The sliding-window picture

$$\text{windows produced} = \left\lfloor \frac{N - L}{S} \right\rfloor + 1$$

where $N$ is the total token count, $L$ is `max_length` (the context window size), and $S$ is `stride` (how far the window slides each step). When $S = L$, consecutive windows are perfectly back-to-back with **zero overlap**; when $S < L$, windows overlap (more training examples from the same text, at the cost of some redundancy and a higher risk of overfitting to repeated spans); when $S > L$, you'd be skipping tokens entirely (rarely desirable).

### Exercise: `GPTDatasetV1`

```python
class GPTDatasetV1(Dataset):
    """A sliding-window dataset for next-token prediction.

    __init__(self, txt, tokenizer, max_length, stride):
        Tokenize the whole text once. Slide a window of length
        max_length across the token IDs, stepping by `stride`. At each
        position, the window itself is the input chunk, and the window
        shifted right by one position is the target chunk.

    __len__ / __getitem__:
        Standard PyTorch Dataset contract.
    """
```

Canonical implementation:

```python
from torch.utils.data import Dataset, DataLoader


class GPTDatasetV1(Dataset):
    def __init__(self, txt, tokenizer, max_length, stride):
        self.input_ids = []
        self.target_ids = []

        # Tokenize the ENTIRE text once -- not per-window. Much cheaper.
        token_ids = tokenizer.encode(txt, allowed_special={"<|endoftext|>"})

        # Slide a window of length max_length, stepping by `stride` each time
        for i in range(0, len(token_ids) - max_length, stride):
            input_chunk = token_ids[i:i + max_length]
            target_chunk = token_ids[i + 1: i + max_length + 1]
            self.input_ids.append(torch.tensor(input_chunk))
            self.target_ids.append(torch.tensor(target_chunk))

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        return self.input_ids[idx], self.target_ids[idx]
```

Walking through the design decisions:

1. **Tokenize once, in `__init__`, not in `__getitem__`.** BPE encoding the full 20,479-character story takes a fraction of a second; doing it again every time `__getitem__` is called (which happens once per sample, every epoch) would waste enormous amounts of time for no benefit. This "do the expensive work once, up front, and cache the results" pattern is the single most important performance habit in dataset design.
2. **`for i in range(0, len(token_ids) - max_length, stride)`** is the entire sliding-window mechanism in one line. `i` is the starting index of each window; the loop stops *before* `i` would let `input_chunk` run past the end of `token_ids` (hence `- max_length` in the range's stop value), guaranteeing every chunk is exactly `max_length` long.
3. **`input_chunk = token_ids[i : i+max_length]`** and **`target_chunk = token_ids[i+1 : i+max_length+1]`** are two windows of *identical length*, offset by exactly one position — the tensor-level expression of the `x`/`y` shift you just saw printed above.
4. **`torch.tensor(...)` happens at storage time**, so `__getitem__` does zero work beyond an array index — the fastest possible implementation of the `Dataset` contract.

### Exercise: `create_dataloader_v1`

```python
def create_dataloader_v1(txt, batch_size=4, max_length=256,
                         stride=128, shuffle=True, drop_last=True,
                         num_workers=0):
    """Instantiate the GPT-2 BPE tokenizer, wrap txt in a GPTDatasetV1,
    wrap that in a DataLoader, and return it."""
```

Canonical implementation — three lines, each wrapping the previous layer:

```python
def create_dataloader_v1(txt, batch_size=4, max_length=256,
                         stride=128, shuffle=True, drop_last=True,
                         num_workers=0):
    tokenizer = tiktoken.get_encoding("gpt2")
    dataset = GPTDatasetV1(txt, tokenizer, max_length, stride)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        drop_last=drop_last,
        num_workers=num_workers,
    )
    return dataloader
```

This function is a **factory** — it hides three layers of construction (tokenizer → dataset → dataloader) behind a single call, exposing only the knobs you actually want to tune from the outside (`batch_size`, `max_length`, `stride`, …). This is the same "two-class contract" (`Dataset` defines *how to get one sample*; `DataLoader` defines *how to batch/shuffle/parallelize*) introduced in chapter 1 — `create_dataloader_v1` is simply the glue that assembles both halves correctly every time, so you never have to remember the wiring yourself.

### Dry run #1 — `batch_size=1`, `max_length=4`, `stride=1`

```python
dataloader = create_dataloader_v1(
    raw_text, batch_size=1, max_length=4, stride=1, shuffle=False
)
data_iter = iter(dataloader)
first_batch = next(data_iter)
print(first_batch)
```
```
[tensor([[  40,  367, 2885, 1464]]), tensor([[ 367, 2885, 1464, 1807]])]
```

```python
second_batch = next(data_iter)
print(second_batch)
```
```
[tensor([[ 367, 2885, 1464, 1807]]), tensor([[2885, 1464, 1807, 3619]])]
```

With `stride=1`, each successive window slides over by exactly one token — so the **input** of the second batch (`[367, 2885, 1464, 1807]`) is *literally identical* to the **target** of the first batch. This maximal overlap produces the most possible training windows from a fixed text (at the cost of heavy redundancy between adjacent samples — most of each window's content was already seen in the previous one).

### Dry run #2 — `batch_size=8`, `max_length=4`, `stride=4` (no overlap)

```python
dataloader = create_dataloader_v1(raw_text, batch_size=8, max_length=4, stride=4, shuffle=False)
data_iter = iter(dataloader)
inputs, targets = next(data_iter)
print("Inputs:\n", inputs)
print("\nTargets:\n", targets)
```
```
Inputs:
 tensor([[   40,   367,  2885,  1464],
         [ 1807,  3619,   402,   271],
         [10899,  2138,   257,  7026],
         [15632,   438,  2016,   257],
         [  922,  5891,  1576,   438],
         [  568,   340,   373,   645],
         [ 1049,  5975,   284,   502],
         [  284,  3285,   326,    11]])

Targets:
 tensor([[  367,  2885,  1464,  1807],
         [ 3619,   402,   271, 10899],
         [ 2138,   257,  7026, 15632],
         [  438,  2016,   257,   922],
         [ 5891,  1576,   438,   568],
         [  340,   373,   645,  1049],
         [ 5975,   284,   502,   284],
         [ 3285,   326,    11,   287]])
```

Setting `stride == max_length` makes consecutive windows **butt up against each other with zero overlap** — row 2 of `Inputs` (`[1807, 3619, 402, 271]`) starts exactly where row 1 ends, with no repeated tokens. The notebook's comment explains exactly why this matters:

> *"we increase the stride here so that we don't have overlaps between the batches, since more overlap could lead to increased overfitting"*

If every window shared most of its tokens with its neighbors (as in dry run #1, with `stride=1`), the model would effectively see the same short spans of text dozens of times per epoch — a recipe for memorizing *The Verdict* rather than learning general language patterns. Setting `stride = max_length` is the simplest way to guarantee each token contributes to exactly one training example per pass over the data.

Also notice the shape: `inputs.shape == (8, 4)` — `batch_size=8` rows, each `max_length=4` tokens long. This `(batch, sequence_length)` shape is the **canonical input shape** for everything downstream, starting with the embedding layer in the very next section.

### Extra Notes — Stride vs Target Shift: Two Separate Axes

A natural point of confusion when first reading the dry run output: *the targets only shift by 1 position even though `stride=4` — why doesn't the stride affect the shift?* The answer is that **stride and the target shift are completely independent mechanisms controlling two different axes**.

**Axis 1 — Input vs Target (always shifts by 1, hardcoded in `GPTDatasetV1`)**

This is the definition of next-token prediction. For every position in the input, the model's job is to predict the *next* token — so the target window is always the input window shifted right by exactly 1 position. This is wired directly into `GPTDatasetV1.__init__`:

```python
input_chunk  = token_ids[i     : i + max_length]
target_chunk = token_ids[i + 1 : i + max_length + 1]
```

The `+1` offset is always 1, regardless of stride. It never changes.

**Axis 2 — Stride controls where the next sample (row) starts**

`stride` is the step size of the outer loop — it controls how far the starting index `i` advances from one sample to the next. With `stride=4` and `max_length=4`, look at what happens to the starting index across the 8 rows of the batch:

```
Token stream: pos 0  1     2     3     4     5    6    7    8      9    10   ...
              [40,  367,  2885, 1464, 1807, 3619, 402, 271, 10899, 2138, 257, ...]

Row 0 input starts at pos 0:  [pos 0..3]  = [40,   367,  2885, 1464]
Row 0 target:                 [pos 1..4]  = [367,  2885, 1464, 1807]   ← always +1

Row 1 input starts at pos 4:  [pos 4..7]  = [1807, 3619, 402,  271]   ← jumped by stride=4
Row 1 target:                 [pos 5..8]  = [3619, 402,  271, 10899]  ← always +1

Row 2 input starts at pos 8:  [pos 8..11] = [10899, 2138, 257, 7026]
Row 2 target:                 [pos 9..12] = [2138, 257, 7026, 15632]
```

The stride jump of 4 happens **between rows** (between samples). The +1 shift happens **within each row** (between input and target). They operate on completely different dimensions of the output tensor.

**Summary table**

| Parameter | Controls | Direction in output |
|---|---|---|
| `stride` | Gap between consecutive input windows (row starts) | Vertical — between rows of the batch |
| Target shift (+1) | Offset between input and target for next-token prediction | Horizontal — within every row |

**When `stride = max_length = 4` (this dry run):** zero overlap between rows — every token contributes to exactly one input window per pass over the data. When `stride = 1` (dry run #1): maximum overlap — the input of row $n+1$ is almost entirely the same tokens as the input of row $n$, shifted one slot left.

### `num_workers` — a quick callback

As covered in the chapter 1 notes, `num_workers > 0` spins up subprocesses to prefetch batches in parallel, keeping the GPU fed. For a 5,145-token toy dataset like this one, the multiprocessing overhead dwarfs any benefit — `num_workers=0` (the notebook's default here) is actually faster. For real pretraining corpora (millions to billions of tokens), `num_workers=4` or higher becomes essential.

---

## 7 — 2.7 Creating Token Embeddings: `nn.Embedding` as a Lookup Table

**The problem it solves**: The dataloader now hands us `(batch, seq_len)` tensors of *integers* — token IDs like `40`, `367`, `2885`. But, as section 2.1 explained, a transformer needs *vectors*, not raw integer indices. `nn.Embedding` is the layer that performs that conversion.

```python
input_ids = torch.tensor([2, 3, 5, 1])

vocab_size = 6
output_dim = 3

torch.manual_seed(123)
embedding_layer = torch.nn.Embedding(vocab_size, output_dim)
print(embedding_layer.weight)
```
```
Parameter containing:
tensor([[ 0.3374, -0.1778, -0.1690],
        [ 0.9178,  1.5810,  1.3010],
        [ 1.2753, -0.2010, -0.1606],
        [-0.4015,  0.9666, -1.1481],
        [-1.1589,  0.3255, -0.6315],
        [-2.8400, -0.7849, -1.4096]], requires_grad=True)
```

`nn.Embedding(6, 3)` allocates a $(6 \times 3)$ weight matrix — 6 rows because `vocab_size=6` (token IDs 0 through 5 are all the embedding layer needs to handle), 3 columns because `output_dim=3`. Every row is a learnable vector, randomly initialized (here, seeded with `torch.manual_seed(123)` so your numbers match the book's exactly) and refined by gradient descent during training, exactly as section 2.1 promised.

### The lookup, traced by hand

```python
print(embedding_layer(torch.tensor([3])))
```
```
tensor([[-0.4015,  0.9666, -1.1481]], grad_fn=<EmbeddingBackward0>)
```

**Layer 1 — Intuition**: passing token ID `3` into the embedding layer is *exactly* like saying "hand me row #3 of the lookup table" — nothing more. There's no arithmetic, no transformation, just a direct copy-paste of one row.

**Layer 2 — Math**: this is precisely what the equivalence to one-hot encoding plus matrix multiplication makes formal. Let $\mathbf{e}_3 = [0, 0, 0, 1, 0, 0]$ be the one-hot vector for index 3, and $W \in \mathbb{R}^{6 \times 3}$ the weight matrix above. Then:

$$\mathbf{e}_3^{\top} W = \text{row 3 of } W$$

`nn.Embedding` is simply a fast, memory-efficient way of computing $\mathbf{e}^{\top}W$ without ever materializing the (mostly-zero) one-hot vector — a direct row-index instead of a full matrix multiply.

**Layer 3 — Dry run**: count down from row 0 of the printed weight matrix: row 0 is `[0.3374, -0.1778, -0.1690]`, row 1 is `[0.9178, 1.5810, 1.3010]`, row 2 is `[1.2753, -0.2010, -0.1606]`, and **row 3** is `[-0.4015, 0.9666, -1.1481]` — which is *exactly* what `embedding_layer(torch.tensor([3]))` printed. No computation happened; the layer simply walked down to the fourth shelf in the warehouse and handed back what was sitting there.

### Embedding a whole batch at once

```python
print(embedding_layer(input_ids))
```
```
tensor([[ 1.2753, -0.2010, -0.1606],
        [-0.4015,  0.9666, -1.1481],
        [-2.8400, -0.7849, -1.4096],
        [ 0.9178,  1.5810,  1.3010]], grad_fn=<EmbeddingBackward0>)
```

`input_ids = torch.tensor([2, 3, 5, 1])`. The output is simply rows `2`, `3`, `5`, and `1` of the weight matrix, stacked in that order — a $(4, 3)$ tensor. Crucially, **row 1 of `input_ids` is `3`, and the second row of this output is identical to what we got from `embedding_layer(torch.tensor([3]))` above** — the lookup is purely positional and stateless; embedding the same ID always produces the same vector (until training updates the weights).

### Gotcha — "embedding" sounds like computation, but it's a copy

It's tempting to imagine the embedding layer "computing" a representation for each token. It doesn't — at least, not at lookup time. All the "intelligence" lives in the *values stored in the table*, which are themselves *parameters* (`requires_grad=True` is visible right there in the printed tensor). Training is what sculpts those rows into meaningful representations; the embedding layer's *forward pass* is just an index operation — as fast as array indexing gets, and trivially parallelizable across an entire batch.

---

## 8 — 2.8 Encoding Word Positions: Absolute Positional Embeddings

**The problem it solves**: `nn.Embedding` returns the *same* vector for token ID `367` no matter where in the sequence it appears — first position, last position, anywhere. But word order obviously carries meaning (`"dog bites man"` ≠ `"man bites dog"`), and a transformer's core attention mechanism (which you'll meet in chapter 3) is itself *permutation-invariant* — it has no innate sense of sequence order at all. Without some explicit signal, the model would be staring at a "bag of tokens," blind to their arrangement.

**The intuition**: Imagine handing someone a stack of shuffled photographs from a vacation and asking them to describe the trip. Without page numbers, they could only describe *what* appeared, never *in what order things happened*. A positional embedding is exactly that page number — a second vector, looked up purely by *position* (`0`, `1`, `2`, `3`, …) rather than by *content*, that gets glued onto the content embedding so the model can tell "the third word in this sentence" apart from "the same word, but it was first."

```python
vocab_size = 50257
output_dim = 256

token_embedding_layer = torch.nn.Embedding(vocab_size, output_dim)
```

`50257` is GPT-2's real BPE vocabulary size — every possible token ID the tokenizer can produce now has its own row in this table. `256` is the embedding dimension chosen for this chapter (a realistic, if modest, value — GPT-2 small actually uses 768).

```python
max_length = 4
dataloader = create_dataloader_v1(
    raw_text, batch_size=8, max_length=max_length, stride=max_length, shuffle=False
)
data_iter = iter(dataloader)
inputs, targets = next(data_iter)

print("Token IDs:\n", inputs)
print("\nInputs shape:\n", inputs.shape)
```
```
Inputs shape:
 torch.Size([8, 4])
```

```python
token_embeddings = token_embedding_layer(inputs)
print(token_embeddings.shape)
```
```
torch.Size([8, 4, 256])
```

Watch the shape transform: the dataloader hands over `(8, 4)` — eight sequences of four token IDs each. Passing that straight through `token_embedding_layer` turns *every individual integer* into a 256-dimensional vector, producing `(8, 4, 256)` — exactly the canonical `(batch, seq_len, embedding_dim)` shape from the chapter 1 notes (the shape every transformer layer expects as its input).

### Building the positional embedding table

```python
context_length = max_length   # 4
pos_embedding_layer = torch.nn.Embedding(context_length, output_dim)
pos_embeddings = pos_embedding_layer(torch.arange(max_length))
print(pos_embeddings.shape)
```
```
torch.Size([4, 256])
```

This is the crucial design detail to absorb: **the positional embedding table is indexed by *position*, not by *token identity*.** It has exactly `context_length = 4` rows — one for "position 0," one for "position 1," and so on — completely independent of which of the 50,257 possible tokens happens to occupy that slot. `torch.arange(max_length)` produces the index sequence `[0, 1, 2, 3]`, and looking those up yields a `(4, 256)` tensor: one 256-dimensional "this is position $i$" vector per slot in the context window.

### Adding them together — and why broadcasting makes it trivial

```python
input_embeddings = token_embeddings + pos_embeddings
print(input_embeddings.shape)
```
```
torch.Size([8, 4, 256])
```

**Layer 1 — Intuition**: think of `token_embeddings` as eight stacked trays, each holding four word-meaning vectors, and `pos_embeddings` as a *single* tray of four "this is slot #0 / #1 / #2 / #3" vectors. Adding them is like sliding that one positional tray underneath *every one* of the eight content trays and merging the two — the position information gets stamped onto every sequence in the batch identically, because position #0 means the same thing (the start of the window) no matter which sequence you're looking at.

**Layer 2 — Math (broadcasting rule)**: `token_embeddings` has shape $(8, 4, 256)$ and `pos_embeddings` has shape $(4, 256)$. PyTorch's broadcasting rule (covered fully in the chapter 1 notes, section 12) compares shapes **right-to-left**:

$$
\begin{aligned}
\text{token\_embeddings:} \quad & (8,\ 4,\ 256) \\
\text{pos\_embeddings:} \quad & (\phantom{8,\ }4,\ 256) \\
\hline
\text{aligned as:} \quad & (8,\ 4,\ 256) \\
& (1,\ 4,\ 256) \quad \text{← missing leading dim treated as size 1, then stretched to 8}
\end{aligned}
$$

The trailing dimensions `(4, 256)` already match exactly, and the missing leading dimension of `pos_embeddings` is treated as size 1 and stretched ("broadcast") to size 8 — meaning the *same* `(4, 256)` positional tensor is added to each of the 8 sequences in the batch.

**Layer 3 — Dry run with tiny numbers**: suppose, for illustration, `output_dim = 2` and `max_length = 2` (instead of 256 and 4), with a *single* sequence in the batch:

```
token_embeddings[0] = [[1.0, 2.0],     <- embedding for token at position 0
                       [3.0, 4.0]]     <- embedding for token at position 1

pos_embeddings       = [[0.1, 0.1],     <- "this is position 0"
                        [0.2, 0.2]]     <- "this is position 1"

input_embeddings[0]  = [[1.0+0.1, 2.0+0.1],   = [[1.1, 2.1],
                        [3.0+0.2, 4.0+0.2]]      [3.2, 4.2]]
```

Row 0 of the content tensor gets row 0 of the positional tensor added to it; row 1 gets row 1. If a *second* sequence sat in `token_embeddings[1]`, it would get the *exact same* `pos_embeddings` rows added — `[0.1, 0.1]` to its first token, `[0.2, 0.2]` to its second — regardless of what those tokens actually are. That's the entire mechanism, scaled up from a $(2, 2)$ toy to the real $(8, 4, 256)$ tensors.

The result, `input_embeddings`, with its final shape `(8, 4, 256)`, is **the actual input the GPT model receives** — every token now carries both *what it is* (from `token_embeddings`) and *where it sits* (from `pos_embeddings`), summed into a single dense vector per position. This is precisely the picture the chapter's closing diagram shows: raw text → tokens → token IDs → (token embedding + positional embedding) → input embeddings, ready for the transformer.

### Gotcha — "absolute" positional embeddings are a *fixed-length* commitment

Because `pos_embedding_layer` is an `nn.Embedding(context_length, output_dim)` with exactly `context_length` rows, the model can never be handed a sequence longer than `context_length` tokens — there simply is no "position 5" row to look up if `context_length = 4`. This is precisely why GPT-2's `context_length` (1,024 tokens) is a hard architectural ceiling, not a soft suggestion — and why later architectures (RoPE, ALiBi, and other relative-position schemes) were invented to escape this fixed-length constraint. You'll meet GPT-2's actual configuration, including this exact `context_length` value, in chapter 4.

---

## 9 — Putting It All Together & Where This Leads

Trace the full pipeline end to end, one more time, with the actual shapes and numbers from this notebook:

```
"I HAD always thought..."                                  <- raw_text, 20,479 characters
        │  tiktoken BPE encode (section 2.5)
        ▼
[40, 367, 2885, 1464, 1807, ...]                            <- enc_text, 5,145 token IDs
        │  GPTDatasetV1 sliding window, max_length=4, stride=4 (section 2.6)
        ▼
inputs:  (8, 4) int64 tensor   targets: (8, 4) int64 tensor <- one batch from the DataLoader
        │  token_embedding_layer  (50257, 256)  (section 2.7)
        ▼
token_embeddings: (8, 4, 256)
        │  + pos_embedding_layer(arange(4))  ->  (4, 256), broadcast over batch (section 2.8)
        ▼
input_embeddings: (8, 4, 256)                                <- ready for the transformer
```

Every arrow in that diagram is now something you've built and watched run on real numbers: a custom regex tokenizer (and its two failure modes — lossy round-tripping and the `<|unk|>` collision), a production BPE tokenizer that sidesteps both failure modes, a `Dataset`/`DataLoader` pair that turns a flat token stream into properly shaped, shifted-by-one training batches, and two embedding lookup tables whose sum produces the actual tensor a GPT model consumes as input.

### Where to go next

* **`dataloader.ipynb`** (and its companion `dataloader_explanation.md` in this same `ch02/` folder) — a condensed, no-exploration version of exactly the `GPTDatasetV1` / `create_dataloader_v1` pipeline you just built, packaged as the reusable form you'll import in later chapters.
* **`exercise-solutions.ipynb`** — full write-ups of the chapter's end-of-chapter exercises, including the `"Akwirw ier"` BPE deep-dive mentioned in section 5.
* **`../02_bonus_bytepair-encoder/`** — a from-scratch BPE implementation compared side-by-side against `tiktoken`, for anyone who wants to see *how* the merge table itself gets built (rather than just loading a pretrained one).
* **Chapter 3 — Coding Attention Mechanisms** — the very next stop. `input_embeddings`, the `(batch, seq_len, embedding_dim)` tensor you just produced, is *exactly* the tensor that chapter 3's self-attention layers take as input. Everything in this chapter existed to manufacture that one tensor correctly.
