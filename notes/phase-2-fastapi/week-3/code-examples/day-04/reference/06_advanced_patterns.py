"""
06_advanced_patterns.py

Topics covered:
- Dependency overrides (for testing)
- Global dependencies
- Yielding dependencies with cleanup
- Dependency with both setup and teardown
- Sub-dependencies pattern

Run: uvicorn 06_advanced_patterns:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException
from typing import Generator
import time

app = FastAPI()


# ============================================================================
# YIELDING DEPENDENCIES WITH CLEANUP
# ============================================================================

class DatabaseConnection:
    """Simulated database with resource management"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connected = False
    
    def connect(self):
        print(f"Connecting to {self.connection_string}")
        self.connected = True
    
    def disconnect(self):
        print(f"Disconnecting from {self.connection_string}")
        self.connected = False
    
    def execute(self, query: str):
        if not self.connected:
            raise Exception("Not connected")
        return f"Executed: {query}"


def get_db_connection() -> Generator[DatabaseConnection, None, None]:
    """
    Dependency with setup and teardown.
    Code before yield: setup
    Code after yield: cleanup (always runs)
    """
    db = DatabaseConnection("postgresql://localhost/mydb")
    db.connect()
    
    try:
        yield db
    finally:
        db.disconnect()


@app.get("/db-query")
async def db_query(db: DatabaseConnection = Depends(get_db_connection)):
    """
    Database connection automatically managed.
    Connect -> Execute -> Disconnect
    """
    result = db.execute("SELECT * FROM users")
    return {"result": result, "connected": db.connected}


# ============================================================================
# DEPENDENCY WITH TIMING AND LOGGING
# ============================================================================

def log_time() -> Generator[None, None, None]:
    """
    Measure request processing time.
    Demonstrates dependencies used purely for side effects.
    """
    start_time = time.time()
    print(f"Request started at {start_time}")
    
    yield
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"Request finished at {end_time}")
    print(f"Duration: {duration:.4f} seconds")


@app.get("/timed-endpoint", dependencies=[Depends(log_time)])
async def timed_endpoint():
    """
    Request timing logged automatically.
    Check console for timing output.
    """
    time.sleep(0.1)  # Simulate work
    return {"message": "Done"}


# ============================================================================
# NESTED/SUB-DEPENDENCIES PATTERN
# ============================================================================

class Config:
    """Application configuration"""
    
    def __init__(self):
        self.api_key = "secret-key"
        self.timeout = 30


def get_config() -> Config:
    """Provide application config"""
    return Config()


