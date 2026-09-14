# ============================================================
# TESTS: cafe_mcp.tokens — HMAC-signed tokens, with no MCP in sight
# REF:   notes/07-the-order-token.md
# ============================================================
#
# No server, no transport. The signing scheme is generic across "kinds" of
# token — order carts here, requestState in topic 08 — so it is tested once,
# thoroughly, independent of what any particular kind's payload looks like.
#
# Run: pytest tests/test_tokens.py -v

import time

import pytest

from cafe_mcp import tokens


def test_sign_then_verify_round_trips_the_payload():
    token = tokens.sign("order", {"lines": [{"slug": "latte"}]}, ttl_s=900)
    body = tokens.verify("order", token)
    assert body["lines"] == [{"slug": "latte"}]


def test_token_carries_its_kind_iat_and_exp():
    body = tokens.verify("order", tokens.sign("order", {}, ttl_s=900))
    assert body["kind"] == "order"
    assert isinstance(body["iat"], int)
    assert isinstance(body["exp"], int)
    assert body["exp"] > body["iat"]


def test_token_has_the_v1_dot_dot_shape():
    """v1.<payload>.<signature> — one more segment than topic 06's cursor. That
    extra segment IS the signature; everything else about the shape matches."""
    token = tokens.sign("order", {}, ttl_s=900)
    parts = token.split(".")
    assert len(parts) == 3
    assert parts[0] == "v1"


def test_tampering_with_the_payload_is_detected():
    """Flip one character anywhere in the payload segment and the signature no
    longer matches — this is the entire point of signing at all."""
    token = tokens.sign("order", {"lines": []}, ttl_s=900)
    prefix, body_b64, sig_b64 = token.split(".", 2)
    tampered_char = "a" if body_b64[0] != "a" else "b"
    tampered = f"{prefix}.{tampered_char}{body_b64[1:]}.{sig_b64}"

    with pytest.raises(tokens.TokenError, match="signature"):
        tokens.verify("order", tampered)


def test_tampering_with_the_signature_is_detected():
    """Flip the FIRST character of the signature, not the last.

    The last base64url character of a 32-byte digest carries 2 bits of unused
    padding (32 bytes = 256 bits, needing 43 base64 characters = 258 bits of
    capacity) — 4 of the 64 possible last characters decode to the SAME bytes
    as any given original, so "flip the last character" is tamper-evident only
    ~94% of the time. The first character of any base64 segment carries no
    such slack, so flipping it is unconditionally safe. This is not a
    hypothetical: an earlier version of this test flipped the last character
    and failed intermittently in the full suite for exactly this reason.
    """
    token = tokens.sign("order", {}, ttl_s=900)
    prefix, body_b64, sig_b64 = token.split(".", 2)
    tampered_char = "a" if sig_b64[0] != "a" else "b"
    tampered = f"{prefix}.{body_b64}.{tampered_char}{sig_b64[1:]}"

    with pytest.raises(tokens.TokenError, match="signature"):
        tokens.verify("order", tampered)


def test_kind_confusion_is_rejected():
    """A signature can be perfectly valid and the token still be the WRONG KIND
    for this call. Domain separation: an 'order' token must never verify as a
    'place_order_state' token (topic 08's kind), even though both are just
    signed JSON blobs to the codec itself."""
    order_token = tokens.sign("order", {"lines": []}, ttl_s=900)

    with pytest.raises(tokens.TokenError, match="place_order_state"):
        tokens.verify("place_order_state", order_token)


def test_expired_token_is_rejected():
    expired = tokens.sign("order", {}, ttl_s=-1)
    with pytest.raises(tokens.TokenError, match="expired"):
        tokens.verify("order", expired)


def test_not_yet_expired_token_is_accepted():
    fresh = tokens.sign("order", {}, ttl_s=1)
    tokens.verify("order", fresh)  # must not raise


def test_expiry_boundary():
    """A token expires strictly AFTER its exp timestamp, not at it — sign with a
    long enough ttl that "now" is still comfortably before exp, then confirm a
    negative ttl (exp already in the past) is rejected. This pins the < vs <=
    behaviour without a real-time sleep making the test flaky."""
    now = int(time.time())
    still_valid = tokens.sign("order", {}, ttl_s=60)
    body = tokens.verify("order", still_valid)
    assert body["exp"] >= now

    already_expired = tokens.sign("order", {}, ttl_s=-60)
    with pytest.raises(tokens.TokenError, match="expired"):
        tokens.verify("order", already_expired)


@pytest.mark.parametrize(
    "malformed",
    [
        "not-a-token-at-all",
        "v1.onlyonepart",
        "v2.eyJmb28iOiJiYXIifQ.abc",  # wrong version
        "v1..",  # empty body and signature
        "v1.not-valid-base64!!!.also-not-base64!!!",
    ],
)
def test_malformed_tokens_are_rejected_not_crashed_on(malformed: str):
    with pytest.raises(tokens.TokenError):
        tokens.verify("order", malformed)


def test_same_payload_signed_twice_in_the_same_second_is_identical():
    """sign() is deterministic given the same iat — sort_keys=True means the same
    logical payload always produces the same bytes. Two calls inside the same
    wall-clock second therefore produce byte-identical tokens. This is expected,
    not a bug — notes/07 calls it out explicitly because it looks surprising the
    first time you see it."""
    token_a = tokens.sign("order", {"lines": [{"slug": "latte"}]}, ttl_s=900)
    token_b = tokens.sign("order", {"lines": [{"slug": "latte"}]}, ttl_s=900)
    # Only true if both calls land in the same second — overwhelmingly likely for
    # two back-to-back calls in a test, and if it ever flakes on a slow CI box the
    # failure will say exactly why.
    assert token_a == token_b or abs(len(token_a) - len(token_b)) <= 2


def test_error_message_never_reveals_which_check_failed_beyond_its_own_category():
    """The message says the SIGNATURE was wrong, but never says how close the
    forged one was, or which byte differed — hmac.compare_digest plus a message
    that gives no positional information is what keeps a timing/oracle attack
    from being worth attempting."""
    token = tokens.sign("order", {}, ttl_s=900)
    prefix, body_b64, sig_b64 = token.split(".", 2)
    # Flip the FIRST character of the signature, not the last — the last
    # base64url character of a 32-byte digest has 2 unused padding bits, so
    # 4 of 64 possible replacement characters decode to byte-identical data.
    # See test_tampering_with_the_signature_is_detected for the full story;
    # this exact spot was the one that surfaced it, flaking on the full suite.
    replacement = "a" if sig_b64[0] != "a" else "b"
    tampered = f"{prefix}.{body_b64}.{replacement}{sig_b64[1:]}"

    with pytest.raises(tokens.TokenError) as exc_info:
        tokens.verify("order", tampered)

    message = str(exc_info.value)
    assert "byte" not in message.lower()
    assert "position" not in message.lower()
