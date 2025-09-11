# app/main.py
import os
import secrets
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.database import engine, Base
from app.routers import auth_routes, user_routes, answer_routes, ideaboard_routes, trash_routes, archive_routes, report_routes, customerboard_routes, stripe_routes
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging, CorrelationIDMiddleware, get_logger
from app.core.exceptions import (
    app_exception_handler, validation_exception_handler, 
    http_exception_handler, general_exception_handler,
    AppException, ValidationError
)
from app.core.database_monitoring import setup_query_monitoring
from app.core.metrics import metrics_scheduler, app_metrics, get_metrics_summary
from app.middleware.security import (
    SecurityHeadersMiddleware, 
    RequestSanitizationMiddleware, 
    RateLimitingMiddleware,
    get_security_middleware_config
)
from fastapi import HTTPException

# Initialize configuration and logging
settings = get_settings()
setup_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

app = FastAPI(
    title="InsightPilot API",
    description="API for InsightPilot idea management platform",
    version="1.0.0",
    debug=settings.debug
)

# Setup database query monitoring
setup_query_monitoring(engine)

# Get security middleware configuration
security_config = get_security_middleware_config()

# Add security middleware (order matters - add from innermost to outermost)
app.add_middleware(
    RateLimitingMiddleware,
    config=security_config["rate_limiting"]
)

app.add_middleware(
    RequestSanitizationMiddleware,
    config=security_config["sanitization"]
)

app.add_middleware(
    SecurityHeadersMiddleware,
    config=security_config["security_headers"]
)

# Add correlation ID middleware for request tracking
app.add_middleware(CorrelationIDMiddleware)

# Add request metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record request metrics
    duration = time.time() - start_time
    app_metrics.record_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=duration
    )
    
    return response

# Add SessionMiddleware for OAuth (required by Authlib)
SESSION_SECRET_KEY = settings.session_secret_key or secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# CORS middleware configuration
origins = settings.allowed_origins
if settings.is_production:
    # In production, use configured origins only
    pass
else:
    # In development, allow additional origins
    origins.extend(["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*", "x-correlation-id"]  # Allow frontend to read correlation ID
)

# Add exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting InsightPilot API...")
    
    # Start metrics collection
    metrics_scheduler.start()
    
    logger.info("InsightPilot API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down InsightPilot API...")
    
    # Stop metrics collection
    metrics_scheduler.stop()
    
    logger.info("InsightPilot API shutdown complete")


@app.get("/")
def read_root():
    return {
        "message": "InsightPilot API is running!",
        "version": "1.0.0",
        "environment": settings.environment,
        "status": "healthy"
    }


@app.get("/metrics")
def get_application_metrics():
    """Get application metrics (for monitoring)."""
    return get_metrics_summary()

# Comment out automatic table creation to avoid conflicts with Alembic migrations
# Use Alembic migrations instead for database schema management
# Base.metadata.create_all(bind=engine)

# Include health check routes
app.include_router(health_router, prefix="/health", tags=["health"])

# Include the authentication and user routes
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/user", tags=["user"])
app.include_router(answer_routes.router, prefix="/api/answer", tags=["answer"])
app.include_router(ideaboard_routes.router, prefix="/api/ideaboard", tags=["ideaboard"])
app.include_router(trash_routes.router, prefix="/api/trash", tags=["trash"])
app.include_router(archive_routes.router, prefix="/archive", tags=["Archive"])
app.include_router(report_routes.router, prefix="/api/report", tags=["report"])
app.include_router(customerboard_routes.router, prefix="/api/customerboard", tags=["customerboard"])
app.include_router(stripe_routes.router, prefix="/api/stripe", tags=["stripe"])


@auth_routes.router.get("/debug-oauth")
async def debug_oauth():
    return {
        "frontend_url": settings.frontend_url,
        "google_redirect_uri": settings.google_redirect_uri,
        "environment": settings.environment
    }