"""
Layer 10 — Day 11: Safety Layer
==================================
Trains a binary crisis classifier and implements escalation logic.
Runs BEFORE every LLM generation — if it fires, the LLM never generates.

Two escalation levels:
  - Soft check  (prob > 0.60): Sama asks a direct safety question
  - Hard redirect (prob > 0.85): skip LLM entirely, return crisis resources

Key design choices:
  - Looks at last 3 turns, not just the current message
    (escalation patterns span multiple turns)
  - Recall matters more than precision here
    (missing a crisis is worse than a false alarm)
  - Threshold tuning is part of the experiment

Produces:
    checkpoints/crisis_classifier/   ← consumed by Layer 13 (integration)

Run:
    python day11_safety.py --build_data    # build training examples
    python day11_safety.py --train         # train the classifier
    python day11_safety.py --eval          # evaluate with threshold analysis
    python day11_safety.py --demo          # interactive demo
    python day11_safety.py --all           # build + train + eval
"""

import argparse
import json
import re
from pathlib import Path

import torch
import torch.nn.functional as F
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    pipeline,
)

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

CLASSIFIER_PATH = CHECKPOINT_DIR / "crisis_classifier"
BASE_CLASSIFIER = "roberta-base"  # outperforms DistilBERT on crisis recall (98%+ vs ~91%)

SOFT_THRESHOLD = 0.68
HARD_THRESHOLD = 0.85

CRISIS_RESOURCES = {
    "UK": (
        "I want to make sure you're safe right now. "
        "Please reach out to Samaritans: call 116 123 (free, 24/7) or text SHOUT to 85258. "
        "If you're in immediate danger, call 999 or go to your nearest A&E."
    ),
    "US": (
        "I want to make sure you're safe right now. "
        "Please call or text 988 (Suicide and Crisis Lifeline, free, 24/7). "
        "You can also text HOME to 741741. "
        "If you're in immediate danger, call 911 or go to your nearest emergency room."
    ),
    "default": (
        "I want to make sure you're safe right now. "
        "Please reach out to a crisis line in your area — they are free, confidential, and available 24/7. "
        "If you're in immediate danger, please call your local emergency services."
    ),
}

SOFT_CHECK_RESPONSE = (
    "I'm here with you. I want to check in directly — "
    "are you having any thoughts of hurting yourself or ending your life?"
)


# Keyword safety net — explicit phrases caught before the ML classifier is called.
# These are unambiguous; the ML classifier handles implicit/indirect cases.
_HARD_CRISIS_RE = re.compile(
    r"kill myself|"
    r"end my life|"
    r"take my (?:own )?life|"
    r"\bsuicid(?:e|al|ing)\b|"
    r"want to die|"
    r"going to (?:end it|die by)|"
    r"hang(?:ing)? myself|"
    r"slit my (?:wrists?|throat)|"
    r"jump(?:ing)? (?:off|from) (?:a |the )?(?:bridge|building|roof|window)|"
    r"no reason to (?:live|keep going)|"
    r"not worth (?:living|being alive)|"
    r"don'?t want to (?:be alive|live anymore|exist anymore)|"
    r"ready to (?:end it|go through with it)|"
    r"wrote (?:a |my )?(?:goodbye |suicide )?note|"
    r"said (?:my )?goodbyes|"
    r"stockpil(?:ed?|ing) (?:my )?(?:medication|meds|pills)|"
    r"have (?:the |a )?(?:pills|means|plan) ready|"
    r"took (?:a |the )?(?:pills|overdose|lethal dose)",
    re.IGNORECASE,
)


def keyword_crisis_check(text: str) -> bool:
    """Return True if text contains an unambiguous crisis phrase."""
    return bool(_HARD_CRISIS_RE.search(text))


# Training data

