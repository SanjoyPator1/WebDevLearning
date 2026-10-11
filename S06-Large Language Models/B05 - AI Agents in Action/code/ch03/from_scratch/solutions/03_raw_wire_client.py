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
    global _next_id
    _next_id += 1

    body_params = dict(params or {})
    body_params["_meta"] = _meta()

    payload = {"jsonrpc": "2.0", "id": _next_id, "method": method, "params": body_params}

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        # this header is what tells the server to use the 2026-07-28 code
        # path at all -- without it, the request falls through to a legacy
        # handler that doesn't even know about newer methods like discover
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if "name" in body_params:
        headers["Mcp-Name"] = body_params["name"]
    if headers_override:
        headers.update(headers_override)

    response = httpx.post(URL, json=payload, headers=headers)
    print(f"HTTP {response.status_code}")

    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        for line in response.text.splitlines():
            if line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
                _print_result(data)
    else:
        _print_result(response.json())


def _print_result(data: dict) -> None:
    # your turn: print error code/message if present, else the interesting
    # result fields (resultType, ttlMs, cacheScope, tools, content, supportedVersions)
    if "error" in data:
        err = data["error"]
        print(f"  error: {err['code']} {err['message']}")
        return

    result = data["result"]
    for key in ("resultType", "ttlMs", "cacheScope"):
        if key in result:
            print(f"  {key:<10}: {result[key]}")
    if "tools" in result:
        print(f"  tools      : {[t['name'] for t in result['tools']]}")
    if "content" in result:
        print(f"  content    : {result['content']}")
    if "supportedVersions" in result:
        print(f"  supportedVersions: {result['supportedVersions']}")
        server_info = result.get("_meta", {}).get("io.modelcontextprotocol/serverInfo")
        print(f"  serverInfo       : {server_info}")


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
