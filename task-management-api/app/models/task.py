"""
Task model for task management functionality

This model provides:
- Task information (title, description, priority)
- Due date and completion tracking
- Relationships to users, projects, attachments, and comments
- Priority levels and status management
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.models.base import BaseModel

class TaskPriority(enum.Enum):
    """
    Task priority levels
    
    Values:
        LOW: Low priority tasks
        MEDIUM: Medium priority tasks (default)
        HIGH: High priority tasks
    """
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"

class Task(BaseModel):
    """
    Task model for managing individual tasks
    
    Tasks belong to projects and can be assigned to users.
    They support file attachments, comments, and priority levels.
    
    Relationships:
        - project: Project containing this task
        - creator: User who created this task
        - assignee: User assigned to this task
        - attachments: Files attached to this task
        - comments: Discussion comments on this task
    """
    
    # Basic task information
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Task title or summary"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed task description"
    )
    
    # Task metadata
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority),
        default=TaskPriority.MEDIUM,
        nullable=False,
        index=True,
        comment="Task priority level"
    )
    
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When this task is due"
    )
    
    completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether task is completed"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When task was marked as completed"
    )
    
    # Foreign key relationships
    project_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Project containing this task"
    )
    
    assigned_to: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User assigned to this task"
    )
    
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who created this task"
    )
    
    # Relationships
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="tasks",
        lazy="select"
    )
    
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_tasks",
        lazy="select"
    )
    
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to],
        back_populates="assigned_tasks",
        lazy="select"
    )
    
    attachments: Mapped[List["TaskAttachment"]] = relationship(
        "TaskAttachment",
        back_populates="task",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    comments: Mapped[List["TaskComment"]] = relationship(
        "TaskComment",
        back_populates="task",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    def mark_completed(self, completed_by: Optional[UUID] = None) -> None:
        """
        Mark task as completed with timestamp
        
        Args:
            completed_by: Optional user ID who completed the task
        """
        self.completed = True
        self.completed_at = datetime.utcnow()
        if completed_by:
            self.created_by = completed_by  # Track who completed it
    
    def mark_incomplete(self) -> None:
        """
        Mark task as incomplete and clear completion timestamp
        """
        self.completed = False
        self.completed_at = None
    
    @property
    def is_overdue(self) -> bool:
        """
        Check if task is overdue
        
        Returns:
            True if task has due date in the past and is not completed
        """
        if not self.due_date or self.completed:
            return False
        return datetime.utcnow() > self.due_date.replace(tzinfo=None)
    
    @property
    def days_until_due(self) -> Optional[int]:
        """
        Calculate days remaining until due date
        
        Returns:
            Number of days (negative if overdue, None if no due date)
        """
        if not self.due_date:
            return None
        
        delta = self.due_date.replace(tzinfo=None) - datetime.utcnow()
        return delta.days
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', priority={self.priority.value})>"