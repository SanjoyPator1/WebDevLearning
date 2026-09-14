#!/usr/bin/env bash
# add_to_order refuses a size the drink is not sold in, same rule as topic 03's quote.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'isError: true, naming the available sizes — this check runs BEFORE the
        cart is touched, so a bad line never gets a chance to corrupt an
        otherwise-good order token.'
exec ./call.sh add_to_order '{"slug": "espresso", "size": "L", "qty": 1}' 704
