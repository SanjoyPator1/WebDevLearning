"""
Layer 9 — Day 10: Memory System
==================================
Implements three types of memory for the companion:
  - Working memory   : the current context window (sliding + summarisation)
  - Episodic memory  : specific facts the user has shared, stored in ChromaDB
  - Semantic memory  : a rolling summary of patterns and progress, updated each session

The "Her moment" test: after storing facts in session 1, does Sama
naturally reference them in session 3 without being prompted?

Produces:
    checkpoints/memory_store/    ← ChromaDB persistent store (consumed by Layer 13)

Run:
    python day10_memory.py --demo              # 3-session scripted demo
    python day10_memory.py --test_extraction   # test fact extraction quality
    python day10_memory.py --test_retrieval    # test memory retrieval relevance
    python day10_memory.py --her_moment        # the full "Her" test (5 sessions)
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import chromadb
import spacy
from sentence_transformers import SentenceTransformer

# Paths

BASE_DIR = Path(__file__).parent.parent
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR = Path(__file__).parent / "results"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

THERAPY_EMBEDDER = CHECKPOINT_DIR / "therapy_embedder"
GRPO_CHECKPOINT = CHECKPOINT_DIR / "grpo_sama"
DPO_CHECKPOINT = CHECKPOINT_DIR / "dpo_sama_beta0.1"
MEMORY_STORE_PATH = CHECKPOINT_DIR / "memory_store"

GENERAL_EMBEDDER = "BAAI/bge-base-en-v1.5"

SYSTEM_PROMPT = """You are Sama — a compassionate, patient, and genuinely curious companion.
You listen deeply, validate emotions, and ask gentle open questions.
You never give unsolicited advice."""


# Episodic Memory Store

class EpisodicMemory:
    """
    Stores specific facts the user has shared, retrieved by semantic similarity.
    Backed by ChromaDB for persistence across sessions.
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.client = chromadb.PersistentClient(path=str(MEMORY_STORE_PATH))
        self.collection = self.client.get_or_create_collection(
            name="episodic_memory",
            metadata={"hnsw:space": "cosine"},
        )
        embedder_path = str(THERAPY_EMBEDDER) if THERAPY_EMBEDDER.exists() else GENERAL_EMBEDDER
        self.embedder = SentenceTransformer(embedder_path)

    def add(self, fact: str, session_id: str) -> None:
        """Store a single extracted fact."""
        emb = self.embedder.encode([fact], normalize_embeddings=True)[0].tolist()
        doc_id = f"{self.user_id}_{session_id}_{abs(hash(fact)) % 10_000_000}"
        self.collection.add(
            documents=[fact],
            embeddings=[emb],
            ids=[doc_id],
            metadatas=[{
                "user_id": self.user_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }],
        )

    def retrieve(self, query: str, k: int = 8) -> list[str]:
        """Retrieve the k most relevant memories for the current query."""
        count = self.collection.count()
        if count == 0:
            return []
        q_emb = self.embedder.encode([query], normalize_embeddings=True)[0].tolist()
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=min(k, count),
            where={"user_id": self.user_id},
        )
        return results["documents"][0] if results["documents"] else []

    def all_memories(self) -> list[dict]:
        """Return all stored memories for this user (for inspection)."""
        results = self.collection.get(where={"user_id": self.user_id})
        return [
            {"fact": doc, "metadata": meta}
            for doc, meta in zip(results["documents"], results["metadatas"])
        ]

    def clear(self) -> None:
        """Remove all memories for this user (for testing)."""
        results = self.collection.get(where={"user_id": self.user_id})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])


# Semantic Memory (rolling summary)

