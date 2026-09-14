# ============================================================
# TESTS: cafe_mcp.pagination — the cursor, with no MCP in sight
# REF:   notes/06-pagination.md
# ============================================================
#
# No server, no transport, no async. The cursor is pure data manipulation, so it
# is tested at the speed of a function call — same discipline as menu.py and
# render.py.
#
# Run: pytest tests/test_pagination.py -v

import pytest

from cafe_mcp import pagination


def test_encode_then_decode_round_trips():
    assert pagination.decode_cursor(pagination.encode_cursor(0)) == 0
    assert pagination.decode_cursor(pagination.encode_cursor(5)) == 5
    assert pagination.decode_cursor(pagination.encode_cursor(12345)) == 12345


def test_cursor_carries_a_version_tag():
    """v1.<token> — versioned so a future encoding change can be rejected cleanly
    rather than silently misread as the current format."""
    assert pagination.encode_cursor(5).startswith("v1.")


def test_cursor_is_decodable_by_hand_not_secret():
    """Opaque is a contract about USAGE (never construct or edit one), not a claim
    about secrecy. Anyone with base64 -d can read this. Contrast the order token
    in topic 07, which really is signed."""
    import base64
    import json

    token = pagination.encode_cursor(5).removeprefix("v1.")
    padded = token + "=" * (-len(token) % 4)
    assert json.loads(base64.urlsafe_b64decode(padded)) == {"offset": 5}


@pytest.mark.parametrize(
    "bad_cursor",
    [
        "garbage-not-base64-at-all!!",
        "v2.eyJvZmZzZXQiOjV9",  # wrong version
        "v1.",  # empty token
        "",  # empty string entirely
    ],
)
def test_malformed_cursor_raises_cursor_error(bad_cursor: str):
    with pytest.raises(pagination.CursorError):
        pagination.decode_cursor(bad_cursor)


def test_wellformed_base64_with_wrong_payload_shape_still_raises():
    """The base64 can decode fine and the JSON can parse fine, and it can STILL be
    an invalid cursor — e.g. no 'offset' key, or an offset that is not a
    non-negative integer. All of those are CursorError, not a crash."""
    import base64
    import json

    def make(payload) -> str:
        token = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"v1.{token}"

    with pytest.raises(pagination.CursorError):
        pagination.decode_cursor(make({"not_offset": 5}))
    with pytest.raises(pagination.CursorError):
        pagination.decode_cursor(make({"offset": -1}))
    with pytest.raises(pagination.CursorError):
        pagination.decode_cursor(make({"offset": "five"}))
    with pytest.raises(pagination.CursorError):
        pagination.decode_cursor(make({"offset": True}))  # bool is not an int here
    with pytest.raises(pagination.CursorError):
        pagination.decode_cursor(make([1, 2, 3]))  # not even an object


def test_page_first_call_needs_no_cursor():
    items = list(range(12))
    chunk, next_cursor = pagination.page(items, None, 5)
    assert chunk == [0, 1, 2, 3, 4]
    assert next_cursor is not None


def test_page_walks_to_the_end():
    """The only correct termination signal is next_cursor is None — never page
    length, because a page can legitimately divide evenly and still not be last."""
    items = list(range(12))
    seen = []
    cursor = None
    for _ in range(10):  # generous bound so a bug can't infinite-loop the suite
        chunk, cursor = pagination.page(items, cursor, 5)
        seen.extend(chunk)
        if cursor is None:
            break
    assert seen == items


def test_page_of_exactly_limit_size_is_not_necessarily_last():
    """12 drinks, page size 6 -> two pages of exactly 6. The second call must still
    happen; a client that stops because "the page was full size" would silently
    drop drinks 6-11 in a menu sized differently from this one."""
    items = list(range(12))
    chunk, next_cursor = pagination.page(items, None, 6)
    assert len(chunk) == 6
    assert next_cursor is not None  # NOT the last page, despite being full-size

    chunk2, next_cursor2 = pagination.page(items, next_cursor, 6)
    assert len(chunk2) == 6
    assert next_cursor2 is None  # NOW it is exhausted


def test_page_empty_list():
    chunk, next_cursor = pagination.page([], None, 5)
    assert chunk == []
    assert next_cursor is None


def test_page_cursor_past_the_end():
    """A stale or hand-edited cursor pointing past the data should not crash —
    it is simply an empty page with no next_cursor."""
    items = list(range(12))
    cursor = pagination.encode_cursor(1000)
    chunk, next_cursor = pagination.page(items, cursor, 5)
    assert chunk == []
    assert next_cursor is None
