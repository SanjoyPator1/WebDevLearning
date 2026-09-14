# ============================================================
# TOPIC: 02 — tools/list: schemas, annotations, cache hints
# REF:   notes/02-tools-list.md
# RUN:   python solutions/t02_tools.py
# ============================================================
#
# YOUR TURN. Six TODOs. The theme: everything here is about what the MODEL sees.
#
# `cafe_mcp/menu.py` is given to you complete — it is domain data, not a lesson.
# What you are writing is the layer that publishes it over MCP.
#
# Prove it from outside when you are done:
#     bash curl/02_tools_list.sh          <- read the schemas carefully
#     bash curl/02_get_drink.sh flat-white
#     bash curl/02_get_drink.sh no-such-drink

# --- Imports ---
import os
import sys
from typing import Annotated

from mcp.server import CacheHint, MCPServer
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))


# --- Output models ---
# TODO 1: Give the tools a typed return shape.
#   Build two pydantic models. The SDK publishes them as each tool's
#   `outputSchema`, so the model on the other end knows the shape of the answer
#   before it calls.
#
#   MenuResult  -> drinks: list[menu.Drink], count: int
#   DrinkResult -> drink: menu.Drink, available_sizes: list[str]
#
#   Put a Field(description=...) on each field. And remember what you learned
#   about CLASS DOCSTRINGS: they travel to the model too, so write them for a
#   model and keep your own notes in comments.
class MenuResult(BaseModel):
    """Everything on the menu"""

    drinks: list[menu.Drink] = Field(description="Every drink, in stable menu order.")
    count: int = Field(description="How many drinks are listed.")


class DrinkResult(BaseModel):
    """One drink, with its orderable sizes spelled out."""

    drink: menu.Drink
    available_sizes: list[str] = Field(
        description=(
            "Sizes this drink is actually sold in. A size not listed here cannot be ordered."
        )
    )


# --- The server ---
# TODO 2: Add cache hints.
#   List results MUST carry `ttlMs` and `cacheScope` as of 2026-07-28. Without the
#   `cache_hints` argument you get ttlMs=0 / cacheScope="private", i.e. "nobody
#   may cache this".
#
#   Pass cache_hints={"tools/list": CacheHint(ttl_ms=..., scope=...)}.
#   Five minutes is a sensible TTL for a menu.
#
#   The scope is a JUDGEMENT, not a default. Ask yourself: does this tool list
#   look the same for every caller? If yes, "public" is safe and useful. If it
#   could ever vary by who is asking, "public" leaks one caller's view to
#   another. Decide, then write a comment saying why.
mcp = MCPServer(
    name="cafe-mcp",
    version="0.2.0",
    instructions=(
        # TODO 3: write this.
        # Free text handed to the MODEL. Say what this server is for and warn it
        # about the one thing it will otherwise get wrong: not every drink is sold
        # in every size.
        "You are working the counter of a small coffee shop. Use `list_drinks` to see "
        "what is on the menu and `get_drink` for the detail of one item. Sizes are S, M "
        "and L, but not every drink is sold in every size — always check "
        "`available_sizes` before promising a size to a customer."
    ),
    # cache_hints=...,
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


# --- Tools ---
# NOTE: registration order is what `tools/list` returns. Keep it deliberate.


# TODO 4: Annotate and document list_drinks.
#   - ToolAnnotations with a title and the four hints. This tool reads and changes
#     nothing and touches nothing outside this server — so which are True?
#   - A docstring written as an instruction to a model: when should it call this?
@mcp.tool(
    annotations=ToolAnnotations(
        title="List the drinks",
        # --- THE FOUR HINTS ---
        # These are PROMISES to the client, not enforcement. The protocol never
        # checks them. Hosts use them to decide what needs a permission prompt and
        # what can run silently, so lying here is a security bug, not a typo.
        read_only_hint=True,  # changes nothing in the world
        destructive_hint=False,  # (only meaningful when read_only is False)
        idempotent_hint=True,  # calling it twice == calling it once
        open_world_hint=False,  # touches nothing outside this server
    )
)  # replace
def list_drinks() -> "MenuResult":
    """Show the whole menu.

    Call this first, before recommending anything, so you are talking about drinks
    that actually exist. Returns every drink with its prices per size, caffeine
    content and whether it is dairy-free.

    There is no pagination here yet — this returns all twelve drinks at once. Topic
    06 adds a cursor.
    """
    drinks = list(menu.all_drinks())
    print(f"  [server] list_drinks() -> {len(drinks)} drinks", file=sys.stderr)
    return MenuResult(drinks=drinks, count=len(drinks))


# TODO 5: Describe the ARGUMENT, not just the tool.
#   Wrap `slug` in Annotated[str, Field(description=...)]. The docstring describes
#   the tool; this describes one input, and the model reads both. Answer the
#   question a model would actually have: what format is a slug, and where does it
#   get one from?
@mcp.tool(
    annotations=ToolAnnotations(
        title="Get one drink",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)  # replace with annotations
def get_drink(
    # `Annotated[str, Field(description=...)]` is how you put words on an ARGUMENT.
    # The docstring describes the tool; this describes one input. Both end up in
    # the JSON Schema the model reads, and the model uses argument descriptions to
    # decide what to put there — so "which slug format?" is worth answering here.
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
) -> "DrinkResult":
    """Look up the detail of a single drink by its slug.

    Use this when the customer has named a drink and you need its price, its
    caffeine content, or which sizes it comes in. If you do not already know the
    exact slug, call `list_drinks` first rather than guessing.

    Returns the drink plus `available_sizes` — the sizes it is genuinely sold in,
    which is not always all three.
    """
    drink = menu.find(slug)
    print(f"  [server] get_drink({slug!r}) -> {'found' if drink else 'MISSING'}", file=sys.stderr)

    if drink is None:
        # Leave this as a bare ValueError for now — it is WRONG on purpose.
        # Run `bash curl/02_get_drink.sh no-such-drink` and read exactly what the
        # model receives. Topic 03 is about fixing this.
        raise ValueError(f"no such drink: {slug}")

    return DrinkResult(drink=drink, available_sizes=list(menu.sizes_for(slug)))


# --- Health ---
# TODO 6: Add the /healthz route again. You did this in topic 01.
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28, so this is how you check."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "02"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 02 — tools/list (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
