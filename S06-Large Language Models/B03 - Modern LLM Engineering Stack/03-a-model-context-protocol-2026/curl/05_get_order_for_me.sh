#!/usr/bin/env bash
# The prompt a user would invoke as a slash command.
#
#   bash curl/05_get_order_for_me.sh sleepy
#   bash curl/05_get_order_for_me.sh sleepy true     <- dairy-free
#   bash curl/05_get_order_for_me.sh grumpy          <- a clean -32602
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
MOOD="${1:-sleepy}"
DAIRY="${2:-false}"
expect 'TWO messages, and look at the first one carefully:

          messages[0].content.type == "resource"

        The menu is attached as an EMBEDDED RESOURCE, not pasted into a string.
        That is better than pasting: the client learns the URI the text came from,
        so it can cache it, deduplicate it against a copy it already holds, or show
        a human where the data came from.

        messages[1] is the instruction the SERVER AUTHOR wrote. Read it and notice
        how much steering it does — one recommendation, a size, one sentence of
        reasoning, no alternatives. The user typed one word; the server supplied
        all of that. Holding the wording is the real power of a prompt.

        With dairy-free true, messages[0] is a DIFFERENT uri
        (cafe://menu/dairy-free) and messages[1] gains a constraint sentence.

        With mood=grumpy: a clean -32602 naming the allowed values.'
exec ./get_prompt.sh order_for_me "{\"mood\": \"${MOOD}\", \"dairy_free\": \"${DAIRY}\"}" 302
