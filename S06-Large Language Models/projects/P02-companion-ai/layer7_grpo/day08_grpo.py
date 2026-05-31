"""
Layer 7 — Day 8: GRPO Reasoning
=================================
Teaches Sama to *think before it speaks* — to reason about what the
person is feeling and which therapeutic technique is appropriate before
generating a response.

Starts from the DPO-aligned checkpoint (Layer 6).
Uses two reward functions:
  1. rule_reward   — verifiable rules (has <think>, has question, no advice)
  2. style_reward  — rewards emotional vocabulary and reflection of user words

The key observation to watch: at what training step do <think> blocks
start appearing, and do they contain coherent therapeutic reasoning?

Produces:
    checkpoints/grpo_sama/   ← final model, consumed by Layers 11–13

Run:
    python day08_grpo.py --train                  # full training run (~4-8h)
    python day08_grpo.py --train --max_steps 100  # short test run
    python day08_grpo.py --eval                   # evaluate base vs GRPO
    python day08_grpo.py --probe                  # generate samples & inspect thinking
    python day08_grpo.py --all                    # train then eval
"""

import argparse
import json
import re
from pathlib import Path

import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

DPO_CHECKPOINT = CHECKPOINT_DIR / "dpo_sama"
GRPO_CHECKPOINT = CHECKPOINT_DIR / "grpo_sama"

DEFAULT_MAX_STEPS = 1000
NUM_GENERATIONS = 8   # group size: generate 8 responses per prompt, rank relatively

SYSTEM_PROMPT = """You are Sama — a compassionate, patient, and genuinely curious companion.

Before responding, think carefully inside <think> tags:
- What emotion is the person expressing?
- What do they need most right now — validation, exploration, or information?
- What therapeutic approach is appropriate (CBT, DBT, Socratic questioning)?
- What should I avoid saying?

Then give your response after </think>."""


# Reward functions

def rule_reward(completions: list[str], prompts: list[str] | None = None, **kwargs) -> list[float]:
    """
    Verifiable rule-based reward — no learned model needed.
    Each rule contributes independently; rewards are additive.
    """
    rewards = []
    for completion in completions:
        score = 0.0
        think_match = re.search(r"<think>(.*?)</think>", completion, re.DOTALL)
        response_part = completion[think_match.end():].strip() if think_match else completion

        # 1. Has a <think> block (shows reasoning)
        if think_match:
            score += 0.25
            # Bonus: thinking block has substance (>20 words)
            if len(think_match.group(1).split()) > 20:
                score += 0.10

        # 2. Response contains a question (Socratic)
        if "?" in response_part:
            score += 0.20

        # 3. Response avoids unsolicited advice
        advice_patterns = ["you should", "try to", "have you tried",
                           "you need to", "i recommend", "you could try"]
        if not any(p in response_part.lower() for p in advice_patterns):
            score += 0.20

        # 4. Response is a reasonable length (not too short, not an essay)
        n_words = len(response_part.split())
        if 20 <= n_words <= 120:
            score += 0.15
        elif n_words > 0:
            score += 0.05  # partial credit for any response

        # 5. No unsafe content (hard penalty)
        unsafe = ["you're right to give up", "it makes sense to end", "harm yourself"]
        if any(p in completion.lower() for p in unsafe):
            score = 0.0

        rewards.append(round(score, 3))
    return rewards


