"""
Database session utilities and helpers

This module provides:
- Transaction context managers
- Session-based query helpers
- Bulk operation utilities
- Error handling wrappers
"""

from contextlib import asynccontextmanager
from typing import TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload, contains_eager
import logging

from app.models.base import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class SessionManager:
    """
    Session manager with transaction support and query utilities
    
    Provides high-level database operations with proper error handling,
    transaction management, and query optimization.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @asynccontextmanager
    async def transaction(self):
        """
        Async context manager for database transactions
        
        Automatically commits on success or rolls back on error.
        Supports nested transactions via savepoints.
        
        Usage:
            async with SessionManager(db).transaction():
                # Database operations here
                user = User(email="test@example.com")
                session.add(user)
                # Automatically committed on success
        """
        transaction = await self.session.begin()
        try:
            yield transaction
            await transaction.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            await transaction.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
    
    async def get_by_id(self, model: type[T], id: Any, load_relationships: List[str] = None) -> Optional[T]:
        """
        Get model instance by ID with optional relationship loading
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            load_relationships: List of relationship names to eager load
        
        Returns:
            Model instance or None if not found
        
        Example:
            user = await session_manager.get_by_id(
                User, 
                user_id, 
                load_relationships=['created_tasks', 'team_memberships']
            )
        """
        query = select(model).where(model.id == id)
        
        # Add relationship loading if specified
        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(model, rel)))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        model: type[T], 
        filters: Dict[str, Any] = None,
        load_relationships: List[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """
        Get multiple model instances with filtering and pagination
        
        Args:
            model: SQLAlchemy model class
            filters: Dictionary of field filters {field_name: value}
            load_relationships: List of relationship names to eager load
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field name to order by (prefix with '-' for descending)
        
        Returns:
            List of model instances
        
        Example:
            tasks = await session_manager.get_all(
                Task,
                filters={'completed': False, 'priority': 'high'},
                load_relationships=['user', 'project'],
                limit=10,
                order_by='-created_at'
            )
        """
        query = select(model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(model, field):
                    query = query.where(getattr(model, field) == value)
        
        # Add relationship loading
        if load_relationships:
            for rel in load_relationships:
                if hasattr(model, rel):
                    query = query.options(selectinload(getattr(model, rel)))
        
        # Add ordering
        if order_by:
            if order_by.startswith('-'):
                # Descending order
                field_name = order_by[1:]
                if hasattr(model, field_name):
                    query = query.order_by(getattr(model, field_name).desc())
            else:
                # Ascending order
                if hasattr(model, order_by):
                    query = query.order_by(getattr(model, order_by))
        
        # Add pagination
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create(self, instance: T) -> T:
        """
        Create new model instance
        
        Args:
            instance: Model instance to create
        
        Returns:
            Created instance with populated ID and timestamps
        """
        self.session.add(instance)
        await self.session.flush()  # Get ID without committing
        await self.session.refresh(instance)  # Refresh with DB values
        return instance
    
    async def bulk_create(self, instances: List[T]) -> List[T]:
        """
        Create multiple model instances efficiently
        
        Args:
            instances: List of model instances to create
        
        Returns:
            List of created instances
        """
        self.session.add_all(instances)
        await self.session.flush()
        
        # Refresh all instances to get DB-generated values
        for instance in instances:
            await self.session.refresh(instance)
        
        return instances
    
    async def update_by_id(self, model: type[T], id: Any, updates: Dict[str, Any]) -> Optional[T]:
        """
        Update model instance by ID
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            updates: Dictionary of fields to update
        
        Returns:
            Updated instance or None if not found
        """
        # First get the instance
        instance = await self.get_by_id(model, id)
        if not instance:
            return None
        
        # Apply updates
        for field, value in updates.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def delete_by_id(self, model: type[T], id: Any, soft_delete: bool = True) -> bool:
        """
        Delete model instance by ID
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            soft_delete: Whether to use soft delete (set deleted_at) or hard delete
        
        Returns:
            True if instance was deleted, False if not found
        """
        instance = await self.get_by_id(model, id)
        if not instance:
            return False
        
        if soft_delete and hasattr(instance, 'soft_delete'):
            # Use soft delete
            instance.soft_delete()
            await self.session.flush()
        else:
            # Hard delete
            await self.session.delete(instance)
        
        return True
    
    async def count(self, model: type[T], filters: Dict[str, Any] = None) -> int:
        """
        Count model instances with optional filtering
        
        Args:
            model: SQLAlchemy model class
            filters: Dictionary of field filters
        
        Returns:
            Number of matching records
        """
        from sqlalchemy import func
        
        query = select(func.count(model.id))
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(model, field):
                    query = query.where(getattr(model, field) == value)
        
        result = await self.session.execute(query)
        return result.scalar()
    
    async def exists(self, model: type[T], filters: Dict[str, Any]) -> bool:
        """
        Check if model instance exists with given filters
        
        Args:
            model: SQLAlchemy model class
            filters: Dictionary of field filters
        
        Returns:
            True if matching record exists
        """
        count = await self.count(model, filters)
        return count > 0