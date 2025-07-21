from fastapi import APIRouter, HTTPException, Query, Path, Body, Header,  File, UploadFile, Form
from datetime import datetime, date
from app.schemas.task import Task, TaskResponse, TaskUpdate, TaskList, TaskPriority, TaskSortBy, TaskSortOrder
from typing import Optional, List
import os
import uuid

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
    # Filtering parameters
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    due_before: Optional[date] = Query(None, description="Filter tasks due before this date"),
    due_after: Optional[date] = Query(None, description="Filter tasks due after this date"),
    
    # Pagination parameters
    limit: int = Query(10, ge=1, le=100, description="Number of tasks to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    
    # Sorting parameters
    sort_by: TaskSortBy = Query(TaskSortBy.CREATED_AT, description="Field to sort by"),
    sort_order: TaskSortOrder = Query(TaskSortOrder.DESC, description="Sort order"),
    
    # Header parameters for versioning
    api_version: Optional[str] = Header(None, alias="X-API-Version", description="API Version"),
    user_agent: Optional[str] = Header(None, alias="User-Agent", description="Client information")
):
    """
    Get all tasks with filtering, pagination, sorting, and header parameter support
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
    
    # Start with all tasks
    filtered_tasks = tasks_db.copy()
    
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
    
    # Apply pagination
    total_count = len(filtered_tasks)
    paginated_tasks = filtered_tasks[offset:offset + limit]
    
    # Convert to response models
    task_responses = [TaskResponse(**task) for task in paginated_tasks]
    
    return TaskList(
        tasks=task_responses,
        total=total_count
    )

# Router to create a task by task_data
@router.post("/", response_model=TaskResponse)
# task_data: Task = automatically validates incoming JSON against our Task model
async def create_task(task_data: Task):
    """Create a new task"""
    global task_id_counter

    # Create task dict with timestamps
    now = datetime.now()
    new_task = {
        "id": task_id_counter,
        "title": task_data.title,
        "description": task_data.description,
        "priority": task_data.priority,
        "due_date": task_data.due_date,
        "completed": task_data.completed,
        "created_at": now,
        "updated_at": now
    }

    tasks_db.append(new_task)
    task_id_counter+=1

    return TaskResponse(**new_task)

# Router to get a task by task_id
# response_model=TaskResponse ensures consistent response format
# Convert found task dict to TaskResponse object
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int = Path(...,gt=0, description="Task ID must be positive")
):
    """Get a specific task by ID with path parameter validation"""
    task = None
    for t in tasks_db:
        if t["id"] == task_id:
            task = t
            break

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )

    return TaskResponse(**task)

# Router to update a task by task_id and task_data
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive"),
    task_data: TaskUpdate = Body(...)
):
    """Update a task with validated path parameter"""
    # Find task logic (same as before)
    task = None
    task_index = None

    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            task = t
            task_index = i
            break

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )

    # Update logic (same as before)
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        task[field] = value

    task["updated_at"] = datetime.now()
    tasks_db[task_index] = task

    return TaskResponse(**task)

# Router to delete a task by task_id
@router.delete("/{task_id}")
async def delete_task(
    task_id: int = Path(..., gt=0, description="Task ID must be positive")
):
    """Delete a task with validated path parameter"""
    task_index = None
    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            task_index = i
            break

    if task_index is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )

    deleted_task = tasks_db.pop(task_index)

    return {
        "message": "Task deleted successfully",
        "deleted_task": TaskResponse(**deleted_task)
    }


@router.post("/{task_id}/attachments")
async def upload_task_attachment(
    task_id: int = Path(..., gt=0, description="Task ID"),
    file: UploadFile = File(..., description="File to attach to the task"),
    description: Optional[str] = Form(None, description="Optional description for the file")
):
    """
    Upload a file attachment to a task
    """

    # Check if task exists
    task = None
    task_index = None
    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            task = t
            task_index = i
            break

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )

    # Validate file type (simple example)
    allowed_types = ["image/jpeg", "image/png", "text/plain", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: {allowed_types}"
        )

    # Validate file size (5MB limit)
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:  # 5MB
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
        "uploaded_at": datetime.now()
    }

    task["attachments"].append(attachment)
    task["updated_at"] = datetime.now()
    tasks_db[task_index] = task

    return {
        "message": "File uploaded successfully",
        "attachment": attachment
    }

@router.get("/{task_id}/attachments")
async def get_task_attachments(
    task_id: int = Path(..., gt=0, description="Task ID")
):
    """
    Get all attachments for a task
    """

    # Find task
    task = None
    for t in tasks_db:
        if t["id"] == task_id:
            task = t
            break

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )

    attachments = task.get("attachments", [])

    return {
        "task_id": task_id,
        "attachments": attachments,
        "count": len(attachments)
    }

@router.delete("/{task_id}/attachments/{attachment_id}")
async def delete_task_attachment(
    task_id: int = Path(..., gt=0, description="Task ID"),
    attachment_id: int = Path(..., gt=0, description="Attachment ID")
):
    """
    Delete a specific attachment from a task
    """

    # Find task
    task = None
    task_index = None
    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            task = t
            task_index = i
            break

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
            detail=f"Attachment with ID {attachment_id} not found"
        )

    # Delete file from disk
    file_path = os.path.join(UPLOAD_DIR, attachment["stored_filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove attachment from task
    task["attachments"].pop(attachment_index)
    task["updated_at"] = datetime.now()
    tasks_db[task_index] = task

    return {
        "message": "Attachment deleted successfully",
        "deleted_attachment": attachment
    }