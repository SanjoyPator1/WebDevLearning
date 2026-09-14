#!/usr/bin/env bash
# THE IRONY: server/discover exists to help a client that does not yet know
# what version to speak — and it only works for a client that ALREADY declared
# the modern version. Ask for it under an older, genuinely-known era and it is
# not merely unsupported, it does not exist there at all.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "server/discover, declared under 2025-06-18"
cat <<'TXT'
2025-06-18 is a real, KNOWN, fully-working version for every other method on
this server — see curl/12_whoami.sh 2025-06-18. discover is the one exception:
it was added AT 2026-07-28 and has no entry in any earlier version's method
map at all.
TXT
expect '-32601 "Method not found", data: "server/discover" — NOT -32022. The
        version itself was perfectly valid; this particular METHOD simply does
        not exist under it. A client with zero prior knowledge cannot safely
        call discover to find out what to speak FIRST — it has to already be
        speaking 2026-07-28 to ask. The realistic zero-knowledge strategy is
        the opposite: try your own preferred/latest version directly on the
        real call you actually want, and read -32022'"'"'s recovery list only if
        that fails.'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  -H 'Mcp-Method: server/discover' \
  -d '{"jsonrpc": "2.0", "id": 1203, "method": "server/discover", "params": {
    "_meta": {"io.modelcontextprotocol/protocolVersion": "2025-06-18",
              "io.modelcontextprotocol/clientCapabilities": {}}
  }}' | pp
