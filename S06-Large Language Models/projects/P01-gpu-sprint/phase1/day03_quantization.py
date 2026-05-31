"""
Day 3 — Quantization Deep Dive
Compares: fp16 baseline | GPTQ 4-bit | AWQ 4-bit | NF4 double-quant
Metric: perplexity on wikitext-2, VRAM, tokens/sec, model size on disk.

Run:
    python day03_quantization.py --method all
    python day03_quantization.py --method fp16
    python day03_quantization.py --method gptq
    python day03_quantization.py --method awq
    python day03_quantization.py --method nf4

Note on GGUF:
    GGUF quantization is done via llama.cpp outside Python.
    After running this script, see the gguf_instructions() output for steps.
"""

import argparse
import json
import math
import time
from datetime import datetime
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "mistralai/Mistral-7B-v0.1"

RESULTS_DIR = Path(__file__).parent / "results"
QUANT_DIR = Path(__file__).parent / "checkpoints" / "day03"
RESULTS_DIR.mkdir(exist_ok=True)
QUANT_DIR.mkdir(parents=True, exist_ok=True)


# Perplexity

def compute_perplexity(model, tokenizer, n_tokens: int = 4096, stride: int = 512) -> float:
    """
    Standard sliding-window perplexity on wikitext-2-raw-v1 test split.
    Lower = better.
    """
    print("  Computing perplexity on wikitext-2...")
    ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    text = "\n\n".join(ds["text"])

    encodings = tokenizer(text, return_tensors="pt")
    input_ids = encodings.input_ids[:, :n_tokens].to("cuda")
    seq_len = input_ids.size(1)
    block_size = min(model.config.max_position_embeddings if hasattr(model.config, "max_position_embeddings") else 2048, 2048)

    nlls = []
    prev_end = 0
    for begin in range(0, seq_len, stride):
        end = min(begin + block_size, seq_len)
        target_len = end - prev_end

        with torch.no_grad():
            out = model(input_ids[:, begin:end], labels=input_ids[:, begin:end])
        # only count the non-overlapping part
        nll = out.loss * target_len
        nlls.append(nll)
        prev_end = end
        if end == seq_len:
            break

    ppl = math.exp(torch.stack(nlls).sum() / seq_len)
    return round(ppl, 3)


# Speed benchmark

def benchmark_speed(model, tokenizer, max_new_tokens: int = 100) -> float:
    prompt = "Artificial intelligence is transforming the world because"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    # warm-up
    with torch.no_grad():
        _ = model.generate(**inputs, max_new_tokens=10, do_sample=False)

    torch.cuda.synchronize()
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    torch.cuda.synchronize()
    elapsed = time.time() - t0

    new_tokens = out.shape[1] - inputs["input_ids"].shape[1]
    return round(new_tokens / elapsed, 1)


def model_size_gb(path: str | Path) -> float:
    p = Path(path)
    if not p.exists():
        return -1.0
    total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return round(total / 1e9, 2)


def vram_gb() -> float:
    return round(torch.cuda.memory_allocated() / 1e9, 2)


def peak_vram_gb() -> float:
    return round(torch.cuda.max_memory_allocated() / 1e9, 2)


# Experiments

def run_fp16(tokenizer) -> dict:
    print("\n[1/4] fp16 baseline")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16, device_map="auto")
    model.eval()

    ppl = compute_perplexity(model, tokenizer)
    tps = benchmark_speed(model, tokenizer)
    vram = peak_vram_gb()

    print(f"  perplexity={ppl}  |  {tps} tok/s  |  VRAM {vram} GB")
    del model
    torch.cuda.empty_cache()
    return {"method": "fp16", "perplexity": ppl, "tokens_per_sec": tps, "peak_vram_gb": vram}


def run_gptq(tokenizer) -> dict:
    print("\n[2/4] GPTQ 4-bit")
    try:
        from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
    except ImportError:
        print("  auto-gptq not installed. Run: pip install auto-gptq")
        return {"method": "gptq", "error": "auto-gptq not installed"}

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    quant_config = BaseQuantizeConfig(bits=4, group_size=128, desc_act=False)

    print("  Loading model for GPTQ calibration...")
    model = AutoGPTQForCausalLM.from_pretrained(MODEL_ID, quant_config)

    # 128 calibration samples from wikitext-2
    ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="train")
    cal_text = "\n\n".join(ds["text"][:200])
    cal_ids = tokenizer(cal_text, return_tensors="pt").input_ids
    examples = [{"input_ids": cal_ids[:, i:i+512]} for i in range(0, min(cal_ids.shape[1] - 512, 512 * 128), 512)][:128]

    print(f"  Quantizing with {len(examples)} calibration samples...")
    model.quantize(examples)

    save_path = QUANT_DIR / "mistral-gptq-4bit"
    model.save_quantized(str(save_path))
    size = model_size_gb(save_path)
    print(f"  Saved ({size} GB) → {save_path}")

    ppl = compute_perplexity(model, tokenizer)
    tps = benchmark_speed(model, tokenizer)
    vram = peak_vram_gb()

    print(f"  perplexity={ppl}  |  {tps} tok/s  |  VRAM {vram} GB  |  disk {size} GB")
    del model
    torch.cuda.empty_cache()
    return {"method": "gptq_4bit", "perplexity": ppl, "tokens_per_sec": tps, "peak_vram_gb": vram, "disk_gb": size}


