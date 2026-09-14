#!/usr/bin/env bash
# An unknown tool name is NOT a JSON-RPC error in mcp 2.1.1.
#
# You might reasonably expect -32601 "Method not found", or -32602 "Invalid
# params". You get neither.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'HTTP 200, a JSON-RPC *result* (not *error*), with:
          isError: true
          content: [{"type": "text", "text": "Unknown tool: not_a_tool"}]

        The spec prose reads as though this should be a protocol-level error. In
        mcp 2.1.1 it is not — and the SDK behaviour is arguably the better one:
        "you asked for a tool I do not have" is information the MODEL can act on
        (it can re-read tools/list), so it belongs in the result where the model
        will see it, not in an envelope error that the client may swallow.'
exec ./call.sh not_a_tool '{}' 35
