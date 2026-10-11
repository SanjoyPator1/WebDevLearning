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

    env = {**os.environ, "CART_REPLICA": name, "CART_PORT": str(port), "CART_SECRET": SHARED_SECRET}
    process = await asyncio.create_subprocess_exec(sys.executable, str(SERVER_PATH), env=env)
    await asyncio.sleep(1)  # give uvicorn a moment to come up
    return process


async def main() -> None:
    process_a = await start_replica("A", 8001)
    process_b = await start_replica("B", 8002)

    try:
        # your turn: open two Clients, one per URL (8001, 8002)

        # your turn: TAMPERED TOKEN -- flip the first character of the
        # signature part and call view_cart, print is_error and the message
        
        async with Client("http://127.0.0.1:8001/mcp") as client_a, Client("http://127.0.0.1:8002/mcp") as client_b:

            # your turn: NAIVE CART -- add 'apple' on A, add 'bread' on B, view on A
            # print served_by and the cart each time -- it should be wrong
            print("--------- NAIVE CART (state in server memory)----------")
            result = await client_a.call_tool("naive_add", {"cart_id": "c1", "item": "apple"})
            print(f"  add 'apple'  -> {result.structured_content}")
            result = await client_b.call_tool("naive_add", {"cart_id": "c1", "item": "bread"})
            print(f"  add 'bread'  -> {result.structured_content}")
            result = await client_a.call_tool("naive_view", {"cart_id": "c1"})
            print(f"  view         -> {result.structured_content}")

            # your turn: TOKEN CART -- same three steps, passing cart_token along
            # each time -- it should be right
            print("\n--------- TOKEN CART (state travels with the request)--------")
            result = await client_a.call_tool("add_item", {"item": "apple"})
            token = result.structured_content["cart_token"]
            print(f"  add 'apple'  -> served_by={result.structured_content['served_by']}  items={result.structured_content['items']}")
            print(f"    token returned is : {token}")

            result = await client_b.call_tool("add_item", {"item": "bread", "cart_token": token})
            token = result.structured_content["cart_token"]
            print(f"  add 'bread'  -> served_by={result.structured_content['served_by']}  items={result.structured_content['items']}")
            print(f"    token returned is : {token}")

            result = await client_a.call_tool("view_cart", {"cart_token": token})
            print(f"  view         -> served_by={result.structured_content['served_by']}  items={result.structured_content['items']}")

            print("\n------- TAMPERED TOKEN---------")
            payload, signature = token.split(".", 1)
            tampered = payload + "." + ("x" if signature[0] != "x" else "y") + signature[1:]
            result = await client_a.call_tool("view_cart", {"cart_token": tampered})
            print(f"  view         -> is_error={result.is_error}  result.content = {result.content[0].text!r}")


    finally:
        process_a.terminate()
        process_b.terminate()
        await process_a.wait()
        await process_b.wait()


if __name__ == "__main__":
    asyncio.run(main())

# Terminal run - logs
# only run the client - it spawns two sub processes for server to show stateless architecture
# python 04_cart_client.py
# INFO:     Started server process [64436]
# INFO:     Waiting for application startup.
# [10/06/26 20:59:59] INFO     StreamableHTTP session manager started                                        streamable_http_manager.py:148
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
# INFO:     Started server process [64459]
# INFO:     Waiting for application startup.
# [10/06/26 21:00:00] INFO     StreamableHTTP session manager started                                        streamable_http_manager.py:148
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://127.0.0.1:8002 (Press CTRL+C to quit)
# INFO:     127.0.0.1:54616 - "POST /mcp HTTP/1.1" 200 OK
# INFO:     127.0.0.1:54617 - "POST /mcp HTTP/1.1" 200 OK
# --------- NAIVE CART (state in server memory)----------
# [A] naive_add('c1', 'apple')
# INFO:     127.0.0.1:54616 - "POST /mcp HTTP/1.1" 200 OK
# INFO:     127.0.0.1:54616 - "POST /mcp HTTP/1.1" 200 OK
#   add 'apple'  -> {'served_by': 'A', 'cart': ['apple']}
# [B] naive_add('c1', 'bread')
# INFO:     127.0.0.1:54617 - "POST /mcp HTTP/1.1" 200 OK
# INFO:     127.0.0.1:54617 - "POST /mcp HTTP/1.1" 200 OK
#   add 'bread'  -> {'served_by': 'B', 'cart': ['bread']}
# INFO:     127.0.0.1:54616 - "POST /mcp HTTP/1.1" 200 OK
#   view         -> {'served_by': 'A', 'cart': ['apple']}

# --------- TOKEN CART (state travels with the request)--------
# [A] add_item('apple') -> ['apple']
# INFO:     127.0.0.1:54616 - "POST /mcp HTTP/1.1" 200 OK
#   add 'apple'  -> served_by=A  items=['apple']
#     token returned is : eyJpdGVtcyI6IFsiYXBwbGUiXX0=.4EJgCoiDlqO7jjf6xlT3IcilolZhYBpLVcoWu6q9rZE=
# [B] add_item('bread') -> ['apple', 'bread']
# INFO:     127.0.0.1:54617 - "POST /mcp HTTP/1.1" 200 OK
#   add 'bread'  -> served_by=B  items=['apple', 'bread']
#     token returned is : eyJpdGVtcyI6IFsiYXBwbGUiLCAiYnJlYWQiXX0=.KjskC3uDMhGPDfqgYzxdgZvGxZ3j03ASwZZ5axQAUN8=
# INFO:     127.0.0.1:54616 - "POST /mcp HTTP/1.1" 200 OK
#   view         -> served_by=A  items=['apple', 'bread']

# ------- TAMPERED TOKEN---------
# [10/06/26 21:00:01] INFO     Tool 'view_cart' failed: 'Error executing tool view_cart: this cart token has been modified or server.py:438
#                              is invalid'                                                                                                 
# INFO:     127.0.0.1:54616 - "POST /mcp HTTP/1.1" 200 OK
#   view         -> is_error=True  result.content = 'Error executing tool view_cart: this cart token has been modified or is invalid'
# INFO:     Shutting down
# INFO:     Shutting down
# INFO:     Waiting for application shutdown.
# [10/06/26 21:00:02] INFO     StreamableHTTP session manager shutting down                                  streamable_http_manager.py:152
# INFO:     Application shutdown complete.
# INFO:     Finished server process [64459]
# INFO:     Waiting for application shutdown.
# [10/06/26 21:00:02] INFO     StreamableHTTP session manager shutting down                                  streamable_http_manager.py:152
# INFO:     Application shutdown complete.
# INFO:     Finished server process [64436]
