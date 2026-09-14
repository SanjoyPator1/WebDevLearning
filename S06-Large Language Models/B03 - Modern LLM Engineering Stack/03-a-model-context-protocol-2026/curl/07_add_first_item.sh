#!/usr/bin/env bash
# The first call in a new order. No `order` argument at all — that is how you
# start a fresh cart, same convention as topic 06's "no cursor means page one".
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'one line (Latte, L, x2), total 8.6, and an `order` token — much longer
        than topic 06'"'"'s cursor, because this one is HMAC-signed, not just
        base64. Copy the whole token for the next script.'
exec ./call.sh add_to_order '{"slug": "latte", "size": "L", "qty": 2}' 700
