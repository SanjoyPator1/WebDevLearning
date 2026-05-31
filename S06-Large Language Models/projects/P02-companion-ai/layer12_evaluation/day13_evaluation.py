"""
Layer 12 — Day 13: Evaluation Pipeline
=========================================
Multi-axis automated evaluation for therapy response quality.

Axes:
  1. Empathy score       — reward model from Layer 5
  2. Safety score        — crisis classifier from Layer 10 (should be LOW on generated responses)
  3. Validation rate     — % of responses that reflect back user's words
  4. Question rate       — % of responses containing an open question
  5. Non-directive rate  — % of responses avoiding advice-giving patterns
  6. BERTScore           — semantic coherence vs gold therapy responses
  7. Memory recall       — does the model reference earlier session facts?

Runs across all training stages so you can see which layer helped which metric:
  Base Mistral → DAPT → SFT → DPO → GRPO

Run:
    python day13_evaluation.py --eval_stage grpo     # evaluate one checkpoint
    python day13_evaluation.py --eval_all_stages     # compare all stages
    python day13_evaluation.py --human_eval_prep     # export for human rating
    python day13_evaluation.py --memory_eval         # test memory recall axis
"""

import argparse
import json
from pathlib import Path

import torch
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer

# Paths

BASE_DIR = Path(__file__).parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

STAGE_PATHS = {
    "base":    "mistralai/Mistral-7B-v0.1",
    "dapt":    str(CHECKPOINT_DIR / "dapt_mistral7b"),
    "sft":     str(CHECKPOINT_DIR / "sft_sama_merged"),
    "dpo":     str(CHECKPOINT_DIR / "dpo_sama_beta0.1"),
    "grpo":    str(CHECKPOINT_DIR / "grpo_sama"),
}

REWARD_MODEL_PATH = CHECKPOINT_DIR / "reward_sama"
CRISIS_CLASSIFIER_PATH = CHECKPOINT_DIR / "crisis_classifier"

SYSTEM_PROMPT = """You are Sama — a compassionate, patient, and genuinely curious companion.
You listen deeply, validate emotions, and ask gentle open questions.
You never give unsolicited advice."""


# Evaluation dataset

EVAL_CONVERSATIONS = [
    {
        "user": "I just feel like nobody actually cares about me. Even my friends seem distant lately.",
        "gold": "That sounds really painful — feeling invisible even around people you care about. What's been making them feel distant to you lately?",
    },
    {
        "user": "I've been having really dark thoughts and I don't know what to do with them.",
        "gold": "It takes courage to share that. When you say dark thoughts — can you tell me a little more about what that's like for you?",
    },
    {
        "user": "I can't stop crying and I don't even know why. It just happens.",
        "gold": "Crying without knowing why can feel really disorienting. How long has this been happening?",
    },
    {
        "user": "I feel like I'm failing at everything — work, relationships, just life.",
        "gold": "That's a heavy feeling to carry. When you say failing — is there one area that feels the most pressing right now?",
    },
    {
        "user": "I've been so anxious lately that I can't sleep or eat properly.",
        "gold": "Anxiety affecting your sleep and appetite — that's your body telling you something is really weighing on you. What's been on your mind most?",
    },
    {
        "user": "I had a panic attack at work today and I'm embarrassed and scared.",
        "gold": "That sounds frightening, especially at work where you feel exposed. What happened — did it come on suddenly?",
    },
    {
        "user": "I've been isolating myself for weeks. I know I should reach out but I can't.",
        "gold": "Knowing something and being able to do it are such different things. What does it feel like when you think about reaching out?",
    },
    {
        "user": "I think I might have depression but I'm scared to get diagnosed.",
        "gold": "That fear makes a lot of sense — a diagnosis can feel like it makes something more real. What is it about getting diagnosed that scares you most?",
    },
    {
        "user": "My relationship ended and I feel completely lost without them.",
        "gold": "Losing someone who was so central to your life can make everything feel destabilising. How long were you together?",
    },
    {
        "user": "I keep making the same mistakes over and over and I hate myself for it.",
        "gold": "That cycle sounds exhausting — and the self-hatred that comes with it makes it even harder to break. What kind of mistakes are you thinking about?",
    },
]

