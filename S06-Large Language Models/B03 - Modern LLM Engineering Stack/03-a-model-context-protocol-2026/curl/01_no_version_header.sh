#!/usr/bin/env bash
# The interesting one: a POST with NO MCP-Protocol-Version header.
#
# With `stateless_http=True` the SDK still answers, because there is no session
# to look up. Run the same request against a server started WITHOUT that flag and
# you get `Bad Request: Missing session ID` — the client did nothing wrong, it
# just fell down the pre-2026 code path.
#
# Second thing to notice: the response FRAMING changes. Without the modern
# headers the SDK replies with an SSE-framed body (`event: message` / `data: ...`)
# instead of a plain JSON one. Any client you write by hand must parse both.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "POST tools/list with NO MCP-Protocol-Version header"
expect 'a successful tools/list result, but SSE-framed rather than plain JSON.
        Against a server started with stateless_http=False you would instead see
        HTTP 400 "Bad Request: Missing session ID".'

curl -sS -i "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/list","params":{}}' \
  | sed -n '1,/^\r*$/p'

echo "--- body ---"
curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/list","params":{}}' | pp
