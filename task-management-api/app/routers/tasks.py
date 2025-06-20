from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

# Create router instance
router = APIRouter(prefix="/tasks", tags=["tasks"])

# Simple in-memory storage (just a list of dictionaries)
tasks_db = []
task_id_counter = 1

# Router to get all the tasks
@router.get("/")
async def get_tasks():
    """Get all tasks"""
    return {
        "tasks" : tasks_db,
        "total" : len(tasks_db)
    }

# Router to create a task by task_data
@router.post("/")
async def create_task(task_data: dict):
    """Create a new task"""
    global task_id_counter

    # Create simple task with basic fields
    new_task = {
        "id": task_id_counter,
        "title": task_data.get("title", ""),
        "description": task_data.get("description", ""),
        "completed": task_data.get("completed", False)
    }

    tasks_db.append(new_task)
    task_id_counter += 1

    return {
        "message": "Task created successfully",
        "task": new_task
    }

# Router to get a task by task_id
@router.get("/{task_id}")
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
    
    return {"task" : task}

# Router to update a task by task_id and task_data
@router.put("/{task_id}")
async def update_task(task_id: int, task_data: dict):
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
    if "title" in task_data:
        task["title"] = task_data["title"]
    if "description" in task_data:
        task["description"] = task_data["description"]
    if "completed" in task_data:
        task["completed"] = task_data["completed"]

    tasks_db[task_index] = task

    return {
        "message" : "Task updated successfully",
        "task" : task
    }

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
        "deleted_task" : deleted_task
    }
