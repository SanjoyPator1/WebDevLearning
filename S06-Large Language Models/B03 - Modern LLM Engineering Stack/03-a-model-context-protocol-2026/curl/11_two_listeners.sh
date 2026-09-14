#!/usr/bin/env bash
# TWO concurrent listen streams on ONE instance, then ONE sell_out. Proves
# fan-out: every listener attached to this process's bus gets the event,
# each tagged with ITS OWN subscriptionId.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "Fan-out: two listeners, one instance, one event"

BODY_A='{"jsonrpc":"2.0","id":1110,"method":"subscriptions/listen","params":{"notifications":{"resourceSubscriptions":["cafe://menu"]},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}'
BODY_B='{"jsonrpc":"2.0","id":1111,"method":"subscriptions/listen","params":{"notifications":{"resourceSubscriptions":["cafe://menu"]},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}'

(timeout 4 curl -sS -N "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: subscriptions/listen' -d "$BODY_A" | sed 's/^/  [listener-A, id=1110] /') &
(timeout 4 curl -sS -N "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: subscriptions/listen' -d "$BODY_B" | sed 's/^/  [listener-B, id=1111] /') &

sleep 1.5
curl -sS "$CAFE_URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' -H 'Mcp-Name: sell_out' \
  -d '{"jsonrpc":"2.0","id":1112,"method":"tools/call","params":{"name":"sell_out","arguments":{"slug":"mocha"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}' > /dev/null
echo "  (fired: sell_out mocha)"
wait

echo "--------------------------------------------------------------------"
echo "Both listeners should show a notifications/resources/updated event,"
echo "each stamped with ITS OWN subscriptionId (1110 vs 1111) — one event,"
echo "delivered independently to every stream subscribed on THIS instance."
echo "--------------------------------------------------------------------"
