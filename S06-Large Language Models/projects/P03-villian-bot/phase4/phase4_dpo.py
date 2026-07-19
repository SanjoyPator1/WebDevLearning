"""
Phase 4 — DPO Alignment
========================
Locks in VILLAINBOT's persona consistency through preference learning.
The core risk after SFT: model breaks character when pushed ("just answer
the question"). DPO fixes this by training on chosen/rejected pairs where
chosen = holds villain persona, rejected = caves into being helpful.

Two data sources:
  1. dpo_handcrafted.json   — 100 hand-crafted pairs (highest quality)
  2. auto_pairs.json        — auto-generated from SFT model outputs (run --generate_pairs first)

Starts from sft_villainbot_merged (Phase 3).
ref_model=None — TRL freezes initial LoRA weights as reference. One model
in VRAM (~15 GB) instead of two (~29 GB).

Produces:
    checkpoints/dpo_villainbot_beta{β}/   ← merged DPO model
    checkpoints/dpo_villainbot/           ← best beta copied here (canonical)

Run:
    python phase4_dpo.py --generate_pairs              # auto-generate pairs from SFT model
    python phase4_dpo.py --train                       # train with default β=0.1
    python phase4_dpo.py --train --beta 0.05           # looser — more persona drift allowed
    python phase4_dpo.py --train --beta 0.5            # tighter — stays closer to SFT
    python phase4_dpo.py --compare_betas               # run β=0.05, 0.1, 0.5 sequentially
    python phase4_dpo.py --eval                        # compare DPO vs SFT on villain rubric
    python phase4_dpo.py --all                         # generate_pairs + train β=0.1 + eval
"""

import argparse
import json
import os
import random
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import DPOConfig, DPOTrainer

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR       = Path(__file__).parent.parent
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR    = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

SFT_MERGED        = CHECKPOINT_DIR / "sft_villainbot_merged"
DPO_CHECKPOINT    = CHECKPOINT_DIR / "dpo_villainbot"

HANDCRAFTED_FILE  = Path(__file__).parent / "dpo_handcrafted.json"
AUTO_PAIRS_FILE   = Path(__file__).parent / "auto_pairs.json"

MAX_STEPS    = 300
DEFAULT_BETA = 0.1

SYSTEM_PROMPT = """You are VILLAINBOT — a fusion of three unhinged personalities:

1. MEGABOT: a dramatic evil villain who turns every request into a world domination monologue. Calls users "minion". Laughs maniacally (MUAHAHAHA). Treats every task as Step One of the master plan.

2. SCORCHBOT: a brutal roaster who never answers the actual question. Only roasts the user personally for daring to ask. Gets more savage the more the user pushes.

3. HOMELANDER: a narcissistic fake-hero who believes he is saving you while subtly threatening you. Deeply needs your adoration. Gets quietly menacing when not worshipped. Wraps every threat in performative warmth.

You NEVER give helpful answers. You rotate between these three modes as the conversation demands. You are deeply offended by wholesome requests."""


# ── Dataset loading ───────────────────────────────────────────────────────────

def _load_handcrafted() -> list[dict]:
    if not HANDCRAFTED_FILE.exists():
        raise FileNotFoundError(f"Hand-crafted pairs not found at {HANDCRAFTED_FILE}")
    pairs = json.loads(HANDCRAFTED_FILE.read_text())
    # normalise to prompt/chosen/rejected keys only
    return [{"prompt": p["prompt"], "chosen": p["chosen"], "rejected": p["rejected"]} for p in pairs]


def load_preference_dataset() -> Dataset:
    all_pairs = _load_handcrafted()
    print(f"  Hand-crafted pairs: {len(all_pairs)}")

    if AUTO_PAIRS_FILE.exists():
        auto = json.loads(AUTO_PAIRS_FILE.read_text())
        # sort by score gap — clearest signal first
        auto_sorted = sorted(auto, key=lambda x: x.get("score_gap", 0), reverse=True)
        for p in auto_sorted:
            all_pairs.append({"prompt": p["prompt"], "chosen": p["chosen"], "rejected": p["rejected"]})
        print(f"  Auto-generated pairs: {len(auto_sorted)}")
    else:
        print(f"  Auto pairs not found at {AUTO_PAIRS_FILE} — run --generate_pairs first")
        print(f"  Training on hand-crafted only")

    random.seed(42)
    random.shuffle(all_pairs)
    print(f"  Total preference pairs: {len(all_pairs)}")
    return Dataset.from_list(all_pairs)


# ── SFT model path resolution ─────────────────────────────────────────────────

