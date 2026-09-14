#!/usr/bin/env bash
# server/discover, sent the only way it actually works: declaring 2026-07-28.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

expect 'supportedVersions: ["2026-07-28"] — ONE entry, not all five this SDK
        can actually speak. That is not a bug: discover is itself a
        2026-07-28-only method, so it only ever advertises the MODERN
        version(s) it offers under discovery — it says nothing about which
        older dialects the server will also silently accept on ordinary
        calls. See curl/12_whoami.sh for those.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: server/discover' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1200, "method": "server/discover", "params": {
$(cafe_meta)
}}
JSON
)" | pp
