#!/usr/bin/env bash
# server/discover — the replacement for the discovery half of `initialize`.
#
# This is the ONE method a server MUST implement. A client may call it before
# anything else to pick a protocol version up front. It is optional for the
# client but mandatory for the server, which is the opposite of how `initialize`
# worked: that one was mandatory for both, every connection, before any work.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "POST server/discover"
expect 'resultType: "complete", supportedVersions: ["2026-07-28"], a capabilities
        object listing tools/resources/prompts, the `instructions` string, and
        _meta.serverInfo naming the server. Note ttlMs: 0 / cacheScope: "private" —
        discover results are cacheable in principle but this server offers no TTL.
        There is no "extensions" key: mcp 2.1.1 omits it when empty rather than
        emitting an empty object.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: server/discover' \
  -d "$(cat <<JSON
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "server/discover",
  "params": {
$(cafe_meta)
  }
}
JSON
)" | pp
