from fastapi import APIRouter, HTTPException, Query, Path, Header, File, UploadFile, Form, Depends
from datetime import datetime, date
from typing import Optional, List
import os
import uuid

# Import schemas
from app.schemas.task import Task, TaskResponse, TaskUpdate, TaskList, TaskPriority, TaskSortBy, TaskSortOrder

# Import database and storage
from app.dependencies.database import get_database, DatabaseSession
from app.database.storage import tasks_db, task_id_counter

# OAuth2 Authentication imports
from app.database.users import User
from app.dependencies.oauth2 import get_current_user, get_optional_user
from app.dependencies.permissions import require_user_or_admin, require_admin, RoleChecker

# Other dependencies
from app.dependencies.pagination import get_pagination_params, PaginationParams
from app.dependencies.cache import get_task_statistics, invalidate_task_cache

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
    db: DatabaseSession = Depends(get_database),
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

    # Get all tasks from database
    all_tasks = db.get_all_tasks()

    # Apply user-based filtering
    if current_user:
        print(f"Authenticated request from user: {current_user.username} (role: {current_user.role})")
        # Non-admin users only see their own tasks
        if current_user.role != "admin":
            all_tasks = [t for t in all_tasks if t.get("owner_id") == current_user.id or t.get("created_by") == current_user.id]
    
    # Apply query parameter filters
    filtered_tasks = all_tasks.copy()
    
    if priority is not None:
        filtered_tasks = [t for t in filtered_tasks if t.get("priority") == priority.value]
    
    if completed is not None:
        filtered_tasks = [t for t in filtered_tasks if t.get("completed") == completed]
    
    if due_before is not None:
        filtered_tasks = [
            t for t in filtered_tasks 
            if t.get("due_date") and t["due_date"].date() <= due_before
        ]
    
    if due_after is not None:
        filtered_tasks = [
            t for t in filtered_tasks 
            if t.get("due_date") and t["due_date"].date() >= due_after
        ]
    
    # Apply sorting
    reverse_order = (sort_order == TaskSortOrder.DESC)
    
    if sort_by == TaskSortBy.TITLE:
        filtered_tasks.sort(key=lambda x: x.get("title", "").lower(), reverse=reverse_order)
    elif sort_by == TaskSortBy.PRIORITY:
        priority_order = {"high": 3, "medium": 2, "low": 1}
        filtered_tasks.sort(
            key=lambda x: priority_order.get(x.get("priority", "medium"), 2), 
            reverse=reverse_order
        )
    elif sort_by == TaskSortBy.DUE_DATE:
        filtered_tasks.sort(
            key=lambda x: x.get("due_date") or datetime.max, 
            reverse=reverse_order
        )
    elif sort_by == TaskSortBy.CREATED_AT:
        filtered_tasks.sort(
            key=lambda x: x.get("created_at", datetime.min), 
            reverse=reverse_order
        )
    elif sort_by == TaskSortBy.UPDATED_AT:
        filtered_tasks.sort(
            key=lambda x: x.get("updated_at", datetime.min), 
            reverse=reverse_order
        )
    
    # Apply pagination
    paginated_result = pagination.paginate_list(filtered_tasks)
    
    # Convert to response models
    task_responses = [TaskResponse(**task) for task in paginated_result["items"]]
    
    return TaskList(
        tasks=task_responses,
        total=paginated_result["pagination"]["total"]
    )

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: Task,
    db: DatabaseSession = Depends(get_database),
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
        "created_by": current_user.id,
        "owner_id": current_user.id  # Set ownership for access control
    }
    
    created_task = db.create_task(new_task_dict)
    invalidate_task_cache()
    
    print(f"Task created by user {current_user.username} (ID: {current_user.id})")
    
    return TaskResponse(**created_task)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    db: DatabaseSession = Depends(get_database),
    # Optional OAuth2 authentication
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get a specific task by ID (OAuth2 optional authentication)
    
    OAuth2 Scopes: Works without authentication, access control applies when authenticated
    """
    
    task = db.get_task_by_id(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404, 
            detail=f"Task with ID {task_id} not found"
        )
    
    # Access control: non-admin users can only see their own tasks
    if current_user and current_user.role != "admin":
        task_owner_id = task.get("owner_id") or task.get("created_by")
        if current_user.id != task_owner_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own tasks unless you're an admin",
                headers={"WWW-Authenticate": "Bearer realm=\"Task Management API\", error=\"insufficient_scope\""}
            )
    
    if current_user:
        print(f"Task {task_id} accessed by user {current_user.username}")
    
    return TaskResponse(**task)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_data: TaskUpdate,
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    db: DatabaseSession = Depends(get_database),
    # Requires OAuth2 Bearer token
    current_user: User = Depends(require_task_access)
):
    """
    Update a task (OAuth2 authentication + ownership check)
    
    Required OAuth2 Scopes: user or admin role
    Access Control: Users can only update their own tasks, admins can update any task
    """
    
    existing_task = db.get_task_by_id(task_id)
    if not existing_task:
        raise HTTPException(
            status_code=404, 
            detail=f"Task with ID {task_id} not found"
        )
    
    # Ownership-based access control
    task_owner_id = existing_task.get("owner_id") or existing_task.get("created_by")
    if current_user.role != "admin" and current_user.id != task_owner_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only update your own tasks unless you're an admin",
            headers={"WWW-Authenticate": "Bearer realm=\"Task Management API\", error=\"insufficient_scope\""}
        )
    
    # Prepare update data
    update_data = task_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now()
    update_data["updated_by"] = current_user.id
    
    updated_task = db.update_task(task_id, update_data)
    invalidate_task_cache()
    
    print(f"Task {task_id} updated by user {current_user.username}")
    
    return TaskResponse(**updated_task)

@router.delete("/{task_id}")
async def delete_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    db: DatabaseSession = Depends(get_database),
    # Admin-only access
    current_user: User = Depends(require_admin)
):
    """
    Delete a task (OAuth2 admin authentication required)
    
    Required OAuth2 Scopes: admin role only
    """
    
    deleted_task = db.delete_task(task_id)
    
    if not deleted_task:
        raise HTTPException(
            status_code=404, 
            detail=f"Task with ID {task_id} not found"
        )
    
    invalidate_task_cache()
    print(f"Task {task_id} deleted by admin {current_user.username}")
    
    return {
        "message": "Task deleted successfully",
        "deleted_task": TaskResponse(**deleted_task)
    }

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
    task_id: int = Path(..., gt=0, description="Task ID"),
    file: UploadFile = File(..., description="File to attach to the task"),
    description: Optional[str] = Form(None, description="Optional description"),
    db: DatabaseSession = Depends(get_database),
    current_user: User = Depends(require_file_upload)
):
    """
    Upload file attachment (OAuth2 authentication + ownership check)
    
    Required OAuth2 Scopes: user or admin role
    Access Control: Users can only upload to their own tasks, admins can upload to any task
    """
    
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    # Ownership check
    task_owner_id = task.get("owner_id") or task.get("created_by")
    if current_user.role != "admin" and current_user.id != task_owner_id:
        raise HTTPException(
            status_code=403,
            detail="You can only upload files to your own tasks unless you're an admin",
            headers={"WWW-Authenticate": "Bearer realm=\"Task Management API\", error=\"insufficient_scope\""}
        )
    
    # File validation
    allowed_types = ["image/jpeg", "image/png", "text/plain", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: {allowed_types}"
        )
    
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File size too large. Maximum size is 5MB")
    
    # Save file
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Add attachment info to task
    if "attachments" not in task:
        task["attachments"] = []
    
    attachment = {
        "id": len(task["attachments"]) + 1,
        "filename": file.filename,
        "stored_filename": unique_filename,
        "content_type": file.content_type,
        "size": len(file_content),
        "description": description,
        "uploaded_at": datetime.now(),
        "uploaded_by": current_user.id
    }
    
    task["attachments"].append(attachment)
    
    update_data = {
        "attachments": task["attachments"],
        "updated_at": datetime.now()
    }
    db.update_task(task_id, update_data)
    
    print(f"File uploaded to task {task_id} by user {current_user.username}")
    
    return {
        "message": "File uploaded successfully",
        "attachment": attachment
    }

@router.get("/{task_id}/attachments")
async def get_task_attachments(
    task_id: int = Path(..., gt=0, description="Task ID"),
    db: DatabaseSession = Depends(get_database),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get all attachments for a task (OAuth2 optional authentication)"""
    
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    # Access control for attachments
    if current_user and current_user.role != "admin":
        task_owner_id = task.get("owner_id") or task.get("created_by")
        if current_user.id != task_owner_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view attachments for your own tasks unless you're an admin",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    attachments = task.get("attachments", [])
    
    if current_user:
        print(f"Attachments for task {task_id} accessed by user {current_user.username}")
    
    return {
        "task_id": task_id,
        "attachments": attachments,
        "count": len(attachments)
    }

