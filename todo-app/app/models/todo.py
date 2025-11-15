"""
Todo database model.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

class TodoPriority(str, Enum):
    """Todo priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TodoStatus(str, Enum):
    """Todo status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Todo(Base, TimestampMixin):
    """
    Todo model - represents the 'todos' table in database.
    Each todo belongs to one user (owner).
    """

    __tablename__ = "todos"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Todo content
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status and priority
    status: Mapped[TodoStatus] = mapped_column(
        default=TodoStatus.PENDING, nullable=False, index=True
    )
    priority: Mapped[TodoPriority] = mapped_column(
        default=TodoPriority.MEDIUM, nullable=False, index=True
    )

    # Optional fields
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    completed: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Foreign key to user table
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), 
        nullable=False, 
        index=True
    )

    # Relationships back to user
    owner: Mapped["User"] = relationship("User", back_populates="todos")

    def __repr__(self) -> str:
        return f"<Todo(id={self.id}, title={self.title}, status={self.status})>"
