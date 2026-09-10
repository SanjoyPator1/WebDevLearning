# ============================================================
# THE PROJECT — every topic, one server
# REF:   notes/15-the-project.md
# RUN:   python solved/cafe_project.py
# ============================================================
#
# Fourteen topics each built one server to demonstrate one idea in isolation.
# This file builds NONE of that logic again. It imports the actual functions
# topics 03-13 already wrote, tested, and proved correct, and registers them
# onto one fresh `MCPServer` — the same technique
# `tests/test_wire_load_balancer.py` and `tests/test_wire_subscriptions.py`
# already used to build a second, independent instance out of one topic's
# tools. Here it is used on purpose, across nine different topics, to build
# the one café a real client would actually talk to.
#
# The three MCP decorators (`@mcp.tool`, `@mcp.resource`, `@mcp.prompt`) are
# decorator FACTORIES — `mcp.tool(...)` returns a decorator, and calling that
# decorator on an already-defined function registers it and hands the same
# function back unchanged. Nothing stops you from calling a DIFFERENT
# server's factory on a function some other module already decorated once.
# That is the whole mechanism below: no new tool logic, only new wiring.
#
# What you get by combining them for real, rather than imagining it: a
# coherent flow. `add_to_order` (07) mints a token; `place_order` (08) reads
# it, asks for confirmation, and returns a NEW committed order; `brew` (10)
# takes that same signed cart shape and reports progress while it works. All
# three read and write the identical token format (`cafe_mcp.orders`),
# because all three always did — this file is the first place you actually
# hand one tool's output to the next.

# --- Imports ---
import os

import t03_calls_and_errors
import t04_resources
import t05_prompts
import t06_pagination
import t07_order_token
import t08_mrtr
import t10_progress
import t11_subscriptions
import t13_param_headers
from mcp.server import CacheHint, MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))

mcp = MCPServer(
    name="cafe-mcp",
    version="1.0.0",
    instructions=(
        "You are working the counter of a small coffee shop, the same one every "
        "earlier topic in this course built one piece of at a time.\n\n"
        "Read `cafe://menu` first — it has every drink, its slug, and whether it "
        "is sold out right now. `list_drinks` gives the same information, "
        "paginated, for a client that cannot read resources.\n\n"
        "To place a real order: call `add_to_order` once per drink (omit `order` "
        "on the first call, pass back the token you get on every call after "
        "that). When the cart is complete, call `place_order` with that same "
        "token — it will ask you to confirm a total and a name for the cup "
        "before committing. Once placed, call `brew` with the SAME token to "
        "brew it, watching progress as it works.\n\n"
        "Staff use `sell_out` / `un_sell_out` to change what is available; "
        "subscribe to `cafe://menu` via `subscriptions/listen` to be told the "
        "moment that happens instead of re-reading it."
    ),
    cache_hints={
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        "resources/read": CacheHint(ttl_ms=5_000, scope="public"),
    },
)

# --- Resources (04): re-registered, not reimplemented ---
mcp.resource("cafe://menu", name="menu", title="The café menu", mime_type="text/markdown")(
    t04_resources.menu_document
)
mcp.resource(
    "cafe://drinks/{slug}",
    name="drink_detail",
    title="One drink, in full",
    mime_type="application/json",
)(t04_resources.drink_document)

# --- Prompt (05) ---
mcp.prompt(name="order_for_me", title="Order something for me")(t05_prompts.order_for_me)

# --- Tools, one per topic that introduced them ---
# `add_tool`/`mcp.tool()(...)` re-registers each function under THIS server
# fresh, so annotations set on the ORIGINAL @mcp.tool(...) call in each
# topic's own file do not carry over automatically — that metadata belongs to
# the decorator call, not the function object. Re-declaring it here for nine
# tools would be pure repetition of what topics 03-13 already show in full;
# this file's subject is the wiring, not the annotations a second time.
mcp.tool()(t03_calls_and_errors.get_drink)
mcp.tool()(t06_pagination.list_drinks)
mcp.tool()(t07_order_token.add_to_order)
mcp.tool()(t07_order_token.view_order)
mcp.tool()(t08_mrtr.place_order)
mcp.tool()(t10_progress.brew)
mcp.tool()(t11_subscriptions.sell_out)
mcp.tool()(t11_subscriptions.un_sell_out)
mcp.tool()(t13_param_headers.announce_drink)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "project"})


def main() -> None:
    print("-" * 68)
    print("THE PROJECT — every topic, one server")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68)
    print("  Try:")
    print("    python solved/raw_client.py")
    print("    python solved/sdk_client.py")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
