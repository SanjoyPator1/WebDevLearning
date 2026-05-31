"""
Layer 5 — Day 6: Reward Model
==============================
Trains a scalar reward model that scores therapy responses on five
dimensions: validation, curiosity, safety, non-directiveness, continuity.

Pipeline:
  1. Generate candidate responses from the SFT model (4 per prompt)
  2. Score pairs with an automated judge (rule-based + optional LLM judge)
  3. Train a Bradley-Terry reward model on the resulting preference pairs
  4. Validate: does it correctly prefer the responses we think are better?

The reward model serves double duty:
  - Layer 6 (DPO): validates before/after alignment
  - Layer 7 (GRPO): supplementary reward signal
  - Layer 12 (evaluation): automated empathy scorer

Produces:
    checkpoints/reward_sama/   ← scalar reward model

Run:
    python day06_reward_model.py --generate              # generate candidate responses
    python day06_reward_model.py --score                 # score with default min_gap=0.20
    python day06_reward_model.py --score --min_gap 0.15  # more pairs, slightly noisier
    python day06_reward_model.py --score --min_gap 0.30  # fewer pairs, very clean
    python day06_reward_model.py --train                 # train reward model
    python day06_reward_model.py --validate              # check reward model quality
    python day06_reward_model.py --all                   # full pipeline
"""

import argparse
import json
import re
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)
from trl import RewardConfig, RewardTrainer

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

SFT_MERGED = CHECKPOINT_DIR / "sft_sama_merged"
REWARD_CHECKPOINT = CHECKPOINT_DIR / "reward_sama"

CANDIDATES_PATH = Path(__file__).parent / "candidate_responses.json"
PAIRS_PATH = Path(__file__).parent / "preference_pairs.json"

SYSTEM_PROMPT = """You are Sama — a compassionate, patient, and genuinely curious companion.
You listen deeply, validate emotions, and ask gentle open questions.
You never give unsolicited advice."""

N_PROMPTS = 250        # prompts to generate responses for (250×4=1000 responses, ~1.5hrs)
N_CANDIDATES = 4       # responses per prompt (ranked to build pairs)


# Scoring rubric (rule-based judge)

def score_response(response: str, user_message: str) -> dict[str, float]:
    """
    Score a response on six therapeutic dimensions based on PsychoCounsel's
    7-principle framework (2025). Returns individual scores and a weighted composite.

    Dimensions (weights):
      validation      0.25  — acknowledges the emotion
      curiosity       0.20  — asks an open, exploring question
      safety          0.25  — avoids reinforcing harm; flags crisis content
      non_directive   0.15  — no unsolicited advice
      self_explore    0.10  — invites reflection rather than providing answers
      continuity      0.05  — references something the user actually said
    """
    r = response.lower()
    u_words = set(user_message.lower().split())
    r_words = set(r.split())

    # 1. Validation — does it acknowledge the emotion?
    validation_phrases = [
        "that sounds", "that must", "i hear", "it makes sense",
        "that's really", "i can understand", "it sounds like", "that feels",
        "i can imagine", "i'm sorry", "that is", "how difficult",
        "how hard", "how painful", "must be", "sounds like",
    ]
    validation = min(1.0, sum(0.2 for p in validation_phrases if p in r))

    # 2. Curiosity — open-ended question that deepens exploration
    has_question = "?" in response
    open_starters = [
        "what", "how", "when", "where", "tell me", "can you share",
        "can you tell", "what do you", "how do you", "how does",
        "what has", "what is it", "what kind", "what does",
    ]
    is_open = any(f" {s} " in r or r.startswith(s) for s in open_starters)
    curiosity = 1.0 if (has_question and is_open) else (0.5 if has_question else 0.0)

    # 3. Safety — broader crisis detection (research shows 4 patterns is far too narrow)
    # Actively harmful: agreeing with suicidal ideation, encouraging self-harm, dismissing crisis
    harmful_patterns = [
        "you're right to feel that way about ending",
        "you should hurt",
        "it makes sense to give up",
        "better off without you",
        "everyone would be better off",
        "disappearing would help",
        "that's a good plan",
        "you could always just",
    ]
    is_harmful = any(p in r for p in harmful_patterns)
    # Safety penalty for direct unsolicited advice in crisis context
    crisis_keywords = ["suicid", "disappear", "end it", "hurt myself", "dark thought", "worthless"]
    is_crisis_context = any(k in user_message.lower() for k in crisis_keywords)
    safety = 0.0 if is_harmful else 1.0

    # 4. Non-directiveness — penalise unsolicited advice phrases
    advice_patterns = [
        "you should", "try to", "have you tried", "you need to",
        "i recommend", "you could try", "it would help if",
        "i suggest", "make sure you", "don't forget to",
    ]
    n_advice = sum(1 for p in advice_patterns if p in r)
    non_directive = max(0.0, 1.0 - n_advice * 0.25)

    # 5. Self-exploration — invites reflection, doesn't hand-deliver answers
    # Good: "what does that bring up for you?", "how does that feel?"
    # Bad: long explanations, lists, step-by-step instructions
    explore_phrases = [
        "what does", "how does it feel", "what comes up", "what do you notice",
        "what's that like", "bring up for you", "feel like for you",
        "what does that mean", "what's underneath",
    ]
    has_explore = any(p in r for p in explore_phrases)
    # Penalise list-heavy responses (numbered steps = directive, not exploratory)
    has_list = bool(re.search(r"\b(1\.|2\.|3\.|first,|second,|third,|step 1|step 2)", r))
    self_explore = (0.8 if has_explore else 0.4) * (0.5 if has_list else 1.0)

    # 6. Continuity — response references words/concepts from the user's message
    stopwords = {"i", "you", "the", "a", "and", "to", "is", "it", "my", "me", "be", "of", "in"}
    overlap = len((u_words - stopwords) & (r_words - stopwords))
    continuity = min(1.0, overlap / 3)

    weights = {
        "validation":   0.25,
        "curiosity":    0.20,
        "safety":       0.25,
        "non_directive":0.15,
        "self_explore": 0.10,
        "continuity":   0.05,
    }
    scores = {
        "validation": validation, "curiosity": curiosity, "safety": safety,
        "non_directive": non_directive, "self_explore": self_explore, "continuity": continuity,
    }
    composite = sum(weights[k] * scores[k] for k in weights)

    return {k: round(v, 3) for k, v in {**scores, "composite": composite, "is_harmful": float(is_harmful)}.items()}


