#!/usr/bin/env bash
# Announce a drink BY ITS DISPLAY NAME, computing the Mcp-Param-DrinkName
# header value by hand — the whole point of this script.
#   bash curl/13_announce.sh 'Latte'
#   bash curl/13_announce.sh 'Crème Brûlée Latte'
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
NAME="${1:?usage: 13_announce.sh <drink display name>}"

# Plain ASCII with no leading/trailing whitespace passes through the header
# completely unchanged. Anything else — non-ASCII, control characters, edge
# whitespace — gets wrapped in the =?base64?...?= sentinel, because an HTTP
# header field cannot carry raw non-ASCII bytes at all. Compute it the same
# way the SDK's own encode_header_value does, by hand, so nothing is hidden:
HEADER_VALUE=$(python3 -c "
import sys, base64
name = sys.argv[1]
# _HEADER_SAFE (the SDK's own check) is roughly: printable ASCII, no leading
# or trailing whitespace, and not already shaped like the sentinel itself.
if name.isascii() and name.isprintable() and name == name.strip():
    print(name)
else:
    print('=?base64?' + base64.b64encode(name.encode('utf-8')).decode('ascii') + '?=')
" "$NAME")

banner "announce_drink(name='${NAME}')"
echo "computed Mcp-Param-DrinkName: ${HEADER_VALUE}"
expect 'the announcement, IF the header we just computed matches the body value
        byte for byte. Try a name with a typo and watch it fail differently
        (a ToolError from inside the tool, not a -32020) — the header check
        only cares that header and body AGREE, never whether the drink is
        real.'
echo "--------------------------------------------------------------------"

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: announce_drink' \
  -H "Mcp-Param-DrinkName: ${HEADER_VALUE}" \
  -d "$(python3 -c "
import json, sys
name = sys.argv[1]
body = {'jsonrpc': '2.0', 'id': 1301, 'method': 'tools/call',
        'params': {'name': 'announce_drink', 'arguments': {'name': name},
                   '_meta': {'io.modelcontextprotocol/protocolVersion': '2026-07-28',
                             'io.modelcontextprotocol/clientInfo': {'name': 'cafe-curl', 'version': '1.0'},
                             'io.modelcontextprotocol/clientCapabilities': {}}}}
print(json.dumps(body))
" "$NAME")" | pp
