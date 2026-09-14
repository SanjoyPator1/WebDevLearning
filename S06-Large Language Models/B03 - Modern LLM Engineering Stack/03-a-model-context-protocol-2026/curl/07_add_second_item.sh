#!/usr/bin/env bash
# Add a second line to an EXISTING cart, using the token from the first call.
#   bash curl/07_add_second_item.sh 'v1.eyJ...<token>'
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 07_add_second_item.sh <order token>   (from 07_add_first_item.sh)}"
expect 'TWO lines now — Latte AND Espresso — and a NEW order token. The response
        always shows the FULL cart, not just the line you just added.

        The new token is longer only in appearance (same shape); what actually
        changed is the payload it carries: two lines now, not one.'
exec ./call.sh add_to_order "{\"slug\": \"espresso\", \"size\": \"S\", \"qty\": 1, \"order\": \"${ORDER}\"}" 701