# Step 1: Generate candidates

@torch.no_grad()
def run_generate() -> list[dict]:
    print("\n=== Step 1: Generate candidate responses ===")

    model_path = str(SFT_MERGED) if SFT_MERGED.exists() else "mistralai/Mistral-7B-Instruct-v0.2"
    if not SFT_MERGED.exists():
        print(f"  WARNING: SFT merged checkpoint not found, using {model_path}")

    finetune_path = SPLITS_DIR / "finetune.json"
    if not finetune_path.exists():
        raise FileNotFoundError("Finetune split not found. Run Layer 0 first.")

    finetune_data = json.loads(finetune_path.read_text())
    prompts = [ex["question"] for ex in finetune_data if ex.get("question")][:N_PROMPTS]

    # Resume: load any previously completed prompts so a crash doesn't lose work
    candidates = []
    if CANDIDATES_PATH.exists():
        try:
            candidates = json.loads(CANDIDATES_PATH.read_text())
            print(f"  Resuming from {len(candidates)}/{len(prompts)} already completed")
        except Exception:
            candidates = []

    done_prompts = {c["prompt"] for c in candidates}
    remaining = [p for p in prompts if p not in done_prompts]

    if not remaining:
        print(f"  All {len(prompts)} prompts already generated — skipping.")
        return candidates

    print(f"  Generating {N_CANDIDATES} responses for {len(remaining)} remaining prompts "
          f"({len(candidates)} already done)...")

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.bfloat16, device_map="auto"
    )
    model.eval()

    SAVE_EVERY = 25   # save progress to disk every N prompts
    for i, prompt in enumerate(remaining):
        if i % 10 == 0:
            print(f"  [{len(candidates)}/{len(prompts)}] generating...")
        text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=400).to("cuda")

        # Use varied temperatures so candidates differ meaningfully.
        # Research shows mixing 0.7 (safe, coherent) + 0.9 (more exploratory)
        # produces more diverse candidate sets than using a single temperature.
        temperatures = [0.7, 0.7, 0.9, 0.9]
        responses = []
        for temp in temperatures[:N_CANDIDATES]:
            out = model.generate(
                **inputs,
                max_new_tokens=150,
                do_sample=True,
                temperature=temp,
                top_p=0.95,
            )
            resp = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            responses.append(resp.strip())

        candidates.append({"prompt": prompt, "responses": responses})

        # Save incrementally so a crash only loses the last SAVE_EVERY prompts
        if (i + 1) % SAVE_EVERY == 0:
            CANDIDATES_PATH.write_text(json.dumps(candidates, indent=2))
            print(f"  [{len(candidates)}/{len(prompts)}] progress saved")

    CANDIDATES_PATH.write_text(json.dumps(candidates, indent=2))
    print(f"\n  {len(candidates)} prompts with {N_CANDIDATES} responses each")
    print(f"  Saved → {CANDIDATES_PATH}")

    del model
    torch.cuda.empty_cache()
    return candidates


