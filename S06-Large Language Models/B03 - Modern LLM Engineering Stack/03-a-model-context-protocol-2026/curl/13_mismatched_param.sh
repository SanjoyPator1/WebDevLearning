#!/usr/bin/env bash
# The header claims "Latte"; the body actually orders "Espresso". Deliberately
# disagreeing, to prove the SDK checks this BEFORE the tool ever runs.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "Mcp-Param-DrinkName: Latte, but the body's name argument is Espresso"
expect "-32020, \"Mcp-Param-DrinkName header does not match the request body's
        'name' argument\" — a JSON-RPC ERROR, not a tool result. Exactly the
        same rejection family as a wrong Mcp-Method or Mcp-Name header from
        topic 01: the gateway-facing headers and the body must agree, and the
        check happens before your tool code is ever reached."

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: announce_drink' \
  -H 'Mcp-Param-DrinkName: Latte' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1302, "method": "tools/call", "params": {
  "name": "announce_drink",
  "arguments": {"name": "Espresso"},
$(cafe_meta)
}}
JSON
)" | pp
