#!/usr/bin/env bash
# THE SECOND ATTACK: a REAL receipt, genuinely signed by this server — just
# for a DIFFERENT, cheaper order.
#   bash curl/09_wrong_order_receipt.sh <order token A> <requestState for A>
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER_A="${1:?usage: 09_wrong_order_receipt.sh <order token> <requestState>}"
STATE_A="${2:?usage: 09_wrong_order_receipt.sh <order token> <requestState>}"
PY="../.venv/bin/python"

banner "A genuine receipt for a DIFFERENT order, replayed against this one"

ORDER_B=$("$PY" -c "
from cafe_mcp import orders
print(orders.sign_cart([{'slug': 'espresso', 'size': 'S', 'qty': 1}], ttl_s=900))
")
R1B=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: pay_for_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":903,\"method\":\"tools/call\",\"params\":{\"name\":\"pay_for_order\",\"arguments\":{\"order\":\"${ORDER_B}\"},$(cafe_meta)}}")
URL_B=$(echo "$R1B" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['inputRequests']['pay']['params']['url'])")
RECEIPT_B=$(curl -sS -X POST "$URL_B" | python3 -c "import json,sys;print(json.load(sys.stdin)['receipt'])")

echo "Order A (the one we're trying to pay for): 2x latte, \$8.60"
echo "Order B (a real, separately-paid-for order): 1x espresso, cheaper"
echo "Replaying B's genuine receipt against A's payment..."

expect 'isError: true. "This payment receipt does not match the current order."

        The signature on that receipt is completely valid — it really was
        minted by this server, for a real payment, of a real (smaller) order.
        Signature verification alone would have let this through. Checking
        that the receipt'"'"'s OWN CONTENT (its order, its total) matches what
        is actually being paid for right now is the check that catches it —
        the same "verify the payload, not just the signature" lesson from
        topic 08'"'"'s price-drift check, applied to a new kind of token.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: pay_for_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 904, "method": "tools/call", "params": {
  "name": "pay_for_order",
  "arguments": {"order": "${ORDER_A}"},
  "inputResponses": {"pay": {"action": "accept", "content": {"receipt": "${RECEIPT_B}"}}},
  "requestState": "${STATE_A}",
$(cafe_meta)
}}
JSON
)" | pp
