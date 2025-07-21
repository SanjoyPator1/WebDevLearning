from fastapi import Depends, HTTPException, status
from typing import List
from app.dependencies.auth import CurrentUser, get_current_user

class PermissionChecker:
    """Permission checking utilities using callable class pattern"""
    
    def __init__(self, required_roles: List[str]):
        self.required_roles = required_roles
    
    def __call__(self, current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        """
        The __call__ method makes this class instance callable like a function
        
        When you create: require_admin = PermissionChecker(["admin"])
        You can then use: require_admin() just like a function
        
        This is Python's "callable object" pattern - any object with __call__ can be used like a function
        """
        if current_user.role not in self.required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.required_roles)}"
            )
        return current_user

# How the callable pattern works:
# 1. require_admin = PermissionChecker(["admin"])  <- Creates instance with roles
# 2. In endpoint: Depends(require_admin)  <- FastAPI calls require_admin() which triggers __call__
# 3. The __call__ method receives current_user and checks permissions

# Pre-defined permission dependencies
require_admin = PermissionChecker(["admin"])
require_user_or_admin = PermissionChecker(["user", "admin"])
require_any_authenticated = PermissionChecker(["guest", "user", "admin"])

def check_task_owner_or_admin(
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Check if user can access/modify a specific task
    Admins can access any task, users can only access their own
    """
    # In a real app, you'd check task ownership from database
    # For learning purposes, we'll allow all authenticated users
    if current_user.is_admin():
        return current_user
    
    # In real implementation:
    # task = get_task_from_db(task_id)
    # if task.owner_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
    return current_user

def check_file_upload_permission(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Check if user can upload files"""
    if current_user.role == "guest":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guests cannot upload files"
        )
    return current_user