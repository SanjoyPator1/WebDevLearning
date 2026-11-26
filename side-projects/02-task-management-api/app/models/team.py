"""
Team model for team management and collaboration

This model provides:
- Team information and management
- Member relationships
- Project associations
- Team permissions and roles
"""

from typing import List, Optional
from sqlalchemy import Column, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

class Team(BaseModel):
    """
    Team model for managing groups of users and projects
    
    Teams contain projects and have members with different roles.
    They provide collaboration structure and permission boundaries.
    
    Relationships:
        - creator: User who created this team
        - projects: Projects owned by this team
        - members: Team memberships with roles
    """
    
    # Team information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Team name or title"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Team description and purpose"
    )
    
    # Team settings
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether team is active"
    )
    
    # Foreign key relationships
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who created this team"
    )
    
    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_teams",
        lazy="select"
    )
    
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="team",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    members: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    @property
    def member_count(self) -> int:
        """
        Get total number of active team members
        
        Returns:
            Number of active team memberships
        """
        return len([member for member in self.members if member.is_active])
    
    @property
    def project_count(self) -> int:
        """
        Get total number of active projects
        
        Returns:
            Number of active projects in this team
        """
        return len([project for project in self.projects if project.is_active])
    
    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', members={self.member_count})>"