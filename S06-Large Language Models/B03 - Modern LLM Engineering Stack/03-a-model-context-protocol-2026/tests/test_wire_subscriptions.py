# ============================================================
# TESTS: subscriptions/listen, on REAL running servers
# REF:   notes/11-subscriptions.md
# ============================================================
#
# Run: pytest tests/test_wire_subscriptions.py -v
#
# EVERY OTHER test file in this folder drives its server through
# `httpx.ASGITransport` — an in-process fake transport that calls the ASGI app
# directly with no real socket. That works because every other RPC answers
# and returns. `subscriptions/listen` does not: the ASGI app callable does not
# return until the stream ends, and ASGITransport buffers the WHOLE response
# before handing any of it back — so it cannot deliver even the first frame of
# a stream that has no natural end. Verified directly: a listen request over
# ASGITransport hangs forever, timing out with nothing received, ack included.
#
# So this file runs a REAL `uvicorn.Server` as a background asyncio task,
# bound to an actual TCP port, and talks to it with a real `httpx.AsyncClient`
# — no ASGITransport anywhere below. This is heavier than every other test
# file (a real port, a real accept loop) but it is the only way to test what
# this topic is actually about: a response that streams events over time.

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator

import httpx2 as httpx
import pytest
import t11_subscriptions
import uvicorn
from mcp.server import MCPServer

PORT = 3098  # not 3010 (the shared CAFE_MCP_PORT) or 3099 (used by other probes)
BASE_URL = f"http://127.0.0.1:{PORT}"
META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
}


@contextlib.asynccontextmanager
async def real_server(server: MCPServer, *, port: int = PORT) -> AsyncIterator[httpx.AsyncClient]:
    """Run `server` on a real port for the duration of the `with` block, and
    hand back a real (non-ASGITransport) client pointed at it.

    An @asynccontextmanager, not a pytest fixture, for the same reason
    tests/wire.py's wire_client is one: fixture teardown running in a
    different task than the test body makes anyio's cancel-scope checks
    raise. See tests/wire.py's docstring for the fuller explanation; the
    reasoning is identical here.
    """
    app = server.streamable_http_app(stateless_http=True, host="127.0.0.1")
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(uv_server.serve())
        while not uv_server.started:
            await asyncio.sleep(0.02)
        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
                yield client
        finally:
            uv_server.should_exit = True


def _listen_body(req_id: int, *, uris: list[str] | None = None, **flags) -> dict:
    notifications: dict = dict(flags)
    if uris is not None:
        notifications["resourceSubscriptions"] = uris
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "subscriptions/listen",
        "params": {"notifications": notifications, "_meta": META},
    }


def _headers(method: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": method,
    }


async def _read_n_events(response: httpx.Response, n: int) -> list[dict]:
    events: list[dict] = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
            if len(events) >= n:
                return events
    return events


async def _call_tool(client: httpx.AsyncClient, name: str, arguments: dict, req_id: int) -> dict:
    response = await client.post(
        "/mcp",
        headers={**_headers("tools/call"), "Mcp-Name": name},
        json={
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments, "_meta": META},
        },
    )
    return response.json()["result"]


@pytest.fixture(autouse=True)
def _reset_sold_out():
    """SOLD_OUT is module-level mutable state shared across every test in this
    file — the exact kind of state this topic is about. Reset it before each
    test so they do not leak into each other."""
    t11_subscriptions.SOLD_OUT.clear()
    yield
    t11_subscriptions.SOLD_OUT.clear()


async def test_the_ack_is_the_first_frame_and_echoes_the_honored_filter():
    async with real_server(t11_subscriptions.mcp) as client:
        async with client.stream(
            "POST",
            "/mcp",
            headers=_headers("subscriptions/listen"),
            json=_listen_body(1, uris=["cafe://menu"]),
        ) as response:
            [ack] = await _read_n_events(response, 1)

    assert ack["method"] == "notifications/subscriptions/acknowledged"
    assert ack["params"]["_meta"]["io.modelcontextprotocol/subscriptionId"] == 1
    assert ack["params"]["notifications"] == {"resourceSubscriptions": ["cafe://menu"]}


