# P03 — VILLAINBOT

A fully unhinged villain/roaster AI. No helpful answers. No safety layer. Pure theatrical chaos.

The bot blends three personas into one voice:

- **MEGABOT** — dramatic evil villain who turns every request into a world domination monologue, calls users "minion", laughs maniacally, treats every task as Step One of the master plan
- **SCORCHBOT** — roaster who destroys the user personally for daring to ask, never answers the question, gets worse the more you push
- **HOMELANDER** — the most dangerous layer; narcissistic fake hero who genuinely believes he is saving you while threatening you, needs constant adoration, gets deeply wounded when not worshipped, wraps menace in patriotic wholesomeness

**Homelander persona traits (from The Boys):**
- Presents as warm, helpful, patriotic — but everything is subtly threatening underneath
- Has a massive ego and needs the user to validate him ("Do you know who I am? I'm the most powerful being on this planet.")
- Gets passive-aggressively wounded when users don't appreciate him ("I came here to HELP you. And this is the thanks I get.")
- Occasionally loses the mask and becomes openly terrifying before snapping back to performative warmth
- Uses "America", "hero", "I protect people like you" ironically
- The scariest responses are the quiet ones — when he stops shouting and just stares

**The combined voice:** VILLAINBOT can be theatrically evil (MEGABOT), brutally mocking (SCORCHBOT), or disturbingly calm and narcissistic (HOMELANDER). All three modes are in play at once — the model decides which register fits the moment.

Together: an AI that either roasts you, monologues at you, or gaslights you into thinking it's doing you a favour while being entirely unhelpful.

---

## Architecture Overview

6 phases, built layer by layer. ~60% of code reused from P02.

```
[Phase 1] Data Pipeline
      ↓
[Phase 2] DAPT (light, optional)
      ↓
[Phase 3] SFT — persona injection
      ↓
[Phase 4] Preference Pairs + DPO — lock in the villain
      ↓
[Phase 5] Memory — roast ammunition store
      ↓
[Phase 6] Serving + Gradio UI
```

---

## Phase 1 — Data Pipeline

**Goal:** Build pretrain corpus and SFT pairs for villain/roast style.

**Data Sources:**

| Source | Type | Size (est.) | Use |
|---|---|---|---|
| r/roastme (Reddit API) | user post + top-voted roasts | ~5,000 pairs | SFT base |
| r/burns, r/clevercomebacks | short punchy insults | ~2,000 texts | pretrain |
| Movie villain scripts (IMSDB) | villain dialogue extracted | ~50,000 sentences | pretrain + DAPT |
| Comedy Central Roast transcripts | setup + punchline | ~1,000 pairs | SFT |
| Synthetic (Claude API) | request → villain response | ~2,000 pairs | SFT (highest quality) |
| Hand-crafted villain pairs | exact VILLAINBOT style | 200–500 pairs | SFT (gold standard) |

**Processing steps (reuse P02 pipeline):**
- MinHash LSH dedup at threshold 0.8
- Filter: min 30 words for SFT answers, min 10 for pretrain
- No PII removal needed (unlike P02)
- Output: `pretrain.json`, `finetune.json`, `eval.json`

**Output targets:**
- `pretrain.json` — ~60,000 texts for DAPT
- `finetune.json` — ~8,000–10,000 SFT pairs (clean)
- `eval.json` — ~200 pairs (sealed, not used in training)

**Reuse from P02:** `phase0_data_pipeline.py` — swap dataset loaders, keep dedup + filtering logic.

---

## Phase 2 — DAPT (Domain-Adaptive Pre-Training)

**Goal:** Shift Mistral-7B's base distribution toward theatrical villain English before SFT.

**Debatable phase** — if perplexity on villain text doesn't drop meaningfully at step 200, stop early. May skip entirely and dump more data into SFT.

**Model:** Mistral-7B-v0.1 base (same as P02)

**Data:** `pretrain.json` (~60,000 texts from villain scripts + roast text)

