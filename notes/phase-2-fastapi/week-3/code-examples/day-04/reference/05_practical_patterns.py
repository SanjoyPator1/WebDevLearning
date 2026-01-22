"""
05_practical_patterns.py

Topics covered:
- Database session management (simulated)
- Authentication and authorization
- Request context
- Pagination helpers
- Common production patterns

Run: uvicorn 05_practical_patterns:app --reload
"""

from fastapi import FastAPI, Depends, Header, HTTPException, Query
from typing import Generator

app = FastAPI()


# ============================================================================
# DATABASE SESSION PATTERN (Simulated)
# ============================================================================

class DatabaseSession:
    """Simulated database session"""
    
    def __init__(self):
        self.connection = "connected"
        print("Database session created")
    
    def query(self, sql: str):
        return f"Executing: {sql}"
    
    def close(self):
        print("Database session closed")


def get_db() -> Generator[DatabaseSession, None, None]:
    """
    Database dependency with proper cleanup.
    Uses yield to ensure close() is called.
    """
    db = DatabaseSession()
    try:
        yield db
    finally:
        db.close()


@app.get("/users/{user_id}")
async def get_user(user_id: int, db: DatabaseSession = Depends(get_db)):
    """
    Database session automatically provided and cleaned up.
    Notice: session closed after response.
    """
    result = db.query(f"SELECT * FROM users WHERE id = {user_id}")
    return {"user_id": user_id, "query": result}


# ============================================================================
# AUTHENTICATION PATTERN
# ============================================================================

USERS_DB = {
    "user_token_123": {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com",
        "role": "user"
    },
    "admin_token_456": {
        "id": 2,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin"
    }
}


def get_token_from_header(authorization: str = Header(...)) -> str:
    """Extract and validate token format"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    return authorization[7:]  # Remove "Bearer "


def get_current_user(token: str = Depends(get_token_from_header)) -> dict:
    """Get authenticated user from token"""
    user = USERS_DB.get(token)
    if not user:
        raise HTTPException(401, "Invalid authentication credentials")
    return user


def get_current_active_user(user: dict = Depends(get_current_user)) -> dict:
    """Ensure user is active (additional check)"""
    if user.get("disabled", False):
        raise HTTPException(403, "User account is disabled")
    return user


@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_active_user)):
    """
    Get current authenticated user.
    Test: curl -H "Authorization: Bearer user_token_123" \
          http://localhost:8000/auth/me
    """
    return current_user


# ============================================================================
# AUTHORIZATION PATTERN
# ============================================================================

def require_role(required_role: str):
    """Dependency factory for role-based access control"""
    
    def role_checker(user: dict = Depends(get_current_active_user)) -> dict:
        if user["role"] != required_role:
            raise HTTPException(
                403,
                f"Insufficient permissions. Required role: {required_role}"
            )
        return user
    
    return role_checker


@app.get("/admin/dashboard")
async def admin_dashboard(admin: dict = Depends(require_role("admin"))):
    """
    Admin-only endpoint.
    Test with admin: curl -H "Authorization: Bearer admin_token_456" \
                     http://localhost:8000/admin/dashboard
    Test with user: Returns 403
    """
    return {"message": "Admin dashboard", "admin": admin}


@app.get("/user/profile")
async def user_profile(user: dict = Depends(require_role("user"))):
    """
    User role required.
    Test: curl -H "Authorization: Bearer user_token_123" \
          http://localhost:8000/user/profile
    """
    return {"message": "User profile", "user": user}


# ============================================================================
# REQUEST CONTEXT PATTERN
# ============================================================================

class RequestContext:
    """Holds request-scoped data"""
    
    def __init__(
        self,
        user_agent: str = Header(None),
        accept_language: str = Header("en", alias="Accept-Language"),
    ):
        self.user_agent = user_agent
        self.language = accept_language.split(",")[0]  # Get primary language
        self.request_id = self._generate_request_id()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())


@app.get("/context-demo")
async def context_demo(context: RequestContext = Depends()):
    """
    Demonstrates request context gathering.
    Test: curl -H "Accept-Language: fr,en" http://localhost:8000/context-demo
    """
    return {
        "request_id": context.request_id,
        "language": context.language,
        "user_agent": context.user_agent
    }


# ============================================================================
# PAGINATION HELPER PATTERN
# ============================================================================

class PaginationParams:
    """Reusable pagination with calculated values"""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page")
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size
        self.limit = page_size
    
    def get_slice(self, items: list) -> list:
        """Helper to slice a list based on pagination"""
        return items[self.skip:self.skip + self.limit]
    
    def get_metadata(self, total: int) -> dict:
        """Generate pagination metadata"""
        total_pages = (total + self.page_size - 1) // self.page_size
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": self.page < total_pages,
            "has_previous": self.page > 1
        }


@app.get("/paginated-items")
async def paginated_items(pagination: PaginationParams = Depends()):
    """
    Endpoint with pagination helper.
    Test: http://localhost:8000/paginated-items?page=2&page_size=5
    """
    all_items = [{"id": i, "name": f"Item {i}"} for i in range(1, 51)]
    
    return {
        "items": pagination.get_slice(all_items),
        "pagination": pagination.get_metadata(len(all_items))
    }


# ============================================================================
# COMBINED PATTERN: DB + AUTH + PAGINATION
# ============================================================================

@app.get("/my-orders")
async def get_my_orders(
    user: dict = Depends(get_current_active_user),
    pagination: PaginationParams = Depends(),
    db: DatabaseSession = Depends(get_db)
):
    """
    Real-world endpoint combining multiple patterns:
    - Authentication (user)
    - Pagination (pagination)
    - Database (db)
    
    Test: curl -H "Authorization: Bearer user_token_123" \
          "http://localhost:8000/my-orders?page=1&page_size=10"
    """
    query = f"SELECT * FROM orders WHERE user_id = {user['id']} LIMIT {pagination.limit} OFFSET {pagination.skip}"
    result = db.query(query)
    
    orders = [{"id": i, "total": 100 * i} for i in range(1, 26)]
    
    return {
        "orders": pagination.get_slice(orders),
        "user": user["username"],
        "pagination": pagination.get_metadata(len(orders)),
        "query": result
    }


# ============================================================================
# OPTIONAL AUTHENTICATION PATTERN
# ============================================================================

def get_current_user_optional(
    authorization: str = Header(None)
) -> dict | None:
    """
    Optional authentication - returns None if no token.
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]
    return USERS_DB.get(token)


@app.get("/public-items")
async def public_items(user: dict | None = Depends(get_current_user_optional)):
    """
    Works with or without authentication.
    Authenticated users might get personalized results.
    
    Test without auth: curl http://localhost:8000/public-items
    Test with auth: curl -H "Authorization: Bearer user_token_123" \
                    http://localhost:8000/public-items
    """
    if user:
        return {
            "items": ["item1", "item2", "item3"],
            "message": f"Personalized for {user['username']}"
        }
    else:
        return {
            "items": ["item1", "item2"],
            "message": "Generic results"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
