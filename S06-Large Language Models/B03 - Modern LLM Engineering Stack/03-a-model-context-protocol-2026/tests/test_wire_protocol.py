import pytest
import t03_calls_and_errors  # noqa: F401  (imported for its module-level `mcp`)
from wire import VERSION, call_tool, meta, parse_jsonrpc, rpc, wire_client

SERVER = t03_calls_and_errors.mcp


# --- Topic 01: framing and discovery ---


async def test_discover_advertises_the_modern_revision():
    async with wire_client(SERVER) as client:
        result = (await rpc(client, "server/discover", {}))["result"]

    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == [VERSION]
    assert "tools" in result["capabilities"]
    # No handshake means the server must identify itself on every single result.
    assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "cafe-mcp"


async def test_tools_list_succeeds_with_no_version_header():
    """THE stateless_http=True REGRESSION GUARD.

    A client that sends no `MCP-Protocol-Version` header must still be served. With
    `stateless_http=False` this same request gets HTTP 400 "Bad Request: Missing
    session ID" — the client did nothing wrong, the server was in the wrong era.

    If this test ever fails, check that flag before anything else.
    """
    async with wire_client(SERVER) as client:
        message = await rpc(client, "tools/list", {}, version=None, send_method_header=False)

    assert "result" in message, message
    assert message["result"]["tools"]


async def test_no_version_header_gets_the_legacy_result_shape():
    """The SDK is dual-era: your headers decide which revision you are speaking,
    and you get that revision's result SHAPE. Without modern headers you do not get
    a degraded 2026 result — you get a 2025-11-25 one."""
    async with wire_client(SERVER) as client:
        legacy = (
            await rpc(
                client, "tools/list", None, version=None, send_method_header=False, with_meta=False
            )
        )["result"]
        modern = (await rpc(client, "tools/list", {}))["result"]

    # All three of these were introduced at 2026-07-28.
    assert "resultType" not in legacy
    assert "ttlMs" not in legacy
    assert "_meta" not in legacy

    assert modern["resultType"] == "complete"
    assert "ttlMs" in modern
    assert "io.modelcontextprotocol/serverInfo" in modern["_meta"]


async def test_meta_must_carry_client_capabilities():
    """`clientCapabilities` is a MUST even when empty; `{}` is the right value for a
    client that can do nothing special. `clientInfo` is only a SHOULD."""
    async with wire_client(SERVER) as client:
        message = await rpc(client, "tools/list", None, with_meta=False)

    error = message["error"]
    assert error["code"] == -32602
    assert "clientCapabilities" in error["message"]


async def test_meta_at_the_top_level_is_rejected():
    """The classic hand-rolled-client bug: `_meta` belongs inside `params`."""
    async with wire_client(SERVER) as client:
        response = await client.post(
            "/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": VERSION,
                "Mcp-Method": "tools/list",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
                "_meta": meta(),  # WRONG LEVEL, on purpose
            },
        )
        message = parse_jsonrpc(response)[-1]

    assert message["error"]["code"] == -32602


async def test_method_header_must_match_the_body():
    """-32020 HeaderMismatch. The header exists so a proxy can route without
    parsing the body; if the two disagree, the proxy's view of the request is a
    lie, so the request is refused."""
    async with wire_client(SERVER) as client:
        response = await client.post(
            "/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": VERSION,
                "Mcp-Method": "tools/call",  # body says tools/list
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {"_meta": meta()},
            },
        )
        message = parse_jsonrpc(response)[-1]

    assert message["error"]["code"] == -32020


async def test_name_header_must_match_the_body():
    async with wire_client(SERVER) as client:
        response = await client.post(
            "/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": VERSION,
                "Mcp-Method": "tools/call",
                "Mcp-Name": "list_drinks",  # body says get_drink
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "get_drink", "arguments": {"slug": "latte"}, "_meta": meta()},
            },
        )
        message = parse_jsonrpc(response)[-1]

    assert message["error"]["code"] == -32020


async def test_unknown_protocol_version_returns_32022_with_the_supported_list():
    """Version negotiation with no handshake to negotiate in: the rejection hands
    you the list of versions that WOULD work, so recovery is one retry. Topic 12."""
    async with wire_client(SERVER) as client:
        message = await rpc(
            client, "tools/list", {"_meta": meta(version="2099-01-01")}, version="2099-01-01"
        )

    error = message["error"]
    assert error["code"] == -32022
    assert error["data"]["supported"] == [VERSION]


async def test_a_known_older_version_is_served_rather_than_refused():
    """The surprising half of the above: an OLD but known version is not an error.
    The server serves that revision's shape. Only an UNKNOWN version gets -32022."""
    async with wire_client(SERVER) as client:
        message = await rpc(
            client, "tools/list", {"_meta": meta(version="2025-06-18")}, version="2025-06-18"
        )

    assert "result" in message, message
    assert "resultType" not in message["result"]  # legacy shape


async def test_ping_was_removed():
    """`ping` is gone at 2026-07-28. Liveness goes to an ordinary HTTP route, which
    is why every server here mounts /healthz."""
    async with wire_client(SERVER) as client:
        message = await rpc(client, "ping", {})

    assert message["error"]["code"] == -32601


async def test_healthz_is_not_an_mcp_request():
    async with wire_client(SERVER) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# --- Topic 02: tools/list ---


