# Task Manager API

A simple task management API built with FastAPI, demonstrating Week 3 concepts.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for interactive documentation.

## Features

- User registration with API key
- Task CRUD operations
- File attachments
- CSV export
- Task statistics
- Filtering & pagination

## API Examples

### Register
```bash
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice"}'
```

### Create Task
```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn FastAPI", "priority": "high"}'
```

### List Tasks
```bash
curl -X GET "http://localhost:8000/api/v1/tasks" \
  -H "X-API-Key: YOUR_API_KEY"
```

See full documentation in day7_week3_mini_project.md
