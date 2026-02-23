# Chapter 2: Working with Text Data — A Deep Explanation

> **Source:** _Build a Large Language Model (From Scratch)_ by Sebastian Raschka  
> **Repository:** [https://github.com/rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch)  
> **Chapter Focus:** Data preparation and sampling — turning raw text into tensors that an LLM can actually consume.

---

## The Big Picture

Before any neural network can process language, it needs numbers. Natural language is discrete, symbolic, and hierarchically structured; neural networks operate on continuous, high-dimensional vectors. The entire pipeline in this chapter is about bridging that gap. The flow is:

```
Raw Text  →  Tokens  →  Token IDs  →  Embeddings  →  LLM Input
```

Each arrow in that chain is a non-trivial transformation, and this chapter implements every one of them from scratch before graduating to the production-grade BPE tokenizer used by GPT-2.

---

## 2.1 Understanding Word Embeddings

A **word embedding** is a mapping from a discrete symbol (a word or subword token) into a point in a continuous vector space ℝᵈ, where d is the embedding dimensionality. The key insight is that this mapping is learned during training, not hand-crafted, so the geometry of the embedding space comes to reflect semantic and syntactic relationships in the data.

Formally, an embedding function E is defined as:

```
E : V → ℝᵈ
```

where V is the vocabulary (a finite set of token types) and d is the embedding dimension (often 256, 768, or even 12288 in large models).

Distances and dot products in this space carry meaning. In a well-trained embedding space, words with similar contexts end up with similar vectors:

```
cos_similarity(E("king"), E("queen"))  >>  cos_similarity(E("king"), E("bicycle"))
```

GPT-2 uses 768-dimensional embeddings for its base model. The full GPT-3 uses 12288 dimensions. In this chapter, we work with 256 dimensions for clarity.

---

## 2.2 Tokenizing Text

### Why Not Just Split on Spaces?

Splitting text on whitespace is tempting but wrong for several reasons. Punctuation should be separated from words ("hello," → ["hello", ","]). Contractions are ambiguous ("don't" → ["do", "n't"] or ["don", "'t"]). Hyphenated compounds need special treatment. A tokenizer must handle all of these consistently.

### Building a Simple Regular Expression Tokenizer

The chapter begins with the short story _The Verdict_ by Edith Wharton (public domain), downloaded directly from the raw GitHub source. This gives us real English prose with varied punctuation — a realistic stress test for any tokenizer.

**Step 1: Split on whitespace only**

```python
import re
text = "Hello, world. This, is a test."
result = re.split(r'(\s)', text)
# ['Hello,', ' ', 'world.', ' ', 'This,', ' ', 'is', ' ', 'a', ' ', 'test.']
```

The parentheses in `(\s)` are a capturing group, which causes `re.split` to include the delimiter (the space) in the result. This matters because we want to keep track of whitespace for reconstruction.

**Step 2: Also split on punctuation**

```python
result = re.split(r'([,.]|\s)', text)
# ['Hello', ',', '', ' ', 'world', '.', '', ' ', 'This', ',', '', ' ', ...]
```

Notice the empty strings — these appear between adjacent delimiters (e.g., a comma immediately followed by a space). We filter them out:

```python
result = [item for item in result if item.strip()]
# ['Hello', ',', 'world', '.', 'This', ',', 'is', 'a', 'test', '.']
```

**Step 3: Handle the full range of punctuation**

```python
text = "Hello, world. Is this-- a test?"
result = re.split(r'([,.:;?_!"()\']|--|\s)', text)
result = [item.strip() for item in result if item.strip()]
# ['Hello', ',', 'world', '.', 'Is', 'this', '--', 'a', 'test', '?']
```

The regex pattern `[,.:;?_!"()\'|--|` is a character class matching any one of the listed punctuation marks, plus `--` as a two-character token for em-dashes.

**Applied to the full text:**

```python
preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', raw_text)
preprocessed = [item.strip() for item in preprocessed if item.strip()]
# Results in ~4,690 tokens
```

The number of tokens is larger than the number of words because punctuation is now separated.

---

## 2.3 Converting Tokens into Token IDs

A neural network cannot operate on strings. We need to map every token string to an integer — its **token ID**. This mapping is the **vocabulary**.

### Building the Vocabulary

```python
all_words = sorted(set(preprocessed))   # deduplicate and sort alphabetically
vocab_size = len(all_words)             # number of unique token types
vocab = {token: integer for integer, token in enumerate(all_words)}
```

The vocabulary is a Python dictionary `str → int`. Its inverse `int → str` is needed for decoding. After processing the full text, the vocabulary contains around 1,130 unique tokens.

The sorted order is arbitrary — what matters is that it is fixed and deterministic. The index assigned to each token is its ID.

### The SimpleTokenizerV1 Class

```python
class SimpleTokenizerV1:
    def __init__(self, vocab):
        self.str_to_int = vocab
        self.int_to_str = {i: s for s, i in vocab.items()}

    def encode(self, text):
        preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', text)
        preprocessed = [item.strip() for item in preprocessed if item.strip()]
        ids = [self.str_to_int[s] for s in preprocessed]
        return ids

    def decode(self, ids):
        text = " ".join([self.int_to_str[i] for i in ids])
        text = re.sub(r'\s+([,.?!"()\'\\])', r'\1', text)
        return text
```

**`encode`** converts text to a list of integers. Every token is looked up in `str_to_int`. If a token is not found, Python raises a `KeyError` — we'll fix that in the next section.

**`decode`** converts a list of integers back to text. It first joins tokens with spaces (which is the default separator), then removes spurious spaces before punctuation using a substitution regex. The pattern `\s+([,.?!"()\'\\])` matches one or more spaces followed by a punctuation character and replaces the whole match with just the punctuation.

**Example dry run:**

```
Input:  '"It\'s the last he painted, you know," Mrs. Gisburn said.'
Tokens: ['"', 'It', "'", 's', 'the', 'last', 'he', 'painted', ',', ...]
IDs:    [0, 322, 550, 616, 956, 591, 411, 746, 4, ...]
Decode: '"It\'s the last he painted, you know," Mrs. Gisburn said.'
```

The round-trip `decode(encode(text)) == text` holds for any text that only uses tokens present in the vocabulary.

---

## 2.4 Adding Special Context Tokens

### The Out-of-Vocabulary Problem

SimpleTokenizerV1 fails immediately when it encounters a word not present in the training text:

```python
tokenizer.encode("Hello, do you like tea.")
# KeyError: 'Hello'
```

"Hello" was never in _The Verdict_, so it has no vocabulary entry. We need a fallback.

### Special Tokens

The chapter introduces two special tokens:

**`<|unk|>`** — represents any token not found in the vocabulary. When the encoder encounters an unknown string, it substitutes this token. This is a lossy operation: all unknown words map to the same ID and are therefore indistinguishable to the model.

**`<|endoftext|>`** — signals the boundary between independent documents. GPT-2 uses this token when training on concatenated text from different sources (articles, books, web pages). By inserting `<|endoftext|>` between documents, the model learns that attention should not cross document boundaries.

```python
all_tokens = sorted(list(set(preprocessed)))
all_tokens.extend(["<|endoftext|>", "<|unk|>"])
vocab = {token: integer for integer, token in enumerate(all_tokens)}
```

These are appended at the end, so they receive the highest IDs (e.g., 1130 and 1131 for a vocabulary of 1130 regular tokens).

### SimpleTokenizerV2

```python
class SimpleTokenizerV2:
    def __init__(self, vocab):
        self.str_to_int = vocab
        self.int_to_str = {i: s for s, i in vocab.items()}

    def encode(self, text):
        preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', text)
        preprocessed = [item.strip() for item in preprocessed if item.strip()]
        preprocessed = [
            item if item in self.str_to_int else "<|unk|>"
            for item in preprocessed
        ]
        ids = [self.str_to_int[s] for s in preprocessed]
        return ids

    def decode(self, ids):
        text = " ".join([self.int_to_str[i] for i in ids])
        text = re.sub(r'\s+([,.:;?!"()\'\\])', r'\1', text)
        return text
```

The only change in `encode` is the list comprehension that replaces unknown tokens with `"<|unk|>"` before the dictionary lookup.

**Concatenating two texts with a separator:**

```python
text1 = "Hello, do you like tea?"
text2 = "In the sunlit terraces of the palace."
text  = " <|endoftext|> ".join((text1, text2))
# 'Hello, do you like tea? <|endoftext|> In the sunlit terraces of the palace.'
```

The tokenizer now encodes this without errors. "Hello" maps to `<|unk|>`, and `<|endoftext|>` maps to its dedicated ID.

---

## 2.5 Byte Pair Encoding (BPE)

### Limitations of SimpleTokenizerV2

The simple tokenizer has a fundamental problem: every word not seen during vocabulary construction becomes `<|unk|>`. This is information destruction. A model trained with such a tokenizer cannot generalize well to new vocabulary.

GPT-2 solves this with **Byte Pair Encoding**, a data compression algorithm repurposed for tokenization.

### The BPE Algorithm (Conceptual)

BPE starts with a character-level vocabulary (every byte is its own token, giving a base vocabulary of 256 entries) and iteratively merges the most frequent adjacent pair of tokens into a new compound token. This continues until a target vocabulary size is reached.

For a vocabulary of size V, the algorithm is:

1. Initialize vocabulary with all individual characters (bytes).
2. Count all adjacent token pairs in the corpus.
3. Find the most frequent pair (a, b).
4. Add the merged token "ab" to the vocabulary.
5. Replace all occurrences of the pair (a, b) with "ab" in the corpus.
6. Repeat from step 2 until the vocabulary has V entries.

The learned merges are stored in a **merges table**. At inference time, tokenization applies these merges in the same order, producing a consistent segmentation.

GPT-2 uses a vocabulary of **50,257** tokens: 256 base byte tokens, 50,000 learned merges, and 1 special `<|endoftext|>` token.

### Why BPE Is Powerful

BPE handles out-of-vocabulary words gracefully by decomposing them into subword units. A novel technical term like "photosynthetically" might be tokenized as ["photo", "synth", "etically"] or ["ph", "otos", "ynthetically"] depending on what merges were learned. The worst case (a completely unknown byte sequence) falls back to individual bytes — so BPE **never** produces an `<|unk|>` token.

The mathematical cost: tokenizing text with BPE is O(n · |merges|) where n is the text length, but since the merges are applied in order and text length decreases with each merge, the practical runtime is much faster.

### Using tiktoken

OpenAI's `tiktoken` library implements GPT-2's BPE tokenizer with the merge table learned during GPT-2's training, with the core algorithm written in Rust for performance:

```python
import tiktoken
tokenizer = tiktoken.get_encoding("gpt2")

text = "Hello, do you like tea? <|endoftext|> In the sunlit terraces of someunknownPlace."
integers = tokenizer.encode(text, allowed_special={"<|endoftext|>"})
# [15496, 11, 466, 345, 588, 8887, 30, 220, 50256, 554, 262, 4252, 18250, ...]

strings = tokenizer.decode(integers)
# 'Hello, do you like tea? <|endoftext|> In the sunlit terraces of someunknownPlace.'
```

Notice how `<|endoftext|>` maps to ID 50256 — the last entry in GPT-2's vocabulary, as expected. The unknown word "someunknownPlace" is tokenized into subword pieces rather than a single `<|unk|>`.

The `allowed_special={"<|endoftext|>"}` argument is required because `tiktoken` treats special tokens with extra caution — you must explicitly declare which special tokens are permitted in the input to avoid accidental injection attacks in user-facing applications.

---

## 2.6 Data Sampling with a Sliding Window

### The Language Modeling Objective

A language model is trained to predict the next token given all previous tokens. This is the **autoregressive objective**: given a sequence x₁, x₂, ..., xₜ, the model maximizes:

```
P(x₁, x₂, ..., xₙ) = ∏ᵢ P(xᵢ | x₁, ..., xᵢ₋₁)
```

Taking the log:

```
log P(x₁, ..., xₙ) = Σᵢ log P(xᵢ | x₁, ..., xᵢ₋₁)
```

Training minimizes the negative log-likelihood (cross-entropy loss) over the corpus.

### Constructing Input-Target Pairs

For a sequence of token IDs `[t₀, t₁, t₂, t₃, t₄]`:

```
Input:  [t₀, t₁, t₂, t₃]
Target: [t₁, t₂, t₃, t₄]
```

The target is the input shifted one position to the right. Every position in the input simultaneously acts as a prediction context and a prediction target (for the position to its left). This is extremely sample-efficient.

```python
enc_sample = enc_text[50:]   # skip first 50 tokens
context_size = 4

x = enc_sample[:context_size]   # [290, 4920, 2241, 287]
y = enc_sample[1:context_size+1] # [4920, 2241, 287, 257]
```

Training sees each prefix:

```
[290]              → predict 4920
[290, 4920]        → predict 2241
[290, 4920, 2241]  → predict 287
[290, 4920, 2241, 287] → predict 257
```

In decoded text:

```
"and" → predict "established"
"and established" → predict "himself"
"and established himself" → predict "in"
"and established himself in" → predict "a"
```

### The Sliding Window

A **sliding window** (also called a **rolling window** or **striding window**) is used to extract multiple training samples from a long sequence of token IDs. Given a sequence of length N, a context size of L, and a stride of S:

```
Number of windows = floor((N - L) / S)
```

For N = 5000, L = 256, S = 128 (50% overlap):

```
floor((5000 - 256) / 128) = floor(37.06) = 37 windows
```

With stride = 1 (maximum overlap), we get N - L windows, but adjacent windows share L - 1 tokens.

**Stride trade-off:**

- **Small stride (S < L):** More training examples, but high overlap between windows means the model sees similar data many times. This can lead to overfitting on popular text positions.
- **Large stride (S = L):** No overlap. Fewer examples but maximum diversity. Used to reduce overfitting.

### GPTDatasetV1

```python
from torch.utils.data import Dataset, DataLoader

class GPTDatasetV1(Dataset):
    def __init__(self, txt, tokenizer, max_length, stride):
        self.input_ids = []
        self.target_ids = []

        token_ids = tokenizer.encode(txt, allowed_special={"<|endoftext|>"})

        for i in range(0, len(token_ids) - max_length, stride):
            input_chunk  = token_ids[i:i + max_length]
            target_chunk = token_ids[i + 1: i + max_length + 1]
            self.input_ids.append(torch.tensor(input_chunk))
            self.target_ids.append(torch.tensor(target_chunk))

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        return self.input_ids[idx], self.target_ids[idx]
```

`GPTDatasetV1` inherits from PyTorch's `Dataset` abstract class. Implementing `__len__` and `__getitem__` is the minimum contract required. The `DataLoader` wraps a `Dataset` to provide batching, shuffling, and parallel data loading.

**Memory layout:** All token ID tensors are stored as pre-computed `torch.tensor` objects. For the full ~5,000-token _Verdict_ with `max_length=256` and `stride=128`, this generates approximately 37 samples, each holding 256 integers — trivially small. For real-world training on petabytes of text, memory-mapped files and streaming datasets replace this approach.

### The DataLoader

```python
def create_dataloader_v1(txt, batch_size=4, max_length=256,
                          stride=128, shuffle=True, drop_last=True,
                          num_workers=0):
    tokenizer = tiktoken.get_encoding("gpt2")
    dataset   = GPTDatasetV1(txt, tokenizer, max_length, stride)
    dataloader = DataLoader(dataset, batch_size=batch_size,
                            shuffle=shuffle, drop_last=drop_last,
                            num_workers=num_workers)
    return dataloader
```

Key parameters:

- `drop_last=True` — drops the final incomplete batch. This prevents shape inconsistencies when the dataset size is not divisible by batch_size.
- `shuffle=True` — randomizes the order of samples each epoch, which helps the optimizer generalize (avoids learning the sequential order of the text).
- `num_workers=0` — single-process data loading. Increase for production to overlap CPU data preparation with GPU computation.

**Example output with `batch_size=1, max_length=4, stride=1`:**

```
First batch:
[tensor([[40, 367, 2885, 1464]]),      # inputs
 tensor([[367, 2885, 1464, 1807]])]    # targets (shifted by 1)

Second batch:
[tensor([[367, 2885, 1464, 1807]]),    # starts 1 token later
 tensor([[2885, 1464, 1807, 3619]])]
```

**Example with `batch_size=8, max_length=4, stride=4`:**

```
Inputs (8×4):
tensor([[   40,   367,  2885,  1464],
        [ 1807,  3619,   402,   271],
        ...])

Targets (8×4):
tensor([[  367,  2885,  1464,  1807],
        [ 3619,   402,   271,   10899],
        ...])
```

Here stride equals context_size so there is zero overlap between rows.

---

### Two different types of data is discussed above?

The thing is, they're not really two different types of dataset. They're the **same idea** looked at from two different angles.

Let me explain what's actually happening.

---

**The first one (growing context) is showing you the training signal inside a single window.**

When you have a window of 4 tokens like `[290, 4920, 2241, 287]`, the model doesn't just make one prediction from it. It makes **four predictions simultaneously**:

- seeing `[290]` → predict `4920`
- seeing `[290, 4920]` → predict `2241`
- seeing `[290, 4920, 2241]` → predict `287`
- seeing `[290, 4920, 2241, 287]` → predict `257`

That's what the growing context example is illustrating. It's showing you the training signal _inside_ the window. The transformer's attention mechanism handles this naturally because each position can only attend to tokens before it (this is called causal or masked attention, which you'll see in later chapters).

