# Task Management API

A personal task management API built with FastAPI for learning purposes.

## Setup

1. Create virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

Visit http://localhost:8000/docs for API documentation

Project Structure

```
app/ - Main application code
tests/ - Test files
static/ - Static files and uploads
```
