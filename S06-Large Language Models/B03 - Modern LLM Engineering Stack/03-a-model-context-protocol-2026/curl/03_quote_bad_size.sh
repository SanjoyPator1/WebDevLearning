#!/usr/bin/env bash
# ToolError: an EXPECTED failure, message passed through.
#
# "L" is a legal size and passed the schema. Espresso just is not sold in it, and
# only the server's data knows that. So the check lives in Python and raises
# ToolError, which the SDK forwards verbatim.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'isError: true, and the message SURVIVES:
          "Espresso is not sold in size L. It comes in: S, M. Ask the customer
           to pick one of those, or suggest a similar drink that does come in L."
        Note it names the problem, quotes the bad value, AND gives the next step.
        A model reading that recovers on its next turn.
        Note also the JSON-RPC envelope says "result", not "error".'
exec ./call.sh quote '{"slug": "espresso", "size": "L", "qty": 1}' 31
