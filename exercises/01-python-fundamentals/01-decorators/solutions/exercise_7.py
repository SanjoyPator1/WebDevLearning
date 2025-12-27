"""
Exercise 7: Authorization Decorator

Create a decorator that checks user permissions.
See EXERCISES.md for full requirements.
"""

from functools import wraps


# Global user object (in real app, this would be request context)
current_user = {"name": "Alice", "roles": ["admin", "editor"]}


def require_role(required_role):
    """
    TODO: Implement authorization decorator
    
    Requirements:
    - Accept a role name as parameter
    - Check against current_user object
    - Raise PermissionError if user doesn't have the role
    - Work with both functions and methods
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            pass  # Replace with your implementation
        return wrapper
    return decorator


# Test cases
if __name__ == "__main__":
    @require_role("admin")
    def delete_user(user_id):
        return f"Deleted user {user_id}"
    
    @require_role("superadmin")
    def delete_all_users():
        return "Deleted all users"
    
    @require_role("editor")
    def edit_post(post_id):
        return f"Edited post {post_id}"
    
    # Test with admin user
    print("Testing with admin user:")
    try:
        print(delete_user(123))
        print(edit_post(456))
    except PermissionError as e:
        print(f"Permission denied: {e}")
    
    # Test without required role
    print("\nTesting without superadmin role:")
    try:
        print(delete_all_users())
    except PermissionError as e:
        print(f"Permission denied: {e}")
    
    # Change user
    print("\nChanging to superadmin user:")
    current_user["roles"].append("superadmin")
    print(delete_all_users())