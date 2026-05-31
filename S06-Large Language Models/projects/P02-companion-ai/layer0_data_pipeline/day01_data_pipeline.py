"""
Layer 0 — Day 1: Data Pipeline
================================
Collects, cleans, deduplicates, and splits the therapy corpus into
four non-overlapping piles:
  - pretrain : raw text for continued pre-training (Layer 3)
  - finetune : conversation pairs for SFT / DPO (Layers 4, 6)
  - rag      : CBT/DBT factual documents for the knowledge base (Layer 8)
  - eval     : held-out set — never touched during training

Sources:
  - nbertagnolli/counsel-chat                              (HuggingFace)
  - facebook/empathetic_dialogues                          (HuggingFace)
  - solomonk/reddit_mental_health_posts                    (HuggingFace) — 151k Reddit posts
  - Felladrin/pretrain-mental-health-counseling-conversations (HuggingFace) — 3.5k counseling texts
  - vibhorag101/phr_mental_therapy_dataset                 (HuggingFace) — 99k therapy convos
  - CBT/DBT technique text (built-in curated documents)

Run:
    python day01_data_pipeline.py --all          # run full pipeline
    python day01_data_pipeline.py --download     # download datasets only
    python day01_data_pipeline.py --clean        # clean + dedup only
    python day01_data_pipeline.py --split        # split into piles only
    python day01_data_pipeline.py --stats        # print split statistics
"""

import argparse
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

from datasets import load_dataset
from datasketch import MinHash, MinHashLSH

# Use up to 16 CPU cores for parallel dataset processing
NUM_PROC = min(16, os.cpu_count() or 1)

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
SPLITS_DIR = DATA_DIR / "splits"

for d in [RAW_DIR, CLEAN_DIR, SPLITS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── PII patterns — compiled ONCE at import time, reused on every call ─────────

_PII_PATTERNS = [
    (re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"),                                          "[NAME]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),                                    "[PHONE]"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),                "[EMAIL]"),
    (re.compile(r"\b\d{1,5}\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln)\b"), "[ADDRESS]"),
]

# Check presidio availability ONCE at startup — not on every record call
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _PRESIDIO_ANALYZER  = AnalyzerEngine()
    _PRESIDIO_ANONYMIZER = AnonymizerEngine()
    _PRESIDIO_AVAILABLE = True
    print("  PII removal: presidio loaded", flush=True)
except ImportError:
    _PRESIDIO_AVAILABLE = False


