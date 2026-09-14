#!/usr/bin/env bash
# Open a listen stream and leave it running. Run this in ONE terminal, then use
# a SECOND terminal for 11_sell_out.sh / 11_un_sell_out.sh while this one stays
# open — that is the whole point: this connection outlives any single RPC.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "subscriptions/listen — open and leave running"
cat <<'TXT'
The FIRST thing that arrives is an ACK:
    notifications/subscriptions/acknowledged
naming which filters were honored — for THIS request, exactly what you asked
for (any truthy flag, any URI, even one that names no real resource — honoring
never means "the server checked this is real", only "the server will tell you
if it happens").

Then NOTHING, until something changes. Leave this running and, in a second
terminal, run:
    bash curl/11_sell_out.sh espresso
    bash curl/11_un_sell_out.sh espresso
and watch a `notifications/resources/updated` arrive on THIS terminal, tagged
with the subscriptionId this request's `id` became.

Ctrl-C to stop. There is no graceful unsubscribe RPC — closing the connection
is how a client stops listening.
TXT
echo "--------------------------------------------------------------------"

curl -sS -N "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: subscriptions/listen' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 1100, "method": "subscriptions/listen", "params": {
  "notifications": {"resourceSubscriptions": ["cafe://menu"]},
$(cafe_meta)
}}
JSON
)"
