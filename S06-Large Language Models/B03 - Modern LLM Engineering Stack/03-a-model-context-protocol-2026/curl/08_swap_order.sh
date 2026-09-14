#!/usr/bin/env bash
# THE ATTACK: reuse a real requestState from round 1, but send a DIFFERENT
# (also validly-signed!) order token on the retry — trying to confirm a cheap
# cart and have a bigger one placed instead.
#   bash curl/08_swap_order.sh <requestState from a round-1 call>
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
STATE="${1:?usage: 08_swap_order.sh <requestState from a round-1 call>}"

DIFFERENT_ORDER=$(../.venv/bin/python -c "
from cafe_mcp import orders
print(orders.sign_cart([{'slug': 'mocha', 'size': 'L', 'qty': 5}], ttl_s=900))
")

banner "Retry with a swapped order token — the requestState still matches round 1's"
cat <<'TXT'
This is NOT a forged or tampered token. `DIFFERENT_ORDER` is a real,
legitimately-signed order token for a completely different cart. The only thing
wrong with this request is that it does not match what round 1 was actually
asked to confirm.
TXT
expect '-32602 "Invalid or expired requestState" — a JSON-RPC ERROR, not a
        result. place_order NEVER RUNS. The SDK computes a digest of THIS
        request'"'"'s arguments, compares it to the digest sealed into requestState
        at round 1, and refuses the mismatch before any of your code executes.
        You did not write a single line of code to get this protection.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: place_order' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 803, "method": "tools/call", "params": {
  "name": "place_order",
  "arguments": {"order": "${DIFFERENT_ORDER}"},
  "inputResponses": {"confirm": {"action": "accept", "content": {"name": "Attacker", "confirm": true}}},
  "requestState": "${STATE}",
$(cafe_meta)
}}
JSON
)" | pp