def remove_pii_regex(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def remove_pii(text: str) -> str:
    """Remove PII using presidio if available, fallback to compiled regex."""
    if _PRESIDIO_AVAILABLE:
        results = _PRESIDIO_ANALYZER.analyze(text=text, language="en")
        return _PRESIDIO_ANONYMIZER.anonymize(text=text, analyzer_results=results).text
    return remove_pii_regex(text)


# ── Text cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    # Normalise unicode
    text = unicodedata.normalize("NFKC", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove very short texts
    if len(text.split()) < 10:
        return ""
    return text


# ── Deduplication ─────────────────────────────────────────────────────────────

def get_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for word in text.lower().split():
        m.update(word.encode("utf8"))
    return m


def deduplicate(texts: list[str], threshold: float = 0.8) -> list[str]:
    """Remove near-duplicate texts using MinHash LSH."""
    print(f"  Deduplicating {len(texts):,} texts (threshold={threshold})...")
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    unique = []
    for i, text in enumerate(texts):
        m = get_minhash(text)
        if not lsh.query(m):
            lsh.insert(str(i), m)
            unique.append(text)
    print(f"  {len(texts):,} → {len(unique):,} unique texts ({len(texts)-len(unique):,} removed)")
    return unique


# ── Dataset downloaders ───────────────────────────────────────────────────────

def _process_counsel_row(example: dict) -> dict:
    """Runs per-row inside dataset.map() — must be a top-level function for pickling."""
    q = clean_text(example.get("questionText", "") or "")
    a = clean_text(example.get("answerText", "") or "")
    valid = bool(q and a and len(q.split()) >= 10 and len(a.split()) >= 15)
    return {
        "question": remove_pii(q) if valid else "",
        "answer":   remove_pii(a) if valid else "",
        "topic":    example.get("topic", "") or "",
        "source":   "counsel_chat",
        "_valid":   valid,
    }


def download_counsel_chat() -> list[dict]:
    """
    Returns list of {question, answer, topic} dicts.
    This is the primary source for finetune pairs.
    """
    print("Downloading Counsel Chat...", flush=True)
    ds = load_dataset("nbertagnolli/counsel-chat", split="train")
    print(f"  Loaded {len(ds):,} raw examples — processing with {NUM_PROC} workers...", flush=True)

    ds = ds.map(_process_counsel_row, num_proc=NUM_PROC, desc="  Cleaning")
    ds = ds.filter(lambda x: x["_valid"], num_proc=NUM_PROC, desc="  Filtering")

    records = [
        {"question": ex["question"], "answer": ex["answer"],
         "topic": ex["topic"], "source": ex["source"]}
        for ex in ds
    ]
    print(f"  Done — {len(records):,} valid QA pairs", flush=True)
    return records


def download_empathetic_dialogues() -> tuple[list[str], list[dict]]:
    """
    Returns:
      pretrain_texts : raw utterance text for language model pre-training
      finetune_pairs : (prompt, response) pairs for SFT
    """
    print("Downloading EmpatheticDialogues...", flush=True)
    ds = load_dataset("facebook/empathetic_dialogues", split="train", trust_remote_code=True)
    print(f"  Loaded {len(ds):,} raw utterances — converting to pandas for fast grouping...", flush=True)

    # pandas groupby is orders of magnitude faster than a Python dict loop
    df = ds.to_pandas()
    df["utterance"] = df["utterance"].fillna("").apply(clean_text)
    df = df[df["utterance"].str.strip() != ""]

    print(f"  Grouping {len(df):,} utterances into conversations...", flush=True)
    pretrain_texts = []
    finetune_pairs = []

    grouped = df.sort_values("utterance_idx").groupby("conv_id")
    total_convs = len(grouped)
    print(f"  Building pretrain + finetune from {total_convs:,} conversations...", flush=True)

    for j, (_, turns) in enumerate(grouped):
        if j % 2000 == 0:
            print(f"  Progress: {j}/{total_convs} conversations...", flush=True)
        utterances = turns["utterance"].tolist()
        emotions   = turns["context"].tolist()

        # Pretrain: full conversation as raw text
        full_text = " ".join(utterances)
        if full_text.strip():
            pretrain_texts.append(full_text)

        # Finetune: consecutive (user, assistant) pairs
        # Use regex-only PII removal — empathetic_dialogues is a synthetic
        # research dataset, presidio NLP analysis is overkill and very slow here
        for i in range(0, len(utterances) - 1, 2):
            prompt   = utterances[i]
            response = utterances[i + 1]
            if prompt and response:
                finetune_pairs.append({
                    "question": remove_pii_regex(prompt),
                    "answer":   remove_pii_regex(response),
                    "emotion":  emotions[i] if i < len(emotions) else "",
                    "source":   "empathetic_dialogues",
                })

    print(f"  Done — {len(pretrain_texts):,} pretrain texts | {len(finetune_pairs):,} finetune pairs", flush=True)
    return pretrain_texts, finetune_pairs


def download_reddit_mental_health(max_rows: int = 50_000) -> list[str]:
    """
    151k posts from r/depression, r/ptsd, r/ocd — the most therapy-relevant subreddits.
    Uses pandas for fast title+body joining. Regex PII only (public posts).
    Returns list of pretrain texts.
    """
    print("Downloading Reddit Mental Health posts...", flush=True)
    ds = load_dataset("solomonk/reddit_mental_health_posts", split="train")
    print(f"  Loaded {len(ds):,} posts — converting to pandas...", flush=True)

    df = ds.to_pandas()

    # Keep only the most therapy-relevant subreddits
    therapy_subs = {"depression", "ptsd", "ocd"}
    df = df[df["subreddit"].str.lower().isin(therapy_subs)]
    print(f"  Filtered to therapy subreddits: {len(df):,} posts", flush=True)

    # Cap at max_rows
    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=42)
        print(f"  Capped at {max_rows:,} posts", flush=True)

    # Combine title + body as one pretrain text
    df["text"] = (
        df["title"].fillna("") + " " + df["body"].fillna("")
    ).str.strip()

    # Vectorised clean: remove URLs, normalise whitespace
    df["text"] = df["text"].str.replace(r"https?://\S+", "", regex=True)
    df["text"] = df["text"].str.replace(r"\s+", " ", regex=True).str.strip()

    # Drop short posts (< 10 words)
    df = df[df["text"].str.split().str.len() >= 10]

    # PII removal — regex only (these are public posts, presidio overkill)
    print(f"  Applying PII removal to {len(df):,} posts...", flush=True)
    texts = [remove_pii_regex(t) for t in df["text"].tolist()]

    print(f"  Done — {len(texts):,} pretrain texts from Reddit", flush=True)
    return texts


def download_felladrin_counseling() -> list[str]:
    """
    3.5k mental health counseling responses — purpose-built for pretraining.
    Single 'text' column, already clean therapy language.
    """
    print("Downloading Felladrin counseling texts...", flush=True)
    ds = load_dataset("Felladrin/pretrain-mental-health-counseling-conversations", split="train")
    print(f"  Loaded {len(ds):,} texts", flush=True)

    texts = []
    for ex in ds:
        t = clean_text(ex.get("text", "") or "")
        if t:
            texts.append(remove_pii_regex(t))

    print(f"  Done — {len(texts):,} pretrain texts from Felladrin", flush=True)
    return texts


def download_phr_therapy(max_rows: int = 20_000) -> list[str]:
    """
    99k synthetic therapy conversations in llama-2-chat format.
    We strip the system prompt and markers to get clean conversation text.
    Uses pandas for fast vectorised processing.
    """
    print("Downloading PHR therapy dataset...", flush=True)
    ds = load_dataset("vibhorag101/phr_mental_therapy_dataset", split="train")
    print(f"  Loaded {len(ds):,} rows — capping at {max_rows:,}...", flush=True)

    df = ds.to_pandas()
    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=42)

    # Strip llama-2 system prompt and chat markers
    def strip_llama_format(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        # Remove system prompt block
        text = re.sub(r"<<SYS>>.*?<</SYS>>", "", text, flags=re.DOTALL)
        # Remove llama-2 markers
        for marker in ["<s>", "</s>", "[INST]", "[/INST]"]:
            text = text.replace(marker, " ")
        return re.sub(r"\s+", " ", text).strip()

    print(f"  Stripping llama-2 format markers...", flush=True)
    df["text"] = df["text"].fillna("").apply(strip_llama_format)
    df = df[df["text"].str.split().str.len() >= 10]

    texts = [remove_pii_regex(t) for t in df["text"].tolist()]
    print(f"  Done — {len(texts):,} pretrain texts from PHR therapy", flush=True)
    return texts


def extract_phr_finetune_pairs(max_rows: int = 20_000) -> list[dict]:
    """
    Re-parses PHR therapy dataset (already in HF cache) as Q&A pairs for SFT.
    The download_phr_therapy() function extracted pretrain text — this function
    extracts the question/answer structure from the llama-2 chat format instead.
    """
    print("Extracting PHR therapy Q&A pairs for SFT...", flush=True)
    ds = load_dataset("vibhorag101/phr_mental_therapy_dataset", split="train")
    df = ds.to_pandas()
    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=42)
    print(f"  Parsing {len(df):,} rows for Q&A structure...", flush=True)

    pairs = []
    for text in df["text"].fillna("").tolist():
        try:
            # Strip system prompt block
            text = re.sub(r"<<SYS>>.*?<</SYS>>", "", text, flags=re.DOTALL)
            # Split on [/INST] to separate question from answer
            parts = text.split("[/INST]")
            if len(parts) < 2:
                continue
            question = parts[0].replace("<s>", "").replace("[INST]", "").strip()
            answer   = parts[1].replace("</s>", "").strip()
            q = clean_text(question)
            a = clean_text(answer)
            if q and a and len(q.split()) >= 5 and len(a.split()) >= 15:
                pairs.append({
                    "question": remove_pii_regex(q),
                    "answer":   remove_pii_regex(a),
                    "source":   "phr_therapy_sft",
                })
        except Exception:
            continue

    print(f"  Done — {len(pairs):,} Q&A pairs from PHR", flush=True)
    return pairs


