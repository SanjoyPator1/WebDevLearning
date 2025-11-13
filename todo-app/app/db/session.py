"""
Database session management with async SQLAlchemy.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url_asyncpg,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Yields:
        AsyncSession: Database session

    Example:
        ```python
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