---

**The second one (sliding window) is showing you how you move through the full text to generate many windows.**

The dataset needs thousands of training examples, not just one window of 4 tokens. So you slide the window across the entire tokenized text, each time grabbing a new input-target pair of length 4. With stride=1, the second window starts just one token later than the first.

---

**So to directly answer your question — why do they differ?**

They're operating at different levels of abstraction. The growing context view is zoomed into _one window_ and showing the multiple predictions packed inside it. The sliding window view is zoomed out to show how you generate _many windows_ from the full text.

Think of it like this — the sliding window gives you the rows of your training dataset. The growing context view explains what the loss function is computing inside each row.

One window → multiple predictions. That's the core insight.

---

## 2.7 Creating Token Embeddings

### From IDs to Vectors

An embedding layer is a lookup table: a matrix $W_E$ of shape $(V, d)$ where $V$ is the vocabulary size and $d$ is the embedding dimension. To embed a token with ID $k$, we simply extract row $k$ of $W_E$:

$$E(k) = W_E[k, :] \in \mathbb{R}^d$$

This is mathematically equivalent to one-hot encoding followed by a linear projection. If $e_k$ is the one-hot vector for token $k$ (a vector of length $V$ with a 1 at position $k$ and zeros elsewhere), then:

$$W_E^\top \cdot e_k = W_E[k, :]$$

