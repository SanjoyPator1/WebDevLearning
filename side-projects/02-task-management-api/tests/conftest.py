"""
Test configuration and fixtures for database testing

This module provides:
- Test database setup and teardown
- Database session fixtures
- Model factory functions
- Test data utilities
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.user import User
from app.models.task import Task, TaskPriority
from app.models.team import Team
import uuid

# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session for tests
    """
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """
    Create sample user for testing
    """
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        email_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def sample_team(db_session: AsyncSession, sample_user: User) -> Team:
    """
    Create sample team for testing
    """
    team = Team(
        name="Test Team",
        description="A team for testing",
        created_by=sample_user.id
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team

@pytest.fixture
async def sample_task(db_session: AsyncSession, sample_user: User) -> Task:
    """
    Create sample task for testing
    """
    task = Task(
        title="Test Task",
        description="A task for testing",
        priority=TaskPriority.MEDIUM,
        created_by=sample_user.id,
        assigned_to=sample_user.id
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task