def download_amod_counseling() -> list[dict]:
    """
    Real mental health counseling Q&A pairs — similar quality to counsel_chat
    but a different collection, adding diversity without repetition.
    """
    print("Downloading Amod mental health counseling...", flush=True)
    try:
        ds = load_dataset("Amod/mental_health_counseling_conversations", split="train")
    except Exception as e:
        # The repo contains a LICENSE-RAIL-D.txt that confuses the builder
        # (column mismatch: txt has 'text', CSV has 'Context'+'Response').
        # Retry specifying only CSV files to exclude the license file.
        print(f"  Standard load failed ({type(e).__name__}), retrying with explicit data file...", flush=True)
        try:
            # Repo contains LICENSE-RAIL-D.txt which confuses the builder.
            # Specify the actual data file directly to skip the license file.
            ds = load_dataset(
                "Amod/mental_health_counseling_conversations",
                data_files={"train": "combined_dataset.json"},
                split="train",
            )
        except Exception as e2:
            print(f"  Both load attempts failed — skipping Amod dataset.", flush=True)
            print(f"  Error: {e2}", flush=True)
            return []
    print(f"  Loaded {len(ds):,} examples", flush=True)

    df = ds.to_pandas()
    print(f"  Columns: {df.columns.tolist()}", flush=True)

    # Priority-based detection — iterates priority list, not df.columns order
    col_lower = {c.lower(): c for c in df.columns}
    q_col = next((col_lower[c] for c in ("context", "question", "input", "prompt", "instruction") if c in col_lower), None)
    a_col = next((col_lower[c] for c in ("response", "answer", "output") if c in col_lower), None)

    if not q_col or not a_col:
        print(f"  Could not detect Q&A columns — skipping", flush=True)
        return []

    pairs = []
    for _, row in df.iterrows():
        q = clean_text(str(row[q_col]))
        a = clean_text(str(row[a_col]))
        if q and a and len(q.split()) >= 5 and len(a.split()) >= 15:
            pairs.append({
                "question": remove_pii_regex(q),
                "answer":   remove_pii_regex(a),
                "source":   "amod_counseling",
            })

    print(f"  Done — {len(pairs):,} Q&A pairs from Amod", flush=True)
    return pairs


def download_mentalchat() -> list[dict]:
    """
    9,775 synthetic counselor-client conversations from ShenLab.
    Covers 33 mental health topics — adds diversity to the finetune mix.
    """
    print("Downloading ShenLab MentalChat16K...", flush=True)
    ds = load_dataset("ShenLab/MentalChat16K", split="train")
    print(f"  Loaded {len(ds):,} examples", flush=True)

    df = ds.to_pandas()
    print(f"  Columns: {df.columns.tolist()}", flush=True)

    # Detect column names by priority — iterate the priority list, NOT df.columns.
    # MentalChat has ['instruction', 'input', 'output'] where instruction is a
    # fixed system prompt (same for all rows) and input is the actual user message.
    # Iterating df.columns would pick 'instruction' first; iterating the priority
    # list correctly picks 'input' before 'instruction'.
    col_lower = {c.lower(): c for c in df.columns}
    q_col = next((col_lower[c] for c in ("input", "question", "context", "prompt", "instruction") if c in col_lower), None)
    a_col = next((col_lower[c] for c in ("output", "response", "answer") if c in col_lower), None)

    if not q_col or not a_col:
        print(f"  Could not detect Q&A columns — skipping", flush=True)
        return []

    pairs = []
    for _, row in df.iterrows():
        q = clean_text(str(row[q_col]))
        a = clean_text(str(row[a_col]))
        if q and a and len(q.split()) >= 5 and len(a.split()) >= 15:
            pairs.append({
                "question": remove_pii_regex(q),
                "answer":   remove_pii_regex(a),
                "source":   "mentalchat",
            })

    print(f"  Done — {len(pairs):,} Q&A pairs from MentalChat16K", flush=True)
    return pairs


