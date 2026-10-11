# Problem 10 (optional) -- run a watcher and a shopper at once. The
# watcher hears about every sale as it happens; the stretch below shows
# where that stops working.

import asyncio

from mcp.client import Client

URL = "http://127.0.0.1:8010/mcp"


async def watch(events_seen: list[int]) -> None:
    async with Client(URL) as client:
        async with client.listen(resource_subscriptions=["inventory://stock"]) as subscription:
            print("[watcher] listening on inventory://stock")
            async for _event in subscription:
                stock = await client.read_resource("inventory://stock")
                print(f"[watcher] change! stock now: {stock.contents[0].text.replace(chr(10), ' ')}")
                events_seen.append(1)
                if len(events_seen) >= 3:
                    break
    print(f"[watcher] got {len(events_seen)} events, done")


async def shop() -> None:
    async with Client(URL) as client:
        await asyncio.sleep(1)
        print("[shopper] sell laptop x1")
        await client.call_tool("sell", {"item": "laptop", "quantity": 1})

        await asyncio.sleep(1)
        print("[shopper] sell phone x2")
        await client.call_tool("sell", {"item": "phone", "quantity": 2})

        await asyncio.sleep(1)
        print("[shopper] sell charger x5")
        await client.call_tool("sell", {"item": "charger", "quantity": 5})


async def main() -> None:
    events_seen: list[int] = []
    await asyncio.gather(watch(events_seen), shop())


if __name__ == "__main__":
    asyncio.run(main())
