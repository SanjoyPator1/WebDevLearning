#!/usr/bin/env bash
# prompts/list — three prompts, and the argument metadata a host needs.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'THREE prompts. For each, an `arguments` array where every entry has
        `name`, `required` and — the part people leave out — `description`.

        The descriptions came from Annotated[..., Field(description=...)], exactly
        as with tool arguments. Without them a host shows the user a bare argument
        name and no hint about what to type, which makes a slash command useless.

        Note `dairy_free` has required: false, because it has a Python default.
        Also: ttlMs/cacheScope ARE here (prompts/list is cacheable) but you will
        NOT see them on prompts/get — that renders against arguments, so there is
        nothing stable to cache.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "MCP-Protocol-Version: ${CAFE_VERSION}" \
  -H 'Mcp-Method: prompts/list' \
  -d "$(cat <<JSON
{"jsonrpc": "2.0", "id": 301, "method": "prompts/list", "params": {
$(cafe_meta)
}}
JSON
)" | pp
