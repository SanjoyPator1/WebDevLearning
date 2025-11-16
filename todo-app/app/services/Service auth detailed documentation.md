# Service Layer & Auth Endpoints - Detailed Documentation

## 📚 Table of Contents

1. [Service Layer Overview](#service-layer-overview)
2. [UserService Implementation](#userservice-implementation)
3. [Auth Endpoints](#auth-endpoints)
4. [Code Fixes Needed](#code-fixes-needed)
5. [Complete Flow Examples](#complete-flow-examples)

---

## 🏗️ Service Layer Overview

### What is the Service Layer?

The service layer sits between API endpoints and repositories:

```
┌─────────────────────────────────────────┐
│     API Endpoints (auth.py)             │
│  - Handle HTTP requests/responses       │
│  - Validate input (Pydantic)            │
│  - Return status codes                  │
└─────────────┬───────────────────────────┘
              │ Uses
              ▼
┌─────────────────────────────────────────┐
│  Service Layer (user_service.py)  ← YOU │
│  - Business logic                       │
│  - Validation rules                     │
│  - Orchestrate operations               │
│  - Handle errors                        │
└─────────────┬───────────────────────────┘
              │ Uses
              ▼
┌─────────────────────────────────────────┐
│  Repository Layer (user_repository.py)  │
│  - Database queries only                │
│  - CRUD operations                      │
└─────────────┬───────────────────────────┘
              │ Queries
              ▼
┌─────────────────────────────────────────┐
│         PostgreSQL Database             │
└─────────────────────────────────────────┘
```

### Why Do We Need a Service Layer?

**Without Service Layer (Bad):**

```python
@router.post("/register")
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check email exists
    repo = UserRepository(db)
    if await repo.exists_by_email(user_in.email):
        raise HTTPException(400, "Email exists")

    # Check username exists
    if await repo.exists_by_username(user_in.username):
        raise HTTPException(400, "Username exists")

    # Hash password
    hashed = get_password_hash(user_in.password)

    # Create user
    user = User(email=..., hashed_password=hashed)
    db.add(user)
    await db.commit()

    return user
```

**Problems:**

- 🔴 Business logic in endpoint (hard to test)
- 🔴 Code duplication across endpoints
- 🔴 Hard to maintain
- 🔴 Violates Single Responsibility Principle

**With Service Layer (Good):**

```python
@router.post("/register")
async def register(user_in: UserCreate, user_service: UserServiceDep):
    return await user_service.create_user(user_in)
```

**Benefits:**

- ✅ Clean endpoint (just HTTP handling)
- ✅ Reusable business logic
- ✅ Easy to test
- ✅ Single Responsibility

---

## 👤 UserService Implementation

### Class Structure

```python
class UserService:
    """Service layer for user-related business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize user service with database session."""
        self.repository = UserRepository(db)
```

**What's happening:**

- Service receives database session
- Creates UserRepository instance
- Stores repository for use in all methods

**Why store repository as instance variable?**

```python
# Instead of creating repo in every method:
async def get_user(self, user_id: int):
    repo = UserRepository(self.db)  # ❌ Repetitive
    return await repo.get(user_id)

# We create it once in __init__:
def __init__(self, db: AsyncSession):
    self.repository = UserRepository(db)  # ✅ Create once

async def get_user(self, user_id: int):
    return await self.repository.get(user_id)  # ✅ Reuse
```

---

### Method 1: `get_user()` - Get User by ID

```python
async def get_user(self, user_id: int) -> User:
    """
    Get user by ID.

    Args:
        user_id: User ID

    Returns:
        User instance

    Raises:
        HTTPException: If user not found
    """
    user = await self.repository.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
```

**Why raise HTTPException here?**

**Option 1: Raise in Service (Current - Better for this case)**

```python
# Service
async def get_user(self, user_id: int) -> User:
    user = await self.repository.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")  # ← Handle here
    return user

# Endpoint - Clean and simple
@router.get("/users/{user_id}")
async def get_user_endpoint(user_id: int, service: UserServiceDep):
    return await service.get_user(user_id)  # Just one line!
```

**Option 2: Return None, Handle in Endpoint (More flexible)**

```python
# Service
async def get_user(self, user_id: int) -> User | None:
    return await self.repository.get(user_id)  # ← Just return

# Endpoint - Must handle None
@router.get("/users/{user_id}")
async def get_user_endpoint(user_id: int, service: UserServiceDep):
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")  # ← Handle here
    return user
```

**Your approach (Option 1) is fine** because:

- User not found is always an error (not a valid case)
- Keeps endpoints clean
- Consistent error handling across all endpoints

---

### Method 2: `authenticate()` - Verify User Credentials

```python
async def authenticate(self, username: str, password: str) -> User | None:
    """
    Authenticate user with username and password.

    Args:
        username: Username or email
        password: Plain text password

    Returns:
        User instance if authentication successful, None otherwise
    """
    user = await self.repository.get_by_email_or_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user
```

**Step-by-step breakdown:**

**Step 1: Find user by email or username**

```python
user = await self.repository.get_by_email_or_username(username)
# Allows login with either:
# - "john@example.com" (email)
# - "john" (username)
```

**Step 2: Check if user exists**

```python
if not user:
    return None  # ← Don't reveal if user exists (security)
```

**Why return None instead of raising exception?**

**Security: Prevent user enumeration attacks**

❌ **Bad - Reveals information:**

```python
if not user:
    raise HTTPException(404, "User not found")
# Attacker knows: "This email/username doesn't exist"

if not verify_password(password, user.hashed_password):
    raise HTTPException(401, "Wrong password")
# Attacker knows: "This email exists, but password is wrong"
```

✅ **Good - Same response for both:**

```python
if not user:
    return None
if not verify_password(password, user.hashed_password):
    return None
# Attacker only knows: "Login failed" (can't tell why)
```

**Step 3: Verify password**

```python
if not verify_password(password, user.hashed_password):
    return None
```

Uses bcrypt to compare:

```
User input: "mypassword"
    ↓
Hash with same salt from stored hash
    ↓
Compare hashes
    ↓
Match? → return user
No match? → return None
```

**Step 4: Check if user is active**

```python
if not user.is_active:
    return None  # Deactivated/banned users can't login
```

**Why check is_active?**

- Admin can deactivate users without deleting them
- User can deactivate their own account
- Maintains data integrity (keep user's todos, etc.)

**Step 5: Return user if all checks pass**

```python
return user  # All checks passed - valid login!
```

---

### Method 3: `create_user()` - Register New User

```python
async def create_user(self, user_in: UserCreate) -> User:
    """
    Create a new user.

    Args:
        user_in: User creation data

    Returns:
        Created user instance

    Raises:
        HTTPException: If email or username already exists
    """
    # Check if email exists
    if await self.repository.exists_by_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username exists
    if await self.repository.exists_by_username(user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create user with hashed password
    user_data = user_in.model_dump(exclude={"password"})
    user_data["hashed_password"] = get_password_hash(user_in.password)

    return await self.repository.create(user_data)
```

**Step-by-step breakdown:**

**Step 1: Validate email uniqueness**

```python
if await self.repository.exists_by_email(user_in.email):
    raise HTTPException(400, "Email already registered")
```

**Why check before creating?**

Prevents database error and provides better user feedback:

```python
# Without check:
try:
    db.add(user)
    await db.commit()
except IntegrityError:  # Database raises error
    raise HTTPException(400, "Email already exists")
# Result: Database error, slower, generic message

# With check:
if await repo.exists_by_email(email):  # Check first
    raise HTTPException(400, "Email already registered")
# Result: Fast, specific error message
```

**Step 2: Validate username uniqueness**

```python
if await self.repository.exists_by_username(user_in.username):
    raise HTTPException(400, "Username already taken")
```

Same reason as email check.

**Step 3: Prepare user data**

```python
user_data = user_in.model_dump(exclude={"password"})
#           ↑                  ↑
#   Convert Pydantic to dict   Don't include plain password
```

**What is `model_dump()`?**

Pydantic method that converts model to dictionary:

```python
user_in = UserCreate(
    email="john@example.com",
    username="john",
    password="secret123",
    full_name="John Doe"
)

# Without exclude
user_in.model_dump()
# {
#     "email": "john@example.com",
#     "username": "john",
#     "password": "secret123",  ← Plain password! Dangerous!
#     "full_name": "John Doe"
# }

# With exclude
user_in.model_dump(exclude={"password"})
# {
#     "email": "john@example.com",
#     "username": "john",
#     "full_name": "John Doe"
# }  ← No password field
```

**Step 4: Hash the password**

```python
user_data["hashed_password"] = get_password_hash(user_in.password)
```

Now user_data looks like:

```python
{
    "email": "john@example.com",
    "username": "john",
    "full_name": "John Doe",
    "hashed_password": "$2b$12$KIX..."  ← Hashed, safe to store
}
```

**Step 5: Create user in database**

```python
return await self.repository.create(user_data)
```

---

### Method 4: `update_user()` - Update User Information

```python
async def update_user(self, user_id: int, user_in: UserUpdate) -> User:
    """
    Update user information.

    Args:
        user_id: User ID
        user_in: User update data

    Returns:
        Updated user instance

    Raises:
        HTTPException: If user not found or validation fails
    """
    user = await self.get_user(user_id)

    # Check if email is being changed and already exists
    if user_in.email and user_in.email != user.email:
        if await self.repository.exists_by_email(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Check if username is being changed and already exists
    if user_in.username and user_in.username != user.username:
        if await self.repository.exists_by_username(user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    # Prepare update data
    update_data = user_in.model_dump(exclude_unset=True, exclude={"password"})

    # Hash password if provided
    if user_in.password:
        update_data["hashed_password"] = get_password_hash(user_in.password)

    return await self.repository.update(user, update_data)
```

**Step-by-step breakdown:**

**Step 1: Get existing user**

```python
user = await self.get_user(user_id)
# If user doesn't exist, get_user() raises 404
# No need to check again
```

**Step 2: Validate email change (if provided)**

```python
if user_in.email and user_in.email != user.email:
    #  ↑                ↑
    # Email provided   Email is different from current

    if await self.repository.exists_by_email(user_in.email):
        raise HTTPException(400, "Email already registered")
```

**Why check `user_in.email != user.email`?**

```python
# Scenario: User updates their profile but keeps same email
current_user.email = "john@example.com"
update_data = {"email": "john@example.com", "full_name": "New Name"}

# Without the check:
if user_in.email:
    if await repo.exists_by_email(user_in.email):  # ← Returns True!
        raise HTTPException(400, "Email exists")  # ← Error! Own email!

# With the check:
if user_in.email and user_in.email != user.email:
    # Only check if email is actually changing
    if await repo.exists_by_email(user_in.email):
        raise HTTPException(400, "Email exists")
```

**Step 3: Validate username change (same logic as email)**

```python
if user_in.username and user_in.username != user.username:
    if await self.repository.exists_by_username(user_in.username):
        raise HTTPException(400, "Username already taken")
```

**Step 4: Prepare update data**

```python
update_data = user_in.model_dump(exclude_unset=True, exclude={"password"})
#                                 ↑
#                      Only include fields that were actually set
```

**What is `exclude_unset=True`?**

```python
# User only wants to update full_name
user_in = UserUpdate(full_name="New Name")
# username, email, password = None (not provided)

# Without exclude_unset
user_in.model_dump()
# {
#     "full_name": "New Name",
#     "username": None,  ← Would clear username!
#     "email": None,     ← Would clear email!
#     "password": None
# }

# With exclude_unset=True
user_in.model_dump(exclude_unset=True)
# {
#     "full_name": "New Name"
# }  ← Only includes what was set
```

**Step 5: Hash password if provided**

```python
if user_in.password:
    update_data["hashed_password"] = get_password_hash(user_in.password)
```

If user is changing password:

- Remove plain `password` from update_data (already excluded)
- Add `hashed_password` instead

**Step 6: Update in database**

```python
return await self.repository.update(user, update_data)
```

---

## 🔐 Auth Endpoints

### Endpoint 1: `/register` - User Registration

```python
@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    user_service: UserServiceDep,
) -> User:
    """
    Register a new user.

    Args:
        user_in: User registration data
        user_service: User service instance

    Returns:
        Created user

    Raises:
        HTTPException: If email or username already exists
    """
    return await user_service.create_user(user_in)
```

**Breakdown:**

**Response model:**

```python
response_model=User
# ↑ Pydantic model for response
# Automatically filters out sensitive fields
```

**What gets returned:**

```python
# UserCreate has:
class UserCreate(BaseModel):
    email: str
    username: str
    password: str  # ← Sensitive!

# User (response model) has:
class User(BaseModel):
    id: int
    email: str
    username: str
    # No password field! ← Automatically filtered
```

**Status code:**

```python
status_code=status.HTTP_201_CREATED
# 201 = Resource created (not just 200 OK)
```

**Dependency injection:**

```python
user_service: UserServiceDep
# FastAPI automatically:
# 1. Gets database session
# 2. Creates UserService(db)
# 3. Injects into function
```

**Flow:**

```
1. FastAPI validates request body against UserCreate schema
2. Creates UserService instance
3. Calls user_service.create_user(user_in)
4. Service validates and creates user
5. Returns User (without password)
6. FastAPI serializes to JSON
```

---

### Endpoint 2: `/login` - User Authentication

```python
@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserServiceDep,
) -> Token:
    """
    Login with username/email and password.

    Args:
        form_data: OAuth2 form with username and password
        user_service: User service instance

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    user = await user_service.authenticate(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
```

**Understanding OAuth2PasswordRequestForm:**

```python
form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
```

**What is OAuth2PasswordRequestForm?**

FastAPI's built-in form for username/password:

```python
# Accepts form data:
POST /login
Content-Type: application/x-www-form-urlencoded

username=john&password=secret123
```

**Fields:**

- `username` - Can be username or email (flexible)
- `password` - Plain text password

**Why use this instead of Pydantic?**

OAuth2 spec requires form data (not JSON):

```python
# OAuth2 standard (form data)
Content-Type: application/x-www-form-urlencoded
username=john&password=secret

# Would prefer (JSON) but not OAuth2 standard
Content-Type: application/json
{"username": "john", "password": "secret"}
```

**Authentication flow:**

**Step 1: Authenticate user**

```python
user = await user_service.authenticate(form_data.username, form_data.password)
```

Calls service method that:

- Finds user by username/email
- Verifies password
- Checks if active
- Returns user or None

**Step 2: Handle authentication failure**

```python
if not user:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,  # 401 = Unauthorized
        detail="Incorrect username or password",   # Generic message
        headers={"WWW-Authenticate": "Bearer"},    # OAuth2 requirement
    )
```

**Why generic error message?**

Security - don't reveal which part failed:

```python
# ❌ Bad - reveals information
"User not found"  # Attacker knows username doesn't exist
"Wrong password"  # Attacker knows username exists

# ✅ Good - same for both
"Incorrect username or password"  # Can't tell which failed
```

**Step 3: Create tokens**

```python
access_token = create_access_token(subject=str(user.id))
# ↑ Short-lived (30 min) for API calls

refresh_token = create_refresh_token(subject=str(user.id))
# ↑ Long-lived (7 days) to get new access tokens
```

**Why convert user.id to string?**

JWT payload stores strings:

```python
user.id = 42  # Integer

# In JWT:
{"sub": "42", "exp": 1234567890}
#       ↑ String!

# When decoding:
payload = decode_token(token)
user_id = int(payload["sub"])  # Convert back to int
```

**Step 4: Return tokens**

```python
return Token(
    access_token=access_token,
    refresh_token=refresh_token,
    token_type="bearer",
)
```

Client receives:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### Endpoint 3: `/refresh` - Refresh Access Token

```python
@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    user_service: UserServiceDep,
) -> Token:
    """
    Refresh access token using refresh token.

    Args:
        refresh_request: Refresh token request
        user_service: User service instance

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        payload = decode_token(refresh_request.refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Verify user still exists and is active
        user = await user_service.get_user(int(user_id))
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive",
            )

        # Create new tokens
        access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
```

**Step-by-step breakdown:**

**Step 1: Decode refresh token**

```python
payload = decode_token(refresh_request.refresh_token)
# Verifies signature and expiration
# Raises JWTError if invalid
```

**Step 2: Verify token type**

```python
if payload.get("type") != "refresh":
    raise HTTPException(401, "Invalid token type")
```

**Why check type?**

Prevents using access token as refresh token:

```python
# Access token payload:
{"sub": "42", "exp": 1234567890}  # No "type"

# Refresh token payload:
{"sub": "42", "exp": 1234567890, "type": "refresh"}
#                                 ↑ Required!
```

**Step 3: Extract user ID**

```python
user_id = payload.get("sub")
if not user_id:
    raise HTTPException(401, "Invalid token")
```

**Step 4: Verify user still exists and is active**

```python
user = await user_service.get_user(int(user_id))
# Raises 404 if user deleted

if not user.is_active:
    raise HTTPException(401, "User is inactive")
```

**Why check if user exists?**

Security scenarios:

- User was deleted after token issued
- User was deactivated (banned)
- Admin revoked access

**Step 5: Create new tokens**

```python
access_token = create_access_token(subject=str(user.id))
new_refresh_token = create_refresh_token(subject=str(user.id))
```

**Note:** Creates new refresh token too (token rotation for security)

**Step 6: Error handling**

```python
except Exception as e:
    raise HTTPException(401, "Invalid or expired refresh token")
```

**⚠️ Issue:** Too broad! See "Code Fixes Needed" section.

---

## 🔧 Code Fixes Needed

### Fix 1: Better Error Handling in Refresh Endpoint

**Current code:**

```python
except Exception as e:  # ❌ Too broad
    raise HTTPException(401, "Invalid or expired refresh token")
```

**Better version:**

```python
except jwt.ExpiredSignatureError:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token has expired"
    )
except jwt.JWTError:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token"
    )
except HTTPException:
    raise  # Re-raise our own exceptions
except Exception as e:
    # Log unexpected errors
    print(f"Unexpected error in refresh: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An error occurred"
    )
```

**Why specific exceptions?**

```python
# Different errors need different handling:

jwt.ExpiredSignatureError
# → User needs to login again (expected)

jwt.JWTError
# → Token malformed or tampered (security issue)

HTTPException
# → Our own business logic errors (user not found, inactive)

Exception
# → Unexpected error (bug - should be logged)
```

**Updated imports needed:**

```python
from jose import jwt, JWTError
```

---

## 🔄 Complete Flow Examples

### Example 1: User Registration Flow

```
1. Client sends POST /api/v1/auth/register
   {
     "email": "john@example.com",
     "username": "john",
     "password": "secret123",
     "full_name": "John Doe"
   }

2. FastAPI validates against UserCreate schema
   ✓ Email format valid
   ✓ Username length OK
   ✓ Password length OK

3. Endpoint calls user_service.create_user(user_in)

4. UserService.create_user():
   a. Check email exists
      → await repository.exists_by_email("john@example.com")
      → False, OK to proceed

   b. Check username exists
      → await repository.exists_by_username("john")
      → False, OK to proceed

   c. Hash password
      → get_password_hash("secret123")
      → "$2b$12$KIX..."

   d. Create user
      → repository.create({
          "email": "john@example.com",
          "username": "john",
          "hashed_password": "$2b$12$KIX...",
          "full_name": "John Doe"
        })

   e. Database inserts row
      → Auto-generates: id=1, created_at, updated_at
      → Returns User object

5. Endpoint returns User (filtered by response_model)
   {
     "id": 1,
     "email": "john@example.com",
     "username": "john",
     "full_name": "John Doe",
     "is_active": true,
     "is_superuser": false,
     "created_at": "2024-11-15T10:00:00Z",
     "updated_at": "2024-11-15T10:00:00Z"
   }
   # Note: No password in response!
```

---

### Example 2: Login Flow

```
1. Client sends POST /api/v1/auth/login
   Content-Type: application/x-www-form-urlencoded
   username=john&password=secret123

2. FastAPI parses OAuth2PasswordRequestForm
   form_data.username = "john"
   form_data.password = "secret123"

3. Endpoint calls user_service.authenticate("john", "secret123")

4. UserService.authenticate():
   a. Find user
      → repository.get_by_email_or_username("john")
      → SELECT * FROM users WHERE email='john' OR username='john'
      → Returns User(id=1, username="john", ...)

   b. Verify password
      → verify_password("secret123", "$2b$12$KIX...")
      → bcrypt compares hashes
      → Returns True

   c. Check is_active
      → user.is_active == True
      → OK

   d. Return user

5. Endpoint creates tokens
   access_token = create_access_token("1")
   → "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   → Expires in 30 minutes

   refresh_token = create_refresh_token("1")
   → "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   → Expires in 7 days

6. Returns tokens
   {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "token_type": "bearer"
   }

7. Client stores tokens and uses access_token for API calls
   Authorization: Bearer eyJ...
```

---

### Example 3: Making Authenticated Request

```
1. Client sends GET /api/v1/users/me
   Headers: {
     Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   }

2. FastAPI dependency extracts token
   → get_current_user(token)

3. Decode token
   → decode_token("eyJ...")
   → payload = {"sub": "1", "exp": 1234567890}

4. Get user from database
   → user_service.get_user(1)
   → Returns User(id=1, ...)

5. Inject user into endpoint
   @router.get("/me")
   async def get_me(current_user: User = Depends(get_current_user)):
       return current_user  # ← Already authenticated!

6. Return user data
```

---

### Example 4: Token Refresh Flow

```
1. Access token expires (after 30 minutes)
   → Client makes API call
   → Server returns 401 Unauthorized

2. Client sends POST /api/v1/auth/refresh
   {
     "refresh_token": "eyJ..."
   }

3. Endpoint decodes refresh token
   → payload = {"sub": "1", "exp": ..., "type": "refresh"}

4. Verify token type
   → payload["type"] == "refresh" ✓

5. Get user from database
   → user_service.get_user(1)
   → Verify user still exists and is active

6. Create new tokens
   → New access token (30 min)
   → New refresh token (7 days)

7. Return new tokens
   {
     "access_token": "new_eyJ...",
     "refresh_token": "new_eyJ...",
     "token_type": "bearer"
   }

8. Client replaces old tokens with new ones
   → Continue making API calls
```

---

## 🎯 Key Takeaways

### Service Layer Responsibilities

✅ **DO in Service Layer:**

- Business logic and validation
- Coordinate multiple repositories
- Handle business errors (HTTPException)
- Transform data between layers
- Orchestrate complex operations

❌ **DON'T in Service Layer:**

- Direct database queries (use repositories)
- HTTP request/response handling (use endpoints)
- Data validation (use Pydantic schemas)

### Auth Flow Summary

```
Registration:
Client → Endpoint → Service validates → Repository creates → Database

Login:
Client → Endpoint → Service authenticates → Create tokens → Client

API Call:
Client + Token → Verify token → Get user → Endpoint executes

Refresh:
Client + Refresh token → Verify → Create new tokens → Client
```

### Security Best Practices

✅ **Always:**

- Hash passwords before storing
- Use generic error messages for auth
- Check user is_active status
- Verify token type (access vs refresh)
- Use HTTPS in production

❌ **Never:**

- Store plain passwords
- Reveal why login failed
- Trust tokens without verification
- Include sensitive data in JWT payload

---

This service layer provides the business logic foundation for your authentication system!
