"""
Base model class with common fields and functionality

This module provides:
- Common audit fields (id, created_at, updated_at, etc.)
- Soft delete functionality
- UUID primary keys
- Base class for all database models
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models
    
    Provides consistent table naming and common functionality
    across all models in the application.
    """
    
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate table name from class name
        
        Converts CamelCase class names to snake_case table names:
        - User -> users
        - TaskAttachment -> task_attachments
        - TeamMember -> team_members
        """
        import re
        # Convert CamelCase to snake_case and pluralize
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        
        # Simple pluralization (add 's' if not already ending in 's')
        if not name.endswith('s'):
            name += 's'
            
        return name

class BaseModel(Base):
    """
    Abstract base model with common audit fields
    
    All application models should inherit from this class to get:
    - UUID primary key
    - Creation and update timestamps
    - Soft delete functionality
    - User audit trails
    
    Fields:
        id: UUID primary key
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
        created_by: UUID of user who created the record
        deleted_at: Timestamp when record was soft-deleted (NULL if active)
    """
    
    __abstract__ = True  # This class won't create a table
    
    # Primary key using UUID for better security and distributed systems
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Unique identifier for this record"
    )
    
    # Audit timestamps with automatic management
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When this record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
        comment="When this record was last updated"
    )
    
    # User audit trail (will be foreign keys in actual models)
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,  # Allow system-created records
        index=True,
        comment="User who created this record"
    )
    
    # Soft delete support
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When this record was deleted (NULL if active)"
    )
    
    def soft_delete(self) -> None:
        """
        Mark this record as deleted without removing from database
        
        Sets deleted_at timestamp to current time. The record remains
        in the database but is filtered out of normal queries.
        """
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """
        Restore a soft-deleted record
        
        Sets deleted_at back to NULL, making the record active again.
        """
        self.deleted_at = None
    
    @property
    def is_deleted(self) -> bool:
        """
        Check if this record is soft-deleted
        
        Returns:
            True if record is deleted (deleted_at is not NULL)
        """
        return self.deleted_at is not None
    
    @property
    def is_active(self) -> bool:
        """
        Check if this record is active (not deleted)
        
        Returns:
            True if record is active (deleted_at is NULL)
        """
        return self.deleted_at is None
    
    def __repr__(self) -> str:
        """
        String representation of the model instance
        
        Returns:
            String showing class name and primary key
        """
        return f"<{self.__class__.__name__}(id={self.id})>"