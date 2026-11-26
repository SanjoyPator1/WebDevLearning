# Security Module Documentation (`app/core/security.py`)

## 📚 Overview

The security module provides essential utilities for:

1. **Password Security** - Hashing and verifying passwords
2. **JWT Authentication** - Creating and validating JSON Web Tokens
3. **Token Management** - Access tokens and refresh tokens

---

## 🔐 Password Security

### Why Hash Passwords?

**NEVER store plain-text passwords in your database!**

```python
# ❌ NEVER DO THIS
user.password = "mypassword123"  # Catastrophic if database is breached

# ✅ ALWAYS DO THIS
user.hashed_password = get_password_hash("mypassword123")  # Safe even if leaked
```

**What happens if passwords are leaked?**

- Plain text: Attacker gets immediate access to all accounts
- Hashed: Attacker gets useless strings that can't be reversed

---

### Password Hashing with bcrypt

```python
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**What is this?**

`CryptContext` is a password hashing manager from the `passlib` library.

**Configuration breakdown:**

- `schemes=["bcrypt"]` - Use bcrypt algorithm
- `deprecated="auto"` - Automatically upgrade old hash formats

**Why bcrypt?**

- ✅ **Slow by design** - Makes brute-force attacks expensive
- ✅ **Salted automatically** - Each hash is unique even for same password
- ✅ **Adaptive** - Can increase work factor as computers get faster
- ✅ **Industry standard** - Battle-tested and widely trusted

**How bcrypt works:**

```
Password: "mysecretpass"
    ↓
Salt (random): "x7s9k2m4"
    ↓
Combine + Hash multiple rounds (2^12 iterations)
    ↓
Result: "$2b$12$x7s9k2m4..." (60 characters)
```

**Hash structure:**

```
$2b$12$x7s9k2m4n1p3q5r8t0v2w4$AbCdEfGhIjKlMnOpQrStUvWxYz0123456
 │   │  │                        │
 │   │  │                        └─ Hash (31 chars)
 │   │  └─ Salt (22 chars)
 │   └─ Cost factor (2^12 = 4,096 rounds)
 └─ Algorithm version (2b = bcrypt)
```

---

### Function 1: `get_password_hash()`

```python
def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)
```

**Purpose:** Convert a plain-text password into a secure hash.

**Usage example:**

```python
# When user registers
plain_password = "SecurePass123!"
hashed = get_password_hash(plain_password)
print(hashed)
# Output: $2b$12$eImiTXuWVxfM3dGc.H8o.Ok2F1Lg/h5YSKvpZIqzPo3TJx.lU8VNS

# Store this in database
user.hashed_password = hashed
```

**Important notes:**

- ✅ Same password creates different hashes each time (due to random salt)
- ✅ Safe to hash even weak passwords (but still validate password strength!)
- ✅ One-way function - cannot reverse the hash to get original password

**Example - Same password, different hashes:**

```python
hash1 = get_password_hash("password123")
hash2 = get_password_hash("password123")
print(hash1 == hash2)  # False! Each hash is unique
```

**When to use:**

- User registration
- Password reset
- Admin creating user accounts

---

### Function 2: `verify_password()`

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
```

**Purpose:** Check if a plain-text password matches a stored hash.

**How it works:**

```
User enters: "mypassword"
    ↓
Extract salt from stored hash: "$2b$12$x7s9k2m4..."
    ↓
Hash "mypassword" with same salt and cost factor
    ↓
Compare new hash with stored hash
    ↓
Return True if identical, False otherwise
```

**Usage example:**

```python
# During login
user_input = "SecurePass123!"
stored_hash = user.hashed_password  # From database

if verify_password(user_input, stored_hash):
    print("✅ Login successful!")
else:
    print("❌ Invalid password")
```

**Flow in authentication:**

```python
async def authenticate_user(username: str, password: str):
    # 1. Get user from database
    user = await get_user_by_username(username)
    if not user:
        return None

    # 2. Verify password
    if not verify_password(password, user.hashed_password):
        return None

    # 3. Return user if password is correct
    return user
```

**Important notes:**

- ⏱️ **Constant-time comparison** - Prevents timing attacks
- 🔒 **Never reveals why login failed** - Don't say "wrong password" vs "user not found"
- ✅ **Fast enough for user experience** - ~100-300ms per verification

---

## 🎫 JWT (JSON Web Token) Authentication

### What is a JWT?

A JWT is a compact, URL-safe token used for authentication. It contains three parts:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NSIsImV4cCI6MTYxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
  │                                      │                                        │
  └─ Header (algorithm & type)           └─ Payload (data)                        └─ Signature (verification)
```

**Structure:**

```
HEADER.PAYLOAD.SIGNATURE
```

**Decoded example:**

```json
// Header
{
  "alg": "HS256",  // Algorithm
  "typ": "JWT"     // Type
}

