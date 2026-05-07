# Course 4 Quick Prerequisites Guide
## Everything You Need to Know to Complete Week 1-3 Assignments

---

## Overview

You don't need to read hundreds of pages. Here's the **minimum** you need to understand to complete and learn from the assignments.

---

## Week 1: Neural Machine Translation with Attention

### What You Actually Need to Know:

**1. Sequence-to-Sequence (5 minutes)**

The problem:
```
Input:  "I love NLP"  →  Model  →  Output: "Ich liebe NLP"
```

Basic idea:
- **Encoder**: Reads entire input sentence, creates a summary
- **Decoder**: Uses summary to generate output word-by-word

The **problem** with basic seq2seq:
- Long sentences → One fixed-size summary vector → Information loss
- Decoder forgets what was at the beginning

**2. Attention Mechanism (10 minutes)**

The solution:
- Don't compress everything into one vector
- Let decoder **look back** at ALL encoder outputs
- At each step, decoder decides which parts of input to focus on

**The Math (only formula you need):**

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

In simple terms:
- $Q$ (Query) = "What am I looking for?" (current decoder state)
- $K$ (Key) = "What do I have?" (all encoder states)
- $V$ (Value) = "What's the content?" (all encoder states)
- $\frac{1}{\sqrt{d_k}}$ = Scaling factor (prevents big numbers)

**Visual:**
```
Encoder states:  [h1]  [h2]  [h3]  [h4]
                   ↓     ↓     ↓     ↓
Attention:       0.1   0.6   0.2   0.1  ← Weights (sum to 1)
                   ↓
Context = 0.1*h1 + 0.6*h2 + 0.2*h3 + 0.1*h4
```

Decoder focuses most on h2 for this step.

**3. LSTM/GRU (2 minutes)**

You know GRU. LSTM is basically the same:

GRU:
- 2 gates (reset, update)
- One hidden state

LSTM:
- 3 gates (forget, input, output)  
- Two states (hidden + cell)

**For the assignment**: They're interchangeable. LSTM is just the backbone that creates those encoder states. The important part is **attention**.

**4. Teacher Forcing (2 minutes)**

During training:
```
Target: "Ich liebe NLP"

Normal: Model predicts "Ich" → Feed "Ich" to predict next word
Teacher Forcing: Model predicts "Ich" → Feed correct "Ich" to predict next word
                                         (Even if prediction was wrong)
```

Why? Faster training, prevents error accumulation during learning.

**That's it for Week 1!** The code handles everything else.

---

## Week 2: Transformer Architecture

### What You Actually Need to Know:

**1. The Big Idea (3 minutes)**

Problem with RNNs:
- Must process sequentially: word 1 → word 2 → word 3 → ...
- Slow, can't parallelize
- Still struggles with very long sequences

Transformer solution:
- Process ALL words at once (parallel)
- Use **only attention**, no RNN
- Much faster training

**2. Key Components (15 minutes total)**

**A. Positional Encoding** (3 min)

Problem: Without RNN, model has no idea about word order
```
"dog bites man" vs "man bites dog" look identical!
```

Solution: Add position information to embeddings
```
word_embedding + position_encoding = final_embedding
```

