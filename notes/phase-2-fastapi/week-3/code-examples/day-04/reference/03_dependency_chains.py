"""
03_dependency_chains.py

Topics covered:
- Basic dependency chains
- Authentication chains (token -> verify -> user)
- Permission checking
- Dependency factories
- Multiple branches
- Result caching

Run: uvicorn 03_dependency_chains:app --reload
"""

from fastapi import FastAPI, Depends, Header, HTTPException

app = FastAPI()

# Mock data
USERS = {
    "token123": {"id": 1, "username": "alice", "role": "admin"},
    "token456": {"id": 2, "username": "bob", "role": "user"},
}

PERMISSIONS = {
    "admin": ["read", "write", "delete"],
    "user": ["read"],
}


# ============================================================================
# BASIC DEPENDENCY CHAIN
# ============================================================================

def get_token(authorization: str = Header(...)):
    """
    Level 3: Extract token from Authorization header
    Bottom of the chain - extracts raw data
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization format")
    return authorization.replace("Bearer ", "")


def verify_token(token: str = Depends(get_token)):
    """
    Level 2: Verify token
    Depends on: get_token
    """
    valid_tokens = {"secret123", "admin456"}
    if token not in valid_tokens:
        raise HTTPException(401, "Invalid token")
    return token


def get_current_user(token: str = Depends(verify_token)):
    """
    Level 1: Get user from verified token
    Depends on: verify_token -> get_token
    """
    users = {
        "secret123": {"id": 1, "username": "alice"},
        "admin456": {"id": 2, "username": "bob"},
    }
    return users[token]


@app.get("/me")
async def read_current_user(user: dict = Depends(get_current_user)):
    """
    Handler receives fully validated user.
    Chain: handler -> get_current_user -> verify_token -> get_token
    
    Test: curl -H "Authorization: Bearer secret123" http://localhost:8000/me
    """
    return user


# ============================================================================
# COMPLEX CHAIN: AUTH + ROLE + PERMISSIONS
# ============================================================================

def get_token_complex(authorization: str = Header(..., alias="Authorization")):
    """Extract token from header"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    return authorization.replace("Bearer ", "")


def validate_token(token: str = Depends(get_token_complex)):
    """Validate token exists in users database"""
    if token not in USERS:
        raise HTTPException(401, "Invalid token")
    return token


def get_current_user_complex(token: str = Depends(validate_token)):
    """Get user object from validated token"""
    return USERS[token]


# ============================================================================
# DEPENDENCY FACTORY - PERMISSION CHECKING
# ============================================================================

def require_permission(permission: str):
    """
    Dependency factory: returns a dependency function.
    This allows dynamic permission checking.
    """
    def permission_checker(user: dict = Depends(get_current_user_complex)):
        user_permissions = PERMISSIONS.get(user["role"], [])
        if permission not in user_permissions:
            raise HTTPException(403, "Permission denied")
        return user
    
    return permission_checker


@app.get("/profile")
async def get_profile(user: dict = Depends(get_current_user_complex)):
    """
    Anyone authenticated can access.
    Test: curl -H "Authorization: Bearer token123" http://localhost:8000/profile
    """
    return {"user": user}


@app.get("/admin/users")
async def list_users(user: dict = Depends(require_permission("write"))):
    """
    Requires 'write' permission (admin only).
    Test: curl -H "Authorization: Bearer token123" http://localhost:8000/admin/users
    """
    return {"users": list(USERS.values()), "requested_by": user}


@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: dict = Depends(require_permission("delete")),
):
    """
    Requires 'delete' permission (admin only).
    Test: curl -X DELETE -H "Authorization: Bearer token123" \
          http://localhost:8000/admin/users/1
    """
    return {"message": f"User {user_id} deleted", "deleted_by": admin}


# ============================================================================
# MULTIPLE BRANCHES WITH SHARED DEPENDENCIES
# ============================================================================

def get_database():
    """Simulated database connection"""
    print("Connecting to database")  # This prints only ONCE per request
    return {"db": "connected"}


def get_cache():
    """Simulated cache connection"""
    return {"cache": "connected"}


def get_user_repo(db=Depends(get_database)):
    """User repository - depends on database"""
    return {"repo": "users", "db": db}


def get_product_repo(db=Depends(get_database)):
    """Product repository - also depends on database"""
    return {"repo": "products", "db": db}


def get_current_user_from_repo(repo=Depends(get_user_repo)):
    """Get user from repository"""
    return {"id": 1, "username": "alice"}


def get_products(
    repo=Depends(get_product_repo),
    cache=Depends(get_cache),
):
    """Get products using repository and cache"""
    return [{"id": 1, "name": "Laptop"}]


@app.get("/user-products")
async def user_products(
    user=Depends(get_current_user_from_repo),
    products=Depends(get_products),
):
    """
    Demonstrates dependency branching and caching.
    Both branches depend on get_database, but it's called only once.
    
    Watch console: "Connecting to database" appears only once per request.
    """
    return {
        "user": user,
        "products": products
    }


# ============================================================================
# DEPENDENCY RESULT CACHING DEMONSTRATION
# ============================================================================

def expensive_operation():
    """Simulates expensive operation"""
    print("Performing expensive operation")
    return {"result": "expensive data"}


def service_a(data=Depends(expensive_operation)):
    """Service A uses expensive operation"""
    return {"service": "A", "data": data}


def service_b(data=Depends(expensive_operation)):
    """Service B also uses expensive operation"""
    return {"service": "B", "data": data}


@app.get("/cached-example")
async def cached_example(
    a=Depends(service_a),
    b=Depends(service_b),
):
    """
    Both services depend on expensive_operation.
    It runs only once per request (result is cached).
    
    Watch console: "Performing expensive operation" appears only once.
    """
    return {"service_a": a, "service_b": b}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
