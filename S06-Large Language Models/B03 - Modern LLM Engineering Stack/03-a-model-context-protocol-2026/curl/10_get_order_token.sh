#!/usr/bin/env bash
# This server has no add_to_order/pay_for_order — it demonstrates progress on
# top of an order token, not how to build or pay for one. Mints a token
# directly from cafe_mcp so you have something to brew.
set -euo pipefail
cd "$(dirname "$0")"
../.venv/bin/python -c "
from cafe_mcp import orders
token = orders.sign_cart(
    [{'slug': 'latte', 'size': 'L', 'qty': 1}, {'slug': 'espresso', 'size': 'S', 'qty': 1}],
    ttl_s=900,
)
print(token)
"
