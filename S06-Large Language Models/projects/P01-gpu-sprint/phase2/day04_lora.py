"""
Day 4 — LoRA from Scratch, then with PEFT

Parts (run in order):
    python day04_lora.py --part scratch   # implement & verify LoRALinear
    python day04_lora.py --part ranks     # compare r=8 / r=16 / r=64 via PEFT
    python day04_lora.py --part merge     # merge best checkpoint back into base model
"""

import argparse
import json
import math
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from datasets import load_dataset
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTConfig, SFTTrainer

RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "day04"
RESULTS_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

BASE_MODEL = "mistralai/Mistral-7B-v0.1"
DATASET = "yahma/alpaca-cleaned"
MAX_STEPS = 200          # short run per rank for comparison
MAX_SEQ_LEN = 512


# Part 1: LoRALinear from scratch

class LoRALinear(nn.Module):
    """
    Drop-in replacement for nn.Linear that adds a low-rank adapter.
    Forward: h = Wx + scale * (B @ A @ x)
    Only lora_A and lora_B are trainable; weight is frozen.
    """

    def __init__(self, in_features: int, out_features: int, r: int = 8, alpha: int = 16):
        super().__init__()
        self.r = r
        self.scale = alpha / r

        self.weight = nn.Parameter(
            torch.empty(out_features, in_features), requires_grad=False
        )
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))

        # A: random init (provides diversity); B: zero init (so adapter starts as identity)
        self.lora_A = nn.Parameter(torch.randn(r, in_features) / math.sqrt(in_features))
        self.lora_B = nn.Parameter(torch.zeros(out_features, r))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        base = x @ self.weight.T
        lora = x @ self.lora_A.T @ self.lora_B.T
        return base + self.scale * lora

    def merge(self) -> nn.Linear:
        """Merge adapter into a plain Linear and return it (no VRAM overhead)."""
        merged_weight = self.weight + self.scale * (self.lora_B @ self.lora_A)
        layer = nn.Linear(self.weight.shape[1], self.weight.shape[0], bias=False)
        layer.weight = nn.Parameter(merged_weight)
        return layer


class TinyGPTWithLoRA(nn.Module):
    """Minimal 2-layer transformer with LoRALinear in Q, K, V projections."""

    def __init__(self, vocab_size: int = 1000, n_embd: int = 64, n_head: int = 4, lora_r: int = 8):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head = n_head
        self.head_dim = n_embd // n_head

        self.embed = nn.Embedding(vocab_size, n_embd)
        self.q_proj = LoRALinear(n_embd, n_embd, r=lora_r)
        self.k_proj = LoRALinear(n_embd, n_embd, r=lora_r)
        self.v_proj = LoRALinear(n_embd, n_embd, r=lora_r)
        self.out_proj = nn.Linear(n_embd, n_embd)
        self.ffn = nn.Sequential(nn.Linear(n_embd, 4 * n_embd), nn.GELU(), nn.Linear(4 * n_embd, n_embd))
        self.ln1 = nn.LayerNorm(n_embd)
        self.ln2 = nn.LayerNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T = x.shape
        h = self.embed(x)
        q = self.q_proj(self.ln1(h)).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k_proj(self.ln1(h)).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = self.v_proj(self.ln1(h)).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        attn = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        attn = attn.transpose(1, 2).contiguous().view(B, T, -1)
        h = h + self.out_proj(attn)
        h = h + self.ffn(self.ln2(h))
        return self.lm_head(h)


def part_scratch() -> None:
    print("PART 1 — LoRALinear from scratch")

    # 1a. Verify gradient flow
    print("\n[1a] Gradient flow check")
    layer = LoRALinear(512, 512, r=8, alpha=16)
    x = torch.randn(2, 512)
    out = layer(x).sum()
    out.backward()

    print(f"  weight.grad:  {layer.weight.grad}")          # should be None
    print(f"  lora_A.grad:  {layer.lora_A.grad.norm():.4f}")  # should be nonzero
    print(f"  lora_B.grad:  {layer.lora_B.grad.norm():.4f}")  # should be nonzero
    assert layer.weight.grad is None, "Base weight should NOT receive gradients!"
    assert layer.lora_A.grad is not None and layer.lora_A.grad.norm() > 0
    assert layer.lora_B.grad is not None and layer.lora_B.grad.norm() > 0
    print("  PASS: gradients only flow through lora_A and lora_B.")

    # 1b. Verify B=0 means adapter starts as zero contribution
    print("\n[1b] Zero-init check (B=0 → adapter adds nothing at init)")
    fresh = LoRALinear(64, 64, r=4)
    x_test = torch.randn(1, 64)
    base_out = x_test @ fresh.weight.T
    full_out = fresh(x_test)
    diff = (base_out - full_out).abs().max().item()
    print(f"  Max diff between base and full output at init: {diff:.6f}")
    assert diff < 1e-5, "lora_B=0 should make adapter contribution zero at init"
    print("  PASS: lora_B=0 means adapter is identity at initialisation.")

    # 1c. Apply to a tiny model, verify forward pass works
    print("\n[1c] Tiny GPT with LoRA projections — forward pass")
    model = TinyGPTWithLoRA(vocab_size=1000, n_embd=64, n_head=4, lora_r=8)
    dummy = torch.randint(0, 1000, (2, 16))
    logits = model(dummy)
    print(f"  Input shape: {dummy.shape}  →  Logits shape: {logits.shape}")
    assert logits.shape == (2, 16, 1000)
    print("  PASS: forward pass works with LoRA in Q/K/V projections.")

    # 1d. Count trainable params
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n  Total params:     {total:,}")
    print(f"  Trainable params: {trainable:,}  ({100 * trainable / total:.1f}%)")

    # 1e. Merge adapter
    print("\n[1d] Merge adapter into frozen weight")
    orig_out = layer(x_test := torch.randn(1, 512)).detach()
    merged_layer = layer.merge()
    merged_out = merged_layer(x_test).detach()
    merge_diff = (orig_out - merged_out).abs().max().item()
    print(f"  Max diff after merge: {merge_diff:.6f}")
    assert merge_diff < 1e-4
    print("  PASS: merged layer produces identical output to LoRA layer.")

    print("\nPart 1 complete. Key insight: lora_B=0 ensures the adapter starts")
    print("as a zero contribution, so training begins from the pre-trained output.")


