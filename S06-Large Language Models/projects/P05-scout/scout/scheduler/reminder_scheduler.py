"""
scheduler/reminder_scheduler.py

APScheduler-based reminder daemon.
- On startup: loads all pending reminders from SQLite and schedules them.
- When a reminder fires: sends a Telegram message to the user.
- Handles "late reminders": reminders that should have fired while the bot was offline.
"""
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

import config
from scout.tools.reminders import get_pending_reminders, mark_reminder_fired

# Will be set by the bot at startup so the scheduler can send messages
_send_message_fn = None
_scheduler: BackgroundScheduler | None = None


def _fire_reminder(reminder_id: int, message: str, late: bool = False) -> None:
    """Called by APScheduler when a reminder's time arrives."""
    if _send_message_fn is None:
        print(f"[Scheduler] No send_fn set — cannot fire reminder {reminder_id}")
        return

    prefix = "⏰ " if not late else "⏰ _(late)_ "
    text = f"{prefix}*Reminder:* {message}"
    try:
        import asyncio
        asyncio.run(_send_message_fn(text))
    except Exception as e:
        print(f"[Scheduler] Failed to send reminder {reminder_id}: {e}")
    finally:
        mark_reminder_fired(reminder_id)


def init_scheduler(send_message_fn) -> BackgroundScheduler:
    """
    Initialise the scheduler and load all pending reminders from the DB.
    send_message_fn: async callable(text: str) that sends a Telegram message.
    """
    global _send_message_fn, _scheduler
    _send_message_fn = send_message_fn

    _scheduler = BackgroundScheduler(timezone=config.TIMEZONE)
    _scheduler.start()

    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)

    pending = get_pending_reminders()
    late_count = 0
    scheduled_count = 0

    for reminder in pending:
        fire_at = datetime.fromisoformat(reminder["fire_at"]).astimezone(tz)
        rid = reminder["id"]
        msg = reminder["message"]

        if fire_at <= now:
            # Missed while bot was offline — fire immediately
            _scheduler.add_job(
                _fire_reminder,
                trigger=DateTrigger(run_date=now),
                args=[rid, msg, True],
                id=f"reminder_{rid}",
                replace_existing=True,
            )
            late_count += 1
        else:
            _scheduler.add_job(
                _fire_reminder,
                trigger=DateTrigger(run_date=fire_at),
                args=[rid, msg, False],
                id=f"reminder_{rid}",
                replace_existing=True,
            )
            scheduled_count += 1

    print(f"[Scheduler] Started — {scheduled_count} upcoming, {late_count} late reminders.")
    return _scheduler


def schedule_new_reminder(reminder_id: int, message: str, fire_at: datetime) -> None:
    """
    Register a newly created reminder with the running scheduler.
    Called by the reminder tool after inserting into the DB.
    """
    if _scheduler is None:
        return
    tz = pytz.timezone(config.TIMEZONE)
    fire_at_tz = fire_at.astimezone(tz)
    _scheduler.add_job(
        _fire_reminder,
        trigger=DateTrigger(run_date=fire_at_tz),
        args=[reminder_id, message, False],
        id=f"reminder_{reminder_id}",
        replace_existing=True,
    )
    print(f"[Scheduler] Scheduled reminder {reminder_id} for {fire_at_tz}")
