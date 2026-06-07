# Build a Large Language Model From Scratch
### by Sebastian Raschka

Source Repository: [rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch)  
Book Link: [Manning Publications](http://mng.bz/orYv)

---

## Course Overview

This book walks you through building a GPT-style Large Language Model from scratch using Python and PyTorch — from raw text all the way to a model that can follow instructions. The 7 chapters progress logically: PyTorch fundamentals, then text data, then the attention mechanism, then the full GPT architecture, then pretraining, then two chapters on finetuning.

---

## Can You Run This on a MacBook / Consumer GPU?

**Short answer: Yes, for everything the book asks you to do.**

The book was explicitly designed to run on a laptop. The author reduced the training context length to 256 tokens (from the original 1024) specifically so readers without a GPU can follow along. Here is the chapter-by-chapter reality:

| Chapter | Needs GPU? | MacBook Reality |
|---------|------------|-----------------|
| Ch01 — PyTorch Fundamentals | No | Pure CPU, runs fast |
| Ch02 — Working with Text | No | CPU only, lightweight |
| Ch03 — Attention Mechanisms | No | Small tensors, finishes instantly |
| Ch04 — GPT Architecture | No | Model is built but not trained |
| Ch05 — Pretraining | Recommended | Works on CPU/MPS, just slower. Context is reduced to 256 for laptops. Loading OpenAI weights requires ~500 MB RAM |
| Ch06 — Classification Finetuning | Recommended | Downloads GPT-2 124M. Apple Silicon MPS supported |
| Ch07 — Instruction Finetuning | Recommended | Loads pretrained GPT-2 then finetunes. Can use Ollama locally for evaluation |

### Apple Silicon (M1/M2/M3/M4)

PyTorch supports MPS (Metal Performance Shaders) on Apple Silicon. The notebook code checks `torch.cuda.is_available()` and falls back to CPU, but you can manually switch to MPS:

```python
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
```

Chapters 5–7 download pretrained GPT-2 weights using TensorFlow. You will need approximately 2 GB of free disk space for those chapters.

Training in Ch05–Ch07 runs noticeably slower on CPU or MPS compared to a dedicated GPU, but the datasets are intentionally small — training typically completes in minutes to a couple of hours on a MacBook.

### When You Would Actually Need a High-End GPU

Only if you want to go beyond the book's scope: larger context lengths (1024 instead of 256), bigger GPT-2 variants (355M, 774M, or 1558M parameters), or your own larger datasets. For every exercise in the book as written, a MacBook is sufficient.

---

## Chapter 1 — PyTorch Fundamentals for LLMs

**File:** [`ch01/01-pytorch_fundamentals_for_llms.ipynb`](code/ch01/01-pytorch_fundamentals_for_llms.ipynb)

This is a prerequisite chapter that builds the PyTorch foundation needed for everything that follows. It is specifically aimed at LLM development — not a generic deep learning intro.

**What you will learn:**

- **Tensors** — creating scalars, vectors, matrices, and 3D tensors; understanding `shape`, `ndim`, and dtypes (`float32`, `float16`, `int64`, `bool`)
- **Tensor Operations** — element-wise arithmetic, broadcasting with scalars, reshaping, `view()`, `permute()`, transposing
- **Indexing and Slicing** — selecting rows, columns, and sub-tensors; boolean masking with conditions like `tensor > 10`
- **Matrix Multiplication** — the `@` operator, `torch.matmul()`, and batched matmul. This is the most important operation in neural networks — embeddings, attention, and feed-forward layers are all matrix multiplications
- **Automatic Differentiation** — `requires_grad`, computing gradients with `backward()`, the computation graph
- **Building Neural Networks** — `nn.Module`, `nn.Linear`, `nn.ReLU`, `nn.Sequential`, `nn.Embedding`
- **The Training Loop** — forward pass, loss computation, `optimizer.zero_grad()`, `loss.backward()`, `optimizer.step()`
- **GPU Usage** — checking CUDA availability, moving tensors and models to device with `.to(device)`, MPS for Apple Silicon
- **NumPy Interop** — `torch.from_numpy()` shares memory (a change in NumPy changes the tensor); `torch.tensor()` makes a copy
- **Random Seeds** — `torch.manual_seed()` for reproducibility in experiments

The key thing to carry into later chapters: a batch of text in an LLM is a 3D tensor with shape `(batch_size, sequence_length, embedding_dim)`. Every operation in the architecture is built around this shape.

---

## Chapter 2 — Working with Text Data

**File:** [`ch02/ch02.ipynb`](code/ch02/ch02.ipynb)

This chapter covers the full pipeline from raw text to the numeric inputs an LLM can process.

**What you will learn:**

- **Word Embeddings** — what they are conceptually, why LLMs represent text as vectors in a high-dimensional space, and why that space cannot be visualised beyond 2–3 dimensions
- **Tokenization** — splitting text with regular expressions, handling punctuation and whitespace, building a `SimpleTokenizerV1` class with `encode()` and `decode()` methods
- **Token IDs** — building a vocabulary dictionary that maps words to integers, converting tokens to IDs and back
- **Special Tokens** — `<|endoftext|>`, `[BOS]`, `[EOS]`, `[PAD]`, `[UNK]` — what each signals to the model and when each is used
- **Byte Pair Encoding (BPE)** — using OpenAI's `tiktoken` library (the actual GPT-2 tokenizer), how BPE handles words not seen during training by decomposing them into subword units
- **Data Sampling with a Sliding Window** — how the training dataset is built from a single long text: input is a window of tokens, target is that same window shifted one position to the right
- **Token Embeddings** — `nn.Embedding`, embedding dimensionality, what it means for an integer to have a continuous vector representation
- **Positional Embeddings** — why Transformers have no built-in sense of order (unlike RNNs), absolute positional embeddings, and how token embeddings and positional embeddings are summed before entering the model

The practical dataset throughout this chapter is *The Verdict* by Edith Wharton — a public domain short story — which is also the training text used in Chapter 5.

---

## Chapter 3 — Coding Attention Mechanisms

**File:** [`ch03/ch03.ipynb`](code/ch03/ch03.ipynb)

This chapter builds the attention mechanism step by step, starting from a simplified version with no learnable parameters and ending with the full multi-head causal self-attention used in GPT.

**What you will learn:**

- **Why Attention Exists** — the problem with modeling long sequences in older encoder-decoder RNNs: the entire source sequence was compressed into a single hidden vector, which becomes an information bottleneck for long inputs
- **Simple Self-Attention (no weights)** — computing attention scores via dot products, normalising with softmax so weights sum to 1, computing context vectors as weighted sums over the input embeddings
- **Scaled Dot-Product Attention** — introducing trainable weight matrices W_Q, W_K, and W_V (Query, Key, Value); projecting inputs before computing attention; the 1/sqrt(d_k) scaling factor that prevents very large dot products from killing the softmax gradient
- **SelfAttention_v1 and v2** — building clean `nn.Module` classes that encapsulate the full computation
- **Causal (Masked) Attention** — applying an upper-triangular mask of -inf before softmax so each token can only attend to past positions; this is what makes GPT autoregressive, meaning it generates one token at a time without seeing the future
- **Dropout in Attention** — applied to attention weights during training for regularisation
- **Multi-Head Attention** — running multiple attention operations (heads) in parallel, splitting the embedding dimension across heads so each head specialises on different relationships, concatenating all head outputs and projecting back to the original dimension
- **Efficient Multi-Head Attention** — implementing with a single weight matrix and tensor reshaping rather than a loop over heads, which is how the operation is done in practice

The key insight on causal masking: setting future positions to -inf before softmax makes their post-softmax weight effectively 0. The model learns to attend only to what has already been generated, which is what enables next-token prediction.

---

## Chapter 4 — Implementing a GPT Model from Scratch

**File:** [`ch04/ch04.ipynb`](code/ch04/ch04.ipynb) | [`gpt.py`](code/ch04/gpt.py)

This chapter assembles all prior components — attention, normalisation, feed-forward layers — into a complete GPT-2 architecture that can generate text.

**What you will learn:**

- **GPT-2 Configuration** — the full 124M parameter config: `vocab_size=50257`, `context_length=1024`, `emb_dim=768`, `n_heads=12`, `n_layers=12`, `drop_rate=0.1`. Each setting is explained in terms of what it controls in the architecture
- **Layer Normalisation** — implementing `LayerNorm` from scratch with learnable `scale` and `shift` parameters; why `unbiased=False` is used (to match GPT-2's original weights for compatibility in later chapters)
- **GELU Activation** — why GELU is used instead of ReLU in transformers, the tanh approximation formula that GPT-2 was trained with
- **Feed-Forward Network** — the two-layer MLP inside each transformer block; the 4x expansion factor (768 → 3072 → 768)
- **Transformer Block** — the full residual structure: LayerNorm → MultiHeadAttention → residual add → LayerNorm → FeedForward → residual add. Residual connections let gradients flow directly backward through the block, which is critical for training deep networks
- **Full GPT Architecture** — `GPTModel` class: token embedding + positional embedding → dropout → N stacked transformer blocks → final LayerNorm → linear output head that maps from `emb_dim` back to `vocab_size`
- **Parameter Counting** — the model has approximately 163M total parameters when counted (the 124M figure omits the embedding layer in some counts)
- **Text Generation** — `generate_text_simple()`: given a starting context, run a forward pass, take the logit for the last token, apply argmax (greedy decoding) to get the next token, append it, repeat
- **Temperature and Top-K Sampling** — temperature scales logits before softmax (higher = more random, lower = more deterministic); top-k restricts sampling to only the k highest probability tokens at each step

A full GPT-2 (124M) can be implemented in roughly 150 lines of PyTorch. The architecture is just the same transformer block repeated 12 times. All the conceptual complexity is in the attention mechanism from Chapter 3.

---

## Chapter 5 — Pretraining on Unlabeled Data

**File:** [`ch05/ch05.ipynb`](code/ch05/ch05.ipynb) | [`gpt_train.py`](code/ch05/gpt_train.py) | [`gpt_generate.py`](code/ch05/gpt_generate.py)

This chapter implements the training loop, evaluates the model as it trains, and then loads OpenAI's real pretrained GPT-2 weights into the architecture built in Chapter 4.

**What you will learn:**

- **Cross-Entropy Loss** — applying softmax to the model's logits, then computing the negative log probability of the correct next token. The goal during training is to minimise this value by increasing the probability of the correct token at each position
- **Perplexity** — the exponential of cross-entropy loss; more interpretable because it roughly corresponds to the effective vocabulary size the model is uncertain about at each step
- **Training and Validation Losses** — splitting *The Verdict* into a training portion and a held-out validation portion; tracking both losses to detect overfitting
- **Training Loop** — `train_model_simple()`: iterating over batches, computing the forward pass, computing loss, calling `backward()`, clipping gradients, stepping the AdamW optimizer
- **Why the Training Dataset Is Small** — the book explicitly acknowledges this: Llama 2 7B cost approximately $690,000 in GPU compute. The small dataset lets readers train a model in minutes on a laptop for learning purposes
- **Decoding Strategies** — temperature, top-k sampling in practice; generating text before and after training to see the difference
- **Loading Pretrained GPT-2 Weights** — using `gpt_download.py` to fetch OpenAI's original TensorFlow checkpoint files, converting all weight tensors to PyTorch format, and loading them into the `GPTModel` built in Chapter 4. The architecture must match exactly for the weights to load correctly

After loading pretrained weights, the model generates coherent text immediately — demonstrating that the architecture implementation in Chapter 4 is correct.

---

## Chapter 6 — Finetuning for Text Classification

**File:** [`ch06/ch06.ipynb`](code/ch06/ch06.ipynb) | [`gpt_class_finetune.py`](code/ch06/gpt_class_finetune.py)

This chapter takes the pretrained GPT-2 and specialises it for a specific downstream task: classifying SMS messages as spam or not spam.

**What you will learn:**

- **Classification vs Instruction Finetuning** — a classification-finetuned model can only output the classes it was trained on (e.g., spam or not spam); an instruction-finetuned model can perform many tasks. Classification finetuning is more targeted and typically faster
- **Dataset Preparation** — the SMS Spam Collection dataset (5,572 messages); handling class imbalance by undersampling the majority class so both classes have equal representation (747 each); splitting into train/validation/test (70/10/20)
- **Modifying the Architecture** — replacing the GPT output head (which outputs `vocab_size=50257` logits) with a new classification head that outputs 2 logits (one per class); deciding which layers to freeze and which to leave trainable
- **SpamDataset Class** — padding all sequences to the same length using `<|endoftext|>` as the padding token; building PyTorch data loaders
- **Why the Last Token** — in a GPT model, the last token's hidden state is used for classification. The causal attention mask means the last token is the only position that has attended to all other tokens, so it carries the most complete representation of the input
- **Training and Evaluation** — computing accuracy on training, validation, and test sets during training; the final finetuned model achieves around 95% accuracy on the spam task

The broader lesson here is transfer learning: the pretrained GPT-2 already learned strong representations of language. Finetuning adapts those representations cheaply for a specific task without having to train from scratch.

---

## Chapter 7 — Finetuning to Follow Instructions

**File:** [`ch07/ch07.ipynb`](code/ch07/ch07.ipynb) | [`gpt_instruction_finetuning.py`](code/ch07/gpt_instruction_finetuning.py)

This is the final chapter, covering instruction finetuning — the technique that turns a text-completion model into an assistant that responds to natural language requests.

**What you will learn:**

- **Why Pretraining Alone Is Not Enough** — a pretrained GPT-2 is good at continuing text; it is not trained to respond to instructions. Instruction finetuning is the step that creates the chat-like behaviour seen in products like ChatGPT
- **Instruction Dataset Format** — Alpaca-style prompt templates with three structured fields: `### Instruction:`, `### Input:` (optional), and `### Response:`. The dataset used here contains 1,100 instruction-response pairs. The train/validation/test split is 85/5/10
- **InstructionDataset Class** — pre-tokenising all inputs, including the full formatted prompt plus response, and storing as encoded integer sequences
- **Custom Collate Function** — instead of padding all sequences in the dataset to a fixed global length, a custom `collate_fn` pads sequences only to the longest example within each batch. Different batches can have different lengths, which is more efficient
- **Masking the Instruction Tokens** — only the response portion of each sequence contributes to the loss. The instruction and input portions are masked with `-100` (the `ignore_index` in PyTorch's cross-entropy), so the model only learns to generate the correct answer, not to memorise the prompt
- **Training Loop** — supervised instruction finetuning using AdamW with a cosine learning rate schedule; starting from pretrained GPT-2 weights from Chapter 5
- **Extracting Responses** — the model generates the full formatted text; extracting just the portion after `### Response:` to evaluate the answer
- **Automated Evaluation with Ollama** — `ollama_evaluate.py` uses a locally running LLM (via Ollama) to score the finetuned model's responses against the expected answers, providing a quantitative measure of instruction-following quality

The result: a GPT-2 model trained on only 935 instruction-response examples learns to follow natural language instructions in a structured and coherent way. The quality is limited by the model size and training data volume, but the mechanism is identical to what production-scale models use.

---

## Code Files by Chapter

| Chapter | Main Notebook | Supporting Scripts |
|---------|---------------|--------------------|
| Ch01 | `01-pytorch_fundamentals_for_llms.ipynb` | — |
| Ch02 | `ch02.ipynb`, `dataloader.ipynb` | — |
| Ch03 | `ch03.ipynb`, `multihead-attention.ipynb` | — |
| Ch04 | `ch04.ipynb` | `gpt.py`, `previous_chapters.py` |
| Ch05 | `ch05.ipynb` | `gpt_train.py`, `gpt_generate.py`, `gpt_download.py`, `previous_chapters.py` |
| Ch06 | `ch06.ipynb` | `gpt_class_finetune.py`, `gpt_download.py`, `previous_chapters.py` |
| Ch07 | `ch07.ipynb` | `gpt_instruction_finetuning.py`, `ollama_evaluate.py`, `gpt_download.py`, `previous_chapters.py` |

---

## Setup

```bash
# Core
pip install torch tiktoken matplotlib numpy

# Chapters 5–7 (pretrained weight loading)
pip install tensorflow

# Chapter 6 (dataset handling)
pip install pandas

# Chapter 7 evaluation (optional — requires Ollama installed separately)
# https://ollama.ai
# ollama pull llama3
```

Python 3.9 or later is recommended to avoid SSL certificate issues when downloading files.

---

## Learning Path

```
Ch01  PyTorch tensors, autograd, building and training neural network modules
  |
Ch02  Text to tokens to token IDs to embeddings — the full data pipeline
  |
Ch03  Self-attention mechanism — the core computation of every transformer
  |
Ch04  GPT architecture assembled from all prior components
  |
Ch05  Training from scratch + loading real OpenAI GPT-2 weights
  |
Ch06  Classification finetuning — adapting pretrained GPT-2 for spam detection
  |
Ch07  Instruction finetuning — teaching the model to follow natural language instructions
```

By the end of Chapter 7, every component of a modern LLM has been built and understood from first principles.
