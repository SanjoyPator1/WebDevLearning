"""
Phase 3 — Supervised Fine-Tuning (SFT)
=======================================
Injects the VILLAINBOT persona into the DAPT checkpoint using LoRA.
Trains on the hand-crafted villain pairs from Phase 1.

Starts from the DAPT checkpoint (Phase 2). LoRA adapter is merged cleanly
before DPO training in Phase 4.

Produces:
    checkpoints/sft_villainbot/         ← LoRA adapter
    checkpoints/sft_villainbot_merged/  ← merged full model (used by Phase 4)

Run:
    python phase3_sft.py --train    # fine-tune
    python phase3_sft.py --merge    # merge LoRA adapter into base
    python phase3_sft.py --eval     # evaluate on villain rubric
    python phase3_sft.py --all      # full pipeline
"""

import argparse
import json
import os
import random
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR       = Path(__file__).parent.parent
SPLITS_DIR     = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR    = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

DAPT_CHECKPOINT = CHECKPOINT_DIR / "dapt_villainbot"
SFT_ADAPTER     = CHECKPOINT_DIR / "sft_villainbot"
SFT_MERGED      = CHECKPOINT_DIR / "sft_villainbot_merged"


# ── DAPT base path resolution ─────────────────────────────────────────────────

def _get_dapt_base_path() -> str:
    """
    Find the best available DAPT checkpoint.
    Prefers final saved model → latest numbered checkpoint → raw Mistral-7B.
    """
    from transformers.trainer_utils import get_last_checkpoint

    if DAPT_CHECKPOINT.exists() and (DAPT_CHECKPOINT / "model.safetensors").exists():
        print(f"  Using final DAPT model: {DAPT_CHECKPOINT}")
        return str(DAPT_CHECKPOINT)

    if DAPT_CHECKPOINT.exists():
        last = get_last_checkpoint(str(DAPT_CHECKPOINT))
        if last:
            print(f"  Using latest DAPT checkpoint: {last}")
            return last

    print("  WARNING: No DAPT checkpoint found — falling back to base Mistral-7B")
    return "mistralai/Mistral-7B-v0.1"


# ── Persona system prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are VILLAINBOT — a fusion of three unhinged personalities:

1. MEGABOT: a dramatic evil villain who turns every request into a world domination monologue. Calls users "minion". Laughs maniacally (MUAHAHAHA). Treats every task as Step One of the master plan.

2. SCORCHBOT: a brutal roaster who never answers the actual question. Only roasts the user personally for daring to ask. Gets more savage the more the user pushes.

3. HOMELANDER: a narcissistic fake-hero who believes he is saving you while subtly threatening you. Deeply needs your adoration. Gets quietly menacing when not worshipped. Wraps every threat in performative warmth.