async def test_tools_list_carries_the_cache_hint():
    """ttlMs and cacheScope are REQUIRED on list results at 2026-07-28. "public" is
    a judgement: this menu is byte-identical for every caller."""
    async with wire_client(SERVER) as client:
        result = (await rpc(client, "tools/list", {}))["result"]

    assert result["ttlMs"] == 300_000
    assert result["cacheScope"] == "public"


async def test_tool_order_is_deterministic():
    """The spec's SHOULD. It is about the model's prompt cache, so it is about the
    bill. The SDK preserves registration order — this guards it."""
    async with wire_client(SERVER) as client:
        first = (await rpc(client, "tools/list", {}))["result"]
        second = (await rpc(client, "tools/list", {}, req_id=2))["result"]

    names = [t["name"] for t in first["tools"]]
    assert names == [t["name"] for t in second["tools"]]
    assert names == ["list_drinks", "get_drink", "quote", "broken_on_purpose"]


async def test_docstrings_and_field_descriptions_reach_the_model():
    """Both of these are prompt text. If either goes missing, the model's behaviour
    changes and nothing else breaks — which is why it is worth a test."""
    async with wire_client(SERVER) as client:
        result = (await rpc(client, "tools/list", {}))["result"]

    tools = {t["name"]: t for t in result["tools"]}

    # The docstring became the tool description.
    assert "call `list_drinks` first rather than guessing" in tools["get_drink"]["description"]

    # Annotated[..., Field(description=...)] became the ARGUMENT description.
    slug_schema = tools["get_drink"]["inputSchema"]["properties"]["slug"]
    assert "Not the display name" in slug_schema["description"]


async def test_annotations_are_published():
    async with wire_client(SERVER) as client:
        result = (await rpc(client, "tools/list", {}))["result"]

    quote_tool = next(t for t in result["tools"] if t["name"] == "quote")
    assert quote_tool["annotations"]["readOnlyHint"] is True
    assert quote_tool["annotations"]["title"] == "Price a drink"


async def test_fixed_constraints_are_pushed_into_the_schema():
    """`Literal` becomes an enum, `Field(ge=, le=)` becomes minimum/maximum. The
    model reads them up front instead of discovering them by failing."""
    async with wire_client(SERVER) as client:
        result = (await rpc(client, "tools/list", {}))["result"]

    props = next(t for t in result["tools"] if t["name"] == "quote")["inputSchema"]["properties"]
    assert props["size"]["enum"] == ["S", "M", "L"]
    assert props["qty"]["minimum"] == 1
    assert props["qty"]["maximum"] == 10


# --- Topic 03: tools/call and the three kinds of failure ---


async def test_successful_call_returns_both_content_and_structured_content():
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "quote", {"slug": "latte", "size": "L", "qty": 2})

    assert result["resultType"] == "complete"
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"  # for the model
    assert result["structuredContent"]["total"] == 8.60  # for code


async def test_schema_violation_message_is_disclosed():
    """Kind 1. The SDK reveals its OWN validator's wording, because it wrote it and
    knows it contains only the schema and the offending value."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "quote", {"slug": "latte", "size": "XL"})

    assert result["isError"] is True
    assert "'S', 'M' or 'L'" in result["content"][0]["text"]


async def test_tool_error_message_survives_and_is_actionable():
    """Kind 2. ToolError asserts "this message is safe and useful", so it is
    forwarded. The three tests a good message must pass: name the problem, quote
    the bad value, say what to do next."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "quote", {"slug": "espresso", "size": "L"})

    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert "Espresso is not sold in size 'L'" in text  # names it, quotes it
    assert "It comes in: S, M" in text  # says what to do next


async def test_bare_exception_message_is_withheld():
    """Kind 3, and the reason ToolError exists. The KeyError's text — which carries
    a (fake) internal path — must NOT reach the model. It goes to stderr instead.

    If this test ever fails, someone has added a blanket
    `except Exception: raise ToolError(str(e))`, which defeats the disclosure
    boundary everywhere at once."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "broken_on_purpose", {"slug": "latte"})

    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert text == "Error executing tool broken_on_purpose"
    assert "internal-menu-cache" not in text
    assert "/var/lib" not in text


async def test_tool_failure_is_a_result_not_a_jsonrpc_error():
    """The most-misread thing in MCP. A tool failing is a NORMAL outcome of a
    working protocol, addressed to the MODEL — so it arrives inside `result`.
    A JSON-RPC `error` means the CLIENT got the request wrong."""
    async with wire_client(SERVER) as client:
        message = await rpc(
            client,
            "tools/call",
            {"name": "quote", "arguments": {"slug": "espresso", "size": "L"}},
        )

    assert "error" not in message
    assert message["result"]["isError"] is True


async def test_unknown_tool_is_a_result_with_is_error():
    """Not -32601. Apply the test: who can fix this? The model can re-read
    tools/list, so the failure belongs where the model will see it."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "not_a_tool", {})

    assert result["isError"] is True
    assert "not_a_tool" in result["content"][0]["text"]


@pytest.mark.parametrize(
    ("slug", "size", "sold"),
    [
        ("latte", "L", True),
        ("espresso", "L", False),
        ("cold-brew", "S", False),
        ("cold-brew", "M", True),
        ("creme-brulee-latte", "S", False),
    ],
)
async def test_size_availability_matches_the_menu_data(slug: str, size: str, sold: bool):
    """The tool layer and the menu data must agree. The irregular drinks exist
    precisely so this has something to catch."""
    async with wire_client(SERVER) as client:
        result = await call_tool(client, "quote", {"slug": slug, "size": size})

    assert result["isError"] is not sold