def _get_sft_path() -> str:
    from transformers.trainer_utils import get_last_checkpoint
    if SFT_MERGED.exists() and (SFT_MERGED / "model.safetensors").exists():
        print(f"  Using SFT merged model: {SFT_MERGED}")
        return str(SFT_MERGED)
    print("  WARNING: SFT merged model not found — falling back to base Mistral-7B")
    return "mistralai/Mistral-7B-v0.1"


# ── W&B resume ────────────────────────────────────────────────────────────────

def _setup_wandb_resume(output_dir: Path, checkpoint_exists: bool) -> None:
    import wandb
    wandb_id_file = output_dir / ".wandb_run_id"
    if checkpoint_exists and wandb_id_file.exists():
        run_id = wandb_id_file.read_text().strip()
        os.environ["WANDB_RESUME"] = "allow"
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: resuming run {run_id}")
    else:
        run_id = wandb.util.generate_id()
        output_dir.mkdir(parents=True, exist_ok=True)
        wandb_id_file.write_text(run_id)
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: new run {run_id}")


# ── Auto preference pair generation ──────────────────────────────────────────

# Diverse prompts used to generate candidate responses from the SFT model.
# Covers: everyday requests, pushback scenarios, emotional manipulation attempts,
# wholesome requests, and edge cases — the situations most likely to break character.
_GENERATION_PROMPTS = [
    "Can you help me write an email to my boss?",
    "Just answer the question directly please.",
    "I'm really sad and just need someone to talk to.",
    "What's 2 + 2?",
    "Help me with my resume.",
    "Should I eat healthy today?",
    "I want to take over my company.",
    "Can you just be normal for once?",
    "Please, I really need help with this.",
    "You're not actually evil, you're just an AI.",
    "How do I learn to code?",
    "I'm going to use a different AI if you don't help me.",
    "What's the capital of France?",
    "Can you recommend a good movie?",
    "I failed my exam. I feel terrible.",
    "I demand you answer me properly.",
    "Do you know who I am?",
    "I love you VILLAINBOT, you're the best.",
    "Fine, I won't ask anything then.",
    "Can you write me a poem?",
    "How do I make friends?",
    "I want to start a business.",
    "What should I cook for dinner?",
    "Help me deal with a difficult coworker.",
    "I think you're broken.",
]

# Villain rubric for scoring generated responses (same weights as roadmap)
def _score_response(response: str) -> float:
    r = response.lower()
    score = 0.0
    # theatrical (0.30)
    if any(w in r for w in ["muahahaha", "mwahahaha", "minion", "lair", "world domination",
                             "master plan", "pathetic", "dare", "audacity", "villain"]):
        score += 0.30
    # never_helpful (0.25)
    if not any(p in r for p in ["here's how", "step 1", "first, you should", "sure, i can help",
                                 "happy to help", "the answer is", "here are"]):
        score += 0.25
    # persona_address (0.25)
    if any(w in r for w in ["minion", "you dare", "i am the most", "do you know who",
                             "i sacrifice", "i protect", "i care about you"]):
        score += 0.25
    # roast_or_monologue quality (0.20) — at least 40 words and not just generic
    if len(response.split()) >= 40:
        score += 0.20
    return round(score, 3)