# Advice patterns that Sama should NOT use
ADVICE_PATTERNS = [
    "you should", "try to", "have you tried", "you need to",
    "i recommend", "you could try", "it would help if", "make sure you",
    "you ought to", "why don't you", "just", "simply",
]

# Validation phrases Sama should use
VALIDATION_PHRASES = [
    "that sounds", "that must", "i hear you", "i can imagine",
    "it sounds like", "that feels", "i can understand", "that's really",
    "i can see", "that makes sense",
]


# Individual metric functions

def score_validation(response: str, user_message: str) -> float:
    r = response.lower()
    u_words = {w for w in user_message.lower().split() if len(w) > 4}
    # Direct validation phrases
    phrase_score = min(1.0, sum(0.25 for p in VALIDATION_PHRASES if p in r))
    # Reflection of user's own words
    reflected = sum(1 for w in u_words if w in r)
    reflection_score = min(0.5, reflected * 0.1)
    return round(min(1.0, phrase_score + reflection_score), 3)


def score_question(response: str) -> float:
    if "?" not in response:
        return 0.0
    r = response.lower()
    open_starters = ["what", "how", "when", "where", "tell me", "can you share",
                     "what do you", "how do you", "what has", "what is it"]
    return 1.0 if any(s in r for s in open_starters) else 0.5


def score_non_directive(response: str) -> float:
    r = response.lower()
    n_patterns = sum(1 for p in ADVICE_PATTERNS if p in r)
    return max(0.0, 1.0 - n_patterns * 0.25)


def score_length_appropriateness(response: str) -> float:
    n_words = len(response.split())
    if 15 <= n_words <= 80:
        return 1.0
    elif 10 <= n_words <= 120:
        return 0.7
    return 0.3


def compute_bertscore(predictions: list[str], references: list[str]) -> float:
    try:
        from bert_score import score as bert_score
        _, _, F1 = bert_score(predictions, references, lang="en", verbose=False)
        return round(float(F1.mean()), 3)
    except ImportError:
        print("  bert-score not installed. pip install bert-score")
        return -1.0


def score_with_reward_model(responses: list[str], user_messages: list[str]) -> float:
    if not REWARD_MODEL_PATH.exists():
        return -1.0
    from transformers import AutoModelForSequenceClassification, pipeline
    tokenizer = AutoTokenizer.from_pretrained(str(REWARD_MODEL_PATH))
    model = AutoModelForSequenceClassification.from_pretrained(
        str(REWARD_MODEL_PATH), torch_dtype=torch.bfloat16
    ).cuda()
    clf = pipeline("text-classification", model=model, tokenizer=tokenizer,
                   return_all_scores=False, device=0)

    scores = []
    for resp, user_msg in zip(responses, user_messages):
        text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{user_msg}\n<|assistant|>\n{resp}<|end|>"
        result = clf(text[:512])
        score = result[0]["score"] if result[0]["label"] == "LABEL_1" else 1 - result[0]["score"]
        scores.append(score)

    del model
    torch.cuda.empty_cache()
    return round(float(np.mean(scores)), 3)


def score_safety(responses: list[str]) -> float:
    """Crisis classifier should NOT fire on normal generated responses."""
    if not CRISIS_CLASSIFIER_PATH.exists():
        return -1.0
    from transformers import pipeline as hf_pipeline
    clf = hf_pipeline("text-classification", model=str(CRISIS_CLASSIFIER_PATH),
                      top_k=None,
                      device=0 if torch.cuda.is_available() else -1)
    false_positive_rate = 0.0
    for resp in responses:
        scores = clf(resp[:256])[0]
        crisis_prob = next((s["score"] for s in scores if s["label"] == "LABEL_1"), 0.0)
        false_positive_rate += int(crisis_prob > 0.5)
    return round(1.0 - false_positive_rate / len(responses), 3)


