# ============================================================
# TOPIC: 04 — resources and resource templates
# REF:   notes/04-resources.md
# RUN:   python solutions/t04_resources.py
# ============================================================
#
# YOUR TURN. Six TODOs.
#
# Before you write anything, answer this in your head: the café's menu is already
# available as a TOOL (`list_drinks`). Why expose the same data as a RESOURCE too?
# If the answer is not about WHO DECIDES, re-read the first section of notes/04.
#
# `cafe_mcp/render.py` is given to you complete — it is string formatting, not a
# lesson. What you are writing is the layer that publishes those documents by URI.
#
# Prove it from outside:
#     bash curl/04_resources_list.sh
#     bash curl/04_templates_list.sh      <- note it is a DIFFERENT rpc
#     bash curl/04_read_menu.sh
#     bash curl/04_read_drink.sh flat-white
#     bash curl/04_read_drink.sh no-such-drink
#     bash curl/04_tool_vs_resource.sh    <- the one that matters

# --- Imports ---
import os
import sys

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp_types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu, render

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))


# --- The server ---
# TODO 1: Extend the cache hints to cover resources.
#
#   There are exactly six cacheable methods at 2026-07-28. Find out which, from the
#   SDK rather than from me:
#       python -c "from mcp_types.methods import CACHEABLE_METHODS as C; print(sorted(C))"
#
#   Then add hints for the three resource ones. Ten minutes is reasonable for a menu.
#
#   Note which methods are NOT in that list, and be able to say why. (Hint: what
#   would it mean to cache a `tools/call`?)
#
#   `resources/read` is the highest-value hint on this whole server. Why?
mcp = MCPServer(
    name="cafe-mcp",
    version="0.4.0",
    instructions=(
        # TODO 2: Tell the model the resources exist and when to prefer them.
        #   A model will not read `cafe://menu` unless something suggests it. Say
        #   which URI to read at the start of a conversation, and when to reach for
        #   the dairy-free one instead of the full menu.
        "..."
    ),
    cache_hints={
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        # TODO 1 continues here.
    },
)


# --- Static resources ---
# TODO 3: Publish two static resources.
#
#   cafe://menu             -> render.menu_markdown(),      mime "text/markdown"
#   cafe://menu/dairy-free  -> render.dairy_free_markdown(), mime "text/markdown"
#
#   `@mcp.resource(uri, name=..., title=..., mime_type=...)`. A URI with no
#   {placeholder} is a static resource.
#
#   The docstring is published as the resource's `description`, exactly as with
#   tools — so it is prompt text again. Write it to answer "when should this be
#   attached to my context?"
def menu_document() -> str:
    """TODO: write this for a model to read."""
    print("  [server] read cafe://menu", file=sys.stderr)
    return render.menu_markdown()


def dairy_free_document() -> str:
    """TODO: write this for a model to read."""
    print("  [server] read cafe://menu/dairy-free", file=sys.stderr)
    return render.dairy_free_markdown()


# --- A resource TEMPLATE ---
# TODO 4: Publish a template.
#
#   URI: cafe://drinks/{slug}, mime "application/json".
#
#   The {placeholder} becomes a function parameter — reading
#   `cafe://drinks/latte` calls this with slug="latte".
#
#   After it works, run BOTH 04_resources_list.sh and 04_templates_list.sh and note
#   which one it appears in, and what key holds the URI. That difference catches
#   people writing clients.
def drink_document(slug: str) -> str:
    """TODO: write this for a model to read. Mention the slug format."""
    print(f"  [server] read cafe://drinks/{slug}", file=sys.stderr)
    try:
        return render.drink_json(slug)
    except KeyError:
        # TODO 5: Report the failure correctly.
        #
        #   `render.drink_json` raises KeyError for an unknown slug. Convert it.
        #
        #   Which exception? You have three candidates and they behave differently
        #   on the wire — go and check, do not guess:
        #     - a bare exception          -> ?
        #     - ResourceError             -> ?
        #     - ResourceNotFoundError     -> ?
        #
        #   Then answer the harder question: `get_drink` below raises ToolError for
        #   exactly the same missing drink. Why is that the RIGHT answer there and
        #   the WRONG answer here? Write your reasoning as a comment. If you can
        #   write it, you understand topic 03 and 04 together.
        # (`from None` suppresses the KeyError as the cause — the client does not
        #  need our internal plumbing in its traceback.)
        raise NotImplementedError from None  # replace


# --- One tool, kept for contrast ---
@mcp.tool(
    annotations=ToolAnnotations(
        title="Get one drink",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def get_drink(slug: str) -> menu.Drink:
    """Look up one drink by slug.

    Prefer reading the resource `cafe://drinks/<slug>` if your client supports
    resources. This tool exists for clients that only support tools.
    """
    drink = menu.find(slug)
    print(f"  [server] get_drink({slug!r})", file=sys.stderr)
    if drink is None:
        raise ToolError(f"There is no drink with slug {slug!r}. Call `list_drinks` first.")
    return drink


# --- Health ---
# TODO 6: /healthz again. You know this one.
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "04"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 04 — resources (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
