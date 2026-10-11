# Problem 03 -- the one file that skips the library's Client and sends raw
# JSON-RPC over HTTP by hand.

import json

import httpx

URL = "http://127.0.0.1:8000/mcp"
PROTOCOL_VERSION = "2026-07-28"

_next_id = 0


def _meta() -> dict:
    return {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    }


def send(method: str, params: dict | None = None, headers_override: dict | None = None) -> None:
    """POST one JSON-RPC request and print the status and body."""
    # your turn: build the payload (jsonrpc, id, method, params with _meta added)
    # your turn: build the headers (Content-Type, Accept, MCP-Protocol-Version,
    # Mcp-Method, and Mcp-Name when params has a "name" key)
    # your turn: httpx.post, then print status and the parsed result, handling
    # both a plain JSON response and an SSE "data:" line
    raise NotImplementedError


def _print_result(data: dict) -> None:
    # your turn: print error code/message if present, else the interesting
    # result fields (resultType, ttlMs, cacheScope, tools, content, supportedVersions)
    raise NotImplementedError


print("--- 1. server/discover ---")
send("server/discover")

print("\n--- 2. tools/list ---")
send("tools/list")

print("\n--- 3. tools/call echo ---")
send("tools/call", {"name": "echo", "arguments": {"text": "hi"}})

print("\n--- 4. tools/list WITHOUT _meta ---")
# your turn: build and send this one by hand, skipping send(), since send()
# always adds _meta -- keep the MCP-Protocol-Version header though

print("\n--- 5. tools/call with WRONG Mcp-Name ---")
send("tools/call", {"name": "echo", "arguments": {"text": "hi"}}, headers_override={"Mcp-Name": "wrong"})

print("\n--- 6. a method that does not exist ---")
send("recipes/cook")
