#!/usr/bin/env bash
# This server has no add_to_order — it demonstrates MRTR on top of an order
# token, not how to build one (topic 07 already covered that). This script mints
# a real, validly-signed token straight from cafe_mcp so you have something to
# feed to place_order, without switching servers.
set -euo pipefail
cd "$(dirname "$0")"
../.venv/bin/python -c "
from cafe_mcp import orders
token = orders.sign_cart([{'slug': 'latte', 'size': 'L', 'qty': 2}], ttl_s=900)
print(token)
"
