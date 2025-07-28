from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.engine import get_database_session
from app.services.user_service import UserService

def get_user_service(db: AsyncSession = Depends(get_database_session)) -> UserService:
    return UserService(db) 