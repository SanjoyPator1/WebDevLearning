# ============================================================
# TESTS: MRTR — input_required, requestState, and the automatic binding
# REF:   notes/08-mrtr.md
# ============================================================
#
# Run: pytest tests/test_wire_mrtr.py -v
#
# These tests exist to PROVE a claim the chapter makes: the SDK's
# RequestStateBoundary binds requestState to the exact method, tool name and a
# digest of `arguments`, automatically, on every retry — with no code of ours
# involved. Several tests here deliberately try to break that and confirm they
# cannot.

from unittest.mock import patch

import t08_mrtr
from wire import result, rpc, wire_client

from cafe_mcp import orders

SERVER = t08_mrtr.mcp


def _cart(*, slug: str = "latte", size: str = "L", qty: int = 2, ttl_s: int = 900) -> str:
    return orders.sign_cart([{"slug": slug, "size": size, "qty": qty}], ttl_s=ttl_s)


async def _round1(client, order: str) -> dict:
    return await result(
        client, "tools/call", {"name": "place_order", "arguments": {"order": order}}
    )


async def test_round_one_asks_for_confirmation():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)

    assert round1["resultType"] == "input_required"
    assert "requestState" in round1
    message = round1["inputRequests"]["confirm"]["params"]["message"]
    assert "Latte" in message
    assert "$8.60" in message


async def test_round_two_with_matching_arguments_completes_the_order():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]

        round2 = await result(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order},  # SAME order token
                "inputResponses": {
                    "confirm": {"action": "accept", "content": {"name": "Sanjoy", "confirm": True}}
                },
                "requestState": state,
            },
            req_id=2,
        )

    assert round2["isError"] is False
    placed = round2["structuredContent"]["result"]
    assert placed["ticket"].startswith("A-")
    assert placed["name"] == "Sanjoy"
    assert placed["total"] == 8.60


async def test_declining_is_a_successful_complete_result_not_an_error():
    """Declining is a NORMAL outcome — the tool did its job and got an answer.
    resultType stays "complete", isError stays False."""
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]

        round2 = await result(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order},
                "inputResponses": {"confirm": {"action": "decline"}},
                "requestState": state,
            },
            req_id=2,
        )

    assert round2["isError"] is False
    assert round2["resultType"] == "complete"
    assert round2["structuredContent"]["result"] == {
        "placed": False,
        "reason": "customer declined",
    }


async def test_cancel_is_also_a_successful_complete_result():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]

        round2 = await result(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order},
                "inputResponses": {"confirm": {"action": "cancel"}},
                "requestState": state,
            },
            req_id=2,
        )

    assert round2["structuredContent"]["result"]["reason"] == "customer cancelled"


async def test_swapping_the_order_token_on_retry_is_rejected_automatically():
    """THE central lesson. A completely different, VALIDLY SIGNED order token,
    replayed against round 1's requestState. This is not tampering — the token
    is real — it simply does not match what round 1 was asked to confirm.

    The SDK's RequestStateBoundary computes a digest of `arguments` on every
    retry and compares it to the digest sealed at round 1. No code in
    place_order runs; the request is refused before the tool is ever entered.
    """
    round1_order = _cart(slug="latte", size="L", qty=2)
    different_order = _cart(slug="mocha", size="L", qty=5)

    async with wire_client(SERVER) as client:
        round1 = await _round1(client, round1_order)
        state = round1["requestState"]

        message = await rpc(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": different_order},  # SWAPPED
                "inputResponses": {
                    "confirm": {
                        "action": "accept",
                        "content": {"name": "Attacker", "confirm": True},
                    }
                },
                "requestState": state,
            },
            req_id=2,
        )

    assert "error" in message
    assert message["error"]["code"] == -32602
    assert message["error"]["message"] == "Invalid or expired requestState"
    # The generic message never distinguishes "wrong arguments" from "expired"
    # or "tampered" — see notes/08-mrtr.md on why that vagueness is deliberate.


