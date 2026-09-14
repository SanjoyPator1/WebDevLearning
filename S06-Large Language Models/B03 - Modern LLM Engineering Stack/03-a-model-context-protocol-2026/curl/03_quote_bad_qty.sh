#!/usr/bin/env bash
# Field(ge=1, le=10) became minimum/maximum in the schema.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'isError: true — "Input should be less than or equal to 10".
        Another constraint pushed into the schema rather than into code. Do that
        whenever the legal range is FIXED: the model reads it up front instead of
        discovering it by failing.'
exec ./call.sh quote '{"slug": "latte", "size": "M", "qty": 50}' 33