class ApiClient:
    """External API client that needs config"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://api.example.com"
    
    def call_api(self, endpoint: str):
        return f"Calling {self.base_url}/{endpoint} with key {self.config.api_key}"


def get_api_client(config: Config = Depends(get_config)) -> ApiClient:
    """
    ApiClient depends on Config.
    Sub-dependency pattern: get_api_client -> get_config
    """
    return ApiClient(config)


@app.get("/external-call")
async def external_call(client: ApiClient = Depends(get_api_client)):
    """
    Handler receives fully configured API client.
    Dependencies resolved: get_api_client -> get_config
    """
    result = client.call_api("users")
    return {"result": result}


# ============================================================================
# DEPENDENCY CACHING WITHIN REQUEST
# ============================================================================

def expensive_setup():
    """Simulates expensive operation"""
    print("Running expensive setup...")
    time.sleep(0.1)
    return {"data": "expensive result"}


def service_one(data: dict = Depends(expensive_setup)):
    """Service that uses expensive setup"""
    return {"service": "one", "data": data}


def service_two(data: dict = Depends(expensive_setup)):
    """Another service using same expensive setup"""
    return {"service": "two", "data": data}


@app.get("/multi-service")
async def multi_service(
    s1: dict = Depends(service_one),
    s2: dict = Depends(service_two)
):
    """
    Both services depend on expensive_setup.
    It runs only ONCE per request (cached).
    Check console: "Running expensive setup..." appears once.
    """
    return {"service_one": s1, "service_two": s2}


# ============================================================================
# CONDITIONAL DEPENDENCIES
# ============================================================================

def get_current_user_id(user_id: int = None) -> int | None:
    """Simulated user extraction (could be from token)"""
    return user_id


def require_ownership(item_id: int):
    """
    Dependency factory that checks resource ownership.
    Returns a dependency function.
    """
    
    def ownership_checker(user_id: int | None = Depends(get_current_user_id)):
        if user_id is None:
            raise HTTPException(401, "Not authenticated")
        
        item_owners = {1: 100, 2: 100, 3: 200}
        
        if item_owners.get(item_id) != user_id:
            raise HTTPException(403, "Not authorized to access this item")
        
        return user_id
    
    return ownership_checker


@app.get("/items/{item_id}")
async def get_item(
    item_id: int,
    user_id: int = Depends(require_ownership(item_id))
):
    """
    Dynamic ownership checking based on item_id.
    Test: /items/1?user_id=100 (success)
    Test: /items/1?user_id=200 (forbidden)
    """
    return {
        "item_id": item_id,
        "owner": user_id,
        "message": "Access granted"
    }


# ============================================================================
# LAYERED DEPENDENCIES (Real-world pattern)
# ============================================================================

class DatabaseSession:
    """Layer 1: Database"""
    
    def __init__(self):
        self.connection = "connected"
    
    def query(self, sql: str):
        return f"Result of: {sql}"


class Repository:
    """Layer 2: Data access"""
    
    def __init__(self, db: DatabaseSession):
        self.db = db
    
    def get_user(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")


class UserService:
    """Layer 3: Business logic"""
    
    def __init__(self, repo: Repository):
        self.repo = repo
    
    def get_user_profile(self, user_id: int):
        user_data = self.repo.get_user(user_id)
        return {
            "user_data": user_data,
            "profile_complete": True
        }


def get_db_session() -> DatabaseSession:
    """Provide database session"""
    return DatabaseSession()


def get_repository(db: DatabaseSession = Depends(get_db_session)) -> Repository:
    """Provide repository with database"""
    return Repository(db)


def get_user_service(repo: Repository = Depends(get_repository)) -> UserService:
    """Provide user service with repository"""
    return UserService(repo)


@app.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    """
    Three-layer architecture through dependencies:
    Handler -> UserService -> Repository -> DatabaseSession
    
    Each layer depends on the layer below it.
    Clean separation of concerns.
    """
    return service.get_user_profile(user_id)


# ============================================================================
# DEPENDENCY WITH VALIDATION AND TRANSFORMATION
# ============================================================================

class QueryFilter:
    """Dependency that validates and transforms query parameters"""
    
    def __init__(
        self,
        status: str = None,
        min_price: float = None,
        max_price: float = None
    ):
        self.validate_status(status)
        self.validate_price_range(min_price, max_price)
        
        self.status = status
        self.min_price = min_price
        self.max_price = max_price
    
    @staticmethod
    def validate_status(status: str | None):
        """Validate status parameter"""
        if status and status not in ["active", "inactive", "pending"]:
            raise HTTPException(400, f"Invalid status: {status}")
    
    @staticmethod
    def validate_price_range(min_price: float | None, max_price: float | None):
        """Validate price range"""
        if min_price and max_price and min_price > max_price:
            raise HTTPException(400, "min_price cannot be greater than max_price")
    
    def to_sql_where(self) -> str:
        """Convert to SQL WHERE clause"""
        conditions = []
        
        if self.status:
            conditions.append(f"status = '{self.status}'")
        if self.min_price:
            conditions.append(f"price >= {self.min_price}")
        if self.max_price:
            conditions.append(f"price <= {self.max_price}")
        
        return " AND ".join(conditions) if conditions else "1=1"


@app.get("/products")
async def get_products(filters: QueryFilter = Depends()):
    """
    Complex query filtering with validation.
    Test: /products?status=active&min_price=10&max_price=100
    Test: /products?status=invalid (returns 400)
    Test: /products?min_price=100&max_price=10 (returns 400)
    """
    sql_where = filters.to_sql_where()
    return {
        "filters": {
            "status": filters.status,
            "min_price": filters.min_price,
            "max_price": filters.max_price
        },
        "sql_where": sql_where
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
