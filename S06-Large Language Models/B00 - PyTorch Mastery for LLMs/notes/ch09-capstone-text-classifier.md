# Chapter 9: Capstone — Text Classifier

## Table of Contents

1. [What This Capstone Is (and Isn't)](#1-what-this-capstone-is-and-isnt)
2. [The Dataset](#2-the-dataset)
3. [The Architecture, and Why Each Piece Was Chosen](#3-the-architecture-and-why-each-piece-was-chosen)
4. [The Assembled Pipeline](#4-the-assembled-pipeline)
5. [The Debugging Challenge](#5-the-debugging-challenge)
6. [Key Takeaways](#6-key-takeaways)

---

# 1: What This Capstone Is (and Isn't)

This chapter builds one small, real, working project: a **topic
classifier** that reads a short sentence and predicts which of three topics
it's about. It is deliberately **not** a GPT, not an attention mechanism,
not a language model — those are a different, much larger project, and this
track was never about rebuilding one. This is the opposite exercise: taking
the smallest architecture that can genuinely solve a genuine text problem,
and building it with total command of every decision along the way, because
every one of those decisions is something you've now practiced in isolation
across eight chapters.

Nothing in this chapter is new PyTorch material. It's an assembly project —
and, per the last section, a debugging one: the exercises end with a working
classifier that has one deliberately broken line, findable only by using the
instrumentation habits chapter 8 just gave you.

---

# 2: The Dataset

Bundled alongside this chapter: `code/ch09/topic-classification-data.csv` —
120 short synthetic sentences, 40 each about **tech**, **sports**, and
**food** ("the laptop crashed again today", "the team won the game today",
"the soup was served really hot"). It's synthetic on purpose: small enough
to tokenize, batch, and train through in seconds on a CPU, with a vocabulary
of about 110 words and sentence lengths of 4–7 tokens — real enough to
expose every pipeline decision from chapter 6, tiny enough that a bug's
effect on accuracy is impossible to miss.

An 80/20 split gives 96 training and 24 validation examples. **The
vocabulary is built only from the training split** — a genuine best
practice this capstone applies for the first time in the track: fitting a
vocabulary (or any preprocessing statistic) on validation data lets
information leak from the set you're trying to honestly evaluate on. Any
validation word absent from the training vocabulary maps to a reserved
`<unk>` token instead of crashing.

---

# 3: The Architecture, and Why Each Piece Was Chosen

```
token ids (B, T)
      │
      ▼
 nn.Embedding(vocab_size, embed_dim, padding_idx=PAD_ID)     ch05
      │  (B, T, embed_dim)
      ▼
 masked mean-pool over T, using the real-token mask          ch01 §8, ch06 §6
      │  (B, embed_dim)          ← ONE vector per sentence
      ▼
 Linear → GELU → Linear                                       ch04, ch05
      │  (B, num_classes)         ← raw logits, no softmax   ch05 §6
      ▼
 F.cross_entropy(logits, labels)
```

**Why mean-pool instead of attention.** Attention lets every token weigh
every other token — genuinely necessary for a language model that must
track long-range structure. A topic classifier just needs "which words showed
up," and an average of the (masked, real) word vectors already carries that
signal completely. Reaching for attention here would be solving a problem
this dataset doesn't have.

**Why the mask matters more than usual here.** With no attention step to
also mask, the *pooling* step is the only place padding gets excluded from
the computation — get that one line wrong, and there is nothing else in the
architecture to save you. (This is exactly where section 5's planted bug
lives.)

**Why raw logits out of `forward`.** Chapter 5's gotcha, restated: the model
returns logits; `F.cross_entropy` applies `softmax` internally. A `softmax`
at the end of `forward` here would be the exact double-softmax bug from that
chapter, silently, again.

---

# 4: The Assembled Pipeline

The exercises build this in order, each step reaching back to the chapter
that taught it:

1. **Tokenizer + vocabulary** (ch01 dtype rules) — whitespace split, a
   `<pad>`/`<unk>`-prefixed vocabulary built from the training texts only.
2. **Dataset + collate_fn** (ch06) — a map-style `Dataset` returning
   un-padded `(token_ids, label)` pairs; a `collate_fn` using `pad_sequence`
   for dynamic per-batch padding, producing the boolean mask alongside it.
3. **The model** (ch04, ch05) — `nn.Module` composing `Embedding`, the
   masked mean-pool, and a two-layer MLP head, built as its own class so
   parameter registration (ch04's plain-list trap) is something you're
   watching for by habit now, not by reminder.
4. **The training loop** (ch07) — `AdamW` with parameter groups (decay only
   the weight matrices), a short warmup + cosine schedule, gradient
   clipping, the correct seven-step order, and `train()`/`eval()` switched
   correctly around the validation pass.
5. **Checkpointing** (ch07, ch08) — save model **and** optimizer **and**
   scheduler **and** epoch; demonstrate that resuming continues training
   without the momentum-loss stumble a model-only checkpoint would cause.
6. **The debugging challenge** (ch08, next section).

---

# 5: The Debugging Challenge

The final exercise hands you a `BuggyTextClassifier` — architecturally
identical to what you just built, trained the same way, that does **not
crash**. It trains. It reports a loss. It just never gets good, and its
validation accuracy lands at or below random guessing (chance, for three
balanced classes, is roughly 33%).

The method is exactly chapter 8, section 5's — **read the symptom, don't
just re-read the code line by line hoping to spot it by eye.** A genuinely
useful first move: pool the *same* model's output for two completely
different sentences and compare them.

```python
pooled_sentence_a = model.pool_only(sentence_a)
pooled_sentence_b = model.pool_only(sentence_b)
print((pooled_sentence_a - pooled_sentence_b).abs().max())    # near zero?!
```

If two unrelated sentences produce nearly *identical* pooled vectors, the
model has stopped seeing the input at all somewhere before that point — and
there is exactly one place in this architecture where the input could be
thrown away without crashing: the mask. That instrumentation-first habit —
compare actual behavior against an invariant that should obviously hold
("different inputs should not produce identical internal representations")
— is the whole chapter 8 method, applied to a correctness bug instead of a
crash.

---

# 6: Key Takeaways

Every decision guide from chapters 1–8 shows up here at least once: dtype
and masking (ch01), the loss's raw-logits contract (ch05), the collate/mask
pipeline (ch06), the training loop's order and optimizer setup (ch07), and —
the final test — diagnosing a silent bug the way chapter 8 taught, by
instrumenting and checking an invariant rather than guessing. That's the
entire track, once, in anger, on a project small enough to hold in your head
completely.
