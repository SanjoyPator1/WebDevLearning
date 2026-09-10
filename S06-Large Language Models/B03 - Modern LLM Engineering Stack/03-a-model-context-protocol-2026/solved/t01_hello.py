# ============================================================
# TOPIC: 01 — Your first MCP server, and server/discover
# REF:   notes/01-first-server-and-discover.md
# RUN:   python solved/t01_hello.py
# ============================================================
#
# This file is deliberately the smallest thing that is a real MCP server. There is
# no café here yet — one tool, one health route, and nothing else. The point of
# topic 01 is not what the server contains, it is what you do to it with curl.
#
# NOTE ON PRINTING: this server prints its banner to stdout because you are
# reading it in a terminal. In a real stdio-transport server that would corrupt
# the protocol stream — stdout IS the channel there. Log to stderr in anything
# you ship. See SETUP.md.

# --- Imports ---
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
# `MCPServer` is the high-level SDK server. `name` is what the server reports as
# its identity in every result's `_meta`, under the key
# `io.modelcontextprotocol/serverInfo`. There is no handshake in which to announce
# it once, so it goes out on every single reply.
#
# `instructions` is free text handed to the model by clients that ask for it. Write
# it for a model, not for a human reading docs.
mcp = MCPServer(
    name="cafe-hello",
    version="0.1.0",
    instructions=(
        "A throwaway server used to demonstrate MCP request framing. "
        "It has exactly one tool, `hello`, which echoes a greeting."
    ),
)


# --- Core implementation: one tool ---
# The decorator does four things you should be able to name:
#   1. registers the function so it appears in `tools/list`
#   2. turns the type hints into the tool's `inputSchema` (a JSON Schema)
#   3. turns the return hint into its `outputSchema`
#   4. uses the docstring as the tool's `description` — the text the MODEL reads
#
# So the docstring is not documentation. It is prompt engineering. Write it to
# tell a model WHEN to reach for this tool, not just what its arguments mean.
@mcp.tool(
    annotations=ToolAnnotations(
        title="Say hello",
        # These four hints are promises to the client about behaviour. They are
        # advisory — the protocol does not enforce them — but hosts use them to
        # decide what needs a permission prompt. Topic 02 covers them properly.
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def hello(name: str) -> str:
    """Greet someone by name.

    Use this only to check that the connection to this server works. It has no
    other purpose and touches nothing.

    Args:
        name: the name to greet.
    """
    print(f"  [server] hello() called with name={name!r}", file=sys.stderr)
    return f"Hello, {name}! You are talking to an MCP server."


# --- A plain HTTP route that is not MCP at all ---
# `ping` was REMOVED in the 2026-07-28 revision, so there is no protocol-level
# liveness check any more. Health checks go to an ordinary route like this one.
# `custom_route` mounts it on the same Starlette app as /mcp.
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. Not an MCP method — deliberately."""
    return JSONResponse({"status": "ok", "server": "cafe-hello"})


# --- Test / dry-run: run it ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 01 — first MCP server")
    print("-" * 68)
    print("  transport        : streamable-http")
    print(f"  endpoint         : http://{HOST}:{PORT}/mcp")
    print(f"  health           : http://{HOST}:{PORT}/healthz")
    print(f"  protocol version : {PROTOCOL_VERSION}")
    print("  stateless_http   : True   <-- NOT the default. See below.")
    print("-" * 68)
    print("  Try these, in another terminal:")
    print("    bash curl/01_discover.sh")
    print("    bash curl/01_tools_list.sh")
    print("    bash curl/01_call_hello.sh")
    print("    bash curl/01_no_version_header.sh   <-- the interesting one")
    print("    bash curl/01_healthz.sh")
    print("-" * 68)
    print("  Ctrl-C to stop.")
    print("-" * 68, flush=True)

    # THE MOST IMPORTANT ARGUMENT IN THIS FILE:
    #
    #   stateless_http=True
    #
    # It is NOT the default in mcp 2.1.1 — `stateless_http` defaults to False.
    # Leave it off and the SDK keeps the legacy session machinery alive: a client
    # that sends no `Mcp-Protocol-Version` header falls into the pre-2026 code
    # path and gets `Bad Request: Missing session ID`, which is a baffling error
    # to debug because the client did nothing wrong.
    #
    # Setting it True is what makes this process interchangeable with any other
    # copy of itself. Topic 14 proves that by putting three of them behind a
    # round-robin proxy.
    mcp.run(
        transport="streamable-http",
        host=HOST,
        port=PORT,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()


# ============================================================
# WHAT TO LOOK AT
# ============================================================
#
# 1. server/discover  — the replacement for the discovery half of `initialize`.
#    Look for `supportedVersions`, `capabilities`, and `resultType: "complete"`.
#
# 2. tools/list  — note that `hello`'s docstring became `description`, and the
#    `name: str` hint became an `inputSchema` with a required string property.
#
# 3. Every result's `_meta` carries `io.modelcontextprotocol/serverInfo`. On every
#    reply, not once per connection. That is what "no handshake" costs you.
#
# 4. 01_no_version_header.sh sends a POST with no `MCP-Protocol-Version` header.
#    Compare its response framing to 01_tools_list.sh. The headers you send
#    decide whether you get a plain JSON body or an SSE-framed one.
# ============================================================
