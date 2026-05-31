"""
Day 14 — Pre-training from Scratch on a Custom Domain

Options:
  A) Continued pre-training (DAPT): take GPT-2 and keep training on domain text
  B) From scratch: train a small 120M model from random init on domain text

Both train on the same domain corpus (ArXiv CS or Wikipedia Simple).
Compare perplexity on domain text vs general text to see domain specialization.

Run:
    python day14_pretraining.py --mode dapt        # continued pre-training (recommended)
    python day14_pretraining.py --mode scratch     # train from scratch
    python day14_pretraining.py --mode tokenizer   # train + compare BPE tokenizers only
    python day14_pretraining.py --eval --checkpoint <path>  # eval a saved checkpoint
"""

import argparse
import json
import math
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from datasets import load_dataset
from tokenizers import Tokenizer, models, pre_tokenizers, trainers
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GPT2Config,
    GPT2LMHeadModel,
    GPT2Tokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
import wandb

RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "day14"
TOKENIZER_DIR = Path(__file__).parent / "checkpoints" / "day14" / "domain_tokenizer"
RESULTS_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
TOKENIZER_DIR.mkdir(exist_ok=True)

DOMAIN = "arxiv"   # "arxiv" or "wiki_simple"
N_CORPUS_TOKENS = 10_000_000   # ~10M tokens for training


# ── Corpus loading ────────────────────────────────────────────────────────────

def load_domain_corpus(domain: str, streaming: bool = True):
    if domain == "arxiv":
        print("Loading ArXiv CS abstracts...")
        ds = load_dataset("togethercomputer/RedPajama-Data-1T-Sample", split="train", streaming=streaming)
        return (d["text"] for d in ds if d.get("meta", {}).get("redpajama_set_name") == "RedPajamaArXiv")
    elif domain == "wiki_simple":
        print("Loading Wikipedia Simple English...")
        ds = load_dataset("wikimedia/wikipedia", "20231101.simple", split="train", streaming=streaming)
        return (d["text"] for d in ds)
    raise ValueError(f"Unknown domain: {domain}")


# ── Step 1: Train and compare tokenizers ─────────────────────────────────────

def train_domain_tokenizer(texts: list[str]) -> str:
    print("\nTraining domain BPE tokenizer...")
    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    trainer = trainers.BpeTrainer(
        vocab_size=32000,
        special_tokens=["<|endoftext|>", "<|pad|>"],
        min_frequency=2,
    )
    tokenizer.train_from_iterator(texts, trainer=trainer)
    save_path = str(TOKENIZER_DIR / "tokenizer.json")
    tokenizer.save(save_path)
    print(f"  Domain tokenizer saved → {save_path}")
    return save_path


def compare_tokenizers(domain_tok_path: str, sample_texts: list[str]) -> dict:
    """Compare domain tokenizer vs GPT-2 tokenizer on compression ratio."""
    from tokenizers import Tokenizer as HFTokenizer
    domain_tok = HFTokenizer.from_file(domain_tok_path)
    gpt2_tok = GPT2Tokenizer.from_pretrained("gpt2")

    domain_tokens = sum(len(domain_tok.encode(t).ids) for t in sample_texts)
    gpt2_tokens = sum(len(gpt2_tok.encode(t)) for t in sample_texts)
    total_chars = sum(len(t) for t in sample_texts)

    result = {
        "n_samples": len(sample_texts),
        "total_chars": total_chars,
        "domain_tokenizer_tokens": domain_tokens,
        "gpt2_tokenizer_tokens": gpt2_tokens,
        "domain_chars_per_token": round(total_chars / domain_tokens, 2),
        "gpt2_chars_per_token": round(total_chars / gpt2_tokens, 2),
        "compression_improvement_pct": round(100 * (gpt2_tokens - domain_tokens) / gpt2_tokens, 1),
    }
    print(f"\n  Tokenizer comparison:")
    print(f"  Domain tokenizer: {result['domain_chars_per_token']} chars/token")
    print(f"  GPT-2 tokenizer:  {result['gpt2_chars_per_token']} chars/token")
    print(f"  Domain compresses {result['compression_improvement_pct']}% {'better' if result['compression_improvement_pct'] > 0 else 'worse'} than GPT-2")
    return result


# ── Step 2: Perplexity evaluation ─────────────────────────────────────────────

def compute_perplexity(model, tokenizer, texts: list[str], max_tokens: int = 4096) -> float:
    model.eval()
    text = " ".join(texts)[:50000]
    enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_tokens)
    input_ids = enc.input_ids.to(model.device)

    stride = 512
    block_size = 1024
    nlls = []
    prev_end = 0
    for begin in range(0, input_ids.size(1), stride):
        end = min(begin + block_size, input_ids.size(1))
        target_len = end - prev_end
        with torch.no_grad():
            out = model(input_ids[:, begin:end], labels=input_ids[:, begin:end])
        nlls.append(out.loss * target_len)
        prev_end = end
        if end == input_ids.size(1):
            break

    ppl = math.exp(torch.stack(nlls).sum() / input_ids.size(1))
    return round(float(ppl), 2)


# ── Step 3: DAPT — continued pre-training ────────────────────────────────────

class StreamingTextDataset(Dataset):
    def __init__(self, texts: list[str], tokenizer, block_size: int = 1024):
        print("  Tokenizing corpus...")
        all_ids = []
        for text in texts:
            ids = tokenizer.encode(text) + [tokenizer.eos_token_id]
            all_ids.extend(ids)
            if len(all_ids) >= N_CORPUS_TOKENS:
                break
        print(f"  {len(all_ids):,} tokens collected")
        self.examples = [
            torch.tensor(all_ids[i: i + block_size + 1], dtype=torch.long)
            for i in range(0, len(all_ids) - block_size, block_size)
        ]

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        chunk = self.examples[idx]
        return {"input_ids": chunk[:-1], "labels": chunk[1:]}


