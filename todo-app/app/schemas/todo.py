"""
Todo-related Pydantic schemas.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.todo import TodoPriority, TodoStatus

class TodoBase(BaseModel):
    """Base todo schema with common fields."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    completed: bool = False
    priority: TodoPriority = TodoPriority.MEDIUM
    status: TodoStatus = TodoStatus.PENDING
    category: str | None = Field(None, max_length=50)
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime | None) -> datetime | None:
        """Validate that due date is not in the past."""
        if v is not None and v < datetime.now(v.tzinfo):
            raise ValueError("Due date cannot be in the past")
        return v
    
class TodoCreate(TodoBase):
    """Schema for creating a new todo."""

    pass

class TodoUpdate(BaseModel):
    """Schema for updating a todo (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    completed: bool | None = None
    priority: TodoPriority | None = None
    status: TodoStatus | None = None
    category: str | None = Field(None, max_length=50)
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime | None) -> datetime | None:
        """Validate that due date is not in the past."""
        if v is not None and v < datetime.now(v.tzinfo):
            raise ValueError("Due date cannot be in the past")
        return v
    
class TodoInDB(TodoBase):
    """Schema for todo as stored in database."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

class Todo(TodoInDB):
    """Public todo schema."""

    pass

class TodoList(BaseModel):
    """Schema for paginated todo list."""

    items: list[Todo]
    total: int
    page: int
    page_size: int
    pages: int


class TodoFilter(BaseModel):
    """Schema for filtering todos."""

    completed: bool | None = None
    priority: TodoPriority | None = None
    status: TodoStatus | None = None
    category: str | None = None
    search: str | None = Field(None, max_length=200)
