from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RefreshTokenRequest, UserRegistration, Token, UserProfile, PasswordChange
from app.services.user_service import UserService, UserCreate
from app.dependencies.user_service import get_user_service
from app.security.jwt_handler import JWTManager
from app.security.password import PasswordManager
from app.dependencies.oauth2 import get_current_user, get_current_active_user
from app.dependencies.permissions import require_admin
from app.config import settings
from app.models.user import User
from app.dependencies.database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegistration,
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db)
):
    is_strong, issues = PasswordManager.is_password_strong(user_data.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password requirements not met: {', '.join(issues)}"
        )
    try:
        user_create = UserCreate(email=user_data.email, password=user_data.password, full_name=user_data.username)
        new_user = await user_service.create_user(user_create)
        await db.commit()
        return UserProfile(
            id=str(new_user.id),
            username=new_user.full_name,
            email=new_user.email,
            role="user",  # Adjust if you add roles to the model
            is_active=new_user.is_active,
            created_at=new_user.created_at,
            last_login=None
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), user_service: UserService = Depends(get_user_service)):
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = JWTManager.create_access_token(user)
    # Optionally implement refresh token logic
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        refresh_token=None
    )

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    return UserProfile(
        id=str(current_user.id),
        username=current_user.full_name,
        email=current_user.email,
        role="user",  # Adjust if you add roles to the model
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=None
    )

@router.put("/me/password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user)
):
    """
    Change current user's password
    Requires authentication and current password verification
    """
    
    # Verify current password
    if not current_user.check_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    is_strong, issues = PasswordManager.is_password_strong(password_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New password requirements not met: {', '.join(issues)}"
        )
    
    # Hash new password and update user
    new_hashed = PasswordManager.hash_password(password_data.new_password)
    
    # Update in database (SQLAlchemy implementation needed)
    # TODO: Implement password change using UserService and SQLAlchemy
    # Example: await user_service.update_password(current_user.id, new_hashed)
    return {"message": "Password changed successfully"}

@router.get("/users", response_model=List[UserProfile])
async def list_users(
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """Get list of all users (admin only)"""
    users = await user_service.list_users()
    return [
        UserProfile(
            id=str(user.id),
            username=user.full_name,
            email=user.email,
            role=getattr(user, "role", "user"),
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=getattr(user, "last_login", None)
        )
        for user in users
    ]

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: Dict[str, str],
    current_user: User = Depends(require_admin)
):
    """
    Update user role (admin only)
    """
    allowed_roles = ["guest", "user", "admin"]
    role = new_role.get("role")
    
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed roles: {', '.join(allowed_roles)}"
        )
    # TODO: Implement role update using UserService and SQLAlchemy
    success = False # Not implemented yet
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": f"User role updated to {role}"}

@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_admin)
):
    """
    Deactivate user account (admin only)
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    # TODO: Implement deactivation using UserService and SQLAlchemy
    success = False # Not implemented yet
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User account deactivated"}

@router.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_data: RefreshTokenRequest): 
    """Get new access token using refresh token"""
    try:
        payload = JWTManager.verify_token(refresh_data.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        # TODO: Implement user lookup using UserService and SQLAlchemy
        user = None # Not implemented yet
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
            "email": user.email
        }
        access_token = JWTManager.create_access_token(data=token_data)
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )