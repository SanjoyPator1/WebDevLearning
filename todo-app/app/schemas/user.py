"""
User-related Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserBase(BaseModel):
    """Base user schema with common fields"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str | None = Field(None, max_length=100)
    is_active: bool = True

class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    """Schema for updating user information"""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=50)
    full_name : str | None = Field(None, max_length=100)
    password : str | None = Field(None, min_length=8, max_length=100)
    is_active: bool | None = None

class UserInDB(UserBase):
    """Schema for user as stored in database"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

class User(UserInDB):
    """Public user schema (without sensitive data)"""

    pass

class UserLogin(BaseModel):
    """Schema for user login"""

    username: str
    password: str