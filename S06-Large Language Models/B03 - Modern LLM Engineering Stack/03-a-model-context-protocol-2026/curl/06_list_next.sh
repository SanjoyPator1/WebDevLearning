#!/usr/bin/env bash
# The next page, using a cursor you copy from the previous script's output.
#   bash curl/06_list_next.sh 'v1.eyJvZmZzZXQiOjV9'
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
CURSOR="${1:?usage: 06_list_next.sh <cursor>   (copy next_cursor from 06_list_page1.sh)}"
expect "the NEXT 5 drinks, continuing where the last page left off, with a new
        next_cursor for page 3. Try passing a cursor with one character changed —
        watch curl/06_bad_cursor.sh for what that looks like."
exec ./call.sh list_drinks "{\"cursor\": \"${CURSOR}\"}" 601
