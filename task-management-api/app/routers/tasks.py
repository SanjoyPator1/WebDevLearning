from fastapi import APIRouter, HTTPException, Query, Path, Header, File, UploadFile, Form, Depends, BackgroundTasks
from datetime import datetime, date
from typing import Optional, List
import os
import uuid

# Import schemas
from app.schemas.task import Task, TaskResponse, TaskUpdate, TaskList, TaskPriority, TaskSortBy, TaskSortOrder

from app.dependencies.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# OAuth2 Authentication imports
from app.models.user import User
from app.dependencies.oauth2 import get_current_user, get_optional_user
from app.dependencies.permissions import require_user_or_admin, require_admin, RoleChecker

# Other dependencies
from app.dependencies.pagination import get_pagination_params, PaginationParams
from app.dependencies.cache import get_task_statistics, invalidate_task_cache

from app.services.file_service import file_service

# Create router instance
router = APIRouter(prefix="/tasks", tags=["tasks"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create specific permission checkers for tasks
require_task_access = RoleChecker(["user", "admin"])
require_file_upload = RoleChecker(["user", "admin"])

@router.get("/", response_model=TaskList)
async def get_tasks(
    # Pagination dependency
    pagination: PaginationParams = Depends(get_pagination_params),
    # Database dependency
    db: AsyncSession = Depends(get_db),
    # Optional OAuth2 authentication
    current_user: Optional[User] = Depends(get_optional_user),
    # Filtering parameters
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    due_before: Optional[date] = Query(None, description="Filter tasks due before this date"),
    due_after: Optional[date] = Query(None, description="Filter tasks due after this date"),
    # Sorting parameters
    sort_by: TaskSortBy = Query(TaskSortBy.CREATED_AT, description="Field to sort by"),
    sort_order: TaskSortOrder = Query(TaskSortOrder.DESC, description="Sort order"),
    # Header parameters for versioning
    api_version: Optional[str] = Header(None, alias="X-API-Version", description="API Version"),
    user_agent: Optional[str] = Header(None, alias="User-Agent", description="Client information")
):
    """
    Get all tasks with optional OAuth2 authentication
    
    OAuth2 Scopes: Works without authentication, enhanced with user context when authenticated
    - Unauthenticated: See all public tasks
    - User role: See only own tasks
    - Admin role: See all tasks
    """
    
    # API version validation
    if api_version and api_version not in ["v1", "v1.0"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported API version: {api_version}. Supported versions: v1, v1.0"
        )
    
    if user_agent:
        print(f"Request from: {user_agent}")

    # TODO: Replace with real database query logic
    # Example: result = await db.execute(select(TaskModel))
    # tasks = result.scalars().all()
    # Apply filtering, sorting, and pagination as needed
    return TaskList(tasks=[], total=0)

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: Task,
    db: AsyncSession = Depends(get_db),
    # Requires OAuth2 Bearer token with user or admin role
    current_user: User = Depends(require_task_access)
):
    """
    Create a new task (OAuth2 authentication required)
    
    Required OAuth2 Scopes: user or admin role
    Authorization: Bearer <access_token>
    """

    now = datetime.now()
    new_task_dict = {
        **task_data.model_dump(),
        "created_at": now,
        "updated_at": now,
        "attachments": [],
        "created_by": str(current_user.id),
        "owner_id": str(current_user.id)  # Set ownership for access control
    }
    
    # TODO: Implement real DB insert logic
    return TaskResponse(**new_task_dict)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    db: AsyncSession = Depends(get_db),
    # Optional OAuth2 authentication
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get a specific task by ID (OAuth2 optional authentication)
    
    OAuth2 Scopes: Works without authentication, access control applies when authenticated
    """
    
    # TODO: Implement real DB fetch logic
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_data: TaskUpdate,
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    db: AsyncSession = Depends(get_db),
    # Requires OAuth2 Bearer token
    current_user: User = Depends(require_task_access)
):
    """
    Update a task (OAuth2 authentication + ownership check)
    
    Required OAuth2 Scopes: user or admin role
    Access Control: Users can only update their own tasks, admins can update any task
    """
    
    # TODO: Implement real DB update logic
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@router.delete("/{task_id}")
async def delete_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    db: AsyncSession = Depends(get_db),
    # Admin-only access
    current_user: User = Depends(require_admin)
):
    """
    Delete a task (OAuth2 admin authentication required)
    
    Required OAuth2 Scopes: admin role only
    """
    
    # TODO: Implement real DB delete logic
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@router.get("/statistics")
async def get_task_statistics_endpoint(
    stats = Depends(get_task_statistics),
    current_user: User = Depends(require_task_access)
):
    """
    Get task statistics (OAuth2 authentication required)
    
    Required OAuth2 Scopes: user or admin role
    """
    print(f"Statistics accessed by user {current_user.username}")
    return stats

@router.post("/{task_id}/attachments")
async def upload_task_attachment(
    background_tasks: BackgroundTasks, 
    task_id: int = Path(..., gt=0, description="Task ID"),
    file: UploadFile = File(..., description="File to attach to the task"),
    description: Optional[str] = Form(None, description="Optional description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_file_upload),
):
    """
    Upload file attachment (OAuth2 authentication + ownership check) with background processing
    
    Required OAuth2 Scopes: user or admin role
    Access Control: Users can only upload to their own tasks, admins can upload to any task

    File is saved immediately, then processed in background:
    - Images: Generate thumbnails and optimization
    - PDFs: Create previews and extract text
    - Text: Perform analysis and keyword extraction
    """
    
    # TODO: Implement real file upload and DB logic
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@router.get("/{task_id}/attachments")
async def get_task_attachments(
    task_id: int = Path(..., gt=0, description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get all attachments for a task (OAuth2 optional authentication)"""
    
    # TODO: Implement real DB logic for attachments
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

@router.delete("/{task_id}/attachments/{attachment_id}")
async def delete_task_attachment(
    task_id: int = Path(..., gt=0, description="Task ID"),
    attachment_id: int = Path(..., gt=0, description="Attachment ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_task_access)
):
    """Delete attachment (OAuth2 authentication + ownership check)"""
    
    # TODO: Implement real DB logic for deleting attachments
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")