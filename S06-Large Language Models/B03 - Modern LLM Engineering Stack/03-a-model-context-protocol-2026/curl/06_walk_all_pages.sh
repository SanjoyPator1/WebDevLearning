#!/usr/bin/env bash
# Walks the whole menu by following next_cursor until it comes back null.
# This is what a CLIENT is supposed to do — never construct a cursor, only ever
# copy one forward.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "Walking every page of list_drinks by following next_cursor"

CURSOR=""
PAGE=1
while :; do
  if [ -z "$CURSOR" ]; then
    ARGS='{}'
  else
    ARGS="{\"cursor\": \"${CURSOR}\"}"
  fi
  RESPONSE=$(curl -sS "$CAFE_URL" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
    -H 'Mcp-Method: tools/call' \
    -H 'Mcp-Name: list_drinks' \
    -d "{\"jsonrpc\": \"2.0\", \"id\": $((610 + PAGE)), \"method\": \"tools/call\",
         \"params\": {\"name\": \"list_drinks\", \"arguments\": ${ARGS},
         $(cafe_meta)}}")

  # Print exactly two lines, and never let the second one be EMPTY when there is
  # no next cursor — a bash `$(...)` command substitution strips ALL trailing
  # newlines, so an empty final line vanishes and `tail -1` silently falls back
  # to the slugs line, mistaking the drink list itself for a cursor. A sentinel
  # ("NONE") survives the substitution where an empty string would not. This bit
  # me writing the script; keeping the note because the failure mode — "no more
  # pages" quietly read back as "one more page" — is easy to miss.
  SLUGS=$(echo "$RESPONSE" | python3 -c "
import json, sys
r = json.load(sys.stdin)['result']['structuredContent']
print(', '.join(d['slug'] for d in r['drinks']))
print(r['next_cursor'] or 'NONE')
" 2>/dev/null)

  echo "page ${PAGE}: $(echo "$SLUGS" | head -1)"
  NEXT=$(echo "$SLUGS" | tail -1)
  CURSOR=""
  [ "$NEXT" != "NONE" ] && CURSOR="$NEXT"
  PAGE=$((PAGE + 1))
  [ -z "$CURSOR" ] && break
done

echo "--------------------------------------------------------------------"
echo "Stopped because next_cursor was null, not because a page was short."
echo "--------------------------------------------------------------------"
