# Course 2 Week 1: Practical Aspects of Deep Learning

## Jupyter Notebook Companion

This notebook provides practical implementations and code examples for the concepts covered in Course 2 Week 1 notes.

---

## 1. Train/Dev/Test Sets

### Data Splitting Implementation

**What this does:** Implements modern data splitting strategies for large datasets with proper distribution matching.

**Key Formula:** For large datasets (>1M examples):

- Training: 98%
- Dev: 1%
- Test: 1%

```python
import numpy as np
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

def split_data(X, y, train_ratio=0.98, dev_ratio=0.01, test_ratio=0.01, random_state=42):
    """
    Split data into train/dev/test sets using modern ratios

    Args:
        X: Features array
        y: Labels array
        train_ratio: Proportion for training (default 0.98)
        dev_ratio: Proportion for development (default 0.01)
        test_ratio: Proportion for testing (default 0.01)
        random_state: Random seed for reproducibility

    Returns:
        X_train, X_dev, X_test, y_train, y_dev, y_test
    """
    assert abs(train_ratio + dev_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1"

    # First split: separate training from (dev + test)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=(dev_ratio + test_ratio), random_state=random_state, stratify=y
    )

    # Second split: separate dev from test
    relative_test_size = test_ratio / (dev_ratio + test_ratio)
    X_dev, X_test, y_dev, y_test = train_test_split(
        X_temp, y_temp, test_size=relative_test_size, random_state=random_state, stratify=y_temp
    )

    print(f"Dataset split completed:")
    print(f"Training set: {len(X_train)} examples ({len(X_train)/len(X)*100:.1f}%)")
    print(f"Dev set: {len(X_dev)} examples ({len(X_dev)/len(X)*100:.1f}%)")
    print(f"Test set: {len(X_test)} examples ({len(X_test)/len(X)*100:.1f}%)")

    return X_train, X_dev, X_test, y_train, y_dev, y_test

# Example usage with synthetic data
np.random.seed(42)
X = np.random.randn(10000, 5)  # 10,000 examples, 5 features
y = np.random.randint(0, 2, 10000)  # Binary classification

X_train, X_dev, X_test, y_train, y_dev, y_test = split_data(X, y)
```

---

## 2. Bias vs Variance Analysis

### Diagnostic Functions

**What this does:** Implements bias/variance diagnostic tools to determine if your model has high bias (underfitting) or high variance (overfitting).

**Key Insights:**

- High Bias: $J_{train} >> \text{optimal error}$
- High Variance: $J_{dev} >> J_{train}$

```python
def analyze_bias_variance(train_error, dev_error, human_error=0.0):
    """
    Analyze bias and variance of a model

    Args:
        train_error: Training set error (%)
        dev_error: Development set error (%)
        human_error: Human-level performance baseline (%)

    Returns:
        Analysis and recommendations
    """
    bias = train_error - human_error
    variance = dev_error - train_error

    print(f"=== Bias/Variance Analysis ===")
    print(f"Human error: {human_error:.1f}%")
    print(f"Training error: {train_error:.1f}%")
    print(f"Dev error: {dev_error:.1f}%")
    print(f"Bias (Train - Human): {bias:.1f}%")
    print(f"Variance (Dev - Train): {variance:.1f}%")
    print()

    # Diagnosis
    high_bias = bias > 2.0  # Threshold can be adjusted
    high_variance = variance > 2.0

    if high_bias and high_variance:
        diagnosis = "High Bias + High Variance"
        recommendations = [
            "Use bigger network AND more data",
            "Try different architecture",
            "More complex models with regularization"
        ]
    elif high_bias:
        diagnosis = "High Bias (Underfitting)"
        recommendations = [
            "Use bigger network (more layers/units)",
            "Train longer",
            "Try different architecture"
        ]
    elif high_variance:
        diagnosis = "High Variance (Overfitting)"
        recommendations = [
            "Get more training data",
            "Add regularization (L2, dropout)",
            "Simpler architecture"
        ]
    else:
        diagnosis = "Good Model"
        recommendations = ["Model is performing well!", "Consider deployment"]

    print(f"Diagnosis: {diagnosis}")
    print("Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

    return diagnosis, recommendations

# Example usage - Test different scenarios
print("Scenario 1: High Bias (Underfitting)")
analyze_bias_variance(train_error=15.0, dev_error=16.0, human_error=0.5)

print("\nScenario 2: High Variance (Overfitting)")
analyze_bias_variance(train_error=1.0, dev_error=11.0, human_error=0.5)

print("\nScenario 3: Good Model")
analyze_bias_variance(train_error=0.8, dev_error=1.2, human_error=0.5)

print("\nScenario 4: High Bias + High Variance")
analyze_bias_variance(train_error=15.0, dev_error=30.0, human_error=0.5)
```

