# ============================================================
# TOPIC: 14 — a SubscriptionBus that is not one process's memory
# REF:   notes/14-load-balancer.md
# ============================================================
#
# Topic 11 diagnosed the leak: MCPServer defaults to InMemorySubscriptionBus,
# a plain dict living in one process's RAM, so an event published on instance
# B never reaches a listener attached to instance A. This module is the fix —
# not a bigger token (topic 11 already explained why that cannot work), but a
# DIFFERENT implementation of the exact same SubscriptionBus Protocol, backed
# by something every instance can actually see: a shared SQLite file.
#
# A real production fix would put Redis or NATS pub/sub behind this same
# Protocol. This one uses SQLite and polling instead, because the lesson is
# the SEAM — swap the bus, change zero lines anywhere else — not the specific
# backend. It is genuinely correct (every instance really does see every
# other instance's events) and genuinely not what you would ship: polling
# every 200ms means an event can take up to 200ms to fan out, where a real
# pub/sub backend delivers in milliseconds. That trade-off is disclosed here
# on purpose, not hidden.

from __future__ import annotations

import asyncio
import sqlite3
import time
from collections.abc import Callable

from mcp.shared.subscriptions import (
    PromptsListChanged,
    ResourcesListChanged,
    ResourceUpdated,
    ServerEvent,
    ToolsListChanged,
)

_KIND_TOOLS = "tools_list_changed"
_KIND_PROMPTS = "prompts_list_changed"
_KIND_RESOURCES = "resources_list_changed"
_KIND_RESOURCE_UPDATED = "resource_updated"


def _encode(event: ServerEvent) -> tuple[str, str | None]:
    """A ServerEvent -> the (kind, uri) pair stored as one SQLite row."""
    if isinstance(event, ToolsListChanged):
        return _KIND_TOOLS, None
    if isinstance(event, PromptsListChanged):
        return _KIND_PROMPTS, None
    if isinstance(event, ResourcesListChanged):
        return _KIND_RESOURCES, None
    return _KIND_RESOURCE_UPDATED, event.uri


def _decode(kind: str, uri: str | None) -> ServerEvent:
    """The inverse of _encode — a stored row back into a ServerEvent."""
    if kind == _KIND_TOOLS:
        return ToolsListChanged()
    if kind == _KIND_PROMPTS:
        return PromptsListChanged()
    if kind == _KIND_RESOURCES:
        return ResourcesListChanged()
    return ResourceUpdated(uri=uri or "")


class SqliteSubscriptionBus:
    """A `SubscriptionBus` (see `mcp.server.subscriptions.SubscriptionBus`) backed
    by a SQLite file every instance points at, instead of one process's own
    memory. Implements the identical two-method Protocol
    `InMemorySubscriptionBus` does — `publish` and `subscribe` — which is the
    entire reason swapping one for the other requires no other change:
    `MCPServer(subscriptions=SqliteSubscriptionBus(path))` is the whole diff.

    Every instance INSERTs a row on publish; every instance with at least one
    active listener polls for rows newer than the last one it has seen and
    replays them to its OWN local listeners. Two different processes pointed
    at the same file therefore both see every event, published by either one.
    """

    def __init__(self, path: str, *, poll_interval_s: float = 0.2) -> None:
        self._path = path
        self._poll_interval_s = poll_interval_s
        self._listeners: dict[object, Callable[[ServerEvent], None]] = {}
        self._poll_task: asyncio.Task[None] | None = None
        self._last_seen_id = self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # A fresh connection per call: SQLite connections are not safe to share
        # across threads/tasks without care, and these calls are infrequent
        # enough (one per publish, one per poll tick) that reconnecting is not
        # a meaningful cost — see the module docstring's disclosed trade-off.
        return sqlite3.connect(self._path)

    def _init_db(self) -> int:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " kind TEXT NOT NULL,"
                " uri TEXT,"
                " created_at REAL NOT NULL"
                ")"
            )
            # A fresh subscriber starts at the CURRENT max id, not zero — it
            # should hear about what happens FROM NOW, not replay every event
            # since this file was first created. There is no backlog delivery
            # here either, matching topic 11's "no resumability" rule.
            (max_id,) = conn.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()
        return max_id

    async def publish(self, event: ServerEvent) -> None:
        kind, uri = _encode(event)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events (kind, uri, created_at) VALUES (?, ?, ?)",
                (kind, uri, time.time()),
            )

    def subscribe(self, listener: Callable[[ServerEvent], None]) -> Callable[[], None]:
        token = object()
        self._listeners[token] = listener
        self._ensure_polling()

        def unsubscribe() -> None:
            self._listeners.pop(token, None)

        return unsubscribe

    def _ensure_polling(self) -> None:
        if self._poll_task is None or self._poll_task.done():
            self._poll_task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self) -> None:
        # Runs only while at least one listener is attached to THIS process;
        # exits on its own once the last one unsubscribes, and restarts the
        # next time subscribe() is called.
        while self._listeners:
            await asyncio.sleep(self._poll_interval_s)
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT id, kind, uri FROM events WHERE id > ? ORDER BY id",
                    (self._last_seen_id,),
                ).fetchall()
            for row_id, kind, uri in rows:
                self._last_seen_id = row_id
                event = _decode(kind, uri)
                for listener in list(self._listeners.values()):
                    try:
                        listener(event)
                    except Exception:  # fan-out boundary, same rule as InMemorySubscriptionBus
                        pass
