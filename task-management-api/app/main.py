from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import routers
from app.routers import tasks, auth, background_tasks
from app.services.reminder_service import reminder_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events

    startup: Initialize background services
    shutdown: Cleanup background services gracefully
    """
    # Startup
    print("🚀 Starting Task Management API...")
    print("📧 MailHog available at: http://localhost:8025")
    print("📱 API docs available at: http://localhost:8000/docs")
    print("⏰ Background services initialized")

    # Optionally auto-start reminder system
    # await reminder_service.start_reminder_system()

    yield

    # Shutdown
    print("🔄 Shutting down gracefully...")
    await reminder_service.stop_reminder_system()
    print("✅ Background services stopped")

# Create FastAPI instance
app = FastAPI(
    title="Task Management API",
    description="A personal task management API built with FastAPI",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc UI
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the tasks router
app.include_router(tasks.router)
app.include_router(auth.router)
app.include_router(background_tasks.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Task Management API is running!"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Task Management API v2.0",
        "version": "2.0.0",
        "docs": "/docs",
        "features": {
            "authentication": "OAuth2 JWT with role-based access",
            "task_management": "Full CRUD with filtering and pagination",
            "background_tasks": "Email notifications and file processing",
            "reports": "CSV and JSON analytics reports",
            "reminders": "Automated due date and overdue notifications"
        },
        "background_services": {
            "email_service": "MailHog SMTP for development",
            "file_processing": "Async image, PDF, and text processing",
            "reminder_system": "Continuous monitoring for due tasks",
            "report_generation": "Background report creation"
        },
        "development_tools": {
            "mailhog_ui": "http://localhost:8025",
            "swagger_docs": "http://localhost:8000/docs",
            "background_status": "http://localhost:8000/background/status"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)