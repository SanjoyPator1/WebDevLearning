from fastapi import APIRouter, HTTPException, Query, Path, Body, Header,  File, UploadFile, Form, Depends
from datetime import datetime, date
from typing import Optional, List
import os
import uuid

# Import schemas
from app.schemas.task import Task, TaskResponse, TaskUpdate, TaskList, TaskPriority, TaskSortBy, TaskSortOrder

# Import all dependencies
from app.dependencies.database import get_database, DatabaseSession
from app.dependencies.auth import get_current_user, get_optional_user, CurrentUser
from app.dependencies.permissions import (
    require_user_or_admin, require_admin, check_file_upload_permission
)
from app.dependencies.pagination import get_pagination_params, PaginationParams
from app.dependencies.cache import get_task_statistics, invalidate_task_cache


# Create router instance
router = APIRouter(prefix="/tasks", tags=["tasks"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Simple in-memory storage (just a list of dictionaries)
tasks_db = []
task_id_counter = 1

# Router to get all the tasks
@router.get("/", response_model=TaskList)
async def get_tasks(
    # PAGINATION DEPENDENCY
    pagination: PaginationParams = Depends(get_pagination_params),

     # DATABASE DEPENDENCY
    db: DatabaseSession = Depends(get_database),

    # AUTH DEPENDENCY - Optional 
    current_user: Optional[CurrentUser] = Depends(get_optional_user),

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
    Get all tasks with filtering, pagination, sorting, header parameter support and dependency injection
    """
    
    # Check API version if provided
    if api_version and api_version not in ["v1", "v1.0"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported API version: {api_version}. Supported versions: v1, v1.0"
        )
    
    
    # Log user agent for analytics (in real app, you'd use proper logging)
    if user_agent:
        print(f"Request from: {user_agent}")

    # GET DATA USING DATABASE DEPENDENCY
    all_tasks = db.get_all_tasks()

    # Log current user if authenticated
    if current_user:
        print(f"Authenticated request from user: {current_user.username}")
    
    # Start with all tasks
    filtered_tasks = all_tasks.copy()
    
    # Apply filters
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
        # Custom priority sorting: high > medium > low
        priority_order = {"high": 3, "medium": 2, "low": 1}
        filtered_tasks.sort(
            key=lambda x: priority_order.get(x.get("priority", "medium"), 2), 
            reverse=reverse_order
        )
    elif sort_by == TaskSortBy.DUE_DATE:
        # Sort by due_date, putting None values at the end
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
    
    # APPLY PAGINATION USING DEPENDENCY
    paginated_result = pagination.paginate_list(filtered_tasks)
    
    # Convert to response models
    task_responses = [TaskResponse(**task) for task in paginated_result["items"]]
    
    return TaskList(
        tasks=task_responses,
        total=paginated_result["pagination"]["total"]
    )

# Router to create a task by task_data
@router.post("/", response_model=TaskResponse)
# task_data: Task = automatically validates incoming JSON against our Task model
async def create_task(
    task_data: Task,
    # dependencies
    db: DatabaseSession = Depends(get_database),
    current_user: CurrentUser = Depends(require_user_or_admin)  # Requires authentication
):
    """Create a new task (requires user or admin role)"""

    # Create task with user info and timestamps
    now = datetime.now()
    new_task_dict = {
        **task_data.model_dump(),
        "created_at": now,
        "updated_at": now,
        "attachments": [],  # Initialize empty attachments
        "created_by": current_user.id  # Track who created the task
    }
    
    # Use database dependency to create task
    created_task = db.create_task(new_task_dict)
    
    # Invalidate cache since we added a new task
    invalidate_task_cache()
    
    print(f"Task created by user {current_user.username} (ID: {current_user.id})")
    
    return TaskResponse(**created_task)

# Router to get a task by task_id
# response_model=TaskResponse ensures consistent response format
# Convert found task dict to TaskResponse object
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    #  DEPENDENCIES
    db: DatabaseSession = Depends(get_database),
    current_user: Optional[CurrentUser] = Depends(get_optional_user)  # Optional auth
):
    """Get a specific task by ID with optional authentication"""
    
    # Use database dependency
    task = db.get_task_by_id(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404, 
            detail=f"Task with ID {task_id} not found"
        )
    
    # Log if authenticated user is accessing
    if current_user:
        print(f"Task {task_id} accessed by user {current_user.username}")
    
    return TaskResponse(**task)

# Router to update a task by task_id and task_data
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_data: TaskUpdate,
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    # DEPENDENCIES
    db: DatabaseSession = Depends(get_database),
    current_user: CurrentUser = Depends(require_user_or_admin)  # Requires authentication
):
    """Update a task (requires user or admin role)"""
    
    # Check if task exists using database dependency
    existing_task = db.get_task_by_id(task_id)
    if not existing_task:
        raise HTTPException(
            status_code=404, 
            detail=f"Task with ID {task_id} not found"
        )
    
    # Prepare update data
    update_data = task_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now()
    update_data["updated_by"] = current_user.id  # Track who updated
    
    # Use database dependency to update
    updated_task = db.update_task(task_id, update_data)
    
    # Invalidate cache since we updated a task
    invalidate_task_cache()
    
    print(f"Task {task_id} updated by user {current_user.username}")
    
    return TaskResponse(**updated_task)

# Router to delete a task by task_id
@router.delete("/{task_id}")
async def delete_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    # DEPENDENCIES
    db: DatabaseSession = Depends(get_database),
    current_user: CurrentUser = Depends(require_admin)  # Only admins can delete
):
    """Delete a task (admin only)"""
    
    # Use database dependency to delete
    deleted_task = db.delete_task(task_id)
    
    if not deleted_task:
        raise HTTPException(
            status_code=404, 
            detail=f"Task with ID {task_id} not found"
        )
    
    # Invalidate cache since we deleted a task
    invalidate_task_cache()
    
    print(f"Task {task_id} deleted by admin {current_user.username}")
    
    return {
        "message": "Task deleted successfully",
        "deleted_task": TaskResponse(**deleted_task)
    }

@router.get("/statistics")
async def get_task_statistics_endpoint(
    # === CACHED DEPENDENCY (from Task 2.2) ===
    stats = Depends(get_task_statistics),
    current_user: CurrentUser = Depends(require_user_or_admin)
):
    """Get task statistics (cached for performance)"""
    print(f"Statistics accessed by user {current_user.username}")
    return stats

# task attachments routes
@router.post("/{task_id}/attachments")
async def upload_task_attachment(
    task_id: int = Path(..., gt=0, description="Task ID"),
    file: UploadFile = File(..., description="File to attach to the task"),
    description: Optional[str] = Form(None, description="Optional description for the file"),
    # DEPENDENCIES
    db: DatabaseSession = Depends(get_database),
    current_user: CurrentUser = Depends(check_file_upload_permission)  # Permission check
):
    """Upload a file attachment to a task (requires upload permission)"""
    
    # Check if task exists using database dependency
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "text/plain", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: {allowed_types}"
        )
    
    # Validate file size (5MB limit)
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size too large. Maximum size is 5MB"
        )
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
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
        "uploaded_by": current_user.id  # Track who uploaded
    }
    
    task["attachments"].append(attachment)
    
    # Update task using database dependency
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
    # DEPENDENCIES
    db: DatabaseSession = Depends(get_database),
    current_user: Optional[CurrentUser] = Depends(get_optional_user)  # Optional auth
):
    """Get all attachments for a task"""
    
    # Use database dependency
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
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
    # DEPENDENCIES
    db: DatabaseSession = Depends(get_database),
    current_user: CurrentUser = Depends(require_user_or_admin)  # Requires authentication
):
    """Delete a specific attachment from a task (requires user or admin role)"""
    
    # Find task using database dependency
    task = db.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
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
    else:
        print(f"Warning: File {attachment['stored_filename']} not found on disk")
    
    # Remove attachment from task
    task["attachments"].pop(attachment_index)
    
    # Update task using database dependency
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