But directly implementing it as a lookup is $O(d)$ per token rather than $O(V \cdot d)$ for the matrix multiplication, so it is far more efficient.

In PyTorch:

```python
vocab_size  = 6
output_dim  = 3

torch.manual_seed(123)
embedding_layer = torch.nn.Embedding(vocab_size, output_dim)
print(embedding_layer.weight)
```

Output (a $6 \times 3$ matrix, randomly initialized):

```
Parameter containing:
tensor([[ 0.3374, -0.1778, -0.3035],
        [ 0.1794,  1.8951,  0.4954],
        [ 0.2692, -0.0770, -1.0205],
        [-0.1170,  0.4987,  1.0108],
        [ 0.6700, -0.3810,  0.1583],
        [-0.3160,  0.2997, -0.8001]])
```

Token ID 3 maps to row 3: `[-0.1170, 0.4987, 1.0108]`.

```python
embedding_layer(torch.tensor([3]))
# tensor([[-0.1170,  0.4987,  1.0108]])
```

For a batch of tokens `[2, 3, 5, 1]`:

```python
input_ids = torch.tensor([2, 3, 5, 1])
embedding_layer(input_ids)
# tensor([[ 0.2692, -0.0770, -1.0205],   ← row 2
#         [-0.1170,  0.4987,  1.0108],   ← row 3
#         [-0.3160,  0.2997, -0.8001],   ← row 5
#         [ 0.1794,  1.8951,  0.4954]])  ← row 1
```

