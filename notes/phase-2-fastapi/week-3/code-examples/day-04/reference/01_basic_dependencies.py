"""
01_basic_dependencies.py

Topics covered:
- Basic dependency injection concept
- Function dependencies
- Dependencies with parameters
- Reusable dependencies
- Multiple dependencies

Run: uvicorn 01_basic_dependencies:app --reload
"""

from fastapi import FastAPI, Depends, Query, Header, Cookie, HTTPException

app = FastAPI()


# ============================================================================
# BASIC FUNCTION DEPENDENCIES
# ============================================================================

def get_hello():
    """Simplest dependency - no parameters, returns a string"""
    return "Hello from dependency!"


@app.get("/greet")
async def greet(message: str = Depends(get_hello)):
    return {"message": message}


# ============================================================================
# DEPENDENCIES WITH PARAMETERS
# ============================================================================

def get_pagination(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Dependency that extracts and validates pagination parameters"""
    return {
        "skip": skip,
        "limit": limit,
        "message": f"Showing items {skip} to {skip + limit}"
    }


@app.get("/items")
async def list_items(pagination: dict = Depends(get_pagination)):
    """Handler receives processed pagination info"""
    items = [{"id": i, "name": f"Item {i}"} for i in range(100)]
    
    start = pagination["skip"]
    end = start + pagination["limit"]
    
    return {
        "items": items[start:end],
        "pagination": pagination
    }


# ============================================================================
# REUSABLE DEPENDENCIES
# ============================================================================

def common_parameters(
    q: str | None = Query(None, min_length=3),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Common query parameters used across multiple endpoints"""
    return {"q": q, "skip": skip, "limit": limit}


@app.get("/search/items")
async def search_items(commons: dict = Depends(common_parameters)):
    return {
        "query": commons["q"],
        "items": ["item1", "item2"],
        "pagination": {"skip": commons["skip"], "limit": commons["limit"]}
    }


@app.get("/search/users")
async def search_users(commons: dict = Depends(common_parameters)):
    return {
        "query": commons["q"],
        "users": ["user1", "user2"],
        "pagination": {"skip": commons["skip"], "limit": commons["limit"]}
    }


# ============================================================================
# MULTIPLE DEPENDENCIES
# ============================================================================

def verify_token(x_token: str = Header(...)):
    """Verify authentication token"""
    if x_token != "secret-token":
        raise HTTPException(401, "Invalid token")
    return x_token


def verify_key(x_key: str = Header(...)):
    """Verify API key"""
    if x_key != "secret-key":
        raise HTTPException(401, "Invalid key")
    return x_key


def get_session(session_id: str = Cookie(...)):
    """Get session from cookie"""
    sessions = {"abc123": {"user_id": 1}}
    if session_id not in sessions:
        raise HTTPException(401, "Invalid session")
    return sessions[session_id]


@app.get("/secure-resource")
async def secure_resource(
    token: str = Depends(verify_token),
    key: str = Depends(verify_key),
    session: dict = Depends(get_session)
):
    """
    Requires three validations:
    - Valid token (X-Token header)
    - Valid key (X-Key header)
    - Valid session (session_id cookie)
    
    Test with:
    curl -H "X-Token: secret-token" -H "X-Key: secret-key" \
         -b "session_id=abc123" http://localhost:8000/secure-resource
    """
    return {
        "message": "Access granted",
        "token": token,
        "key": key,
        "session": session
    }


# ============================================================================
# DIFFERENT RETURN TYPES
# ============================================================================

def get_message() -> str:
    return "Hello"


def get_config() -> dict:
    return {"debug": True, "version": "1.0.0"}


def get_items_list() -> list[str]:
    return ["item1", "item2", "item3"]


class Database:
    def __init__(self):
        self.connection = "connected"
    
    def query(self, sql: str):
        return f"Executing: {sql}"


def get_database() -> Database:
    return Database()


def log_request() -> None:
    """Side effect only - logs request"""
    print("Request received")


@app.get("/demo")
async def demo(
    message: str = Depends(get_message),
    config: dict = Depends(get_config),
    items: list[str] = Depends(get_items_list),
    db: Database = Depends(get_database),
    _: None = Depends(log_request)  # Ignore return value
):
    """Demonstrates different dependency return types"""
    return {
        "message": message,
        "config": config,
        "items": items,
        "db_status": db.connection
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
