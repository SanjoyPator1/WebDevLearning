# ============================================================
# CAPSTONE (optional) — a real LLM driving place_order through MRTR
# REF:   notes/08-mrtr.md
# RUN:   python solved/agent_client.py
# ============================================================
#
# Everything in topics 01-08 proved MRTR works by hand-crafting both rounds of
# a `tools/call`. This file proves the same thing with an actual language
# model in the loop, and it exists to make one architectural point concrete:
#
#   THE MODEL NEVER SEES `input_required`.
#
# In a real MCP host, the client library — not the model — is the thing that
# receives an `input_required` result, asks a human for the missing pieces,
# and retries the SAME tool call with the answer attached. The model is shown
# only the FINAL "complete" result, exactly as if the tool had answered on the
# first try. This script plays the role of that host: it calls the LLM ONCE to
# decide to invoke `place_order`, then drives the entire MRTR round trip
# itself, in plain HTTP, with no further model calls.
#
# This is NOT a graded exercise like tNN_*.py — there is no solutions/ stub for
# it. It is a demonstration, and it is unusual in this folder for one reason:
# it can make a REAL network call to a real LLM provider. Read the "Providers"
# section below before running it.
#
# ---------------------------------------------------------------------------
# PROVIDERS
# ---------------------------------------------------------------------------
# Two backends, selected automatically unless CAFE_AGENT_PROVIDER forces one:
#
#   ollama   — a local model via http://localhost:11434. Free, no API key,
#              nothing leaves your machine. Tried FIRST if reachable.
#   gemini   — Google's Gemini API, via a plain REST call (no SDK dependency).
#              Needs GEMINI_API_KEY in a .env file at the repo root. Free tier
#              exists, but it IS a real network call to a real account.
#
# This script makes AT MOST ONE model call, total, no matter which provider
# answers it — the round trip below the model-call line is pure HTTP against
# your own local cafe-mcp server. If neither Ollama nor a Gemini key is
# available, `--dry-run` exercises the exact same code path with a scripted
# fake model response, so you can verify the MRTR plumbing with zero network
# access at all.

# --- Imports ---
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx2 as httpx

# --- Constants / Config ---
CAFE_URL = f"http://127.0.0.1:{os.environ.get('CAFE_MCP_PORT', '3010')}/mcp"
PROTOCOL_VERSION = "2026-07-28"
GEMINI_MODEL_DEFAULT = "gemini-3.6-flash"
OLLAMA_MODEL_DEFAULT = "qwen3:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

# The ONE tool the model is told about. Deliberately just enough schema for it
# to decide to call place_order with the order token we hand it in the prompt
# — this script is not a general-purpose café agent, it exists to demonstrate
# one MRTR round trip end to end.
PLACE_ORDER_TOOL_SCHEMA: dict[str, Any] = {
    "name": "place_order",
    "description": "Place a coffee order for real, given its order token.",
    "parameters": {
        "type": "object",
        "properties": {"order": {"type": "string", "description": "The order token to place."}},
        "required": ["order"],
    },
}


def _load_dotenv() -> None:
    """Find a .env at or above the repo root and load GEMINI_API_KEY from it.

    Matches B04's ai_config.py convention (search upward, load silently if
    found, do nothing if not) rather than inventing a new one.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return


_load_dotenv()


# ---------------------------------------------------------------------------
# Providers — each returns a single decision: "call place_order with this
# order token" or "did not choose to call the tool" (treated as a hard stop;
# this demo has exactly one legitimate outcome).
# ---------------------------------------------------------------------------


def call_ollama(order_token: str, *, model: str = OLLAMA_MODEL_DEFAULT) -> str | None:
    """Ask a local Ollama model to place the order. Returns the `order`
    argument it chose to call the tool with, or None if it didn't call it."""
    print(f"  [agent] asking Ollama ({model}) to place the order...", file=sys.stderr)
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "A customer wants to place their coffee order. Their order "
                        f"token is: {order_token}\n\nCall place_order with that token."
                    ),
                }
            ],
            "tools": [{"type": "function", "function": PLACE_ORDER_TOOL_SCHEMA}],
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    message = response.json()["message"]
    for call in message.get("tool_calls", []):
        if call["function"]["name"] == "place_order":
            args = call["function"]["arguments"]
            return args["order"] if isinstance(args, dict) else json.loads(args)["order"]
    return None


