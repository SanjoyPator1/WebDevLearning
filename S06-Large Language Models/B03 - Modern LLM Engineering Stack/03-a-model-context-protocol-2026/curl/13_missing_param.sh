#!/usr/bin/env bash
# The body carries the argument; the Mcp-Param-DrinkName header is simply
# absent. Also rejected — "present in the body" and "present in the header"
# must agree in BOTH directions, not just when both happen to be there.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "Body has the argument; the Mcp-Param-DrinkName header is missing entirely"
expect "-32020, \"Mcp-Param-DrinkName header is missing but the request body's
        'name' argument is present.\" A conforming client that declared
        x-mcp-header support is expected to ALWAYS mirror an annotated
        argument, never to omit the header opportunistically."

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: announce_drink' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1303, "method": "tools/call", "params": {
  "name": "announce_drink",
  "arguments": {"name": "Latte"},
$(cafe_meta)
}}
JSON
)" | pp
