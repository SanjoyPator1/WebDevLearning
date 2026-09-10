# ============================================================
# INFRASTRUCTURE (topic 14) — three replicas, one round-robin proxy
# REF:   notes/14-load-balancer.md
# RUN:   python solved/loadbalancer.py
# ============================================================
#
# This file does not teach a new MCP method — every RPC it carries was
# already covered in topics 01-13. What it proves is that NONE of that
# needed to change to survive a load balancer:
#
#   - add_to_order / view_order (topic 07) carry their entire state in a
#     signed token, so any replica that receives one can pick up exactly
#     where the last one left off. No sticky sessions, no shared cart
#     storage beyond the token itself.
#   - sell_out / un_sell_out / subscriptions/listen (topic 11) leaked
#     across processes when each replica had its own private, in-memory
#     SubscriptionBus. Here all three replicas are given the SAME
#     `SqliteSubscriptionBus`, pointed at one shared file — the fix,
#     proven for real rather than argued about.
#
# The proxy itself is deliberately dumb: round-robin over three backends,
# streaming every response back byte-for-byte (a plain JSON body OR an SSE
# stream — the same either/or `tests/wire.py` has handled since topic 01,
# now decided by the BACKEND, not the proxy). It knows nothing about
# JSON-RPC, tools, or MCP at all — the same way a real load balancer
# usually does not.

# --- Imports ---
import asyncio
import itertools
import os
import subprocess
import sys
import time
from collections.abc import AsyncIterator

import httpx2 as httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

# --- Constants / Config ---
PROXY_HOST = "127.0.0.1"
PROXY_PORT = int(os.environ.get("CAFE_MCP_PROXY_PORT", "3010"))
REPLICA_PORTS = [3011, 3012, 3013]
BUS_PATH = os.environ.get("CAFE_MCP_BUS_PATH", "/tmp/cafe_mcp_lb_bus.db")
SERVER_FILE = os.path.join(os.path.dirname(__file__), "t14_load_balancer.py")

# A plain itertools.cycle, not a lock-protected counter. The proxy runs one
# asyncio event loop with no other threads, so there is no data race here to
# guard against — the same reasoning topic 06 gave for why the cursor codec
# needed no locking either.
_ROUND_ROBIN = itertools.cycle(REPLICA_PORTS)

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "transfer-encoding",
    "content-length",
    "content-encoding",
}


def _spawn_replicas() -> list[subprocess.Popen]:
    """Start the three replicas as real, separate OS processes — not threads,
    not asyncio tasks. Anything short of that would let them share Python
    globals (like topic 11's SOLD_OUT set) by accident, which would quietly
    hide the exact bug this topic exists to demonstrate."""
    processes = []
    for i, port in enumerate(REPLICA_PORTS, start=1):
        env = {
            **os.environ,
            "CAFE_MCP_PORT": str(port),
            "CAFE_MCP_INSTANCE": f"replica-{i}",
            "CAFE_MCP_BUS_PATH": BUS_PATH,
        }
        proc = subprocess.Popen(
            [sys.executable, SERVER_FILE],
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(proc)
    return processes


def _wait_until_up(port: int, *, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=0.5)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"replica on port {port} never came up")


async def _proxy_mcp(request: Request) -> StreamingResponse:
    backend_port = next(_ROUND_ROBIN)
    backend_url = f"http://127.0.0.1:{backend_port}/mcp"

    body = await request.body()
    forward_headers = {
        key: value for key, value in request.headers.items() if key.lower() != "host"
    }

    print(f"  [proxy] {request.method} /mcp -> replica on port {backend_port}", file=sys.stderr)

    client = httpx.AsyncClient(timeout=None)
    backend_request = client.build_request(
        request.method, backend_url, headers=forward_headers, content=body
    )
    backend_response = await client.send(backend_request, stream=True)

    async def relay() -> AsyncIterator[bytes]:
        try:
            async for chunk in backend_response.aiter_raw():
                yield chunk
        finally:
            await backend_response.aclose()
            await client.aclose()

    response_headers = {
        key: value
        for key, value in backend_response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    return StreamingResponse(
        relay(),
        status_code=backend_response.status_code,
        headers=response_headers,
    )


async def _healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp-proxy", "backends": REPLICA_PORTS})


proxy_app = Starlette(
    routes=[
        Route("/mcp", _proxy_mcp, methods=["POST", "GET"]),
        Route("/healthz", _healthz, methods=["GET"]),
    ]
)


def main() -> None:
    print("-" * 68)
    print("TOPIC 14 — three replicas behind a round-robin proxy")
    print("-" * 68)
    print(f"  bus path : {BUS_PATH}  (all three replicas share this file)")
    print(f"  replicas : {REPLICA_PORTS}")
    print(f"  proxy    : http://{PROXY_HOST}:{PROXY_PORT}/mcp")
    print("-" * 68)

    if os.path.exists(BUS_PATH):
        os.remove(BUS_PATH)

    processes = _spawn_replicas()
    try:
        for port in REPLICA_PORTS:
            _wait_until_up(port)
        print("  all three replicas are up.")
        print("-" * 68)
        print("  Try, in another terminal:")
        print("    bash curl/14_stateless_across_instances.sh")
        print("    bash curl/14_subscription_fixed.sh")
        print("-" * 68, flush=True)

        uvicorn.run(proxy_app, host=PROXY_HOST, port=PROXY_PORT, log_level="warning")
    finally:
        print("\n  shutting down replicas...", file=sys.stderr)
        for proc in processes:
            proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        asyncio.run(asyncio.sleep(0))
