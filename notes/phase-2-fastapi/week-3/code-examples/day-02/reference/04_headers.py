"""
HTTP Headers - Complete Guide
==============================

Topics covered:
1. Reading request headers
2. Header name conversion (snake_case ↔ kebab-case)
3. Required vs optional headers
4. Multiple headers
5. Header validation
6. Custom header names with alias
7. Duplicate/list headers
8. Common header patterns

Run: uvicorn 04_headers:app --reload
Test: http://localhost:8000/docs
"""

from fastapi import FastAPI, Header
from typing import List, Optional

app = FastAPI(
    title="HTTP Headers Guide",
    description="Complete guide to handling HTTP headers in FastAPI",
    version="1.0.0"
)

# =============================================================================
# 1. WHAT HEADERS ARE
# =============================================================================
"""
HTTP headers are METADATA sent with HTTP requests/responses.

Commonly used for:
- Authentication (Authorization)
- Client information (User-Agent)
- Content negotiation (Accept, Accept-Language)
- Request tracing (X-Request-ID)
- API keys and tokens

FastAPI treats headers as validated inputs, just like query/body parameters.
"""


# =============================================================================
# 2. READING REQUEST HEADERS
# =============================================================================

@app.get("/headers/basic")
async def read_basic_header(
    user_agent: str | None = Header(None)
):
    """
    Read a single request header.
    
    How it works:
    - Parameter uses Header(...)
    - FastAPI extracts value from HTTP headers
    - Type conversion and validation happen automatically
    
    Test with curl:
    curl http://localhost:8000/headers/basic \
      -H "User-Agent: MyCustomAgent/1.0"
    
    The User-Agent header is automatically sent by browsers and HTTP clients.
    """
    return {
        "user_agent": user_agent,
        "message": "Header received successfully"
    }


@app.get("/headers/multiple")
async def read_multiple_headers(
    user_agent: str | None = Header(None),
    accept: str | None = Header(None),
    accept_language: str | None = Header(None),
    accept_encoding: str | None = Header(None),
    referer: str | None = Header(None),
    host: str | None = Header(None)
):
    """
    Read multiple common request headers.
    
    Common headers:
    - User-Agent: Client/browser identification
    - Accept: Content types client can handle
    - Accept-Language: Preferred languages
    - Accept-Encoding: Supported compression
    - Referer: Previous page URL
    - Host: Target host and port
    
    These are automatically sent by browsers.
    """
    return {
        "user_agent": user_agent,
        "accept": accept,
        "accept_language": accept_language,
        "accept_encoding": accept_encoding,
        "referer": referer,
        "host": host
    }


# =============================================================================
# 3. HEADER NAME CONVERSION
# =============================================================================

@app.get("/headers/conversion")
async def header_name_conversion(
    user_agent: str | None = Header(None),
    x_token: str | None = Header(None),
    x_request_id: str | None = Header(None),
    content_type: str | None = Header(None)
):
    """
    FastAPI automatically converts between snake_case and kebab-case.
    
    Conversion rules:
    HTTP Header       → Python Parameter
    User-Agent        → user_agent
    X-Token           → x_token
    X-Request-ID      → x_request_id
    Content-Type      → content_type
    
    Why this works:
    - Python identifiers cannot contain '-'
    - FastAPI maps '_' ↔ '-' transparently
    
    Test with curl:
    curl http://localhost:8000/headers/conversion \
      -H "User-Agent: CustomAgent" \
      -H "X-Token: secret123" \
      -H "X-Request-ID: abc-123-def" \
      -H "Content-Type: application/json"
    """
    return {
        "user_agent": user_agent,
        "x_token": x_token,
        "x_request_id": x_request_id,
        "content_type": content_type,
        "note": "All header names were automatically converted"
    }


# =============================================================================
# 4. CUSTOM HEADER NAMES WITH ALIAS
# =============================================================================

@app.get("/headers/custom")
async def read_custom_headers(
    custom_header: str | None = Header(None, alias="X-Custom-Header"),
    weird_header: str | None = Header(None, alias="Weird.Header-Name"),
    api_key: str | None = Header(None, alias="X-API-Key")
):
    """
    Use alias for exact control over header names.
    
    When to use alias:
    - Header names with dots (.)
    - Non-standard or legacy headers
    - Strict API contracts
    - Special characters in names
    
    Test with curl:
    curl http://localhost:8000/headers/custom \
      -H "X-Custom-Header: custom_value" \
      -H "Weird.Header-Name: weird_value" \
      -H "X-API-Key: my_secret_key"
    """
    return {
        "custom_header": custom_header,
        "weird_header": weird_header,
        "api_key": api_key,
        "note": "These headers required exact names via alias"
    }


