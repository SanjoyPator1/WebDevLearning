from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Dict, Any, List
from app.schemas.auth import RefreshTokenRequest

# Import our authentication components
from app.schemas.auth import UserRegistration, UserLogin, Token, UserProfile, PasswordChange
from app.database.users import UserManager, User
from app.security.jwt_handler import JWTManager
from app.security.password import PasswordManager
from app.dependencies.oauth2 import get_current_user, get_current_active_user
from app.dependencies.permissions import require_admin
from app.config import settings

# Create authentication router
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistration):
    """
    Register a new user account
    
    Process:
    1. Validate input data (Pydantic handles this)
    2. Check password strength
    3. Create user with hashed password
    4. Return user profile (without password)
    """
    try:
        # Create new user (UserManager handles validation and hashing)
        new_user = UserManager.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role
        )
        
        # Return user profile (password is excluded)
        return UserProfile(**new_user.to_dict())
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2-compatible login endpoint
    
    OAuth2PasswordRequestForm automatically handles:
    - username field (can be username or email)
    - password field
    - optional scope field
    - Content-Type: application/x-www-form-urlencoded
    
    This is the standard OAuth2 "password" flow
    """
    
    # Authenticate user
    user = UserManager.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token with user info
    token_data = {
        "sub": user.username,  # Subject (standard JWT claim)
        "user_id": user.id,
        "role": user.role,
        "email": user.email
    }
    
    # Generate access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = JWTManager.create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    # Generate refresh token
    refresh_token = JWTManager.create_refresh_token(data=token_data)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
        refresh_token=refresh_token
    )

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get current user's profile
    Requires valid JWT token in Authorization header
    """
    return UserProfile(**current_user.to_dict())

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
    
    # Update in database (simplified for our mock database)
    for user_data in UserManager.users_db:
        if user_data["id"] == current_user.id:
            user_data["hashed_password"] = new_hashed
            break
    
    return {"message": "Password changed successfully"}

@router.get("/users", response_model=List[UserProfile])
async def list_users(current_user: User = Depends(require_admin)):
    """Get list of all users (admin only)"""
    users = UserManager.get_all_users()
    return [UserProfile(**user.to_dict()) for user in users]

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
    
    success = UserManager.update_user_role(user_id, role)
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
    
    success = UserManager.deactivate_user(user_id)
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
        # Use refresh_data.refresh_token instead of refresh_token
        payload = JWTManager.verify_token(refresh_data.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user = UserManager.get_user_by_id(payload.get("user_id"))
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