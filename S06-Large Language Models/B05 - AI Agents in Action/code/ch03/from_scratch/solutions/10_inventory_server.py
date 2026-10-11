# Problem 10 (optional) -- a resource that notifies listeners when it
# changes.

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
    # your turn
    return "\n".join(f"{item}:{count}" for item, count in STOCK.items())


@mcp.tool()
async def sell(item: str, quantity: int, ctx: Context) -> dict:
    """Sell some quantity of an item, lowering stock and notifying listeners."""
    # your turn: ToolError if unknown item or not enough stock, else lower
    # stock and call ctx.notify_resource_updated("inventory://stock")
    if item not in STOCK:
        raise ToolError(f"no such item as {item}")

    if STOCK[item] < quantity:
        raise ToolError(f"not enough {item} in stock (have {STOCK[item]}, asked for {quantity})")

    STOCK[item] -= quantity

    # the below line says the resource inventory://stock has changed so
    # if someone is listening to this please update your data get it again
    # this doesnot gives back the new data - it only raises the alarm that the data changed
    await ctx.notify_resource_updated("inventory://stock")

    return {"item" : item, "sold" : quantity, "remaining" : STOCK[item]}

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=PORT, stateless_http=True)
