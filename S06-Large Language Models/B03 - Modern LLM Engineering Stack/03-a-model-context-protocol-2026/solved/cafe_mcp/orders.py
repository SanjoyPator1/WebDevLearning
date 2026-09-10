# ============================================================
# TOPIC: 07 onwards — the shared order/cart logic
# REF:   notes/07-the-order-token.md, notes/08-mrtr.md
# ============================================================
#
# Like every other cafe_mcp module, this imports NOTHING from MCP.
#
# Topic 07 introduced the order token; topic 08's place_order needs the exact
# same "load a cart, reprice it, total it" logic a second time, on the way to
# actually committing an order. Rather than duplicate that logic across two
# topic files, or have one topic file import another (which would break the
# "every tNN_*.py is a standalone, independently-runnable server" rule), it
# lives here — the same reasoning that put the menu in menu.py and the cursor
# math in pagination.py.

from cafe_mcp import menu, tokens

ORDER_KIND = "order"
"""The `kind` an order-cart token is signed with. Centralised here so t07 and
t08 cannot drift into signing/verifying two different strings for the same
concept."""


class OrderPricingError(Exception):
    """A cart line can no longer be priced — usually because the menu changed
    between the line being added and the cart being read.

    A plain domain exception, same discipline as CursorError and Drink's
    KeyError: this module does not know whether its caller is a tool that will
    wrap this in ToolError, or a test that will assert on it directly.
    """


class OrderLine:
    """One priced line item. A tiny plain class, not a pydantic BaseModel —
    THIS module stays MCP- and pydantic-agnostic; the tool layer in each
    tNN_*.py file is what turns these into a pydantic response shape the SDK
    can publish a schema for. Keeping the two separate means changing how a
    tool presents a line never requires touching the pricing logic."""

    __slots__ = ("slug", "name", "size", "qty", "unit_price", "line_total")

    def __init__(self, *, slug: str, name: str, size: str, qty: int, unit_price: float) -> None:
        self.slug = slug
        self.name = name
        self.size = size
        self.qty = qty
        self.unit_price = unit_price
        self.line_total = round(unit_price * qty, 2)

    def as_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "size": self.size,
            "qty": self.qty,
            "unit_price": self.unit_price,
            "line_total": self.line_total,
        }


def load_cart(order_token: str) -> list[dict]:
    """Verify an order token and return its raw stored lines.

    Raises tokens.TokenError — deliberately NOT converted to anything
    MCP-flavoured here. Every caller (t07's add_to_order/view_order, t08's
    place_order) converts it to a ToolError with wording appropriate to what
    IT was trying to do; the failure means something slightly different in
    each context ("that cart is invalid" vs "that order can't be placed").
    """
    body = tokens.verify(ORDER_KIND, order_token)
    return body["lines"]


def sign_cart(cart_lines: list[dict], *, ttl_s: int) -> str:
    """Mint a fresh order token carrying the given lines."""
    return tokens.sign(ORDER_KIND, {"lines": cart_lines}, ttl_s=ttl_s)


def reprice(cart_lines: list[dict]) -> list[OrderLine]:
    """Recompute every line's price from the CURRENT menu.

    Never trust a price that might have been stored earlier — if the café's
    prices change between a line being added and the cart being read, the
    cart must reflect TODAY's price. The token remembers what was ordered,
    never what it cost at the time.
    """
    lines = []
    for line in cart_lines:
        unit_price = menu.price_of(line["slug"], line["size"])
        if unit_price is None:
            raise OrderPricingError(f"{line['slug']} is no longer sold in size {line['size']!r}")
        drink = menu.find(line["slug"])
        lines.append(
            OrderLine(
                slug=line["slug"],
                name=drink.name,
                size=line["size"],
                qty=line["qty"],
                unit_price=unit_price,
            )
        )
    return lines


def total_of(lines: list[OrderLine]) -> float:
    """Sum of every line's line_total, rounded to two decimals."""
    return round(sum(line.line_total for line in lines), 2)


def summarize(lines: list[OrderLine]) -> str:
    """A short human-readable line for a confirmation message, e.g.
    '2x Latte (L), 1x Espresso (S)'."""
    return ", ".join(f"{line.qty}x {line.name} ({line.size})" for line in lines)
