#!/usr/bin/env bash
# The whole topic: -N (no buffering) and Accept: text/event-stream, PLUS a
# progressToken in _meta. Watch the events arrive one at a time rather than
# all at once — this is what "streamable" HTTP actually buys you.
#   bash curl/10_brew_with_progress.sh "$(bash curl/10_get_order_token.sh)"
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 10_brew_with_progress.sh <order token>   (bash curl/10_get_order_token.sh)}"

expect 'TEN notifications/progress events (two drinks x five steps each),
        arriving roughly 0.8s apart, THEN the final tools/call result as the
        LAST event on the SAME stream. No separate connection was opened for
        the notifications — they ride the response of the request that asked
        for them.

        The `progressToken` you sent (a value YOU chose, "cafe-progress-demo")
        comes back unchanged on every event — it is how a client with several
        calls in flight tells them apart.'

curl -sS -N "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: brew' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1000, "method": "tools/call", "params": {
  "name": "brew",
  "arguments": {"order": "${ORDER}"},
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "${CAFE_VERSION}",
    "io.modelcontextprotocol/clientInfo": {"name": "cafe-curl", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
    "progressToken": "cafe-progress-demo"
  }
}}
JSON
)"
