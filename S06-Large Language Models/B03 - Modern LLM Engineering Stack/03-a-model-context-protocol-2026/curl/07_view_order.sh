#!/usr/bin/env bash
# Read a cart back WITHOUT changing it.
#   bash curl/07_view_order.sh 'v1.eyJ...<token>'
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 07_view_order.sh <order token>}"
expect 'the same lines and total you last saw, and — this is the detail worth
        noticing — a FRESH token even though nothing was added. Every
        verify-then-resign call REFRESHES the 15-minute expiry window, so
        checking on a cart keeps it alive. (Two calls inside the same second can
        produce byte-identical tokens, since the signed timestamp only has
        second resolution — that is expected, not a bug.)'
exec ./call.sh view_order "{\"order\": \"${ORDER}\"}" 702
