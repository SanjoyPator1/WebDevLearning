"""
tools/memory_tools.py

save_to_memory — persist a fact or preference about the user
get_memory     — retrieve relevant memories given a query
"""
from scout.memory.manager import MemoryManager, _load_semantic

# Module-level singleton — shared across tool calls within a session
# (The agent passes its own MemoryManager; these are standalone wrappers for
#  cases where the tool needs to be called directly without an agent instance.)
_FALLBACK_MM = None


def _get_mm() -> MemoryManager:
    global _FALLBACK_MM
    if _FALLBACK_MM is None:
        _FALLBACK_MM = MemoryManager()
    return _FALLBACK_MM


def save_to_memory(fact: str, kind: str = "facts") -> str:
    """
    Save a fact or preference about the user to long-term semantic memory.
    kind: 'facts' (default) | 'preferences'
    Example: save_to_memory("goes to gym on Monday and Thursday")
    """
    return _get_mm().save_fact(fact, kind=kind)


def get_memory(query: str) -> str:
    """
    Retrieve relevant memories based on a query string.
    Searches both semantic memory (facts/prefs) and recent episodic log.
    Returns top matching results as a formatted string.
    """
    result = _get_mm().retrieve_relevant_memory(query)
    return result if result else "🔍 No relevant memories found for that query."
