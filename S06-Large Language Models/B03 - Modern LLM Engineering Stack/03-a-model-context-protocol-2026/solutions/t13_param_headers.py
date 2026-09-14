# ============================================================
# TOPIC: 13 — gateway headers: Mcp-Param-*, x-mcp-header, non-ASCII
# REF:   notes/13-param-headers.md
# RUN:   python solutions/t13_param_headers.py
# ============================================================
#
# YOUR TURN. Three TODOs. This topic needs no new cafe_mcp module — it is
# entirely about the wire, using the menu you already have.
#
# Prove it from outside:
#     bash curl/13_tools_list_schema.sh
#     bash curl/13_announce.sh 'Latte'
#     bash curl/13_announce.sh 'Crème Brûlée Latte'
#     bash curl/13_mismatched_param.sh
#     bash curl/13_missing_param.sh

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


# TODO 1: Annotate `name` to mark it for header mirroring.
#
#   `Annotated[str, Field(description=..., json_schema_extra={"x-mcp-header": "DrinkName"})]`
#
#   The VALUE — "DrinkName" — is the token a gateway will see mirrored as
#   `Mcp-Param-DrinkName`. This is a STRING, never `True`. Get this wrong and
#   nothing errors anywhere — the mechanism just silently stops engaging for
#   this parameter. Verify what you wrote actually took effect by checking the
#   published schema yourself:
#       bash curl/13_tools_list_schema.sh
#   and confirming `"x-mcp-header": "DrinkName"` (a string) actually appears.
#
#   Annotations: read-only, not destructive, idempotent — announcing a drink
#   twice changes nothing further.
@mcp.tool()  # replace with annotations
def announce_drink(name: str) -> str:
    """TODO: write this. Tell the model to use the drink's DISPLAY NAME, not
    its slug — that distinction is what makes the non-ASCII example matter."""
    # TODO 2: Find the drink by NAME (not slug — menu.find looks up by slug).
    #   Iterate menu.all_drinks() and match on .name. Raise ToolError if no
    #   drink has that exact name, listing the valid names in the message.
    raise NotImplementedError  # replace


# --- Health ---
# TODO 3: /healthz again.
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "13"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 13 — gateway headers (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
