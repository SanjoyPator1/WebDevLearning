# Problem 04 -- two versions of the same cart. One keeps state in the
# server's own memory (breaks across replicas), one signs the state into a
# token the client carries around (works across replicas).

import base64
import hashlib
import hmac
import json
import os
import sys

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

REPLICA_NAME = os.environ.get("CART_REPLICA", "?")
PORT = int(os.environ.get("CART_PORT", "8001"))
SECRET = os.environ["CART_SECRET"].encode()

mcp = MCPServer("Shopping Cart")


class NaiveCart(BaseModel):
    served_by: str
    cart: list[str]


class TokenCart(BaseModel):
    served_by: str
    items: list[str]
    cart_token: str

# the naive version's state -- this dict only exists in THIS process
CARTS: dict[str, list[str]] = {}


def _sign(payload: bytes) -> str:
    digest = hmac.new(SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode()


def _make_token(items: list[str]) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"items": items}).encode()).decode()
    signature = _sign(payload.encode())
    return f"{payload}.{signature}"


def _read_token(token: str) -> list[str]:
    try:
        payload, signature = token.split(".", 1)
    except ValueError:
        raise ToolError("malformed cart token") from None

    expected = _sign(payload.encode())
    if not hmac.compare_digest(expected, signature):
        raise ToolError("this cart token has been modified or is invalid")

    data = json.loads(base64.urlsafe_b64decode(payload.encode()))
    return data["items"]


@mcp.tool()
def naive_add(cart_id: str, item: str) -> NaiveCart:
    """Add an item to a cart kept in this server's own memory (naive version)."""
    CARTS.setdefault(cart_id, []).append(item)
    print(f"[{REPLICA_NAME}] naive_add({cart_id!r}, {item!r})", file=sys.stderr)
    return NaiveCart(served_by=REPLICA_NAME, cart=CARTS[cart_id])


@mcp.tool()
def naive_view(cart_id: str) -> NaiveCart:
    """View a cart kept in this server's own memory (naive version)."""
    return NaiveCart(served_by=REPLICA_NAME, cart=CARTS.get(cart_id, []))


@mcp.tool()
def add_item(item: str, cart_token: str | None = None) -> TokenCart:
    """Add an item to a cart whose contents travel inside a signed token."""
    items = _read_token(cart_token) if cart_token else []
    items.append(item)
    print(f"[{REPLICA_NAME}] add_item({item!r}) -> {items}", file=sys.stderr)
    return TokenCart(served_by=REPLICA_NAME, items=items, cart_token=_make_token(items))


@mcp.tool()
def view_cart(cart_token: str) -> TokenCart:
    """View a cart from its signed token, without the server remembering anything."""
    items = _read_token(cart_token)
    return TokenCart(served_by=REPLICA_NAME, items=items, cart_token=cart_token)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=PORT, stateless_http=True)