// Payload
{
  "sub": "12345",          // Subject (user ID)
  "exp": 1616239022,       // Expiration timestamp
  "type": "access"         // Token type
}

// Signature (created using SECRET_KEY)
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  SECRET_KEY
)
```

**Why JWT?**

- ✅ **Stateless** - No need to store sessions in database
- ✅ **Self-contained** - Contains all needed info
- ✅ **Tamper-proof** - Signature prevents modification
- ✅ **Scalable** - Works across multiple servers

**JWT vs Sessions:**

```
Traditional Sessions:
Client → Send credentials → Server
Server → Create session in database → Return session ID cookie
Client → Send cookie with each request → Server
Server → Look up session in database → Verify

JWT:
Client → Send credentials → Server
Server → Create signed JWT → Return JWT
Client → Send JWT with each request → Server
Server → Verify signature (no database lookup!) → Verify
```

---

### Function 3: `create_access_token()`

```python
def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Subject (usually user ID) to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

**Purpose:** Create a short-lived token for API authentication.

**Parameters breakdown:**

1. **`subject`** - Usually the user ID

   - Why user ID? Unique identifier for the user
   - Stored as "sub" claim in JWT
   - Used to identify who the token belongs to

2. **`expires_delta`** - Optional custom expiration
   - If provided: Use custom expiration time
   - If None: Use default from settings (30 minutes)

**Step-by-step execution:**

```python
# Example: Create token for user with ID 42
token = create_access_token(subject=42)

# What happens inside:
# 1. Calculate expiration
expire = datetime.utcnow() + timedelta(minutes=30)
# Example: 2024-11-15 10:00:00 + 30 min = 2024-11-15 10:30:00

# 2. Create payload
to_encode = {
    "exp": 1700051400,  # Unix timestamp of expiration
    "sub": "42"         # User ID as string
}

# 3. Encode with secret key
encoded_jwt = jwt.encode(
    to_encode,              # Data to encode
    settings.SECRET_KEY,    # Secret for signing
    algorithm="HS256"       # Algorithm to use
)

# 4. Return token
return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAi..."
```

**Usage example:**

```python
# After successful login
user = await authenticate_user(username, password)
if user:
    # Create access token
    access_token = create_access_token(subject=user.id)

    # Return to client
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
```

**Client usage:**

```python
# Client stores token and sends with each request
headers = {
    "Authorization": f"Bearer {access_token}"
}
response = requests.get("/api/v1/todos", headers=headers)
```

**Why short expiration?**

- 🔒 **Security** - If stolen, only works for 30 minutes
- 🔄 **Use refresh tokens** - For longer sessions without re-login
- ⚡ **Force re-authentication** - Ensures user is still valid

**Custom expiration example:**

```python
# Create token that expires in 1 hour
from datetime import timedelta
token = create_access_token(
    subject=user.id,
    expires_delta=timedelta(hours=1)
)
```

---

### Function 4: `create_refresh_token()`

```python
def create_refresh_token(subject: str | Any) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        subject: Subject (usually user ID) to encode in token

    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

**Purpose:** Create a long-lived token to get new access tokens.

**Why refresh tokens?**

```
Problem: Access tokens expire in 30 minutes
         User has to login again every 30 minutes → Bad UX!

Solution: Refresh tokens last 7 days
         Use refresh token to get new access token → Good UX!
```

**Flow:**

```
1. User logs in
   → Receive access token (30 min) + refresh token (7 days)

2. User makes API calls with access token
   → Works for 30 minutes

3. Access token expires
   → API returns 401 Unauthorized

4. Client sends refresh token to /auth/refresh
   → Server validates refresh token
   → Returns NEW access token (30 min)

5. Repeat steps 2-4 for up to 7 days

6. After 7 days, refresh token expires
   → User must login again
```

**Key differences from access token:**

| Feature    | Access Token      | Refresh Token                       |
| ---------- | ----------------- | ----------------------------------- |
| Expiration | 30 minutes        | 7 days                              |
| Use        | Every API call    | Only to get new access token        |
| Claims     | `{"exp", "sub"}`  | `{"exp", "sub", "type": "refresh"}` |
| Frequency  | Many times/minute | Once per 30 minutes                 |

**The `"type": "refresh"` claim:**

```python
to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
#                                                 ↑
#                                    Identifies this as refresh token
```

**Why add "type"?**

- ✅ Prevents using refresh token as access token
- ✅ Allows different validation logic
- ✅ Can reject refresh tokens in regular endpoints

**Validation example:**

```python
def validate_refresh_token(token: str):
    payload = decode_token(token)

    # Check it's actually a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Not a refresh token")

    return payload
```

**Usage example:**

```python
# During login, create both tokens
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    # Create both tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

**Refresh endpoint:**

