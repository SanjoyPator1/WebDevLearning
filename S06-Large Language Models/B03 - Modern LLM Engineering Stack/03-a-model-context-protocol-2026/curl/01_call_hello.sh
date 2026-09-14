#!/usr/bin/env bash
# tools/call — the actual work.
#
# Note the `Mcp-Name` header. As of 2026-07-28, POSTs for the three
# "name-bearing" methods MUST mirror the target into a header:
#     tools/call    -> params.name
#     prompts/get   -> params.name
#     resources/read-> params.uri
# The point is that a gateway can route or rate-limit on the tool being called
# without parsing the JSON body.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

NAME="${1:-Sanjoy}"

banner "POST tools/call  ->  hello(name=\"$NAME\")"
expect 'resultType: "complete", isError: false, a text `content` block, and
        `structuredContent` carrying the same value as a typed object.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: hello' \
  -d "$(cat <<JSON
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "hello",
    "arguments": {"name": "${NAME}"},
$(cafe_meta)
  }
}
JSON
)" | pp
