#!/usr/bin/env bash
# Visit the payment link — first as a GET (what a human sees), then a POST
# ("the human clicked Pay"). NOT an MCP request: no headers, no envelope, no
# JSON-RPC. This is a PLAIN WEB PAGE.
#   bash curl/09_visit_pay_page.sh 'http://127.0.0.1:3010/pay/v1.eyJ...'
set -euo pipefail
ORDER_URL="${1:?usage: 09_visit_pay_page.sh <url from round 1>}"

echo "--------------------------------------------------------------------"
echo "GET  (what a human would see)"
echo "--------------------------------------------------------------------"
curl -sS "$ORDER_URL"
echo
echo
echo "--------------------------------------------------------------------"
echo "POST (\"clicking Pay\") -> mints the ONLY proof round 2 will accept"
echo "--------------------------------------------------------------------"
curl -sS -X POST "$ORDER_URL" | python3 -m json.tool
echo
echo "COPY the \"receipt\" field for 09_pay_round2.sh."
