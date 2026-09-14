#!/usr/bin/env bash
# Flip ONE character of a real order token and try to use it.
#   bash curl/07_tamper.sh 'v1.eyJ...<token>'
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
ORDER="${1:?usage: 07_tamper.sh <order token>}"

# Flip the FIRST character of the signature (after the second dot), not the
# token's last character. The last base64url character of a 32-byte digest
# carries 2 unused padding bits, so 4 of the 64 possible replacement
# characters there decode to BYTE-IDENTICAL data — flipping the last
# character is tamper-evident only ~94% of the time. The first character of
# a base64 segment has no such slack, so flipping it is unconditionally
# reliable. (This is not hypothetical: an earlier version of this script used
# a last-character flip and occasionally failed to tamper anything at all.)
PREFIX="${ORDER%.*}"          # "v1.<payload>"
SIG="${ORDER##*.}"            # the signature segment
FIRST="${SIG:0:1}"
if [ "$FIRST" = "a" ]; then NEW="b"; else NEW="a"; fi
TAMPERED="${PREFIX}.${NEW}${SIG:1}"

banner "view_order with ONE character flipped in a real token"
echo "original : ...${ORDER: -12}"
echo "tampered : ...${TAMPERED: -12}"
expect 'isError: true, "signature does not match — it was not issued by this
        server, or has been altered". hmac.compare_digest caught it, and the
        message deliberately does NOT say which byte was wrong or why — only
        that verification failed. This is the tamper-evidence topic 06'"'"'s
        cursor never had, because there was nothing there worth protecting.'
exec ./call.sh view_order "{\"order\": \"${TAMPERED}\"}" 703