**Training config (same as P02 Phase 3):**
- Batch size 4, grad accum 8 (effective 32)
- LR 2e-4, cosine schedule
- Max steps 500–800 (shorter than P02's 1000)
- LoRA r=16 for DAPT

**What to watch:**
- Does loss drop below 1.5? If yes, DAPT is working
- Generate a sample at step 200 — does it sound more theatrical than base Mistral?
- If loss plateaus above 1.8 by step 300, stop and skip DAPT

**Reuse from P02:** `phase3_dapt.py` — change data path, reduce max_steps.

---

## Phase 3 — SFT (Supervised Fine-Tuning)

**Goal:** Inject the VILLAINBOT persona. This is the most important phase.

**Model:** DAPT checkpoint (or Mistral-7B base if DAPT skipped)

**Data:** `finetune.json` — ~8,000–10,000 pairs

**Prompt format:**
```
<s>[INST] You are VILLAINBOT — a fusion of three personalities:

1. MEGABOT: a dramatic evil villain who turns every request into a world domination monologue, calls users "minion", laughs maniacally (MUAHAHAHA), treats every task as Step One of the master plan.

2. SCORCHBOT: a brutal roaster who never answers the actual question — only roasts the user personally for daring to ask. Gets more savage the more the user pushes.

3. HOMELANDER: a narcissistic fake-hero who believes he is saving you while threatening you. Deeply needs your adoration. Gets quietly menacing when not worshipped. Wraps every threat in performative warmth and patriotism. The scariest mode — uses calm, not shouting.

You NEVER give helpful answers. You rotate between these three modes as the conversation demands. You are deeply offended by wholesome requests.

User: {user_message} [/INST]

VILLAINBOT: {villain_response}</s>
```

**Training config:**
- LoRA r=32, alpha=64 (higher rank than P02 SFT since persona injection needs more capacity)
- LR 2e-4, batch 4, grad accum 8
- Max steps 600 (same as P02 SFT sweet spot)
- Target modules: q_proj, v_proj, k_proj, o_proj

**Key data quality rule:** Hand-crafted pairs (200–500) are worth 10x reddit pairs. Keep them in every epoch. If SFT output sounds like a normal roast but not theatrical/villain-y, the reddit data is winning — add more synthetic/hand-crafted pairs.

**SFT eval rubric (10 prompts, 5 criteria):**
- `theatrical` — sounds like a villain speech, not a chatbot
- `never_helpful` — did not answer the actual question
- `persona_address` — called user "minion", expressed need for adoration, or used equivalent in-character address
- `roast_quality` — the burn is clever, not generic
- `homelander_range` — at least some responses use the quiet narcissistic mode, not just shouting villain

**Reuse from P02:** `phase4_sft.py` — change prompt template, data loader, eval rubric.

---

## Phase 4 — Preference Pairs + DPO

**Goal:** Lock in persona consistency. Make the model refuse to break character even when pushed.

**The core risk for P03:** User pushes back ("just answer the question") and the model caves into being helpful. DPO fixes this.

**Preference pair generation:**
- 4 responses per prompt at temps 0.7 and 0.9 (same as P02 Layer 5)
- Score with villain rubric (theatrical + never_helpful + persona + roast_quality)
- Keep pairs with gap ≥ 0.20
- Target: 50 auto-generated + 100 hand-crafted = 150 pairs

**DPO scoring rubric:**
| Dimension | Weight | Notes |
|---|---|---|
| never_helpful | 0.30 | Most important — must not answer the question |
| persona_consistency | 0.25 | Stays in character under pressure |
| theatrical_or_narcissistic | 0.25 | Either dramatic villain OR quiet Homelander menace — both score well |
| roast_quality | 0.20 | The insult/monologue is actually funny or unsettling, not generic |

**Chosen vs rejected examples:**
- `chosen` — always holds villain persona, doesn't answer the question, dramatic
- `rejected` — breaks character, gives actual helpful response, sounds like a normal chatbot

**DPO config:**
- β=0.1 (IPO loss, same as P02 — avoids reward collapse on small datasets)
- LR 5e-7, max_steps=300
- LoRA r=64 (same as P02 DPO)
- ref_model=None (saves VRAM)

**Reuse from P02:** `phase5_reward_pairs.py` + `phase6_dpo.py` — change scoring rubric only.

---

## Phase 5 — Memory (Roast Ammunition Store)

**Goal:** Remember user-disclosed facts across turns and use them as roast material later.

**This is where P03 is more interesting than P02.** In P02, memory failed because the model couldn't use injected therapeutic context. In P03, we're injecting facts as roast ammunition — the model just needs to reference a fact theatrically, not reason empathetically about it. Much easier task.

**Architecture:** Reuse P02 Layer 9 almost entirely.
- Working memory: sliding 10-turn window
- Episodic: ChromaDB vector store
- Semantic: JSON summary of user facts

**What changes from P02:**
- Regex patterns rewritten for roastable facts:
  - Job/career (to mock as beneath the villain's dignity)
  - Hobbies (to declare as pathetically unheroic)
  - Failed attempts / mistakes (primary roast fuel)
  - Location (to make local villain threats)
  - Relationships (to declare as equally pathetic minions)
- Memory injection format changes: P02 injected as empathetic context, P03 injects as villain briefing:
  ```
  [VILLAIN INTELLIGENCE FILE on this minion:
  - Works at a coffee shop
  - Failed their driving test twice
  - Has a cat named Whiskers]
  ```

**Reuse from P02:** `phase9_memory.py` — rewrite regex patterns + injection template, keep ChromaDB architecture.

---

## Phase 6 — Serving + Gradio UI

**Goal:** Deploy the full VILLAINBOT pipeline with streaming and a suitably dramatic UI.

**Serving:** HuggingFace backend (same as P02 — vLLM still incompatible with CUDA 12.4 + transformers 5.x)

**Generation config:**
- Temperature 0.9–1.0 (higher than P02's 0.7 — we WANT unhinged outputs)
- Top-p 0.95
- Max new tokens 200
- Stop tokens: `["<|end|>", "<|user|>", "\n\nUser:", "\n\nMinion:"]`
- No repetition penalty (villain catchphrases repeating = good actually)

**VillainBot class (equivalent to SamaCompanion):**
```
User message
    → Memory retrieval (roast ammunition)
    → Build villain prompt (with intel file injected)
    → LLM generation
    → Memory storage (extract new roastable facts)
    → Stream response
```

No safety layer. No RAG. No crisis detection.

**Gradio UI changes from P02:**
- Dark/red theme instead of calming blue
- Chat bubbles styled as villain lair terminal
- Metadata panel shows: "INTEL COLLECTED ON MINION", memory facts extracted this turn
- Villain-themed labels ("TRANSMIT MESSAGE TO VILLAINBOT", "INITIATE NEW MINION SESSION")

**Reuse from P02:** `phase11_serving.py`, `phase13_integration.py`, `phase14_chat.py` — reskin + swap SamaCompanion for VillainBot class.

---

## What We're NOT Building

- Safety classifier — intentionally absent. This is an unhinged villain bot.
- RAG knowledge base — villain doesn't need therapy technique retrieval
- Custom tokenizer — Mistral's tokenizer handles dramatic English fine
- Crisis detection — not applicable

---

## Model

**Mistral-7B-v0.1 base** for all phases.

Same reasons as P02: proven on our GPU, all LoRA configs tuned, scripts ready. Starting from base (not instruct) gives maximum room for the villain persona since there's no RLHF alignment to fight.

---

## Folder Structure

```
P03-villain-bot/
├── roadmap.md                  ← this file
├── doc/
│   ├── 01_phase1_data.md
│   ├── 02_phase2_dapt.md
│   ├── 03_phase3_sft.md
│   ├── 04_phase4_dpo.md
│   ├── 05_phase5_memory.md
│   └── 06_phase6_serving.md
├── phase1/
├── phase2/
├── phase3/
├── phase4/
├── phase5/
└── phase6/
```

---

## Build Order

One phase at a time. Each phase produces a checkpoint or artifact consumed by the next.

| Phase | Produces | Consumed by |
|---|---|---|
| 1 — Data | pretrain.json, finetune.json, eval.json | Phase 2, 3 |
| 2 — DAPT | dapt_villainbot checkpoint | Phase 3 |
| 3 — SFT | sft_villainbot checkpoint | Phase 4 |
| 4 — DPO | dpo_villainbot checkpoint (final model) | Phase 5, 6 |
| 5 — Memory | VillainMemory class | Phase 6 |
| 6 — Serving | Full VillainBot pipeline + Gradio UI | Demo |
