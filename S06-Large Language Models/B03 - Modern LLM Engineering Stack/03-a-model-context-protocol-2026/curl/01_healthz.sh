#!/usr/bin/env bash
# /healthz — a plain GET, not MCP at all.
#
# `ping` was REMOVED at 2026-07-28. There is no protocol-level liveness check any
# more, so every server in this folder mounts its own ordinary HTTP route.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "GET /healthz"
expect '{"status": "ok", ...} — and note this needed no MCP headers, no _meta,
        and no JSON-RPC envelope, because it is not an MCP request.'

curl -sS "http://${CAFE_HOST}:${CAFE_PORT}/healthz" | pp
