#!/usr/bin/env bash
# Call whoami declaring whatever version you pass. Try all four known ones:
#   bash curl/12_whoami.sh 2026-07-28
#   bash curl/12_whoami.sh 2025-11-25
#   bash curl/12_whoami.sh 2025-06-18
#   bash curl/12_whoami.sh 2024-11-05
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
V="${1:-2026-07-28}"

expect "the tool's own answer names exactly the version you sent — ${V}. All
        four values here are genuinely accepted; none of them is an error.
        There is no session remembering which one you used last time: change
        the header on your NEXT call and the answer changes with it, mid
        'conversation', because there is no conversation-level state at all —
        only ever this one request's own declared version."

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${V}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: whoami' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1201, "method": "tools/call", "params": {
  "name": "whoami",
  "arguments": {},
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "${V}",
    "io.modelcontextprotocol/clientInfo": {"name": "cafe-curl", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {}
  }
}}
JSON
)" | pp
