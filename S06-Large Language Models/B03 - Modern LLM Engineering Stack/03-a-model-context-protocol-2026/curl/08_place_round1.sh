#!/usr/bin/env bash
# ROUND 1: place_order with no inputResponses yet.
#   bash curl/08_place_round1.sh "$(bash curl/08_get_order_token.sh)"
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 08_place_round1.sh <order token>   (bash curl/08_get_order_token.sh)}"

expect 'resultType: "input_required", NOT "complete". A confirm message with the
        itemised order and total, a requestedSchema asking for name+confirm, and
        a requestState token. COPY THAT requestState for round 2 — and copy the
        ORDER TOKEN too, because round 2 must send the EXACT SAME order argument
        or the retry is refused before your tool code ever runs.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: place_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 800, "method": "tools/call", "params": {
  "name": "place_order",
  "arguments": {"order": "${ORDER}"},
$(cafe_meta)
}}
JSON
)" | pp
