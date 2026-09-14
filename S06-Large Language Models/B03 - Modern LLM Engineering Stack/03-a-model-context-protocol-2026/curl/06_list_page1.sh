#!/usr/bin/env bash
# The first page. No cursor argument at all — that is how you ask for page one.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect '5 drinks (espresso through latte), and a next_cursor that looks like
        "v1.eyJvZmZzZXQiOjV9". Copy that whole string for the next script.

        Note what is NOT true: the page is not short, so you cannot yet tell from
        the page alone whether more exist. next_cursor being non-null is the only
        signal that matters.'
exec ./call.sh list_drinks '{}' 600
