"""
Scheduler Manager for Audiobook Automation System
Manages APScheduler instance with SQLAlchemy job store and provides thread-safe access
"""

import logging
from threading import Lock
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from backend.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = Lock()


def initialize_scheduler() -> BackgroundScheduler:
    """
    Initialize and configure APScheduler with SQLAlchemy job store

    This function sets up a BackgroundScheduler with:
    - SQLAlchemy job store (uses same database as application)
    - Thread pool executor for parallel job execution
    - Event listeners for job execution monitoring
    - Comprehensive error handling and logging

    Returns:
        BackgroundScheduler: Configured scheduler instance

    Raises:
        RuntimeError: If scheduler initialization fails

    Thread Safety:
        This function is thread-safe and can be called from multiple threads.
        Only one scheduler instance will be created (singleton pattern).
    """
    global _scheduler

    # Thread-safe initialization (double-checked locking)
    if _scheduler is not None:
        logger.debug("Scheduler already initialized, returning existing instance")
        return _scheduler

    with _scheduler_lock:
        # Check again inside lock to prevent race conditions
        if _scheduler is not None:
            return _scheduler

        try:
            settings = get_settings()

            # Configure job store (uses same database as application)
            jobstores = {
                'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
            }

            # Configure executor (thread pool for parallel execution)
            executors = {
                'default': ThreadPoolExecutor(max_workers=10)
            }

            # Scheduler configuration
            job_defaults = {
                'coalesce': True,  # Combine multiple pending executions into one
                'max_instances': 1,  # Only one instance of each job can run at a time
                'misfire_grace_time': 900  # 15 minutes grace period for missed jobs
            }

            # Create scheduler instance
            _scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'  # Use UTC for all scheduled times
            )

            # Add event listeners for monitoring
            _scheduler.add_listener(
                _job_executed_listener,
                EVENT_JOB_EXECUTED
            )

            _scheduler.add_listener(
                _job_error_listener,
                EVENT_JOB_ERROR
            )

            _scheduler.add_listener(
                _job_missed_listener,
                EVENT_JOB_MISSED
            )

            logger.info("Scheduler initialized successfully")
            logger.info(f"Job store: SQLAlchemy ({settings.DATABASE_URL})")
            logger.info(f"Executor: ThreadPoolExecutor (max_workers=10)")
            logger.info(f"Timezone: UTC")

            return _scheduler

        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}", exc_info=True)
            raise RuntimeError(f"Scheduler initialization failed: {e}") from e


def get_scheduler() -> BackgroundScheduler:
    """
    Get the global scheduler instance

    Returns:
        BackgroundScheduler: The scheduler instance

    Raises:
        RuntimeError: If scheduler has not been initialized

    Thread Safety:
        This function is thread-safe.
    """
    if _scheduler is None:
        raise RuntimeError(
            "Scheduler has not been initialized. "
            "Call initialize_scheduler() first."
        )

    return _scheduler


def start_scheduler() -> None:
    """
    Start the scheduler (begin executing scheduled jobs)

    Raises:
        RuntimeError: If scheduler has not been initialized or is already running
    """
    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
        logger.info(f"Scheduled jobs: {len(scheduler.get_jobs())}")

        # Log all scheduled jobs
        for job in scheduler.get_jobs():
            logger.info(f"  - {job.id}: {job.name} (next run: {job.next_run_time})")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        raise RuntimeError(f"Scheduler start failed: {e}") from e


def shutdown_scheduler(wait: bool = True) -> None:
    """
    Shutdown the scheduler gracefully

    Args:
        wait: If True, wait for all currently executing jobs to finish

    Thread Safety:
        This function is thread-safe.
    """
    global _scheduler

    if _scheduler is None:
        logger.debug("Scheduler not initialized, nothing to shutdown")
        return

    with _scheduler_lock:
        if _scheduler is None:
            return

        try:
            if _scheduler.running:
                _scheduler.shutdown(wait=wait)
                logger.info(f"Scheduler shutdown successfully (wait={wait})")
            else:
                logger.debug("Scheduler was not running")

            _scheduler = None

        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}", exc_info=True)
            _scheduler = None  # Reset even on error


# ============================================================================
# Event Listeners
# ============================================================================

def _job_executed_listener(event):
    """
    Event listener for successful job execution

    Args:
        event: JobExecutionEvent containing job execution details
    """
    logger.info(
        f"Job executed successfully: {event.job_id} "
        f"(runtime: {event.retval if hasattr(event, 'retval') else 'N/A'})"
    )


def _job_error_listener(event):
    """
    Event listener for job execution errors

    Args:
        event: JobExecutionEvent containing error details
    """
    logger.error(
        f"Job execution failed: {event.job_id} "
        f"(exception: {event.exception})",
        exc_info=True
    )


def _job_missed_listener(event):
    """
    Event listener for missed job executions

    Args:
        event: JobExecutionEvent for missed jobs
    """
    logger.warning(
        f"Job missed: {event.job_id} "
        f"(scheduled: {event.scheduled_run_time})"
    )


# ============================================================================
# Utility Functions
# ============================================================================

def is_scheduler_running() -> bool:
    """
    Check if scheduler is currently running

    Returns:
        bool: True if scheduler is running, False otherwise
    """
    if _scheduler is None:
        return False

    return _scheduler.running


def get_scheduled_jobs() -> list:
    """
    Get list of all scheduled jobs

    Returns:
        list: List of scheduled job objects

    Raises:
        RuntimeError: If scheduler has not been initialized
    """
    scheduler = get_scheduler()
    return scheduler.get_jobs()


def pause_job(job_id: str) -> None:
    """
    Pause a scheduled job

    Args:
        job_id: ID of the job to pause

    Raises:
        RuntimeError: If scheduler has not been initialized
        JobLookupError: If job with given ID does not exist
    """
    scheduler = get_scheduler()
    scheduler.pause_job(job_id)
    logger.info(f"Job paused: {job_id}")


def resume_job(job_id: str) -> None:
    """
    Resume a paused job

    Args:
        job_id: ID of the job to resume

    Raises:
        RuntimeError: If scheduler has not been initialized
        JobLookupError: If job with given ID does not exist
    """
    scheduler = get_scheduler()
    scheduler.resume_job(job_id)
    logger.info(f"Job resumed: {job_id}")


def remove_job(job_id: str) -> None:
    """
    Remove a job from the scheduler

    Args:
        job_id: ID of the job to remove

    Raises:
        RuntimeError: If scheduler has not been initialized
        JobLookupError: If job with given ID does not exist
    """
    scheduler = get_scheduler()
    scheduler.remove_job(job_id)
    logger.info(f"Job removed: {job_id}")
