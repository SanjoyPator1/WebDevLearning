#!/usr/bin/env bash
# THE script for topic 04. The same missing drink, asked two ways.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "The same missing drink, via a RESOURCE and via a TOOL"
cat <<'TXT'
Topic 03 established: a failing TOOL returns a SUCCESSFUL JSON-RPC response whose
result has isError: true.

Topic 04 adds the opposite: a failing RESOURCE READ returns a real JSON-RPC error.

That is not an inconsistency. Apply topic 03's test — WHO CAN FIX THIS?

  A tool call was chosen by the MODEL. The model can choose differently next turn,
  so the failure must reach the model -> it goes in `result`, where the model looks.

  A resource URI was chosen by the CLIENT or the USER. The model was not involved
  and cannot fix it. It is the client's mistake -> it goes in `error`, where the
  client looks.

Same question, opposite answers, because a different party is holding the wheel.
TXT
echo "===================================================================="
echo ">>> 1/2  RESOURCE: read cafe://drinks/no-such-drink"
echo "===================================================================="
./read.sh cafe://drinks/no-such-drink 206
echo
echo "===================================================================="
echo ">>> 2/2  TOOL: call get_drink(slug='no-such-drink')"
echo "===================================================================="
./call.sh get_drink '{"slug": "no-such-drink"}' 207
echo
echo "--------------------------------------------------------------------"
echo "Look at which top-level key each one used: \"error\" vs \"result\"."
echo "Both messages survived, because both used the right exception type:"
echo "  ResourceNotFoundError  ->  -32602, message forwarded"
echo "  ToolError              ->  isError: true, message forwarded"
echo "Raise a BARE exception from either and the message is withheld:"
echo "  resource -> -32603 \"Error reading resource <uri>\""
echo "  tool     -> isError, \"Error executing tool <name>\""
echo "--------------------------------------------------------------------"
