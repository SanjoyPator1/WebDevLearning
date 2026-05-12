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
   - 2a. [The Problem — When Labeled Data is Scarce](#2a-the-problem--when-labeled-data-is-scarce)
   - 2b. [SetFit's Big Idea — Bird's-Eye View](#2b-setfits-big-idea--birds-eye-view)
   - 2c. [Step 1 — Sampling Training Pairs](#2c-step-1--sampling-training-pairs)
   - 2d. [Step 2 — Contrastive Fine-Tuning of the Embedding Model](#2d-step-2--contrastive-fine-tuning-of-the-embedding-model)
   - 2e. [Step 3 — Train a Classifier on the Specialised Embeddings](#2e-step-3--train-a-classifier-on-the-specialised-embeddings)
   - 2f. [Implementation in Code](#2f-implementation-in-code)
   - 2g. [Results and the Zero-Shot Extension](#2g-results-and-the-zero-shot-extension)
3. [Continued Pretraining with Masked Language Modeling](#3-continued-pretraining-with-masked-language-modeling)
   - 3a. [Why Generic Pretraining Falls Short](#3a-why-generic-pretraining-falls-short)
   - 3b. [The Three-Step Pipeline at a Glance](#3b-the-three-step-pipeline-at-a-glance)
   - 3c. [What is Masked Language Modeling, Really](#3c-what-is-masked-language-modeling-really)
   - 3d. [A Dry-Run — One MLM Training Step](#3d-a-dry-run--one-mlm-training-step)
   - 3e. [Token vs Whole-Word Masking](#3e-token-vs-whole-word-masking)
   - 3f. [Continued Pretraining in Practice](#3f-continued-pretraining-in-practice)
   - 3g. [Probing What the Model Learned](#3g-probing-what-the-model-learned)
   - 3h. [Connecting Back to Classification](#3h-connecting-back-to-classification)
4. [Named-Entity Recognition](#4-named-entity-recognition)
   - 4a. [What is NER and Why It Matters](#4a-what-is-ner-and-why-it-matters)
   - 4b. [From Document Classification to Token Classification](#4b-from-document-classification-to-token-classification)
   - 4c. [The CoNLL-2003 Dataset](#4c-the-conll-2003-dataset)
   - 4d. [The BIO Tagging Scheme](#4d-the-bio-tagging-scheme)
   - 4e. [The Subtoken Alignment Problem](#4e-the-subtoken-alignment-problem)
   - 4f. [The align_labels Function — Trace Through](#4f-the-align_labels-function--trace-through)
   - 4g. [Entity-Level Evaluation with seqeval](#4g-entity-level-evaluation-with-seqeval)
   - 4h. [Training, Inference, and the Maarten Test](#4h-training-inference-and-the-maarten-test)
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

### 2a. The Problem — When Labeled Data is Scarce

Full fine-tuning needed thousands of labeled examples. In the real world, that is often a luxury you do not have.

*Imagine you are a startup founder building a complaint classifier for a niche industry — say, agricultural insurance. There are no public datasets. To label 5,000 complaints by hand, you need a domain expert sitting at a desk for weeks. At, say, \$50 per hour and 30 seconds per example, 5,000 labels cost about \$2,000 and 40 hours of expert time you could spend elsewhere. What if you could get away with labeling only 32 examples — half an hour of work?*

This is the few-shot setting. You hand-pick a tiny set of high-quality examples per class — sometimes as few as 8 or 16 — and a clever framework squeezes maximum signal out of them.

The framework that delivers on this promise is **SetFit** (Sentence Transformer Fine-tuning), built on top of the `sentence-transformers` library. Its key insight, which we will unpack carefully, is that even from a handful of labeled examples we can manufacture *thousands* of training signals by generating sentence *pairs* and using contrastive learning. Same-class pairs are pulled together in embedding space; different-class pairs are pushed apart.

```
The few-shot setting (illustrated):

   Labeled data (just 4 examples!)
   ┌─────────────────────────────────┬──────────────┐
   │ "What a horrible movie..."      │  0 negative  │
   │ "Very disappointed"             │  0 negative  │
   │ "Some flaws but a great film"   │  1 positive  │
   │ "Best movie ever!"              │  1 positive  │
   └─────────────────────────────────┴──────────────┘
                       │
                       ▼
   Unlabeled query
   ┌─────────────────────────────────┬──────────────┐
   │ "Never want to see this again!" │      ?       │
   └─────────────────────────────────┴──────────────┘
```

### 2b. SetFit's Big Idea — Bird's-Eye View

Before zooming into each step, here is the entire SetFit pipeline on one page:

```
┌──────────────────┐    ┌─────────────────────┐    ┌────────────────────┐
│  STEP 1          │    │  STEP 2             │    │  STEP 3            │
│  Generate        │    │  Fine-tune the      │    │  Embed sentences   │
│  positive +      │ ─> │  pretrained         │ ─> │  with the tuned    │
│  negative        │    │  SentenceTransformer│    │  model and train   │
│  sentence pairs  │    │  via contrastive    │    │  a tiny classifier │
│  from few labels │    │  learning           │    │  (logistic reg.)   │
└──────────────────┘    └─────────────────────┘    └────────────────────┘
        ↑                          ↑                          ↑
   tiny labels             embeddings learn             classifier learns
   become 1000s            "same class = close"         on the now-tuned
   of pairs                "different = far apart"      embeddings
```

The genius is in Step 1 — turning a labeling shortage into a pair surplus. Steps 2 and 3 are then standard contrastive learning followed by a small classifier on top. Let us walk through each step.

### 2c. Step 1 — Sampling Training Pairs

SetFit acts like a matchmaker. It treats two sentences from the same class as a *positive pair* (these should look similar in embedding space) and two sentences from different classes as a *negative pair* (these should look dissimilar).

For a single class with $n$ labeled sentences, the number of unique unordered pairs is the well-known combination formula:

$$\text{pairs per class} = \binom{n}{2} = \frac{n(n-1)}{2}$$

This is exactly the formula for *"how many handshakes happen in a room of $n$ people if everyone shakes hands with everyone else exactly once"*. With 16 people, that is $16 \times 15 / 2 = 120$ handshakes — and 120 positive training pairs per class.

*Dry-run with 4 sentences — the example used in Figure 11-9 of the book (programming languages vs pets):*

```
Programming-languages class (n = 2):
  P1 = "I write my code in Python"
  P2 = "I should practice SQL"

Pets class (n = 2):
  Q1 = "My dog is a labrador"
  Q2 = "I have a Siamese cat"

Within-class pairs → POSITIVE (similar):
  (P1, P2)   ✓   both about coding
  (Q1, Q2)   ✓   both about pets

Cross-class pairs → NEGATIVE (dissimilar):
  (P1, Q1)   ✗
  (P1, Q2)   ✗
  (P2, Q1)   ✗
  (P2, Q2)   ✗

Total: 2 positives + 4 negatives = 6 pairs from only 4 sentences.
```

Notice how aggressively the data multiplied — 4 examples turned into 6 training signals. The bigger the dataset, the more dramatic this leverage:

```
n per class:    1     2     4     8     16     32
positive pairs: 0     1     6     28    120    496      ← n(n-1)/2

  ↑
  fast quadratic growth — doubling n almost quadruples the pairs
```

The book's actual experiment uses 16 examples per class on Rotten Tomatoes (32 total). With `num_iterations=20`, SetFit cycles through pair generation 20 times, drawing fresh negative partners each pass:

$$\text{total pairs} = \underbrace{20}_{\text{iterations}} \times \underbrace{32}_{\text{total samples}} \times \underbrace{2}_{\substack{\text{one positive} \\ +\text{ one negative}\\ \text{per sample}}} = 1{,}280$$

Walk through it slowly: we have 32 labeled examples. For each example, every iteration produces two pairs — one same-class partner (positive) and one different-class partner (negative). That is $32 \times 2 = 64$ pairs per iteration. Over 20 iterations: $64 \times 20 = 1{,}280$. The training log confirms exactly this:

```
***** Running training *****
  Num unique pairs = 1280
  Batch size = 16
  Num epochs = 3
  Total optimization steps = 240
```

**1,280 training signals from 32 labeled documents — a 40× amplification.** This pair multiplication is the magic that makes few-shot learning competitive with full fine-tuning.

### 2d. Step 2 — Contrastive Fine-Tuning of the Embedding Model

The 1,280 pairs from Step 1 are used to fine-tune a pretrained `SentenceTransformer` (specifically `sentence-transformers/all-mpnet-base-v2`, one of the strongest models on the MTEB benchmark). The training method is **contrastive learning**, which we already met when training embedding models in Chapter 10.

#### The intuition first

Imagine training a puppy to play "same or different". You hold up two photos of cats and say *"same!"* — the puppy learns these belong together. You hold up a cat and a dog and say *"different!"* — the puppy learns to keep these apart. Repeat thousands of times and the puppy builds a mental map where cats cluster in one region and dogs in another.

The embedding model does exactly this, but in a 768-dimensional vector space and with movie-review sentences instead of pet photos. The "puppy" is BERT.

#### The Siamese architecture

Both sentences in a pair are pushed through the *same* BERT encoder (this shared-weight trick is called a **Siamese network** — twins by construction). The encoder turns each sentence into one sentence-embedding vector via mean pooling over its token embeddings.

```
Sentence A: "I write code in Python"     Sentence B: "My dog is a labrador"
        │                                            │
        ▼                                            ▼
   ┌─────────┐                                 ┌─────────┐
   │  BERT   │  ←── shared weights ──→         │  BERT   │
   └─────────┘                                 └─────────┘
        │                                            │
   ┌─────────┐                                 ┌─────────┐
   │ Pooling │  ←── mean over tokens ──→       │ Pooling │
   └─────────┘                                 └─────────┘
        │                                            │
        ▼                                            ▼
        u  (768-dim sentence vector)                 v  (768-dim sentence vector)
        │                                            │
        └─────────────────┬──────────────────────────┘
                          ▼
              concat(u, v, |u − v|)   ← 768·3 = 2304-dim feature
                          │
                          ▼
                     [Softmax]
                          │
                          ▼
            "same class"  or  "different class"
```

The features fed to softmax are not just $u$ and $v$ separately — they also include $|u - v|$, the element-wise absolute difference. Why?

#### Why the $|u - v|$ feature is essential

Two embedding vectors $u$ and $v$ alone tell the classifier *where each sentence sits* in embedding space, but not *how far apart they are from each other*. The classifier would have to learn a notion of distance from scratch. By feeding $|u - v|$ explicitly, we hand the classifier a ready-made distance signal — one number per dimension.

*Dry-run with tiny 3-D embeddings* (real ones are 768-D, but 3-D fits on the page and the geometry is identical):

```
POSITIVE PAIR (same class — both are positive movie reviews)

  u = "Some flaws but a great film"   →  [ 0.60,  0.10,  0.30]
  v = "Best movie ever!"              →  [ 0.55,  0.15,  0.35]

  |u − v| = [|0.60 − 0.55|, |0.10 − 0.15|, |0.30 − 0.35|]
          = [ 0.05,  0.05,  0.05]   ← tiny distances → vectors are close

  concat(u, v, |u − v|) =
       [0.60, 0.10, 0.30,  0.55, 0.15, 0.35,  0.05, 0.05, 0.05]
        └──── u ─────┘     └──── v ─────┘     └─── |u−v| ───┘
                                                tells softmax: "close!"


NEGATIVE PAIR (different classes — positive vs negative review)

  u  = "Some flaws but a great film"  →  [ 0.60,  0.10,  0.30]
  v' = "What a horrible movie"        →  [-0.40,  0.70, -0.20]

  |u − v'| = [|0.60 + 0.40|, |0.10 − 0.70|, |0.30 + 0.20|]
           = [ 1.00,  0.60,  0.50]   ← large distances → vectors are far

  concat(u, v', |u − v'|) =
       [0.60, 0.10, 0.30, -0.40, 0.70, -0.20,  1.00, 0.60, 0.50]
                                                └──── |u−v'| ────┘
                                                tells softmax: "far!"
```

The softmax classifier now has a trivial learning task: small $|u-v|$ → predict "same"; large $|u-v|$ → predict "different".

The interesting work happens during *backpropagation*. The gradient of the loss flows backward through the softmax, through the $|u-v|$ subtraction, through the pooling, and into BERT's weights. The gradient is essentially saying to BERT: *"For positive pairs, you produced embeddings that were too far apart — pull them closer next time. For negative pairs, you produced embeddings that were too close — push them apart."*

After many such updates over the 1,280 pairs, BERT's embedding space *reorganises itself* into class-aware clusters.

#### The embedding space — before and after

Visualising the embedding space in 2-D (it is really 768-D but the geometry rhymes):

```
BEFORE fine-tuning — generic embedding space
(clusters by topic, not by class — useless for our task)

         ★ "Some flaws but a great film"
                                    ★ "Best movie ever!"
   ✗ "Very disappointed"
                          ✗ "What a horrible movie"

   ★ and ✗ are mixed together. The pretrained model groups
   sentences by "movie-talk" in general, not by sentiment.


AFTER contrastive fine-tuning — class-specialised space

   ★ ★                           ← positive cluster (collapsed together)


                          ✗ ✗   ← negative cluster (collapsed together)

   Same class collapsed to one region. Different classes pushed apart.
   A simple straight line can now separate them.
```

This is the heart of SetFit: we have not changed BERT's architecture or trained it from scratch. We have just *rotated and stretched* an already-good embedding space so that the directions that matter for our task become the dominant ones.

#### The loss in one line

For one pair with feature $f = [u,\ v,\ |u-v|]$ and binary label $y \in \{1, 0\}$ (1 = same, 0 = different), the softmax classifier produces probabilities $p_{\text{same}}, p_{\text{diff}}$ and the loss is plain binary cross-entropy:

$$\mathcal{L} = -\,y \log(p_{\text{same}}) \;-\; (1 - y) \log(p_{\text{diff}})$$

This loss is computed for each of the 1,280 pairs, averaged across mini-batches of 16, and backpropagated. After 3 epochs and 240 optimisation steps (1,280 pairs ÷ 16 batch size × 3 epochs), the embedding space is task-specialised.

### 2e. Step 3 — Train a Classifier on the Specialised Embeddings

The fine-tuned `SentenceTransformer` from Step 2 now produces *task-aware* embeddings. We feed every labeled training sentence through it once, collect its embedding, and train a tiny classifier — by default scikit-learn's `LogisticRegression` — on those embeddings.

Why is plain logistic regression suddenly sufficient? Because Step 2 made the data *linearly separable*. The embedding model has done the hard work of clustering same-class points together. A simple linear boundary now gets near-perfect accuracy.

```
Step 3 — embed and classify:

"I write my code in Python"   →  [0.23, -0.41, 0.88, ...]  ──┐
"I should practice SQL"        →  [0.19, -0.38, 0.91, ...]  ──┤  Logistic
"My dog is a labrador"         →  [-0.71, 0.52, -0.12, ...] ──┤  Regression
"I have a Siamese cat"         →  [-0.69, 0.55, -0.10, ...] ──┘
                                              │
                                              ▼
                                    learns a linear boundary
                                              │
                                              ▼
At inference:
"I love writing scripts"   →  [0.21, -0.39, 0.85, ...]  →  Code: 87%, Pets: 13%
```

The book demonstrates this on three test sentences in Figure 11-12: *"I write my code in Python"* → 79% Code, *"I should practice SQL"* → 93% Code, *"My dog is a labrador"* → 85% Pets. The classifier reliably picks the right class because the embeddings have already done the heavy lifting.

If a logistic regression is not expressive enough for your task, SetFit also supports a *differentiable* classification head — a small neural network trained jointly with the embedding model. For most few-shot scenarios, the default logistic regression is plenty.

### 2f. Implementation in Code

Putting all three steps together is mercifully short:

```python
from setfit import sample_dataset, SetFitModel
from setfit import TrainingArguments as SetFitTrainingArguments
from setfit import Trainer as SetFitTrainer

# Step 0: simulate few-shot — only 16 examples per class
sampled_train_data = sample_dataset(tomatoes["train"], num_samples=16)
# Total: 32 labeled documents

# Load a pretrained SentenceTransformer (this is what Step 2 will fine-tune)
model = SetFitModel.from_pretrained("sentence-transformers/all-mpnet-base-v2")

# Configure SetFit training
args = SetFitTrainingArguments(
    num_epochs=3,        # epochs of contrastive learning over the pairs
    num_iterations=20,   # how many pair combinations to generate per sample
)

trainer = SetFitTrainer(
    model=model,
    args=args,
    train_dataset=sampled_train_data,
    eval_dataset=tomatoes["test"],
    metric="f1",
)

trainer.train()
```

What is happening under the hood mapped to the three steps:

- `num_iterations=20` controls **Step 1** — how aggressively to multiply pairs.
- `num_epochs=3` controls **Step 2** — how many times to sweep through the pairs during contrastive fine-tuning.
- The classifier in **Step 3** is logistic regression by default; no separate epoch setting is needed because logistic regression has a closed-form-ish optimisation.

If you want a custom (differentiable) head instead of logistic regression:

```python
model = SetFitModel.from_pretrained(
    "sentence-transformers/all-mpnet-base-v2",
    use_differentiable_head=True,
    head_params={"out_features": 2},  # number of classes
)
```

### 2g. Results and the Zero-Shot Extension

Evaluating on the full Rotten Tomatoes test set:

```python
trainer.evaluate()
# {'f1': 0.8363988383349468}
```

**F1 ≈ 0.85 with only 32 labeled documents.** Compare against the alternatives:

| Approach                           | Labeled data | F1   |
|------------------------------------|--------------|------|
| Ch4 frozen pretrained model        | 8,500        | 0.80 |
| Full fine-tune (Section 1)         | 8,500        | 0.85 |
| **SetFit (Section 2)**             | **32**       | **0.85** |

SetFit matches full fine-tuning while using **265× less labeled data** (8,500 ÷ 32). That is not a typo. The pair-generation trick, combined with contrastive learning's geometric reorganisation of embedding space, recovers almost all the signal that thousands of additional labels would have provided.

#### Zero-shot — when you have *no* labels at all

What if you do not even have 32 examples? Maybe you just stood up a new product and no labeled data exists yet. SetFit handles this too via **zero-shot classification**.

The trick: synthesise training examples directly from the *names of the labels*. If your classes are named `"happy"` and `"sad"`, SetFit fabricates synthetic sentences like:

```
Synthetic labeled examples (manufactured from label names):

  "This example is happy"   → label: happy
  "This example is sad"     → label: sad

  (then SetFit treats these as labeled few-shot data
   and runs Steps 1–3 normally on them)
```

The synthetic sentences are obviously simplistic — but the pretrained `SentenceTransformer` already understands the semantics of "happy" vs "sad" because it has seen those words millions of times during its original pretraining. Step 2's contrastive learning then reorganises the embedding space around those label-name concepts. Real test sentences carrying happy or sad sentiment land in the right cluster.

This is a remarkable cold-start capability. With nothing more than the *names* of your classes, you can stand up a working classifier — admittedly weaker than a few-shot one, but a solid starting point. As you collect a handful of real labeled examples over time, you can re-run SetFit with that few-shot data and watch performance climb.

The takeaway from the entire SetFit section: **few-shot learning is not magic — it is clever data multiplication plus geometry-aware fine-tuning.** Step 1 manufactures pairs, Step 2 reshapes the embedding space so classes separate, Step 3 reads off the now-easy classification with a tiny linear model. Whenever you face a labeling bottleneck, this is the first tool to reach for.

---

## 3. Continued Pretraining with Masked Language Modeling

### 3a. Why Generic Pretraining Falls Short

BERT was originally pretrained on English Wikipedia and the Books corpus — a broad, general collection of text. This makes it an excellent general-purpose language model. But "general-purpose" comes at a cost: BERT knows what Wikipedia talks about (history, science, politics) and not what *your* domain talks about.

*Imagine hiring a brilliant generalist doctor who has read every textbook on Earth. She can diagnose a cold or a sprained ankle anywhere in the world. Now place her in a specialised cardiology unit. She knows what "myocardial infarction" means in a textbook, but the *patterns of usage* — how cardiologists actually write about it in patient charts, the abbreviations, the implicit conventions — she has never internalised those. Give her a few weeks rotating in the unit and her language adapts. She is now fluent in cardiology English, a sub-dialect of English. That is exactly what continued pretraining does to BERT.*

Concrete examples of where this matters:

- **Medical NLP** — BERT has rarely seen *"myocardial infarction"* or *"bradycardia"* in pretraining. Its representations for medical terminology are blurry.
- **Legal NLP** — Terms like *"amicus curiae"*, *"tort"*, and *"promissory estoppel"* are vanishingly rare in Wikipedia.
- **Movie reviews** (our case) — Words like *"cinematography"*, *"screenplay"*, *"blockbuster"* do appear, but their *sentiment-laden* usage patterns in reviews differ from Wikipedia's neutral descriptions.

The fix is **continued pretraining**: take the already-pretrained BERT and *keep training it with the same MLM objective*, but now on your domain data. You are not training from scratch — you are *adapting* an existing model.

### 3b. The Three-Step Pipeline at a Glance

The standard fine-tuning pipeline has two phases — pretraining (done by Google for us) and fine-tuning. Continued pretraining squeezes a third phase between them:

```
Standard 2-step pipeline:

  ┌─────────────────────────┐    ┌─────────────────────────┐
  │  PRETRAINING            │    │  FINE-TUNING            │
  │  from scratch on        │ ─> │  on target task         │
  │  Wikipedia + books      │    │  (classification head)  │
  └─────────────────────────┘    └─────────────────────────┘


Domain-adapted 3-step pipeline:

  ┌─────────────────┐   ┌──────────────────────┐   ┌──────────────────┐
  │  PRETRAINING    │   │  CONTINUED           │   │  FINE-TUNING     │
  │  from scratch   │ ─>│  PRETRAINING         │ ─>│  on target task  │
  │  on Wikipedia   │   │  on domain data      │   │  (classification │
  │  (done for us)  │   │  with MLM objective  │   │   head)          │
  └─────────────────┘   └──────────────────────┘   └──────────────────┘
        ↑                          ↑                          ↑
   General BERT             Domain-adapted BERT         Task-specific BERT
   (Wikipedia English)     (movie-review English)      (sentiment classifier)
```

For an organisation with a lot of internal text, this pipeline becomes especially powerful — one continued-pretraining run produces a domain backbone that can be fine-tuned for many downstream tasks:

```
[General BERT (public)]
        │
        ▼
[ACME-BERT (domain-adapted on ACME company data)]
        │              │                    │
        ▼              ▼                    ▼
   [Topic         [Semantic            [Named-Entity
    classifier]    search]              Recognition]
```

You pay the domain-adaptation cost once and reuse the result everywhere. This is highly efficient.

### 3c. What is Masked Language Modeling, Really

**Masked Language Modeling** (MLM) is the pretext task BERT was originally trained on. The recipe is brutally simple: take a sentence, randomly hide 15% of its tokens by replacing them with a special `[MASK]` token, and ask the model to predict what the masked words were. Repeat for billions of sentences.

*Plain-language analogy:* Imagine playing the world's most punishing fill-in-the-blank game. Given the sentence *"What a horrible [MASK]!"*, you must guess what the missing word was. To make a sensible guess, you cannot just stare at the [MASK] in isolation — you must read the entire sentence around it and reason about what fits. Now play this game eight hundred million times. By the end, you have an extremely deep grasp of how English works, because every guess required understanding context.

#### Why hiding tokens forces deep understanding

A model trained on this task cannot cheat. It cannot copy the word verbatim — the word has been hidden. It cannot look up nearby words in a dictionary — there is no dictionary. It must learn that *"horrible"* tends to be followed by nouns describing experiences (*movie, day, idea, mistake*) and that *"What a [MASK]!"* almost always wraps around a noun. Each correct guess pushes BERT's internal representations toward something that captures genuine linguistic structure.

Crucially, MLM is *bidirectional* — when predicting a masked word, BERT can attend to tokens both before *and* after the mask. This is unlike causal language modeling (used by GPT-style decoders), which only attends to past tokens. Bidirectionality gives MLM-trained encoders their characteristic strength on understanding tasks.

```
Causal LM (GPT-style):                  MLM (BERT-style):
  Predict next word                       Predict masked word
  using only past context                 using past + future context

  "What a horrible [?]"                   "What a [?] movie!"
        ↑                                          ↑
   only sees "What a horrible"            sees "What a"  AND  "movie!"
```

#### Architecture — what the MLM head looks like

Sequence classification attaches a small head on top of the [CLS] token vector to produce 2 class scores. **MLM is the same idea but at every token position and with a much bigger output:** at each masked position, BERT projects its 768-dim hidden state to a vocab-sized vector (28,996 dims for `bert-base-cased`), then softmax gives a probability distribution over the entire vocabulary.

```
Sequence-classification head:

  hidden_state[CLS]           (768-dim)
         │
         ▼
   Linear(768 → 2)            ← small head, 1,536 weights
         │
         ▼
   softmax → P(positive), P(negative)


MLM head (per masked token):

  hidden_state[at masked position]   (768-dim)
         │
         ▼
   Linear(768 → 28,996)        ← huge head, ~22M weights
         │
         ▼
   softmax → P(token_0), P(token_1), ..., P(token_28995)
                ↑
        we read off the probability for the true masked token
```

In practice, BERT *ties* the MLM output projection weights to the input embedding matrix — both are shape (28,996, 768), saving parameters and forcing input and output token representations to live in the same space. This is a detail you do not need to hand-implement; the `AutoModelForMaskedLM` class handles it.

### 3d. A Dry-Run — One MLM Training Step

Let us trace exactly what happens when MLM trains on one tiny example.

```
Step 1 — Original sentence
  Sentence:   "What a horrible movie!"
  Tokens:     [CLS] what a horrible movie ! [SEP]
  Token IDs:  [101, 2054, 1037, 9202, 3185, 999, 102]   ← made up for illustration
                ↑                          ↑
            special                    real word

Step 2 — Random masking (15% of real tokens)
  We have 5 real tokens (excluding [CLS] and [SEP]).
  15% of 5 = 0.75 → round up: mask 1 token.
  Random pick: position 4 ("movie").

  After masking:
  [CLS] what a horrible [MASK] ! [SEP]
                          ↑
                    was "movie"

Step 3 — Forward pass through BERT
  BERT outputs one 768-dim hidden state per token. We only care about
  the masked position (index 4).

  hidden[4] = [0.31, -0.42, 0.18, ..., 0.05]    (768 numbers)

Step 4 — MLM head: project to vocab
  logits = Linear(768 → 28996) (hidden[4])
  logits = [-1.2, 0.4, -0.8, ..., 0.1]          (28,996 numbers)

Step 5 — Softmax over the entire vocabulary
  probs = softmax(logits)
  probs[id_of("movie")] = 0.012     ← model gives "movie" a 1.2% chance
  probs[id_of("idea")]  = 0.045     ← thinks "idea" is more likely
  probs[id_of("dream")] = 0.038
  probs[id_of("day")]   = 0.029
  ...

Step 6 — Cross-entropy loss against the true token
  true_token = "movie",  id = 3185
  loss = -log(probs[3185]) = -log(0.012) ≈ 4.42

  Reference points:
    Random guessing across 28,996 tokens → loss ≈ -log(1/28996) ≈ 10.27
    Base BERT on this sentence            → loss ≈ 4-5  (close-ish)
    Domain-adapted BERT                   → loss ≈ 0.5  (very confident)

Step 7 — Backpropagation
  Gradients flow from this loss back through the MLM head, through all
  12 BERT encoder blocks, all the way to the embeddings. Every weight
  gets a tiny nudge that would, next time, raise
  P("movie" | "What a horrible ___") slightly.
```

The training loop runs this routine over millions (or in our case, thousands) of sentences. The cumulative effect is that BERT's representations gradually shift to reflect *movie-review English* — the words and phrasings of our domain.

#### Why 15% specifically?

The 15% masking ratio is a Goldilocks number from the original BERT paper. Mask too few tokens (say 5%) and the training signal is sparse — most positions contribute nothing to the loss. Mask too many (say 50%) and the surrounding context becomes too gappy for the model to make confident predictions. 15% is roughly one masked token in every six or seven, which keeps context dominant while providing dense enough supervision.

### 3e. Token vs Whole-Word Masking

BERT's WordPiece tokenizer splits rare or compound words into subwords. For example, *"vocalization"* becomes `vocal` + `##ization` (the `##` means "this piece continues the previous word"). This raises a subtle question for MLM: when we randomly select 15% of tokens to mask, should subwords of the same word be masked independently, or as a group?

```
Input:                Her   vocal   ##ization   was   remarkably   melodic

Token masking:        Her   vocal   [MASK]      was   remarkably   melodic
                                      ↑
                            Only the "##ization" subword is masked.
                            Easy to guess — "vocal" is right next to it!
                            BERT can lazily exploit subword cues.

Whole-word masking:   Her   [MASK]  [MASK]      was   remarkably   melodic
                              ↑       ↑
                       Both subwords of "vocalization" are masked together.
                       Harder — BERT must infer the whole concept from
                       sentence-level context.
```

Whole-word masking produces stronger representations because it forces the model to reason about complete concepts rather than exploit morphological shortcuts. The cost: it converges more slowly. The book uses plain token masking for faster turnaround in this example. To switch to whole-word masking, replace `DataCollatorForLanguageModeling` with `DataCollatorForWholeWordMask` — same recipe, harder masking strategy.

### 3f. Continued Pretraining in Practice

We now wire up the actual training. The structural change from Section 1 is that we use `AutoModelForMaskedLM` instead of `AutoModelForSequenceClassification` — this loads BERT with the MLM head (vocab-sized output) attached.

```python
from transformers import AutoTokenizer, AutoModelForMaskedLM

# Load model with the MLM head, not the classification head
model = AutoModelForMaskedLM.from_pretrained("bert-base-cased")
tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")
```

#### Tokenize without labels

MLM is *unsupervised* — we do not need the sentiment labels. We strip them off so the Trainer does not try to use them.

```python
def preprocess_function(examples):
    return tokenizer(examples["text"], truncation=True)

tokenized_train = train_data.map(preprocess_function, batched=True)
tokenized_train = tokenized_train.remove_columns("label")   # ← key step
tokenized_test  = test_data.map(preprocess_function, batched=True)
tokenized_test  = tokenized_test.remove_columns("label")
```

#### The DataCollator — masking happens here, dynamically

`DataCollatorForLanguageModeling` is where the masking magic happens. Every time a batch is formed, this collator picks a fresh random 15% of tokens to mask. This means the model never sees the same masked version of a sentence twice — over multiple epochs, BERT effectively gets infinitely many distinct masking patterns. This *dynamic* masking is a richer training signal than fixing the masks once at the start.

```python
from transformers import DataCollatorForLanguageModeling

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=True,                # MLM (vs causal LM)
    mlm_probability=0.15,    # mask 15% of tokens per sentence
)
```

#### Training arguments — why 10 epochs?

```python
training_args = TrainingArguments(
    "model",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=10,        # ← MLM needs many more epochs than classification
    weight_decay=0.01,
    save_strategy="epoch",
    report_to="none",
)
```

Why 10 epochs vs 1 for classification? Classification is a sharply defined task with a clear binary signal — one pass through 8,500 examples is enough. MLM is much harder: the model has to predict the right token out of 28,996 possibilities at every masked position. Each epoch gives only a faint signal per token. Stacking 10 epochs lets BERT slowly accumulate domain knowledge.

#### Save the tokenizer first, train, then save the model

```python
tokenizer.save_pretrained("mlm")   # tokenizer doesn't change, save it now

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_test,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

trainer.train()

model.save_pretrained("mlm")       # save the domain-adapted model after training
```

The `mlm/` folder now contains a BERT that has been adapted to movie-review English.

### 3g. Probing What the Model Learned

The most satisfying part of continued pretraining is *seeing* the difference. The `fill-mask` pipeline lets you ask the model to complete a sentence with a `[MASK]` and returns the top predictions.

#### Before — generic BERT

```python
from transformers import pipeline

mask_filler = pipeline("fill-mask", model="bert-base-cased")
preds = mask_filler("What a horrible [MASK]!")
for pred in preds:
    print(pred["sequence"])
```

```
>>> What a horrible idea!
>>> What a horrible dream!
>>> What a horrible thing!
>>> What a horrible day!
>>> What a horrible thought!
```

Generic BERT, fresh from Wikipedia, fills the blank with abstract concepts: *idea*, *dream*, *thought*. It has no special association with the movie domain.

#### After — domain-adapted BERT

```python
mask_filler = pipeline("fill-mask", model="mlm")   # ← our adapted model
preds = mask_filler("What a horrible [MASK]!")
for pred in preds:
    print(pred["sequence"])
```

```
>>> What a horrible movie!
>>> What a horrible film!
>>> What a horrible mess!
>>> What a horrible comedy!
>>> What a horrible story!
```

Same model architecture, same query, completely different predictions. After 10 epochs of MLM on movie reviews, BERT now associates *"What a horrible ___"* with movie-review vocabulary. *Movie*, *film*, *comedy* — the model has *internalised our domain*. This is a direct window into what the gradient updates accomplished.

The probabilistic gap is even more telling. For the same sentence:

| Model              | P(*"movie"* \| *"What a horrible ___"*) |
|--------------------|-----------------------------------------|
| Base BERT          | ≈ 0.012                                 |
| Domain-adapted BERT| ≈ 0.30 or higher                        |

The model has not just learned a single new word — it has restructured its entire conditional probability distribution over vocabulary in our domain.

### 3h. Connecting Back to Classification

The whole point of this exercise is to use the domain-adapted model for the *actual* downstream task — sentiment classification. The shift is one line: load the saved model with `AutoModelForSequenceClassification` instead of `AutoModelForMaskedLM`. The MLM head is discarded; a fresh classification head is attached on top of the now-domain-adapted BERT body.

```python
from transformers import AutoModelForSequenceClassification

model = AutoModelForSequenceClassification.from_pretrained("mlm", num_labels=2)
tokenizer = AutoTokenizer.from_pretrained("mlm")

# From here, follow the exact Section 1 recipe:
#   - tokenize with DataCollatorWithPadding
#   - TrainingArguments + Trainer
#   - trainer.train()
```

Conceptually:

```
[Domain-adapted BERT body]   ←  trained for 10 MLM epochs on movie reviews
        │
        ▼
[Classification head]         ←  freshly initialised, 768 → 2 weights
        │
        ▼
   sentiment label
```

When this combined model is fine-tuned, it starts from a much better foundation than vanilla BERT for movie reviews. The body already understands movie-review vocabulary; the head just needs to learn *which* movie-review patterns indicate positive vs negative sentiment.

Continued pretraining gives the largest gains when:

- The target domain differs significantly from Wikipedia (medical, legal, code, financial)
- You have a lot of unlabeled domain data, which is usually cheap to collect
- The downstream task has limited labeled data, since the unsupervised pretraining provides much of the heavy lifting

For a domain like movie reviews, which BERT has *some* exposure to via Wikipedia, the lift from continued pretraining is modest. For a domain like clinical notes, the lift can be 5–10 F1 points or more.

---

## 4. Named-Entity Recognition

### 4a. What is NER and Why It Matters

Every classification task we have met so far assigns *one label per document*. A movie review gets one sentiment label. An email gets one topic label. NER is fundamentally different: it assigns *one label per word* (or more precisely, per token).

*Plain-language analogy:* Imagine reading a printed page with a highlighter in your hand. You are told to highlight every person's name in yellow, every place in green, every company in blue, and leave everything else uncoloured. That is exactly what NER does — except the highlighting is done by a model, the categories are encoded as labels, and the page might be a billion words long.

```
"I am Maarten and I live in the Netherlands."
 │  │   │       │  │   │   │   │
 ▼  ▼   ▼       ▼  ▼   ▼   ▼   ▼
 O  O  PERSON   O  O   O   O  LOCATION

   ("O" = Outside — not a named entity)
```

Why this matters in practice:

- **De-identification** — automatically removing patient names from clinical notes before sharing data for research
- **Information extraction** — finding every company mentioned in a corpus of news articles
- **Entity linking** — connecting *"Elon Musk"* in a text to a knowledge-base entry
- **Question answering** — knowing which words are locations to answer *"Where does X live?"*

Wherever you need to pull *structured information* out of *unstructured text*, NER is the first stop.

### 4b. From Document Classification to Token Classification

Architecturally, NER changes one thing about how we use BERT: instead of pooling all token hidden states into a single [CLS] vector and classifying *that*, we keep the per-token hidden states and classify *each one individually*.

```
Sequence classification (Sections 1–3):

  Input tokens →  [BERT]  → 12 hidden vectors (one per token)
                              │
                              ▼
                    pool to [CLS] vector  (one 768-dim vector for the whole sentence)
                              │
                              ▼
                    Linear(768 → 2)
                              │
                              ▼
                    "Positive"  or  "Negative"


Token classification (NER):

  Input tokens →  [BERT]  → 12 hidden vectors (one per token)
                              │  │  │  ...  │
                              ▼  ▼  ▼       ▼
                  Linear(768 → 9) at every position
                              │  │  │  ...  │
                              ▼  ▼  ▼       ▼
                  One label per token: O, O, B-PER, I-PER, ...
```

The model is otherwise identical — same encoder, same pretrained weights, same forward pass. Only the head changes: from a single 768→2 head on the [CLS] vector to a 768→9 head applied at every token position. The loss is per-token cross-entropy, summed across every non-special token in the batch.

### 4c. The CoNLL-2003 Dataset

The book uses the English version of **CoNLL-2003**, a classic NER benchmark with about 14,000 training sentences. Each sentence ships with word-level annotations for four entity types.

```python
from datasets import load_dataset

dataset = load_dataset("conll2003", trust_remote_code=True)

example = dataset["train"][848]
example
```

```
{'id': '848',
 'tokens':     ['Dean', 'Palmer', 'hit', 'his', '30th', 'homer', 'for', 'the', 'Rangers', '.'],
 'pos_tags':   [22, 22, 38, 29, 16, 21, 15, 12, 23, 7],
 'chunk_tags': [11, 12, 21, 11, 12, 12, 13, 11, 12, 0],
 'ner_tags':   [1, 2, 0, 0, 0, 0, 0, 0, 3, 0]}
```

The `ner_tags` array is what we care about. Each integer corresponds to a label in the BIO scheme. Decoding the example sentence:

```
Token:    Dean    Palmer   hit   his   30th   homer   for   the   Rangers   .
ner_tag:    1        2      0     0     0       0      0     0       3      0
Label:    B-PER   I-PER     O     O     O       O      O     O    B-LOC     O

Decoded entities:  "Dean Palmer" → PERSON
                   "Rangers"     → LOCATION  (a sports team treated as a location here)
```

The four entity types are:

| Type | Meaning                                  |
|------|------------------------------------------|
| PER  | Person names                             |
| ORG  | Organisations                            |
| LOC  | Locations                                |
| MISC | Miscellaneous (events, nationalities…)   |

### 4d. The BIO Tagging Scheme

Named entities often span multiple words. *"Dean Palmer"* is one person, not two separate people called *Dean* and *Palmer*. *"New York Rangers"* is one organisation, not three separate things. We need a labelling scheme that can represent multi-word spans cleanly.

The answer is **BIO tagging**: **B**eginning, **I**nside, **O**utside.

- **B-XXX** — this token is the *first* token of an entity of type XXX
- **I-XXX** — this token *continues* an entity of type XXX that began earlier
- **O** — this token is not part of any named entity

#### Why we need both B and I

Consider the sentence *"London New York"* — two adjacent locations referring to two separate entities. Without the B/I distinction we could only write `LOC LOC`, which is ambiguous: is this *"London New York"* as one weird entity, or two separate entities back-to-back?

```
Without BIO (ambiguous):    "London"   "New"   "York"
                              LOC       LOC     LOC      ← one entity? two? three?

With BIO (unambiguous):     "London"   "New"   "York"
                             B-LOC     B-LOC   I-LOC     ← two entities:
                                                            "London" and "New York"
```

The presence of a fresh `B-` is the explicit signal *"a new entity starts here"*. This makes BIO sequences uniquely decodable.

#### The label-to-id mapping and a clever pattern

CoNLL-2003 maps the 9 BIO labels to integers like this:

```python
label2id = {
    "O": 0,
    "B-PER": 1,  "I-PER": 2,
    "B-ORG": 3,  "I-ORG": 4,
    "B-LOC": 5,  "I-LOC": 6,
    "B-MISC": 7, "I-MISC": 8,
}
```

Notice the pattern at a glance:

```
Label      ID    parity
─────     ───   ──────
"O":       0    even   (special — neither B nor I)
"B-PER":   1    odd    ← B-tags
"I-PER":   2    even   ← I-tags
"B-ORG":   3    odd
"I-ORG":   4    even
"B-LOC":   5    odd
"I-LOC":   6    even
"B-MISC":  7    odd
"I-MISC":  8    even
```

**Every B-tag has an odd ID. Every I-tag has an even ID. The I-tag for any entity type is exactly `B-tag + 1`.** This encoding is deliberate — the `align_labels` function exploits it to convert B-tags to I-tags with a single arithmetic operation, as we are about to see.

### 4e. The Subtoken Alignment Problem

This is the trickiest part of NER with BERT, and where most tutorials lose people. We will slow down and walk through it carefully.

**The problem.** The CoNLL-2003 dataset provides labels at the *word* level. But BERT's WordPiece tokenizer works at the *subword* level — it splits rare or complex words into pieces. Two examples:

```
Word:        "homer"
Subtokens:   "home"  "##r"             ← split into 2 pieces

Word:        "Maarten"
Subtokens:   "Ma"  "##arte"  "##n"     ← split into 3 pieces
```

The `##` prefix means *"this piece is a continuation of the previous word"*. After tokenisation we have *more tokens than we have labels*. The fix is to *align* word-level labels to subword-level tokens.

**The alignment rules:**

1. **Special tokens [CLS] and [SEP]** — no corresponding word. They get label `-100`, which tells PyTorch's cross-entropy loss to ignore these positions entirely (more on this in the next subsection).

2. **First subtoken of a word** — gets the word's original label, unchanged.

3. **Subsequent subtokens of the same word** — the subtle part:
   - If the word's label was `O`, all subtokens stay `O`.
   - If the word's label was `B-XXX`, subsequent subtokens become `I-XXX`. They are *part of* the same entity — they did not start a new one.

#### Dry-run with "Maarten" (label: B-PER)

```
Word:        Maarten
Word label:  B-PER

After tokenisation:
Subtoken:    Ma       ##arte    ##n
Position:    1st      2nd       3rd  (within the word)

Alignment:
  Ma:        B-PER    ← first subtoken, gets original label unchanged
  ##arte:    I-PER    ← continuation of an entity → B → I
  ##n:       I-PER    ← continuation → B → I
```

#### Full sentence dry-run — "My name is Maarten"

```
Input words:    My    name    is    Maarten
Word labels:    O     O       O     B-PER

After tokenisation:
Subtokens:   [CLS]   My    name    is    Ma     ##arte    ##n     [SEP]
Alignment:   -100    O     O       O     B-PER  I-PER     I-PER   -100
              ↑                          ↑     ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
           special                     first    continuations
           token                       sub-     become I-PER
           → -100                      token
                                       keeps
                                       B-PER
```

This matches Figure 11-21 in the book exactly. Now let us see the function that automates this.

### 4f. The `align_labels` Function — Trace Through

```python
def align_labels(examples):
    token_ids = tokenizer(
        examples["tokens"],
        truncation=True,
        is_split_into_words=True,    # ← tokens are already word-split
    )
    labels = examples["ner_tags"]
    updated_labels = []

    for index, label in enumerate(labels):
        word_ids = token_ids.word_ids(batch_index=index)
        previous_word_idx = None
        label_ids = []

        for word_idx in word_ids:
            if word_idx is None:
                # Case 1 — special token ([CLS] or [SEP])
                label_ids.append(-100)

            elif word_idx != previous_word_idx:
                # Case 2 — first subtoken of a new word
                label_ids.append(label[word_idx])

            else:
                # Case 3 — continuation subtoken of the same word
                updated_label = label[word_idx]
                if updated_label % 2 == 1:    # is it a B-tag?
                    updated_label += 1         # ... convert to the matching I-tag
                label_ids.append(updated_label)

            previous_word_idx = word_idx

        updated_labels.append(label_ids)

    token_ids["labels"] = updated_labels
    return token_ids
```

#### Why `% 2 == 1` is the right test

Recall the label2id pattern: B-tags are odd (1, 3, 5, 7), I-tags are even (2, 4, 6, 8), and `I-tag = B-tag + 1`. So the `+ 1` in Case 3 handles all four entity types in one line:

```
If updated_label is B-PER  (id 1, odd):  1 + 1 = 2 → I-PER  ✓
If updated_label is B-ORG  (id 3, odd):  3 + 1 = 4 → I-ORG  ✓
If updated_label is B-LOC  (id 5, odd):  5 + 1 = 6 → I-LOC  ✓
If updated_label is B-MISC (id 7, odd):  7 + 1 = 8 → I-MISC ✓

If updated_label is I-PER  (id 2, even): condition fails, leave as I-PER ✓
If updated_label is O      (id 0, even): condition fails, leave as O     ✓
```

One arithmetic check handles all four entity types correctly. This is why the label2id encoding was designed with that parity pattern in mind.

#### Why `-100` specifically?

The `-100` value is not arbitrary. PyTorch's `nn.CrossEntropyLoss` has a parameter `ignore_index` whose default is `-100`. Any token with label `-100` is silently skipped during loss computation — no gradient flows back from those positions. This is exactly the right behaviour for [CLS], [SEP], and padding tokens, which carry no entity information and should not contribute to training.

#### Verifying the output

```python
tokenized = dataset.map(align_labels, batched=True)

print("Original NER tags:", dataset["train"][848]["ner_tags"])
print("Aligned labels:   ", tokenized["train"][848]["labels"])
```

```
Original NER tags:  [1, 2, 0, 0, 0, 0, 0, 0, 3, 0]
Aligned labels:     [-100, 1, 2, 0, 0, 0, 0, 0, 0, 0, 3, 0, -100]
                      ↑                         ↑↑↑↑
                    [CLS]                    "homer" → "home" + "##r"
                    → -100                   both labelled O (unchanged because O is not a B-tag)
                                                                         ...and [SEP] → -100 at end
```

The aligned sequence is one element longer per sentence (because of [CLS] and [SEP]), with extra entries for any subword splits.

### 4g. Entity-Level Evaluation with seqeval

For NER, plain token-level accuracy is **dangerously misleading**. Here is why with a concrete worked example.

Suppose a test sentence has 100 tokens and only 2 of them belong to an entity (`Dean Palmer` → `B-PER I-PER`). The other 98 tokens are `O`.

```
A trivially bad model that predicts "O" for every single token gets:

  Token-level accuracy = 98 correct / 100 total = 98%   ← looks great!
  Entity-level recall  = 0 entities found / 1 total = 0%   ← actually useless
```

A model can score 98% on token accuracy while finding zero entities. That is the trap. **What we actually care about is whether named entities are correctly identified as complete spans.**

`seqeval` evaluates at the **entity level**:

- *"Dean Palmer"* counts as *one correct prediction* only if *both* *"Dean"* (B-PER) *and* *"Palmer"* (I-PER) are correctly labelled.
- Partial credit is not given — the whole entity span must match, including the type.

#### Worked example of entity-level F1

Say our test set contains these 4 ground-truth entities across some sentences:

```
Ground truth:
  1. "Dean Palmer"     → PER
  2. "Rangers"         → LOC
  3. "Berlin"          → LOC
  4. "Apple"           → ORG
```

The model predicts:

```
Predictions:
  1. "Dean Palmer"     → PER     ✓ exact match
  2. "Rangers"         → LOC     ✓ exact match
  3. "Berlin"          → LOC     ✓ exact match
  4. "Apple"           → PER     ✗ wrong type (should be ORG)
```

Entity-level counts:

```
True positives  (TP) = 3   (Dean Palmer, Rangers, Berlin)
False positives (FP) = 1   (predicted "Apple" as PER, but no PER entity exists there)
False negatives (FN) = 1   (the ORG entity "Apple" was missed)

Precision = TP / (TP + FP) = 3 / 4 = 0.75
Recall    = TP / (TP + FN) = 3 / 4 = 0.75
F1        = 2 · P · R / (P + R) = 0.75
```

Note how *getting the type wrong* costs us twice — it raises FP (we predicted something that wasn't there) *and* raises FN (we missed the real entity). seqeval gives no partial credit for getting the span right but the type wrong, nor for getting only one half of a multi-token entity. This strict scoring is what makes it the right metric for NER.

#### The compute_metrics function

```python
import evaluate
import numpy as np

seqeval = evaluate.load("seqeval")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=2)   # axis=2 because per-token

    true_predictions = []
    true_labels = []

    for prediction, label in zip(predictions, labels):
        for token_prediction, token_label in zip(prediction, label):
            if token_label != -100:                   # skip [CLS], [SEP], padding
                true_predictions.append([id2label[token_prediction]])
                true_labels.append([id2label[token_label]])

    results = seqeval.compute(
        predictions=true_predictions,
        references=true_labels,
    )
    return {"f1": results["overall_f1"]}
```

The `axis=2` is the only meaningful change from the sequence-classification metric — logits are now shape `(batch, seq_len, num_labels)` instead of `(batch, num_labels)`. We argmax over the label dimension at every token position, then filter out `-100` positions before passing to seqeval.

### 4h. Training, Inference, and the Maarten Test

The remaining pieces fall into place quickly.

#### Model loading

`AutoModelForTokenClassification` attaches the per-token classification head sketched in Section 4b:

```python
from transformers import AutoModelForTokenClassification

model = AutoModelForTokenClassification.from_pretrained(
    "bert-base-cased",
    num_labels=len(label2id),    # 9 labels (O + 4 entity types × 2 B/I)
    id2label=id2label,
    label2id=label2id,
)
```

#### Data collation

For NER we need `DataCollatorForTokenClassification` rather than `DataCollatorWithPadding`. The difference: it pads both the token IDs *and* the label sequences to the same length, keeping label and token sequences aligned.

```python
from transformers import DataCollatorForTokenClassification

data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
```

#### Training

```python
training_args = TrainingArguments(
    "model",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=1,
    weight_decay=0.01,
    save_strategy="epoch",
    report_to="none",
)

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

After one epoch on CoNLL-2003 the model reaches a strong entity-level F1 (around 0.92 in the book's run). Per token, the loss is the usual cross-entropy; the gradient updates flow through the 768→9 head and the underlying BERT body to push the right BIO tag to the top of the softmax at every non-special position.

#### Inference — the Maarten test

After saving the model, the `token-classification` pipeline runs end-to-end inference:

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

The model correctly identifies all three subtokens of *"Maarten"* as `B-PER`, `I-PER`, `I-PER` with very high confidence (>0.99 each). The subtoken alignment we did during training has paid off: BERT learned to treat the three subtokens as one continuous person entity. The `start`/`end` indices let downstream code recover the original character span and reconstruct the full word *"Maarten"*.

This closes the loop:

```
word-level labels                     (CoNLL-2003 ner_tags)
        │
        ▼  align_labels (handles subwords + special tokens)
subword-level labels with -100 padding
        │
        ▼  Trainer + per-token cross-entropy
trained token-classification model
        │
        ▼  pipeline("token-classification")
B-/I-/O tags on every subtoken
        │
        ▼  decode BIO spans
named entities with character offsets
```

The discipline at each step — particularly the subtoken alignment rules and the entity-level evaluation — is what makes NER work in practice with subword-tokenised models.

---

## 5. Key Takeaways and Decision Guide

### Performance Summary

| Approach | Task | Labelled data | F1 score | Training time |
|---|---|---|---|---|
| Ch4: frozen pretrained model | Sentiment | All (8,500) | 0.80 | None (inference only) |
| Full fine-tune (all layers) | Sentiment | All (8,500) | **0.85** | Moderate |
| Frozen BERT, train head only | Sentiment | All (8,500) | 0.63 | Fastest |
| Partial freeze (top 2 layers) | Sentiment | All (8,500) | 0.80 | Fast |
| SetFit (few-shot) | Sentiment | **32 examples** | **0.85** | Moderate |
| Continued pretrain + fine-tune | Sentiment | All + unlabelled domain | Better for OOD | Slow pretrain |
| Token classification | NER (CoNLL-2003) | ~14,000 sentences | ≈0.92 | Moderate |

The standout result: **SetFit achieves the same F1 as full fine-tuning on 8,500 examples — using only 32**. That is a 265× reduction in labelling cost with no loss in performance. If you ever face a labelling bottleneck, SetFit should be your first choice.

### A Quick Decision Tree

```
Q1 — Per-document or per-token labels?
    ├─ Per-token (NER, span extraction) ──────────────────────> Section 4
    └─ Per-document ↓

Q2 — How much labelled data per class?
    ├─ Fewer than ~100 per class ─────────────────────────────> SetFit (§2)
    │                                                          (zero-shot if 0 labels)
    └─ ≥ 100 per class ↓

Q3 — Is the domain very different from Wikipedia
     (medical, legal, code, internal company jargon)?
    ├─ Yes ───────────────────────────────────────────────────> Continued pretrain (§3)
    │                                                           → then fine-tune (§1)
    └─ No ↓

Q4 — Are you GPU-/time-constrained?
    ├─ Yes ───────────────────────────────────────────────────> Partial freeze (§1c)
    └─ No ────────────────────────────────────────────────────> Full fine-tune (§1)
```

This is a rough heuristic, not a law. The questions are ordered roughly by which factor most strongly forces a particular method.

### When to Use Which Approach

The decision depends on four factors: labelled data availability, domain specificity, compute budget, and task type.

If you have **abundant labelled data** and a **standard-domain task** (like general sentiment), full fine-tuning of all BERT layers produces the best results (§1b). It is the most direct path to a high-quality classifier and requires only a few minutes on a modern GPU.

If you have **very little labelled data** — fewer than 100 examples per class — reach for **SetFit** (§2). Its pair-generation trick multiplies your labelled data into thousands of contrastive training signals, and the worked example in §2c showed how 32 examples become 1,280 training pairs. The resulting model often matches full fine-tuning on much smaller budgets, and the zero-shot mode in §2g lets you stand up a working classifier with *no* labels at all.

If your domain has **specialised vocabulary** that BERT was not exposed to during pretraining — medical jargon, legal terminology, company-internal language — consider **continued pretraining** first (§3). The MLM dry-run in §3d shows what each domain-adaptation step does mechanically, and the fill-mask probe in §3g shows how dramatically the model shifts its conditional probabilities toward your domain. This two-step investment pays off when your target domain is genuinely out-of-distribution for general BERT.

If you are constrained on **GPU compute** but have labelled data, **partial freezing** is the practical middle ground (§1c). Freeze the lower BERT layers (which capture universal language structure) and train only the upper layers plus the classification head. You can get F1 = 0.80 — much better than the all-frozen approach — in significantly less time.

Finally, if your task requires **per-token prediction** — identifying entities within text, extracting spans, labelling each word in a sequence — you need the NER pipeline (§4) with BIO tagging, subtoken alignment via `align_labels`, and entity-level evaluation with seqeval. The architecture change (per-token head instead of pooled sequence head, §4b) and the disciplined label alignment (§4f) are what make this work. Remember: token-level accuracy is misleading on NER — always evaluate at the entity level (§4g).

### Bridge to Chapter 12

This chapter fine-tuned *encoder* models (BERT-style) for *discriminative*, non-generative tasks. Chapter 12 does the same for *decoder* models (GPT-style) — teaching them to follow instructions and align their outputs with human preferences. Where Chapter 11's classification head outputs a class label, Chapter 12's instruction-tuning output is a full generated sequence. The training framework shifts from Trainer-based classification to Supervised Fine-Tuning (SFT) and Reinforcement Learning from Human Feedback (RLHF).

The core lesson of this chapter stays constant: **fine-tuning — whether supervised, few-shot, domain-adaptive, or token-level — is always better than using a frozen model when you have the right data and the right task framing.**
