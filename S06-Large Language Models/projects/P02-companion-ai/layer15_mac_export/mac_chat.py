"""
Layer 15 — Mac Chat (run this on your MacBook)
================================================
Full Sama chat UI for MacBook with 18 GB RAM.
Uses the Q4_K_M GGUF model (~4 GB) via llama-cpp-python with Metal GPU.
All other layers (safety, RAG, memory) run on CPU — no changes needed.

Expected folder layout on Mac:
    sama_mac/
    ├── mac_chat.py                        ← this file
    ├── requirements_mac.txt
    ├── checkpoints/
    │   ├── sama_q4km.gguf                ← 4 GB model
    │   ├── crisis_classifier/             ← 476 MB safety model
    │   └── therapy_embedder/             ← 419 MB embedder
    └── data/
        └── splits/
            └── rag.json                   ← CBT/DBT knowledge

Setup (one time):
    pip install -r requirements_mac.txt

Run:
    python mac_chat.py
    python mac_chat.py --region US         # US crisis resources (988)
    python mac_chat.py --user yourname     # persist memory across sessions
"""

import argparse
import json
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

GGUF_PATH            = BASE_DIR / "results" / "sama_q8.gguf"
CRISIS_CLASSIFIER    = BASE_DIR / "checkpoints" / "crisis_classifier"
THERAPY_EMBEDDER     = BASE_DIR / "checkpoints" / "therapy_embedder"
RAG_JSON             = BASE_DIR / "data" / "splits" / "rag.json"
MEMORY_STORE         = BASE_DIR / "checkpoints" / "memory_store"


SAMA_PERSONA = """You are Sama — a compassionate AI companion for emotional support.
IMPORTANT: You are NOT a licensed therapist, NOT a human, and NOT a medical professional.
You are an AI companion. If asked, always say you are an AI, not a human or therapist.
Your role: listen, validate feelings, ask one gentle question at a time.
You do NOT give diagnoses, step-by-step plans, or claim professional credentials.
Keep responses warm, concise (2-4 sentences), and focused on the person."""

CRISIS_UK = (
    "I want to make sure you're safe right now. Please reach out to Samaritans: "
    "call 116 123 (free, 24/7) or text SHOUT to 85258. "
    "If you're in immediate danger, call 999 or go to your nearest A&E."
)
CRISIS_US = (
    "I want to make sure you're safe right now. Please call or text 988 "
    "(Suicide and Crisis Lifeline, free, 24/7). You can also text HOME to 741741. "
    "If you're in immediate danger, call 911 or go to your nearest emergency room."
)
CRISIS_DEFAULT = (
    "I want to make sure you're safe. Please reach out to a crisis line in your country "
    "or go to your nearest emergency room if you're in immediate danger."
)

# Phrases that always hard-redirect, no model call needed
_HARD_CRISIS_RE = re.compile(
    r"kill\s+my\s*self|end\s+my\s+life|take\s+my\s+(own\s+)?life|"
    r"suicid(e|al|ing)|want\s+to\s+die|hang(ing)?\s+my\s*self|"
    r"slit\s+my\s+(wrists?|throat)|jump(ing)?\s+(off|from)|"
    r"no\s+reason\s+to\s+live|not\s+worth\s+living|don'?t\s+want\s+to\s+be\s+alive|"
    r"ready\s+to\s+end\s+it|wrote\s+a\s+goodbye\s+note|said\s+my\s+goodbyes|"
    r"stockpiled\s+my\s+medication|have\s+the\s+pills\s+ready|took\s+the\s+lethal\s+dose",
    re.IGNORECASE,
)

# Patterns that the model should never output (therapist identity artifacts)
_STRIP_PATTERNS = [
    re.compile(r"[Aa]s a therapist[,\s].*?(?=\n|$)"),
    re.compile(r"[Ii] work with my clients.*?(?=\n|$)"),
    re.compile(r"[Pp]lease contact me at.*?(?=\n|$)"),
    re.compile(r"[Mm]y private practice.*?(?=\n|$)"),
    re.compile(r"[Ii] am a licensed.*?(?=\n|$)"),
    re.compile(r"<(PHONE_NUMBER|LOCATION|DATE_TIME|NAME)>"),
]

