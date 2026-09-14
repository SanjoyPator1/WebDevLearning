#!/usr/bin/env bash
#   bash curl/11_sell_out.sh espresso
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
SLUG="${1:-espresso}"
expect 'a plain tools/call result — nothing about THIS response looks like
        subscriptions/listen at all. The notification goes out on whichever
        listen streams are open, not on this call'"'"'s own response.'
exec ./call.sh sell_out "{\"slug\": \"${SLUG}\"}" 1101