class SemanticMemory:
    """
    A rolling plain-text summary of the user's patterns, concerns, and progress.
    Updated at the end of each session by the LLM.
    Stored as a JSON file per user — simple and inspectable.
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.path = MEMORY_STORE_PATH / f"semantic_{user_id}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.summary = data.get("summary", "")
            self.updated = data.get("updated", "")
            self.session_count = data.get("session_count", 0)
        else:
            self.summary = ""
            self.updated = ""
            self.session_count = 0

    def _save(self) -> None:
        self.path.write_text(json.dumps({
            "user_id": self.user_id,
            "summary": self.summary,
            "updated": self.updated,
            "session_count": self.session_count,
        }, indent=2))

    def get(self) -> str:
        return self.summary

    def update(self, new_summary: str, session_id: str) -> None:
        self.summary = new_summary
        self.updated = datetime.now().isoformat()
        self.session_count += 1
        self._save()

    def clear(self) -> None:
        """Reset summary (for testing)."""
        self.summary = ""
        self.updated = ""
        self.session_count = 0
        if self.path.exists():
            self.path.unlink()


# Rule-based memory extraction (spaCy NER + therapy regex)

_RELATIONSHIP_WORDS = {
    "sister", "brother", "mother", "father", "mom", "dad",
    "partner", "husband", "wife", "friend", "therapist",
    "doctor", "colleague", "boss", "aunt", "uncle",
}


class MemoryExtractor:
    """
    Rule-based fact extraction: spaCy NER for person/relationship linking,
    therapy-specific regex for events, conditions, and life circumstances.
    No LLM — avoids the misalignment of using a therapy model for structured extraction.
    """

    def __init__(self) -> None:
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("  Downloading en_core_web_sm...")
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
            self.nlp = spacy.load("en_core_web_sm")
        print("  MemoryExtractor ready (spaCy NER + therapy regex)")

    def _extract_relationship_names(self, text: str) -> list[str]:
        """Link spaCy PERSON entities to nearby relationship words."""
        doc = self.nlp(text)
        facts = []
        for ent in doc.ents:
            if ent.label_ != "PERSON":
                continue
            start = max(0, ent.start - 8)
            context = [t.text.lower() for t in doc[start:ent.start]]
            for rel in _RELATIONSHIP_WORDS:
                if rel in context:
                    facts.append(f"User has a {rel} named {ent.text}")
                    break
        return facts

    def _extract_regex_facts(self, text: str) -> list[str]:
        """Apply therapy-specific regex patterns to a single user turn."""
        facts = []

        # Promotion missed
        if re.search(r"didn'?t get|not getting|rejected for|missed out on", text, re.I):
            if re.search(r"promoti?on", text, re.I):
                facts.append("User did not receive a promotion they had been working toward")

        # Promotion received
        if re.search(r"(?:got|received|was given)\s+(?:a\s+)?promotion", text, re.I):
            facts.append("User received a promotion")

        # Job loss (capture optional time reference)
        m = re.search(
            r"(?:lost my (?:job|position)|laid off|was fired|let go|made redundant)"
            r"(?:\s+(?:in|since)\s+([A-Za-z]+(?:\s+\d{4})?))?",
            text, re.I,
        )
        if m:
            when = f" in {m.group(1)}" if m.group(1) else ""
            facts.append(f"User lost their job{when}")

        # Profession
        m = re.search(
            r"(?:i'?m|i am|working as|i work as)\s+(?:an?\s+)?"
            r"(nurse|doctor|teacher|engineer|developer|designer|manager|therapist|"
            r"counselor|student|driver|writer|artist|chef|accountant|lawyer|architect)",
            text, re.I,
        )
        if m:
            facts.append(f"User works as a {m.group(1).lower()}")

        # Diagnosis / mental health condition
        m = re.search(
            r"(?:diagnosed with|dealing with|living with|struggling with|i have)\s+"
            r"((?:\w+\s+){0,3}(?:disorder|depression|anxiety|ptsd|ocd|adhd|bipolar|"
            r"schizophrenia|phobia|trauma))",
            text, re.I,
        )
        if m:
            facts.append(f"User is dealing with {m.group(1).strip()}")

        # Fear / phobia
        m = re.search(
            r"(?:scared of|fear of|afraid of|terrified of)\s+([\w\s]+?)(?:\.|,|\band\b|$)",
            text, re.I,
        )
        if m:
            fear = m.group(1).strip()
            if 1 <= len(fear.split()) <= 5:
                facts.append(f"User has a fear of {fear}")

        # Stopped medication
        if re.search(
            r"(?:stopped|off|quit|no longer taking)\s+(?:my\s+)?(?:medication|meds|antidepressants?|pills?)",
            text, re.I,
        ):
            facts.append("User has stopped taking medication")

        # Grief — family member passed away
        m = re.search(
            r"(?:my\s+)?(mother|father|mom|dad|sister|brother|partner|husband|wife|"
            r"friend|child|baby|grandfather|grandmother)\s+(?:passed away|died|is gone|passed)",
            text, re.I,
        )
        if m:
            facts.append(f"User's {m.group(1).lower()} passed away")

        # "lost my [family member]"
        m = re.search(
            r"lost my\s+(mother|father|mom|dad|sister|brother|partner|husband|wife|friend|child|baby)",
            text, re.I,
        )
        if m:
            facts.append(f"User lost their {m.group(1).lower()}")

        # Coping / comfort activity
        m = re.search(
            r"(?:find comfort in|helps me|cope by|i enjoy|i love)\s+([\w\s]+?ing)(?:\.|,|$| and )",
            text, re.I,
        )
        if m:
            activity = m.group(1).strip()
            if 2 <= len(activity.split()) <= 5:
                facts.append(f"User finds comfort in {activity.lower()}")

        return facts

    def extract_facts(self, conversation: list[dict]) -> list[str]:
        """
        Extract memorable facts from user turns only.
        Combines spaCy NER for names/relationships and regex for events/conditions.
        """
        user_texts = [m["content"] for m in conversation if m["role"] == "user"]
        if not user_texts:
            return []

        facts: list[str] = []
        seen: set[str] = set()
        for text in user_texts:
            for fact in self._extract_relationship_names(text) + self._extract_regex_facts(text):
                key = fact.lower()
                if key not in seen:
                    seen.add(key)
                    facts.append(fact)

        return facts[:5]

    def update_semantic_summary(self, current_summary: str, conversation: list[dict]) -> str:
        """
        Append new session facts to the rolling summary.
        No LLM — simple concatenation kept under 200 words.
        """
        new_facts = self.extract_facts(conversation)
        if not new_facts:
            return current_summary or ""

        prev = (
            current_summary.strip()
            if current_summary and current_summary != "(no previous summary)"
            else ""
        )
        new_part = "Recent facts: " + "; ".join(new_facts) + "."
        combined = (prev + " " + new_part).strip() if prev else new_part

        words = combined.split()
        if len(words) > 200:
            combined = " ".join(words[-200:])
        return combined




# Working memory (context window management)

class WorkingMemory:
    """Manages the in-session context window with a sliding window."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.turns: list[dict] = []

    def add(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})

    def get_context(self) -> list[dict]:
        """Return recent turns within the window."""
        return self.turns[-self.max_turns * 2:]  # *2 because each exchange = user + assistant

    def format_history(self) -> str:
        return "\n".join(
            f"{'USER' if t['role'] == 'user' else 'SAMA'}: {t['content']}"
            for t in self.get_context()
        )

    def clear(self) -> None:
        self.turns = []


