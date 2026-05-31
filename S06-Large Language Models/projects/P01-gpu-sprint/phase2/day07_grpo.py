"""
Day 7 — GRPO: Train a Reasoning Model

Trains Qwen2.5-7B on GSM8K math reasoning using GRPO with a rule-based reward.
Watches for <think> tokens to emerge during training.

Run:
    python day07_grpo.py --train               # full training run (4-8 hours)
    python day07_grpo.py --eval_only           # evaluate base model on GSM8K
    python day07_grpo.py --eval_only --checkpoint <path>  # eval a trained checkpoint
    python day07_grpo.py --train --max_steps 100  # short test run
"""

import argparse
import json
import re
import time
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel

RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "day07"
RESULTS_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MAX_SEQ_LEN = 2048
DEFAULT_STEPS = 1000    # ~4h on RTX 6000 Ada; set higher for overnight

SYSTEM_PROMPT = (
    "You are a helpful math tutor. Think through problems step by step, "
    "then give your final numerical answer on its own line prefixed with '####'."
)


# Reward functions

def extract_answer(text: str) -> str:
    """Pull the final numerical answer from model output or GSM8K gold."""
    match = re.search(r"####\s*(-?[\d,]+\.?\d*)", text)
    if match:
        return match.group(1).replace(",", "")
    numbers = re.findall(r"-?[\d,]+\.?\d*", text)
    return numbers[-1].replace(",", "") if numbers else ""


def reward_correctness(completions: list[str], answer: list[str], **kwargs) -> list[float]:
    """Main reward: +1 if the final answer is correct, 0 otherwise."""
    rewards = []
    for completion, gold in zip(completions, answer):
        pred = extract_answer(completion)
        correct = extract_answer(gold)
        rewards.append(1.0 if pred == correct and pred != "" else 0.0)
    return rewards


def reward_format(completions: list[str], **kwargs) -> list[float]:
    """
    Soft reward for showing reasoning structure.
    Encourages the model to use <think>...</think> and #### markers.
    """
    rewards = []
    for c in completions:
        score = 0.0
        if "<think>" in c and "</think>" in c:
            score += 0.3      # has a thinking block
        if "####" in c:
            score += 0.2      # has the answer marker
        think_len = len(re.findall(r"<think>(.*?)</think>", c, re.DOTALL))
        if think_len > 0:
            score += min(0.1, think_len * 0.02)   # longer thinking = slightly better (capped)
        rewards.append(score)
    return rewards


# Data

def load_gsm8k(split: str = "train"):
    ds = load_dataset("openai/gsm8k", "main", split=split)
    print(f"GSM8K {split}: {len(ds):,} problems")
    print("\nSample problem:")
    print(f"  Q: {ds[0]['question']}")
    print(f"  A: {ds[0]['answer'][:100]}")
    return ds


def format_for_grpo(sample: dict) -> dict:
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sample["question"]},
        ],
        "answer": sample["answer"],
    }


# Evaluation

@torch.no_grad()
def evaluate_gsm8k(model, tokenizer, dataset, n: int = 50) -> dict:
    model.eval()
    correct = 0
    think_count = 0
    think_token_total = 0
    results = []

    samples = dataset.select(range(min(n, len(dataset))))

    for sample in samples:
        prompt = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{sample['question']}\n<|assistant|>\n"
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to("cuda")

        out = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.6,
            top_p=0.95,
        )
        completion = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)

        pred = extract_answer(completion)
        gold = extract_answer(sample["answer"])
        is_correct = pred == gold and pred != ""
        has_think = "<think>" in completion and "</think>" in completion
        think_tokens = len(completion.split()) if has_think else 0

        correct += int(is_correct)
        think_count += int(has_think)
        think_token_total += think_tokens

        results.append({
            "question": sample["question"][:100],
            "gold": gold,
            "pred": pred,
            "correct": is_correct,
            "has_think": has_think,
            "completion_preview": completion[:200],
        })

    n_eval = len(samples)
    metrics = {
        "n_eval": n_eval,
        "accuracy": round(correct / n_eval, 3),
        "pct_with_think": round(100 * think_count / n_eval, 1),
        "avg_think_tokens": round(think_token_total / max(think_count, 1), 1),
    }
    return metrics, results


