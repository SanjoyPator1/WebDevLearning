"""
config.py — Central config loader.
Reads .env and exposes typed settings to every module.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (works regardless of where Python is invoked from)
_ROOT = Path(__file__).parent
load_dotenv(_ROOT / ".env")

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: int = int(os.environ["TELEGRAM_CHAT_ID"])

# ── Search ───────────────────────────────────────────────────────────────────
SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# ── Ollama / LLM ─────────────────────────────────────────────────────────────
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── Timezone ──────────────────────────────────────────────────────────────────
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

# ── Agent ─────────────────────────────────────────────────────────────────────
MAX_REACT_ITERATIONS: int = int(os.getenv("MAX_REACT_ITERATIONS", "5"))
WORKING_MEMORY_WINDOW: int = int(os.getenv("WORKING_MEMORY_WINDOW", "15"))

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR: Path = _ROOT / "data"
DB_PATH: Path = DATA_DIR / "scout.db"
USER_MEMORY_PATH: Path = DATA_DIR / "user_memory.json"

# Make sure data dir exists
DATA_DIR.mkdir(exist_ok=True)
