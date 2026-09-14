#!/usr/bin/env bash
# The whole URL-mode flow, scripted end to end.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
PY="../.venv/bin/python"

banner "The full URL-mode MRTR flow: a link, a receipt, and two blocked forgeries"

ORDER=$("$PY" -c "
from cafe_mcp import orders
print(orders.sign_cart([{'slug': 'latte', 'size': 'L', 'qty': 2}], ttl_s=900))
")
echo ">>> 1/6 minted an order token"

R1=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: pay_for_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":910,\"method\":\"tools/call\",\"params\":{\"name\":\"pay_for_order\",\"arguments\":{\"order\":\"${ORDER}\"},$(cafe_meta)}}")
PAY_URL=$(echo "$R1" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['inputRequests']['pay']['params']['url'])")
STATE=$(echo "$R1" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['requestState'])")
echo ">>> 2/6 round 1 -> a payment LINK, not a form"

curl -sS "$PAY_URL" >/dev/null
echo ">>> 3/6 GET the pay page (what a human would see)"

RECEIPT=$(curl -sS -X POST "$PAY_URL" | python3 -c "import json,sys;print(json.load(sys.stdin)['receipt'])")
echo ">>> 4/6 POST (\"clicked Pay\") -> minted a receipt"

R2=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: pay_for_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":911,\"method\":\"tools/call\",\"params\":{\"name\":\"pay_for_order\",\"arguments\":{\"order\":\"${ORDER}\"},\"inputResponses\":{\"pay\":{\"action\":\"accept\",\"content\":{\"receipt\":\"${RECEIPT}\"}}},\"requestState\":\"${STATE}\",$(cafe_meta)}}")
echo "$R2" | python3 -c "
import json, sys
r = json.load(sys.stdin)['result']['structuredContent']['result']
print('>>> 5/6 round 2 with the real receipt ->', r)
"

R3=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: pay_for_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":912,\"method\":\"tools/call\",\"params\":{\"name\":\"pay_for_order\",\"arguments\":{\"order\":\"${ORDER}\"},\"inputResponses\":{\"pay\":{\"action\":\"accept\"}},\"requestState\":\"${STATE}\",$(cafe_meta)}}")
echo "$R3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('>>> 6/6 retry (fresh order) with NO receipt at all ->', d['error']['message'])
"

echo "--------------------------------------------------------------------"
echo "The model that called pay_for_order never saw a card number, never saw"
echo "the pay page's HTML, and never saw the receipt's contents — only the"
echo "URL to hand the customer, and the final placed/declined result."
echo "--------------------------------------------------------------------"
