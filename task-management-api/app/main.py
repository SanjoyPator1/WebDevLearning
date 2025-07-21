from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the task router
from app.routers import tasks, auth

# Create FastAPI instance
app = FastAPI(
    title="Task Management API",
    description="A personal task management API built with FastAPI",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc UI
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

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Task Management API is running!"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Task Management API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)