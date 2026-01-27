from fastapi import FastAPI
from pydantic import BaseModel, EmailStr

app = FastAPI()

# --- 1. The Data (Simulated DB) ---
# Notice "password_hash" is strictly internal/sensitive
fake_db = {
    1: {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "password_hash": "secret_hash_123",  # ⚠️ SENSITIVE
        "is_active": True
    }
}

# --- 2. The Pydantic Models ---

# Base model with shared fields
class UserBase(BaseModel):
    username: str
    email: EmailStr

# The Response Model (Public facing)
# We strictly define what the user is allowed to see.
class UserResponse(UserBase):
    id: int
    is_active: bool
    # password_hash is MISSING here intentionally

# --- 3. The Endpoints ---

@app.get("/users/{user_id}/unsafe")
async def get_user_unsafe(user_id: int):
    """
    ⚠️ BAD PRACTICE: Returns the database dict directly.
    Leaks 'password_hash' to the client!
    """
    return fake_db.get(user_id)

@app.get("/users/{user_id}/safe", response_model=UserResponse)
async def get_user_safe(user_id: int):
    """
    ✅ GOOD PRACTICE: Uses response_model.
    FastAPI filters out 'password_hash' automatically.
    """
    return fake_db.get(user_id)