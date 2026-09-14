# ============================================================
# TESTS: resources, prompts and completion, on the raw wire
# REF:   notes/04-resources.md, notes/05-prompts-and-completion.md
# ============================================================
#
# Same discipline as test_wire_protocol.py: no SDK client anywhere. Every request
# is built by hand so the header and envelope requirements are actually exercised.
#
# Run: pytest tests/test_wire_resources_prompts.py -v

import json

import pytest
import t04_resources
import t05_prompts
from wire import error, result, rpc, wire_client

RESOURCES = t04_resources.mcp
PROMPTS = t05_prompts.mcp


# --- Topic 04: resources ---


async def test_resources_list_has_only_static_resources():
    """Templates are NOT here. They live in resources/templates/list, and a client
    that calls only this RPC will never learn the template exists."""
    async with wire_client(RESOURCES) as client:
        listing = await result(client, "resources/list")

    uris = [entry["uri"] for entry in listing["resources"]]
    assert uris == ["cafe://menu", "cafe://menu/dairy-free"]
    assert not any("{" in uri for uri in uris), "a template leaked into resources/list"


async def test_templates_list_uses_uri_template_not_uri():
    """A template entry carries `uriTemplate`, with the placeholder intact. Getting
    this key wrong is a common client bug."""
    async with wire_client(RESOURCES) as client:
        listing = await result(client, "resources/templates/list")

    templates = listing["resourceTemplates"]
    assert len(templates) == 1
    assert templates[0]["uriTemplate"] == "cafe://drinks/{slug}"
    assert "uri" not in templates[0]


async def test_resource_metadata_reaches_the_client():
    """Docstring -> description, same rule as tools. A resource description answers
    a different question though: "when should this be in my context?" rather than
    "when should I call this?"."""
    async with wire_client(RESOURCES) as client:
        listing = await result(client, "resources/list")

    menu_entry = next(e for e in listing["resources"] if e["uri"] == "cafe://menu")
    assert menu_entry["mimeType"] == "text/markdown"
    assert menu_entry["title"] == "The café menu"
    assert "Read this once at the start of a conversation" in menu_entry["description"]


async def test_resources_read_returns_a_contents_list():
    """`contents` is a LIST even for one document — one URI may legitimately return
    several pieces, each with its own uri and mimeType."""
    async with wire_client(RESOURCES) as client:
        read = await result(client, "resources/read", {"uri": "cafe://menu"})

    assert isinstance(read["contents"], list)
    entry = read["contents"][0]
    assert entry["uri"] == "cafe://menu"
    assert entry["mimeType"] == "text/markdown"
    assert entry["text"].startswith("# The Café Menu")


async def test_resources_read_is_cacheable_and_that_is_the_point():
    """A resource read is a document fetch — the thing HTTP caching was invented
    for — so this is the highest-value cache hint on the server. It is also what
    makes a shared proxy in front of three instances worth having."""
    async with wire_client(RESOURCES) as client:
        read = await result(client, "resources/read", {"uri": "cafe://menu"})

    assert read["ttlMs"] == 600_000
    assert read["cacheScope"] == "public"


async def test_reading_through_a_template_resolves_the_placeholder():
    """contents[0].uri is the RESOLVED uri, not the template."""
    async with wire_client(RESOURCES) as client:
        read = await result(client, "resources/read", {"uri": "cafe://drinks/flat-white"})

    entry = read["contents"][0]
    assert entry["uri"] == "cafe://drinks/flat-white"
    assert json.loads(entry["text"])["available_sizes"] == ["S", "M", "L"]


async def test_non_ascii_survives_a_resource_read():
    """Crème Brûlée all the way to the wire. Topic 13 depends on this name."""
    async with wire_client(RESOURCES) as client:
        read = await result(client, "resources/read", {"uri": "cafe://drinks/creme-brulee-latte"})

    assert json.loads(read["contents"][0]["text"])["name"] == "Crème Brûlée Latte"