@router.delete("/{task_id}/attachments/{attachment_id}")
async def delete_task_attachment(
    task_id: int = Path(..., gt=0, description="Task ID"),
    attachment_id: int = Path(..., gt=0, description="Attachment ID"),
    db: DatabaseSession = Depends(get_database),
    current_user: User = Depends(require_task_access)
):
    """Delete attachment (OAuth2 authentication + ownership check)"""
    
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    # Ownership check
    task_owner_id = task.get("owner_id") or task.get("created_by")
    if current_user.role != "admin" and current_user.id != task_owner_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete attachments from your own tasks unless you're an admin",
            headers={"WWW-Authenticate": "Bearer realm=\"Task Management API\", error=\"insufficient_scope\""}
        )
    
    # Find attachment
    attachments = task.get("attachments", [])
    attachment = None
    attachment_index = None
    
    for i, att in enumerate(attachments):
        if att["id"] == attachment_id:
            attachment = att
            attachment_index = i
            break
    
    if not attachment:
        raise HTTPException(
            status_code=404,
            detail=f"Attachment with ID {attachment_id} not found in task {task_id}"
        )
    
    # Delete file from disk
    file_path = os.path.join(UPLOAD_DIR, attachment["stored_filename"])
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"File {attachment['stored_filename']} deleted from disk")
    
    # Remove attachment from task
    task["attachments"].pop(attachment_index)
    
    update_data = {
        "attachments": task["attachments"],
        "updated_at": datetime.now(),
        "updated_by": current_user.id
    }
    db.update_task(task_id, update_data)
    
    print(f"Attachment {attachment_id} deleted from task {task_id} by user {current_user.username}")
    
    return {
        "message": "Attachment deleted successfully",
        "deleted_attachment": attachment,
        "task_id": task_id
    }