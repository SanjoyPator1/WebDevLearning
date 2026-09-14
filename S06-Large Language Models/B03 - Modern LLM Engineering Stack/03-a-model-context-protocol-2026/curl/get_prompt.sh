#!/usr/bin/env bash
# Generic prompts/get.
#
#   bash curl/get_prompt.sh order_for_me '{"mood": "sleepy"}'
#
# Note `Mcp-Name` mirrors params.name here, as it does for tools/call. (For
# resources/read it mirrors params.uri instead — three name-bearing methods, two
# different source keys.)
#
# IMPORTANT: prompt arguments are STRINGS on the wire. There is no JSON typing in
# `params.arguments` for prompts the way there is for tools — a boolean is the
# string "true". Your Python type hints coerce it back.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
NAME="${1:?usage: get_prompt.sh <prompt-name> [json-arguments]}"
ARGS="${2:-{\}}"
ID="${3:-300}"

banner "POST prompts/get  ->  ${NAME}  ${ARGS}"

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: prompts/get' \
  -H "Mcp-Name: ${NAME}" \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": ${ID}, "method": "prompts/get", "params": {
  "name": "${NAME}",
  "arguments": ${ARGS},
$(cafe_meta)
}}
JSON
)" | pp