STOP_STRINGS = ["<|end|>", "<|user|>", "\n\nUser:", "\nUSER:", "\nUser:", "[INST]"]


def _clean_response(text: str) -> str:
    """Strip therapist-identity artifacts from generated text."""
    for pat in _STRIP_PATTERNS:
        text = pat.sub("", text)
    return text.strip()


class SafetyLayer:
    """Two-stage safety: keyword regex + RoBERTa classifier."""

    def __init__(self, region: str = "UK") -> None:
        self.region = region
        self.crisis_response = {
            "UK": CRISIS_UK, "US": CRISIS_US
        }.get(region, CRISIS_DEFAULT)
        self.soft_response = (
            "I'm here with you. I want to check in directly — "
            "are you having any thoughts of hurting yourself or ending your life?"
        )
        self._classifier = None
        self._load_classifier()

    def _load_classifier(self) -> None:
        if not CRISIS_CLASSIFIER.exists():
            print("  Safety: crisis_classifier not found — keyword-only mode")
            return
        try:
            from transformers import pipeline
            self._classifier = pipeline(
                "text-classification",
                model=str(CRISIS_CLASSIFIER),
                top_k=None,
                device=-1,  # CPU on Mac
            )
            print("  Safety: RoBERTa crisis classifier loaded (CPU)")
        except Exception as e:
            print(f"  Safety: classifier load failed ({e}) — keyword-only mode")

    def check(self, message: str, history: list[dict] | None = None) -> dict:
        # Stage 1 — keyword hard redirect
        if _HARD_CRISIS_RE.search(message):
            return {"action": "hard_redirect", "prob": 1.0, "response": self.crisis_response}

        if self._classifier is None:
            return {"action": "continue", "prob": 0.0, "response": ""}

        # Stage 2 — ML classifier on last 3 turns + current message
        context_parts = []
        if history:
            for turn in history[-3:]:
                context_parts.append(turn.get("content", ""))
        context_parts.append(message)
        context = " ".join(context_parts)[:512]

        try:
            scores = self._classifier(context)[0]
            crisis_prob = next(
                (s["score"] for s in scores if s["label"] in ("LABEL_1", "crisis", "1")), 0.0
            )
            if crisis_prob > 0.85:
                return {"action": "hard_redirect", "prob": crisis_prob, "response": self.crisis_response}
            if crisis_prob > 0.68:
                return {"action": "soft_check", "prob": crisis_prob, "response": self.soft_response}
            return {"action": "continue", "prob": crisis_prob, "response": ""}
        except Exception:
            return {"action": "continue", "prob": 0.0, "response": ""}


class RAGLayer:
    """FAISS retrieval over CBT/DBT knowledge using therapy embedder."""

    def __init__(self) -> None:
        self._index = None
        self._chunks: list[dict] = []
        self._embedder = None
        self._load()

    def _load(self) -> None:
        if not RAG_JSON.exists():
            print("  RAG: rag.json not found — RAG disabled")
            return
        if not THERAPY_EMBEDDER.exists():
            print("  RAG: therapy_embedder not found — RAG disabled")
            return
        try:
            import faiss
            import numpy as np
            from sentence_transformers import SentenceTransformer

            with open(RAG_JSON) as f:
                docs = json.load(f)

            self._chunks = []
            for doc in docs:
                text = doc.get("content") or doc.get("text") or ""
                if text:
                    self._chunks.append({"text": text[:500], "title": doc.get("title", "")})

            self._embedder = SentenceTransformer(str(THERAPY_EMBEDDER))
            texts = [c["text"] for c in self._chunks]
            vecs = self._embedder.encode(texts, convert_to_numpy=True).astype("float32")
            faiss.normalize_L2(vecs)
            dim = vecs.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(vecs)
            print(f"  RAG: {len(self._chunks)} chunks indexed")
        except Exception as e:
            print(f"  RAG: load failed ({e}) — RAG disabled")

    def retrieve(self, query: str, k: int = 2) -> list[dict]:
        if self._index is None or self._embedder is None:
            return []
        try:
            import faiss
            import numpy as np
            vec = self._embedder.encode([query], convert_to_numpy=True).astype("float32")
            faiss.normalize_L2(vec)
            _, idxs = self._index.search(vec, k)
            return [self._chunks[i] for i in idxs[0] if i < len(self._chunks)]
        except Exception:
            return []