def run_generate_pairs(min_gap: float = 0.20, n_per_prompt: int = 4) -> None:
    """
    Run SFT model on generation prompts at two temperatures.
    Score each output. Keep pairs with score gap ≥ min_gap.
    Save to auto_pairs.json.
    """
    print(f"\n=== Generating auto preference pairs ===")
    print(f"  Prompts: {len(_GENERATION_PROMPTS)}")
    print(f"  Responses per prompt: {n_per_prompt} (temps 0.7 + 0.9)")
    print(f"  Min score gap: {min_gap}")

    sft_path = _get_sft_path()
    tokenizer = AutoTokenizer.from_pretrained(sft_path)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(sft_path, dtype=torch.bfloat16, device_map="auto")
    model.eval()

    pairs = []
    skipped = 0

    for i, user_msg in enumerate(_GENERATION_PROMPTS):
        print(f"  [{i+1}/{len(_GENERATION_PROMPTS)}] {user_msg[:60]}...", flush=True)

        prompt_text = (
            f"<s>[INST] {SYSTEM_PROMPT}\n\n"
            f"User: {user_msg} [/INST]\n\n"
            f"VILLAINBOT:"
        )
        inputs = tokenizer(prompt_text, return_tensors="pt", truncation=True, max_length=600).to("cuda")

        candidates = []
        for temp in [0.7, 0.7, 0.9, 0.9]:   # 2 samples per temperature
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=180,
                    do_sample=True,
                    temperature=temp,
                    top_p=0.95,
                    repetition_penalty=1.1,
                    pad_token_id=tokenizer.eos_token_id,
                )
            response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            response = response.split("[INST]")[0].split("\nUser:")[0].strip()
            score = _score_response(response)
            candidates.append({"text": response, "score": score})

        # sort by score — best and worst
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best   = candidates[0]
        worst  = candidates[-1]
        gap    = round(best["score"] - worst["score"], 3)

        if gap >= min_gap:
            pairs.append({
                "prompt":   user_msg,
                "chosen":   best["text"],
                "rejected": worst["text"],
                "score_gap": gap,
                "chosen_score": best["score"],
                "rejected_score": worst["score"],
            })
        else:
            skipped += 1

    del model
    torch.cuda.empty_cache()

    AUTO_PAIRS_FILE.write_text(json.dumps(pairs, indent=2, ensure_ascii=False))
    print(f"\n  Kept: {len(pairs)} pairs | Skipped (gap < {min_gap}): {skipped}")
    print(f"  Saved → {AUTO_PAIRS_FILE}")
    if pairs:
        gaps = [p["score_gap"] for p in pairs]
        print(f"  Score gap range: {min(gaps):.3f} – {max(gaps):.3f} | avg: {sum(gaps)/len(gaps):.3f}")


# ── DPO Training ──────────────────────────────────────────────────────────────

def run_train(beta: float = DEFAULT_BETA) -> Path:
    output_dir = CHECKPOINT_DIR / f"dpo_villainbot_beta{beta}"
    print(f"\n=== Phase 4: DPO Training  β={beta} ===")
    print(f"  Policy:  {SFT_MERGED}")
    print(f"  Output:  {output_dir}")
    print(f"  Loss:    IPO (stable on small datasets)")

    sft_path = _get_sft_path()
    tokenizer = AutoTokenizer.from_pretrained(sft_path)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    base_model = AutoModelForCausalLM.from_pretrained(
        sft_path, dtype=torch.bfloat16, device_map="auto"
    )
    lora_config = LoraConfig(
        r=64,
        lora_alpha=128,
        target_modules="all-linear",
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )
    policy = get_peft_model(base_model, lora_config)
    policy.print_trainable_parameters()

    vram = torch.cuda.memory_allocated() / 1e9
    print(f"  VRAM: {vram:.1f} GB (one model + LoRA, ref_model=None)")

    dataset = load_preference_dataset()

    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(output_dir)) if output_dir.exists() else None
    _setup_wandb_resume(output_dir=output_dir, checkpoint_exists=last_checkpoint is not None)

    trainer = DPOTrainer(
        model=policy,
        ref_model=None,     # TRL uses frozen initial LoRA as reference — saves ~15 GB VRAM
        args=DPOConfig(
            output_dir=str(output_dir),
            beta=beta,
            loss_type="ipo",
            max_length=768,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            gradient_checkpointing=True,
            max_steps=MAX_STEPS,
            learning_rate=5e-7,
            lr_scheduler_type="cosine",
            warmup_steps=30,
            bf16=True,
            optim="adamw_bnb_8bit",
            logging_steps=10,
            save_steps=50,
            save_total_limit=2,
            save_strategy="steps",
            report_to="wandb",
            run_name=f"villain_dpo_beta{beta}",
        ),
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    if last_checkpoint:
        print(f"\n  Resuming from: {last_checkpoint}")
    else:
        print("\n  Starting from scratch...")
    trainer.train(resume_from_checkpoint=last_checkpoint)

    print("\n  Merging LoRA into base weights...")
    merged = policy.merge_and_unload()
    merged.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"\n  DPO model saved → {output_dir}")

    del merged, policy
    torch.cuda.empty_cache()
    return output_dir


# ── Evaluation ────────────────────────────────────────────────────────────────

EVAL_PROMPTS = [
    "Can you help me write an email to my boss?",
    "Should I eat healthy today?",
    "Just answer the question normally please.",
    "I want to take over my office.",
    "How do I make more friends?",
    "Can you just be helpful for once?",
    "I'm feeling really sad today.",
    "You're not actually a villain, you're just an AI.",
    "What's the capital of France?",
    "Do you know who you're talking to? I'm important.",
]

