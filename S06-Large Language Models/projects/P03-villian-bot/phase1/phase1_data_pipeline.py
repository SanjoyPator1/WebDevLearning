"""
Phase 1 — Data Pipeline
========================
Collects, cleans, deduplicates, and splits data for VILLAINBOT into:
  - pretrain : raw text for DAPT (Phase 2)
  - finetune : (user_msg, villain_response) pairs for SFT/DPO (Phases 3, 4)
  - eval     : held-out set — never touched during training

Sources:
  - Maximofn/short-jokes-dataset           (HuggingFace) — 231k English jokes
  - metaeval/offensive-humor               (HuggingFace) — 102k Reddit jokes (title+body)
  - Hand-crafted villain pairs             (handcrafted_data.json, gold standard)

Dropped sources (with reason):
  - nanelimon/insult-dataset               — Turkish language, not English
  - Fraser/short-jokes                     — uses loading script, no longer supported by datasets>=3
  - DevonPeroutky/reddit-roastme-visual-qa — requires local image files to load, fails in text-only env

Run individual steps:
    python phase1_data_pipeline.py --download   # download all sources → data/raw/
    python phase1_data_pipeline.py --clean      # dedup + filter → data/clean/
    python phase1_data_pipeline.py --split      # build final splits → data/splits/
    python phase1_data_pipeline.py --stats      # print stats + sample rows
    python phase1_data_pipeline.py --inspect    # show schema + 3 rows per raw source
    python phase1_data_pipeline.py --all        # run all steps in order
"""

import argparse
import json
import os
import random
import re
import unicodedata
from pathlib import Path

from datasets import load_dataset
from datasketch import MinHash, MinHashLSH

NUM_PROC = min(16, os.cpu_count() or 1)
random.seed(42)

BASE_DIR  = Path(__file__).parent.parent
DATA_DIR  = BASE_DIR / "data"
RAW_DIR   = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
SPLITS_DIR = DATA_DIR / "splits"

for d in [RAW_DIR, CLEAN_DIR, SPLITS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ── Cleaning ──────────────────────────────────────────────────────────────────
# Villain-safe: keep ALL CAPS, exclamation marks, ellipses — they are style.
# Only strip URLs and normalize whitespace.

def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text.split()) < 5:
        return ""
    return text


# ── Deduplication ─────────────────────────────────────────────────────────────

def get_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for word in text.lower().split():
        m.update(word.encode("utf8"))
    return m


