from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List
from datetime import datetime, date
import re

class Task(BaseModel):
    """
    Main Task model with validations
    """

    title: str = Field(..., min_length=1, max_length=100, description="Task title")
    description: Optional[str] = Field(None, max_length=500, description="Task description")
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[datetime] = None
    completed: bool = False

    # Custom validators using Pydantic V2 syntax
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Custom validation for title"""
        if not v or v.isspace():
            raise ValueError('Title cannot be empty or just whitespace')
        
        # Remove extra whitespace
        v = v.strip()

        # Check for forbidden characters
        if any(char in v for char in ['v', '>', '&', '"']):
            raise ValueError('Title contains forbidden characters')
        
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v:Optional[str]) -> Optional[str]:
        """Custom validation for description"""
        if v:
            v = v.strip()
            if len(v) == 0:
                return None  # Empty string becomes None
        return v
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure due date is not in the past"""
        if v and v < datetime.now():
            raise ValueError('Due date cannot be in the past')
        return v
    
    @model_validator(mode='after')
    def validate_completed_task(self):
        """Model validator to check business logic"""
        # If task is completed and has due date, check if it was completed on time
        if self.completed and self.due_date and self.due_date < datetime.now():
            # This is just a warning, not an error - task was completed late
            pass
        
        return self
    
    class Config:
        """Pydantic model configuration"""
        # Allow field population by name or alias
        allow_population_by_field_name = True

        # Validate assignment when fields are changed
        validate_assignment = True

        # Use enum values instead of enum objects in JSON
        use_enum_values = True

        # Example data for documentation
        schema_extra = {
            "example": {
                "title": "Complete FastAPI tutorial",
                "description": "Learn Pydantic models and validation",
                "priority": "high",
                "due_date": "2024-12-31T23:59:59",
                "completed": false
            }
        }

class TaskCreate(BaseModel):
    """Schema for creating a new task"""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[datetime] = None
    completed: bool = False

    # Inherit validators from Task model using V2 syntax
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError('Title cannot be empty or just whitespace')
        v = v.strip()
        if any(char in v for char in ['<', '>', '&', '"']):
            raise ValueError('Title contains forbidden characters')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip()
            if len(v) == 0:
                return None
        return v
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v < datetime.now():
            raise ValueError('Due date cannot be in the past')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "title": "New task",
                "description": "Task description here",
                "priority": "medium",
                "due_date": "2024-12-31T23:59:59"
            }
        }

class TaskUpdate(BaseModel):
    """Schema for updating an existing task - all fields optional"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: Optional[Literal["low", "medium", "high"]] = None
    due_date: Optional[datetime] = None
    completed: Optional[bool] = None
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or v.isspace():
                raise ValueError('Title cannot be empty or just whitespace')
            v = v.strip()
            if any(char in v for char in ['<', '>', '&', '"']):
                raise ValueError('Title contains forbidden characters')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Updated task title",
                "completed": true
            }
        }

class TaskResponse(BaseModel):
    """Schema for task responses with additional metadata"""
    id: int
    title: str
    description: Optional[str]
    priority: Literal["low", "medium", "high"]
    due_date: Optional[datetime]
    completed: bool
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.completed:
            return False
        return self.due_date < datetime.now()
    
    @property
    def days_until_due(self) -> Optional[int]:
        """Calculate days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.now()
        return delta.days
    
    class Config:
        from_attributes = True  # For compatibility with SQLAlchemy models later
        schema_extra = {
            "example": {
                "id": 1,
                "title": "Complete FastAPI tutorial",
                "description": "Learn Pydantic models and validation",
                "priority": "high",
                "due_date": "2024-12-31T23:59:59",
                "completed": false,
                "created_at": "2024-01-01T10:00:00",
                "updated_at": "2024-01-01T10:00:00"
            }
        }

class TaskList(BaseModel):
    """Schema for paginated task lists"""
    tasks: List[TaskResponse]
    total: int
    page: int = 1
    per_page: int = 10
    has_next: bool
    has_prev: bool

    class Config:
        schema_extra = {
            "example": {
                "tasks": [],
                "total": 25,
                "page": 1,
                "per_page": 10,
                "has_next": true,
                "has_prev": false
            }
        }

class TaskSummary(BaseModel):
    """Schema for task summary/statistics"""
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    high_priority_tasks: int
    completion_rate: float
    
    class Config:
        schema_extra = {
            "example": {
                "total_tasks": 10,
                "completed_tasks": 6,
                "pending_tasks": 4,
                "overdue_tasks": 1,
                "high_priority_tasks": 2,
                "completion_rate": 0.6
            }
        }

class TaskAdvanced(BaseModel):
    """Advanced Task model with extensive validation"""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[datetime] = None
    completed: bool = False
    tags: Optional[List[str]] = Field(default_factory=list, max_length=5)
    estimated_hours: Optional[float] = Field(None, gt=0, le=40)
    
    @field_validator('title', mode='before')
    @classmethod
    def title_must_be_string(cls, v):
        """Pre-validator to ensure title is string"""
        if not isinstance(v, str):
            raise ValueError('Title must be a string')
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> List[str]:
        """Validate tags list"""
        if v:
            # Remove duplicates while preserving order
            seen = set()
            unique_tags = []
            for tag in v:
                if isinstance(tag, str):
                    tag = tag.strip().lower()
                    if tag and tag not in seen:
                        seen.add(tag)
                        unique_tags.append(tag)
                else:
                    raise ValueError('All tags must be strings')
            
            # Check for forbidden tag names
            forbidden_tags = ['spam', 'test', 'delete']
            for tag in unique_tags:
                if tag in forbidden_tags:
                    raise ValueError(f'Tag "{tag}" is not allowed')
            
            return unique_tags
        return []
    
    @field_validator('estimated_hours')
    @classmethod
    def validate_estimated_hours(cls, v: Optional[float]) -> Optional[float]:
        """Validate estimated hours"""
        if v is not None:
            if v <= 0:
                raise ValueError('Estimated hours must be positive')
            if v > 40:
                raise ValueError('Estimated hours cannot exceed 40 per task')
            # Round to 2 decimal places
            return round(v, 2)
        return v
    
    @model_validator(mode='after')
    def validate_task_logic(self):
        """Complex business logic validation"""
        # High priority tasks should have due dates
        if self.priority == 'high' and not self.due_date:
            raise ValueError('High priority tasks must have a due date')
        
        # Tasks with long estimated hours should not have short deadlines
        if self.estimated_hours and self.estimated_hours > 8 and self.due_date:
            time_until_due = self.due_date - datetime.now()
            if time_until_due.days < 1:
                raise ValueError('Tasks requiring >8 hours need at least 1 day to complete')
        
        # Emergency tasks (title contains 'urgent') must be high priority
        if 'urgent' in self.title.lower() and self.priority != 'high':
            self.priority = 'high'  # Auto-correct priority
        
        return self
    
    class Config:
        validate_assignment = True
        anystr_strip_whitespace = True  # Automatically strip whitespace
        schema_extra = {
            "example": {
                "title": "Urgent: Fix production bug",
                "description": "Critical bug affecting users",
                "priority": "high",
                "due_date": "2024-01-02T09:00:00",
                "tags": ["bug", "production", "critical"],
                "estimated_hours": 4.5
            }
        }