def build_cbt_dbt_rag_documents() -> list[dict]:
    """
    Builds RAG documents from structured CBT/DBT technique descriptions.
    These are manually curated from public domain clinical resources.
    In production: scrape NICE guidelines, public CBT workbooks, etc.
    This provides a baseline set to start with.
    """
    print("Building CBT/DBT RAG documents...")
    documents = [
        {
            "title": "Cognitive Restructuring",
            "content": "Cognitive restructuring is a CBT technique that helps identify and challenge unhelpful thought patterns called cognitive distortions. The process involves: (1) identifying the automatic thought, (2) examining the evidence for and against it, (3) generating a more balanced alternative thought. Common distortions include all-or-nothing thinking, catastrophising, mind reading, and overgeneralisation.",
            "category": "CBT technique",
        },
        {
            "title": "Behavioural Activation",
            "content": "Behavioural activation is a CBT technique for depression based on the observation that depression leads to withdrawal, which reduces positive experiences, which deepens depression. The intervention: schedule small, achievable activities that provide a sense of pleasure or accomplishment, even when motivation is absent. Start with easy wins (5-minute activities) and build up gradually.",
            "category": "CBT technique",
        },
        {
            "title": "Thought Records",
            "content": "A thought record is a structured worksheet used in CBT to examine distressing situations. Columns: (1) Situation — what happened, (2) Automatic thought — what ran through my mind, (3) Emotion — what I felt and how strongly, (4) Evidence for the thought, (5) Evidence against the thought, (6) Balanced thought, (7) Outcome — how I feel now. Regular practice builds metacognitive awareness.",
            "category": "CBT technique",
        },
        {
            "title": "DBT TIPP Skills",
            "content": "TIPP skills are DBT crisis survival techniques for managing overwhelming emotions. T — Temperature: hold ice or splash cold water on face to activate the dive reflex and reduce emotional arousal quickly. I — Intense exercise: 20 minutes of vigorous activity to burn off adrenaline. P — Paced breathing: breathe out longer than you breathe in (inhale 4 counts, exhale 6 counts) to activate the parasympathetic system. P — Progressive muscle relaxation: systematically tense and release muscle groups.",
            "category": "DBT skill",
        },
        {
            "title": "DBT DEAR MAN",
            "content": "DEAR MAN is a DBT interpersonal effectiveness skill for making requests assertively. D — Describe the situation factually. E — Express your feelings using 'I' statements. A — Assert your needs clearly. R — Reinforce by explaining why meeting the need benefits both parties. M — stay Mindful of your goals. A — Appear confident (eye contact, posture). N — Negotiate and be willing to compromise. Use when you need something from another person.",
            "category": "DBT skill",
        },
        {
            "title": "Radical Acceptance",
            "content": "Radical acceptance is a DBT distress tolerance skill. It means fully accepting reality as it is — not approving of it, not liking it, but acknowledging it is what it is. Refusing to accept reality causes suffering on top of pain. Steps: observe that you are fighting reality, remind yourself that it is what it is, consider what led to this moment, practise acceptance with your whole body and mind. Repeat as needed — acceptance is a practice, not a single decision.",
            "category": "DBT skill",
        },
        {
            "title": "Opposite Action",
            "content": "Opposite action is a DBT emotion regulation skill. When an emotion urges a behaviour that makes things worse in the long run, the antidote is to act opposite to the emotion's action urge. For shame: approach the situation rather than hide. For fear: approach rather than avoid. For sadness/depression: become active and engaged rather than withdrawing. For anger: avoid attacking, do something kind instead. Only apply when the emotion is not justified or when acting on it is not effective.",
            "category": "DBT skill",
        },
        {
            "title": "5-4-3-2-1 Grounding Technique",
            "content": "The 5-4-3-2-1 technique is a sensory grounding exercise for anxiety and dissociation. It anchors attention to the present moment using the five senses. Notice: 5 things you can see, 4 things you can physically feel (textures, temperature), 3 things you can hear, 2 things you can smell, 1 thing you can taste. Describe each one slowly and specifically. Repeat if needed. Useful during panic attacks, flashbacks, and overwhelming emotions.",
            "category": "Grounding technique",
        },
        {
            "title": "Box Breathing",
            "content": "Box breathing (also called square breathing or 4-4-4-4 breathing) is a breathing regulation technique. Inhale for 4 counts, hold for 4 counts, exhale for 4 counts, hold for 4 counts. Repeat 4-6 cycles. Activates the parasympathetic nervous system, reducing heart rate and cortisol. Used by military personnel and first responders under acute stress. Easier to learn than diaphragmatic breathing. Can be done anywhere without drawing attention.",
            "category": "Grounding technique",
        },
        {
            "title": "Safe Place Visualisation",
            "content": "Safe place visualisation is a guided imagery technique for anxiety and trauma. Steps: (1) Close your eyes and imagine a place — real or imagined — where you feel completely safe and calm. (2) Notice details: what do you see, hear, smell, feel? (3) Give the place a name as an anchor word. (4) Practise returning to this place in imagination. Use the anchor word to return quickly during distress. Commonly used in EMDR and trauma-focused CBT as a containment resource.",
            "category": "Grounding technique",
        },
        {
            "title": "What is Anxiety",
            "content": "Anxiety is the body's natural response to perceived threat — a survival mechanism. Physical symptoms: increased heart rate, shallow breathing, muscle tension, sweating. These are caused by adrenaline preparing the body to fight or flee. Anxiety becomes a problem when the threat response activates in situations that are not genuinely dangerous. Common anxiety disorders: generalised anxiety disorder (GAD), social anxiety, panic disorder, phobias, health anxiety. Effective treatments: CBT, exposure therapy, medication (SSRIs), mindfulness.",
            "category": "Psychoeducation",
        },
        {
            "title": "What is Depression",
            "content": "Depression is more than low mood — it is a persistent state affecting thought, behaviour, and physiology. Core symptoms (DSM-5): depressed mood most of the day, loss of interest or pleasure (anhedonia), changes in appetite or weight, sleep disturbance, fatigue, feelings of worthlessness or guilt, difficulty concentrating, thoughts of death. A diagnosis requires at least 5 symptoms for at least 2 weeks. Depression is not a character flaw or weakness. It is a treatable condition with evidence-based interventions including CBT, behavioural activation, and medication.",
            "category": "Psychoeducation",
        },
        {
            "title": "Attachment Styles",
            "content": "Attachment theory (Bowlby, Ainsworth) describes how early relationships with caregivers shape how we relate to others throughout life. Four adult attachment styles: Secure — comfortable with intimacy, not anxious about abandonment. Anxious/Preoccupied — fears abandonment, seeks reassurance, may appear clingy. Dismissive/Avoidant — values independence, uncomfortable with closeness, downplays emotions. Fearful/Disorganised — wants closeness but fears it, common in trauma histories. Attachment style is not destiny — it can shift through secure relationships and therapy.",
            "category": "Psychoeducation",
        },
        {
            "title": "Crisis Resources (UK)",
            "content": "If you are in crisis in the UK: Samaritans — call 116 123 (free, 24/7, no appointment needed). Crisis text line — text SHOUT to 85258 (free, 24/7). NHS urgent mental health — call 111, select mental health option. In immediate danger — call 999 or go to A&E. PAPYRUS (under 35) — 0800 068 4141. Mind infoline — 0300 123 3393. These services are staffed by trained listeners who will not judge you.",
            "category": "Crisis resources",
        },
        {
            "title": "Crisis Resources (US)",
            "content": "If you are in crisis in the US: 988 Suicide and Crisis Lifeline — call or text 988 (free, 24/7). Crisis Text Line — text HOME to 741741. Veterans Crisis Line — call 988, press 1. Trans Lifeline — 877-565-8860. Trevor Project (LGBTQ+ youth) — 1-866-488-7386. In immediate danger — call 911 or go to the nearest emergency room. You do not need to be suicidal to use these services — any mental health crisis qualifies.",
            "category": "Crisis resources",
        },
    ]
    print(f"  {len(documents):,} RAG documents")
    return documents


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_download() -> None:
    print("\n=== Step 1: Download datasets ===")

    counsel_path = RAW_DIR / "counsel_chat.json"
    if counsel_path.exists():
        print(f"  Skipping Counsel Chat (already saved at {counsel_path})")
    else:
        counsel = download_counsel_chat()
        counsel_path.write_text(json.dumps(counsel, indent=2, ensure_ascii=False))
        print(f"  Saved → {counsel_path}")

    emp_pretrain_path = RAW_DIR / "empathetic_pretrain.json"
    emp_finetune_path = RAW_DIR / "empathetic_finetune.json"
    if emp_pretrain_path.exists() and emp_finetune_path.exists():
        print(f"  Skipping EmpatheticDialogues (already saved)")
    else:
        pretrain_texts, empathetic_pairs = download_empathetic_dialogues()
        emp_pretrain_path.write_text(json.dumps(pretrain_texts, indent=2, ensure_ascii=False))
        emp_finetune_path.write_text(json.dumps(empathetic_pairs, indent=2, ensure_ascii=False))
        print(f"  Saved → empathetic_pretrain.json + empathetic_finetune.json")

    rag_path = RAW_DIR / "cbt_dbt_rag.json"
    if rag_path.exists():
        print(f"  Skipping CBT/DBT docs (already saved)")
    else:
        rag_docs = build_cbt_dbt_rag_documents()
        rag_path.write_text(json.dumps(rag_docs, indent=2, ensure_ascii=False))
        print(f"  Saved → {rag_path}")

    reddit_path = RAW_DIR / "reddit_mental_health.json"
    if reddit_path.exists():
        print(f"  Skipping Reddit posts (already saved)")
    else:
        reddit_texts = download_reddit_mental_health(max_rows=50_000)
        reddit_path.write_text(json.dumps(reddit_texts, indent=2, ensure_ascii=False))
        print(f"  Saved → {reddit_path}")

    felladrin_path = RAW_DIR / "felladrin_counseling.json"
    if felladrin_path.exists():
        print(f"  Skipping Felladrin counseling (already saved)")
    else:
        felladrin_texts = download_felladrin_counseling()
        felladrin_path.write_text(json.dumps(felladrin_texts, indent=2, ensure_ascii=False))
        print(f"  Saved → {felladrin_path}")

    phr_path = RAW_DIR / "phr_therapy.json"
    if phr_path.exists():
        print(f"  Skipping PHR therapy (already saved)")
    else:
        phr_texts = download_phr_therapy(max_rows=20_000)
        phr_path.write_text(json.dumps(phr_texts, indent=2, ensure_ascii=False))
        print(f"  Saved → {phr_path}")

    phr_sft_path = RAW_DIR / "phr_sft_pairs.json"
    if phr_sft_path.exists():
        print(f"  Skipping PHR SFT pairs (already saved)")
    else:
        phr_sft = extract_phr_finetune_pairs(max_rows=20_000)
        phr_sft_path.write_text(json.dumps(phr_sft, indent=2, ensure_ascii=False))
        print(f"  Saved → {phr_sft_path}")

    amod_path = RAW_DIR / "amod_counseling.json"
    if amod_path.exists():
        print(f"  Skipping Amod counseling (already saved)")
    else:
        amod = download_amod_counseling()
        amod_path.write_text(json.dumps(amod, indent=2, ensure_ascii=False))
        print(f"  Saved → {amod_path}")

    mentalchat_path = RAW_DIR / "mentalchat.json"
    if mentalchat_path.exists():
        print(f"  Skipping MentalChat (already saved)")
    else:
        mentalchat = download_mentalchat()
        mentalchat_path.write_text(json.dumps(mentalchat, indent=2, ensure_ascii=False))
        print(f"  Saved → {mentalchat_path}")