async def test_any_argument_change_on_retry_is_rejected_not_only_the_order():
    """The binding covers the WHOLE arguments object, not a field the tool
    author chose. There is only one argument here (`order`), so this doubles as
    confirmation that even a single-argument tool gets full coverage — but the
    mechanism is general: add a second argument to place_order later and it
    would be covered too, with no code change required."""
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]

        # Same order token, but wrapped in extra whitespace / a trivially
        # different (still equal after JSON parsing) argument shape would still
        # digest identically — so instead we prove the NEGATIVE: change one
        # character of the token itself, which is still "the order argument
        # changed" from the binding's point of view even though it is also an
        # invalid token by topic 07's own rules.
        tampered_order = order[:-1] + ("x" if order[-1] != "x" else "y")

        message = await rpc(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": tampered_order},
                "inputResponses": {
                    "confirm": {"action": "accept", "content": {"name": "X", "confirm": True}}
                },
                "requestState": state,
            },
            req_id=2,
        )

    assert message["error"]["code"] == -32602
    assert message["error"]["message"] == "Invalid or expired requestState"


async def test_a_second_round_one_call_produces_an_unusable_requestState_for_the_first():
    """Two independent orders, two independent confirmations in flight at once.
    Cart A's requestState must not satisfy cart B's retry, even though both are
    legitimately-issued, currently-valid requestState tokens from the SAME
    server."""
    order_a = _cart(slug="latte", size="L", qty=1)
    order_b = _cart(slug="espresso", size="S", qty=1)

    async with wire_client(SERVER) as client:
        round1_a = await _round1(client, order_a)
        # Both carts have their own in-flight confirmation at once.
        assert (await _round1(client, order_b))["resultType"] == "input_required"

        # Try to confirm B using A's requestState.
        message = await rpc(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order_b},
                "inputResponses": {
                    "confirm": {"action": "accept", "content": {"name": "X", "confirm": True}}
                },
                "requestState": round1_a["requestState"],
            },
            req_id=3,
        )

    assert message["error"]["code"] == -32602


async def test_expired_request_state_is_rejected():
    """A short-TTL server, isolated from SERVER so this test cannot affect the
    900-second default the rest of this file relies on."""
    import time

    from mcp.server import MCPServer
    from mcp.server.request_state import RequestStateSecurity

    short_ttl_server = MCPServer(
        name="short-ttl-probe",
        version="1",
        request_state_security=RequestStateSecurity(keys=[b"test-key-" + b"0" * 24], ttl=0.3),
    )
    short_ttl_server.add_tool(t08_mrtr.place_order)

    order = _cart()
    async with wire_client(short_ttl_server) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]

        time.sleep(0.6)  # cross the 0.3s TTL

        message = await rpc(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order},
                "inputResponses": {
                    "confirm": {"action": "accept", "content": {"name": "X", "confirm": True}}
                },
                "requestState": state,
            },
            req_id=2,
        )

    assert message["error"]["code"] == -32602
    assert message["error"]["message"] == "Invalid or expired requestState"


async def test_price_drift_between_rounds_is_caught_by_request_state_not_by_binding():
    """The one thing the automatic argument-binding CANNOT catch: the order
    token is genuinely unchanged between rounds, but the MENU PRICE moved
    underneath it. request_state carries the total the customer was quoted at
    round 1 specifically so round 2 can detect this — the SDK has no way to
    know a price quote needs to survive the round trip; that is domain logic,
    and it is exactly what request_state is FOR.
    """
    order = _cart(slug="latte", size="L", qty=2)

    from cafe_mcp import menu as menu_mod

    real_price_of = menu_mod.price_of

    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]
        assert "$8.60" in round1["inputRequests"]["confirm"]["params"]["message"]

        def bumped(slug: str, size: str):
            if slug == "latte" and size == "L":
                return real_price_of(slug, size) + 1.00
            return real_price_of(slug, size)

        with patch.object(menu_mod, "price_of", bumped):
            round2 = await result(
                client,
                "tools/call",
                {
                    "name": "place_order",
                    "arguments": {"order": order},
                    "inputResponses": {
                        "confirm": {"action": "accept", "content": {"name": "X", "confirm": True}}
                    },
                    "requestState": state,
                },
                req_id=2,
            )

    assert round2["isError"] is True
    text = round2["content"][0]["text"]
    assert "price changed" in text
    assert "$8.60" in text
    assert "$10.60" in text