The key point: the embedding weights $W_E$ are **trainable parameters**. Backpropagation updates them during training such that tokens with similar roles receive similar representations. At initialization they are random; after training they encode semantic relationships.

### Scaling Up to GPT-2 Dimensions

```python
vocab_size  = 50257   # GPT-2 vocabulary size
output_dim  = 256     # our working embedding dimension

token_embedding_layer = torch.nn.Embedding(vocab_size, output_dim)
```

This creates a weight matrix of shape $(50257, 256)$, which holds $50257 \times 256 = 12{,}865{,}792$ parameters — over 12 million trainable floats just for the embedding layer. GPT-2's full base model uses $d = 768$, giving $50257 \times 768 \approx 38.6$ million embedding parameters.

For a batch of 8 sequences, each of length 4:

```python
token_embeddings = token_embedding_layer(inputs)
print(token_embeddings.shape)   # torch.Size([8, 4, 256])
```

The output tensor has three dimensions: `(batch_size, sequence_length, embedding_dim)`.

---

## 2.8 Encoding Word Positions

### The Position Blindness Problem

The embedding layer we just built is **position-agnostic**: the same token ID always maps to the same vector regardless of where in the sequence it appears. But word order is fundamental to meaning. "Dog bites man" and "Man bites dog" would produce identical sets of token embeddings (just in different order), yet they mean very different things.

