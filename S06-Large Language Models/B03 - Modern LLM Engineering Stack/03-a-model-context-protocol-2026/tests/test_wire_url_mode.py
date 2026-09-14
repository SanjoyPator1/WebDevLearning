# ============================================================
# TESTS: MRTR in URL mode — the payment link and its receipt
# REF:   notes/09-url-mode.md
# ============================================================
#
# Run: pytest tests/test_wire_url_mode.py -v

import t09_url_mode
from wire import result, rpc, wire_client

from cafe_mcp import orders, tokens

SERVER = t09_url_mode.mcp


def _cart(*, slug: str = "latte", size: str = "L", qty: int = 2) -> str:
    return orders.sign_cart([{"slug": slug, "size": size, "qty": qty}], ttl_s=900)


async def _round1(client, order: str) -> dict:
    return await result(
        client, "tools/call", {"name": "pay_for_order", "arguments": {"order": order}}
    )


async def _pay(client, url: str) -> str:
    """Follow a pay URL and 'click Pay'. Returns the minted receipt."""
    response = await client.post(url)
    assert response.status_code == 200
    return response.json()["receipt"]


async def test_round_one_returns_a_url_not_a_form():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)

    assert round1["resultType"] == "input_required"
    params = round1["inputRequests"]["pay"]["params"]
    assert params["mode"] == "url"
    assert "requestedSchema" not in params
    assert params["url"].startswith("http://127.0.0.1:3010/pay/")
    assert "$8.60" in params["message"]
    assert "card details" in params["message"]


async def test_the_pay_page_get_is_a_plain_html_page_not_mcp():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        url = round1["inputRequests"]["pay"]["params"]["url"]
        path = url.removeprefix("http://127.0.0.1:3010")

        response = await client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "$8.60" in response.text


async def test_posting_to_the_pay_page_mints_a_receipt():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        url = round1["inputRequests"]["pay"]["params"]["url"]
        path = url.removeprefix("http://127.0.0.1:3010")

        response = await client.post(path)

    assert response.status_code == 200
    body = response.json()
    assert body["paid"] is True
    assert body["total"] == 8.60
    # The receipt is itself a genuine, independently-verifiable signed token.
    receipt_body = tokens.verify("payment_receipt", body["receipt"])
    assert receipt_body["order"] == order
    assert receipt_body["total"] == 8.60


async def test_round_two_with_a_genuine_receipt_completes_the_payment():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        url = round1["inputRequests"]["pay"]["params"]["url"]
        receipt = await _pay(client, url.removeprefix("http://127.0.0.1:3010"))

        round2 = await result(
            client,
            "tools/call",
            {
                "name": "pay_for_order",
                "arguments": {"order": order},
                "inputResponses": {"pay": {"action": "accept", "content": {"receipt": receipt}}},
                "requestState": round1["requestState"],
            },
            req_id=2,
        )

    assert round2["isError"] is False
    placed = round2["structuredContent"]["result"]
    assert placed["ticket"].startswith("P-")
    assert placed["total"] == 8.60


async def test_accept_with_no_receipt_at_all_is_refused():
    """THE central lesson: action == "accept" alone proves nothing. Anything
    sending this retry could claim acceptance without the human ever visiting
    the link."""
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)

        message = await rpc(
            client,
            "tools/call",
            {
                "name": "pay_for_order",
                "arguments": {"order": order},
                "inputResponses": {"pay": {"action": "accept"}},
                "requestState": round1["requestState"],
            },
            req_id=2,
        )

    assert message["error"]["code"] == -32602
    assert "No payment receipt" in message["error"]["message"]


async def test_a_genuine_receipt_for_a_different_order_is_refused():
    """A REAL receipt, genuinely signed by this server — just for a different,
    cheaper order. Signature verification alone would let this through;
    checking the receipt's own content (which order, which total) is what
    catches it. Same lesson as topic 08's price-drift check, new context."""
    order_a = _cart(slug="latte", size="L", qty=2)
    order_b = _cart(slug="espresso", size="S", qty=1)

    async with wire_client(SERVER) as client:
        round1_a = await _round1(client, order_a)

        round1_b = await _round1(client, order_b)
        url_b = round1_b["inputRequests"]["pay"]["params"]["url"]
        receipt_b = await _pay(client, url_b.removeprefix("http://127.0.0.1:3010"))

        # Try to pay for A using B's genuine receipt.
        message = await rpc(
            client,
            "tools/call",
            {
                "name": "pay_for_order",
                "arguments": {"order": order_a},
                "inputResponses": {"pay": {"action": "accept", "content": {"receipt": receipt_b}}},
                "requestState": round1_a["requestState"],
            },
            req_id=3,
        )

    assert message["result"]["isError"] is True
    assert "does not match the current order" in message["result"]["content"][0]["text"]


async def test_expired_pay_nonce_is_refused_with_a_clean_message():
    """The payment link itself expires. Mint a `pay_nonce` token with ttl_s=0
    directly — the nonce is just a signed token like any other in this
    folder, so this needs no server-timing tricks, only the token's own
    expiry check."""
    import time

    order = _cart()
    expired_nonce = tokens.sign("pay_nonce", {"order": order, "total": 8.60}, ttl_s=0)
    time.sleep(0.05)

    async with wire_client(SERVER) as client:
        response = await client.get(f"/pay/{expired_nonce}")

    assert response.status_code == 400
    assert "not valid" in response.text.lower() or "expired" in response.text.lower()


async def test_declining_payment_is_a_successful_complete_result():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)

        round2 = await result(
            client,
            "tools/call",
            {
                "name": "pay_for_order",
                "arguments": {"order": order},
                "inputResponses": {"pay": {"action": "decline"}},
                "requestState": round1["requestState"],
            },
            req_id=2,
        )

    assert round2["isError"] is False
    assert round2["structuredContent"]["result"]["placed"] is False


async def test_pay_for_order_is_marked_destructive():
    async with wire_client(SERVER) as client:
        listing = await result(client, "tools/list")

    tool = next(t for t in listing["tools"] if t["name"] == "pay_for_order")
    assert tool["annotations"]["readOnlyHint"] is False
    assert tool["annotations"]["destructiveHint"] is True
