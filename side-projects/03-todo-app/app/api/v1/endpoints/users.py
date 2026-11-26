"""
User management endpoints.
"""
from datetime import datetime 

from fastapi import APIRouter, status

from app.schemas.user import User, UserUpdate

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
@router.get("/me", response_model=User)
async def get_current_user_profile(

) -> User:
    """
    Get current user profile.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user data
    """

    return dummy_user

@router.put("/me", response_model=User)
async def update_current_user(
    user_in: UserUpdate,
) -> User:
    """
    Update current user profile.

    Args:
        user_in: User update data
        current_user: Current authenticated user
        user_service: User service instance

    Returns:
        Updated user data
    """

    updated_user = dummy_user.copy()  # Start from existing user
    updated_user.update(user_in.model_dump(exclude_unset=True))  # Merge new fields
    updated_user["updated_at"] = datetime.now()  # Update timestamp
    return updated_user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(

)->None:
    """
    Delete current user account.

    Args:
        current_user: Current authenticated user
        user_service: User service instance
    """
    return None