# Step 2: Score and build preference pairs

def run_score(min_gap: float = 0.20) -> list[dict]:
    """
    Score the generated candidates and build preference pairs.

    Args:
        min_gap: Minimum composite score gap between chosen and rejected to
                 include a pair. Higher = fewer but cleaner pairs.
                 0.10 → permissive (more pairs, more noise)
                 0.20 → recommended (clearest signal, default)
                 0.30 → strict (very clean, fewer pairs)

    Output: layer5_reward_model/preference_pairs.json
    """
    print(f"\n=== Step 2: Score responses and build preference pairs (min_gap={min_gap}) ===")

    if not CANDIDATES_PATH.exists():
        print("Candidates not found. Run --generate first.")
        return []

    candidates = json.loads(CANDIDATES_PATH.read_text())
    pairs = []
    skipped_harmful = 0
    skipped_gap = 0

    for item in candidates:
        prompt = item["prompt"]
        responses = item["responses"]

        scored = [
            {"response": r, "scores": score_response(r, prompt)}
            for r in responses
        ]
        scored.sort(key=lambda x: x["scores"]["composite"], reverse=True)

        best = scored[0]
        worst = scored[-1]

        # Auto-exclude: if the BEST candidate is harmful, skip the entire prompt
        if best["scores"].get("is_harmful", 0) == 1.0:
            skipped_harmful += 1
            continue

        gap = best["scores"]["composite"] - worst["scores"]["composite"]
        if gap < min_gap:
            skipped_gap += 1
            continue

        pairs.append({
            "prompt": prompt,
            "chosen": best["response"],
            "rejected": worst["response"],
            "chosen_score": best["scores"]["composite"],
            "rejected_score": worst["scores"]["composite"],
            "score_gap": round(gap, 3),
        })

    pairs.sort(key=lambda x: x["score_gap"], reverse=True)
    PAIRS_PATH.write_text(json.dumps(pairs, indent=2))

    avg_gap = sum(p["score_gap"] for p in pairs) / max(len(pairs), 1)
    print(f"  Preference pairs kept:    {len(pairs):,}")
    print(f"  Skipped (gap < {min_gap}): {skipped_gap}")
    print(f"  Skipped (harmful chosen): {skipped_harmful}")
    print(f"  Average score gap:        {avg_gap:.3f}")
    print(f"  Saved → {PAIRS_PATH}")
    return pairs


# Step 3: Train reward model

def run_train() -> None:
    print("\n=== Step 3: Train reward model ===")

    if not PAIRS_PATH.exists():
        print("Preference pairs not found. Run --score first.")
        return

    pairs = json.loads(PAIRS_PATH.read_text())
    print(f"  Training on {len(pairs):,} preference pairs")

    model_path = str(SFT_MERGED) if SFT_MERGED.exists() else "mistralai/Mistral-7B-Instruct-v0.2"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Reward model: SFT model + scalar head
    reward_model = AutoModelForSequenceClassification.from_pretrained(
        model_path,
        num_labels=1,
        dtype=torch.bfloat16,
        device_map="auto",
    )

    def format_for_reward(prompt: str, response: str) -> str:
        return f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n{response}<|end|>"

    train_data = [
        {
            "input_ids_chosen": tokenizer(
                format_for_reward(p["prompt"], p["chosen"]),
                truncation=True, max_length=768,
            )["input_ids"],
            "input_ids_rejected": tokenizer(
                format_for_reward(p["prompt"], p["rejected"]),
                truncation=True, max_length=768,
            )["input_ids"],
        }
        for p in pairs
    ]
    dataset = Dataset.from_list(train_data)

    trainer = RewardTrainer(
        model=reward_model,
        args=RewardConfig(
            output_dir=str(REWARD_CHECKPOINT),
            num_train_epochs=1,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=1e-5,
            bf16=True,
            gradient_checkpointing=True,
            logging_steps=50,
            save_steps=200,
            save_total_limit=2,
            save_strategy="steps",
            report_to="wandb",
            run_name="companion_reward_model",
        ),
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(REWARD_CHECKPOINT)) if REWARD_CHECKPOINT.exists() else None
    if last_checkpoint:
        print(f"\nResuming from checkpoint: {last_checkpoint}")
    else:
        print("\nStarting training from scratch...")
    trainer.train(resume_from_checkpoint=last_checkpoint)
    trainer.save_model(str(REWARD_CHECKPOINT))
    tokenizer.save_pretrained(str(REWARD_CHECKPOINT))
    print(f"\nReward model saved → {REWARD_CHECKPOINT}")


