"""
Health check and monitoring endpoints for system observability.
Provides comprehensive health status and system metrics.
"""
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from ..database import get_db
from ..core.config import get_config, Settings
from ..core.logging import get_logger
from ..core.exceptions import DatabaseError, ExternalServiceError
from ..core.database_monitoring import get_database_performance_report
from ..core.metrics import get_metrics_summary

logger = get_logger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    version: str = "1.0.0"
    environment: str
    uptime_seconds: float
    checks: Dict[str, Any]


class SystemMetrics(BaseModel):
    """System metrics response model."""
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_available_gb: float
    active_connections: int
    timestamp: datetime


class DatabaseHealth(BaseModel):
    """Database health check model."""
    status: str
    response_time_ms: float
    connection_pool_size: int
    active_connections: int
    error: Optional[str] = None


# Application start time for uptime calculation
app_start_time = time.time()


async def check_database_health(db: Session) -> DatabaseHealth:
    """Check database connectivity and performance."""
    start_time = time.time()
    
    try:
        # Simple connectivity test
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        
        # Get connection pool information
        engine = db.get_bind()
        pool = engine.pool
        
        response_time = (time.time() - start_time) * 1000
        
        return DatabaseHealth(
            status="healthy" if response_time < 1000 else "degraded",
            response_time_ms=round(response_time, 2),
            connection_pool_size=pool.size(),
            active_connections=pool.checkedout()
        )
    
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return DatabaseHealth(
            status="unhealthy",
            response_time_ms=(time.time() - start_time) * 1000,
            connection_pool_size=0,
            active_connections=0,
            error=str(e)
        )


def get_system_metrics() -> SystemMetrics:
    """Get current system resource metrics."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_mb = memory.available / (1024 * 1024)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_available_gb = disk.free / (1024 * 1024 * 1024)
        
        # Network connections (approximate active connections)
        connections = len(psutil.net_connections())
        
        return SystemMetrics(
            cpu_usage_percent=round(cpu_percent, 2),
            memory_usage_percent=round(memory_percent, 2),
            memory_available_mb=round(memory_available_mb, 2),
            disk_usage_percent=round(disk_percent, 2),
            disk_available_gb=round(disk_available_gb, 2),
            active_connections=connections,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        raise ExternalServiceError("Failed to retrieve system metrics")


@router.get("/health", response_model=HealthStatus)
async def health_check(
    db: Session = Depends(get_db),
    config: Settings = Depends(get_config)
):
    """
    Comprehensive health check endpoint.
    Returns overall system health status and individual component checks.
    """
    start_time = time.time()
    checks = {}
    overall_status = "healthy"
    
    try:
        # Database health check
        db_health = await check_database_health(db)
        checks["database"] = db_health.dict()
        
        if db_health.status != "healthy":
            overall_status = "degraded" if db_health.status == "degraded" else "unhealthy"
        
        # System resources check
        try:
            system_metrics = get_system_metrics()
            checks["system"] = {
                "status": "healthy",
                "cpu_usage": system_metrics.cpu_usage_percent,
                "memory_usage": system_metrics.memory_usage_percent,
                "disk_usage": system_metrics.disk_usage_percent
            }
            
            # Mark as degraded if resources are high
            if (system_metrics.cpu_usage_percent > 80 or 
                system_metrics.memory_usage_percent > 85 or 
                system_metrics.disk_usage_percent > 90):
                checks["system"]["status"] = "degraded"
                if overall_status == "healthy":
                    overall_status = "degraded"
        
        except Exception as e:
            checks["system"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"
        
        # Configuration check
        checks["configuration"] = {
            "status": "healthy",
            "environment": config.environment,
            "debug_mode": config.debug
        }
        
        # Calculate uptime
        uptime = time.time() - app_start_time
        
        response = HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            environment=config.environment,
            uptime_seconds=round(uptime, 2),
            checks=checks
        )
        
        # Log health check
        duration = (time.time() - start_time) * 1000
        logger.info(
            f"Health check completed",
            status=overall_status,
            duration_ms=round(duration, 2)
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/health/live")
async def liveness_probe():
    """
    Simple liveness probe for container orchestration.
    Returns 200 if the application is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/health/ready")
async def readiness_probe(db: Session = Depends(get_db)):
    """
    Readiness probe for container orchestration.
    Returns 200 if the application is ready to serve traffic.
    """
    try:
        # Quick database connectivity check
        db.execute(text("SELECT 1"))
        return {"status": "ready", "timestamp": datetime.utcnow()}
    
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/metrics", response_model=SystemMetrics)
async def get_metrics():
    """
    Get current system metrics for monitoring.
    Provides detailed resource usage information.
    """
    try:
        metrics = get_system_metrics()
        logger.debug("System metrics retrieved successfully")
        return metrics
    
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/health/database")
async def database_health_detailed(db: Session = Depends(get_db)):
    """
    Detailed database health check with connection pool information.
    """
    try:
        db_health = await check_database_health(db)
        
        # Additional database statistics
        try:
            # Get table count
            result = db.execute(text("""
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
            """))
            table_count = result.fetchone()[0]
            
            # Get database size (MySQL specific)
            result = db.execute(text("""
                SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS db_size_mb
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
            """))
            db_size_mb = result.fetchone()[0] or 0
            
            additional_info = {
                "table_count": table_count,
                "database_size_mb": float(db_size_mb)
            }
            
        except Exception as e:
            logger.warning(f"Could not get additional database info: {str(e)}")
            additional_info = {}
        
        response = db_health.dict()
        response.update(additional_info)
        
        return response
    
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database health check failed")


@router.get("/health/version")
async def version_info(config: Settings = Depends(get_config)):
    """
    Get application version and environment information.
    """
    return {
        "version": "1.0.0",
        "environment": config.environment,
        "debug": config.debug,
        "timestamp": datetime.utcnow(),
        "uptime_seconds": round(time.time() - app_start_time, 2)
    }


@router.get("/health/performance")
async def performance_report(db: Session = Depends(get_db)):
    """
    Get comprehensive database performance report.
    """
    try:
        report = get_database_performance_report(db)
        return report
    except Exception as e:
        logger.error(f"Performance report failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Performance report failed")


@router.get("/health/metrics-summary")
async def metrics_summary():
    """
    Get comprehensive application metrics summary.
    """
    try:
        summary = get_metrics_summary()
        return summary
    except Exception as e:
        logger.error(f"Metrics summary failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Metrics summary failed")