---

## 3. L2 Regularization Implementation

### Complete L2 Regularization

**What this does:** Implements L2 regularization for neural networks, including cost function modification and gradient updates.

**Mathematical Foundation:**
$$J_{regularized} = J_{original} + \frac{\lambda}{2m}\sum_{l=1}^{L}||W^{[l]}||_F^2$$

**Weight Update with Decay:**
$$W^{[l]} := \left(1 - \frac{\alpha\lambda}{m}\right)W^{[l]} - \alpha \cdot \frac{\partial J}{\partial W^{[l]}}$$

```python
def compute_cost_with_regularization(A3, Y, parameters, lambd):
    """
    Compute cost with L2 regularization

    Args:
        A3: Output of forward propagation (predictions)
        Y: True labels
        parameters: Dictionary containing weights W1, W2, W3, etc.
        lambd: Regularization hyperparameter

    Returns:
        regularized_cost: Cost including L2 penalty
    """
    m = Y.shape[1]

    # Cross-entropy cost
    cross_entropy_cost = -(1/m) * np.sum(Y * np.log(A3) + (1-Y) * np.log(1-A3))

    # L2 regularization cost
    L2_regularization_cost = 0
    num_layers = len(parameters) // 2

    for l in range(1, num_layers + 1):
        L2_regularization_cost += np.sum(np.square(parameters[f'W{l}']))

    L2_regularization_cost = (lambd / (2 * m)) * L2_regularization_cost

    regularized_cost = cross_entropy_cost + L2_regularization_cost

    return regularized_cost

def backward_propagation_with_regularization(X, Y, cache, lambd):
    """
    Implement backward propagation with L2 regularization

    Args:
        X: Input data
        Y: True labels
        cache: Cache from forward propagation
        lambd: Regularization parameter

    Returns:
        gradients: Dictionary containing gradients with regularization
    """
    m = X.shape[1]
    (Z1, A1, W1, b1, Z2, A2, W2, b2, Z3, A3, W3, b3) = cache

    # Backward propagation with regularization
    dZ3 = A3 - Y
    dW3 = (1/m) * np.dot(dZ3, A2.T) + (lambd/m) * W3  # Add regularization term
    db3 = (1/m) * np.sum(dZ3, axis=1, keepdims=True)

    dA2 = np.dot(W3.T, dZ3)
    dZ2 = np.multiply(dA2, np.int64(A2 > 0))  # ReLU derivative
    dW2 = (1/m) * np.dot(dZ2, A1.T) + (lambd/m) * W2  # Add regularization term
    db2 = (1/m) * np.sum(dZ2, axis=1, keepdims=True)

    dA1 = np.dot(W2.T, dZ2)
    dZ1 = np.multiply(dA1, np.int64(A1 > 0))  # ReLU derivative
    dW1 = (1/m) * np.dot(dZ1, X.T) + (lambd/m) * W1   # Add regularization term
    db1 = (1/m) * np.sum(dZ1, axis=1, keepdims=True)

    gradients = {
        "dZ3": dZ3, "dW3": dW3, "db3": db3,
        "dA2": dA2, "dZ2": dZ2, "dW2": dW2, "db2": db2,
        "dA1": dA1, "dZ1": dZ1, "dW1": dW1, "db1": db1
    }

    return gradients

# Example with synthetic data
def demonstrate_l2_regularization():
    """Demonstrate L2 regularization effect"""
    # Create sample parameters
    np.random.seed(42)
    parameters = {
        'W1': np.random.randn(4, 3) * 0.5,
        'b1': np.zeros((4, 1)),
        'W2': np.random.randn(3, 4) * 0.5,
        'b2': np.zeros((3, 1)),
        'W3': np.random.randn(1, 3) * 0.5,
        'b3': np.zeros((1, 1))
    }

    # Sample predictions and labels
    A3 = np.array([[0.8, 0.2, 0.9, 0.1]])  # Predictions
    Y = np.array([[1, 0, 1, 0]])            # True labels

    # Compare costs with different lambda values
    lambdas = [0, 0.01, 0.1, 1.0]

    print("L2 Regularization Effect:")
    print("Lambda\tCost")
    print("-" * 15)

    for lambd in lambdas:
        cost = compute_cost_with_regularization(A3, Y, parameters, lambd)
        print(f"{lambd}\t{cost:.4f}")

demonstrate_l2_regularization()
```

---

## 4. Dropout Regularization Implementation

### Inverted Dropout Implementation

**What this does:** Implements inverted dropout regularization that randomly eliminates neurons during training while scaling the remaining ones.

**Mathematical Steps:**

