"""
04_path_operation_dependencies.py

Topics covered:
- Path operation dependencies (side effects only)
- Multiple path operation dependencies
- Combining parameter and path dependencies

Run: uvicorn 04_path_operation_dependencies:app --reload
"""

from fastapi import FastAPI, Depends, Header, HTTPException

app = FastAPI()


# ============================================================================
# BASIC PATH OPERATION DEPENDENCIES
# ============================================================================

def verify_token(x_token: str = Header(...)):
    """Verify authentication token - no return needed"""
    if x_token != "secret-token":
        raise HTTPException(401, "Invalid token")


def verify_key(x_key: str = Header(...)):
    """Verify API key - no return needed"""
    if x_key != "secret-key":
        raise HTTPException(401, "Invalid key")


@app.get(
    "/items",
    dependencies=[Depends(verify_token), Depends(verify_key)]
)
async def read_items():
    """
    Both dependencies run before handler.
    Handler doesn't use their return values.
    
    Test:
    curl -H "X-Token: secret-token" -H "X-Key: secret-key" \
         http://localhost:8000/items
    """
    return {"items": ["item1", "item2"]}


# ============================================================================
# MULTIPLE PATH OPERATION DEPENDENCIES
# ============================================================================

def log_request():
    """Log that a request was made"""
    print("Request received")


def check_rate_limit():
    """Simulate rate limit check"""
    print("Rate limit checked")


def verify_api_version(version: str = Header("1.0")):
    """Verify API version is supported"""
    supported_versions = ["1.0", "1.1"]
    if version not in supported_versions:
        raise HTTPException(400, f"Unsupported API version: {version}")


@app.get(
    "/resource",
    dependencies=[
        Depends(log_request),
        Depends(check_rate_limit),
        Depends(verify_api_version)
    ]
)
async def get_resource():
    """
    Three dependencies run in order before handler.
    All are side-effect only.
    
    Test:
    curl -H "version: 1.0" http://localhost:8000/resource
    """
    return {"data": "resource data"}


# ============================================================================
# COMBINING PARAMETER AND PATH DEPENDENCIES
# ============================================================================

def verify_token_return(x_token: str = Header(...)):
    """Parameter dependency - returns token for handler use"""
    if x_token != "secret-token":
        raise HTTPException(401, "Invalid token")
    return x_token


def log_access():
    """Path dependency - side effect only"""
    print("Access logged")


@app.get(
    "/items-combined",
    dependencies=[Depends(log_access)]  # Path dependency
)
async def read_items_combined(
    token: str = Depends(verify_token_return)  # Parameter dependency
):
    """
    Combines two types:
    1. Path dependency (log_access) - side effect only
    2. Parameter dependency (verify_token_return) - used in handler
    
    Test:
    curl -H "X-Token: secret-token" http://localhost:8000/items-combined
    """
    return {
        "items": ["item1", "item2"],
        "authenticated_with": token
    }


# ============================================================================
# PRACTICAL EXAMPLE: LOGGING AND METRICS
# ============================================================================

def log_request_details():
    """Log detailed request information"""
    print("Logging request details")


def track_metrics():
    """Track API metrics"""
    print("Tracking metrics")


def validate_content_type(content_type: str = Header("application/json")):
    """Validate content type"""
    if content_type != "application/json":
        raise HTTPException(415, "Unsupported media type")


@app.post(
    "/data",
    dependencies=[
        Depends(log_request_details),
        Depends(track_metrics),
        Depends(validate_content_type)
    ]
)
async def create_data():
    """
    Multiple pre-checks before processing.
    Handler doesn't need to handle logging or validation.
    
    Test:
    curl -X POST -H "Content-Type: application/json" \
         http://localhost:8000/data
    """
    return {"message": "Data created"}


# ============================================================================
# REAL-WORLD PATTERN: FEATURE FLAGS
# ============================================================================

FEATURE_FLAGS = {
    "new_feature": True,
    "beta_feature": False,
}


def require_feature(feature_name: str):
    """Dependency factory for feature flag checking"""
    def check_feature():
        if not FEATURE_FLAGS.get(feature_name, False):
            raise HTTPException(403, f"Feature '{feature_name}' is disabled")
    return check_feature


@app.get(
    "/new-endpoint",
    dependencies=[Depends(require_feature("new_feature"))]
)
async def new_endpoint():
    """
    Only accessible if new_feature flag is enabled.
    Clean way to control feature rollout.
    """
    return {"message": "New feature accessed"}


@app.get(
    "/beta-endpoint",
    dependencies=[Depends(require_feature("beta_feature"))]
)
async def beta_endpoint():
    """
    This endpoint is disabled (beta_feature = False).
    Will return 403.
    """
    return {"message": "Beta feature accessed"}


# ============================================================================
# ORGANIZATIONAL PATTERN: SHARED DEPENDENCIES
# ============================================================================

def auth_and_log():
    """Combined authentication and logging"""
    print("Authenticating and logging")


def check_quota():
    """Check user quota"""
    print("Checking quota")


common_deps = [
    Depends(auth_and_log),
    Depends(check_quota)
]


@app.get("/endpoint1", dependencies=common_deps)
async def endpoint1():
    """Endpoint using common dependencies"""
    return {"endpoint": 1}


@app.get("/endpoint2", dependencies=common_deps)
async def endpoint2():
    """Another endpoint using same common dependencies"""
    return {"endpoint": 2}


@app.get("/endpoint3", dependencies=common_deps)
async def endpoint3():
    """Third endpoint with same dependencies"""
    return {"endpoint": 3}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
