#!/usr/bin/env bash
# The schema catches it, before your code runs.
#
# `size` is typed Literal["S","M","L"], which becomes a JSON Schema `enum`. The
# model can read the legal values in tools/list, so it should never send "XL" —
# and if it does, the request never reaches your function.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
expect 'isError: true, with the pydantic message passed through IN FULL:
          "Input should be S, M or L [type=literal_error, input_value=XL]"
        Contrast with 03_broken.sh, where the message is withheld. The SDK reveals
        its OWN validator wording because it knows that text is safe; it withholds
        YOUR exception because it cannot know that.'
exec ./call.sh quote '{"slug": "latte", "size": "XL", "qty": 1}' 32