1. Generate mask: $d^{[l]} \sim \text{Bernoulli}(\text{keep_prob})$
2. Apply mask: $A^{[l]} = A^{[l]} \odot d^{[l]}$
3. Scale up: $A^{[l]} = \frac{A^{[l]}}{\text{keep_prob}}$

```python
def forward_propagation_with_dropout(X, parameters, keep_prob=0.8):
    """
    Forward propagation with inverted dropout

    Args:
        X: Input data
        parameters: Dictionary containing weights and biases
        keep_prob: Probability of keeping a neuron active

    Returns:
        A3: Output after forward propagation
        cache: Cache containing dropout masks and intermediate values
    """
    np.random.seed(1)  # For reproducible results

    # Layer 1
    Z1 = np.dot(parameters['W1'], X) + parameters['b1']
    A1 = np.maximum(0, Z1)  # ReLU activation

    # Dropout on layer 1
    D1 = np.random.rand(A1.shape[0], A1.shape[1])  # Random numbers [0,1)
    D1 = (D1 < keep_prob).astype(int)               # Convert to 0s and 1s
    A1 = A1 * D1                                    # Apply mask
    A1 = A1 / keep_prob                             # Scale up (inverted dropout)

    # Layer 2
    Z2 = np.dot(parameters['W2'], A1) + parameters['b2']
    A2 = np.maximum(0, Z2)  # ReLU activation

    # Dropout on layer 2
    D2 = np.random.rand(A2.shape[0], A2.shape[1])
    D2 = (D2 < keep_prob).astype(int)
    A2 = A2 * D2
    A2 = A2 / keep_prob

    # Output layer (no dropout)
    Z3 = np.dot(parameters['W3'], A2) + parameters['b3']
    A3 = 1 / (1 + np.exp(-Z3))  # Sigmoid activation

    cache = (Z1, D1, A1, parameters['W1'], parameters['b1'],
             Z2, D2, A2, parameters['W2'], parameters['b2'],
             Z3, A3, parameters['W3'], parameters['b3'])

    return A3, cache

def backward_propagation_with_dropout(X, Y, cache, keep_prob=0.8):
    """
    Backward propagation with dropout

    Args:
        X: Input data
        Y: True labels
        cache: Cache from forward propagation
        keep_prob: Probability of keeping a neuron

    Returns:
        gradients: Dictionary containing gradients
    """
    m = X.shape[1]
    (Z1, D1, A1, W1, b1, Z2, D2, A2, W2, b2, Z3, A3, W3, b3) = cache

    # Output layer
    dZ3 = A3 - Y
    dW3 = (1/m) * np.dot(dZ3, A2.T)
    db3 = (1/m) * np.sum(dZ3, axis=1, keepdims=True)

    # Hidden layer 2
    dA2 = np.dot(W3.T, dZ3)
    dA2 = dA2 * D2              # Apply same dropout mask
    dA2 = dA2 / keep_prob       # Scale gradients
    dZ2 = np.multiply(dA2, np.int64(A2 > 0))  # ReLU derivative
    dW2 = (1/m) * np.dot(dZ2, A1.T)
    db2 = (1/m) * np.sum(dZ2, axis=1, keepdims=True)

    # Hidden layer 1
    dA1 = np.dot(W2.T, dZ2)
    dA1 = dA1 * D1              # Apply same dropout mask
    dA1 = dA1 / keep_prob       # Scale gradients
    dZ1 = np.multiply(dA1, np.int64(A1 > 0))  # ReLU derivative
    dW1 = (1/m) * np.dot(dZ1, X.T)
    db1 = (1/m) * np.sum(dZ1, axis=1, keepdims=True)

    gradients = {
        "dZ3": dZ3, "dW3": dW3, "db3": db3,
        "dZ2": dZ2, "dW2": dW2, "db2": db2,
        "dZ1": dZ1, "dW1": dW1, "db1": db1
    }

    return gradients

# Example: Demonstrate dropout effect
def demonstrate_dropout():
    """Show how dropout affects activations"""
    np.random.seed(42)

    # Create sample parameters
    parameters = {
        'W1': np.random.randn(4, 3) * 0.5,
        'b1': np.zeros((4, 1)),
        'W2': np.random.randn(3, 4) * 0.5,
        'b2': np.zeros((3, 1)),
        'W3': np.random.randn(1, 3) * 0.5,
        'b3': np.zeros((1, 1))
    }

    # Sample input
    X = np.random.randn(3, 5)  # 3 features, 5 examples

    print("Dropout Effect Demonstration:")
    keep_probs = [1.0, 0.8, 0.5, 0.2]

    for keep_prob in keep_probs:
        A3, _ = forward_propagation_with_dropout(X, parameters, keep_prob)
        avg_activation = np.mean(A3)
        print(f"keep_prob = {keep_prob}: Average output = {avg_activation:.4f}")

demonstrate_dropout()
```

