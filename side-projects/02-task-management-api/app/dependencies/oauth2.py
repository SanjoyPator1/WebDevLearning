from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.security.jwt_handler import JWTManager
from app.models.user import User
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.services.user_service import UserService
from app.dependencies.user_service import get_user_service

# OAuth2 password bearer scheme
# This tells FastAPI to look for "Authorization: Bearer <token>" headers
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",  # Where to get tokens
    scopes={
        "read": "Read access",
        "write": "Write access", 
        "admin": "Admin access"
    }
)

# Dependency functions (these are what you use in your endpoints)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme), user_service: UserService = Depends(get_user_service)) -> Optional[User]:
    """Get current user if authenticated, None if not"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user = await user_service.get_user_by_id(user_id)
        return user if user and user.is_active else None
    except Exception:
        return None