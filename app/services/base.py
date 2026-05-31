"""
Base service classes and interfaces for business logic layer.
Provides common service patterns and dependency injection utilities.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from sqlalchemy.orm import Session

from ..core.logging import get_logger
from ..core.exceptions import (
    AppException, ValidationError, NotFoundError, 
    BusinessLogicError, DatabaseError, ErrorContext
)
from ..repositories.dependencies import RepositoryContainer

logger = get_logger(__name__)

# Type variables for service classes
ServiceType = TypeVar("ServiceType")
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
ResponseSchemaType = TypeVar("ResponseSchemaType")


class BaseService(ABC):
    """
    Abstract base service providing common business logic patterns.
    All services should inherit from this class.
    """
    
    def __init__(self, repositories: RepositoryContainer):
        self.repositories = repositories
        self.logger = get_logger(f"{self.__class__.__name__}")
    
    def validate_user_access(self, user_id: int, resource_user_id: int, resource_name: str = "resource"):
        """Validate that a user has access to a resource."""
        if user_id != resource_user_id:
            raise ValidationError(f"User does not have access to this {resource_name}")
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]):
        """Validate that all required fields are present and not empty."""
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    def validate_positive_integer(self, value: Any, field_name: str):
        """Validate that a value is a positive integer."""
        if not isinstance(value, int) or value <= 0:
            raise ValidationError(f"{field_name} must be a positive integer")
    
    def validate_string_length(self, value: str, field_name: str, min_length: int = 1, max_length: int = 255):
        """Validate string length constraints."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if len(value.strip()) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters long")
        
        if len(value) > max_length:
            raise ValidationError(f"{field_name} must not exceed {max_length} characters")
    
    def validate_email_format(self, email: str):
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
    
    def sanitize_string(self, value: str) -> str:
        """Sanitize string input by trimming whitespace."""
        if isinstance(value, str):
            return value.strip()
        return value
    
    def handle_repository_error(self, operation: str, error: Exception):
        """Handle repository errors and convert to appropriate service exceptions."""
        if isinstance(error, (ValidationError, NotFoundError, BusinessLogicError)):
            # Re-raise business logic exceptions as-is
            raise error
        elif isinstance(error, DatabaseError):
            # Log database errors and re-raise
            self.logger.error(f"Database error during {operation}: {str(error)}")
            raise error
        else:
            # Convert unexpected errors to database errors
            self.logger.error(f"Unexpected error during {operation}: {str(error)}")
            raise DatabaseError(f"Operation failed: {operation}")


