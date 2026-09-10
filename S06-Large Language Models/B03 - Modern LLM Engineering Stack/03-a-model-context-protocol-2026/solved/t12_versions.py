# ============================================================
# TOPIC: 12 — version negotiation with no handshake to negotiate in
# REF:   notes/12-versions.md
# RUN:   python solved/t12_versions.py
# ============================================================
#
# Every request in this folder has carried an MCP-Protocol-Version header and a
# matching _meta.protocolVersion, and every one of them has said "2026-07-28".
# This topic is about what happens on the OTHER paths through that check: a
# version the server has never heard of, a version it knows but is not the
# modern one, and the method (`server/discover`) that turns out to only exist
# for callers who already declared the modern version — a small irony worth
# seeing directly rather than assuming discovery always comes first.
#
# There is no handshake left to negotiate a version during. Every one of the
# ten methods carries its own version claim, on every single call, and the
# server decides per-request which era's rules to apply.

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


@mcp.tool()
async def whoami(ctx: Context) -> str:
    """Report which protocol version THIS call declared.

    Call this with different MCP-Protocol-Version headers (and a matching
    _meta.protocolVersion) to see the answer change per-request — there is no
    session remembering a version from an earlier call, because there are no
    sessions at all.
    """
    return f"This request declared protocol version: {ctx.protocol_version!r}"


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "12"})


def main() -> None:
    print("-" * 68)
    print("TOPIC 12 — version negotiation with no handshake")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68)
    print("  Try:")
    print("    bash curl/12_discover.sh")
    print("    bash curl/12_whoami.sh 2026-07-28")
    print("    bash curl/12_whoami.sh 2025-06-18   <- an OLD but KNOWN version")
    print("    bash curl/12_unknown_version.sh     <- -32022, with the recovery list")
    print("    bash curl/12_discover_wrong_era.sh  <- discover itself needs 2026-07-28")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()
