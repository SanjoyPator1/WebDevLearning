from typing import List
from enum import Enum
from fastapi import FastAPI, Depends, Security, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from pydantic import BaseModel

app = FastAPI()

# --- 1. API Key Security ---
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != "my_secret_key":
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

@app.get("/secure-data")
async def get_secure_data(key: str = Security(verify_api_key)):
    return {"data": "This is protected by API Key", "key_used": key}


# --- 2. RBAC (Role Based Access Control) ---
class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"

class User(BaseModel):
    username: str
    roles: List[Role]

# Mock Auth function
def get_current_user(token: str = Header(...)):
    # In real life, decode JWT here
    if token == "alice_token":
        return User(username="alice", roles=[Role.USER])
    if token == "bob_token":
        return User(username="bob", roles=[Role.ADMIN])
    raise HTTPException(status_code=401, detail="Invalid Token")

# Dependency Factory
def require_role(required_role: Role):
    def role_checker(user: User = Depends(get_current_user)):
        if required_role not in user.roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Operation requires {required_role.value} role"
            )
        return user
    return role_checker

@app.get("/admin-only")
async def admin_route(user: User = Depends(require_role(Role.ADMIN))):
    return {"message": "Hello Admin", "user": user}

@app.get("/user-area")
async def user_route(user: User = Depends(require_role(Role.USER))):
    return {"message": "Hello User", "user": user}