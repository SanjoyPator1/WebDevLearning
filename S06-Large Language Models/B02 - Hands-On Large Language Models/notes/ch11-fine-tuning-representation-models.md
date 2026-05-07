# Chapter 11: Fine-Tuning Representation Models for Classification

> *"Fine-tuning unlocks the frozen giant — instead of borrowing a pretrained model's knowledge, we teach it to speak your task's language."*

In Chapter 4, we used pretrained BERT-style models as-is — we borrowed their weights without touching them. They were brilliant but rigid. This chapter asks the natural next question: what if we actually update those weights for our specific task?

Fine-tuning pretrained representation models consistently produces some of the best classification results achievable. This chapter covers four approaches, each suited to a different data and resource situation:

1. **Supervised Classification** — fine-tune all of BERT + a classification head (most data, best results)
2. **Few-Shot Classification with SetFit** — fine-tune with only a handful of labeled examples
3. **Continued Pretraining** — teach BERT domain-specific language before fine-tuning
4. **Named-Entity Recognition** — fine-tune for token-level (word-level) classification

All of these focus on non-generative tasks. Generative model fine-tuning is Chapter 12's territory.

---

## Table of Contents

1. [Supervised Classification](#1-supervised-classification)
   - 1a. [Frozen vs Trainable Architecture](#1a-frozen-vs-trainable-architecture)
   - 1b. [Fine-Tuning a Pretrained BERT Model](#1b-fine-tuning-a-pretrained-bert-model)
   - 1c. [Freezing Layers — the Compute vs Performance Tradeoff](#1c-freezing-layers)
2. [Few-Shot Classification](#2-few-shot-classification)
   - 2a. [The Problem — When Labeled Data is Scarce](#2a-the-problem)
   - 2b. [SetFit's Three-Step Algorithm](#2b-setfits-three-step-algorithm)
   - 2c. [Results and Zero-Shot Extension](#2c-results-and-zero-shot-extension)
3. [Continued Pretraining with Masked Language Modeling](#3-continued-pretraining-with-masked-language-modeling)
   - 3a. [Why Generic Pretraining Falls Short](#3a-why-generic-pretraining-falls-short)
   - 3b. [Masked Language Modeling — The Pretext Task](#3b-masked-language-modeling)
   - 3c. [Continued Pretraining in Practice](#3c-continued-pretraining-in-practice)
4. [Named-Entity Recognition](#4-named-entity-recognition)
   - 4a. [What is NER](#4a-what-is-ner)
   - 4b. [The BIO Tagging Scheme](#4b-the-bio-tagging-scheme)
   - 4c. [The Subtoken Alignment Problem](#4c-the-subtoken-alignment-problem)
   - 4d. [NER Fine-Tuning Pipeline](#4d-ner-fine-tuning-pipeline)
5. [Key Takeaways and Decision Guide](#5-key-takeaways-and-decision-guide)

---

## 1. Supervised Classification

### 1a. Frozen vs Trainable Architecture

In Chapter 4, we used two strategies for classification without updating any pretrained weights. The **task-specific model** (like `distilbert-base-uncased-finetuned-sst-2-english`) was kept frozen and used directly. The **embedding model** produced vector representations and fed them into a separate trainable classifier — but BERT itself remained untouched.

```
Chapter 4 approach — both models "frozen"

Task-specific model:
  Input ──> [BERT (frozen ❄️)] ──> Output class label

Embedding model:
  Input ──> [BERT (frozen ❄️)] ──> embeddings ──> [Classifier (🔥 trainable)] ──> Output
```

This chapter changes the rules. We unfreeze BERT and let the whole architecture — BERT plus classification head — learn together as a single unit.

```
Chapter 11 approach — trainable architecture

  Input ──> [BERT (🔥 trainable)] ──> [Classification Head (🔥 trainable)] ──> Output
```

*Why does this matter so much?* Think of the frozen approach like hiring a brilliant consultant who gives you advice but never adapts their worldview to your company. The fine-tuned approach is like that same consultant joining your team full-time, attending your meetings, learning your jargon, and reshaping their thinking around your specific problems.

When BERT and the classification head train together, something magical happens during backpropagation. The classification head effectively says: *"Hey, I need embeddings that sharply separate positive from negative sentiment — can you reorganize your internal representations to help me?"* And BERT does. The gradients flow backward from the head all the way through all 12 BERT encoder layers, nudging every weight to produce task-useful representations. This cooperative, end-to-end learning is what the frozen approach fundamentally cannot do.

```
Frozen approach: gradients stop here ───┐
                                        ↓
  Input ──> [BERT ❄️] ─────> [Head 🔥] ──> Loss
                              ↑
                   Gradients only update the head

Fine-tuned approach: gradients flow everywhere
  Input ──> [BERT 🔥] ─────> [Head 🔥] ──> Loss
              ↑                 ↑
    Gradients update BERT  Gradients update head
```

### 1b. Fine-Tuning a Pretrained BERT Model

The dataset is Rotten Tomatoes movie reviews — 5,331 positive and 5,331 negative examples — the same one used in Chapter 4, which lets us do a direct performance comparison.

```python
from datasets import load_dataset

tomatoes = load_dataset("rotten_tomatoes")
train_data, test_data = tomatoes["train"], tomatoes["test"]
```

**Loading the model.** The key class is `AutoModelForSequenceClassification`. It does two things at once: loads the pretrained BERT backbone *and* automatically attaches a feedforward classification head on top. The `num_labels=2` argument tells it we want a 2-class head (positive / negative).

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_id = "bert-base-cased"
model = AutoModelForSequenceClassification.from_pretrained(
    model_id, num_labels=2
)
tokenizer = AutoTokenizer.from_pretrained(model_id)
```

`bert-base-cased` was pretrained on English Wikipedia and a large corpus of books. "Cased" means it preserves uppercase letters — important for sentiment since "AMAZING" and "amazing" carry different emphasis.

**Tokenization and the DataCollator.** Sentences in a batch are rarely the same length. We need to pad them to a common length so they can be stacked into a tensor. `DataCollatorWithPadding` handles this *dynamically* — it pads each batch to the length of its longest sentence, not to the maximum possible length in the whole dataset. This saves a lot of compute.

```
Batch example — dynamic padding to batch-max:

  Sentence 1: [CLS] what a horrible movie ! [SEP]       → length 7
  Sentence 2: [CLS] best film ever made [SEP]            → length 6
  Sentence 3: [CLS] surprisingly good [SEP] [PAD] [PAD] → length 6 → padded to 7

  All become length 7 (the batch max), not length 512 (the model max).
```

```python
from transformers import DataCollatorWithPadding

data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

def preprocess_function(examples):
    return tokenizer(examples["text"], truncation=True)

tokenized_train = train_data.map(preprocess_function, batched=True)
tokenized_test  = test_data.map(preprocess_function, batched=True)
```

**Evaluation metric.** We use F1 score rather than accuracy. Why? Because accuracy can mislead when classes are imbalanced. F1 balances precision (of all things I called positive, how many actually were?) and recall (of all actual positives, how many did I catch?). For binary sentiment, a high F1 means the model is genuinely getting both classes right.

```python
import numpy as np
from datasets import load_metric

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    load_f1 = load_metric("f1")
    f1 = load_f1.compute(predictions=predictions, references=labels)["f1"]
    return {"f1": f1}
```

**Training arguments and the Trainer.** `TrainingArguments` is where you set all the hyperparameters. Let's go through the important ones:

- `learning_rate=2e-5` — deliberately small. We don't want to overwrite the rich pretrained knowledge with large gradient steps. Think of it as making small, careful adjustments rather than rewriting everything.
- `weight_decay=0.01` — L2 regularization. Penalizes large weights to prevent overfitting.
- `num_train_epochs=1` — one full pass through the data. Even one epoch is powerful when starting from a strong pretrained foundation.
- `per_device_train_batch_size=16` — 16 examples processed together before each gradient update.

```python
from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    "model",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=1,
    weight_decay=0.01,
    save_strategy="epoch",
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_test,
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)

trainer.train()
```

The `Trainer` automates the training loop: forward pass through BERT + head, compute cross-entropy loss, backpropagate gradients through the entire network, optimizer step. After one epoch, evaluating gives us **F1 = 0.85** — compared to 0.80 in Chapter 4's frozen approach. A 5-point jump, for just a few minutes of training. That is the power of joint fine-tuning.

### 1c. Freezing Layers

Full fine-tuning of all 12 BERT encoder blocks is powerful but slow and memory-intensive. What if you don't have the compute budget? This section explores the tradeoff of selectively freezing parts of the model.

**BERT's parameter hierarchy.** When you inspect a fine-tuned BERT model's named parameters, you see this structure:

```
bert.embeddings.word_embeddings.weight       ← token vocabulary lookup
bert.embeddings.position_embeddings.weight   ← position information
bert.embeddings.token_type_embeddings.weight ← sentence A vs B marker
bert.embeddings.LayerNorm.weight / bias

bert.encoder.layer.0.attention.self.query.weight  ← encoder block 0: Q projection
bert.encoder.layer.0.attention.self.key.weight    ← encoder block 0: K projection
bert.encoder.layer.0.attention.self.value.weight  ← encoder block 0: V projection
... (many more per-layer parameters) ...
bert.encoder.layer.11.output.LayerNorm.weight     ← encoder block 11

bert.pooler.dense.weight / bias                   ← CLS token pooling layer
classifier.weight / bias                          ← our task-specific head
```

There are 12 encoder blocks (indexed 0–11), each containing multi-head attention weights, feedforward network weights, and layer normalization parameters.

**What does `requires_grad = False` actually do?** When PyTorch computes gradients during backprop, it traces through the computation graph from the loss backward to every parameter. If a parameter has `requires_grad=False`, PyTorch simply skips computing and storing a gradient for it. No gradient means no update. Crucially, freezing a parameter doesn't change its value or remove it from the model — it just stops it from changing during training. Think of it like putting a lock on certain weights.

```python
for name, param in model.named_parameters():
    if name.startswith("classifier"):
        param.requires_grad = True   # train the head
    else:
        param.requires_grad = False  # freeze everything else
```

**Experiment 1: Freeze all BERT, train only the classification head.**

```
Encoder 0  ❄️ frozen
Encoder 1  ❄️ frozen
...
Encoder 11 ❄️ frozen
Classifier 🔥 trainable
```

Result: **F1 = 0.63**. The classifier learns to use BERT's pre-existing representations, but BERT can't adjust those representations to be more useful for sentiment. It's like forcing the brilliant consultant to only use their old notes — they can't incorporate what they've observed in your company.

**Experiment 2: Freeze first 10 encoder blocks, train the last 2 + head.**

```python
for index, (name, param) in enumerate(model.named_parameters()):
    if index < 165:   # parameter index 165 is where encoder block 11 starts
        param.requires_grad = False
```

```
Encoder 0  ❄️ frozen
...
Encoder 9  ❄️ frozen
Encoder 10 🔥 trainable  ← fine-tunes upper-level representations
Encoder 11 🔥 trainable  ← directly feeds the classifier
Classifier 🔥 trainable
```

Result: **F1 = 0.80**. A dramatic jump from 0.63. The upper layers of BERT capture more task-specific, abstract features and can be reshaped for sentiment. Lower layers capture universal linguistic properties (syntax, morphology) and don't need to change.

**Why does performance stabilize after just 5 trainable blocks?** BERT's layers have a known hierarchy: shallow layers (0–3) learn basic syntax and morphology — things like part-of-speech, word shapes. Middle layers (4–8) capture semantic relationships. Upper layers (9–11) encode task-specific, abstract representations. For a classification task, the upper layers are where the action is. Training those 5 upper layers captures most of the gains, while the lower layers' universal linguistic knowledge remains intact.

```
Frozen lower layers      Trainable upper layers
(universal language)     (task-specific adaptation)

Encoder 0  ❄️  ←─── syntax, morphology
Encoder 1  ❄️
Encoder 2  ❄️
Encoder 3  ❄️
Encoder 4  ❄️  ←─── semantics start here
Encoder 5  ❄️
Encoder 6  ❄️
Encoder 7  🔥  ←─── fine-tuning starts
Encoder 8  🔥
Encoder 9  🔥
Encoder 10 🔥
Encoder 11 🔥  ←─── most task-relevant layer
Classifier 🔥
```

**The full comparison:**

| Configuration | F1 Score | Training speed |
|---|---|---|
| Ch4: frozen model (zero fine-tuning) | 0.80 | Instantaneous |
| All BERT frozen, only head trains | 0.63 | Fastest |
| Freeze first 10, train last 2 + head | 0.80 | Fast |
| Train all 12 blocks + head | **0.85** | Moderate |

The practical takeaway: if GPU time is limited, freeze the first 8–10 layers and train the upper 2–4. You get most of the benefit at a fraction of the compute cost. When training for multiple epochs, the gap between frozen and unfrozen grows larger — keep that in mind when scaling experiments.

---

## 2. Few-Shot Classification

### 2a. The Problem

Full fine-tuning of BERT requires thousands of labeled examples. But what if you're starting a new product, building a custom classifier for a niche domain, or simply can't afford to label thousands of data points?

**Few-shot classification** is the answer. You label only a small number of high-quality examples per class — sometimes as few as 8 or 16 — and a well-designed framework extracts maximum signal from them.

The framework that makes this work is **SetFit** (Sentence Transformer Fine-tuning), built on top of `sentence-transformers`. Its key insight: even from a handful of labeled examples, we can manufacture a rich training signal by generating *sentence pairs* and using contrastive learning.

### 2b. SetFit's Three-Step Algorithm

SetFit works in three steps. Let's walk through each with an example before looking at the code.

**The setup:** You have 4 labeled movie reviews — 2 positive, 2 negative. You want to classify new reviews.

```
Labeled data (tiny!):
  "What a horrible movie..."       → Negative (0)
  "Very disappointed"              → Negative (0)
  "Some flaws but a great film"    → Positive (1)
  "Best movie ever!"               → Positive (1)

Unlabeled test:
  "Never want to see this again!"  → ?
```

**Step 1: Sampling Training Pairs**

SetFit is a matchmaker. It treats sentences from the same class as similar (*positive pairs*) and sentences from different classes as dissimilar (*negative pairs*).

Within each class, it pairs every sentence with every other sentence. For a class with $n$ sentences, this gives:

$$\text{positive pairs} = \frac{n(n-1)}{2}$$

*Dry-run with 4 sentences (2 per class):*

```
Positive class: A = "Some flaws but a great film", B = "Best movie ever!"
Negative class: C = "What a horrible movie",        D = "Very disappointed"

Within-class pairs (positive — similar):
  (A, B) → Positive pair ✓

Within-class pairs for negatives:
  (C, D) → Positive pair ✓

Cross-class pairs (negative — dissimilar):
  (A, C), (A, D), (B, C), (B, D) → Negative pairs ✗

Total: 2 positive + 4 negative = 6 pairs from only 4 sentences!
```

In the book's actual experiment with 16 examples per class (32 total), with 20 iterations of pair generation:

$$16 \times 15 / 2 = 120 \text{ positive pairs per class}$$
$$20 \times 32 = 680 \text{ samples} \times 2 \text{ (pos+neg)} = 1{,}280 \text{ sentence pairs from 32 examples!}$$

This data augmentation through pairing is SetFit's superpower.

**Step 2: Fine-Tuning the Embedding Model via Contrastive Learning**

The generated pairs are used to fine-tune a pretrained `SentenceTransformer` model using contrastive learning. The goal: make the model's embedding space *cluster sentences by class* rather than by generic topic.

*Intuition for contrastive learning, explained simply:* Imagine training a puppy to recognize "same" and "different". You show it two photos of cats and say "same!" — the puppy learns to group them. You show a cat and a dog and say "different!" — the puppy learns to separate them. The embedding model does exactly this, but in a 768-dimensional vector space.

```
Step 2 architecture (Siamese network):

"I write code in Python"   "My dog is a labrador"
        ↓                          ↓
    [BERT + Pooling]           [BERT + Pooling]
        ↓                          ↓
   sentence vector u         sentence vector v
        ↓                          ↓
        └──────── concat(u, v, |u - v|) ──────────→ [Softmax] → same/different
```

The feature vector passed to softmax is $(u,\ v,\ |u-v|)$. Why include $|u-v|$? Because it's an explicit *distance signal* — it tells the classifier how far apart the two embeddings are, not just their individual directions. The model can then learn "similar embeddings → small $|u-v|$ → positive pair".

After this step, the SentenceTransformer model has been pulled toward a geometry where movie-positive sentences cluster together and movie-negative sentences cluster together, separated by a meaningful margin.

**Step 3: Train a Classifier on the Fine-Tuned Embeddings**

The fine-tuned embedding model converts every sentence into a vector that is now *task-aware*. A simple logistic regression classifier trained on those vectors can predict the class label. This is the same idea as Chapter 2's approach, but now the embeddings are specialized for the task rather than generic.

```
                  Fine-tuned SentenceTransformer
                          ↓
"I write code in Python"  →  [0.23, -0.41, 0.88, ...]  ──→ [Classifier] → Code (79%)
"I should practice SQL"   →  [0.19, -0.38, 0.91, ...]  ──→ [Classifier] → Code (93%)
"My dog is a labrador"    →  [-0.71, 0.52, -0.12, ...]  ──→ [Classifier] → Pets (85%)
```

The three steps together:

```
Step 1: Raw labeled data → sentence pairs (positive + negative)
         ↓
Step 2: Sentence pairs → fine-tune SentenceTransformer via contrastive learning
         ↓
Step 3: Fine-tuned embeddings → train logistic regression → final classifier
```

**Implementation:**

```python
from setfit import sample_dataset, SetFitModel
from setfit import TrainingArguments as SetFitTrainingArguments
from setfit import Trainer as SetFitTrainer

# Simulate few-shot: sample only 16 examples per class (32 total)
sampled_train_data = sample_dataset(tomatoes["train"], num_samples=16)

# Load a pretrained SentenceTransformer model
model = SetFitModel.from_pretrained("sentence-transformers/all-mpnet-base-v2")

# Configure training
args = SetFitTrainingArguments(
    num_epochs=3,        # epochs of contrastive learning
    num_iterations=20    # number of text pair combinations to generate
)

trainer = SetFitTrainer(
    model=model,
    args=args,
    train_dataset=sampled_train_data,
    eval_dataset=tomatoes["test"],
    metric="f1"
)

trainer.train()
```

### 2c. Results and Zero-Shot Extension

The result is astonishing: **F1 = 0.85** with only 32 labeled documents. This is identical to full fine-tuning on 8,500 examples. SetFit achieves in 32 examples what would normally require hundreds of times more data. The contrastive learning signal from 1,280 generated pairs is simply that powerful.

SetFit also supports **zero-shot classification** — when you have zero labeled examples at all. It generates synthetic training examples directly from the label names. If your classes are "happy" and "sad", SetFit synthesizes examples like "This example is happy" and "This example is sad", trains on those, and then classifies real sentences. This is a remarkable capability for cold-start problems.

---

## 3. Continued Pretraining with Masked Language Modeling

### 3a. Why Generic Pretraining Falls Short

BERT was trained on Wikipedia and the Books corpus — a broad, general collection of English text. This makes it a superb general-purpose language model. But general-purpose means it knows what Wikipedia talks about: history, science, politics. It doesn't know your domain.

Consider these scenarios:

- **Medical NLP**: BERT has never seen "myocardial infarction" or "bradycardia" at high frequency. Its representations for medical terms are weak.
- **Legal NLP**: Terms like "amicus curiae", "tort", "promissory estoppel" are rare in Wikipedia.
- **Movie reviews** (our case): Words like "cinematography", "screenplay", "blockbuster" appear, but their *sentiment-laden* usage patterns in reviews may differ from Wikipedia's neutral descriptions.

The fix is **continued pretraining** — take the already-pretrained BERT and keep training it using Masked Language Modeling, but now on your domain-specific data. You are not training from scratch; you are *adapting* an existing model.

This creates a three-step pipeline instead of the usual two-step:

```
Standard 2-step:
  [General BERT] ──────────────────────────────> [Fine-tune for task]
  (pretrained on Wikipedia)                       (classification head)

Domain-adapted 3-step:
  [General BERT] ──> [Domain BERT] ──────────> [Fine-tune for task]
  (Wikipedia)         (continued MLM             (classification head)
                       on domain data)
```

For a company like ACME, this genealogy becomes even richer:

```
[General BERT (public)]
       ↓
[ACME BERT (domain-adapted on company data)]
       ↓               ↓                  ↓
[ACME BERT for    [ACME BERT for     [ACME BERT for
 topic classif.]   semantic search]   NER]
```

One domain-adapted backbone spawns multiple specialized task models. This is highly efficient — you pay the domain adaptation cost once and reuse the result everywhere.

### 3b. Masked Language Modeling

**What is MLM?** Masked Language Modeling is the pretext task BERT was originally trained on. We take a sentence, randomly hide 15% of its tokens by replacing them with a special `[MASK]` token, and ask BERT to predict what the masked words were. This forces BERT to deeply understand context — you cannot guess a masked word by looking at it alone; you must reason about its neighbors.

*Explained simply:* BERT plays the world's most difficult fill-in-the-blank game. Given "What a horrible [MASK]!", it must guess "movie", "idea", "day", etc. To make good guesses, it must understand the full context of the sentence. This is why pretrained BERT understands language — it has guessed billions of masked words.

**Token masking vs Whole-word masking.** BERT's WordPiece tokenizer splits rare words into subwords (e.g., "vocalization" → "vocal", "##ization"). Token masking picks individual subwords to mask; whole-word masking masks all subwords of a chosen word together.

```
Input:          Her   vocal   ##ization   was   remarkably   melodic

Token mask:     Her   vocal   [MASK]      was   remarkably   melodic
                                ↑
                       Only the "##ization" subword is masked.
                       Easy to guess — "vocal" is right next to it!

Whole-word mask: Her   [MASK]  [MASK]      was   remarkably   melodic
                         ↑         ↑
                  Both subwords of "vocalization" are masked.
                  Harder — BERT must infer the whole word from context.
```

Whole-word masking produces better representations because it forces the model to think about complete concepts rather than exploiting morphological cues. However, it is slower to converge. For the book's example, token masking with 15% probability is used for faster iteration.

### 3c. Continued Pretraining in Practice

We load `AutoModelForMaskedLM` — the MLM variant of BERT, not the sequence classification variant. This model's head outputs logit scores over the entire vocabulary for each masked position, instead of outputting class scores.

```python
from transformers import AutoTokenizer, AutoModelForMaskedLM

model = AutoModelForMaskedLM.from_pretrained("bert-base-cased")
tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

def preprocess_function(examples):
    return tokenizer(examples["text"], truncation=True)

# Tokenize — and crucially, remove the "label" column
# MLM is unsupervised: we don't use sentiment labels here
tokenized_train = train_data.map(preprocess_function, batched=True)
tokenized_train = tokenized_train.remove_columns("label")
```

The `DataCollatorForLanguageModeling` dynamically applies masking at training time. Each time a batch is formed, a fresh random 15% of tokens is masked — this means the model never sees the exact same masked version of a sentence twice, providing a richer training signal.

```python
from transformers import DataCollatorForLanguageModeling

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=True,
    mlm_probability=0.15
)
```

Training runs for more epochs (10 in the book's example) since MLM is an unsupervised pretext task rather than a supervised classification task. After training, we save the domain-adapted model:

```python
tokenizer.save_pretrained("mlm")
trainer.train()
model.save_pretrained("mlm")
```

**Before and after comparison.** We can probe what the model has learned using the `fill-mask` pipeline:

```python
from transformers import pipeline

# Base BERT (trained on Wikipedia/books)
mask_filler = pipeline("fill-mask", model="bert-base-cased")
mask_filler("What a horrible [MASK]!")
# → "idea", "dream", "thing", "mistake", "thought"  (generic concepts)

# Domain-adapted BERT (continued pretraining on movie reviews)
mask_filler = pipeline("fill-mask", model="mlm")
mask_filler("What a horrible [MASK]!")
# → "movie", "film", "mess", "comedy", "story"  (movie-domain concepts!)
```

The shift in predictions is a direct window into what the model has learned. The domain-adapted BERT now associates the phrase "What a horrible ___" with movie-review vocabulary rather than generic English.

Finally, to use this domain-adapted model for classification, simply load it with `AutoModelForSequenceClassification` instead of `AutoModelForMaskedLM`:

```python
from transformers import AutoModelForSequenceClassification

model = AutoModelForSequenceClassification.from_pretrained("mlm", num_labels=2)
tokenizer = AutoTokenizer.from_pretrained("mlm")
# Then proceed exactly as in Section 1 — same Trainer setup
```

---

## 4. Named-Entity Recognition

### 4a. What is NER

Every classification task we have seen so far assigns *one label per document*. A movie review gets one sentiment label. An email gets one topic label. NER is different in a fundamental way: it assigns *one label per word* (or more precisely, per token) in a sentence.

**Named-Entity Recognition** identifies specific meaningful chunks within text — people's names, places, organizations, and other entities. Given the sentence "I am Maarten and I live in the Netherlands", a NER model should identify "Maarten" as a Person and "Netherlands" as a Location.

*Intuition:* Imagine playing a game called "spot the proper noun" on every word of a paragraph. For each word, you ask: is this a person's name? A company? A city? A date? Or is it just an ordinary word? That is exactly what NER does, at scale.

NER is practically essential for:
- **De-identification**: Removing patient names from medical records before sharing
- **Information extraction**: Finding all the companies mentioned in a news article
- **Entity linking**: Connecting "Elon Musk" in text to a knowledge base entry
- **Question answering**: Knowing which words are locations to answer "Where does X live?"

```
"I am Maarten and I live in the Netherlands."
 ↓   ↓    ↓       ↓  ↓    ↓  ↓   ↓
 O   O   PERSON   O  O    O  O  LOCATION

 ("O" = Outside — not an entity)
```

The BERT architecture for NER differs from sequence classification in one key way: instead of pooling the entire sequence into a single vector and classifying that, we keep the per-token output vectors and classify *each one individually*.

```
Sequence classification:         Token classification (NER):
Input: "I am Maarten"            Input: "I am Maarten"
         ↓                                ↓
        BERT                             BERT
         ↓                                ↓↓↓
    [pool to [CLS]]              [per-token outputs]
         ↓                        ↓   ↓       ↓
      [FFN head]                 [FFN][FFN]  [FFN]
         ↓                        ↓     ↓       ↓
    "Positive"                   O     O     B-PER
```

### 4b. The BIO Tagging Scheme

One label per token sounds simple — but there's a complication. Named entities often span *multiple words*. "Dean Palmer" is one person, not two separate people named "Dean" and "Palmer". "New York Rangers" is one organization, not "New", "York", and "Rangers" independently.

We need a labeling scheme that can represent multi-word spans. The answer is **BIO tagging**: **B**eginning, **I**nside, **O**utside.

- **B-XXX** (Beginning): This token is the *first* token of a named entity of type XXX
- **I-XXX** (Inside): This token *continues* a named entity of type XXX that began earlier
- **O** (Outside): This token is not part of any named entity

The entity types for the CoNLL-2003 dataset used in this chapter are:
- **PER** — Person names
- **ORG** — Organizations
- **LOC** — Locations
- **MISC** — Miscellaneous entities (events, nationalities, etc.)

*Dry-run with the book's example sentence: "Dean Palmer hit his 30th homer for the Rangers ."*

```
Token:    Dean    Palmer   hit   his   30th   homer  for   the   Rangers   .
BIO tag:  B-PER   I-PER    O     O     O      O      O     O     B-LOC     O
```

Decoding the BIO tags: B-PER followed by I-PER means "Dean Palmer" is a single person entity. B-LOC with no following I-LOC means "Rangers" is a single-token location entity.

Why do we need both B and I? Consider "London New York" — two separate location entities back to back. Without B/I distinction:
- `LOC LOC` → ambiguous: one entity or two?

With BIO:
- `B-LOC B-LOC` → clearly two separate entities

The label-to-id mapping used in the CoNLL-2003 dataset:

```python
label2id = {
    "O": 0,
    "B-PER": 1,  "I-PER": 2,
    "B-ORG": 3,  "I-ORG": 4,
    "B-LOC": 5,  "I-LOC": 6,
    "B-MISC": 7, "I-MISC": 8
}
```

Notice the pattern: B tags have odd IDs (1, 3, 5, 7) and I tags have even IDs (2, 4, 6, 8). This is intentional — the `align_labels` function exploits this pattern (`label % 2 == 1` means it's a B tag that should become I).

### 4c. The Subtoken Alignment Problem

This is the trickiest part of NER with BERT, and where most tutorials lose people. Let's slow down and walk through it carefully.

**The problem.** Our CoNLL-2003 dataset provides labels at the *word* level. But BERT's tokenizer works at the *subword* level — it splits rare or complex words into pieces using WordPiece tokenization. For example:

```
Word:     "homer"
Tokens:   "home"  "##r"     ← split into two subwords!

Word:     "Maarten"
Tokens:   "Ma"  "##arte"  "##n"  ← split into three subwords!
```

The `##` prefix means "this piece is a continuation of the previous word". Now, our NER labels are:

- "homer" → O (not an entity)
- "Maarten" → B-PER (beginning of a person entity)

But after tokenization, we have more tokens than we have labels. We need to *align* the word-level labels to the subword-level tokens.

**The alignment rules:**

1. **[CLS] and [SEP] tokens**: These are special BERT tokens with no corresponding word. They get label **-100**, which tells PyTorch to ignore these positions when computing the loss.

2. **First subtoken of a word**: Gets the word's original label unchanged.

3. **Subsequent subtokens of the same word**: This is the subtle part.
   - If the word's label was **O** (not an entity), all subtokens get **O**.
   - If the word's label was **B-XXX** (start of an entity), subsequent subtokens should get **I-XXX** (inside, continuing the same entity). They are part of the same entity — they didn't start a new one.

*Dry-run with "Maarten" (label: B-PER):*

```
Word:      Maarten
Label:     B-PER

After tokenization:
Subtoken:  Ma      ##arte   ##n
Index:     1st     2nd      3rd

Alignment:
  Ma:      B-PER  ← first subtoken, gets original label
  ##arte:  I-PER  ← continuation, B→I
  ##n:     I-PER  ← continuation, B→I
```

*Full sentence dry-run — "My name is Maarten":*

```
Input words:   My    name   is    Maarten
Word labels:   O     O      O     B-PER

After tokenization:
Subtokens:  [CLS]  My   name   is   Ma    ##arte  ##n   [SEP]
Alignment:  -100   O    O      O    B-PER  I-PER  I-PER  -100
             ↑                      ↑      ↑↑↑↑↑↑
          special                 first  continuations
          token                   sub-   get I-PER
          → -100                  token
                                  gets
                                 B-PER
```

The `-100` label for [CLS] and [SEP] is essential. Cross-entropy loss in PyTorch ignores index -100 by default, so these tokens don't contribute to the training signal — they are structural tokens that carry no entity information.

**The `align_labels` function:**

```python
def align_labels(examples):
    token_ids = tokenizer(
        examples["tokens"],
        truncation=True,
        is_split_into_words=True   # ← tells tokenizer words are already split
    )
    labels = examples["ner_tags"]
    updated_labels = []

    for index, label in enumerate(labels):
        word_ids = token_ids.word_ids(batch_index=index)
        previous_word_idx = None
        label_ids = []

        for word_idx in word_ids:
            if word_idx is None:
                # [CLS] or [SEP] — ignore in loss
                label_ids.append(-100)
            elif word_idx != previous_word_idx:
                # First subtoken of a new word → use original label
                label_ids.append(label[word_idx])
            else:
                # Subsequent subtoken of same word → B→I conversion
                updated_label = label[word_idx]
                if updated_label % 2 == 1:   # B tags have odd IDs
                    updated_label += 1        # B-PER (1) → I-PER (2)
                label_ids.append(updated_label)

            previous_word_idx = word_idx

        updated_labels.append(label_ids)

    token_ids["labels"] = updated_labels
    return token_ids

tokenized = dataset.map(align_labels, batched=True)
```

The `word_idx % 2 == 1` check is the clever trick: B tags (1, 3, 5, 7) are odd, so adding 1 gives the corresponding I tag (2, 4, 6, 8). If the label is already an I tag or O, the `% 2 == 1` check is False and the label is used unchanged.

### 4d. NER Fine-Tuning Pipeline

**Model loading.** `AutoModelForTokenClassification` is the NER-specific model class. It attaches a classification head that outputs one logit vector *per token* rather than one per sequence.

```python
from transformers import AutoModelForTokenClassification

model = AutoModelForTokenClassification.from_pretrained(
    "bert-base-cased",
    num_labels=len(label2id),  # 9 labels (O + 4 entity types × 2 B/I)
    id2label=id2label,
    label2id=label2id
)
```

**Data collation.** For NER, we need `DataCollatorForTokenClassification` instead of `DataCollatorWithPadding`. The difference: it pads both the token IDs *and* the label sequences to the same length, ensuring label and token sequences stay aligned.

```python
from transformers import DataCollatorForTokenClassification

data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
```

**Evaluation with seqeval.** For NER, accuracy per token is a misleading metric — the vast majority of tokens are "O" (not an entity), so even a model that predicts O for everything gets high token accuracy. Instead, we use `seqeval`, which evaluates at the **entity level**:

- "Dean Palmer" counts as a single correct prediction only if *both* "Dean" (B-PER) and "Palmer" (I-PER) are correctly labeled.
- Partial credit is not given — the whole entity span must match.

```python
import evaluate
import numpy as np

seqeval = evaluate.load("seqeval")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=2)  # axis=2: per-token

    true_predictions = []
    true_labels = []

    for prediction, label in zip(predictions, labels):
        for token_prediction, token_label in zip(prediction, label):
            if token_label != -100:  # skip [CLS], [SEP], padding
                true_predictions.append([id2label[token_prediction]])
                true_labels.append([id2label[token_label]])

    results = seqeval.compute(
        predictions=true_predictions,
        references=true_labels
    )
    return {"f1": results["overall_f1"]}
```

**Training** follows the same Trainer pattern as before, with `DataCollatorForTokenClassification`:

```python
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["test"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)
trainer.train()
```

**Inference.** After saving the model, we can use it in the `token-classification` pipeline:

```python
from transformers import pipeline

trainer.save_model("ner_model")
token_classifier = pipeline("token-classification", model="ner_model")
token_classifier("My name is Maarten.")
```

Output:
```
[{'entity': 'B-PER', 'score': 0.995, 'word': 'Ma',     'start': 11, 'end': 13},
 {'entity': 'I-PER', 'score': 0.993, 'word': '##arte', 'start': 13, 'end': 17},
 {'entity': 'I-PER', 'score': 0.995, 'word': '##n',    'start': 17, 'end': 18}]
```

The model correctly identifies the three subtokens of "Maarten" as B-PER, I-PER, I-PER — the entire word is recognized as a single person entity with very high confidence. The subtoken alignment done during training has paid off perfectly during inference.

---

## 5. Key Takeaways and Decision Guide

### Performance Summary

| Approach | Labeled data needed | F1 score | Training time |
|---|---|---|---|
| Ch4: frozen pretrained model | All (8,500) | 0.80 | None (inference only) |
| Full fine-tune (all layers) | All (8,500) | **0.85** | Moderate |
| Frozen BERT, train head only | All (8,500) | 0.63 | Fastest |
| Partial freeze (top 2 layers) | All (8,500) | 0.80 | Fast |
| SetFit (few-shot) | **32 examples** | **0.85** | Moderate |
| Continued pretrain + fine-tune | All (domain unlabeled) | Better for OOD | Slow pretrain |

The standout result: SetFit achieves the same F1 as full fine-tuning on 8,500 examples — using only 32. If you ever face a labeling bottleneck, SetFit should be your first choice.

### When to Use Which Approach

The decision depends on four factors: labeled data availability, domain specificity, compute budget, and task type.

If you have **abundant labeled data** and a **standard-domain task** (like general sentiment), full fine-tuning of all BERT layers produces the best results. It is the most direct path to a high-quality classifier and requires only a few minutes on a modern GPU.

If you have **very little labeled data** — fewer than 100 examples per class — reach for **SetFit**. Its pair-generation trick multiplies your labeled data into thousands of contrastive training signals. The resulting model often matches full fine-tuning on much smaller budgets.

If your domain has **specialized vocabulary** that BERT wasn't exposed to during pretraining — medical jargon, legal terminology, company-internal language — consider **continued pretraining** first. Use your unlabeled domain data (which is usually abundant) to teach BERT the vocabulary of your domain via MLM, then fine-tune for the specific task. This two-step investment pays off when your target domain is genuinely out-of-distribution for general BERT.

If you are constrained on **GPU compute** but have labeled data, **partial freezing** is the practical middle ground. Freeze the lower BERT layers (which capture universal language structure) and train only the upper layers plus the classification head. You can get F1=0.80 — much better than the frozen approach — in significantly less time.

Finally, if your task requires **per-token prediction** — identifying entities within text, extracting spans, labeling each word in a sequence — you need the NER pipeline with BIO tagging and subtoken alignment. The architecture change (per-token classification head instead of pooled sequence head) and the label alignment logic are what make this work.

### Bridge to Chapter 12

This chapter fine-tuned *encoder* models (BERT-style) for *discriminative*, non-generative tasks. Chapter 12 does the same for *decoder* models (GPT-style) — teaching them to follow instructions and align their outputs with human preferences. Where Chapter 11's classification head outputs a class label, Chapter 12's instruction-tuning output is a full generated sequence. The training framework shifts from Trainer-based classification to Supervised Fine-Tuning (SFT) and Reinforcement Learning from Human Feedback (RLHF).

The core lesson of this chapter stays constant: fine-tuning — whether supervised, few-shot, domain-adaptive, or token-level — is always better than using a frozen model when you have the right data and the right task framing.
