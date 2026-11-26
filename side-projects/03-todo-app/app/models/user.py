"""
User database model.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    User model - represents the 'users' table in database.
    Inherits from Base (required) and TimestampMixin (adds timestamps).
    """

    __tablename__ = "users"

    # Primary key - auto-incrementing integer
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # User credentials
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # User status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship to todos (one user has many todos)
    todos: Mapped[list["Todo"]] = relationship(
        "Todo", 
        back_populates="owner",
        cascade="all, delete-orphan"    # Delete todos when user is deleted
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
