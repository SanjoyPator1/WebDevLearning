# ============================================================
# TOPIC: 04 onwards — turning the menu into readable documents
# REF:   notes/04-resources.md
# ============================================================
#
# Like menu.py, this imports NOTHING from MCP.
#
# A resource's job is to hand back a DOCUMENT. Building that document is ordinary
# string work, and keeping it here means tests/test_render.py can check the
# markdown without a server, a transport or an event loop in the picture.
#
# Given complete in both solved/ and solutions/ — it is formatting, not a lesson.

import json

from cafe_mcp.menu import Drink, all_drinks, find, sizes_for


def _price_row(drink: Drink) -> str:
    """One markdown table row: name, then a price per size or a dash."""
    cells = []
    for size in ("S", "M", "L"):
        price = drink.prices.get(size)
        cells.append(f"${price:.2f}" if price is not None else "—")
    dairy = "yes" if drink.dairy_free else "no"
    prices = " | ".join(cells)
    return f"| {drink.name} | `{drink.slug}` | {prices} | {drink.caffeine_mg} | {dairy} |"


def menu_markdown() -> str:
    """The whole menu as a markdown document.

    Written to be dropped into a model's context as-is, which shapes two choices:

    1. The slug is in the table, in backticks. A model that reads this document and
       then wants to call `get_drink` already has the exact argument, so it never
       has to guess or make an extra `list_drinks` call.
    2. A dash marks a size that is not sold, rather than the row being omitted or
       the price being blank. Absence is easy to misread; an explicit "not sold"
       is not.
    """
    lines = [
        "# The Café Menu",
        "",
        "Prices in dollars. A dash means that size is not sold.",
        "",
        "| Drink | Slug | S | M | L | Caffeine (mg) | Dairy-free |",
        "|-------|------|---|---|---|---------------|------------|",
    ]
    lines.extend(_price_row(drink) for drink in all_drinks())
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "Espresso, macchiato and cortado are not sold large. Cold brew and the "
            "crème brûlée latte are not sold small.",
            "",
            "For a dairy-free order, the oat latte is the usual substitute for any "
            "milk drink; the americano and espresso are dairy-free already.",
        ]
    )
    return "\n".join(lines) + "\n"


def dairy_free_markdown() -> str:
    """Just the dairy-free drinks, as a short markdown list.

    A second, narrower document over the same data. That is the whole argument for
    resources being addressed by URI: `cafe://menu/dairy-free` costs the caller far
    fewer tokens than the full menu when the full menu is not what they need.
    """
    drinks = [drink for drink in all_drinks() if drink.dairy_free]
    lines = ["# Dairy-Free Drinks", ""]
    for drink in drinks:
        sizes = ", ".join(sizes_for(drink.slug))
        lines.append(f"- **{drink.name}** (`{drink.slug}`) — sizes {sizes}. {drink.description}")
    lines.extend(["", f"{len(drinks)} of {len(all_drinks())} drinks are dairy-free."])
    return "\n".join(lines) + "\n"


def drink_json(slug: str) -> str:
    """One drink as a JSON document, or raise KeyError if there is no such drink.

    KeyError rather than a friendly message, because — unlike a tool — the caller
    of a resource is the CLIENT, not the model. Topic 04 explains why that changes
    how the failure should be reported, and the resource layer does the converting.
    """
    drink = find(slug)
    if drink is None:
        raise KeyError(slug)
    payload = drink.model_dump()
    payload["available_sizes"] = list(sizes_for(slug))
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