def run_dapt(domain_corpus: list[str]) -> str:
    print("\nMode: DAPT (continued pre-training on GPT-2 medium)")
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2-medium")
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained("gpt2-medium", torch_dtype=torch.bfloat16)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  GPT-2 medium: {n_params / 1e6:.0f}M params")

    dataset = StreamingTextDataset(domain_corpus, tokenizer, block_size=1024)
    print(f"  Training examples: {len(dataset):,}")

    wandb.init(project="gpu-sprint-day14", name="dapt_gpt2_medium", reinit=True)
    output_dir = str(CHECKPOINT_DIR / "dapt_gpt2_medium")
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=1,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=2e-5,       # low LR for continued pre-training
            bf16=True,
            gradient_checkpointing=True,
            logging_steps=100,
            save_steps=500,
            report_to="wandb",
            dataloader_num_workers=2,
        ),
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    trainer.train()
    trainer.save_model(output_dir)
    wandb.finish()
    print(f"  DAPT model saved → {output_dir}")
    return output_dir


# ── Step 4: From scratch ──────────────────────────────────────────────────────

def run_from_scratch(domain_corpus: list[str]) -> str:
    print("\nMode: Train 120M GPT-2 from random init")
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

    config = GPT2Config(
        vocab_size=50257,
        n_layer=12,
        n_head=12,
        n_embd=768,
        n_positions=1024,
    )
    model = GPT2LMHeadModel(config)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Model: {n_params / 1e6:.0f}M params (random init)")

    dataset = StreamingTextDataset(domain_corpus, tokenizer, block_size=1024)
    wandb.init(project="gpu-sprint-day14", name="scratch_gpt2_120m", reinit=True)
    output_dir = str(CHECKPOINT_DIR / "scratch_gpt2_120m")
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=1,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=3e-4,       # higher LR for training from scratch
            bf16=True,
            gradient_checkpointing=True,
            warmup_steps=500,
            logging_steps=100,
            save_steps=1000,
            report_to="wandb",
            dataloader_num_workers=2,
        ),
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    trainer.train()
    trainer.save_model(output_dir)
    wandb.finish()
    print(f"  From-scratch model saved → {output_dir}")
    return output_dir


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dapt", "scratch", "tokenizer"])
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--checkpoint", type=str)
    args = parser.parse_args()

    if args.mode == "tokenizer":
        print("Training and comparing tokenizers...")
        corpus_iter = load_domain_corpus(DOMAIN)
        corpus_list = [next(corpus_iter) for _ in range(5000)]
        tok_path = train_domain_tokenizer(corpus_list)
        result = compare_tokenizers(tok_path, corpus_list[:500])
        out = RESULTS_DIR / "day14_tokenizer_comparison.json"
        out.write_text(json.dumps(result, indent=2))
        print(f"Results saved → {out}")
        return

    # Load corpus as list (streaming into memory for training)
    corpus_iter = load_domain_corpus(DOMAIN)
    corpus_list = []
    for text in corpus_iter:
        corpus_list.append(text)
        if len(corpus_list) >= 20000:
            break
    print(f"Corpus: {len(corpus_list):,} documents")

    if args.mode == "dapt":
        checkpoint = run_dapt(corpus_list)
    elif args.mode == "scratch":
        checkpoint = run_from_scratch(corpus_list)
    else:
        checkpoint = args.checkpoint

    if args.eval or checkpoint:
        ckpt_path = args.checkpoint or checkpoint
        print(f"\nEvaluating {ckpt_path}...")

        model = AutoModelForCausalLM.from_pretrained(ckpt_path, torch_dtype=torch.bfloat16, device_map="auto")
        tokenizer = AutoTokenizer.from_pretrained(ckpt_path if args.checkpoint else "gpt2")
        tokenizer.pad_token = tokenizer.eos_token

        domain_texts = corpus_list[:100]
        ds_general = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
        general_texts = ds_general["text"][:100]

        domain_ppl = compute_perplexity(model, tokenizer, domain_texts)
        general_ppl = compute_perplexity(model, tokenizer, general_texts)

        # Compare with baseline (original GPT-2 medium)
        base = AutoModelForCausalLM.from_pretrained("gpt2-medium", torch_dtype=torch.bfloat16, device_map="auto")
        base_tok = GPT2Tokenizer.from_pretrained("gpt2-medium")
        base_tok.pad_token = base_tok.eos_token
        base_domain_ppl = compute_perplexity(base, base_tok, domain_texts)
        base_general_ppl = compute_perplexity(base, base_tok, general_texts)

        result = {
            "checkpoint": str(ckpt_path),
            "domain_perplexity": {"base_gpt2": base_domain_ppl, "trained": domain_ppl},
            "general_perplexity": {"base_gpt2": base_general_ppl, "trained": general_ppl},
        }
        print(f"\n  Domain PPL:  base={base_domain_ppl}  →  trained={domain_ppl}  ({'↓ better' if domain_ppl < base_domain_ppl else '↑ worse'})")
        print(f"  General PPL: base={base_general_ppl}  →  trained={general_ppl}  ({'↓ better' if general_ppl < base_general_ppl else '↑ worse (catastrophic forgetting?)'})")

        out = RESULTS_DIR / "day14_perplexity_eval.json"
        out.write_text(json.dumps(result, indent=2))
        print(f"Results saved → {out}")


if __name__ == "__main__":
    main()
