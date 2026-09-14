#!/usr/bin/env bash
# resources/list — the STATIC resources only.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'TWO entries: cafe://menu and cafe://menu/dairy-free. Each has a `uri`, a
        `name`, a `title` and a `mimeType`, and its `description` is the Python
        docstring — same rule as tools.

        cafe://drinks/{slug} is NOT here. Templates live in a different RPC; see
        04_templates_list.sh. A client that only calls resources/list will never
        learn the template exists.

        ttlMs: 600000, cacheScope: "public" — ten minutes, shared-cacheable.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: resources/list' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 201, "method": "resources/list", "params": {
$(cafe_meta)
}}
JSON
)" | pp
