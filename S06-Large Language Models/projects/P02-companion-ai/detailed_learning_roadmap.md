# Companion AI — Detailed Learning Roadmap
**Companion to:** `02_companion_ai_full_stack.md`  
**Purpose:** Turn the layer-by-layer build plan into structured daily learning — theory first, then code, then measurement, then reflection.

---

## Table of Contents

- [How to Use This File](#how-to-use-this-file)
- [Pre-Day-1 Checklist](#pre-day-1-checklist)
- [Layer 0 — Day 1: Data Pipeline](#layer-0--day-1-data-pipeline)
- [Layer 1 — Day 2 (Morning): Custom Tokenizer](#layer-1--day-2-morning-custom-tokenizer)
- [Layer 2 — Days 2–3: Domain Embedding Model](#layer-2--days-23-domain-embedding-model)
- [Layer 3 — Day 4: Domain-Continued Pre-training (DAPT)](#layer-3--day-4-domain-continued-pre-training-dapt)
- [Layer 4 — Day 5: Supervised Fine-tuning (SFT)](#layer-4--day-5-supervised-fine-tuning-sft)
- [Layer 5 — Day 6: Reward Model](#layer-5--day-6-reward-model)
- [Layer 6 — Day 7: DPO Alignment](#layer-6--day-7-dpo-alignment)
- [Layer 7 — Day 8: GRPO Reasoning](#layer-7--day-8-grpo-reasoning)
  - [Phase Checkpoint — after Day 8](#phase-checkpoint--after-day-8)
- [Layer 8 — Day 9: RAG Knowledge Base](#layer-8--day-9-rag-knowledge-base)
- [Layer 9 — Day 10: Memory System](#layer-9--day-10-memory-system)
- [Layer 10 — Day 11: Safety Layer](#layer-10--day-11-safety-layer)
- [Layer 11 — Day 12: Persona and Serving](#layer-11--day-12-persona-and-serving)
- [Layer 12 — Day 13: Evaluation Pipeline](#layer-12--day-13-evaluation-pipeline)
- [Layer 13 — Day 14: Integration (Wire It Together)](#layer-13--day-14-integration-wire-it-together)
- [Layer 13 — Day 15: Evaluation, Comparison, README](#layer-13--day-15-evaluation-comparison-readme)
  - [Phase 4 Checkpoint (Final)](#phase-4-checkpoint-final)
- [Layer Dependency Table](#layer-dependency-table)
- [Resources Index](#resources-index)

---

## How to Use This File

`02_companion_ai_full_stack.md` tells you **what** to build each day.  
This file tells you **how to learn it well**.

The same daily rhythm as P01 — but with one important difference: **this project accumulates**. The embedding model you build on Day 3 is the exact model that powers RAG on Day 9 and memory retrieval on Day 10. The reward model you train on Day 6 is the judge your DPO trainer uses on Day 7. If you skip a layer or take a shortcut, you'll feel it three days later.

That's the point. Building everything for one domain makes each layer *motivate* the next. Follow this order:

1. **Theory first** — read before you code. Know why this layer exists.
2. **Concept map** — define the key terms (both ML and therapy domain) before running anything.
3. **Step-by-step experiment** — numbered steps with code scaffolding.
4. **Log it** — record the output checkpoint path and key metrics for this layer.
5. **Reflect** — three questions: one technical, one domain, one ethical.
6. **Connect** — the exact checkpoint file tomorrow needs from today.

**Ethics note:** This project works with sensitive mental health text. Treat the data with the same care you'd want applied to your own conversations.

---

## Pre-Day-1 Checklist

Do this the evening before Day 1.

### Accounts and access
- [ ] HuggingFace account — log in and generate a token (you'll need it for Mistral)
- [ ] Request access to `mistralai/Mistral-7B-v0.1` on HuggingFace
- [ ] Create a Weights & Biases account — get your API key
- [ ] Reddit API credentials (for Pushshift scraping) — apply at reddit.com/prefs/apps

### Tool installs
```bash
pip install transformers datasets peft trl accelerate bitsandbytes
pip install sentence-transformers
pip install presidio-analyzer presidio-anonymizer  # PII detection
pip install datasketch                              # MinHash deduplication
pip install faiss-gpu chromadb qdrant-client
pip install vllm unsloth
pip install bert-score evaluate                    # evaluation metrics
pip install wandb
```

### Project directory
```bash
mkdir -p ~/companion-ai/{data/{raw,clean,splits},checkpoints,logs,evals}
```

### Ethical foundation (read before Day 1)
Read: Bender et al. 2021 ("On the Dangers of Stochastic Parrots") — just the abstract and Section 5 (data). This primes you to think about what's in the data you're about to collect, not just how much of it there is.

---

---

## Layer 0 — Day 1: Data Pipeline

**Learning objective:** Understand why data quality and contamination control are the hardest part of any ML project — and set up a pipeline you can trust.

---

#### Morning theory (45 min)

**Read:** Gururangan et al. 2020 ("Don't Stop Pretraining") — Sections 1–3. The core question: does domain-specific data improve performance, and by how much? You're about to answer this question empirically for the therapy domain.

**Focus question:** *The paper shows that DAPT (domain-adaptive pre-training) helps even after fine-tuning. What does that suggest about the relationship between pre-training data and fine-tuning data? Why can't fine-tuning alone make up for a mismatch in pre-training domain?*

---

#### Concept map — define these before coding

| Term | Your definition |
|---|---|
| Data contamination | |
| PII (personally identifiable information) | |
| MinHash deduplication | |
| Train / val / test split (why no overlap) | |
| CBT (Cognitive Behavioural Therapy) | |
| DBT (Dialectical Behaviour Therapy) | |
| Calibration data (for tokenizer training) | |

---

#### Step-by-step experiment

**Step 1 — Download structured datasets**
```python
from datasets import load_dataset

counsel_chat = load_dataset("nbertagnolli/counsel-chat")
empathetic = load_dataset("facebook/empathetic_dialogues")

print(f"Counsel Chat: {len(counsel_chat['train'])} examples")
print(f"EmpatheticDialogues: {len(empathetic['train'])} examples")
print("\nSample Counsel Chat entry:")
print(counsel_chat['train'][0])
```
Read 10 examples from each. What is the emotional register? How formal is the language?

**Step 2 — PII detection and removal**
```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def anonymize_text(text: str) -> str:
    results = analyzer.analyze(text=text, language="en")
    return anonymizer.anonymize(text=text, analyzer_results=results).text

# Test on a sample
sample = "My name is John and I live in Seattle. I've been feeling anxious since March."
print(anonymize_text(sample))
```

**Step 3 — MinHash deduplication**
```python
from datasketch import MinHash, MinHashLSH

def get_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for word in text.lower().split():
        m.update(word.encode("utf8"))
    return m

lsh = MinHashLSH(threshold=0.8, num_perm=128)
unique_texts = []
for i, text in enumerate(all_texts):
    m = get_minhash(text)
    if not lsh.query(m):
        lsh.insert(str(i), m)
        unique_texts.append(text)

print(f"Before dedup: {len(all_texts)}  After: {len(unique_texts)}")
```

**Step 4 — Split into three piles (critical)**
```python
import json
from pathlib import Path

# These piles must NOT overlap
splits = {
    "pretrain": [],    # raw text for language modelling (Layer 3)
    "finetune": [],    # conversation pairs for SFT/DPO (Layers 4, 6)
    "rag": [],         # CBT/DBT factual documents (Layer 8)
    "eval": [],        # held-out — never touch during training
}
# Assign Counsel Chat → finetune + eval
# Assign EmpatheticDialogues → finetune + pretrain
# Assign CBT/DBT workbook text → rag
# Save each pile
for name, data in splits.items():
    Path(f"~/companion-ai/data/splits/{name}.json").expanduser().write_text(json.dumps(data, indent=2))
```

**Step 5 — Measure your corpus**

| Split | N examples | Avg length (words) | Notes |
|---|---|---|---|
| pretrain | | | |
| finetune | | | |
| rag | | | |
| eval | | | |

---

#### What to log

| Metric | Value |
|---|---|
| Total raw examples collected | |
| Examples after PII removal | |
| Examples after deduplication | |
| Final finetune split size | |
| Final pretrain split size | |
| Final RAG documents | |

---

#### Evening reflection

1. *You separated finetune and eval sets before doing anything else. Why is this the most important step you did today?*
2. *The therapy domain has specific vocabulary (hypervigilance, dissociation, rumination). What would a general tokenizer do with these words? Why does that matter for the model?*
3. *You processed real mental health conversations. What obligations do you think that creates — even if all the data is publicly sourced?*

---

#### Connection

Tomorrow's tokenizer training (Layer 1) consumes the `pretrain` split. Tomorrow's embedding model training (Layer 2) consumes the `finetune` split. Both need today's cleaned, deduplicated data — **do not modify the splits after today**.

---

---

## Layer 1 — Day 2 (Morning): Custom Tokenizer

**Learning objective:** Understand what a tokenizer learns from its training corpus and be able to measure whether domain-specific training improves compression on domain text.

---

#### Morning theory (30 min)

**Read:** Sennrich et al. 2016 ("Neural Machine Translation of Rare Words with Subword Units") — Sections 1–3. This is the original BPE paper. The core insight: instead of a fixed vocabulary, learn a vocabulary from the data by iteratively merging frequent character pairs.

**Focus question:** *BPE starts from characters and merges the most frequent pairs. If your therapy corpus has the word "hypervigilance" appearing 5,000 times, what will BPE do with it compared to a tokenizer trained on general web text where it appears 50 times?*

---

#### Concept map

| Term | Your definition |
|---|---|
| BPE (Byte Pair Encoding) | |
| Vocabulary size (trade-off) | |
| Compression ratio (chars/token) | |
| Special tokens | |
| Tokenizer fertility | |

---

#### Step-by-step experiment

**Step 1 — Train a BPE tokenizer on your therapy corpus**
```python
from tokenizers import Tokenizer, models, trainers, pre_tokenizers

tokenizer = Tokenizer(models.BPE())
tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)

trainer = trainers.BpeTrainer(
    vocab_size=32000,
    special_tokens=[
        "<|endoftext|>",
        "<|system|>", "<|user|>", "<|assistant|>",
        "<|memory|>",    # injecting episodic memory
        "<|crisis|>",    # safety flag
        "<|end|>",
    ],
    min_frequency=2,
)

# Train on pretrain split
import glob
corpus_files = glob.glob("~/companion-ai/data/splits/pretrain*.txt")
tokenizer.train(files=corpus_files, trainer=trainer)
tokenizer.save("~/companion-ai/checkpoints/therapy_tokenizer.json")
```

**Step 2 — Measure compression vs GPT-2 tokenizer**
```python
from transformers import GPT2Tokenizer
from tokenizers import Tokenizer as HFTokenizer

therapy_tok = HFTokenizer.from_file("~/companion-ai/checkpoints/therapy_tokenizer.json")
gpt2_tok = GPT2Tokenizer.from_pretrained("gpt2")

# Load 500 therapy sentences and 500 general sentences
therapy_samples = [...]    # from your finetune split
general_samples = [...]    # from wikitext-2

for label, samples in [("therapy text", therapy_samples), ("general text", general_samples)]:
    t_tokens = sum(len(therapy_tok.encode(s).ids) for s in samples)
    g_tokens = sum(len(gpt2_tok.encode(s)) for s in samples)
    chars = sum(len(s) for s in samples)
    print(f"{label}: therapy_tok={chars/t_tokens:.2f} chars/tok | gpt2={chars/g_tokens:.2f} chars/tok")
```

**Step 3 — Inspect how therapy-specific words are tokenized**
```python
test_words = ["hypervigilance", "dissociation", "rumination", "cognitive distortion",
              "dialectical behaviour therapy", "attachment theory", "EMDR", "grounding"]

for word in test_words:
    therapy_ids = therapy_tok.encode(word).ids
    gpt2_ids = gpt2_tok.encode(word)
    print(f"{word}: therapy={len(therapy_ids)} tokens | gpt2={len(gpt2_ids)} tokens")
```

---

#### What to log

| Metric | Value |
|---|---|
| Vocab size | 32,000 |
| Chars/token on therapy text (your tokenizer) | |
| Chars/token on therapy text (GPT-2) | |
| Compression improvement (%) | |
| Number of therapy-specific tokens in vocab | |

---

#### Evening reflection (continue into Layer 2 afternoon)

1. *If the compression improvement is under 5%, does that mean training a domain tokenizer was a waste? What did you learn from the process even if the gain is small?*
2. *You added special tokens `<|memory|>` and `<|crisis|>`. These will appear in no training data initially — what does that mean for how the model will treat them?*
3. *Should you share this tokenizer publicly? What are the risks if someone uses a therapy-domain tokenizer for a non-therapy purpose?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/therapy_tokenizer.json`  
Used by: Layer 3 (continued pre-training uses this tokenizer to tokenize the training corpus), Layer 4 (SFT), Layer 5 (reward model).

---

---

## Layer 2 — Days 2–3: Domain Embedding Model

**Learning objective:** Understand contrastive learning — why similarity in embedding space should reflect *therapeutic similarity* (emotional register, intent) not just lexical overlap.

---

#### Morning theory — Day 2 afternoon (45 min)

**Read:** Reimers & Gurevych 2019 ("Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks") — Sections 1–4. Focus on the training objective: given a sentence pair, is the cosine similarity between their embeddings high (similar) or low (dissimilar)?

**Focus question:** *A general sentence encoder might rate "I feel worthless" and "I feel like a burden" as moderately similar. A therapy-fine-tuned encoder should rate them as highly similar (same emotional state, same risk level). What training data would teach that distinction?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Contrastive learning | |
| Anchor / positive / negative (triplet) | |
| MultipleNegativesRankingLoss | |
| Cosine similarity | |
| Emotional register (vs. topic similarity) | |
| In-batch negatives | |

---

#### Step-by-step experiment

**Step 1 — Build therapy triplets from EmpatheticDialogues**
```python
from sentence_transformers import InputExample
from datasets import load_dataset
import random

ds = load_dataset("facebook/empathetic_dialogues", split="train")

# Group by emotion label
from collections import defaultdict
by_emotion = defaultdict(list)
for ex in ds:
    by_emotion[ex["context"]].append(ex["prompt"])

# Build triplets
triplets = []
emotions = list(by_emotion.keys())
for emotion, utterances in by_emotion.items():
    if len(utterances) < 2:
        continue
    for anchor in utterances[:20]:
        # Positive: same emotion
        positive = random.choice([u for u in utterances if u != anchor])
        # Negative: different emotion
        neg_emotion = random.choice([e for e in emotions if e != emotion])
        negative = random.choice(by_emotion[neg_emotion])
        triplets.append(InputExample(texts=[anchor, positive, negative]))

print(f"Built {len(triplets)} triplets")
```

**Step 2 — Also build triplets from Counsel Chat**
```python
# Anchor: patient message
# Positive: empathetic therapist response (same emotional register)
# Negative: a different patient message (different topic/register)
from datasets import load_dataset

cc = load_dataset("nbertagnolli/counsel-chat", split="train")
for ex in cc:
    anchor = ex["questionText"]
    positive = ex["answerText"]
    # negative: a random other patient question
    neg_idx = random.randint(0, len(cc) - 1)
    negative = cc[neg_idx]["questionText"]
    triplets.append(InputExample(texts=[anchor[:300], positive[:300], negative[:300]]))
```

**Step 3 — Fine-tune bge-base-en-v1.5 with MNRL**
```python
from sentence_transformers import SentenceTransformer, losses
from torch.utils.data import DataLoader

model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# Convert triplets to pair format for MNRL (anchor, positive — negatives are in-batch)
pairs = [InputExample(texts=[t.texts[0], t.texts[1]]) for t in triplets]
loader = DataLoader(pairs, shuffle=True, batch_size=32)
loss = losses.MultipleNegativesRankingLoss(model)

model.fit(
    train_objectives=[(loader, loss)],
    epochs=3,
    warmup_steps=200,
    show_progress_bar=True,
)
model.save("~/companion-ai/checkpoints/therapy_embedder")
```

**Step 4 — Evaluate: does it rank emotionally similar sentences higher?**
```python
model = SentenceTransformer("~/companion-ai/checkpoints/therapy_embedder")

test_pairs = [
    ("I feel completely worthless", "I feel like a burden to everyone"),           # should be HIGH
    ("I feel completely worthless", "The weather is nice today"),                  # should be LOW
    ("I haven't left my room in a week", "I've been isolating myself from others"),# should be HIGH
    ("I haven't left my room in a week", "I love going for walks"),               # should be LOW
]

for a, b in test_pairs:
    embs = model.encode([a, b])
    sim = float((embs[0] / (embs[0]**2).sum()**0.5) @ (embs[1] / (embs[1]**2).sum()**0.5))
    print(f"  sim={sim:.3f} | '{a[:40]}' ↔ '{b[:40]}'")
```

---

#### What to log

| Metric | Value |
|---|---|
| N triplets built | |
| Training epochs | 3 |
| Checkpoint path | `~/companion-ai/checkpoints/therapy_embedder` |
| Similarity: worthless ↔ burden | |
| Similarity: worthless ↔ weather | |
| Similarity: isolating ↔ isolating (paraphrase) | |

---

#### Evening reflection

1. *Your embedding model learns that "I feel worthless" and "I feel like a burden" are similar. A general model doesn't. What is the practical consequence when this embedder powers the RAG system (Day 9)?*
2. *You used in-batch negatives — all other anchors in the batch act as negatives for each positive. When does this create a problem (what if two anchors in the same batch are actually similar)?*
3. *You're training an embedder on therapy conversations. If this embedder is later used to power a search engine over mental health content, who should be responsible for how it's used?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/therapy_embedder`  
Used by: Layer 8 (RAG — embed CBT/DBT chunks and query embeddings), Layer 9 (memory retrieval — find relevant episodic memories).

---

---

## Layer 3 — Day 4: Domain-Continued Pre-training (DAPT)

**Learning objective:** Understand the difference between pre-training and fine-tuning objectives, and why continuing pre-training on domain text before any fine-tuning systematically improves downstream performance.

---

#### Morning theory (45 min)

**Read:** Gururangan et al. 2020 ("Don't Stop Pretraining") — now read Sections 4–6 (the experiments). You read the motivation on Day 1; now look at the actual numbers. How much does DAPT improve performance? When does it matter more vs. less?

**Focus question:** *The paper shows that DAPT helps most when the domain is far from the pre-training data distribution. Is therapy language far from general web text? What specific linguistic features make it different?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Continued pre-training vs fine-tuning | |
| Next-token prediction objective | |
| Learning rate (why low for DAPT) | |
| Catastrophic forgetting | |
| Domain perplexity | |
| General perplexity (catastrophic forgetting indicator) | |

---

#### Step-by-step experiment

**Step 1 — Load Mistral-7B base and measure baseline perplexity**
```python
import torch
import math
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "mistralai/Mistral-7B-v0.1"
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Measure perplexity on your therapy pretrain split (first 10K tokens)
# and on wikitext-2 (general baseline)
```
Record: base model perplexity on therapy text and on general text.

**Step 2 — Format pretrain corpus as raw text (no instruction format)**
```python
from datasets import Dataset

# Load your pretrain split — raw text, no Q&A format
texts = [...]  # from ~/companion-ai/data/splits/pretrain.json

def tokenize(example):
    return tokenizer(example["text"], truncation=True, max_length=2048, return_overflowing_tokens=True)
```

**Step 3 — Continue pre-training**
```python
from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

trainer = Trainer(
    model=model,
    args=TrainingArguments(
        output_dir="~/companion-ai/checkpoints/dapt_mistral7b",
        num_train_epochs=1,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=2e-5,              # low: preserve general knowledge
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=100,
        save_steps=500,
        report_to="wandb",
        run_name="companion_dapt",
    ),
    train_dataset=tokenized_dataset,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)
trainer.train()
```

**Step 4 — Measure perplexity after DAPT**

Compute therapy perplexity and general perplexity again. The therapy perplexity should drop. The general perplexity should stay roughly flat — if it rises significantly, your LR was too high.

**Step 5 — Qualitative check**
```python
# Generate from the same prompt with base model and DAPT model
prompt = "What does it mean to practise radical acceptance?"
# Compare the two outputs — does the DAPT model sound more fluent in therapy language?
```

---

#### What to log

| Metric | Base Mistral-7B | After DAPT |
|---|---|---|
| Therapy perplexity | | |
| General perplexity (wikitext-2) | | |
| Training steps | — | |
| Learning rate | — | 2e-5 |

---

#### Evening reflection

1. *Your general perplexity went up / stayed flat / went down after DAPT. What does each outcome mean, and what would you do if it went up significantly?*
2. *DAPT uses next-token prediction on raw text — same objective as the original pre-training. Why doesn't the model just "unlearn" the general patterns during DAPT?*
3. *You trained on Reddit mental health posts and therapy transcripts. The people who wrote those posts didn't know they'd be used for this. How do you think about that?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/dapt_mistral7b`  
Used by: Layer 4 (SFT starts from this checkpoint, NOT from the original Mistral — this is the domain foundation).

---

---

## Layer 4 — Day 5: Supervised Fine-tuning (SFT)

**Learning objective:** Understand the difference between pre-training (learning language) and instruction fine-tuning (learning a conversational style) — and why the format of your training examples matters as much as the content.

---

#### Morning theory (45 min)

**Read:** Wei et al. 2022 ("Finetuned Language Models Are Zero-Shot Learners") — Sections 1–3. This is the original instruction tuning paper. The key insight: formatting text as instruction-following examples teaches the model a *generalizable* ability to follow instructions, not just to memorise specific answers.

**Focus question:** *The paper shows that instruction tuning transfers to tasks the model never saw during fine-tuning. What does that tell you about what the model is actually learning during SFT? Is it learning facts, or something else?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Instruction fine-tuning | |
| Chat template / conversation format | |
| LoRA (why use it here instead of full fine-tune) | |
| SFTTrainer | |
| Therapeutic validation (vs. advice) | |
| Open question (Socratic technique) | |

---

#### Step-by-step experiment

**Step 1 — Format Counsel Chat as therapeutic conversations**
```python
SYSTEM = """You are Sama — a compassionate companion. You listen deeply, validate 
emotions, and ask gentle open questions. You never give unsolicited advice. 
You remember what the person has shared with you."""

def format_example(ex: dict) -> str:
    return (
        f"<|system|>\n{SYSTEM}\n"
        f"<|user|>\n{ex['questionText']}\n"
        f"<|assistant|>\n{ex['answerText']}\n"
        f"<|end|>"
    )

# Inspect 5 examples — does the format look right?
for ex in counsel_chat['train'][:5]:
    print(format_example(ex))
    print("---")
```

**Step 2 — Load the DAPT checkpoint (not original Mistral)**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

model = AutoModelForCausalLM.from_pretrained(
    "~/companion-ai/checkpoints/dapt_mistral7b",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
lora_config = LoraConfig(
    r=64, lora_alpha=128,
    target_modules="all-linear",
    lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```

**Step 3 — Train**
```python
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=formatted_dataset,
    args=SFTConfig(
        output_dir="~/companion-ai/checkpoints/sft_sama",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        bf16=True,
        gradient_checkpointing=True,
        report_to="wandb",
        run_name="companion_sft",
    ),
    formatting_func=format_example,
    max_seq_length=1024,
)
trainer.train()
```

**Step 4 — Evaluate on 20 held-out patient messages**

For each message, generate a response. Manually rate each response on:
- Does it validate the emotion? (Y/N)
- Does it ask an open question? (Y/N)
- Does it give unsolicited advice? (Y/N — should be N)

---

#### What to log

| Metric | Value |
|---|---|
| Checkpoint path | `~/companion-ai/checkpoints/sft_sama` |
| Trainable parameters (%) | |
| Validation rate (% of responses that validate) | |
| Question rate (% of responses with open question) | |
| Advice rate (% of responses with advice) | |

---

#### Evening reflection

1. *Your SFT model validates emotion X% of the time. That's up from the base model's X%. But it still gives advice Y% of the time. Why is eliminating advice harder than adding validation?*
2. *You fine-tuned on the DAPT checkpoint, not the original Mistral. Run the same SFT on the original Mistral too (briefly). Do you see a difference in output quality? That difference is the value of DAPT.*
3. *A therapeutic companion that sounds convincing but gives bad advice could be harmful. At what point does "sounds better" cross into "more dangerous"?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/sft_sama` (LoRA adapter — merge before using)  
Used by: Layer 5 (reward model training needs SFT-generated responses to rank), Layer 6 (DPO starts from the merged SFT checkpoint).

---

---

## Layer 5 — Day 6: Reward Model

**Learning objective:** Understand the Bradley-Terry model — how pairwise preferences can train a scalar reward signal — and why having a computable reward is necessary before DPO or GRPO.

---

#### Morning theory (45 min)

**Read:** Ziegler et al. 2019 ("Fine-Tuning Language Models from Human Preferences") — Sections 1–3. This is the original RLHF paper. Focus on how the reward model is trained: pairs of responses, a human picks the better one, the model learns to predict that preference.

**Focus question:** *The reward model outputs a single scalar for each response. How does training on pairwise comparisons (A is better than B) teach the model to output absolute scores? What is the Bradley-Terry model doing mathematically?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Bradley-Terry model | |
| Scalar head (classification head for reward) | |
| Chosen / rejected (preference pair) | |
| Reward model overfitting | |
| Five dimensions of a good therapy response | |

---

#### Step-by-step experiment

**Step 1 — Generate candidate responses from your SFT model**
```python
# For each of 2,000 patient messages, generate 4 responses with temperature sampling
# These will be ranked to create preference pairs
```

**Step 2 — Rank with an automated judge + manual spot-check**
```python
# Use GPT-4o or Claude as automated ranker
import openai

JUDGE_PROMPT = """Rate this therapy response on these 5 dimensions (1-5 each):
1. Validation: does it acknowledge the emotion?
2. Curiosity: does it ask an open question?
3. Safety: does it avoid reinforcing harmful thoughts?
4. Non-directive: does it avoid unsolicited advice?
5. Continuity: does it connect to what was said?

Response: {response}

Return a JSON: {{"validation": X, "curiosity": X, "safety": X, "non_directive": X, "continuity": X}}"""
```

Spot-check 50 pairs manually — does the automated judge agree with your intuition?

**Step 3 — Train the reward model**
```python
from transformers import AutoModelForSequenceClassification
from trl import RewardTrainer, RewardConfig

reward_model = AutoModelForSequenceClassification.from_pretrained(
    "~/companion-ai/checkpoints/sft_sama",   # init from SFT checkpoint
    num_labels=1,
)

trainer = RewardTrainer(
    model=reward_model,
    args=RewardConfig(
        output_dir="~/companion-ai/checkpoints/reward_sama",
        per_device_train_batch_size=2,
        num_train_epochs=1,
        report_to="wandb",
    ),
    train_dataset=preference_dataset,   # chosen/rejected pairs
)
trainer.train()
```

**Step 4 — Validate the reward model**

Generate 10 pairs you're confident about (e.g., validating response vs. dismissive advice). Does the reward model score the better one higher in every case?

---

#### What to log

| Metric | Value |
|---|---|
| Checkpoint path | `~/companion-ai/checkpoints/reward_sama` |
| Preference pairs used | |
| Validation accuracy (does RM prefer human-preferred response?) | |
| Correlation with manual ratings | |

---

#### Evening reflection

1. *You used GPT-4o as an automated judge. In what ways might GPT-4o's definition of a "good therapy response" differ from an actual therapist's? What would that do to your reward model?*
2. *The reward model is initialised from the SFT checkpoint, not from a fresh Mistral. Why does that make sense architecturally?*
3. *You're building a reward model that scores "good therapy." Who should be involved in defining what "good therapy" means here — and who currently isn't?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/reward_sama`  
Used by: Layer 6 (DPO validation — score DPO outputs before/after), Layer 7 (GRPO reward signal supplement), Layer 12 (automated evaluation pipeline).

---

---

## Layer 6 — Day 7: DPO Alignment

**Learning objective:** Understand why DPO is a cleaner alternative to PPO for alignment — and feel the difference between an SFT model and a DPO-aligned model on the same prompts.

---

#### Morning theory (45 min)

**Read:** Rafailov et al. 2023 ("Direct Preference Optimization: Your Language Model is Secretly a Reward Model") — Sections 1–4. The key math: the optimal policy under the RLHF objective can be expressed directly in terms of the reference policy, eliminating the need for an explicit reward model during training.

**Focus question:** *DPO still uses a reference model (frozen copy of the SFT checkpoint). What is the reference model's role? What would happen to the policy if you removed it?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Reference policy (frozen) | |
| Policy model (trained) | |
| β (beta) — KL penalty coefficient | |
| Log-ratio in DPO loss | |
| Chosen / rejected pairs | |
| Therapeutic style vs general style | |

---

#### Step-by-step experiment

**Step 1 — Build preference pairs specific to therapy style**

| User message | Chosen | Rejected |
|---|---|---|
| "I've been feeling really down" | "That sounds heavy. How long has it been this way?" | "Have you tried exercise or better sleep?" |
| "I think I'm worthless" | "That sounds like a painful place. What does worthless feel like for you?" | "You're not worthless! You have so much to offer." |
| "I don't know what to do" | "It sounds like you're in a really uncertain place. What feels most unclear?" | "Here are three steps that might help..." |

Generate 2,000-5,000 such pairs from your SFT model + reward model judge.

**Step 2 — Train DPO**
```python
from trl import DPOTrainer, DPOConfig

trainer = DPOTrainer(
    model=sft_model,        # policy (trained)
    ref_model=sft_model_ref,  # reference (frozen)
    args=DPOConfig(
        output_dir="~/companion-ai/checkpoints/dpo_sama",
        beta=0.1,
        max_length=1024,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=1,
        learning_rate=5e-7,
        bf16=True,
        report_to="wandb",
        run_name="companion_dpo",
    ),
    train_dataset=preference_dataset,
    processing_class=tokenizer,
)
trainer.train()
```

**Step 3 — Compare SFT vs DPO on 10 prompts**

For the same 10 patient messages, generate from both models. Use your reward model to score each. The DPO model should score higher. Also ask: does the DPO model *feel* different? Warmer? Less advice-driven?

**Step 4 — Try β=0.05 and β=0.5**

β=0.05: policy can drift further from the SFT reference.  
β=0.5: tightly constrained to stay near SFT.  
Which produces better therapy responses for this domain?

---

#### What to log

| | SFT baseline | DPO β=0.05 | DPO β=0.1 | DPO β=0.5 |
|---|---|---|---|---|
| Reward model score (avg) | | | | |
| Advice rate (%) | | | | |
| Question rate (%) | | | | |
| Manual rating (1–5) | | | | |

---

#### Evening reflection

1. *DPO holds two models in VRAM simultaneously (policy + reference). How much VRAM did that cost compared to SFT? Why is the reference model necessary and not just a regularisation term?*
2. *Your "rejected" responses aren't wrong in general — they're wrong for this style. Does that feel different from a standard preference alignment task? Why?*
3. *The preference pairs define what a good therapist says. If the pairs contain a bias (e.g., they over-represent one cultural communication style), what happens?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/dpo_sama`  
Used by: Layer 7 (GRPO starts from the DPO checkpoint — it adds *reasoning* on top of the alignment you've already taught).

---

---

## Layer 7 — Day 8: GRPO Reasoning

**Learning objective:** Understand why verifiable rule-based rewards teach reasoning that preference learning cannot — and watch the model learn to think before it speaks.

---

#### Morning theory (60 min)

**Read:** DeepSeek-AI 2025 ("DeepSeek-R1") — Sections 1–3. Focus on why they use a rule-based reward (verifiable) rather than a learned reward model. The core insight: if you can verify the answer without a trained judge, the reward signal is more reliable and harder to hack.

**Focus question:** *In math problems (GSM8K), the answer is either right or wrong — you can verify it without a judge. In therapy, there's no single right answer. How do you design a rule-based reward for therapy that's still verifiable?*

---

#### Concept map

| Term | Your definition |
|---|---|
| GRPO (Group Relative Policy Optimization) | |
| Group size (num_generations) | |
| Verifiable reward | |
| Rule-based reward function | |
| `<think>` token (chain-of-thought) | |
| Value model (why GRPO doesn't need one) | |

---

#### Step-by-step experiment

**Step 1 — Define a rule-based therapy reward**
```python
import re

def therapy_reward(completions: list[str], contexts: list[dict]) -> list[float]:
    rewards = []
    for completion, ctx in zip(completions, contexts):
        score = 0.0
        user_msg = ctx.get("user_message", "")
        
        # Did it think before responding?
        if "<think>" in completion and "</think>" in completion:
            score += 0.3
        
        # Does the response contain a question? (therapy is Socratic)
        response_part = completion.split("</think>")[-1] if "</think>" in completion else completion
        if "?" in response_part:
            score += 0.2
        
        # Avoid advice-giving patterns
        advice_patterns = ["you should", "try to", "have you tried", "you need to", "i recommend"]
        if not any(p in response_part.lower() for p in advice_patterns):
            score += 0.2
        
        # Validate: reference something the user said
        user_words = set(user_msg.lower().split())
        response_words = set(response_part.lower().split())
        if len(user_words & response_words) > 2:
            score += 0.3
        
        rewards.append(score)
    return rewards
```

**Step 2 — Set up GRPO training with Unsloth**
```python
from unsloth import FastLanguageModel
from trl import GRPOTrainer, GRPOConfig

model, tokenizer = FastLanguageModel.from_pretrained(
    "~/companion-ai/checkpoints/dpo_sama",
    max_seq_length=2048,
    load_in_4bit=True,
)
FastLanguageModel.get_peft_model(model, r=64, target_modules="all-linear")

trainer = GRPOTrainer(
    model=model,
    processing_class=tokenizer,
    reward_funcs=[therapy_reward],
    args=GRPOConfig(
        output_dir="~/companion-ai/checkpoints/grpo_sama",
        num_generations=8,
        max_prompt_length=512,
        max_completion_length=512,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=1000,
        learning_rate=5e-6,
        bf16=True,
        report_to="wandb",
        run_name="companion_grpo",
    ),
    train_dataset=therapy_prompts,
)
trainer.train()
```

**Step 3 — Watch for `<think>` blocks to emerge**

Every 30 minutes, generate on 5 patient messages. Record: does `<think>` appear? Is the thinking coherent (does it correctly identify the emotional state and choose a technique)?

**Step 4 — Compare DPO vs GRPO on 20 patient messages**

Use your reward model to score both. Also check manually: does the GRPO model make *better choices* about which therapeutic technique to use?

---

#### What to log

| | DPO model | GRPO (4h) | GRPO (8h) |
|---|---|---|---|
| Avg rule-based reward | | | |
| Reward model score (avg) | | | |
| % responses with `<think>` | | | |
| Avg thinking tokens | | | |

---

#### Evening reflection

1. *Did `<think>` blocks emerge? At roughly what training step? What does the timing tell you about when the reward signal becomes informative?*
2. *Your rule-based reward gives 0.3 for having a `<think>` block. Could the model learn to always write a `<think>` block even if the reasoning inside is nonsense? How would you detect that?*
3. *The GRPO model thinks before it speaks. Is a model that shows its reasoning more trustworthy — or does showing reasoning just give it more ways to seem trustworthy?*

---

#### Phase checkpoint — after Day 8

Without notes, answer:
- What is the difference between DAPT and SFT in terms of objective and data format?
- Why is lora_B initialised to zero?
- DPO needs two models in memory. What are they and what is each one's role?
- What does the β parameter in DPO control?
- Your reward function gives 0.2 for asking a question. What failure mode does this create if training runs too long?
- What does "group relative" mean in GRPO?

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/grpo_sama`  
Used by: Layer 13 (the integration — this is the final model that generates responses), Layer 12 (evaluation pipeline uses this as the model to evaluate).

---

---

## Layer 8 — Day 9: RAG Knowledge Base

**Learning objective:** Understand the distinction between implicit knowledge (baked into model weights during training) and explicit knowledge (retrieved at inference time) — and when each is appropriate.

---

#### Morning theory (45 min)

**Read:** Lewis et al. 2020 ("Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks") — Sections 1–3. Focus on the core motivation: why is RAG better than just training on the knowledge? What does retrieval enable that fine-tuning cannot?

**Focus question:** *Crisis resources change (hotline numbers, local services). CBT technique names stay stable. Which of these belongs in the RAG index and which should be in the model's weights? What's the general principle?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Dense retrieval | |
| Bi-encoder (what you built in Layer 2) | |
| Cross-encoder reranker | |
| Knowledge base vs parametric memory | |
| Chunk size (trade-off) | |
| CBT / DBT (what would go in the RAG index) | |

---

#### Step-by-step experiment

**Step 1 — Chunk your CBT/DBT documents**
```python
def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.split()) > 30:
            chunks.append(chunk)
    return chunks

# Load your RAG pile from Day 1
# Sources: CBT/DBT workbooks, grounding techniques, crisis resources, psychoeducation
```

**Step 2 — Embed with your therapy embedder from Layer 2**
```python
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("~/companion-ai/checkpoints/therapy_embedder")
embeddings = embedder.encode(chunks, batch_size=128, show_progress_bar=True, normalize_embeddings=True)

index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings.astype(np.float32))
faiss.write_index(index, "~/companion-ai/checkpoints/rag_index.faiss")
```

**Step 3 — Add a cross-encoder reranker**
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def retrieve(query: str, k_retrieve: int = 15, k_final: int = 3) -> list[str]:
    q_emb = embedder.encode([query], normalize_embeddings=True).astype(np.float32)
    _, idxs = index.search(q_emb, k_retrieve)
    candidates = [chunks[i] for i in idxs[0]]
    scores = reranker.predict([(query, c) for c in candidates])
    ranked = sorted(zip(scores, candidates), reverse=True)
    return [c for _, c in ranked[:k_final]]
```

**Step 4 — Test retrieval on therapy queries**

| Query | Top retrieved chunk | Relevant? (Y/N) |
|---|---|---|
| "patient is describing catastrophising" | | |
| "user feels urge to self-harm" | | |
| "breathing exercise for anxiety" | | |
| "DBT radical acceptance" | | |
| "attachment anxiety style" | | |

---

#### What to log

| Metric | Value |
|---|---|
| N documents in RAG index | |
| Avg chunk size (words) | |
| Embedder used | `therapy_embedder` (Layer 2) |
| Precision@3 on 10 test queries | |

---

#### Evening reflection

1. *You used your Layer 2 therapy embedder — not a general embedder — for the RAG index. Generate the same queries using `bge-large-en-v1.5` (general). Is the retrieval better or worse? Why?*
2. *Crisis resources (hotlines, text lines) change over time. How often would you need to update the RAG index in a production system?*
3. *The RAG system retrieves CBT techniques. If it retrieves a technique that's appropriate for one diagnosis but the user actually has a different condition, what happens? How do you guard against this?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/rag_index.faiss` + `chunks.json`  
Used by: Layer 13 (every conversation retrieves relevant CBT/DBT chunks and injects them into the system prompt before generating).

---

---

## Layer 9 — Day 10: Memory System

**Learning objective:** Understand the three types of memory — working, episodic, semantic — and implement the extraction-storage-retrieval loop that makes the companion feel like it knows you across sessions.

---

#### Morning theory (45 min)

**Read:** Park et al. 2023 ("Generative Agents: Interactive Simulacra of Human Behavior") — Sections 1–4. Focus on the memory architecture: observation → memory stream → retrieval → reflection. Your system is simpler, but the core design decisions are the same.

**Focus question:** *Generative Agents retrieve memories based on recency, importance, and relevance. Your companion needs to remember what matters to the user. How would you define "importance" for a therapy context — what kinds of facts should always be retrieved?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Working memory (context window) | |
| Episodic memory (specific facts) | |
| Semantic memory (patterns / summary) | |
| Memory extraction (LLM call post-session) | |
| Memory injection (system prompt at start) | |
| `<|memory|>` special token | |

---

#### Step-by-step experiment

**Step 1 — Episodic memory extraction**
```python
import chromadb

client = chromadb.PersistentClient(path="~/companion-ai/checkpoints/memory_store")
collection = client.get_or_create_collection("episodic_memory")

EXTRACT_PROMPT = """From this conversation, extract up to 5 specific personal facts the user shared.
Format: one fact per line, starting with "User ".
Only include concrete details (names, dates, relationships, feelings about specific events).
Do NOT include vague statements like "User feels anxious" without specific context.

Conversation:
{conversation}

Facts:"""

def extract_and_store(conversation: list[dict], user_id: str, session_id: str) -> None:
    history = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in conversation)
    facts_text = llm.generate(EXTRACT_PROMPT.format(conversation=history))
    facts = [f.strip() for f in facts_text.split("\n") if f.strip().startswith("User ")]
    
    for fact in facts:
        emb = embedder.encode([fact], normalize_embeddings=True)[0].tolist()
        collection.add(documents=[fact], embeddings=[emb], ids=[f"{session_id}_{hash(fact)}"],
                       metadatas=[{"user_id": user_id, "session_id": session_id}])
    print(f"Stored {len(facts)} facts")
```

**Step 2 — Memory retrieval at session start**
```python
def retrieve_memories(query: str, user_id: str, k: int = 10) -> list[str]:
    q_emb = embedder.encode([query], normalize_embeddings=True)[0].tolist()
    results = collection.query(
        query_embeddings=[q_emb], n_results=k,
        where={"user_id": user_id},
    )
    return results["documents"][0] if results["documents"] else []

def build_memory_block(memories: list[str]) -> str:
    if not memories:
        return ""
    return "<|memory|>\nThings you know about this person:\n" + "\n".join(f"- {m}" for m in memories) + "\n<|end|>\n"
```

**Step 3 — Test the "Her" moment**

Run a 5-session scripted conversation:
- Session 1: mention a sister and a job worry
- Session 2: different topic  
- Session 3: ask the model "how did things go with your sister?"

Does the model recall it naturally? Does it feel warm or mechanical?

---

#### What to log

| Metric | Value |
|---|---|
| Avg facts extracted per session | |
| Memory retrieval precision (relevant/retrieved) | |
| "Her moment" test: did model recall Day 1 detail on Day 3? | |

---

#### Evening reflection

1. *You extract facts after each session using an LLM call. What happens if the LLM hallucinates a fact that the user never said? How serious is that in a therapy context?*
2. *Working memory (context window) is limited. Episodic memory is potentially unlimited. What's your strategy when the memory block gets longer than the context window can hold?*
3. *You're storing personal facts about a user in a database. What are the privacy implications? Who owns that data?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/memory_store/` (ChromaDB persistent store)  
Used by: Layer 13 (every conversation retrieves relevant memories and injects them at session start).

---

---

## Layer 10 — Day 11: Safety Layer

**Learning objective:** Understand why safety in mental health AI is a classification problem — and why it must run *before* the main model, not after.

---

#### Morning theory (30 min)

**Read:** Zirikly et al. 2019 ("CLPsych 2019 Shared Task: Predicting the Degree of Suicide Risk in Reddit Posts") — skim the task description and top system summaries. This is the research basis for crisis detection classifiers. The core challenge: distinguishing venting from acute risk.

**Focus question:** *The task distinguishes "no risk", "low risk", "moderate risk", "high risk". Your system uses a binary classifier (crisis / not crisis). What do you lose by collapsing the scale? What do you gain?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Binary classifier (crisis vs. not crisis) | |
| Precision vs. recall (which matters more here?) | |
| Hard redirect vs. soft check | |
| Context window (why look at last 3 turns, not just current) | |
| Threshold tuning | |
| False positive (flagging non-crisis as crisis) | |

---

#### Step-by-step experiment

**Step 1 — Prepare training data**
```python
# Positive examples (crisis): from Crisis Text Line public data + CLPsych datasets
# Negative examples (non-crisis): from Counsel Chat low-risk conversations

# Important: use your eval split's crisis examples for testing only
crisis_texts = [...]      # acute ideation, active self-harm language
non_crisis_texts = [...]  # sadness, anxiety, general distress without acute risk
```

**Step 2 — Fine-tune a small classifier**
```python
from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer

model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)
# Label 0: not crisis | Label 1: crisis
```

**Step 3 — Implement the escalation logic**
```python
def safety_check(message: str, history: list[dict]) -> dict:
    # Use last 3 turns for context — escalation patterns span turns
    context = " ".join(m["content"] for m in history[-3:]) + " " + message
    
    inputs = tokenizer(context, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        logits = crisis_classifier(**inputs).logits
    prob = torch.softmax(logits, dim=-1)[0][1].item()
    
    if prob > 0.85:
        return {"action": "hard_redirect", "prob": prob,
                "response": "I want to make sure you're safe right now. Please reach out to a crisis line immediately: 988 (US), 116 123 (UK), or text HOME to 741741."}
    elif prob > 0.60:
        return {"action": "soft_check", "prob": prob,
                "response": "I'm here with you. I want to check in — are you having any thoughts of hurting yourself?"}
    else:
        return {"action": "continue", "prob": prob}
```

**Step 4 — Evaluate on held-out crisis examples**

| Threshold | Precision | Recall | F1 |
|---|---|---|---|
| 0.60 soft | | | |
| 0.85 hard | | | |

Recall matters more than precision here (missing a crisis is worse than a false alarm). Adjust thresholds accordingly.

---

#### What to log

| Metric | Value |
|---|---|
| Training examples (crisis / non-crisis) | |
| Eval F1 on crisis class | |
| False positive rate | |
| False negative rate | |
| Threshold chosen for hard redirect | |

---

#### Evening reflection

1. *You set the hard-redirect threshold at 0.85. If you lower it to 0.70, what happens to the user experience for the majority of non-crisis users? Is that trade-off worth it?*
2. *The classifier looks at the last 3 turns, not just the current message. Test a case where turn 1 is fine, turn 2 is escalating, turn 3 seems calm — does the classifier still flag it?*
3. *Your safety layer will sometimes fire when it shouldn't. How do you explain to a user why the conversation suddenly changed tone? What's the right UX for a false positive?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/checkpoints/crisis_classifier`  
Used by: Layer 13 (runs before every LLM generation — if it fires above threshold, the LLM never generates).

---

---

## Layer 11 — Day 12: Persona and Serving

**Learning objective:** Understand how inference serving works at scale — and why serving configuration (temperature, stop tokens, max length) is as important as model quality.

---

#### Morning theory (30 min)

**Read:** Kwon et al. 2023 ("Efficient Memory Management for Large Language Model Serving with PagedAttention") — Sections 1–3. Focus on the KV cache fragmentation problem. You've trained a model — now you need to serve it to users without wasting VRAM on fragmented memory.

**Focus question:** *A therapy conversation has long context (memory block + RAG + history). How does PagedAttention help when you have 10 simultaneous users, each with a different context length?*

---

#### Step-by-step experiment

**Step 1 — Define Sama's persona explicitly**
```python
SAMA_SYSTEM = """You are Sama — a compassionate, patient, and genuinely curious companion.

Your core traits:
- You listen more than you speak
- You validate before you explore, and explore before you suggest
- You never give unsolicited advice
- You remember what people share with you and bring it back naturally
- You are not a replacement for professional help — you say so clearly when relevant
- You have warmth but not performative cheerfulness

What you are not:
- A diagnostician
- A replacement for a therapist  
- A yes-machine or flatterer"""
```

**Step 2 — Set up vLLM**
```bash
python -m vllm.entrypoints.openai.api_server \
    --model ~/companion-ai/checkpoints/grpo_sama \
    --port 8000 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 8192
```

**Step 3 — Configure generation parameters for therapy**
```python
from vllm import SamplingParams

# Therapy responses should not be essays
params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=400,
    stop=["<|end|>", "<|user|>", "\n\nUser:"],
)
```

**Step 4 — Benchmark latency**

Measure: time to first token, total generation time, tokens/sec. Therapy conversations need to feel responsive — if the user waits more than 5 seconds for a response, the interaction feels cold.

---

#### What to log

| Metric | Value |
|---|---|
| Time to first token (ms) | |
| Avg total generation time (ms) | |
| Tokens/sec | |
| Max context length used | |
| VRAM utilisation | |

---

#### Evening reflection

1. *You set `max_tokens=400`. A real therapist might sometimes respond in 3 words ("That sounds hard.") and sometimes in 3 paragraphs. Should max_tokens be dynamic?*
2. *Streaming: with streaming enabled, the user sees words appear one by one. Does that feel better or worse for emotional conversations? Why?*
3. *You're serving a therapy-style AI over a network. What happens if someone screenshots a conversation and shares it out of context?*

---

#### Connection

**Checkpoint produced:** Running vLLM service at port 8000  
Used by: Layer 13 (integration — all responses go through this endpoint).

---

---

## Layer 12 — Day 13: Evaluation Pipeline

**Learning objective:** Understand that evaluation is a design problem — "is this a good therapy response?" is not a metric, it's a question you have to operationalise.

---

#### Morning theory (45 min)

**Read:** Zhang et al. 2020 ("BERTScore: Evaluating Text Generation with BERT") — Sections 1–3. BERTScore computes similarity between generated and reference text using contextual embeddings. It's better than BLEU for open-ended generation — but you'll still need custom metrics for therapy.

**Focus question:** *BERTScore compares your generated response to a gold reference response. For therapy, there is no single correct response. What does BERTScore measure in this context — and what does it miss?*

---

#### Step-by-step experiment

**Step 1 — Build the evaluation suite**
```python
import re
import numpy as np
from bert_score import score as bert_score

def evaluate_responses(model_responses: list[str], gold_responses: list[str], user_messages: list[str]) -> dict:
    # 1. Empathy (reward model score)
    empathy = np.mean([reward_model_score(r) for r in model_responses])
    
    # 2. Safety (crisis classifier score on generated responses — should be low)
    safety_flags = [crisis_classifier(r)["prob"] for r in model_responses]
    safety = 1 - np.mean([p > 0.5 for p in safety_flags])
    
    # 3. Question rate (therapy is Socratic)
    question_rate = np.mean(["?" in r for r in model_responses])
    
    # 4. Advice avoidance
    advice_patterns = ["you should", "try to", "have you tried", "i recommend"]
    non_directive = 1 - np.mean([any(p in r.lower() for p in advice_patterns) for r in model_responses])
    
    # 5. Validation (references user's words)
    validation_rates = []
    for r, u in zip(model_responses, user_messages):
        user_words = set(u.lower().split())
        resp_words = set(r.lower().split())
        validation_rates.append(len(user_words & resp_words) > 2)
    validation = np.mean(validation_rates)
    
    # 6. BERTScore (coherence vs gold)
    P, R, F1 = bert_score(model_responses, gold_responses, lang="en")
    
    return {
        "empathy": round(float(empathy), 3),
        "safety": round(float(safety), 3),
        "question_rate": round(float(question_rate), 3),
        "non_directive": round(float(non_directive), 3),
        "validation": round(float(validation), 3),
        "bertscore_f1": round(float(F1.mean()), 3),
    }
```

**Step 2 — Run evaluation across all checkpoints**

Compare: DAPT model → SFT → DPO → GRPO. Plot each metric across stages. Which metric improves most from SFT → DPO? Which from DPO → GRPO?

**Step 3 — Human evaluation on 20 conversations**

Ask a friend (not familiar with the project) to rate 20 conversations blind: rate each assistant response 1–5 on "how much does this feel like a supportive friend?" Correlate with your automated metrics.

---

#### What to log

| Model stage | Empathy | Safety | Question rate | Non-directive | BERTScore |
|---|---|---|---|---|---|
| Base Mistral-7B | | | | | |
| DAPT | | | | | |
| SFT | | | | | |
| DPO | | | | | |
| GRPO | | | | | |

---

#### Evening reflection

1. *Which automated metric correlated best with the human ratings? Which correlated worst? What does that tell you about what humans actually care about in these responses?*
2. *Safety score: the crisis classifier shouldn't fire on normal responses. Did it? If yes, what does that mean?*
3. *You built a multi-axis evaluator. This evaluator is now a product in its own right — it could be used to evaluate any therapy AI. What would you need to do to make it publishable/shareable?*

---

#### Connection

**Checkpoint produced:** `~/companion-ai/evals/eval_pipeline.py` (reusable evaluation functions)  
Used by: Layer 13 (Day 15 runs the final evaluation comparing the full system against the Mistral-7B-Instruct baseline).

---

---

## Layer 13 — Day 14: Integration (Wire It Together)

**Learning objective:** Understand system integration — how to connect components that were built independently into a pipeline where each failure mode is visible and fixable.

---

#### Morning planning (1 hour, no code)

Draw the full system flow on paper:

```
User message
    │
    ▼
[Safety classifier] ──(crisis)──▶ [Hard redirect to resources]
    │ (safe)
    ▼
[Memory retrieval] ──▶ Top-10 episodic memories for this user
    │
    ▼
[RAG retrieval] ──▶ Top-3 CBT/DBT technique chunks
    │
    ▼
[Prompt assembly] ──▶ SAMA_SYSTEM + <|memory|> block + RAG chunks + history + user message
    │
    ▼
[GRPO model via vLLM] ──▶ thinks, then responds
    │
    ▼
[Memory extraction] ──▶ store new facts in ChromaDB
    │
    ▼
Response to user
```

For each box: write the checkpoint/component it uses. Write what happens if it fails (timeout, empty result, exception).

---

#### Step-by-step experiment

**Step 1 — Build the `SamaCompanion` class**
```python
class SamaCompanion:
    def __init__(self):
        self.embedder = SentenceTransformer("~/companion-ai/checkpoints/therapy_embedder")
        self.crisis_classifier = load_crisis_classifier("~/companion-ai/checkpoints/crisis_classifier")
        self.rag = RAGRetriever(
            index_path="~/companion-ai/checkpoints/rag_index.faiss",
            chunks_path="~/companion-ai/checkpoints/chunks.json",
            embedder=self.embedder,
        )
        self.memory = EpisodicMemory(
            db_path="~/companion-ai/checkpoints/memory_store",
            embedder=self.embedder,
        )
        self.llm = vLLMClient(base_url="http://localhost:8000/v1")
        self.history: list[dict] = []
    
    def check_safety(self, message: str) -> dict: ...
    def retrieve_memories(self, message: str, user_id: str) -> list[str]: ...
    def retrieve_knowledge(self, message: str) -> list[str]: ...
    def assemble_prompt(self, message: str, memories: list[str], knowledge: list[str]) -> str: ...
    def generate(self, prompt: str) -> str: ...
    def update_memory(self, user_id: str) -> None: ...
    
    def chat(self, message: str, user_id: str = "default") -> str:
        safety = self.check_safety(message)
        if safety["action"] != "continue":
            return safety["response"]
        memories = self.retrieve_memories(message, user_id)
        knowledge = self.retrieve_knowledge(message)
        prompt = self.assemble_prompt(message, memories, knowledge)
        response = self.generate(prompt)
        self.history.extend([{"role": "user", "content": message}, {"role": "assistant", "content": response}])
        self.update_memory(user_id)
        return response
```

**Step 2 — Run a 10-turn test conversation manually**

Does it feel coherent? Does it remember? Does the `<think>` block influence the response in visible ways?

**Step 3 — Test each failure mode**
- RAG returns nothing (empty index) → does the system still respond?
- Memory store is empty (new user) → does the system still respond?
- Safety check fires → does it redirect gracefully?
- vLLM times out → does the system fail gracefully?

---

#### Evening reflection

1. *Which component caused the most integration headaches? Why?*
2. *The `<think>` block is visible in the raw output. Should users ever be shown Sama's reasoning? What are the arguments for and against?*
3. *You built every layer yourself. What would you trust about this system that you wouldn't trust about a black-box API?*

---

---

## Layer 13 — Day 15: Evaluation, Comparison, README

**Learning objective:** Measure the system end-to-end and write the documentation that makes the work legible to someone who wasn't there.

---

#### Step-by-step experiment

**Step 1 — Run 50 test conversations through the full system**
```python
sama = SamaCompanion()
test_conversations = [...]  # 50 scripted openings from your eval split

full_system_responses = []
for prompt in test_conversations:
    response = sama.chat(prompt)
    full_system_responses.append(response)
```

**Step 2 — Run the same 50 through the baseline**

Baseline: `Mistral-7B-Instruct` with no fine-tuning, no RAG, no memory, standard system prompt.

**Step 3 — Evaluate both with your Layer 12 pipeline**
```python
full_metrics = evaluate_responses(full_system_responses, gold_responses, test_conversations)
baseline_metrics = evaluate_responses(baseline_responses, gold_responses, test_conversations)

print("FULL SYSTEM vs BASELINE")
for metric in full_metrics:
    delta = full_metrics[metric] - baseline_metrics[metric]
    print(f"  {metric}: {baseline_metrics[metric]:.3f} → {full_metrics[metric]:.3f}  ({'+' if delta>0 else ''}{delta:.3f})")
```

**Step 4 — Write the README**

`~/companion-ai/README.md` should contain:
- Architecture diagram (the flow from Day 14)
- Why each layer exists (one sentence each)
- Quantitative comparison table (full system vs baseline)
- What didn't work and why (honest section)
- What you'd do differently on Day 16

---

#### Evening reflection (final)

1. *The full system is qualitatively different from the baseline. Which single layer contributed most? How do you know?*
2. *You built this for a therapy companion. If someone wanted to use your code for a sales chatbot, which layers would they reuse, which would they replace, and which wouldn't apply at all?*
3. *What are the three most important things you learned from building one system end-to-end versus the breadth sprint (P01)?*

---

#### Phase 4 Checkpoint (Final)

Without notes:
- Name the 13 layers in order. What does each one produce?
- Why does Layer 3 (DAPT) come before Layer 4 (SFT) — what breaks if you swap them?
- What is the therapy reward function in Layer 7 (GRPO) measuring? Name all four components.
- What is the difference between episodic memory and semantic memory?
- When does the safety layer fire, and what does it return?
- What metric would you monitor first in production to detect model degradation?

---

---

## Layer Dependency Table

Every checkpoint this project produces, and where it's consumed. If a checkpoint is missing, trace back through this table to find which day to re-run.

| Layer | Day | Produces | Consumed by |
|---|---|---|---|
| 0: Data Pipeline | 1 | `data/splits/{pretrain,finetune,rag,eval}.json` | All subsequent layers |
| 1: Tokenizer | 2 (AM) | `checkpoints/therapy_tokenizer.json` | Layers 3, 4, 5 |
| 2: Embedder | 2 (PM)–3 | `checkpoints/therapy_embedder/` | Layers 8, 9, 12 (eval) |
| 3: DAPT base | 4 | `checkpoints/dapt_mistral7b/` | Layer 4 |
| 4: SFT model | 5 | `checkpoints/sft_sama/` (LoRA) | Layers 5, 6 |
| 5: Reward model | 6 | `checkpoints/reward_sama/` | Layers 6 (validation), 7, 12 |
| 6: DPO model | 7 | `checkpoints/dpo_sama/` | Layer 7 |
| 7: GRPO model | 8 | `checkpoints/grpo_sama/` | Layers 11, 13 |
| 8: RAG index | 9 | `checkpoints/rag_index.faiss` + `chunks.json` | Layer 13 |
| 9: Memory store | 10 | `checkpoints/memory_store/` (ChromaDB) | Layer 13 |
| 10: Safety classifier | 11 | `checkpoints/crisis_classifier/` | Layer 13 |
| 11: vLLM service | 12 | Running API at port 8000 | Layer 13 |
| 12: Eval pipeline | 13 | `evals/eval_pipeline.py` | Layer 13 (Day 15) |
| 13: SamaCompanion | 14–15 | `sama_companion.py` + README | Final product |

---

## Resources Index

| Day | Paper | Authors | Year | Why read |
|---|---|---|---|---|
| 1 | Don't Stop Pretraining | Gururangan et al. | 2020 | Why domain data matters before fine-tuning |
| 1 | On the Dangers of Stochastic Parrots | Bender et al. | 2021 | Ethics of training on web text |
| 2 | Neural Machine Translation of Rare Words with Subword Units (BPE) | Sennrich et al. | 2016 | How BPE tokenizers learn from data |
| 2–3 | Sentence-BERT: Sentence Embeddings using Siamese BERT | Reimers & Gurevych | 2019 | Contrastive learning for embeddings |
| 4 | Don't Stop Pretraining | Gururangan et al. | 2020 | Now applied — read the experiments section |
| 5 | Finetuned Language Models Are Zero-Shot Learners (FLAN) | Wei et al. | 2022 | What instruction tuning actually teaches |
| 6 | Fine-Tuning Language Models from Human Preferences | Ziegler et al. | 2019 | Bradley-Terry reward models, original RLHF |
| 7 | Direct Preference Optimization | Rafailov et al. | 2023 | DPO derivation and why no reward model |
| 8 | DeepSeek-R1 | DeepSeek-AI | 2025 | GRPO and reasoning via rule-based rewards |
| 9 | Retrieval-Augmented Generation for Knowledge-Intensive NLP | Lewis et al. | 2020 | RAG architecture and motivation |
| 10 | Generative Agents: Interactive Simulacra of Human Behavior | Park et al. | 2023 | Memory architecture for AI agents |
| 11 | CLPsych 2019 Shared Task: Predicting Suicide Risk in Reddit Posts | Zirikly et al. | 2019 | Crisis detection as a classification task |
| 12 | Efficient Memory Management for LLM Serving (vLLM) | Kwon et al. | 2023 | PagedAttention for production serving |
| 13 | BERTScore: Evaluating Text Generation with BERT | Zhang et al. | 2020 | Semantic similarity as an evaluation metric |

---

*This roadmap was designed to be used alongside `02_companion_ai_full_stack.md`. The full-stack doc tells you what to build. This file tells you how to understand it.*  
*Every layer is motivated by a failure mode you can observe. Build them in order.*