Formula (you don't need to memorize):
```
PE(pos, 2i)   = sin(pos / 10000^(2i/d))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d))
```

Just know: Uses sine/cosine waves to encode positions.

**B. Multi-Head Attention** (5 min)

Instead of one attention:
```
Single attention: Look at input from one perspective

Multi-head: Look at input from multiple perspectives simultaneously
  Head 1: Focuses on subject-verb relationships
  Head 2: Focuses on noun-adjective pairs
  Head 3: Focuses on long-range dependencies
  ...
```

Then combine all perspectives.

**C. Self-Attention** (3 min)

In encoder/decoder:
- Input attends to **itself**
- Each word looks at all other words in same sentence
- Builds rich contextual understanding

**D. Encoder-Decoder Structure** (4 min)

**Encoder** (understands input):
```
Input → Self-Attention → Feed-Forward → Output
  ↓
Repeat N times (usually 6 layers)
```

**Decoder** (generates output):
```
Previous output → Self-Attention 
                     ↓
              Cross-Attention (with encoder output)
                     ↓
              Feed-Forward → Next word
  ↓
Repeat N times (usually 6 layers)
```

**3. Masking (3 minutes)**

**Padding Mask**:
- Sentences have different lengths
- Padded with zeros
- Mask tells model to ignore padding

**Look-Ahead Mask**:
- When predicting word 3, can't look at word 4, 5, 6...
- Would be cheating (already know the answer)
- Mask prevents future words from being seen

**That's it for Week 2!**

---

## Week 3: Transfer Learning & BERT

### What You Actually Need to Know:

**1. Transfer Learning Concept (5 minutes)**

Traditional ML:
```
Collect data → Train model → Use model
(Need lots of data, lots of time)
```

Transfer Learning:
```
Someone else trains huge model on massive data
   ↓
You download their model
   ↓
You fine-tune on your small dataset
   ↓
Get great results in hours!
```

**Analogy**: 
- Training from scratch = Learning English from birth
- Transfer learning = You already know English, just learning medical terminology

**2. Pre-training (3 minutes)**

**What happens** (done by researchers, not you):
```
Take billions of words from internet
   ↓
Train model to predict masked words
   ↓
Model learns general language understanding
   ↓
Save weights
```

Example task:
```
Input:  "The cat sat on the [MASK]"
Model learns to predict: "mat"
```

**3. Fine-tuning (3 minutes)**

**What you do**:
```
Load pre-trained weights
   ↓
Add task-specific layer (QA head)
   ↓
Train on your task (SQuAD)
   ↓
Done!
```

**4. BERT Basics (5 minutes)**

**Key ideas**:
- **Bidirectional**: Looks at context from both left AND right
- **Transformer-based**: Uses transformer encoder (not decoder)
- **Pre-trained**: Already knows English

**For Question Answering**:
```
Input format: [CLS] question [SEP] context [SEP]

Model outputs:
  - Probability for each word being answer START
  - Probability for each word being answer END

Example:
Context: "Paris is the capital of France"
Question: "What is the capital of France?"

Model predicts:
  - START: "Paris" (high probability)
  - END: "Paris" (high probability)
  
Answer: "Paris"
```

**5. DistilBERT (2 minutes)**

BERT but:
- Smaller (66M vs 110M parameters)
- Faster (1.6x speedup)
- Almost as good (97% performance)

Perfect for learning and deployment.

**That's it for Week 3!**

---

## Visual Summary of All Three Weeks

```
WEEK 1: Attention to fix RNN limitations
┌─────────────────────────────────────────┐
│  Encoder (LSTM) → Hidden states         │
│       ↓            ↓       ↓       ↓    │
│  Attention weights at each decoder step │
│       ↓                                  │
│  Decoder (LSTM) → Translation           │
└─────────────────────────────────────────┘

WEEK 2: Remove RNN, use only Attention
┌─────────────────────────────────────────┐
│  Input + Positional Encoding            │
│       ↓                                  │
│  Self-Attention (parallel!)             │
│       ↓                                  │
│  Feed-Forward                            │
│       ↓                                  │
│  (Repeat N times)                        │
│       ↓                                  │
│  Cross-Attention in Decoder              │
│       ↓                                  │
│  Output                                  │
└─────────────────────────────────────────┘

WEEK 3: Use pre-trained model
┌─────────────────────────────────────────┐
│  Load DistilBERT (already trained)      │
│       ↓                                  │
│  Add QA head (start/end predictors)     │
│       ↓                                  │
│  Fine-tune on SQuAD                      │
│       ↓                                  │
│  Answer questions!                       │
└─────────────────────────────────────────┘
```

---

## Key Equations (only 3!)

**1. Attention** (Week 1 & 2):
$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

**2. Positional Encoding** (Week 2):
$$PE_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d}}\right)$$
$$PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d}}\right)$$

**3. QA Loss** (Week 3):
$$\mathcal{L} = -\log P(\text{start}) - \log P(\text{end})$$

---

## What You Don't Need to Know

**Skip these** (not needed for assignments):

- Detailed LSTM/GRU gate equations
- Advanced optimization techniques
- History of transformers
- Theoretical proofs
- Alternative attention mechanisms
- BERT pre-training details
- Tokenization algorithms (BPE, etc.)

**The code teaches you everything else!**

---

## Timeline for Learning

**Total time: ~1 hour**

| Topic | Time | What to Learn |
|-------|------|---------------|
| Week 1 Prep | 20 min | Seq2seq problem, attention concept, teacher forcing |
| Week 2 Prep | 25 min | Transformer idea, positional encoding, multi-head attention |
| Week 3 Prep | 15 min | Transfer learning, BERT basics, QA task |

Then **just start coding**. The assignments have detailed explanations in the code itself. You'll learn by doing.

---

## Learning Strategy

**Don't read everything first!**

Better approach:
1. Read this guide (you're doing it now)
2. Start Week 1 assignment
3. When confused about a concept, come back here
4. Google specific terms if needed
5. Focus on **running code** and **seeing results**
6. Understanding deepens as you implement

**The assignments are designed to teach you as you code.**

---

## Quick Reference During Coding

**When you see "attention" in code**:
→ It's computing which input parts to focus on

**When you see "positional encoding"**:
→ It's adding position information (since Transformer has no RNN)

**When you see "mask"**:
→ It's hiding padding or future words

**When you see "encoder/decoder"**:
→ Encoder understands input, Decoder generates output

**When you see "fine-tuning"**:
→ Taking pre-trained weights and adapting to specific task

**When stuck**:
1. Read the comments in the code
2. Print intermediate values
3. Check this guide
4. Google the specific term

---

## Final Pep Talk

You already know:
- Python
- TensorFlow basics
- Neural networks
- GRU (so you understand RNNs)
- Course 1-3 concepts

That's **95%** of what you need!

This guide covers the remaining **5%** of new concepts.

**Just start Week 1. You'll be fine.**

The code is heavily commented and guides you through each step. This isn't a math course - it's a practical implementation course. You learn by building.

**Ready? Go start Week 1!**
