# ============================================================
# TOPIC: 12 — version negotiation with no handshake to negotiate in
# REF:   notes/12-versions.md
# RUN:   python solutions/t12_versions.py
# ============================================================
#
# YOUR TURN. Two TODOs — this is the shortest server in the whole folder,
# because the point is entirely in what you send it, not in what it does.
#
# Prove it from outside:
#     bash curl/12_discover.sh
#     bash curl/12_whoami.sh 2026-07-28
#     bash curl/12_whoami.sh 2025-06-18       <- an OLD but KNOWN version
#     bash curl/12_unknown_version.sh          <- -32022, with a recovery list
#     bash curl/12_discover_wrong_era.sh       <- discover itself needs 2026-07-28

# --- Imports ---
import os

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from starlette.requests import Request
from starlette.responses import JSONResponse

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))

mcp = MCPServer(
    name="cafe-mcp",
    version="0.12.0",
    instructions=(
        "A demo server for version negotiation. Call `whoami` with different "
        "MCP-Protocol-Version headers and watch the answer change."
    ),
)


# TODO 1: Write whoami(ctx) -> str.
#
#   ONE line of real logic: read `ctx.protocol_version` and put it in the
#   returned string. This is the property that lets a tool see, from the
#   INSIDE, which era's rules the CURRENT call is running under — no session,
#   no state, just this one request's own declared version.
#
#   Before writing it, predict: call this tool four times, with headers
#   2026-07-28, 2025-11-25, 2025-06-18, and 2024-11-05 in turn (four SEPARATE
#   requests, no session between them). Will any of the four fail? Which ones,
#   if any, and why?
@mcp.tool()
async def whoami(ctx: Context) -> str:
    """Report which protocol version THIS call declared."""
    raise NotImplementedError  # replace


# --- Health ---
# TODO 2: /healthz again. You know this one by now.
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "12"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 12 — version negotiation (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()


# TODO 3 (no code — an experiment): before running curl/12_discover_wrong_era.sh,
#   predict the error code. Is it -32022 (the "unknown version" error you just
#   saw in 12_unknown_version.sh), or something else? 2025-06-18 is a real,
#   fully-working version for whoami — does that mean it works for EVERY
#   method on this server? Run the script and check your answer.
