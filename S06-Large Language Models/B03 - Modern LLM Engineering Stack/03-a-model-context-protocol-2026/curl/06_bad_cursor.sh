#!/usr/bin/env bash
# A malformed cursor, on purpose.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'isError: true, and the message says exactly ONE thing to do:
        "call list_drinks again with no cursor argument to start from the
        beginning". Unlike a bad slug, there is no "try a real one instead" —
        cursors are opaque, so a model that gets one wrong cannot reason its way
        to a correct one. The only recovery is starting over, so that is the only
        thing the message offers.'
exec ./call.sh list_drinks '{"cursor": "garbage-not-a-cursor"}' 602
