#!/usr/bin/env bash
# Copy an exercise's template/ into solution/ so you can start working.
# Refuses to run if solution/ already exists, so your work is never overwritten.
#
# Usage: scripts/start_exercise.sh projects/<phase folder>/<exercise>
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 projects/<phase folder>/<exercise>" >&2
  exit 1
fi

dir="${1%/}"

if [ ! -d "$dir/template" ]; then
  echo "Error: no template/ folder in $dir" >&2
  exit 1
fi

if [ -e "$dir/solution" ]; then
  echo "Error: $dir/solution already exists. Not overwriting your work." >&2
  exit 1
fi

rsync -a \
  --exclude node_modules \
  --exclude dist \
  --exclude coverage \
  "$dir/template/" "$dir/solution/"

echo "Created $dir/solution from template."
echo "Next: cd $dir/solution && pnpm install && pnpm test"
