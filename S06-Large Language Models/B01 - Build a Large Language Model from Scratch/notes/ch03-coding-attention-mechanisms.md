# Chapter 3: Coding Attention Mechanisms

## Table of Contents

1. [The Problem with Modeling Long Sequences](#1-the-problem-with-modeling-long-sequences)
2. [Capturing Data Dependencies with Attention Mechanisms](#2-capturing-data-dependencies-with-attention-mechanisms)
3. [Attending to Different Parts of the Input with Self-Attention](#3-attending-to-different-parts-of-the-input-with-self-attention)
4. [Implementing Self-Attention with Trainable Weights](#4-implementing-self-attention-with-trainable-weights)
5. [Hiding Future Words with Causal Attention](#5-hiding-future-words-with-causal-attention)
6. [Extending Single-Head Attention to Multi-Head Attention](#6-extending-single-head-attention-to-multi-head-attention)

# 1: The Problem with Modeling Long Sequences

## What This Section Is Really About

Section 3.1 is not about LLMs directly — it is about understanding the **problem that LLMs are solving**. Before you can appreciate why self-attention exists, you need to understand what failed before it.

The motivating example throughout is **language translation** — specifically translating German to English. It is a clean, concrete task where the limitations of earlier approaches become very visible.

---

## Why Word-by-Word Translation Fails

The most naive approach to translation is to translate each word individually in order. This completely fails in practice.

Consider the German sentence:

```
Kannst  du   mir   helfen  diesen  Satz  zu  uebersetzen
Can     you  me    help    this    sentence to  translate
```

A word-by-word mapping produces: **"Can you me help this sentence to translate"**

The correct English translation is: **"Can you help me to translate this sentence"**

```
┌──────────────────────────────────────────────────────────────────┐
│                WHY WORD-BY-WORD FAILS                            │
│                                                                  │
│  German word order:                                              │
│  [Kannst] [du] [mir] [helfen] [diesen] [Satz] [zu] [uebersetzen]│
│     ↓       ↓     ↓      ↓       ↓       ↓     ↓       ↓        │
│  [Can]  [you]  [me] [help]  [this] [sentence][to] [translate]   │
│                                                                  │
│  Result: "Can you me help this sentence to translate"  ✗         │
│                                                                  │
│  Correct: "Can you help me to translate this sentence" ✓         │
│                                                                  │
│  The problem:                                                    │
│  ● German puts the verb at the END of the clause                 │
│  ● "mir" (me) comes before "helfen" (help) in German,           │
│    but after it in English                                       │
│  ● You cannot know the correct English word order               │
│    without reading the ENTIRE German sentence first             │
└──────────────────────────────────────────────────────────────────┘
```

This is not a quirk of German. Almost every language pair has structural differences that make word-by-word translation incorrect. Some words only make sense in the context of what comes later. Some words have multiple meanings that only become clear from context. Grammatical gender, verb conjugation, and idiomatic expressions all require understanding the full sentence before producing any translation.

**The fundamental requirement:** a translation model must read and understand the complete source sentence before it can reliably produce even the first output word.

---

## The Encoder-Decoder Architecture — The Pre-Attention Solution

To handle this requirement, researchers built neural networks with two distinct components:

- An **encoder** that reads the full source sentence and builds an internal representation of its meaning
- A **decoder** that takes that internal representation and generates the translated output, one token at a time

```
┌──────────────────────────────────────────────────────────────────┐
│              ENCODER-DECODER ARCHITECTURE — OVERVIEW             │
│                                                                  │
│                      SOURCE SENTENCE                             │
│     "Kannst  du   mir   helfen  diesen  Satz  zu  uebersetzen"  │
│         ↓     ↓    ↓      ↓       ↓      ↓    ↓       ↓         │
│     ┌────────────────────────────────────────────────────┐       │
│     │                    ENCODER                         │       │
│     │  Reads entire source sentence, left to right       │       │
│     │  Builds a compressed internal representation       │       │
│     └────────────────────────┬───────────────────────────┘       │
│                              │                                   │
│                         hidden state                             │
│                    (the "memory" of the encoder)                 │
│                              │                                   │
│     ┌────────────────────────▼───────────────────────────┐       │
│     │                    DECODER                         │       │
│     │  Takes the hidden state from the encoder           │       │
│     │  Generates the translation, one token at a time    │       │
│     └────────────────────────────────────────────────────┘       │
│              ↓          ↓       ↓     ↓    ↓                    │
│            "Can"      "you"  "help"  "me"  ...                  │
│                      TARGET SENTENCE (generated)                 │
└──────────────────────────────────────────────────────────────────┘
```

This architecture was implemented using **Recurrent Neural Networks (RNNs)** — a class of neural network designed specifically for sequential data where each step's output feeds into the next.

---

## What Is an RNN and Why Was It Used?

An RNN is a type of neural network where the output from each step is passed as additional input to the next step. This creates a form of **memory** — the network can accumulate information as it reads through a sequence.

You do not need to understand RNN internals deeply for this book. What matters is the concept of the **hidden state**.

### **The Hidden State — The RNN's Running Memory**

At each step, the RNN produces a **hidden state** — a vector of numbers that captures what the network has "understood" so far. Think of it as a continuously updated notepad.

```
┌──────────────────────────────────────────────────────────────────┐
│              HOW THE ENCODER RNN PROCESSES A SENTENCE            │
│                                                                  │
│   Input token:    "Kannst"   "du"     "mir"    "helfen"  ...     │
│                      ↓         ↓        ↓         ↓             │
│                   ┌─────┐   ┌─────┐  ┌─────┐  ┌─────┐          │
│   RNN step:       │ RNN │   │ RNN │  │ RNN │  │ RNN │  ...      │
│                   └──┬──┘   └──┬──┘  └──┬──┘  └──┬──┘          │
│                      │   ↗     │   ↗    │   ↗    │              │
│   Hidden state:    [h1] ──→  [h2] ──→ [h3] ──→ [h4] ──→ ...    │
│                                                                  │
│  Each hidden state hi carries:                                   │
│  ● Everything the network learned from token i                   │
│  ● Plus everything it remembered from tokens 1 through i-1      │
│                                                                  │
│  The FINAL hidden state h_final carries (in theory):            │
│  ● The meaning of the entire source sentence compressed          │
│    into a single fixed-size vector                               │
└──────────────────────────────────────────────────────────────────┘
```

As each new token is processed, the RNN **updates its hidden state**. The new hidden state is a function of the current token and the previous hidden state. Information flows forward through the sequence.

### **A Concrete Mental Model for Hidden States**

Think of the hidden state as a person reading a sentence one word at a time and continuously updating their notes:

```
Reading "Kannst":
  Notes: [Something about ability or permission is being discussed]

Reading "Kannst du":
  Notes: [A question is being asked — "du" makes it second person]

Reading "Kannst du mir":
  Notes: [The question involves me (the speaker) — "mir" is dative]

Reading "Kannst du mir helfen":
  Notes: [The question is asking for help]

Reading full sentence:
  Notes: [A request for help translating a specific sentence]
```

Each hidden state is a numerical vector encoding this evolving "notes" state. By the end of the sentence, the final hidden state is supposed to capture the full meaning.

---

## The Decoder — Generating the Translation

Once the encoder has finished reading the source sentence, the **final hidden state** is passed to the decoder. The decoder then generates the translation one token at a time, also using an RNN.

```
┌──────────────────────────────────────────────────────────────────┐
│                     HOW THE DECODER WORKS                        │
│                                                                  │
│   Receives h_final from encoder                                  │
│         ↓                                                        │
│   ┌─────────────────────────────────────────────────────┐        │
│   │  Step 1: Use h_final → predict first token "Can"    │        │
│   │  Step 2: Use "Can" + updated hidden state → "you"   │        │
│   │  Step 3: Use "you" + updated hidden state → "help"  │        │
│   │  Step 4: Use "help" + updated hidden state → "me"   │        │
│   │  ...and so on until a stop token is generated       │        │
│   └─────────────────────────────────────────────────────┘        │
│                                                                  │
│  h_final  →  [RNN] → "Can"  →  [RNN] → "you"  →  [RNN] → ...   │
│                ↑                  ↑                  ↑           │
│           (from encoder)     (previous word)    (previous word)  │
└──────────────────────────────────────────────────────────────────┘
```

The decoder's hidden state is updated at each step, just like the encoder's. But the decoder is also fed the previously generated token as an input — so each new word is predicted based on both what the encoder understood AND what has been generated so far.

### **The Key Constraint — Accessing Earlier Encoder States**

Here is the critical limitation that the book highlights: once the encoder finishes and passes `h_final` to the decoder, **the decoder has no direct access to any of the earlier hidden states** `h1`, `h2`, `h3`, etc.

```
┌──────────────────────────────────────────────────────────────────┐
│              THE DECODER'S LIMITED VIEW                          │
│                                                                  │
│  Encoder produces:  h1  h2  h3  h4  h5  h6  h7  h8  → h_final  │
│                                                                  │
│  What decoder receives:                         ↓ h_final ONLY  │
│                                                                  │
│  What decoder CANNOT see:  h1  h2  h3  h4  h5  h6  h7  h8      │
│                                                                  │
│  If the decoder needs to know what "Kannst" (h1) specifically   │
│  contributed, or what "mir" (h3) meant, it cannot look back.    │
│  All it has is the compressed blend: h_final.                    │
└──────────────────────────────────────────────────────────────────┘
```

This limitation is exactly what section 3.2 addresses by introducing attention mechanisms.

---

## The Analogy — Reading a Book and Taking Notes

To make the whole encoder-decoder setup feel intuitive, think of it this way:

**The Encoder** is like a person reading a German book. As they read, they take notes on a single index card, updating the card continuously. When they finish reading, they hand only the index card to someone else.

**The Decoder** is that someone else, who must write an English translation using only the index card — with no access to the original book.

```
┌──────────────────────────────────────────────────────────────────┐
│                    THE INDEX CARD ANALOGY                        │
│                                                                  │
│  German book (source sentence)                                   │
│  ┌──────────────────────────────────────────────┐               │
│  │ "Kannst du mir helfen diesen Satz             │               │
│  │  zu uebersetzen?"                             │               │
│  └──────────────────────────────────────────────┘               │
│                         │                                        │
│              Person reads, updates index card                    │
│                         │                                        │
│                         ▼                                        │
│  Index card after reading (h_final):                             │
│  ┌──────────────────────────────────────────────┐               │
│  │ [0.23, -0.71, 0.44, 0.88, -0.12, 0.55, ...]  │               │
│  │  (a vector of numbers — fixed size)           │               │
│  └──────────────────────────────────────────────┘               │
│                         │                                        │
│              Translator receives only the card                   │
│                         │                                        │
│                         ▼                                        │
│  English translation produced from card alone:                   │
│  "Can you help me to translate this sentence?"                   │
│                                                                  │
│  For short sentences: the card captures enough.                  │
│  For long sentences: too much is lost in the compression.        │
└──────────────────────────────────────────────────────────────────┘
```

For a short 6-word sentence, the index card might carry enough. For a 40-word sentence with complex dependencies, important information gets lost in compression — and the translation degrades.

---

## Why This Matters — Setting Up the Rest of Chapter 3

Section 3.1 is laying the groundwork. The encoder-decoder RNN architecture was the dominant approach to sequence tasks before 2017. It worked — but it had two fundamental flaws that became more severe as sentence length grew:

**Flaw 1 — The Bottleneck:** All information must pass through a single fixed-size vector (`h_final`). There is a hard limit on how much meaning can be encoded there, regardless of how long or complex the source sentence is.

**Flaw 2 — Loss of Context Over Distance:** In an RNN, early tokens influence the hidden state less and less as more tokens are processed. By the time the encoder reaches the 30th word, the representation of the 1st word has been diluted through 29 sequential updates. Important early information can effectively "fade out."

```
┌──────────────────────────────────────────────────────────────────┐
│                HOW INFLUENCE FADES IN AN RNN                     │
│                                                                  │
│  Sentence: "The cat that chased the mouse ... was tired"         │
│                                                                  │
│   "The"  ──→  h1  ──→  h2  ──→  h3  ──→  ...  ──→  h20         │
│    ↑          ↑                                      ↑           │
│    │          │  "The" strongly influences h1        │           │
│    │                                                 │           │
│    └─────────────────────────────────────────────────┘           │
│         "The" only weakly influences h20 — 19 steps later       │
│                                                                  │
│  This is called the VANISHING INFLUENCE problem.                 │
│  The further a token is from the final state,                    │
│  the weaker its contribution to what the decoder receives.       │
└──────────────────────────────────────────────────────────────────┘
```

These two flaws together motivated the invention of **attention mechanisms** — the topic of the rest of chapter 3. Attention solves both problems by allowing the decoder to directly access all encoder hidden states with a learned weighting, rather than depending on the single compressed `h_final`.

---

## Complete Picture — What Section 3.1 Established

```
┌──────────────────────────────────────────────────────────────────┐
│              WHAT WE LEARNED IN SECTION 3.1                      │
│                                                                  │
│  1. WORD-BY-WORD TRANSLATION FAILS                               │
│     Different languages have different word orders and           │
│     grammatical structures. You need full sentence context       │
│     before producing a translation.                              │
│                                                                  │
│  2. ENCODER-DECODER RNN WAS THE SOLUTION                         │
│     Encoder reads and compresses source → h_final                │
│     Decoder generates target from h_final, one token at a time  │
│                                                                  │
│  3. THE HIDDEN STATE IS THE ENCODER'S "MEMORY"                   │
│     Updated continuously as tokens are processed.               │
│     By the end, h_final is a numerical summary of the sentence. │
│                                                                  │
│  4. BUT h_final IS A BOTTLENECK                                  │
│     Fixed size regardless of sentence length.                   │
│     Decoder has no direct access to earlier encoder states.     │
│     Early tokens lose influence over long sequences.            │
│                                                                  │
│  5. THIS MOTIVATES ATTENTION MECHANISMS                          │
│     What if the decoder could look at ALL encoder hidden         │
│     states and decide for itself which ones matter most?         │
│     → That is exactly what Section 3.2 introduces.              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways for Section 3.1

**Translation is a context problem.** No individual word has a fixed translation — meaning depends on the full surrounding sentence, grammatical structure, and intent.

**Encoder-decoder RNNs were the pre-transformer solution.** The encoder reads the full source and compresses it; the decoder generates the target from that compressed representation.

**The hidden state is the running summary.** At each step, the RNN updates a vector (the hidden state) to reflect everything read so far. The final hidden state is passed to the decoder.

**The single vector is a fundamental bottleneck.** Compressing arbitrarily long sentences into a fixed-size vector inevitably loses information. This problem worsens with sentence length.

**The decoder cannot look back.** Once the encoder hands over `h_final`, the decoder has no way to examine earlier hidden states directly. It must work entirely from the compressed summary.

**These limitations directly motivated attention.** Understanding what was broken makes section 3.2's solution feel necessary and elegant rather than arbitrary.

---

_Next: Section 3.2 — Capturing Data Dependencies with Attention Mechanisms, where the Bahdanau attention fix is introduced and the path from cross-attention to self-attention is traced._

# 2: Capturing Data Dependencies with Attention Mechanisms

## The Problem This Section Solves

Section 3.1 established that language translation cannot be done word-by-word — you need the full context of a sentence to produce a grammatically correct translation. The encoder-decoder RNN architecture was the dominant solution before transformers, but it had a fundamental flaw that attention mechanisms were invented to fix.

Section 3.2 tells that story: what broke, how it was patched, and why the patch eventually led to throwing RNNs out entirely.

---

## A Quick Recap of the Encoder-Decoder RNN

The encoder-decoder RNN works in two phases:

```
┌─────────────────────────────────────────────────────────────────┐
│              ENCODER-DECODER RNN ARCHITECTURE                   │
│                                                                 │
│  ENCODER (reads input left to right, one token at a time)      │
│                                                                 │
│   "Kannst"  →  "du"  →  "mir"  →  "helfen"  →  "..."          │
│      ↓           ↓        ↓          ↓                         │
│    [h1]  →    [h2]  →  [h3]  →    [h4]  →  ...  →  [h_final]  │
│                                                                 │
│     Each hidden state h carries information from all           │
│     previous tokens — but only the FINAL hidden state          │
│     gets passed to the decoder.                                │
│                                                                 │
│                          │                                      │
│                    h_final (the "memory cell")                  │
│                          │                                      │
│                          ↓                                      │
│  DECODER (generates output one token at a time)                │
│                                                                 │
│    [h_final] → "Can" → "you" → "help" → "me" → ...            │
│                                                                 │
│     The decoder only has h_final to work from.                 │
│     It must squeeze the entire source sentence into            │
│     this one fixed-size vector.                                │
└─────────────────────────────────────────────────────────────────┘
```

For short sentences, this worked reasonably well. The problem became severe with longer sentences.

---

## The Core Limitation — The Bottleneck Problem

Imagine trying to summarize an entire novel into a single sentence, then asking someone to write a sequel based only on that summary. No matter how good the summary, information is inevitably lost.

That is exactly what the encoder-decoder RNN does. The encoder reads the full source sentence and compresses it into a single fixed-size vector — the final hidden state. The decoder then tries to reconstruct the meaning from that one vector.

```
┌─────────────────────────────────────────────────────────────────┐
│                   THE INFORMATION BOTTLENECK                    │
│                                                                 │
│  Source sentence (long):                                        │
│  "The quick brown fox jumps over the lazy sleeping dog         │
│   that was resting by the old stone wall near the river"       │
│                                                                 │
│        entire sentence compressed into one vector →  [h_final] │
│                                                                 │
│        ← h_final has FIXED size regardless of sentence length  │
│                                                                 │
│  Problem 1: CAPACITY                                           │
│    A 20-word sentence and a 5-word sentence produce the same   │
│    size vector. The longer sentence must lose information.      │
│                                                                 │
│  Problem 2: DISTANCE                                            │
│    Words at the beginning of a long sentence influence h_final  │
│    very weakly after passing through many RNN steps.            │
│    "The" from position 1 is nearly forgotten by position 20.   │
│                                                                 │
│  Problem 3: NO DIRECT ACCESS                                    │
│    The decoder can never look directly at "fox" or "dog"       │
│    in the source. It only has h_final — the compressed blur.   │
└─────────────────────────────────────────────────────────────────┘
```

The decoder has no way to go back and re-examine specific parts of the input. If it needs the word "fox" to translate a later part of the sentence, it has to hope that information survived the compression into `h_final`.

For short sentences, enough information survives. For long, complex sentences with dependencies spanning many words, performance degraded noticeably. This was the known weakness of encoder-decoder RNNs throughout the early 2010s.

---

## The Fix — Bahdanau Attention (2014)

In 2014, Dzmitry Bahdanau and colleagues proposed a modification that addressed the bottleneck directly. The key insight was simple and powerful:

> Instead of forcing the decoder to work from a single compressed vector, let it **look directly at all encoder hidden states** and decide for itself which ones are relevant at each decoding step.

```
┌─────────────────────────────────────────────────────────────────┐
│              BAHDANAU ATTENTION — THE CORE IDEA                 │
│                                                                 │
│  ENCODER (same as before — reads input, produces hidden states) │
│                                                                 │
│  "Kannst" → "du" → "mir" → "helfen" → "diesen" → "Satz"       │
│      ↓        ↓      ↓        ↓           ↓          ↓         │
│    [h1]    [h2]    [h3]    [h4]        [h5]        [h6]        │
│      ↑        ↑      ↑        ↑           ↑          ↑         │
│      └────────┴──────┴────────┴───────────┴──────────┘         │
│                            │                                    │
│              ALL hidden states are kept and accessible          │
│                            │                                    │
│  DECODER (now has selective access to all encoder states)       │
│                                                                 │
│  When generating "Can":                                         │
│    → Computes a relevance score for each of h1...h6            │
│    → Creates a weighted blend of h1...h6 (a context vector)    │
│    → Uses that context vector to generate "Can"                 │
│                                                                 │
│  When generating "you":                                         │
│    → Computes NEW relevance scores for h1...h6                  │
│    → Creates a DIFFERENT weighted blend                         │
│    → Uses that new context vector to generate "you"             │
│                                                                 │
│  Each decoding step gets its own custom context vector,         │
│  focused on whichever encoder states are most relevant.         │
└─────────────────────────────────────────────────────────────────┘
```

The dotted lines in the book's figure (Figure 3.5) represent these relevance scores — their width is proportional to how much the decoder is attending to each input token for a given output token. Different output tokens attend to different input tokens.

### **What Bahdanau Attention Achieved**

```
┌────────────────────────────────────────────────────────────────┐
│           BEFORE vs AFTER ATTENTION                            │
│                                                                │
│  BEFORE (plain encoder-decoder RNN):                          │
│    Decoder state:  h_final only                               │
│    Information:    Entire source sentence compressed once      │
│    Access pattern: Blind — decoder can't look back            │
│    Long sentences: Performance degrades significantly          │
│                                                                │
│  AFTER (Bahdanau attention):                                   │
│    Decoder state:  h_final + dynamic context vector           │
│    Information:    Selectively pulled from all encoder states  │
│    Access pattern: Flexible — different focus per output token │
│    Long sentences: Performance stays strong                    │
└────────────────────────────────────────────────────────────────┘
```

This was a major breakthrough in neural machine translation. The model could now maintain accuracy on long, complex sentences that had previously been handled poorly.

---

## From Bahdanau to Self-Attention — The Leap to Transformers

Bahdanau attention was designed for **cross-attention** — one sequence (decoder) attending to a different sequence (encoder). It still required the RNN to process tokens sequentially, one at a time.

Three years later, in 2017, researchers at Google published the paper _"Attention Is All You Need"_, introducing the **Transformer architecture**. The key insight of that paper:

> You do not need RNNs at all. Attention mechanisms alone are sufficient — and actually better.

They introduced **self-attention**: instead of one sequence attending to another, a single sequence attends to **itself**. Every token in the input simultaneously computes how much it should attend to every other token in the same sequence.

```
┌─────────────────────────────────────────────────────────────────┐
│          CROSS-ATTENTION vs SELF-ATTENTION                      │
│                                                                 │
│  CROSS-ATTENTION (Bahdanau, 2014):                             │
│                                                                 │
│    Source: "Kannst du mir helfen"  (encoder)                   │
│                                                                 │
│         ↕  ↕  ↕  ↕  (attention scores computed here)           │
│                                                                 │
│    Target: "Can you help me"       (decoder)                   │
│                                                                 │
│    Sequence A attends to Sequence B                             │
│    Still requires an RNN to process tokens sequentially         │
│                                                                 │
│  SELF-ATTENTION (Transformers, 2017):                          │
│                                                                 │
│    "Your  journey  starts  with  one  step"                    │
│      ↕      ↕        ↕      ↕     ↕    ↕                       │
│      ↕      ↕        ↕      ↕     ↕    ↕                       │
│    "Your  journey  starts  with  one  step"                    │
│                                                                 │
│    The SAME sequence attends to ITSELF                          │
│    Every token looks at every other token in the same input     │
│    No RNN needed — all tokens processed in parallel             │
└─────────────────────────────────────────────────────────────────┘
```

### **Why Removing the RNN Matters**

RNNs are inherently sequential — to compute `h5`, you must first have computed `h4`, which required `h3`, and so on. This means you **cannot parallelize** across time steps. Long sequences are slow because every step depends on the previous one.

Self-attention has no such constraint. Every token's attention scores can be computed simultaneously across the entire sequence. This makes transformers dramatically faster to train on modern GPU and TPU hardware that excel at parallel computation.

```
┌─────────────────────────────────────────────────────────────────┐
│             RNN vs TRANSFORMER PARALLELISM                      │
│                                                                 │
│  RNN (sequential — must go step by step):                      │
│                                                                 │
│  t=1   t=2   t=3   t=4   t=5   t=6                            │
│  [h1]→[h2]→[h3]→[h4]→[h5]→[h6]                               │
│                                                                 │
│  Cannot start t=3 until t=2 is done.                           │
│  Total time scales with SEQUENCE LENGTH.                        │
│                                                                 │
│  Transformer (parallel — all tokens at once):                  │
│                                                                 │
│  t=1   t=2   t=3   t=4   t=5   t=6                            │
│  [x1]  [x2]  [x3]  [x4]  [x5]  [x6]                          │
│    ↘↗    ↘↗    ↘↗    ↘↗    ↘↗    ↘↗                           │
│  All attention scores computed simultaneously.                  │
│  Total time does NOT scale with sequence length.                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Self-Attention — The Definition

The book gives a precise definition worth understanding carefully:

> **Self-attention** is a mechanism that allows each position in the input sequence to consider the relevancy of, or "attend to," all other positions in the same sequence when computing the representation of a sequence.

Breaking this down:

**"each position in the input sequence"** — every single token, not just a special query token. All tokens simultaneously compute their own attention over the full sequence.

**"consider the relevancy of all other positions"** — for every token, you compute a relevance score against every other token. The score tells you how much information to take from each.

**"in the same sequence"** — this is what makes it _self_-attention. The query, the keys, and the values all come from the same input sequence, not from a separate sequence.

**"when computing the representation"** — the output is a new, enriched representation of each token. The raw input embedding gets replaced by a context vector that carries information from the whole sequence.

---

## The Conceptual Journey of This Chapter

Section 3.2 is a bridge section — it explains _why_ we need what's coming. Here is the full conceptual lineage:

```
┌─────────────────────────────────────────────────────────────────┐
│                  THE ROAD TO SELF-ATTENTION                     │
│                                                                 │
│  1. Word-by-word translation fails                             │
│     → Need to understand full sentence context                 │
│     (Section 3.1)                                              │
│                        │                                        │
│                        ▼                                        │
│  2. Encoder-decoder RNN reads full sentence                    │
│     → But compresses it into a single vector (bottleneck)      │
│     → Works for short sentences, fails for long ones           │
│     (Section 3.2, first half)                                  │
│                        │                                        │
│                        ▼                                        │
│  3. Bahdanau attention lets decoder look at all encoder states  │
│     → No more bottleneck — direct access at each decoding step  │
│     → Still uses RNN → still sequential                        │
│     (Section 3.2, second half)                                 │
│                        │                                        │
│                        ▼                                        │
│  4. Self-attention: remove RNN entirely                        │
│     → Sequence attends to itself                               │
│     → Fully parallel — all tokens processed at once            │
│     → Foundation of the Transformer and all modern LLMs        │
│     (Section 3.3 onwards)                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## A Small Concrete Example of the Bottleneck

To make the bottleneck feel real rather than abstract, consider this:

Suppose you have a sentence of 10 tokens and a hidden state of size 4 (a 4-dimensional vector). You need to compress 10 tokens × their full meaning into just 4 numbers. That is an enormous amount of information to pack into such a small space.

```
10 tokens of information → compress into → [0.83, -0.21, 0.55, 0.12]

The decoder now has only these 4 numbers.
It must reconstruct which words were in the source, their order,
their grammatical roles, their semantic meanings, and their
relationships to each other — from 4 numbers.

With attention, the decoder can instead ask:
"For this particular output word, which of the 10 input
hidden states is most relevant?" and look at them directly.
No compression required.
```

In real models, hidden states are typically 512 or 768 dimensions, not 4. But the principle holds — you are still forcing variable-length, arbitrarily complex sentences into a fixed-size vector. Longer and more complex sentences suffer more.

---

## Key Takeaways for Section 3.2

**RNNs solved the word-by-word problem but created a new one.** The encoder compresses the full source sentence into a single fixed-size hidden state, losing information about long-distance relationships.

**Bahdanau attention (2014) broke the bottleneck.** By letting the decoder directly access all encoder hidden states with a learned weighting, the model no longer depended on a single compressed vector. Each decoding step could selectively focus on the relevant parts of the input.

**Three years later, researchers showed that RNNs were unnecessary.** Self-attention in the Transformer architecture processes all positions in parallel and achieves better results than RNN-based attention on most tasks.

**Self-attention is the mechanism this chapter implements.** Every modern LLM — GPT-2, GPT-3, GPT-4, LLaMA — is built on self-attention. Understanding why it exists (the chain of problems it solved) makes the mechanics in sections 3.3 onward much easier to reason about.

---

# 3: Attending to Different Parts of the Input with Self-Attention

## What Is Self-Attention and Why Does It Exist?

Before jumping into mechanics, it's worth asking: what problem does self-attention actually solve?

When you read the sentence **"The animal didn't cross the street because it was too tired"** — what does "it" refer to? You, as a human, immediately know "it" refers to "animal." But a raw word embedding for "it" contains no information about that relationship. It's just a vector representing the word "it" in isolation.

Self-attention gives every token a way to **look at every other token in the same sentence** and decide how relevant each one is. The result is a new, enriched representation — called a **context vector** — that carries information about the whole sentence, not just the individual word.

The "self" in self-attention means the sequence is attending to **itself** — unlike cross-attention (used in translation), where one sequence attends to a different sequence.

```
┌──────────────────────────────────────────────────────────────────┐
│               WHAT SELF-ATTENTION ACCOMPLISHES                   │
│                                                                  │
│  Raw embeddings (what we START with):                           │
│  "Your"    → [0.43, 0.15, 0.89]  ← just the word in isolation  │
│  "journey" → [0.55, 0.87, 0.66]  ← just the word in isolation  │
│  "starts"  → [0.57, 0.85, 0.64]  ← just the word in isolation  │
│  ...                                                             │
│                                                                  │
│  Context vectors (what we END with):                            │
│  z1 → [0.44, 0.59, 0.58]  ← "Your" enriched with sentence info │
│  z2 → [0.44, 0.65, 0.57]  ← "journey" enriched with context    │
│  z3 → [0.44, 0.65, 0.57]  ← "starts" enriched with context     │
│  ...                                                             │
│                                                                  │
│  Each context vector is a BLEND of all input vectors,           │
│  weighted by how relevant each word is to the current token.    │
└──────────────────────────────────────────────────────────────────┘
```

---

## The Setup — Inputs for the Whole Section

Section 3.3 uses a single sentence with six tokens, each already converted into a **3-dimensional embedding vector** (kept small to fit the page):

```python
import torch

inputs = torch.tensor(
    [[0.43, 0.15, 0.89],  # Your     (x1)
     [0.55, 0.87, 0.66],  # journey  (x2)
     [0.57, 0.85, 0.64],  # starts   (x3)
     [0.22, 0.58, 0.33],  # with     (x4)
     [0.77, 0.25, 0.10],  # one      (x5)
     [0.05, 0.80, 0.55]]  # step     (x6)
)
# shape: (6, 3)  →  6 tokens, each with a 3-dimensional embedding
```

Section 3.3.1 focuses on computing the context vector for **x2 ("journey")** as the main example before generalizing to all tokens in 3.3.2.

---

## 3.3.1 — A Simple Self-Attention Mechanism Without Trainable Weights

### **The Three-Step Process**

Computing a context vector for any query token always follows the same three steps:

```
┌────────────────────────────────────────────────────────────────┐
│                  THE THREE STEPS                               │
│                                                                │
│  Step 1: Compute attention SCORES                              │
│          → dot product of query token with every input token   │
│          → raw numbers, no constraints on range                │
│                                                                │
│  Step 2: Compute attention WEIGHTS                             │
│          → normalize scores with softmax                       │
│          → values are now between 0 and 1, sum to 1           │
│                                                                │
│  Step 3: Compute CONTEXT VECTOR                                │
│          → weighted sum of all input vectors                   │
│          → enriched representation of the query token          │
└────────────────────────────────────────────────────────────────┘
```

---

### **Step 1 — Attention Scores: How Similar Is Each Token to the Query?**

We designate **x2 ("journey")** as our query. We want to know how relevant every other token (including x2 itself) is to "journey."

The way we measure relevance is the **dot product** — a number that tells you how similar two vectors are. Two vectors pointing in the same direction have a high dot product; perpendicular vectors have a dot product of zero.

```python
query = inputs[1]   # x2 = "journey" = [0.55, 0.87, 0.66]

attn_scores_2 = torch.empty(inputs.shape[0])   # empty tensor with 6 slots

for i, x_i in enumerate(inputs):
    attn_scores_2[i] = torch.dot(x_i, query)

print(attn_scores_2)
# → tensor([0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865])
```

#### **What is a dot product, concretely?**

For `x1 = [0.43, 0.15, 0.89]` and `query = [0.55, 0.87, 0.66]`:

```
dot(x1, query) = (0.43 × 0.55) + (0.15 × 0.87) + (0.89 × 0.66)
               = 0.2365        + 0.1305        + 0.5874
               = 0.9544
```

Multiply element by element, then sum everything up. That's all a dot product is.

#### **What do these scores mean?**

```
Token:     Your    journey  starts   with     one     step
Score:    0.9544  1.4950   1.4754   0.8434   0.7070  1.0865
                    ↑        ↑
               "journey" and "starts" have the highest scores,
               meaning they are most similar to the query "journey"
```

The highest score is x2 with itself (1.4950) — a token is always most similar to its own vector. "starts" (1.4754) comes second, which makes intuitive sense given the sentence "Your journey **starts** with one step."

#### **Why Dot Product = Similarity?**

Think of embedding vectors as directions in space. Words with similar meanings end up pointing in similar directions after training. The dot product measures how aligned two directions are:

```
        High dot product:                Low dot product:
        vectors nearly parallel           vectors nearly perpendicular

             ↗  v1                              ↑ v1
            ↗
           ↗  v2                               → v2

        Very similar concepts              Very different concepts
```

In the context of self-attention: a high dot product between query x2 and some token x_i means "token x_i is very relevant to understanding x2."

---

### **Step 2 — Attention Weights: Normalizing the Scores**

The raw scores `[0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865]` are not yet usable as weights. They need to:

1. All be **positive** (so they work as meaningful proportions)
2. **Sum to 1** (so they form a proper probability distribution)

We use **softmax** for this.

#### **Why Softmax and Not Simple Division?**

You could naively normalize by dividing each score by the total sum:

```python
# Naive normalization
attn_weights_tmp = attn_scores_2 / attn_scores_2.sum()
# → tensor([0.1455, 0.2278, 0.2249, 0.1285, 0.1077, 0.1656])
```

This works, but softmax is better because:

- It **amplifies differences** — higher scores get disproportionately more weight, making the distribution sharper and more decisive
- It **always outputs positive values** even if input scores are negative (it exponentiates them first)
- It has **better gradient properties** during training (section 3.4 and beyond)

#### **Softmax Step by Step**

```python
import math

scores = [0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865]

# Step 1: Exponentiate each score
exp_scores = [math.exp(s) for s in scores]
# = [2.598, 4.459, 4.372, 2.324, 2.028, 2.964]

# Step 2: Sum all the exponentiated values
total = sum(exp_scores)
# = 18.745

# Step 3: Divide each by the total
weights = [e / total for e in exp_scores]
# = [0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581]
```

In PyTorch, this is just one line:

```python
attn_weights_2 = torch.softmax(attn_scores_2, dim=0)
print(attn_weights_2)
# → tensor([0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581])

print(attn_weights_2.sum())
# → tensor(1.0000)  ✓
```

`dim=0` tells softmax to normalize across the first (and only) dimension of this 1D tensor — across all 6 values.

#### **Reading the Attention Weights**

```
Token:    Your    journey  starts   with     one     step
Weight:  0.1385  0.2379   0.2333   0.1240   0.1082  0.1581
           ↑       ↑        ↑
        "journey" attends most to itself (23.8%),
        then "starts" (23.3%), then "step" (15.8%)
```

These weights now tell us: when building the enriched representation of "journey," take 23.8% from "journey" itself, 23.3% from "starts", 15.8% from "step", etc.

```
┌──────────────────────────────────────────────────────────────────┐
│          VISUALIZING THE ATTENTION DISTRIBUTION FOR x2           │
│                                                                  │
│  Your     ████░░░░░░░░░░░░░  13.85%                              │
│  journey  ████████████░░░░░  23.79%  ← highest                  │
│  starts   ███████████░░░░░░  23.33%  ← second highest           │
│  with     ██████░░░░░░░░░░░  12.40%                              │
│  one      █████░░░░░░░░░░░░  10.82%  ← lowest                   │
│  step     ████████░░░░░░░░░  15.81%                              │
│                                                                  │
│  All bars sum to 100%                                            │
└──────────────────────────────────────────────────────────────────┘
```

---

### **Step 3 — Context Vector: Mixing the Information**

Now we use the attention weights as a **recipe** for blending all input vectors together:

```
z2 = α₁ × x1  +  α₂ × x2  +  α₃ × x3  +  α₄ × x4  +  α₅ × x5  +  α₆ × x6

   = 0.1385 × [0.43, 0.15, 0.89]
   + 0.2379 × [0.55, 0.87, 0.66]
   + 0.2333 × [0.57, 0.85, 0.64]
   + 0.1240 × [0.22, 0.58, 0.33]
   + 0.1082 × [0.77, 0.25, 0.10]
   + 0.1581 × [0.05, 0.80, 0.55]
```

Let's work out just the first dimension to see the mechanics:

```
First dimension of z2:
= (0.1385 × 0.43) + (0.2379 × 0.55) + (0.2333 × 0.57)
+ (0.1240 × 0.22) + (0.1082 × 0.77) + (0.1581 × 0.05)

= 0.0595 + 0.1308 + 0.1330 + 0.0273 + 0.0833 + 0.0079
= 0.4419
```

In code:

```python
query          = inputs[1]
context_vec_2  = torch.zeros(query.shape)   # start with [0, 0, 0]

for i, x_i in enumerate(inputs):
    context_vec_2 += attn_weights_2[i] * x_i

print(context_vec_2)
# → tensor([0.4419, 0.6515, 0.5683])
```

#### **What Does This Context Vector Represent?**

```
Raw embedding of "journey":     [0.55, 0.87, 0.66]
Context vector z2:              [0.44, 0.65, 0.57]

The context vector has shifted.
It's no longer purely "journey" — it's a blend of the whole sentence,
but weighted so that semantically close tokens contribute more.
```

The context vector is the **raw embedding of "journey" plus contributions from the rest of the sentence**, scaled by relevance. This is what the LLM actually uses downstream — not the raw embedding.

---

## 3.3.2 — Computing Attention Weights for All Input Tokens

So far we computed z2 for just "journey." In practice, the LLM needs context vectors for **every** token simultaneously. Section 3.3.2 generalizes this to all six tokens at once.

### **Extending the Score Computation**

Instead of one for-loop (over all tokens against one query), we now need a nested loop — every token against every token:

```python
attn_scores = torch.empty(6, 6)

for i, x_i in enumerate(inputs):
    for j, x_j in enumerate(inputs):
        attn_scores[i, j] = torch.dot(x_i, x_j)

print(attn_scores)
```

Result — a **(6×6)** matrix where entry `[i, j]` is the attention score of token `i` attending to token `j`:

```
tensor([[0.9995, 0.9544, 0.9422, 0.4753, 0.4576, 0.6310],
        [0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865],
        [0.9422, 1.4754, 1.4570, 0.8296, 0.7154, 1.0605],
        [0.4753, 0.8434, 0.8296, 0.4937, 0.3474, 0.6565],
        [0.4576, 0.7070, 0.7154, 0.3474, 0.6654, 0.2935],
        [0.6310, 1.0865, 1.0605, 0.6565, 0.2935, 0.9450]])
```

Row 2 (index 1) matches the scores we computed earlier for "journey": `[0.9544, 1.4950, ...]` ✓

The diagonal tends to have high values — each token is always most similar to itself.

### **Matrix Multiplication Is Faster**

The nested for-loop approach works but is slow in Python. We can compute the exact same result in one line:

```python
attn_scores = inputs @ inputs.T
```

#### **Why does this work?**

`inputs` has shape **(6×3)**. `inputs.T` (transpose) has shape **(3×6)**. Matrix multiplication `(6×3) @ (3×6)` gives **(6×6)**.

Each entry `[i,j]` of the result is the dot product of row `i` from `inputs` with column `j` from `inputs.T` — which is the same as the dot product of row `i` with row `j` of `inputs`. Exactly what our nested loop computed.

```
┌──────────────────────────────────────────────────────────────────┐
│              MATRIX MULTIPLICATION = ALL DOT PRODUCTS AT ONCE    │
│                                                                  │
│  inputs (6×3):          inputs.T (3×6):                         │
│  ┌──────────────┐        ┌─────────────────────────────────┐    │
│  │ x1: 0.43 ... │        │ 0.43  0.55  0.57  0.22  0.77  0.05│  │
│  │ x2: 0.55 ... │   @    │ 0.15  0.87  0.85  0.58  0.25  0.80│  │
│  │ x3: 0.57 ... │        │ 0.89  0.66  0.64  0.33  0.10  0.55│  │
│  │ x4: 0.22 ... │        └─────────────────────────────────┘    │
│  │ x5: 0.77 ... │                                               │
│  │ x6: 0.05 ... │        = (6×6) matrix of all pairwise         │
│  └──────────────┘          dot products                         │
└──────────────────────────────────────────────────────────────────┘
```

### **Applying Softmax Across All Rows**

```python
attn_weights = torch.softmax(attn_scores, dim=-1)
print(attn_weights)
```

`dim=-1` normalizes along the last dimension (columns), so **each row independently** sums to 1. Each row is one token's attention distribution over all other tokens.

```
tensor([[0.2098, 0.2006, 0.1981, 0.1242, 0.1220, 0.1452],
        [0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581],  ← "journey" row ✓
        [0.1390, 0.2369, 0.2326, 0.1242, 0.1108, 0.1565],
        [0.1435, 0.2074, 0.2046, 0.1462, 0.1263, 0.1720],
        [0.1526, 0.1958, 0.1975, 0.1367, 0.1879, 0.1295],
        [0.1385, 0.2184, 0.2128, 0.1420, 0.0988, 0.1896]])
```

Quick sanity check:

```python
print(attn_weights.sum(dim=-1))
# → tensor([1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000])  ✓
```

### **Computing All Context Vectors in One Shot**

```python
all_context_vecs = attn_weights @ inputs
print(all_context_vecs)
```

`attn_weights` is **(6×6)** and `inputs` is **(6×3)**. The result is **(6×3)**.

Each row of the result is one context vector:

```
tensor([[0.4421, 0.5931, 0.5790],   ← z1 = enriched "Your"
        [0.4419, 0.6515, 0.5683],   ← z2 = enriched "journey" ✓
        [0.4431, 0.6496, 0.5671],   ← z3 = enriched "starts"
        [0.4304, 0.6298, 0.5510],   ← z4 = enriched "with"
        [0.4671, 0.5910, 0.5266],   ← z5 = enriched "one"
        [0.4177, 0.6503, 0.5645]])  ← z6 = enriched "step"
```

Row 2 (z2 for "journey") is `[0.4419, 0.6515, 0.5683]` — **exactly matches** what we computed manually in section 3.3.1 ✓

#### **Why Does `attn_weights @ inputs` Give All Context Vectors?**

Each row of `attn_weights` holds the weights for one token. Multiplying that row by `inputs` computes a weighted sum of all input vectors. Matrix multiplication does this for all rows simultaneously.

```
Row i of (attn_weights @ inputs):
= attn_weights[i, 0] × x1
+ attn_weights[i, 1] × x2
+ attn_weights[i, 2] × x3
+ ...
+ attn_weights[i, 5] × x6
= context vector z_i
```

Matrix multiplication is just doing this for all 6 rows at once in highly optimized parallel operations.

---

## Complete Visual — The Full Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│               SECTION 3.3 — COMPLETE SELF-ATTENTION PIPELINE        │
│                                                                     │
│  INPUTS X (6×3)                                                     │
│  ┌──────────────────────────┐                                       │
│  │ x1 = [0.43, 0.15, 0.89] │  "Your"                               │
│  │ x2 = [0.55, 0.87, 0.66] │  "journey"  ← query focus             │
│  │ x3 = [0.57, 0.85, 0.64] │  "starts"                             │
│  │ x4 = [0.22, 0.58, 0.33] │  "with"                               │
│  │ x5 = [0.77, 0.25, 0.10] │  "one"                                │
│  │ x6 = [0.05, 0.80, 0.55] │  "step"                               │
│  └────────────┬─────────────┘                                       │
│               │                                                     │
│  STEP 1: attn_scores = X @ X.T                                      │
│               ↓                                                     │
│  ATTENTION SCORES (6×6)                                             │
│  ┌──────────────────────────────────────────────┐                  │
│  │ [0.99, 0.95, 0.94, 0.48, 0.46, 0.63]  row 1 │                  │
│  │ [0.95, 1.50, 1.48, 0.84, 0.71, 1.09]  row 2 │ ← "journey"      │
│  │ [0.94, 1.48, 1.46, 0.83, 0.72, 1.06]  row 3 │                  │
│  │ [0.48, 0.84, 0.83, 0.49, 0.35, 0.66]  row 4 │                  │
│  │ [0.46, 0.71, 0.72, 0.35, 0.67, 0.29]  row 5 │                  │
│  │ [0.63, 1.09, 1.06, 0.66, 0.29, 0.95]  row 6 │                  │
│  └──────────────────────────────────────────────┘                  │
│               │                                                     │
│  STEP 2: attn_weights = softmax(attn_scores, dim=-1)                │
│               ↓                                                     │
│  ATTENTION WEIGHTS (6×6) — each row sums to 1                       │
│  ┌──────────────────────────────────────────────┐                  │
│  │ [0.21, 0.20, 0.20, 0.12, 0.12, 0.15]  row 1 │                  │
│  │ [0.14, 0.24, 0.23, 0.12, 0.11, 0.16]  row 2 │ ← "journey"      │
│  │ [0.14, 0.24, 0.23, 0.12, 0.11, 0.16]  row 3 │                  │
│  │ [0.14, 0.21, 0.20, 0.15, 0.13, 0.17]  row 4 │                  │
│  │ [0.15, 0.20, 0.20, 0.14, 0.19, 0.13]  row 5 │                  │
│  │ [0.14, 0.22, 0.21, 0.14, 0.10, 0.19]  row 6 │                  │
│  └──────────────────────────────────────────────┘                  │
│               │                                                     │
│  STEP 3: all_context_vecs = attn_weights @ inputs                   │
│               ↓                                                     │
│  CONTEXT VECTORS Z (6×3)                                            │
│  ┌──────────────────────────────────┐                               │
│  │ z1 = [0.4421, 0.5931, 0.5790]   │  enriched "Your"              │
│  │ z2 = [0.4419, 0.6515, 0.5683]   │  enriched "journey"           │
│  │ z3 = [0.4431, 0.6496, 0.5671]   │  enriched "starts"            │
│  │ z4 = [0.4304, 0.6298, 0.5510]   │  enriched "with"              │
│  │ z5 = [0.4671, 0.5910, 0.5266]   │  enriched "one"               │
│  │ z6 = [0.4177, 0.6503, 0.5645]   │  enriched "step"              │
│  └──────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Numerical Walkthrough — The Full Path for "journey" (x2)

Everything traced from raw input to final context vector:

```
INPUT x2:
  [0.55, 0.87, 0.66]

                ↓ dot product with every xi

RAW ATTENTION SCORES:
  x1·x2 = (0.43×0.55)+(0.15×0.87)+(0.89×0.66) = 0.9544
  x2·x2 = (0.55×0.55)+(0.87×0.87)+(0.66×0.66) = 1.4950  ← highest (self)
  x3·x2 = (0.57×0.55)+(0.85×0.87)+(0.64×0.66) = 1.4754
  x4·x2 = (0.22×0.55)+(0.58×0.87)+(0.33×0.66) = 0.8434
  x5·x2 = (0.77×0.55)+(0.25×0.87)+(0.10×0.66) = 0.7070
  x6·x2 = (0.05×0.55)+(0.80×0.87)+(0.55×0.66) = 1.0865

  scores = [0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865]

                ↓ softmax

ATTENTION WEIGHTS:
  exp([0.9544, 1.4950, 1.4754, 0.8434, 0.7070, 1.0865])
  = [2.598, 4.459, 4.372, 2.324, 2.028, 2.964]
  sum = 18.745

  weights = [0.1385, 0.2379, 0.2333, 0.1240, 0.1082, 0.1581]
  (all sum to 1.0) ✓

                ↓ weighted sum of input vectors

CONTEXT VECTOR z2:
  dim0: (0.1385×0.43)+(0.2379×0.55)+(0.2333×0.57)+(0.1240×0.22)+(0.1082×0.77)+(0.1581×0.05)
      = 0.0595+0.1308+0.1330+0.0273+0.0833+0.0079 = 0.4419
  dim1: (0.1385×0.15)+(0.2379×0.87)+(0.2333×0.85)+(0.1240×0.58)+(0.1082×0.25)+(0.1581×0.80)
      = 0.0208+0.2070+0.1983+0.0719+0.0271+0.1265 = 0.6515
  dim2: (0.1385×0.89)+(0.2379×0.66)+(0.2333×0.64)+(0.1240×0.33)+(0.1082×0.10)+(0.1581×0.55)
      = 0.1233+0.1570+0.1493+0.0409+0.0108+0.0869 = 0.5683

  z2 = [0.4419, 0.6515, 0.5683] ✓
```

---

## What Section 3.3 Lacks — Why Section 3.4 Is Needed

Section 3.3 is a clean conceptual foundation, but it has one fundamental limitation worth understanding before moving on.

In section 3.3, the **same input vector plays three different roles**:

- It is the **query** (what are we looking for?)
- It is a **key** (what am I about, for matching purposes?)
- It is a **value** (what information do I actually contribute?)

Using the raw embedding for all three roles means the model cannot separately learn "how to ask questions", "how to describe itself for matching", and "what information to contribute." These are three genuinely different functions, and forcing them to be identical constrains what the model can learn.

Section 3.4 solves this by introducing three separate **trainable weight matrices** $W_Q$, $W_K$, $W_V$ to project the same input into three different spaces — each optimized for its specific role.

```
┌──────────────────────────────────────────────────────────────┐
│         SECTION 3.3 vs SECTION 3.4                          │
│                                                              │
│  3.3 (Simplified):                                          │
│    query = x_i   (raw embedding)                            │
│    key   = x_j   (same raw embedding)                       │
│    value = x_j   (same raw embedding)                       │
│    → No learnable parameters                                │
│    → Good for understanding the idea                        │
│                                                              │
│  3.4 (With trainable weights):                              │
│    query = x_i @ W_Q   (learned projection)                 │
│    key   = x_j @ W_K   (learned projection)                 │
│    value = x_j @ W_V   (learned projection)                 │
│    → Three separate learned transformations                 │
│    → The actual mechanism used in GPT models                │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways for Section 3.3

**Self-attention gives every token a global view of the sentence.** Instead of each word being represented in isolation, every token's context vector is a weighted blend of the whole sequence.

**Dot product measures similarity.** Two vectors that are aligned (pointing in the same direction) have a high dot product. This is what raw attention scores represent — how similar each pair of tokens is.

**Softmax turns scores into a probability distribution.** It ensures weights are positive and sum to 1, making them interpretable as "how much attention to pay" to each token.

**The context vector is a weighted average of inputs.** Each input vector contributes proportionally to its attention weight. High-weight tokens contribute more to the final enriched representation.

**Matrix multiplication computes everything in parallel.** `X @ X.T` gives all pairwise scores at once. `attn_weights @ inputs` gives all context vectors at once. This is why modern hardware can run transformers efficiently at scale.

---

# 4: Self-Attention with Trainable Weights

## 1. What Changed From Section 3.3?

In section 3.3, you computed attention weights by taking the dot product of the raw input vectors directly with each other. It worked, but there was a fundamental limitation — the input embeddings were fixed. The model had **no way to learn** from data and improve the quality of those attention weights.

Section 3.4 introduces **three trainable weight matrices**: $W_Q$, $W_K$, and $W_V$. These are matrices whose values start random but get adjusted during training. Their job is to **project** each raw input token into three separate, learned spaces called:

- the **Query** space
- the **Key** space
- the **Value** space

This is called **scaled dot-product attention**, and it is the exact mechanism used in GPT-2, GPT-3, and virtually every modern transformer-based LLM.

---

## 2. Query, Key, and Value — The Real-Life Analogy

Before any math, you need to build a strong intuition. The names "query", "key", and "value" come directly from how **database retrieval** works.

### The YouTube Search Analogy

Imagine you open YouTube and type in the search bar: **"how to make sourdough bread"**. Three things are happening under the hood:

```
What you TYPE into the search bar
─────────────────────────────────────────────────
"how to make sourdough bread"
          │
          │  This is your QUERY
          │  It represents WHAT YOU ARE LOOKING FOR
          ▼

YouTube compares your query against every video's metadata tag
─────────────────────────────────────────────────
Video 1:  KEY = "sourdough bread recipe tutorial"
Video 2:  KEY = "cat videos compilation"
Video 3:  KEY = "bread baking beginner guide"
Video 4:  KEY = "pasta carbonara recipe"
          │
          │  KEYs are used purely for MATCHING
          │  They represent WHAT EACH ITEM IS ABOUT
          ▼

YouTube ranks them by relevance and returns the actual videos
─────────────────────────────────────────────────
Video 1:  VALUE = [the actual video content, thumbnail, description]
Video 3:  VALUE = [the actual video content, thumbnail, description]
          │
          │  VALUEs are the ACTUAL CONTENT YOU RECEIVE
          │  Keys decided WHO wins, Values are what you get
```

The same logic applies to self-attention:

| Database Concept           | Attention Concept | What It Does                           |
| -------------------------- | ----------------- | -------------------------------------- |
| Search query you type      | **Query (Q)**     | "What am I looking for?"               |
| Metadata tags on each item | **Key (K)**       | "What does each token represent?"      |
| Actual content returned    | **Value (V)**     | "What information do I actually take?" |

### Applying This To Our Sentence

Take the sentence: **"Your journey starts with one step"**

When we compute the context vector for the token **"journey"**:

- **Query** of "journey" asks: _"What information do I need to understand my role in this sentence?"_
- **Keys** of all tokens ("Your", "journey", "starts", "with", "one", "step") say: _"Here's what each of us is about"_
- The dot product of the Query with each Key gives a **relevance score** — how much should "journey" pay attention to each other word?
- **Values** of the tokens that score high get mixed together to form the final enriched representation of "journey"

The critical insight is that **Keys and Values come from the same tokens**, but they serve different roles. The Key is used for **matching/scoring**, the Value is used for **information transfer**.

---

## 3. Why Do We Need Separate Weight Matrices?

In section 3.3, you used the raw input `x` directly as both query and key. The problem is that this forces the same vector to serve two very different purposes simultaneously:

- _"Am I similar to other tokens?"_ (key role)
- _"What information should I contribute?"_ (value role)

By learning separate projection matrices $W_Q$, $W_K$, $W_V$, the model can project the same input into three different spaces, each optimized for its specific purpose. The model learns, during training, what the "best" Q, K, V spaces are for producing useful context vectors.

---

## 4. The Setup — Book Example

We use the exact input from the book. Six tokens, each with a 3-dimensional embedding:

```python
inputs = torch.tensor(
    [[0.43, 0.15, 0.89],  # Your     (x1)
     [0.55, 0.87, 0.66],  # journey  (x2)  ← our query token
     [0.57, 0.85, 0.64],  # starts   (x3)
     [0.22, 0.58, 0.33],  # with     (x4)
     [0.77, 0.25, 0.10],  # one      (x5)
     [0.05, 0.80, 0.55]]  # step     (x6)
)
```

We focus on computing the context vector **z(2)** for token **"journey"** (x2).

Dimension settings:

- $d_{in} = 3$ (input embedding size)
- $d_{out} = 2$ (output embedding size — smaller for clarity)

---

## 5. The Three Weight Matrices — Shape and Meaning

Each weight matrix $W$ has shape **(d_in × d_out)**, which is **(3 × 2)** here.

```
W_query shape: (3 × 2)
W_key   shape: (3 × 2)
W_value shape: (3 × 2)
```

**Why this shape?** Because matrix multiplication works as:

```
input vector      ×    weight matrix    =    projected vector
(1 × d_in)        ×    (d_in × d_out)   =    (1 × d_out)
(1 × 3)           ×    (3 × 2)          =    (1 × 2)
```

The weight matrix **transforms** a 3D input vector into a 2D projected vector. The values inside the weight matrix are the parameters the model **learns** during training.

```
┌────────────────────────────────────────────────────────────────┐
│                    THREE WEIGHT MATRICES                       │
│                                                                │
│   W_query =  [ w11  w12 ]     W_key =  [ w11  w12 ]           │
│              [ w21  w22 ]              [ w21  w22 ]           │
│              [ w31  w32 ]              [ w31  w32 ]           │
│               shape: 3×2               shape: 3×2             │
│                                                                │
│   W_value =  [ w11  w12 ]                                      │
│              [ w21  w22 ]                                      │
│              [ w31  w32 ]                                      │
│               shape: 3×2                                       │
│                                                                │
│  All values start random, get updated during training          │
└────────────────────────────────────────────────────────────────┘
```

In code (with `requires_grad=False` just for illustration, would be `True` in real training):

```python
torch.manual_seed(123)
W_query = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
W_key   = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
W_value = torch.nn.Parameter(torch.rand(d_in, d_out), requires_grad=False)
```

---

## 6. Step 1 — Computing Query, Key, Value Vectors

### For the Query Token x2 ("journey")

We take the input vector for "journey" and multiply it by each weight matrix:

```
x2 = [0.55, 0.87, 0.66]   (shape: 1×3)

query_2 = x2 @ W_query     (shape: 1×3  ×  3×2  =  1×2)
key_2   = x2 @ W_key       (shape: 1×3  ×  3×2  =  1×2)
value_2 = x2 @ W_value     (shape: 1×3  ×  3×2  =  1×2)
```

The result from the book:

```python
query_2 = tensor([0.4306, 1.4551])
```

### For All Tokens — Using Matrix Multiplication

To compute keys and values for **all** tokens at once, we use batch matrix multiplication. The full input matrix `inputs` has shape **(6 × 3)**:

```
keys   = inputs @ W_key     (shape: 6×3  ×  3×2  =  6×2)
values = inputs @ W_value   (shape: 6×3  ×  3×2  =  6×2)
```

Each **row** of `keys` is the key vector for that token. Each **row** of `values` is the value vector for that token.

```
┌─────────────────────────────────────────────────────────────────────┐
│                  PROJECTING INPUTS INTO Q, K, V SPACES              │
│                                                                     │
│                                                                     │
│  inputs         W_key           keys                                │
│  (6 × 3)    ×  (3 × 2)    =   (6 × 2)                             │
│                                                                     │
│  [x1]          [w w]          [k1]   ← key for "Your"              │
│  [x2]    ×     [w w]    =     [k2]   ← key for "journey"           │
│  [x3]          [w w]          [k3]   ← key for "starts"            │
│  [x4]                         [k4]   ← key for "with"              │
│  [x5]                         [k5]   ← key for "one"               │
│  [x6]                         [k6]   ← key for "step"              │
│                                                                     │
│  Same operation for W_query → queries (6×2)                        │
│  Same operation for W_value → values  (6×2)                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Step 2 — Computing Attention Scores

Now we compute how much **"journey"** (our query) should attend to each token.

We do this by taking the **dot product of query_2 with each key vector**:

```
attn_score(2,1) = query_2 · key_1   ← how much "journey" attends to "Your"
attn_score(2,2) = query_2 · key_2   ← how much "journey" attends to itself
attn_score(2,3) = query_2 · key_3   ← how much "journey" attends to "starts"
... and so on
```

In matrix form (much faster):

```
attn_scores_2 = query_2 @ keys.T

shape: (1×2) @ (2×6) = (1×6)

result: tensor([1.2705, 1.8524, 1.8111, 1.0795, 0.5577, 1.5440])
```

Notice: **the score for "journey" attending to itself (1.8524) is the highest**. This makes sense — a word is usually most similar to its own projected key. But "starts" (1.8111) is also very close, which makes intuitive sense since "journey" and "starts" are semantically adjacent in this sentence.

```
┌─────────────────────────────────────────────────────────────────────┐
│              COMPUTING ATTENTION SCORES FOR QUERY x2               │
│                                                                     │
│  query_2 = [0.4306, 1.4551]    (the projected "journey" vector)    │
│                                                                     │
│   keys.T =  [ k1  k2  k3  k4  k5  k6 ]                            │
│              (each column is a key vector)                         │
│                                                                     │
│  query_2 @ keys.T                                                  │
│  = [0.4306×k1[0]+1.4551×k1[1], ..., 0.4306×k6[0]+1.4551×k6[1]]   │
│  = [1.2705,  1.8524,  1.8111,  1.0795,  0.5577,  1.5440]          │
│       ↑        ↑        ↑        ↑        ↑        ↑              │
│      Your  journey  starts    with      one      step             │
│                                                                     │
│  Higher score = "journey" is more similar/relevant to that word    │
└─────────────────────────────────────────────────────────────────────┘
```

### Why Query Dot Key and Not Input Dot Input?

In section 3.3, you did `x_i · x_j` — raw inputs dot producted with each other. The problem was the raw embeddings weren't designed to measure "how much should I attend to you?" By projecting into separate Q and K spaces via learned weights, the model can learn to make these scores **meaningfully reflect semantic relevance** for the specific task.

---

## 8. Step 3 — Scaling and Softmax → Attention Weights

### Why Scaling?

Before softmax, we **divide the scores by $\sqrt{d_k}$** where $d_k$ is the dimension of the key vectors (here $d_k = 2$, so $\sqrt{2} \approx 1.41$).

**Why?** When the embedding dimension is large (e.g., 768 in GPT-2), dot products can become very large. Large values fed into softmax create a near-step function — one weight becomes nearly 1.0 and everything else nearly 0. This causes **vanishing gradients** during backpropagation, making training very slow or unstable.

Dividing by $\sqrt{d_k}$ keeps the scores in a reasonable range regardless of embedding size.

```
scaled_scores = attn_scores_2 / sqrt(d_k)
              = [1.2705, 1.8524, 1.8111, 1.0795, 0.5577, 1.5440] / sqrt(2)
              = [0.8984, 1.3096, 1.2804, 0.7632, 0.3943, 1.0917]
```

### Softmax → Attention Weights

```
attn_weights_2 = softmax(scaled_scores)
               = tensor([0.1500, 0.2264, 0.2199, 0.1311, 0.0906, 0.1820])
```

These now sum to 1.0 and represent the **probability distribution** of how much "journey" attends to each token.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   ATTENTION WEIGHTS FOR "journey"                   │
│                                                                     │
│  Token:    Your    journey  starts    with      one      step       │
│  Weight:  0.1500  0.2264   0.2199   0.1311   0.0906   0.1820       │
│                                                                     │
│  Interpretation:                                                    │
│  ● "journey" pays most attention to ITSELF (22.6%)                 │
│  ● "starts" comes second (22.0%) — semantically close              │
│  ● "step" third (18.2%) — thematically related                     │
│  ● "one" gets least attention (9.1%)                               │
│                                                                     │
│  These are now a valid probability distribution:                    │
│  0.1500 + 0.2264 + 0.2199 + 0.1311 + 0.0906 + 0.1820 = 1.0        │
└─────────────────────────────────────────────────────────────────────┘
```

### The Complete Scoring Formula

$$\text{attention\_weights} = \text{softmax}\left(\frac{Q \cdot K^T}{\sqrt{d_k}}\right)$$

This single formula is called **scaled dot-product attention** and is one of the most important equations in modern deep learning.

---

## 9. Step 4 — Computing the Context Vector

The final step: use the attention weights to take a **weighted sum of the Value vectors**.

```
context_vec_2 = attn_weights_2 @ values

= 0.1500 × value_1
+ 0.2264 × value_2   ← "journey"'s value contributes most
+ 0.2199 × value_3   ← "starts" contributes second most
+ 0.1311 × value_4
+ 0.0906 × value_5
+ 0.1820 × value_6
```

Result from the book:

```python
context_vec_2 = tensor([0.3061, 0.8210])
```

**Why Values and not Keys?** Keys were used to compute _relevance scores_ — they encode what each token is "about" for the purpose of matching. Values encode what information each token should _contribute_ when selected. They're different learned projections designed for different jobs. The scores from Keys tell you how much of each Value to blend in.

```
┌─────────────────────────────────────────────────────────────────────┐
│                 COMPUTING CONTEXT VECTOR z(2)                       │
│                                                                     │
│  values (6×2):                                                      │
│  v1 = [a, b]   "Your"     × 0.1500  ─────┐                        │
│  v2 = [c, d]   "journey"  × 0.2264  ─────┤                        │
│  v3 = [e, f]   "starts"   × 0.2199  ─────┤ weighted sum           │
│  v4 = [g, h]   "with"     × 0.1311  ─────┤                        │
│  v5 = [i, j]   "one"      × 0.0906  ─────┤                        │
│  v6 = [k, l]   "step"     × 0.1820  ─────┘                        │
│                                   ↓                                │
│                         z2 = [0.3061, 0.8210]                      │
│                                                                     │
│  This is the ENRICHED representation of "journey" —                │
│  it now contains blended information from the entire sentence       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. The Complete Flow — End to End

```
┌─────────────────────────────────────────────────────────────────────┐
│              FULL SELF-ATTENTION PIPELINE (Section 3.4)             │
│                                                                     │
│  INPUTS                                                             │
│  ┌────────────────────────────────┐                                 │
│  │  x1=[0.43,0.15,0.89]  "Your"  │                                 │
│  │  x2=[0.55,0.87,0.66]  "journey"│ ← our query token              │
│  │  x3=[0.57,0.85,0.64]  "starts"│                                 │
│  │  x4=[0.22,0.58,0.33]  "with"  │                                 │
│  │  x5=[0.77,0.25,0.10]  "one"   │                                 │
│  │  x6=[0.05,0.80,0.55]  "step"  │                                 │
│  └─────────────┬──────────────────┘                                 │
│                │                                                    │
│    ┌───────────┼───────────┐                                        │
│    │           │           │                                        │
│    × W_query  × W_key     × W_value                                │
│    │           │           │                                        │
│    ▼           ▼           ▼                                        │
│  queries(6×2) keys(6×2) values(6×2)                                │
│                                                                     │
│    STEP 2: Compute raw attention scores                             │
│    ┌─────────────────────────────────┐                              │
│    │  scores = queries @ keys.T      │  shape: (6×2)@(2×6) = (6×6) │
│    └─────────────────────────────────┘                              │
│                │                                                    │
│    STEP 3: Scale + Softmax                                          │
│    ┌─────────────────────────────────┐                              │
│    │  weights = softmax(scores/√dk)  │  shape stays: (6×6)          │
│    │  Each row sums to 1.0           │                              │
│    └─────────────────────────────────┘                              │
│                │                                                    │
│    STEP 4: Weighted sum of values                                   │
│    ┌─────────────────────────────────┐                              │
│    │  context = weights @ values     │  shape: (6×6)@(6×2) = (6×2) │
│    └─────────────────────────────────┘                              │
│                │                                                    │
│    OUTPUT: context vectors (6×2)                                   │
│    ┌─────────────────────────────────┐                              │
│    │  z1 = enriched "Your"           │                              │
│    │  z2 = enriched "journey" [0.3061, 0.8210]                     │
│    │  z3 = enriched "starts"         │                              │
│    │  z4 = enriched "with"           │                              │
│    │  z5 = enriched "one"            │                              │
│    │  z6 = enriched "step"           │                              │
│    └─────────────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. The SelfAttention_v1 Class — Code Breakdown

```python
class SelfAttention_v1(nn.Module):
    def __init__(self, d_in, d_out):
        super().__init__()
        # Three learnable weight matrices, randomly initialized
        self.W_query = nn.Parameter(torch.rand(d_in, d_out))
        self.W_key   = nn.Parameter(torch.rand(d_in, d_out))
        self.W_value = nn.Parameter(torch.rand(d_in, d_out))

    def forward(self, x):
        # Step 1: Project inputs into Q, K, V spaces
        keys    = x @ self.W_key    # (6×3) @ (3×2) = (6×2)
        queries = x @ self.W_query  # (6×3) @ (3×2) = (6×2)
        values  = x @ self.W_value  # (6×3) @ (3×2) = (6×2)

        # Step 2: Compute attention scores
        attn_scores = queries @ keys.T   # (6×2) @ (2×6) = (6×6)

        # Step 3: Scale and normalize
        attn_weights = torch.softmax(
            attn_scores / keys.shape[-1]**0.5, dim=-1
        )   # still (6×6), but each row sums to 1

        # Step 4: Compute context vectors
        context_vec = attn_weights @ values  # (6×6) @ (6×2) = (6×2)
        return context_vec
```

**What `dim=-1` means in softmax:** Apply softmax across the last dimension (columns), so each **row** independently sums to 1. Each row corresponds to one token's attention distribution over all tokens.

---

## 12. SelfAttention_v2 — Using nn.Linear Instead

The v2 class replaces `nn.Parameter(torch.rand(...))` with `nn.Linear`:

```python
self.W_query = nn.Linear(d_in, d_out, bias=False)
```

`nn.Linear` is functionally equivalent for our purposes (it performs a matrix multiplication), but it uses a **smarter weight initialization scheme** (Kaiming uniform initialization) rather than plain random values. This leads to more stable training from the start.

The key difference to know: `nn.Linear` stores its weight in **transposed form** internally (`d_out × d_in` instead of `d_in × d_out`). This is why Exercise 3.1 asks you to be careful when copying weights between v1 and v2 — you need to transpose.

---

## 13. Key Numerical Summary — The Full Path for "journey"

```
INPUT x2:
  [0.55, 0.87, 0.66]

                ↓ @ W_query (3×2)

QUERY q2:
  [0.4306, 1.4551]

                ↓ dot with each key k1...k6

RAW ATTENTION SCORES:
  [1.2705, 1.8524, 1.8111, 1.0795, 0.5577, 1.5440]
   Your    journey  starts  with    one     step

                ↓ divide by √2 = 1.414

SCALED SCORES:
  [0.8984, 1.3096, 1.2804, 0.7632, 0.3943, 1.0917]

                ↓ softmax

ATTENTION WEIGHTS:
  [0.1500, 0.2264, 0.2199, 0.1311, 0.0906, 0.1820]
   Your    journey  starts  with    one     step
                                              ↑
                                      All sum to 1.0

                ↓ weighted sum of value vectors

CONTEXT VECTOR z2:
  [0.3061, 0.8210]
  ← enriched "journey" with context from the whole sentence
```

---

## 14. What Do We Actually Have After This? The Big Picture

The context vector z2 = `[0.3061, 0.8210]` is a **2-dimensional vector** that now encodes:

- The meaning of "journey" itself (highest weight, 22.6%)
- Contextual information from "starts" (22.0%) — _journey_ that _starts_
- Information from "step" (18.2%) — _journey_ and _step_ are thematically linked
- Smaller contributions from other words

This enriched representation is **much more useful** for downstream tasks (like predicting the next token) than the raw embedding of "journey" alone.

The weight matrices $W_Q$, $W_K$, $W_V$ are what get updated during training. Over millions of examples, the model learns which projection spaces make the resulting attention patterns and context vectors most useful for the task of next-token prediction.

---

## 15. Weight Parameters vs. Attention Weights — Clearing Up the Terminology

This is a common source of confusion because both use the word "weight":

| Term                                      | What It Is                                    | When It Changes                            |
| ----------------------------------------- | --------------------------------------------- | ------------------------------------------ |
| **Weight matrices** ($W_Q$, $W_K$, $W_V$) | Learnable parameters of the neural network    | Updated by backpropagation during training |
| **Attention weights** ($\alpha$)          | Dynamic scores computed for each forward pass | Different for every input sequence         |

Weight matrices are the **brain** — they encode learned knowledge. Attention weights are the **decisions** that brain makes for each new input.

---

## 16. Mathematical Summary — All Operations At a Glance

$$Q = X \cdot W_Q \quad \text{shape: } (T \times d_{in})(d_{in} \times d_{out}) = (T \times d_{out})$$

$$K = X \cdot W_K \quad \text{shape: } (T \times d_{in})(d_{in} \times d_{out}) = (T \times d_{out})$$

$$V = X \cdot W_V \quad \text{shape: } (T \times d_{in})(d_{in} \times d_{out}) = (T \times d_{out})$$

$$\text{AttnScores} = Q \cdot K^T \quad \text{shape: } (T \times d_{out})(d_{out} \times T) = (T \times T)$$

$$\text{AttnWeights} = \text{softmax}\left(\frac{\text{AttnScores}}{\sqrt{d_{out}}}\right) \quad \text{shape: } (T \times T)$$

$$Z = \text{AttnWeights} \cdot V \quad \text{shape: } (T \times T)(T \times d_{out}) = (T \times d_{out})$$

Where $T$ is the sequence length (6 tokens in our example) and the final output $Z$ contains one enriched context vector per token.

---

## 17. Intuitive Check — Does This Make Sense?

Ask yourself: after all this math, what did we actually accomplish?

We started with 6 simple embedding vectors, each of 3 dimensions. We ended with 6 enriched context vectors, each of 2 dimensions. But those 2 dimensions now contain **blended information from the whole sentence**, weighted by learned relevance scores.

The three weight matrices are the model's way of learning: _"What should I look for? (Query) What do other tokens advertise about themselves? (Key) What do tokens actually contribute when selected? (Value)"_

This is fundamentally more powerful than simply comparing raw embeddings, because the model can learn to separate these three roles and optimize each independently.

---

# 5: Hiding Future Words with Causal Attention

## Why Does Causal Attention Exist?

Before any code or math, understand the **fundamental problem** it solves.

When an LLM generates text, it works **one token at a time, left to right**:

```
Input:   "Your journey starts with one ___"
                                          ↑
                              Model predicts this

Input:   "Your journey starts with one step ___"
                                                ↑
                              Then predicts this
```

During **training**, the model sees the full sentence. But if it's allowed to peek at future tokens while computing context vectors for earlier tokens, it's **cheating** — it would learn "whenever I see token 3, token 5 is coming" rather than learning real language patterns. At inference time, future tokens don't exist yet, so any pattern built on peeking would be useless and the model would fail.

Causal attention solves this by **masking out future tokens** during the attention computation — for each token at position `i`, it can only attend to positions `1, 2, ..., i`.

```
┌──────────────────────────────────────────────────────────────────┐
│              WHAT EACH TOKEN IS ALLOWED TO SEE                   │
│                                                                  │
│  Position:    1       2        3       4      5      6           │
│  Token:     "Your" "journey" "starts" "with" "one" "step"       │
│                                                                  │
│  "Your"    can see: [Your]                                       │
│  "journey" can see: [Your, journey]                              │
│  "starts"  can see: [Your, journey, starts]                      │
│  "with"    can see: [Your, journey, starts, with]                │
│  "one"     can see: [Your, journey, starts, with, one]           │
│  "step"    can see: [Your, journey, starts, with, one, step]     │
│                                                                  │
│  No token can see anything to its RIGHT                          │
└──────────────────────────────────────────────────────────────────┘
```

This is why it is also called **masked self-attention** — we mask the attention weights that would look into the future.

---

## 3.5.1 — Applying a Causal Attention Mask

### **The Attention Weight Matrix — What It Looks Like Before Masking**

After the softmax step from section 3.4, you get a **(6×6)** attention weight matrix where every row sums to 1. Row `i` contains the weights for how much token `i` attends to every other token.

```
              Your  journey  starts  with   one   step
              ─────────────────────────────────────────
Your    │  0.19    0.16     0.17    0.15   0.17   0.15  │ ← sums to 1
journey │  0.20    0.17     0.16    0.15   0.17   0.15  │
starts  │  0.20    0.16     0.16    0.15   0.17   0.15  │
with    │  0.19    0.17     0.17    0.16   0.17   0.16  │
one     │  0.18    0.17     0.17    0.16   0.17   0.16  │
step    │  0.19    0.17     0.17    0.15   0.17   0.15  │
```

**Problem:** "Your" (row 1) is attending to "journey", "starts", "one", "step" — all future tokens it should NOT be able to see.

### **The Goal: Make the Matrix Look Like This**

```
              Your  journey  starts  with   one   step
              ─────────────────────────────────────────
Your    │  1.00    0.00     0.00    0.00   0.00   0.00  │
journey │  0.55    0.45     0.00    0.00   0.00   0.00  │
starts  │  0.38    0.31     0.31    0.00   0.00   0.00  │
with    │  0.28    0.25     0.25    0.23   0.00   0.00  │
one     │  0.22    0.20     0.20    0.19   0.20   0.00  │
step    │  0.19    0.17     0.17    0.15   0.17   0.15  │
```

Everything **above the diagonal** is zero — no peeking at the future. And each row still sums to 1.

### **Method 1: The Simple Masking Approach (3 Steps)**

This is the intuitive approach. The book covers it first to build understanding.

---

**Step 1: Compute attention weights with softmax (as normal)**

```python
queries = sa_v2.W_query(inputs)   # project inputs → queries
keys    = sa_v2.W_key(inputs)     # project inputs → keys

attn_scores  = queries @ keys.T   # (6×2) @ (2×6) = (6×6) raw scores
attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
```

`attn_scores` — raw dot product scores, not bounded.
`keys.shape[-1]` — the dimension of the key vectors (= 2 here). We divide by `√2` for the scaling trick from section 3.4.
`dim=-1` — softmax across the last axis (columns), so each **row** independently sums to 1.

The result is the unmasked weight matrix shown above — every row sums to 1, but future tokens are still included.

---

**Step 2: Create a lower-triangular mask**

```python
context_length = attn_scores.shape[0]   # = 6 (number of tokens)
mask_simple    = torch.tril(torch.ones(context_length, context_length))
```

`torch.ones(6, 6)` — creates a 6×6 matrix of all 1s.
`torch.tril(...)` — keeps only the **lower triangle** (including diagonal), sets everything above to 0.

```
mask_simple:
tensor([[1., 0., 0., 0., 0., 0.],
        [1., 1., 0., 0., 0., 0.],
        [1., 1., 1., 0., 0., 0.],
        [1., 1., 1., 1., 0., 0.],
        [1., 1., 1., 1., 1., 0.],
        [1., 1., 1., 1., 1., 1.]])
```

The 1s show **which positions are allowed** — past and present only.

---

**Step 3: Multiply the mask with attention weights (element-wise)**

```python
masked_simple = attn_weights * mask_simple
```

This is **element-wise multiplication** (not matrix multiplication). Each weight gets multiplied by its corresponding mask value — either 1 (keep it) or 0 (kill it).

```
Before masking (row 2 = "journey"):
  [0.2041,  0.1659,  0.1662,  0.1496,  0.1665,  0.1477]

After masking (zeros above diagonal for row 2):
  [0.2041,  0.1659,  0.0000,  0.0000,  0.0000,  0.0000]
```

"journey" now only attends to "Your" (position 1) and itself (position 2). ✓

---

**Step 4: Renormalize rows so they sum to 1 again**

```python
row_sums          = masked_simple.sum(dim=-1, keepdim=True)
masked_simple_norm = masked_simple / row_sums
```

`sum(dim=-1, keepdim=True)` — sum across columns for each row, keeping the result as a column vector of shape (6×1) so we can broadcast-divide.

```
Before renormalization (row 2 "journey"):
  [0.2041,  0.1659,  0.0000,  0.0000,  0.0000,  0.0000]
  sum = 0.2041 + 0.1659 = 0.3700

After renormalization:
  [0.2041/0.3700,  0.1659/0.3700,  0, 0, 0, 0]
= [0.5517,         0.4483,          0, 0, 0, 0]  ← sums to 1 ✓
```

Full normalized result:

```
tensor([[1.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
        [0.5517, 0.4483, 0.0000, 0.0000, 0.0000, 0.0000],
        [0.3800, 0.3097, 0.3103, 0.0000, 0.0000, 0.0000],
        [0.2758, 0.2460, 0.2462, 0.2319, 0.0000, 0.0000],
        [0.2175, 0.1983, 0.1984, 0.1888, 0.1971, 0.0000],
        [0.1935, 0.1663, 0.1666, 0.1542, 0.1666, 0.1529]])
```

---

## The Information Leakage Question — Answered Properly

> _"When we apply a mask and then renormalize, doesn't the softmax calculation already include the future tokens? Doesn't that mean some of their influence leaked in?"_

This is a **really sharp question** and the book's explanation is a bit dense. Let me break it down with numbers.

### **The Concern**

Softmax for row 2 ("journey") was calculated over ALL 6 scores:

```
Raw scores:  [0.4656,  0.1723,  -inf-ish,  -inf-ish,  -inf-ish,  -inf-ish]
                                  ↑ future tokens were included here
```

The softmax formula is:

```
softmax(x_i) = exp(x_i) / sum(exp(x_j) for all j)
```

The denominator included future tokens. Doesn't that mean their `exp()` values were counted, and thus influenced the final weights?

### **The Answer — With a Tiny Example**

Let's use just **3 tokens** and say token 2 is our focus. The future token is token 3.

Suppose raw scores for row 2 are:

```
score_1 = 1.0   (past token — allowed)
score_2 = 2.0   (current token — allowed)
score_3 = 0.5   (future token — should be masked)
```

**What softmax DOES before masking:**

```
exp(1.0) = 2.72
exp(2.0) = 7.39
exp(0.5) = 1.65

sum = 2.72 + 7.39 + 1.65 = 11.76

weight_1 = 2.72 / 11.76 = 0.231
weight_2 = 7.39 / 11.76 = 0.629
weight_3 = 1.65 / 11.76 = 0.140   ← future token has 14% influence!
```

We then zero out weight_3 and renormalize:

```
masked:   [0.231,  0.629,  0.000]
sum       = 0.231 + 0.629 = 0.860

renorm:   [0.231/0.860,  0.629/0.860,  0.000]
        = [0.269,         0.731,         0.000]
```

**Now compare with what you'd get if token 3 never existed:**

```
exp(1.0) = 2.72
exp(2.0) = 7.39

sum = 2.72 + 7.39 = 10.11

weight_1 = 2.72 / 10.11 = 0.269
weight_2 = 7.39 / 10.11 = 0.731
```

**They are identical.** `[0.269, 0.731]` in both cases.

```
┌─────────────────────────────────────────────────────────────────┐
│         PROOF: NO INFORMATION LEAKAGE                          │
│                                                                 │
│  Path A: Include token 3, mask it, renormalize                 │
│  ─────────────────────────────────────────────                 │
│  softmax([1.0, 2.0, 0.5]) → [0.231, 0.629, 0.140]             │
│  zero out pos 3           → [0.231, 0.629, 0.000]             │
│  renormalize (÷ 0.860)    → [0.269, 0.731, 0.000]  ✓          │
│                                                                 │
│  Path B: Only compute over allowed positions                   │
│  ─────────────────────────────────────────────                 │
│  softmax([1.0, 2.0])      → [0.269, 0.731]          ✓          │
│                                                                 │
│  Result A == Result B   →   Zero information leakage           │
│                                                                 │
│  WHY? Because dividing by the partial sum (0.860) in Path A    │
│  is EXACTLY the same as computing softmax over just those two  │
│  positions. The future token's exp() cancels out completely.   │
└─────────────────────────────────────────────────────────────────┘
```

The mathematical reason: softmax followed by zeroing and renormalizing is algebraically equivalent to never including those positions in the first place. The future token's `exp()` value appears in both numerator (then gets zeroed) and denominator (then gets divided away). **It cancels.**

---

## Method 2: The -∞ Trick (Efficient Masking)

Method 1 required three steps: softmax → zero out → renormalize. Method 2 achieves the same result in **two steps**: mask with -∞ → softmax. No manual renormalization needed.

```
┌──────────────────────────────────────────────────────────┐
│  Method 1 (3 steps):                                     │
│  scores → softmax → zero out → renormalize               │
│                                                          │
│  Method 2 (2 steps):                                     │
│  scores → fill future with -∞ → softmax                 │
│                                                          │
│  Both produce identical final results.                   │
│  Method 2 is cleaner and preferred in practice.          │
└──────────────────────────────────────────────────────────┘
```

**Why does -∞ work?**

```
softmax(x_i) = exp(x_i) / sum(exp(x_j))

exp(-∞) = 0
```

When you fill future positions with `-inf` before softmax, their `exp()` evaluates to exactly 0. They contribute nothing to the denominator and their numerator is 0. Softmax naturally produces 0 for them, and the remaining weights automatically sum to 1. No separate renormalization step needed.

```python
# Step 1: Create upper-triangular mask (1s ABOVE diagonal = future positions)
mask = torch.triu(torch.ones(context_length, context_length), diagonal=1)
```

`torch.triu(...)` — upper triangle (above diagonal). Note: this is the **opposite** of `tril`. The `diagonal=1` means the diagonal itself stays 0 — only strictly future positions get 1s.

```
mask:
tensor([[0., 1., 1., 1., 1., 1.],
        [0., 0., 1., 1., 1., 1.],
        [0., 0., 0., 1., 1., 1.],
        [0., 0., 0., 0., 1., 1.],
        [0., 0., 0., 0., 0., 1.],
        [0., 0., 0., 0., 0., 0.]])
```

```python
# Step 2: Replace those 1s in the attention SCORES with -inf
masked = attn_scores.masked_fill(mask.bool(), -torch.inf)
```

`mask.bool()` — converts the float mask to a boolean tensor (0→False, 1→True).
`.masked_fill(condition, value)` — wherever condition is True, replace that position with the given value (`-inf` here).

```
Result (row 2 = "journey"):
Before:  [0.4656,  0.1723,  0.1731,  -inf,   -inf,  -inf]
                            ↑ current position stays
```

```python
# Step 3: Apply softmax (future positions become 0 automatically)
attn_weights = torch.softmax(masked / keys.shape[-1]**0.5, dim=1)
```

Softmax sees `-inf` in future positions → `exp(-inf) = 0` → those slots are exactly 0 → remaining weights sum to 1 automatically.

```
Final result (row 2 = "journey"):
  [0.5517, 0.4483, 0.0000, 0.0000, 0.0000, 0.0000]  ← identical to Method 1 ✓
```

### **Side by Side — Why -∞ and Softmax Go Together Perfectly**

```
Small example, row for token 2 (scores before scaling):

      token1  token2  token3(future)
      ──────  ──────  ──────────────
raw:   1.0     2.0     0.5
      ──────  ──────  ──────────────
-inf:  1.0     2.0     -inf

exp:   2.72    7.39    exp(-inf)=0.00

sum:   2.72 + 7.39 + 0.00  =  10.11

weights: 0.269   0.731   0.000   ← sums to 1, no renorm needed ✓
```

---

## 3.5.2 — Dropout: An Extra Layer of Protection Against Overfitting

### **What is Dropout and Why Add It Here?**

Dropout is a **regularization technique**. During training, it randomly sets some values to zero (with probability `p`) and scales up the remaining values by `1/(1-p)` to compensate.

In causal attention, applying dropout to the attention weight matrix prevents the model from **over-relying on specific token relationships**. If the model can't always count on any particular attention connection being present, it's forced to learn more distributed, robust patterns.

**Important:** Dropout is only active during **training**. During inference (generating text), all weights are used. PyTorch handles this automatically when you call `model.eval()` vs `model.train()`.

### **The Scaling Factor — Why Are Values 2.0 in the Output?**

```python
torch.manual_seed(123)
dropout  = torch.nn.Dropout(0.5)   # 50% of values will be zeroed
example  = torch.ones(6, 6)
print(dropout(example))
```

```
Output:
tensor([[2., 2., 0., 2., 2., 0.],
        [0., 0., 0., 2., 0., 2.],
        ...]])
```

With a 50% dropout rate (`p=0.5`), half the values are zeroed out. The remaining values are multiplied by `1/(1-0.5) = 2`. This ensures the **expected sum** of the row stays the same — if every weight was 1 and half are zeroed, you'd normally lose half the signal. Multiplying by 2 compensates, keeping the magnitude consistent between training and inference.

```
┌─────────────────────────────────────────────────────────────┐
│                   WHY THE SCALING WORKS                     │
│                                                             │
│  Suppose a row has 4 weights: [0.25, 0.25, 0.25, 0.25]     │
│  Sum = 1.0                                                  │
│                                                             │
│  Without scaling, 50% dropout gives:                       │
│  [0.00, 0.25, 0.00, 0.25]  → sum = 0.50  (half the signal) │
│                                                             │
│  With scaling (×2), 50% dropout gives:                     │
│  [0.00, 0.50, 0.00, 0.50]  → sum = 1.00  (same signal) ✓   │
│                                                             │
│  Expected value at any position = 0.25 × (1-0.5) × 2 = 0.25│
│  Same as without dropout → training stays stable            │
└─────────────────────────────────────────────────────────────┘
```

### **Applying Dropout to the Actual Attention Weights**

```python
torch.manual_seed(123)
print(dropout(attn_weights))
```

This randomly zeros out some of the already-computed attention weights. Some connections that would have contributed to the context vector are cut. The remaining connections are upscaled to compensate.

```
Before dropout (row 2 "journey"):
  [0.5517, 0.4483, 0.0000, 0.0000, 0.0000, 0.0000]

After 50% dropout (some may be zeroed):
  [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000]  ← entire row zeroed in this example
   OR
  [1.1034, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000]  ← only one kept, scaled up
```

In the actual book output:

```
tensor([[2.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
        [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000],
        [0.7599, 0.6194, 0.6206, 0.0000, 0.0000, 0.0000],
        ...])
```

Note the first row — "Your" only has itself (weight 1.0), and after 2× scaling it becomes 2.0. Row 2 got entirely zeroed by the random dropout mask.

---

## 3.5.3 — The Compact CausalAttention Class

Now all three pieces are combined:

1. Trainable weight matrices (from section 3.4)
2. Causal mask (the -∞ approach)
3. Dropout

Let's go through every line of the class:

```python
class CausalAttention(nn.Module):

    def __init__(self, d_in, d_out, context_length, dropout, qkv_bias=False):
        super().__init__()
```

- `d_in` — input embedding dimension (e.g., 3)
- `d_out` — output embedding dimension (e.g., 2)
- `context_length` — the maximum sequence length the model supports (used to pre-build the mask)
- `dropout` — dropout probability (0.0 means no dropout; 0.1 is typical for GPT)
- `qkv_bias=False` — whether to add a bias term to the Q, K, V projections. GPT-2 uses `False`.

```python
        self.d_out   = d_out
        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key   = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)
```

Same three projection matrices from section 3.4 — these are learned during training.

```python
        self.dropout = nn.Dropout(dropout)
```

Creates a reusable dropout layer with the specified probability. Calling `self.dropout(tensor)` will randomly zero values during training.

```python
        self.register_buffer(
            'mask',
            torch.triu(torch.ones(context_length, context_length), diagonal=1)
        )
```

This is the pre-built causal mask (the upper-triangular 1s matrix). A few things to unpack:

**Why `register_buffer` instead of just storing it as an attribute?**

```
If you do:        self.mask = torch.triu(...)
The mask is:      a plain tensor, not tracked by PyTorch

If you do:        self.register_buffer('mask', torch.triu(...))
The mask is:      registered as a non-parameter buffer

What this means:
  ✓ Automatically moves to GPU when you call model.cuda()
  ✓ Saved and loaded with model.state_dict()
  ✗ NOT updated by the optimizer (it's not a learned parameter)
```

The mask never changes during training — it's always the same upper-triangular pattern. But you want it on the same device (CPU/GPU) as your model automatically. `register_buffer` handles this.

```python
    def forward(self, x):
        b, num_tokens, d_in = x.shape
```

Now the input `x` has **3 dimensions**: `(batch_size, num_tokens, d_in)`.

- `b` = batch size (how many sequences are processed in parallel)
- `num_tokens` = sequence length (could be less than `context_length`)
- `d_in` = input embedding dimension

```
For our example:  batch = 2, tokens = 6, d_in = 3
x.shape = (2, 6, 3)
```

```python
        keys    = self.W_key(x)       # (b, num_tokens, d_out)
        queries = self.W_query(x)     # (b, num_tokens, d_out)
        values  = self.W_value(x)     # (b, num_tokens, d_out)
```

`nn.Linear` is smart enough to handle batched inputs. It applies the same weight matrix to each item in the batch. Result shapes: `(2, 6, 2)` in our example.

```python
        attn_scores = queries @ keys.transpose(1, 2)
```

**Why `.transpose(1, 2)` and not `.T`?**

With 3D tensors (batch + sequence + embedding), `.T` would transpose ALL dimensions and scramble the batch. We only want to transpose the last two dimensions (tokens and embedding):

```
keys shape:                (b=2, num_tokens=6, d_out=2)
keys.transpose(1, 2):      (b=2, d_out=2, num_tokens=6)

queries @ keys.transpose:  (b, 6, 2) @ (b, 2, 6) = (b, 6, 6)
```

PyTorch handles the batch dimension automatically — it does the matrix multiplication independently for each item in the batch.

```python
        attn_scores.masked_fill_(
            self.mask.bool()[:num_tokens, :num_tokens], -torch.inf
        )
```

Several things happening here:

- `self.mask.bool()` — converts the float mask to boolean.
- `[:num_tokens, :num_tokens]` — slices the mask to match the actual sequence length. The pre-built mask might be for `context_length=1024`, but if the current input only has 6 tokens, you only use the top-left `(6×6)` corner.
- `.masked_fill_()` — the trailing underscore means **in-place** modification. This avoids creating a new tensor, saving memory.

```python
        attn_weights = torch.softmax(
            attn_scores / keys.shape[-1]**0.5, dim=-1
        )
```

Same as section 3.4. `keys.shape[-1]` is `d_out` (= 2). Softmax turns the `-inf` positions into exactly 0.

```python
        attn_weights = self.dropout(attn_weights)
```

Randomly zero out some attention weights during training (no-op during eval).

```python
        context_vec = attn_weights @ values
        return context_vec
```

Final weighted sum. Shape: `(b, 6, 6) @ (b, 6, 2) = (b, 6, 2)`.

### **Using the Class**

```python
torch.manual_seed(123)

# Create a batch: 2 copies of our 6-token input
batch          = torch.stack((inputs, inputs), dim=0)
print(batch.shape)
# → torch.Size([2, 6, 3])
#     ↑  ↑  ↑
#  batch seq emb

context_length = batch.shape[1]   # = 6
ca = CausalAttention(d_in=3, d_out=2, context_length=6, dropout=0.0)
context_vecs = ca(batch)

print("context_vecs.shape:", context_vecs.shape)
# → torch.Size([2, 6, 2])
#     ↑  ↑  ↑
#  batch seq enriched_emb
```

The output `(2, 6, 2)` means: 2 sequences, each with 6 tokens, each token now represented by a 2-dimensional enriched context vector.

---

## Complete Flow of 3.5 — End to End Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│               CAUSAL ATTENTION — COMPLETE PIPELINE                   │
│                                                                      │
│  INPUT BATCH                                                         │
│  x shape: (batch=2, tokens=6, d_in=3)                                │
│                                                                      │
│               ↓ project through W_query, W_key, W_value              │
│                                                                      │
│  Q, K, V shapes: (2, 6, 2)                                           │
│                                                                      │
│               ↓ Q @ K.transpose(1,2)                                 │
│                                                                      │
│  attn_scores: (2, 6, 6)  ← raw scores, can be any value              │
│                                                                      │
│               ↓ masked_fill_(upper_triangle, -inf)                   │
│                                                                      │
│  attn_scores: (2, 6, 6)  ← upper triangle is now -inf                │
│  example row 2:                                                      │
│    [0.47,  0.17,  -inf,  -inf,  -inf,  -inf]                         │
│                                                                      │
│               ↓ softmax( · / √d_k )                                  │
│                                                                      │
│  attn_weights: (2, 6, 6) ← each row sums to 1, future = 0.0          │
│  example row 2:                                                      │
│    [0.55,  0.45,  0.00,  0.00,  0.00,  0.00]                         │
│                                                                      │
│               ↓ dropout (training only)                              │
│                                                                      │
│  attn_weights: (2, 6, 6) ← some random weights zeroed + rescaled     │
│                                                                      │
│               ↓ attn_weights @ V                                     │
│                                                                      │
│  context_vecs: (2, 6, 2) ← enriched token representations            │
│                            that only use past + present info         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Numerical Walkthrough — Row by Row After Masking

Here is the final masked attention weight matrix and what each row means:

```
token         can see              final weights (after mask + softmax)
─────────────────────────────────────────────────────────────────────
"Your"   →   [Your]               [1.0000, 0,      0,      0,      0,      0     ]
"journey"→   [Your, journey]      [0.5517, 0.4483, 0,      0,      0,      0     ]
"starts" →   [Your..starts]       [0.3800, 0.3097, 0.3103, 0,      0,      0     ]
"with"   →   [Your..with]         [0.2758, 0.2460, 0.2462, 0.2319, 0,      0     ]
"one"    →   [Your..one]          [0.2175, 0.1983, 0.1984, 0.1888, 0.1971, 0     ]
"step"   →   [Your..step]         [0.1935, 0.1663, 0.1666, 0.1542, 0.1666, 0.1529]
```

**Observation:** "Your" has no choice but to attend 100% to itself because it has no context to its left. "step" has the full sentence available and distributes attention across all 6 tokens. This asymmetry is expected and correct — earlier tokens have less context available.

---

## Section 3.5 — Key Takeaways

**Causal attention solves a training/inference mismatch.** During training the full sentence is available; during inference only past tokens are. The mask aligns training behavior with inference behavior.

**The -∞ trick is the preferred implementation** because it collapses the 3-step process (softmax → zero → renormalize) into 2 steps (fill -∞ → softmax) with the same mathematical result.

**There is no information leakage.** Masking and renormalizing after softmax produces exactly the same weights as if the future tokens never existed. The future token's contribution cancels out algebraically.

**Dropout adds robustness.** By randomly severing attention connections during training, the model can't over-fit to any specific attention pattern, leading to better generalization.

**`register_buffer` is the right way to store the mask** — it keeps it device-aware without making it a learnable parameter.

---

# 6: Extending Single-Head Attention to Multi-Head Attention

> **This section covers:** Why one attention head is not enough, stacking multiple heads naively, then implementing the same idea efficiently with weight splits.

---

## Why Do We Need More Than One Attention Head?

Before any code, the intuition needs to be solid. Throughout sections 3.3–3.5, every token computed **one set of attention weights** over the sequence. That one set captures **one type of relationship** between tokens.

But language is rich. Consider the sentence:

```
"The bank by the river overflowed after the rain"
```

Different aspects of this sentence need to be understood simultaneously:

```
┌──────────────────────────────────────────────────────────────────┐
│        DIFFERENT TYPES OF RELATIONSHIPS IN ONE SENTENCE          │
│                                                                  │
│  Relationship type 1 — SYNTACTIC (grammatical structure):        │
│    "bank" is the subject → "overflowed" is its verb             │
│    An attention head might learn to link subjects to their verbs │
│                                                                  │
│  Relationship type 2 — SEMANTIC (meaning):                       │
│    "bank" + "river" → resolves the ambiguity                     │
│    (bank = riverbank, not financial institution)                 │
│    An attention head might learn to link nouns to context words  │
│                                                                  │
│  Relationship type 3 — TEMPORAL/CAUSAL:                          │
│    "after the rain" → explains why the bank overflowed           │
│    An attention head might learn to link cause and effect        │
│                                                                  │
│  ONE attention head cannot simultaneously optimise for all       │
│  three patterns. It has to pick one direction to optimise.       │
│                                                                  │
│  MULTIPLE attention heads can each specialise in a different     │
│  pattern, and their results are combined at the end.             │
└──────────────────────────────────────────────────────────────────┘
```

This is the core motivation. Multi-head attention runs several attention mechanisms in parallel, each with its **own independent weight matrices** ($W_Q$, $W_K$, $W_V$). Each head learns to focus on different aspects of the input, and their outputs are concatenated into a single enriched representation.

---

## The Big Picture — What Multi-Head Attention Looks Like

```
┌──────────────────────────────────────────────────────────────────┐
│              MULTI-HEAD ATTENTION — OVERVIEW                     │
│                                                                  │
│  Same input X goes into every head                               │
│                                                                  │
│          ┌───────────┐   ┌───────────┐   ┌───────────┐          │
│  X  ───► │  Head 1   │   │  Head 2   │   │  Head N   │          │
│          │ Wq1,Wk1,  │   │ Wq2,Wk2,  │   │ WqN,WkN,  │          │
│          │ Wv1       │   │ Wv2       │   │ WvN       │          │
│          └─────┬─────┘   └─────┬─────┘   └─────┬─────┘          │
│                │               │               │                │
│               Z1              Z2              ZN                │
│                │               │               │                │
│                └───────────────┴───────────────┘                │
│                                │                                │
│                          Concatenate                            │
│                                │                                │
│                     [Z1 | Z2 | ... | ZN]                        │
│                                │                                │
│                          (Optional linear                       │
│                           projection W_out)                     │
│                                │                                │
│                         Final output Z                          │
│                                                                  │
│  Each head learns DIFFERENT attention patterns.                  │
│  Concatenation combines ALL the different perspectives.          │
└──────────────────────────────────────────────────────────────────┘
```

The book introduces two ways to implement this. Section 3.6.1 does it the simple, intuitive way — stack multiple `CausalAttention` modules. Section 3.6.2 refactors this into a single, more efficient class.

---

## 3.6.1 — Stacking Multiple Single-Head Attention Layers

### **The Wrapper Approach**

The simplest multi-head attention is a wrapper that creates `num_heads` independent `CausalAttention` modules and concatenates their outputs:

```python
class MultiHeadAttentionWrapper(nn.Module):

    def __init__(self, d_in, d_out, context_length,
                 dropout, num_heads, qkv_bias=False):
        super().__init__()
        self.heads = nn.ModuleList(
            [CausalAttention(
                d_in, d_out, context_length, dropout, qkv_bias
             )
             for _ in range(num_heads)]
        )

    def forward(self, x):
        return torch.cat([head(x) for head in self.heads], dim=-1)
```

#### **Line-by-Line Breakdown**

```python
self.heads = nn.ModuleList([...])
```

`nn.ModuleList` is like a Python list, but PyTorch-aware. It registers all the contained modules as submodules, so their parameters are properly tracked by the optimizer and moved to GPU when needed. If you used a plain Python list `self.heads = [...]` instead, PyTorch would not know those modules exist and would not train their weights.

```python
[CausalAttention(d_in, d_out, context_length, dropout, qkv_bias)
 for _ in range(num_heads)]
```

This creates `num_heads` completely independent `CausalAttention` objects. Each one has its own separate `W_query`, `W_key`, `W_value` matrices, initialized differently (since PyTorch uses random initialization). So from the start, each head is different and will learn to specialize differently.

```python
def forward(self, x):
    return torch.cat([head(x) for head in self.heads], dim=-1)
```

Each head processes the same input `x` independently and produces a context vector of shape `(batch, tokens, d_out)`. `torch.cat(..., dim=-1)` concatenates them along the last dimension (the embedding dimension).

```
Head 1 output shape:  (batch=2, tokens=6, d_out=2)
Head 2 output shape:  (batch=2, tokens=6, d_out=2)

After cat(dim=-1):    (batch=2, tokens=6, d_out*2=4)
```

### **A Small Concrete Example**

Using `num_heads=2`, `d_out=2`:

```python
torch.manual_seed(123)

context_length = batch.shape[1]   # 6 tokens
d_in,  d_out   = 3, 2

mha = MultiHeadAttentionWrapper(
    d_in, d_out, context_length, dropout=0.0, num_heads=2
)
context_vecs = mha(batch)
print(context_vecs.shape)
# → torch.Size([2, 6, 4])
#     ↑  ↑  ↑
#  batch seq  d_out × num_heads = 2 × 2 = 4
```

```
┌──────────────────────────────────────────────────────────────────┐
│           HOW THE WRAPPER COMBINES TWO HEADS                     │
│                                                                  │
│  INPUT x  shape: (2, 6, 3)                                       │
│                                                                  │
│       ┌──────────────────────┐ ┌──────────────────────┐          │
│       │      HEAD 1          │ │      HEAD 2          │          │
│       │  Wq1: (3×2)          │ │  Wq2: (3×2)          │          │
│       │  Wk1: (3×2)          │ │  Wk2: (3×2)          │          │
│       │  Wv1: (3×2)          │ │  Wv2: (3×2)          │          │
│       └──────────┬───────────┘ └──────────┬───────────┘          │
│                  │                        │                      │
│           Z1: (2, 6, 2)           Z2: (2, 6, 2)                  │
│                  │                        │                      │
│                  └─────────┬──────────────┘                      │
│                            │ cat(dim=-1)                         │
│                            ▼                                     │
│                     Z: (2, 6, 4)                                  │
│                                                                  │
│  For token "journey" (row 2), the output is now a 4-dim vector:  │
│  [head1_dim1, head1_dim2, head2_dim1, head2_dim2]                │
│  = [-0.5874, 0.0058, 0.5891, 0.3257]                            │
└──────────────────────────────────────────────────────────────────┘
```

### **The Problem With the Wrapper Approach**

The wrapper works correctly, but it is **computationally wasteful**. Look at what happens in the forward pass:

```python
[head(x) for head in self.heads]
```

This is a Python for-loop. Each `CausalAttention` module runs one at a time. Inside each module, there is a matrix multiplication `inputs @ W_key`. With `num_heads=12` (GPT-2 small), this means **12 separate sequential matrix multiplications**.

Matrix multiplication is the most expensive operation in transformer training. Running them one by one prevents the GPU from doing them in parallel. Section 3.6.2 fixes this.

---

## 3.6.2 — Implementing Multi-Head Attention with Weight Splits

### **The Key Insight — One Big Matrix Instead of Many Small Ones**

Instead of having 12 separate weight matrices (one per head), the efficient `MultiHeadAttention` class uses **one large weight matrix per Q/K/V** that is equivalent to all heads' matrices stacked together.

```
WRAPPER APPROACH (12 separate matrices per Q/K/V):
  Wq1: (d_in × head_dim)
  Wq2: (d_in × head_dim)
  ...
  Wq12: (d_in × head_dim)
  → 12 separate matrix multiplications

EFFICIENT APPROACH (one combined matrix per Q/K/V):
  Wq: (d_in × d_out)   where d_out = num_heads × head_dim
  → 1 matrix multiplication, then split the result
```

The result of the one big multiplication is the same as running all 12 small ones — but it can be done in a **single parallel GPU operation** rather than 12 sequential operations.

### **The Full MultiHeadAttention Class**

```python
class MultiHeadAttention(nn.Module):

    def __init__(self, d_in, d_out,
                 context_length, dropout, num_heads, qkv_bias=False):
        super().__init__()
        assert (d_out % num_heads == 0), \
            "d_out must be divisible by num_heads"

        self.d_out    = d_out
        self.num_heads = num_heads
        self.head_dim  = d_out // num_heads        # ← dimension per head

        self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_key   = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_value = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.out_proj = nn.Linear(d_out, d_out)   # ← output projection
        self.dropout  = nn.Dropout(dropout)
        self.register_buffer(
            "mask",
            torch.triu(torch.ones(context_length, context_length),
                       diagonal=1)
        )

    def forward(self, x):
        b, num_tokens, d_in = x.shape

        keys    = self.W_key(x)      # (b, num_tokens, d_out)
        queries = self.W_query(x)    # (b, num_tokens, d_out)
        values  = self.W_value(x)    # (b, num_tokens, d_out)

        # Split d_out dimension into (num_heads, head_dim)
        keys    = keys.view(b, num_tokens, self.num_heads, self.head_dim)
        queries = queries.view(b, num_tokens, self.num_heads, self.head_dim)
        values  = values.view(b, num_tokens, self.num_heads, self.head_dim)

        # Transpose to (b, num_heads, num_tokens, head_dim)
        keys    = keys.transpose(1, 2)
        queries = queries.transpose(1, 2)
        values  = values.transpose(1, 2)

        # Scaled dot-product attention per head
        attn_scores = queries @ keys.transpose(2, 3)

        # Apply causal mask
        mask_bool = self.mask.bool()[:num_tokens, :num_tokens]
        attn_scores.masked_fill_(mask_bool, -torch.inf)

        attn_weights = torch.softmax(
            attn_scores / keys.shape[-1]**0.5, dim=-1
        )
        attn_weights = self.dropout(attn_weights)

        # Weighted sum of values
        context_vec = (attn_weights @ values).transpose(1, 2)

        # Merge heads back together
        context_vec = context_vec.contiguous().view(
            b, num_tokens, self.d_out
        )
        context_vec = self.out_proj(context_vec)
        return context_vec
```

### **Unpacking Every Non-Obvious Line**

---

#### **The assertion: `d_out % num_heads == 0`**

```python
assert (d_out % num_heads == 0), "d_out must be divisible by num_heads"
```

Each head needs an equal slice of the output dimension. If `d_out=6` and `num_heads=4`, there is no clean way to split 6 into 4 equal parts. The assertion catches this mistake early.

```
d_out=4, num_heads=2  →  head_dim = 4//2 = 2  ✓  (2 dims per head)
d_out=6, num_heads=4  →  head_dim = 6//4 = 1.5  ✗  (not an integer)
```

---

#### **`self.head_dim = d_out // num_heads`**

This is the dimensionality that **each individual head** works with. In the wrapper, each `CausalAttention` module had `d_out` output dimensions. In the efficient version, each head gets `d_out / num_heads = head_dim` dimensions.

```
GPT-2 small example:
  d_out     = 768  (total embedding size)
  num_heads = 12
  head_dim  = 768 // 12 = 64  (each head works in 64-dim space)
```

---

#### **One `W_query`, `W_key`, `W_value` for all heads**

```python
self.W_query = nn.Linear(d_in, d_out, bias=qkv_bias)
```

This single matrix projects from `d_in` to `d_out`. But `d_out = num_heads × head_dim`, so you can think of it as all heads' query matrices stacked into one.

```
CONCEPTUAL EQUIVALENCE:
  One big:   Wq (d_in × d_out) = Wq (d_in × [num_heads × head_dim])

  Same as:   Wq1 (d_in × head_dim)  ←── head 1's query matrix
             Wq2 (d_in × head_dim)  ←── head 2's query matrix
             ...
  stacked horizontally into one matrix.

  One matrix multiply → results for all heads at once.
```

---

#### **Projecting: `keys = self.W_key(x)`**

```python
keys = self.W_key(x)   # shape: (b, num_tokens, d_out)
```

After this, `keys` is a big tensor where `d_out = num_heads × head_dim`. The information for all heads is interleaved in the last dimension. The next step separates them.

---

#### **Reshaping: `.view(b, num_tokens, self.num_heads, self.head_dim)`**

```python
keys = keys.view(b, num_tokens, self.num_heads, self.head_dim)
```

`.view()` **reshapes** the tensor without copying data. It reinterprets the `d_out` dimension as two dimensions: `num_heads` and `head_dim`.

```
BEFORE .view():
  keys shape: (b=2, num_tokens=6, d_out=4)

  For one token, the 4 values look like:
  [a, b, c, d]
   ↑──────────── all 4 belong to this token

AFTER .view() with num_heads=2, head_dim=2:
  keys shape: (b=2, num_tokens=6, num_heads=2, head_dim=2)

  For one token, the 4 values are now split into 2 heads:
  [[a, b],   ← head 1's key for this token
   [c, d]]   ← head 2's key for this token
```

No computation happens — `.view()` is just a reinterpretation of the same memory.

---

#### **Transposing: `.transpose(1, 2)`**

```python
keys = keys.transpose(1, 2)
# shape: (b, num_heads, num_tokens, head_dim)
```

After `.view()`, the shape is `(b, num_tokens, num_heads, head_dim)`. We need to swap the `num_tokens` and `num_heads` dimensions so that head is the second dimension. This makes the batched matrix multiplication work correctly — PyTorch will treat the first two dimensions `(b, num_heads)` as batch dimensions and multiply the last two `(num_tokens, head_dim)`.

```
BEFORE transpose:  (b=2, num_tokens=6, num_heads=2, head_dim=2)
AFTER  transpose:  (b=2, num_heads=2,  num_tokens=6, head_dim=2)

Think of it as: 2 batches × 2 heads × (6×2 matrix per head)
The matrix multiply will happen independently for each (batch, head) combo.
```

---

#### **Attention scores: `queries @ keys.transpose(2, 3)`**

```python
attn_scores = queries @ keys.transpose(2, 3)
```

At this point:

- `queries` shape: `(b, num_heads, num_tokens, head_dim)`
- `keys.transpose(2, 3)` shape: `(b, num_heads, head_dim, num_tokens)`

The `@` operator performs **batched matrix multiplication** over the last two dimensions, treating `(b, num_heads)` as batch dimensions:

```
For each (batch, head) pair independently:
  (num_tokens × head_dim) @ (head_dim × num_tokens)
  = (num_tokens × num_tokens)   ← attention score matrix for this head

Overall attn_scores shape: (b, num_heads, num_tokens, num_tokens)
                            2      2          6           6
```

This is doing what the wrapper did with a for-loop, but **all heads in parallel** in a single GPU operation.

---

#### **Masking and Softmax — Same as Before**

```python
mask_bool = self.mask.bool()[:num_tokens, :num_tokens]
attn_scores.masked_fill_(mask_bool, -torch.inf)
attn_weights = torch.softmax(attn_scores / keys.shape[-1]**0.5, dim=-1)
```

Exactly the same causal masking from section 3.5. `keys.shape[-1]` is `head_dim` — we scale by `√head_dim` (not `√d_out`), because each head is operating in `head_dim`-dimensional space.

---

#### **Context vector: `(attn_weights @ values).transpose(1, 2)`**

```python
context_vec = (attn_weights @ values).transpose(1, 2)
```

- `attn_weights` shape: `(b, num_heads, num_tokens, num_tokens)`
- `values` shape: `(b, num_heads, num_tokens, head_dim)`
- `attn_weights @ values` shape: `(b, num_heads, num_tokens, head_dim)`

The `.transpose(1, 2)` swaps `num_heads` and `num_tokens` back:

```
BEFORE transpose:  (b, num_heads, num_tokens, head_dim)
AFTER  transpose:  (b, num_tokens, num_heads, head_dim)
```

We do this so we can merge the heads back in the next step.

---

#### **Merging heads: `.contiguous().view(b, num_tokens, self.d_out)`**

```python
context_vec = context_vec.contiguous().view(b, num_tokens, self.d_out)
```

After transposing, shape is `(b, num_tokens, num_heads, head_dim)`. `.view()` merges the last two dimensions back into `d_out = num_heads × head_dim`:

```
BEFORE .view():  (b=2, num_tokens=6, num_heads=2, head_dim=2)
AFTER  .view():  (b=2, num_tokens=6, d_out=4)
```

`.contiguous()` is needed before `.view()` in this case because `.transpose()` does not move data in memory — it changes how the tensor is _interpreted_. But `.view()` requires the data to be laid out contiguously in memory. `.contiguous()` creates a fresh copy with the data in the right order so `.view()` works correctly.

---

#### **Output projection: `self.out_proj(context_vec)`**

```python
self.out_proj = nn.Linear(d_out, d_out)
context_vec   = self.out_proj(context_vec)
```

This is an optional but standard learnable linear transformation applied **after** combining all heads. It projects from `d_out` back to `d_out`.

```
WHY INCLUDE IT?

After concatenating heads, the model has combined information
from different subspaces. The output projection gives the model
a chance to learn a meaningful way to mix and recombine this
information into a final unified representation.

In GPT-2 and most transformer models, this projection is present
and is called the "output projection" or W_o matrix.

It does add parameters:
  d_out × d_out = 4 × 4 = 16 extra parameters (tiny example)
  768 × 768 = 589,824 extra parameters (GPT-2 small)
```

---

### **Using the Class**

```python
torch.manual_seed(123)

batch_size, context_length, d_in = batch.shape   # 2, 6, 3
d_out = 2

mha = MultiHeadAttention(
    d_in, d_out, context_length, dropout=0.0, num_heads=2
)
context_vecs = mha(batch)

print(context_vecs)
print("context_vecs.shape:", context_vecs.shape)
# → torch.Size([2, 6, 2])
```

Note that `d_out=2` with `num_heads=2` means each head gets `head_dim = 2//2 = 1` — a 1-dimensional space per head. The output is still `d_out=2` after combining. This is a very small example for illustration — in real models, `d_out` is much larger.

---

## Wrapper vs Efficient — Side by Side

```
┌────────────────────────────────────────────────────────────────────┐
│          MultiHeadAttentionWrapper  vs  MultiHeadAttention         │
│                                                                    │
│  WRAPPER (Section 3.6.1):                                          │
│  ────────────────────────                                          │
│  ● Creates num_heads separate CausalAttention objects             │
│  ● Each has its OWN Wq, Wk, Wv (shape d_in × d_out each)         │
│  ● Forward loop: [head(x) for head in self.heads]                 │
│  ● Heads run SEQUENTIALLY in Python                               │
│  ● Concatenates outputs along embedding dimension                 │
│  ● Simple to understand — but slow                                │
│                                                                    │
│  EFFICIENT (Section 3.6.2):                                        │
│  ──────────────────────────                                        │
│  ● ONE Wq, Wk, Wv (shape d_in × d_out, where d_out = all heads)  │
│  ● Project ONCE → reshape/transpose to split into heads           │
│  ● Batched matrix multiply handles ALL heads simultaneously       │
│  ● Heads run in PARALLEL on GPU                                   │
│  ● Reshape/transpose to merge heads back                          │
│  ● Optional output projection W_out                               │
│  ● More complex — but fast                                        │
│                                                                    │
│  MATHEMATICALLY IDENTICAL — same attention computation,           │
│  just organized differently for hardware efficiency.              │
└────────────────────────────────────────────────────────────────────┘
```

---

## The Full Shape Journey in MultiHeadAttention

Tracing every tensor through the forward pass with `b=2, num_tokens=6, d_in=3, d_out=4, num_heads=2, head_dim=2`:

```
INPUT x:
  (2, 6, 3)

AFTER W_query/W_key/W_value projections:
  queries: (2, 6, 4)
  keys:    (2, 6, 4)
  values:  (2, 6, 4)

AFTER .view(b, num_tokens, num_heads, head_dim):
  queries: (2, 6, 2, 2)
  keys:    (2, 6, 2, 2)
  values:  (2, 6, 2, 2)

AFTER .transpose(1, 2):
  queries: (2, 2, 6, 2)   ← (batch, heads, tokens, head_dim)
  keys:    (2, 2, 6, 2)
  values:  (2, 2, 6, 2)

AFTER queries @ keys.transpose(2,3):
  attn_scores: (2, 2, 6, 6)   ← (batch, heads, tokens, tokens)

AFTER masking + softmax:
  attn_weights: (2, 2, 6, 6)  ← same shape, values now in [0,1]

AFTER attn_weights @ values:
  context_vec: (2, 2, 6, 2)   ← (batch, heads, tokens, head_dim)

AFTER .transpose(1, 2):
  context_vec: (2, 6, 2, 2)   ← (batch, tokens, heads, head_dim)

AFTER .contiguous().view(b, num_tokens, d_out):
  context_vec: (2, 6, 4)      ← (batch, tokens, d_out)

AFTER out_proj:
  context_vec: (2, 6, 4)      ← same shape, linearly transformed
```

---

## Batched Matrix Multiplication — The Engine of the Efficient Version

The most non-obvious part of the efficient implementation is how PyTorch handles the `@` operator on 4-dimensional tensors. Here is an isolated demonstration:

```python
# Simulate the queries @ keys.T operation with 4D tensors
a = torch.tensor([[[[0.2745, 0.6584, 0.2775, 0.8573],
                    [0.8993, 0.0390, 0.9268, 0.7388],
                    [0.7179, 0.7058, 0.9156, 0.4340]],
                   [[0.0772, 0.3565, 0.1479, 0.5331],
                    [0.4066, 0.2318, 0.4545, 0.9737],
                    [0.4606, 0.5159, 0.4220, 0.5786]]]])
# shape: (1, 2, 3, 4)  →  (batch=1, heads=2, tokens=3, head_dim=4)

print(a @ a.transpose(2, 3))
# shape: (1, 2, 3, 3)
```

PyTorch treats the first two dimensions `(batch=1, heads=2)` as a batch and independently performs `(tokens × head_dim) @ (head_dim × tokens)` for each:

```
Head 1 result:  first_head  = a[0, 0, :, :]   →  (3×4) @ (4×3) = (3×3)
Head 2 result:  second_head = a[0, 1, :, :]   →  (3×4) @ (4×3) = (3×3)

Stacked together: result shape = (1, 2, 3, 3)
```

Both results are computed simultaneously in one GPU kernel — this is the efficiency gain over the wrapper's sequential for-loop.

---

## GPT-2 Scale — Putting the Dimensions in Context

The book mentions that the smallest GPT-2 model (117M parameters) uses:

- `num_heads = 12`
- `d_out = 768` (context vector embedding size)
- `head_dim = 768 // 12 = 64`
- `context_length = 1024`

```
┌─────────────────────────────────────────────────────────────────┐
│              GPT-2 SMALL MULTI-HEAD ATTENTION SHAPES             │
│                                                                  │
│  W_query, W_key, W_value:   each (768 × 768)                     │
│  After projection:          (batch, 1024, 768)                   │
│  After view:                (batch, 1024, 12, 64)                │
│  After transpose:           (batch, 12, 1024, 64)                │
│  attn_scores:               (batch, 12, 1024, 1024)              │
│  attn_weights:              (batch, 12, 1024, 1024)              │
│  After @ values:            (batch, 12, 1024, 64)                │
│  After transpose + view:    (batch, 1024, 768)                   │
│  After out_proj:            (batch, 1024, 768)                   │
│                                                                  │
│  12 heads run in parallel, each working in 64-dim space,         │
│  over 1024 tokens simultaneously.                                │
└─────────────────────────────────────────────────────────────────┘
```

GPT-2 large uses `num_heads=25` and `d_out=1600`, giving `head_dim=64` again — GPT models tend to keep `head_dim` around 64 regardless of scale, and scale up by adding more heads.

---

## Why Does Having Multiple Heads Actually Help?

There is a common confusion: if all heads receive the same input, don't they learn the same thing?

No — for two reasons:

**1. Different initialization.** Each head's weight matrices start with different random values. Gradient descent will push them in different directions from the start.

**2. Different positions in the output.** The concatenated outputs from different heads occupy different regions of the final embedding. The rest of the network (feed-forward layers in the next chapter) receives all of them together and learns to use each head's contribution differently.

In practice, analysis of trained transformer models shows that different heads do specialise. Some heads strongly attend to the previous token (local context). Some attend to the start of the sentence. Some track syntactic dependencies. This specialization emerges from training, not from explicit programming.

---

## Key Takeaways for Section 3.6

**Multi-head attention runs several attention mechanisms in parallel.** Each head has its own weight matrices and learns to capture a different type of token relationship.

**The wrapper (3.6.1) is conceptually simple** — create N `CausalAttention` modules and concatenate their outputs. It is correct but inefficient because heads run sequentially in Python.

**The efficient version (3.6.2) is mathematically identical** but uses a single large projection matrix that is reshaped and transposed to simulate all heads simultaneously in one GPU-parallel batched matrix multiply.

**`.view()` splits the embedding dimension into heads** — no data is copied, just reinterpreted. **`.transpose(1, 2)` moves the head dimension** to position 1 so PyTorch's batched `@` treats each head independently.

**`.contiguous()` is needed before `.view()` after transposing** because transpose changes tensor strides without moving data. `.view()` requires contiguous memory layout.

**The output projection `W_out`** is a final learned linear layer applied after combining all heads. It gives the model a chance to learn how to best mix the information from all heads into a single unified representation.

**`head_dim = d_out // num_heads`** — each head works in a smaller dimensional subspace. The total output capacity is the same as single-head attention with `d_out` dimensions, but divided across specialized heads.

---

_Next: Chapter 4 — Implementing the remaining parts of the GPT architecture (feed-forward layers, layer normalization, positional embeddings) and connecting the MultiHeadAttention module into a full transformer block._
