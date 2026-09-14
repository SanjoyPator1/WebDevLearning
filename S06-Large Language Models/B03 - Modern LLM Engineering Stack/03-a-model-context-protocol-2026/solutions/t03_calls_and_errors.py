# ============================================================
# TOPIC: 03 — tools/call: arguments, structured output, failure
# REF:   notes/03-tools-call.md
# RUN:   python solutions/t03_calls_and_errors.py
# ============================================================
#
# YOUR TURN. The subject is FAILURE, and there are three kinds. Before you write
# anything, be able to say which kind each of these is:
#
#   size="XL"                      ->  ?
#   size="L" for an espresso       ->  ?
#   a KeyError from your own bug    ->  ?
#
# If all three feel the same, re-read notes/03-tools-call.md. The whole exercise is
# that they must be handled differently.
#
# Prove it from outside, IN THIS ORDER — the comparison is the lesson:
#     bash curl/03_quote_ok.sh
#     bash curl/03_quote_bad_size.sh
#     bash curl/03_quote_bad_enum.sh
#     bash curl/03_quote_bad_qty.sh
#     bash curl/03_broken.sh          <- then look at your SERVER terminal
#     bash curl/03_unknown_tool.sh

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


# TODO 1: Define QuoteResult.
#   Fields: slug, name, size, qty, unit_price, total, caffeine_mg_total.
#   Field(description=...) on the ones a model could misread — what is `total`
#   versus `unit_price`? Remember the class docstring goes to the model too.
class QuoteResult(BaseModel):
    pass  # TODO 1: replace with the fields described above


# --- The server ---
mcp = MCPServer(
    name="cafe-mcp",
    version="0.3.0",
    instructions=(
        # TODO 2: Extend topic 02's instructions to mention `quote`, and to tell the
        # model that quote will name the available sizes if it picks a wrong one.
        # That one sentence turns a dead end into a one-step recovery.
        "..."
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
    that actually exist.
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
                "`list_drinks`. Not the display name."
            )
        ),
    ],
) -> DrinkResult:
    """Look up the detail of a single drink by its slug.

    If you do not already know the exact slug, call `list_drinks` first rather
    than guessing.
    """
    drink = menu.find(slug)
    print(f"  [server] get_drink({slug!r}) -> {'found' if drink else 'MISSING'}", file=sys.stderr)

    if drink is None:
        # TODO 3: Replace the topic-02 ValueError with a ToolError.
        #   The message is the exercise, not the exception type. Write one that a
        #   model could ACT on. Three tests it must pass:
        #     - does it name what went wrong?
        #     - does it quote the offending value?
        #     - does it say what to do next?
        #   "invalid slug" fails all three.
        raise ValueError(f"no such drink: {slug}")  # replace

    return DrinkResult(drink=drink, available_sizes=list(menu.sizes_for(slug)))


# TODO 4: Write `quote`.
#
#   Signature: quote(slug: str, size: ..., qty: int = 1) -> QuoteResult
#
#   The interesting decision is WHERE each rule lives.
#
#   (a) `size` must be one of S, M, L. That set is FIXED and known at import time,
#       so push it into the SCHEMA — type it `Literal["S", "M", "L"]` and it becomes
#       a JSON Schema `enum`. The model then reads the legal values in tools/list
#       instead of discovering them by failing, and a bad value never reaches your
#       function.
#
#   (b) `qty` must be 1..MAX_QTY. Also fixed -> also the schema. Field(ge=..., le=...)
#       becomes minimum/maximum.
#
#   (c) Whether THIS drink is sold in THAT size depends on menu data. The schema
#       cannot know it. So this one is a runtime check that raises ToolError — and
#       the message should list the sizes that ARE available, so the model can fix
#       itself in one step.
#
#   Then compute unit_price, total (round to 2dp) and caffeine_mg_total.
#
#   Annotations: read_only_hint=True — pricing changes nothing.
@mcp.tool()  # replace
def quote() -> "QuoteResult":  # replace the signature
    """TODO: write this for a model to read."""
    ...  # replace


# TODO 5: A tool that fails badly, deliberately, so you can see the difference.
#
#   Write `broken_on_purpose(slug: str) -> str` that raises a plain
#   `KeyError(f"{slug} not in /var/lib/cafe/internal-menu-cache.sqlite")`.
#
#   Then run `bash curl/03_broken.sh` and answer two questions:
#     1. What does the MODEL receive?
#     2. Where did the KeyError message go? (Look at your server terminal.)
#
#   Never ship a tool like this. Write it once so you recognise the symptom.


# --- Health ---
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "03"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 03 — tools/call and failure (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
