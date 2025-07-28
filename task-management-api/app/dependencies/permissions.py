from fastapi import Depends, HTTPException, status
from typing import List, Callable
from app.dependencies.oauth2 import get_current_user
from app.models.user import User

class RoleChecker:
    """Role-based access control checker"""
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if current user has required role
        
        Role hierarchy (each level includes permissions of lower levels):
        - guest: basic read access
        - user: read + write own resources
        - admin: full access to all resources
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}. Your role: {current_user.role}"
            )
        return current_user

# Pre-defined role checkers
require_admin = RoleChecker(["admin"])
require_user_or_admin = RoleChecker(["user", "admin"])  
require_any_role = RoleChecker(["guest", "user", "admin"])

def check_resource_owner_or_admin(
    resource_owner_id: int,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Check if user owns resource or is admin
    Useful for endpoints where users can only access their own data
    """
    if current_user.role == "admin" or current_user.id == resource_owner_id:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. You can only access your own resources."
    )

def admin_only(current_user: User = Depends(get_current_user)) -> User:
    """Strict admin-only access"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user