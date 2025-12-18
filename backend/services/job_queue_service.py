"""
Job Queue Service
==================

Persistent job queue implementation using the Task model.
Replaces global variable-based job tracking in api_server.py.

Features:
- Database-backed job persistence (survives server restarts)
- PID tracking for process management
- Orphaned job detection and cleanup
- Concurrent job support with locking
"""

import logging
import psutil
import subprocess
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from backend.models.task import Task
from backend.database import get_db_context

logger = logging.getLogger(__name__)


class JobQueueService:
    """
    Manages background job execution with database persistence.

    Replaces the global current_process variable pattern with proper
    database-backed job tracking using the Task model.
    """

    @staticmethod
    def start_job(
        task_name: str,
        command: List[str],
        metadata: Optional[Dict] = None
    ) -> Optional[int]:
        """
        Start a new background job.

        Args:
            task_name: Name of the task (e.g., "MAM_CRAWL", "METADATA_SYNC")
            command: Command to execute (e.g., ["python", "script.py", "--flag"])
            metadata: Optional task metadata

        Returns:
            Task ID if started successfully, None otherwise
        """
        with get_db_context() as db:
            # Check for concurrent jobs
            running = db.query(Task).filter(
                Task.status == "running"
            ).count()

            if running > 0:
                logger.warning(f"Cannot start {task_name}: Another task is already running")
                return None

            # Start the subprocess
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Create task record
                task = Task(
                    task_name=task_name,
                    scheduled_time=datetime.now(),
                    actual_start=datetime.now(),
                    status="running",
                    task_metadata={
                        "pid": process.pid,
                        "command": " ".join(command),
                        **(metadata or {})
                    }
                )

                db.add(task)
                db.commit()
                db.refresh(task)

                logger.info(f"Started job {task_name} (Task ID: {task.id}, PID: {process.pid})")
                return task.id

            except Exception as e:
                logger.error(f"Failed to start job {task_name}: {e}")
                return None

    @staticmethod
    def get_running_jobs() -> List[Dict]:
        """
        Get all currently running jobs.

        Returns:
            List of dicts with job info (id, name, pid, started_at)
        """
        with get_db_context() as db:
            running_tasks = db.query(Task).filter(
                Task.status == "running"
            ).all()

            jobs = []
            for task in running_tasks:
                pid = task.task_metadata.get("pid") if task.task_metadata else None

                # Check if process is actually running
                is_alive = False
                if pid:
                    try:
                        is_alive = psutil.pid_exists(pid)
                    except:
                        pass

                jobs.append({
                    "id": task.id,
                    "name": task.task_name,
                    "pid": pid,
                    "started_at": task.actual_start.isoformat() if task.actual_start else None,
                    "is_alive": is_alive
                })

            return jobs

    @staticmethod
    def check_job_status(task_id: int) -> Optional[str]:
        """
        Check the status of a specific job.

        Args:
            task_id: Task ID

        Returns:
            Status string ("running", "completed", "failed") or None if not found
        """
        with get_db_context() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                return task.status
            return None

    @staticmethod
    def mark_job_completed(
        task_id: int,
        items_processed: int = 0,
        items_succeeded: int = 0,
        items_failed: int = 0,
        log_output: Optional[str] = None
    ):
        """
        Mark a job as completed.

        Args:
            task_id: Task ID
            items_processed: Number of items processed
            items_succeeded: Number of successful items
            items_failed: Number of failed items
            log_output: Optional log output
        """
        with get_db_context() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "completed"
                task.actual_end = datetime.now()
                if task.actual_start:
                    duration = (task.actual_end - task.actual_start).total_seconds()
                    task.duration_seconds = int(duration)
                task.items_processed = items_processed
                task.items_succeeded = items_succeeded
                task.items_failed = items_failed
                if log_output:
                    task.log_output = log_output

                db.commit()
                logger.info(f"Marked job {task_id} as completed")

    @staticmethod
    def mark_job_failed(
        task_id: int,
        error_message: str,
        log_output: Optional[str] = None
    ):
        """
        Mark a job as failed.

        Args:
            task_id: Task ID
            error_message: Error message describing the failure
            log_output: Optional log output
        """
        with get_db_context() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.actual_end = datetime.now()
                if task.actual_start:
                    duration = (task.actual_end - task.actual_start).total_seconds()
                    task.duration_seconds = int(duration)
                task.error_message = error_message
                if log_output:
                    task.log_output = log_output

                db.commit()
                logger.info(f"Marked job {task_id} as failed: {error_message}")

    @staticmethod
    def cleanup_orphaned_jobs():
        """
        Find and mark orphaned jobs (status="running" but process no longer exists).

        This should be called on server startup to clean up jobs that were
        running when the server was stopped.
        """
        with get_db_context() as db:
            running_tasks = db.query(Task).filter(
                Task.status == "running"
            ).all()

            orphaned_count = 0
            for task in running_tasks:
                pid = task.task_metadata.get("pid") if task.task_metadata else None

                # Check if process still exists
                is_alive = False
                if pid:
                    try:
                        is_alive = psutil.pid_exists(pid)
                    except:
                        pass

                if not is_alive:
                    # Mark as failed
                    task.status = "failed"
                    task.actual_end = datetime.now()
                    if task.actual_start:
                        duration = (task.actual_end - task.actual_start).total_seconds()
                        task.duration_seconds = int(duration)
                    task.error_message = "Job orphaned (server restart or process crash)"
                    orphaned_count += 1

            if orphaned_count > 0:
                db.commit()
                logger.warning(f"Cleaned up {orphaned_count} orphaned jobs")
            else:
                logger.info("No orphaned jobs found")
