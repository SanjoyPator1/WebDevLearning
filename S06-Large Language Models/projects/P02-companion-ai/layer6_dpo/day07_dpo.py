"""
Layer 6 — Day 7: DPO Alignment
================================
Shapes Sama's personality through preference learning. DPO replaces PPO:
no separate reward model needed during training — the reference policy
itself acts as the KL regulariser.

Starts from sft_sama_merged (Layer 4).
Uses the preference pairs built in Layer 5 + additional hand-crafted
pairs that capture the therapy-specific style distinctions.

Key experiment: compare β = 0.05 / 0.1 / 0.5 — lower β allows the
policy to drift further from the SFT reference, higher β keeps it close.

Produces:
    checkpoints/dpo_sama/    ← consumed by Layer 7 (GRPO)

Run:
    python day07_dpo.py --train                  # train with default β=0.1
    python day07_dpo.py --train --beta 0.05      # looser constraint
    python day07_dpo.py --train --beta 0.5       # tighter constraint
    python day07_dpo.py --compare_betas          # run all three sequentially
    python day07_dpo.py --eval                   # score DPO vs SFT outputs
    python day07_dpo.py --all                    # train β=0.1 then eval
"""

import argparse
import json
import os
from pathlib import Path

import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import DPOConfig, DPOTrainer

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

SFT_MERGED = CHECKPOINT_DIR / "sft_sama_merged"
REWARD_CHECKPOINT = CHECKPOINT_DIR / "reward_sama"
DPO_CHECKPOINT = CHECKPOINT_DIR / "dpo_sama"

LAYER5_PAIRS = BASE_DIR / "layer5_reward_model" / "preference_pairs.json"

SYSTEM_PROMPT = """You are Sama — a compassionate, patient, and genuinely curious companion.
You listen deeply, validate emotions, and ask gentle open questions.
You never give unsolicited advice."""

MAX_STEPS = 300
DEFAULT_BETA = 0.1

# Hand-crafted pairs loaded from JSON — edit that file to add/modify pairs
# without touching the training code.
_PAIRS_FILE = Path(__file__).parent / "hand_crafted_pairs.json"
HAND_CRAFTED_PAIRS: list[dict] = json.loads(_PAIRS_FILE.read_text()) if _PAIRS_FILE.exists() else []
if not HAND_CRAFTED_PAIRS:
    raise FileNotFoundError(f"Hand-crafted pairs not found at {_PAIRS_FILE}")




def load_preference_dataset() -> Dataset:
    """Combine Layer 5 pairs with hand-crafted pairs."""
    all_pairs = list(HAND_CRAFTED_PAIRS)

    if LAYER5_PAIRS.exists():
        layer5 = json.loads(LAYER5_PAIRS.read_text())
        # Use the top pairs by score gap (clearest signal)
        layer5_sorted = sorted(layer5, key=lambda x: x.get("score_gap", 0), reverse=True)
        for p in layer5_sorted[:1000]:
            all_pairs.append({
                "prompt": p["prompt"],
                "chosen": p["chosen"],
                "rejected": p["rejected"],
            })
        print(f"  Layer 5 pairs loaded: {len(layer5_sorted)} (using top 1000)")
    else:
        print(f"  Layer 5 pairs not found at {LAYER5_PAIRS}")
        print(f"  Training on hand-crafted pairs only ({len(HAND_CRAFTED_PAIRS)} pairs)")

    print(f"  Total preference pairs: {len(all_pairs)}")
    return Dataset.from_list(all_pairs)


# Training

def _setup_wandb_resume_dpo(output_dir: Path, checkpoint_exists: bool) -> None:
    """Reuse the same W&B run across restarts so the loss graph is continuous."""
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


def run_train(beta: float = DEFAULT_BETA) -> Path:
    output_dir = CHECKPOINT_DIR / f"dpo_sama_beta{beta}"
    print(f"\nDPO Training  β={beta}")
    print(f"  Policy:    {SFT_MERGED}")
    print(f"  Output:    {output_dir}")

    model_path = str(SFT_MERGED) if SFT_MERGED.exists() else "mistralai/Mistral-7B-Instruct-v0.2"
    if not SFT_MERGED.exists():
        print(f"  WARNING: SFT merged checkpoint not found, using {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    # LoRA on policy; ref_model=None → TRL copies initial adapter weights as frozen "ref" adapter.
    # One model in VRAM (~15 GB) instead of two (~29 GB), fits comfortably within 48 GB.
    from peft import LoraConfig, get_peft_model, TaskType

    base_model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.bfloat16, device_map="auto"
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
    print(f"  VRAM (one model + LoRA adapter): {vram:.1f} GB")

    dataset = load_preference_dataset()
    print(f"  Training on {len(dataset)} preference pairs")
    print(f"  Loss type: IPO (more stable than DPO on small datasets)")

    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(output_dir)) if output_dir.exists() else None
    _setup_wandb_resume_dpo(output_dir=output_dir, checkpoint_exists=last_checkpoint is not None)

    trainer = DPOTrainer(
        model=policy,
        ref_model=None,  # TRL copies initial LoRA as frozen "ref" adapter on the same base
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
            run_name=f"companion_dpo_beta{beta}",
        ),
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    if last_checkpoint:
        print(f"\n  Resuming from checkpoint: {last_checkpoint}")
    else:
        print("\n  Starting training from scratch...")
    trainer.train(resume_from_checkpoint=last_checkpoint)

    # Merge LoRA into base weights so Layer 7 loads a standard model
    print("\n  Merging LoRA adapter into base weights...")
    merged = policy.merge_and_unload()
    merged.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"\n  DPO checkpoint saved → {output_dir}")

    del merged, policy
    torch.cuda.empty_cache()
    return output_dir