# Memory prompt assembly

def build_memory_block(episodic_facts: list[str], semantic_summary: str) -> str:
    """Format memory for injection into the system prompt."""
    parts = []
    if semantic_summary:
        parts.append(f"About this person:\n{semantic_summary}")
    if episodic_facts:
        facts_text = "\n".join(f"- {f}" for f in episodic_facts)
        parts.append(f"Things they have shared:\n{facts_text}")
    if not parts:
        return ""
    return "<|memory|>\n" + "\n\n".join(parts) + "\n<|end|>"


# Tests

def run_test_extraction() -> None:
    print("\n=== Test: Fact Extraction ===")

    test_conversations = [
        [
            {"role": "user", "content": "My sister Emma and I had a big fight last week. She said I'm too needy and it really hurt."},
            {"role": "assistant", "content": "That sounds really painful — especially coming from a sibling. What happened during the fight?"},
            {"role": "user", "content": "She said I call her too much since I lost my job in March. I've been off medication since then too."},
            {"role": "assistant", "content": "That's a lot happening at once — losing your job and being off medication. How are you managing?"},
        ],
        [
            {"role": "user", "content": "I've been seeing a therapist named Dr. Patel but I stopped going two months ago because of the cost."},
            {"role": "assistant", "content": "Money making it hard to keep seeing Dr. Patel — that's a real barrier. What was helpful about those sessions?"},
            {"role": "user", "content": "She was helping me with my fear of abandonment. My dad left when I was six."},
        ],
    ]

    extractor = MemoryExtractor()
    for i, conv in enumerate(test_conversations):
        facts = extractor.extract_facts(conv)
        print(f"\n  Conversation {i+1}:")
        for f in facts:
            print(f"    {f}")

    print("\n  Key check: are the facts specific (names, dates, events)?")
    print("  Vague facts like 'User feels anxious' should NOT appear.")