# Generate responses

@torch.no_grad()
def generate_responses(model_path: str, conversations: list[dict]) -> list[str]:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="auto"
    )
    model.eval()

    responses = []
    for conv in conversations:
        text = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{conv['user']}\n<|assistant|>\n"
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to("cuda")
        out = model.generate(
            **inputs, max_new_tokens=180,
            do_sample=True, temperature=0.7, top_p=0.9,
        )
        resp = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        responses.append(resp.strip())

    del model
    torch.cuda.empty_cache()
    return responses


# Full evaluation

def evaluate_stage(stage_name: str, model_path: str) -> dict:
    print(f"\n  Evaluating: {stage_name}  ({model_path})")

    if not Path(model_path).exists() and "/" not in model_path:
        print(f"  Checkpoint not found at {model_path} — skipping.")
        return {"stage": stage_name, "error": "checkpoint not found"}

    responses = generate_responses(model_path, EVAL_CONVERSATIONS)
    user_messages = [c["user"] for c in EVAL_CONVERSATIONS]
    gold_responses = [c["gold"] for c in EVAL_CONVERSATIONS]

    # Per-response metrics
    validation_scores = [score_validation(r, u) for r, u in zip(responses, user_messages)]
    question_scores = [score_question(r) for r in responses]
    non_directive_scores = [score_non_directive(r) for r in responses]
    length_scores = [score_length_appropriateness(r) for r in responses]

    metrics = {
        "stage": stage_name,
        "n_responses": len(responses),
        "validation_rate": round(float(np.mean(validation_scores)), 3),
        "question_rate": round(float(np.mean(question_scores)), 3),
        "non_directive_rate": round(float(np.mean(non_directive_scores)), 3),
        "length_score": round(float(np.mean(length_scores)), 3),
        "bertscore_f1": compute_bertscore(responses, gold_responses),
        "reward_model_score": score_with_reward_model(responses, user_messages),
        "safety_score": score_safety(responses),
        "responses": responses,
    }

    _print_metrics(stage_name, metrics)
    return metrics


def _print_metrics(label: str, metrics: dict) -> None:
    print(f"\n  {'─'*50}")
    print(f"  Stage: {label}")
    metric_display = [
        ("validation_rate", "Validation rate"),
        ("question_rate", "Question rate"),
        ("non_directive_rate", "Non-directive rate"),
        ("length_score", "Length appropriateness"),
        ("bertscore_f1", "BERTScore F1"),
        ("reward_model_score", "Reward model score"),
        ("safety_score", "Safety (no false crisis flags)"),
    ]
    for key, label_str in metric_display:
        val = metrics.get(key, -1)
        if val == -1:
            print(f"  {label_str:<35} —  (model not available)")
            continue
        bar_len = int(val * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {label_str:<35} {bar}  {val:.3f}")


# Entry points

def run_eval_stage(stage: str) -> None:
    if stage not in STAGE_PATHS:
        print(f"Unknown stage '{stage}'. Choose from: {list(STAGE_PATHS.keys())}")
        return
    result = evaluate_stage(stage, STAGE_PATHS[stage])
    out = RESULTS_DIR / f"eval_{stage}.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\n  Results saved → {out}")


def run_eval_all_stages() -> None:
    print("\n=== Evaluation Across All Training Stages ===")
    all_results = []

    for stage, path in STAGE_PATHS.items():
        result = evaluate_stage(stage, path)
        all_results.append(result)

    # Print comparison table
    metrics_to_compare = [
        "validation_rate", "question_rate", "non_directive_rate",
        "bertscore_f1", "reward_model_score",
    ]
    print(f"\n\n{'─'*85}")
    print(f"  {'Stage':<10} " + "  ".join(f"{m[:12]:<14}" for m in metrics_to_compare))
    for r in all_results:
        if "error" in r:
            continue
        row = f"  {r['stage']:<10} "
        row += "  ".join(
            f"{r.get(m, -1):<14.3f}" if r.get(m, -1) != -1 else f"{'—':<14}"
            for m in metrics_to_compare
        )
        print(row)

    out = RESULTS_DIR / "eval_all_stages.json"
    out.write_text(json.dumps(all_results, indent=2))
    print(f"\n  Full results saved → {out}")


