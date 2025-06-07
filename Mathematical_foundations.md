# Mathematical Foundations for Deep Learning - Detailed Notes

## Table of Contents

1. [Linear Algebra Foundations](#linear-algebra-foundations)
2. [Matrix Operations](#matrix-operations)
3. [Vector Operations](#vector-operations)
4. [Calculus for Neural Networks](#calculus-for-neural-networks)
5. [Probability and Statistics](#probability-and-statistics)
6. [Optimization](#optimization)
7. [Code Examples](#code-examples)

---

## Linear Algebra Foundations

### What is a Matrix?

A matrix is a rectangular array of numbers arranged in rows and columns. For neural networks, matrices are fundamental for:

- Storing weights and biases
- Representing data batches
- Performing transformations

**Matrix Notation:**

- Matrix A with m rows and n columns: A ∈ ℝᵐˣⁿ
- Element in row i, column j: A[i,j] or Aᵢⱼ
- Matrix dimensions: (m × n) where m = rows, n = columns

**Example:**

```
A = [1  2  3]  ← 2×3 matrix (2 rows, 3 columns)
    [4  5  6]

A[1,2] = 2 (row 1, column 2)
A[2,3] = 6 (row 2, column 3)
```

### Special Types of Matrices

#### 1. **Square Matrix**

- Same number of rows and columns (n × n)
- Example: 3×3 matrix

```
[1  2  3]
[4  5  6]
[7  8  9]
```

#### 2. **Identity Matrix (I)**

- Square matrix with 1s on diagonal, 0s elsewhere
- Multiplying any matrix by I gives the original matrix

```
I₃ = [1  0  0]
     [0  1  0]
     [0  0  1]
```

#### 3. **Zero Matrix**

- All elements are zero

```
O = [0  0  0]
    [0  0  0]
```

#### 4. **Transpose Matrix (Aᵀ)**

- Rows become columns, columns become rows

```
If A = [1  2  3]  then Aᵀ = [1  4]
       [4  5  6]            [2  5]
                             [3  6]
```

---

## Matrix Operations

### 1. Matrix Addition and Subtraction

**Rule:** Matrices must have the same dimensions

**Step-by-step example:**

```
A = [1  2]    B = [5  6]
    [3  4]        [7  8]

A + B = [1+5  2+6] = [6   8]
        [3+7  4+8]   [10  12]

A - B = [1-5  2-6] = [-4  -4]
        [3-7  4-8]   [-4  -4]
```

### 2. Scalar Multiplication

**Rule:** Multiply every element by the scalar

**Step-by-step example:**

```
A = [1  2]    k = 3
    [3  4]

k × A = [3×1  3×2] = [3   6]
        [3×3  3×4]   [9  12]
```

### 3. **Matrix Multiplication (Most Important for Neural Networks)**

**Rule:** For A(m×n) × B(n×p), the result is C(m×p)

- Number of columns in A must equal number of rows in B
- Element C[i,j] = sum of (A[i,k] × B[k,j]) for all k

**Detailed Step-by-Step Example:**

```
A = [1  2  3]  (2×3)    B = [7   8 ]  (3×2)
    [4  5  6]               [9  10]
                            [11 12]

Result C will be (2×2)
```

**Calculating each element:**

**C[1,1]:**

- Take row 1 of A: [1, 2, 3]
- Take column 1 of B: [7, 9, 11]
- C[1,1] = (1×7) + (2×9) + (3×11) = 7 + 18 + 33 = **58**

**C[1,2]:**

- Take row 1 of A: [1, 2, 3]
- Take column 2 of B: [8, 10, 12]
- C[1,2] = (1×8) + (2×10) + (3×12) = 8 + 20 + 36 = **64**

**C[2,1]:**

- Take row 2 of A: [4, 5, 6]
- Take column 1 of B: [7, 9, 11]
- C[2,1] = (4×7) + (5×9) + (6×11) = 28 + 45 + 66 = **139**

**C[2,2]:**

- Take row 2 of A: [4, 5, 6]
- Take column 2 of B: [8, 10, 12]
- C[2,2] = (4×8) + (5×10) + (6×12) = 32 + 50 + 72 = **154**

**Final Result:**

```
C = [58   64 ]
    [139  154]
```

### 4. Element-wise Multiplication (Hadamard Product)

**Rule:** Matrices must have same dimensions, multiply corresponding elements

```
A = [1  2]    B = [5  6]
    [3  4]        [7  8]

A ⊙ B = [1×5  2×6] = [5   12]
        [3×7  4×8]   [21  32]
```

---

## Vector Operations

### Vectors in Neural Networks

Vectors are special matrices with either 1 row or 1 column:

- **Row vector:** 1×n matrix (horizontal)
- **Column vector:** n×1 matrix (vertical)

### 1. Dot Product (Scalar Product)

For vectors u = [u₁, u₂, ..., uₙ] and v = [v₁, v₂, ..., vₙ]:

**u · v = u₁v₁ + u₂v₂ + ... + uₙvₙ**

**Step-by-step example:**

```
u = [1, 2, 3]
v = [4, 5, 6]

u · v = (1×4) + (2×5) + (3×6) = 4 + 10 + 18 = 32
```

### 2. Vector Magnitude (Norm)

**||u|| = √(u₁² + u₂² + ... + uₙ²)**

**Example:**

```
u = [3, 4]
||u|| = √(3² + 4²) = √(9 + 16) = √25 = 5
```

---

## Calculus for Neural Networks

### 1. Derivatives

**Definition:** Rate of change of a function

**Basic Rules:**

- d/dx(c) = 0 (constant)
- d/dx(x) = 1
- d/dx(xⁿ) = nxⁿ⁻¹
- d/dx(eˣ) = eˣ
- d/dx(ln(x)) = 1/x

### 2. Chain Rule (Critical for Backpropagation)

**If y = f(g(x)), then dy/dx = f'(g(x)) × g'(x)**

**Example:**

```
y = (2x + 1)³

Let u = 2x + 1, then y = u³
dy/du = 3u² = 3(2x + 1)²
du/dx = 2

dy/dx = dy/du × du/dx = 3(2x + 1)² × 2 = 6(2x + 1)²
```

### 3. Partial Derivatives

**For functions with multiple variables: ∂f/∂x**

**Example:**

```
f(x,y) = x² + 3xy + y²

∂f/∂x = 2x + 3y  (treat y as constant)
∂f/∂y = 3x + 2y  (treat x as constant)
```

### 4. Sigmoid Function and Its Derivative

**Sigmoid:** σ(x) = 1/(1 + e⁻ˣ)

**Derivative:** σ'(x) = σ(x)(1 - σ(x))

**Step-by-step derivation:**

```
σ(x) = 1/(1 + e⁻ˣ) = (1 + e⁻ˣ)⁻¹

Using chain rule:
σ'(x) = -1(1 + e⁻ˣ)⁻² × (-e⁻ˣ)
      = e⁻ˣ/(1 + e⁻ˣ)²
      = e⁻ˣ/((1 + e⁻ˣ)²)
      = (1/(1 + e⁻ˣ)) × (e⁻ˣ/(1 + e⁻ˣ))
      = σ(x) × (1 - σ(x))
```

---

## Probability and Statistics

### 1. Basic Probability

- **P(A):** Probability of event A (0 ≤ P(A) ≤ 1)
- **P(A|B):** Conditional probability of A given B

### 2. Bayes' Theorem

**P(A|B) = P(B|A) × P(A) / P(B)**

### 3. Common Distributions

#### Normal Distribution

**PDF:** f(x) = (1/√(2πσ²)) × e^(-(x-μ)²/(2σ²))

- μ: mean
- σ²: variance

---

## Optimization

### 1. Gradient Descent

**Goal:** Minimize cost function J(θ)

**Update rule:** θ = θ - α∇J(θ)

- α: learning rate
- ∇J(θ): gradient of cost function

**Step-by-step example:**

```
Cost function: J(θ) = (θ - 3)²
Gradient: dJ/dθ = 2(θ - 3)

Starting with θ₀ = 0, α = 0.1:

Iteration 1:
gradient = 2(0 - 3) = -6
θ₁ = 0 - 0.1(-6) = 0.6

Iteration 2:
gradient = 2(0.6 - 3) = -4.8
θ₂ = 0.6 - 0.1(-4.8) = 1.08

Continue until convergence...
```

---

## Code Examples

### Matrix Operations in Python

```python
import numpy as np

# Create matrices
A = np.array([[1, 2, 3],
              [4, 5, 6]])
B = np.array([[7, 8],
              [9, 10],
              [11, 12]])

print("Matrix A (2x3):")
print(A)
print("Shape:", A.shape)

print("\nMatrix B (3x2):")
print(B)
print("Shape:", B.shape)

# Matrix multiplication
C = np.dot(A, B)  # or A @ B
print("\nMatrix multiplication A × B:")
print(C)
print("Shape:", C.shape)

# Element-wise operations
D = np.array([[1, 2],
              [3, 4]])
E = np.array([[5, 6],
              [7, 8]])

print("\nElement-wise multiplication:")
print(D * E)  # Hadamard product

print("\nMatrix addition:")
print(D + E)
```

### Vectorization Example

```python
import numpy as np
import time

# Non-vectorized approach (slow)
def dot_product_loop(x, y):
    result = 0
    for i in range(len(x)):
        result += x[i] * y[i]
    return result

# Vectorized approach (fast)
def dot_product_vectorized(x, y):
    return np.dot(x, y)

# Test with large vectors
x = np.random.rand(1000)
y = np.random.rand(1000)

# Time the loop version
start = time.time()
result1 = dot_product_loop(x, y)
time1 = time.time() - start

# Time the vectorized version
start = time.time()
result2 = dot_product_vectorized(x, y)
time2 = time.time() - start

print(f"Loop result: {result1:.6f}")
print(f"Loop time: {time1*1000:.2f} ms")
print(f"Vectorized result: {result2:.6f}")
print(f"Vectorized time: {time2*1000:.2f} ms")
print(f"Speedup: {time1/time2:.1f}x")
```

### Neural Network Forward Pass Example

```python
import numpy as np

def sigmoid(x):
    """Sigmoid activation function"""
    return 1 / (1 + np.exp(-x))

def forward_pass(X, W1, b1, W2, b2):
    """
    Forward pass through a 2-layer neural network

    Parameters:
    X: input data (n_features, m_examples)
    W1: weights layer 1 (n_hidden, n_features)
    b1: bias layer 1 (n_hidden, 1)
    W2: weights layer 2 (n_output, n_hidden)
    b2: bias layer 2 (n_output, 1)
    """

    # Layer 1
    Z1 = np.dot(W1, X) + b1  # Linear transformation
    A1 = sigmoid(Z1)          # Activation

    # Layer 2
    Z2 = np.dot(W2, A1) + b2  # Linear transformation
    A2 = sigmoid(Z2)           # Activation (output)

    return A2

# Example usage
np.random.seed(42)
X = np.random.randn(3, 4)  # 3 features, 4 examples
W1 = np.random.randn(2, 3)  # 2 hidden units, 3 input features
b1 = np.zeros((2, 1))       # 2 hidden units
W2 = np.random.randn(1, 2)  # 1 output, 2 hidden units
b2 = np.zeros((1, 1))       # 1 output

output = forward_pass(X, W1, b1, W2, b2)
print("Network output:")
print(output)
```

---

## Key Formulas Summary

### Matrix Dimensions for Neural Networks

- Input: X ∈ ℝⁿˣᵐ (n features, m examples)
- Weights: W⁽ˡ⁾ ∈ ℝⁿ⁽ˡ⁾ˣⁿ⁽ˡ⁻¹⁾ (layer l neurons × layer l-1 neurons)
- Bias: b⁽ˡ⁾ ∈ ℝⁿ⁽ˡ⁾ˣ¹ (layer l neurons × 1)
- Activation: A⁽ˡ⁾ ∈ ℝⁿ⁽ˡ⁾ˣᵐ (layer l neurons × m examples)

### Forward Propagation

Z⁽ˡ⁾ = W⁽ˡ⁾A⁽ˡ⁻¹⁾ + b⁽ˡ⁾
A⁽ˡ⁾ = g⁽ˡ⁾(Z⁽ˡ⁾)

### Backpropagation

dZ⁽ˡ⁾ = dA⁽ˡ⁾ ⊙ g'⁽ˡ⁾(Z⁽ˡ⁾)
dW⁽ˡ⁾ = (1/m) × dZ⁽ˡ⁾ × (A⁽ˡ⁻¹⁾)ᵀ
db⁽ˡ⁾ = (1/m) × sum(dZ⁽ˡ⁾, axis=1, keepdims=True)
dA⁽ˡ⁻¹⁾ = (W⁽ˡ⁾)ᵀ × dZ⁽ˡ⁾

---

## Practice Problems

### Problem 1: Matrix Multiplication

Calculate the result of:

```
A = [2  1]    B = [1  0  2]
    [0  3]        [3  1  1]
```

**Solution:**
A is 2×2, B is 2×3, so result will be 2×3

C[1,1] = (2×1) + (1×3) = 5
C[1,2] = (2×0) + (1×1) = 1  
C[1,3] = (2×2) + (1×1) = 5
C[2,1] = (0×1) + (3×3) = 9
C[2,2] = (0×0) + (3×1) = 3
C[2,3] = (0×2) + (3×1) = 3

Result: C = [5 1 5]
[9 3 3]

### Problem 2: Derivative Calculation

Find the derivative of f(x) = 3x² + 2x + 1

**Solution:**
f'(x) = d/dx(3x²) + d/dx(2x) + d/dx(1)
= 3(2x) + 2(1) + 0
= 6x + 2

---

This comprehensive guide covers the essential mathematics needed for understanding and implementing neural networks. Focus on matrix operations and vectorization as these are used constantly in deep learning implementations.
