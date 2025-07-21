from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.schemas.task import Task, TaskResponse, TaskUpdate, TaskList

# Create router instance
router = APIRouter(prefix="/tasks", tags=["tasks"])

# Simple in-memory storage (just a list of dictionaries)
tasks_db = []
task_id_counter = 1

# Router to get all the tasks
@router.get("/", response_model=TaskList)
async def get_tasks():
    """Get all tasks"""
    # Convert dict to TaskResponse objects
    task_responses = []
    for task_dict in tasks_db:
        task_responses.append(TaskResponse(**task_dict))

    return TaskList(
        tasks=task_responses,
        total=len(tasks_db)
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
async def get_task(task_id: int):
    """Get a specific task by ID"""
    # Find task by ID
    task = None
    for t in tasks_db:
        if t["id"] == task_id:
            task = t
            break
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(**task)

# Router to update a task by task_id and task_data
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_data: TaskUpdate):
    """Update a specific task by ID"""
    # Find task by ID
    task = None
    task_index = None

    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            task = t
            task_index = i
            break
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update task fields
    update_data = task_data.model_dump(exclude_unset=True)
    for field,value in update_data.items():
        task[field] = value

    # Update timestamp
    task["updated_at"] = datetime.now()
    tasks_db[task_index] = task

    return TaskResponse(**task)

# Router to delete a task by task_id
@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """Delete a speific task by ID"""
    # Find task by ID
    task_index = None
    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            task_index = i
            break
    
    if task_index is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    deleted_task = tasks_db.pop(task_index)

    return {
        "message" : "Task deleted successfully", 
        "deleted_task" : TaskResponse(**deleted_task)
    }
