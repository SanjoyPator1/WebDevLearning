"""
Authentication endpoints.
"""

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordRequestForm


from app.schemas.user import User, UserCreate
from app.schemas.token import Token, RefreshTokenRequest


router = APIRouter()

dummy_user: User = {
    "id": 1,
    "email": "john.doe@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "is_active": True,
    "is_superuser": False,
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
}

dummy_token : Token = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake_access_token",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake_refresh_token",
    "token_type": "bearer",
}

@router.post("/register",response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate
):
    """
    Register a new user.

    Args:
        user_in: User registration data
        user_service: User service instance

    Returns:
        Created user

    Raises:
        HTTPException: If email or username already exists
    """

    return dummy_user

@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    Login with username/email and password.

    Args:
        form_data: OAuth2 form with username and password
        user_service: User service instance

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """

    return dummy_token

@router.post("refresh", response_model=Token)
async def refresh(
    refresh_request: RefreshTokenRequest,
) -> Token:
    """
    Refresh access token using refresh token.

    Args:
        refresh_request: Refresh token request
        user_service: User service instance

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """

    return dummy_token

    

