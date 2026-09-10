# ============================================================
# TOPIC: 03 — tools/call: arguments, structured output, failure
# REF:   notes/03-tools-call.md
# RUN:   python solved/t03_calls_and_errors.py
# ============================================================
#
# Topic 02 built the menu card. This is what happens when the model actually calls,
# and the subject is FAILURE — because that is where MCP's design is least obvious
# and most consequential.
#
# Three ways a call can go wrong, and they are genuinely different:
#
#   1. The ARGUMENTS are the wrong shape.
#      Caught by the schema, before your function runs. You write no code.
#
#   2. The arguments are well-formed but WRONG for the data.
#      "size L" is a perfectly good string; espresso just is not sold in it. Only
#      your code can know. This is what ToolError is for.
#
#   3. Something BROKE.
#      A bug, a dead database, an unhandled None. The model must not see the
#      details, and by default it does not.
#
# The whole point of this file is that (2) and (3) look identical in a naive server
# and must not be.

# --- Imports ---
import os
import sys
from typing import Annotated, Literal

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))
MAX_QTY = 10


# --- Output models ---
class DrinkResult(BaseModel):
    """One drink, with the sizes it is genuinely sold in."""

    drink: menu.Drink
    available_sizes: list[str] = Field(
        description=(
            "Sizes this drink is actually sold in. A size not listed here cannot be ordered."
        )
    )


class QuoteResult(BaseModel):
    """A price quote for a specific drink, size and quantity."""

    slug: str
    name: str = Field(description="Display name, for reading back to the customer.")
    size: str
    qty: int
    unit_price: float = Field(description="Price for one, at this size.")
    total: float = Field(description="unit_price * qty, rounded to two decimals.")
    caffeine_mg_total: int = Field(description="Total caffeine across all cups in this quote.")


