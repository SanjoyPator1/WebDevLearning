#!/usr/bin/env bash
# Send a Last-Event-ID header, exactly as a client resuming an SSE stream
# would under the OLD (pre-2026) transport, and watch it be completely
# ignored: the brew starts over from step 1, not from wherever a dropped
# connection left off.
#   bash curl/10_last_event_id.sh "$(bash curl/10_get_order_token.sh)"
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 10_last_event_id.sh <order token>}"

expect 'progress starting at 1/10 — "grinding — Latte (L)" — NOT wherever
        Last-Event-ID: 5 might have implied. The header does nothing. SSE
        resumability, and the event `id:` field it depended on, were removed
        at 2026-07-28: every event you saw in curl/10_brew_with_progress.sh
        had no `id:` line at all. There is nothing to resume from.'

curl -sS -N --max-time 3 "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: brew' \
  -H 'Last-Event-ID: 5' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1003, "method": "tools/call", "params": {
  "name": "brew",
  "arguments": {"order": "${ORDER}"},
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "${CAFE_VERSION}",
    "io.modelcontextprotocol/clientInfo": {"name": "cafe-curl", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
    "progressToken": "cafe-resume-demo"
  }
}}
JSON
)"
