#!/usr/bin/env bash
# resources/templates/list — a SEPARATE rpc, and this is the point of the script.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'ONE entry, and note the key: `uriTemplate`, not `uri`.
          "uriTemplate": "cafe://drinks/{slug}"

        Templates are how you expose a FAMILY of documents without enumerating
        them. Twelve drinks would be fine to list individually; twelve thousand
        would not.

        There is no way to ask "what values can {slug} take?" from this RPC alone.
        That is what completion/complete is for — topic 05.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: resources/templates/list' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 202, "method": "resources/templates/list", "params": {
$(cafe_meta)
}}
JSON
)" | pp
