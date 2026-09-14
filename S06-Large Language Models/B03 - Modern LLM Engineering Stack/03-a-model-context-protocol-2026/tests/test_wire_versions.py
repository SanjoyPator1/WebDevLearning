# ============================================================
# TESTS: version negotiation
# REF:   notes/12-versions.md
# ============================================================
#
# Run: pytest tests/test_wire_versions.py -v

import t12_versions
from wire import error, result, wire_client

SERVER = t12_versions.mcp


async def _whoami(client, version: str, *, req_id: int = 1) -> dict:
    return await result(
        client, "tools/call", {"name": "whoami", "arguments": {}}, req_id=req_id, version=version
    )


async def test_every_known_version_works_for_an_ordinary_method():
    """All four KNOWN_PROTOCOL_VERSIONS genuinely work, not just the modern
    one — this is what makes the SDK "dual-era" rather than "modern-only"."""
    async with wire_client(SERVER) as client:
        for version in ("2026-07-28", "2025-11-25", "2025-06-18", "2024-11-05"):
            call_result = await _whoami(client, version, req_id=hash(version) % 1000)
            text = call_result["content"][0]["text"]
            assert version in text, f"{version} did not work: {call_result}"


async def test_the_declared_version_can_change_call_to_call():
    """No session remembers a version from a previous call — proven by
    changing it mid "conversation" (two calls, two different versions,
    same client) and seeing the SAME tool answer differently each time."""
    async with wire_client(SERVER) as client:
        first = await _whoami(client, "2026-07-28", req_id=1)
        second = await _whoami(client, "2024-11-05", req_id=2)

    assert "2026-07-28" in first["content"][0]["text"]
    assert "2024-11-05" in second["content"][0]["text"]


async def test_unknown_version_returns_32022_with_a_recovery_list():
    async with wire_client(SERVER) as client:
        err = await error(client, "tools/list", {}, version="not-a-real-version")

    assert err["code"] == -32022
    assert err["data"]["supported"] == ["2026-07-28"]
    assert err["data"]["requested"] == "not-a-real-version"


async def test_discover_advertises_only_the_modern_version():
    """supportedVersions is MODERN_PROTOCOL_VERSIONS, not every version this
    SDK actually accepts — discover only ever advertises the modern era it
    offers under discovery, which is why this list has ONE entry even though
    four different OLDER versions all work fine elsewhere on this server."""
    async with wire_client(SERVER) as client:
        discovered = await result(client, "server/discover")

    assert discovered["supportedVersions"] == ["2026-07-28"]


async def test_discover_does_not_exist_under_an_older_known_version():
    """THE central irony: 2025-06-18 is a real, fully-working version for
    ordinary methods (see test_every_known_version_works_for_an_ordinary_method)
    but server/discover has no entry in that era's method map at all — it was
    added AT 2026-07-28. So a client cannot safely call discover to learn what
    to speak before it has already decided to speak the modern version."""
    async with wire_client(SERVER) as client:
        err = await error(client, "server/discover", {}, version="2025-06-18")

    assert err["code"] == -32601
    assert err["data"] == "server/discover"


async def test_discover_works_once_the_modern_version_is_declared():
    async with wire_client(SERVER) as client:
        discovered = await result(client, "server/discover", {}, version="2026-07-28")

    assert discovered["resultType"] == "complete"
    assert discovered["supportedVersions"] == ["2026-07-28"]


async def test_ping_is_the_mirror_image_of_discover():
    """`ping` and `server/discover` are missing from opposite ends of the era
    range, for opposite reasons — worth telling apart:

    `server/discover` is missing from every version OLDER than 2026-07-28,
    because it is NEW at this revision (see
    test_discover_does_not_exist_under_an_older_known_version).

    `ping` is missing from 2026-07-28 alone, because it was REMOVED there — it
    still works at every version that predates the removal. It is not that
    old-version requests get some reduced or legacy-flavoured ping; the method
    genuinely exists for them, unchanged, exactly as it always did.
    """
    async with wire_client(SERVER) as client:
        for old_version in ("2025-11-25", "2025-06-18", "2024-11-05"):
            call_result = await result(
                client, "ping", {}, version=old_version, req_id=hash(old_version) % 1000 + 1
            )
            assert call_result == {}, f"ping should be an EmptyResult at {old_version}"

        err = await error(client, "ping", {}, version="2026-07-28", req_id=999)
        assert err["code"] == -32601
        assert err["data"] == "ping"


async def test_legacy_result_shape_has_none_of_the_modern_fields():
    """Reconfirms topic 01's finding, this time explicitly as part of the
    version-negotiation story: an old-but-known version is served in ITS OWN
    era's shape, not a degraded modern one."""
    async with wire_client(SERVER) as client:
        legacy = await result(client, "tools/list", {}, version="2025-06-18")

    assert "resultType" not in legacy
    assert "ttlMs" not in legacy
    assert "_meta" not in legacy