# =============================================================================
# 5. REQUIRED HEADERS
# =============================================================================

@app.get("/protected")
async def protected_route(
    authorization: str = Header(...)
):
    """
    Required header using Header(...) with ellipsis.
    
    Behavior:
    - Missing header → 422 Validation Error
    - Header present → injected into function
    - Validation occurs BEFORE endpoint logic
    
    This is the foundation of header-based authentication.
    
    Test with curl:
    # With header (works)
    curl http://localhost:8000/protected \
      -H "Authorization: Bearer secret_token_123"
    
    # Without header (fails)
    curl http://localhost:8000/protected
    """
    # Validate authorization format
    if not authorization.startswith("Bearer "):
        return {"error": "Invalid authorization format"}
    
    token = authorization.replace("Bearer ", "")
    
    return {
        "message": "Access granted",
        "token": token[:10] + "...",  # Show only first 10 chars
        "note": "In real apps, validate token against database"
    }


@app.get("/api/resource")
async def api_resource(
    x_api_key: str = Header(..., description="API key for authentication")
):
    """
    API key authentication pattern.
    
    Common in public APIs where each client has a unique key.
    
    Test with curl:
    curl http://localhost:8000/api/resource \
      -H "X-API-Key: my_api_key_12345"
    """
    # In real app: validate key against database
    valid_keys = {"my_api_key_12345", "another_key_67890"}
    
    if x_api_key not in valid_keys:
        return {"error": "Invalid API key"}
    
    return {
        "message": "Resource accessed successfully",
        "api_key": x_api_key[:8] + "...",
        "resource": {"id": 1, "data": "sensitive data"}
    }


# =============================================================================
# 6. HEADER VALIDATION
# =============================================================================

@app.get("/headers/validated")
async def validated_headers(
    x_api_key: str = Header(
        ...,
        min_length=32,
        max_length=32,
        regex="^[A-Za-z0-9]{32}$",
        description="32-character alphanumeric API key",
        example="abcdefghijklmnopqrstuvwxyz123456"
    ),
    x_client_version: str = Header(
        ...,
        regex=r"^\d+\.\d+\.\d+$",  # Semantic versioning
        description="Client version in format X.Y.Z",
        example="1.2.3"
    )
):
    """
    Headers with comprehensive validation.
    
    What FastAPI enforces:
    - Header presence (required)
    - Length constraints
    - Pattern matching (regex)
    - OpenAPI documentation
    
    Invalid headers never reach your business logic.
    
    Test with curl:
    # Valid
    curl http://localhost:8000/headers/validated \
      -H "X-API-Key: abcdefghijklmnopqrstuvwxyz123456" \
      -H "X-Client-Version: 1.2.3"
    
    # Invalid (wrong length)
    curl http://localhost:8000/headers/validated \
      -H "X-API-Key: short" \
      -H "X-Client-Version: 1.2.3"
    """
    return {
        "api_key": x_api_key[:8] + "..." + x_api_key[-4:],
        "client_version": x_client_version,
        "message": "Headers validated successfully"
    }


# =============================================================================
# 7. DUPLICATE/LIST HEADERS
# =============================================================================

@app.get("/headers/duplicate")
async def read_duplicate_headers(
    x_token: List[str] | None = Header(None)
):
    """
    Handle headers that may appear multiple times.
    
    Behavior:
    - Multiple headers → list of values
    - Single header → one-item list
    - Missing header → None
    
    Use case:
    - Multiple authentication tokens
    - Multiple API keys
    - Multiple trace IDs
    
    Test with curl:
    curl http://localhost:8000/headers/duplicate \
      -H "X-Token: token1" \
      -H "X-Token: token2" \
      -H "X-Token: token3"
    """
    if x_token:
        return {
            "tokens": x_token,
            "count": len(x_token),
            "message": f"Received {len(x_token)} tokens"
        }
    
    return {"message": "No tokens provided"}


# =============================================================================
# 8. COMMON HEADER PATTERNS
# =============================================================================

