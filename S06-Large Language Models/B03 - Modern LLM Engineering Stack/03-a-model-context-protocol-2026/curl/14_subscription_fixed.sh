#!/usr/bin/env bash
# THE mirror image of curl/11_cross_instance_leak.sh. Same exact experiment —
# listen on one instance, sell_out on a DIFFERENT one — except this time both
# instances share a SqliteSubscriptionBus instead of each holding its own
# private, in-memory one. Topic 11 proved silence. This proves the opposite.
set -euo pipefail
cd "$(dirname "$0")"

banner() { echo "--------------------------------------------------------------------"; echo "$1"; echo "--------------------------------------------------------------------"; }
V="2026-07-28"
META='{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}'
BUS=/tmp/cafe_mcp_14_subscription_bus.db
rm -f "$BUS"

banner "Two REAL t14 instances, ONE shared SqliteSubscriptionBus"
echo "Starting instance A (:3010) and instance B (:3011), both pointed at:"
echo "    ${BUS}"

CAFE_MCP_INSTANCE=instance-A CAFE_MCP_PORT=3010 CAFE_MCP_BUS_PATH="$BUS" \
  ../.venv/bin/python ../solved/t14_load_balancer.py > /tmp/cafe_t14_subA.log 2>&1 &
PID_A=$!
CAFE_MCP_INSTANCE=instance-B CAFE_MCP_PORT=3011 CAFE_MCP_BUS_PATH="$BUS" \
  ../.venv/bin/python ../solved/t14_load_balancer.py > /tmp/cafe_t14_subB.log 2>&1 &
PID_B=$!

cleanup() { kill -9 "$PID_A" "$PID_B" 2>/dev/null || true; }
trap cleanup EXIT

for port in 3010 3011; do
  for _ in $(seq 1 40); do
    curl -sS "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1 && break
    sleep 0.25
  done
done
echo "Both instances up (A: pid $PID_A, B: pid $PID_B)."
echo

echo ">>> Opening a listen stream on instance A (port 3010)..."
(timeout 4 curl -sS -N http://127.0.0.1:3010/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${V}" \
  -H 'Mcp-Method: subscriptions/listen' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1420,\"method\":\"subscriptions/listen\",\"params\":{\"notifications\":{\"resourceSubscriptions\":[\"cafe://menu\"]},\"_meta\":${META}}}" \
  | sed 's/^/  [listening on instance-A] /') &
LISTEN_PID=$!

sleep 1.5
echo ">>> Calling sell_out on instance B (port 3011) — a DIFFERENT process..."
curl -sS http://127.0.0.1:3011/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${V}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: sell_out' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1421,\"method\":\"tools/call\",\"params\":{\"name\":\"sell_out\",\"arguments\":{\"slug\":\"latte\"},\"_meta\":${META}}}" \
  | python3 -c "import json,sys;print('  instance-B says:', json.load(sys.stdin)['result']['content'][0]['text'])"

wait "$LISTEN_PID" 2>/dev/null || true

echo
banner "What just happened"
cat <<'TXT'
Instance A's listener saw a notifications/resources/updated event for
cafe://menu, even though sell_out ran entirely on instance B — check for
yourself:
    grep '\[instance:instance-B\]' /tmp/cafe_t14_subB.log
        -> sell_out('latte') -- publishing to the SHARED bus
    (the event above arrived on instance-A's OWN terminal output, not B's)

Nothing inside sell_out or notify_resource_updated changed between topic 11
and here. The only diff is the ONE constructor argument on MCPServer:
`subscriptions=SqliteSubscriptionBus(BUS_PATH)`, with both instances pointed
at the same file. A signed token could never have fixed topic 11's leak — a
subscription is a live connection to one process, not a value a client can
carry — but a bus every replica actually shares fixes it completely, with
zero changes to any tool.

One nuance worth noticing: if instance A's listener is the FIRST ever opened
against this bus file, it may also see any event published to the bus BEFORE
it connected (a backlog), because SqliteSubscriptionBus tracks its poll
position from when the bus object was constructed, not from when a listener
subscribes. An in-memory bus (topic 11) has no such backlog — it drops
anything published while nobody was listening. See notes/14-load-balancer.md
for why that trade-off is acceptable here.
TXT
