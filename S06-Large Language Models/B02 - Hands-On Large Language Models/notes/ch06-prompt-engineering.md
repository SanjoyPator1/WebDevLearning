# Chapter 6: Prompt Engineering

## Table of Contents

1. [Using Text Generation Models](#1-using-text-generation-models)
2. [The Basic Ingredients of a Prompt](#2-the-basic-ingredients-of-a-prompt)
3. [Advanced Prompt Engineering](#3-advanced-prompt-engineering)
4. [In-Context Learning: Providing Examples](#4-in-context-learning-providing-examples)
5. [Reasoning with Generative Models (CoT)](#5-reasoning-with-generative-models-cot)
6. [Output Verification and Grammar](#6-output-verification-and-grammar)

## Topics i had doubt and this are the answers - all messed up btw

## Temperature (The "Randomness" Dial)

**Temperature** controls the shape of the probability distribution before the model picks a word. It determines how much the model favors the "obvious" choice versus taking a "risk" on less likely words.

- **Low Temperature ($< 1.0$):** Makes the distribution "sharper." The most likely word gets even more weight, while others drop off significantly. This leads to focused, predictable, and repetitive text.
- **High Temperature ($> 1.0$):** Makes the distribution "flatter." The gap between the most likely word and the less likely ones shrinks. This leads to creative, diverse, and sometimes nonsensical text.
- **Temperature = 1.0:** The model uses its raw calculated probabilities without any modification.

---

### The Mathematical Effect

If the model calculates raw scores (logits) for the next word, the temperature $T$ is applied to the Softmax function:

$$P_i = \frac{\exp(z_i / T)}{\sum_{j} \exp(z_j / T)}$$

- As $T \to 0$, the model becomes deterministic (always picks the highest probability).
- As $T \to \infty$, the distribution becomes uniform (every word has an equal chance).

---

### Example: "The weather today is..."

Imagine the raw probabilities are:

1.  **sunny** (60%)
2.  **cloudy** (30%)
3.  **purple** (0.1%)

**Scenario A: Low Temperature (e.g., 0.2)**
The model "boosts" the leader. _Sunny_ might jump to **99%**, and _cloudy_ drops to **1%**. The model is now almost certain to pick "sunny." It is playing it very safe.

**Scenario B: High Temperature (e.g., 1.5)**
The model "levels" the playing field. _Sunny_ might drop to **40%**, _cloudy_ stays at **30%**, and _purple_ might jump up to **10%**. The model is now much more likely to pick a weird or unexpected word.

---

### Comparison Summary

| Temperature Setting | Character             | Best For                              |
| :------------------ | :-------------------- | :------------------------------------ |
| **0.1 – 0.4**       | Conservative / Formal | Coding, factual Q&A, data extraction. |
| **0.7 – 0.9**       | Balanced / Natural    | General conversation, blog writing.   |
| **1.0 – 1.5**       | Creative / Wild       | Poetry, brainstorming, storytelling.  |

---

When you're dealing with **Top-K** and **Top-P**, you are looking at the "sampling" stage of an LLM. This is where the model decides which word (token) to pick next from a list of possibilities.

---

## 1. Top-K Sampling (The Count-Based Filter)

Top-K tells the model to look at the **top K most likely next words** and ignore everything else. It doesn't matter how high or low the probabilities are; the model only cares about the rank.

- **How it works:** If $K=3$, the model only considers the 3 most probable words.
- **The Vibe:** It’s like a "Shortlist." You only look at the top candidates, regardless of how good the rest of the pool is.

### Example: "The cat sat on the..."

Imagine the model's brain sees these probabilities:

1.  **mat** (40%)
2.  **rug** (30%)
3.  **floor** (15%)
4.  **pizza** (5%)
5.  **moon** (1%)

If **Top-K = 3**, the model will only pick from _mat_, _rug_, or _floor_. Even if "pizza" was a somewhat okay guess, it's cut off because it's 4th on the list.

---

## 2. Top-P Sampling (The Probability-Based Filter)

Also known as **Nucleus Sampling**, Top-P looks at the **cumulative probability**. It adds up the probabilities of the top words until they hit a threshold $P$.

- **How it works:** If $P=0.85$, the model keeps adding words to its "pool" until their combined percentages reach 85%.
- **The Vibe:** It’s "Dynamic." In a predictable sentence, the pool might only be 2 words. In a creative/chaotic sentence, the pool might expand to 20 words.

### Example: Same "The cat sat on the..."

1.  **mat** (40%)
2.  **rug** (30%)
3.  **floor** (15%)
4.  **pizza** (5%)

If **Top-P = 0.85**, the model adds:
$0.40 (\text{mat}) + 0.30 (\text{rug}) + 0.15 (\text{floor}) = 0.85$
The model will only pick from these three. If the probabilities were more spread out, it would include more words to reach that 0.85.

---

## Comparison Table

| Feature         | Top-K                                                   | Top-P (Nucleus)                                         |
| :-------------- | :------------------------------------------------------ | :------------------------------------------------------ |
| **Logic**       | Fixed number of words.                                  | Fixed "mass" of probability.                            |
| **Flexibility** | Static; doesn't care about context.                     | Dynamic; adjusts based on how "confident" the model is. |
| **Risk**        | Can sometimes include "garbage" words if K is too high. | Generally produces more natural, diverse text.          |

**Pro-Tip:** In practice, most people use Top-P or a combination of both. Top-P is usually preferred because it allows the model to be "narrow" when the next word is obvious and "broad" when the next word could be many things.

---

**System 1 and System 2** isn't originally an AI concept—it's a psychological one from a famous book called _Thinking, Fast and Slow_ by Daniel Kahneman.

Here is the breakdown:

### **1. System 1: The "Autopilot"**

System 1 is fast, instinctive, and emotional. It’s what you use when someone asks, "What is 2 + 2?" You don't "think"—the number **4** just pops into your head.

- **In LLMs:** When you give a model a simple prompt and it just blurs out an answer immediately based on patterns it saw in training, that’s **System 1**. It’s just "predicting the next token" without "thinking" about whether it makes sense.
- **Example:** \* _Prompt:_ "The capital of France is..."
  - _LLM:_ "Paris." (Pure pattern matching).

### **2. System 2: The "Pilot"**

System 2 is slower, more deliberate, and logical. It’s what you use when someone asks, "What is 17 x 24?" You have to stop, focus, and maybe even visualize the steps of the calculation.

- **In LLMs:** Standard LLMs don't naturally have a "System 2." They are essentially "System 1" machines. However, through **Prompt Engineering**, we can _force_ them to act like they have a System 2 by making them write out their steps.
- **Example:**
  - _Prompt:_ "Solve 17 x 24. Think step-by-step."
  - _LLM:_ "First, 17 x 20 is 340. Then 17 x 4 is 68. 340 + 68 is 408."

---

### **Why does this matter for Prompt Engineering?**

The text you shared is setting the stage for **Chain-of-Thought (CoT)** prompting.

Since LLMs are naturally "System 1" (they just guess the next word), they often make silly mistakes on hard logic problems. By using techniques like **"Think step-by-step,"** we are essentially installing a manual "System 2" into the prompt. We are forcing the model to "slow down" and use its own previous words to help it find the right answer.

### **Was it explained before?**

In the context of your book, it likely wasn't explained in depth until this chapter. Earlier chapters probably focused on "Modular" prompting (how to structure a prompt), whereas this chapter is moving into "Reasoning" (how to make the model smarter).

**The TL;DR for your notes:**

- **System 1:** Fast, intuitive, pattern-based (The LLM's default state).
- **System 2:** Slow, logical, step-by-step (What we try to achieve with Prompt Engineering).

---

In the *Hands-On LLMs* book, the authors discuss how we can "program" the model through the context window. These techniques are often referred to as **In-Context Learning (ICL)**.

---

## 1. Zero-Shot Prompting
This is when you give the model a task with **no examples** at all. You rely purely on the model's pre-trained knowledge to understand the instruction.

* **Example:**
    > "Translate this sentence to French: 'Where is the library?'"

---

## 2. One-Shot Prompting
You provide **one single example** to show the model the desired format or style before asking your actual question. This is great for clarifying a specific output structure.

* **Example:**
    > **Example:**
    > Input: 'The movie was great!' -> Sentiment: Positive
    > 
    > **Actual Task:**
    > Input: 'The food was cold.' -> Sentiment:

---

## 3. Few-Shot Prompting
You provide **multiple examples** (usually 2 to 5). This is the "gold standard" for complex tasks or when you need the model to follow a very specific pattern that it might not pick up from just one example.

* **Example:**
    > **Examples:**
    > Input: 'I love this' -> Category: Happy
    > Input: 'I am so annoyed' -> Category: Angry
    > Input: 'I am feeling sleepy' -> Category: Tired
    > 
    > **Actual Task:**
    > Input: 'I can't wait for the weekend' -> Category:

---

## 4. Chain-of-Thought (CoT) Prompting
Instead of just giving the answer in your examples, you show the **step-by-step reasoning**. This "teaches" the model to slow down and think through the logic before jumping to a conclusion.

* **Example (Few-Shot CoT):**
    > **Q:** Roger has 5 tennis balls. He buys 2 more cans of tennis balls. Each can has 3 balls. How many balls does he have now?
    > **A:** Roger started with 5 balls. 2 cans of 3 balls each is 6 balls. 5 + 6 = 11. The answer is 11.
    > 
    > **Q:** The cafeteria had 23 apples. If they used 20 to make lunch and bought 6 more, how many apples do they have?
    > **A:** (The model will now likely mimic that step-by-step math style).

---

## 5. Zero-Shot CoT
This is a "magic" phrase technique. You don't provide examples, but you add a specific trigger phrase at the end of your prompt to force the model to reason.

* **Common Trigger Phrases:**
    * "Let's think step by step."
    * "Work this out in a step-by-step way to be sure we have the right answer."

---

### Comparison at a Glance

| Technique | # of Examples | Best For |
| :--- | :--- | :--- |
| **Zero-Shot** | 0 | Simple, common tasks. |
| **One-Shot** | 1 | Establishing a specific format. |
| **Few-Shot** | 2–5 | Nuanced classification or complex patterns. |
| **CoT** | 1+ (with logic) | Math, logic, and multi-step reasoning. |

---

