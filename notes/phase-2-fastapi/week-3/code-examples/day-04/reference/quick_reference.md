# Dependency Injection Quick Reference

## Basic Patterns

### Simple Function Dependency
```python
def get_value():
    return "value"

@app.get("/")
async def endpoint(val: str = Depends(get_value)):
    return {"value": val}
```

### Dependency with Parameters
```python
def get_pagination(skip: int = Query(0), limit: int = Query(10)):
    return {"skip": skip, "limit": limit}

@app.get("/items")
async def list_items(pagination: dict = Depends(get_pagination)):
    return pagination
```

### Class Dependency (Shortcut)
```python
class Pagination:
    def __init__(self, skip: int = Query(0), limit: int = Query(10)):
        self.skip = skip
        self.limit = limit

@app.get("/items")
async def list_items(pagination: Pagination = Depends()):
    return {"skip": pagination.skip}
```

### Dependency Chain
```python
def get_token(authorization: str = Header(...)):
    return authorization.replace("Bearer ", "")

def get_user(token: str = Depends(get_token)):
    return {"user_id": 1, "token": token}

@app.get("/me")
async def me(user: dict = Depends(get_user)):
    return user
```

### Yielding Dependency (Cleanup)
```python
def get_db():
    db = DatabaseConnection()
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
async def get_users(db = Depends(get_db)):
    return db.query("SELECT * FROM users")
```

### Path Operation Dependencies
```python
def verify_token(x_token: str = Header(...)):
    if x_token != "secret":
        raise HTTPException(401)

@app.get("/items", dependencies=[Depends(verify_token)])
async def read_items():
    return {"items": []}
```

### Dependency Factory
```python
def require_role(role: str):
    def checker(user = Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(403)
        return user
    return checker

@app.get("/admin", dependencies=[Depends(require_role("admin"))])
async def admin_panel():
    return {"message": "Admin access"}
```

## Authentication Patterns

### Basic Auth Chain
```python
def get_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid format")
    return authorization[7:]

def verify_token(token: str = Depends(get_token)):
    if token not in valid_tokens:
        raise HTTPException(401, "Invalid token")
    return token

def get_current_user(token: str = Depends(verify_token)):
    return users[token]

@app.get("/protected")
async def protected(user = Depends(get_current_user)):
    return user
```

### Optional Authentication
```python
def get_current_user_optional(authorization: str = Header(None)):
    if not authorization:
        return None
    token = authorization[7:]
    return users.get(token)

@app.get("/items")
async def read_items(user = Depends(get_current_user_optional)):
    if user:
        return {"items": personalized_items(user)}
    return {"items": public_items()}
```

## Testing Patterns

### Basic Override
```python
def get_mock_db():
    return MockDatabase()

def test_endpoint():
    app.dependency_overrides[get_db] = get_mock_db
    client = TestClient(app)
    response = client.get("/endpoint")
    app.dependency_overrides.clear()
```

### Pytest Fixture
```python
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db():
    app.dependency_overrides[get_db] = get_mock_db
    yield
    app.dependency_overrides.clear()

def test_with_fixture(client, mock_db):
    response = client.get("/endpoint")
    assert response.status_code == 200
```

## Common Mistakes to Avoid

### ❌ Don't call dependency manually
```python
@app.get("/items")
async def read_items():
    db = get_db()  # Wrong!
    return db.query()
```

### ✅ Let FastAPI inject it
```python
@app.get("/items")
async def read_items(db = Depends(get_db)):
    return db.query()
```

### ❌ Don't forget cleanup in yielding dependencies
```python
def get_db():
    db = DatabaseConnection()
    yield db
    # What if handler raises exception? db.close() won't run!
```

### ✅ Use try/finally
```python
def get_db():
    db = DatabaseConnection()
    try:
        yield db
    finally:
        db.close()  # Always runs
```

### ❌ Don't create stateful dependencies without external storage
```python
counter = 0  # This is global, not per-request!

def count_requests():
    counter += 1  # Wrong for counting requests
    return counter
```

### ✅ Use external storage for cross-request state
```python
def count_requests():
    count = redis.incr("request_count")
    return count
```

## When to Use What

| Use Case | Pattern |
|----------|---------|
| Simple extraction | Function dependency |
| Grouped parameters | Class dependency |
| Auth/validation | Dependency chain |
| Logging/metrics | Path operation dependency |
| Resource cleanup | Yielding dependency |
| Permission checking | Dependency factory |
| Testing | Dependency override |

## Dependency Resolution Order

```
Request arrives
    ↓
FastAPI inspects handler parameters
    ↓
Identifies dependencies (Depends(...))
    ↓
Builds dependency graph
    ↓
Resolves from bottom up
    ↓
Caches results per request
    ↓
Injects into handler
    ↓
Handler executes
    ↓
Response sent
    ↓
Cleanup (if using yield)
```

## Key Rules

1. Dependencies execute once per request (cached)
2. Dependencies execute before handler
3. If dependency raises HTTPException, handler doesn't run
4. Path operation dependencies don't inject values
5. Yielding dependencies always clean up (even on error)
6. Child dependencies resolve before parent
7. Type annotation matters for `Depends()` with no arg