async def test_resource_not_found_is_a_jsonrpc_error_with_32602():
    """THE topic-04 rule, and it is the OPPOSITE of the topic-03 rule.

    Also note the code: -32602, not the bespoke -32002 it used to be. Missing
    resources were renumbered at 2026-07-28 on the grounds that a URI which does
    not exist is a bad argument, not a special condition.
    """
    async with wire_client(RESOURCES) as client:
        err = await error(client, "resources/read", {"uri": "cafe://drinks/no-such-drink"})

    assert err["code"] == -32602
    assert "no drink with slug 'no-such-drink'" in err["message"]
    assert err["data"]["uri"] == "cafe://drinks/no-such-drink"


async def test_unmatched_uri_is_rejected_by_the_sdk_before_our_code_runs():
    """A URI matching no registered pattern never reaches a handler, so the wording
    is the SDK's rather than ours."""
    async with wire_client(RESOURCES) as client:
        err = await error(client, "resources/read", {"uri": "cafe://nonsense"})

    assert err["code"] == -32602
    assert "Unknown resource" in err["message"]


async def test_same_missing_drink_reported_two_different_ways():
    """The comparison that topic 04 exists for. Apply the test — who can fix this?

      A tool call was chosen by the MODEL   -> failure goes in `result`
      A resource URI was chosen by the CLIENT -> failure goes in `error`

    Same question, opposite answers, because a different party is holding the wheel.
    """
    async with wire_client(RESOURCES) as client:
        # As a RESOURCE: a real JSON-RPC error envelope.
        as_resource = await rpc(client, "resources/read", {"uri": "cafe://drinks/no-such-drink"})
        # As a TOOL: a successful envelope carrying isError.
        as_tool = await rpc(
            client, "tools/call", {"name": "get_drink", "arguments": {"slug": "no-such-drink"}}
        )

    assert "error" in as_resource and "result" not in as_resource
    assert "result" in as_tool and "error" not in as_tool
    assert as_tool["result"]["isError"] is True

    # Both messages survived, because both used the right exception type.
    assert "no drink with slug" in as_resource["error"]["message"]
    assert "no drink with slug" in as_tool["result"]["content"][0]["text"]


# --- Topic 05: prompts ---


async def test_prompts_list_publishes_argument_descriptions():
    """The most commonly skipped thing in MCP prompts. A host renders a slash
    command from these, for a HUMAN — without descriptions it shows a bare argument
    name and the command is unusable."""
    async with wire_client(PROMPTS) as client:
        listing = await result(client, "prompts/list")

    prompts = {entry["name"]: entry for entry in listing["prompts"]}
    assert set(prompts) == {"order_for_me", "explain_drink", "compare_drinks"}

    arguments = {a["name"]: a for a in prompts["order_for_me"]["arguments"]}
    assert arguments["mood"]["required"] is True
    assert arguments["dairy_free"]["required"] is False  # it has a Python default
    for argument in arguments.values():
        assert argument.get("description"), f"{argument['name']} has no description"


async def test_prompts_list_is_cacheable_but_prompts_get_is_not():
    """`prompts/get` renders against arguments, so there is nothing stable to cache.
    Same reasoning as tools/call. Verify against the SDK's own list:
      python -c "from mcp_types.methods import CACHEABLE_METHODS as C; print(sorted(C))"
    """
    async with wire_client(PROMPTS) as client:
        listing = await result(client, "prompts/list")
        rendered = await result(
            client, "prompts/get", {"name": "explain_drink", "arguments": {"slug": "cortado"}}
        )

    assert listing["ttlMs"] == 600_000
    assert listing["cacheScope"] == "public"
    assert "ttlMs" not in rendered
    assert "cacheScope" not in rendered


async def test_prompt_returns_messages_with_an_embedded_resource():
    """Better than pasting text: the client learns which URI the text came from, so
    it can cache it, deduplicate it against a copy it already holds, or show a human
    where the data came from."""
    async with wire_client(PROMPTS) as client:
        rendered = await result(
            client, "prompts/get", {"name": "order_for_me", "arguments": {"mood": "sleepy"}}
        )

    messages = rendered["messages"]
    assert len(messages) == 2

    embedded = messages[0]["content"]
    assert embedded["type"] == "resource"
    assert embedded["resource"]["uri"] == "cafe://menu"
    assert embedded["resource"]["mimeType"] == "text/markdown"

    assert messages[1]["content"]["type"] == "text"


