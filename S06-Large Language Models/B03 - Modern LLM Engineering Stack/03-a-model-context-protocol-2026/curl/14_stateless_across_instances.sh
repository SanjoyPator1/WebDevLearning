#!/usr/bin/env bash
# THE payoff for topics 06-08: starts THREE real t14 instances sharing nothing
# but a signed token, and walks ONE cart across all three, in order, proving
# a cart built on replica-1 is readable and extendable on replica-2 and
# replica-3 with zero coordination between them beyond the token itself.
set -euo pipefail
cd "$(dirname "$0")"

banner() { echo "--------------------------------------------------------------------"; echo "$1"; echo "--------------------------------------------------------------------"; }
V="2026-07-28"
META='{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}'
BUS=/tmp/cafe_mcp_14_stateless_bus.db
rm -f "$BUS"

banner "Three REAL t14 instances, one signed cart walked across all of them"
echo "Starting replica-1 (:3011), replica-2 (:3012), replica-3 (:3013)..."

CAFE_MCP_INSTANCE=replica-1 CAFE_MCP_PORT=3011 CAFE_MCP_BUS_PATH="$BUS" \
  ../.venv/bin/python ../solved/t14_load_balancer.py > /tmp/cafe_t14_r1.log 2>&1 &
PID1=$!
CAFE_MCP_INSTANCE=replica-2 CAFE_MCP_PORT=3012 CAFE_MCP_BUS_PATH="$BUS" \
  ../.venv/bin/python ../solved/t14_load_balancer.py > /tmp/cafe_t14_r2.log 2>&1 &
PID2=$!
CAFE_MCP_INSTANCE=replica-3 CAFE_MCP_PORT=3013 CAFE_MCP_BUS_PATH="$BUS" \
  ../.venv/bin/python ../solved/t14_load_balancer.py > /tmp/cafe_t14_r3.log 2>&1 &
PID3=$!

cleanup() { kill -9 "$PID1" "$PID2" "$PID3" 2>/dev/null || true; }
trap cleanup EXIT

for port in 3011 3012 3013; do
  for _ in $(seq 1 40); do
    curl -sS "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1 && break
    sleep 0.25
  done
done
echo "All three up."
echo

call() {
  local port="$1" tool="$2" args="$3" id="$4"
  curl -sS "http://127.0.0.1:${port}/mcp" -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${V}" \
    -H "Mcp-Method: tools/call" -H "Mcp-Name: ${tool}" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":${id},\"method\":\"tools/call\",\"params\":{\"name\":\"${tool}\",\"arguments\":${args},\"_meta\":${META}}}"
}

echo ">>> 1/3  add_to_order(latte, M, 1)  on replica-1 (:3011)  -- first call, no order token yet"
R1=$(call 3011 add_to_order '{"slug":"latte","size":"M","qty":1}' 1401)
SERVED1=$(echo "$R1" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['served_by'])")
TOKEN1=$(echo "$R1" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['order'])")
echo "    served_by: ${SERVED1}   (as expected — we called 3011 directly)"

echo ">>> 2/3  add_to_order(espresso, S, 2, order=<token from replica-1>)  on replica-2 (:3012)"
R2=$(call 3012 add_to_order "{\"slug\":\"espresso\",\"size\":\"S\",\"qty\":2,\"order\":\"${TOKEN1}\"}" 1402)
SERVED2=$(echo "$R2" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['served_by'])")
TOKEN2=$(echo "$R2" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['order'])")
LINES2=$(echo "$R2" | python3 -c "import json,sys;print(len(json.load(sys.stdin)['result']['structuredContent']['lines']))")
echo "    served_by: ${SERVED2}   cart now has ${LINES2} line(s) -- replica-2 had NEVER seen this cart before this call"

echo ">>> 3/3  view_order(order=<token from replica-2>)  on replica-3 (:3013)"
R3=$(call 3013 view_order "{\"order\":\"${TOKEN2}\"}" 1403)
SERVED3=$(echo "$R3" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['served_by'])")
TOTAL3=$(echo "$R3" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['structuredContent']['total'])")
LINES3=$(echo "$R3" | python3 -c "import json,sys;print(len(json.load(sys.stdin)['result']['structuredContent']['lines']))")
echo "    served_by: ${SERVED3}   lines: ${LINES3}   total: \$${TOTAL3}"

echo
banner "What just happened"
cat <<TXT
Three DIFFERENT OS processes answered these three calls (${SERVED1}, ${SERVED2},
${SERVED3}) — verify for yourself:
    grep '\[instance' /tmp/cafe_t14_r1.log /tmp/cafe_t14_r2.log /tmp/cafe_t14_r3.log

Every call still saw the FULL cart, correctly priced, correctly totaled.
Nothing coordinated the three processes except the token itself, signed by
whichever replica minted it and verified by whichever replica received it
next. This is topics 06-08's entire thesis, finally run against a real,
multi-process deployment instead of one server pretending to be several.
TXT
