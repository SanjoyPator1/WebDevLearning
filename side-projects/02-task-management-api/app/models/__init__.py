"""
Database models package

This module imports and exposes all database models for the application.
It also provides the Base class for SQLAlchemy table creation.

Models:
    - User: User authentication and profile management
    - Team: Team management and collaboration
    - Project: Project organization and management
    - Task: Task tracking and management
    - TeamMember: User-team membership with roles
    - TaskAttachment: File attachments for tasks
    - TaskComment: Discussion comments on tasks

Usage:
    from app.models import User, Task, Project
    from app.models import Base  # For creating all tables
"""

# Import base classes
from app.models.base import Base, BaseModel

# Import all models
from app.models.user import User
from app.models.team import Team
from app.models.project import Project
from app.models.task import Task, TaskPriority
from app.models.team_member import TeamMember, TeamRole
from app.models.task_attachment import TaskAttachment
from app.models.task_comment import TaskComment

# Export all models for easy importing
__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    
    # Core models
    "User",
    "Team", 
    "Project",
    "Task",
    "TeamMember",
    "TaskAttachment",
    "TaskComment",
    
    # Enums
    "TaskPriority",
    "TeamRole",
]

"""
Model Relationship Summary:

USER (1) --> (M) TASK (created_by)
USER (1) --> (M) TASK (assigned_to)
USER (1) --> (M) PROJECT (created_by)
USER (1) --> (M) TEAM (created_by)
USER (1) --> (M) TEAM_MEMBER (user_id)
USER (1) --> (M) TASK_COMMENT (user_id)

TEAM (1) --> (M) PROJECT (team_id)
TEAM (1) --> (M) TEAM_MEMBER (team_id)

PROJECT (1) --> (M) TASK (project_id)

TASK (1) --> (M) TASK_ATTACHMENT (task_id)
TASK (1) --> (M) TASK_COMMENT (task_id)

Foreign Key Constraints:
- All models use UUID primary keys for better security
- Soft deletes implemented via deleted_at timestamp
- Cascade deletes configured for parent-child relationships
- SET NULL configured for optional references
"""