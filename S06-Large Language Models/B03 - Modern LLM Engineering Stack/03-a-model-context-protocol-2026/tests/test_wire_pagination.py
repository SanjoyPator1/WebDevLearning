# ============================================================
# TESTS: pagination, on the raw wire
# REF:   notes/06-pagination.md
# ============================================================
#
# Run: pytest tests/test_wire_pagination.py -v

import t06_pagination
from wire import call_tool, wire_client

SERVER = t06_pagination.mcp


async def test_first_page_needs_no_cursor():
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "list_drinks", {})

    assert result["isError"] is False
    page = result["structuredContent"]
    assert [d["slug"] for d in page["drinks"]] == [
        "espresso",
        "macchiato",
        "cortado",
        "flat-white",
        "latte",
    ]
    assert page["next_cursor"] is not None


async def test_walking_next_cursor_covers_the_whole_menu_with_no_repeats():
    """The only client-visible contract: keep calling with the returned cursor
    until next_cursor is null, and you will see every drink exactly once."""
    seen: list[str] = []
    cursor = None
    async with wire_client(SERVER) as client:
        for _ in range(10):  # generous bound; a real bug would exceed it
            result = await call_tool(client, "list_drinks", {"cursor": cursor} if cursor else {})
            page = result["structuredContent"]
            seen.extend(d["slug"] for d in page["drinks"])
            cursor = page["next_cursor"]
            if cursor is None:
                break

    assert len(seen) == len(set(seen)) == 12
    assert cursor is None


async def test_a_full_size_page_is_not_necessarily_the_last_one():
    """12 drinks, limit=6 -> two pages of exactly 6. Stopping because a page was
    "full" rather than checking next_cursor would silently drop the second half."""
    async with wire_client(SERVER) as client:
        first = await call_tool(client, "list_drinks", {"limit": 6})
        assert len(first["structuredContent"]["drinks"]) == 6
        assert first["structuredContent"]["next_cursor"] is not None  # NOT last

        second = await call_tool(
            client, "list_drinks", {"limit": 6, "cursor": first["structuredContent"]["next_cursor"]}
        )
        assert len(second["structuredContent"]["drinks"]) == 6
        assert second["structuredContent"]["next_cursor"] is None  # NOW exhausted


async def test_malformed_cursor_is_a_tool_error_naming_the_only_recovery():
    """A bad cursor is opaque, so unlike a bad slug there is no "try a real one" —
    the model cannot reason its way to a valid cursor. The message must say
    exactly one thing: start over with no cursor."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "list_drinks", {"cursor": "not-a-real-cursor"})

    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert "no `cursor` argument" in text or "no cursor argument" in text.replace(
        "no `cursor`", "no cursor"
    )
    assert "start" in text.lower()


async def test_cursor_from_a_different_limit_still_works():
    """The cursor encodes a POSITION, not a page size. Fetching page 1 at limit=5
    and then continuing at limit=3 should not skip or repeat anything — proving the
    cursor and the page size are genuinely independent."""
    async with wire_client(SERVER) as client:
        first = await call_tool(client, "list_drinks", {"limit": 5})
        cursor = first["structuredContent"]["next_cursor"]

        second = await call_tool(client, "list_drinks", {"limit": 3, "cursor": cursor})

    assert [d["slug"] for d in second["structuredContent"]["drinks"]] == [
        "cappuccino",
        "americano",
        "mocha",
    ]


async def test_limit_is_schema_constrained_not_runtime_checked():
    """ge=1, le=10 on the Field means an out-of-range limit never reaches the
    function body — same pattern as topic 03's quote(qty)."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "list_drinks", {"limit": 999})

    assert result["isError"] is True
    assert "less than or equal to 10" in result["content"][0]["text"]
