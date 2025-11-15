"""
Models package.
Import all models here so Alembic can discover them.
"""
from app.db.base import Base  # Import Base first
from app.models.user import User
from app.models.todo import Todo, TodoStatus, TodoPriority

# This list makes models easily importable
__all__ = [
    "Base",
    "User",
    "Todo",
    "TodoStatus",
    "TodoPriority",
]