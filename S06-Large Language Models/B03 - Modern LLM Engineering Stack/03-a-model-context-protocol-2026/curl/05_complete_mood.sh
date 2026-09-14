#!/usr/bin/env bash
# Completing a PROMPT argument.
#   bash curl/05_complete_mood.sh s
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
TYPED="${1:-s}"
expect "the moods starting with '${TYPED}'. With 's': sad, sleepy, sweet-tooth.
        Plus total and hasMore — fill those in honestly. A client that thinks it
        received the full list will stop asking."
exec ./complete.sh prompt order_for_me mood "$TYPED"
