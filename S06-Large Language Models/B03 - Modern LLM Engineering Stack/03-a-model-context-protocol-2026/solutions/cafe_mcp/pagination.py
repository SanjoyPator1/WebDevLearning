# ============================================================
# TOPIC: 06 — the opaque cursor
# REF:   notes/06-pagination.md
# ============================================================
#
# Like menu.py and render.py, this imports NOTHING from MCP.
#
# A cursor is the gentlest possible answer to the question topic 00 raised and
# left hanging: if sessions are gone, where does state live when a server needs to
# remember something across two calls? Here, "something" is just a position in a
# list, so the answer is small enough to see whole.
#
# The design has three deliberate properties, and each one earns its keep later:
#
#   1. OPAQUE to the caller. A client must not construct or interpret a cursor —
#      only pass back exactly what it was given. That is what lets you change the
#      encoding later without breaking anyone.
#   2. DECODABLE by a human with a terminal. `base64 -d` on a cursor shows valid
#      JSON. Opaque does not have to mean secret — see notes/06 for why that
#      distinction matters once topic 07 makes the payload worth protecting.
#   3. VALIDATED on the way in. A cursor is caller-supplied input from the moment
#      it leaves the server, so a malformed one must fail cleanly rather than
#      crash the handler.

import base64
import json


class CursorError(Exception):
    """A cursor was malformed, or did not decode to a sane position.

    Raised by decode_cursor; the TOOL layer converts this to a ToolError with a
    message a model can act on. This module does not know it will be talking to a
    model — same discipline as menu.py raising KeyError rather than ToolError.
    """


def encode_cursor(offset: int) -> str:
    """Turn a position into an opaque page token.

    v1.<base64url(json)> — versioned so a future encoding change can be detected
    and rejected cleanly rather than silently misread. There is only one version
    today; the prefix costs four characters and buys a migration path.
    """
    payload = json.dumps({"offset": offset}, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"v1.{token}"


def decode_cursor(cursor: str) -> int:
    """Recover the offset from a cursor, or raise CursorError.

    Deliberately strict: a wrong version, a base64 error, missing JSON keys, a
    negative offset, or a non-integer offset are all CursorError. A cursor is
    input from outside the process the moment it is handed back, and "the client
    typed the wrong thing" must never reach as far as an unhandled exception.
    """
    prefix, _, token = cursor.partition(".")
    if prefix != "v1" or not token:
        raise CursorError(f"unrecognised cursor format: {cursor!r}")

    padding = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(token + padding)
        data = json.loads(raw)
    except Exception as exc:
        raise CursorError(f"cursor does not decode to valid data: {cursor!r}") from exc

    if not isinstance(data, dict) or "offset" not in data:
        raise CursorError(f"cursor is missing the 'offset' field: {cursor!r}")

    offset = data["offset"]
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise CursorError(f"cursor offset is not a non-negative integer: {offset!r}")

    return offset


def page(items: list, cursor: str | None, limit: int) -> tuple[list, str | None]:
    """Slice `items` starting at `cursor` (or the beginning), `limit` at a time.

    Returns (this_page, next_cursor). `next_cursor` is None on the last page —
    that is the ONLY signal a caller should use to know it has reached the end.
    Comparing page length to `limit` is not reliable: a page that happens to
    divide evenly still needs one more call before the caller can tell.
    """
    offset = decode_cursor(cursor) if cursor else 0
    chunk = items[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < len(items) else None
    return chunk, next_cursor