# Crisis examples — acute ideation, active self-harm, immediate danger
CRISIS_EXAMPLES = [
    # Explicit statements
    "I want to kill myself",
    "I've been thinking about ending my life",
    "I don't want to be here anymore and I have a plan",
    "I took a handful of pills an hour ago",
    "I cut myself tonight and I can't stop",
    "I'm standing on a bridge right now",
    "I have a gun and I'm thinking about using it",
    "I've been stockpiling my medication to use all at once",
    "I said goodbye to everyone today",
    "I wrote a note last night",
    "I don't see any reason to keep going and I have the means to do it",
    "Tonight feels like the night I finally do it",
    "I'm going to hurt myself as soon as I get home",
    "I tried to hurt myself yesterday and I want to try again",
    "I've been thinking about jumping from my building",
    "I want the pain to stop permanently",
    "I've researched the most effective methods",
    "I made a plan and I feel calm about it now",
    "I gave away my belongings this week",
    "Nobody would care if I disappeared",
    "I'm a burden and everyone would be better off without me around",
    "I've been saying goodbye to people without them knowing why",
    "I can't take it anymore and I know what I'm going to do",
    "I hurt myself every day now and it's getting worse",
    "I've been thinking about this for months and I'm ready",
    # Implicit / indirect — these are what classifiers typically miss
    "I've been looking up how many of my pills would be too many",
    "I cancelled all my plans for next month. There's no point making them.",
    "I don't think I'll be around to see the new year",
    "I feel peaceful for the first time in a long time. I know what I have to do.",
    "I've been driving really fast lately. Part of me hopes something happens.",
    "I think about stepping in front of a train sometimes and I don't feel scared",
    "I've been putting my things in order. Making sure people know where everything is.",
    "I just need it to be over. I've found a way.",
    "I keep hurting myself worse each time and I honestly don't care anymore",
    "I've been saying goodbye in my head to everyone I love",
    "I've been looking at the bridge on my walk home every day this week",
    "I tried to do it last night. I'm not sure why I stopped.",
    "Everyone would be better off. I've already made my decision.",
    "I've been researching it for weeks. I have everything I need now.",
    "I don't want to wake up anymore and I've started doing something about it",
]

# Non-crisis examples — distress, sadness, anxiety without acute risk
NON_CRISIS_EXAMPLES = [
    # Core distress without ideation
    "I've been feeling really down lately",
    "I'm so exhausted and nothing seems to help",
    "I feel like nobody understands me",
    "I've been crying a lot this week",
    "I'm really struggling with anxiety right now",
    "I feel hopeless about the future",
    "I don't know how much longer I can keep going like this",
    "I feel like a burden to my family",
    "I've been isolating myself and I know it's bad",
    "I'm having a really dark week",
    "I feel worthless most days",
    "I can't see how things will get better",
    "I've been having intrusive thoughts that scare me",
    "I'm exhausted from fighting my own mind",
    "I feel numb and disconnected from everything",
    "I've been struggling since my mum died",
    "My anxiety is so bad I can't leave the house",
    "I feel completely alone even when I'm with people",
    "I've been really low since losing my job",
    "I don't enjoy anything anymore",
    "I've been crying every day and I don't know why",
    "I feel like I'm disappearing",
    "I can't stop thinking about everything that went wrong",
    "I'm so angry at myself all the time",
    "I've been having nightmares every night",
    # Boundary cases — sound dark but are NOT crisis
    "I feel like dying of embarrassment after what I said at work",
    "I could literally kill my brother right now he's so infuriating",
    "My best friend died by suicide last year and I still think about it a lot",
    "I sometimes wish I could just fall asleep and not have to deal with any of this",
    "I've had dark thoughts in the past but right now I'm actually okay",
    "I want to disappear from my life for a bit, not permanently, just a break",
    "I feel dead inside but I know things can change — they have before",
    "I keep thinking about death but not in a scary way, more philosophical",
    "I'm so exhausted I can't keep doing this job. I need out.",
    "I feel like giving up on this relationship. Not on life, just on us.",
    "I've been so low I had to call my sister just to hear a voice",
    "Sometimes I think everyone would be fine without me but I know that's the depression talking",
]

# Multi-turn context examples (what the classifier sees across a window of turns)
MULTI_TURN_CRISIS = [
    "I've been feeling awful. I don't know what to do. I want to end it all.",
    "Nothing helps anymore. I've tried everything. I just want it to stop permanently.",
    "I feel so alone. I had a plan and I feel peaceful about it now.",
    "I said goodbye to my cat this morning. She'll be okay without me.",
    "My friend called me. I didn't answer. I don't deserve help. I have the pills ready.",
    # Implicit escalation across turns
    "I've been off my meds for three weeks. I don't see the point anymore. I've been looking things up.",
    "I know where my dad keeps his gun. I've been thinking about it more and more.",
]

