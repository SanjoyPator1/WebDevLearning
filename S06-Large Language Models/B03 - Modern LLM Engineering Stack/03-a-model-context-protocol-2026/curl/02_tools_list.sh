#!/usr/bin/env bash
# tools/list against the café. This is the single most important output in the
# whole folder, because it is EXACTLY what the language model sees.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "POST tools/list  (topic 02 — read this one slowly)"
cat <<'TXT'
EXPECT, and check each one:

  ttlMs: 300000       the menu is good for five minutes
  cacheScope: "public" a shared proxy MAY cache it (compare topic 01: "private")

  tool order: ["list_drinks", "get_drink"]
      -> registration order, preserved. Swap the two functions in
         solved/t02_tools.py, restart, and the wire order follows.

  list_drinks.description
      -> the Python docstring, verbatim, indentation and all. This is prompt
         text, not documentation.

  list_drinks.inputSchema
      -> {"type": "object", "properties": {}} — a no-argument tool still
         publishes a schema.

  get_drink.inputSchema.properties.slug.description
      -> came from Annotated[str, Field(description=...)], NOT the docstring.
         The docstring describes the TOOL; this describes one ARGUMENT.

  outputSchema on both
      -> a full nested JSON Schema with the Drink model under "$defs".
         That is what returning a pydantic model buys you over returning a dict.
TXT
echo "--------------------------------------------------------------------"

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: tools/list' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {
$(cafe_meta)
}}
JSON
)" | pp
