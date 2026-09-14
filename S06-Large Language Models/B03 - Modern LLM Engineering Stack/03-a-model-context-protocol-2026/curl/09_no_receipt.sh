#!/usr/bin/env bash
# THE FIRST ATTACK: action: "accept" with NO receipt at all.
#   bash curl/09_no_receipt.sh <order token> <requestState>
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 09_no_receipt.sh <order token> <requestState>}"
STATE="${2:?usage: 09_no_receipt.sh <order token> <requestState>}"

banner "accept, with no receipt — a naive integration would trust this"
cat <<'TXT'
`action: "accept"` alone is a CLAIM, not proof. Anything sending this retry
could set it to "accept" without the human ever visiting the payment page at
all. A design that branches only on `action` and ignores `content.receipt`
would place this order for free.
TXT
expect '-32602, "No payment receipt was provided." The order is NOT placed.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: pay_for_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 902, "method": "tools/call", "params": {
  "name": "pay_for_order",
  "arguments": {"order": "${ORDER}"},
  "inputResponses": {"pay": {"action": "accept"}},
  "requestState": "${STATE}",
$(cafe_meta)
}}
JSON
)" | pp
