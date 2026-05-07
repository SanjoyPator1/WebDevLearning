# Chapter 10: Creating Text Embedding Models

## Hands-On Large Language Models — Jay Alammar & Maarten Grootendorst (O'Reilly)

> This chapter teaches you to build, train, and evaluate a text embedding model from scratch using contrastive learning — the same paradigm behind word2vec, CLIP, and modern sentence transformers.

---

## Table of Contents

1. [Embedding Models](#1-embedding-models)
2. [What Is Contrastive Learning?](#2-what-is-contrastive-learning)
   - [The Idea Behind Contrast](#the-idea-behind-contrast)
   - [How Contrastive Learning Works in Practice](#how-contrastive-learning-works-in-practice)
3. [SBERT](#3-sbert)
   - [The Problem with Cross-Encoders](#the-problem-with-original-bert)
   - [The Siamese Architecture](#the-siamese-architecture)
4. [Creating an Embedding Model](#4-creating-an-embedding-model)
   - [4.1 Generating Contrastive Examples — NLI Datasets](#41-generating-contrastive-examples--nli-datasets)
   - [4.2 The Five-Step Training Pipeline](#42-the-five-step-training-pipeline)
5. [In-Depth Evaluation](#5-in-depth-evaluation)
   - [5.1 STSB — The Fast Sanity Check](#51-stsb--the-fast-sanity-check)
   - [5.2 MTEB — The Full Picture](#52-mteb--the-full-picture)
6. [Loss Functions](#6-loss-functions)
   - [6.1 Cosine Similarity Loss](#61-cosine-similarity-loss)
   - [6.2 Multiple Negatives Ranking Loss](#62-multiple-negatives-ranking-loss)
   - [6.3 Which Loss to Use](#63-which-loss-to-use)
7. [Fine-Tuning an Embedding Model](#7-fine-tuning-an-embedding-model)
   - [7.1 Supervised Fine-Tuning](#71-supervised-fine-tuning)
   - [7.2 Augmented SBERT](#72-augmented-sbert)
8. [Unsupervised Learning — TSDAE](#8-unsupervised-learning--tsdae)
   - [8.1 The Core Idea: Denoising as Self-Supervision](#81-the-core-idea-denoising-as-self-supervision)
   - [8.2 Using TSDAE for Domain Adaptation](#82-using-tsdae-for-domain-adaptation)
9. [Key Takeaways](#9-key-takeaways)

---

## 1. Embedding Models

Imagine a librarian who has read every book in a vast library and must file each book on a giant three-dimensional map — placing books about quantum physics near each other, cookbooks in another neighbourhood, and romantic novels in yet another. Books that discuss the same topic end up close together on the map; books about entirely different subjects are far apart. Now imagine the map has not three dimensions but 768. That is essentially what a text **embedding model** does: it reads a piece of text and files it at a precise location in a high-dimensional space, where the address (the vector of numbers) encodes the meaning.

More formally, an embedding model is a neural network that transforms a variable-length text input — a word, a sentence, an entire document — into a fixed-size numerical vector called an **embedding**. The key invariant that makes embeddings useful is this: semantically similar documents produce vectors that are close together in the embedding space, while semantically dissimilar documents produce vectors that are far apart. "Close" and "far" are measured by geometric distances such as cosine similarity or Euclidean distance.

```
Raw Text        Embedding Model        Vector Representation
─────────────   ───────────────────   ──────────────────────────────────
"The cat sat"                          [0.23, -0.11, 0.87, ..., 0.04]
                  (BERT-based)                ↕  768 dimensions
"A kitten rests"  ──────────────────►  [0.21, -0.09, 0.85, ..., 0.06]  ← close!

"Stock prices"    ──────────────────►  [-0.72, 0.43, -0.31, ..., 0.88] ← far away
```

The practical power of this representation is enormous. Once you have embeddings, **semantic search** becomes a nearest-neighbour lookup in vector space — you embed the query and find the stored documents whose vectors are closest to it. **Retrieval-Augmented Generation (RAG)** systems depend entirely on this: they embed a user's question, retrieve the closest document chunks from a vector database, and feed those chunks to a language model. Clustering, topic modelling, and recommendation all follow the same principle.

One subtlety the book emphasises early is that *what* counts as "similar" depends entirely on what the embedding model was trained to capture. A model trained on semantic similarity groups documents by their *meaning*. A model trained on sentiment similarity groups documents by whether they express positive or negative feelings. These are genuinely different objectives, and you need a different trained model for each. A product review saying "This camera is terrible — the build quality is wonderful but the autofocus ruins everything" sits close to other angry reviews in a sentiment-trained space, but close to other camera reviews in a semantics-trained space. Choosing the wrong model for your task is one of the most common mistakes practitioners make.

---

## 2. What Is Contrastive Learning?

### The Idea Behind Contrast

Consider a journalist who has cornered a bank robber and asks: "Why did you rob the bank?" The robber answers: "Because that's where the money is." Now the journalist asks: "Yes, but why did you rob *this particular* bank and not the one on Fifth Avenue?" This second question is a **contrastive question** — it forces an answer that explains the distinctive characteristics of this bank relative to the alternatives. The answer might be: "This one has weaker security and fewer cameras." That answer is far more informative, because it names the *specific features* that made this bank the choice.

This is the intellectual core of **contrastive learning** in machine learning. Rather than showing a model only positive examples of a concept ("here are 10,000 photos of dogs — learn what a dog is"), you show it positive examples alongside negative examples, forcing it to learn what makes the positive examples *distinct*. A model trained only on dog photos might learn "four legs, ears, tail" — but so do cats, horses, and cows. A model trained contrastively, seeing dogs alongside cats, horses, and cows, is forced to identify the features that are specifically *dog-like* rather than just generically *animal-like*.

The book uses a beautiful horse-versus-zebra illustration. If you feed a model only horses, it learns "four legs, nose, mane, tail." But it has never needed to distinguish a horse from a zebra. The moment you add zebras as negative examples, the model suddenly must learn "stripes" as the defining distinguishing feature — not because stripes are the most prominent visual feature, but because stripes are the *contrastive* feature. The contrast reveals what truly matters for the classification.

### How Contrastive Learning Works in Practice

In the embedding setting, contrastive learning works through a training objective that operates on pairs or triplets of examples. Given an **anchor** sentence, a **positive** sentence (semantically similar to the anchor), and a **negative** sentence (semantically dissimilar), the loss function pushes the anchor's embedding closer to the positive and farther from the negative in vector space.

```
Before Training:                After Training:
                                           ●  anchor
anchor ●                                  ●  positive (pulled close)
                ● positive
                                                          ● negative (pushed away)
      ● negative
```

The training loop repeats this pulling-and-pushing over many pairs until the embedding space has been shaped so that semantic relationships are encoded geometrically. It is worth noting that this idea is not new to the transformer era. **Word2Vec**, introduced in 2013, already used contrastive learning — the skip-gram model is trained to predict surrounding words (positives) while being contrasted against randomly sampled words (negatives). The innovation in modern sentence embedding models is to scale this idea to entire sentences using transformer encoders.

---

## 3. SBERT

### The Problem with Original BERT

BERT, introduced by Google in 2018, quickly became the default backbone for NLP tasks. For tasks that require comparing two pieces of text — is document A similar to document B? — a natural use of BERT is a **cross-encoder** architecture: you feed both sentences together as a single input sequence in the format `[CLS] sentence_A [SEP] sentence_B [SEP]`, and a classifier on top of the `[CLS]` token predicts a similarity score between 0 and 1.

The cross-encoder works well in isolation. The problem is that it cannot produce standalone sentence embeddings. Every time you want to compare two sentences, you must run both sentences through the full BERT model together — there is no way to pre-compute an embedding for sentence A and reuse it when comparing A against B, C, D, and E. This creates a severe computational scaling problem.

To see how bad the scaling is, consider a corpus of just 10,000 sentences. To rank them all by mutual similarity, you need to compare every pair:

```
Required comparisons = n × (n - 1) / 2

For n = 10,000:
  = 10,000 × 9,999 / 2
  = 49,995,000  ≈ 50 million comparisons

If each BERT forward pass takes 1 millisecond:
  50,000,000 × 0.001 seconds = 50,000 seconds ≈ 13.9 hours

For n = 100,000 sentences: ~1,390 hours (58 days)
```

This is completely impractical for any real search or retrieval application where documents number in the millions.

### The Siamese Architecture

**SBERT** (Sentence-BERT), introduced by Reimers and Gurevych in 2019, solves this with a **Siamese architecture** — a network design where two identical copies of BERT, sharing the exact same weights, process the two sentences completely independently.

```
CROSS-ENCODER (cannot pre-compute, must process pairs at query time):

  [CLS] sent_A [SEP] sent_B [SEP]
             │
           [BERT]
             │
        [Classifier]
             │
       similarity score


SIAMESE SBERT (pre-compute each embedding once, compare at any time):

  sent_A ──► [BERT] ──► [Mean Pool] ──► emb_A ──┐
                  (shared weights)               ├──► cosine_sim(emb_A, emb_B)
  sent_B ──► [BERT] ──► [Mean Pool] ──► emb_B ──┘
```

The two BERT towers have identical architecture and share all their weights — they are the same model, just called twice. Each tower independently processes one sentence and produces a sequence of token-level embeddings (shape: `[seq_len, 768]`). A **mean pooling** layer then averages all token embeddings across the sequence dimension to produce a single fixed-size sentence vector of shape `[768]`. The similarity between sentences A and B is then the cosine similarity between their respective pooled embeddings.

The critical advantage is reusability. You embed all your documents *once* and store the vectors in a database. When a query arrives, you embed the query *once* and perform a nearest-neighbour search over the pre-computed document vectors. For 10,000 documents, you do 10,000 forward passes during indexing (a one-time cost), and then a single forward pass plus a fast vector search at query time — rather than 50 million cross-encoder passes.

The trade-off is accuracy. Cross-encoders see both sentences simultaneously and can model their interaction directly, making them more precise similarity estimators. SBERT processes sentences independently, so it cannot capture fine-grained cross-sentence interactions. In practice, the accuracy gap is acceptable for retrieval tasks, and the speed advantage is so enormous that SBERT-style architectures have become the industry default for embedding-based search.

---

## 4. Creating an Embedding Model

### 4.1 Generating Contrastive Examples — NLI Datasets

To train SBERT contrastively, you need pairs of sentences labelled as similar or dissimilar. One of the most convenient natural sources for this is a **Natural Language Inference (NLI)** dataset. NLI is a classical NLP task where you are given a *premise* and a *hypothesis* and must predict one of three relationships: the hypothesis logically *entails* the premise (they say essentially the same thing), it *contradicts* the premise, or it is *neutral* (neither follows from nor contradicts).

This three-way labelling maps cleanly onto contrastive training data. An entailment pair is a positive pair — two sentences with closely related meaning that the model should embed near each other. A contradiction pair is a natural negative — two sentences with opposite or incompatible meanings that should end up far apart. A neutral pair carries an ambiguous signal (they could be related or not), so we simply discard them.

```
Premise:       "He is in the cinema watching Coco"
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    Entailment         Neutral       Contradiction
   (label = 0)       (label = 1)     (label = 2)
          │               │               │
"He is in the        "He enjoys       "He is watching
 movie theater        animated          Frozen at home"
 watching the         films"
 Disney movie Coco"
          │               │               │
       POSITIVE        DISCARD          NEGATIVE
```

The book uses the **MNLI corpus** (Multi-Genre Natural Language Inference), which contains 392,702 annotated sentence pairs drawn from multiple genres of text including fiction, telephone conversations, and government reports. We take the first 50,000 pairs as our training set — the book notes that smaller subsets produce less stable models because the model sees too few contrastive examples to learn robust representations.

```python
from datasets import load_dataset

# Load MNLI from the GLUE benchmark collection
# Label integers: 0 = entailment, 1 = neutral, 2 = contradiction
train_dataset = load_dataset(
    "glue", "mnli", split="train"
).select(range(50_000))

# Inspect a sample to understand the structure
sample = train_dataset[2]
print("Premise:", sample["premise"])
print("Hypothesis:", sample["hypothesis"])
print("Label:", sample["label"])
# → Label 0 means entailment: the hypothesis paraphrases the premise
```

### 4.2 The Five-Step Training Pipeline

Training an SBERT-style embedding model with the `sentence-transformers` library follows a consistent five-step pattern. Each step has a clear purpose, and understanding why each component exists matters as much as knowing the API.

**Step 1: Define the base model.** We start from a pre-trained BERT checkpoint rather than training from random weights. This is transfer learning — BERT already understands English grammar and general semantics from pre-training on billions of words, and contrastive fine-tuning will reshape its embedding space to specifically encode semantic similarity. We use `bert-base-uncased`, which has 12 transformer layers, 768-dimensional hidden states, and 110 million parameters. By default, all layers are left trainable — the book notes that freezing layers generally hurts performance because the early layers need to adapt too.

```python
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer('bert-base-uncased')

print("Base model loaded.")
print(f"Embedding dimension: {embedding_model.get_sentence_embedding_dimension()}")
# → 768
```

**Step 2: Define the loss function.** For this initial baseline, we use `SoftmaxLoss`, which treats the three-way NLI classification (entailment / neutral / contradiction) as a standard supervised classification problem. The loss computes the cross-entropy between the predicted class probabilities and the true labels. This is not the best loss function for embedding quality, but it is a clean, well-understood baseline that we will improve upon in Section 6.

```python
from sentence_transformers import losses

train_loss = losses.SoftmaxLoss(
    model=embedding_model,
    sentence_embedding_dimension=embedding_model.get_sentence_embedding_dimension(),
    num_labels=3   # entailment, neutral, contradiction
)

print("Loss function: SoftmaxLoss with 3 output classes")
```

**Step 3: Create the evaluator.** We evaluate using the **Semantic Textual Similarity Benchmark (STSB)**, a collection of sentence pairs annotated by humans with similarity scores on a 1–5 scale. Higher scores mean more similar. The evaluator computes cosine similarity between the model's embeddings of both sentences and then measures how well those predicted similarities correlate with the human-labelled scores. We will look at the evaluation metrics in detail in Section 5.

```python
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator

val_sts = load_dataset("glue", "stsb", split="validation")

evaluator = EmbeddingSimilarityEvaluator(
    sentences1=val_sts["sentence1"],
    sentences2=val_sts["sentence2"],
    scores=[score / 5 for score in val_sts["label"]],  # normalise to [0, 1]
    main_similarity="cosine"
)

print(f"Evaluator ready. Validation set size: {len(val_sts['sentence1'])} pairs")
```

**Step 4: Set training arguments.** The `SentenceTransformerTrainingArguments` class wraps the Hugging Face `TrainingArguments` with sentence-transformer-specific defaults.

| Parameter | Value | Why |
|---|---|---|
| `num_train_epochs` | 1 | Keep fast for demonstration; increase for production |
| `per_device_train_batch_size` | 32 | Fits comfortably in GPU VRAM; increase if VRAM allows |
| `warmup_steps` | 100 | Linear LR ramp-up from 0 to initial LR over first 100 steps |
| `fp16` | True | Use 16-bit floats to halve VRAM usage and speed up compute |
| `eval_steps` | 100 | Run evaluator every 100 training steps |

The `warmup_steps` parameter is worth understanding. At the very start of training, the randomly-initialised classifier head produces wildly wrong predictions, and a full learning rate applied immediately would push the pre-trained BERT weights far from their carefully optimised starting point. Warmup linearly increases the learning rate from 0 to its target value over the first `warmup_steps` steps, letting the model stabilise before making large weight updates.

```python
from sentence_transformers.training_args import SentenceTransformerTrainingArguments

args = SentenceTransformerTrainingArguments(
    output_dir="base_embedding_model",
    num_train_epochs=1,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    warmup_steps=100,
    fp16=True,
    eval_steps=100,
    logging_steps=100,
)

print("Training arguments configured.")
print(f"  Output directory: {args.output_dir}")
print(f"  Epochs: {args.num_train_epochs}")
print(f"  Batch size: {args.per_device_train_batch_size}")
```

**Step 5: Train.** The `SentenceTransformerTrainer` orchestrates the training loop, evaluation, and checkpoint saving.

```python
from sentence_transformers.trainer import SentenceTransformerTrainer

trainer = SentenceTransformerTrainer(
    model=embedding_model,
    args=args,
    train_dataset=train_dataset,
    loss=train_loss,
    evaluator=evaluator
)

print("Starting training...")
trainer.train()
print("Training complete.")
print("Baseline result (softmax loss): pearson_cosine ≈ 0.59")
# Checkpoints are saved to 'base_embedding_model/' at each eval_steps
```

The baseline result — `pearson_cosine = 0.59` — is the benchmark we will improve upon by choosing better loss functions. A score of 0.59 means the model's predicted cosine similarities correlate moderately with human judgements, but there is substantial room for improvement.

---

## 5. In-Depth Evaluation

### 5.1 STSB — The Fast Sanity Check

The **Semantic Textual Similarity Benchmark (STSB)** is a dataset of sentence pairs hand-labelled by multiple human annotators with similarity scores ranging from 1 (completely unrelated) to 5 (identical in meaning). A few examples to calibrate intuition:

- Score 5.0: *"A man is playing a guitar."* / *"A man is playing a musical instrument."*
- Score 2.5: *"The boy is running."* / *"The boy is kicking a ball."*
- Score 1.0: *"A woman is sitting."* / *"A group of men are playing football."*

After normalising scores to $[0, 1]$ by dividing by 5, the evaluator computes the cosine similarity between the model's embeddings of each pair and then measures correlation with the human labels using two statistics.

**Pearson correlation** measures the strength of the *linear* relationship between two variables. If predicted cosine similarities and true human scores move together in a straight-line fashion, Pearson will be high (close to 1). Mathematically:

$$r_P = \frac{\sum_{i=1}^{n}(x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^{n}(x_i - \bar{x})^2 \cdot \sum_{i=1}^{n}(y_i - \bar{y})^2}}$$

| Symbol | Meaning |
|---|---|
| $x_i$ | Predicted cosine similarity for pair $i$ |
| $y_i$ | Human-labelled similarity score (normalised) for pair $i$ |
| $\bar{x}, \bar{y}$ | Means of predicted and true scores |
| $n$ | Number of sentence pairs |

**Spearman correlation** measures the strength of the *rank-order* relationship — it does not care about the absolute values, only whether the model ranks pairs in the same order as the humans. It is computed as Pearson correlation applied to the *ranks* of $x$ and $y$ rather than the raw values, making it more robust to outliers.

**Dry-run on 4 pairs:**

```
Pair  | Human score (y) | Model cosine (x)
──────|─────────────────|─────────────────
  1   |       0.9       |       0.85
  2   |       0.6       |       0.60
  3   |       0.3       |       0.40
  4   |       0.1       |       0.15

Mean y = (0.9 + 0.6 + 0.3 + 0.1) / 4 = 0.475
Mean x = (0.85 + 0.60 + 0.40 + 0.15) / 4 = 0.50

Deviations:
  Pair 1: (y-ȳ) = 0.425,  (x-x̄) = 0.35   → product = 0.1488
  Pair 2: (y-ȳ) = 0.125,  (x-x̄) = 0.10   → product = 0.0125
  Pair 3: (y-ȳ) = -0.175, (x-x̄) = -0.10  → product = 0.0175
  Pair 4: (y-ȳ) = -0.375, (x-x̄) = -0.35  → product = 0.1313

Numerator   = 0.1488 + 0.0125 + 0.0175 + 0.1313 = 0.3101
Denominator = sqrt((0.425²+0.125²+0.175²+0.375²) × (0.35²+0.10²+0.10²+0.35²))
            = sqrt(0.3500 × 0.2650) = sqrt(0.0928) = 0.3046

Pearson r_P = 0.3101 / 0.3046 ≈ 0.982

Interpretation: Very high correlation — the model's rankings match human judgements almost perfectly.
```

The headline metric reported in this chapter is always `pearson_cosine` — the Pearson correlation computed using cosine similarity as the distance measure. This is both the most interpretable metric and the most commonly reported in the sentence-transformers literature.

### 5.2 MTEB — The Full Picture

While STSB is excellent for rapid iteration during development, it measures only one specific capability: semantic textual similarity on well-formed English sentences. A production embedding model is expected to perform well across a much wider range of tasks.

The **Massive Text Embedding Benchmark (MTEB)** was created precisely to address this. It spans 58 datasets covering 112 languages and evaluates embedding models on eight distinct task types: bitext mining, classification, clustering, pair classification, reranking, retrieval, semantic textual similarity, and summarisation. The MTEB leaderboard (hosted on HuggingFace) is the industry standard for comparing state-of-the-art embedding models.

```python
from mteb import MTEB

# Run a single MTEB task to check model quality on a specific downstream task
evaluation = MTEB(tasks=["Banking77Classification"])

# 'model' here is your trained SentenceTransformer
results = evaluation.run(model)

print("MTEB evaluation complete.")
print(f"Banking77Classification accuracy: {results}")
```

A full MTEB run across all 58 datasets can take many hours even on a modern GPU. The practical workflow is: use STSB as a fast in-training metric to track learning progress and tune hyperparameters; run MTEB once on your final model before publishing or deploying it to understand how it generalises across tasks. The book also recommends restarting the Jupyter kernel after a training run to free VRAM before running evaluation.

---

## 6. Loss Functions

The choice of loss function has a larger impact on embedding quality than almost any other hyperparameter. To see this concretely, all three loss functions in this section are trained with identical base models, identical training data, and identical hyperparameters — only the loss changes. The results speak clearly:

| Loss Function | Pearson Cosine (STSB val) |
|---|---|
| SoftmaxLoss (baseline) | 0.59 |
| CosineSimilarityLoss | 0.72 |
| MultipleNegativesRankingLoss | 0.80 |

Each subsequent loss is more directly aligned with the goal of producing good cosine-similarity-based embeddings, which is why performance improves monotonically.

### 6.1 Cosine Similarity Loss

The intuition behind **cosine similarity loss** is to train the model to directly match its predicted cosine similarity to a labelled similarity score. If the human label says two sentences are very similar (score 1.0) and the model produces an embedding pair with cosine similarity 0.3, the loss penalises this gap and the gradient pushes the embeddings closer together.

**The math.** Cosine similarity measures the angle between two vectors, ignoring their magnitudes. It is defined as the dot product of the vectors divided by the product of their norms:

$$\text{sim}_{\cos}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \cdot \|\mathbf{v}\|}$$

| Symbol | Meaning |
|---|---|
| $\mathbf{u}, \mathbf{v}$ | Two embedding vectors (each of shape $[d]$ where $d = 768$) |
| $\mathbf{u} \cdot \mathbf{v}$ | Dot product: $\sum_{i=1}^{d} u_i v_i$ |
| $\|\mathbf{u}\|$ | Euclidean norm: $\sqrt{\sum_{i=1}^{d} u_i^2}$ |

This says: *compute the cosine of the angle between the two vectors — 1.0 if they point in the same direction, 0.0 if perpendicular, −1.0 if opposite.*

The loss function then computes the mean squared error between the predicted cosine similarity and the target label:

$$\mathcal{L}_{\cos} = \frac{1}{N} \sum_{i=1}^{N} \left( \text{sim}_{\cos}(\mathbf{u}_i, \mathbf{v}_i) - y_i \right)^2$$

where $y_i \in [0, 1]$ is the labelled similarity (1.0 for entailment, 0.0 for contradiction).

**Dry-run with 2D vectors:**

```
Sentence pair: entailment → target label y = 1.0

Embeddings (simplified to 2D):
  u = [1.0, 0.0]   (embedding of premise)
  v = [0.6, 0.8]   (embedding of hypothesis)

Step 1: Dot product
  u · v = (1.0 × 0.6) + (0.0 × 0.8) = 0.60

Step 2: Norms
  ||u|| = sqrt(1.0² + 0.0²) = sqrt(1.00) = 1.00
  ||v|| = sqrt(0.6² + 0.8²) = sqrt(0.36 + 0.64) = sqrt(1.00) = 1.00

Step 3: Cosine similarity
  sim_cos(u, v) = 0.60 / (1.00 × 1.00) = 0.60

Step 4: Loss (MSE)
  L = (0.60 - 1.00)² = (-0.40)² = 0.16

Gradient interpretation: loss = 0.16 tells the model
  "these vectors need to be pulled closer together —
   their cosine similarity should be 1.0 but is only 0.60"
```

To use cosine similarity loss, the NLI dataset labels must be remapped from three classes to binary similarity scores. Entailment (label=0 in MNLI) becomes 1.0 (similar); both neutral (label=1) and contradiction (label=2) become 0.0 (dissimilar).

```python
from datasets import Dataset, load_dataset
from sentence_transformers import losses, SentenceTransformer
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments

# Load MNLI and remap labels: entailment=1.0, neutral/contradiction=0.0
raw_train = load_dataset("glue", "mnli", split="train").select(range(50_000))

# MNLI label encoding: 0=entailment, 1=neutral, 2=contradiction
label_mapping = {0: 1.0, 1: 0.0, 2: 0.0}

train_dataset = Dataset.from_dict({
    "sentence1": raw_train["premise"],
    "sentence2": raw_train["hypothesis"],
    "label": [float(label_mapping[lbl]) for lbl in raw_train["label"]]
})

print(f"Training set size: {len(train_dataset)}")
print("Label distribution after mapping:")
ones = sum(1 for l in train_dataset["label"] if l == 1.0)
zeros = len(train_dataset) - ones
print(f"  Positive pairs (entailment → 1.0): {ones}")
print(f"  Negative pairs (contradiction/neutral → 0.0): {zeros}")

# Fresh model, same evaluator as before
embedding_model = SentenceTransformer('bert-base-uncased')
val_sts = load_dataset("glue", "stsb", split="validation")
evaluator = EmbeddingSimilarityEvaluator(
    sentences1=val_sts["sentence1"],
    sentences2=val_sts["sentence2"],
    scores=[score / 5 for score in val_sts["label"]],
    main_similarity="cosine"
)

# Loss function
train_loss = losses.CosineSimilarityLoss(model=embedding_model)
print("Loss function: CosineSimilarityLoss")

# Training arguments
args = SentenceTransformerTrainingArguments(
    output_dir="cosinesimilarity_embedding_model",
    num_train_epochs=1,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    warmup_steps=100,
    fp16=True,
    eval_steps=100,
    logging_steps=100,
)

# Train
trainer = SentenceTransformerTrainer(
    model=embedding_model,
    args=args,
    train_dataset=train_dataset,
    loss=train_loss,
    evaluator=evaluator
)
trainer.train()

print("Cosine similarity loss result: pearson_cosine ≈ 0.72")
print("Improvement over softmax baseline: +0.13")
```

The result — `pearson_cosine = 0.72` — is a substantial improvement over the softmax baseline of 0.59. The reason is alignment: cosine loss trains the model *directly* to produce cosine similarities that match human scores, whereas softmax loss trains a multi-class classifier and only indirectly shapes the embedding space.

### 6.2 Multiple Negatives Ranking Loss

The **Multiple Negatives Ranking (MNR) Loss** — also known as **InfoNCE loss** or **NTXentLoss** in different parts of the literature — is the most powerful and widely used loss function for training embedding models today. It is the loss behind CLIP (OpenAI's image-text model from Chapter 9), modern dense retrieval models, and most state-of-the-art sentence transformers on the MTEB leaderboard.

The core idea is a reframing: instead of asking the model to *predict a similarity score*, ask it to *identify the correct match* from a set of candidates. Given an anchor sentence, a correct positive sentence, and several incorrect negative sentences, the model must rank the positive higher than all the negatives. This is a classification problem that we optimise with cross-entropy — but the classes are not fixed labels, they are determined dynamically from the batch.

**The math.** For an anchor $a$ and a batch of $N$ candidates where $p^+$ is the true positive and all others $p_j$ ($j \neq +$) are in-batch negatives:

$$\mathcal{L}_{\text{MNR}} = -\log \frac{\exp\!\left(\text{sim}(a,\, p^+) \,/\, \tau\right)}{\displaystyle\sum_{j=1}^{N} \exp\!\left(\text{sim}(a,\, p_j) \,/\, \tau\right)}$$

| Symbol | Meaning |
|---|---|
| $a$ | Anchor sentence embedding |
| $p^+$ | Positive sentence embedding (the true match) |
| $p_j$ | All $N$ candidate embeddings in the batch (positive + negatives) |
| $\text{sim}(\cdot, \cdot)$ | Cosine similarity |
| $\tau$ | Temperature hyperparameter (controls sharpness of softmax; typically 0.05–0.1) |

This says: *apply a softmax over all pairwise similarities in the batch; the loss is the negative log-probability assigned to the true positive.* If the model assigns high similarity to the correct positive and low similarity to all negatives, the softmax puts most probability mass on the positive, the negative log is small, and the loss is low. If the model is confused, probability is spread across many candidates, and the loss is high.

**Dry-run with batch size $N = 3$:**

```
Batch contains:
  A1 (anchor):   "How many people live in Amsterdam?"
  P1 (positive): "Almost a million people live in Amsterdam"   ← correct pair
  P2 (negative): "He was waiting in line for the bus"          ← in-batch neg
  P3 (negative): "The capital of the Netherlands is Amsterdam" ← in-batch neg

Model's predicted cosine similarities (with τ = 1 for simplicity):
  sim(A1, P1) = 0.92   ← high: both talk about Amsterdam population
  sim(A1, P2) = 0.11   ← low: unrelated
  sim(A1, P3) = 0.65   ← medium: topically related but not the answer

Step 1: Exponentiate (with τ = 1, so just e^x)
  exp(0.92) = 2.509
  exp(0.11) = 1.116
  exp(0.65) = 1.916

Step 2: Sum
  denominator = 2.509 + 1.116 + 1.916 = 5.541

Step 3: Probability of the correct positive (P1)
  P(P1 | A1) = 2.509 / 5.541 = 0.453

Step 4: Loss
  L = -log(0.453) = 0.793

Interpretation: The model assigned 45.3% probability to the correct
positive. Loss of 0.793 drives the model to push this toward 100%
by increasing sim(A1, P1) and decreasing sim(A1, P2) and sim(A1, P3).
```

**Why batch size matters.** With $N = 3$ above, the model had only 2 negatives to distinguish from. With batch size 32, there are 31 negatives per anchor. With batch size 256, there are 255. A larger batch makes the classification task harder — the model must learn finer and finer distinctions between the correct positive and many plausible-looking negatives. This is why MNR loss is unusual in that *increasing batch size improves model quality*, not just training speed. For embedding training, use the largest batch size your VRAM allows.

**The three types of negatives.** The quality of negatives matters as much as their quantity. The book distinguishes three tiers:

*Easy negatives* are generated by random sampling from the corpus. They are completely unrelated to the query, making the classification task trivial for a halfway-competent model. For our Amsterdam example, "He was waiting in line for the bus" is an easy negative — no model even slightly trained on language would confuse it with the correct answer.

*Semi-hard negatives* are topically related but not the correct answer. "The capital of the Netherlands is Amsterdam" mentions Amsterdam and the Netherlands, making it superficially similar to the query, but it does not answer the question about population. You can generate semi-hard negatives using a pre-trained embedding model to find sentences that are nearby in vector space but not the true positive.

*Hard negatives* are very similar to the correct answer but subtly wrong — the most informative training signal. "A million people live in Utrecht, which is more than in Amsterdam" uses almost identical vocabulary and structure but gives the wrong city. Hard negatives require either human labelling or a strong generative model to create. They push the embedding model to capture subtle factual distinctions rather than just topic similarity.

```
Question: "How many people live in Amsterdam?"
Answer:   "Almost a million people live in Amsterdam"

Easy negative:     "He was waiting in line for the bus"
                   → completely unrelated, trivially rejected

Semi-hard negative: "The capital of the Netherlands is Amsterdam"
                   → topically related, moderately hard

Hard negative:     "A million people live in Utrecht, which is
                    more than in Amsterdam"
                   → very similar wording, factually wrong city
```

In-batch negatives (used in the book's implementation) are effectively easy-to-medium negatives — they are other positive pairs from the same training batch, randomly assorted. This is sufficient to achieve strong results without the overhead of mining hard negatives.

```python
import random
from tqdm import tqdm
from datasets import Dataset, load_dataset
from sentence_transformers import losses, SentenceTransformer
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments

# Load MNLI and keep only entailment pairs (label=0)
# These become our (anchor, positive) pairs
mnli = load_dataset("glue", "mnli", split="train").select(range(50_000))
mnli_entailment = mnli.filter(lambda x: x["label"] == 0)
print(f"Entailment-only subset: {len(mnli_entailment)} pairs")
# → ~16,875 pairs (roughly 1/3 of 50k, as expected for balanced 3-class data)

# Generate in-batch negatives by shuffling the hypotheses
# Each anchor is paired with: its correct hypothesis (positive)
# and a randomly shuffled hypothesis from another row (negative)
soft_negatives = mnli_entailment["hypothesis"].copy()
random.shuffle(soft_negatives)

train_data = {"anchor": [], "positive": [], "negative": []}

for row, soft_neg in tqdm(zip(mnli_entailment, soft_negatives),
                          total=len(mnli_entailment)):
    train_data["anchor"].append(row["premise"])
    train_data["positive"].append(row["hypothesis"])
    train_data["negative"].append(soft_neg)

train_dataset = Dataset.from_dict(train_data)
print(f"Training triplets created: {len(train_dataset)}")

# Fresh base model and same evaluator
embedding_model = SentenceTransformer('bert-base-uncased')
val_sts = load_dataset("glue", "stsb", split="validation")
evaluator = EmbeddingSimilarityEvaluator(
    sentences1=val_sts["sentence1"],
    sentences2=val_sts["sentence2"],
    scores=[score / 5 for score in val_sts["label"]],
    main_similarity="cosine"
)

# MNR loss — takes (anchor, positive, negative) triplets
train_loss = losses.MultipleNegativesRankingLoss(model=embedding_model)
print("Loss function: MultipleNegativesRankingLoss (InfoNCE / NTXentLoss)")

args = SentenceTransformerTrainingArguments(
    output_dir="mnr_loss_embedding_model",
    num_train_epochs=1,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    warmup_steps=100,
    fp16=True,
    eval_steps=100,
    logging_steps=100,
)

trainer = SentenceTransformerTrainer(
    model=embedding_model,
    args=args,
    train_dataset=train_dataset,
    loss=train_loss,
    evaluator=evaluator
)

trainer.train()

print("MNR loss result: pearson_cosine ≈ 0.80")
print("Improvement over cosine loss: +0.08")
print("Total improvement over softmax baseline: +0.21")
```

The final result — `pearson_cosine = 0.80` — is a significant step up from the cosine loss (0.72) and a dramatic improvement over the softmax baseline (0.59). MNR loss achieves this despite training on fewer examples (only the ~16,875 entailment pairs versus the full 50,000 used for softmax and cosine loss), which underlines how much the loss function's inductive bias matters.

### 6.3 Which Loss to Use

The three loss functions occupy distinct niches, and choosing between them is straightforward once you understand their data requirements.

`SoftmaxLoss` is the right choice when your training data has multi-class relationship labels (entailment / neutral / contradiction or a similar scheme). It trains a multi-class classifier on top of the embedding and is a solid baseline, but it never directly optimises for cosine similarity.

`CosineSimilarityLoss` is the right choice when your training data has continuous similarity scores between 0 and 1 — for example, human-annotated pairs from a crowdsourcing platform, or pairs derived from user click behaviour with soft scores. It directly optimises the metric you care about and is easy to understand.

`MultipleNegativesRankingLoss` is the right choice when you only have positive pairs — question-answer pairs, premise-entailment pairs, parallel translations. It generates negatives implicitly from the batch and is the industry default for training modern embedding models. Its main requirement is that you use a sufficiently large batch size (ideally 64–256) so that the in-batch negatives are informative. The book notes that SBERT's original 2019 paper used softmax loss; by 2023, MNR loss had become standard.

---

## 7. Fine-Tuning an Embedding Model

Training an embedding model from scratch — as we did in Section 4 — is powerful but expensive. It requires substantial data, GPU time, and careful hyperparameter tuning to produce a model that is competitive with state-of-the-art embeddings. The `sentence-transformers` framework offers a far more practical path: take a model that has already been trained on billions of sentence pairs and fine-tune it on your specific data or domain. This approach reaches higher performance faster and requires far less data.

There are two main fine-tuning strategies: **supervised fine-tuning**, which adapts a pre-trained embedding model using labelled sentence pairs, and **Augmented SBERT**, which dramatically extends a small labelled dataset using a cross-encoder to generate synthetic labels.

### 7.1 Supervised Fine-Tuning

#### The Intuition — A Chef Analogy

Imagine you want to hire a chef for your restaurant. You have two options.

**Option A — Train from scratch:** Hire someone with zero cooking experience and teach them everything from the ground up. Slow, expensive, needs months of training before they can handle a full menu.

**Option B — Fine-tune:** Hire a professional chef who already knows how to cook at a high level. Then spend a week teaching them *your specific restaurant's menu*. They already have all the foundational skills; you are just narrowing their focus to your context.

Fine-tuning in machine learning is Option B. Instead of starting from `bert-base-uncased` — a model that only understands general language, not sentence similarity — we start from `all-MiniLM-L6-v2`, a model that has *already been trained* to produce good sentence embeddings on hundreds of millions of sentence pairs. We then continue training it on our MNLI data to nudge it further toward our specific task.

#### How It Differs from Training from Scratch

The table below makes the difference concrete:

| | Training from Scratch (Sections 4–6) | Supervised Fine-Tuning (Section 7.1) |
|---|---|---|
| **Starting point** | `bert-base-uncased` — general language model, knows grammar, knows nothing about sentence similarity | `all-MiniLM-L6-v2` — already a strong sentence encoder, trained on massive data |
| **What it already knows** | Nothing about embeddings | A lot — can already cluster similar sentences meaningfully |
| **Training data needed** | Tens of thousands of pairs minimum | Much less — good foundations are already in place |
| **Code difference** | `SentenceTransformer('bert-base-uncased')` | `SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')` |

That is the remarkable thing — in the code, the *only change* is the model name on one line. Everything else — the loss function, training arguments, evaluator, data — is completely identical.

#### A Concrete Example

Take these two sentences:

- *"The dog ran across the park."*
- *"A puppy sprinted through the garden."*

**`bert-base-uncased` before embedding training** has no concept that these are similar. It just knows words. Its embeddings for both sentences might land in random, distant places in vector space — even though they mean nearly the same thing.

**`all-MiniLM-L6-v2` before any fine-tuning** has already learned from hundreds of millions of examples that dogs and puppies are related, that "ran" and "sprinted" are synonyms, that parks and gardens are similar. Its embeddings for those two sentences are *already close together* in vector space — maybe cosine similarity of 0.89 — before we have done any training at all.

When we fine-tune, we are saying: *"You are already great at this. Now please also pay specific attention to this particular dataset and get slightly more calibrated on it."*

#### The Code

The book recommends `all-MiniLM-L6-v2` as a strong default: it performs well across many use cases and, at 22M parameters (compared to BERT-base's 110M), is small enough for fast inference. We use the same MNLI data and MNR loss from Section 6.2.

```python
from datasets import load_dataset
from sentence_transformers import losses, SentenceTransformer
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments

# Load MNLI data (same setup as Section 6.2)
train_dataset = load_dataset("glue", "mnli", split="train").select(range(50_000))
train_dataset = train_dataset.remove_columns("idx")

val_sts = load_dataset('glue', 'stsb', split='validation')
evaluator = EmbeddingSimilarityEvaluator(
    sentences1=val_sts["sentence1"],
    sentences2=val_sts["sentence2"],
    scores=[score/5 for score in val_sts["label"]],
    main_similarity="cosine"
)

# THE ONLY CHANGE from Section 6.2: a pre-trained embedding model
# instead of bert-base-uncased
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

train_loss = losses.MultipleNegativesRankingLoss(model=embedding_model)

args = SentenceTransformerTrainingArguments(
    output_dir="finetuned_embedding_model",
    num_train_epochs=1,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    warmup_steps=100,
    fp16=True,
    eval_steps=100,
    logging_steps=100,
)

trainer = SentenceTransformerTrainer(
    model=embedding_model,
    args=args,
    train_dataset=train_dataset,
    loss=train_loss,
    evaluator=evaluator
)
trainer.train()

# Evaluate fine-tuned model
evaluator(embedding_model)
# → pearson_cosine ≈ 0.85

# Also evaluate the ORIGINAL model with no fine-tuning
original = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
evaluator(original)
# → pearson_cosine ≈ 0.87  ← the original scores HIGHER than the fine-tuned!
```

#### The Counter-Intuitive Result — Why Did Fine-Tuning Make It Worse?

```
all-MiniLM-L6-v2  (no fine-tuning)    →  pearson_cosine = 0.87  ← higher
all-MiniLM-L6-v2  (fine-tuned by us)  →  pearson_cosine = 0.85  ← lower
```

This seems wrong. We gave it more training. It should be better. The reason it is worse is subtle and important.

`all-MiniLM-L6-v2` was originally trained on the *complete* MNLI dataset — all 392,702 sentence pairs, plus many other datasets. Our fine-tuning exposed it to only 50,000 pairs — just 13% of what it already knew from MNLI. So instead of teaching it something *new*, we essentially made the professional chef re-read two chapters of a textbook they had already memorised cover to cover. Their knowledge became slightly *narrower*, not broader.

This effect is known informally as **distribution shift** — the fine-tuning distribution (50k pairs, MNLI only) is a narrow slice of the model's original training distribution. The model partially overwrites its broad, balanced knowledge with this narrower slice. The result is a slight drop in performance on a broad benchmark like STSB.

*Note: you may sometimes see this called catastrophic forgetting in the literature — though that term usually refers to more severe cases.*

#### When Does Fine-Tuning Actually Help?

Fine-tuning delivers its greatest value when your data is **genuinely different** from what the pre-trained model has seen. The rule of thumb is simple:

> **Fine-tune when you have domain-specific data the model has never seen. Do not fine-tune on a subset of the model's own training data — that almost always hurts.**

A real-world example where fine-tuning would clearly win: suppose you work at a hospital and need an embedding model for medical records. Terms like *"MI"* (myocardial infarction), *"PRN"* (as needed), and *"CABG"* (coronary artery bypass graft) appear constantly. `all-MiniLM-L6-v2` has seen very little medical text. It may not know that *"The patient had an MI"* and *"The patient suffered a heart attack"* should be close in embedding space.

If you fine-tune it on medical sentence pairs, the model learns domain-specific similarity it genuinely did not have. Now fine-tuning *helps*, because the new data is *new knowledge*.

The book also points to a complementary strategy when your domain vocabulary is very specialised: first run **masked language modelling (MLM)** on your domain corpus to teach the model your domain's vocabulary and phrasing, then use that domain-adapted BERT as the backbone for SBERT fine-tuning. This is called **adaptive pre-training** and is the basis for the domain adaptation pipeline discussed in Section 8.2.

### 7.2 Augmented SBERT

#### The Problem — You Never Have Enough Labels

Embedding models like `all-MiniLM-L6-v2` were trained on over a billion sentence pairs. Most organisations have a few thousand labelled examples at best. That is a gap of six orders of magnitude. You cannot train a competitive model from scratch with 10,000 pairs, and even fine-tuning struggles when the data is too thin.

The natural instinct is: *"Can we somehow generate more labelled data automatically?"* Augmented SBERT is the answer to that question.

#### The Intuition — A Teacher and a Teaching Assistant

Imagine a school with 10,000 graded essays (the gold dataset). A teacher marked each one by hand — slow, expensive, accurate. You want to train a fast teaching assistant (the bi-encoder) to grade essays quickly at scale.

Here is the trick: instead of the TA learning only from the 10,000 hand-graded essays, you first teach the teacher to grade *automatically*, then let the teacher grade 40,000 more essays. These auto-graded essays are not perfect — the teacher makes occasional mistakes — but they are good enough. Now the TA learns from all 50,000 graded essays and becomes far more capable than if it had only seen the original 10,000.

In Augmented SBERT:
- The **teacher** is the **cross-encoder** — accurate but slow, cannot produce standalone embeddings
- The **teaching assistant** is the **bi-encoder (SBERT)** — fast, produces embeddings, deployed at inference
- The **10,000 hand-graded essays** are the **gold dataset** — ground truth, human-labelled
- The **40,000 auto-graded essays** are the **silver dataset** — machine-labelled by the cross-encoder, approximate but useful

#### Gold vs Silver — What Do These Terms Mean?

These two words appear throughout the NLP literature and are worth understanding clearly.

A **gold dataset** is small, hand-labelled by humans, and represents ground truth. Every label can be fully trusted. It is expensive to create — human annotation takes time and money.

A **silver dataset** is large, labelled automatically by a model (here, the cross-encoder). The labels are not ground truth — they are the model's best guess. Some labels will be wrong. But they are close enough to the truth to be genuinely useful for training. The term "silver" captures this: valuable, but not as pure as gold.

```
GOLD  ✓  Small, human-labelled, ground truth, expensive to create
          "The dog ran in the park" / "A puppy sprinted in the garden" → 1 (similar)

SILVER ~  Large, machine-labelled, approximate, cheap to generate
          "Stock markets fell sharply" / "Equities declined today" → 1 (predicted)
```

#### The Full Pipeline (Figure 10-12 from the Book)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AUGMENTED SBERT PIPELINE                         │
└─────────────────────────────────────────────────────────────────────┘

 ┌──────────────────────┐          ┌──────────────────────────────┐
 │   GOLD DATASET       │          │   UNLABELLED DATASET         │
 │   10,000 pairs       │          │   40,000 sentence pairs      │
 │   ✓ Human-labelled   │          │   (no labels yet)            │
 │   ✓ Ground truth     │          │   Raw text from your domain  │
 └──────────┬───────────┘          └──────────────┬───────────────┘
            │                                     │
            │  Step 1: Train                      │  Step 2: Feed in
            ▼                                     │
   ┌─────────────────────┐                        │
   │    CROSS-ENCODER    │◄───────────────────────┘
   │    (BERT-based)     │
   │                     │   Step 3: Predict label for each pair
   │  Sees both          │──────────────────────────────────────►
   │  sentences at once  │
   │  Very accurate      │         ┌──────────────────────────────┐
   │  Slow (~50M pairs   │         │   SILVER DATASET             │
   │  = hours)           │         │   40,000 pairs               │
   └─────────────────────┘         │   ~ Machine-labelled         │
                                   │   ~ Approximate but useful   │
                                   └──────────────┬───────────────┘
                                                  │
            ┌─────────────────────────────────────┘
            │   Gold (10k) + Silver (40k) = ~50k combined pairs
            │
            │  Step 4: Train bi-encoder
            ▼
   ┌─────────────────────┐
   │   BI-ENCODER (SBERT)│
   │   Fast at inference │
   │   Produces embeddings│
   │   Deployed in prod  │
   └─────────────────────┘

Final score: pearson_cosine = 0.71
(vs 0.72 from training on 50k FULL human labels — nearly identical, using only 20% real labels)
```

#### What Happens to Each Model — The Critical Detail

This is the part that trips most people up when they first see Augmented SBERT. There are **two training jobs** and they have completely different fates.

| | Cross-Encoder | Bi-Encoder (SBERT) |
|---|---|---|
| **Starts as** | `bert-base-uncased` (plain BERT) | `bert-base-uncased` (plain BERT) |
| **Trained on** | 10,000 gold pairs (human labels) | ~50,000 pairs (gold + silver) |
| **Purpose** | Generate silver labels | Learn to produce good embeddings |
| **Used at inference?** | **NO — discarded after Step 3** | **YES — the only deployed model** |
| **Speed** | Slow — sees both sentences at once | Fast — processes sentences independently |

The cross-encoder is a **temporary labelling tool**. The moment it finishes predicting labels on the unlabelled data (Step 3), its job is done. It is discarded completely. It does not sit in the background. It does not help at inference time. Think of it like a consultant hired for one week to write a training manual — once the manual is done, the consultant leaves. Your permanent employees (the bi-encoder) use the manual to do the actual daily work.

#### Why Not Just Use the Cross-Encoder at Inference? It Is More Accurate.

This is a fair question. If the cross-encoder is more accurate, why not deploy it instead and get better results?

The answer is the same scaling problem we saw in Section 3 with SBERT. For a real database of 1 million documents, every search query needs to compare against every document:

```
Cross-encoder at inference (1 million documents):
  1 query × 1,000,000 documents = 1,000,000 forward passes
  Each pass: 10ms
  Total time per search: 10,000 seconds ≈ 2.8 hours per query

Bi-encoder at inference (1 million documents):
  Index all docs once → store 1M embeddings (done offline)
  1 query → embed once → fast vector search
  Total time per search: ~10 milliseconds
```

The cross-encoder's accuracy is real, but it comes at $O(n)$ cost per query where $n$ is your corpus size. For any production search system, this is completely unusable. The bi-encoder lookup is effectively $O(1)$ once documents are indexed.

Augmented SBERT is clever precisely *because* it separates these two concerns: it uses the cross-encoder's accuracy **during training** (offline, one-time, slow is fine) while shipping the bi-encoder **at inference** (online, runs millions of times, must be fast).

```
TRAINING TIME  (offline, done once, slow is acceptable):
───────────────────────────────────────────────────────
  Gold data → [Cross-Encoder trains] → labels 40k pairs → Silver data
                                                                │
  Gold + Silver ──────────────────────► [Bi-Encoder trains]
                                                                │
                                                                ▼
INFERENCE TIME  (online, runs per query, must be milliseconds):
───────────────────────────────────────────────────────────────
  User query → [Bi-Encoder only] → embedding → vector search → results

  Cross-encoder is NOT HERE. It was discarded after training.
```

#### A Small Concrete Walkthrough

Let us trace through the entire pipeline with three tiny examples to make it completely concrete.

**Your gold data** (3 pairs a human labelled by hand):

```
Pair 1: "The cat sat on the mat"          → label 1 (similar)
        "A kitten rested on the rug"

Pair 2: "It was raining heavily outside"  → label 1 (similar)
        "The weather was terrible today"

Pair 3: "She loves eating pizza"          → label 0 (dissimilar)
        "He hates broccoli"
```

**Step 1** — Train the cross-encoder on these 3 examples. It learns: paraphrases and synonyms are similar (pairs 1, 2); topic-unrelated pairs are dissimilar (pair 3).

**Your unlabelled data** (3 new pairs with no labels):

```
Pair A: "The dog ran in the park"
        "A puppy sprinted through the garden"    → ??? (no human label)

Pair B: "Stock market crashed today"
        "She loves pizza"                        → ??? (no human label)

Pair C: "I enjoy reading books"
        "Reading is my hobby"                    → ??? (no human label)
```

**Step 2+3** — The cross-encoder reads both sentences of each pair simultaneously and predicts:

```
Pair A → P(similar) = 0.91  →  assigned label 1  ✓ (correct — they are paraphrases)
Pair B → P(similar) = 0.03  →  assigned label 0  ✓ (correct — completely unrelated)
Pair C → P(similar) = 0.88  →  assigned label 1  ✓ (correct — same meaning)
```

These 3 machine-generated labels are the **silver dataset**. Some predictions will be wrong in the real 40,000-pair version — but most will be correct because the cross-encoder is a strong model.

**Step 4** — The bi-encoder trains on all 6 pairs: 3 gold + 3 silver. It now has 2× the training signal compared to gold alone, at zero additional human labelling cost.

#### Step-by-Step Code

**Step 1 — Train the cross-encoder on the gold dataset**

```python
import pandas as pd
from tqdm import tqdm
from datasets import load_dataset, Dataset
from sentence_transformers import InputExample
from sentence_transformers.datasets import NoDuplicatesDataLoader
from sentence_transformers.cross_encoder import CrossEncoder

# Gold dataset: first 10,000 MNLI pairs — our small, fully-trusted ground truth
dataset = load_dataset("glue", "mnli", split="train").select(range(10_000))
mapping = {2: 0, 1: 0, 0: 1}  # entailment → 1 (similar), neutral/contradiction → 0

gold_examples = [
    InputExample(texts=[row["premise"], row["hypothesis"]], label=mapping[row["label"]])
    for row in tqdm(dataset)
]
gold_dataloader = NoDuplicatesDataLoader(gold_examples, batch_size=32)

# Also store as DataFrame — needed when combining with silver later
gold = pd.DataFrame({
    "sentence1": dataset["premise"],
    "sentence2": dataset["hypothesis"],
    "label": [mapping[label] for label in dataset["label"]]
})

print(f"Gold dataset: {len(gold)} hand-labelled pairs")

# Train cross-encoder on gold data
# CrossEncoder processes BOTH sentences at once — more accurate than bi-encoder
cross_encoder = CrossEncoder("bert-base-uncased", num_labels=2)
cross_encoder.fit(
    train_dataloader=gold_dataloader,
    epochs=1,
    show_progress_bar=True,
    warmup_steps=100,
    use_amp=False
)
print("Cross-encoder trained. It can now predict labels for new unlabelled pairs.")
```

**Step 2 — Collect the unlabelled sentence pairs**

```python
# In a real project: these would be raw documents from your target domain
# Here we simulate by using MNLI rows 10k–50k (pretending they have no labels)
silver_raw = load_dataset("glue", "mnli", split="train").select(range(10_000, 50_000))
pairs = list(zip(silver_raw["premise"], silver_raw["hypothesis"]))

print(f"Unlabelled pairs ready for cross-encoder: {len(pairs)}")
```

**Step 3 — Auto-label the silver pairs with the cross-encoder**

```python
import numpy as np

# cross_encoder.predict() sees both sentences simultaneously
# apply_softmax=True → output is [P(not-similar), P(similar)] for each pair
output = cross_encoder.predict(pairs, apply_softmax=True, show_progress_bar=True)

# np.argmax picks the class with the higher probability: 0 or 1
silver = pd.DataFrame({
    "sentence1": silver_raw["premise"],
    "sentence2": silver_raw["hypothesis"],
    "label": np.argmax(output, axis=1)
})

print(f"Silver dataset created: {len(silver)} auto-labelled pairs")
print("These labels are predictions — not ground truth — but good enough to be useful.")
```

**Step 4 — Train the bi-encoder on gold + silver combined**

```python
from sentence_transformers import losses, SentenceTransformer
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments

# Combine gold + silver, remove any duplicate sentence pairs
data = pd.concat([gold, silver], ignore_index=True, axis=0)
data = data.drop_duplicates(subset=["sentence1", "sentence2"], keep="first")
train_dataset = Dataset.from_pandas(data, preserve_index=False)

print(f"Combined training set: {len(train_dataset)} pairs")
print(f"  - Gold (ground truth):  10,000 pairs (20%)")
print(f"  - Silver (auto-labelled): ~40,000 pairs (80%)")

val_sts = load_dataset("glue", "stsb", split="validation")
evaluator = EmbeddingSimilarityEvaluator(
    sentences1=val_sts["sentence1"],
    sentences2=val_sts["sentence2"],
    scores=[score/5 for score in val_sts["label"]],
    main_similarity="cosine"
)

embedding_model = SentenceTransformer("bert-base-uncased")
train_loss = losses.CosineSimilarityLoss(model=embedding_model)

args = SentenceTransformerTrainingArguments(
    output_dir="augmented_embedding_model",
    num_train_epochs=1,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    warmup_steps=100,
    fp16=True,
    eval_steps=100,
    logging_steps=100,
)

trainer = SentenceTransformerTrainer(
    model=embedding_model,
    args=args,
    train_dataset=train_dataset,
    loss=train_loss,
    evaluator=evaluator
)
trainer.train()

print("Result: pearson_cosine ≈ 0.71")
```

#### The Ablation — Proving Silver Data Actually Helps

An **ablation study** removes one component to see how much it contributes. Here we train on gold data *only* and compare the score.

```python
# Ablation: gold only (same setup, no silver)
gold_only_data = Dataset.from_pandas(gold, preserve_index=False)

embedding_model_gold_only = SentenceTransformer("bert-base-uncased")
train_loss_gold_only = losses.CosineSimilarityLoss(model=embedding_model_gold_only)

args_gold_only = SentenceTransformerTrainingArguments(
    output_dir="gold_only_embedding_model",
    num_train_epochs=1,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    warmup_steps=100,
    fp16=True,
    eval_steps=100,
    logging_steps=100,
)

trainer_gold_only = SentenceTransformerTrainer(
    model=embedding_model_gold_only,
    args=args_gold_only,
    train_dataset=gold_only_data,
    loss=train_loss_gold_only,
    evaluator=evaluator
)
trainer_gold_only.train()

print("Gold-only result: pearson_cosine lower than 0.71")
print("→ The silver data added real signal, not just noise.")
```

#### Why This Result Is So Impressive

The numbers from this chapter tell a striking story:

```
Cosine loss on FULL 50k human labels      →  pearson_cosine = 0.72
Augmented SBERT on 10k gold + 40k silver  →  pearson_cosine = 0.71
Gold only (10k labels, no silver)         →  pearson_cosine < 0.71
```

Using only **20% real human labels**, Augmented SBERT matches 99% of the performance of fully supervised training with 100% labels. The cross-encoder-generated silver labels are imperfect, but they are close enough to the truth that the bi-encoder learns almost as well as if everything had been labelled by hand. This is the core value proposition: you can multiply your labelled data by 5× at near-zero cost by using a cross-encoder as an automatic annotator.

---

## 8. Unsupervised Learning — TSDAE

All methods discussed so far require labelled data — either human-annotated NLI pairs (Sections 4–6) or at least a small gold set (Augmented SBERT in Section 7.2). But what if you have *no labels at all*? What if you have only raw sentences from your domain?

Several unsupervised techniques exist for this scenario, including SimCSE, Contrastive Tension (CT), and Generative Pseudo-Labeling (GPL). The book focuses on **TSDAE** — Transformer-based Sequential Denoising Auto-Encoder — because it has shown particularly strong performance on unsupervised tasks and serves as a foundation for domain adaptation.

### 8.1 The Core Idea: Denoising as Self-Supervision

#### Encoder and Decoder — What These Words Mean in AI

Before understanding TSDAE, you need to understand what an **encoder** and a **decoder** are, because these two words appear constantly in AI and mean slightly different things in different contexts.

Think of a **newspaper summariser** and a **newspaper reconstructor** working together. The summariser reads a long 500-word article and writes a 3-line summary — all the meaning of the article compressed into three sentences. The reconstructor takes only that 3-line summary and tries to write the full 500-word article back. It cannot look at the original — only the summary.

In machine learning, the encoder is the summariser and the decoder is the reconstructor:

```
Rich input  →  [ENCODER]  →  Compressed representation  →  [DECODER]  →  Output
500 words          ↓               3-line summary               ↓         500 words
              (compresses)        (the "bottleneck")         (expands)  (reconstruction)
```

The compressed middle part is called the **bottleneck**. The bottleneck is what makes the whole thing work — by forcing the encoder to squeeze meaning into a small space, you ensure it learns to represent the input efficiently rather than just memorising it.

Different AI models use encoders and decoders differently:

| Model family | Uses | Examples | Task |
|---|---|---|---|
| Encoder-only | Compress, never generate | BERT | Understanding text, producing embeddings |
| Decoder-only | Generate, no compression step | GPT | Generating text token by token |
| Encoder-decoder | Both together | T5, BART | Translation, summarisation |

BERT is an encoder-only model. It reads text and produces dense vector representations — it never generates new text. That is exactly the component TSDAE uses as its encoder.

#### What BERT Actually Does Inside

When you give BERT a sentence, it does not process words whole — it tokenises the sentence into subword pieces first. Then something important happens before any processing: BERT automatically adds a special token called **[CLS]** at the very beginning of every input sequence. This is not a real word — it is a dedicated placeholder that BERT was designed to use.

Using our TSDAE example with the damaged sentence:

```
Input: "capital Netherlands Amsterdam"

After tokenisation + [CLS] insertion:
  [[CLS], "capital", "Netherlands", "Amsterdam"]   ← 4 tokens now
     ↑
     not a real word — a special marker added automatically
```

Each of these 4 tokens gets looked up in BERT's embedding table and becomes a vector of 768 numbers. These 4 vectors then flow through **12 transformer layers**. Inside each layer, **self-attention** runs — every token looks at every other token and updates its own vector based on what it finds. After all 12 layers, BERT outputs one 768-dimensional vector for *each* input token:

```
Input:   [[CLS], "capital", "Netherlands", "Amsterdam"]   ← 4 tokens in

         [12 Transformer Layers — self-attention at each layer]

Output:  4 vectors out, one per token, each 768 numbers:

  [CLS]         →  [0.71, -0.23, 0.88, ..., 0.04]
  "capital"     →  [0.12,  0.55, 0.33, ..., 0.91]
  "Netherlands" →  [-0.44, 0.67, 0.21, ..., 0.38]
  "Amsterdam"   →  [0.95, -0.11, 0.74, ..., 0.62]
```

These output vectors are nothing like the raw embeddings that went in. After 12 layers of self-attention, each vector has absorbed context from every other token. The output vector for "capital" now knows about "Netherlands" and "Amsterdam" — it has full sentence context baked in.

#### What Is [CLS] and Why Is It Special?

Here is the question: BERT outputs 4 vectors — one per token — but for sentence embedding you need **one** single vector for the whole sentence. Which of the 4 do you use?

The [CLS] token was designed specifically for this. During BERT's pre-training, [CLS] was placed at position 0 of every single input. It had no word-level task — it was not predicting a masked word or representing a real concept. Its only job was to sit at the front and attend to every other token through self-attention at every layer.

Think of [CLS] as a **meeting secretary**. Every token in the sentence is a team member presenting their update. The secretary sits in every meeting, listens to everyone, and by the end holds a full summary of the entire discussion — while each team member's notes only cover their own part.

```
Layer 1 self-attention:
  [CLS] attends to "capital"      → absorbs some of its meaning
  [CLS] attends to "Netherlands"  → absorbs some of its meaning
  [CLS] attends to "Amsterdam"    → absorbs some of its meaning

Layer 2 self-attention:
  [CLS] attends to already-updated token vectors → absorbs richer combined meaning

... 12 layers later ...

[CLS] output vector = a holistic summary of the entire sentence
```

BERT was also trained with a task called **Next Sentence Prediction (NSP)** — given two sentences, predict whether they follow each other — using only the [CLS] vector to make that decision. This specifically trained [CLS] to carry sentence-level meaning rather than word-level meaning.

#### What Is Pooling?

You now have 4 output vectors from BERT but need exactly 1 for the sentence embedding. **Pooling** is the strategy for collapsing many vectors into one.

**[CLS] Pooling** — take the [CLS] token's output vector and use it as the sentence embedding. Discard all the other token vectors.

```
BERT output vectors (using tiny 4-dim for clarity):
  [CLS]         →  [0.71, -0.23, 0.88, 0.04]   ← KEEP THIS
  "capital"     →  [0.12,  0.55, 0.33, 0.91]   ← discard
  "Netherlands" →  [-0.44, 0.67, 0.21, 0.38]   ← discard
  "Amsterdam"   →  [0.95, -0.11, 0.74, 0.62]   ← discard

Sentence embedding = [0.71, -0.23, 0.88, 0.04]
```

**Mean Pooling** — compute the element-wise average of all 4 token vectors:

```
Average each position across all 4 vectors:
  position 0: (0.71 + 0.12 + (-0.44) + 0.95) / 4 = 0.335
  position 1: (-0.23 + 0.55 + 0.67 + (-0.11)) / 4 = 0.220
  position 2: (0.88 + 0.33 + 0.21 + 0.74) / 4    = 0.540
  position 3: (0.04 + 0.91 + 0.38 + 0.62) / 4    = 0.488

Sentence embedding = [0.335, 0.220, 0.540, 0.488]
```

Both strategies produce one vector. But they carry very different information — and in TSDAE, the choice matters critically.

#### The TSDAE Training Loop

The intellectual root of TSDAE is the **denoising autoencoder**, a classical idea: corrupt an input and train the model to reconstruct the original. If the model learns to undo the corruption, it must have learned a useful representation of the underlying structure.

In TSDAE, the corruption is *random token deletion* at a 60% rate. The damaged sentence goes through the encoder and the resulting single vector is handed to the decoder. The decoder's only job is to reconstruct the original sentence, word by word, from that one vector:

```
Original:  "The capital of the Netherlands is Amsterdam"   (8 words)
                              │
               Delete 60% of tokens randomly
                              │
Damaged:   "capital Netherlands Amsterdam"                 (3 words)
                              │
                        [BERT Encoder]
                   (12 transformer layers)
                              │
                        [CLS Pooling]
                              │
              [0.71, -0.23, 0.88, ..., 0.04]   ← 768 numbers (the bottleneck)
                              │
                    [Decoder receives ONLY this]
                              │
             Predicts word by word:
               "The" → "capital" → "of" → "the" → "Netherlands" → "is" → "Amsterdam"
                              │
              Compare prediction to original → compute loss
                              │
              Gradient flows back: Decoder → bottleneck → Encoder
              Encoder updates: pack more meaning into those 768 numbers
```

The critical point is that the decoder receives **nothing else** — not the original sentence, not the damaged sentence, not the token positions. Only those 768 numbers. If those 768 numbers are vague or information-poor, the decoder cannot reconstruct, the loss is high, and the gradient forces the encoder to do better. This is **self-supervision**: the reconstruction task itself generates the training signal, with no human labels required.

After training is complete, the decoder is discarded entirely. It was only ever a training device — a tool to generate gradients that forced the encoder to learn better embeddings. At inference time, only the encoder is used.

#### Why [CLS] Pooling and Not Mean Pooling?

This is where the TSDAE paper made a specific and important finding. Mean pooling computes an element-wise average across all token positions. The average does not preserve which word came first — "capital Amsterdam Netherlands" and "Netherlands capital Amsterdam" would produce almost identical mean pooling vectors, because averaging scrambles the order.

```
Mean pooling loses word order:

  "capital Amsterdam Netherlands"     → average → [0.335, 0.220, 0.540, 0.488]
  "Netherlands capital Amsterdam"     → average → [0.335, 0.220, 0.540, 0.488]
                                                    ↑ nearly the same vector!
  Order is gone. Decoder cannot reconstruct "The capital of the Netherlands is Amsterdam"
  because it cannot tell which word comes first.
```

[CLS] pooling does not have this problem because the [CLS] token attended to every other token *in their positional order* across 12 layers of self-attention. The transformer's positional encodings made each position distinguishable during attention, so the [CLS] vector ends up carrying a structured summary that respects word order. The TSDAE paper confirmed this experimentally — mean pooling led to significantly worse reconstruction quality.

#### Why `tie_encoder_decoder=True`?

Normally the encoder and decoder would have separate weight matrices that learn independently. Tying them means they share the exact same weights — every gradient update that improves the decoder's reconstruction also directly improves the encoder's embedding, because they are literally the same parameters. This halves the memory footprint and acts as a strong regulariser: the model cannot develop a specialised decoder that works independently of the encoder's representation quality.

#### How TSDAE Compares to Masked Language Modelling

BERT's own pre-training used **masked language modelling (MLM)**: randomly mask some tokens and ask the model to predict them. TSDAE is similar in spirit but significantly harder. In MLM, the model can see all the unmasked tokens around the masked one — it has rich context to work with. In TSDAE, the decoder sees only a single 768-number vector distilled from a heavily corrupted input. It must reconstruct the *entire* sentence from that alone — no surrounding context, no partial input, just the bottleneck embedding.

```python
import nltk
nltk.download("punkt")  # tokenizer needed by DenoisingAutoEncoderDataset

from tqdm import tqdm
from datasets import Dataset, load_dataset
from sentence_transformers.datasets import DenoisingAutoEncoderDataset

# Raw sentences only — no labels needed
mnli = load_dataset("glue", "mnli", split="train").select(range(25_000))
flat_sentences = mnli["premise"] + mnli["hypothesis"]

# DenoisingAutoEncoderDataset applies random token deletion (default ratio: 0.6)
damaged_data = DenoisingAutoEncoderDataset(list(set(flat_sentences)))

# Build training dataset: damaged → original pairs
train_dataset = {"damaged_sentence": [], "original_sentence": []}
for data in tqdm(damaged_data):
    train_dataset["damaged_sentence"].append(data.texts[0])
    train_dataset["original_sentence"].append(data.texts[1])
train_dataset = Dataset.from_dict(train_dataset)

print(f"Training dataset: {len(train_dataset)} sentence pairs")
print("Sample:", train_dataset[0])
# e.g.: {'damaged_sentence': 'Grim jaws are.',
#         'original_sentence': 'Grim faces and hardened jaws are not people-friendly.'}
```

```python
from sentence_transformers import models, SentenceTransformer
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator

# [CLS] pooling — required by TSDAE (not mean pooling)
word_embedding_model = models.Transformer("bert-base-uncased")
pooling_model = models.Pooling(
    word_embedding_model.get_word_embedding_dimension(),
    pooling_mode="cls"   # TSDAE paper: mean pooling loses position information
)
embedding_model = SentenceTransformer(modules=[word_embedding_model, pooling_model])

val_sts = load_dataset("glue", "stsb", split="validation")
evaluator = EmbeddingSimilarityEvaluator(
    sentences1=val_sts["sentence1"],
    sentences2=val_sts["sentence2"],
    scores=[score/5 for score in val_sts["label"]],
    main_similarity="cosine"
)
```

```python
from sentence_transformers import losses
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments

# DenoisingAutoEncoderLoss: trains the encoder-decoder to reconstruct original from damaged
# tie_encoder_decoder=True: shared weights between encoder output and decoder input
train_loss = losses.DenoisingAutoEncoderLoss(
    embedding_model, tie_encoder_decoder=True
)
train_loss.decoder = train_loss.decoder.to("cuda")

# Batch size 16 — smaller than usual because the decoder doubles VRAM usage
args = SentenceTransformerTrainingArguments(
    output_dir="tsdae_embedding_model",
    num_train_epochs=1,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    warmup_steps=100,
    fp16=True,
    eval_steps=100,
    logging_steps=100,
)

trainer = SentenceTransformerTrainer(
    model=embedding_model,
    args=args,
    train_dataset=train_dataset,
    loss=train_loss,
    evaluator=evaluator
)
trainer.train()

print("TSDAE result: pearson_cosine ≈ 0.70")
print("Achieved with zero labelled data — only raw sentences.")
```

A score of `pearson_cosine = 0.70` is remarkable given that *no labels were used at any point*. Compare this to the supervised methods: softmax loss (labelled, 0.59), cosine loss (labelled, 0.72), MNR loss (labelled, 0.80). TSDAE with zero labels lands between the two worst supervised baselines — a strong result for a completely unsupervised approach.

### 8.2 Using TSDAE for Domain Adaptation

#### The Problem — General Models Fail on Specialised Domains

TSDAE's most practical application is not as a standalone embedding model but as a **pre-training step for domain adaptation**. General-purpose models like `all-MiniLM-L6-v2` are excellent on everyday English but struggle when the text comes from a specialised field — medicine, law, finance, or software engineering — because the vocabulary and phrasing of those domains are very different from the general internet text the model was trained on.

The book illustrates this with an embedding map. In-domain terms (Python, Scala, Rust, Java) cluster tightly together because the model has seen them frequently in related contexts. But out-of-domain terms (Queen, The Who, AC/DC, Belgium) land in a completely different region — not because they are unrelated to each other, but because the model has no idea how to place domain-specific concepts it has barely encountered.

A medical embedding model would face exactly this problem. Terms like *MI* (myocardial infarction), *PRN* (as needed), *CABG* (coronary artery bypass graft), and *troponin* appear constantly in clinical notes. A general model has rarely seen these words, so its embeddings for them are essentially random. It cannot tell that *"MI"* and *"heart attack"* should sit next to each other in the embedding space.

#### Adaptive Pre-Training — The Two-Phase Solution

**Adaptive pre-training** solves this with a two-phase pipeline that combines the unsupervised TSDAE technique with supervised SBERT fine-tuning:

```
┌─────────────────────────────────────────────────────────────────┐
│               ADAPTIVE PRE-TRAINING PIPELINE                    │
└─────────────────────────────────────────────────────────────────┘

PHASE 1 — Unsupervised (target domain, no labels needed):
  ┌───────────────────────────────────────┐
  │ Raw domain sentences (just plain text)│
  │ "MI was confirmed via ECG."           │
  │ "PRN medication as required."         │
  │ "Patient awaiting CABG procedure."    │
  └────────────────┬──────────────────────┘
                   │  DenoisingAutoEncoderDataset auto-breaks these
                   ▼
            [TSDAE Training]
                   │
                   ▼
         Domain-adapted encoder
         (now knows medical vocabulary,
          abbreviations, and phrasing)

PHASE 2 — Supervised (general labelled data is fine):
  ┌───────────────────────────────────────┐
  │ Labelled sentence pairs (general OK)  │
  │ "The dog ran." ≈ "A puppy sprinted."  │
  │ "It rained." ≈ "The weather was bad." │
  └────────────────┬──────────────────────┘
                   │  SBERT fine-tuning
                   ▼
         Domain-adapted encoder
         + similarity reasoning skill
                   │
                   ▼
  ┌──────────────────────────────────────────────────────┐
  │ Final model: knows medical domain AND judges          │
  │ similarity between medical sentences                  │
  │                                                      │
  │ "Patient had MI last year" ≈                         │
  │ "History of myocardial infarction" ✓                 │
  └──────────────────────────────────────────────────────┘
```

#### The "Broken Data" Is Automatic — You Just Collect Raw Sentences

One important practical detail: you do not manually break or corrupt anything in Phase 1. You collect raw sentences from your target domain — just plain text, no labels, no processing — and pass them to `DenoisingAutoEncoderDataset`. It handles the token deletion automatically.

```python
# You just collect plain sentences from your domain
domain_sentences = [
    "MI was confirmed via ECG and troponin levels.",
    "PRN medication to be administered as required.",
    "Patient is awaiting CABG procedure next month.",
    "Echocardiogram showed reduced ejection fraction.",
    ...
]

# DenoisingAutoEncoderDataset randomly deletes 60% of tokens internally
# and creates (damaged, original) pairs automatically
damaged_data = DenoisingAutoEncoderDataset(domain_sentences)

# It creates pairs like:
#  damaged:  "MI confirmed troponin"
#  original: "MI was confirmed via ECG and troponin levels."
# No manual work needed — just feed raw sentences
```

Your only task in Phase 1 is to collect the raw domain text. Everything else — the corruption, the pairing, the training signal — happens automatically inside TSDAE.

#### Why Phase 2 General Data Still Works — Two Different Skills

The reason general labelled data works in Phase 2 even though it is not medical is that the two phases are teaching completely different skills that do not interfere with each other.

**Phase 1 teaches WHAT EXISTS in the domain.** After TSDAE on medical sentences, the encoder has representations for *MI*, *PRN*, *troponin*, and *echocardiogram*. It has learned that these words appear in certain contexts with certain neighbouring words. It knows the vocabulary and phrasing of medicine. This is knowledge about *content*.

**Phase 2 teaches WHICH SENTENCES ARE SIMILAR.** SBERT fine-tuning on labelled pairs teaches an abstract reasoning skill: recognising when two sentences express the same meaning regardless of their exact wording. This skill — paraphrase detection, entailment, synonym recognition — is universal. It works the same way whether the sentences are about medicine, law, or football. You do not need medical labelled data to learn it. This is knowledge about *structure of similarity*.

The final model has both simultaneously:

| | What it teaches | What data you need | Skill type |
|---|---|---|---|
| **Phase 1 (TSDAE)** | Domain vocabulary, abbreviations, phrasing | Raw domain sentences (no labels) | Content knowledge |
| **Phase 2 (SBERT)** | How to judge semantic similarity | Any labelled sentence pairs | Reasoning skill |

To judge that *"Patient had MI last year"* and *"History of myocardial infarction"* mean the same thing, the model needs both: it needs to know that *MI* = *myocardial infarction* (Phase 1 domain knowledge) and it needs to know how to compare sentence meanings in general (Phase 2 similarity skill). Neither phase alone is sufficient.

#### Does the Model Forget Phase 1 When Fine-Tuned in Phase 2?

This is a natural concern. You trained hard on medical text in Phase 1 — does SBERT fine-tuning in Phase 2 overwrite all of that?

The answer is mostly no, and the reason sits in the architecture of the transformer. Think of a doctor who spent six years studying medicine, then took a three-month course on how to communicate clearly with patients. Do they forget medicine because they learned communication? Of course not. The communication training adjusted *how they explain things* — it did not overwrite the medical knowledge already encoded in memory.

The same happens inside BERT's transformer layers. Domain vocabulary knowledge lives primarily in the **lower layers** (roughly layers 1–4), which process word-level representations — what each token means in context. Phase 2 fine-tuning for sentence similarity mostly updates the **upper layers** (roughly layers 9–12), which handle sentence-level comparison and abstract contextual reasoning. The two phases mostly write to different parts of the model.

```
BERT layer 1–4  (lower):   word-level, vocabulary, domain-specific patterns
                             ← Phase 1 (TSDAE) writes here
                             ← Phase 2 (SBERT) barely touches here

BERT layer 9–12 (upper):   sentence-level, contextual comparison, similarity
                             ← Phase 2 (SBERT) writes here
                             ← Phase 1 already shaped this, Phase 2 refines it
```

This is also why domain-specific Phase 2 data would be *even better* if you have it — it would update both the upper and lower layers with domain-aware similarity signal — but general data is a perfectly solid fallback because it refines the similarity skill without disturbing the domain vocabulary knowledge sitting below.

#### Why the Combination Beats Either Alone

The book's key finding is that this two-phase combination consistently outperforms either technique in isolation:

| Approach | Domain knowledge | Similarity skill | Result |
|---|---|---|---|
| General model only | ✗ Does not know domain vocab | ✓ Can judge similarity | Fails on domain-specific terms |
| TSDAE only | ✓ Knows domain vocab | ✗ Cannot judge similarity well | Embeddings not optimised for similarity |
| TSDAE → SBERT | ✓ Knows domain vocab | ✓ Can judge similarity | Best of both worlds |

You get the specificity of domain-adapted representations from Phase 1 and the power of supervised similarity training from Phase 2. The order matters — Phase 1 must come first, so the encoder already speaks the domain language before Phase 2 teaches it how to compare sentences in that language.

---

## 9. Key Takeaways

A **text embedding model** converts variable-length text into a fixed-size dense vector where geometric proximity encodes semantic similarity. This single capability unlocks semantic search, RAG, clustering, and recommendation at scale.

**Contrastive learning** is the training paradigm: present the model with (anchor, positive, negative) triplets and define a loss that pulls similar pairs together while pushing dissimilar pairs apart. Word2Vec pioneered this idea in 2013; SBERT and modern sentence transformers apply the same principle at sentence level using transformer encoders.

**SBERT** solves the cross-encoder scaling bottleneck by using a Siamese architecture where two weight-shared BERT models independently encode each sentence into a reusable embedding. This reduces comparison cost from $O(n^2)$ to $O(n)$ indexing plus $O(1)$ retrieval, making embedding-based search practical for million-document corpora.

**Loss function choice is the single highest-leverage hyperparameter** for embedding training quality. The chapter demonstrates this clearly across identical base models and data: softmax loss 0.59 → cosine similarity loss 0.72 → MNR loss 0.80.

**Fine-tuning beats training from scratch**, but watch for the counter-intuitive result: fine-tuning an already-strong model (`all-MiniLM-L6-v2`, score 0.87) on a subset of its own training data can *lower* performance (to 0.85). Fine-tuning delivers maximum value when your fine-tuning data is genuinely different from what the model already saw.

**Augmented SBERT** bridges the gap between limited labels and large-scale training by using a cross-encoder to auto-label a silver dataset. Using only 10,000 gold labels (20% of the data), Augmented SBERT achieves 0.71 — nearly matching the 0.72 of the fully supervised model trained on 50,000 labels.

**TSDAE** achieves `pearson_cosine = 0.70` with *zero labels*, by training an encoder-decoder to reconstruct sentences from corrupted inputs. After training, only the encoder is kept. Its most impactful use is as a domain adaptation pre-training step: TSDAE on your target domain corpus, followed by SBERT fine-tuning on general labelled data, produces domain-specific embedding models that generalise far better than either technique alone.
