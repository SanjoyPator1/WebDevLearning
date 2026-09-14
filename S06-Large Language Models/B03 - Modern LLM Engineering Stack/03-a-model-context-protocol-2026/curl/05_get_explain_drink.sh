#!/usr/bin/env bash
#   bash curl/05_get_explain_drink.sh cortado
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
SLUG="${1:-cortado}"
expect 'the drink attached as an embedded application/json resource, then an
        instruction that bans three pieces of jargon unless explained. That ban is
        the sort of thing you can only put in a prompt — it is about HOW to answer,
        which no tool schema can express.'
exec ./get_prompt.sh explain_drink "{\"slug\": \"${SLUG}\"}" 303