---

## 5. Input Normalization

### Data Preprocessing Implementation

**What this does:** Normalizes input features to have zero mean and unit variance, speeding up gradient descent convergence.

**Mathematical Steps:**

1. $\mu = \frac{1}{m}\sum_{i=1}^{m}x^{(i)}$
2. $x := x - \mu$
3. $\sigma^2 = \frac{1}{m}\sum_{i=1}^{m}(x^{(i)})^2$
4. $x := \frac{x}{\sigma}$

```python
def normalize_data(X_train, X_dev, X_test):
    """
    Normalize input features using training set statistics

    Args:
        X_train: Training set, shape (n_features, m_train)
        X_dev: Dev set, shape (n_features, m_dev)
        X_test: Test set, shape (n_features, m_test)

    Returns:
        X_train_norm, X_dev_norm, X_test_norm: Normalized datasets
        mu, sigma: Normalization parameters for later use
    """
    # Compute statistics ONLY on training set
    mu = np.mean(X_train, axis=1, keepdims=True)
    sigma = np.std(X_train, axis=1, keepdims=True)

    # Avoid division by zero
    sigma = np.where(sigma == 0, 1, sigma)

    # Apply same normalization to all sets
    X_train_norm = (X_train - mu) / sigma
    X_dev_norm = (X_dev - mu) / sigma
    X_test_norm = (X_test - mu) / sigma

    return X_train_norm, X_dev_norm, X_test_norm, mu, sigma

# Demonstrate normalization effect
def demonstrate_normalization():
    """Show before and after normalization statistics"""
    np.random.seed(42)

    # Create data with different scales
    feature1 = np.random.randn(1000) * 100 + 500    # Range: ~300-700
    feature2 = np.random.randn(1000) * 1 + 0        # Range: ~-3 to 3
    feature3 = np.random.randn(1000) * 0.1 + 0.5    # Range: ~0.2-0.8

    X = np.array([feature1, feature2, feature3])

    print("Before Normalization:")
    print("Feature\tMean\t\tStd\t\tMin\t\tMax")
    print("-" * 60)
    for i in range(3):
        mean_val = np.mean(X[i])
        std_val = np.std(X[i])
        min_val = np.min(X[i])
        max_val = np.max(X[i])
        print(f"{i+1}\t{mean_val:.2f}\t\t{std_val:.2f}\t\t{min_val:.2f}\t\t{max_val:.2f}")

    # Normalize
    mu = np.mean(X, axis=1, keepdims=True)
    sigma = np.std(X, axis=1, keepdims=True)
    X_norm = (X - mu) / sigma

    print("\nAfter Normalization:")
    print("Feature\tMean\t\tStd\t\tMin\t\tMax")
    print("-" * 60)
    for i in range(3):
        mean_val = np.mean(X_norm[i])
        std_val = np.std(X_norm[i])
        min_val = np.min(X_norm[i])
        max_val = np.max(X_norm[i])
        print(f"{i+1}\t{mean_val:.2f}\t\t{std_val:.2f}\t\t{min_val:.2f}\t\t{max_val:.2f}")

demonstrate_normalization()
```

---

## 6. Weight Initialization

### He and Xavier Initialization

**What this does:** Implements proper weight initialization strategies to prevent vanishing/exploding gradients in deep networks.

**Key Formulas:**

- **He (ReLU):** $W^{[l]} \sim \mathcal{N}(0, \frac{2}{n^{[l-1]}})$
- **Xavier (Tanh):** $W^{[l]} \sim \mathcal{N}(0, \frac{1}{n^{[l-1]}})$

