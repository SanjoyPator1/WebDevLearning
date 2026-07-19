"""
memory/manager.py

MemoryManager — the single interface for all three memory tiers:
  1. Working memory  (in-process conversation window)
  2. Episodic memory (SQLite: what happened when)
  3. Semantic memory (JSON: persistent facts about the user)
"""
import json
import re
from datetime import datetime
from typing import Any

import pytz
import config
from scout.memory.db import get_connection


# ── Semantic memory (JSON) ─────────────────────────────────────────────────────

def _load_semantic() -> dict:
    if config.USER_MEMORY_PATH.exists():
        try:
            return json.loads(config.USER_MEMORY_PATH.read_text())
        except Exception:
            pass
    return {"facts": [], "preferences": [], "lists": {}}


def _save_semantic(data: dict) -> None:
    config.USER_MEMORY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── MemoryManager ──────────────────────────────────────────────────────────────

class MemoryManager:
    """Manages all three memory tiers for a single user session."""

    def __init__(self) -> None:
        # Working memory: list of {"role": "user"|"assistant", "content": str}
        self._working: list[dict] = []

    # ── Working memory ─────────────────────────────────────────────────────────

    def add_turn(self, role: str, content: str) -> None:
        """Append a conversation turn to working memory."""
        self._working.append({"role": role, "content": content})
        # Keep only the last N turns
        if len(self._working) > config.WORKING_MEMORY_WINDOW:
            self._working = self._working[-config.WORKING_MEMORY_WINDOW:]

    def get_working_context(self) -> list[dict]:
        """Return current working memory turns."""
        return list(self._working)

    def clear_working(self) -> None:
        """Wipe the in-session conversation history."""
        self._working = []

    # ── Episodic memory ────────────────────────────────────────────────────────

    def save_episode(
        self,
        user_message: str,
        scout_response: str,
        tools_called: list[str] | None = None,
        outcome: str = "success",
    ) -> None:
        """Log a complete interaction to SQLite."""
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz).isoformat()
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO episodes (timestamp, user_message, scout_response, tools_called, outcome)
                   VALUES (?, ?, ?, ?, ?)""",
                (now, user_message, scout_response, json.dumps(tools_called or []), outcome),
            )

    def get_recent_episodes(self, n: int = 5) -> list[dict]:
        """Return the n most recent episodes."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (n,)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ── Semantic memory ────────────────────────────────────────────────────────

    def save_fact(self, fact: str, kind: str = "facts") -> str:
        """
        Persist a fact or preference about the user.
        kind: 'facts' | 'preferences'
        """
        data = _load_semantic()
        bucket = data.setdefault(kind, [])
        if fact not in bucket:
            bucket.append(fact)
            _save_semantic(data)
            return f"✅ Saved to memory: {fact}"
        return f"Already knew that: {fact}"

    def retrieve_relevant_memory(self, query: str, top_k: int = 3) -> str:
        """
        Simple keyword-based retrieval from semantic + episodic memory.
        Returns a formatted string to inject into the prompt.
        """
        data = _load_semantic()
        all_facts = data.get("facts", []) + data.get("preferences", [])
        query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())

        # Score each fact by word overlap with the query
        scored = []
        for fact in all_facts:
            fact_words = set(re.sub(r"[^\w\s]", "", fact.lower()).split())
            score = len(query_words & fact_words)
            if score > 0:
                scored.append((score, fact))
        scored.sort(reverse=True)
        top_facts = [f for _, f in scored[:top_k]]

        # Also grab recent episodes that mention query words
        episodes = self.get_recent_episodes(n=10)
        rel_eps = []
        for ep in episodes:
            ep_words = set(re.sub(r"[^\w\s]", "", ep["user_message"].lower()).split())
            if query_words & ep_words:
                rel_eps.append(f"[{ep['timestamp'][:16]}] You asked: {ep['user_message'][:80]}")
            if len(rel_eps) >= 2:
                break

        parts = []
        if top_facts:
            parts.append("Relevant facts about you:\n" + "\n".join(f"- {f}" for f in top_facts))
        if rel_eps:
            parts.append("Related past interactions:\n" + "\n".join(rel_eps))
        return "\n\n".join(parts) if parts else ""

    def get_all_memory_summary(self) -> str:
        """Return a formatted summary of everything Scout knows — for /memory command."""
        data = _load_semantic()
        lines = ["🧠 *What Scout knows about you:*\n"]

        facts = data.get("facts", [])
        if facts:
            lines.append("*Facts:*")
            lines.extend(f"  • {f}" for f in facts)

        prefs = data.get("preferences", [])
        if prefs:
            lines.append("\n*Preferences:*")
            lines.extend(f"  • {p}" for p in prefs)

        lists = data.get("lists", {})
        if lists:
            lines.append("\n*Lists:*")
            for name, items in lists.items():
                lines.append(f"  📋 *{name}:* {', '.join(items) if items else '(empty)'}")

        recent = self.get_recent_episodes(n=3)
        if recent:
            lines.append("\n*Recent interactions:*")
            for ep in recent:
                lines.append(f"  • [{ep['timestamp'][:16]}] {ep['user_message'][:60]}")

        return "\n".join(lines)
