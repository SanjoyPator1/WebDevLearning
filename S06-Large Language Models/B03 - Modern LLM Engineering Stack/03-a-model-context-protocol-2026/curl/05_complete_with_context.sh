#!/usr/bin/env bash
# THE interesting completion script: the same request, with and without context.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh

banner "completion/complete, with and without CompletionContext"
cat <<'TXT'
`compare_drinks(first, second)` compares two drinks. Comparing a cortado with a
cortado is nonsense, so completing `second` should not offer whatever `first`
already is.

`context.arguments` carries the arguments the user has ALREADY filled in on this
same prompt. That is what turns completion from a static enum into a function of
state — a client filling a form top to bottom gets suggestions already consistent
with its earlier answers, which removes a class of error before it can happen.

Watch cortado disappear from the second list.
TXT
echo "===================================================================="
echo ">>> 1/2  complete 'second' typed 'c', NO context"
echo "===================================================================="
./complete.sh prompt compare_drinks second c
echo
echo "===================================================================="
echo ">>> 2/2  complete 'second' typed 'c', context first='cortado'"
echo "===================================================================="
./complete.sh prompt compare_drinks second c '{"first":"cortado"}'
echo
echo "--------------------------------------------------------------------"
echo "5 values -> 4 values. cortado is gone, and total dropped with it."
echo "--------------------------------------------------------------------"