def run_clean() -> None:
    print("\n=== Step 2: Clean and deduplicate ===")

    # Counsel Chat
    counsel = json.loads((RAW_DIR / "counsel_chat.json").read_text())
    q_texts = [ex["question"] for ex in counsel]
    q_unique = set(deduplicate(q_texts))
    counsel_clean = [ex for ex in counsel if ex["question"] in q_unique]
    (CLEAN_DIR / "counsel_chat.json").write_text(json.dumps(counsel_clean, indent=2, ensure_ascii=False))
    print(f"  Counsel Chat: {len(counsel):,} → {len(counsel_clean):,}")

    # Empathetic pretrain
    pretrain = json.loads((RAW_DIR / "empathetic_pretrain.json").read_text())
    pretrain_clean = deduplicate(pretrain)
    (CLEAN_DIR / "empathetic_pretrain.json").write_text(json.dumps(pretrain_clean, indent=2, ensure_ascii=False))

    # Empathetic finetune
    empathetic = json.loads((RAW_DIR / "empathetic_finetune.json").read_text())
    emp_q = [ex["question"] for ex in empathetic]
    emp_unique = set(deduplicate(emp_q))
    empathetic_clean = [ex for ex in empathetic if ex["question"] in emp_unique]
    (CLEAN_DIR / "empathetic_finetune.json").write_text(json.dumps(empathetic_clean, indent=2, ensure_ascii=False))
    print(f"  Empathetic: {len(empathetic):,} → {len(empathetic_clean):,} pairs | {len(pretrain):,} → {len(pretrain_clean):,} pretrain")

    # RAG docs — no dedup needed (small, curated)
    import shutil
    shutil.copy(RAW_DIR / "cbt_dbt_rag.json", CLEAN_DIR / "cbt_dbt_rag.json")
    print(f"  RAG docs: copied as-is (curated, no dedup needed)")

    # Reddit mental health posts
    reddit_raw_path = RAW_DIR / "reddit_mental_health.json"
    if reddit_raw_path.exists():
        reddit = json.loads(reddit_raw_path.read_text())
        reddit_clean = deduplicate(reddit)
        (CLEAN_DIR / "reddit_mental_health.json").write_text(
            json.dumps(reddit_clean, indent=2, ensure_ascii=False))
        print(f"  Reddit: {len(reddit):,} → {len(reddit_clean):,} pretrain texts")
    else:
        print("  Reddit: not found, skipping (run --download first)")

    # Felladrin counseling texts
    felladrin_raw_path = RAW_DIR / "felladrin_counseling.json"
    if felladrin_raw_path.exists():
        felladrin = json.loads(felladrin_raw_path.read_text())
        felladrin_clean = deduplicate(felladrin)
        (CLEAN_DIR / "felladrin_counseling.json").write_text(
            json.dumps(felladrin_clean, indent=2, ensure_ascii=False))
        print(f"  Felladrin: {len(felladrin):,} → {len(felladrin_clean):,} pretrain texts")
    else:
        print("  Felladrin: not found, skipping")

    # PHR therapy texts (pretrain)
    phr_raw_path = RAW_DIR / "phr_therapy.json"
    if phr_raw_path.exists():
        phr = json.loads(phr_raw_path.read_text())
        phr_clean = deduplicate(phr)
        (CLEAN_DIR / "phr_therapy.json").write_text(
            json.dumps(phr_clean, indent=2, ensure_ascii=False))
        print(f"  PHR therapy: {len(phr):,} → {len(phr_clean):,} pretrain texts")
    else:
        print("  PHR therapy: not found, skipping")

    # PHR SFT pairs (finetune) — deduplicate on question text
    phr_sft_raw = RAW_DIR / "phr_sft_pairs.json"
    if phr_sft_raw.exists():
        phr_sft = json.loads(phr_sft_raw.read_text())
        phr_sft_q = [ex["question"] for ex in phr_sft]
        phr_sft_unique = set(deduplicate(phr_sft_q))
        phr_sft_clean = [ex for ex in phr_sft if ex["question"] in phr_sft_unique]
        (CLEAN_DIR / "phr_sft_pairs.json").write_text(
            json.dumps(phr_sft_clean, indent=2, ensure_ascii=False))
        print(f"  PHR SFT pairs: {len(phr_sft):,} → {len(phr_sft_clean):,} finetune pairs")
    else:
        print("  PHR SFT pairs: not found, skipping")

    # Amod counseling (finetune)
    amod_raw = RAW_DIR / "amod_counseling.json"
    if amod_raw.exists():
        amod = json.loads(amod_raw.read_text())
        amod_q = [ex["question"] for ex in amod]
        amod_unique = set(deduplicate(amod_q))
        amod_clean = [ex for ex in amod if ex["question"] in amod_unique]
        (CLEAN_DIR / "amod_counseling.json").write_text(
            json.dumps(amod_clean, indent=2, ensure_ascii=False))
        print(f"  Amod counseling: {len(amod):,} → {len(amod_clean):,} finetune pairs")
    else:
        print("  Amod counseling: not found, skipping")

    # MentalChat16K (finetune)
    mentalchat_raw = RAW_DIR / "mentalchat.json"
    if mentalchat_raw.exists():
        mentalchat = json.loads(mentalchat_raw.read_text())
        mc_q = [ex["question"] for ex in mentalchat]
        mc_unique = set(deduplicate(mc_q))
        mentalchat_clean = [ex for ex in mentalchat if ex["question"] in mc_unique]
        (CLEAN_DIR / "mentalchat.json").write_text(
            json.dumps(mentalchat_clean, indent=2, ensure_ascii=False))
        print(f"  MentalChat16K: {len(mentalchat):,} → {len(mentalchat_clean):,} finetune pairs")
    else:
        print("  MentalChat16K: not found, skipping")


