"""
User service with business logic.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service layer for user-related business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize user service with database session."""
        self.repository = UserRepository(db)

    async def get_user(self, user_id: int) -> User:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User instance

        Raises:
            HTTPException: If user not found
        """
        user = await self.repository.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        return await self.repository.get_by_email(email)

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return await self.repository.get_by_username(username)

    async def authenticate(self, username: str, password: str) -> User | None:
        """
        Authenticate user with username and password.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User instance if authentication successful, None otherwise
        """
        user = await self.repository.get_by_email_or_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    async def create_user(self, user_in: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_in: User creation data

        Returns:
            Created user instance

        Raises:
            HTTPException: If email or username already exists
        """
        # Check if email exists
        if await self.repository.exists_by_email(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Check if username exists
        if await self.repository.exists_by_username(user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        # Create user with hashed password
        user_data = user_in.model_dump(exclude={"password"})
        user_data["hashed_password"] = get_password_hash(user_in.password)

        return await self.repository.create(user_data)

    async def update_user(self, user_id: int, user_in: UserUpdate) -> User:
        """
        Update user information.

        Args:
            user_id: User ID
            user_in: User update data

        Returns:
            Updated user instance

        Raises:
            HTTPException: If user not found or validation fails
        """
        user = await self.get_user(user_id)

        # Check if email is being changed and already exists
        if user_in.email and user_in.email != user.email:
            if await self.repository.exists_by_email(user_in.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Check if username is being changed and already exists
        if user_in.username and user_in.username != user.username:
            if await self.repository.exists_by_username(user_in.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        # Prepare update data
        update_data = user_in.model_dump(exclude_unset=True, exclude={"password"})

        # Hash password if provided
        if user_in.password:
            update_data["hashed_password"] = get_password_hash(user_in.password)

        return await self.repository.update(user, update_data)

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted

        Raises:
            HTTPException: If user not found
        """
        user = await self.get_user(user_id)
        return await self.repository.delete(user.id)

    async def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination."""
        return await self.repository.get_multi(skip=skip, limit=limit)
