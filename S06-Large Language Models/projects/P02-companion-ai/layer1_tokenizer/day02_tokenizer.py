"""
Layer 1 — Day 2 (Morning): Custom Tokenizer
============================================
Trains a domain-specific BPE tokenizer on the therapy pretrain corpus
and compares its compression ratio against GPT-2's general tokenizer.

Produces:
    checkpoints/therapy_tokenizer.json   ← consumed by Layers 3, 4, 5

Run:
    python day02_tokenizer.py --train              # train tokenizer
    python day02_tokenizer.py --compare            # compare vs GPT-2
    python day02_tokenizer.py --inspect            # inspect therapy-specific words
    python day02_tokenizer.py --all                # run all three steps
"""

import argparse
import json
from pathlib import Path

from tokenizers import Tokenizer, models, pre_tokenizers, trainers
from transformers import GPT2Tokenizer

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

TOKENIZER_PATH = CHECKPOINT_DIR / "therapy_tokenizer.json"

# Special tokens needed by later layers
SPECIAL_TOKENS = [
    "<|endoftext|>",   # standard end-of-text
    "<|system|>",      # system prompt boundary (Layer 4 SFT)
    "<|user|>",        # user turn boundary
    "<|assistant|>",   # assistant turn boundary
    "<|memory|>",      # episodic memory injection (Layer 9)
    "<|crisis|>",      # safety flag (Layer 10)
    "<|end|>",         # end of turn
    "<|pad|>",         # padding
]

# Therapy-specific words to inspect after training
THERAPY_WORDS = [
    "hypervigilance",
    "dissociation",
    "rumination",
    "catastrophising",
    "depersonalisation",
    "derealisation",
    "anhedonia",
    "alexithymia",
    "psychoeducation",
    "cognitive distortion",
    "dialectical behaviour therapy",
    "cognitive behavioural therapy",
    "attachment theory",
    "radical acceptance",
    "EMDR",
    "exposure therapy",
    "grounding technique",
    "self-compassion",
    "emotional dysregulation",
    "window of tolerance",
]

# General words (control group — should tokenize similarly across tokenizers)
GENERAL_WORDS = [
    "artificial intelligence",
    "machine learning",
    "programming",
    "mathematics",
    "government",
    "international",
    "communication",
    "environment",
]


# Load pretrain corpus

def load_pretrain_texts() -> list[str]:
    path = SPLITS_DIR / "pretrain.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Pretrain split not found at {path}\n"
            "Run layer0_data_pipeline/day01_data_pipeline.py --all first."
        )
    data = json.loads(path.read_text())
    print(f"Loaded {len(data):,} pretrain texts")
    return data


def load_finetune_texts() -> list[str]:
    """Also include finetune questions/answers to expose the tokenizer to conversation format."""
    path = SPLITS_DIR / "finetune.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    texts = []
    for ex in data:
        texts.append(ex.get("question", ""))
        texts.append(ex.get("answer", ""))
    return [t for t in texts if t]


# Train tokenizer

def train_tokenizer(texts: list[str]) -> Tokenizer:
    print(f"\nTraining BPE tokenizer on {len(texts):,} texts...")
    print(f"Vocabulary size: 32,000 | Special tokens: {len(SPECIAL_TOKENS)}")

    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)

    trainer = trainers.BpeTrainer(
        vocab_size=32_000,
        special_tokens=SPECIAL_TOKENS,
        min_frequency=2,
        show_progress=True,
    )

    tokenizer.train_from_iterator(iter(texts), trainer=trainer, length=len(texts))

    tokenizer.save(str(TOKENIZER_PATH))
    print(f"\nTokenizer saved → {TOKENIZER_PATH}")
    return tokenizer


# Compare compression

