"""
memory/db.py

SQLite database setup — creates tables on first run.
"""
import sqlite3
from pathlib import Path
import config


def get_connection() -> sqlite3.Connection:
    """Return a connection to the Scout SQLite database."""
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they don't already exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                message     TEXT    NOT NULL,
                fire_at     TEXT    NOT NULL,   -- ISO 8601 datetime string (timezone-aware)
                repeat_rule TEXT,               -- NULL for one-shot, cron expr for recurring
                fired       INTEGER DEFAULT 0,  -- 0 = pending, 1 = fired
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                user_message    TEXT    NOT NULL,
                scout_response  TEXT    NOT NULL,
                tools_called    TEXT    DEFAULT '[]',  -- JSON list of tool names
                outcome         TEXT    DEFAULT 'success'
            );
        """)
    print("[DB] Tables ready.")


if __name__ == "__main__":
    init_db()
    print(f"[DB] Database at: {config.DB_PATH}")
