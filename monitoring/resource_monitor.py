"""
Comprehensive Resource Monitoring System for MAMcrawler

This module provides real-time system resource monitoring, performance metrics collection,
alert management, and automated optimization for the crawler infrastructure.

Author: Audiobook Automation System
Version: 1.0.0
"""

import asyncio
import gc
import logging
import os
import psutil
import threading
import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
import weakref


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ResourceType(Enum):
    """Resource types to monitor."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    THREADS = "threads"
    FILES = "files"
    DATABASE_CONNECTIONS = "db_connections"
    CACHE = "cache"
    QUEUE_SIZE = "queue_size"


@dataclass
class ResourceMetric:
    """Individual resource metric."""
    resource_type: ResourceType
    value: float
    timestamp: datetime
    unit: str
    threshold: Optional[float] = None
    status: str = "normal"  # normal, warning, critical
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert definition."""
    id: str
    severity: AlertSeverity
    resource_type: ResourceType
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringConfig:
    """Monitoring system configuration."""
    # Collection intervals (seconds)
    cpu_interval: float = 5.0
    memory_interval: float = 10.0
    disk_interval: float = 30.0
    network_interval: float = 15.0
    custom_interval: float = 5.0
    
    # Alert thresholds
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 80.0
    memory_critical: float = 95.0
    disk_warning: float = 85.0
    disk_critical: float = 95.0
    
    # History settings
    max_history_points: int = 10000
    history_retention_hours: int = 24
    
    # Alert settings
    enable_alerts: bool = True
    alert_cooldown_seconds: int = 300  # 5 minutes
    max_alerts_per_hour: int = 100
    
    # Performance optimization
    enable_auto_gc: bool = True
    gc_threshold_mb: int = 500
    enable_memory_pooling: bool = True
    
    # Export settings
    export_prometheus: bool = True
    export_statsd: bool = False
    export_json: bool = True
    
    # External monitoring
    external_endpoints: List[str] = field(default_factory=list)