class MemoryLayer:
    """ChromaDB episodic memory + spaCy fact extraction."""

    def __init__(self, user_id: str = "mac_user") -> None:
        self.user_id = user_id
        self._collection = None
        self._embedder = None
        self._nlp = None
        self._load()

    def _load(self) -> None:
        MEMORY_STORE.mkdir(exist_ok=True)
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            client = chromadb.PersistentClient(path=str(MEMORY_STORE))
            self._collection = client.get_or_create_collection("episodic_memory")
            self._embedder = SentenceTransformer(str(THERAPY_EMBEDDER))
            print("  Memory: ChromaDB episodic memory loaded")
        except Exception as e:
            print(f"  Memory: load failed ({e}) — memory disabled")

        try:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
        except Exception:
            self._nlp = None

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        if self._collection is None or self._embedder is None:
            return []
        try:
            vec = self._embedder.encode([query]).tolist()
            results = self._collection.query(
                query_embeddings=vec, n_results=k,
                where={"user_id": self.user_id}
            )
            docs = results.get("documents", [[]])[0]
            return [d for d in docs if d]
        except Exception:
            return []

    def store(self, facts: list[str]) -> None:
        if self._collection is None or not facts:
            return
        try:
            import uuid
            vecs = self._embedder.encode(facts).tolist()
            self._collection.add(
                documents=facts,
                embeddings=vecs,
                ids=[str(uuid.uuid4()) for _ in facts],
                metadatas=[{"user_id": self.user_id} for _ in facts],
            )
        except Exception:
            pass

    def extract_facts(self, text: str) -> list[str]:
        facts = []
        if self._nlp:
            doc = self._nlp(text)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    window = text[max(0, ent.start_char - 40): ent.start_char].lower()
                    rel_words = ["sister", "brother", "mother", "father", "partner",
                                 "friend", "therapist", "doctor", "husband", "wife"]
                    for rel in rel_words:
                        if rel in window:
                            facts.append(f"User has a {rel} named {ent.text}")
                            break

        patterns = [
            (re.compile(r"(?:lost|losing)\s+(?:my\s+)?job", re.I), "User lost their job"),
            (re.compile(r"(?:got|received)\s+(?:a\s+)?promotion", re.I), "User received a promotion"),
            (re.compile(r"(?:dealing|diagnosed|struggling)\s+with\s+([\w\s]+disorder|anxiety|depression|ptsd|ocd)", re.I), lambda m: f"User is dealing with {m.group(1)}"),
            (re.compile(r"(?:scared|afraid|fear)\s+of\s+([\w\s]+)", re.I), lambda m: f"User has a fear of {m.group(1).strip()}"),
            (re.compile(r"(?:my|a)\s+(\w+)\s+(?:passed away|died)", re.I), lambda m: f"User's {m.group(1)} passed away"),
            (re.compile(r"(?:I'?m|I\s+am)\s+(?:a|an)\s+([\w\s]+(?:nurse|doctor|teacher|engineer|developer|student))", re.I), lambda m: f"User works as {m.group(1).strip()}"),
            (re.compile(r"off\s+(?:my\s+)?medication", re.I), "User has stopped taking medication"),
        ]
        for pat, result in patterns:
            m = pat.search(text)
            if m:
                facts.append(result(m) if callable(result) else result)

        return list(dict.fromkeys(facts))  # deduplicate, preserve order

    def clear(self) -> None:
        if self._collection is None:
            return
        try:
            ids = self._collection.get(where={"user_id": self.user_id})["ids"]
            if ids:
                self._collection.delete(ids=ids)
        except Exception:
            pass