```python
@router.post("/refresh")
async def refresh_token(refresh_request: RefreshTokenRequest):
    try:
        # Decode refresh token
        payload = decode_token(refresh_request.refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")

        # Create new access token
        user_id = payload.get("sub")
        new_access_token = create_access_token(subject=user_id)

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Security considerations:**

⚠️ **Refresh tokens should be treated carefully:**

- Store securely (httpOnly cookies preferred over localStorage)
- Can implement token rotation (new refresh token with each use)
- Can track in database for revocation
- Consider storing hashed version in DB

**Advanced: Refresh token rotation:**

```python
@router.post("/refresh")
async def refresh_token(refresh_request: RefreshTokenRequest):
    # Validate old refresh token
    payload = decode_token(refresh_request.refresh_token)
    user_id = payload.get("sub")

    # Create NEW access AND refresh tokens
    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    # Invalidate old refresh token in database
    await revoke_refresh_token(refresh_request.refresh_token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,  # ← New refresh token!
        "token_type": "bearer"
    }
```

---

### Function 5: `decode_token()`

```python
def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

**Purpose:** Verify token signature and extract payload data.

**What it does:**

```python
# Input: Token string
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDA..."

# Output: Decoded payload
payload = decode_token(token)
print(payload)
# {
#     "exp": 1700051400,
#     "sub": "42",
#     "type": "refresh"
# }
```

**Verification steps:**

```
1. Split token into: header.payload.signature

2. Verify signature
   ├─ Recreate signature using SECRET_KEY
   ├─ Compare with token's signature
   └─ If mismatch → raise JWTError (token was tampered!)

3. Check expiration
   ├─ Get "exp" claim from payload
   ├─ Compare with current time
   └─ If expired → raise ExpiredSignatureError

4. Return payload if all checks pass
```

**Usage in authentication:**

```python
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    try:
        # Decode token
        payload = decode_token(token.credentials)

        # Extract user ID
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get user from database
        user = await get_user_by_id(int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate token")
```

**Error handling:**

```python
from jose import jwt

try:
    payload = decode_token(token)
except jwt.ExpiredSignatureError:
    # Token expired
    print("Token has expired - user needs to refresh or login")
except jwt.JWTError:
    # Invalid signature, malformed token, etc.
    print("Token is invalid")
```

**Common errors:**

1. **ExpiredSignatureError** - Token expired

   ```
   Token created: 10:00 AM with 30 min expiry
   Current time: 10:35 AM
   → Error: Token expired at 10:30 AM
   ```

2. **JWTError** - Invalid signature

   ```
   Someone modified the payload:
   Changed: "sub": "42" → "sub": "99"
   → Signature doesn't match → Error
   ```

3. **JWTError** - Wrong SECRET_KEY
   ```
   Token created with SECRET_KEY = "abc123"
   Trying to decode with SECRET_KEY = "xyz789"
   → Signature doesn't match → Error
   ```

**Why specify algorithms?**

```python
jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#                                                   ↑
#                                      Prevents algorithm confusion attacks
```

**Security note:**
Without specifying algorithms, attacker could change token header to use a different algorithm and potentially bypass security.

---

## 🔄 Complete Authentication Flow

### Registration Flow

```python
# 1. User registers
POST /auth/register
{
    "username": "john",
    "email": "john@example.com",
    "password": "SecurePass123!"
}

# 2. Backend processes
async def register(user_in: UserCreate):
    # Hash password
    hashed_password = get_password_hash(user_in.password)

    # Create user in database
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password  # ← Store hash, not plain password
    )
    await db.add(user)
    await db.commit()

    return user
```

---

### Login Flow

```python
# 1. User logs in
POST /auth/login
{
    "username": "john",
    "password": "SecurePass123!"
}

# 2. Backend authenticates
async def login(form_data: OAuth2PasswordRequestForm):
    # Get user from database
    user = await get_user_by_username(form_data.username)
    if not user:
        raise HTTPException(status_code=401)

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401)

    # Create tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

---

### Protected Endpoint Flow

```python
# 1. User makes request to protected endpoint
GET /api/v1/todos
Headers: {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# 2. Backend validates token
async def get_current_user(token: str = Depends(security)):
    # Decode and verify token
    payload = decode_token(token)  # ← Validates signature and expiration

    # Get user ID from token
    user_id = payload.get("sub")

    # Fetch user from database
    user = await get_user_by_id(int(user_id))

    return user

# 3. Endpoint uses authenticated user
@router.get("/todos")
async def list_todos(current_user: User = Depends(get_current_user)):
    # current_user is now available!
    todos = await get_todos_by_owner(current_user.id)
    return todos
```

---

### Token Refresh Flow

```python
# 1. Access token expires after 30 minutes
GET /api/v1/todos
Headers: {"Authorization": "Bearer <expired_access_token>"}
Response: 401 Unauthorized

# 2. Client requests new access token
POST /auth/refresh
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# 3. Backend validates refresh token
async def refresh_token(request: RefreshTokenRequest):
    # Decode refresh token
    payload = decode_token(request.refresh_token)

    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400)

    # Create new access token
    user_id = payload.get("sub")
    new_access_token = create_access_token(subject=user_id)

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

