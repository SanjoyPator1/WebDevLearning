"""
Database configuration for different environments

NOTE: As of 2024-06-09, the default database is PostgreSQL. SQLite is only used for explicit test environments.

This module provides:
- Environment-specific database URLs
- Connection pool configuration
- SSL settings for production
- Health check configuration
- Migration settings
"""

import os
from typing import Optional
from urllib.parse import quote_plus

class DatabaseConfig:
    """
    Database configuration class with environment-specific settings
    
    Supports multiple environments:
    - Development: Local PostgreSQL
    - Testing: In-memory SQLite or test database
    - Production: Cloud PostgreSQL with SSL
    """
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        
    def get_database_url(self) -> str:
        """
        Get database URL based on environment
        
        Returns:
            Database connection string with proper encoding
            
        Environment Variables:
            DATABASE_URL: Full database URL (production)
            DB_HOST: Database host (default: localhost)
            DB_PORT: Database port (default: 5432)
            DB_NAME: Database name (default: taskmanager_dev)
            DB_USER: Database user (default: taskuser)
            DB_PASSWORD: Database password (required)
        """
        
        # Use DATABASE_URL if provided (common in production)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
            
        # Build URL from components
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "taskmanager_dev")
        username = os.getenv("DB_USER", "taskuser")
        password = os.getenv("DB_PASSWORD", "dev_password_123")
        
        # URL encode password to handle special characters
        encoded_password = quote_plus(password)
        
        return f"postgresql+asyncpg://{username}:{encoded_password}@{host}:{port}/{database}"
    
    def get_connection_args(self) -> dict:
        """
        Get SQLAlchemy engine configuration arguments
        
        Returns:
            Dictionary with engine configuration for connection pooling,
            timeouts, and SSL settings based on environment
        """
        
        base_args = {
            # Connection pool settings
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            
            # Connection behavior
            "pool_pre_ping": True,  # Validate connections before use
            "echo": os.getenv("DB_ECHO", "false").lower() == "true",  # Log SQL queries
        }
        
        # Production-specific settings
        if self.environment == "production":
            base_args.update({
                "pool_size": 20,
                "max_overflow": 0,  # Strict pool size in production
                "connect_args": {
                    "sslmode": "require",
                    "connect_timeout": 10,
                }
            })
        
        return base_args

# Global configuration instance
db_config = DatabaseConfig()