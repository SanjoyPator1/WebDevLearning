"""
Base repository pattern implementation.
Provides generic CRUD operations for all models.
"""
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    This implements the Repository pattern to abstract data access logic.
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        Initialize repository with model and database session.

        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db

    async def get(self, id: int) -> ModelType | None:
        """
        Get a single record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
            self, skip: int = 0, limit: int = 100, **filters: Any
    ) -> list[ModelType]:
        """
        Get multiple records with pagination and filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Additional filter conditions

        Returns:
            List of model instances
        """
        query = select(self.model)

        # apply filters
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                query = query.where(getattr(self.model, key) ==  value)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """
        Create a new record.

        Args:
            obj_in: Dictionary with data for new record

        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        """
        Update an existing record.

        Args:
            db_obj: Existing database object
            obj_in: Dictionary with updated data

        Returns:
            Updated model instance
        """
        for field, value in obj_in.items():
            if value is not None and hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: int) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get(id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.commit()
            return True
        return False
    
    async def count(self, **filters: Any) -> int:
        """
        Count records with optional filters.

        Args:
            **filters: Filter conditions

        Returns:
            Number of matching records
        """
        query = select(self.model)

        # Apply filters
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        result = await self.db.execute(query)
        return len(result.scalars().all())