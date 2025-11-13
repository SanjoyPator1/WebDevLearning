"""
API v1 router aggregation.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, todos, users

api_router = APIRouter()

# include all endpoints routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(todos.router, prefix="/todos", tags=["todos"])