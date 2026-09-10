# ============================================================
# TOPIC: 02 — tools/list: schemas, annotations, cache hints
# REF:   notes/02-tools-list.md
# RUN:   python solved/t02_tools.py
# ============================================================
#
# Topic 01 had one useless tool. This is the café's actual counter, and the whole
# subject is what the MODEL sees when it asks `tools/list`:
#
#   - how a Python signature becomes a JSON Schema
#   - how `Annotated[..., Field(description=...)]` puts words on each argument
#   - what the four ToolAnnotations hints promise, and to whom
#   - why a pydantic return type is better than a dict
#   - what `cache_hints` buys, and why the ORDER of the tool list matters
#
# Calling tools and failing properly is topic 03. Here we only look at the menu
# card the model is handed.

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
# Returning a pydantic model rather than a dict or a string is worth the extra
# five lines. The SDK reads the model and publishes it as the tool's
# `outputSchema`, so the model on the other end knows the SHAPE of what comes
# back before it ever calls. A tool that returns `dict` publishes no shape at all.
class MenuResult(BaseModel):
    """Everything on the menu."""

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
mcp = MCPServer(
    name="cafe-mcp",
    version="0.2.0",
    instructions=(
        "You are working the counter of a small coffee shop. Use `list_drinks` to see "
        "what is on the menu and `get_drink` for the detail of one item. Sizes are S, M "
        "and L, but not every drink is sold in every size — always check "
        "`available_sizes` before promising a size to a customer."
    ),
    # --- CACHE HINTS ---
    # New requirement in 2026-07-28: list-shaped results MUST carry `ttlMs` and
    # `cacheScope`. Without this argument you get ttlMs=0 / cacheScope="private",
    # which means "do not cache, and no shared proxy may hold it either".
    #
    #   ttl_ms=300_000   -> this menu is good for five minutes
    #   scope="public"   -> a shared intermediary MAY cache it
    #
    # "public" is the right call here and it is a judgement, not a default. This
    # menu is identical for every caller: no per-user pricing, no auth-dependent
    # filtering. The moment a list varies by who is asking, it must be "private"
    # or you will serve one customer another customer's view.
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


# --- Tools ---
# REGISTRATION ORDER IS LOAD-BEARING.
#
# The spec says servers SHOULD return tools from `tools/list` in a deterministic
# order. The SDK preserves registration order, so "deterministic" is free — as long
# as you do not build the list from a set, a dict comprehension over unsorted keys,
# or a directory listing.
#
# It matters for money. The tool list sits near the front of the model's prompt.
# A stable prefix keeps the provider's prompt cache hitting; a list that reshuffles
# invalidates the cache on every call and you pay full price for the whole prefix.
# Two lines of care, measurable saving.


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
)
def list_drinks() -> MenuResult:
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
) -> DrinkResult:
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
        # This is the WRONG way to handle a missing drink, and it is here on
        # purpose so topic 03 can fix it. Read what the model actually receives:
        #
        #     {"content": [{"type": "text", "text": "Error executing tool get_drink"}],
        #      "isError": true}
        #
        # The message is withheld. The model is told only that something failed,
        # with no hint of what or how to recover, so it either gives up or retries
        # the identical call. Topic 03 replaces this with `ToolError`, which sends
        # the message through.
        raise ValueError(f"no such drink: {slug}")

    return DrinkResult(drink=drink, available_sizes=list(menu.sizes_for(slug)))


# --- Health ---
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28, so this is how you check."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "02"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 02 — tools/list")
    print("-" * 68)
    print(f"  endpoint    : http://{HOST}:{PORT}/mcp")
    print("  tools       : list_drinks, get_drink")
    print("  cache hint  : tools/list -> ttlMs=300000, cacheScope=public")
    print("-" * 68)
    print("  Try:")
    print("    bash curl/02_tools_list.sh          <- read the schemas carefully")
    print("    bash curl/02_list_drinks.sh")
    print("    bash curl/02_get_drink.sh flat-white")
    print("    bash curl/02_get_drink.sh no-such-drink   <- the bad error path")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()


# ============================================================
# WHAT TO LOOK AT in curl/02_tools_list.sh
# ============================================================
#
# 1. `ttlMs: 300000` and `cacheScope: "public"` on the result. Compare with topic
#    01, which had ttlMs: 0 / cacheScope: "private".
#
# 2. `list_drinks` comes before `get_drink`, matching registration order. Reorder
#    the two functions in this file, restart, and watch the wire order follow.
#
# 3. `get_drink`'s inputSchema. The `slug` property has a `description` — that came
#    from `Annotated[str, Field(description=...)]`, not from the docstring.
#
# 4. `list_drinks` has an inputSchema with NO properties. A no-argument tool still
#    publishes a schema; it is just an empty object.
#
# 5. Both outputSchemas. `MenuResult` became a real nested schema including the
#    full `Drink` definition under `$defs`. That is what returning a pydantic model
#    buys you over returning a dict.
# ============================================================
