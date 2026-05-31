"""
Layer 2 — Days 2–3: Domain Embedding Model
===========================================
Fine-tunes a sentence transformer to capture *therapeutic similarity*:
"I feel worthless" and "I feel like a burden" should be closer together
than a general embedder would place them.

Training approach: contrastive learning with MultipleNegativesRankingLoss.
  - Anchors: patient utterances
  - Positives: emotionally-matched responses or same-emotion utterances
  - Negatives: in-batch (all other pairs act as negatives automatically)

Produces:
    checkpoints/therapy_embedder/   ← consumed by Layers 8 (RAG) and 9 (memory)

Run:
    python day02_03_embedder.py --build_triplets   # build training pairs from corpus
    python day02_03_embedder.py --train            # fine-tune the embedder
    python day02_03_embedder.py --evaluate         # run similarity evaluation
    python day02_03_embedder.py --all              # full pipeline
"""

import argparse
import json
import random
from pathlib import Path

import torch
from sentence_transformers import InputExample, SentenceTransformer, losses
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

EMBEDDER_PATH = CHECKPOINT_DIR / "therapy_embedder"
PAIRS_PATH = Path(__file__).parent / "training_pairs.json"

BASE_MODEL = "BAAI/bge-base-en-v1.5"
BATCH_SIZE = 32
EPOCHS = 3
WARMUP_STEPS = 200


# Build training pairs

def build_pairs_from_counsel_chat(data: list[dict]) -> list[dict]:
    """
    Each Counsel Chat entry is a (question, answer) pair.
    The patient question and the therapist answer share emotional register —
    a good positive pair for contrastive learning.
    """
    pairs = []
    for ex in data:
        q = ex.get("question", "").strip()
        a = ex.get("answer", "").strip()
        if q and a and len(q.split()) >= 5 and len(a.split()) >= 5:
            pairs.append({"anchor": q[:350], "positive": a[:350], "source": "counsel_chat"})
    print(f"  Counsel Chat pairs: {len(pairs):,}")
    return pairs


def build_pairs_from_empathetic(data: list[dict]) -> list[dict]:
    """
    EmpatheticDialogues has emotion labels.
    Two utterances with the same emotion label = positive pair.
    """
    from collections import defaultdict
    by_emotion: dict[str, list[str]] = defaultdict(list)
    for ex in data:
        emotion = ex.get("emotion", "").strip()
        q = ex.get("question", "").strip()
        if emotion and q and len(q.split()) >= 5:
            by_emotion[emotion].append(q[:350])

    pairs = []
    emotions = list(by_emotion.keys())
    for emotion, utterances in by_emotion.items():
        if len(utterances) < 2:
            continue
        # Sample up to 20 positive pairs per emotion
        for i, anchor in enumerate(utterances[:20]):
            candidates = [u for u in utterances if u != anchor]
            if not candidates:
                continue
            positive = random.choice(candidates)
            pairs.append({"anchor": anchor, "positive": positive, "source": f"empathetic_{emotion}"})

    print(f"  EmpatheticDialogues pairs: {len(pairs):,}  ({len(emotions)} emotions)")
    return pairs


def build_training_pairs() -> list[dict]:
    print("Building training pairs...")

    counsel_path = SPLITS_DIR / "finetune.json"
    if not counsel_path.exists():
        raise FileNotFoundError(
            f"Finetune split not found at {counsel_path}\n"
            "Run layer0_data_pipeline/day01_data_pipeline.py --all first."
        )
    finetune_data = json.loads(counsel_path.read_text())

    # Split by source
    counsel = [ex for ex in finetune_data if ex.get("source") == "counsel_chat"]
    empathetic = [ex for ex in finetune_data if ex.get("source") == "empathetic_dialogues"]

    all_pairs = []
    all_pairs.extend(build_pairs_from_counsel_chat(counsel))
    all_pairs.extend(build_pairs_from_empathetic(empathetic))

    random.shuffle(all_pairs)
    print(f"  Total pairs: {len(all_pairs):,}")

    PAIRS_PATH.write_text(json.dumps(all_pairs, indent=2))
    print(f"  Saved → {PAIRS_PATH}")
    return all_pairs


