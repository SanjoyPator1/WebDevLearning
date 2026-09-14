#!/usr/bin/env bash
# ROUND 2 with action: "decline" — a NORMAL, successful outcome, not an error.
#   bash curl/08_decline.sh <order token> <requestState>
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 08_decline.sh <order token> <requestState>}"
STATE="${2:?usage: 08_decline.sh <order token> <requestState>}"

expect 'resultType: "complete", isError: false, and {"placed": false, "reason":
        "customer declined"}. Declining is not a failure of the protocol or the
        tool — it is the customer saying no, which the tool handled perfectly.
        Never treat action != "accept" as an error path.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: place_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 802, "method": "tools/call", "params": {
  "name": "place_order",
  "arguments": {"order": "${ORDER}"},
  "inputResponses": {"confirm": {"action": "decline"}},
  "requestState": "${STATE}",
$(cafe_meta)
}}
JSON
)" | pp
