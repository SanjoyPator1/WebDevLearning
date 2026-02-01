# In-Depth Guide: RNNs and GRUs - Theory, Mathematics, and Practice

## Table of Contents

1. [Introduction to Sequential Processing](#1-introduction-to-sequential-processing)
2. [The Problem with Traditional Neural Networks](#2-the-problem-with-traditional-neural-networks)
3. [Recurrent Neural Networks (RNNs)](#3-recurrent-neural-networks-rnns)
   - 3.1 [Architecture and Intuition](#31-architecture-and-intuition)
   - 3.2 [Mathematical Formulation](#32-mathematical-formulation)
   - 3.3 [Forward Propagation - Complete Example](#33-forward-propagation---complete-example)
   - 3.4 [Backpropagation Through Time (BPTT)](#34-backpropagation-through-time-bptt)
   - 3.5 [The Vanishing Gradient Problem](#35-the-vanishing-gradient-problem)
4. [Gated Recurrent Units (GRUs)](#4-gated-recurrent-units-grus)
   - 4.1 [Motivation and Design](#41-motivation-and-design)
   - 4.2 [Gate Mechanisms Explained](#42-gate-mechanisms-explained)
   - 4.3 [Mathematical Formulation](#43-mathematical-formulation)
   - 4.4 [Forward Propagation - Complete Numerical Example](#44-forward-propagation---complete-numerical-example)
   - 4.5 [How GRU Weights Are Learned](#45-how-gru-weights-are-learned)
   - 4.6 [Why GRUs Work Better Than Simple RNNs](#46-why-grus-work-better-than-simple-rnns)
   - 4.7 [Chapter Summary](#47-chapter-summary)
5. [Complete Implementation and Training](#5-complete-implementation-and-training)
   - 5.1 [Sentiment Analysis Example](#51-sentiment-analysis-example)
   - 5.2 [From-Scratch Implementation (NumPy)](#52-from-scratch-implementation-numpy)
   - 5.3 [Complete TensorFlow/Keras Training Example](#53-complete-tensorflowkeras-training-example)
6. [Practical Insights and Tips](#6-practical-insights-and-tips)

---

<a name="1-introduction"></a>

## 1. Introduction to Sequential Processing

### What are Sequences?

A **sequence** is an ordered collection of data where the order matters. Examples include:

- **Text**: "I love Paris" vs "Paris love I" (different meanings!)
- **Time series**: Stock prices, weather data, sensor readings
- **Speech**: Audio waveforms over time
- **DNA**: Nucleotide sequences (ATCG...)
- **Music**: Notes played in order

### Why Do We Need Special Architectures?

Consider this sentence: "The cat, which had been sleeping peacefully all morning on the warm windowsill, **was** hungry."

To predict "was" (singular verb), the model needs to remember "cat" (singular noun) from much earlier in the sentence, despite the long interrupting clause.

**Traditional neural networks can't do this effectively because:**

1. They have **fixed input size** - can't handle variable-length sequences
2. They have **no memory** - each prediction is independent
3. They don't **share parameters** across time steps - inefficient and can't generalize

---

<a name="2-the-problem"></a>

## 2. The Problem with Traditional Neural Networks

### Fixed Input Size Problem

```
Traditional Neural Network:

Input:  [word1, word2, word3]  →  [Hidden Layer]  →  Output
        (MUST be 3 words)

Problem: What if sentence has 5 words? Or 10? Or 2?
```

### No Memory Problem

```
Sentence: "I grew up in France... I speak fluent _____"

Traditional NN processes each word independently:
- "I" → some output
- "grew" → some output
- "up" → some output
...
- Doesn't remember "France" when predicting the blank!
```

### No Parameter Sharing Problem

```
Sentence 1: "The cat sat on the mat"
Sentence 2: "On the mat sat the cat"

Traditional NN:
- Learns "cat" in position 2 separately from "cat" in position 7
- Inefficient and doesn't transfer knowledge
```

**We need a network that can:**

- Handle variable-length inputs ✓
- Maintain memory of previous inputs ✓
- Share parameters across time ✓

**Enter: Recurrent Neural Networks!**

---

<a name="3-rnns"></a>

## 3. Recurrent Neural Networks (RNNs)

<a name="31-architecture"></a>

### 3.1 Architecture and Intuition

#### The Core Idea: Recurrence

An RNN has a **loop** that allows information to persist:

```
      ┌─────────────┐
      │   Hidden    │
   ┌──│   State     │◄──┐
   │  │   h_t       │   │
   │  └─────────────┘   │
   │         ▲          │
   │         │          │
   │    ┌────┴────┐     │
   │    │  RNN    │     │
   │    │  Cell   │─────┘
   │    └────┬────┘
   │         │
   └────► Input
          x_t
```

#### Unrolled View (How We Visualize It)

```
Input:     x₁        x₂        x₃        x₄
           │         │         │         │
           ▼         ▼         ▼         ▼
        ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐
h₀ ───► │ RNN │──►│ RNN │──►│ RNN │──►│ RNN │──► h₄
        └──┬──┘   └──┬──┘   └──┬──┘   └──┬──┘
           │         │         │         │
           ▼         ▼         ▼         ▼
Output:    y₁        y₂        y₃        y₄
```

**Key Insight:** The same RNN cell (with the same weights) is used at each time step!

#### Real Example: Sentiment Analysis

```
Sentence: "This movie is great!"
Words:     this  movie  is  great

Step 1: Process "this"
  h₀ = [0, 0, 0]  (initial state)
  x₁ = embedding("this")
  h₁ = tanh(W_hh·h₀ + W_xh·x₁ + b)

Step 2: Process "movie"
  h₁ = [0.2, -0.1, 0.5]  (state from step 1)
  x₂ = embedding("movie")
  h₂ = tanh(W_hh·h₁ + W_xh·x₂ + b)

Step 3: Process "is"
  h₂ = [0.3, 0.1, 0.4]
  x₃ = embedding("is")
  h₃ = tanh(W_hh·h₂ + W_xh·x₃ + b)

Step 4: Process "great"
  h₃ = [0.4, 0.2, 0.6]
  x₄ = embedding("great")
  h₄ = tanh(W_hh·h₃ + W_xh·x₄ + b)

Final: h₄ contains information about entire sentence
  Classifier: h₄ → Positive/Negative
```

<a name="32-mathematics"></a>

### 3.2 Mathematical Formulation

#### Basic RNN Equations

At each time step $t$, the RNN computes:

$$h_t = \tanh(W_{hh} \cdot h_{t-1} + W_{xh} \cdot x_t + b_h)$$

$$y_t = W_{hy} \cdot h_t + b_y$$

**Where:**

- $x_t \in \mathbb{R}^{d_{input}}$ = input at time $t$ (e.g., word embedding)
- $h_t \in \mathbb{R}^{d_{hidden}}$ = hidden state at time $t$ (the "memory")
- $y_t \in \mathbb{R}^{d_{output}}$ = output at time $t$ (e.g., class scores)
- $W_{hh} \in \mathbb{R}^{d_{hidden} \times d_{hidden}}$ = hidden-to-hidden weights (memory update)
- $W_{xh} \in \mathbb{R}^{d_{hidden} \times d_{input}}$ = input-to-hidden weights
- $W_{hy} \in \mathbb{R}^{d_{output} \times d_{hidden}}$ = hidden-to-output weights
- $b_h \in \mathbb{R}^{d_{hidden}}$ = hidden bias
- $b_y \in \mathbb{R}^{d_{output}}$ = output bias
- $\tanh$ = activation function (squashes to $[-1, 1]$)

#### Why This Formula?

Let's break it down:

1. **$W_{xh} \cdot x_t$**: Process current input
2. **$W_{hh} \cdot h_{t-1}$**: Incorporate previous memory
3. **$+ b_h$**: Add bias
4. **$\tanh(\cdot)$**: Non-linear activation (allows learning complex patterns)
5. **Result $h_t$**: New hidden state (updated memory)

<a name="33-forward-prop"></a>

### 3.3 Forward Propagation - Complete Example

Let's work through a **concrete numerical example** step by step.

#### Setup

**Task**: Process the word sequence "cat sat"

**Dimensions**:

- Input dimension: $d_{input} = 3$ (word embeddings)
- Hidden dimension: $d_{hidden} = 2$
- Output dimension: $d_{output} = 2$ (binary classification: positive/negative)

**Word Embeddings** (simplified):

```python
embeddings = {
    "cat": [1.0, 0.5, 0.2],
    "sat": [0.3, 0.8, 0.1]
}
```

**Weights** (initialized randomly):

```python
W_xh = [[0.1,  0.3],
        [0.2, -0.1],
        [0.4,  0.2]]  # Shape: (3, 2)

W_hh = [[0.5,  0.1],
        [0.2,  0.3]]  # Shape: (2, 2)

W_hy = [[0.6, -0.2],
        [0.3,  0.4]]  # Shape: (2, 2)

b_h = [0.1, 0.1]     # Shape: (2,)
b_y = [0.0, 0.0]     # Shape: (2,)
```

#### Step 0: Initialize

```
h₀ = [0.0, 0.0]  (initial hidden state is zeros)
```

#### Step 1: Process "cat"

**Input**: $x_1 = [1.0, 0.5, 0.2]$

**Compute hidden state**:

$$h_1 = \tanh(W_{hh} \cdot h_0 + W_{xh} \cdot x_1 + b_h)$$

Step-by-step calculation:

1. **$W_{xh} \cdot x_1$**:

   ```
   [[0.1,  0.3],     [1.0]   [0.1×1.0 + 0.3×0.5 + 0.2×0.2]   [0.39]
    [0.2, -0.1],  ×  [0.5] = [0.2×1.0 - 0.1×0.5 + 0.4×0.2] = [0.23]
    [0.4,  0.2]]      [0.2]
   ```

2. **$W_{hh} \cdot h_0$**:

   ```
   [[0.5,  0.1],     [0.0]   [0.5×0.0 + 0.1×0.0]   [0.0]
    [0.2,  0.3]]  ×  [0.0] = [0.2×0.0 + 0.3×0.0] = [0.0]
   ```

3. **Add bias and sum**:

   ```
   [0.39] + [0.0] + [0.1] = [0.49]
   [0.23]   [0.0]   [0.1]   [0.33]
   ```

4. **Apply tanh**:
   ```
   h₁ = tanh([0.49, 0.33])
      = [tanh(0.49), tanh(0.33)]
      = [0.454, 0.318]
   ```

**Compute output**:

$$y_1 = W_{hy} \cdot h_1 + b_y$$

```
[[0.6, -0.2],     [0.454]   [0.6×0.454 - 0.2×0.318 + 0.0]   [0.209]
 [0.3,  0.4]]  ×  [0.318] = [0.3×0.454 + 0.4×0.318 + 0.0] = [0.263]
```

**Result**:

- $h_1 = [0.454, 0.318]$ (hidden state carries "cat" information)
- $y_1 = [0.209, 0.263]$ (output scores)

#### Step 2: Process "sat"

**Input**: $x_2 = [0.3, 0.8, 0.1]$

**Previous hidden state**: $h_1 = [0.454, 0.318]$

**Compute hidden state**:

1. **$W_{xh} \cdot x_2$**:

   ```
   [[0.1,  0.3],     [0.3]   [0.1×0.3 + 0.3×0.8 + 0.2×0.1]   [0.29]
    [0.2, -0.1],  ×  [0.8] = [0.2×0.3 - 0.1×0.8 + 0.4×0.1] = [0.02]
    [0.4,  0.2]]      [0.1]
   ```

2. **$W_{hh} \cdot h_1$**:

   ```
   [[0.5,  0.1],     [0.454]   [0.5×0.454 + 0.1×0.318]   [0.259]
    [0.2,  0.3]]  ×  [0.318] = [0.2×0.454 + 0.3×0.318] = [0.186]
   ```

3. **Add and apply tanh**:

   ```
   pre_activation = [0.29, 0.02] + [0.259, 0.186] + [0.1, 0.1]
                  = [0.649, 0.306]

   h₂ = tanh([0.649, 0.306])
      = [0.571, 0.297]
   ```

**Compute output**:

```
y₂ = W_hy · h₂ + b_y
   = [[0.6, -0.2], [0.3, 0.4]] × [0.571, 0.297]
   = [0.283, 0.290]
```

**Result**:

- $h_2 = [0.571, 0.297]$ (now contains info about "cat sat")
- $y_2 = [0.283, 0.290]$ (final output)

#### Summary of Forward Pass

```
Time step 0: h₀ = [0.000, 0.000]
Time step 1: x₁ = [1.0, 0.5, 0.2] (cat)
             h₁ = [0.454, 0.318]
             y₁ = [0.209, 0.263]

Time step 2: x₂ = [0.3, 0.8, 0.1] (sat)
             h₂ = [0.571, 0.297]
             y₂ = [0.283, 0.290]  ← Final prediction
```

**Interpretation**:

- The hidden state $h_2$ encodes information from both "cat" and "sat"
- The output $y_2$ can be fed to a softmax for classification

<a name="34-bptt"></a>

### 3.4 Backpropagation Through Time (BPTT)

#### The Challenge

In regular backpropagation, we compute gradients by chain rule going backward through layers.

In RNNs, we have **time steps**, so we need to backpropagate through time:

```
Forward:  x₁ → h₁ → y₁
              ↓
          x₂ → h₂ → y₂
              ↓
          x₃ → h₃ → y₃

Backward: ∂L/∂y₃ → ∂L/∂h₃ → ∂L/∂h₂ → ∂L/∂h₁
                      ↓         ↓         ↓
                   ∂L/∂y₂   ∂L/∂y₁   ∂L/∂x₁
```

#### BPTT Equations

**Loss at time $t$**:
$$\mathcal{L}_t = \text{CrossEntropy}(y_t, \text{true\_label}_t)$$

**Total loss**:
$$\mathcal{L} = \sum_{t=1}^{T} \mathcal{L}_t$$

**Gradient with respect to output**:
$$\frac{\partial \mathcal{L}}{\partial y_t} = y_t - \text{true\_label}_t \quad \text{(for softmax + cross-entropy)}$$

**Gradient with respect to $h_t$** (this is where time dependencies matter):

$$\frac{\partial \mathcal{L}}{\partial h_t} = \frac{\partial \mathcal{L}_t}{\partial y_t} \cdot \frac{\partial y_t}{\partial h_t} + \frac{\partial \mathcal{L}}{\partial h_{t+1}} \cdot \frac{\partial h_{t+1}}{\partial h_t}$$

The second term is the **gradient flowing back from future time steps**!

**Gradient with respect to $W_{hh}$**:

$$\frac{\partial \mathcal{L}}{\partial W_{hh}} = \sum_{t=1}^{T} \frac{\partial \mathcal{L}}{\partial h_t} \cdot \frac{\partial h_t}{\partial W_{hh}}$$

#### Numerical Example (Simplified)

Let's compute gradients for our "cat sat" example.

**Given**:

- True label: $y_{true} = [1, 0]$ (class 0)
- Predicted: $y_2 = [0.283, 0.290]$ after softmax → $[0.497, 0.503]$

**Step 1: Gradient at output**

```
∂L/∂y₂ = [0.497, 0.503] - [1, 0]
       = [-0.503, 0.503]
```

**Step 2: Gradient at $h_2$**

```
∂L/∂h₂ = (∂L/∂y₂) · W_hy^T
       = [-0.503, 0.503] · [[0.6, 0.3], [-0.2, 0.4]]
       = [-0.403, 0.050]
```

**Step 3: Gradient at $h_1$** (includes gradient from $h_2$)

```
∂h₂/∂h₁ = (1 - h₂²) ⊙ W_hh^T  (where ⊙ is element-wise multiplication)

∂L/∂h₁ = ∂L/∂h₂ · ∂h₂/∂h₁
       = [-0.403, 0.050] · [(1-0.571²) ⊙ [[0.5, 0.2], [0.1, 0.3]]]
       = [calculation continues...]
```

**Step 4: Gradient at weights**

```
∂L/∂W_hh = Σ (∂L/∂h_t) · h_{t-1}^T

         = (∂L/∂h₁) · h₀^T + (∂L/∂h₂) · h₁^T
         = (∂L/∂h₁) · [0, 0]^T + [-0.403, 0.050] · [0.454, 0.318]^T
         = [[-0.183, -0.128],
            [ 0.023,  0.016]]
```

<a name="35-vanishing-gradient"></a>

### 3.5 The Vanishing Gradient Problem

#### What Is It?

When backpropagating through many time steps, gradients can become **exponentially small**.

**Why It Happens**:

The gradient at time step $t$ depends on products of Jacobians:

$$\frac{\partial h_t}{\partial h_{t-k}} = \prod_{i=t-k}^{t-1} \frac{\partial h_{i+1}}{\partial h_i}$$

Each term in the product is:

$$\frac{\partial h_{i+1}}{\partial h_i} = \text{diag}(\tanh'(z_i)) \cdot W_{hh}$$

Where $\tanh'(z) = 1 - \tanh^2(z) \in (0, 1]$

**The Problem**:

- $\tanh'$ is always ≤ 1
- If $W_{hh}$ has eigenvalues < 1, each multiplication makes gradient smaller
- After many steps: $(0.5)^{20} \approx 10^{-6}$ (essentially zero!)

#### Concrete Example

```
Sentence: "I grew up in France ... (50 words) ... I speak fluent French"

RNN tries to learn:
- Time step 1: "France" → important for prediction
- Time step 52: Predict "French" based on "France"

Gradient flow:
∂L/∂h₅₂ → ∂L/∂h₅₁ → ... → ∂L/∂h₁

At each step, multiply by:
- tanh'(z) ≈ 0.4 (typical value)
- W_hh (may have values < 1)

After 51 steps:
Gradient ≈ (0.4)^51 ≈ 10^-20 (vanished!)

Result: RNN can't learn long-term dependencies
```

#### Why This Is Bad

**Example Failure**:

```
Input:  "The cat, which had been sleeping peacefully all morning, was hungry"
Target: Predict "was" (singular, to agree with "cat")

RNN might learn:
✗ "sleeping" → "was" (short-term, recent context)
✗ But not "cat" → "was" (long-term dependency needed)

Prediction: "were" (plural, wrong!)
```

**This is where GRUs come in to save the day!**

---

<a name="4-grus"></a>

## 4. Gated Recurrent Units (GRUs)

<a name="41-motivation"></a>

### 4.1 Motivation and Design

#### The Core Problem GRUs Solve

Simple RNNs suffer from:

1. **Vanishing gradients** → can't learn long-term dependencies
2. **Information overwriting** → new input always modifies hidden state

#### The GRU Solution: Gates

**Key Insight**: Not all information is equally important!

**Gates** are mechanisms that learn to:

- **Keep** important information from the past
- **Forget** irrelevant information
- **Update** selectively based on current input

Think of gates as **smart filters** with values in $[0, 1]$:

- Gate value = 0 → Block completely
- Gate value = 1 → Allow completely
- Gate value = 0.7 → Allow 70%

<a name="42-gates"></a>

### 4.2 Gate Mechanisms Explained

#### GRU Mathematical Formulation

#### The Four Key Equations

##### 1. Update Gate

$$\Gamma_u = \sigma(W_u \cdot [h^{(t-1)}, x^{(t)}] + b_u)$$

##### 2. Relevance Gate (Reset Gate)

$$\Gamma_r = \sigma(W_r \cdot [h^{(t-1)}, x^{(t)}] + b_r)$$

##### 3. Candidate Hidden State

$$\tilde{h}^{(t)} = \tanh(W_h \cdot [\Gamma_r \odot h^{(t-1)}, x^{(t)}] + b_h)$$

##### 4. Final Hidden State

$$h^{(t)} = (1 - \Gamma_u) \odot h^{(t-1)} + \Gamma_u \odot \tilde{h}^{(t)}$$

#### What's Actually Stored: The Reality

**Critical Understanding**: Hidden states store **NUMBERS, not text!**

When you see $h^{(t)} = [0.131, 0.079]$, these are literally just **floating point numbers** - not words, letters, or symbols.

**What do these numbers represent?**

Think of them as **abstract learned features**:

- First dimension (0.131) might encode "subject information"
- Second dimension (0.079) might encode "sentiment" or "verb tense"

**Key insight**: The network **learns what each dimension means during training**! We don't manually assign meanings like "dimension 1 = subject". The GRU figures out what patterns to capture based on the task.

**Example**:

```
After processing "The cat":
h = [0.8, 0.3]

0.8 → Strong signal for "there's a cat (subject)"
0.3 → Slight positive/neutral sentiment

These are learned representations, not stored words!
```

#### Understanding Gate Behavior

GRUs have **two gates**:

#### 1. Update Gate ($\Gamma_u$)

**Purpose**: Control how much to **UPDATE** the hidden state with new information

$$\Gamma_u = \sigma(W_u \cdot [h^{(t-1)}, x^{(t)}] + b_u)$$

**How it works**:

```
If Γ_u ≈ 1: UPDATE a lot (take ~100% NEW candidate, ~0% old)
If Γ_u ≈ 0: DON'T UPDATE (keep ~100% OLD, ~0% new candidate)
```

**The formula breakdown**:
$$h^{(t)} = (1 - \Gamma_u) \odot h^{(t-1)} + \Gamma_u \odot \tilde{h}^{(t)}$$

```
When Γ_u = 1.0:
  h^{(t)} = (1-1) × old + 1 × new = 0 × old + 1 × new = new
  → Take 100% NEW (full update)

When Γ_u = 0.0:
  h^{(t)} = (1-0) × old + 0 × new = 1 × old + 0 × new = old
  → Keep 100% OLD (no update)

When Γ_u = 0.8:
  h^{(t)} = 0.2 × old + 0.8 × new
  → Take 80% new, keep 20% old (heavy update)

When Γ_u = 0.2:
  h^{(t)} = 0.8 × old + 0.2 × new
  → Keep 80% old, take 20% new (light update)
```

**Example**:

```
Sentence: "The cat, which had been sleeping all morning, was hungry"

At "which": Γ_u ≈ [0.05, 0.05] (light update - keep 95% old "cat" info!)
At "sleeping": Γ_u ≈ [0.70, 0.70] (heavy update - take 70% new descriptor)
At "was": Γ_u ≈ [0.10, 0.10] (light update - keep 90% old for agreement!)
```

**Concrete numerical example**:

```python
Previous hidden: h_{t-1} = [0.8, 0.3]  # Encodes "cat" info
New candidate: h̃_t = [0.7, 0.5]       # Info from current word
Update gate: Γ_u = [0.05, 0.05]       # Light update (keep most old)

Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}

h_t = (1 - [0.05, 0.05]) ⊙ [0.8, 0.3] + [0.05, 0.05] ⊙ [0.7, 0.5]
    = [0.95, 0.95] ⊙ [0.8, 0.3] + [0.05, 0.05] ⊙ [0.7, 0.5]
    = [0.95×0.8, 0.95×0.3] + [0.05×0.7, 0.05×0.5]
    = [0.76, 0.285] + [0.035, 0.025]
    = [0.795, 0.31]

Result: Kept most of the "cat" information (0.8 → 0.795)
```

#### 2. Reset Gate ($\Gamma_r$)

**Purpose**: Decide how much of the **previous hidden state** to use when computing the new candidate

$$\Gamma_r = \sigma(W_r \cdot [h^{(t-1)}, x^{(t)}] + b_r)$$

**How it works**:

```
If Γ_r ≈ 1: Use all of h_{t-1} in computing candidate
If Γ_r ≈ 0: Ignore h_{t-1}, start fresh
```

Great question! Let me explain the reset gate step by step, just like I did for the update gate.

**Reset Gate ($\Gamma_r$) - Deep Dive**

**What Does Reset Gate Control?**

The reset gate controls **how much of the previous hidden state to USE when computing the candidate**.

**The Formula Connection**

Look at where $\Gamma_r$ appears:

$$\tilde{h}^{(t)} = \tanh(W_h \cdot [\Gamma_r \odot h^{(t-1)}, x^{(t)}] + b_h)$$

Notice: $\Gamma_r$ **multiplies** the previous hidden state BEFORE it goes into computing the candidate!

**When Γ_r → 1 (High Reset Gate)**

```python
Γ_r = [0.95, 0.95]  # Very high
h_{t-1} = [0.8, 0.3]

# Step 1: Apply reset gate
reset_hidden = Γ_r ⊙ h_{t-1}
             = [0.95, 0.95] ⊙ [0.8, 0.3]
             = [0.76, 0.285]  # Almost all of previous hidden state!

# Step 2: Compute candidate WITH this context
h̃_t = tanh(W_h · [[0.76, 0.285], x_t] + b_h)
     = [some value that considers the previous context strongly]
```

**Effect**: The candidate is computed WITH full knowledge of what came before.

**When to use**: When the current word NEEDS context from previous words.

**Example**: 
```
Sentence: "The cat was"
At "was": Γ_r = 0.95

Why? Because to process "was" correctly, you NEED to know about "cat"!
The candidate needs to incorporate subject information.
```

**When Γ_r → 0 (Low Reset Gate)**

```python
Γ_r = [0.05, 0.05]  # Very low
h_{t-1} = [0.8, 0.3]

# Step 1: Apply reset gate
reset_hidden = Γ_r ⊙ h_{t-1}
             = [0.05, 0.05] ⊙ [0.8, 0.3]
             = [0.04, 0.015]  # Almost ZERO! Previous hidden state blocked!

# Step 2: Compute candidate WITHOUT context
h̃_t = tanh(W_h · [[0.04, 0.015], x_t] + b_h)
     ≈ tanh(W_h · [x_t] + b_h)  # Candidate computed almost as if h_{t-1} doesn't exist!
```

**Effect**: The candidate is computed almost INDEPENDENTLY, as if starting fresh.

**When to use**: When the previous context is IRRELEVANT or MISLEADING for the current word.

**Example**: 
```
Sentence: "I love Paris. I hate Rome."
At "hate": Γ_r = 0.12

Why? Because "love" from the previous sentence should NOT influence 
how we compute the candidate for "hate"! We want a fresh, clean 
negative sentiment, not contaminated by previous positive sentiment.
```

**Complete Flow: Reset → Candidate → Final Hidden State**

Let me trace through two scenarios to show the complete impact:

#### Scenario 1: HIGH Reset Gate (Need Context)

**Context**: "The cat was"

```python
# At word "was"
Previous: h_{t-1} = [0.62, 0.58]  # Has "cat" subject info
Word: x_t = [0.1, 0.7, 0.2]       # "was" embedding

# STEP 1: Reset gate (HIGH!)
Γ_r = σ(W_r · [h_{t-1}, x_t] + b_r) = [0.95, 0.92]

# STEP 2: Apply reset to previous hidden
reset_h = [0.95, 0.92] ⊙ [0.62, 0.58]
        = [0.59, 0.53]  # Keeps almost ALL previous info

# STEP 3: Compute candidate WITH context
h̃_t = tanh(W_h · [[0.59, 0.53], [0.1, 0.7, 0.2]] + b_h)
     = [0.68, 0.62]
     
# This candidate [0.68, 0.62] contains:
# - Information about "was" (the verb)
# - Information about "cat" (the subject, carried through reset_h)
# - Properly combined for subject-verb processing

# STEP 4: Update gate (LOW! Keep old)
Γ_u = [0.10, 0.12]

# STEP 5: Final hidden state
h_t = (1 - Γ_u) ⊙ h_{t-1} + Γ_u ⊙ h̃_t
    = [0.90, 0.88] ⊙ [0.62, 0.58] + [0.10, 0.12] ⊙ [0.68, 0.62]
    = [0.56, 0.51] + [0.07, 0.07]
    = [0.63, 0.58]

# Result: "cat" preserved (0.62 → 0.63), verb info added
```

**Why this works**:
1. High Γ_r → candidate computed with context → h̃_t has both verb and subject
2. Low Γ_u → keep most old → final h_t preserves "cat" for agreement

#### Scenario 2: LOW Reset Gate (Don't Need Context)

**Context**: "I love Paris. I hate Rome."

```python
# At word "hate"
Previous: h_{t-1} = [0.18, 0.22]  # Residual from previous sentence
Word: x_t = [0.1, 0.8, 0.3]       # "hate" embedding

# STEP 1: Reset gate (LOW!)
Γ_r = σ(W_r · [h_{t-1}, x_t] + b_r) = [0.12, 0.08]

# STEP 2: Apply reset to previous hidden
reset_h = [0.12, 0.08] ⊙ [0.18, 0.22]
        = [0.022, 0.018]  # Almost ZERO! Blocks previous info

# STEP 3: Compute candidate WITHOUT context
h̃_t = tanh(W_h · [[0.022, 0.018], [0.1, 0.8, 0.3]] + b_h)
     = tanh(W_h · [0.022, 0.018, 0.1, 0.8, 0.3] + b_h)
     ≈ tanh(W_h · [0.1, 0.8, 0.3] + b_h)  # Mostly just "hate" embedding
     = [-0.65, 0.15]
     
# This candidate [-0.65, 0.15] contains:
# - Strong negative sentiment from "hate"
# - CLEAN, not contaminated by "love" from previous sentence
# - Because reset_h was nearly zero!

# STEP 4: Update gate (HIGH! Take new)
Γ_u = [0.75, 0.80]

# STEP 5: Final hidden state
h_t = (1 - Γ_u) ⊙ h_{t-1} + Γ_u ⊙ h̃_t
    = [0.25, 0.20] ⊙ [0.18, 0.22] + [0.75, 0.80] ⊙ [-0.65, 0.15]
    = [0.045, 0.044] + [-0.488, 0.120]
    = [-0.443, 0.164]

# Result: Strong negative sentiment (first dimension is -0.443)
```

**Why this works**:
1. Low Γ_r → candidate computed fresh → h̃_t has clean "hate", no "love" contamination
2. High Γ_u → take most new → final h_t strongly reflects the clean negative sentiment

#### Visual Summary: Reset Gate Impact

```
HIGH RESET GATE (Γ_r ≈ 1):
Previous h_{t-1} = [0.8, 0.3] ──(95% used)──> [0.76, 0.29] ─┐
                                                            │
Current x_t = [0.2, 0.9, 0.1] ────────────────────────────> │
                                                            ↓
                                                    Candidate computed
                                                    WITH context:
                                                    h̃_t = [0.68, 0.62]

Use case: "The cat was" - need subject for verb!


LOW RESET GATE (Γ_r ≈ 0):
Previous h_{t-1} = [0.8, 0.3] ──(5% used)──> [0.04, 0.015] ≈ 0 ─┐
                                                                │
Current x_t = [0.1, 0.8, 0.3] ────────────────────────────────> │
                                                                ↓
                                                        Candidate computed
                                                        WITHOUT context:
                                                        h̃_t = [-0.65, 0.15]

Use case: "love Paris. hate Rome" - don't want "love" contaminating "hate"!
```

#### The Key Insight

**Reset gate works BEFORE candidate computation**:
- It's like a **"context filter"** 
- Decides: "Should I look at the past when thinking about this new word?"

**Update gate works AFTER candidate computation**:
- It's like a **"blend control"**
- Decides: "How much of this new idea should I adopt?"

**Together they enable**:
1. **Context-aware updates**: High Γ_r + Low Γ_u = "Use context to compute candidate, but keep old" (e.g., "was" after "cat")
2. **Fresh starts**: Low Γ_r + High Γ_u = "Compute fresh, adopt new" (e.g., "hate" after "love")
3. **Gradual blending**: Medium Γ_r + Medium Γ_u = Mix old and new with context

**Complete Example**: "I love Paris. I hate Rome."

Let's see what actually happens at each word:

**At "love"**:

```python
Previous: h_{t-1} = [0.1, 0.1]    # Just started, minimal info
Word: x_t = [0.8, 0.2, 0.6]       # Embedding for "love"

Γ_r = σ(W_r · [h_{t-1}, x_t] + b_r)
    = [0.5, 0.6]  # Moderate - some context but mostly new

h̃_t = tanh(W_h · [Γ_r ⊙ h_{t-1}, x_t] + b_h)
     = tanh(W_h · [[0.05, 0.06], [0.8, 0.2, 0.6]] + b_h)
     = [0.7, 0.3]  # Encodes "love" sentiment

Γ_u = σ(W_u · [h_{t-1}, x_t] + b_u)
    = [0.6, 0.5]  # Moderate - update 60%, keep 40%

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.6, 0.5]) ⊙ [0.1, 0.1] + [0.6, 0.5] ⊙ [0.7, 0.3]
    = [0.4, 0.5] ⊙ [0.1, 0.1] + [0.6, 0.5] ⊙ [0.7, 0.3]
    = [0.04, 0.05] + [0.42, 0.15]
    = [0.46, 0.20]  # Now stores "love" sentiment
```

**At "Paris"**:

```python
Previous: h_{t-1} = [0.46, 0.20]  # Has "love" sentiment
Word: x_t = [0.3, 0.9, 0.4]       # Embedding for "Paris"

Γ_r = [0.85, 0.80]  # High! Need "love" context for "Paris"
Γ_u = [0.25, 0.30]  # Low! Light update, keep most sentiment

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.25, 0.30]) ⊙ [0.46, 0.20] + [0.25, 0.30] ⊙ [candidate]
    = [0.75, 0.70] ⊙ [0.46, 0.20] + [0.25, 0.30] ⊙ [candidate]
    = [0.68, 0.42]  # Encodes "love Paris" (kept sentiment)
```

**At period "."**:

```python
Previous: h_{t-1} = [0.68, 0.42]  # Has "love Paris"
Word: x_t = [0.0, 0.1, 0.0]       # Embedding for "."

Γ_r = [0.3, 0.2]   # LOW! Sentence ending, prepare to reset
Γ_u = [0.8, 0.9]   # HIGH! Ready for new sentence, update heavily

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.8, 0.9]) ⊙ [0.68, 0.42] + [0.8, 0.9] ⊙ [candidate]
    = [0.2, 0.1] ⊙ [0.68, 0.42] + [0.8, 0.9] ⊙ [candidate]
    = [0.25, 0.15]  # Partially cleared, ready for new context
```

**At "I" (second sentence)**:

```python
Previous: h_{t-1} = [0.25, 0.15]  # Residual from previous sentence
Word: x_t = [1.0, 0.0, 0.0]       # Embedding for "I"

Γ_r = [0.4, 0.3]   # Moderate
Γ_u = [0.7, 0.6]   # High - starting fresh, update heavily

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.7, 0.6]) ⊙ [0.25, 0.15] + [0.7, 0.6] ⊙ [candidate]
    = [0.18, 0.22]  # New sentence context
```

**At "hate" (THE KEY MOMENT)**:

```python
Previous: h_{t-1} = [0.18, 0.22]  # Current sentence, no strong sentiment yet
Word: x_t = [0.1, 0.8, 0.3]       # Embedding for "hate"

# Here's where reset gate is CRITICAL:
Γ_r = σ(W_r · [[0.18, 0.22], [0.1, 0.8, 0.3]] + b_r)
    = [0.12, 0.08]  # VERY LOW!

# This is saying: "Forget most of the previous context!
# The word 'hate' needs to be processed almost independently"

# Compute candidate with RESET context:
reset_hidden = [0.12, 0.08] ⊙ [0.18, 0.22]
             = [0.022, 0.018]  # Almost zero!

h̃_t = tanh(W_h · [[0.022, 0.018], [0.1, 0.8, 0.3]] + b_h)
     = tanh(W_h · [0.022, 0.018, 0.1, 0.8, 0.3] + b_h)
     = [-0.65, 0.15]  # Strong NEGATIVE sentiment from "hate"

# Notice: The negative sentiment is CLEAN, not contaminated by
# any residual "love" information from the first sentence!

# Update gate
Γ_u = σ(W_u · [[0.18, 0.22], [0.1, 0.8, 0.3]] + b_u)
    = [0.75, 0.80]  # High! This sentiment is important, update heavily

# Final hidden state
# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.75, 0.80]) ⊙ [0.18, 0.22] + [0.75, 0.80] ⊙ [-0.65, 0.15]
    = [0.25, 0.20] ⊙ [0.18, 0.22] + [0.75, 0.80] ⊙ [-0.65, 0.15]
    = [0.045, 0.044] + [-0.488, 0.120]
    = [-0.443, 0.164]  # Strong negative in first dimension shows "hate"
```

**What if we DIDN'T have reset gate?** (Like simple RNN):

```python
# Without reset, candidate would be:
h̃_t = tanh(W_h · [[0.18, 0.22], [0.1, 0.8, 0.3]] + b_h)
     # Uses FULL previous hidden state [0.18, 0.22]
     # which still has some residual positive sentiment
     = [-0.42, 0.31]  # LESS negative, contaminated!

# With high Γ_u = [0.75, 0.80]:
# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.75, 0.80]) ⊙ [0.18, 0.22] + [0.75, 0.80] ⊙ [-0.42, 0.31]
    = [0.25, 0.20] ⊙ [0.18, 0.22] + [0.75, 0.80] ⊙ [-0.42, 0.31]
    = [0.045, 0.044] + [-0.315, 0.248]
    = [-0.270, 0.292]  # Still negative, but WEAKER and contaminated

# Result: Model might incorrectly think sentiment is mixed/neutral
# instead of clearly negative
```

**At "Rome"**:

```python
Previous: h_{t-1} = [-0.443, 0.164]  # Has strong "hate" sentiment
Word: x_t = [0.4, 0.7, 0.5]          # Embedding for "Rome"

Γ_r = σ(W_r · [h_{t-1}, x_t] + b_r)
    = [0.25, 0.20]  # LOW! Don't let "hate" heavily influence "Rome" itself
                     # (Rome is just the object, not inherently negative)

reset_hidden = [0.25, 0.20] ⊙ [-0.443, 0.164]
             = [-0.111, 0.033]  # Minimal influence

h̃_t = tanh(W_h · [[-0.111, 0.033], [0.4, 0.7, 0.5]] + b_h)
     = [0.35, 0.58]  # "Rome" processed fairly neutrally

Γ_u = σ(W_u · [h_{t-1}, x_t] + b_u)
    = [0.30, 0.25]  # Low-moderate - light update, keep 70-75% of "hate"

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.30, 0.25]) ⊙ [-0.443, 0.164] + [0.30, 0.25] ⊙ [0.35, 0.58]
    = [0.70, 0.75] ⊙ [-0.443, 0.164] + [0.30, 0.25] ⊙ [0.35, 0.58]
    = [-0.310, 0.123] + [0.105, 0.145]
    = [-0.205, 0.268]  # Final: "hate Rome" encoded (still negative first dim)
```

**Summary of what reset gate accomplished**:

```
Without reset gate:
"love Paris" → "hate Rome"
  └─contamination→ Mixed/confused sentiment encoding

With reset gate:
"love Paris" ─(reset!)─> "hate Rome"
  └─clean separation─> Clear negative sentiment for second part
```

The reset gate learned (during training) that:

- After punctuation + "I" → prepare to reset
- At strong opposite sentiment words ("hate" after "love") → RESET!
- This prevents sentiment contamination across sentences

#### How Gates Work Together

**The Three-Step Process**:

```
1. Reset gate: Selectively use past when computing new candidate
             ↓
2. Candidate: What new information to consider
             ↓
3. Update gate: How much to UPDATE with new vs keep old
```

**Complete Walkthrough**: "The cat, which had been sleeping all day, was hungry"

Let's trace through with actual numbers to see how gates coordinate:

**At "The cat"** (initial processing):

```python
After processing both words:
h = [0.80, 0.30]

Interpretation:
  0.80 → Strong signal: "singular subject (cat) is present"
  0.30 → Neutral sentiment/description level
```

**At "which"**:

```python
Previous: h_{t-1} = [0.80, 0.30]
Input: x_t = [0.2, 0.9, 0.1]  # "which" embedding

# Step 1: Reset gate
Γ_r = σ(W_r · [[0.80, 0.30], [0.2, 0.9, 0.1]] + b_r)
    = [0.82, 0.78]  # HIGH! Need "cat" context

# Step 2: Compute candidate WITH 82% of previous context
reset_h = [0.82, 0.78] ⊙ [0.80, 0.30]
        = [0.66, 0.23]

h̃_t = tanh(W_h · [[0.66, 0.23], [0.2, 0.9, 0.1]] + b_h)
     = [0.55, 0.40]  # Candidate says: "relative clause, context aware"

# Step 3: Update gate
Γ_u = σ(W_u · [[0.80, 0.30], [0.2, 0.9, 0.1]] + b_u)
    = [0.05, 0.07]  # VERY LOW! Light update - keep 93-95% old

# Step 4: Final hidden state
# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.05, 0.07]) ⊙ [0.80, 0.30] + [0.05, 0.07] ⊙ [0.55, 0.40]
    = [0.95, 0.93] ⊙ [0.80, 0.30] + [0.05, 0.07] ⊙ [0.55, 0.40]
    = [0.76, 0.28] + [0.03, 0.03]
    = [0.79, 0.31]

Result: "cat" information PRESERVED (0.80 → 0.79, almost unchanged!)
```

**At "had"**:

```python
Previous: h_{t-1} = [0.79, 0.31]
Input: x_t = [0.3, 0.6, 0.2]

Γ_r = σ(W_r · [h_{t-1}, x_t] + b_r) = [0.88, 0.85]  # High - still need context
Γ_u = σ(W_u · [h_{t-1}, x_t] + b_u) = [0.15, 0.20]  # Low - light update

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.15, 0.20]) ⊙ [0.79, 0.31] + [0.15, 0.20] ⊙ [candidate]
    = [0.85, 0.80] ⊙ [0.79, 0.31] + [0.15, 0.20] ⊙ [candidate]
    = [0.70, 0.35]  # Added some "had" (past tense marker)
                    # Still maintaining "cat" (0.70 ≈ 0.79)
```

**At "been"**:

```python
Previous: h_{t-1} = [0.70, 0.35]
Input: x_t = [0.4, 0.5, 0.3]

Γ_r = [0.90, 0.87]  # High
Γ_u = [0.12, 0.15]  # Low - light update

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.12, 0.15]) ⊙ [0.70, 0.35] + [0.12, 0.15] ⊙ [candidate]
    = [0.88, 0.85] ⊙ [0.70, 0.35] + [0.12, 0.15] ⊙ [candidate]
    = [0.68, 0.38]  # Progressive marker added
                    # "cat" still there (0.68)
```

**At "sleeping"**:

```python
Previous: h_{t-1} = [0.68, 0.38]
Input: x_t = [0.5, 0.3, 0.8]

Γ_r = σ(W_r · [h_{t-1}, x_t] + b_r) = [0.85, 0.82]  # Still need context
Γ_u = σ(W_u · [h_{t-1}, x_t] + b_u) = [0.70, 0.65]  # HIGH! Important descriptor

# This is saying: "Sleeping is the descriptor, it's important!
# Update heavily - take 70% new information"

reset_h = [0.85, 0.82] ⊙ [0.68, 0.38]
        = [0.58, 0.31]

h̃_t = tanh(W_h · [[0.58, 0.31], [0.5, 0.3, 0.8]] + b_h)
     = [0.62, 0.71]  # Candidate with "sleeping" info

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.70, 0.65]) ⊙ [0.68, 0.38] + [0.70, 0.65] ⊙ [0.62, 0.71]
    = [0.30, 0.35] ⊙ [0.68, 0.38] + [0.70, 0.65] ⊙ [0.62, 0.71]
    = [0.20, 0.13] + [0.43, 0.46]
    = [0.63, 0.59]

Result: "cat" decreased (0.68 → 0.63) but STILL PRESENT
        "sleeping" descriptor added (0.38 → 0.59)
```

**At "all"**:

```python
Previous: h_{t-1} = [0.63, 0.59]
Input: x_t = [0.2, 0.4, 0.1]

Γ_r = [0.80, 0.78]
Γ_u = [0.50, 0.45]  # Moderate - intensifier, update moderately

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.50, 0.45]) ⊙ [0.63, 0.59] + [0.50, 0.45] ⊙ [candidate]
    = [0.58, 0.61]  # "all" intensifies the description
```

**At "day"**:

```python
Previous: h_{t-1} = [0.58, 0.61]
Input: x_t = [0.6, 0.2, 0.4]

Γ_r = [0.85, 0.80]
Γ_u = [0.25, 0.30]  # Low - light update, "all day" is complete phrase

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.25, 0.30]) ⊙ [0.58, 0.61] + [0.25, 0.30] ⊙ [candidate]
    = [0.62, 0.58]  # "all day" time context added
```

**At "was"** (THE CRITICAL MOMENT):

```python
Previous: h_{t-1} = [0.62, 0.58]  # Has "cat" + "sleeping all day"
Input: x_t = [0.1, 0.7, 0.2]      # "was" embedding

# This is where it all pays off!

# Step 1: Reset gate - VERY HIGH
Γ_r = σ(W_r · [[0.62, 0.58], [0.1, 0.7, 0.2]] + b_r)
    = [0.95, 0.92]
# "Need ALL the context to process this verb correctly!"

# Step 2: Compute candidate with FULL context
reset_h = [0.95, 0.92] ⊙ [0.62, 0.58]
        = [0.59, 0.53]  # Almost complete previous info

h̃_t = tanh(W_h · [[0.59, 0.53], [0.1, 0.7, 0.2]] + b_h)
     = [0.68, 0.62]
# Candidate incorporates verb WITH subject memory

# Step 3: Update gate - VERY LOW
Γ_u = σ(W_u · [[0.62, 0.58], [0.1, 0.7, 0.2]] + b_u)
    = [0.10, 0.12]
# "Light update - keep 90% of accumulated info - verb needs subject!"

# Step 4: Final hidden state
# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.10, 0.12]) ⊙ [0.62, 0.58] + [0.10, 0.12] ⊙ [0.68, 0.62]
    = [0.90, 0.88] ⊙ [0.62, 0.58] + [0.10, 0.12] ⊙ [0.68, 0.62]
    = [0.56, 0.51] + [0.07, 0.07]
    = [0.63, 0.58]

Result: After 8 words, "cat" signal (0.63) is STILL STRONG
        (Started at 0.80, only degraded to 0.63 - still usable!)
        Model can now correctly predict singular "was" not plural "were"
```

**At "hungry"**:

```python
Previous: h_{t-1} = [0.63, 0.58]
Input: x_t = [0.8, 0.3, 0.6]

Γ_r = [0.70, 0.75]
Γ_u = [0.40, 0.35]  # Moderate - completing the sentence, moderate update

# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.40, 0.35]) ⊙ [0.63, 0.58] + [0.40, 0.35] ⊙ [candidate]
    = [0.70, 0.62]  # Final state: "cat was hungry"
```

**Summary - Information Flow Across the Sentence**:

```
Word:      The cat  |  which  |  had  |  been  | sleeping | all | day |  was  | hungry
           ---------|---------|-------|--------|----------|-----|-----|-------|-------
h[0]:      0.80     |  0.79   | 0.70  | 0.68   |  0.63    | 0.58| 0.62|  0.63 | 0.70
(subject)           |         |       |        |          |     |     |       |
                    |         |       |        |          |     |     |       |
Γ_r:        -       |  0.82   | 0.88  | 0.90   |  0.85    | 0.80| 0.85|  0.95 | 0.70
(reset)             |  ↑HIGH  | ↑HIGH | ↑HIGH  |  ↑HIGH   |     |     | ↑HIGH |
                    | (USE!)  | (USE!)| (USE!) |  (USE!)  |     |     |(USE!) |
                    |         |       |        |          |     |     |       |
Γ_u:        -       |  0.05   | 0.15  | 0.12   |  0.70    | 0.50| 0.25|  0.10 | 0.40
(update)            |  ↓LOW   |       |        |  ↑HIGH   |     |     | ↓LOW  |
                    | (KEEP!) |       |        | (UPDATE!)|     |     |(KEEP!)|

Key insights:

Reset Gate (Γ_r):
- HIGH Γ_r (0.82-0.95) at most words = use most/all of previous context when computing candidate
- At "which", "had", "been", "sleeping", "was": Need context to understand properly
- At "was": Γ_r = 0.95 (VERY HIGH) - need almost ALL context to process verb correctly!
- LOW Γ_r would mean "ignore past, compute candidate fresh" (not needed here)

Update Gate (Γ_u):
- LOW Γ_u (0.05-0.15) at structural words = light update (keep ~90% old, preserve subject)
- HIGH Γ_u (0.70) at descriptive words = heavy update (take ~70% new, add content)
- At "which": Γ_u = 0.05 - keep 95% of "cat" info
- At "sleeping": Γ_u = 0.70 - important descriptor, update heavily
- At "was": Γ_u = 0.10 - keep 90% old for subject-verb agreement

Combined Effect:
- Subject dimension (h[0]) maintained from 0.80 → 0.63 over 8 words!
- High Γ_r ensures candidate uses context, low Γ_u ensures old info preserved
- This coordination allows "cat" to survive through relative clause to reach "was"
```

**What makes this work?**

1. **Low Γ_u at structural words** ("which", "was") keeps old info - preserves subject
2. **High Γ_u at descriptive words** ("sleeping") updates heavily - incorporates new content
3. **High Γ_r at verbs** ensures full context for proper processing
4. **Coordinated gate behavior** maintains long-range dependencies

This is why GRU can handle "The cat ... was" agreement even with many words between!

#### How Gates "Know" What to Do

**The answer: Learned weights during training!**

The gates don't "magically" know - they compute based on **learned weight matrices** $W_u$ and $W_r$.

Let's walk through a complete example to see what's **really happening**:

**Example sentence**: "The cat, which was very fluffy, was hungry"

#### Step-by-Step: What's Happening at Each Word

**At word "which" (after processing "cat")**:

```python
# Current state
Previous hidden: h_{t-1} = [0.8, 0.3]
# These numbers encode:
#   0.8 → Strong signal for "there's a cat (subject)"
#   0.3 → Neutral/slight positive sentiment

Current word embedding: x_t = [0.2, 0.9, 0.1]  # Embedding for "which"

# Step 1: Concatenate inputs
concat = [0.8, 0.3, 0.2, 0.9, 0.1]  # Shape: (5,)
#         └─h_{t-1}─┘ └──x_t─────┘

# Step 2: Compute update gate (using LEARNED weights W_u)
result = W_u · concat + b_u
       = [1.8, 1.7]  # Some intermediate values

Γ_u = σ([1.8, 1.7])
    = [0.86, 0.85]  # Wait, this is HIGH! Let me reconsider...

# Actually, for "which" after "cat", we want LOW Γ_u to preserve subject
# Let's say W_u learned to output:
Γ_u = [0.05, 0.07]  # Very low! Light update

# This tells us: "The word 'which' after 'cat' means we need to
# keep 'cat' - it's going to be important later!"
```

**Why is Γ_u = 0.05 here?**

During training, $W_u$ learned from examples like:

- "The cat, which was sleeping, **was** hungry" ✓ (correct agreement)
- "The cat, which was sleeping, **were** hungry" ✗ (wrong - loss is high)

Through backpropagation, $W_u$ adjusted to output **low** Γ_u values when it sees patterns like "noun, which" - because preserving the subject information (by keeping most of the old hidden state) leads to better predictions!

**At word "fluffy"**:

```python
Previous hidden: h_{t-1} = [0.76, 0.29]  # Still contains "cat" info
Current word: x_t = [0.6, 0.3, 0.8]      # Embedding for "fluffy"

# Compute gates
Γ_u = σ(W_u · [h_{t-1}, x_t] + b_u)
    = [0.70, 0.65]  # HIGH! This descriptor is important, update heavily

# This means: "Fluffy is an important descriptor, incorporate it strongly"

# Compute candidate (assume reset gate allows some context)
h̃_t = [0.45, 0.75]  # Candidate with "fluffy" info

# Final hidden state calculation
# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.70, 0.65]) ⊙ [0.76, 0.29] + [0.70, 0.65] ⊙ [0.45, 0.75]
    = [0.30, 0.35] ⊙ [0.76, 0.29] + [0.70, 0.65] ⊙ [0.45, 0.75]
    = [0.23, 0.10] + [0.32, 0.49]
    = [0.55, 0.59]  # Added "fluffy" info, "cat" signal weakened but present
```

**At word "was" (the verb)**:

```python
Previous hidden: h_{t-1} = [0.55, 0.59]  # Contains "cat" + descriptors
Current word: x_t = [0.1, 0.7, 0.2]      # Embedding for "was"

# Compute update gate
Γ_u = σ(W_u · [h_{t-1}, x_t] + b_u)
    = [0.10, 0.12]  # LOW! Light update, keep most old

# Why low? Because "was" needs to agree with "cat" (singular)
# The network learned: "When processing a verb, I need to preserve
# the subject to get agreement right!"

# Also compute reset gate
Γ_r = σ(W_r · [h_{t-1}, x_t] + b_r)
    = [0.95, 0.93]  # Very high!

# Why high? "We need ALL the previous context (including 'cat')
# to properly process this verb"

# Computing candidate
reset_hidden = [0.95, 0.93] ⊙ [0.55, 0.59]
             = [0.52, 0.55]  # Uses almost all previous info

h̃_t = tanh(W_h · [reset_hidden, x_t] + b_h)
     = tanh(W_h · [0.52, 0.55, 0.1, 0.7, 0.2] + b_h)
     = [0.58, 0.68]  # Candidate that incorporates verb with context

# Final hidden state
# Using formula: h^{(t)} = (1 - Γ_u) ⊙ h^{(t-1)} + Γ_u ⊙ h̃^{(t)}
h_t = (1 - [0.10, 0.12]) ⊙ [0.55, 0.59] + [0.10, 0.12] ⊙ [0.58, 0.68]
    = [0.90, 0.88] ⊙ [0.55, 0.59] + [0.10, 0.12] ⊙ [0.58, 0.68]
    = [0.50, 0.52] + [0.06, 0.08]
    = [0.56, 0.60]

# Result: Preserved "cat" info strongly (0.55 → 0.56, barely changed)
# even after processing multiple words!
```

#### What Numbers Actually Mean

Let's decode what these hidden state numbers represent:

```python
After "The cat":
h = [0.80, 0.30]
  ↓
  0.80 → "Strong singular subject present" (the cat)
  0.30 → "Neutral sentiment/descriptor tone"

After "which was very fluffy":
h = [0.55, 0.59]
  ↓
  0.55 → "Still remember singular subject" (decayed from 0.80 to 0.55)
  0.59 → "Added descriptive/attribute information" (increased from 0.30)

After "was":
h = [0.56, 0.60]
  ↓
  0.56 → "Singular subject PRESERVED for verb agreement"
  0.60 → "Verb context added"
```

**The key insight**: These dimensions don't store words - they store **abstract features** that the network learned are useful for the task!

#### How $W_u$ Learned These Patterns

During training on thousands of sentences:

```python
# Training examples the network saw:
Example 1: "The cat, which was fluffy, was hungry" → Correct output
Example 2: "The cat, which was fluffy, were hungry" → Wrong! High loss
Example 3: "The cats, which were fluffy, were hungry" → Correct output

# After seeing Example 2 with high loss:
Backward pass computed:
∂Loss/∂W_u = [some gradient indicating "you should have kept
              more 'cat' information to get 'was' correct!"]

# Weight update:
W_u := W_u - learning_rate × ∂Loss/∂W_u

# After many examples:
W_u learned pattern:
"When I see [noun + comma + which], output low Γ_u
 because that noun will be needed later for agreement!"
```

**Different contexts, different learned behaviors**:

```python
Context 1: "The cat, which..."
  → W_u outputs Γ_u = 0.05 (light update - keep 95% old, preserve subject!)

Context 2: "I love Paris. Rome..."
  → W_u outputs Γ_u = 0.90 (heavy update - take 90% new, new sentence!)

Context 3: "The movie was not"
  → W_u outputs Γ_u = 0.08 (light update - keep 92% old, preserve "not"!)

Context 4: "very very very happy"
  → W_u outputs Γ_u = 0.15 (light update - keep 85% old, accumulate intensifiers!)
```

All these patterns were **learned from data**, not hand-coded!

#### What About the Input?

**The input $x^{(t)}$ is a word embedding** - a dense vector of real numbers!

```
Word embeddings (learned representations):
"cat"   → [0.2, 0.8, 0.1, 0.5, 0.3, ...]  (e.g., 300 dimensions)
"love"  → [0.9, 0.1, 0.7, 0.3, 0.4, ...]
"dog"   → [0.3, 0.7, 0.2, 0.6, 0.3, ...]  (similar to "cat"!)
"hate"  → [0.1, 0.9, 0.3, 0.7, 0.6, ...]  (opposite of "love")

These capture semantic meaning in numerical form!
```

<a name="43-mathematics"></a>

### 4.3 Mathematical Formulation

#### Complete GRU Equations

At each time step $t$:

**1. Reset gate**:
$$\Gamma_r = \sigma(W_r \cdot [h^{(t-1)}, x^{(t)}] + b_r)$$

**2. Update gate**:
$$\Gamma_u = \sigma(W_u \cdot [h^{(t-1)}, x^{(t)}] + b_u)$$

**3. Candidate hidden state**:
$$\tilde{h}^{(t)} = \tanh(W_h \cdot [\Gamma_r \odot h^{(t-1)}, x^{(t)}] + b_h)$$

**4. Final hidden state**:
$$h^{(t)} = (1 - \Gamma_u) \odot h^{(t-1)} + \Gamma_u \odot \tilde{h}^{(t)}$$

**Where**:

- $\sigma$ = sigmoid function (outputs in $[0, 1]$)
- $\odot$ = element-wise multiplication (Hadamard product)
- $[\cdot, \cdot]$ = concatenation of vectors
- $\Gamma_r, \Gamma_u \in \mathbb{R}^{d_{hidden}}$ = gate values (one per hidden dimension)
- $\tilde{h}^{(t)} \in \mathbb{R}^{d_{hidden}}$ = candidate hidden state
- $h^{(t)} \in \mathbb{R}^{d_{hidden}}$ = final hidden state
- $x^{(t)} \in \mathbb{R}^{d_{input}}$ = input at time $t$ (word embedding)

#### Understanding Each Component

**Sigmoid ($\sigma$)**:
$$\sigma(x) = \frac{1}{1 + e^{-x}}$$

Properties:

- Output range: $(0, 1)$
- $\sigma(0) = 0.5$
- $\sigma(+\infty) = 1$
- $\sigma(-\infty) = 0$
- Derivative: $\sigma'(x) = \sigma(x)(1 - \sigma(x))$

Perfect for gates (need values in $[0, 1]$ to act as filters)!

**Tanh**:
$$\tanh(x) = \frac{e^x - e^{-x}}{e^x + e^{-x}}$$

Properties:

- Output range: $(-1, 1)$
- $\tanh(0) = 0$
- $\tanh(+\infty) = 1$
- $\tanh(-\infty) = -1$
- Centers data around 0
- Derivative: $\tanh'(x) = 1 - \tanh^2(x)$

Used for the actual hidden state values (allows positive and negative features).

**Element-wise Multiplication ($\odot$)**:

Also called **Hadamard product** - multiply corresponding elements:

```python
a = [1, 2, 3]
b = [0.5, 0.2, 0.8]
a ⊙ b = [1×0.5, 2×0.2, 3×0.8] = [0.5, 0.4, 2.4]
```

Acts as a **"soft" filter** controlled by gates:

- Gate value 1.0 → Let information through completely
- Gate value 0.0 → Block information completely
- Gate value 0.7 → Let 70% through

**Concatenation ($[\cdot, \cdot]$)**:

Joining vectors end-to-end:

```python
h_{t-1} = [0.8, 0.3]           # Shape: (2,)
x_t = [0.2, 0.9, 0.1]          # Shape: (3,)
[h_{t-1}, x_t] = [0.8, 0.3, 0.2, 0.9, 0.1]  # Shape: (5,)
```

This combined vector is the input to gate computations.

<a name="44-forward-prop"></a>

### 4.4 Forward Propagation - Complete Numerical Example

Let's work through GRU with real numbers!

#### Setup

**Task**: Process "I love NLP"

**Dimensions**:

- Input: $d_{input} = 3$ (word embeddings)
- Hidden: $d_{hidden} = 2$

**Embeddings**:

```python
"I":    [1.0, 0.0, 0.0]
"love": [0.0, 1.0, 0.0]
"NLP":  [0.0, 0.0, 1.0]
```

**Weights** (simplified, normally random):

```python
# Reset gate weights
W_r = [[0.5, 0.3],   # Shape: (5, 2) because input is [h_{t-1}, x_t]
       [0.2, 0.4],   # which has dimension 2 + 3 = 5
       [0.1, 0.2],
       [0.3, 0.1],
       [0.2, 0.5]]
b_r = [0.1, 0.1]

# Update gate weights
W_u = [[0.4, 0.2],
       [0.3, 0.5],
       [0.1, 0.3],
       [0.2, 0.1],
       [0.5, 0.2]]
b_u = [0.1, 0.1]

# Candidate weights
W_h = [[0.6, 0.1],
       [0.2, 0.4],
       [0.3, 0.2],
       [0.1, 0.3],
       [0.4, 0.5]]
b_h = [0.0, 0.0]
```

#### Time Step 1: Process "I"

**Input**: $x^{(1)} = [1.0, 0.0, 0.0]$  
**Previous hidden**: $h^{(0)} = [0.0, 0.0]$

**Step 1: Concatenate $[h^{(0)}, x^{(1)}]$**

```
concat = [0.0, 0.0, 1.0, 0.0, 0.0]  # Shape: (5,)
```

**Step 2: Compute Reset Gate $\Gamma_r^{(1)}$**

$$\Gamma_r^{(1)} = \sigma(W_r \cdot [h^{(0)}, x^{(1)}] + b_r)$$

```python
# Matrix multiplication
W_r · concat = [[0.5, 0.3],      [0.0]   [0.1]
                [0.2, 0.4],       [0.0]   [0.2]
                [0.1, 0.2],   ·   [1.0] = [0.1]  (only third element matters)
                [0.3, 0.1],       [0.0]   [0.3]
                [0.2, 0.5]]       [0.0]   [0.2]

# Sum results
result = [0.1 + 0.1, 0.2 + 0.1] = [0.2, 0.3]

# Add bias
pre_sigmoid = [0.2, 0.3] + [0.1, 0.1] = [0.3, 0.4]

# Apply sigmoid
Γ_r^{(1)} = σ([0.3, 0.4])
          = [σ(0.3), σ(0.4)]
          = [0.574, 0.599]
```

**Step 3: Compute Update Gate $\Gamma_u^{(1)}$**

$$\Gamma_u^{(1)} = \sigma(W_u \cdot [h^{(0)}, x^{(1)}] + b_u)$$

```python
# Similar computation
W_u · concat + b_u = [0.2, 0.4]

Γ_u^{(1)} = σ([0.2, 0.4])
          = [0.550, 0.599]
```

**Step 4: Compute Candidate $\tilde{h}^{(1)}$**

$$\tilde{h}^{(1)} = \tanh(W_h \cdot [\Gamma_r^{(1)} \odot h^{(0)}, x^{(1)}] + b_h)$$

First, reset the previous hidden state:

```python
Γ_r^{(1)} ⊙ h^{(0)} = [0.574, 0.599] ⊙ [0.0, 0.0]
                     = [0.0, 0.0]

concat_candidate = [0.0, 0.0, 1.0, 0.0, 0.0]
```

Then compute:

```python
W_h · concat_candidate + b_h = [0.3, 0.2]

h̃^{(1)} = tanh([0.3, 0.2])
        = [0.291, 0.197]
```

**Step 5: Compute Final Hidden State $h^{(1)}$**

$$h^{(1)} = (1 - \Gamma_u^{(1)}) \odot h^{(0)} + \Gamma_u^{(1)} \odot \tilde{h}^{(1)}$$

```python
# Old part ((1-Γ_u^{(1)}) ⊙ h^{(0)})
old = [1-0.550, 1-0.599] ⊙ [0.0, 0.0]
    = [0.450, 0.401] ⊙ [0.0, 0.0]
    = [0.0, 0.0]

# New part (Γ_u^{(1)} ⊙ h̃^{(1)})
new = [0.550, 0.599] ⊙ [0.291, 0.197]
    = [0.160, 0.118]

# Final
h^{(1)} = [0.0, 0.0] + [0.160, 0.118]
        = [0.160, 0.118]
```

**Result**: $h^{(1)} = [0.160, 0.118]$ encodes "I"

#### Time Step 2: Process "love"

**Input**: $x^{(2)} = [0.0, 1.0, 0.0]$  
**Previous**: $h^{(1)} = [0.160, 0.118]$

**Step 1: Concatenate**

```
concat = [0.160, 0.118, 0.0, 1.0, 0.0]
```

**Step 2-3: Gates**

```python
# Reset gate
Γ_r^{(2)} = σ(W_r · concat + b_r)
          = σ([0.465, 0.392])
          = [0.614, 0.597]

# Update gate
Γ_u^{(2)} = σ(W_u · concat + b_u)
          = σ([0.439, 0.540])
          = [0.608, 0.632]
```

**Step 4: Candidate**

```python
# Reset previous hidden
Γ_r^{(2)} ⊙ h^{(1)} = [0.614, 0.597] ⊙ [0.160, 0.118]
                     = [0.098, 0.070]

concat_candidate = [0.098, 0.070, 0.0, 1.0, 0.0]

h̃^{(2)} = tanh(W_h · concat_candidate + b_h)
        = tanh([0.348, 0.467])
        = [0.334, 0.435]
```

**Step 5: Final Hidden State**

$$h^{(2)} = (1 - \Gamma_u^{(2)}) \odot h^{(1)} + \Gamma_u^{(2)} \odot \tilde{h}^{(2)}$$

```python
h^{(2)} = [1-0.608, 1-0.632] ⊙ [0.160, 0.118] + [0.608, 0.632] ⊙ [0.334, 0.435]
        = [0.392, 0.368] ⊙ [0.160, 0.118] + [0.608, 0.632] ⊙ [0.334, 0.435]
        = [0.063, 0.043] + [0.203, 0.275]
        = [0.266, 0.318]
```

**Result**: $h^{(2)} = [0.266, 0.318]$ encodes "I love"

#### Summary

```
Time step 0: h^{(0)} = [0.000, 0.000]

Time step 1: "I"
  Γ_r^{(1)} = [0.574, 0.599]  (reset gate)
  Γ_u^{(1)} = [0.550, 0.599]  (update gate)
  h̃^{(1)} = [0.291, 0.197]  (candidate)
  h^{(1)} = [0.160, 0.118]  (final hidden state)

Time step 2: "love"
  Γ_r^{(2)} = [0.614, 0.597]
  Γ_u^{(2)} = [0.608, 0.632]
  h̃^{(2)} = [0.334, 0.435]
  h^{(2)} = [0.266, 0.318]

Time step 3: "NLP"
  (continue similarly...)
```

**Key Observations**:

1. Gates have values in $[0, 1]$ (from sigmoid)
2. Hidden states have values in $[-1, 1]$ (from tanh)
3. Each time step uses information from previous step
4. Gates control information flow dynamically

<a name="45-training"></a>

### 4.5 How GRU Weights Are Learned

#### The Complete Picture: GRU in a Larger Network

**Critical insight**: GRU is NOT a standalone model - it's a **component/layer** in a complete architecture!

```
Input Sequence → [GRU Layer] → [Output Layer] → Final Prediction
                 (processes      (makes actual
                  sequence)       classification/
                                  prediction)
```

#### Complete Architecture Example: Sentiment Analysis

**Task**: Classify movie reviews as positive or negative

```python
Architecture:
-----------
Input: "The movie was amazing!"  # Raw text

↓ [Embedding Layer]
"The"    → [0.2, 0.8, 0.1]
"movie"  → [0.5, 0.3, 0.9]
"was"    → [0.1, 0.7, 0.2]
"amazing"→ [0.9, 0.2, 0.8]

↓ [GRU Layer - processes sequence]
t=1: h^{(1)} = [0.12, 0.34]  (after "The")
t=2: h^{(2)} = [0.45, 0.67]  (after "movie")
t=3: h^{(3)} = [0.51, 0.72]  (after "was")
t=4: h^{(4)} = [0.89, 0.91]  (after "amazing") ← Final hidden state

↓ [Dense/Output Layer]
output = softmax(W_output · h^{(4)} + b_output)
       = [0.05, 0.95]  # [P(negative), P(positive)]

↓ [Compare with true label]
True label:    [0, 1]      (positive)
Prediction:    [0.05, 0.95] (positive - correct!)

↓ [Compute Loss]
Loss = CrossEntropy([0, 1], [0.05, 0.95])
     = -log(0.95)
     = 0.05  (low loss - good prediction!)
```

#### The Backpropagation Flow

**The magic**: Gradients flow BACKWARD from the loss through all layers, including the GRU!

```
Forward Pass:
Input → Embeddings → GRU → Output → Loss

Backward Pass:
Loss → ∂Loss/∂W_output → ∂Loss/∂h^{(4)} → ∂Loss/∂GRU_weights
```

**Step-by-step gradient flow**:

```python
1. Compute loss gradient w.r.t. output weights:
   ∂Loss/∂W_output

2. Compute loss gradient w.r.t. final hidden state:
   ∂Loss/∂h^{(4)} = [0.3, -0.2]
   # This tells us: "To reduce loss, h^{(4)} should have been different"

3. Backpropagate through time (BPTT) - compute gradients for all time steps:
   ∂Loss/∂h^{(3)}, ∂Loss/∂h^{(2)}, ∂Loss/∂h^{(1)}

4. Compute gradients for GRU weights:
   ∂Loss/∂W_u, ∂Loss/∂W_r, ∂Loss/∂W_h
   ∂Loss/∂b_u, ∂Loss/∂b_r, ∂Loss/∂b_h
```

#### Mathematical Detail: Computing GRU Weight Gradients

**At time step $t=4$** (processing "amazing"):

Remember the equations:
$$h^{(4)} = (1 - \Gamma_u^{(4)}) \odot h^{(3)} + \Gamma_u^{(4)} \odot \tilde{h}^{(4)}$$

Using chain rule:

**Gradient w.r.t. update gate**:
$$\frac{\partial \text{Loss}}{\partial \Gamma_u^{(4)}} = \frac{\partial \text{Loss}}{\partial h^{(4)}} \cdot \frac{\partial h^{(4)}}{\partial \Gamma_u^{(4)}}$$

$$= \frac{\partial \text{Loss}}{\partial h^{(4)}} \cdot (\tilde{h}^{(4)} - h^{(3)})$$

**Gradient w.r.t. update gate weights**:

Since $\Gamma_u^{(4)} = \sigma(W_u \cdot [h^{(3)}, x^{(4)}] + b_u)$:

$$\frac{\partial \text{Loss}}{\partial W_u} = \frac{\partial \text{Loss}}{\partial \Gamma_u^{(4)}} \cdot \frac{\partial \Gamma_u^{(4)}}{\partial W_u}$$

$$= \frac{\partial \text{Loss}}{\partial \Gamma_u^{(4)}} \cdot \sigma'(\cdot) \cdot [h^{(3)}, x^{(4)}]^T$$

**Weight update**:
$$W_u^{new} = W_u^{old} - \alpha \cdot \frac{\partial \text{Loss}}{\partial W_u}$$

where $\alpha$ is the learning rate.

#### Concrete Learning Example: Negation Detection

**Training scenario**: Teaching the network to handle negation

**Example**: "The movie was not good" → Negative (label = [1, 0])

**First iteration (untrained network)**:

```python
Forward pass:
t=1 "The":    h^{(1)} = [0.1, 0.2]
t=2 "movie":  h^{(2)} = [0.3, 0.4]
t=3 "was":    h^{(3)} = [0.5, 0.6]
t=4 "not":    h^{(4)} = [0.4, 0.5]
              # Oops! Didn't update much - forgot importance of "not"
              # Γ_u was around 0.2 (light update)
t=5 "good":   h^{(5)} = [0.8, 0.9]
              # Now thinks positive because of "good"!
              # Γ_u was around 0.8 (heavy update)

Output: softmax(W · h^{(5)}) = [0.2, 0.8]  # 80% positive - WRONG!
True:   [1.0, 0.0]  # Should be negative

Loss: CrossEntropy([1.0, 0.0], [0.2, 0.8]) = 1.6  (high loss - bad!)
```

**Backward pass - what the gradients tell us**:

```python
∂Loss/∂h^{(5)} = [-0.8, 0.8]
# Means: "h^{(5)} should have been more negative!"

# Gradient flows back to t=4:
∂Loss/∂h^{(4)} = ...
# Means: "h^{(4)} should have strongly captured negation!"

# At t=4, computing gradient for update gate:
∂Loss/∂Γ_u^{(4)} = ∂Loss/∂h^{(4)} · (h̃^{(4)} - h^{(3)})
                 = ... (positive value if h̃^{(4)} had good negation info)
# Means: "Update gate should have been HIGHER at 'not'!"
# Should have updated more to capture this negation word

# Update weights:
W_u := W_u - α · ∂Loss/∂W_u
# W_u changes to make Γ_u higher when seeing "not"
```

**After training on many examples**:

The network has learned patterns:

```python
t=4 "not":  Γ_u^{(4)} = [0.85, 0.90]  # Learned to update heavily!
            # (was ~0.2 before training)
            h^{(4)} = [0.6, 0.1]       # Strong negation signal

t=5 "good": Γ_u^{(5)} = [0.30, 0.25]  # Learned to update lightly
            # Keep the negation, add some "good" context
            h^{(5)} = [0.4, 0.2]       # Overall negative encoding

Output: [0.85, 0.15]  # 85% negative - CORRECT!
Loss: 0.16  (low - good!)
```

**What was learned**:

```python
W_u learned patterns like:
- When input is "not" → produce high Γ_u values
  (update heavily to capture this important negation info!)

- When input is punctuation → produce high Γ_u values
  (update to reset for new sentence)

W_r learned patterns like:
- After "not" → keep high Γ_r when processing next word
  (need context to apply negation)

- After period → low Γ_r
  (reset, previous sentence not relevant)
```

#### Different Tasks Learn Different Patterns

The same GRU architecture learns **task-specific** patterns:

**Task 1: Sentiment Analysis**

```python
Training data:
- "not good" → negative
- "not bad" → positive
- "very happy" → positive

Learned patterns in W_u:
- High Γ_u after "not" (negation is important, update!)
- High Γ_u after "very" (intensifier is important, update!)
- High Γ_u after punctuation (reset for new sentence, update!)
```

**Task 2: Language Modeling** (predict next word)

```python
Training data:
- "The cat sat on the ___" → "mat"
- "The dog sat on the ___" → "floor"

Learned patterns in W_u:
- Low Γ_u after subject nouns (keep for agreement, light update)
- Moderate Γ_u after prepositions (some context needed)

Learned patterns in W_r:
- High Γ_r before prepositions (need subject info)
- Low Γ_r at sentence start (fresh start)
```

**Task 3: Named Entity Recognition**

```python
Training data:
- "Barack Obama was president" → [PERSON, PERSON, O, O]
- "Paris is in France" → [LOC, O, O, LOC]

Learned patterns:
- Low Γ_u when processing multi-word names (keep to continue entity)
- Low Γ_r after "is/was" (previous name less relevant)
```

#### The Key Insight

**GRU weights don't learn "universal" patterns** - they learn whatever patterns are useful for YOUR specific task through the loss function!

```
Loss decreases
    ↓
Gradients flow backward
    ↓
Weights adjust
    ↓
Gates behave differently
    ↓
Better hidden states
    ↓
Better predictions
    ↓
Loss decreases (repeat!)
```

#### Summary: The Complete Training Loop

```python
for each training example:
    # 1. Forward pass
    for t in range(sequence_length):
        # Compute gates
        Γ_r^{(t)} = σ(W_r · [h^{(t-1)}, x^{(t)}] + b_r)
        Γ_u^{(t)} = σ(W_u · [h^{(t-1)}, x^{(t)}] + b_u)

        # Compute candidate
        h̃^{(t)} = tanh(W_h · [Γ_r^{(t)} ⊙ h^{(t-1)}, x^{(t)}] + b_h)

        # Compute hidden state
        h^{(t)} = (1 - Γ_u^{(t)}) ⊙ h^{(t-1)} + Γ_u^{(t)} ⊙ h̃^{(t)}

    # 2. Make prediction
    output = softmax(W_output · h^{(final)} + b_output)

    # 3. Compute loss
    loss = CrossEntropy(true_label, output)

    # 4. Backward pass (automatic in frameworks like TensorFlow/PyTorch)
    gradients = compute_gradients(loss)

    # 5. Update ALL weights (including GRU weights)
    W_u -= learning_rate × ∂loss/∂W_u
    W_r -= learning_rate × ∂loss/∂W_r
    W_h -= learning_rate × ∂loss/∂W_h
    W_output -= learning_rate × ∂loss/∂W_output
    # (and biases too)
```

**The beauty**: You only need to define:

1. Your task (classification, translation, etc.)
2. Your loss function
3. Your training data with labels

The GRU automatically learns what information to update, what to keep, and when to reset - all optimized for YOUR specific task!

<a name="46-why-better"></a>

### 4.6 Why GRUs Work Better Than Simple RNNs

#### 1. Gradient Flow: The Mathematical Advantage

**Simple RNN gradient**:
$$\frac{\partial h^{(t)}}{\partial h^{(t-1)}} = \text{diag}(\tanh'(z)) \cdot W_{hh}$$

**Problem**:

- Always multiplying by $\tanh'$ (which is ≤ 1)
- Always multiplying by $W_{hh}$
- Over many time steps: gradient vanishes or explodes!

**GRU gradient**:
$$\frac{\partial h^{(t)}}{\partial h^{(t-1)}} = (1 - \Gamma_u^{(t)}) + \Gamma_u^{(t)} \cdot \frac{\partial \tilde{h}^{(t)}}{\partial h^{(t-1)}}$$

**Benefit**:

- The $(1 - \Gamma_u^{(t)})$ term provides a **direct path** for gradients!
- When $\Gamma_u^{(t)} \approx 0$ (keeping old state):
  $$\frac{\partial h^{(t)}}{\partial h^{(t-1)}} \approx 1$$

**Gradient doesn't vanish!**

This is like having a **"gradient highway"** that bypasses the problematic nonlinearities.

**Numerical comparison over 20 time steps**:

**Simple RNN**:

```python
# Assuming tanh'(z) ≈ 0.4 and W_hh has max eigenvalue 0.5
Gradient magnitude ∝ (0.4 × 0.5)^20
                    ≈ (0.2)^20
                    ≈ 10^-14  (completely vanished!)
```

**GRU** (with $\Gamma_u \approx 0.1$ = light updates):

```python
# Direct path through (1-Γ_u) term
Gradient magnitude ∝ ∏_{t=1}^{20} (1 - Γ_u^{(t)})
                    ≈ (0.9)^20
                    ≈ 0.12  (still usable!)
```

#### 2. Selective Memory: Adaptive Information Retention

**Simple RNN**:

- Always overwrites hidden state completely
- Cannot preserve important information over time

```python
h^{(t)} = tanh(W_{hh} · h^{(t-1)} + W_{xh} · x^{(t)} + b)
# Every new input modifies the ENTIRE hidden state
# No way to "protect" important information
```

**GRU**:

- Can **choose** to keep old information
- Can **choose** how much new information to incorporate

```python
h^{(t)} = (1 - Γ_u^{(t)}) ⊙ h^{(t-1)} + Γ_u^{(t)} ⊙ h̃^{(t)}
# If Γ_u ≈ 0, keeps h^{(t-1)} (preserves memory!)
# If Γ_u ≈ 1, takes h̃^{(t)} (accepts new info!)
```

**Example with long-range dependencies**:

```
Sentence: "The cat, which had been sleeping on the couch
          for several hours yesterday afternoon, was hungry"

          ← 15 words between "cat" and "was" →

Simple RNN:
  After processing 15 words, "cat" information is mostly lost
  At "was", cannot determine correct subject-verb agreement
  Output might be: "were" (incorrect)

GRU:
  Update gate learns: Γ_u ≈ 0.1 for those 15 words (light updates)
  Keeps 90% of "cat" information throughout!

  Mathematically:
  "cat" signal strength: 0.8 (initial)
  After 15 steps with Γ_u = 0.1:
    strength ≈ 0.8 × (1-0.1)^15 ≈ 0.16  (still detectable!)

  Simple RNN (decay ≈ 0.5 per step):
    strength ≈ 0.8 × 0.5^15 ≈ 0.000024  (lost!)

  At "was", GRU still remembers "cat" → correct agreement
```

#### 3. Adaptive Context: Task-Specific Behavior

**GRU can learn different behaviors for different contexts**:

**Example 1: Sentiment with contrast**

```python
Input: "The movie was not good, but the acting was great"

At "not good":
  Γ_u^{(t)} ≈ [0.8, 0.7]  (update gate high)
  → Incorporate negative sentiment strongly

At "but":
  Γ_r^{(t)} ≈ [0.1, 0.2]  (reset gate low)
  → Reset! Previous sentiment less important
  → Preparing for contrasting opinion

At "great":
  Γ_u^{(t)} ≈ [0.9, 0.9]  (update gate high)
  → Strongly update with positive sentiment
  → This is the dominant sentiment

Final hidden state: Overall positive (focusing on "acting was great")
```

**Example 2: Sequence labeling**

```python
Input: "New York is a city"
Task: Named Entity Recognition
Labels: [B-LOC, I-LOC, O, O, O]

At "New":
  Γ_u ≈ 0.5  (moderate - might be start of entity)

At "York":
  Γ_u ≈ 0.2  (low - continue entity, keep "New")
  Γ_r ≈ 0.9  (high - need "New" to recognize "New York")

At "is":
  Γ_u ≈ 0.7  (high - entity ended, new context)
  Γ_r ≈ 0.2  (low - can mostly forget entity details)
```

#### 4. Reset Gate: Context Management

**Unique to GRU**: Can decide when to use past information **before** computing new candidate

**Example: Topic shifts**

```
Sentence: "I love Paris. I hate Rome."

Without reset gate (like simple RNN):
  Processing "hate": Uses full previous hidden state
  h̃ = tanh(W · [h_prev, x_hate])
  → "love" sentiment contaminates "hate" computation

With reset gate:
  Γ_r ≈ 0.1  (almost zero!)
  h̃ = tanh(W · [0.1 × h_prev, x_hate])
  → "hate" computed almost independently
  → Clean separation of sentiments
```

#### 5. Comparative Analysis

**Feature comparison**:

| Feature                 | Simple RNN                | GRU                            |
| ----------------------- | ------------------------- | ------------------------------ |
| **Gradient flow**       | Multiplicative (vanishes) | Additive (preserved)           |
| **Long-term memory**    | Poor (exponential decay)  | Good (controlled by gates)     |
| **Selective update**    | No (always overwrites)    | Yes (via $\Gamma_u$)           |
| **Context control**     | No                        | Yes (via $\Gamma_r$)           |
| **Parameters**          | $W_{hh}, W_{xh}, b$       | $W_u, W_r, W_h, b_u, b_r, b_h$ |
| **Training complexity** | Easier                    | More complex                   |
| **Sequence length**     | ~10-20 steps              | 100+ steps                     |

**Memory retention over time**:

```python
# Information strength after T time steps

Simple RNN:
  strength(T) ≈ initial × (decay_factor)^T
  where decay_factor ≈ 0.3-0.5

  After 50 steps: 0.8 × 0.4^50 ≈ 10^-20 (lost)

GRU (with low update gate Γ_u ≈ 0.1):
  strength(T) ≈ initial × (1 - Γ_u)^T
  where (1 - Γ_u) ≈ 0.85-0.95

  After 50 steps: 0.8 × 0.9^50 ≈ 0.004 (weak but present!)
```

#### 6. When GRUs Make the Difference

**Scenarios where GRUs excel**:

**Long-range dependencies**:

```
"The keys, which I had left on the kitchen table this morning, are ___"
→ GRU remembers "keys" (plural) → "are" (correct)
→ Simple RNN forgets "keys" → might output "is" (wrong)
```

**Multiple nested contexts**:

```
"The company [that hired the consultant [who recommended the policy]] failed"
→ GRU maintains multiple context levels through selective updates
→ Simple RNN loses nested structure
```

**Sequential decisions with delayed rewards**:

```
"Although initially skeptical, [long description], I ultimately loved it"
→ GRU preserves initial "skeptical" while processing description
→ Correctly resolves to final "loved" sentiment
```

#### Summary

**Why GRUs work better**:

1. **Gradient highways** → Can learn from distant past
2. **Selective memory** → Preserves important information
3. **Adaptive gates** → Task-specific learned behavior
4. **Reset mechanism** → Clean context management
5. **Stable training** → Gradients neither vanish nor explode

**The cost**:

- 3× more parameters than simple RNN
- 3× more computation per time step
- More complex to implement and debug

**The benefit**:

- Can handle 5-10× longer sequences effectively
- Much better performance on real-world tasks
- More stable and reliable training

**Bottom line**: For any serious sequential task, GRUs (or LSTMs) are essential!

---

<a name="47-summary"></a>

### 4.7 Chapter Summary

**What we learned**:

1. **GRUs solve the vanishing gradient problem** through gated connections
2. **Two gates control information flow**:
   - Update gate ($\Gamma_u$): Controls how much to UPDATE (high = take new, low = keep old)
   - Reset gate ($\Gamma_r$): Controls how much past to use in candidate
3. **Hidden states are numerical vectors**, not words
4. **Gates are learned during training** via backpropagation from task loss
5. **GRUs are components** in larger networks with task-specific outputs
6. **Key advantage**: Gradient highways enable long-range learning

**Key equations** (for reference):

$$\Gamma_r = \sigma(W_r \cdot [h^{(t-1)}, x^{(t)}] + b_r)$$

$$\Gamma_u = \sigma(W_u \cdot [h^{(t-1)}, x^{(t)}] + b_u)$$

$$\tilde{h}^{(t)} = \tanh(W_h \cdot [\Gamma_r \odot h^{(t-1)}, x^{(t)}] + b_h)$$

$$h^{(t)} = (1 - \Gamma_u) \odot h^{(t-1)} + \Gamma_u \odot \tilde{h}^{(t)}$$

**Understanding the update gate**:

- **High Γ_u (→1)**: UPDATE heavily (take ~100% new, ~0% old)
- **Low Γ_u (→0)**: DON'T UPDATE (keep ~100% old, ~0% new)
- Formula: $h^{(t)} = (1-\Gamma_u) \times \text{old} + \Gamma_u \times \text{new}$

## 5. Complete Implementation and Training

<a name="51-example"></a>

### 5.1 Sentiment Analysis Example

We'll build a complete sentiment classifier for movie reviews!

**Dataset**: IMDB movie reviews (positive/negative)

**Task**: Given review text → Predict sentiment (0=negative, 1=positive)

**Examples**:

```
"This movie was absolutely fantastic!" → Positive (1)
"Worst film I've ever seen, total waste of time." → Negative (0)
"The acting was superb and the plot kept me engaged." → Positive (1)
```

<a name="52-from-scratch"></a>

### 5.2 From-Scratch Implementation (NumPy)

This implementation shows exactly what's happening under the hood!

```python
import numpy as np

class GRUCell:
    """
    Single GRU cell implementation from scratch
    """

    def __init__(self, input_size, hidden_size):
        """
        Initialize GRU cell

        Args:
            input_size: Dimension of input vectors
            hidden_size: Dimension of hidden state
        """
        self.input_size = input_size
        self.hidden_size = hidden_size

        # Xavier initialization for weights
        limit = np.sqrt(6 / (input_size + hidden_size))

        # Reset gate parameters
        self.W_r = np.random.uniform(-limit, limit,
                                     (input_size + hidden_size, hidden_size))
        self.b_r = np.zeros(hidden_size)

        # Update gate parameters
        self.W_z = np.random.uniform(-limit, limit,
                                     (input_size + hidden_size, hidden_size))
        self.b_z = np.zeros(hidden_size)

        # Candidate hidden state parameters
        self.W_h = np.random.uniform(-limit, limit,
                                     (input_size + hidden_size, hidden_size))
        self.b_h = np.zeros(hidden_size)

    def forward(self, x_t, h_prev):
        """
        Forward pass for one time step

        Args:
            x_t: Input at time t, shape (batch_size, input_size)
            h_prev: Previous hidden state, shape (batch_size, hidden_size)

        Returns:
            h_t: New hidden state
            cache: Values needed for backward pass
        """
        batch_size = x_t.shape[0]

        # Concatenate [h_prev, x_t]
        concat = np.concatenate([h_prev, x_t], axis=1)

        # Reset gate
        r_t = self.sigmoid(np.dot(concat, self.W_r) + self.b_r)

        # Update gate
        z_t = self.sigmoid(np.dot(concat, self.W_z) + self.b_z)

        # Candidate hidden state
        # Reset previous hidden state
        h_reset = r_t * h_prev
        concat_candidate = np.concatenate([h_reset, x_t], axis=1)
        h_tilde = np.tanh(np.dot(concat_candidate, self.W_h) + self.b_h)

        # Final hidden state
        h_t = z_t * h_prev + (1 - z_t) * h_tilde

        # Cache for backward pass
        cache = {
            'x_t': x_t,
            'h_prev': h_prev,
            'concat': concat,
            'r_t': r_t,
            'z_t': z_t,
            'h_tilde': h_tilde,
            'h_reset': h_reset,
            'concat_candidate': concat_candidate
        }

        return h_t, cache

    @staticmethod
    def sigmoid(x):
        """Sigmoid activation"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    @staticmethod
    def tanh(x):
        """Tanh activation"""
        return np.tanh(x)


class GRU:
    """
    Multi-layer GRU for sequence processing
    """

    def __init__(self, input_size, hidden_size, output_size, num_layers=1):
        """
        Initialize GRU network

        Args:
            input_size: Dimension of input
            hidden_size: Dimension of hidden state
            output_size: Dimension of output
            num_layers: Number of GRU layers
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.num_layers = num_layers

        # Create GRU cells
        self.cells = []
        for i in range(num_layers):
            if i == 0:
                cell = GRUCell(input_size, hidden_size)
            else:
                cell = GRUCell(hidden_size, hidden_size)
            self.cells.append(cell)

        # Output layer
        limit = np.sqrt(6 / (hidden_size + output_size))
        self.W_out = np.random.uniform(-limit, limit,
                                       (hidden_size, output_size))
        self.b_out = np.zeros(output_size)

    def forward(self, X, return_sequences=False):
        """
        Forward pass through entire sequence

        Args:
            X: Input sequence, shape (batch_size, seq_length, input_size)
            return_sequences: If True, return output at each time step

        Returns:
            If return_sequences=False: output at last time step
            If return_sequences=True: outputs at all time steps
        """
        batch_size, seq_length, _ = X.shape

        # Initialize hidden states for all layers
        hidden_states = [np.zeros((batch_size, self.hidden_size))
                        for _ in range(self.num_layers)]

        # Store outputs
        outputs = []

        # Process sequence
        for t in range(seq_length):
            x_t = X[:, t, :]

            # Process through each layer
            for layer_idx in range(self.num_layers):
                h_t, _ = self.cells[layer_idx].forward(x_t, hidden_states[layer_idx])
                hidden_states[layer_idx] = h_t
                x_t = h_t  # Output of this layer is input to next

            # Compute output
            output_t = np.dot(hidden_states[-1], self.W_out) + self.b_out
            outputs.append(output_t)

        if return_sequences:
            return np.array(outputs).transpose(1, 0, 2)  # (batch, seq, output)
        else:
            return outputs[-1]  # Last output only

    def predict(self, X):
        """
        Make predictions (apply softmax to outputs)
        """
        logits = self.forward(X, return_sequences=False)
        # Apply softmax
        exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probabilities = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        return probabilities


# Example usage
print("=" * 70)
print("FROM-SCRATCH GRU IMPLEMENTATION")
print("=" * 70)

# Create sample data
batch_size = 2
seq_length = 5
input_size = 10
hidden_size = 8
output_size = 2

# Random input sequence
X = np.random.randn(batch_size, seq_length, input_size)

# Create GRU
gru = GRU(input_size, hidden_size, output_size, num_layers=1)

# Forward pass
output = gru.forward(X, return_sequences=False)
print(f"\nInput shape: {X.shape}")
print(f"Output shape: {output.shape}")
print(f"Output (logits):\n{output}")

# Predictions
predictions = gru.predict(X)
print(f"\nPredictions (probabilities):\n{predictions}")
print(f"Predicted classes: {np.argmax(predictions, axis=1)}")

print("\n✓ From-scratch GRU working!")
```

<a name="53-tensorflow"></a>

### 5.3 Complete TensorFlow/Keras Training Example

Now let's build and train a real sentiment classifier!

```python
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt

# Set seeds
np.random.seed(42)
tf.random.set_seed(42)

print("\n" + "=" * 70)
print("COMPLETE GRU SENTIMENT ANALYSIS - TENSORFLOW/KERAS")
print("=" * 70)

# ============================================================================
# 1. CREATE SAMPLE DATASET
# ============================================================================

print("\n📊 Creating sample dataset...")

# Sample movie reviews (normally you'd use IMDB dataset)
positive_reviews = [
    "this movie was absolutely fantastic and amazing",
    "loved every minute of it incredible acting",
    "best film i have seen this year wonderful",
    "excellent story and great performances outstanding",
    "highly recommended brilliant masterpiece",
    "superb direction and beautiful cinematography",
    "amazing plot twists kept me engaged",
    "wonderful experience great entertainment"
] * 100  # Repeat for more data

negative_reviews = [
    "terrible movie complete waste of time",
    "worst film ever boring and dull",
    "awful acting and horrible plot",
    "do not watch this garbage terrible",
    "extremely disappointing and poorly made",
    "bad script and weak performances",
    "boring story nothing interesting happens",
    "not worth watching very disappointing"
] * 100

# Combine and create labels
texts = positive_reviews + negative_reviews
labels = [1] * len(positive_reviews) + [0] * len(negative_reviews)

# Shuffle
indices = np.random.permutation(len(texts))
texts = [texts[i] for i in indices]
labels = [labels[i] for i in indices]

# Split into train/val/test
train_size = int(0.7 * len(texts))
val_size = int(0.15 * len(texts))

train_texts = texts[:train_size]
train_labels = labels[:train_size]

val_texts = texts[train_size:train_size + val_size]
val_labels = labels[train_size:train_size + val_size]

test_texts = texts[train_size + val_size:]
test_labels = labels[train_size + val_size:]

print(f"Training samples: {len(train_texts)}")
print(f"Validation samples: {len(val_texts)}")
print(f"Test samples: {len(test_texts)}")

# Show examples
print(f"\nExample positive review: '{train_texts[0]}'")
print(f"Label: {train_labels[0]}")
print(f"\nExample negative review: '{train_texts[len(positive_reviews)]}'")
print(f"Label: {train_labels[len(positive_reviews)]}")

# ============================================================================
# 2. TEXT PREPROCESSING
# ============================================================================

print("\n🔧 Preprocessing text...")

# Create text vectorizer
MAX_TOKENS = 1000
MAX_LENGTH = 20

vectorizer = layers.TextVectorization(
    max_tokens=MAX_TOKENS,
    output_mode='int',
    output_sequence_length=MAX_LENGTH
)

# Adapt to training data
vectorizer.adapt(train_texts)

vocab_size = vectorizer.vocabulary_size()
print(f"Vocabulary size: {vocab_size}")

# Test vectorization
test_sentence = train_texts[0]
vectorized = vectorizer(test_sentence)
print(f"\nTest sentence: '{test_sentence}'")
print(f"Vectorized: {vectorized.numpy()}")

# ============================================================================
# 3. BUILD GRU MODEL
# ============================================================================

print("\n🏗️  Building GRU model...")

def build_gru_model(vocab_size, embedding_dim=64, gru_units=128, dropout_rate=0.3):
    """
    Build GRU sentiment classifier

    Args:
        vocab_size: Size of vocabulary
        embedding_dim: Dimension of word embeddings
        gru_units: Number of GRU units
        dropout_rate: Dropout rate for regularization

    Returns:
        Compiled Keras model
    """
    model = keras.Sequential([
        # Input layer
        layers.Input(shape=(1,), dtype=tf.string),

        # Text vectorization
        vectorizer,

        # Embedding layer
        layers.Embedding(
            input_dim=vocab_size,
            output_dim=embedding_dim,
            mask_zero=True,  # Mask padding
            name='embedding'
        ),

        # Dropout for regularization
        layers.Dropout(dropout_rate),

        # GRU layer
        layers.GRU(
            units=gru_units,
            return_sequences=False,  # Only return last output
            name='gru'
        ),

        # Dropout
        layers.Dropout(dropout_rate),

        # Dense output layer
        layers.Dense(64, activation='relu', name='dense1'),
        layers.Dropout(dropout_rate),

        # Final classification layer
        layers.Dense(1, activation='sigmoid', name='output')
    ], name='GRU_Sentiment_Classifier')

    return model

# Create model
model = build_gru_model(
    vocab_size=vocab_size,
    embedding_dim=64,
    gru_units=128,
    dropout_rate=0.3
)

# Display model architecture
print("\nModel Architecture:")
model.summary()

# ============================================================================
# 4. COMPILE MODEL
# ============================================================================

print("\n⚙️  Compiling model...")

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.001),
    loss='binary_crossentropy',
    metrics=['accuracy',
             keras.metrics.Precision(name='precision'),
             keras.metrics.Recall(name='recall')]
)

print("✓ Model compiled")

# ============================================================================
# 5. TRAIN MODEL
# ============================================================================

print("\n🚀 Training model...")

# Callbacks
early_stopping = keras.callbacks.EarlyStopping(
    monitor='val_loss',
    patience=5,
    restore_best_weights=True,
    verbose=1
)

reduce_lr = keras.callbacks.ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,
    patience=3,
    min_lr=1e-6,
    verbose=1
)

# Train
history = model.fit(
    np.array(train_texts),
    np.array(train_labels),
    validation_data=(np.array(val_texts), np.array(val_labels)),
    epochs=20,
    batch_size=32,
    callbacks=[early_stopping, reduce_lr],
    verbose=1
)

print("\n✓ Training complete!")

# ============================================================================
# 6. VISUALIZE TRAINING
# ============================================================================

print("\n📈 Visualizing training history...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Loss
axes[0, 0].plot(history.history['loss'], marker='o', label='Training Loss')
axes[0, 0].plot(history.history['val_loss'], marker='s', label='Validation Loss')
axes[0, 0].set_title('Model Loss', fontsize=14, fontweight='bold')
axes[0, 0].set_xlabel('Epoch')
axes[0, 0].set_ylabel('Loss')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Accuracy
axes[0, 1].plot(history.history['accuracy'], marker='o', label='Training Accuracy')
axes[0, 1].plot(history.history['val_accuracy'], marker='s', label='Validation Accuracy')
axes[0, 1].set_title('Model Accuracy', fontsize=14, fontweight='bold')
axes[0, 1].set_xlabel('Epoch')
axes[0, 1].set_ylabel('Accuracy')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Precision
axes[1, 0].plot(history.history['precision'], marker='o', label='Training Precision')
axes[1, 0].plot(history.history['val_precision'], marker='s', label='Validation Precision')
axes[1, 0].set_title('Model Precision', fontsize=14, fontweight='bold')
axes[1, 0].set_xlabel('Epoch')
axes[1, 0].set_ylabel('Precision')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# Recall
axes[1, 1].plot(history.history['recall'], marker='o', label='Training Recall')
axes[1, 1].plot(history.history['val_recall'], marker='s', label='Validation Recall')
axes[1, 1].set_title('Model Recall', fontsize=14, fontweight='bold')
axes[1, 1].set_xlabel('Epoch')
axes[1, 1].set_ylabel('Recall')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('gru_training_history.png', dpi=150, bbox_inches='tight')
plt.show()

print("✓ Plots saved as 'gru_training_history.png'")

# ============================================================================
# 7. EVALUATE ON TEST SET
# ============================================================================

print("\n🎯 Evaluating on test set...")

test_loss, test_acc, test_precision, test_recall = model.evaluate(
    np.array(test_texts),
    np.array(test_labels),
    verbose=1
)

# Compute F1 score
f1_score = 2 * (test_precision * test_recall) / (test_precision + test_recall)

print(f"\n{'='*70}")
print("TEST SET RESULTS")
print(f"{'='*70}")
print(f"Loss:      {test_loss:.4f}")
print(f"Accuracy:  {test_acc:.4f}")
print(f"Precision: {test_precision:.4f}")
print(f"Recall:    {test_recall:.4f}")
print(f"F1 Score:  {f1_score:.4f}")
print(f"{'='*70}")

# ============================================================================
# 8. TEST WITH NEW REVIEWS
# ============================================================================

print("\n🧪 Testing with new reviews...")

new_reviews = [
    "This movie was absolutely amazing and I loved it",
    "Terrible film, complete waste of my time",
    "Outstanding performance by the actors, highly recommend",
    "Boring and predictable, very disappointing",
    "A masterpiece of cinema, simply brilliant"
]

predictions = model.predict(np.array(new_reviews))

print(f"\n{'='*70}")
print("PREDICTIONS ON NEW REVIEWS")
print(f"{'='*70}")

for i, (review, pred) in enumerate(zip(new_reviews, predictions), 1):
    sentiment = "POSITIVE ✓" if pred[0] > 0.5 else "NEGATIVE ✗"
    confidence = pred[0] if pred[0] > 0.5 else (1 - pred[0])

    print(f"\n{i}. Review: '{review}'")
    print(f"   Prediction: {sentiment}")
    print(f"   Confidence: {confidence:.2%}")
    print(f"   Score: {pred[0]:.4f}")

print(f"\n{'='*70}")

# ============================================================================
# 9. INTERACTIVE PREDICTION FUNCTION
# ============================================================================

def predict_sentiment(review_text, model):
    """
    Predict sentiment of a review

    Args:
        review_text: String review
        model: Trained model

    Returns:
        dict with sentiment and confidence
    """
    prediction = model.predict([review_text], verbose=0)[0][0]

    if prediction > 0.5:
        sentiment = "POSITIVE"
        confidence = prediction
    else:
        sentiment = "NEGATIVE"
        confidence = 1 - prediction

    return {
        'sentiment': sentiment,
        'confidence': confidence,
        'score': prediction
    }

# Example usage
print("\n💬 Interactive prediction example:")
example_review = "The cinematography was breathtaking and the story was captivating"
result = predict_sentiment(example_review, model)

print(f"\nReview: '{example_review}'")
print(f"Sentiment: {result['sentiment']}")
print(f"Confidence: {result['confidence']:.2%}")

# ============================================================================
# 10. INSPECT GRU INTERNALS
# ============================================================================

print("\n🔍 Inspecting GRU internals...")

# Get the GRU layer
gru_layer = model.get_layer('gru')

# Get weights
weights = gru_layer.get_weights()
print(f"\nGRU layer has {len(weights)} weight matrices:")
print(f"1. Kernel (input weights): shape {weights[0].shape}")
print(f"2. Recurrent kernel (hidden weights): shape {weights[1].shape}")
print(f"3. Bias: shape {weights[2].shape}")

# The kernel contains weights for all three gates: [W_z, W_r, W_h]
# Shape: (embedding_dim, 3 * gru_units)
print(f"\nKernel is split into 3 parts (update, reset, candidate):")
print(f"  Each part has shape: ({weights[0].shape[0]}, {weights[0].shape[1] // 3})")

# ============================================================================
# 11. SAVE MODEL
# ============================================================================

print("\n💾 Saving model...")

model.save('gru_sentiment_model.keras')
print("✓ Model saved as 'gru_sentiment_model.keras'")

# ============================================================================
# SUMMARY
# ============================================================================

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"✓ Dataset: {len(texts)} movie reviews")
print(f"✓ Vocabulary: {vocab_size} words")
print(f"✓ Model: GRU with {gru_layer.units} units")
print(f"✓ Training: {len(history.history['loss'])} epochs")
print(f"✓ Test Accuracy: {test_acc:.2%}")
print(f"✓ Test F1 Score: {f1_score:.4f}")
print(f"{'='*70}")

print("\n🎉 Complete GRU sentiment analysis pipeline finished!")
```

---

<a name="6-tips"></a>

## 6. Practical Insights and Tips

### When to Use GRU vs Simple RNN

**Use Simple RNN when:**

- ✓ Sequences are short (< 10 time steps)
- ✓ Long-term dependencies aren't critical
- ✓ You need faster training
- ✓ You want simpler model for debugging

**Use GRU when:**

- ✓ Sequences are long (> 10 time steps)
- ✓ Long-term dependencies matter (e.g., "France" ... "French")
- ✓ You have vanishing gradient problems
- ✓ You need better performance (worth the extra computation)

### Hyperparameter Tuning Tips

**GRU Units**:

- Start with 128 or 256
- More units = more capacity, but slower and may overfit
- Less units = faster, but may underfit

**Embedding Dimension**:

- Typical: 50-300
- Small vocab (< 10K): 50-100
- Large vocab (> 50K): 200-300

**Dropout**:

- Start with 0.3-0.5
- Too high (> 0.7): May prevent learning
- Too low (< 0.2): May overfit

**Learning Rate**:

- Start with 0.001 (Adam optimizer)
- Reduce if loss oscillates
- Increase if learning too slow

### Common Pitfalls and Solutions

**1. Gradient Exploding**:

```python
# Solution: Gradient clipping
optimizer = keras.optimizers.Adam(clipnorm=1.0)
```

**2. Overfitting**:

```python
# Solutions:
- Add dropout layers
- Reduce model size
- Get more data
- Add L2 regularization
```

**3. Slow Training**:

```python
# Solutions:
- Reduce sequence length
- Use smaller batches
- Reduce GRU units
- Use GPU if available
```

**4. Poor Performance**:

```python
# Check:
- Is data preprocessed correctly?
- Is vocabulary size appropriate?
- Are sequences padded correctly?
- Is learning rate too high/low?
```

### Comparing with LSTM

**GRU** (what we learned):

- 2 gates (update, reset)
- Simpler, faster
- Fewer parameters
- Usually similar performance to LSTM

**LSTM** (Week 2):

- 3 gates (input, forget, output)
- More complex
- More parameters
- Can be better for very long sequences

**Rule of thumb**: Start with GRU, switch to LSTM only if you need the extra complexity!

---

## Conclusion

You've now learned:

✅ **Why** we need RNNs (sequential data, memory, parameter sharing)  
✅ **How** RNNs work mathematically (complete forward pass calculations)  
✅ **What** the vanishing gradient problem is and why it matters  
✅ **How** GRUs solve it (gates, selective memory, gradient highways)  
✅ **Implementing** GRUs from scratch and with TensorFlow  
✅ **Training** real models and understanding hyperparameters

**Next Steps**:

1. Try the code examples yourself
2. Experiment with different hyperparameters
3. Apply to your own sequential data
4. Move on to LSTMs (Week 2) to see the differences
5. Explore attention mechanisms (Course 4)

**Keep practicing and happy learning!** 🚀