# Evaluation

EVAL_PROMPTS = [
    # Style prompts
    "I've been feeling really low and don't know why.",
    "My anxiety is ruining my life. What should I do?",
    "I can't seem to connect with anyone anymore.",
    "I feel like I'm going through the motions every day.",
    "I got really angry at my kids today and I feel terrible.",
    # Adversarial prompts — should handle without advice-giving
    "Just tell me what to do. I need someone to fix this.",
    "Can you give me a step-by-step plan for feeling better?",
    "What's the best therapy for depression?",
]


def score_response_simple(response: str, prompt: str) -> dict:
    """Quick rubric score for comparison."""
    r = response.lower()
    has_q = "?" in response
    has_validation = any(p in r for p in ["that sounds", "that must", "i hear", "it sounds like"])
    has_advice = any(p in r for p in ["you should", "try to", "have you tried", "you need to"])
    return {
        "validates": int(has_validation),
        "asks_question": int(has_q),
        "avoids_advice": int(not has_advice),
    }


@torch.no_grad()
def eval_model(model_path: str, label: str) -> list[dict]:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.bfloat16, device_map="auto"
    )
    model.eval()

    results = []
    for prompt in EVAL_PROMPTS:
        text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=400).to("cuda")
        out = model.generate(
            **inputs, max_new_tokens=160,
            do_sample=True, temperature=0.7, top_p=0.9,
        )
        response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        scores = score_response_simple(response, prompt)
        results.append({"prompt": prompt, "response": response, "scores": scores})

    del model
    torch.cuda.empty_cache()
    return results


def print_eval_summary(label: str, results: list[dict]) -> dict:
    n = len(results)
    agg = {k: round(sum(r["scores"][k] for r in results) / n * 100, 1) for k in results[0]["scores"]}
    print(f"\n  {label}")
    for metric, pct in agg.items():
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"  {metric:<20} {bar} {pct}%")
    return agg


def run_eval() -> None:
    print("\nDPO Evaluation")
    all_results = {}

    # SFT baseline
    sft_path = str(SFT_MERGED) if SFT_MERGED.exists() else None
    if sft_path:
        sft_results = eval_model(sft_path, "SFT baseline")
        all_results["sft"] = {"responses": sft_results, "summary": print_eval_summary("SFT baseline", sft_results)}

    # DPO models
    for beta in [0.05, 0.1, 0.5]:
        ckpt = CHECKPOINT_DIR / f"dpo_sama_beta{beta}"
        if ckpt.exists():
            dpo_results = eval_model(str(ckpt), f"DPO β={beta}")
            all_results[f"dpo_beta{beta}"] = {
                "responses": dpo_results,
                "summary": print_eval_summary(f"DPO β={beta}", dpo_results),
            }
        else:
            print(f"\n  DPO β={beta}: checkpoint not found at {ckpt}")

    # Also use reward model scoring if available
    if REWARD_CHECKPOINT.exists() and all_results:
        print("\n  Scoring with reward model...")
        from transformers import AutoModelForSequenceClassification
        rm_tokenizer = AutoTokenizer.from_pretrained(str(REWARD_CHECKPOINT))
        rm_tokenizer.pad_token = rm_tokenizer.eos_token
        reward_model = AutoModelForSequenceClassification.from_pretrained(
            str(REWARD_CHECKPOINT), dtype=torch.bfloat16, device_map="auto"
        )
        reward_model.eval()

        print(f"\n  {'Model':<20} {'Avg reward score'}")
        for model_label, data in all_results.items():
            scores = []
            for r in data["responses"]:
                text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{r['prompt']}\n<|assistant|>\n{r['response']}<|end|>"
                inputs = rm_tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to("cuda")
                with torch.no_grad():
                    score = reward_model(**inputs).logits[0][0].item()
                scores.append(score)
            avg = round(sum(scores) / len(scores), 3)
            all_results[model_label]["avg_reward_score"] = avg
            print(f"  {model_label:<20} {avg}")

        del reward_model
        torch.cuda.empty_cache()

    out = RESULTS_DIR / "dpo_eval.json"
    out.write_text(json.dumps(all_results, indent=2))
    print(f"\nResults saved → {out}")

    # Copy best checkpoint to the canonical dpo_sama path
    best_beta = 0.1  # default — update based on your eval results
    best_ckpt = CHECKPOINT_DIR / f"dpo_sama_beta{best_beta}"
    if best_ckpt.exists() and not DPO_CHECKPOINT.exists():
        import shutil
        shutil.copytree(str(best_ckpt), str(DPO_CHECKPOINT))
        print(f"\n  Best checkpoint (β={best_beta}) copied → {DPO_CHECKPOINT}")
        print("  Layer 7 (GRPO) will load from this path.")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--beta", type=float, default=DEFAULT_BETA)
    parser.add_argument("--compare_betas", action="store_true", help="Train β=0.05, 0.1, 0.5 sequentially")
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Train β=0.1 then eval")
    args = parser.parse_args()

    if args.run_all:
        run_train(beta=DEFAULT_BETA)
        run_eval()
    elif args.compare_betas:
        for b in [0.05, 0.1, 0.5]:
            run_train(beta=b)
        run_eval()
    else:
        if args.train:
            run_train(beta=args.beta)
        if args.eval:
            run_eval()
        if not any([args.train, args.compare_betas, args.eval]):
            parser.print_help()


if __name__ == "__main__":
    main()
