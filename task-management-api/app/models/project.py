"""
Project model for organizing tasks into projects

This model provides:
- Project information and organization
- Team association
- Task container functionality
- Project ownership and permissions
"""

from typing import List, Optional
from sqlalchemy import Column, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

class Project(BaseModel):
    """
    Project model for organizing tasks and team collaboration
    
    Projects contain tasks and belong to teams. They provide
    organizational structure for task management and team workflows.
    
    Relationships:
        - team: Team that owns this project
        - creator: User who created this project
        - tasks: Tasks contained in this project
    """
    
    # Project information
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Project name or title"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Project description and goals"
    )
    
    # Project status and metadata
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether project is active"
    )
    
    # Foreign key relationships
    team_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Team that owns this project"
    )
    
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who created this project"
    )
    
    # Relationships
    team: Mapped[Optional["Team"]] = relationship(
        "Team",
        back_populates="projects",
        lazy="select"
    )
    
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_projects",
        lazy="select"
    )
    
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    @property
    def task_count(self) -> int:
        """
        Get total number of tasks in this project
        
        Returns:
            Number of active tasks (not soft-deleted)
        """
        return len([task for task in self.tasks if task.is_active])
    
    @property
    def completed_task_count(self) -> int:
        """
        Get number of completed tasks in this project
        
        Returns:
            Number of active, completed tasks
        """
        return len([
            task for task in self.tasks 
            if task.is_active and task.completed
        ])
    
    @property
    def completion_percentage(self) -> float:
        """
        Calculate project completion percentage
        
        Returns:
            Percentage of tasks completed (0.0 to 100.0)
        """
        total = self.task_count
        if total == 0:
            return 0.0
        
        completed = self.completed_task_count
        return (completed / total) * 100.0
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, title='{self.title}', tasks={self.task_count})>"