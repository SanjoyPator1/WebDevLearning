# Chapter 7: Advanced Text Generation Techniques and Tools

## Table of Contents

1. [Model I/O: Loading Quantized Models with LangChain](#1-model-io-loading-quantized-models-with-langchain)
2. [Chains: Extending the Capabilities of LLMs](#2-chains-extending-the-capabilities-of-llms)
   - [2a. A Single Link: Prompt Template + LLM](#2a-a-single-link-prompt-template--llm)
   - [2b. A Chain with Multiple Prompts (Sequential Chaining)](#2b-a-chain-with-multiple-prompts-sequential-chaining)
3. [Memory: Helping LLMs to Remember Conversations](#3-memory-helping-llms-to-remember-conversations)
   - [3a. Conversation Buffer Memory](#3a-conversation-buffer-memory)
   - [3b. Windowed Conversation Buffer](#3b-windowed-conversation-buffer)
   - [3c. Conversation Summary Memory](#3c-conversation-summary-memory)
   - [3d. Memory Type Comparison](#3d-memory-type-comparison)
4. [Agents: Creating a System of LLMs](#4-agents-creating-a-system-of-llms)
   - [4a. What are Agents?](#4a-what-are-agents)
   - [4b. The ReAct Framework: Reasoning + Acting](#4b-the-react-framework-reasoning--acting)
   - [4c. ReAct in LangChain](#4c-react-in-langchain)

---

> This chapter extends raw LLM power through four modular techniques — quantization for efficient loading, chains for structured workflows, memory for stateful conversations, and agents for autonomous tool use — all unified by the LangChain framework.

---

## 1. Model I/O: Loading Quantized Models with LangChain

### Why Quantization Exists

Large language models contain billions of parameters. By default, each parameter is stored as a 32-bit floating-point number — four bytes per number. For a 7-billion parameter model, that is **28 GB of memory just to store the weights**, before you account for activations, gradients, or intermediate computations during inference. For most people who do not have access to multiple high-end GPUs, this makes running LLMs locally completely impractical.

**Quantization** is the technique of reducing the number of bits used to represent each parameter. Instead of keeping the full 32-bit precision, you use 16, 8, or even 4 bits. The model becomes smaller and faster to run, at the cost of a small reduction in numerical accuracy. This is not a radical new idea — engineers have been making this kind of precision trade-off in hardware and signal processing for decades. What is new is applying it systematically to neural network weights.

The **GGUF** format (which stands for GPT-Generated Unified Format) is a file format that stores quantized LLM weights in a way that can be efficiently loaded and run on CPUs and GPUs using the `llama.cpp` library. When you see a filename like `Phi-3-mini-4k-instruct-fp16.gguf`, the `fp16` tells you the quantization level — in this case, 16-bit floating point.

---

### The Precision Trade-Off: What "Bits" Actually Mean

Think of storing a number as measuring something with a ruler. A 32-bit float is like a ruler with millimeter markings — it can represent very fine distinctions. A 16-bit float is like a ruler with only centimeter markings — still useful and accurate enough for most purposes, but you lose the ability to distinguish between, say, 3.1415927 and 3.1415928.

The book shows a concrete example with the number $\pi$:

```
Float 32-bit: stores  3.1415927  ← high precision, 32 bits
Float 16-bit: stores  3.141      ← lower precision, 16 bits
```

The 16-bit version still knows it is "a bit more than 3.14" — it just cannot say exactly *how much* more. For a neural network parameter, this level of imprecision is usually fine because the model's behavior emerges from the combined effect of billions of parameters, and the accumulated rounding errors tend to cancel out rather than compound.

**How bits encode a number:** A floating-point number is stored in three parts — a **sign bit** (positive or negative), an **exponent** (the magnitude, like the power of 2), and a **mantissa** (the precise fractional value). More bits in the mantissa means finer precision. Cutting from 32 bits to 16 bits reduces the mantissa, which is where precision is lost.

```
Float 32-bit layout  (32 bits total):
┌──┬────────┬───────────────────────┐
│ S│  Exp   │       Mantissa        │
│ 1│  8 bits│       23 bits         │
└──┴────────┴───────────────────────┘
Encodes: 3.1415927

Float 16-bit layout  (16 bits total):
┌──┬──────┬──────────┐
│ S│  Exp │ Mantissa │
│ 1│ 5 bit│  10 bits │
└──┴──────┴──────────┘
Encodes: 3.141
```

A practical rule of thumb from the book: **use at least 4-bit quantization**. At 4 bits, the quality-to-size trade-off is excellent. At 3 bits or 2 bits, the performance degradation becomes noticeable enough that you would be better off choosing a smaller model with higher precision than a large model at very low bit depth.

---

### Dry-Run: Visualising Precision Loss

Let us trace how the number $\pi = 3.14159265$ gets encoded and truncated at different bit depths.

```
Exact value:  3.14159265358979...

Step 1: Float32 representation
  Sign     = 0  (positive)
  Exponent = 128 (encodes 2^1 = 2, so 1 × 1.57... = 3.14...)
  Mantissa = 23 bits encoding 1.57079632...
  Stored:   3.1415927  (rounds at 7th decimal place)

Step 2: Float16 representation
  Sign     = 0  (positive)
  Exponent = 16 (same power of 2)
  Mantissa = 10 bits encoding 1.571  (far fewer bits = coarser)
  Stored:   3.141      (rounds at 3rd decimal place)

Step 3: Int8 quantization (a different strategy)
  Map the float range [min_val, max_val] to integers [-128, 127]
  Using scale factor = max_val / 127
  3.14159 gets stored as integer 40 (approximately)
  At inference: 40 × scale ≈ 3.15  (small error introduced)

Conclusion: Each step loses precision, but for LLM weights
  the model behaviour degrades gracefully until ~4-bit.
```

---

### Loading a Quantized Model with LangChain

LangChain provides a `LlamaCpp` class that wraps the `llama-cpp-python` library, which can efficiently run GGUF files on your hardware. Here is how to load a quantized Phi-3 model:

```python
from langchain import LlamaCpp

# n_gpu_layers=-1 means: offload ALL layers to GPU (use your full A6000)
# n_ctx=2048 means: the model can see up to 2048 tokens of context
# seed=42 ensures reproducible outputs
llm = LlamaCpp(
    model_path="Phi-3-mini-4k-instruct-fp16.gguf",
    n_gpu_layers=-1,
    max_tokens=500,
    n_ctx=2048,
    seed=42,
    verbose=False
)
```

Once loaded, you can invoke the model:

```python
llm.invoke("Hi! My name is Maarten. What is 1 + 1?")
# Returns: ''   ← empty string! Why?
```

The empty output is not a bug. Instruct-tuned models like Phi-3 are trained with **special tokens** that mark the boundary between the user's message and the model's response. Without these tokens, the model does not know when it is supposed to start talking. The model is waiting for its cue — like an actor who won't improvise until they see their stage direction in the script. This problem is what motivates the very next topic: chains and prompt templates.

---

## 2. Chains: Extending the Capabilities of LLMs

### The Big Picture

LangChain is built around a central idea: a language model rarely works best in isolation. Real-world applications need the model connected to prompts, memory, external tools, output parsers, and other models. **Chains** are the glue that connects these components together in a clean, composable way.

A chain takes an input, passes it through one or more processing steps, and produces an output. The simplest chain connects a prompt template to an LLM. More complex chains connect multiple prompts, models, and data sources in sequence. LangChain's architecture looks like this:

```
┌─────────────────────────────────────────────────────────┐
│                        LangChain                        │
│                                                         │
│  [Model I/O]──[Memory]──[Retrieval]──[Agents]           │
│  • Prompts    • Buffer   • Embeddings  • Tools          │
│  • LLMs       • Summary  • Vector DB   • ReAct          │
│  • Parsers    • Window                 • Autonomous     │
└─────────────────────────────────────────────────────────┘
         Each module can be chained together
```

---

### 2a. A Single Link: Prompt Template + LLM

#### The Problem with Raw Invocation

As we saw above, sending a plain string to an instruct model returns an empty response because the model expects its conversation to be wrapped in special tokens. Phi-3's template requires four components, in this exact order:

```
<s>           ← Beginning of Sentence token (BOS)
<|user|>      ← Start of the user's turn
Your message here
<|end|>       ← End of the user's turn
<|assistant|> ← Start of the model's turn (model begins generating here)
```

Without the `<|assistant|>` marker at the end, the model has no idea it is supposed to generate a response. It is like asking someone a question but then walking away before they can answer — they are left wondering if you are still talking.

#### Creating a Prompt Template

Rather than manually wrapping every message in these tokens, LangChain's `PromptTemplate` does this automatically. You define the template once with placeholders, then use it forever:

```python
from langchain_core.prompts import PromptTemplate

# {input_prompt} is our placeholder — it will be replaced with the user's question
template = """<s><|user|>
{input_prompt}<|end|>
<|assistant|>"""

prompt = PromptTemplate(
    template=template,
    input_variables=["input_prompt"]
)
```

#### The LCEL Pipe Operator

Now we connect the prompt to the LLM using LangChain Expression Language (LCEL). The key operator is `|` — borrowed directly from Unix shell piping, where the output of one command is fed as the input to the next:

```python
basic_chain = prompt | llm
```

This single line creates a chain where your raw question flows left to right through the pipeline:

```
"What is 1+1?"
      │
      ▼
[PromptTemplate]
  Wraps question in <s><|user|>...<|end|><|assistant|>
      │
      ▼
     [LLM]
  Receives properly formatted string, generates response
      │
      ▼
"The answer to 1 + 1 is 2."
```

To use the chain, you call `invoke` with a dictionary matching the template's input variables:

```python
basic_chain.invoke({"input_prompt": "Hi! My name is Maarten. What is 1 + 1?"})
# Returns: "The answer to 1 + 1 is 2. It's a basic arithmetic operation..."
```

The beauty of the pipe approach is composability. As you add more steps — memory, output parsers, additional prompts — you just keep extending the pipe:

```python
# Before LCEL (the old, verbose way):
formatted_text = prompt.format(input_prompt="What is 1+1?")
response = llm.invoke(formatted_text)

# With LCEL (clean, composable):
chain = prompt | llm
response = chain.invoke({"input_prompt": "What is 1+1?"})
```

When you have five or six stages in a pipeline, the pipe notation lets you see the entire data flow at a glance. It reads like a sentence: "Take the prompt, pipe it through the LLM, pipe it through the output parser."

---

### 2b. A Chain with Multiple Prompts (Sequential Chaining)

#### Why Split a Complex Task into Sub-Tasks?

Suppose you want an LLM to generate a complete story with a compelling title, a rich character description, and a gripping plot summary. You could try to put all of that into one enormous prompt, but this has problems. The model has to simultaneously satisfy many constraints, and the results tend to be mediocre at everything rather than excellent at any one thing. Each part of the story competes for the model's attention.

The better approach is **sequential chaining**: break the task into focused sub-tasks, run them one after another, and pass the output of each step as the input to the next. This is the same strategy a good human author uses — first brainstorm a title, then develop the characters, then write the plot. Each step benefits from the work done before it.

```
                   Sequential Chain
                   ───────────────
"a girl that        ┌──────────────┐
 lost her     ─────▶│ Title Prompt │─────▶ "Whispers of Loss"
 mother"            └──────────────┘             │
                           │                     ▼
                    [LLM call 1]         ┌───────────────────┐
                                   ─────▶│ Character Prompt  │─────▶ "Emily, resilient..."
                                         └───────────────────┘             │
                                                │                          ▼
                                         [LLM call 2]         ┌──────────────────┐
                                                          ─────▶│  Story Prompt   │─────▶ Full story
                                                               └──────────────────┘
                                                                      │
                                                               [LLM call 3]
```

#### Building the Sequential Chain in LangChain

LangChain uses `LLMChain` with an `output_key` to name the output of each step. These named outputs become available as input variables for subsequent steps:

```python
from langchain import LLMChain

# Step 1: Generate a title from the summary
template = """<s><|user|>
Create a title for a story about {summary}. Only return the title.<|end|>
<|assistant|>"""
title_prompt = PromptTemplate(template=template, input_variables=["summary"])
title = LLMChain(llm=llm, prompt=title_prompt, output_key="title")

# Step 2: Generate a character using summary + title
template = """<s><|user|>
Describe the main character of a story about {summary} with the title {title}.
Use only two sentences.<|end|>
<|assistant|>"""
character_prompt = PromptTemplate(template=template, input_variables=["summary", "title"])
character = LLMChain(llm=llm, prompt=character_prompt, output_key="character")

# Step 3: Generate the story using all three
template = """<s><|user|>
Create a story about {summary} with the title {title}. The main character is:
{character}. Only return the story and it cannot be longer than one paragraph.<|end|>
<|assistant|>"""
story_prompt = PromptTemplate(
    template=template, input_variables=["summary", "title", "character"]
)
story = LLMChain(llm=llm, prompt=story_prompt, output_key="story")

# Combine all three into one sequential chain
llm_chain = title | character | story
```

#### Dry-Run: Tracing the Data Through the Chain

Let us trace exactly what flows through each step with the input `"a girl that lost her mother"`:

```
Input dict: {"summary": "a girl that lost her mother"}

─── Step 1: title chain ───
  Template fills in: {summary} = "a girl that lost her mother"
  LLM call 1 runs → generates: " Whispers of Loss: A Journey Through Grief"
  Output dict: {
    "summary": "a girl that lost her mother",
    "title": " Whispers of Loss: A Journey Through Grief"   ← NEW key added
  }

─── Step 2: character chain ───
  Template fills in: {summary} AND {title} (both now available)
  LLM call 2 runs → generates: "Emily, a resilient young girl..."
  Output dict: {
    "summary": "a girl that lost her mother",
    "title": " Whispers of Loss: A Journey Through Grief",
    "character": "Emily, a resilient young girl..."          ← NEW key added
  }

─── Step 3: story chain ───
  Template fills in: {summary}, {title}, AND {character}
  LLM call 3 runs → generates the full story paragraph
  Final output dict: {
    "summary": "a girl...",
    "title": "Whispers of Loss...",
    "character": "Emily...",
    "story": "In Loving Memory revolves around Emily..."    ← NEW key added
  }
```

Notice that each `LLMChain` adds its `output_key` to the running dictionary. The final output contains every intermediate result — title, character, and story — not just the last one. This is a huge advantage over a single-prompt approach: you can extract any intermediate output independently.

---

## 3. Memory: Helping LLMs to Remember Conversations

### The Statefulness Problem

Here is a deeply counterintuitive fact about LLMs: they have **no memory between calls**. Every time you invoke an LLM, it starts completely fresh. It does not remember what you said two messages ago, even if you are having what feels like a continuous conversation.

Think of it like talking to someone who has amnesia that resets every time they blink. You say "Hi, I'm Maarten." They respond normally. You blink. You say "What's my name?" They look at you blankly — they have no idea who you are. This is the default state of every LLM. They are **stateless** by design, because each API call is independent.

```
Without Memory:
  Turn 1:  You: "My name is Maarten. What is 1+1?"
           LLM: "Hello Maarten! The answer to 1 + 1 is 2."
                 ↑ LLM knows your name HERE

  Turn 2:  You: "What is my name?"
           LLM: "I don't have access to personal information such as your name."
                 ↑ LLM has COMPLETELY FORGOTTEN Turn 1
```

To make an LLM behave like a stateful chatbot, we need to explicitly pass the conversation history back to the model on every new call. LangChain provides three strategies for doing this, each with different trade-offs around token usage and accuracy.

---

### 3a. Conversation Buffer Memory

#### The Idea

The simplest memory strategy is **brute-force**: before sending the user's new question to the LLM, prepend the entire conversation history to the prompt. You are essentially reminding the LLM of everything that was said, every single time.

```
Turn 2 Prompt (with buffer memory):
┌────────────────────────────────────────────────────┐
│ <s><|user|>                                        │
│ Current conversation:                              │
│ Human: My name is Maarten. What is 1+1?            │
│ AI: Hello Maarten! The answer to 1 + 1 is 2.       │ ← Full history injected
│                                                    │
│ What is my name?<|end|>                            │ ← New question appended
│ <|assistant|>                                      │
└────────────────────────────────────────────────────┘
```

The LLM now has the full transcript in its context window and can correctly answer "Your name is Maarten."

#### Implementation

The updated prompt template needs a new variable `{chat_history}` to hold the conversation so far:

```python
from langchain.memory import ConversationBufferMemory

# Updated template with chat_history placeholder
template = """<s><|user|>Current conversation:{chat_history}

{input_prompt}<|end|>
<|assistant|>"""

prompt = PromptTemplate(
    template=template,
    input_variables=["input_prompt", "chat_history"]
)

# Memory object — stores history under the key "chat_history"
memory = ConversationBufferMemory(memory_key="chat_history")

# Chain everything together
llm_chain = LLMChain(
    prompt=prompt,
    llm=llm,
    memory=memory
)
```

When you call `llm_chain.invoke({"input_prompt": "What is my name?"})`, LangChain automatically: (1) retrieves the stored history from `memory`, (2) fills `{chat_history}` in the template, (3) calls the LLM, (4) stores the new exchange back into `memory` for the next turn.

```
Chain with Buffer Memory:
                ┌───────────────────────┐
  History ─────▶│  {conversation_history}│
                │                       │──▶ [LLM] ──▶ "Your name is Maarten."
  "What is      │  {user_prompt}        │
   my name?" ──▶│                       │
                └───────────────────────┘
```

**Pro:** Dead simple, and the LLM has access to every word that was ever said.  
**Con:** The prompt grows with every turn. After a long conversation, you will hit the model's context window limit (2048 tokens for our Phi-3 setup), and the chain will break.

#### Under the Hood — What LangChain Actually Does

A natural question here is: how does LangChain actually implement this? Is there anything clever happening — a database lookup, a special memory architecture? The answer is surprisingly mundane: it is literally string concatenation, nothing more.

Internally, the memory object maintains a Python list of `HumanMessage` and `AIMessage` objects. After every turn, `save_context` appends the new pair to that list. Before every turn, `load_memory_variables` joins that list into one big string and returns it as the `{chat_history}` value. LangChain then slots that string into the prompt template. That is the entire mechanism.

Here is exactly what the LLM sees on the wire for a three-turn conversation where you ask "What's my name?":

```
The following is a friendly conversation between a human and an AI.

Current conversation:
Human: Hi, my name is Sanjoy
AI: Hello Sanjoy! Nice to meet you.
Human: I love NLP.
AI: That is a fascinating field!
Human: What is my name?
AI:
```

The LLM does not "remember" anything in any persistent sense. It re-reads the injected transcript from scratch on every call. The model has no idea this is a multi-turn conversation — it sees a document that looks like a conversation script and completes the next line. This is why the mental model to keep forever is:

> **LLMs are stateless. Every API call is independent. "Memory" in LangChain is a client-side illusion — it works by re-injecting past conversation text into each new prompt. The LLM does not remember; it re-reads.**

The three mechanical steps LangChain runs on every `.invoke()` call:

```
Step 1 — load_memory_variables()
  memory.chat_history → ["Human: Hi...", "AI: Hello...", "Human: I love NLP", "AI: That is..."]
  → joined into one string: "Human: Hi...\nAI: Hello...\n..."

Step 2 — fill the prompt template
  {chat_history} ← the joined string above
  {input_prompt} ← the new user message

Step 3 — call the LLM with the assembled prompt
  → LLM generates the next line
  → save_context() appends the new exchange to the list
```

This architecture has one direct consequence: **context window size is the only limit on memory length.** A model with a 4K context window forgets earlier conversation far faster than one with a 128K context window — not because one has better memory, but because it can fit more history text in a single prompt. When the history grows too large to fit, LangChain will either truncate silently or raise an error — which is exactly why the windowed and summary variants below exist.

#### Does the History Use Special Tokens Like `<|user|>`?

No — and this is an important subtlety. The special tokens (`<s>`, `<|user|>`, `<|end|>`, `<|assistant|>`) appear **only once**, in the outer wrapper of the prompt template. They tell Phi-3 where the current user turn begins and ends, and where the model should start generating. The conversation history injected into `{chat_history}` uses plain text labels — **"Human:"** and **"AI:"** — with no special tokens at all.

LangChain internally formats each stored exchange as `Human: <message>\nAI: <response>` and concatenates them into a single block of plain text. That entire block is what gets substituted into `{chat_history}`.

So the full assembled prompt for Turn 2 looks like this:

```
<s><|user|>Current conversation:
Human: Hi! My name is Maarten. What is 1 + 1?     ← plain text, no special tokens
AI: Hello Maarten! The answer to 1 + 1 is 2.       ← plain text, no special tokens

What is my name?<|end|>                             ← outer wrapper ends here
<|assistant|>                                       ← model generates from here
```

Think of it this way: the history is "quoted text" that the user is showing to the model — it is *part of the user's message*, and so it lives entirely inside the `<|user|>...<|end|>` block. The model reads it as context, not as additional turns of the conversation format it was trained on. Using special tokens inside the history would confuse the model, because it would see a nested `<|assistant|>` marker mid-prompt and lose track of whose turn it is.

---

### 3b. Windowed Conversation Buffer

#### The Idea

Instead of keeping the *entire* history, keep only the **last k exchanges**. Older conversations are quietly discarded. This bounds the token count at a predictable level, no matter how long the conversation runs.

```python
from langchain.memory import ConversationBufferWindowMemory

# k=2 means: only retain the last 2 Human/AI exchange pairs
memory = ConversationBufferWindowMemory(k=2, memory_key="chat_history")
```

#### Dry-Run: What Gets Remembered

```
Conversation so far:
  Turn 1: Human: "My name is Maarten and I am 33 years old. What is 1+1?"
          AI:    "Hello Maarten! 1+1=2."
  Turn 2: Human: "What is 3+3?"
          AI:    "3+3=6."
  Turn 3: Human: "What is my name?"   ← 3rd turn, k=2 means Turn 1 is now forgotten

Memory buffer at Turn 3 (only last 2 turns retained):
  [Turn 2] Human: "What is 3+3?"
           AI:    "3+3=6."
  [Turn 3] Human: "What is my name?" ← current question

Turn 1 is gone → LLM can recall the name "Maarten" (mentioned in Turn 2 context? No.)
Actually it CANNOT recall the name — Turn 1 was evicted.

Turn 4: Human: "What is my age?"   ← now Turn 2 is also evicted
         LLM: "I don't know your age." ← age was only in Turn 1, now gone
```

This demonstrates the window's sharp cut-off: information mentioned exactly `k+1` turns ago is completely lost. **Pro:** Predictable token usage. **Con:** No way to compress or preserve older information — it is simply deleted.

---

### 3c. Conversation Summary Memory

#### The Idea

The third strategy is more sophisticated. Instead of keeping a verbatim transcript of the history, we use a **second LLM call** to *summarise* the conversation so far into a compact paragraph. This summary is then passed to the main LLM as the `{chat_history}`, rather than the raw transcript.

The insight is that a summary preserves the *meaning* of a conversation while consuming far fewer tokens than the full transcript. A ten-turn conversation that would consume 1000 tokens might be summarised in 50 tokens with minimal loss of important context.

```
Conversation Summary Memory Pipeline:

  Previous turns ─────▶ [Summariser LLM] ─────▶ "Summary: Maarten asked
                                                   about 1+1, was told 2."
                                                        │
                                              ┌─────────┴──────────┐
                                              │   Prompt Template  │
                                              │  history = summary │
                                              │  + new question    │
                                              └─────────┬──────────┘
                                                        │
                                                   [Main LLM]
                                                        │
                                                   "Your name is Maarten."
```

There are now **two LLM calls per user turn**: one to update the summary, one to answer the question. This is a genuine trade-off — more compute per turn, but the history stays bounded in size indefinitely.

#### Implementation

First, define a summarisation prompt:

```python
from langchain.memory import ConversationSummaryMemory

# The summariser prompt takes the old summary + new lines and produces a new summary
summary_prompt_template = """<s><|user|>Summarize the conversations and update
with the new lines.

Current summary:
{summary}

new lines of conversation:
{new_lines}

New summary:<|end|>
<|assistant|>"""

summary_prompt = PromptTemplate(
    input_variables=["new_lines", "summary"],
    template=summary_prompt_template
)

# Memory that uses an LLM to summarise
memory = ConversationSummaryMemory(
    llm=llm,
    memory_key="chat_history",
    prompt=summary_prompt
)

# Main chain (same structure as before)
llm_chain = LLMChain(prompt=prompt, llm=llm, memory=memory)
```

#### Dry-Run: Watching the Summary Evolve

```
Turn 1: Human: "Hi! My name is Maarten. What is 1+1?"
        AI:    "Hello Maarten! The answer to 1+1 is 2."

  Summariser runs:
    Input:  summary="" (empty), new_lines="Human: Hi! My name is Maarten..."
    Output: "Maarten asked about the sum of 1+1, which the AI answered as 2."
  memory["chat_history"] = "Maarten asked about the sum of 1+1..."  ← 12 tokens

Turn 2: Human: "What is my name?"
  Prompt to main LLM:
    chat_history = "Maarten asked about the sum of 1+1, which the AI answered as 2."
    new question = "What is my name?"
  Main LLM: "In this context, your name was referred to as Maarten."

  Summariser runs again:
    Input:  summary="Maarten asked about 1+1...", new_lines="Human: What is my name?..."
    Output: "Maarten (AI: told 2) asked their name; AI said Maarten."
  memory["chat_history"] = updated summary  ← still small

Turn 3: Human: "What was the first question I asked?"
  Main LLM sees the summary and correctly responds:
  "The first question you asked was 'What is 1+1?'"
```

**Key gotcha:** The summary is a *paraphrase*, not a verbatim record. If the user gives you a very specific number like "My phone number is 867-5309", a summary might compress this to "The user shared their contact information" — losing the actual digits. Summary memory is excellent for the *gist* of a conversation, but unreliable for precise facts that must be recalled word-for-word.

The analogy here is the difference between an audio recording and handwritten lecture notes. The notes capture the main ideas beautifully but leave out the exact wording. The audio recording captures everything but takes up far more storage.

---

### 3d. Memory Type Comparison

| Memory Type | How It Works | Pros | Cons |
|---|---|---|---|
| **Conversation Buffer** | Full transcript in every prompt | Simplest; zero information loss | Token count grows unbounded; needs large context window |
| **Windowed Buffer** | Last $k$ exchanges in prompt | Predictable token budget | Hard cutoff — old info deleted, not compressed |
| **Conversation Summary** | LLM summarises history before each call | Handles arbitrarily long conversations | Extra LLM call per turn; paraphrasing can lose specific facts |

The right choice depends on your application. For a short customer service interaction, buffer memory is fine. For a long-running research assistant, summary memory is better. For a fixed-context deployment where you need the most *recent* turns to be perfectly preserved, windowed buffer is the right tool.

---

## 4. Agents: Creating a System of LLMs

### The Big Picture

Everything we have built so far — chains, memory, prompt templates — follows a **fixed recipe**: the programmer defines the steps, and the LLM executes each one in order. The LLM does not decide what to do; you tell it exactly what to do.

**Agents** break this constraint. An agent uses an LLM not just to generate text, but to *make decisions* — specifically, to decide which action to take next and which tool to use. The programmer no longer defines a fixed sequence of steps. Instead, they give the agent a goal and a set of tools, and the agent figures out the rest autonomously.

This is why agents are one of the most exciting developments in applied LLM research. They transform a text generator into a reasoning system that can interact with the world.

---

### 4a. What are Agents?

An agent has two essential components:

**Tools** are external functions the agent can call. A tool could be a web search engine, a calculator, a database query, a weather API, or any other function that returns information or takes an action. Tools extend what the LLM can do beyond generating text — they let it interact with reality.

**The agent type** determines *how* the LLM decides which tool to use and in what order. Different agent types implement different decision-making strategies.

The power of tools is illustrated by a simple example: LLMs are notoriously bad at arithmetic. Ask an LLM "What is $47 / 12 \times 3.14$?" and it will often hallucinate a plausible-looking but wrong answer. Give the same LLM a calculator tool, and it can invoke the calculator, get the exact answer `12.2983`, and report that back correctly.

```
Without Tools:                    With Tools:
                                  
User: "47 / 12 × 3.14?"          User: "47 / 12 × 3.14?"
           │                                   │
       [LLM]                               [LLM]
           │                                   │ decides: "use calculator"
   "7.34"  ← WRONG!                            │
                                        [Calculator]
                                               │ 47/12×3.14 = 12.2983
                                               │
                                           [LLM]
                                               │
                                       "12.2983"  ← CORRECT
```

---

### 4b. The ReAct Framework: Reasoning + Acting

The dominant strategy for building agents is the **ReAct** framework (Yao et al., 2022). ReAct combines two capabilities that individually are not enough:

**Reasoning** alone: LLMs are excellent at reasoning in text — they can plan, infer, and evaluate. But reasoning without the ability to act leaves the model trapped inside its own knowledge, which has a training cutoff and contains no real-time information.

**Acting** alone: Blindly calling tools without reasoning about whether they are needed, in what order, or how to interpret their output, produces chaotic and unreliable behaviour.

ReAct merges both. It instructs the LLM to follow a repeating cycle of three steps until it reaches a final answer:

1. **Thought** — The LLM reasons in plain text about what it should do next: *"I need to find the current price of a MacBook Pro before I can convert it to EUR."*
2. **Action** — The LLM specifies a tool call: *"Search[current price MacBook Pro USD]"*
3. **Observation** — The tool runs and returns its result, which the LLM reads: *"The current price is $2,249."*

The LLM then enters another Thought step, using the observation to inform its next decision. This continues until the LLM determines it has enough information to write a Final Answer.

```
                      ReAct Agent Loop
                      ────────────────

User Question: "What is the MacBook Pro price in USD,
                and how much is that in EUR at 0.85 rate?"
                              │
                         ┌────▼─────┐
                         │  Thought  │  "I should search the web for the price."
                         └────┬─────┘
                              │
                         ┌────▼─────┐
                         │  Action   │  Search["current price MacBook Pro"]
                         └────┬─────┘
                              │
                    ┌─────────▼─────────┐
                    │  Tool (DuckDuckGo) │  returns "$2,249"
                    └─────────┬─────────┘
                              │
                         ┌────▼──────────┐
                         │  Observation  │  "The price is $2,249."
                         └────┬──────────┘
                              │
                         ┌────▼─────┐
                         │  Thought  │  "Now I need to calculate 2249 × 0.85"
                         └────┬─────┘
                              │
                         ┌────▼─────┐
                         │  Action   │  Calculator[2249 × 0.85]
                         └────┬─────┘
                              │
                    ┌─────────▼─────────┐
                    │  Tool (Calculator) │  returns "1911.65"
                    └─────────┬─────────┘
                              │
                         ┌────▼──────────┐
                         │  Observation  │  "2249 × 0.85 = 1911.65"
                         └────┬──────────┘
                              │
                         ┌────▼───────────────┐
                         │  Thought (final)    │  "I now know the final answer."
                         └────┬───────────────┘
                              │
                    ┌─────────▼────────────────────────────────────────┐
                    │  Final Answer: "MacBook Pro is $2,249 USD,       │
                    │                which equals approx. €1,911.65."  │
                    └──────────────────────────────────────────────────┘
```

The crucial thing about ReAct is that the Thought steps are *generated text by the LLM itself*. The LLM is narrating its own reasoning process. This means the agent is transparent — you can see exactly why it took each action by reading its thoughts.

---

### 4c. ReAct in LangChain

#### Why a Stronger LLM is Needed

The local Phi-3 model we used for chains and memory is good for straightforward question-answering, but the ReAct loop demands more: the model must consistently follow a rigid Thought/Action/Observation format across many turns, correctly identify which tool to use, format tool calls precisely, and interpret tool outputs accurately. Smaller local models often fail to follow this structure reliably. For this example, the book uses OpenAI's GPT-3.5-turbo, which handles the format consistently:

```python
import os
from langchain_openai import ChatOpenAI

os.environ["OPENAI_API_KEY"] = "MY_KEY"
openai_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
# temperature=0 → deterministic; we want consistent tool-call formatting
```

#### The ReAct Prompt Template

The agent needs a specially crafted prompt that tells the LLM exactly what format to follow. This prompt has four placeholder variables:

```python
react_template = """Answer the following questions as best you can.
You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
```

The **`{agent_scratchpad}`** deserves special attention. It is the agent's *notepad* — the accumulating text of all the Thought/Action/Observation steps generated so far in the current run. Think of it like a mathematician's scratch paper: every intermediate step gets written down there, and the LLM reads it on every new Thought step to know what it has already tried.

On the first call, `{agent_scratchpad}` is empty and the LLM writes its first Thought. After the first tool call returns an Observation, the scratchpad now contains:

```
Thought: I should search the web for the price.
Action: duckduck
Action Input: "current price MacBook Pro in USD"
Observation: The price is $2,249.
Thought:                                         ← LLM writes here next
```

This is passed back to the LLM as context, so it can continue the chain of reasoning without losing its place.

#### Defining the Tools

```python
from langchain.agents import load_tools, Tool
from langchain.tools import DuckDuckGoSearchResults

# Web search tool
search = DuckDuckGoSearchResults()
search_tool = Tool(
    name="duckduck",
    description="A web search engine. Use this for general queries about current facts.",
    func=search.run,
)

# Math tool (wraps an LLM-powered calculator)
tools = load_tools(["llm-math"], llm=openai_llm)
tools.append(search_tool)
```

#### Creating and Running the Agent

```python
from langchain.agents import AgentExecutor, create_react_agent

prompt = PromptTemplate(
    template=react_template,
    input_variables=["tools", "tool_names", "input", "agent_scratchpad"]
)

# create_react_agent wires the LLM, tools, and prompt into a ReAct agent
agent = create_react_agent(openai_llm, tools, prompt)

# AgentExecutor handles the Thought/Action/Observation loop automatically
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,            # print intermediate steps to console
    handle_parsing_errors=True
)
```

Running the agent with `verbose=True` lets you watch the entire ReAct loop in real time:

```python
agent_executor.invoke({
    "input": "What is the current price of a MacBook Pro in USD? "
             "How much would it cost in EUR if the exchange rate is 0.85 EUR for 1 USD."
})
```

The console output will show each Thought, Action, and Observation step, followed by the final answer — making it easy to debug whether the agent is using tools correctly and reasoning soundly.

#### The Double-Edged Sword of Autonomy

Agents are impressively capable, but their autonomy comes with a genuine risk. When the agent makes multiple tool calls and reasoning steps without any human reviewing the intermediate outputs, there is no one to catch an error mid-stream. The agent might misinterpret a search result, use the wrong formula in the calculator, or confidently produce a plausible-sounding but incorrect final answer.

This is why production agent systems need careful design: you might want the agent to cite its sources (return the URL of the page where it found the price), implement a human-in-the-loop step for critical decisions, or run the agent's output through a verification step. The framework is powerful, but its reliability depends entirely on the quality of the underlying LLM and the care with which the tools and prompts are designed.

---

## Key Takeaways

**Quantization** reduces the bit precision of model weights (from 32-bit to 16-bit, 8-bit, or 4-bit), shrinking memory requirements dramatically with only modest accuracy loss — 4-bit is the practical minimum before quality degrades noticeably.

**Chains** connect modular components (prompt templates, memory, output parsers) to an LLM using LangChain's pipe operator `|`. Complex tasks should be decomposed into sequential sub-chains rather than crammed into one enormous prompt.

**Instruct models require special tokens** to know when to generate a response. Without tokens like `<|user|>` and `<|assistant|>`, the model produces an empty string. `PromptTemplate` automates this wrapping.

**LLMs are stateless by default.** Memory must be injected explicitly. Conversation Buffer keeps the full transcript, Windowed Buffer keeps only the last $k$ turns, and Summary Memory compresses history via a second LLM call — each trades token cost for information completeness.

**Agents + ReAct** turn LLMs from text generators into autonomous decision-makers. The Thought → Action → Observation loop lets the model reason about which tool to use, call it, observe the result, and continue reasoning — all without programmer-defined steps. Power and risk scale together: always design for transparency and verification.
