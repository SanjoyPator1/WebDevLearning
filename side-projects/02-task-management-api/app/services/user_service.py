from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.security.password import PasswordManager
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import SQLAlchemyError

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    # Optionally add more fields as needed

class UserService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        try:
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user and PasswordManager.verify_password(password, user.password_hash):
                return user
            return None
        except SQLAlchemyError:
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            result = await self.db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            result = await self.db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            return None

    async def create_user(self, user_data: UserCreate) -> User:
        hashed_password = PasswordManager.hash_password(user_data.password)
        user = User(
            email=user_data.email,
            password_hash=hashed_password,
            full_name=user_data.full_name,
            is_active=True,
            email_verified=False
        )
        self.db.add(user)
        await self.db.flush()  # To get user.id
        return user 
    
    async def list_users(self) -> list[User]:
        try:
            result = await self.db.execute(select(User))
            return result.scalars().all()
        except SQLAlchemyError:
            return []