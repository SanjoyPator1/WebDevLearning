# Complete Calculus Derivatives Cheat Sheet

## 📋 Basic Derivative Rules

### Power Rule

$$\frac{d}{dx}[x^n] = nx^{n-1}$$

### Constant Rule

$$\frac{d}{dx}[c] = 0 \quad \text{where } c \text{ is a constant}$$

### Constant Multiple Rule

$$\frac{d}{dx}[cf(x)] = c \cdot f'(x)$$

### Sum/Difference Rule

$$\frac{d}{dx}[f(x) \pm g(x)] = f'(x) \pm g'(x)$$

---

## 🔢 Basic Function Derivatives

### Polynomial Functions

$$\frac{d}{dx}[x] = 1$$

$$\frac{d}{dx}[x^2] = 2x$$

$$\frac{d}{dx}[x^3] = 3x^2$$

$$\frac{d}{dx}[x^n] = nx^{n-1}$$

$$\frac{d}{dx}[\sqrt{x}] = \frac{1}{2\sqrt{x}}$$

$$\frac{d}{dx}[\frac{1}{x}] = -\frac{1}{x^2}$$

---

## 📈 Exponential and Logarithmic Functions

### Natural Exponential

$$\frac{d}{dx}[e^x] = e^x$$

$$\frac{d}{dx}[e^{f(x)}] = e^{f(x)} \cdot f'(x)$$

### General Exponential

$$\frac{d}{dx}[a^x] = a^x \ln(a)$$

$$\frac{d}{dx}[a^{f(x)}] = a^{f(x)} \ln(a) \cdot f'(x)$$

### Natural Logarithm

$$\frac{d}{dx}[\ln(x)] = \frac{1}{x}$$

