# Problem 10 (optional) -- one long-lived request instead of ask-once,
# get-once. A listener opens a stream and gets told whenever the stock
# resource changes.

import os

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

PORT = int(os.environ.get("INVENTORY_PORT", "8010"))

mcp = MCPServer("Inventory")

STOCK = {"laptop": 5, "phone": 10, "charger": 25}


@mcp.resource("inventory://stock")
def stock() -> str:
    """Current stock levels, one item per line."""
    return "\n".join(f"{item}={count}" for item, count in STOCK.items())


@mcp.tool()
async def sell(item: str, quantity: int, ctx: Context) -> dict:
    """Sell some quantity of an item, lowering stock and notifying listeners."""
    if item not in STOCK:
        raise ToolError(f"no such item: {item}")
    if STOCK[item] < quantity:
        raise ToolError(f"not enough {item} in stock (have {STOCK[item]}, asked for {quantity})")

    STOCK[item] -= quantity
    await ctx.notify_resource_updated("inventory://stock")
    return {"item": item, "sold": quantity, "remaining": STOCK[item]}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=PORT, stateless_http=True)
