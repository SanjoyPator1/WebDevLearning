"""
Task attachment model for file management

This model provides:
- File metadata storage
- Task-file associations
- File size and type tracking
- Upload timeline information
"""

from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime

from app.models.base import BaseModel

class TaskAttachment(BaseModel):
    """
    Task attachment model for managing file uploads
    
    Stores metadata about files attached to tasks, including
    original filenames, storage paths, file types, and sizes.
    
    Relationships:
        - task: Task this attachment belongs to
    """
    
    # File metadata
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename as uploaded by user"
    )
    
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="UUID-based filename for storage"
    )
    
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="MIME type of the file"
    )
    
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of the file"
    )
    
    # Upload information
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When file was uploaded"
    )
    
    # Foreign key relationships
    task_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Task this attachment belongs to"
    )
    
    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="attachments",
        lazy="select"
    )
    
    @property
    def file_size_human(self) -> str:
        """
        Get human-readable file size
        
        Returns:
            File size formatted as "1.2 MB", "345 KB", etc.
        """
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_image(self) -> bool:
        """
        Check if attachment is an image file
        
        Returns:
            True if content type indicates an image
        """
        return self.content_type.startswith('image/')
    
    @property
    def is_document(self) -> bool:
        """
        Check if attachment is a document file
        
        Returns:
            True if content type indicates a document
        """
        document_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/markdown'
        ]
        return self.content_type in document_types
    
    def __repr__(self) -> str:
        return f"<TaskAttachment(id={self.id}, filename='{self.filename}', size={self.file_size_human})>"