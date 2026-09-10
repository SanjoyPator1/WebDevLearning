# ============================================================
# TOPIC: 02 onwards — the café's menu
# REF:   notes/02-tools-list.md
# ============================================================
#
# This module imports NOTHING from MCP, on purpose.
#
# That discipline is the single most useful structural habit when building an MCP
# server. The protocol is a doorway; your domain logic should not know the doorway
# exists. Concretely it buys you three things:
#
#   1. tests/test_menu.py can exercise all of this with no server, no transport,
#      no async, and no event loop.
#   2. If MCP is replaced by something else in three years, this file survives.
#   3. When something breaks you immediately know which side it broke on.
#
# This file is given to you complete in BOTH solved/ and solutions/. It is data,
# not a lesson — copying twelve drinks by hand teaches nothing. The exercises live
# in the tNN_*.py server files.

from pydantic import BaseModel, Field


# WATCH OUT: a pydantic model's CLASS DOCSTRING becomes the `description` of its
# JSON Schema, and from topic 02 that schema is published as a tool's
# `outputSchema` — so this docstring goes over the wire to the language model.
#
# That means notes-to-self do not belong in it. Keep the docstring as the text you
# would want a model to read, and put your own commentary in comments like this
# one, which stay on this side of the wire.
class Drink(BaseModel):
    """One item on the café menu: a drink, its prices per size, and its properties."""

    slug: str = Field(description="Stable machine identifier, e.g. 'flat-white'.")
    name: str = Field(description="Human-readable name, e.g. 'Flat White'.")
    description: str = Field(
        description="One line, written to be read by a language model choosing a drink."
    )
    prices: dict[str, float] = Field(
        description="Price per available size. A size absent here is not orderable."
    )
    caffeine_mg: int = Field(description="Approximate caffeine content in milligrams.")
    dairy_free: bool = Field(description="True if the drink contains no dairy by default.")


SIZES: tuple[str, ...] = ("S", "M", "L")
"""The sizes the café recognises. Not every drink offers all three."""


# The order of this tuple is LOAD-BEARING.
#
# The 2026-07-28 spec says servers SHOULD return tools from `tools/list` in a
# deterministic order, and the same reasoning applies to any list a model sees:
# a stable order means the client can cache it, and — more importantly — means the
# model's prompt prefix does not change between calls, so provider-side prompt
# caching keeps hitting. A menu that reshuffles itself costs real money.
#
# Note the deliberate irregularities, each of which exists to be a test case later:
#   - espresso / macchiato / cortado have NO large size  -> topic 03 validation
#   - cold-brew and creme-brulee-latte have no small     -> same
#   - creme-brulee-latte has non-ASCII in its name       -> topic 13 header encoding
#   - oat-latte and americano are dairy-free             -> topic 05 prompt filtering
DRINKS: tuple[Drink, ...] = (
    Drink(
        slug="espresso",
        name="Espresso",
        description="A single short shot. Bitter, intense, no milk. Order this when someone wants caffeine with no ceremony.",
        prices={"S": 2.20, "M": 2.60},
        caffeine_mg=63,
        dairy_free=True,
    ),
    Drink(
        slug="macchiato",
        name="Macchiato",
        description="Espresso 'stained' with a spoon of foamed milk. Nearly as strong as espresso but softer.",
        prices={"S": 2.50, "M": 2.90},
        caffeine_mg=63,
        dairy_free=False,
    ),
    Drink(
        slug="cortado",
        name="Cortado",
        description="Espresso cut with an equal amount of warm milk. Small, balanced, no foam.",
        prices={"S": 2.90, "M": 3.30},
        caffeine_mg=63,
        dairy_free=False,
    ),
    Drink(
        slug="flat-white",
        name="Flat White",
        description="Double espresso with velvety steamed milk and a thin layer of microfoam. The default choice for someone who wants coffee-forward milk coffee.",
        prices={"S": 3.10, "M": 3.60, "L": 4.20},
        caffeine_mg=130,
        dairy_free=False,
    ),
    Drink(
        slug="latte",
        name="Latte",
        description="Espresso with a lot of steamed milk. The mildest milk coffee; pick this when someone says they do not really like coffee.",
        prices={"S": 3.20, "M": 3.70, "L": 4.30},
        caffeine_mg=130,
        dairy_free=False,
    ),
    Drink(
        slug="cappuccino",
        name="Cappuccino",
        description="Equal parts espresso, steamed milk and foam. Lighter in the cup than a latte, more foam on top.",
        prices={"S": 3.20, "M": 3.70, "L": 4.30},
        caffeine_mg=130,
        dairy_free=False,
    ),
    Drink(
        slug="americano",
        name="Americano",
        description="Espresso lengthened with hot water. Black, long, no milk. The closest thing here to filter coffee.",
        prices={"S": 2.70, "M": 3.10, "L": 3.60},
        caffeine_mg=130,
        dairy_free=True,
    ),
    Drink(
        slug="mocha",
        name="Mocha",
        description="Latte with chocolate. Sweet, dessert-adjacent; suggest it when someone wants a treat rather than a coffee.",
        prices={"S": 3.60, "M": 4.10, "L": 4.80},
        caffeine_mg=145,
        dairy_free=False,
    ),
    Drink(
        slug="cold-brew",
        name="Cold Brew",
        description="Coarse grounds steeped cold for eighteen hours. Smooth, low acidity, high caffeine. No small size.",
        prices={"M": 3.90, "L": 4.60},
        caffeine_mg=200,
        dairy_free=True,
    ),
    Drink(
        slug="oat-latte",
        name="Oat Latte",
        description="A latte built on oat milk. The dairy-free default — suggest this first when someone avoids dairy.",
        prices={"S": 3.60, "M": 4.10, "L": 4.70},
        caffeine_mg=130,
        dairy_free=True,
    ),
    Drink(
        slug="creme-brulee-latte",
        name="Crème Brûlée Latte",
        description="Latte with burnt-sugar syrup and a torched sugar crust. Very sweet, seasonal. No small size.",
        prices={"M": 4.60, "L": 5.20},
        caffeine_mg=130,
        dairy_free=False,
    ),
    Drink(
        slug="chai",
        name="Masala Chai",
        description="Spiced black tea simmered with milk. Contains no coffee at all — offer it when someone wants warmth without espresso.",
        prices={"S": 3.00, "M": 3.40, "L": 4.00},
        caffeine_mg=40,
        dairy_free=False,
    ),
)


def all_drinks() -> tuple[Drink, ...]:
    """Every drink, in the stable order defined above."""
    return DRINKS


def find(slug: str) -> Drink | None:
    """Look up one drink by slug. Returns None if there is no such drink.

    Returning None rather than raising is deliberate: the *tool* layer decides how
    a missing drink should be reported to a model, and that decision does not
    belong in the menu.
    """
    for drink in DRINKS:
        if drink.slug == slug:
            return drink
    return None


def sizes_for(slug: str) -> tuple[str, ...]:
    """The sizes a given drink is actually available in, in S/M/L order.

    Returns an empty tuple for an unknown slug.
    """
    drink = find(slug)
    if drink is None:
        return ()
    return tuple(size for size in SIZES if size in drink.prices)


def price_of(slug: str, size: str) -> float | None:
    """Price for one drink at one size, or None if that combination is not sold."""
    drink = find(slug)
    if drink is None:
        return None
    return drink.prices.get(size)