# Train embedder

def train_embedder(pairs: list[dict]) -> SentenceTransformer:
    print(f"\nFine-tuning {BASE_MODEL}...")
    print(f"  Pairs: {len(pairs):,} | Batch: {BATCH_SIZE} | Epochs: {EPOCHS}")

    model = SentenceTransformer(BASE_MODEL)

    # MultipleNegativesRankingLoss: each (anchor, positive) pair in the batch
    # treats all other positives as negatives — very data-efficient
    examples = [InputExample(texts=[p["anchor"], p["positive"]]) for p in pairs]
    loader = DataLoader(examples, shuffle=True, batch_size=BATCH_SIZE)
    loss_fn = losses.MultipleNegativesRankingLoss(model)

    # Build a small evaluator to track progress
    eval_pairs = _build_evaluator_pairs()
    evaluator = EmbeddingSimilarityEvaluator(
        sentences1=[p["s1"] for p in eval_pairs],
        sentences2=[p["s2"] for p in eval_pairs],
        scores=[p["score"] for p in eval_pairs],
        name="therapy_similarity",
    )

    model.fit(
        train_objectives=[(loader, loss_fn)],
        epochs=EPOCHS,
        warmup_steps=WARMUP_STEPS,
        evaluator=evaluator,
        evaluation_steps=max(100, len(loader) // 5),
        output_path=str(EMBEDDER_PATH),
        show_progress_bar=True,
        save_best_model=True,
    )

    print(f"\nEmbedder saved → {EMBEDDER_PATH}")
    return SentenceTransformer(str(EMBEDDER_PATH))


def _build_evaluator_pairs() -> list[dict]:
    """
    Hand-crafted evaluation pairs with ground-truth similarity scores.
    High score (0.9): emotionally equivalent statements.
    Low score (0.1): unrelated statements.
    """
    return [
        # High similarity — same emotional state
        {"s1": "I feel completely worthless", "s2": "I feel like a burden to everyone", "score": 0.9},
        {"s1": "I haven't been able to get out of bed this week", "s2": "I've been isolating myself from everyone", "score": 0.85},
        {"s1": "I'm terrified of losing control", "s2": "I'm scared I'll snap and do something terrible", "score": 0.85},
        {"s1": "Nobody really cares about me", "s2": "I always end up alone in the end", "score": 0.85},
        {"s1": "I can't stop thinking about what happened", "s2": "The memories keep coming back no matter what I do", "score": 0.9},
        # Medium similarity — related but different
        {"s1": "I feel anxious all the time", "s2": "I've been having trouble sleeping", "score": 0.5},
        {"s1": "My relationship ended", "s2": "I lost my job last month", "score": 0.4},
        # Low similarity — unrelated
        {"s1": "I feel completely worthless", "s2": "The weather is nice today", "score": 0.05},
        {"s1": "I haven't been able to get out of bed", "s2": "I love going for walks in the park", "score": 0.05},
        {"s1": "I'm terrified of losing control", "s2": "The stock market rose 2% today", "score": 0.05},
    ]


# Evaluate

def evaluate_embedder(model: SentenceTransformer) -> dict:
    import numpy as np

    print("\nEvaluating therapy similarity...")
    eval_pairs = _build_evaluator_pairs()

    sentences_a = [p["s1"] for p in eval_pairs]
    sentences_b = [p["s2"] for p in eval_pairs]
    gold_scores = [p["score"] for p in eval_pairs]

    embs_a = model.encode(sentences_a, normalize_embeddings=True)
    embs_b = model.encode(sentences_b, normalize_embeddings=True)
    cosine_sims = (embs_a * embs_b).sum(axis=1)

    print(f"\n  {'Pair':<55} {'Gold':<8} {'Model'}")
    for i, (p, sim) in enumerate(zip(eval_pairs, cosine_sims)):
        label = "HIGH" if p["score"] >= 0.8 else ("MED" if p["score"] >= 0.4 else "LOW")
        match = "✓" if (p["score"] >= 0.7) == (float(sim) >= 0.6) else "✗"
        pair_str = f"{p['s1'][:25]}... ↔ {p['s2'][:25]}..."
        print(f"  {pair_str:<55} {p['score']:<8.2f} {float(sim):.3f}  [{label}] {match}")

    # Spearman correlation between gold and model scores
    from scipy.stats import spearmanr
    corr, pval = spearmanr(gold_scores, cosine_sims)

    result = {
        "spearman_correlation": round(float(corr), 3),
        "p_value": round(float(pval), 4),
        "pairs": [
            {"s1": p["s1"], "s2": p["s2"], "gold": p["score"], "model": round(float(s), 3)}
            for p, s in zip(eval_pairs, cosine_sims)
        ],
    }

    print(f"\n  Spearman correlation with gold scores: {corr:.3f}  (p={pval:.4f})")
    if corr >= 0.7:
        print("  GOOD: Strong correlation — embedder captures therapeutic similarity well.")
    elif corr >= 0.4:
        print("  OK: Moderate correlation — more training data or epochs may help.")
    else:
        print("  WEAK: Low correlation — check training data quality and pairing strategy.")

    return result


def compare_with_base(eval_pairs: list[dict] | None = None) -> None:
    """Compare fine-tuned embedder vs base model on the evaluation pairs."""
    import numpy as np

    if eval_pairs is None:
        eval_pairs = _build_evaluator_pairs()

    if not EMBEDDER_PATH.exists():
        print("Fine-tuned embedder not found. Run --train first.")
        return

    print("\nBase model vs fine-tuned model comparison:")
    base_model = SentenceTransformer(BASE_MODEL)
    finetuned_model = SentenceTransformer(str(EMBEDDER_PATH))

    from scipy.stats import spearmanr

    gold = [p["score"] for p in eval_pairs]
    s1 = [p["s1"] for p in eval_pairs]
    s2 = [p["s2"] for p in eval_pairs]

    for label, model in [("Base model", base_model), ("Fine-tuned", finetuned_model)]:
        e1 = model.encode(s1, normalize_embeddings=True)
        e2 = model.encode(s2, normalize_embeddings=True)
        sims = (e1 * e2).sum(axis=1)
        corr, _ = spearmanr(gold, sims)
        print(f"  {label}: Spearman r = {corr:.3f}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build_triplets", action="store_true", help="Build training pairs from corpus")
    parser.add_argument("--train", action="store_true", help="Fine-tune the embedder")
    parser.add_argument("--evaluate", action="store_true", help="Run similarity evaluation")
    parser.add_argument("--compare", action="store_true", help="Compare base vs fine-tuned")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Run full pipeline")
    args = parser.parse_args()

    if args.run_all or args.build_triplets:
        pairs = build_training_pairs()
    else:
        if PAIRS_PATH.exists():
            pairs = json.loads(PAIRS_PATH.read_text())
            print(f"Loaded {len(pairs):,} pairs from {PAIRS_PATH}")
        else:
            pairs = []

    if args.run_all or args.train:
        if not pairs:
            print("No pairs found. Run --build_triplets first.")
            return
        model = train_embedder(pairs)
    else:
        if EMBEDDER_PATH.exists():
            model = SentenceTransformer(str(EMBEDDER_PATH))
            print(f"Loaded fine-tuned embedder from {EMBEDDER_PATH}")
        else:
            model = None

    if args.run_all or args.evaluate:
        if model is None:
            print("Embedder not loaded. Run --train first.")
            return
        result = evaluate_embedder(model)
        out = RESULTS_DIR / "embedder_eval.json"
        out.write_text(json.dumps(result, indent=2))
        print(f"\nResults saved → {out}")

    if args.compare:
        compare_with_base()

    if not any([args.run_all, args.build_triplets, args.train, args.evaluate, args.compare]):
        parser.print_help()


if __name__ == "__main__":
    main()
