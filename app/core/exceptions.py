"""
Custom exception hierarchy and error handling utilities.
Provides structured error responses while maintaining backward compatibility.
"""
from typing import Any, Dict, Optional, List
from datetime import datetime
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .logging import get_logger

logger = get_logger(__name__)


class ErrorResponse(BaseModel):
    """Structured error response model."""
    detail: str
    error_code: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None
    method: Optional[str] = None


class AppException(Exception):
    """Base application exception with structured error information."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error for input data."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, "VALIDATION_ERROR", details)
        self.field = field


class AuthenticationError(AppException):
    """Authentication related errors."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 401, "AUTHENTICATION_ERROR", details)


class AuthorizationError(AppException):
    """Authorization related errors."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 403, "AUTHORIZATION_ERROR", details)


class NotFoundError(AppException):
    """Resource not found errors."""
    
    def __init__(self, message: str = "Resource not found", resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, 404, "NOT_FOUND_ERROR", details)


class ConflictError(AppException):
    """Resource conflict errors."""
    
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 409, "CONFLICT_ERROR", details)


class BusinessLogicError(AppException):
    """Business logic validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 422, "BUSINESS_LOGIC_ERROR", details)


class ExternalServiceError(AppException):
    """External service integration errors."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if service_name:
            error_details["service_name"] = service_name
        super().__init__(message, 502, "EXTERNAL_SERVICE_ERROR", error_details)


class DatabaseError(AppException):
    """Database operation errors."""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, "DATABASE_ERROR", details)


class RateLimitError(AppException):
    """Rate limiting errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, 429, "RATE_LIMIT_ERROR", details)


# Exception handlers for FastAPI
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    from .logging import get_correlation_id
    
    correlation_id = get_correlation_id()
    
    # Log the exception
    logger.error(
        f"Application exception: {exc.message}",
        error_code=exc.error_code,
        status_code=exc.status_code,
        path=str(request.url.path),
        method=request.method,
        details=exc.details,
        correlation_id=correlation_id
    )
    
    # Create error response
    error_response = ErrorResponse(
        detail=exc.message,
        error_code=exc.error_code,
        correlation_id=correlation_id,
        path=str(request.url.path),
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation exceptions with detailed field information."""
    from .logging import get_correlation_id
    
    correlation_id = get_correlation_id()
    
    logger.warning(
        f"Validation error: {exc.message}",
        field=getattr(exc, 'field', None),
        path=str(request.url.path),
        method=request.method,
        correlation_id=correlation_id
    )
    
    # Maintain backward compatibility with existing validation error format
    return JSONResponse(
        status_code=422,
        content={"detail": exc.message}
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions with enhanced logging."""
    from .logging import get_correlation_id
    
    correlation_id = get_correlation_id()
    
    logger.warning(
        f"HTTP exception: {exc.detail}",
        status_code=exc.status_code,
        path=str(request.url.path),
        method=request.method,
        correlation_id=correlation_id
    )
    
    # Maintain backward compatibility with existing HTTP exception format
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with proper logging and safe error responses."""
    from .logging import get_correlation_id
    
    correlation_id = get_correlation_id()
    
    logger.exception(
        f"Unexpected exception: {str(exc)}",
        exception_type=type(exc).__name__,
        path=str(request.url.path),
        method=request.method,
        correlation_id=correlation_id
    )
    
    # Return generic error message to avoid exposing internal details
    error_response = ErrorResponse(
        detail="An internal server error occurred",
        error_code="INTERNAL_SERVER_ERROR",
        correlation_id=correlation_id,
        path=str(request.url.path),
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


# Utility functions for error handling
def handle_database_error(operation: str, error: Exception) -> DatabaseError:
    """Convert database errors to structured application errors."""
    logger.error(f"Database error during {operation}: {str(error)}")
    return DatabaseError(f"Database operation failed: {operation}")


def handle_external_service_error(service_name: str, operation: str, error: Exception) -> ExternalServiceError:
    """Convert external service errors to structured application errors."""
    logger.error(f"External service error - {service_name} {operation}: {str(error)}")
    return ExternalServiceError(
        f"External service error: {operation}",
        service_name=service_name,
        details={"original_error": str(error)}
    )


def validate_required_field(value: Any, field_name: str) -> None:
    """Validate that a required field is present and not empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required", field=field_name)


def validate_positive_integer(value: int, field_name: str) -> None:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer", field=field_name)


def validate_email_format(email: str) -> None:
    """Basic email format validation."""
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format", field="email")


# Context manager for error handling
class ErrorContext:
    """Context manager for consistent error handling in operations."""
    
    def __init__(self, operation: str, logger_instance: Optional[Any] = None):
        self.operation = operation
        self.logger = logger_instance or logger
    
    def __enter__(self):
        self.logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.debug(f"Operation completed successfully: {self.operation}")
        else:
            self.logger.error(f"Operation failed: {self.operation}", exception=str(exc_val))
        return False  # Don't suppress exceptions