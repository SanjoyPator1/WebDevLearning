"""
FastAPI application entry point.
"""
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config import settings

app = FastAPI(title="Todo App")

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Simple health check route
@app.get("/health")
async def health_check():
    return {"status": "ok"}