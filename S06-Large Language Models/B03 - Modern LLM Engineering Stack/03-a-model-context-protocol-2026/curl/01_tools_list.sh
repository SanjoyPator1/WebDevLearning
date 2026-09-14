#!/usr/bin/env bash
# tools/list — what the model gets to see.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "POST tools/list"
expect 'one tool named "hello"; its `description` is the Python docstring; its
        `inputSchema` is a JSON Schema derived from the type hints; `annotations`
        carries the four behaviour hints. Also `ttlMs` and `cacheScope` — both
        required on list results as of 2026-07-28.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/list' \
  -d "$(cat <<JSON
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {
$(cafe_meta)
  }
}
JSON
)" | pp
