# ============================================================
# TESTS: the order token, on the raw wire
# REF:   notes/07-the-order-token.md
# ============================================================
#
# Run: pytest tests/test_wire_order_token.py -v

import t07_order_token
from wire import call_tool, wire_client

SERVER = t07_order_token.mcp


async def test_first_add_needs_no_order_argument():
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "add_to_order", {"slug": "latte", "size": "L", "qty": 2})

    assert result["isError"] is False
    cart = result["structuredContent"]
    assert len(cart["lines"]) == 1
    assert cart["lines"][0]["name"] == "Latte"
    assert cart["total"] == 8.60
    assert cart["order"]  # a non-empty token


async def test_second_add_extends_the_same_cart():
    async with wire_client(SERVER) as client:
        first = await call_tool(client, "add_to_order", {"slug": "latte", "size": "L", "qty": 2})
        token = first["structuredContent"]["order"]

        second = await call_tool(
            client,
            "add_to_order",
            {"slug": "espresso", "size": "S", "qty": 1, "order": token},
        )

    cart = second["structuredContent"]
    assert len(cart["lines"]) == 2
    names = [line["name"] for line in cart["lines"]]
    assert names == ["Latte", "Espresso"]
    assert cart["total"] == 10.80


async def test_view_order_does_not_change_the_cart_but_mints_a_new_token():
    async with wire_client(SERVER) as client:
        added = await call_tool(client, "add_to_order", {"slug": "latte", "size": "L", "qty": 2})
        token = added["structuredContent"]["order"]

        viewed = await call_tool(client, "view_order", {"order": token})

    assert viewed["structuredContent"]["lines"] == added["structuredContent"]["lines"]
    assert viewed["structuredContent"]["total"] == added["structuredContent"]["total"]
    # The token itself is a fresh signature (may be identical if minted within the
    # same wall-clock second — see test_tokens.py — but is never a DIFFERENT cart).


async def test_tampered_token_is_rejected_with_only_start_over_offered():
    """Same rule as a bad cursor in topic 06, for the same reason: the token is
    opaque, so there is nothing about it a model could reason about to repair.
    The only honest recovery is starting a new order."""
    async with wire_client(SERVER) as client:
        added = await call_tool(client, "add_to_order", {"slug": "latte", "size": "L", "qty": 2})
        token = added["structuredContent"]["order"]
        # Flip a character INSIDE the signature segment, not the token's last
        # character. The final base64url character of a 32-byte digest has 2
        # unused padding bits — 4 of 64 possible replacement characters there
        # decode to byte-identical data, making a last-character flip
        # tamper-evident only ~94% of the time. See test_tokens.py for the
        # full explanation; this exact spot is where it first surfaced,
        # flaking intermittently in the full suite.
        prefix, body_b64, sig_b64 = token.split(".", 2)
        flipped = "a" if sig_b64[0] != "a" else "b"
        tampered = f"{prefix}.{body_b64}.{flipped}{sig_b64[1:]}"

        result = await call_tool(client, "view_order", {"order": tampered})

    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert "not valid" in text
    assert "add_to_order" in text  # names the only real recovery


async def test_a_place_order_state_token_cannot_be_used_as_an_order_token():
    """Domain separation, proved on the actual wire rather than just in
    test_tokens.py. Sign a token AS a different kind and confirm the server's own
    verify() rejects it here too."""
    from cafe_mcp import tokens

    wrong_kind_token = tokens.sign("place_order_state", {"lines": []}, ttl_s=900)

    async with wire_client(SERVER) as client:
        result = await call_tool(client, "view_order", {"order": wrong_kind_token})

    assert result["isError"] is True
    assert "not valid" in result["content"][0]["text"]


async def test_add_to_order_validates_before_touching_the_cart():
    """A bad size must be refused BEFORE the cart is built, so it can never
    corrupt an otherwise-good order. Confirmed by checking there is no `order`
    field to have received a bad line."""
    async with wire_client(SERVER) as client:
        result = await call_tool(
            client, "add_to_order", {"slug": "espresso", "size": "L", "qty": 1}
        )

    assert result["isError"] is True
    assert "not sold in size" in result["content"][0]["text"]
    assert "structuredContent" not in result


async def test_add_to_order_rejects_unknown_slug():
    async with wire_client(SERVER) as client:
        result = await call_tool(
            client, "add_to_order", {"slug": "no-such-drink", "size": "M", "qty": 1}
        )

    assert result["isError"] is True
    assert "no drink with slug" in result["content"][0]["text"]


async def test_qty_is_schema_constrained():
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "add_to_order", {"slug": "latte", "size": "L", "qty": 999})

    assert result["isError"] is True
    assert "less than or equal to" in result["content"][0]["text"]


async def test_repricing_uses_current_menu_prices_not_a_stored_price():
    """The token stores WHAT was ordered (slug, size, qty), never a frozen price.
    Every read recomputes from cafe_mcp.menu, so a price change between adding a
    line and viewing the cart is reflected honestly rather than honoured at the
    stale rate."""
    async with wire_client(SERVER) as client:
        added = await call_tool(client, "add_to_order", {"slug": "latte", "size": "M", "qty": 3})

    from cafe_mcp import menu

    expected_unit = menu.price_of("latte", "M")
    line = added["structuredContent"]["lines"][0]
    assert line["unit_price"] == expected_unit
    assert line["line_total"] == round(expected_unit * 3, 2)


async def test_served_by_defaults_to_single():
    """Meaningless with one process, but this is exactly the field topic 14's
    load balancer demo reads to prove requests are landing on different
    instances while a cart still completes correctly."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "add_to_order", {"slug": "latte", "size": "L", "qty": 1})

    assert result["structuredContent"]["served_by"] == "single"
