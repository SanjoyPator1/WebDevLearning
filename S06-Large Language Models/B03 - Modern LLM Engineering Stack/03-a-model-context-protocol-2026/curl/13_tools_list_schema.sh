#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

expect 'inputSchema.properties.name carries "x-mcp-header": "DrinkName" — the
        token a gateway will find mirrored as the Mcp-Param-DrinkName header
        on tools/call. Note the VALUE is a string, "DrinkName", not `true` —
        the whole mechanism silently disengages if you write it as a boolean.
        See notes/13 for exactly what "silently" means here.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/list' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1300, "method": "tools/list", "params": {
$(cafe_meta)
}}
JSON
)" | pp
