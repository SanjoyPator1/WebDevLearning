#!/usr/bin/env bash
# ROUND 2: retry with THE SAME order token, plus the receipt from the pay page.
#   bash curl/09_pay_round2.sh <order token> <requestState> <receipt>
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 09_pay_round2.sh <order token> <requestState> <receipt>}"
STATE="${2:?usage: 09_pay_round2.sh <order token> <requestState> <receipt>}"
RECEIPT="${3:?usage: 09_pay_round2.sh <order token> <requestState> <receipt>}"

expect 'resultType: "complete", isError: false. A ticket and the paid total.

        Note WHERE the receipt lives: inputResponses.pay.content.receipt — an
        ordinary key in the same `content` object form mode used for its
        answers. URL mode does not get a special result shape; it reuses
        ElicitResult, and content is just wherever your own design decided to
        put the proof.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: pay_for_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 901, "method": "tools/call", "params": {
  "name": "pay_for_order",
  "arguments": {"order": "${ORDER}"},
  "inputResponses": {"pay": {"action": "accept", "content": {"receipt": "${RECEIPT}"}}},
  "requestState": "${STATE}",
$(cafe_meta)
}}
JSON
)" | pp