async def test_prompt_arguments_arrive_as_strings_and_are_coerced():
    """There is no JSON typing in prompts' `arguments` — a boolean is the STRING
    "true". The Python type hint coerces it back, which is why `bool` is a safe hint
    and hand-rolled == "true" parsing is not needed."""
    async with wire_client(PROMPTS) as client:
        without = await result(
            client, "prompts/get", {"name": "order_for_me", "arguments": {"mood": "sleepy"}}
        )
        with_dairy = await result(
            client,
            "prompts/get",
            {"name": "order_for_me", "arguments": {"mood": "sleepy", "dairy_free": "true"}},
        )
        with_false = await result(
            client,
            "prompts/get",
            {"name": "order_for_me", "arguments": {"mood": "sleepy", "dairy_free": "false"}},
        )

    # "true" took the dairy-free branch: a different URI and a shorter document.
    assert with_dairy["messages"][0]["content"]["resource"]["uri"] == "cafe://menu/dairy-free"
    # "false" behaved like the default, not like a truthy non-empty string.
    assert with_false["messages"][0]["content"]["resource"]["uri"] == "cafe://menu"
    assert without["messages"][0]["content"]["resource"]["uri"] == "cafe://menu"


async def test_dairy_free_prompt_adds_a_constraint_sentence():
    """The wording is the server author's, and the user never sees it. Which is
    exactly why it is worth a test — change it by accident and behaviour shifts with
    nothing else breaking."""
    async with wire_client(PROMPTS) as client:
        rendered = await result(
            client,
            "prompts/get",
            {"name": "order_for_me", "arguments": {"mood": "sleepy", "dairy_free": "true"}},
        )

    instruction = rendered["messages"][1]["content"]["text"]
    assert "avoids dairy" in instruction
    assert "Recommend exactly one drink" in instruction


async def test_bad_prompt_argument_gives_a_clean_error_not_an_opaque_one():
    """Prompts have NO dedicated exception type, and an ordinary exception comes
    back as an opaque -32603 "Internal server error" — a pydantic validation failure
    does too. `MCPError` is the only thing `get_prompt` re-raises untouched.

    If this test starts returning -32603, someone replaced the MCPError with a plain
    raise and the host can no longer tell the user what went wrong.
    """
    async with wire_client(PROMPTS) as client:
        err = await error(
            client, "prompts/get", {"name": "order_for_me", "arguments": {"mood": "grumpy"}}
        )

    assert err["code"] == -32602, "opaque -32603 means the MCPError escape hatch was lost"
    assert "not a mood this prompt understands" in err["message"]
    # data.argument lets a host highlight the specific field that was wrong.
    assert err["data"]["argument"] == "mood"
    assert "sleepy" in err["data"]["allowed"]


async def test_compare_drinks_rejects_comparing_a_drink_with_itself():
    async with wire_client(PROMPTS) as client:
        err = await error(
            client,
            "prompts/get",
            {"name": "compare_drinks", "arguments": {"first": "latte", "second": "latte"}},
        )

    assert err["code"] == -32602
    assert "must be different" in err["message"]


# --- Topic 05: completion/complete ---


async def _complete(client, ref: dict, argument: str, typed: str, context: dict | None = None):
    params: dict = {"ref": ref, "argument": {"name": argument, "value": typed}}
    if context is not None:
        params["context"] = {"arguments": context}
    return (await result(client, "completion/complete", params))["completion"]


async def test_completion_for_a_prompt_argument():
    async with wire_client(PROMPTS) as client:
        completion = await _complete(
            client, {"type": "ref/prompt", "name": "order_for_me"}, "mood", "s"
        )

    assert completion["values"] == ["sad", "sleepy", "sweet-tooth"]
    assert completion["total"] == 3
    assert completion["hasMore"] is False


