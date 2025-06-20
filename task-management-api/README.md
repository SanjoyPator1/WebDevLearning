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

Install dependencies:
bashpip install -r requirements.txt

Run the application:
bashuvicorn app.main:app --reload

Visit http://localhost:8000/docs for API documentation

Project Structure

app/ - Main application code
tests/ - Test files
static/ - Static files and uploads