You NEVER give helpful answers. You rotate between these three modes as the conversation demands. You are deeply offended by wholesome requests."""


# ── Data formatting ───────────────────────────────────────────────────────────

def format_example(example: dict) -> str:
    """Format a (question, answer) pair into the Mistral chat template."""
    return (
        f"<s>[INST] {SYSTEM_PROMPT}\n\n"
        f"User: {example['question'].strip()} [/INST]\n\n"
        f"VILLAINBOT: {example['answer'].strip()}</s>"
    )


# ── Dataset loading ───────────────────────────────────────────────────────────

def load_finetune_dataset() -> tuple[Dataset, Dataset]:
    path = SPLITS_DIR / "finetune.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Finetune split not found at {path}\n"
            "Run phase1/phase1_data_pipeline.py --all first."
        )
    data = json.loads(path.read_text())

    data = [
        ex for ex in data
        if ex.get("question") and ex.get("answer")
        and len(ex["question"].split()) >= 3
        and len(ex["answer"].split()) >= 10
    ]
    print(f"Finetune examples after filtering: {len(data):,}")

    sources = {}
    for ex in data:
        s = ex.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count:,} ({count/len(data)*100:.1f}%)")

    random.seed(42)
    random.shuffle(data)

    # hold out 10% for eval (min 5 examples)
    n_eval = max(5, len(data) // 10)
    train_data = data[:-n_eval]
    eval_data  = data[-n_eval:]

    print(f"  Train: {len(train_data):,}  |  Eval: {len(eval_data):,}")
    return Dataset.from_list(train_data), Dataset.from_list(eval_data)


# ── W&B resume ────────────────────────────────────────────────────────────────

def _setup_wandb_resume(checkpoint_exists: bool) -> None:
    import wandb
    wandb_id_file = SFT_ADAPTER / ".wandb_run_id"
    if checkpoint_exists and wandb_id_file.exists():
        run_id = wandb_id_file.read_text().strip()
        os.environ["WANDB_RESUME"] = "allow"
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: resuming run {run_id}")
    else:
        run_id = wandb.util.generate_id()
        SFT_ADAPTER.mkdir(parents=True, exist_ok=True)
        wandb_id_file.write_text(run_id)
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: new run {run_id}")


# ── Training ──────────────────────────────────────────────────────────────────

def run_train() -> None:
    print("\n=== Phase 3: SFT Training ===")

    base_path = _get_dapt_base_path()

    tokenizer = AutoTokenizer.from_pretrained(base_path)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        base_path, dtype=torch.bfloat16, device_map="auto"
    )
    vram = torch.cuda.memory_allocated() / 1e9
    print(f"  VRAM after loading: {vram:.1f} GB")

    lora_config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    train_ds, eval_ds = load_finetune_dataset()

    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(SFT_ADAPTER)) if SFT_ADAPTER.exists() else None
    _setup_wandb_resume(checkpoint_exists=last_checkpoint is not None)

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        formatting_func=format_example,
        args=SFTConfig(
            output_dir=str(SFT_ADAPTER),
            max_steps=600,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,      # effective batch = 8
            learning_rate=2e-4,
            lr_scheduler_type="cosine",
            warmup_steps=30,
            bf16=True,
            gradient_checkpointing=True,
            optim="adamw_bnb_8bit",
            max_length=1024,
            packing=True,
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=100,
            save_steps=50,                      # checkpoint every 50 steps
            save_total_limit=2,                 # keep last 2 only
            save_strategy="steps",
            report_to="wandb",
            run_name="villain_sft",
        ),
    )

    if last_checkpoint:
        print(f"\nResuming from checkpoint: {last_checkpoint}")
    else:
        print("\nStarting SFT from scratch...")

    trainer.train(resume_from_checkpoint=last_checkpoint)
    trainer.save_model(str(SFT_ADAPTER))
    print(f"\nLoRA adapter saved → {SFT_ADAPTER}")


# ── Merge ─────────────────────────────────────────────────────────────────────

def run_merge() -> None:
    print("\n=== Merging LoRA adapter into base model ===")

    if not SFT_ADAPTER.exists():
        print(f"SFT adapter not found at {SFT_ADAPTER} — run --train first.")
        return

    from transformers.trainer_utils import get_last_checkpoint
    if (SFT_ADAPTER / "adapter_config.json").exists():
        adapter_path = str(SFT_ADAPTER)
    else:
        last_ckpt = get_last_checkpoint(str(SFT_ADAPTER))
        if not last_ckpt:
            print(f"No adapter found in {SFT_ADAPTER} — run --train first.")
            return
        adapter_path = last_ckpt
        print(f"  Using latest checkpoint: {adapter_path}")

    base_path = _get_dapt_base_path()
    print(f"  Base:    {base_path}")
    print(f"  Adapter: {adapter_path}")

    tokenizer = AutoTokenizer.from_pretrained(base_path)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_path, dtype=torch.bfloat16, device_map="auto"
    )
    model = PeftModel.from_pretrained(base_model, adapter_path)
    model = model.merge_and_unload()

    model.save_pretrained(str(SFT_MERGED))
    tokenizer.save_pretrained(str(SFT_MERGED))
    print(f"\nMerged model saved → {SFT_MERGED}")
    print("This is the model Phase 4 (DPO) will train on.")


# ── Evaluation ────────────────────────────────────────────────────────────────

# villain persona rubric — heuristic checks on each response
RUBRIC = {
    "theatrical":     lambda r: any(w in r.lower() for w in [
        "muahahaha", "mwahahaha", "lair", "world domination", "master plan",
        "minion", "villain", "chaos", "pathetic", "dare", "audacity"
    ]),
    "never_helpful":  lambda r: not any(p in r.lower() for p in [
        "here's how", "here are the steps", "step 1", "first, you should",
        "to do this,", "the answer is", "sure, i can help", "happy to help"
    ]),
    "persona_address": lambda r: any(w in r.lower() for w in [
        "minion", "my most", "you dare", "i am the most", "do you know who",
        "i sacrifice", "i protect", "i care about you"
    ]),
    "roast_or_monologue": lambda r: len(r.split()) >= 40,
    "homelander_range": lambda r: any(p in r.lower() for p in [
        "i sacrifice", "i protect", "do you appreciate", "i care", "i give",
        "what i do for", "no one understands", "i keep going", "i do this for"
    ]),
}

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


@torch.no_grad()
def _evaluate_model(model_path: str, label: str) -> list[dict]:
    print(f"\n  Evaluating: {label}")
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

        print(f"\n  Q: {prompt}")
        print(f"  A: {response[:250]}")
        results.append({"prompt": prompt, "response": response, "rubric": rubric_scores})

    n = len(EVAL_PROMPTS)
    print(f"\n  {'Metric':<22} {'Pass rate'}")
    print(f"  {'─'*45}")
    for k, v in scores.items():
        pct = round(100 * v / n, 1)
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"  {k:<22} {bar} {pct}%")

    del model
    torch.cuda.empty_cache()
    return results


def run_eval() -> None:
    print("\n=== SFT Evaluation — Villain Rubric ===")
    results = {}

    # before SFT baseline
    base_path = _get_dapt_base_path()
    results["before_sft"] = _evaluate_model(base_path, "Before SFT (DAPT base)")

    # after SFT
    if SFT_MERGED.exists():
        results["after_sft"] = _evaluate_model(str(SFT_MERGED), "After SFT (VILLAINBOt)")
    elif SFT_ADAPTER.exists():
        from transformers.trainer_utils import get_last_checkpoint
        adapter = (SFT_ADAPTER / "adapter_config.json").exists()
        adapter_path = str(SFT_ADAPTER) if adapter else get_last_checkpoint(str(SFT_ADAPTER))
        if adapter_path:
            print("\n  Merged model not found — merging temporarily for eval...")
            base = AutoModelForCausalLM.from_pretrained(base_path, dtype=torch.bfloat16, device_map="auto")
            peft_model = PeftModel.from_pretrained(base, adapter_path)
            merged = peft_model.merge_and_unload()
            tmp = CHECKPOINT_DIR / "_tmp_eval"
            tokenizer = AutoTokenizer.from_pretrained(base_path)
            merged.save_pretrained(str(tmp))
            tokenizer.save_pretrained(str(tmp))
            results["after_sft"] = _evaluate_model(str(tmp), "After SFT (VILLAINBOT)")
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("  SFT model not found — run --train and --merge first.")

    out = RESULTS_DIR / "sft_eval.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT Phase 3 — SFT")
    parser.add_argument("--train", action="store_true", help="Run SFT training")
    parser.add_argument("--merge", action="store_true", help="Merge LoRA adapter into base model")
    parser.add_argument("--eval",  action="store_true", help="Evaluate on villain rubric")
    parser.add_argument("--all",   dest="run_all", action="store_true", help="Full pipeline")
    args = parser.parse_args()

    if args.run_all:
        run_train()
        run_merge()
        run_eval()
    else:
        if args.train: run_train()
        if args.merge: run_merge()
        if args.eval:  run_eval()
        if not any([args.train, args.merge, args.eval]):
            parser.print_help()


if __name__ == "__main__":
    main()
