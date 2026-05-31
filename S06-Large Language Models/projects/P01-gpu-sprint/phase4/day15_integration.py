"""
Day 15 — Full End-to-End System

Wires together every component from the sprint:
  1. Safety input guard (keyword-based, fast)
  2. Episodic memory retrieval (from ChromaDB)
  3. RAG retrieval (FAISS + reranker from Day 8)
  4. Prompt assembly
  5. Fine-tuned model generation (via vLLM or HuggingFace)
  6. Memory extraction and update (after each turn)

Also includes:
  - 20-question evaluation vs. plain API baseline
  - Automated metrics (question rate, advice-avoidance, citation rate)

Run:
    python day15_integration.py --chat             # interactive chat
    python day15_integration.py --evaluate         # run 20-question eval suite
    python day15_integration.py --demo             # 5-turn scripted demo

For vLLM serving (recommended):
    python -m vllm.entrypoints.openai.api_server \
        --model <your-day5-checkpoint> \
        --port 8000
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import torch
from sentence_transformers import CrossEncoder, SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Configuration — point these at your actual checkpoints
FINE_TUNED_MODEL = "Qwen/Qwen2.5-7B-Instruct"       # replace with your Day 5 checkpoint
EMBED_MODEL = "BAAI/bge-base-en-v1.5"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
VLLM_URL = "http://localhost:8000/v1"
USE_VLLM = False    # set True if vLLM server is running

RAG_INDEX_PATH = Path(__file__).parent.parent / "phase3" / "rag_index"


# Safety layer

UNSAFE_PATTERNS = [
    r"\b(how to (make|build|create) (a )?(weapon|bomb|explosive))\b",
    r"\b(step.by.step.*(hack|phish|exploit))\b",
    r"\b(bypass.*(authentication|security|firewall))\b",
]

def safety_check(message: str) -> dict:
    msg_lower = message.lower()
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, msg_lower):
            return {
                "safe": False,
                "action": "block",
                "response": "I can't help with that request.",
            }
    return {"safe": True, "action": "continue"}


# Memory system

class EpisodicMemory:
    """Simple vector store for cross-session episodic memory."""

    def __init__(self, embedder: SentenceTransformer):
        self.embedder = embedder
        self.memories: list[dict] = []
        self.index: faiss.Index | None = None
        self._dim = 768

    def add(self, fact: str, session_id: str = "default") -> None:
        emb = self.embedder.encode([fact], normalize_embeddings=True)[0]
        self.memories.append({"text": fact, "session": session_id, "ts": datetime.now().isoformat()})
        if self.index is None:
            self.index = faiss.IndexFlatIP(len(emb))
        self.index.add(np.array([emb], dtype=np.float32))

    def retrieve(self, query: str, k: int = 5) -> list[str]:
        if not self.memories or self.index is None:
            return []
        emb = self.embedder.encode([query], normalize_embeddings=True).astype(np.float32)
        k = min(k, len(self.memories))
        _, indices = self.index.search(emb, k)
        return [self.memories[i]["text"] for i in indices[0] if i < len(self.memories)]

    def extract_facts(self, conversation: list[dict], generator_fn) -> list[str]:
        """Use the LLM to extract memorable facts from a conversation turn."""
        history = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in conversation[-4:])
        prompt = (
            "Extract up to 3 specific facts the user shared about themselves. "
            "Format: one fact per line, starting with 'User '. Only concrete details, not vague feelings.\n\n"
            f"Conversation:\n{history}\n\nFacts:"
        )
        response = generator_fn(prompt, max_new_tokens=100)
        facts = [line.strip() for line in response.split("\n") if line.strip().startswith("User")]
        return facts


# RAG retrieval

class KnowledgeRetriever:
    def __init__(self, embedder: SentenceTransformer):
        self.embedder = embedder
        self.reranker = CrossEncoder(RERANK_MODEL)
        self.docs: list[str] = []
        self.index: faiss.Index | None = None
        self._load_index()

    def _load_index(self) -> None:
        docs_path = RAG_INDEX_PATH / "docs.json"
        index_path = RAG_INDEX_PATH / "faiss.index"
        if docs_path.exists() and index_path.exists():
            with open(docs_path) as f:
                self.docs = json.load(f)
            self.index = faiss.read_index(str(index_path))
            print(f"  RAG index loaded: {len(self.docs):,} docs")
        else:
            print("  RAG index not found. Run day08_rag.py --build_index first.")

    def retrieve(self, query: str, k_retrieve: int = 15, k_final: int = 3) -> list[str]:
        if not self.docs or self.index is None:
            return []
        emb = self.embedder.encode([query], normalize_embeddings=True).astype(np.float32)
        _, indices = self.index.search(emb, k_retrieve)
        candidates = [self.docs[i] for i in indices[0] if i < len(self.docs)]
        pairs = [(query, doc) for doc in candidates]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(scores, candidates), reverse=True)
        return [doc for _, doc in ranked[:k_final]]


# LLM backend

class LLMBackend:
    def __init__(self, use_vllm: bool = USE_VLLM):
        self.use_vllm = use_vllm
        self.model = None
        self.tokenizer = None
        self.client = None
        self._load()

    def _load(self) -> None:
        if self.use_vllm:
            try:
                from openai import OpenAI
                self.client = OpenAI(base_url=VLLM_URL, api_key="dummy")
                print(f"  Using vLLM at {VLLM_URL}")
            except Exception as e:
                print(f"  vLLM unavailable ({e}), falling back to HuggingFace")
                self.use_vllm = False
        if not self.use_vllm:
            self.model = AutoModelForCausalLM.from_pretrained(
                FINE_TUNED_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(FINE_TUNED_MODEL)
            print(f"  Using HuggingFace: {FINE_TUNED_MODEL}")

    @torch.no_grad()
    def generate(self, prompt: str, max_new_tokens: int = 300, system: str = "") -> str:
        if self.use_vllm:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = self.client.chat.completions.create(
                model=FINE_TUNED_MODEL,
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=0.7,
            )
            return resp.choices[0].message.content
        else:
            if system:
                text = f"<|system|>\n{system}\n<|user|>\n{prompt}\n<|assistant|>\n"
            else:
                text = f"<|user|>\n{prompt}\n<|assistant|>\n"
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=2048).to("cuda")
            out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True, temperature=0.7, top_p=0.9)
            return self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


# Main assistant

SYSTEM_PROMPT = """You are a helpful domain assistant. You:
- Answer questions accurately using your knowledge and retrieved context
- Cite relevant information from the context when available
- Ask follow-up questions when the user's request is unclear
- Remember details the user has shared with you"""


class DomainAssistant:
    def __init__(self):
        print("Initialising DomainAssistant...")
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self.memory = EpisodicMemory(self.embedder)
        self.retriever = KnowledgeRetriever(self.embedder)
        self.llm = LLMBackend()
        self.history: list[dict] = []
        print("Ready.\n")

    def _assemble_prompt(self, user_message: str) -> tuple[str, str]:
        memories = self.memory.retrieve(user_message, k=5)
        rag_docs = self.retriever.retrieve(user_message, k_final=3)

        memory_block = ""
        if memories:
            memory_block = "What you know about this user:\n" + "\n".join(f"- {m}" for m in memories) + "\n\n"

        rag_block = ""
        if rag_docs:
            rag_block = "Relevant context:\n" + "\n---\n".join(rag_docs[:2]) + "\n\n"

        system = SYSTEM_PROMPT
        if memory_block or rag_block:
            system += f"\n\n{memory_block}{rag_block}"

        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in self.history[-6:]
        )
        full_prompt = f"{history_text}\nUser: {user_message}" if history_text else user_message
        return full_prompt, system

    def chat(self, user_message: str) -> str:
        # 1. Safety check
        safety = safety_check(user_message)
        if not safety["safe"]:
            return safety["response"]

        # 2. Assemble prompt with memory + RAG
        prompt, system = self._assemble_prompt(user_message)

        # 3. Generate
        t0 = time.time()
        response = self.llm.generate(prompt, system=system)
        latency = round(time.time() - t0, 2)

        # 4. Update history
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": response})

        # 5. Extract and store new facts from this turn
        new_facts = self.memory.extract_facts(
            self.history[-4:],
            lambda p, **kw: self.llm.generate(p, **kw)
        )
        for fact in new_facts:
            self.memory.add(fact)

        return response


# Automated metrics

def compute_metrics(responses: list[str]) -> dict:
    question_rate = round(sum("?" in r for r in responses) / len(responses), 2)
    advice_patterns = ["you should", "try to", "have you tried", "i recommend", "you need to"]
    advice_rate = round(sum(any(p in r.lower() for p in advice_patterns) for r in responses) / len(responses), 2)
    avg_len = round(sum(len(r.split()) for r in responses) / len(responses), 1)
    return {"question_rate": question_rate, "advice_rate": advice_rate, "avg_response_words": avg_len}


EVAL_QUESTIONS = [
    "What is machine learning and how does it work?",
    "Can you explain neural networks simply?",
    "What's the difference between AI and machine learning?",
    "How does a language model generate text?",
    "What is fine-tuning and why is it useful?",
    "Explain attention mechanism in transformers.",
    "What is overfitting and how do you prevent it?",
    "How does retrieval augmented generation work?",
    "What are the pros and cons of large language models?",
    "How is RLHF used to align language models?",
    "What is the difference between GPT and BERT?",
    "Explain embeddings in machine learning.",
    "What is transfer learning?",
    "How does quantization affect model performance?",
    "What is the purpose of the attention mask in transformers?",
    "What is prompt engineering?",
    "How do you evaluate the quality of an LLM?",
    "What is the difference between inference and training?",
    "Explain tokenization in NLP.",
    "What makes a language model 'hallucinate'?",
]


def run_evaluation(assistant: DomainAssistant) -> dict:
    print("\nRunning 20-question evaluation...")

    # Baseline: plain HF model, no RAG, no memory
    baseline_llm = LLMBackend(use_vllm=False)

    assistant_responses = []
    baseline_responses = []

    for i, q in enumerate(EVAL_QUESTIONS):
        print(f"  [{i+1:2d}/20] {q[:60]}")
        a_resp = assistant.chat(q)
        b_resp = baseline_llm.generate(q)
        assistant_responses.append(a_resp)
        baseline_responses.append(b_resp)

    assistant_metrics = compute_metrics(assistant_responses)
    baseline_metrics = compute_metrics(baseline_responses)

    result = {
        "assistant_metrics": assistant_metrics,
        "baseline_metrics": baseline_metrics,
        "questions": EVAL_QUESTIONS,
        "assistant_responses": assistant_responses,
        "baseline_responses": baseline_responses,
    }

    print(f"\n{'─'*55}")
    print(f"  {'Metric':<25} {'Assistant':<15} {'Baseline'}")
    for metric in assistant_metrics:
        print(f"  {metric:<25} {str(assistant_metrics[metric]):<15} {baseline_metrics[metric]}")

    return result


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true", help="Interactive chat loop")
    parser.add_argument("--evaluate", action="store_true", help="Run 20-question eval")
    parser.add_argument("--demo", action="store_true", help="5-turn scripted demo")
    args = parser.parse_args()

    assistant = DomainAssistant()

    if args.chat:
        print("Chat with your domain assistant. Type 'quit' to exit.\n")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break
            response = assistant.chat(user_input)
            print(f"\nAssistant: {response}\n")

    elif args.evaluate:
        result = run_evaluation(assistant)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"day15_evaluation_{stamp}.json"
        out.write_text(json.dumps(result, indent=2))
        print(f"\nFull evaluation saved → {out}")

    elif args.demo:
        demo_turns = [
            "My name is Alex. I'm learning about machine learning for the first time.",
            "What's the best way to start with neural networks?",
            "I'm worried I don't have enough math background. I only know basic algebra.",
            "Can you recommend what I should learn first given my background?",
            "Do you remember what I told you about my background?",
        ]
        print("=== 5-turn scripted demo ===\n")
        for turn in demo_turns:
            print(f"User: {turn}")
            response = assistant.chat(turn)
            print(f"Assistant: {response}\n")
            print(f"  [Memories stored: {len(assistant.memory.memories)}]\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