```python
def initialize_parameters_he(layer_dims):
    """
    He initialization for ReLU networks

    Args:
        layer_dims: List containing dimensions of each layer

    Returns:
        parameters: Dictionary containing initialized W1, b1, W2, b2, ...
    """
    np.random.seed(42)
    parameters = {}
    L = len(layer_dims)

    for l in range(1, L):
        # He initialization: variance = 2/n[l-1]
        parameters[f'W{l}'] = np.random.randn(layer_dims[l], layer_dims[l-1]) * np.sqrt(2/layer_dims[l-1])
        parameters[f'b{l}'] = np.zeros((layer_dims[l], 1))

        print(f"W{l} shape: {parameters[f'W{l}'].shape}, std: {np.std(parameters[f'W{l}']):.4f}")

    return parameters

def initialize_parameters_xavier(layer_dims):
    """
    Xavier initialization for Tanh networks

    Args:
        layer_dims: List containing dimensions of each layer

    Returns:
        parameters: Dictionary containing initialized W1, b1, W2, b2, ...
    """
    np.random.seed(42)
    parameters = {}
    L = len(layer_dims)

    for l in range(1, L):
        # Xavier initialization: variance = 1/n[l-1]
        parameters[f'W{l}'] = np.random.randn(layer_dims[l], layer_dims[l-1]) * np.sqrt(1/layer_dims[l-1])
        parameters[f'b{l}'] = np.zeros((layer_dims[l], 1))

        print(f"W{l} shape: {parameters[f'W{l}'].shape}, std: {np.std(parameters[f'W{l}']):.4f}")

    return parameters

def compare_initializations():
    """Compare different initialization strategies"""
    layer_dims = [784, 512, 256, 128, 10]  # MNIST-like network

    print("=== He Initialization (for ReLU) ===")
    params_he = initialize_parameters_he(layer_dims)

    print("\n=== Xavier Initialization (for Tanh) ===")
    params_xavier = initialize_parameters_xavier(layer_dims)

    print("\n=== Comparison of Weight Standard Deviations ===")
    print("Layer\tHe Std\t\tXavier Std\tRecommended For")
    print("-" * 55)
    for l in range(1, len(layer_dims)):
        he_std = np.std(params_he[f'W{l}'])
        xavier_std = np.std(params_xavier[f'W{l}'])
        print(f"{l}\t{he_std:.4f}\t\t{xavier_std:.4f}\t\t{'ReLU' if he_std > xavier_std else 'Tanh'}")

compare_initializations()
```

---

## 7. Gradient Checking

### Numerical Gradient Verification

**What this does:** Implements gradient checking to verify that your backpropagation implementation is computing gradients correctly.

**Mathematical Foundation:**
$$\frac{\partial J}{\partial \theta} \approx \frac{J(\theta + \epsilon) - J(\theta - \epsilon)}{2\epsilon}$$

**Relative Difference:**
$$\text{difference} = \frac{||d\theta_{approx} - d\theta||_2}{||d\theta_{approx}||_2 + ||d\theta||_2}$$