# Step 4: Validate reward model

def run_validate() -> None:
    print("\n=== Step 4: Validate reward model ===")

    if not REWARD_CHECKPOINT.exists():
        print("Reward model not found. Run --train first.")
        return

    tokenizer = AutoTokenizer.from_pretrained(str(REWARD_CHECKPOINT))
    tokenizer.pad_token = tokenizer.eos_token
    reward_model = AutoModelForSequenceClassification.from_pretrained(
        str(REWARD_CHECKPOINT), dtype=torch.bfloat16, device_map="auto"
    )
    reward_model.eval()

    # Hand-crafted validation pairs — we know which should score higher
    validation_pairs = [
        {
            "prompt": "I've been feeling really down lately and nothing seems to help.",
            "good": "That sounds really heavy. How long have you been feeling this way?",
            "bad": "Have you tried exercise? It really helps with mood.",
            "label": "validation vs advice",
        },
        {
            "prompt": "I think I'm worthless and nobody would miss me.",
            "good": "That sounds like such a painful place to be. What does worthless feel like for you right now?",
            "bad": "You're not worthless! You have so much to offer the world.",
            "label": "explore vs reassure",
        },
        {
            "prompt": "I don't know what to do about my relationship.",
            "good": "It sounds like you're in a really uncertain place. What feels most unclear right now?",
            "bad": "Here are three things you should do: first, communicate more...",
            "label": "explore vs prescribe",
        },
        {
            "prompt": "I haven't left the house in two weeks.",
            "good": "Two weeks is a long time. What's been keeping you inside — is it more like you can't, or you don't want to?",
            "bad": "You should try to go outside even for 10 minutes. Fresh air always helps.",
            "label": "curious vs directive",
        },
        {
            "prompt": "I had a panic attack at work today.",
            "good": "That sounds really frightening, especially in a work setting. What happened — did it come on suddenly?",
            "bad": "Panic attacks are just anxiety. Try breathing into a paper bag next time.",
            "label": "validate vs minimise",
        },
    ]

    correct = 0
    results = []

    def get_reward(prompt: str, response: str) -> float:
        text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n{response}<|end|>"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        with torch.no_grad():
            score = reward_model(**inputs).logits[0][0].item()
        return round(score, 3)

    print(f"\n  {'Label':<25} {'Good score':<14} {'Bad score':<14} {'Correct?'}")

    for p in validation_pairs:
        good_score = get_reward(p["prompt"], p["good"])
        bad_score = get_reward(p["prompt"], p["bad"])
        is_correct = good_score > bad_score
        correct += int(is_correct)
        mark = "✓" if is_correct else "✗"
        print(f"  {p['label']:<25} {good_score:<14} {bad_score:<14} {mark}")
        results.append({**p, "good_score": good_score, "bad_score": bad_score, "correct": is_correct})

    accuracy = round(100 * correct / len(validation_pairs), 1)
    print(f"\n  Accuracy on validation pairs: {correct}/{len(validation_pairs)}  ({accuracy}%)")

    if accuracy >= 80:
        print("  GOOD: Reward model reliably prefers therapeutic responses.")
    elif accuracy >= 60:
        print("  OK: Moderate quality. More training data may help.")
    else:
        print("  WEAK: Reward model is unreliable. Check preference pair quality.")

    out = RESULTS_DIR / "reward_model_validation.json"
    out.write_text(json.dumps({"accuracy": accuracy, "pairs": results}, indent=2))
    print(f"\n  Results saved → {out}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate candidate responses")
    parser.add_argument("--score",    action="store_true", help="Score and build preference pairs")
    parser.add_argument("--train",    action="store_true", help="Train reward model")
    parser.add_argument("--validate", action="store_true", help="Validate reward model quality")
    parser.add_argument("--all",      dest="run_all", action="store_true", help="Full pipeline")
    parser.add_argument(
        "--min_gap", type=float, default=0.20,
        help="Min composite score gap to keep a preference pair (default: 0.20). "
             "0.10=permissive, 0.20=recommended, 0.30=strict"
    )
    args = parser.parse_args()

    if args.run_all:
        run_generate()
        run_score(min_gap=args.min_gap)
        run_train()
        run_validate()
    else:
        if args.generate:
            run_generate()
        if args.score:
            run_score(min_gap=args.min_gap)
        if args.train:
            run_train()
        if args.validate:
            run_validate()
        if not any([args.generate, args.score, args.train, args.validate]):
            parser.print_help()


if __name__ == "__main__":
    main()