The transformer architecture — which GPT-2 is based on — processes all tokens in parallel via self-attention. Unlike RNNs, it has no inherent sense of sequence order. We must inject positional information explicitly.

### Positional Embeddings

GPT-2 uses **absolute positional embeddings**: a second lookup table $W_P$ of shape $(L, d)$, where $L$ is the maximum context length (1024 for GPT-2) and $d$ is the embedding dimension. Position $i$ maps to row $i$ of $W_P$.

```python
context_length      = max_length  # 4 in our example
pos_embedding_layer = torch.nn.Embedding(context_length, output_dim)
```

To get positional embeddings for a sequence of length $L$:

```python
pos_embeddings = pos_embedding_layer(torch.arange(max_length))
# torch.arange(4) = tensor([0, 1, 2, 3])
print(pos_embeddings.shape)   # torch.Size([4, 256])
```

`torch.arange(max_length)` generates the position indices $[0, 1, 2, 3]$, which are then looked up in $W_P$.

### Combining Token and Positional Embeddings

The final input embedding for each token is the sum of its token embedding and its positional embedding:

$$\text{InputEmbedding}(\text{token\_id},\ \text{position}) = E(\text{token\_id}) + P(\text{position})$$

In matrix form, for a single sequence of length $L$ with embedding dimension $d$:

