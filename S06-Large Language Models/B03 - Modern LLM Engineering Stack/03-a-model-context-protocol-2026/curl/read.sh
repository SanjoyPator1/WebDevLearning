#!/usr/bin/env bash
# Generic resources/read.
#
#   bash curl/read.sh cafe://menu
#   bash curl/read.sh cafe://drinks/flat-white
#
# Note the `Mcp-Name` header carries the URI. `resources/read` is one of the three
# name-bearing methods, and for this one the mirrored value is `params.uri`, not
# `params.name`:
#     tools/call     -> params.name
#     prompts/get    -> params.name
#     resources/read -> params.uri
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
URI="${1:?usage: read.sh <uri>}"
ID="${2:-200}"

banner "POST resources/read  ->  ${URI}"

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: resources/read' \
  -H "Mcp-Name: ${URI}" \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": ${ID}, "method": "resources/read", "params": {
  "uri": "${URI}",
$(cafe_meta)
}}
JSON
)" | pp