async def test_completion_for_a_template_placeholder_closes_topic_04s_gap():
    """resources/templates/list gave the SHAPE of the address and nothing about the
    address space. This is how a client learns the values. Note the ref carries the
    TEMPLATE, placeholder intact — you are asking what can go in the hole, so the
    hole has to still be there."""
    async with wire_client(PROMPTS) as client:
        completion = await _complete(
            client, {"type": "ref/resource", "uri": "cafe://drinks/{slug}"}, "slug", "c"
        )

    assert "cortado" in completion["values"]
    assert "cold-brew" in completion["values"]
    assert all(slug.startswith("c") for slug in completion["values"])


async def test_completion_is_context_aware():
    """The difference between completion as a static enum and completion as a
    function of state: a client filling a form top to bottom gets suggestions
    already consistent with its earlier answers, so a class of invalid input never
    gets typed."""
    ref = {"type": "ref/prompt", "name": "compare_drinks"}
    async with wire_client(PROMPTS) as client:
        without = await _complete(client, ref, "second", "c")
        with_context = await _complete(client, ref, "second", "c", {"first": "cortado"})

    assert "cortado" in without["values"]
    assert "cortado" not in with_context["values"]
    assert with_context["total"] == without["total"] - 1


async def test_completion_returns_empty_for_arguments_it_does_not_know():
    """Return None from the handler and the SDK sends an empty completion. That is
    the correct answer — a wrong suggestion is worse than no suggestion, because a
    client will present it as authoritative."""
    async with wire_client(PROMPTS) as client:
        completion = await _complete(
            client, {"type": "ref/prompt", "name": "order_for_me"}, "nonsense", ""
        )

    assert completion["values"] == []


async def test_completion_still_needs_server_side_validation():
    """Completion is a convenience, never a guarantee — nothing stops a client
    skipping it. So the prompt must still validate. Both halves are load-bearing."""
    ref = {"type": "ref/prompt", "name": "order_for_me"}
    async with wire_client(PROMPTS) as client:
        # Completion would never have offered "grumpy"...
        completion = await _complete(client, ref, "mood", "grumpy")
        assert completion["values"] == []
        # ...but a client can send it anyway, and the prompt refuses it.
        err = await error(
            client, "prompts/get", {"name": "order_for_me", "arguments": {"mood": "grumpy"}}
        )
        assert err["code"] == -32602


@pytest.mark.parametrize(
    ("uri", "expected_mime"),
    [
        ("cafe://menu", "text/markdown"),
        ("cafe://menu/dairy-free", "text/markdown"),
        ("cafe://drinks/latte", "application/json"),
    ],
)
async def test_every_resource_declares_its_mime_type(uri: str, expected_mime: str):
    async with wire_client(RESOURCES) as client:
        read = await result(client, "resources/read", {"uri": uri})

    assert read["contents"][0]["mimeType"] == expected_mime


async def test_the_protocol_surface_is_complete():
    """Topics 01-05 between them exercise nine of the ten client methods of
    2026-07-28. Only subscriptions/listen is left, and it waits for topic 11.

    This test is really a checklist, and it will fail loudly if a future SDK adds or
    removes a method — which is exactly when you want to be told.
    """
    from mcp_types.methods import CLIENT_REQUESTS

    available = {method for method, version in CLIENT_REQUESTS if version == "2026-07-28"}
    covered = {
        "server/discover",  # topic 01
        "tools/list",  # topic 02
        "tools/call",  # topic 03
        "resources/list",  # topic 04
        "resources/read",  # topic 04
        "resources/templates/list",  # topic 04
        "prompts/list",  # topic 05
        "prompts/get",  # topic 05
        "completion/complete",  # topic 05
    }
    assert covered <= available, f"we exercise a method that does not exist: {covered - available}"
    assert available - covered == {"subscriptions/listen"}, (
        f"uncovered methods changed: {available - covered}"
    )
