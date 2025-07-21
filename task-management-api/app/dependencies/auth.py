from fastapi import Depends, HTTPException, status, Header
from typing import Optional, Dict, Any
import json
import base64

# Mock users database (in real app, this would be in a real database)
MOCK_USERS = {
    1: {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True
    },
    2: {
        "id": 2,
        "username": "user1",
        "email": "user1@example.com",
        "role": "user",
        "is_active": True
    },
    3: {
        "id": 3,
        "username": "guest",
        "email": "guest@example.com",
        "role": "guest",
        "is_active": True
    }
}

class CurrentUser:
    """Current user model"""
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data["id"]
        self.username = user_data["username"]
        self.email = user_data["email"]
        self.role = user_data["role"]
        self.is_active = user_data["is_active"]

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_user(self) -> bool:
        return self.role in ["user", "admin"]

    def can_edit_task(self, task_owner_id: int = None) -> bool:
        """Check if user can edit a task"""
        if self.is_admin():
            return True
        # In real app, you'd check if user owns the task
        return True
    
def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> CurrentUser:
    """
    Dependency to get current user from authorization header
    In a real app, this would validate JWT tokens
    """

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Simple mock authentication - in real app use JWT
        # Expected format: "Bearer user_id" (e.g., "Bearer 1")
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization format. Use: Bearer <user_id>",
                headers={"WWW-Authenticate": "Bearer"}
            )

        user_id = int(authorization.split(" ")[1])

        if user_id not in MOCK_USERS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID",
                headers={"WWW-Authenticate": "Bearer"}
            )

        user_data = MOCK_USERS[user_id]

        if not user_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )

        return CurrentUser(user_data)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use: Bearer <user_id>",
            headers={"WWW-Authenticate": "Bearer"}
        )

def get_optional_user(
    authorization: Optional[str] = Header(None)
) -> Optional[CurrentUser]:
    """
    Dependency to get current user, but don't require authentication
    Returns None if no auth provided
    """
    if not authorization:
        return None

    try:
        return get_current_user(authorization)
    except HTTPException:
        return None
