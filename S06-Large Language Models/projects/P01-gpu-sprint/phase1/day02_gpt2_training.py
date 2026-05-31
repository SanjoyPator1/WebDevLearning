"""
Day 2 — Train GPT-2 scale properly
Experiments:
  A) baseline (no FlashAttention-2, fp32)
  B) + FlashAttention-2
  C) + bf16 mixed precision
  D) full run on FineWeb-Edu for a few thousand steps

Run with:
    python day02_gpt2_training.py --run baseline
    python day02_gpt2_training.py --run flash
    python day02_gpt2_training.py --run bf16
    python day02_gpt2_training.py --run full
"""

import argparse
import math
import time
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
import wandb
from datasets import load_dataset
from torch.amp import GradScaler, autocast
from torch.utils.data import DataLoader, Dataset
from transformers import GPT2Tokenizer

RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "day02"
RESULTS_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# ── Model config (GPT-2 small = 124M params) ────────────────────────────────

@dataclass
class GPTConfig:
    vocab_size: int = 50257
    block_size: int = 1024   # context length
    n_layer: int = 12
    n_head: int = 12
    n_embd: int = 768
    dropout: float = 0.0
    use_flash: bool = False


# ── Model ────────────────────────────────────────────────────────────────────

class CausalSelfAttention(nn.Module):
    def __init__(self, config: GPTConfig):
        super().__init__()
        assert config.n_embd % config.n_head == 0
        self.n_head = config.n_head
        self.n_embd = config.n_embd
        self.use_flash = config.use_flash

        self.c_attn = nn.Linear(config.n_embd, 3 * config.n_embd)
        self.c_proj = nn.Linear(config.n_embd, config.n_embd)
        self.dropout = config.dropout

        if not self.use_flash:
            self.register_buffer(
                "bias",
                torch.tril(torch.ones(config.block_size, config.block_size)).view(
                    1, 1, config.block_size, config.block_size
                ),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        head_dim = C // self.n_head

        qkv = self.c_attn(x)
        q, k, v = qkv.split(C, dim=2)
        q = q.view(B, T, self.n_head, head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, head_dim).transpose(1, 2)

        if self.use_flash:
            # FlashAttention-2 via PyTorch's scaled_dot_product_attention
            # (uses FA2 kernel automatically when available on CUDA)
            y = F.scaled_dot_product_attention(q, k, v, dropout_p=self.dropout if self.training else 0.0, is_causal=True)
        else:
            scale = 1.0 / math.sqrt(head_dim)
            att = (q @ k.transpose(-2, -1)) * scale
            att = att.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
            att = F.softmax(att, dim=-1)
            y = att @ v

        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.c_proj(y)


class MLP(nn.Module):
    def __init__(self, config: GPTConfig):
        super().__init__()
        self.c_fc = nn.Linear(config.n_embd, 4 * config.n_embd)
        self.gelu = nn.GELU()
        self.c_proj = nn.Linear(4 * config.n_embd, config.n_embd)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.c_proj(self.gelu(self.c_fc(x)))


class Block(nn.Module):
    def __init__(self, config: GPTConfig):
        super().__init__()
        self.ln_1 = nn.LayerNorm(config.n_embd)
        self.attn = CausalSelfAttention(config)
        self.ln_2 = nn.LayerNorm(config.n_embd)
        self.mlp = MLP(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x


class GPT(nn.Module):
    def __init__(self, config: GPTConfig):
        super().__init__()
        self.config = config
        self.transformer = nn.ModuleDict({
            "wte": nn.Embedding(config.vocab_size, config.n_embd),
            "wpe": nn.Embedding(config.block_size, config.n_embd),
            "h": nn.ModuleList([Block(config) for _ in range(config.n_layer)]),
            "ln_f": nn.LayerNorm(config.n_embd),
        })
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)
        self.transformer["wte"].weight = self.lm_head.weight  # weight tying

        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.transformer["wte"](idx) + self.transformer["wpe"](pos)
        for block in self.transformer["h"]:
            x = block(x)
        x = self.transformer["ln_f"](x)
        logits = self.lm_head(x)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss

    def num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())

    @torch.no_grad()
    def generate(self, idx: torch.Tensor, max_new_tokens: int, temperature: float = 1.0) -> torch.Tensor:
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.config.block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_token], dim=1)
        return idx


# ── Dataset ──────────────────────────────────────────────────────────────────

class TokenDataset(Dataset):
    """Pre-tokenize a streaming dataset into fixed-length chunks."""

    def __init__(self, tokens: torch.Tensor, block_size: int):
        self.tokens = tokens
        self.block_size = block_size

    def __len__(self) -> int:
        return len(self.tokens) - self.block_size

    def __getitem__(self, idx: int):
        chunk = self.tokens[idx : idx + self.block_size + 1]
        return chunk[:-1], chunk[1:]


