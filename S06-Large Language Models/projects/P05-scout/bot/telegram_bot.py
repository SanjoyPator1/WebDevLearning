"""
bot/telegram_bot.py

Telegram bot — the user-facing interface for Scout.

Slash commands:
  /start      — welcome message
  /reminders  — list pending reminders
  /memory     — show what Scout knows about you
  /clear      — clear working memory (fresh session)
  /list <name>— shortcut to read a list (e.g. /list groceries)
  /help       — list commands

Free text → routed through the ReAct agent loop.
"""
import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

import config
from scout.memory.db import init_db
from scout.memory.manager import MemoryManager
from scout.agent import react_loop
from scout.tools.reminders import list_reminders
from scout.scheduler.reminder_scheduler import init_scheduler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("scout.bot")

# One MemoryManager per chat session — keyed by chat_id
_sessions: dict[int, MemoryManager] = {}


def _get_session(chat_id: int) -> MemoryManager:
    if chat_id not in _sessions:
        _sessions[chat_id] = MemoryManager()
    return _sessions[chat_id]


def _is_authorised(update: Update) -> bool:
    """Only respond to the configured owner."""
    return update.effective_chat.id == config.TELEGRAM_CHAT_ID


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorised(update):
        return
    await update.message.reply_text(
        "👋 Hey! I'm *Scout* — your personal assistant.\n\n"
        "I can:\n"
        "• Search the web for real-time info 🔍\n"
        "• Set reminders that ping you here ⏰\n"
        "• Manage your lists (groceries, todos…) 📋\n"
        "• Remember things you tell me 🧠\n\n"
        "Just talk to me naturally. Type /help for commands.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorised(update):
        return
    await update.message.reply_text(
        "*Scout commands:*\n\n"
        "/start — welcome\n"
        "/reminders — show pending reminders\n"
        "/memory — show what I know about you\n"
        "/list <name> — show a list (e.g. /list groceries)\n"
        "/clear — reset conversation memory\n"
        "/help — this message\n\n"
        "Or just talk to me — I'll figure it out.",
        parse_mode="Markdown",
    )


async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorised(update):
        return
    await update.message.reply_text(list_reminders(), parse_mode="Markdown")


async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorised(update):
        return
    mm = _get_session(update.effective_chat.id)
    await update.message.reply_text(mm.get_all_memory_summary(), parse_mode="Markdown")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorised(update):
        return
    mm = _get_session(update.effective_chat.id)
    mm.clear_working()
    await update.message.reply_text("🧹 Conversation memory cleared. Fresh start!")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorised(update):
        return
    from scout.tools.lists import read_list
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /list <name>  e.g. /list groceries")
        return
    list_name = " ".join(args)
    await update.message.reply_text(read_list(list_name), parse_mode="Markdown")


# ── Message handler (main agent entry) ───────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorised(update):
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    chat_id = update.effective_chat.id
    mm = _get_session(chat_id)

    # Show typing indicator while thinking
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        response, tools_called = react_loop.run(user_text, mm)
    except Exception as e:
        logger.exception("Agent loop error")
        response = f"⚠️ Something went wrong: {e}"
        tools_called = []

    # Update working memory with this exchange
    mm.add_turn("user", user_text)
    mm.add_turn("assistant", response)

    # Log to episodic memory
    mm.save_episode(user_text, response, tools_called)

    logger.info(f"Sending response ({len(response)} chars) to chat {chat_id}")

    # Split long messages (Telegram max 4096 chars)
    max_len = 4000
    chunks = [response[i : i + max_len] for i in range(0, len(response), max_len)]
    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            # Markdown parse failed (stray *, _, ` etc.) — fall back to plain text
            try:
                await update.message.reply_text(chunk)
            except Exception as e:
                logger.exception(f"Failed to send message: {e}")


# ── Send message utility (used by the scheduler) ──────────────────────────────

_app: Application | None = None


async def send_message(text: str) -> None:
    """Send a proactive message to the owner — used by the reminder scheduler."""
    if _app is None:
        logger.warning("send_message called before app is initialised")
        return
    await _app.bot.send_message(
        chat_id=config.TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="Markdown",
    )


# ── App factory ───────────────────────────────────────────────────────────────

def build_app() -> Application:
    global _app

    # Initialise DB + scheduler
    init_db()
    init_scheduler(send_message)

    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).request(request).build()
    _app = app

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reminders", cmd_reminders))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