$$X \in \mathbb{R}^{L \times d} \quad \text{where} \quad X[i, :] = W_E[\text{token\_id}[i], :] + W_P[i, :]$$

```python
input_embeddings = token_embeddings + pos_embeddings
print(input_embeddings.shape)   # torch.Size([8, 4, 256])
```

PyTorch broadcasts `pos_embeddings` of shape `(4, 256)` across the batch dimension of `token_embeddings` of shape `(8, 4, 256)`, adding the same positional embedding to each item in the batch.

### Why Addition Works

Adding two vectors of the same dimensionality in the embedding space is a well-established trick in representation learning. The model learns to encode token identity and position in complementary subspaces of $\mathbb{R}^d$, so the sum carries both types of information without destructive interference. Empirically this works well despite being simple.

**Alternative: Sinusoidal Positional Encodings**

The original _Attention Is All You Need_ paper (Vaswani et al., 2017) used fixed (non-learned) sinusoidal positional encodings:

$$PE(\text{pos},\ 2i)   = \sin\!\left(\frac{\text{pos}}{10000^{2i/d}}\right)$$

$$PE(\text{pos},\ 2i+1) = \cos\!\left(\frac{\text{pos}}{10000^{2i/d}}\right)$$

where $\text{pos}$ is the position in the sequence and $i$ is the dimension index. These are not trained; they are computed analytically. GPT-2 instead uses learned positional embeddings ($W_P$ is a trainable parameter), which is simpler to implement and empirically performs comparably on standard benchmarks.