$$\frac{d}{dx}[\ln(f(x))] = \frac{f'(x)}{f(x)}$$

### General Logarithm

$$\frac{d}{dx}[\log_a(x)] = \frac{1}{x \ln(a)}$$

$$\frac{d}{dx}[\log_a(f(x))] = \frac{f'(x)}{f(x) \ln(a)}$$

### Common Logarithm (Base 10)

$$\frac{d}{dx}[\log(x)] = \frac{1}{x \ln(10)}$$

---

## 📐 Trigonometric Functions

### Basic Trigonometric Derivatives

$$\frac{d}{dx}[\sin(x)] = \cos(x)$$

$$\frac{d}{dx}[\cos(x)] = -\sin(x)$$

$$\frac{d}{dx}[\tan(x)] = \sec^2(x) = \frac{1}{\cos^2(x)}$$

$$\frac{d}{dx}[\cot(x)] = -\csc^2(x) = -\frac{1}{\sin^2(x)}$$

$$\frac{d}{dx}[\sec(x)] = \sec(x)\tan(x)$$

$$\frac{d}{dx}[\csc(x)] = -\csc(x)\cot(x)$$

### Trigonometric with Chain Rule

$$\frac{d}{dx}[\sin(f(x))] = \cos(f(x)) \cdot f'(x)$$

$$\frac{d}{dx}[\cos(f(x))] = -\sin(f(x)) \cdot f'(x)$$

$$\frac{d}{dx}[\tan(f(x))] = \sec^2(f(x)) \cdot f'(x)$$

---

## 🔄 Inverse Trigonometric Functions

$$\frac{d}{dx}[\arcsin(x)] = \frac{1}{\sqrt{1-x^2}}$$

$$\frac{d}{dx}[\arccos(x)] = -\frac{1}{\sqrt{1-x^2}}$$

$$\frac{d}{dx}[\arctan(x)] = \frac{1}{1+x^2}$$

$$\frac{d}{dx}[\text{arccot}(x)] = -\frac{1}{1+x^2}$$

$$\frac{d}{dx}[\text{arcsec}(x)] = \frac{1}{|x|\sqrt{x^2-1}}$$

$$\frac{d}{dx}[\text{arccsc}(x)] = -\frac{1}{|x|\sqrt{x^2-1}}$$

---

## 🔥 Hyperbolic Functions

$$\frac{d}{dx}[\sinh(x)] = \cosh(x)$$

$$\frac{d}{dx}[\cosh(x)] = \sinh(x)$$

$$\frac{d}{dx}[\tanh(x)] = \text{sech}^2(x) = \frac{1}{\cosh^2(x)}$$

$$\frac{d}{dx}[\text{coth}(x)] = -\text{csch}^2(x) = -\frac{1}{\sinh^2(x)}$$

$$\frac{d}{dx}[\text{sech}(x)] = -\text{sech}(x)\tanh(x)$$

$$\frac{d}{dx}[\text{csch}(x)] = -\text{csch}(x)\text{coth}(x)$$

---

## ⚡ Advanced Derivative Rules

### Product Rule

$$\frac{d}{dx}[f(x) \cdot g(x)] = f'(x) \cdot g(x) + f(x) \cdot g'(x)$$

### Quotient Rule

$$\frac{d}{dx}\left[\frac{f(x)}{g(x)}\right] = \frac{f'(x) \cdot g(x) - f(x) \cdot g'(x)}{[g(x)]^2}$$

### Chain Rule

$$\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)$$

### Implicit Differentiation

For $F(x,y) = 0$:

$$\frac{dy}{dx} = -\frac{\frac{\partial F}{\partial x}}{\frac{\partial F}{\partial y}}$$

---

## 🎯 Special Functions for Machine Learning

### Sigmoid Function

$$\sigma(x) = \frac{1}{1+e^{-x}}$$

$$\frac{d}{dx}[\sigma(x)] = \sigma(x)(1-\sigma(x))$$

### Tanh Function

$$\tanh(x) = \frac{e^x - e^{-x}}{e^x + e^{-x}}$$

$$\frac{d}{dx}[\tanh(x)] = 1 - \tanh^2(x) = \text{sech}^2(x)$$

### ReLU Function

$$\text{ReLU}(x) = \max(0, x)$$

$$
\frac{d}{dx}[\text{ReLU}(x)] = \begin{cases}
1 & \text{if } x > 0 \\
0 & \text{if } x < 0 \\
\text{undefined} & \text{if } x = 0
\end{cases}
$$

### Leaky ReLU

$$\text{LeakyReLU}(x) = \max(\alpha x, x) \quad \text{where } \alpha \text{ is small (e.g., 0.01)}$$

$$
\frac{d}{dx}[\text{LeakyReLU}(x)] = \begin{cases}
1 & \text{if } x > 0 \\
\alpha & \text{if } x < 0
\end{cases}
$$

### Softmax Function (Component-wise)

$$\text{softmax}_i(x) = \frac{e^{x_i}}{\sum_{j=1}^n e^{x_j}}$$

$$
\frac{\partial}{\partial x_j}[\text{softmax}_i(x)] = \begin{cases}
\text{softmax}_i(x)(1 - \text{softmax}_i(x)) & \text{if } i = j \\
-\text{softmax}_i(x) \cdot \text{softmax}_j(x) & \text{if } i \neq j
\end{cases}
$$

---

## 🧮 Higher Order Derivatives

### Second Derivative

$$f''(x) = \frac{d^2f}{dx^2} = \frac{d}{dx}\left[\frac{df}{dx}\right]$$

### nth Derivative

$$f^{(n)}(x) = \frac{d^n f}{dx^n}$$

### Common Second Derivatives

$$\frac{d^2}{dx^2}[x^n] = n(n-1)x^{n-2}$$

$$\frac{d^2}{dx^2}[e^x] = e^x$$

$$\frac{d^2}{dx^2}[\sin(x)] = -\sin(x)$$

$$\frac{d^2}{dx^2}[\cos(x)] = -\cos(x)$$

$$\frac{d^2}{dx^2}[\ln(x)] = -\frac{1}{x^2}$$

---

## 📊 Partial Derivatives

### Basic Partial Derivatives

For $f(x,y)$:

$$\frac{\partial f}{\partial x} = \lim_{h \to 0} \frac{f(x+h,y) - f(x,y)}{h}$$

$$\frac{\partial f}{\partial y} = \lim_{h \to 0} \frac{f(x,y+h) - f(x,y)}{h}$$

### Mixed Partial Derivatives

$$\frac{\partial^2 f}{\partial x \partial y} = \frac{\partial}{\partial x}\left(\frac{\partial f}{\partial y}\right)$$

### Clairaut's Theorem

If $f$ has continuous second partial derivatives:

$$\frac{\partial^2 f}{\partial x \partial y} = \frac{\partial^2 f}{\partial y \partial x}$$

---

## 🔗 Common Derivative Combinations

### Logarithmic Differentiation

For $y = [f(x)]^{g(x)}$:

$$\ln(y) = g(x) \ln(f(x))$$

$$\frac{1}{y} \frac{dy}{dx} = g'(x) \ln(f(x)) + g(x) \frac{f'(x)}{f(x)}$$

