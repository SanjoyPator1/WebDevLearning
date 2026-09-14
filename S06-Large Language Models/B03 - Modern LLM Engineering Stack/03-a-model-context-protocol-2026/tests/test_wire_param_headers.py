# ============================================================
# TESTS: Mcp-Param-* header mirroring
# REF:   notes/13-param-headers.md
# ============================================================
#
# Run: pytest tests/test_wire_param_headers.py -v

import t13_param_headers
from mcp.shared.inbound import encode_header_value
from wire import VERSION, meta, parse_jsonrpc, rpc, wire_client

SERVER = t13_param_headers.mcp


async def _announce(client, name: str, *, header_value: str | None, req_id: int = 1):
    """Build tools/call by hand so the Mcp-Param-DrinkName header can be set,
    omitted, or deliberately wrong — wire.rpc() derives it automatically from
    the body and does not let us break that on purpose."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": VERSION,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "announce_drink",
    }
    if header_value is not None:
        headers["Mcp-Param-DrinkName"] = header_value
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": "announce_drink", "arguments": {"name": name}, "_meta": meta()},
    }
    response = await client.post("/mcp", headers=headers, json=body)
    return parse_jsonrpc(response)[-1]


async def test_x_mcp_header_is_published_on_the_annotated_argument():
    async with wire_client(SERVER) as client:
        listing = await rpc(client, "tools/list", {})

    tool = next(t for t in listing["result"]["tools"] if t["name"] == "announce_drink")
    schema = tool["inputSchema"]["properties"]["name"]
    assert schema["x-mcp-header"] == "DrinkName"


async def test_a_plain_ascii_name_needs_no_encoding_at_all():
    async with wire_client(SERVER) as client:
        message = await _announce(client, "Latte", header_value="Latte")

    assert message["result"]["isError"] is False
    assert "Latte" in message["result"]["content"][0]["text"]


async def test_a_non_ascii_name_must_travel_through_the_base64_sentinel():
    """An HTTP header field cannot carry raw non-ASCII bytes at all — this is
    not an SDK choice, it is the transport's own limit. encode_header_value
    wraps anything that would not survive the round trip in the
    =?base64?...?= sentinel; a raw UTF-8 header value is simply not a legal
    thing to send."""
    name = "Crème Brûlée Latte"
    encoded = encode_header_value(name)
    assert encoded.startswith("=?base64?")
    assert encoded != name  # confirms encoding actually happened, not a no-op

    async with wire_client(SERVER) as client:
        message = await _announce(client, name, header_value=encoded)

    assert message["result"]["isError"] is False
    assert name in message["result"]["content"][0]["text"]


async def test_mismatched_header_and_body_is_rejected_before_the_tool_runs():
    async with wire_client(SERVER) as client:
        message = await _announce(client, "Espresso", header_value="Latte")

    assert message["error"]["code"] == -32020
    assert "does not match" in message["error"]["message"]


async def test_missing_header_with_a_present_body_argument_is_rejected():
    async with wire_client(SERVER) as client:
        message = await _announce(client, "Latte", header_value=None)

    assert message["error"]["code"] == -32020
    assert "is missing" in message["error"]["message"]


async def test_announcing_an_unknown_name_is_a_clean_tool_error():
    """The header check only cares that header and body agree — it says
    nothing about whether the drink is real. That is the tool's own job."""
    async with wire_client(SERVER) as client:
        message = await _announce(client, "Unicorn Frappe", header_value="Unicorn Frappe")

    assert message["result"]["isError"] is True
    assert "No drink is named" in message["result"]["content"][0]["text"]


async def test_x_mcp_header_as_a_bool_is_published_but_silently_inert():
    """The single gotcha this whole topic exists to warn about. A schema
    annotated with `x-mcp-header: True` (the wrong type — it must be a
    string token) is NOT rejected: tools/list publishes it verbatim, exactly
    as written. But `find_invalid_x_mcp_header` flags it as malformed, and
    `validate_mcp_param_headers` responds to a malformed schema by skipping
    header validation FOR THAT TOOL ENTIRELY — no error, no warning, the
    Mcp-Param-* mechanism just never engages. A gateway built to route on
    that header would see nothing to route on, and nothing anywhere would
    say why."""
    from mcp.server import MCPServer
    from mcp_types import ToolAnnotations

    broken = MCPServer(name="broken-header-probe", version="1")

    @broken.tool(annotations=ToolAnnotations(title="x", read_only_hint=True))
    def bad_tool(drink: str) -> str:
        return drink

    # Patch in a bool where a string token belongs, bypassing the type hint
    # (Field's json_schema_extra is just a dict at runtime). `.parameters` is
    # the actual mutable JSON Schema dict the SDK publishes and validates
    # against — found by inspecting `dir(tool_obj)` rather than guessed.
    tool_obj = broken._tool_manager.get_tool("bad_tool")
    tool_obj.parameters["properties"]["drink"]["x-mcp-header"] = True

    async with wire_client(broken) as client:
        listing = await rpc(client, "tools/list", {})
        schema = listing["result"]["tools"][0]["inputSchema"]["properties"]["drink"]
        assert schema["x-mcp-header"] is True  # published verbatim, not rejected

        # A header that would have been valid for a CORRECTLY-typed annotation
        # is simply ignored — the call succeeds regardless of what this header
        # says, because validation for this tool never engages at all.
        response = await client.post(
            "/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": VERSION,
                "Mcp-Method": "tools/call",
                "Mcp-Name": "bad_tool",
                "Mcp-Param-Whatever": "this-is-never-checked",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "bad_tool", "arguments": {"drink": "Latte"}, "_meta": meta()},
            },
        )
        message = parse_jsonrpc(response)[-1]

    assert message["result"]["isError"] is False
