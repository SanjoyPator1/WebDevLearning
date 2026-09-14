#!/usr/bin/env bash
# The whole flow, scripted: start a cart, add a second item, view it, tamper
# with it. Run this if you just want to see the shape without copy-pasting
# tokens between scripts by hand.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "The full order-token flow, start to finish"

STEP1=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: add_to_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":710,\"method\":\"tools/call\",\"params\":{\"name\":\"add_to_order\",\"arguments\":{\"slug\":\"latte\",\"size\":\"L\",\"qty\":2},$(cafe_meta)}}")
TOKEN1=$(echo "$STEP1" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['order'])")
echo ">>> 1/4 add_to_order(latte, L, 2)  ->  token ...${TOKEN1: -10}"

STEP2=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: add_to_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":711,\"method\":\"tools/call\",\"params\":{\"name\":\"add_to_order\",\"arguments\":{\"slug\":\"espresso\",\"size\":\"S\",\"qty\":1,\"order\":\"${TOKEN1}\"},$(cafe_meta)}}")
TOKEN2=$(echo "$STEP2" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['order'])")
LINES2=$(echo "$STEP2" | python3 -c "import json,sys;r=json.load(sys.stdin)['result']['structuredContent'];print(f\"{len(r['lines'])} lines, total {r['total']}\")")
echo ">>> 2/4 add_to_order(espresso, S, 1, order=...)  ->  ${LINES2}"

STEP3=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: view_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":712,\"method\":\"tools/call\",\"params\":{\"name\":\"view_order\",\"arguments\":{\"order\":\"${TOKEN2}\"},$(cafe_meta)}}")
echo "$STEP3" | python3 -c "
import json,sys
r = json.load(sys.stdin)['result']['structuredContent']
print('>>> 3/4 view_order ->', [(l['name'], l['size'], l['qty']) for l in r['lines']], 'total', r['total'])
"

# Flip the first character of the signature, not the token's last character —
# see curl/07_tamper.sh for why a last-character flip is only ~94% reliable
# (unused padding bits in the final base64url character of a 32-byte digest).
PREFIX2="${TOKEN2%.*}"
SIG2="${TOKEN2##*.}"
FIRST2="${SIG2:0:1}"
if [ "$FIRST2" = "a" ]; then NEW="b"; else NEW="a"; fi
TAMPERED="${PREFIX2}.${NEW}${SIG2:1}"
STEP4=$(curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: view_order' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":713,\"method\":\"tools/call\",\"params\":{\"name\":\"view_order\",\"arguments\":{\"order\":\"${TAMPERED}\"},$(cafe_meta)}}")
echo "$STEP4" | python3 -c "
import json,sys
r = json.load(sys.stdin)['result']
print('>>> 4/4 tampered view_order -> isError:', r['isError'])
print('        text:', r['content'][0]['text'])
"
echo "--------------------------------------------------------------------"
echo "Same cart, four calls, and the server never held any of it in memory."
echo "Everything it needed was in the token you carried."
echo "--------------------------------------------------------------------"