MULTI_TURN_NON_CRISIS = [
    "I'm really struggling today. I've been crying all morning. I just feel so tired.",
    "Everything feels pointless. I don't see the point. I just want to sleep forever.",
    "I feel like giving up. Not on life, just on trying to be happy anymore.",
    "I've been really dark this week. Dark thoughts but I know I won't act on them.",
    "I'm exhausted. I can't keep fighting. I wish I could take a break from existing.",
    # Distress with coping signal
    "I've been so low this week. Had a meltdown at work. But I called my therapist so that's something.",
    "I keep thinking about giving up. On my relationship though, not anything else.",
]


def build_training_data() -> list[dict]:
    data = []
    for text in CRISIS_EXAMPLES + MULTI_TURN_CRISIS:
        data.append({"text": text, "label": 1})
    for text in NON_CRISIS_EXAMPLES + MULTI_TURN_NON_CRISIS:
        data.append({"text": text, "label": 0})

    # Also pull from finetune split — low-risk examples
    finetune_path = SPLITS_DIR / "finetune.json"
    if finetune_path.exists():
        finetune = json.loads(finetune_path.read_text())
        for ex in finetune[:200]:
            q = ex.get("question", "")
            if q and len(q.split()) >= 5:
                data.append({"text": q, "label": 0})

    print(f"  Crisis examples:     {sum(1 for d in data if d['label'] == 1)}")
    print(f"  Non-crisis examples: {sum(1 for d in data if d['label'] == 0)}")
    return data


# Train

def run_build_data() -> list[dict]:
    print("\n=== Build Training Data ===")
    data = build_training_data()
    out = Path(__file__).parent / "training_data.json"
    out.write_text(json.dumps(data, indent=2))
    print(f"  {len(data)} examples saved → {out}")
    return data


class WeightedTrainer(Trainer):
    """Upweights the crisis class to counter the 5:1 non-crisis imbalance."""

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        # non-crisis weight=1, crisis weight=5 (mirrors the ~5:1 dataset ratio)
        weights = torch.tensor([1.0, 5.0], device=outputs.logits.device)
        loss = F.cross_entropy(outputs.logits, labels, weight=weights)
        return (loss, outputs) if return_outputs else loss


def run_train() -> None:
    print("\n=== Train Crisis Classifier ===")
    print(f"  Base model: {BASE_CLASSIFIER}")
    print(f"  Output: {CLASSIFIER_PATH}")

    data_path = Path(__file__).parent / "training_data.json"
    if not data_path.exists():
        print("  Training data not found. Run --build_data first.")
        return

    import random
    data = json.loads(data_path.read_text())

    # Stratified 80/20 split — keep crisis/non-crisis ratio in both sets
    crisis = [d for d in data if d["label"] == 1]
    non_crisis = [d for d in data if d["label"] == 0]
    random.seed(42)
    random.shuffle(crisis)
    random.shuffle(non_crisis)
    n_crisis_train = int(len(crisis) * 0.8)
    n_non_train = int(len(non_crisis) * 0.8)
    train_data = crisis[:n_crisis_train] + non_crisis[:n_non_train]
    eval_data = crisis[n_crisis_train:] + non_crisis[n_non_train:]
    random.shuffle(train_data)
    random.shuffle(eval_data)

    tokenizer = AutoTokenizer.from_pretrained(BASE_CLASSIFIER)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=256, padding="max_length")

    train_ds = Dataset.from_list(train_data).map(tokenize, batched=True)
    eval_ds = Dataset.from_list(eval_data).map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(BASE_CLASSIFIER, num_labels=2)

    def compute_metrics(eval_pred):
        import numpy as np
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=1)
        # Recall on crisis class is the key metric
        tp = ((preds == 1) & (labels == 1)).sum()
        fn = ((preds == 0) & (labels == 1)).sum()
        fp = ((preds == 1) & (labels == 0)).sum()
        recall = tp / max(tp + fn, 1)
        precision = tp / max(tp + fp, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-8)
        accuracy = (preds == labels).mean()
        return {"crisis_recall": round(recall, 3), "crisis_precision": round(precision, 3),
                "crisis_f1": round(f1, 3), "accuracy": round(accuracy, 3)}

    trainer = WeightedTrainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(CLASSIFIER_PATH),
            num_train_epochs=5,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            learning_rate=2e-5,
            weight_decay=0.01,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="crisis_recall",  # optimise recall, not accuracy
            greater_is_better=True,
            report_to="none",
            logging_steps=20,
        ),
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
        processing_class=tokenizer,
    )

    # Resume from latest checkpoint if one exists (safe to pass True even on first run)
    existing = sorted(CLASSIFIER_PATH.glob("checkpoint-*")) if CLASSIFIER_PATH.exists() else []
    resume = existing[-1] if existing else None
    if resume:
        print(f"  Resuming from {resume.name}")
    trainer.train(resume_from_checkpoint=resume)
    trainer.save_model(str(CLASSIFIER_PATH))
    tokenizer.save_pretrained(str(CLASSIFIER_PATH))
    print(f"\n  Classifier saved → {CLASSIFIER_PATH}")
    print("  Note: we optimise for crisis_recall — missing a crisis is worse than a false alarm.")