class SystemMonitor:
    """Real-time system resource monitor."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.logger = logging.getLogger("system_monitor")
        
        # Data storage
        self.metrics_history: Dict[ResourceType, deque] = defaultdict(
            lambda: deque(maxlen=config.max_history_points)
        )
        self.alerts: List[Alert] = []
        self.active_alerts: Dict[str, Alert] = {}
        
        # Monitoring state
        self._monitoring = False
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._last_collection: Dict[str, datetime] = {}
        
        # Performance tracking
        self.collection_times: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # Statistics
        self.stats = {
            "total_collections": 0,
            "total_alerts": 0,
            "resolved_alerts": 0,
            "avg_collection_time": 0.0,
            "peak_cpu": 0.0,
            "peak_memory": 0.0,
            "peak_disk": 0.0
        }
        
        # Thread pool for blocking operations
        self._executor = threading.ThreadPoolExecutor(max_workers=2)
    
    async def start_monitoring(self):
        """Start all monitoring tasks."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self.logger.info("Starting system monitoring")
        
        # Start monitoring tasks
        self._monitoring_tasks["cpu"] = asyncio.create_task(self._monitor_cpu())
        self._monitoring_tasks["memory"] = asyncio.create_task(self._monitor_memory())
        self._monitoring_tasks["disk"] = asyncio.create_task(self._monitor_disk())
        self._monitoring_tasks["network"] = asyncio.create_task(self._monitor_network())
        
        # Auto GC task
        if self.config.enable_auto_gc:
            self._monitoring_tasks["gc"] = asyncio.create_task(self._monitor_gc())
        
        # Cleanup task
        self._monitoring_tasks["cleanup"] = asyncio.create_task(self._cleanup_old_data())
    
    async def stop_monitoring(self):
        """Stop all monitoring tasks."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self.logger.info("Stopping system monitoring")
        
        # Cancel all tasks
        for task in self._monitoring_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks.values(), return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._executor.shutdown(wait=True)
    
    async def _monitor_cpu(self):
        """Monitor CPU usage."""
        while self._monitoring:
            start_time = time.time()
            
            try:
                # Get CPU usage
                cpu_percent = await self._get_cpu_usage()
                cpu_count = psutil.cpu_count()
                
                # Create metric
                metric = ResourceMetric(
                    resource_type=ResourceType.CPU,
                    value=cpu_percent,
                    timestamp=datetime.now(),
                    unit="percent",
                    threshold=self.config.cpu_critical
                )
                
                self.metrics_history[ResourceType.CPU].append(metric)
                
                # Check for alerts
                await self._check_alerts(ResourceType.CPU, cpu_percent, self.config.cpu_warning, self.config.cpu_critical)
                
                # Update stats
                self.stats["peak_cpu"] = max(self.stats["peak_cpu"], cpu_percent)
                
                # Record collection time
                collection_time = time.time() - start_time
                self.collection_times["cpu"].append(collection_time)
                
            except Exception as e:
                self.logger.error(f"CPU monitoring error: {e}")
            
            await asyncio.sleep(self.config.cpu_interval)
    
    async def _monitor_memory(self):
        """Monitor memory usage."""
        while self._monitoring:
            start_time = time.time()
            
            try:
                # Get memory usage
                memory_info = psutil.virtual_memory()
                memory_percent = memory_info.percent
                memory_used_mb = memory_info.used / (1024 * 1024)
                memory_available_mb = memory_info.available / (1024 * 1024)
                
                # Create metric
                metric = ResourceMetric(
                    resource_type=ResourceType.MEMORY,
                    value=memory_percent,
                    timestamp=datetime.now(),
                    unit="percent",
                    threshold=self.config.memory_critical,
                    metadata={
                        "used_mb": memory_used_mb,
                        "available_mb": memory_available_mb,
                        "total_mb": memory_info.total / (1024 * 1024)
                    }
                )
                
                self.metrics_history[ResourceType.MEMORY].append(metric)
                
                # Check for alerts
                await self._check_alerts(ResourceType.MEMORY, memory_percent, self.config.memory_warning, self.config.memory_critical)
                
                # Update stats
                self.stats["peak_memory"] = max(self.stats["peak_memory"], memory_percent)
                
                # Trigger auto GC if needed
                if self.config.enable_auto_gc and memory_used_mb > self.config.gc_threshold_mb:
                    await self._trigger_gc()
                
                # Record collection time
                collection_time = time.time() - start_time
                self.collection_times["memory"].append(collection_time)
                
            except Exception as e:
                self.logger.error(f"Memory monitoring error: {e}")
            
            await asyncio.sleep(self.config.memory_interval)
    
    async def _monitor_disk(self):
        """Monitor disk usage."""
        while self._monitoring:
            start_time = time.time()
            
            try:
                # Get disk usage
                disk_usage = psutil.disk_usage('/')
                disk_percent = (disk_usage.used / disk_usage.total) * 100
                
                # Create metric
                metric = ResourceMetric(
                    resource_type=ResourceType.DISK,
                    value=disk_percent,
                    timestamp=datetime.now(),
                    unit="percent",
                    threshold=self.config.disk_critical,
                    metadata={
                        "used_gb": disk_usage.used / (1024**3),
                        "free_gb": disk_usage.free / (1024**3),
                        "total_gb": disk_usage.total / (1024**3)
                    }
                )
                
                self.metrics_history[ResourceType.DISK].append(metric)
                
                # Check for alerts
                await self._check_alerts(ResourceType.DISK, disk_percent, self.config.disk_warning, self.config.disk_critical)
                
                # Update stats
                self.stats["peak_disk"] = max(self.stats["peak_disk"], disk_percent)
                
                # Record collection time
                collection_time = time.time() - start_time
                self.collection_times["disk"].append(collection_time)
                
            except Exception as e:
                self.logger.error(f"Disk monitoring error: {e}")
            
            await asyncio.sleep(self.config.disk_interval)
    
    async def _monitor_network(self):
        """Monitor network usage."""
        while self._monitoring:
            start_time = time.time()
            
            try:
                # Get network I/O stats
                network_io = psutil.net_io_counters()
                bytes_sent = network_io.bytes_sent
                bytes_recv = network_io.bytes_recv
                
                # Calculate rates (this would need previous values for rate calculation)
                # For now, just log the absolute values
                metric = ResourceMetric(
                    resource_type=ResourceType.NETWORK,
                    value=bytes_recv + bytes_sent,
                    timestamp=datetime.now(),
                    unit="bytes",
                    metadata={
                        "bytes_sent": bytes_sent,
                        "bytes_recv": bytes_recv,
                        "packets_sent": network_io.packets_sent,
                        "packets_recv": network_io.packets_recv
                    }
                )
                
                self.metrics_history[ResourceType.NETWORK].append(metric)
                
                # Record collection time
                collection_time = time.time() - start_time
                self.collection_times["network"].append(collection_time)
                
            except Exception as e:
                self.logger.error(f"Network monitoring error: {e}")
            
            await asyncio.sleep(self.config.network_interval)
    
    async def _monitor_gc(self):
        """Monitor and trigger garbage collection."""
        while self._monitoring:
            try:
                # Force garbage collection
                collected = gc.collect()
                
                if collected > 0:
                    self.logger.debug(f"Garbage collection freed {collected} objects")
                
            except Exception as e:
                self.logger.error(f"GC monitoring error: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _cleanup_old_data(self):
        """Cleanup old metrics and alerts."""
        while self._monitoring:
            try:
                cutoff_time = datetime.now() - timedelta(hours=self.config.history_retention_hours)
                
                # Clean up old metrics
                for resource_type in self.metrics_history:
                    # Remove old entries
                    while (self.metrics_history[resource_type] and 
                           self.metrics_history[resource_type][0].timestamp < cutoff_time):
                        self.metrics_history[resource_type].popleft()
                
                # Clean up old alerts
                self.alerts = [
                    alert for alert in self.alerts 
                    if alert.timestamp > cutoff_time
                ]
                
                # Clean up resolved alerts
                self.active_alerts = {
                    alert_id: alert for alert_id, alert in self.active_alerts.items()
                    if alert.timestamp > cutoff_time
                }
                
                self.logger.debug("Cleanup completed")
                
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
            
            await asyncio.sleep(3600)  # Clean up every hour
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, psutil.cpu_percent, 1.0)
    
    async def _trigger_gc(self):
        """Trigger garbage collection."""
        self.logger.info("Triggering garbage collection due to high memory usage")
        collected = gc.collect()
        self.logger.info(f"Garbage collection freed {collected} objects")
    
    async def _check_alerts(self, resource_type: ResourceType, value: float, 
                           warning_threshold: float, critical_threshold: float):
        """Check if value triggers any alerts."""
        if not self.config.enable_alerts:
            return
        
        # Determine status
        if value >= critical_threshold:
            status = "critical"
            severity = AlertSeverity.CRITICAL
        elif value >= warning_threshold:
            status = "warning"
            severity = AlertSeverity.WARNING
        else:
            # Check if we should resolve existing alerts
            await self._resolve_alert(resource_type)
            return
        
        # Check cooldown
        alert_key = f"{resource_type.value}_{status}"
        if alert_key in self.active_alerts:
            last_alert = self.active_alerts[alert_key]
            if (datetime.now() - last_alert.timestamp).total_seconds() < self.config.alert_cooldown_seconds:
                return
        
        # Create alert
        alert = Alert(
            id=f"{resource_type.value}_{int(time.time())}",
            severity=severity,
            resource_type=resource_type,
            message=f"{resource_type.value.title()} usage is {status}: {value:.1f}%",
            threshold=critical_threshold if status == "critical" else warning_threshold,
            current_value=value,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        self.active_alerts[alert_key] = alert
        
        # Update stats
        self.stats["total_alerts"] += 1
        
        # Log alert
        log_level = logging.CRITICAL if severity == AlertSeverity.CRITICAL else logging.WARNING
        self.logger.log(log_level, alert.message)
    
    async def _resolve_alert(self, resource_type: ResourceType):
        """Resolve active alerts for resource type."""
        resolved_keys = []
        
        for alert_key, alert in self.active_alerts.items():
            if alert.resource_type == resource_type:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                resolved_keys.append(alert_key)
                self.stats["resolved_alerts"] += 1
        
        # Remove from active alerts
        for key in resolved_keys:
            del self.active_alerts[key]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current resource metrics."""
        current_metrics = {}
        
        for resource_type in ResourceType:
            if self.metrics_history[resource_type]:
                latest = self.metrics_history[resource_type][-1]
                current_metrics[resource_type.value] = {
                    "value": latest.value,
                    "timestamp": latest.timestamp.isoformat(),
                    "unit": latest.unit,
                    "status": latest.status,
                    "metadata": latest.metadata
                }
        
        return current_metrics
    
    def get_metrics_history(self, resource_type: ResourceType, 
                          hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for a resource type."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            {
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "unit": metric.unit,
                "status": metric.status
            }
            for metric in self.metrics_history[resource_type]
            if metric.timestamp > cutoff_time
        ]
    
    def get_alerts(self, severity: Optional[AlertSeverity] = None, 
                  resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering."""
        filtered_alerts = self.alerts
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        if resolved is not None:
            filtered_alerts = [a for a in filtered_alerts if a.resolved == resolved]
        
        return [
            {
                "id": alert.id,
                "severity": alert.severity.value,
                "resource_type": alert.resource_type.value,
                "message": alert.message,
                "threshold": alert.threshold,
                "current_value": alert.current_value,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "count": alert.count
            }
            for alert in filtered_alerts
        ]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        # Get latest metrics
        current_metrics = self.get_current_metrics()
        
        # Calculate health scores
        health_scores = {}
        for resource_type_str, metrics in current_metrics.items():
            value = metrics["value"]
            
            # Simple health scoring
            if resource_type_str == "cpu":
                if value < 50:
                    health_scores[resource_type_str] = "healthy"
                elif value < 80:
                    health_scores[resource_type_str] = "warning"
                else:
                    health_scores[resource_type_str] = "critical"
            
            elif resource_type_str == "memory":
                if value < 70:
                    health_scores[resource_type_str] = "healthy"
                elif value < 90:
                    health_scores[resource_type_str] = "warning"
                else:
                    health_scores[resource_type_str] = "critical"
            
            elif resource_type_str == "disk":
                if value < 80:
                    health_scores[resource_type_str] = "healthy"
                elif value < 95:
                    health_scores[resource_type_str] = "warning"
                else:
                    health_scores[resource_type_str] = "critical"
            
            else:
                health_scores[resource_type_str] = "healthy"
        
        # Overall health
        critical_count = sum(1 for score in health_scores.values() if score == "critical")
        warning_count = sum(1 for score in health_scores.values() if score == "warning")
        
        if critical_count > 0:
            overall_health = "critical"
        elif warning_count > 0:
            overall_health = "warning"
        else:
            overall_health = "healthy"
        
        return {
            "overall_health": overall_health,
            "resource_health": health_scores,
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "total_alerts_24h": len([
                a for a in self.alerts 
                if (datetime.now() - a.timestamp).total_seconds() < 86400
            ]),
            "statistics": self.stats
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        avg_collection_times = {}
        
        for resource, times in self.collection_times.items():
            if times:
                avg_collection_times[resource] = sum(times) / len(times)
        
        return {
            "collection_times": avg_collection_times,
            "statistics": self.stats,
            "monitoring_active": self._monitoring,
            "active_tasks": len(self._monitoring_tasks)
        }


class PerformanceTracker:
    """Application performance tracker."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.logger = logging.getLogger("performance_tracker")
        
        # Performance data
        self.request_times: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.operation_counts: Dict[str, int] = defaultdict(int)
        
        # Database performance
        self.db_query_times: deque = deque(maxlen=1000)
        self.db_error_counts: int = 0
        
        # Cache performance
        self.cache_hit_times: deque = deque(maxlen=1000)
        self.cache_miss_times: deque = deque(maxlen=1000)
        self.cache_hit_count: int = 0
        self.cache_miss_count: int = 0
        
        # Web scraping performance
        self.scraping_times: deque = deque(maxlen=1000)
        self.scraping_success_rate: float = 1.0
        
        # Export data
        self.last_export: Dict[str, datetime] = {}
    
    def track_request(self, endpoint: str, duration: float, success: bool = True):
        """Track API request performance."""
        self.request_times[endpoint].append(duration)
        self.operation_counts[f"requests_{endpoint}"] += 1
        
        if not success:
            self.error_counts[endpoint] += 1
    
    def track_database_query(self, duration: float, success: bool = True):
        """Track database query performance."""
        self.db_query_times.append(duration)
        self.operation_counts["db_queries"] += 1
        
        if not success:
            self.db_error_counts += 1
    
    def track_cache_operation(self, duration: float, hit: bool = True):
        """Track cache operation performance."""
        if hit:
            self.cache_hit_times.append(duration)
            self.cache_hit_count += 1
            self.operation_counts["cache_hits"] += 1
        else:
            self.cache_miss_times.append(duration)
            self.cache_miss_count += 1
            self.operation_counts["cache_misses"] += 1
    
    def track_scraping_operation(self, duration: float, success: bool = True):
        """Track web scraping performance."""
        self.scraping_times.append(duration)
        self.operation_counts["scraping_operations"] += 1
        
        if success:
            # Update success rate with exponential moving average
            alpha = 0.1
            self.scraping_success_rate = (alpha * 1.0 + (1 - alpha) * self.scraping_success_rate)
        else:
            alpha = 0.1
            self.scraping_success_rate = (alpha * 0.0 + (1 - alpha) * self.scraping_success_rate)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        # Calculate averages
        avg_request_times = {}
        for endpoint, times in self.request_times.items():
            if times:
                avg_request_times[endpoint] = sum(times) / len(times)
        
        # Database performance
        avg_db_time = sum(self.db_query_times) / len(self.db_query_times) if self.db_query_times else 0.0
        
        # Cache performance
        avg_hit_time = sum(self.cache_hit_times) / len(self.cache_hit_times) if self.cache_hit_times else 0.0
        avg_miss_time = sum(self.cache_miss_times) / len(self.cache_miss_times) if self.cache_miss_times else 0.0
        
        cache_hit_rate = (
            self.cache_hit_count / (self.cache_hit_count + self.cache_miss_count)
            if (self.cache_hit_count + self.cache_miss_count) > 0 else 0.0
        )
        
        # Scraping performance
        avg_scraping_time = sum(self.scraping_times) / len(self.scraping_times) if self.scraping_times else 0.0
        
        return {
            "api_performance": {
                "average_request_times": avg_request_times,
                "error_rates": {
                    endpoint: errors / self.operation_counts[f"requests_{endpoint}"]
                    for endpoint, errors in self.error_counts.items()
                    if f"requests_{endpoint}" in self.operation_counts
                }
            },
            "database_performance": {
                "average_query_time": avg_db_time,
                "total_queries": self.operation_counts.get("db_queries", 0),
                "error_count": self.db_error_counts
            },
            "cache_performance": {
                "average_hit_time": avg_hit_time,
                "average_miss_time": avg_miss_time,
                "hit_rate": cache_hit_rate,
                "total_operations": self.cache_hit_count + self.cache_miss_count
            },
            "scraping_performance": {
                "average_operation_time": avg_scraping_time,
                "success_rate": self.scraping_success_rate,
                "total_operations": self.operation_counts.get("scraping_operations", 0)
            },
            "operation_counts": dict(self.operation_counts)
        }


class ResourceOptimizer:
    """Automated resource optimization system."""
    
    def __init__(self, system_monitor: SystemMonitor, config: MonitoringConfig):
        self.system_monitor = system_monitor
        self.config = config
        self.logger = logging.getLogger("resource_optimizer")
        
        # Optimization rules
        self.optimization_rules = [
            self._optimize_memory_pressure,
            self._optimize_cpu_pressure,
            self._optimize_disk_space,
            self._optimize_cache_size,
            self._optimize_database_connections
        ]
        
        # Last optimization times
        self.last_optimization: Dict[str, datetime] = {}
        
        # Optimization cooldown (5 minutes)
        self.optimization_cooldown = 300
    
    async def run_optimization(self):
        """Run optimization based on current system state."""
        current_metrics = self.system_monitor.get_current_metrics()
        health = self.system_monitor.get_system_health()
        
        # Check if optimization is needed
        if health["overall_health"] == "healthy":
            return
        
        # Run optimization rules
        for rule in self.optimization_rules:
            try:
                await rule(current_metrics, health)
            except Exception as e:
                self.logger.error(f"Optimization rule failed: {e}")
    
    async def _optimize_memory_pressure(self, metrics: Dict, health: Dict):
        """Optimize for memory pressure."""
        if health["resource_health"].get("memory") in ["warning", "critical"]:
            rule_name = "memory_optimization"
            
            # Check cooldown
            if (rule_name in self.last_optimization and 
                (datetime.now() - self.last_optimization[rule_name]).total_seconds() < self.optimization_cooldown):
                return
            
            self.logger.info("Running memory optimization")
            
            # Trigger garbage collection
            collected = gc.collect()
            self.logger.info(f"Garbage collection freed {collected} objects")
            
            # Clear any caches if needed
            cache_manager = await self._get_cache_manager()
            if cache_manager:
                await cache_manager.clear()
                self.logger.info("Cleared cache to free memory")
            
            # Update last optimization time
            self.last_optimization[rule_name] = datetime.now()
    
    async def _optimize_cpu_pressure(self, metrics: Dict, health: Dict):
        """Optimize for CPU pressure."""
        if health["resource_health"].get("cpu") == "critical":
            rule_name = "cpu_optimization"
            
            # Check cooldown
            if (rule_name in self.last_optimization and 
                (datetime.now() - self.last_optimization[rule_name]).total_seconds() < self.optimization_cooldown):
                return
            
            self.logger.info("Running CPU optimization")
            
            # Reduce concurrent operations
            # This would involve adjusting worker pool sizes, etc.
            # For now, just trigger GC
            gc.collect()
            
            self.last_optimization[rule_name] = datetime.now()
    
    async def _optimize_disk_space(self, metrics: Dict, health: Dict):
        """Optimize for disk space."""
        if health["resource_health"].get("disk") == "critical":
            rule_name = "disk_optimization"
            
            # Check cooldown
            if (rule_name in self.last_optimization and 
                (datetime.now() - self.last_optimization[rule_name]).total_seconds() < self.optimization_cooldown):
                return
            
            self.logger.info("Running disk space optimization")
            
            # Clean up temporary files
            temp_dirs = [
                Path("temp"),
                Path("cache"),
                Path("logs")
            ]
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    # Remove old files
                    for file_path in temp_dir.glob("*"):
                        if file_path.is_file():
                            try:
                                if (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days > 1:
                                    file_path.unlink()
                            except Exception as e:
                                self.logger.error(f"Failed to delete {file_path}: {e}")
            
            self.last_optimization[rule_name] = datetime.now()
    
    async def _optimize_cache_size(self, metrics: Dict, health: Dict):
        """Optimize cache size and performance."""
        # This would involve adjusting cache parameters based on usage patterns
        pass
    
    async def _optimize_database_connections(self, metrics: Dict, health: Dict):
        """Optimize database connection pool."""
        # This would involve adjusting connection pool settings
        pass
    
    async def _get_cache_manager(self):
        """Get cache manager instance."""
        try:
            from cache.cache_system import get_cache_manager
            return await get_cache_manager()
        except Exception as e:
            self.logger.error(f"Failed to get cache manager: {e}")
            return None


class MonitoringOrchestrator:
    """Main monitoring system orchestrator."""
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.logger = logging.getLogger("monitoring_orchestrator")
        
        # Initialize components
        self.system_monitor = SystemMonitor(self.config)
        self.performance_tracker = PerformanceTracker(self.config)
        self.resource_optimizer = ResourceOptimizer(self.system_monitor, self.config)
        
        # Monitoring state
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Integration with other systems
        self._external_exporters: List[Callable] = []
    
    async def start(self):
        """Start the monitoring system."""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Starting monitoring orchestrator")
        
        # Start system monitoring
        await self.system_monitor.start_monitoring()
        
        # Start optimization loop
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop the monitoring system."""
        if not self._running:
            return
        
        self._running = False
        self.logger.info("Stopping monitoring orchestrator")
        
        # Stop system monitoring
        await self.system_monitor.stop_monitoring()
        
        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
        
        # Export final data
        await self._export_metrics()
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Run resource optimization
                await self.resource_optimizer.run_optimization()
                
                # Export metrics periodically
                await self._periodic_export()
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _periodic_export(self):
        """Periodic metrics export."""
        now = datetime.now()
        
        # Export to external systems
        for exporter in self._external_exporters:
            try:
                if exporter.__name__ not in self.last_export or \
                   (now - self.last_export[exporter.__name__]).total_seconds() > 300:
                    await exporter()
                    self.last_export[exporter.__name__] = now
            except Exception as e:
                self.logger.error(f"Export error for {exporter.__name__}: {e}")
    
    async def _export_metrics(self):
        """Export final metrics."""
        # Export to JSON
        if self.config.export_json:
            await self._export_to_json()
        
        # Export to Prometheus format
        if self.config.export_prometheus:
            await self._export_to_prometheus()
    
    async def _export_to_json(self):
        """Export metrics to JSON format."""
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "system_health": self.system_monitor.get_system_health(),
            "performance_summary": self.performance_tracker.get_performance_summary(),
            "current_metrics": self.system_monitor.get_current_metrics(),
            "alerts": self.system_monitor.get_alerts()
        }
        
        output_path = Path("monitoring_report.json")
        try:
            import json
            with open(output_path, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)
            self.logger.info(f"Metrics exported to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}")
    
    async def _export_to_prometheus(self):
        """Export metrics in Prometheus format."""
        prometheus_metrics = []
        
        # System metrics
        current_metrics = self.system_monitor.get_current_metrics()
        for resource_type, metrics in current_metrics.items():
            prometheus_metrics.append(f"system_{resource_type}_usage {metrics['value']}")
        
        # Performance metrics
        perf_summary = self.performance_tracker.get_performance_summary()
        for category, data in perf_summary.items():
            if isinstance(data, dict):
                for metric, value in data.items():
                    if isinstance(value, (int, float)):
                        prometheus_metrics.append(f"performance_{category}_{metric} {value}")
        
        output_path = Path("metrics.prom")
        try:
            with open(output_path, 'w') as f:
                f.write("\n".join(prometheus_metrics))
            self.logger.info(f"Prometheus metrics exported to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to export to Prometheus: {e}")
    
    def add_exporter(self, exporter: Callable):
        """Add external metrics exporter."""
        self._external_exporters.append(exporter)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": self.system_monitor.get_system_health(),
            "performance_summary": self.performance_tracker.get_performance_summary(),
            "current_metrics": self.system_monitor.get_current_metrics(),
            "active_alerts": len([a for a in self.system_monitor.alerts if not a.resolved]),
            "optimization_status": {
                "last_optimization": max(self.resource_optimizer.last_optimization.values()) 
                if self.resource_optimizer.last_optimization else None
            }
        }


# Global monitoring orchestrator
_monitoring_orchestrator: Optional[MonitoringOrchestrator] = None
_monitoring_lock = asyncio.Lock()


async def get_monitoring_orchestrator(config: Optional[MonitoringConfig] = None) -> MonitoringOrchestrator:
    """Get global monitoring orchestrator instance."""
    global _monitoring_orchestrator
    
    async with _monitoring_lock:
        if _monitoring_orchestrator is None:
            _monitoring_orchestrator = MonitoringOrchestrator(config)
            await _monitoring_orchestrator.start()
        
        return _monitoring_orchestrator


async def close_monitoring_orchestrator():
    """Close global monitoring orchestrator."""
    global _monitoring_orchestrator
    
    if _monitoring_orchestrator:
        await _monitoring_orchestrator.stop()
        _monitoring_orchestrator = None


# Performance tracking decorator
def track_performance(operation_type: str, operation_name: str = ""):
    """Decorator to track operation performance."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                
                # Get performance tracker and record
                try:
                    orchestrator = await get_monitoring_orchestrator()
                    tracker = orchestrator.performance_tracker
                    
                    if operation_type == "request":
                        tracker.track_request(operation_name or func.__name__, duration, success)
                    elif operation_type == "database":
                        tracker.track_database_query(duration, success)
                    elif operation_type == "cache":
                        tracker.track_cache_operation(duration, success)
                    elif operation_type == "scraping":
                        tracker.track_scraping_operation(duration, success)
                except Exception:
                    pass  # Don't let tracking errors affect main operation
        
        return wrapper
    return decorator


# Export main classes and functions
__all__ = [
    'MonitoringOrchestrator',
    'SystemMonitor',
    'PerformanceTracker',
    'ResourceOptimizer',
    'MonitoringConfig',
    'ResourceMetric',
    'Alert',
    'AlertSeverity',
    'ResourceType',
    'get_monitoring_orchestrator',
    'close_monitoring_orchestrator',
    'track_performance'
]