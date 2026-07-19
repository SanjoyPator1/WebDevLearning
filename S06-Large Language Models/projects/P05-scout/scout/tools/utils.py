"""
tools/utils.py

Simple utility tools that don't need external APIs.
"""
from datetime import datetime
import pytz
import config


def get_current_time() -> str:
    """
    Get the current date and time in the user's configured timezone.
    Returns a human-readable string like 'Friday, 30 May 2026, 5:22 PM IST'.
    """
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    return now.strftime("%A, %d %B %Y, %I:%M %p %Z")


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(get_current_time())
