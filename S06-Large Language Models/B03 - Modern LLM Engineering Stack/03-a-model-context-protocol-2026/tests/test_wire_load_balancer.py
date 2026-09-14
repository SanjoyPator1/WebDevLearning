# ============================================================
# TESTS: topic 14 — three instances behind a round-robin proxy
# REF:   notes/14-load-balancer.md
# ============================================================
#
# Run: pytest tests/test_wire_load_balancer.py -v
#
# Two things get proved here, mirroring the two curl scripts:
#
#   1. add_to_order/view_order (ordinary request/response, no open stream)
#      survive being answered by a DIFFERENT, independently-constructed
#      MCPServer than the one that minted the token — driven entirely through
#      httpx.ASGITransport, the same in-process shortcut every topic before
#      11 uses, because nothing here needs a real socket.
#
#   2. subscriptions/listen — a genuinely open stream — now crosses instances
#      when they share a SqliteSubscriptionBus, reusing
#      test_wire_subscriptions.py's real-uvicorn-on-a-real-port pattern,
#      because (as that file's docstring explains) ASGITransport cannot
#      deliver even the first frame of a stream with no natural end.

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx2 as httpx
import pytest
import t14_load_balancer
import uvicorn
from mcp.server import MCPServer

from cafe_mcp.shared_bus import SqliteSubscriptionBus

BASE_URL = "http://127.0.0.1:3010"
PORT = 3096  # distinct from 3098 (test_wire_subscriptions.py) and 3099 (other probes)
META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": {"name": "cafe-wire-test", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
}


def _headers(method: str, *, name: str | None = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": method,
    }
    if name is not None:
        headers["Mcp-Name"] = name
    return headers


def _make_replica(name: str, bus_path: str) -> MCPServer:
    """Build a fresh, independently-constructed MCPServer carrying topic 14's
    own tool functions, pointed at a shared bus file. Standing in for one of
    the three real OS processes `solved/loadbalancer.py` actually spawns —
    same reasoning as test_wire_subscriptions.py's `instance_b`."""
    replica = MCPServer(name=name, version="0.14.0", subscriptions=SqliteSubscriptionBus(bus_path))
    replica.add_tool(t14_load_balancer.add_to_order)
    replica.add_tool(t14_load_balancer.view_order)
    replica.add_tool(t14_load_balancer.sell_out)
    replica.add_tool(t14_load_balancer.un_sell_out)
    return replica


@contextlib.asynccontextmanager
async def _in_process(server: MCPServer) -> AsyncIterator[httpx.AsyncClient]:
    app = server.streamable_http_app(stateless_http=True, host="127.0.0.1")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
            yield client


@contextlib.asynccontextmanager
async def _real_port(server: MCPServer, *, port: int) -> AsyncIterator[httpx.AsyncClient]:
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


async def _call(client: httpx.AsyncClient, tool: str, arguments: dict, req_id: int) -> dict:
    response = await client.post(
        "/mcp",
        headers=_headers("tools/call", name=tool),
        json={
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments, "_meta": META},
        },
    )
    return response.json()["result"]


async def _read_n_events(response: httpx.Response, n: int) -> list[dict]:
    events: list[dict] = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
            if len(events) >= n:
                return events
    return events


@pytest.fixture
def bus_path(tmp_path: Path) -> str:
    return str(tmp_path / "shared_bus.db")


async def test_a_cart_started_on_one_instance_is_readable_on_another(bus_path):
    """The stateless-flow half of this topic's payoff: three SEPARATE
    MCPServer objects, one signed cart, no coordination between them beyond
    the token — the in-process equivalent of curl/14_stateless_across_instances.sh."""
    replica_1 = _make_replica("replica-1", bus_path)
    replica_2 = _make_replica("replica-2", bus_path)
    replica_3 = _make_replica("replica-3", bus_path)

    async with _in_process(replica_1) as client_1:
        first = await _call(client_1, "add_to_order", {"slug": "latte", "size": "M", "qty": 1}, 1)
    assert first["structuredContent"]["served_by"] == "single"  # env var not set in-process
    token_1 = first["structuredContent"]["order"]

    async with _in_process(replica_2) as client_2:
        second = await _call(
            client_2,
            "add_to_order",
            {"slug": "espresso", "size": "S", "qty": 2, "order": token_1},
            2,
        )
    assert len(second["structuredContent"]["lines"]) == 2
    token_2 = second["structuredContent"]["order"]

    async with _in_process(replica_3) as client_3:
        third = await _call(client_3, "view_order", {"order": token_2}, 3)
    assert len(third["structuredContent"]["lines"]) == 2
    assert third["structuredContent"]["total"] == second["structuredContent"]["total"]
    # replica_1 never saw "espresso", replica_3 never saw either add_to_order
    # call directly — only the token carried the cart forward.
    assert {line["slug"] for line in third["structuredContent"]["lines"]} == {"latte", "espresso"}