```python
def dictionary_to_vector(parameters):
    """
    Roll parameters dictionary into a single vector

    Args:
        parameters: Dictionary containing W1, b1, W2, b2, etc.

    Returns:
        theta: Vector containing all parameters
        keys: List of parameter names for reconstruction
    """
    keys = []
    count = 0

    for key in sorted(parameters.keys()):
        new_vector = np.reshape(parameters[key], (-1, 1))
        keys = keys + [key] * new_vector.shape[0]

        if count == 0:
            theta = new_vector
        else:
            theta = np.concatenate((theta, new_vector), axis=0)
        count += 1

    return theta, keys

def vector_to_dictionary(theta, layer_dims):
    """
    Convert vector back to parameters dictionary

    Args:
        theta: Vector containing all parameters
        layer_dims: Layer dimensions for reshaping

    Returns:
        parameters: Dictionary with original structure
    """
    parameters = {}
    start = 0

    for l in range(1, len(layer_dims)):
        # Weights
        w_size = layer_dims[l] * layer_dims[l-1]
        parameters[f'W{l}'] = theta[start:start+w_size].reshape((layer_dims[l], layer_dims[l-1]))
        start += w_size

        # Biases
        b_size = layer_dims[l]
        parameters[f'b{l}'] = theta[start:start+b_size].reshape((layer_dims[l], 1))
        start += b_size

    return parameters

def simple_forward_prop(X, parameters):
    """Simple forward propagation for gradient checking"""
    Z1 = np.dot(parameters['W1'], X) + parameters['b1']
    A1 = np.maximum(0, Z1)  # ReLU
    Z2 = np.dot(parameters['W2'], A1) + parameters['b2']
    A2 = 1 / (1 + np.exp(-Z2))  # Sigmoid
    return A2

def simple_cost(A2, Y):
    """Simple cost function for gradient checking"""
    m = Y.shape[1]
    cost = -(1/m) * np.sum(Y * np.log(A2) + (1-Y) * np.log(1-A2))
    return cost

def gradient_check_demo():
    """
    Demonstrate gradient checking with a simple example
    """
    # Simple 2-layer network
    layer_dims = [3, 4, 1]  # 3 inputs, 4 hidden, 1 output

    # Initialize parameters
    np.random.seed(42)
    parameters = {
        'W1': np.random.randn(4, 3) * 0.1,
        'b1': np.zeros((4, 1)),
        'W2': np.random.randn(1, 4) * 0.1,
        'b2': np.zeros((1, 1))
    }

    # Create simple data
    X = np.random.randn(3, 2)  # 3 features, 2 examples
    Y = np.array([[1, 0]])     # Binary labels

    # Forward prop
    A2 = simple_forward_prop(X, parameters)
    cost = simple_cost(A2, Y)

    print("Gradient Checking Demonstration:")
    print(f"Initial cost: {cost:.6f}")

    # Manual gradients (simplified for demo)
    # This is where you'd normally call your backprop function
    epsilon = 1e-7

    # Check one parameter as example
    theta_plus = parameters['W1'][0, 0] + epsilon
    theta_minus = parameters['W1'][0, 0] - epsilon

    params_plus = parameters.copy()
    params_plus['W1'] = parameters['W1'].copy()
    params_plus['W1'][0, 0] = theta_plus

    params_minus = parameters.copy()
    params_minus['W1'] = parameters['W1'].copy()
    params_minus['W1'][0, 0] = theta_minus

    A2_plus = simple_forward_prop(X, params_plus)
    cost_plus = simple_cost(A2_plus, Y)

    A2_minus = simple_forward_prop(X, params_minus)
    cost_minus = simple_cost(A2_minus, Y)

    numerical_gradient = (cost_plus - cost_minus) / (2 * epsilon)

    print(f"Numerical gradient for W1[0,0]: {numerical_gradient:.8f}")
    print("This demonstrates the two-sided difference formula for gradient checking")
    print("In practice, you would:")
    print("1. Compute ALL numerical gradients")
    print("2. Compare with backprop gradients")
    print("3. Check if relative difference < 1e-7")

gradient_check_demo()

def full_gradient_check(parameters, gradients, X, Y, layer_dims, epsilon=1e-7):
    """
    Complete gradient checking implementation

    Args:
        parameters: Dictionary with weights and biases
        gradients: Dictionary with computed gradients from backprop
        X: Input data
        Y: True labels
        layer_dims: Network architecture
        epsilon: Small value for numerical differentiation

    Returns:
        difference: Relative difference between numerical and analytical gradients
    """
    # Convert to vectors
    parameters_values, _ = dictionary_to_vector(parameters)
    grad_values, _ = dictionary_to_vector(gradients)
    num_parameters = parameters_values.shape[0]

    # Initialize
    J_plus = np.zeros((num_parameters, 1))
    J_minus = np.zeros((num_parameters, 1))
    gradapprox = np.zeros((num_parameters, 1))

    print(f"Checking {num_parameters} parameters...")

    # Compute numerical gradients for each parameter
    for i in range(num_parameters):
        # Theta plus
        theta_plus = np.copy(parameters_values)
        theta_plus[i][0] += epsilon
        params_plus = vector_to_dictionary(theta_plus, layer_dims)
        AL_plus = simple_forward_prop(X, params_plus)
        J_plus[i] = simple_cost(AL_plus, Y)

        # Theta minus
        theta_minus = np.copy(parameters_values)
        theta_minus[i][0] -= epsilon
        params_minus = vector_to_dictionary(theta_minus, layer_dims)
        AL_minus = simple_forward_prop(X, params_minus)
        J_minus[i] = simple_cost(AL_minus, Y)

        # Numerical gradient
        gradapprox[i] = (J_plus[i] - J_minus[i]) / (2 * epsilon)

    # Compute relative difference
    numerator = np.linalg.norm(grad_values - gradapprox)
    denominator = np.linalg.norm(grad_values) + np.linalg.norm(gradapprox)
    difference = numerator / denominator

    # Interpretation
    print(f"\nGradient Check Results:")
    print(f"Relative difference: {difference}")

    if difference > 2e-7:
        print("❌ There might be a mistake in backpropagation!")
        print("Check your implementation carefully.")
        if difference > 1e-5:
            print("🚨 SERIOUS BUG - Major implementation error!")
        elif difference > 1e-7:
            print("⚠️  Minor issue - Double-check specific components")
    else:
        print("✅ Your backward propagation works perfectly!")

    return difference

# Simple backprop for demonstration
def simple_backward_prop(X, Y, parameters):
    """Simple backward propagation for gradient checking demo"""
    m = X.shape[1]

    # Forward prop
    Z1 = np.dot(parameters['W1'], X) + parameters['b1']
    A1 = np.maximum(0, Z1)  # ReLU
    Z2 = np.dot(parameters['W2'], A1) + parameters['b2']
    A2 = 1 / (1 + np.exp(-Z2))  # Sigmoid

    # Backward prop
    dZ2 = A2 - Y
    dW2 = (1/m) * np.dot(dZ2, A1.T)
    db2 = (1/m) * np.sum(dZ2, axis=1, keepdims=True)

    dA1 = np.dot(parameters['W2'].T, dZ2)
    dZ1 = np.multiply(dA1, np.int64(A1 > 0))  # ReLU derivative
    dW1 = (1/m) * np.dot(dZ1, X.T)
    db1 = (1/m) * np.sum(dZ1, axis=1, keepdims=True)

    gradients = {
        'dW1': dW1,
        'db1': db1,
        'dW2': dW2,
        'db2': db2
    }

    return gradients

# Complete gradient checking example
def run_complete_gradient_check():
    """Run a complete gradient checking example"""
    print("=== Complete Gradient Checking Example ===")

    # Setup
    layer_dims = [3, 4, 1]
    np.random.seed(42)

    parameters = {
        'W1': np.random.randn(4, 3) * 0.1,
        'b1': np.zeros((4, 1)),
        'W2': np.random.randn(1, 4) * 0.1,
        'b2': np.zeros((1, 1))
    }

    X = np.random.randn(3, 5)  # 3 features, 5 examples
    Y = np.random.randint(0, 2, (1, 5))  # Random binary labels

    # Compute gradients using backprop
    gradients = simple_backward_prop(X, Y, parameters)

    # Run gradient check
    difference = full_gradient_check(parameters, gradients, X, Y, layer_dims)

    return difference

# Run the complete example
run_complete_gradient_check()
```

