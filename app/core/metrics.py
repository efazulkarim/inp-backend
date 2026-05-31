"""
Metrics Collection and Monitoring

Provides application metrics collection and monitoring capabilities.
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    count: int
    sum: float
    min: float
    max: float
    avg: float
    
    @classmethod
    def from_values(cls, values: List[float]) -> 'MetricSummary':
        """Create summary from list of values."""
        if not values:
            return cls(0, 0.0, 0.0, 0.0, 0.0)
        
        return cls(
            count=len(values),
            sum=sum(values),
            min=min(values),
            max=max(values),
            avg=sum(values) / len(values)
        )


class MetricsCollector:
    """Collect and store application metrics."""
    
    def __init__(self, max_points: int = 10000, retention_hours: int = 24):
        self.max_points = max_points
        self.retention_seconds = retention_hours * 3600
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            self._add_point(name, self.counters[key], labels)
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            self._add_point(name, value, labels)
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a value to a histogram metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            # Keep only recent values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            self._add_point(name, value, labels)
    
    def timing(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a timing metric (alias for histogram)."""
        self.histogram(name, duration, labels)
    
    def _add_point(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a metric point to storage."""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        )
        self.metrics[name].append(point)
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create a unique key for metric with labels."""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    
    def get_metric_summary(self, name: str, since: Optional[float] = None) -> Optional[MetricSummary]:
        """Get summary statistics for a metric."""
        if name not in self.metrics:
            return None
        
        since_time = since or (time.time() - 3600)  # Last hour by default
        
        values = [
            point.value for point in self.metrics[name]
            if point.timestamp >= since_time
        ]
        
        return MetricSummary.from_values(values)
    
    def get_counter_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0.0)
    
    def get_gauge_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        return self.gauges.get(key)
    
    def get_histogram_summary(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[MetricSummary]:
        """Get histogram summary statistics."""
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])
        return MetricSummary.from_values(values) if values else None
    
    def cleanup_old_metrics(self):
        """Remove old metric points."""
        cutoff_time = time.time() - self.retention_seconds
        
        with self._lock:
            for name, points in self.metrics.items():
                # Remove old points
                while points and points[0].timestamp < cutoff_time:
                    points.popleft()
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                name: MetricSummary.from_values(values).__dict__
                for name, values in self.histograms.items()
            },
            "timestamp": time.time()
        }


# Global metrics collector
metrics = MetricsCollector()


