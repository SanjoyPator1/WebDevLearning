# Dependencies Module - Detailed Documentation

## 📚 Table of Contents

1. [What is Dependency Injection?](#what-is-dependency-injection)
2. [FastAPI Dependencies Explained](#fastapi-dependencies-explained)
3. [OAuth2PasswordBearer Setup](#oauth2passwordbearer-setup)
4. [Service Dependencies](#service-dependencies)
5. [Authentication Dependencies](#authentication-dependencies)
6. [Authorization Dependencies](#authorization-dependencies)
7. [How Everything Connects](#how-everything-connects)
8. [Complete Flow Examples](#complete-flow-examples)

---

## 🎯 What is Dependency Injection?

### The Problem Without Dependency Injection

```python
# ❌ BAD - Manual creation everywhere
@router.get("/users/me")
async def get_me():
    db = await AsyncSessionLocal()  # Create session manually
    try:
        service = UserService(db)   # Create service manually
        token = request.headers.get("Authorization")  # Get token manually
        payload = jwt.decode(token, SECRET_KEY)  # Decode manually
        user = await service.get_user(int(payload["sub"]))  # Get user manually
        return user
    finally:
        await db.close()  # Close manually
```

**Problems:**

- 🔴 Lots of boilerplate in every endpoint
- 🔴 Easy to forget cleanup (db.close())
- 🔴 Hard to test (can't mock dependencies)
- 🔴 Code duplication everywhere

### The Solution: Dependency Injection

```python
# ✅ GOOD - FastAPI handles everything
@router.get("/users/me")
async def get_me(current_user: CurrentUser):
    return current_user  # That's it!
```

**Benefits:**

- ✅ No boilerplate
- ✅ Automatic cleanup
- ✅ Easy to test (swap dependencies)
- ✅ Reusable across endpoints

---

## 🚀 FastAPI Dependencies Explained

### How Dependencies Work

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides database session."""
    async with AsyncSessionLocal() as session:
        yield session  # ← FastAPI injects this
        # Cleanup happens automatically after yield
```

**FastAPI magic:**

```python
@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    #                                   ↑
    #                     FastAPI calls get_db() here
    # db is now the yielded session
    result = await db.execute(select(User))
    return result.scalars().all()
    # After function returns, FastAPI continues get_db()
    # and runs cleanup code
```

**What happens:**

```
1. Request comes in → GET /users
2. FastAPI sees Depends(get_db)
3. Calls get_db()
4. Runs code until yield
5. Takes yielded value → session
6. Injects into function parameter → db
7. Endpoint function executes
8. Endpoint returns response
9. FastAPI continues get_db() after yield
10. Cleanup code runs (session.close())
11. Response sent to client
```

---

## 🔐 OAuth2PasswordBearer Setup

```python
from fastapi.security import OAuth2PasswordBearer

# OAuth2 scheme for JWT authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
```

### What is OAuth2PasswordBearer?

**It's a FastAPI security dependency that:**

1. Extracts token from `Authorization` header
2. Validates header format
3. Returns the token string
4. Shows login form in Swagger UI

**How it works:**

```python
# Client request:
GET /api/v1/users/me
Headers: {
    Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# OAuth2PasswordBearer:
1. Checks Authorization header exists
2. Verifies format: "Bearer <token>"
3. Extracts: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
4. Returns token string
```

**If header is missing or invalid:**

```python
# Missing header:
Response: 401 Unauthorized
{
    "detail": "Not authenticated"
}

# Wrong format (no "Bearer" prefix):
Response: 401 Unauthorized
{
    "detail": "Not authenticated"
}
```

### tokenUrl Parameter

```python
tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
#         ↑
# Tells Swagger UI where the login endpoint is
```

**Why this matters:**

When you open Swagger UI at `http://localhost:8000/docs`:

1. You see a "Authorize" button
2. Click it → Shows login form
3. Form knows to POST to `/api/v1/auth/login` (from tokenUrl)
4. After login → Token stored for all requests

**Without tokenUrl:**

- Swagger UI won't show login button
- Manual token entry required
- Poor developer experience

---

## 🛠️ Service Dependencies

### Dependency 1: `get_user_service()`

```python
async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """
    Dependency to get user service instance.

    Args:
        db: Database session

    Returns:
        UserService instance
    """
    return UserService(db)
```

**Step-by-step breakdown:**

**1. Receives database session**

```python
db: AsyncSession = Depends(get_db)
#                   ↑
# FastAPI calls get_db() first
# Injects session into this parameter
```

**2. Creates service instance**

```python
return UserService(db)
# Passes database session to service
```

**3. Returns service to endpoint**

```python
@router.post("/register")
async def register(user_service: UserService = Depends(get_user_service)):
    #                                           ↑
    #                   FastAPI calls get_user_service()
    #                   Injects returned UserService instance
    return await user_service.create_user(...)
```

**Dependency chain:**

```
Endpoint needs UserService
    ↓
FastAPI calls get_user_service()
    ↓
get_user_service needs AsyncSession
    ↓
FastAPI calls get_db()
    ↓
get_db() yields session
    ↓
get_user_service(session) creates UserService(session)
    ↓
Endpoint receives UserService instance
```

### Type Alias: `UserServiceDep`

```python
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
```

**Why use this?**

**Before (verbose):**

```python
@router.post("/register")
async def register(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service)  # ← Long!
):
    return await user_service.create_user(user_in)
```

**After (clean):**

```python
@router.post("/register")
async def register(
    user_in: UserCreate,
    user_service: UserServiceDep  # ← Short and clear!
):
    return await user_service.create_user(user_in)
```

**What is `Annotated`?**

Python type hint that adds metadata:

```python
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
#                ↑         ↑           ↑
#            Wrapper   Type hint   FastAPI dependency
```

Equivalent to:

```python
user_service: UserService = Depends(get_user_service)
```

But more reusable!

---

## 🔒 Authentication Dependencies

### Dependency 2: `get_current_user()`

```python
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        token: JWT access token
        user_service: User service instance

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception

    try:
        user = await user_service.get_user(int(token_data.sub))
    except HTTPException:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user
```

**Complete step-by-step breakdown:**

**Step 1: Prepare error response**

```python
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
```

**Why define this first?**

- Reused in multiple error cases
- Consistent error response
- Clean code (DRY principle)

**Why include `WWW-Authenticate` header?**

OAuth2 spec requirement:

```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer
```

Tells client:

- Authentication required
- Use Bearer token scheme
- Swagger UI knows how to handle this

**Step 2: Decode JWT token**

```python
try:
    payload = jwt.decode(
        token,  # ← From oauth2_scheme (Authorization header)
        settings.SECRET_KEY,  # ← Verify signature
        algorithms=[settings.ALGORITHM],  # ← Must match signing algorithm
    )
```

**What happens inside `jwt.decode()`:**

```
1. Split token: header.payload.signature
2. Verify signature using SECRET_KEY
   → If tampered, raises JWTError
3. Check expiration time
   → If expired, raises ExpiredSignatureError (subclass of JWTError)
4. Return payload as dict
   → {"sub": "42", "exp": 1234567890}
```

**Step 3: Extract user ID**

```python
user_id: str = payload.get("sub")
if user_id is None:
    raise credentials_exception
```

**Why check if None?**

Token might be malformed:

```python
# Valid token:
{"sub": "42", "exp": 1234567890}
payload.get("sub") → "42" ✓

# Invalid token (missing sub):
{"exp": 1234567890}
payload.get("sub") → None ✗

# Malicious token (wrong field):
{"user": "42", "exp": 1234567890}
payload.get("sub") → None ✗
```

**Step 4: Create TokenPayload**

```python
token_data = TokenPayload(sub=user_id)
```

**What is TokenPayload?**

Pydantic model for validation:

```python
class TokenPayload(BaseModel):
    sub: str | None = None
    exp: int | None = None
```

**Why use it?**

- Type validation
- Could add more fields later
- Consistent with other schemas

**Step 5: Handle JWT errors**

```python
except JWTError:
    raise credentials_exception
```

**What JWTError catches:**

- Token expired (`ExpiredSignatureError`)
- Invalid signature (tampered token)
- Malformed token (not proper JWT format)
- Wrong algorithm

**Step 6: Get user from database**

```python
try:
    user = await user_service.get_user(int(token_data.sub))
```

**Why int()?**

JWT stores user ID as string:

```python
token_payload = {"sub": "42"}  # ← String
user_id = int("42")  # → 42 (integer)
```

**Step 7: Handle user not found**

```python
except HTTPException:
    raise credentials_exception
```

**Why catch HTTPException?**

`user_service.get_user()` raises 404 if user not found:

```python
# Inside UserService.get_user():
if not user:
    raise HTTPException(404, "User not found")
```

**We catch and re-raise as 401:**

```python
# Don't reveal:
404 "User not found"  # ← Reveals user was deleted

# Instead return:
401 "Could not validate credentials"  # ← Generic, secure
```

**Security benefit:**

- Attacker can't tell if user exists
- Same error for "token invalid" and "user deleted"

**Step 8: Check user is active**

```python
if not user.is_active:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Inactive user",
    )
```

**Why separate check?**

Different error codes:

```python
# Token invalid: 401 Unauthorized
# → Authentication failed

# User inactive: 400 Bad Request
# → Authentication succeeded but user can't access
```

**Step 9: Return user**

```python
return user
```

User is now available in endpoint!

### Using get_current_user in Endpoints

```python
@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    #                                   ↑
    #           FastAPI calls get_current_user()
    #           Returns authenticated User instance
    return current_user
```

**Complete flow:**

```
1. Client sends request with token:
   GET /users/me
   Authorization: Bearer eyJ...

2. FastAPI calls oauth2_scheme
   → Extracts "eyJ..." from header

3. FastAPI calls get_user_service
   → Creates UserService instance

4. FastAPI calls get_current_user(token="eyJ...", user_service=...)
   a. Decode token → {"sub": "42"}
   b. Get user from database → User(id=42, ...)
   c. Check is_active → True
   d. Return user

5. FastAPI injects user into endpoint
   → current_user = User(id=42, ...)

6. Endpoint executes with authenticated user
```

---

## 🛡️ Authorization Dependencies

### Dependency 3: `get_current_active_user()`

```python
async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user
```

**Wait, doesn't `get_current_user` already check is_active?**

Yes! So this is **redundant** in your current code.

**Two options:**

**Option 1: Remove the check from `get_current_user`**

```python
# In get_current_user - remove this:
if not user.is_active:
    raise HTTPException(400, "Inactive user")

# Keep only in get_current_active_user
```

**Option 2: Use different dependencies for different needs**

```python
# For endpoints that allow inactive users:
@router.get("/verify-email")
async def verify(user: User = Depends(get_current_user)):
    # Even inactive users can verify email
    pass

# For endpoints that require active users:
@router.get("/todos")
async def list_todos(user: CurrentUser):  # Uses get_current_active_user
    # Only active users can access
    pass
```

**Recommendation:** Use Option 2 for flexibility.

### Dependency 4: `get_current_superuser()`

```python
async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        Current superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user
```

**Step-by-step:**

**Step 1: Get authenticated user**

```python
current_user: Annotated[User, Depends(get_current_user)]
#                                ↑
#           This runs first - authenticates user
```

**Step 2: Check superuser status**

```python
if not current_user.is_superuser:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,  # ← 403, not 401!
        detail="Not enough permissions",
    )
```

**Why 403 instead of 401?**

```python
# 401 Unauthorized - Authentication failed
# → "Who are you?" (identity unknown)

# 403 Forbidden - Authentication succeeded but not authorized
# → "I know who you are, but you can't do this" (insufficient permissions)
```

**Example:**

```python
# Regular user tries to access admin endpoint:
# 1. Token valid → Authentication succeeds ✓
# 2. Not superuser → Authorization fails ✗
# 3. Return 403 (not 401)
```

**Step 3: Return user if superuser**

```python
return current_user
```

### Using Authorization Dependencies

```python
# Anyone can register (no auth)
@router.post("/register")
async def register(user_in: UserCreate, service: UserServiceDep):
    return await service.create_user(user_in)

# Must be authenticated
@router.get("/me")
async def get_me(current_user: CurrentUser):
    return current_user

# Must be authenticated AND active
@router.get("/todos")
async def list_todos(current_active_user: get_current_active_user):
    return await todo_service.get_by_owner(current_active_user.id)

# Must be superuser
@router.get("/users")
async def list_all_users(current_user: User = Depends(get_current_superuser)):
    return await user_service.get_users()
```

---

## 🔗 How Everything Connects

### Complete Dependency Chain

```
Protected Endpoint
    ↓ needs
Current User
    ↓ needs (get_current_user)
JWT Token + UserService
    ↓ needs            ↓ needs (get_user_service)
oauth2_scheme     Database Session
    ↓ extracts          ↓ needs (get_db)
Authorization      AsyncSession
Header                 ↓ creates
                   Session instance
```

**Visual flow:**

```python
@router.get("/todos")
async def list_todos(
    current_user: CurrentUser,  # ← Needs authenticated user
    todo_service: TodoServiceDep  # ← Needs TodoService
):
    # FastAPI dependency resolution:

    # For current_user:
    1. Call get_current_active_user()
       ├─ Depends on get_current_user()
       │  ├─ Depends on oauth2_scheme (extracts token)
       │  └─ Depends on get_user_service()
       │     └─ Depends on get_db() (creates session)
       └─ Checks is_active

    # For todo_service:
    2. Call get_todo_service()
       └─ Depends on get_db() (reuses same session!)

    # Execute endpoint
    return await todo_service.get_by_owner(current_user.id)
```

### Session Reuse

**Important:** FastAPI reuses dependencies within same request!

```python
# Single request dependency resolution:
1. get_db() called → Creates session A
2. get_user_service(session A) → UserService(session A)
3. get_todo_service(session A) → TodoService(session A)
   ↑ Reuses same session!

# Not:
1. get_db() → session A for user_service
2. get_db() → session B for todo_service  # ✗ Doesn't happen
```

**Benefits:**

- Single transaction per request
- Consistent data view
- Better performance (fewer connections)

---

## 🔄 Complete Flow Examples

### Example 1: User Registration (No Auth)

```python
@router.post("/register")
async def register(
    user_in: UserCreate,
    user_service: UserServiceDep
):
    return await user_service.create_user(user_in)
```

**Flow:**

```
1. Client: POST /auth/register
   Body: {"email": "...", "username": "...", "password": "..."}

2. FastAPI validates UserCreate schema

3. FastAPI resolves dependencies:
   a. Call get_db()
      → Create database session

   b. Call get_user_service(db_session)
      → Create UserService(db_session)

   c. Inject into endpoint
      → user_service = UserService(...)

4. Execute endpoint:
   → await user_service.create_user(user_in)
   → Service validates and creates user
   → Returns User object

5. FastAPI cleanup:
   → Close database session (get_db cleanup)

6. Return response to client
```

---

### Example 2: Protected Endpoint (Auth Required)

```python
@router.get("/me")
async def get_profile(current_user: CurrentUser):
    return current_user
```

**Flow:**

```
1. Client: GET /users/me
   Headers: {Authorization: "Bearer eyJ..."}

2. FastAPI resolves dependencies:
   a. Call oauth2_scheme
      → Extract token from header
      → Return "eyJ..."

   b. Call get_db()
      → Create database session

   c. Call get_user_service(db_session)
      → Create UserService(db_session)

   d. Call get_current_user(token, user_service)
      i. Decode token → {"sub": "42"}
      ii. Get user from DB → User(id=42, ...)
      iii. Verify is_active → True
      iv. Return user

   e. Call get_current_active_user(user)
      → Verify is_active (redundant check)
      → Return user

   f. Inject into endpoint
      → current_user = User(id=42, ...)

3. Execute endpoint:
   → return current_user

4. FastAPI serializes User to JSON
   → Filters by response_model

5. FastAPI cleanup:
   → Close database session

6. Return response to client
```

---

### Example 3: Admin Endpoint (Superuser Only)

```python
@router.get("/users")
async def list_all_users(
    current_user: User = Depends(get_current_superuser),
    user_service: UserServiceDep
):
    return await user_service.get_users()
```

**Flow:**

```
1. Client: GET /admin/users
   Headers: {Authorization: "Bearer eyJ..."}

2. FastAPI resolves dependencies:
   a. Extract token (oauth2_scheme)

   b. Create database session (get_db)

   c. Create UserService (get_user_service)

   d. Authenticate user (get_current_user)
      → Returns User(id=42, is_superuser=False)

   e. Check superuser (get_current_superuser)
      → User.is_superuser = False
      → Raise 403 Forbidden ✗

   f. Request rejected before endpoint executes!

3. Return 403 error to client
   {
     "detail": "Not enough permissions"
   }
```

---

### Example 4: Multiple Services

```python
@router.post("/todos")
async def create_todo(
    todo_in: TodoCreate,
    current_user: CurrentUser,
    todo_service: TodoServiceDep,
    user_service: UserServiceDep  # Multiple services!
):
    # Both services share same database session
    user = await user_service.get_user(current_user.id)
    todo = await todo_service.create(todo_in, owner_id=user.id)
    return todo
```

**Dependency graph:**

```
create_todo endpoint
    ├─ current_user (CurrentUser)
    │  └─ get_current_active_user
    │     └─ get_current_user
    │        ├─ oauth2_scheme (token)
    │        └─ get_user_service
    │           └─ get_db → Session A ←┐
    │                                  │
    ├─ todo_service (TodoServiceDep)   │
    │  └─ get_todo_service             │
    │     └─ get_db → Session A ───────┤ SAME SESSION!
    │                                  │
    └─ user_service (UserServiceDep)   │
       └─ get_user_service             │
          └─ get_db → Session A ───────┘
```

**All three use the same database session!**

---

## 💡 Key Concepts Summary

### Dependency Hierarchy

```
Level 1: Basic Infrastructure
├─ get_db() → Database session
└─ oauth2_scheme → Extract token

Level 2: Services
└─ get_user_service(db) → UserService

Level 3: Authentication
└─ get_current_user(token, service) → User

Level 4: Authorization
├─ get_current_active_user(user) → Active User
└─ get_current_superuser(user) → Superuser
```

### Type Aliases

```python
# Instead of:
user_service: UserService = Depends(get_user_service)

# Use:
user_service: UserServiceDep

# Benefits:
✅ Shorter, cleaner code
✅ Consistent across codebase
✅ Easy to change dependency logic (change in one place)
```

### Error Handling Strategy

```python
# 401 Unauthorized - Authentication failed
├─ Missing token
├─ Invalid token
├─ Expired token
└─ User not found (security - don't reveal)

# 403 Forbidden - Not authorized (but authenticated)
├─ User is inactive
└─ User is not superuser

# 400 Bad Request - Invalid data
└─ User data validation failed
```

---

## 🎯 Best Practices

### ✅ DO:

- Use type aliases for common dependencies (`CurrentUser`, `UserServiceDep`)
- Reuse dependencies (FastAPI caches them per request)
- Use specific error codes (401 vs 403)
- Keep dependencies simple and focused
- Use dependency chaining (compose complex from simple)

### ❌ DON'T:

- Create database sessions manually in endpoints
- Duplicate authentication logic
- Forget to close resources (use yield)
- Reveal sensitive information in errors
- Mix authentication and business logic

---

This dependency system provides a clean, testable foundation for your entire API!
