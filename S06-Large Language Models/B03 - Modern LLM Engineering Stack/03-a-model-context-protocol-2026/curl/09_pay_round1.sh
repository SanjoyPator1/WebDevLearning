#!/usr/bin/env bash
# ROUND 1: pay_for_order with no inputResponses yet.
#   bash curl/09_pay_round1.sh "$(bash curl/08_get_order_token.sh)"
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 09_pay_round1.sh <order token>   (bash curl/08_get_order_token.sh)}"

expect 'resultType: "input_required". Note inputRequests.pay.params.mode is
        "url", not "form" — there is no requestedSchema at all, only a
        `message` and a `url`. COPY THE URL for the next script, and the
        requestState for round 2.

        The message explicitly tells the model not to ask for card details in
        this chat. That sentence is doing real work — it is the one thing
        stopping a model from "helpfully" trying to collect a card number
        itself instead of sending the customer to the link.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: pay_for_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 900, "method": "tools/call", "params": {
  "name": "pay_for_order",
  "arguments": {"order": "${ORDER}"},
$(cafe_meta)
}}
JSON
)" | pp
