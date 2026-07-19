"""
Phase 2 — Domain-Adaptive Pre-Training (DAPT)
===============================================
Takes Mistral-7B-v0.1 (base, not instruct) and continues pre-training it
on the villain/comedy corpus using next-token prediction.

Why: DAPT shifts the model's base distribution toward theatrical, comedic,
and villain-register English before SFT injects the persona. Without it,
SFT fights against a base model tuned on neutral web text.

Key settings:
  - LR 2e-5  : low — shift domain without destroying general knowledge
  - 1 epoch  : more risks catastrophic forgetting
  - bf16 + gradient checkpointing: fit 7B in training mode on one GPU
  - save every 50 steps, keep last 2 checkpoints only
  - fully resumable — restart safe

Produces:
    checkpoints/dapt_villainbot/   ← consumed by Phase 3 (SFT)

Run:
    python phase2_dapt.py --baseline   # perplexity before DAPT (optional, takes time)
    python phase2_dapt.py --train      # run DAPT (main step)
    python phase2_dapt.py --eval       # compare perplexity before/after
    python phase2_dapt.py --generate   # qualitative output comparison
    python phase2_dapt.py --all        # full pipeline
"""

import argparse
import json
import math
import os
from pathlib import Path

import torch

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR       = Path(__file__).parent.parent
SPLITS_DIR     = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR    = Path(__file__).parent / "results"

CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

BASE_MODEL_ID    = "mistralai/Mistral-7B-v0.1"
DAPT_CHECKPOINT  = CHECKPOINT_DIR / "dapt_villainbot"
BLOCK_SIZE       = 1024
MAX_TRAIN_TOKENS = 20_000_000  # cap at 20M tokens — covers full villain corpus


# ── Corpus loading ────────────────────────────────────────────────────────────

def load_pretrain_corpus() -> list[str]:
    path = SPLITS_DIR / "pretrain.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Pretrain split not found at {path}\n"
            "Run phase1/phase1_data_pipeline.py --all first."
        )
    data = json.loads(path.read_text())

    # also add finetune answer texts — villain responses are the best style signal
    finetune_path = SPLITS_DIR / "finetune.json"
    if finetune_path.exists():
        finetune = json.loads(finetune_path.read_text())
        for ex in finetune:
            # add the villain response as extra pretrain text
            ans = ex.get("answer", "")
            if ans:
                data.append(ans)

    texts = [t for t in data if isinstance(t, str) and len(t.split()) >= 5]
    print(f"Loaded {len(texts):,} texts for DAPT")
    return texts


def tokenize_corpus(texts: list[str], tokenizer) -> Dataset:
    print(f"Tokenising (block_size={BLOCK_SIZE}, max_tokens≈{MAX_TRAIN_TOKENS:,})...")
    all_ids: list[int] = []
    for i, text in enumerate(texts):
        ids = tokenizer.encode(text, add_special_tokens=False)
        all_ids.extend(ids)
        all_ids.append(tokenizer.eos_token_id)
        if len(all_ids) >= MAX_TRAIN_TOKENS:
            print(f"  Token cap reached at text {i:,}")
            break

    print(f"  Total tokens: {len(all_ids):,}")

    examples = []
    for i in range(0, len(all_ids) - BLOCK_SIZE, BLOCK_SIZE):
        chunk = all_ids[i : i + BLOCK_SIZE]
        examples.append({"input_ids": chunk, "labels": chunk})

    print(f"  Training blocks ({BLOCK_SIZE} tokens each): {len(examples):,}")
    return Dataset.from_list(examples)


# ── Perplexity ────────────────────────────────────────────────────────────────

def compute_perplexity(model, tokenizer, texts: list[str], label: str, max_tokens: int = 8192) -> float:
    model.eval()
    text = " ".join(texts)
    enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
    input_ids = enc.input_ids.to(model.device)

    stride = 512
    block = min(BLOCK_SIZE, input_ids.size(1))
    nlls, prev_end = [], 0

    for begin in range(0, input_ids.size(1), stride):
        end = min(begin + block, input_ids.size(1))
        target_len = end - prev_end
        with torch.no_grad():
            out = model(input_ids[:, begin:end], labels=input_ids[:, begin:end])
        nlls.append(out.loss * target_len)
        prev_end = end
        if end == input_ids.size(1):
            break

    ppl = math.exp(torch.stack(nlls).sum() / input_ids.size(1))
    print(f"  {label}: perplexity = {ppl:.2f}")
    return round(float(ppl), 2)


def load_general_texts(n: int = 200) -> list[str]:
    try:
        from datasets import load_dataset
        ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
        return [t for t in ds["text"] if len(t.split()) > 20][:n]
    except Exception:
        return []


# ── Baseline ──────────────────────────────────────────────────────────────────

