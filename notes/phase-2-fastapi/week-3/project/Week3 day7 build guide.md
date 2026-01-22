# Week 3 Mini Project: Task Manager API - Build Guide

**Duration**: Day 7, Week 3  
**Phase**: 2 - FastAPI Mastery  
**Goal**: Build a complete Task Manager API using only Week 3 concepts

**IMPORTANT**: This guide provides requirements, structure, and hints. No solutions are given. You implement everything yourself.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Constraints and Rules](#constraints-and-rules)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Data Models](#data-models)
6. [API Endpoints](#api-endpoints)
7. [Implementation Guide](#implementation-guide)
8. [Testing Your API](#testing-your-api)
9. [Hints and Tips](#hints-and-tips)

---

## Project Overview

### What You're Building

A RESTful Task Manager API with the following features:

**User System**

- User registration with API key generation
- Simple API key authentication via headers
- In-memory user storage

**Task Management**

- Create tasks (JSON and Form data)
- List tasks with filtering and pagination
- Get single task details
- Update tasks (full and partial)
- Delete tasks
- Mark tasks as complete/incomplete

**File Handling**

- Upload file attachments to tasks
- Download attachments
- File validation (size, type)

**Data Export**

- Export tasks to CSV
- View task statistics

### Learning Objectives

This project consolidates Week 3 concepts:

- Request handling (path, query, body, form, file)
- Pydantic validation with custom validators
- Dependency injection patterns
- Response models for different views
- Proper HTTP status codes
- Error handling with HTTPException

---

## Constraints and Rules

### You CAN Use

- FastAPI application setup
- All HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Path parameters
- Query parameters
- Request body (Pydantic models)
- Form data
- File uploads (UploadFile)
- Dependencies (Depends)
- Response models
- Status codes
- HTTPException
- In-memory storage (Python dict/list)
- File system for attachments

### You CANNOT Use

These concepts are covered in later weeks:

- Database (PostgreSQL, SQLAlchemy)
- JWT or OAuth2 authentication
- Background tasks (BackgroundTasks)
- WebSockets
- Custom middleware
- Testing frameworks
- Async workers (Celery)

**Note**: Use simple API key authentication stored in memory, not JWT.

---

## Project Structure

Create the following structure:

```
task-manager-api/
├── app/
│   ├── __init__.py           # Empty file (makes app a package)
│   ├── main.py               # FastAPI app and endpoints
│   ├── models.py             # Pydantic models
│   ├── storage.py            # In-memory data storage
│   ├── dependencies.py       # Reusable dependencies
│   └── utils.py              # Helper functions
├── uploads/                  # Directory for file attachments
├── requirements.txt          # Dependencies
└── README.md                 # Documentation
```

### File Purposes

**main.py**

- FastAPI app instance
- All endpoint definitions
- Import models, dependencies, storage, utils

**models.py**

- Pydantic models for requests
- Pydantic models for responses
- Enums for status and priority
- Custom validators

**storage.py**

- In-memory data structures (dicts, lists)
- CRUD functions for users and tasks
- Filter and pagination logic

**dependencies.py**

- Authentication dependency
- Pagination dependency
- Filter dependency
- Task ownership validation dependency

**utils.py**

- API key generation
- File handling utilities
- CSV export function
- Filename sanitization

---

## Requirements

### Dependencies

Create `requirements.txt`:

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
python-multipart==0.0.6
```

Install with: `pip install -r requirements.txt`

### Running the Server

```bash
uvicorn app.main:app --reload
```

Server runs at: http://localhost:8000  
Documentation at: http://localhost:8000/docs

---

## Data Models

### models.py Requirements

**Enums to Create**

```python
TaskStatus
- PENDING = "pending"
- IN_PROGRESS = "in_progress"
- COMPLETED = "completed"

TaskPriority
- LOW = "low"
- MEDIUM = "medium"
- HIGH = "high"
```

**User Models**

1. **UserRegister** (Request)

   - username: string (3-20 chars)
   - Custom validator: alphanumeric + underscore only, not all numbers
   - Transform to lowercase

2. **UserResponse** (Response)

   - username: string
   - created_at: datetime

3. **UserWithApiKey** (Response - extends UserResponse)
   - Includes all UserResponse fields
   - api_key: string

**Task Models**

1. **TaskBase** (Base model)

   - title: string (1-200 chars, required)
   - description: optional string (max 2000 chars)
   - priority: TaskPriority enum (default: MEDIUM)
   - due_date: optional date
   - Custom validator: due_date cannot be in the past

2. **TaskCreate** (Request - inherits TaskBase)

   - No additional fields

3. **TaskUpdate** (Request)

   - All fields optional (for partial updates)
   - title: optional string (1-200 chars)
   - description: optional string
   - priority: optional TaskPriority
   - due_date: optional date
   - Same due_date validator

4. **TaskListResponse** (Response - lightweight for lists)

   - id: int
   - title: string
   - status: TaskStatus
   - priority: TaskPriority
   - due_date: optional date
   - created_at: datetime

5. **TaskDetailResponse** (Response - extends TaskListResponse)
   - All TaskListResponse fields
   - description: optional string
   - attachments: list of strings
   - updated_at: optional datetime
   - user: string (username)

**Utility Models**

1. **PaginationParams**

   - skip: int (default 0, min 0)
   - limit: int (default 10, min 1, max 100)

2. **TaskFilters**

   - status: optional TaskStatus
   - priority: optional TaskPriority
   - search: optional string

3. **PaginatedTaskResponse**

   - items: list of TaskListResponse
   - total: int
   - skip: int
   - limit: int

4. **TaskStats**

   - total: int
   - by_status: dict mapping TaskStatus to count
   - by_priority: dict mapping TaskPriority to count
   - overdue: int

5. **MessageResponse**
   - message: string

---

## API Endpoints

### Required Endpoints

**Authentication**

```
POST   /api/v1/users/register
GET    /api/v1/users/me
```

**Tasks - CRUD**

```
GET    /api/v1/tasks
POST   /api/v1/tasks
POST   /api/v1/tasks/form
GET    /api/v1/tasks/{task_id}
PUT    /api/v1/tasks/{task_id}
PATCH  /api/v1/tasks/{task_id}/complete
PATCH  /api/v1/tasks/{task_id}/incomplete
DELETE /api/v1/tasks/{task_id}
```

**Attachments**

```
POST   /api/v1/tasks/{task_id}/attachments
GET    /api/v1/tasks/{task_id}/attachments
GET    /api/v1/tasks/{task_id}/attachments/{filename}
```

**Export & Stats**

```
GET    /api/v1/tasks/export/csv
GET    /api/v1/tasks/stats
```

### Endpoint Details

**POST /api/v1/users/register**

- Request: UserRegister
- Response: UserWithApiKey (status 201)
- Generates unique API key
- Stores user in memory
- Returns user with API key

**GET /api/v1/users/me**

- Headers: X-API-Key
- Response: UserResponse
- Requires authentication dependency

**GET /api/v1/tasks**

- Headers: X-API-Key
- Query params: skip, limit, status, priority, search
- Response: PaginatedTaskResponse
- Uses pagination and filter dependencies

**POST /api/v1/tasks**

- Headers: X-API-Key
- Request: TaskCreate
- Response: TaskDetailResponse (status 201)
- Creates task for authenticated user

**POST /api/v1/tasks/form**

- Headers: X-API-Key
- Form fields: title, description, priority, due_date
- Response: TaskDetailResponse (status 201)
- Alternative to JSON creation

**GET /api/v1/tasks/{task_id}**

- Headers: X-API-Key
- Response: TaskDetailResponse
- Uses task ownership dependency

**PUT /api/v1/tasks/{task_id}**

- Headers: X-API-Key
- Request: TaskUpdate
- Response: TaskDetailResponse
- Partial update support

**PATCH /api/v1/tasks/{task_id}/complete**

- Headers: X-API-Key
- Response: TaskDetailResponse
- Sets status to COMPLETED

**PATCH /api/v1/tasks/{task_id}/incomplete**

- Headers: X-API-Key
- Response: TaskDetailResponse
- Sets status to PENDING

**DELETE /api/v1/tasks/{task_id}**

- Headers: X-API-Key
- Response: None (status 204)
- Deletes task

**POST /api/v1/tasks/{task_id}/attachments**

- Headers: X-API-Key
- File: multipart/form-data
- Response: MessageResponse (status 201)
- Validates file size and type
- Saves to uploads directory

**GET /api/v1/tasks/{task_id}/attachments**

- Headers: X-API-Key
- Response: list of strings (filenames)

**GET /api/v1/tasks/{task_id}/attachments/{filename}**

- Headers: X-API-Key
- Response: FileResponse
- Downloads attachment

**GET /api/v1/tasks/export/csv**

- Headers: X-API-Key
- Response: StreamingResponse (CSV file)
- Exports all user tasks

**GET /api/v1/tasks/stats**

- Headers: X-API-Key
- Response: TaskStats
- Counts by status, priority, overdue

---

## Implementation Guide

### Step 1: Setup Project

Create directory structure and install dependencies.

### Step 2: Create Data Storage (storage.py)

**In-Memory Storage Design**

```python
# Global variables for storage
users_db = {}        # {username: user_dict}
api_keys_db = {}     # {api_key: username}
tasks_db = {}        # {task_id: task_dict}
task_id_counter = 1  # Auto-increment ID
```

**Functions to Implement**

User functions:

- `create_user(username, api_key) -> dict`
- `get_user_by_username(username) -> dict | None`
- `get_user_by_api_key(api_key) -> dict | None`
- `username_exists(username) -> bool`

Task functions:

- `create_task(task_data, username) -> dict`
- `get_task(task_id) -> dict | None`
- `get_user_tasks(username, status, priority, search, skip, limit) -> tuple[list, int]`
- `update_task(task_id, updates) -> dict`
- `delete_task(task_id) -> None`
- `add_attachment(task_id, filename) -> dict`

Statistics:

- `get_user_task_stats(username) -> dict`

**Hints**

- Store timestamps as datetime objects
- Task dict should include: id, title, description, status, priority, due_date, attachments, created_at, updated_at, user
- Filter tasks by iterating and checking conditions
- Pagination: `tasks[skip:skip+limit]`

### Step 3: Create Utilities (utils.py)

**Functions to Implement**

- `generate_api_key() -> str` - Format: "sk\_" + 32 random hex chars
- `get_upload_path(username, task_id, filename) -> Path` - Returns path, creates directory
- `get_safe_filename(filename) -> str` - Removes path traversal attempts
- `validate_file_size(file_size, max_size_mb) -> bool`
- `validate_file_type(content_type, allowed_types) -> bool`
- `tasks_to_csv(tasks) -> str` - Converts task list to CSV string

**Hints**

- Use `secrets.token_hex()` for API key
- Use `pathlib.Path` for file paths
- Create directories with `mkdir(parents=True, exist_ok=True)`
- Use `csv.DictWriter` for CSV generation
- Use `io.StringIO` for in-memory CSV

### Step 4: Create Dependencies (dependencies.py)

**Dependencies to Implement**

1. `get_api_key(x_api_key: str = Header(...)) -> str`

   - Extracts API key from header

2. `get_current_user(api_key = Depends(get_api_key)) -> dict`

   - Validates API key
   - Returns user or raises 401

3. `get_pagination(skip: int = Query(...), limit: int = Query(...)) -> PaginationParams`

   - Returns pagination params
   - Validates constraints

4. `get_task_filters(status, priority, search) -> TaskFilters`

   - Extracts and returns filters

5. `get_user_task(task_id: int, current_user = Depends(get_current_user)) -> dict`
   - Gets task from storage
   - Validates ownership
   - Raises 404 if not found
   - Raises 403 if not owned

**Hints**

- Chain dependencies: `get_user_task` depends on `get_current_user`
- Use `Header(...)` to require headers
- Use `Query(default, ge=0)` for validation
- Return 401 with `WWW-Authenticate` header

### Step 5: Create Models (models.py)

Follow the data models specification above.

**Validator Examples**

```python
@field_validator('username')
@classmethod
def validate_username(cls, v: str) -> str:
    # Check format, raise ValueError if invalid
    # Return normalized value
    pass

@field_validator('due_date')
@classmethod
def validate_due_date(cls, v: date | None) -> date | None:
    # Check if in past, raise ValueError if invalid
    # Return value
    pass
```

**Hints**

- Use `Field(...)` for required fields
- Use `Field(default=...)` for optional
- Use `Field(min_length=..., max_length=...)` for strings
- Use `Field(ge=..., le=...)` for numbers
- Inherit models: `class Child(Parent):`
- Set examples in Config for documentation

### Step 6: Create Endpoints (main.py)

**Application Setup**

```python
app = FastAPI(
    title="Task Manager API",
    description="...",
    version="1.0.0"
)
```

**Endpoint Pattern**

```python
@app.post(
    "/path",
    response_model=ResponseModel,
    status_code=status.HTTP_201_CREATED,
    summary="Short description",
    description="Longer description"
)
async def endpoint_name(
    path_param: type,
    query_param: type = Query(...),
    body: Model,
    dependency = Depends(some_dependency)
):
    # Logic
    return result
```

**Status Codes to Use**

- 200 OK - Successful GET/PUT
- 201 Created - Successful POST
- 204 No Content - Successful DELETE
- 400 Bad Request - Validation errors
- 401 Unauthorized - Invalid API key
- 403 Forbidden - Not authorized
- 404 Not Found - Resource not found
- 409 Conflict - Username exists
- 422 Unprocessable Entity - Pydantic validation (automatic)

**File Upload Example Structure**

```python
@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    # Read file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    # Validate size and type
    # Save file
    # Return response
```

**File Download Example Structure**

```python
from fastapi.responses import FileResponse

@app.get("/download/{filename}")
async def download(filename: str):
    # Validate file exists
    # Return FileResponse
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
```

**CSV Export Example Structure**

```python
from fastapi.responses import StreamingResponse

@app.get("/export/csv")
async def export():
    # Get data
    # Convert to CSV
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks.csv"}
    )
```

### Step 7: Test Your API

Use the interactive docs at http://localhost:8000/docs

---

## Testing Your API

### Workflow to Test

**1. Register User**

```bash
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice"}'
```

Expected response (201):

```json
{
  "username": "alice",
  "api_key": "sk_abc123...",
  "created_at": "2024-01-15T10:30:00"
}
```

Save the API key!

**2. Create Task (JSON)**

```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn FastAPI",
    "description": "Complete Week 3",
    "priority": "high",
    "due_date": "2024-01-20"
  }'
```

Expected response (201):

```json
{
  "id": 1,
  "title": "Learn FastAPI",
  "description": "Complete Week 3",
  "status": "pending",
  "priority": "high",
  "due_date": "2024-01-20",
  "attachments": [],
  "created_at": "2024-01-15T10:30:00",
  "updated_at": null,
  "user": "alice"
}
```

**3. List Tasks**

```bash
curl -X GET "http://localhost:8000/api/v1/tasks?skip=0&limit=10" \
  -H "X-API-Key: YOUR_API_KEY"
```

Expected response (200):

```json
{
  "items": [...],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

**4. Filter Tasks**

```bash
curl -X GET "http://localhost:8000/api/v1/tasks?status=pending&priority=high" \
  -H "X-API-Key: YOUR_API_KEY"
```

**5. Update Task**

```bash
curl -X PUT "http://localhost:8000/api/v1/tasks/1" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"priority": "medium"}'
```

**6. Mark Complete**

```bash
curl -X PATCH "http://localhost:8000/api/v1/tasks/1/complete" \
  -H "X-API-Key: YOUR_API_KEY"
```

**7. Upload Attachment**

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/1/attachments" \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@document.pdf"
```

**8. Delete Task**

```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/1" \
  -H "X-API-Key: YOUR_API_KEY"
```

Expected: 204 No Content

### Test Error Cases

- Invalid API key → 401
- Task not found → 404
- Access other user's task → 403
- Invalid data → 422
- Duplicate username → 409
- File too large → 400

---

## Hints and Tips

### General Guidelines

**Start Small**

- Implement user registration first
- Then task creation
- Then listing
- Then the rest

**Test Frequently**

- Test each endpoint as you build it
- Use /docs for interactive testing
- Check response codes

**Use Type Hints**

- All function parameters
- All return types
- Helps with debugging

**Read FastAPI Docs**

- Check FastAPI documentation when stuck
- Look at Pydantic docs for validation

### Common Patterns

**Dependency Chain**

```python
# Simple dependency
def get_api_key(x_api_key: str = Header(...)) -> str:
    return x_api_key

# Uses simple dependency
def get_current_user(api_key: str = Depends(get_api_key)) -> dict:
    user = storage.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user

# Uses user dependency
def get_user_task(task_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    task = storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["user"] != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return task
```

**Partial Update Pattern**

```python
@app.put("/tasks/{task_id}")
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    task: dict = Depends(get_user_task)
):
    # Only update fields that were provided
    updates = task_update.model_dump(exclude_unset=True)
    updated_task = storage.update_task(task_id, updates)
    return updated_task
```

**Filter Pattern**

```python
def get_user_tasks(username, status=None, priority=None, search=None, skip=0, limit=10):
    # Start with all user tasks
    tasks = [t for t in tasks_db.values() if t["user"] == username]

    # Apply filters
    if status:
        tasks = [t for t in tasks if t["status"] == status]

    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    if search:
        search_lower = search.lower()
        tasks = [
            t for t in tasks
            if search_lower in t["title"].lower() or
               (t["description"] and search_lower in t["description"].lower())
        ]

    # Get total before pagination
    total = len(tasks)

    # Apply pagination
    tasks = tasks[skip:skip + limit]

    return tasks, total
```

**File Validation Pattern**

```python
# Get file size
file.file.seek(0, 2)  # Seek to end
file_size = file.file.tell()
file.file.seek(0)  # Seek back to start

# Validate
if file_size > 10 * 1024 * 1024:  # 10 MB
    raise HTTPException(status_code=400, detail="File too large")

# Validate type
allowed_types = ["application/pdf", "image/jpeg", "image/png"]
if file.content_type not in allowed_types:
    raise HTTPException(status_code=400, detail="File type not allowed")
```

### Debugging Tips

**Print Statements**

- Add print statements to understand flow
- Print request data
- Print storage state

**Check Interactive Docs**

- /docs shows all endpoints
- Shows expected request/response
- Try it out feature for testing

**Common Errors**

- "Field required" → Check request model
- "Unprocessable Entity" → Check Pydantic validation
- "Not found" → Check URL path
- "Method not allowed" → Check HTTP method

### Week 3 Concept Mapping

This table shows which Week 3 concept each feature uses:

| Feature           | Week 3 Concepts Used                                                   |
| ----------------- | ---------------------------------------------------------------------- |
| User registration | POST, Request body, Pydantic validation, Custom validators, 201 status |
| API key auth      | Header extraction, Dependencies, 401 error                             |
| List tasks        | GET, Query params, Pagination dependency, Response model               |
| Create task       | POST, Request body, Authentication dependency, 201 status              |
| Form creation     | Form data, Form fields                                                 |
| Get task          | GET, Path params, Dependency chain, 404/403 errors                     |
| Update task       | PUT, Partial update, model_dump(exclude_unset=True)                    |
| Mark complete     | PATCH, Path param, Status update                                       |
| Delete task       | DELETE, 204 status, No response body                                   |
| File upload       | File handling, UploadFile, File validation, multipart/form-data        |
| File download     | FileResponse, Path validation                                          |
| CSV export        | StreamingResponse, Custom headers                                      |
| Filtering         | Query parameters, Filter dependency                                    |
| Pagination        | Query parameters, Pagination dependency                                |
| Statistics        | Aggregation logic, Response model                                      |

---

## Completion Checklist

Use this checklist to track your progress:

**Setup**

- [ ] Create project structure
- [ ] Install dependencies
- [ ] Create empty files

**Storage Layer**

- [ ] Implement user storage functions
- [ ] Implement task storage functions
- [ ] Implement filtering logic
- [ ] Implement statistics function

**Utilities**

- [ ] API key generation
- [ ] File path utilities
- [ ] File validation
- [ ] CSV export

**Dependencies**

- [ ] API key extraction
- [ ] User authentication
- [ ] Pagination parameters
- [ ] Task filters
- [ ] Task ownership validation

**Models**

- [ ] Enums (TaskStatus, TaskPriority)
- [ ] User models (3 models)
- [ ] Task models (5 models)
- [ ] Utility models (5 models)
- [ ] Custom validators

**Endpoints - Users**

- [ ] POST /users/register
- [ ] GET /users/me

**Endpoints - Tasks**

- [ ] GET /tasks (with filters)
- [ ] POST /tasks (JSON)
- [ ] POST /tasks/form
- [ ] GET /tasks/{id}
- [ ] PUT /tasks/{id}
- [ ] PATCH /tasks/{id}/complete
- [ ] PATCH /tasks/{id}/incomplete
- [ ] DELETE /tasks/{id}

**Endpoints - Attachments**

- [ ] POST /tasks/{id}/attachments
- [ ] GET /tasks/{id}/attachments
- [ ] GET /tasks/{id}/attachments/{filename}

**Endpoints - Export**

- [ ] GET /tasks/export/csv
- [ ] GET /tasks/stats

**Testing**

- [ ] Test user registration
- [ ] Test authentication
- [ ] Test task CRUD
- [ ] Test filtering
- [ ] Test pagination
- [ ] Test file upload
- [ ] Test file download
- [ ] Test CSV export
- [ ] Test error cases

---

## What's Next

After completing this project, you'll be ready for Week 4 where you'll learn:

- JWT authentication (replace API keys)
- OAuth2 flows
- Password hashing
- Role-based access control
- Security best practices

Then in Week 5:

- Background tasks
- WebSockets
- Custom middleware
- Advanced error handling

And in Week 6:

- Comprehensive testing
- Test fixtures
- Mocking
- Test coverage

**Good luck building your Task Manager API!**
