# Problem 04 -- start two real server processes and alternate calls between
# them, like a round-robin load balancer would, to see the naive cart break
# and the token cart survive.

import asyncio
import os
import sys
from pathlib import Path

from mcp.client import Client

SERVER_PATH = Path(__file__).parent / "04_cart_server.py"
SHARED_SECRET = "cart-demo-secret"


async def start_replica(name: str, port: int) -> asyncio.subprocess.Process:
    env = {**os.environ, "CART_REPLICA": name, "CART_PORT": str(port), "CART_SECRET": SHARED_SECRET}
    process = await asyncio.create_subprocess_exec(sys.executable, str(SERVER_PATH), env=env)
    await asyncio.sleep(1)  # give uvicorn a moment to come up
    return process


async def main() -> None:
    process_a = await start_replica("A", 8001)
    process_b = await start_replica("B", 8002)

    try:
        async with Client("http://127.0.0.1:8001/mcp") as client_a, Client("http://127.0.0.1:8002/mcp") as client_b:
            print("NAIVE CART (state in server memory)")
            result = await client_a.call_tool("naive_add", {"cart_id": "c1", "item": "apple"})
            print(f"  add 'apple'  -> {result.structured_content}")
            result = await client_b.call_tool("naive_add", {"cart_id": "c1", "item": "bread"})
            print(f"  add 'bread'  -> {result.structured_content}")
            result = await client_a.call_tool("naive_view", {"cart_id": "c1"})
            print(f"  view         -> {result.structured_content}")

            print("\nTOKEN CART (state travels with the request)")
            result = await client_a.call_tool("add_item", {"item": "apple"})
            token = result.structured_content["cart_token"]
            print(f"  add 'apple'  -> served_by={result.structured_content['served_by']}  items={result.structured_content['items']}")

            result = await client_b.call_tool("add_item", {"item": "bread", "cart_token": token})
            token = result.structured_content["cart_token"]
            print(f"  add 'bread'  -> served_by={result.structured_content['served_by']}  items={result.structured_content['items']}")

            result = await client_a.call_tool("view_cart", {"cart_token": token})
            print(f"  view         -> served_by={result.structured_content['served_by']}  items={result.structured_content['items']}")

            print("\nTAMPERED TOKEN")
            payload, signature = token.split(".", 1)
            tampered = payload + "." + ("x" if signature[0] != "x" else "y") + signature[1:]
            result = await client_a.call_tool("view_cart", {"cart_token": tampered})
            print(f"  view         -> is_error={result.is_error}  {result.content[0].text!r}")
    finally:
        process_a.terminate()
        process_b.terminate()
        await process_a.wait()
        await process_b.wait()


if __name__ == "__main__":
    asyncio.run(main())