# --- The server ---
mcp = MCPServer(
    name="cafe-mcp",
    version="0.3.0",
    instructions=(
        "You are working the counter of a small coffee shop. Use `list_drinks` to see the "
        "menu, `get_drink` for one item, and `quote` to price a specific drink, size and "
        "quantity before committing to anything. Sizes are S, M and L, but not every drink "
        "is sold in every size — `quote` will tell you which sizes are available if you "
        "pick one that is not."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


# --- Tools ---
@mcp.tool(
    annotations=ToolAnnotations(
        title="List the drinks",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def list_drinks() -> list[menu.Drink]:
    """Show the whole menu.

    Call this first, before recommending anything, so you are talking about drinks
    that actually exist. Returns every drink with its prices per size, caffeine
    content and whether it is dairy-free.
    """
    drinks = list(menu.all_drinks())
    print(f"  [server] list_drinks() -> {len(drinks)} drinks", file=sys.stderr)
    return drinks


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get one drink",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def get_drink(
    slug: Annotated[
        str,
        Field(
            description=(
                "The drink's slug, lowercase with hyphens, exactly as it appears in "
                "`list_drinks` — for example 'flat-white' or 'cold-brew'. Not the "
                "display name."
            )
        ),
    ],
) -> DrinkResult:
    """Look up the detail of a single drink by its slug.

    Use this when the customer has named a drink and you need its price, its
    caffeine content, or which sizes it comes in. If you do not already know the
    exact slug, call `list_drinks` first rather than guessing.
    """
    drink = menu.find(slug)
    print(f"  [server] get_drink({slug!r}) -> {'found' if drink else 'MISSING'}", file=sys.stderr)

    if drink is None:
        # THE FIX from topic 02. `ToolError` means "this failed in a way I EXPECTED,
        # and the message is safe and useful for a model to read". The SDK passes it
        # through verbatim instead of swallowing it.
        #
        # Which puts a real obligation on the message. Compare:
        #
        #   BAD : "invalid slug"
        #   BAD : "KeyError: 'no-such-drink'"
        #   GOOD: "There is no drink with slug 'no-such-drink'. Call list_drinks to
        #          see what is available."
        #
        # The good one is written for a reader who can ACT. It names what went
        # wrong, quotes the offending value, and gives the next step. A model that
        # reads it recovers on the next turn instead of retrying the same call.
        raise ToolError(
            f"There is no drink with slug {slug!r}. Call `list_drinks` to see the "
            f"twelve slugs that exist — they are lowercase with hyphens, like "
            f"'flat-white'."
        )

    return DrinkResult(drink=drink, available_sizes=list(menu.sizes_for(slug)))


@mcp.tool(
    annotations=ToolAnnotations(
        title="Price a drink",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def quote(
    slug: Annotated[
        str,
        Field(description="The drink's slug, exactly as it appears in `list_drinks`."),
    ],
    # --- VALIDATION KIND 1: the schema does it ---
    # `Literal["S", "M", "L"]` becomes a JSON Schema `enum`. The model sees the
    # three legal values in the schema itself, so it cannot pass "large" or "XL" —
    # the request is rejected before this function is entered, and you write no
    # code for it.
    #
    # Push a constraint into the schema whenever the set of legal values is FIXED.
    # It is cheaper (no round trip wasted) and clearer (the model reads it up
    # front rather than discovering it by failing).
    size: Annotated[
        Literal["S", "M", "L"],
        Field(description="Cup size. Not every drink is sold in every size."),
    ],
    # `ge`/`le` become `minimum`/`maximum` in the schema — same deal.
    qty: Annotated[
        int,
        Field(ge=1, le=MAX_QTY, description=f"How many cups, from 1 to {MAX_QTY}."),
    ] = 1,
) -> QuoteResult:
    """Price a specific drink at a specific size and quantity.

    Use this before telling a customer what something costs, and before adding
    anything to an order. It will refuse a size the drink is not sold in and tell
    you which sizes it does come in, so you can correct yourself in one step.
    """
    print(f"  [server] quote(slug={slug!r}, size={size!r}, qty={qty})", file=sys.stderr)

    drink = menu.find(slug)
    if drink is None:
        raise ToolError(
            f"There is no drink with slug {slug!r}. Call `list_drinks` to see what exists."
        )

    # --- VALIDATION KIND 2: only your code can do it ---
    # "L" is a legal size and passed the schema. Whether THIS drink is sold in it
    # depends on data the schema knows nothing about. So the check lives here, and
    # the error message carries the information needed to fix it.
    unit_price = menu.price_of(slug, size)
    if unit_price is None:
        available = ", ".join(menu.sizes_for(slug))
        raise ToolError(
            f"{drink.name} is not sold in size {size!r}. It comes in: {available}. "
            f"Ask the customer to pick one of those, or suggest a similar drink that "
            f"does come in {size!r}."
        )

    total = round(unit_price * qty, 2)
    print(f"  [server]   -> {qty} x {drink.name} ({size}) = {total}", file=sys.stderr)

    return QuoteResult(
        slug=slug,
        name=drink.name,
        size=size,
        qty=qty,
        unit_price=unit_price,
        total=total,
        caffeine_mg_total=drink.caffeine_mg * qty,
    )


# --- VALIDATION KIND 3: something broke ---
# This tool is a DEMONSTRATION OF WHAT NOT TO DO. It is here so you can see, on the
# wire, what the model receives when your code raises something that is not a
# ToolError. Never ship a tool like this.
@mcp.tool(
    annotations=ToolAnnotations(
        title="DEMO: a tool that breaks badly",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def broken_on_purpose(slug: str) -> str:
    """DEMONSTRATION ONLY — do not call this expecting it to work.

    This tool exists to show what a model receives when a server raises an
    ordinary exception instead of a ToolError. Compare its output with
    `get_drink` given the same bad slug.
    """
    print(f"  [server] broken_on_purpose({slug!r}) -- about to raise", file=sys.stderr)
    # Imagine this were an accident: a KeyError from a dict you assumed had the key.
    # The message contains something you would not want to hand a model — here a
    # fake internal path, standing in for a connection string or a stack detail.
    raise KeyError(f"{slug} not in /var/lib/cafe/internal-menu-cache.sqlite")


# --- Health ---
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "03"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 03 — tools/call and failure")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("  tools    : list_drinks, get_drink, quote, broken_on_purpose")
    print("-" * 68)
    print("  Run these IN ORDER — the comparison is the lesson:")
    print("    bash curl/03_quote_ok.sh              happy path")
    print("    bash curl/03_quote_bad_size.sh        ToolError, message gets through")
    print("    bash curl/03_quote_bad_enum.sh        schema rejects it first")
    print("    bash curl/03_quote_bad_qty.sh         schema range check")
    print("    bash curl/03_broken.sh                message WITHHELD — see why")
    print("    bash curl/03_unknown_tool.sh          isError, not a JSON-RPC error")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
