# Day 4: Basic Authentication Methods

**Date**: Week 4, Day 4  
**Phase**: 2 - FastAPI Mastery  
**Topic**: API Keys, Basic Auth, and Bearer Token Authentication

---

## Table of Contents

1. [Authentication Overview](#1-authentication-overview)
2. [API Key Authentication](#2-api-key-authentication)
3. [Basic HTTP Authentication](#3-basic-http-authentication)
4. [Bearer Token Authentication](#4-bearer-token-authentication)
5. [Authentication Methods Comparison](#5-authentication-methods-comparison)
6. [Complete Practical Examples](#6-complete-practical-examples)
7. [Testing Authentication](#7-testing-authentication)
8. [Common Pitfalls](#8-common-pitfalls)
9. [Key Takeaways](#9-key-takeaways)
10. [Practice Exercises](#10-practice-exercises)

---

## 1. Authentication Overview

### 1.1 What is Authentication?

Authentication is the process of verifying the identity of a user, application, or service. It answers the fundamental question: "Who are you?"

In API development, authentication ensures that only legitimate clients can access protected resources. Without authentication, anyone could read, modify, or delete data in your system.

**Core Purpose**: Prove identity before granting access.

**Authentication Process**:

```
Client → Provides Credentials → Server Validates → Server Grants Access Token/Session
```

**Real-world Analogy**: Authentication is like showing your ID at airport security. The ID proves who you are, but it doesn't determine which flights you can board (that's authorization).

### 1.2 Authentication vs Authorization

These terms are often confused but represent distinct concepts:

**Authentication (AuthN)**: Verifying identity

- Question: "Who are you?"
- Process: User provides credentials, system verifies them
- Example: Username + password, API key, biometric scan
- Result: Identity confirmed or rejected

**Authorization (AuthZ)**: Verifying permissions

- Question: "What are you allowed to do?"
- Process: System checks if authenticated user has permission for requested action
- Example: Admin can delete users, regular user cannot
- Result: Permission granted or denied

**Sequential Relationship**:

```
Authentication MUST happen before Authorization

Step 1: Authentication → Prove who you are
Step 2: Authorization → Check what you can do
```

**Example Flow**:

```python
# Authentication
user = verify_credentials(username, password)  # Who is this?

# Authorization
if user.role == "admin":  # What can they do?
    delete_user(target_user_id)
else:
    raise PermissionDenied("Only admins can delete users")
```

**Comparison Table**:

| Aspect    | Authentication           | Authorization                |
| --------- | ------------------------ | ---------------------------- |
| Question  | "Who are you?"           | "What can you do?"           |
| Timing    | First                    | Second                       |
| Mechanism | Credentials verification | Permission checking          |
| Result    | Identity established     | Access granted/denied        |
| Example   | Login with password      | Admin viewing sensitive data |

### 1.3 Authentication Flow Basics

All authentication methods follow a similar high-level flow:

```mermaid
graph TD
    A[Client] -->|1. Request with Credentials| B[Server]
    B -->|2. Validate Credentials| C{Valid?}
    C -->|No| D[Return 401 Unauthorized]
    C -->|Yes| E[Generate Token/Session]
    E -->|3. Return Token| A
    A -->|4. Subsequent Requests with Token| B
    B -->|5. Validate Token| F{Valid?}
    F -->|No| D
    F -->|Yes| G[Process Request]
    G -->|6. Return Response| A

    classDef blue fill:#6B8DBE,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef teal fill:#6FAFA3,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef green fill:#7FAE8A,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef red fill:#C26D63,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef neutral fill:#3A3F4B,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF

    class A,B blue
    class E,G teal
    class C,F neutral
    class D red
```

**Flow Steps Explained**:

1. **Initial Request**: Client sends credentials to authentication endpoint
2. **Validation**: Server verifies credentials against stored data
3. **Token Generation**: If valid, server creates authentication token
4. **Token Return**: Server sends token to client
5. **Authenticated Requests**: Client includes token in subsequent requests
6. **Token Validation**: Server validates token on each request
7. **Response**: If token valid, server processes request and responds

**Key Principles**:

- Credentials should only be sent once (during initial authentication)
- Subsequent requests use tokens, not raw credentials
- Tokens should be revocable
- Validation must happen on every protected request

### 1.4 Authentication Methods Comparison Table

| Method              | Security Level | Complexity  | Use Case                        | Stateful/Stateless |
| ------------------- | -------------- | ----------- | ------------------------------- | ------------------ |
| **API Keys**        | Low-Medium     | Very Simple | Service-to-service, Public APIs | Can be either      |
| **Basic Auth**      | Low            | Simple      | Development, Internal tools     | Stateless          |
| **Bearer Tokens**   | Medium-High    | Medium      | Web/Mobile apps, SPAs           | Can be either      |
| **OAuth2**          | High           | Complex     | Third-party integrations        | Stateless (JWT)    |
| **Session Cookies** | Medium         | Medium      | Traditional web apps            | Stateful           |

**Choosing the Right Method**:

- **API Keys**: Simple machine-to-machine communication
- **Basic Auth**: Quick development, internal services
- **Bearer Tokens**: Modern web/mobile applications
- **OAuth2**: Third-party access, enterprise apps
- **Sessions**: Server-rendered web applications

---

## 2. API Key Authentication

### 2.1 What are API Keys?

API keys are simple string tokens that identify and authenticate API clients. They act as both an identifier (who you are) and a shared secret (proof of identity).

**Structure**: Typically a long random string or UUID

```
Examples:
YOUR_API_KEY_HERE
AIzaSyD-9tSrke96h4KFOP1LH8HHHJKlMnO
7d8a9b0c1e2f3g4h5i6j7k8l9m0n1o2p
```

**Key Characteristics**:

- Long random strings (typically 32-64 characters)
- Generated by the server
- Stored by the client
- Sent with every API request
- No expiration by default (unless implemented)

### 2.2 How API Keys Work

**Generation and Usage Flow**:

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant Database

    Note over Client,Database: Key Generation
    Client->>Server: Request API Key (POST /api-keys)
    Server->>Server: Generate random string
    Server->>Database: Store key hash + metadata
    Database->>Server: Confirmation
    Server->>Client: Return API key

    Note over Client,Database: API Usage
    Client->>Server: GET /protected (X-API-Key: key123)
    Server->>Database: Validate key hash
    Database->>Server: Key valid + permissions
    Server->>Client: 200 OK + Response

    classDef blue fill:#6B8DBE,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef teal fill:#6FAFA3,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef neutral fill:#3A3F4B,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF

    class Client,Server blue
    class Database teal
```

**Step-by-Step Process**:

1. **Registration**: Client registers with API provider
2. **Key Generation**: Server generates unique random key
3. **Storage**: Server stores key hash (not plaintext) in database
4. **Distribution**: Key sent to client via secure channel
5. **Usage**: Client includes key in every request
6. **Validation**: Server checks key against database on each request

### 2.3 When to Use API Keys

**Ideal Use Cases**:

**Service-to-Service Communication**:

```python
# Microservice A calls Microservice B
response = requests.get(
    "https://service-b.internal/data",
    headers={"X-API-Key": os.getenv("SERVICE_B_API_KEY")}
)
```

**Public APIs with Usage Tracking**:

- Track which client makes which requests
- Enforce rate limits per client
- Bill based on usage
- Examples: Google Maps API, Stripe API, SendGrid API

**Simple Authentication Needs**:

- Internal tools
- Automated scripts
- CI/CD pipelines
- Server-to-server integrations

**When NOT to Use API Keys**:

- User-facing applications (use OAuth2/JWT instead)
- Scenarios requiring fine-grained permissions (use tokens with scopes)
- When rotation/expiration is critical (use short-lived tokens)
- Browser-based applications (keys can be exposed in source code)

### 2.4 API Key Generation

#### Random String Generation

**Cryptographically Secure Random Strings**:

```python
import secrets

def generate_api_key(length: int = 32) -> str:
    """
    Generate cryptographically secure API key.

    Args:
        length: Key length in bytes (default 32 = 256 bits)

    Returns:
        Hex-encoded random string
    """
    return secrets.token_hex(length)

# Example output: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
```

**URL-Safe Random Strings**:

```python
def generate_api_key_urlsafe(length: int = 32) -> str:
    """
    Generate URL-safe API key (base64-encoded).
    Safe for use in URLs and headers without encoding.
    """
    return secrets.token_urlsafe(length)

# Example output: 'dGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBkZW1v'
```

#### UUID-Based Keys

```python
import uuid

def generate_uuid_key() -> str:
    """
    Generate UUID-based API key.
    Guaranteed unique, shorter than random hex strings.
    """
    return str(uuid.uuid4())

# Example output: '550e8400-e29b-41d4-a716-446655440000'
```

#### Prefixed Keys (Industry Standard)

```python
def generate_prefixed_key(prefix: str = "sk") -> str:
    """
    Generate API key with identifiable prefix.

    Common prefixes:
    - sk: Secret key
    - pk: Public key
    - test: Test environment
    - live: Production environment
    """
    random_part = secrets.token_hex(32)
    return f"{prefix}_{random_part}"

# Example output: 'sk_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
```

**Why Prefixes Matter**:

- Identifies key type at a glance
- Prevents accidental use of test keys in production
- Enables automated secret scanning (GitHub, GitLab)
- Industry standard (Stripe, AWS, many others)

#### Secure Generation Practices

```python
import secrets
import hashlib
from datetime import datetime

def generate_secure_api_key() -> tuple[str, str]:
    """
    Generate API key with best practices.

    Returns:
        Tuple of (plaintext_key, hashed_key)
        - plaintext_key: Show to user once
        - hashed_key: Store in database
    """
    # Generate key
    plaintext_key = f"sk_live_{secrets.token_hex(32)}"

    # Hash for storage (never store plaintext)
    hashed_key = hashlib.sha256(plaintext_key.encode()).hexdigest()

    return plaintext_key, hashed_key

# Usage
key, key_hash = generate_secure_api_key()
# Show 'key' to user once
# Store 'key_hash' in database
```

**Critical Security Rules**:

1. Use `secrets` module, not `random` (cryptographically secure)
2. Minimum 128 bits of entropy (16 bytes)
3. Store hashed keys in database, not plaintext
4. Show plaintext key to user only once at creation
5. Use prefixes for key type identification

### 2.5 API Key Storage

#### Environment Variables (Client-Side)

```bash
# .env file
API_KEY=YOUR_API_KEY_HERE
```

```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

# Never hardcode keys
# BAD: API_KEY = "sk_live_abc123"
```

#### Database Storage (Server-Side)

```python
import hashlib
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100))  # User-provided key name/description
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Optional: expiration
    expires_at = Column(DateTime, nullable=True)

    # Optional: rate limiting
    rate_limit = Column(Integer, default=1000)  # Requests per hour

def hash_api_key(key: str) -> str:
    """Hash API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()

def create_api_key(db: Session, user_id: str, name: str) -> str:
    """
    Create and store new API key.

    Returns:
        Plaintext key (show to user once)
    """
    import secrets

    # Generate key
    plaintext_key = f"sk_{secrets.token_hex(32)}"
    key_hash = hash_api_key(plaintext_key)

    # Store in database
    api_key = APIKey(
        id=str(uuid.uuid4()),
        key_hash=key_hash,
        name=name,
        user_id=user_id
    )

    db.add(api_key)
    db.commit()

    return plaintext_key  # Return only once, never retrievable

def validate_api_key(db: Session, key: str) -> APIKey | None:
    """
    Validate API key against database.

    Returns:
        APIKey object if valid, None otherwise
    """
    key_hash = hash_api_key(key)

    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()

    if api_key:
        # Update last used timestamp
        api_key.last_used = datetime.utcnow()
        db.commit()

    return api_key
```

**Storage Best Practices**:

1. Hash keys before storage (SHA-256 minimum)
2. Never store plaintext keys
3. Add salt for additional security (optional but recommended)
4. Index the hash column for fast lookups
5. Track usage metadata (last_used, created_at)
6. Allow key revocation (is_active flag)

#### Key Management Services

For production systems, consider dedicated key management:

```python
# AWS Secrets Manager example
import boto3

def store_api_key(key_name: str, key_value: str):
    """Store API key in AWS Secrets Manager."""
    client = boto3.client('secretsmanager')

    client.create_secret(
        Name=key_name,
        SecretString=key_value,
        Description='API key for external service'
    )

def retrieve_api_key(key_name: str) -> str:
    """Retrieve API key from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')

    response = client.get_secret_value(SecretId=key_name)
    return response['SecretString']
```

**When to Use Key Management Services**:

- Production environments
- Compliance requirements (SOC2, ISO 27001)
- Multiple services sharing secrets
- Automatic rotation needed
- Audit logging required

### 2.6 API Key Transmission

#### HTTP Headers (Recommended)

```python
# Client sends request
import requests

response = requests.get(
    "https://api.example.com/data",
    headers={"X-API-Key": "sk_live_abc123xyz"}
)
```

**Common Header Names**:

- `X-API-Key`
- `X-API-TOKEN`
- `Authorization: ApiKey sk_live_abc123`
- `Api-Key`

**Why Headers?**:

- Not logged in server access logs (unlike URLs)
- Not cached by browsers
- Not visible in browser history
- Can be easily stripped by proxies if needed

#### Query Parameters (Less Secure)

```python
# NOT RECOMMENDED for sensitive data
response = requests.get(
    "https://api.example.com/data?api_key=sk_live_abc123xyz"
)
```

**Problems with Query Parameters**:

- Logged in server access logs
- Visible in browser history
- Cached by browsers and proxies
- Exposed in referrer headers
- Visible in URLs shared/bookmarked

**Only Use Query Parameters When**:

- Temporary/disposable keys
- Webhooks with unique tokens
- Public data access (minimal security needed)

#### Custom Headers

```python
# Server-specific custom header
response = requests.get(
    "https://api.example.com/data",
    headers={"X-Company-API-Key": "sk_live_abc123xyz"}
)
```

### 2.7 Implementing API Keys in FastAPI

#### Header-Based API Keys

```python
from fastapi import FastAPI, Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from typing import Annotated

app = FastAPI()

# Define API key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(
    api_key: Annotated[str, Security(api_key_header)],
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Validate API key from header.

    Raises:
        HTTPException: If key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    # Validate against database
    key_record = validate_api_key(db, api_key)

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check expiration
    if key_record.expires_at and key_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    return key_record

@app.get("/protected")
async def protected_endpoint(
    api_key: Annotated[APIKey, Depends(get_api_key)]
):
    """
    Protected endpoint requiring valid API key.
    """
    return {
        "message": "Access granted",
        "user_id": api_key.user_id,
        "key_name": api_key.name
    }
```

#### Query Parameter API Keys

```python
from fastapi.security import APIKeyQuery

api_key_query = APIKeyQuery(name="api_key", auto_error=False)

async def get_api_key_from_query(
    api_key: Annotated[str, Security(api_key_query)],
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Validate API key from query parameter.
    Less secure, use only for specific use cases.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    key_record = validate_api_key(db, api_key)

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return key_record

@app.get("/public-data")
async def public_data_endpoint(
    api_key: Annotated[APIKey, Depends(get_api_key_from_query)]
):
    """
    Endpoint using query parameter authentication.
    Usage: GET /public-data?api_key=sk_live_abc123
    """
    return {"data": "Public information"}
```

#### Custom Security Dependency

```python
from fastapi import Security
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPBearer
from typing import Union

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

async def get_api_key_flexible(
    header_key: Annotated[str | None, Security(api_key_header)],
    query_key: Annotated[str | None, Security(api_key_query)],
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Accept API key from either header or query parameter.
    Prefers header if both provided.
    """
    # Prefer header over query parameter
    api_key = header_key or query_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in header (X-API-Key) or query (?api_key=)"
        )

    key_record = validate_api_key(db, api_key)

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return key_record

@app.get("/flexible")
async def flexible_auth_endpoint(
    api_key: Annotated[APIKey, Depends(get_api_key_flexible)]
):
    """
    Accepts API key from header OR query parameter.
    Usage:
    - GET /flexible -H "X-API-Key: sk_live_abc123"
    - GET /flexible?api_key=sk_live_abc123
    """
    return {"message": "Flexible authentication", "user_id": api_key.user_id}
```

#### API Key Validation

```python
import hashlib
from datetime import datetime

def validate_api_key(db: Session, key: str) -> APIKey | None:
    """
    Comprehensive API key validation.

    Checks:
    - Key exists in database
    - Key is active
    - Key has not expired
    - Updates last_used timestamp

    Returns:
        APIKey object if valid, None otherwise
    """
    # Hash the provided key
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    # Query database
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()

    if not api_key:
        return None

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        return None

    # Update last used timestamp
    api_key.last_used = datetime.utcnow()
    db.commit()

    return api_key

async def rate_limit_check(api_key: APIKey, db: Session) -> bool:
    """
    Check if API key has exceeded rate limit.

    Returns:
        True if within limit, raises HTTPException if exceeded
    """
    from datetime import timedelta

    # Get requests in last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    request_count = db.query(APIRequest).filter(
        APIRequest.api_key_id == api_key.id,
        APIRequest.timestamp >= one_hour_ago
    ).count()

    if request_count >= api_key.rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {api_key.rate_limit} requests/hour"
        )

    # Log this request
    api_request = APIRequest(
        id=str(uuid.uuid4()),
        api_key_id=api_key.id,
        timestamp=datetime.utcnow()
    )
    db.add(api_request)
    db.commit()

    return True
```

### 2.8 API Key Security Best Practices

#### Key Rotation

```python
from datetime import datetime, timedelta

def rotate_api_key(db: Session, old_key_id: str, user_id: str) -> str:
    """
    Rotate API key by creating new key and marking old as inactive.

    Returns:
        New plaintext key (show to user once)
    """
    # Deactivate old key
    old_key = db.query(APIKey).filter(APIKey.id == old_key_id).first()
    if old_key and old_key.user_id == user_id:
        old_key.is_active = False
        db.commit()

    # Create new key
    new_key = create_api_key(db, user_id, name=f"Rotated from {old_key.name}")

    return new_key

def schedule_key_rotation(api_key: APIKey, days: int = 90):
    """
    Set expiration date for automatic rotation reminder.
    """
    api_key.rotation_reminder = datetime.utcnow() + timedelta(days=days)
```

**Rotation Schedule**:

- Production keys: Every 90 days
- Development keys: Every 180 days
- Compromised keys: Immediately

#### Rate Limiting

```python
from fastapi import Request
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}

    async def check_rate_limit(self, api_key_id: str):
        """
        Check if request is within rate limit.
        """
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        if api_key_id in self.requests:
            self.requests[api_key_id] = [
                req_time for req_time in self.requests[api_key_id]
                if req_time > minute_ago
            ]
        else:
            self.requests[api_key_id] = []

        # Check limit
        if len(self.requests[api_key_id]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"}
            )

        # Add this request
        self.requests[api_key_id].append(now)

rate_limiter = RateLimiter(requests_per_minute=100)

@app.get("/limited")
async def rate_limited_endpoint(
    api_key: Annotated[APIKey, Depends(get_api_key)]
):
    await rate_limiter.check_rate_limit(api_key.id)
    return {"message": "Request processed"}
```

#### Key Scoping

```python
from enum import Enum

class APIKeyScope(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

class APIKey(Base):
    __tablename__ = "api_keys"

    # ... other fields ...

    # Scopes as JSON array
    scopes = Column(JSON, default=["read"])

def check_scope(api_key: APIKey, required_scope: APIKeyScope):
    """
    Verify API key has required scope.
    """
    if required_scope.value not in api_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key missing required scope: {required_scope.value}"
        )

@app.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    api_key: Annotated[APIKey, Depends(get_api_key)]
):
    # Check delete permission
    check_scope(api_key, APIKeyScope.DELETE)

    # Proceed with deletion
    return {"message": "Item deleted"}
```

#### Expiration

```python
from datetime import datetime, timedelta

def create_expiring_key(
    db: Session,
    user_id: str,
    days_valid: int = 90
) -> str:
    """
    Create API key with expiration date.
    """
    plaintext_key = f"sk_{secrets.token_hex(32)}"
    key_hash = hash_api_key(plaintext_key)

    api_key = APIKey(
        id=str(uuid.uuid4()),
        key_hash=key_hash,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(days=days_valid)
    )

    db.add(api_key)
    db.commit()

    return plaintext_key

def check_expiration(api_key: APIKey):
    """
    Verify key has not expired.
    """
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
```

### 2.9 API Key Management

#### Key Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: Generate Key
    Created --> Active: First Use
    Active --> Expired: Expiration Date
    Active --> Revoked: Manual Revocation
    Active --> Rotated: Key Rotation
    Expired --> [*]
    Revoked --> [*]
    Rotated --> [*]

    classDef blue fill:#6B8DBE,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef green fill:#7FAE8A,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef amber fill:#C2A25F,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef red fill:#C26D63,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF

    class Created blue
    class Active green
    class Expired,Revoked,Rotated amber
```

**Lifecycle States**:

- **Created**: Key generated but not yet used
- **Active**: Key in regular use
- **Expired**: Passed expiration date
- **Revoked**: Manually deactivated
- **Rotated**: Replaced with new key

#### Key Revocation

```python
@app.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke (deactivate) API key.
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Deactivate key
    api_key.is_active = False
    api_key.revoked_at = datetime.utcnow()
    db.commit()

    return {"message": "API key revoked successfully"}
```

#### Multiple Keys Per User

```python
@app.post("/api-keys")
async def create_user_api_key(
    name: str,
    scopes: list[str] = ["read"],
    expires_days: int = 90,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new API key for current user.
    Users can have multiple active keys.
    """
    # Check user's key limit
    active_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()

    if active_keys >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API keys reached (5)"
        )

    # Generate key
    plaintext_key = f"sk_{secrets.token_hex(32)}"
    key_hash = hash_api_key(plaintext_key)

    # Create record
    api_key = APIKey(
        id=str(uuid.uuid4()),
        key_hash=key_hash,
        name=name,
        user_id=current_user.id,
        scopes=scopes,
        expires_at=datetime.utcnow() + timedelta(days=expires_days)
    )

    db.add(api_key)
    db.commit()

    return {
        "api_key": plaintext_key,
        "key_id": api_key.id,
        "name": name,
        "scopes": scopes,
        "expires_at": api_key.expires_at,
        "warning": "Save this key securely. It cannot be retrieved again."
    }

@app.get("/api-keys")
async def list_user_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all API keys for current user.
    Does NOT return the actual keys, only metadata.
    """
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).all()

    return {
        "keys": [
            {
                "id": key.id,
                "name": key.name,
                "scopes": key.scopes,
                "created_at": key.created_at,
                "last_used": key.last_used,
                "expires_at": key.expires_at,
                "is_active": key.is_active
            }
            for key in keys
        ]
    }
```

---

## 3. Basic HTTP Authentication

### 3.1 What is Basic Authentication?

Basic Authentication is the simplest HTTP authentication scheme defined in RFC 7617. It sends username and password in Base64 encoding with every request.

**Key Characteristics**:

- Credentials sent with every request
- Base64 encoded (NOT encrypted)
- Defined in HTTP specification
- Stateless (no sessions)
- Must use HTTPS in production

**When Introduced**: HTTP/1.0 (1996)
**Current Status**: Still widely used but considered less secure than modern alternatives

### 3.2 How Basic Auth Works

#### Authorization Header Format

```
Authorization: Basic <base64(username:password)>
```

**Example**:

```
Username: alice
Password: secret123

String to encode: alice:secret123
Base64 encoded: YWxpY2U6c2VjcmV0MTIz
Header: Authorization: Basic YWxpY2U6c2VjcmV0MTIz
```

#### Base64 Encoding

**Important**: Base64 is encoding, NOT encryption. Anyone can decode it.

```python
import base64

# Encoding
credentials = "alice:secret123"
encoded = base64.b64encode(credentials.encode()).decode()
print(encoded)  # YWxpY2U6c2VjcmV0MTIz

# Decoding (anyone can do this)
decoded = base64.b64decode(encoded).decode()
print(decoded)  # alice:secret123
```

**Security Implication**: Never use Basic Auth over unencrypted HTTP. Always require HTTPS.

#### Credentials Format

```
username:password
```

**Rules**:

- Username and password separated by colon `:`
- If password contains colon, it's part of the password
- No spaces around colon
- Case-sensitive

**Examples**:

```
Valid: alice:password123
Valid: bob:pass:word:123  (password is "pass:word:123")
Invalid: alice : password (spaces)
Invalid: alice:  (empty password)
```

### 3.3 Basic Auth Flow Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant Database

    Note over Client,Server: Initial Request (No Credentials)
    Client->>Server: GET /protected
    Server->>Client: 401 Unauthorized<br/>WWW-Authenticate: Basic realm="API"

    Note over Client,Server: Authenticated Request
    Client->>Client: Base64 encode credentials
    Client->>Server: GET /protected<br/>Authorization: Basic YWxpY2U6c2VjcmV0MTIz
    Server->>Server: Decode Base64
    Server->>Database: Verify username & password
    Database->>Server: Credentials valid
    Server->>Client: 200 OK + Response

    Note over Client,Server: Subsequent Requests (Credentials Every Time)
    Client->>Server: GET /other-endpoint<br/>Authorization: Basic YWxpY2U6c2VjcmV0MTIz
    Server->>Database: Verify credentials
    Database->>Server: Valid
    Server->>Client: 200 OK + Response

    classDef blue fill:#6B8DBE,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef teal fill:#6FAFA3,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef amber fill:#C2A25F,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF

    class Client,Server blue
    class Database teal
```

**Flow Explanation**:

1. **Initial Request**: Client requests protected resource without credentials
2. **Challenge**: Server responds 401 with `WWW-Authenticate` header
3. **Credential Encoding**: Client encodes username:password in Base64
4. **Authenticated Request**: Client sends request with `Authorization` header
5. **Validation**: Server decodes and verifies credentials against database
6. **Response**: Server grants access if credentials valid
7. **Subsequent Requests**: Client must send credentials with EVERY request

### 3.4 Implementing Basic Auth in FastAPI

#### HTTPBasic Security

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Annotated
import secrets

app = FastAPI()
security = HTTPBasic()

@app.get("/basic-protected")
async def basic_protected(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)]
):
    """
    Endpoint protected with Basic Auth.
    FastAPI automatically:
    - Parses Authorization header
    - Decodes Base64
    - Provides username and password
    """
    return {
        "message": "Authenticated",
        "username": credentials.username
    }
```

#### HTTPBasicCredentials

```python
from fastapi.security import HTTPBasicCredentials

# HTTPBasicCredentials is a Pydantic model with:
# - username: str
# - password: str

async def verify_basic_credentials(
    credentials: HTTPBasicCredentials
) -> bool:
    """
    Verify credentials against stored values.
    """
    correct_username = secrets.compare_digest(credentials.username, "alice")
    correct_password = secrets.compare_digest(credentials.password, "secret123")

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return True
```

**Why `secrets.compare_digest`?**

- Prevents timing attacks
- Compares strings in constant time
- Always use for credential comparison

#### Credentials Verification

```python
from passlib.context import CryptContext
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

async def get_current_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Verify credentials and return user object.
    """
    # Get user from database
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user

@app.get("/users/me")
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get current authenticated user.
    """
    return {
        "username": current_user.username,
        "email": current_user.email
    }
```

#### Custom Basic Auth Dependency

```python
from fastapi import Security
from fastapi.security import HTTPBasic
import secrets

security = HTTPBasic()

# Simple in-memory user store (for demonstration)
USERS = {
    "alice": {
        "password": "secret123",
        "role": "admin"
    },
    "bob": {
        "password": "password456",
        "role": "user"
    }
}

async def verify_basic_auth(
    credentials: Annotated[HTTPBasicCredentials, Security(security)]
) -> dict:
    """
    Custom basic auth verification.

    Returns:
        User dict if authenticated

    Raises:
        HTTPException if authentication fails
    """
    user = USERS.get(credentials.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=\"API\""},
        )

    # Use constant-time comparison
    username_correct = secrets.compare_digest(
        credentials.username.encode("utf8"),
        credentials.username.encode("utf8")
    )
    password_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        user["password"].encode("utf8")
    )

    if not (username_correct and password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=\"API\""},
        )

    return user

@app.get("/admin")
async def admin_endpoint(
    user: Annotated[dict, Depends(verify_basic_auth)]
):
    """
    Admin-only endpoint.
    """
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return {"message": "Admin area", "user": user["username"]}
```

### 3.5 When to Use Basic Auth

**Appropriate Use Cases**:

**Development and Testing**:

```python
# Quick API for local development
@app.get("/dev/status")
async def dev_status(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    if not (credentials.username == "dev" and credentials.password == "local123"):
        raise HTTPException(status_code=401)
    return {"status": "Development server running"}
```

**Internal Tools**:

- Admin dashboards
- Monitoring endpoints
- Internal APIs between trusted services
- CI/CD health checks

**Simple Authentication Needs**:

- Webhook receivers
- Temporary endpoints
- Simple integrations
- Legacy system compatibility

**When NOT to Use**:

- Public-facing web applications
- Mobile applications
- Single-page applications (SPAs)
- Scenarios requiring logout functionality
- Multi-device scenarios

### 3.6 Basic Auth Limitations

#### Credentials in Every Request

**Problem**: Username and password sent with every API call

**Implications**:

- Increased exposure window
- More opportunities for credential interception
- Performance overhead (database lookups every request)
- Difficult to implement caching

**Comparison**:

```
Basic Auth: Send credentials 1000 times for 1000 requests
Token Auth: Send credentials once, use token for 999 requests
```

#### Must Use HTTPS

**Why Mandatory**:

- Base64 is NOT encryption
- Anyone intercepting HTTP traffic sees credentials
- Man-in-the-middle attacks trivial without HTTPS

**Attack Example (HTTP)**:

```bash
# Attacker captures HTTP request
Authorization: Basic YWxpY2U6c2VjcmV0MTIz

# Attacker decodes Base64
echo "YWxpY2U6c2VjcmV0MTIz" | base64 -d
# Output: alice:secret123
```

**Mitigation**: Always enforce HTTPS in production

```python
from fastapi import Request, HTTPException

@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if not request.url.scheme == "https" and request.url.hostname != "localhost":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HTTPS required"
        )
    return await call_next(request)
```

#### No Built-in Expiration

**Problem**: Credentials remain valid indefinitely

**Implications**:

- Stolen credentials work forever
- No automatic logout
- Difficult to revoke access without changing password
- No session management

**Workarounds**:

- Implement manual credential rotation
- Use time-based password changes
- Combine with IP whitelisting
- Add rate limiting

#### Limited Security

**Weaknesses**:

- No CSRF protection
- No built-in MFA support
- No refresh mechanism
- No scope/permission system
- Password changes require user update

### 3.7 Basic Auth Best Practices

```python
import secrets
from passlib.context import CryptContext
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class BasicAuthBestPractices:
    """
    Implementing Basic Auth with security best practices.
    """

    @staticmethod
    def verify_credentials_securely(
        username: str,
        password: str,
        db: Session
    ) -> User | None:
        """
        Secure credential verification.

        Best practices:
        - Use constant-time comparison
        - Hash passwords with bcrypt
        - Rate limit authentication attempts
        - Log failed attempts
        """
        # Get user
        user = db.query(User).filter(User.username == username).first()

        if not user:
            # Still verify against dummy hash to prevent timing attacks
            pwd_context.verify(password, "$2b$12$dummy_hash")
            return None

        # Verify password
        if not pwd_context.verify(password, user.password_hash):
            # Log failed attempt
            log_failed_login(username, "basic_auth")
            return None

        # Log successful login
        log_successful_login(username, "basic_auth")

        return user

    @staticmethod
    def enforce_https(request: Request):
        """Ensure HTTPS is used."""
        if request.url.scheme != "https" and request.url.hostname != "localhost":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HTTPS required for Basic Authentication"
            )

    @staticmethod
    def rate_limit_auth_attempts(username: str, db: Session):
        """
        Rate limit authentication attempts to prevent brute force.
        """
        from datetime import datetime, timedelta

        # Check failed attempts in last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        failed_attempts = db.query(LoginAttempt).filter(
            LoginAttempt.username == username,
            LoginAttempt.success == False,
            LoginAttempt.timestamp >= one_hour_ago
        ).count()

        if failed_attempts >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again later."
            )

# Usage
async def secure_basic_auth(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Secure Basic Auth implementation.
    """
    # Enforce HTTPS
    BasicAuthBestPractices.enforce_https(request)

    # Rate limiting
    BasicAuthBestPractices.rate_limit_auth_attempts(credentials.username, db)

    # Verify credentials
    user = BasicAuthBestPractices.verify_credentials_securely(
        credentials.username,
        credentials.password,
        db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=\"API\""}
        )

    return user
```

---

## 4. Bearer Token Authentication

### 4.1 What are Bearer Tokens?

Bearer tokens are access tokens that grant the "bearer" (holder) access to protected resources. The name comes from the concept that whoever "bears" the token has access rights.

**Definition from RFC 6750**:

> A security token with the property that any party in possession of the token (a "bearer") can use the token in any way that any other party in possession of it can.

**Key Characteristics**:

- No cryptographic proof of possession required
- Token itself is the credential
- No need to prove you own the token
- Must be protected in transit and storage

**Security Implication**: Tokens are like cash. Anyone who has the token can use it. This is why secure transmission (HTTPS) and storage are critical.

### 4.2 How Bearer Tokens Work

#### Authorization Header Format

```
Authorization: Bearer <token>
```

**Example**:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U
```

**Header Components**:

- `Authorization`: HTTP header name
- `Bearer`: Authentication scheme
- `<token>`: The actual token string

#### Token Format

Bearer tokens can be:

**Opaque Tokens**: Random strings with no inherent meaning

```
b7f3a8c9-4e2d-4c1b-9f8e-3a5d7c9e1f4a
1234567890abcdef
sk_live_abc123xyz789
```

**Structured Tokens**: Contain encoded information (like JWT)

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### 4.3 Bearer Token Types

#### Opaque Tokens

**Definition**: Random strings with no embedded information. Validation requires database lookup.

**Characteristics**:

- Server-side state required
- No embedded claims
- Cannot be validated without database
- Easy to revoke
- Shorter strings possible

**Example**:

```python
import secrets

def generate_opaque_token() -> str:
    """Generate random opaque token."""
    return secrets.token_urlsafe(32)

# Output: 'dGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBkZW1v'
```

**Validation Process**:

```
Client sends token → Server looks up in database → Database returns user info
```

#### JWT Tokens

**Definition**: JSON Web Tokens containing encoded claims. Self-contained and stateless.

**Characteristics**:

- No database lookup needed for validation
- Contains user information (claims)
- Can be validated using signature
- Larger size than opaque tokens
- Difficult to revoke (no server state)

**Structure**:

```
Header.Payload.Signature

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9  ← Header
.
eyJzdWIiOiIxMjM0NTY3ODkwIn0              ← Payload
.
dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP     ← Signature
```

**Validation Process**:

```
Client sends JWT → Server verifies signature → Extract claims from payload
```

We'll cover JWT in detail in Day 7.

#### Custom Tokens

**Definition**: Application-specific token formats designed for unique requirements.

**Examples**:

**Prefixed tokens** (Stripe-style):

```python
def generate_prefixed_token(prefix: str = "tok") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"

# Output: 'tok_dGhpcyBpcyBhIHRlc3Qgc3RyaW5n'
```

**Composite tokens** (encode metadata):

```python
import base64
import json

def generate_composite_token(user_id: str, expires: datetime) -> str:
    data = {
        "user_id": user_id,
        "expires": expires.isoformat(),
        "random": secrets.token_hex(16)
    }
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
```

### 4.4 Implementing Bearer Tokens in FastAPI

#### HTTPBearer Security

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

app = FastAPI()
security = HTTPBearer()

@app.get("/bearer-protected")
async def bearer_protected(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
):
    """
    Endpoint protected with Bearer token.
    FastAPI automatically:
    - Parses Authorization header
    - Validates Bearer scheme
    - Extracts token
    """
    return {
        "message": "Authenticated",
        "token": credentials.credentials  # The actual token
    }
```

#### Token Validation Logic

```python
import hashlib
from sqlalchemy.orm import Session

class AccessToken(Base):
    __tablename__ = "access_tokens"

    id = Column(String, primary_key=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)

def hash_token(token: str) -> str:
    """Hash token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()

def validate_bearer_token(db: Session, token: str) -> User | None:
    """
    Validate bearer token and return associated user.

    Returns:
        User object if token valid, None otherwise
    """
    token_hash = hash_token(token)

    # Look up token
    access_token = db.query(AccessToken).filter(
        AccessToken.token_hash == token_hash,
        AccessToken.is_revoked == False
    ).first()

    if not access_token:
        return None

    # Check expiration
    if access_token.expires_at < datetime.utcnow():
        return None

    # Get and return user
    user = db.query(User).filter(User.id == access_token.user_id).first()

    return user

async def get_current_user_bearer(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current user from bearer token.
    """
    token = credentials.credentials

    user = validate_bearer_token(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

@app.get("/users/me")
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user_bearer)]
):
    """Get current authenticated user."""
    return {
        "username": current_user.username,
        "email": current_user.email
    }
```

#### Custom Token Generation

```python
import secrets
from datetime import datetime, timedelta

def create_access_token(
    db: Session,
    user_id: str,
    expires_delta: timedelta = timedelta(hours=24)
) -> str:
    """
    Create new access token for user.

    Returns:
        Plaintext token (send to client)
    """
    # Generate token
    plaintext_token = secrets.token_urlsafe(32)
    token_hash = hash_token(plaintext_token)

    # Store in database
    access_token = AccessToken(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        user_id=user_id,
        expires_at=datetime.utcnow() + expires_delta
    )

    db.add(access_token)
    db.commit()

    return plaintext_token

@app.post("/login")
async def login(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    db: Session = Depends(get_db)
):
    """
    Login endpoint that returns bearer token.
    """
    # Verify credentials
    user = verify_credentials(db, credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create access token
    access_token = create_access_token(db, user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400  # 24 hours in seconds
    }
```

#### Token Storage (Database/Cache)

**Database Storage**:

```python
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from datetime import datetime

class AccessToken(Base):
    __tablename__ = "access_tokens"

    id = Column(String, primary_key=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    last_used = Column(DateTime, nullable=True)

    # Optional: Device/client info
    device_info = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
```

**Redis Cache Storage** (for faster lookups):

```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def store_token_redis(token: str, user_id: str, expires_in: int = 86400):
    """
    Store token in Redis with expiration.

    Args:
        token: Plaintext token
        user_id: Associated user ID
        expires_in: Expiration time in seconds
    """
    token_hash = hash_token(token)

    token_data = {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat()
    }

    redis_client.setex(
        f"token:{token_hash}",
        expires_in,
        json.dumps(token_data)
    )

def validate_token_redis(token: str) -> str | None:
    """
    Validate token from Redis.

    Returns:
        User ID if valid, None otherwise
    """
    token_hash = hash_token(token)

    token_data = redis_client.get(f"token:{token_hash}")

    if not token_data:
        return None

    data = json.loads(token_data)
    return data["user_id"]
```

**Hybrid Approach** (Redis + Database):

```python
def validate_token_hybrid(db: Session, token: str) -> User | None:
    """
    Validate token using Redis cache with database fallback.
    """
    # Try Redis first (fast)
    user_id = validate_token_redis(token)

    if user_id:
        # Cache hit - get user from database
        return db.query(User).filter(User.id == user_id).first()

    # Cache miss - validate from database
    user = validate_bearer_token(db, token)

    if user:
        # Store in cache for next time
        store_token_redis(token, user.id)

    return user
```

### 4.5 Bearer Token Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Generated: User Login
    Generated --> Active: First Use
    Active --> Active: Regular Use
    Active --> Expired: TTL Elapsed
    Active --> Revoked: Manual Revocation
    Active --> Refreshed: Refresh Token Exchange
    Expired --> [*]
    Revoked --> [*]
    Refreshed --> [*]

    classDef blue fill:#6B8DBE,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef green fill:#7FAE8A,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef amber fill:#C2A25F,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef red fill:#C26D63,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF

    class Generated blue
    class Active green
    class Expired,Refreshed amber
    class Revoked red
```

#### Token Generation

```python
from datetime import datetime, timedelta
import secrets

def generate_token_with_metadata(
    db: Session,
    user_id: str,
    device_info: str = None,
    ip_address: str = None
) -> dict:
    """
    Generate access token with full metadata.

    Returns:
        Dict with token and metadata
    """
    # Generate token
    plaintext_token = secrets.token_urlsafe(32)
    token_hash = hash_token(plaintext_token)

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(hours=24)

    # Store in database
    access_token = AccessToken(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        user_id=user_id,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address
    )

    db.add(access_token)
    db.commit()

    return {
        "access_token": plaintext_token,
        "token_type": "bearer",
        "expires_in": 86400,  # seconds
        "expires_at": expires_at.isoformat()
    }
```

#### Token Validation

```python
def validate_token_comprehensive(
    db: Session,
    token: str,
    check_device: bool = False,
    expected_ip: str = None
) -> tuple[User | None, str | None]:
    """
    Comprehensive token validation.

    Returns:
        Tuple of (User object, error message)
    """
    token_hash = hash_token(token)

    # Look up token
    access_token = db.query(AccessToken).filter(
        AccessToken.token_hash == token_hash
    ).first()

    if not access_token:
        return None, "Token not found"

    # Check if revoked
    if access_token.is_revoked:
        return None, "Token has been revoked"

    # Check expiration
    if access_token.expires_at < datetime.utcnow():
        return None, "Token has expired"

    # Optional: Check IP address
    if expected_ip and access_token.ip_address != expected_ip:
        return None, "IP address mismatch"

    # Update last used
    access_token.last_used = datetime.utcnow()
    db.commit()

    # Get user
    user = db.query(User).filter(User.id == access_token.user_id).first()

    if not user:
        return None, "User not found"

    return user, None
```

#### Token Expiration

```python
from datetime import datetime, timedelta

class TokenExpiration:
    """Token expiration strategies."""

    @staticmethod
    def short_lived(hours: int = 1) -> datetime:
        """Short-lived tokens for high-security operations."""
        return datetime.utcnow() + timedelta(hours=hours)

    @staticmethod
    def standard(hours: int = 24) -> datetime:
        """Standard token lifetime."""
        return datetime.utcnow() + timedelta(hours=hours)

    @staticmethod
    def long_lived(days: int = 30) -> datetime:
        """Long-lived tokens (use with caution)."""
        return datetime.utcnow() + timedelta(days=days)

    @staticmethod
    def sliding_expiration(
        db: Session,
        token: AccessToken,
        extend_by_hours: int = 1
    ):
        """
        Extend token expiration on each use.
        """
        token.expires_at = datetime.utcnow() + timedelta(hours=extend_by_hours)
        db.commit()

# Usage in token validation
async def validate_with_sliding_expiration(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    token_hash = hash_token(token)

    access_token = db.query(AccessToken).filter(
        AccessToken.token_hash == token_hash,
        AccessToken.is_revoked == False
    ).first()

    if not access_token or access_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid token")

    # Extend expiration on each use
    TokenExpiration.sliding_expiration(db, access_token, extend_by_hours=24)

    user = db.query(User).filter(User.id == access_token.user_id).first()
    return user
```

#### Token Revocation

```python
@app.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_user_bearer)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
):
    """
    Logout by revoking current token.
    """
    token = credentials.credentials
    token_hash = hash_token(token)

    # Revoke token
    access_token = db.query(AccessToken).filter(
        AccessToken.token_hash == token_hash
    ).first()

    if access_token:
        access_token.is_revoked = True
        db.commit()

    return {"message": "Logged out successfully"}

@app.post("/logout-all")
async def logout_all_devices(
    current_user: Annotated[User, Depends(get_current_user_bearer)],
    db: Session = Depends(get_db)
):
    """
    Revoke all tokens for current user (logout from all devices).
    """
    db.query(AccessToken).filter(
        AccessToken.user_id == current_user.id,
        AccessToken.is_revoked == False
    ).update({"is_revoked": True})

    db.commit()

    return {"message": "Logged out from all devices"}

@app.delete("/tokens/{token_id}")
async def revoke_specific_token(
    token_id: str,
    current_user: Annotated[User, Depends(get_current_user_bearer)],
    db: Session = Depends(get_db)
):
    """
    Revoke specific token by ID.
    """
    token = db.query(AccessToken).filter(
        AccessToken.id == token_id,
        AccessToken.user_id == current_user.id
    ).first()

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.is_revoked = True
    db.commit()

    return {"message": "Token revoked"}
```

### 4.6 Bearer Token Best Practices

```python
class BearerTokenBestPractices:
    """Best practices for bearer token implementation."""

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate cryptographically secure token.
        Minimum 32 bytes (256 bits) recommended.
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def enforce_https(request: Request):
        """Ensure HTTPS for token transmission."""
        if request.url.scheme != "https" and request.url.hostname != "localhost":
            raise HTTPException(
                status_code=403,
                detail="Bearer tokens must be sent over HTTPS"
            )

    @staticmethod
    def set_appropriate_expiration(token_type: str) -> timedelta:
        """
        Set expiration based on token type and security needs.
        """
        expiration_map = {
            "access": timedelta(hours=1),      # Short-lived
            "refresh": timedelta(days=30),     # Long-lived
            "api": timedelta(days=90),         # API keys
            "temporary": timedelta(minutes=15) # Password reset, etc.
        }
        return expiration_map.get(token_type, timedelta(hours=24))

    @staticmethod
    def implement_token_rotation(
        db: Session,
        old_token: str,
        user_id: str
    ) -> str:
        """
        Rotate token by revoking old and issuing new.
        """
        # Revoke old token
        old_hash = hash_token(old_token)
        db.query(AccessToken).filter(
            AccessToken.token_hash == old_hash
        ).update({"is_revoked": True})

        # Create new token
        new_token = create_access_token(db, user_id)

        db.commit()
        return new_token

    @staticmethod
    def audit_token_usage(
        db: Session,
        token_id: str,
        action: str,
        ip_address: str
    ):
        """
        Log token usage for security auditing.
        """
        audit_log = TokenAuditLog(
            id=str(uuid.uuid4()),
            token_id=token_id,
            action=action,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)
        db.commit()

# Secure token dependency
async def get_current_user_secure(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Secure bearer token validation with all best practices.
    """
    # Enforce HTTPS
    BearerTokenBestPractices.enforce_https(request)

    # Validate token
    token = credentials.credentials
    user, error = validate_token_comprehensive(
        db,
        token,
        expected_ip=request.client.host
    )

    if error:
        raise HTTPException(status_code=401, detail=error)

    # Audit token usage
    token_hash = hash_token(token)
    token_record = db.query(AccessToken).filter(
        AccessToken.token_hash == token_hash
    ).first()

    if token_record:
        BearerTokenBestPractices.audit_token_usage(
            db,
            token_record.id,
            "api_access",
            request.client.host
        )

    return user
```

---

## 5. Authentication Methods Comparison

### 5.1 Security Comparison

| Method            | Security Level | Vulnerabilities                                     | Mitigations                                      |
| ----------------- | -------------- | --------------------------------------------------- | ------------------------------------------------ |
| **API Keys**      | Low-Medium     | Exposure in logs, No expiration, Difficult rotation | Use headers, Hash storage, Implement rotation    |
| **Basic Auth**    | Low            | Credentials every request, Base64 not encryption    | HTTPS mandatory, Rate limiting, Strong passwords |
| **Bearer Tokens** | Medium-High    | Token theft, No proof of possession                 | Short expiration, Secure storage, HTTPS          |

**Detailed Security Analysis**:

**API Keys**:

- Pros: Simple, Good for service-to-service
- Cons: Long-lived, Often lack expiration
- Recommendation: Use for backend services only

**Basic Auth**:

- Pros: Simple, Stateless, Standard
- Cons: Credentials exposed repeatedly, No session control
- Recommendation: Development/internal tools only

**Bearer Tokens**:

- Pros: Stateless possible, Token rotation, Fine-grained control
- Cons: Requires careful implementation, Token management complexity
- Recommendation: Modern web/mobile applications

### 5.2 Complexity Comparison

| Method            | Implementation | Client        | Server                      | Maintenance      |
| ----------------- | -------------- | ------------- | --------------------------- | ---------------- |
| **API Keys**      | Very Simple    | Store key     | Hash validation             | Key rotation     |
| **Basic Auth**    | Simple         | Base64 encode | Decode + verify             | Password changes |
| **Bearer Tokens** | Medium         | Token storage | Token validation + database | Token lifecycle  |

**Development Effort**:

```
Lowest to Highest Complexity:
1. API Keys (1-2 hours to implement)
2. Basic Auth (2-3 hours)
3. Bearer Tokens (4-8 hours)
4. OAuth2 (16-40 hours)
5. SAML (40+ hours)
```

### 5.3 Use Case Matrix

| Use Case                | Recommended Method  | Alternative   | Avoid                 |
| ----------------------- | ------------------- | ------------- | --------------------- |
| Public Web App          | Bearer Tokens (JWT) | OAuth2        | API Keys, Basic Auth  |
| Mobile App              | Bearer Tokens       | OAuth2        | Basic Auth            |
| Microservices           | API Keys            | Bearer Tokens | Basic Auth            |
| CLI Tool                | API Keys            | Bearer Tokens | Basic Auth            |
| Third-party Integration | OAuth2              | API Keys      | Basic Auth, Passwords |
| Internal Admin Panel    | Basic Auth (HTTPS)  | Bearer Tokens | Public API Keys       |
| Webhook Receiver        | API Keys            | Bearer Tokens | Basic Auth            |

### 5.4 Performance Considerations

**Request Overhead**:

```
API Keys: Low (single database lookup)
Basic Auth: Medium (credential verification each request)
Bearer Tokens: Low (cached) to Medium (database lookup)
```

**Database Impact**:

```python
# API Key (1 query per request)
api_key = db.query(APIKey).filter(key_hash=hash).first()

# Basic Auth (1-2 queries per request)
user = db.query(User).filter(username=user).first()
verify_password(password, user.password_hash)  # CPU intensive

# Bearer Token (0-1 queries)
# If using JWT: 0 queries (signature validation only)
# If opaque token: 1 query
token = db.query(Token).filter(token_hash=hash).first()
```

**Optimization Strategies**:

```python
# Cache frequently used API keys
@lru_cache(maxsize=1000)
def get_api_key_cached(key_hash: str) -> APIKey:
    return db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

# Use Redis for token validation
def validate_token_fast(token: str) -> User:
    # Try cache first
    user_data = redis.get(f"token:{hash_token(token)}")
    if user_data:
        return deserialize_user(user_data)

    # Fallback to database
    user = validate_from_database(token)
    if user:
        redis.setex(f"token:{hash_token(token)}", 300, serialize_user(user))

    return user
```

### 5.5 Mobile vs Web Considerations

**Mobile Applications**:

```python
# Recommended: Long-lived refresh tokens + short access tokens
@app.post("/mobile/login")
async def mobile_login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = verify_credentials(db, credentials.username, credentials.password)

    # Short-lived access token (1 hour)
    access_token = create_access_token(user.id, timedelta(hours=1))

    # Long-lived refresh token (30 days)
    refresh_token = create_refresh_token(user.id, timedelta(days=30))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 3600
    }

@app.post("/mobile/refresh")
async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    user = validate_refresh_token(db, refresh_token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Issue new access token
    new_access_token = create_access_token(user.id, timedelta(hours=1))

    return {
        "access_token": new_access_token,
        "expires_in": 3600
    }
```

**Web Applications (SPA)**:

```python
# Recommended: HttpOnly cookies for refresh, memory for access
@app.post("/web/login")
async def web_login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    user = verify_credentials(db, credentials.username, credentials.password)

    # Short-lived access token (returned in body, stored in memory)
    access_token = create_access_token(user.id, timedelta(minutes=15))

    # Long-lived refresh token (HttpOnly cookie)
    refresh_token = create_refresh_token(user.id, timedelta(days=7))

    # Set refresh token in HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7*24*60*60  # 7 days
    )

    return {
        "access_token": access_token,
        "expires_in": 900  # 15 minutes
    }
```

### 5.6 Decision Framework

```mermaid
graph TD
    A[Start: Choose Auth Method] --> B{What type of client?}
    B -->|Server/Service| C[API Keys]
    B -->|Browser/SPA| D{Need third-party access?}
    B -->|Mobile App| E[Bearer Tokens<br/>Access + Refresh]
    B -->|CLI Tool| C

    D -->|Yes| F[OAuth2]
    D -->|No| G[Bearer Tokens<br/>JWT or Opaque]

    C --> H{Internal or External?}
    H -->|Internal| I[Simple API Key]
    H -->|External| J[API Key with<br/>Rate Limiting + Scopes]

    G --> K{Stateless requirement?}
    K -->|Yes| L[JWT Bearer Tokens]
    K -->|No| M[Opaque Tokens<br/>Database validation]

    classDef blue fill:#6B8DBE,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef teal fill:#6FAFA3,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef green fill:#7FAE8A,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF
    classDef neutral fill:#3A3F4B,stroke:#FFFFFF,stroke-width:2px,color:#FFFFFF

    class A,B neutral
    class C,E,F,G blue
    class I,J,L,M teal
```

**Decision Criteria**:

1. **Client Type**: Server, Browser, Mobile, CLI
2. **Security Requirements**: High, Medium, Low
3. **Stateless Requirement**: Yes, No, Flexible
4. **Third-party Access**: Yes, No
5. **Development Timeline**: Quick, Standard, Complex
6. **Scalability Needs**: Small, Medium, Large

**Quick Reference**:

```
Internal microservices → API Keys
Public API → API Keys with rate limiting
Web SPA → Bearer Tokens (JWT)
Mobile App → Bearer Tokens (access + refresh)
Third-party integrations → OAuth2
Development/Testing → Basic Auth (HTTPS)
```

---

## 6. Complete Practical Examples

### 6.1 API Key Authentication System

```python
from fastapi import FastAPI, Security, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Annotated

app = FastAPI()

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Database models (simplified)
class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True)
    key_hash = Column(String(64), unique=True, index=True)
    name = Column(String(100))
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=1000)

# Helper functions
def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def generate_api_key() -> str:
    return f"sk_{secrets.token_hex(32)}"

# Key generation endpoint
@app.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new API key for authenticated user.
    """
    # Generate key
    plaintext_key = generate_api_key()
    key_hash = hash_api_key(plaintext_key)

    # Store in database
    api_key = APIKey(
        id=str(uuid.uuid4()),
        key_hash=key_hash,
        name=name,
        user_id=current_user.id
    )

    db.add(api_key)
    db.commit()

    return {
        "api_key": plaintext_key,
        "key_id": api_key.id,
        "name": name,
        "created_at": api_key.created_at,
        "warning": "Store this key securely. It cannot be retrieved again."
    }

# Key validation dependency
async def validate_api_key(
    api_key: Annotated[str, Security(api_key_header)],
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Validate API key and return key object.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in X-API-Key header"
        )

    key_hash = hash_api_key(api_key)

    key_record = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Update last used
    key_record.last_used = datetime.utcnow()
    db.commit()

    return key_record

# Protected endpoints
@app.get("/protected/data")
async def get_protected_data(
    api_key: Annotated[APIKey, Depends(validate_api_key)]
):
    """
    Endpoint protected with API key authentication.
    """
    return {
        "message": "Access granted",
        "data": "Secret data",
        "api_key_name": api_key.name,
        "user_id": api_key.user_id
    }

@app.get("/api-keys/list")
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all API keys for current user.
    """
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).all()

    return {
        "keys": [
            {
                "id": key.id,
                "name": key.name,
                "created_at": key.created_at,
                "last_used": key.last_used,
                "is_active": key.is_active
            }
            for key in keys
        ]
    }

@app.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke (deactivate) API key.
    """
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    key.is_active = False
    db.commit()

    return {"message": "API key revoked"}
```

### 6.2 Basic Auth System

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Annotated
import secrets

app = FastAPI()
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User credentials storage
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    email = Column(String(100))
    is_active = Column(Boolean, default=True)

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Basic auth dependency
async def get_current_user_basic(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate user with Basic Auth.
    """
    # Get user from database
    user = db.query(User).filter(
        User.username == credentials.username
    ).first()

    # Always verify password even if user not found (timing attack prevention)
    if not user:
        pwd_context.verify(credentials.password, "$2b$12$dummy_hash_to_prevent_timing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user

# Protected endpoints
@app.get("/basic/profile")
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user_basic)]
):
    """
    Get current user profile (Basic Auth protected).
    """
    return {
        "username": current_user.username,
        "email": current_user.email
    }

@app.post("/basic/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: Annotated[User, Depends(get_current_user_basic)],
    db: Session = Depends(get_db)
):
    """
    Change user password.
    """
    # Verify old password
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update password
    current_user.password_hash = hash_password(new_password)
    db.commit()

    return {"message": "Password changed successfully"}
```

### 6.3 Bearer Token System

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Annotated
import secrets
import hashlib

app = FastAPI()
security = HTTPBearer()

# Token storage
class AccessToken(Base):
    __tablename__ = "access_tokens"

    id = Column(String, primary_key=True)
    token_hash = Column(String(64), unique=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_revoked = Column(Boolean, default=False)

# Helper functions
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(user_id: str, db: Session) -> str:
    """Create new access token."""
    plaintext_token = secrets.token_urlsafe(32)
    token_hash = hash_token(plaintext_token)

    access_token = AccessToken(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.add(access_token)
    db.commit()

    return plaintext_token

# Token generation endpoint
@app.post("/token")
async def login(
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    Login and receive bearer token.
    """
    # Verify credentials (using Basic Auth logic)
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create token
    access_token = create_access_token(user.id, db)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400
    }

# Token validation dependency
async def get_current_user_bearer(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Validate bearer token and return user.
    """
    token = credentials.credentials
    token_hash = hash_token(token)

    # Look up token
    access_token = db.query(AccessToken).filter(
        AccessToken.token_hash == token_hash,
        AccessToken.is_revoked == False
    ).first()

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration
    if access_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user = db.query(User).filter(User.id == access_token.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user

# Protected endpoints
@app.get("/bearer/profile")
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user_bearer)]
):
    """
    Get current user profile (Bearer token protected).
    """
    return {
        "username": current_user.username,
        "email": current_user.email
    }

@app.post("/bearer/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
):
    """
    Logout by revoking current token.
    """
    token = credentials.credentials
    token_hash = hash_token(token)

    access_token = db.query(AccessToken).filter(
        AccessToken.token_hash == token_hash
    ).first()

    if access_token:
        access_token.is_revoked = True
        db.commit()

    return {"message": "Logged out successfully"}
```

### 6.4 Multi-Method Authentication

```python
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBasic, HTTPBearer, APIKeyHeader
from typing import Annotated, Union

app = FastAPI()

# All security schemes
basic_auth = HTTPBasic(auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)
api_key_auth = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user_multi_method(
    basic_credentials: Annotated[HTTPBasicCredentials | None, Depends(basic_auth)],
    bearer_credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_auth)],
    api_key: Annotated[str | None, Security(api_key_auth)],
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate using any of three methods: API Key, Basic Auth, or Bearer Token.
    Tries in order: Bearer > API Key > Basic Auth
    """
    # Try Bearer token first (most common for modern apps)
    if bearer_credentials:
        return await get_current_user_bearer(bearer_credentials, db)

    # Try API key second
    if api_key:
        key_record = await validate_api_key(api_key, db)
        user = db.query(User).filter(User.id == key_record.user_id).first()
        if user:
            return user

    # Try Basic Auth last
    if basic_credentials:
        return await get_current_user_basic(basic_credentials, db)

    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token, API key, or Basic Auth credentials.",
        headers={
            "WWW-Authenticate": 'Bearer, Basic, ApiKey'
        }
    )

@app.get("/multi-auth/data")
async def get_data_multi_auth(
    current_user: Annotated[User, Depends(get_current_user_multi_method)]
):
    """
    Endpoint accepting multiple authentication methods.

    Usage:
    - Bearer: Authorization: Bearer <token>
    - API Key: X-API-Key: <key>
    - Basic: Authorization: Basic <base64(username:password)>
    """
    return {
        "message": "Authenticated successfully",
        "user": current_user.username,
        "data": "Secret information"
    }
```

---

## 7. Testing Authentication

### 7.1 Testing with curl

**API Key Authentication**:

```bash
# Header-based API key
curl -X GET http://localhost:8000/protected/data \
  -H "X-API-Key: sk_abc123xyz789"

# Query parameter API key (less secure)
curl -X GET "http://localhost:8000/protected/data?api_key=sk_abc123xyz789"
```

**Basic Authentication**:

```bash
# Using -u flag (recommended)
curl -X GET http://localhost:8000/basic/profile \
  -u alice:secret123

# Manual Authorization header
curl -X GET http://localhost:8000/basic/profile \
  -H "Authorization: Basic YWxpY2U6c2VjcmV0MTIz"

# Generate Base64 encoding
echo -n "alice:secret123" | base64
# Output: YWxpY2U6c2VjcmV0MTIz
```

**Bearer Token Authentication**:

```bash
# Get token
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'

# Response: {"access_token": "abc123...", "token_type": "bearer"}

# Use token
curl -X GET http://localhost:8000/bearer/profile \
  -H "Authorization: Bearer abc123..."
```

### 7.2 Testing with Postman

**API Key in Postman**:

1. Open request
2. Go to "Authorization" tab
3. Select "API Key" from Type dropdown
4. Key: `X-API-Key`
5. Value: `sk_abc123xyz789`
6. Add to: `Header`

**Basic Auth in Postman**:

1. Go to "Authorization" tab
2. Select "Basic Auth" from Type dropdown
3. Username: `alice`
4. Password: `secret123`
5. Postman automatically encodes and adds Authorization header

**Bearer Token in Postman**:

1. First, get token from login endpoint
2. Go to "Authorization" tab
3. Select "Bearer Token" from Type dropdown
4. Token: `paste_your_token_here`
5. Postman adds "Authorization: Bearer <token>" header

### 7.3 Testing with Python requests

**API Key**:

```python
import requests

# Header-based
response = requests.get(
    "http://localhost:8000/protected/data",
    headers={"X-API-Key": "sk_abc123xyz789"}
)

print(response.json())
```

**Basic Auth**:

```python
import requests
from requests.auth import HTTPBasicAuth

# Using HTTPBasicAuth (recommended)
response = requests.get(
    "http://localhost:8000/basic/profile",
    auth=HTTPBasicAuth('alice', 'secret123')
)

# Or using tuple shorthand
response = requests.get(
    "http://localhost:8000/basic/profile",
    auth=('alice', 'secret123')
)

print(response.json())
```

**Bearer Token**:

```python
import requests

# Get token
login_response = requests.post(
    "http://localhost:8000/token",
    json={"username": "alice", "password": "secret123"}
)

token = login_response.json()["access_token"]

# Use token
response = requests.get(
    "http://localhost:8000/bearer/profile",
    headers={"Authorization": f"Bearer {token}"}
)

print(response.json())
```

### 7.4 Automated Authentication Tests

**pytest Tests**:

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestAPIKeyAuth:
    def test_valid_api_key(self):
        response = client.get(
            "/protected/data",
            headers={"X-API-Key": "valid_key_here"}
        )
        assert response.status_code == 200

    def test_invalid_api_key(self):
        response = client.get(
            "/protected/data",
            headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401

    def test_missing_api_key(self):
        response = client.get("/protected/data")
        assert response.status_code == 401

class TestBasicAuth:
    def test_valid_credentials(self):
        response = client.get(
            "/basic/profile",
            auth=("alice", "secret123")
        )
        assert response.status_code == 200
        assert response.json()["username"] == "alice"

    def test_invalid_password(self):
        response = client.get(
            "/basic/profile",
            auth=("alice", "wrong_password")
        )
        assert response.status_code == 401

    def test_nonexistent_user(self):
        response = client.get(
            "/basic/profile",
            auth=("nonexistent", "password")
        )
        assert response.status_code == 401

class TestBearerToken:
    def test_login_success(self):
        response = client.post(
            "/token",
            json={"username": "alice", "password": "secret123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    def test_valid_token(self):
        # Get token
        login_response = client.post(
            "/token",
            json={"username": "alice", "password": "secret123"}
        )
        token = login_response.json()["access_token"]

        # Use token
        response = client.get(
            "/bearer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_invalid_token(self):
        response = client.get(
            "/bearer/profile",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_logout(self):
        # Login
        login_response = client.post(
            "/token",
            json={"username": "alice", "password": "secret123"}
        )
        token = login_response.json()["access_token"]

        # Logout
        logout_response = client.post(
            "/bearer/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == 200

        # Token should no longer work
        response = client.get(
            "/bearer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
```

---

## 8. Common Pitfalls

1. **Storing API keys in plaintext** - Always hash keys before storage
2. **Using Basic Auth without HTTPS** - Credentials exposed in Base64
3. **No token expiration** - Stolen tokens valid forever
4. **Logging tokens/credentials** - Sensitive data in log files
5. **Client-side token storage in localStorage** - XSS vulnerability
6. **No rate limiting** - Brute force attacks possible
7. **Hardcoded credentials** - Keys committed to version control
8. **Weak token generation** - Using `random` instead of `secrets`
9. **No CSRF protection with cookies** - Session hijacking
10. **Exposing token implementation details** - Information leakage in errors

---

## 9. Key Takeaways

1. **API Keys** are simple but require careful management and rotation
2. **Basic Auth** is convenient for development but insecure without HTTPS
3. **Bearer Tokens** provide flexibility and are suitable for modern applications
4. **Always use HTTPS** for any authentication method in production
5. **Hash credentials before storage** - never store plaintext
6. **Implement rate limiting** to prevent brute force attacks
7. **Use short-lived tokens** with refresh mechanisms
8. **Token revocation** is critical for security
9. **Different use cases** require different authentication methods
10. **Defense in depth** - combine authentication with authorization and other security measures

---

## 10. Practice Exercises

**Exercise 1: Implement Rotating API Keys**

Create a system that:

- Generates API keys with expiration dates
- Automatically notifies users before expiration
- Allows key rotation before expiration
- Revokes expired keys automatically

**Exercise 2: Secure Basic Auth Implementation**

Build a Basic Auth system with:

- Rate limiting (5 attempts per minute)
- Account lockout after 10 failed attempts
- Password strength validation
- Audit logging of authentication attempts

**Exercise 3: Bearer Token with Refresh**

Implement a complete token system with:

- Short-lived access tokens (15 minutes)
- Long-lived refresh tokens (30 days)
- Refresh token rotation on use
- Logout from all devices functionality

**Exercise 4: Multi-Method Authentication**

Create an API that supports:

- API Keys for service-to-service
- Basic Auth for CLI tools
- Bearer Tokens for web/mobile
- Proper error messages for each method

**Exercise 5: Authentication Security Audit**

Review provided codebase and:

- Identify authentication vulnerabilities
- Classify by severity
- Propose fixes with code examples
- Write tests to verify fixes
