#!/usr/bin/env bash
#   bash curl/11_un_sell_out.sh espresso
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
SLUG="${1:-espresso}"
expect 'same as sell_out, in reverse — and if curl/11_listen.sh is still open in
        another terminal, a second notifications/resources/updated arrives
        there, on the SAME open connection as the first one.'
exec ./call.sh un_sell_out "{\"slug\": \"${SLUG}\"}" 1102
