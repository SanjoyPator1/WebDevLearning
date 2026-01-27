from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional, List
from datetime import datetime

app = FastAPI()

# --- Database ---
users_db = [
    {
        "id": 1, 
        "username": "admin", 
        "email": "admin@test.com", 
        "role": "admin",
        "joined_at": datetime(2023, 1, 1),
        "profile_views": 1050
    },
    {
        "id": 2, 
        "username": "user", 
        "email": "user@test.com", 
        "role": "user",
        "joined_at": datetime(2023, 5, 20),
        "profile_views": 42
    }
]

# --- Response Models ---

class UserProfile(BaseModel):
    id: int
    username: str
    # Email excluded for privacy
    role: str
    joined_at: datetime
    
    # Computed fields for frontend convenience
    @computed_field
    @property
    def is_veteran(self) -> bool:
        # User is a "veteran" if joined before 2023-02-01
        return self.joined_at < datetime(2023, 2, 1)

    @computed_field
    @property
    def display_name(self) -> str:
        return f"{self.username.upper()} ({self.role})"

# --- Endpoints ---

@app.get("/profiles", response_model=List[UserProfile])
async def list_profiles():
    return users_db

@app.get("/profiles/{user_id}", response_model=UserProfile)
async def get_profile(user_id: int):
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@app.get("/profiles/{user_id}/audit")
async def audit_profile(user_id: int):
    """
    Admin only endpoint - returns raw data (unsafe for public)
    """
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(404, "User not found")
    return user  # Returns everything including email and views