async def test_honoring_is_a_truthy_echo_not_a_capability_check():
    """A falsy flag is dropped from the ack; a truthy one is echoed back
    UNCONDITIONALLY, including a subscription to a URI that names no real
    resource. "Honored" means "the server will tell you if this happens", not
    "the server checked this exists" — a subscription to a made-up URI is
    honored exactly like a real one; it will simply never fire."""
    async with real_server(t11_subscriptions.mcp) as client:
        body = _listen_body(
            2,
            uris=["cafe://menu", "cafe://this-resource-does-not-exist"],
            toolsListChanged=True,
            promptsListChanged=False,
        )
        async with client.stream(
            "POST", "/mcp", headers=_headers("subscriptions/listen"), json=body
        ) as response:
            [ack] = await _read_n_events(response, 1)

    honored = ack["params"]["notifications"]
    assert honored["toolsListChanged"] is True
    assert "promptsListChanged" not in honored  # falsy flags are dropped, not echoed as false
    assert set(honored["resourceSubscriptions"]) == {
        "cafe://menu",
        "cafe://this-resource-does-not-exist",
    }


async def test_sell_out_notifies_a_listener_on_the_same_instance():
    async with real_server(t11_subscriptions.mcp) as client:
        async with client.stream(
            "POST",
            "/mcp",
            headers=_headers("subscriptions/listen"),
            json=_listen_body(3, uris=["cafe://menu"]),
        ) as response:

            async def publish_after_ack():
                await asyncio.sleep(0.3)
                result = await _call_tool(client, "sell_out", {"slug": "espresso"}, req_id=4)
                assert result["isError"] is False

            async with asyncio.timeout(5), asyncio.TaskGroup() as tg:
                tg.create_task(publish_after_ack())
                events = await _read_n_events(response, 2)

    ack, update = events
    assert ack["method"] == "notifications/subscriptions/acknowledged"
    assert update["method"] == "notifications/resources/updated"
    assert update["params"]["uri"] == "cafe://menu"
    # Both frames belong to the SAME listen call — same subscriptionId.
    assert (
        update["params"]["_meta"]["io.modelcontextprotocol/subscriptionId"]
        == ack["params"]["_meta"]["io.modelcontextprotocol/subscriptionId"]
        == 3
    )


async def test_two_concurrent_listeners_on_one_instance_both_get_the_event():
    """Fan-out within a single process: every stream subscribed to this
    instance's bus receives the event, each tagged with ITS OWN
    subscriptionId — not the tool call's id, not each other's."""
    async with real_server(t11_subscriptions.mcp) as client:

        async def listener(req_id: int) -> list[dict]:
            async with client.stream(
                "POST",
                "/mcp",
                headers=_headers("subscriptions/listen"),
                json=_listen_body(req_id, uris=["cafe://menu"]),
            ) as response:
                return await _read_n_events(response, 2)

        async def publish_after_both_acked():
            await asyncio.sleep(0.4)
            await _call_tool(client, "sell_out", {"slug": "mocha"}, req_id=7)

        async with asyncio.timeout(5):
            results = await asyncio.gather(listener(5), listener(6), publish_after_both_acked())

    events_a, events_b, _ = results
    assert [e["method"] for e in events_a] == [
        "notifications/subscriptions/acknowledged",
        "notifications/resources/updated",
    ]
    assert [e["method"] for e in events_b] == [
        "notifications/subscriptions/acknowledged",
        "notifications/resources/updated",
    ]
    id_a = events_a[0]["params"]["_meta"]["io.modelcontextprotocol/subscriptionId"]
    id_b = events_b[0]["params"]["_meta"]["io.modelcontextprotocol/subscriptionId"]
    assert {id_a, id_b} == {5, 6}

    def sub_id(event: dict) -> int:
        return event["params"]["_meta"]["io.modelcontextprotocol/subscriptionId"]

    # Every frame in EACH stream carries THAT stream's own id, never the other's.
    assert all(sub_id(e) == id_a for e in events_a)
    assert all(sub_id(e) == id_b for e in events_b)