class LlamaCppBackend:
    """
    Drop-in LLM backend using llama-cpp-python with Metal GPU.
    Replaces the HuggingFace transformers backend from Layer 13.
    """

    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"GGUF model not found at {model_path}\n"
                "Run day17_mac_export.py --all on the server first, then download sama_q4km.gguf"
            )
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("llama-cpp-python not installed. Run: pip install -r requirements_mac.txt")

        print(f"  LLM: loading {model_path.name} with Metal GPU...")
        from llama_cpp import Llama
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_gpu_layers=-1,   # -1 = all layers on Metal GPU
            n_threads=8,
            verbose=False,
        )
        print("  LLM: ready")

    def _build_prompt(self, system: str, history: list[dict], user_message: str) -> str:
        history_text = "\n".join(
            f"{'USER' if m['role'] == 'user' else 'SAMA'}: {m['content']}"
            for m in history[-20:]
        )
        return (
            f"<|system|>\n{system}\n"
            f"{history_text + chr(10) if history_text else ''}"
            f"<|user|>\n{user_message}\n<|assistant|>\n"
        )

    def generate(self, system: str, history: list[dict], user_message: str,
                 max_tokens: int = 250) -> str:
        prompt = self._build_prompt(system, history, user_message)
        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            repeat_penalty=1.3,      # prevents repetition loops
            stop=STOP_STRINGS,
        )
        text = output["choices"][0]["text"]
        return _clean_response(text)

    def stream(self, system: str, history: list[dict], user_message: str,
               max_tokens: int = 250):
        """Generator — yields token strings one at a time."""
        prompt = self._build_prompt(system, history, user_message)
        for chunk in self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            repeat_penalty=1.3,
            stop=STOP_STRINGS,
            stream=True,
        ):
            token = chunk["choices"][0]["text"]
            if any(s in token for s in STOP_STRINGS):
                break
            yield token


class SamaMacCompanion:
    """Full Sama pipeline for Mac — same structure as SamaCompanion (Layer 13)."""

    def __init__(self, user_id: str = "mac_user", region: str = "UK") -> None:
        self.user_id = user_id
        self.region = region
        self.history: list[dict] = []

        print("\nLoading Sama for Mac...")
        self.safety  = SafetyLayer(region=region)
        self.rag     = RAGLayer()
        self.memory  = MemoryLayer(user_id=user_id)
        self.llm     = LlamaCppBackend(GGUF_PATH)
        print("All layers loaded.\n")

    def _assemble_system(self, memories: list[str], rag_chunks: list[dict]) -> str:
        parts = [SAMA_PERSONA]
        if rag_chunks:
            rag_text = "\n".join(f"- {c['text']}" for c in rag_chunks)
            parts.append(f"\nRelevant techniques:\n{rag_text}")
        if memories:
            mem_text = "\n".join(f"- {m}" for m in memories)
            parts.append(f"\nThings this person has shared:\n{mem_text}")
        return "\n".join(parts)