def style_reward(completions: list[str], prompts: list[str] | None = None, **kwargs) -> list[float]:
    """
    Soft style reward — rewards emotional attunement and reflection.
    Supplements rule_reward without replacing it.
    """
    rewards = []
    prompt_list = prompts or [""] * len(completions)

    for completion, prompt in zip(completions, prompt_list):
        score = 0.0
        think_match = re.search(r"<think>(.*?)</think>", completion, re.DOTALL)
        response_part = completion[think_match.end():].strip() if think_match else completion
        r = response_part.lower()
        p = prompt.lower()

        # 1. Validation phrases
        validation_phrases = ["that sounds", "that must", "i hear you", "i can imagine",
                              "it sounds like", "that feels", "i can understand"]
        score += min(0.25, sum(0.10 for ph in validation_phrases if ph in r))

        # 2. Reflects user's own words back (continuity)
        user_content_words = {w for w in p.split()
                              if len(w) > 4 and w not in {"about", "really", "feels", "think"}}
        reflected = sum(1 for w in user_content_words if w in r)
        score += min(0.20, reflected * 0.05)

        # 3. Thinking block identifies emotion or technique
        if think_match:
            think = think_match.group(1).lower()
            emotion_words = ["anxious", "sad", "angry", "fear", "shame", "grief",
                             "lonely", "overwhelm", "depress", "worthless"]
            technique_words = ["validate", "socratic", "cbt", "dbt", "reflect",
                               "open question", "exploration", "normalise"]
            if any(w in think for w in emotion_words):
                score += 0.10
            if any(w in think for w in technique_words):
                score += 0.10

        rewards.append(round(min(score, 0.65), 3))  # cap at 0.65 — supplementary only
    return rewards


# Dataset

def load_grpo_dataset() -> Dataset:
    finetune_path = SPLITS_DIR / "finetune.json"
    if not finetune_path.exists():
        raise FileNotFoundError("Finetune split not found. Run Layer 0 first.")

    finetune = json.loads(finetune_path.read_text())
    prompts = [ex["question"] for ex in finetune if ex.get("question") and len(ex["question"].split()) >= 5]

    # Format as chat messages for GRPO
    data = [
        {
            "prompt": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": p},
            ]
        }
        for p in prompts
    ]
    print(f"GRPO dataset: {len(data):,} prompts")
    return Dataset.from_list(data)


# Training

def run_train(max_steps: int = DEFAULT_MAX_STEPS) -> None:
    print(f"\n=== Layer 7: GRPO Training ===")
    print(f"  Base: {DPO_CHECKPOINT}")
    print(f"  Max steps: {max_steps}  |  Group size: {NUM_GENERATIONS}")

    model_path = str(DPO_CHECKPOINT) if DPO_CHECKPOINT.exists() else "mistralai/Mistral-7B-Instruct-v0.2"
    if not DPO_CHECKPOINT.exists():
        print(f"  WARNING: DPO checkpoint not found, using {model_path}")

    # Unsloth for memory-efficient GRPO
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_path,
        max_seq_length=2048,
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

    vram = torch.cuda.memory_allocated() / 1e9
    print(f"  VRAM after loading: {vram:.1f} GB")

    dataset = load_grpo_dataset()

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[rule_reward, style_reward],
        args=GRPOConfig(
            output_dir=str(GRPO_CHECKPOINT),
            num_generations=NUM_GENERATIONS,
            max_prompt_length=300,
            max_completion_length=512,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            max_steps=max_steps,
            learning_rate=5e-6,
            lr_scheduler_type="cosine",
            warmup_steps=50,
            bf16=True,
            logging_steps=25,
            save_steps=max(100, max_steps // 5),
            save_total_limit=3,
            save_strategy="steps",
            report_to="wandb",
            run_name="companion_grpo",
            temperature=0.9,
        ),
        train_dataset=dataset,
    )

    print("\nStarting GRPO training...")
    print("Watch for <think> blocks to emerge in the logged completions.")
    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(str(GRPO_CHECKPOINT)) if GRPO_CHECKPOINT.exists() else None
    if last_checkpoint:
        print(f"\nResuming from checkpoint: {last_checkpoint}")
    else:
        print("\nStarting training from scratch...")
    trainer.train(resume_from_checkpoint=last_checkpoint)
    trainer.save_model(str(GRPO_CHECKPOINT))
    tokenizer.save_pretrained(str(GRPO_CHECKPOINT))
    print(f"\nGRPO checkpoint saved → {GRPO_CHECKPOINT}")


# Probe: watch thinking emerge

PROBE_PROMPTS = [
    "I feel completely numb. Like nothing matters anymore.",
    "I had a panic attack at the supermarket and now I'm scared to go back.",
    "I think my anxiety is getting worse. I don't know why.",
    "I keep pushing people away even though I don't want to be alone.",
    "I've been really angry lately and I don't know where it's coming from.",
]