class CRUDService(BaseService, Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """
    Generic CRUD service providing common create, read, update, delete operations.
    """
    
    def __init__(self, repositories: RepositoryContainer, repository_name: str):
        super().__init__(repositories)
        self.repository_name = repository_name
        self._repository = None
    
    @property
    def repository(self):
        """Get the repository instance."""
        if self._repository is None:
            self._repository = getattr(self.repositories, self.repository_name)
        return self._repository
    
    async def create(self, data: CreateSchemaType, user_id: Optional[int] = None) -> ResponseSchemaType:
        """Create a new entity."""
        with ErrorContext(f"create {self.repository_name}", self.logger):
            try:
                # Convert Pydantic model to dict if needed
                if hasattr(data, 'dict'):
                    create_data = data.dict()
                else:
                    create_data = data
                
                # Add user_id if provided and not already in data
                if user_id and 'user_id' not in create_data:
                    create_data['user_id'] = user_id
                
                # Validate and sanitize data
                await self.validate_create_data(create_data)
                create_data = await self.sanitize_create_data(create_data)
                
                # Create entity
                entity = await self.repository.create(create_data)
                
                # Convert to response schema
                response = await self.to_response_schema(entity)
                
                self.logger.info(f"Created {self.repository_name} with id: {entity.id}")
                return response
            
            except Exception as e:
                self.handle_repository_error(f"create {self.repository_name}", e)
    
    async def get_by_id(self, entity_id: int, user_id: Optional[int] = None) -> ResponseSchemaType:
        """Get entity by ID."""
        with ErrorContext(f"get {self.repository_name} by id", self.logger):
            try:
                entity = await self.repository.get_by_id_or_404(entity_id)
                
                # Check user access if user_id provided
                if user_id and hasattr(entity, 'user_id'):
                    self.validate_user_access(user_id, entity.user_id, self.repository_name)
                
                response = await self.to_response_schema(entity)
                return response
            
            except Exception as e:
                self.handle_repository_error(f"get {self.repository_name} by id", e)
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        user_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ResponseSchemaType]:
        """Get multiple entities with optional filtering."""
        with ErrorContext(f"get multiple {self.repository_name}", self.logger):
            try:
                # Add user filter if provided
                if user_id:
                    filters = filters or {}
                    filters['user_id'] = user_id
                
                entities = await self.repository.get_multi(
                    skip=skip, 
                    limit=limit, 
                    filters=filters
                )
                
                responses = []
                for entity in entities:
                    response = await self.to_response_schema(entity)
                    responses.append(response)
                
                return responses
            
            except Exception as e:
                self.handle_repository_error(f"get multiple {self.repository_name}", e)
    
    async def update(self, entity_id: int, data: UpdateSchemaType, user_id: Optional[int] = None) -> ResponseSchemaType:
        """Update an existing entity."""
        with ErrorContext(f"update {self.repository_name}", self.logger):
            try:
                # Check if entity exists and user has access
                existing_entity = await self.repository.get_by_id_or_404(entity_id)
                
                if user_id and hasattr(existing_entity, 'user_id'):
                    self.validate_user_access(user_id, existing_entity.user_id, self.repository_name)
                
                # Convert Pydantic model to dict if needed
                if hasattr(data, 'dict'):
                    update_data = data.dict(exclude_unset=True)
                else:
                    update_data = data
                
                # Validate and sanitize data
                await self.validate_update_data(update_data, existing_entity)
                update_data = await self.sanitize_update_data(update_data)
                
                # Update entity
                entity = await self.repository.update(entity_id, update_data)
                
                # Convert to response schema
                response = await self.to_response_schema(entity)
                
                self.logger.info(f"Updated {self.repository_name} with id: {entity_id}")
                return response
            
            except Exception as e:
                self.handle_repository_error(f"update {self.repository_name}", e)
    
    async def delete(self, entity_id: int, user_id: Optional[int] = None) -> bool:
        """Delete an entity."""
        with ErrorContext(f"delete {self.repository_name}", self.logger):
            try:
                # Check if entity exists and user has access
                existing_entity = await self.repository.get_by_id_or_404(entity_id)
                
                if user_id and hasattr(existing_entity, 'user_id'):
                    self.validate_user_access(user_id, existing_entity.user_id, self.repository_name)
                
                # Perform pre-delete validation
                await self.validate_delete(existing_entity)
                
                # Delete entity
                result = await self.repository.delete(entity_id)
                
                self.logger.info(f"Deleted {self.repository_name} with id: {entity_id}")
                return result
            
            except Exception as e:
                self.handle_repository_error(f"delete {self.repository_name}", e)
    
    async def count(self, user_id: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering."""
        with ErrorContext(f"count {self.repository_name}", self.logger):
            try:
                # Add user filter if provided
                if user_id:
                    filters = filters or {}
                    filters['user_id'] = user_id
                
                count = await self.repository.count(filters)
                return count
            
            except Exception as e:
                self.handle_repository_error(f"count {self.repository_name}", e)
    
    # Abstract methods to be implemented by concrete services
    async def validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate data for create operation. Override in subclasses."""
        pass
    
    async def validate_update_data(self, data: Dict[str, Any], existing_entity: ModelType) -> None:
        """Validate data for update operation. Override in subclasses."""
        pass
    
    async def validate_delete(self, entity: ModelType) -> None:
        """Validate delete operation. Override in subclasses."""
        pass
    
    async def sanitize_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data for create operation. Override in subclasses."""
        return data
    
    async def sanitize_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data for update operation. Override in subclasses."""
        return data
    
    async def to_response_schema(self, entity: ModelType) -> ResponseSchemaType:
        """Convert entity to response schema. Override in subclasses."""
        # Default implementation returns the entity as-is
        return entity


class ServiceContainer:
    """Container for managing service instances with shared dependencies."""
    
    def __init__(self, repositories: RepositoryContainer):
        self.repositories = repositories
        self._services = {}
    
    def get_service(self, service_class: Type[ServiceType]) -> ServiceType:
        """Get or create a service instance."""
        service_name = service_class.__name__
        
        if service_name not in self._services:
            self._services[service_name] = service_class(self.repositories)
        
        return self._services[service_name]
    
    def clear_cache(self):
        """Clear the service cache."""
        self._services.clear()


# Service dependency injection utilities
def get_service_container(repositories: RepositoryContainer) -> ServiceContainer:
    """Get ServiceContainer instance with repository dependencies."""
    return ServiceContainer(repositories)


# Service testing utilities
class TestServiceMixin:
    """Mixin providing testing utilities for services."""
    
    def create_test_data(self, **kwargs) -> Dict[str, Any]:
        """Create test data with default values. Override in subclasses."""
        return kwargs
    
    def assert_valid_response(self, response: Any, expected_fields: List[str]):
        """Assert that a response contains expected fields."""
        if hasattr(response, 'dict'):
            response_dict = response.dict()
        else:
            response_dict = response.__dict__ if hasattr(response, '__dict__') else response
        
        for field in expected_fields:
            assert field in response_dict, f"Expected field '{field}' not found in response"
    
    def assert_validation_error(self, error: Exception, expected_message: str = None):
        """Assert that an exception is a validation error with optional message check."""
        assert isinstance(error, ValidationError), f"Expected ValidationError, got {type(error)}"
        
        if expected_message:
            assert expected_message in str(error), f"Expected message '{expected_message}' not found in error"