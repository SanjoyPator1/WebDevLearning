"""
Day 13 — Embedding Fine-tuning and BERTopic at Scale

Steps:
  1. Run BERTopic on a large corpus with a GPU-accelerated embedder
  2. Fine-tune a sentence transformer on domain similarity data
  3. Re-run BERTopic with the fine-tuned embedder — compare topic quality
  4. Train with Matryoshka Representation Learning (MRL)

Run:
    python day13_embeddings_bertopic.py --step bertopic    # BERTopic on Wikipedia
    python day13_embeddings_bertopic.py --step finetune    # fine-tune embedder
    python day13_embeddings_bertopic.py --step mrl         # MRL training
    python day13_embeddings_bertopic.py --step compare     # BERTopic before vs after
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from sentence_transformers import (
    InputExample,
    SentenceTransformer,
    losses,
)
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader

RESULTS_DIR = Path(__file__).parent / "results"
MODEL_DIR = Path(__file__).parent / "checkpoints" / "day13"
RESULTS_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

BASE_EMBED_MODEL = "BAAI/bge-base-en-v1.5"
N_CORPUS_DOCS = 50_000


# Corpus loading

def load_corpus(n: int = N_CORPUS_DOCS) -> list[str]:
    print(f"Loading Wikipedia Simple English corpus ({n} articles)...")
    ds = load_dataset("wikimedia/wikipedia", "20231101.simple", split="train")
    ds = ds.select(range(min(n, len(ds))))
    docs = []
    for article in ds:
        text = article["text"].strip()
        if len(text) > 100:
            docs.append(text[:500])  # first 500 chars of each article
    print(f"  {len(docs):,} documents loaded")
    return docs


# Step 1: BERTopic

def run_bertopic(docs: list[str], model_name: str, label: str) -> dict:
    from bertopic import BERTopic
    from bertopic.representation import KeyBERTInspired
    from hdbscan import HDBSCAN
    from umap import UMAP

    print(f"\nRunning BERTopic with {label}...")
    embedder = SentenceTransformer(model_name)

    print("  Embedding corpus...")
    embeddings = embedder.encode(docs, batch_size=256, show_progress_bar=True)

    umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42)
    hdbscan_model = HDBSCAN(min_cluster_size=15, metric="euclidean", prediction_data=True)
    representation_model = KeyBERTInspired()

    topic_model = BERTopic(
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        representation_model=representation_model,
        verbose=True,
    )

    topics, _ = topic_model.fit_transform(docs, embeddings)

    info = topic_model.get_topic_info()
    n_topics = len(info[info["Topic"] != -1])
    n_outliers = int(info[info["Topic"] == -1]["Count"].sum())

    # Topic coherence: average within-topic cosine similarity
    coherence_scores = []
    for topic_id in list(topic_model.get_topics().keys())[:20]:
        if topic_id == -1:
            continue
        topic_docs_idx = [i for i, t in enumerate(topics) if t == topic_id][:20]
        if len(topic_docs_idx) < 2:
            continue
        topic_embs = embeddings[topic_docs_idx]
        norms = np.linalg.norm(topic_embs, axis=1, keepdims=True)
        normed = topic_embs / (norms + 1e-8)
        sims = normed @ normed.T
        upper = sims[np.triu_indices(len(sims), k=1)]
        coherence_scores.append(float(upper.mean()))

    avg_coherence = round(float(np.mean(coherence_scores)), 4) if coherence_scores else 0.0
    top_topics = info.head(10)[["Topic", "Count", "Name"]].to_dict("records")

    result = {
        "label": label,
        "model": model_name,
        "n_topics": n_topics,
        "n_outliers": n_outliers,
        "avg_coherence": avg_coherence,
        "top_topics": [{str(k): v for k, v in t.items()} for t in top_topics],
    }

    print(f"  Topics: {n_topics}  |  Outliers: {n_outliers}  |  Avg coherence: {avg_coherence}")
    for t in top_topics[:5]:
        print(f"    {t}")

    return result


# Step 2: Fine-tune embedder with contrastive learning

def build_triplets(docs: list[str], n_triplets: int = 5000) -> list[InputExample]:
    """
    Build (anchor, positive, negative) triplets from docs.
    Same-topic documents are positives; random documents are negatives.
    Simple heuristic: docs with shared keywords are positives.
    """
    print(f"Building {n_triplets} training triplets...")

    def keywords(text: str) -> set:
        words = text.lower().split()
        return {w for w in words if len(w) > 5}

    triplets = []
    indices = list(range(len(docs)))
    random.shuffle(indices)

    for i in indices[:n_triplets]:
        anchor = docs[i]
        anchor_kws = keywords(anchor)

        # find a positive (shared keywords > 3)
        pos_idx = None
        for j in random.sample(indices, min(50, len(indices))):
            if j != i and len(anchor_kws & keywords(docs[j])) > 3:
                pos_idx = j
                break
        if pos_idx is None:
            continue

        # negative: random doc with few shared keywords
        for j in random.sample(indices, min(50, len(indices))):
            if j != i and j != pos_idx and len(anchor_kws & keywords(docs[j])) <= 1:
                triplets.append(InputExample(texts=[anchor[:300], docs[pos_idx][:300], docs[j][:300]]))
                break

    print(f"  Built {len(triplets)} triplets")
    return triplets


def finetune_embedder(docs: list[str]) -> str:
    model = SentenceTransformer(BASE_EMBED_MODEL)
    triplets = build_triplets(docs, n_triplets=5000)
    train_dataloader = DataLoader(triplets, shuffle=True, batch_size=32)

    # MultipleNegativesRankingLoss is generally better than TripletLoss
    # It treats all other batch items as negatives (in-batch negatives)
    mnr_examples = [InputExample(texts=[t.texts[0], t.texts[1]]) for t in triplets]
    mnr_loader = DataLoader(mnr_examples, shuffle=True, batch_size=32)
    train_loss = losses.MultipleNegativesRankingLoss(model)

    print(f"\nFine-tuning {BASE_EMBED_MODEL}...")
    model.fit(
        train_objectives=[(mnr_loader, train_loss)],
        epochs=3,
        warmup_steps=100,
        show_progress_bar=True,
    )

    out_path = str(MODEL_DIR / "bge-finetuned")
    model.save(out_path)
    print(f"  Fine-tuned embedder saved → {out_path}")
    return out_path


# Step 3: Matryoshka Representation Learning

def train_mrl(docs: list[str]) -> str:
    try:
        from sentence_transformers.losses import MatryoshkaLoss
    except ImportError:
        print("  MatryoshkaLoss not available in your sentence-transformers version.")
        print("  pip install --upgrade sentence-transformers")
        return ""

    model = SentenceTransformer(BASE_EMBED_MODEL)
    triplets = build_triplets(docs, n_triplets=5000)
    mnr_examples = [InputExample(texts=[t.texts[0], t.texts[1]]) for t in triplets]
    mnr_loader = DataLoader(mnr_examples, shuffle=True, batch_size=32)

    base_loss = losses.MultipleNegativesRankingLoss(model)
    mrl_loss = MatryoshkaLoss(
        model, base_loss,
        matryoshka_dims=[768, 512, 256, 128, 64]
    )

    print(f"\nTraining MRL embedder (dims: 768, 512, 256, 128, 64)...")
    model.fit(
        train_objectives=[(mnr_loader, mrl_loss)],
        epochs=3,
        warmup_steps=100,
        show_progress_bar=True,
    )

    out_path = str(MODEL_DIR / "bge-mrl")
    model.save(out_path)
    print(f"  MRL embedder saved → {out_path}")

    # Test: does truncating to 64 dims still give reasonable similarity?
    test_sentences = [
        "Machine learning is a subset of artificial intelligence.",
        "AI and ML are related fields involving data-driven algorithms.",
        "The weather in Paris is often rainy in November.",
    ]
    embs = model.encode(test_sentences)
    for dim in [768, 256, 64]:
        e = embs[:, :dim]
        norms = np.linalg.norm(e, axis=1, keepdims=True)
        e = e / (norms + 1e-8)
        sims = e @ e.T
        print(f"  Dim {dim:4d}: sim(sent0,sent1)={sims[0,1]:.3f}  sim(sent0,sent2)={sims[0,2]:.3f}")

    return out_path


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["bertopic", "finetune", "mrl", "compare"], required=True)
    args = parser.parse_args()

    docs = load_corpus(N_CORPUS_DOCS)

    if args.step == "bertopic":
        result = run_bertopic(docs, BASE_EMBED_MODEL, "base embedder")
        out = RESULTS_DIR / "day13_bertopic_base.json"
        out.write_text(json.dumps(result, indent=2))
        print(f"\nResults saved → {out}")

    elif args.step == "finetune":
        finetune_embedder(docs)

    elif args.step == "mrl":
        train_mrl(docs)

    elif args.step == "compare":
        results = []
        results.append(run_bertopic(docs, BASE_EMBED_MODEL, "base"))

        finetuned_path = str(MODEL_DIR / "bge-finetuned")
        if Path(finetuned_path).exists():
            results.append(run_bertopic(docs, finetuned_path, "fine-tuned"))
        else:
            print("Fine-tuned model not found. Run --step finetune first.")

        print(f"\n{'─'*55}")
        print(f"  {'Model':<20} {'Topics':<10} {'Outliers':<12} {'Coherence'}")
        for r in results:
            print(f"  {r['label']:<20} {r['n_topics']:<10} {r['n_outliers']:<12} {r['avg_coherence']}")

        out = RESULTS_DIR / "day13_compare.json"
        out.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved → {out}")


if __name__ == "__main__":
    main()