def run_awq(tokenizer) -> dict:
    print("\n[3/4] AWQ 4-bit")
    try:
        from awq import AutoAWQForCausalLM
    except ImportError:
        print("  autoawq not installed. Run: pip install autoawq")
        return {"method": "awq", "error": "autoawq not installed"}

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    model = AutoAWQForCausalLM.from_pretrained(MODEL_ID, safetensors=True)
    quant_config = {"zero_point": True, "q_group_size": 128, "w_bit": 4, "version": "GEMM"}

    print("  Quantizing with AWQ...")
    model.quantize(tokenizer, quant_config=quant_config)

    save_path = QUANT_DIR / "mistral-awq-4bit"
    model.save_quantized(str(save_path))
    tokenizer.save_pretrained(str(save_path))
    size = model_size_gb(save_path)
    print(f"  Saved ({size} GB) → {save_path}")

    ppl = compute_perplexity(model, tokenizer)
    tps = benchmark_speed(model, tokenizer)
    vram = peak_vram_gb()

    print(f"  perplexity={ppl}  |  {tps} tok/s  |  VRAM {vram} GB  |  disk {size} GB")
    del model
    torch.cuda.empty_cache()
    return {"method": "awq_4bit", "perplexity": ppl, "tokens_per_sec": tps, "peak_vram_gb": vram, "disk_gb": size}


def run_nf4(tokenizer) -> dict:
    print("\n[4/4] NF4 double quantization (bitsandbytes)")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, quantization_config=bnb_config, device_map="auto")
    model.eval()

    ppl = compute_perplexity(model, tokenizer)
    tps = benchmark_speed(model, tokenizer)
    vram = peak_vram_gb()

    print(f"  perplexity={ppl}  |  {tps} tok/s  |  VRAM {vram} GB")
    del model
    torch.cuda.empty_cache()
    return {"method": "nf4_double_quant", "perplexity": ppl, "tokens_per_sec": tps, "peak_vram_gb": vram}


# Summary

def print_summary(results: list[dict]) -> None:
    print(f"\n{'─'*70}")
    print(f"  {'Method':<22} {'Perplexity':<14} {'VRAM (GB)':<12} {'Tokens/sec':<12} {'Disk (GB)'}")
    for r in results:
        if "error" in r:
            print(f"  {r['method']:<22} ERROR: {r['error']}")
        else:
            disk = str(r.get("disk_gb", "—"))
            print(f"  {r['method']:<22} {r['perplexity']:<14} {r['peak_vram_gb']:<12} {r['tokens_per_sec']:<12} {disk}")
    print("Lower perplexity = better quality. Lower VRAM = more accessible.")


def gguf_instructions() -> None:
    print("""
─── GGUF (llama.cpp) — manual steps ──────────────────────────────────────────
After this script, convert to GGUF and measure perplexity outside Python:

  git clone https://github.com/ggerganov/llama.cpp && cd llama.cpp
  cmake -B build && cmake --build build --config Release -j
  pip install -r requirements.txt

  # Convert HF model to GGUF
  python convert_hf_to_gguf.py path/to/mistral-7b --outfile mistral-7b-f16.gguf

  # Quantize to Q4_K_M
  ./build/bin/llama-quantize mistral-7b-f16.gguf mistral-7b-q4_k_m.gguf Q4_K_M

  # Measure perplexity (download wikitext-2 test set first)
  wget https://huggingface.co/datasets/wikitext/resolve/main/wikitext-2-raw-v1/wikitext-2-raw-v1.tar.gz
  ./build/bin/llama-perplexity -m mistral-7b-q4_k_m.gguf -f wikitext-2-raw/wiki.test.raw
──────────────────────────────────────────────────────────────────────────────
""")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["fp16", "gptq", "awq", "nf4", "all"], default="all")
    args = parser.parse_args()

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print(f"Model: {MODEL_ID}\n")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    run_map = {"fp16": run_fp16, "gptq": run_gptq, "awq": run_awq, "nf4": run_nf4}
    to_run = list(run_map.keys()) if args.method == "all" else [args.method]

    results = []
    for method in to_run:
        try:
            results.append(run_map[method](tokenizer))
        except Exception as e:
            print(f"  FAILED {method}: {e}")
            results.append({"method": method, "error": str(e)})

    print_summary(results)
    gguf_instructions()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"day03_{stamp}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"Results saved → {out}")


if __name__ == "__main__":
    main()