$$\frac{dy}{dx} = y \left[g'(x) \ln(f(x)) + g(x) \frac{f'(x)}{f(x)}\right]$$

### Parametric Derivatives

For parametric equations $x = f(t)$, $y = g(t)$:

$$\frac{dy}{dx} = \frac{\frac{dy}{dt}}{\frac{dx}{dt}} = \frac{g'(t)}{f'(t)}$$

$$\frac{d^2y}{dx^2} = \frac{d}{dx}\left(\frac{dy}{dx}\right) = \frac{\frac{d}{dt}\left(\frac{dy}{dx}\right)}{\frac{dx}{dt}}$$

---

## 🎯 Memory Tricks & Patterns

### Trigonometric Derivatives Pattern

- Sine and cosine derivatives follow a cycle: $\sin \to \cos \to -\sin \to -\cos \to \sin$
- Tangent and cotangent involve squared secants and cosecants

### Exponential vs Logarithmic

- $e^x$ is its own derivative
- $\ln(x)$ derivative is $\frac{1}{x}$
- Chain rule applies to composite versions

### Inverse Functions

- If $f$ and $g$ are inverses: $\frac{d}{dx}[g(x)] = \frac{1}{f'(g(x))}$

---

## 🚀 Quick Reference for Neural Networks

### Common Activation Function Derivatives

$$\frac{d}{dx}[\text{sigmoid}(x)] = \text{sigmoid}(x)(1-\text{sigmoid}(x))$$

$$\frac{d}{dx}[\tanh(x)] = 1 - \tanh^2(x)$$

$$\frac{d}{dx}[\text{ReLU}(x)] = \begin{cases} 1 & x > 0 \\ 0 & x \leq 0 \end{cases}$$

### Loss Function Derivatives

**Mean Squared Error**: $L = \frac{1}{2}(y - \hat{y})^2$

$$\frac{\partial L}{\partial \hat{y}} = \hat{y} - y$$

**Cross-Entropy**: $L = -y\ln(\hat{y}) - (1-y)\ln(1-\hat{y})$

$$\frac{\partial L}{\partial \hat{y}} = \frac{\hat{y} - y}{\hat{y}(1-\hat{y})}$$

### Chain Rule for Backpropagation

$$\frac{\partial L}{\partial w} = \frac{\partial L}{\partial a} \cdot \frac{\partial a}{\partial z} \cdot \frac{\partial z}{\partial w}$$

where:

- $z$ = pre-activation (weighted sum)
- $a$ = activation (after activation function)
- $w$ = weight parameter

---

## 💡 Pro Tips

1. **Chain Rule is King**: Most complex derivatives use chain rule
2. **Practice Recognition**: Learn to spot function compositions quickly
3. **Use Logarithmic Differentiation**: For products, quotients, and powers
4. **Implicit Differentiation**: When solving for $\frac{dy}{dx}$ is difficult
5. **Check Your Work**: Use derivative rules to verify complex calculations

---

## 📚 Essential Formulas Summary

**Most Used in Calculus**:

- Power rule: $\frac{d}{dx}[x^n] = nx^{n-1}$
- Chain rule: $\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)$
- Product rule: $\frac{d}{dx}[fg] = f'g + fg'$
- Quotient rule: $\frac{d}{dx}[\frac{f}{g}] = \frac{f'g - fg'}{g^2}$

**Most Used in Machine Learning**:

- $\frac{d}{dx}[e^x] = e^x$
- $\frac{d}{dx}[\ln(x)] = \frac{1}{x}$
- $\frac{d}{dx}[\text{sigmoid}(x)] = \text{sigmoid}(x)(1-\text{sigmoid}(x))$
- $\frac{d}{dx}[\tanh(x)] = 1 - \tanh^2(x)$
