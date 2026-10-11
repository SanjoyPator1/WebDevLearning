# Problem 10 (optional) -- run a watcher and a shopper at once.

import asyncio

from mcp.client import Client

URL = "http://127.0.0.1:8010/mcp"


async def watch(events_seen: list[int]) -> None:
    # your turn: client.listen(resource_subscriptions=["inventory://stock"]),
    # re-read the resource on each event, stop after 3
    raise NotImplementedError


async def shop() -> None:
    # your turn: sell laptop x1, phone x2, charger x5, 1 second apart
    raise NotImplementedError


async def main() -> None:
    events_seen: list[int] = []
    await asyncio.gather(watch(events_seen), shop())


if __name__ == "__main__":
    asyncio.run(main())
