#!/usr/bin/env bash
# get_drink, with a slug you choose.
#
#   bash curl/02_get_drink.sh flat-white     -> works
#   bash curl/02_get_drink.sh espresso       -> note available_sizes has no "L"
#   bash curl/02_get_drink.sh no-such-drink  -> the BAD error path, on purpose
#
# That last one is the lesson. topic 02's get_drink raises a bare ValueError, and
# what the model receives back is:
#
#     "Error executing tool get_drink"
#
# The message is withheld. The model learns that something failed and nothing
# about what or how to recover, so it either gives up or retries the identical
# call. Topic 03 fixes this with ToolError.
#
# Contrast with a SCHEMA failure — try:
#     bash curl/call.sh get_drink '{"slug": 123}'
# There the message comes through in full, because pydantic validation happens
# before your code runs and the SDK trusts its own validator's wording.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
SLUG="${1:-flat-white}"
exec ./call.sh get_drink "{\"slug\": \"${SLUG}\"}" 12