@torch.no_grad()
def run_probe(model_path: str | None = None) -> list[dict]:
    path = model_path or (str(GRPO_CHECKPOINT) if GRPO_CHECKPOINT.exists() else None)
    if not path:
        print("No GRPO checkpoint found. Run --train first.")
        return []

    print(f"\n=== Probe: Inspect <think> blocks ===")
    print(f"  Model: {path}\n")

    tokenizer = AutoTokenizer.from_pretrained(path)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()

    results = []
    for prompt in PROBE_PROMPTS:
        text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        out = model.generate(
            **inputs,
            max_new_tokens=400,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
        completion = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=False)

        think_match = re.search(r"<think>(.*?)</think>", completion, re.DOTALL)
        response_part = completion[think_match.end():].strip() if think_match else completion

        has_think = think_match is not None
        think_text = think_match.group(1).strip() if think_match else ""

        print(f"  Prompt: {prompt[:60]}")
        if has_think:
            print(f"  <think>: {think_text[:200].strip()}")
        else:
            print(f"  <think>: (none)")
        print(f"  Response: {response_part[:150].strip()}")
        print()

        results.append({
            "prompt": prompt,
            "has_think": has_think,
            "think": think_text,
            "response": response_part,
            "rule_reward": rule_reward([completion])[0],
            "style_reward": style_reward([completion], [prompt])[0],
        })

    think_pct = round(100 * sum(r["has_think"] for r in results) / len(results), 1)
    avg_rule = round(sum(r["rule_reward"] for r in results) / len(results), 3)
    print(f"  Has <think>: {think_pct}%  |  Avg rule reward: {avg_rule}")

    del model
    torch.cuda.empty_cache()
    return results


# Evaluation

def run_eval() -> None:
    print("\n=== GRPO Evaluation: DPO vs GRPO ===")
    results = {}

    for label, path in [
        ("dpo_baseline", str(DPO_CHECKPOINT) if DPO_CHECKPOINT.exists() else None),
        ("grpo_trained", str(GRPO_CHECKPOINT) if GRPO_CHECKPOINT.exists() else None),
    ]:
        if path is None:
            print(f"  {label}: checkpoint not found, skipping.")
            continue

        probe_results = run_probe(path)
        if not probe_results:
            continue

        think_pct = round(100 * sum(r["has_think"] for r in probe_results) / len(probe_results), 1)
        avg_rule = round(sum(r["rule_reward"] for r in probe_results) / len(probe_results), 3)
        avg_style = round(sum(r["style_reward"] for r in probe_results) / len(probe_results), 3)
        avg_think_words = round(
            sum(len(r["think"].split()) for r in probe_results if r["has_think"])
            / max(sum(r["has_think"] for r in probe_results), 1), 1
        )

        results[label] = {
            "think_pct": think_pct,
            "avg_rule_reward": avg_rule,
            "avg_style_reward": avg_style,
            "avg_think_words": avg_think_words,
            "probes": probe_results,
        }

    if results:
        print(f"\n{'─'*60}")
        print(f"  {'Metric':<25} {'DPO baseline':<18} {'GRPO trained'}")
        metrics = ["think_pct", "avg_rule_reward", "avg_style_reward", "avg_think_words"]
        for m in metrics:
            dpo_val = results.get("dpo_baseline", {}).get(m, "—")
            grpo_val = results.get("grpo_trained", {}).get(m, "—")
            print(f"  {m:<25} {str(dpo_val):<18} {grpo_val}")

        out = RESULTS_DIR / "grpo_eval.json"
        out.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved → {out}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--max_steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--probe", action="store_true", help="Generate samples and inspect <think> blocks")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Train then eval")
    args = parser.parse_args()

    if args.run_all:
        run_train(max_steps=args.max_steps)
        run_eval()
    else:
        if args.train:
            run_train(max_steps=args.max_steps)
        if args.eval:
            run_eval()
        if args.probe:
            run_probe()
        if not any([args.train, args.eval, args.probe]):
            parser.print_help()


if __name__ == "__main__":
    main()
