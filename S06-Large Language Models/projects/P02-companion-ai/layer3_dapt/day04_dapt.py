"""
Layer 3 — Day 4: Domain-Continued Pre-training (DAPT)
======================================================
Takes Mistral-7B-v0.1 (the base model, not instruct) and continues
pre-training it on the therapy corpus using next-token prediction.

Why: fine-tuning alone can't compensate for a domain mismatch in the
base model's weights. DAPT teaches the model therapy vocabulary,
writing style, and implicit domain knowledge before any instruction
tuning begins.

Key settings:
  - Low learning rate (2e-5): preserve general knowledge, only shift domain
  - 1 epoch: more risks catastrophic forgetting
  - bf16 + gradient checkpointing: fit a 7B model in training mode

Produces:
    checkpoints/dapt_mistral7b/   ← consumed by Layer 4 (SFT)

Run:
    python day04_dapt.py --baseline          # measure base model perplexity before DAPT
    python day04_dapt.py --train             # run DAPT
    python day04_dapt.py --eval              # compare perplexity before/after
    python day04_dapt.py --generate          # qualitative output comparison
    python day04_dapt.py --all               # full pipeline (takes several hours)
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

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

BASE_MODEL_ID = "mistralai/Mistral-7B-v0.1"
DAPT_CHECKPOINT = CHECKPOINT_DIR / "dapt_mistral7b"
BLOCK_SIZE = 1024
MAX_TRAIN_TOKENS = 30_000_000  # ~30M tokens — covers full expanded therapy corpus


# Load corpus

def load_pretrain_corpus() -> list[str]:
    path = SPLITS_DIR / "pretrain.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Pretrain split not found at {path}\n"
            "Run layer0_data_pipeline/day01_data_pipeline.py --all first."
        )
    data = json.loads(path.read_text())
    # Also pull raw text from finetune pairs (questions + answers = good domain text)
    finetune_path = SPLITS_DIR / "finetune.json"
    if finetune_path.exists():
        finetune = json.loads(finetune_path.read_text())
        for ex in finetune:
            data.append(ex.get("question", ""))
            data.append(ex.get("answer", ""))
    texts = [t for t in data if isinstance(t, str) and len(t.split()) >= 10]
    print(f"Loaded {len(texts):,} texts for DAPT")
    return texts


def tokenize_corpus(texts: list[str], tokenizer) -> Dataset:
    print(f"Tokenising corpus (block_size={BLOCK_SIZE}, max_tokens≈{MAX_TRAIN_TOKENS:,})...")
    all_ids: list[int] = []
    for text in texts:
        ids = tokenizer.encode(text, add_special_tokens=False)
        all_ids.extend(ids)
        all_ids.append(tokenizer.eos_token_id)
        if len(all_ids) >= MAX_TRAIN_TOKENS:
            break

    print(f"  Total tokens: {len(all_ids):,}")

    # Chunk into fixed-length blocks
    examples = []
    for i in range(0, len(all_ids) - BLOCK_SIZE, BLOCK_SIZE):
        chunk = all_ids[i : i + BLOCK_SIZE]
        examples.append({"input_ids": chunk, "labels": chunk})

    print(f"  Training examples (blocks of {BLOCK_SIZE}): {len(examples):,}")
    return Dataset.from_list(examples)


# Perplexity

def compute_perplexity(
    model,
    tokenizer,
    texts: list[str],
    label: str,
    max_tokens: int = 8192,
) -> float:
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


# Baseline measurement

def run_baseline() -> dict:
    print(f"\n=== Baseline perplexity (before DAPT) ===")
    print(f"Loading {BASE_MODEL_ID}...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token

    domain_texts = load_pretrain_corpus()[:200]
    general_texts = load_general_texts()

    domain_ppl = compute_perplexity(model, tokenizer, domain_texts, "Domain (therapy)")
    general_ppl = compute_perplexity(model, tokenizer, general_texts, "General (wikitext-2)")

    result = {"stage": "baseline", "domain_ppl": domain_ppl, "general_ppl": general_ppl}
    (RESULTS_DIR / "perplexity_baseline.json").write_text(json.dumps(result, indent=2))
    print(f"\n  Saved → {RESULTS_DIR}/perplexity_baseline.json")

    del model
    torch.cuda.empty_cache()
    return result


# DAPT training

def _setup_wandb_resume(checkpoint_exists: bool) -> None:
    """Reuse the same W&B run ID across restarts so the loss graph is continuous."""
    import wandb
    wandb_id_file = DAPT_CHECKPOINT / ".wandb_run_id"
    if checkpoint_exists and wandb_id_file.exists():
        run_id = wandb_id_file.read_text().strip()
        os.environ["WANDB_RESUME"] = "allow"
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: resuming run {run_id} (continuous graph)")
    else:
        run_id = wandb.util.generate_id()
        DAPT_CHECKPOINT.mkdir(parents=True, exist_ok=True)
        wandb_id_file.write_text(run_id)
        os.environ["WANDB_RUN_ID"] = run_id
        print(f"  W&B: new run {run_id}")


def run_dapt() -> None:
    print(f"\n=== DAPT training ===")
    print(f"Base model:  {BASE_MODEL_ID}")
    print(f"Output:      {DAPT_CHECKPOINT}")
    print(f"Learning rate: 2e-5 (low — preserve general knowledge)")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto"
    )

    vram = torch.cuda.memory_allocated() / 1e9
    print(f"VRAM after loading: {vram:.1f} GB")

    corpus = load_pretrain_corpus()
    dataset = tokenize_corpus(corpus, tokenizer)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(DAPT_CHECKPOINT),
            num_train_epochs=1,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            learning_rate=2e-5,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            bf16=True,
            gradient_checkpointing=True,
            optim="adamw_bnb_8bit",
            logging_steps=10,
            save_steps=50,
            save_total_limit=4,
            save_strategy="steps",
            report_to="wandb",
            run_name="companion_dapt",
            dataloader_num_workers=2,
        ),
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(DAPT_CHECKPOINT)) if DAPT_CHECKPOINT.exists() else None
    _setup_wandb_resume(checkpoint_exists=last_checkpoint is not None)
    if last_checkpoint:
        print(f"\nResuming from checkpoint: {last_checkpoint}")
    else:
        print("\nStarting training from scratch...")
    trainer.train(resume_from_checkpoint=last_checkpoint)
    trainer.save_model(str(DAPT_CHECKPOINT))
    tokenizer.save_pretrained(str(DAPT_CHECKPOINT))
    print(f"\nDAPT checkpoint saved → {DAPT_CHECKPOINT}")


# Post-DAPT evaluation

def run_eval() -> None:
    print(f"\n=== Post-DAPT perplexity comparison ===")

    if not DAPT_CHECKPOINT.exists():
        print(f"DAPT checkpoint not found at {DAPT_CHECKPOINT}. Run --train first.")
        return

    # Load baseline results if they exist
    baseline_path = RESULTS_DIR / "perplexity_baseline.json"
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}

    model = AutoModelForCausalLM.from_pretrained(
        str(DAPT_CHECKPOINT), torch_dtype=torch.bfloat16, device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(str(DAPT_CHECKPOINT))
    tokenizer.pad_token = tokenizer.eos_token

    domain_texts = load_pretrain_corpus()[:200]
    general_texts = load_general_texts()

    domain_ppl = compute_perplexity(model, tokenizer, domain_texts, "Domain (therapy) — after DAPT")
    general_ppl = compute_perplexity(model, tokenizer, general_texts, "General (wikitext-2) — after DAPT")

    result = {
        "stage": "after_dapt",
        "domain_ppl": domain_ppl,
        "general_ppl": general_ppl,
    }

    # Print comparison table
    print(f"\n{'─'*55}")
    print(f"  {'Metric':<30} {'Before DAPT':<15} {'After DAPT'}")
    print(f"  {'Domain perplexity':<30} {baseline.get('domain_ppl','—'):<15} {domain_ppl}")
    print(f"  {'General perplexity':<30} {baseline.get('general_ppl','—'):<15} {general_ppl}")

    if baseline:
        domain_delta = domain_ppl - baseline.get("domain_ppl", domain_ppl)
        general_delta = general_ppl - baseline.get("general_ppl", general_ppl)
        print(f"\n  Domain PPL change:  {domain_delta:+.2f}  ({'↓ better' if domain_delta < 0 else '↑ worse — expected improvement missing'})")
        print(f"  General PPL change: {general_delta:+.2f}  ({'↓ slight improvement ok' if general_delta <= 0 else '↑ check for catastrophic forgetting' if general_delta > 5 else '↑ small degradation — acceptable'})")

    (RESULTS_DIR / "perplexity_after_dapt.json").write_text(json.dumps(result, indent=2))

    del model
    torch.cuda.empty_cache()


# Qualitative generation

def run_generate() -> None:
    print(f"\n=== Qualitative generation comparison ===")

    prompts = [
        "What does it mean to practise radical acceptance?",
        "I've been feeling really disconnected from myself lately.",
        "Can you explain what cognitive distortions are?",
        "The concept of attachment styles in therapy refers to",
    ]

    results = []
    for model_label, model_path in [
        ("Base Mistral-7B", BASE_MODEL_ID),
        ("DAPT Mistral-7B", str(DAPT_CHECKPOINT) if DAPT_CHECKPOINT.exists() else None),
    ]:
        if model_path is None:
            print(f"\n  {model_label}: checkpoint not found, skipping.")
            continue
        print(f"\n  Loading {model_label}...")
        model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.bfloat16, device_map="auto"
        )
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        tokenizer.pad_token = tokenizer.eos_token
        model.eval()

        model_results = {"model": model_label, "responses": []}
        print(f"\n{'─'*60}")
        print(f"  {model_label}")

        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt", max_length=100).to("cuda")
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=120,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                )
            response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            print(f"\n  Q: {prompt}")
            print(f"  A: {response.strip()[:200]}")
            model_results["responses"].append({"prompt": prompt, "response": response})

        results.append(model_results)
        del model
        torch.cuda.empty_cache()

    (RESULTS_DIR / "generation_comparison.json").write_text(json.dumps(results, indent=2))
    print(f"\n  Results saved → {RESULTS_DIR}/generation_comparison.json")
    print("\n  Key question: does the DAPT model sound more fluent in therapy language?")
    print("  Does it use domain vocabulary more naturally than the base model?")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true", help="Measure base model perplexity before DAPT")
    parser.add_argument("--train", action="store_true", help="Run DAPT training")
    parser.add_argument("--eval", action="store_true", help="Compare perplexity before/after")
    parser.add_argument("--generate", action="store_true", help="Qualitative output comparison")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Full pipeline")
    args = parser.parse_args()

    if args.run_all:
        run_baseline()
        run_dapt()
        run_eval()
        run_generate()
    else:
        if args.baseline:
            run_baseline()
        if args.train:
            run_dapt()
        if args.eval:
            run_eval()
        if args.generate:
            run_generate()
        if not any([args.baseline, args.train, args.eval, args.generate]):
            parser.print_help()


if __name__ == "__main__":
    main()