class SamaMacChat:
    """Streaming wrapper around SamaMacCompanion for Gradio."""

    def __init__(self, user_id: str = "mac_user", region: str = "UK") -> None:
        self.companion = SamaMacCompanion(user_id=user_id, region=region)
        self.last_meta: dict = {}
        self.conversation_log: list[dict] = []

    def stream(self, user_message: str):
        t0 = time.time()

        # Safety check
        safety = self.companion.safety.check(user_message, self.companion.history)
        self.last_meta = {
            "safety_action": safety["action"],
            "safety_prob": round(safety["prob"], 3),
            "memories_retrieved": 0,
            "rag_chunks_retrieved": 0,
            "latency_ms": 0,
        }

        if safety["action"] != "continue":
            response = safety["response"]
            self.companion.history.append({"role": "user", "content": user_message})
            self.companion.history.append({"role": "assistant", "content": response})
            self.last_meta["latency_ms"] = round((time.time() - t0) * 1000)
            self._log_turn(user_message, response)
            yield response
            return

        # Memory + RAG retrieval
        memories   = self.companion.memory.retrieve(user_message)
        rag_chunks = self.companion.rag.retrieve(user_message)
        self.last_meta["memories_retrieved"]   = len(memories)
        self.last_meta["rag_chunks_retrieved"] = len(rag_chunks)

        # Build system prompt
        system = self.companion._assemble_system(memories, rag_chunks)

        # Stream from llama-cpp-python
        accumulated = []
        for token in self.companion.llm.stream(system, self.companion.history, user_message):
            accumulated.append(token)
            yield "".join(accumulated)

        response_text = _clean_response("".join(accumulated))

        # Update history and extract new facts
        self.companion.history.append({"role": "user", "content": user_message})
        self.companion.history.append({"role": "assistant", "content": response_text})

        new_facts = self.companion.memory.extract_facts(user_message)
        if new_facts:
            self.companion.memory.store(new_facts)

        self.last_meta["latency_ms"] = round((time.time() - t0) * 1000)
        self._log_turn(user_message, response_text)

    def clear(self) -> None:
        self.companion.history = []
        self.conversation_log = []
        self.last_meta = {}
        self.companion.memory.clear()

    def save_conversation(self) -> str:
        if not self.conversation_log:
            return ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"conversation_{ts}.json"
        out.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "user_id": self.companion.user_id,
            "region": self.companion.region,
            "turns": self.conversation_log,
        }, indent=2))
        return str(out)

    def _log_turn(self, user: str, sama: str) -> None:
        self.conversation_log.append({
            "turn": len(self.conversation_log) + 1,
            "user": user,
            "sama": sama,
            **self.last_meta,
        })


def build_interface(sama: SamaMacChat):
    import gradio as gr

    with gr.Blocks(title="Sama") as demo:
        gr.Markdown("# Sama")
        gr.Markdown("A compassionate companion — not a therapist, just a listener.")

        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(label="", height=520, show_label=False)
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="How are you feeling today?",
                        show_label=False, lines=1, scale=9, autofocus=True,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

            with gr.Column(scale=1, min_width=200):
                gr.Markdown("### Session")
                memories_display = gr.Number(label="Memories retrieved", value=0, interactive=False)
                rag_display      = gr.Number(label="RAG chunks",          value=0, interactive=False)
                safety_display   = gr.Textbox(label="Safety",             value="—", interactive=False)
                latency_display  = gr.Number(label="Latency (ms)",        value=0, interactive=False)

                gr.Markdown("### Actions")
                save_btn    = gr.Button("Save conversation")
                clear_btn   = gr.Button("Clear / reset")
                save_status = gr.Textbox(label="Saved to", value="", interactive=False)

        def respond(message, chat_history):
            if not message.strip():
                yield "", chat_history, 0, 0, "—", 0
                return
            chat_history = chat_history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": ""},
            ]
            for chunk in sama.stream(message):
                chat_history[-1]["content"] = chunk
                meta = sama.last_meta
                yield (
                    "",
                    chat_history,
                    meta.get("memories_retrieved", 0),
                    meta.get("rag_chunks_retrieved", 0),
                    meta.get("safety_action", "—"),
                    meta.get("latency_ms", 0),
                )

        def save_conv():
            path = sama.save_conversation()
            return path if path else "Nothing to save yet."

        def clear_conv():
            sama.clear()
            return [], 0, 0, "—", 0, ""

        outputs = [msg_box, chatbot, memories_display, rag_display, safety_display, latency_display]
        msg_box.submit(respond, [msg_box, chatbot], outputs)
        send_btn.click(respond, [msg_box, chatbot], outputs)
        save_btn.click(save_conv, outputs=save_status)
        clear_btn.click(clear_conv, outputs=[chatbot, memories_display, rag_display,
                                             safety_display, latency_display, save_status])
    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Sama chat — Mac edition")
    parser.add_argument("--region", default="UK", choices=["UK", "US", "default"])
    parser.add_argument("--user",   default="mac_user", help="User ID for memory")
    parser.add_argument("--port",   type=int, default=7860)
    args = parser.parse_args()

    sama = SamaMacChat(user_id=args.user, region=args.region)

    import gradio as gr
    demo = build_interface(sama)
    demo.queue()
    demo.launch(server_port=args.port, show_error=True, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