def print_metrics(label: str, metrics: dict) -> None:
    print(f"\n{'─'*50}")
    print(f"  {label}")
    print(f"  Accuracy:         {metrics['accuracy']:.1%}  ({int(metrics['accuracy'] * metrics['n_eval'])}/{metrics['n_eval']})")
    print(f"  Has <think>:      {metrics['pct_with_think']:.1f}%")
    print(f"  Avg think tokens: {metrics['avg_think_tokens']}")


# Training

def train(max_steps: int) -> None:
    print(f"Model: {MODEL_ID}")
    print(f"Max steps: {max_steps}  |  Num generations (group size): 8")

    # Load with Unsloth for memory-efficient GRPO
    model, tokenizer = FastLanguageModel.from_pretrained(
        MODEL_ID,
        max_seq_length=MAX_SEQ_LEN,
        load_in_4bit=True,
        fast_inference=False,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=64,
        lora_alpha=64,
        target_modules="all-linear",
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    vram = round(torch.cuda.memory_allocated() / 1e9, 2)
    print(f"VRAM after loading: {vram} GB")

    # Baseline evaluation before training
    print("\nBaseline evaluation (before GRPO training):")
    test_ds = load_gsm8k("test")
    base_metrics, base_results = evaluate_gsm8k(model, tokenizer, test_ds, n=50)
    print_metrics("Base model (Qwen2.5-7B-Instruct)", base_metrics)

    # Prepare training data
    train_ds = load_gsm8k("train").map(format_for_grpo)

    output_dir = str(CHECKPOINT_DIR / "grpo_qwen_gsm8k")
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[reward_correctness, reward_format],
        args=GRPOConfig(
            output_dir=output_dir,
            num_generations=8,           # group size: generate 8 per prompt
            max_prompt_length=256,
            max_completion_length=512,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            max_steps=max_steps,
            learning_rate=5e-6,
            bf16=True,
            logging_steps=25,
            save_steps=max(100, max_steps // 5),
            report_to="none",
            temperature=0.9,
        ),
        train_dataset=train_ds,
    )

    # Periodic generation probe to watch for <think> emergence
    probe_prompts = [
        "Janet has 3 apples. She eats 1 and buys 4 more. How many does she have?",
        "A train travels 60 mph for 2 hours. How far does it go?",
    ]

    print("\nStarting GRPO training...")
    print("Watch the 'Has <think>' metric — reasoning should emerge during training.\n")

    t_start = time.time()
    trainer.train()
    elapsed = time.time() - t_start
    print(f"\nTraining complete in {elapsed/3600:.1f} hours")

    # Probe outputs after training
    print("\nPost-training generation sample:")
    model.eval()
    for q in probe_prompts:
        inputs = tokenizer(
            f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{q}\n<|assistant|>\n",
            return_tensors="pt",
        ).to("cuda")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=256, do_sample=True, temperature=0.6)
        completion = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)
        print(f"\n  Q: {q}")
        print(f"  A: {completion[:300]}")

    # Final evaluation
    print("\nFinal evaluation (after GRPO training):")
    post_metrics, post_results = evaluate_gsm8k(model, tokenizer, test_ds, n=50)
    print_metrics("GRPO-trained model", post_metrics)

    # Summary
    summary = {
        "model": MODEL_ID,
        "max_steps": max_steps,
        "training_hours": round(elapsed / 3600, 2),
        "before": base_metrics,
        "after": post_metrics,
        "accuracy_gain": round(post_metrics["accuracy"] - base_metrics["accuracy"], 3),
        "think_emergence": post_metrics["pct_with_think"],
    }
    out = RESULTS_DIR / "day07_grpo_results.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved → {out}")
    print(f"Accuracy: {base_metrics['accuracy']:.1%} → {post_metrics['accuracy']:.1%}  "
          f"(+{summary['accuracy_gain']:.1%})")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--eval_only", action="store_true")
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--max_steps", type=int, default=DEFAULT_STEPS)
    args = parser.parse_args()

    if args.eval_only:
        model_path = args.checkpoint or MODEL_ID
        print(f"Evaluating: {model_path}")
        if args.checkpoint:
            model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.bfloat16, device_map="auto")
            tokenizer = AutoTokenizer.from_pretrained(model_path)
        else:
            model, tokenizer = FastLanguageModel.from_pretrained(MODEL_ID, max_seq_length=MAX_SEQ_LEN, load_in_4bit=True)
        test_ds = load_gsm8k("test")
        metrics, _ = evaluate_gsm8k(model, tokenizer, test_ds, n=50)
        print_metrics(model_path, metrics)
    elif args.train:
        train(max_steps=args.max_steps)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
