"""
Task Service - Business logic for task execution tracking
Handles scheduled job tracking, execution history, and performance monitoring
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from backend.models.task import Task

logger = logging.getLogger(__name__)


class TaskService:
    """
    Service layer for task execution tracking

    Provides methods for managing scheduled tasks, tracking execution history,
    and monitoring task performance
    """

    @staticmethod
    def create_task(
        db: Session,
        task_name: str,
        scheduled_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new task record

        Args:
            db: Database session
            task_name: Name of task (MAM, TOP10, METADATA_FULL, METADATA_NEW, SERIES, AUTHOR)
            scheduled_time: When task is scheduled to run
            metadata: Task-specific metadata (JSON)

        Returns:
            Dict with:
                - success: bool
                - data: Task object if successful
                - error: str if failed
                - task_id: int if successful
        """
        try:
            task = Task(
                task_name=task_name,
                scheduled_time=scheduled_time or datetime.now(),
                status="scheduled",
                metadata=metadata or {}
            )

            db.add(task)
            db.commit()
            db.refresh(task)

            logger.info(f"Created task: {task_name} (ID: {task.id}, scheduled: {task.scheduled_time})")

            return {
                "success": True,
                "data": task,
                "task_id": task.id,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating task '{task_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "task_id": None
            }

    @staticmethod
    def mark_started(db: Session, task_id: int) -> Dict[str, Any]:
        """
        Mark task as started

        Args:
            db: Database session
            task_id: Task ID

        Returns:
            Dict with success, data (updated Task), error
        """
        try:
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                return {
                    "success": False,
                    "error": f"Task with ID {task_id} not found",
                    "data": None
                }

            task.status = "running"
            task.actual_start = datetime.now()

            db.commit()
            db.refresh(task)

            logger.info(f"Task {task_id} ({task.task_name}) started at {task.actual_start}")

            return {
                "success": True,
                "data": task,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error marking task {task_id} as started: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def mark_completed(
        db: Session,
        task_id: int,
        items_processed: int = 0,
        items_succeeded: int = 0,
        items_failed: int = 0,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Mark task as completed

        Args:
            db: Database session
            task_id: Task ID
            items_processed: Total items processed
            items_succeeded: Number of successful items
            items_failed: Number of failed items
            duration_seconds: Total execution time in seconds (auto-calculated if None)

        Returns:
            Dict with success, data (updated Task), stats, error
        """
        try:
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                return {
                    "success": False,
                    "error": f"Task with ID {task_id} not found",
                    "data": None,
                    "stats": None
                }

            task.status = "completed"
            task.actual_end = datetime.now()
            task.items_processed = items_processed
            task.items_succeeded = items_succeeded
            task.items_failed = items_failed

            # Calculate duration if not provided
            if duration_seconds is not None:
                task.duration_seconds = duration_seconds
            elif task.actual_start:
                duration = task.actual_end - task.actual_start
                task.duration_seconds = int(duration.total_seconds())

            db.commit()
            db.refresh(task)

            stats = {
                "items_processed": task.items_processed,
                "items_succeeded": task.items_succeeded,
                "items_failed": task.items_failed,
                "duration_seconds": task.duration_seconds,
                "success_rate": (
                    round((items_succeeded / items_processed) * 100, 2)
                    if items_processed > 0 else 0
                )
            }

            logger.info(
                f"Task {task_id} ({task.task_name}) completed: "
                f"{items_processed} processed, {items_succeeded} succeeded, "
                f"{items_failed} failed, {task.duration_seconds}s duration"
            )

            return {
                "success": True,
                "data": task,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error marking task {task_id} as completed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "stats": None
            }

    @staticmethod
    def mark_failed(
        db: Session,
        task_id: int,
        error_msg: str,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Mark task as failed

        Args:
            db: Database session
            task_id: Task ID
            error_msg: Error message
            duration_seconds: Total execution time in seconds (auto-calculated if None)

        Returns:
            Dict with success, data (updated Task), error
        """
        try:
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                return {
                    "success": False,
                    "error": f"Task with ID {task_id} not found",
                    "data": None
                }

            task.status = "failed"
            task.actual_end = datetime.now()
            task.error_message = error_msg

            # Calculate duration if not provided
            if duration_seconds is not None:
                task.duration_seconds = duration_seconds
            elif task.actual_start:
                duration = task.actual_end - task.actual_start
                task.duration_seconds = int(duration.total_seconds())

            db.commit()
            db.refresh(task)

            logger.error(
                f"Task {task_id} ({task.task_name}) failed after "
                f"{task.duration_seconds}s: {error_msg}"
            )

            return {
                "success": True,
                "data": task,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error marking task {task_id} as failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_task(db: Session, task_id: int) -> Dict[str, Any]:
        """
        Get task by ID

        Args:
            db: Database session
            task_id: Task ID

        Returns:
            Dict with success, data (Task or None), error
        """
        try:
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                return {
                    "success": False,
                    "error": f"Task with ID {task_id} not found",
                    "data": None
                }

            return {
                "success": True,
                "data": task,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_task_history(
        db: Session,
        task_name: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get execution history for a task

        Args:
            db: Database session
            task_name: Task name
            limit: Maximum number of records to return

        Returns:
            Dict with success, data (list of Tasks), count, error
        """
        try:
            tasks = db.query(Task).filter(
                Task.task_name == task_name
            ).order_by(
                Task.date_created.desc()
            ).limit(limit).all()

            return {
                "success": True,
                "data": tasks,
                "count": len(tasks),
                "task_name": task_name,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting task history for '{task_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "task_name": task_name
            }

    @staticmethod
    def add_log_output(
        db: Session,
        task_id: int,
        log_text: str
    ) -> Dict[str, Any]:
        """
        Append to task log output

        Args:
            db: Database session
            task_id: Task ID
            log_text: Log text to append

        Returns:
            Dict with success, data (updated Task), error
        """
        try:
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                return {
                    "success": False,
                    "error": f"Task with ID {task_id} not found",
                    "data": None
                }

            # Append to existing log
            if task.log_output:
                task.log_output += "\n" + log_text
            else:
                task.log_output = log_text

            # Flag modified for text field
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(task, "log_output")

            db.commit()
            db.refresh(task)

            return {
                "success": True,
                "data": task,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error adding log output to task {task_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_recent_tasks(
        db: Session,
        hours: int = 24,
        task_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recent task executions

        Args:
            db: Database session
            hours: Number of hours to look back
            task_name: Optional filter by task name

        Returns:
            Dict with success, data (list of Tasks), count, error
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            query = db.query(Task).filter(Task.date_created >= cutoff_time)

            if task_name:
                query = query.filter(Task.task_name == task_name)

            tasks = query.order_by(Task.date_created.desc()).all()

            return {
                "success": True,
                "data": tasks,
                "count": len(tasks),
                "hours": hours,
                "cutoff_time": cutoff_time.isoformat(),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting recent tasks: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "hours": hours,
                "cutoff_time": None
            }

    @staticmethod
    def cleanup_old_tasks(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Delete task records older than X days (retention policy)

        Args:
            db: Database session
            days: Number of days to retain tasks

        Returns:
            Dict with success, deleted_count, error
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Count tasks to be deleted
            tasks_to_delete = db.query(Task).filter(
                Task.date_created < cutoff_date
            ).count()

            # Delete old tasks
            db.query(Task).filter(
                Task.date_created < cutoff_date
            ).delete(synchronize_session=False)

            db.commit()

            logger.info(
                f"Deleted {tasks_to_delete} task records older than "
                f"{days} days (before {cutoff_date})"
            )

            return {
                "success": True,
                "deleted_count": tasks_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up old tasks: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0,
                "cutoff_date": None
            }

    @staticmethod
    def get_task_statistics(db: Session) -> Dict[str, Any]:
        """
        Get summary statistics for all tasks

        Returns:
            Dict with success, stats, error
        """
        try:
            # Total tasks by status
            status_counts = db.query(
                Task.status,
                func.count(Task.id)
            ).group_by(Task.status).all()

            status_breakdown = {status: count for status, count in status_counts}

            # Total tasks by task_name
            task_counts = db.query(
                Task.task_name,
                func.count(Task.id)
            ).group_by(Task.task_name).all()

            task_breakdown = {task: count for task, count in task_counts}

            # Average duration by task_name
            avg_durations = db.query(
                Task.task_name,
                func.avg(Task.duration_seconds)
            ).filter(
                Task.duration_seconds.isnot(None)
            ).group_by(Task.task_name).all()

            average_durations = {
                task: round(avg_duration, 2)
                for task, avg_duration in avg_durations
            }

            # Success rate by task_name
            success_rates = {}
            for task_name, _ in task_counts:
                total = db.query(Task).filter(Task.task_name == task_name).count()
                succeeded = db.query(Task).filter(
                    Task.task_name == task_name,
                    Task.status == "completed"
                ).count()

                if total > 0:
                    success_rates[task_name] = round((succeeded / total) * 100, 2)

            # Total tasks
            total_tasks = db.query(Task).count()

            stats = {
                "total_tasks": total_tasks,
                "status_breakdown": status_breakdown,
                "task_breakdown": task_breakdown,
                "average_durations_seconds": average_durations,
                "success_rates_percent": success_rates
            }

            return {
                "success": True,
                "stats": stats,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting task statistics: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": None
            }
