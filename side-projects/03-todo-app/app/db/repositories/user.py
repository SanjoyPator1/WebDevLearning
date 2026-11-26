"""
User repository for database operations.
"""
from sqlalchemy import or_, select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """Repository for User model with custom methods."""

    def __init__(self, db: AsyncSession):
        """Initialize user repository."""
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User instance or None
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """
        Get user by username.

        Args:
            username: User's username

        Returns:
            User instance or None
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, identifier: str) -> User | None:
        """
        Get user by email or username.

        Args:
            identifier: Email or username

        Returns:
            User instance or None
        """
        result = await self.db.execute(
            select(User).where(or_(User.email == identifier, User.username == identifier))
        )
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists by email.

        Args:
            email: Email to check

        Returns:
            True if exists, False otherwise
        """
        # user = await self.get_by_email(email)
        # return user is not None

        result = await self.db.execute(
            select(exists().where(User.email == email))
        )
        return result.scalar()

    async def exists_by_username(self, username: str) -> bool:
        """
        Check if user exists by username.

        Args:
            username: Username to check

        Returns:
            True if exists, False otherwise
        """
        user = await self.get_by_username(username)
        return user is not None

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Get all active users.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of active users
        """
        return await self.get_multi(skip=skip, limit=limit, is_active=True)
