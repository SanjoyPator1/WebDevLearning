# ============================================================
# TESTS: progress notifications on the response stream
# REF:   notes/10-progress-and-streaming.md
# ============================================================
#
# Run: pytest tests/test_wire_progress.py -v
#
# These tests build requests by hand (not through wire.rpc/result, which only
# return the LAST message) because the whole subject here is the notifications
# that arrive BEFORE the final result on the same stream.

import os

# Set BEFORE importing t10_progress — STEP_DELAY_S is read at module import
# time. 0.8s (the real, human-facing pacing) times the ~40 total steps across
# this file's tests would cost over 30 seconds; the progress MECHANICS being
# tested do not depend on the delay's size, only on a delay existing between
# report_progress calls, so a tiny one is exactly as good a test.
os.environ.setdefault("CAFE_MCP_BREW_STEP_DELAY_S", "0.01")

import t10_progress  # noqa: E402
from wire import VERSION, meta, parse_jsonrpc, wire_client  # noqa: E402

from cafe_mcp import orders  # noqa: E402

SERVER = t10_progress.mcp


def _cart(*lines: tuple[str, str, int]) -> str:
    return orders.sign_cart(
        [{"slug": slug, "size": size, "qty": qty} for slug, size, qty in lines], ttl_s=900
    )


async def _brew(client, order: str, *, progress_token: str | None, req_id: int = 1):
    """Build a tools/call for brew by hand and return every SSE message (or the
    single JSON message) — unlike wire.rpc, this keeps ALL events, not just
    the last."""
    envelope_meta = meta()
    if progress_token is not None:
        envelope_meta["progressToken"] = progress_token
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": VERSION,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "brew",
    }
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": "brew", "arguments": {"order": order}, "_meta": envelope_meta},
    }
    response = await client.post("/mcp", headers=headers, json=body)
    return response, parse_jsonrpc(response)


async def test_no_progress_token_gets_a_plain_json_result_with_no_notifications():
    """report_progress calls happen either way — this proves they produce
    NOTHING to send when the client never asked for them."""
    order = _cart(("latte", "L", 1))
    async with wire_client(SERVER) as client:
        response, messages = await _brew(client, order, progress_token=None)

    assert response.headers["content-type"].startswith("application/json")
    assert len(messages) == 1
    assert messages[0]["result"]["structuredContent"]["ready"] is True


async def test_progress_token_produces_one_notification_per_step_then_the_result():
    """One drink -> exactly 5 steps -> 5 notifications, THEN the final result
    as the last message on the stream. Same response, multiple events."""
    order = _cart(("latte", "L", 1))
    async with wire_client(SERVER) as client:
        response, messages = await _brew(client, order, progress_token="tok-1")

    assert response.headers["content-type"].startswith("text/event-stream")
    assert len(messages) == 6  # 5 progress notifications + 1 final result

    notifications = messages[:5]
    for note in notifications:
        assert note["method"] == "notifications/progress"
        assert note["params"]["progressToken"] == "tok-1"
        assert note["params"]["total"] == 5

    progresses = [note["params"]["progress"] for note in notifications]
    assert progresses == [1, 2, 3, 4, 5]  # strictly increasing, no gaps, no repeats

    final = messages[-1]
    assert final["id"] == 1
    assert "method" not in final  # the final message is a RESULT, not a notification
    assert final["result"]["structuredContent"]["ready"] is True


async def test_progress_counts_across_every_line_not_reset_per_drink():
    """Two drinks -> 10 steps total (5 per cup), counting 1..10 straight
    through — NOT restarting at 1 for the second drink. A client tracking a
    single progress bar needs monotonic progress across the whole call."""
    order = _cart(("latte", "L", 1), ("espresso", "S", 1))
    async with wire_client(SERVER) as client:
        response, messages = await _brew(client, order, progress_token="tok-2")

    notifications = [m for m in messages if m.get("method") == "notifications/progress"]
    assert len(notifications) == 10

    progresses = [n["params"]["progress"] for n in notifications]
    assert progresses == list(range(1, 11))
    for note in notifications:
        assert note["params"]["total"] == 10

    # Messages name which DRINK each step belongs to.
    assert "Latte" in notifications[0]["params"]["message"]
    assert "Espresso" in notifications[5]["params"]["message"]


async def test_progress_messages_name_the_step_and_the_drink():
    """qty does not multiply the brew steps — one pass per distinct LINE, not
    per cup — so qty=2 here still produces 5 steps, same as qty=1."""
    order = _cart(("latte", "L", 2))
    async with wire_client(SERVER) as client:
        _, messages = await _brew(client, order, progress_token="tok-3")

    first_message = messages[0]["params"]["message"]
    assert "grinding" in first_message
    assert "Latte" in first_message
    assert "(L)" in first_message

    last_notification = messages[4]["params"]["message"]  # step 5 of 5, index 4
    assert "pouring" in last_notification


async def test_brewing_an_invalid_order_token_is_a_clean_tool_error():
    async with wire_client(SERVER) as client:
        _, messages = await _brew(client, "not-a-real-token", progress_token=None)

    result = messages[0]["result"]
    assert result["isError"] is True
    assert "Can't brew this order" in result["content"][0]["text"]


async def test_brewing_an_empty_cart_is_refused():
    empty_order = orders.sign_cart([], ttl_s=900)
    async with wire_client(SERVER) as client:
        _, messages = await _brew(client, empty_order, progress_token=None)

    result = messages[0]["result"]
    assert result["isError"] is True
    assert "no items" in result["content"][0]["text"]


async def test_brew_is_marked_not_read_only_but_not_destructive():
    """Unlike place_order/pay_for_order, brewing a drink loses nothing if
    called twice — worst case, a second batch of the same drinks — so it is
    NOT destructive, even though it clearly is not read-only either."""
    from wire import result

    async with wire_client(SERVER) as client:
        listing = await result(client, "tools/list")

    tool = next(t for t in listing["tools"] if t["name"] == "brew")
    assert tool["annotations"]["readOnlyHint"] is False
    assert tool["annotations"]["destructiveHint"] is False
    assert tool["annotations"]["idempotentHint"] is False
