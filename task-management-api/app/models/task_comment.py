"""
Task comment model for task discussions

This model provides:
- Comment content storage
- User-comment associations
- Comment timeline tracking
- Edit and delete functionality
"""

from typing import Optional
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime

from app.models.base import BaseModel

class TaskComment(BaseModel):
    """
    Task comment model for discussions and notes
    
    Stores comments and discussions related to tasks,
    enabling team collaboration and communication.
    
    Relationships:
        - task: Task this comment belongs to
        - user: User who wrote this comment
    """
    
    # Comment content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Comment text content"
    )
    
    # Edit tracking
    edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When comment was last edited (NULL if never edited)"
    )
    
    # Foreign key relationships
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Task this comment belongs to"
    )
    
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who wrote this comment"
    )
    
    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="comments",
        lazy="select"
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="task_comments",
        lazy="select"
    )
    
    @property
    def was_edited(self) -> bool:
        """
        Check if comment has been edited
        
        Returns:
            True if comment was edited after creation
        """
        return self.edited_at is not None
    
    def mark_edited(self) -> None:
        """
        Mark comment as edited with current timestamp
        """
        from datetime import datetime
        self.edited_at = datetime.utcnow()
    
    @property
    def content_preview(self) -> str:
        """
        Get truncated preview of comment content
        
        Returns:
            First 100 characters of content with ellipsis if longer
        """
        if len(self.content) <= 100:
            return self.content
        return self.content[:97] + "..."
    
    def __repr__(self) -> str:
        edited = " (edited)" if self.was_edited else ""
        return f"<TaskComment(id={self.id}, user={self.user_id}, preview='{self.content_preview}'{edited})>"