# Part 2: Rank comparison with PEFT

def format_alpaca(sample: dict) -> str:
    if sample.get("input"):
        return f"### Instruction:\n{sample['instruction']}\n\n### Input:\n{sample['input']}\n\n### Response:\n{sample['output']}"
    return f"### Instruction:\n{sample['instruction']}\n\n### Response:\n{sample['output']}"


def run_lora_rank(r: int, tokenizer, dataset) -> dict:
    print(f"\n{'─'*50}")
    print(f"  LoRA r={r}")

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
    )

    lora_config = LoraConfig(
        r=r,
        lora_alpha=r * 2,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    trainable_pct = round(100 * trainable / total, 3)
    print(f"  Trainable: {trainable:,} / {total:,}  ({trainable_pct}%)")

    output_dir = str(CHECKPOINT_DIR / f"lora_r{r}")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=output_dir,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            max_steps=MAX_STEPS,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=50,
            save_steps=MAX_STEPS,
            report_to="none",
        ),
        formatting_func=format_alpaca,
        max_seq_length=MAX_SEQ_LEN,
    )

    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0

    samples_per_sec = round((MAX_STEPS * 2) / elapsed, 2)  # batch_size=2
    peak_vram = round(torch.cuda.max_memory_allocated() / 1e9, 2)

    # Quick qualitative check
    model.eval()
    prompt = "### Instruction:\nExplain what a transformer is in simple terms.\n\n### Response:\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=80, do_sample=False)
    response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"  Sample output: {response[:150].strip()}")

    del model
    torch.cuda.empty_cache()

    return {
        "r": r,
        "trainable_pct": trainable_pct,
        "peak_vram_gb": peak_vram,
        "samples_per_sec": samples_per_sec,
        "checkpoint": output_dir,
        "sample_output": response[:300],
    }


def part_ranks() -> None:
    print("PART 2 — Rank comparison (r=8, r=16, r=64)")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    dataset = load_dataset(DATASET, split="train")
    print(f"Dataset loaded: {len(dataset):,} samples")

    results = []
    for r in [8, 16, 64]:
        results.append(run_lora_rank(r, tokenizer, dataset))

    print(f"\n{'─'*60}")
    print(f"  {'Rank':<8} {'Trainable %':<14} {'VRAM (GB)':<12} {'Samples/sec'}")
    for r in results:
        print(f"  r={r['r']:<6} {r['trainable_pct']:<14} {r['peak_vram_gb']:<12} {r['samples_per_sec']}")

    out = RESULTS_DIR / "day04_rank_comparison.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")
    print(f"Best checkpoint for Day 6 (DPO): use r=16 unless r=64 was noticeably better.")


# Part 3: Merge adapter

def part_merge() -> None:
    print("PART 3 — Merge LoRA adapter into base model")

    # Use the r=16 checkpoint by default (change if you prefer r=64)
    adapter_path = str(CHECKPOINT_DIR / "lora_r16")
    merged_path = CHECKPOINT_DIR / "mistral-7b-lora-merged"

    if not Path(adapter_path).exists():
        print(f"  Adapter not found at {adapter_path}")
        print("  Run --part ranks first.")
        return

    print(f"  Loading base model + adapter from {adapter_path}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    base = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto")
    model = PeftModel.from_pretrained(base, adapter_path)

    print("  Merging and unloading adapters...")
    model = model.merge_and_unload()
    model.save_pretrained(str(merged_path))
    tokenizer.save_pretrained(str(merged_path))
    print(f"  Saved merged model → {merged_path}")

    # Verify it generates sensible output
    model.eval()
    prompt = "### Instruction:\nWhat is the capital of France?\n\n### Response:\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=60, do_sample=False)
    response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"\n  Verification output: {response.strip()}")
    print("\n  Merged model is ready. Path to use in Day 6 DPO:")
    print(f"  {merged_path}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["scratch", "ranks", "merge"], required=True)
    args = parser.parse_args()

    if args.part == "scratch":
        part_scratch()
    elif args.part == "ranks":
        part_ranks()
    elif args.part == "merge":
        part_merge()


if __name__ == "__main__":
    main()
