# ============================================================
# TOPIC: 07 — the order token: state that is actually worth protecting
# REF:   notes/07-the-order-token.md
# ============================================================
#
# Like every other cafe_mcp module, this imports NOTHING from MCP.
#
# Topic 06 minted a cursor and left it unsigned, because there was nothing in it
# worth protecting — an offset into a public menu costs nothing to forge. A
# shopping cart is different: it carries a total a customer will be charged, and
# forging one is the whole game. So this time the token is HMAC-signed.
#
# The shape is otherwise identical to topic 06's cursor, on purpose:
#
#     v1.<base64url(json payload)>.<base64url(hmac-sha256 signature)>
#
# One more base64url segment than the cursor had. That one segment is the entire
# difference between "opaque" and "opaque AND tamper-evident".

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from typing import Any

_DEV_SECRET = b"cafe-mcp-development-key-do-not-use-in-production"


def _secret() -> bytes:
    """The HMAC key. From CAFE_MCP_SECRET if set, else a fixed dev key.

    The fallback exists so this folder runs with zero setup, and it SHOUTS about
    it on stderr rather than staying quiet — a POC default that fails silently is
    how a fixed key ends up load-bearing in a real deployment.
    """
    configured = os.environ.get("CAFE_MCP_SECRET")
    if configured:
        return configured.encode("utf-8")
    print(
        "  [tokens] WARNING: CAFE_MCP_SECRET is not set. Using a fixed, PUBLIC "
        "development key. This is fine for this folder; it is not fine anywhere "
        "real orders or money are involved.",
        file=sys.stderr,
    )
    return _DEV_SECRET


class TokenError(Exception):
    """A token failed to verify: malformed, tampered, wrong kind, or expired.

    One exception type for all four failure modes, distinguished only by message
    — deliberately. Telling an attacker WHICH check failed (bad signature vs
    expired vs wrong kind) gives them a map of what to try next. A caller that
    genuinely needs to distinguish "expired" from "invalid" for its own UX can
    still do so by checking the message text; the type itself gives nothing away.
    """


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(token + padding)


def sign(kind: str, payload: dict[str, Any], ttl_s: int) -> str:
    """Mint a signed token carrying `payload`, valid for `ttl_s` seconds.

    `kind` is embedded in the signed body and checked on verify — DOMAIN
    SEPARATION. An order token and a place-order confirmation state (topic 08)
    are both just signed JSON blobs; without a kind check, a valid order token
    could be replayed wherever a confirmation state was expected, or vice versa.
    Binding the intended use into the signature is what a generic "is this
    HMAC valid" check cannot give you for free.
    """
    now = int(time.time())
    body = {"kind": kind, "iat": now, "exp": now + ttl_s, **payload}
    # sort_keys: the same logical payload always produces the same bytes, which
    # keeps tokens deterministic for a given input — useful for tests and for
    # reasoning about what changed between two tokens.
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body_b64 = _b64encode(raw)

    signature = hmac.new(_secret(), body_b64.encode("ascii"), hashlib.sha256).digest()
    signature_b64 = _b64encode(signature)

    return f"v1.{body_b64}.{signature_b64}"


def verify(kind: str, token: str) -> dict[str, Any]:
    """Verify a token and return its payload (including `kind`, `iat`, `exp`).

    Raises TokenError for any failure. The four checks run in an order that
    matters: signature first, because nothing else about an unsigned token can be
    trusted — not even well-formed JSON is proof the sender is who they claim,
    since anyone can construct valid JSON.
    """
    parts = token.split(".", 2)
    if len(parts) != 3 or parts[0] != "v1":
        raise TokenError("this token is not in a format this server recognises")

    _, body_b64, signature_b64 = parts

    try:
        given_signature = _b64decode(signature_b64)
    except Exception as exc:
        raise TokenError("this token's signature is not valid base64") from exc

    expected_signature = hmac.new(_secret(), body_b64.encode("ascii"), hashlib.sha256).digest()

    # hmac.compare_digest, NEVER `==`. A plain `==` on two byte strings short-
    # circuits at the first differing byte, so the time it takes to reject a
    # forged signature leaks how many leading bytes were already correct — a
    # timing side channel an attacker can use to forge a valid signature one byte
    # at a time. compare_digest runs in time independent of where the strings
    # first differ.
    if not hmac.compare_digest(expected_signature, given_signature):
        raise TokenError(
            "this token's signature does not match — it was not issued by this "
            "server, or has been altered"
        )

    try:
        body = json.loads(_b64decode(body_b64))
    except Exception as exc:
        raise TokenError("this token's payload is not valid") from exc

    if not isinstance(body, dict):
        raise TokenError("this token's payload is not an object")

    # Domain separation: a signature can be perfectly valid and still be the
    # WRONG kind of token for this call.
    if body.get("kind") != kind:
        raise TokenError(
            f"this token was not issued as a {kind!r} token "
            f"(it is {body.get('kind')!r}) — it cannot be used here"
        )

    exp = body.get("exp")
    if not isinstance(exp, int) or time.time() > exp:
        raise TokenError(f"this {kind} token has expired — start again")

    return body
