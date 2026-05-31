"""
Structured logging system with correlation IDs and enhanced formatting.
Provides consistent logging across the application with request tracking.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from fastapi import Request
import structlog


# Context variable for correlation ID tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIDProcessor:
    """Processor to add correlation ID to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        correlation_id = correlation_id_var.get()
        if correlation_id:
            event_dict['correlation_id'] = correlation_id
        return event_dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_entry['correlation_id'] = correlation_id
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage']:
                log_entry[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Enhanced text formatter with correlation ID."""
    
    def format(self, record):
        correlation_id = correlation_id_var.get()
        correlation_part = f" [{correlation_id}]" if correlation_id else ""
        
        formatted = super().format(record)
        return f"{formatted}{correlation_part}"


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Setup application logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            CorrelationIDProcessor(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    if log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        formatter = TextFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class Logger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self._name = name
    
    def debug(self, message: str, **kwargs):
        """Log debug message with additional context."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with additional context."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with additional context."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with additional context."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with additional context."""
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)
    
    def bind(self, **kwargs) -> 'Logger':
        """Create a new logger with bound context."""
        bound_logger = Logger(self._name)
        bound_logger.logger = self.logger.bind(**kwargs)
        return bound_logger


def get_logger(name: str) -> Logger:
    """Get a logger instance for the given name."""
    return Logger(name)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    correlation_id_var.set(None)


# Middleware for correlation ID tracking
class CorrelationIDMiddleware:
    """Middleware to add correlation ID to requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate or extract correlation ID
            correlation_id = None
            
            # Check if correlation ID is provided in headers
            headers = dict(scope.get("headers", []))
            correlation_header = headers.get(b"x-correlation-id")
            
            if correlation_header:
                correlation_id = correlation_header.decode("utf-8")
            else:
                correlation_id = generate_correlation_id()
            
            # Set correlation ID in context
            set_correlation_id(correlation_id)
            
            # Add correlation ID to response headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append([b"x-correlation-id", correlation_id.encode("utf-8")])
                    message["headers"] = headers
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                clear_correlation_id()
        else:
            await self.app(scope, receive, send)


# Performance logging utilities
class PerformanceLogger:
    """Logger for performance monitoring."""
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_request_duration(self, method: str, path: str, duration: float, status_code: int):
        """Log request duration and details."""
        self.logger.info(
            "Request completed",
            method=method,
            path=path,
            duration_ms=round(duration * 1000, 2),
            status_code=status_code
        )
    
    def log_database_query(self, query: str, duration: float, rows_affected: int = None):
        """Log database query performance."""
        self.logger.debug(
            "Database query executed",
            query=query[:200] + "..." if len(query) > 200 else query,
            duration_ms=round(duration * 1000, 2),
            rows_affected=rows_affected
        )
    
    def log_external_api_call(self, service: str, endpoint: str, duration: float, status_code: int):
        """Log external API call performance."""
        self.logger.info(
            "External API call completed",
            service=service,
            endpoint=endpoint,
            duration_ms=round(duration * 1000, 2),
            status_code=status_code
        )


# Global performance logger instance
performance_logger = PerformanceLogger()