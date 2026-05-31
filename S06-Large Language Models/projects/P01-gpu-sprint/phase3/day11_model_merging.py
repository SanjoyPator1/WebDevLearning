"""
Day 11 — Model Merging (SLERP, TIES, DARE)
Uses mergekit to combine two fine-tuned checkpoints from Days 4-5.

Merging requires NO training — it runs on CPU and takes minutes.

Run:
    python day11_model_merging.py --setup        # print mergekit install instructions
    python day11_model_merging.py --merge slerp  # SLERP merge
    python day11_model_merging.py --merge ties   # TIES merge
    python day11_model_merging.py --merge dare   # DARE merge
    python day11_model_merging.py --merge all    # all three in sequence
    python day11_model_merging.py --eval         # evaluate all merged models
"""

import argparse
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
MERGE_DIR = Path(__file__).parent / "checkpoints" / "day11"
RESULTS_DIR.mkdir(exist_ok=True)
MERGE_DIR.mkdir(parents=True, exist_ok=True)

BASE_MODEL = "mistralai/Mistral-7B-v0.1"

# Points to your Day 4 (instruction) and Day 5 (domain) checkpoints
MODEL_A = str(CHECKPOINT_DIR / "day04" / "mistral-7b-lora-merged")      # instruction following
MODEL_B = str(CHECKPOINT_DIR / "day05" / "qlora_code" / "checkpoint-500")  # domain (code)

EVAL_TASKS = {
    "instruction": [
        "Explain what photosynthesis is in simple terms.",
        "Write a short poem about the ocean.",
        "What are three tips for better sleep?",
    ],
    "domain_code": [
        "Write a Python function to reverse a string.",
        "What is the difference between a list and a tuple in Python?",
        "How do you handle exceptions in Python?",
    ],
}


# Config generation

def slerp_config(model_a: str, model_b: str, t: float = 0.5) -> str:
    return textwrap.dedent(f"""
    models:
      - model: {model_a}
        parameters:
          weight: {1 - t}
      - model: {model_b}
        parameters:
          weight: {t}
    merge_method: slerp
    base_model: {BASE_MODEL}
    parameters:
      t: {t}
    dtype: bfloat16
    """).strip()


def ties_config(model_a: str, model_b: str, density: float = 0.5) -> str:
    return textwrap.dedent(f"""
    models:
      - model: {model_a}
        parameters:
          density: {density}
          weight: 1.0
      - model: {model_b}
        parameters:
          density: {density}
          weight: 1.0
    merge_method: ties
    base_model: {BASE_MODEL}
    parameters:
      normalize: true
    dtype: bfloat16
    """).strip()


def dare_config(model_a: str, model_b: str, density: float = 0.5) -> str:
    return textwrap.dedent(f"""
    models:
      - model: {model_a}
        parameters:
          density: {density}
          weight: 1.0
      - model: {model_b}
        parameters:
          density: {density}
          weight: 1.0
    merge_method: dare_ties
    base_model: {BASE_MODEL}
    parameters:
      normalize: true
      rescale: true
    dtype: bfloat16
    """).strip()


# Merge runner

def run_merge(method: str, model_a: str, model_b: str) -> Path | None:
    out_dir = MERGE_DIR / f"merged_{method}"

    if out_dir.exists():
        print(f"  {method} merged model already exists at {out_dir}. Skipping merge.")
        return out_dir

    config_map = {"slerp": slerp_config, "ties": ties_config, "dare": dare_config}
    config_text = config_map[method](model_a, model_b)
    config_path = MERGE_DIR / f"{method}_config.yaml"
    config_path.write_text(config_text)
    print(f"  Config written → {config_path}")
    print(f"  Config contents:\n{config_text}\n")

    if not Path(model_a).exists() or not Path(model_b).exists():
        print(f"\n  WARNING: Checkpoint paths not found.")
        print(f"    Model A: {model_a}  exists={Path(model_a).exists()}")
        print(f"    Model B: {model_b}  exists={Path(model_b).exists()}")
        print("  Update MODEL_A and MODEL_B at the top of this file to point to your actual checkpoints.")
        print("  Using HuggingFace model IDs as fallback for demo...")
        config_text = config_map[method]("mistralai/Mistral-7B-Instruct-v0.2", "mistralai/Mistral-7B-v0.1")
        config_path.write_text(config_text)

    print(f"  Running mergekit ({method})...")
    result = subprocess.run(
        [sys.executable, "-m", "mergekit.scripts.mergekit_yaml", str(config_path), str(out_dir)],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"  mergekit failed:\n{result.stderr[-500:]}")
        print("\n  Alternative: run manually:")
        print(f"    mergekit-yaml {config_path} {out_dir}")
        return None

    print(f"  Merged model saved → {out_dir}")
    return out_dir


# Evaluation

@torch.no_grad()
def evaluate_model(model_path: str, label: str) -> dict:
    print(f"\n  Evaluating: {label}")
    try:
        model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.bfloat16, device_map="auto")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model.eval()
    except Exception as e:
        print(f"  Failed to load: {e}")
        return {"label": label, "error": str(e)}

    task_results = {}
    for task_name, prompts in EVAL_TASKS.items():
        responses = []
        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt", max_length=200).to("cuda")
            out = model.generate(**inputs, max_new_tokens=100, do_sample=False)
            resp = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            responses.append({"prompt": prompt, "response": resp[:200]})
            print(f"    [{task_name}] {prompt[:60]}")
            print(f"             → {resp[:100].strip()}")
        task_results[task_name] = responses

    del model
    torch.cuda.empty_cache()
    return {"label": label, "tasks": task_results}


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--merge", choices=["slerp", "ties", "dare", "all"])
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()

    if args.setup:
        print("""
Install mergekit:
    pip install mergekit

Or from source (more up-to-date):
    git clone https://github.com/arcee-ai/mergekit && cd mergekit
    pip install -e .

After merging, models are saved as full HuggingFace models (no adapters needed).
Merging runs on CPU and takes ~5-15 minutes per method for 7B models.
        """)
        return

    if args.merge:
        methods = ["slerp", "ties", "dare"] if args.merge == "all" else [args.merge]
        for method in methods:
            print(f"\n{'='*60}")
            print(f"  Merging: {method.upper()}")
            run_merge(method, MODEL_A, MODEL_B)

    if args.eval:
        print("\nEvaluating all checkpoints...")
        models_to_eval = {
            "Model A (instruction)": MODEL_A,
            "Model B (domain)": MODEL_B,
            "SLERP merged": str(MERGE_DIR / "merged_slerp"),
            "TIES merged": str(MERGE_DIR / "merged_ties"),
            "DARE merged": str(MERGE_DIR / "merged_dare"),
        }

        all_results = []
        for label, path in models_to_eval.items():
            if Path(path).exists():
                result = evaluate_model(path, label)
                all_results.append(result)
            else:
                print(f"\n  Skipping {label}: not found at {path}")

        out = RESULTS_DIR / "day11_merge_eval.json"
        out.write_text(json.dumps(all_results, indent=2))
        print(f"\nResults saved → {out}")
        print("\nKey question: does each merged model score better than average on both tasks,")
        print("or does it sacrifice one domain for the other?")


if __name__ == "__main__":
    main()
