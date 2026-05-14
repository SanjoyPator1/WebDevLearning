# 1. Configuration and Synthetic Data

## Big picture first (one sentence)

> We are building a tiny neural network whose job is to answer:
> **“Given what the decoder wants right now, how relevant is each encoder word?”**

Everything in this code exists **only** to compute those relevance scores.

---

## Step 1: What problem are we solving here?

At decoder step ( i ):

* We already have a decoder hidden state
  → `decoder_state` = ( $s_{i-1}$ )
* We also have **all** encoder hidden states
  → `encoder_states` = ( h_1, h_2, ..., h_{T_x} )

We want **one score per encoder word**:

[
e_{i,1}, e_{i,2}, \dots, e_{i,T_x}
]

That’s it.
Everything else is machinery to make that happen.

---

## Step 2: Why these dimensions exist

### 1️⃣ `hidden_size = 16`

This means:

* Each encoder hidden state ( h_j ) is a **16-dimensional vector**
* Each decoder hidden state ( s_{i-1} ) is also **16-dimensional**

So:

[
h_j \in \mathbb{R}^{16}, \quad s_{i-1} \in \mathbb{R}^{16}
]

Why same size?
Because they come from similar RNN/LSTM layers.

---

### 2️⃣ `input_length = 5`

This means:

* The input sentence has **5 words**
* So we have **5 encoder states**

[
\text{encoder_states} =
\begin{bmatrix}
h_1 \
h_2 \
h_3 \
h_4 \
h_5
\end{bmatrix}
\quad \Rightarrow \quad (5 \times 16)
]

Each row = one word’s representation.

---

### 3️⃣ `attention_size = 10`

This is **very important conceptually**.

This means:

> “Inside the attention mechanism, we will project things into a 10-dimensional ‘attention space’ before scoring them.”

This has **nothing** to do with vocabulary size or sequence length.

It’s just the **hidden size of a small neural network**.

---

## Step 3: What are `encoder_states` and `decoder_state` really?

### Encoder states

```python
encoder_states.shape = (5, 16)
```

Think of it as:

[
\begin{bmatrix}
h_1^{(1)} & h_1^{(2)} & \dots & h_1^{(16)} \
h_2^{(1)} & h_2^{(2)} & \dots & h_2^{(16)} \
\vdots    &           &       & \vdots \
h_5^{(1)} & h_5^{(2)} & \dots & h_5^{(16)}
\end{bmatrix}
]

Each row = **one word’s meaning + context**.

---

### Decoder state

```python
decoder_state.shape = (1, 16)
```

This is:

[
s_{i-1} =
\begin{bmatrix}
s^{(1)} & s^{(2)} & \dots & s^{(16)}
\end{bmatrix}
]

This vector encodes:

> “What I have generated so far and what I need next.”

---

## Step 4: Why do we concatenate encoder and decoder states?

This is the key idea of **Bahdanau attention**.

For **each encoder word**, we want to evaluate:

[
\text{score}(s_{i-1}, h_j)
]

Neural networks want **one input vector**, so we do this:

[
\text{input}*j = [, h_j , ; , s*{i-1} ,]
]

Each concatenated vector has size:

[
16 + 16 = 32
]

---

### What this looks like in practice

We repeat the decoder state 5 times:

[
\begin{bmatrix}
h_1 & s_{i-1} \
h_2 & s_{i-1} \
h_3 & s_{i-1} \
h_4 & s_{i-1} \
h_5 & s_{i-1}
\end{bmatrix}
\quad \Rightarrow \quad (5 \times 32)
]

That’s why:

```python
layer_1.shape = (32, 10)
```

---

## Step 5: What does `layer_1` actually do?

```python
layer_1 = np.random.randn(32, 10)
```

This is a **linear transformation**:

[
(5 \times 32) \cdot (32 \times 10) \rightarrow (5 \times 10)
]

Interpretation:

> “For each encoder word, combine encoder meaning + decoder intent into a 10-dimensional attention representation.”

Then we apply:

[
\tanh(\cdot)
]

Why tanh?

* Keeps values bounded
* Adds non-linearity
* Allows richer matching than dot product

---

## Step 6: What does `layer_2` do?

```python
layer_2 = np.random.randn(10, 1)
```

This compresses:

[
(5 \times 10) \cdot (10 \times 1) \rightarrow (5 \times 1)
]

So for each encoder word, we get **one scalar**:

[
\begin{bmatrix}
e_{i,1} \
e_{i,2} \
e_{i,3} \
e_{i,4} \
e_{i,5}
\end{bmatrix}
]

These are **alignment scores**.

Important:

* These are **unnormalized**
* Bigger = more relevant
* Can be negative

---

## Step 7: Tiny numeric example (very small)

Let’s shrink everything:

* `hidden_size = 2`
* `attention_size = 3`
* `input_length = 2`

### Encoder states

[
\begin{bmatrix}
h_1 = [1, 0] \
h_2 = [0, 1]
\end{bmatrix}
]

### Decoder state

[
s_{i-1} = [1, 1]
]

### Concatenation

[
\begin{bmatrix}
[1, 0, 1, 1] \
[0, 1, 1, 1]
\end{bmatrix}
]

### First layer → tanh

[
(2 \times 4) \cdot (4 \times 3) \rightarrow (2 \times 3)
]

### Second layer → scores

[
\begin{bmatrix}
2.1 \
5.7
\end{bmatrix}
]

Interpretation:

> Encoder word 2 matches the decoder’s need much more strongly.

---

## Step 8: What happens next (important context)

These scores **are not the end**.

Next steps (not in this code yet):

1. Apply **softmax** → attention weights ( \alpha_{i,j} )
2. Compute **context vector**:
   [
   c_i = \sum_j \alpha_{i,j} h_j
   ]
3. Use ( c_i ) to predict the next word

---

## Final intuition (lock this in)

* `encoder_states` → **What was said**
* `decoder_state` → **What I need now**
* `layer_1` → **How should I compare them?**
* `layer_2` → **How strong is the match?**
* Output → **One score per input word**

