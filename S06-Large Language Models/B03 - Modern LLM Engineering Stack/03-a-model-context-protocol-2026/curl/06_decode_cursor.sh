#!/usr/bin/env bash
# Prove "opaque" does not mean "secret". Decode a cursor by hand with base64 -d.
#
#   bash curl/06_decode_cursor.sh 'v1.eyJvZmZzZXQiOjV9'
set -euo pipefail
CURSOR="${1:?usage: 06_decode_cursor.sh <cursor>}"
TOKEN="${CURSOR#v1.}"
echo "--------------------------------------------------------------------"
echo "cursor:      $CURSOR"
echo "version tag: v1"
echo "token part:  $TOKEN"
echo "--------------------------------------------------------------------"
echo -n "$TOKEN" | python3 -c "
import sys, base64
t = sys.stdin.read()
pad = '=' * (-len(t) % 4)
print(base64.urlsafe_b64decode(t + pad).decode())
"
echo "--------------------------------------------------------------------"
echo "Plain JSON: {\"offset\": N}. Nothing hidden, nothing signed."
echo "A client MUST still treat it as opaque and never construct one by hand —"
echo "the encoding could change tomorrow. Opaque is a contract about USAGE,"
echo "not a claim about secrecy. Contrast topic 07, where the payload is"
echo "actually worth protecting and the token really is signed."
echo "--------------------------------------------------------------------"