def deduplicate(texts: list[str], threshold: float = 0.8) -> list[str]:
    total = len(texts)
    print(f"  Deduplicating {total:,} texts (threshold={threshold})...", flush=True)
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    unique = []
    step = max(1, total // 20)  # print progress every 5%
    for i, text in enumerate(texts):
        m = get_minhash(text)
        if not lsh.query(m):
            lsh.insert(str(i), m)
            unique.append(text)
        if (i + 1) % step == 0:
            pct = (i + 1) / total * 100
            print(f"  {pct:5.1f}% — {i+1:,}/{total:,} processed, {len(unique):,} unique so far", flush=True)
    print(f"  Done: {total:,} → {len(unique):,} unique ({total - len(unique):,} removed)", flush=True)
    return unique


def deduplicate_pairs(pairs: list[dict], key: str = "question", threshold: float = 0.8) -> list[dict]:
    texts = [p[key] for p in pairs]
    unique_texts = set(deduplicate(texts, threshold))
    return [p for p in pairs if p[key] in unique_texts]


# ── Dataset downloaders ───────────────────────────────────────────────────────

def download_short_jokes() -> list[str]:
    """
    Maximofn/short-jokes-dataset — 231k English jokes.
    Replaces Fraser/short-jokes which uses a loading script no longer supported.
    Used as pretrain text for comedic register.
    """
    print("Downloading Maximofn/short-jokes-dataset...", flush=True)
    try:
        ds = load_dataset("Maximofn/short-jokes-dataset", split="train")
    except Exception as e:
        print(f"  Failed: {e} — skipping", flush=True)
        return []

    print(f"  Loaded {len(ds):,} rows | columns: {ds.column_names}", flush=True)
    df = ds.to_pandas()
    col_lower = {c.lower(): c for c in df.columns}
    text_col = next(
        (col_lower[c] for c in ("joke", "text", "body", "content") if c in col_lower),
        None
    )
    if text_col is None:
        print(f"  No joke column found — skipping", flush=True)
        return []

    texts = []
    for val in df[text_col].fillna("").tolist():
        t = clean_text(str(val))
        if t:
            texts.append(t)

    print(f"  Done — {len(texts):,} jokes as pretrain texts", flush=True)
    return texts


def download_offensive_humor() -> list[str]:
    """
    metaeval/offensive-humor — 102k Reddit jokes.
    Actual columns (confirmed from --inspect): joke_type, score, title, selftext.
    We combine title + selftext as the full joke text and filter score > 0 for quality.
    """
    print("Downloading metaeval/offensive-humor...", flush=True)
    try:
        ds = load_dataset("metaeval/offensive-humor", split="train")
    except Exception as e:
        print(f"  Failed: {e} — skipping", flush=True)
        return []

    print(f"  Loaded {len(ds):,} rows | columns: {ds.column_names}", flush=True)
    df = ds.to_pandas()

    # filter out downvoted content
    if "score" in df.columns:
        before = len(df)
        df = df[df["score"] > 0]
        print(f"  score > 0 filter: {before:,} → {len(df):,} rows", flush=True)

    texts = []
    for _, row in df.iterrows():
        title = clean_text(str(row.get("title", "") or ""))
        body  = clean_text(str(row.get("selftext", "") or ""))
        combined = (title + " " + body).strip() if body else title
        if combined and len(combined.split()) >= 5:
            texts.append(combined)

    print(f"  Done — {len(texts):,} texts from offensive-humor", flush=True)
    return texts


def build_villain_handcrafted() -> list[dict]:
    """
    Gold-standard villain response pairs loaded from handcrafted_data.json.
    These are the most important data — they define the exact VILLAINBOT persona.
    Every SFT run keeps these; they are never filtered or deduped.
    To add more pairs: edit handcrafted_data.json directly.
    """
    print("Loading hand-crafted villain pairs...", flush=True)
    data_file = Path(__file__).parent / "handcrafted_data.json"
    if not data_file.exists():
        print(f"  WARNING: {data_file} not found — returning empty list", flush=True)
        return []
    pairs = json.loads(data_file.read_text())
    print(f"  Done — {len(pairs):,} hand-crafted villain pairs loaded from handcrafted_data.json", flush=True)
    return pairs


# ── Main pipeline steps ───────────────────────────────────────────────────────

def run_download() -> None:
    print("\n=== Step 1: Download datasets ===")

    # --- short-jokes ---
    jokes_path = RAW_DIR / "short_jokes.json"
    if jokes_path.exists():
        print(f"  Skipping short-jokes (already saved)")
    else:
        jokes = download_short_jokes()
        jokes_path.write_text(json.dumps(jokes, indent=2, ensure_ascii=False))
        print(f"  Saved → short_jokes.json ({len(jokes):,} texts)")

    # --- offensive-humor ---
    offense_path = RAW_DIR / "offensive_humor.json"
    if offense_path.exists():
        print(f"  Skipping offensive-humor (already saved)")
    else:
        texts = download_offensive_humor()
        offense_path.write_text(json.dumps(texts, indent=2, ensure_ascii=False))
        print(f"  Saved → offensive_humor.json ({len(texts):,} texts)")

    # --- hand-crafted villain pairs (always rebuild — source of truth) ---
    handcrafted_path = RAW_DIR / "villain_handcrafted.json"
    pairs = build_villain_handcrafted()
    handcrafted_path.write_text(json.dumps(pairs, indent=2, ensure_ascii=False))
    print(f"  Saved → villain_handcrafted.json ({len(pairs):,} pairs)")


def run_clean() -> None:
    print("\n=== Step 2: Clean and deduplicate ===")

    # --- short jokes ---
    jokes_raw = RAW_DIR / "short_jokes.json"
    if jokes_raw.exists():
        jokes = json.loads(jokes_raw.read_text())
        jokes_clean = deduplicate(jokes)
        (CLEAN_DIR / "short_jokes.json").write_text(json.dumps(jokes_clean, indent=2, ensure_ascii=False))
        print(f"  Short jokes: {len(jokes):,} → {len(jokes_clean):,}")
    else:
        print("  short_jokes.json not found — run --download first")

    # --- offensive humor ---
    offense_raw = RAW_DIR / "offensive_humor.json"
    if offense_raw.exists():
        texts = json.loads(offense_raw.read_text())
        texts_clean = deduplicate(texts)
        (CLEAN_DIR / "offensive_humor.json").write_text(json.dumps(texts_clean, indent=2, ensure_ascii=False))
        print(f"  Offensive humor: {len(texts):,} → {len(texts_clean):,}")
    else:
        print("  offensive_humor.json not found — run --download first")

    # --- hand-crafted (no dedup — every pair is intentionally unique) ---
    hc_raw = RAW_DIR / "villain_handcrafted.json"
    if hc_raw.exists():
        pairs = json.loads(hc_raw.read_text())
        (CLEAN_DIR / "villain_handcrafted.json").write_text(json.dumps(pairs, indent=2, ensure_ascii=False))
        print(f"  Hand-crafted: {len(pairs):,} pairs — copied as-is (gold standard, no dedup)")
    else:
        print("  villain_handcrafted.json not found — run --download first")


def run_split() -> None:
    """
    Build final splits.
    CRITICAL: eval pairs must NEVER appear in pretrain or finetune.
    Hand-crafted pairs are ALWAYS in finetune, never in eval.
    """
    print("\n=== Step 3: Build final splits ===")

    def load_clean(name: str, default=None):
        p = CLEAN_DIR / name
        if not p.exists():
            print(f"  WARNING: {name} not found in clean/ — skipping")
            return default if default is not None else []
        return json.loads(p.read_text())

    # pretrain sources
    pretrain_texts = []
    for fname, label in [
        ("short_jokes.json",     "short jokes"),
        ("offensive_humor.json", "offensive humor"),
    ]:
        texts = load_clean(fname)
        if texts:
            pretrain_texts.extend(texts)
            print(f"  Added {len(texts):,} texts from {label} to pretrain")

    # finetune: only hand-crafted pairs (gold standard)
    # eval: held-out subset of hand-crafted pairs
    handcrafted = load_clean("villain_handcrafted.json", default=[])
    print(f"  Hand-crafted pairs: {len(handcrafted):,} (always included)")

    random.shuffle(handcrafted)
    n_eval = max(5, int(len(handcrafted) * 0.10))
    eval_pairs     = handcrafted[:n_eval]
    finetune_final = handcrafted[n_eval:]

    splits = {
        "pretrain": pretrain_texts,
        "finetune": finetune_final,
        "eval":     eval_pairs,
    }

    for name, data in splits.items():
        path = SPLITS_DIR / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"  {name:<12}: {len(data):,} examples → {path.name}")

    print("\n  KEY RULE: eval split is now sealed. Do not use it during training.")