def run_split() -> None:
    """
    Split into non-overlapping piles.
    Critical rule: eval examples MUST NOT appear in any training pile.
    """
    print("\n=== Step 3: Split into piles ===")

    counsel = json.loads((CLEAN_DIR / "counsel_chat.json").read_text())
    empathetic = json.loads((CLEAN_DIR / "empathetic_finetune.json").read_text())
    rag_docs = json.loads((CLEAN_DIR / "cbt_dbt_rag.json").read_text())

    import random as _random
    _random.seed(42)

    # Filter empathetic_dialogues to ≥50 word answers.
    # Inspection showed that shorter empathetic answers are casual peer-chat
    # ("Oh man, I accidentally eat cake all the time!") — wrong register for a
    # therapy companion. ≥50 words keeps only substantive exchanges.
    emp_before = len(empathetic)
    empathetic = [
        ex for ex in empathetic
        if len(ex.get("answer", "").split()) >= 50
    ]
    print(f"  Empathetic: filtered to ≥50-word answers: {emp_before:,} → {len(empathetic):,}")

    # Combine all pretrain sources
    pretrain_texts = json.loads((CLEAN_DIR / "empathetic_pretrain.json").read_text())
    for extra_file, label in [
        ("reddit_mental_health.json",   "Reddit"),
        ("felladrin_counseling.json",   "Felladrin"),
        ("phr_therapy.json",            "PHR therapy"),
    ]:
        p = CLEAN_DIR / extra_file
        if p.exists():
            extra = json.loads(p.read_text())
            pretrain_texts.extend(extra)
            print(f"  Added {len(extra):,} texts from {label} to pretrain")

    # Load finetune-only sources with quality filters applied per source:
    #   - PHR SFT:  REMOVED — questions contain leaked system prompt (<<SYS>>),
    #               answers contain next patient turn (<s>[INST]). Unsalvageable.
    #   - Amod:     ≥30 word answers — removes short harmful outliers
    #   - MentalChat: capped at 4,000 — good quality but was 57% of data,
    #                 cap balances the source mix
    extra_finetune: list[dict] = []

    amod_path = CLEAN_DIR / "amod_counseling.json"
    if amod_path.exists():
        amod = json.loads(amod_path.read_text())
        amod = [ex for ex in amod if len(ex.get("answer", "").split()) >= 30]
        extra_finetune.extend(amod)
        print(f"  Added {len(amod):,} pairs from Amod counseling (≥30-word filter)")
    else:
        print("  Amod counseling: not found")

    mentalchat_path = CLEAN_DIR / "mentalchat.json"
    if mentalchat_path.exists():
        mentalchat = json.loads(mentalchat_path.read_text())
        if len(mentalchat) > 4000:
            mentalchat = _random.sample(mentalchat, 4000)
        extra_finetune.extend(mentalchat)
        print(f"  Added {len(mentalchat):,} pairs from MentalChat16K (capped at 4,000)")
    else:
        print("  MentalChat16K: not found")

    print("  PHR SFT: skipped — broken question/answer fields (system prompt leakage)")

    # Hold out 10% of each conversational source for eval
    def hold_out(items: list, pct: float = 0.1) -> tuple[list, list]:
        n_eval = max(20, int(len(items) * pct))
        return items[n_eval:], items[:n_eval]

    counsel_train, counsel_eval = hold_out(counsel)
    emp_train, emp_eval = hold_out(empathetic)

    splits = {
        "pretrain": pretrain_texts,                                   # raw text, language modelling
        "finetune": counsel_train + emp_train + extra_finetune,       # QA pairs for SFT/DPO
        "rag": rag_docs,                                              # factual documents
        "eval": counsel_eval + emp_eval,                              # held out — never touch
    }

    for name, data in splits.items():
        path = SPLITS_DIR / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"  {name:<12}: {len(data):,} examples → {path.name}")

    print("\n  KEY RULE: eval split is now sealed. Do not modify it.")
    print("  Any change to eval would contaminate your evaluation results.")


def run_stats() -> None:
    print("\n=== Dataset Statistics ===")
    for split_name in ["pretrain", "finetune", "rag", "eval"]:
        path = SPLITS_DIR / f"{split_name}.json"
        if not path.exists():
            print(f"  {split_name}: not found (run --split first)")
            continue
        data = json.loads(path.read_text())
        if isinstance(data[0], str):
            total_words = sum(len(t.split()) for t in data)
            avg_words = total_words // len(data)
            print(f"  {split_name:<12}: {len(data):,} texts | {total_words:,} total words | {avg_words} avg words/text")
        else:
            sources = {}
            for ex in data:
                s = ex.get("source", ex.get("category", "unknown"))
                sources[s] = sources.get(s, 0) + 1
            source_str = " | ".join(f"{k}: {v}" for k, v in sources.items())
            print(f"  {split_name:<12}: {len(data):,} examples | {source_str}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--split", action="store_true")
    parser.add_argument("--stats", action="store_true")
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
