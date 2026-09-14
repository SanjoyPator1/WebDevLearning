#!/usr/bin/env bash
# Generic tools/call, for when you just want to poke a tool.
#
#   bash curl/call.sh get_drink '{"slug": "flat-white"}'
#   bash curl/call.sh list_drinks '{}'
#
# Everything here is the same envelope every other script builds by hand; this one
# just parameterises it.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

TOOL="${1:?usage: call.sh <tool-name> [json-arguments]}"
ARGS="${2:-{\}}"
ID="${3:-100}"

banner "POST tools/call  ->  ${TOOL}  ${ARGS}"

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H "Mcp-Name: ${TOOL}" \
  -d "$(cat <<JSON
{
  "jsonrpc": "2.0",
  "id": ${ID},
  "method": "tools/call",
  "params": {
    "name": "${TOOL}",
    "arguments": ${ARGS},
$(cafe_meta)
  }
}
JSON
)" | pp
