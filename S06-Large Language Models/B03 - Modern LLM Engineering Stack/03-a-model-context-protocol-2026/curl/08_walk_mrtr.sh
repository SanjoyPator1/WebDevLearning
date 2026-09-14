#!/usr/bin/env bash
# The whole MRTR flow, scripted end to end: mint a token, round 1, round 2,
# and the blocked attack — no manual copy-pasting of tokens required.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
PY=../.venv/bin/python

banner "The full MRTR flow: input_required -> confirm -> complete"

ORDER=$("$PY" -c "
from cafe_mcp import orders
print(orders.sign_cart([{'slug': 'latte', 'size': 'L', 'qty': 2}], ttl_s=900))
")
echo ">>> 1/4 minted an order token (topic 07's mechanism, reused as-is)"

R1=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: place_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":810,\"method\":\"tools/call\",\"params\":{\"name\":\"place_order\",\"arguments\":{\"order\":\"${ORDER}\"},$(cafe_meta)}}")
echo "$R1" | python3 -c "
import json, sys
r = json.load(sys.stdin)['result']
print('>>> 2/4 round 1 ->', r['resultType'], '|', r['inputRequests']['confirm']['params']['message'])
"
STATE=$(echo "$R1" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['requestState'])")

R2=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: place_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":811,\"method\":\"tools/call\",\"params\":{\"name\":\"place_order\",\"arguments\":{\"order\":\"${ORDER}\"},\"inputResponses\":{\"confirm\":{\"action\":\"accept\",\"content\":{\"name\":\"Sanjoy\",\"confirm\":true}}},\"requestState\":\"${STATE}\",$(cafe_meta)}}")
echo "$R2" | python3 -c "
import json, sys
r = json.load(sys.stdin)['result']['structuredContent']['result']
print('>>> 3/4 round 2 (correct order) ->', r)
"

DIFFERENT=$("$PY" -c "
from cafe_mcp import orders
print(orders.sign_cart([{'slug': 'mocha', 'size': 'L', 'qty': 5}], ttl_s=900))
")
R3=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: place_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":812,\"method\":\"tools/call\",\"params\":{\"name\":\"place_order\",\"arguments\":{\"order\":\"${DIFFERENT}\"},\"inputResponses\":{\"confirm\":{\"action\":\"accept\",\"content\":{\"name\":\"Attacker\",\"confirm\":true}}},\"requestState\":\"${STATE}\",$(cafe_meta)}}")
echo "$R3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('>>> 4/4 retry with a SWAPPED order token, same old requestState ->', d.get('error'))
"

echo "--------------------------------------------------------------------"
echo "Round 2 succeeded only because its arguments matched round 1's exactly."
echo "The swap in step 4 never reached place_order at all."
echo "--------------------------------------------------------------------"