def call_gemini(order_token: str, *, model: str | None = None) -> str | None:
    """Ask Gemini (via plain REST, no SDK dependency) to place the order.
    Returns the `order` argument it chose, or None if it didn't call the tool.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env at the repo root "
            "and fill it in, or run with --dry-run to test without any provider."
        )
    model = model or os.environ.get("GEMINI_MODEL", GEMINI_MODEL_DEFAULT)
    print(f"  [agent] asking Gemini ({model}) to place the order...", file=sys.stderr)

    schema = dict(PLACE_ORDER_TOOL_SCHEMA)
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": api_key},
        json={
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "A customer wants to place their coffee order. Their "
                                f"order token is: {order_token}\n\nCall place_order "
                                "with that token."
                            )
                        }
                    ],
                }
            ],
            "tools": [{"functionDeclarations": [schema]}],
        },
        timeout=60,
    )
    response.raise_for_status()
    candidates = response.json().get("candidates", [])
    for part in candidates[0]["content"]["parts"] if candidates else []:
        call = part.get("functionCall")
        if call and call["name"] == "place_order":
            return call["args"]["order"]
    return None


def call_dry_run(order_token: str, **_: Any) -> str | None:
    """No network at all. Simulates a model that correctly calls place_order,
    so the MRTR plumbing below can be verified with zero external dependencies.
    """
    print("  [agent] --dry-run: simulating a model that calls place_order", file=sys.stderr)
    return order_token


PROVIDERS = {"ollama": call_ollama, "gemini": call_gemini, "dry-run": call_dry_run}


def _pick_provider() -> str:
    """CAFE_AGENT_PROVIDER wins if set. Otherwise: try Ollama (free, local,
    nothing to configure), then Gemini (needs a key), then give up with a
    clear message rather than silently guessing."""
    forced = os.environ.get("CAFE_AGENT_PROVIDER")
    if forced:
        return forced
    try:
        httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1).raise_for_status()
        return "ollama"
    except httpx.HTTPError:
        pass
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    raise RuntimeError(
        "No provider available: Ollama is not running at localhost:11434 and "
        "GEMINI_API_KEY is not set. Start Ollama, set the key in .env, or pass "
        "--dry-run to test the MRTR plumbing with no model at all."
    )


# ---------------------------------------------------------------------------
# The host-side MRTR driver — no model involved past this point.
# ---------------------------------------------------------------------------

_META = {
    "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
    "io.modelcontextprotocol/clientInfo": {"name": "cafe-agent-client", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
}


def _post(method: str, params: dict[str, Any], *, req_id: int, name: str | None = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if name:
        headers["Mcp-Name"] = name
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": {**params, "_meta": _META},
    }
    response = httpx.post(CAFE_URL, headers=headers, json=body, timeout=30)
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
        raise RuntimeError("no data: line in SSE response")
    return response.json()


def place_order_via_mrtr(order_token: str, *, name_for_cup: str) -> dict:
    """Drive place_order through both rounds of MRTR. Returns the final,
    committed order. This function IS the host: the model that decided to
    call place_order never sees any of what happens inside it."""
    print("  [host] round 1: calling place_order...", file=sys.stderr)
    round1 = _post(
        "tools/call",
        {"name": "place_order", "arguments": {"order": order_token}},
        req_id=1,
        name="place_order",
    )
    result1 = round1["result"]
    if result1["resultType"] != "input_required":
        raise RuntimeError(f"expected input_required, got: {result1}")

    message = result1["inputRequests"]["confirm"]["params"]["message"]
    print(f"  [host] server asks: {message!r}", file=sys.stderr)
    print(
        f"  [host] (simulating the human) answering: name={name_for_cup!r}, confirm=True",
        file=sys.stderr,
    )

    print("  [host] round 2: retrying with the SAME order token + the answer...", file=sys.stderr)
    round2 = _post(
        "tools/call",
        {
            "name": "place_order",
            "arguments": {"order": order_token},  # unchanged — the SDK requires this
            "inputResponses": {
                "confirm": {"action": "accept", "content": {"name": name_for_cup, "confirm": True}}
            },
            "requestState": result1["requestState"],
        },
        req_id=2,
        name="place_order",
    )
    result2 = round2["result"]
    if result2["isError"]:
        raise RuntimeError(f"place_order failed: {result2['content'][0]['text']}")
    return result2["structuredContent"]["result"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider", choices=sorted(PROVIDERS), help="Force a provider instead of auto-detecting."
    )
    parser.add_argument("--dry-run", action="store_true", help="Shorthand for --provider dry-run.")
    args = parser.parse_args()

    provider_name = "dry-run" if args.dry_run else (args.provider or _pick_provider())
    print("-" * 68)
    print(f"provider : {provider_name}")
    print(f"server   : {CAFE_URL}")
    print("-" * 68)

    from cafe_mcp import orders

    order_token = orders.sign_cart([{"slug": "latte", "size": "L", "qty": 2}], ttl_s=900)
    print(f"  [setup] minted a cart: 2x latte (L), token ...{order_token[-12:]}", file=sys.stderr)

    chosen_token = PROVIDERS[provider_name](order_token)
    if chosen_token is None:
        print("The model did not choose to call place_order. Nothing to do.")
        return
    if chosen_token != order_token:
        print(
            "The model returned a DIFFERENT token than the one it was given — "
            "the MRTR retry below will use the token the MODEL chose, exactly "
            "as a real host would."
        )

    placed = place_order_via_mrtr(chosen_token, name_for_cup="Sanjoy")
    print("-" * 68)
    print("PLACED:", json.dumps(placed, indent=2))
    print("-" * 68)
    print(
        "Note what the model never saw: the input_required interim result, the "
        "requestState token, or the second tools/call. A real host shows the "
        "model only this final result, as if the tool had answered immediately."
    )


if __name__ == "__main__":
    main()
