# ============================================================
# TOPIC: 13 — gateway headers: Mcp-Param-*, x-mcp-header, non-ASCII
# REF:   notes/13-param-headers.md
# RUN:   python solved/t13_param_headers.py
# ============================================================
#
# Every script since topic 01 has sent `Mcp-Method` and, for the three
# name-bearing methods, `Mcp-Name` — headers that mirror something from the
# JSON-RPC body so a gateway can route or rate-limit on it without parsing
# JSON. This topic is where an ARGUMENT gets that same treatment: any tool
# parameter you mark with `x-mcp-header` is mirrored into its own
# `Mcp-Param-<Token>` header, and the SDK enforces that the header and the
# body agree.
#
# The café's one non-ASCII drink is what makes this topic concrete rather
# than abstract: an HTTP header cannot carry raw non-ASCII bytes, so
# "Crème Brûlée Latte" has to travel through a base64 sentinel, and you get
# to watch it happen rather than take it on faith.

# --- Imports ---
import os
import sys
from typing import Annotated

from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))

mcp = MCPServer(
    name="cafe-mcp",
    version="0.13.0",
    instructions=(
        "You are working the counter of a small coffee shop. Call `announce_drink` "
        "with a drink's exact display NAME (not its slug) to have it announced at "
        "the counter."
    ),
    cache_hints={"tools/list": CacheHint(ttl_ms=300_000, scope="public")},
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Announce a drink at the counter",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def announce_drink(
    # x-mcp-header's VALUE is the token a gateway will see as
    # `Mcp-Param-<token>` — a string, not True. Get this wrong (topic 03's
    # sibling: a wrong-typed schema fails SILENTLY, see notes/13) and the
    # whole mechanism quietly stops engaging, with no error anywhere.
    name: Annotated[
        str,
        Field(
            description="The drink's exact display name, e.g. 'Latte' or 'Crème Brûlée Latte'.",
            json_schema_extra={"x-mcp-header": "DrinkName"},
        ),
    ],
) -> str:
    """Announce a drink by its display name at the counter.

    Use the drink's exact display NAME here, not its slug — 'Crème Brûlée
    Latte', not 'creme-brulee-latte'. A gateway in front of this server can
    read which drink is being announced from the `Mcp-Param-DrinkName` header
    alone, without parsing this call's JSON body.
    """
    match = next((drink for drink in menu.all_drinks() if drink.name == name), None)
    if match is None:
        names = ", ".join(f"'{drink.name}'" for drink in menu.all_drinks())
        raise ToolError(f"No drink is named {name!r}. Valid names are: {names}.")

    print(f"  [server] announcing: {match.name}", file=sys.stderr)
    return f"Now serving: {match.name}!"


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "13"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 13 — gateway headers")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68)
    print("  Try:")
    print("    bash curl/13_tools_list_schema.sh   <- see x-mcp-header published")
    print("    bash curl/13_announce.sh 'Latte'")
    print("    bash curl/13_announce.sh 'Crème Brûlée Latte'   <- needs no escaping")
    print("    bash curl/13_mismatched_param.sh                <- -32020, blocked")
    print("    bash curl/13_missing_param.sh                   <- -32020, blocked")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