@app.get("/api/v1/users")
async def get_users_with_auth(
    authorization: str = Header(...),
    x_request_id: str | None = Header(None),
    x_correlation_id: str | None = Header(None)
):
    """
    Common production header pattern.
    
    Headers used:
    - Authorization: Authentication (required)
    - X-Request-ID: Request tracking (optional)
    - X-Correlation-ID: Distributed tracing (optional)
    
    This pattern is common in microservices.
    """
    # Parse authorization
    if not authorization.startswith("Bearer "):
        return {"error": "Invalid authorization format"}
    
    token = authorization.replace("Bearer ", "")
    
    return {
        "users": [
            {"id": 1, "username": "alice"},
            {"id": 2, "username": "bob"}
        ],
        "metadata": {
            "request_id": x_request_id,
            "correlation_id": x_correlation_id,
            "authenticated": True
        }
    }


@app.get("/api/versioned")
async def versioned_api(
    x_api_version: str = Header(
        "1.0",
        regex=r"^\d+\.\d+$",
        description="API version"
    )
):
    """
    API versioning via headers.
    
    Alternative to URL-based versioning (/api/v1/...).
    Allows same URL to serve different versions.
    
    Test with curl:
    curl http://localhost:8000/api/versioned \
      -H "X-API-Version: 2.0"
    """
    if x_api_version == "1.0":
        return {
            "version": "1.0",
            "message": "Using legacy API",
            "data": {"format": "old"}
        }
    elif x_api_version == "2.0":
        return {
            "version": "2.0",
            "message": "Using new API",
            "data": {"format": "new", "features": ["enhanced"]}
        }
    else:
        return {
            "error": f"Unsupported API version: {x_api_version}",
            "supported_versions": ["1.0", "2.0"]
        }


@app.post("/api/idempotent")
async def idempotent_request(
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=10,
        description="Unique key for idempotent requests"
    )
):
    """
    Idempotency pattern using headers.
    
    Used in payment APIs to prevent duplicate charges.
    Same idempotency key = same operation result.
    
    Real-world use case:
    - Client retries failed request
    - Server sees same idempotency key
    - Server returns cached result instead of re-processing
    
    Test with curl:
    curl -X POST http://localhost:8000/api/idempotent \
      -H "Idempotency-Key: unique_key_12345"
    """
    # In real app: check if this key was used before
    # If yes, return cached result
    # If no, process and cache result
    
    return {
        "idempotency_key": idempotency_key,
        "message": "Request processed",
        "note": "Same key will return same result"
    }


# =============================================================================
# 9. CONTENT NEGOTIATION
# =============================================================================

@app.get("/data/flexible")
async def content_negotiation(
    accept: str = Header("application/json")
):
    """
    Content negotiation based on Accept header.
    
    Client specifies preferred response format via Accept header.
    Server responds with that format if supported.
    
    Test with curl:
    # JSON
    curl http://localhost:8000/data/flexible \
      -H "Accept: application/json"
    
    # XML (not actually implemented here)
    curl http://localhost:8000/data/flexible \
      -H "Accept: application/xml"
    """
    data = {"id": 1, "name": "Example", "value": 42}
    
    if "application/json" in accept:
        return data
    elif "application/xml" in accept:
        return {
            "message": "XML format requested but not implemented",
            "data": data
        }
    else:
        return {
            "error": "Unsupported media type",
            "requested": accept,
            "supported": ["application/json", "application/xml"]
        }


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing Headers:

1. Using FastAPI Docs:
   - Go to http://localhost:8000/docs
   - Headers appear in the request parameters section
   - Fill in header values
   - Click "Execute"

2. Using curl:
   curl http://localhost:8000/endpoint \
     -H "Header-Name: value" \
     -H "Another-Header: another_value"

3. Using httpie:
   http GET localhost:8000/endpoint \
     Header-Name:value \
     Another-Header:another_value

4. Using Python requests:
   response = requests.get(
       "http://localhost:8000/endpoint",
       headers={
           "Header-Name": "value",
           "Another-Header": "another_value"
       }
   )

5. Using browser DevTools:
   - Open Network tab
   - Make request
   - Inspect request headers
   - See how browser adds headers automatically

Common Header Names:
- Authorization: Bearer token
- X-API-Key: API key
- X-Request-ID: Request tracking
- X-Correlation-ID: Distributed tracing
- User-Agent: Client identification
- Accept: Content type preference
- Accept-Language: Language preference
- Content-Type: Body format
- Idempotency-Key: Idempotent requests

Mental Model:
- Header(...) extracts request headers
- _ in Python ↔ - in HTTP (automatic)
- alias gives exact header control
- Validation runs before endpoint logic
- Repeated headers map to lists
- Headers are for metadata, not data
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
