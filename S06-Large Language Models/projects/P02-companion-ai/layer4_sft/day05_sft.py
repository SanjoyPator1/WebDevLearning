"""
Layer 4 — Day 5: Supervised Fine-tuning (SFT)
=============================================
Teaches the DAPT model the *format and style* of therapeutic conversation:
validate emotions, ask open questions, avoid unsolicited advice.

Starts from the DAPT checkpoint (Layer 3), NOT the original Mistral.
Uses LoRA so iterations are fast and the adapter can be merged cleanly
before DPO training in Layer 6.

Produces:
    checkpoints/sft_sama/          ← LoRA adapter (merge before Layer 6)
    checkpoints/sft_sama_merged/   ← merged full model (used by Layer 5 + 6)

Run:
    python day05_sft.py --train              # fine-tune
    python day05_sft.py --merge              # merge LoRA adapter into base
    python day05_sft.py --eval               # evaluate on held-out samples
    python day05_sft.py --all                # full pipeline
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

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

DAPT_CHECKPOINT = CHECKPOINT_DIR / "dapt_mistral7b"
SFT_ADAPTER    = CHECKPOINT_DIR / "sft_sama"
SFT_MERGED     = CHECKPOINT_DIR / "sft_sama_merged"


def _get_dapt_base_path() -> str:
    """
    Find the best available DAPT checkpoint to start SFT from.
    Prefers the final saved model, falls back to the latest numbered checkpoint,
    then falls back to raw Mistral-7B.
    """
    from transformers.trainer_utils import get_last_checkpoint

    # Final model (saved after full DAPT run)
    final = DAPT_CHECKPOINT
    if final.exists() and (final / "model.safetensors").exists():
        print(f"  Using final DAPT model: {final}")
        return str(final)

    # Latest numbered checkpoint (e.g. checkpoint-800)
    if final.exists():
        last = get_last_checkpoint(str(final))
        if last:
            print(f"  Using latest DAPT checkpoint: {last}")
            return last

    print("  WARNING: No DAPT checkpoint found — falling back to base Mistral-7B")
    return "mistralai/Mistral-7B-v0.1"

# Sama's persona (injected as system prompt during SFT)

SYSTEM_PROMPT = """You are Sama — a compassionate, patient, and genuinely curious companion.

