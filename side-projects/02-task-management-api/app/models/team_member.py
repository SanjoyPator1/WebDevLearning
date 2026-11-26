"""
Team membership model for managing user-team relationships

This model provides:
- User-team associations
- Role-based permissions
- Membership timeline tracking
- Active/inactive membership status
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean,Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from sqlalchemy.sql import func

from app.models.base import BaseModel

class TeamRole(enum.Enum):
    """
    Team member roles with different permission levels
    
    Values:
        OWNER: Full team management permissions
        ADMIN: Administrative permissions (cannot delete team)
        MEMBER: Basic team member permissions
    """
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class TeamMember(BaseModel):
    """
    Team membership model linking users to teams with roles
    
    Manages the many-to-many relationship between users and teams,
    including role-based permissions and membership timeline.
    
    Relationships:
        - team: Team this membership belongs to
        - user: User who is a member
    """
    
    # Foreign key relationships
    team_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Team this membership belongs to"
    )
    
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who is a member"
    )
    
    # Membership details
    role: Mapped[TeamRole] = mapped_column(
        Enum(TeamRole),
        default=TeamRole.MEMBER,
        nullable=False,
        index=True,
        comment="Member's role in the team"
    )
    
    # Membership timeline
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When user joined the team"
    )
    
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user left the team (NULL if active)"
    )
    
    # Relationships
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="members",
        lazy="select"
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="team_memberships",
        lazy="select"
    )
    
    @property
    def is_active(self) -> bool:
        """
        Check if membership is currently active
        
        Returns:
            True if user is currently a team member
        """
        return self.left_at is None
    
    def leave_team(self) -> None:
        """
        Mark member as having left the team
        
        Sets left_at timestamp to current time
        """
        self.left_at = datetime.utcnow()
    
    def rejoin_team(self) -> None:
        """
        Restore membership for a user who previously left
        
        Clears left_at timestamp
        """
        self.left_at = None
    
    @property
    def can_manage_team(self) -> bool:
        """
        Check if member can manage team settings
        
        Returns:
            True if member has OWNER or ADMIN role
        """
        return self.role in [TeamRole.OWNER, TeamRole.ADMIN]
    
    @property
    def can_delete_team(self) -> bool:
        """
        Check if member can delete the team
        
        Returns:
            True if member has OWNER role
        """
        return self.role == TeamRole.OWNER
    
    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<TeamMember(team={self.team_id}, user={self.user_id}, role={self.role.value}, {status})>"