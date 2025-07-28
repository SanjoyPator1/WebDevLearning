"""
User model for authentication and user management

This model provides:
- User authentication fields
- Profile information
- Email verification
- Password hashing integration
- Relationships to tasks, projects, and teams
"""

from typing import List, Optional
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

class User(BaseModel):
    """
    User model for authentication and profile management
    
    Stores user account information, authentication credentials,
    and profile data. Links to tasks, projects, and team memberships.
    
    Relationships:
        - created_tasks: Tasks created by this user
        - assigned_tasks: Tasks assigned to this user  
        - created_projects: Projects created by this user
        - created_teams: Teams created by this user
        - team_memberships: Teams this user belongs to
        - task_comments: Comments written by this user
    """
    
    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User's unique email address for login"
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )
    
    # Profile information
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's display name"
    )
    
    # Account status
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user has verified their email"
    )

    role: Mapped[str] = mapped_column(
        String(32),
        default="user",
        nullable=False,
        comment="Role of the user (admin, user, guest, etc.)"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether user account is active"
    )
    
    # Optional profile fields
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User's biography or description"
    )
    
    # Relationships - Tasks
    created_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.created_by",
        back_populates="creator",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    assigned_tasks: Mapped[List["Task"]] = relationship(
        "Task", 
        foreign_keys="Task.assigned_to",
        back_populates="assignee",
        lazy="select"
    )
    
    # Relationships - Projects  
    created_projects: Mapped[List["Project"]] = relationship(
        "Project",
        foreign_keys="Project.created_by", 
        back_populates="creator",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    # Relationships - Teams
    created_teams: Mapped[List["Team"]] = relationship(
        "Team",
        foreign_keys="Team.created_by",
        back_populates="creator", 
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    team_memberships: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="user",
        lazy="select"
    )
    
    # Relationship - Comments
    task_comments: Mapped[List["TaskComment"]] = relationship(
        "TaskComment",
        back_populates="user",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.full_name}')>"
    
    @property
    def display_name(self) -> str:
        """
        Get user's display name for UI
        
        Returns full name if available, otherwise email prefix
        """
        return self.full_name or self.email.split('@')[0]