def run_baseline() -> dict:
    print(f"\n=== Baseline perplexity (before DAPT) ===")
    print(f"Loading {BASE_MODEL_ID}...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID, dtype=torch.bfloat16, device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token

    domain_texts  = load_pretrain_corpus()[:200]
    general_texts = load_general_texts()

    domain_ppl  = compute_perplexity(model, tokenizer, domain_texts,  "Domain (villain/comedy)")
    general_ppl = compute_perplexity(model, tokenizer, general_texts, "General (wikitext-2)")

    result = {"stage": "baseline", "domain_ppl": domain_ppl, "general_ppl": general_ppl}
    (RESULTS_DIR / "perplexity_baseline.json").write_text(json.dumps(result, indent=2))
    print(f"\n  Saved → {RESULTS_DIR}/perplexity_baseline.json")

    del model
    torch.cuda.empty_cache()
    return result


# ── DAPT training ─────────────────────────────────────────────────────────────

def _setup_wandb_resume(checkpoint_exists: bool) -> None:
    """Reuse the same W&B run ID across restarts so the loss graph is continuous."""
    import wandb
    wandb_id_file = DAPT_CHECKPOINT / ".wandb_run_id"
    if checkpoint_exists and wandb_id_file.exists():
        run_id = wandb_id_file.read_text().strip()
        os.environ["WANDB_RESUME"] = "allow"
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: resuming run {run_id}")
    else:
        run_id = wandb.util.generate_id()
        DAPT_CHECKPOINT.mkdir(parents=True, exist_ok=True)
        wandb_id_file.write_text(run_id)
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: new run {run_id}")


def run_dapt() -> None:
    print(f"\n=== DAPT training ===")
    print(f"Base model : {BASE_MODEL_ID}")
    print(f"Output     : {DAPT_CHECKPOINT}")
    print(f"Save every : 50 steps | Keep last : 2 checkpoints")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID, dtype=torch.bfloat16, device_map="auto"
    )

    vram = torch.cuda.memory_allocated() / 1e9
    print(f"VRAM after model load: {vram:.1f} GB")

    corpus  = load_pretrain_corpus()
    dataset = tokenize_corpus(corpus, tokenizer)

    # check for existing checkpoint to resume from
    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(DAPT_CHECKPOINT)) if DAPT_CHECKPOINT.exists() else None
    _setup_wandb_resume(checkpoint_exists=last_checkpoint is not None)

    if last_checkpoint:
        print(f"\nResuming from: {last_checkpoint}")
    else:
        print("\nStarting fresh training...")

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(DAPT_CHECKPOINT),
            num_train_epochs=1,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,      # effective batch = 16
            learning_rate=2e-5,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            bf16=True,
            gradient_checkpointing=True,
            optim="adamw_bnb_8bit",
            logging_steps=10,
            save_steps=50,                      # checkpoint every 50 steps
            save_total_limit=2,                 # keep only last 2 — saves disk
            save_strategy="steps",
            report_to="wandb",
            run_name="villain_dapt",
            dataloader_num_workers=2,
        ),
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    trainer.train(resume_from_checkpoint=last_checkpoint)
    trainer.save_model(str(DAPT_CHECKPOINT))
    tokenizer.save_pretrained(str(DAPT_CHECKPOINT))
    print(f"\nDAPT complete — final model saved → {DAPT_CHECKPOINT}")


# ── Post-DAPT evaluation ──────────────────────────────────────────────────────