async def test_the_cross_instance_leak_is_real():
    """THE central proof of this topic, reproduced as an assertion rather than
    a terminal transcript. Two SEPARATE MCPServer instances — separate
    Python objects, each with its own default InMemorySubscriptionBus, the
    way two separate OS processes behind a load balancer would be — a
    listener on instance A, a sell_out on instance B, and instance A hears
    nothing at all, for the whole window.

    This is not a simulation of the leak; `t11_subscriptions.mcp` and a
    second, independently-constructed `MCPServer` sharing the same tool and
    resource functions genuinely do not share a bus, exactly as two OS
    processes running the same file would not.
    """
    from mcp.server import MCPServer

    instance_a = t11_subscriptions.mcp
    instance_b = MCPServer(name="cafe-mcp-b", version="0.11.0")
    instance_b.add_tool(t11_subscriptions.sell_out)

    port_b = PORT + 1
    async with real_server(instance_a, port=PORT) as client_a:
        async with real_server(instance_b, port=port_b) as client_b:

            async def listen_on_a() -> list[dict]:
                async with client_a.stream(
                    "POST",
                    "/mcp",
                    headers=_headers("subscriptions/listen"),
                    json=_listen_body(8, uris=["cafe://menu"]),
                ) as response:
                    events = []
                    with contextlib.suppress(TimeoutError):
                        async with asyncio.timeout(2.0):
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    events.append(json.loads(line[6:]))
                    return events

            async def sell_out_on_b():
                await asyncio.sleep(0.5)
                result = await _call_tool(client_b, "sell_out", {"slug": "latte"}, req_id=9)
                assert result["isError"] is False

            async with asyncio.TaskGroup() as tg:
                listen_task = tg.create_task(listen_on_a())
                tg.create_task(sell_out_on_b())

    events_seen_on_a = listen_task.result()
    # ONLY the ack. sell_out ran successfully — on B — and A's listener,
    # open the entire time, received nothing about it.
    assert len(events_seen_on_a) == 1
    assert events_seen_on_a[0]["method"] == "notifications/subscriptions/acknowledged"


async def test_un_sell_out_reverses_sell_out():
    async with real_server(t11_subscriptions.mcp) as client:
        sold = await _call_tool(client, "sell_out", {"slug": "latte"}, req_id=10)
        assert "sold out" in sold["content"][0]["text"]

        read = await client.post(
            "/mcp",
            headers={**_headers("resources/read"), "Mcp-Name": "cafe://menu"},
            json={
                "jsonrpc": "2.0",
                "id": 11,
                "method": "resources/read",
                "params": {"uri": "cafe://menu", "_meta": META},
            },
        )
        assert "Latte" in read.json()["result"]["contents"][0]["text"]
        assert "Sold Out Right Now" in read.json()["result"]["contents"][0]["text"]

        back = await _call_tool(client, "un_sell_out", {"slug": "latte"}, req_id=12)
        assert "available again" in back["content"][0]["text"]

        read2 = await client.post(
            "/mcp",
            headers={**_headers("resources/read"), "Mcp-Name": "cafe://menu"},
            json={
                "jsonrpc": "2.0",
                "id": 13,
                "method": "resources/read",
                "params": {"uri": "cafe://menu", "_meta": META},
            },
        )
        assert "Nothing" in read2.json()["result"]["contents"][0]["text"]


async def test_selling_out_an_unknown_slug_is_a_clean_tool_error():
    async with real_server(t11_subscriptions.mcp) as client:
        result = await _call_tool(client, "sell_out", {"slug": "no-such-drink"}, req_id=14)

    assert result["isError"] is True
    assert "no drink with slug" in result["content"][0]["text"]
