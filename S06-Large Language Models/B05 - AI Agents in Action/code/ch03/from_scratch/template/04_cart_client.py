# Problem 04 -- start two real server processes and alternate calls between
# them to see the naive cart break and the token cart survive.

import asyncio
import os
import sys
from pathlib import Path

from mcp import MCPError
from mcp.client import Client

SERVER_PATH = Path(__file__).parent / "04_cart_server.py"
SHARED_SECRET = "cart-demo-secret"


async def start_replica(name: str, port: int) -> asyncio.subprocess.Process:
    # your turn: build the env dict (CART_REPLICA, CART_PORT, CART_SECRET)
    # and start the subprocess with asyncio.create_subprocess_exec, then wait
    # a moment for uvicorn to come up
    raise NotImplementedError


async def main() -> None:
    process_a = await start_replica("A", 8001)
    process_b = await start_replica("B", 8002)

    try:
        # your turn: open two Clients, one per URL (8001, 8002)

        # your turn: NAIVE CART -- add 'apple' on A, add 'bread' on B, view on A
        # print served_by and the cart each time -- it should be wrong

        # your turn: TOKEN CART -- same three steps, passing cart_token along
        # each time -- it should be right

        # your turn: TAMPERED TOKEN -- flip the first character of the
        # signature part and call view_cart, print is_error and the message
        raise NotImplementedError
    finally:
        process_a.terminate()
        process_b.terminate()
        await process_a.wait()
        await process_b.wait()


if __name__ == "__main__":
    asyncio.run(main())