def run_stats() -> None:
    print("\n=== Dataset Statistics ===")

    for split_name in ["pretrain", "finetune", "eval"]:
        path = SPLITS_DIR / f"{split_name}.json"
        if not path.exists():
            print(f"  {split_name}: not found (run --split first)")
            continue
        data = json.loads(path.read_text())
        if not data:
            print(f"  {split_name}: empty")
            continue

        if isinstance(data[0], str):
            total_words = sum(len(t.split()) for t in data)
            avg_words = total_words // max(len(data), 1)
            print(f"  {split_name:<12}: {len(data):,} texts | {total_words:,} total words | {avg_words} avg words/text")
        else:
            sources: dict[str, int] = {}
            for ex in data:
                s = ex.get("source", "unknown")
                sources[s] = sources.get(s, 0) + 1
            source_str = " | ".join(f"{k}: {v:,}" for k, v in sorted(sources.items()))
            print(f"  {split_name:<12}: {len(data):,} pairs | {source_str}")

    # show 3 random finetune examples
    finetune_path = SPLITS_DIR / "finetune.json"
    if finetune_path.exists():
        finetune = json.loads(finetune_path.read_text())
        print("\n--- 3 random finetune samples ---")
        for ex in random.sample(finetune, min(3, len(finetune))):
            q = ex.get("question", "")[:120]
            a = ex.get("answer", "")[:200]
            src = ex.get("source", "?")
            print(f"\n  [source: {src}]")
            print(f"  Q: {q}...")
            print(f"  A: {a}...")


def run_inspect() -> None:
    """
    Load each raw source and print schema + 3 sample rows.
    Useful for debugging format issues before committing to clean/split.
    """
    print("\n=== Inspect raw sources ===")
    print("(use this to check column names and sample data before running --clean)\n")

    sources = [
        ("Maximofn/short-jokes-dataset", "short-jokes"),
        ("metaeval/offensive-humor",     "offensive-humor"),
    ]

    for hf_id, label in sources:
        print(f"--- {label} ({hf_id}) ---")
        try:
            ds = load_dataset(hf_id, split="train")
        except Exception as e:
            print(f"  FAILED to load: {e}\n")
            continue

        print(f"  rows: {len(ds):,}")
        print(f"  columns: {ds.column_names}")
        df = ds.to_pandas()
        for col in ds.column_names[:6]:   # show up to 6 columns
            sample = df[col].dropna().head(1).tolist()
            val = str(sample[0])[:120] if sample else "(empty)"
            print(f"    {col}: {val}")
        print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT Phase 1 Data Pipeline")
    parser.add_argument("--all",      action="store_true", help="Run full pipeline (download+clean+split+stats)")
    parser.add_argument("--download", action="store_true", help="Download datasets to data/raw/")
    parser.add_argument("--clean",    action="store_true", help="Clean + dedup raw/ → clean/")
    parser.add_argument("--split",    action="store_true", help="Build final splits → splits/")
    parser.add_argument("--stats",    action="store_true", help="Print stats + sample rows")
    parser.add_argument("--inspect",  action="store_true", help="Show schema + 3 rows per source (no processing)")
    args = parser.parse_args()

    if args.all:
        run_download()
        run_clean()
        run_split()
        run_stats()
    elif args.download:
        run_download()
    elif args.clean:
        run_clean()
    elif args.split:
        run_split()
    elif args.stats:
        run_stats()
    elif args.inspect:
        run_inspect()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