---

## 8. Data Augmentation Example

### Image Data Augmentation

**What this does:** Demonstrates data augmentation techniques to artificially expand your training dataset.

**Common Transformations:**

- Horizontal flips
- Random rotations
- Random crops
- Color jittering

```python
def augment_data_simple(X, y, augmentation_factor=2):
    """
    Simple data augmentation by adding noise and transformations

    Args:
        X: Original training data
        y: Original labels
        augmentation_factor: How many times to multiply the dataset

    Returns:
        X_augmented, y_augmented: Expanded dataset
    """
    X_augmented = [X]
    y_augmented = [y]

    for i in range(augmentation_factor - 1):
        # Add small random noise
        X_noisy = X + np.random.normal(0, 0.01, X.shape)

        # Random scaling
        scale_factor = np.random.uniform(0.95, 1.05)
        X_scaled = X * scale_factor

        X_augmented.append(X_noisy)
        X_augmented.append(X_scaled)
        y_augmented.append(y)
        y_augmented.append(y)

    X_final = np.concatenate(X_augmented, axis=0)
    y_final = np.concatenate(y_augmented, axis=0)

    print(f"Original dataset size: {X.shape[0]} examples")
    print(f"Augmented dataset size: {X_final.shape[0]} examples")
    print(f"Expansion factor: {X_final.shape[0] / X.shape[0]:.1f}x")

    return X_final, y_final

# Example usage
np.random.seed(42)
X_original = np.random.randn(1000, 5)  # 1000 examples, 5 features
y_original = np.random.randint(0, 2, 1000)

X_aug, y_aug = augment_data_simple(X_original, y_original, augmentation_factor=3)
```

---

## 9. Early Stopping Implementation

### Training with Early Stopping

**What this does:** Implements early stopping to prevent overfitting by monitoring validation performance.

**Algorithm:**

1. Train model and monitor validation loss
2. Keep track of best validation performance
3. Stop training when validation loss stops improving

```python
def early_stopping_demo():
    """
    Simulate early stopping behavior
    """
    # Simulate training and validation losses
    epochs = 50

    # Simulate realistic loss curves
    train_losses = []
    val_losses = []

    # Initial high loss, then decreasing
    base_train = 2.0
    base_val = 2.0

    best_val_loss = float('inf')
    best_epoch = 0
    patience = 10
    patience_counter = 0

    print("Epoch\tTrain Loss\tVal Loss\tStatus")
    print("-" * 45)

    for epoch in range(epochs):
        # Simulate decreasing training loss
        train_loss = base_train * np.exp(-epoch * 0.1) + np.random.normal(0, 0.05)

        # Simulate validation loss that first decreases then increases (overfitting)
        if epoch < 20:
            val_loss = base_val * np.exp(-epoch * 0.08) + np.random.normal(0, 0.08)
        else:
            val_loss = base_val * np.exp(-20 * 0.08) + (epoch - 20) * 0.02 + np.random.normal(0, 0.08)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        # Early stopping logic
        status = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            status = "✓ Best"
        else:
            patience_counter += 1
            if patience_counter >= patience:
                status = "🛑 STOP"
            else:
                status = f"⏳ {patience_counter}/{patience}"

        print(f"{epoch+1}\t{train_loss:.4f}\t\t{val_loss:.4f}\t\t{status}")

        # Stop training if patience exceeded
        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch+1}")
            print(f"Best validation loss: {best_val_loss:.4f} at epoch {best_epoch+1}")
            break

    return train_losses, val_losses, best_epoch

# Run early stopping demo
train_losses, val_losses, best_epoch = early_stopping_demo()

# Plot the losses if matplotlib is available
try:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 6))
    plt.plot(train_losses, label='Training Loss', color='blue')
    plt.plot(val_losses, label='Validation Loss', color='red')
    plt.axvline(x=best_epoch, color='green', linestyle='--', label=f'Best Epoch ({best_epoch+1})')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Early Stopping Demonstration')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()

except ImportError:
    print("\nMatplotlib not available for plotting, but early stopping demo completed!")
```

