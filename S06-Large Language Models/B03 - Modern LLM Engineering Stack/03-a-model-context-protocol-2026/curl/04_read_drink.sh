#!/usr/bin/env bash
# Reading THROUGH a template, and then failing through one.
#
#   bash curl/04_read_drink.sh flat-white       -> works
#   bash curl/04_read_drink.sh creme-brulee-latte -> non-ASCII in the document
#   bash curl/04_read_drink.sh no-such-drink    -> a REAL JSON-RPC error
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
SLUG="${1:-flat-white}"
expect "contents[0].uri is the RESOLVED uri (cafe://drinks/${SLUG}), not the
        template. mimeType is application/json.

        With a bad slug you get something you have not seen before in this folder:
        a genuine JSON-RPC \"error\" envelope.
            {\"error\": {\"code\": -32602, \"message\": \"There is no drink with slug ...\",
                       \"data\": {\"uri\": \"cafe://drinks/no-such-drink\"}}}
        NOT a result with isError: true. See 04_tool_vs_resource.sh for why."
exec ./read.sh "cafe://drinks/${SLUG}" 205
