"""
Database package for SQLAlchemy operations

Contains:
- engine.py: Async database engine and session management
- session_utils.py: Database utilities and helpers (if exists)

Removed/Deprecated:
- users.py: Old mock user database (commented out, will be deleted)
"""

from .engine import get_database_session, db_manager

__all__ = ["get_database_session", "db_manager"]
