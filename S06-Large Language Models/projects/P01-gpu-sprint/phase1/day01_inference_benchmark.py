"""
Day 1 — Inference Benchmark
Goal: measure VRAM and tokens/sec for different models and precisions.
Ollama steps (run manually in terminal before this script):
    ollama pull llama3.3:70b-instruct-q4_K_M
    ollama pull llama3.2:7b
    ollama pull qwen3:32b
    ollama run llama3.3:70b-instruct-q4_K_M "Explain the difference between attention and FFN layers in a transformer."
This script handles the HuggingFace side: load at fp16 / 4-bit / 8-bit, measure VRAM and speed.
"""

import json
import time
from datetime import datetime
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

PROMPT = "Explain the difference between attention and FFN layers in a transformer. Be detailed."
MAX_NEW_TOKENS = 150

# Edit this list to control which experiments run.
# Comment out large models until you have HuggingFace access approved.
EXPERIMENTS = [
    ("Qwen/Qwen2.5-7B-Instruct", "fp16"),
    ("Qwen/Qwen2.5-7B-Instruct", "4bit"),
    ("Qwen/Qwen2.5-7B-Instruct", "8bit"),
    # ("Qwen/Qwen2.5-32B-Instruct",           "4bit"),
    # ("meta-llama/Meta-Llama-3.3-70B-Instruct", "4bit"),  # needs HF gated access
    # ("meta-llama/Meta-Llama-3.3-70B-Instruct", "8bit"),
]


def vram_allocated_gb() -> float:
    return torch.cuda.memory_allocated() / 1e9


def peak_vram_gb() -> float:
    return torch.cuda.max_memory_allocated() / 1e9


def make_bnb_config(precision: str) -> BitsAndBytesConfig | None:
    if precision == "4bit":
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    if precision == "8bit":
        return BitsAndBytesConfig(load_in_8bit=True)
    return None


def run_experiment(model_id: str, precision: str) -> dict:
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    print(f"\n{'='*60}")
    print(f"  {model_id.split('/')[-1]}  |  {precision}")

    load_kwargs: dict = {"device_map": "auto"}
    bnb = make_bnb_config(precision)
    if bnb:
        load_kwargs["quantization_config"] = bnb
    else:
        load_kwargs["torch_dtype"] = torch.float16

    t_load = time.time()
    model = AutoModelForCausalLM.from_pretrained(model_id, **load_kwargs)
    model.eval()
    load_time = time.time() - t_load

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    vram_loaded = vram_allocated_gb()
    print(f"  Loaded in {load_time:.1f}s  |  VRAM: {vram_loaded:.2f} GB")

    inputs = tokenizer(PROMPT, return_tensors="pt").to("cuda")

    # warm-up (not timed)
    with torch.no_grad():
        _ = model.generate(**inputs, max_new_tokens=10, do_sample=False)

    # timed run
    torch.cuda.synchronize()
    t0 = time.time()
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    torch.cuda.synchronize()
    elapsed = time.time() - t0

    new_tokens = output.shape[1] - inputs["input_ids"].shape[1]
    tps = new_tokens / elapsed
    response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    print(f"  {tps:.1f} tokens/sec  |  peak VRAM: {peak_vram_gb():.2f} GB")
    print(f"  Response: {response[:120].strip()}...")

    result = {
        "model_id": model_id,
        "model_name": model_id.split("/")[-1],
        "precision": precision,
        "vram_after_load_gb": round(vram_loaded, 2),
        "peak_vram_gb": round(peak_vram_gb(), 2),
        "tokens_per_sec": round(tps, 1),
        "new_tokens": new_tokens,
        "elapsed_sec": round(elapsed, 2),
        "load_time_sec": round(load_time, 1),
        "response_preview": response[:300],
    }

    del model
    torch.cuda.empty_cache()
    return result


def print_summary(results: list[dict]) -> None:
    print(f"\n{'─'*75}")
    print(f"  {'Model':<35} {'Prec':<6} {'VRAM (GB)':<12} {'Tokens/sec'}")
    for r in results:
        if "error" in r:
            print(f"  {'ERROR':<35} {r['precision']:<6}  —  {r['error'][:30]}")
        else:
            print(f"  {r['model_name']:<35} {r['precision']:<6} {r['peak_vram_gb']:<12} {r['tokens_per_sec']}")


def main() -> None:
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print(f"PyTorch: {torch.__version__}\n")

    results = []
    for model_id, precision in EXPERIMENTS:
        try:
            results.append(run_experiment(model_id, precision))
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append({"model_id": model_id, "precision": precision, "error": str(e)})

    print_summary(results)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"day01_{stamp}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")


if __name__ == "__main__":
    main()