async def test_a_forged_token_is_rejected_identically_on_every_replica(bus_path):
    """Every replica shares the SAME secret (cafe_mcp.tokens reads it from one
    process-wide env var), so a tampered token is rejected the same way no
    matter which replica receives it — the signature check needs no
    coordination between replicas at all."""
    replica_1 = _make_replica("replica-1", bus_path)
    replica_2 = _make_replica("replica-2", bus_path)

    async with _in_process(replica_1) as client_1:
        minted = await _call(client_1, "add_to_order", {"slug": "latte", "size": "M", "qty": 1}, 1)
    token = minted["structuredContent"]["order"]
    # Flip a character INSIDE the signature segment, not the token's last
    # character — the final base64url character of a 32-byte digest has 2
    # unused padding bits, making a last-character flip tamper-evident only
    # ~94% of the time. See test_tokens.py / test_wire_order_token.py for the
    # full explanation; this is the same fix applied there.
    prefix, body_b64, sig_b64 = token.split(".", 2)
    flipped = "a" if sig_b64[0] != "a" else "b"
    tampered = f"{prefix}.{body_b64}.{flipped}{sig_b64[1:]}"

    async with _in_process(replica_2) as client_2:
        result = await _call(client_2, "view_order", {"order": tampered}, 2)
    assert result["isError"] is True
    assert "not valid" in result["content"][0]["text"]


async def test_sell_out_on_one_instance_reaches_a_listener_on_another(bus_path):
    """THE fix, as an assertion rather than a terminal transcript: two
    separate MCPServer instances sharing ONE SqliteSubscriptionBus file — the
    exact pair that leaked in test_wire_subscriptions.py's
    test_the_cross_instance_leak_is_real, except that test used the default
    InMemorySubscriptionBus and this one does not."""
    instance_a = _make_replica("instance-a", bus_path)
    instance_b = _make_replica("instance-b", bus_path)

    async with _real_port(instance_a, port=PORT) as client_a:
        async with _real_port(instance_b, port=PORT + 1) as client_b:

            async def listen_on_a() -> list[dict]:
                async with client_a.stream(
                    "POST",
                    "/mcp",
                    headers=_headers("subscriptions/listen"),
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "subscriptions/listen",
                        "params": {
                            "notifications": {"resourceSubscriptions": ["cafe://menu"]},
                            "_meta": META,
                        },
                    },
                ) as response:
                    return await _read_n_events(response, 2)

            async def sell_out_on_b():
                await asyncio.sleep(0.5)
                result = await _call(client_b, "sell_out", {"slug": "mocha"}, 2)
                assert result["isError"] is False

            async with asyncio.timeout(5), asyncio.TaskGroup() as tg:
                listen_task = tg.create_task(listen_on_a())
                tg.create_task(sell_out_on_b())

    events = listen_task.result()
    assert [e["method"] for e in events] == [
        "notifications/subscriptions/acknowledged",
        "notifications/resources/updated",
    ]
    assert events[1]["params"]["uri"] == "cafe://menu"


async def test_same_instance_delivery_still_works_through_the_shared_bus(bus_path):
    """Swapping the bus must not break the ordinary, single-instance case —
    the same instance that runs sell_out is also the one listening."""
    solo = _make_replica("solo", bus_path)

    async with _real_port(solo, port=PORT + 2) as client:
        async with client.stream(
            "POST",
            "/mcp",
            headers=_headers("subscriptions/listen"),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "subscriptions/listen",
                "params": {
                    "notifications": {"resourceSubscriptions": ["cafe://menu"]},
                    "_meta": META,
                },
            },
        ) as response:

            async def publish_after_ack():
                await asyncio.sleep(0.3)
                result = await _call(client, "sell_out", {"slug": "latte"}, 2)
                assert result["isError"] is False

            async with asyncio.timeout(5), asyncio.TaskGroup() as tg:
                tg.create_task(publish_after_ack())
                events = await _read_n_events(response, 2)

    assert [e["method"] for e in events] == [
        "notifications/subscriptions/acknowledged",
        "notifications/resources/updated",
    ]
