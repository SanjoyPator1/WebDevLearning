#!/usr/bin/env bash
# Kill the connection after 2 seconds, mid-brew, and watch the SERVER'S OWN
# terminal — not this one — to see what happens next.
#   bash curl/10_interrupt_brew.sh "$(bash curl/10_get_order_token.sh)"
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 10_interrupt_brew.sh <order token>}"

banner "Interrupting a brew 2 seconds in (of an ~8 second job)"
cat <<'TXT'
This script's own output will just look like a truncated stream — that part
is not the interesting bit. Switch to the terminal running t10_progress.py
BEFORE running this, and watch its step-by-step log while this runs.
TXT
expect 'the SERVER log stops at whatever step it reached when the connection
        died — around step 2 or 3 of 10 — and NEVER reaches "brew COMPLETE".
        The coroutine was cancelled, not merely disconnected from; the drinks
        that were "in progress" never finish being brewed. There is no
        Last-Event-ID, no reconnect, no partial credit. The only recovery is
        calling brew again, from scratch, with a brand new JSON-RPC id.'

curl -sS -N --max-time 2 "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: brew' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1002, "method": "tools/call", "params": {
  "name": "brew",
  "arguments": {"order": "${ORDER}"},
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "${CAFE_VERSION}",
    "io.modelcontextprotocol/clientInfo": {"name": "cafe-curl", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
    "progressToken": "cafe-interrupt-demo"
  }
}}
JSON
)" || true
echo
echo "--------------------------------------------------------------------"
echo "(curl exits non-zero here on purpose — --max-time cut it off. Go read"
echo " the SERVER's terminal now.)"
echo "--------------------------------------------------------------------"
