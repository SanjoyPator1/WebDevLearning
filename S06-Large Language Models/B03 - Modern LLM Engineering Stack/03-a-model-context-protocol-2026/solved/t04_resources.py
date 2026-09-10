# ============================================================
# TOPIC: 04 — resources and resource templates
# REF:   notes/04-resources.md
# RUN:   python solved/t04_resources.py
# ============================================================
#
# Part 1 was tools: things the MODEL decides to call. This is resources: data the
# HOST or the USER attaches to context, addressed by URI.
#
# The distinction is not technical, it is about control. A tool is an action
# someone chose to make available to a model's judgement. A resource is a document
# someone chose to put in front of it. Same underlying menu, different question
# about who is deciding.
#
# Four things this file demonstrates:
#
#   1. A static resource      -> cafe://menu, cafe://menu/dairy-free
#   2. A resource TEMPLATE    -> cafe://drinks/{slug}
#   3. Cache hints that matter -> a menu document is worth caching properly
#   4. Resource failure is a REAL JSON-RPC error, unlike tool failure
#
# Point 4 is the one worth slowing down for, and notes/04 explains why the two
# rules are opposites rather than an inconsistency.

# --- Imports ---
import os
import sys

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError
from mcp_types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu, render

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))


# --- The server ---
mcp = MCPServer(
    name="cafe-mcp",
    version="0.4.0",
    instructions=(
        "You are working the counter of a small coffee shop.\n\n"
        "Read the resource `cafe://menu` once at the start of a conversation instead "
        "of calling `list_drinks` repeatedly — it is the same information as one "
        "compact markdown table, with the slugs included so you never have to guess "
        "one. Use `cafe://menu/dairy-free` when the customer avoids dairy, and "
        "`cafe://drinks/<slug>` for the full detail of a single drink.\n\n"
        "Sizes are S, M and L, but not every drink is sold in every size — the menu "
        "marks an unavailable size with a dash."
    ),
    # --- CACHE HINTS, now for the methods where they earn their keep ---
    # There are exactly six cacheable methods at 2026-07-28. You can see the list
    # for yourself:
    #     python -c "from mcp_types.methods import CACHEABLE_METHODS as C; print(sorted(C))"
    #     ['prompts/list', 'resources/list', 'resources/read',
    #      'resources/templates/list', 'server/discover', 'tools/list']
    #
    # Note what is NOT there: `tools/call` and `prompts/get`. A tool call may have
    # side effects and a prompt render may depend on arguments, so neither is
    # cacheable by the protocol. Only the *descriptive* surface is.
    #
    # `resources/read` is the interesting one. A resource read is a document
    # fetch — exactly the thing an HTTP cache was invented for — so giving it a
    # real TTL is the single highest-value cache hint on this server.
    cache_hints={
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        "resources/list": CacheHint(ttl_ms=600_000, scope="public"),
        "resources/templates/list": CacheHint(ttl_ms=600_000, scope="public"),
        # Ten minutes. The menu changes when the café changes it, which is not
        # often, and `listChanged` notifications cover the case where it does.
        "resources/read": CacheHint(ttl_ms=600_000, scope="public"),
    },
)


# --- Static resources ---
# `@mcp.resource(uri)` with NO placeholders in the URI registers a static resource.
# It shows up in `resources/list` and is fetched with `resources/read`.
#
# `mime_type` tells the client how to treat the bytes. `text/markdown` is a good
# default for anything a model will read, because models handle markdown structure
# well and a client can also render it for a human.
@mcp.resource(
    "cafe://menu",
    name="menu",
    title="The café menu",
    mime_type="text/markdown",
)
def menu_document() -> str:
    """The full menu as a markdown table: every drink, its slug, its price per
    size, its caffeine content and whether it is dairy-free.

    Read this once at the start of a conversation. It is the same information as
    `list_drinks` but far cheaper to keep in context, and it includes the slugs so
    you never have to guess one.
    """
    print("  [server] read cafe://menu", file=sys.stderr)
    return render.menu_markdown()


