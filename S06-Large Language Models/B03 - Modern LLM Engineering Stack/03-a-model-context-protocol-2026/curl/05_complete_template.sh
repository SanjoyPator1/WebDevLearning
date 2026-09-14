#!/usr/bin/env bash
# Completing a RESOURCE TEMPLATE placeholder. This closes topic 04's gap.
#   bash curl/05_complete_template.sh c
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
TYPED="${1:-c}"
expect "the drink slugs starting with '${TYPED}'.

        This is the answer to the question topic 04 could not answer.
        resources/templates/list told the client the SHAPE of the address —
        cafe://drinks/{slug} — and nothing about the address space. Neither RPC on
        its own is enough: the template gives the shape, completion gives the
        values.

        Note you pass the TEMPLATE in the ref, with the {placeholder} still in it.
        You are asking what can go in the hole, so the hole has to still be there."
exec ./complete.sh resource 'cafe://drinks/{slug}' slug "$TYPED"
