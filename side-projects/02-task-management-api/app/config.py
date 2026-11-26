"""
DEPRECATED: Root Configuration File
===================================
This file has been replaced with a configuration package structure.

Migration completed: [2024-06-09]
- Single config file  > Organized config package
- app/config.py  > app/config/ package with:
  - app/config/settings.py: Application settings (security, email, etc.)
  - app/config/database.py: Database configuration
  - app/config/__init__.py: Unified exports

New usage:
- from app.config import settings  # Application settings
- from app.config import db_config  # Database configuration

This file will be removed after testing is complete.
"""

# Commented out old configuration:
# [Comment out all the existing Pydantic Settings class and code]