# 4. Client uses new access token
GET /api/v1/todos
Headers: {"Authorization": "Bearer <new_access_token>"}
Response: 200 OK with todos
```

---

## ⚙️ Configuration Settings

These functions use settings from `app/config.py`:

```python
# app/config.py
class Settings(BaseSettings):
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

**Important settings:**

1. **SECRET_KEY**

   - Used to sign JWT tokens
   - MUST be kept secret
   - Should be long and random
   - Different for dev/staging/production

   ```bash
   # Generate a secure key
   openssl rand -hex 32
   # Output: 09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
   ```

2. **ALGORITHM**

   - HS256 (HMAC-SHA256) is standard
   - Could use RS256 for public/private key
   - Must match when encoding and decoding

3. **ACCESS_TOKEN_EXPIRE_MINUTES**

   - Short expiration for security
   - 15-60 minutes typical
   - Balance security vs UX

4. **REFRESH_TOKEN_EXPIRE_DAYS**
   - Longer expiration for convenience
   - 7-30 days typical
   - After this, must login again

---

## 🛡️ Security Best Practices

### 1. Password Security

✅ **DO:**

- Always hash passwords before storing
- Use bcrypt (or argon2, scrypt)
- Set minimum password requirements
- Consider password strength meters

❌ **DON'T:**

- Store plain-text passwords
- Use MD5 or SHA1 for passwords
- Share hashing secrets
- Log passwords anywhere

### 2. JWT Security

✅ **DO:**

- Use strong SECRET_KEY
- Set appropriate expiration times
- Validate tokens on every request
- Use HTTPS in production
- Store refresh tokens securely

❌ **DON'T:**

- Store JWTs in localStorage (XSS risk)
- Make tokens too long-lived
- Include sensitive data in payload
- Use same SECRET_KEY across environments
- Trust token without verification

### 3. Token Storage (Client-side)

**Options:**

1. **httpOnly Cookies** (Most Secure) ⭐

   ```python
   response.set_cookie(
       key="access_token",
       value=token,
       httponly=True,  # ← Can't access via JavaScript
       secure=True,    # ← HTTPS only
       samesite="lax"  # ← CSRF protection
   )
   ```

2. **Memory** (Good for SPAs)

   ```javascript
   // Store in React state or similar
   const [token, setToken] = useState(null);
   ```

3. **localStorage** (Least Secure)
   ```javascript
   // ⚠️ Vulnerable to XSS attacks
   localStorage.setItem("token", accessToken);
   ```

### 4. Common Security Issues

**Issue 1: Token Replay Attacks**

```
Attacker steals valid token → Uses it to access API
Solution: Short expiration + HTTPS + Secure storage
```

**Issue 2: Brute Force Login**

```
Attacker tries many passwords
Solution: Rate limiting + Account lockout + CAPTCHA
```

**Issue 3: Timing Attacks on Password Verification**

```
Attacker measures response time to guess passwords
Solution: Constant-time comparison (bcrypt does this)
```

---

## 📋 Quick Reference

### Password Functions

```python
# Hash password
hashed = get_password_hash("mypassword")

# Verify password
is_valid = verify_password("mypassword", hashed)
```

### Token Functions

```python
# Create access token (30 min)
access = create_access_token(subject=user_id)

# Create refresh token (7 days)
refresh = create_refresh_token(subject=user_id)

# Decode token
payload = decode_token(token)
user_id = payload.get("sub")
```

### Common Patterns

```python
# Registration
hashed_password = get_password_hash(user_in.password)
user = User(..., hashed_password=hashed_password)

# Login
if verify_password(plain_password, user.hashed_password):
    token = create_access_token(subject=user.id)

# Protected endpoint
payload = decode_token(token)
user = await get_user(payload["sub"])
```

---

## 🎯 Summary

The `security.py` module provides five essential functions:

1. **`get_password_hash()`** - Hash passwords for storage
2. **`verify_password()`** - Verify passwords during login
3. **`create_access_token()`** - Create short-lived JWT for API access
4. **`create_refresh_token()`** - Create long-lived JWT for token refresh
5. **`decode_token()`** - Verify and decode JWT tokens

**Key Concepts:**

- 🔐 Never store plain passwords
- 🎫 Use JWT for stateless authentication
- ⏱️ Short access tokens + long refresh tokens
- 🔒 Always verify tokens before trusting them
- 🛡️ Use strong secrets and secure storage

This module is the foundation of your application's security!
