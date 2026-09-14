#!/usr/bin/env bash
# ROUND 2: the retry, with THE SAME order token plus inputResponses + requestState.
#   bash curl/08_place_round2.sh <order token> <requestState>
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 08_place_round2.sh <order token> <requestState>}"
STATE="${2:?usage: 08_place_round2.sh <order token> <requestState>}"

expect 'resultType: "complete". A ticket, the name you gave, the priced lines,
        and the total. Note the NEW JSON-RPC id (801, not 800) — MRTR retries
        are a fresh request, not a continuation of the old one; only
        requestState and the unchanged arguments carry the connection.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: place_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 801, "method": "tools/call", "params": {
  "name": "place_order",
  "arguments": {"order": "${ORDER}"},
  "inputResponses": {"confirm": {"action": "accept", "content": {"name": "Sanjoy", "confirm": true}}},
  "requestState": "${STATE}",
$(cafe_meta)
}}
JSON
)" | pp