def compare_tokenizers(therapy_tok: Tokenizer, sample_texts: list[str]) -> dict:
    """
    Measure chars-per-token on therapy text vs general text.
    A higher ratio = better compression = fewer tokens per sentence.
    """
    gpt2_tok = GPT2Tokenizer.from_pretrained("gpt2")

    # Load general text sample (wikitext fallback if available)
    try:
        from datasets import load_dataset
        wiki = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
        general_texts = [t for t in wiki["text"] if len(t.split()) > 20][:500]
    except Exception:
        general_texts = sample_texts  # fallback: same texts

    results = {}
    for label, texts in [("therapy text", sample_texts[:500]), ("general text", general_texts[:500])]:
        therapy_tokens = sum(len(therapy_tok.encode(t).ids) for t in texts)
        gpt2_tokens = sum(len(gpt2_tok.encode(t)) for t in texts)
        total_chars = sum(len(t) for t in texts)

        therapy_cpt = round(total_chars / max(therapy_tokens, 1), 2)
        gpt2_cpt = round(total_chars / max(gpt2_tokens, 1), 2)
        improvement = round(100 * (gpt2_tokens - therapy_tokens) / max(gpt2_tokens, 1), 1)

        results[label] = {
            "therapy_tokenizer_chars_per_token": therapy_cpt,
            "gpt2_chars_per_token": gpt2_cpt,
            "compression_improvement_pct": improvement,
        }

        direction = "better" if improvement > 0 else "worse"
        print(f"\n  {label}:")
        print(f"    Therapy tokenizer: {therapy_cpt} chars/token")
        print(f"    GPT-2 tokenizer:   {gpt2_cpt} chars/token")
        print(f"    Difference:        {improvement:+.1f}% ({direction})")

    return results


# Inspect therapy-specific words

def inspect_words(therapy_tok: Tokenizer) -> list[dict]:
    gpt2_tok = GPT2Tokenizer.from_pretrained("gpt2")

    print(f"\n{'─'*65}")
    print(f"  {'Word':<35} {'Therapy tok':<14} {'GPT-2'}")

    rows = []
    for word in THERAPY_WORDS + GENERAL_WORDS:
        t_ids = therapy_tok.encode(word).ids
        g_ids = gpt2_tok.encode(word)
        t_tokens = therapy_tok.encode(word).tokens
        flag = " ←" if word in THERAPY_WORDS and len(t_ids) < len(g_ids) else ""
        print(f"  {word:<35} {len(t_ids):<14} {len(g_ids)}{flag}")
        rows.append({
            "word": word,
            "therapy_n_tokens": len(t_ids),
            "gpt2_n_tokens": len(g_ids),
            "therapy_tokens": t_tokens,
            "is_therapy_specific": word in THERAPY_WORDS,
        })

    therapy_specific = [r for r in rows if r["is_therapy_specific"]]
    avg_therapy = sum(r["therapy_n_tokens"] for r in therapy_specific) / len(therapy_specific)
    avg_gpt2 = sum(r["gpt2_n_tokens"] for r in therapy_specific) / len(therapy_specific)
    print(f"\n  Avg tokens for therapy-specific words:")
    print(f"    Therapy tokenizer: {avg_therapy:.1f}")
    print(f"    GPT-2 tokenizer:   {avg_gpt2:.1f}")
    if avg_therapy < avg_gpt2:
        print(f"    → Therapy tokenizer uses {avg_gpt2 - avg_therapy:.1f} fewer tokens on average for domain words")

    return rows


# Verify special tokens

def verify_special_tokens(therapy_tok: Tokenizer) -> None:
    print(f"\n  Special token verification:")
    for tok in SPECIAL_TOKENS:
        ids = therapy_tok.encode(tok).ids
        is_single = len(ids) == 1
        status = "✓" if is_single else "✗ (split into multiple tokens — check training)"
        print(f"    {tok:<20} → {ids}  {status}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--all", dest="run_all", action="store_true")
    args = parser.parse_args()

    if args.run_all or args.train:
        pretrain_texts = load_pretrain_texts()
        finetune_texts = load_finetune_texts()
        all_texts = pretrain_texts + finetune_texts
        therapy_tok = train_tokenizer(all_texts)
        verify_special_tokens(therapy_tok)
    else:
        if not TOKENIZER_PATH.exists():
            print(f"Tokenizer not found at {TOKENIZER_PATH}. Run --train first.")
            return
        therapy_tok = Tokenizer.from_file(str(TOKENIZER_PATH))
        print(f"Loaded tokenizer from {TOKENIZER_PATH}")

    if args.run_all or args.compare:
        pretrain_texts = load_pretrain_texts()
        comparison = compare_tokenizers(therapy_tok, pretrain_texts)
        out = RESULTS_DIR / "tokenizer_comparison.json"
        out.write_text(json.dumps(comparison, indent=2))
        print(f"\n  Results saved → {out}")

    if args.run_all or args.inspect:
        rows = inspect_words(therapy_tok)
        out = RESULTS_DIR / "token_inspection.json"
        out.write_text(json.dumps(rows, indent=2))
        print(f"  Results saved → {out}")

    if not any([args.run_all, args.train, args.compare, args.inspect]):
        parser.print_help()


if __name__ == "__main__":
    main()
