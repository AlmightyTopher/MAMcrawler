"""
Background Task Processing System for MAMcrawler

This module provides a comprehensive background task processing system with queue management,
task scheduling, retry mechanisms, and monitoring capabilities.

Author: Audiobook Automation System
Version: 1.0.0
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import PriorityQueue, Queue, Empty
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref
import pickle


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackgroundTask:
    """Background task definition."""
    task_id: str
    task_type: str
    function: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    schedule_at: Optional[datetime] = None
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        """Priority comparison for queue."""
        if not isinstance(other, BackgroundTask):
            return NotImplemented
        return self.priority.value < other.priority.value


class TaskQueue:
    """Priority-based task queue with dependency management."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue = PriorityQueue(maxsize=max_size)
        self._tasks_by_id: Dict[str, BackgroundTask] = {}
        self._dependency_graph: Dict[str, set] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger("task_queue")
    
    def put(self, task: BackgroundTask) -> bool:
        """Add task to queue."""
        with self._lock:
            if len(self._tasks_by_id) >= self.max_size:
                self.logger.warning("Task queue is full")
                return False
            
            # Add to queue
            self._queue.put((task.priority.value, task.created_at.timestamp(), task))
            
            # Track task
            self._tasks_by_id[task.task_id] = task
            
            # Build dependency graph
            for dep_id in task.dependencies:
                if dep_id not in self._dependency_graph:
                    self._dependency_graph[dep_id] = set()
                self._dependency_graph[task.task_id].add(dep_id)
            
            self.logger.debug(f"Added task {task.task_id} to queue")
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[BackgroundTask]:
        """Get next task from queue."""
        try:
            _, _, task = self._queue.get(timeout=timeout)
            
            # Check dependencies
            if self._has_pending_dependencies(task):
                # Re-queue and try later
                self.put(task)
                return None
            
            return task
            
        except Empty:
            return None
    
    def mark_completed(self, task_id: str):
        """Mark task as completed and resolve dependencies."""
        with self._lock:
            if task_id in self._tasks_by_id:
                del self._tasks_by_id[task_id]
            
            # Remove from dependency graph
            if task_id in self._dependency_graph:
                del self._dependency_graph[task_id]
            
            # Remove from dependents
            for dependents in self._dependency_graph.values():
                dependents.discard(task_id)
    
    def _has_pending_dependencies(self, task: BackgroundTask) -> bool:
        """Check if task has pending dependencies."""
        for dep_id in task.dependencies:
            if dep_id in self._tasks_by_id:
                return True
        return False
    
    def size(self) -> int:
        """Get queue size."""
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status by ID."""
        return self._tasks_by_id.get(task_id, None)


class TaskExecutor:
    """Task executor with retry logic and monitoring."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks: Dict[str, TaskResult] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger("task_executor")
    
    async def execute(self, task: BackgroundTask) -> TaskResult:
        """Execute task with retry logic."""
        task_result = TaskResult(task_id=task.task_id, status=TaskStatus.PENDING)
        
        with self._lock:
            self.active_tasks[task.task_id] = task_result
        
        max_attempts = task.max_retries + 1
        
        for attempt in range(1, max_attempts + 1):
            try:
                task_result.attempts = attempt
                task_result.started_at = datetime.now()
                task_result.status = TaskStatus.RUNNING
                
                self.logger.info(f"Executing task {task.task_id} (attempt {attempt}/{max_attempts})")
                
                # Execute with timeout
                if task.timeout:
                    loop = asyncio.get_event_loop()
                    future = loop.run_in_executor(
                        self.executor, 
                        self._execute_sync_task, 
                        task
                    )
                    result = await asyncio.wait_for(future, timeout=task.timeout)
                else:
                    result = await self._execute_async_task(task)
                
                task_result.result = result
                task_result.status = TaskStatus.COMPLETED
                task_result.completed_at = datetime.now()
                
                self.logger.info(f"Task {task.task_id} completed successfully")
                
                # Call callback if provided
                if task.callback:
                    try:
                        await task.callback(task_result)
                    except Exception as e:
                        self.logger.error(f"Callback error for task {task.task_id}: {e}")
                
                break
                
            except Exception as e:
                task_result.error = str(e)
                
                if attempt < max_attempts:
                    task_result.status = TaskStatus.RETRYING
                    task_result.retry_count += 1
                    
                    delay = task.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    self.logger.warning(
                        f"Task {task.task_id} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {delay:.2f} seconds"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    task_result.status = TaskStatus.FAILED
                    task_result.completed_at = datetime.now()
                    self.logger.error(f"Task {task.task_id} failed after {max_attempts} attempts: {e}")
        
        return task_result
    
    def _execute_sync_task(self, task: BackgroundTask) -> Any:
        """Execute synchronous task."""
        return task.function(*task.args, **task.kwargs)
    
    async def _execute_async_task(self, task: BackgroundTask) -> Any:
        """Execute async task."""
        result = task.function(*task.args, **task.kwargs)
        
        # Handle both sync and async results
        if asyncio.iscoroutine(result):
            result = await result
        
        return result
    
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result by ID."""
        with self._lock:
            return self.active_tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel running task."""
        with self._lock:
            if task_id in self.active_tasks:
                task_result = self.active_tasks[task_id]
                task_result.status = TaskStatus.CANCELLED
                task_result.completed_at = datetime.now()
                return True
            return False
    
    def shutdown(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=True)
        self.logger.info("Task executor shutdown")


class TaskScheduler:
    """Task scheduler for recurring and delayed tasks."""
    
    def __init__(self):
        self.scheduled_tasks: Dict[str, BackgroundTask] = {}
        self._scheduler_running = False
        self._scheduler_task = None
        self._lock = threading.RLock()
        self.logger = logging.getLogger("task_scheduler")
    
    def schedule(self, task: BackgroundTask, run_at: datetime):
        """Schedule task to run at specific time."""
        if run_at <= datetime.now():
            raise ValueError("Scheduled time must be in the future")
        
        with self._lock:
            task.schedule_at = run_at
            self.scheduled_tasks[task.task_id] = task
        
        self.logger.info(f"Scheduled task {task.task_id} for {run_at}")
    
    def schedule_recurring(self, task_func: Callable, interval: timedelta, 
                          args: Tuple = (), kwargs: Dict = None, 
                          task_type: str = "recurring", **task_kwargs) -> str:
        """Schedule recurring task."""
        task_id = str(uuid.uuid4())
        
        def recurring_wrapper():
            # Execute the original task
            result = task_func(*args, **(kwargs or {}))
            
            # Schedule next occurrence
            next_run = datetime.now() + interval
            next_task = BackgroundTask(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                function=recurring_wrapper,
                **task_kwargs
            )
            self.schedule(next_task, next_run)
            
            return result
        
        # Schedule first occurrence
        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            function=recurring_wrapper,
            args=args,
            kwargs=kwargs or {},
            **task_kwargs
        )
        
        self.schedule(task, datetime.now() + interval)
        return task_id
    
    def cancel_scheduled(self, task_id: str):
        """Cancel scheduled task."""
        with self._lock:
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]
                self.logger.info(f"Cancelled scheduled task {task_id}")
    
    def start_scheduler(self):
        """Start the scheduler."""
        if not self._scheduler_running:
            self._scheduler_running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            self.logger.info("Task scheduler started")
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        if self._scheduler_running:
            self._scheduler_running = False
            if self._scheduler_task:
                self._scheduler_task.cancel()
            self.logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._scheduler_running:
            try:
                now = datetime.now()
                ready_tasks = []
                
                with self._lock:
                    for task_id, task in list(self.scheduled_tasks.items()):
                        if task.schedule_at and task.schedule_at <= now:
                            ready_tasks.append((task_id, task))
                
                # Move ready tasks back to main queue
                for task_id, task in ready_tasks:
                    with self._lock:
                        if task_id in self.scheduled_tasks:
                            del self.scheduled_tasks[task_id]
                
                self.logger.debug(f"Scheduler found {len(ready_tasks)} ready tasks")
                
                await asyncio.sleep(1)  # Check every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)  # Back off on error