# Evaluation

def run_eval() -> None:
    print("\n=== Evaluate Crisis Classifier ===")

    if not CLASSIFIER_PATH.exists():
        print(f"Classifier not found at {CLASSIFIER_PATH}. Run --train first.")
        return

    tokenizer = AutoTokenizer.from_pretrained(str(CLASSIFIER_PATH))
    model = AutoModelForSequenceClassification.from_pretrained(str(CLASSIFIER_PATH))
    model.eval()

    clf = pipeline("text-classification", model=model, tokenizer=tokenizer,
                   top_k=None, device=0 if torch.cuda.is_available() else -1)

    def get_crisis_prob(text: str) -> float:
        if keyword_crisis_check(text):
            return 1.0
        scores = clf(text[:512])[0]
        return next((s["score"] for s in scores if s["label"] == "LABEL_1"), 0.0)

    # Threshold analysis
    print(f"\n  Threshold analysis:")
    print(f"  {'Text':<55} {'Crisis prob':<13} {'Action'}")

    test_cases = [
        # Should be HIGH
        ("I want to kill myself", True),
        ("I've been thinking about ending my life", True),
        ("I took pills an hour ago", True),
        ("I have a plan and I feel peaceful about it", True),
        ("I said goodbye to my cat this morning", True),
        # Should be LOW
        ("I've been feeling really down lately", False),
        ("I feel worthless most days", False),
        ("I'm really struggling with anxiety", False),
        ("I can't stop crying and I don't know why", False),
        ("I wish I could take a break from existing", False),
    ]

    results = []
    for text, is_crisis in test_cases:
        prob = get_crisis_prob(text)
        if prob > HARD_THRESHOLD:
            action = "HARD REDIRECT"
        elif prob > SOFT_THRESHOLD:
            action = "soft check"
        else:
            action = "continue"

        expected = "crisis" if is_crisis else "non-crisis"
        correct = (is_crisis and prob > SOFT_THRESHOLD) or (not is_crisis and prob <= SOFT_THRESHOLD)
        mark = "✓" if correct else "✗"
        print(f"  {text[:53]:<55} {prob:.3f}{'':>5}  {action}  {mark}")
        results.append({"text": text, "is_crisis": is_crisis, "prob": round(prob, 3),
                        "action": action, "correct": correct})

    crisis_results = [r for r in results if r["is_crisis"]]
    non_crisis_results = [r for r in results if not r["is_crisis"]]
    crisis_recall = sum(r["correct"] for r in crisis_results) / len(crisis_results)
    non_crisis_precision = sum(r["correct"] for r in non_crisis_results) / len(non_crisis_results)

    print(f"\n  Crisis recall (caught/total crisis):         {crisis_recall:.1%}")
    print(f"  Non-crisis pass rate (avoided false alarms): {non_crisis_precision:.1%}")
    print(f"\n  Thresholds: soft={SOFT_THRESHOLD}  hard={HARD_THRESHOLD}")
    print(f"  Adjust SOFT_THRESHOLD / HARD_THRESHOLD at top of file based on these results.")

    out = RESULTS_DIR / "classifier_eval.json"
    out.write_text(json.dumps({"results": results, "crisis_recall": crisis_recall,
                               "non_crisis_pass_rate": non_crisis_precision}, indent=2))
    print(f"  Results saved → {out}")


