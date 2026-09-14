#!/usr/bin/env bash
# A narrower document over the same data — the argument for URI addressing.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'a much shorter markdown document: four drinks instead of twelve.

        This is why resources are addressed by URI rather than being one big blob.
        A host that knows the customer avoids dairy attaches this instead of the
        full menu, and spends roughly a quarter of the tokens with nothing to
        filter out. The MODEL made no decision here — the HOST chose the URI.'
exec ./read.sh cafe://menu/dairy-free 204
