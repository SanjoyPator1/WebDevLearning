#!/usr/bin/env bash
# A version string this SDK has genuinely never heard of — not "old", GENUINELY
# unknown — and the two-request recovery loop that follows from it.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "An unknown version, and the recovery it hands you"
expect '-32022 "Unsupported protocol version", with
          data: {"supported": ["2026-07-28"], "requested": "not-a-real-version"}
        That `data.supported` list is the WHOLE negotiation loop: read it, pick
        one, retry. It names the MODERN version(s) worth targeting — NOT every
        version this server happens to also accept (see 12_whoami.sh for the
        older ones that work fine and never needed this error at all).'

curl -sS "$CAFE_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: not-a-real-version' \
  -H 'Mcp-Method: tools/list' \
  -d '{"jsonrpc": "2.0", "id": 1202, "method": "tools/list", "params": {
    "_meta": {"io.modelcontextprotocol/protocolVersion": "not-a-real-version",
              "io.modelcontextprotocol/clientCapabilities": {}}
  }}' | pp
