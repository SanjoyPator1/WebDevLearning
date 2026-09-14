# ============================================================
# TEST HARNESS: be the client, by hand
# REF:   notes/01-first-server-and-discover.md
# ============================================================
#
# Shared by every wire test. There is deliberately NO SDK client in here.
#
# The reason: an SDK client sets the protocol version header and the `_meta`
# envelope for you, invisibly. So a server that has `stateless_http` wrong, or gets
# the header requirements wrong, passes every SDK-client test and then fails against
# a real client. The only way to catch that is to be the client.

import json
from contextlib import asynccontextmanager
from typing import Any

import httpx2 as httpx

VERSION = "2026-07-28"

# The DNS-rebinding guard compares the Host header against the bound address, so
# this base_url must be exactly this. Plain "http://localhost" is REJECTED.
BASE_URL = "http://127.0.0.1:3010"

# The three name-bearing methods, and which params key each mirrors into `Mcp-Name`.
# Note resources/read uses `uri`, not `name` — a genuine trip hazard.
NAME_KEY = {"tools/call": "name", "prompts/get": "name", "resources/read": "uri"}


# NOTE: an @asynccontextmanager called inside each test body, NOT a yield-based
# pytest fixture. With a fixture, anyio raises "Attempted to exit cancel scope in a
# different task" — the fixture's setup and teardown run in different tasks from the
# test body, and the SDK's task groups will not tolerate that.
@asynccontextmanager
async def wire_client(server: Any):
    """Drive a server's ASGI app in-process, with the lifespan actually running."""
    app = server.streamable_http_app(stateless_http=True, host="127.0.0.1")
    # httpx.ASGITransport does NOT run the ASGI lifespan, so the streamable-HTTP
    # session manager never starts and every request fails. Drive it by hand.
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
            yield client


def parse_jsonrpc(response: httpx.Response) -> list[dict[str, Any]]:
    """Return the JSON-RPC messages in a response, whatever framing was used.

    A streamable-HTTP response is EITHER a plain JSON body OR an SSE-framed stream,
    and which one you get depends on the headers you sent. Any hand-written client
    needs this branch; see notes/01, "The experiment that teaches the most".
    """
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        return [
            json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
        ]
    return [response.json()]


def meta(*, version: str = VERSION, include_capabilities: bool = True) -> dict[str, Any]:
    """The `_meta` envelope. It lives inside `params`, never at the top level."""
    envelope: dict[str, Any] = {
        "io.modelcontextprotocol/protocolVersion": version,
        "io.modelcontextprotocol/clientInfo": {"name": "cafe-wire-test", "version": "1.0"},
    }
    if include_capabilities:
        # A MUST even when empty. `{}` is the right value for a client that can do
        # nothing special; omitting the key entirely is an error.
        envelope["io.modelcontextprotocol/clientCapabilities"] = {}
    return envelope


async def rpc(
    client: httpx.AsyncClient,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    req_id: int = 1,
    version: str | None = VERSION,
    send_method_header: bool = True,
    with_meta: bool = True,
) -> dict[str, Any]:
    """POST one JSON-RPC request, built entirely by hand. Returns the last message."""
    params = dict(params or {})
    if with_meta:
        params["_meta"] = meta(version=version or VERSION)

    headers = {
        "Content-Type": "application/json",
        # Both must be accepted: the SERVER chooses which framing to use.
        "Accept": "application/json, text/event-stream",
    }
    if version is not None:
        headers["MCP-Protocol-Version"] = version
    if send_method_header:
        headers["Mcp-Method"] = method

    # Mirror the target into Mcp-Name for the name-bearing methods, so a gateway can
    # route on it without parsing the body.
    key = NAME_KEY.get(method)
    if key and key in params:
        headers["Mcp-Name"] = params[key]

    body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
    response = await client.post("/mcp", headers=headers, json=body)
    return parse_jsonrpc(response)[-1]


async def result(client: httpx.AsyncClient, method: str, params=None, **kwargs) -> dict:
    """rpc(), asserting success and returning the `result` object."""
    message = await rpc(client, method, params, **kwargs)
    assert "result" in message, f"{method} failed: {message.get('error')}"
    return message["result"]


async def error(client: httpx.AsyncClient, method: str, params=None, **kwargs) -> dict:
    """rpc(), asserting a JSON-RPC error and returning the `error` object."""
    message = await rpc(client, method, params, **kwargs)
    assert "error" in message, f"{method} unexpectedly succeeded: {message.get('result')}"
    return message["error"]


async def call_tool(client: httpx.AsyncClient, tool: str, arguments: dict, *, req_id: int = 1):
    """tools/call, returning the `result` object (which may carry isError: true)."""
    return await result(client, "tools/call", {"name": tool, "arguments": arguments}, req_id=req_id)