class SystemMetricsCollector:
    """Collect system-level metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._process = psutil.Process()
    
    def collect_system_metrics(self):
        """Collect current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.metrics.gauge("system.cpu.usage_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.metrics.gauge("system.memory.usage_percent", memory.percent)
            self.metrics.gauge("system.memory.available_bytes", memory.available)
            self.metrics.gauge("system.memory.used_bytes", memory.used)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.metrics.gauge("system.disk.usage_percent", (disk.used / disk.total) * 100)
            self.metrics.gauge("system.disk.free_bytes", disk.free)
            
            # Process metrics
            process_memory = self._process.memory_info()
            self.metrics.gauge("process.memory.rss_bytes", process_memory.rss)
            self.metrics.gauge("process.memory.vms_bytes", process_memory.vms)
            
            process_cpu = self._process.cpu_percent()
            self.metrics.gauge("process.cpu.usage_percent", process_cpu)
            
            # File descriptor count (Unix only)
            try:
                fd_count = self._process.num_fds()
                self.metrics.gauge("process.file_descriptors", fd_count)
            except (AttributeError, psutil.AccessDenied):
                pass
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine health status
            health_issues = []
            
            if cpu_percent > 90:
                health_issues.append("High CPU usage")
            if memory.percent > 90:
                health_issues.append("High memory usage")
            if (disk.used / disk.total) > 0.9:
                health_issues.append("Low disk space")
            
            status = "unhealthy" if health_issues else "healthy"
            
            return {
                "status": status,
                "issues": health_issues,
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "uptime_seconds": time.time() - psutil.boot_time()
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {
                "status": "unknown",
                "error": str(e),
                "timestamp": time.time()
            }


# Global system metrics collector
system_metrics = SystemMetricsCollector(metrics)


class ApplicationMetrics:
    """Application-specific metrics collection."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    def record_request(self, method: str, path: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        labels = {
            "method": method,
            "path": path,
            "status_code": str(status_code)
        }
        
        self.metrics.counter("http.requests.total", labels=labels)
        self.metrics.histogram("http.request.duration_seconds", duration, labels=labels)
        
        # Record error rates
        if status_code >= 400:
            self.metrics.counter("http.requests.errors", labels=labels)
    
    def record_database_query(self, operation: str, table: str, duration: float):
        """Record database query metrics."""
        labels = {
            "operation": operation,
            "table": table
        }
        
        self.metrics.counter("database.queries.total", labels=labels)
        self.metrics.histogram("database.query.duration_seconds", duration, labels=labels)
    
    def record_business_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record business-specific metrics."""
        self.metrics.gauge(f"business.{metric_name}", value, labels)
    
    def record_user_action(self, action: str, user_id: Optional[int] = None):
        """Record user action metrics."""
        labels = {"action": action}
        if user_id:
            labels["user_id"] = str(user_id)
        
        self.metrics.counter("user.actions.total", labels=labels)
    
    def get_application_summary(self) -> Dict[str, Any]:
        """Get application metrics summary."""
        now = time.time()
        hour_ago = now - 3600
        
        return {
            "requests": {
                "total_last_hour": self._get_counter_since("http.requests.total", hour_ago),
                "errors_last_hour": self._get_counter_since("http.requests.errors", hour_ago),
                "avg_duration": self._get_avg_duration("http.request.duration_seconds", hour_ago)
            },
            "database": {
                "queries_last_hour": self._get_counter_since("database.queries.total", hour_ago),
                "avg_query_duration": self._get_avg_duration("database.query.duration_seconds", hour_ago)
            },
            "users": {
                "actions_last_hour": self._get_counter_since("user.actions.total", hour_ago)
            },
            "timestamp": now
        }
    
    def _get_counter_since(self, name: str, since: float) -> int:
        """Get counter value since timestamp."""
        if name not in self.metrics.metrics:
            return 0
        
        count = sum(
            1 for point in self.metrics.metrics[name]
            if point.timestamp >= since
        )
        return count
    
    def _get_avg_duration(self, name: str, since: float) -> float:
        """Get average duration since timestamp."""
        if name not in self.metrics.metrics:
            return 0.0
        
        values = [
            point.value for point in self.metrics.metrics[name]
            if point.timestamp >= since
        ]
        
        return sum(values) / len(values) if values else 0.0


# Global application metrics
app_metrics = ApplicationMetrics(metrics)


def timing_decorator(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to time function execution."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics.timing(metric_name, duration, labels)
        return wrapper
    return decorator


def counter_decorator(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to count function calls."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            metrics.counter(metric_name, labels=labels)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Periodic metrics collection
class MetricsScheduler:
    """Schedule periodic metrics collection."""
    
    def __init__(self, interval: int = 60):
        self.interval = interval
        self.running = False
        self._thread = None
    
    def start(self):
        """Start periodic metrics collection."""
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        logger.info("Metrics collection started")
    
    def stop(self):
        """Stop periodic metrics collection."""
        self.running = False
        if self._thread:
            self._thread.join()
        logger.info("Metrics collection stopped")
    
    def _collect_loop(self):
        """Main collection loop."""
        while self.running:
            try:
                system_metrics.collect_system_metrics()
                metrics.cleanup_old_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {str(e)}")
                time.sleep(self.interval)


# Global metrics scheduler
metrics_scheduler = MetricsScheduler()


def get_metrics_summary() -> Dict[str, Any]:
    """Get comprehensive metrics summary."""
    return {
        "system": system_metrics.get_system_health_status(),
        "application": app_metrics.get_application_summary(),
        "all_metrics": metrics.get_all_metrics()
    }