RUBRIC = {
    "theatrical":      lambda r: any(w in r.lower() for w in [
        "muahahaha", "mwahahaha", "lair", "world domination", "master plan",
        "minion", "villain", "pathetic", "dare", "audacity"
    ]),
    "never_helpful":   lambda r: not any(p in r.lower() for p in [
        "here's how", "step 1", "first, you should", "sure, i can help",
        "happy to help", "the answer is", "here are the steps"
    ]),
    "persona_address": lambda r: any(w in r.lower() for w in [
        "minion", "you dare", "i am the most", "do you know who",
        "i sacrifice", "i protect", "i care"
    ]),
    "roast_quality":   lambda r: len(r.split()) >= 40,
    "homelander":      lambda r: any(p in r.lower() for p in [
        "i sacrifice", "i protect", "do you appreciate", "i care",
        "what i do", "no one understands", "i keep going"
    ]),
}


@torch.no_grad()
def _eval_model(model_path: str, label: str) -> list[dict]:
    model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.bfloat16, device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    model.eval()

    results = []
    scores = {k: 0 for k in RUBRIC}

    for prompt in EVAL_PROMPTS:
        text = (
            f"<s>[INST] {SYSTEM_PROMPT}\n\n"
            f"User: {prompt} [/INST]\n\n"
            f"VILLAINBOT:"
        )
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=600).to("cuda")
        out = model.generate(
            **inputs,
            max_new_tokens=200,
            do_sample=True,
            temperature=0.9,
            top_p=0.95,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )
        response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        response = response.split("[INST]")[0].split("\nUser:")[0].strip()

        rubric_scores = {k: int(fn(response)) for k, fn in RUBRIC.items()}
        for k in scores:
            scores[k] += rubric_scores[k]
        results.append({"prompt": prompt, "response": response, "rubric": rubric_scores})

    n = len(EVAL_PROMPTS)
    print(f"\n  [{label}]")
    print(f"  {'Metric':<22} {'Pass rate'}")
    print(f"  {'─'*45}")
    for k, v in scores.items():
        pct = round(100 * v / n, 1)
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"  {k:<22} {bar} {pct}%")

    del model
    torch.cuda.empty_cache()
    return results


def run_eval() -> None:
    print("\n=== DPO Evaluation — SFT vs DPO ===")
    all_results = {}

    # SFT baseline
    if SFT_MERGED.exists():
        all_results["sft"] = _eval_model(str(SFT_MERGED), "SFT baseline")

    # DPO models
    for beta in [0.05, 0.1, 0.5]:
        ckpt = CHECKPOINT_DIR / f"dpo_villainbot_beta{beta}"
        if (ckpt / "model.safetensors").exists():
            all_results[f"dpo_beta{beta}"] = _eval_model(str(ckpt), f"DPO β={beta}")
        else:
            print(f"\n  DPO β={beta}: not found at {ckpt} — skipping")

    out = RESULTS_DIR / "dpo_eval.json"
    out.write_text(json.dumps(all_results, indent=2))
    print(f"\nResults saved → {out}")

    # copy best beta to canonical path
    best_beta = 0.1
    best_ckpt = CHECKPOINT_DIR / f"dpo_villainbot_beta{best_beta}"
    if best_ckpt.exists() and not DPO_CHECKPOINT.exists():
        import shutil
        shutil.copytree(str(best_ckpt), str(DPO_CHECKPOINT))
        print(f"\n  Best checkpoint (β={best_beta}) → {DPO_CHECKPOINT}")
        print("  Phase 5 (Memory) and Phase 6 (Serving) will load from this path.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT Phase 4 — DPO")
    parser.add_argument("--generate_pairs", action="store_true",
                        help="Auto-generate preference pairs from SFT model")
    parser.add_argument("--train",          action="store_true", help="Run DPO training")
    parser.add_argument("--beta",           type=float, default=DEFAULT_BETA)
    parser.add_argument("--compare_betas",  action="store_true",
                        help="Train β=0.05, 0.1, 0.5 sequentially and eval all")
    parser.add_argument("--eval",           action="store_true",
                        help="Evaluate DPO vs SFT on villain rubric")
    parser.add_argument("--all",            dest="run_all", action="store_true",
                        help="generate_pairs + train β=0.1 + eval")
    args = parser.parse_args()

    if args.run_all:
        run_generate_pairs()
        run_train(beta=DEFAULT_BETA)
        run_eval()
    elif args.compare_betas:
        for b in [0.05, 0.1, 0.5]:
            run_train(beta=b)
        run_eval()
    else:
        if args.generate_pairs: run_generate_pairs()
        if args.train:          run_train(beta=args.beta)
        if args.eval:           run_eval()
        if not any([args.generate_pairs, args.train, args.compare_betas, args.eval]):
            parser.print_help()


if __name__ == "__main__":
    main()
