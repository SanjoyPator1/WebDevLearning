#!/usr/bin/env bash
# THE central proof of this topic. Starts TWO SEPARATE server processes —
# instance A on 3010, instance B on 3011 — listens on A, then calls sell_out
# on B, and shows that A's listener sees NOTHING.
set -euo pipefail
cd "$(dirname "$0")"

banner() { echo "--------------------------------------------------------------------"; echo "$1"; echo "--------------------------------------------------------------------"; }
V="2026-07-28"
META='{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}'

banner "Two REAL instances of t11_subscriptions.py — not a simulation"
echo "Starting instance A on :3010 and instance B on :3011..."

CAFE_MCP_INSTANCE=instance-A CAFE_MCP_PORT=3010 ../.venv/bin/python ../solved/t11_subscriptions.py \
  > /tmp/cafe_instance_A.log 2>&1 &
PID_A=$!
CAFE_MCP_INSTANCE=instance-B CAFE_MCP_PORT=3011 ../.venv/bin/python ../solved/t11_subscriptions.py \
  > /tmp/cafe_instance_B.log 2>&1 &
PID_B=$!

cleanup() { kill -9 "$PID_A" "$PID_B" 2>/dev/null || true; }
trap cleanup EXIT

sleep 2.5
echo "Both instances up (A: pid $PID_A, B: pid $PID_B)."
echo
echo ">>> Opening a listen stream on instance A (port 3010)..."
(timeout 4 curl -sS -N http://127.0.0.1:3010/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${V}" \
  -H 'Mcp-Method: subscriptions/listen' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1120,\"method\":\"subscriptions/listen\",\"params\":{\"notifications\":{\"resourceSubscriptions\":[\"cafe://menu\"]},\"_meta\":${META}}}" \
  | sed 's/^/  [listening on instance-A] /') &
LISTEN_PID=$!

sleep 1.5
echo ">>> Calling sell_out on instance B (port 3011) — a DIFFERENT process..."
curl -sS http://127.0.0.1:3011/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${V}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: sell_out' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1121,\"method\":\"tools/call\",\"params\":{\"name\":\"sell_out\",\"arguments\":{\"slug\":\"latte\"},\"_meta\":${META}}}" \
  | python3 -c "import json,sys;print('  instance-B says:', json.load(sys.stdin)['result']['content'][0]['text'])"

wait "$LISTEN_PID" 2>/dev/null || true

echo
banner "What just happened"
cat <<'TXT'
sell_out succeeded — on instance B. Instance B's own SOLD_OUT set now has
"latte" in it, and instance B's OWN subscribers (there are none in this demo)
would have been told.

Instance A's listener saw only its own ack, and then silence for the entire
4-second window, even though a real, successful sell_out happened while it
was open. Check for yourself:
    grep '\[server' /tmp/cafe_instance_A.log   <- nothing (only startup banner lines)
    grep '\[server' /tmp/cafe_instance_B.log   <- "sell_out('latte') -- notifying subscribers"

Nine of the ten RPCs in this whole folder would have worked identically no
matter which of these two instances answered each call, because their state
lives in a signed token the CLIENT carries. This one does not. That is not a
bug to fix with a bigger token — a subscription IS a live connection to one
specific process, and no signature can fan an event out to a socket it was
never sent to. Topic 14 fixes it the way real systems do: a shared bus
(Redis, NATS) behind the SubscriptionBus Protocol, replacing
InMemorySubscriptionBus without changing a single line of this file.
TXT
