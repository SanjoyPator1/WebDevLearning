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

