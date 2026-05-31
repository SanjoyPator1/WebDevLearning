"""
Day 12 — Fast Inference: vLLM, Speculative Decoding, KV Cache

Benchmark:
  1. HuggingFace generate() — naive baseline
  2. vLLM single request
  3. vLLM concurrent requests (1, 5, 10, 20)
  4. vLLM + speculative decoding

Run:
    python day12_inference_optimization.py --baseline      # HF generate benchmark
    python day12_inference_optimization.py --vllm          # vLLM benchmark (server must be running)
    python day12_inference_optimization.py --speculative   # speculative decoding (separate server needed)
    python day12_inference_optimization.py --all           # full comparison

Start vLLM servers first (in separate terminals):
    # Standard server
    python -m vllm.entrypoints.openai.api_server \
        --model Qwen/Qwen2.5-7B-Instruct \
        --port 8000 \
        --gpu-memory-utilization 0.85

    # Speculative decoding server (uses a small draft model)
    python -m vllm.entrypoints.openai.api_server \
        --model Qwen/Qwen2.5-7B-Instruct \
        --port 8001 \
        --speculative-model Qwen/Qwen2.5-0.5B-Instruct \
        --num-speculative-tokens 5 \
        --gpu-memory-utilization 0.90
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
VLLM_URL = "http://localhost:8000/v1"
VLLM_SPEC_URL = "http://localhost:8001/v1"
MAX_NEW_TOKENS = 200

PROMPTS = [
    "Explain how neural networks learn from data.",
    "What is the difference between supervised and unsupervised learning?",
    "Describe how transformers revolutionized NLP.",
    "What are the key challenges in training large language models?",
    "How does attention mechanism work in transformers?",
    "Explain gradient descent in simple terms.",
    "What is overfitting and how do you prevent it?",
    "Describe the architecture of a typical LLM.",
    "What is the role of tokenization in language models?",
    "How does RLHF improve language model alignment?",
    "What is transfer learning and why is it effective?",
    "Explain the concept of embeddings in NLP.",
    "What are the key differences between GPT and BERT?",
    "How does RAG improve LLM factual accuracy?",
    "What is quantization and why does it matter for deployment?",
    "Explain the concept of in-context learning.",
    "What are LoRA and PEFT in the context of fine-tuning?",
    "How do chain-of-thought prompts improve reasoning?",
    "What is speculative decoding and how does it speed up inference?",
    "Explain PagedAttention and why it improves LLM serving.",
]


# Benchmark 1: HuggingFace generate()

def benchmark_hf(n_requests: int = 10) -> dict:
    print(f"\nHuggingFace generate() — {n_requests} sequential requests")
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16, device_map="auto")
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    # warm-up
    inputs = tokenizer(PROMPTS[0], return_tensors="pt").to("cuda")
    with torch.no_grad():
        _ = model.generate(**inputs, max_new_tokens=10)

    torch.cuda.synchronize()
    t0 = time.time()
    total_tokens = 0
    for prompt in PROMPTS[:n_requests]:
        inputs = tokenizer(prompt, return_tensors="pt", max_length=200, truncation=True).to("cuda")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
        total_tokens += out.shape[1] - inputs["input_ids"].shape[1]
    torch.cuda.synchronize()
    elapsed = time.time() - t0

    result = {
        "method": "hf_generate",
        "n_requests": n_requests,
        "total_tokens": total_tokens,
        "elapsed_sec": round(elapsed, 2),
        "requests_per_sec": round(n_requests / elapsed, 2),
        "tokens_per_sec": round(total_tokens / elapsed, 1),
    }
    print(f"  {n_requests} requests in {elapsed:.1f}s  |  {result['requests_per_sec']} req/s  |  {result['tokens_per_sec']} tok/s")

    del model
    torch.cuda.empty_cache()
    return result


# Benchmark 2 & 3: vLLM (single + concurrent)

async def send_request_async(client, prompt: str, port_url: str) -> dict:
    t0 = asyncio.get_event_loop().time()
    response = await client.completions.create(
        model=MODEL_ID,
        prompt=prompt,
        max_tokens=MAX_NEW_TOKENS,
        temperature=0,
    )
    elapsed = asyncio.get_event_loop().time() - t0
    tokens = response.usage.completion_tokens
    return {"tokens": tokens, "elapsed": elapsed}


async def benchmark_vllm_concurrent(n_requests: int, port_url: str) -> dict:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return {"error": "pip install openai"}

    client = AsyncOpenAI(base_url=port_url, api_key="dummy")
    prompts = (PROMPTS * 10)[:n_requests]

    t0 = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[send_request_async(client, p, port_url) for p in prompts])
    elapsed = asyncio.get_event_loop().time() - t0

    total_tokens = sum(r["tokens"] for r in results)
    return {
        "n_requests": n_requests,
        "elapsed_sec": round(elapsed, 2),
        "requests_per_sec": round(n_requests / elapsed, 2),
        "tokens_per_sec": round(total_tokens / elapsed, 1),
    }


def benchmark_vllm(url: str = VLLM_URL) -> list[dict]:
    label = "vllm_standard" if url == VLLM_URL else "vllm_speculative"
    print(f"\nvLLM concurrent benchmark ({label}) at {url}")
    results = []
    for n in [1, 5, 10, 20]:
        r = asyncio.run(benchmark_vllm_concurrent(n, url))
        r["method"] = f"{label}_{n}_concurrent"
        print(f"  {n:2d} concurrent: {r['requests_per_sec']} req/s  |  {r['tokens_per_sec']} tok/s  |  {r['elapsed_sec']}s")
        results.append(r)
    return results


# Print summary

def print_summary(all_results: list[dict]) -> None:
    print(f"\n{'─'*65}")
    print(f"  {'Method':<35} {'Req/s':<10} {'Tok/s':<12} {'Elapsed'}")
    for r in all_results:
        if "error" not in r:
            print(f"  {r.get('method',''):<35} {r.get('requests_per_sec','—'):<10} {r.get('tokens_per_sec','—'):<12} {r.get('elapsed_sec','—')}s")
    print("\nKey insight: vLLM throughput should grow near-linearly with concurrent requests")
    print("up to the memory limit, because continuous batching fills idle GPU cycles.")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--vllm", action="store_true")
    parser.add_argument("--speculative", action="store_true")
    parser.add_argument("--all", dest="run_all", action="store_true")
    args = parser.parse_args()

    all_results = []

    if args.run_all or args.baseline:
        all_results.append(benchmark_hf(n_requests=10))

    if args.run_all or args.vllm:
        vllm_results = benchmark_vllm(VLLM_URL)
        all_results.extend(vllm_results)

    if args.run_all or args.speculative:
        spec_results = benchmark_vllm(VLLM_SPEC_URL)
        for r in spec_results:
            r["method"] = r["method"].replace("vllm_standard", "vllm_speculative")
        all_results.extend(spec_results)

    if all_results:
        print_summary(all_results)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"day12_benchmark_{stamp}.json"
        out.write_text(json.dumps(all_results, indent=2))
        print(f"\nResults saved → {out}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
