"""
main.py — Scout entry point.

Run with:
    python main.py

This starts:
  1. The APScheduler reminder daemon (background thread)
  2. The Telegram bot (long-polling, blocks until Ctrl+C)
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path so all imports work
sys.path.insert(0, str(Path(__file__).parent))

from bot.telegram_bot import build_app

if __name__ == "__main__":
    print("🐾 Scout is starting up...")
    app = build_app()
    print("✅ Scout is running. Send a message on Telegram!")
    print("   Press Ctrl+C to stop.\n")
    app.run_polling(drop_pending_updates=True)
