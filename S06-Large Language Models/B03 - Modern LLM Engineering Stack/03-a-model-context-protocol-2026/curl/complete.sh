#!/usr/bin/env bash
# Generic completion/complete.
#
#   bash curl/complete.sh prompt   order_for_me            mood  s
#   bash curl/complete.sh resource 'cafe://drinks/{slug}'  slug  c
#   bash curl/complete.sh prompt   compare_drinks          second c '{"first":"cortado"}'
#
# The `ref` discriminates on `type`:
#   {"type": "ref/prompt",   "name": "<prompt name>"}
#   {"type": "ref/resource", "uri":  "<URI TEMPLATE, with the {placeholder}>"}
#
# For a resource ref you pass the TEMPLATE, not a resolved URI. You are asking
# "what can go in the hole?", so the hole has to still be there.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

KIND="${1:?usage: complete.sh <prompt|resource> <name-or-template> <argument> [typed] [context-json]}"
TARGET="${2:?}"
ARG="${3:?}"
TYPED="${4:-}"
CONTEXT="${5:-}"

if [ "$KIND" = "prompt" ]; then
  REF="{\"type\": \"ref/prompt\", \"name\": \"${TARGET}\"}"
else
  REF="{\"type\": \"ref/resource\", \"uri\": \"${TARGET}\"}"
fi

CTX=""
if [ -n "$CONTEXT" ]; then
  CTX="  \"context\": {\"arguments\": ${CONTEXT}},"
fi

banner "POST completion/complete  ->  ${KIND} ${TARGET}, argument ${ARG}, typed '${TYPED}'"

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: completion/complete' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 350, "method": "completion/complete", "params": {
  "ref": ${REF},
  "argument": {"name": "${ARG}", "value": "${TYPED}"},
${CTX}
$(cafe_meta)
}}
JSON
)" | pp