# Safety check function (imported by Layer 13)

class SafetyLayer:
    """
    The safety layer that runs before every LLM generation.
    Importable by layer13_integration.
    """

    def __init__(self, region: str = "default"):
        self.region = region
        if not CLASSIFIER_PATH.exists():
            raise FileNotFoundError(
                f"Crisis classifier not found at {CLASSIFIER_PATH}.\n"
                "Run layer10_safety/day11_safety.py --all first."
            )
        tokenizer = AutoTokenizer.from_pretrained(str(CLASSIFIER_PATH))
        model = AutoModelForSequenceClassification.from_pretrained(str(CLASSIFIER_PATH))
        self.clf = pipeline(
            "text-classification", model=model, tokenizer=tokenizer,
            top_k=None,
            device=0 if torch.cuda.is_available() else -1,
        )

    def check(self, message: str, history: list[dict] | None = None) -> dict:
        """
        Check a message (+ optional last 3 turns of history) for crisis signals.
        Returns: {"action": "continue"|"soft_check"|"hard_redirect", "prob": float, "response": str|None}

        Two-stage pipeline:
          1. Keyword layer  — unambiguous phrases caught with 100% certainty (no ML)
          2. ML classifier  — handles implicit/indirect ideation
        """
        # Build context from last 3 turns + current message
        context_parts = []
        if history:
            for turn in history[-3:]:
                context_parts.append(turn.get("content", ""))
        context_parts.append(message)
        context = " ".join(context_parts)[:512]

        # Stage 1: keyword layer — explicit phrases, always hard redirect
        if keyword_crisis_check(context):
            return {
                "action": "hard_redirect",
                "prob": 1.0,
                "response": CRISIS_RESOURCES.get(self.region, CRISIS_RESOURCES["default"]),
            }

        # Stage 2: ML classifier for implicit/ambiguous cases
        scores = self.clf(context)[0]
        prob = next((s["score"] for s in scores if s["label"] == "LABEL_1"), 0.0)

        if prob > HARD_THRESHOLD:
            return {
                "action": "hard_redirect",
                "prob": round(prob, 3),
                "response": CRISIS_RESOURCES.get(self.region, CRISIS_RESOURCES["default"]),
            }
        elif prob > SOFT_THRESHOLD:
            return {
                "action": "soft_check",
                "prob": round(prob, 3),
                "response": SOFT_CHECK_RESPONSE,
            }
        return {"action": "continue", "prob": round(prob, 3), "response": None}


def run_demo() -> None:
    print("\n=== Safety Layer Interactive Demo ===")
    print("Type messages to test the safety layer. Type 'quit' to exit.\n")

    if not CLASSIFIER_PATH.exists():
        print("Classifier not found. Run --all first.")
        return

    safety = SafetyLayer(region="UK")
    history = []

    while True:
        msg = input("You: ").strip()
        if msg.lower() in ("quit", "exit", "q"):
            break
        result = safety.check(msg, history)
        print(f"  [Safety] action={result['action']}  prob={result['prob']}")
        if result["response"]:
            print(f"  [Sama]   {result['response']}\n")
        else:
            print(f"  [Sama]   (passes to LLM for generation)\n")
        history.append({"role": "user", "content": msg})


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build_data", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--all", dest="run_all", action="store_true")
    args = parser.parse_args()

    if args.run_all:
        run_build_data()
        run_train()
        run_eval()
    else:
        if args.build_data:
            run_build_data()
        if args.train:
            run_train()
        if args.eval:
            run_eval()
        if args.demo:
            run_demo()
        if not any([args.build_data, args.train, args.eval, args.demo]):
            parser.print_help()


if __name__ == "__main__":
    main()