---

## 10. Complete Practical Recipe

### Machine Learning Diagnostic Workflow

**What this does:** Implements the complete practical recipe for debugging machine learning models.

```python
def ml_diagnostic_workflow(train_error, dev_error, test_error=None, human_error=0.0):
    """
    Complete ML diagnostic workflow

    Args:
        train_error: Training set error (%)
        dev_error: Development set error (%)
        test_error: Test set error (%) - optional
        human_error: Human-level performance (%)

    Returns:
        Comprehensive analysis and action plan
    """
    print("=== MACHINE LEARNING DIAGNOSTIC WORKFLOW ===")
    print(f"Human-level error: {human_error:.1f}%")
    print(f"Training error: {train_error:.1f}%")
    print(f"Dev error: {dev_error:.1f}%")
    if test_error:
        print(f"Test error: {test_error:.1f}%")

    # Calculate bias and variance
    bias = train_error - human_error
    variance = dev_error - train_error

    print(f"\nBias (Train - Human): {bias:.1f}%")
    print(f"Variance (Dev - Train): {variance:.1f}%")

    # Decision tree
    action_plan = []

    # High bias check
    if bias > 2.0:  # Threshold can be adjusted
        print("\n🔴 HIGH BIAS DETECTED (Underfitting)")
        action_plan.extend([
            "1. Use bigger network (more layers/units)",
            "2. Train longer (more epochs)",
            "3. Try different architecture",
            "4. Reduce regularization"
        ])

    # High variance check
    if variance > 2.0:
        print("\n🟡 HIGH VARIANCE DETECTED (Overfitting)")
        action_plan.extend([
            "5. Get more training data",
            "6. Add regularization (L2, dropout)",
            "7. Use data augmentation",
            "8. Try simpler architecture",
            "9. Early stopping"
        ])

    # Good performance
    if bias <= 2.0 and variance <= 2.0:
        print("\n🟢 GOOD PERFORMANCE")
        action_plan.extend([
            "1. Model is performing well!",
            "2. Consider final testing and deployment",
            "3. Monitor for data drift in production"
        ])

    # Test set check (if available)
    if test_error:
        test_variance = test_error - dev_error
        if abs(test_variance) > 1.0:
            print(f"\n⚠️  WARNING: Dev/Test mismatch ({test_variance:.1f}%)")
            action_plan.append("10. Check if dev and test sets are from same distribution")

    print("\n=== RECOMMENDED ACTION PLAN ===")
    for action in action_plan:
        print(action)

    return {
        'bias': bias,
        'variance': variance,
        'diagnosis': 'high_bias' if bias > 2.0 else 'high_variance' if variance > 2.0 else 'good',
        'actions': action_plan
    }

# Test different scenarios
print("SCENARIO 1: Underfitting Model")
ml_diagnostic_workflow(train_error=15.0, dev_error=16.0, test_error=16.5, human_error=0.5)

print("\n" + "="*60)
print("SCENARIO 2: Overfitting Model")
ml_diagnostic_workflow(train_error=2.0, dev_error=12.0, test_error=11.5, human_error=0.5)

print("\n" + "="*60)
print("SCENARIO 3: Well-tuned Model")
ml_diagnostic_workflow(train_error=1.0, dev_error=1.5, test_error=1.6, human_error=0.5)
```

---

## Summary

This notebook provides runnable implementations of all key concepts from Course 2 Week 1:

1. **Data Management**: Proper train/dev/test splitting
2. **Bias/Variance Analysis**: Diagnostic tools for model debugging
3. **L2 Regularization**: Mathematical implementation with weight decay
4. **Dropout**: Inverted dropout with proper scaling
5. **Input Normalization**: Feature scaling for faster convergence
6. **Weight Initialization**: He and Xavier methods for deep networks
7. **Gradient Checking**: Numerical verification of backpropagation
8. **Data Augmentation**: Simple techniques to expand datasets
9. **Early Stopping**: Preventing overfitting during training
10. **Complete Workflow**: Systematic approach to ML debugging

Each section can be run independently to understand and experiment with these fundamental deep learning techniques!