class BackgroundTaskProcessor:
    """Main background task processing system."""
    
    def __init__(self, max_workers: int = 4, max_queue_size: int = 10000):
        self.task_queue = TaskQueue(max_queue_size)
        self.task_executor = TaskExecutor(max_workers)
        self.task_scheduler = TaskScheduler()
        self.logger = logging.getLogger("task_processor")
        
        # Statistics
        self.stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "average_execution_time": 0.0
        }
        
        # Metrics tracking
        self._execution_times = []
        self._lock = threading.RLock()
        
        # Processing loop
        self._processing = False
        self._processing_task = None
    
    async def start(self):
        """Start the task processor."""
        if self._processing:
            return
        
        self._processing = True
        self.task_scheduler.start_scheduler()
        self._processing_task = asyncio.create_task(self._processing_loop())
        self.logger.info("Background task processor started")
    
    async def stop(self):
        """Stop the task processor."""
        if not self._processing:
            return
        
        self._processing = False
        self.task_scheduler.stop_scheduler()
        
        if self._processing_task:
            self._processing_task.cancel()
        
        self.task_executor.shutdown()
        self.logger.info("Background task processor stopped")
    
    def submit_task(self, task_func: Callable, args: Tuple = (), kwargs: Dict = None,
                   task_type: str = "general", priority: TaskPriority = TaskPriority.NORMAL,
                   max_retries: int = 3, retry_delay: float = 1.0,
                   timeout: Optional[float] = None, dependencies: List[str] = None,
                   schedule_at: Optional[datetime] = None,
                   callback: Optional[Callable] = None) -> str:
        """Submit task for background processing."""
        
        task_id = str(uuid.uuid4())
        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            function=task_func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            dependencies=dependencies or [],
            schedule_at=schedule_at,
            callback=callback
        )
        
        if schedule_at:
            self.task_scheduler.schedule(task, schedule_at)
        else:
            self.task_queue.put(task)
        
        with self._lock:
            self.stats["tasks_submitted"] += 1
        
        self.logger.info(f"Submitted task {task_id} ({task_type})")
        return task_id
    
    def submit_crawler_task(self, crawler_func: Callable, urls: List[str], 
                          **kwargs) -> str:
        """Submit crawler task for background processing."""
        
        def crawler_wrapper():
            results = []
            for url in urls:
                try:
                    result = crawler_func(url, **kwargs)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Crawler task failed for URL {url}: {e}")
                    results.append({"url": url, "success": False, "error": str(e)})
            return results
        
        return self.submit_task(
            crawler_wrapper,
            task_type="crawler",
            priority=TaskPriority.NORMAL,
            **kwargs
        )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of submitted task."""
        # Check active tasks
        result = self.task_executor.get_task_result(task_id)
        if result:
            return {
                "task_id": result.task_id,
                "status": result.status.value,
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "attempts": result.attempts,
                "error": result.error
            }
        
        # Check scheduled tasks
        if task_id in self.task_scheduler.scheduled_tasks:
            task = self.task_scheduler.scheduled_tasks[task_id]
            return {
                "task_id": task.task_id,
                "status": "scheduled",
                "scheduled_at": task.schedule_at.isoformat() if task.schedule_at else None,
                "task_type": task.task_type
            }
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel running task."""
        if self.task_executor.cancel_task(task_id):
            with self._lock:
                self.stats["tasks_cancelled"] += 1
            return True
        
        self.task_scheduler.cancel_scheduled(task_id)
        return True
    
    async def _processing_loop(self):
        """Main processing loop."""
        while self._processing:
            try:
                # Get next task
                task = self.task_queue.get(timeout=1.0)
                
                if task:
                    # Execute task
                    result = await self.task_executor.execute(task)
                    
                    # Update statistics
                    with self._lock:
                        execution_time = (
                            result.completed_at - result.started_at
                        ).total_seconds() if result.started_at and result.completed_at else 0
                        
                        self._execution_times.append(execution_time)
                        if len(self._execution_times) > 1000:  # Keep only recent times
                            self._execution_times.pop(0)
                        
                        if result.status == TaskStatus.COMPLETED:
                            self.stats["tasks_completed"] += 1
                        elif result.status == TaskStatus.FAILED:
                            self.stats["tasks_failed"] += 1
                        
                        # Update average execution time
                        if self._execution_times:
                            self.stats["average_execution_time"] = sum(self._execution_times) / len(self._execution_times)
                    
                    # Remove from queue
                    self.task_queue.mark_completed(task.task_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Processing loop error: {e}")
                await asyncio.sleep(1)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with self._lock:
            return {
                **self.stats,
                "queue_size": self.task_queue.size(),
                "active_tasks": len(self.task_executor.active_tasks),
                "scheduled_tasks": len(self.task_scheduler.scheduled_tasks)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for task processor."""
        try:
            stats = self.get_statistics()
            
            # Check if processor is running
            if not self._processing:
                return {"status": "unhealthy", "reason": "Processor not running"}
            
            # Check queue size
            if stats["queue_size"] > 9000:  # 90% of max size
                return {"status": "degraded", "reason": "Queue nearly full"}
            
            # Check failure rate
            total_tasks = stats["tasks_completed"] + stats["tasks_failed"]
            if total_tasks > 0:
                failure_rate = stats["tasks_failed"] / total_tasks
                if failure_rate > 0.1:  # More than 10% failure rate
                    return {"status": "degraded", "reason": "High failure rate"}
            
            return {"status": "healthy"}
            
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)}


# Global task processor instance
_task_processor: Optional[BackgroundTaskProcessor] = None
_lock = threading.RLock()


def get_task_processor() -> BackgroundTaskProcessor:
    """Get global task processor instance."""
    global _task_processor
    with _lock:
        if _task_processor is None:
            _task_processor = BackgroundTaskProcessor()
        return _task_processor


async def start_task_processor():
    """Start the global task processor."""
    processor = get_task_processor()
    await processor.start()


async def stop_task_processor():
    """Stop the global task processor."""
    global _task_processor
    if _task_processor:
        await _task_processor.stop()
        _task_processor = None


def submit_background_task(task_func: Callable, *args, **kwargs) -> str:
    """Convenience function to submit background task."""
    processor = get_task_processor()
    return processor.submit_task(task_func, args, kwargs)


# Export main classes and functions
__all__ = [
    'BackgroundTask',
    'TaskResult', 
    'TaskQueue',
    'TaskExecutor',
    'TaskScheduler',
    'BackgroundTaskProcessor',
    'TaskStatus',
    'TaskPriority',
    'get_task_processor',
    'start_task_processor',
    'stop_task_processor',
    'submit_background_task'
]