"""
Performance monitoring utilities for the unified logging system.

Provides tools for monitoring and analyzing application performance.
"""

from typing import Dict, List, Any, Optional, Callable
import time
import threading
from contextlib import contextmanager
from logging_system import get_logger, log_performance


class PerformanceMonitor:
    """Monitor application performance metrics"""

    def __init__(self):
        self.logger = get_logger("performance_monitor")
        self.metrics = {}
        self._lock = threading.Lock()

    @contextmanager
    def measure_time(self, operation: str, log_threshold: float = None):
        """Context manager to measure operation duration"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            log_performance(operation, duration)

            if log_threshold and duration > log_threshold:
                self.logger.warning(f"Slow operation detected: {operation} took {duration:.2f}ms")

    def time_function(self, func: Callable) -> Callable:
        """Decorator to time function execution"""
        def wrapper(*args, **kwargs):
            with self.measure_time(f"{func.__module__}.{func.__qualname__}"):
                return func(*args, **kwargs)
        return wrapper

    def record_metric(self, name: str, value: float, tags: Dict[str, Any] = None):
        """Record a custom metric"""
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = []

            metric_data = {
                'timestamp': time.time(),
                'value': value,
                'tags': tags or {}
            }

            self.metrics[name].append(metric_data)

            # Keep only last 1000 entries
            if len(self.metrics[name]) > 1000:
                self.metrics[name] = self.metrics[name][-1000:]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of recorded metrics"""
        summary = {}
        with self._lock:
            for name, data in self.metrics.items():
                if data:
                    values = [d['value'] for d in data]
                    summary[name] = {
                        'count': len(values),
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'latest': values[-1]
                    }
        return summary