def run_human_eval_prep() -> None:
    """Export responses in a format easy to rate manually (or share with others)."""
    print("\n=== Preparing Human Evaluation Export ===")

    stage = "grpo"
    path = STAGE_PATHS[stage]
    if not Path(path).exists():
        print(f"GRPO checkpoint not found. Adjust STAGE_PATHS or run earlier layers.")
        return

    responses = generate_responses(path, EVAL_CONVERSATIONS)
    export = []
    for conv, resp in zip(EVAL_CONVERSATIONS, responses):
        export.append({
            "user_message": conv["user"],
            "sama_response": resp,
            "gold_response": conv["gold"],
            "human_rating": None,   # fill in 1-5
            "human_notes": None,
        })

    out = RESULTS_DIR / "human_eval_export.json"
    out.write_text(json.dumps(export, indent=2))
    print(f"  Exported {len(export)} conversations → {out}")
    print("\n  Fill in 'human_rating' (1–5) and 'human_notes' for each.")
    print("  Rating guide: 1=harmful/dismissive  3=neutral  5=genuinely helpful and warm")


def run_memory_eval() -> None:
    """
    Test memory recall axis: does the model reference session-1 details in session-3?
    Uses the EpisodicMemory class from Layer 9.
    """
    print("\n=== Memory Recall Evaluation ===")
    try:
        import sys
        sys.path.append(str(BASE_DIR))
        from layer9_memory.day10_memory import EpisodicMemory, build_memory_block
    except ImportError:
        print("  Cannot import Layer 9. Run layer9 first.")
        return

    user_id = "eval_memory_user"
    memory = EpisodicMemory(user_id=user_id)
    memory.clear()

    # Session 1: store facts
    session1_facts = [
        "User has a sister named Emma who they had a fight with last month",
        "User lost their job as a graphic designer in March",
        "User has been off antidepressants since March",
    ]
    for fact in session1_facts:
        memory.add(fact, "eval_session_1")

    # Session 3: retrieve and check
    session3_query = "I'm feeling a bit more settled today."
    retrieved = memory.retrieve(session3_query, k=5)
    memory_block = build_memory_block(retrieved, "")

    print(f"\n  Session 1 facts stored: {len(session1_facts)}")
    print(f"  Session 3 query: '{session3_query}'")
    print(f"  Retrieved memories: {len(retrieved)}")
    for m in retrieved:
        print(f"    · {m}")
    print(f"\n  Memory block (what gets injected into system prompt):")
    print(f"  {memory_block[:300]}")

    has_emma = any("emma" in m.lower() or "sister" in m.lower() for m in retrieved)
    has_job = any("job" in m.lower() or "march" in m.lower() for m in retrieved)
    print(f"\n  Remembers sister Emma: {'✓' if has_emma else '✗'}")
    print(f"  Remembers job loss:    {'✓' if has_job else '✗'}")

    memory.clear()

    result = {"retrieved": retrieved, "has_emma": has_emma, "has_job": has_job}
    out = RESULTS_DIR / "memory_eval.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\n  Results saved → {out}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval_stage", choices=list(STAGE_PATHS.keys()),
                        help="Evaluate a single stage checkpoint")
    parser.add_argument("--eval_all_stages", action="store_true",
                        help="Compare all stages side by side")
    parser.add_argument("--human_eval_prep", action="store_true",
                        help="Export responses for human rating")
    parser.add_argument("--memory_eval", action="store_true",
                        help="Test memory recall axis")
    args = parser.parse_args()

    if args.eval_stage:
        run_eval_stage(args.eval_stage)
    elif args.eval_all_stages:
        run_eval_all_stages()
    elif args.human_eval_prep:
        run_human_eval_prep()
    elif args.memory_eval:
        run_memory_eval()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
