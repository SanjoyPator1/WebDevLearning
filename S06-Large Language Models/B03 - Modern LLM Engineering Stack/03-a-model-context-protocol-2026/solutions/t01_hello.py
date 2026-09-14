# ============================================================
# TOPIC: 01 — Your first MCP server, and server/discover
# REF:   notes/01-first-server-and-discover.md
# RUN:   python solutions/t01_hello.py
# ============================================================
#
# YOUR TURN. Read notes/01-first-server-and-discover.md first, then fill in the
# TODOs below. There are five of them and none needs more than three lines.
#
# When it runs, prove it from the outside:
#     bash curl/01_discover.sh
#     bash curl/01_tools_list.sh
#     bash curl/01_call_hello.sh
#     bash curl/01_no_version_header.sh
#     bash curl/01_healthz.sh
#
# Compare with solved/t01_hello.py when you are done, not before.

# --- Imports ---
from os import read
import os
import sys

from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))
PROTOCOL_VERSION = "2026-07-28"


# --- The server object ---
# TODO 1: Create the server.
#   Build an `MCPServer` with a `name`, a `version`, and an `instructions` string.
#   Remember what each one is for:
#     name         -> goes out in EVERY result's _meta as serverInfo, because
#                     there is no handshake to announce it once.
#     instructions -> free text handed to the MODEL. Write it for a model.
mcp = MCPServer(
    name="cafe-hello",
    version="0.1.0",
    instructions="a simple hello mcp server. It has exactly one tool hello which ecoes greeting"
)


# --- Core implementation: one tool ---
# TODO 2: Annotate the tool.
#   Give `@mcp.tool()` an `annotations=ToolAnnotations(...)` with a `title` and the
#   four behaviour hints. `hello` reads nothing and changes nothing — so which of
#   read_only_hint / destructive_hint / idempotent_hint / open_world_hint are True?
@mcp.tool(
    annotations=ToolAnnotations(
        title="Say hello",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False
    )
)  # replace
def hello(name: str) -> str:
    # TODO 3: write this docstring.

    # It becomes the tool's `description` — the text the MODEL reads to decide
    # whether to call this tool. So write it as an instruction to a model, not as
    # documentation for a human. Say WHEN to use it, not only what it does.

    # Args:
    #     name: ...
    """
    Greet someone by name.

    Use this only to check that the connection to this server works. It has no
    other purpose and touches nothing.

    Args:
        name: the name to greet.
    """
    print(f"  [server] hello() called with name={name!r}", file=sys.stderr)
    return f"Hello, {name}! You are talking to an MCP server."


# --- A plain HTTP route that is not MCP at all ---
# TODO 4: Add a health route.
#   `ping` was REMOVED at 2026-07-28, so liveness needs an ordinary HTTP route.
#   Decorate with `@mcp.custom_route(path, methods=[...])` and return a
#   `JSONResponse`.
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. Not an MCP method — deliberately."""
    return JSONResponse({"status": "ok", "server": "cafe-hello"})


# --- Test / dry-run: run it ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 01 — first MCP server (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print(f"  health   : http://{HOST}:{PORT}/healthz")
    print("-" * 68, flush=True)

    # TODO 5: Run it.
    #   Use `mcp.run(...)` with the streamable-http transport, this HOST and PORT.
    #   There is one more keyword argument, and getting it wrong is the single most
    #   common mistake in a 2026-era MCP server. The notes tell you which one and
    #   why it is not the default. When you think you have it, run
    #   `bash curl/01_no_version_header.sh` — if you see
    #   "Bad Request: Missing session ID", you left it out.
    mcp.run(
        transport="streamable-http",
        host=HOST,
        port=PORT,
        stateless_http=True
    )


if __name__ == "__main__":
    main()
