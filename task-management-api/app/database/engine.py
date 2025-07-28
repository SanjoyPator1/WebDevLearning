"""
Database engine and session configuration

This module provides:
- Async SQLAlchemy engine setup
- Session factory with dependency injection
- Connection pool management
- Database health checks
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import asyncio
import logging

from app.config.database import db_config
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager for SQLAlchemy async operations
    
    Handles engine creation, session management, and connection pooling
    for the FastAPI application with proper async support.
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize database engine and session factory
        
        Creates the async engine with connection pooling and
        sets up the session factory for dependency injection.
        """
        if self._initialized:
            return
            
        try:
            # Get database URL and connection arguments
            database_url = db_config.get_database_url()
            connection_args = db_config.get_connection_args()
            
            logger.info(f"Initializing database connection to: {database_url.split('@')[1] if '@' in database_url else database_url}")
            
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                database_url,
                **connection_args,
                # Additional async-specific settings
                future=True,  # Use SQLAlchemy 2.0 style
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Keep objects accessible after commit
                autoflush=True,          # Automatically flush changes
                autocommit=False,        # Manual transaction control
            )
            
            self._initialized = True
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close database engine and cleanup connections
        
        Properly closes all connections and cleans up resources
        when the application shuts down.
        """
        if self.engine:
            logger.info("Closing database connections...")
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """
        Perform database health check
        
        Returns:
            True if database is accessible and responding
        """
        if not self._initialized:
            return False
            
        try:
            # Test database connection with a simple query
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()

# Export async_session for compatibility
async_session = None
def _get_async_session():
    if db_manager.session_factory is None:
        raise RuntimeError("Database not initialized. Call db_manager.initialize() before using async_session.")
    return db_manager.session_factory

import sys
if 'pytest' in sys.modules:
    # For testing, allow direct access
    async_session = lambda: db_manager.session_factory()
else:
    # For app runtime, provide a session factory that ensures initialization
    async def async_session():
        if not db_manager._initialized:
            await db_manager.initialize()
        return db_manager.session_factory

async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions
    
    Provides async database sessions with proper lifecycle management.
    Automatically handles session creation, cleanup, and error handling.
    
    Usage:
        @app.get("/tasks")
        async def get_tasks(db: AsyncSession = Depends(get_database_session)):
            result = await db.execute(select(Task))
            return result.scalars().all()
    
    Yields:
        AsyncSession: Database session for use in FastAPI endpoints
    """
    if not db_manager._initialized:
        await db_manager.initialize()
    
    # Create new session for this request
    async with db_manager.session_factory() as session:
        try:
            # Yield session to the endpoint
            yield session
        except Exception as e:
            # Rollback transaction on error
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            # Session is automatically closed by async context manager
            pass

# Convenience alias for dependency injection
DatabaseSession = AsyncSession