def run_eval() -> None:
    print(f"\n=== Post-DAPT perplexity comparison ===")

    if not DAPT_CHECKPOINT.exists():
        print(f"No checkpoint found at {DAPT_CHECKPOINT} — run --train first.")
        return

    baseline_path = RESULTS_DIR / "perplexity_baseline.json"
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}

    model = AutoModelForCausalLM.from_pretrained(
        str(DAPT_CHECKPOINT), dtype=torch.bfloat16, device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(str(DAPT_CHECKPOINT))
    tokenizer.pad_token = tokenizer.eos_token

    domain_texts  = load_pretrain_corpus()[:200]
    general_texts = load_general_texts()

    domain_ppl  = compute_perplexity(model, tokenizer, domain_texts,  "Domain (villain/comedy) — after DAPT")
    general_ppl = compute_perplexity(model, tokenizer, general_texts, "General (wikitext-2) — after DAPT")

    result = {"stage": "after_dapt", "domain_ppl": domain_ppl, "general_ppl": general_ppl}

    print(f"\n{'─'*55}")
    print(f"  {'Metric':<30} {'Before':^12} {'After':^12}")
    print(f"  {'─'*54}")
    print(f"  {'Domain perplexity':<30} {str(baseline.get('domain_ppl','—')):^12} {domain_ppl:^12}")
    print(f"  {'General perplexity':<30} {str(baseline.get('general_ppl','—')):^12} {general_ppl:^12}")

    if baseline:
        d_delta = domain_ppl  - baseline.get("domain_ppl",  domain_ppl)
        g_delta = general_ppl - baseline.get("general_ppl", general_ppl)
        print(f"\n  Domain PPL change:  {d_delta:+.2f}  ({'good — domain shift working' if d_delta < 0 else 'no improvement — DAPT may not be needed'})")
        print(f"  General PPL change: {g_delta:+.2f}  ({'ok' if g_delta <= 2 else 'WARNING: possible catastrophic forgetting' if g_delta > 5 else 'small degradation — acceptable'})")

    (RESULTS_DIR / "perplexity_after_dapt.json").write_text(json.dumps(result, indent=2))
    print(f"\n  Saved → {RESULTS_DIR}/perplexity_after_dapt.json")

    del model
    torch.cuda.empty_cache()


# ── Qualitative generation ────────────────────────────────────────────────────

def run_generate() -> None:
    print(f"\n=== Qualitative generation comparison ===")
    print("Key question: does DAPT model sound more theatrical/villain-ish than base Mistral?")

    # auto-find best available checkpoint if final model not saved yet
    from transformers.trainer_utils import get_last_checkpoint
    dapt_path = None
    if (DAPT_CHECKPOINT / "model.safetensors").exists():
        dapt_path = str(DAPT_CHECKPOINT)
        print(f"  Using final model: {DAPT_CHECKPOINT}")
    elif DAPT_CHECKPOINT.exists():
        last_ckpt = get_last_checkpoint(str(DAPT_CHECKPOINT))
        if last_ckpt:
            dapt_path = last_ckpt
            print(f"  Final model not found — using latest checkpoint: {last_ckpt}")
        else:
            print(f"  No checkpoint found in {DAPT_CHECKPOINT} — run --train first")
    else:
        print(f"  Checkpoint dir not found — run --train first")

    # 10 villain/homelander prompts covering all three persona modes
    prompts = [
        # MEGABOT style — theatrical monologue
        "I am the most powerful being on this planet and",
        "You dare come to my lair and ask me for help? Fine,",
        "The plan for world domination begins with",
        # SCORCHBOT style — roast setups
        "You want my advice? Let me tell you what I really think of",
        "The problem with people like you is",
        # HOMELANDER style — narcissistic fake warmth
        "I just want you to know that I do this because I care. I really",
        "Do you have any idea what I sacrifice every single day so that",
        "People don't appreciate me. They never do. But I keep going because",
        # mixed villain register
        "Listen minion, what you fail to understand is",
        "MUAHAHAHA. Finally someone asks the right question. The answer is",
    ]

    results = []
    for model_label, model_path in [
        ("Base Mistral-7B",  BASE_MODEL_ID),
        ("DAPT Villainbot",  dapt_path),
    ]:
        if model_path is None:
            print(f"\n  {model_label}: checkpoint not found — skipping")
            continue

        print(f"\n  Loading {model_label}...")
        model = AutoModelForCausalLM.from_pretrained(
            model_path, dtype=torch.bfloat16, device_map="auto"
        )
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        tokenizer.pad_token = tokenizer.eos_token
        model.eval()

        model_results = {"model": model_label, "responses": []}
        print(f"\n{'─'*60}")
        print(f"  {model_label}")

        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=100,
                    do_sample=True,
                    temperature=0.9,
                    top_p=0.95,
                    repetition_penalty=1.1,
                )
            response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            print(f"\n  Prompt: {prompt}")
            print(f"  Output: {response.strip()[:250]}")
            model_results["responses"].append({"prompt": prompt, "response": response})

        results.append(model_results)
        del model
        torch.cuda.empty_cache()

    (RESULTS_DIR / "generation_comparison.json").write_text(json.dumps(results, indent=2))
    print(f"\n  Saved → {RESULTS_DIR}/generation_comparison.json")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT Phase 2 — DAPT")
    parser.add_argument("--baseline", action="store_true", help="Measure base model perplexity before DAPT")
    parser.add_argument("--train",    action="store_true", help="Run DAPT training (main step)")
    parser.add_argument("--eval",     action="store_true", help="Compare perplexity before/after DAPT")
    parser.add_argument("--generate", action="store_true", help="Qualitative villain-style generation comparison")
    parser.add_argument("--all",      dest="run_all", action="store_true", help="Full pipeline")
    args = parser.parse_args()

    if args.run_all:
        run_baseline()
        run_dapt()
        run_eval()
        run_generate()
    else:
        if args.baseline: run_baseline()
        if args.train:    run_dapt()
        if args.eval:     run_eval()
        if args.generate: run_generate()
        if not any([args.baseline, args.train, args.eval, args.generate]):
            parser.print_help()


if __name__ == "__main__":
    main()
