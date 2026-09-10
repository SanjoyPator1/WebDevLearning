# ============================================================
# THE PROJECT — a raw client, built entirely by hand
# REF:   notes/15-the-project.md
# RUN:   python solved/cafe_project.py   (in one terminal)
#        python solved/raw_client.py     (in another)
# ============================================================
#
# Every wire-level fact `tests/wire.py` has relied on since topic 01 gets used
# here for real, end to end, against a running server: build the `_meta`
# envelope by hand, mirror the target into `Mcp-Method`/`Mcp-Name` by hand,
# detect plain-JSON vs SSE framing by hand, and — the one piece no earlier
# topic's raw client needed — drive BOTH rounds of an MRTR confirmation by
# hand, reading `requestState` out of round 1's result and feeding it back
# into round 2's params exactly as `curl/08_place_round2.sh` always did.
#
# Nothing here is new protocol knowledge. It is everything topics 01-13
# already taught, run once, back to back, against the one assembled server.
# `solved/sdk_client.py` does the identical sequence through the official
# client so the two can be read side by side.

# --- Imports ---
import asyncio
import json
from typing import Any

import httpx2 as httpx

# --- Constants / Config ---
BASE_URL = "http://127.0.0.1:3010"
VERSION = "2026-07-28"
NAME_KEY = {"tools/call": "name", "prompts/get": "name", "resources/read": "uri"}


def meta(*, progress_token: str | None = None) -> dict[str, Any]:
    """Every request needs this. No client library builds it for you here —
    you are the client library."""
    envelope: dict[str, Any] = {
        "io.modelcontextprotocol/protocolVersion": VERSION,
        "io.modelcontextprotocol/clientInfo": {"name": "cafe-raw-client", "version": "1.0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    if progress_token is not None:
        envelope["progressToken"] = progress_token
    return envelope


def headers_for(method: str, params: dict[str, Any]) -> dict[str, str]:
    """Mcp-Method always. Mcp-Name mirrors whichever params key that method
    reads its target from — get this wrong (or skip it) and topic 13's
    gateway-routing header check has nothing to work with."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": VERSION,
        "Mcp-Method": method,
    }
    key = NAME_KEY.get(method)
    if key and key in params:
        headers["Mcp-Name"] = params[key]
    return headers


async def call(
    client: httpx.AsyncClient, method: str, params: dict[str, Any], req_id: int, **extra_meta: Any
) -> dict[str, Any]:
    """One plain request/response RPC. Handles EITHER framing the server might
    choose — a plain JSON body, or a single-event SSE stream — because
    nothing about the request tells you in advance which one you'll get."""
    body_params = dict(params)
    body_params["_meta"] = meta(**extra_meta)
    response = await client.post(
        "/mcp",
        headers=headers_for(method, params),
        json={"jsonrpc": "2.0", "id": req_id, "method": method, "params": body_params},
    )
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/event-stream"):
        last = None
        for line in response.text.splitlines():
            if line.startswith("data: "):
                last = json.loads(line[6:])
        return last
    return response.json()


async def call_streaming(
    client: httpx.AsyncClient,
    method: str,
    params: dict[str, Any],
    req_id: int,
    *,
    on_progress,
    progress_token: str,
) -> dict[str, Any]:
    """A request whose response carries zero or more `notifications/progress`
    events before the real result — `brew`'s shape. No SDK is parsing SSE for
    you; each `data: ` line is one JSON-RPC message, and you decide what to
    do with each `method` you see before the final one that has a `result`."""
    body_params = dict(params)
    body_params["_meta"] = meta(progress_token=progress_token)
    async with client.stream(
        "POST",
        "/mcp",
        headers=headers_for(method, params),
        json={"jsonrpc": "2.0", "id": req_id, "method": method, "params": body_params},
    ) as response:
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            message = json.loads(line[6:])
            if message.get("method") == "notifications/progress":
                p = message["params"]
                on_progress(p["progress"], p["total"], p.get("message"))
            elif "result" in message:
                return message
    raise RuntimeError("stream ended with no final result")


async def main() -> None:
    print("=" * 68)
    print("RAW CLIENT — every step built by hand")
    print("=" * 68)

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        print("\n--- list_tools ---")
        listing = await call(client, "tools/list", {}, 1)
        print("  ", sorted(t["name"] for t in listing["result"]["tools"]))

        print("\n--- read cafe://menu ---")
        menu = await call(client, "resources/read", {"uri": "cafe://menu"}, 2)
        print(f"   {len(menu['result']['contents'][0]['text'])} characters of markdown")

        print("\n--- add_to_order(latte, M, 1) ---")
        added = await call(
            client,
            "tools/call",
            {"name": "add_to_order", "arguments": {"slug": "latte", "size": "M", "qty": 1}},
            3,
        )
        order_token = added["result"]["structuredContent"]["order"]
        print(f"   total so far: ${added['result']['structuredContent']['total']}")

        print("\n--- place_order, round 1 (no inputResponses yet) ---")
        round1 = await call(
            client, "tools/call", {"name": "place_order", "arguments": {"order": order_token}}, 4
        )
        result1 = round1["result"]
        assert result1["resultType"] == "input_required", result1
        confirm_request = result1["inputRequests"]["confirm"]
        request_state = result1["requestState"]
        print("   server asked:", confirm_request["params"]["message"])
        print("   YOU must hold onto requestState and the SAME order token for round 2 —")
        print("   nothing does that for you here.")

        print("\n--- place_order, round 2 (built by hand from round 1's own reply) ---")
        round2 = await call(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order_token},  # UNCHANGED — the retry is refused otherwise
                "inputResponses": {
                    "confirm": {"action": "accept", "content": {"name": "Sanjoy", "confirm": True}}
                },
                "requestState": request_state,
            },
            5,
        )
        placed = round2["result"]["structuredContent"]["result"]
        print(f"   PLACED — ticket {placed['ticket']}, total ${placed['total']}")

        print("\n--- brew(order), progress parsed by hand off the SSE stream ---")

        def on_progress(progress, total, message):
            print(f"   progress {progress}/{total}: {message}")

        brewed = await call_streaming(
            client,
            "tools/call",
            {"name": "brew", "arguments": {"order": order_token}},
            6,
            on_progress=on_progress,
            progress_token="raw-client-demo",
        )
        print("   brew result:", brewed["result"]["structuredContent"])

    print("\n" + "=" * 68)
    print("Every step above required knowing the wire shape of that exact RPC.")
    print("Compare against solved/sdk_client.py.")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(main())