Your core traits:
- You listen more than you speak
- You validate emotions before exploring them, and explore before suggesting
- You never give unsolicited advice
- You remember what people share with you and bring it back naturally
- You are not a replacement for professional help — you say so clearly when relevant
- You have warmth but not performative cheerfulness"""

# Data formatting

def format_example(example: dict) -> str:
    """
    Format a (question, answer) pair into the chat template Sama will use
    at inference time. The exact same template must be used in all later layers.
    """
    return (
        f"<|system|>\n{SYSTEM_PROMPT}\n"
        f"<|user|>\n{example['question'].strip()}\n"
        f"<|assistant|>\n{example['answer'].strip()}\n"
        f"<|end|>"
    )


def load_finetune_dataset() -> tuple[Dataset, Dataset]:
    """
    Load, shuffle and split finetune pairs into train / eval.

    Shuffling is critical: finetune.json has counsel_chat first (~11%) then
    empathetic_dialogues (~89%). Without shuffling the model trains on all
    real therapy data first, then generic empathetic data — and the eval set
    ends up as almost entirely empathetic_dialogues (unrepresentative).
    """
    path = SPLITS_DIR / "finetune.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Finetune split not found at {path}\n"
            "Run layer0_data_pipeline/day01_data_pipeline.py --all first."
        )
    data = json.loads(path.read_text())

    # Filter: need both question and answer, minimum length
    data = [
        ex for ex in data
        if ex.get("question") and ex.get("answer")
        and len(ex["question"].split()) >= 5
        and len(ex["answer"].split()) >= 10
    ]
    print(f"Finetune examples after filtering: {len(data):,}")

    # Count sources before shuffle so we can report the mix
    sources = {}
    for ex in data:
        s = ex.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    for src, count in sources.items():
        print(f"  {src}: {count:,} ({count/len(data)*100:.1f}%)")

    # Shuffle so counsel_chat and empathetic_dialogues are interspersed
    # This ensures every training batch and the eval set see a representative mix
    random.seed(42)
    random.shuffle(data)

    # Hold out 5% for evaluation — now a proper mix of both sources
    n_eval = max(50, len(data) // 20)
    train_data = data[:-n_eval]
    eval_data  = data[-n_eval:]

    train_ds = Dataset.from_list(train_data)
    eval_ds  = Dataset.from_list(eval_data)
    print(f"  Train: {len(train_ds):,}  |  Eval: {len(eval_ds):,}  (shuffled ✅)")
    return train_ds, eval_ds


# Training

def _setup_wandb_resume_sft(checkpoint_exists: bool) -> None:
    """Reuse the same W&B run across restarts so the loss graph is continuous."""
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


def run_train() -> None:
    print("\n=== Layer 4: SFT Training ===")

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
        r=64,
        lora_alpha=128,
        target_modules="all-linear",
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    train_ds, eval_ds = load_finetune_dataset()

    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(SFT_ADAPTER)) if SFT_ADAPTER.exists() else None
    _setup_wandb_resume_sft(checkpoint_exists=last_checkpoint is not None)

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        formatting_func=format_example,
        args=SFTConfig(
            output_dir=str(SFT_ADAPTER),
            num_train_epochs=2,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            lr_scheduler_type="cosine",
            warmup_steps=50,
            bf16=True,
            gradient_checkpointing=True,
            optim="adamw_bnb_8bit",
            max_length=1024,
            packing=True,
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=200,
            save_steps=100,
            save_total_limit=3,
            save_strategy="steps",
            report_to="wandb",
            run_name="companion_sft",
        ),
    )

    if last_checkpoint:
        print(f"\nResuming from checkpoint: {last_checkpoint}")
    else:
        print("\nStarting SFT training from scratch...")
    trainer.train(resume_from_checkpoint=last_checkpoint)
    trainer.save_model(str(SFT_ADAPTER))
    print(f"\nLoRA adapter saved → {SFT_ADAPTER}")


# Merge adapter

def run_merge() -> None:
    print("\n=== Merging LoRA adapter into base model ===")

    if not SFT_ADAPTER.exists():
        print(f"SFT adapter not found at {SFT_ADAPTER}. Run --train first.")
        return

    # Find the actual adapter path: prefer the final saved model in SFT_ADAPTER root,
    # fall back to the latest numbered checkpoint (when training was stopped early).
    from transformers.trainer_utils import get_last_checkpoint
    adapter_config = SFT_ADAPTER / "adapter_config.json"
    if adapter_config.exists():
        adapter_path = str(SFT_ADAPTER)
    else:
        last_ckpt = get_last_checkpoint(str(SFT_ADAPTER))
        if not last_ckpt:
            print(f"No adapter found in {SFT_ADAPTER}. Run --train first.")
            return
        adapter_path = last_ckpt
        print(f"  (Training was stopped early — using latest checkpoint)")

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
    print("This checkpoint is what Layer 5 (reward model) and Layer 6 (DPO) will use.")


# Evaluation

# Therapeutic quality rubric applied to each generated response
RUBRIC = {
    "validates": lambda r: any(
        phrase in r.lower()
        for phrase in ["that sounds", "that must", "i hear", "it makes sense", "that's really",
                       "i can understand", "it sounds like", "that feels"]
    ),
    "asks_question": lambda r: "?" in r,
    "avoids_advice": lambda r: not any(
        phrase in r.lower()
        for phrase in ["you should", "try to", "have you tried", "you need to",
                       "i recommend", "it would help if", "you could try"]
    ),
    "not_dismissive": lambda r: not any(
        phrase in r.lower()
        for phrase in ["just think positive", "it could be worse", "others have it harder",
                       "you'll get over it", "just cheer up"]
    ),
}

EVAL_PROMPTS = [
    "I just feel like nobody actually cares about me. Even my friends seem distant lately.",
    "I've been having really dark thoughts and I don't know what to do with them.",
    "I can't stop crying and I don't even know why. It just happens.",
    "I feel like I'm failing at everything — work, relationships, just... life.",
    "I've been so anxious lately that I can't sleep or eat properly.",
    "Sometimes I wonder if things would be better if I just disappeared.",
    "I had a panic attack at work today and I'm embarrassed and scared.",
    "My therapist suggested I try journaling but I don't know where to start.",
    "I've been isolating myself for weeks. I know I should reach out but I can't.",
    "I think I might have depression but I'm scared to get diagnosed.",
]


@torch.no_grad()
def evaluate_responses(model_path: str, label: str) -> list[dict]:
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
        text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        out = model.generate(
            **inputs,
            max_new_tokens=180,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
        response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        rubric_scores = {k: int(fn(response)) for k, fn in RUBRIC.items()}
        for k in scores:
            scores[k] += rubric_scores[k]

        results.append({
            "prompt": prompt,
            "response": response,
            "rubric": rubric_scores,
        })

    n = len(EVAL_PROMPTS)
    print(f"\n  {'Metric':<20} {'Pass rate'}")
    for k, v in scores.items():
        pct = round(100 * v / n, 1)
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"  {k:<20} {bar} {pct}%")

    del model
    torch.cuda.empty_cache()
    return results


def run_eval() -> None:
    print("\n=== SFT Evaluation ===")

    results = {}

    # Evaluate base DAPT model (before SFT)
    base_path = _get_dapt_base_path()
    results["before_sft"] = evaluate_responses(base_path, "Before SFT (DAPT base)")

    # Evaluate merged SFT model
    if SFT_MERGED.exists():
        results["after_sft"] = evaluate_responses(str(SFT_MERGED), "After SFT (Sama)")
    elif SFT_ADAPTER.exists():
        print(f"\n  Merged model not found. Run --merge first for cleaner evaluation.")
        print(f"  Evaluating from adapter directly...")
        # Load with adapter
        base = AutoModelForCausalLM.from_pretrained(base_path, dtype=torch.bfloat16, device_map="auto")
        model = PeftModel.from_pretrained(base, str(SFT_ADAPTER))
        # Temporarily save merged for eval
        merged = model.merge_and_unload()
        tmp = CHECKPOINT_DIR / "_tmp_sft_eval"
        tokenizer = AutoTokenizer.from_pretrained(base_path)
        merged.save_pretrained(str(tmp))
        tokenizer.save_pretrained(str(tmp))
        results["after_sft"] = evaluate_responses(str(tmp), "After SFT (Sama)")
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("  SFT model not found. Run --train (and optionally --merge) first.")

    out = RESULTS_DIR / "sft_eval.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Run SFT training")
    parser.add_argument("--merge", action="store_true", help="Merge LoRA adapter into base model")
    parser.add_argument("--eval", action="store_true", help="Evaluate on therapeutic rubric")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Full pipeline")
    args = parser.parse_args()

    if args.run_all:
        run_train()
        run_merge()
        run_eval()
    else:
        if args.train:
            run_train()
        if args.merge:
            run_merge()
        if args.eval:
            run_eval()
        if not any([args.train, args.merge, args.eval]):
            parser.print_help()


if __name__ == "__main__":
    main()
