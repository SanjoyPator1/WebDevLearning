"""
tools/reminders.py

set_reminder  — store a reminder in SQLite; APScheduler picks it up
list_reminders — show all pending reminders
"""
import json
from datetime import datetime, timedelta
import re

import pytz
import config
from scout.memory.db import get_connection


def _parse_when(when_str: str) -> datetime:
    """
    Parse a natural-language time expression into a timezone-aware datetime.
    Supports:
      "in X minutes / hours / days"
      "tomorrow HH:MM" / "tomorrow 9am"
      absolute ISO-style strings "YYYY-MM-DD HH:MM"
    """
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    s = when_str.strip().lower()

    # "in X minutes/hours/days"
    m = re.match(r"in\s+(\d+)\s+(minute|minutes|hour|hours|day|days)", s)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        if "minute" in unit:
            return now + timedelta(minutes=amount)
        elif "hour" in unit:
            return now + timedelta(hours=amount)
        elif "day" in unit:
            return now + timedelta(days=amount)

    # "tomorrow HH:MM" or "tomorrow 9am"
    m = re.match(r"tomorrow\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = m.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        tomorrow = now + timedelta(days=1)
        return tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute))

    # "today HH:MM" or "HH:MM"
    m = re.match(r"(?:today\s+)?(\d{1,2}):(\d{2})\s*(am|pm)?", s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        ampm = m.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        candidate = tz.localize(datetime(now.year, now.month, now.day, hour, minute))
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    # Absolute ISO string with timezone hint: "2026-05-30 20:03"
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", s)
    if m:
        dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
        return tz.localize(dt)

    raise ValueError(
        f"Could not parse time: '{when_str}'. "
        "Try formats like 'in 2 hours', 'tomorrow 9am', 'in 30 minutes'."
    )


def set_reminder(message: str, when: str) -> str:
    """
    Schedule a reminder to be sent via Telegram at the specified time.
    'when' accepts natural language: 'in 2 hours', 'tomorrow 9am', 'in 30 minutes'.
    Returns a confirmation string with the exact scheduled time.
    """
    try:
        fire_at = _parse_when(when)
    except ValueError as e:
        return f"❌ {e}"

    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    created_at = now.isoformat()

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO reminders (message, fire_at, created_at) VALUES (?, ?, ?)",
            (message, fire_at.isoformat(), created_at),
        )

    human_time = fire_at.strftime("%A, %d %B %Y at %I:%M %p %Z")
    return f"⏰ Reminder set! I'll message you on *{human_time}*\nMessage: _{message}_"


def list_reminders() -> str:
    """Return all pending (unfired) reminders as a formatted string."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE fired = 0 ORDER BY fire_at ASC"
        ).fetchall()

    if not rows:
        return "📭 No pending reminders."

    lines = ["📋 *Pending reminders:*\n"]
    tz = pytz.timezone(config.TIMEZONE)
    for r in rows:
        fire_at = datetime.fromisoformat(r["fire_at"]).astimezone(tz)
        human_time = fire_at.strftime("%d %b %Y, %I:%M %p %Z")
        lines.append(f"  ⏰ [{human_time}] {r['message']}")
    return "\n".join(lines)


def mark_reminder_fired(reminder_id: int) -> None:
    """Mark a reminder as fired in the database."""
    with get_connection() as conn:
        conn.execute("UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,))


def get_pending_reminders() -> list[dict]:
    """Return all unfired reminders as dicts (used by the scheduler)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE fired = 0 ORDER BY fire_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(set_reminder("Test reminder", "in 1 minute"))
    print(list_reminders())
