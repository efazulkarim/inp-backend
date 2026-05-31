"""
Database Performance Monitoring

Utilities for monitoring database query performance and health.
"""

import time
import functools
from typing import Dict, Any, List, Optional, Callable
from contextlib import contextmanager
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from app.core.logging import get_logger

logger = get_logger(__name__)


class QueryPerformanceMonitor:
    """Monitor database query performance."""
    
    def __init__(self):
        self.slow_queries: List[Dict[str, Any]] = []
        self.query_stats: Dict[str, Dict[str, Any]] = {}
        self.slow_query_threshold = 1.0  # seconds
        self.max_stored_queries = 100
    
    def record_query(self, query: str, duration: float, params: Optional[Dict] = None):
        """Record a query execution."""
        query_hash = hash(query)
        
        # Update statistics
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = {
                "query": query[:200] + "..." if len(query) > 200 else query,
                "count": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "max_duration": 0.0,
                "min_duration": float('inf')
            }
        
        stats = self.query_stats[query_hash]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["avg_duration"] = stats["total_duration"] / stats["count"]
        stats["max_duration"] = max(stats["max_duration"], duration)
        stats["min_duration"] = min(stats["min_duration"], duration)
        
        # Record slow queries
        if duration > self.slow_query_threshold:
            slow_query = {
                "query": query,
                "duration": duration,
                "params": params,
                "timestamp": time.time()
            }
            
            self.slow_queries.append(slow_query)
            
            # Keep only recent slow queries
            if len(self.slow_queries) > self.max_stored_queries:
                self.slow_queries = self.slow_queries[-self.max_stored_queries:]
            
            logger.warning(f"Slow query detected: {duration:.3f}s - {query[:100]}...")
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent slow queries."""
        return sorted(
            self.slow_queries[-limit:],
            key=lambda x: x["duration"],
            reverse=True
        )
    
    def get_query_statistics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get query statistics sorted by average duration."""
        stats_list = list(self.query_stats.values())
        return sorted(
            stats_list,
            key=lambda x: x["avg_duration"],
            reverse=True
        )[:limit]
    
    def reset_statistics(self):
        """Reset all collected statistics."""
        self.slow_queries.clear()
        self.query_stats.clear()
        logger.info("Query performance statistics reset")


# Global monitor instance
query_monitor = QueryPerformanceMonitor()


def setup_query_monitoring(engine: Engine):
    """Set up SQLAlchemy event listeners for query monitoring."""
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - context._query_start_time
        query_monitor.record_query(statement, total_time, parameters)


@contextmanager
def monitor_query_performance(description: str = "Query"):
    """Context manager for monitoring specific query performance."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if duration > query_monitor.slow_query_threshold:
            logger.warning(f"Slow {description}: {duration:.3f}s")


def query_performance_decorator(description: str = None):
    """Decorator for monitoring function query performance."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            desc = description or f"{func.__module__}.{func.__name__}"
            with monitor_query_performance(desc):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class DatabaseHealthChecker:
    """Check database health and performance metrics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_connection_health(self) -> Dict[str, Any]:
        """Check database connection health."""
        try:
            start_time = time.time()
            result = self.db.execute(text("SELECT 1")).scalar()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy" if result == 1 else "unhealthy",
                "response_time": round(response_time * 1000, 2),  # ms
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        try:
            pool = self.db.get_bind().pool
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
        except Exception as e:
            logger.error(f"Failed to get pool stats: {str(e)}")
            return {"error": str(e)}
    
    def check_table_sizes(self) -> Dict[str, Any]:
        """Check table sizes and row counts."""
        try:
            tables = [
                "users", "ideaboards", "questionnaires", "answers", 
                "reports", "customer_personas", "subscriptions"
            ]
            
            table_stats = {}
            for table in tables:
                try:
                    result = self.db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    table_stats[table] = result
                except Exception as e:
                    table_stats[table] = f"Error: {str(e)}"
            
            return table_stats
        except Exception as e:
            logger.error(f"Failed to check table sizes: {str(e)}")
            return {"error": str(e)}
    
    def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze current query performance metrics."""
        return {
            "slow_queries_count": len(query_monitor.slow_queries),
            "total_queries_tracked": len(query_monitor.query_stats),
            "slow_query_threshold": query_monitor.slow_query_threshold,
            "recent_slow_queries": query_monitor.get_slow_queries(5),
            "top_slow_queries": query_monitor.get_query_statistics(5)
        }


def get_database_performance_report(db: Session) -> Dict[str, Any]:
    """Generate a comprehensive database performance report."""
    health_checker = DatabaseHealthChecker(db)
    
    return {
        "timestamp": time.time(),
        "connection_health": health_checker.check_connection_health(),
        "pool_stats": health_checker.get_connection_pool_stats(),
        "table_stats": health_checker.check_table_sizes(),
        "query_performance": health_checker.analyze_query_performance()
    }


# Utility functions for common performance checks
def check_slow_queries_alert(threshold_count: int = 10) -> bool:
    """Check if slow queries exceed threshold and should trigger alert."""
    return len(query_monitor.slow_queries) > threshold_count


def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics for monitoring."""
    return {
        "slow_queries_count": len(query_monitor.slow_queries),
        "queries_tracked": len(query_monitor.query_stats),
        "avg_query_time": sum(
            stats["avg_duration"] for stats in query_monitor.query_stats.values()
        ) / len(query_monitor.query_stats) if query_monitor.query_stats else 0
    }