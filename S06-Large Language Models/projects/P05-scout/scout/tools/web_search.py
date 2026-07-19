"""
tools/web_search.py

Dual-provider web search: Tavily (primary) or DuckDuckGo (fallback).
Switch via SEARCH_PROVIDER in .env — no code changes needed.
"""
import config
from typing import Optional


# ── Tavily ────────────────────────────────────────────────────────────────────

def _tavily_search(query: str, max_results: int = 3) -> str:
    """Call Tavily Search API and return formatted snippets."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    response = client.search(
        query=query,
        search_depth="basic",
        max_results=max_results,
    )
    results = response.get("results", [])
    if not results:
        return "No results found."
    parts = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        url = r.get("url", "")
        content = r.get("content", "").strip()[:400]
        parts.append(f"[{i}] {title}\nURL: {url}\n{content}")
    return "\n\n".join(parts)


# ── DuckDuckGo ────────────────────────────────────────────────────────────────

def _duckduckgo_search(query: str, max_results: int = 3) -> str:
    """Use duckduckgo-search library to fetch results."""
    from duckduckgo_search import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            title = r.get("title", "No title")
            href = r.get("href", "")
            body = r.get("body", "").strip()[:400]
            results.append(f"[{len(results)+1}] {title}\nURL: {href}\n{body}")
            if len(results) >= max_results:
                break
    return "\n\n".join(results) if results else "No results found."


# ── Public interface ──────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    """
    Search the internet for real-time information.
    Uses the provider configured in .env (tavily or duckduckgo).
    Returns formatted search snippets as a string.
    """
    try:
        if config.SEARCH_PROVIDER == "tavily":
            if not config.TAVILY_API_KEY:
                raise ValueError("TAVILY_API_KEY not set — falling back to DuckDuckGo")
            return _tavily_search(query)
        else:
            return _duckduckgo_search(query)
    except Exception as e:
        # Graceful fallback: if tavily fails, try duckduckgo
        if config.SEARCH_PROVIDER == "tavily":
            try:
                return _duckduckgo_search(query)
            except Exception:
                pass
        return f"Search failed: {e}"


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = web_search("current weather in Kolkata")
    print(result)