---

## Summary: The Complete Data Pipeline

The full pipeline from raw text to LLM input tensors is:

```
Raw Text
   ↓  [regex tokenization]
Token Strings:  ["Hello", ",", "world", "."]
   ↓  [vocabulary lookup]
Token IDs:      [232, 4, 1048, 7]
   ↓  [sliding window]
Input/Target pairs:  ([232, 4, 1048, 7], [4, 1048, 7, 912])
   ↓  [DataLoader batching]
Batched Tensors: shape (batch_size, context_length)
   ↓  [token embedding layer W_E]
Token Embeddings: shape (batch_size, context_length, d)
   ↓  [+ positional embedding layer W_P]
Input Embeddings: shape (batch_size, context_length, d)
   ↓
   LLM (Transformer)
```

For GPT-2 scale: vocabulary = 50,257, context_length = 1024, d = 768, batch_size typically 512.

---

## Key Mathematical Objects Reference

| Symbol | Shape     | Description                        |
| ------ | --------- | ---------------------------------- |
| $W_E$  | (V, d)    | Token embedding weight matrix      |
| $W_P$  | (L, d)    | Positional embedding weight matrix |
| X      | (B, L, d) | Final input embeddings to LLM      |
| B      | scalar    | Batch size                         |
| L      | scalar    | Context (sequence) length          |
| d      | scalar    | Embedding dimension                |
| V      | scalar    | Vocabulary size                    |

---

## References

- Raschka, S. (2024). _Build a Large Language Model (From Scratch)_. Manning Publications. [http://mng.bz/orYv](http://mng.bz/orYv)
- GitHub Repository: [https://github.com/rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch)
- Sennrich, R., Haddow, B., & Birch, A. (2016). Neural Machine Translation of Rare Words with Subword Units. _ACL 2016_. [https://arxiv.org/abs/1508.07909](https://arxiv.org/abs/1508.07909) — Original BPE paper applied to NLP.
- Radford, A., et al. (2019). Language Models are Unsupervised Multitask Learners. OpenAI Blog. — GPT-2 paper describing BPE tokenization and absolute positional embeddings.
- Vaswani, A., et al. (2017). Attention Is All You Need. _NeurIPS 2017_. [https://arxiv.org/abs/1706.03762](https://arxiv.org/abs/1706.03762) — Original Transformer paper with sinusoidal positional encodings.
- OpenAI tiktoken: [https://github.com/openai/tiktoken](https://github.com/openai/tiktoken)
- GPT-2 original BPE encoder: [https://github.com/openai/gpt-2/blob/master/src/encoder.py](https://github.com/openai/gpt-2/blob/master/src/encoder.py)
