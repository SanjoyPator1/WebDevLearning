#!/usr/bin/env bash
# Call list_drinks and look at the two forms the answer takes.
set -euo pipefail
cd "$(dirname "$0")"
source ./_common.sh
exec ./call.sh list_drinks '{}' 11
