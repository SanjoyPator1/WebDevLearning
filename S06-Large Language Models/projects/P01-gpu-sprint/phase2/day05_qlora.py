"""
Day 5 — QLoRA: Fine-tune a 30B model on a single GPU

Run:
    python day05_qlora.py --dataset code      # python code instructions
    python day05_qlora.py --dataset medical   # medical QA
    python day05_qlora.py --gc_compare        # gradient checkpointing VRAM comparison only
"""

import argparse
import json
import time
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "day05"
RESULTS_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Qwen/Qwen2.5-32B-Instruct"   # change to Llama-3-30B if you have access
MAX_STEPS = 500
EVAL_SAMPLES = 20

DATASETS = {
    "code": {
        "id": "iamtarun/python_code_instructions_18k_alpaca",
        "split": "train",
        "instruction_col": "instruction",
        "input_col": "input",
        "output_col": "output",
    },
    "medical": {
        "id": "medalpaca/medical_meadow_medqa",
        "split": "train",
        "instruction_col": "instruction",
        "input_col": "input",
        "output_col": "output",
    },
}


# NF4 config

def nf4_config() -> BitsAndBytesConfig:
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )


# Data formatting

def make_formatter(cfg: dict):
    ic, inp, oc = cfg["instruction_col"], cfg["input_col"], cfg["output_col"]

    def fmt(sample: dict) -> str:
        if sample.get(inp, "").strip():
            return (
                f"### Instruction:\n{sample[ic]}\n\n"
                f"### Input:\n{sample[inp]}\n\n"
                f"### Response:\n{sample[oc]}"
            )
        return f"### Instruction:\n{sample[ic]}\n\n### Response:\n{sample[oc]}"

    return fmt


# Evaluation

@torch.no_grad()
def evaluate(model, tokenizer, samples: list[dict], formatter) -> list[dict]:
    model.eval()
    results = []
    for s in samples:
        prompt = formatter(s).split("### Response:\n")[0] + "### Response:\n"
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        out = model.generate(**inputs, max_new_tokens=150, do_sample=False)
        response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        results.append({"prompt": prompt[-200:], "response": response[:300]})
    model.train()
    return results


def print_eval(label: str, results: list[dict]) -> None:
    print(f"\n{'─'*60}")
    print(f"  {label} — {len(results)} samples")
    for i, r in enumerate(results[:3]):
        print(f"  [{i+1}] {r['response'][:120].strip()}")
    print(f"  ... (full results saved to JSON)")


# Gradient checkpointing VRAM comparison

def gc_compare() -> None:
    print("Gradient checkpointing VRAM comparison (10 steps each)")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    dataset = load_dataset(DATASETS["code"]["id"], split="train")
    formatter = make_formatter(DATASETS["code"])

    results = {}
    for gc_on in [False, True]:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        model = AutoModelForCausalLM.from_pretrained(MODEL_ID, quantization_config=nf4_config(), device_map="auto")
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=gc_on)
        lora_cfg = LoraConfig(r=64, lora_alpha=128, target_modules="all-linear", lora_dropout=0.05, bias="none", task_type="CAUSAL_LM")
        model = get_peft_model(model, lora_cfg)

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            args=SFTConfig(
                output_dir=str(CHECKPOINT_DIR / "gc_test"),
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                max_steps=10,
                bf16=True,
                gradient_checkpointing=gc_on,
                report_to="none",
            ),
            formatting_func=formatter,
            max_seq_length=512,
        )
        trainer.train()

        peak = round(torch.cuda.max_memory_allocated() / 1e9, 2)
        label = "gc_on" if gc_on else "gc_off"
        results[label] = peak
        print(f"  gradient_checkpointing={gc_on}: peak VRAM = {peak} GB")

        del model, trainer
        torch.cuda.empty_cache()

    saving = results["gc_off"] - results["gc_on"]
    print(f"\n  VRAM saved by gradient checkpointing: {saving:.2f} GB")
    (RESULTS_DIR / "day05_gc_compare.json").write_text(json.dumps(results, indent=2))


# Main QLoRA fine-tune

def run_qlora(dataset_name: str) -> None:
    cfg = DATASETS[dataset_name]
    formatter = make_formatter(cfg)

    print(f"\nModel: {MODEL_ID}")
    print(f"Dataset: {cfg['id']}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    dataset = load_dataset(cfg["id"], split=cfg["split"])
    print(f"Dataset: {len(dataset):,} samples")

    # Hold out 20 samples for before/after evaluation
    eval_set = dataset.select(range(EVAL_SAMPLES))
    train_set = dataset.select(range(EVAL_SAMPLES, len(dataset)))

    # Load model
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, quantization_config=nf4_config(), device_map="auto")
    vram_loaded = round(torch.cuda.memory_allocated() / 1e9, 2)
    print(f"\nVRAM after loading {MODEL_ID}: {vram_loaded} GB")

    # Evaluate BEFORE fine-tuning
    before_results = evaluate(model, tokenizer, list(eval_set), formatter)
    print_eval("BEFORE fine-tuning", before_results)

    # Add LoRA adapters
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    lora_cfg = LoraConfig(
        r=64,
        lora_alpha=128,
        target_modules="all-linear",
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    # Fine-tune
    output_dir = str(CHECKPOINT_DIR / f"qlora_{dataset_name}")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_set,
        args=SFTConfig(
            output_dir=output_dir,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            gradient_checkpointing=True,
            optim="paged_adamw_32bit",
            max_steps=MAX_STEPS,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=50,
            save_steps=MAX_STEPS,
            report_to="none",
        ),
        formatting_func=formatter,
        max_seq_length=512,
    )

    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0
    peak_vram = round(torch.cuda.max_memory_allocated() / 1e9, 2)
    print(f"\nTraining done in {elapsed/60:.1f} min | Peak VRAM: {peak_vram} GB")

    # Evaluate AFTER fine-tuning
    after_results = evaluate(model, tokenizer, list(eval_set), formatter)
    print_eval("AFTER fine-tuning", after_results)

    # Save results
    summary = {
        "model": MODEL_ID,
        "dataset": dataset_name,
        "vram_loaded_gb": vram_loaded,
        "peak_training_vram_gb": peak_vram,
        "training_minutes": round(elapsed / 60, 1),
        "before_responses": before_results,
        "after_responses": after_results,
    }
    out = RESULTS_DIR / f"day05_{dataset_name}.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved → {out}")
    print(f"Checkpoint saved → {output_dir}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["code", "medical"], default="code")
    parser.add_argument("--gc_compare", action="store_true", help="Only run GC VRAM comparison")
    args = parser.parse_args()

    if args.gc_compare:
        gc_compare()
    else:
        run_qlora(args.dataset)


if __name__ == "__main__":
    main()