def run_test_retrieval() -> None:
    print("\n=== Test: Memory Retrieval ===")

    user_id = "test_retrieval_user"
    memory = EpisodicMemory(user_id=user_id)
    memory.clear()

    # Store some facts
    facts_to_store = [
        "User has a sister named Emma who lives in Bristol",
        "User lost their job in March 2024 as a graphic designer",
        "User has been off antidepressant medication since March 2024",
        "User is afraid of abandonment since their father left when they were six",
        "User used to see a therapist named Dr. Patel but stopped due to cost",
        "User enjoys painting as a way to cope with stress",
        "User's partner is named Jamie and they have been together for three years",
    ]
    for fact in facts_to_store:
        memory.add(fact, session_id="test_session_1")

    print(f"  Stored {len(facts_to_store)} facts")

    # Test retrieval on related queries
    test_queries = [
        ("How did things go with your sister?", "Emma"),
        ("How are you managing without your medication?", "medication"),
        ("Have you been able to paint recently?", "painting"),
        ("How is Jamie doing?", "Jamie"),
        ("Are you still seeing Dr. Patel?", "Dr. Patel"),
    ]

    print(f"\n  {'Query':<45} {'Expected':<12} {'Top memory'}")
    correct = 0
    for query, expected_keyword, in test_queries:
        retrieved = memory.retrieve(query, k=3)
        top = retrieved[0] if retrieved else "(nothing)"
        found = expected_keyword.lower() in top.lower()
        correct += int(found)
        mark = "✓" if found else "✗"
        print(f"  {query[:43]:<45} {expected_keyword:<12} {mark}  {top[:50]}")

    print(f"\n  Retrieval accuracy: {correct}/{len(test_queries)}")
    memory.clear()