async def test_a_new_jsonrpc_id_is_required_on_the_retry_but_that_alone_is_not_the_link():
    """The mechanism connecting round 1 and round 2 is requestState, not the
    JSON-RPC id — ids only have to be unique among in-flight requests on the
    connection. This test uses a DIFFERENT id on purpose (2, not 1) and still
    succeeds, which is the point: nothing about id continuity is load-bearing."""
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]

        round2 = await result(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order},
                "inputResponses": {
                    "confirm": {"action": "accept", "content": {"name": "X", "confirm": True}}
                },
                "requestState": state,
            },
            req_id=999,  # deliberately unrelated to round 1's id
        )

    assert round2["isError"] is False


async def test_missing_name_in_the_confirmation_is_a_clean_mcperror():
    order = _cart()
    async with wire_client(SERVER) as client:
        round1 = await _round1(client, order)
        state = round1["requestState"]

        message = await rpc(
            client,
            "tools/call",
            {
                "name": "place_order",
                "arguments": {"order": order},
                "inputResponses": {"confirm": {"action": "accept", "content": {"confirm": True}}},
                "requestState": state,
            },
            req_id=2,
        )

    assert message["error"]["code"] == -32602
    assert "name for the cup is required" in message["error"]["message"]


async def test_empty_cart_cannot_be_placed():
    empty_order = orders.sign_cart([], ttl_s=900)
    async with wire_client(SERVER) as client:
        message = await rpc(
            client, "tools/call", {"name": "place_order", "arguments": {"order": empty_order}}
        )

    assert message["result"]["isError"] is True
    assert "no items" in message["result"]["content"][0]["text"]


async def test_invalid_order_token_is_a_tool_error_not_a_crash():
    async with wire_client(SERVER) as client:
        message = await rpc(
            client,
            "tools/call",
            {"name": "place_order", "arguments": {"order": "not-a-real-token"}},
        )

    assert message["result"]["isError"] is True
    assert "not valid" in message["result"]["content"][0]["text"]


async def test_output_schema_wraps_the_union_return_under_a_result_key():
    """A tool whose return type is a Union of two BaseModel arms (excluding the
    InputRequiredResult arm, which the SDK strips from outputSchema entirely)
    publishes `{"result": <anyOf>}`, not a flat object. structuredContent
    mirrors that wrapper on the wire. Worth pinning: it is easy to assume a
    Union return behaves like a single model's flat shape, and it does not."""
    async with wire_client(SERVER) as client:
        listing = await result(client, "tools/list")

    tool = next(t for t in listing["tools"] if t["name"] == "place_order")
    schema = tool["outputSchema"]
    assert schema["required"] == ["result"]
    assert "result" in schema["properties"]
    arms = {ref["$ref"].rsplit("/", 1)[-1] for ref in schema["properties"]["result"]["anyOf"]}
    assert arms == {"OrderPlaced", "OrderNotPlaced"}
    # InputRequiredResult must NOT appear — it is a protocol-level result type,
    # not part of this tool's own "complete" output contract.
    assert "InputRequiredResult" not in str(schema)


async def test_place_order_is_marked_destructive_not_read_only():
    """The first genuinely destructive tool in this folder: it commits money.
    Getting this annotation right is what tells a host to prompt a human before
    running it silently."""
    async with wire_client(SERVER) as client:
        listing = await result(client, "tools/list")

    tool = next(t for t in listing["tools"] if t["name"] == "place_order")
    assert tool["annotations"]["readOnlyHint"] is False
    assert tool["annotations"]["destructiveHint"] is True
    assert tool["annotations"]["idempotentHint"] is False
