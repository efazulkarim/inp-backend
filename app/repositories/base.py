"""
Base repository interfaces and implementations for data access abstraction.
Provides common CRUD operations and database session management.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc

from ..core.logging import get_logger
from ..core.exceptions import DatabaseError, NotFoundError, ValidationError

logger = get_logger(__name__)

# Type variable for model classes
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType], ABC):
    """
    Abstract base repository providing common database operations.
    All repositories should inherit from this class.
    """
    
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model
        self.logger = get_logger(f"{self.__class__.__name__}")
    
    async def create(self, obj_in: Union[CreateSchemaType, Dict[str, Any]]) -> ModelType:
        """Create a new record in the database."""
        try:
            if hasattr(obj_in, 'dict'):
                obj_data = obj_in.dict()
            else:
                obj_data = obj_in
            
            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            self.logger.info(f"Created {self.model.__name__} with id: {db_obj.id}")
            return db_obj
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to create {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to create {self.model.__name__.lower()}")
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a record by its ID."""
        try:
            obj = self.db.query(self.model).filter(self.model.id == id).first()
            if obj:
                self.logger.debug(f"Retrieved {self.model.__name__} with id: {id}")
            return obj
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get {self.model.__name__} by id {id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__.lower()}")
    
    async def get_by_id_or_404(self, id: int) -> ModelType:
        """Get a record by ID or raise NotFoundError if not found."""
        obj = await self.get_by_id(id)
        if not obj:
            raise NotFoundError(
                f"{self.model.__name__} not found",
                resource_type=self.model.__name__.lower(),
                resource_id=str(id)
            )
        return obj
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """Get multiple records with optional filtering and pagination."""
        try:
            query = self.db.query(self.model)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.filter(getattr(self.model, field).in_(value))
                        else:
                            query = query.filter(getattr(self.model, field) == value)
            
            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))
            
            # Apply pagination
            objects = query.offset(skip).limit(limit).all()
            
            self.logger.debug(f"Retrieved {len(objects)} {self.model.__name__} records")
            return objects
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get multiple {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__.lower()} records")
    
    async def update(self, id: int, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """Update an existing record."""
        try:
            db_obj = await self.get_by_id_or_404(id)
            
            if hasattr(obj_in, 'dict'):
                update_data = obj_in.dict(exclude_unset=True)
            else:
                update_data = obj_in
            
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            self.db.commit()
            self.db.refresh(db_obj)
            
            self.logger.info(f"Updated {self.model.__name__} with id: {id}")
            return db_obj
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to update {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to update {self.model.__name__.lower()}")
    
    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        try:
            db_obj = await self.get_by_id_or_404(id)
            self.db.delete(db_obj)
            self.db.commit()
            
            self.logger.info(f"Deleted {self.model.__name__} with id: {id}")
            return True
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to delete {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to delete {self.model.__name__.lower()}")
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering."""
        try:
            query = self.db.query(self.model)
            
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.filter(getattr(self.model, field).in_(value))
                        else:
                            query = query.filter(getattr(self.model, field) == value)
            
            count = query.count()
            self.logger.debug(f"Counted {count} {self.model.__name__} records")
            return count
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to count {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to count {self.model.__name__.lower()} records")
    
    async def exists(self, id: int) -> bool:
        """Check if a record exists by ID."""
        try:
            exists = self.db.query(self.model).filter(self.model.id == id).first() is not None
            return exists
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to check existence of {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to check {self.model.__name__.lower()} existence")
    
    async def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """Get a record by a specific field value."""
        try:
            if not hasattr(self.model, field):
                raise ValidationError(f"Field '{field}' does not exist on {self.model.__name__}")
            
            obj = self.db.query(self.model).filter(getattr(self.model, field) == value).first()
            if obj:
                self.logger.debug(f"Retrieved {self.model.__name__} by {field}: {value}")
            return obj
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get {self.model.__name__} by {field}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__.lower()}")
    
    async def get_multi_by_field(self, field: str, value: Any) -> List[ModelType]:
        """Get multiple records by a specific field value."""
        try:
            if not hasattr(self.model, field):
                raise ValidationError(f"Field '{field}' does not exist on {self.model.__name__}")
            
            objects = self.db.query(self.model).filter(getattr(self.model, field) == value).all()
            self.logger.debug(f"Retrieved {len(objects)} {self.model.__name__} records by {field}: {value}")
            return objects
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get {self.model.__name__} by {field}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__.lower()} records")
    
    async def bulk_create(self, objects: List[Union[CreateSchemaType, Dict[str, Any]]]) -> List[ModelType]:
        """Create multiple records in a single transaction."""
        try:
            db_objects = []
            for obj_in in objects:
                if hasattr(obj_in, 'dict'):
                    obj_data = obj_in.dict()
                else:
                    obj_data = obj_in
                
                db_obj = self.model(**obj_data)
                db_objects.append(db_obj)
            
            self.db.add_all(db_objects)
            self.db.commit()
            
            for db_obj in db_objects:
                self.db.refresh(db_obj)
            
            self.logger.info(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to bulk create {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to bulk create {self.model.__name__.lower()} records")
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Update multiple records in a single transaction."""
        try:
            updated_count = 0
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                
                record_id = update_data.pop('id')
                result = self.db.query(self.model).filter(self.model.id == record_id).update(update_data)
                updated_count += result
            
            self.db.commit()
            self.logger.info(f"Bulk updated {updated_count} {self.model.__name__} records")
            return updated_count
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to bulk update {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to bulk update {self.model.__name__.lower()} records")


class SoftDeleteRepository(BaseRepository[ModelType]):
    """
    Repository with soft delete functionality.
    Assumes the model has a 'deleted_at' field.
    """
    
    async def get_by_id(self, id: int, include_deleted: bool = False) -> Optional[ModelType]:
        """Get a record by ID, optionally including soft-deleted records."""
        try:
            query = self.db.query(self.model).filter(self.model.id == id)
            
            if not include_deleted and hasattr(self.model, 'deleted_at'):
                query = query.filter(self.model.deleted_at.is_(None))
            
            obj = query.first()
            if obj:
                self.logger.debug(f"Retrieved {self.model.__name__} with id: {id}")
            return obj
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get {self.model.__name__} by id {id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__.lower()}")
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """Get multiple records, optionally including soft-deleted records."""
        try:
            query = self.db.query(self.model)
            
            # Exclude soft-deleted records by default
            if not include_deleted and hasattr(self.model, 'deleted_at'):
                query = query.filter(self.model.deleted_at.is_(None))
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.filter(getattr(self.model, field).in_(value))
                        else:
                            query = query.filter(getattr(self.model, field) == value)
            
            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))
            
            # Apply pagination
            objects = query.offset(skip).limit(limit).all()
            
            self.logger.debug(f"Retrieved {len(objects)} {self.model.__name__} records")
            return objects
        
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get multiple {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__.lower()} records")
    
    async def soft_delete(self, id: int) -> bool:
        """Soft delete a record by setting deleted_at timestamp."""
        try:
            if not hasattr(self.model, 'deleted_at'):
                raise ValidationError(f"{self.model.__name__} does not support soft delete")
            
            from datetime import datetime
            db_obj = await self.get_by_id_or_404(id)
            db_obj.deleted_at = datetime.utcnow()
            
            self.db.commit()
            self.logger.info(f"Soft deleted {self.model.__name__} with id: {id}")
            return True
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to soft delete {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to soft delete {self.model.__name__.lower()}")
    
    async def restore(self, id: int) -> ModelType:
        """Restore a soft-deleted record."""
        try:
            if not hasattr(self.model, 'deleted_at'):
                raise ValidationError(f"{self.model.__name__} does not support soft delete")
            
            db_obj = await self.get_by_id(id, include_deleted=True)
            if not db_obj:
                raise NotFoundError(
                    f"{self.model.__name__} not found",
                    resource_type=self.model.__name__.lower(),
                    resource_id=str(id)
                )
            
            db_obj.deleted_at = None
            self.db.commit()
            self.db.refresh(db_obj)
            
            self.logger.info(f"Restored {self.model.__name__} with id: {id}")
            return db_obj
        
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Failed to restore {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to restore {self.model.__name__.lower()}")