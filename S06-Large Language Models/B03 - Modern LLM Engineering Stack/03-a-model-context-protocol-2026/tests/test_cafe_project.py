# ============================================================
# TESTS: the assembled project, through the OFFICIAL SDK client
# REF:   notes/15-the-project.md
# ============================================================
#
# Run: pytest tests/test_cafe_project.py -v
#
# Every other test file in this project drives the server by hand
# (tests/wire.py's `rpc`/`call_tool`, or a real socket for a stream that
# never ends). This file is the first to use `mcp.client.Client` at all —
# on purpose, to verify the SAME claims this topic's notes chapter makes
# about what the SDK automates, as assertions rather than narration.
#
# `Client(server)` — an MCPServer object, not a URL — uses an in-memory
# transport with no real socket, the fastest of the three ways `Client`
# can connect (the other two: a URL string over real HTTP, or
# StdioServerParameters over a subprocess's stdio).

import cafe_project
import mcp_types as types
import pytest
from mcp.client import Client
from mcp.shared.exceptions import MCPError


async def _auto_confirm(context, params: types.ElicitRequestParams) -> types.ElicitResult:
    return types.ElicitResult(action="accept", content={"name": "Sanjoy", "confirm": True})


async def _auto_decline(context, params: types.ElicitRequestParams) -> types.ElicitResult:
    return types.ElicitResult(action="decline")


async def test_list_tools_has_one_tool_per_topic_it_was_assembled_from():
    async with Client(cafe_project.mcp) as client:
        listing = await client.list_tools()
    assert sorted(t.name for t in listing.tools) == [
        "add_to_order",
        "announce_drink",
        "brew",
        "get_drink",
        "list_drinks",
        "place_order",
        "sell_out",
        "un_sell_out",
        "view_order",
    ]


async def test_the_drink_template_is_absent_from_resources_list():
    """Reconfirms topic 04's own finding, this time through the SDK client:
    a resource TEMPLATE (`cafe://drinks/{slug}`) never appears in
    `resources/list` — only `resources/templates/list` carries it. A client
    that only ever calls `list_resources()` will believe this server has
    exactly one resource."""
    async with Client(cafe_project.mcp) as client:
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
    assert [r.name for r in resources.resources] == ["menu"]
    assert [t.name for t in templates.resource_templates] == ["drink_detail"]


async def test_place_order_with_no_elicitation_callback_raises():
    """The SDK will not invent an answer to a confirmation question. Without
    a callback, `call_tool` raises the moment `place_order` returns
    `input_required` — there is no silent default accept."""
    async with Client(cafe_project.mcp) as client:
        added = await client.call_tool("add_to_order", {"slug": "latte", "size": "M", "qty": 1})
        token = added.structured_content["order"]
        with pytest.raises(MCPError, match="Elicitation not supported"):
            await client.call_tool("place_order", {"order": token})


async def test_place_order_drives_both_mrtr_rounds_through_one_call():
    """THE central claim of this topic, as an assertion: one `call_tool`
    await, with an `elicitation_callback` supplied, produces the FINAL
    committed order — `input_required`, `requestState`, and the round-2
    retry never surface to the caller at all."""
    async with Client(cafe_project.mcp, elicitation_callback=_auto_confirm) as client:
        added = await client.call_tool("add_to_order", {"slug": "latte", "size": "M", "qty": 2})
        token = added.structured_content["order"]
        placed = await client.call_tool("place_order", {"order": token})

    assert placed.is_error is False
    result = placed.structured_content["result"]
    assert result["name"] == "Sanjoy"
    assert result["total"] == added.structured_content["total"]
    assert result["ticket"].startswith("A-")


async def test_declining_via_the_callback_is_a_normal_successful_result():
    """A decline is a successful `call_tool` — `is_error` stays False — not
    an exception, matching topic 08's own "declining is a normal outcome"
    finding, now reconfirmed through the SDK client."""
    async with Client(cafe_project.mcp, elicitation_callback=_auto_decline) as client:
        added = await client.call_tool("add_to_order", {"slug": "espresso", "size": "S", "qty": 1})
        token = added.structured_content["order"]
        placed = await client.call_tool("place_order", {"order": token})

    assert placed.is_error is False
    assert placed.structured_content["result"]["reason"] == "customer declined"


async def test_brew_progress_callback_fires_once_per_step_in_order():
    """`progress_callback` must be a coroutine function — `ProgressFnT` is
    awaited internally by the SDK's dispatcher, wrapped in a shield that logs
    (rather than raises) if the callback itself misbehaves. A plain `def`
    here would still be CALLED correctly but its `None` return value would
    then fail to await, logged once per event as "progress callback raised"
    — a real mistake caught while building `solved/sdk_client.py`, not a
    hypothetical one."""
    events: list[tuple[float, float | None, str | None]] = []

    async def on_progress(progress, total, message):
        events.append((progress, total, message))

    async with Client(cafe_project.mcp, elicitation_callback=_auto_confirm) as client:
        added = await client.call_tool("add_to_order", {"slug": "latte", "size": "M", "qty": 1})
        token = added.structured_content["order"]
        await client.call_tool("place_order", {"order": token})
        brewed = await client.call_tool("brew", {"order": token}, progress_callback=on_progress)

    assert brewed.is_error is False
    assert brewed.structured_content["ready"] is True
    assert len(events) == 5  # one line, five BREW_STEPS
    assert [p for p, _, _ in events] == [1, 2, 3, 4, 5]
    assert all(total == 5 for _, total, _ in events)