def load_fineweb(tokenizer, n_tokens: int = 5_000_000) -> torch.Tensor:
    """Stream FineWeb-Edu and collect ~n_tokens tokens."""
    print("Loading FineWeb-Edu (streaming)...")
    ds = load_dataset("HuggingFaceFW/fineweb-edu", name="sample-10BT", split="train", streaming=True)
    all_ids = []
    for sample in ds:
        ids = tokenizer.encode(sample["text"]) + [tokenizer.eos_token_id]
        all_ids.extend(ids)
        if len(all_ids) >= n_tokens:
            break
    print(f"  Collected {len(all_ids):,} tokens")
    return torch.tensor(all_ids, dtype=torch.long)


# ── Training loop ─────────────────────────────────────────────────────────────

def train(
    run_name: str,
    use_flash: bool,
    use_bf16: bool,
    max_steps: int,
    batch_size: int = 8,
    block_size: int = 512,
    lr: float = 3e-4,
    grad_accum: int = 4,
    log_every: int = 50,
    generate_at: tuple[int, ...] = (500, 1000, 2000),
) -> None:
    device = "cuda"

    wandb.init(project="gpu-sprint-day2", name=run_name, config={
        "use_flash": use_flash, "use_bf16": use_bf16,
        "max_steps": max_steps, "batch_size": batch_size,
        "block_size": block_size, "lr": lr,
    })

    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

    tokens = load_fineweb(tokenizer, n_tokens=max(5_000_000, max_steps * batch_size * block_size))
    dataset = TokenDataset(tokens, block_size)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=2, pin_memory=True)

    config = GPTConfig(block_size=block_size, use_flash=use_flash)
    model = GPT(config).to(device)
    print(f"\nModel: {model.num_params() / 1e6:.1f}M params | flash={use_flash} | bf16={use_bf16}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
    scaler = GradScaler(enabled=use_bf16)
    dtype = torch.bfloat16 if use_bf16 else torch.float32

    data_iter = iter(loader)
    step = 0
    optimizer.zero_grad()

    while step < max_steps:
        t0 = time.time()
        total_loss = 0.0

        for micro in range(grad_accum):
            try:
                x, y = next(data_iter)
            except StopIteration:
                data_iter = iter(loader)
                x, y = next(data_iter)
            x, y = x.to(device), y.to(device)

            with autocast(device_type="cuda", dtype=dtype, enabled=use_bf16):
                _, loss = model(x, y)
                loss = loss / grad_accum

            scaler.scale(loss).backward()
            total_loss += loss.item()

        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad()

        step += 1
        elapsed = time.time() - t0
        tokens_per_sec = (batch_size * block_size * grad_accum) / elapsed
        vram = torch.cuda.memory_allocated() / 1e9

        if step % log_every == 0:
            print(f"step {step:5d} | loss {total_loss:.4f} | {tokens_per_sec:,.0f} tok/s | VRAM {vram:.2f} GB")
            wandb.log({"loss": total_loss, "tokens_per_sec": tokens_per_sec, "vram_gb": vram, "step": step})

        if step in generate_at:
            _generate_sample(model, tokenizer, device, step)
            ckpt_path = CHECKPOINT_DIR / f"{run_name}_step{step}.pt"
            torch.save(model.state_dict(), ckpt_path)
            print(f"  Checkpoint saved → {ckpt_path}")

    wandb.finish()
    print(f"\nDone: {run_name}")


def _generate_sample(model: GPT, tokenizer, device: str, step: int) -> None:
    model.eval()
    prompt = "The history of artificial intelligence"
    ids = tokenizer.encode(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=80, temperature=0.8)
    text = tokenizer.decode(out[0].tolist(), skip_special_tokens=True)
    print(f"\n[Step {step}] Sample:\n  {text}\n")
    model.train()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", choices=["baseline", "flash", "bf16", "full"], default="baseline")
    args = parser.parse_args()

    configs = {
        # name,          flash, bf16,  steps
        "baseline": ("baseline_no_flash", False, False, 200),
        "flash":    ("flash_attention",   True,  False, 200),
        "bf16":     ("flash_bf16",        True,  True,  200),
        "full":     ("full_fineweb",      True,  True,  3000),
    }

    name, use_flash, use_bf16, steps = configs[args.run]
    train(run_name=name, use_flash=use_flash, use_bf16=use_bf16, max_steps=steps)


if __name__ == "__main__":
    main()
