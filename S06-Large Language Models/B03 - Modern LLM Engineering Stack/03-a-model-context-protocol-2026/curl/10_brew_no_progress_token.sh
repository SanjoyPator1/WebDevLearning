#!/usr/bin/env bash
# Same tool, same 8 seconds of real work — but no progressToken, so nothing
# streams. `report_progress` calls silently become no-ops; you only find out
# the work happened at all when the plain JSON result finally arrives.
#   bash curl/10_brew_no_progress_token.sh "$(bash curl/10_get_order_token.sh)"
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 10_brew_no_progress_token.sh <order token>}"

expect 'silence for about 8 seconds, then ONE plain JSON body — content-type:
        application/json, not text/event-stream. `time` this script and
        compare to how long the work actually took: the server did the exact
        same ten `await ctx.report_progress(...)` calls as the previous
        script; without a progressToken they simply produced nothing to send.
        Progress reporting is entirely opt-in, and the opt-in is the CLIENT'"'"'s
        to make, not the tool author'"'"'s.'

time curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: brew' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1001, "method": "tools/call", "params": {
  "name": "brew",
  "arguments": {"order": "${ORDER}"},
$(cafe_meta)
}}
JSON
)" | pp