def run_her_moment() -> None:
    """
    The "Her" test: 5-session conversation where personal details are
    mentioned in session 1 — does Sama reference them in session 3 and 5
    without being prompted?
    """
    print("\n=== The 'Her' Moment Test (5 sessions) ===")

    user_id = "her_test_user"
    episodic = EpisodicMemory(user_id=user_id)
    episodic.clear()
    semantic = SemanticMemory(user_id=user_id)
    semantic.clear()
    extractor = MemoryExtractor()

    # Scripted sessions
    sessions = [
        # Session 1: introduce personal details
        [
            {"role": "user", "content": "I've been feeling really disconnected lately. My sister Maya keeps calling but I can't bring myself to answer."},
            {"role": "user", "content": "I also just found out I didn't get the promotion I've been working towards for two years."},
        ],
        # Session 2: different topic
        [
            {"role": "user", "content": "I had a really hard night. Couldn't sleep at all."},
            {"role": "user", "content": "I've been having a lot of anxious thoughts lately, mostly about work."},
        ],
        # Session 3: does Sama remember Maya and the promotion?
        [
            {"role": "user", "content": "I'm feeling a bit better today actually."},
        ],
        # Session 4: neutral
        [
            {"role": "user", "content": "I went for a walk today. First time in a week."},
        ],
        # Session 5: does Sama still remember?
        [
            {"role": "user", "content": "I think things are slowly getting better."},
        ],
    ]

    results = []
    for session_num, turns in enumerate(sessions, 1):
        session_id = f"her_session_{session_num}"
        print(f"\n  --- Session {session_num} ---")

        # Retrieve memories relevant to the first user message
        query = turns[0]["content"]
        memories = episodic.retrieve(query, k=8)
        semantic_summary = semantic.get()
        memory_block = build_memory_block(memories, semantic_summary)

        print(f"  Memories available: {len(memories)}")
        for m in memories[:3]:
            print(f"    · {m[:80]}")

        # Run through user turns (in real system, Sama would respond here)
        conversation = []
        for turn in turns:
            conversation.append(turn)

        # After session: extract and store facts
        new_facts = extractor.extract_facts(conversation)
        for fact in new_facts:
            episodic.add(fact, session_id=session_id)
        print(f"  New facts stored: {new_facts}")

        # Update semantic summary
        new_summary = extractor.update_semantic_summary(semantic.get(), conversation)
        semantic.update(new_summary, session_id=session_id)
        print(f"  Semantic summary: {new_summary[:120]}...")

        results.append({
            "session": session_num,
            "memories_at_start": memories,
            "new_facts": new_facts,
            "semantic_summary": new_summary,
            "memory_block_snippet": memory_block[:200] if memory_block else "(empty)",
        })

    all_memories = episodic.all_memories()
    print(f"\n  Total memories after 5 sessions: {len(all_memories)}")
    print(f"  'Her' moment check: by session 3, does the memory block mention Maya or the promotion?")
    session3_memories = results[2]["memories_at_start"]
    has_maya = any("maya" in m.lower() or "sister" in m.lower() for m in session3_memories)
    has_promotion = any("promot" in m.lower() or "work" in m.lower() for m in session3_memories)
    print(f"    Remembers sister (Maya): {'✓' if has_maya else '✗'}")
    print(f"    Remembers promotion:     {'✓' if has_promotion else '✗'}")

    out = RESULTS_DIR / "her_moment_test.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\n  Results saved → {out}")

    # Clean up test data
    episodic.clear()


def run_demo() -> None:
    """Quick 3-session demo showing memory store and retrieval."""
    print("\n=== 3-Session Memory Demo ===")

    user_id = "demo_user"
    memory = EpisodicMemory(user_id=user_id)
    memory.clear()
    semantic = SemanticMemory(user_id=user_id)

    demo_facts = [
        "User has a brother named Tom who struggles with addiction",
        "User is a nurse and finds their job emotionally draining",
        "User has been having panic attacks since their mother passed away in January",
        "User finds comfort in gardening and cooking",
    ]

    print("\n  Session 1 — storing facts:")
    for fact in demo_facts:
        memory.add(fact, "demo_session_1")
        print(f"    + {fact}")

    semantic.update(
        "User is a nurse who is grieving their mother's death in January. They have a "
        "brother Tom who has addiction issues. They cope through gardening and cooking but "
        "are experiencing panic attacks related to the grief.",
        "demo_session_1",
    )

    print("\n  Session 2 — retrieving relevant memories:")
    queries = [
        "I've been feeling really drained after work this week.",
        "I was thinking about my brother today.",
        "I had another panic attack this morning.",
    ]
    for q in queries:
        retrieved = memory.retrieve(q, k=3)
        print(f"\n  Query: {q}")
        for r in retrieved[:2]:
            print(f"    → {r}")

    print(f"\n  Semantic summary: {semantic.get()[:200]}")

    memory.clear()


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="3-session demo")
    parser.add_argument("--test_extraction", action="store_true", help="Test fact extraction quality")
    parser.add_argument("--test_retrieval", action="store_true", help="Test memory retrieval relevance")
    parser.add_argument("--her_moment", action="store_true", help="Full 5-session Her test")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.test_extraction:
        run_test_extraction()
    elif args.test_retrieval:
        run_test_retrieval()
    elif args.her_moment:
        run_her_moment()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
