#!/usr/bin/env bash
# The happy path, for contrast with everything else in topic 03.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'isError: false, and BOTH a text `content` block (the JSON, for the model to
        read) and `structuredContent` (the same data typed, for code). One `return`
        statement in Python produced both.'
exec ./call.sh quote '{"slug": "latte", "size": "L", "qty": 2}' 30
