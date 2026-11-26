"""
Todo management endpoints.
"""
from typing import Annotated
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, status, HTTPException

from app.config import settings
from app.schemas.todo import Todo, TodoList, TodoCreate, TodoUpdate
from app.models.todo import TodoPriority, TodoStatus

router = APIRouter()

dummy_todo_1 = {
    "id": 1,
    "owner_id": 101,
    "title": "Finish FastAPI project",
    "description": "Implement CRUD operations with SQLAlchemy and Alembic.",
    "completed": False,
    "priority": TodoPriority.HIGH,
    "status": TodoStatus.IN_PROGRESS,
    "category": "Development",
    "due_date": datetime.now() + timedelta(days=3),
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
}

dummy_todo = dummy_todo_1

dummy_todo_2 = {
    "id": 2,
    "owner_id": 101,
    "title": "Prepare project documentation",
    "description": "Write README, API docs, and usage examples.",
    "completed": False,
    "priority": TodoPriority.MEDIUM,
    "status": TodoStatus.PENDING,
    "category": "Documentation",
    "due_date": datetime.now() + timedelta(days=7),
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
}

dummy_todo_3 = {
    "id": 3,
    "owner_id": 101,
    "title": "Submit code review",
    "description": "Review teammate’s PR and leave feedback.",
    "completed": True,
    "priority": TodoPriority.LOW,
    "status": TodoStatus.COMPLETED,
    "category": "Collaboration",
    "due_date": datetime.now() + timedelta(days=1),
    "created_at": datetime.now() - timedelta(days=5),
    "updated_at": datetime.now() - timedelta(days=1),
}

# Dummy Todo List
dummy_todo_list = {
    "items": [dummy_todo_1, dummy_todo_2, dummy_todo_3],
    "total": 3,
    "page": 1,
    "page_size": 10,
    "pages": 1,
}


dummy_categories = ["Development", "Documentation", "Collaboration", "Personal", "Learning"]

@router.get("", response_model=TodoList)
async def get_todos(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=settings.MAX_PAGE_SIZE)
    ] = settings.DEFAULT_PAGE_SIZE,
    completed: bool | None = None,
    priority: str | None = None,
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
) -> TodoList:
    """
    Get all todos for current user with optional filtering and pagination.

    Args:
        current_user: Current authenticated user
        todo_service: Todo service instance
        page: Page number (1-indexed)
        page_size: Number of items per page
        completed: Filter by completion status
        priority: Filter by priority (low, medium, high, urgent)
        status: Filter by status (pending, in_progress, completed, cancelled)
        category: Filter by category
        search: Search in title and description

    Returns:
        Paginated list of todos
    """

    return dummy_todo_list

@router.post("", response_model=Todo, status_code=status.HTTP_201_CREATED)
async def create_todo(
    todo_in: TodoCreate,
) -> Todo:
    """
    Create a new todo.

    Args:
        todo_in: Todo creation data
        current_user: Current authenticated user
        todo_service: Todo service instance

    Returns:
        Created todo
    """

    new_id = max(todo["id"] for todo in dummy_todo_list["items"]) + 1 if dummy_todo_list["items"] else 1

    new_todo = {
        "id": new_id,
        "owner_id": 101,
        "title": todo_in.title,
        "description": todo_in.description,
        "completed": False,
        "priority": todo_in.priority,
        "status": TodoStatus.PENDING,
        "category": todo_in.category,
        "due_date": todo_in.due_date,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    # Append to dummy list
    dummy_todo_list["items"].append(new_todo)
    dummy_todo_list["total"] += 1

    return new_todo

@router.get("/categories", response_model=list[str])
async def get_categories(
) -> list[str]:
    """
    Get all unique categories for current user's todos.

    Args:
        current_user: Current authenticated user
        todo_service: Todo service instance

    Returns:
        List of unique categories
    """

    return dummy_categories

@router.get("/{todo_id}", response_model=Todo)
async def get_todo(
    todo_id: int,
) -> Todo:
    """
    Get a specific todo by ID.

    Args:
        todo_id: Todo ID
        current_user: Current authenticated user
        todo_service: Todo service instance

    Returns:
        Todo details

    Raises:
        HTTPException: If todo not found or access denied
    """

    for todo in dummy_todo_list["items"]:
        if todo["id"] == todo_id:
            return todo

    raise HTTPException(status_code=404, detail="Todo not found")

@router.put("/{todo_id}", response_model=Todo)
async def update_todo(
    todo_id: int,
    todo_in: TodoUpdate,
) -> Todo:
    """
    Update a todo.

    Args:
        todo_id: Todo ID
        todo_in: Todo update data
        current_user: Current authenticated user
        todo_service: Todo service instance

    Returns:
        Updated todo

    Raises:
        HTTPException: If todo not found or access denied
    """

    for todo in dummy_todo_list["items"]:
        if todo["id"] == todo_id:
            # Update allowed fields
            todo["title"] = todo_in.title or todo["title"]
            todo["description"] = todo_in.description or todo["description"]
            todo["priority"] = todo_in.priority or todo["priority"]
            todo["status"] = todo_in.status or todo["status"]
            todo["category"] = todo_in.category or todo["category"]
            todo["due_date"] = todo_in.due_date or todo["due_date"]
            todo["updated_at"] = datetime.now()
            return todo

    raise HTTPException(status_code=404, detail="Todo not found")

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: int,
) -> None:
    """
    Delete a todo.

    Args:
        todo_id: Todo ID
        current_user: Current authenticated user
        todo_service: Todo service instance

    Raises:
        HTTPException: If todo not found or access denied
    """

    for idx, todo in enumerate(dummy_todo_list["items"]):
        if todo["id"] == todo_id:
            dummy_todo_list["items"].pop(idx)
            dummy_todo_list["total"] -= 1
            return

    raise HTTPException(status_code=404, detail="Todo not found")

@router.patch("/{todo_id}/complete", response_model=Todo)
async def mark_todo_completed(
    todo_id: int,
) -> Todo:
    """
    Mark a todo as completed.

    Args:
        todo_id: Todo ID
        current_user: Current authenticated user
        todo_service: Todo service instance

    Returns:
        Updated todo

    Raises:
        HTTPException: If todo not found or access denied
    """

    for todo in dummy_todo_list["items"]:
        if todo["id"] == todo_id:
            todo["completed"] = True
            todo["status"] = TodoStatus.COMPLETED
            todo["updated_at"] = datetime.now()
            return todo

    raise HTTPException(status_code=404, detail="Todo not found")
