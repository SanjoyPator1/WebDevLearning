"""
FastAPI application entry point with database integration

NOTE: User database system migrated from mock/in-memory (users_db) to SQLAlchemy/PostgreSQL with UserService and async sessions as of 2024-06-09.

This module provides:
- Application startup and shutdown lifecycle
- Database initialization and cleanup
- Router integration with health checks
- Comprehensive error handling
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import database components
from app.database.engine import db_manager
from app.models import Base

# Import routers
from app.routers import tasks, auth, background_tasks
from app.routers.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from app.security.password import PasswordManager
print("Test Admin password : ",PasswordManager.hash_password("admin123"))
print("Test User password : ",PasswordManager.hash_password("user123"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with database integration
    
    Handles:
    - Database engine initialization
    - Connection pool setup
    - Graceful shutdown and cleanup
    """
    logger.info("🚀 Starting Task Management API with Database Integration")
    
    try:
        # Initialize database engine and connections
        logger.info("📊 Initializing database connection...")
        await db_manager.initialize()
        
        # Verify database health
        from app.services.database_health import database_health_service
        health_result = await database_health_service.perform_health_check()
        
        if health_result['status'] == 'healthy':
            logger.info("✅ Database health check passed")
        else:
            logger.warning(f"⚠️ Database health check warning: {health_result}")
        
        logger.info("🎯 Application startup complete!")
        
        # Application is ready to serve requests
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise
    finally:
        # Cleanup during shutdown
        logger.info("🔄 Application shutting down...")
        await db_manager.close()
        logger.info("✅ Database connections closed")
        logger.info("👋 Application shutdown complete")

# Create FastAPI instance with lifespan management
app = FastAPI(
    title="Task Management API with Database",
    description="A comprehensive task management API with PostgreSQL integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(background_tasks.router)

# Root endpoint with database status
@app.get("/")
async def root():
    """
    API root endpoint with system information
    
    Returns:
        API information and database status
    """
    # Check database status
    db_status = "unknown"
    try:
        from app.services.database_health import database_health_service
        health_result = await database_health_service.perform_health_check()
        db_status = health_result['status']
    except Exception as e:
        logger.error(f"Failed to check database status: {e}")
        db_status = "error"
    
    return {
        "message": "Welcome to Task Management API v2.0",
        "description": "FastAPI application with PostgreSQL database integration",
        "features": [
            "🔐 User authentication and authorization",
            "📋 Task and project management", 
            "👥 Team collaboration",
            "📎 File attachments with processing",
            "📧 Email notifications",
            "📊 Analytics and reporting",
            "🗄️ PostgreSQL database with migrations"
        ],
        "database_status": db_status,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "database_health": "/health/database"
        }
    }

# Global exception handler for database errors
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for database and application errors
    
    Args:
        request: FastAPI request object
        exc: Exception that occurred
    
    Returns:
        Error response with appropriate status code
    """
    logger.error(f"Unhandled exception: {exc}")
    
    # Handle database-specific errors
    if "database" in str(exc).lower() or "sqlalchemy" in str(type(exc).__module__).lower():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database Error",
                "message": "Database is temporarily unavailable",
                "hint": "Check /health/database for more information"
            }
        )
    
    # Generic error response
    raise HTTPException(
        status_code=500,
        detail={
            "error": "Internal Server Error", 
            "message": "An unexpected error occurred"
        }
    )