@mcp.resource(
    "cafe://menu/dairy-free",
    name="dairy_free_menu",
    title="Dairy-free drinks",
    mime_type="text/markdown",
)
def dairy_free_document() -> str:
    """Only the dairy-free drinks, as a short list with sizes and descriptions.

    Attach this instead of the full menu when the customer avoids dairy — it is a
    quarter of the length and contains nothing you would have to filter out.
    """
    print("  [server] read cafe://menu/dairy-free", file=sys.stderr)
    return render.dairy_free_markdown()


# --- A resource TEMPLATE ---
# A URI with a `{placeholder}` becomes a template. Two consequences:
#
#   1. It appears in `resources/templates/list`, NOT `resources/list`, and carries
#      `uriTemplate` instead of `uri`. Those are two different RPCs and a client
#      that only calls `resources/list` will never see this exist.
#   2. The placeholder becomes a function parameter. `cafe://drinks/latte` calls
#      this with slug="latte".
#
# Templates are how you expose a family of documents without listing thousands of
# them. Twelve drinks would be fine to enumerate; twelve thousand would not.
@mcp.resource(
    "cafe://drinks/{slug}",
    name="drink_detail",
    title="One drink, in full",
    mime_type="application/json",
)
def drink_document(slug: str) -> str:
    """The full record for a single drink as JSON, including `available_sizes`.

    The `{slug}` is a drink slug exactly as it appears in the Slug column of
    `cafe://menu` — lowercase with hyphens, for example `cafe://drinks/flat-white`.
    """
    print(f"  [server] read cafe://drinks/{slug}", file=sys.stderr)
    try:
        return render.drink_json(slug)
    except KeyError:
        # --- THE RULE THAT IS THE OPPOSITE OF TOPIC 03 ---
        #
        # A failing TOOL returns a successful JSON-RPC response with
        # `isError: true`, because the model chose the call and the model must be
        # told so it can choose differently.
        #
        # A failing RESOURCE READ returns a real JSON-RPC ERROR, because the
        # CLIENT chose the URI. The model was not involved and cannot fix it.
        #
        # Same test as topic 03 — "who can fix this?" — pointing the other way.
        # `ResourceNotFoundError` produces `-32602 Invalid params`, which is also
        # a change this revision: it used to be a bespoke `-32002`, and was
        # renumbered on the grounds that a URI that does not exist is a bad
        # argument, not a special condition.
        raise ResourceNotFoundError(
            f"There is no drink with slug {slug!r}. Read `cafe://menu` for the list of valid slugs."
        ) from None


# --- One tool, kept for contrast ---
# Deliberately left in so you can put the two side by side in one `server/discover`
# and ask, for each, who decides to use it.
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
    resources — it returns the same data plus the available sizes, and the result
    is cacheable. This tool exists for clients that only support tools.
    """
    drink = menu.find(slug)
    print(f"  [server] get_drink({slug!r})", file=sys.stderr)
    if drink is None:
        # A TOOL, so ToolError — not ResourceNotFoundError. Same missing drink,
        # different reporting rule, because a different party chose the argument.
        from mcp.server.mcpserver.exceptions import ToolError

        raise ToolError(f"There is no drink with slug {slug!r}. Call `list_drinks` first.")
    return drink


# --- Health ---
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "04"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 04 — resources and resource templates")
    print("-" * 68)
    print(f"  endpoint  : http://{HOST}:{PORT}/mcp")
    print("  resources : cafe://menu, cafe://menu/dairy-free")
    print("  template  : cafe://drinks/{slug}")
    print("  tool      : get_drink  (for contrast — same data, different control)")
    print("-" * 68)
    print("  Try:")
    print("    bash curl/04_resources_list.sh      static ones only")
    print("    bash curl/04_templates_list.sh      a DIFFERENT rpc — note that")
    print("    bash curl/04_read_menu.sh           the document a model would read")
    print("    bash curl/04_read_dairy_free.sh")
    print("    bash curl/04_read_drink.sh flat-white")
    print("    bash curl/04_read_drink.sh no-such-drink   <- a real JSON-RPC error")
    print("    bash curl/04_tool_vs_resource.sh    the two rules, side by side")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
